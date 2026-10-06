"""Join the rendered scenes with the mix and write, for the current FILM_LANG:
the 1080p film (with a soft subtitle track), a 720p copy under 26 MB, an .srt
and a voice-only MP3. The audio arrives already mastered to -16 LUFS from
audio.py (fixed gain + gentle limiter); this step only encodes and measures."""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import timeline  # noqa: E402
from common import load_narration  # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "output")
LANG = timeline.LANG
B = timeline.CBUILD
SEGMENTS = load_narration(LANG)

if LANG == "en":
    NAME, TITLE, SUB_LANG = "twenty-boats", "Twenty Boats", "eng"
    SPOKEN = [("eleven hundred and seventy-eight", "1,178"), ("nine hundred and sixty-two", "962"),
              ("seven hundred and ten", "710"), ("twenty-two hundred", "2,200"),
              ("fifteen hundred", "1,500"), ("eighteen ninety-four", "1894"),
              ("thirteen thousand", "13,000"), ("forty-six thousand", "46,000"),
              ("ten thousand", "10,000"), ("nineteen-oh-nine", "1909"),
              ("eleven forty p.m.", "11:40 p.m."), ("April fourteenth", "April 14"),
              ("twenty miles", "20 miles"), ("fifty-eight miles", "58 miles"),
              ("sixty-five", "65"), ("twenty-eight", "28")]
else:
    NAME, TITLE, SUB_LANG = "dvacet-clunu", "Dvacet člunů", "ces"
    SPOKEN = [("tisíc sto sedmdesát osm", "1 178"), ("devět set šedesát dva", "962"),
              ("sedm set deset", "710"), ("dva tisíce dvě stě", "2 200"),
              ("tisíc pět set", "1 500"), ("osmnáct set devadesát čtyři", "1894"),
              ("třinácti tisíc", "13 000"), ("čtyřicet šest tisíc", "46 000"),
              ("deset tisíc", "10 000"), ("devatenáct set devět", "1909"),
              ("Čtrnáctého dubna", "14. dubna"), ("dvacet mil", "20 mil"),
              ("padesát osm mil", "58 mil"), ("šedesát pět", "65"), ("dvacet osm", "28")]
SPOKEN = [(a, b.replace(" ", "\u00a0") if LANG == "cs" else b) for a, b in SPOKEN]
MAX_LINE = 42


def stamp(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def display(text):
    for a, b in SPOKEN:
        text = text.replace(a, b)
    return text


def wrap2(text):
    """Break a cue into at most two balanced lines."""
    if len(text) <= MAX_LINE:
        return text
    words = text.split(" ")
    best, cut = None, 1
    for k in range(1, len(words)):
        a, b = " ".join(words[:k]), " ".join(words[k:])
        score = max(len(a), len(b)) - (10 if a[-1] in ",.?!:;" else 0)
        if max(len(a), len(b)) > MAX_LINE + 4:
            score += 100
        if best is None or score < best:
            best, cut = score, k
    return " ".join(words[:cut]) + "\n" + " ".join(words[cut:])


def cues_for(sentence, words, offset):
    """Split one sentence into subtitle cues (<= 2 lines of ~42 chars), timed by its words,
    without breaking inside a number that is written as digits on screen."""
    toks = sentence.split(" ")
    assert len(toks) == len(words), (sentence, len(toks), len(words))
    protected = set()
    for a, _ in SPOKEN:
        n = len(a.split(" "))
        for i in range(len(toks) - n + 1):
            if " ".join(toks[i:i + n]).strip(".,?!:") .startswith(a) or \
                    re.sub(r"[.,?!:]$", "", " ".join(toks[i:i + n])) == a:
                protected.update(range(i + 1, i + n))      # can't cut before these
    out, start = [], 0
    while start < len(toks):
        end = start + 1
        best = end
        while end <= len(toks):
            if len(display(" ".join(toks[start:end]))) > 2 * MAX_LINE - 4:
                break
            if end == len(toks) or end not in protected:
                best = end
            end += 1
        # prefer to cut after punctuation
        for k in range(best, start + 1, -1):
            if k < len(toks) and toks[k - 1][-1] in ",.:;?" and k not in protected and \
                    k - start >= (best - start) * 0.5:
                best = k
                break
        text = display(" ".join(toks[start:best]))
        out.append((offset + words[start][1], offset + words[best - 1][2], wrap2(text)))
        start = best
    return out


def write_srt(path):
    text = dict(SEGMENTS)
    cues = []
    for s in timeline.build():
        if s["voice"] is None:
            continue
        sents = text[s["key"]]
        for i, sent in enumerate(sents):
            ws = [w for w in s["words"] if w[3] == i]
            cues += cues_for(sent, ws, s["start"])
    # tidy: minimum duration, no overlaps
    fixed = []
    for k, (a, b, txt) in enumerate(cues):
        b = max(b + 0.25, a + 1.0)
        if k + 1 < len(cues):
            b = min(b, cues[k + 1][0] - 0.05)
        fixed.append((a, b, txt))
    with open(path, "w", encoding="utf-8") as f:
        for i, (a, b, txt) in enumerate(fixed, 1):
            f.write(f"{i}\n{stamp(a)} --> {stamp(b)}\n{txt}\n\n")
    return len(fixed)


def run(cmd, capture=False):
    print("+", " ".join(str(c) for c in cmd[:8]), "...", flush=True)
    r = subprocess.run(cmd, check=True, capture_output=capture, text=True)
    return r.stderr if capture else None


def measure(path):
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-map", "0:a:0", "-af",
               "ebur128=peak=true", "-f", "null", "-"], capture=True)
    i = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])
    tp = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", err)[-1])
    return i, tp


def main():
    os.makedirs(OUT, exist_ok=True)
    srt = os.path.join(OUT, f"{NAME}.srt")
    n = write_srt(srt)
    print(f"{n} subtitle cues -> {srt}")
    joined = os.path.join(B, "joined.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i",
         os.path.join(B, "scenes", "list.txt"), "-c", "copy", joined])
    mix = os.path.join(B, "mix.wav")          # already mastered to -16 LUFS by audio.py
    master = os.path.join(OUT, f"{NAME}.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-i", joined, "-i", mix, "-i", srt,
         "-map", "0:v", "-map", "1:a", "-map", "2:s", "-c:v", "libx264", "-preset", "slow",
         "-crf", "20", "-maxrate", "9M", "-bufsize", "18M", "-pix_fmt", "yuv420p", "-r", "30",
         "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest",
         "-c:s", "mov_text", "-metadata:s:s:0", f"language={SUB_LANG}",
         "-metadata:s:a:0", f"language={SUB_LANG}", "-metadata", f"title={TITLE}",
         "-movflags", "+faststart", master])
    small = os.path.join(OUT, f"{NAME}-720p.mp4")
    log = os.path.join(B, "x264pass")
    dur = sum(s["dur"] for s in timeline.build())
    kbps = min(2400, int(25.0 * 8 * 1000 / dur - 128 - 20))      # stays under ~25 MB
    # video from the master, audio straight from the mastered mix (no AAC-to-AAC re-encode)
    vid = ["-vf", "scale=1280:720:flags=lanczos", "-c:v", "libx264", "-preset", "slow",
           "-b:v", f"{kbps}k", "-passlogfile", log]
    run(["ffmpeg", "-v", "error", "-y", "-i", master, *vid, "-pass", "1", "-an", "-f", "mp4",
         "/dev/null"])
    run(["ffmpeg", "-v", "error", "-y", "-i", master, "-i", mix, *vid, "-pass", "2",
         "-map", "0:v", "-map", "1:a", "-map", "0:s", "-c:a", "aac", "-b:a", "160k",
         "-ar", "48000", "-shortest", "-c:s", "mov_text", "-metadata:s:s:0", f"language={SUB_LANG}",
         "-metadata:s:a:0", f"language={SUB_LANG}", "-movflags", "+faststart", small])
    voice = os.path.join(B, "voice_master.wav")
    run(["ffmpeg", "-v", "error", "-y", "-i", voice, "-ac", "1", "-ar", "44100",
         "-c:a", "libmp3lame", "-b:a", "192k", "-metadata", f"title={TITLE} (narration)",
         os.path.join(OUT, f"{NAME}-narration.mp3")])
    i, tp = measure(master)
    size = os.path.getsize(small) / 1e6
    print(f"wrote {master} ({dur:.1f}s, {i:.1f} LUFS, true peak {tp:.1f} dBFS)")
    print(f"wrote {small} ({size:.1f} MB)")


if __name__ == "__main__":
    main()
