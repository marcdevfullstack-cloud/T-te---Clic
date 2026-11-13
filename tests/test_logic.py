"""Tests de la logique de HeadPilot (sans caméra ni souris)."""
import random
import unittest

from headpilot.config import Config
from headpilot.filters import OneEuroFilter
from headpilot.gestures import FaceSignals, GestureDetector, GestureSettings
from headpilot.keyboard_layout import LAYOUTS, UNITS_WIDE, VK_RETURN, hit, place, typed_char
from headpilot.pointer import DwellClicker, PointerMapper

OPEN = FaceSignals(blink=0.05, brow=0.1, jaw=0.05)
CLOSED = FaceSignals(blink=0.9, brow=0.1, jaw=0.05)
BROWS = FaceSignals(blink=0.05, brow=0.8, jaw=0.05)
MOUTH = FaceSignals(blink=0.05, brow=0.1, jaw=0.7)


def feed(det, start, seconds, signals, fps=30):
    events = []
    for i in range(int(seconds * fps)):
        events += det.update(start + i / fps, signals)
    return events


class FilterTests(unittest.TestCase):
    def test_reduces_jitter_but_follows_moves(self):
        random.seed(1)
        f = OneEuroFilter(min_cutoff=0.5, beta=0.1)
        out = [f(0.5 + random.uniform(-0.01, 0.01), i / 30) for i in range(60)]
        self.assertLess(max(out[30:]) - min(out[30:]), 0.01)  # tremblement atténué
        for i in range(60, 90):
            last = f(0.9, i / 30)
        self.assertGreater(last, 0.85)  # un vrai mouvement est suivi


class PointerTests(unittest.TestCase):
    def test_center_and_edges(self):
        m = PointerMapper(smoothing=0)
        m.calibrate([(0.0, 0.5)] * 5)
        self.assertEqual(m.map(0.0, 0.5, 0.0), (0.5, 0.5))
        m2 = PointerMapper(smoothing=0)
        m2.calibrate([(0.0, 0.5)])
        x, y = m2.map(0.30, 0.5, 0.0)  # tête tournée au-delà de l'amplitude : bord droit
        self.assertEqual(x, 1.0)

    def test_sensitivity_reduces_needed_movement(self):
        low, high = PointerMapper(1.0, smoothing=0), PointerMapper(2.0, smoothing=0)
        for m in (low, high):
            m.calibrate([(0.0, 0.0)])
        self.assertGreater(high.map(0.05, 0, 0)[0], low.map(0.05, 0, 0)[0])

    def test_dwell_click_then_needs_to_move_away(self):
        d = DwellClicker(seconds=1.0, radius_px=20, rearm_px=50)
        fired = [d.update(t / 10, 500 + (t % 3), 300).fired for t in range(12)]
        self.assertEqual(fired.count(True), 1)  # un clic après ~1 s, malgré de petits tremblements
        self.assertFalse(any(d.update(2 + t / 10, 500, 300).fired for t in range(30)))  # pas de rafale
        d.update(5.0, 600, 300)  # on s'éloigne...
        self.assertTrue(any(d.update(5.1 + t / 10, 600, 300).fired for t in range(15)))  # ...puis reclic

    def test_dwell_progress_resets_when_moving(self):
        d = DwellClicker(seconds=1.0, radius_px=20)
        d.update(0, 100, 100)
        self.assertAlmostEqual(d.update(0.5, 100, 100).progress, 0.5)
        self.assertEqual(d.update(0.6, 200, 100).progress, 0.0)


    def test_no_dwell_click_right_after_a_click(self):
        d = DwellClicker(seconds=1.0, radius_px=20, rearm_px=50)
        d.hold(500, 300)  # clic par clignement à cet endroit
        self.assertFalse(any(d.update(t / 10, 500, 300).fired for t in range(40)))

    def test_dwell_repeats_on_keyboard(self):
        d = DwellClicker(seconds=1.0, radius_px=20, rearm_px=50)
        fired = [d.update(t / 10, 500, 300, repeat=True).fired for t in range(33)]
        self.assertEqual(fired.count(True), 3)  # « lll » : une lettre par seconde, sans bouger


class KeyboardLayoutTests(unittest.TestCase):
    def test_rows_fill_the_width(self):
        for mode, rows in LAYOUTS.items():
            for row in rows:
                self.assertAlmostEqual(sum(k.width for k in row), UNITS_WIDE, msg=mode)

    def test_hit_and_shift(self):
        placed = place("abc", unit=80, row_h=64, gap=6, left=10, top=40)
        a = hit(placed, 10 + 30, 40 + 30)
        self.assertEqual(a.key.label, "a")
        self.assertEqual(typed_char(a.key, shift=True), "A")
        self.assertEqual(typed_char(hit(placed, 10 + 6.0 * 80, 40 + 2 * 70 + 30).key, shift=True), "B")
        self.assertIsNone(hit(placed, 5, 5))  # bandeau du titre : pas une touche
        enter = [p for p in placed if p.key.label == "Entrée"][0]
        self.assertEqual(enter.key.value, VK_RETURN)


class GestureTests(unittest.TestCase):
    def test_natural_blink_does_not_click(self):
        g = GestureDetector()
        events = feed(g, 0, 1, OPEN) + feed(g, 1, 0.15, CLOSED) + feed(g, 1.15, 1, OPEN)
        self.assertNotIn("click_left", events)

    def test_long_blink_clicks_once(self):
        g = GestureDetector()
        events = feed(g, 0, 1, OPEN) + feed(g, 1, 0.6, CLOSED) + feed(g, 1.6, 0.5, OPEN)
        self.assertEqual(events.count("click_left"), 1)

    def test_eyes_closed_long_toggles_pause_without_click(self):
        g = GestureDetector()
        events = feed(g, 0, 3.0, CLOSED) + feed(g, 3, 0.5, OPEN)
        self.assertEqual(events, ["toggle_pause"])

    def test_brows_right_click_once_per_raise(self):
        g = GestureDetector()
        events = feed(g, 0, 2, BROWS) + feed(g, 2, 0.5, OPEN) + feed(g, 2.5, 1, BROWS)
        self.assertEqual(events.count("click_right"), 2)

    def test_mouth_scroll_mode(self):
        g = GestureDetector()
        events = feed(g, 0, 1, MOUTH) + feed(g, 1, 0.5, OPEN)
        self.assertEqual(events, ["scroll_on", "scroll_off"])

    def test_disabled_gestures(self):
        g = GestureDetector(GestureSettings(blink_click=False, brow_right_click=False, mouth_scroll=False))
        events = feed(g, 0, 0.6, CLOSED) + feed(g, 0.6, 1, OPEN) + feed(g, 2, 1, BROWS) + feed(g, 3, 1, MOUTH)
        self.assertEqual(events, [])

    def test_lost_face_cancels_gestures(self):
        g = GestureDetector()
        feed(g, 0, 0.3, CLOSED)
        g.update(0.4, None)
        events = feed(g, 0.5, 0.5, OPEN)
        self.assertNotIn("click_left", events)


class ConfigTests(unittest.TestCase):
    def test_update_validates_types(self):
        c = Config()
        self.assertEqual(c.update({"dwell_seconds": "1.5", "voice": False, "inconnu": 3}), ["dwell_seconds", "voice"])
        self.assertEqual(c.update({"sensitivity_x": "abc"}), [])


if __name__ == "__main__":
    unittest.main()
