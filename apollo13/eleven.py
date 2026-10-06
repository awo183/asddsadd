"""Thin ElevenLabs client: text -> (mono float32 audio, sample rate, word timings).

The API key never passes through this code: it is either attached by the
environment's outbound proxy (header xi-api-key) or read from
ELEVENLABS_API_KEY and sent as that header. It is never printed or logged.
"""
import base64
import io
import json
import os
import subprocess
import time
import urllib.error
import urllib.request

import numpy as np
import soundfile as sf

API = "https://api.elevenlabs.io/v1"
MODEL = os.environ.get("ELEVEN_MODEL", "eleven_multilingual_v2")


def _headers():
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    key = os.environ.get("ELEVENLABS_API_KEY")
    if key:
        h["xi-api-key"] = key
    return h


def synth(text, voice_id, settings=None, prev=None, nxt=None, language=None, tries=4):
    """Return (audio, sr, words) where words = [(word, start_s, end_s), ...]."""
    body = {"text": text, "model_id": MODEL,
            "voice_settings": settings or {"stability": 0.5, "similarity_boost": 0.8,
                                           "style": 0.15, "use_speaker_boost": True}}
    if prev:
        body["previous_text"] = prev
    if nxt:
        body["next_text"] = nxt
    if language:
        body["language_code"] = language
    url = f"{API}/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_192"
    for k in range(tries):
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=_headers())
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            break
        except urllib.error.HTTPError as e:
            msg = e.read()[:300].decode("utf8", "ignore")
            if e.code in (429, 500, 502, 503) and k < tries - 1:
                time.sleep(2 ** (k + 1))
                continue
            raise RuntimeError(f"ElevenLabs HTTP {e.code}: {msg}") from None
    mp3 = base64.b64decode(d["audio_base64"])
    wav = subprocess.run(["ffmpeg", "-v", "error", "-i", "-", "-f", "wav", "-ac", "1", "-ar", "44100", "-"],
                         input=mp3, capture_output=True, check=True).stdout
    x, sr = sf.read(io.BytesIO(wav))
    al = d.get("alignment") or d.get("normalized_alignment")
    return x.astype(np.float32), sr, words_from_alignment(al), mp3


def words_from_alignment(al):
    chars, t0s, t1s = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    words, cur, s, e = [], "", None, None
    for c, a, b in zip(chars, t0s, t1s):
        if c.isspace():
            if cur:
                words.append((cur, s, e))
            cur, s = "", None
            continue
        if s is None:
            s = a
        cur += c
        e = b
    if cur:
        words.append((cur, s, e))
    return words
