"""Scenes for "Twenty Boats" / "Dvacet člunů".

Each scene draws frame(t) for t in [0, dur) and lists its sound cues. All text
comes from strings.py and every animation waits for a word in the scene's own
narration timings, so the English and Czech cuts share one plan but are each
timed to their own voice (FILM_LANG=en|cs).

Archival: Library of Congress (Bain News Service photos, Chronicling America
newspapers), public domain. Maps: Natural Earth. Diagrams/charts: drawn here.
"""
import json
import math
import os
import re
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import geo  # noqa: E402
import look  # noqa: E402
from look import (CORAL, INK, INK2, WHITE, YELLOW, BLUE, W, FPS,  # noqa: E402
                  clamp, ease_in_out, ease_out, lerp, lin, pop)
from strings import LANG, L, N, num  # noqa: E402

ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(ROOT, "build", "titanic", "assets")
CUTS = os.path.join(ROOT, "build", "titanic", "cut")
SLIDE = 0.55          # paper-slide transition length


# ------------------------------------------------------------------ assets
def photo(name, crop=None):
    im = np.array(Image.open(os.path.join(ASSETS, name)).convert("RGB"))
    if crop:
        x0, y0, x1, y1 = crop
        im = im[y0:y1, x0:x1]
    return im


def die_cut(name, out_name, max_side=2400):
    """Cut an object out of a photo (rembg, cached). Returns RGB and matte,
    cropped to the object."""
    path = os.path.join(CUTS, out_name + ".png")
    if not os.path.exists(path):
        from rembg import new_session, remove
        im = Image.open(os.path.join(ASSETS, name)).convert("RGB")
        im.thumbnail((max_side, max_side))
        os.makedirs(CUTS, exist_ok=True)
        remove(im, session=new_session("isnet-general-use")).save(path)
    a = np.array(Image.open(path).convert("RGBA"))
    ys, xs = np.where(a[..., 3] > 20)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return a[..., :3].copy(), a[..., 3].copy()


class FilmPrint:
    """A short stretch of archival film shown as a torn-edged print that moves."""

    def __init__(self, name, t0, t1, target_h, seed=1, crop=0.06, fps_src=24.0):
        cap = cv2.VideoCapture(os.path.join(ASSETS, name))
        cap.set(cv2.CAP_PROP_POS_MSEC, t0 * 1000)
        self.frames, self.fps = [], fps_src
        while cap.get(cv2.CAP_PROP_POS_MSEC) < t1 * 1000:
            ok, img = cap.read()
            if not ok:
                break
            h, w = img.shape[:2]
            img = img[int(h * crop):int(h * (1 - crop)), int(w * crop):int(w * (1 - crop))]
            s = target_h / img.shape[0]
            img = cv2.resize(img, (int(img.shape[1] * s), int(target_h)), interpolation=cv2.INTER_AREA)
            self.frames.append(look.print_grade(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), 0.05))
        cap.release()
        fh, fw = self.frames[0].shape[:2]
        blank = np.zeros((fh, fw, 3), np.uint8)
        self.frame_spr = look.torn_print(blank, border=16, seed=seed, grade=False, tex=False)

    def draw(self, f, t, x, y, scale=1.0, angle=0.0, alpha=1.0):
        k = int(t * self.fps) % (2 * len(self.frames) - 2)      # play forward, then back
        k = k if k < len(self.frames) else 2 * len(self.frames) - 2 - k
        self.frame_spr.draw(f, x, y, scale=scale, angle=angle, alpha=alpha)
        look.Sprite(self.frames[k]).draw(f, x, y, scale=scale, angle=angle, alpha=alpha)


# ------------------------------------------------------------------ icons
def boat_icon(w=56, color=INK):
    """A flat double-ended lifeboat seen from the side, with a light sheer stripe."""
    h = int(w * 0.40)
    pad = 4
    img = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.uint8)
    xs = np.linspace(-1, 1, 60)
    top = [(pad + (x + 1) / 2 * w, pad + h * 0.10 * x * x) for x in xs]       # sheer rises to the ends
    bot = [(pad + (x + 1) / 2 * w, pad + h * (0.10 + 0.90 * (1 - abs(x) ** 2.2))) for x in xs[::-1]]
    poly = np.array(top + bot, np.float32)
    cv2.fillPoly(img, [np.round(poly * 4).astype(np.int32)], tuple(color) + (255,), cv2.LINE_AA,
                 shift=2)
    stripe = np.array([(x, y + h * 0.22) for x, y in top[6:-6]], np.float32)
    cv2.polylines(img, [np.round(stripe * 4).astype(np.int32)], False, (242, 236, 223, 255),
                  max(1, w // 28), cv2.LINE_AA, shift=2)
    return look.Sprite(img)


def ship_icon(w=520, color=INK, funnels=4, accent=None):
    """A flat side-view liner: hull, superstructure, funnels, a row of portholes."""
    h = int(w * 0.42)
    img = np.zeros((h, w, 4), np.uint8)
    c = tuple(color) + (255,)
    hull_top, hull_bot = int(h * 0.58), int(h * 0.95)
    hull = np.array([[0, hull_top], [w, hull_top - int(h * 0.04)], [int(w * 0.93), hull_bot],
                     [int(w * 0.05), hull_bot]], np.int32)
    cv2.fillPoly(img, [hull], c, cv2.LINE_AA)
    cv2.rectangle(img, (int(w * 0.12), int(h * 0.42)), (int(w * 0.84), hull_top), c, -1)
    cv2.rectangle(img, (int(w * 0.22), int(h * 0.32)), (int(w * 0.74), int(h * 0.42)), c, -1)
    xs = np.linspace(0.28, 0.66, funnels) if funnels > 1 else [0.48]
    for k, fx in enumerate(xs):
        x0 = int(w * fx)
        fc = tuple(accent) + (255,) if accent is not None else c
        cv2.rectangle(img, (x0, int(h * 0.06)), (x0 + int(w * 0.055), int(h * 0.34)), c, -1)
        cv2.rectangle(img, (x0, int(h * 0.06)), (x0 + int(w * 0.055), int(h * 0.12)), fc, -1)
    for x in range(int(w * 0.12), int(w * 0.86), max(8, w // 40)):
        cv2.circle(img, (x, int(h * 0.68)), max(2, w // 160), (0, 0, 0, 0), -1, cv2.LINE_AA)
    return look.Sprite(img)


def radio_icon(t, cx, cy, frame, alpha=1.0, size=1.0, active=True, color=INK):
    """A wireless mast with pulsing arcs."""
    s = size
    look.hand_line(frame, (cx, cy + 70 * s), (cx, cy - 30 * s), 1.0, color, int(7 * s), 1, 0.0,
                   alpha)
    look.hand_line(frame, (cx - 34 * s, cy + 70 * s), (cx, cy - 10 * s), 1.0, color, int(5 * s), 2,
                   0.0, alpha)
    look.hand_line(frame, (cx + 34 * s, cy + 70 * s), (cx, cy - 10 * s), 1.0, color, int(5 * s), 3,
                   0.0, alpha)
    cv2.circle(frame, (int(cx), int(cy - 36 * s)), int(9 * s), color, -1, cv2.LINE_AA)
    if not active:
        return
    for k in range(3):
        ph = (t * 0.9 + k / 3) % 1.0
        r = 30 * s + ph * 90 * s
        a = (1 - ph) * alpha
        ov = frame.copy()
        for sgn in (-1, 1):
            cv2.ellipse(ov, (int(cx), int(cy - 36 * s)), (int(r), int(r)), 0,
                        -40 if sgn > 0 else 140, 40 if sgn > 0 else 220, CORAL, int(6 * s),
                        cv2.LINE_AA)
        cv2.addWeighted(ov, a, frame, 1 - a, 0, dst=frame)


# ------------------------------------------------------------------ base scene
def _norm(w):
    return re.sub(r"^[^\w]+|[^\w]+$", "", w.lower())


class Scene:
    entry = "slide"           # how this scene arrives over the previous one
    seed = 1

    def __init__(self, spec):
        self.spec, self.D = spec, spec["dur"]
        self.S = spec["sentences"]
        self.words = spec["words"]
        self.sfx = []
        self.prev_last = None
        self.setup()

    def setup(self):
        pass

    # timing helpers --------------------------------------------------
    def cue(self, key, sent=None, after=0.0, end=False):
        """Time (s) when the narration says the word(s) N(key) in this scene."""
        needle = [_norm(x) for x in N(key).split()]
        toks = [(_norm(w[0]), w) for w in self.words]
        for i in range(len(toks)):
            w = toks[i][1]
            if (sent is not None and w[3] != sent) or w[1] < after:
                continue
            if all(i + j < len(toks) and toks[i + j][0].startswith(n) for j, n in enumerate(needle)):
                return toks[i + len(needle) - 1][1][2] if end else w[1]
        raise KeyError(f"[{LANG}] cue '{key}' ({N(key)!r}) not found in scene {self.spec['key']}")

    def sent(self, i):
        return self.S[i] if i < len(self.S) else self.D

    def event(self, t, kind, gain=1.0):
        if 0 <= t < self.D + 0.5:
            self.sfx.append((round(float(t), 3), kind, float(gain)))

    # drawing ---------------------------------------------------------
    def frame(self, t):
        f = self.draw(t)
        if self.entry == "slide" and self.prev_last is not None and t < SLIDE:
            f = slide_over(self.prev_last, f, t / SLIDE)
        if self.entry == "fade" and self.prev_last is not None and t < 0.4:
            u = t / 0.4
            f = cv2.addWeighted(self.prev_last, 1 - u, f, u, 0)
        return f

    def draw(self, t):
        return look.paper_view()

    def shots(self, t, cuts, fns, kinds=None):
        """Switch between shot functions at the given times with paper slides."""
        k = 0
        while k + 1 < len(fns) and t >= cuts[k]:
            k += 1
        f = fns[k](t)
        if k > 0:
            t0 = cuts[k - 1]
            kind = (kinds or ["slide"] * len(cuts))[k - 1]
            if kind == "slide" and t - t0 < SLIDE:
                f = slide_over(fns[k - 1](t0 - 1 / FPS), f, (t - t0) / SLIDE)
        return f


def slide_over(under, over, u):
    """The new sheet slides in from the right over the old one, casting a shadow."""
    u = ease_in_out(u)
    out = under.copy()
    shift = int(-W * 0.18 * u)
    if shift:
        out = np.roll(out, shift, axis=1)
        out[:, W + shift:] = under[:, -1:]
    x0 = int(W * (1 - u))
    if x0 < W:
        # shadow cast onto the old sheet
        sw = 46
        xs0 = max(x0 - sw, 0)
        if x0 > 0:
            g = np.linspace(0, 1, x0 - xs0, dtype=np.float32)[None, :, None] ** 2 * 0.45
            out[:, xs0:x0] = (out[:, xs0:x0] * (1 - g)).astype(np.uint8)
        out[:, x0:] = over[:, :W - x0]
    return out


# ------------------------------------------------------------------ 1. hook
class Hook(Scene):
    entry = None

    def setup(self):
        rgb, a = die_cut("titanic_departing_southampton_1912-04-10.jpg", "titanic_southampton")
        self.ship = look.cutout(rgb, a, target_h=640)
        self.ship_small = look.cutout(rgb, a, target_h=300)
        self.disc = look.circle_sprite(330, CORAL)
        self.boat = boat_icon(64)
        sun = photo("newyork-sun_1912-04-16_p1.jpg", (0, 0, 2486, 1640))
        self.sun = look.torn_print(sun, target_h=800, border=0, seed=3, sepia=0.04, edge_amp=9)
        berg = photo("iceberg_viewed_from_carpathia_1912.jpg", (1390, 600, 2990, 1560))
        self.berg = look.torn_print(berg, target_h=540, border=18, seed=5, sepia=0.05)
        self.disc2 = look.circle_sprite(250, CORAL, seed=5)
        self.t_boats = self.cue("h_lifeboats", 0)
        self.t_law = self.cue("h_law", 0)
        self.t_why = self.sent(1)
        self.t_1500 = self.cue("h_1500", 1)
        self.t_die = self.cue("h_die", 1)
        self.t_c = self.sent(2)
        self.t_berg = self.cue("h_iceberg", 2)
        self.t_rule = self.cue("h_rule", 2)
        ev = self.event
        ev(0.2, "whoosh", 0.7)
        ev(0.35, "pop", 0.8)
        for k in range(0, 20, 2):
            ev(self.t_boats + k * 0.045, "pop", 0.35)
        ev(self.t_law, "pop", 0.7)
        ev(self.t_law + 0.15, "marker", 0.6)
        ev(self.t_why, "whoosh", 0.8)
        ev(self.t_why, "paper", 0.6)
        ev(self.t_1500 - 0.05, "marker", 0.8)
        ev(self.t_1500 + 0.5, "squeak", 0.7)
        ev(self.t_1500, "pop", 0.9)
        ev(self.t_die, "pop", 0.6)
        ev(self.t_c, "whoosh", 0.8)
        ev(self.t_c, "paper", 0.6)
        ev(self.t_berg + 0.15, "squeak", 0.6)
        ev(self.t_rule, "thud", 0.9)
        ev(self.t_rule + 0.35, "squeak", 0.6)

    def shot_ship(self, t):
        f = look.paper_view(lerp(-30, 30, t / max(self.t_why, 1)), 0)
        s, a = pop(t, 0.3, 0.5)
        self.disc.draw(f, 1210, 430, scale=s, alpha=a)
        u = ease_out(lin(t, 0.1, 1.1))
        x = lerp(2600, 980, u) + 14 * t
        self.ship.draw(f, x, 420 + 4 * math.sin(t * 1.3), angle=-1.0)
        if t > self.t_boats:
            for k in range(20):
                s, a = pop(t, self.t_boats + k * 0.045, 0.3)
                self.boat.draw(f, 476 + (k % 10) * 108, 808 + (k // 10) * 52, scale=s, alpha=a)
        lab_a = clamp((t - self.t_boats - 0.3) / 0.25) * (1 - clamp((t - self.t_law) / 0.2))
        if lab_a > 0:
            look.draw_text(f, L("n_boats"), 960, 960, "head", 46, INK, anchor="c", alpha=lab_a,
                           tracking=1)
        if t >= self.t_law:
            s, a = pop(t, self.t_law, 0.35)
            txt = L("more_than")
            w = look.text_width(txt, "head", 58, tracking=1)
            x0 = 960 - w / 2
            ww = look.text_width(L("more_word"), "head", 58, tracking=1)
            look.highlight(f, x0 - 12, 913, x0 + ww + 14, 983, lin(t, self.t_law + 0.1,
                                                                    self.t_law + 0.6), seed=3)
            look.draw_text(f, txt, 960, 970, "head", 58, INK, anchor="c", alpha=a, scale=s,
                           tracking=1)
        look.chip(f, L("rms"), 1450, 180, 24, fg=INK, bg=WHITE, alpha=clamp((t - 1.0) / 0.3))
        return f

    def shot_paper(self, t):
        f = look.paper_view(80, -40)
        lt = t - self.t_why
        args = dict(x=640, y=530 - 6 * lt, scale=1.0 + 0.01 * lt, angle=-2.5)
        self.sun.draw(f, **args)
        look.highlight_on(f, self.sun, (226, 360, 2200, 450), lin(t, self.t_1500 - 0.1,
                                                                   self.t_1500 + 0.6),
                          args, seed=2)
        if t > self.t_1500 + 0.45:
            ph = self.sun.photo
            cx, cy = self.sun.local(ph[0] + 312 * ph[2], ph[1] + 404 * ph[2], **args)
            look.hand_circle(f, cx, cy, 70, 34, lin(t, self.t_1500 + 0.45, self.t_1500 + 1.0),
                             width=7, seed=4)
        s, a = pop(t, self.t_1500, 0.45)
        self.disc2.draw(f, 1540, 470, scale=s, alpha=a)
        look.draw_text(f, L("approx_1500"), 1540, 470, "black", 124, INK, anchor="c", valign="mid",
                       scale=s, alpha=a)
        t_died = max(self.t_die, self.t_1500 + 0.45)
        if t > t_died:
            s, a = pop(t, t_died)
            look.strip_sprite(L("died"), "display_i", 76, seed=2).draw(f, 1560, 640, scale=s,
                                                                      alpha=a, angle=-4)
        look.chip(f, L("sun_cap"), 110, 1000, 22, fg=INK, bg=WHITE)
        return f

    def shot_berg(self, t):
        f = look.paper_view(-60, 30)
        lt = t - self.t_c
        args = dict(x=660 + 8 * lt, y=470, scale=1.0 + 0.012 * lt, angle=2.0)
        self.berg.draw(f, **args)
        if t > self.t_berg:
            ph = self.berg.photo
            bx, by = self.berg.local(ph[0] + 800 * ph[2], ph[1] + 455 * ph[2], **args)
            look.hand_circle(f, bx, by, 120, 62, lin(t, self.t_berg + 0.1, self.t_berg + 0.7),
                             width=7, seed=8)
        look.chip(f, L("berg_cap"), 660, 860, 20, fg=INK, bg=WHITE, anchor="c")
        if t > self.t_rule:
            s, a = pop(t, self.t_rule, 0.45)
            look.strip_sprite("1894", "display", 150, seed=9, fill=(236, 228, 206)).draw(
                f, 1460, 460, scale=s, alpha=a, angle=-4)
            look.hand_line(f, (1300, 600), (1630, 588), lin(t, self.t_rule + 0.35,
                                                            self.t_rule + 0.8),
                           CORAL, 9, seed=3)
            look.draw_text(f, L("old_rule"), 1465, 690, "display_i", 60, INK, anchor="c",
                           alpha=clamp((t - self.t_rule - 0.3) / 0.3))
        return f

    def draw(self, t):
        f = self.shots(t, [self.t_why, self.t_c],
                       [self.shot_ship, self.shot_paper, self.shot_berg])
        if t < 0.35:
            f = (f.astype(np.float32) * (t / 0.35)).astype(np.uint8)
        return f


# ------------------------------------------------------------------ 2. title
class Title(Scene):
    def setup(self):
        self.boat = boat_icon(64)
        for k in range(0, 20, 2):
            self.event(0.25 + k * 0.04, "pop", 0.35)
        self.event(0.0, "whoosh", 0.7)
        self.event(0.62, "thud", 1.0)
        self.event(1.0, "paper", 0.5)

    def draw(self, t):
        f = look.paper_view(-200 + 10 * t, 120)
        for k in range(20):
            s, a = pop(t, 0.25 + k * 0.04, 0.3)
            self.boat.draw(f, 416 + (k % 10) * 121, 790 + (k // 10) * 60 +
                           3 * math.sin(t * 2 + k * 0.6), scale=s, alpha=a)
        s, a = pop(t, 0.62, 0.42)
        look.draw_text(f, L("title"), 960, 430, "black", 176, INK, anchor="c", valign="mid",
                       scale=s * (1 + 0.006 * t), alpha=a, tracking=2)
        if t > 1.0:
            s, a = pop(t, 1.0)
            look.strip_sprite(L("subtitle"), "display_i", 54, seed=4).draw(f, 960, 610, scale=s,
                                                                         alpha=a, angle=-1.5)
        return f


# ------------------------------------------------------------------ 3. the rule
class Rules(Scene):
    def setup(self):
        rgb, a = die_cut("titanic_departing_southampton_1912-04-10.jpg", "titanic_southampton")
        self.ship = look.cutout(rgb, a, target_h=120)
        self.liner = ship_icon(150, INK2, 2)
        lb = photo("titanic_collapsible_d_from_carpathia_1912-04-15.jpg", (60, 40, 3780, 2560))
        self.lbp = look.torn_print(lb, target_h=300, border=14, seed=37, sepia=0.05)
        self.t_size = self.cue("r_size", 0)
        self.t_1894 = self.cue("r_1894", 0)
        self.t_big = self.cue("r_biggest", 1)
        self.t_stop = self.cue("r_stopped", 1)
        self.t_ten = self.cue("r_ten", 1)
        self.t_tit = self.cue("r_titanic", 2)
        self.t_same = self.cue("r_same", 2)
        self.t_fifth = self.cue("r_fifth", 2)
        self.t_seats = self.sent(3)
        self.t_962 = self.cue("r_962", 3)
        self.t_1178 = self.cue("r_1178", 3)
        self.t_2200 = self.cue("r_2200", 4)
        ev = self.event
        ev(0.0, "whoosh", 0.7)
        ev(0.3, "draw", 0.5)
        ev(self.t_size, "swipe", 0.5)
        ev(self.t_1894, "thud", 0.8)
        ev(self.t_big, "grow", 0.6)
        ev(self.t_stop, "squeak", 0.7)
        ev(self.t_ten + 0.2, "pop", 0.6)
        ev(self.t_tit, "grow_long", 0.8)
        ev(self.t_tit + 0.1, "count", 0.5)
        ev(self.t_same, "whoosh", 0.7)
        ev(self.t_same, "paper", 0.5)
        ev(self.t_fifth - 0.6, "marker", 0.7)
        ev(self.t_seats, "whoosh", 0.7)
        ev(self.t_962, "grow", 0.6)
        ev(self.t_1178, "grow", 0.6)
        ev(self.t_2200, "grow_long", 0.8)
        ev(self.t_2200 + 0.9, "squeak", 0.6)

    # tonnage scale -------------------------------------------------------
    def shot_scale(self, t):
        f = look.paper_view(200 - 6 * t, -60)
        x0, x1, y = 150, 1770, 700
        tx = lambda v: x0 + (x1 - x0) * v / 50000  # noqa: E731
        a = clamp(t / 0.3)
        look.draw_text(f, L("chart_title"), 130, 160, "serif_b", 62, INK, alpha=a)
        look.draw_text(f, L("chart_sub"), 132, 214, "serif_i", 34, INK2, alpha=a)
        # covered region
        u = ease_out(lin(t, self.t_size, self.t_size + 0.7))
        if u > 0:
            look.rough_rect(f, x0, y - 190, x0 + (tx(10000) - x0) * u, y, look.PAPER2, seed=1)
            la = clamp((t - self.t_size - 0.5) / 0.3)
            cov = L("covered")
            look.draw_text(f, cov[0], (x0 + tx(10000)) / 2, y - 112, "label", 22, INK2, anchor="c",
                           alpha=la, tracking=2)
            look.draw_text(f, cov[1], (x0 + tx(10000)) / 2, y - 78, "label", 22, INK2, anchor="c",
                           alpha=la, tracking=2)
        # axis
        ua = ease_out(lin(t, 0.3, 1.1))
        cv2.line(f, (x0, y), (int(x0 + (x1 - x0) * ua), y), INK, 3, cv2.LINE_AA)
        for k, v in enumerate(range(0, 50001, 10000)):
            s, al = pop(t, 0.35 + k * 0.1, 0.3)
            if al > 0:
                cv2.line(f, (int(tx(v)), y), (int(tx(v)), y + 16), INK, 3, cv2.LINE_AA)
                look.draw_text(f, num(v), tx(v), y + 58, "sans", 28, INK, anchor="c", alpha=al)
        look.draw_text(f, L("gross_tons"), x1, y + 104, "label", 22, INK2, anchor="r", tracking=2,
                       alpha=clamp((t - 0.9) / 0.3))
        # 1894 stamp
        if t > self.t_1894:
            s, al = pop(t, self.t_1894, 0.4)
            look.strip_sprite("1894", "display", 92, seed=11, fill=(236, 228, 206)).draw(
                f, 1640, 190, scale=s, alpha=al, angle=-5)
        # biggest liner of 1894
        ub = ease_out(lin(t, self.t_big, self.t_big + 0.7))
        if ub > 0:
            look.rough_rect(f, x0, 300, x0 + (tx(12950) - x0) * ub, 356, INK2, seed=3)
            self.liner.draw(f, x0 + (tx(12950) - x0) * ub - 70, 268, alpha=clamp(ub * 3))
            look.draw_text(f, L("biggest"), tx(12950) + 22, 328, "sans", 30, INK, valign="mid",
                           alpha=clamp((t - self.t_big - 0.5) / 0.3))
        # the table stops here
        if t > self.t_stop:
            look.hand_line(f, (tx(10000), 255), (tx(10000), y + 26),
                           lin(t, self.t_stop, self.t_stop + 0.5), INK, 6, seed=5, bow=0.01)
        if t > self.t_ten + 0.2:
            s, al = pop(t, self.t_ten + 0.2, 0.4)
            look.strip_sprite(L("and_up"), "display_i", 46, seed=7).draw(f, tx(10000) + 290, 880,
                                                                        scale=s, alpha=al, angle=-2)
        # the Titanic
        ut = ease_out(lin(t, self.t_tit, self.t_tit + 1.1))
        if ut > 0:
            xe = x0 + (tx(46328) - x0) * ut
            look.rough_rect(f, x0, 384, xe, 446, CORAL, seed=4)
            self.ship.draw(f, xe - 120, 470 + 2 * math.sin(t * 1.5), alpha=clamp(ut * 3), angle=-1)
            val = 46328 if ut > 0.985 else int(46328 * ut)
            look.draw_text(f, f"{L('titanic_bar')}  {num(val)}", xe - 260, 415, "head", 34, INK,
                           anchor="r", valign="mid", alpha=clamp(ut * 3 - 0.5))
        return f

    # the 1912 report quote --------------------------------------------
    def shot_quote(self, t):
        f = look.paper_view(-300, 140)
        lines = L("quote_rule")
        lt = t - self.t_same
        # card
        look.rough_rect(f, 230 - 6 * lt, 210, 1700 - 6 * lt, 880, WHITE, seed=9, rough=3)
        x, y0, lh = 300 - 6 * lt, 330, 92
        hot = L("quote_rule_hot").split()
        # highlight the hot phrase where it falls on the lines
        u_all = lin(t, self.t_fifth - 0.7, self.t_fifth + 0.3)
        spans = _phrase_spans(lines, hot, "serif", 58)
        tot = sum(b - a for _, a, b in spans) or 1
        done = 0.0
        for li, a, b in spans:
            uu = clamp((u_all * tot - done) / (b - a))
            look.highlight(f, x + a - 8, y0 + li * lh - 52, x + b + 8, y0 + li * lh + 16, uu,
                           seed=20 + li)
            done += b - a
        for i, ln in enumerate(lines):
            look.draw_text(f, ln, x, y0 + i * lh, "serif", 58, INK,
                           alpha=clamp((t - self.t_same - 0.2 - i * 0.12) / 0.25))
        look.draw_text(f, "— " + L("quote_rule_src"), x, 790, "sans", 28, INK2,
                       alpha=clamp((t - self.t_same - 0.6) / 0.3))
        return f

    # seats --------------------------------------------------------------
    def shot_seats(self, t):
        f = look.paper_view(-80, 60)
        a = clamp((t - self.t_seats) / 0.3)
        look.draw_text(f, L("seats_title"), 130, 170, "serif_b", 62, INK, alpha=a)
        look.draw_text(f, L("seats_sub"), 132, 222, "serif_i", 34, INK2, alpha=a)
        sp, ap = pop(t, self.t_seats + 0.3, 0.45)
        self.lbp.draw(f, 1560, 215, scale=sp, alpha=ap, angle=3)
        look.chip(f, L("lifeboat_cap"), 1560, 395, 17, fg=INK, bg=WHITE, anchor="c", alpha=ap)
        bx0, scale = 560, 1180 / 2400
        rows = [(self.t_962, 962, L("seat_law"), INK2, num(962)),
                (self.t_1178, 1178, L("seat_had"), BLUE, num(1178)),
                (self.t_2200, 2201, L("seat_aboard"), CORAL, L("aboard_val"))]
        for k, (t0, v, lab, col, vs) in enumerate(rows):
            y = 380 + k * 150
            la = clamp((t - t0 + 0.15) / 0.25)
            look.draw_text(f, lab, bx0 - 30, y + 30, "label", 28, INK, anchor="r", valign="mid",
                           alpha=la, tracking=1)
            u = ease_out(lin(t, t0, t0 + (1.0 if v > 2000 else 0.7)))
            if u > 0:
                xe = bx0 + v * scale * u
                look.rough_rect(f, bx0, y, xe, y + 62, col, seed=30 + k)
                look.draw_text(f, vs if u > 0.98 else num(int(v * u)), xe + 20, y + 31, "head", 40,
                               INK, valign="mid")
        if t > self.t_2200 + 0.9:
            xa, xb, yb = bx0 + 1178 * scale, bx0 + 2201 * scale, 380 + 2 * 150 + 100
            u = lin(t, self.t_2200 + 0.9, self.t_2200 + 1.4)
            look.hand_line(f, (xa, yb), (xb, yb), u, CORAL, 7, seed=12, bow=0.02)
            look.hand_line(f, (xa, yb - 22), (xa, yb + 4), u, CORAL, 7, seed=13, bow=0.0)
            look.hand_line(f, (xb, yb - 22), (xb, yb + 4), u, CORAL, 7, seed=14, bow=0.0)
            look.draw_text(f, L("no_seat"), (xa + xb) / 2, yb + 62, "head", 38, CORAL, anchor="c",
                           alpha=clamp((t - self.t_2200 - 1.2) / 0.3))
        return f

    def draw(self, t):
        return self.shots(t, [self.t_same, self.t_seats],
                          [self.shot_scale, self.shot_quote, self.shot_seats])


def _phrase_spans(lines, hot, face, size):
    """(line index, x start, x end) of a phrase that may wrap across lines."""
    hot = [_norm(h) for h in hot]
    words = [(li, wd) for li, ln in enumerate(lines) for wd in ln.split(" ")]
    # find the phrase
    toks = [_norm(w) for _, w in words]
    for i in range(len(toks)):
        if toks[i:i + len(hot)] == hot:
            idx = range(i, i + len(hot))
            break
    else:
        return []
    spans = {}
    for k in idx:
        li, wd = words[k]
        # x of this word on its line
        before = " ".join(w for (l2, w) in words[:k] if l2 == li)
        xa = look.text_width(before + " ", face, size) - 6 if before else 0
        xb = look.text_width((before + " " if before else "") + wd, face, size) - 6
        a, b = spans.get(li, (xa, xb))
        spans[li] = (min(a, xa), max(b, xb))
    return [(li, a, b) for li, (a, b) in sorted(spans.items())]


# ------------------------------------------------------------------ 4. why: compartments, radio, ferries
class Ferry(Scene):
    def setup(self):
        wt = photo("washington-times_1912-04-15_p1.jpg", (0, 0, 2626, 1560))
        self.wt = look.torn_print(wt, target_h=760, border=0, seed=12, sepia=0.04, edge_amp=9)
        rep = photo("washington-times_1909-01-23_p1_republic.jpg", (0, 0, 2610, 1560))
        self.rep = look.torn_print(rep, target_h=760, border=0, seed=13, sepia=0.04, edge_amp=9)
        self.reel = FilmPrint("titanic_disaster_newsreel_1912_loc.mp4", 41.0, 56.0, 560, seed=14)
        self.big = ship_icon(560, INK, 4)
        self.res = ship_icon(420, INK, 1)
        self.boat = boat_icon(46)
        self.disc = look.circle_sprite(230, YELLOW, seed=8)
        self.d_left = look.circle_sprite(215, CORAL, seed=9)
        self.d_right = look.circle_sprite(185, YELLOW, seed=10)
        self.t_wt = self.cue("f_watertight", 0)
        self.t_radio = self.cue("f_radio", 0)
        self.t_s1 = self.sent(1)
        self.t_ferries = self.cue("f_ferries", 1)
        self.t_diag = max(self.t_s1 + 1.6, self.t_ferries - 0.5)
        self.t_rescue = self.cue("f_rescue", 1)
        self.t_s2 = self.sent(2)
        self.t_1909 = self.cue("f_1909", 2)
        self.t_rep = self.cue("f_republic", 2)
        self.t_radioed = self.cue("f_radioed", 2)
        self.t_1500 = self.cue("f_1500", 2)
        ev = self.event
        ev(0.0, "whoosh", 0.7)
        ev(0.05, "paper", 0.5)
        ev(self.t_wt - 0.1, "marker", 0.8)
        ev(self.t_wt + 0.5, "marker", 0.6)
        ev(self.t_radio, "morse", 0.6)
        ev(self.t_s1, "whoosh", 0.7)
        ev(self.t_s1 + 0.05, "projector", 0.5)
        ev(self.t_diag, "whoosh", 0.6)
        ev(self.t_ferries, "pop", 0.6)
        ev(self.t_rescue, "pop", 0.5)
        ev(self.t_s2, "whoosh", 0.7)
        ev(self.t_s2, "paper", 0.5)
        ev(self.t_rep - 0.05, "marker", 0.8)
        ev(self.t_radioed - 0.05, "marker", 0.7)
        ev(self.t_radioed, "morse", 0.4)
        ev(self.t_1500, "pop", 0.9)
        ev(self.t_1500 + 0.1, "count", 0.5)

    def shot_wt(self, t):
        f = look.paper_view(-150, 30)
        args = dict(x=820 + 6 * t, y=520, scale=1.0 + 0.01 * t, angle=1.8)
        self.wt.draw(f, **args)
        look.highlight_on(f, self.wt, (790, 366, 2190, 446), lin(t, self.t_wt - 0.15, self.t_wt + 0.45),
                          args, seed=5)
        look.highlight_on(f, self.wt, (212, 452, 950, 520), lin(t, self.t_wt + 0.45, self.t_wt + 0.85),
                          args, seed=6)
        look.chip(f, L("wt_cap"), 110, 1000, 21, fg=INK, bg=WHITE)
        if t > self.t_radio:
            s, a = pop(t, self.t_radio, 0.4)
            look.circle_sprite(150, YELLOW, seed=2).draw(f, 1690, 330, scale=s, alpha=a)
            radio_icon(t, 1690, 330, f, alpha=a, size=1.1 * s)
            look.draw_text(f, L("radio_lbl"), 1690, 520, "head", 40, INK, anchor="c", alpha=a,
                           tracking=2)
        return f

    def shot_ferry(self, t):
        f = look.paper_view(250, -150)
        lt = t - self.t_s1
        # the ship in trouble (left) and the rescue ship (right)
        s, a = pop(t, self.t_diag + 0.1, 0.4)
        self.d_left.draw(f, 470, 440, scale=s, alpha=a)
        self.big.draw(f, 470, 470 + 4 * math.sin(lt * 0.8), scale=s, alpha=a, angle=3.5 + 0.6 * lt)
        s2, a2 = pop(t, max(self.t_rescue, self.t_diag + 0.3), 0.4)
        self.d_right.draw(f, 1480, 440, scale=s2, alpha=a2)
        self.res.draw(f, 1480, 470, scale=s2, alpha=a2)
        look.chip(f, L("sinking_ship"), 470, 640, 22, fg=INK, bg=WHITE, anchor="c", alpha=a)
        look.chip(f, L("rescue_ship"), 1480, 640, 22, fg=INK, bg=WHITE, anchor="c", alpha=a2)
        # water line
        cv2.line(f, (120, 560), (1800, 560), (150, 170, 190), 3, cv2.LINE_AA)
        # boats shuttle along a loop between the two
        if t > self.t_ferries - 0.3:
            ua = clamp((t - self.t_ferries + 0.3) / 0.4)
            cx, cy, rx, ry = 975, 760, 430, 70
            pts = [(cx + rx * math.cos(th), cy + ry * math.sin(th))
                   for th in np.linspace(0, 2 * math.pi, 120)]
            ov = f.copy()
            for k in range(0, 118, 3):
                cv2.line(ov, tuple(np.int32(pts[k])), tuple(np.int32(pts[k + 1])), INK2, 3,
                         cv2.LINE_AA)
            cv2.addWeighted(ov, 0.7 * ua, f, 1 - 0.7 * ua, 0, dst=f)
            for k in range(4):
                th = (lt * 0.55 + k / 4) * 2 * math.pi
                bx, by = cx + rx * math.cos(th), cy + ry * math.sin(th)
                self.boat.draw(f, bx, by - 10, alpha=ua, scale=1.0 if math.sin(th) > 0 else 0.85)
            s3, a3 = pop(t, self.t_ferries)
            look.strip_sprite(L("ferry_strip"), "display_i", 70, seed=15).draw(
                f, 960, 230, scale=s3, alpha=a3, angle=-2)
        return f

    def shot_rep(self, t):
        f = look.paper_view(100, 80)
        lt = t - self.t_s2
        args = dict(x=720 - 5 * lt, y=530, scale=1.0 + 0.01 * lt, angle=-2.0)
        self.rep.draw(f, **args)
        look.highlight_on(f, self.rep, (812, 400, 2380, 488), lin(t, self.t_rep - 0.1, self.t_rep + 0.5),
                          args, seed=8)
        look.highlight_on(f, self.rep, (880, 490, 2470, 572),
                          lin(t, self.t_radioed - 0.1, self.t_radioed + 0.5), args, seed=9)
        look.chip(f, L("rep_cap"), 110, 1000, 21, fg=INK, bg=WHITE)
        s, a = pop(t, self.t_s2 + 0.15)
        look.strip_sprite(L("rep_year"), "display", 96, seed=17, fill=(236, 228, 206)).draw(
            f, 1560, 240, scale=s, alpha=a, angle=4)
        if t > self.t_1500:
            s, a = pop(t, self.t_1500, 0.45)
            self.disc.draw(f, 1560, 600, scale=s, alpha=a)
            u = clamp((t - self.t_1500) / 0.8)
            txt = L("saved_num") if u >= 1 else "≈" + num(int(1500 * ease_out(u)))
            look.draw_text(f, txt, 1560, 590, "black", 96, INK, anchor="c", valign="mid",
                           scale=s, alpha=a)
            look.draw_text(f, L("saved_lbl"), 1560, 690, "head", 36, INK, anchor="c",
                           alpha=clamp((t - self.t_1500 - 0.6) / 0.3), tracking=2)
        return f

    def draw(self, t):
        return self.shots(t, [self.t_s1, self.t_diag, self.t_s2],
                          [self.shot_wt, self.shot_reel, self.shot_ferry, self.shot_rep])

    def shot_reel(self, t):
        f = look.paper_view(-250, 120)
        lt = t - self.t_s1
        self.reel.draw(f, lt, 900 + 6 * lt, 480, scale=1.0 + 0.01 * lt, angle=-2.0)
        look.chip(f, L("olympic_cap"), 900, 880, 21, fg=INK, bg=WHITE, anchor="c")
        return f


# ------------------------------------------------------------------ 5. the night
class Night(Scene):
    def setup(self):
        wk = photo("titanic_vs_mauretania_subdivision_diagram_1912.jpg", (309, 206, 3020, 944))
        self.walker = look.torn_print(wk, target_h=200, border=14, seed=41, sepia=0.0, grade=False)
        self.t_eleven = self.cue("n_eleven", 0)
        self.t_berg = self.cue("n_iceberg", 0)
        self.t_s1 = self.sent(1)
        self.t_five = self.cue("n_five", 1)
        self.t_four = self.cue("n_four", 1)
        self.t_s2 = self.sent(2)
        self.t_two = self.cue("n_two", 2)
        self.t_forty = self.cue("n_forty", 2)
        ev = self.event
        ev(0.0, "whoosh", 0.8)
        ev(0.3, "draw", 0.4)
        ev(self.t_eleven, "pop", 0.7)
        ev(self.t_berg, "impact", 1.0)
        ev(self.t_s1, "whoosh", 0.7)
        for k in range(5):
            ev(self.t_five + 0.05 + k * 0.28, "water", 0.5)
        ev(self.t_four, "squeak", 0.6)
        ev(self.t_four + 0.45, "x", 0.8)
        ev(self.t_s2, "whoosh", 0.6)
        ev(self.t_two, "clock", 0.7)
        ev(self.t_forty + 0.4, "pop", 0.6)

    def shot_map(self, t):
        u = ease_in_out(lin(t, 0.0, self.t_s1))
        cam = geo.lerp_cam(geo.MapCam(48.5, -30.0, 22.0), geo.MapCam(45.0, -40.0, 30.0), u)
        f = geo.base(cam)
        P = geo.PLACES
        geo.route(f, cam, [P["titanic"], P["newyork"]], 1.0, (120, 128, 130), 3)
        path = [P["southampton"], P["cherbourg"], P["queenstown"], P["titanic"]]
        ur = ease_in_out(lin(t, 0.3, self.t_berg))
        tip = geo.route(f, cam, path, ur, WHITE, 4)
        for k, (key, tt) in enumerate((("southampton", 0.35), ("cherbourg", 0.6),
                                       ("queenstown", 0.9))):
            x, y = cam.xy(*P[key])
            s, a = pop(t, tt)
            cv2.circle(f, (int(x), int(y)), int(7 * s), WHITE, -1, cv2.LINE_AA)
        xs, ys = cam.xy(*P["southampton"])
        look.chip(f, L("southampton"), xs - 14, ys + 48, 20, fg=INK, bg=look.LAND, anchor="r",
                  alpha=clamp((t - 0.4) / 0.3))
        xq, yq = cam.xy(*P["queenstown"])
        look.chip(f, L("queenstown"), xq - 16, yq - 40, 20, fg=INK, bg=look.LAND, anchor="r",
                  alpha=clamp((t - 0.95) / 0.3))
        xn, yn = cam.xy(*P["newyork"])
        look.chip(f, L("newyork"), xn + 14, yn + 40, 20, fg=INK, bg=look.LAND,
                  alpha=clamp((t - 0.6) / 0.3))
        if tip is not None and t < self.t_berg:
            cv2.circle(f, (int(tip[0]), int(tip[1])), 9, WHITE, -1, cv2.LINE_AA)
        xt, yt = cam.xy(*P["titanic"])
        if t > self.t_berg:
            geo.marker(f, xt, yt, t, self.t_berg, CORAL, 13)
        if t > self.t_eleven:
            s, a = pop(t, self.t_eleven, 0.35)
            look.chip(f, L("hit_time"), xt + 36, yt - 72, 32, fg=INK, bg=YELLOW, scale=s, alpha=a)
        look.draw_text(f, L("north_atlantic"), cam.xy(36.0, -36)[0], cam.xy(36.0, -36)[1], "label",
                       24, (120, 128, 132), anchor="c", tracking=8)
        return f

    def shot_comp(self, t):
        f = look.paper_view(-320, -200)
        a = clamp((t - self.t_s1 - 0.1) / 0.3)
        look.draw_text(f, L("comp_title"), 130, 170, "serif_b", 60, INK, alpha=a)
        x0, x1, yt, yb = 140, 1780, 530, 750
        sp, ap = pop(t, self.t_s1 + 0.35, 0.45)
        self.walker.draw(f, 1440, 215, scale=sp, alpha=ap, angle=2)
        look.chip(f, L("walker_cap"), 1440, 345, 18, fg=INK, bg=WHITE, anchor="c", alpha=ap)
        n = 16
        cw = (x1 - x0) / n
        # hull: deck line, keel and a raked bow at the right
        hull = np.array([[x0, yt], [x1 + 40, yt - 16], [x1 - 30, yb], [x0 + 40, yb]], np.float32)
        # water in the first five compartments from the bow (right)
        for k in range(5):
            u = ease_out(lin(t, self.t_five + 0.05 + k * 0.28, self.t_five + 0.45 + k * 0.28))
            if u <= 0:
                continue
            cx1 = x1 - k * cw
            cx0 = cx1 - cw
            level = yb - (yb - yt - 20) * u
            poly = _clip_poly(hull, cx0, cx1, level)
            if poly is not None:
                ov = f.copy()
                cv2.fillPoly(ov, [np.round(poly * 4).astype(np.int32)], look.WATER, cv2.LINE_AA,
                             shift=2)
                cv2.addWeighted(ov, 0.9, f, 0.1, 0, dst=f)
        cv2.polylines(f, [np.round(hull * 4).astype(np.int32)], True, INK, 5, cv2.LINE_AA, shift=2)
        for k in range(1, n):
            x = x1 - k * cw
            yt_k = yt - 16 * (x - x0) / (x1 - x0)
            cv2.line(f, (int(x), int(yt_k)), (int(x), yb - 2), INK, 3, cv2.LINE_AA)
        look.draw_text(f, L("bow"), x1 + 40, yb + 54, "label", 24, INK2, anchor="r", tracking=2,
                       alpha=a)
        if t > self.t_five + 1.2:
            look.chip(f, L("flooded"), x1 - 2.5 * cw, yb + 70, 26, fg=WHITE, bg=look.rgb("#3E6E96"),
                      anchor="c", alpha=clamp((t - self.t_five - 1.2) / 0.3))
        if t > self.t_four:
            u = lin(t, self.t_four, self.t_four + 0.45)
            xa, xb, yb2 = x1 - 4 * cw + 6, x1 - 6, yt - 60
            look.hand_line(f, (xa, yb2), (xb, yb2 - 10), u, INK, 6, seed=21, bow=0.03)
            look.hand_line(f, (xa, yb2 - 18), (xa, yb2 + 14), u, INK, 6, seed=22, bow=0.0)
            look.hand_line(f, (xb, yb2 - 28), (xb, yb2 + 4), u, INK, 6, seed=23, bow=0.0)
            look.draw_text(f, L("survive4"), (xa + xb) / 2, yb2 - 40, "head", 38, INK, anchor="c",
                           alpha=clamp((t - self.t_four - 0.2) / 0.3))
            look.cross(f, x1 - 4.5 * cw, (yt + yb) / 2, 44, lin(t, self.t_four + 0.45,
                                                                self.t_four + 0.9), CORAL, 11, 4)
        look.draw_text(f, L("comp_note"), 1780, 1010, "serif_i", 26, INK2, anchor="r", alpha=a)
        return f

    def shot_clock(self, t):
        f = look.paper_view(400, 200)
        cx, cy, r = 600, 540, 260
        s, a = pop(t, self.t_s2 + 0.1, 0.5)
        look.circle_sprite(r + 30, WHITE, halftone_dots=False).draw(f, cx, cy, scale=s, alpha=a)
        if a > 0.5:
            cv2.circle(f, (cx, cy), r + 4, INK, 6, cv2.LINE_AA)
            for k in range(12):
                th = math.radians(k * 30 - 90)
                p0 = (cx + (r - 30) * math.cos(th), cy + (r - 30) * math.sin(th))
                p1 = (cx + (r - 6) * math.cos(th), cy + (r - 6) * math.sin(th))
                cv2.line(f, tuple(np.int32(p0)), tuple(np.int32(p1)), INK, 5, cv2.LINE_AA)
            # arc from 11:40 to 2:20 sweeps as he speaks
            a0 = 11 * 30 + 20 - 90               # 11:40 on the dial, degrees from +x
            sweep = 160 / 60 * 30                # 2 h 40 min = 80 degrees
            u = ease_in_out(lin(t, self.t_two, self.t_forty + 0.6))
            if u > 0:
                ov = f.copy()
                cv2.ellipse(ov, (cx, cy), (r - 50, r - 50), 0, a0, a0 + sweep * u, CORAL, -1,
                            cv2.LINE_AA)
                cv2.ellipse(ov, (cx, cy), (r - 50, r - 50), 0, a0, a0 + sweep * u, CORAL, 2,
                            cv2.LINE_AA)
                pts = [(cx, cy)] + [(cx + (r - 50) * math.cos(math.radians(a0 + sweep * u * k / 30)),
                                     cy + (r - 50) * math.sin(math.radians(a0 + sweep * u * k / 30)))
                                    for k in range(31)]
                cv2.fillPoly(ov, [np.int32(pts)], CORAL, cv2.LINE_AA)
                cv2.addWeighted(ov, 0.85, f, 0.15, 0, dst=f)
            th = math.radians(a0 + sweep * u)
            cv2.line(f, (cx, cy), (int(cx + (r - 70) * math.cos(th)), int(cy + (r - 70) * math.sin(th))),
                     INK, 9, cv2.LINE_AA)
            cv2.circle(f, (cx, cy), 14, INK, -1, cv2.LINE_AA)
        if t > self.t_two:
            s, a = pop(t, self.t_two, 0.4)
            look.draw_text(f, L("time_left"), 1340, 520, "black", 150, INK, anchor="c",
                           valign="mid", scale=s, alpha=a)
        if t > self.t_forty + 0.4:
            s, a = pop(t, self.t_forty + 0.4)
            look.chip(f, L("time_span"), 1340, 680, 34, fg=INK, bg=YELLOW, anchor="c", scale=s,
                      alpha=a)
        return f

    def draw(self, t):
        return self.shots(t, [self.t_s1, self.t_s2], [self.shot_map, self.shot_comp, self.shot_clock])


def _clip_poly(poly, x0, x1, ytop):
    """Intersect a convex polygon with the box x0..x1, y >= ytop."""
    def clip(pts, inside, inter):
        out = []
        for i in range(len(pts)):
            a, b = pts[i - 1], pts[i]
            ia, ib = inside(a), inside(b)
            if ib:
                if not ia:
                    out.append(inter(a, b))
                out.append(b)
            elif ia:
                out.append(inter(a, b))
        return out

    def ix(xv):
        return lambda a, b: (xv, a[1] + (b[1] - a[1]) * (xv - a[0]) / ((b[0] - a[0]) or 1e-6))

    def iy(yv):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (yv - a[1]) / ((b[1] - a[1]) or 1e-6), yv)

    pts = [tuple(p) for p in poly]
    pts = clip(pts, lambda p: p[0] >= x0 + 2, ix(x0 + 2))
    pts = clip(pts, lambda p: p[0] <= x1 - 2, ix(x1 - 2))
    pts = clip(pts, lambda p: p[1] >= ytop, iy(ytop))
    return np.array(pts, np.float32) if len(pts) >= 3 else None


# ------------------------------------------------------------------ 6. the radio
class Radio(Scene):
    def setup(self):
        self.carp = FilmPrint("titanic_disaster_newsreel_1912_loc.mp4", 297.0, 307.5, 250, seed=31)
        cal = photo("californian_from_carpathia_1912-04-15.jpg", (40, 120, 2900, 1700))
        self.cal = look.torn_print(cal, target_h=250, border=14, seed=32, sepia=0.05)
        self.t_cal = self.cue("c_californian", 0)
        self.t_twenty = self.cue("c_twenty", 0)
        self.t_op = self.cue("c_operator", 0)
        self.t_s1 = self.sent(1)
        self.t_carp = self.cue("c_carpathia", 1)
        self.t_call = self.cue("c_call", 1)
        self.t_58 = self.cue("c_58", 1)
        self.t_arr = self.cue("c_arrived", 1)
        self.t_late = self.cue("c_late", 1)
        ev = self.event
        ev(0.0, "whoosh", 0.7)
        ev(0.1, "zoom", 0.6)
        ev(self.t_cal, "pop", 0.7)
        ev(self.t_twenty, "draw", 0.5)
        ev(self.t_op, "pop", 0.6)
        ev(self.t_op + 0.1, "radio_off", 0.6)
        ev(self.t_carp, "pop", 0.7)
        ev(self.t_carp + 0.1, "paper", 0.4)
        ev(self.t_call, "morse", 0.7)
        ev(self.t_58, "pop", 0.5)
        ev(self.t_arr, "draw", 0.5)
        ev(self.t_late, "thud", 0.9)

    def draw(self, t):
        P = geo.PLACES
        u = ease_in_out(lin(t, 0.0, 1.6))
        mid_lat, mid_lon = 41.62, -49.75
        mid_lat, mid_lon = 41.86, -50.15
        cam = geo.lerp_cam(geo.MapCam(45.0, -40.0, 30.0), geo.MapCam(mid_lat, mid_lon, 560.0), u)
        if t > self.t_s1 - 0.6:
            u2 = ease_in_out(lin(t, self.t_s1 - 0.6, self.t_s1 + 0.8))
            cam = geo.MapCam(lerp(mid_lat, 41.50, u2), lerp(mid_lon, -49.62, u2), lerp(560, 430, u2))
        f = geo.base(cam)
        xt, yt = cam.xy(*P["titanic"])
        geo.marker(f, xt, yt, t, 0.0, CORAL, 12)
        look.chip(f, L("titanic"), xt + 26, yt + 34, 22, fg=INK, bg=CORAL,
                  alpha=clamp((t - 1.2) / 0.3))
        # the Californian, stopped in the ice to the north
        xc, yc = cam.xy(*P["californian"])
        if t > self.t_cal:
            s, a = pop(t, self.t_cal)
            cv2.circle(f, (int(xc), int(yc)), int(11 * s), WHITE, -1, cv2.LINE_AA)
            look.chip(f, L("californian"), xc + 24, yc, 22, fg=INK, bg=WHITE, scale=s, alpha=a)
            sp, ap = pop(t, self.t_cal + 0.15, 0.45)
            ap *= 1 - clamp((t - self.t_carp) / 0.5) * 0.65      # steps back when the Carpathia arrives
            self.cal.draw(f, 330, 230, scale=sp * 0.95, alpha=ap, angle=-3)
            look.chip(f, L("cal_cap"), 330, 400, 18, fg=INK, bg=WHITE, anchor="c", alpha=ap * 0.95)
        if t > self.t_twenty:
            r = 20 / 60 * cam.ppd
            geo.ring(f, xt, yt, r, lin(t, self.t_twenty, self.t_twenty + 0.8), WHITE, 2, 0.8)
            look.chip(f, L("lt20"), xt - r - 14, yt, 22, fg=INK, bg=WHITE,
                      anchor="r", alpha=clamp((t - self.t_twenty - 0.4) / 0.3))
        if t > self.t_op:
            s, a = pop(t, self.t_op)
            look.chip(f, L("asleep"), xc + 24, yc + 46, 22, fg=WHITE, bg=look.rgb("#5A6166"),
                      scale=s, alpha=a)
            look.draw_text(f, "z", xc - 30, yc - 26 - 6 * math.sin(t * 2), "hand", 40, WHITE,
                           alpha=a * 0.9)
            look.draw_text(f, "z", xc - 52, yc - 54 - 6 * math.sin(t * 2 + 1), "hand", 30, WHITE,
                           alpha=a * 0.7)
        # the Carpathia, to the south-east
        xk, yk = cam.xy(*P["carpathia"])
        if t > self.t_call:
            for k in range(3):
                ph = ((t - self.t_call) * 0.55 + k / 3) % 1.0
                if t - self.t_call < k / 3 / 0.55:
                    continue
                rr = ph * math.hypot(xk - xt, yk - yt) * 1.05
                ov = f.copy()
                cv2.circle(ov, (int(xt), int(yt)), int(rr), YELLOW, 3, cv2.LINE_AA)
                cv2.addWeighted(ov, 0.7 * (1 - ph), f, 1 - 0.7 * (1 - ph), 0, dst=f)
        if t > self.t_carp:
            s, a = pop(t, self.t_carp)
            cv2.circle(f, (int(xk), int(yk)), int(11 * s), YELLOW, -1, cv2.LINE_AA)
            look.chip(f, L("carpathia"), xk + 24, yk + 4, 22, fg=INK, bg=YELLOW, scale=s, alpha=a)
            sp, ap = pop(t, self.t_carp + 0.1, 0.45)
            self.carp.draw(f, t - self.t_carp, 1600, 240, scale=sp * 0.95, alpha=ap, angle=3)
            look.chip(f, L("carp_cap"), 1600, 410, 18, fg=INK, bg=WHITE, anchor="c", alpha=ap * 0.95)
        if t > self.t_58:
            u = lin(t, self.t_58, self.t_58 + 0.6)
            p0, p1 = np.array([xk, yk]), np.array([xt, yt])
            for k in range(0, 40, 2):
                a0, a1 = k / 40, (k + 1) / 40
                if a0 > ease_out(u):
                    break
                cv2.line(f, tuple(np.int32(p0 + (p1 - p0) * a0)),
                         tuple(np.int32(p0 + (p1 - p0) * min(a1, ease_out(u)))), YELLOW, 3,
                         cv2.LINE_AA)
            mx, my = (xk + xt) / 2, (yk + yt) / 2
            look.chip(f, L("mi58"), mx + 26, my + 30, 22, fg=INK, bg=YELLOW,
                      alpha=clamp((t - self.t_58 - 0.3) / 0.3))
        if t > self.t_arr:
            # timeline card at the bottom
            a = clamp((t - self.t_arr) / 0.3)
            x0, x1, y = 300, 1620, 960
            look.rough_rect(f, x0 - 40, y - 70, x1 + 40, y + 60, WHITE, a, seed=40)
            if a > 0.5:
                t2x = lambda hh: x0 + (x1 - x0) * (hh - 2.0) / 2.5  # noqa: E731  2:00 .. 4:30
                cv2.line(f, (x0, y), (x1, y), INK, 3, cv2.LINE_AA)
                xs, xa = t2x(2 + 20 / 60), t2x(4.0)
                cv2.circle(f, (int(xs), y), 10, CORAL, -1, cv2.LINE_AA)
                look.draw_text(f, L("sank"), xs, y - 22, "label", 24, INK, anchor="c")
                u = ease_out(lin(t, self.t_arr + 0.2, self.t_arr + 1.0))
                look.rough_rect(f, xs, y - 8, xs + (xa - xs) * u, y + 8, CORAL, seed=41)
                if u > 0.95:
                    cv2.circle(f, (int(xa), y), 10, INK, -1, cv2.LINE_AA)
                    look.draw_text(f, L("arrived"), xa, y + 44, "label", 24, INK, anchor="c")
        if t > self.t_late:
            s, a = pop(t, self.t_late, 0.35)
            look.strip_sprite(L("too_late"), "head", 64, ink=WHITE,
                              fill=CORAL, seed=44).draw(f, 960, 820, scale=s, alpha=a, angle=-3)
        look.draw_text(f, L("map_note"), 1880, 1050, "serif_i", 22, (150, 156, 160), anchor="r")
        return f


# ------------------------------------------------------------------ 7. the boats
class Boats(Scene):
    def setup(self):
        lb = photo("titanic_lifeboats_approaching_carpathia_1912-04-15.jpg")
        self.lb = look.torn_print(lb, target_h=800, border=18, seed=51, sepia=0.04)
        self.t_half = self.cue("b_half", 0)
        self.t_s1 = self.sent(1)
        self.t_65 = self.cue("b_65", 1)
        self.t_28 = self.cue("b_28", 1)
        self.t_s2 = self.sent(2)
        self.t_710 = self.cue("b_710", 2)
        self.t_1178 = self.cue("b_1178", 2)
        # 65 seats in a boat shape: 11, 13, 15, 13, 13
        rows, self.seats = [11, 14, 15, 14, 11], []
        for r, nrow in enumerate(rows):
            for k in range(nrow):
                self.seats.append((960 + (k - (nrow - 1) / 2) * 60, 560 + (r - 2) * 66))
        xs = np.linspace(-1, 1, 80)
        rx, ry = 560, 205
        upper = [(960 + rx * x, 560 - ry * (1 - x * x) ** 0.75) for x in xs]
        lower = [(960 + rx * x, 560 + ry * (1 - x * x) ** 0.75) for x in xs[::-1]]
        self.hull = np.round(np.array(upper + lower) * 4).astype(np.int32)
        ev = self.event
        ev(0.0, "whoosh", 0.7)
        ev(0.05, "paper", 0.5)
        ev(self.t_half, "pop", 0.6)
        ev(self.t_s1, "whoosh", 0.6)
        ev(self.t_65, "ripple", 0.6)
        ev(self.t_28, "count", 0.6)
        ev(self.t_s2, "whoosh", 0.6)
        ev(self.t_710, "count_long", 0.6)
        ev(self.t_1178, "pop", 0.6)

    def shot_photo(self, t):
        f = look.paper_view(-40, -100)
        args = dict(x=900 + 10 * t, y=500, scale=1.0 + 0.012 * t, angle=-1.5)
        self.lb.draw(f, **args)
        look.chip(f, L("boats_cap"), 900, 960, 21, fg=INK, bg=WHITE, anchor="c")
        if t > self.t_half:
            s, a = pop(t, self.t_half)
            look.strip_sprite(L("half_empty"), "display_i", 80, seed=52).draw(
                f, 1560, 800, scale=s, alpha=a, angle=-4)
        return f

    def shot_boat(self, t):
        f = look.paper_view(320, 100)
        a = clamp((t - self.t_s1 - 0.1) / 0.3)
        look.draw_text(f, L("boat7"), 960, 230, "head", 46, INK, anchor="c", alpha=a, tracking=2)
        # the boat seen from above, around its seats
        ov = f.copy()
        cv2.fillPoly(ov, [self.hull], WHITE, cv2.LINE_AA, shift=2)
        cv2.addWeighted(ov, 0.8 * a, f, 1 - 0.8 * a, 0, dst=f)
        if a > 0.5:
            cv2.polylines(f, [self.hull], True, INK, 6, cv2.LINE_AA, shift=2)
        for k, (x, y) in enumerate(self.seats):
            s, al = pop(t, self.t_65 + k * 0.012, 0.25)
            if al <= 0:
                continue
            filled = t > self.t_28 + k * 0.035 and k < 28
            if filled:
                fs, _ = pop(t, self.t_28 + k * 0.035, 0.25)
                cv2.circle(f, (int(x), int(y)), int(22 * fs), CORAL, -1, cv2.LINE_AA)
            cv2.circle(f, (int(x), int(y)), int(22 * s), INK, 3, cv2.LINE_AA)
        if t > self.t_65 + 0.4:
            look.draw_text(f, L("seats65"), 660, 870, "head", 44, INK, anchor="c",
                           alpha=clamp((t - self.t_65 - 0.4) / 0.3))
        if t > self.t_28:
            n = min(28, int((t - self.t_28) / 0.035) + 1)
            txt = L("aboard28") if n >= 28 else str(n)
            look.draw_text(f, txt, 1260, 870, "head", 44, CORAL, anchor="c")
        return f

    def shot_grid(self, t):
        f = look.paper_view(-260, 160)
        cols, rows = 62, 19
        x0, y0, d = 168, 300, 25.6
        a = clamp((t - self.t_s2) / 0.3)
        n_fill = 0 if t < self.t_710 else int(710 * ease_in_out(lin(t, self.t_710, self.t_710 + 1.4)))
        empty_hot = t > self.t_1178 + 0.2
        for k in range(cols * rows):
            r, c = divmod(k, cols)
            x, y = int(x0 + c * d), int(y0 + r * d)
            if k < n_fill:
                cv2.circle(f, (x, y), 9, INK, -1, cv2.LINE_AA)
            else:
                col = CORAL if empty_hot and k >= 710 else (120, 112, 104)
                if a > 0:
                    cv2.circle(f, (x, y), 9, col, 2, cv2.LINE_AA)
        if t > self.t_710:
            look.draw_text(f, L("surv710") if n_fill >= 705 else "≈" + num(n_fill), 168, 230,
                           "head", 50, INK)
        if t > self.t_1178:
            s, al = pop(t, self.t_1178)
            look.draw_text(f, L("seats1178"), 1752, 230, "head", 50, INK, anchor="r", scale=s,
                           alpha=al)
        if empty_hot:
            s, al = pop(t, self.t_1178 + 0.5)
            look.strip_sprite(L("empty470"), "display_i", 56, seed=57).draw(f, 1300, 870, scale=s,
                                                                           alpha=al, angle=-2)
        return f

    def draw(self, t):
        return self.shots(t, [self.t_s1, self.t_s2], [self.shot_photo, self.shot_boat, self.shot_grid])


# ------------------------------------------------------------------ 8. after
class After(Scene):
    def setup(self):
        rgb, a = die_cut("titanic_departing_southampton_1912-04-10.jpg", "titanic_southampton")
        self.ship = look.cutout(rgb, a, target_h=230)
        crowd = photo("crowd_awaiting_titanic_survivors_1912-04.jpg", (40, 40, 3960, 2880))
        self.crowd = look.torn_print(crowd, target_h=400, border=16, seed=63, sepia=0.05)
        self.iip = None
        for name in ("international_ice_patrol_1948_usn.jpg",):
            if os.path.exists(os.path.join(ASSETS, name)):
                self.iip = look.torn_print(photo(name), target_h=420, border=16, seed=61,
                                           sepia=0.05)
        self.t_treaty = self.cue("a_treaty", 0)
        self.t_seat = self.cue("a_seat", 0)
        self.t_radios = self.cue("a_radios", 0)
        self.t_ice = self.cue("a_ice", 1)
        self.t_s2 = self.sent(2)
        self.t_break = self.cue("a_break", 2)
        self.t_problem = self.cue("a_problem", 2)
        ev = self.event
        ev(0.0, "whoosh", 0.7)
        ev(self.t_treaty, "paper", 0.6)
        ev(self.t_seat + 0.3, "squeak", 0.6)
        ev(self.t_radios + 0.3, "squeak", 0.6)
        ev(self.t_ice + 0.3, "squeak", 0.6)
        ev(self.t_ice, "pop", 0.5)
        ev(self.t_s2, "whoosh", 0.6)
        ev(self.t_break - 0.1, "marker", 0.8)
        ev(self.t_problem, "thud", 1.0)

    def shot_treaty(self, t):
        f = look.paper_view(160, -120)
        a = clamp((t - 0.35) / 0.3)
        cx = 640
        sp, ap = pop(t, 0.5, 0.45)
        if self.iip is None or t < self.t_ice + 0.1:
            k = 1.0 if self.iip is None else 1 - clamp((t - self.t_ice) / 0.3)
            self.crowd.draw(f, 1560, 470, scale=sp * 0.92, alpha=ap * k, angle=-3)
            look.chip(f, L("crowd_cap"), 1560, 710, 18, fg=INK, bg=WHITE, anchor="c", alpha=ap * k)
        look.rough_rect(f, cx - 560, 190, cx + 560, 860, WHITE, a, seed=62, rough=3)
        if a > 0:
            look.draw_text(f, L("solas"), cx - 540, 290, "head", 46, INK, alpha=a, tracking=1)
            look.draw_text(f, L("solas_full"), cx - 540, 350, "serif_i", 32, INK2, alpha=a)
        for k, (key, t0) in enumerate((("rule1", self.t_seat), ("rule2", self.t_radios),
                                       ("rule3", self.t_ice))):
            if t < t0:
                continue
            y = 480 + k * 120
            s, al = pop(t, t0, 0.35)
            cv2.rectangle(f, (cx - 540, y - 34), (cx - 480, y + 26), INK, 4, cv2.LINE_AA)
            look.tick(f, cx - 510, y - 6, 26, lin(t, t0 + 0.25, t0 + 0.6), CORAL, 9)
            look.draw_text(f, L(key), cx - 450, y + 12, "label", 34, INK, scale=s, alpha=al)
        if self.iip is not None and t > self.t_ice:
            s, al = pop(t, self.t_ice + 0.1, 0.45)
            self.iip.draw(f, 1520, 470, scale=s, alpha=al, angle=3)
            look.chip(f, L("iip_cap"), 1520, 760, 21, fg=INK, bg=WHITE, anchor="c", alpha=al)
        return f

    def shot_end(self, t):
        f = look.paper_view(-400, -60)
        lt = t - self.t_s2
        lines = L("end1")
        hot, hot_line = L("end1_hot")
        a = clamp(lt / 0.3)
        for i, ln in enumerate(lines):
            y = 380 + i * 120
            if i == hot_line:
                w = look.text_width(ln, "black", 96, tracking=1)
                hw = look.text_width(hot, "black", 96, tracking=1)
                x0 = 960 - w / 2 + (w - hw)
                look.highlight(f, x0 - 16, y - 82, x0 + hw + 16, y + 18,
                               lin(t, self.t_break - 0.1, self.t_break + 0.6), seed=70)
            look.draw_text(f, ln, 960, y, "black", 96, INK, anchor="c", alpha=a, tracking=1)
        if t > self.t_problem:
            s, al = pop(t, self.t_problem, 0.45)
            look.draw_text(f, L("end2"), 960, 690, "black", 82, CORAL, anchor="c", scale=s,
                           alpha=al, tracking=1)
        self.ship.draw(f, 760 + 40 * lt, 900, alpha=clamp((lt - 0.4) / 0.6) * 0.95, angle=-0.5)
        return f

    def draw(self, t):
        return self.shots(t, [self.t_s2], [self.shot_treaty, self.shot_end])


# ------------------------------------------------------------------ 9. end card
class End(Scene):
    def setup(self):
        self.event(0.0, "whoosh", 0.6)
        with open(os.path.join(HERE, "credits.json")) as fh:
            self.credits = json.load(fh)[LANG]

    def draw(self, t):
        f = look.paper_view(300, 260)
        a = clamp(t / 0.4)
        look.draw_text(f, L("end_title"), 960, 170, "black", 84, INK, anchor="c", alpha=a,
                       tracking=2)
        look.draw_text(f, L("credits_head"), 960, 240, "label", 24, INK2, anchor="c", alpha=a,
                       tracking=4)
        y = 320
        for k, line in enumerate(self.credits):
            al = clamp((t - 0.3 - k * 0.06) / 0.3)
            face, size = ("label", 24) if line.isupper() else ("sans", 25)
            if not line:
                y += 14
                continue
            look.draw_text(f, line, 960, y, face, size, INK, anchor="c", alpha=al)
            y += 40
        if t > self.D - 1.2:
            k = clamp((t - (self.D - 1.2)) / 1.2)
            f = (f.astype(np.float32) * (1 - k)).astype(np.uint8)
        return f


SCENES = {"hook": Hook, "title": Title, "rules": Rules, "ferry": Ferry, "night": Night,
          "radio": Radio, "boats": Boats, "after": After, "end": End}
