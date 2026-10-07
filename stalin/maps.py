"""Paper maps (V3): a vector map of Europe from Natural Earth and a Prague street
map from CARTO tiles, both recoloured onto the paper texture."""
import json
import math
import os
import subprocess
import urllib.request

import cv2
import numpy as np

import vox as V
from shots import Shot, register, tag_img, annotate, mark_sfx
from vox import H, INK, RED, W, WHITE, clamp, ease_back, ease_io, lerp, lin

GEO = os.path.join(V.BUILD, "geo")
NE_URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
          "ne_50m_admin_0_countries.geojson")
LAT0 = 50.0
KX = math.cos(math.radians(LAT0))

LAND = (214, 203, 178)
WATER = (190, 199, 194)
GROUPS = {
    "CS": ["CZE", "SVK"],
    "USSR": ["RUS", "UKR", "BLR", "LTU", "LVA", "EST", "MDA", "GEO", "ARM", "AZE", "KAZ", "UZB", "TKM",
             "KGZ", "TJK"],
}


def _countries():
    os.makedirs(GEO, exist_ok=True)
    path = os.path.join(GEO, "ne_50m_admin_0_countries.geojson")
    if not os.path.exists(path):
        subprocess.run(["curl", "-sSL", "--retry", "3", "-o", path, NE_URL], check=True)
    d = json.load(open(path))
    out = {}
    for ft in d["features"]:
        p = ft["properties"]
        iso = p.get("ADM0_A3") or p.get("ISO_A3")
        g = ft["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        rings = []
        for poly in polys:
            for ring in poly[:1]:                 # outer rings only
                a = np.array(ring, np.float64)
                if a[:, 0].max() < -30 or a[:, 0].min() > 80 or a[:, 1].max() < 25:
                    continue
                rings.append(np.stack([a[:, 0] * KX, -a[:, 1]], 1))
        if rings:
            out[iso] = rings
    return out


_C = None


def countries():
    global _C
    if _C is None:
        _C = _countries()
    return _C


def proj(lon, lat):
    return lon * KX, -lat


class Cam:
    def __init__(self, lon, lat, width_deg):
        self.cx, self.cy = proj(lon, lat)
        self.s = W / (width_deg * KX)

    def pts(self, xy):
        return np.stack([(xy[:, 0] - self.cx) * self.s + W / 2, (xy[:, 1] - self.cy) * self.s + H / 2], 1)

    def pt(self, lon, lat):
        x, y = proj(lon, lat)
        return (x - self.cx) * self.s + W / 2, (y - self.cy) * self.s + H / 2


def interp_cam(keys, t):
    """keys: [(t, lon, lat, width_deg)]; log-interpolated zoom with ease in/out."""
    if t <= keys[0][0]:
        return Cam(*keys[0][1:])
    for a, b in zip(keys, keys[1:]):
        if t <= b[0]:
            u = ease_io(lin(t, a[0], b[0]))
            w = math.exp(lerp(math.log(a[3]), math.log(b[3]), u))
            return Cam(lerp(a[1], b[1], u), lerp(a[2], b[2], u), w)
    return Cam(*keys[-1][1:])


def tint(f, mask, color, alpha=1.0):
    m = mask.astype(np.float32)[..., None] / 255 * alpha
    mult = f.astype(np.float32) * np.array(color, np.float32) / 235
    f[:] = np.clip(f + (mult - f) * m, 0, 255).astype(np.uint8)


@register("map")
class Map(Shot):
    """keys: [(t, lon, lat, width_deg)], fills: [{group|iso, color, at}],
    pins: [{lon, lat, at, label}], labels: [{lon, lat, text, at, size}], route: [...]"""
    grain = 3.0

    def setup(self):
        s = self.spec
        self.paper = V.paper(seed=21)
        for p in s.get("pins", []):
            self.add(p.get("at", 0), "ping", 0.8)
        for lb in s.get("labels", []):
            self.add(lb.get("at", 0), "pop", 0.4)
        for k in range(len(s["keys"]) - 1):
            if s["keys"][k + 1][0] - s["keys"][k][0] > 0.3:
                self.add(s["keys"][k][0], "whoosh", 0.7)
        self.marks = s.get("marks", [])
        mark_sfx(self, self.marks)

    def draw(self, t):
        s = self.spec
        cam = interp_cam(s["keys"], t)
        f = V.cover(self.paper, W, H, 1.0)
        land = np.zeros((H, W), np.uint8)
        coast = []
        hil = {}
        for fl in s.get("fills", []):
            if t < fl.get("at", 0):
                continue
            for iso in GROUPS.get(fl.get("group"), [fl.get("iso")]):
                hil[iso] = fl
        hmasks = {}
        for iso, rings in countries().items():
            for r in rings:
                p = cam.pts(r)
                if p[:, 0].max() < -50 or p[:, 0].min() > W + 50 or p[:, 1].max() < -50 or p[:, 1].min() > H + 50:
                    continue
                q = np.round(p * 4).astype(np.int32)
                cv2.fillPoly(land, [q], 255, cv2.LINE_AA, shift=2)
                coast.append(q)
                if iso in hil:
                    key = id(hil[iso])
                    if key not in hmasks:
                        hmasks[key] = (hil[iso], np.zeros((H, W), np.uint8))
                    cv2.fillPoly(hmasks[key][1], [q], 255, cv2.LINE_AA, shift=2)
        tint(f, 255 - land, WATER)
        tint(f, land, LAND)
        for fl, m in hmasks.values():
            u = ease_io(lin(t, fl.get("at", 0), fl.get("at", 0) + 0.5))
            tint(f, m, fl.get("color", RED), 0.9 * u)
            if fl.get("outline", True):
                cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                cv2.drawContours(f, cnts, -1, (60, 20, 20), 2, cv2.LINE_AA)
        cv2.polylines(f, coast, True, (120, 110, 95), 1, cv2.LINE_AA, shift=2)
        for r in s.get("routes", []):
            pts = np.array([cam.pt(*ll) for ll in r["pts"]])
            u = ease_io(lin(t, r["at"], r["at"] + r.get("d", 1.5)))
            V.draw_path(f, densify(pts), u, RED, 6, head=True)
        for lb in s.get("labels", []):
            if t < lb.get("at", 0):
                continue
            x, y = cam.pt(lb["lon"], lb["lat"])
            u = lin(t, lb.get("at", 0), lb.get("at", 0) + 0.3)
            im = V.text_img(lb["text"], lb.get("font", "oswald"), lb.get("size", 46), tuple(lb.get("color", INK)),
                            tracking=lb.get("tracking", 6))
            V.place(f, im, x, y, 0.85 + 0.15 * ease_back(u), 0, clamp(u * 2), shadow=False)
        for p in s.get("pins", []):
            if t < p.get("at", 0):
                continue
            x, y = cam.pt(p["lon"], p["lat"])
            draw_pin(f, x, y, t - p.get("at", 0), p.get("label"), p.get("side", "right"))
        annotate(f, t, self.marks, self.seed)
        return f


def densify(pts, n=40):
    out = []
    for a, b in zip(pts, pts[1:]):
        for u in np.linspace(0, 1, n, endpoint=False):
            out.append(a + (b - a) * u)
    out.append(pts[-1])
    return np.array(out)


def draw_pin(f, x, y, dt, label=None, side="right"):
    u = ease_back(lin(dt, 0, 0.3))
    ph = (dt % 1.2) / 1.2
    if dt > 0.3:
        r = int(10 + 26 * ph)
        ov = f.copy()
        cv2.circle(ov, (int(x), int(y)), r, RED, 3, cv2.LINE_AA)
        cv2.addWeighted(ov, (1 - ph) * 0.8, f, 1 - (1 - ph) * 0.8, 0, dst=f)
    cv2.circle(f, (int(x), int(y)), max(int(15 * u), 1), WHITE, -1, cv2.LINE_AA)
    cv2.circle(f, (int(x), int(y)), max(int(10 * u), 1), RED, -1, cv2.LINE_AA)
    if label and dt > 0.15:
        im = tag_img(label, 40)
        a = clamp((dt - 0.15) * 4)
        if side == "right":
            V.place(f, im, x + 30, y, 0.9 + 0.1 * a, 0, a, shadow=True, ax=0, ay=0.5)
        else:
            V.place(f, im, x - 30, y, 0.9 + 0.1 * a, 0, a, shadow=True, ax=1, ay=0.5)


# ---------------------------------------------------------------- Prague street map
TILE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
TS = 256


def tile_xy(lon, lat, z):
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def mosaic(lon, lat, z, nx=10, ny=7):
    """Stitch tiles around a point; returns (img, x0_tile, y0_tile)."""
    os.makedirs(os.path.join(GEO, "tiles"), exist_ok=True)
    cx, cy = tile_xy(lon, lat, z)
    x0, y0 = int(cx) - nx // 2, int(cy) - ny // 2
    out_path = os.path.join(GEO, f"mosaic_{z}_{x0}_{y0}_{nx}x{ny}.png")
    if os.path.exists(out_path):
        return V.load_rgb(out_path), x0, y0
    img = np.zeros((ny * TS, nx * TS, 3), np.uint8)
    for j in range(ny):
        for i in range(nx):
            p = os.path.join(GEO, "tiles", f"{z}_{x0 + i}_{y0 + j}.jpg")
            if not os.path.exists(p):
                req = urllib.request.Request(TILE_URL.format(z=z, x=x0 + i, y=y0 + j),
                                             headers={"User-Agent": "asddsadd-film/1.0"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    open(p, "wb").write(r.read())
            t = V.load_rgb(p)
            img[j * TS:(j + 1) * TS, i * TS:(i + 1) * TS] = cv2.resize(t, (TS, TS))
    cv2.imwrite(out_path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    return img, x0, y0


def recolor_city(img):
    """Esri light-gray canvas -> paper palette: water blue-grey, parks olive, streets light."""
    f = img.astype(np.float32)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    lum = f.mean(2)
    water = np.clip((b - g - 2) / 4, 0, 1) * (lum < 226)
    park = np.clip((g - r - 1) / 4, 0, 1) * (1 - water)
    v = np.clip((lum - 236) / 16, -1.5, 1)[..., None]
    out = np.array(LAND, np.float32) + v * 34
    out = out * (1 - park[..., None]) + np.array((192, 196, 160), np.float32) * park[..., None]
    out = out * (1 - water[..., None]) + np.array(WATER, np.float32) * 0.92 * water[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)


@register("city")
class City(Shot):
    """Prague map. keys: [(t, lon, lat, zoom)] (zoom in web-mercator levels, fractional);
    pins/labels as in Map. Uses one recoloured mosaic at level z."""
    grain = 3.0

    def setup(self):
        s = self.spec
        self.z = s.get("z", 15)
        lon, lat = s.get("center", (14.4172, 50.0944))
        raw, self.x0, self.y0 = mosaic(lon, lat, self.z, s.get("nx", 10), s.get("ny", 7))
        col = recolor_city(raw)
        pap = V.cover(V.paper(seed=23), col.shape[1], col.shape[0])
        self.img = (col.astype(np.float32) * pap.astype(np.float32) / 228).clip(0, 255).astype(np.uint8)
        for p in s.get("pins", []):
            self.add(p.get("at", 0), "ping", 0.8)
        for rg in s.get("rings", []):
            self.add(rg["at"], "sub", 0.8)
        for k in range(len(s["keys"]) - 1):
            if s["keys"][k + 1][0] - s["keys"][k][0] > 0.3:
                self.add(s["keys"][k][0], "whoosh", 0.6)
        self.marks = s.get("marks", [])
        mark_sfx(self, self.marks)

    def cam(self, t):
        keys = self.spec["keys"]
        if t <= keys[0][0]:
            k = keys[0][1:]
        elif t >= keys[-1][0]:
            k = keys[-1][1:]
        else:
            for a, b in zip(keys, keys[1:]):
                if t <= b[0]:
                    u = ease_io(lin(t, a[0], b[0]))
                    k = (lerp(a[1], b[1], u), lerp(a[2], b[2], u), lerp(a[3], b[3], u))
                    break
        lon, lat, zoom = k
        tx, ty = tile_xy(lon, lat, self.z)
        px, py = (tx - self.x0) * TS, (ty - self.y0) * TS
        s = 2 ** (zoom - self.z)
        return px, py, s

    def pt(self, cam, lon, lat):
        px, py, s = cam
        tx, ty = tile_xy(lon, lat, self.z)
        return (W / 2 + ((tx - self.x0) * TS - px) * s, H / 2 + ((ty - self.y0) * TS - py) * s)

    def draw(self, t):
        s = self.spec
        cam = self.cam(t)
        px, py, sc = cam
        M = np.float32([[sc, 0, W / 2 - px * sc], [0, sc, H / 2 - py * sc]])
        f = cv2.warpAffine(self.img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        for rg in s.get("rings", []):
            x, y = self.pt(cam, rg["lon"], rg["lat"])
            for k in range(rg.get("n", 5)):
                st = rg["at"] + k * rg.get("every", 0.35)
                u = lin(t, st, st + rg.get("d", 1.6))
                if 0 < u < 1:
                    ov = f.copy()
                    cv2.circle(ov, (int(x), int(y)), int(40 + u * rg.get("r", 1100)), RED, 6, cv2.LINE_AA)
                    cv2.addWeighted(ov, (1 - u) * 0.9, f, 1 - (1 - u) * 0.9, 0, dst=f)
        for lb in s.get("labels", []):
            if t < lb.get("at", 0):
                continue
            x, y = self.pt(cam, lb["lon"], lb["lat"])
            u = lin(t, lb.get("at", 0), lb.get("at", 0) + 0.3)
            im = V.text_img(lb["text"], lb.get("font", "oswald"), lb.get("size", 44), tuple(lb.get("color", INK)),
                            tracking=lb.get("tracking", 5))
            V.place(f, im, x, y, 0.85 + 0.15 * ease_back(u), lb.get("rot", 0), clamp(u * 2), shadow=False)
        for p in s.get("pins", []):
            if t < p.get("at", 0):
                continue
            x, y = self.pt(cam, p["lon"], p["lat"])
            draw_pin(f, x, y, t - p.get("at", 0), p.get("label"), p.get("side", "right"))
        annotate(f, t, self.marks, self.seed)
        return f
