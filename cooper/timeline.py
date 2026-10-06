"""Scene layout for "The Calmest Man on the Plane", timed to the narration."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from fx import BUILD, FPS  # noqa: E402

LANG = os.environ.get("FILM_LANG", "en")
CBUILD = os.path.join(BUILD, "cooper" if LANG == "en" else f"cooper_{LANG}")

# (scene, seconds before the voice, seconds after it). None = no voice.
PLAN = [
    ("hook", 0.5, 0.35),
    ("title", None, 2.6),
    ("note", 0.3, 0.35),
    ("demands", 0.3, 0.35),
    ("orders", 0.3, 0.35),
    ("jump", 0.3, 0.45),
    ("profile", 0.3, 0.35),
    ("money", 0.3, 1.1),
    ("end", None, 4.0),
]


def build():
    with open(os.path.join(CBUILD, "voice", "timings.json")) as f:
        timings = json.load(f)
    scenes, t = [], 0.0
    for key, pre, post in PLAN:
        if pre is None:
            dur, voice, sentences, vdur = post, None, [], 0.0
        else:
            v = timings[key]
            dur, voice, vdur = pre + v["duration"] + post, pre, v["duration"]
            sentences = [pre + s for s in v["sentences"]]
        frames = round(dur * FPS)
        scenes.append({"key": key, "start": round(t, 4), "dur": frames / FPS, "frames": frames,
                       "voice": voice, "voice_end": (voice or 0) + vdur, "sentences": sentences})
        t += frames / FPS
    return scenes


if __name__ == "__main__":
    for s in build():
        print(f"{s['key']:9s} start {s['start']:7.2f}  dur {s['dur']:6.2f}  "
              f"sentences {[round(x, 2) for x in s['sentences']]}")
    print(f"total {sum(s['dur'] for s in build()):.2f}s")
