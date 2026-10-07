"""Score: one ElevenLabs Music cue per chapter mood (instrumental), cached in
build/stalin/music/. plan.MUSIC places them on the timeline."""
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vox as V  # noqa: E402

OUT = os.path.join(V.BUILD, "music")
CUES = {
    "hook": ("Tense dark cinematic documentary underscore, ticking clock pulse, low staccato strings, deep drums "
             "building tension, 1950s cold war mood, instrumental, no vocals", 40),
    "order": ("Investigative documentary underscore, mid-tempo pizzicato strings and light percussion, curious and "
              "slightly ironic, Eastern European flavour, clarinet motif, instrumental, no vocals", 100),
    "sculptor": ("Melancholic slow solo piano with soft sustained strings, sad and intimate, documentary, "
                 "instrumental, no vocals", 50),
    "blast": ("Dark tension building cinematic score, pulsing low brass and percussion, rising strings, ominous, "
              "documentary climax, instrumental, no vocals", 66),
    "bill": ("Reflective modern ambient documentary score, steady metronome-like tick, warm synth pad and piano, "
             "thoughtful, slowly resolving to a soft ending, instrumental, no vocals", 75),
}


def generate(name):
    prompt, secs = CUES[name]
    path = os.path.join(OUT, f"{name}.mp3")
    if os.path.exists(path):
        return path
    os.makedirs(OUT, exist_ok=True)
    body = {"prompt": prompt, "music_length_ms": int(secs * 1000)}
    req = urllib.request.Request("https://api.elevenlabs.io/v1/music", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        open(path, "wb").write(r.read())
    return path


if __name__ == "__main__":
    for n in sys.argv[1:] or CUES:
        print("  music", n, generate(n), flush=True)
