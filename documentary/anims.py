"""Procedural animations (skia). Each function draws one frame: fn(canvas, t, dur, state, **kw)."""
import functools
import json
import math
import os
import random

import cv2
import numpy as np
import skia

from engine import (ASSETS, BOOK, BOOK_I, NUM, NUM_B, NUM_I, CREAM, GOLD, H, HAND, INK, SANS, SERIF, SERIF_I, TYPE, W, clamp,
                    draw_image, draw_text, ease_in_out, ease_out, fade_env, font, formula, paint,
                    skia_image_from_bgra, smooth, wrap)

DIM = (150, 140, 125)
NAVY = (14, 18, 28)


# ----------------------------------------------------------------------------- common pieces
def bg(c, top=(16, 20, 30), bottom=(6, 7, 11), glow=(70, 52, 30), gx=0.5, gy=0.45):
    p = skia.Paint(Shader=skia.GradientShader.MakeLinear(
        points=[(0, 0), (0, H)], colors=[skia.Color(*top), skia.Color(*bottom)]))
    c.drawPaint(p)
    if glow:
        g = skia.Paint(Shader=skia.GradientShader.MakeRadial(
            center=(W * gx, H * gy), radius=W * 0.55,
            colors=[skia.Color(*glow, 110), skia.Color(*glow, 0)]))
        c.drawPaint(g)


def fade_black(c, a):
    if a > 0:
        c.drawRect(skia.Rect.MakeWH(W, H), paint((0, 0, 0), a))


def master_fade(c, t, dur, fin=0.8, fout=0.8):
    fade_black(c, 1 - fade_env(t, dur, fin, fout))


@functools.lru_cache(maxsize=None)
def noise_texture(w, h, base, var, seed=1, fibers=True, stains=True):
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1, (h // 4, w // 4)).astype(np.float32)
    n = cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC)
    fine = rng.normal(0, 1, (h, w)).astype(np.float32)
    lum = n * 0.6 + fine * 0.25
    if fibers:
        f = np.zeros((h, w), np.float32)
        for _ in range(900):
            x, y = rng.integers(0, w), rng.integers(0, h)
            ang = rng.uniform(0, math.pi)
            ln = rng.uniform(8, 40)
            cv2.line(f, (int(x), int(y)), (int(x + ln * math.cos(ang)), int(y + ln * math.sin(ang))),
                     float(rng.uniform(-1, 1)), 1)
        lum += cv2.GaussianBlur(f, (0, 0), 0.8) * 0.6
    if stains:
        s = rng.normal(0, 1, (h // 60 + 2, w // 60 + 2)).astype(np.float32)
        s = cv2.resize(s, (w, h), interpolation=cv2.INTER_CUBIC)
        lum += np.clip(s - 1.4, 0, None) * -1.2
    img = np.zeros((h, w, 4), np.uint8)
    for i, ch in enumerate((2, 1, 0)):  # base is RGB -> BGRA
        img[..., ch] = np.clip(base[i] + lum * var, 0, 255)
    # edge darkening
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.minimum.reduce([x, y, w - x, h - y]) / (0.12 * min(w, h))
    e = 0.72 + 0.28 * np.clip(d, 0, 1)
    img[..., :3] = (img[..., :3].astype(np.float32) * e[..., None]).astype(np.uint8)
    img[..., 3] = 255
    return skia_image_from_bgra(img)


def paper(w, h, seed=3):
    return noise_texture(w, h, (226, 211, 178), 9.0, seed)


def slate_tex():
    return noise_texture(W, H, (44, 50, 48), 7.0, 11, fibers=False, stains=False)


def polyline_partial(points, frac):
    """Return the points of a polyline truncated to `frac` of its total length."""
    pts = np.asarray(points, np.float64)
    if frac >= 1:
        return pts
    seg = np.hypot(*np.diff(pts, axis=0).T)
    cum = np.concatenate([[0], np.cumsum(seg)])
    target = cum[-1] * max(frac, 0)
    i = np.searchsorted(cum, target)
    if i == 0:
        return pts[:1]
    i = min(i, len(pts) - 1)
    u = (target - cum[i - 1]) / max(seg[i - 1], 1e-9)
    end = pts[i - 1] + (pts[i] - pts[i - 1]) * u
    return np.vstack([pts[:i], end])


def draw_polyline(c, pts, p):
    if len(pts) < 2:
        return
    path = skia.Path()
    path.moveTo(*pts[0])
    for x, y in pts[1:]:
        path.lineTo(x, y)
    c.drawPath(path, p)


def fmt_int(n):
    return f"{n:,}"


# ----------------------------------------------------------------------------- titles
FORMULAS = [
    r"\frac{1}{\pi}=\frac{2\sqrt{2}}{9801}\sum_{k=0}^{\infty}\frac{(4k)!\,(1103+26390k)}{(k!)^4\,396^{4k}}",
    r"1729 = 1^3+12^3 = 9^3+10^3",
    r"3=\sqrt{1+2\sqrt{1+3\sqrt{1+4\sqrt{1+\cdots}}}}",
    r"p(n)\sim\frac{1}{4n\sqrt{3}}\,e^{\pi\sqrt{2n/3}}",
    r"\sum_{n=0}^{\infty}\frac{q^{n^2}}{(1-q)(1-q^2)\cdots(1-q^n)}=\prod_{n=0}^{\infty}\frac{1}{(1-q^{5n+1})(1-q^{5n+4})}",
    r"p(5n+4)\equiv 0\ (\mathrm{mod}\ 5)",
    r"\sum_{n=1}^{\infty}\frac{n^{13}}{e^{2\pi n}-1}=\frac{1}{24}",
    r"\pi\approx\left(9^2+\frac{19^2}{22}\right)^{1/4}",
    r"\sum_{n\geq 1}\tau(n)\,q^n = q\prod_{n\geq 1}(1-q^n)^{24}",
    r"f(q)=1+\frac{q}{(1+q)^2}+\frac{q^4}{(1+q)^2(1+q^2)^2}+\cdots",
    r"\int_0^{\infty}x^{s-1}\sum_{k=0}^{\infty}\frac{\varphi(k)}{k!}(-x)^k\,dx=\Gamma(s)\,\varphi(-s)",
    r"L\approx\pi\left[3(a+b)-\sqrt{(3a+b)(a+3b)}\right]",
    r"1+2+3+4+\cdots = -\frac{1}{12}",
    r"\frac{1}{1+\frac{e^{-2\pi}}{1+\frac{e^{-4\pi}}{1+\cdots}}}=\left(\sqrt{\frac{5+\sqrt{5}}{2}}-\frac{\sqrt{5}+1}{2}\right)e^{2\pi/5}",
    r"p(7n+5)\equiv 0\ (\mathrm{mod}\ 7)",
    r"p(11n+6)\equiv 0\ (\mathrm{mod}\ 11)",
]


def _drift_formulas(c, t, st, alpha=0.16, n=14, seed=5, speed=1.0, size=40):
    if "drift" not in st:
        rng = random.Random(seed)
        items = []
        for i in range(n):
            depth = rng.uniform(0.35, 1.0)
            items.append(dict(f=FORMULAS[(i + seed) % len(FORMULAS)], x=rng.uniform(-0.2, 1.0) * W,
                              y=rng.uniform(0.04, 0.92) * H, d=depth, v=rng.uniform(14, 30)))
        st["drift"] = items
    for it in st["drift"]:
        img = formula(it["f"], size=size)
        s = 0.55 + 0.6 * it["d"]
        x = (it["x"] + t * it["v"] * it["d"] * speed) % (W + 900) - 700
        draw_image(c, img, x, it["y"], h=img.height() * s * 0.5, a=alpha * it["d"])


def title(c, t, dur, st, title="RAMANUJAN", subtitle=""):
    bg(c, glow=(80, 58, 28))
    _drift_formulas(c, t, st, alpha=0.13)
    a1 = smooth((t - 0.6) / 2.2)
    f = font(SERIF, 190, 500)
    # letters resolve from wide tracking to tight
    tr = 60 * (1 - ease_out((t - 0.6) / 4.0)) + 26
    draw_text(c, title, W / 2, H / 2 + 30, f, GOLD, a1, align="center", shadow=12, tracking=tr)
    lw = 700 * ease_out((t - 2.0) / 2.0)
    c.drawRect(skia.Rect.MakeXYWH(W / 2 - lw / 2, H / 2 + 75, lw, 2), paint(GOLD, 0.8 * a1))
    a2 = smooth((t - 3.0) / 1.8)
    draw_text(c, subtitle, W / 2, H / 2 + 150, font(SERIF_I, 64, 400), CREAM, a2, align="center", shadow=8)
    master_fade(c, t, dur, 1.2, 1.5)


def chapter_card(c, t, dur, st, num="I", name="", years=""):
    bg(c, glow=(60, 45, 26), gy=0.5)
    _drift_formulas(c, t + 40, st, alpha=0.07, n=8, seed=hash(name) % 97)
    a = smooth((t - 0.3) / 1.0)
    draw_text(c, f"CHAPTER {num}", W / 2, H / 2 - 70, font(SANS, 26, 500), GOLD, a, align="center", tracking=9)
    f = font(SERIF, 104, 500)
    a2 = smooth((t - 0.7) / 1.2)
    draw_text(c, name, W / 2, H / 2 + 50, f, CREAM, a2, align="center", shadow=10)
    lw = 360 * ease_out((t - 1.0) / 1.4)
    c.drawRect(skia.Rect.MakeXYWH(W / 2 - lw / 2, H / 2 + 88, lw, 2), paint(GOLD, 0.7 * a2))
    draw_text(c, years, W / 2, H / 2 + 150, font(SERIF_I, 46, 400), DIM, smooth((t - 1.3) / 1.2), align="center")
    master_fade(c, t, dur, 0.7, 0.9)


# ----------------------------------------------------------------------------- letters
def _stamp(c, x, y):
    c.save()
    c.translate(x, y)
    c.rotate(3)
    # perforated edge
    c.drawRect(skia.Rect.MakeXYWH(-6, -6, 132, 162), paint((236, 228, 210)))
    for i in range(12):
        for (px, py) in ((-6 + i * 12, -6), (-6 + i * 12, 156)):
            c.drawCircle(px, py, 4, paint((205, 190, 160)))
    c.drawRect(skia.Rect.MakeXYWH(4, 4, 112, 142), paint((150, 48, 44)))
    c.drawRect(skia.Rect.MakeXYWH(14, 30, 92, 88), paint((236, 220, 200), 0.9))
    draw_text(c, "INDIA", 60, 24, font(SERIF, 22, 700), (240, 225, 205), align="center")
    draw_text(c, "POSTAGE", 60, 140, font(SERIF, 16, 700), (240, 225, 205), align="center")
    draw_text(c, "1", 60, 98, font(SERIF, 64, 600), (150, 48, 44), align="center")
    c.restore()
    # postmark
    c.save()
    c.translate(x - 70, y + 70)
    c.rotate(-12)
    pm = paint((60, 40, 70), 0.55, stroke=3)
    c.drawCircle(0, 0, 70, pm)
    c.drawCircle(0, 0, 50, paint((60, 40, 70), 0.45, stroke=2))
    draw_text(c, "MADRAS", 0, -12, font(SERIF, 26, 700), (60, 40, 70), 0.6, align="center")
    draw_text(c, "JAN 1913", 0, 22, font(SERIF, 22, 700), (60, 40, 70), 0.6, align="center")
    for k in range(5):
        path = skia.Path()
        yy = -40 + k * 20
        path.moveTo(80, yy)
        for s in range(10):
            path.quadTo(100 + s * 24, yy - 10, 112 + s * 24, yy)
        c.drawPath(path, paint((60, 40, 70), 0.4, stroke=3))
    c.restore()


def letter_envelope(c, t, dur, st):
    bg(c, top=(30, 22, 16), bottom=(10, 8, 6), glow=(120, 85, 45))
    u = ease_in_out(t / dur)
    c.save()
    c.translate(W / 2, H / 2 + 20)
    c.scale(0.92 + 0.16 * u, 0.92 + 0.16 * u)
    c.rotate(-4 + 3 * u)
    ew, eh = 1100, 640
    # shadow
    c.drawRect(skia.Rect.MakeXYWH(-ew / 2 + 18, -eh / 2 + 26, ew, eh), paint((0, 0, 0), 0.6, blur=30))
    draw_image(c, paper(ew, eh, seed=21), -ew / 2, -eh / 2)
    # flap lines
    fl = paint((150, 128, 95), 0.35, stroke=2)
    draw_polyline(c, [(-ew / 2, -eh / 2), (0, -eh / 2 + 260), (ew / 2, -eh / 2)], fl)
    _stamp(c, ew / 2 - 170, -eh / 2 + 40)
    fh = font(HAND, 40)
    lines = ["G. H. Hardy, Esq., F.R.S.", "Trinity College,", "Cambridge,", "England."]
    for i, ln in enumerate(lines):
        a = smooth((t - 0.6 - i * 0.7) / 0.9)
        draw_text(c, ln, -260 + i * 60, 40 + i * 70, fh, INK, a * 0.92)
    c.restore()
    master_fade(c, t, dur, 1.0, 0.8)


def letter_text(c, t, dur, st, text="", header="Madras, 16th January 1913", sign="", hand_size=46,
                formula_tex=None):
    bg(c, top=(26, 20, 15), bottom=(8, 6, 5), glow=(110, 80, 45))
    pw, ph = 1440, 1900
    if "lines" not in st:
        f = font(HAND, hand_size)
        paras = [p.strip() for p in text.split("\n") if p.strip()]
        lines = []
        for p in paras:
            lines += wrap(p, f, pw - 260)
            lines.append("")
        st["lines"] = lines
        st["nchar"] = sum(len(l) for l in lines)
    lines = st["lines"]
    f = font(HAND, hand_size)
    lh = hand_size * 2.05
    write_end = dur * 0.86
    chars = st["nchar"] * clamp((t - 0.5) / max(write_end - 0.5, 0.1))
    # follow the writing line with the camera
    total_rows = len(lines) + 3
    cur_row = 0
    acc = 0
    for i, ln in enumerate(lines):
        if acc + len(ln) >= chars:
            cur_row = i
            break
        acc += len(ln)
    else:
        cur_row = len(lines)
    if formula_tex:
        total_rows += 3
    y_focus = 230 + (cur_row + 3) * lh
    cam_y = clamp(y_focus - H * 0.55, 0, ph - H + 80)
    st["cam"] = st.get("cam", cam_y) * 0.9 + cam_y * 0.1
    c.save()
    c.translate((W - pw) / 2, 40 - st["cam"])
    c.rotate(-0.6)
    c.drawRect(skia.Rect.MakeXYWH(14, 20, pw, ph), paint((0, 0, 0), 0.6, blur=30))
    draw_image(c, paper(pw, ph, seed=8), 0, 0)
    for k in range(int(ph / lh)):
        c.drawRect(skia.Rect.MakeXYWH(90, 200 + k * lh + 14, pw - 180, 1.2), paint((120, 140, 170), 0.18))
    draw_text(c, header, pw - 130, 150, f, INK, smooth(t / 0.8) * 0.9, align="right")
    shown = chars
    y = 200 + 2 * lh
    for ln in lines:
        if ln:
            n = int(clamp(shown, 0, len(ln)))
            if n > 0:
                draw_text(c, ln[:n], 130, y, f, INK, 0.92)
            shown -= len(ln)
        y += lh
    if formula_tex and shown > 0:
        img = formula(formula_tex, size=34, rgb=INK)
        draw_image(c, img, 160, y, h=img.height() * 0.55, a=smooth(shown / 30) * 0.9)
        y += img.height() * 0.55 + lh
    if sign and chars >= st["nchar"]:
        draw_text(c, sign, pw - 160, y + lh, f, INK, smooth((t - write_end) / 0.8) * 0.9, align="right")
    c.restore()
    master_fade(c, t, dur, 0.8, 0.8)


# ----------------------------------------------------------------------------- formulas & numbers
def formula_wall(c, t, dur, st):
    bg(c, glow=(50, 40, 25))
    if "items" not in st:
        rng = random.Random(42)
        items = []
        for i, f in enumerate(FORMULAS):
            items.append(dict(f=f, x=rng.uniform(0.05, 0.75) * W, y=(i + 0.5) / len(FORMULAS) * H * 1.3 - H * 0.15,
                              d=rng.uniform(0.4, 1.0), t0=rng.uniform(0, 0.5) * dur))
        st["items"] = items
    for it in sorted(st["items"], key=lambda q: q["d"]):
        img = formula(it["f"], size=44)
        s = (0.4 + 0.55 * it["d"])
        y = it["y"] - t * 22 * it["d"]
        x = it["x"] + math.sin(t * 0.2 + it["d"] * 9) * 20
        a = smooth((t - it["t0"]) / 1.5) * (0.25 + 0.75 * it["d"] ** 2)
        draw_image(c, img, x, y, h=img.height() * s * 0.72, a=a)
    master_fade(c, t, dur, 0.8, 0.8)


@functools.lru_cache(maxsize=None)
def digits(which, n=1500):
    import mpmath
    mpmath.mp.dps = n + 10
    v = mpmath.pi if which == "pi" else mpmath.sqrt(2)
    return mpmath.nstr(v, n, strip_zeros=False)


def digits_pi(c, t, dur, st):
    bg(c, glow=(40, 50, 70))
    f = font(TYPE, 38)
    half = dur / 2
    which = "pi" if t < half else "sqrt2"
    lt = t if t < half else t - half
    s = digits(which)
    per_row = 52
    cw = f.measureText("0") + 4
    x0 = W / 2 - per_row * cw / 2 + 120
    nshow = int(20 + lt * 70)
    rows = [s[i:i + per_row] for i in range(0, min(nshow, len(s)), per_row)]
    y0 = 200 - max(0, len(rows) - 15) * 52
    for r, row in enumerate(rows):
        y = y0 + r * 52
        if y < -40:
            continue
        for k, ch in enumerate(row):
            idx = r * per_row + k
            age = nshow - idx
            col = GOLD if age < 6 else CREAM
            a = 0.25 + 0.6 * clamp(1 - age / 600) + (0.15 if age < 6 else 0)
            c.drawString(ch, x0 + k * cw, y, f, paint(col, a))
    sym = "π" if which == "pi" else "√2"
    a = fade_env(lt, half, 0.6, 0.6)
    c.drawPaint(skia.Paint(Shader=skia.GradientShader.MakeLinear(
        points=[(0, 0), (560, 0)], colors=[skia.Color(6, 8, 14, int(235 * a)), skia.Color(6, 8, 14, 0)])))
    draw_text(c, sym, 230, H / 2 + 60, font(SERIF, 240, 500), GOLD, a, align="center", shadow=14)
    master_fade(c, t, dur, 0.7, 0.7)
    fade_black(c, 0.9 * (1 - smooth(abs(t - half) / 0.35)))


def slate(c, t, dur, st):
    draw_image(c, slate_tex(), 0, 0)
    items = [
        (r"\frac{\pi^2}{6}=1+\frac{1}{2^2}+\frac{1}{3^2}+\frac{1}{4^2}+\cdots", 160, 140),
        (r"\frac{x}{e^x-1}=\sum_{n=0}^{\infty}B_n\,\frac{x^n}{n!}", 1000, 230),
        (r"\sin x = x-\frac{x^3}{3!}+\frac{x^5}{5!}-\cdots", 220, 460),
        (r"\sqrt{x+n+a}=\sqrt{ax+(n+a)^2+x\sqrt{a(x+n)+(n+a)^2+\cdots}}", 600, 640),
        (r"\Gamma(x+1)=x\,\Gamma(x)", 1180, 470),
        (r"1-5\left(\frac{1}{2}\right)^3+9\left(\frac{1\cdot 3}{2\cdot 4}\right)^3-\cdots=\frac{2}{\pi}", 160, 860),
    ]
    n = len(items)
    for i, (tex, x, y) in enumerate(items):
        t0 = 0.4 + i * (dur * 0.75 / n)
        prog = clamp((t - t0) / 2.2)
        if prog <= 0:
            continue
        img = formula(tex, size=40, rgb=(235, 235, 225))
        w, h = img.width() * 0.62, img.height() * 0.62
        c.save()
        c.clipRect(skia.Rect.MakeXYWH(x - 10, y - 10, (w + 20) * prog, h + 20))
        draw_image(c, img, x, y, w=w, h=h, a=0.88)
        c.restore()
    # chalk speckle
    if "speck" not in st:
        rng = np.random.default_rng(3)
        m = (rng.random((H, W)) > 0.82).astype(np.uint8) * 140
        arr = np.zeros((H, W, 4), np.uint8)
        arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3] = 48, 50, 44, m
        st["speck"] = skia_image_from_bgra(arr)
    draw_image(c, st["speck"], 0, 0, a=0.6)
    # the elbow eraser sweeps across near the end
    e = clamp((t - dur * 0.82) / (dur * 0.14))
    if e > 0:
        ex = -300 + e * (W + 600)
        c.save()
        c.clipRect(skia.Rect.MakeXYWH(0, 0, max(0, ex - 100), H))
        draw_image(c, slate_tex(), 0, 0, a=0.85)
        c.restore()
        # chalk-dust smear left by the sweep
        c.drawCircle(ex - 120, H * 0.45 + math.sin(e * 9) * 120, 300, paint((120, 126, 120), 0.10, blur=90))
    c.drawPaint(skia.Paint(Shader=skia.GradientShader.MakeRadial(
        center=(W / 2, H / 2), radius=W * 0.7, colors=[skia.Color(0, 0, 0, 0), skia.Color(0, 0, 0, 170)])))
    master_fade(c, t, dur, 0.6, 0.7)


def nested_radical(c, t, dur, st):
    bg(c, glow=(45, 50, 70))
    img = formula(r"3=\sqrt{1+2\sqrt{1+3\sqrt{1+4\sqrt{1+5\sqrt{1+\cdots}}}}}", size=58)
    draw_image(c, img, W / 2, 230, h=img.height() * 0.62, a=smooth(t / 1.2), center=True)
    vals = []
    for n in range(1, 13):
        v = 1.0
        for k in range(n + 1, 1, -1):
            v = math.sqrt(1 + k * v)
        vals.append(v)
    x0, y0, bw, gap, hmax = 360, 900, 70, 30, 440
    c.drawRect(skia.Rect.MakeXYWH(x0 - 20, y0 - hmax, 1260, 2), paint(GOLD, 0.5 * smooth((t - 1) / 1)))
    draw_text(c, "3", x0 - 50, y0 - hmax + 12, font(NUM_B, 40), GOLD, smooth((t - 1) / 1), align="right")
    for i, v in enumerate(vals):
        p = ease_out((t - 1.2 - i * 0.35) / 0.9)
        if p <= 0:
            continue
        h = hmax * (v / 3) * p
        x = x0 + i * (bw + gap)
        c.drawRect(skia.Rect.MakeXYWH(x, y0 - h, bw, h), paint((120, 150, 200), 0.75))
        draw_text(c, f"{v:.5f}"[:6], x + bw / 2, y0 - h - 14, font(NUM, 22), CREAM, p, align="center")
        draw_text(c, str(i + 1), x + bw / 2, y0 + 34, font(SANS, 20, 400), DIM, p, align="center")
    draw_text(c, "nesting depth", W / 2, y0 + 80, font(SANS, 22, 400), DIM, smooth((t - 1.5) / 1), align="center",
              tracking=3)
    master_fade(c, t, dur, 0.6, 0.7)


def continued_fraction(c, t, dur, st):
    bg(c, glow=(40, 45, 70))
    stages = [
        r"\dfrac{1}{1+\dfrac{e^{-2\pi}}{1+\cdots}}",
        r"\dfrac{1}{1+\dfrac{e^{-2\pi}}{1+\dfrac{e^{-4\pi}}{1+\cdots}}}",
        r"\dfrac{1}{1+\dfrac{e^{-2\pi}}{1+\dfrac{e^{-4\pi}}{1+\dfrac{e^{-6\pi}}{1+\cdots}}}}",
    ]
    rhs = r"=\left(\sqrt{\dfrac{5+\sqrt{5}}{2}}-\dfrac{\sqrt{5}+1}{2}\right)\,e^{2\pi/5}"
    k = min(int(t / (dur * 0.17)), 2)
    lt = t - k * dur * 0.17
    img = formula(stages[k], size=46)
    sc = 0.9
    a = smooth(lt / 0.6) if k == 0 else 1.0
    if k > 0 and lt < 0.4:  # brief dissolve from the previous stage
        prev = formula(stages[k - 1], size=46)
        draw_image(c, prev, 150, H / 2 - prev.height() * sc / 2 - 60, h=prev.height() * sc, a=1 - lt / 0.4)
        a = lt / 0.4
    draw_image(c, img, 150, H / 2 - img.height() * sc / 2 - 60, h=img.height() * sc, a=a)
    ra = smooth((t - dur * 0.55) / 1.2)
    rimg = formula(rhs, size=46)
    final = formula(stages[2], size=46)
    draw_image(c, rimg, 150 + final.width() * sc + 24, H / 2 - rimg.height() * sc / 2 - 60,
               h=rimg.height() * sc, a=ra)
    if ra > 0:
        import mpmath
        mpmath.mp.dps = 30
        val = (mpmath.sqrt((5 + mpmath.sqrt(5)) / 2) - (mpmath.sqrt(5) + 1) / 2) * mpmath.e ** (2 * mpmath.pi / 5)
        s = mpmath.nstr(val, 18)
        draw_text(c, "= " + s + "…", W / 2, H - 230, font(NUM, 60), GOLD, ra, align="center", shadow=8)
        draw_text(c, "From Ramanujan's first letter to Hardy, 1913", W / 2, H - 150, font(SERIF_I, 34), DIM, ra,
                  align="center")
    master_fade(c, t, dur, 0.6, 0.8)


PART4 = [[4], [3, 1], [2, 2], [2, 1, 1], [1, 1, 1, 1]]
PCOL = [(222, 170, 90), (120, 170, 210), (200, 120, 110), (140, 190, 140)]


def partitions4(c, t, dur, st):
    bg(c, glow=(45, 40, 60))
    draw_text(c, "The partitions of 4", W / 2, 150, font(SERIF, 70, 500), CREAM, smooth(t / 1), align="center")
    u, gap = 70, 22
    for r, parts in enumerate(PART4):
        t0 = dur * 0.38 + r * dur * 0.1
        a = ease_out((t - t0) / 0.6)
        if a <= 0:
            continue
        y = 260 + r * 135
        x = 640
        for j, p in enumerate(parts):
            for b in range(p):
                rect = skia.Rect.MakeXYWH(x + b * (u + 6), y + (1 - a) * 30, u, u)
                c.drawRRect(skia.RRect.MakeRectXY(rect, 10, 10), paint(PCOL[j % 4], 0.92 * a))
            x += p * (u + 6) + gap
        label = " + ".join(map(str, parts))
        draw_text(c, label, 580, y + 52, font(NUM, 50), CREAM, a, align="right")
    fa = smooth((t - dur * 0.9) / 0.6)
    draw_text(c, "p(4) = 5", W - 260, H - 120, font(NUM_B, 66), GOLD, fa, align="center", shadow=8)
    master_fade(c, t, dur, 0.6, 0.6)


@functools.lru_cache(maxsize=None)
def partitions_table(N=400):
    p = [0] * (N + 1)
    p[0] = 1
    for n in range(1, N + 1):
        s, k = 0, 1
        while True:
            g1 = k * (3 * k - 1) // 2
            if g1 > n:
                break
            sign = 1 if k % 2 else -1
            s += sign * p[n - g1]
            g2 = k * (3 * k + 1) // 2
            if g2 <= n:
                s += sign * p[n - g2]
            k += 1
        p[n] = s
    return p


def partition_growth(c, t, dur, st):
    bg(c, glow=(40, 40, 60))
    p = partitions_table()
    x0, y0, gw, gh = 260, 900, 1400, 640
    ax = paint(DIM, 0.6, stroke=2)
    draw_polyline(c, [(x0, y0 - gh), (x0, y0), (x0 + gw, y0)], ax)
    for e in range(0, 14, 2):
        y = y0 - gh * e / 13
        draw_text(c, "10" + "".join("\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079"[int(d)] for d in str(e)) if e else "1", x0 - 20, y + 8, font(NUM, 24), DIM, 0.8,
                  align="right")
        c.drawRect(skia.Rect.MakeXYWH(x0, y, gw, 1), paint(DIM, 0.12))
    for n in range(0, 201, 50):
        draw_text(c, str(n), x0 + gw * n / 200, y0 + 36, font(NUM, 24), DIM, 0.8, align="center")
    draw_text(c, "n", x0 + gw + 30, y0 + 8, font(SERIF_I, 34), DIM, 0.9)
    draw_text(c, "number of partitions  p(n)", x0, y0 - gh - 30, font(SANS, 24, 500), DIM, 0.9, tracking=2)
    prog = ease_in_out((t - 0.5) / (dur * 0.8))
    nmax = max(1, int(200 * prog))
    pts = [(x0 + gw * n / 200, y0 - gh * math.log10(p[n]) / 13) for n in range(1, nmax + 1)]
    draw_polyline(c, pts, paint((120, 180, 230), 1.0, stroke=4))
    draw_polyline(c, pts, paint((120, 180, 230), 0.4, stroke=12, blur=6))
    for n, label in ((10, "42"), (100, "190,569,292"), (200, "")):
        if nmax >= n:
            a = smooth((nmax - n) / 6 + 0.3)
            x, y = x0 + gw * n / 200, y0 - gh * math.log10(p[n]) / 13
            c.drawCircle(x, y, 9, paint(GOLD, a))
            if label:
                draw_text(c, f"p({n}) = {label}", x + 22, y - 22, font(NUM_B, 40), GOLD, a, shadow=6)
    # running counter
    draw_text(c, f"n = {nmax}", x0 + 60, y0 - gh + 60, font(NUM, 30), DIM, 0.9)
    draw_text(c, "p(n) = " + fmt_int(p[nmax]), x0 + 60, y0 - gh + 130, font(NUM_B, 58), CREAM, 0.95)
    master_fade(c, t, dur, 0.6, 0.7)


def partition_formula(c, t, dur, st):
    bg(c, glow=(55, 45, 30))
    img = formula(r"p(n)\;\sim\;\frac{1}{4n\sqrt{3}}\;e^{\pi\sqrt{2n/3}}", size=64)
    draw_image(c, img, W / 2, 250, h=img.height() * 0.75, a=smooth(t / 1.2), center=True)
    draw_text(c, "Hardy & Ramanujan, 1918", W / 2, 400, font(SERIF_I, 36), DIM, smooth((t - 1) / 1), align="center")
    a = smooth((t - dur * 0.38) / 1.0)
    draw_text(c, "p(200)", 420, 630, font(NUM_B, 60), CREAM, a, align="right")
    draw_text(c, "MacMahon, by hand:", 470, 560, font(SANS, 24, 500), DIM, a, tracking=2)
    draw_text(c, "3,972,999,029,388", 470, 630, font(NUM_B, 66), CREAM, a)
    b = (t - dur * 0.62) / (dur * 0.25)
    if b > 0:
        target = "3,972,999,029,388"
        rng = random.Random(int(t * 25))
        out = ""
        locked = int(len(target) * clamp(b))
        for i, ch in enumerate(target):
            out += ch if (i < locked or not ch.isdigit()) else str(rng.randint(0, 9))
        draw_text(c, "Hardy–Ramanujan formula:", 470, 760, font(SANS, 24, 500), DIM, smooth(b * 3), tracking=2)
        draw_text(c, out, 470, 830, font(NUM_B, 66), GOLD, smooth(b * 3), shadow=8)
        if b >= 1:
            draw_text(c, "✓ exact", 1250, 830, font(NUM_B, 52), (150, 210, 150), smooth((b - 1) * 4))
    master_fade(c, t, dur, 0.6, 0.7)


def partition_congruence(c, t, dur, st):
    bg(c, glow=(50, 40, 55))
    p = partitions_table()
    ns = [4, 9, 14, 19, 24, 29, 34, 39]
    draw_text(c, "n ends in 4 or 9", 420, 170, font(SANS, 26, 500), DIM, smooth((t - dur * 0.25) / 1), align="center",
              tracking=2)
    draw_text(c, "p(n)", 980, 170, font(SANS, 26, 500), DIM, smooth((t - dur * 0.25) / 1), align="center", tracking=2)
    for i, n in enumerate(ns):
        t0 = dur * 0.3 + i * dur * 0.045
        a = ease_out((t - t0) / 0.5)
        if a <= 0:
            continue
        y = 250 + i * 72
        draw_text(c, str(n), 420, y, font(NUM, 48), CREAM, a, align="center")
        draw_text(c, fmt_int(p[n]), 980, y, font(NUM, 48), CREAM, a, align="center")
        b = smooth((t - t0 - 0.8) / 0.5)
        draw_text(c, f"= 5 × {fmt_int(p[n] // 5)}", 1200, y, font(NUM, 42), GOLD, b)
    ca = smooth((t - dur * 0.78) / 1.0)
    for j, tex in enumerate([r"p(5k+4)\equiv 0\ (\mathrm{mod}\ 5)", r"p(7k+5)\equiv 0\ (\mathrm{mod}\ 7)",
                             r"p(11k+6)\equiv 0\ (\mathrm{mod}\ 11)"]):
        img = formula(tex, size=40, rgb=GOLD)
        aa = smooth((t - dur * 0.78 - j * 0.6) / 0.8)
        draw_image(c, img, 330 + j * 450, 870, h=img.height() * 0.5, a=aa)
    if ca > 0:
        c.drawRect(skia.Rect.MakeXYWH(300, 845, 1320, 1.5), paint(GOLD, 0.5 * ca))
    master_fade(c, t, dur, 0.6, 0.7)


def pi_series(c, t, dur, st):
    bg(c, glow=(40, 48, 70))
    img = formula(FORMULAS[0], size=54)
    draw_image(c, img, W / 2, 210, h=img.height() * 0.68, a=smooth(t / 1.2), center=True)
    if "approx" not in st:
        import mpmath
        mpmath.mp.dps = 80
        true = mpmath.nstr(mpmath.pi, 60, strip_zeros=False)
        acc = mpmath.mpf(0)
        rows = []
        for k in range(4):
            acc += mpmath.factorial(4 * k) * (1103 + 26390 * k) / (mpmath.factorial(k) ** 4 * mpmath.mpf(396) ** (4 * k))
            approx = 1 / (2 * mpmath.sqrt(2) / 9801 * acc)
            s = mpmath.nstr(approx, 60, strip_zeros=False)
            good = 0
            while good < len(s) and s[good] == true[good]:
                good += 1
            rows.append((s[:44], good))
        st["approx"] = rows
    f = font(TYPE, 38)
    cw = f.measureText("0") + 1
    for k, (s, good) in enumerate(st["approx"]):
        t0 = dur * 0.25 + k * dur * 0.13
        a = ease_out((t - t0) / 0.6)
        if a <= 0:
            continue
        y = 470 + k * 95
        draw_text(c, f"{k + 1} term" + ("s" if k else " "), 300, y, font(SANS, 26, 500), DIM, a, align="right",
                  tracking=1)
        x = 350
        for i, ch in enumerate(s):
            col = GOLD if i < good else (95, 95, 100)
            c.drawString(ch, x + i * cw, y, f, paint(col, a))
        draw_text(c, f"{max(good - 2, 0)} correct digits", 350 + 44 * cw + 30, y, font(SANS, 22, 500), GOLD, a * 0.9)
    b = smooth((t - dur * 0.8) / 1.0)
    draw_text(c, "1985:  17,526,100 digits of π", W / 2, H - 90, font(NUM_B, 50), CREAM, b, align="center",
              shadow=8)
    master_fade(c, t, dur, 0.6, 0.7)


def highly_composite(c, t, dur, st):
    bg(c, glow=(50, 45, 35))
    N = 400
    d = [0] * (N + 1)
    for i in range(1, N + 1):
        for j in range(i, N + 1, i):
            d[j] += 1
    rec, best = set(), 0
    for n in range(1, N + 1):
        if d[n] > best:
            best = d[n]
            rec.add(n)
    x0, y0, gw, gh = 180, 930, 1560, 640
    prog = ease_in_out((t - 0.3) / (dur * 0.65))
    nmax = int(N * prog)
    bw = gw / N
    for n in range(1, nmax + 1):
        h = gh * d[n] / 26
        col, a = (GOLD, 1.0) if n in rec else ((110, 130, 160), 0.55)
        c.drawRect(skia.Rect.MakeXYWH(x0 + (n - 1) * bw, y0 - h, max(bw - 0.6, 1), h), paint(col, a))
    for n in (12, 60, 360):
        if nmax >= n:
            a = smooth((nmax - n) / 10)
            x, y = x0 + (n - 0.5) * bw, y0 - gh * d[n] / 26
            draw_text(c, str(n), x, y - 50, font(NUM_B, 44), GOLD, a, align="center", shadow=6)
            draw_text(c, f"{d[n]} divisors", x, y - 18, font(SANS, 20, 500), CREAM, a, align="center")
    draw_text(c, "Highly composite numbers", W / 2, 140, font(SERIF, 64, 500), CREAM, smooth(t / 1), align="center")
    draw_text(c, "number of divisors of n, for n = 1 … 400", W / 2, 195, font(SANS, 24), DIM, smooth(t / 1),
              align="center", tracking=1)
    master_fade(c, t, dur, 0.6, 0.7)


def taxi1729(c, t, dur, st):
    c.clear(skia.Color(6, 7, 10))
    rng = random.Random(9)
    for i in range(26):  # drifting street-light bokeh
        x = (rng.uniform(0, W) + t * rng.uniform(-20, 20)) % W
        y = rng.uniform(0.1, 0.9) * H
        r = rng.uniform(30, 110)
        col = rng.choice([(240, 190, 110), (230, 160, 80), (180, 200, 230)])
        c.drawCircle(x, y, r, paint(col, rng.uniform(0.05, 0.16), blur=r * 0.4))
    u = ease_out(t / 3)
    c.save()
    c.translate(W / 2, H / 2)
    c.scale(0.9 + 0.1 * u, 0.9 + 0.1 * u)
    pw, ph = 900, 300
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-pw / 2 + 12, -ph / 2 + 18, pw, ph), 20, 20),
                paint((0, 0, 0), 0.7, blur=20))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-pw / 2, -ph / 2, pw, ph), 20, 20), paint((22, 22, 24)))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-pw / 2 + 14, -ph / 2 + 14, pw - 28, ph - 28), 14, 14),
                paint((210, 205, 190), 0.9, stroke=5))
    draw_text(c, "HACKNEY CARRIAGE", 0, -ph / 2 + 62, font(SANS, 26, 600), (210, 205, 190), 0.85, align="center",
              tracking=8)
    draw_text(c, "No. 1729", 0, ph / 2 - 60, font(NUM_B, 160), (236, 230, 214), smooth(t / 1.2), align="center",
              shadow=6)
    c.restore()
    master_fade(c, t, dur, 1.0, 0.8)


def _iso_cube(c, x, y, n, u, col, a):
    """Isometric cube of side n units (grid lines); (x, y) = bottom-front corner."""
    cx, cy = math.cos(math.pi / 6) * u, math.sin(math.pi / 6) * u
    L, R, U = (-cx, -cy), (cx, -cy), (0, -u)

    def P(i, j, k):  # i along L, j along R, k up
        return (x + L[0] * i + R[0] * j, y + L[1] * i + R[1] * j + U[1] * k)

    faces = [
        ([P(0, 0, 0), P(n, 0, 0), P(n, 0, n), P(0, 0, n)], 0.75),  # left face
        ([P(0, 0, 0), P(0, n, 0), P(0, n, n), P(0, 0, n)], 0.55),  # right face
        ([P(0, 0, n), P(n, 0, n), P(n, n, n), P(0, n, n)], 1.0),   # top face
    ]
    for pts, shade in faces:
        path = skia.Path()
        path.addPoly([skia.Point(*p) for p in pts], True)
        c.drawPath(path, paint(tuple(int(v * shade) for v in col), a))
    gp = paint((20, 20, 25), 0.35 * a, stroke=1.2 if n > 4 else 2)
    for s in range(n + 1):
        draw_polyline(c, [P(s, 0, 0), P(s, 0, n)], gp)
        draw_polyline(c, [P(0, 0, s), P(n, 0, s)], gp)
        draw_polyline(c, [P(0, s, 0), P(0, s, n)], gp)
        draw_polyline(c, [P(0, 0, s), P(0, n, s)], gp)
        draw_polyline(c, [P(s, 0, n), P(s, n, n)], gp)
        draw_polyline(c, [P(0, s, n), P(n, s, n)], gp)


def cubes1729(c, t, dur, st):
    bg(c, glow=(50, 45, 40))
    u = 20
    a1 = ease_out((t - 0.3) / 1.0)
    a2 = ease_out((t - dur * 0.25) / 1.0)
    # left pair: 1^3 + 12^3
    _iso_cube(c, 300, 700, 1, u, (230, 180, 90), a1)
    draw_text(c, "+", 375, 700, font(SERIF, 70, 400), CREAM, a1, align="center")
    _iso_cube(c, 640, 760, 12, u, (230, 180, 90), a1)
    draw_text(c, "1³ + 12³", 520, 870, font(NUM, 58), CREAM, a1, align="center")
    draw_text(c, "1 + 1728", 520, 935, font(NUM, 32), DIM, a1, align="center")
    # right pair: 9^3 + 10^3
    _iso_cube(c, 1240, 760, 9, u, (120, 170, 220), a2)
    draw_text(c, "+", 1412, 700, font(SERIF, 70, 400), CREAM, a2, align="center")
    _iso_cube(c, 1600, 760, 10, u, (120, 170, 220), a2)
    draw_text(c, "9³ + 10³", 1420, 870, font(NUM, 58), CREAM, a2, align="center")
    draw_text(c, "729 + 1000", 1420, 935, font(NUM, 32), DIM, a2, align="center")
    a3 = smooth((t - dur * 0.45) / 1.0)
    draw_text(c, "1729", W / 2, 200, font(NUM_B, 140), GOLD, a3, align="center", shadow=12)
    draw_text(c, "the smallest number that is the sum of two cubes in two different ways", W / 2, 270,
              font(SERIF_I, 36), CREAM, smooth((t - dur * 0.55) / 1.0), align="center")
    master_fade(c, t, dur, 0.6, 0.8)


# ----------------------------------------------------------------------------- mock theta
@functools.lru_cache(maxsize=1)
def mock_theta_image(size=1100):
    """Phase portrait of Ramanujan's mock theta function f(q) on the unit disc (cached PNG)."""
    path = os.path.join(os.environ.get("DOC_CACHE", "/tmp"), f"mock_theta_v2_{size}.png")
    if os.path.exists(path):
        return cv2.imread(path, cv2.IMREAD_UNCHANGED)
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import colormaps
    y, x = np.mgrid[-1:1:size * 1j, -1:1:size * 1j]
    q = (x + 1j * y) * 0.993
    r = np.abs(q)
    inside = r < 0.993
    q = np.where(inside, q, 0)
    with np.errstate(all="ignore"):
        f = np.ones_like(q)
        den = np.ones_like(q)
        for n in range(1, 120):
            den = den * (1 + q ** n) ** 2
            f = f + q ** (n * n) / den
        f = np.nan_to_num(f, nan=0.0, posinf=1e6, neginf=-1e6)
    phase = (np.angle(f) / (2 * np.pi)) % 1.0
    rgb = colormaps["twilight_shifted"](phase)[..., :3]
    lm = np.log2(np.abs(f) + 1e-9)
    band = lm * 2 - np.floor(lm * 2)
    shade = 0.62 + 0.38 * band ** 0.6
    iso = np.abs(((phase * 12) % 1.0) - 0.5) * 2  # 12 phase lines
    shade *= 0.75 + 0.25 * np.clip(iso * 6, 0, 1)
    rgb = np.clip(rgb * shade[..., None], 0, 1)
    bgr = (rgb[..., ::-1] * 255).astype(np.uint8)
    alpha = (np.clip((0.993 - np.hypot(x, y) * 0.993) * 500, 0, 1) * 255).astype(np.uint8)
    img = np.dstack([bgr, alpha])
    cv2.imwrite(path, img)
    return img


def mock_theta(c, t, dur, st):
    bg(c, top=(8, 8, 14), bottom=(2, 2, 4), glow=(40, 30, 60))
    if "img" not in st:
        st["img"] = skia_image_from_bgra(mock_theta_image())
    img = st["img"]
    u = t / dur
    c.save()
    c.translate(W * 0.29, H / 2)
    c.rotate(u * 25)
    s = 0.9 + 0.12 * ease_in_out(u)
    size = 820 * s
    c.drawCircle(0, 0, size / 2 + 6, paint((120, 100, 180), 0.25, blur=40))
    draw_image(c, img, -size / 2, -size / 2, w=size, h=size, a=smooth(t / 1.5))
    c.restore()
    a = smooth((t - 1) / 1.2)
    draw_text(c, "A mock theta function", 1390, 330, font(SERIF, 60, 500), CREAM, a, align="center")
    fimg = formula(r"f(q)=\sum_{n=0}^{\infty}\frac{q^{n^2}}{(1+q)^2(1+q^2)^2\cdots(1+q^n)^2}", size=44)
    draw_image(c, fimg, 1390, 470, h=fimg.height() * 0.5, a=a, center=True)
    draw_text(c, "plotted for complex q inside the unit disc", 1390, 600, font(SERIF_I, 32), DIM,
              smooth((t - 2) / 1.2), align="center")
    draw_text(c, "colour = phase   ·   bands = magnitude", 1390, 650, font(SANS, 22, 400), DIM,
              smooth((t - 2.5) / 1.2), align="center", tracking=2)
    master_fade(c, t, dur, 0.8, 0.8)


def candle(c, t, dur, st, name="Srinivasa Ramanujan", dates="22 December 1887  –  26 April 1920"):
    c.clear(skia.Color(3, 3, 4))
    fl = 1 + 0.06 * math.sin(t * 11) + 0.04 * math.sin(t * 17.3 + 1) + 0.03 * math.sin(t * 5.1)
    cx, cy = W / 2, H * 0.52
    c.drawPaint(skia.Paint(Shader=skia.GradientShader.MakeRadial(
        center=(cx, cy - 40), radius=620 * fl, colors=[skia.Color(120, 70, 25, 120), skia.Color(0, 0, 0, 0)])))
    # lamp (diya)
    lamp = skia.Path()
    lamp.moveTo(cx - 150, cy + 40)
    lamp.quadTo(cx, cy + 170, cx + 150, cy + 40)
    lamp.quadTo(cx + 175, cy + 30, cx + 205, cy + 5)
    lamp.quadTo(cx + 120, cy + 60, cx - 150, cy + 40)
    lamp.close()
    c.drawPath(lamp, paint((105, 58, 32)))
    c.drawPath(lamp, paint((180, 110, 60), 0.5, stroke=2))
    sway = math.sin(t * 2.1) * 6 + math.sin(t * 7.7) * 2
    fx, fy = cx + 175, cy - 8
    flame = skia.Path()
    hgt = 120 * fl
    flame.moveTo(fx - 22, fy)
    flame.cubicTo(fx - 30, fy - hgt * 0.5, fx + sway, fy - hgt * 0.8, fx + sway * 1.5, fy - hgt)
    flame.cubicTo(fx + sway + 10, fy - hgt * 0.8, fx + 32, fy - hgt * 0.45, fx + 22, fy)
    flame.close()
    c.drawPath(flame, paint((255, 170, 60), 0.5, blur=26))
    c.drawPath(flame, paint((255, 205, 120), 0.95, blur=3))
    c.drawCircle(fx + sway * 0.3, fy - hgt * 0.3, 10, paint((255, 250, 235), 0.9, blur=6))
    a = smooth((t - 2.0) / 2.0)
    draw_text(c, name, W / 2, H * 0.2, font(SERIF, 76, 500), CREAM, a, align="center", shadow=8)
    draw_text(c, dates, W / 2, H * 0.2 + 70, font(NUM_I, 38), GOLD, a * 0.9, align="center")
    master_fade(c, t, dur, 1.5, 1.5)


def legacy_names(c, t, dur, st):
    bg(c, top=(10, 12, 20), bottom=(3, 3, 6), glow=(40, 45, 70))
    if "g" not in st:
        rng = random.Random(4)
        n = 40
        while True:  # random 3-regular graph via pairing
            stubs = [i for i in range(n) for _ in range(3)]
            rng.shuffle(stubs)
            edges = set()
            ok = True
            for i in range(0, len(stubs), 2):
                a, b = sorted((stubs[i], stubs[i + 1]))
                if a == b or (a, b) in edges:
                    ok = False
                    break
                edges.add((a, b))
            if ok:
                break
        st["g"] = (n, sorted(edges))
    n, edges = st["g"]
    rot = t * 4
    R = 330
    pts = [(W / 2 + R * math.cos(math.radians(rot + 360 * i / n)), H / 2 + R * math.sin(math.radians(rot + 360 * i / n)))
           for i in range(n)]
    ga = smooth(t / 2) * 0.55
    for k, (a, b) in enumerate(edges):
        p = ease_out((t - 0.3 - k * 0.04) / 1.0)
        if p <= 0:
            continue
        ax, ay = pts[a]
        bx, by = pts[b]
        draw_polyline(c, [(ax, ay), (ax + (bx - ax) * p, ay + (by - ay) * p)], paint((120, 160, 230), ga, stroke=1.6))
    for (x, y) in pts:
        c.drawCircle(x, y, 6, paint(GOLD, smooth(t / 1.5)))
    names = ["Ramanujan graphs", "Ramanujan tau function", "The Ramanujan conjecture", "Hardy–Ramanujan number  1729",
             "Rogers–Ramanujan identities", "Mock theta functions", "Ramanujan sums", "Ramanujan's master theorem"]
    spots = [(0.2, 0.14), (0.8, 0.14), (0.17, 0.4), (0.83, 0.4), (0.17, 0.66), (0.83, 0.66), (0.3, 0.92), (0.7, 0.92)]
    for i, (nm, (sx, sy)) in enumerate(zip(names, spots)):
        a = smooth((t - 0.8 - i * dur * 0.09) / 1.0)
        draw_text(c, nm, sx * W, sy * H, font(SERIF, 42, 500), CREAM, a, align="center", shadow=8)
    master_fade(c, t, dur, 0.7, 0.8)


def hardy_scale(c, t, dur, st):
    bg(c, glow=(55, 45, 30))
    draw_text(c, "Hardy's scale of natural mathematical talent", W / 2, 150, font(SERIF, 60, 500), CREAM,
              smooth(t / 1), align="center")
    rows = [("G. H. Hardy", 25), ("J. E. Littlewood", 30), ("David Hilbert", 80), ("Srinivasa Ramanujan", 100)]
    x0, bwmax = 640, 1000
    for i, (nm, v) in enumerate(rows):
        t0 = dur * (0.2 + i * 0.17)
        p = ease_out((t - t0) / 1.4)
        if p <= 0:
            continue
        y = 330 + i * 150
        col = GOLD if v == 100 else (120, 150, 190)
        draw_text(c, nm, x0 - 30, y + 48, font(SERIF, 46, 500), CREAM, smooth(p * 2), align="right")
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x0, y, bwmax * v / 100 * p, 70), 6, 6), paint(col, 0.9))
        draw_text(c, str(int(round(v * p))), x0 + bwmax * v / 100 * p + 20, y + 54, font(NUM_B, 50), col,
                  smooth(p * 2))
    master_fade(c, t, dur, 0.6, 0.8)


def infinity(c, t, dur, st):
    bg(c, top=(8, 9, 14), bottom=(2, 2, 4), glow=(70, 52, 28))
    pts = []
    for i in range(400):
        s = 2 * math.pi * i / 399
        d = 1 + math.sin(s) ** 2
        pts.append((W / 2 + 420 * math.cos(s) / d, H / 2 + 420 * math.sin(s) * math.cos(s) / d))
    prog = ease_in_out((t - 0.5) / (dur * 0.6))
    part = polyline_partial(pts, prog)
    draw_polyline(c, part, paint(GOLD, 0.35, stroke=26, blur=18))
    draw_polyline(c, part, paint((255, 225, 160), 0.95, stroke=7))
    master_fade(c, t, dur, 0.8, 2.0)


def credits(c, t, dur, st, lines=()):
    c.clear(skia.Color(4, 4, 6))
    y = H + 40 - (t / dur) * (len(lines) * 50 + H + 100)
    for kind, txt in lines:
        if kind == "h":
            f, col, gap = font(SERIF, 52, 600), GOLD, 80
        elif kind == "s":
            f, col, gap = font(SANS, 24, 600), GOLD, 50
        elif kind == "sp":
            y += 40
            continue
        else:
            f, col, gap = font(SERIF, 30, 400), CREAM, 42
        if -60 < y < H + 60:
            for k, ln in enumerate(wrap(txt, f, 1500)):
                draw_text(c, ln, W / 2, y + k * gap * 0.9, f, col, 0.95, align="center")
            y += gap * 0.9 * (len(wrap(txt, f, 1500)) - 1)
        y += gap
    master_fade(c, t, dur, 1.0, 1.5)


# ----------------------------------------------------------------------------- maps
GEO = os.path.join(ASSETS, "geo")


@functools.lru_cache(maxsize=1)
def _geo():
    land = json.load(open(os.path.join(GEO, "countries.geojson")))
    polys = []
    for f in land["features"]:
        g = f["geometry"]
        rings = g["coordinates"] if g["type"] == "Polygon" else [r for p in g["coordinates"] for r in p]
        if g["type"] == "Polygon":
            rings = [g["coordinates"][0]]
        else:
            rings = [p[0] for p in g["coordinates"]]
        for r in rings:
            polys.append(np.asarray(r, np.float64))
    rivers = []
    rv = json.load(open(os.path.join(GEO, "rivers10.geojson")))
    for f in rv["features"]:
        nm = f["properties"].get("name") or ""
        if nm not in ("Cauvery", "Krishna", "Godavari", "Ganges", "Thames", "Nile", "Indus"):
            continue
        g = f["geometry"]
        lines = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        for ln in lines:
            rivers.append((nm, np.asarray(ln, np.float64)))
    return polys, rivers


class MapView:
    def __init__(self, lon0, lon1, lat0, lat1, ox=0, oy=0, w=W, h=H):
        self.lon0, self.lon1, self.lat0, self.lat1 = lon0, lon1, lat0, lat1
        self.ox, self.oy, self.w, self.h = ox, oy, w, h
        mid = math.radians((lat0 + lat1) / 2)
        self.k = math.cos(mid)
        # keep aspect: fit bbox into w x h
        sx = w / ((lon1 - lon0) * self.k)
        sy = h / (self._mercy(lat1) - self._mercy(lat0))
        self.s = min(sx, sy)
        self.cx = (lon0 + lon1) / 2
        self.cy = (self._mercy(lat0) + self._mercy(lat1)) / 2

    def _mercy(self, lat):
        return math.degrees(math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))) * self.k if False else \
            math.degrees(math.log(math.tan(math.pi / 4 + math.radians(clamp(lat, -85, 85)) / 2)))

    def xy(self, lon, lat):
        x = self.ox + self.w / 2 + (lon - self.cx) * self.s * self.k
        y = self.oy + self.h / 2 - (self._mercy(lat) - self.cy) * self.s
        return x, y

    def xy_arr(self, a):
        lat = np.clip(a[:, 1], -85, 85)
        my = np.degrees(np.log(np.tan(np.pi / 4 + np.radians(lat) / 2)))
        x = self.ox + self.w / 2 + (a[:, 0] - self.cx) * self.s * self.k
        y = self.oy + self.h / 2 - (my - self.cy) * self.s
        return np.stack([x, y], 1)


SEA = (22, 38, 52)
LAND = (196, 178, 140)


def render_map(view, scale=1.0, rivers=True):
    """Pre-render a base map (BGR numpy) for `view`, at `scale` x resolution."""
    w, h = int(view.w * scale), int(view.h * scale)
    v = MapView(view.lon0, view.lon1, view.lat0, view.lat1, 0, 0, w, h)
    surf = skia.Surface(w, h)
    c = surf.getCanvas()
    c.clear(skia.Color(*SEA))
    polys, rv = _geo()
    lp = paint(LAND)
    bp = paint((120, 100, 75), 0.6, stroke=1.2 * scale)
    lon_pad = (view.lon1 - view.lon0) * 0.6
    lat_pad = (view.lat1 - view.lat0) * 0.6
    for pts in polys:
        if (pts[:, 0].max() < view.lon0 - lon_pad or pts[:, 0].min() > view.lon1 + lon_pad or
                pts[:, 1].max() < view.lat0 - lat_pad or pts[:, 1].min() > view.lat1 + lat_pad):
            continue
        xy = v.xy_arr(pts)
        path = skia.Path()
        path.addPoly([skia.Point(float(x), float(y)) for x, y in xy], True)
        c.drawPath(path, lp)
        c.drawPath(path, bp)
    if rivers:
        rp = paint((70, 110, 140), 0.85, stroke=2.2 * scale)
        for nm, ln in rv:
            xy = v.xy_arr(ln)
            draw_polyline(c, xy, rp)
    arr = surf.makeImageSnapshot().toarray()[..., :3].copy()
    # paper texture
    tex = np.random.default_rng(2).normal(0, 1, (h // 3, w // 3)).astype(np.float32)
    tex = cv2.resize(tex, (w, h))
    arr = np.clip(arr.astype(np.float32) + tex[..., None] * 6, 0, 255).astype(np.uint8)
    return arr


def _pin(c, x, y, label, a, side="right", size=40, col=GOLD):
    if a <= 0:
        return
    c.drawCircle(x, y, 22 * a, paint(col, 0.25 * a, blur=8))
    c.drawCircle(x, y, 9, paint(col, a))
    c.drawCircle(x, y, 9, paint((40, 30, 20), a, stroke=2))
    f = font(SERIF, size, 600)
    if side == "right":
        draw_text(c, label, x + 22, y + 12, f, (250, 244, 230), a, shadow=6)
    else:
        draw_text(c, label, x - 22, y + 12, f, (250, 244, 230), a, align="right", shadow=6)


def map_erode(c, t, dur, st):
    if "base" not in st:
        st["view"] = MapView(66.0, 93.0, 5.0, 31.0)
        st["base"] = render_map(st["view"], scale=3.0)
    base = st["base"]
    view = st["view"]
    z = 1 + 2.4 * ease_in_out((t - 1.0) / (dur * 0.55))
    # zoom toward Tamil Nadu
    tx, ty = view.xy(78.6, 11.6)
    fx = W / 2 + (tx - W / 2) * smooth((t - 1) / (dur * 0.55))
    fy = H / 2 + (ty - H / 2) * smooth((t - 1) / (dur * 0.55))
    k = z / 3.0
    M = np.array([[k, 0, W / 2 - k * fx * 3.0], [0, k, H / 2 - k * fy * 3.0]], np.float32)
    img = cv2.warpAffine(base, M, (W, H), flags=cv2.INTER_AREA)
    alpha = np.full((H, W, 1), 255, np.uint8)
    sk = skia_image_from_bgra(np.concatenate([img, alpha], 2))
    c.drawImage(sk, 0, 0)

    def P(lon, lat):
        x, y = view.xy(lon, lat)
        return W / 2 + (x - fx) * z, H / 2 + (y - fy) * z

    a0 = smooth((t - 0.3) / 1.0) * (1 - smooth((t - 1.6) / 0.8))
    draw_text(c, "BRITISH INDIA", *P(79.5, 23.0), font(SERIF, 54, 600), (60, 45, 30), a0 * 0.8, align="center",
              tracking=10)
    zt = dur * 0.55 + 1
    _pin(c, *P(77.72, 11.34), "Erode", smooth((t - zt) / 0.8), side="left")
    _pin(c, *P(79.39, 10.96), "Kumbakonam", smooth((t - zt - 0.8) / 0.8))
    _pin(c, *P(80.27, 13.08), "Madras", smooth((t - zt - 1.6) / 0.8))
    ka = smooth((t - zt - 2.4) / 1.0)
    draw_text(c, "Kaveri river", *P(78.4, 10.45), font(SERIF_I, 34), (40, 75, 105), ka * 0.95, align="center")
    draw_text(c, "MADRAS PRESIDENCY", *P(78.3, 12.6), font(SERIF, 38, 600), (70, 52, 34), ka * 0.85, align="center",
              tracking=6)
    master_fade(c, t, dur, 0.8, 0.8)


VOYAGE = [(80.29, 13.08), (80.9, 10.5), (81.9, 7.2), (80.6, 5.6), (79.8, 6.9), (76.5, 8.0), (70.0, 11.5),
          (60.0, 13.0), (51.5, 12.3), (45.0, 12.6), (43.4, 12.6), (38.5, 19.5), (34.5, 26.5), (32.55, 29.9),
          (32.3, 31.3), (28.0, 33.3), (20.0, 35.0), (14.5, 36.4), (10.5, 37.6), (5.0, 37.4), (-2.0, 36.4),
          (-5.6, 35.95), (-9.6, 37.0), (-9.9, 43.2), (-5.5, 47.5), (-4.0, 49.6), (0.5, 50.4), (1.6, 51.15),
          (0.6, 51.47), (0.05, 51.5)]
RETURN = [(0.05, 51.5), (0.6, 51.47), (1.6, 51.15), (0.5, 50.4), (-4.0, 49.6), (-5.5, 47.5), (-9.9, 43.2),
          (-9.6, 37.0), (-5.6, 35.95), (-2.0, 36.4), (5.0, 37.4), (10.5, 37.6), (14.5, 36.4), (20.0, 35.0),
          (28.0, 33.3), (32.3, 31.3), (32.55, 29.9), (34.5, 26.5), (38.5, 19.5), (43.4, 12.6), (45.0, 12.6),
          (51.5, 13.5), (62.0, 17.0), (72.83, 18.94)]


def _route_map(c, t, dur, st, route, start, end, d0, d1, overland=None):
    if "base" not in st:
        st["view"] = MapView(-14.0, 92.0, 0.0, 58.0)
        st["base"] = render_map(st["view"], scale=1.2, rivers=False)
    view = st["view"]
    base = st["base"]
    u = ease_in_out(t / dur)
    k = (1.0 + 0.05 * u) / 1.2
    fx, fy = W / 2 * 1.2, H / 2 * 1.2
    M = np.array([[k, 0, W / 2 - k * fx], [0, k, H / 2 - k * fy]], np.float32)
    img = cv2.warpAffine(base, M, (W, H), flags=cv2.INTER_AREA)
    sk = skia_image_from_bgra(np.concatenate([img, np.full((H, W, 1), 255, np.uint8)], 2))
    c.drawImage(sk, 0, 0)
    zz = 1.0 + 0.05 * u

    def P(lon, lat):
        x, y = view.xy(lon, lat)
        return W / 2 + (x - W / 2) * zz, H / 2 + (y - H / 2) * zz

    pts = [P(*p) for p in route]
    prog = ease_in_out((t - 1.5) / (dur * 0.7))
    part = polyline_partial(pts, prog)
    dash = paint((250, 240, 220), 0.9, stroke=4)
    dash.setPathEffect(skia.DashPathEffect.Make([14, 10], 0))
    draw_polyline(c, part, dash)
    if prog > 0:
        x, y = part[-1]
        c.drawCircle(x, y, 16, paint((255, 235, 190), 0.4, blur=8))
        c.drawCircle(x, y, 8, paint((255, 240, 210), 1.0))
    if overland and prog >= 1:
        q = ease_in_out((t - 1.5 - dur * 0.7) / 1.5)
        op = [P(*p) for p in overland]
        rail = paint(GOLD, 0.95, stroke=4)
        rail.setPathEffect(skia.DashPathEffect.Make([4, 8], 0))
        draw_polyline(c, polyline_partial(op, q), rail)
    _pin(c, *pts[0], start, smooth((t - 0.4) / 0.8), side="left" if route[0][0] > 40 else "right", size=44)
    draw_text(c, d0, pts[0][0] + (-22 if route[0][0] > 40 else 22), pts[0][1] + 52, font(SERIF_I, 32), CREAM,
              smooth((t - 0.8) / 0.8), align="right" if route[0][0] > 40 else "left", shadow=6)
    ea = smooth((t - 1.5 - dur * 0.7) / 0.8)
    endpt = P(*(overland[-1] if overland else route[-1]))
    right = (overland[-1] if overland else route[-1])[0] > 40
    _pin(c, *endpt, end, ea, side="left" if not right else "right", size=44)
    draw_text(c, d1, endpt[0] + (22 if right else -22), endpt[1] + 52, font(SERIF_I, 32), CREAM, ea,
              align="left" if right else "right", shadow=6)
    master_fade(c, t, dur, 0.8, 0.8)


def map_voyage(c, t, dur, st):
    _route_map(c, t, dur, st, VOYAGE, "Madras", "London", "17 March 1914", "April 1914")


def map_return(c, t, dur, st):
    _route_map(c, t, dur, st, RETURN, "London", "Madras", "February 1919", "March 1919",
               overland=[(72.83, 18.94), (75.0, 17.5), (78.5, 15.0), (80.27, 13.08)])


REGISTRY = {
    "title": title, "chapter": chapter_card, "letter_envelope": letter_envelope, "letter_text": letter_text,
    "letter_mock": letter_text, "formula_wall": formula_wall, "digits_pi": digits_pi, "slate": slate,
    "nested_radical": nested_radical, "continued_fraction": continued_fraction, "partitions4": partitions4,
    "partition_growth": partition_growth, "partition_formula": partition_formula,
    "partition_congruence": partition_congruence, "pi_series": pi_series, "highly_composite": highly_composite,
    "taxi1729": taxi1729, "cubes1729": cubes1729, "mock_theta": mock_theta, "candle": candle,
    "legacy_names": legacy_names, "hardy_scale": hardy_scale, "infinity": infinity, "credits": credits,
    "map_erode": map_erode, "map_voyage": map_voyage, "map_return": map_return,
}
