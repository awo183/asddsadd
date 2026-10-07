"""Shot types for the film. Each shot is built from a spec dict and draws frame(t)
for local time t (seconds). Shots also list their sound events in self.sfx as
(local_time, name, gain).

Spec keys shared by every shot: type, start, dur (filled in by plan.py), and
optionally flash (white flash on entry), leak (light leak on entry), sfx (extra
[(t, name, gain)]).
"""
import math
import os

import cv2
import numpy as np

import vox as V
from vox import (BLACK, H, INK, PAPER, RED, W, WHITE, clamp, ease_back, ease_io, ease_out,
                 ease_out_expo, lerp, lin)

ASSETS = os.path.join(V.BUILD, "assets")


def asset(p):
    return p if os.path.isabs(p) else os.path.join(ASSETS, p)


_IMG = {}


def img(path):
    if path is None:                      # asset not found yet: visible placeholder for previews
        ph = np.full((900, 1200, 3), 90, np.uint8)
        cv2.putText(ph, "MISSING", (300, 480), cv2.FONT_HERSHEY_SIMPLEX, 4, (255, 80, 80), 8)
        return ph
    p = asset(path)
    if p not in _IMG:
        _IMG[p] = V.load_rgba(p) if p.endswith(".png") else V.load_rgb(p)
    return _IMG[p]


class Shot:
    film = False        # archival look (dust, flicker)
    grain = 4.0

    def __init__(self, spec):
        self.spec = spec
        self.dur = spec["dur"]
        self.sfx = list(spec.get("sfx", []))
        self.seed = V.seed_of(spec.get("id", spec["type"]), spec["start"])
        self.setup()

    def setup(self):
        pass

    def draw(self, t):
        raise NotImplementedError

    def frame(self, t, i):
        f = self.draw(t)
        s = self.spec
        if s.get("leak"):
            V.light_leak(f, max(0.0, 1 - t / 0.35) * 0.8, self.seed)
        if self.film or s.get("film"):
            V.dust(f, i, s.get("dust", 1.0))
        V.finish(f, i, s.get("grain", self.grain), s.get("vig", 0.35),
                 0.04 if (self.film or s.get("film")) else 0.0)
        if s.get("flash") and t < 2.5 / V.FPS:
            V.fill(f, (255, 255, 255), 1.0 if t < 1 / V.FPS else 0.55)
        fo = s.get("fade_out", 0)
        if fo and t > self.dur - fo:
            V.fill(f, BLACK, lin(t, self.dur - fo, self.dur))
        fi = s.get("fade_in", 0)
        if fi and t < fi:
            V.fill(f, BLACK, 1 - lin(t, 0, fi))
        return f

    def add(self, t, name, gain=1.0):
        self.sfx.append((t, name, gain))


# ---------------------------------------------------------------- helpers
def kenburns(src, t, dur, z0, z1, c0, c1, ease=ease_io):
    u = ease(lin(t, 0, dur)) if ease else lin(t, 0, dur)
    return V.cover(src, W, H, lerp(z0, z1, u), lerp(c0[0], c1[0], u), lerp(c0[1], c1[1], u))


def kb_mapper(src, t, dur, z0, z1, c0, c1, ease=ease_io):
    """Function mapping normalized image coords to screen coords for the same Ken Burns state."""
    u = ease(lin(t, 0, dur)) if ease else lin(t, 0, dur)
    ih, iw = src.shape[:2]
    sc = max(W / iw, H / ih) * lerp(z0, z1, u)
    vw, vh = W / sc, H / sc
    x0 = clamp(lerp(c0[0], c1[0], u) * iw - vw / 2, 0, max(iw - vw, 0))
    y0 = clamp(lerp(c0[1], c1[1], u) * ih - vh / 2, 0, max(ih - vh, 0))
    return lambda nx, ny: ((nx * iw - x0) * sc, (ny * ih - y0) * sc)


def annotate(f, t, marks, seed, mapper=None):
    """marks: list of dicts {kind: circle|arrow|underline|label, at, ...} in screen px,
    or with nx/ny (and np0/np1) in normalized image coords when a mapper is given."""
    for k, m in enumerate(marks):
        if mapper is not None and "nx" in m:
            m = dict(m)
            m["x"], m["y"] = mapper(m["nx"], m["ny"])
        if mapper is not None and "np0" in m:
            m = dict(m)
            m["p0"], m["p1"] = mapper(*m["np0"]), mapper(*m["np1"])
        u = (t - m["at"]) / m.get("d", 0.5)
        if u <= 0:
            continue
        kind = m["kind"]
        if kind == "circle":
            pts = V.circle_pts(m["x"], m["y"], m["rx"], m.get("ry", m["rx"]), seed + k)
            V.draw_path(f, pts, V.sine_io(u), m.get("color", RED), m.get("w", 8))
        elif kind == "arrow":
            pts = V.arrow_pts(m["p0"], m["p1"], seed + k)
            V.draw_path(f, pts, V.sine_io(u), m.get("color", RED), m.get("w", 8), head=True)
        elif kind == "underline":
            pts = V.underline_pts(m["x0"], m["x1"], m["y"], seed + k)
            V.draw_path(f, pts, V.sine_io(u), m.get("color", RED), m.get("w", 8))
        elif kind == "cross":
            r = m.get("r", 40)
            x, y = m["x"], m["y"]
            V.draw_path(f, np.array([(x - r, y - r), (x + r, y + r)], float), V.sine_io(u * 2), m.get("color", RED),
                        m.get("w", 10))
            V.draw_path(f, np.array([(x + r, y - r), (x - r, y + r)], float), V.sine_io(u * 2 - 1),
                        m.get("color", RED), m.get("w", 10))
        elif kind == "label":
            im = V.text_img(m["text"], m.get("font", "caveat"), m.get("size", 64), m.get("color", RED))
            a = ease_out(u * 2)
            V.place(f, im, m["x"], m["y"] + (1 - a) * 12, 1.0, m.get("rot", -3), a, shadow=False)
        elif kind == "tag":
            im = tag_img(m["text"], m.get("size", 40))
            a = ease_back(u * 1.5)
            V.place(f, im, m["x"], m["y"], 0.85 + 0.15 * a, m.get("rot", 0), clamp(u * 3), shadow=True,
                    ax=m.get("ax", 0.5), ay=m.get("ay", 0.5))


_TAGS = {}


def tag_img(s, size=40, bg=(16, 16, 16), fg=WHITE):
    key = (s, size, bg, fg)
    if key not in _TAGS:
        t = V.text_img(s, "oswald", size, fg, tracking=2)
        px, py = int(size * 0.45), int(size * 0.3)
        out = np.zeros((t.shape[0] + 2 * py, t.shape[1] + 2 * px, 4), np.uint8)
        out[..., :3] = bg
        out[..., 3] = 240
        tmp = out[..., :3].copy()
        V.blit(tmp, t, px, py)
        out[..., :3] = tmp
        _TAGS[key] = out
    return _TAGS[key]


def mark_sfx(shot, marks):
    for m in marks:
        if m["kind"] in ("circle", "arrow", "underline", "cross"):
            shot.add(m["at"], "marker", 0.7)
        elif m["kind"] == "tag":
            shot.add(m["at"], "pop", 0.3)


# ---------------------------------------------------------------- full-frame photo / footage
class Photo(Shot):
    """Full-screen archival still with Ken Burns (B1/B16), optional marks and caption tag."""
    film = True

    def setup(self):
        s = self.spec
        src = img(s["img"])[..., :3]
        g = s.get("grade", "bw")
        if g == "bw":
            self.src = V.bw(src, s.get("contrast", 1.25))
        elif g == "muted":
            gray = cv2.cvtColor(cv2.cvtColor(src, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB)
            self.src = cv2.addWeighted(src, 0.6, gray, 0.4, 0)
        elif g == "duotone":
            import variety
            self.src = variety.duotone(src)
        else:
            self.src = src
        if s.get("scan"):
            self.add(s["scan"].get("at", 0.0), "paper_slide", 0.6)
        if s.get("expand"):
            self.add(s["expand"].get("at", 0.5), "whoosh", 0.5)
        for m in s.get("loupes", []):
            self.add(m["at"], "pop", 0.5)
        for m in s.get("rulers", []):
            self.add(m["at"], "pen", 0.6)
        if s.get("shake_sound"):
            for k in s.get("shakes", []):
                self.add(k, s["shake_sound"], 1.0)
        self.marks = s.get("marks", [])
        mark_sfx(self, self.marks)

    def draw(self, t):
        s = self.spec
        f = kenburns(self.src, t, self.dur, s.get("z0", 1.0), s.get("z1", 1.08),
                     s.get("c0", (0.5, 0.5)), s.get("c1", s.get("c0", (0.5, 0.5))))
        dx = dy = 0.0
        for k in s.get("shakes", []):
            a, b = V.shake(t, k, 0.5, 26, self.seed)
            dx, dy = dx + a, dy + b
        if dx or dy:
            f = cv2.warpAffine(f, np.float32([[1.03, 0, dx - W * 0.015], [0, 1.03, dy - H * 0.015]]), (W, H),
                               borderMode=cv2.BORDER_REPLICATE)
        if s.get("darken"):
            a0, a1 = s["darken"]
            cv2.convertScaleAbs(f, dst=f, alpha=lerp(1.0, a1, ease_io(lin(t, a0, self.dur))))
        mp = kb_mapper(self.src, t, self.dur, s.get("z0", 1.0), s.get("z1", 1.08), s.get("c0", (0.5, 0.5)),
                       s.get("c1", s.get("c0", (0.5, 0.5))))
        if s.get("flashlight") or s.get("loupes") or s.get("rulers") or s.get("scan") or s.get("expand"):
            import variety
            if s.get("flashlight"):
                variety.flashlight(f, t, s["flashlight"])
            base = f.copy() if s.get("loupes") else None
            for m in s.get("loupes", []):
                m2 = dict(m)
                if "ntx" in m:
                    m2["tx"], m2["ty"] = mp(m["ntx"], m["nty"])
                variety.loupe(f, t, m2, base)
            for m in s.get("rulers", []):
                m2 = dict(m)
                if "nx" in m:
                    m2["x"], m2["y0"] = mp(m["nx"], m["ny0"])
                    m2["y1"] = mp(m["nx"], m["ny1"])[1]
                variety.ruler(f, t, m2)
        annotate(f, t, self.marks, self.seed, mp)
        for tg in s.get("tags", []):
            draw_tag(f, t, tg)
        if s.get("scan"):
            import variety
            variety.scan(f, t, s["scan"], V.cover(V.paper(seed=7, tone=V.AGED), W, H))
        if s.get("expand"):
            import variety
            f = variety.expand(f, t, s["expand"], V.cover(V.paper(seed=3), W, H))
        return f


class Footage(Shot):
    """Real video, graded B&W (or colour), with optional push-in, marks and slow motion."""
    film = True

    def setup(self):
        s = self.spec
        self.cap = cv2.VideoCapture(asset(s["src"]))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 25
        self.n = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.idx, self.cur = -1, None
        self.marks = s.get("marks", [])
        mark_sfx(self, self.marks)

    def src_frame(self, t):
        s = self.spec
        idx = int((s.get("in", 0.0) + t * s.get("speed", 1.0)) * self.fps)
        idx = min(max(idx, 0), max(self.n - 2, 0))
        if idx < self.idx or self.cur is None:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            self.idx = idx - 1
        while self.idx < idx:
            ok = self.cap.grab()
            if not ok:
                break
            self.idx += 1
            self.cur = None
        if self.cur is None:
            ok, im = self.cap.retrieve()
            if ok:
                self.cur = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
                g = s.get("grade", "bw")
                if g == "bw":
                    self.cur = V.bw(self.cur, s.get("contrast", 1.2), 0.04)
                elif g == "muted":
                    gray = cv2.cvtColor(cv2.cvtColor(self.cur, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB)
                    self.cur = cv2.addWeighted(self.cur, 0.65, gray, 0.35, 0)
            elif self.cur is None:
                self.cur = np.zeros((H, W, 3), np.uint8)
        return self.cur

    def draw(self, t):
        s = self.spec
        src = self.src_frame(t)
        f = kenburns(src, t, self.dur, s.get("z0", 1.0), s.get("z1", 1.04),
                     s.get("c0", (0.5, 0.5)), s.get("c1", s.get("c0", (0.5, 0.5))), ease=None)
        annotate(f, t, self.marks, self.seed)
        for tg in s.get("tags", []):
            draw_tag(f, t, tg)
        cap = s.get("caption")
        if cap:
            draw_caption(f, cap)
        return f


def draw_tag(f, t, tg):
    """Date/place tag (V9-style chip) or handwritten note that pops in at tg['at']."""
    u = lin(t, tg.get("at", 0.2), tg.get("at", 0.2) + 0.3)
    if u <= 0:
        return
    if tg.get("hand"):
        st = tg.get("stroke", 5)
        im = V.text_img(tg["text"], "caveat", tg.get("size", 92), tuple(tg.get("color", RED)), stroke=st,
                        stroke_color=(250, 248, 240))
        V.place(f, im, tg.get("x", W - 120), tg.get("y", 140) + (1 - ease_out(u)) * 14, 1.0, tg.get("rot", -4),
                clamp(u * 2), shadow=False, ax=tg.get("ax", 1.0))
        return
    im = tag_img(tg["text"], tg.get("size", 48), tg.get("bg", (16, 16, 16)), tg.get("fg", WHITE))
    V.place(f, im, tg.get("x", 90), tg.get("y", H - 120), 0.85 + 0.15 * ease_back(u), tg.get("rot", 0),
            clamp(u * 2), shadow=True, ax=tg.get("ax", 0.0), ay=0.5)


def draw_caption(f, text):
    """Burned-in caption for archival audio (B19): white, outlined, bottom centre."""
    lines = V.wrap(text, "mont_med", 44, 1500)
    y = H - 80 - len(lines) * 58
    for ln in lines:
        im = V.text_img(ln, "mont_med", 44, WHITE, stroke=3, stroke_color=(0, 0, 0))
        V.blit(f, im, W / 2 - im.shape[1] / 2, y)
        y += 58


# ---------------------------------------------------------------- paper collage
class Collage(Shot):
    """V1 paper board. items: list of dicts
       {kind: card|cutout|stamp|tag|text|png, img, x, y, size, rot, at, depth, torn, mode}
    plus camera push (z0->z1, pan px), optional highlight headline."""
    grain = 3.0

    def setup(self):
        s = self.spec
        self.bg = V.paper(seed=s.get("paper_seed", 1))
        self.layers = []
        for k, it in enumerate(s.get("items", [])):
            kind = it.get("kind", "card")
            if kind == "card":
                im = V.card(img(it["img"])[..., :3], it.get("size", 760), torn=it.get("torn", False),
                            seed=self.seed + k, grade=it.get("grade", True))
                snd = "pop"
            elif kind == "cutout":
                src = img(it["img"])
                im = V.cutout(src[..., :3], src[..., 3], it.get("size", 760), grade=it.get("grade", True))
                snd = "whoosh"
            elif kind == "stamp":
                im = V.stamp(it["text"], size=it.get("size", 110), seed=self.seed + k)
                snd = "stamp"
            elif kind == "tag":
                im = V.label_strip(it["text"], it.get("role"), it.get("size", 54))
                snd = "pop"
            elif kind == "text":
                im = V.text_img(it["text"], it.get("font", "anton"), it.get("size", 120),
                                tuple(it.get("color", INK)), tracking=it.get("tracking", 0))
                snd = "pop"
            elif kind == "video":
                im = None
                cap = cv2.VideoCapture(asset(it["src"]))
                self.videos = getattr(self, "videos", {})
                self.videos[k] = [cap, cap.get(cv2.CAP_PROP_FPS) or 25, -1, None]
                snd = "pop"
            elif kind == "png":
                im = img(it["img"])
                if im.shape[2] == 3:
                    im = np.dstack([im, np.full(im.shape[:2], 255, np.uint8)])
                sz = it.get("size")
                if sz:
                    im = V.fit_long(im, sz)
                snd = "pop"
            else:
                raise ValueError(kind)
            self.layers.append((it, im))
            if it.get("sound", True) is not False:
                if kind != "tag" or it.get("sound"):         # name strips slide in silently
                    self.add(it.get("at", 0.0), it.get("sound") if isinstance(it.get("sound"), str) else snd,
                             0.55 if snd != "stamp" else 0.9)
        self.marks = s.get("marks", [])
        mark_sfx(self, self.marks)
        hl = s.get("headline")
        if hl:
            self.add(hl.get("hl_at", hl.get("at", 0) + 0.4), "marker", 0.6)

    def cam(self, t):
        s = self.spec
        u = lin(t, 0, self.dur)
        z = lerp(s.get("z0", 1.0), s.get("z1", 1.06), u)
        px = lerp(0, s.get("pan", (30, 0))[0], u)
        py = lerp(0, s.get("pan", (30, 0))[1], u)
        return z, px, py

    def draw(self, t):
        z, px, py = self.cam(t)
        bg = self.bg
        f = V.cover(bg, W, H, 1.0 + (z - 1) * 0.3)
        sx, sy = 0.0, 0.0
        for it, im in self.layers:
            if it.get("kind") == "stamp":
                dx, dy = V.shake(t, it.get("at", 0) + 4 / V.FPS, 0.12, 9, self.seed)
                sx, sy = sx + dx, sy + dy
        self.draw_headline(f, t, z)
        for k, (it, im) in enumerate(self.layers):
            at = it.get("at", 0.0)
            if t < at:
                continue
            if it.get("kind") == "video":
                im = self.video_frame(k, it, t - at)
            fade = 1.0 - ease_out(lin(t, it["out"], it["out"] + 0.35)) if it.get("out") is not None else 1.0
            if fade <= 0:
                continue
            d = it.get("depth", 1.0)
            zz = 1 + (z - 1) * d
            x = W / 2 + (it["x"] - W / 2) * zz + px * d + sx
            y = H / 2 + (it["y"] - H / 2) * zz + py * d + sy
            kind = it.get("kind", "card")
            if kind == "stamp":
                u = lin(t, at, at + 4 / V.FPS)
                sc = lerp(1.8, 1.0, V.ease_in(u))
                V.place(f, im, x, y, sc * zz * it.get("scale", 1.0), it.get("rot", -10), 0.92 * clamp(u * 2),
                        shadow=False, mode="multiply")
                continue
            enter = it.get("enter") or ("pop", "drop", "slide", "pop")[(self.seed + k) % 4]
            if kind == "tag":
                enter = it.get("enter") or "slide"
            if enter == "slide":
                u = ease_out(lin(t, at, at + 0.3))
                x -= (1 - u) * 90
                sc, a = 1.0, u
            elif enter == "drop":
                u = lin(t, at, at + 5 / V.FPS)
                sc, a = lerp(1.3, 1.0, ease_out(u)), clamp(u * 2)
            else:
                u = lin(t, at, at + 9 / V.FPS)
                sc, a = lerp(0.85, 1.0, ease_back(u)), clamp(u * 2.5)
            rot = it.get("rot", 0.0) + it.get("spin", 0.0) * lin(t, at, self.dur)
            V.place(f, im, x, y, sc * zz * it.get("scale", 1.0), rot, a * fade,
                    shadow=it.get("shadow", True), ax=it.get("ax", 0.5), ay=it.get("ay", 0.5))
        annotate(f, t, self.marks, self.seed)
        for tg in self.spec.get("tags", []):
            draw_tag(f, t, tg)
        return f

    def video_frame(self, k, it, t):
        cap, fps, idx, cur = self.videos[k]
        want = int((it.get("in", 0.0) + t * it.get("speed", 1.0)) * fps)
        if want < idx or cur is None:
            cap.set(cv2.CAP_PROP_POS_FRAMES, want)
            idx = want - 1
        while idx < want:
            if not cap.grab():
                break
            idx += 1
            cur = None
        if cur is None:
            ok, fr = cap.retrieve()
            fr = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB) if ok else np.zeros((640, 360, 3), np.uint8)
            if it.get("crop"):
                x0, y0, x1, y1 = it["crop"]
                h, w = fr.shape[:2]
                fr = fr[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
            cur = V.card(fr, it.get("size", 700), border=14, grade=it.get("grade", False))
        self.videos[k] = [cap, fps, idx, cur]
        return cur

    def draw_headline(self, f, t, z):
        hl = self.spec.get("headline")
        if not hl:
            return
        draw_phrase(f, t, hl)


def draw_phrase(f, t, hl):
    """Kinetic phrase with a highlighter swipe behind key words (V2).
    hl: {lines: [str], x, y, size, font, at, stagger, hi: [(line, first_word, last_word)], hl_at, color}"""
    size = hl.get("size", 92)
    fnt = hl.get("font", "mont")
    color = tuple(hl.get("color", INK))
    at = hl.get("at", 0.0)
    stag = hl.get("stagger", 0.07)
    lh = int(size * 1.22)
    x0, y = hl.get("x", 140), hl.get("y", 140)
    center = hl.get("align") == "center"
    k = 0
    word_boxes = []
    for li, line in enumerate(hl["lines"]):
        words = line.split()
        space = V.text_w("a b", fnt, size) - V.text_w("ab", fnt, size)
        widths = [V.text_w(w_, fnt, size) for w_ in words]
        total = sum(widths) + space * (len(words) - 1)
        x = W / 2 - total / 2 if center else x0
        boxes = []
        for wi, w_ in enumerate(words):
            boxes.append((x, y, x + widths[wi], y + size * 1.05))
            x += widths[wi] + space
        word_boxes.append(boxes)
        y += lh
    for li, a, b in hl.get("hi", []):
        bx0 = word_boxes[li][a][0] - 10
        bx1 = word_boxes[li][b][2] + 10
        by0 = word_boxes[li][a][1] + size * 0.18
        by1 = word_boxes[li][a][1] + size * 1.08
        u = ease_out(lin(t, hl.get("hl_at", at + 0.5), hl.get("hl_at", at + 0.5) + 0.42))
        V.marker(f, bx0, by0, bx1, by1, u, seed=li * 7 + a)
    cps = hl.get("typing")                 # typewriter: letters appear one by one at cps
    nchar = 0
    for li, line in enumerate(hl["lines"]):
        for wi, w_ in enumerate(line.split()):
            bx = word_boxes[li][wi]
            if cps:
                shown = int((t - at) * cps) - nchar
                nchar += len(w_) + 1
                if shown <= 0:
                    continue
                part = w_[:shown]
                im = V.text_img(part, fnt, size, color)
                V.blit(f, im, bx[0], bx[1])
                continue
            st = at + k * stag
            k += 1
            u = ease_out(lin(t, st, st + 0.2))
            if u <= 0:
                continue
            im = V.text_img(w_, fnt, size, color)
            V.blit(f, im, bx[0], bx[1] + (1 - u) * 22, u)


# ---------------------------------------------------------------- type cards
class Slam(Shot):
    """V5 huge words. lines: [str], accent: index of the red line, bg: paper|black|img"""
    grain = 4.0

    def setup(self):
        s = self.spec
        if s.get("sound", "impact"):
            self.add(s.get("at", 0.0), s.get("sound", "impact"), s.get("gain", 1.0))
        if s.get("bg") not in (None, "paper", "black"):
            self.bgimg = V.bw(img(s["bg"])[..., :3])
        self.size = s.get("size", 230)

    def draw(self, t):
        s = self.spec
        bg = s.get("bg", "black")
        if bg == "paper":
            f = V.cover(V.paper(seed=3), W, H, 1.0 + 0.04 * lin(t, 0, self.dur))
            col = INK
        elif bg == "black":
            f = np.zeros((H, W, 3), np.uint8)
            f[:] = (12, 12, 12)
            col = WHITE
        else:
            f = kenburns(self.bgimg, t, self.dur, 1.05, 1.12, (0.5, 0.5), (0.5, 0.5))
            cv2.convertScaleAbs(f, dst=f, alpha=0.38)
            col = WHITE
        at = s.get("at", 0.0)
        lines = s["lines"]
        sizes = s.get("sizes", [self.size] * len(lines))
        ims = [V.text_img(ln, s.get("font", "anton"), sz, RED if s.get("accent") == k else col,
                          tracking=4) for k, (ln, sz) in enumerate(zip(lines, sizes))]
        total = sum(im.shape[0] for im in ims) + 20 * (len(ims) - 1)
        y = H / 2 - total / 2
        for k, im in enumerate(ims):
            st = at + k * s.get("stagger", 0.12)
            u = lin(t, st, st + 4 / V.FPS)
            if u > 0:
                sc = lerp(1.18, 1.0, V.ease_in(u))
                V.place(f, im, W / 2, y + im.shape[0] / 2, sc, 0, clamp(u * 2), shadow=bg == "paper")
            y += im.shape[0] + 20
        return f


class Chapter(Shot):
    """B6 chapter card: white condensed caps, film flicker, metallic boom."""
    film = True
    grain = 6.0

    def setup(self):
        s = self.spec
        self.add(s.get("at", 0.1), "boom", 1.0)
        self.bgimg = V.bw(img(s["bg"])[..., :3]) if s.get("bg") else None

    def draw(self, t):
        s = self.spec
        if self.bgimg is not None:
            f = kenburns(self.bgimg, t, self.dur, 1.0, 1.08, (0.5, 0.5), (0.5, 0.45))
            cv2.convertScaleAbs(f, dst=f, alpha=0.42)
        else:
            f = np.zeros((H, W, 3), np.uint8)
        at = s.get("at", 0.1)
        if t >= at:
            fl = 1.0
            if t < at + 0.28:
                fl = 0.75 + 0.25 * np.random.default_rng(int(t * 1000)).random()
            im = V.text_img(s["text"], "oswald", s.get("size", 150), WHITE, tracking=6)
            V.place(f, im, W / 2, H / 2 - (40 if s.get("sub") else 0), 1.0 + 0.02 * lin(t, at, self.dur), 0,
                    fl * clamp((t - at) / 0.2), shadow=False)
            if s.get("sub"):
                sub = V.text_img(s["sub"], "mont_med", 44, (200, 196, 188), tracking=3)
                V.place(f, sub, W / 2, H / 2 + 80, 1.0, 0, clamp((t - at - 0.3) / 0.3), shadow=False)
        return f


class Black(Shot):
    grain = 2.0

    def draw(self, t):
        return np.zeros((H, W, 3), np.uint8)


class Highlight(Shot):
    """V2 phrase on paper (or B3 typed document with a highlighter)."""
    grain = 3.0

    def setup(self):
        s = self.spec
        hl = s["phrase"]
        self.add(hl.get("hl_at", hl.get("at", 0) + 0.5), "marker", 0.7)
        if s.get("style") == "doc":
            self.add(hl.get("at", 0), "typewriter", 0.6)

    def draw(self, t):
        s = self.spec
        if s.get("style") == "doc":
            f = V.cover(V.paper(seed=7, tone=V.AGED), W, H, 1.0 + 0.07 * ease_io(lin(t, 0, self.dur)), 0.5, 0.45)
        else:
            f = V.cover(V.paper(seed=5), W, H, 1.0 + 0.03 * lin(t, 0, self.dur))
        draw_phrase(f, t, s["phrase"])
        annotate(f, t, s.get("marks", []), self.seed)
        return f


class Counter(Shot):
    """V7 stat card: number counts up, unit, caption. bg: paper or a darkened photo."""
    grain = 3.0

    def setup(self):
        s = self.spec
        at, d = s.get("at", 0.1), s.get("count", 1.0)
        n = min(int(d * 5), 6)
        for k in range(n):
            self.add(at + k * d / n, "tick", 0.3)
        self.add(at + d, "hit", 0.9)
        self.bgimg = V.bw(img(s["bg"])[..., :3]) if s.get("bg") not in (None, "paper") else None
        if self.bgimg is not None and s.get("duo"):
            import variety
            self.bgimg = variety.duotone(img(s["bg"])[..., :3])

    def fmt(self, v):
        s = self.spec
        dec = s.get("decimals", 0)
        txt = f"{v:,.{dec}f}".replace(",", " ").replace(".", ",")
        return s.get("prefix", "") + txt

    def draw(self, t):
        s = self.spec
        if self.bgimg is None:
            f = V.cover(V.paper(seed=11), W, H, 1.0 + 0.03 * lin(t, 0, self.dur))
            col, sub = INK, (70, 64, 58)
        else:
            f = kenburns(self.bgimg, t, self.dur, 1.04, 1.1, (0.5, 0.5), (0.5, 0.5))
            f = cv2.GaussianBlur(f, (0, 0), 6)
            cv2.convertScaleAbs(f, dst=f, alpha=0.62 if s.get("duo") else 0.4)
            col, sub = WHITE, (240, 232, 220)
        at, d = s.get("at", 0.1), s.get("count", 1.0)
        u = ease_out_expo(lin(t, at, at + d))
        v = lerp(s.get("from", 0), s["to"], u)
        num = V.text_img(self.fmt(v), "anton", s.get("size", 260),
                         WHITE if s.get("duo") else (RED if s.get("red", True) else col))
        unit = V.text_img(s.get("unit", ""), "anton", int(s.get("size", 260) * 0.45), col) if s.get("unit") else None
        final = V.text_img(self.fmt(s["to"]), "anton", s.get("size", 260), col)
        gap = 30
        tw_ = final.shape[1] + (unit.shape[1] + gap if unit is not None else 0)
        x = W / 2 - tw_ / 2
        y = H / 2 - final.shape[0] / 2 - 40
        dx, dy = V.shake(t, at + d, 0.15, 6, self.seed)
        sc = 1.0 + 0.06 * (1 - ease_out(lin(t, at + d, at + d + 0.25))) * (t > at + d)
        if t >= at:
            V.place(f, num, x + dx + num.shape[1] / 2, y + dy + final.shape[0] / 2, sc, 0, 1.0, shadow=False)
            if unit is not None:
                V.blit(f, unit, x + final.shape[1] + gap + dx, y + final.shape[0] - unit.shape[0] + dy)
        cap = s.get("caption")
        if cap:
            cu = ease_out(lin(t, at + d * 0.6, at + d * 0.6 + 0.3))
            im = V.text_img(cap, "mont", 56, sub)
            V.blit(f, im, W / 2 - im.shape[1] / 2, y + final.shape[0] + 40 + (1 - cu) * 16, cu)
        return f


SHOTS = {"photo": Photo, "footage": Footage, "collage": Collage, "slam": Slam, "chapter": Chapter,
         "black": Black, "highlight": Highlight, "counter": Counter}


def register(name):
    def deco(cls):
        SHOTS[name] = cls
        return cls
    return deco


def make(spec):
    return SHOTS[spec["type"]](spec)
