"""De la tête à l'écran : position du curseur et clic par immobilité (logique pure, testable)."""
import math
import statistics
from dataclasses import dataclass

from .filters import OneEuroFilter

# Amplitude de tête qui couvre tout l'écran, à sensibilité 1 (rotation mesurée par le nez).
BASE_RANGE_X = 0.22  # nez décalé de ±0,22 × écart des yeux = bord gauche/droit
BASE_RANGE_Y = 0.12  # vers le haut/bas, la tête bouge moins


class PointerMapper:
    """Pointage absolu : tourner la tête vers un coin de l'écran y amène le curseur."""

    def __init__(self, sensitivity_x: float = 1.0, sensitivity_y: float = 1.0, smoothing: float = 0.5):
        self.sensitivity_x = sensitivity_x
        self.sensitivity_y = sensitivity_y
        self.center: tuple[float, float] | None = None
        self._fx = OneEuroFilter()
        self._fy = OneEuroFilter()
        self.set_smoothing(smoothing)

    def set_smoothing(self, smoothing: float):
        """0 = très réactif, 1 = très stable."""
        smoothing = max(0.0, min(1.0, smoothing))
        for f in (self._fx, self._fy):
            f.min_cutoff = 2.5 - 2.2 * smoothing
            f.beta = 0.6 - 0.5 * smoothing

    @property
    def calibrated(self) -> bool:
        return self.center is not None

    def calibrate(self, samples: list[tuple[float, float]]):
        """Centre = position de repos de la tête (médiane, robuste aux secousses)."""
        self.center = (statistics.median(s[0] for s in samples), statistics.median(s[1] for s in samples))
        self._fx.reset()
        self._fy.reset()

    def map(self, yaw: float, pitch: float, t: float) -> tuple[float, float]:
        """Renvoie une position normalisée (0-1, 0-1) sur l'écran, lissée."""
        cx, cy = self.center or (yaw, pitch)
        nx = 0.5 + (yaw - cx) / (2 * BASE_RANGE_X / self.sensitivity_x)
        ny = 0.5 + (pitch - cy) / (2 * BASE_RANGE_Y / self.sensitivity_y)
        nx, ny = self._fx(nx, t), self._fy(ny, t)
        return max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny))


@dataclass
class DwellState:
    progress: float = 0.0  # 0 à 1
    fired: bool = False


class DwellClicker:
    """Clic par immobilité : rester dans un petit cercle pendant `seconds` déclenche un clic.

    Après un clic, il faut s'éloigner (`rearm_px`) avant de pouvoir recliquer : on évite
    ainsi les clics en rafale quand la personne se repose sans bouger.
    """

    def __init__(self, seconds: float = 1.2, radius_px: float = 28, rearm_px: float = 60):
        self.seconds = seconds
        self.radius_px = radius_px
        self.rearm_px = rearm_px
        self.reset()

    def reset(self):
        self._anchor: tuple[float, float] | None = None
        self._since = 0.0
        self._armed = True
        self._last_click: tuple[float, float] | None = None

    def update(self, t: float, x: float, y: float) -> DwellState:
        if self._anchor is None or math.dist(self._anchor, (x, y)) > self.radius_px:
            self._anchor, self._since = (x, y), t
        if not self._armed and (self._last_click is None or math.dist(self._last_click, (x, y)) > self.rearm_px):
            self._armed = True
            self._anchor, self._since = (x, y), t
        if not self._armed:
            return DwellState()
        progress = (t - self._since) / self.seconds
        if progress >= 1:
            self._armed = False
            self._last_click = (x, y)
            return DwellState(1.0, True)
        return DwellState(max(0.0, progress), False)
