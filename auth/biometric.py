import base64

import cv2
import numpy as np

from config import FACE_SIZE

_OFFSETS = [(-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1)]
_GRID = 4


def lbp_histogram(gray: np.ndarray) -> np.ndarray:
    """Local Binary Pattern 8-neighbour, histogram 256-bin per sel pada grid 4x4 -> vektor 4096-d."""
    g = gray.astype(np.int16)
    h, w = g.shape
    center = g[1:-1, 1:-1]
    code = np.zeros(center.shape, dtype=np.uint8)
    for k, (dy, dx) in enumerate(_OFFSETS):
        neighbour = g[1 + dy:h - 1 + dy, 1 + dx:w - 1 + dx]
        code |= (neighbour >= center).astype(np.uint8) << k
    ch, cw = code.shape[0] // _GRID, code.shape[1] // _GRID
    feats = []
    for i in range(_GRID):
        for j in range(_GRID):
            cell = code[i * ch:(i + 1) * ch, j * cw:(j + 1) * cw]
            hist = np.bincount(cell.ravel(), minlength=256).astype(np.float32)
            feats.append(hist / max(hist.sum(), 1.0))
    return np.concatenate(feats)


class FaceEngine:
    def __init__(self):
        if not hasattr(cv2, "CascadeClassifier"):
            raise RuntimeError('OpenCV 5.x tidak menyertakan CascadeClassifier. Jalankan: pip install "opencv-python>=4.9,<5"')
        self.cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        if self.cascade.empty():
            raise RuntimeError("Haar cascade wajah tidak ditemukan")

    def detect(self, frame_bgr):
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        faces = self.cascade.detectMultiScale(gray, 1.2, 5, minSize=(90, 90))
        if len(faces) == 0:
            return None
        return tuple(int(v) for v in max(faces, key=lambda f: f[2] * f[3]))

    def encode(self, frame_bgr, box) -> np.ndarray:
        x, y, w, h = box
        x0, y0 = x + int(0.15 * w), y + int(0.10 * h)
        x1, y1 = x + int(0.85 * w), y + int(0.95 * h)
        gray = cv2.cvtColor(frame_bgr[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
        return self.vector_from_gray(gray)

    @staticmethod
    def vector_from_gray(gray: np.ndarray) -> np.ndarray:
        face = cv2.equalizeHist(cv2.resize(gray, (FACE_SIZE, FACE_SIZE)))
        return lbp_histogram(face)

    @staticmethod
    def average(vectors) -> np.ndarray:
        return np.mean(vectors, axis=0).astype(np.float32)

    @staticmethod
    def similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Histogram intersection rata-rata antar sel (0..1)."""
        return float(np.minimum(a.reshape(-1, 256), b.reshape(-1, 256)).sum(axis=1).mean())


def encode_vector(vec: np.ndarray) -> str:
    return base64.b64encode(vec.astype(np.float32).tobytes()).decode("ascii")


def decode_vector(text: str) -> np.ndarray:
    return np.frombuffer(base64.b64decode(text), dtype=np.float32)
