"""Flat Vox-style explainer diagrams on paper: the Letná cross-section (slope,
plinth, basement, statue, skeleton, rubble, metronome...), the figure layout
seen from above, and a floor-area comparison."""
import math

import cv2
import numpy as np

import vox as V
from shots import Shot, annotate, draw_phrase, img, mark_sfx, register
from vox import H, INK, RED, W, WHITE, clamp, ease_back, ease_io, ease_out, lerp, lin

EARTH = (176, 150, 112)
EARTH_D = (150, 124, 90)
CONCRETE = (168, 166, 158)
CONCRETE_D = (120, 118, 112)
GRANITE = (196, 192, 184)
WATER = (150, 176, 182)
DARK = (46, 42, 38)
GLOW = (255, 196, 90)


def poly(f, pts, color, alpha=1.0, outline=None, w=3):
    p = np.round(np.array(pts, np.float32) * 4).astype(np.int32)
    if alpha >= 1:
        cv2.fillPoly(f, [p], color, cv2.LINE_AA, shift=2)
    elif alpha > 0:
        ov = f.copy()
        cv2.fillPoly(ov, [p], color, cv2.LINE_AA, shift=2)
        cv2.addWeighted(ov, alpha, f, 1 - alpha, 0, dst=f)
    if outline is not None and alpha > 0:
        cv2.polylines(f, [p], True, outline, w, cv2.LINE_AA, shift=2)


def label(f, text, x, y, u, size=40, color=INK, ax=0.5, font="oswald", bg=None):
    if u <= 0:
        return
    if bg:
        from shots import tag_img
        im = tag_img(text, size)
        V.place(f, im, x, y, 0.85 + 0.15 * ease_back(u), 0, clamp(u * 2), shadow=True, ax=ax)
        return
    im = V.text_img(text, font, size, color, tracking=3)
    V.place(f, im, x, y, 0.85 + 0.15 * ease_back(u), 0, clamp(u * 2), shadow=False, ax=ax)


# ---------------------------------------------------------------- Letná cross-section
GROUND = [(0, 470), (1060, 470), (1150, 500), (1300, 610), (1460, 760), (1600, 880), (1920, 900)]
PLINTH = [(660, 470), (700, 360), (1000, 360), (1040, 470)]
BASEMENT = (700, 490, 1010, 690)


@register("section")
class Section(Shot):
    """Cross-section of the Letná slope. Layers switch on at times given in spec['show']:
    {statue, skeleton, granite, basement, pillars, rubble, cracks, head_roll, bridge, metronome,
     person, glow, crane_x, mauzoleum, labels: [...]}"""
    grain = 3.0

    def setup(self):
        s = self.spec
        self.show = s.get("show", {})
        st = s.get("statue_img")
        self.statue = None
        if st:
            src = img(st)
            self.statue = V.cutout(src[..., :3], src[..., 3], 900, outline=6) if src.shape[2] == 4 else None
        for k, at in self.show.items():
            if isinstance(at, (int, float)) and at > 0.05 and k not in ("statue",):   # only things that appear mid-shot
                self.add(at, {"rubble": "rattle", "cracks": "wood_crack", "head_roll": "whoosh_big",
                              "crane_x": "stamp", "pillars": "pop", "basement": "whoosh",
                              "metronome": "metronome", "glow": "riser"}.get(k, "pop"), 0.5)
        self.marks = s.get("marks", [])
        mark_sfx(self, self.marks)

    def on(self, key, t):
        at = self.show.get(key)
        if at is None:
            return 0.0
        return ease_out(lin(t, at, at + 0.45))

    def draw(self, t):
        s = self.spec
        z = s.get("z0", 1.0) + (s.get("z1", 1.04) - s.get("z0", 1.0)) * ease_io(lin(t, 0, self.dur))
        cx, cy = s.get("focus", (W / 2, H / 2))
        f = V.cover(V.paper(seed=61), W, H, 1.0)
        canvas = f.copy()
        self.draw_scene(canvas, t)
        M = np.float32([[z, 0, cx - cx * z], [0, z, cy - cy * z]])
        f = cv2.warpAffine(canvas, M, (W, H), borderMode=cv2.BORDER_REPLICATE)
        for lb in s.get("labels", []):       # labels stay crisp: placed through the zoom, drawn after it
            label(f, lb["text"], cx + (lb["x"] - cx) * z, cy + (lb["y"] - cy) * z,
                  ease_out(lin(t, lb["at"], lb["at"] + 0.35)), lb.get("size", 40), tuple(lb.get("color", INK)),
                  lb.get("ax", 0.5), bg=lb.get("bg"))
        annotate(f, t, self.marks, self.seed)
        if s.get("headline"):
            draw_phrase(f, t, s["headline"])
        return f

    def draw_scene(self, f, t):
        # river and bridge
        poly(f, [(1560, 900), (1920, 900), (1920, H), (1560, H)], WATER)
        u = self.on("bridge", t)
        if u:
            poly(f, [(1500, 860), (1920, 860), (1920, 880), (1500, 880)], DARK, u)
            for x in (1620, 1780):
                poly(f, [(x, 880), (x + 24, 880), (x + 30, 960), (x - 6, 960)], DARK, u)
            label(f, "ČECHŮV MOST", 1640, 815, u, 34)
        # hill
        poly(f, GROUND + [(1920, H), (0, H)], EARTH)
        cv2.polylines(f, [np.array(GROUND, np.int32)], False, EARTH_D, 4, cv2.LINE_AA)
        # basement
        ub = self.on("basement", t)
        if ub:
            x0, y0, x1, y1 = BASEMENT
            poly(f, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], DARK, ub)
            poly(f, [(x0, (y0 + y1) / 2 - 6), (x1, (y0 + y1) / 2 - 6), (x1, (y0 + y1) / 2 + 6),
                     (x0, (y0 + y1) / 2 + 6)], CONCRETE_D, ub)
            ug = self.on("glow", t)
            if ug:
                poly(f, [(x0 + 10, y0 + 10), (x1 - 10, y0 + 10), (x1 - 10, y1 - 10), (x0 + 10, y1 - 10)],
                     GLOW, 0.35 * ug + 0.1 * ug * math.sin(t * 5))
        up = self.on("pillars", t)
        if up:
            x0, y0, x1, y1 = BASEMENT
            for k in range(7):
                x = x0 + 30 + k * (x1 - x0 - 60) / 6
                for (a, b) in ((y0, (y0 + y1) / 2 - 6), ((y0 + y1) / 2 + 6, y1)):
                    h = (b - a) * ease_out(clamp(up * 1.6 - k * 0.08))
                    poly(f, [(x - 9, b - h), (x + 9, b - h), (x + 9, b), (x - 9, b)], CONCRETE, 1.0)
        ur = self.on("rubble", t)
        if ur:
            rng = np.random.default_rng(5)
            x0, y0, x1, y1 = BASEMENT
            for _ in range(int(160 * ur)):
                x, y = rng.uniform(x0 + 10, x1 - 10), rng.uniform(y1 - (y1 - y0) * 0.9 * ur, y1 - 8)
                r = rng.uniform(8, 20)
                poly(f, [(x - r, y), (x - r * 0.3, y - r), (x + r, y - r * 0.6), (x + r * 0.7, y + r * 0.5)],
                     GRANITE if rng.random() < 0.6 else CONCRETE_D, 1.0, DARK, 1)
        # plinth
        poly(f, PLINTH, CONCRETE, 1.0, DARK, 3)
        for y in range(380, 470, 22):
            cv2.line(f, (680 + (470 - y) // 3, y), (1020 - (470 - y) // 3, y), CONCRETE_D, 2, cv2.LINE_AA)
        uc = self.on("cracks", t)
        if uc:
            rng = np.random.default_rng(9)
            for k in range(9):
                x = rng.uniform(640, 1080)
                pts = [(x, 470)]
                for j in range(8):
                    pts.append((pts[-1][0] + rng.uniform(-40, 40) + (25 if x > 900 else 0), pts[-1][1] + 38))
                V.draw_path(f, np.array(pts, float), uc, RED, 7)
        # statue
        us = self.on("statue", t) if "statue" in self.show else 0.0
        ug2 = self.on("granite", t)
        uk = self.on("skeleton", t)
        if us:
            body = [(735, 360), (965, 360), (975, 175), (925, 120), (760, 150), (735, 200)]
            if self.statue is not None and not (ug2 or uk):
                sc = 270 / self.statue.shape[0]
                V.place(f, self.statue, 850, 362, sc, 0, us, shadow=False, ay=1.0)
            else:
                poly(f, body, GRANITE, us, DARK, 3)
                if ug2:
                    for y in range(150, 360, 30):
                        for x in range(735 + (y // 30 % 2) * 30, 975, 60):
                            cv2.rectangle(f, (x, y), (x + 58, y + 28), (150, 146, 138), 2, cv2.LINE_AA)
                if uk:
                    inner = [(775, 350), (925, 350), (930, 200), (900, 165), (790, 180), (775, 215)]
                    poly(f, inner, CONCRETE_D, uk, DARK, 2)
                    for x in range(790, 925, 22):
                        cv2.line(f, (x, 350), (x, 190), (90, 60, 50), 2, cv2.LINE_AA)
                    for y in range(200, 350, 22):
                        cv2.line(f, (780, y), (925, y), (90, 60, 50), 2, cv2.LINE_AA)
        uh = self.on("head_roll", t)
        if uh:
            path = np.array([(930, 140), (1050, 300), (1150, 495), (1300, 605), (1460, 755), (1600, 845)], float)
            pts = []
            for a, b in zip(path, path[1:]):
                for k in range(20):
                    pts.append(a + (b - a) * k / 20)
            pts = np.array(pts)
            dash = pts[::3]
            n = int(len(dash) * uh)
            for k in range(0, n - 1, 2):
                cv2.line(f, tuple(dash[k].astype(int)), tuple(dash[k + 1].astype(int)), RED, 5, cv2.LINE_AA)
            p = pts[min(int(len(pts) * uh), len(pts) - 1)]
            cv2.circle(f, (int(p[0]), int(p[1]) - 28), 30, GRANITE, -1, cv2.LINE_AA)
            cv2.circle(f, (int(p[0]), int(p[1]) - 28), 30, DARK, 3, cv2.LINE_AA)
            ang = uh * 14
            cv2.line(f, (int(p[0]), int(p[1]) - 28), (int(p[0] + 26 * math.cos(ang)), int(p[1] - 28 + 26 * math.sin(ang))),
                     DARK, 3, cv2.LINE_AA)
        um = self.on("metronome", t)
        if um:
            base = (850, 360)
            poly(f, [(800, 360), (900, 360), (860, 300), (840, 300)], DARK, um)
            ang = math.radians(28 * math.sin(t * 2.4))
            tip = (850 + 330 * math.sin(ang) * um, 300 - 330 * math.cos(ang) * um)
            cv2.line(f, (850, 300), (int(tip[0]), int(tip[1])), RED, 12, cv2.LINE_AA)
        upn = self.on("person", t)
        if upn:
            from extras import person
            person(f, 1020, 360, 46 * upn, INK, upn)
        ux = self.on("crane_x", t)
        if ux:
            poly(f, [(560, 470), (580, 470), (580, 120), (560, 120)], (230, 170, 40), ux)
            poly(f, [(560, 120), (900, 120), (900, 136), (560, 136)], (230, 170, 40), ux)
            V.draw_path(f, np.array([(500, 100), (960, 480)], float), ux, RED, 14)
            V.draw_path(f, np.array([(960, 100), (500, 480)], float), clamp(ux * 1.5 - 0.5), RED, 14)


# ---------------------------------------------------------------- figures seen from above
@register("layout")
class Layout(Shot):
    """Stalin in front, two rows of four figures behind him (Soviet / Czechoslovak)."""
    grain = 3.0

    def setup(self):
        s = self.spec
        self.add(s.get("at", 0.1), "pop", 0.6)
        for k in range(8):
            self.add(s.get("rows_at", 0.6) + k * 0.12, "pop", 0.3)

    def draw(self, t):
        s = self.spec
        f = V.cover(V.paper(seed=71), W, H, 1.0 + 0.03 * lin(t, 0, self.dur))
        at, ra = s.get("at", 0.1), s.get("rows_at", 0.6)
        u = ease_back(lin(t, at, at + 0.35))
        cx = 420
        cv2.circle(f, (cx, H // 2), int(70 * u), RED, -1, cv2.LINE_AA)
        label(f, "STALIN", cx, H // 2 + 115, lin(t, at, at + 0.3), 46)
        rows = s.get("rows", [["DĚLNÍK", "VĚDEC", "KOLCHOZNICE", "RUDOARMĚJEC"],
                              ["DĚLNÍK", "ROLNICE", "NOVÁTOR", "VOJÁK"]])
        names = s.get("row_names", ["SSSR", "ČSR"])
        for r, (row, ry) in enumerate(zip(rows, (H / 2 - 190, H / 2 + 190))):
            label(f, names[r], 640, ry, lin(t, ra + r * 0.5, ra + r * 0.5 + 0.3), 44, RED, ax=1.0)
            for k, nm in enumerate(row):
                st = ra + r * 0.5 + k * 0.12
                v = ease_back(lin(t, st, st + 0.3))
                x = 760 + k * 270
                cv2.circle(f, (int(x), int(ry)), max(int(48 * v), 1), INK if r else (90, 84, 76), -1, cv2.LINE_AA)
                label(f, nm, x, ry + 85, lin(t, st, st + 0.3), 32)
        ua = ease_out(lin(t, ra + 1.2, ra + 1.8))
        if ua:
            V.draw_path(f, V.arrow_pts((1800, H / 2), (560, H / 2), 3, 30, 0.0), ua, RED, 6, head=True)
            label(f, "SMĚR POHLEDU", 1200, H / 2 - 40, ua, 30, RED)
        return f


@register("area")
class Area(Shot):
    """Floor area comparison seen from above: squares with labels (m²)."""
    grain = 3.0

    def setup(self):
        for it in self.spec["items"]:
            self.add(it["at"], "pop", 0.7)

    def draw(self, t):
        s = self.spec
        f = V.cover(V.paper(seed=81), W, H, 1.0 + 0.03 * lin(t, 0, self.dur))
        ppm = s.get("px_per_m", 150)
        for it in s["items"]:
            u = ease_back(lin(t, it["at"], it["at"] + 0.35))
            if u <= 0:
                continue
            w, h = it["w"] * ppm * u, it["h"] * ppm * u
            x, y = it["x"], s.get("y", H / 2 + 40)
            col = tuple(it.get("color", RED))
            ov = f.copy()
            cv2.rectangle(ov, (int(x - w / 2), int(y - h / 2)), (int(x + w / 2), int(y + h / 2)), col, -1, cv2.LINE_AA)
            cv2.addWeighted(ov, it.get("alpha", 0.85), f, 1 - it.get("alpha", 0.85), 0, dst=f)
            cv2.rectangle(f, (int(x - w / 2), int(y - h / 2)), (int(x + w / 2), int(y + h / 2)), INK, 3, cv2.LINE_AA)
            if it.get("person"):
                from extras import person
                person(f, x, y + h / 2 - 10, 1.8 * ppm * 0.55 * u, INK, clamp(u))
            label(f, it["label"], x, y - h / 2 - 50, lin(t, it["at"] + 0.2, it["at"] + 0.5), 46,
                  INK if it.get("color") != RED else RED)
            if it.get("sub"):
                label(f, it["sub"], x, y + h / 2 + 45, lin(t, it["at"] + 0.3, it["at"] + 0.6), 32, (80, 74, 66),
                      font="mont_med")
        return f
