"""Reconnaissance des gestes du visage (logique pure, testable).

- Clignement LONG (0,45 à 1,6 s) : clic gauche. Les clignements naturels (< 0,3 s) sont ignorés.
- Yeux fermés 2,5 s : pause / reprise du contrôle (sans les mains).
- Sourcils levés 0,35 s : clic droit.
- Bouche ouverte : mode défilement (lever / baisser la tête fait défiler).
"""
from dataclasses import dataclass

EYES_CLOSED = 0.5
BROW_UP = 0.55
BROW_DOWN = 0.35
JAW_OPEN = 0.45
JAW_CLOSED = 0.3


@dataclass
class GestureSettings:
    blink_click: bool = True
    brow_right_click: bool = True
    mouth_scroll: bool = True
    long_blink_min: float = 0.45
    long_blink_max: float = 1.6
    pause_blink: float = 2.5
    brow_hold: float = 0.35
    refractory: float = 0.6  # délai minimal entre deux clics


@dataclass(frozen=True)
class FaceSignals:
    blink: float  # 0 à 1, les deux yeux
    brow: float  # 0 à 1, sourcils levés
    jaw: float  # 0 à 1, bouche ouverte


class GestureDetector:
    def __init__(self, settings: GestureSettings | None = None):
        self.settings = settings or GestureSettings()
        self.closed_since: float | None = None
        self._pause_fired = False
        self._brow_since: float | None = None
        self._brow_fired = False
        self.scrolling = False
        self._last_click = float("-inf")

    @property
    def eyes_closed(self) -> bool:
        return self.closed_since is not None

    @property
    def brow_active(self) -> bool:
        return self._brow_since is not None

    def closed_for(self, now: float) -> float:
        return 0.0 if self.closed_since is None else now - self.closed_since

    def update(self, now: float, s: FaceSignals | None) -> list[str]:
        """Événements : click_left, click_right, toggle_pause, scroll_on, scroll_off."""
        st = self.settings
        events: list[str] = []
        if s is None:  # visage perdu : on annule les gestes en cours
            self.closed_since, self._brow_since = None, None
            if self.scrolling:
                self.scrolling = False
                events.append("scroll_off")
            return events

        # Yeux : clignement long = clic ; très long = pause
        if s.blink >= EYES_CLOSED:
            if self.closed_since is None:
                self.closed_since, self._pause_fired = now, False
            elif not self._pause_fired and now - self.closed_since >= st.pause_blink:
                self._pause_fired = True
                events.append("toggle_pause")
        elif self.closed_since is not None:
            duration = now - self.closed_since
            self.closed_since = None
            if not self._pause_fired and st.blink_click and st.long_blink_min <= duration <= st.long_blink_max:
                self._click(now, "click_left", events)

        # Sourcils levés = clic droit
        if s.brow >= BROW_UP:
            if self._brow_since is None:
                self._brow_since, self._brow_fired = now, False
            elif not self._brow_fired and st.brow_right_click and now - self._brow_since >= st.brow_hold:
                self._brow_fired = True
                self._click(now, "click_right", events)
        elif s.brow <= BROW_DOWN:
            self._brow_since = None

        # Bouche ouverte = défilement (hystérésis : pas de clignotement du mode)
        if st.mouth_scroll and not self.scrolling and s.jaw >= JAW_OPEN:
            self.scrolling = True
            events.append("scroll_on")
        elif self.scrolling and (s.jaw <= JAW_CLOSED or not st.mouth_scroll):
            self.scrolling = False
            events.append("scroll_off")
        return events

    def _click(self, now: float, event: str, events: list[str]):
        if now - self._last_click >= self.settings.refractory:
            self._last_click = now
            events.append(event)
