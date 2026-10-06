"""Render every scene to its own video, in parallel, and collect sound cues.

usage:
  render.py all                      render all scenes to build/scenes/*.mp4
  render.py preview SCENE t [t ...]  save still frames to build/preview/
"""
import json
import os
import subprocess
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline  # noqa: E402
from fx import BUILD, FPS, H, W, finish  # noqa: E402


SCENES = {
    "cold_open": ("scenes_a", "ColdOpen"), "title": ("scenes_a", "Title"),
    "summer_1966": ("scenes_a", "Summer1966"), "pixels": ("scenes_a", "Pixels"),
    "rules": ("scenes_b", "Rules"), "learning": ("scenes_b", "Learning"),
    "imagenet": ("scenes_b", "ImageNet"), "today": ("scenes_c", "Today"),
    "watch": ("scenes_c", "Watch"), "end": ("scenes_c", "End"),
}


def scene_class(key):
    import importlib
    module, name = SCENES[key]
    return getattr(importlib.import_module(module), name)


def render_scene(spec):
    start = time.time()
    scene = scene_class(spec["key"])(spec)
    out = os.path.join(BUILD, "scenes", f"{spec['key']}.mp4")
    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "fast",
         "-crf", "12", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in range(spec["frames"]):
        f = scene.frame(i / FPS)
        ff.stdin.write(finish(f, i).tobytes())
    ff.stdin.close()
    ff.wait()
    print(f"  {spec['key']:12s} {spec['frames']} frames in {time.time() - start:.0f}s", flush=True)
    return spec["key"], [(spec["start"] + t, kind, gain) for t, kind, gain in scene.sfx]


def main():
    specs = timeline.build()
    if sys.argv[1] == "preview":
        import cv2
        key, times = sys.argv[2], [float(x) for x in sys.argv[3:]]
        spec = next(s for s in specs if s["key"] == key)
        scene = scene_class(key)(spec)
        os.makedirs(os.path.join(BUILD, "preview"), exist_ok=True)
        for i in range(spec["frames"]):
            t = i / FPS
            f = scene.frame(t)
            if any(abs(t - x) < 0.5 / FPS for x in times):
                path = os.path.join(BUILD, "preview", f"{key}_{t:05.2f}.jpg")
                cv2.imwrite(path, cv2.cvtColor(finish(f, i), cv2.COLOR_RGB2BGR),
                            [cv2.IMWRITE_JPEG_QUALITY, 85])
                print(path)
            if t > max(times):
                break
        return
    only = sys.argv[2:]
    os.makedirs(os.path.join(BUILD, "scenes"), exist_ok=True)
    todo = [s for s in specs if not only or s["key"] in only]
    todo.sort(key=lambda s: -s["frames"])
    with Pool(int(os.environ.get("JOBS", "4"))) as pool:
        results = dict(pool.map(render_scene, todo, chunksize=1))
    cues_path = os.path.join(BUILD, "sfx.json")
    cues = {}
    if os.path.exists(cues_path):
        with open(cues_path) as f:
            cues = json.load(f)
    cues.update(results)
    with open(cues_path, "w") as f:
        json.dump(cues, f)
    with open(os.path.join(BUILD, "scenes", "list.txt"), "w") as f:
        for s in specs:
            f.write(f"file '{s['key']}.mp4'\n")


if __name__ == "__main__":
    main()
