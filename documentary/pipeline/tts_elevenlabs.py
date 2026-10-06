"""Czech narration through the ElevenLabs API (needs ELEVENLABS_API_KEY in the environment).

    ELEVENLABS_API_KEY=...  python3 tts_elevenlabs.py
Optional: ELEVENLABS_VOICE_ID (default: a deep narrator voice), ELEVENLABS_MODEL (default
eleven_multilingual_v2, which speaks Czech). Each segment is generated with the neighbouring
text as context so intonation flows across cuts; results are cached by text+voice+model.
"""
import hashlib, json, os, subprocess, sys, time, urllib.error, urllib.request
import soundfile as sf

from common import BUILD

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128"


def synth(key, voice, model, text, prev_text, next_text):
    body = {"text": text, "model_id": model,
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.2, "use_speaker_boost": True}}
    if prev_text:
        body["previous_text"] = prev_text
    if next_text:
        body["next_text"] = next_text
    req = urllib.request.Request(API.format(voice=voice), data=json.dumps(body).encode(),
                                 headers={"xi-api-key": key, "Content-Type": "application/json",
                                          "Accept": "audio/mpeg"})
    for attempt in range(6):
        try:
            return urllib.request.urlopen(req, timeout=180).read()
        except urllib.error.HTTPError as e:
            msg = e.read()[:300].decode(errors="replace")
            if e.code in (429, 500, 502, 503):
                time.sleep(5 * (attempt + 1))
                continue
            sys.exit(f"ElevenLabs error {e.code}: {msg}")
    sys.exit("ElevenLabs: too many retries")


def main():
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        sys.exit("ELEVENLABS_API_KEY is not set")
    voice = os.environ.get("ELEVENLABS_VOICE_ID", "nPczCjzI2devNBz1zQrb")
    model = os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")
    lang = os.environ.get("DOC_LANG", "cs")
    segs = json.load(open(os.path.join(HERE, f"narration_{lang}.json")))["segments"]
    out = os.path.join(BUILD, "voice")
    cache = os.path.join(BUILD, "voice_cache")
    os.makedirs(out, exist_ok=True)
    os.makedirs(cache, exist_ok=True)
    durs = {}
    for i, s in enumerate(segs):
        text = s.get("tts", s["text"])
        prev_t = segs[i - 1].get("tts", segs[i - 1]["text"]) if i else ""
        next_t = segs[i + 1].get("tts", segs[i + 1]["text"]) if i + 1 < len(segs) else ""
        h = hashlib.sha1(f"{voice}|{model}|{prev_t}|{text}|{next_t}".encode()).hexdigest()[:16]
        mp3 = os.path.join(cache, f"{s['id']}_{h}.mp3")
        if not os.path.exists(mp3):
            open(mp3, "wb").write(synth(key, voice, model, text, prev_t, next_t))
            print("synth", s["id"], flush=True)
        wav = os.path.join(out, s["id"] + ".wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-ac", "1", "-ar", "44100", wav], check=True)
        durs[s["id"]] = sf.info(wav).duration
    json.dump(durs, open(os.path.join(out, "durations.json"), "w"), indent=1)
    print(f"{len(durs)} segments, {sum(durs.values()):.1f}s")


if __name__ == "__main__":
    main()
