"""Frame compositor: shots (photos, footage, animations), crossfades, overlays.

Frames are BGR uint8 numpy arrays of shape (H, W, 3). Animations draw with
skia; footage is decoded by ffmpeg; the result is piped to an ffmpeg encoder
(NVIDIA NVENC when a GPU is available, libx264 otherwise).
"""
import functools
import io
import math
import os
import subprocess

import cv2
import numpy as np
import skia

W, H, FPS = 1920, 1080, 25
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.environ.get("DOC_ASSETS", os.path.join(HERE, "..", "build", "assets"))
CACHE = os.environ.get("DOC_CACHE", os.path.join(HERE, "..", "build", "cache"))


# ----------------------------------------------------------------------------- helpers
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp(x)
    return 4 * x * x * x if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def fade_env(t, dur, fin=0.6, fout=0.6):
    """Opacity envelope with fade-in and fade-out."""
    a = 1.0
    if fin > 0:
        a = min(a, clamp(t / fin))
    if fout > 0:
        a = min(a, clamp((dur - t) / fout))
    return smooth(a)


@functools.lru_cache(maxsize=None)
def typeface(name, wght=None):
    path = os.path.join(ASSETS, "fonts", name)
    tf = skia.Typeface.MakeFromFile(path)
    if tf is None:
        raise FileNotFoundError(path)
    if wght is not None:
        C = skia.FontArguments.VariationPosition.Coordinate
        pos = skia.FontArguments.VariationPosition(
            skia.FontArguments.VariationPosition.Coordinates([C(int.from_bytes(b"wght", "big"), float(wght))]))
        fa = skia.FontArguments()
        fa.setVariationDesignPosition(pos)
        tf = tf.makeClone(fa)
    return tf


def font(name, size, wght=None):
    f = skia.Font(typeface(name, wght), size)
    f.setSubpixel(True)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


SERIF = "CormorantGaramond.ttf"
SERIF_I = "CormorantGaramond-Italic.ttf"
BOOK = "EBGaramond.ttf"
BOOK_I = "EBGaramond-Italic.ttf"
SANS = "Inter.ttf"
HAND = "HomemadeApple-Regular.ttf"
TYPE = "SpecialElite-Regular.ttf"
NUM = "Spectral-Regular.ttf"      # lining figures for numbers
NUM_B = "Spectral-SemiBold.ttf"
NUM_I = "Spectral-Italic.ttf"

GOLD = (233, 196, 120)
CREAM = (244, 236, 220)
INK = (40, 30, 22)


def paint(rgb=(255, 255, 255), a=1.0, stroke=None, blur=None):
    p = skia.Paint(AntiAlias=True)
    p.setColor(skia.Color(int(rgb[0]), int(rgb[1]), int(rgb[2]), int(clamp(a) * 255)))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


def draw_text(c, text, x, y, f, rgb=(255, 255, 255), a=1.0, align="left", shadow=0, tracking=0.0):
    """Draw a single line. align: left|center|right. tracking: extra px between glyphs."""
    if tracking:
        widths = [f.measureText(ch) for ch in text]
        total = sum(widths) + tracking * (len(text) - 1)
    else:
        total = f.measureText(text)
    if align == "center":
        x -= total / 2
    elif align == "right":
        x -= total
    if shadow:
        sp = paint((0, 0, 0), a * 0.75, blur=shadow)
        _draw_run(c, text, x + 2, y + 3, f, sp, tracking)
    _draw_run(c, text, x, y, f, paint(rgb, a), tracking)
    return total


def _draw_run(c, text, x, y, f, p, tracking):
    if not tracking:
        c.drawString(text, x, y, f, p)
        return
    for ch in text:
        c.drawString(ch, x, y, f, p)
        x += f.measureText(ch) + tracking


def wrap(text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if f.measureText(t) > maxw and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def skia_image_from_bgra(arr):
    arr = np.ascontiguousarray(arr)
    return skia.Image.fromarray(arr, colorType=skia.ColorType.kBGRA_8888_ColorType,
                                alphaType=skia.AlphaType.kUnpremul_AlphaType)


@functools.lru_cache(maxsize=256)
def formula(tex, size=60, rgb=CREAM):
    """Render LaTeX-like math (matplotlib mathtext) to a skia.Image (cached on disk)."""
    import hashlib
    key = hashlib.md5(f"{tex}|{size}|{rgb}".encode()).hexdigest()
    os.makedirs(os.path.join(CACHE, "tex"), exist_ok=True)
    path = os.path.join(CACHE, "tex", key + ".png")
    if not os.path.exists(path):
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib.figure import Figure
        matplotlib.rcParams["mathtext.fontset"] = "cm"
        buf = io.BytesIO()
        fig = Figure(figsize=(0.01, 0.01))
        fig.text(0, 0, f"${tex}$", fontsize=size, color="#%02x%02x%02x" % tuple(rgb))
        fig.savefig(buf, dpi=144, format="png", transparent=True, bbox_inches="tight", pad_inches=0.02)
        arr = cv2.imdecode(np.frombuffer(buf.getvalue(), np.uint8), cv2.IMREAD_UNCHANGED)
        if arr.shape[2] == 3:
            arr = cv2.cvtColor(arr, cv2.COLOR_BGR2BGRA)
        # pad
        arr = cv2.copyMakeBorder(arr, 8, 8, 8, 8, cv2.BORDER_CONSTANT, value=(0, 0, 0, 0))
        cv2.imwrite(path, arr)
    arr = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    return skia_image_from_bgra(arr)


def draw_image(c, img, x, y, w=None, h=None, a=1.0, center=False):
    iw, ih = img.width(), img.height()
    if w is None and h is None:
        w, h = iw, ih
    elif w is None:
        w = iw * h / ih
    elif h is None:
        h = ih * w / iw
    if center:
        x, y = x - w / 2, y - h / 2
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(clamp(a))
    c.drawImageRect(img, skia.Rect.MakeXYWH(x, y, w, h),
                    skia.SamplingOptions(skia.CubicResampler.Mitchell()), p)
    return w, h


# ----------------------------------------------------------------------------- grading
def _mat(m):
    return np.array(m, np.float32)


# colour matrices operate on BGR
GRADES = {
    "none": None,
    # luminance-preserving warm monochrome (B, G, R gains on Y)
    "sepia": _mat([[0.114 * 0.80, 0.587 * 0.80, 0.299 * 0.80],
                   [0.114 * 0.96, 0.587 * 0.96, 0.299 * 0.96],
                   [0.114 * 1.08, 0.587 * 1.08, 0.299 * 1.08]]),
    "bw": _mat([[0.114, 0.587, 0.299]] * 3),
    "warm": _mat([[0.88, 0.02, 0.0], [0.0, 0.98, 0.04], [0.02, 0.05, 1.04]]),
    "cool": _mat([[1.04, 0.03, 0.0], [0.0, 0.98, 0.02], [0.0, 0.0, 0.92]]),
    "faded": _mat([[0.75, 0.15, 0.05], [0.08, 0.80, 0.10], [0.05, 0.15, 0.82]]),
}


def grade(img, kind, contrast=1.0, bright=0.0):
    m = GRADES.get(kind)
    if m is not None:
        img = cv2.transform(img, m)
    if contrast != 1.0 or bright:
        img = cv2.convertScaleAbs(img, alpha=contrast, beta=bright * 255 + 128 * (1 - contrast))
    return img


@functools.lru_cache(maxsize=1)
def vignette():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    v = 1.0 - 0.38 * np.clip(d - 0.45, 0, None) ** 1.6
    return np.clip(v, 0.45, 1.0)[..., None].astype(np.float32)


@functools.lru_cache(maxsize=1)
def grain_bank():
    rng = np.random.default_rng(7)
    small = rng.normal(0, 1, (8, H // 2, W // 2)).astype(np.float32)
    return [cv2.resize(s, (W, H), interpolation=cv2.INTER_LINEAR) for s in small]


def film_look(img, fi, amount=3.0, vig=True):
    f = img.astype(np.float32)
    if vig:
        f *= vignette()
    if amount:
        f += grain_bank()[fi % 8][..., None] * amount
    return np.clip(f, 0, 255).astype(np.uint8)


# ----------------------------------------------------------------------------- shots
class Shot:
    dur = 0.0
    look = "photo"  # photo | footage | anim (controls grain/vignette)
    caption = None   # lower-third text (name, place, date)

    def frame(self, t):
        raise NotImplementedError

    def close(self):
        pass


def load_image(path):
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(path)
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        a = img[..., 3:4].astype(np.float32) / 255
        img = (img[..., :3].astype(np.float32) * a + 18 * (1 - a)).astype(np.uint8)
    return img


class Photo(Shot):
    """Ken Burns move over a still. Portrait/odd-aspect images get a blurred backdrop."""

    def __init__(self, path, dur, z0=1.0, z1=1.12, p0=(0.5, 0.5), p1=(0.5, 0.5), tone="sepia",
                 caption=None, fit=None, contrast=1.05):
        self.path, self.dur, self.z0, self.z1, self.p0, self.p1 = path, dur, z0, z1, p0, p1
        self.tone, self.caption, self.fit, self.contrast = tone, caption, fit, contrast
        self._prep = None

    def _prepare(self):
        img = load_image(self.path)
        img = grade(img, self.tone, self.contrast)
        ih, iw = img.shape[:2]
        aspect = iw / ih
        fit = self.fit if self.fit is not None else aspect < 1.3
        zmax = max(self.z0, self.z1)
        if not fit:
            # cover: scale so the image covers the frame at zoom 1
            s = max(W / iw, H / ih) * zmax * 1.02
            img = cv2.resize(img, (int(iw * s), int(ih * s)), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
            self._prep = ("cover", img, None)
        else:
            s_bg = max(W / iw, H / ih) * 1.15
            bg = cv2.resize(img, (int(iw * s_bg) + 2, int(ih * s_bg) + 2), interpolation=cv2.INTER_AREA)
            bh, bw = bg.shape[:2]
            bg = bg[(bh - H) // 2:(bh - H) // 2 + H, (bw - W) // 2:(bw - W) // 2 + W]
            bg = cv2.GaussianBlur(bg, (0, 0), 28)
            bg = cv2.convertScaleAbs(bg, alpha=0.38)
            fh = H * 0.86
            s = fh / ih * zmax
            fg = cv2.resize(img, (max(2, int(iw * s)), max(2, int(ih * s))),
                            interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
            self._prep = ("fit", fg, bg)

    def frame(self, t):
        if self._prep is None:
            self._prepare()
        mode, img, bg = self._prep
        u = ease_in_out(t / max(self.dur, 1e-6))
        z = self.z0 + (self.z1 - self.z0) * u
        px = self.p0[0] + (self.p1[0] - self.p0[0]) * u
        py = self.p0[1] + (self.p1[1] - self.p0[1]) * u
        ih, iw = img.shape[:2]
        zmax = max(self.z0, self.z1)
        if mode == "cover":
            # the prepared image covers the frame at zoom zmax*1.02; output scale for zoom z:
            k = max(W / iw, H / ih) * z
            win_w, win_h = W / k, H / k
            cx = win_w / 2 + (iw - win_w) * px
            cy = win_h / 2 + (ih - win_h) * py
            M = np.array([[k, 0, W / 2 - k * cx], [0, k, H / 2 - k * cy]], np.float32)
            return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        # fit mode: foreground centered, slight zoom, small drift
        k = z / zmax
        cx = W / 2 + (px - 0.5) * 120
        cy = H / 2 + (py - 0.5) * 60
        M = np.array([[k, 0, cx - k * iw / 2], [0, k, cy - k * ih / 2]], np.float32)
        out = bg.copy()
        fg = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                            borderValue=(0, 0, 0))
        mask = cv2.warpAffine(np.full(img.shape[:2], 255, np.uint8), M, (W, H), flags=cv2.INTER_LINEAR)
        # soft shadow
        sh = cv2.GaussianBlur(mask, (0, 0), 18)
        sh = np.roll(np.roll(sh, 10, 0), 8, 1).astype(np.float32) / 255 * 0.55
        out = (out.astype(np.float32) * (1 - sh[..., None])).astype(np.uint8)
        m = mask.astype(np.float32)[..., None] / 255
        return (fg.astype(np.float32) * m + out.astype(np.float32) * (1 - m)).astype(np.uint8)


class Footage(Shot):
    """A video clip decoded by ffmpeg, scaled/cropped to fill the frame, looped if short."""
    look = "footage"

    def __init__(self, path, dur, start=0.0, speed=1.0, tone="sepia", caption=None, contrast=1.08,
                 clip_len=None, hflip=False):
        self.path, self.dur, self.start, self.speed = path, dur, start, speed
        self.tone, self.caption, self.contrast, self.clip_len, self.hflip = tone, caption, contrast, clip_len, hflip
        self.proc = None
        self.t_read = None
        self.last = None

    def _open(self, t):
        seek = self.start + t * self.speed
        if self.clip_len:
            seek = seek % max(self.clip_len - 0.2, 0.5)
        vf = []
        if self.speed != 1.0:
            vf.append(f"setpts=PTS/{self.speed}")
        vf += [f"fps={FPS}", f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=bicubic",
               f"crop={W}:{H}"]
        if self.hflip:
            vf.append("hflip")
        vf.append("format=bgr24")
        cmd = ["ffmpeg", "-v", "error", "-stream_loop", "-1", "-ss", f"{seek:.3f}", "-i", self.path,
               "-an", "-vf", ",".join(vf), "-f", "rawvideo", "-"]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.DEVNULL)
        self.t_read = t - 1.0 / FPS

    def frame(self, t):
        if self.proc is None:
            self._open(t)
        while self.t_read < t - 0.5 / FPS:
            buf = self.proc.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                break
            self.last = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
            self.t_read += 1.0 / FPS
        if self.last is None:
            return np.zeros((H, W, 3), np.uint8)
        return grade(self.last, self.tone, self.contrast)

    def close(self):
        if self.proc:
            self.proc.kill()
            self.proc.wait()
            self.proc = None


class Anim(Shot):
    look = "anim"

    def __init__(self, fn, dur, caption=None, grain=0.0, **kw):
        self.fn, self.dur, self.caption, self.kw, self.grain = fn, dur, caption, kw, grain
        self.surface = None
        self.state = {}

    def frame(self, t):
        if self.surface is None:
            self.surface = skia.Surface(W, H)
        c = self.surface.getCanvas()
        c.save()
        self.fn(c, t, self.dur, self.state, **self.kw)
        c.restore()
        arr = self.surface.makeImageSnapshot().toarray()
        return np.ascontiguousarray(arr[..., :3])


# ----------------------------------------------------------------------------- overlays
class Overlay:
    """Something drawn over the composited frame between t0 and t0+dur (global time)."""

    def __init__(self, t0, dur, fn, **kw):
        self.t0, self.dur, self.fn, self.kw = t0, dur, fn, kw


def blend_bgra(dst, layer_bgra_premul, opacity=1.0):
    """Composite a premultiplied BGRA layer (H, W, 4) over dst (H, W, 3)."""
    if opacity <= 0:
        return dst
    a = layer_bgra_premul[..., 3:4].astype(np.float32) * (opacity / 255.0)
    src = layer_bgra_premul[..., :3].astype(np.float32) * opacity
    out = src + dst.astype(np.float32) * (1 - a)
    return np.clip(out, 0, 255).astype(np.uint8)


# ----------------------------------------------------------------------------- encoder
@functools.lru_cache(maxsize=None)
def encoder_args(pref="auto", quality="high"):
    """Return (name, ffmpeg video codec args). Prefers NVIDIA NVENC when usable."""
    cq = {"high": 20, "web": 24}[quality]
    nvenc = ["-c:v", "h264_nvenc", "-preset", "p7", "-tune", "hq", "-rc", "vbr", "-cq", str(cq + 1),
             "-b:v", "0", "-maxrate", "10M", "-bufsize", "20M", "-profile:v", "high",
             "-spatial-aq", "1", "-temporal-aq", "1", "-bf", "3", "-pix_fmt", "yuv420p"]
    x264 = ["-c:v", "libx264", "-preset", "medium", "-crf", str(cq), "-maxrate", "8M", "-bufsize", "16M",
            "-profile:v", "high", "-tune", "film", "-pix_fmt", "yuv420p"]
    if pref in ("auto", "nvenc", "gpu"):
        test = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"color=black:s={W}x{H}:r={FPS}",
                               "-frames:v", "2", "-c:v", "h264_nvenc", "-f", "null", "-"],
                              capture_output=True)
        if test.returncode == 0:
            return "h264_nvenc (GPU)", nvenc
        if pref in ("nvenc", "gpu"):
            print("WARNING: NVENC requested but no usable NVIDIA GPU found; falling back to libx264 (CPU).")
    return "libx264 (CPU)", x264


def open_encoder(path, pref="auto", quality="high"):
    name, args = encoder_args(pref, quality)
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-"] + args + ["-r", str(FPS), "-video_track_timescale", "12800", path]
    return name, subprocess.Popen(cmd, stdin=subprocess.PIPE)
