"""Editing effects: transitions, camera shake, archive-film look, light leaks, glitch.

All functions work on uint8/float32 numpy RGB frames of size H x W.
"""
import functools, math
import numpy as np
from PIL import Image, ImageFilter

from common import W, H, ease, ease_in_out


# ---------------------------------------------------------------- transitions
def dissolve(a, b, x):
    k = ease(x)
    return a * (1 - k) + b * k


def dip(a, b, x, color=0.0):
    if x < 0.5:
        k = ease(x * 2)
        return a * (1 - k) + color * k
    k = ease(x * 2 - 1)
    return color * (1 - k) + b * k


def flash(a, b, x):
    """Hard cut hidden under a white flash peaking at the midpoint."""
    base = a if x < 0.5 else b
    w = max(0.0, 1 - abs(x - 0.5) * 2) ** 1.5
    return base * (1 - w) + 255 * w


def _blur_x(img, px):
    if px < 1:
        return img
    k = int(px) | 1
    c = np.cumsum(np.pad(img, ((0, 0), (k, k), (0, 0)), mode="edge"), axis=1, dtype=np.float32)
    return (c[:, k + k // 2 + 1: k + k // 2 + 1 + W] - c[:, k // 2 + 1: k // 2 + 1 + W]) / k


def whip(a, b, x, direction=1):
    """Whip pan: old shot slides out, new shot slides in, with motion blur."""
    e = ease_in_out(x)
    off = int(e * W) * direction
    out = np.empty_like(a)
    if direction > 0:
        out[:, :W - off] = a[:, off:] if off < W else a[:, :0]
        out[:, W - off:] = b[:, :off]
    else:
        off = -off
        out[:, off:] = a[:, :W - off]
        out[:, :off] = b[:, W - off:]
    speed = math.sin(math.pi * x)
    return _blur_x(out, 90 * speed)


def zoom_through(a, b, x):
    """Punch through the old shot into the new one."""
    if x < 0.5:
        k = ease(x * 2)
        return zoom_frame(a, 1 + 0.35 * k) * (1 - 0.6 * k) + 255 * 0.6 * k * 0.15
    k = ease((x - 0.5) * 2)
    return zoom_frame(b, 1.25 - 0.25 * k) * (0.55 + 0.45 * k)


def glitch_cut(a, b, x, n):
    base = a if x < 0.5 else b
    amt = max(0.0, 1 - abs(x - 0.5) * 2)
    return glitch(base, amt, n)


def burn(a, b, x, n):
    """Film burn: hot orange bloom washes over the cut."""
    base = a if x < 0.5 else b
    w = max(0.0, 1 - abs(x - 0.5) * 2)
    leak = light_leak(n, strength=1.0)
    return np.clip(base * (1 - 0.5 * w) + leak * (1.6 * w) + 255 * (w ** 3) * 0.6, 0, 255)


TRANSITIONS = {"dissolve", "black", "white", "flash", "whip", "whip_l", "zoom", "glitch", "burn", "cut"}


def transition(kind, a, b, x, n):
    a = a.astype(np.float32)
    b = b.astype(np.float32)
    if kind == "dissolve":
        out = dissolve(a, b, x)
    elif kind == "black":
        out = dip(a, b, x, 0.0)
    elif kind == "flash":
        out = flash(a, b, x)
    elif kind == "whip":
        out = whip(a, b, x, 1)
    elif kind == "whip_l":
        out = whip(a, b, x, -1)
    elif kind == "zoom":
        out = zoom_through(a, b, x)
    elif kind == "glitch":
        out = glitch_cut(a, b, x, n)
    elif kind == "burn":
        out = burn(a, b, x, n)
    else:
        out = b
    return np.clip(out, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- frame effects
def zoom_frame(arr, z, cx=0.5, cy=0.5):
    if abs(z - 1) < 1e-3:
        return arr
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    cw, ch = W / z, H / z
    x0 = min(max(cx * W - cw / 2, 0), W - cw)
    y0 = min(max(cy * H - ch / 2, 0), H - ch)
    return np.asarray(im.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)), dtype=np.float32)


def shake(arr, lt, hits, amp=22.0, decay=6.0):
    """Camera shake after impact times (seconds, shot-local)."""
    dx = dy = 0.0
    for t0 in hits:
        u = lt - t0
        if 0 <= u < 1.2:
            e = amp * math.exp(-decay * u)
            dx += e * math.sin(u * 61.0 + t0)
            dy += e * math.cos(u * 47.0 + 2 * t0)
    if abs(dx) < 0.5 and abs(dy) < 0.5:
        return arr
    z = 1 + 2.2 * (abs(dx) + abs(dy)) / W
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    cw, ch = W / z, H / z
    x0 = (W - cw) / 2 - dx / z
    y0 = (H - ch) / 2 - dy / z
    x0 = min(max(x0, 0), W - cw)
    y0 = min(max(y0, 0), H - ch)
    return np.asarray(im.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)))


def glitch(arr, amt, n):
    if amt <= 0.02:
        return arr
    rng = np.random.default_rng(n * 7919)
    out = np.array(arr, dtype=np.float32, copy=True)
    s = int(30 * amt)
    out[..., 0] = np.roll(out[..., 0], s, axis=1)
    out[..., 2] = np.roll(out[..., 2], -s, axis=1)
    for _ in range(int(8 * amt) + 1):
        y = rng.integers(0, H - 40)
        h = rng.integers(8, 60)
        out[y:y + h] = np.roll(out[y:y + h], int(rng.integers(-120, 120) * amt), axis=1)
    if rng.random() < amt * 0.5:
        out = out * 0.75 + 255 * 0.25 * (rng.random() < 0.5)
    return out


@functools.lru_cache(maxsize=1)
def _leak_blobs():
    rng = np.random.default_rng(42)
    small = np.zeros((54, 96, 3), np.float32)
    yy, xx = np.mgrid[0:54, 0:96]
    for _ in range(5):
        cx, cy, r = rng.uniform(0, 96), rng.uniform(0, 54), rng.uniform(12, 30)
        col = np.array([255, rng.uniform(90, 160), rng.uniform(20, 60)], np.float32)
        small += np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r))[..., None] * col
    return small


def light_leak(n, strength=0.5):
    """Warm, drifting light leak (additive). Returns float32 H x W x 3."""
    base = _leak_blobs()
    shift = int((n * 0.7) % 96)
    sm = np.roll(base, shift, axis=1)
    big = np.asarray(Image.fromarray(np.clip(sm, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC),
                     dtype=np.float32)
    flick = 0.75 + 0.25 * math.sin(n * 0.37) * math.sin(n * 0.11)
    return big * strength * flick


@functools.lru_cache(maxsize=1)
def _dust_bank():
    """Pre-drawn dust/scratch layers for an old-film look (alpha masks)."""
    rng = np.random.default_rng(1950)
    bank = []
    for k in range(16):
        im = Image.new("L", (W, H), 0)
        from PIL import ImageDraw
        d = ImageDraw.Draw(im)
        for _ in range(rng.integers(6, 18)):
            x, y, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1, 4)
            d.ellipse([x - r, y - r, x + r, y + r], fill=int(rng.uniform(90, 200)))
        for _ in range(rng.integers(0, 3)):
            x = rng.uniform(0, W)
            d.line([(x, 0), (x + rng.uniform(-6, 6), H)], fill=int(rng.uniform(40, 110)), width=1)
        for _ in range(rng.integers(0, 2)):
            x, y = rng.uniform(0, W), rng.uniform(0, H)
            pts = [(x + i * 6 + rng.uniform(-3, 3), y + rng.uniform(-8, 8)) for i in range(int(rng.uniform(4, 14)))]
            d.line(pts, fill=int(rng.uniform(80, 160)), width=1)
        bank.append(np.asarray(im.filter(ImageFilter.GaussianBlur(0.6)), dtype=np.float32)[..., None] / 255.0)
    return bank


def film_look(arr, n, strength=1.0):
    """Dust, hairline scratches and exposure flicker of old film stock."""
    rng = np.random.default_rng(n)
    out = arr.astype(np.float32)
    flick = 1 + (rng.random() - 0.5) * 0.06 * strength
    out *= flick
    if rng.random() < 0.55 * strength:
        m = _dust_bank()[int(rng.integers(0, 16))]
        dark = rng.random() < 0.7
        out = out * (1 - m * 0.8) + (0 if dark else 230) * m * 0.8
    return out
