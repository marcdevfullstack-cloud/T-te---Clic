"""Pilotage de la souris Windows (ctypes, aucune dépendance)."""
import ctypes
import subprocess
import sys

IS_WINDOWS = sys.platform == "win32"

_LEFTDOWN, _LEFTUP = 0x0002, 0x0004
_RIGHTDOWN, _RIGHTUP = 0x0008, 0x0010
_WHEEL = 0x0800


class _Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def enable_dpi_awareness():
    """Coordonnées en vrais pixels, même avec un affichage à 125 % ou 150 %."""
    if not IS_WINDOWS:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def screen_size() -> tuple[int, int]:
    if not IS_WINDOWS:
        return 1920, 1080
    return ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1)


class _Rect(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def work_area() -> tuple[int, int, int, int]:
    """Zone utile de l'écran (sans la barre des tâches) : gauche, haut, largeur, hauteur."""
    r = _Rect()
    if IS_WINDOWS and ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0):
        return r.left, r.top, r.right - r.left, r.bottom - r.top
    w, h = screen_size()
    return 0, 0, w, h


def position() -> tuple[int, int]:
    p = _Point()
    if IS_WINDOWS:
        ctypes.windll.user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def move(x: float, y: float):
    if IS_WINDOWS:
        ctypes.windll.user32.SetCursorPos(int(round(x)), int(round(y)))


def click(button: str = "left", double: bool = False):
    if not IS_WINDOWS:
        return
    down, up = (_RIGHTDOWN, _RIGHTUP) if button == "right" else (_LEFTDOWN, _LEFTUP)
    for _ in range(2 if double else 1):
        ctypes.windll.user32.mouse_event(down, 0, 0, 0, 0)
        ctypes.windll.user32.mouse_event(up, 0, 0, 0, 0)


def scroll(notches: float):
    """Molette : positif = vers le haut."""
    if IS_WINDOWS and notches:
        ctypes.windll.user32.mouse_event(_WHEEL, 0, 0, int(notches * 120), 0)


# --- Clavier : vraies frappes envoyées à la fenêtre active (SendInput) ---------------

_KEYEVENTF_KEYUP, _KEYEVENTF_UNICODE = 0x0002, 0x0004


class _KeybdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.c_size_t)]


class _MouseInput(ctypes.Structure):  # présent seulement pour donner sa taille à l'union
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.c_size_t)]


class _InputUnion(ctypes.Union):
    _fields_ = [("ki", _KeybdInput), ("mi", _MouseInput)]


class _Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("u", _InputUnion)]


def _send(events: list[tuple[int, int, int]]):
    """events : (vk, scan, flags) envoyés d'un seul bloc."""
    if not IS_WINDOWS or not events:
        return
    arr = (_Input * len(events))()
    for i, (vk, scan, flags) in enumerate(events):
        arr[i].type = 1  # INPUT_KEYBOARD
        arr[i].u.ki = _KeybdInput(vk, scan, flags, 0, 0)
    ctypes.windll.user32.SendInput(len(events), arr, ctypes.sizeof(_Input))


def type_text(text: str):
    """Tape du texte Unicode (accents, €…), quelle que soit la disposition du clavier."""
    events = []
    for ch in text:
        for unit in _utf16_units(ch):
            events += [(0, unit, _KEYEVENTF_UNICODE), (0, unit, _KEYEVENTF_UNICODE | _KEYEVENTF_KEYUP)]
    _send(events)


def press_key(vk: int):
    """Touche spéciale : Entrée, Retour arrière, Tab, flèches…"""
    ext = 0x0001 if 0x21 <= vk <= 0x2E else 0  # flèches & co : touches « étendues »
    _send([(vk, 0, ext), (vk, 0, ext | _KEYEVENTF_KEYUP)])


def _utf16_units(ch: str) -> list[int]:
    data = ch.encode("utf-16-le")
    return [int.from_bytes(data[i:i + 2], "little") for i in range(0, len(data), 2)]


def open_onscreen_keyboard():
    """Clavier visuel de Windows (osk.exe), utilisable avec le clic par immobilité."""
    if IS_WINDOWS:
        subprocess.Popen("osk.exe", shell=True)  # noqa: S602,S607 - programme système
