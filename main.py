"""HeadPilot — contrôle de l'ordinateur par la tête et le regard. © 2026 MarcDev@

    python main.py
"""
import sys

from headpilot import mouse
from headpilot.config import APP_NAME, VERSION, Config


def main():
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    if "--version" in sys.argv:
        print(f"{APP_NAME} {VERSION}")
        return
    mouse.enable_dpi_awareness()  # vrais pixels, avant toute fenêtre
    from headpilot.ui.window import run_app

    run_app(Config.load())


if __name__ == "__main__":
    main()
