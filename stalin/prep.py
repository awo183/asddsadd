"""Prepare derived assets: background-removed cutouts of people and the monument,
and generated graphics (a grey silhouette)."""
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fetch  # noqa: E402
import vox as V  # noqa: E402
from extras import person  # noqa: E402

IMG = os.path.join(V.BUILD, "assets", "img")
PEOPLE = ["svec_portrait", "lukes_portrait", "klimes_portrait", "zabransky_portrait", "stalin_portrait"]
# (Hasil holds a book and Khrushchev a glass in their photos: those stay as prints, not cutouts)
OBJECTS = {"monument_side": "isnet-general-use", "monument_full_a": "isnet-general-use"}


def silhouette():
    path = os.path.join(IMG, "silhouette.png")
    if os.path.exists(path):
        return
    f = np.zeros((700, 400, 3), np.uint8)
    person(f, 200, 690, 660, (255, 255, 255), 1.0)
    a = f[..., 0]
    out = np.zeros((700, 400, 4), np.uint8)
    out[..., :3] = (120, 114, 104)
    out[..., 3] = (a * 0.85).astype(np.uint8)
    cv2.imwrite(path, cv2.cvtColor(out, cv2.COLOR_RGBA2BGRA))


def main():
    silhouette()
    for n in PEOPLE:
        src = os.path.join(IMG, f"{n}.jpg")
        if os.path.exists(src):
            fetch.cutout(src, os.path.join(IMG, f"{n}_cut.png"), "u2net_human_seg")
            print("cutout", n)
    for n, model in OBJECTS.items():
        src = os.path.join(IMG, f"{n}.jpg")
        if os.path.exists(src):
            fetch.cutout(src, os.path.join(IMG, f"{n}_cut.png"), model)


if __name__ == "__main__":
    main()
