#!/usr/bin/env bash
# Build "How Machines Learned to See" from scratch.
#
#   ./make.sh            full pipeline (download, voice, detection, render, mix)
#
# Needs: python3, ffmpeg, ~1 GB of disk, network access to github.com and
# raw/media.githubusercontent.com. Takes ~20-30 minutes on 4 CPU cores.
set -euo pipefail
cd "$(dirname "$0")"

WORK=${WORK:-$PWD/.work}
export FOOTAGE=$WORK/footage
MODELS=$WORK/models
mkdir -p "$FOOTAGE" "$MODELS" build output

# 1. python environment
if [ ! -x "$WORK/venv/bin/python" ]; then
  python3 -m venv "$WORK/venv"
  "$WORK/venv/bin/pip" install -q -r requirements.txt
fi
PY="$WORK/venv/bin/python"

# 2. real footage: Intel IoT DevKit sample videos (CC BY 4.0)
SRC=https://raw.githubusercontent.com/intel-iot-devkit/sample-videos/master
for clip in car-detection classroom face-demographics-walking-and-pause \
            face-demographics-walking fruit-and-vegetable-detection \
            head-pose-face-detection-female-and-male one-by-one-person-detection \
            people-detection person-bicycle-car-detection store-aisle-detection \
            worker-zone-detection driver-action-recognition bottle-detection bolt-detection; do
  [ -s "$FOOTAGE/$clip.mp4" ] || curl -sSL --retry 3 -o "$FOOTAGE/$clip.mp4" "$SRC/$clip.mp4"
done

# 3. models: Kokoro TTS voice, YOLOX + YuNet detectors (OpenCV Model Zoo)
K=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
Z=https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models
[ -s "$MODELS/kokoro-v1.0.onnx" ] || curl -sSL -o "$MODELS/kokoro-v1.0.onnx" "$K/kokoro-v1.0.onnx"
[ -s "$MODELS/voices-v1.0.bin" ] || curl -sSL -o "$MODELS/voices-v1.0.bin" "$K/voices-v1.0.bin"
[ -s "$MODELS/object_detection_yolox_2022nov.onnx" ] || curl -sSL -o "$MODELS/object_detection_yolox_2022nov.onnx" \
  "$Z/object_detection_yolox/object_detection_yolox_2022nov.onnx"
[ -s "$MODELS/face_detection_yunet_2023mar.onnx" ] || curl -sSL -o "$MODELS/face_detection_yunet_2023mar.onnx" \
  "$Z/face_detection_yunet/face_detection_yunet_2023mar.onnx"

# 4. narration, detections, example crops
"$PY" src/tts.py "$MODELS" build/voice
"$PY" src/detect.py "$MODELS" "$FOOTAGE" build/detections
"$PY" src/crops.py

# 5. picture, sound, final film
"$PY" src/render.py all
STEMS=1 "$PY" src/audio.py
"$PY" src/finalize.py
