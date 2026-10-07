"""More animation types, so the film doesn't keep repeating the same few moves:
2.5D parallax, flashlight sweep, magnifier loupe, measuring ruler, duotone,
scanner reveal, card-to-fullscreen expand, before/after split, film strip,
icon grid, and the transitions between shots."""
import math
import os

import cv2
import numpy as np

import vox as V
from shots import Shot, annotate, asset, draw_tag, img, kenburns, kb_mapper, mark_sfx, register, tag_img
from vox import H, INK, RED, W, WHITE, clamp, ease_back, ease_io, ease_out, lerp, lin

CREAM = (236, 228, 208)


# ---------------------------------------------------------------- photo treatments
def duotone(src, dark=(18, 10, 12), mid=(176, 34, 40), light=CREAM):
    """Black -> red -> cream gradient map (the red duotone used for dark moments)."""
    g = cv2.cvtColor(src, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    g = np.clip((g - 0.5) * 1.25 + 0.5, 0, 1)[..., None]
    lo = np.array(dark, np.float32) + (np.array(mid, np.float32) - dark) * np.clip(g * 2, 0, 1)
    hi = np.array(mid, np.float32) + (np.array(light, np.float32) - mid) * np.clip(g * 2 - 1, 0, 1)
    return np.where(g < 0.5, lo, hi).astype(np.uint8)


def flashlight(f, t, spec):
    """Dark photo lit by a moving torch beam. spec: {path: [(t, nx, ny)], r, dark}"""
    path = spec["path"]
    if t <= path[0][0]:
        x, y = path[0][1:]
    elif t >= path[-1][0]:
        x, y = path[-1][1:]
    else:
        for a, b in zip(path, path[1:]):
            if t <= b[0]:
                u = ease_io(lin(t, a[0], b[0]))
                x, y = lerp(a[1], b[1], u), lerp(a[2], b[2], u)
                break
    r = spec.get("r", 380) * (1 + 0.03 * math.sin(t * 9))
    yy, xx = np.ogrid[0:H, 0:W]
    d = np.sqrt((xx - x * W) ** 2 + (yy - y * H) ** 2) / r
    light = np.clip(1.25 - d, 0, 1) ** 1.6
    dark = spec.get("dark", 0.2)
    k = dark + (spec.get("gain", 1.6) - dark) * light
    f[:] = np.clip(f * k[..., None] * np.array([1.0, 0.97, 0.88]), 0, 255).astype(np.uint8)


def loupe(f, t, m, src_frame):
    """Magnifier: a ring at (x, y) showing the frame around (tx, ty) enlarged."""
    u = ease_back(lin(t, m["at"], m["at"] + 0.4))
    if u <= 0:
        return
    r = int(m.get("r", 210) * u)
    if r < 4:
        return
    zoom = m.get("zoom", 2.4)
    tx, ty = m["tx"], m["ty"]
    half = int(r / zoom) + 2
    x0, y0 = int(clamp(tx - half, 0, W - 2 * half)), int(clamp(ty - half, 0, H - 2 * half))
    patch = src_frame[y0:y0 + 2 * half, x0:x0 + 2 * half]
    patch = cv2.resize(patch, (2 * r, 2 * r), interpolation=cv2.INTER_CUBIC)
    mask = np.zeros((2 * r, 2 * r), np.uint8)
    cv2.circle(mask, (r, r), r - 2, 255, -1, cv2.LINE_AA)
    cx, cy = int(m["x"]), int(m["y"])
    rgba = np.dstack([patch, mask])
    V.place(f, rgba, cx, cy, 1.0, 0, 1.0, shadow=True)
    cv2.circle(f, (cx, cy), r, WHITE, 10, cv2.LINE_AA)
    cv2.circle(f, (cx, cy), r + 5, INK, 3, cv2.LINE_AA)
    a = math.radians(45)
    p0 = (int(cx + (r + 5) * math.cos(a)), int(cy + (r + 5) * math.sin(a)))
    p1 = (int(cx + (r + 120) * math.cos(a)), int(cy + (r + 120) * math.sin(a)))
    cv2.line(f, p0, p1, INK, 22, cv2.LINE_AA)
    if m.get("guide", True):
        cv2.line(f, (int(tx), int(ty)), (int(cx - r * 0.7), int(cy + r * 0.7)), WHITE, 3, cv2.LINE_AA)
        cv2.circle(f, (int(tx), int(ty)), int(30 / zoom * 2), WHITE, 3, cv2.LINE_AA)


def ruler(f, t, m):
    """Measuring line growing from y0 to y1 at x with ticks and a running value."""
    u = ease_out(lin(t, m["at"], m["at"] + m.get("d", 1.1)))
    if u <= 0:
        return
    x, y0, y1 = m["x"], m["y0"], m["y1"]
    yt = lerp(y0, y1, u)
    cv2.line(f, (int(x), int(y0)), (int(x), int(yt)), RED, 7, cv2.LINE_AA)
    cv2.line(f, (int(x - 30), int(y0)), (int(x + 30), int(y0)), RED, 7, cv2.LINE_AA)
    n = 10
    for k in range(n + 1):
        yk = lerp(y0, y1, k / n)
        if (yk - yt) * (y1 - y0) > 0:
            break
        cv2.line(f, (int(x - 14), int(yk)), (int(x + 14), int(yk)), RED, 4, cv2.LINE_AA)
    cv2.line(f, (int(x - 30), int(yt)), (int(x + 30), int(yt)), RED, 7, cv2.LINE_AA)
    val = m["value"] * u
    txt = (f"{val:.1f}".replace(".", ",") if m.get("decimals", 1) else f"{val:.0f}") + " " + m.get("unit", "m")
    im = V.text_img(txt, "anton", m.get("size", 130), RED, stroke=6, stroke_color=CREAM)
    V.place(f, im, x + 50, clamp((y0 + yt) / 2, 120, H - 120), 1.0, 0, 1.0, shadow=False, ax=0.0, ay=0.5)


def scan(f, t, sp, paper_bg):
    """Scanner bar sweeping down: above it the photo, below it blank paper."""
    u = ease_io(lin(t, sp.get("at", 0.0), sp.get("at", 0.0) + sp.get("d", 1.0)))
    if u >= 1:
        return
    y = int(H * u)
    f[y:] = paper_bg[y:]
    band = np.clip(1 - np.abs(np.arange(-40, 40)) / 40, 0, 1) ** 2
    for k, b in enumerate(band):
        yy = y + k - 40
        if 0 <= yy < H:
            f[yy] = np.clip(f[yy].astype(np.float32) + b * np.array([150, 255, 190]) * 0.6, 0, 255).astype(np.uint8)


def expand(f, t, sp, paper_bg):
    """Starts as a small print on paper and grows into the full frame at sp['at']."""
    u = ease_io(lin(t, sp.get("at", 0.5), sp.get("at", 0.5) + sp.get("d", 0.6)))
    if u >= 1:
        return f
    sc = lerp(sp.get("scale", 0.5), 1.0, u)
    rot = lerp(sp.get("rot", -4), 0, u)
    border = int(lerp(22, 0, u))
    small = cv2.resize(f, (int(W * sc), int(H * sc)), interpolation=cv2.INTER_AREA)
    card = np.zeros((small.shape[0] + 2 * border, small.shape[1] + 2 * border, 4), np.uint8)
    card[..., :3] = WHITE
    card[..., 3] = 255
    card[border:border + small.shape[0], border:border + small.shape[1], :3] = small
    out = paper_bg.copy()
    V.place(out, card, lerp(sp.get("x", W / 2), W / 2, u), lerp(sp.get("y", H / 2), H / 2, u), 1.0, rot, 1.0,
            shadow=u < 0.95)
    return out


# ---------------------------------------------------------------- 2.5D parallax
@register("parallax")
class Parallax(Shot):
    """Cut-out subject (fg) moves faster than the inpainted, softly blurred background."""
    film = True

    def setup(self):
        s = self.spec
        src = img(s["img"])[..., :3]
        cut = img(s["fg"])
        mask = cut[..., 3]
        if mask.shape != src.shape[:2]:
            mask = cv2.resize(mask, (src.shape[1], src.shape[0]))
        cache = asset(s["fg"]).replace(".png", "_bg.jpg")
        if os.path.exists(cache):
            bg = V.load_rgb(cache)
        else:
            k = max(src.shape[:2]) / 900
            small = cv2.resize(src, None, fx=1 / k, fy=1 / k, interpolation=cv2.INTER_AREA)
            m = cv2.resize(mask, (small.shape[1], small.shape[0]))
            m = cv2.dilate((m > 60).astype(np.uint8) * 255, np.ones((15, 15), np.uint8))
            filled = cv2.inpaint(cv2.cvtColor(small, cv2.COLOR_RGB2BGR), m, 9, cv2.INPAINT_TELEA)
            filled = cv2.resize(cv2.cvtColor(filled, cv2.COLOR_BGR2RGB), (src.shape[1], src.shape[0]),
                                interpolation=cv2.INTER_CUBIC)
            a = cv2.GaussianBlur(mask, (0, 0), 3).astype(np.float32)[..., None] / 255
            bg = (src * (1 - a) + filled * a).astype(np.uint8)
            cv2.imwrite(cache, cv2.cvtColor(bg, cv2.COLOR_RGB2BGR))
        g = s.get("grade", "bw")
        conv = (lambda x: V.bw(x, 1.2)) if g == "bw" else (lambda x: x)
        self.bg = cv2.GaussianBlur(conv(bg), (0, 0), s.get("blur", 2.2))
        fg = conv(src)
        self.fg = np.dstack([fg, mask])
        self.marks = s.get("marks", [])
        mark_sfx(self, self.marks)

    def draw(self, t):
        s = self.spec
        u = ease_io(lin(t, 0, self.dur))
        zb = lerp(s.get("z0", 1.05), s.get("z1", 1.1), u)
        zf = lerp(s.get("zf0", 1.05), s.get("zf1", 1.22), u)
        c = s.get("c", (0.5, 0.5))
        f = V.cover(self.bg, W, H, zb, c[0], c[1])
        cv2.convertScaleAbs(f, dst=f, alpha=s.get("bg_dim", 0.8))
        ih, iw = self.fg.shape[:2]
        sc = max(W / iw, H / ih) * zf
        vw, vh = W / sc, H / sc
        x0 = clamp(c[0] * iw - vw / 2, 0, max(iw - vw, 0)) + s.get("drift", 0.0) * iw * u
        y0 = clamp(c[1] * ih - vh / 2, 0, max(ih - vh, 0))
        M = np.float32([[sc, 0, -x0 * sc], [0, sc, -y0 * sc]])
        V.warp_into(f, self.fg, M, 1.0)
        annotate(f, t, self.marks, self.seed)
        for tg in s.get("tags", []):
            draw_tag(f, t, tg)
        return f


# ---------------------------------------------------------------- before / after split
@register("split")
class Split(Shot):
    """Image A full frame; a divider sweeps across and reveals image B. Labels on each side."""
    film = True

    def setup(self):
        s = self.spec
        self.a = V.bw(img(s["a"])[..., :3], 1.2)
        b = img(s["b"])[..., :3]
        self.b = b if s.get("b_color") else V.bw(b, 1.2)
        self.add(s.get("at", 0.6), "whoosh", 0.6)

    def draw(self, t):
        s = self.spec
        fa = kenburns(self.a, t, self.dur, 1.02, 1.08, s.get("ca", (0.5, 0.5)), s.get("ca", (0.5, 0.5)))
        fb = kenburns(self.b, t, self.dur, 1.02, 1.08, s.get("cb", (0.5, 0.5)), s.get("cb", (0.5, 0.5)))
        u = ease_io(lin(t, s.get("at", 0.6), s.get("at", 0.6) + s.get("d", 1.0)))
        xdiv = int(lerp(W, W * s.get("stop", 0.5), u))
        f = fa.copy()
        f[:, xdiv:] = fb[:, xdiv:]
        if 0 < xdiv < W:
            cv2.line(f, (xdiv, 0), (xdiv, H), WHITE, 8, cv2.LINE_AA)
            cv2.circle(f, (xdiv, H // 2), 34, WHITE, -1, cv2.LINE_AA)
            for d in (-1, 1):
                pts = np.array([(xdiv + d * 8, H // 2 - 12), (xdiv + d * 20, H // 2), (xdiv + d * 8, H // 2 + 12)],
                               np.int32)
                cv2.fillPoly(f, [pts], INK, cv2.LINE_AA)
        la = V.text_img(s["la"], "oswald", 60, WHITE, tracking=4)
        V.place(f, tag_img(s["la"], 56), 90, 110, 1.0, 0, 1.0, ax=0.0)
        if u > 0.3:
            V.place(f, tag_img(s["lb"], 56, RED), W - 90, 110, 1.0, 0, clamp((u - 0.3) * 3), ax=1.0)
        del la
        return f


# ---------------------------------------------------------------- film strip
@register("filmstrip")
class Filmstrip(Shot):
    """Frames on a black film strip sliding sideways, with slight gate weave."""
    film = True

    def setup(self):
        s = self.spec
        fh = s.get("frame_h", 560)
        self.frames = []
        for p in s["imgs"]:
            im = V.bw(img(p)[..., :3], 1.2)
            fw = int(fh * 1.42)
            self.frames.append(V.cover(im, fw, fh))
        self.fh, self.fw = fh, int(fh * 1.42)
        self.add(0.0, "projector", 0.7)

    def draw(self, t):
        s = self.spec
        f = V.cover(V.paper(seed=101), W, H, 1.0)
        gap = 70
        strip_h = self.fh + 2 * 90
        total = len(self.frames) * (self.fw + gap) + gap
        u = lin(t, 0, self.dur)
        x0 = lerp(W * 0.15, W - total - W * 0.05, u)
        rng = np.random.default_rng(int(t * V.FPS))
        y0 = (H - strip_h) / 2 + rng.uniform(-1.5, 1.5)
        strip = np.zeros((strip_h, total, 4), np.uint8)
        strip[..., :3] = (16, 15, 14)
        strip[..., 3] = 255
        for k in range(0, total, 64):
            for yy in (28, strip_h - 58):
                cv2.rectangle(strip, (k + 18, yy), (k + 46, yy + 30), (0, 0, 0, 0), -1)
        for k, fr in enumerate(self.frames):
            xx = gap + k * (self.fw + gap)
            strip[90:90 + self.fh, xx:xx + self.fw, :3] = fr
        V.place(f, strip, x0, y0, 1.0, s.get("rot", -2), 1.0, shadow=True, ax=0.0, ay=0.0)
        for tg in s.get("tags", []):
            draw_tag(f, t, tg)
        return f


# ---------------------------------------------------------------- icon grid
@register("icons")
class Icons(Shot):
    """n person icons popping in row by row (each icon = `per` people), big count label."""
    grain = 3.0

    def setup(self):
        s = self.spec
        self.add(s.get("at", 0.1), "pop", 0.5)
        self.add(s.get("at", 0.1) + s.get("d", 1.4), "hit", 0.6)

    def draw(self, t):
        s = self.spec
        f = V.cover(V.paper(seed=111), W, H, 1.0 + 0.03 * lin(t, 0, self.dur))
        n, cols = s["n"], s.get("cols", 11)
        rows = (n + cols - 1) // cols
        size = s.get("size", 70)
        gx, gy = size * 1.15, size * 1.45
        x0 = W * s.get("x", 0.36) - (cols - 1) * gx / 2
        y0 = H / 2 - (rows - 1) * gy / 2 + size * 0.6
        at, d = s.get("at", 0.1), s.get("d", 1.4)
        shown = 0
        for k in range(n):
            st = at + d * k / n
            u = ease_back(lin(t, st, st + 0.18))
            if u <= 0:
                continue
            shown += 1
            r, c = divmod(k, cols)
            x, y = x0 + c * gx, y0 + r * gy
            col = RED if k in s.get("red", []) else INK
            h = size * u
            cv2.circle(f, (int(x), int(y - h * 0.62)), max(int(h * 0.17), 1), col, -1, cv2.LINE_AA)
            body = np.array([(x - h * 0.24, y), (x + h * 0.24, y), (x + h * 0.19, y - h * 0.42),
                             (x - h * 0.19, y - h * 0.42)], np.float32)
            cv2.fillPoly(f, [np.round(body * 4).astype(np.int32)], col, cv2.LINE_AA, shift=2)
        val = int(round(s["value"] * shown / n))
        num = V.text_img(f"{val}", "anton", 230, RED)
        V.place(f, num, W * 0.8, H / 2 - 60, 1.0, 0, 1.0, shadow=False)
        lab = V.text_img(s["label"], "mont", 60, INK)
        V.place(f, lab, W * 0.8, H / 2 + 110, 1.0, 0, 1.0, shadow=False)
        if s.get("note"):
            nt = V.text_img(s["note"], "caveat", 64, RED)
            V.place(f, nt, W * 0.8, H / 2 + 200, 1.0, -3, clamp((t - at - d) * 3), shadow=False)
        return f


# ---------------------------------------------------------------- transitions
def transition(prev, cur, u, kind, seed=0):
    """Blend the outgoing frame `prev` into the incoming `cur`; u runs 0 -> 1."""
    e = ease_io(u)
    if kind == "push":
        out = np.empty_like(cur)
        dx = int(W * e)
        out[:, :W - dx] = prev[:, dx:]
        out[:, W - dx:] = cur[:, :dx]
        return out
    if kind == "slide":                       # incoming sheet slides up over the old one
        out = prev.copy()
        dy = int(H * (1 - e))
        out[dy:] = cur[:H - dy]
        if 0 < dy < H:
            sh = np.clip(1 - np.arange(40) / 40, 0, 1)[:, None, None] * 0.35
            y0 = max(dy - 40, 0)
            out[y0:dy] = (out[y0:dy] * (1 - sh[-(dy - y0):])).astype(np.uint8)
        return out
    if kind == "zoom":                        # punch through the old frame into the new one
        s1 = 1 + 1.4 * ease_out(u) ** 2
        a = cv2.warpAffine(prev, np.float32([[s1, 0, W / 2 * (1 - s1)], [0, s1, H / 2 * (1 - s1)]]), (W, H))
        s2 = lerp(0.82, 1.0, ease_out(u))
        b = cv2.warpAffine(cur, np.float32([[s2, 0, W / 2 * (1 - s2)], [0, s2, H / 2 * (1 - s2)]]), (W, H),
                           borderMode=cv2.BORDER_REPLICATE)
        return cv2.addWeighted(a, 1 - e, b, e, 0)
    if kind == "whip":
        k = int(60 * math.sin(math.pi * u)) * 2 + 1
        src = prev if u < 0.5 else cur
        sh = int((W * 0.6) * (u if u < 0.5 else u - 1))
        m = np.float32([[1, 0, -sh], [0, 1, 0]])
        moved = cv2.warpAffine(src, m, (W, H), borderMode=cv2.BORDER_REFLECT)
        return cv2.blur(moved, (k, 1)) if k > 1 else moved
    if kind == "tear":                        # torn paper edge wipes left to right
        rng = np.random.default_rng(seed)
        ys = np.arange(H)
        jag = (np.cumsum(rng.normal(0, 6, H)) % 60) - 30 + 18 * np.sin(ys / 37.0)
        edge = (lerp(-120, W + 120, e) + jag).astype(int)
        out = prev.copy()
        for y in range(0, H):
            x = max(min(edge[y], W), 0)
            out[y, :x] = cur[y, :x]
            if 0 < x < W - 8:
                out[y, x:x + 8] = (238, 232, 216)
        return out
    if kind == "glitch":
        src = prev if u < 0.5 else cur
        out = src.copy()
        rng = np.random.default_rng(seed + int(u * 100))
        for _ in range(9):
            y = int(rng.uniform(0, H - 60))
            h = int(rng.uniform(8, 60))
            out[y:y + h] = np.roll(src[y:y + h], int(rng.uniform(-90, 90)), axis=1)
        out[..., 0] = np.roll(out[..., 0], 12, axis=1)
        out[..., 2] = np.roll(out[..., 2], -12, axis=1)
        return out
    return cur
