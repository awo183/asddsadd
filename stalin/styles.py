"""Four alternative visual styles, rendered as previews of the same hook
(0:00-0:14: the half-demolished statue, its 15.5 m height, Letná today, the
title), so the looks can be compared side by side.

usage:
  styles.py render [style ...]   -> build/stalin/styles/<style>.mp4 (with narration, music, effects)
  styles.py sheet                -> build/stalin/styles/sheet.jpg (one frame per beat and style)
"""
import math
import os
import subprocess
import sys

import cv2
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vox as V  # noqa: E402
from vox import FPS, H, W, clamp, ease_back, ease_io, ease_out, ease_out_expo, lerp, lin  # noqa: E402

OUT = os.path.join(V.BUILD, "styles")
IMG = os.path.join(V.BUILD, "assets", "img")
BEATS = [(0.0, 5.24), (5.24, 7.88), (7.88, 11.72), (11.72, 14.4)]   # same cut points as the film's hook
DUR = BEATS[-1][1]


def load(name):
    p = os.path.join(IMG, name)
    return V.load_rgba(p) if p.endswith(".png") else V.load_rgb(p)


def beat_of(t):
    for k, (a, b) in enumerate(BEATS):
        if t < b:
            return k, t - a, b - a
    return len(BEATS) - 1, t - BEATS[-1][0], BEATS[-1][1] - BEATS[-1][0]


def halftone(img, w, h, cell=9, ink=(20, 18, 16), paper=(237, 227, 204), zoom=1.0, cx=0.5, cy=0.5, angle=0.0):
    """Printed-dot version of a photo, as a static (h, w) RGB image."""
    g8 = cv2.cvtColor(V.cover(img, w, h, zoom, cx, cy), cv2.COLOR_RGB2GRAY)
    g8 = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(6, 6)).apply(g8)
    g = np.clip((g8.astype(np.float32) / 255 - 0.5) * 1.3 + 0.5, 0, 1)
    out = np.empty((h, w, 3), np.uint8)
    out[:] = paper
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    big = int(max(w, h) * 1.5)
    for gy in range(-big // 2, big // 2, cell):
        for gx in range(-big // 2, big // 2, cell):
            x = w / 2 + gx * c - gy * s
            y = h / 2 + gx * s + gy * c
            if 0 <= x < w and 0 <= y < h:
                r = (1 - g[int(y), int(x)]) ** 0.9 * cell * 0.62
                if r > 0.6:
                    cv2.circle(out, (int(x * 4), int(y * 4)), int(r * 4), ink, -1, cv2.LINE_AA, shift=2)
    return out


def chip(text, color, px=30, py=15):
    """Text image on a solid colour plate, as RGBA."""
    out = np.zeros((text.shape[0] + 2 * py, text.shape[1] + 2 * px, 4), np.uint8)
    rgb = np.empty(out.shape[:2] + (3,), np.uint8)
    rgb[:] = color
    V.blit(rgb, text, px, py)
    out[..., :3], out[..., 3] = rgb, 255
    return out


def word_times():
    import layout
    return layout.layout()["voice"][0]["words"]


# =====================================================================================
# 1. CONSTRUCTIVIST: red / black / cream, diagonals, halftone, sunburst
# =====================================================================================
class Constructivist:
    name = "constructivist"
    RED, BLACK, CREAM = (200, 22, 40), (17, 16, 15), (237, 227, 204)

    def __init__(self):
        self.paper = V.paper(seed=201, tone=self.CREAM)
        self.ht1 = halftone(load("demolition_scaffold.jpg"), 1050, 720, 7, zoom=1.9, cx=0.42, cy=0.2)
        self.cut = load("monument_side_cut.png")
        self.ht_cut = halftone(self.cut[..., :3], self.cut.shape[1], self.cut.shape[0], 6, ink=self.BLACK,
                               paper=(255, 255, 255))
        a = cv2.resize(self.cut[..., 3], (self.ht_cut.shape[1], self.ht_cut.shape[0]))
        self.ht_cut = np.dstack([self.ht_cut, a])
        m = load("metronome_today2.jpg")
        self.ht3 = halftone(m, 900, 900, 8, ink=self.BLACK, paper=self.CREAM, zoom=1.0, cx=0.45, cy=0.45)

    def bg(self, t):
        return V.cover(self.paper, W, H, 1.0 + 0.02 * t / DUR)

    def wedge(self, f, u, color, pts):
        p = np.array(pts, np.float32)
        ctr = p.mean(0)
        p = ctr + (p - ctr) * u
        cv2.fillPoly(f, [np.round(p * 4).astype(np.int32)], color, cv2.LINE_AA, shift=2)

    def frame(self, t):
        k, lt, d = beat_of(t)
        f = self.bg(t)
        R, B, C = self.RED, self.BLACK, self.CREAM
        if k == 0:
            u = ease_out(lin(lt, 0, 0.5))
            self.wedge(f, u, R, [(0, 0), (1150, 0), (520, H), (0, H)])
            card = np.dstack([self.ht1, np.full(self.ht1.shape[:2], 255, np.uint8)])
            sc = lerp(0.92, 1.02, ease_io(lin(lt, 0, d)))
            V.place(f, card, 1270 - 40 * ease_out(lin(lt, 0, 0.6)), 560, sc, -6, ease_out(lin(lt, 0.1, 0.5)))
            yr = V.text_img("1962", "anton", 300, C)
            V.place(f, yr, 300, 330 + (1 - ease_out(lin(lt, 0.3, 0.7))) * 80, 1.0, -8, lin(lt, 0.3, 0.6),
                    shadow=False)
            bh = chip(V.text_img("ŘÍJEN", "oswald", 110, C, tracking=12), B)
            V.place(f, bh, 300, 590, 1.0, -8, lin(lt, 0.5, 0.8), shadow=False)
            hu = lin(lt, 3.9, 4.5)
            if hu:
                cv2.ellipse(f, (1200, 330), (170, 150), -20, -90, -90 + 360 * ease_out(hu), R, 16, cv2.LINE_AA)
        elif k == 1:
            self.wedge(f, 1.0, B, [(W * 0.55, 0), (W, 0), (W, H), (W * 0.35, H)])
            sc = 760 / self.ht_cut.shape[0]
            V.place(f, self.ht_cut, 620, 560, sc * lerp(0.94, 1.0, ease_out(lin(lt, 0, 0.5))), 0, 1.0,
                    shadow=False)
            u = ease_out_expo(lin(lt, 0.2, 1.4))
            cv2.rectangle(f, (int(W * 0.62), int(900 - 640 * u)), (int(W * 0.62) + 46, 900), R, -1)
            num = V.text_img(f"{15.5 * u:.1f}".replace(".", ","), "anton", 300, C)
            V.place(f, num, W * 0.82, 470, 1.0, 0, 1.0, shadow=False)
            m = V.text_img("METRŮ", "oswald", 120, R, tracking=14)
            V.place(f, m, W * 0.82, 690, 1.0, 0, lin(lt, 0.8, 1.1), shadow=False)
        elif k == 2:
            u = ease_out(lin(lt, 0, 0.6))
            cv2.circle(f, (640, 540), int(470 * u), R, -1, cv2.LINE_AA)
            mask = np.zeros(self.ht3.shape[:2], np.uint8)
            cv2.circle(mask, (450, 450), 420, 255, -1, cv2.LINE_AA)
            disc = np.dstack([self.ht3, mask])
            V.place(f, disc, 640, 540, lerp(0.8, 1.0, ease_back(lin(lt, 0.1, 0.6))), lt * 4, lin(lt, 0.1, 0.4),
                    shadow=False)
            for j, txt in enumerate(["SRAZ", "NA", "STALINU"]):
                im = V.text_img(txt, "anton", 200, B if j != 2 else R)
                V.place(f, im, 1380 + (1 - ease_out(lin(lt, 0.8 + j * 0.25, 1.2 + j * 0.25))) * 400, 280 + j * 220,
                        1.0, -8, lin(lt, 0.8 + j * 0.25, 1.0 + j * 0.25), shadow=False)
            bar = chip(V.text_img("LETNÁ · DNES", "oswald", 54, C, tracking=8), B, 25, 12)
            V.place(f, bar, 640, 1000, 1.0, 0, lin(lt, 0.3, 0.6), shadow=False)
        else:
            f[:] = R
            rot = lt * 6
            for j in range(18):
                a0 = math.radians(rot + j * 20)
                a1 = math.radians(rot + j * 20 + 9)
                pts = [(W / 2, H / 2 + 120), (W / 2 + 2400 * math.cos(a0), H / 2 + 120 + 2400 * math.sin(a0)),
                       (W / 2 + 2400 * math.cos(a1), H / 2 + 120 + 2400 * math.sin(a1))]
                cv2.fillPoly(f, [np.array(pts, np.int32)], (178, 16, 32), cv2.LINE_AA)
            s1 = V.text_img("STALIN", "anton", 330, B)
            V.place(f, s1, W / 2, 400, lerp(1.25, 1.0, V.ease_in(lin(lt, 0, 0.15))), -4, lin(lt, 0, 0.1),
                    shadow=False)
            bh = chip(V.text_img("NA SPLÁTKY", "anton", 170, C, tracking=6), B, 45, 20)
            V.place(f, bh, W / 2, 720, lerp(1.25, 1.0, V.ease_in(lin(lt, 0.15, 0.3))), -4, lin(lt, 0.15, 0.25),
                    shadow=False)
        return V.finish(f, int(t * FPS), 3.5, 0.25)

    sfx = [(0.05, "stamp", 0.8), (4.3, "marker", 0.6), (5.3, "whoosh", 0.6), (6.6, "hit", 0.7),
           (7.95, "whoosh", 0.6), (8.8, "pop", 0.5), (11.72, "impact", 1.0), (11.75, "boom", 0.6)]


# =====================================================================================
# 2. DARK CINEMATIC MINIMAL: black, letterbox, thin type, focus pulls, dark map
# =====================================================================================
class Minimal:
    name = "minimal"
    WHITE = (236, 234, 228)
    ACC = (228, 196, 120)

    def __init__(self):
        self.p1 = V.bw(load("demolition_scaffold.jpg"), 1.15)
        self.cut = load("monument_side_cut.png")
        import maps
        raw, self.mx0, self.my0 = maps.mosaic(14.4172, 50.0944, 15, 12, 8)
        g = cv2.cvtColor(raw, cv2.COLOR_RGB2GRAY).astype(np.float32)
        r, gg, b = [raw[..., i].astype(np.float32) for i in range(3)]
        water = np.clip((b - gg - 2) / 4, 0, 1) * (g < 226)
        land = np.clip((g - 200) / 55, 0, 1)
        dark = np.stack([12 + 30 * (1 - land), 12 + 30 * (1 - land), 14 + 32 * (1 - land)], -1)
        roads = np.clip((g - 245) / 10, 0, 1)[..., None]
        dark = dark * (1 - roads) + np.array([70, 70, 74]) * roads
        dark = dark * (1 - water[..., None]) + np.array([14, 30, 42]) * water[..., None]
        self.map = np.clip(dark, 0, 255).astype(np.uint8)

    def letterbox(self, f, u=1.0):
        bar = int(H * 0.12 * u)
        f[:bar] = 0
        f[H - bar:] = 0

    def thin(self, f, s, x, y, size=40, a=1.0, ax=0.0, color=None, font="mont_med", tracking=10):
        im = V.text_img(s, font, size, color or self.WHITE, tracking=tracking)
        V.place(f, im, x, y, 1.0, 0, a, shadow=False, ax=ax, ay=0.5)
        return im.shape[1]

    def frame(self, t):
        k, lt, d = beat_of(t)
        if k == 0:
            f = V.cover(self.p1, W, H, lerp(1.5, 1.75, ease_io(lin(lt, 0, d))), 0.42, 0.22)
            blur = lerp(14, 0, ease_out(lin(lt, 0, 1.4)))
            if blur > 0.3:
                f = cv2.GaussianBlur(f, (0, 0), blur)
            cv2.convertScaleAbs(f, dst=f, alpha=0.85)
            self.letterbox(f)
            a = lin(lt, 1.0, 1.6)
            w = self.thin(f, "PRAHA, LETNÁ", 140, H - 230, 34, a)
            self.thin(f, "ŘÍJEN 1962", 140, H - 180, 26, a, color=self.ACC, tracking=14)
            cv2.line(f, (140, H - 205), (140 + int(w * ease_out(lin(lt, 1.2, 2.0))), H - 205), self.WHITE, 1,
                     cv2.LINE_AA)
            hu = ease_out(lin(lt, 3.9, 4.7))
            if hu:
                cx, cy = W * 0.52, H * 0.36
                cv2.ellipse(f, (int(cx), int(cy)), (210, 210), 0, -90, -90 + 360 * hu, self.WHITE, 2, cv2.LINE_AA)
                self.thin(f, "HLAVA", cx + 240, cy - 160, 26, hu, tracking=12)
                cv2.line(f, (int(cx + 150), int(cy - 150)), (int(cx + 230), int(cy - 160)), self.WHITE, 1,
                         cv2.LINE_AA)
        elif k == 1:
            f = np.zeros((H, W, 3), np.uint8)
            yy = np.arange(H)[:, None]
            f[:] = (np.clip(26 - np.abs(yy - H * 0.6) / 30, 6, 26)).astype(np.uint8)[..., None]
            for x in range(0, W, 120):
                cv2.line(f, (x, 0), (x, H), (24, 24, 26), 1)
            sc = 640 / self.cut.shape[0]
            gray = cv2.cvtColor(cv2.cvtColor(self.cut[..., :3], cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB)
            cut = np.dstack([(gray * 0.9).astype(np.uint8), self.cut[..., 3]])
            V.place(f, cut, 780, 880, sc * lerp(1.0, 1.04, lin(lt, 0, d)), 0, ease_out(lin(lt, 0, 0.6)),
                    shadow=False, ay=1.0)
            u = ease_out_expo(lin(lt, 0.3, 1.6))
            x = 1230
            top = 880 - 640 * u
            cv2.line(f, (x, 880), (x, int(top)), self.ACC, 2, cv2.LINE_AA)
            for j in range(16):
                yj = 880 - 40 * j
                if yj < top:
                    break
                cv2.line(f, (x, yj), (x + (18 if j % 5 == 0 else 9), yj), self.ACC, 1, cv2.LINE_AA)
            self.thin(f, f"{15.5 * u:05.2f}".replace(".", ",") + " M", x + 50, top, 92, 1.0, font="mont",
                      tracking=6)
            self.thin(f, "VÝŠKA SOCHY", x + 52, top + 80, 28, lin(lt, 1.0, 1.4), color=(150, 150, 150))
            self.letterbox(f)
        elif k == 2:
            import maps
            z = lerp(15.2, 16.1, ease_io(lin(lt, 0, d)))
            tx, ty = maps.tile_xy(14.4172, 50.0944, 15)
            px, py = (tx - self.mx0) * 256, (ty - self.my0) * 256
            sc = 2 ** (z - 15)
            M = np.float32([[sc, 0, W / 2 - px * sc], [0, sc, H / 2 - py * sc]])
            f = cv2.warpAffine(self.map, M, (W, H), borderMode=cv2.BORDER_REPLICATE)
            pu = lin(lt, 0.4, 0.8)
            if pu:
                ph = (lt % 1.6) / 1.6
                ov = f.copy()
                cv2.circle(ov, (W // 2, H // 2), int(14 + 90 * ph), self.ACC, 2, cv2.LINE_AA)
                cv2.addWeighted(ov, 1 - ph, f, ph, 0, dst=f)
                glow = np.zeros_like(f)
                cv2.circle(glow, (W // 2, H // 2), 26, self.ACC, -1, cv2.LINE_AA)
                f = cv2.add(f, cv2.GaussianBlur(glow, (0, 0), 14))
                cv2.circle(f, (W // 2, H // 2), 7, (255, 245, 220), -1, cv2.LINE_AA)
                cv2.line(f, (W // 2 + 12, H // 2 - 12), (W // 2 + 120, H // 2 - 120), self.WHITE, 1, cv2.LINE_AA)
                self.thin(f, "LETNÁ", W // 2 + 135, H // 2 - 140, 34, pu)
                self.thin(f, "50.094° N  14.417° E", W // 2 + 137, H // 2 - 96, 20, pu, color=(150, 150, 150),
                          font="cp")
            self.thin(f, "„SRAZ NA STALINU“", W / 2, H - 200, 44, lin(lt, 1.5, 2.1), ax=0.5, font="play_reg",
                      tracking=4)
            self.letterbox(f)
        else:
            f = np.zeros((H, W, 3), np.uint8)
            a = ease_out(lin(lt, 0.0, 0.9))
            tr = int(lerp(60, 26, a))
            im = V.text_img("STALIN NA SPLÁTKY", "play", 120, self.WHITE, tracking=tr)
            V.place(f, im, W / 2, H / 2 - 20, 1.0, 0, a, shadow=False)
            w = int(im.shape[1] * 0.5 * ease_out(lin(lt, 0.5, 1.3)))
            cv2.line(f, (W // 2 - w, H // 2 + 70), (W // 2 + w, H // 2 + 70), self.ACC, 2, cv2.LINE_AA)
            self.thin(f, "DOKUMENT", W / 2, H / 2 + 120, 24, lin(lt, 0.9, 1.4), ax=0.5, color=(150, 150, 150),
                      tracking=22)
        return V.finish(f, int(t * FPS), 3.0, 0.5)

    sfx = [(0.2, "whoosh_big", 0.5), (4.0, "ping", 0.5), (5.3, "sub", 0.5), (7.95, "whoosh", 0.4),
           (8.4, "ping", 0.6), (11.72, "boom", 0.7)]


# =====================================================================================
# 3. COLD WAR DOSSIER: desk, folder, polaroids, typewriter, redaction, red string
# =====================================================================================
class Dossier:
    name = "dossier"
    RED = (176, 26, 30)

    def __init__(self):
        rng = np.random.default_rng(301)
        yy, xx = np.mgrid[0:H + 200, 0:W + 200].astype(np.float32)
        n = V._noise(H + 200, W + 200, 40, rng)
        grain = np.sin(yy / 5.0 + n * 2.2 + np.sin(xx / 500) * 1.5) * 0.5 + 0.5
        grain = grain * 0.7 + V._noise(H + 200, W + 200, 6, rng) * 0.3
        wood = np.stack([62 + 30 * grain, 38 + 18 * grain, 24 + 10 * grain], -1)
        self.desk = np.clip(wood + rng.normal(0, 3, wood.shape), 0, 255).astype(np.uint8)
        cork = rng.normal(0, 1, (H, W)).astype(np.float32)
        cork = cv2.GaussianBlur(cork, (0, 0), 1.2) * 18
        self.cork = np.clip(np.stack([150 + cork, 110 + cork * 0.8, 70 + cork * 0.6], -1), 0, 255).astype(np.uint8)
        self.polaroid1 = self.polaroid(load("demolition_scaffold.jpg"), 760, "LETNÁ, 10/1962", zoom=1.7,
                                       c=(0.42, 0.22))
        self.polaroid2 = self.polaroid(load("metronome_today2.jpg"), 520, "METRONOM, DNES")
        cut = load("monument_side.jpg")
        self.clip = V.card(cut, 640, border=14, seed=4)
        self.folder = self.make_folder()
        import maps
        raw, self.mx0, self.my0 = maps.mosaic(14.4172, 50.0944, 15, 12, 8)
        self.map = maps.recolor_city(raw)

    def polaroid(self, img, w, caption, zoom=1.0, c=(0.5, 0.5)):
        h = int(w * 1.18)
        out = np.zeros((h, w, 4), np.uint8)
        out[..., :3], out[..., 3] = (244, 241, 232), 255
        pw = w - 60
        ph = pw
        out[30:30 + ph, 30:30 + pw, :3] = V.bw(V.cover(img, pw, ph, zoom, *c), 1.1, 0.03, (1.0, 0.97, 0.9))
        tmp = out[..., :3].copy()
        im = V.text_img(caption, "caveat", int(w * 0.085), (40, 40, 60))
        V.blit(tmp, im, w / 2 - im.shape[1] / 2, 30 + ph + (h - 30 - ph) / 2 - im.shape[0] / 2)
        out[..., :3] = tmp
        return out

    def make_folder(self):
        w, h = 1500, 980
        out = np.zeros((h, w, 4), np.uint8)
        pap = V.cover(V.paper(seed=302, tone=(214, 182, 128)), w, h)
        out[..., :3], out[..., 3] = pap, 255
        cv2.rectangle(out, (0, 0), (420, 70), (0, 0, 0, 0), -1)
        tab = V.cover(V.paper(seed=303, tone=(206, 174, 120)), 380, 70)
        out[0:70, 20:400, :3] = tab
        out[0:70, 20:400, 3] = 255
        tmp = out[..., :3].copy()
        V.blit(tmp, V.text_img("SPIS Č. 1962/14", "type", 40, (60, 40, 30)), 50, 14)
        out[..., :3] = tmp
        return out

    def typed(self, f, s, x, y, t0, t, size=54, cps=18, color=(30, 28, 26)):
        n = int(max(t - t0, 0) * cps)
        if n <= 0:
            return
        im = V.text_img(s[:n], "type", size, color)
        V.blit(f, im, x, y)

    def frame(self, t):
        k, lt, d = beat_of(t)
        f = V.cover(self.desk, W, H, 1.0 + 0.03 * t / DUR, 0.5, 0.5)
        if k in (0, 1):
            V.place(f, self.folder, W / 2, H / 2 + 40, 1.0, -1.5, 1.0)
        if k == 0:
            u = lin(lt, 0.0, 0.35)
            V.place(f, self.polaroid1, 620, 520, lerp(1.3, 1.0, ease_out(u)), -6, clamp(u * 2))
            self.typed(f, "MÍSTO:  LETNÁ, PRAHA", 1070, 330, 0.6, lt)
            self.typed(f, "DATUM:  ŘÍJEN 1962", 1070, 410, 1.6, lt)
            self.typed(f, "AKCE:   ODSTRANĚNÍ", 1070, 490, 2.5, lt)
            if lt > 3.6:
                st = V.stamp("PŘÍSNĚ TAJNÉ", self.RED, 90, 7)
                uu = lin(lt, 3.6, 3.75)
                V.place(f, st, 1350, 700, lerp(1.7, 1.0, V.ease_in(uu)), -9, 0.9 * clamp(uu * 2), shadow=False,
                        mode="multiply")
            hu = lin(lt, 4.0, 4.6)
            if hu:
                V.draw_path(f, V.circle_pts(640, 300, 120, 100, 5), V.sine_io(hu), self.RED, 7)
        elif k == 1:
            V.place(f, self.clip, 640, 560, 1.0, 3, 1.0)
            self.typed(f, "VÝŠKA SOCHY:", 1070, 380, 0.0, lt, 60, 30)
            num = V.text_img("15,5 m", "type", 110, (30, 28, 26))
            V.blit(f, num, 1070, 470)
            ru = ease_io(lin(lt, 0.7, 1.4))
            if ru < 1:
                x0 = 1060 + int((num.shape[1] + 30) * ru)
                cv2.rectangle(f, (x0, 470), (1060 + num.shape[1] + 30, 470 + num.shape[0]), (14, 14, 14), -1)
            self.typed(f, "(ověřeno)", 1075, 610, 1.6, lt, 40, 20, (90, 80, 70))
        elif k == 2:
            f[:] = self.cork
            import maps
            tx, ty = maps.tile_xy(14.4172, 50.0944, 15)
            px, py = (tx - self.mx0) * 256, (ty - self.my0) * 256
            mapw, maph = 1100, 760
            M = np.float32([[1.4, 0, mapw / 2 - px * 1.4], [0, 1.4, maph / 2 - py * 1.4]])
            mp = cv2.warpAffine(self.map, M, (mapw, maph), borderMode=cv2.BORDER_REPLICATE)
            card = np.dstack([mp, np.full((maph, mapw), 255, np.uint8)])
            V.place(f, card, 1150, 560, 1.0, 2, 1.0)
            pin = (1150, 560)
            cv2.circle(f, pin, 16, self.RED, -1, cv2.LINE_AA)
            cv2.circle(f, (pin[0] - 4, pin[1] - 4), 5, (255, 200, 200), -1, cv2.LINE_AA)
            u = lin(lt, 0.0, 0.35)
            V.place(f, self.polaroid2, 420, 470, lerp(1.25, 1.0, ease_out(u)), -7, clamp(u * 2))
            su = ease_io(lin(lt, 0.6, 1.4))
            if su:
                p0 = np.array([520, 300], float)
                p1 = np.array(pin, float)
                pts = [p0 + (p1 - p0) * s + np.array([0, 60 * math.sin(math.pi * s)]) for s in np.linspace(0, su, 30)]
                cv2.polylines(f, [np.array(pts, np.int32)], False, self.RED, 4, cv2.LINE_AA)
                cv2.circle(f, (520, 300), 12, self.RED, -1, cv2.LINE_AA)
            nb = chip(V.text_img("„sraz na Stalinu“", "caveat", 80, (30, 30, 70)), (250, 236, 120), 30, 20)
            V.place(f, nb, 1450, 900, 1.0, -4, ease_out(lin(lt, 1.6, 2.0)))
        else:
            V.place(f, self.folder, W / 2, H / 2 + 40, 1.0, -1.5, 1.0)
            t1 = V.text_img("STALIN", "type", 200, (30, 26, 22))
            t2 = V.text_img("NA SPLÁTKY", "type", 140, (30, 26, 22))
            n = int(lt * 22)
            V.blit(f, V.text_img("STALIN"[:n] or " ", "type", 200, (30, 26, 22)), W / 2 - t1.shape[1] / 2, 300)
            if n > 6:
                V.blit(f, V.text_img("NA SPLÁTKY"[:n - 6], "type", 140, (30, 26, 22)), W / 2 - t2.shape[1] / 2, 560)
            if lt > 0.9:
                st = V.stamp("ARCHIV", self.RED, 120, 11)
                uu = lin(lt, 0.9, 1.05)
                V.place(f, st, W / 2 + 420, 820, lerp(1.7, 1.0, V.ease_in(uu)), -10, 0.9 * clamp(uu * 2),
                        shadow=False, mode="multiply")
        yy, xx = np.ogrid[0:H, 0:W]
        lamp = np.clip(1.15 - np.sqrt(((xx - W * 0.45) / W) ** 2 + ((yy - H * 0.35) / H) ** 2) * 1.1, 0.35, 1.05)
        f = np.clip(f * lamp[..., None], 0, 255).astype(np.uint8)
        return V.finish(f, int(t * FPS), 4.0, 0.3)

    sfx = [(0.05, "paper", 0.9), (0.6, "typewriter", 0.6), (1.6, "typewriter", 0.5), (2.5, "typewriter", 0.5),
           (3.6, "stamp", 1.0), (4.0, "marker", 0.6), (5.25, "paper_slide", 0.6), (5.9, "pen", 0.5),
           (7.9, "pop", 0.6), (8.5, "pen", 0.5), (11.72, "typewriter", 0.7), (12.65, "stamp", 1.0)]


# =====================================================================================
# 4. NEWSPAPER PRINT: halftone pages, columns, headlines, page turns
# =====================================================================================
class Newspaper:
    name = "newspaper"
    INK = (24, 22, 20)
    NEWS = (232, 226, 210)

    def __init__(self):
        self.page1 = self.page("LETNÁ, ŘÍJEN 1962", "Dělníci sbíječkami rozbíjejí hlavu obří sochy",
                               halftone(load("demolition_scaffold.jpg"), 1700, 900, 7, self.INK, self.NEWS, 1.6,
                                        0.42, 0.22, 15), seed=1)
        cut = load("monument_side.jpg")
        self.page2 = self.page("15,5 METRU", "Tak vysoký byl Stalin na Letné",
                               halftone(cut, 1700, 900, 7, self.INK, self.NEWS, 1.0, 0.5, 0.4, 15), seed=2)
        self.page3 = self.page("DNES: SRAZ NA STALINU", "Kde dnes stojí metronom, stál kdysi Stalin",
                               halftone(load("metronome_today.jpg"), 1700, 900, 7, self.INK, self.NEWS, 1.0, 0.5,
                                        0.5, 15), seed=3)

    def page(self, head, sub, photo, seed=0):
        w, h = 1900, 2300
        pg = V.cover(V.paper(seed=400 + seed, tone=self.NEWS), w, h)
        cv2.rectangle(pg, (80, 70), (w - 80, 76), self.INK, -1)
        V.blit(pg, V.text_img("LETENSKÝ VĚSTNÍK", "play", 120, self.INK, tracking=6), 100, 90)
        cv2.rectangle(pg, (80, 260), (w - 80, 264), self.INK, -1)
        V.blit(pg, V.text_img("ROČNÍK XIV · ČÍSLO 248 · CENA 50 HALÉŘŮ", "cp", 34, self.INK), 100, 274)
        cv2.rectangle(pg, (80, 330), (w - 80, 332), self.INK, -1)
        lines = V.wrap(head, "play", 170, w - 200)
        y = 360
        for ln in lines:
            im = V.text_img(ln, "play", 170, self.INK)
            V.blit(pg, im, 100, y)
            y += 190
        V.blit(pg, V.text_img(sub, "play_reg", 64, (60, 56, 50)), 100, y + 10)
        y += 120
        pg[y:y + photo.shape[0], 100:100 + photo.shape[1]] = photo[:, :min(photo.shape[1], w - 200)]
        self.photo_y = y
        y += photo.shape[0] + 30
        rng = np.random.default_rng(seed)
        cw = (w - 200 - 3 * 40) / 4
        for c in range(4):
            for r in range(26):
                x0 = 100 + c * (cw + 40)
                ln = cw * (rng.uniform(0.75, 1.0) if r % 7 != 6 else rng.uniform(0.3, 0.6))
                cv2.line(pg, (int(x0), int(y + r * 34)), (int(x0 + ln), int(y + r * 34)), (120, 114, 104), 9)
        return pg

    def view(self, pg, z, cx, cy, rot=0.0):
        h, w = pg.shape[:2]
        sc = W / w * z
        M = cv2.getRotationMatrix2D((cx * w, cy * h), rot, sc)
        M[0, 2] += W / 2 - cx * w
        M[1, 2] += H / 2 - cy * h
        return cv2.warpAffine(pg, M, (W, H), borderMode=cv2.BORDER_CONSTANT, borderValue=(40, 36, 32))

    def frame(self, t):
        k, lt, d = beat_of(t)
        if k == 0:
            u = ease_io(lin(lt, 0, d))
            f = self.view(self.page1, lerp(1.0, 1.35, u), 0.5, lerp(0.33, 0.46, u), lerp(-2, -0.5, u))
        elif k == 1:
            f = self.view(self.page2, lerp(1.25, 1.1, ease_io(lin(lt, 0, d))), 0.5, 0.27, 1.5)
            mu = ease_out(lin(lt, 0.3, 0.8))
            V.marker(f, 230, 240, 1180, 470, mu, alpha=0.6)
        elif k == 2:
            f = self.view(self.page3, lerp(1.0, 1.3, ease_io(lin(lt, 0, d))), 0.5, lerp(0.33, 0.45, ease_io(lin(lt, 0, d))),
                          -1.5)
        else:
            f = np.empty((H, W, 3), np.uint8)
            f[:] = self.NEWS
            f = V.cover(V.paper(seed=499, tone=self.NEWS), W, H, 1.0)
            cv2.rectangle(f, (120, 180), (W - 120, 190), self.INK, -1)
            cv2.rectangle(f, (120, 880), (W - 120, 890), self.INK, -1)
            s = lerp(1.3, 1.0, V.ease_in(lin(lt, 0, 0.15)))
            V.place(f, V.text_img("STALIN", "play", 300, self.INK), W / 2, 420, s, 0, lin(lt, 0, 0.1), shadow=False)
            V.place(f, V.text_img("NA SPLÁTKY", "play", 190, (150, 24, 30)), W / 2, 690, s, 0, lin(lt, 0.1, 0.2),
                    shadow=False)
        # page turn between beats: the next page sweeps in over the last 0.35 s
        nxt = None
        for a, b in BEATS[1:]:
            if a - 0.35 < t < a:
                nxt = (a, (t - (a - 0.35)) / 0.35)
        if nxt:
            u = ease_io(nxt[1])
            x = int(W * (1 - u))
            sh = np.clip(np.linspace(0.55, 1, 60), 0, 1)
            if 0 < x < W:
                f[:, max(x - 60, 0):x] = (f[:, max(x - 60, 0):x] * sh[-(x - max(x - 60, 0)):][None, :, None]).astype(
                    np.uint8)
                f[:, x:] = (236, 230, 214)
        return V.finish(f, int(t * FPS), 4.5, 0.35)

    sfx = [(0.05, "paper", 0.8), (4.0, "marker", 0.6), (4.95, "paper_slide", 0.8), (5.6, "marker", 0.6),
           (7.6, "paper_slide", 0.8), (11.4, "paper_slide", 0.8), (11.72, "impact", 0.9)]


STYLES = {s.name: s for s in (Constructivist, Minimal, Dossier, Newspaper)}


def render_video(style):
    os.makedirs(OUT, exist_ok=True)
    st = STYLES[style]()
    raw = os.path.join(OUT, f"{style}_raw.mp4")
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "16",
                           "-pix_fmt", "yuv420p", raw], stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        ff.stdin.write(np.ascontiguousarray(st.frame(i / FPS)).tobytes())
    ff.stdin.close()
    ff.wait()
    wav = os.path.join(OUT, f"{style}.wav")
    mix_audio(st.sfx, wav)
    out = os.path.join(OUT, f"{style}.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-i", wav, "-map", "0:v", "-map", "1:a", "-vf",
                    "scale=1280:720:flags=lanczos", "-c:v", "libx264", "-preset", "slow", "-crf", "21",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)
    print("wrote", out)


def mix_audio(events, path):
    """The film's first narration paragraph (cut before the next sentence), the hook music and effects."""
    import audio
    import layout
    SR = audio.SR
    n = int((DUR + 0.6) * SR)
    L = layout.layout()
    blk = L["voice"][0]
    voice = np.zeros((n, 2), np.float32)
    v = audio.decode(blk["mp3"])
    cut = int((BEATS[3][0] - blk["start"] + 0.05) * SR)
    v = v[:cut].copy()
    v[-int(0.08 * SR):] *= np.linspace(1, 0, int(0.08 * SR))[:, None]
    audio.add(voice, v, blk["start"])
    fx = np.zeros((n, 2), np.float32)
    for t, name, g in events:
        audio.add(fx, audio.sfx(name), t, audio.GAIN.get(name, 0.4) * g)
    music = audio.to_lufs(audio.decode(os.path.join(V.BUILD, "music", "hook.mp3")), -20.0)[:n]
    music = np.pad(music, ((0, n - len(music)), (0, 0)))
    env = audio.envelope(voice.mean(1), 0.02, 0.6)[:n]
    env = np.pad(env, (0, n - len(env)))
    music *= (10 ** (-9 * np.clip(env / 0.03, 0, 1) / 20))[:, None]
    voice = audio.to_lufs(voice, -16)
    fx = np.tanh(audio.to_lufs(fx, -28) / 0.35) * 0.35
    music = audio.to_lufs(music, -29)
    mix = voice + fx + music
    mix *= 10 ** ((-14 - audio.lufs(mix)) / 20)
    peak = np.abs(mix).max()
    if peak > 0.97:
        mix *= 0.97 / peak
    sf.write(path, mix, SR, subtype="PCM_24")


def sheet():
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for name, cls in STYLES.items():
        st = cls()
        row = []
        for a, b in BEATS:
            fr = st.frame(a + (b - a) * 0.75)
            fr = cv2.resize(fr, (480, 270))
            row.append(fr)
        rows.append(np.hstack(row))
        cv2.putText(rows[-1], name, (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 230, 0), 2)
    p = os.path.join(OUT, "sheet.jpg")
    cv2.imwrite(p, cv2.cvtColor(np.vstack(rows), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(p)


if __name__ == "__main__":
    if sys.argv[1] == "sheet":
        sheet()
    else:
        for s in sys.argv[2:] or STYLES:
            render_video(s)
