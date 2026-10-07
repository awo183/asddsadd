"""More shot types: timeline strip (V8), scale comparison, clipping stack (V4)."""
import math

import cv2
import numpy as np

import vox as V
from shots import Shot, annotate, draw_phrase, img, mark_sfx, register
from vox import H, INK, RED, W, WHITE, clamp, ease_back, ease_io, ease_out, lerp, lin

MUTED = (120, 112, 100)


@register("timeline")
class Timeline(Shot):
    """years: [{year, label, at, img?}]; the strip slides so the newest year is centred."""
    grain = 3.0

    def setup(self):
        s = self.spec
        self.gap = s.get("gap", 520)
        for y in s["years"]:
            self.add(y["at"], "whoosh", 0.5)
            self.add(y["at"] + 0.12, "pop", 0.6)
        self.cards = {}
        for k, y in enumerate(s["years"]):
            if y.get("img"):
                self.cards[k] = V.card(img(y["img"])[..., :3], y.get("size", 420), border=12, seed=k)

    def draw(self, t):
        s = self.spec
        f = V.cover(V.paper(seed=31), W, H, 1.0)
        ys = s["years"]
        events = [(y["at"], k) for k, y in enumerate(ys)] + [tuple(x) for x in s.get("focus", [])]
        events.sort()
        past = [e for e in events if t >= e[0]] or [events[0]]
        act, t_act = past[-1][1], past[-1][0]
        prev = past[-2][1] if len(past) > 1 else act
        u = ease_io(lin(t, t_act, t_act + 0.45))
        cx = lerp(prev, act, u) * self.gap
        x0 = W / 2 - cx
        base = H * 0.66
        L = (len(ys) - 1) * self.gap
        lu = ease_out(lin(t, 0, 0.5))
        cv2.line(f, (int(x0 - 400), int(base)), (int(x0 + lerp(0, L + 400, lu)), int(base)), INK, 5, cv2.LINE_AA)
        for k, y in enumerate(ys):
            if t < y["at"]:
                continue
            x = x0 + k * self.gap
            a = ease_back(lin(t, y["at"], y["at"] + 0.3))
            on = k == act
            col = RED if on else MUTED
            cv2.circle(f, (int(x), int(base)), int(18 * a), col, -1, cv2.LINE_AA)
            cv2.circle(f, (int(x), int(base)), int(18 * a), INK, 3, cv2.LINE_AA)
            yr = V.text_img(str(y["year"]), "anton", 120, col)
            V.place(f, yr, x, base + 110, (1.15 if on else 0.85) * (0.8 + 0.2 * a), 0, clamp(a * 2), shadow=False)
            if y.get("label"):
                lb = V.text_img(y["label"], "mont", 40, INK if on else MUTED)
                V.place(f, lb, x, base + 205, 1.0, 0, clamp(a * 2), shadow=False)
            if k in self.cards:
                V.place(f, self.cards[k], x, base - 250, 0.85 + 0.15 * a, (-3, 2, -2, 3)[k % 4], clamp(a * 2))
        annotate(f, t, s.get("marks", []), self.seed)
        return f


def person(f, x, base, h, color=INK, a=1.0):
    """Simple flat person silhouette of height h standing on base at x."""
    if a <= 0:
        return
    ov = f.copy()
    r = h * 0.085
    cv2.circle(ov, (int(x), int(base - h + r)), int(r), color, -1, cv2.LINE_AA)
    body = np.array([[x - h * 0.13, base - h * 0.80], [x + h * 0.13, base - h * 0.80],
                     [x + h * 0.11, base - h * 0.42], [x + h * 0.07, base], [x - h * 0.07, base],
                     [x - h * 0.11, base - h * 0.42]], np.float32)
    cv2.fillPoly(ov, [np.round(body * 4).astype(np.int32)], color, cv2.LINE_AA, shift=2)
    cv2.addWeighted(ov, a, f, 1 - a, 0, dst=f)


def metronome(f, x, base, h, t):
    """The Letná metronome: black A-frame with a red swinging needle (25 m)."""
    if h <= 2:
        return
    fh = h * 0.22
    pts = np.array([(x - fh * 0.55, base), (x + fh * 0.55, base), (x + fh * 0.08, base - fh),
                    (x - fh * 0.08, base - fh)], np.int32)
    cv2.fillPoly(f, [pts], (30, 28, 26), cv2.LINE_AA)
    ang = math.radians(16 * math.sin(t * 2.2))
    piv = (x, base - fh * 0.8)
    tip = (x + math.sin(ang) * (h - fh * 0.8), base - fh * 0.8 - math.cos(ang) * (h - fh * 0.8))
    cv2.line(f, (int(piv[0]), int(piv[1])), (int(tip[0]), int(tip[1])), RED, max(int(h * 0.02), 4), cv2.LINE_AA)


def building(f, x, base, w, h, floors, color=(150, 140, 125), a=1.0):
    if a <= 0:
        return
    ov = f.copy()
    cv2.rectangle(ov, (int(x - w / 2), int(base - h)), (int(x + w / 2), int(base)), color, -1, cv2.LINE_AA)
    fh = h / floors
    for i in range(floors):
        for j in range(4):
            wx = x - w / 2 + w * (0.12 + j * 0.21)
            wy = base - h + i * fh + fh * 0.25
            cv2.rectangle(ov, (int(wx), int(wy)), (int(wx + w * 0.12), int(wy + fh * 0.45)), (226, 218, 198), -1)
    cv2.addWeighted(ov, a, f, 1 - a, 0, dst=f)


@register("compare")
class Compare(Shot):
    """Scale comparison on paper. items: [{kind: person|building|img, h_m, x, label, at, img?, w_m?, floors?}],
    ruler: {h_m, at, label}; px_per_m sets the scale."""
    grain = 3.0

    def setup(self):
        s = self.spec
        self.cut = {}
        for k, it in enumerate(s["items"]):
            self.add(it.get("at", 0), "pop", 0.7)
            if it["kind"] == "img":
                src = img(it["img"])
                cut = V.cutout(src[..., :3], src[..., 3], 1400, outline=8) if src.shape[2] == 4 else \
                    V.card(src, 1400)
                self.cut[k] = cut
        r = s.get("ruler")
        if r:
            self.add(r["at"], "riser", 0.4)
            self.add(r["at"] + r.get("d", 1.2), "hit", 0.8)

    def draw(self, t):
        s = self.spec
        f = V.cover(V.paper(seed=41), W, H, 1.0 + 0.03 * lin(t, 0, self.dur))
        base = s.get("base", H * 0.86)
        ppm = s.get("px_per_m", 50)
        cv2.line(f, (0, int(base)), (W, int(base)), INK, 4, cv2.LINE_AA)
        for k, it in enumerate(s["items"]):
            at = it.get("at", 0)
            if t < at:
                continue
            a = ease_out(lin(t, at, at + 0.35))
            h = it["h_m"] * ppm
            x = it["x"]
            if it["kind"] == "person":
                person(f, x, base, h * (0.6 + 0.4 * a), it.get("color", INK), clamp(a * 2))
            elif it["kind"] == "metronome":
                metronome(f, x, base, h * a, t)
            elif it["kind"] == "statue":
                block = [(x - h * 0.55, base), (x + h * 0.55, base), (x + h * 0.5, base - h * 0.9),
                         (x + h * 0.2, base - h), (x - h * 0.5, base - h * 0.85)]
                ov = f.copy()
                cv2.fillPoly(ov, [np.array(block, np.int32)], (196, 192, 184), cv2.LINE_AA)
                cv2.addWeighted(ov, 0.9 * clamp(a * 2), f, 1 - 0.9 * clamp(a * 2), 0, dst=f)
                cv2.polylines(f, [np.array(block, np.int32)], True, INK, 3, cv2.LINE_AA)
            elif it["kind"] == "building":
                building(f, x, base, it.get("w_m", 12) * ppm, h * a, it.get("floors", 5), a=clamp(a * 2))
            else:
                cut = self.cut[k]
                sc = h / cut.shape[0]
                V.place(f, cut, x, base, sc * (0.9 + 0.1 * ease_back(lin(t, at, at + 0.35))), 0, clamp(a * 2),
                        ay=1.0)
            if it.get("label"):
                lb = V.text_img(it["label"], "mont", 38, INK)
                V.place(f, lb, x, base + 42, 1.0, 0, clamp(a * 2), shadow=False)
        r = s.get("ruler")
        if r and t >= r["at"]:
            u = ease_out_q(lin(t, r["at"], r["at"] + r.get("d", 1.2)))
            hx = r.get("x", W - 220)
            top = base - r["h_m"] * ppm * u
            cv2.line(f, (int(hx), int(base)), (int(hx), int(top)), RED, 6, cv2.LINE_AA)
            cv2.line(f, (int(hx - 26), int(top)), (int(hx + 26), int(top)), RED, 6, cv2.LINE_AA)
            val = r["h_m"] * u
            txt = f"{val:.1f}".replace(".", ",") + " m"
            im = V.text_img(txt, "anton", 110, RED)
            V.place(f, im, hx - 40, top - 30, 1.0, 0, 1.0, shadow=False, ax=1.0, ay=0.5)
            if r.get("guide"):
                for xx in range(0, W, 40):
                    cv2.line(f, (xx, int(top)), (xx + 20, int(top)), (180, 60, 60), 2, cv2.LINE_AA)
        annotate(f, t, s.get("marks", []), self.seed)
        if s.get("headline"):
            draw_phrase(f, t, s["headline"])
        return f


def ease_out_q(u):
    u = clamp(u)
    return 1 - (1 - u) ** 2


def clipping_img(head, sub=None, w=900, seed=0, kicker=None):
    """A generic period-style newspaper clipping (no real masthead): headline,
    optional standfirst, grey text lines, torn edges."""
    rng = np.random.default_rng(seed)
    lines = V.wrap(head, "play", 76, w - 80)
    hh = len(lines) * 88
    sub_lines = V.wrap(sub, "play_reg", 38, w - 80) if sub else []
    body_y = 60 + (50 if kicker else 0) + hh + len(sub_lines) * 48 + 30
    h = body_y + 260
    pap = V.cover(V.paper(seed=50 + seed % 5, tone=V.AGED), w, h, 1.0)
    out = np.dstack([pap, np.full((h, w), 255, np.uint8)])
    tmp = out[..., :3].copy()
    y = 40
    if kicker:
        k = V.text_img(kicker.upper(), "oswald", 30, (90, 20, 20), tracking=3)
        V.blit(tmp, k, 40, y)
        y += 50
    for ln in lines:
        im = V.text_img(ln, "play", 76, (22, 20, 18))
        V.blit(tmp, im, 40, y)
        y += 88
    for ln in sub_lines:
        im = V.text_img(ln, "play_reg", 38, (60, 56, 50))
        V.blit(tmp, im, 40, y)
        y += 48
    y += 20
    cols = 3
    cw = (w - 80 - (cols - 1) * 24) / cols
    for c in range(cols):
        for r_ in range(9):
            x0 = 40 + c * (cw + 24)
            ln = cw * (rng.uniform(0.7, 1.0) if r_ % 5 != 4 else rng.uniform(0.3, 0.6))
            cv2.line(tmp, (int(x0), int(y + r_ * 26)), (int(x0 + ln), int(y + r_ * 26)), (120, 112, 98), 7)
    out[..., :3] = tmp
    edge = (V._noise(1, w, 18, rng)[0] * 22 + rng.random(w) * 6).astype(int)
    for x in range(w):
        out[h - edge[x]:, x, 3] = 0
        out[:max(edge[(x * 7) % w] // 3, 1), x, 3] = 0
    return out


@register("clippings")
class Clippings(Shot):
    """V4 stack: clips [{head, sub, kicker, at, x, y, rot, img?}], last one gets a push and highlight."""
    grain = 3.0

    def setup(self):
        s = self.spec
        self.ims = []
        for k, c in enumerate(s["clips"]):
            if c.get("img"):
                im = V.card(img(c["img"])[..., :3], c.get("size", 900), border=0, grade=c.get("grade", False),
                            torn=True, seed=k)
            else:
                im = clipping_img(c["head"], c.get("sub"), c.get("w", 900), self.seed + k, c.get("kicker"))
            self.ims.append(im)
            self.add(c["at"], "paper", 0.9)

    def draw(self, t):
        s = self.spec
        last = s["clips"][-1]
        z = 1.0 + 0.12 * ease_io(lin(t, last["at"] + 0.3, self.dur))
        f = V.cover(V.paper(seed=13), W, H, 1.0 + 0.03 * lin(t, 0, self.dur))
        for k, (c, im) in enumerate(zip(s["clips"], self.ims)):
            if t < c["at"]:
                continue
            u = lin(t, c["at"], c["at"] + 5 / V.FPS)
            sc = lerp(1.3, 1.0, ease_out(u))
            dx, dy = V.shake(t, c["at"] + 5 / V.FPS, 0.1, 6, self.seed + k)
            x = W / 2 + (c.get("x", W / 2) - W / 2) * z + dx
            y = H / 2 + (c.get("y", H / 2) - H / 2) * z + dy
            V.place(f, im, x, y, sc * z * c.get("scale", 1.0), c.get("rot", 0), clamp(u * 2))
        annotate(f, t, s.get("marks", []), self.seed)
        return f


@register("subscribe")
class Subscribe(Shot):
    """A red subscribe button pops in, gets clicked, turns grey."""
    grain = 3.0

    def setup(self):
        s = self.spec
        self.add(s.get("at", 0.15), "pop", 0.8)
        self.add(s.get("click", 1.4), "tick", 1.0)
        self.add(s.get("click", 1.4) + 0.05, "pop", 0.6)

    def draw(self, t):
        s = self.spec
        f = V.cover(V.paper(seed=91), W, H, 1.0)
        at, ck = s.get("at", 0.15), s.get("click", 1.4)
        u = ease_back(lin(t, at, at + 0.35))
        done = t >= ck
        press = 1 - 0.06 * (1 - ease_out(lin(t, ck, ck + 0.2))) if done else 1.0
        col = (110, 106, 100) if done else RED
        txt = s.get("done_text", "ODEBÍRÁNO ✓") if done else s.get("text", "ODEBÍRAT")
        lab = V.text_img(txt.replace(" ✓", ""), "oswald", 96, WHITE, tracking=4)
        bw_, bh = lab.shape[1] + 140, lab.shape[0] + 70
        btn = np.zeros((bh, bw_, 4), np.uint8)
        cv2.rectangle(btn, (0, 0), (bw_ - 1, bh - 1), col + (255,), -1)
        tmp = btn[..., :3].copy()
        V.blit(tmp, lab, 70, 35)
        btn[..., :3] = tmp
        V.place(f, btn, W / 2, H / 2, max(u, 0.01) * press, 0, clamp(u * 3))
        if t >= ck - 0.6:
            v = ease_out(lin(t, ck - 0.6, ck))
            cx, cy = lerp(W / 2 + 420, W / 2 + 60, v), lerp(H / 2 + 300, H / 2 + 20, v)
            pts = np.array([(cx, cy), (cx, cy + 62), (cx + 16, cy + 48), (cx + 30, cy + 76), (cx + 40, cy + 70),
                            (cx + 27, cy + 43), (cx + 48, cy + 43)], np.int32)
            cv2.fillPoly(f, [pts], WHITE, cv2.LINE_AA)
            cv2.polylines(f, [pts], True, INK, 3, cv2.LINE_AA)
        return f
