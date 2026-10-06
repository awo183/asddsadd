"""Contact sheets of review stills: contact.py OUT.jpg img1 img2 ... (labels = file names)."""
import os
import sys

from PIL import Image, ImageDraw


def sheet(paths, out, cols=3, w=640):
    h = int(w * 1080 / 1920)
    rows = (len(paths) + cols - 1) // cols
    S = Image.new("RGB", (cols * w, rows * (h + 22)), (20, 20, 20))
    d = ImageDraw.Draw(S)
    for k, p in enumerate(paths):
        im = Image.open(p).convert("RGB").resize((w, h))
        x, y = (k % cols) * w, (k // cols) * (h + 22)
        S.paste(im, (x, y + 22))
        d.text((x + 4, y + 4), os.path.basename(p), fill=(255, 220, 0))
    S.save(out, quality=82)


if __name__ == "__main__":
    sheet(sys.argv[2:], sys.argv[1])
