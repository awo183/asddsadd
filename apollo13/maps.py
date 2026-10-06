"""Flat animated maps from Natural Earth: muted land on paper, thin borders, one accent.

A base map is drawn once at high resolution in an equirectangular projection
(x scaled by cos(lat0)); views crop and scale it for zooms.
"""
import json
import math
import os

import cv2
import numpy as np

import look as lk

MAPS = None          # set by scenes.py to build/apollo13/assets/maps


def _rings(geom):
    if geom["type"] == "Polygon":
        return geom["coordinates"]
    if geom["type"] == "MultiPolygon":
        return [r for poly in geom["coordinates"] for r in poly]
    return []


class BaseMap:
    """lon0..lon1, lat0..lat1 drawn at ppd pixels per degree of latitude."""

    def __init__(self, name, lon0, lon1, lat0, lat1, ppd, states=False, shift360=False, labels=()):
        self.lon0, self.lon1, self.lat0, self.lat1, self.ppd = lon0, lon1, lat0, lat1, ppd
        self.kx = math.cos(math.radians((lat0 + lat1) / 2))
        self.shift = shift360
        self.w = int((lon1 - lon0) * ppd * self.kx)
        self.h = int((lat1 - lat0) * ppd)
        cache = os.path.join(MAPS, f"base_{name}_{self.w}x{self.h}.png")
        if os.path.exists(cache):
            self.rgba = cv2.imread(cache, cv2.IMREAD_UNCHANGED)[..., [2, 1, 0, 3]]
            return
        land = np.zeros((self.h, self.w), np.uint8)
        edges = np.zeros((self.h, self.w), np.uint8)
        countries = json.load(open(os.path.join(MAPS, "ne_50m_admin_0_countries.geojson")))["features"]
        for ft in countries:
            for ring in _rings(ft["geometry"]):
                pts = self.poly(ring)
                if pts is not None:
                    cv2.fillPoly(land, [pts], 255, cv2.LINE_AA)
                    cv2.polylines(edges, [pts], True, 255, max(2, ppd // 20), cv2.LINE_AA)
        if states:
            st = json.load(open(os.path.join(MAPS, "ne_50m_admin_1_states_provinces_lakes.geojson")))["features"]
            for ft in st:
                if ft["properties"].get("admin") != "United States of America":
                    continue
                for ring in _rings(ft["geometry"]):
                    pts = self.poly(ring)
                    if pts is not None:
                        cv2.polylines(edges, [pts], True, 170, max(1, ppd // 30), cv2.LINE_AA)
        if self.shift:      # small Pacific islands matter on the splashdown map
            isl = json.load(open(os.path.join(MAPS, "ne_10m_minor_islands.geojson")))["features"]
            for ft in isl:
                for ring in _rings(ft["geometry"]):
                    pts = self.poly(ring)
                    if pts is not None:
                        cv2.fillPoly(land, [pts], 255, cv2.LINE_AA)
                        cv2.polylines(edges, [pts], True, 255, 2, cv2.LINE_AA)
        rgba = np.zeros((self.h, self.w, 4), np.uint8)
        rgba[..., :3] = lk.LAND
        rgba[..., 3] = land
        e = edges.astype(np.float32)[..., None] / 255.0
        rgba[..., :3] = (rgba[..., :3] * (1 - e * 0.85) + np.array(lk.LAND_EDGE) * e * 0.85).astype(np.uint8)
        rgba[..., 3] = np.maximum(rgba[..., 3], (edges * 0.6).astype(np.uint8))
        # a soft "coastline shadow" so land sits on the paper like a cut-out
        sh = cv2.GaussianBlur(land, (0, 0), ppd / 18)
        shadow = np.zeros_like(rgba)
        shadow[..., :3] = (205, 196, 176)
        shadow[..., 3] = (sh * 0.35).astype(np.uint8)
        a1 = rgba[..., 3:4].astype(np.float32) / 255
        a2 = shadow[..., 3:4].astype(np.float32) / 255
        out_a = a1 + a2 * (1 - a1)
        out_c = (rgba[..., :3] * a1 + shadow[..., :3] * a2 * (1 - a1)) / np.maximum(out_a, 1e-6)
        self.rgba = np.concatenate([out_c.astype(np.uint8), (out_a * 255).astype(np.uint8)], 2)
        cv2.imwrite(cache, self.rgba[..., [2, 1, 0, 3]])

    def xy(self, lat, lon):
        if self.shift and lon < 0:
            lon += 360
        return (lon - self.lon0) * self.ppd * self.kx, (self.lat1 - lat) * self.ppd

    def poly(self, ring):
        arr = np.array(ring, np.float64)
        if self.shift:
            arr[:, 0] = np.where(arr[:, 0] < 0, arr[:, 0] + 360, arr[:, 0])
        if arr[:, 0].max() < self.lon0 - 5 or arr[:, 0].min() > self.lon1 + 5 or \
                arr[:, 1].max() < self.lat0 - 5 or arr[:, 1].min() > self.lat1 + 5:
            return None
        x = (arr[:, 0] - self.lon0) * self.ppd * self.kx
        y = (self.lat1 - arr[:, 1]) * self.ppd
        return np.stack([x, y], 1).astype(np.int32)


class MapView:
    """A camera on a BaseMap: centre (lat, lon) and scale (screen px per map px)."""

    def __init__(self, base, lat, lon, scale):
        self.b, self.lat, self.lon, self.s = base, lat, lon, scale

    def matrix(self):
        cx, cy = self.b.xy(self.lat, self.lon)
        return np.float32([[self.s, 0, lk.W / 2 - cx * self.s], [0, self.s, lk.H / 2 - cy * self.s]])

    def draw(self, frame):
        warped = cv2.warpAffine(self.b.rgba, self.matrix(), (lk.W, lk.H), flags=cv2.INTER_AREA,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        lk.blit(frame, warped, 0, 0)

    def pt(self, lat, lon):
        x, y = self.b.xy(lat, lon)
        cx, cy = self.b.xy(self.lat, self.lon)
        return lk.W / 2 + (x - cx) * self.s, lk.H / 2 + (y - cy) * self.s


def lerp_view(base, a, b, u):
    """Interpolate two (lat, lon, scale) views; zoom interpolates in log space."""
    u = lk.ease_in_out(u)
    lat = lk.lerp(a[0], b[0], u)
    lon = lk.lerp(a[1], b[1], u)
    s = math.exp(lk.lerp(math.log(a[2]), math.log(b[2]), u))
    return MapView(base, lat, lon, s)


def route_points(mv, a, b, bend=0.22, n=60):
    """A gently arcing route between two (lat, lon) points, in screen coords."""
    p0, p1 = np.array(mv.pt(*a)), np.array(mv.pt(*b))
    mid = (p0 + p1) / 2 + np.array([-(p1 - p0)[1], (p1 - p0)[0]]) * bend
    ts = np.linspace(0, 1, n)[:, None]
    return (1 - ts) ** 2 * p0 + 2 * (1 - ts) * ts * mid + ts ** 2 * p1


def dashed_route(frame, pts, u, color=lk.ACCENT, thick=6, dash=22, gap=14):
    """Draw a route progressively as a dashed line with a moving head dot."""
    if u <= 0:
        return
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    upto = cum[-1] * lk.clamp(u)

    def at(d):
        i = min(np.searchsorted(cum, d) - 1, len(seg) - 1)
        i = max(i, 0)
        f = (d - cum[i]) / max(seg[i], 1e-6)
        return pts[i] + (pts[i + 1] - pts[i]) * f
    xs, ys = pts[:, 0], pts[:, 1]

    def dr(ov, ox, oy):
        d = 0.0
        while d < upto:
            e = min(d + dash, upto)
            a_, b_ = at(d), at(e)
            cv2.line(ov, (int(a_[0] - ox), int(a_[1] - oy)), (int(b_[0] - ox), int(b_[1] - oy)), color, thick,
                     cv2.LINE_AA)
            d += dash + gap
        h = at(upto)
        cv2.circle(ov, (int(h[0] - ox), int(h[1] - oy)), thick + 3, color, -1, cv2.LINE_AA)
    lk.overlay(frame, 1.0, dr, (xs.min() - 20, ys.min() - 20, xs.max() + 20, ys.max() + 20))
