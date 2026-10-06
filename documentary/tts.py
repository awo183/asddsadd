"""Synthesize the narration offline with Kokoro (ONNX).

Usage: python3 tts.py MODEL_DIR OUT_DIR
Writes OUT_DIR/<beat_id>.wav (24 kHz mono) and OUT_DIR/durations.json.
"""
import json
import os
import re
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

from script import BEATS

VOICES = {"N": "af_heart", "H": "bm_george", "R": "am_michael"}
LANG = {"N": "en-us", "H": "en-gb", "R": "en-us"}
SPEED = {"N": 0.92, "H": 0.92, "R": 0.90}

# Pronunciation overrides (IPA in Kokoro's phoneme set).
NAMES = {
    "Srinivasa": "ʃɹiːnɪvˈɑːsə",
    "Ramanujan's": "ɹɑːmˈɑːnʊdʒənz",
    "Ramanujan": "ɹɑːmˈɑːnʊdʒən",
    "Kumbakonam": "kʊmbəkˈoʊnəm",
    "Kaveri": "kˈɑːvɛɹi",
    "Komalatammal": "kˈoʊməlɐtˌɑːmɑːl",
    "Sarangapani": "sɑːɹəŋɡəpˈɑːni",
    "Sannidhi": "sˈʌnɪdi",
    "Janaki": "dʒˈɑːnəki",
    "Namagiri": "nˈɑːməɡɪɹi",
    "Pachaiyappa's": "pətʃˈaɪjəpəz",
    "Ramachandra": "ɹɑːmətʃˈʌndɹə",
    "Zwegers": "zwˈeɪɡɚz",
    "MacMahon": "məkmˈɑːn",
    "Edensor": "ˈɛnzɚ",
    "Cauchy's": "koʊʃˈiːz",
    "Bernoulli": "bɚnˈuːli",
    "kala": "kˈɑːlɑː",
    "pani": "pˈɑːni",
}

ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def two_digits(n):
    if n < 20:
        return ONES[n]
    t, o = divmod(n, 10)
    return TENS[t] + ("-" + ONES[o] if o else "")


def year_words(y):
    if 2000 <= y < 2010:
        return "two thousand and " + ONES[y - 2000]
    hi, lo = divmod(y, 100)
    if lo == 0:
        return two_digits(hi) + " hundred"
    if lo < 10:
        return two_digits(hi) + " oh-" + ONES[lo]
    return two_digits(hi) + " " + two_digits(lo)


def normalize(text):
    text = re.sub(r"\b(1[89]\d\d|20[0-2]\d)\b", lambda m: year_words(int(m.group(1))), text)
    text = text.replace("G. H. Hardy", "G H Hardy")
    return text


_NAME_RE = re.compile(r"\b(" + "|".join(sorted(map(re.escape, NAMES), key=len, reverse=True)) + r")\b")


def to_phonemes(tok, text, lang):
    """Phonemize text, substituting hand-written IPA for the names above."""
    parts = _NAME_RE.split(normalize(text))
    out = []
    for i, part in enumerate(parts):
        if i % 2:
            out.append(NAMES[part])
        elif part.strip():
            # keep leading punctuation (e.g. ", ") that follows a name
            lead = re.match(r"^[\s]*([,.;:!?]*)", part).group(1)
            body = part.strip().lstrip(",.;:!?").strip()
            if lead:
                out[-1] = out[-1] + lead if out else lead
            if body:
                out.append(tok.phonemize(body, lang))
    return " ".join(out)


def main():
    model_dir, out_dir = sys.argv[1], sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    k = Kokoro(os.path.join(model_dir, "kokoro-v1.0.onnx"), os.path.join(model_dir, "voices-v1.0.bin"))
    durations = {}
    for b in BEATS:
        if not b["voice"]:
            continue
        path = os.path.join(out_dir, b["id"] + ".wav")
        if os.path.exists(path):
            durations[b["id"]] = sf.info(path).duration
            continue
        v = b["voice"]
        # synthesize sentence groups separately: Kokoro degrades on very long inputs
        sentences = re.split(r"(?<=[.;?!])\s+", b["text"])
        chunks, cur = [], ""
        for s in sentences:
            if len(cur) + len(s) > 220 and cur:
                chunks.append(cur)
                cur = s
            else:
                cur = (cur + " " + s).strip()
        if cur:
            chunks.append(cur)
        audio = []
        for c in chunks:
            ph = to_phonemes(k.tokenizer, c, LANG[v])
            samples, sr = k.create(ph, voice=VOICES[v], speed=SPEED[v], lang=LANG[v], is_phonemes=True)
            audio.append(samples)
            audio.append(np.zeros(int(0.28 * sr), dtype=np.float32))
        audio = np.concatenate(audio[:-1])
        # trim leading/trailing near-silence
        nz = np.where(np.abs(audio) > 0.01)[0]
        audio = audio[max(0, nz[0] - 1200): nz[-1] + 2400]
        sf.write(path, audio, sr)
        durations[b["id"]] = len(audio) / sr
        print(f"{b['id']:8s} {durations[b['id']]:6.1f}s", flush=True)
    with open(os.path.join(out_dir, "durations.json"), "w") as f:
        json.dump(durations, f, indent=1)
    print("total speech", round(sum(durations.values()), 1), "s")


if __name__ == "__main__":
    main()
