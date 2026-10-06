"""Join the rendered scenes with the mix; write the 1080p film, a 720p copy under
26 MB, the .srt subtitles (cued from the real word timings) and a voice-only MP3.
Loudness: two-pass EBU R128 normalisation to -16 LUFS.
"""
import importlib.util
import json
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "output")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


timeline = _load("a13_timeline", os.path.join(HERE, "timeline.py"))
LANG = timeline.LANG
narration = _load("a13_narration", os.path.join(HERE, "narration.py" if LANG == "en" else f"narration_{LANG}.py"))
B = timeline.ABUILD
if LANG == "en":
    NAME, TITLE, SUB_LANG = "the-28-volt-switch", "The 28-Volt Switch", "eng"
else:
    NAME, TITLE, SUB_LANG = "spinac-na-28-voltu", "Spínač na 28 voltů", "ces"
MAX_CUE, MAX_LINE = 80, 42


def stamp(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def norm(w):
    return re.sub(r"[^\w]", "", w.lower())


def protected(words, phrases):
    """Indices of words that sit inside a phrase the subtitles rewrite (keep them together)."""
    keep = set()
    toks = [norm(w[0]) for w in words]
    for a, _ in phrases:
        p = [norm(x) for x in a.split()]
        for i in range(len(toks) - len(p) + 1):
            if toks[i:i + len(p)] == p:
                keep.update(range(i + 1, i + len(p)))       # no break before these
    return keep


def chunks(words):
    """Split a sentence's words into subtitle cues of at most MAX_CUE characters,
    preferring breaks after commas."""
    keep = protected(words, narration.SUBTITLE)
    out, cur = [], []
    def shown(ws):
        text = " ".join(x[0] for x in ws)
        for a_, b_ in narration.SUBTITLE:
            text = text.replace(a_, b_)
        return text
    for i, w in enumerate(words):
        trial = shown(cur + [w])
        if cur and len(trial) > MAX_CUE and i not in keep:
            # back up to the last comma if it leaves a reasonable cue
            cut = max((k for k, x in enumerate(cur) if x[0].endswith(",") and k >= 3 and (k + 1) not in keep),
                      default=None)
            if cut is not None and cut < len(cur) - 1:
                out.append(cur[:cut + 1])
                cur = cur[cut + 1:]
            else:
                out.append(cur)
                cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return out


def two_lines(text):
    if len(text) <= MAX_LINE:
        return text
    words = text.split()
    best, bi = None, 1
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        score = max(len(a), len(b)) + (0 if a.endswith(",") else 3)
        if best is None or score < best:
            best, bi = score, i
    return " ".join(words[:bi]) + "\n" + " ".join(words[bi:])


def write_srt(path):
    cues = []
    text_of = dict(narration.SEGMENTS)
    for s in timeline.build():
        if s["voice"] is None:
            continue
        i0 = 0
        for sentence in text_of[s["key"]]:          # words belong to sentences by count, not by time
            n = len(sentence.split())
            sent_words = s["words"][i0:i0 + n]
            i0 += n
            for ch in chunks(sent_words):
                text = " ".join(w[0] for w in ch)
                for a, b in narration.SUBTITLE:
                    text = text.replace(a, b)
                cues.append([s["start"] + ch[0][1], s["start"] + ch[-1][2] + 0.25, text])
    for i in range(len(cues) - 1):                      # no overlaps, no flicker
        cues[i][1] = min(cues[i][1], cues[i + 1][0] - 0.04)
        if cues[i + 1][0] - cues[i][1] < 0.3:
            cues[i][1] = cues[i + 1][0] - 0.04
    with open(path, "w", encoding="utf8") as f:
        for i, (t0, t1, line) in enumerate(cues, 1):
            f.write(f"{i}\n{stamp(t0)} --> {stamp(t1)}\n{two_lines(line)}\n\n")
    return len(cues)


def run(cmd, capture=False):
    print("+", " ".join(cmd[:6]), "...")
    r = subprocess.run(cmd, check=True, capture_output=capture, text=True)
    return r.stderr if capture else None


def loudnorm_filter(src):
    """Two-pass loudnorm: measure, then normalise linearly to -16 LUFS / -1.5 dBTP."""
    err = run(["ffmpeg", "-hide_banner", "-i", src, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
               "-f", "null", "-"], capture=True)
    m = json.loads(err[err.rindex("{"):err.rindex("}") + 1])
    return (f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
            f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:"
            f"linear=true")


def main():
    os.makedirs(OUT, exist_ok=True)
    srt = os.path.join(OUT, f"{NAME}.srt")
    print(f"{write_srt(srt)} subtitle cues")
    joined = os.path.join(B, "joined.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i",
         os.path.join(B, "scenes", "list.txt"), "-c", "copy", joined])
    mix = os.path.join(B, "mix.wav")
    af = loudnorm_filter(mix)
    master = os.path.join(OUT, f"{NAME}.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-i", joined, "-i", mix, "-i", srt,
         "-map", "0:v", "-map", "1:a", "-map", "2:s", "-c:v", "libx264", "-preset", "slow",
         "-crf", "21", "-maxrate", "4500k", "-bufsize", "9M", "-pix_fmt", "yuv420p", "-r", "30",
         "-af", af, "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-c:s", "mov_text", "-metadata:s:s:0", f"language={SUB_LANG}",
         "-metadata", f"title={TITLE}", "-movflags", "+faststart", master])
    small = os.path.join(OUT, f"{NAME}-720p.mp4")
    log = os.path.join(B, "x264pass")
    dur = sum(s["dur"] for s in timeline.build())
    # stay under 26 MB (decimal) whatever the running time: two-pass to a fixed bitrate
    kbps = int(min(2200, 0.95 * 26e6 * 8 / 1000 / dur - 128))
    base = ["ffmpeg", "-v", "error", "-y", "-i", master, "-vf", "scale=1280:720:flags=lanczos",
            "-c:v", "libx264", "-preset", "slow", "-b:v", f"{kbps}k", "-passlogfile", log]
    run(base + ["-pass", "1", "-an", "-f", "mp4", "/dev/null"])
    run(base + ["-pass", "2", "-map", "0:v", "-map", "0:a", "-map", "0:s", "-c:a", "aac",
                "-b:a", "128k", "-c:s", "mov_text", "-movflags", "+faststart", small])
    voice = os.path.join(B, "stems", "voice.wav")
    if os.path.exists(voice):
        run(["ffmpeg", "-v", "error", "-y", "-i", voice, "-af", loudnorm_filter(voice), "-ac", "1",
             "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "128k",
             os.path.join(OUT, f"{NAME}-narration.mp3")])
    for p in (master, small):
        print(f"wrote {p} ({os.path.getsize(p) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
