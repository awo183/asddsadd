"""The paper-collage look of "Twenty Boats": palette, type, paper, prints,
cut-outs, highlighter, hand-drawn marks, tape labels and pop-in motion.

Frames are uint8 RGB arrays (H, W, 3). Sprites are premultiplied float32 RGBA
images that can be drawn at any position, scale and tilt.
"""
import math
import os
import zlib
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "assets", "fonts")
W, H, FPS = 1920, 1080, 30

# ------------------------------------------------------------------ palette (see STYLE.md)
PAPER = (242, 236, 223)      # #F2ECDF warm off-white paper
PAPER2 = (228, 219, 202)     # #E4DBCA darker paper (cards, shading)
WHITE = (251, 249, 243)      # #FBF9F3 print borders, paper strips
GRID = (212, 203, 186)       # #D4CBBA graph-paper lines
INK = (30, 28, 27)           # #1E1C1B near-black type and line work
INK2 = (96, 90, 84)          # #605A54 secondary type
YELLOW = (247, 210, 30)      # #F7D21E signature highlighter yellow
CORAL = (242, 118, 90)       # #F2765A accent: circles, markers, emphasis
BLUE = (76, 111, 214)        # #4C6FD6 secondary, only for "the other side" in comparisons
SEA = (44, 50, 54)           # #2C3236 night-map sea
LAND = (214, 197, 158)       # #D6C59E night-map land
WATER = (120, 160, 196)      # #78A0C4 flood water in diagrams


def rgb(hexs):
    hexs = hexs.lstrip("#")
    return tuple(int(hexs[i:i + 2], 16) for i in (0, 2, 4))


# ------------------------------------------------------------------ easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lin(t, t0, t1):
    return clamp((t - t0) / (t1 - t0)) if t1 != t0 else float(t >= t1)


def smooth(u):
    u = clamp(u)
    return u * u * (3 - 2 * u)


def ease_out(u):
    u = clamp(u)
    return 1 - (1 - u) ** 3


def ease_in_out(u):
    u = clamp(u)
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


def back_out(u, k=1.9):
    u = clamp(u)
    return 1 + (k + 1) * (u - 1) ** 3 + k * (u - 1) ** 2


def lerp(a, b, u):
    return a + (b - a) * u


def pop(t, t0, dur=0.38):
    """(scale, alpha) of an element popping in at t0."""
    if t < t0:
        return 0.0, 0.0
    u = (t - t0) / dur
    return (0.55 + 0.45 * back_out(u)), clamp(u * 2.5)


def fade(t, t0, t1, d=0.25):
    return clamp(min((t - t0) / d + 1 if d else 1, (t1 - t) / d + 1 if d else 1))


# ------------------------------------------------------------------ type
FACES = {
    # name: (file, default weight, default width)
    "sans": ("Archivo-VF.ttf", 600, 100),
    "head": ("Archivo-VF.ttf", 800, 100),
    "black": ("Archivo-VF.ttf", 900, 100),
    "cond": ("Archivo-VF.ttf", 800, 80),
    "label": ("Archivo-VF.ttf", 700, 100),
    "serif": ("LibreCaslonText-VF.ttf", 400, None),
    "serif_b": ("LibreCaslonText-VF.ttf", 700, None),
    "serif_i": ("LibreCaslonText-Italic-VF.ttf", 400, None),
    "display_i": ("PlayfairDisplay-Italic-VF.ttf", 800, None),
    "display": ("PlayfairDisplay-VF.ttf", 800, None),
    "hand": ("Caveat-VF.ttf", 700, None),
    "mono": ("IBMPlexMono-Medium.ttf", None, None),
}


@lru_cache(maxsize=None)
def font(face, size, wght=None):
    path, w0, wd = FACES[face]
    f = ImageFont.truetype(os.path.join(FONTS, path), int(size))
    if w0 is not None:
        axes = [a["name"] if isinstance(a["name"], str) else a["name"].decode()
                for a in f.get_variation_axes()]
        vals = []
        for a in axes:
            a = a.lower()
            vals.append(wght or w0 if a.startswith("weight") else wd or 100)
        f.set_variation_by_axes(vals)
    return f


@lru_cache(maxsize=None)
def metrics(face, size, wght=None):
    """Cap height and the extra room accents on capitals need (Ě, Š, Ů ...)."""
    f = font(face, size, wght)
    cap = -f.getbbox("H", anchor="ls")[1]
    top = -f.getbbox("ĚŠČŘŽÁÍÉŮŇŤĎÝ", anchor="ls")[1]
    desc = f.getbbox("gjpqy,", anchor="ls")[3]
    return cap, top, desc


@lru_cache(maxsize=6000)
def text_sprite(s, face="sans", size=48, color=INK, wght=None, tracking=0):
    """Text as a sprite; its anchor point (0, 0) is the left end of the baseline.
    The canvas leaves headroom above the cap height so accents are never cut."""
    f = font(face, size, wght)
    cap, top, desc = metrics(face, size, wght)
    pad = int(size * 0.12) + 4
    if tracking:
        widths = [f.getlength(ch) for ch in s]
        width = sum(widths) + tracking * max(len(s) - 1, 0)
    else:
        width = f.getlength(s)
    bb = f.getbbox(s, anchor="ls")
    left_over = max(0, -bb[0])
    wpx = int(width + left_over + 2 * pad + max(0, bb[2] - width))
    base = pad + max(top, cap) + 2
    hpx = int(base + max(desc, bb[3]) + pad)
    img = Image.new("RGBA", (wpx, hpx), tuple(color) + (0,))
    d = ImageDraw.Draw(img)
    x0 = pad + left_over
    if tracking:
        x = x0
        for ch, w in zip(s, widths):
            d.text((x, base), ch, font=f, fill=tuple(color) + (255,), anchor="ls")
            x += w + tracking
    else:
        d.text((x0, base), s, font=f, fill=tuple(color) + (255,), anchor="ls")
    spr = Sprite(np.array(img), anchor=(x0, base))
    spr.width, spr.cap = width, cap
    return spr


def text_width(s, face="sans", size=48, wght=None, tracking=0):
    return text_sprite(s, face, size, INK, wght, tracking).width


def draw_text(frame, s, x, y, face="sans", size=48, color=INK, anchor="l", valign="base",
              alpha=1.0, scale=1.0, angle=0.0, wght=None, tracking=0):
    """Draw text. x is the left/centre/right edge (anchor l/c/r); y is the baseline
    (valign="base"), the middle of the cap height ("mid") or the cap top ("top")."""
    if not s or alpha <= 0.003:
        return 0
    spr = text_sprite(s, face, int(size), tuple(color), wght, tracking)
    w, cap = spr.width, spr.cap
    dx = {"l": 0, "c": -w / 2, "r": -w}[anchor]
    dy = {"base": 0, "mid": cap / 2, "top": cap}[valign]
    # pivot for scale/rotation = the anchor point itself
    spr.draw(frame, x, y, scale=scale, angle=angle, alpha=alpha, offset=(dx, dy))
    return w


def wrap(s, face, size, max_w, wght=None):
    words, lines, cur = s.split(), [], ""
    for wd in words:
        cand = (cur + " " + wd).strip()
        if cur and text_width(cand, face, size, wght) > max_w:
            lines.append(cur)
            cur = wd
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


# ------------------------------------------------------------------ sprites
class Sprite:
    """Premultiplied RGBA image with an anchor point, drawable with scale + tilt."""

    def __init__(self, rgba, anchor=None, premultiplied=False):
        a = rgba.astype(np.float32)
        if a.shape[2] == 3:
            a = np.dstack([a, np.full(a.shape[:2], 255, np.float32)])
        if not premultiplied:
            a[..., :3] *= a[..., 3:4] / 255.0
        self.a = a / 255.0
        self.h, self.w = a.shape[:2]
        self.anchor = anchor if anchor is not None else (self.w / 2, self.h / 2)

    def matrix(self, x, y, scale=1.0, angle=0.0, offset=(0, 0)):
        """2x3 affine taking sprite pixels to screen pixels for draw(...)."""
        ax, ay = self.anchor[0] - offset[0], self.anchor[1] - offset[1]
        c, s = math.cos(math.radians(angle)) * scale, math.sin(math.radians(angle)) * scale
        return np.array([[c, -s, x - (c * ax - s * ay)], [s, c, y - (s * ax + c * ay)]], np.float32)

    def local(self, px, py, x, y, scale=1.0, angle=0.0, offset=(0, 0)):
        """Screen position of the sprite pixel (px, py) when drawn at (x, y)."""
        m = self.matrix(x, y, scale, angle, offset)
        return float(m[0, 0] * px + m[0, 1] * py + m[0, 2]), float(m[1, 0] * px + m[1, 1] * py + m[1, 2])

    def draw(self, frame, x, y, scale=1.0, angle=0.0, alpha=1.0, offset=(0, 0), clip=None):
        """Put the anchor point at (x, y). offset shifts the image in its own
        (unscaled, unrotated) coordinates before the transform."""
        if alpha <= 0.003 or scale <= 0.01:
            return
        m = self.matrix(x, y, scale, angle, offset)
        corners = np.array([[0, 0, 1], [self.w, 0, 1], [0, self.h, 1], [self.w, self.h, 1]],
                           np.float32) @ m.T
        fx0, fy0, fx1, fy1 = clip if clip else (0, 0, frame.shape[1], frame.shape[0])
        x0 = max(int(math.floor(corners[:, 0].min())) - 1, fx0)
        y0 = max(int(math.floor(corners[:, 1].min())) - 1, fy0)
        x1 = min(int(math.ceil(corners[:, 0].max())) + 1, fx1)
        y1 = min(int(math.ceil(corners[:, 1].max())) + 1, fy1)
        if x1 <= x0 or y1 <= y0:
            return
        tx, ty = float(m[0, 2]), float(m[1, 2])
        if abs(angle) < 1e-3 and abs(scale - 1) < 1e-4 and abs(tx - round(tx)) < 1e-3 and \
                abs(ty - round(ty)) < 1e-3:
            tx, ty = int(round(tx)), int(round(ty))
            x0, y0 = max(tx, fx0), max(ty, fy0)
            x1, y1 = min(tx + self.w, fx1), min(ty + self.h, fy1)
            if x1 <= x0 or y1 <= y0:
                return
            src = self.a[y0 - ty:y1 - ty, x0 - tx:x1 - tx]
        else:
            m2 = m.copy()
            m2[0, 2] -= x0
            m2[1, 2] -= y0
            src = cv2.warpAffine(self.a, m2, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        composite(frame, src, x0, y0, alpha)


def composite(frame, src, x0, y0, alpha=1.0):
    """Premultiplied 'over' of src (float 0..1 RGBA) onto the uint8 frame."""
    h, w = src.shape[:2]
    roi = frame[y0:y0 + h, x0:x0 + w]
    if roi.shape[:2] != (h, w):
        src = src[:roi.shape[0], :roi.shape[1]]
    a = src[..., 3:4] * alpha
    if float(a.max()) <= 0.002:
        return
    out = roi.astype(np.float32) * (1 - a) + src[..., :3] * (255.0 * alpha)
    roi[:] = np.clip(out, 0, 255).astype(np.uint8)


def with_shadow(rgba, blur=14, dx=10, dy=14, opacity=0.38, color=(40, 30, 20)):
    """Bake a soft drop shadow under a straight-alpha RGBA image (uint8)."""
    pad = int(blur * 2.5 + max(abs(dx), abs(dy)))
    h, w = rgba.shape[:2]
    out = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.float32)
    al = np.zeros(out.shape[:2], np.float32)
    al[pad + dy:pad + dy + h, pad + dx:pad + dx + w] = rgba[..., 3] / 255.0
    al = cv2.GaussianBlur(al, (0, 0), blur) * opacity
    out[..., :3] = np.array(color, np.float32) / 255.0 * al[..., None]
    out[..., 3] = al
    fg = rgba.astype(np.float32) / 255.0
    fa = fg[..., 3:4]
    region = out[pad:pad + h, pad:pad + w]
    region[..., :3] = fg[..., :3] * fa + region[..., :3] * (1 - fa)
    region[..., 3:4] = fa + region[..., 3:4] * (1 - fa)
    spr = Sprite((out * 255).astype(np.float32), premultiplied=True)
    spr.anchor = (pad + w / 2, pad + h / 2)
    spr.core = (pad, pad, w, h)
    return spr


# ------------------------------------------------------------------ paper
def _noise(h, w, scale, seed):
    rng = np.random.default_rng(seed)
    small = rng.standard_normal((max(2, h // scale + 2), max(2, w // scale + 2))).astype(np.float32)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC)


@lru_cache(maxsize=8)
def paper(w=2400, h=1400, seed=1, grid=48, tint=PAPER, crumple=1.0, grid_alpha=0.42):
    """Warm textured paper with a faint printed grid and soft creases (uint8 RGB)."""
    base = np.empty((h, w, 3), np.float32)
    base[:] = tint
    mott = _noise(h, w, 180, seed) * 3.0 + _noise(h, w, 40, seed + 1) * 1.6
    fib = np.random.default_rng(seed + 2).standard_normal((h, w)).astype(np.float32)
    fib = cv2.GaussianBlur(fib, (0, 0), 0.7) * 2.2
    streak = cv2.GaussianBlur(np.random.default_rng(seed + 3).standard_normal((h, w))
                              .astype(np.float32), (0, 0), sigmaX=6, sigmaY=0.6) * 5
    shade = mott + fib + streak
    if crumple:
        rng = np.random.default_rng(seed + 4)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        height = np.zeros((h, w), np.float32)
        for _ in range(22):
            ang = rng.uniform(0, np.pi)
            nx, ny = np.cos(ang), np.sin(ang)
            off = rng.uniform(-0.5, 0.5) * (w + h) * 0.5
            d = (xx - w / 2) * nx + (yy - h / 2) * ny - off
            height += np.abs(d) * rng.uniform(-0.02, 0.02)
        gx = cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3)
        light = (gx * -0.6 + gy * -0.8)
        light = cv2.GaussianBlur(light, (0, 0), 2.0)
        shade += np.clip(light * 6.0, -9, 9) * crumple
    base += shade[..., None]
    img = np.clip(base, 0, 255).astype(np.uint8)
    if grid:
        ov = img.copy()
        jitter = _noise(h, w, 300, seed + 5)
        for x in range(grid // 2, w, grid):
            cv2.line(ov, (x, 0), (x, h), GRID, 1, cv2.LINE_AA)
        for y in range(grid // 2, h, grid):
            cv2.line(ov, (0, y), (w, y), GRID, 1, cv2.LINE_AA)
        a = (grid_alpha * (0.8 + 0.2 * np.clip(jitter, -1, 1)))[..., None]
        img = (img * (1 - a) + ov * a).astype(np.uint8)
    return img


def paper_view(cx=0.0, cy=0.0, zoom=1.0, **kw):
    """A 1920x1080 window into a big sheet of paper (camera pan/zoom)."""
    p = paper(**kw)
    ph, pw = p.shape[:2]
    if abs(zoom - 1) < 1e-4:
        x0 = int(round(clamp(pw / 2 - W / 2 + cx, 0, pw - W)))
        y0 = int(round(clamp(ph / 2 - H / 2 + cy, 0, ph - H)))
        return p[y0:y0 + H, x0:x0 + W].copy()
    m = np.float32([[zoom, 0, W / 2 - zoom * (pw / 2 + cx)], [0, zoom, H / 2 - zoom * (ph / 2 + cy)]])
    return cv2.warpAffine(p, m, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def sheet(color=PAPER, seed=7, w=W, h=H, grid=48, crumple=0.6):
    return paper(w=w, h=h, seed=seed, grid=grid, tint=color, crumple=crumple)


# ------------------------------------------------------------------ archival prints
_CURVE = np.clip(255 * (0.5 + 0.5 * np.tanh(1.5 * (np.arange(256) / 255 - 0.5) * 2) /
                         np.tanh(1.5)), 0, 255).astype(np.uint8)


def print_grade(img, sepia=0.10, contrast=True, lift=14):
    """Archival photo as a slightly warm black-and-white print."""
    g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if img.ndim == 3 else img
    g = cv2.createCLAHE(clipLimit=1.6, tileGridSize=(8, 8)).apply(g)
    if contrast:
        g = cv2.LUT(g, _CURVE)
    g = g.astype(np.float32) * (255 - lift) / 255 + lift
    warm = np.array([1.0 + 0.06 * sepia * 10, 1.0 + 0.02 * sepia * 10, 1.0 - 0.07 * sepia * 10])
    out = np.clip(g[..., None] * warm[None, None, :] * np.array([0.99, 0.975, 0.95]), 0, 255)
    return out.astype(np.uint8)


def halftone(gray_rgb, cell=5, amount=0.22):
    """Add a fine printed-dot texture (like the reference's newsprint cut-outs)."""
    h, w = gray_rgb.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r, c45 = (xx + yy) / (cell * 1.414), (xx - yy) / (cell * 1.414)
    dots = (np.cos(r * 2 * np.pi) + np.cos(c45 * 2 * np.pi)) * 0.25 + 0.5
    lum = gray_rgb.mean(axis=2, keepdims=True) / 255.0
    screen = (dots[..., None] < lum).astype(np.float32)
    out = gray_rgb.astype(np.float32) * (1 - amount) + (screen * 255) * amount
    return np.clip(out, 0, 255).astype(np.uint8)


def _torn_mask(h, w, amp, seed, inset=0):
    """Rectangle mask with torn, fibrous edges."""
    rng = np.random.default_rng(seed)
    m = np.zeros((h, w), np.uint8)

    def edge(n):
        a = np.cumsum(rng.standard_normal(n)) * 0.6
        a -= np.linspace(a[0], a[-1], n)
        a = a / (np.abs(a).max() + 1e-6) * amp * 0.6 + rng.standard_normal(n) * amp * 0.18
        return np.abs(a) + inset

    top, bot, lef, rig = edge(w), edge(w), edge(h), edge(h)
    xs, ys = np.arange(w), np.arange(h)
    pts = ([(x, top[x]) for x in xs] + [(w - 1 - rig[y], y) for y in ys] +
           [(x, h - 1 - bot[x]) for x in xs[::-1]] + [(lef[y], y) for y in ys[::-1]])
    cv2.fillPoly(m, [np.array(pts, np.int32)], 255, cv2.LINE_AA)
    return m


def torn_print(img, target_h=None, border=16, seed=1, sepia=0.10, grade=True, tex=True,
               shadow=True, edge_amp=7):
    """An archival photo as a print with a torn white paper border and a drop shadow."""
    src_w = img.shape[1]
    if target_h:
        s = target_h / img.shape[0]
        img = cv2.resize(img, (max(1, int(img.shape[1] * s)), int(target_h)),
                         interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    ph = print_grade(img, sepia) if grade else img
    if tex:
        ph = halftone(ph, amount=0.08)
    h, w = ph.shape[:2]
    H2, W2 = h + 2 * border, w + 2 * border
    out = np.zeros((H2, W2, 4), np.uint8)
    out[..., :3] = WHITE
    out[border:border + h, border:border + w, :3] = ph
    m = _torn_mask(H2, W2, edge_amp, seed)
    out[..., 3] = m
    # paper fibres catch a little shade along the torn edge
    edge = cv2.GaussianBlur((m < 250).astype(np.float32), (0, 0), 1.5)
    out[..., :3] = np.clip(out[..., :3].astype(np.float32) - edge[..., None] * 18, 0, 255)
    spr = with_shadow(out) if shadow else Sprite(out)
    pad = spr.core[0] if shadow else 0
    spr.photo = (pad + border, pad + border, w / src_w)     # origin x, y and scale of the photo
    return spr


def cutout(img, mask, target_h=None, sepia=0.10, grade=True, tex=True, shadow=True, feather=1.2,
           outline=0):
    """A die-cut object (photo + matte) with a soft shadow, like the reference cut-outs."""
    if target_h:
        s = target_h / img.shape[0]
        size = (max(1, int(img.shape[1] * s)), int(target_h))
        img = cv2.resize(img, size, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
        mask = cv2.resize(mask, size, interpolation=cv2.INTER_LINEAR)
    ph = print_grade(img, sepia) if grade else img
    if tex:
        ph = halftone(ph, amount=0.10)
    a = mask.astype(np.float32)
    if feather:
        a = cv2.GaussianBlur(a, (0, 0), feather)
    out = np.dstack([ph, np.clip(a, 0, 255).astype(np.uint8)])
    if outline:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * outline + 1, 2 * outline + 1))
        grown = cv2.dilate(mask, k)
        base = np.zeros_like(out)
        base[..., :3] = WHITE
        base[..., 3] = cv2.GaussianBlur(grown, (0, 0), 1.0)
        fa = out[..., 3:4].astype(np.float32) / 255
        out = np.dstack([(out[..., :3] * fa + base[..., :3] * (1 - fa)).astype(np.uint8),
                         np.maximum(out[..., 3], base[..., 3])])
    return with_shadow(out, blur=12, dx=8, dy=12, opacity=0.32) if shadow else Sprite(out)


# ------------------------------------------------------------------ shapes
def circle_sprite(r, color, halftone_dots=True, seed=3):
    """A flat colour disc with a halftone speckle (reference: coral circles)."""
    s = int(2 * r + 8)
    img = np.zeros((s, s, 4), np.uint8)
    cv2.circle(img, (s // 2, s // 2), int(r), tuple(color) + (255,), -1, cv2.LINE_AA)
    if halftone_dots:
        yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
        dots = (np.cos((xx + yy) / 7.0 * np.pi) + np.cos((xx - yy) / 7.0 * np.pi))
        grad = np.clip((xx / s) * 1.2 - 0.2, 0, 1)
        speck = ((dots > 1.2 + 0.6 * (1 - grad)) * 18).astype(np.float32)
        noise = _noise(s, s, 6, seed) * 4
        img[..., :3] = np.clip(img[..., :3].astype(np.float32) - speck[..., None] - noise[..., None],
                               0, 255).astype(np.uint8)
    return Sprite(img)


def rough_rect(frame, x0, y0, x1, y1, color, alpha=1.0, seed=0, rough=2.5, texture=True):
    """A flat fill with slightly rough edges and a dry-brush texture (chart bars)."""
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    if x1 - x0 < 2 or y1 - y0 < 2 or alpha <= 0:
        return
    pad = int(rough * 3) + 2
    h, w = y1 - y0 + 2 * pad, x1 - x0 + 2 * pad
    m = np.zeros((h, w), np.float32)
    cv2.rectangle(m, (pad, pad), (w - pad, h - pad), 1.0, -1)
    if rough:
        n = _tex(h, w, seed)
        m = np.clip(cv2.GaussianBlur(m, (0, 0), rough * 0.6) * 1.6 - 0.3 + n * 0.25, 0, 1)
    src = np.zeros((h, w, 4), np.float32)
    shade = (1 - (_tex(h, w, seed + 9) * 0.06 if texture else 0))[..., None]
    src[..., :3] = np.array(color, np.float32) / 255 * shade * m[..., None]
    src[..., 3] = m
    X0, Y0 = x0 - pad, y0 - pad
    cx0, cy0 = max(X0, 0), max(Y0, 0)
    cx1, cy1 = min(X0 + w, frame.shape[1]), min(Y0 + h, frame.shape[0])
    if cx1 <= cx0 or cy1 <= cy0:
        return
    composite(frame, src[cy0 - Y0:cy1 - Y0, cx0 - X0:cx1 - X0], cx0, cy0, alpha)


@lru_cache(maxsize=64)
def _tex_cached(h, w, seed):
    return np.clip(_noise(h, w, 3, seed) * 0.5 + _noise(h, w, 18, seed + 1) * 0.5, -1, 1)


def _tex(h, w, seed):
    return _tex_cached(int(h), int(w), int(seed) % 16)


def highlight(frame, x0, y0, x1, y1, u, color=YELLOW, seed=0, alpha=0.88):
    """A yellow highlighter stroke sweeping left to right over [x0, x1] (multiply)."""
    if u <= 0:
        return
    x0, x1, y0, y1 = int(x0), int(x1), int(y0), int(y1)
    xe = int(x0 + (x1 - x0) * ease_out(u))
    rng = np.random.default_rng(seed)
    w = xe - x0
    if w < 2:
        return
    h = y1 - y0
    pad = 8
    X0, Y0 = x0 - pad, y0 - pad
    cx0, cy0 = max(X0, 0), max(Y0, 0)
    cx1, cy1 = min(xe + pad, frame.shape[1]), min(y1 + pad, frame.shape[0])
    if cx1 <= cx0 or cy1 <= cy0:
        return
    hh, ww = cy1 - cy0, cx1 - cx0
    xs = np.arange(ww) + cx0
    wob_t = np.interp(xs, np.linspace(x0, x1, 9), rng.uniform(-2.5, 2.5, 9)) + h * 0.03
    wob_b = np.interp(xs, np.linspace(x0, x1, 9), rng.uniform(-2.5, 2.5, 9)) - h * 0.03
    ys = (np.arange(hh) + cy0)[:, None]
    m = ((ys >= y0 + wob_t[None, :]) & (ys <= y1 + wob_b[None, :]) & (xs[None, :] >= x0) &
         (xs[None, :] <= xe)).astype(np.float32)
    # slanted chisel ends
    slope = (ys - y0) / max(h, 1) * 6
    m *= ((xs[None, :] >= x0 + 6 - slope) & (xs[None, :] <= xe - slope + 2)).astype(np.float32)
    m = cv2.GaussianBlur(m, (0, 0), 1.0)
    streak = 1 - 0.10 * (_tex(hh, ww, seed + 3) * 0.5 + 0.5)
    a = (m * alpha * streak)[..., None]
    roi = frame[cy0:cy1, cx0:cx1].astype(np.float32)
    tint = np.array(color, np.float32) / 255.0
    roi = roi * (1 - a) + roi * tint * a
    frame[cy0:cy1, cx0:cx1] = np.clip(roi, 0, 255).astype(np.uint8)


def highlight_on(frame, spr, rect, u, draw_args, color=YELLOW, seed=0, alpha=0.85):
    """Highlighter over rect=(x0, y0, x1, y1) given in the sprite's photo pixels
    (see torn_print().photo); it tilts and scales with the sprite."""
    if u <= 0:
        return
    ox, oy, k = getattr(spr, "photo", (0, 0, 1.0))
    x0, y0, x1, y1 = [ox + rect[0] * k, oy + rect[1] * k, ox + rect[2] * k, oy + rect[3] * k]
    pad = 6
    w, h = int(x1 - x0 + 2 * pad), int(y1 - y0 + 2 * pad)
    if w < 4 or h < 4:
        return
    rng = np.random.default_rng(seed)
    xe = pad + (w - 2 * pad) * ease_out(u)
    xs = np.arange(w, dtype=np.float32)
    wob_t = np.interp(xs, np.linspace(0, w, 9), rng.uniform(-0.05, 0.05, 9) * h) + pad
    wob_b = np.interp(xs, np.linspace(0, w, 9), rng.uniform(-0.05, 0.05, 9) * h) + h - pad
    ys = np.arange(h, dtype=np.float32)[:, None]
    slope = (ys - pad) / max(h - 2 * pad, 1) * h * 0.12
    m = ((ys >= wob_t[None, :]) & (ys <= wob_b[None, :]) & (xs[None, :] >= pad + slope * 0.5) &
         (xs[None, :] <= xe - slope + h * 0.06)).astype(np.float32)
    m = cv2.GaussianBlur(m, (0, 0), max(0.8, h / 60))
    m *= (1 - 0.10 * (_tex(h, w, seed + 3) * 0.5 + 0.5))
    M = spr.matrix(*draw_args) if isinstance(draw_args, tuple) else spr.matrix(**draw_args)
    T = np.array([[1, 0, x0 - pad], [0, 1, y0 - pad], [0, 0, 1]], np.float32)
    M2 = M @ T
    corners = np.array([[0, 0, 1], [w, 0, 1], [0, h, 1], [w, h, 1]], np.float32) @ M2.T
    X0, Y0 = max(int(corners[:, 0].min()) - 1, 0), max(int(corners[:, 1].min()) - 1, 0)
    X1 = min(int(corners[:, 0].max()) + 2, frame.shape[1])
    Y1 = min(int(corners[:, 1].max()) + 2, frame.shape[0])
    if X1 <= X0 or Y1 <= Y0:
        return
    M2[0, 2] -= X0
    M2[1, 2] -= Y0
    mm = cv2.warpAffine(m, M2, (X1 - X0, Y1 - Y0), flags=cv2.INTER_LINEAR)
    a = (mm * alpha)[..., None]
    roi = frame[Y0:Y1, X0:X1].astype(np.float32)
    tint = np.array(color, np.float32) / 255.0
    frame[Y0:Y1, X0:X1] = np.clip(roi * (1 - a + a * tint), 0, 255).astype(np.uint8)


def _stroke(frame, pts, u, color, width=7, alpha=1.0):
    """Draw the first u (0..1) of a polyline like a felt-tip marker."""
    if u <= 0 or len(pts) < 2:
        return
    pts = np.asarray(pts, np.float32)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    L = cum[-1] * clamp(u)
    k = int(np.searchsorted(cum, L))
    use = pts[:k].tolist()
    if 0 < k < len(pts):
        f = (L - cum[k - 1]) / max(seg[k - 1], 1e-6)
        use.append((pts[k - 1] + (pts[k] - pts[k - 1]) * f).tolist())
    if len(use) < 2:
        return
    xs, ys = [p[0] for p in use], [p[1] for p in use]
    x0, y0 = int(max(min(xs) - width * 2, 0)), int(max(min(ys) - width * 2, 0))
    x1 = int(min(max(xs) + width * 2, frame.shape[1]))
    y1 = int(min(max(ys) + width * 2, frame.shape[0]))
    if x1 <= x0 or y1 <= y0:
        return
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    arr = (np.array(use) - [x0, y0]) * 4
    cv2.polylines(m, [arr.astype(np.int32)], False, 255, int(width), cv2.LINE_AA, shift=2)
    a = (m.astype(np.float32) / 255 * alpha)[..., None]
    roi = frame[y0:y1, x0:x1].astype(np.float32)
    frame[y0:y1, x0:x1] = np.clip(roi * (1 - a) + np.array(color, np.float32) * a, 0,
                                  255).astype(np.uint8)


def hand_circle(frame, cx, cy, rx, ry, u, color=CORAL, width=7, seed=0, alpha=1.0):
    """A hand-drawn loop around a target that draws itself on."""
    rng = np.random.default_rng(seed)
    a0 = rng.uniform(-2.6, -1.9)
    n = 120
    th = np.linspace(a0, a0 + 2 * np.pi * 1.08, n)
    wob = 1 + np.interp(np.linspace(0, 1, n), np.linspace(0, 1, 6), rng.uniform(-0.05, 0.05, 6))
    drift = np.linspace(0, 0.06, n)
    pts = np.stack([cx + rx * (wob + drift) * np.cos(th), cy + ry * (wob - drift * 0.5) * np.sin(th)], 1)
    _stroke(frame, pts, ease_in_out(u), color, width, alpha)


def hand_line(frame, p0, p1, u, color=CORAL, width=7, seed=0, bow=0.04, alpha=1.0):
    rng = np.random.default_rng(seed)
    p0, p1 = np.array(p0, float), np.array(p1, float)
    d = p1 - p0
    nrm = np.array([-d[1], d[0]]) / (np.linalg.norm(d) + 1e-6)
    s = np.linspace(0, 1, 40)
    bend = np.sin(s * np.pi) * np.linalg.norm(d) * bow * rng.choice([-1, 1])
    pts = p0 + s[:, None] * d + bend[:, None] * nrm
    _stroke(frame, pts, ease_out(u), color, width, alpha)


def hand_arrow(frame, p0, p1, u, color=INK, width=5, seed=0, bow=0.18, head=22, alpha=1.0):
    """A curved hand-drawn arrow from p0 to p1; the head appears when the line arrives."""
    rng = np.random.default_rng(seed)
    p0, p1 = np.array(p0, float), np.array(p1, float)
    d = p1 - p0
    nrm = np.array([-d[1], d[0]]) / (np.linalg.norm(d) + 1e-6)
    s = np.linspace(0, 1, 50)
    side = rng.choice([-1, 1])
    pts = p0 + s[:, None] * d + (np.sin(s * np.pi) * np.linalg.norm(d) * bow * side)[:, None] * nrm
    _stroke(frame, pts, ease_out(clamp(u / 0.8)), color, width, alpha)
    if u > 0.8:
        k = clamp((u - 0.8) / 0.2)
        tip, prev = pts[-1], pts[-6]
        v = (tip - prev) / (np.linalg.norm(tip - prev) + 1e-6)
        for sgn in (-1, 1):
            ang = math.radians(150 * sgn)
            r = np.array([v[0] * math.cos(ang) - v[1] * math.sin(ang),
                          v[0] * math.sin(ang) + v[1] * math.cos(ang)])
            _stroke(frame, [tip, tip + r * head], k, color, width, alpha)


def cross(frame, cx, cy, size, u, color=CORAL, width=10, seed=0):
    hand_line(frame, (cx - size, cy - size), (cx + size, cy + size), clamp(u * 2), color, width,
              seed, 0.03)
    hand_line(frame, (cx + size, cy - size), (cx - size, cy + size), clamp(u * 2 - 1), color,
              width, seed + 1, 0.03)


def tick(frame, cx, cy, size, u, color=CORAL, width=9):
    pts = [(cx - size, cy), (cx - size * 0.3, cy + size * 0.7), (cx + size, cy - size * 0.8)]
    _stroke(frame, pts, ease_out(u), color, width)


# ------------------------------------------------------------------ tape strips + labels
@lru_cache(maxsize=512)
def strip_sprite(s, face="display_i", size=64, ink=INK, fill=(232, 222, 196), pad=(26, 16),
                 seed=0, wght=None, torn=True):
    """Text on a torn strip of paper (reference: 'Proud of', 'Whole')."""
    t = text_sprite(s, face, size, ink, wght)
    cap, top, desc = metrics(face, size, wght)
    tw = int(t.width)
    w = tw + 2 * pad[0]
    h = int(cap + 2 * pad[1] + size * 0.18)
    img = np.zeros((h, w, 4), np.uint8)
    img[..., :3] = fill
    img[..., 3] = _torn_mask(h, w, 5 if torn else 0.01, seed) if torn else 255
    tex = (_noise(h, w, 6, seed + 1) * 5)[..., None]
    img[..., :3] = np.clip(img[..., :3].astype(np.float32) + tex, 0, 255).astype(np.uint8)
    pil = Image.fromarray(img)
    ta = (t.a * 255).astype(np.uint8)
    # un-premultiply text for pasting
    al = ta[..., 3:4].astype(np.float32) / 255
    rgbt = np.where(al > 0, ta[..., :3] / np.maximum(al, 1e-3), 0).clip(0, 255).astype(np.uint8)
    timg = Image.fromarray(np.dstack([rgbt, ta[..., 3]]))
    base_y = pad[1] + cap + int(size * 0.04)
    pil.alpha_composite(timg, (int(pad[0] - t.anchor[0]), int(base_y - t.anchor[1])))
    return with_shadow(np.array(pil), blur=6, dx=4, dy=6, opacity=0.30)


def chip(frame, s, x, y, size=26, fg=WHITE, bg=INK, alpha=1.0, scale=1.0, anchor="l", face="label",
         tracking=1, padx=14, pady=10):
    """A flat label chip (map labels, captions)."""
    spr = _chip_sprite(s, size, fg, bg, face, tracking, padx, pady)
    off = {"l": spr.w / 2, "c": 0, "r": -spr.w / 2}[anchor]
    spr.draw(frame, x + off * scale, y, scale=scale, alpha=alpha)
    return spr.w


@lru_cache(maxsize=512)
def _chip_sprite(s, size, fg, bg, face, tracking, padx, pady):
    t = text_sprite(s, face, size, fg, None, tracking)
    cap = t.cap
    w, h = int(t.width + 2 * padx), int(cap + 2 * pady)
    tmp = np.zeros((h, w, 3), np.uint8)
    tmp[:] = bg
    t.draw(tmp, padx, pady + cap)
    return Sprite(np.dstack([tmp, np.full((h, w), 255, np.uint8)]))


def seed_of(*parts):
    return zlib.crc32("|".join(map(str, parts)).encode()) & 0xFFFF


# ------------------------------------------------------------------ finishing
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / (W / 2)) ** 2 + ((_yy - H / 2) / (H / 2)) ** 2)
VIGNETTE = (np.clip(1.0 - 0.16 * np.clip(_r - 0.55, 0, None) ** 1.5, 0, 1) * 255).astype(np.uint8)
VIGNETTE = np.repeat(VIGNETTE[..., None], 3, axis=2)
_rng = np.random.default_rng(1912)
GRAIN = []
for _ in range(4):
    n = _rng.normal(0, 1.6, (H, W)).astype(np.float32)
    n = np.repeat(n[..., None], 3, axis=2)
    GRAIN.append((np.clip(n, 0, 255).astype(np.uint8), np.clip(-n, 0, 255).astype(np.uint8)))
del _yy, _xx, _r


def finish(frame, i):
    cv2.multiply(frame, VIGNETTE, dst=frame, scale=1 / 255)
    pos, neg = GRAIN[i % len(GRAIN)]
    cv2.add(frame, pos, dst=frame)
    cv2.subtract(frame, neg, dst=frame)
    return frame
