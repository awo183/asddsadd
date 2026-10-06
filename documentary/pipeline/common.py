"""Shared constants and drawing helpers for the documentary renderer."""
import functools, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 25
HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.environ.get("DOC_BUILD", os.path.join(HERE, "..", "build"))
ASSETS = os.path.join(BUILD, "assets")
FONTS = os.path.join(BUILD, "fonts")
GEO = os.path.join(BUILD, "geo")

# Palette: charcoal, bone-white text, uranium-glass green, amber, Soviet red.
BG = (13, 14, 15)
BG2 = (24, 26, 27)
INK = (236, 230, 218)
DIM = (150, 146, 138)
URANIUM = (155, 226, 60)
AMBER = (224, 164, 58)
RED = (196, 48, 40)
STEEL = (92, 104, 112)


# Typography: stencil display face (like the markings on ore crates and military kit) for
# titles and figures, a condensed industrial sans for labels, typewriter faces for dates,
# documents and archive captions, and a book serif for supporting lines.
FONT_FILES = {
    "display": ("BigShouldersStencilDisplay.ttf", 800),
    "oswald": ("BigShouldersDisplay.ttf", 600),
    "serif": ("SourceSerif4.ttf", 400),
    "serif_i": ("SourceSerif4-Italic.ttf", 400),
    "playfair": ("PlayfairDisplay.ttf", 500),
    "sans": ("CourierPrime-Regular.ttf", None),
    "plex": ("IBMPlexSans.ttf", 400),  # has Cyrillic, for credits
    "mono": ("SpecialElite-Regular.ttf", None),
    "type": ("SpecialElite-Regular.ttf", None),
}


@functools.lru_cache(maxsize=None)
def font(name, size, weight=None):
    path, default_weight = FONT_FILES[name]
    weight = weight if weight is not None else default_weight
    f = ImageFont.truetype(os.path.join(FONTS, path), size)
    if weight is not None:
        try:
            axes = f.get_variation_axes()
            vals = []
            for a in axes:
                nm = a.get("name", b"")
                nm = nm.decode() if isinstance(nm, bytes) else nm
                if nm.lower() == "weight":
                    vals.append(min(max(weight, a["minimum"]), a["maximum"]))
                elif nm.lower() in ("optical size", "opsz"):
                    vals.append(min(max(size * 0.75, a["minimum"]), a["maximum"]))
                else:
                    vals.append(a["default"])
            f.set_variation_by_axes(vals)
        except (OSError, AttributeError):
            pass  # static font
    return f


class ADraw(ImageDraw.ImageDraw):
    """ImageDraw whose text() honours the alpha of fill/stroke colours.

    Pillow draws text at full opacity even with an RGBA ink, which breaks fades,
    so semi-transparent text is rendered on its own layer and pasted with a mask.
    """

    def text(self, xy, text, fill=None, font=None, anchor=None, spacing=4, align="left",
             stroke_width=0, stroke_fill=None, **kw):
        fa = fill[3] if isinstance(fill, tuple) and len(fill) == 4 else 255
        sa = stroke_fill[3] if isinstance(stroke_fill, tuple) and len(stroke_fill) == 4 else 255
        if fa >= 255 and (not stroke_width or sa >= 255):
            return super().text(xy, text, fill=fill, font=font, anchor=anchor, spacing=spacing, align=align,
                                stroke_width=stroke_width, stroke_fill=stroke_fill, **kw)
        if fa <= 0 and (not stroke_width or sa <= 0):
            return
        l, t, r, b = self.textbbox(xy, text, font=font, anchor=anchor, spacing=spacing, align=align,
                                   stroke_width=stroke_width)
        x0, y0 = int(math.floor(l)) - 2, int(math.floor(t)) - 2
        w, h = int(math.ceil(r)) - x0 + 2, int(math.ceil(b)) - y0 + 2
        if w <= 0 or h <= 0:
            return
        pos = (xy[0] - x0, xy[1] - y0)
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        opts = dict(font=font, anchor=anchor, spacing=spacing, align=align)
        if stroke_width and stroke_fill is not None and sa > 0:
            sl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            ImageDraw.ImageDraw(sl).text(pos, text, fill=tuple(stroke_fill[:3]) + (255,), stroke_width=stroke_width,
                                         stroke_fill=tuple(stroke_fill[:3]) + (255,), **opts)
            sl.putalpha(sl.getchannel("A").point(lambda v: v * sa // 255))
            layer.alpha_composite(sl)
        if fa > 0:
            tl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            ImageDraw.ImageDraw(tl).text(pos, text, fill=tuple(fill[:3]) + (255,), **opts)
            tl.putalpha(tl.getchannel("A").point(lambda v: v * fa // 255))
            layer.alpha_composite(tl)
        self._image.paste(layer, (x0, y0), layer)


def Draw(img):
    return ADraw(img, "RGBA")


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = min(max(x, 0.0), 1.0)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ramp(t, a, b):
    """0 before a, 1 after b, smooth in between."""
    if b <= a:
        return 1.0 if t >= b else 0.0
    return ease((t - a) / (b - a))


def fade_window(t, dur, fin=0.6, fout=0.6):
    return min(ramp(t, 0, fin), 1 - ramp(t, dur - fout, dur))


def lerp(a, b, x):
    return a + (b - a) * x


def mix(c1, c2, x):
    return tuple(int(lerp(a, b, x)) for a, b in zip(c1, c2))


def with_alpha(c, a):
    return (c[0], c[1], c[2], int(max(0, min(1, a)) * 255))


# ---------- textures ----------
@functools.lru_cache(maxsize=1)
def vignette():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    v = 1 - 0.42 * np.clip(d - 0.35, 0, None) ** 1.6
    return np.clip(v, 0.45, 1)[..., None].astype(np.float32)


@functools.lru_cache(maxsize=1)
def grain_bank():
    rng = np.random.default_rng(7)
    # half-res grain upscaled reads as film grain rather than digital noise
    bank = []
    for _ in range(12):
        g = rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
        g = np.array(Image.fromarray(((g * 40) + 128).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR),
                     dtype=np.float32) - 128
        bank.append(g[..., None])
    return bank


def finish(frame, n, grain=6.0, vig=True):
    """Apply vignette + film grain to an RGB uint8 array; returns uint8."""
    f = frame.astype(np.float32)
    if vig:
        f *= vignette()
    if grain:
        f += grain_bank()[n % 12] * (grain / 40.0)
    return np.clip(f, 0, 255).astype(np.uint8)


@functools.lru_cache(maxsize=1)
def paper_bg():
    """Dark, slightly mottled background used under animations."""
    rng = np.random.default_rng(3)
    small = rng.normal(0, 1, (27, 48)).astype(np.float32)
    big = np.array(Image.fromarray(((small * 18) + 128).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC),
                   dtype=np.float32) - 128
    base = np.array(BG, dtype=np.float32)[None, None, :] + big[..., None] * 0.35
    y = np.linspace(-1, 1, H)[:, None, None]
    base += (1 - y ** 2) * 6
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))


def canvas():
    return paper_bg().copy()


# ---------- text ----------
def text_center(draw, xy, text, fnt, fill, anchor="mm", spacing=0, tracking=0):
    if tracking:
        # manual letter spacing
        widths = [draw.textlength(ch, font=fnt) for ch in text]
        total = sum(widths) + tracking * (len(text) - 1)
        x0 = xy[0] - total / 2 if anchor[0] == "m" else (xy[0] if anchor[0] == "l" else xy[0] - total)
        x = x0
        for ch, w in zip(text, widths):
            draw.text((x, xy[1]), ch, font=fnt, fill=fill, anchor="l" + anchor[1])
            x += w + tracking
        return
    draw.text(xy, text, font=fnt, fill=fill, anchor=anchor, spacing=spacing)


def wrap(draw, text, fnt, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=fnt) <= width:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def overlay_rgba(base_rgb, rgba):
    """Alpha-composite an RGBA PIL image onto an RGB PIL image."""
    out = base_rgb.convert("RGBA")
    out.alpha_composite(rgba)
    return out.convert("RGB")


def lower_third(label, sub=None, alpha=1.0):
    """Small archival source caption, bottom-left. Returns RGBA layer."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if alpha <= 0:
        return layer
    d = Draw(layer)
    f1 = font("oswald", 38, 700)
    f2 = font("sans", 25)
    x, y = 84, H - 140
    w = max(d.textlength(label, font=f1), d.textlength(sub or "", font=f2)) + 40
    d.rectangle([x - 20, y - 8, x - 14, y + (78 if sub else 42)], fill=with_alpha(URANIUM, alpha))
    d.rectangle([x - 14, y - 8, x + w, y + (78 if sub else 42)], fill=(0, 0, 0, int(140 * alpha)))
    d.text((x, y), label.upper(), font=f1, fill=with_alpha(INK, alpha), anchor="la")
    if sub:
        d.text((x, y + 46), sub, font=f2, fill=with_alpha((196, 190, 178), alpha), anchor="la")
    return layer


# ---------- photos ----------
@functools.lru_cache(maxsize=8)
def load_photo(key, bw=False):
    path = None
    for ext in (".jpg", ".jpeg", ".png", ".JPG"):
        p = os.path.join(ASSETS, key + ext)
        if os.path.exists(p):
            path = p
            break
    if path is None:
        raise FileNotFoundError(key)
    im = Image.open(path).convert("RGB")
    if bw:
        im = im.convert("L").convert("RGB")
    return im


def cover_rect(iw, ih, zoom, cx, cy):
    """Crop rectangle (in image coords) covering a 16:9 frame at given zoom/centre (0..1)."""
    ar = W / H
    if iw / ih > ar:
        ch = ih / zoom
        cw = ch * ar
    else:
        cw = iw / zoom
        ch = cw / ar
    cw, ch = min(cw, iw), min(ch, ih)
    x0 = max(0.0, min(cx * iw - cw / 2, iw - cw))
    y0 = max(0.0, min(cy * ih - ch / 2, ih - ch))
    return (x0, y0, x0 + cw, y0 + ch)


def ken_burns(im, p, z0=1.0, z1=1.12, c0=(0.5, 0.5), c1=(0.5, 0.5), fit="cover"):
    """Frame at progress p (0..1) of a slow push/pan over a still."""
    p = min(max(p, 0.0), 1.0)  # shots run a little past their end during dissolves
    e = ease_in_out(p) * 0.85 + p * 0.15
    z = max(1.0, lerp(z0, z1, e))
    cx, cy = lerp(c0[0], c1[0], e), lerp(c0[1], c1[1], e)
    iw, ih = im.size
    if fit == "contain":
        # portrait / odd aspect: blurred backdrop + whole image, gently zoomed
        return contain_frame(im, z, cx, cy)
    box = cover_rect(iw, ih, z, cx, cy)
    return im.resize((W, H), Image.BICUBIC, box=box)


_BACKDROPS = {}


def _backdrop(im):
    key = id(im)
    if key in _BACKDROPS:
        return _BACKDROPS[key][1]
    if len(_BACKDROPS) > 3:
        _BACKDROPS.pop(next(iter(_BACKDROPS)))
    bg = im.resize((W // 8, H // 8), Image.BILINEAR, box=cover_rect(im.size[0], im.size[1], 1.0, .5, .5))
    bg = bg.filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BICUBIC)
    bg = Image.blend(bg, Image.new("RGB", (W, H), BG), 0.55)
    _BACKDROPS[key] = (im, bg)  # keep im alive so its id() is not reused
    return bg


def contain_frame(im, z=1.0, cx=0.5, cy=0.5):
    iw, ih = im.size
    bg = _backdrop(im).copy()
    scale = min((W * 0.92) / iw, (H * 0.92) / ih) * z
    nw, nh = int(iw * scale), int(ih * scale)
    fg = im.resize((nw, nh), Image.BICUBIC)
    x = int(W / 2 - nw / 2 + (0.5 - cx) * nw * (z - 1))
    y = int(H / 2 - nh / 2 + (0.5 - cy) * nh * (z - 1))
    sh = Image.new("RGBA", (nw + 60, nh + 60), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([30, 30, nw + 30, nh + 30], fill=(0, 0, 0, 150))
    sh = sh.filter(ImageFilter.GaussianBlur(18))
    bg = bg.convert("RGBA")
    bg.alpha_composite(sh, (x - 30 + 8, y - 30 + 12))
    bg = bg.convert("RGB")
    bg.paste(fg, (x, y))
    return bg


def grade(im, sat=0.85, warm=0.0, contrast=1.05):
    """Gentle unifying grade for archive material."""
    a = np.asarray(im, dtype=np.float32)
    lum = a @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    a = lum[..., None] + (a - lum[..., None]) * sat
    a = (a - 128) * contrast + 128
    if warm:
        a[..., 0] += 8 * warm
        a[..., 2] -= 8 * warm
    return np.clip(a, 0, 255).astype(np.uint8)
