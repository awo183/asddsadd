"""Scenes 5-7: hand-written rules, learning from examples, ImageNet."""
import json
import math
import os

import cv2
import numpy as np

from fx import (AMBER, BG, BUILD, CYAN, GREEN, GREY, H, RED, W, WHITE, Clip, Dets, View, blit,
                canvas, chip, clamp, dashed, ease_out, fill_rect, grade, lerp, lin, line, mix,
                overlay, paste, smooth, text, text_rgba, window)
from scenes_a import Scene


def load_crops():
    with open(os.path.join(BUILD, "crops", "index.json")) as f:
        index = json.load(f)
    out = []
    for it in index:
        img = cv2.imread(os.path.join(BUILD, "crops", it["file"]))
        out.append((cv2.cvtColor(img, cv2.COLOR_BGR2RGB), it["label"]))
    return out


# ---------------------------------------------------------------------- rules
CODE = [
    "# hand-written vision rules",
    "def is_person(image):",
    "    edges   = find_edges(image)",
    "    corners = find_corners(edges)",
    "    head    = find_circle(edges)",
    "    body    = find_box(edges, below=head)",
    "    if head and body \\",
    "       and body.height > 2 * head.height:",
    "        return True",
    "    return False",
]


class Rules(Scene):
    CLIP = "face-demographics-walking-and-pause"
    PANEL = (1150, 170, 1850, 910)

    def __init__(self, spec):
        super().__init__(spec)
        self.clip = Clip(self.CLIP)
        self.obj = Dets(self.CLIP, "obj")
        self.faces = Dets(self.CLIP, "face")
        self.cps = 50.0
        self.starts, t = [], 0.6
        for i, s in enumerate(CODE):
            self.starts.append(t)
            for k in range(0, len(s), 2):
                if s[k] != " ":
                    self.event(t + k / self.cps, "key", 0.35, key=("key", i, k))
            t += len(s) / self.cps + 0.08
        s1, s2, s3, s4 = self.S[1:5]
        self.t_light, self.t_angle, self.t_shadow, self.t_fail = s4 + 0.9, s4 + 1.55, s4 + 2.2, s4 + 3.0
        self.last_person = None

    def clip_time(self, t):
        return 4.2 + t * 0.85

    def footage(self, t):
        img, idx = self.clip.at(self.clip_time(t))
        view = View(img.shape[1], img.shape[0], zoom=1.12, center=(560, 216))
        f = grade(view.render(img), sat=0.8)
        # what breaks the rules: lighting, angle, shadows
        light = lerp(1.0, 0.34, smooth(lin(t, self.t_light, self.t_light + 0.45)))
        ang = lerp(0, -9, smooth(lin(t, self.t_angle, self.t_angle + 0.5)))
        if ang:
            m = cv2.getRotationMatrix2D((620, 560), ang, 1 + abs(ang) * 0.012)
            f = cv2.warpAffine(f, m, (W, H), borderMode=cv2.BORDER_REPLICATE)
        else:
            m = None
        sh = smooth(lin(t, self.t_shadow, self.t_shadow + 0.6))
        if sh > 0:
            yy, xx = np.ogrid[0:H, 0:W]
            edge = lerp(-400, 820, sh) + (yy - 540) * 0.45
            mask = np.clip((edge - xx) / 6.0, 0, 1).astype(np.float32)
            f = (f * (1 - 0.72 * mask[..., None])).astype(np.uint8)
        if light < 1:
            f = cv2.convertScaleAbs(f, alpha=light, beta=-12 * (1 - light))
        return f, img, idx, view, m

    def frame(self, t):
        f, src, idx, view, rot = self.footage(t)
        s1, s2, s3, s4 = self.S[1:5]
        edges_on = smooth(lin(t, s1, s1 + 0.55))
        if edges_on > 0:
            gray = cv2.GaussianBlur(cv2.cvtColor(f, cv2.COLOR_RGB2GRAY), (3, 3), 1.0)
            e = cv2.dilate(cv2.Canny(gray, 16, 40), np.ones((2, 2), np.uint8))
            wipe = int(lerp(0, W, edges_on))
            footage_k = lerp(0.22, 0.5, lin(t, self.t_light - 0.2, self.t_light + 0.3))
            if wipe > 0:
                dark = cv2.convertScaleAbs(np.ascontiguousarray(f[:, :wipe]), alpha=footage_k)
                dark[e[:, :wipe] > 0] = AMBER
                f[:, :wipe] = dark
            if 0 < wipe < W:
                line(f, (wipe, 0), (wipe, H), (255, 225, 160), 3)
            self.event(s1, "scan", 0.7)
        else:
            f = cv2.convertScaleAbs(f, alpha=0.82)
        if t >= s2:
            self.corners(f, src, view, rot, t, s2)
        if t >= s3:
            self.template(f, idx, view, rot, t, s3)
        self.code_panel(f, t)
        if self.t_fail <= t < self.t_fail + 0.3:      # glitch
            k = int(14 * math.sin((t - self.t_fail) * 60))
            f[..., 0] = np.roll(f[..., 0], k, axis=1)
            f[..., 2] = np.roll(f[..., 2], -k, axis=1)
            self.event(self.t_fail, "glitch", 0.9)
        return self.fade(f, t, fin=0.25, fout=0.3)

    def map_pt(self, view, rot, x, y):
        X, Y = view.pt(x, y)
        if rot is not None:
            X, Y = rot @ np.array([X, Y, 1.0])
        return X, Y

    def corners(self, f, src, view, rot, t, s2):
        gray = cv2.cvtColor(src, cv2.COLOR_RGB2GRAY)
        pts = cv2.goodFeaturesToTrack(gray, maxCorners=110, qualityLevel=0.02, minDistance=9)
        if pts is None:
            return
        n = int(len(pts) * ease_out(lin(t, s2, s2 + 0.7)))
        fail = lin(t, self.t_light, self.t_fail)
        rng = np.random.default_rng(int(t * 30))
        for k, p in enumerate(pts[:n]):
            X, Y = self.map_pt(view, rot, *p[0])
            if fail > 0 and rng.random() < fail * 0.6:   # corners vanish as the light goes
                continue
            c = CYAN
            cv2.line(f, (int(X) - 8, int(Y)), (int(X) + 8, int(Y)), c, 2, cv2.LINE_AA)
            cv2.line(f, (int(X), int(Y) - 8), (int(X), int(Y) + 8), c, 2, cv2.LINE_AA)
        if n:
            self.event(s2, "ticks", 0.6)

    def template(self, f, idx, view, rot, t, s3):
        persons = self.obj.get(idx, {0}, 0.5)
        faces = self.faces.get(idx, None, 0.6)
        if persons:
            self.last_person = (max(persons, key=lambda d: d[2] * d[3]),
                                max(faces, key=lambda d: d[2] * d[3]) if faces else None)
        if self.last_person is None:
            return
        p, fc = self.last_person
        fail = t >= self.t_fail
        a = ease_out(lin(t, s3, s3 + 0.4))
        col = RED if fail else GREEN
        jit = (8 * math.sin(t * 41), 6 * math.cos(t * 37)) if fail else (0, 0)
        if fc is not None:
            hx, hy, hr = fc[0] + fc[2] / 2, fc[1] + fc[3] / 2, max(fc[2], fc[3]) * 0.68
        else:
            hx, hy, hr = p[0] + p[2] / 2, p[1] + p[3] * 0.15, p[2] * 0.2
        HX, HY = self.map_pt(view, rot, hx, hy)
        HX, HY = HX + jit[0] * 3, HY + jit[1] * 2
        R = hr * view.s
        bx0, by0 = self.map_pt(view, rot, p[0] + p[2] * 0.08, hy + hr * 1.05)
        bx1, by1 = self.map_pt(view, rot, p[0] + p[2] * 0.92, p[1] + p[3])
        bx0, bx1 = bx0 - jit[0] * 4, bx1 + jit[0] * 2

        def draw(ov, ox, oy):
            cv2.circle(ov, (int(HX), int(HY)), int(R), col, 3, cv2.LINE_AA)
            for (x0, y0, x1, y1) in ((bx0, by0, bx1, by0), (bx1, by0, bx1, by1),
                                     (bx0, by1, bx1, by1), (bx0, by0, bx0, by1)):
                dashed(ov, (x0, y0), (x1, y1), col, 3)
            dashed(ov, (HX, HY + R), (HX, min(by1, H - 20)), col, 2, 8, 8)
        overlay(f, a, draw)
        lab = "PERSON? NO" if fail else "PERSON? YES"
        chip(f, lab, HX - R, HY - R - 10, col, size=26, alpha=a)
        if fail:
            self.event(self.t_fail, "error", 1.0)
        else:
            self.event(s3, "confirm", 0.7)
        chip(f, "HEAD", HX + R + 10, HY, col, size=18, alpha=a, anchor="lm")
        chip(f, "BODY", bx0 - 10, (by0 + min(by1, H)) / 2, col, size=18, alpha=a, anchor="rm")

    def code_panel(self, f, t):
        x0, y0, x1, y1 = self.PANEL
        a = ease_out(lin(t, 0.15, 0.6))
        fill_rect(f, x0, y0, x1, y1, (10, 11, 15), 0.86 * a)
        fill_rect(f, x0, y0, x1, y0 + 46, (24, 26, 32), 0.95 * a)
        for k, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
            cv2.circle(f, (x0 + 26 + k * 22, y0 + 23), 7, mix((24, 26, 32), c, a), -1, cv2.LINE_AA)
        text(f, "rules.py", (x0 + x1) / 2, y0 + 23, "mono", 20, GREY, a, "cm")
        s1, s2, s3 = self.S[1:4]
        hl = {2: s1, 3: s2, 4: s3, 5: s3, 6: s3, 7: s3}
        fail_u = lin(t, self.t_fail - 0.4, self.t_fail + 0.6)
        for i, (s, t0) in enumerate(zip(CODE, self.starts)):
            n = int(clamp((t - t0) * self.cps, 0, len(s)))
            if not n:
                continue
            y = y0 + 78 + i * 50
            col = GREY if s.lstrip().startswith("#") else WHITE
            if i in hl and t >= hl[i]:
                k = ease_out(lin(t, hl[i], hl[i] + 0.25))
                failed = fail_u > 0 and i >= 2 and (i - 2) / 6 < fail_u
                hc = RED if failed else AMBER
                fill_rect(f, x0 + 8, y - 6, x1 - 8, y + 38, hc, 0.16 * k)
                fill_rect(f, x0 + 8, y - 6, x0 + 12, y + 38, hc, k)
                col = mix(col, hc, k)
                if failed and i <= 5:
                    text(f, "×", x1 - 30, y + 16, "mono_bold", 30, RED, 1, "cm")
            text(f, s[:n], x0 + 30, y, "mono", 24, col, a)
            if n < len(s) and int(t * 4) % 2 == 0:
                w = text_rgba(s[:n], "mono", 24, WHITE).shape[1]
                fill_rect(f, x0 + 30 + w, y + 2, x0 + 42 + w, y + 32, AMBER, a)
        if t >= self.t_fail:
            k = ease_out(lin(t, self.t_fail, self.t_fail + 0.3))
            fill_rect(f, x0, y1 - 74, x1, y1, (60, 14, 14), 0.9 * k)
            text(f, "RuleError: no person found", x0 + 30, y1 - 37, "mono_bold", 26, RED, k, "lm")


# ------------------------------------------------------------------- learning
class Learning(Scene):
    LAYERS_X = [800, 990, 1180, 1370, 1560]
    COUNTS = [5, 8, 8, 6, 3]
    OUT_LABELS = ["person", "car", "bicycle"]
    SLOT = (600, 560)

    def __init__(self, spec):
        super().__init__(spec)
        self.crops = [c for c in load_crops() if c[1] in self.OUT_LABELS]
        rng = np.random.default_rng(11)
        self.nodes = []
        for x, n in zip(self.LAYERS_X, self.COUNTS):
            self.nodes.append([(x, 560 + (k - (n - 1) / 2) * 92) for k in range(n)])
        self.edges = []
        for l in range(len(self.nodes) - 1):
            for i, a in enumerate(self.nodes[l]):
                for j, b in enumerate(self.nodes[l + 1]):
                    self.edges.append((l, a, b, rng.random() ** 2, rng.random() * 6.28,
                                       3 + rng.random() * 6))
        # schedule of training examples sliding in
        self.items, t, k = [], self.S[1] + 0.1, 0
        order = rng.permutation(len(self.crops))
        while t < self.D:
            gap = lerp(0.42, 0.075, smooth(lin(t, self.S[1] + 1.5, self.S[2] + 2.0)))
            self.items.append((t, order[k % len(order)]))
            t += gap
            k += 1
        self.travel = 1.1
        self.probs = np.array([0.33, 0.33, 0.34])

    def frame(self, t):
        f = canvas(BG)
        s1, s2 = self.S[1], self.S[2]
        # --- "So researchers flipped the problem."
        if t < s1 + 0.6:
            a = window(t, 0.15, s1 + 0.2, 0.3)
            u = lin(t, 1.15, 1.7)
            word, col = ("RULES", WHITE) if u < 0.5 else ("EXAMPLES", AMBER)
            img = text_rgba(word, "display", 150, col, 10)
            sy = abs(math.cos(math.pi * u))
            if sy > 0.02:
                img = cv2.resize(img, (img.shape[1], max(1, int(img.shape[0] * sy))))
                blit(f, img, 960 - img.shape[1] / 2, 540 - img.shape[0] / 2, a)
            if u <= 0 and t > 0.55:
                w = text_rgba("RULES", "display", 150, WHITE, 10).shape[1]
                k = ease_out(lin(t, 0.55, 0.95))
                line(f, (960 - w / 2 - 20, 548), (960 - w / 2 - 20 + (w + 40) * k, 548), RED, 9)
            self.event(1.15, "flip", 0.8)
        if t < s1 - 0.2:
            return self.fade(f, t, fin=0.25)
        net_a = ease_out(lin(t, s1 - 0.2, s1 + 0.5))
        text(f, "LEARNING FROM EXAMPLES", 120, 96, "mono_bold", 26, AMBER, net_a, tracking=4)
        progress = smooth(lin(t, s1, self.D - 0.6))
        # --- waves of activation from arrivals
        arrivals = [ta + self.travel for ta, _ in self.items if ta + self.travel <= t]
        recent = [ta for ta in arrivals if t - ta < 0.9]

        def act(layer, seed):
            v = 0.0
            for ta in recent:
                r = (np.sin(seed * 12.9898 + ta * 78.233) * 43758.5453) % 1.0
                v = max(v, math.exp(-((t - ta - layer * 0.11) / 0.09) ** 2) * (0.35 + 0.65 * r))
            return v

        # edges
        for (l, a, b, w, ph, fr) in self.edges:
            flick = 0.5 + 0.5 * math.sin(t * fr + ph)
            wt = lerp(flick, w, progress)
            boost = act(l + 0.5, a[1] + b[1] * 0.37)
            k = clamp((0.08 + 0.42 * wt + 0.7 * boost) * net_a)
            line(f, a, b, mix((24, 27, 33), AMBER, k), 1 + int(wt * 2.2 * progress + boost * 2))
        # nodes
        for l, layer in enumerate(self.nodes):
            for (x, y) in layer:
                v = act(l, x * 0.01 + y)
                cv2.circle(f, (int(x), int(y)), 17, mix(BG, (48, 52, 60), net_a), -1, cv2.LINE_AA)
                if v > 0.02:
                    cv2.circle(f, (int(x), int(y)), 17, mix((48, 52, 60), AMBER, v * net_a), -1,
                               cv2.LINE_AA)
                cv2.circle(f, (int(x), int(y)), 17, mix(BG, (120, 126, 136), net_a), 2, cv2.LINE_AA)
        # layer captions
        for x, cap in zip(self.LAYERS_X, ("INPUT", "", "HIDDEN LAYERS", "", "OUTPUT")):
            if cap:
                text(f, cap, x, 935, "mono", 18, GREY, net_a, "ct", tracking=3)
        # outputs
        cur = None
        if arrivals:
            cur = self.crops[self.items[len(arrivals) - 1][1]][1]
        target = np.full(3, 1 / 3)
        if cur:
            noise = np.abs(np.sin(np.array([1.7, 2.3, 3.1]) * t * 3)) * (1 - progress)
            target = noise + 0.05
            target[self.OUT_LABELS.index(cur)] += lerp(0.2, 6.0, progress)
            target /= target.sum()
        self.probs += (target - self.probs) * 0.25
        for k, (lab, (x, y)) in enumerate(zip(self.OUT_LABELS, self.nodes[-1])):
            p = float(self.probs[k])
            hot = lab == cur and progress > 0.5
            text(f, lab.upper(), x + 36, y - 14, "mono_bold", 22, AMBER if hot else WHITE, net_a,
                 "lm")
            fill_rect(f, x + 36, y + 4, x + 236, y + 14, (40, 44, 52), net_a)
            fill_rect(f, x + 36, y + 4, x + 36 + 200 * p, y + 14, AMBER if hot else GREY, net_a)
            text(f, f"{p:.2f}", x + 248, y + 9, "mono", 20, WHITE, net_a, "lm")
        # input slot + sliding examples
        sx, sy = self.SLOT
        cv2.rectangle(f, (sx - 90, sy - 90), (sx + 90, sy + 90), mix(BG, (90, 96, 106), net_a), 2)
        for ta, ci in self.items:
            u = (t - ta) / self.travel
            if u < 0 or u > 1.25:
                continue
            img, lab = self.crops[ci]
            size = int(lerp(150, 96, lin(ta, s1 + 1.5, s2 + 2.0)))
            x = lerp(-120, sx, min(u, 1.0))
            if u > 1:
                k = 1 - (u - 1) / 0.25
                size = max(4, int(size * k))
            im = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)
            paste(f, im, x - size / 2, sy - size / 2)
            if u <= 1 and size > 100:
                chip(f, lab, x - size / 2, sy + size / 2 + 4, AMBER, size=18, anchor="lt")
            if u >= 1:
                self.event(ta + self.travel, "tick", 0.25 if size < 100 else 0.45)
        # counter
        if t > s2 - 0.3:
            a = ease_out(lin(t, s2 - 0.3, s2 + 0.2))
            n = int(10 ** lerp(1, 6.12, smooth(lin(t, s2, self.D - 0.5))))
            text(f, "EXAMPLES SEEN", 1800, 80, "mono", 20, GREY, a, "rt", tracking=3)
            text(f, f"{n:,}", 1800, 110, "display", 58, WHITE, a, "rt")
            text(f, "WEIGHTS ADJUSTING", 1800, 186, "mono", 18, AMBER,
                 a * (0.55 + 0.45 * math.sin(t * 9)), "rt", tracking=3)
        return self.fade(f, t, fin=0.25, fout=0.35)


# ------------------------------------------------------------------- imagenet
BARS = [(2010, 28.2, "NEC-UIUC"), (2011, 25.8, "XRCE"), (2012, 15.3, "AlexNet"),
        (2013, 11.7, "Clarifai"), (2014, 6.7, "GoogLeNet"), (2015, 3.6, "ResNet")]
HUMAN = 5.1


class ImageNet(Scene):
    CELL, TILE = 54, 48

    def __init__(self, spec):
        super().__init__(spec)
        crops = load_crops()
        rng = np.random.default_rng(4)
        cols, rows = int(np.ceil(W / self.CELL)) + 1, int(np.ceil(H / self.CELL)) + 1
        ox = (W - cols * self.CELL) / 2 + (self.CELL - self.TILE) / 2
        oy = (H - rows * self.CELL) / 2 + (self.CELL - self.TILE) / 2
        self.full, self.empty = canvas((14, 15, 19)), canvas((14, 15, 19))
        self.tiles = []
        for r in range(rows):
            for c in range(cols):
                img, lab = crops[rng.integers(len(crops))]
                if rng.random() < 0.5:
                    img = img[:, ::-1]
                x, y = int(ox + c * self.CELL), int(oy + r * self.CELL)
                paste(self.full, cv2.resize(img, (self.TILE, self.TILE),
                                            interpolation=cv2.INTER_AREA), x, y)
                fill_rect(self.empty, x, y, x + self.TILE, y + self.TILE, (24, 26, 31))
                self.tiles.append((x, y, lab))
        self.order = rng.permutation(len(self.tiles))
        self.pops = [(0.6 + k * 0.22, int(rng.integers(len(self.tiles)))) for k in range(26)]
        b0 = self.S[1]
        self.bar_t = [b0 + 0.45, b0 + 0.95, b0 + 2.1, b0 + 4.4, b0 + 4.95, self.S[2] + 0.4]

    def frame(self, t):
        t_chart = self.S[1] - 0.25
        if t < t_chart + 0.5:
            f = self.mosaic(t)
            if t > t_chart:
                k = smooth(lin(t, t_chart, t_chart + 0.5))
                f = cv2.addWeighted(f, 1 - k, self.chart(t), k, 0)
        else:
            f = self.chart(t)
        return self.fade(f, t, fin=0.3, fout=0.4)

    def mosaic(self, t):
        f = self.empty.copy()
        n = int(len(self.tiles) * ease_out(lin(t, 0.2, 5.8)))
        for k in self.order[:n]:
            x, y, _ = self.tiles[k]
            f[y:y + self.TILE, x:x + self.TILE] = self.full[y:y + self.TILE, x:x + self.TILE]
        s = lerp(2.3, 1.0, smooth(lin(t, 0, 6.4)))
        m = np.float32([[s, 0, W / 2 * (1 - s)], [0, s, H / 2 * (1 - s)]])
        f = cv2.warpAffine(f, m, (W, H), flags=cv2.INTER_LINEAR)
        f = cv2.convertScaleAbs(f, alpha=0.8)
        visible = set(self.order[:n].tolist())
        for tp, k in self.pops:
            if k in visible and tp < t < tp + 0.9:
                x, y, lab = self.tiles[k]
                X, Y = (x - W / 2) * s + W / 2, (y - H / 2) * s + H / 2
                a = window(t, tp, tp + 0.9, 0.12)
                cv2.rectangle(f, (int(X), int(Y)), (int(X + self.TILE * s), int(Y + self.TILE * s)),
                              AMBER, 2)
                chip(f, lab, X, Y - 3, AMBER, size=18, alpha=a)
                self.event(tp, "tick", 0.3)
        a = ease_out(lin(t, 0.4, 0.9))
        fill_rect(f, 470, 380, 1450, 700, (8, 9, 12), 0.86 * a)
        fill_rect(f, 470, 380, 476, 700, AMBER, a)
        text(f, "IMAGENET  ·  2009", 960, 430, "mono_bold", 28, AMBER, a, "cm", tracking=4)
        n_img = int(14197122 * ease_out(lin(t, 0.6, 5.6)))
        text(f, f"{n_img:,}", 960, 540, "display", 130, WHITE, a, "cm")
        text(f, "LABELED IMAGES  ·  21,841 CATEGORIES", 960, 650, "mono", 24, GREY, a, "cm",
             tracking=2)
        self.event(0.6, "count", 0.7)
        return f

    def chart(self, t):
        f = canvas(BG)
        a = ease_out(lin(t, self.S[1] - 0.2, self.S[1] + 0.3))
        text(f, "IMAGENET CHALLENGE", 170, 92, "display", 46, WHITE, a)
        text(f, "Top-5 classification error of each year's winning entry", 172, 152, "mono", 22,
             GREY, a)
        base, top, x_l, x_r = 880, 300, 260, 1500
        unit = (base - top) / 30
        for v in (0, 10, 20, 30):
            y = base - v * unit
            line(f, (x_l, y), (x_r, y), mix(BG, (40, 44, 52), a), 1)
            text(f, f"{v}%", x_l - 16, y, "mono", 20, GREY, a, "rm")
        xs = [lerp(x_l + 110, x_r - 100, i / 5) for i in range(6)]
        bw = 140
        for i, ((year, val, who), x, tb) in enumerate(zip(BARS, xs, self.bar_t)):
            u = ease_out(lin(t, tb, tb + 0.5))
            if u <= 0:
                text(f, str(year), x, base + 18, "mono_bold", 24, GREY, a * 0.5, "ct")
                continue
            deep = year >= 2012
            col = (88, 98, 115) if not deep else (AMBER if year in (2012, 2015) else (196, 146, 60))
            hgt = val * unit * u
            fill_rect(f, x - bw / 2, base - hgt, x + bw / 2, base, col)
            ly = base - max(val * u, 9.0) * unit - 12
            text(f, f"{val * u:.1f}%", x, ly, "display", 34, WHITE, u, "cb")
            text(f, who, x, ly - 44, "mono", 20, AMBER if deep else GREY, u, "cb")
            text(f, str(year), x, base + 18, "mono_bold", 24, WHITE, a, "ct")
            self.event(tb, "bar", 0.6)
        # era brackets
        for (i0, i1, lab, col, tt) in ((0, 1, "HAND-DESIGNED FEATURES", GREY, self.bar_t[1] + 0.4),
                                       (2, 5, "DEEP NEURAL NETWORKS", AMBER, self.bar_t[2] + 0.6)):
            k = ease_out(lin(t, tt, tt + 0.4))
            if k > 0:
                y = base + 66
                line(f, (xs[i0] - bw / 2, y), (xs[i0] - bw / 2 + (xs[i1] - xs[i0] + bw) * k, y), col, 2)
                text(f, lab, (xs[i0] + xs[i1]) / 2, y + 10, "mono_bold", 20, col, k, "ct",
                     tracking=3)
        # AlexNet drop callout
        tc = self.bar_t[2] + 1.0
        k = ease_out(lin(t, tc, tc + 0.4))
        if k > 0:
            y0, y1 = base - BARS[1][1] * unit, base - BARS[2][1] * unit
            xa = xs[2] + bw / 2 + 22
            dashed(f, (xs[1] + bw / 2, y0), (xa + 10, y0), WHITE, 2, 8, 6)
            line(f, (xa, y0), (xa, lerp(y0, y1, k)), WHITE, 3)
            if k > 0.9:
                cv2.arrowedLine(f, (int(xa), int(y1 - 30)), (int(xa), int(y1)), WHITE, 3,
                                cv2.LINE_AA, tipLength=0.5)
            text(f, "−10.5 pts", xa + 14, (y0 + y1) / 2, "mono_bold", 24, WHITE, k, "lm")
            self.event(tc, "whoosh", 0.5)
        # human line
        th = self.S[2] + 2.5
        k = smooth(lin(t, th, th + 0.7))
        if k > 0:
            y = base - HUMAN * unit
            dashed(f, (x_l, y), (x_r, y), CYAN, 3, 16, 10, upto=k)
            ka = lin(t, th + 0.5, th + 0.8)
            text(f, "TRAINED HUMAN", x_r + 24, y - 4, "mono_bold", 24, CYAN, ka, "lb")
            text(f, f"≈ {HUMAN}% error", x_r + 24, y + 4, "mono", 22, CYAN, ka, "lt")
            self.event(th, "sweep", 0.6)
        tr = self.S[2] + 3.5
        k = ease_out(lin(t, tr, tr + 0.3))
        if k > 0:
            x = xs[5]
            pulse = 0.5 + 0.5 * math.sin((t - tr) * 6)
            cv2.rectangle(f, (int(x - bw / 2 - 8), int(base - BARS[5][1] * unit - 8)),
                          (int(x + bw / 2 + 8), base + 4), mix(AMBER, WHITE, pulse * 0.5), 3)
            chip(f, "BELOW HUMAN ERROR", x, base - 9 * unit - 120, AMBER, size=20, alpha=k,
                 anchor="cb")
            self.event(tr, "confirm", 0.8)
        text(f, "Sources: ILSVRC results 2010–2015 · human estimate: A. Karpathy (2014)",
             170, 1062, "mono", 18, (100, 104, 112), a, "lb")
        return f
