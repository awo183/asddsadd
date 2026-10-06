"""Generate the narration with Kokoro (local, offline neural TTS).

Writes one WAV per segment plus timings.json with each segment's length and
the start time of every sentence inside it.
"""
import json
import os
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

sys.path.insert(0, os.path.dirname(__file__))
if os.environ.get("NARRATION"):          # another film's script, e.g. cooper/narration.py
    import importlib.util
    _spec = importlib.util.spec_from_file_location("narration", os.environ["NARRATION"])
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    SEGMENTS = _mod.SEGMENTS
else:
    from narration import SEGMENTS  # noqa: E402

MODELS, OUT = sys.argv[1], sys.argv[2]
VOICE = os.environ.get("VOICE", "af_heart")
SPEED = float(os.environ.get("SPEED", "0.95"))
PAUSE = 0.30          # silence between sentences
SHORT_PAUSE = 0.12    # between one-word beats ("Person. Car. Bicycle.")

os.makedirs(OUT, exist_ok=True)
kokoro = Kokoro(os.path.join(MODELS, "kokoro-v1.0.onnx"),
                os.path.join(MODELS, "voices-v1.0.bin"))
if ":" in VOICE:                          # blend, e.g. "am_michael:0.7,am_onyx:0.3"
    VOICE = sum(kokoro.get_voice_style(name) * float(w)
                for name, w in (part.split(":") for part in VOICE.split(",")))
timings = {}
for key, sentences in SEGMENTS:
    parts, starts, t, sr = [], [], 0.0, 24000
    for i, text in enumerate(sentences):
        samples, sr = kokoro.create(text, voice=VOICE, speed=SPEED, lang="en-us")
        # trim leading/trailing near-silence so pauses are under our control
        idx = np.where(np.abs(samples) > 0.01)[0]
        samples = samples[max(idx[0] - 240, 0): idx[-1] + 2400]
        if i:
            gap = SHORT_PAUSE if len(text.split()) == 1 else PAUSE
            parts.append(np.zeros(int(gap * sr), np.float32))
            t += gap
        starts.append(round(t, 3))
        parts.append(samples.astype(np.float32))
        t += len(samples) / sr
    audio = np.concatenate(parts)
    sf.write(os.path.join(OUT, f"{key}.wav"), audio, sr)
    timings[key] = {"duration": round(len(audio) / sr, 3), "sentences": starts}
    print(f"{key:12s} {timings[key]['duration']:6.2f}s  sentences at {starts}")
print(f"total speech {sum(v['duration'] for v in timings.values()):.2f}s")
with open(os.path.join(OUT, "timings.json"), "w") as f:
    json.dump(timings, f, indent=2)
