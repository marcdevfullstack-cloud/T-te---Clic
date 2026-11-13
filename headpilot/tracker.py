"""Suivi du visage avec MediaPipe Face Landmarker : orientation de la tête et gestes."""
import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

from .gestures import FaceSignals

NOSE_TIP = 1
EYE_OUTER_LEFT, EYE_OUTER_RIGHT = 33, 263


@dataclass(frozen=True)
class FaceReading:
    yaw: float  # rotation gauche/droite : décalage du nez par rapport au milieu des yeux
    pitch: float  # rotation haut/bas
    signals: FaceSignals
    nose: tuple[float, float]  # en pixels, pour l'affichage
    eyes: tuple[tuple[float, float], tuple[float, float]]


class FaceTracker:
    def __init__(self, model_path: Path):
        self._landmarker = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
            output_face_blendshapes=True,
        ))

    def process(self, frame_bgr, timestamp_ms: int) -> FaceReading | None:
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        if not result.face_landmarks:
            return None
        lms = result.face_landmarks[0]
        h, w = frame_bgr.shape[:2]
        px = lambda i: (lms[i].x * w, lms[i].y * h)  # noqa: E731
        nose, left, right = px(NOSE_TIP), px(EYE_OUTER_LEFT), px(EYE_OUTER_RIGHT)
        eye_dist = math.dist(left, right)
        if eye_dist < 5:
            return None
        mid = ((left[0] + right[0]) / 2, (left[1] + right[1]) / 2)
        # Le nez se décale par rapport aux yeux quand la tête tourne, pas quand elle se déplace :
        # on suit donc la rotation, indépendamment de la position dans l'image.
        yaw = (nose[0] - mid[0]) / eye_dist
        pitch = (nose[1] - mid[1]) / eye_dist

        sc = {c.category_name: c.score for c in result.face_blendshapes[0]} if result.face_blendshapes else {}
        g = lambda name: sc.get(name, 0.0)  # noqa: E731
        signals = FaceSignals(
            blink=min(g("eyeBlinkLeft"), g("eyeBlinkRight")),  # les DEUX yeux fermés
            brow=max(g("browInnerUp"), (g("browOuterUpLeft") + g("browOuterUpRight")) / 2),
            jaw=g("jawOpen"),
        )
        return FaceReading(yaw, pitch, signals, nose, (left, right))

    def close(self):
        self._landmarker.close()
