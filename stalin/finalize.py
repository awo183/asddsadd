"""Mux picture and mix, normalise loudness, write Czech subtitles and a 720p copy."""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout  # noqa: E402
import vox as V  # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "output")
NAME = "stalin-na-splatky"
TITLE = "Stalin na splátky"
SPOKEN = [  # spoken numbers -> digits for the subtitles
    ("devatenáct set šedesát dva", "1962"), ("devatenáct set šedesát jedna", "1961"),
    ("devatenáct set padesát šest", "1956"), ("devatenáct set padesát pět", "1955"),
    ("devatenáct set padesát čtyři", "1954"), ("devatenáct set padesát tři", "1953"),
    ("devatenáct set padesát dva", "1952"), ("devatenáct set čtyřicet devět", "1949"),
    ("devatenáct set čtyřicet osm", "1948"), ("devatenáct set devadesát jedna", "1991"),
    ("dva tisíce dvacet šest", "2026"), ("dva tisíce devatenáct", "2019"), ("dva tisíce dvacet jedna", "2021"),
    ("patnáct a půl metru", "15,5 metru"), ("sto čtyřicet milionů", "140 milionů"),
    ("čtyři a půl milionu", "4,5 milionu"), ("sedmnáct tisíc tun", "17 000 tun"),
    ("dvě stě třicet pět", "235"), ("šest set", "600"), ("tři a půl metru čtverečního", "3,5 m²"),
    ("dvacet pět metrů", "25 metrů"), ("sedm tun", "7 tun"), ("sedmdesát let", "70 let"),
    ("Pětapadesát", "55"),
]


def stamp(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(path, max_chars=42):
    """One cue per short phrase, timed from the word alignment."""
    L = layout.layout()
    cues = []
    for blk in L["voice"]:
        words = blk["words"]
        cur = []
        for k, w in enumerate(words):
            cur.append(w)
            text = " ".join(x["w"] for x in cur)
            end_sentence = re.search(r"[.!?…]$", w["w"])
            nxt = words[k + 1]["w"] if k + 1 < len(words) else ""
            if end_sentence or len(text) + len(nxt) + 1 > max_chars or k + 1 == len(words):
                cues.append([cur[0]["t0"], cur[-1]["t1"] + 0.15, text])
                cur = []
    for k in range(len(cues) - 1):
        cues[k][1] = min(cues[k][1], cues[k + 1][0] - 0.02)
    with open(path, "w") as f:
        for i, (t0, t1, line) in enumerate(cues, 1):
            for a, b in SPOKEN:
                line = line.replace(a, b)
            f.write(f"{i}\n{stamp(t0)} --> {stamp(t1)}\n{line}\n\n")


def run(cmd):
    print("+", " ".join(cmd[:6]), "...", flush=True)
    subprocess.run(cmd, check=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    srt = os.path.join(OUT, f"{NAME}.srt")
    write_srt(srt)
    video = os.path.join(V.BUILD, "video.mp4")
    master = os.path.join(OUT, f"{NAME}.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", os.path.join(V.BUILD, "mix.wav"), "-i", srt,
         "-map", "0:v", "-map", "1:a", "-map", "2:s", "-c:v", "libx264", "-preset", "slow", "-crf", "19",
         "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p", "-tune", "film",
         "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-c:s", "mov_text", "-metadata:s:s:0", "language=ces", "-metadata", f"title={TITLE}",
         "-shortest", "-movflags", "+faststart", master])
    small = os.path.join(OUT, f"{NAME}-720p.mp4")
    dur = layout.layout()["duration"]
    kbps = min(2200, int(45 * 8 * 1024 / dur - 140))      # keep the 720p copy under ~45 MB
    log = os.path.join(V.BUILD, "x264pass")
    base = ["ffmpeg", "-v", "error", "-y", "-i", master, "-vf", "scale=1280:720:flags=lanczos", "-c:v", "libx264",
            "-preset", "slow", "-b:v", f"{kbps}k", "-passlogfile", log]
    run(base + ["-pass", "1", "-an", "-f", "mp4", "/dev/null"])
    run(base + ["-pass", "2", "-map", "0:v", "-map", "0:a", "-map", "0:s", "-c:a", "aac", "-b:a", "128k",
                "-c:s", "mov_text", "-movflags", "+faststart", small])
    print("wrote", master, small)


if __name__ == "__main__":
    main()
