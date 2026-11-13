"""Raccourci global pour l'aidant : Ctrl + Alt + P met en pause / reprend, même hors de la fenêtre."""
import ctypes
import ctypes.wintypes as wt
import threading

MOD_ALT, MOD_CONTROL, MOD_NOREPEAT = 0x1, 0x2, 0x4000
WM_HOTKEY = 0x0312
PM_REMOVE = 0x1


class GlobalHotkey:
    def __init__(self, callback, key: str = "P"):
        self._callback = callback
        self._key = ord(key.upper())
        self._running = True
        self.registered = False
        threading.Thread(target=self._run, name="hotkey", daemon=True).start()

    def _run(self):
        import time

        user32 = ctypes.windll.user32
        self.registered = bool(user32.RegisterHotKey(None, 1, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, self._key))
        msg = wt.MSG()
        while self._running:
            while user32.PeekMessageW(ctypes.byref(msg), None, WM_HOTKEY, WM_HOTKEY, PM_REMOVE):
                if msg.message == WM_HOTKEY:
                    self._callback()
            time.sleep(0.05)
        user32.UnregisterHotKey(None, 1)

    def close(self):
        self._running = False
