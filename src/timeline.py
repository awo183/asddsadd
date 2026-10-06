"""Lay the scenes out against the measured narration."""
import json
import os

from fx import BUILD, FPS

PRE, POST = 0.45, 0.75   # breathing room before / after the voice in a scene

# (scene key, seconds before the voice, seconds after it). None = no voice.
PLAN = [
    ("cold_open", 1.0, 0.9),
    ("title", None, 4.2),
    ("summer_1966", PRE, POST),
    ("pixels", PRE, POST),
    ("rules", PRE, POST),
    ("learning", PRE, POST),
    ("imagenet", PRE, POST),
    ("today", PRE, POST),
    ("watch", PRE, 1.6),
    ("end", None, 6.0),
]


def build():
    with open(os.path.join(BUILD, "voice", "timings.json")) as f:
        timings = json.load(f)
    scenes, t = [], 0.0
    for key, pre, post in PLAN:
        if pre is None:
            dur, voice, sentences = post, None, []
        else:
            v = timings[key]
            dur, voice = pre + v["duration"] + post, pre
            sentences = [pre + s for s in v["sentences"]]
        frames = round(dur * FPS)
        scenes.append({"key": key, "start": round(t, 4), "dur": frames / FPS, "frames": frames,
                       "voice": voice, "sentences": sentences})
        t += frames / FPS
    return scenes


if __name__ == "__main__":
    for s in build():
        print(f"{s['key']:12s} start {s['start']:7.2f}  dur {s['dur']:6.2f}  "
              f"sentences {[round(x, 2) for x in s['sentences']]}")
    print(f"total {sum(s['dur'] for s in build()):.2f}s")
