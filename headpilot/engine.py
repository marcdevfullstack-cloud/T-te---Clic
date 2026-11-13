"""Moteur de HeadPilot : caméra → visage → gestes → souris.

Tourne sur son propre fil. L'interface lit l'état via le Bridge et envoie des demandes
(pause, recentrer, clavier, réglages) via request().
"""
import math
import sys
import threading
import time
from collections import deque

import cv2

from . import mouse
from .config import Config
from .gestures import GestureDetector, GestureSettings
from .pointer import DwellClicker, PointerMapper
from .tracker import FaceTracker

CALIBRATION_SECONDS = 2.0
TAKEOVER_PX = 40  # la vraie souris a bougé de plus que ça : l'aidant reprend la main
TAKEOVER_SECONDS = 2.5
SCROLL_SPEED = 60.0  # crans de molette par seconde, par unité d'inclinaison de la tête
CLICK_LOOKBACK = 0.15  # on clique là où était le curseur juste AVANT le geste


def open_camera(index: int):
    backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
    cap = cv2.VideoCapture(index, backend)
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f"Impossible d'ouvrir la caméra n°{index}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return cap


class Engine:
    def __init__(self, cfg: Config, bridge=None, overlay=None, keyboard=None):
        self.cfg = cfg
        self.bridge = bridge
        self.overlay = overlay
        self.keyboard = keyboard  # clavier HeadPilot (None : clavier visuel de Windows)
        self.mapper = PointerMapper()
        self.dwell = DwellClicker()
        self.gestures = GestureDetector(GestureSettings())
        self.apply_settings()

        self.quit = threading.Event()
        self.paused = False
        self.status = "Démarrage"
        self.error: str | None = None
        self._requests: set[str] = set()
        self._lock = threading.Lock()
        self._calib_until: float | None = None
        self._calib_samples: list[tuple[float, float]] = []
        self._last_set: tuple[float, float] | None = None
        self._takeover_until = 0.0
        self._history: deque[tuple[float, float, float]] = deque(maxlen=60)  # (t, x, y)
        self._gesture_start_pos: tuple[float, float] | None = None
        self._scroll_acc = 0.0
        self._last_t: float | None = None
        self._fps = 0.0
        self._published_at = 0.0
        self._screen = mouse.screen_size()

    # --- Réglages et demandes ---------------------------------------------------

    def apply_settings(self):
        c = self.cfg
        self.mapper.sensitivity_x, self.mapper.sensitivity_y = c.sensitivity_x, c.sensitivity_y
        self.mapper.set_smoothing(c.smoothing)
        self.dwell.seconds = c.dwell_seconds
        g = self.gestures.settings
        g.blink_click, g.brow_right_click, g.mouth_scroll = c.blink_click, c.brow_right_click, c.mouth_scroll

    def request(self, name: str):
        with self._lock:
            self._requests.add(name)

    def _take(self, name: str) -> bool:
        with self._lock:
            if name in self._requests:
                self._requests.discard(name)
                return True
            return False

    def toggle_pause(self):
        self.paused = not self.paused
        self.dwell.reset()
        if self.paused:
            self._say("Contrôle en pause.", "Contrôle en pause", "grey")
        else:
            self._last_set = None
            self._say("Contrôle actif.", "Contrôle actif", "green")

    # --- Boucle principale --------------------------------------------------------

    def run(self):
        try:
            cap = open_camera(self.cfg.camera_index)
        except RuntimeError as exc:
            self.error = str(exc)
            self.status = "Caméra indisponible"
            self._publish(time.monotonic(), None, force=True)
            self.quit.wait()
            return
        tracker = FaceTracker(self.cfg.model_path)
        self._start_calibration(time.monotonic())
        last_ts = -1
        try:
            while not self.quit.is_set():
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.05)
                    continue
                frame = cv2.flip(frame, 1)  # miroir : tourner la tête à droite va à droite
                now = time.monotonic()
                last_ts = max(int(now * 1000), last_ts + 1)
                reading = tracker.process(frame, last_ts)
                self._step(now, reading)
                if self.bridge is not None:
                    self._draw(frame, reading)
                    self.bridge.publish_frame(frame)
                self._publish(now, reading)
        finally:
            cap.release()
            tracker.close()
            if self.overlay is not None:
                self.overlay.set_state(0, "hidden")

    def _step(self, now: float, reading):
        if self._last_t is not None:
            dt = now - self._last_t
            self._fps = 0.9 * self._fps + 0.1 * (1 / dt if dt > 0 else 0)
        self._last_t = now

        if self._take("pause"):
            self.toggle_pause()
        if self._take("recenter"):
            self._start_calibration(now)
        if self._take("keyboard"):
            self._toggle_keyboard()

        was_closed, was_brow = self.gestures.eyes_closed, self.gestures.brow_active
        events = self.gestures.update(now, reading.signals if reading else None)
        if (self.gestures.eyes_closed and not was_closed) or (self.gestures.brow_active and not was_brow):
            self._gesture_start_pos = self._position_at(now - CLICK_LOOKBACK)
        if "toggle_pause" in events:
            self.toggle_pause()

        if self._calib_until is not None:
            self._calibrate(now, reading)
            self._set_overlay(0, "hidden")
            return
        if self.paused or reading is None or not self.mapper.calibrated:
            self.status = "En pause" if self.paused else "Visage non détecté" if reading is None else self.status
            self._set_overlay(0, "hidden")
            return

        # L'aidant a touché la vraie souris : on lui laisse la main quelques secondes.
        x0, y0 = mouse.position()
        if self._last_set is not None and math.dist((x0, y0), self._last_set) > TAKEOVER_PX:
            self._takeover_until = now + TAKEOVER_SECONDS
            self._last_set = None
            self._log("Souris physique : contrôle par la tête suspendu", "orange")
        if now < self._takeover_until:
            self.status = "Souris physique"
            self.dwell.reset()
            self._set_overlay(0, "hidden")
            return

        self.status = "Défilement" if self.gestures.scrolling else "Actif"
        freeze = self.gestures.eyes_closed or self.gestures.brow_active or self.gestures.scrolling
        if self.gestures.scrolling:
            self._scroll(now, reading)
        elif not freeze:
            nx, ny = self.mapper.map(reading.yaw, reading.pitch, now)
            w, h = self._screen
            x, y = nx * (w - 1), ny * (h - 1)
            mouse.move(x, y)
            self._last_set = (x, y)
            self._history.append((now, x, y))

        for event in events:
            if event == "click_left":
                self._click("left", "Clic gauche (clignement)")
            elif event == "click_right":
                self._click("right", "Clic droit (sourcils)")
            elif event == "scroll_on":
                self._scroll_acc = 0.0
                self._log("Défilement : lève ou baisse la tête", "blue")
            elif event == "scroll_off":
                self._log("Fin du défilement", "blue")

        progress = 0.0
        if self.cfg.dwell_click and not freeze:
            x, y = mouse.position()
            on_keys = self.keyboard is not None and self.keyboard.contains(x, y)
            st = self.dwell.update(now, x, y, repeat=on_keys)
            progress = st.progress
            if st.fired:
                self._click("left", "Clic (immobilité)", use_gesture_pos=False)
        self._set_overlay(progress, "scroll" if self.gestures.scrolling else "pointer")

    # --- Actions ------------------------------------------------------------------

    def _click(self, button: str, label: str, use_gesture_pos: bool = True):
        if use_gesture_pos and self._gesture_start_pos is not None:
            mouse.move(*self._gesture_start_pos)  # là où l'on visait avant de cligner
            self._last_set = self._gesture_start_pos
        mouse.click(button)
        self._gesture_start_pos = None
        self.dwell.hold(*mouse.position())  # pas de second clic sur place par immobilité
        if self.overlay is not None:
            self.overlay.flash()
        if self.cfg.click_sound:
            _tick(button)
        self._log(label, "green")

    def _toggle_keyboard(self):
        if self.keyboard is None:
            mouse.open_onscreen_keyboard()
            self._say("Clavier visuel ouvert.", "Clavier visuel de Windows ouvert", "accent")
        elif self.keyboard.toggle():
            self._say("Clavier affiché. Clique d'abord dans le texte où écrire.",
                      "Clavier affiché : clique d'abord dans le texte où écrire", "accent")
        else:
            self._say("Clavier masqué.", "Clavier masqué", "grey")

    def _scroll(self, now: float, reading):
        center_pitch = self.mapper.center[1]
        tilt = reading.pitch - center_pitch  # positif : tête baissée
        if abs(tilt) < 0.02:  # zone neutre
            return
        dt = min(now - (self._history[-1][0] if self._history else now), 0.1) or 1 / 30
        self._scroll_acc += -tilt * SCROLL_SPEED * dt
        notches = int(self._scroll_acc)
        if notches:
            mouse.scroll(notches)
            self._scroll_acc -= notches
        self._history.append((now, *(self._last_set or mouse.position())))

    def _position_at(self, t: float) -> tuple[float, float] | None:
        best = None
        for ht, x, y in self._history:
            if ht <= t:
                best = (x, y)
        return best or (self._history[-1][1:] if self._history else None)

    # --- Recentrage ---------------------------------------------------------------

    def _start_calibration(self, now: float):
        self._calib_until = now + CALIBRATION_SECONDS
        self._calib_samples = []
        self.status = "Recentrage"
        self._say("Regarde le centre de l'écran, sans bouger.", "Recentrage : regarde le centre de l'écran", "orange")

    def _calibrate(self, now: float, reading):
        self.status = "Recentrage"
        if reading is not None:
            self._calib_samples.append((reading.yaw, reading.pitch))
        if now < self._calib_until:
            return
        if len(self._calib_samples) < 10:  # visage pas assez vu : on prolonge
            self._calib_until = now + 1.0
            return
        self.mapper.calibrate(self._calib_samples)
        self._calib_until = None
        w, h = self._screen
        mouse.move(w / 2, h / 2)
        self._last_set = (w / 2, h / 2)
        self.dwell.reset()
        self._say("C'est prêt. Tourne la tête pour déplacer la souris.", "Recentrage terminé", "green")

    # --- Interface ------------------------------------------------------------------

    def _set_overlay(self, progress: float, mode: str):
        if self.overlay is not None:
            self.overlay.set_state(progress, mode)

    def _say(self, speech: str, log: str, tone: str):
        if self.bridge is not None:
            if self.cfg.voice:
                self.bridge.speak(speech)
            self.bridge.log(log, tone)
        print(log)

    def _log(self, text: str, tone: str):
        if self.bridge is not None:
            self.bridge.log(text, tone)

    def _draw(self, frame, reading):
        if reading is None:
            return
        color = (166, 107, 255) if not self.paused else (140, 140, 140)
        for p in reading.eyes:
            cv2.circle(frame, (int(p[0]), int(p[1])), 4, (255, 200, 120), -1, cv2.LINE_AA)
        mid = ((reading.eyes[0][0] + reading.eyes[1][0]) / 2, (reading.eyes[0][1] + reading.eyes[1][1]) / 2)
        cv2.line(frame, (int(mid[0]), int(mid[1])), (int(reading.nose[0]), int(reading.nose[1])), color, 2, cv2.LINE_AA)
        cv2.circle(frame, (int(reading.nose[0]), int(reading.nose[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(frame, (int(reading.nose[0]), int(reading.nose[1])), 6, color, -1, cv2.LINE_AA)

    def _publish(self, now: float, reading, force: bool = False):
        if self.bridge is None or (not force and now - self._published_at < 0.08):
            return
        self._published_at = now
        s = reading.signals if reading else None
        calib_left = None if self._calib_until is None else max(0.0, self._calib_until - now)
        self.bridge.publish_state({
            "status": self.status,
            "paused": self.paused,
            "error": self.error,
            "face": reading is not None,
            "calibrating": calib_left,
            "fps": round(self._fps),
            "signals": {"blink": s.blink if s else 0, "brow": s.brow if s else 0, "jaw": s.jaw if s else 0},
            "closedFor": round(self.gestures.closed_for(now), 2),
            "scrolling": self.gestures.scrolling,
            "settings": self.cfg.to_dict(),
        })


def _tick(button: str):
    """Petit « tic » sonore de confirmation, sans bloquer le moteur."""
    if sys.platform != "win32":
        return
    import winsound

    freq = 1500 if button == "left" else 900
    threading.Thread(target=winsound.Beep, args=(freq, 35), daemon=True).start()
