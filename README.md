# Ramanujan: The Mind That Reached for Infinity

A ~21-minute English documentary on the life of **Srinivasa Ramanujan** (1887–1920): the self-taught
prodigy from Kumbakonam, his 1913 letter to G. H. Hardy, five years at Trinity College, Cambridge,
isolation, illness and depression in wartime England, his election to the Royal Society, his return
to India and early death at 32, and the mathematics he left behind.

The film combines **real archival photographs and film** (Wikimedia Commons, public domain / Creative
Commons), **procedural math animations** (partitions, the 1/π series, taxicab number 1729, a mock theta
function, maps of his voyages), an offline neural **English voiceover**, an original synthesized score,
English subtitles and chapter markers.

> No moving footage of Ramanujan himself is known to exist. Archive film in the documentary shows the
> places and era (British India, steamships, wartime England), and is labelled as such on screen.

## Output

| File | What |
|---|---|
| `video/ramanujan_documentary_1080p.mp4` | 1920×1080, 25 fps, H.264 + AAC, English soft subtitles, chapters (if under GitHub's size limit) |
| `video/parts/*.mp4` | The same film split into chapter files (each < 100 MB) |
| `video/ramanujan_documentary.en.srt` | English subtitles |
| `documentary/` | The full production pipeline (script, TTS, animations, score, compositor) |
| `CREDITS.md` | Every archival image/clip used, with author and license |

## Chapters

0. Prologue – the letter · I. A Boy from Kumbakonam · II. The Notebooks · III. The Letter ·
IV. Crossing the Black Water · V. Two Minds · VI. A Long Winter · VII. Recognition ·
VIII. Homecoming · IX. The Infinite Legacy

## Rebuilding

```bash
pip install kokoro-onnx soundfile opencv-python-headless skia-python matplotlib mpmath numpy
# skia needs libEGL:  apt-get install -y libegl1 libgl1
# models (GitHub releases):
#   https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
#   https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
cd documentary
python3 tts.py MODEL_DIR VO_DIR                       # narration -> VO_DIR/*.wav
DOC_ASSETS=ASSETS_DIR DOC_CACHE=CACHE_DIR \
python3 build.py --vo VO_DIR --media MEDIA_DIR --out OUT_DIR --encoder auto
```

`ASSETS_DIR` holds `fonts/` (Google Fonts, OFL/Apache) and `geo/` (Natural Earth GeoJSON);
`MEDIA_DIR` holds `photos/`, `video/` and `manifest.json` (see `media/manifest.json`).

### GPU rendering

`--encoder auto` (default) uses **NVIDIA NVENC (`h264_nvenc`)** whenever a usable GPU is present and falls
back to `libx264` on the CPU otherwise. `--encoder nvenc` forces the GPU path (it warns and falls back if no
GPU is found). The cloud container this was built in has no GPU, so the published render used `libx264`;
re-running the same command on an NVIDIA machine renders on the GPU with identical output layout.

## Network access used / needed

Used (allowed in the build environment): `pypi.org`, `files.pythonhosted.org`, `github.com` +
release-asset hosts (Kokoro model), `raw.githubusercontent.com` (fonts, Natural Earth),
`commons.wikimedia.org`, `upload.wikimedia.org` (archival media), `archive.ubuntu.com` (libEGL).

Blocked, and worth allowing for a richer cut: `archive.org` and `*.archive.org` (public-domain newsreels and
1900s–1920s film of India and England), `en.wikipedia.org` (fact checks), `www.loc.gov` / `tile.loc.gov`
(Library of Congress photos/films), `www.europeana.eu` / `api.europeana.eu`, `wellcomecollection.org` /
`iiif.wellcomecollection.org` (medical history: tuberculosis, sanatoria), `huggingface.co` +
`cdn-lfs.huggingface.co` (more TTS voices, Whisper for subtitle QA), `freesound.org`.
Optional API keys as environment variables: `PEXELS_API_KEY`, `PIXABAY_API_KEY` (+ `pixabay.com`),
`EUROPEANA_API_KEY`, `ELEVENLABS_API_KEY` (+ `api.elevenlabs.io`) for a premium narrator voice.

## Sources for the script

G. H. Hardy, *Ramanujan: Twelve Lectures* (1940) and obituary notice (1921); Ramanujan's letters to Hardy
(16 Jan 1913; 12 Jan 1920) as published in Berndt & Rankin, *Ramanujan: Letters and Commentary* (1995);
Robert Kanigel, *The Man Who Knew Infinity* (1991). Disputed details are attributed in the narration.
