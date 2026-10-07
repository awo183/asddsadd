"""Five more styles, deliberately unlike the Vox/print family: flat vector
illustration, isometric 3D diorama, blueprint drawing, neon synthwave and comic
book. Same 14 s hook and narration as styles.py, so they compare 1:1.

usage: styles2.py render [style ...] | styles2.py sheet
"""
import math
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import styles as S  # noqa: E402
import vox as V  # noqa: E402
from styles import BEATS, DUR, beat_of, chip, load  # noqa: E402
from vox import FPS, H, W, clamp, ease_back, ease_io, ease_out, ease_out_expo, lerp, lin  # noqa: E402


def vgrad(c0, c1, h=H, w=W):
    u = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    g = np.array(c0, np.float32) * (1 - u) + np.array(c1, np.float32) * u
    return np.repeat(g, w, axis=1).astype(np.uint8)


def mix(a, b, u):
    return cv2.addWeighted(a, 1 - u, b, u, 0)


def poly(f, pts, color, alpha=1.0):
    p = np.round(np.array(pts, np.float32) * 4).astype(np.int32)
    if alpha >= 1:
        cv2.fillPoly(f, [p], color, cv2.LINE_AA, shift=2)
    elif alpha > 0:
        ov = f.copy()
        cv2.fillPoly(ov, [p], color, cv2.LINE_AA, shift=2)
        cv2.addWeighted(ov, alpha, f, 1 - alpha, 0, dst=f)


def statue_mask():
    cut = load("monument_side_cut.png")
    a = cut[..., 3]
    ys, xs = np.nonzero(a > 60)
    return cut[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


# =====================================================================================
# A. FLAT VECTOR ILLUSTRATION
# =====================================================================================
class Flat:
    name = "flat"
    NAVY, CORAL, ORANGE, TEAL, CREAM, YEL = (15, 26, 46), (233, 87, 63), (242, 140, 56), (46, 196, 182), \
        (253, 240, 213), (255, 201, 71)

    def __init__(self):
        cut = statue_mask()
        g = cv2.cvtColor(cut[..., :3], cv2.COLOR_RGB2GRAY)
        g = cv2.bilateralFilter(g, 9, 40, 9)
        q = np.digitize(g, [80, 130, 180])
        pal = np.array([(58, 70, 104), (96, 112, 150), (146, 160, 192), (206, 214, 232)], np.uint8)
        rgb = pal[q]
        a = (cv2.GaussianBlur(cut[..., 3], (0, 0), 1.0) > 120).astype(np.uint8) * 255
        self.statue = np.dstack([rgb, a])
        rng = np.random.default_rng(5)
        self.stars = [(rng.uniform(0, W), rng.uniform(0, H * 0.55), rng.uniform(1, 2.6), rng.uniform(0, 6))
                      for _ in range(160)]
        self.sky_n = vgrad((22, 34, 66), (68, 92, 140))
        self.sky_d = vgrad((120, 190, 226), (214, 238, 246))
        self.city = [(rng.uniform(-50, W), rng.uniform(60, 190), rng.uniform(50, 120)) for _ in range(40)]
        self.sparks = [(rng.uniform(0, 1), rng.uniform(-2.6, -0.4), rng.uniform(300, 700)) for _ in range(40)]
        self.coins = [(rng.uniform(150, W - 150), rng.uniform(0, 1.1), rng.uniform(-30, 30)) for _ in range(26)]

    def hill(self, f, color):
        pts = [(0, 760), (300, 720), (760, 690), (1200, 700), (1500, 760), (1800, 900), (W, 960), (W, H), (0, H)]
        poly(f, pts, color)

    def skyline(self, f, color, win):
        for x, h, w in self.city:
            cv2.rectangle(f, (int(x), int(700 - h)), (int(x + w), 720), color, -1)
            for yy in range(int(700 - h) + 14, 690, 22):
                for xx in range(int(x) + 10, int(x + w) - 10, 18):
                    if (xx * 7 + yy * 3) % 5 == 0:
                        cv2.rectangle(f, (xx, yy), (xx + 6, yy + 9), win, -1)

    def scene(self, t, day=0.0, statue=1.0, zoom=1.0, focus=(960, 520), metronome=0.0):
        f = mix(self.sky_n, self.sky_d, day) if day > 0 else self.sky_n.copy()
        if day < 1:
            for x, y, r, ph in self.stars:
                a = (0.5 + 0.5 * math.sin(t * 2 + ph)) * (1 - day)
                cv2.circle(f, (int(x), int(y)), int(r), (int(255 * a), int(250 * a), int(220 * a)), -1, cv2.LINE_AA)
            cv2.circle(f, (1560, 210), 90, self.CREAM, -1, cv2.LINE_AA)
            cv2.circle(f, (1530, 190), 18, (232, 220, 192), -1, cv2.LINE_AA)
            cv2.circle(f, (1590, 240), 12, (232, 220, 192), -1, cv2.LINE_AA)
        if day > 0:
            cv2.circle(f, (1560, 200), int(110 * day), (255, 214, 120), -1, cv2.LINE_AA)
        self.skyline(f, tuple(int(lerp(a, b, day)) for a, b in zip((34, 50, 86), (150, 178, 196))), (255, 206, 92))
        self.hill(f, tuple(int(lerp(a, b, day)) for a, b in zip((22, 36, 62), (92, 150, 112))))
        poly(f, [(700, 690), (1220, 690), (1160, 600), (760, 600)],
             tuple(int(lerp(a, b, day)) for a, b in zip((52, 66, 98), (196, 186, 170))))
        if statue > 0:
            sc = 330 / self.statue.shape[0]
            V.place(f, self.statue, 960, 604, sc * statue, 0, clamp(statue * 1.5), shadow=False, ay=1.0)
        if metronome > 0:
            u = ease_back(clamp(metronome))
            poly(f, [(900, 600), (1020, 600), (975, 500), (945, 500)], self.NAVY)
            ang = math.radians(18 * math.sin(t * 2.3))
            L = 420 * u
            tip = (960 + L * math.sin(ang), 520 - L * math.cos(ang))
            cv2.line(f, (960, 520), (int(tip[0]), int(tip[1])), self.CORAL, 14, cv2.LINE_AA)
            cv2.circle(f, (960, 520), 14, self.YEL, -1, cv2.LINE_AA)
            for k, x in enumerate((820, 860, 1080, 1120)):
                hh = 34
                col = (self.TEAL, self.ORANGE, self.CORAL, self.YEL)[k]
                cv2.circle(f, (x, 600 - hh - 8), 7, self.NAVY, -1, cv2.LINE_AA)
                cv2.rectangle(f, (x - 7, 600 - hh), (x + 7, 600), col, -1)
        if zoom != 1.0:
            M = np.float32([[zoom, 0, focus[0] * (1 - zoom)], [0, zoom, focus[1] * (1 - zoom)]])
            f = cv2.warpAffine(f, M, (W, H), borderMode=cv2.BORDER_REPLICATE)
        return f

    def pill(self, f, text, x, y, u, bg, fg=(255, 255, 255), size=64, ax=0.5):
        im = V.text_img(text, "mont_black", size, fg)
        h = im.shape[0] + 34
        w = im.shape[1] + 64
        out = np.zeros((h, w, 4), np.uint8)
        cv2.rectangle(out, (h // 2, 0), (w - h // 2, h), tuple(bg) + (255,), -1)
        cv2.circle(out, (h // 2, h // 2), h // 2, tuple(bg) + (255,), -1, cv2.LINE_AA)
        cv2.circle(out, (w - h // 2, h // 2), h // 2, tuple(bg) + (255,), -1, cv2.LINE_AA)
        rgb = out[..., :3].copy()
        V.blit(rgb, im, 32, 17)
        out[..., :3] = rgb
        V.place(f, out, x, y, 0.6 + 0.4 * ease_back(u), 0, clamp(u * 3), shadow=False, ax=ax)

    def frame(self, t):
        k, lt, d = beat_of(t)
        if k == 0:
            f = self.scene(t, zoom=lerp(1.0, 1.15, ease_io(lin(lt, 0, d))), focus=(960, 500))
            cx, cy = 1050, 300
            if lt > 2.5:
                for ph, vx, sp in self.sparks:
                    tt = ((lt * 1.8 + ph) % 1.0)
                    x = cx + vx * 60 * tt * 3
                    y = cy - 140 * tt + 380 * tt * tt
                    cv2.circle(f, (int(x), int(y)), 4, self.YEL, -1, cv2.LINE_AA)
            for k2 in range(5):
                x = 800 + k2 * 80
                cv2.line(f, (x, 300), (x, 610), (200, 160, 110), 3, cv2.LINE_AA)
            for yy in range(320, 610, 60):
                cv2.line(f, (790, yy), (1130, yy), (200, 160, 110), 3, cv2.LINE_AA)
            self.pill(f, "ŘÍJEN 1962", 160, 160, lin(lt, 0.3, 0.7), self.CORAL, ax=0.0)
        elif k == 1:
            f = self.scene(t, zoom=lerp(1.45, 1.55, lin(lt, 0, d)), focus=(960, 520))
            u = ease_out_expo(lin(lt, 0.2, 1.3))
            x, y0, y1 = 1330, 920, 160
            yt = lerp(y0, y1, u)
            cv2.line(f, (x, y0), (x, int(yt)), self.TEAL, 16, cv2.LINE_AA)
            cv2.circle(f, (x, y0), 12, self.TEAL, -1, cv2.LINE_AA)
            cv2.circle(f, (x, int(yt)), 12, self.TEAL, -1, cv2.LINE_AA)
            self.pill(f, f"{15.5 * u:.1f} m".replace(".", ","), x + 40, yt, lin(lt, 0.3, 0.6), self.TEAL, ax=0.0)
            cv2.circle(f, (560, 840), 14, self.CREAM, -1, cv2.LINE_AA)
            cv2.rectangle(f, (548, 856), (572, 920), self.ORANGE, -1)
            self.pill(f, "člověk 1,8 m", 470, 970, lin(lt, 0.9, 1.2), self.NAVY, size=34)
        elif k == 2:
            day = ease_io(lin(lt, 0, 1.0))
            f = self.scene(t, day=day, statue=1 - ease_io(lin(lt, 0.1, 0.6)), metronome=lin(lt, 0.6, 1.2))
            self.pill(f, "LETNÁ, DNES", 160, 160, lin(lt, 0.5, 0.9), self.NAVY, ax=0.0)
            u = lin(lt, 1.4, 1.8)
            if u:
                self.pill(f, "Sraz na Stalinu?", 1210, 430, u, (255, 255, 255), self.NAVY, size=52, ax=0.0)
                poly(f, [(1215, 470), (1250, 470), (1130, 560)], (255, 255, 255), clamp(u * 3))
        else:
            f = vgrad(self.CORAL, self.ORANGE)
            for x, ph, rot in self.coins:
                tt = lt - ph
                if tt < 0:
                    continue
                y = min(-80 + 1400 * tt * tt, 980 - (x % 7) * 12)
                cv2.ellipse(f, (int(x), int(y)), (46, 46), rot, 0, 360, self.YEL, -1, cv2.LINE_AA)
                cv2.ellipse(f, (int(x), int(y)), (46, 46), rot, 0, 360, (214, 150, 30), 6, cv2.LINE_AA)
                im = V.text_img("Kčs", "mont_black", 26, (180, 110, 20))
                V.place(f, im, x, y, 1.0, rot, 1.0, shadow=False)
            s1 = V.text_img("STALIN", "mont_black", 250, (255, 255, 255))
            s2 = V.text_img("NA SPLÁTKY", "mont_black", 140, self.NAVY)
            V.place(f, s1, W / 2, 400, 0.6 + 0.4 * ease_back(lin(lt, 0, 0.35)), 0, lin(lt, 0, 0.15), shadow=False)
            V.place(f, s2, W / 2, 620, 0.6 + 0.4 * ease_back(lin(lt, 0.15, 0.5)), 0, lin(lt, 0.15, 0.3),
                    shadow=False)
        return f

    sfx = [(0.3, "pop", 0.7), (2.6, "jackhammer", 0.5), (5.4, "whoosh", 0.5), (5.6, "pop", 0.7), (6.4, "pop", 0.5),
           (8.0, "whoosh_big", 0.5), (8.6, "pop", 0.6), (9.4, "pop", 0.6), (11.72, "hit", 0.8), (12.2, "cash", 0.8)]


# =====================================================================================
# B. ISOMETRIC 3D DIORAMA (a small flat-shaded software renderer)
# =====================================================================================
def box(x0, x1, y0, y1, z0, z1, color, tag=None):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1),
         (x0, y1, z1)]
    faces = [((4, 5, 6, 7), (0, 0, 1)), ((0, 1, 5, 4), (0, -1, 0)), ((1, 2, 6, 5), (1, 0, 0)),
             ((2, 3, 7, 6), (0, 1, 0)), ((3, 0, 4, 7), (-1, 0, 0))]
    return [([v[i] for i in idx], n, color, tag) for idx, n in faces]


class Iso:
    name = "iso"
    BG0, BG1 = (243, 233, 220), (226, 208, 188)
    LIGHT = np.array([-0.45, -0.6, 0.66])

    def __init__(self):
        self.bg = vgrad(self.BG0, self.BG1)
        F = []
        F += box(-46, 46, -34, 14, -8, 0, (163, 177, 138))
        for k in range(4):
            F += box(-30 + k * 2, 30 - k * 2, 14 + k * 5, 19 + k * 5, -8 - k * 3, -5 - k * 3, (186, 178, 160))
        F += box(-46, 46, 34, 52, -22, -18, (127, 183, 190))
        F += box(-14, 14, -7, 7, 0, 3, (217, 197, 178))
        F += box(-12, 12, -6, 6, 3, 6, (208, 188, 168))
        F += box(-10, 10, -4.5, 4.5, 6, 9, (200, 180, 160))
        self.base = F
        S_ = []
        S_ += box(-1.2, 1.2, 2.4, 3.8, 9, 24.5, (150, 160, 178), "statue")
        for k, yy in enumerate((1.0, -0.8, -2.6, -4.4)):
            S_ += box(-3.2, -1.0, yy - 1.4, yy, 9, 22 - k * 0.6, (140 + k * 4, 150 + k * 4, 168 + k * 4), "statue")
            S_ += box(1.0, 3.2, yy - 1.4, yy, 9, 22.4 - k * 0.6, (146 + k * 4, 156 + k * 4, 174 + k * 4), "statue")
        S_ += box(-3.6, 3.6, -6.6, -5.8, 9, 23, (132, 142, 160), "statue")
        self.statue = S_
        rng = np.random.default_rng(8)
        self.trees = []
        for _ in range(16):
            x, y = rng.uniform(-42, 42), rng.uniform(-32, -10)
            if abs(x) < 16:
                continue
            self.trees += box(x - 1.4, x + 1.4, y - 1.4, y + 1.4, 0, 5 + rng.uniform(0, 3), (110, 150, 104))
        self.people = []
        for x, y, c in ((-8, 9, (233, 87, 63)), (6, 10, (46, 120, 182)), (12, -9, (242, 160, 56)),
                        (-16, -12, (90, 90, 110)), (9, 6.5, (200, 60, 90))):
            self.people += box(x - 0.4, x + 0.4, y - 0.4, y + 0.4, 0, 1.9, c)

    def project(self, p, yaw, scale, cx, cy, pitch=math.radians(32)):
        x, y, z = p
        c, s = math.cos(yaw), math.sin(yaw)
        xr, yr = x * c - y * s, x * s + y * c
        sx = cx + xr * scale
        sy = cy + (yr * math.sin(pitch) - z * math.cos(pitch)) * scale
        depth = yr * math.cos(pitch) + z * math.sin(pitch)
        return sx, sy, depth

    def render(self, faces, yaw, scale, cx, cy, f, extra=()):
        items = []
        for verts, n, color, tag in list(faces) + list(extra):
            P = [self.project(v, yaw, scale, cx, cy) for v in verts]
            pts = np.array([(p[0], p[1]) for p in P])
            e1, e2 = pts[1] - pts[0], pts[2] - pts[0]
            area = e1[0] * e2[1] - e1[1] * e2[0]
            if area <= 0:          # back-facing
                continue
            shade = 0.62 + 0.38 * max(0.0, float(np.dot(n, self.LIGHT)))
            col = tuple(int(min(255, c * shade)) for c in color)
            items.append((np.mean([p[2] for p in P]), pts, col))
        items.sort(key=lambda it: it[0])         # far faces first
        for _, pts, col in items:
            cv2.fillPoly(f, [np.round(pts * 4).astype(np.int32)], col, cv2.LINE_AA, shift=2)
            cv2.polylines(f, [np.round(pts * 4).astype(np.int32)], True, tuple(int(c * 0.82) for c in col), 1,
                          cv2.LINE_AA, shift=2)

    def scaffold(self, f, yaw, scale, cx, cy, u):
        col = (150, 110, 70)
        for z in np.arange(9, 25.5, 2.5):
            ring = [(-4.2, -7, z), (4.2, -7, z), (4.2, 4.6, z), (-4.2, 4.6, z), (-4.2, -7, z)]
            P = [self.project(p, yaw, scale, cx, cy)[:2] for p in ring]
            cv2.polylines(f, [np.round(np.array(P) * 4).astype(np.int32)], False, col, 2, cv2.LINE_AA, shift=2)
        for x, y in ((-4.2, -7), (4.2, -7), (4.2, 4.6), (-4.2, 4.6), (0, 4.6), (0, -7), (4.2, -1.2), (-4.2, -1.2)):
            a = self.project((x, y, 9), yaw, scale, cx, cy)
            b = self.project((x, y, 9 + 16.5 * u), yaw, scale, cx, cy)
            cv2.line(f, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), col, 2, cv2.LINE_AA)

    def metronome(self, t, u):
        if u <= 0:
            return []
        h = 7 * u
        F = box(-2.2, 2.2, -1.2, 1.2, 9, 9 + h * 0.4, (44, 44, 54))
        F += box(-0.6, 0.6, -0.5, 0.5, 9, 9 + h, (44, 44, 54))
        ang = math.radians(20 * math.sin(t * 2.2))
        L = 23 * u
        px, pz = 0.0, 9 + h * 0.8
        tx, tz = px + L * math.sin(ang), pz + L * math.cos(ang)
        nx = (math.cos(ang) * 0.35, 0, -math.sin(ang) * 0.35)
        quad = [(px - nx[0], 1.0, pz - nx[2]), (px + nx[0], 1.0, pz + nx[2]), (tx + nx[0], 1.0, tz + nx[2]),
                (tx - nx[0], 1.0, tz - nx[2])]
        F.append((quad, (0, 1, 0), (230, 57, 70), None))
        F.append((quad[::-1], (0, -1, 0), (230, 57, 70), None))
        return F

    def frame(self, t):
        k, lt, d = beat_of(t)
        f = self.bg.copy()
        yaw = math.radians(lerp(-38, -18, t / DUR))
        scale, cx, cy = 13.5, W / 2, 640
        if k == 1:
            z = ease_io(lin(lt, 0, 0.6))
            scale, cy = lerp(13.5, 24, z), lerp(640, 840, z)
        cv2.ellipse(f, (int(cx), int(cy + 60)), (int(scale * 60), int(scale * 18)), 0, 0, 360, (210, 192, 172), -1,
                    cv2.LINE_AA)
        statue_u = 1.0
        met_u = 0.0
        if k == 2:
            statue_u = 1 - ease_io(lin(lt, 0.0, 0.6))
            met_u = ease_back(lin(lt, 0.6, 1.3))
        if k == 3:
            statue_u, met_u = 0.0, 1.0
            yaw = math.radians(lerp(-18, 40, ease_io(lin(lt, 0, d))))
            scale, cy = 9.0, 760
        faces = self.base + self.trees + (self.people if k >= 2 else [])
        st = []
        if statue_u > 0:
            for verts, n, col, tag in self.statue:
                st.append(([(x, y, 9 + (z - 9) * statue_u) for x, y, z in verts], n, col, tag))
        self.render(faces, yaw, scale, cx, cy, f, st + self.metronome(t, met_u))
        if k == 0:
            self.scaffold(f, yaw, scale, cx, cy, ease_out(lin(lt, 0.2, 1.4)))
            if lt > 2.6:
                hx, hy, _ = self.project((0, 3, 24), yaw, scale, cx, cy)
                rng = np.random.default_rng(int(t * FPS))
                for _ in range(10):
                    cv2.circle(f, (int(hx + rng.normal(0, 26)), int(hy + rng.normal(0, 18))), 3, (90, 84, 76), -1,
                               cv2.LINE_AA)
            Flat.pill(Flat, f, "ŘÍJEN 1962", 140, 140, lin(lt, 0.3, 0.7), (60, 66, 90), ax=0.0)
        elif k == 1:
            u = ease_out_expo(lin(lt, 0.5, 1.5))
            a = self.project((5.5, 3.8, 9), yaw, scale, cx, cy)
            b = self.project((5.5, 3.8, 9 + 15.5 * u), yaw, scale, cx, cy)
            cv2.line(f, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), (230, 57, 70), 6, cv2.LINE_AA)
            for p in (a, b):
                cv2.line(f, (int(p[0] - 20), int(p[1])), (int(p[0] + 20), int(p[1])), (230, 57, 70), 6, cv2.LINE_AA)
            Flat.pill(Flat, f, f"{15.5 * u:.1f} m".replace(".", ","), b[0] + 40, b[1], lin(lt, 0.6, 0.9),
                      (230, 57, 70), ax=0.0)
        elif k == 2:
            Flat.pill(Flat, f, "LETNÁ, DNES", 140, 140, lin(lt, 0.4, 0.8), (60, 66, 90), ax=0.0)
            Flat.pill(Flat, f, "„sraz na Stalinu“", W - 140, 140, lin(lt, 1.4, 1.8), (255, 255, 255), (60, 66, 90),
                      size=50, ax=1.0)
        else:
            s1 = V.text_img("STALIN NA SPLÁTKY", "mont_black", 130, (52, 58, 84))
            V.place(f, s1, W / 2, 170, 0.6 + 0.4 * ease_back(lin(lt, 0, 0.4)), 0, lin(lt, 0, 0.2), shadow=False)
        return V.finish(f, int(t * FPS), 2.0, 0.15)

    sfx = [(0.3, "pop", 0.6), (0.6, "hammer_wood", 0.6), (2.7, "jackhammer", 0.5), (5.3, "whoosh", 0.6),
           (5.9, "pen", 0.5), (7.9, "whoosh", 0.5), (8.5, "pop", 0.7), (9.2, "metronome", 0.4),
           (11.72, "whoosh_big", 0.6), (11.9, "hit", 0.7)]


# =====================================================================================
# C. BLUEPRINT / TECHNICAL DRAWING
# =====================================================================================
class Blueprint:
    name = "blueprint"
    BG = (16, 62, 112)
    LINE = (232, 242, 252)

    def __init__(self):
        g = np.empty((H, W, 3), np.uint8)
        g[:] = self.BG
        for x in range(0, W, 30):
            cv2.line(g, (x, 0), (x, H), (34, 84, 136) if x % 150 else (58, 108, 162), 1)
        for y in range(0, H, 30):
            cv2.line(g, (0, y), (W, y), (34, 84, 136) if y % 150 else (58, 108, 162), 1)
        self.grid = g
        rng = np.random.default_rng(3)

        def lines(img, w, h, zoom=1.0, cx=0.5, cy=0.5, lo=40, hi=110, mask=None):
            v = V.cover(img[..., :3], w, h, zoom, cx, cy)
            gray = cv2.bilateralFilter(cv2.cvtColor(v, cv2.COLOR_RGB2GRAY), 9, 50, 9)
            e = cv2.Canny(gray, lo, hi)
            if mask is not None:
                e[cv2.resize(mask, (w, h)) < 100] = 0
            e = cv2.dilate(e, np.ones((2, 2), np.uint8))
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            order = (xx / w * 0.75 + yy / h * 0.25) + rng.random((h, w)).astype(np.float32) * 0.08
            return e, order

        self.l1 = lines(load("demolition_closeup.jpg"), 1300, 820, 1.0, 0.5, 0.42, 25, 80)
        cut = statue_mask()
        self.cut_h, self.cut_w = 700, int(700 * cut.shape[1] / cut.shape[0])
        self.l2 = lines(cut, self.cut_w, self.cut_h, 1.0, 0.5, 0.5, 40, 120,
                        cut[..., 3])
        import maps
        raw, mx0, my0 = maps.mosaic(14.4172, 50.0944, 15, 12, 8)
        tx, ty = maps.tile_xy(14.4172, 50.0944, 15)
        px, py = (tx - mx0) * 256, (ty - my0) * 256
        crop = raw[int(py - 600):int(py + 600), int(px - 1000):int(px + 1000)]
        crop = cv2.resize(crop, (1700, 1020))
        f3 = crop.astype(np.float32)
        lum = f3.mean(2)
        water = ((f3[..., 2] - f3[..., 1] > 3) & (lum < 226)).astype(np.uint8) * 255
        water = cv2.morphologyEx(water, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        roads = (lum > 246).astype(np.uint8) * 255
        roads = cv2.morphologyEx(roads, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        e = cv2.Canny(roads, 50, 150) // 2 + cv2.dilate(cv2.Canny(water, 50, 150), np.ones((3, 3), np.uint8))
        yy, xx = np.mgrid[0:1020, 0:1700].astype(np.float32)
        self.l3 = (e, np.sqrt((xx - 850) ** 2 + (yy - 510) ** 2) / 1000 + rng.random((1020, 1700)).astype(np.float32) * 0.05)

    def reveal(self, f, ln, x, y, u):
        e, order = ln
        m = ((e > 0) & (order < u * 1.08)).astype(np.float32)
        h, w = e.shape
        roi = f[y:y + h, x:x + w].astype(np.float32)
        a = m[..., None] * 0.95
        f[y:y + h, x:x + w] = (roi * (1 - a) + np.array(self.LINE, np.float32) * a).astype(np.uint8)

    def text(self, f, s, x, y, size=34, a=1.0, ax=0.0, rot=0.0, font="cp_bold"):
        im = V.text_img(s, font, size, self.LINE, tracking=3)
        V.place(f, im, x, y, 1.0, rot, a, shadow=False, ax=ax, ay=0.5)

    def title_block(self, f, rows, u):
        x0, y0, w, h = W - 640, H - 250, 580, 200
        if u <= 0:
            return
        cv2.rectangle(f, (x0, y0), (x0 + int(w * u), y0 + h), self.LINE, 2, cv2.LINE_AA)
        for k, (a, b) in enumerate(rows):
            yy = y0 + 18 + k * 46
            if u > 0.3 + k * 0.15:
                cv2.line(f, (x0, yy + 30), (x0 + w, yy + 30), self.LINE, 1, cv2.LINE_AA)
                self.text(f, a, x0 + 16, yy + 12, 22)
                self.text(f, b, x0 + 230, yy + 12, 26)

    def dim(self, f, x, y0, y1, u, label):
        yt = lerp(y0, y1, u)
        cv2.line(f, (x, int(y0)), (x, int(yt)), self.LINE, 2, cv2.LINE_AA)
        for yy in (y0, yt):
            cv2.line(f, (x - 40, int(yy)), (x + 16, int(yy)), self.LINE, 1, cv2.LINE_AA)
        for yy, dirn in ((y0, -1), (yt, 1)):
            pts = np.array([(x, yy), (x - 9, yy - dirn * 24), (x + 9, yy - dirn * 24)], np.int32)
            cv2.fillPoly(f, [pts], self.LINE, cv2.LINE_AA)
        if u > 0.2:
            self.text(f, label, x + 30, (y0 + yt) / 2, 40, clamp((u - 0.2) * 3), 0.5, 90)

    def frame(self, t):
        k, lt, d = beat_of(t)
        f = self.grid.copy()
        if k == 0:
            self.reveal(f, self.l1, 120, 110, ease_io(lin(lt, 0, 3.0)))
            self.title_block(f, [("OBJEKT", "STALINŮV POMNÍK"), ("MÍSTO", "LETNÁ, PRAHA"), ("DATUM", "10 / 1962"),
                                 ("LIST", "1 / 4")], lin(lt, 1.0, 2.2))
            hu = lin(lt, 3.9, 4.6)
            if hu:
                V.draw_path(f, V.circle_pts(1050, 330, 150, 130, 3), V.sine_io(hu), (255, 210, 90), 4)
                self.text(f, "DET. A — HLAVA", 1220, 210, 30, hu)
        elif k == 1:
            x0, y0 = 520, 230
            self.reveal(f, self.l2, x0, y0, ease_io(lin(lt, 0, 1.4)))
            u = ease_out_expo(lin(lt, 0.6, 1.8))
            self.dim(f, x0 + self.cut_w + 90, y0 + self.cut_h, y0, u, "15 500 mm")
            self.text(f, "POHLED BOČNÍ · M 1:100", x0, y0 + self.cut_h + 60, 30, lin(lt, 0.5, 0.9))
        elif k == 2:
            self.reveal(f, self.l3, 110, 30, ease_io(lin(lt, 0, 1.6)))
            cx, cy = 110 + 850, 30 + 510
            u = lin(lt, 1.0, 1.6)
            if u:
                V.draw_path(f, V.circle_pts(cx, cy, 70, 70, 9), V.sine_io(u), (255, 210, 90), 4)
                cv2.line(f, (cx + 50, cy - 50), (cx + 200, cy - 200), self.LINE, 2, cv2.LINE_AA)
                self.text(f, "METRONOM (1991)", cx + 215, cy - 220, 34, u)
                self.text(f, "„sraz na Stalinu“", cx + 215, cy - 170, 30, lin(lt, 1.8, 2.2), font="type")
            cv2.circle(f, (W - 150, 150), 60, self.LINE, 2, cv2.LINE_AA)
            cv2.line(f, (W - 150, 80), (W - 150, 220), self.LINE, 2, cv2.LINE_AA)
            self.text(f, "S", W - 150, 60, 34, 1.0, 0.5)
        else:
            u = ease_out(lin(lt, 0, 0.8))
            cv2.rectangle(f, (200, 260), (200 + int((W - 400) * u), H - 260), self.LINE, 3, cv2.LINE_AA)
            cv2.rectangle(f, (220, 280), (220 + int((W - 440) * u), H - 280), self.LINE, 1, cv2.LINE_AA)
            n = int(max(lt - 0.3, 0) * 26)
            s = "STALIN NA SPLÁTKY"
            self.text(f, s[:n] or " ", W / 2 - V.text_w(s, "cp_bold", 120, 3) / 2, H / 2 - 30, 120)
            self.text(f, "VÝKRES Č. 1 · MĚŘÍTKO 1:100 · LETNÁ", W / 2, H / 2 + 90, 30, lin(lt, 1.2, 1.6), 0.5)
        return V.finish(f, int(t * FPS), 3.0, 0.3)

    sfx = [(0.1, "pen", 0.6), (1.4, "pen", 0.5), (3.9, "marker", 0.6), (5.3, "pen", 0.6), (6.0, "tick", 0.6),
           (7.9, "paper_slide", 0.6), (8.9, "marker", 0.5), (11.72, "typewriter", 0.6), (12.6, "stamp", 0.7)]


# =====================================================================================
# D. NEON SYNTHWAVE
# =====================================================================================
class Neon:
    name = "neon"
    PINK, CYAN, RED, PURPLE = (255, 60, 170), (60, 230, 255), (255, 50, 70), (150, 70, 255)

    def __init__(self):
        self.sky = vgrad((10, 4, 26), (52, 10, 70))
        cut = statue_mask()
        a = cut[..., 3]
        sc = 560 / a.shape[0]
        a = cv2.resize(a, (int(a.shape[1] * sc), 560))
        cnts, _ = cv2.findContours((a > 100).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(cnts, key=cv2.contourArea)[:, 0, :].astype(np.float32)
        c = cv2.approxPolyDP(c, 2.0, True)[:, 0, :].astype(np.float32)
        self.outline = c - c.min(0)
        self.osize = self.outline.max(0)
        rng = np.random.default_rng(12)
        self.city = [(rng.uniform(-60, W), rng.uniform(40, 170), rng.uniform(40, 110)) for _ in range(46)]

    def base(self, t):
        f = self.sky.copy()
        hy = int(H * 0.64)
        cx, cy, r = W // 2, hy - 30, 300
        sun = np.zeros_like(f)
        for y in range(cy - r, cy + 1):
            w = int(math.sqrt(max(r * r - (y - cy) ** 2, 0)))
            band = (y - (cy - r)) / r
            if (y // 14) % 2 == 0 or band < 0.45:
                col = (255, int(lerp(220, 60, band)), int(lerp(90, 160, band)))
                cv2.line(sun, (cx - w, y), (cx + w, y), col, 1)
        f = cv2.add(f, (sun * 0.85).astype(np.uint8))
        for x, h, w in self.city:
            cv2.rectangle(f, (int(x), hy - int(h)), (int(x + w), hy), (8, 2, 18), -1)
        f[hy:] = (12, 2, 24)
        lay = np.zeros_like(f)
        off = (t * 120) % 60
        for k in range(0, 40):
            y = hy + (k * 60 + off) ** 1.25 / 25
            if y > H:
                break
            cv2.line(lay, (0, int(y)), (W, int(y)), self.PINK, 2, cv2.LINE_AA)
        for k in range(-20, 21):
            cv2.line(lay, (W // 2 + k * 24, hy), (W // 2 + k * 260, H), self.PINK, 2, cv2.LINE_AA)
        return f, lay

    def glow(self, f, lay):
        small = cv2.resize(lay, (W // 2, H // 2))
        g1 = cv2.resize(cv2.GaussianBlur(small, (0, 0), 10), (W, H))
        g2 = cv2.GaussianBlur(lay, (0, 0), 2.5)
        core = cv2.addWeighted(lay, 0.6, np.full_like(lay, 255), 0.0, 0)
        out = cv2.add(f, cv2.addWeighted(g1, 1.6, g2, 0.9, 0))
        return cv2.add(out, (core * 0.55).astype(np.uint8))

    def neon_text(self, lay, s, x, y, size, color, u=1.0, font="monoton", flick=1.0):
        if u <= 0:
            return
        im = V.text_img(s, font, size, (255, 255, 255))
        a = im[..., 3]
        edge = cv2.morphologyEx(a, cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8)) if font != "monoton" else a
        h, w = a.shape
        x0, y0 = int(x - w / 2), int(y - h / 2)
        x1, y1 = max(x0, 0), max(y0, 0)
        x2, y2 = min(x0 + w, W), min(y0 + h, H)
        if x2 <= x1 or y2 <= y1:
            return
        e = edge[y1 - y0:y2 - y0, x1 - x0:x2 - x0].astype(np.float32)[..., None] / 255 * u * flick
        roi = lay[y1:y2, x1:x2].astype(np.float32)
        lay[y1:y2, x1:x2] = np.clip(roi + e * np.array(color, np.float32), 0, 255).astype(np.uint8)

    def flicker(self, t, t0):
        if t < t0:
            return 0.0
        dt = t - t0
        if dt > 0.6:
            return 0.92 + 0.08 * math.sin(t * 50)
        return 1.0 if (int(dt * 30) * 7) % 5 not in (1, 3) else 0.15

    def frame(self, t):
        k, lt, d = beat_of(t)
        f, lay = self.base(t)
        if k in (0, 1):
            sc = 1.0 if k == 0 else 1.15
            ox, oy = W / 2 - self.osize[0] * sc / 2, H * 0.64 - 40 - self.osize[1] * sc
            pts = self.outline * sc + (ox, oy)
            u = ease_io(lin(lt, 0, 2.2)) if k == 0 else 1.0
            n = max(int(len(pts) * u), 2)
            cv2.polylines(lay, [np.round(pts[:n] * 4).astype(np.int32)], k == 1, self.RED, 4, cv2.LINE_AA, shift=2)
            if k == 0:
                self.neon_text(lay, "1962", 300, 220, 150, self.PINK, lin(lt, 0.3, 0.5), flick=self.flicker(lt, 0.3))
                self.neon_text(lay, "ŘÍJEN", 300, 360, 70, self.CYAN, lin(lt, 0.8, 1.0), font="oswald",
                               flick=self.flicker(lt, 0.8))
                if lt > 2.6:
                    rng = np.random.default_rng(int(t * FPS))
                    hx, hy = pts[:, 0].min() + 120, pts[:, 1].min() + 40
                    for _ in range(14):
                        a = rng.uniform(0, 2 * math.pi)
                        r = rng.uniform(10, 70)
                        cv2.line(lay, (int(hx), int(hy)), (int(hx + r * math.cos(a)), int(hy + r * math.sin(a))),
                                 (255, 220, 120), 2, cv2.LINE_AA)
            else:
                u = ease_out_expo(lin(lt, 0.2, 1.4))
                x, y0, y1 = int(ox + self.osize[0] * sc + 80), H * 0.64 - 40, oy
                yt = lerp(y0, y1, u)
                cv2.line(lay, (x, int(y0)), (x, int(yt)), self.CYAN, 4, cv2.LINE_AA)
                for j in range(0, 11):
                    yj = lerp(y0, y1, j / 10)
                    if (yj - yt) * (y1 - y0) > 0:
                        break
                    cv2.line(lay, (x, int(yj)), (x + (30 if j % 5 == 0 else 15), int(yj)), self.CYAN, 3, cv2.LINE_AA)
                self.neon_text(lay, f"{15.5 * u:.1f} m".replace(".", ","), x + 230, (y0 + yt) / 2, 110, self.CYAN,
                               1.0, font="oswald")
        elif k == 2:
            u = ease_back(lin(lt, 0.2, 0.9))
            bx, by = W / 2, H * 0.64 - 20
            pts = np.array([(bx - 120 * u, by), (bx + 120 * u, by), (bx + 20, by - 160 * u), (bx - 20, by - 160 * u)])
            cv2.polylines(lay, [pts.astype(np.int32)], True, self.CYAN, 4, cv2.LINE_AA)
            ang = math.radians(22 * math.sin(t * 2.3))
            L = 480 * u
            piv = (bx, by - 130 * u)
            tip = (piv[0] + L * math.sin(ang), piv[1] - L * math.cos(ang))
            cv2.line(lay, (int(piv[0]), int(piv[1])), (int(tip[0]), int(tip[1])), self.RED, 6, cv2.LINE_AA)
            fl = self.flicker(lt, 1.2)
            self.neon_text(lay, "SRAZ NA", 360, 300, 80, self.PINK, lin(lt, 1.2, 1.3), font="oswald", flick=fl)
            self.neon_text(lay, "STALINU", 360, 420, 110, self.PINK, lin(lt, 1.2, 1.3), font="oswald", flick=fl)
            self.neon_text(lay, "LETNÁ · DNES", W - 330, 300, 56, self.CYAN, lin(lt, 0.6, 0.7), font="oswald",
                           flick=self.flicker(lt, 0.6))
        else:
            fl1, fl2 = self.flicker(lt, 0.0), self.flicker(lt, 0.45)
            self.neon_text(lay, "STALIN", W / 2, 360, 230, self.RED, 1.0, flick=fl1)
            self.neon_text(lay, "NA SPLÁTKY", W / 2, 560, 110, self.CYAN, 1.0, font="oswald", flick=fl2)
            refl = cv2.flip(lay[160:H * 64 // 100], 0)
            hy = int(H * 0.64)
            hh = min(refl.shape[0], H - hy)
            lay[hy:hy + hh] = cv2.add(lay[hy:hy + hh], (refl[:hh] * 0.25).astype(np.uint8))
        f = self.glow(f, lay)
        return V.finish(f, int(t * FPS), 3.0, 0.4)

    sfx = [(0.3, "glitch", 0.6), (0.8, "glitch", 0.5), (2.7, "jackhammer", 0.4), (5.3, "sub", 0.5), (5.6, "riser", 0.4),
           (8.0, "whoosh", 0.5), (9.1, "glitch", 0.6), (11.72, "glitch", 0.8), (11.75, "boom", 0.7), (12.2, "glitch", 0.5)]


# =====================================================================================
# E. COMIC BOOK / GRAPHIC NOVEL
# =====================================================================================
def cel(img, w, h, zoom=1.0, cx=0.5, cy=0.5, color=False, levels=4):
    v = V.cover(img[..., :3], w, h, zoom, cx, cy)
    for _ in range(3):
        v = cv2.bilateralFilter(v, 9, 60, 9)
    gray = cv2.cvtColor(v, cv2.COLOR_RGB2GRAY)
    edges = cv2.adaptiveThreshold(cv2.medianBlur(gray, 7), 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 6)
    if color:
        q = (v // 56) * 56 + 28
        out = cv2.convertScaleAbs(q, alpha=1.1)
    else:
        g = cv2.createCLAHE(2.0, (6, 6)).apply(gray)
        bins = np.linspace(0, 255, levels + 1)[1:-1]
        idx = np.digitize(g, bins)
        tones = np.linspace(40, 245, levels).astype(np.uint8)
        out = cv2.cvtColor(tones[idx], cv2.COLOR_GRAY2RGB)
        yy, xx = np.mgrid[0:h, 0:w]
        dots = ((xx % 8 - 4) ** 2 + (yy % 8 - 4) ** 2) < 6
        mid = (idx == 1) & dots
        out[mid] = (25, 25, 25)
    out[edges == 0] = (14, 12, 12)
    return out


class Comic:
    name = "comic"
    INK, YEL, RED, PAGE = (14, 12, 12), (255, 222, 60), (226, 36, 40), (246, 242, 230)

    def __init__(self):
        self.p1 = cel(load("demolition_scaffold.jpg"), 1840, 600, 1.7, 0.42, 0.2)
        self.p2 = cel(load("construction_1953.jpg"), 900, 400, 1.0, 0.5, 0.45)
        self.p3 = cel(load("monument_side.jpg"), 900, 400, 1.6, 0.3, 0.2)
        self.p4 = cel(load("monument_low_sepia.jpg"), 1000, 980, 1.0, 0.45, 0.35)
        self.p5 = cel(load("metronome_today.jpg"), 1840, 1000, 1.0, 0.5, 0.5, color=True)

    def panel(self, f, img, x, y, u, rot=0.0):
        if u <= 0:
            return
        h, w = img.shape[:2]
        out = np.zeros((h + 20, w + 20, 4), np.uint8)
        out[..., :3], out[..., 3] = self.INK, 255
        out[10:10 + h, 10:10 + w, :3] = img
        V.place(f, out, x + (1 - ease_out(u)) * 220, y, 1.0, rot, clamp(u * 3), shadow=False, ax=0.0, ay=0.0)

    def caption(self, f, s, x, y, u, size=58, rot=-1.5):
        if u <= 0:
            return
        im = V.text_img(s, "bangers", size, self.INK, tracking=2)
        c = chip(im, self.YEL, 22, 10)
        cv2.rectangle(c, (0, 0), (c.shape[1] - 1, c.shape[0] - 1), self.INK + (255,), 5)
        V.place(f, c, x, y, 0.8 + 0.2 * ease_back(u), rot, clamp(u * 3), shadow=False, ax=0.0, ay=0.0)

    def sfx_word(self, f, s, x, y, size, u, rot=-8, color=None, shake=True):
        if u <= 0:
            return
        im = V.text_img(s, "bangers", size, color or self.YEL, tracking=4, stroke=10, stroke_color=self.INK)
        dx = dy = 0.0
        if shake:
            rng = np.random.default_rng(int(u * 100))
            dx, dy = rng.uniform(-8, 8), rng.uniform(-8, 8)
        V.place(f, im, x + dx, y + dy, 0.5 + 0.5 * ease_back(u), rot, clamp(u * 4), shadow=False)

    def burst(self, f, x, y, rx, ry, u, color):
        if u <= 0:
            return
        pts = []
        for k in range(28):
            a = k / 28 * 2 * math.pi
            r = 1.0 if k % 2 == 0 else 0.72
            pts.append((x + rx * r * u * math.cos(a), y + ry * r * u * math.sin(a)))
        p = np.array(pts, np.int32)
        cv2.fillPoly(f, [p], color, cv2.LINE_AA)
        cv2.polylines(f, [p], True, self.INK, 7, cv2.LINE_AA)

    def balloon(self, f, s, x, y, u, tail):
        if u <= 0:
            return
        im = V.text_img(s, "bangers", 64, self.INK, tracking=2)
        w, h = im.shape[1] + 90, im.shape[0] + 70
        cv2.ellipse(f, (int(x), int(y)), (int(w / 2 * u), int(h / 2 * u)), 0, 0, 360, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.ellipse(f, (int(x), int(y)), (int(w / 2 * u), int(h / 2 * u)), 0, 0, 360, self.INK, 6, cv2.LINE_AA)
        tri = np.array([(x - 40, y + h / 2 * u - 10), (x + 10, y + h / 2 * u - 10), tail], np.int32)
        cv2.fillPoly(f, [tri], (255, 255, 255), cv2.LINE_AA)
        cv2.polylines(f, [tri], False, self.INK, 6, cv2.LINE_AA)
        if u > 0.7:
            V.place(f, im, x, y, 1.0, 0, 1.0, shadow=False)

    def frame(self, t):
        k, lt, d = beat_of(t)
        f = np.empty((H, W, 3), np.uint8)
        f[:] = self.PAGE
        if k == 0:
            self.panel(f, self.p1, 30, 24, lin(lt, 0, 0.35))
            self.panel(f, self.p2, 30, 650, lin(lt, 2.3, 2.6), 0)
            self.panel(f, self.p3, 960, 650, lin(lt, 3.6, 3.9), 0)
            self.caption(f, "PRAHA, ŘÍJEN 1962", 60, 50, lin(lt, 0.4, 0.7))
            self.sfx_word(f, "RATATATA!", 520, 850, 150, lin(lt, 2.6, 2.8), -10)
            if lt > 3.9:
                self.sfx_word(f, "KRACH!", 1500, 760, 120, lin(lt, 3.9, 4.1), 8, self.RED)
        elif k == 1:
            for j in range(40):
                a = j / 40 * 2 * math.pi
                cv2.line(f, (W // 2, H // 2), (int(W / 2 + 1400 * math.cos(a)), int(H / 2 + 1400 * math.sin(a))),
                         (226, 220, 204), 10)
            self.panel(f, self.p4, 120, 40, lin(lt, 0, 0.3))
            u = ease_out_expo(lin(lt, 0.3, 1.3))
            x, y0, y1 = 1100, 990, 90
            yt = lerp(y0, y1, u)
            cv2.line(f, (x, y0), (x, int(yt)), self.INK, 10, cv2.LINE_AA)
            self.burst(f, 1500, 470, 330, 230, ease_back(lin(lt, 0.8, 1.1)), self.YEL)
            if lt > 1.0:
                self.sfx_word(f, f"{15.5 * u:.1f} METRU!".replace(".", ","), 1500, 470, 96, 1.0, -6, self.RED,
                              shake=False)
        elif k == 2:
            self.panel(f, self.p5, 30, 24, lin(lt, 0, 0.35))
            self.caption(f, "LETNÁ, DNES", 60, 50, lin(lt, 0.3, 0.6))
            self.balloon(f, "SRAZ NA STALINU?", 1360, 300, ease_back(lin(lt, 1.3, 1.6)), (1240, 560))
        else:
            f[:] = self.RED
            for j in range(48):
                a = j / 48 * 2 * math.pi + lt * 0.3
                b = a + 0.06
                pts = np.array([(W / 2, H / 2), (W / 2 + 1500 * math.cos(a), H / 2 + 1500 * math.sin(a)),
                                (W / 2 + 1500 * math.cos(b), H / 2 + 1500 * math.sin(b))], np.int32)
                cv2.fillPoly(f, [pts], self.YEL if j % 2 else (240, 120, 40), cv2.LINE_AA)
            s1 = V.text_img("STALIN", "bangers", 300, self.YEL, tracking=8, stroke=14, stroke_color=self.INK)
            s2 = V.text_img("NA SPLÁTKY!", "bangers", 170, (255, 255, 255), tracking=6, stroke=12,
                            stroke_color=self.INK)
            for im, y, t0 in ((s1, 400, 0.0), (s2, 660, 0.25)):
                u = lin(lt, t0, t0 + 0.25)
                V.place(f, im, W / 2 + 10, y + 12, 0.5 + 0.5 * ease_back(u), -5, clamp(u * 3) * 0.6, shadow=False)
                V.place(f, im, W / 2, y, 0.5 + 0.5 * ease_back(u), -5, clamp(u * 3), shadow=False)
            self.caption(f, "Č. 1 · 1962", 120, 880, lin(lt, 0.6, 0.9), 64, 3)
        return V.finish(f, int(t * FPS), 2.0, 0.15)

    sfx = [(0.05, "whoosh", 0.6), (0.4, "pop", 0.5), (2.3, "whoosh", 0.5), (2.6, "jackhammer", 0.7),
           (3.6, "whoosh", 0.5), (3.9, "impact", 0.7), (5.3, "whoosh", 0.6), (6.1, "hit", 0.7), (7.9, "whoosh", 0.6),
           (9.2, "pop", 0.7), (11.72, "impact", 1.0), (12.0, "pop", 0.6)]


S.STYLES.update({c.name: c for c in (Flat, Iso, Blueprint, Neon, Comic)})
NEW = ["flat", "iso", "blueprint", "neon", "comic"]

if __name__ == "__main__":
    if sys.argv[1] == "sheet":
        keep = dict(S.STYLES)
        S.STYLES.clear()
        S.STYLES.update({k: keep[k] for k in NEW})
        S.OUT = os.path.join(V.BUILD, "styles2")
        S.sheet()
    else:
        S.OUT = os.path.join(V.BUILD, "styles2")
        for s in sys.argv[2:] or NEW:
            S.render_video(s)
