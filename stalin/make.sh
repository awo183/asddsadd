#!/usr/bin/env bash
# Build "Stalin na splátky" (Czech, ~5 min).
#
# Needs: python3, ffmpeg, yt-dlp, network access, and these services connected
# to the environment: ElevenLabs (voice, sound effects, music), Serper (image
# search), Pexels (stock video). The photo selection in build/stalin/assets/img
# was made by hand from fetch.py's contact sheets; see build/stalin/assets/img/credits.json.
set -euo pipefail
cd "$(dirname "$0")/.."
WORK=${WORK:-$PWD/.work}
if [ ! -x "$WORK/venv/bin/python" ]; then
  python3 -m venv "$WORK/venv"
  "$WORK/venv/bin/pip" install -q numpy pillow opencv-python-headless scipy soundfile "rembg[cpu]"
fi
PY="$WORK/venv/bin/python"

"$PY" stalin/tts.py          # narration, eleven_v4, with word timings
"$PY" stalin/sfx.py          # sound-effect library
"$PY" stalin/music.py        # five music cues
"$PY" stalin/prep.py         # cutouts of people and the monument
"$PY" stalin/render.py all   # picture, rendered in parallel chunks
"$PY" stalin/audio.py        # voice + sound effects + ducked music
"$PY" stalin/finalize.py     # output/stalin-na-splatky.mp4 (+720p, subtitles)
