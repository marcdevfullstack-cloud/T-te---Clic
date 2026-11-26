"""Filtre « One Euro » : lisse les tremblements quand on bouge peu, reste réactif quand on bouge vite.

Référence : Casiez, Roussel, Vogel, « 1€ Filter » (CHI 2012), standard pour le pointage par la tête.
"""
import math


def _alpha(dt: float, cutoff: float) -> float:
    tau = 1.0 / (2 * math.pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


class OneEuroFilter:
    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.02, d_cutoff: float = 1.0):
        self.min_cutoff = min_cutoff  # plus bas = plus stable à l'arrêt
        self.beta = beta  # plus haut = plus réactif aux mouvements rapides
        self.d_cutoff = d_cutoff
        self.reset()

    def reset(self):
        self._x: float | None = None
        self._dx = 0.0
        self._t: float | None = None

    def __call__(self, x: float, t: float) -> float:
        if self._x is None or self._t is None or t <= self._t:
            self._x, self._t = x, t
            return x
        dt = t - self._t
        self._t = t
        dx = (x - self._x) / dt
        self._dx += _alpha(dt, self.d_cutoff) * (dx - self._dx)
        cutoff = self.min_cutoff + self.beta * abs(self._dx)
        self._x += _alpha(dt, cutoff) * (x - self._x)
        return self._x
