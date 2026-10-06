"""Cut labeled example images out of the footage using the cached detections.

These real crops feed the "learning from examples" and dataset animations.
Writes build/crops/<label>_<n>.png (square, 160 px) and build/crops/index.json.
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from detect import COCO  # noqa: E402
from fx import BUILD, FOOTAGE  # noqa: E402

WANT = {0: 14, 1: 8, 2: 10, 39: 4, 45: 5, 41: 2, 47: 3, 49: 3, 46: 2, 50: 2}
CLIPS = ["person-bicycle-car-detection", "car-detection", "store-aisle-detection",
         "worker-zone-detection", "people-detection", "one-by-one-person-detection",
         "fruit-and-vegetable-detection", "bottle-detection"]
SIZE = 160


def main():
    out = os.path.join(BUILD, "crops")
    os.makedirs(out, exist_ok=True)
    picks = []   # (clip, frame, det)
    for name in CLIPS:
        path = os.path.join(BUILD, "detections", f"{name}.obj.json")
        if not os.path.exists(path):
            print("skip", name)
            continue
        with open(path) as f:
            frames = json.load(f)["frames"]
        last = {}
        for i, dets in enumerate(frames):
            for d in dets:
                c = int(d[5])
                if c not in WANT or d[4] < 0.6 or min(d[2], d[3]) < 24:
                    continue
                if i - last.get(c, -10 ** 6) < 40:   # spread picks across the clip
                    continue
                last[c] = i
                picks.append((name, i, d))
    by_class = {}
    for p in picks:
        by_class.setdefault(int(p[2][5]), []).append(p)
    rng = np.random.default_rng(1)
    chosen = []
    for c, n in WANT.items():
        items = by_class.get(c, [])
        if len(items) > n:
            items = [items[k] for k in sorted(rng.choice(len(items), n, replace=False))]
        chosen += items
    index = []
    for name in sorted({p[0] for p in chosen}):
        cap = cv2.VideoCapture(os.path.join(FOOTAGE, name + ".mp4"))
        want = sorted((p for p in chosen if p[0] == name), key=lambda p: p[1])
        idx, img = -1, None
        for _, fi, d in want:
            while idx < fi:
                ok, img = cap.read()
                idx += 1
            h, w = img.shape[:2]
            cx, cy, side = d[0] + d[2] / 2, d[1] + d[3] / 2, max(d[2], d[3]) * 1.15
            x0, y0 = int(max(cx - side / 2, 0)), int(max(cy - side / 2, 0))
            x1, y1 = int(min(cx + side / 2, w)), int(min(cy + side / 2, h))
            crop = cv2.resize(img[y0:y1, x0:x1], (SIZE, SIZE), interpolation=cv2.INTER_AREA)
            label = COCO[int(d[5])]
            fn = f"{label.replace(' ', '_')}_{len(index):03d}.png"
            cv2.imwrite(os.path.join(out, fn), crop)
            index.append({"file": fn, "label": label})
    with open(os.path.join(out, "index.json"), "w") as f:
        json.dump(index, f, indent=1)
    counts = {}
    for it in index:
        counts[it["label"]] = counts.get(it["label"], 0) + 1
    print(len(index), "crops", counts)


if __name__ == "__main__":
    main()
