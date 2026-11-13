"""Anneau autour du curseur : progression du clic par immobilité, mode défilement, éclair de clic.

Fenêtre Windows « superposée » (layered) : vraie transparence pixel par pixel, toujours
au premier plan, jamais active, et que les clics TRAVERSENT. Elle suit le vrai curseur
à 60 images/s, indépendamment de la caméra. Dessin avec Pillow.
"""
import ctypes
import ctypes.wintypes as wt
import threading
import time

import numpy as np
from PIL import Image, ImageDraw

SIZE = 76
ACCENT = (124, 92, 255)
GREEN = (34, 197, 94)
BLUE = (59, 139, 255)

_user32 = ctypes.windll.user32
_gdi32 = ctypes.windll.gdi32
_kernel32 = ctypes.windll.kernel32

WS_POPUP = 0x80000000
WS_EX_LAYERED, WS_EX_TRANSPARENT, WS_EX_TOPMOST = 0x80000, 0x20, 0x8
WS_EX_TOOLWINDOW, WS_EX_NOACTIVATE = 0x80, 0x08000000
ULW_ALPHA, AC_SRC_ALPHA = 0x2, 0x1
SW_SHOWNOACTIVATE, SW_HIDE = 4, 0
PM_REMOVE = 0x1

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
_user32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
_user32.DefWindowProcW.restype = ctypes.c_ssize_t
_user32.CreateWindowExW.restype = wt.HWND
_user32.CreateWindowExW.argtypes = [wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int, wt.HWND, wt.HMENU, wt.HINSTANCE, wt.LPVOID]
_gdi32.CreateDIBSection.restype = wt.HBITMAP
_user32.GetDC.restype = wt.HDC
_gdi32.CreateCompatibleDC.restype = wt.HDC
_gdi32.SelectObject.restype = wt.HGDIOBJ
_gdi32.SelectObject.argtypes = [wt.HDC, wt.HGDIOBJ]
_gdi32.DeleteObject.argtypes = [wt.HGDIOBJ]
_gdi32.DeleteDC.argtypes = [wt.HDC]
_user32.ReleaseDC.argtypes = [wt.HWND, wt.HDC]
_user32.GetDC.argtypes = [wt.HWND]
_gdi32.CreateCompatibleDC.argtypes = [wt.HDC]
_gdi32.CreateDIBSection.argtypes = [wt.HDC, ctypes.c_void_p, wt.UINT, ctypes.POINTER(ctypes.c_void_p),
                                    wt.HANDLE, wt.DWORD]
_user32.UpdateLayeredWindow.argtypes = [wt.HWND, wt.HDC, ctypes.c_void_p, ctypes.c_void_p, wt.HDC,
                                        ctypes.c_void_p, wt.DWORD, ctypes.c_void_p, wt.DWORD]
_user32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
_user32.ShowWindow.argtypes = [wt.HWND, ctypes.c_int]
_user32.DestroyWindow.argtypes = [wt.HWND]


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [("cbSize", wt.UINT), ("style", wt.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", wt.HINSTANCE), ("hIcon", wt.HICON),
                ("hCursor", wt.HANDLE), ("hbrBackground", wt.HBRUSH), ("lpszMenuName", wt.LPCWSTR),
                ("lpszClassName", wt.LPCWSTR), ("hIconSm", wt.HICON)]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [("BlendOp", ctypes.c_byte), ("BlendFlags", ctypes.c_byte),
                ("SourceConstantAlpha", ctypes.c_ubyte), ("AlphaFormat", ctypes.c_byte)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long),
                ("biPlanes", wt.WORD), ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", ctypes.c_long), ("biYPelsPerMeter", ctypes.c_long),
                ("biClrUsed", wt.DWORD), ("biClrImportant", wt.DWORD)]


def render(progress: float, mode: str, flash: float) -> Image.Image:
    """mode : "pointer", "scroll", "hidden". flash : 0 à 1, éclair après un clic."""
    scale = 3  # dessin en haute résolution puis réduction : bords bien lisses
    s = SIZE * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c, r, wd = s / 2, s / 2 - 6 * scale, 5 * scale
    if flash > 0:
        a = int(170 * flash)
        rr = r * (0.55 + 0.45 * (1 - flash))
        d.ellipse((c - rr, c - rr, c + rr, c + rr), fill=(*GREEN, a))
    if mode == "scroll":
        d.ellipse((c - r, c - r, c + r, c + r), outline=(*BLUE, 230), width=wd)
        for sign in (-1, 1):  # flèches haut / bas
            y = c + sign * r * 0.45
            d.polygon([(c - 9 * scale, y), (c + 9 * scale, y), (c, y + sign * 10 * scale)], fill=(*BLUE, 240))
    elif mode == "pointer" and progress > 0.02:
        d.ellipse((c - r, c - r, c + r, c + r), outline=(255, 255, 255, 110), width=wd)
        d.arc((c - r, c - r, c + r, c + r), -90, -90 + 360 * min(progress, 1), fill=(*ACCENT, 255), width=wd)
    return img.resize((SIZE, SIZE), Image.LANCZOS)


class CursorOverlay:
    """Fenêtre-anneau qui suit le curseur, pilotée depuis n'importe quel fil via set_state()."""

    def __init__(self):
        self._lock = threading.Lock()
        self._state = (0.0, "hidden")
        self._flash_at = 0.0
        self._running = True
        self._thread = threading.Thread(target=self._run, name="overlay", daemon=True)
        self._thread.start()

    def set_state(self, progress: float, mode: str):
        with self._lock:
            self._state = (progress, mode)

    def flash(self):
        with self._lock:
            self._flash_at = time.monotonic()

    def close(self):
        self._running = False

    # --- Fil de la fenêtre (la fenêtre appartient à ce fil) ----------------------

    def _run(self):
        self._wndproc = WNDPROC(lambda h, m, w, l: _user32.DefWindowProcW(h, m, w, l))
        hinst = _kernel32.GetModuleHandleW(None)
        wc = WNDCLASSEXW(cbSize=ctypes.sizeof(WNDCLASSEXW), lpfnWndProc=self._wndproc,
                         hInstance=hinst, lpszClassName="HeadPilotCursorRing")
        _user32.RegisterClassExW(ctypes.byref(wc))
        ex = WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        hwnd = _user32.CreateWindowExW(ex, "HeadPilotCursorRing", "HeadPilot", WS_POPUP, 0, 0, SIZE, SIZE,
                                       None, None, hinst, None)
        visible, last_key = False, None
        msg = wt.MSG()
        while self._running:
            while _user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
                _user32.TranslateMessage(ctypes.byref(msg))
                _user32.DispatchMessageW(ctypes.byref(msg))
            with self._lock:
                progress, mode = self._state
                flash = max(0.0, 1 - (time.monotonic() - self._flash_at) / 0.35)
            show = mode != "hidden" and (mode == "scroll" or progress > 0.02 or flash > 0)
            if show:
                pt = wt.POINT()
                _user32.GetCursorPos(ctypes.byref(pt))
                key = (round(progress, 2), mode, round(flash, 2))
                if key != last_key:
                    self._blit(hwnd, render(progress, mode, flash), pt.x - SIZE // 2, pt.y - SIZE // 2)
                    last_key = key
                else:
                    _user32.SetWindowPos(hwnd, wt.HWND(-1), pt.x - SIZE // 2, pt.y - SIZE // 2, 0, 0,
                                         0x0001 | 0x0010)  # SWP_NOSIZE | SWP_NOACTIVATE, toujours au-dessus
                if not visible:
                    _user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
                    visible = True
            elif visible:
                _user32.ShowWindow(hwnd, SW_HIDE)
                visible, last_key = False, None
            time.sleep(1 / 60)
        _user32.DestroyWindow(hwnd)

    @staticmethod
    def _blit(hwnd, img: Image.Image, x: int, y: int):
        """Envoie l'image RGBA (alpha prémultiplié, ordre BGRA) à la fenêtre superposée."""
        arr = np.asarray(img, dtype=np.float32)
        alpha = arr[:, :, 3:4] / 255.0
        bgra = np.concatenate([arr[:, :, 2::-1] * alpha, arr[:, :, 3:4]], axis=2).astype(np.uint8)
        data = np.ascontiguousarray(bgra).tobytes()

        screen_dc = _user32.GetDC(None)
        mem_dc = _gdi32.CreateCompatibleDC(screen_dc)
        bmi = BITMAPINFOHEADER(biSize=ctypes.sizeof(BITMAPINFOHEADER), biWidth=SIZE, biHeight=-SIZE,
                               biPlanes=1, biBitCount=32, biCompression=0)
        bits = ctypes.c_void_p()
        hbmp = _gdi32.CreateDIBSection(mem_dc, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
        ctypes.memmove(bits, data, len(data))
        old = _gdi32.SelectObject(mem_dc, hbmp)
        pos, size, src = wt.POINT(x, y), wt.SIZE(SIZE, SIZE), wt.POINT(0, 0)
        blend = BLENDFUNCTION(0, 0, 255, AC_SRC_ALPHA)
        _user32.UpdateLayeredWindow(hwnd, screen_dc, ctypes.byref(pos), ctypes.byref(size), mem_dc,
                                    ctypes.byref(src), 0, ctypes.byref(blend), ULW_ALPHA)
        _gdi32.SelectObject(mem_dc, old)
        _gdi32.DeleteObject(hbmp)
        _gdi32.DeleteDC(mem_dc)
        _user32.ReleaseDC(None, screen_dc)

