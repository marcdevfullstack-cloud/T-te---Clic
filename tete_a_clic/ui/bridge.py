"""Pont moteur → interface : flux vidéo local (MJPEG, 127.0.0.1 + jeton) et état."""
import secrets
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2

VIDEO_WIDTH = 480
VIDEO_FPS = 15


class _StreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        bridge = self.server.bridge
        if self.path != f"/stream?k={bridge.token}":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        last = -1
        try:
            while not bridge.closed:
                jpeg, seq = bridge.wait_frame(last, 1.0)
                if jpeg is None or seq == last:
                    continue
                last = seq
                self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                                 + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n")
        except OSError:
            return

    def log_message(self, *args):
        pass


class Bridge:
    def __init__(self):
        self.token = secrets.token_urlsafe(16)
        self.closed = False
        self._cond = threading.Condition()
        self._jpeg: bytes | None = None
        self._seq = 0
        self._encoded_at = 0.0
        self._state: dict = {}
        self._speech: deque = deque(maxlen=5)
        self._log: deque = deque(maxlen=6)
        self._next_id = 0
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _StreamHandler)
        self._server.daemon_threads = True
        self._server.bridge = self
        threading.Thread(target=self._server.serve_forever, name="video", daemon=True).start()
        self.video_url = f"http://127.0.0.1:{self._server.server_address[1]}/stream?k={self.token}"

    def publish_frame(self, frame_bgr):
        now = time.monotonic()
        if now - self._encoded_at < 1 / VIDEO_FPS:
            return
        self._encoded_at = now
        h, w = frame_bgr.shape[:2]
        if w > VIDEO_WIDTH:
            frame_bgr = cv2.resize(frame_bgr, (VIDEO_WIDTH, int(h * VIDEO_WIDTH / w)), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 75])
        if ok:
            with self._cond:
                self._jpeg, self._seq = buf.tobytes(), self._seq + 1
                self._cond.notify_all()

    def wait_frame(self, last_seq: int, timeout: float):
        with self._cond:
            if self._seq == last_seq:
                self._cond.wait(timeout)
            return self._jpeg, self._seq

    def publish_state(self, state: dict):
        self._state = state

    def speak(self, text: str):
        self._next_id += 1
        self._speech.append({"id": self._next_id, "text": text})

    def log(self, text: str, tone: str = "accent"):
        self._next_id += 1
        self._log.appendleft({"id": self._next_id, "text": text, "tone": tone, "time": time.strftime("%H:%M:%S")})

    def snapshot(self) -> dict:
        return {**self._state, "videoUrl": self.video_url, "speech": list(self._speech), "log": list(self._log)}

    def close(self):
        self.closed = True
        with self._cond:
            self._cond.notify_all()
        self._server.shutdown()
        self._server.server_close()
