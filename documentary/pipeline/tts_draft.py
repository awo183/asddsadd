"""Temporary Czech voice (Google Translate TTS via gTTS) for timing and previews only.

The final film uses the ElevenLabs narration (import_narration.py or tts_elevenlabs.py).
"""
import json, os, subprocess, sys
import soundfile as sf
from gtts import gTTS

from common import BUILD

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    lang = os.environ.get("DOC_LANG", "cs")
    segs = json.load(open(os.path.join(HERE, f"narration_{lang}.json")))["segments"]
    out = os.path.join(BUILD, "voice")
    os.makedirs(out, exist_ok=True)
    durs = {}
    for s in segs:
        mp3 = os.path.join(out, s["id"] + ".draft.mp3")
        wav = os.path.join(out, s["id"] + ".wav")
        if not os.path.exists(mp3):
            gTTS(s.get("tts", s["text"]), lang=lang).save(mp3)
        # gTTS is slow and flat: speed it up a touch and trim edges
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-af",
                        "atempo=1.12,silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                        "silenceremove=start_periods=1:start_threshold=-45dB,areverse",
                        "-ac", "1", "-ar", "44100", wav], check=True)
        durs[s["id"]] = sf.info(wav).duration
        print(s["id"], round(durs[s["id"]], 1), flush=True)
    json.dump(durs, open(os.path.join(out, "durations.json"), "w"), indent=1)
    print(f"draft narration: {sum(durs.values()):.1f}s")


if __name__ == "__main__":
    main()
