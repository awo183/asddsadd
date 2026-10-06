"""Record the narration with ElevenLabs, one sentence at a time.

  FILM_LANG=en|cs  python apollo13/tts.py

Each sentence is a separate request (with the neighbouring sentences passed as
context so the delivery flows), trimmed of silence and measured. Writes
build/apollo13[_cs]/voice/<segment>.wav and timings.json:
  {segment: {"duration": s, "sentences": [start, ...], "words": [[word, t0, t1], ...]}}
Word times come from ElevenLabs' character alignment, so every animation can be
cued to the moment a word is actually spoken. Takes are cached by text+voice.
"""
import hashlib
import importlib.util
import json
import os
import sys

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    """Import a module from this folder by path (src/ has same-named modules)."""
    spec = importlib.util.spec_from_file_location(f"a13_{name}", os.path.join(HERE, f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


synth = load("eleven").synth
timeline = load("timeline")
LANG = timeline.LANG
SEGMENTS = load("narration" if LANG == "en" else f"narration_{LANG}").SEGMENTS
VOICE = os.environ.get("ELEVEN_VOICE", "c6SfcYrb2t09NHXiT80T")      # "Jarnathan", multilingual
SETTINGS = {"stability": 0.45, "similarity_boost": 0.8, "style": 0.2, "use_speaker_boost": True}
PAUSE = 0.30
OUT = os.path.join(timeline.ABUILD, "voice")
CACHE = os.path.join(os.path.dirname(HERE), "build", "apollo13_tts_cache")


def take(text, prev, nxt):
    key = hashlib.sha1(json.dumps([text, prev, nxt, VOICE, SETTINGS, LANG]).encode()).hexdigest()[:16]
    wav, js, mp3 = (os.path.join(CACHE, f"{key}.{e}") for e in ("wav", "json", "mp3"))
    if not os.path.exists(js):
        x, sr, words, raw = synth(text, VOICE, SETTINGS, prev=prev, nxt=nxt)
        sf.write(wav, x, sr)
        open(mp3, "wb").write(raw)
        json.dump({"text": text, "words": words}, open(js, "w"), ensure_ascii=False)
    x, sr = sf.read(wav)
    return x.astype(np.float32), sr, json.load(open(js))["words"]


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(CACHE, exist_ok=True)
    timings, chars = {}, 0
    for key, sentences in SEGMENTS:
        parts, starts, words, t, sr = [], [], [], 0.0, 44100
        for i, text in enumerate(sentences):
            prev = sentences[i - 1] if i else None
            nxt = sentences[i + 1] if i + 1 < len(sentences) else None
            x, sr, ws = take(text, prev, nxt)
            chars += len(text)
            idx = np.where(np.abs(x) > 0.012)[0]
            a = max(idx[0] - int(0.02 * sr), 0)
            b = min(idx[-1] + int(0.12 * sr), len(x))
            x = x[a:b]
            if i:
                parts.append(np.zeros(int(PAUSE * sr), np.float32))
                t += PAUSE
            starts.append(round(t, 3))
            off = t - a / sr
            words += [[w, round(off + s, 3), round(off + e, 3)] for w, s, e in ws]
            parts.append(x)
            t += len(x) / sr
        audio = np.concatenate(parts)
        sf.write(os.path.join(OUT, f"{key}.wav"), audio, sr)
        timings[key] = {"duration": round(len(audio) / sr, 3), "sentences": starts, "words": words}
        print(f"{key:9s} {timings[key]['duration']:6.2f}s  sentences at {starts}")
    total = sum(v["duration"] for v in timings.values())
    print(f"total speech {total:.2f}s ({chars} characters)")
    with open(os.path.join(OUT, "timings.json"), "w") as f:
        json.dump(timings, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
