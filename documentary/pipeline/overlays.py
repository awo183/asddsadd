"""On-picture graphics placed over footage: kinetic words, place/date tags, dosimeter, countdown.

Every overlay is a dict in a shot's "overlays" list and is drawn on an RGBA layer.
Times (t0/t1) are shot-local seconds.
"""
import math
from PIL import Image, ImageDraw, ImageFilter

from common import (W, H, Draw, INK, DIM, URANIUM, AMBER, RED, font, ramp, ease_out, ease, lerp, with_alpha,
                    text_center)


def _window(lt, t0, t1, fin=0.25, fout=0.3):
    return ramp(lt, t0, t0 + fin) * (1 - ramp(lt, t1 - fout, t1))


def _shadowed_text(layer, xy, text, fnt, color, a, anchor="mm", blur=10, tracking=0):
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    text_center(Draw(sh), (xy[0] + 4, xy[1] + 6), text, fnt, (0, 0, 0, int(200 * a)), anchor=anchor, tracking=tracking)
    layer.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    text_center(Draw(layer), xy, text, fnt, with_alpha(color, a), anchor=anchor, tracking=tracking)


def words(layer, lt, o):
    t0, t1 = o.get("t0", 0.3), o.get("t1", o.get("t0", 0.3) + 2.2)
    if lt < t0 or lt > t1:
        return
    a = _window(lt, t0, t1)
    style = o.get("style", "big")
    pos = {"center": (W / 2, H / 2), "low": (W / 2, H * 0.78), "top": (W / 2, H * 0.2),
           "left": (W * 0.3, H / 2), "right": (W * 0.7, H / 2)}[o.get("pos", "center")]
    color = {"ink": INK, "uranium": URANIUM, "amber": AMBER, "red": RED}[o.get("color", "ink")]
    text = o["text"]
    if style == "big":
        s = lerp(1.18, 1.0, ease_out(min(1, (lt - t0) / 0.35)))
        size = int(o.get("size", 190) * s)
        _shadowed_text(layer, pos, text, font("display", size), color, a, tracking=int(6 * s))
    elif style == "stamp":
        k = ease_out(min(1, (lt - t0) / 0.18))
        sc = lerp(1.9, 1.0, k)
        size = o.get("size", 130)
        f = font("display", size)
        tw = int(Draw(layer).textlength(text, font=f)) + 80
        st = Image.new("RGBA", (tw, size + 60), (0, 0, 0, 0))
        sd = Draw(st)
        col = (196, 36, 32)
        sd.rounded_rectangle([6, 6, tw - 6, size + 54], 14, outline=col + (235,), width=9)
        sd.text((tw / 2, (size + 60) / 2 + 4), text, font=f, fill=col + (235,), anchor="mm")
        st = st.resize((max(1, int(tw * sc)), max(1, int((size + 60) * sc))), Image.BICUBIC)
        st = st.rotate(o.get("angle", -8), expand=True, resample=Image.BICUBIC)
        st.putalpha(st.getchannel("A").point(lambda v: int(v * a * min(1, k * 1.5))))
        layer.alpha_composite(st, (int(pos[0] - st.width / 2), int(pos[1] - st.height / 2)))
    elif style == "type":
        n = int(max(0, lt - t0) * o.get("cps", 26))
        f = font("mono", o.get("size", 58))
        shown = text[:n]
        d = Draw(layer)
        full = d.textlength(text, font=f)
        x = pos[0] - full / 2
        d.rectangle([x - 26, pos[1] - 52, x + full + 26, pos[1] + 48], fill=(0, 0, 0, int(150 * a)))
        d.text((x, pos[1]), shown, font=f, fill=with_alpha(INK, a), anchor="lm")
        if n < len(text) and int(lt * 3) % 2 == 0:
            cx = x + d.textlength(shown, font=f)
            d.rectangle([cx + 4, pos[1] - 26, cx + 22, pos[1] + 26], fill=with_alpha(URANIUM, a))
    elif style == "count":
        k = ease_out(min(1, (lt - t0) / o.get("count_dur", 1.6)))
        v = int(round(o["value"] * k / o.get("step", 1)) * o.get("step", 1))
        txt = o.get("fmt", "{:,}").format(v).replace(",", " ")
        _shadowed_text(layer, pos, txt, font("display", o.get("size", 220)), color, a)
        if o.get("sub"):
            _shadowed_text(layer, (pos[0], pos[1] + o.get("size", 220) * 0.78), o["sub"], font("serif", 54), INK, a,
                           blur=6)
    elif style == "quote":
        f = font("serif_i", o.get("size", 64))
        d = Draw(layer)
        from common import wrap
        lines = wrap(d, text, f, W * 0.7)
        y = pos[1] - (len(lines) - 1) * o.get("size", 64) * 0.62
        for line in lines:
            _shadowed_text(layer, (pos[0], y), line, f, color, a, blur=8)
            y += o.get("size", 64) * 1.25


def tag(layer, lt, o):
    """Typewriter place/date tag, top-left — shown only when the place or year changes."""
    t0, t1 = o.get("t0", 0.25), o.get("t1", 3.8)
    if lt < t0 or lt > t1:
        return
    a = _window(lt, t0, t1, 0.2, 0.5)
    d = Draw(layer)
    f = font("mono", 40)
    text = o["text"]
    n = int((lt - t0) * 30)
    shown = text[:n]
    x, y = 86, 92
    full = d.textlength(text, font=f)
    d.rectangle([x - 18, y - 34, x + full + 22, y + 30], fill=(0, 0, 0, int(140 * a)))
    d.rectangle([x - 18, y - 34, x - 12, y + 30], fill=with_alpha(URANIUM, a))
    d.text((x, y), shown, font=f, fill=with_alpha(INK, a), anchor="lm")


def illustrative(layer, lt, o):
    d = Draw(layer)
    d.text((W - 56, H - 48), o.get("text", "ilustrační záběr"), font=font("sans", 24),
           fill=(230, 226, 214, 150), anchor="rs")


def dosimeter(layer, lt, o):
    t0, t1 = o.get("t0", 0.3), o.get("t1", 99)
    if lt < t0 or lt > t1:
        return
    a = _window(lt, t0, t1, 0.4, 0.5)
    lvl = lerp(o.get("l0", 0.2), o.get("l1", 0.9), ease(min(1, (lt - t0) / o.get("rise", 4.0))))
    lvl += 0.04 * math.sin(lt * 23) * math.sin(lt * 7)
    cx, cy, r = W - 230, H - 210, 150
    d = Draw(layer)
    d.rounded_rectangle([cx - r - 30, cy - r - 30, cx + r + 30, cy + 90], 22, fill=(18, 20, 20, int(215 * a)),
                        outline=with_alpha(DIM, a * 0.8), width=3)
    for i in range(11):
        ang = math.radians(200 - i * 22)
        x0, y0 = cx + math.cos(ang) * (r - 8), cy - math.sin(ang) * (r - 8)
        x1, y1 = cx + math.cos(ang) * (r - 30), cy - math.sin(ang) * (r - 30)
        col = URANIUM if i < 6 else (AMBER if i < 9 else RED)
        d.line([(x0, y0), (x1, y1)], fill=with_alpha(col, a), width=5)
    ang = math.radians(200 - max(0, min(1, lvl)) * 220)
    d.line([(cx, cy), (cx + math.cos(ang) * (r - 20), cy - math.sin(ang) * (r - 20))], fill=with_alpha(INK, a), width=6)
    d.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=with_alpha(INK, a))
    d.text((cx, cy + 56), o.get("label", "RADIACE"), font=font("oswald", 34, 700), fill=with_alpha(DIM, a), anchor="mm")
    if lvl > 0.75 and int(lt * 4) % 2 == 0:
        d.ellipse([cx + r - 10, cy - r - 10, cx + r + 10, cy - r + 10], fill=with_alpha(RED, a))


def countdown(layer, lt, o):
    start, step, t0 = o.get("from", 5), o.get("step", 1.0), o.get("t0", 0.0)
    k = int((lt - t0) // step)
    if lt < t0 or k >= start:
        return
    num = start - k
    u = ((lt - t0) % step) / step
    a = 1 - ease(max(0, u - 0.7) / 0.3)
    s = lerp(1.25, 1.0, ease_out(min(1, u / 0.2)))
    _shadowed_text(layer, (W / 2, H / 2), str(num), font("display", int(330 * s)), INK, a, blur=14)
    d = Draw(layer)
    r = 250
    d.arc([W / 2 - r, H / 2 - r, W / 2 + r, H / 2 + r], -90, -90 + 360 * u, fill=with_alpha(URANIUM, 0.9), width=8)


KINDS = {"words": words, "tag": tag, "illustrative": illustrative, "dosimeter": dosimeter, "countdown": countdown}


def draw_overlays(im, lt, overlays):
    if not overlays:
        return im
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for o in overlays:
        KINDS[o["kind"]](layer, lt, o)
    if layer.getbbox() is None:
        return im
    out = im.convert("RGBA")
    out.alpha_composite(layer)
    return out.convert("RGB")
