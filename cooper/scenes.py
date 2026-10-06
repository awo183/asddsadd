"""Scenes for "The Calmest Man on the Plane" — a behavioural breakdown of the
1971 D.B. Cooper hijacking, told in the style of a true-crime analysis channel.

Archival stills: FBI and 1971 press photos (public domain), aircraft photo
(GFDL). B-roll: NASA (public domain). Map: Natural Earth (public domain).
"""
import json
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fx import (FPS, H, W, Clip, View, blit, canvas, clamp, darken, ease_out, fill_rect,  # noqa
                font, lerp, lin, line, mix, overlay, paste, smooth, text, text_rgba, window)
from narration import SEGMENTS  # noqa: E402

import fx  # noqa: E402

ASSETS = os.path.join(ROOT, "build", "cooper", "assets")
fx.FOOTAGE = ASSETS            # Clip() looks here for the NASA b-roll

INK = (8, 8, 10)
RED = (225, 38, 38)
YEL = (255, 210, 40)
WHITE = (240, 238, 232)
GREY = (150, 150, 150)
DIM = (90, 92, 96)
GREEN = (80, 210, 120)
PAPER = (226, 219, 200)
TEXT = dict(SEGMENTS)


# ------------------------------------------------------------------ helpers
def load(name, gray=False):
    for cand in ("x_" + name, name):
        p = os.path.join(ASSETS, cand)
        if os.path.exists(p):
            try:
                im = Image.open(p).convert("RGB")
                return np.array(im)
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
    out = cv2.multiply(out, (tint[0] * bright, tint[1] * bright, tint[2] * bright, 0))
    return out


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
    # drop shadow
    fill_rect(f, x0 + 14, y0 + 18, x0 + card.shape[1] + 14, y0 + card.shape[0] + 18, (0, 0, 0),
              0.55 * k)
    mask = (card.sum(axis=2) > 0)
    region = f[max(y0, 0):y0 + card.shape[0], max(x0, 0):x0 + card.shape[1]]
    sub_card = card[max(-y0, 0):max(-y0, 0) + region.shape[0], max(-x0, 0):max(-x0, 0) + region.shape[1]]
    sub_mask = mask[max(-y0, 0):max(-y0, 0) + region.shape[0], max(-x0, 0):max(-x0, 0) + region.shape[1]]
    region[sub_mask] = sub_card[sub_mask]
    # map from source pixel to screen
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


def pop_text(f, s, x, y, size, color, t, t0, name="black", anchor="cm", tracking=0, alpha=1.0,
             shadow=True):
    """Kinetic word: punches in at t0 with a quick scale-down."""
    if t < t0:
        return
    u = lin(t, t0, t0 + 0.16)
    k = lerp(1.45, 1.0, ease_out(u))
    img = text_rgba(s, name, int(size), tuple(color), tracking)
    if abs(k - 1) > 0.01:
        img = cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_LINEAR)
    h, w = img.shape[:2]
    X = x - (w / 2 if anchor[0] == "c" else w if anchor[0] == "r" else 0)
    Y = y - (h / 2 if anchor[1] == "m" else h if anchor[1] == "b" else 0)
    a = alpha * lin(t, t0, t0 + 0.06)
    if shadow:
        sh = img.copy()
        sh[..., :3] = 0
        blit(f, sh, X + 5, Y + 6, a * 0.7)
    blit(f, img, X, Y, a)


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
    f = font("black", size)
    w = int(f.getlength(word)) + 70
    img = Image.new("RGBA", (w, size + 60), color + (0,))
    d = ImageDraw.Draw(img)
    d.rectangle((5, 5, w - 6, size + 54), outline=color + (255,), width=8)
    d.text((35, 18), word, font=f, fill=color + (255,))
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
    """Typewriter case-file caption."""
    if t < t0:
        return
    a = lin(t, t0, t0 + 0.2)
    fill_rect(f, x - 20, y - 20, x + 780, y + 42 * len(lines) + 12, (0, 0, 0), 0.55 * a)
    fill_rect(f, x - 20, y - 20, x - 14, y + 42 * len(lines) + 12, RED, a)
    cps, tt = 38.0, t0 + 0.1
    for k, (s, col, size) in enumerate(lines):
        n = int(clamp((t - tt) * cps, 0, len(s)))
        if n:
            text(f, s[:n], x, y + k * 42, "mono_bold", size, col, a)
        tt += len(s) / cps + 0.1


def caption(f, t, t0, t1, words, hot=(), y=900, size=58):
    """Big word-by-word subtitles; words in `hot` are drawn red."""
    if t < t0 - 0.05:
        return
    n = len(words)
    total = sum(len(w) + 1 for w in words)
    acc, shown = 0, []
    for w in words:
        wt = t0 + (t1 - t0) * acc / total
        acc += len(w) + 1
        if t >= wt:
            shown.append(w)
    rows, cur = [], []
    for w in words:
        test = " ".join(cur + [w])
        if text_rgba(test, "black", size, WHITE).shape[1] > W - 300 and cur:
            rows.append(cur)
            cur = [w]
        else:
            cur.append(w)
    rows.append(cur)
    k = 0
    for r, row in enumerate(rows):
        widths = [text_rgba(w + " ", "black", size, WHITE).shape[1] for w in row]
        x = W / 2 - sum(widths) / 2
        yy = y - (len(rows) - 1 - r) * size * 1.25
        for w, wd in zip(row, widths):
            if k < len(shown):
                col = RED if w.strip(".,!?").lower() in hot else WHITE
                pop_text(f, w, x, yy, size, col, 99, 0, anchor="lm")
            x += wd
            k += 1


class Words:
    """Estimate when each word of a narrated sentence is spoken."""

    def __init__(self, scene_key, starts, voice_end):
        self.sent = TEXT[scene_key]
        self.starts = starts
        self.ends = [s - 0.3 for s in starts[1:]] + [voice_end]

    def at(self, i, needle, offset=0.0):
        s = self.sent[i]
        j = s.lower().find(needle.lower())
        frac = j / max(len(s), 1) if j >= 0 else 0
        return self.starts[i] + (self.ends[i] - self.starts[i]) * frac + offset

    def span(self, i):
        return self.starts[i], self.ends[i]


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
        z1 = 1.12 if t < S[2] else 1.55
        if t < S[2]:
            pt, box = photo_frame(f, self.sketch, t, S[2], 760, 540, 860, 1.0, 1.1, tilt=-1.5)
        else:
            pt, box = photo_frame(f, self.sketch, t - S[2], self.D - S[2], 760, 540, 860, 1.12,
                                  1.5, tilt=-1.5, c0=(wd / 2, h * 0.42), c1=(wd / 2, h * 0.36))
        # kinetic words for the opening sentence
        pop_text(f, "HIJACKED", 1300, 300, 92, WHITE, t, w.at(0, "hijacked"), anchor="lm")
        pop_text(f, "$200,000", 1300, 430, 110, YEL, t, w.at(0, "two hundred"), anchor="lm")
        pop_text(f, "VANISHED", 1300, 570, 92, RED, t, w.at(0, "jumped"), anchor="lm")
        for k, nd in enumerate(("hijacked", "two hundred", "jumped")):
            self.event(w.at(0, nd), "thud", 0.8)
        if dark > 0:
            f = darken(f, 1 - 0.92 * dark)
            if S[1] <= t < S[2] - 0.2:
                pop_text(f, "NEVER SEEN AGAIN.", W / 2, H / 2, 120, WHITE, t, S[1] + 0.25)
                self.event(S[1] + 0.25, "boom", 1.0)
        if t >= S[2]:
            tc = w.at(2, "calm")
            u = lin(t, tc - 0.3, tc + 0.4)
            # eyes of the composite, roughly 38% down the sketch
            ex, ey = pt(wd * 0.5, h * 0.37)
            circle_draw(f, ex, ey, 270, 120, u)
            pop_text(f, "CALM.", 1460, 760, 150, YEL, t, tc)
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
        g = 18 * (1 - lin(t, 0, 0.5)) * (0.6 + 0.4 * math.sin(t * 70))
        text(f, "THE CALMEST MAN", W / 2, 470, "black", 132, WHITE, 1, "cm", tracking=4)
        text(f, "ON THE PLANE", W / 2, 610, "black", 132, RED, 1, "cm", tracking=4)
        a = lin(t, 0.5, 0.9)
        line(f, (W / 2 - 330 * a, 700), (W / 2 + 330 * a, 700), RED, 4)
        text(f, "THE D.B. COOPER HIJACKING  ·  1971", W / 2, 745, "mono_bold", 28, GREY, a,
             "cm", tracking=6)
        f = rgb_split(f, g)
        self.event(0.0, "boom", 1.0)
        self.event(0.0, "glitch", 0.7)
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
            lower_third(f, t, 0.5, [("NOVEMBER 24, 1971", RED, 30),
                                     ("PORTLAND, OREGON  ·  NORTHWEST ORIENT FLIGHT 305", WHITE, 24)])
            for k in range(60):
                self.event(0.6 + k * 0.045, "type", 0.25, key=("lt", k))
            tn = w.at(0, "dan cooper")
            if t > tn:
                a = ease_out(lin(t, tn, tn + 0.3))
                fill_rect(f, 1240, 130, 1830, 290, (0, 0, 0), 0.6 * a)
                text(f, "PASSENGER", 1270, 150, "mono", 22, GREY, a)
                text(f, '"DAN COOPER"', 1270, 182, "black", 64, WHITE, a)
                text(f, "ONE-WAY TICKET  ·  PAID CASH", 1270, 256, "mono", 22, YEL, a)
                self.event(tn, "thud", 0.6)
        elif t < S[2]:
            lt = t - S[1]
            f = canvas(INK)
            pt, box = photo_frame(f, self.plane, lt, S[2] - S[1], W / 2, 470, 520, 1.0, 1.15,
                                  tilt=1.0, appear=lin(lt, 0, 0.2), sat=0.45)
            self.event(S[1], "shutter", 0.8)
            text(f, "THE AIRCRAFT: BOEING 727, N467US", W / 2, 790, "mono_bold", 26, GREY, 1, "cm")
            pop_text(f, "BOURBON & SODA", W / 2, 880, 64, WHITE, t, w.at(1, "bourbon"))
            pop_text(f, "→  A NOTE", W / 2, 970, 64, YEL, t, w.at(1, "a note"))
            f = vignette(f)
        else:
            f = self.note_card(t)
        return self.fade(f, t, fin=0.25, fout=0.2)

    def note_card(self, t):
        S, w = self.S, self.w
        f = canvas((14, 13, 12))
        lt = t - S[2]
        opened = lin(t, w.at(2, "it isn't") - 0.05, w.at(2, "it isn't") + 0.25)
        cx, cy = W / 2, 430
        pw, ph = 900, int(lerp(260, 460, ease_out(opened)))
        y_slide = lerp(140, 0, ease_out(lin(lt, 0, 0.4)))
        x0, y0 = cx - pw / 2, cy - ph / 2 + y_slide
        fill_rect(f, x0 + 16, y0 + 20, x0 + pw + 16, y0 + ph + 20, (0, 0, 0), 0.6)
        fill_rect(f, x0, y0, x0 + pw, y0 + ph, PAPER)
        line(f, (x0, y0 + ph / 2), (x0 + pw, y0 + ph / 2), (190, 182, 160), 2)
        self.event(S[2], "paper", 0.9)
        if opened > 0.3:
            a = lin(opened, 0.3, 0.9)
            text(f, "I HAVE A BOMB", cx, y0 + 110, "type", 64, (30, 28, 26), a, "cm")
            text(f, "IN MY BRIEFCASE.", cx, y0 + 190, "type", 64, (30, 28, 26), a, "cm")
            text(f, "Note wording as later recalled by the flight attendant", cx, y0 + ph - 50,
                 "mono", 20, (110, 100, 88), a, "cm")
            self.event(w.at(2, "it isn't"), "hit", 0.8)
        if t >= S[3]:
            words = TEXT["note"][3].split()
            caption(f, t, S[3], self.w.ends[3], words, hot={"i", "have", "a", "bomb"}, y=900, size=60)
            text(f, "— to flight attendant Florence Schaffner", W / 2, 1010, "mono", 22, GREY,
                 lin(t, S[3] + 0.4, S[3] + 0.8), "cm")
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
        self.stamp_plan = stamp("A PLAN", RED, 110)

    def frame(self, t):
        S, w = self.S, self.w
        f = canvas(INK)
        if t < S[2]:
            pt, box = photo_frame(f, self.sketch, t, S[2], 520, 540, 820, 1.0, 1.08, tilt=-1.0,
                                  appear=lin(t, 0, 0.25))
            text(f, "BEHAVIOUR ANALYSIS", 980, 210, "mono_bold", 26, RED, lin(t, 0.2, 0.5),
                 tracking=5)
            pop_text(f, "NOTICE WHAT HE", 980, 280, 64, WHITE, t, 0.3, anchor="lt")
            pop_text(f, "DOESN'T DO.", 980, 360, 64, YEL, t, w.at(0, "doesn't do"), anchor="lt")
            items = [("SHOUTING", w.at(1, "shout")), ("THREATS", w.at(1, "threaten")),
                     ("PASSENGERS AWARE", w.at(1, "never realize"))]
            for k, (lab, tk) in enumerate(items):
                y = 520 + k * 110
                if t >= tk - 0.1:
                    text(f, lab, 1060, y, "black", 54, WHITE, lin(t, tk - 0.1, tk + 0.1), "lm")
                    check(f, 1000, y, 50, False, lin(t, tk, tk + 0.3))
                    self.event(tk, "x", 0.7)
            self.event(0.3, "thud", 0.5)
        elif t < S[3]:
            self.ransom_note(f, t)
        elif t < S[4]:
            self.four(f, t)
        else:
            lt = t - S[4]
            pop_text(f, "NOT PANIC.", W / 2, 400, 120, (110, 110, 110), t, S[4])
            if t > w.at(4, "panic") + 0.15:
                line(f, (W / 2 - 400, 400), (W / 2 - 400 + 800 * lin(t, w.at(4, "panic") + 0.15,
                                                                      w.at(4, "panic") + 0.4), 400),
                     RED, 10)
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
        text(f, "DEMANDS", (x0 + x1) / 2, y0 + 70, "type", 60, (40, 36, 32), k, "cm")
        rows = [("$200,000", '"negotiable American currency"', w.at(2, "two hundred")),
                ("4 PARACHUTES", "two main, two reserve", w.at(2, "four parachutes")),
                ("FUEL TRUCK", "waiting in Seattle", w.at(2, "four parachutes") + 0.6)]
        for i, (big, small, tk) in enumerate(rows):
            y = y0 + 200 + i * 190
            if t >= tk:
                a = lin(t, tk, tk + 0.12)
                text(f, big, x0 + 80, y, "type", 76, (30, 28, 26), a)
                text(f, small, x0 + 84, y + 92, "type", 32, (100, 92, 82), a)
                self.event(tk, "type_burst", 0.7)
        if t >= rows[1][2] + 0.2:
            tk = rows[1][2] + 0.2
            circle_draw(f, x0 + 330, y0 + 200 + 190 + 40, 300, 75, lin(t, tk, tk + 0.4))
            self.event(tk, "marker", 0.6)

    def four(self, f, t):
        S, w = self.S, self.w
        pop_text(f, "4", 330, 520, 420, RED, t, S[3])
        self.event(S[3], "boom", 0.9)
        for k in range(4):
            tk = S[3] + 0.5 + k * 0.18
            if t >= tk:
                cx = 760 + k * 280
                col = WHITE if k == 0 else YEL
                parachute(f, cx, 380, 1.4, col, lin(t, tk, tk + 0.15))
                lab = "HIM" if k == 0 else "?"
                text(f, lab, cx, 650, "black", 48, col, lin(t, tk, tk + 0.2), "cm")
        th = w.at(3, "hostage")
        if t >= th:
            a = lin(t, th, th + 0.2)
            text(f, "A HOSTAGE COULD BE FORCED TO JUMP TOO", 1180, 760, "black", 46, WHITE, a, "cm")
            self.event(th, "thud", 0.6)
        ts = w.at(3, "sabotaged")
        if t >= ts:
            a = lin(t, ts, ts + 0.2)
            text(f, "→ NO ONE DARES TAMPER WITH THE CHUTES", 1180, 840, "black", 46, RED, a, "cm")
            text(f, "STRATEGIC DECEPTION", 1180, 930, "mono_bold", 30, YEL, a, "cm", tracking=6)


# ------------------------------------------------------------------ 5. orders
def draw_727(f, cx, cy, scale, stair, alpha=1.0, hl=0.0):
    """Side view of a Boeing 727 (nose left). stair: 0 stowed .. 1 lowered."""
    P = lambda x, y: (int(cx + (x - 500) * scale), int(cy + y * scale))  # noqa: E731
    body, edge = (52, 55, 60), (215, 215, 210)

    def poly(ov, pts, fill, outline=edge, w=2):
        arr = np.array([P(x, y) for x, y in pts], np.int32)
        if fill is not None:
            cv2.fillPoly(ov, [arr], fill, cv2.LINE_AA)
        cv2.polylines(ov, [arr], True, outline, w, cv2.LINE_AA)

    ov = f
    # fin + T-tail
    poly(ov, [(740, -38), (905, -38), (1000, -215), (925, -218)], body)
    poly(ov, [(905, -212), (1015, -214), (1004, -200), (915, -199)], body)
    # fuselage
    pts = [(60, -38), (880, -38), (980, -12), (990, 4), (900, 30), (780, 38), (60, 38)]
    poly(ov, pts, body)
    cv2.ellipse(ov, P(62, 0), (int(62 * scale), int(38 * scale)), 0, 90, 270, body, -1, cv2.LINE_AA)
    cv2.ellipse(ov, P(62, 0), (int(62 * scale), int(38 * scale)), 0, 90, 270, edge, 2, cv2.LINE_AA)
    # windows
    poly(ov, [(30, -18), (62, -24), (82, -24), (82, -12), (34, -10)], (20, 22, 26), edge, 1)
    for x in range(140, 760, 24):
        cv2.circle(ov, P(x, -14), max(2, int(5 * scale)), (170, 175, 180), -1, cv2.LINE_AA)
    # engines (side pod + centre intake)
    poly(ov, [(740, -34), (870, -34), (880, -20), (870, -6), (740, -6)], (70, 74, 80))
    poly(ov, [(800, -38), (840, -62), (860, -62), (860, -38)], (70, 74, 80))
    # wing and gear (gear down, as he ordered)
    poly(ov, [(360, 16), (520, 16), (620, 34), (560, 38)], (70, 74, 80))
    for gx, gy in ((480, 38), (110, 38)):
        line(ov, P(gx, gy), P(gx, gy + 48), edge, max(2, int(4 * scale)))
        cv2.circle(ov, P(gx, gy + 56), max(3, int(12 * scale)), (30, 30, 32), -1, cv2.LINE_AA)
        cv2.circle(ov, P(gx, gy + 56), max(3, int(12 * scale)), edge, 2, cv2.LINE_AA)
    # aft airstair, hinged under the tail
    a = math.radians(lerp(-12, 38, ease_out(stair)))
    hx, hy, L = 845, 32, 150
    ex, ey = hx + L * math.cos(a), hy + L * math.sin(a)
    nx, ny = -math.sin(a) * 12, math.cos(a) * 12
    col = mix((120, 124, 130), RED, hl)
    poly(ov, [(hx, hy), (ex, ey), (ex + nx, ey + ny), (hx + nx, hy + ny)], col, col, 2)
    for k in range(1, 7):
        sx, sy = hx + (ex - hx) * k / 7, hy + (ey - hy) * k / 7
        line(ov, P(sx, sy), P(sx + nx, sy + ny), (30, 30, 32), 2)
    return P(ex, ey), P(hx, hy)


class Orders(Scene):
    def __init__(self, spec):
        super().__init__(spec)
        self.crew = load("Crew_of_Northwest_Airlines_Flight_305_after_D._B._Cooper_hijacking.jpg")
        self.chase = Clip("dc8_chase")

    def frame(self, t):
        S, w = self.S, self.w
        if t < S[1]:
            f = canvas(INK)
            pt, box = photo_frame(f, self.crew, t, S[1], W / 2, 450, 600, 1.0, 1.12,
                                  appear=lin(t, 0, 0.2), sat=0.0)
            self.event(0.0, "shutter", 0.8)
            text(f, "THE CREW OF FLIGHT 305  ·  NEVADA STATE JOURNAL, 1971", W / 2, 800, "mono", 22,
                 GREY, 1, "cm")
            pop_text(f, "PASSENGERS  →  RELEASED", W / 2, 885, 56, WHITE, t, w.at(0, "trades"))
            pop_text(f, "$200,000 + 4 PARACHUTES  →  ON BOARD", W / 2, 965, 56, YEL, t,
                     w.at(0, "for the cash"))
            f = vignette(f)
        elif t < S[2]:
            img, _ = self.chase.at(176 + (t - S[1]) * 0.8)
            f = crime_grade(View(img.shape[1], img.shape[0], zoom=1.1).render(img), sat=0.15,
                            bright=0.45, tint=(0.85, 0.95, 1.12))
            f = vignette(f)
            fill_rect(f, 560, 230, 1360, 850, (4, 8, 6), 0.82)
            cv2.rectangle(f, (560, 230), (1360, 850), (60, 200, 110), 2)
            text(f, "HIJACKER'S INSTRUCTIONS", 600, 262, "mono_bold", 26, (60, 200, 110), 1)
            rows = [("DESTINATION", "MEXICO CITY", w.at(1, "mexico")),
                    ("ALTITUDE", "BELOW 10,000 FT", w.at(1, "low and")),
                    ("AIRSPEED", "MINIMUM", w.at(1, "slow")),
                    ("LANDING GEAR", "DOWN", w.at(1, "landing gear")),
                    ("WING FLAPS", "15°", w.at(1, "landing gear") + 0.5),
                    ("CABIN", "UNPRESSURIZED", w.at(1, "cabin"))]
            for k, (a_, b_, tk) in enumerate(rows):
                y = 340 + k * 80
                if t >= tk:
                    a = lin(t, tk, tk + 0.1)
                    text(f, a_ + " " + "." * (16 - len(a_)), 600, y, "mono_bold", 34,
                         (60, 200, 110), a)
                    text(f, b_, 1320, y, "mono_bold", 34, (190, 255, 210), a, "rt")
                    self.event(tk, "beep", 0.5)
            self.event(S[1], "static", 0.6)
        else:
            lt = t - S[2]
            f = canvas(INK)
            st = lin(t, w.at(2, "rear staircase") - 0.2, w.at(2, "rear staircase") + 1.0)
            end, hinge = draw_727(f, W / 2 - 120, 460, 1.3, st, hl=lin(st, 0, 0.3))
            if st > 0.4:
                a = lin(st, 0.4, 0.8)
                lx, ly = end[0] - 120, end[1] + 230
                arrow_draw(f, (lx + 20, ly - 70), (end[0] - 8, end[1] + 14), a)
                text(f, "AFT AIRSTAIR", lx, ly, "black", 56, RED, a, "rt")
                text(f, "CAN BE LOWERED IN FLIGHT", lx, ly + 66, "mono_bold", 28, WHITE, a, "rt")
                self.event(w.at(2, "rear staircase"), "hydraulic", 0.8)
            text(f, "BOEING 727", 140, 140, "black", 44, WHITE, lin(lt, 0, 0.3))
            text(f, "Side view (illustration)", 142, 196, "mono", 20, GREY, lin(lt, 0, 0.3))
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
        states = json.load(fh)["features"]

    def rings(geom):
        if geom["type"] == "Polygon":
            return geom["coordinates"]
        return [r for poly in geom["coordinates"] for r in poly]

    for ft in states:
        if ft["properties"].get("admin") not in ("United States of America", "Canada"):
            continue
        for ring in rings(ft["geometry"]):
            pts = np.array([proj(lat, lon) for lon, lat in ring], np.int32)
            cv2.fillPoly(m, [pts], (24, 27, 32))
    for ft in states:
        if ft["properties"].get("admin") not in ("United States of America", "Canada"):
            continue
        for ring in rings(ft["geometry"]):
            pts = np.array([proj(lat, lon) for lon, lat in ring], np.int32)
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
    for name, (lat, lon) in (("WASHINGTON", (47.3, -120.4)), ("OREGON", (43.9, -120.3)),
                             ("NEVADA", (39.6, -116.8)), ("IDAHO", (44.3, -115.0)),
                             ("CALIFORNIA", (39.9, -122.6))):
        x, y = proj(lat, lon)
        text(m, name, x, y, "mono_bold", 54, (54, 58, 66), 1, "cm", tracking=14)
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
    total, target, out = sum(seg), sum(seg) * frac, [pts[0]]
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
    i = ROUTE.index(p)
    return sum(seg[:i]) / sum(seg)


def draw_place(f, mv, name, lat, lon, a=1.0, col=WHITE, right=True):
    x, y = mv.pt(lat, lon)
    cv2.circle(f, (int(x), int(y)), 9, col, -1, cv2.LINE_AA)
    text(f, name, x + (20 if right else -20), y, "mono_bold", 28, col, a, "lm" if right else "rm",
         tracking=3)


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
            mv = MapView(lerp(46.75, 46.35, smooth(t / self.t_cut)), -122.45,
                         lerp(330, 420, smooth(t / self.t_cut)))
            f = mv.render()
            fj = frac_of(JUMP)
            pts = route_upto(mv, fj * smooth(lin(t, 0.2, 2.6)))
            cv2.polylines(f, [np.array(pts, np.int32)], False, YEL, 5, cv2.LINE_AA)
            for name in ("SEATTLE", "PORTLAND"):
                draw_place(f, mv, name, *PLACES[name])
            jx, jy = mv.pt(*JUMP)
            pulse(f, jx, jy, t, 2.6)
            if t > 2.6:
                text(f, "ESTIMATED JUMP AREA", jx + 40, jy - 40, "mono_bold", 26, RED, lin(t, 2.6, 2.9),
                     "lb")
            text(f, "8:13 PM", 120, 120, "black", 110, WHITE, lin(t, 0.3, 0.6))
            text(f, "NOVEMBER 24, 1971", 126, 250, "mono_bold", 28, GREY, lin(t, 0.3, 0.6))
            self.event(0.3, "clock", 0.8)
        elif t < S[1] - 0.1:
            img, _ = self.forest.at(1.0 + (t - self.t_cut) * 0.9)
            f = crime_grade(View(img.shape[1], img.shape[0], zoom=1.15).render(img), sat=0.1,
                            bright=0.42, tint=(0.8, 0.92, 1.1))
            f = self.rain(f, t)
            f = vignette(f)
            text(f, "SOUTHWEST WASHINGTON", 120, 120, "mono_bold", 28, GREY, 1)
            if t >= t_jolt:
                pop_text(f, "THE TAIL JOLTS UPWARD", W / 2, 540, 92, WHITE, t, t_jolt)
                f = shake(f, t, t_jolt, 0.6, 26)
                self.event(t_jolt, "boom", 1.0)
            self.event(self.t_cut, "rain", 1.0)
        else:
            lt = t - S[1]
            mv = MapView(lerp(43.8, 43.5, smooth(lt / 2.4)), -121.0, lerp(135, 120, smooth(lt / 2.4)))
            f = mv.render()
            cv2.polylines(f, [np.array(route_upto(mv, 1.0), np.int32)], False, (120, 100, 40), 4,
                          cv2.LINE_AA)
            for name in PLACES:
                draw_place(f, mv, name, *PLACES[name])
            rx, ry = mv.pt(*PLACES["RENO"])
            pulse(f, rx, ry, t, S[1] + 0.1, WHITE)
            pop_text(f, "CABIN: EMPTY", W / 2 + 420, 560, 110, RED, t, w.at(1, "gone"))
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
CARR = ['"No experienced parachutist would have',
        'jumped in the pitch-black night, in the rain,',
        'with a 200-mile-an-hour wind in his face,',
        'wearing loafers and a trench coat."']


class Profile(Scene):
    def __init__(self, spec):
        super().__init__(spec)
        self.poster = best("DB_Cooper_Wanted_Poster.jpg")
        self.forest = Clip("wa_landscape")
        self.wrong = stamp("WRONG", RED, 90)

    def frame(self, t):
        S, w = self.S, self.w
        if t < S[1]:
            f = canvas(INK)
            h, wd = self.poster.shape[:2]
            photo_frame(f, self.poster, t, S[1], 600, 540, 980, 1.0, 1.25, tilt=1.2,
                        c0=(wd / 2, h * 0.35), c1=(wd / 2, h * 0.55), sat=0.0)
            text(f, "FBI BULLETIN, 1971", 600, 1050, "mono", 20, GREY, 1, "cm")
            text(f, "THE FBI'S FIRST THEORY", 1130, 300, "mono_bold", 26, RED, lin(t, 0.3, 0.6),
                 tracking=4)
            pop_text(f, "AN EXPERT", 1130, 400, 96, WHITE, t, w.at(0, "expert"), anchor="lm")
            pop_text(f, "SKYDIVER", 1130, 510, 96, WHITE, t, w.at(0, "skydiver"), anchor="lm")
            stamp_at(f, self.wrong, 1420, 700, t, w.at(0, "opposite"))
            self.event(w.at(0, "opposite"), "stamp", 1.0)
            f = vignette(f)
        elif t < S[2]:
            img, _ = self.forest.at(30 + (t - S[1]) * 0.7)
            f = crime_grade(View(img.shape[1], img.shape[0], zoom=1.1).render(img), sat=0.0,
                            bright=0.28)
            f = vignette(f)
            a = lin(t, S[1], S[1] + 0.3)
            hot = {"pitch-black": w.at(1, "at night"), "rain,": w.at(1, "rain"),
                   "loafers": w.at(1, "loafers"), "trench": w.at(1, "trench")}
            for k, ln in enumerate(CARR):
                x = 240
                y = 330 + k * 92
                for word in ln.split(" "):
                    key = word.strip('"')
                    col = WHITE
                    for hk, ht in hot.items():
                        if key.startswith(hk.strip(",")) and t >= ht:
                            col = YEL
                    wd = text(f, word + " ", x, y, "xbold", 58, col, a)[0]
                    x += wd - 6
            text(f, "— FBI Special Agent Larry Carr, 2007", 244, 720, "mono_bold", 28, RED,
                 lin(t, S[1] + 0.5, S[1] + 0.9))
            self.event(S[1], "rain", 0.7)
        else:
            f = canvas(INK)
            text(f, "THE CONTRADICTION", W / 2, 140, "black", 70, WHITE, lin(t, S[2], S[2] + 0.2),
                 "cm", tracking=6)
            line(f, (W / 2, 230), (W / 2, 960), (60, 60, 64), 3)
            left = ["the note", "the demands", "four parachutes", "the flight plan",
                    "the rear stairs"]
            right = ["jumped at night", "into a rainstorm", "in loafers",
                     "reserve chute sewn shut*"]
            tl, tr = w.at(2, "planned"), w.at(2, "almost nothing")
            text(f, "THE HIJACKING", W / 4, 280, "black", 54, GREEN, lin(t, tl - 0.2, tl), "cm")
            text(f, "THE LANDING", 1380, 280, "black", 54, RED, lin(t, tr - 0.2, tr), "cm")
            for k, s in enumerate(left):
                tk = tl + k * 0.22
                if t >= tk:
                    check(f, 250, 410 + k * 110, 44, True, lin(t, tk, tk + 0.25))
                    text(f, s.upper(), 320, 410 + k * 110, "xbold", 44, WHITE, lin(t, tk, tk + 0.15),
                         "lm")
            for k, s in enumerate(right):
                tk = tr + k * 0.25
                if t >= tk:
                    check(f, 1080, 410 + k * 110, 44, False, lin(t, tk, tk + 0.25))
                    text(f, s.upper(), 1140, 410 + k * 110, "xbold", 44, WHITE, lin(t, tk, tk + 0.15),
                         "lm")
                    self.event(tk, "x", 0.5)
            text(f, "*per the FBI: one reserve chute was a training dummy, sewn shut", W / 2, 1010,
                 "mono", 20, GREY, lin(t, tr + 1.0, tr + 1.4), "cm")
            f = vignette(f)
        return self.fade(f, t, fin=0.2, fout=0.2)


# ------------------------------------------------------------------ 8. money
class Money(Scene):
    def __init__(self, spec):
        super().__init__(spec)
        self.money = load("Money_stolen_by_D._B._Cooper.jpg")
        self.forest = Clip("wa_landscape")
        self.sketch_b = best("Revised_Composite_Sketch_B.jpg", "D.B._Cooper_Composite_Sketch_B_-_Original.jpg",
                             "CompositeB-FBI-1973.jpg")
        self.poster = best("DB_Cooper_Wanted_Poster.jpg")
        self.unsolved = stamp("UNSOLVED", RED, 110)
        self.match = stamp("SERIAL NUMBERS MATCH", (230, 200, 60), 52, angle=6)

    def frame(self, t):
        S, w = self.S, self.w
        if t < S[0] + 2.6:
            mv = MapView(lerp(46.0, 45.82, smooth(t / 2.6)), lerp(-122.5, -122.68, smooth(t / 2.6)),
                         lerp(800, 1500, smooth(t / 2.6)))
            f = mv.render()
            draw_place(f, mv, "PORTLAND", *PLACES["PORTLAND"], col=GREY)
            jx, jy = mv.pt(*JUMP)
            cv2.circle(f, (int(jx), int(jy)), 10, (140, 60, 60), -1, cv2.LINE_AA)
            text(f, "ESTIMATED JUMP AREA", jx + 20, jy, "mono", 22, (160, 90, 90), 1, "lm")
            tx, ty = mv.pt(*TENA)
            pulse(f, tx, ty, t, 0.5, YEL)
            text(f, "TENA BAR, COLUMBIA RIVER", tx - 30, ty + 40, "mono_bold", 30, YEL,
                 lin(t, 0.5, 0.8), "rt")
            text(f, "FEBRUARY 1980", tx - 30, ty + 84, "mono_bold", 26, WHITE, lin(t, 0.6, 0.9), "rt")
            self.event(0.5, "ping", 0.8)
            f = vignette(f)
        elif t < S[1]:
            lt = t - (S[0] + 2.6)
            f = canvas(INK)
            photo_frame(f, self.money, lt, S[1] - S[0] - 2.6, 640, 520, 620, 1.0, 1.15,
                        tilt=-1.0, appear=lin(lt, 0, 0.2), sat=0.5)
            self.event(S[0] + 2.6, "shutter", 0.8)
            n = int(5800 * ease_out(lin(lt, 0.1, 1.0)))
            text(f, f"${n:,}", 1490, 330, "black", 120, YEL, lin(lt, 0, 0.2), "cm")
            text(f, "FOUND BY AN 8-YEAR-OLD BOY", 1490, 430, "mono_bold", 26, WHITE,
                 lin(lt, 0.3, 0.6), "cm")
            stamp_at(f, self.match, 1490, 620, t, S[0] + 2.6 + 1.8)
            self.event(S[0] + 2.6 + 1.8, "stamp", 0.8)
            f = vignette(f)
        elif t < S[2]:
            img, _ = self.forest.at(12 + (t - S[1]) * 0.8)
            f = crime_grade(View(img.shape[1], img.shape[0], zoom=1.1).render(img), sat=0.05,
                            bright=0.35)
            f = vignette(f)
            pop_text(f, "$194,200", W / 2, 470, 150, WHITE, t, S[1] + 0.1)
            pop_text(f, "NEVER FOUND.", W / 2, 620, 80, RED, t, w.at(1, "neither"))
            self.event(w.at(1, "neither"), "thud", 0.9)
        elif t < S[3]:
            f = canvas(INK)
            h, wd = self.poster.shape[:2]
            photo_frame(f, self.poster, t - S[2], S[3] - S[2], W / 2, 540, 900, 1.05, 1.15,
                        tilt=-1.5, sat=0.0)
            stamp_at(f, self.unsolved, W / 2, 470, t, w.at(2, "unsolved"))
            self.event(w.at(2, "unsolved"), "stamp", 1.0)
            text(f, "FBI ENDED ITS ACTIVE INVESTIGATION IN JULY 2016", W / 2, 1020, "mono_bold", 26,
                 WHITE, lin(t, w.at(2, "unsolved") + 0.5, w.at(2, "unsolved") + 0.8), "cm")
            f = vignette(f)
        else:
            lt = t - S[3]
            f = canvas(INK)
            img = self.sketch_b
            h, wd = img.shape[:2]
            half = img[:, wd // 2:] if wd > h else img     # the sunglasses version
            hh, ww = half.shape[:2]
            photo_frame(f, half, lt, self.D - S[3], W / 2, 540, 900, 1.0, 1.35,
                        c0=(ww / 2, hh * 0.5), c1=(ww / 2, hh * 0.38), sat=0.25)
            f = vignette(f)
            self.event(S[3], "drone_end", 1.0)
        return self.fade(f, t, fin=0.2, fout=0.9 if t > S[3] else 0.2)


# ------------------------------------------------------------------ 9. end
CREDITS = [
    ("NARRATION", "Synthetic voice · Kokoro TTS"),
    ("ARCHIVAL", "FBI sketches, bulletin & evidence photo (public domain)"),
    ("", "Crew photo: Nevada State Journal, 1971 (public domain)"),
    ("", "N467US photo: Clint Groves via Wikimedia Commons (GFDL 1.2)"),
    ("B-ROLL", "NASA (public domain, illustrative)"),
    ("MAP DATA", "Natural Earth"),
]


class End(Scene):
    def frame(self, t):
        f = canvas(INK)
        a = ease_out(lin(t, 0.1, 0.6))
        text(f, "THE CALMEST MAN ON THE PLANE", W / 2, 300, "black", 64, WHITE, a, "cm", tracking=3)
        line(f, (W / 2 - 240 * a, 360), (W / 2 + 240 * a, 360), RED, 3)
        for k, (role, who) in enumerate(CREDITS):
            ka = ease_out(lin(t, 0.5 + k * 0.1, 0.9 + k * 0.1))
            y = 450 + k * 50
            text(f, role, 760, y, "mono_bold", 22, RED, ka, "rm", tracking=3)
            text(f, who, 790, y, "mono", 22, (200, 200, 200), ka, "lm")
        return self.fade(f, t, fin=0.0, fout=0.8)


SCENES = {"hook": Hook, "title": Title, "note": Note, "demands": Demands, "orders": Orders,
          "jump": Jump, "profile": Profile, "money": Money, "end": End}
