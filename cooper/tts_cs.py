"""Czech narration for the Cooper film, with a choice of speech engines.

  CS_TTS=google  GOOGLE_TTS_KEY=...   Google Cloud Text-to-Speech (best quality)
  CS_TTS=piper                        Piper, offline (needs huggingface.co once)
  CS_TTS=edge                         Microsoft Edge voices (speech.platform.bing.com)

Writes build/cooper_cs/voice/<segment>.wav and timings.json in the same format
as src/tts.py, so the rest of the pipeline is unchanged.
"""
import asyncio
import base64
import io
import json
import os
import subprocess
import sys
import urllib.request

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from narration_cs import SEGMENTS  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "build",
                                                          "cooper_cs", "voice")
ENGINE = os.environ.get("CS_TTS", "google")
RATE = float(os.environ.get("CS_RATE", "1.0"))
PAUSE = 0.30


def google(text):
    key = os.environ["GOOGLE_TTS_KEY"]
    voice = os.environ.get("CS_VOICE") or pick_google_voice(key)
    body = {"input": {"text": text},
            "voice": {"languageCode": "cs-CZ", "name": voice},
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 24000,
                            "speakingRate": RATE}}
    req = urllib.request.Request(
        f"https://texttospeech.googleapis.com/v1/text:synthesize?key={key}",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        audio = base64.b64decode(json.load(r)["audioContent"])
    x, sr = sf.read(io.BytesIO(audio))
    return x.astype(np.float32), sr


_GOOGLE_VOICE = None


def pick_google_voice(key):
    """Prefer a deep male Chirp 3 HD voice, then WaveNet, then Standard."""
    global _GOOGLE_VOICE
    if _GOOGLE_VOICE:
        return _GOOGLE_VOICE
    with urllib.request.urlopen(
            f"https://texttospeech.googleapis.com/v1/voices?languageCode=cs-CZ&key={key}") as r:
        voices = json.load(r).get("voices", [])
    names = [v["name"] for v in voices]
    male = [v["name"] for v in voices if v.get("ssmlGender") == "MALE"]
    for pref in ("Chirp3-HD-Charon", "Chirp3-HD-Orus", "Chirp3-HD-Fenrir", "Chirp3-HD"):
        hit = [n for n in (male or names) if pref in n]
        if hit:
            _GOOGLE_VOICE = hit[0]
            break
    else:
        for tier in ("Wavenet", "Neural2", "Standard"):
            hit = [n for n in (male or names) if tier in n] or [n for n in names if tier in n]
            if hit:
                _GOOGLE_VOICE = hit[0]
                break
    print("google voice:", _GOOGLE_VOICE, file=sys.stderr)
    return _GOOGLE_VOICE


_PIPER = None


def piper(text):
    global _PIPER
    if _PIPER is None:
        from piper import PiperVoice  # pip install piper-tts
        base = "https://huggingface.co/rhasspy/piper-voices/resolve/main/cs/cs_CZ/jirka/medium/"
        mdir = os.path.join(os.path.dirname(HERE), ".work", "models")
        os.makedirs(mdir, exist_ok=True)
        for f in ("cs_CZ-jirka-medium.onnx", "cs_CZ-jirka-medium.onnx.json"):
            p = os.path.join(mdir, f)
            if not os.path.exists(p):
                urllib.request.urlretrieve(base + f, p)
        _PIPER = PiperVoice.load(os.path.join(mdir, "cs_CZ-jirka-medium.onnx"))
    from piper import SynthesisConfig
    cfg = SynthesisConfig(length_scale=float(os.environ.get("CS_LENGTH", "1.0")) / RATE,
                          noise_scale=0.6, noise_w_scale=0.7)
    buf = io.BytesIO()
    import wave
    with wave.open(buf, "wb") as w:
        _PIPER.synthesize_wav(text, w, syn_config=cfg)
    buf.seek(0)
    x, sr = sf.read(buf)
    return x.astype(np.float32), sr


def edge(text):
    import edge_tts  # pip install edge-tts
    voice = os.environ.get("CS_VOICE", "cs-CZ-AntoninNeural")
    pct = int(round((RATE - 1) * 100))

    async def run():
        data = b""
        async for chunk in edge_tts.Communicate(text, voice, rate=f"{pct:+d}%").stream():
            if chunk["type"] == "audio":
                data += chunk["data"]
        return data
    mp3 = asyncio.run(run())
    wav = subprocess.run(["ffmpeg", "-v", "error", "-i", "-", "-f", "wav", "-ac", "1", "-ar",
                          "24000", "-"], input=mp3, capture_output=True, check=True).stdout
    x, sr = sf.read(io.BytesIO(wav))
    return x.astype(np.float32), sr


SYNTH = {"google": google, "piper": piper, "edge": edge}[ENGINE]


def main():
    os.makedirs(OUT, exist_ok=True)
    timings = {}
    for key, sentences in SEGMENTS:
        parts, starts, t, sr = [], [], 0.0, 24000
        for i, text in enumerate(sentences):
            x, sr = SYNTH(text)
            if x.ndim > 1:
                x = x.mean(axis=1)
            idx = np.where(np.abs(x) > 0.01)[0]
            x = x[max(idx[0] - int(0.01 * sr), 0): idx[-1] + int(0.1 * sr)]
            if i:
                parts.append(np.zeros(int(PAUSE * sr), np.float32))
                t += PAUSE
            starts.append(round(t, 3))
            parts.append(x)
            t += len(x) / sr
        audio = np.concatenate(parts)
        sf.write(os.path.join(OUT, f"{key}.wav"), audio, sr)
        timings[key] = {"duration": round(len(audio) / sr, 3), "sentences": starts}
        print(f"{key:10s} {timings[key]['duration']:6.2f}s  sentences at {starts}")
    print(f"total speech {sum(v['duration'] for v in timings.values()):.2f}s")
    with open(os.path.join(OUT, "timings.json"), "w") as f:
        json.dump(timings, f, indent=2)


if __name__ == "__main__":
    main()
