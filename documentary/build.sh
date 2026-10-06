#!/usr/bin/env bash
# Build "Uran pro Stalina" (Czech version) from scratch.
# (The English cut "Uranium for Stalin" is reproducible from commit 04bf1ff.)
#
#   ./build.sh                                   # GPU (NVENC) if available, else CPU
#   ENCODER=nvenc ./build.sh                     # require the GPU encoder
#   NARRATION="narace_1.mp3 narace_2.mp3" ./build.sh   # use your ElevenLabs recording (see NARRACE_ElevenLabs.txt)
#   ELEVENLABS_API_KEY=... ./build.sh            # or generate the voice through the ElevenLabs API
#   (with neither, a temporary draft voice is used for timing/previews)
#
# Needs: python3, ffmpeg, ~2 GB disk. Python deps: see requirements.txt.
set -euo pipefail
cd "$(dirname "$0")/pipeline"

export DOC_BUILD="${DOC_BUILD:-$(cd .. && pwd)/build}"
export KOKORO_DIR="${KOKORO_DIR:-$DOC_BUILD/tts}"
export DOC_LANG="${DOC_LANG:-cs}"
ENCODER="${ENCODER:-auto}"
mkdir -p "$DOC_BUILD"/{assets,fonts,geo,tts,voice}

fetch() { [ -s "$2" ] || curl -sSL --retry 4 -o "$2" "$1"; }

echo "== fonts and map data"
GF=https://raw.githubusercontent.com/google/fonts/main
fetch "$GF/ofl/bigshouldersstencildisplay/BigShouldersStencilDisplay%5Bwght%5D.ttf" "$DOC_BUILD/fonts/BigShouldersStencilDisplay.ttf"
fetch "$GF/ofl/bigshouldersdisplay/BigShouldersDisplay%5Bwght%5D.ttf"               "$DOC_BUILD/fonts/BigShouldersDisplay.ttf"
fetch "$GF/ofl/sourceserif4/SourceSerif4%5Bopsz,wght%5D.ttf"                         "$DOC_BUILD/fonts/SourceSerif4.ttf"
fetch "$GF/ofl/sourceserif4/SourceSerif4-Italic%5Bopsz,wght%5D.ttf"                  "$DOC_BUILD/fonts/SourceSerif4-Italic.ttf"
fetch "$GF/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf"                        "$DOC_BUILD/fonts/PlayfairDisplay.ttf"
fetch "$GF/apache/specialelite/SpecialElite-Regular.ttf"                             "$DOC_BUILD/fonts/SpecialElite-Regular.ttf"
fetch "$GF/ofl/courierprime/CourierPrime-Regular.ttf"                                "$DOC_BUILD/fonts/CourierPrime-Regular.ttf"
fetch "$GF/ofl/ibmplexsans/IBMPlexSans%5Bwdth,wght%5D.ttf"                          "$DOC_BUILD/fonts/IBMPlexSans.ttf"
NE=https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson
fetch "$NE/ne_50m_admin_0_countries.geojson" "$DOC_BUILD/geo/countries50.geojson"

echo "== archive footage and photographs (Wikimedia Commons)"
python3 fetch_assets.py "$DOC_BUILD/assets"

echo "== narration ($DOC_LANG)"
if [ -n "${NARRATION:-}" ]; then
  # your ElevenLabs recording: cut into script lines by speech recognition (works with or
  # without <break> pauses); import_narration.py is the pause-based fallback
  mkdir -p "$DOC_BUILD/asr"
  if [ ! -d "$DOC_BUILD/asr/vosk-model-small-cs-0.4-rhasspy" ]; then
    fetch https://alphacephei.com/vosk/models/vosk-model-small-cs-0.4-rhasspy.zip "$DOC_BUILD/asr/cs.zip"
    python3 -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$DOC_BUILD/asr/cs.zip" "$DOC_BUILD/asr"
  fi
  [ -f "$DOC_BUILD/voice/durations.json" ] || python3 tts_draft.py   # placeholder for lines not recorded yet
  python3 align_narration.py $NARRATION || python3 import_narration.py $NARRATION
elif [ -n "${ELEVENLABS_API_KEY:-}" ]; then
  python3 tts_elevenlabs.py                          # ElevenLabs API
else
  echo "   no ElevenLabs recording or key: using the temporary draft voice"
  python3 tts_draft.py
fi

echo "== edit, sound, subtitles"
python3 timeline.py
python3 audio.py
python3 subtitles.py

echo "== picture ($ENCODER)"
python3 render.py --encoder "$ENCODER"

echo "== mux"
python3 mux.py
ls -lh "$DOC_BUILD"/Uran_pro_Stalina*.mp4
