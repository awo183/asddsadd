"""Join the rendered scenes with the mix; write the film, a 720p copy and subtitles."""
import importlib.util
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "output")
NAME = "the-calmest-man-on-the-plane"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


timeline = _load("cooper_timeline", os.path.join(HERE, "timeline.py"))
narration = _load("cooper_narration", os.path.join(HERE, "narration.py"))
B = timeline.CBUILD
SPOKEN = [("nineteen seventy-one", "1971"), ("nineteen eighty", "1980"),
          ("eight thirteen p.m.", "8:13 p.m."), ("two hundred thousand dollars", "$200,000"),
          ("five thousand eight hundred dollars", "$5,800")]


def stamp(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(path):
    with open(os.path.join(B, "voice", "timings.json")) as f:
        timings = json.load(f)
    text = dict(narration.SEGMENTS)
    cues = []
    for s in timeline.build():
        if s["voice"] is None:
            continue
        sent, starts = text[s["key"]], s["sentences"]
        end = s["voice"] + timings[s["key"]]["duration"]
        for k, line in enumerate(sent):
            t0 = s["start"] + starts[k]
            t1 = s["start"] + (starts[k + 1] - 0.1 if k + 1 < len(sent) else end)
            for a, b in SPOKEN:
                line = line.replace(a, b)
            cues.append((t0, t1, line))
    with open(path, "w") as f:
        for i, (t0, t1, line) in enumerate(cues, 1):
            f.write(f"{i}\n{stamp(t0)} --> {stamp(t1)}\n{line}\n\n")


def run(cmd):
    print("+", " ".join(cmd[:6]), "...")
    subprocess.run(cmd, check=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    srt = os.path.join(OUT, f"{NAME}.srt")
    write_srt(srt)
    joined = os.path.join(B, "joined.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i",
         os.path.join(B, "scenes", "list.txt"), "-c", "copy", joined])
    master = os.path.join(OUT, f"{NAME}.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-i", joined, "-i", os.path.join(B, "mix.wav"), "-i", srt,
         "-map", "0:v", "-map", "1:a", "-map", "2:s", "-c:v", "libx264", "-preset", "slow",
         "-crf", "21", "-maxrate", "6M", "-bufsize", "12M", "-pix_fmt", "yuv420p", "-tune", "film",
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-c:s", "mov_text", "-metadata:s:s:0", "language=eng",
         "-metadata", "title=The Calmest Man on the Plane", "-movflags", "+faststart", master])
    small = os.path.join(OUT, f"{NAME}-720p.mp4")
    log = os.path.join(B, "x264pass")
    base = ["ffmpeg", "-v", "error", "-y", "-i", master, "-vf", "scale=1280:720:flags=lanczos",
            "-c:v", "libx264", "-preset", "slow", "-b:v", "1600k", "-passlogfile", log]
    run(base + ["-pass", "1", "-an", "-f", "mp4", "/dev/null"])
    run(base + ["-pass", "2", "-map", "0:v", "-map", "0:a", "-map", "0:s", "-c:a", "aac",
                "-b:a", "128k", "-c:s", "mov_text", "-movflags", "+faststart", small])
    voice = os.path.join(B, "stems", "voice.wav")
    if os.path.exists(voice):
        run(["ffmpeg", "-v", "error", "-y", "-i", voice, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
             "-ac", "1", "-c:a", "libmp3lame", "-b:a", "128k",
             os.path.join(OUT, f"{NAME}-narration.mp3")])
    print("wrote", master, small)


if __name__ == "__main__":
    main()
