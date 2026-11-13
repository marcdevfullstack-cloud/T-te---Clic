"""Clavier HeadPilot : grandes touches, toujours au premier plan, qui ne prend JAMAIS le focus.

Pourquoi pas le clavier visuel de Windows (osk.exe) ? Il ignore souvent les clics simulés
par un autre programme : le texte n'arrive pas. Ce clavier-ci reçoit les clics (tête ou vraie
souris) comme n'importe quelle fenêtre, mais sans s'activer : la fenêtre où l'on écrit garde
le focus et reçoit de vraies frappes (SendInput). Le bandeau indique où le texte va s'écrire.
"""
import ctypes
import ctypes.wintypes as wt
import os
import threading
import time

from PIL import Image, ImageDraw, ImageFont

from . import mouse
from .keyboard_layout import UNITS_WIDE, hit, place, shown_label, typed_char
from .overlay import WNDCLASSEXW, WNDPROC, WS_EX_LAYERED, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW, WS_EX_TOPMOST
from .overlay import WS_POPUP, blit

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32
_user32.GetForegroundWindow.restype = wt.HWND
_user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
_user32.SetForegroundWindow.argtypes = [wt.HWND]
_user32.IsWindow.argtypes = [wt.HWND]
_user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
_user32.LoadCursorW.restype = wt.HANDLE
_user32.LoadCursorW.argtypes = [wt.HINSTANCE, ctypes.c_void_p]

WM_MOUSEACTIVATE, WM_LBUTTONDOWN = 0x0021, 0x0201
MA_NOACTIVATE = 3
SW_SHOWNOACTIVATE, SW_HIDE = 4, 0
PM_REMOVE = 0x1

ACCENT = (124, 92, 255)
GREEN = (34, 197, 94)
SS = 2  # dessin en double résolution, puis réduction : bords lisses


def _font(name: str, size: int):
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


class VirtualKeyboard:
    """Pilotable depuis n'importe quel fil ; la fenêtre vit sur son propre fil."""

    def __init__(self, on_press=None):
        self.on_press = on_press  # callback(label) : son, journal
        self._lock = threading.Lock()
        self._want_visible = False
        self._mode = "abc"
        self._shift = False
        self._at_top = False
        self._pressed: tuple[int, float] | None = None
        self._warn_until = 0.0
        self._target = None  # fenêtre qui reçoit le texte
        self._screen_rect = (0, 0, 0, 0)
        self._placed = []
        self._dirty = True
        self._running = True
        self._pid = os.getpid()
        self._thread = threading.Thread(target=self._run, name="keyboard", daemon=True)
        self._thread.start()

    # --- API (tout fil) ------------------------------------------------------------

    @property
    def visible(self) -> bool:
        return self._want_visible

    def toggle(self) -> bool:
        with self._lock:
            self._want_visible = not self._want_visible
            self._dirty = True
            return self._want_visible

    def contains(self, x: float, y: float) -> bool:
        l, t, r, b = self._screen_rect
        return self._want_visible and l <= x < r and t <= y < b

    def close(self):
        self._running = False

    # --- Fil de la fenêtre -----------------------------------------------------------

    def _run(self):
        self._wndproc = WNDPROC(self._proc)
        hinst = _kernel32.GetModuleHandleW(None)
        wc = WNDCLASSEXW(cbSize=ctypes.sizeof(WNDCLASSEXW), lpfnWndProc=self._wndproc, hInstance=hinst,
                         hCursor=_user32.LoadCursorW(None, ctypes.c_void_p(32512)),  # flèche
                         lpszClassName="HeadPilotKeyboard")
        _user32.RegisterClassExW(ctypes.byref(wc))
        ex = WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        self._hwnd = _user32.CreateWindowExW(ex, "HeadPilotKeyboard", "Clavier HeadPilot", WS_POPUP,
                                             0, 0, 10, 10, None, None, hinst, None)
        shown, last_key = False, None
        msg = wt.MSG()
        while self._running:
            while _user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
                _user32.TranslateMessage(ctypes.byref(msg))
                _user32.DispatchMessageW(ctypes.byref(msg))
            self._track_target()
            if not self._want_visible:
                if shown:
                    _user32.ShowWindow(self._hwnd, SW_HIDE)
                    shown, last_key = False, None
                    self._screen_rect = (0, 0, 0, 0)
                time.sleep(1 / 20)
                continue
            if self._dirty or not shown:
                self._layout()
            pt = wt.POINT()
            _user32.GetCursorPos(ctypes.byref(pt))
            l, t, _, _ = self._screen_rect
            hover = hit(self._placed, pt.x - l, pt.y - t)
            hover_i = self._placed.index(hover) if hover else None
            now = time.monotonic()
            pressed = self._pressed[0] if self._pressed and now - self._pressed[1] < 0.25 else None
            warn = now < self._warn_until
            key = (hover_i, pressed, self._mode, self._shift, self._target_title(), warn, self._screen_rect)
            if key != last_key:
                blit(self._hwnd, self._render(hover_i, pressed, warn), l, t)
                last_key = key
            if not shown:
                _user32.ShowWindow(self._hwnd, SW_SHOWNOACTIVATE)
                shown = True
            time.sleep(1 / 30)
        _user32.DestroyWindow(self._hwnd)

    def _proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_MOUSEACTIVATE:
            return MA_NOACTIVATE  # cliquer sur le clavier n'active jamais sa fenêtre
        if msg == WM_LBUTTONDOWN:
            x, y = ctypes.c_short(lparam & 0xFFFF).value, ctypes.c_short((lparam >> 16) & 0xFFFF).value
            try:
                self._press_at(x, y)
            except Exception as exc:  # une erreur ne doit jamais bloquer la souris
                print("Clavier :", exc)
            return 0
        return _user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    # --- Géométrie et rendu ----------------------------------------------------------------

    def _layout(self):
        left, top, width, height = mouse.work_area()
        try:
            s = _user32.GetDpiForSystem() / 96
        except (AttributeError, OSError):
            s = 1.0
        unit = int(max(54 * s, min(92 * s, width * 0.6 / UNITS_WIDE)))
        self._row_h, self._gap = int(unit * 0.8), max(4, int(6 * s))
        self._pad, self._title_h = int(14 * s), int(34 * s)
        self._scale = s
        w = int(UNITS_WIDE * unit) - self._gap + 2 * self._pad
        h = self._pad + self._title_h + 4 * self._row_h + 3 * self._gap + self._pad
        x = left + (width - w) // 2
        y = top + int(10 * s) if self._at_top else top + height - h - int(10 * s)
        self._placed = place(self._mode, unit, self._row_h, self._gap, self._pad, self._pad + self._title_h)
        self._screen_rect = (x, y, x + w, y + h)
        self._dirty = False

    def _render(self, hover_i, pressed_i, warn) -> Image.Image:
        l, t, r, b = self._screen_rect
        w, h = r - l, b - t
        img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        k = SS
        d.rounded_rectangle((0, 0, w * k - 1, h * k - 1), radius=18 * k, fill=(13, 17, 33, 250),
                            outline=(*ACCENT, 120), width=2 * k)
        s = self._scale
        title_font = _font("segoeuib.ttf", int(15 * s * k))
        info_font = _font("segoeui.ttf", int(13 * s * k))
        ty = self._pad * k + int(6 * s * k)
        d.text((self._pad * k + 4 * k, ty), "HeadPilot · clavier", font=title_font, fill=(230, 232, 245))
        if warn:
            info, color = "Clique d'abord dans le texte où écrire", (255, 170, 80)
        else:
            target = self._target_title()
            info = f"Écrit dans : {target}" if target else "Clique dans le texte où écrire"
            color = (160, 168, 200)
        tw = d.textlength(info, font=info_font)
        d.text((w * k - self._pad * k - 4 * k - tw, ty + 2 * k), info, font=info_font, fill=color)

        key_font = _font("segoeuib.ttf", int(self._row_h * 0.36 * k))
        small_font = _font("segoeuib.ttf", int(self._row_h * 0.26 * k))
        sym_font = _font("seguisym.ttf", int(self._row_h * 0.40 * k))
        for i, p in enumerate(self._placed):
            key = p.key
            x0, y0, x1, y1 = (v * k for v in p.rect)
            special = key.action != "char" or key.label == "Espace"
            fill = (26, 31, 54) if special else (36, 42, 70)
            if key.action == "vk" and key.label == "Entrée":
                fill = (78, 56, 190)
            if key.action == "shift" and self._shift:
                fill = ACCENT
            outline, ow = (255, 255, 255, 25), 1 * k
            if i == hover_i:
                fill = tuple(min(255, c + 22) for c in fill)
                outline, ow = (*ACCENT, 255), 3 * k
            if i == pressed_i:
                fill, outline = GREEN, (*GREEN, 255)
            d.rounded_rectangle((x0, y0, x1, y1), radius=10 * k, fill=(*fill, 255), outline=outline, width=ow)
            label = shown_label(key, self._shift)
            font = sym_font if key.symbol else small_font if len(label) > 1 else key_font
            d.text(((x0 + x1) / 2, (y0 + y1) / 2), label, font=font, fill=(240, 242, 255), anchor="mm")
        return img.resize((w, h), Image.LANCZOS)

    # --- Actions -------------------------------------------------------------------------------

    def _press_at(self, x: int, y: int):
        p = hit(self._placed, x, y)
        if p is None:
            return
        key = p.key
        if key.action in ("char", "vk"):
            if not self._focus_target():
                self._warn_until = time.monotonic() + 3
                return
            if key.action == "char":
                mouse.type_text(typed_char(key, self._shift))
                self._shift = False
            else:
                mouse.press_key(key.value)
        elif key.action == "shift":
            self._shift = not self._shift
        elif key.action == "mode":
            self._mode, self._shift, self._dirty = key.value, False, True
        elif key.action == "move":
            self._at_top, self._dirty = not self._at_top, True
        elif key.action == "hide":
            self._want_visible = False
        self._pressed = (self._placed.index(p), time.monotonic())
        if self.on_press:
            self.on_press(key.label)

    def _owner_pid(self, hwnd) -> int:
        pid = wt.DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value

    def _track_target(self):
        """Retient la dernière fenêtre active qui n'est pas HeadPilot : c'est là qu'on écrit."""
        fg = _user32.GetForegroundWindow()
        if fg and self._owner_pid(fg) != self._pid:
            self._target = fg

    def _focus_target(self) -> bool:
        """Si HeadPilot a le focus (clic sur son panneau), on le rend à la fenêtre où l'on écrit.
        Par sécurité, on ne tape rien si le focus reste chez HeadPilot."""
        fg = _user32.GetForegroundWindow()
        if fg and self._owner_pid(fg) != self._pid:
            return True
        if self._target and _user32.IsWindow(self._target):
            _user32.SetForegroundWindow(self._target)
            time.sleep(0.06)
            fg = _user32.GetForegroundWindow()
            return bool(fg) and self._owner_pid(fg) != self._pid
        return False

    def _target_title(self) -> str:
        if not self._target or not _user32.IsWindow(self._target):
            return ""
        buf = ctypes.create_unicode_buffer(256)
        _user32.GetWindowTextW(self._target, buf, 256)
        title = buf.value.strip()
        return title if len(title) <= 48 else title[:46] + "…"
