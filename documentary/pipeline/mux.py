"""Combine picture, final mix and subtitles into the finished film(s)."""
import argparse, os, subprocess
from common import BUILD

ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(BUILD, "Uranium_for_Stalin.mp4"))
ap.add_argument("--web", default=os.path.join(BUILD, "Uranium_for_Stalin_web.mp4"),
                help="smaller copy (<100 MB) for sharing / committing; '' to skip")
ap.add_argument("--web-bitrate", default="950k")
args = ap.parse_args()

picture = os.path.join(BUILD, "picture.mp4")
mix = os.path.join(BUILD, "mix.wav")
srt = os.path.join(BUILD, "subtitles.en.srt")
meta = ["-metadata", "title=Uranium for Stalin",
        "-metadata", "comment=Czechoslovak uranium, the first Soviet atomic bomb and the labour camps of Jáchymov",
        "-metadata:s:a:0", "language=eng", "-metadata:s:s:0", "language=eng"]

subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", picture, "-i", mix, "-i", srt,
                "-map", "0:v", "-map", "1:a", "-map", "2:s", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-c:s", "mov_text", *meta, "-movflags", "+faststart", args.out], check=True)
print("film ->", args.out)

if args.web:
    # two-pass 1080p x264 at a fixed budget so the file fits GitHub's 100 MB limit
    log = os.path.join(BUILD, "x264_2pass")
    common = ["-i", picture, "-c:v", "libx264", "-preset", "slow", "-b:v", args.web_bitrate, "-maxrate", "2500k",
              "-bufsize", "5000k", "-pix_fmt", "yuv420p", "-passlogfile", log]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *common, "-pass", "1", "-an", "-f", "null", "-"], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", *common[:2], "-i", mix, "-i", srt, *common[2:], "-pass", "2",
                    "-map", "0:v", "-map", "1:a", "-map", "2:s", "-c:a", "aac", "-b:a", "128k", "-c:s", "mov_text",
                    *meta, "-movflags", "+faststart", args.web], check=True)
    print("web copy ->", args.web)
