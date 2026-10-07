"""Narration with ElevenLabs (eleven_v4, voice "Kuba") and character timestamps.

Each paragraph of the script is one request, sent with the neighbouring text so
the delivery flows. Writes build/stalin/voice/{NN}.mp3 + {NN}.json (alignment)
and voice/manifest.json: per paragraph the text, duration and word start times.
"""
import base64
import hashlib
import json
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vox as V  # noqa: E402

VOICE_ID = "pt8Kvp57SW3o4WuGqWZG"      # Kuba - Czech Social Media
MODEL = "eleven_v4"
SETTINGS = {"stability": 0.45, "similarity_boost": 0.8, "style": 0.25, "use_speaker_boost": True,
            "speed": 1.06}
OUT = os.path.join(V.BUILD, "voice")


def request(text, prev_text, next_text):
    body = {"text": text, "model_id": MODEL, "voice_settings": SETTINGS}
    if prev_text:
        body["previous_text"] = prev_text[-600:]
    if next_text:
        body["next_text"] = next_text[:600]
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/with-timestamps?output_format=mp3_44100_192",
        json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


def words_from_alignment(text, al):
    """Word start/end times from character alignment."""
    chars, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    words, cur, t0, t1 = [], "", None, None
    for c, a, b in zip(chars, st, en):
        if c.isspace():
            if cur:
                words.append({"w": cur, "t0": t0, "t1": t1})
                cur = ""
        else:
            if not cur:
                t0 = a
            cur += c
            t1 = b
    if cur:
        words.append({"w": cur, "t0": t0, "t1": t1})
    return words


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


def synth(paragraphs):
    """paragraphs: list of strings. Cached by text + settings."""
    os.makedirs(OUT, exist_ok=True)
    manifest = []
    for k, text in enumerate(paragraphs):
        key = hashlib.md5(json.dumps([text, MODEL, VOICE_ID, SETTINGS]).encode()).hexdigest()[:10]
        mp3 = os.path.join(OUT, f"{k:02d}_{key}.mp3")
        js = os.path.join(OUT, f"{k:02d}_{key}.json")
        if not os.path.exists(mp3):
            prev_t = paragraphs[k - 1] if k else None
            next_t = paragraphs[k + 1] if k + 1 < len(paragraphs) else None
            d = request(text, prev_t, next_t)
            open(mp3, "wb").write(base64.b64decode(d["audio_base64"]))
            json.dump(d["alignment"], open(js, "w"), ensure_ascii=False)
            print(f"  voice {k:02d}: {len(text)} chars", flush=True)
        al = json.load(open(js))
        manifest.append({"text": text, "mp3": mp3, "dur": duration(mp3),
                         "words": words_from_alignment(text, al)})
    json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), ensure_ascii=False, indent=1)
    return manifest


if __name__ == "__main__":
    import script
    paras = script.paragraphs()
    m = synth(paras)
    tot = sum(p["dur"] for p in m)
    nw = sum(len(p["words"]) for p in m)
    print(f"{len(m)} paragraphs, {nw} words, {tot:.1f}s of voice ({nw / tot * 60:.0f} wpm)")
