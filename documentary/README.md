# Uran pro Stalina / Uranium for Stalin

A ~10-minute documentary on the question *Jakou roli sehrál československý uran při vývoji první sovětské atomové bomby, a jaké byly podmínky v uranových dolech a lágrech?*

| Version | File | Narration |
|---|---|---|
| **Czech remake** (current pipeline) | built by `build.sh` → `build/Uran_pro_Stalina*.mp4` | ElevenLabs (your recording or the API). Until then, a temporary draft voice |
| English first cut | `Uranium_for_Stalin_web.mp4` (10:39) | Kokoro TTS, reproducible from commit `04bf1ff` |

## The Czech remake

**Script:** written to the FacelessOS 5.1 rules (Google Drive `FacelessOS5.1/skills`). The process followed them in order:

1. **Research brief:** every number traces to a source, and anything unverifiable was cut.
2. **Anchor:** the spoken register comes from the 0:00–2:00 transcript of the top-performing video in this lane, at 113 wpm.
3. **Hook and angle:**
   - The hook is under 100 words, with a jolt, a "Jenže" turn and a promise.
   - The angle is contrarian. The reactor for the first bomb ran from June 1948; the prisoner camps opened in 1949. So prisoners dug the uranium for every bomb *after* the first.
4. **Pacing:** a rehook every 30–45 s and one mid-video CTA. The film ends at the final payoff.
5. **Machine scan and greenlight audit (A–E):** looped until clean.

See [`SCRIPT_CS.md`](SCRIPT_CS.md) for the brief, sources, timestamped script with visual cues, and the Rotation Log.

**Picture:** rebuilt to stop the repetition:

- **Pacing:** a new visual every ~2.2 s (median), with cuts landing on spoken words.
- **Captions:** no more caption bar on every shot. A typewriter place/date tag appears only when the place or year changes. Big kinetic words carry the key numbers, and illustrative footage is marked *ilustrační záběr*.
- **Transitions:** hard cuts, whip pans, flash cuts, glitch, film burn and punch-in zooms. Impacts get a camera shake.
- **Set pieces:** launch countdown, the secret agreement typed out and stamped PŘÍSNĚ TAJNÉ, an evidence board with red string (Stalin, Beria, Kurchatov → URAN? → JÁCHYMOV), a Truman teletype, a dosimeter, a spa-vs-mine split screen, counters, maps and charts.
- **Archive look:** dust, scratches and flicker on old film.
- **Sound:** whooshes on whips, hits on stamps, Geiger crackle, risers, and war-drum percussion in the tense sections.

### Giving it your ElevenLabs voice

1. Open [`NARRACE_ElevenLabs.txt`](NARRACE_ElevenLabs.txt) and paste **part 1** and then **part 2** into ElevenLabs:
   - Use **Eleven Multilingual v2**, with a calm Czech male narrator.
   - Keep the `<break time="1.5s" />` tags. They aren't read aloud; they mark the cuts.
2. Send the two MP3s (attach them here, or commit them to `documentary/narration/` on this branch).
3. Build:
   ```bash
   NARRATION="narration/narace_1.mp3 narration/narace_2.mp3" ./build.sh
   ```
   `import_narration.py` splits the recording into the 42 script lines at the breaks; it was tested to an exact split. The edit re-times itself to your voice.

**ElevenLabs API instead:** add `ELEVENLABS_API_KEY` (and optionally `ELEVENLABS_VOICE_ID`) to the environment and run `./build.sh`. `tts_elevenlabs.py` generates every line with its neighbours as context.

### GPU rendering

`render.py --encoder auto` (the default) uses **NVIDIA NVENC** when a GPU is present and libx264 otherwise; `ENCODER=nvenc ./build.sh` requires the GPU. NVENC speeds up the encode; frame drawing is Python on the CPU, so more cores help most. Rendering is chunked and resumable: re-running only redraws chunks whose edit changed.

## Pipeline

| Step | File |
|---|---|
| Archive download (Wikimedia Commons, licences recorded) | `pipeline/fetch_assets.py`, `assets_manifest.json` |
| Narration | `narration_cs.json` → `import_narration.py` / `tts_elevenlabs.py` / `tts_draft.py` |
| Edit decision list | `pipeline/edl_cs.py` → `timeline.py` (word-anchored cuts, auto coverage, auto sound cues) |
| Picture | `render.py`, `anims.py`, `overlays.py`, `fx.py`, `common.py` |
| Score, SFX, mix (EBU R128, −16 LUFS) | `audio.py` |
| Subtitles, mux, <100 MB web copy | `subtitles.py`, `mux.py` |

Credits for every archive item (author and licence) are in [`CREDITS.md`](CREDITS.md) and in the film's end titles.

## Accuracy notes

- **Estimates:** prisoner numbers (60–70 thousand) and total uranium mined (~112,000 t over six decades) are historians' estimates and are presented as such.
- **The first bomb:** how much Jáchymov ore went into it is not documented. The film says what the dates allow:
  - Reactor A, which made its plutonium, started in **June 1948** and used, among other uranium, ~100 t captured in Germany.
  - The labour camps for prisoners at the uranium mines opened in **1949**.
- **Illustrative footage:** 1940s coal-mining film and 1950s Zwickau miner photos are labelled *ilustrační záběr*. U.S. test footage is labelled as such.
