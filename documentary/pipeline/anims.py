"""Motion graphics for the documentary. Every animation is f(t, dur, **params) -> PIL RGB image."""
import functools, json, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from common import (Draw, W, H, BG, BG2, INK, DIM, URANIUM, AMBER, RED, STEEL, GEO, font, ease, ease_out,
                    ease_in_out, ramp, lerp, mix, with_alpha, canvas, text_center, wrap, load_photo)

SS = 2  # supersampling for vector-heavy frames


# ---------------------------------------------------------------- particles
def _particles(seed, n):
    rng = np.random.default_rng(seed)
    return rng.random((n, 5))


def draw_particles(img, t, seed=1, n=90, color=URANIUM, rise=26, alpha=0.55, size=(1.5, 4.5)):
    """Slowly rising glowing motes (radioactive dust)."""
    p = _particles(seed, n)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x, y, s, ph, sp in p:
        yy = (y * H - t * rise * (0.4 + sp)) % (H + 40) - 20
        xx = x * W + math.sin(t * 0.6 + ph * 6.28) * 18
        r = lerp(size[0], size[1], s)
        a = alpha * (0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * 2 + ph * 9)))
        d.ellipse([xx - r, yy - r, xx + r, yy + r], fill=with_alpha(color, a))
    glow = layer.filter(ImageFilter.GaussianBlur(4))
    out = img.convert("RGBA")
    out.alpha_composite(glow)
    out.alpha_composite(layer)
    return out.convert("RGB")


# ---------------------------------------------------------------- title & cards
def title(t, dur, **_):
    img = canvas()
    img = draw_particles(img, t, seed=11, n=140, alpha=0.7)
    d = Draw(img)
    a = ramp(t, 0.6, 2.4) * (1 - ramp(t, dur - 1.0, dur))
    track = lerp(40, 12, ease_out(t / dur))
    text_center(d, (W / 2, H / 2 - 40), "URANIUM FOR STALIN", font("display", 176),
                with_alpha(INK, a), tracking=track)
    a2 = ramp(t, 2.0, 3.6) * (1 - ramp(t, dur - 1.0, dur))
    w = 520 * ease_out(ramp(t, 1.6, 3.2))
    d.rectangle([W / 2 - w, H / 2 + 72, W / 2 + w, H / 2 + 75], fill=with_alpha(URANIUM, a2))
    text_center(d, (W / 2, H / 2 + 128), "Czechoslovakia, the Soviet bomb and the hell of Jáchymov",
                font("serif", 44, 400), with_alpha(DIM, a2))
    return img


def chapter(t, dur, num="I", name="", years="", **_):
    img = canvas()
    img = draw_particles(img, t, seed=hash(num) % 97, n=60, alpha=0.4)
    d = Draw(img)
    a = ramp(t, 0.2, 1.0) * (1 - ramp(t, dur - 0.7, dur))
    text_center(d, (W / 2, H / 2 - 120), num, font("playfair", 70, 500), with_alpha(URANIUM, a))
    w = 300 * ease_out(ramp(t, 0.3, 1.4))
    d.rectangle([W / 2 - w, H / 2 - 62, W / 2 + w, H / 2 - 60], fill=with_alpha(DIM, a * 0.8))
    text_center(d, (W / 2, H / 2 + 20), name.upper(), font("display", 150), with_alpha(INK, a),
                tracking=lerp(18, 8, ease_out(t / dur)))
    if years:
        text_center(d, (W / 2, H / 2 + 125), years, font("oswald", 38, 300), with_alpha(DIM, a), tracking=6)
    return img


def dateline(t, dur, lines=(), flash_at=None, **_):
    """Typewriter date/location slug on black; optional white flash at the end."""
    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = Draw(img)
    y = H / 2 - (len(lines) - 1) * 40
    start = 0.4
    for i, line in enumerate(lines):
        n = int(max(0, (t - start) * 22))
        shown = line[:n]
        f = font("mono", 54 if i == 0 else 34)
        col = INK if i == 0 else DIM
        d.text((W / 2 - d.textlength(line, font=f) / 2, y), shown, font=f, fill=col, anchor="lm")
        if 0 < n < len(line) and int(t * 3) % 2 == 0:
            cx = W / 2 - d.textlength(line, font=f) / 2 + d.textlength(shown, font=f)
            d.rectangle([cx + 4, y - 24, cx + 20, y + 24], fill=URANIUM)
        start += len(line) / 22 + 0.3
        y += 80
    if flash_at is not None and t > flash_at:
        k = ease(min(1, (t - flash_at) / max(0.05, dur - flash_at)))
        img = Image.blend(img, Image.new("RGB", (W, H), (255, 252, 240)), k)
    return img


def dedication(t, dur, **_):
    img = canvas()
    img = draw_particles(img, t, seed=5, n=50, alpha=0.35, color=INK, rise=12)
    d = Draw(img)
    a = ramp(t, 0.5, 2.0) * (1 - ramp(t, dur - 1.2, dur))
    text_center(d, (W / 2, H / 2 - 40), "In memory of the prisoners", font("serif", 64, 400), with_alpha(INK, a))
    text_center(d, (W / 2, H / 2 + 40), "of the Czechoslovak uranium camps, 1949 – 1961", font("serif", 64, 400),
                with_alpha(INK, a))
    return img


# ---------------------------------------------------------------- maps
@functools.lru_cache(maxsize=1)
def _world():
    from shapely.geometry import shape
    from shapely.ops import unary_union
    gj = json.load(open(os.path.join(GEO, "countries50.geojson")))
    geoms = {}
    for f in gj["features"]:
        iso = f["properties"].get("ADM0_A3") or f["properties"].get("ISO_A3")
        geoms[iso] = shape(f["geometry"]).buffer(0)
    groups = {
        "CSK": ["CZE", "SVK"],
        "SUN": ["RUS", "UKR", "BLR", "EST", "LVA", "LTU", "MDA", "GEO", "ARM", "AZE", "KAZ", "UZB", "TKM", "KGZ", "TJK"],
    }
    merged = {}
    used = set()
    for g, members in groups.items():
        merged[g] = unary_union([geoms[m] for m in members if m in geoms])
        used.update(members)
    rest = {k: v for k, v in geoms.items() if k not in used}
    return merged, rest


def _polys(geom):
    if geom.geom_type == "Polygon":
        return [geom]
    return list(getattr(geom, "geoms", []))


class View:
    """Equirectangular projection with cos(lat) scaling around a centre."""

    def __init__(self, lon, lat, scale):
        self.lon, self.lat, self.scale = lon, lat, scale
        self.k = math.cos(math.radians(lat))

    def xy(self, lon, lat):
        return (W / 2 + (lon - self.lon) * self.k * self.scale, H / 2 - (lat - self.lat) * self.scale)

    def arr(self, coords):
        c = np.asarray(coords)
        x = W / 2 + (c[:, 0] - self.lon) * self.k * self.scale
        y = H / 2 - (c[:, 1] - self.lat) * self.scale
        return np.stack([x, y], 1)


def lerp_view(v0, v1, x):
    # zoom geometrically so the move feels constant-speed
    s = math.exp(lerp(math.log(v0[2]), math.log(v1[2]), x))
    return View(lerp(v0[0], v1[0], x), lerp(v0[1], v1[1], x), s)


@functools.lru_cache(maxsize=8)
def _world_simplified(tol):
    merged, rest = _world()
    simp = lambda g: g.simplify(tol, preserve_topology=True) if tol else g
    return {k: simp(v) for k, v in merged.items()}, {k: simp(v) for k, v in rest.items()}


def draw_map(view, highlight=None, ss=SS):
    key = (round(view.lon, 4), round(view.lat, 4), round(view.scale, 3),
           tuple(sorted((k, tuple(v[0]), v[1], tuple(v[2])) for k, v in (highlight or {}).items())), ss)
    if key not in _MAP_CACHE:
        if len(_MAP_CACHE) > 4:
            _MAP_CACHE.pop(next(iter(_MAP_CACHE)))
        _MAP_CACHE[key] = _draw_map_uncached(view, highlight, ss)
    return _MAP_CACHE[key].copy()


_MAP_CACHE = {}


def _draw_map_uncached(view, highlight, ss):
    """Render land/borders. highlight: {group_code: (fill_rgb, alpha, outline_rgb)}."""
    highlight = highlight or {}
    # simplify to about half a pixel at this zoom
    tol = 0.5 / (view.scale * ss)
    level = max([0.0, 0.002, 0.006, 0.015, 0.04][i] for i in range(5) if [0.0, 0.002, 0.006, 0.015, 0.04][i] <= tol)
    merged, rest = _world_simplified(level)
    img = Image.new("RGB", (W * ss, H * ss), (11, 13, 15))
    d = Draw(img)
    land, border = (34, 37, 39), (64, 70, 74)

    def poly_pts(p):
        return [tuple(pt) for pt in (view.arr(p.exterior.coords) * ss)]

    def visible(p):
        minx, miny, maxx, maxy = p.bounds
        x0, y1 = view.xy(minx, miny)
        x1, y0 = view.xy(maxx, maxy)
        if (x1 - x0) < 1.5 and (y1 - y0) < 1.5:
            return False  # sub-pixel islands
        return x1 > -50 and x0 < W + 50 and y1 > -50 and y0 < H + 50

    for geom in list(rest.values()) + [merged[g] for g in merged if g not in highlight]:
        for p in _polys(geom):
            if visible(p):
                d.polygon(poly_pts(p), fill=land, outline=border, width=max(1, ss))
    for g, (fill, a, outline) in highlight.items():
        for p in _polys(merged[g]):
            if visible(p):
                pts = poly_pts(p)
                d.polygon(pts, fill=mix(land, fill, a))
                d.line(pts + [pts[0]], fill=outline, width=3 * ss, joint="curve")
    if ss != 1:
        img = img.resize((W, H), Image.LANCZOS)
    return img


def marker(d, xy, t, color=URANIUM, label=None, sub=None, a=1.0, side="r", r=9):
    x, y = xy
    pulse = (t * 0.8) % 1
    rr = r + 34 * pulse
    d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=with_alpha(color, a * (1 - pulse)), width=3)
    d.ellipse([x - r, y - r, x + r, y + r], fill=with_alpha(color, a))
    if label:
        f = font("oswald", 40, 500)
        dx = 26 if side == "r" else -26
        anc = "lm" if side == "r" else "rm"
        d.text((x + dx, y - (12 if sub else 0)), label, font=f, fill=with_alpha(INK, a), anchor=anc,
               stroke_width=4, stroke_fill=(0, 0, 0, int(160 * a)))
        if sub:
            d.text((x + dx, y + 26), sub, font=font("serif", 28, 400), fill=with_alpha(DIM, a), anchor=anc,
                   stroke_width=3, stroke_fill=(0, 0, 0, int(160 * a)))


def map_label(d, view, lon, lat, text, a, size=34, color=DIM, tracking=8):
    x, y = view.xy(lon, lat)
    text_center(d, (x, y), text, font("oswald", size, 400), with_alpha(color, a), tracking=tracking)


JACHYMOV = (12.9113, 50.3717)
TEST_SITE = (77.8159, 50.4378)
MOSCOW = (37.6176, 55.7558)
HORNI_SLAVKOV = (12.8077, 50.1387)
PRIBRAM = (14.0104, 49.6899)
OSTROV = (12.9391, 50.3059)


def map_zoom_jachymov(t, dur, **_):
    v0, v1 = (15.5, 50.2, 62.0), (13.2, 50.25, 330.0)
    x = ease_in_out(ramp(t, 0.6, dur - 2.2))
    view = lerp_view(v0, v1, x)
    img = draw_map(view, {"CSK": (AMBER, 0.28, AMBER)})
    d = Draw(img)
    a_country = 1 - ramp(t, dur * 0.35, dur * 0.55)
    map_label(d, view, 17.6, 49.0, "CZECHOSLOVAKIA", a_country, 44, AMBER)
    map_label(d, view, 10.4, 51.3, "GERMANY", a_country * 0.8, 32)
    map_label(d, view, 19.3, 52.2, "POLAND", a_country * 0.8, 32)
    map_label(d, view, 14.0, 47.6, "AUSTRIA", a_country * 0.8, 32)
    a_reg = ramp(t, dur * 0.55, dur * 0.75)
    map_label(d, view, 13.45, 50.82, "SAXONY", a_reg, 38)
    map_label(d, view, 13.8, 50.02, "BOHEMIA", a_reg, 38)
    map_label(d, view, 12.45, 50.52, "ORE  MOUNTAINS", a_reg * 0.9, 30, INK, 10)
    a_m = ramp(t, dur * 0.7, dur * 0.85)
    marker(d, view.xy(*JACHYMOV), t, URANIUM, "JÁCHYMOV", "St. Joachimsthal", a_m)
    return img


def _great_circle(p0, p1, n=200):
    lon1, lat1, lon2, lat2 = map(math.radians, (*p0, *p1))
    a = np.array([math.cos(lat1) * math.cos(lon1), math.cos(lat1) * math.sin(lon1), math.sin(lat1)])
    b = np.array([math.cos(lat2) * math.cos(lon2), math.cos(lat2) * math.sin(lon2), math.sin(lat2)])
    om = math.acos(np.clip(a @ b, -1, 1))
    pts = []
    for f in np.linspace(0, 1, n):
        v = (math.sin((1 - f) * om) * a + math.sin(f * om) * b) / math.sin(om)
        pts.append((math.degrees(math.atan2(v[1], v[0])), math.degrees(math.asin(v[2]))))
    return pts, om * 6371.0


def map_distance(t, dur, **_):
    view = lerp_view((44.0, 50.5, 21.0), (45.5, 50.0, 23.5), t / dur)
    img = draw_map(view, {"SUN": (RED, 0.22, (150, 50, 44)), "CSK": (AMBER, 0.3, AMBER)})
    d = Draw(img)
    pts, km = _great_circle(JACHYMOV, TEST_SITE)
    x = ease_in_out(ramp(t, 1.2, dur - 1.6))
    n = max(2, int(len(pts) * x))
    xy = [view.xy(*p) for p in pts[:n]]
    d.line(xy, fill=with_alpha(URANIUM, 0.95), width=5, joint="curve")
    marker(d, view.xy(*JACHYMOV), t, AMBER, "JÁCHYMOV", None, ramp(t, 0.2, 0.9), side="l")
    marker(d, view.xy(*TEST_SITE), t, RED, "SEMIPALATINSK", "test site, 1949", ramp(t, dur - 1.8, dur - 1.0), side="l")
    map_label(d, view, 48.0, 61.0, "SOVIET UNION", ramp(t, 0.3, 1.2), 44, (214, 120, 110), 12)
    a = ramp(t, 1.2, 1.8)
    text_center(d, (W / 2, H - 120), f"{int(round(km * x / 10) * 10):,} km", font("display", 110),
                with_alpha(INK, a))
    return img


def train_route(t, dur, **_):
    view = View(30.0, 52.0, 40.0)
    img = draw_map(view, {"SUN": (RED, 0.22, (150, 50, 44)), "CSK": (AMBER, 0.3, AMBER)})
    d = Draw(img)
    # schematic rail line east (not a surveyed route)
    route = [JACHYMOV, (14.4, 50.1), (17.0, 49.9), (19.9, 50.05), (24.0, 50.0), (27.5, 50.3), (30.5, 50.45),
             (33.5, 51.4), (35.5, 53.4), MOSCOW]
    xy = [view.xy(*p) for p in route]
    # dashed rail
    seglen = np.cumsum([0] + [math.dist(xy[i], xy[i + 1]) for i in range(len(xy) - 1)])
    total = seglen[-1]

    def at(s):
        i = int(np.searchsorted(seglen, s) - 1)
        i = min(max(i, 0), len(xy) - 2)
        f = (s - seglen[i]) / max(1e-6, seglen[i + 1] - seglen[i])
        return (lerp(xy[i][0], xy[i + 1][0], f), lerp(xy[i][1], xy[i + 1][1], f))

    reveal = ease_in_out(ramp(t, 0.3, 2.5)) * total
    s = 0
    while s < reveal:
        d.line([at(s), at(min(s + 14, reveal))], fill=with_alpha(INK, 0.55), width=4)
        s += 24
    # wagons moving east
    for k in range(6):
        pos = ((t - 1.0) * 120 - k * 70)
        if 0 < pos < total:
            x, y = at(pos)
            d.rectangle([x - 14, y - 9, x + 14, y + 9], fill=with_alpha(URANIUM, 0.95), outline=(0, 0, 0, 200))
    marker(d, view.xy(*JACHYMOV), t, AMBER, "JÁCHYMOV", None, 1, side="l")
    marker(d, view.xy(*MOSCOW), t, RED, "MOSCOW", None, ramp(t, 2.0, 2.6))
    a = ramp(t, 1.5, 2.2)
    text_center(d, (W / 2, 120), "SEALED WAGONS — EAST TO THE USSR", font("display", 90), with_alpha(INK, a), tracking=6)
    d.text((W - 60, H - 50), "Schematic route", font=font("sans", 22), fill=with_alpha(DIM, 0.8), anchor="rm")
    return img


def camp_map(t, dur, **_):
    view = lerp_view((13.6, 49.95, 290.0), (13.45, 49.98, 310.0), t / dur)
    img = draw_map(view, {"CSK": (AMBER, 0.12, (120, 100, 70))})
    d = Draw(img)
    regions = [(JACHYMOV, "JÁCHYMOV", 0.8), (HORNI_SLAVKOV, "HORNÍ SLAVKOV", 1.6), (PRIBRAM, "PŘÍBRAM", 2.4)]
    for (lon, lat), name, t0 in regions:
        a = ramp(t, t0, t0 + 0.8)
        x, y = view.xy(lon, lat)
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        r = 70
        gd.ellipse([x - r, y - r, x + r, y + r], fill=with_alpha(RED, 0.45 * a))
        glow = glow.filter(ImageFilter.GaussianBlur(26))
        im2 = img.convert("RGBA")
        im2.alpha_composite(glow)
        img = im2.convert("RGB")
        d = Draw(img)
        marker(d, (x, y), t, RED, name, None, a, side="r" if name != "HORNÍ SLAVKOV" else "l")
    # earlier draws are re-done after glow compositing
    for (lon, lat), name, t0 in regions:
        a = ramp(t, t0, t0 + 0.8)
        marker(d, view.xy(lon, lat), t, RED, name, None, a, side="r" if name != "HORNÍ SLAVKOV" else "l")
    n = int(round(18 * ease_out(ramp(t, 1.0, dur - 1.5))))
    a = ramp(t, 0.8, 1.4)
    d.text((110, H - 210), f"{n}", font=font("display", 200), fill=with_alpha(INK, a), anchor="ls")
    d.text((110 + d.textlength("18", font=font("display", 200)) + 24, H - 230), "LABOUR CAMPS",
           font=font("oswald", 54, 500), fill=with_alpha(INK, a), anchor="ls")
    d.text((110 + d.textlength("18", font=font("display", 200)) + 24, H - 188), "around the uranium mines · 1949–1961",
           font=font("serif", 32), fill=with_alpha(DIM, a), anchor="ls")
    map_label(d, view, 14.42, 50.08, "Prague", ramp(t, 0.2, 0.8), 30, DIM, 2)
    x, y = view.xy(14.42, 50.08)
    d.ellipse([x - 5, y + 18, x + 5, y + 28], fill=with_alpha(DIM, ramp(t, 0.2, 0.8)))
    return img


# ---------------------------------------------------------------- typography pieces
def etymology(t, dur, **_):
    img = canvas()
    d = Draw(img)
    f = font("display", 190)
    steps = [("JOACHIMSTHALER", "silver coin of Joachimsthal, 1520", 0.3),
             ("THALER", "the coin's name across Europe", dur * 0.38),
             ("DOLLAR", "", dur * 0.66)]
    for i, (word, sub, t0) in enumerate(steps):
        t1 = steps[i + 1][2] if i + 1 < len(steps) else dur + 1
        a = ramp(t, t0, t0 + 0.7) * (1 - ramp(t, t1 - 0.4, t1 + 0.2))
        if a <= 0:
            continue
        col = URANIUM if word == "DOLLAR" else INK
        if word == "JOACHIMSTHALER":
            # "JOACHIMS" dims out before the cut, leaving THALER
            dim = ramp(t, t1 - 1.6, t1 - 0.6)
            wa = d.textlength("JOACHIMS", font=f)
            total = d.textlength(word, font=f)
            x0 = W / 2 - total / 2
            d.text((x0, H / 2 - 30), "JOACHIMS", font=f, fill=with_alpha(INK, a * (1 - 0.8 * dim)), anchor="lm")
            d.text((x0 + wa, H / 2 - 30), "THALER", font=f, fill=with_alpha(mix(INK, AMBER, dim), a), anchor="lm")
        else:
            text_center(d, (W / 2, H / 2 - 30), word, f, with_alpha(col, a), tracking=6)
        if sub:
            text_center(d, (W / 2, H / 2 + 100), sub, font("serif", 40), with_alpha(DIM, a))
    return img


def elements(t, dur, **_):
    img = canvas()
    img = draw_particles(img, t, seed=21, n=70, alpha=0.5)
    d = Draw(img)
    tiles = [(84, "Po", "Polonium", 0.4), (88, "Ra", "Radium", 1.3)]
    for i, (z, sym, name, t0) in enumerate(tiles):
        a = ramp(t, t0, t0 + 0.6)
        s = lerp(0.85, 1.0, ease_out(ramp(t, t0, t0 + 0.8)))
        cx = W / 2 + (i - 0.5) * 420
        cy = H / 2 - 40
        w2, h2 = 170 * s, 210 * s
        col = URANIUM if sym == "Ra" else AMBER
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).rounded_rectangle([cx - w2, cy - h2, cx + w2, cy + h2], 18,
                                               fill=with_alpha(col, 0.28 * a * (0.8 + 0.2 * math.sin(t * 3))))
        glow = glow.filter(ImageFilter.GaussianBlur(30))
        im2 = img.convert("RGBA")
        im2.alpha_composite(glow)
        img = im2.convert("RGB")
        d = Draw(img)
        d.rounded_rectangle([cx - w2, cy - h2, cx + w2, cy + h2], 18, fill=(20, 22, 22, int(230 * a)),
                            outline=with_alpha(col, a), width=4)
        d.text((cx - w2 + 26, cy - h2 + 20), str(z), font=font("oswald", int(46 * s), 400), fill=with_alpha(DIM, a))
        d.text((cx, cy + 5), sym, font=font("playfair", int(170 * s), 600), fill=with_alpha(INK, a), anchor="mm")
        d.text((cx, cy + h2 - 46), name.upper(), font=font("oswald", int(40 * s), 400), fill=with_alpha(col, a),
               anchor="mm")
    a = ramp(t, 2.2, 3.0)
    text_center(d, (W / 2, H - 170), "Discovered in 1898 by Marie and Pierre Curie", font("serif", 44), with_alpha(INK, a))
    text_center(d, (W / 2, H - 112), "from pitchblende residues shipped from Joachimsthal", font("serif", 36),
                with_alpha(DIM, a))
    return img


def _lungs(d, cx, cy, s, a, col):
    # stylised lungs: two lobes + trachea and bronchi
    for side in (-1, 1):
        pts = []
        for k in range(60):
            th = k / 59 * 2 * math.pi
            r = 1 + 0.18 * math.cos(2 * th) - 0.1 * math.sin(th) * side
            x = cx + side * 120 * s + math.cos(th) * 95 * s * r
            y = cy + 40 * s + math.sin(th) * 170 * s * (1.05 if math.sin(th) > 0 else 0.95)
            pts.append((x, y))
        d.polygon(pts, outline=with_alpha(col, a), fill=with_alpha(col, a * 0.08), width=4)
    d.line([(cx, cy - 210 * s), (cx, cy - 60 * s)], fill=with_alpha(col, a), width=8)
    for side in (-1, 1):
        d.line([(cx, cy - 60 * s), (cx + side * 80 * s, cy - 10 * s), (cx + side * 120 * s, cy + 60 * s)],
               fill=with_alpha(col, a), width=6, joint="curve")
        d.line([(cx + side * 80 * s, cy - 10 * s), (cx + side * 150 * s, cy - 20 * s)], fill=with_alpha(col, a), width=4)
        d.line([(cx + side * 120 * s, cy + 60 * s), (cx + side * 100 * s, cy + 130 * s)], fill=with_alpha(col, a), width=4)


def radon(t, dur, **_):
    img = canvas()
    d = Draw(img)
    chain = [("U-238", "uranium"), ("…", ""), ("Ra-226", "radium"), ("Rn-222", "radon gas")]
    x0, y0, gap = 220, 330, 300
    for i, (iso, name) in enumerate(chain):
        a = ramp(t, 0.3 + i * 0.6, 0.9 + i * 0.6)
        x = x0 + i * gap
        col = URANIUM if iso == "Rn-222" else (AMBER if iso.startswith("Ra") else INK)
        if iso != "…":
            d.ellipse([x - 78, y0 - 78, x + 78, y0 + 78], outline=with_alpha(col, a), width=4,
                      fill=(20, 22, 22, int(220 * a)))
            d.text((x, y0 - 6), iso, font=font("oswald", 44, 500), fill=with_alpha(INK, a), anchor="mm")
            d.text((x, y0 + 116), name, font=font("serif", 30), fill=with_alpha(DIM, a), anchor="mm")
        else:
            d.text((x, y0), "…", font=font("oswald", 60), fill=with_alpha(DIM, a), anchor="mm")
        if i < len(chain) - 1:
            aa = ramp(t, 0.7 + i * 0.6, 1.1 + i * 0.6)
            d.line([(x + 90, y0), (x + gap - 90, y0)], fill=with_alpha(DIM, aa), width=3)
            d.polygon([(x + gap - 90, y0), (x + gap - 104, y0 - 8), (x + gap - 104, y0 + 8)], fill=with_alpha(DIM, aa))
    # radon motes drift from the Rn node into the lungs
    lx, ly = 1480, 560
    la = ramp(t, 2.6, 3.4)
    _lungs(d, lx, ly, 1.25, la, INK)
    rng = np.random.default_rng(4)
    sx, sy = x0 + 3 * gap, y0
    stuck = 0
    for k in range(70):
        t0 = 3.0 + k * 0.07
        if t < t0:
            continue
        u = min(1, (t - t0) / 2.2)
        tx = lx + rng.uniform(-200, 200)
        ty = ly + rng.uniform(-60, 200)
        x = lerp(sx, tx, ease_in_out(u)) + math.sin(t * 2 + k) * 10 * (1 - u)
        y = lerp(sy, ty, ease_in_out(u)) - math.sin(u * math.pi) * 120
        r = 5
        d.ellipse([x - r, y - r, x + r, y + r], fill=with_alpha(URANIUM, 0.9))
        stuck += u >= 1
    a = ramp(t, 4.0, 4.8)
    d.text((140, H - 210), "Radon-222", font=font("oswald", 56, 500), fill=with_alpha(URANIUM, a))
    d.text((140, H - 140), "radioactive gas · half-life 3.8 days · its decay products lodge in the lungs",
           font=font("serif", 34), fill=with_alpha(DIM, a))
    return img


def agreement(t, dur, **_):
    img = canvas()
    # paper sheet
    pw, ph = 980, 920
    px, py = W / 2 - pw / 2, H / 2 - ph / 2 + 30 - 30 * ease_out(ramp(t, 0, 1.2))
    a = ramp(t, 0, 0.8)
    paper = Image.new("RGBA", (pw, ph), (226, 216, 192, 255))
    pd = ImageDraw.Draw(paper)
    rng = np.random.default_rng(9)
    for _ in range(400):
        x, y = rng.uniform(0, pw), rng.uniform(0, ph)
        pd.point((x, y), fill=(190, 178, 150, 255))
    lines = [("PRAGUE, 23 NOVEMBER 1945", "type", 30),
             ("", "type", 20),
             ("AGREEMENT", "type", 50),
             ("between Czechoslovakia and the USSR", "type", 30),
             ("on the mining of radioactive ores", "type", 30),
             ("and their delivery to the Soviet Union", "type", 30)]
    y = 110
    cps = 34
    chars = int(max(0, t - 0.8) * cps)
    total_chars = sum(len(l[0]) + 4 for l in lines)
    for text, fnt, size in lines:
        f = font(fnt, size)
        shown = text[:max(0, chars)]
        chars -= len(text) + 4
        pd.text((pw / 2, y), shown, font=f, fill=(40, 34, 28, 255), anchor="mm")
        y += size + 34
    y += 30
    for k in range(7):
        w = rng.uniform(0.55, 0.92) * (pw - 220)
        if chars > k * 8:
            pd.rectangle([110, y, 110 + w, y + 10], fill=(150, 140, 120, 255))
        y += 42
    paper.putalpha(int(255 * a))
    shadow = Image.new("RGBA", (pw + 80, ph + 80), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle([40, 40, pw + 40, ph + 40], fill=(0, 0, 0, int(170 * a)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(22))
    base = img.convert("RGBA")
    base.alpha_composite(shadow, (int(px - 40 + 10), int(py - 40 + 18)))
    base.alpha_composite(paper, (int(px), int(py)))
    # stamp
    st = min(dur - 1.2, 0.8 + total_chars / cps + 0.3)
    if t > st:
        k = ease_out(min(1, (t - st) / 0.25))
        sc = lerp(1.6, 1.0, k)
        stamp = Image.new("RGBA", (760, 200), (0, 0, 0, 0))
        sd = ImageDraw.Draw(stamp)
        sd.rounded_rectangle([10, 10, 750, 190], 16, outline=(176, 30, 30, 230), width=10)
        sd.text((380, 100), "TOP SECRET", font=font("display", 140), fill=(176, 30, 30, 230), anchor="mm")
        stamp = stamp.resize((int(760 * sc), int(200 * sc)), Image.BICUBIC).rotate(-9, expand=True,
                                                                                   resample=Image.BICUBIC)
        stamp.putalpha(stamp.getchannel("A").point(lambda v: int(v * min(1, k * 1.2))))
        base.alpha_composite(stamp, (int(W / 2 - stamp.width / 2 + 120), int(H / 2 + 140 - stamp.height / 2)))
    img = base.convert("RGB")
    d = Draw(img)
    d.text((W - 60, H - 50), "Illustration – not the original document", font=font("sans", 22),
           fill=with_alpha(DIM, 0.8), anchor="rm")
    return img


def bar_chart(t, dur, **_):
    img = canvas()
    d = Draw(img)
    years = [1946, 1947, 1948, 1949]
    data = {  # tonnes of uranium for the Soviet programme
        "Germany (Soviet zone)": ([15, 150, 321.2, 767.8], STEEL),
        "Czechoslovakia": ([18, 49.1, 103.2, 147.3], AMBER),
        "Bulgaria": ([26.6, 7.6, 18.2, 30.3], (120, 112, 100)),
        "Poland": ([0, 2.3, 9.3, 43.3], (90, 84, 76)),
    }
    a = ramp(t, 0.2, 0.9)
    d.text((140, 110), "URANIUM FOR THE SOVIET BOMB PROGRAMME", font=font("oswald", 56, 500), fill=with_alpha(INK, a))
    d.text((140, 180), "tonnes of uranium supplied per year", font=font("serif", 34), fill=with_alpha(DIM, a))
    x0, y0, gw, hmax, vmax = 220, H - 190, 360, 600, 800
    for g in range(0, 801, 200):
        y = y0 - g / vmax * hmax
        d.line([(x0 - 20, y), (x0 + gw * 4 + 40, y)], fill=with_alpha(DIM, 0.18 * a), width=1)
        d.text((x0 - 34, y), str(g), font=font("sans", 24), fill=with_alpha(DIM, a), anchor="rm")
    bw = 66
    for yi, yr in enumerate(years):
        gx = x0 + yi * gw + 40
        g = ease_out(ramp(t, 1.0 + yi * 0.7, 2.4 + yi * 0.7))
        for si, (name, (vals, col)) in enumerate(data.items()):
            v = vals[yi] * g
            bx = gx + si * (bw + 8)
            hh = v / vmax * hmax
            d.rectangle([bx, y0 - hh, bx + bw, y0], fill=with_alpha(col, a))
            if name == "Czechoslovakia" and g > 0.05:
                d.text((bx + bw / 2, y0 - hh - 26), f"{vals[yi]:.0f}", font=font("oswald", 34, 600),
                       fill=with_alpha(AMBER, g), anchor="mm")
        d.text((gx + 2 * (bw + 8) - 4, y0 + 40), str(yr), font=font("oswald", 40, 400), fill=with_alpha(INK, a),
               anchor="mm")
    lx, ly = W - 600, 110
    for si, (name, (_, col)) in enumerate(data.items()):
        d.rectangle([lx, ly + si * 52 - 14, lx + 28, ly + si * 52 + 14], fill=with_alpha(col, a))
        d.text((lx + 44, ly + si * 52), name, font=font("sans", 30), fill=with_alpha(INK if si == 1 else DIM, a),
               anchor="lm")
    d.text((W - 60, H - 50), "Data: Soviet production figures cited in histories of the Soviet atomic project",
           font=font("sans", 22), fill=with_alpha(DIM, 0.8 * a), anchor="rm")
    return img


def plutonium_chain(t, dur, **_):
    img = canvas()
    d = Draw(img)
    steps = [("URANIUM ORE", "Jáchymov · Saxony · Bulgaria · Poland · USSR", AMBER),
             ("URANIUM METAL", "processed in the USSR", INK),
             ("REACTOR A", "Chelyabinsk-40 · June 1948", INK),
             ("PLUTONIUM-239", "separated from spent fuel", URANIUM),
             ("RDS-1", "29 August 1949", RED)]
    n = len(steps)
    xs = [180 + i * (W - 360) / (n - 1) for i in range(n)]
    y = H / 2 - 20
    for i, (name, sub, col) in enumerate(steps):
        t0 = 0.3 + i * (dur - 2.0) / n
        a = ramp(t, t0, t0 + 0.6)
        r = 92
        d.ellipse([xs[i] - r, y - r, xs[i] + r, y + r], outline=with_alpha(col, a), width=5,
                  fill=(20, 22, 22, int(230 * a)))
        d.ellipse([xs[i] - 14, y - 14, xs[i] + 14, y + 14], fill=with_alpha(col, a))
        for k, line in enumerate(wrap(d, name, font("oswald", 40, 500), 300)):
            d.text((xs[i], y + 140 + k * 46), line, font=font("oswald", 40, 500), fill=with_alpha(INK, a), anchor="mm")
        for k, line in enumerate(wrap(d, sub, font("serif", 28), 300)):
            d.text((xs[i], y + 196 + k * 34), line, font=font("serif", 28), fill=with_alpha(DIM, a), anchor="mm")
        if i < n - 1:
            aa = ease_in_out(ramp(t, t0 + 0.4, t0 + 1.2))
            xa, xb = xs[i] + r + 10, xs[i + 1] - r - 10
            d.line([(xa, y), (lerp(xa, xb, aa), y)], fill=with_alpha(DIM, 0.9), width=4)
            for k in range(4):
                u = ((t * 0.6 + k / 4) % 1)
                if u < aa:
                    px = lerp(xa, xb, u)
                    d.ellipse([px - 5, y - 5, px + 5, y + 5], fill=with_alpha(col, 0.9))
    return img


def timeline_1948(t, dur, **_):
    img = canvas()
    d = Draw(img)
    events = [("NOV 1945", "Secret uranium agreement with the USSR", AMBER),
              ("FEB 1948", "Communist seizure of power", RED),
              ("OCT 1948", "Law on forced labour camps", RED),
              ("1949", "First labour camps at the uranium mines", INK),
              ("AUG 1949", "First Soviet atomic test", URANIUM)]
    x0, x1, y = 170, W - 170, H / 2 + 20
    grow = ease_in_out(ramp(t, 0.2, dur - 1.5))
    d.line([(x0, y), (lerp(x0, x1, grow), y)], fill=with_alpha(DIM, 0.9), width=4)
    for i, (date, text, col) in enumerate(events):
        x = x0 + i * (x1 - x0) / (len(events) - 1)
        if (x - x0) / (x1 - x0) > grow + 0.001:
            continue
        a = ramp(t, 0.2 + grow * 0 + i * (dur - 1.5) / len(events), 0.8 + i * (dur - 1.5) / len(events))
        a = max(a, 0.0)
        up = i % 2 == 0
        d.ellipse([x - 12, y - 12, x + 12, y + 12], fill=with_alpha(col, a))
        d.line([(x, y + (-20 if up else 20)), (x, y + (-90 if up else 90))], fill=with_alpha(col, a), width=3)
        lines = wrap(d, text, font("serif", 30), 320)
        block = [(date, font("oswald", 46, 700), col)] + [(l, font("serif", 30), INK) for l in lines]
        heights = [56] + [36] * len(lines)
        yy = (y - 110 - sum(heights)) if up else (y + 110)
        for (txt, f, c), hh in zip(block, heights):
            d.text((x, yy + hh / 2), txt, font=f, fill=with_alpha(c, a), anchor="mm")
            yy += hh
    return img


def camp_names(t, dur, **_):
    img = canvas()
    d = Draw(img)
    names = [("ROVNOST", "Equality"), ("SVORNOST", "Concord"), ("BRATRSTVÍ", "Brotherhood")]
    for i, (cz, en) in enumerate(names):
        t0 = 0.3 + i * 1.2
        a = ramp(t, t0, t0 + 0.7)
        x = W / 2 + (i - 1) * 560
        d.text((x, H / 2 - 40), cz, font=font("display", 130), fill=with_alpha(INK, a), anchor="mm")
        d.text((x, H / 2 + 50), f"“{en}”", font=font("serif", 50), fill=with_alpha(AMBER, ramp(t, t0 + 0.5, t0 + 1.1)),
               anchor="mm")
    # barbed wire drawn across the bottom
    wa = ease_in_out(ramp(t, 1.0, dur - 0.5))
    y = H - 230
    xe = 80 + (W - 160) * wa
    d.line([(80, y), (xe, y)], fill=(170, 170, 165, 230), width=3)
    d.line([(80, y + 6), (xe, y + 6)], fill=(120, 120, 118, 200), width=2)
    xb = 120
    while xb < xe:
        d.line([(xb - 12, y - 12), (xb + 12, y + 16)], fill=(190, 190, 185, 240), width=3)
        d.line([(xb + 12, y - 12), (xb - 12, y + 16)], fill=(190, 190, 185, 240), width=3)
        xb += 90
    d.text((W / 2, H - 140), "Mines – and labour camps – at Jáchymov", font=font("serif", 32),
           fill=with_alpha(DIM, ramp(t, 3.0, 3.8)), anchor="mm")
    return img


@functools.lru_cache(maxsize=1)
def _person_icon(size=22):
    s = size * 4
    im = Image.new("L", (s, s * 2), 0)
    d = ImageDraw.Draw(im)
    d.ellipse([s * 0.3, 0, s * 0.7, s * 0.4], fill=255)
    d.rounded_rectangle([s * 0.18, s * 0.46, s * 0.82, s * 1.3], s * 0.15, fill=255)
    d.rectangle([s * 0.26, s * 1.2, s * 0.46, s * 1.95], fill=255)
    d.rectangle([s * 0.54, s * 1.2, s * 0.74, s * 1.95], fill=255)
    return im.resize((size, size * 2), Image.LANCZOS)


def prisoners(t, dur, **_):
    img = canvas()
    d = Draw(img)
    icon = _person_icon(16)
    cols, rows = 50, 13  # 650 figures x 100 = 65,000
    gx0, gy0, sx, sy = 260, 300, 28, 44
    filled = int(cols * rows * ease_in_out(ramp(t, 0.8, dur - 2.0)))
    off = Image.new("RGB", icon.size, (52, 54, 55))
    on = Image.new("RGB", icon.size, AMBER)
    for i in range(cols * rows):
        r, c = divmod(i, cols)
        img.paste(on if i < filled else off, (gx0 + c * sx, gy0 + r * sy), icon)
    d = Draw(img)
    n = filled * 100
    d.text((W / 2, 170), f"≈ {n:,}", font=font("display", 150), fill=INK, anchor="mm")
    d.text((W / 2, H - 120), "prisoners passed through the uranium camps, 1949–1961  ·  each figure = 100  ·  historians' estimate",
           font=font("serif", 30), fill=DIM, anchor="mm")
    return img


def mukl(t, dur, **_):
    img = canvas()
    d = Draw(img)
    words = [("M", "UŽ"), ("U", "RČENÝ"), ("K", ""), ("L", "IKVIDACI")]
    f = font("display", 180)
    expand = ease_in_out(ramp(t, 1.6, 3.2))
    gap = 26
    widths = [d.textlength(a, font=f) + d.textlength(b, font=f) * expand for a, b in words]
    total = sum(widths) + gap * (len(words) - 1) * (0.2 + 0.8 * expand)
    x = W / 2 - total / 2
    a0 = ramp(t, 0.2, 0.9)
    for (cap, rest), w in zip(words, widths):
        d.text((x, H / 2 - 60), cap, font=f, fill=with_alpha(URANIUM, a0), anchor="ls")
        if expand > 0.02 and rest:
            cw = d.textlength(cap, font=f)
            layer = Image.new("RGBA", (int(d.textlength(rest, font=f)) + 10, 260), (0, 0, 0, 0))
            Draw(layer).text((0, 200), rest, font=f, fill=with_alpha(INK, expand), anchor="ls")
            crop = layer.crop((0, 0, max(1, int(layer.width * expand)), 260))
            img.paste(crop, (int(x + cw), int(H / 2 - 60 - 200)), crop)
        x += w + gap * (0.2 + 0.8 * expand)
    d = Draw(img)
    a = ramp(t, 3.3, 4.1)
    text_center(d, (W / 2, H / 2 + 80), "“a man destined for liquidation”", font("serif", 64), with_alpha(INK, a))
    text_center(d, (W / 2, H / 2 + 170), "how former prisoners still explain the word mukl", font("serif", 32),
                with_alpha(DIM, a))
    return img


def tower_diagram(t, dur, **_):
    img = canvas()
    d = Draw(img)
    tx, ty, tw, th = W / 2 - 170, 150, 340, 800
    floors = 7
    a = ramp(t, 0.1, 0.8)
    d.rectangle([tx, ty, tx + tw, ty + th], outline=with_alpha((170, 70, 50), a), width=6)
    for k in range(1, floors):
        y = ty + k * th / floors
        d.line([(tx, y), (tx + tw, y)], fill=with_alpha((120, 60, 46), a * 0.7), width=2)
    # sieves: dashed lines on a few floors
    for k in (2, 4, 6):
        y = ty + k * th / floors - 30
        for x in range(int(tx + 30), int(tx + tw - 30), 22):
            d.line([(x, y), (x + 12, y)], fill=with_alpha(AMBER, a), width=4)
    # carts hauled up the left side
    for k in range(4):
        u = ((t * 0.18 + k / 4) % 1)
        y = ty + th - u * th
        d.rectangle([tx - 90, y - 18, tx - 30, y + 18], fill=with_alpha(STEEL, a), outline=(0, 0, 0, 180))
    d.line([(tx - 60, ty + th), (tx - 60, ty)], fill=with_alpha(DIM, a * 0.6), width=2)
    # ore falling through the floors, dust drifting out
    rng = np.random.default_rng(12)
    for k in range(80):
        ph, xo = rng.random(), rng.uniform(40, tw - 40)
        u = (t * 0.25 + ph) % 1
        y = ty + 40 + u * (th - 80)
        x = tx + xo + math.sin(u * 20 + k) * 6
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=with_alpha(URANIUM, a * 0.9))
    dust = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dust)
    for k in range(120):
        ph = rng.random()
        u = (t * 0.12 + ph) % 1
        side = -1 if k % 2 else 1
        x = W / 2 + side * (tw / 2 + u * 420) + math.sin(t + k) * 20
        y = ty + rng.uniform(50, th - 50) - u * 80
        r = 3 + u * 9
        dd.ellipse([x - r, y - r, x + r, y + r], fill=with_alpha(URANIUM, a * 0.35 * (1 - u)))
    dust = dust.filter(ImageFilter.GaussianBlur(5))
    base = img.convert("RGBA")
    base.alpha_composite(dust)
    img = base.convert("RGB")
    d = Draw(img)
    la = ramp(t, 1.0, 1.8)
    d.text((tx - 120, ty + 40), "Ore hauled\nto the top floor", font=font("serif", 32), fill=with_alpha(INK, la), anchor="ra",
           align="right")
    d.text((tx + tw + 50, ty + 2 * th / floors - 40), "Sieves", font=font("serif", 32), fill=with_alpha(AMBER, la), anchor="la")
    d.text((tx + tw + 50, ty + 4.6 * th / floors), "Radioactive dust,\nno protection", font=font("serif", 32),
           fill=with_alpha(URANIUM, ramp(t, 2.0, 2.8)), anchor="la")
    d.text((W - 60, H - 50), "Schematic", font=font("sans", 22), fill=with_alpha(DIM, 0.8), anchor="rm")
    return img


def production_counter(t, dur, **_):
    img = canvas()
    img = draw_particles(img, t, seed=31, n=80, alpha=0.45)
    d = Draw(img)
    x = ease_out(ramp(t, 0.5, dur - 1.5))
    yr = int(lerp(1946, 1990, x))
    n = int(round(100000 * x / 500) * 500)
    d.text((W / 2, H / 2 - 170), f"1946 – {yr}", font=font("oswald", 60, 400), fill=DIM, anchor="mm")
    d.text((W / 2, H / 2), f"≈ {n:,}", font=font("display", 260), fill=INK, anchor="mm")
    d.text((W / 2, H / 2 + 160), "tonnes of uranium mined in Czechoslovakia", font=font("serif", 46), fill=AMBER,
           anchor="mm")
    return img


def credits_roll(t, dur, pages=(), **_):
    """pages: list of (heading, [lines]) shown as successive two-column pages."""
    img = canvas()
    d = Draw(img)
    per = dur / max(1, len(pages))
    i = min(int(t / per), len(pages) - 1)
    lt = t - i * per
    a = ramp(lt, 0, 0.6) * (1 - ramp(lt, per - 0.6, per))
    heading, lines = pages[i]
    d.text((W / 2, 110), heading.upper(), font=font("oswald", 46, 500), fill=with_alpha(URANIUM, a), anchor="mm")
    f = font("sans", 21)
    colw = (W - 240) / 2
    half = (len(lines) + 1) // 2
    for c in range(2):
        y = 190
        for line in lines[c * half:(c + 1) * half]:
            for k, l in enumerate(wrap(d, line, f, colw - 30)):
                d.text((120 + c * colw, y), l, font=f, fill=with_alpha(INK if k == 0 else DIM, a))
                y += 27
            y += 6
    return img


ANIMS = {f.__name__: f for f in [title, chapter, dateline, dedication, map_zoom_jachymov, map_distance, train_route,
                                 camp_map, etymology, elements, radon, agreement, bar_chart, plutonium_chain,
                                 timeline_1948, camp_names, prisoners, mukl, tower_diagram, production_counter,
                                 credits_roll]}
