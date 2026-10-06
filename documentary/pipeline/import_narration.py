"""Import a narration recorded in ElevenLabs (or anywhere) and cut it into script segments.

Usage:
    python3 import_narration.py narace_1.mp3 narace_2.mp3  # one or more files, in script order
    python3 import_narration.py folder_with_files/        # one file per segment, named <id>.mp3/.wav

For a single file, the script (NARRACE_ElevenLabs.txt) puts a <break time="1.5s" /> between
segments. Those are the longest pauses in the recording, so the N-1 longest silences are
taken as the cut points. The result is checked against the expected segment count and the
relative segment lengths, and written to build/voice/<id>.wav + durations.json.
"""
import json, os, subprocess, sys
import numpy as np
import soundfile as sf

from common import BUILD

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def silences(x, min_len=0.45, thresh_db=-42):
    hop = int(SR * 0.01)
    frames = len(x) // hop
    rms = np.sqrt((x[: frames * hop].reshape(frames, hop) ** 2).mean(1) + 1e-12)
    db = 20 * np.log10(rms)
    quiet = db < thresh_db
    out, start = [], None
    for i, q in enumerate(quiet):
        if q and start is None:
            start = i
        elif not q and start is not None:
            if (i - start) * 0.01 >= min_len:
                out.append((start * 0.01, i * 0.01))
            start = None
    return out


def main():
    srcs = sys.argv[1:]
    src = srcs[0]
    lang = os.environ.get("DOC_LANG", "cs")
    segs = json.load(open(os.path.join(HERE, f"narration_{lang}.json")))["segments"]
    out_dir = os.path.join(BUILD, "voice")
    os.makedirs(out_dir, exist_ok=True)
    durs = {}
    if os.path.isdir(src):
        for s in segs:
            cands = [f for f in os.listdir(src) if os.path.splitext(f)[0] == s["id"]]
            if not cands:
                sys.exit(f"missing file for segment {s['id']}")
            x = load(os.path.join(src, cands[0]))
            sf.write(os.path.join(out_dir, s["id"] + ".wav"), x, SR)
            durs[s["id"]] = len(x) / SR
    else:
        gap = np.zeros(int(1.6 * SR), np.float32)  # files are joined with a pause like a <break>
        x = np.concatenate([np.concatenate([load(f), gap]) for f in srcs])[: -len(gap)]
        sil = silences(x)
        need = len(segs) - 1
        if len(sil) < need:
            sys.exit(f"found only {len(sil)} pauses, need {need}: was the script pasted with the <break> tags?")
        # the inter-segment breaks are the longest pauses
        cuts = sorted(sorted(sil, key=lambda s: s[1] - s[0], reverse=True)[:need])
        if min(b - a for a, b in cuts) < 0.9:
            # breaks were not rendered as long pauses: pick, for each expected boundary
            # (from text length), the nearest pause instead
            chars = np.cumsum([len(s.get("tts", s["text"])) for s in segs], dtype=float)
            expect = chars[:-1] / chars[-1] * (len(x) / SR)
            cuts, used = [], set()
            for e in expect:
                best = min((abs((a + b) / 2 - e), i) for i, (a, b) in enumerate(sil) if i not in used)[1]
                used.add(best)
                cuts.append(sil[best])
            cuts.sort()
            print("pauses too short for a clean split; aligned cuts to expected positions")
        shortest_cut = min(b - a for a, b in cuts)
        others = sorted((b - a for a, b in sil if (a, b) not in cuts), reverse=True)
        print(f"{len(sil)} pauses; shortest cut {shortest_cut:.2f}s, longest non-cut {others[0] if others else 0:.2f}s")
        bounds = [0.0] + [(a + b) / 2 for a, b in cuts] + [len(x) / SR]
        chars = np.array([len(s["text"]) for s in segs], float)
        lens = np.diff(bounds)
        ratio = (lens / lens.sum()) / (chars / chars.sum())
        bad = [segs[i]["id"] for i, r in enumerate(ratio) if r < 0.5 or r > 2.0]
        if bad:
            print("WARNING: segment lengths look off for", bad, "- check the cut points")
        for s, a, b in zip(segs, bounds[:-1], bounds[1:]):
            seg = x[int(a * SR): int(b * SR)]
            # trim the silence we cut inside, keep 60 ms of air
            nz = np.where(np.abs(seg) > 10 ** (-42 / 20))[0]
            if len(nz):
                seg = seg[max(0, nz[0] - int(0.06 * SR)): nz[-1] + int(0.12 * SR)]
            sf.write(os.path.join(out_dir, s["id"] + ".wav"), seg, SR)
            durs[s["id"]] = len(seg) / SR
    json.dump(durs, open(os.path.join(out_dir, "durations.json"), "w"), indent=1)
    print(f"imported {len(durs)} segments, {sum(durs.values()):.1f}s of narration")


if __name__ == "__main__":
    main()
