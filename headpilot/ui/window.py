"""Fenêtre de contrôle de HeadPilot (pywebview + Edge WebView2)."""
import threading
from pathlib import Path

import webview

from .. import mouse
from ..config import APP_NAME, AUTHOR, CONTACT_EMAIL, RESOURCE_DIR, VERSION, Config
from ..engine import Engine

WEB_DIR = Path(__file__).resolve().parent / "web"
if not WEB_DIR.exists():  # application installée
    WEB_DIR = RESOURCE_DIR / "headpilot" / "ui" / "web"


class Api:
    """Fonctions appelées par l'interface (window.pywebview.api.*)."""

    def __init__(self, engine: Engine, bridge):
        self._engine = engine
        self._bridge = bridge

    def state(self) -> dict:
        return self._bridge.snapshot()

    def action(self, name: str):
        if name in ("pause", "recenter", "keyboard"):
            self._engine.request(name)

    def set_setting(self, key: str, value) -> bool:
        cfg = self._engine.cfg
        if not cfg.update({key: value}):
            return False
        cfg.save()
        self._engine.apply_settings()
        return True

    def about(self) -> dict:
        return {"name": APP_NAME, "version": VERSION, "author": AUTHOR, "contact": CONTACT_EMAIL}


def run_app(cfg: Config):
    from ..hotkey import GlobalHotkey
    from ..overlay import CursorOverlay
    from .bridge import Bridge

    bridge = Bridge()
    overlay = CursorOverlay()
    engine = Engine(cfg, bridge=bridge, overlay=overlay)
    hotkey = GlobalHotkey(lambda: engine.request("pause"))
    api = Api(engine, bridge)

    left, top, _, area_h = mouse.work_area()
    window = webview.create_window(
        f"{APP_NAME} — contrôle par la tête", url=str(WEB_DIR / "panel.html"), js_api=api,
        width=460, height=min(880, area_h - 40), x=left + 20, y=top + 10,
        min_size=(400, 520), background_color="#0b0e1a",
    )

    def worker():
        threading.Thread(target=engine.run, name="engine", daemon=True).start()

    def on_closed():
        engine.quit.set()
        overlay.close()
        hotkey.close()
        bridge.close()

    window.events.closed += on_closed
    webview.start(worker, http_server=True, private_mode=True)
