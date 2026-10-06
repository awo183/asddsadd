"""Scenes 1-4: cold open, title, the 1966 Summer Vision Project, pixels."""
import math

import cv2
import numpy as np
from PIL import Image, ImageDraw

from detect import COCO
from fx import (AMBER, BG, CYAN, DARK, GREY, H, INK, PAPER, RED, W, WHITE, Clip, Dets, View,
                blit, brackets, canvas, chip, clamp, darken, det_box, ease_out, fill_rect,
                font, grade, lerp, lin, line, overlay, paste, smooth, text, text_rgba, window)


class Scene:
    def __init__(self, spec):
        self.D = spec["dur"]
        self.S = spec["sentences"]
        self.sfx = []
        self._seen = set()

    def event(self, t, kind, gain=1.0, key=None):
        """Record a sound effect once (scenes render in worker processes)."""
        key = key if key is not None else (kind, round(t, 2))
        if key not in self._seen:
            self._seen.add(key)
            self.sfx.append((round(t, 3), kind, gain))

    def fade(self, f, t, fin=0.0, fout=0.35):
        k = 1.0
        if fin:
            k = min(k, lin(t, 0, fin))
        if fout:
            k = min(k, lin(t, self.D, self.D - fout))
        return darken(f, k)


# ----------------------------------------------------------------------- wall
DET_CLASSES = {0, 1, 2, 7, 39, 41, 45, 46, 47, 49}
FACE_CLIPS = {"classroom", "face-demographics-walking", "head-pose-face-detection-female-and-male"}


class Wall:
    """A 4x4 wall of live camera feeds that a virtual camera can fly over."""
    COLS, ROWS, TW, TH, GAP = 4, 4, 432, 243, 16

    def __init__(self, tiles, with_dets=False):
        self.tiles = []
        for name, start in tiles:
            dets = None
            if with_dets:
                dets = Dets(name, "face" if name in FACE_CLIPS else "obj")
            self.tiles.append((Clip(name), start, dets, name))
        ow = self.COLS * self.TW + (self.COLS - 1) * self.GAP
        oh = self.ROWS * self.TH + (self.ROWS - 1) * self.GAP
        self.ox, self.oy = (W - ow) / 2, (H - oh) / 2

    def rect(self, i):
        c, r = i % self.COLS, i // self.COLS
        return (self.ox + c * (self.TW + self.GAP), self.oy + r * (self.TH + self.GAP),
                self.TW, self.TH)

    def center(self, i):
        x, y, w, h = self.rect(i)
        return x + w / 2, y + h / 2

    def draw(self, f, t, s, focus, sat=0.8, bright=1.0, boxes=0.0, hud=1.0, scene=None):
        for i, (clip, start, dets, name) in enumerate(self.tiles):
            x, y, w, h = self.rect(i)
            X0, Y0 = W / 2 + (x - focus[0]) * s, H / 2 + (y - focus[1]) * s
            X1, Y1 = X0 + w * s, Y0 + h * s
            if X1 < 0 or Y1 < 0 or X0 > W or Y0 > H:
                continue
            img, idx = clip.at(start + t)
            ix0, iy0 = int(round(X0)), int(round(Y0))
            iw, ih = int(round(X1)) - ix0, int(round(Y1)) - iy0
            v = View(img.shape[1], img.shape[0], (0, 0, iw, ih))
            tile = grade(v.render(img), sat=sat, bright=bright)
            paste(f, tile, ix0, iy0)
            k = s
            if hud > 0:
                sz = int(clamp(13 * k, 7, 54))
                text(f, f"CAM {i + 1:02d}", X0 + 8 * k, Y0 + 6 * k, "mono_bold", sz, WHITE,
                     0.85 * hud)
                if int((t + i * 0.37) * 2) % 2 == 0:
                    cv2.circle(f, (int(X1 - 14 * k), int(Y0 + 14 * k)), max(2, int(4.5 * k)),
                               RED, -1, cv2.LINE_AA)
                secs = int(start + t) + 9 * 3600 + 14 * 60 + i * 7
                ts = f"{secs // 3600:02d}:{secs // 60 % 60:02d}:{secs % 60:02d}"
                text(f, ts, X0 + 8 * k, Y1 - 6 * k, "mono", sz, WHITE, 0.7 * hud, anchor="lb")
            if dets is not None and boxes > 0:
                sx, sy = iw / img.shape[1], ih / img.shape[0]
                is_face = name in FACE_CLIPS
                for d in dets.get(idx, None if is_face else DET_CLASSES, 0.5):
                    box = (X0 + d[0] * sx, Y0 + d[1] * sy, X0 + (d[0] + d[2]) * sx,
                           Y0 + (d[1] + d[3]) * sy)
                    label = "FACE" if is_face else COCO[int(d[5])].upper()
                    det_box(f, box, f"{label} {d[4]:.2f}", CYAN if is_face else AMBER,
                            alpha=boxes, size=int(clamp(10 * k, 8, 30)), thick=1)


COLD_TILES = [
    ("person-bicycle-car-detection", 40.0), ("classroom", 1.0),
    ("fruit-and-vegetable-detection", 4.0), ("car-detection", 13.0),
    ("face-demographics-walking", 5.0), ("store-aisle-detection", 17.0),
    ("one-by-one-person-detection", 8.0), ("bottle-detection", 2.0),
    ("worker-zone-detection", 2.0), ("head-pose-face-detection-female-and-male", 0.0),
    ("people-detection", 0.5), ("driver-action-recognition", 30.0),
    ("face-demographics-walking-and-pause", 6.0), ("fruit-and-vegetable-detection", 30.0),
    ("store-aisle-detection", 40.0), ("worker-zone-detection", 30.0),
]


class ColdOpen(Scene):
    FOCUS = 5   # the store-aisle tile we start inside

    def __init__(self, spec):
        super().__init__(spec)
        self.wall = Wall(COLD_TILES)

    def frame(self, t):
        f = canvas((5, 6, 8))
        s0 = W / Wall.TW
        e = smooth(lin(t, 0.7, 6.2))
        s = s0 ** (1 - e)
        g = (s0 - s) / (s0 - 1)
        focus = (lerp(self.wall.center(self.FOCUS)[0], W / 2, g),
                 lerp(self.wall.center(self.FOCUS)[1], H / 2, g))
        s *= 1 + 0.05 * smooth(lin(t, 6.2, self.D))
        dim = lin(t, 8.0, self.D - 0.4)
        self.wall.draw(f, t, s, focus, sat=lerp(0.8, 0.1, dim), bright=lerp(1, 0.5, dim),
                       hud=clamp(lin(t, 0.2, 1.0)))
        if t > 0.6:
            self.event(0.6, "whoosh_long", 0.6)
        if t >= 8.6:
            a = ease_out(lin(t, 8.6, 8.9))
            fill_rect(f, 960 - 340, 540 - 50, 960 + 340, 540 + 50, (8, 9, 11), 0.88 * a)
            overlay(f, a, lambda ov, ox, oy: cv2.rectangle(
                ov, (620 - ox, 490 - oy), (1300 - ox, 590 - oy), AMBER, 1, cv2.LINE_AA),
                (618, 488, 1302, 592))
            w, _ = text(f, "OBJECTS UNDERSTOOD: 0", 960, 540, "mono_bold", 36, AMBER, a, "cm")
            if int(t * 2.4) % 2 == 0:
                fill_rect(f, 960 + w / 2 + 6, 522, 960 + w / 2 + 24, 560, AMBER, a)
            self.event(8.6, "blip", 0.7)
        return self.fade(f, t, fin=0.6, fout=0.6)


# ---------------------------------------------------------------------- title
class Title(Scene):
    BOX = (330, 360, 1590, 720)

    def frame(self, t):
        f = canvas(BG)
        x0, y0, x1, y1 = self.BOX
        e = ease_out(lin(t, 0.1, 0.95))
        bx0, by0 = lerp(60, x0, e), lerp(60, y0, e)
        bx1, by1 = lerp(W - 60, x1, e), lerp(H - 60, y1, e)
        brackets(f, bx0, by0, bx1, by1, AMBER, arm=56, thick=3)
        self.event(0.1, "whoosh", 0.8)
        sweep = lerp(x0, x1 + 40, smooth(lin(t, 0.75, 1.75)))
        clip = (0, 0, int(sweep), H)
        text(f, "HOW MACHINES", 960, 476, "display", 118, WHITE, 1, "cm", tracking=6, clip=clip)
        text(f, "LEARNED TO SEE", 960, 610, "display", 118, AMBER, 1, "cm", tracking=6,
             clip=clip)
        if 0.75 < t < 1.8:
            a = window(t, 0.75, 1.75, 0.1)
            overlay(f, a, lambda ov, ox, oy: cv2.line(ov, (int(sweep) - ox, y0 + 18 - oy),
                                                      (int(sweep) - ox, y1 - 18 - oy),
                                                      (255, 230, 170), 3, cv2.LINE_AA))
            self.event(0.75, "hit", 1.0)
        if t > 1.8:
            chip(f, "TITLE 0.99", x0 - 1, y0 - 4, AMBER, size=24, alpha=ease_out(lin(t, 1.8, 2.0)))
            self.event(1.8, "blip", 0.8)
        text(f, "A SHORT DOCUMENTARY", 960, 790, "mono", 24, GREY, ease_out(lin(t, 2.1, 2.7)),
             "cm", tracking=10)
        return self.fade(f, t, fout=0.6)


# ---------------------------------------------------------------- summer 1966
def make_paper(seed=3):
    rng = np.random.default_rng(seed)
    low = cv2.resize(rng.normal(0, 1, (18, 32)).astype(np.float32), (W, H),
                     interpolation=cv2.INTER_CUBIC)
    fine = rng.normal(0, 1, (H, W)).astype(np.float32)
    fibre = cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 1.2, 6)
    p = np.array(PAPER, np.float32) + (low * 7 + fine * 3.5 + fibre * 10)[..., None]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    p *= np.clip(1.05 - 0.22 * r ** 2, 0, 1)[..., None]
    return np.clip(p, 0, 255).astype(np.uint8)


def make_stamp(word, color=(184, 40, 36)):
    f = font("type", 64)
    w = int(f.getlength(word)) + 60
    img = Image.new("RGBA", (w, 120), color + (0,))
    d = ImageDraw.Draw(img)
    d.rectangle((4, 4, w - 5, 115), outline=color + (255,), width=6)
    d.text((30, 22), word, font=f, fill=color + (255,))
    a = np.array(img)
    rng = np.random.default_rng(5)
    holes = cv2.GaussianBlur(rng.random(a.shape[:2]).astype(np.float32), (0, 0), 1.5)
    a[..., 3] = (a[..., 3] * np.clip((holes - 0.38) * 6, 0.25, 1)).astype(np.uint8)
    img = Image.fromarray(a).rotate(8, expand=True, resample=Image.BICUBIC)
    return np.array(img)


class Summer1966(Scene):
    LINES = [  # text, size, x, y
        ("MASSACHUSETTS INSTITUTE OF TECHNOLOGY", 34, 300, 200),
        ("Artificial Intelligence Group", 30, 300, 250),
        ("July 1966", 30, 300, 296),
        ("THE SUMMER VISION PROJECT", 66, 300, 392),
        ("Objective: a program that can look at a picture,", 33, 300, 520),
        ("pick out the objects in it, and name them.", 33, 300, 566),
    ]
    CPS = 30.0

    def __init__(self, spec):
        super().__init__(spec)
        self.paper = make_paper()
        self.stamp = make_stamp("ONE SUMMER")
        self.sched, t = [], 0.55
        for i, (s, size, x, y) in enumerate(self.LINES):
            self.sched.append(t)
            for k, ch in enumerate(s):
                if ch != " ":
                    self.event(t + k / self.CPS, "type", 0.55, key=("type", i, k))
            t += len(s) / self.CPS + (0.45 if i == 3 else 0.22)
            self.event(t - 0.12, "carriage", 0.5, key=("ret", i))
        self.typed_end = t

    def frame(self, t):
        f = self.paper.copy()
        cur = None
        for i, ((s, size, x, y), t0) in enumerate(zip(self.LINES, self.sched)):
            n = int(clamp((t - t0) * self.CPS, 0, len(s)))
            if n:
                w, h = text(f, s[:n], x, y, "type", size, INK, 0.92)
                if n < len(s) or (i + 1 < len(self.LINES) and t < self.sched[i + 1]):
                    cur = (x + w, y, size)
            if i == 3 and t > t0 + len(s) / self.CPS:
                u = ease_out(lin(t, t0 + len(s) / self.CPS, t0 + len(s) / self.CPS + 0.4))
                tw = text_rgba(s, "type", size, INK).shape[1]
                line(f, (x, y + 84), (x + tw * u, y + 84), INK, 3)
        if cur and t < self.S[1] and int(t * 3) % 2 == 0:
            fill_rect(f, cur[0] + 2, cur[1] + 8, cur[0] + 2 + cur[2] * 0.5, cur[1] + cur[2] + 6,
                      INK, 0.85)
        # "They gave themselves one summer."
        ts = self.S[1]
        if t > ts - 0.1:
            for j, m in enumerate(("JUNE", "JULY", "AUGUST")):
                a = ease_out(lin(t, ts + j * 0.15, ts + j * 0.15 + 0.3))
                bx = 300 + j * 300
                overlay(f, a * 0.9, lambda ov, ox, oy, bx=bx: cv2.rectangle(
                    ov, (bx - ox, 690 - oy), (bx + 270 - ox, 800 - oy), INK, 2, cv2.LINE_AA),
                    (bx - 2, 688, bx + 272, 802))
                text(f, m, bx + 135, 745, "type", 38, INK, a, "cm")
            u = smooth(lin(t, ts + 0.4, ts + 1.4))
            if u > 0:
                fill_rect(f, 300, 822, 300 + 870 * u, 832, (184, 40, 36), 0.85)
            ps = ts + 1.15
            if t > ps:
                k = 1 + 0.6 * (1 - ease_out(lin(t, ps, ps + 0.14)))
                st = self.stamp
                if k > 1.001:
                    st = cv2.resize(st, None, fx=k, fy=k, interpolation=cv2.INTER_LINEAR)
                blit(f, st, 1440 - st.shape[1] / 2, 745 - st.shape[0] / 2,
                     0.9 * lin(t, ps, ps + 0.06))
                self.event(ps, "stamp", 1.0)
        # slow push in on the paper
        z = 1 + 0.045 * smooth(lin(t, 0, self.S[2]))
        m = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z)
        f = cv2.warpAffine(f, m, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        # "It would take nearly half a century."
        t3 = self.S[2]
        k = smooth(lin(t, t3 - 0.1, t3 + 0.5))
        if k > 0:
            dark = canvas(BG)
            f = cv2.addWeighted(f, 1 - k, dark, k, 0)
            u = smooth(lin(t, t3 + 0.35, t3 + 1.85))
            year = int(round(lerp(1966, 2012, u)))
            self.event(t3 + 0.35, "count", 0.8)
            text(f, str(year), 960, 470, "display", 250, AMBER, k, "cm", tracking=4)
            x0, x1, y = 460, 1460, 680
            line(f, (x0, y), (x1, y), (70, 74, 82), 3)
            for dec in range(1970, 2011, 10):
                xx = lerp(x0, x1, (dec - 1966) / 46)
                line(f, (xx, y - 10), (xx, y + 10), (90, 94, 102), 2)
                text(f, str(dec), xx, y + 22, "mono", 20, GREY, k * 0.9, "ct")
            if u > 0:
                line(f, (x0, y), (lerp(x0, x1, u), y), AMBER, 5)
                cv2.circle(f, (int(lerp(x0, x1, u)), y), 9, AMBER, -1, cv2.LINE_AA)
            text(f, "1966", x0, y - 22, "mono_bold", 22, WHITE, k, "cb")
            text(f, "+46 YEARS", x1, y - 22, "mono_bold", 22, AMBER,
                 ease_out(lin(t, t3 + 1.85, t3 + 2.15)), "cb")
        return self.fade(f, t, fin=0.3, fout=0.3)


# --------------------------------------------------------------------- pixels
class Pixels(Scene):
    FACE_CLIP, FREEZE = "head-pose-face-detection-female-and-male", 1.9
    STREET_CLIP, STREET_T = "person-bicycle-car-detection", 41.0

    def __init__(self, spec):
        super().__init__(spec)
        self.face = Clip(self.FACE_CLIP)
        self.street = Clip(self.STREET_CLIP)
        self.freeze_img, idx = None, int(self.FREEZE * self.face.fps)
        faces = Dets(self.FACE_CLIP, "face").frames[idx]
        man = max(faces, key=lambda d: d[0])          # the face on the right
        self.ex, self.ey = int(man[6]), int(man[7])  # his right eye (image left)
        self.s1 = 112.0
        self.t_cut1, self.t_cut2 = 1.95, 2.9
        self.z0, self.z1 = 3.0, 6.0

    def zoom_state(self, t):
        e = smooth(lin(t, self.z0, self.z1))
        s0 = W / 768
        s = s0 * (self.s1 / s0) ** e
        g = smooth(lin(t, self.z0, self.z1 - 0.6))
        px = lerp(self.ex * s0, W / 2, g)
        py = lerp(self.ey * s0, H / 2, g)
        return s, self.ex - px / s, self.ey - py / s

    def grid_image(self, img, s, x0, y0):
        m = np.float32([[s, 0, -(x0 - 0.5) * s], [0, s, -(y0 - 0.5) * s]])
        near = cv2.warpAffine(img, m, (W, H), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE)
        if s >= 9:
            return near
        m2 = np.float32([[s, 0, -x0 * s], [0, s, -y0 * s]])
        smooth_img = cv2.warpAffine(img, m2, (W, H), flags=cv2.INTER_LINEAR,
                                    borderMode=cv2.BORDER_REPLICATE)
        u = lin(s, 5, 9)
        return cv2.addWeighted(near, u, smooth_img, 1 - u, 0) if u > 0 else smooth_img

    def cells(self, s, x0, y0):
        i0 = int(math.floor(x0 - 0.5)) - 1
        j0 = int(math.floor(y0 - 0.5)) - 1
        for j in range(j0, j0 + int(H / s) + 3):
            for i in range(i0, i0 + int(W / s) + 3):
                cx, cy = (i - x0 + 0.5) * s, (j - y0 + 0.5) * s
                if -s < cx < W + s and -s < cy < H + s and 0 <= i < 768 and 0 <= j < 432:
                    yield i, j, cx, cy

    def frame(self, t):
        if t < self.t_cut1:
            img, _ = self.face.at(t * 0.9 + self.FREEZE - self.t_cut1 * 0.9)
            v = View(img.shape[1], img.shape[0], zoom=1 + 0.04 * t / self.t_cut1)
            f = grade(v.render(img))
        elif t < self.t_cut2:
            img, _ = self.street.at(self.STREET_T + t - self.t_cut1)
            f = grade(View(img.shape[1], img.shape[0], zoom=1.1).render(img))
            self.event(self.t_cut1, "cut", 0.4)
        else:
            if self.freeze_img is None:
                self.freeze_img = grade(self.face.at(self.FREEZE)[0], sat=0.9)
            img = self.freeze_img
            s, x0, y0 = self.zoom_state(t)
            self.event(self.z0, "zoom", 0.9)
            split = lin(t, self.S[2] + 0.1, self.S[2] + 1.2)
            if split <= 0:
                f = self.grid_image(img, s, x0, y0)
                self.draw_grid(f, img, s, x0, y0, t)
            else:
                f = self.draw_split(img, s, x0, y0, t, smooth(split))
            self.caption(f, t)
        return self.fade(f, t, fout=0.35)

    def draw_grid(self, f, img, s, x0, y0, t):
        ga = lin(s, 22, 55)
        if ga > 0:
            def draw(ov, ox, oy):
                i0 = int(math.floor(x0 - 0.5))
                for i in range(i0, i0 + int(W / s) + 3):
                    X = int(round((i - x0) * s))
                    cv2.line(ov, (X, 0), (X, H), (0, 0, 0), 2)
                j0 = int(math.floor(y0 - 0.5))
                for j in range(j0, j0 + int(H / s) + 3):
                    Y = int(round((j - y0) * s))
                    cv2.line(ov, (0, Y), (W, Y), (0, 0, 0), 2)
            overlay(f, 0.55 * ga, draw)
        na = lin(s, 70, 104)
        if na > 0:
            size = int(s * 0.165)
            for i, j, cx, cy in self.cells(s, x0, y0):
                r, g, b = (int(v) for v in img[j, i])
                lum = 0.3 * r + 0.59 * g + 0.11 * b
                col = (20, 20, 20) if lum > 150 else (245, 245, 240)
                for k, (lab, v) in enumerate((("R", r), ("G", g), ("B", b))):
                    text(f, f"{lab} {v:3d}", cx, cy + (k - 1) * s * 0.23, "mono_bold", size, col,
                         na * 0.95, "cm")

    def draw_split(self, img, s, x0, y0, t, e):
        """Pull the grid apart into its red, green and blue layers.

        Starts additive (the three layers sum back to the original picture),
        ends as a stack of opaque sheets with each layer's numbers."""
        base = self.grid_image(img, s, x0, y0)
        add, stack = canvas((0, 0, 0)), canvas((0, 0, 0))
        k = lerp(1.0, 0.42, e)
        lw, lh = int(W * k), int(H * k)
        centers = [(lerp(960, 530, e), lerp(540, 330, e)), (960, 540),
                   (lerp(960, 1390, e), lerp(540, 750, e))]
        words = [self.S[2] + 1.45, self.S[2] + 1.85, self.S[2] + 2.35]
        names = [("RED", (255, 90, 90)), ("GREEN", (90, 235, 120)), ("BLUE", (110, 160, 255))]
        cells = [c for c in self.cells(s, x0, y0)
                 if s / 2 <= c[2] <= W - s / 2 and s / 2 <= c[3] <= H - s / 2]
        na = lin(e, 0.65, 1.0)
        placed = []
        for c in (2, 1, 0):
            layer = np.zeros_like(base)
            layer[..., c] = base[..., c]
            small = cv2.resize(layer, (lw, lh), interpolation=cv2.INTER_AREA if k < 1 else
                               cv2.INTER_NEAREST)
            hl = window(t, words[c] - 0.05, words[c] + 0.7, 0.15)
            small = cv2.convertScaleAbs(small, alpha=1 + 0.5 * e + 0.4 * hl)
            if na > 0:
                for i, j, ccx, ccy in cells:
                    text(small, str(int(img[j, i][c])), ccx * k, ccy * k, "mono_bold",
                         int(s * k * 0.3), (235, 235, 235), na * 0.9, "cm")
                cv2.rectangle(small, (0, 0), (lw - 1, lh - 1), names[c][1], 2, cv2.LINE_AA)
            X, Y = int(centers[c][0] - lw / 2), int(centers[c][1] - lh / 2)
            region = add[max(Y, 0):Y + lh, max(X, 0):X + lw]
            src = small[max(-Y, 0):max(-Y, 0) + region.shape[0],
                        max(-X, 0):max(-X, 0) + region.shape[1]]
            cv2.add(region, src, dst=region)
            paste(stack, small, X, Y)
            placed.append((c, X, Y))
        u = smooth(lin(e, 0.3, 0.8))
        f = cv2.addWeighted(add, 1 - u, stack, u, 0) if u > 0 else add
        for c, X, Y in placed:
            wa = ease_out(lin(t, words[c], words[c] + 0.25))
            if wa > 0:
                chip(f, names[c][0], X, Y + lh + 10, names[c][1], size=24, alpha=wa, anchor="lt")
                self.event(words[c], "blip", 0.6)
        return f

    def caption(self, f, t):
        t0 = self.S[1] + 1.35
        a = ease_out(lin(t, t0, t0 + 0.3)) * lin(t, self.S[2] + 0.45, self.S[2] + 0.1)
        if a <= 0:
            return
        fill_rect(f, 90, 800, 820, 990, (8, 9, 12), 0.8 * a)
        fill_rect(f, 90, 800, 96, 990, AMBER, a)
        text(f, "ONE HD VIDEO FRAME", 126, 822, "mono_bold", 22, AMBER, a)
        text(f, "1920 × 1080 pixels × 3 colors", 126, 862, "sans", 34, WHITE, a)
        n = int(6220800 * ease_out(lin(t, t0, t0 + 1.0)))
        text(f, f"= {n:,} numbers", 126, 912, "display", 44, AMBER, a)
        self.event(t0, "count", 0.6)
