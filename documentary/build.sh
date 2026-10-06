#!/usr/bin/env bash
# Build "Uranium for Stalin" from scratch.
#
#   ./build.sh            # auto: renders on an NVIDIA GPU (NVENC) if one is available, else CPU
#   ENCODER=nvenc ./build.sh   # require the GPU encoder
#   ENCODER=x264  ./build.sh   # force CPU encoding
#
# Needs: python3, ffmpeg, ~2 GB disk. Python deps: see requirements.txt.
set -euo pipefail
cd "$(dirname "$0")/pipeline"

export DOC_BUILD="${DOC_BUILD:-$(cd .. && pwd)/build}"
export KOKORO_DIR="${KOKORO_DIR:-$DOC_BUILD/tts}"
ENCODER="${ENCODER:-auto}"
mkdir -p "$DOC_BUILD"/{assets,fonts,geo,tts,voice}

fetch() { [ -s "$2" ] || curl -sSL --retry 4 -o "$2" "$1"; }

echo "== fonts, map data, voice model"
GF=https://raw.githubusercontent.com/google/fonts/main
fetch "$GF/ofl/bigshouldersstencildisplay/BigShouldersStencilDisplay%5Bwght%5D.ttf" "$DOC_BUILD/fonts/BigShouldersStencilDisplay.ttf"
fetch "$GF/ofl/bigshouldersdisplay/BigShouldersDisplay%5Bwght%5D.ttf"               "$DOC_BUILD/fonts/BigShouldersDisplay.ttf"
fetch "$GF/ofl/sourceserif4/SourceSerif4%5Bopsz,wght%5D.ttf"                         "$DOC_BUILD/fonts/SourceSerif4.ttf"
fetch "$GF/ofl/sourceserif4/SourceSerif4-Italic%5Bopsz,wght%5D.ttf"                  "$DOC_BUILD/fonts/SourceSerif4-Italic.ttf"
fetch "$GF/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf"                        "$DOC_BUILD/fonts/PlayfairDisplay.ttf"
fetch "$GF/apache/specialelite/SpecialElite-Regular.ttf"                             "$DOC_BUILD/fonts/SpecialElite-Regular.ttf"
fetch "$GF/ofl/courierprime/CourierPrime-Regular.ttf"                                "$DOC_BUILD/fonts/CourierPrime-Regular.ttf"
NE=https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson
fetch "$NE/ne_50m_admin_0_countries.geojson" "$DOC_BUILD/geo/countries50.geojson"
KO=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
fetch "$KO/kokoro-v1.0.onnx"  "$KOKORO_DIR/kokoro-v1.0.onnx"
fetch "$KO/voices-v1.0.bin"   "$KOKORO_DIR/voices-v1.0.bin"

echo "== archive footage and photographs (Wikimedia Commons)"
python3 fetch_assets.py "$DOC_BUILD/assets"

echo "== narration"
python3 tts.py "$DOC_BUILD/voice"

echo "== edit, sound, subtitles"
python3 timeline.py
python3 audio.py
python3 subtitles.py

echo "== picture ($ENCODER)"
python3 render.py --encoder "$ENCODER"

echo "== mux"
python3 mux.py
ls -lh "$DOC_BUILD"/Uranium_for_Stalin*.mp4
