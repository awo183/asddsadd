#!/usr/bin/env bash
# Build "Twenty Boats" (English) and "Dvacet člunů" (Czech).
#   titanic/make.sh [en|cs|both]      (default: both)
#
# Needs: python3 with requirements (see titanic/requirements.txt), ffmpeg with
# librubberband, the archival assets in build/titanic/assets (sources and
# licences in titanic/ASSETS.md), Natural Earth land in build/titanic/geo, and
# ELEVENLABS_API_KEY for the narration (eleven_v4). There is no fallback voice:
# if ElevenLabs is unreachable the build stops.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-.work/venv/bin/python}
which=${1:-both}

mkdir -p build/titanic/geo
for f in ne_50m_land; do
  [ -s build/titanic/geo/$f.geojson ] || curl -sSL -o build/titanic/geo/$f.geojson \
    https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/$f.geojson
done

for lang in en cs; do
  [[ $which == both || $which == "$lang" ]] || continue
  FILM_LANG=$lang "$PY" titanic/tts.py            # ElevenLabs, one sentence at a time
  FILM_LANG=$lang "$PY" titanic/render.py all     # scenes in parallel
  FILM_LANG=$lang STEMS=1 "$PY" titanic/audio.py  # score, sound effects, mix
  FILM_LANG=$lang "$PY" titanic/finalize.py       # -16 LUFS, 1080p + 720p, .srt, voice MP3
done
