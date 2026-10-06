"""Render the documentary picture from timeline.json.

Frames are composited in Python (stills with slow push/pan, archive film decoded by
ffmpeg, motion graphics from anims.py), then piped to an H.264 encoder. The timeline
is split into equal frame ranges rendered in parallel and joined losslessly.

Encoder: --encoder auto (default) uses NVIDIA NVENC when a working GPU is present,
otherwise libx264 on the CPU. Force one with --encoder nvenc / --encoder x264.
"""
import argparse, json, math, os, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image

from common import (W, H, FPS, BUILD, ASSETS, BG, ken_burns, contain_frame, load_photo, grade, finish,
                    lower_third, ramp, ease)
from anims import ANIMS


# ---------------------------------------------------------------- encoders
def nvenc_available():
    try:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                            "color=black:s=256x256:d=0.2", "-c:v", "h264_nvenc", "-f", "null", "-"],
                           capture_output=True, timeout=60)
        return r.returncode == 0
    except Exception:
        return False


def encoder_args(kind, quality):
    if kind == "nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p6", "-tune", "hq", "-rc", "vbr", "-cq", str(quality),
                "-b:v", "0", "-spatial-aq", "1", "-temporal-aq", "1", "-bf", "3", "-g", str(FPS * 4)]
    return ["-c:v", "libx264", "-preset", "medium", "-crf", str(quality), "-tune", "film",
            "-g", str(FPS * 4), "-threads", "2"]


# ---------------------------------------------------------------- frame sources
class PhotoSource:
    def __init__(self, shot):
        self.s = shot
        im = load_photo(shot["key"], shot.get("bw", False))
        g = grade(im, sat=shot.get("sat", 0.82), warm=shot.get("warm", 0.15), contrast=1.04)
        self.im = Image.fromarray(g)

    def frame(self, lt):
        s = self.s
        p = min(max(lt / max(s["dur"], 0.1), 0), 1.15)
        if s.get("fit") == "contain":
            z = 1 + (s.get("z1", 1.06) - 1) * ease(p)
            return contain_frame(self.im, z)
        return ken_burns(self.im, p, s.get("z0", 1.0), s.get("z1", 1.12), tuple(s.get("c0", (0.5, 0.5))),
                         tuple(s.get("c1", (0.5, 0.5))))


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:format=duration", "-of", "json", path],
                         capture_output=True, text=True).stdout
    d = json.loads(out)
    st = d["streams"][0]
    return st["width"], st["height"], float(d["format"]["duration"])


def find_asset(key):
    for ext in (".webm", ".ogv", ".mp4", ".mkv"):
        p = os.path.join(ASSETS, key + ext)
        if os.path.exists(p):
            return p
    raise FileNotFoundError(key)


class VideoSource:
    """Decodes an archive clip with ffmpeg, starting at the right local time."""

    def __init__(self, shot, local_start):
        self.s = shot
        path = find_asset(shot["key"])
        iw, ih, _ = probe(path)
        speed = shot.get("speed", 1.0)
        t_in = shot.get("t_in", 0.0) + local_start * speed
        need = shot["dur"] + 2.0 - local_start  # -t is an output option: seconds after retiming
        sat = shot.get("sat", 0.8)
        crop = shot.get("crop")  # optional "w:h:x:y" in source pixels (e.g. to drop burned-in titles)
        pre = f"crop={crop}," if crop else ""
        pts = f"setpts=PTS/{speed}," if speed != 1.0 else ""
        cover = shot.get("fit", "auto") == "cover" or (shot.get("fit", "auto") == "auto" and abs(iw / ih - W / H) < 0.12)
        if cover:
            vf = (f"{pre}{pts}fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase:flags=bicubic,"
                  f"crop={W}:{H},eq=saturation={sat}:contrast=1.04,format=rgb24")
        else:
            # pillarbox old 4:3 film over a blurred, darkened copy of itself
            vf = (f"{pre}{pts}fps={FPS},split[a][b];"
                  f"[a]scale={W // 4}:{H // 4}:force_original_aspect_ratio=increase,crop={W // 4}:{H // 4},"
                  f"boxblur=10:2,eq=brightness=-0.18:saturation=0.5,scale={W}:{H}[bg];"
                  f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=bicubic[fg];"
                  f"[bg][fg]overlay=(W-w)/2:(H-h)/2,eq=saturation={sat}:contrast=1.04,format=rgb24")
        cmd = ["ffmpeg", "-v", "error", "-ss", f"{t_in:.3f}", "-i", path, "-t", f"{need:.3f}",
               "-filter_complex" if not cover else "-vf", vf, "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=W * H * 3 * 4)
        self.last = None
        self.n = 0
        self.local_start = local_start

    def frame(self, lt):
        target = int(round((lt - self.local_start) * FPS))
        while self.n <= target:
            buf = self.p.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                break  # clip ran out: hold the last frame
            self.last = buf
            self.n += 1
        if self.last is None:
            return Image.new("RGB", (W, H), BG)
        return Image.frombuffer("RGB", (W, H), self.last, "raw", "RGB", 0, 1)

    def close(self):
        try:
            self.p.kill()
        except Exception:
            pass


class AnimSource:
    def __init__(self, shot):
        self.s = shot
        self.f = ANIMS[shot["anim"]]

    def frame(self, lt):
        return self.f(lt, self.s["dur"], **self.s.get("params", {}))


class SolidSource:
    def __init__(self, shot):
        self.im = Image.new("RGB", (W, H), tuple(shot.get("color", (0, 0, 0))))

    def frame(self, lt):
        return self.im


def make_source(shot, local_start):
    kind = shot["type"]
    if kind == "photo":
        return PhotoSource(shot)
    if kind == "video":
        return VideoSource(shot, local_start)
    if kind == "anim":
        return AnimSource(shot)
    return SolidSource(shot)


# ---------------------------------------------------------------- compositing
def shot_frame(shot, src, lt, n):
    im = src.frame(lt)
    if shot.get("cap"):
        label, sub = shot["cap"]
        a = ramp(lt, 0.6, 1.2) * (1 - ramp(lt, shot["dur"] - 0.9, shot["dur"] - 0.3))
        if a > 0:
            im = im.convert("RGBA")
            im.alpha_composite(lower_third(label, sub, a))
            im = im.convert("RGB")
    arr = np.asarray(im)
    real = shot["type"] in ("photo", "video")
    return finish(arr, n, grain=2.5 if real else 0.0, vig=real)


def render_range(args):
    timeline_path, f0, f1, out_path, enc, quality = args
    if os.path.exists(out_path):
        print(f"[{os.path.basename(out_path)}] already rendered, reusing", flush=True)
        return out_path
    final_path, out_path = out_path, out_path + ".tmp.mp4"
    tl = json.load(open(timeline_path))
    shots = tl["shots"]
    sources = {}
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", *encoder_args(enc, quality), "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_path]
    enc_p = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def get(i, lt):
        if i not in sources:
            sources[i] = make_source(shots[i], max(0.0, lt))
        return shot_frame(shots[i], sources[i], lt, n)

    t_start = time.time()
    idx = 0
    for n in range(f0, f1):
        T = n / FPS
        while idx + 1 < len(shots) and shots[idx + 1]["start"] <= T:
            idx += 1
        while idx > 0 and shots[idx]["start"] > T:
            idx -= 1
        cur = shots[idx]
        lt = T - cur["start"]
        trans = cur.get("trans", "dissolve")
        td = cur.get("td", 0.6)
        if idx > 0 and lt < td and trans in ("dissolve", "black"):
            prev = shots[idx - 1]
            plt = T - prev["start"]
            x = lt / td
            if trans == "dissolve":
                a = get(idx - 1, plt).astype(np.float32)
                b = get(idx, lt).astype(np.float32)
                k = ease(x)
                frame = (a * (1 - k) + b * k).astype(np.uint8)
            else:  # dip to black
                if x < 0.5:
                    frame = (get(idx - 1, plt).astype(np.float32) * (1 - ease(x * 2))).astype(np.uint8)
                else:
                    frame = (get(idx, lt).astype(np.float32) * ease(x * 2 - 1)).astype(np.uint8)
        elif trans == "white" and lt < td:
            b = get(idx, lt).astype(np.float32)
            k = ease(lt / td)
            frame = (255 * (1 - k) + b * k).astype(np.uint8)
        else:
            frame = get(idx, lt)
        # free decoders of shots that are finished
        for j in [j for j in sources if j < idx - 1]:
            if hasattr(sources[j], "close"):
                sources[j].close()
            del sources[j]
        enc_p.stdin.write(np.ascontiguousarray(frame).tobytes())
        if (n - f0) % 250 == 0:
            el = time.time() - t_start
            print(f"[{os.path.basename(out_path)}] {n - f0}/{f1 - f0} frames, {el:.0f}s", flush=True)
    enc_p.stdin.close()
    if enc_p.wait() != 0:
        raise RuntimeError(f"encoder failed for {out_path}")
    for s in sources.values():
        if hasattr(s, "close"):
            s.close()
    os.rename(out_path, final_path)
    return final_path


def check(timeline_path):
    """Smoke test: build every shot's source and render one frame from its middle."""
    tl = json.load(open(timeline_path))
    bad = 0
    for s in tl["shots"]:
        try:
            src = make_source(s, s["dur"] / 2)
            shot_frame(s, src, s["dur"] / 2, 0)
            if hasattr(src, "close"):
                src.close()
        except Exception as e:
            bad += 1
            print("FAIL", s.get("id"), s.get("key") or s.get("anim"), repr(e), flush=True)
    print(f"checked {len(tl['shots'])} shots, {bad} failures")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeline", default=os.path.join(BUILD, "timeline.json"))
    ap.add_argument("--out", default=os.path.join(BUILD, "picture.mp4"))
    ap.add_argument("--encoder", choices=["auto", "nvenc", "x264"], default="auto")
    ap.add_argument("--quality", type=int, default=None, help="CRF (x264) or CQ (nvenc)")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--start", type=float, default=0.0, help="preview: start time (s)")
    ap.add_argument("--end", type=float, default=None, help="preview: end time (s)")
    ap.add_argument("--chunks", type=int, default=None, help="number of resumable chunks (default 3 x jobs)")
    ap.add_argument("--check", action="store_true", help="render one frame of every shot and exit")
    args = ap.parse_args()
    if args.check:
        return check(args.timeline)

    enc = args.encoder
    if enc == "auto":
        enc = "nvenc" if nvenc_available() else "x264"
    elif enc == "nvenc" and not nvenc_available():
        sys.exit("NVENC requested but no working NVIDIA GPU/driver found (ffmpeg could not open h264_nvenc).")
    quality = args.quality if args.quality is not None else (24 if enc == "nvenc" else 22)
    print(f"encoder: {enc} (quality {quality})", flush=True)

    tl = json.load(open(args.timeline))
    total = int(round(tl["duration"] * FPS))
    f_start = int(args.start * FPS)
    f_end = min(total, int(args.end * FPS)) if args.end else total
    jobs = max(1, args.jobs)
    nchunks = args.chunks or jobs * 3
    step = math.ceil((f_end - f_start) / nchunks)
    import hashlib
    tag = hashlib.md5(open(args.timeline, "rb").read() + f"{enc}{quality}".encode()).hexdigest()[:8]
    parts = []
    for j in range(nchunks):
        a, b = f_start + j * step, min(f_end, f_start + (j + 1) * step)
        if a < b:
            parts.append((args.timeline, a, b, f"{args.out}.{tag}.{a}-{b}.mp4", enc, quality))
    t0 = time.time()
    with ProcessPoolExecutor(min(jobs, len(parts))) as ex:
        outs = list(ex.map(render_range, parts))
    lst = args.out + ".txt"
    with open(lst, "w") as f:
        for o in outs:
            f.write(f"file '{os.path.abspath(o)}'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    "-movflags", "+faststart", args.out], check=True)
    os.remove(lst)  # chunks are kept so a re-run only renders what changed
    print(f"picture done in {time.time() - t0:.0f}s -> {args.out}", flush=True)


if __name__ == "__main__":
    main()
