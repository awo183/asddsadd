"""Render the film in parallel chunks of consecutive shots.

usage:
  render.py all                    render every chunk, then join them (build/stalin/video.mp4)
  render.py preview ID t [t ...]   save stills of one shot (local times) to build/stalin/preview/
  render.py sheet [every]          contact sheet of the whole film, one still per shot
"""
import json
import os
import subprocess
import sys
import time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cv2  # noqa: E402
import numpy as np  # noqa: E402

import vox as V  # noqa: E402

OUT = V.BUILD


def load_shots():
    import plan
    return plan.timeline()


def build(spec):
    import maps  # noqa: F401  (registers map shot types)
    import extras  # noqa: F401
    import diagrams  # noqa: F401
    import shots
    return shots.make(spec)


def render_chunk(job):
    k, specs = job
    start = time.time()
    path = os.path.join(OUT, "chunks", f"chunk_{k:02d}.mp4")
    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{V.W}x{V.H}",
         "-r", str(V.FPS), "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "15",
         "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    events = []
    n = 0
    for spec in specs:
        shot = build(spec)
        f0 = spec["f0"]
        for j in range(spec["frames"]):
            t = j / V.FPS
            ff.stdin.write(np.ascontiguousarray(shot.frame(t, f0 + j)).tobytes())
        n += spec["frames"]
        events += [(spec["start"] + t, name, gain) for t, name, gain in shot.sfx if t < spec["dur"]]
    ff.stdin.close()
    ff.wait()
    print(f"  chunk {k:02d}: {len(specs)} shots, {n} frames in {time.time() - start:.0f}s", flush=True)
    return k, events


def chunks(specs, jobs):
    # small chunks, longest first, so the pool stays busy
    out, cur, size = [], [], 0
    target = max(sum(s["frames"] for s in specs) // (jobs * 4), 120)
    for s in specs:
        cur.append(s)
        size += s["frames"]
        if size >= target:
            out.append(cur)
            cur, size = [], 0
    if cur:
        out.append(cur)
    return list(enumerate(out))


def main():
    specs = load_shots()
    cmd = sys.argv[1]
    if cmd == "preview":
        sid, times = sys.argv[2], [float(x) for x in sys.argv[3:]]
        spec = next(s for s in specs if s["id"] == sid)
        shot = build(spec)
        os.makedirs(os.path.join(OUT, "preview"), exist_ok=True)
        for t in times:
            f = shot.frame(t, spec["f0"] + int(t * V.FPS))
            p = os.path.join(OUT, "preview", f"{sid}_{t:05.2f}.jpg")
            cv2.imwrite(p, cv2.cvtColor(f, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
            print(p)
        return
    if cmd == "sheet":
        only = sys.argv[2:] or None
        thumbs = []
        for s in specs:
            if only and s["id"] not in only:
                continue
            shot = build(s)
            t = min(s["dur"] * 0.7, s["dur"] - 0.05)
            f = shot.frame(t, s["f0"])
            th = cv2.resize(f, (480, 270))
            cv2.putText(th, s["id"], (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 230, 0), 2)
            thumbs.append(th)
        cols = 4
        while len(thumbs) % cols:
            thumbs.append(np.zeros_like(thumbs[0]))
        rows = [np.hstack(thumbs[i:i + cols]) for i in range(0, len(thumbs), cols)]
        os.makedirs(os.path.join(OUT, "preview"), exist_ok=True)
        for i in range(0, len(rows), 6):
            p = os.path.join(OUT, "preview", f"sheet_{i // 6:02d}.jpg")
            cv2.imwrite(p, cv2.cvtColor(np.vstack(rows[i:i + 6]), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 80])
            print(p)
        return
    os.makedirs(os.path.join(OUT, "chunks"), exist_ok=True)
    jobs = chunks(specs, int(os.environ.get("JOBS", "4")))
    order = sorted(jobs, key=lambda j: -sum(s["frames"] for s in j[1]))
    with Pool(int(os.environ.get("JOBS", "4"))) as pool:
        results = dict(pool.map(render_chunk, order, chunksize=1))
    events = [e for k in sorted(results) for e in results[k]]
    json.dump(events, open(os.path.join(OUT, "sfx_events.json"), "w"))
    with open(os.path.join(OUT, "chunks", "list.txt"), "w") as f:
        for k, _ in jobs:
            f.write(f"file 'chunk_{k:02d}.mp4'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i",
                    os.path.join(OUT, "chunks", "list.txt"), "-c", "copy", os.path.join(OUT, "video.mp4")],
                   check=True)
    print("wrote", os.path.join(OUT, "video.mp4"))


if __name__ == "__main__":
    main()
