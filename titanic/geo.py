"""Flat animated maps (Natural Earth land, public domain) drawn as vectors, so the
camera can zoom from the whole North Atlantic down to a few miles of sea."""
import json
import math
import os
from functools import lru_cache

import cv2
import numpy as np

import look

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEO = os.path.join(ROOT, "build", "titanic", "geo")
LAT0 = 47.0                      # equirectangular, scaled for the mid-Atlantic
KX = math.cos(math.radians(LAT0))

PLACES = {
    "southampton": (50.90, -1.40),
    "cherbourg": (49.64, -1.62),
    "queenstown": (51.85, -8.29),
    "newyork": (40.71, -74.01),
    "halifax": (44.65, -63.57),
    "caperace": (46.66, -53.07),
    # Titanic's CQD position as sent by wireless: 41°46'N 50°14'W
    "titanic": (41.767, -50.233),
    # The Californian stopped in ice to the north; estimates of the distance run
    # from ~5-10 miles (British inquiry) to 19 miles (her captain). Placed ~15 nmi N.
    "californian": (42.017, -50.30),
    # The Carpathia, 58 nmi to the south-east when she heard the call (approximate).
    "carpathia": (41.21, -49.18),
}


def nm_to_deg(nm):
    return nm / 60.0


@lru_cache(maxsize=1)
def land():
    """Land polygons (lists of lon/lat rings) inside the North Atlantic window."""
    with open(os.path.join(GEO, "ne_50m_land.geojson")) as f:
        gj = json.load(f)
    rings = []
    for feat in gj["features"]:
        g = feat["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            ring = np.array(poly[0], np.float64)
            if (ring[:, 0].max() < -100 or ring[:, 0].min() > 40 or ring[:, 1].max() < 20 or
                    ring[:, 1].min() > 75):
                continue
            rings.append(ring)
    return rings


class MapCam:
    """Camera over the map: centre (lat, lon) and pixels per degree of latitude."""

    def __init__(self, lat, lon, ppd):
        self.lat, self.lon, self.ppd = lat, lon, ppd

    def xy(self, lat, lon):
        return (look.W / 2 + (lon - self.lon) * KX * self.ppd,
                look.H / 2 - (lat - self.lat) * self.ppd)

    def pts(self, ring):
        x = look.W / 2 + (ring[:, 0] - self.lon) * KX * self.ppd
        y = look.H / 2 - (ring[:, 1] - self.lat) * self.ppd
        return np.stack([x, y], 1)


def lerp_cam(a, b, u):
    """Zoom between two cameras in log space so the move feels even."""
    la, lb = math.log(a.ppd), math.log(b.ppd)
    ppd = math.exp(look.lerp(la, lb, u))
    # keep the motion of the centre proportional to the zoom
    k = (ppd - a.ppd) / (b.ppd - a.ppd) if b.ppd != a.ppd else u
    return MapCam(look.lerp(a.lat, b.lat, k), look.lerp(a.lon, b.lon, k), ppd)


def base(cam, sea=look.SEA, land_col=look.LAND, grat=True):
    """The flat map: sea, land and a faint graticule."""
    f = np.empty((look.H, look.W, 3), np.uint8)
    f[:] = sea
    # faint paper texture over the sea so it matches the collage
    tex = look.paper(w=look.W, h=look.H, seed=11, grid=0, tint=sea, crumple=0.5)
    f[:] = tex
    if grat:
        step = 5 if cam.ppd < 80 else 1 if cam.ppd < 400 else 0.25
        col = tuple(min(255, c + 16) for c in sea)
        lat0 = math.floor((cam.lat - 20) / step) * step
        lon0 = math.floor((cam.lon - 40) / step) * step
        for k in range(200):
            la = lat0 + k * step
            x0, y = cam.xy(la, cam.lon - 90)
            x1, _ = cam.xy(la, cam.lon + 90)
            if -10 < y < look.H + 10:
                cv2.line(f, (int(x0), int(y)), (int(x1), int(y)), col, 1, cv2.LINE_AA)
        for k in range(400):
            lo = lon0 + k * step
            x, y0 = cam.xy(cam.lat + 60, lo)
            _, y1 = cam.xy(cam.lat - 60, lo)
            if -10 < x < look.W + 10:
                cv2.line(f, (int(x), int(y0)), (int(x), int(y1)), col, 1, cv2.LINE_AA)
    polys = []
    for ring in land():
        p = cam.pts(ring)
        if p[:, 0].max() < -50 or p[:, 0].min() > look.W + 50 or p[:, 1].max() < -50 or \
                p[:, 1].min() > look.H + 50:
            continue
        polys.append(np.round(p * 8).astype(np.int32))
    if polys:
        cv2.fillPoly(f, polys, land_col, cv2.LINE_AA, shift=3)
        edge = tuple(max(0, c - 40) for c in land_col)
        cv2.polylines(f, polys, True, edge, 1, cv2.LINE_AA, shift=3)
    return f


def route(frame, cam, path, u, color=look.WHITE, width=4, dashed=True, alpha=1.0):
    """Draw the first u of a lat/lon path (great-circle-ish via interpolation)."""
    pts = []
    for (la0, lo0), (la1, lo1) in zip(path[:-1], path[1:]):
        for s in np.linspace(0, 1, 40, endpoint=False):
            pts.append(cam.xy(la0 + (la1 - la0) * s, lo0 + (lo1 - lo0) * s))
    pts.append(cam.xy(*path[-1]))
    pts = np.array(pts, np.float32)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    L = cum[-1] * look.clamp(u)
    if L <= 0:
        return None
    ov = frame.copy() if alpha < 1 else frame
    dash, gap = (18, 12) if dashed else (1e9, 0)
    s = 0.0
    while s < L:
        e = min(s + dash, L)
        a = np.interp(s, cum, np.arange(len(cum)))
        b = np.interp(e, cum, np.arange(len(cum)))
        ia, ib = int(a), int(b)
        seg_pts = [_at(pts, a)] + [pts[k] for k in range(ia + 1, ib + 1)] + [_at(pts, b)]
        cv2.polylines(ov, [np.round(np.array(seg_pts) * 4).astype(np.int32)], False, color, width,
                      cv2.LINE_AA, shift=2)
        s = e + gap
    if alpha < 1:
        cv2.addWeighted(ov, alpha, frame, 1 - alpha, 0, dst=frame)
    k = np.interp(L, cum, np.arange(len(cum)))
    return _at(pts, k)


def _at(pts, k):
    i = min(int(k), len(pts) - 2)
    f = k - i
    return pts[i] + (pts[i + 1] - pts[i]) * f


def marker(frame, x, y, t, t0, color=look.CORAL, r=12, pulse=True):
    """A dot that pops in at t0 and sends out slow pulse rings."""
    if t < t0:
        return
    s, a = look.pop(t, t0)
    if pulse:
        for k in range(2):
            ph = ((t - t0) * 0.7 + k * 0.5) % 1.0
            rr = r + ph * r * 4
            ov = frame.copy()
            cv2.circle(ov, (int(x), int(y)), int(rr), color, 3, cv2.LINE_AA)
            cv2.addWeighted(ov, (1 - ph) * 0.8 * a, frame, 1 - (1 - ph) * 0.8 * a, 0, dst=frame)
    cv2.circle(frame, (int(x), int(y)), int(r * s + 3), look.WHITE, -1, cv2.LINE_AA)
    cv2.circle(frame, (int(x), int(y)), int(r * s), color, -1, cv2.LINE_AA)


def ring(frame, x, y, r, u, color=look.WHITE, width=2, alpha=0.9, dashed=True):
    """A distance ring that draws itself around (x, y)."""
    if u <= 0:
        return
    n = 160
    th = np.linspace(-math.pi / 2, -math.pi / 2 + 2 * math.pi * look.ease_out(u), n)
    pts = np.stack([x + r * np.cos(th), y + r * np.sin(th)], 1)
    ov = frame.copy()
    step = 2 if dashed else 1
    for k in range(0, n - 1, step):
        cv2.line(ov, tuple(np.int32(pts[k])), tuple(np.int32(pts[k + 1])), color, width, cv2.LINE_AA)
    cv2.addWeighted(ov, alpha, frame, 1 - alpha, 0, dst=frame)
