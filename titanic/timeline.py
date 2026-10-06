"""Scene layout for "Twenty Boats", timed to each language's own narration."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(ROOT, "src"))
from fx import BUILD, FPS  # noqa: E402

LANG = os.environ.get("FILM_LANG", "en")
CBUILD = os.path.join(BUILD, "titanic", LANG)

# (scene, seconds before the voice, seconds after it). None = no voice.
PLAN = [
    ("hook", 0.6, 0.45),
    ("title", None, 2.6),
    ("rules", 0.35, 0.4),
    ("ferry", 0.35, 0.4),
    ("night", 0.35, 0.4),
    ("radio", 0.35, 0.45),
    ("boats", 0.35, 0.4),
    ("after", 0.35, 1.5),
    ("end", None, 5.0),
]


def build():
    with open(os.path.join(CBUILD, "voice", "timings.json")) as f:
        timings = json.load(f)
    scenes, t = [], 0.0
    for key, pre, post in PLAN:
        if pre is None:
            dur, voice, sentences, words, vdur = post, None, [], [], 0.0
        else:
            v = timings[key]
            dur, voice, vdur = pre + v["duration"] + post, pre, v["duration"]
            sentences = [pre + s for s in v["sentences"]]
            words = [[w, pre + a, pre + b, i] for w, a, b, i in v["words"]]
        frames = round(dur * FPS)
        scenes.append({"key": key, "start": round(t, 4), "dur": frames / FPS, "frames": frames,
                       "voice": voice, "voice_end": (voice or 0) + vdur, "sentences": sentences,
                       "words": words})
        t += frames / FPS
    return scenes


if __name__ == "__main__":
    for s in build():
        print(f"{s['key']:7s} start {s['start']:7.2f}  dur {s['dur']:6.2f}  "
              f"sentences {[round(x, 2) for x in s['sentences']]}")
    print(f"total {sum(s['dur'] for s in build()):.2f}s")
