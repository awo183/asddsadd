#!/usr/bin/env bash
# Build "The Calmest Man on the Plane" (English) and "Nejklidnější muž v letadle" (Czech).
#   cooper/make.sh [en|cs|both]      (default: both)
# Needs the assets in build/cooper/assets (see cooper/SCRIPT.md for sources), the
# Kokoro models for English and the Piper cs_CZ "jirka" voice for Czech.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-.work/venv/bin/python}
MODELS=${MODELS:-.work/models}
which=${1:-both}

if [[ $which == en || $which == both ]]; then
  NARRATION=cooper/narration.py VOICE="am_michael:0.7,am_onyx:0.3" SPEED=1.02 \
    "$PY" src/tts.py "$MODELS" build/cooper/voice
  FILM_LANG=en "$PY" cooper/render.py all
  FILM_LANG=en STEMS=1 "$PY" cooper/audio.py
  FILM_LANG=en "$PY" cooper/finalize.py
fi
if [[ $which == cs || $which == both ]]; then
  CS_TTS=piper CS_LENGTH=0.95 "$PY" cooper/tts_cs.py build/cooper_cs/voice
  FILM_LANG=cs "$PY" cooper/render.py all
  FILM_LANG=cs STEMS=1 "$PY" cooper/audio.py
  VOICE_CREDIT="Piper (cs_CZ jirka)" FILM_LANG=cs "$PY" cooper/finalize.py
fi
