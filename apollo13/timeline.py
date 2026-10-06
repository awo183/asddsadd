"""Scene layout for "The 28-Volt Switch", timed to the narration of each language."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(ROOT, "build")
FPS = 30

LANG = os.environ.get("FILM_LANG", "en")
ABUILD = os.path.join(BUILD, "apollo13" if LANG == "en" else f"apollo13_{LANG}")
ASSETS = os.path.join(BUILD, "apollo13", "assets")      # shared by both languages

# (scene, seconds before the voice, seconds after it). None = no voice.
PLAN = [
    ("hook", 0.6, 0.5),
    ("title", None, 3.2),
    ("switch", 0.35, 0.45),
    ("volts", 0.3, 0.5),
    ("drop", 0.3, 0.5),
    ("detank", 0.3, 0.45),
    ("weld", 0.3, 0.6),
    ("blast", 0.3, 0.6),
    ("lifeboat", 0.3, 2.8),
    ("verdict", 0.4, 1.2),
    ("end", None, 7.0),
]


def build():
    with open(os.path.join(ABUILD, "voice", "timings.json")) as f:
        timings = json.load(f)
    scenes, t = [], 0.0
    for key, pre, post in PLAN:
        if pre is None:
            dur, voice, sentences, words, vdur = post, None, [], [], 0.0
        else:
            v = timings[key]
            dur, voice, vdur = pre + v["duration"] + post, pre, v["duration"]
            sentences = [pre + s for s in v["sentences"]]
            words = [(w, pre + a, pre + b) for w, a, b in v["words"]]
        frames = round(dur * FPS)
        scenes.append({"key": key, "start": round(t, 4), "dur": frames / FPS, "frames": frames,
                       "voice": voice, "voice_end": (voice or 0) + vdur, "sentences": sentences,
                       "words": words})
        t += frames / FPS
    return scenes


if __name__ == "__main__":
    for s in build():
        print(f"{s['key']:9s} start {s['start']:7.2f}  dur {s['dur']:6.2f}  "
              f"sentences {[round(x, 2) for x in s['sentences']]}")
    print(f"total {sum(s['dur'] for s in build()):.2f}s")
