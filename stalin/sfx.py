"""Sound-effect library generated with the ElevenLabs sound-generation API.

Every visual event in the film has a sound (style guide section 8). The prompts
below are generated once and cached as 48 kHz WAV in build/stalin/sfx/.
"""
import json
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vox as V  # noqa: E402

OUT = os.path.join(V.BUILD, "sfx")

# name: (prompt, seconds, prompt_influence)
LIBRARY = {
    "whoosh": ("Quick airy whoosh swish, clean, short, for a motion graphics transition", 0.7, 0.6),
    "whoosh_big": ("Deep cinematic whoosh pass-by with low rumble tail", 1.4, 0.6),
    "pop": ("Soft paper cut-out pop, light cardboard flick, single short sound", 0.5, 0.7),
    "paper": ("Sheet of paper slapped down onto a wooden table, single paper slap", 0.6, 0.7),
    "paper_slide": ("Paper sliding quickly across a desk, short rustle", 0.8, 0.6),
    "stamp": ("Heavy rubber stamp slammed onto paper on a wooden desk, single hard thud", 0.8, 0.7),
    "shutter": ("Vintage film camera shutter click with flash pop", 0.6, 0.7),
    "typewriter": ("Old mechanical typewriter typing quickly, several keystrokes", 2.0, 0.6),
    "marker": ("Felt-tip marker squeak drawing a quick line on paper", 0.7, 0.7),
    "pen": ("Pen scratching across paper drawing a long line", 1.6, 0.6),
    "ping": ("Short soft metallic ping, map marker notification, clean", 0.6, 0.6),
    "tick": ("Single crisp mechanical counter tick click, very short", 0.5, 0.8),
    "hit": ("Punchy cinematic hit with short low boom, for a number reveal", 1.2, 0.6),
    "impact": ("Huge cinematic trailer impact boom with deep sub bass and reverb tail", 2.5, 0.6),
    "boom": ("Heavy metallic boom, like a giant steel door slam in a huge hall, long echo", 3.0, 0.6),
    "riser": ("Tense orchestral string riser building to a peak, cinematic, ends abruptly", 3.0, 0.5),
    "explosion": ("Large controlled demolition explosion of a stone monument, distant blast, rumble, "
                  "debris falling", 4.5, 0.5),
    "sub": ("Deep sub bass drop boom with long dark tail", 3.0, 0.6),
    "crowd": ("Large 1950s crowd cheering and applauding at an outdoor rally in a city square, "
              "distant brass band", 5.0, 0.4),
    "chisel": ("Stonemasons chiseling granite with hammers and chisels, several workers, echo", 3.0, 0.5),
    "projector": ("Old 16mm film projector running, mechanical rattle and whir", 4.0, 0.5),
    "metronome": ("Slow heavy mechanical metronome ticking, wooden, large and resonant", 4.0, 0.6),
    "wind": ("Cold wind blowing across an empty hilltop plain, desolate", 5.0, 0.4),
    "heartbeat": ("Slow deep heartbeat, cinematic, tense", 3.0, 0.6),
    "glitch": ("Short film burn flicker crackle and pop", 0.6, 0.6),
    "door": ("Heavy prison cell metal door slam with echo", 2.0, 0.6),
    "gas": ("Quiet hiss of gas escaping from a kitchen stove valve in a silent room", 3.0, 0.5),
    "applause": ("Polite applause from a small group indoors, 1950s ceremony", 3.0, 0.5),
    "radio": ("Old radio static tuning, short", 1.5, 0.6),
    "jackhammer": ("Pneumatic jackhammer breaking stone, short burst, outdoor", 1.6, 0.6),
    "cash": ("Old mechanical cash register ding with drawer opening", 1.0, 0.7),
    "scratch": ("Vinyl record scratch stop, comedic", 0.8, 0.7),
    "murmur": ("Crowd of people murmuring and chuckling, small town square", 2.0, 0.5),
    "wood_crack": ("Wooden beam cracking and breaking, short", 1.0, 0.6),
    "pour": ("Wet concrete pouring from a mixer chute", 2.0, 0.5),
    "drum": ("Single slow deep funeral drum hit with reverb", 2.0, 0.6),
    "hammer_wood": ("Carpenters hammering nails into wooden boards, a few hits", 1.8, 0.6),
    "rattle": ("Window glass panes rattling from a distant shockwave", 1.5, 0.6),
    "guitar": ("Short distorted electric guitar rock riff sting, 1990s", 1.5, 0.6),
    "helicopter": ("Helicopter rotor flying overhead, passing", 3.0, 0.5),
    "beep": ("Two short electronic warning beeps", 0.8, 0.7),
    "drip": ("Water drip echoing in an empty concrete basement", 1.5, 0.6),
}


def generate(name):
    prompt, secs, infl = LIBRARY[name]
    wav = os.path.join(OUT, f"{name}.wav")
    if os.path.exists(wav):
        return wav
    os.makedirs(OUT, exist_ok=True)
    mp3 = os.path.join(OUT, f"{name}.mp3")
    body = {"text": prompt, "duration_seconds": secs, "prompt_influence": infl}
    req = urllib.request.Request("https://api.elevenlabs.io/v1/sound-generation", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        open(mp3, "wb").write(r.read())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-ar", "48000", "-ac", "2", wav], check=True)
    return wav


def main(names=None):
    for n in names or LIBRARY:
        generate(n)
        print("  sfx", n, flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
