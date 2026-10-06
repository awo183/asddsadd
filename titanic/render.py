"""Render "Twenty Boats" scene by scene, in parallel.

usage (FILM_LANG=en|cs):
  render.py all [scene ...]           render scenes to build/titanic/<lang>/scenes/*.mp4
  render.py preview SCENE t [t ...]   save stills to build/titanic/<lang>/preview/
  render.py board                     one still per sentence of every scene, for review
"""
import json
import os
import subprocess
import sys
import time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import timeline  # noqa: E402
sys.path.insert(0, HERE)        # timeline appends src/; keep this film's modules first
import look  # noqa: E402

OUT = timeline.CBUILD
FPS, W, H = look.FPS, look.W, look.H


def make(spec, specs):
    import scenes
    scene = scenes.SCENES[spec["key"]](spec)
    k = [s["key"] for s in specs].index(spec["key"])
    if k > 0 and scene.entry:
        prev_spec = specs[k - 1]
        prev = scenes.SCENES[prev_spec["key"]](prev_spec)
        scene.prev_last = prev.frame(prev_spec["frames"] / FPS - 1 / FPS)
    return scene


def render_scene(args):
    spec, specs = args
    start = time.time()
    scene = make(spec, specs)
    out = os.path.join(OUT, "scenes", f"{spec['key']}.mp4")
    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "15",
         "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in range(spec["frames"]):
        ff.stdin.write(look.finish(scene.frame(i / FPS), i).tobytes())
    ff.stdin.close()
    ff.wait()
    print(f"  {spec['key']:7s} {spec['frames']} frames in {time.time() - start:.0f}s", flush=True)
    return spec["key"], [(spec["start"] + t, kind, gain) for t, kind, gain in scene.sfx]


def still(scene, spec, t, path):
    import cv2
    i = int(round(t * FPS))
    f = look.finish(scene.frame(i / FPS), i)
    cv2.imwrite(path, cv2.cvtColor(f, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
    return path


def main():
    specs = timeline.build()
    mode = sys.argv[1]
    if mode == "preview":
        key, times = sys.argv[2], [float(x) for x in sys.argv[3:]]
        spec = next(s for s in specs if s["key"] == key)
        scene = make(spec, specs)
        os.makedirs(os.path.join(OUT, "preview"), exist_ok=True)
        for t in times:
            print(still(scene, spec, t, os.path.join(OUT, "preview", f"{key}_{t:05.2f}.jpg")))
        return
    if mode == "board":
        os.makedirs(os.path.join(OUT, "board"), exist_ok=True)
        only = sys.argv[2:]
        for spec in specs:
            if only and spec["key"] not in only:
                continue
            scene = make(spec, specs)
            # one still a little after each sentence starts and near each sentence's end
            ts = sorted({min(spec["dur"] - 0.05, x) for s0 in (spec["sentences"] or [0.0])
                         for x in (s0 + 1.2,)} | {spec["dur"] - 0.1})
            for t in ts:
                print(still(scene, spec, t, os.path.join(OUT, "board", f"{spec['key']}_{t:05.2f}.jpg")))
        return
    only = sys.argv[2:]
    os.makedirs(os.path.join(OUT, "scenes"), exist_ok=True)
    todo = sorted((s for s in specs if not only or s["key"] in only), key=lambda s: -s["frames"])
    with Pool(int(os.environ.get("JOBS", "4"))) as pool:
        results = dict(pool.map(render_scene, [(s, specs) for s in todo], chunksize=1))
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
