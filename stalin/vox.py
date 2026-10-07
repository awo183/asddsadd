"""Vox-style collage toolkit: paper, cutouts, stamps, highlighter, hand-drawn
marks, film look. Frames are numpy uint8 arrays (H, W, 3), RGB.

Everything is drawn with numpy/OpenCV/PIL so it renders the same on any machine.
"""
import math
import os
import zlib
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 30
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(ROOT, "build", "stalin")
FONT_DIR = os.path.join(ROOT, "assets", "fonts")

# palette (style guide section 5)
PAPER = (233, 225, 206)
PAPER_DARK = (207, 196, 170)
AGED = (222, 208, 172)
INK = (24, 22, 20)
RED = (215, 38, 46)
HILITE = (255, 216, 58)
WHITE = (244, 242, 236)
GREY = (150, 146, 138)
BLACK = (10, 10, 10)

FONTS = {
    "anton": ("Anton-Regular.ttf", None),
    "bebas": ("BebasNeue-Regular.ttf", None),
    "oswald": ("Oswald[wght].ttf", 700),
    "mont": ("Montserrat[wght].ttf", 800),
    "mont_med": ("Montserrat[wght].ttf", 600),
    "caveat": ("Caveat[wght].ttf", 700),
    "play": ("PlayfairDisplay[wght].ttf", 900),
    "play_reg": ("PlayfairDisplay[wght].ttf", 500),
    "cp": ("CourierPrime-Regular.ttf", None),
    "cp_bold": ("CourierPrime-Bold.ttf", None),
    "type": ("SpecialElite-Regular.ttf", None),
    "bangers": ("Bangers-Regular.ttf", None),
    "monoton": ("Monoton-Regular.ttf", None),
    "mont_black": ("Montserrat[wght].ttf", 900),
    "mont_light": ("Montserrat[wght].ttf", 300),
}


# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lin(t, t0, t1):
    return clamp((t - t0) / (t1 - t0)) if t1 != t0 else float(t >= t1)


def lerp(a, b, u):
    return a + (b - a) * u


def ease_out(u):
    u = clamp(u)
    return 1 - (1 - u) ** 3


def ease_in(u):
    u = clamp(u)
    return u ** 3


def ease_io(u):
    u = clamp(u)
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


def ease_out_expo(u):
    u = clamp(u)
    return 1.0 if u >= 1 else 1 - 2 ** (-10 * u)


def ease_back(u, s=1.9):
    """easeOutBack: overshoots ~6 % then settles (the 'pop')."""
    u = clamp(u)
    return 1 + (s + 1) * (u - 1) ** 3 + s * (u - 1) ** 2


def sine_io(u):
    u = clamp(u)
    return -(math.cos(math.pi * u) - 1) / 2


def seed_of(*parts):
    return zlib.crc32("|".join(str(p) for p in parts).encode())


# ---------------------------------------------------------------- text
@lru_cache(maxsize=None)
def font(name, size):
    path, wght = FONTS[name]
    f = ImageFont.truetype(os.path.join(FONT_DIR, path), int(size))
    if wght is not None:
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
    return f


@lru_cache(maxsize=20000)
def text_img(s, name, size, color=INK, tracking=0, stroke=0, stroke_color=None):
    """RGBA image of one line of text with headroom for Czech accents."""
    f = font(name, size)
    asc, desc = f.getmetrics()
    pad = int(size * 0.3) + stroke
    if tracking:
        width = sum(f.getlength(c) for c in s) + tracking * max(len(s) - 1, 0)
    else:
        width = f.getlength(s)
    img = Image.new("RGBA", (int(width) + 2 * pad + 4, asc + desc + 2 * pad), tuple(color) + (0,))
    d = ImageDraw.Draw(img)
    kw = dict(font=f, fill=tuple(color) + (255,))
    if stroke:
        kw.update(stroke_width=stroke, stroke_fill=tuple(stroke_color or BLACK) + (255,))
    if tracking:
        x = pad
        for c in s:
            d.text((x, pad), c, **kw)
            x += f.getlength(c) + tracking
    else:
        d.text((pad, pad), s, **kw)
    a = np.array(img)
    ys, xs = np.nonzero(a[..., 3])
    if len(xs) == 0:
        return a
    return a[max(ys.min() - 2, 0): ys.max() + 3, max(xs.min() - 2, 0): xs.max() + 3]


def text_w(s, name, size, tracking=0):
    return text_img(s, name, size, (255, 255, 255), tracking).shape[1]


def wrap(s, name, size, max_w):
    words, lines, cur = s.split(), [], ""
    for wd in words:
        cand = (cur + " " + wd).strip()
        if cur and text_w(cand, name, size) > max_w:
            lines.append(cur)
            cur = wd
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- textures
def _noise(h, w, cell, rng):
    small = rng.random((h // cell + 3, w // cell + 3)).astype(np.float32)
    return cv2.resize(small, (w + 3 * cell, h + 3 * cell), interpolation=cv2.INTER_CUBIC)[:h, :w]


def _cache(name, make):
    os.makedirs(os.path.join(BUILD, "tex"), exist_ok=True)
    path = os.path.join(BUILD, "tex", name + ".png")
    if os.path.exists(path):
        return cv2.cvtColor(cv2.imread(path, cv2.IMREAD_UNCHANGED), cv2.COLOR_BGR2RGB)
    img = make()
    cv2.imwrite(path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    return img


@lru_cache(maxsize=8)
def paper(w=2400, h=1400, seed=1, tone=PAPER):
    """Warm paper with blotches, fibres and soft edge darkening."""
    def make():
        rng = np.random.default_rng(seed)
        n = (_noise(h, w, 260, rng) - 0.5) * 16 + (_noise(h, w, 60, rng) - 0.5) * 9 + \
            (_noise(h, w, 7, rng) - 0.5) * 7 + rng.normal(0, 2.2, (h, w)).astype(np.float32)
        img = np.empty((h, w, 3), np.float32)
        img[:] = tone
        img += n[..., None] * np.array([1.0, 0.97, 0.9], np.float32)
        fib = np.zeros((h, w), np.float32)
        for _ in range(int(w * h / 900)):
            x, y = rng.integers(0, w), rng.integers(0, h)
            ang, ln = rng.uniform(0, math.pi), rng.uniform(6, 26)
            x2, y2 = int(x + math.cos(ang) * ln), int(y + math.sin(ang) * ln)
            cv2.line(fib, (int(x), int(y)), (x2, y2), float(rng.choice([-1, 1]) * rng.uniform(4, 9)), 1,
                     cv2.LINE_AA)
        img += cv2.GaussianBlur(fib, (0, 0), 0.6)[..., None]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        img *= (1 - 0.13 * np.clip(r - 0.55, 0, None) ** 1.5)[..., None]
        return np.clip(img, 0, 255).astype(np.uint8)
    return _cache(f"paper_{w}x{h}_{seed}_{tone[0]}", make)


@lru_cache(maxsize=64)
def grunge(h, w, seed, keep=0.82):
    """Alpha mask (0..1) with ink missing in specks and patches."""
    rng = np.random.default_rng(seed)
    n = _noise(h, w, 9, rng) * 0.55 + _noise(h, w, 3, rng) * 0.45
    return np.clip((n - (1 - keep) * 0.9) * 6, 0, 1).astype(np.float32)


# ---------------------------------------------------------------- compositing
def _shadow_src(rgba, blur):
    a = rgba[..., 3].astype(np.float32) / 255
    pad = int(blur * 2.5)
    a = cv2.copyMakeBorder(a, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
    return cv2.GaussianBlur(a, (0, 0), blur), pad


_SHADOWS = {}


def warp_into(frame, src, M, alpha=1.0, mode="normal", color=None):
    """Warp src (RGBA uint8, or float mask if color is given) by the 2x3 matrix M
    (src -> screen) and composite it onto the frame. Only the bbox is touched."""
    if alpha <= 0.003:
        return
    h, w = src.shape[:2]
    corners = np.array([[0, 0, 1], [w, 0, 1], [0, h, 1], [w, h, 1]], np.float32) @ M.T
    x0, y0 = np.floor(corners.min(0)).astype(int) - 1
    x1, y1 = np.ceil(corners.max(0)).astype(int) + 1
    fh, fw = frame.shape[:2]
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, fw), min(y1, fh)
    if x1 <= x0 or y1 <= y0:
        return
    M2 = M.copy()
    M2[:, 2] -= (x0, y0)
    flags = cv2.INTER_LINEAR
    out = cv2.warpAffine(src, M2, (x1 - x0, y1 - y0), flags=flags, borderMode=cv2.BORDER_CONSTANT,
                         borderValue=0)
    roi = frame[y0:y1, x0:x1].astype(np.float32)
    if color is not None:                       # src is a float mask
        a = out[..., None] * alpha
        res = roi + (np.array(color, np.float32) - roi) * a
    else:
        a = out[..., 3:4].astype(np.float32) * (alpha / 255)
        rgb = out[..., :3].astype(np.float32)
        if mode == "multiply":
            rgb = roi * rgb / 255
        elif mode == "screen":
            rgb = 255 - (255 - roi) * (255 - rgb) / 255
        res = roi + (rgb - roi) * a
    frame[y0:y1, x0:x1] = np.clip(res, 0, 255).astype(np.uint8)


def matrix(w, h, cx, cy, scale=1.0, rot=0.0, ax=0.5, ay=0.5):
    """Matrix placing an (w, h) image so its anchor (ax, ay) lands on (cx, cy)."""
    a = math.radians(rot)
    c, s = math.cos(a) * scale, math.sin(a) * scale
    px, py = w * ax, h * ay
    return np.float32([[c, -s, cx - (c * px - s * py)], [s, c, cy - (s * px + c * py)]])


def place(frame, rgba, cx, cy, scale=1.0, rot=0.0, alpha=1.0, shadow=True, mode="normal",
          ax=0.5, ay=0.5, shadow_k=1.0):
    """Draw an RGBA layer centred at (cx, cy) with rotation (degrees) and a soft drop shadow."""
    if alpha <= 0.003 or scale <= 0.001:
        return
    h, w = rgba.shape[:2]
    M = matrix(w, h, cx, cy, scale, rot, ax, ay)
    if shadow:
        key = (id(rgba), rgba.shape)
        blur = 14
        if key not in _SHADOWS:
            _SHADOWS[key] = _shadow_src(rgba, blur)
        sm, pad = _SHADOWS[key]
        Ms = matrix(w + 2 * pad, h + 2 * pad, cx + 4 * scale, cy + 14 * scale, scale, rot,
                    (w * ax + pad) / (w + 2 * pad), (h * ay + pad) / (h + 2 * pad))
        warp_into(frame, sm, Ms, alpha * 0.5 * shadow_k, color=(0, 0, 0))
    warp_into(frame, rgba, M, alpha, mode)


def blit(frame, rgba, x, y, alpha=1.0):
    place(frame, rgba, x, y, 1.0, 0.0, alpha, shadow=False, ax=0, ay=0)


def fill(frame, color, alpha=1.0):
    if alpha >= 1:
        frame[:] = color
    elif alpha > 0:
        frame[:] = (frame * (1 - alpha) + np.array(color, np.float32) * alpha).astype(np.uint8)


def rect(frame, x0, y0, x1, y1, color, alpha=1.0):
    x0, y0, x1, y1 = max(int(x0), 0), max(int(y0), 0), min(int(x1), frame.shape[1]), min(int(y1), frame.shape[0])
    if x1 > x0 and y1 > y0 and alpha > 0:
        roi = frame[y0:y1, x0:x1]
        roi[:] = (roi * (1 - alpha) + np.array(color, np.float32) * alpha).astype(np.uint8)


# ---------------------------------------------------------------- images
def load_rgb(path):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(path)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def load_rgba(path):
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(path)
    if img.shape[2] == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    return cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)


_CURVE = None


def bw(img, contrast=1.25, crush=0.05, tone=(1.0, 1.0, 1.0)):
    """High-contrast black and white with crushed blacks (style guide 6.1)."""
    if max(img.shape[:2]) < 2000:          # soften JPEG blocks before the contrast boost
        img = cv2.bilateralFilter(img, 5, 18, 5)
    g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    g = cv2.equalizeHist((g * 255).astype(np.uint8)).astype(np.float32) / 255 * 0.2 + g * 0.8
    g = np.clip((g - 0.5) * contrast + 0.5, 0, 1)
    g = np.clip((g - crush) / (1 - crush), 0, 1)
    g = g ** 1.05
    out = np.stack([g * tone[0], g * tone[1], g * tone[2]], -1) * 255
    return np.clip(out, 0, 255).astype(np.uint8)


def cover(img, w, h, zoom=1.0, cx=0.5, cy=0.5):
    """Cover-fit img into (w, h) with extra zoom, centred on normalized (cx, cy)."""
    ih, iw = img.shape[:2]
    s = max(w / iw, h / ih) * zoom
    vw, vh = w / s, h / s
    x0 = clamp(cx * iw - vw / 2, 0, max(iw - vw, 0))
    y0 = clamp(cy * ih - vh / 2, 0, max(ih - vh, 0))
    M = np.float32([[s, 0, -x0 * s], [0, s, -y0 * s]])
    return cv2.warpAffine(img, M, (int(w), int(h)), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def fit_long(img, long_side):
    h, w = img.shape[:2]
    s = long_side / max(h, w)
    return cv2.resize(img, (max(int(w * s), 1), max(int(h * s), 1)),
                      interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)


def card(img, long_side=900, border=18, grade=True, torn=False, seed=0, tone=WHITE):
    """Photo print with a white border (B4), optionally torn at the bottom."""
    im = fit_long(img, long_side)
    if grade:
        im = bw(im, 1.15, 0.03, (1.0, 0.99, 0.95))
    h, w = im.shape[:2]
    out = np.zeros((h + 2 * border, w + 2 * border, 4), np.uint8)
    out[..., :3] = tone
    out[..., 3] = 255
    out[border:border + h, border:border + w, :3] = im
    if torn:
        rng = np.random.default_rng(seed)
        H2, W2 = out.shape[:2]
        edge = (_noise(1, W2, 24, rng)[0] * 30 + rng.random(W2) * 6).astype(int)
        for x in range(W2):
            out[H2 - edge[x]:, x, 3] = 0
    return out


def cutout(img, mask, long_side=900, outline=12, grade=True):
    """Background-removed subject with a white sticker outline (Vox collage)."""
    ys, xs = np.nonzero(mask > 40)            # crop to the subject first so long_side means the subject
    if len(xs):
        img, mask = img[ys.min():ys.max() + 1, xs.min():xs.max() + 1], mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    im = fit_long(img, long_side)
    m = cv2.resize(mask, (im.shape[1], im.shape[0]), interpolation=cv2.INTER_LINEAR)
    if grade:
        im = bw(im, 1.15, 0.03, (1.0, 0.99, 0.95))
    pad = outline + 4
    im = cv2.copyMakeBorder(im, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
    m = cv2.copyMakeBorder(m, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
    hard = (m > 110).astype(np.uint8) * 255
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * outline + 1, 2 * outline + 1))
    ring = cv2.GaussianBlur(cv2.dilate(hard, k), (0, 0), 1.2)
    out = np.zeros(im.shape[:2] + (4,), np.uint8)
    out[..., :3] = WHITE
    a = m.astype(np.float32)[..., None] / 255
    out[..., :3] = (np.array(WHITE, np.float32) * (1 - a) + im * a).astype(np.uint8)
    out[..., 3] = np.maximum(ring, m)
    ys, xs = np.nonzero(out[..., 3] > 8)
    return out[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def stamp(word, color=RED, size=110, seed=0, border=True):
    """Red rubber stamp with a grunge mask (B2)."""
    t = text_img(word, "anton", size, color, tracking=int(size * 0.06))
    th, tw = t.shape[:2]
    p = int(size * 0.28)
    bw_ = max(int(size * 0.09), 4)
    h, w = th + 2 * p, tw + 2 * p
    out = np.zeros((h, w, 4), np.uint8)
    out[..., :3] = color
    a = np.zeros((h, w), np.float32)
    a[p:p + th, p:p + tw] = t[..., 3] / 255
    if border:
        cv2.rectangle(a, (bw_ // 2 + 2, bw_ // 2 + 2), (w - bw_ // 2 - 3, h - bw_ // 2 - 3), 1.0, bw_)
    a *= grunge(h, w, seed)
    out[..., 3] = (a * 235).astype(np.uint8)
    return out


def label_strip(name, role=None, size=54):
    """Black name strip with white caps and an optional grey role line (V9)."""
    t = text_img(name.upper(), "oswald", size, WHITE, tracking=2)
    r = text_img(role, "mont_med", int(size * 0.55), (200, 196, 188)) if role else None
    pw = 26
    w = max(t.shape[1], r.shape[1] if r is not None else 0) + 2 * pw
    h = t.shape[0] + 2 * 18 + (r.shape[0] + 10 if r is not None else 0)
    out = np.zeros((h, w, 4), np.uint8)
    out[..., :3] = (16, 16, 16)
    out[..., 3] = 245
    tmp = np.zeros((h, w, 3), np.uint8)
    tmp[:] = (16, 16, 16)
    blit(tmp, t, pw, 18)
    if r is not None:
        blit(tmp, r, pw, 18 + t.shape[0] + 10)
    out[..., :3] = tmp
    cv2.rectangle(out, (0, 0), (8, h), RED + (255,), -1)
    return out


# ---------------------------------------------------------------- hand-drawn marks
def circle_pts(cx, cy, rx, ry, seed=0, n=90, over=0.16):
    rng = np.random.default_rng(seed)
    a0 = rng.uniform(-2.4, -1.8)
    ts = np.linspace(0, 1, n)
    wob = 1 + 0.035 * np.sin(ts * 7 + rng.uniform(0, 6)) + 0.02 * np.sin(ts * 13 + rng.uniform(0, 6))
    ang = a0 + ts * (2 * math.pi * (1 + over))
    grow = 1 + 0.06 * ts
    return np.stack([cx + np.cos(ang) * rx * wob * grow, cy + np.sin(ang) * ry * wob * grow], 1)


def arrow_pts(p0, p1, seed=0, n=40, bend=0.12):
    rng = np.random.default_rng(seed)
    p0, p1 = np.array(p0, float), np.array(p1, float)
    d = p1 - p0
    nrm = np.array([-d[1], d[0]]) / (np.linalg.norm(d) + 1e-6)
    ts = np.linspace(0, 1, n)[:, None]
    b = bend * rng.choice([-1, 1]) * np.linalg.norm(d)
    return p0 + d * ts + nrm * (np.sin(ts * math.pi) * b)


def underline_pts(x0, x1, y, seed=0, n=30):
    rng = np.random.default_rng(seed)
    ts = np.linspace(0, 1, n)
    return np.stack([x0 + (x1 - x0) * ts, y + np.sin(ts * 3 + rng.uniform(0, 3)) * 4 + ts * 6], 1)


def draw_path(frame, pts, u, color=RED, thick=8, alpha=1.0, head=False):
    """Draw the first u (0..1) of a polyline like a marker stroke."""
    if u <= 0 or alpha <= 0:
        return
    n = max(int(len(pts) * clamp(u)), 2)
    p = pts[:n]
    ov = frame.copy()
    cv2.polylines(ov, [np.round(p * 4).astype(np.int32)], False, color, thick, cv2.LINE_AA, shift=2)
    cv2.polylines(ov, [np.round((p + 1.2) * 4).astype(np.int32)], False, color, max(thick - 3, 1), cv2.LINE_AA,
                  shift=2)
    if head and u >= 0.98:
        e, d = p[-1], p[-1] - p[-4]
        d = d / (np.linalg.norm(d) + 1e-6)
        for s in (1, -1):
            a = math.radians(150 * s)
            r = np.array([d[0] * math.cos(a) - d[1] * math.sin(a), d[0] * math.sin(a) + d[1] * math.cos(a)])
            q = e + r * thick * 4.5
            cv2.line(ov, tuple(np.round(e * 4).astype(int)), tuple(np.round(q * 4).astype(int)), color, thick,
                     cv2.LINE_AA, shift=2)
    if alpha >= 0.99:
        frame[:] = ov
    else:
        cv2.addWeighted(ov, alpha, frame, 1 - alpha, 0, dst=frame)


def marker(frame, x0, y0, x1, y1, u, color=HILITE, alpha=0.75, seed=0, angle=-1.2):
    """Yellow highlighter swipe (multiply) from x0 to x1, progress u."""
    if u <= 0:
        return
    xe = x0 + (x1 - x0) * clamp(u)
    rng = np.random.default_rng(seed)
    h = y1 - y0
    top = [(x, y0 + rng.uniform(-3, 3)) for x in np.linspace(x0, xe, 8)]
    bot = [(x, y1 + rng.uniform(-3, 3)) for x in np.linspace(xe, x0, 8)]
    pts = np.array(top + [(xe + h * 0.12, (y0 + y1) / 2)] + bot + [(x0 - h * 0.1, (y0 + y1) / 2)], np.float32)
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    ctr = np.array([(x0 + x1) / 2, (y0 + y1) / 2])
    pts = (pts - ctr) @ np.array([[c, s], [-s, c]], np.float32) + ctr
    mask = np.zeros(frame.shape[:2], np.uint8)
    cv2.fillPoly(mask, [np.round(pts * 4).astype(np.int32)], 255, cv2.LINE_AA, shift=2)
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return
    bx0, bx1, by0, by1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    roi = frame[by0:by1, bx0:bx1].astype(np.float32)
    a = mask[by0:by1, bx0:bx1, None].astype(np.float32) / 255 * alpha
    mult = roi * np.array(color, np.float32) / 255
    frame[by0:by1, bx0:bx1] = np.clip(roi + (mult - roi) * a, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- film look
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_R = np.sqrt(((_xx - W / 2) / (W / 2)) ** 2 + ((_yy - H / 2) / (H / 2)) ** 2)
del _yy, _xx


@lru_cache(maxsize=4)
def vignette_map(strength):
    v = np.clip(1.0 - strength * np.clip(_R - 0.35, 0, None) ** 1.7, 0, 1)
    return np.repeat((v * 255).astype(np.uint8)[..., None], 3, 2)


@lru_cache(maxsize=4)
def grain_bank(amount):
    rng = np.random.default_rng(int(amount * 100))
    bank = []
    for _ in range(8):
        n = rng.normal(0, amount, (H // 2, W // 2)).astype(np.float32)
        n = cv2.resize(n, (W, H), interpolation=cv2.INTER_LINEAR)
        n = np.repeat(n[..., None], 3, 2)
        bank.append((np.clip(n, 0, 255).astype(np.uint8), np.clip(-n, 0, 255).astype(np.uint8)))
    return bank


def finish(frame, i, grain=4.0, vig=0.35, flicker=0.0):
    cv2.multiply(frame, vignette_map(vig), dst=frame, scale=1 / 255)
    if flicker:
        k = 1 + (np.random.default_rng(i * 7919).random() - 0.5) * flicker
        cv2.convertScaleAbs(frame, dst=frame, alpha=k)
    if grain:
        pos, neg = grain_bank(grain)[i % 8]
        cv2.add(frame, pos, dst=frame)
        cv2.subtract(frame, neg, dst=frame)
    return frame


def dust(frame, i, amount=1.0):
    """Archival film dirt: white specks, hairs and the odd vertical scratch."""
    rng = np.random.default_rng(i * 104729 + 17)
    ov = frame.copy()
    for _ in range(int(rng.poisson(5 * amount))):
        x, y = int(rng.uniform(0, W)), int(rng.uniform(0, H))
        r = int(rng.uniform(1, 3.5))
        c = int(rng.uniform(170, 255)) if rng.random() < 0.75 else int(rng.uniform(0, 40))
        cv2.circle(ov, (x, y), r, (c, c, c), -1, cv2.LINE_AA)
    if rng.random() < 0.25 * amount:
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        pts = arrow_pts((x, y), (x + rng.uniform(-60, 60), y + rng.uniform(-60, 60)), int(rng.integers(9999)), 12, 0.3)
        cv2.polylines(ov, [pts.astype(np.int32)], False, (225, 225, 225), 1, cv2.LINE_AA)
    if rng.random() < 0.18 * amount:
        x = int(rng.uniform(0, W))
        cv2.line(ov, (x, 0), (x + int(rng.uniform(-6, 6)), H), (200, 200, 200), 1, cv2.LINE_AA)
    cv2.addWeighted(ov, 0.7, frame, 0.3, 0, dst=frame)


def light_leak(frame, u, seed=0):
    """Warm light leak (screen blend), strength u 0..1."""
    if u <= 0:
        return
    rng = np.random.default_rng(seed)
    cx, cy = rng.uniform(0.1, 0.9) * W, rng.uniform(-0.1, 0.4) * H
    d = np.sqrt((np.arange(W)[None, :] - cx) ** 2 / (W * 0.5) ** 2 +
                (np.arange(H)[:, None] - cy) ** 2 / (H * 0.6) ** 2)
    g = np.clip(1 - d, 0, 1) ** 1.6 * u
    leak = np.stack([g * 255, g * 150, g * 60], -1)
    f = frame.astype(np.float32)
    frame[:] = np.clip(255 - (255 - f) * (255 - leak) / 255, 0, 255).astype(np.uint8)


def shake(t, t0, dur=0.12, amp=10, seed=0):
    if t < t0 or t > t0 + dur:
        return 0.0, 0.0
    rng = np.random.default_rng(seed + int((t - t0) * FPS))
    k = 1 - (t - t0) / dur
    return rng.uniform(-amp, amp) * k, rng.uniform(-amp, amp) * k
