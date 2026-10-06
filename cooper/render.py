"""Render "The Calmest Man on the Plane" scene by scene, in parallel.

usage:
  render.py all [scene ...]          render scenes to build/cooper/scenes/*.mp4
  render.py preview SCENE t [t ...]  save still frames to build/cooper/preview/
"""
import json
import os
import subprocess
import sys
import time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, HERE)        # this film's timeline/narration win over src/
import timeline  # noqa: E402
from fx import FPS, H, W, finish  # noqa: E402

OUT = timeline.CBUILD


def render_scene(spec):
    import scenes
    start = time.time()
    scene = scenes.SCENES[spec["key"]](spec)
    out = os.path.join(OUT, "scenes", f"{spec['key']}.mp4")
    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "14",
         "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in range(spec["frames"]):
        ff.stdin.write(finish(scene.frame(i / FPS), i).tobytes())
    ff.stdin.close()
    ff.wait()
    print(f"  {spec['key']:9s} {spec['frames']} frames in {time.time() - start:.0f}s", flush=True)
    return spec["key"], [(spec["start"] + t, kind, gain) for t, kind, gain in scene.sfx]


def main():
    specs = timeline.build()
    if sys.argv[1] == "preview":
        import cv2
        import scenes
        key, times = sys.argv[2], [float(x) for x in sys.argv[3:]]
        spec = next(s for s in specs if s["key"] == key)
        scene = scenes.SCENES[key](spec)
        os.makedirs(os.path.join(OUT, "preview"), exist_ok=True)
        for i in range(spec["frames"]):
            t = i / FPS
            if t > max(times) + 0.5 / FPS:
                break
            f = scene.frame(t)
            if any(abs(t - x) < 0.5 / FPS for x in times):
                path = os.path.join(OUT, "preview", f"{key}_{t:05.2f}.jpg")
                cv2.imwrite(path, cv2.cvtColor(finish(f, i), cv2.COLOR_RGB2BGR),
                            [cv2.IMWRITE_JPEG_QUALITY, 85])
                print(path)
        return
    only = sys.argv[2:]
    os.makedirs(os.path.join(OUT, "scenes"), exist_ok=True)
    todo = sorted((s for s in specs if not only or s["key"] in only), key=lambda s: -s["frames"])
    with Pool(int(os.environ.get("JOBS", "4"))) as pool:
        results = dict(pool.map(render_scene, todo, chunksize=1))
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
