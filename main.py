"""Tête-à-Clic — contrôle de l'ordinateur par la tête et le regard. © 2026 MarcDev@

    python main.py              lance l'application
    python main.py --version    affiche la version
    python main.py --selftest   vérifie l'installation (modèle d'IA, interface), sans caméra
"""
import ctypes
import sys

from tete_a_clic import mouse
from tete_a_clic.config import APP_ID, APP_NAME, VERSION, Config


def _log_to_file(cfg: Config):
    """Application installée (sans console) : les messages vont dans un journal."""
    if not getattr(sys, "frozen", False) and sys.stdout is not None:
        return
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    log = open(cfg.data_dir / "tete_a_clic.log", "a", encoding="utf-8", buffering=1)  # noqa: SIM115
    sys.stdout = sys.stderr = log


def _already_running() -> bool:
    """Deux exemplaires se disputeraient la webcam et la souris : un seul à la fois."""
    if sys.platform != "win32":
        return False
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    _already_running.handle = kernel32.CreateMutexW(None, False, f"Local\\{APP_ID}.SingleInstance")
    if kernel32.GetLastError() != 183:  # ERROR_ALREADY_EXISTS
        return False
    ctypes.windll.user32.MessageBoxW(None, f"{APP_NAME} est déjà ouvert.", APP_NAME, 0x40 | 0x40000)
    return True


def _selftest() -> int:
    """Charge le modèle d'IA et vérifie l'interface, sans ouvrir la caméra. Code 0 = tout va bien."""
    import numpy as np

    from tete_a_clic.tracker import FaceTracker
    from tete_a_clic.ui.window import WEB_DIR

    cfg = Config()
    assert (WEB_DIR / "panel.html").exists(), f"interface introuvable : {WEB_DIR}"
    tracker = FaceTracker(cfg.model_path)
    reading = tracker.process(np.zeros((480, 640, 3), np.uint8), 1)
    tracker.close()
    assert reading is None  # image noire : aucun visage, mais le modèle a tourné
    print(f"{APP_NAME} {VERSION} : autotest réussi")
    return 0


def main():
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    if "--version" in sys.argv:
        print(f"{APP_NAME} {VERSION}")
        return
    cfg = Config.load()
    _log_to_file(cfg)
    if "--selftest" in sys.argv:
        try:
            sys.exit(_selftest())
        except Exception as exc:  # noqa: BLE001 - le code de sortie suffit au script de fabrication
            print("Autotest échoué :", repr(exc))
            sys.exit(1)
    if _already_running():
        return
    mouse.enable_dpi_awareness()  # vrais pixels, avant toute fenêtre
    from tete_a_clic.ui.window import run_app

    print(f"--- {APP_NAME} {VERSION} ---")
    run_app(cfg)


if __name__ == "__main__":
    main()
