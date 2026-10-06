"""Drawing, footage and easing helpers shared by every scene.

Frames are numpy uint8 arrays (H, W, 3) in RGB order.
"""
import json
import os
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 30
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
FOOTAGE = os.environ.get("FOOTAGE", os.path.join(ROOT, "footage"))

BG = (9, 10, 13)
AMBER = (255, 186, 64)
CYAN = (96, 205, 255)
RED = (255, 72, 66)
GREEN = (96, 230, 140)
WHITE = (238, 238, 232)
GREY = (138, 143, 150)
DARK = (22, 24, 29)
INK = (40, 36, 32)
PAPER = (229, 222, 203)

FONT_FILES = {
    "display": "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf",
    "display_light": "/usr/share/fonts/opentype/inter/InterDisplay-Light.otf",
    "black": "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf",
    "xbold": "/usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf",
    "sans": "/usr/share/fonts/opentype/inter/Inter-Medium.otf",
    "mono": os.path.join(ROOT, "assets/fonts/IBMPlexMono-Medium.ttf"),
    "mono_bold": os.path.join(ROOT, "assets/fonts/IBMPlexMono-SemiBold.ttf"),
    "type": os.path.join(ROOT, "assets/fonts/SpecialElite-Regular.ttf"),
    "tw": os.path.join(ROOT, "assets/fonts/SpecialElite-Regular.ttf"),
    "cp": os.path.join(ROOT, "assets/fonts/CourierPrime-Regular.ttf"),
    "cp_bold": os.path.join(ROOT, "assets/fonts/CourierPrime-Bold.ttf"),
}


# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lin(t, t0, t1):
    return clamp((t - t0) / (t1 - t0)) if t1 != t0 else float(t >= t1)


def smooth(u):
    u = clamp(u)
    return u * u * u * (u * (u * 6 - 15) + 10)


def ease_out(u):
    u = clamp(u)
    return 1 - (1 - u) ** 3


def ease_in(u):
    u = clamp(u)
    return u ** 3


def lerp(a, b, u):
    return a + (b - a) * u


def window(t, t0, t1, fade=0.25):
    """1 inside [t0, t1], ramps over `fade` seconds on both sides."""
    return clamp(min((t - t0) / fade + 1, (t1 - t) / fade + 1))


def mix(c1, c2, u):
    return tuple(int(lerp(a, b, u)) for a, b in zip(c1, c2))


# ---------------------------------------------------------------- text
@lru_cache(maxsize=None)
def font(name, size):
    return ImageFont.truetype(FONT_FILES[name], size)


@lru_cache(maxsize=30000)
def text_rgba(s, name, size, color, tracking=0):
    f = font(name, size)
    asc, desc = f.getmetrics()
    if tracking:
        width = sum(f.getlength(ch) for ch in s) + tracking * max(len(s) - 1, 0)
    else:
        width = f.getlength(s)
    img = Image.new("RGBA", (int(width) + 6, asc + desc + 4), color + (0,))
    d = ImageDraw.Draw(img)
    if tracking:
        x = 2
        for ch in s:
            d.text((x, 2), ch, font=f, fill=color + (255,))
            x += f.getlength(ch) + tracking
    else:
        d.text((2, 2), s, font=f, fill=color + (255,))
    return np.array(img)


def blit(frame, rgba, x, y, alpha=1.0, clip=None):
    """Alpha-composite an RGBA image onto the frame at integer (x, y)."""
    if alpha <= 0.003:
        return
    h, w = rgba.shape[:2]
    fx0, fy0, fx1, fy1 = clip if clip else (0, 0, frame.shape[1], frame.shape[0])
    fx0, fy0 = max(fx0, 0), max(fy0, 0)
    fx1, fy1 = min(fx1, frame.shape[1]), min(fy1, frame.shape[0])
    x0, y0 = max(int(x), fx0), max(int(y), fy0)
    x1, y1 = min(int(x) + w, fx1), min(int(y) + h, fy1)
    if x1 <= x0 or y1 <= y0:
        return
    src = rgba[y0 - int(y): y1 - int(y), x0 - int(x): x1 - int(x)]
    a = src[..., 3:4].astype(np.float32) * (alpha / 255.0)
    dst = frame[y0:y1, x0:x1].astype(np.float32)
    frame[y0:y1, x0:x1] = (dst + (src[..., :3] - dst) * a).astype(np.uint8)


def text(frame, s, x, y, name="sans", size=32, color=WHITE, alpha=1.0, anchor="lt",
         tracking=0, clip=None):
    """Draw text; anchor is horizontal (l/c/r) + vertical (t/m/b). Returns (w, h)."""
    if not s:
        return 0, 0
    img = text_rgba(s, name, int(size), tuple(color), int(tracking))
    h, w = img.shape[:2]
    if anchor[0] == "c":
        x -= w / 2
    elif anchor[0] == "r":
        x -= w
    if anchor[1] == "m":
        y -= h / 2
    elif anchor[1] == "b":
        y -= h
    blit(frame, img, round(x), round(y), alpha, clip)
    return w, h


def text_width(s, name, size, tracking=0):
    return text_rgba(s, name, int(size), (255, 255, 255), int(tracking)).shape[1]


# ---------------------------------------------------------------- shapes
def fill_rect(frame, x0, y0, x1, y1, color, alpha=1.0):
    x0, y0 = max(int(x0), 0), max(int(y0), 0)
    x1, y1 = min(int(x1), frame.shape[1]), min(int(y1), frame.shape[0])
    if x1 <= x0 or y1 <= y0 or alpha <= 0:
        return
    roi = frame[y0:y1, x0:x1]
    if alpha >= 1:
        roi[:] = color
    else:
        roi[:] = (roi * (1 - alpha) + np.array(color, np.float32) * alpha).astype(np.uint8)


def overlay(frame, alpha, draw, bbox=None):
    """Run draw(canvas, ox, oy) on a copy of the frame (or of bbox only), then
    blend it back at alpha. Drawing code must subtract (ox, oy) from coordinates."""
    if alpha <= 0.003:
        return
    if bbox is None:
        x0, y0, x1, y1 = 0, 0, frame.shape[1], frame.shape[0]
    else:
        x0, y0 = max(int(bbox[0]), 0), max(int(bbox[1]), 0)
        x1, y1 = min(int(bbox[2]) + 1, frame.shape[1]), min(int(bbox[3]) + 1, frame.shape[0])
        if x1 <= x0 or y1 <= y0:
            return
    roi = frame[y0:y1, x0:x1]
    ov = roi.copy()
    draw(ov, x0, y0)
    if alpha >= 0.997:
        roi[:] = ov
    else:
        cv2.addWeighted(ov, alpha, roi, 1 - alpha, 0, dst=roi)


def line(frame, p0, p1, color, thick=2):
    cv2.line(frame, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), color, thick, cv2.LINE_AA)


def dashed(frame, p0, p1, color, thick=2, dash=14, gap=10, upto=1.0):
    p0, p1 = np.array(p0, float), np.array(p1, float)
    length = np.linalg.norm(p1 - p0) * upto
    if length < 1:
        return
    d = (p1 - p0) / np.linalg.norm(p1 - p0)
    s = 0.0
    while s < length:
        e = min(s + dash, length)
        line(frame, p0 + d * s, p0 + d * e, color, thick)
        s += dash + gap


def brackets(frame, x0, y0, x1, y1, color, arm=None, thick=3):
    arm = arm or max(10, min(x1 - x0, y1 - y0) * 0.2)
    for (cx, cy, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        line(frame, (cx, cy), (cx + dx * arm, cy), color, thick)
        line(frame, (cx, cy), (cx, cy + dy * arm), color, thick)


def chip(frame, s, x, y, color, size=20, fg=BG, alpha=1.0, anchor="lb", pad=6, name="mono_bold"):
    """A filled label chip (like a detector's class label)."""
    img = text_rgba(s, name, int(size), tuple(fg), 0)
    h, w = img.shape[:2]
    cw, ch = w + 2 * pad - 4, h + pad - 2
    if anchor[0] == "r":
        x -= cw
    elif anchor[0] == "c":
        x -= cw / 2
    if anchor[1] == "b":
        y -= ch
    elif anchor[1] == "m":
        y -= ch / 2
    fill_rect(frame, x, y, x + cw, y + ch, color, 0.92 * alpha)
    blit(frame, img, round(x + pad - 2), round(y + pad / 2 - 2), alpha)
    return cw, ch


def det_box(frame, box, label, color, appear=1.0, alpha=1.0, size=20, thick=2):
    """Detector-style box: thin frame, heavy corners, label chip. appear 0→1 animates in."""
    if appear <= 0 or alpha <= 0:
        return
    x0, y0, x1, y1 = box
    k = 1 + 0.25 * (1 - ease_out(appear))
    cx, cy, hw, hh = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 * k, (y1 - y0) / 2 * k
    x0, y0, x1, y1 = cx - hw, cy - hh, cx + hw, cy + hh
    a = alpha * clamp(appear * 1.5)

    def draw(ov, ox, oy):
        cv2.rectangle(ov, (int(x0 - ox), int(y0 - oy)), (int(x1 - ox), int(y1 - oy)), color, 1,
                      cv2.LINE_AA)
        brackets(ov, x0 - ox, y0 - oy, x1 - ox, y1 - oy, color, thick=thick + 1)

    overlay(frame, a, draw, (x0 - 4, y0 - 4, x1 + 4, y1 + 4))
    if label and appear > 0.5:
        if y0 < size * 1.8:   # no room above the box: hang the label below it
            chip(frame, label, x0 - 1, y1 + 3, color, size=size, alpha=a, anchor="lt")
        else:
            chip(frame, label, x0 - 1, y0 - 2, color, size=size, alpha=a)


# ---------------------------------------------------------------- footage
class Clip:
    """Sequential frame access to a video file by timestamp (seconds)."""

    def __init__(self, name):
        self.path = os.path.join(FOOTAGE, name + ".mp4")
        self.name = name
        self._open()

    def _open(self):
        self.cap = cv2.VideoCapture(self.path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.idx, self.img = -1, None

    def frame(self, idx):
        idx = max(int(idx), 0)
        if idx < self.idx:
            self._open()
        moved = False
        while self.idx < idx:
            if not self.cap.grab():
                break
            self.idx += 1
            moved = True
        if moved or self.img is None:
            ok, img = self.cap.retrieve()
            if ok:
                self.img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return self.img

    def at(self, t):
        idx = int(t * self.fps + 1e-6)
        return self.frame(idx), min(idx, self.idx)


class Dets:
    """Cached detections for a clip, with a little temporal smoothing."""

    def __init__(self, name, kind="obj"):
        path = os.path.join(BUILD, "detections", f"{name}.{kind}.json")
        with open(path) as f:
            d = json.load(f)
        self.fps, self.frames = d["fps"], d["frames"]

    def get(self, idx, classes=None, min_score=0.45, hold=2):
        out = []
        for k in range(idx, max(idx - hold, 0) - 1, -1):
            if k >= len(self.frames):
                continue
            for d in self.frames[k]:
                if d[4] < min_score or (classes is not None and int(d[5]) not in classes):
                    continue
                if all(iou(d, o) < 0.35 or int(o[5]) != int(d[5]) for o in out):
                    out.append(d)
        return out


def iou(a, b):
    ax1, ay1, bx1, by1 = a[0] + a[2], a[1] + a[3], b[0] + b[2], b[1] + b[3]
    iw = max(0.0, min(ax1, bx1) - max(a[0], b[0]))
    ih = max(0.0, min(ay1, by1) - max(a[1], b[1]))
    inter = iw * ih
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union > 0 else 0.0


# ---------------------------------------------------------------- framing
class View:
    """Maps a source image into a screen rectangle (cover-fit, zoom, pan)."""

    def __init__(self, src_w, src_h, rect=(0, 0, W, H), zoom=1.0, center=None):
        x, y, w, h = rect
        self.rect = rect
        self.s = max(w / src_w, h / src_h) * zoom
        cw, ch = w / self.s, h / self.s
        cx, cy = center if center is not None else (src_w / 2, src_h / 2)
        self.x0 = clamp(cx - cw / 2, 0, max(src_w - cw, 0))
        self.y0 = clamp(cy - ch / 2, 0, max(src_h - ch, 0))

    def render(self, img, interp=cv2.INTER_LINEAR):
        x, y, w, h = self.rect
        m = np.float32([[self.s, 0, -self.x0 * self.s], [0, self.s, -self.y0 * self.s]])
        return cv2.warpAffine(img, m, (int(w), int(h)), flags=interp, borderMode=cv2.BORDER_REPLICATE)

    def pt(self, px, py):
        x, y, _, _ = self.rect
        return x + (px - self.x0) * self.s, y + (py - self.y0) * self.s

    def box(self, d):
        x0, y0 = self.pt(d[0], d[1])
        x1, y1 = self.pt(d[0] + d[2], d[1] + d[3])
        return x0, y0, x1, y1


def paste(frame, img, x, y):
    h, w = img.shape[:2]
    x0, y0 = max(int(x), 0), max(int(y), 0)
    x1, y1 = min(int(x) + w, frame.shape[1]), min(int(y) + h, frame.shape[0])
    if x1 > x0 and y1 > y0:
        frame[y0:y1, x0:x1] = img[y0 - int(y): y1 - int(y), x0 - int(x): x1 - int(x)]


_CURVE = np.clip(255 * (0.5 + 0.5 * np.tanh(1.25 * (np.arange(256) / 255 - 0.5) * 2) /
                         np.tanh(1.25)), 0, 255).astype(np.uint8)


def grade(img, sat=0.85, bright=1.0, cool=0.0, warm=0.0):
    """Gentle filmic grade: S-curve contrast, saturation, brightness and tint."""
    out = cv2.LUT(img, _CURVE)
    if sat != 1.0:
        g = cv2.cvtColor(cv2.cvtColor(out, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB)
        out = cv2.addWeighted(out, sat, g, 1 - sat, 0)
    if cool or warm:
        shift = np.array([warm * 14 - cool * 10, warm * 4, cool * 16 - warm * 10], np.float32)
        out = np.clip(out.astype(np.float32) + shift, 0, 255).astype(np.uint8)
    if bright != 1.0:
        out = cv2.convertScaleAbs(out, alpha=bright)
    return out


def darken(frame, k):
    if k < 1:
        cv2.convertScaleAbs(frame, dst=frame, alpha=max(k, 0))
    return frame


def canvas(color=BG):
    f = np.empty((H, W, 3), np.uint8)
    f[:] = color
    return f


# ---------------------------------------------------------------- finishing
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / (W / 2)) ** 2 + ((_yy - H / 2) / (H / 2)) ** 2)
VIGNETTE = np.repeat((np.clip(1.0 - 0.28 * np.clip(_r - 0.45, 0, None) ** 1.6, 0, 1) * 255)
                     .astype(np.uint8)[..., None], 3, axis=2)
_rng = np.random.default_rng(7)
GRAIN = []
for _ in range(6):
    n = _rng.normal(0, 2.2, (H // 2, W // 2, 1)).astype(np.float32)
    n = cv2.resize(n, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    n = np.repeat(n, 3, axis=2)
    GRAIN.append((np.clip(n, 0, 255).astype(np.uint8), np.clip(-n, 0, 255).astype(np.uint8)))
del _yy, _xx, _r


def finish(frame, i):
    cv2.multiply(frame, VIGNETTE, dst=frame, scale=1 / 255)
    pos, neg = GRAIN[i % len(GRAIN)]
    cv2.add(frame, pos, dst=frame)
    cv2.subtract(frame, neg, dst=frame)
    return frame
