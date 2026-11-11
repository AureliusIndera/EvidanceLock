import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np

from auth.biometric import FaceEngine

WINDOW = "kalibrasi"
AVG = 5


def show(frame, text):
    cv2.putText(frame, text, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.imshow(WINDOW, frame)


def wait_space(cap, face, text):
    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        frame = cv2.flip(frame, 1)
        box = face.detect(frame)
        if box:
            x, y, w, h = box
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 220, 0), 2)
        show(frame, text)
        key = cv2.waitKey(30) & 0xFF
        if key == 32:
            return True
        if key == 27:
            return False


def record(cap, face, n, text):
    vecs = []
    while len(vecs) < n:
        ok, frame = cap.read()
        if not ok:
            continue
        frame = cv2.flip(frame, 1)
        box = face.detect(frame)
        if box:
            vecs.append(face.encode(frame, box))
            x, y, w, h = box
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 220, 0), 2)
        show(frame, f"{text} {len(vecs)}/{n}")
        if cv2.waitKey(30) & 0xFF == 27:
            break
    return vecs


def window_scores(template, vecs):
    return [FaceEngine.similarity(template, FaceEngine.average(vecs[i:i + AVG]))
            for i in range(0, len(vecs) - AVG + 1)]


def stats(name, s):
    print(f"{name:<9} min={min(s):.3f}  rata2={np.mean(s):.3f}  maks={max(s):.3f}  (n={len(s)})")


def main():
    face, cap = FaceEngine(), cv2.VideoCapture(0)
    if not wait_space(cap, face, "1. Template: hadap lurus, SPASI mulai"):
        return
    template = FaceEngine.average(record(cap, face, 30, "Merekam template"))
    if not wait_space(cap, face, "2. Genuine: gerakkan kepala/cahaya, SPASI mulai"):
        return
    genuine = window_scores(template, record(cap, face, 60, "Merekam genuine"))
    impostor = []
    if wait_space(cap, face, "3. Impostor: orang LAIN, SPASI mulai (ESC lewati)"):
        impostor = window_scores(template, record(cap, face, 60, "Merekam impostor"))
    cap.release()
    cv2.destroyAllWindows()

    print()
    stats("GENUINE", genuine)
    if impostor:
        stats("IMPOSTOR", impostor)
        if min(genuine) > max(impostor):
            print(f"\nTerpisah. Rekomendasi FACE_THRESHOLD = {(min(genuine) + max(impostor)) / 2:.2f}")
        else:
            print("\nTumpang tindih: ambang tidak bisa memisahkan. Ganti metode pengenal wajah.")
    else:
        print(f"\nTanpa data impostor. Ambang aman harus di bawah {min(genuine):.2f} dan di atas skor orang lain.")


if __name__ == "__main__":
    main()
