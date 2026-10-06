"""Generate the English voice-over with Kokoro (open-weight neural TTS, runs locally).

Czech / German / Russian names are passed as hand-written IPA so the engine
does not anglicise them ("Jáchymov" would otherwise come out as "Jack-ee-mov").
"""
import json, os, re, sys
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.environ.get("KOKORO_DIR", os.path.join(HERE, "..", "build", "tts"))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "build", "voice")

# Longest keys first so multi-word phrases win over their parts.
IPA = {
    "muž určený k likvidaci": "mˈʊʒ ˈʊɹtʃɛniː k lˈɪkvɪdˌɑːtsi",
    "Sankt Joachimsthal": "zˈɑŋkt jˈoʊɑːxɪmstˌɑːl",
    "Joachimsthalers": "jˈoʊɑːxɪmstˌɑːləɹz",
    "Joachimsthal": "jˈoʊɑːxɪmstˌɑːl",
    "Horní Slavkov": "hˈɔːɹniː slˈɑːfkɔf",
    "Jáchymov": "jˈɑːxɪmɔf",
    "Příbram": "pʒˈiːbɹɑːm",
    "Svornost": "svˈɔːɹnɔst",
    "Vojna": "vˈɔɪnɑ",
    "Ostrov": "ˈɔstɹɔf",
    "mukl": "mˈʊkəl",
    "Pech": "pˈɛx",
    "Lavrentiy": "lɑvɹˈɛntiː",
    "Kurchatov": "kʊɹtʃˈɑːtəf",
    "Gottwald": "ɡˈɔtvɑlt",
    "Mauthausen": "mˈaʊthaʊzən",
    "RDS-1": "ˌɑːɹdˌiːˈɛs wˈʌn",
    "Joe-1": "dʒˈoʊ wˈʌn",
}
_pattern = re.compile("|".join(re.escape(k) for k in sorted(IPA, key=len, reverse=True)))


def to_phonemes(tok, text, lang):
    out, pos = [], 0
    for m in _pattern.finditer(text):
        chunk = text[pos:m.start()]
        if chunk.strip():
            out.append(tok.phonemize(chunk, lang))
        out.append(IPA[m.group(0)])
        pos = m.end()
    tail = text[pos:]
    if tail.strip():
        out.append(tok.phonemize(tail, lang))
    ph = " ".join(p.strip() for p in out if p.strip())
    # phonemizing fragments separately drops the punctuation that touches an override
    ph = re.sub(r"\s+([,.;:?!])", r"\1", ph)
    return ph


def main():
    cfg = json.load(open(os.path.join(HERE, "narration.json")))
    os.makedirs(OUT, exist_ok=True)
    k = Kokoro(os.path.join(MODEL_DIR, "kokoro-v1.0.onnx"), os.path.join(MODEL_DIR, "voices-v1.0.bin"))
    voice, speed, lang = cfg["voice"], cfg["speed"], "en-us"
    durations = {}
    only = set(sys.argv[2:])
    for seg in cfg["segments"]:
        path = os.path.join(OUT, seg["id"] + ".wav")
        if only and seg["id"] not in only and os.path.exists(path):
            durations[seg["id"]] = sf.info(path).duration
            continue
        ph = to_phonemes(k.tokenizer, seg["text"], lang)
        audio, sr = k.create(ph, voice=voice, speed=speed, lang=lang, is_phonemes=True)
        sf.write(path, audio.astype(np.float32), sr)
        durations[seg["id"]] = len(audio) / sr
        print(f"{seg['id']}: {durations[seg['id']]:.2f}s  {ph[:90]}")
    json.dump(durations, open(os.path.join(OUT, "durations.json"), "w"), indent=1)
    print("total narration", round(sum(durations.values()), 1), "s")


if __name__ == "__main__":
    main()
