"""Render "The 28-Volt Switch" scene by scene, in parallel.

usage:
  FILM_LANG=en|cs render.py all [scene ...]       scenes -> build/apollo13[_cs]/scenes/*.mp4
  FILM_LANG=en|cs render.py preview SCENE t [t ...] still frames -> build/apollo13[_cs]/preview/
  FILM_LANG=en|cs render.py contact                 one still per cue-point of every scene

Each scene enters with its own transition (paper slide, push, zoom) over the
last frame of the scene before it, so scenes can still render in parallel.
"""
import json
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import look as lk  # noqa: E402
import timeline  # noqa: E402

OUT = timeline.ABUILD
FPS, W, H = lk.FPS, lk.W, lk.H
TR = 0.55                      # transition length, seconds


def make_scene(spec):
    import scenes
    return scenes.SCENES[spec["key"]](spec)


def last_frame(specs, k):
    if k == 0:
        return None
    prev = specs[k - 1]
    sc = make_scene(prev)
    return sc.frame((prev["frames"] - 1) / FPS)


def transition(kind, a, b, u):
    """Blend the previous scene's last frame `a` into the new frame `b` (u: 0..1)."""
    e = lk.ease_in_out(u)
    if kind == "slide":                     # a new sheet of paper slides over the old one
        out = a.copy()
        shift = int(e * W * 0.18)
        if shift:
            out[:, :W - shift] = a[:, shift:]
            out[:, W - shift:] = a[:, -1:]
        out = (out.astype(np.float32) * (1 - 0.25 * e)).astype(np.uint8)
        x = int((1 - e) * (W + 40))
        if x < W:
            sh = np.zeros((H, 60), np.float32)
            sh[:] = np.linspace(0, 0.35, 60)[None, :]
            x0 = max(x - 60, 0)
            seg = out[:, x0:x]
            if seg.shape[1]:
                seg[:] = (seg * (1 - sh[:, -seg.shape[1]:, None])).astype(np.uint8)
            out[:, x:] = b[:, :W - x]
        return out
    if kind == "push":                      # the camera pans to the next panel
        x = int(e * W)
        out = np.empty_like(a)
        out[:, :W - x] = a[:, x:]
        out[:, W - x:] = b[:, :x]
        return out
    if kind == "up":
        y = int((1 - e) * H)
        out = a.copy()
        out[y:] = b[:H - y]
        return out
    if kind == "zoom":                      # quick push-in through the old frame
        s = 1 + 0.35 * e
        m = cv2.getRotationMatrix2D((W / 2, H / 2), 0, s)
        za = cv2.warpAffine(a, m, (W, H), borderMode=cv2.BORDER_REFLECT)
        s2 = 0.92 + 0.08 * e
        m2 = cv2.getRotationMatrix2D((W / 2, H / 2), 0, s2)
        zb = cv2.warpAffine(b, m2, (W, H), borderMode=cv2.BORDER_REFLECT)
        return cv2.addWeighted(za, 1 - e, zb, e, 0)
    return b


def render_scene(job):
    specs, k = job
    spec = specs[k]
    start = time.time()
    sc = make_scene(spec)
    kind = sc.trans if k > 0 else "none"
    prev = last_frame(specs, k) if kind != "none" else None
    if prev is not None:
        sc.sfx.append((0.0, "paper" if kind in ("slide", "up") else "whoosh", 0.7))
    out = os.path.join(OUT, "scenes", f"{spec['key']}.mp4")
    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "15",
         "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in range(spec["frames"]):
        t = i / FPS
        f = sc.frame(t)
        if prev is not None and t < TR:
            f = transition(kind, prev, f, t / TR)
        ff.stdin.write(lk.finish(f, i).tobytes())
    ff.stdin.close()
    ff.wait()
    print(f"  {spec['key']:9s} {spec['frames']} frames in {time.time() - start:.0f}s", flush=True)
    return spec["key"], [(spec["start"] + t, kind_, gain) for t, kind_, gain in sc.sfx]


def preview(specs, key, times, tag=""):
    k = next(i for i, s in enumerate(specs) if s["key"] == key)
    spec = specs[k]
    sc = make_scene(spec)
    kind = sc.trans if k > 0 else "none"
    prev = last_frame(specs, k) if kind != "none" and min(times) < TR else None
    os.makedirs(os.path.join(OUT, "preview"), exist_ok=True)
    paths = []
    for i in range(spec["frames"]):
        t = i / FPS
        if t > max(times) + 0.5 / FPS:
            break
        want = any(abs(t - x) < 0.5 / FPS for x in times)
        if not want and not getattr(sc, "needs_sequential", False):
            # cheap skip: scenes are stateless except for one-shot sound cues
            continue
        f = sc.frame(t)
        if prev is not None and t < TR:
            f = transition(kind, prev, f, t / TR)
        if want:
            p = os.path.join(OUT, "preview", f"{tag}{key}_{t:05.2f}.jpg")
            cv2.imwrite(p, cv2.cvtColor(lk.finish(f, i), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88])
            paths.append(p)
    return paths


def main():
    specs = timeline.build()
    import scenes
    scenes.canvas_paper()                 # make the shared paper once
    if sys.argv[1] == "preview":
        for p in preview(specs, sys.argv[2], [float(x) for x in sys.argv[3:]]):
            print(p)
        return
    only = sys.argv[2:]
    os.makedirs(os.path.join(OUT, "scenes"), exist_ok=True)
    jobs = sorted(((specs, k) for k, s in enumerate(specs) if not only or s["key"] in only),
                  key=lambda j: -j[0][j[1]]["frames"])
    with Pool(int(os.environ.get("JOBS", "4"))) as pool:
        results = dict(pool.map(render_scene, jobs, chunksize=1))
    path = os.path.join(OUT, "sfx.json")
    cues = json.load(open(path)) if os.path.exists(path) else {}
    cues.update(results)
    with open(path, "w") as f:
        json.dump(cues, f)
    with open(os.path.join(OUT, "scenes", "list.txt"), "w") as f:
        for s in specs:
            f.write(f"file '{s['key']}.mp4'\n")


if __name__ == "__main__":
    main()
