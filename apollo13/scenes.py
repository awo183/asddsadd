"""Scenes for "The 28-Volt Switch" — why Apollo 13's oxygen tank exploded.

A paper-collage explainer: archival NASA photos and film printed with white
borders and laid on warm paper, a yellow marker sweeping over the real 1970
review board report, hand-drawn ink, flat maps and charts. The camera moves
across one big collage canvas: each scene is a set of panels placed on that
canvas, and the camera pans and pushes between them.

Every animation is cued to the moment a word is spoken (ElevenLabs word timings),
so the English and Czech cuts share every scene but keep their own timing.
All on-screen text comes from strings.py.
"""
import json
import math
import os
import re
import sys
from functools import lru_cache

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import look as lk  # noqa: E402
import maps  # noqa: E402
from strings import LANG, L, C, num  # noqa: E402

ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(ROOT, "build", "apollo13", "assets")
NASA = os.path.join(ASSETS, "nasa")
VIDEO = os.path.join(ASSETS, "video")
REPORT = os.path.join(ASSETS, "report")
maps.MAPS = os.path.join(ASSETS, "maps")

W, H, FPS = lk.W, lk.H, lk.FPS
INK, YELLOW, ACCENT, WHITE, PAPER = lk.INK, lk.YELLOW, lk.ACCENT, lk.WHITE, lk.PAPER
clamp, lin, smooth, ease_out, ease_in_out, back_out, lerp = (lk.clamp, lk.lin, lk.smooth, lk.ease_out,
                                                              lk.ease_in_out, lk.back_out, lk.lerp)
GAP = 260            # space between panels on the collage canvas


def norm(w):
    return re.sub(r"[^\w.,']", "", w.lower()).strip(".,'")


# ------------------------------------------------------------------ big paper canvas
_CANVAS = None


def canvas_paper():
    """One big sheet of paper that every panel of every scene sits on."""
    global _CANVAS
    if _CANVAS is None:
        path = os.path.join(ASSETS, "paper_canvas.png")
        if os.path.exists(path):
            _CANVAS = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB)
        else:
            half = lk._paper((3 * (W + GAP) + 800) // 2, (2 * (H + GAP) + 800) // 2, seed=5)
            _CANVAS = cv2.resize(half, (half.shape[1] * 2, half.shape[0] * 2), interpolation=cv2.INTER_LINEAR)
            cv2.imwrite(path, cv2.cvtColor(_CANVAS, cv2.COLOR_RGB2BGR))
    return _CANVAS


def paper_at(x, y, w=W, h=H):
    c = canvas_paper()
    x, y = int(round(x)) + 400, int(round(y)) + 400
    x = max(0, min(x, c.shape[1] - w))
    y = max(0, min(y, c.shape[0] - h))
    return c[y:y + h, x:x + w].copy()


# ------------------------------------------------------------------ media
class Clip:
    def __init__(self, name):
        self.path = os.path.join(VIDEO, name + ".mp4")
        self.cap, self.idx, self.img = None, -1, None

    def at(self, t):
        if self.cap is None:
            self.cap = cv2.VideoCapture(self.path)
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        i = max(int(t * self.fps), 0)
        if i < self.idx:
            self.cap.release()
            self.cap, self.idx = cv2.VideoCapture(self.path), -1
        while self.idx < i:
            if not self.cap.grab():
                break
            self.idx += 1
            self.img = None
        if self.img is None:
            ok, im = self.cap.retrieve()
            if ok:
                self.img = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
        return self.img


def nasa(name):
    for ext in (".jpg", ".png", ".jpeg"):
        p = os.path.join(NASA, name + ext)
        if os.path.exists(p):
            return p
    raise FileNotFoundError(name)


@lru_cache(maxsize=32)
def card(name, height, caption=None, crop=None, rot90=False, border=14, cap_size=21):
    path = nasa(name)
    if rot90:
        img = cv2.rotate(lk._load_rgb(path), cv2.ROTATE_90_CLOCKWISE)
        if crop:
            hh, ww = img.shape[:2]
            img = img[int(crop[1] * hh):int(crop[3] * hh), int(crop[0] * ww):int(crop[2] * ww)]
        s = height / img.shape[0]
        img = lk.archival(cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA))
        return lk.frame_card(img, border, 46 if caption else 0, caption, cap_size)
    return lk.photo_card(path, height, border, crop=crop, bottom=46 if caption else 0, caption=caption,
                         cap_size=cap_size)


def video_card(img, height, caption=None, border=12, crop_l=0.035):
    img = img[:, int(img.shape[1] * crop_l):]
    s = height / img.shape[0]
    im = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    im = lk.archival(im, sat=0.9, warm=0.03)
    return lk.frame_card(im, border, 44 if caption else 0, caption, 20)


# ------------------------------------------------------------------ documents
_WORDS = None


def page_words(pg):
    global _WORDS
    if _WORDS is None:
        _WORDS = json.load(open(os.path.join(REPORT, "words.json")))
    return _WORDS[str(pg)]["words"]


def phrase_boxes(pg, first, count):
    """Boxes of `count` words starting at the first word that begins with `first`
    (matched on the OCR text layer of the real scan), grouped into line strokes."""
    ws = page_words(pg)
    toks = first.lower().split()
    start = None
    for i in range(len(ws)):
        if all(i + k < len(ws) and ws[i + k][4].lower().strip('.,;:"()').startswith(toks[k]) for k in range(len(toks))):
            start = i
            break
    if start is None:
        raise KeyError(f"phrase {first!r} not on page {pg}")
    words = ws[start:start + count]
    lines = []
    for x0, y0, x1, y1, _ in words:
        if lines and abs(lines[-1][1] - y0) < 12:
            l0 = lines[-1]
            lines[-1] = [min(l0[0], x0), min(l0[1], y0), max(l0[2], x1), max(l0[3], y1)]
        else:
            lines.append([x0, y0, x1, y1])
    return lines


@lru_cache(maxsize=8)
def doc_card(pg, y0, y1, width):
    """A crop of a real report page, printed like a photocopy on warm paper."""
    img = cv2.imread(os.path.join(REPORT, f"p{pg:03d}.png"), cv2.IMREAD_GRAYSCALE)
    x0, x1 = 120, img.shape[1] - 110
    crop = img[int(y0):int(y1), x0:x1].astype(np.float32) / 255.0
    s = width / crop.shape[1]
    crop = cv2.resize(crop, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    ink = np.array(INK, np.float32)
    pap = np.array((250, 247, 238), np.float32)
    rgb = (ink + (pap - ink) * np.clip((crop[..., None] - 0.15) / 0.8, 0, 1)).astype(np.uint8)
    pad = 46
    out = np.zeros((rgb.shape[0] + 2 * pad, rgb.shape[1] + 2 * pad, 4), np.uint8)
    out[..., :3] = pap.astype(np.uint8)
    out[..., 3] = 255
    out[pad:pad + rgb.shape[0], pad:pad + rgb.shape[1], :3] = rgb
    out = lk.torn_card(out, seed=pg, amp=4)
    return out, s, x0, y0, pad


class Doc:
    """A report page crop with marker strokes that follow the narration."""

    def __init__(self, pg, y0, y1, width):
        self.pg, self.base = pg, doc_card(pg, y0, y1, width)
        self.marks = []          # (lines, t0, t1, seed)
        self.circles = []        # (lines, t0, seed)

    def mark(self, first, count, t0, t1):
        self.marks.append((phrase_boxes(self.pg, first, count), t0, t1, len(self.marks) + self.pg))

    def circle(self, first, count, t0):
        self.circles.append((phrase_boxes(self.pg, first, count), t0, len(self.circles) + 7))

    def to_card(self, x, y):
        _, s, x0, y0, pad = self.base
        return (x - x0) * s + pad, (y - y0) * s + pad

    def sprite(self, t):
        img = self.base[0].copy()
        for lines, t0, t1, seed in self.marks:
            total = sum(l[2] - l[0] for l in lines)
            done = total * ease_in_out(lin(t, t0, t1))
            for k, (x0, y0, x1, y1) in enumerate(lines):
                seg = x1 - x0
                u = clamp(done / seg) if seg > 0 else 0
                done -= seg
                if u <= 0:
                    break
                yc = (y0 + y1) / 2 + 3            # OCR boxes overlap the next line: use a band
                a = self.to_card(x0 - 6, yc - 15)
                b = self.to_card(x1 + 8, yc + 15)
                lk.highlight(img, a[0], a[1], b[0], b[1], u, seed=seed + k)
        for lines, t0, seed in self.circles:
            u = lin(t, t0, t0 + 0.9)
            if u <= 0:
                continue
            xs = [self.to_card(l[0], 0)[0] for l in lines] + [self.to_card(l[2], 0)[0] for l in lines]
            ys = [self.to_card(0, l[1])[1] for l in lines] + [self.to_card(0, l[3])[1] for l in lines]
            cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
            lk.circle_draw(img, cx, cy, (max(xs) - min(xs)) / 2 + 34, (max(ys) - min(ys)) / 2 + 16, u,
                           ACCENT, 6, seed)
        return img


# ------------------------------------------------------------------ scene base
class Scene:
    trans = "slide"           # how the scene enters: slide | push | up | zoom | none

    def __init__(self, spec):
        self.spec = spec
        self.D, self.S, self.key = spec["dur"], spec["sentences"], spec["key"]
        self.words = spec.get("words", [])
        self.voice, self.vend = spec.get("voice"), spec.get("voice_end", 0)
        self.sfx, self._seen = [], set()
        self.panels = []          # (x, y, draw(frame, t))
        self.setup()

    def setup(self):
        pass

    # word cues
    def cue(self, key, end=False, nth=0):
        toks = [norm(x) for x in C(key).split()]
        ws = [norm(w[0]) for w in self.words]
        hits = []
        for i in range(len(ws) - len(toks) + 1):
            ok = all((ws[i + k].startswith(toks[k]) if k == len(toks) - 1 else ws[i + k] == toks[k])
                     for k in range(len(toks)))
            if ok:
                hits.append(i)
        if len(hits) <= nth:
            raise KeyError(f"[{self.key}] cue {key!r} ({C(key)!r}) not spoken")
        i = hits[nth]
        return self.words[i + len(toks) - 1][2] if end else self.words[i][1]

    def sent_end(self, i):
        """End of sentence i (seconds, scene time)."""
        if i + 1 < len(self.S):
            return self.S[i + 1] - 0.3
        return self.vend

    def at(self, t, t0, kind, gain=1.0):
        """Fire a sound effect once, at exactly t0."""
        k = (kind, round(t0, 2))
        if t >= t0 and k not in self._seen:
            self._seen.add(k)
            self.sfx.append((round(t0, 3), kind, gain))

    # the collage canvas
    def camera(self, t):
        return (W / 2, H / 2, 1.0)

    def frame(self, t):
        cx, cy, z = self.camera(t)
        vw, vh = W / z, H / z
        vx, vy = cx - vw / 2, cy - vh / 2
        iw, ih = int(math.ceil(vw)), int(math.ceil(vh))
        out = paper_at(vx, vy, iw, ih)
        for px, py, draw in self.panels:
            ix0, iy0 = max(vx, px), max(vy, py)
            ix1, iy1 = min(vx + vw, px + W), min(vy + vh, py + H)
            if ix1 - ix0 < 2 or iy1 - iy0 < 2:
                continue
            buf = paper_at(px, py)
            draw(buf, t)
            sx0, sy0 = int(round(ix0 - px)), int(round(iy0 - py))
            dx0, dy0 = int(round(ix0 - vx)), int(round(iy0 - vy))
            ww = min(int(round(ix1 - ix0)), W - sx0, iw - dx0)
            hh = min(int(round(iy1 - iy0)), H - sy0, ih - dy0)
            if ww > 0 and hh > 0:
                out[dy0:dy0 + hh, dx0:dx0 + ww] = buf[sy0:sy0 + hh, sx0:sx0 + ww]
        if (iw, ih) != (W, H):
            out = cv2.resize(out, (W, H), interpolation=cv2.INTER_AREA if z < 1 else cv2.INTER_LINEAR)
        return out

    def pan(self, t, stops):
        """stops: [(t_start, duration, (x, y, z)), ...] in order; returns camera."""
        x, y, z = stops[0][2]
        for t0, d, (nx, ny, nz) in stops[1:]:
            u = ease_in_out(lin(t, t0, t0 + d))
            if u <= 0:
                break
            x, y = lerp(x, nx, u), lerp(y, ny, u)
            z = math.exp(lerp(math.log(z), math.log(nz), u))
            if u >= 1:
                continue
        return x, y, z

    def whooshes(self, t, stops):
        for t0, d, _ in stops[1:]:
            self.at(t, t0, "whoosh", 0.7)


def P(i, j=0):
    """Canvas position of panel (column i, row j)."""
    return i * (W + GAP), j * (H + GAP)


def center(i, j=0, z=1.0, dx=0, dy=0):
    x, y = P(i, j)
    return (x + W / 2 + dx, y + H / 2 + dy, z)


def slide_in(t, t0, dur=0.55, dist=1400):
    """Offset for a card sliding in from the right with a little settle."""
    u = lin(t, t0, t0 + dur)
    return (1 - ease_out(u)) * dist, u


def caption_chip(f, s, x, y, t, t0, size=22, anchor="lb"):
    lk.label(f, s, x, y, t, t0, size=size, name="medium", fg=lk.INK_SOFT, bg=WHITE, anchor=anchor,
             pad=(12, 8))


def headline(f, s, x, y, size, t, t0, color=INK, anchor="lt", name="black", tracking=2):
    """Headline that rises in word by word."""
    u = lin(t, t0, t0 + 0.4)
    if u <= 0:
        return 0, 0
    dy = (1 - ease_out(u)) * 26
    return lk.text(f, s, x, y + dy, name, size, color, alpha=clamp(u * 2), anchor=anchor, tracking=tracking)


def text_box(s, name, size, tracking=0):
    return lk.text_size(s, name, size, tracking)


def hot_sweep(f, x, y, w, h, t, t0, t1, seed=0):
    lk.highlight(f, x - 8, y, x + w + 8, y + h, ease_in_out(lin(t, t0, t1)), seed=seed)


# ------------------------------------------------------------------ drawings
def earth_moon(f, t, route_u, boom_u, boom_t, dist_u, labels):
    """Flat Earth-Moon diagram with Apollo 13's outbound route."""
    ex, ey, er = 380, 600, 150
    mx, my, mr = 1560, 360, 72

    def body(ov, ox, oy):
        cv2.circle(ov, (ex - ox, ey - oy), er, (58, 70, 82), -1, cv2.LINE_AA)
        for k in (-0.55, -0.15, 0.25, 0.62):
            yy = int(ey + k * er)
            half = int(math.sqrt(max(er * er - (k * er) ** 2, 0)))
            cv2.line(ov, (ex - half - ox, yy - oy), (ex + half - ox, yy - oy), (82, 96, 108), 2, cv2.LINE_AA)
        cv2.ellipse(ov, (ex - ox, ey - oy), (int(er * 0.45), er), 0, 0, 360, (82, 96, 108), 2, cv2.LINE_AA)
        cv2.circle(ov, (ex - ox, ey - oy), er, INK, 4, cv2.LINE_AA)
        cv2.circle(ov, (mx - ox, my - oy), mr, lk.PAPER_DARK, -1, cv2.LINE_AA)
        for dx, dy, r in ((-18, -12, 11), (16, 8, 8), (-4, 24, 6), (22, -20, 5)):
            cv2.circle(ov, (mx + dx - ox, my + dy - oy), r, (196, 186, 166), -1, cv2.LINE_AA)
        cv2.circle(ov, (mx - ox, my - oy), mr, INK, 4, cv2.LINE_AA)
    lk.overlay(f, 1.0, body, (ex - er - 8, my - mr - 8, mx + mr + 8, ey + er + 8))
    lk.text(f, L("earth"), ex, ey + er + 24, "black", 30, INK, anchor="ct", tracking=4)
    lk.text(f, L("moon"), mx, my + mr + 20, "black", 30, INK, anchor="ct", tracking=4)
    p0, p1 = np.array([ex + er * 0.7, ey - er * 0.72]), np.array([mx - mr - 40, my + 30])
    mid = (p0 + p1) / 2 + np.array([0, -260])
    ts = np.linspace(0, 1, 80)[:, None]
    curve = (1 - ts) ** 2 * p0 + 2 * (1 - ts) * ts * mid + ts ** 2 * p1
    maps.dashed_route(f, curve, route_u, INK, 5, 18, 12)
    bi = int(0.84 * (len(curve) - 1))
    bx, by = curve[bi]
    if boom_u > 0:
        burst(f, bx, by, t - boom_t)
        lk.pulse_marker(f, bx, by, t, boom_t, ACCENT, 15)
    if dist_u > 0:
        y = ey + er + 120
        x1 = bx
        lk.draw_path(f, [(ex, y), (ex + (x1 - ex) * ease_out(dist_u), y)], 1.0, INK, 4, 3)
        for xx in (ex, ex + (x1 - ex) * ease_out(dist_u)):
            lk.draw_path(f, [(xx, y - 16), (xx, y + 16)], 1.0, INK, 4, 4)
        lk.draw_path(f, [(x1, by + 26), (x1, y - 20)], ease_out(dist_u), INK_SOFT_(), 2, 5)
    for kind, x, y, t0 in labels:
        if kind == "boom":
            lk.label(f, L("boom"), bx - 24, by + 40, t, t0, size=32, name="black", fg=WHITE, bg=ACCENT,
                     anchor="rt")
        elif kind == "dist":
            lk.label(f, L("dist"), (ex + bx) / 2, ey + er + 150, t, t0, size=34, name="black", anchor="ct",
                     bar=YELLOW)
        elif kind == "date":
            lk.label(f, L("date_13"), x, y, t, t0, size=36, name="black", anchor="lt", bar=ACCENT)
        elif kind == "route":
            rx, ry = curve[int(0.32 * (len(curve) - 1))]
            lk.label(f, L("route"), rx - 20, ry - 26, t, t0, size=26, name="black", anchor="rb", rot=-8)
    return bx, by


def hours_text(n):
    """'8 HOURS' / Czech plural: 1 HODINA, 2-4 HODINY, 0 and 5+ HODIN."""
    if LANG == "en":
        return f"{n} HOUR" if n == 1 else f"{n} HOURS"
    word = "HODINA" if n == 1 else "HODINY" if 2 <= n <= 4 else "HODIN"
    return f"{n} {word}"


def INK_SOFT_():
    return lk.INK_SOFT


def burst(f, x, y, dt):
    """A flat cartoon explosion: accent star and rays."""
    if dt < 0:
        return
    u = clamp(dt / 0.45)
    r = 28 + 90 * ease_out(u)
    a = 1.0 if dt < 0.6 else clamp(1 - (dt - 0.6) / 0.6)
    if a <= 0:
        return

    def dr(ov, ox, oy):
        n = 12
        pts = []
        for k in range(2 * n):
            ang = k * math.pi / n + 0.2
            rr = r if k % 2 == 0 else r * 0.48
            pts.append((x + math.cos(ang) * rr - ox, y + math.sin(ang) * rr - oy))
        cv2.fillPoly(ov, [np.array(pts, np.int32)], YELLOW, cv2.LINE_AA)
        cv2.polylines(ov, [np.array(pts, np.int32)], True, ACCENT, 5, cv2.LINE_AA)
        for k in range(8):
            ang = k * math.pi / 4 + 0.4
            r0, r1 = r * 1.15, r * (1.15 + 0.5 * u)
            cv2.line(ov, (int(x + math.cos(ang) * r0 - ox), int(y + math.sin(ang) * r0 - oy)),
                     (int(x + math.cos(ang) * r1 - ox), int(y + math.sin(ang) * r1 - oy)), ACCENT, 6, cv2.LINE_AA)
    R = r * 1.8 + 10
    lk.overlay(f, a, dr, (x - R, y - R, x + R, y + R))


def tank_diagram(f, cx, cy, r, t, hot=0.0, switch_open=0.0, fan_spin=0.0, spark=0.0, fire=0.0,
                 tube_off=0.0, char=0.0):
    """Simplified cutaway of an Apollo service-module oxygen tank (illustration)."""
    tube_x0, tube_x1 = cx - 26, cx + 26
    top, bot = cy - r * 0.78, cy + r * 0.8

    def dr(ov, ox, oy):
        o = np.array([ox, oy])
        c = (int(cx - ox), int(cy - oy))
        cv2.circle(ov, c, r + 16, (232, 226, 214), -1, cv2.LINE_AA)
        cv2.circle(ov, c, r, (250, 248, 242), -1, cv2.LINE_AA)
        if fire > 0:
            rng = np.random.default_rng(7)
            flick = int(t * 18)
            for k in range(16):
                ang = rng.uniform(0, 2 * math.pi)
                rr = rng.uniform(0.15, 0.8) * r * fire
                px, py = cx - 40 + math.cos(ang) * rr * 0.55, cy + math.sin(ang) * rr * 0.75
                hgt = (40 + 70 * rng.random()) * fire * (0.85 + 0.3 * ((k * 7 + flick) % 5) / 4)
                wid = hgt * 0.45
                for col, sc in ((ACCENT, 1.0), (YELLOW, 0.55)):
                    pts = [(px - wid * sc, py), (px - wid * 0.5 * sc, py - hgt * 0.55 * sc),
                           (px + (k % 3 - 1) * 6, py - hgt * sc), (px + wid * 0.5 * sc, py - hgt * 0.5 * sc),
                           (px + wid * sc, py), (px, py + wid * 0.6 * sc)]
                    cv2.fillPoly(ov, [(np.array(pts) - o).astype(np.int32)], col, cv2.LINE_AA)
        cv2.circle(ov, c, r, INK, 6, cv2.LINE_AA)
        cv2.circle(ov, c, r + 16, INK, 3, cv2.LINE_AA)
        # neck and the wires leaving the tank
        cv2.rectangle(ov, (int(cx - 34 - ox), int(cy - r - 70 - oy)), (int(cx + 34 - ox), int(cy - r + 4 - oy)),
                      (250, 248, 242), -1)
        cv2.rectangle(ov, (int(cx - 34 - ox), int(cy - r - 70 - oy)), (int(cx + 34 - ox), int(cy - r + 4 - oy)),
                      INK, 5)
        # heater tube
        cv2.rectangle(ov, (int(tube_x0 - ox), int(top - oy)), (int(tube_x1 - ox), int(bot - oy)),
                      lk.PAPER_DARK, -1)
        cv2.rectangle(ov, (int(tube_x0 - ox), int(top - oy)), (int(tube_x1 - ox), int(bot - oy)), INK, 4)
        # heater coil: glows when hot
        col = tuple(int(lerp(a, b, clamp(hot))) for a, b in zip(INK, ACCENT))
        pts = []
        for k in range(15):
            yy = top + 60 + k * (bot - top - 120) / 14
            pts.append((cx + (-16 if k % 2 else 16) - ox, yy - oy))
        cv2.polylines(ov, [np.array(pts, np.int32)], False, col, 5, cv2.LINE_AA)
        # fans (top and bottom of the tube)
        for fy in (top + 26, bot - 26):
            for k in range(3):
                ang = fan_spin + k * 2 * math.pi / 3
                p = (int(cx + math.cos(ang) * 46 - ox), int(fy + math.sin(ang) * 14 - oy))
                cv2.line(ov, (int(cx - ox), int(fy - oy)), p, INK, 7, cv2.LINE_AA)
            cv2.circle(ov, (int(cx - ox), int(fy - oy)), 8, INK, -1, cv2.LINE_AA)
        # fan wires running up the tube (insulation chars with `char`)
        wc = tuple(int(lerp(a, b, clamp(char))) for a, b in zip((214, 120, 60), (40, 30, 26)))
        for dx in (-34, -42):
            cv2.line(ov, (int(cx + dx - ox), int(top + 26 - oy)), (int(cx + dx - ox), int(cy - r - 70 - oy)),
                     wc, 5, cv2.LINE_AA)
        # thermostatic switch box with its contact
        sx, sy = cx + 26, cy - 10
        cv2.rectangle(ov, (int(sx - ox), int(sy - 34 - oy)), (int(sx + 70 - ox), int(sy + 34 - oy)), WHITE, -1)
        cv2.rectangle(ov, (int(sx - ox), int(sy - 34 - oy)), (int(sx + 70 - ox), int(sy + 34 - oy)), INK, 4)
        cv2.circle(ov, (int(sx + 16 - ox), int(sy + 12 - oy)), 6, INK, -1, cv2.LINE_AA)
        cv2.circle(ov, (int(sx + 56 - ox), int(sy + 12 - oy)), 6, INK, -1, cv2.LINE_AA)
        ang = -math.radians(32 * clamp(switch_open))
        ex_, ey_ = sx + 16 + math.cos(ang) * 44, sy + 12 + math.sin(ang) * 44
        cv2.line(ov, (int(sx + 16 - ox), int(sy + 12 - oy)), (int(ex_ - ox), int(ey_ - oy)), INK, 6, cv2.LINE_AA)
        # the fill tube (knocked out of place in 1968)
        fx = cx - r * 0.52
        off = tube_off * 26
        cv2.line(ov, (int(fx - ox), int(cy - r * 0.62 - oy)), (int(fx + off - ox), int(cy + r * 0.5 - oy)),
                 tuple(int(lerp(a, b, clamp(tube_off))) for a, b in zip((150, 144, 134), ACCENT)), 7, cv2.LINE_AA)
        if spark > 0:
            rng = np.random.default_rng(int(t * 60))
            sx2, sy2 = cx - 38, top + 90
            for k in range(9):
                ang = rng.uniform(0, 2 * math.pi)
                ln = rng.uniform(16, 52) * spark
                cv2.line(ov, (int(sx2 - ox), int(sy2 - oy)),
                         (int(sx2 + math.cos(ang) * ln - ox), int(sy2 + math.sin(ang) * ln - oy)),
                         YELLOW if k % 2 else ACCENT, 5, cv2.LINE_AA)
    R = r + 110
    lk.overlay(f, 1.0, dr, (cx - R, cy - R - 60, cx + R, cy + R))
    return {"switch": (cx + 61, cy - 10), "heater": (cx, cy + r * 0.35), "fan": (cx, top + 26),
            "tank": (cx - r * 0.7, cy - r * 0.7), "wire": (cx - 38, top + 90), "tube": (cx - r * 0.52, cy)}


def leader(f, p_from, p_to, u, color=INK):
    lk.draw_path(f, [p_from, p_to], ease_out(u), color, 3, 9)


def clock_face(f, cx, cy, r, hours):
    def dr(ov, ox, oy):
        c = (int(cx - ox), int(cy - oy))
        cv2.circle(ov, c, r, WHITE, -1, cv2.LINE_AA)
        if hours > 0:
            cv2.ellipse(ov, c, (r - 10, r - 10), -90, 0, 360 * hours / 12, (252, 226, 120), -1, cv2.LINE_AA)
        cv2.circle(ov, c, r, INK, 7, cv2.LINE_AA)
        for k in range(12):
            a = k * math.pi / 6
            r0 = r - (26 if k % 3 == 0 else 16)
            cv2.line(ov, (int(cx + math.cos(a) * r0 - ox), int(cy + math.sin(a) * r0 - oy)),
                     (int(cx + math.cos(a) * (r - 8) - ox), int(cy + math.sin(a) * (r - 8) - oy)), INK, 4, cv2.LINE_AA)
        a = -math.pi / 2 + hours / 12 * 2 * math.pi
        cv2.line(ov, c, (int(cx + math.cos(a) * (r - 40) - ox), int(cy + math.sin(a) * (r - 40) - oy)), ACCENT, 9,
                 cv2.LINE_AA)
        a2 = -math.pi / 2 + (hours % 1) * 2 * math.pi
        cv2.line(ov, c, (int(cx + math.cos(a2) * (r - 22) - ox), int(cy + math.sin(a2) * (r - 22) - oy)), INK, 5,
                 cv2.LINE_AA)
        cv2.circle(ov, c, 12, INK, -1, cv2.LINE_AA)
    lk.overlay(f, 1.0, dr, (cx - r - 8, cy - r - 8, cx + r + 8, cy + r + 8))


def person(f, x, y, s, color, alpha=1.0):
    def dr(ov, ox, oy):
        cv2.circle(ov, (int(x - ox), int(y - 30 * s - oy)), int(13 * s), color, -1, cv2.LINE_AA)
        cv2.ellipse(ov, (int(x - ox), int(y + 8 * s - oy)), (int(20 * s), int(24 * s)), 0, 180, 360, color, -1,
                    cv2.LINE_AA)
    lk.overlay(f, alpha, dr, (x - 30 * s, y - 50 * s, x + 30 * s, y + 12 * s))


def meter(f, cx, cy, r, value, t):
    """Flat analogue ammeter (illustration)."""
    def dr(ov, ox, oy):
        c = (int(cx - ox), int(cy - oy))
        cv2.rectangle(ov, (int(cx - r - 30 - ox), int(cy - r - 40 - oy)), (int(cx + r + 30 - ox), int(cy + 80 - oy)),
                      WHITE, -1)
        cv2.rectangle(ov, (int(cx - r - 30 - ox), int(cy - r - 40 - oy)), (int(cx + r + 30 - ox), int(cy + 80 - oy)),
                      INK, 6)
        cv2.ellipse(ov, c, (r, r), 0, 200, 340, INK, 4, cv2.LINE_AA)
        cv2.ellipse(ov, c, (r - 6, r - 6), 0, 300, 340, (250, 214, 120), 12, cv2.LINE_AA)
        for k in range(9):
            a = math.radians(200 + k * 140 / 8)
            cv2.line(ov, (int(cx + math.cos(a) * (r - 20) - ox), int(cy + math.sin(a) * (r - 20) - oy)),
                     (int(cx + math.cos(a) * r - ox), int(cy + math.sin(a) * r - oy)), INK, 4, cv2.LINE_AA)
        a = math.radians(200 + 140 * value)
        cv2.line(ov, c, (int(cx + math.cos(a) * (r - 12) - ox), int(cy + math.sin(a) * (r - 12) - oy)), ACCENT, 7,
                 cv2.LINE_AA)
        cv2.circle(ov, c, 14, INK, -1, cv2.LINE_AA)
    lk.overlay(f, 1.0, dr, (cx - r - 40, cy - r - 50, cx + r + 40, cy + 90))
    lk.text(f, "A", cx, cy + 40, "black", 34, INK, anchor="cm")


# ================================================================== 1. hook
class Hook(Scene):
    trans = "none"

    def setup(self):
        c = self.cue
        self.t_know, self.t_space, self.t_how = c("know") - 0.25, c("space") - 0.35, c("how") - 0.35
        self.stops = [(0, 0, center(0, 0, 1.0)),
                      (self.t_know, 0.85, center(1, 0, 1.0)),
                      (self.t_space, 0.85, center(2, 0, 1.0)),
                      (self.t_how, 0.8, center(2, 1, 1.0))]
        self.panels = [(*P(0, 0), self.p_map), (*P(1, 0), self.p_quote), (*P(2, 0), self.p_ground),
                       (*P(2, 1), self.p_question)]
        # the quote's hot words follow the spoken words
        self.q_words = [w for w in self.words if c("houston") - 0.05 <= w[1] <= self.sent_end(2) + 0.2]

    def camera(self, t):
        x, y, z = self.pan(t, self.stops)
        if t < self.t_know:
            z *= 1 + 0.035 * lin(t, 0, self.t_know)
        return x, y, z

    def p_map(self, f, t):
        c = self.cue
        tb, tm = c("blew"), c("miles")
        self.at(t, tb, "boom_soft", 0.7)
        self.at(t, tm, "pop")
        self.at(t, c("april"), "pop", 0.6)
        earth_moon(f, t, route_u=ease_in_out(lin(t, 0.3, tb)), boom_u=lin(t, tb, tb + 0.3), boom_t=tb,
                   dist_u=lin(t, tm, tm + 0.7),
                   labels=[("date", 120, 120, c("april")), ("boom", 0, 0, tb + 0.15), ("dist", 0, 0, tm + 0.3),
                           ("route", 760, 300, 0.9)])
        lk.text(f, L("map_note"), W - 60, H - 50, "medium", 22, lk.INK_SOFT, anchor="rb")

    def p_quote(self, f, t):
        t0 = self.t_know - 0.2
        dx, u = slide_in(t, t0, 0.6, 900)
        self.at(t, t0, "paper", 0.6)
        mcc = card("S70-34902", 560, L("mcc_cap"))
        lk.place(f, mcc, 520 - dx * 0.4, 560, 1.0, -4 + 2 * (1 - u), alpha=clamp(u * 2))
        # the quote, typeset in serif, highlighted word by word as it is spoken
        size = 88
        lines = lk.wrap(L("quote"), "serif", size, 880)
        x0, y0 = 1000, 300
        hot = set(L("quote_hot").split())
        qw = list(self.q_words)
        k = 0
        for li, ln in enumerate(lines):
            x = x0
            for wd in ln.split():
                ww, hh = lk.text_size(wd + " ", "serif", size)
                tw = qw[min(k, len(qw) - 1)] if qw else None
                if wd in hot and tw:
                    hot_sweep(f, x, y0 + li * 112 + 10, lk.text_size(wd, "serif", size)[0], hh - 22, t,
                              tw[1], tw[2] + 0.05, seed=k)
                    if t >= tw[1]:
                        self.at(t, tw[1], "marker", 0.35)
                x += ww
                k += 1
        for li, ln in enumerate(lines):
            uu = lin(t, self.cue("houston") - 0.25 + li * 0.15, self.cue("houston") + 0.2 + li * 0.15)
            lk.text(f, ln, x0, y0 + li * 112 + (1 - ease_out(uu)) * 20, "serif", size, INK, alpha=uu)
        ua = lin(t, self.cue("problem"), self.cue("problem") + 0.4)
        lk.text(f, "— " + L("quote_attr"), x0, y0 + len(lines) * 112 + 26, "serif_italic", 30, lk.INK_SOFT,
                alpha=ua)

    def p_ground(self, f, t):
        c = self.cue
        t0 = self.t_space
        dx, u = slide_in(t, t0, 0.65, 1000)
        self.at(t, t0 + 0.1, "paper", 0.6)
        pad = card("S70-32990", 820, L("pad_cap"), crop=(0.0, 0.03, 1.0, 0.97), cap_size=19)
        lk.place(f, pad, 470 + dx * 0.3, 545, 1.0, 3, alpha=clamp(u * 2))
        lines = lk.wrap(L("ground"), "black", 86, 860, 2)
        tg = c("ground")
        for li, ln in enumerate(lines):
            tw, th = lk.text_size(ln, "black", 86, 2)
            if li == len(lines) - 1:
                hot_sweep(f, 960, 150 + li * 104 + 14, tw - 8, th - 34, t, tg, tg + 0.6, seed=3)
            headline(f, ln, 960, 150 + li * 104, 86, t, tg - 0.15 + li * 0.12)
        self.at(t, tg, "marker", 0.4)
        lk.label(f, L("two_weeks"), 968, 470, t, c("two_weeks"), size=34, name="black", bar=ACCENT, anchor="lt")
        self.at(t, c("two_weeks"), "pop")
        ts = c("tiny") - 0.2
        dx2, u2 = slide_in(t, ts, 0.5, 900)
        self.at(t, ts, "paper", 0.5)
        sw = card("S70-40850", 380, crop=(0.08, 0.05, 0.92, 0.95))
        lk.place(f, sw, 1420 + dx2, 760, 1.0, -6, alpha=clamp(u2 * 2))
        if t > c("28v"):
            lk.circle_draw(f, 1395, 690, 150, 70, lin(t, c("28v"), c("28v") + 0.7), ACCENT, 7, 2)
        self.at(t, c("28v"), "pen", 0.5)
        lk.label(f, L("rated28"), 1180, 1000, t, c("28v") + 0.2, size=32, name="black", fg=WHITE, bg=INK,
                 anchor="lb")

    def p_question(self, f, t):
        c = self.cue
        lines = L("q")
        keys = ["how", "small", "kill", "three"]
        y = 200
        size = 88
        for li, (ln, k) in enumerate(zip(lines, keys)):
            t0 = c(k) - 0.1
            tw, th = lk.text_size(ln, "black", size, 2)
            if li == 1:
                hot_sweep(f, 120, y + 16, tw - 6, th - 36, t, c("small"), c("small", end=True) + 0.25, seed=5)
                self.at(t, c("small"), "marker", 0.4)
            headline(f, ln, 120, y, size, t, t0)
            y += 112
        td = c("three") - 0.4
        dx, u = slide_in(t, td, 0.6, 900)
        self.at(t, td, "paper", 0.5)
        crew = card("108-KSC-70PC-105", 640, L("crew_cap"), crop=(0.0, 0.1, 1.0, 0.95), cap_size=18)
        lk.place(f, crew, 1610 + dx, 560, 1.0, 4, alpha=clamp(u * 2))


# ================================================================== 2. title
class Title(Scene):
    trans = "slide"

    def setup(self):
        self.panels = [(*P(0, 0), self.draw)]

    def draw(self, f, t):
        dx, u = slide_in(t, 0.0, 0.8, 700)
        launch = card("S70-34852", 980, crop=(0.0, 0.0, 1.0, 0.96))
        lk.place(f, launch, 1660 + dx - t * 14, 560, 1.0, 5, alpha=clamp(u * 2))
        self.at(t, 0.05, "whoosh", 0.6)
        size = 150
        hot = L("title_hot")
        y = 250
        for li, ln in enumerate((L("title1"), L("title2"))):
            tw, th = lk.text_size(ln, "black", size, 3)
            if hot in ln:
                pre = ln[:ln.index(hot)]
                px = lk.text_size(pre, "black", size, 3)[0] - (16 if pre else 0)
                hw = lk.text_size(hot, "black", size, 3)[0]
                hot_sweep(f, 130 + px, y + 30, hw - 10, th - 60, t, 0.55, 1.15, seed=11)
            headline(f, ln, 130, y, size, t, 0.15 + li * 0.18, tracking=3)
            y += 170
        self.at(t, 0.55, "marker", 0.5)
        uu = lin(t, 0.7, 1.1)
        lk.text(f, L("title_sub"), 138, y + 30, "medium", 44, lk.INK_SOFT, alpha=uu)


# ================================================================== 3. switch
class Switch(Scene):
    trans = "slide"

    def setup(self):
        self.panels = [(*P(0, 0), self.draw)]

    def camera(self, t):
        return center(0, 0, 1.0 + 0.03 * lin(t, 0, self.D))

    def draw(self, f, t):
        c = self.cue
        tk, th, tc = c("tank2"), c("heater"), c("click")
        t80 = c("80f")
        opened = lin(t, tc, tc + 0.25)
        self.at(t, tc, "click", 0.9)
        hot = 1.0 - opened if t > 0.4 else lin(t, 0, 0.4)
        p = tank_diagram(f, 640, 580, 330, t, hot=hot, switch_open=opened, fan_spin=t * 2.4)
        # labels with leader lines
        tsw = self.S[0] - 0.05
        leader(f, (p["switch"][0] + 60, p["switch"][1] - 30), (1000, 250), lin(t, tsw, tsw + 0.4))
        lk.label(f, L("tswitch"), 980, 250, t, tsw + 0.3, size=34, name="black", fg=WHITE, bg=INK, anchor="lb")
        self.at(t, tsw + 0.3, "pop")
        if t > tsw:
            lk.circle_draw(f, p["switch"][0], p["switch"][1], 62, 50, lin(t, tsw, tsw + 0.6), ACCENT, 6, 4)
        leader(f, (p["heater"][0] - 30, p["heater"][1]), (200, 880), lin(t, th, th + 0.4))
        lk.label(f, L("heater"), 200, 880, t, th + 0.25, size=30, name="black", anchor="lt")
        self.at(t, th + 0.25, "pop", 0.7)
        leader(f, p["tank"], (170, 180), lin(t, tk, tk + 0.4))
        lk.label(f, L("tank"), 170, 180, t, tk + 0.25, size=30, name="black", anchor="lb", bar=ACCENT)
        self.at(t, tk + 0.25, "pop", 0.7)
        lk.text(f, L("diagram"), 70, H - 50, "serif_italic", 24, lk.INK_SOFT, anchor="lb")
        # thermometer
        gx, gy0, gy1 = 1640, 300, 840
        level = ease_in_out(lin(t, t80 - 1.2, t80 + 0.1)) * 0.62
        limit_y = gy1 - 0.62 * (gy1 - gy0)

        def therm(ov, ox, oy):
            cv2.rectangle(ov, (gx - 34 - ox, gy0 - oy), (gx + 34 - ox, gy1 - oy), WHITE, -1)
            cv2.rectangle(ov, (gx - 34 - ox, gy0 - oy), (gx + 34 - ox, gy1 - oy), INK, 5)
            cv2.circle(ov, (gx - ox, gy1 + 40 - oy), 58, ACCENT, -1, cv2.LINE_AA)
            cv2.circle(ov, (gx - ox, gy1 + 40 - oy), 58, INK, 5, cv2.LINE_AA)
            top_y = int(gy1 - level * (gy1 - gy0))
            cv2.rectangle(ov, (gx - 16 - ox, top_y - oy), (gx + 16 - ox, gy1 + 10 - oy), ACCENT, -1)
            for k in range(11):
                yy = int(gy1 - k * (gy1 - gy0) / 10)
                cv2.line(ov, (gx + 34 - ox, yy - oy), (gx + (56 if k % 5 == 0 else 46) - ox, yy - oy), INK, 4)
        lk.overlay(f, 1.0, therm, (gx - 70, gy0 - 10, gx + 80, gy1 + 110))
        if t > t80 - 0.2:
            lk.draw_path(f, [(gx - 70, limit_y), (gx + 120, limit_y)], lin(t, t80 - 0.2, t80 + 0.2), INK, 4, 6)
        lk.label(f, L("limit"), gx - 90, limit_y, t, t80, size=48, name="black", anchor="rm", bar=YELLOW)
        self.at(t, t80, "pop")
        lk.label(f, L("opens"), gx - 90, limit_y + 70, t, tc + 0.1, size=30, name="black", fg=WHITE, bg=ACCENT,
                 anchor="rt")


# ================================================================== 4. volts
class Volts(Scene):
    trans = "push"

    def setup(self):
        c = self.cue
        self.t_doc = c("upgraded") - 0.5
        self.stops = [(0, 0, center(0, 0)), (self.t_doc, 0.8, center(1, 0, 1.0))]
        self.panels = [(*P(0, 0), self.chart), (*P(1, 0), self.doc)]
        pg = 175
        self.d = Doc(pg, 1150, 1800, 1500)
        self.d.mark("did not change the switch", 13, c("upgraded"), c("upgraded") + 1.6)
        self.d.mark("serious oversight", 7, c("caught"), c("caught") + 1.2)

    def camera(self, t):
        x, y, z = self.pan(t, self.stops)
        if t > self.t_doc:
            z *= 1 + 0.06 * lin(t, self.t_doc + 0.8, self.D)
        return x, y, z

    def chart(self, f, t):
        c = self.cue
        lk.text(f, L("power"), 150, 120, "black", 52, INK, tracking=3)
        lk.underline(f, 150, 150 + lk.text_size(L("power"), "black", 52, 3)[0], 196, lin(t, 0.2, 0.8), YELLOW, 10, 1)
        base, ppv = 900, 8.4
        bars = [(c("design28") - 0.15, 28, 470, INK, L("bar1"), L("bar1_sub")),
                (c("65") - 0.35, 65, 900, ACCENT, L("bar2"), L("bar2_sub"))]
        for t0, v, x, col, lab, sub in bars:
            u = ease_out(lin(t, t0, t0 + 0.8))
            hgt = v * ppv * u
            lk.fill_rect(f, x, base - hgt, x + 250, base, col)
            if u > 0:
                self.at(t, t0, "rise", 0.6)
                lk.text(f, f"{int(round(v * u))} V", x + 125, base - hgt - 14, "black", 84, col, anchor="cb")
            ua = lin(t, t0, t0 + 0.3)
            lk.text(f, lab, x + 125, base + 22, "black", 32, INK, alpha=ua, anchor="ct", tracking=2)
            lk.text(f, sub, x + 125, base + 66, "medium", 26, lk.INK_SOFT, alpha=ua, anchor="ct")
        lk.draw_path(f, [(400, base), (1230, base)], lin(t, 0.0, 0.4), INK, 5, 2)
        # the switches' rating stays at 28 V
        t2 = c("65") + 0.9
        y28 = base - 28 * ppv
        if t > t2:
            u = lin(t, t2, t2 + 0.6)
            xx = 400 + 880 * u
            x = 400
            while x < xx:
                lk.fill_rect(f, x, y28 - 3, min(x + 26, xx), y28 + 3, INK)
                x += 40
        lk.label(f, L("switch_rated"), 1250, y28, t, t2 + 0.4, size=30, name="black", fg=WHITE, bg=INK, anchor="lm")
        self.at(t, t2 + 0.4, "pop")
        ta = c("65") + 0.5
        if t > ta:
            lk.arrow_draw(f, (760, base - 28 * ppv - 120), (880, base - 65 * ppv + 40), lin(t, ta, ta + 0.6),
                          ACCENT, 6, 3)
            self.at(t, ta, "pen", 0.4)
        lk.label(f, L("times"), 640, base - 28 * ppv - 140, t, ta + 0.4, size=46, name="black", bg=YELLOW, anchor="lb")

    def doc(self, f, t):
        u = lin(t, self.t_doc - 0.2, self.t_doc + 0.5)
        spr = self.d.sprite(t)
        lk.place(f, spr, W / 2 + (1 - ease_out(u)) * 200, H / 2 - 40, 1.0, -1.2, alpha=1.0)
        for _, t0, _, _ in self.d.marks:
            self.at(t, t0, "marker", 0.45)
        lk.label(f, L("doc_label"), 150, 110, t, self.t_doc + 0.3, size=24, name="black", fg=WHITE, bg=INK)
        lk.label(f, L("mistake1"), 150, 170, t, self.d.marks[0][1], size=34, name="black", fg=WHITE, bg=ACCENT)
        lk.text(f, L("doc_src_52"), W - 120, H - 46, "medium", 22, lk.INK_SOFT, anchor="rb",
                alpha=lin(t, self.t_doc + 0.4, self.t_doc + 0.8))
        if LANG == "cs":
            for key, t0 in (("tr_nochange", self.d.marks[0][1]), ("tr_oversight", self.d.marks[1][1])):
                if t >= t0 and (key == "tr_oversight" or t < self.d.marks[1][1]):
                    lk.label(f, L(key), W / 2, H - 120, t, t0 + 0.2, size=34, name="serif_italic", anchor="cb",
                             bar=YELLOW)


# ================================================================== 5. drop (US map)
class USMap:
    _base = None

    @classmethod
    def base(cls):
        if cls._base is None:
            cls._base = maps.BaseMap("us", -128, -64, 22, 52, 90, states=True)
        return cls._base


BOULDER = (40.015, -105.27)
DOWNEY = (33.94, -118.13)
KSC = (28.573, -80.649)
WIDE_US = (37.5, -96.5, 0.30)


def us_frame(f, view, t):
    view.draw(f)
    fade = clamp(1 - (view.s - 0.34) / 0.25)                 # ocean names only on the wide view
    for key, lat, lon, size in (("pacific", 30.5, -124.5, 30), ("atlantic", 32.0, -70.5, 30)):
        x, y = view.pt(lat, lon)
        lk.text(f, L(key), x, y, "semi", size, lk.INK_SOFT, anchor="cm", tracking=6, alpha=fade)


class Drop(Scene):
    trans = "slide"

    def setup(self):
        self.panels = [(*P(0, 0), self.draw)]

    def view(self, t):
        b = USMap.base()
        c = self.cue
        zt = c("dropped") - 0.2
        zin = (DOWNEY[0] + 0.4, DOWNEY[1] + 6.2, 1.15)
        if t < zt:
            return maps.MapView(b, *WIDE_US)
        if t < self.vend - 0.6:
            return maps.lerp_view(b, WIDE_US, zin, lin(t, zt, zt + 1.1))
        return maps.lerp_view(b, zin, WIDE_US, lin(t, self.vend - 0.6, self.D))

    def draw(self, f, t):
        c = self.cue
        v = self.view(t)
        us_frame(f, v, t)
        tcal = c("california")
        route = maps.route_points(v, BOULDER, DOWNEY, bend=-0.25)
        maps.dashed_route(f, route, ease_in_out(lin(t, 0.4, tcal + 0.1)), ACCENT, 6)
        self.at(t, 0.4, "pen", 0.3)
        bx, by = v.pt(*BOULDER)
        lk.pulse_marker(f, bx, by, t, 0.2, INK, 11)
        lk.label(f, L("boulder"), bx + 24, by - 20, t, 0.3, size=26, name="black", anchor="lb")
        lk.label(f, L("boulder_sub"), bx + 24, by - 20 + 4, t, 0.45, size=22, name="medium", anchor="lt")
        dx, dy = v.pt(*DOWNEY)
        lk.pulse_marker(f, dx, dy, t, tcal, ACCENT, 14)
        self.at(t, tcal, "pop")
        lk.label(f, L("downey"), dx + 26, dy - 26, t, tcal + 0.1, size=28, name="black", anchor="lb", bar=ACCENT)
        lk.label(f, L("downey_sub"), dx + 26, dy - 22, t, tcal + 0.25, size=22, name="medium", anchor="lt")
        lk.label(f, L("mistake2"), 120, 110, t, c("second"), size=34, name="black", fg=WHITE, bg=ACCENT)
        self.at(t, c("second"), "pop")
        lk.label(f, L("date_drop"), 120, 190, t, c("y1968"), size=40, name="black", bar=YELLOW)
        self.at(t, c("y1968"), "pop", 0.7)
        # the drop: an inset of the tank shelf falling ~2 inches
        ti = c("dropped")
        if t > ti - 0.1 and t < self.vend - 0.4:
            a = lin(t, ti - 0.1, ti + 0.3) * (1 - lin(t, self.vend - 0.7, self.vend - 0.4))
            fall = ease_out(lin(t, ti + 0.25, ti + 0.45))
            sx, sy = 1300, 520

            def inset(ov, ox, oy):
                cv2.rectangle(ov, (sx - 360 - ox, sy - 300 - oy), (sx + 360 - ox, sy + 300 - oy), WHITE, -1)
                cv2.rectangle(ov, (sx - 360 - ox, sy - 300 - oy), (sx + 360 - ox, sy + 300 - oy), INK, 5)
                yy = int(sy + 40 + fall * 46)
                cv2.rectangle(ov, (sx - 250 - ox, yy - oy), (sx + 250 - ox, yy + 22 - oy), INK, -1)
                cv2.circle(ov, (sx - 90 - ox, yy - 92 - oy), 90, (250, 248, 242), -1, cv2.LINE_AA)
                cv2.circle(ov, (sx - 90 - ox, yy - 92 - oy), 90, INK, 6, cv2.LINE_AA)
                cv2.circle(ov, (sx + 110 - ox, yy - 70 - oy), 68, (250, 248, 242), -1, cv2.LINE_AA)
                cv2.circle(ov, (sx + 110 - ox, yy - 70 - oy), 68, INK, 6, cv2.LINE_AA)
                cv2.line(ov, (sx - 300 - ox, sy + 40 - oy), (sx + 300 - ox, sy + 40 - oy), (200, 190, 170), 3)
            lk.overlay(f, a, inset, (sx - 370, sy - 310, sx + 370, sy + 310))
            if fall > 0:
                self.at(t, ti + 0.25, "thud", 0.8)
                lk.arrow_draw(f, (sx + 290, sy - 30), (sx + 290, sy + 110), lin(t, ti + 0.3, ti + 0.8), ACCENT, 6, 8,
                              bend=0.0)
            lk.label(f, L("drop_amt"), sx, sy + 260, t, c("inches"), size=34, name="black", fg=WHITE, bg=ACCENT,
                     anchor="cm")
            self.at(t, c("inches"), "pop")
        tt = c("tube")
        if t > tt - 0.3:
            a = lin(t, tt - 0.3, tt + 0.1)

            def inset2(ov, ox, oy):
                cv2.rectangle(ov, (980 - ox, 140 - oy), (1830 - ox, 760 - oy), WHITE, -1)
                cv2.rectangle(ov, (980 - ox, 140 - oy), (1830 - ox, 760 - oy), INK, 5)
            lk.overlay(f, a, inset2, (970, 130, 1840, 770))
            if a > 0.9:
                tank_diagram(f, 1405, 470, 230, t, hot=0, tube_off=lin(t, tt, tt + 0.5))
            lk.label(f, L("tube"), 1405, 800, t, tt + 0.3, size=26, name="black", fg=WHITE, bg=ACCENT, anchor="ct")
            self.at(t, tt + 0.3, "pop")


# ================================================================== 6. detank
class Detank(Scene):
    trans = "none"         # continues the map

    def setup(self):
        c = self.cue
        self.t_pan = c("improvised") - 0.4
        self.stops = [(0, 0, center(0, 0)), (self.t_pan, 0.8, center(1, 0))]
        self.panels = [(*P(0, 0), self.map), (*P(1, 0), self.clock)]
        self.clip = Clip("firing_room")

    def camera(self, t):
        return self.pan(t, self.stops)

    def map(self, f, t):
        c = self.cue
        b = USMap.base()
        tk = c("kennedy")
        zin = (KSC[0] + 1.0, KSC[1] - 3.5, 0.75)
        v = maps.lerp_view(b, WIDE_US, zin, lin(t, tk - 0.2, tk + 1.2))
        us_frame(f, v, t)
        maps.dashed_route(f, maps.route_points(v, BOULDER, DOWNEY, bend=-0.25), 1.0, ACCENT, 6)
        maps.dashed_route(f, maps.route_points(v, DOWNEY, KSC, bend=-0.12), ease_in_out(lin(t, 0.0, tk)), ACCENT, 6)
        for pt in (BOULDER, DOWNEY):
            x, y = v.pt(*pt)
            lk.pulse_marker(f, x, y, t, -2, INK if pt == BOULDER else ACCENT, 11)
        kx, ky = v.pt(*KSC)
        lk.pulse_marker(f, kx, ky, t, tk, ACCENT, 15)
        self.at(t, tk, "pop")
        lk.label(f, L("ksc"), kx - 30, ky - 30, t, tk + 0.1, size=30, name="black", anchor="rb", bar=ACCENT)
        lk.label(f, L("date_detank"), kx - 30, ky + 6, t, tk + 0.35, size=34, name="black", anchor="rt", bg=YELLOW)
        self.at(t, tk + 0.35, "pop", 0.7)
        lk.label(f, L("wont_empty"), 120, 120, t, c("empty"), size=40, name="black", fg=WHITE, bg=INK)
        self.at(t, c("empty"), "pop")

    def clock(self, f, t):
        c = self.cue
        tr, te = c("running"), c("eight", end=True)
        img = self.clip.at(max(t - self.t_pan + 1.0, 0))
        if img is not None:
            vc = video_card(img, 470, L("firing_cap"))
            lk.place(f, vc, 520, 560, 1.0, -3)
        hours = 8 * ease_in_out(lin(t, tr, te + 0.4))
        clock_face(f, 1330, 520, 250, hours)
        if t > tr:
            self.at(t, tr, "tick_run", 0.5)
        lk.text(f, hours_text(int(hours + 0.5)), 1330, 840, "black", 80, INK, anchor="ct")
        lk.label(f, L("heaters_on"), 1330, 190, t, tr - 0.1, size=34, name="black", fg=WHITE, bg=ACCENT, anchor="cb")
        self.at(t, tr - 0.1, "pop")


# ================================================================== 7. weld
class Weld(Scene):
    trans = "slide"

    def setup(self):
        c = self.cue
        self.t_chart = c("1000") - 0.7
        self.t_launch = c("noticed") - 0.35
        self.stops = [(0, 0, center(0, 0)), (self.t_chart, 0.8, center(1, 0)), (self.t_launch, 0.7, center(1, 1))]
        self.panels = [(*P(0, 0), self.switch), (*P(1, 0), self.chart), (*P(1, 1), self.launch)]
        self.clip = Clip("liftoff")

    def camera(self, t):
        return self.pan(t, self.stops)

    def switch(self, f, t):
        c = self.cue
        tw = c("welded")
        sw = card("S70-40850", 760, L("fused_cap"), crop=(0.02, 0.0, 0.98, 1.0), cap_size=20)
        lk.place(f, sw, 760 + t * 6, 530, 1.0 + 0.02 * t / self.D, -3)
        if t > tw:
            lk.circle_draw(f, 740, 330, 330, 120, lin(t, tw, tw + 0.7), ACCENT, 8, 6)
        self.at(t, tw, "pen", 0.5)
        lk.stamp(f, L("welded"), 1520, 330, t, c("welded") + 0.15)
        self.at(t, c("welded") + 0.15, "stamp", 0.9)

    def chart(self, f, t):
        c = self.cue
        t1 = c("1000")
        x0, y0, x1, y1 = 260, 220, 1500, 860
        lk.text(f, L("temp_title"), x0, 110, "black", 40, INK, tracking=2)
        lk.draw_path(f, [(x0, y0 - 20), (x0, y1), (x1 + 40, y1)], lin(t, self.t_chart, self.t_chart + 0.5), INK, 5, 3)
        for k in range(9):
            xx = x0 + k * (x1 - x0) / 8
            lk.text(f, str(k), xx, y1 + 16, "semi", 26, lk.INK_SOFT, anchor="ct",
                    alpha=lin(t, self.t_chart + 0.3, self.t_chart + 0.6))
        lk.text(f, L("temp_axis"), (x0 + x1) / 2, y1 + 60, "bold", 26, lk.INK_SOFT, anchor="ct",
                alpha=lin(t, self.t_chart + 0.3, self.t_chart + 0.6))
        vmax = 1100.0
        ly = y1 - 80 / vmax * (y1 - y0)
        xx, x = x0 + (x1 - x0) * lin(t, self.t_chart + 0.3, self.t_chart + 0.9), x0
        while x < xx:
            lk.fill_rect(f, x, ly - 2, min(x + 22, xx), ly + 2, INK)
            x += 34
        lk.label(f, L("temp_limit"), x1 + 10, ly, t, self.t_chart + 0.7, size=28, name="black", anchor="lm",
                 bg=YELLOW)
        # schematic curve: up past the limit within the first hours, then held near the estimate
        us = np.linspace(0, 1, 160)
        temps = 40 + 960 * (1 - np.exp(-us * 4.2))
        xs = x0 + us * (x1 - x0)
        ys = y1 - temps / vmax * (y1 - y0)
        u = ease_in_out(lin(t, t1 - 0.45, t1 + 1.1))
        if u > 0:
            n = max(2, int(len(us) * u))
            lk.draw_path(f, list(zip(xs[:n], ys[:n])), 1.0, ACCENT, 8, 1)
            self.at(t, t1 - 0.45, "rise", 0.7)
        py = y1 - 1000 / vmax * (y1 - y0)
        lk.label(f, L("temp_peak"), x1 - 60, py - 30, t, t1 + 0.9, size=54, name="black", fg=WHITE, bg=ACCENT,
                 anchor="rb")
        self.at(t, t1 + 0.9, "pop")
        ti = c("insulation")
        lk.label(f, L("insul"), x1 - 20, ly - 60, t, ti, size=30, name="black", fg=WHITE, bg=INK, anchor="rb")
        self.at(t, ti, "pop", 0.7)
        lk.text(f, L("chart_note"), x0, H - 40, "serif_italic", 22, lk.INK_SOFT, anchor="lb",
                alpha=lin(t, self.t_chart + 0.5, self.t_chart + 1.0))

    def launch(self, f, t):
        c = self.cue
        tn, tf = c("noticed"), c("flew")
        clip_t = 33.0 + max(t - self.t_launch, 0)
        img = self.clip.at(clip_t)
        if img is not None:
            vc = video_card(img, 700, L("launch_cap"))
            lk.place(f, vc, W / 2 + 200, 560, 1.0 + 0.03 * lin(t, tf, self.D), -2)
        if t > tf:
            self.at(t, tf, "rumble", 0.6)
        lk.stamp(f, L("nobody"), 470, 190, t, tn, size=56, color=INK, rot=-9)
        self.at(t, tn, "stamp", 0.6)


# ================================================================== 8. blast
class Blast(Scene):
    trans = "slide"

    def setup(self):
        c = self.cue
        self.t_diag = c("2.7") - 0.4
        self.t_photo = c("blast") + 0.25
        self.stops = [(0, 0, center(0, 0)), (self.t_diag, 0.7, center(1, 0)),
                      (self.t_photo, 0.35, center(2, 0))]
        self.panels = [(*P(0, 0), self.mcc), (*P(1, 0), self.diagram), (*P(2, 0), self.photo)]

    def camera(self, t):
        x, y, z = self.pan(t, self.stops)
        tb = self.cue("blast")
        if tb - 0.05 < t < tb + 0.4:                      # the jolt
            k = (1 - lin(t, tb, tb + 0.4)) * 14
            x += math.sin(t * 90) * k
            y += math.cos(t * 77) * k
        return x, y, z

    def mcc(self, f, t):
        c = self.cue
        m = card("S70-34902", 620, L("mcc2_cap"))
        lk.place(f, m, 600 + t * 8, 560, 1.0, -3)
        # mission clock
        ts = c("stir")
        secs = 55 * 3600 + 52 * 60 + 40 + min(t, ts) * (18 / max(ts, 0.1))
        if t > ts:
            secs = 55 * 3600 + 52 * 60 + 58 + 22 * ease_in_out(lin(t, ts + 0.6, self.t_diag + 0.3))
        hh, mm, ss = int(secs // 3600), int(secs % 3600 // 60), int(secs % 60)
        lk.text(f, L("met"), 1180, 300, "black", 30, lk.INK_SOFT, tracking=4)
        lk.text(f, f"{hh:02d}:{mm:02d}:{ss:02d}", 1170, 340, "black", 120, INK, tracking=2)
        self.at(t, 0.3, "tick_run", 0.3)
        lk.label(f, L("stir"), 1180, 560, t, ts, size=44, name="black", bg=YELLOW, anchor="lt")
        self.at(t, ts, "pop")

    def diagram(self, f, t):
        c = self.cue
        tf, tsh, tfi, tb = c("fans"), c("shorted"), c("fire"), c("blast")
        spin = t * (2 + 10 * lin(t, tf - 0.4, tf))
        tank_diagram(f, 760, 560, 330, t, hot=0.3, switch_open=0.0, fan_spin=spin,
                     spark=lin(t, tsh, tsh + 0.1) * (1 if t < tfi + 0.3 else 0.6),
                     fire=ease_out(lin(t, tfi, tb + 0.2)), char=1.0)
        cnt = 2.7 * ease_in_out(lin(t, c("2.7"), tsh))
        lk.text(f, "+" + num(cnt, 1) + " s", 1250, 250, "black", 110, ACCENT if t > tsh else INK)
        self.at(t, tsh, "spark", 0.8)
        lk.label(f, L("short"), 1250, 470, t, tsh, size=40, name="black", fg=WHITE, bg=ACCENT, anchor="lt")
        lk.label(f, L("fire"), 1250, 560, t, tfi, size=40, name="black", bg=YELLOW, anchor="lt")
        self.at(t, tfi, "whoomp", 0.7)
        if tb - 0.05 < t:
            a = 1 - lin(t, tb, tb + 0.35)
            lk.fill_rect(f, 0, 0, W, H, (255, 250, 236), a)
        self.at(t, tb, "boom", 1.0)

    def photo(self, f, t):
        c = self.cue
        tp = c("panel")
        img = card("7010516", 820, L("sm_cap"), crop=(0.08, 0.0, 0.92, 1.0), cap_size=20)
        z = 1.0 + 0.05 * lin(t, self.t_photo, self.D)
        cx, cy = W / 2 + 20, 520
        lk.place(f, img, cx, cy, z, 2)
        ih, iw = img.shape[:2]
        # damaged bay, in photo coords (crop-adjusted), then rotate 2 degrees with the card
        u0, v0 = (0.58 - 0.08) / 0.84, 0.62
        px = cx + (u0 - 0.5) * (iw - 28) * z
        py = cy + (v0 - 0.5) * (ih - 60) * z - 10
        if t > tp - 0.1:
            lk.circle_draw(f, px, py, 230 * z, 150 * z, lin(t, tp - 0.1, tp + 0.6), ACCENT, 8, 9)
            lk.arrow_draw(f, (px + 300, py - 290), (px + 160, py - 140), lin(t, tp + 0.3, tp + 0.9), ACCENT, 7, 2)
        self.at(t, tp - 0.1, "pen", 0.6)
        lk.label(f, L("panel"), px + 140, py - 300, t, tp + 0.6, size=40, name="black", fg=WHITE, bg=ACCENT,
                 anchor="lb")
        self.at(t, tp + 0.6, "pop")


# ================================================================== 9. lifeboat
class PacMap:
    _base = None

    @classmethod
    def base(cls):
        if cls._base is None:
            cls._base = maps.BaseMap("pac", 110, 230, -50, 5, 56, shift360=True)
        return cls._base


SPLASH = (-21.667, -165.367)


class Lifeboat(Scene):
    trans = "slide"

    def setup(self):
        self.t_map = self.vend + 0.1
        self.stops = [(0, 0, center(0, 0)), (self.t_map, 0.7, center(1, 0))]
        self.panels = [(*P(0, 0), self.compare), (*P(1, 0), self.splash)]
        self.clip = Clip("chutes")

    def camera(self, t):
        return self.pan(t, self.stops)

    def compare(self, f, t):
        c = self.cue
        lm = card("as13-59-8484", 640, L("lm_cap"), crop=(0.0, 0.0, 1.0, 0.92), rot90=True, cap_size=20)
        lk.place(f, lm, 460 + t * 5, 540, 1.0, -4)
        tlm = c("lm")
        rows = [(c("two_men"), L("built"), L("built_v"), 2, 2, INK, 330),
                (c("three_men"), L("used"), L("used_v"), 3, 4, ACCENT, 650)]
        for t0, lab, val, ppl, days, col, y in rows:
            ua = lin(t, t0 - 0.2, t0 + 0.2)
            lk.text(f, lab, 960, y - 120, "black", 30, lk.INK_SOFT, alpha=ua, tracking=4)
            lk.text(f, val, 960, y - 80, "black", 52, col, alpha=ua)
            for p in range(ppl):
                for d in range(days):
                    k = p * days + d
                    tk = t0 + 0.15 + k * 0.07
                    u = back_out(lin(t, tk, tk + 0.25), 2.0)
                    if u <= 0:
                        continue
                    x = 990 + d * 120
                    yy = y + 40 + p * 74
                    s = 0.9 * u
                    lk.fill_rect(f, x - 48 * s, yy - 30 * s, x + 48 * s, yy + 30 * s, col if d else col)
                    person(f, x, yy + 14 * s, 0.75 * s, WHITE)
                    self.at(t, tk, "tick", 0.25)
        lk.label(f, L("load"), 1520, 900, t, c("four"), size=46, name="black", bg=YELLOW, anchor="cm")
        self.at(t, c("four"), "pop")
        lk.label(f, "AQUARIUS", 300, 140, t, tlm, size=26, name="black", fg=WHITE, bg=INK)

    def splash(self, f, t):
        b = PacMap.base()
        wide = (-27.0, 172.0, 0.40)
        close = (-23.0, 181.0, 0.62)
        v = maps.lerp_view(b, wide, close, lin(t, self.t_map + 0.6, self.D))
        v.draw(f)
        for key, lat, lon in (("aus", -25, 134), ("nz", -38.5, 175.5), ("fiji", -17.8, 178), ("samoa", -13.8, -172)):
            x, y = v.pt(lat, lon)
            lk.text(f, L(key), x, y + 36, "bold", 24, lk.INK_SOFT, anchor="ct", tracking=3)
        sx, sy = v.pt(*SPLASH)
        lk.pulse_marker(f, sx, sy, t, self.t_map + 0.4, ACCENT, 15)
        self.at(t, self.t_map + 0.4, "pop")
        lk.label(f, L("splash"), sx + 30, sy - 24, t, self.t_map + 0.5, size=32, name="black", bar=ACCENT)
        dx, u = slide_in(t, self.t_map + 0.3, 0.6, 900)
        ph = card("S70-35638", 600, L("chutes_cap"), crop=(0.0, 0.08, 1.0, 0.92), cap_size=18)
        lk.place(f, ph, 360 - dx, 500, 1.0, -4, alpha=clamp(u * 2))
        self.at(t, self.t_map + 0.3, "paper", 0.5)


# ================================================================== 10. verdict
class Verdict(Scene):
    trans = "slide"

    def setup(self):
        c = self.cue
        self.t_p1 = c("last") - 0.15
        self.t_p2 = c("warning") - 0.3
        self.stops = [(0, 0, center(0, 0)), (self.t_p1, 0.8, center(1, 0)), (self.t_p2, 0.8, center(2, 0))]
        self.panels = [(*P(0, 0), self.doc1), (*P(1, 0), self.doc2), (*P(2, 0), self.final)]
        self.d1 = Doc(174, 1368, 1612, 1700)
        self.d1.mark("unusual combination", 4, c("combo"), c("combo") + 1.2)
        self.d2 = Doc(183, 1234, 1452, 1640)
        self.d2.mark("contained ammeters", 9, c("meters") - 0.1, c("meters") + 1.6)
        self.d2.circle("contained ammeters", 9, c("never"))

    def camera(self, t):
        x, y, z = self.pan(t, self.stops)
        if self.t_p1 + 0.8 < t < self.t_p2:
            z *= 1 + 0.05 * lin(t, self.t_p1 + 0.8, self.t_p2)
        return x, y, z

    def doc1(self, f, t):
        lk.place(f, self.d1.sprite(t), W / 2, H / 2 - 30, 1.0, 1.0)
        self.at(t, self.d1.marks[0][1], "marker", 0.45)
        lk.text(f, L("doc_src_51"), W - 120, H - 46, "medium", 22, lk.INK_SOFT, anchor="rb")
        lk.label(f, L("doc_label"), 150, 110, t, 0.3, size=24, name="black", fg=WHITE, bg=INK)
        if LANG == "cs":
            lk.label(f, L("tr_combo"), W / 2, H - 110, t, self.d1.marks[0][1] + 0.2, size=36, name="serif_italic",
                     anchor="cb", bar=YELLOW)

    def doc2(self, f, t):
        lk.place(f, self.d2.sprite(t), W / 2, H / 2 - 30, 1.0, -1.0)
        self.at(t, self.d2.marks[0][1], "marker", 0.45)
        self.at(t, self.d2.circles[0][1], "pen", 0.5)
        lk.text(f, L("doc_src_ammeter"), W - 120, H - 46, "medium", 22, lk.INK_SOFT, anchor="rb")
        lk.label(f, L("mistake3"), 150, 110, t, self.t_p1 + 0.5, size=30, name="black", fg=WHITE, bg=ACCENT)
        if LANG == "cs":
            lk.label(f, L("tr_ammeter"), W / 2, H - 110, t, self.d2.marks[0][1] + 0.3, size=30, name="serif_italic",
                     anchor="cb", bar=YELLOW)

    def final(self, f, t):
        c = self.cue
        jitter = 0.86 + 0.01 * math.sin(t * 13)
        meter(f, 520, 560, 230, jitter, t)
        lk.text(f, L("meter"), 520, 700, "black", 32, INK, anchor="ct", tracking=3)
        lk.text(f, L("meter_note"), 520, 760, "serif_italic", 24, lk.INK_SOFT, anchor="ct")
        lk.label(f, L("never_dropped"), 520, 250, t, self.t_p2 + 0.6, size=30, name="black", fg=WHITE, bg=ACCENT,
                 anchor="cb")
        tw = c("warning")
        y = 400
        size = 86
        for li, ln in enumerate((L("final1"), L("final2"))):
            tw_, th = lk.text_size(ln, "black", size, 2)
            hot = L("final_hot")
            if hot in ln:
                pre = ln[:ln.index(hot)]
                px = lk.text_size(pre, "black", size, 2)[0] - (12 if pre else 0)
                hw = lk.text_size(hot, "black", size, 2)[0]
                hot_sweep(f, 900 + px, y + 18, hw - 8, th - 36, t, c("on_meter"), c("on_meter", end=True) + 0.3, 21)
                self.at(t, c("on_meter"), "marker", 0.5)
            headline(f, ln, 900, y, size, t, tw + li * 0.35)
            y += 108


# ================================================================== 11. end
class End(Scene):
    trans = "slide"

    def setup(self):
        self.panels = [(*P(0, 0), self.draw)]

    def draw(self, f, t):
        ttl = L("end1")
        tw, th = lk.text_size(ttl, "black", 92, 3)
        hot_sweep(f, 140, 160, tw - 8, th - 36, t, 0.3, 0.9, 31)
        headline(f, ttl, 140, 140, 92, t, 0.0, tracking=3)
        y = 330
        for i, (role, val) in enumerate(L("credits")):
            a = lin(t, 0.4 + i * 0.12, 0.8 + i * 0.12)
            if role:
                lk.text(f, role, 140, y, "black", 24, lk.INK_SOFT, alpha=a, tracking=4)
            lk.text(f, val, 520, y - 2, "medium", 28, INK, alpha=a)
            y += 64
        lines = lk.wrap(L("photo_ids"), "regular", 20, 1450)
        for i, ln in enumerate(lines):
            lk.text(f, ln, 140, y + 30 + i * 30, "regular", 20, lk.INK_SOFT, alpha=lin(t, 1.4, 1.8))


SCENES = {"hook": Hook, "title": Title, "switch": Switch, "volts": Volts, "drop": Drop, "detank": Detank,
          "weld": Weld, "blast": Blast, "lifeboat": Lifeboat, "verdict": Verdict, "end": End}
