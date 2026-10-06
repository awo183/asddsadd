"""Join the rendered scenes, lay in the mix, and write the final film + subtitles."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline  # noqa: E402
from fx import BUILD, ROOT  # noqa: E402
from narration import SEGMENTS  # noqa: E402

OUT = os.path.join(ROOT, "output")
NAME = "how-machines-learned-to-see"


def stamp(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(path):
    import json
    with open(os.path.join(BUILD, "voice", "timings.json")) as f:
        timings = json.load(f)
    text = dict(SEGMENTS)
    cues = []
    for s in timeline.build():
        if s["voice"] is None:
            continue
        sentences = text[s["key"]]
        starts = s["sentences"]
        end_of_voice = s["voice"] + timings[s["key"]]["duration"]
        # merge the one-word beats ("Person. Car. Bicycle.") into one cue
        k = 0
        while k < len(sentences):
            j = k
            while j + 1 < len(sentences) and len(sentences[j + 1].split()) == 1:
                j += 1
            t0 = s["start"] + starts[k]
            t1 = s["start"] + (starts[j + 1] - 0.1 if j + 1 < len(sentences) else end_of_voice)
            line = " ".join(sentences[k:j + 1])
            for spoken, written in (("nineteen sixty-six", "1966"), ("two thousand nine", "2009"),
                                    ("twenty twelve", "2012"), ("M.I.T.", "MIT")):
                line = line.replace(spoken, written)
            cues.append((t0, t1, line))
            k = j + 1
    with open(path, "w") as f:
        for i, (t0, t1, line) in enumerate(cues, 1):
            f.write(f"{i}\n{stamp(t0)} --> {stamp(t1)}\n{line}\n\n")


def run(cmd):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    srt = os.path.join(OUT, f"{NAME}.srt")
    write_srt(srt)
    joined = os.path.join(BUILD, "joined.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i",
         os.path.join(BUILD, "scenes", "list.txt"), "-c", "copy", joined])
    run(["ffmpeg", "-v", "error", "-y", "-i", joined, "-i", os.path.join(BUILD, "mix.wav"),
         "-i", srt, "-map", "0:v", "-map", "1:a", "-map", "2:s",
         "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-maxrate", "6M", "-bufsize", "12M",
         "-pix_fmt", "yuv420p", "-profile:v", "high", "-tune", "film",
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-c:s", "mov_text", "-metadata:s:s:0", "language=eng",
         "-metadata", "title=How Machines Learned to See", "-movflags", "+faststart",
         os.path.join(OUT, f"{NAME}.mp4")])
    print("wrote", os.path.join(OUT, f"{NAME}.mp4"))
    voice = os.path.join(BUILD, "stems", "voice.wav")
    if os.path.exists(voice):
        run(["ffmpeg", "-v", "error", "-y", "-i", voice, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
             "-ac", "1", "-c:a", "libmp3lame", "-b:a", "128k", os.path.join(OUT, "narration.mp3")])


if __name__ == "__main__":
    main()
