"""Narration for both cuts, recorded with ElevenLabs one sentence at a time.

  FILM_LANG=en|cs  python titanic/tts.py

Uses the eleven_v4 model and one voice for both languages. The API key comes
from ELEVENLABS_API_KEY (sent as the xi-api-key header when it is set; in the
cloud sandbox a proxy adds it). Fails loudly instead of falling back to any
other engine.

Each sentence is requested with character timestamps, cached (re-runs cost
nothing) and trimmed of silence. The voice is used exactly as ElevenLabs
renders it (VOICE_TEMPO can stretch it, but that adds audible artefacts). Writes, per segment, build/titanic/<lang>/voice/
<segment>.wav plus timings.json:
  {segment: {"duration": s, "sentences": [start, ...],
             "words": [[word, start, end, sentence_index], ...]}}
with all times relative to the start of the segment's audio.
"""
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import timeline  # noqa: E402
from common import load_narration  # noqa: E402

LANG = timeline.LANG
SEGMENTS = load_narration(LANG)

MODEL = os.environ.get("ELEVEN_MODEL", "eleven_v4")
VOICE = os.environ.get("ELEVEN_VOICE", "6xPz2opT0y5qtoRh1U1Y")   # "Christian"
SETTINGS = {"stability": 0.5, "similarity_boost": 0.8, "style": 0.0, "use_speaker_boost": True,
            "speed": float(os.environ.get("ELEVEN_SPEED", "1.07"))}
SR = 44100
TEMPO = float(os.environ.get("VOICE_TEMPO", "1.0"))    # optional stretch; off: it colours the voice
PAUSE = 0.30            # between sentences inside a segment
OUT = os.path.join(timeline.CBUILD, "voice")
CACHE = os.path.join(timeline.BUILD, "titanic", "tts_cache")


def request(text, prev_text, next_text):
    body = {"text": text, "model_id": MODEL, "language_code": LANG, "voice_settings": SETTINGS}
    if prev_text:
        body["previous_text"] = prev_text
    if next_text:
        body["next_text"] = next_text
    headers = {"Content-Type": "application/json"}
    if os.environ.get("ELEVENLABS_API_KEY"):
        headers["xi-api-key"] = os.environ["ELEVENLABS_API_KEY"]
    url = (f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}/with-timestamps"
           "?output_format=mp3_44100_192")
    for attempt in range(4):
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read()[:300].decode("utf-8", "replace")
            if e.code in (401, 403):
                sys.exit(f"ElevenLabs refused the request ({e.code}): {msg}\n"
                         "Check ELEVENLABS_API_KEY. Not falling back to another voice engine.")
            if e.code == 400 and ("previous_text" in body or "next_text" in body):
                body.pop("previous_text", None)
                body.pop("next_text", None)
                continue
            print(f"  HTTP {e.code}: {msg} (retrying)", file=sys.stderr)
        except urllib.error.URLError as e:
            print(f"  network error: {e} (retrying)", file=sys.stderr)
        time.sleep(2 ** (attempt + 1))
    sys.exit("ElevenLabs is not reachable; stopping (no fallback).")


def synth(text, prev_text, next_text):
    """Audio (float32 mono at SR) and [[word, start, end], ...] for one sentence."""
    key = hashlib.sha1(json.dumps([MODEL, VOICE, SETTINGS, LANG, text, prev_text, next_text],
                                  sort_keys=True).encode()).hexdigest()[:16]
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, key + ".json")
    if not os.path.exists(path):
        d = request(text, prev_text, next_text)
        with open(path, "w") as f:
            json.dump({"text": text, "audio": d["audio_base64"], "alignment": d.get("alignment")}, f)
    with open(path) as f:
        d = json.load(f)
    mp3 = base64.b64decode(d["audio"])
    af = [] if TEMPO == 1 else ["-af", f"rubberband=tempo={TEMPO}:formant=preserved:pitchq=quality"]
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", "-", *af, "-f", "f32le", "-ac", "1",
                          "-ar", str(SR), "-"], input=mp3, capture_output=True, check=True).stdout
    x = np.frombuffer(pcm, np.float32).copy()
    al = d["alignment"]
    chars, t0s, t1s = (al["characters"], al["character_start_times_seconds"],
                       al["character_end_times_seconds"])
    words, cur, ws, we = [], "", None, None
    for ch, a, b in zip(chars, t0s, t1s):
        if ch.isspace():
            if cur:
                words.append([cur, ws, we])
            cur, ws = "", None
            continue
        if ws is None:
            ws = a
        cur += ch
        we = b
    if cur:
        words.append([cur, ws, we])
    return x, [[w, a / TEMPO, b / TEMPO] for w, a, b in words]


def trim(x, words):
    """Cut leading/trailing silence; shift word times to match."""
    idx = np.where(np.abs(x) > 0.006)[0]
    a = max(idx[0] - int(0.015 * SR), 0)
    b = min(idx[-1] + int(0.12 * SR), len(x))
    off = a / SR
    words = [[w, max(s - off, 0.0), max(e - off, 0.0)] for w, s, e in words]
    return x[a:b], words


def main():
    os.makedirs(OUT, exist_ok=True)
    flat = [s for _, ss in SEGMENTS for s in ss]
    timings, k = {}, 0
    for key, sentences in SEGMENTS:
        parts, starts, words, t = [], [], [], 0.0
        for i, text in enumerate(sentences):
            prev_text = flat[k - 1] if k else None
            next_text = flat[k + 1] if k + 1 < len(flat) else None
            k += 1
            x, w = trim(*synth(text, prev_text, next_text))
            if i:
                parts.append(np.zeros(int(PAUSE * SR), np.float32))
                t += PAUSE
            starts.append(round(t, 3))
            words += [[wd, round(t + s, 3), round(t + e, 3), i] for wd, s, e in w]
            parts.append(x)
            t += len(x) / SR
        audio = np.concatenate(parts)
        sf.write(os.path.join(OUT, f"{key}.wav"), audio, SR)
        timings[key] = {"duration": round(len(audio) / SR, 3), "sentences": starts, "words": words}
        print(f"{key:8s} {timings[key]['duration']:6.2f}s  sentences at {starts}")
    total = sum(v["duration"] for v in timings.values())
    nwords = sum(len(v["words"]) for v in timings.values())
    print(f"total speech {total:.2f}s, {nwords} words, {nwords / total * 60:.0f} wpm")
    with open(os.path.join(OUT, "timings.json"), "w") as f:
        json.dump(timings, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
