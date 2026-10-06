"""Cut an ElevenLabs recording into script lines by speech recognition (no <break> pauses needed).

    python3 align_narration.py rec1.mp3 [rec2.mp3 ...]

Vosk (offline Czech model, VOSK_MODEL env var) transcribes the recording with word times;
the transcript is aligned to the script (narration_<lang>.json, "tts" text) with difflib, and
every line is cut in the silence just before its first word. Lines not covered by the
recording keep whatever is already in build/voice (e.g. the draft voice) and are reported.
"""
import difflib, json, os, re, subprocess, sys, unicodedata, wave
import numpy as np
import soundfile as sf

from common import BUILD

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100


def norm(w):
    w = unicodedata.normalize("NFKD", w.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in w if not unicodedata.combining(c)))


def load(path, sr):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def transcribe(x16, model_dir):
    from vosk import Model, KaldiRecognizer, SetLogLevel
    SetLogLevel(-1)
    rec = KaldiRecognizer(Model(model_dir), 16000)
    rec.SetWords(True)
    pcm = (np.clip(x16, -1, 1) * 32767).astype("<i2").tobytes()
    words = []
    step = 16000 * 2 * 4
    for i in range(0, len(pcm), step):
        if rec.AcceptWaveform(pcm[i:i + step]):
            words += json.loads(rec.Result()).get("result", [])
    words += json.loads(rec.FinalResult()).get("result", [])
    return words


def main():
    files = sys.argv[1:]
    lang = os.environ.get("DOC_LANG", "cs")
    model_dir = os.environ.get("VOSK_MODEL", os.path.join(BUILD, "asr", "vosk-model-small-cs-0.4-rhasspy"))
    segs = json.load(open(os.path.join(HERE, f"narration_{lang}.json")))["segments"]
    gap = 1.6
    xs = [load(f, SR) for f in files]
    x = np.concatenate(sum([[a, np.zeros(int(gap * SR), np.float32)] for a in xs], [])[:-1])
    x16 = load_resampled = np.concatenate(sum([[load(f, 16000), np.zeros(int(gap * 16000), np.float32)] for f in files], [])[:-1])
    words = transcribe(x16, model_dir)
    print(f"recognised {len(words)} words in {len(x) / SR:.1f}s")

    # script tokens with their segment index
    toks, owner = [], []
    for k, s in enumerate(segs):
        for w in s.get("tts", s["text"]).split():
            n = norm(w)
            if n:
                toks.append(n)
                owner.append(k)
    rec = [norm(w["word"]) for w in words]
    sm = difflib.SequenceMatcher(None, toks, rec, autojunk=False)
    t_of = {}  # script token index -> (start, end) seconds
    for a, b, size in sm.get_matching_blocks():
        for i in range(size):
            t_of[a + i] = (words[b + i]["start"], words[b + i]["end"])
    matched = np.zeros(len(segs))
    total = np.zeros(len(segs))
    for i, k in enumerate(owner):
        total[k] += 1
        matched[k] += i in t_of
    cover = matched / np.maximum(total, 1)
    covered = [k for k in range(len(segs)) if cover[k] >= 0.35]
    print("lines covered:", f"{segs[covered[0]]['id']} .. {segs[covered[-1]]['id']}" if covered else "none",
          f"({len(covered)} of {len(segs)})")
    low = [segs[k]["id"] for k in covered if cover[k] < 0.6]
    if low:
        print("weak recognition (check these cuts):", low)

    # extra words the script doesn't contain (e.g. a <break> tag read aloud)
    extras = []
    for tag, a1, a2, b1, b2 in sm.get_opcodes():
        if tag in ("insert", "replace") and b2 - b1 >= 3 and (tag == "insert" or (b2 - b1) > 2 * (a2 - a1) + 2):
            extras.append((words[b1]["start"], " ".join(w["word"] for w in words[b1:b2])))
    if extras:
        print("possible extra speech:", extras[:8])

    def seg_start(k):
        idx = [i for i, o in enumerate(owner) if o == k and i in t_of]
        return t_of[idx[0]][0] if idx else None

    def seg_end(k):
        idx = [i for i, o in enumerate(owner) if o == k and i in t_of]
        return t_of[idx[-1]][1] if idx else None

    out_dir = os.path.join(BUILD, "voice")
    os.makedirs(out_dir, exist_ok=True)
    dpath = os.path.join(out_dir, "durations.json")
    durs = json.load(open(dpath)) if os.path.exists(dpath) else {}
    env = np.abs(x)
    for j, k in enumerate(covered):
        start = seg_start(k)
        prev_end = seg_end(covered[j - 1]) if j > 0 else 0.0
        if start is None:
            continue
        # cut in the quietest 10 ms window between the previous line's last word and this line's first word
        lo, hi = int(max(prev_end, start - 1.5) * SR), int(start * SR)
        if hi - lo > 441:
            frames = env[lo:hi][: (hi - lo) // 441 * 441].reshape(-1, 441).mean(1)
            cut = lo + int(np.argmin(frames + np.linspace(0, frames.max() * 0.2, len(frames)))) * 441
        else:
            cut = hi
        end_k = seg_end(k)
        nxt = seg_start(covered[j + 1]) if j + 1 < len(covered) else None
        stop = int(((end_k + nxt) / 2 if nxt else min(len(x) / SR, end_k + 0.4)) * SR)
        a, b = max(0, cut - int(0.04 * SR)), stop
        seg = x[a:b]
        nz = np.where(np.abs(seg) > 10 ** (-45 / 20))[0]
        if len(nz):
            seg = seg[max(0, nz[0] - int(0.05 * SR)): nz[-1] + int(0.15 * SR)]
        sf.write(os.path.join(out_dir, segs[k]["id"] + ".wav"), seg, SR)
        durs[segs[k]["id"]] = len(seg) / SR
    json.dump(durs, open(dpath, "w"), indent=1)
    print(f"wrote {len(covered)} lines from the recording; total narration now {sum(durs.values()):.1f}s")
    missing = [s["id"] for k, s in enumerate(segs) if k not in covered]
    if missing:
        print("not in this recording (kept previous audio):", missing)


if __name__ == "__main__":
    main()
