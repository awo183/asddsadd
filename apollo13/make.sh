#!/usr/bin/env bash
# Build "The 28-Volt Switch" (English) and "Spínač na 28 voltů" (Czech).
#   apollo13/make.sh [en|cs|both]      (default: both)
# Needs: .work/venv with requirements.txt, ElevenLabs access (an outbound proxy credential
# or ELEVENLABS_API_KEY; the key is never printed), and the assets from fetch_assets.py.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-.work/venv/bin/python}
which=${1:-both}

[[ -d build/apollo13/assets/nasa ]] || "$PY" apollo13/fetch_assets.py
for lang in en cs; do
  [[ $which == both || $which == "$lang" ]] || continue
  FILM_LANG=$lang "$PY" apollo13/tts.py                 # one ElevenLabs request per sentence, cached
  FILM_LANG=$lang "$PY" apollo13/render.py all          # scenes in parallel (JOBS=4)
  FILM_LANG=$lang STEMS=1 "$PY" apollo13/audio.py       # score, sound effects, mix
  FILM_LANG=$lang "$PY" apollo13/finalize.py            # film, 720p copy, .srt, narration .mp3
done
