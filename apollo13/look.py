"""The paper-collage look: texture, cut-out photos, marker highlights, hand-drawn
ink, labels and type. Shared by every scene of "The 28-Volt Switch".

Frames are RGB uint8 arrays (H, W, 3). Sprites are RGBA uint8 arrays.
"""
import math
import os
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")

# Tight palette: off-white paper, near-black ink, signature yellow, one accent.
PAPER = (240, 234, 221)
PAPER_DARK = (226, 218, 201)
INK = (30, 29, 28)
INK_SOFT = (92, 88, 82)
YELLOW = (255, 212, 0)
ACCENT = (226, 74, 44)          # signal red-orange
WHITE = (252, 250, 246)
LAND = (219, 210, 190)
LAND_EDGE = (192, 181, 160)

FONT = {
    "black": "Archivo-Black.ttf", "xbold": "Archivo-ExtraBold.ttf", "bold": "Archivo-Bold.ttf",
    "semi": "Archivo-SemiBold.ttf", "medium": "Archivo-Medium.ttf", "regular": "Archivo-Regular.ttf",
    "cond": "Archivo-CondensedBlack.ttf", "serif": "LibreCaslonText-Regular.ttf",
    "serif_bold": "LibreCaslonText-Bold.ttf", "serif_italic": "LibreCaslonText-Italic.ttf",
}


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


def back_out(u, s=1.7):
    u = clamp(u)
    return 1 + (s + 1) * (u - 1) ** 3 + s * (u - 1) ** 2


def lerp(a, b, u):
    return a + (b - a) * u


# ------------------------------------------------------------------ paper
def _paper(w, h, seed=3):
    rng = np.random.default_rng(seed)
    base = np.empty((h, w, 3), np.float32)
    base[:] = PAPER
    n1 = cv2.GaussianBlur(rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 1.2) * 3.2
    n2 = cv2.resize(rng.normal(0, 1, (h // 24, w // 24)).astype(np.float32), (w, h),
                    interpolation=cv2.INTER_CUBIC) * 2.0
    fib = np.zeros((h, w), np.float32)
    for _ in range(900):                       # faint paper fibres
        x, y = rng.integers(0, w), rng.integers(0, h)
        ang, ln = rng.uniform(0, math.pi), rng.uniform(8, 40)
        cv2.line(fib, (int(x), int(y)), (int(x + math.cos(ang) * ln), int(y + math.sin(ang) * ln)),
                 float(rng.uniform(-1, 1)), 1, cv2.LINE_AA)
    fib = cv2.GaussianBlur(fib, (0, 0), 0.8) * 5
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    vig = (1 - 0.10 * np.clip(r - 0.35, 0, None) ** 1.5)[..., None]
    out = (base + (n1 + n2 + fib)[..., None]) * vig
    return np.clip(out, 0, 255).astype(np.uint8)


PAPER_BIG = None


def paper_bg(ox=0.0, oy=0.0):
    """A 1920x1080 crop of a larger paper sheet; ox/oy drift it (parallax)."""
    global PAPER_BIG
    if PAPER_BIG is None:
        PAPER_BIG = _paper(W + 400, H + 300)
    x = int(clamp(200 + ox, 0, 400))
    y = int(clamp(150 + oy, 0, 300))
    return PAPER_BIG[y:y + H, x:x + W].copy()


# ------------------------------------------------------------------ type
@lru_cache(maxsize=None)
def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, FONT[name]), int(size))


@lru_cache(maxsize=6000)
def text_sprite(s, name, size, color=INK, tracking=0):
    """RGBA sprite of a text line sized from real glyph bounds (accents never clip).
    Returns (rgba, baseline_y) where baseline_y is the baseline's row in the sprite."""
    f = font(name, size)
    asc, desc = f.getmetrics()
    widths = [f.getlength(ch) for ch in s]
    width = sum(widths) + tracking * max(len(s) - 1, 0)
    top = min([f.getbbox(ch, anchor="ls")[1] for ch in s if not ch.isspace()] + [-asc])
    bot = max([f.getbbox(ch, anchor="ls")[3] for ch in s if not ch.isspace()] + [desc])
    pad = int(size * 0.08) + 2
    hgt = int(bot - top) + 2 * pad
    img = Image.new("RGBA", (int(width) + 2 * pad + 4, hgt), tuple(color) + (0,))
    d = ImageDraw.Draw(img)
    base = pad - top
    if tracking:
        x = pad
        for ch, wch in zip(s, widths):
            d.text((x, base), ch, font=f, fill=tuple(color) + (255,), anchor="ls")
            x += wch + tracking
    else:
        d.text((pad, base), s, font=f, fill=tuple(color) + (255,), anchor="ls")
    return np.array(img), int(base)


def text_size(s, name, size, tracking=0):
    img, base = text_sprite(s, name, int(size), INK, int(tracking))
    return img.shape[1], img.shape[0]


def text(frame, s, x, y, name="bold", size=40, color=INK, alpha=1.0, anchor="lt", tracking=0,
         scale=1.0):
    """Draw text. anchor: l/c/r + t/m/b (box) or 's' (baseline) for vertical."""
    if not s or alpha <= 0.003:
        return 0, 0
    img, base = text_sprite(s, name, int(size), tuple(color), int(tracking))
    if scale != 1.0:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
        base = int(base * scale)
    h, w = img.shape[:2]
    x -= {"l": 0, "c": w / 2, "r": w}[anchor[0]]
    y -= {"t": 0, "m": h / 2, "b": h, "s": base}[anchor[1]]
    blit(frame, img, x, y, alpha)
    return w, h


def wrap(s, name, size, max_w, tracking=0):
    words, lines, cur = s.split(), [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if cur and text_size(trial, name, size, tracking)[0] > max_w:
            lines.append(cur)
            cur = wd
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


# ------------------------------------------------------------------ compositing
def blit(frame, rgba, x, y, alpha=1.0):
    if alpha <= 0.003:
        return
    h, w = rgba.shape[:2]
    x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, frame.shape[1]), min(y + h, frame.shape[0])
    if x1 <= x0 or y1 <= y0:
        return
    src = rgba[y0 - y:y1 - y, x0 - x:x1 - x]
    a = src[..., 3:4].astype(np.float32) * (alpha / 255.0)
    dst = frame[y0:y1, x0:x1, :3].astype(np.float32)
    frame[y0:y1, x0:x1, :3] = (dst + (src[..., :3].astype(np.float32) - dst) * a).astype(np.uint8)
    if frame.shape[2] == 4:          # drawing onto a card: keep its alpha opaque where we drew
        da = frame[y0:y1, x0:x1, 3:4].astype(np.float32)
        frame[y0:y1, x0:x1, 3:4] = np.maximum(da, a * 255).astype(np.uint8)


def multiply(frame, rgba, x, y, alpha=1.0):
    """Multiply-blend an RGBA sprite (marker ink on paper keeps the text readable)."""
    h, w = rgba.shape[:2]
    x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, frame.shape[1]), min(y + h, frame.shape[0])
    if x1 <= x0 or y1 <= y0 or alpha <= 0:
        return
    src = rgba[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32)
    a = src[..., 3:4] / 255.0 * alpha
    dst = frame[y0:y1, x0:x1, :3].astype(np.float32)
    mul = dst * src[..., :3] / 255.0
    frame[y0:y1, x0:x1, :3] = (dst + (mul - dst) * a).astype(np.uint8)


def place(frame, rgba, cx, cy, scale=1.0, rot=0.0, alpha=1.0, shadow=0.35, shadow_off=(10, 14),
          shadow_blur=14):
    """Composite a sprite centred at (cx, cy), scaled and rotated (degrees), with a soft
    drop shadow. Only the sprite's bounding region is warped."""
    if alpha <= 0.003 or scale <= 0.001:
        return
    h, w = rgba.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), rot, scale)   # keeps the centre at (w/2, h/2)
    corners = np.array([[0, 0], [w, 0], [0, h], [w, h]], np.float32) @ m[:, :2].T + m[:, 2]
    pad = int(shadow_blur * 2 + max(abs(shadow_off[0]), abs(shadow_off[1])) + 4) if shadow > 0 else 2
    ox, oy = cx - w / 2, cy - h / 2                             # sprite centre -> (cx, cy)
    bx0 = int(math.floor(ox + corners[:, 0].min())) - pad
    by0 = int(math.floor(oy + corners[:, 1].min())) - pad
    bw = int(math.ceil(corners[:, 0].max() - corners[:, 0].min())) + 2 * pad + 2
    bh = int(math.ceil(corners[:, 1].max() - corners[:, 1].min())) + 2 * pad + 2
    if bx0 > W or by0 > H or bx0 + bw < 0 or by0 + bh < 0:
        return
    m2 = m.copy()
    m2[0, 2] += ox - bx0
    m2[1, 2] += oy - by0
    warped = cv2.warpAffine(rgba, m2, (bw, bh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                            borderValue=(0, 0, 0, 0))
    if shadow > 0:
        sa = warped[..., 3].astype(np.float32)
        sa = np.roll(np.roll(sa, int(shadow_off[1]), 0), int(shadow_off[0]), 1)
        sa = cv2.GaussianBlur(sa, (0, 0), shadow_blur)
        sh = np.zeros((bh, bw, 4), np.uint8)
        sh[..., :3] = (40, 32, 24)
        sh[..., 3] = np.clip(sa * shadow, 0, 255).astype(np.uint8)
        blit(frame, sh, bx0, by0, alpha)
    blit(frame, warped, bx0, by0, alpha)


def to_rgba(img, alpha=255):
    a = np.full(img.shape[:2] + (1,), alpha, np.uint8)
    return np.concatenate([img, a], 2)


@lru_cache(maxsize=64)
def _load_rgb(path):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def photo_card(path, height, border=14, grade=True, crop=None, bottom=0, caption=None,
               cap_size=22, max_side=1700):
    """A photo printed with a white border (optionally a deeper bottom border for a
    hand-written style caption), as an RGBA sprite."""
    img = _load_rgb(path)
    if crop:
        x0, y0, x1, y1 = crop
        hh, ww = img.shape[:2]
        img = img[int(y0 * hh):int(y1 * hh), int(x0 * ww):int(x1 * ww)]
    s = height / img.shape[0]
    if img.shape[1] * s > max_side:
        s = max_side / img.shape[1]
    img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    if grade:
        img = archival(img)
    return frame_card(img, border, bottom, caption, cap_size)


def frame_card(img, border=14, bottom=0, caption=None, cap_size=22):
    h, w = img.shape[:2]
    lines = wrap(caption, "medium", cap_size, w - 6) if caption else []
    lh = int(cap_size * 1.3)
    bb = max(bottom if bottom else border, border + len(lines) * lh + 8 if lines else 0)
    card = np.empty((h + border + bb, w + 2 * border, 4), np.uint8)
    card[..., :3] = WHITE
    card[..., 3] = 255
    card[border:border + h, border:border + w, :3] = img
    y = border + h + (bb - len(lines) * lh) / 2 - 3
    for ln in lines:                       # captions wrap rather than run off the print
        spr, _ = text_sprite(ln, "medium", cap_size, INK_SOFT)
        blit(card, spr, border - 2, y)
        y += lh
    return card


def archival(img, sat=0.82, warm=0.06):
    """Gentle print look so photos sit on the paper: lifted blacks, warmer, less saturated."""
    x = img.astype(np.float32)
    g = x.mean(axis=2, keepdims=True)
    x = g + (x - g) * sat
    x = x * np.array([1 + warm, 1.0, 1 - warm * 1.4], np.float32)
    x = 14 + x * (236 / 255)
    return np.clip(x, 0, 255).astype(np.uint8)


def torn_card(rgba, seed=1, amp=5):
    """Rough, torn-paper edge mask for cut-out cards."""
    h, w = rgba.shape[:2]
    rng = np.random.default_rng(seed)
    mask = np.zeros((h, w), np.uint8)
    n = 60

    def edge(length):
        v = np.cumsum(rng.normal(0, 1, n))
        v = (v - v.mean()) / (np.abs(v).max() + 1e-6) * amp
        return np.interp(np.linspace(0, n - 1, length), np.arange(n), v)
    top, bot = edge(w), edge(w)
    pts = [(x, amp + top[x]) for x in range(0, w, 4)] + [(w - 1, h - 1 - amp + bot[-1])] + \
          [(x, h - 1 - amp + bot[x]) for x in range(w - 1, -1, -4)]
    cv2.fillPoly(mask, [np.array(pts, np.int32)], 255, cv2.LINE_AA)
    out = rgba.copy()
    out[..., 3] = np.minimum(out[..., 3], mask)
    return out


# ------------------------------------------------------------------ marker & ink
def _rng(seed):
    return np.random.default_rng(seed)


@lru_cache(maxsize=256)
def marker_stroke(w, h, seed=0, color=YELLOW):
    """A yellow highlighter stroke, slightly uneven, as an RGBA sprite."""
    w, h = int(max(w, 4)), int(max(h, 4))
    rng = _rng(seed)
    a = np.zeros((h + 8, w + 8), np.float32)
    top = 4 + rng.normal(0, 1, 8).cumsum() * 0.6
    bot = h + 4 + rng.normal(0, 1, 8).cumsum() * 0.6
    xs = np.linspace(0, w + 7, 8)
    pts = [(x, y) for x, y in zip(xs, top)] + [(x, y) for x, y in zip(xs[::-1], bot[::-1])]
    cv2.fillPoly(a, [np.array(pts, np.int32)], 1.0, cv2.LINE_AA)
    streak = cv2.resize(rng.normal(0, 1, (6, 1)).astype(np.float32), (w + 8, h + 8)) * 0.06
    a = np.clip(a * (0.86 + streak), 0, 1)
    a[:, :6] *= np.linspace(0.3, 1, 6)[None, :]
    out = np.zeros((h + 8, w + 8, 4), np.uint8)
    out[..., :3] = color
    out[..., 3] = (a * 255).astype(np.uint8)
    return out


def highlight(frame, x0, y0, x1, y1, u, seed=0, color=YELLOW, alpha=0.9):
    """Sweep a marker stroke over the box (x0, y0)-(x1, y1); u is 0..1 progress."""
    if u <= 0:
        return
    w, h = int(x1 - x0), int(y1 - y0)
    spr = marker_stroke(w, h, seed, color)
    cut = int(spr.shape[1] * clamp(u))
    if cut < 2:
        return
    part = spr[:, :cut].copy()
    tip = min(10, cut)
    part[:, -tip:, 3] = (part[:, -tip:, 3] * np.linspace(1, 0.5, tip)[None, :]).astype(np.uint8)
    multiply(frame, part, x0 - 4, y0 - 4, alpha)


def wobble_path(points, seed=0, amp=2.0):
    rng = _rng(seed)
    p = np.array(points, np.float32)
    n = len(p)
    noise = cv2.GaussianBlur(rng.normal(0, 1, (n, 2)).astype(np.float32), (0, 0), 3)
    return p + noise * amp


def draw_path(frame, points, u, color=ACCENT, thick=7, seed=0, alpha=1.0):
    """Draw a polyline progressively (0..1), with a hand-made wobble."""
    if u <= 0 or len(points) < 2:
        return
    p = wobble_path(points, seed)
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    total = seg.sum()
    upto = total * clamp(u)
    acc, out = 0.0, [p[0]]
    for i, s in enumerate(seg):
        if acc + s >= upto:
            f = (upto - acc) / max(s, 1e-6)
            out.append(p[i] + (p[i + 1] - p[i]) * f)
            break
        out.append(p[i + 1])
        acc += s
    pts = np.array(out, np.float32)
    x0, y0 = pts.min(0) - thick * 2
    x1, y1 = pts.max(0) + thick * 2

    def dr(ov, ox, oy):
        q = (pts - [ox, oy]).astype(np.int32)
        cv2.polylines(ov, [q], False, color, thick, cv2.LINE_AA)
        cv2.circle(ov, tuple(q[-1]), thick // 2, color, -1, cv2.LINE_AA)
    overlay(frame, alpha, dr, (x0, y0, x1, y1))


def ellipse_points(cx, cy, rx, ry, turns=1.12, start=-100, seed=0, n=90):
    rng = _rng(seed)
    ang = np.radians(start) + np.linspace(0, 2 * math.pi * turns, n)
    jit = 1 + cv2.GaussianBlur(rng.normal(0, 1, (n, 1)).astype(np.float32), (0, 0), 5)[:, 0] * 0.08
    grow = np.linspace(1.0, 1.08, n)
    return [(cx + math.cos(a) * rx * j * g, cy + math.sin(a) * ry * j * g) for a, j, g in zip(ang, jit, grow)]


def circle_draw(frame, cx, cy, rx, ry, u, color=ACCENT, thick=7, seed=0, alpha=1.0):
    draw_path(frame, ellipse_points(cx, cy, rx, ry, seed=seed), u, color, thick, seed, alpha)


def underline(frame, x0, x1, y, u, color=ACCENT, thick=6, seed=0):
    xs = np.linspace(x0, x1, 30)
    pts = [(x, y + math.sin(i * 0.4 + seed) * 2) for i, x in enumerate(xs)]
    draw_path(frame, pts, ease_out(u), color, thick, seed)


def arrow_draw(frame, p0, p1, u, color=ACCENT, thick=7, seed=0, bend=0.18):
    p0, p1 = np.array(p0, float), np.array(p1, float)
    mid = (p0 + p1) / 2 + np.array([-(p1 - p0)[1], (p1 - p0)[0]]) * bend
    ts = np.linspace(0, 1, 40)[:, None]
    curve = (1 - ts) ** 2 * p0 + 2 * (1 - ts) * ts * mid + ts ** 2 * p1
    draw_path(frame, curve, clamp(u / 0.8), color, thick, seed)
    hu = clamp((u - 0.8) / 0.2)
    if hu > 0:
        d = curve[-1] - curve[-4]
        d /= np.linalg.norm(d) + 1e-6
        n = np.array([-d[1], d[0]])
        L = 26 * hu
        for s in (1, -1):
            q = curve[-1] - d * L + n * L * 0.55 * s
            draw_path(frame, [curve[-1], q], 1.0, color, thick, seed + s)


def overlay(frame, alpha, draw, bbox):
    if alpha <= 0.003:
        return
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


# ------------------------------------------------------------------ labels
def label(frame, s, x, y, t, t0, size=30, name="bold", fg=INK, bg=WHITE, anchor="lb", pad=(16, 10),
          rot=0.0, bar=None):
    """A label chip that pops in (overshoot) at t0. bar = accent colour strip on the left."""
    u = lin(t, t0, t0 + 0.32)
    if u <= 0:
        return
    spr, _ = text_sprite(s, name, size, fg)
    tw, th = spr.shape[1], spr.shape[0]
    bw, bh = tw + 2 * pad[0] + (8 if bar else 0), th + 2 * pad[1] - 8
    card = np.zeros((bh, bw, 4), np.uint8)
    card[..., :3] = bg
    card[..., 3] = 255
    if bar:
        card[:, :8, :3] = bar
    blit(card, spr, pad[0] + (8 if bar else 0) - 4, (bh - th) / 2)
    sc = back_out(u, 2.2)
    cx = x + {"l": bw / 2, "c": 0, "r": -bw / 2}[anchor[0]]
    cy = y + {"t": bh / 2, "m": 0, "b": -bh / 2}[anchor[1]]
    cx = clamp(cx, bw / 2 + 24, frame.shape[1] - bw / 2 - 24)      # never leave the frame
    cy = clamp(cy, bh / 2 + 20, frame.shape[0] - bh / 2 - 20)
    place(frame, card, cx, cy, sc, rot, alpha=clamp(u * 3), shadow=0.28, shadow_off=(5, 7), shadow_blur=8)
    return bw, bh


def pulse_marker(frame, x, y, t, t0, color=ACCENT, r=13):
    u = lin(t, t0, t0 + 0.35)
    if u <= 0:
        return
    rr = r * back_out(u, 2.5)
    for k in range(2):
        ph = ((t - t0) * 0.9 + k * 0.5) % 1.0
        rad = rr + ph * 46
        a = (1 - ph) * 0.55 * u

        def dr(ov, ox, oy, rad=rad):
            cv2.circle(ov, (int(x - ox), int(y - oy)), int(rad), color, 3, cv2.LINE_AA)
        overlay(frame, a, dr, (x - rad - 4, y - rad - 4, x + rad + 4, y + rad + 4))

    def dot(ov, ox, oy):
        cv2.circle(ov, (int(x - ox), int(y - oy)), int(rr), WHITE, -1, cv2.LINE_AA)
        cv2.circle(ov, (int(x - ox), int(y - oy)), int(rr * 0.68), color, -1, cv2.LINE_AA)
    overlay(frame, 1.0, dot, (x - rr - 3, y - rr - 3, x + rr + 3, y + rr + 3))


def stamp(frame, s, cx, cy, t, t0, size=74, color=ACCENT, rot=-7):
    u = lin(t, t0, t0 + 0.22)
    if u <= 0:
        return
    spr, _ = text_sprite(s, "black", size, color, 4)
    h, w = spr.shape[:2]
    box = np.zeros((h + 36, w + 48, 4), np.uint8)
    cv2.rectangle(box, (5, 5), (w + 42, h + 30), tuple(color) + (255,), 7, cv2.LINE_AA)
    blit(box, spr, 24, 18)
    rng = _rng(len(s))
    grain = (rng.random(box.shape[:2]) > 0.18).astype(np.uint8)
    box[..., 3] = box[..., 3] * grain
    sc = lerp(1.6, 1.0, ease_out(u))
    place(frame, box, cx, cy, sc, rot, alpha=clamp(u * 1.5) * 0.92, shadow=0)


# ------------------------------------------------------------------ finishing
_rng_f = np.random.default_rng(11)
GRAIN = [cv2.resize(_rng_f.normal(0, 1.3, (H // 2, W // 2)).astype(np.float32), (W, H))[..., None]
         for _ in range(5)]


def finish(frame, i):
    g = GRAIN[i % len(GRAIN)]
    out = frame.astype(np.float32) + g
    return np.clip(out, 0, 255).astype(np.uint8)
