"""Contact sheet of a video: one frame every N seconds, labelled with its time."""
import sys

import cv2
import numpy as np


def sheet(path, out, every=2.0, cols=6, w=300):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    tiles = []
    t = 0.5
    while t * fps < n - 1:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
        ok, im = cap.read()
        if not ok:
            break
        h = int(im.shape[0] * w / im.shape[1])
        im = cv2.resize(im, (w, h))
        cv2.putText(im, f"{t:.1f}", (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 230, 255), 2)
        tiles.append(im)
        t += every
    hmax = max(x.shape[0] for x in tiles)
    tiles = [cv2.copyMakeBorder(x, 0, hmax - x.shape[0], 0, 0, cv2.BORDER_CONSTANT) for x in tiles]
    while len(tiles) % cols:
        tiles.append(np.zeros_like(tiles[0]))
    grid = np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)])
    cv2.imwrite(out, grid, [cv2.IMWRITE_JPEG_QUALITY, 70])
    print(out, len(tiles), "frames")


if __name__ == "__main__":
    sheet(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 2.0,
          int(sys.argv[4]) if len(sys.argv) > 4 else 6)
