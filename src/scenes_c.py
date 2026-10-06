"""Scenes 8-10: machine vision today, the surveillance question, end card."""
import math

import cv2
import numpy as np

from detect import COCO
from fx import (AMBER, BG, CYAN, GREY, H, RED, W, WHITE, Clip, Dets, View, blit, brackets,
                canvas, chip, clamp, det_box, ease_out, fill_rect, grade, lerp, lin, line, mix,
                overlay, paste, smooth, text, window)
from scenes_a import Scene, Wall


_SHADE = np.linspace(1.0, 0.45, 170, dtype=np.float32) ** 1.5


def hud(f, t, cam, place, count=None, count_label="OBJECTS", extra=""):
    """Security-camera style overlay along the bottom of the frame."""
    band = f[H - 170:]
    band[:] = (band * _SHADE[:, None, None]).astype(np.uint8)
    if int(t * 2) % 2 == 0:
        cv2.circle(f, (70, H - 60), 9, RED, -1, cv2.LINE_AA)
    text(f, "LIVE", 90, H - 60, "mono_bold", 24, WHITE, 0.95, "lm")
    text(f, f"{cam}  ·  {place}{extra}", 168, H - 60, "mono", 22, WHITE, 0.85, "lm")
    if count is not None:
        text(f, count_label, W - 70, H - 112, "mono", 20, WHITE, 0.8, "rb", tracking=3)
        text(f, str(count), W - 70, H - 30, "display", 64, AMBER, 1, "rb")


class Shot:
    """A piece of footage with live detection boxes drawn over it."""

    def __init__(self, clip, t0, classes, zoom=1.0, center=None, min_score=0.5, tmap=None):
        self.clip, self.dets = Clip(clip), Dets(clip, "obj")
        self.t0, self.classes, self.zoom, self.center = t0, classes, zoom, center
        self.min_score, self.tmap = min_score, tmap

    def render(self, t, sat=0.85):
        img, idx = self.clip.at(self.tmap(t) if self.tmap else self.t0 + t)
        v = View(img.shape[1], img.shape[0], zoom=self.zoom, center=self.center)
        dets = self.dets.get(idx, self.classes, self.min_score, hold=3)
        return grade(v.render(img), sat=sat), v, dets


class Today(Scene):
    def __init__(self, spec):
        super().__init__(spec)
        S = self.S
        self.cuts = [0.0, 0.95, 1.9, S[1], S[5], S[5] + 2.25, self.D]
        self.shots = [
            Shot("fruit-and-vegetable-detection", 9.0, {47}, zoom=1.15, center=(480, 300)),
            Shot("car-detection", 17.6 - 0.95, {2}, zoom=1.1),
            Shot("bottle-detection", 3.0 - 1.9, {39}, zoom=1.05),
            # time-remapped with one jump cut so each object is in frame when it is named
            Shot("person-bicycle-car-detection", 0, {0, 1, 2}, min_score=0.42,
                 tmap=lambda t, S=S: (np.interp(t, [S[1], S[2] + 0.3, S[3]], [40.0, 43.4, 43.7])
                                      if t < S[3] else
                                      np.interp(t, [S[3], S[4], S[5]], [46.3, 47.2, 48.25]))),
            Shot("store-aisle-detection", 18.0 - S[5], {0}),
            Shot("worker-zone-detection", 26.0 - S[5] - 2.25, {0}),
        ]
        self.places = [("CAM 03", "PACKING LINE"), ("CAM 11", "LOADING BAY"),
                       ("CAM 07", "QUALITY CHECK"), ("CAM 04", "PARKING LOT"),
                       ("CAM 02", "STORE AISLE 6"), ("CAM 09", "WAREHOUSE FLOOR")]
        self.zone = np.array([(880, 610), (1420, 560), (1560, 700), (960, 790)], np.float32)
        self.alert_t = None

    def frame(self, t):
        k = max(i for i, c in enumerate(self.cuts[:-1]) if t >= c)
        if k > 0:
            self.event(self.cuts[k], "cut", 0.35)
        shot = self.shots[k]
        f, v, dets = shot.render(t)
        if k <= 2:
            for d in dets:
                det_box(f, v.box(d), f"{COCO[int(d[5])].upper()} {d[4]:.2f}", AMBER,
                        appear=lin(t, self.cuts[k] + 0.1, self.cuts[k] + 0.35), size=24)
            self.event(self.cuts[k] + 0.1, "blip", 0.5)
            hud(f, t, *self.places[k])
        elif k == 3:
            self.parking(f, t, v, dets)
        elif k == 4:
            for d in dets:
                det_box(f, v.box(d), f"SHOPPER {d[4]:.2f}", AMBER, size=22)
            hud(f, t, *self.places[k], count=len(dets), count_label="SHOPPERS IN AISLE")
        else:
            self.worker(f, t, v, dets)
        return self.fade(f, t, fin=0.2, fout=0.3)

    def parking(self, f, t, v, dets):
        S = self.S
        scan0 = S[1] + 0.9
        u = (t - scan0) / 0.8
        scan_y = lerp(-40, H + 40, clamp(u)) if u >= 0 else -100
        if 0 <= u <= 1:
            def draw(ov, ox, oy):
                cv2.rectangle(ov, (0, int(scan_y) - 60 - oy), (W, int(scan_y) - oy), AMBER, -1)
            overlay(f, 0.10, draw)
            line(f, (0, scan_y), (W, scan_y), (255, 222, 150), 3)
            self.event(scan0, "scan", 0.8)
        words = {0: S[2], 2: S[3], 1: S[4]}
        n = 0
        for d in dets:
            c = int(d[5])
            box = v.box(d)
            if u < 0 or (u <= 1 and (box[1] + box[3]) / 2 > scan_y):
                continue
            n += 1
            hot = words[c] <= t < words[c] + 0.75
            focus = any(w <= t < w + 0.75 for w in words.values())
            a = 1.0 if hot or not focus else 0.45
            size = 34 if hot else 22
            det_box(f, box, f"{COCO[c].upper()} {d[4]:.2f}", AMBER, alpha=a, size=size,
                    thick=4 if hot else 2)
            if hot:
                self.event(words[c], "blip_hi", 1.0)
        if t >= S[3]:
            self.event(S[3], "cut", 0.35)
        fi = int(self.shots[3].tmap(t) * 12)
        hud(f, t, *self.places[3], count=n, extra=f"  ·  FRAME {fi:06d}")

    def worker(self, f, t, v, dets):
        poly = np.array([v.pt(x, y) for x, y in self.zone], np.int32)
        inside = False
        for d in dets:
            foot = (d[0] + d[2] / 2, d[1] + d[3])
            if cv2.pointPolygonTest(self.zone.reshape(-1, 1, 2), foot, False) >= 0:
                inside = True
        if inside and self.alert_t is None:
            self.alert_t = t
        alert = self.alert_t is not None and t >= self.alert_t
        pulse = 0.5 + 0.5 * math.sin(t * 14) if alert else 0
        col = RED if alert else AMBER

        def draw(ov, ox, oy):
            cv2.fillPoly(ov, [poly], col)
        overlay(f, 0.18 + 0.22 * pulse, draw)
        cv2.polylines(f, [poly], True, col, 3, cv2.LINE_AA)
        x0, y0 = poly[:, 0].min(), poly[:, 1].min()
        chip(f, "RESTRICTED ZONE", x0 + 40, y0 - 4, col, size=20)
        for d in dets:
            det_box(f, v.box(d), f"WORKER {d[4]:.2f}", RED if alert else AMBER, size=22,
                    thick=3 if alert else 2)
        hud(f, t, *self.places[5])
        if alert:
            a = ease_out(lin(t, self.alert_t, self.alert_t + 0.2))
            fill_rect(f, 560, 150, 1360, 236, (120, 16, 14), 0.9 * a)
            tri = np.array([(612, 214), (640, 166), (668, 214)], np.int32)
            cv2.fillPoly(f, [tri], WHITE, cv2.LINE_AA)
            text(f, "!", 640, 198, "display", 34, (120, 16, 14), a, "cm")
            text(f, "WORKER IN DANGER ZONE", 990, 193, "display", 42, WHITE, a, "cm")
            self.event(self.alert_t, "alarm", 1.0)


# ---------------------------------------------------------------------- watch
WATCH_TILES = [
    ("person-bicycle-car-detection", 44.4), ("classroom", 5.0),
    ("fruit-and-vegetable-detection", 31.0), ("car-detection", 17.0),
    ("face-demographics-walking", 4.0), ("store-aisle-detection", 19.0),
    ("one-by-one-person-detection", 8.0), ("bottle-detection", 2.0),
    ("worker-zone-detection", 36.5), ("head-pose-face-detection-female-and-male", 2.0),
    ("people-detection", 0.5), ("driver-action-recognition", 30.0),
    ("face-demographics-walking-and-pause", 7.0), ("fruit-and-vegetable-detection", 49.0),
    ("store-aisle-detection", 40.0), ("worker-zone-detection", 17.0),
]


class Watch(Scene):
    def __init__(self, spec):
        super().__init__(spec)
        self.class_clip = Clip("classroom")
        self.class_faces = Dets("classroom", "face")
        self.pair = Clip("head-pose-face-detection-female-and-male")
        self.pair_faces = Dets("head-pose-face-detection-female-and-male", "face")
        self.wall = None
        rng = np.random.default_rng(9)
        self.prints = [rng.random(48) for _ in range(2)]

    def frame(self, t):
        S = self.S
        if t < S[1]:
            f = self.classroom(t)
        elif t < S[2]:
            f = self.identify(t)
            self.event(S[1], "cut", 0.3)
        else:
            f = self.wall_shot(t)
        return self.fade(f, t, fin=0.25, fout=0.2)

    def classroom(self, t):
        img, idx = self.class_clip.at(3.0 + t)
        z = 1 + 0.08 * t / self.S[1]
        v = View(img.shape[1], img.shape[0], zoom=z, center=(980, 560))
        f = grade(v.render(img), sat=0.4, cool=0.7, bright=0.9)
        faces = sorted(self.class_faces.get(idx, None, 0.6), key=lambda d: d[0])
        for k, d in enumerate(faces):
            x0, y0, x1, y1 = v.box(d)
            a = ease_out(lin(t, 0.5 + k * 0.18, 0.75 + k * 0.18))
            pad = 14
            overlay(f, a, lambda ov, ox, oy: brackets(ov, x0 - pad - ox, y0 - pad - oy,
                                                      x1 + pad - ox, y1 + pad - oy, WHITE,
                                                      arm=18, thick=2),
                    (x0 - pad - 4, y0 - pad - 4, x1 + pad + 4, y1 + pad + 4))
            chip(f, f"FACE {k + 1:02d}", x0 - pad, y0 - pad - 4, WHITE, size=18, alpha=a)
            self.event(0.5 + k * 0.18, "blip", 0.4)
        band = f[:150]
        band[:] = (band * _SHADE[:150][::-1, None, None]).astype(np.uint8)
        text(f, f"FACES DETECTED: {len(faces)}", 70, 66, "mono_bold", 24, WHITE, 0.9, "lm")
        return f

    def identify(self, t):
        S = self.S
        lt = t - S[1]
        img, idx = self.pair.at(0.5 + lt)
        v = View(img.shape[1], img.shape[0], zoom=1.0)
        f = grade(v.render(img), sat=0.45, cool=0.6, bright=0.85)
        faces = sorted(self.pair_faces.get(idx, None, 0.6, hold=3), key=lambda d: d[0])[:2]
        a = ease_out(lin(lt, 0.15, 0.5))
        for k, d in enumerate(faces):
            x0, y0, x1, y1 = v.box(d)
            pts = [v.pt(d[6 + 2 * j], d[7 + 2 * j]) for j in range(5)]

            def draw(ov, ox, oy, pts=pts, x0=x0, y0=y0, x1=x1, y1=y1):
                brackets(ov, x0 - ox, y0 - oy, x1 - ox, y1 - oy, CYAN, arm=26, thick=3)
                q = [(int(x - ox), int(y - oy)) for x, y in pts]
                for i, j in ((0, 1), (0, 2), (1, 2), (2, 3), (2, 4), (3, 4), (0, 3), (1, 4)):
                    cv2.line(ov, q[i], q[j], CYAN, 1, cv2.LINE_AA)
                for p in q:
                    cv2.circle(ov, p, 5, WHITE, -1, cv2.LINE_AA)
            overlay(f, a, draw)
            chip(f, f"FACE {'AB'[k]}", x0, y0 - 4, CYAN, size=20, alpha=a)
        # identity search panel along the bottom
        top = 700
        band = f[top:]
        band[:] = (band * 0.28).astype(np.uint8)
        line(f, (0, top), (W, top), mix(BG, CYAN, a), 2)
        text(f, "IDENTITY SEARCH", 70, top + 22, "mono_bold", 26, WHITE, a, tracking=3)
        for k, d in enumerate(faces):
            px, y = 70 + k * 930, top + 80
            ka = ease_out(lin(lt, 0.4 + k * 0.3, 0.8 + k * 0.3))
            if ka <= 0:
                continue
            fx0, fy0 = int(max(d[0] - d[2] * 0.25, 0)), int(max(d[1] - d[3] * 0.25, 0))
            fx1 = int(min(d[0] + d[2] * 1.25, img.shape[1]))
            fy1 = int(min(d[1] + d[3] * 1.25, img.shape[0]))
            thumb = grade(cv2.resize(img[fy0:fy1, fx0:fx1], (150, 150)), sat=0.4, cool=0.5)
            paste(f, thumb, px, y)
            cv2.rectangle(f, (px, y), (px + 150, y + 150), CYAN, 2)
            text(f, f"FACE {'AB'[k]}", px + 175, y + 2, "mono_bold", 24, CYAN, ka)
            text(f, "FACEPRINT", px + 175, y + 44, "mono", 18, GREY, ka, tracking=2)
            for j, val in enumerate(self.prints[k][:40]):
                hgt = 6 + 34 * (0.6 * val + 0.4 * abs(math.sin(lt * 5 + j)))
                fill_rect(f, px + 175 + j * 7, y + 118 - hgt, px + 180 + j * 7, y + 118, CYAN,
                          0.85 * ka)
            prog = smooth(lin(lt, 1.0 + k * 0.35, 3.6 + k * 0.35))
            bx, bx1 = px + 490, px + 860
            text(f, "SEARCHING DATABASE" if prog < 1 else "MATCH FOUND", bx, y + 2, "mono_bold",
                 22, WHITE if prog < 1 else AMBER, ka)
            fill_rect(f, bx, y + 46, bx1, y + 58, (36, 40, 48), ka)
            fill_rect(f, bx, y + 46, bx + (bx1 - bx) * prog, y + 58, CYAN if prog < 1 else AMBER,
                      ka)
            if prog >= 1:
                ra = ease_out(lin(lt, 3.6 + k * 0.35, 3.9 + k * 0.35))
                text(f, "NAME", bx, y + 104, "mono", 18, GREY, ra, "lm")
                fill_rect(f, bx + 70, y + 88, bx + 70 + 190 * ra, y + 120, (230, 230, 225), ra)
                text(f, "0.98" if k == 0 else "0.97", bx1, y + 104, "display", 34, AMBER, ra, "rm")
                self.event(S[1] + 3.6 + k * 0.35, "confirm", 0.8)
        return f

    def wall_shot(self, t):
        S = self.S
        if self.wall is None:
            self.wall = Wall(WATCH_TILES, with_dets=True)
        lt = t - S[2]
        f = canvas((4, 5, 7))
        s = lerp(1.0, 0.9, smooth(lin(t, S[2], self.D)))
        dim = smooth(lin(t, S[3] + 0.3, S[3] + 2.4))
        boxes = ease_out(lin(lt, 0.2, 0.6)) * (1 - smooth(lin(t, self.D - 1.4, self.D - 0.3)))
        self.wall.draw(f, lt, s, (W / 2, H / 2), sat=lerp(0.55, 0.2, dim),
                       bright=lerp(0.95, 0.0, dim), boxes=boxes, hud=1 - dim)
        self.event(S[2] + 0.2, "blip_many", 0.8)
        return f


# ------------------------------------------------------------------------ end
CREDITS = [
    ("NARRATION", "Synthetic voice · Kokoro TTS"),
    ("FOOTAGE", "Intel IoT DevKit sample videos · CC BY 4.0"),
    ("DETECTION", "YOLOX & YuNet (OpenCV Model Zoo), run on the footage"),
    ("DATA", "ImageNet · ILSVRC results 2010–2015"),
    ("MUSIC", "Original synthesized score"),
]


class End(Scene):
    def frame(self, t):
        f = canvas(BG)
        a = ease_out(lin(t, 0.2, 1.0))
        text(f, "HOW MACHINES LEARNED TO SEE", 960, 330, "display", 64, WHITE, a, "cm", tracking=4)
        line(f, (960 - 260 * a, 392), (960 + 260 * a, 392), AMBER, 3)
        for k, (role, who) in enumerate(CREDITS):
            ka = ease_out(lin(t, 1.0 + k * 0.15, 1.5 + k * 0.15))
            y = 480 + k * 52
            text(f, role, 900, y, "mono_bold", 22, AMBER, ka, "rm", tracking=3)
            text(f, who, 930, y, "mono", 22, (200, 202, 205), ka, "lm")
        return self.fade(f, t, fin=0.0, fout=0.9)
