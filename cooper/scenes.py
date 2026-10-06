"""Scenes for "The Calmest Man on the Plane" — a behavioural breakdown of the
1971 D.B. Cooper hijacking, told in the style of a true-crime analysis channel.

All on-screen text is typewriter type (Special Elite for headlines, Courier
Prime for captions) and types itself on, one keystroke at a time. Strings come
from strings.py, so the same scenes render the English and the Czech cut
(FILM_LANG=en|cs).

Archival stills: FBI and 1971 press photos (public domain), aircraft photo
(GFDL). B-roll: NASA (public domain). Map: Natural Earth (public domain).
"""
import json
import math
import os
import sys
import zlib
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fx import (FPS, H, W, Clip, View, blit, canvas, clamp, darken, ease_out, fill_rect,  # noqa
                font, lerp, lin, line, mix, overlay, paste, smooth, text_rgba)
from strings import CARR_HOT_WORDS, LANG, QUOTE_HOT_WORDS, L, N, money  # noqa: E402

import fx  # noqa: E402

if LANG == "en":
    from narration import SEGMENTS  # noqa: E402
else:
    from narration_cs import SEGMENTS  # noqa: E402

ASSETS = os.path.join(ROOT, "build", "cooper", "assets")
fx.FOOTAGE = ASSETS            # Clip() looks here for the NASA b-roll
CURRENT = None                 # the scene being rendered (for keystroke sounds)

INK = (8, 8, 10)
RED = (225, 38, 38)
YEL = (255, 210, 40)
WHITE = (240, 238, 232)
GREY = (150, 150, 150)
GREEN = (80, 210, 120)
TERM = (60, 200, 110)
PAPER = (226, 219, 200)
INKED = (34, 31, 28)
TEXT = dict(SEGMENTS)
HEAD, BODY, BOLD = "tw", "cp", "cp_bold"    # Special Elite, Courier Prime, Courier Prime Bold


# ------------------------------------------------------------------ typewriter text
@lru_cache(maxsize=6000)
def typed_line(s, name, size, color):
    """Render a line with slight per-key jitter and ink variation (like a real
    typewriter), plus the x position where each character starts."""
    f = font(name, size)
    asc, desc = f.getmetrics()
    xs = [6.0]
    for ch in s:
        xs.append(xs[-1] + f.getlength(ch))
    top = PAD_TOP(size)         # headroom for accents on capitals (Ě, Š, Í, Ž ...)
    img = Image.new("RGBA", (int(xs[-1]) + 12, top + asc + desc + 12), color + (0,))
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(zlib.crc32(f"{s}|{name}|{size}".encode()))
    for i, ch in enumerate(s):
        jy = rng.uniform(-1.0, 1.0) * size / 55
        ink = int(255 * rng.uniform(0.8, 1.0))
        d.text((xs[i], top + 6 + jy), ch, font=f, fill=color + (ink,))
    return np.array(img), tuple(xs)


def PAD_TOP(size):
    return int(size * 0.32)


def _place(img, x, y, size, anchor):
    """Top-left corner for an anchor, ignoring the accent headroom."""
    h, w = img.shape[:2]
    top = PAD_TOP(size)
    core = h - top
    X = x - (w / 2 if anchor[0] == "c" else w if anchor[0] == "r" else 0)
    Y = y - (core / 2 if anchor[1] == "m" else core if anchor[1] == "b" else 0) - top
    return X, Y, top


def cps_for(size):
    return clamp(1500 / size, 16, 42)


def type_text(f, s, x, y, size, color, t, t0, name=HEAD, anchor="lt", cps=None, alpha=1.0,
              cursor=True, shadow=True, sound=True):
    """Type a line on, one keystroke at a time. Returns the full line width."""
    if not s or t < t0 or alpha <= 0.003:
        return 0
    cps = cps or cps_for(size)
    img, xs = typed_line(s, name, int(size), tuple(color))
    h, w = img.shape[:2]
    n = min(len(s), int((t - t0) * cps) + 1)
    X, Y, top = _place(img, x, y, int(size), anchor)
    clip = (int(X), 0, int(X + xs[n]), H)
    if shadow:
        sh, _ = typed_line(s, name, int(size), (0, 0, 0))
        blit(f, sh, round(X) + max(2, size // 22), round(Y) + max(2, size // 18), 0.75 * alpha,
             (clip[0] + 4, 0, clip[2] + 4, H))
    blit(f, img, round(X), round(Y), alpha, clip)
    done = t0 + len(s) / cps
    if cursor and (n < len(s) or (t - done < 0.7 and int((t - done) * 3) % 2 == 0)):
        cx, core = X + xs[n] + 2, h - top
        fill_rect(f, cx, Y + top + core * 0.18, cx + size * 0.5, Y + top + core * 0.8, color,
                  0.8 * alpha)
    if sound and CURRENT is not None:
        gain = 0.42 if size >= 70 else 0.26
        for i in range(n):
            if s[i] != " " and (size >= 40 or i % 2 == 0):
                CURRENT.event(t0 + i / cps, "type" if size < 70 else "type_heavy", gain,
                              key=("k", s, round(t0, 2), i))
        if n == len(s) and size >= 70:
            CURRENT.event(done + 0.05, "carriage_soft", 0.5, key=("ret", s, round(t0, 2)))
    return w


def typed_width(s, size, name=HEAD):
    return typed_line(s, name, int(size), (255, 255, 255))[0].shape[1]


def static(f, s, x, y, size, color, alpha=1.0, name=BODY, anchor="lt"):
    """Already-typed text (no animation)."""
    if alpha <= 0.003 or not s:
        return 0
    img, _ = typed_line(s, name, int(size), tuple(color))
    X, Y, _ = _place(img, x, y, int(size), anchor)
    blit(f, img, round(X), round(Y), alpha)
    return img.shape[1]


# ------------------------------------------------------------------ helpers
def load(name):
    for cand in ("x_" + name, name):
        p = os.path.join(ASSETS, cand)
        if os.path.exists(p):
            try:
                return np.array(Image.open(p).convert("RGB"))
            except Exception:
                pass
    raise FileNotFoundError(name)


def best(*names):
    """Largest available of several versions of the same image."""
    out = None
    for n in names:
        try:
            im = load(n)
        except FileNotFoundError:
            continue
        if out is None or im.shape[0] * im.shape[1] > out.shape[0] * out.shape[1]:
            out = im
    return out


_CURVE = np.clip(255 * (0.5 + 0.5 * np.tanh(1.6 * (np.arange(256) / 255 - 0.52) * 2)
                        / np.tanh(1.6)), 0, 255).astype(np.uint8)


def crime_grade(img, sat=0.3, bright=0.9, tint=(0.94, 1.0, 1.08)):
    """Cold, crushed, desaturated true-crime grade."""
    out = cv2.LUT(img, _CURVE)
    g = cv2.cvtColor(cv2.cvtColor(out, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB)
    out = cv2.addWeighted(out, sat, g, 1 - sat, 0)
    return cv2.multiply(out, (tint[0] * bright, tint[1] * bright, tint[2] * bright, 0))


_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / (W / 2)) ** 2 + ((_yy - H / 2) / (H / 2)) ** 2)
HEAVY_VIG = np.repeat((np.clip(1.05 - 0.55 * _r ** 1.8, 0.18, 1) * 255).astype(np.uint8)[..., None],
                      3, axis=2)
del _yy, _xx, _r


def vignette(f):
    cv2.multiply(f, HEAVY_VIG, dst=f, scale=1 / 255)
    return f


def kenburns(img, t, D, z0=1.0, z1=1.12, c0=None, c1=None, rect=(0, 0, W, H)):
    h, w = img.shape[:2]
    u = smooth(t / D) if D > 0 else 1
    c0 = c0 or (w / 2, h / 2)
    c1 = c1 or c0
    v = View(w, h, rect=rect, zoom=lerp(z0, z1, u),
             center=(lerp(c0[0], c1[0], u), lerp(c0[1], c1[1], u)))
    return v.render(img, cv2.INTER_CUBIC), v


def photo_frame(f, img, t, D, cx, cy, hgt, z0=1.0, z1=1.08, tilt=0.0, border=10, appear=1.0,
                c0=None, c1=None, sat=0.3):
    """An archival print laid on the dark background, slowly pushing in."""
    h, w = img.shape[:2]
    pw, ph = int(hgt * w / h), int(hgt)
    sub, v = kenburns(img, t, D, z0, z1, c0, c1, rect=(0, 0, pw, ph))
    sub = crime_grade(sub, sat=sat, bright=1.0)
    card = np.full((ph + 2 * border, pw + 2 * border, 3), (205, 200, 188), np.uint8)
    card[border:border + ph, border:border + pw] = sub
    if tilt:
        m = cv2.getRotationMatrix2D((card.shape[1] / 2, card.shape[0] / 2), tilt, 1.0)
        card = cv2.warpAffine(card, m, (card.shape[1], card.shape[0]), borderValue=(0, 0, 0))
    k = ease_out(appear)
    if k < 1:
        card = cv2.convertScaleAbs(card, alpha=k)
    x0, y0 = int(cx - card.shape[1] / 2), int(cy - card.shape[0] / 2)
    fill_rect(f, x0 + 14, y0 + 18, x0 + card.shape[1] + 14, y0 + card.shape[0] + 18, (0, 0, 0),
              0.55 * k)
    mask = card.sum(axis=2) > 0
    region = f[max(y0, 0):y0 + card.shape[0], max(x0, 0):x0 + card.shape[1]]
    oy, ox = max(-y0, 0), max(-x0, 0)
    sub_card = card[oy:oy + region.shape[0], ox:ox + region.shape[1]]
    sub_mask = mask[oy:oy + region.shape[0], ox:ox + region.shape[1]]
    region[sub_mask] = sub_card[sub_mask]

    def pt(px, py):
        X, Y = v.pt(px, py)
        return x0 + border + X, y0 + border + Y
    return pt, (x0, y0, x0 + card.shape[1], y0 + card.shape[0])


def circle_draw(f, cx, cy, rx, ry, u, color=RED, thick=6):
    """Hand-drawn style red circle that draws itself on (u: 0..1)."""
    if u <= 0:
        return
    end = -100 + 380 * ease_out(u)
    for k, (dx, dy, dr) in enumerate(((0, 0, 0), (3, -2, 5))):
        cv2.ellipse(f, (int(cx + dx), int(cy + dy)), (int(rx + dr), int(ry - dr * 0.6)),
                    -8 + k * 4, -100, end, color, thick - 2 * k, cv2.LINE_AA)


def arrow_draw(f, p0, p1, u, color=RED, thick=6):
    if u <= 0:
        return
    p = (lerp(p0[0], p1[0], ease_out(u)), lerp(p0[1], p1[1], ease_out(u)))
    cv2.arrowedLine(f, (int(p0[0]), int(p0[1])), (int(p[0]), int(p[1])), color, thick, cv2.LINE_AA,
                    tipLength=0.18 if u > 0.6 else 0.0)


def check(f, x, y, size, ok, u):
    """Draw a check mark (ok) or a cross, drawn on with u in 0..1."""
    if u <= 0:
        return
    u = ease_out(u)
    if ok:
        a, b, c = (x, y), (x + size * 0.35, y + size * 0.4), (x + size, y - size * 0.5)
        line(f, a, (lerp(a[0], b[0], min(u * 2, 1)), lerp(a[1], b[1], min(u * 2, 1))), GREEN, 7)
        if u > 0.5:
            v = (u - 0.5) * 2
            line(f, b, (lerp(b[0], c[0], v), lerp(b[1], c[1], v)), GREEN, 7)
    else:
        s = size / 2
        line(f, (x - s, y - s), (lerp(x - s, x + s, min(u * 2, 1)), lerp(y - s, y + s, min(u * 2, 1))),
             RED, 8)
        if u > 0.5:
            v = (u - 0.5) * 2
            line(f, (x + s, y - s), (lerp(x + s, x - s, v), lerp(y - s, y + s, v)), RED, 8)


def stamp(word, color=RED, size=80, angle=-9):
    f = font(BOLD, size)
    w = int(f.getlength(word)) + 70
    img = Image.new("RGBA", (w, size + 60), color + (0,))
    d = ImageDraw.Draw(img)
    d.rectangle((5, 5, w - 6, size + 54), outline=color + (255,), width=8)
    d.text((35, 14), word, font=f, fill=color + (255,))
    a = np.array(img)
    rng = np.random.default_rng(len(word))
    holes = cv2.GaussianBlur(rng.random(a.shape[:2]).astype(np.float32), (0, 0), 1.6)
    a[..., 3] = (a[..., 3] * np.clip((holes - 0.36) * 6, 0.2, 1)).astype(np.uint8)
    return np.array(Image.fromarray(a).rotate(angle, expand=True, resample=Image.BICUBIC))


def stamp_at(f, img, cx, cy, t, t0):
    if t < t0:
        return
    k = 1 + 0.7 * (1 - ease_out(lin(t, t0, t0 + 0.12)))
    im = img if k < 1.01 else cv2.resize(img, None, fx=k, fy=k)
    blit(f, im, cx - im.shape[1] / 2, cy - im.shape[0] / 2, 0.92 * lin(t, t0, t0 + 0.05))


def flash(f, t, t0, dur=0.12):
    if t0 <= t < t0 + dur:
        k = 1 - (t - t0) / dur
        cv2.addWeighted(f, 1 - 0.85 * k, np.full_like(f, 255), 0.85 * k, 0, dst=f)


def shake(f, t, t0, dur=0.5, amp=18):
    if t0 <= t < t0 + dur:
        k = (1 - (t - t0) / dur) ** 2
        dx, dy = amp * k * math.sin(t * 90), amp * k * math.cos(t * 77)
        m = np.float32([[1.03, 0, dx - W * 0.015], [0, 1.03, dy - H * 0.015]])
        return cv2.warpAffine(f, m, (W, H), borderMode=cv2.BORDER_REPLICATE)
    return f


def rgb_split(f, amount):
    k = int(amount)
    if k:
        f[..., 0] = np.roll(f[..., 0], k, axis=1)
        f[..., 2] = np.roll(f[..., 2], -k, axis=1)
    return f


def lower_third(f, t, t0, lines, x=90, y=860):
    """Case-file caption, typed line after line."""
    if t < t0:
        return
    a = lin(t, t0, t0 + 0.2)
    fill_rect(f, x - 20, y - 20, x + 860, y + 46 * len(lines) + 12, (0, 0, 0), 0.6 * a)
    fill_rect(f, x - 20, y - 20, x - 14, y + 46 * len(lines) + 12, RED, a)
    tt = t0 + 0.1
    for k, (s, col, size) in enumerate(lines):
        type_text(f, s, x, y + k * 46, size, col, t, tt, name=BOLD, cps=38, shadow=False,
                  cursor=k == len(lines) - 1)
        tt += len(s) / 38 + 0.1


def caption(f, t, t0, t1, words, hot=(), y=900, size=60):
    """Subtitles typed on in time with the narration; `hot` words in red."""
    if t < t0 - 0.05:
        return
    total = sum(len(w) + 1 for w in words)
    times, acc = [], 0
    for w in words:
        times.append(t0 + (t1 - t0) * acc / total)
        acc += len(w) + 1
    rows, cur = [], []
    for w in words:
        if typed_width(" ".join(cur + [w]), size) > W - 300 and cur:
            rows.append(cur)
            cur = [w]
        else:
            cur.append(w)
    rows.append(cur)
    k = 0
    for r, row in enumerate(rows):
        widths = [typed_width(w + " ", size) for w in row]
        x = W / 2 - sum(widths) / 2
        yy = y - (len(rows) - 1 - r) * size * 1.25
        for w, wd in zip(row, widths):
            col = RED if w.strip(".,!?").lower() in hot else WHITE
            type_text(f, w, x, yy, size, col, t, times[k], anchor="lm", cps=30,
                      cursor=k == len(words) - 1)
            x += wd
            k += 1


class Words:
    """Estimate when each word of a narrated sentence is spoken."""

    def __init__(self, scene_key, starts, voice_end):
        self.sent = TEXT[scene_key]
        self.starts = starts
        self.ends = [s - 0.3 for s in starts[1:]] + [voice_end]

    def at(self, i, key, offset=0.0):
        s = self.sent[i]
        j = s.lower().find(N(key).lower())
        frac = j / max(len(s), 1) if j >= 0 else 0
        return self.starts[i] + (self.ends[i] - self.starts[i]) * frac + offset


# ------------------------------------------------------------------ base scene
class Scene:
    def __init__(self, spec):
        self.D = spec["dur"]
        self.S = spec["sentences"]
        self.key = spec["key"]
        self.sfx = []
        self._seen = set()
        if self.S:
            self.w = Words(self.key, self.S, spec["voice_end"])

    def event(self, t, kind, gain=1.0, key=None):
        key = key if key is not None else (kind, round(t, 2))
        if key not in self._seen:
            self._seen.add(key)
            self.sfx.append((round(t, 3), kind, gain))

    def fade(self, f, t, fin=0.2, fout=0.25):
        k = 1.0
        if fin:
            k = min(k, lin(t, 0, fin))
        if fout:
            k = min(k, lin(t, self.D, self.D - fout))
        return darken(f, k)


# ------------------------------------------------------------------ 1. hook
class Hook(Scene):
    def __init__(self, spec):
        super().__init__(spec)
        self.sketch = best("D.B._Cooper_FBI_Composite_A.jpg", "Cooper_Composite_A.jpg")

    def frame(self, t):
        S, w = self.S, self.w
        f = canvas(INK)
        dark = lin(t, S[1] - 0.15, S[1]) * (1 - lin(t, S[2] - 0.2, S[2] + 0.2))
        h, wd = self.sketch.shape[:2]
        if t < S[2]:
            pt, box = photo_frame(f, self.sketch, t, S[2], 760, 540, 860, 1.0, 1.1, tilt=-1.5)
        else:
            pt, box = photo_frame(f, self.sketch, t - S[2], self.D - S[2], 760, 540, 860, 1.12,
                                  1.5, tilt=-1.5, c0=(wd / 2, h * 0.42), c1=(wd / 2, h * 0.36))
        type_text(f, L("w_hijacked"), 1260, 300, 96, WHITE, t, w.at(0, "hijacked"), anchor="lm",
                  sound=dark < 0.5)
        type_text(f, L("w_money"), 1260, 430, 104, YEL, t, w.at(0, "money"), anchor="lm",
                  sound=dark < 0.5)
        type_text(f, L("w_vanished"), 1260, 570, 96, RED, t, w.at(0, "jumped"), anchor="lm",
                  sound=dark < 0.5)
        for k in ("hijacked", "money", "jumped"):
            self.event(w.at(0, k), "thud", 0.6)
        if dark > 0:
            f = darken(f, 1 - 0.92 * dark)
            if S[1] <= t < S[2] - 0.2:
                type_text(f, L("never"), W / 2, H / 2, 112, WHITE, t, S[1] + 0.2, anchor="cm")
                self.event(S[1] + 0.2, "boom", 1.0)
        if t >= S[2]:
            tc = w.at(2, "calm")
            ex, ey = pt(wd * 0.5, h * 0.37)
            circle_draw(f, ex, ey, 270, 120, lin(t, tc - 0.3, tc + 0.4))
            type_text(f, L("calm"), 1450, 760, 150, YEL, t, tc, anchor="cm")
            self.event(tc, "hit", 1.0)
        f = vignette(f)
        if self.D - 0.25 < t:
            flash(f, t, self.D - 0.25, 0.25)
            self.event(self.D - 0.25, "whoosh", 0.8)
        return self.fade(f, t, fin=0.4, fout=0.0)


# ------------------------------------------------------------------ 2. title
class Title(Scene):
    def frame(self, t):
        f = canvas(INK)
        g = 14 * (1 - lin(t, 0, 0.4)) * (0.6 + 0.4 * math.sin(t * 70))
        type_text(f, L("title1"), W / 2, 470, 120, WHITE, t, 0.05, anchor="cm", cps=26)
        type_text(f, L("title2"), W / 2, 610, 120, RED, t, 0.05 + len(L("title1")) / 26 + 0.05,
                  anchor="cm", cps=26)
        a = lin(t, 1.5, 1.8)
        line(f, (W / 2 - 330 * a, 700), (W / 2 + 330 * a, 700), RED, 4)
        type_text(f, L("title3"), W / 2, 745, 30, GREY, t, 1.6, name=BOLD, anchor="cm", cps=40,
                  shadow=False)
        f = rgb_split(f, g)
        self.event(0.0, "boom", 1.0)
        return self.fade(f, t, fin=0.0, fout=0.3)


# ------------------------------------------------------------------ 3. note
class Note(Scene):
    def __init__(self, spec):
        super().__init__(spec)
        self.takeoff = Clip("dc8_takeoff")
        self.plane = load("Northwest_Airlines_Boeing_727-51_N467US.jpg")

    def frame(self, t):
        S, w = self.S, self.w
        if t < S[1]:
            img, _ = self.takeoff.at(22.0 + t * 0.85)
            f = crime_grade(View(img.shape[1], img.shape[0], zoom=1.08).render(img), sat=0.25,
                            bright=0.75)
            f = vignette(f)
            lower_third(f, t, 0.5, [(L("lt_date"), RED, 32), (L("lt_flight"), WHITE, 26)])
            tn = w.at(0, "dan")
            if t > tn:
                a = ease_out(lin(t, tn, tn + 0.3))
                fill_rect(f, 1210, 130, 1850, 300, (0, 0, 0), 0.6 * a)
                type_text(f, L("pass_label"), 1240, 146, 24, GREY, t, tn, name=BOLD, shadow=False,
                          cursor=False)
                type_text(f, L("pass_name"), 1240, 178, 66, WHITE, t, tn + 0.25, cursor=False)
                type_text(f, L("pass_sub"), 1240, 258, 24, YEL, t, tn + 0.9, name=BOLD,
                          shadow=False)
        elif t < S[2]:
            lt = t - S[1]
            f = canvas(INK)
            photo_frame(f, self.plane, lt, S[2] - S[1], W / 2, 470, 520, 1.0, 1.15, tilt=1.0,
                        appear=lin(lt, 0, 0.2), sat=0.45)
            self.event(S[1], "shutter", 0.8)
            type_text(f, L("aircraft"), W / 2, 790, 28, GREY, t, S[1] + 0.3, name=BOLD, anchor="cm",
                      shadow=False, cursor=False)
            type_text(f, L("bourbon"), W / 2, 880, 64, WHITE, t, w.at(1, "bourbon"), anchor="cm",
                      cursor=False)
            type_text(f, L("a_note"), W / 2, 970, 64, YEL, t, w.at(1, "note"), anchor="cm")
            f = vignette(f)
        else:
            f = self.note_card(t)
        return self.fade(f, t, fin=0.25, fout=0.2)

    def note_card(self, t):
        S, w = self.S, self.w
        f = canvas((14, 13, 12))
        lt = t - S[2]
        t_open = w.at(2, "isnt")
        opened = lin(t, t_open - 0.05, t_open + 0.25)
        cx, cy = W / 2, 430
        pw, ph = 900, int(lerp(260, 460, ease_out(opened)))
        y_slide = lerp(140, 0, ease_out(lin(lt, 0, 0.4)))
        x0, y0 = cx - pw / 2, cy - ph / 2 + y_slide
        fill_rect(f, x0 + 16, y0 + 20, x0 + pw + 16, y0 + ph + 20, (0, 0, 0), 0.6)
        fill_rect(f, x0, y0, x0 + pw, y0 + ph, PAPER)
        line(f, (x0, y0 + ph / 2), (x0 + pw, y0 + ph / 2), (190, 182, 160), 2)
        self.event(S[2], "paper", 0.9)
        if opened > 0.3:
            t1 = t_open + 0.2
            type_text(f, L("note1"), cx, y0 + 110, 66, INKED, t, t1, anchor="cm", shadow=False,
                      cursor=False)
            type_text(f, L("note2"), cx, y0 + 196, 66, INKED, t, t1 + len(L("note1")) / 22 + 0.1,
                      anchor="cm", shadow=False)
            static(f, L("note_cap"), cx, y0 + ph - 50, 22, (110, 100, 88), lin(opened, 0.6, 1.0),
                   anchor="cm")
            self.event(t_open, "hit", 0.8)
        if t >= S[3]:
            caption(f, t, S[3], self.w.ends[3], TEXT["note"][3].split(), hot=QUOTE_HOT_WORDS,
                    y=900, size=58)
            type_text(f, L("quote_attr"), W / 2, 1010, 24, GREY, t, S[3] + 0.4, name=BODY,
                      anchor="cm", shadow=False, cursor=False, sound=False)
            self.event(w.at(3, "bomb"), "boom", 0.9)
        return vignette(f)


# ------------------------------------------------------------------ 4. demands
def parachute(f, cx, cy, s, color, a=1.0):
    def draw(ov, ox, oy):
        c = (int(cx - ox), int(cy - oy))
        cv2.ellipse(ov, c, (int(70 * s), int(48 * s)), 0, 180, 360, color, -1, cv2.LINE_AA)
        for k in range(-3, 4):
            cv2.line(ov, (int(c[0] + k * 20 * s), c[1]), (c[0], int(c[1] + 110 * s)), color, 2,
                     cv2.LINE_AA)
        cv2.rectangle(ov, (int(c[0] - 14 * s), int(c[1] + 105 * s)),
                      (int(c[0] + 14 * s), int(c[1] + 140 * s)), color, -1)
    overlay(f, a, draw, (cx - 80 * s, cy - 60 * s, cx + 80 * s, cy + 150 * s))


class Demands(Scene):
    def __init__(self, spec):
        super().__init__(spec)
        self.sketch = best("D.B._Cooper_FBI_Composite_A.jpg", "Cooper_Composite_A.jpg")
        self.stamp_plan = stamp(L("a_plan"), RED, 110)

    def frame(self, t):
        S, w = self.S, self.w
        f = canvas(INK)
        if t < S[2]:
            photo_frame(f, self.sketch, t, S[2], 520, 540, 820, 1.0, 1.08, tilt=-1.0,
                        appear=lin(t, 0, 0.25))
            type_text(f, L("analysis"), 980, 200, 28, RED, t, 0.15, name=BOLD, shadow=False,
                      cursor=False)
            type_text(f, L("notice1"), 980, 260, 66, WHITE, t, 0.3, cursor=False)
            type_text(f, L("notice2"), 980, 345, 66, YEL, t, max(0.3 + len(L("notice1")) / cps_for(66),
                                                                  w.at(0, "doesnt") - 0.2))
            items = [(L("item_shout"), w.at(1, "shout")), (L("item_threat"), w.at(1, "threaten")),
                     (L("item_aware"), w.at(1, "realize"))]
            for k, (lab, tk) in enumerate(items):
                y = 520 + k * 110
                if t >= tk - 0.1:
                    type_text(f, lab, 1060, y, 54, WHITE, t, tk - 0.1, anchor="lm", cursor=False)
                    check(f, 1000, y, 50, False, lin(t, tk + 0.25, tk + 0.55))
                    self.event(tk + 0.25, "x", 0.7)
        elif t < S[3]:
            self.ransom_note(f, t)
        elif t < S[4]:
            self.four(f, t)
        else:
            type_text(f, L("not_panic"), W / 2, 400, 110, (120, 120, 120), t, S[4], anchor="cm",
                      cursor=False)
            tp = w.at(4, "panic") + 0.3
            if t > tp:
                hw = typed_width(L("not_panic"), 110) / 2
                line(f, (W / 2 - hw, 400), (W / 2 - hw + 2 * hw * lin(t, tp, tp + 0.25), 400), RED, 10)
            stamp_at(f, self.stamp_plan, W / 2, 650, t, w.at(4, "plan"))
            self.event(w.at(4, "plan"), "stamp", 1.0)
            self.event(S[4], "riser", 0.6)
        return self.fade(vignette(f), t, fin=0.2, fout=0.2)

    def ransom_note(self, f, t):
        S, w = self.S, self.w
        lt = t - S[2]
        x0, y0, x1, y1 = 460, 160, 1460, 900
        k = ease_out(lin(lt, 0, 0.3))
        fill_rect(f, x0 + 18, y0 + 22, x1 + 18, y1 + 22, (0, 0, 0), 0.6 * k)
        fill_rect(f, x0, y0, x1, y1, PAPER, k)
        type_text(f, L("demands"), (x0 + x1) / 2, y0 + 70, 62, INKED, t, S[2] + 0.1, anchor="cm",
                  shadow=False, cursor=False)
        rows = [(L("d_money"), L("d_money_sub"), w.at(2, "two_hundred")),
                (L("d_chutes"), L("d_chutes_sub"), w.at(2, "four_chutes")),
                (L("d_fuel"), L("d_fuel_sub"), w.at(2, "four_chutes") + 0.9)]
        for i, (big, small, tk) in enumerate(rows):
            y = y0 + 200 + i * 190
            type_text(f, big, x0 + 80, y, 76, INKED, t, tk, shadow=False, cursor=False)
            type_text(f, small, x0 + 84, y + 94, 32, (100, 92, 82), t, tk + len(big) / cps_for(76),
                      name=BODY, shadow=False, cursor=False)
        tk = rows[1][2] + 0.5
        if t >= tk:
            cw = typed_width(rows[1][0], 76)
            circle_draw(f, x0 + 80 + cw / 2, y0 + 200 + 190 + 44, cw / 2 + 60, 75, lin(t, tk, tk + 0.4))
            self.event(tk, "marker", 0.6)

    def four(self, f, t):
        S, w = self.S, self.w
        type_text(f, "4", 330, 520, 420, RED, t, S[3], anchor="cm", cursor=False)
        self.event(S[3], "boom", 0.9)
        for k in range(4):
            tk = S[3] + 0.5 + k * 0.18
            if t >= tk:
                cx = 760 + k * 280
                col = WHITE if k == 0 else YEL
                parachute(f, cx, 380, 1.4, col, lin(t, tk, tk + 0.15))
                type_text(f, L("him") if k == 0 else "?", cx, 650, 48, col, t, tk, anchor="cm",
                          cursor=False)
        type_text(f, L("hostage"), 1180, 760, 44, WHITE, t, w.at(3, "hostage"), anchor="cm",
                  cps=40, cursor=False)
        ts = w.at(3, "sabotaged")
        type_text(f, L("tamper"), 1180, 840, 44, RED, t, ts, anchor="cm", cps=40, cursor=False)
        type_text(f, L("deception"), 1180, 930, 32, YEL, t, ts + 0.9, name=BOLD, anchor="cm",
                  shadow=False)


# ------------------------------------------------------------------ 5. orders
def draw_727(f, cx, cy, scale, stair, hl=0.0):
    """Side view of a Boeing 727 (nose left). stair: 0 stowed .. 1 lowered."""
    P = lambda x, y: (int(cx + (x - 500) * scale), int(cy + y * scale))  # noqa: E731
    body, edge = (52, 55, 60), (215, 215, 210)

    def poly(pts, fill, outline=edge, w=2):
        arr = np.array([P(x, y) for x, y in pts], np.int32)
        if fill is not None:
            cv2.fillPoly(f, [arr], fill, cv2.LINE_AA)
        cv2.polylines(f, [arr], True, outline, w, cv2.LINE_AA)

    poly([(740, -38), (905, -38), (1000, -215), (925, -218)], body)          # fin
    poly([(905, -212), (1015, -214), (1004, -200), (915, -199)], body)      # T-tail
    poly([(60, -38), (880, -38), (980, -12), (990, 4), (900, 30), (780, 38), (60, 38)], body)
    cv2.ellipse(f, P(62, 0), (int(62 * scale), int(38 * scale)), 0, 90, 270, body, -1, cv2.LINE_AA)
    cv2.ellipse(f, P(62, 0), (int(62 * scale), int(38 * scale)), 0, 90, 270, edge, 2, cv2.LINE_AA)
    poly([(30, -18), (62, -24), (82, -24), (82, -12), (34, -10)], (20, 22, 26), edge, 1)
    for x in range(140, 760, 24):
        cv2.circle(f, P(x, -14), max(2, int(5 * scale)), (170, 175, 180), -1, cv2.LINE_AA)
    poly([(740, -34), (870, -34), (880, -20), (870, -6), (740, -6)], (70, 74, 80))
    poly([(800, -38), (840, -62), (860, -62), (860, -38)], (70, 74, 80))
    poly([(360, 16), (520, 16), (620, 34), (560, 38)], (70, 74, 80))
    for gx, gy in ((480, 38), (110, 38)):
        line(f, P(gx, gy), P(gx, gy + 48), edge, max(2, int(4 * scale)))
        cv2.circle(f, P(gx, gy + 56), max(3, int(12 * scale)), (30, 30, 32), -1, cv2.LINE_AA)
        cv2.circle(f, P(gx, gy + 56), max(3, int(12 * scale)), edge, 2, cv2.LINE_AA)
    a = math.radians(lerp(-12, 38, ease_out(stair)))
    hx, hy, Ln = 845, 32, 150
    ex, ey = hx + Ln * math.cos(a), hy + Ln * math.sin(a)
    nx, ny = -math.sin(a) * 12, math.cos(a) * 12
    col = mix((120, 124, 130), RED, hl)
    poly([(hx, hy), (ex, ey), (ex + nx, ey + ny), (hx + nx, hy + ny)], col, col, 2)
    for k in range(1, 7):
        sx, sy = hx + (ex - hx) * k / 7, hy + (ey - hy) * k / 7
        line(f, P(sx, sy), P(sx + nx, sy + ny), (30, 30, 32), 2)
    return P(ex, ey)


class Orders(Scene):
    def __init__(self, spec):
        super().__init__(spec)
        self.crew = load("Crew_of_Northwest_Airlines_Flight_305_after_D._B._Cooper_hijacking.jpg")
        self.chase = Clip("dc8_chase")

    def frame(self, t):
        S, w = self.S, self.w
        if t < S[1]:
            f = canvas(INK)
            photo_frame(f, self.crew, t, S[1], W / 2, 450, 600, 1.0, 1.12, appear=lin(t, 0, 0.2),
                        sat=0.0)
            self.event(0.0, "shutter", 0.8)
            type_text(f, L("crew_cap"), W / 2, 800, 24, GREY, t, 0.3, name=BOLD, anchor="cm",
                      shadow=False, cursor=False, cps=48)
            type_text(f, L("released"), W / 2, 885, 54, WHITE, t, w.at(0, "trades"), anchor="cm",
                      cps=34, cursor=False)
            type_text(f, L("onboard"), W / 2, 965, 54, YEL, t, w.at(0, "cash"), anchor="cm", cps=40)
            f = vignette(f)
        elif t < S[2]:
            img, _ = self.chase.at(176 + (t - S[1]) * 0.8)
            f = crime_grade(View(img.shape[1], img.shape[0], zoom=1.1).render(img), sat=0.15,
                            bright=0.45, tint=(0.85, 0.95, 1.12))
            f = vignette(f)
            fill_rect(f, 540, 230, 1380, 850, (4, 8, 6), 0.82)
            cv2.rectangle(f, (540, 230), (1380, 850), TERM, 2)
            type_text(f, L("instr"), 580, 258, 28, TERM, t, S[1], name=BOLD, shadow=False,
                      cursor=False, cps=40)
            rows = [(L("r_dest"), w.at(1, "mexico")), (L("r_alt"), w.at(1, "low")),
                    (L("r_speed"), w.at(1, "slow")), (L("r_gear"), w.at(1, "gear")),
                    (L("r_flaps"), w.at(1, "gear") + 0.5), (L("r_cabin"), w.at(1, "cabin"))]
            for k, ((a_, b_), tk) in enumerate(rows):
                y = 340 + k * 80
                type_text(f, a_ + " " + "." * max(2, 15 - len(a_)), 580, y, 34, TERM, t, tk - 0.15,
                          name=BOLD, shadow=False, cursor=False, cps=60)
                type_text(f, b_, 1340, y, 34, (190, 255, 210), t, tk + 0.1, name=BOLD, anchor="rt",
                          shadow=False, cps=40, cursor=k == len(rows) - 1)
                if t >= tk:
                    self.event(tk, "beep", 0.4)
            self.event(S[1], "static", 0.6)
        else:
            lt = t - S[2]
            f = canvas(INK)
            ts = w.at(2, "stair")
            st = lin(t, ts - 0.2, ts + 1.0)
            end = draw_727(f, W / 2 - 120, 460, 1.3, st, hl=lin(st, 0, 0.3))
            if st > 0.4:
                a = lin(st, 0.4, 0.8)
                lx, ly = end[0] - 120, end[1] + 230
                arrow_draw(f, (lx + 20, ly - 70), (end[0] - 8, end[1] + 14), a)
                type_text(f, L("stair"), lx, ly, 58, RED, t, ts + 0.3, anchor="rt", cursor=False)
                type_text(f, L("stair_sub"), lx, ly + 70, 28, WHITE, t, ts + 0.9, name=BOLD,
                          anchor="rt", shadow=False)
                self.event(ts, "hydraulic", 0.8)
            type_text(f, L("plane"), 140, 130, 48, WHITE, t, S[2], cursor=False)
            type_text(f, L("plane_sub"), 142, 196, 22, GREY, t, S[2] + 0.4, name=BODY, shadow=False,
                      cursor=False, sound=False)
            f = vignette(f)
        return self.fade(f, t, fin=0.2, fout=0.2)


# ------------------------------------------------------------------ maps
LON0, LAT1, PPD = -126.0, 50.0, 360.0
KX = math.cos(math.radians(44.5))
MAP_W, MAP_H = int(13 * KX * PPD), int(12 * PPD)
PLACES = {"SEATTLE": (47.449, -122.309), "PORTLAND": (45.589, -122.597),
          "RENO": (39.499, -119.768)}
JUMP = (45.95, -122.56)     # commonly cited estimate (near Ariel, Washington)
TENA = (45.718, -122.774)   # Tena Bar, where ransom money was found in 1980
ROUTE = [(47.449, -122.309), (46.9, -122.45), (46.4, -122.55), JUMP, (45.3, -122.3),
         (44.0, -121.6), (42.2, -120.9), (40.6, -120.2), (39.499, -119.768)]


def proj(lat, lon):
    return (lon - LON0) * KX * PPD, (LAT1 - lat) * PPD


_MAP = None


def base_map():
    global _MAP
    if _MAP is not None:
        return _MAP
    m = np.empty((MAP_H, MAP_W, 3), np.uint8)
    m[:] = (10, 14, 20)
    with open(os.path.join(ASSETS, "ne_50m_admin_1_states_provinces_lakes.geojson")) as fh:
        states = [s for s in json.load(fh)["features"]
                  if s["properties"].get("admin") in ("United States of America", "Canada")]

    def rings(geom):
        if geom["type"] == "Polygon":
            return geom["coordinates"]
        return [r for poly in geom["coordinates"] for r in poly]

    for pass_ in (0, 1):
        for ft in states:
            for ring in rings(ft["geometry"]):
                pts = np.array([proj(lat, lon) for lon, lat in ring], np.int32)
                if pass_ == 0:
                    cv2.fillPoly(m, [pts], (24, 27, 32))
                else:
                    cv2.polylines(m, [pts], True, (64, 68, 76), 3, cv2.LINE_AA)
    with open(os.path.join(ASSETS, "ne_10m_rivers_lake_centerlines.geojson")) as fh:
        rivers = json.load(fh)["features"]
    for ft in rivers:
        if ft["properties"].get("name") not in ("Columbia", "Willamette", "Lewis", "Snake"):
            continue
        g = ft["geometry"]
        lines_ = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        for ln in lines_:
            pts = np.array([proj(lat, lon) for lon, lat in ln], np.int32)
            cv2.polylines(m, [pts], False, (40, 80, 120), 5, cv2.LINE_AA)
    for key, (lat, lon) in (("st_wa", (47.3, -120.4)), ("st_or", (43.9, -120.3)),
                            ("st_nv", (39.6, -116.8)), ("st_id", (44.3, -115.0)),
                            ("st_ca", (39.9, -122.6))):
        x, y = proj(lat, lon)
        static(m, " ".join(L(key)), x, y, 54, (54, 58, 66), name=BOLD, anchor="cm")
    _MAP = m
    return m


class MapView:
    def __init__(self, lat, lon, ppd):
        self.lat, self.lon, self.ppd = lat, lon, ppd

    def render(self):
        s = self.ppd / PPD
        cx, cy = proj(self.lat, self.lon)
        m = np.float32([[s, 0, W / 2 - cx * s], [0, s, H / 2 - cy * s]])
        return cv2.warpAffine(base_map(), m, (W, H), flags=cv2.INTER_AREA,
                              borderValue=(10, 14, 20))

    def pt(self, lat, lon):
        s = self.ppd / PPD
        cx, cy = proj(self.lat, self.lon)
        x, y = proj(lat, lon)
        return W / 2 + (x - cx) * s, H / 2 + (y - cy) * s


def route_upto(mv, frac):
    pts = [mv.pt(*p) for p in ROUTE]
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    target, out = sum(seg) * frac, [pts[0]]
    for (a, b), d in zip(zip(pts, pts[1:]), seg):
        if target >= d:
            out.append(b)
            target -= d
        else:
            u = target / d if d else 0
            out.append((lerp(a[0], b[0], u), lerp(a[1], b[1], u)))
            break
    return out


def frac_of(p):
    pts = [proj(*q) for q in ROUTE]
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    return sum(seg[:ROUTE.index(p)]) / sum(seg)


def draw_place(f, mv, name, lat, lon, t, t0, col=WHITE):
    x, y = mv.pt(lat, lon)
    cv2.circle(f, (int(x), int(y)), 9, col, -1, cv2.LINE_AA)
    type_text(f, name, x + 20, y, 28, col, t, t0, name=BOLD, anchor="lm", shadow=False,
              cursor=False, sound=False)


def pulse(f, x, y, t, t0, col=RED):
    if t < t0:
        return
    for k in range(3):
        u = ((t - t0) * 0.9 + k / 3) % 1.0
        r = int(20 + 110 * u)
        overlay(f, 1 - u, lambda ov, ox, oy, r=r: cv2.circle(ov, (int(x - ox), int(y - oy)), r, col,
                                                             4, cv2.LINE_AA),
                (x - r - 6, y - r - 6, x + r + 6, y + r + 6))
    cv2.circle(f, (int(x), int(y)), 12, col, -1, cv2.LINE_AA)


# ------------------------------------------------------------------ 6. jump
class Jump(Scene):
    def __init__(self, spec):
        super().__init__(spec)
        self.forest = Clip("wa_landscape")
        self.t_cut = 3.6

    def frame(self, t):
        S, w = self.S, self.w
        t_jolt = w.at(0, "jolts")
        if t < self.t_cut:
            u = smooth(t / self.t_cut)
            mv = MapView(lerp(46.75, 46.35, u), -122.45, lerp(330, 420, u))
            f = mv.render()
            pts = route_upto(mv, frac_of(JUMP) * smooth(lin(t, 0.2, 2.6)))
            cv2.polylines(f, [np.array(pts, np.int32)], False, YEL, 5, cv2.LINE_AA)
            for name in ("SEATTLE", "PORTLAND"):
                draw_place(f, mv, name, *PLACES[name], t, 0.1)
            jx, jy = mv.pt(*JUMP)
            pulse(f, jx, jy, t, 2.6)
            type_text(f, L("jump_area"), jx + 40, jy - 40, 28, RED, t, 2.6, name=BOLD, anchor="lb",
                      shadow=False, cursor=False)
            type_text(f, L("time"), 120, 110, 110, WHITE, t, 0.2, cursor=False)
            type_text(f, L("date"), 126, 250, 30, GREY, t, 0.6, name=BOLD, shadow=False)
            self.event(0.3, "clock", 0.8)
        elif t < S[1] - 0.1:
            img, _ = self.forest.at(1.0 + (t - self.t_cut) * 0.9)
            f = crime_grade(View(img.shape[1], img.shape[0], zoom=1.15).render(img), sat=0.1,
                            bright=0.42, tint=(0.8, 0.92, 1.1))
            f = self.rain(f, t)
            f = vignette(f)
            type_text(f, L("sw_wa"), 120, 110, 30, GREY, t, self.t_cut + 0.1, name=BOLD, shadow=False)
            if t >= t_jolt:
                type_text(f, L("jolt"), W / 2, 540, 88, WHITE, t, t_jolt, anchor="cm", cps=40)
                f = shake(f, t, t_jolt, 0.6, 26)
                self.event(t_jolt, "boom", 1.0)
            self.event(self.t_cut, "rain", 1.0)
        else:
            lt = t - S[1]
            u = smooth(lt / 2.4)
            mv = MapView(lerp(43.8, 43.5, u), -121.0, lerp(135, 120, u))
            f = mv.render()
            cv2.polylines(f, [np.array(route_upto(mv, 1.0), np.int32)], False, (120, 100, 40), 4,
                          cv2.LINE_AA)
            for name in PLACES:
                draw_place(f, mv, name, *PLACES[name], t, S[1])
            rx, ry = mv.pt(*PLACES["RENO"])
            pulse(f, rx, ry, t, S[1] + 0.1, WHITE)
            type_text(f, L("empty"), W / 2 + 420, 560, 100, RED, t, w.at(1, "gone"), anchor="cm",
                      cps=30)
            self.event(w.at(1, "gone"), "hit", 1.0)
            f = vignette(f)
        return self.fade(f, t, fin=0.2, fout=0.25)

    def rain(self, f, t):
        rng = np.random.default_rng(int(t * FPS))
        ov = np.zeros_like(f)
        for _ in range(260):
            x, y = int(rng.integers(0, W)), int(rng.integers(0, H))
            ln = int(rng.integers(30, 70))
            cv2.line(ov, (x, y), (x - ln // 5, y + ln), (150, 160, 175), 1, cv2.LINE_AA)
        return cv2.add(f, ov)


# ------------------------------------------------------------------ 7. profile
class Profile(Scene):
    def __init__(self, spec):
        super().__init__(spec)
        self.poster = best("DB_Cooper_Wanted_Poster.jpg")
        self.forest = Clip("wa_landscape")
        self.wrong = stamp(L("wrong"), RED, 90)

    def frame(self, t):
        S, w = self.S, self.w
        if t < S[1]:
            f = canvas(INK)
            h, wd = self.poster.shape[:2]
            photo_frame(f, self.poster, t, S[1], 600, 540, 980, 1.0, 1.25, tilt=1.2,
                        c0=(wd / 2, h * 0.35), c1=(wd / 2, h * 0.55), sat=0.0)
            static(f, L("bulletin"), 600, 1050, 22, GREY, 1, anchor="cm")
            type_text(f, L("theory"), 1130, 300, 28, RED, t, 0.3, name=BOLD, shadow=False,
                      cursor=False)
            type_text(f, L("expert1"), 1130, 400, 96, WHITE, t, w.at(0, "expert"), anchor="lm",
                      cursor=False)
            type_text(f, L("expert2"), 1130, 510, 96, WHITE, t, w.at(0, "skydiver"), anchor="lm")
            stamp_at(f, self.wrong, 1420, 700, t, w.at(0, "opposite"))
            self.event(w.at(0, "opposite"), "stamp", 1.0)
            f = vignette(f)
        elif t < S[2]:
            img, _ = self.forest.at(30 + (t - S[1]) * 0.7)
            f = crime_grade(View(img.shape[1], img.shape[0], zoom=1.1).render(img), sat=0.0,
                            bright=0.28)
            f = vignette(f)
            self.carr_quote(f, t)
            self.event(S[1], "rain", 0.7)
        else:
            f = canvas(INK)
            self.contradiction(f, t)
            f = vignette(f)
        return self.fade(f, t, fin=0.2, fout=0.2)

    def carr_quote(self, f, t):
        S, w = self.S, self.w
        lines = L("carr")
        # type the quote in time with the narrator, a line per quarter of the sentence
        t0, t1 = S[1], w.ends[1]
        hot = {k: w.at(1, v) for k, v in CARR_HOT_WORDS.items()}
        for k, ln in enumerate(lines):
            tl = lerp(t0, t1 - 0.6, k / len(lines))
            x, y = 220, 320 + k * 96
            cps = len(ln) / max((t1 - t0) / len(lines) - 0.15, 0.5)
            for wi, word in enumerate(ln.split(" ")):
                start = tl + len(" ".join(ln.split(" ")[:wi])) / cps
                col = WHITE
                for hk, ht in hot.items():
                    if word.lower().startswith(hk.lower().strip(",")) and t >= ht:
                        col = YEL
                ww = type_text(f, word, x, y, 54, col, t, start, cps=cps, cursor=False)
                x += typed_width(word + " ", 54)
        type_text(f, L("carr_attr"), 224, 720, 28, RED, t, t1 - 0.2, name=BOLD, shadow=False)

    def contradiction(self, f, t):
        S, w = self.S, self.w
        type_text(f, L("contradiction"), W / 2, 140, 72, WHITE, t, S[2], anchor="cm", cursor=False)
        line(f, (W / 2, 230), (W / 2, 960), (60, 60, 64), 3)
        tl, tr = w.at(2, "planned"), w.at(2, "nothing")
        type_text(f, L("hijacking"), W / 4 + 40, 280, 54, GREEN, t, tl - 0.2, anchor="cm",
                  cursor=False)
        type_text(f, L("landing"), 1380, 280, 54, RED, t, tr - 0.2, anchor="cm", cursor=False)
        for k, s in enumerate(L("left")):
            tk = tl + k * 0.25
            if t >= tk:
                check(f, 250, 410 + k * 110, 44, True, lin(t, tk + 0.25, tk + 0.5))
                type_text(f, s, 320, 410 + k * 110, 40, WHITE, t, tk, name=BOLD, anchor="lm",
                          cursor=False, cps=44)
        for k, s in enumerate(L("right")):
            tk = tr + k * 0.28
            if t >= tk:
                check(f, 1080, 410 + k * 110, 44, False, lin(t, tk + 0.25, tk + 0.5))
                type_text(f, s, 1140, 410 + k * 110, 40, WHITE, t, tk, name=BOLD, anchor="lm",
                          cursor=False, cps=44)
                self.event(tk + 0.25, "x", 0.5)
        type_text(f, L("chute_note"), W / 2, 1010, 22, GREY, t, tr + 1.4, name=BODY, anchor="cm",
                  shadow=False, cursor=False, sound=False, cps=60)


# ------------------------------------------------------------------ 8. money
class Money(Scene):
    def __init__(self, spec):
        super().__init__(spec)
        self.money = load("Money_stolen_by_D._B._Cooper.jpg")
        self.forest = Clip("wa_landscape")
        self.sketch_b = best("Revised_Composite_Sketch_B.jpg", "CompositeB-FBI-1973.jpg")
        self.poster = best("DB_Cooper_Wanted_Poster.jpg")
        self.unsolved = stamp(L("unsolved"), RED, 110)
        self.match = stamp(L("match"), (230, 200, 60), 50, angle=6)

    def frame(self, t):
        S, w = self.S, self.w
        if t < S[0] + 2.6:
            u = smooth(t / 2.6)
            mv = MapView(lerp(46.0, 45.82, u), lerp(-122.5, -122.68, u), lerp(800, 1500, u))
            f = mv.render()
            draw_place(f, mv, "PORTLAND", *PLACES["PORTLAND"], t, 0.0, col=GREY)
            jx, jy = mv.pt(*JUMP)
            cv2.circle(f, (int(jx), int(jy)), 10, (140, 60, 60), -1, cv2.LINE_AA)
            static(f, L("jump_area"), jx + 20, jy, 22, (160, 90, 90), 1, name=BOLD, anchor="lm")
            tx, ty = mv.pt(*TENA)
            pulse(f, tx, ty, t, 0.5, YEL)
            type_text(f, L("tena"), tx - 30, ty + 40, 32, YEL, t, 0.5, name=BOLD, anchor="rt",
                      shadow=False, cursor=False)
            type_text(f, L("feb"), tx - 30, ty + 86, 28, WHITE, t, 1.3, name=BOLD, anchor="rt",
                      shadow=False)
            self.event(0.5, "ping", 0.8)
            f = vignette(f)
        elif t < S[1]:
            t0 = S[0] + 2.6
            lt = t - t0
            f = canvas(INK)
            photo_frame(f, self.money, lt, S[1] - t0, 640, 520, 620, 1.0, 1.15, tilt=-1.0,
                        appear=lin(lt, 0, 0.2), sat=0.5)
            self.event(t0, "shutter", 0.8)
            n = int(5800 * ease_out(lin(lt, 0.1, 1.0)))
            static(f, money(n), 1490, 330, 120, YEL, lin(lt, 0, 0.2), name=HEAD, anchor="cm")
            type_text(f, L("found_by"), 1490, 430, 28, WHITE, t, t0 + 0.4, name=BOLD, anchor="cm",
                      shadow=False)
            stamp_at(f, self.match, 1490, 620, t, t0 + 1.8)
            self.event(t0 + 1.8, "stamp", 0.8)
            self.event(t0 + 0.1, "count", 0.6)
            f = vignette(f)
        elif t < S[2]:
            img, _ = self.forest.at(12 + (t - S[1]) * 0.8)
            f = crime_grade(View(img.shape[1], img.shape[0], zoom=1.1).render(img), sat=0.05,
                            bright=0.35)
            f = vignette(f)
            type_text(f, L("rest"), W / 2, 470, 140, WHITE, t, S[1] + 0.1, anchor="cm", cursor=False)
            type_text(f, L("never_found"), W / 2, 620, 76, RED, t, w.at(1, "neither"), anchor="cm")
            self.event(w.at(1, "neither"), "thud", 0.9)
        elif t < S[3]:
            f = canvas(INK)
            photo_frame(f, self.poster, t - S[2], S[3] - S[2], W / 2, 540, 900, 1.05, 1.15,
                        tilt=-1.5, sat=0.0)
            tu = w.at(2, "unsolved")
            stamp_at(f, self.unsolved, W / 2, 470, t, tu)
            self.event(tu, "stamp", 1.0)
            type_text(f, L("fbi_end"), W / 2, 1020, 28, WHITE, t, tu + 0.5, name=BOLD, anchor="cm",
                      shadow=False, cps=48)
            f = vignette(f)
        else:
            lt = t - S[3]
            f = canvas(INK)
            img = self.sketch_b
            h, wd = img.shape[:2]
            half = img[:, wd // 2:] if wd > h else img
            hh, ww = half.shape[:2]
            photo_frame(f, half, lt, self.D - S[3], W / 2, 540, 900, 1.0, 1.35,
                        c0=(ww / 2, hh * 0.5), c1=(ww / 2, hh * 0.38), sat=0.25)
            f = vignette(f)
            self.event(S[3], "drone_end", 1.0)
        return self.fade(f, t, fin=0.2, fout=0.9 if t > S[3] else 0.2)


# ------------------------------------------------------------------ 9. end
class End(Scene):
    def frame(self, t):
        f = canvas(INK)
        type_text(f, L("end_title"), W / 2, 300, 66, WHITE, t, 0.05, anchor="cm", cps=40)
        a = ease_out(lin(t, 0.9, 1.3))
        line(f, (W / 2 - 240 * a, 360), (W / 2 + 240 * a, 360), RED, 3)
        voice = os.environ.get("VOICE_CREDIT", "Kokoro TTS")
        for k, (role, who) in enumerate(L("credits")):
            ka = ease_out(lin(t, 0.9 + k * 0.1, 1.3 + k * 0.1))
            y = 450 + k * 50
            static(f, role, 760, y, 22, RED, ka, name=BOLD, anchor="rm")
            static(f, who.format(voice=voice), 790, y, 22, (200, 200, 200), ka, name=BODY,
                   anchor="lm")
        return self.fade(f, t, fin=0.0, fout=0.8)


SCENES = {"hook": Hook, "title": Title, "note": Note, "demands": Demands, "orders": Orders,
          "jump": Jump, "profile": Profile, "money": Money, "end": End}
