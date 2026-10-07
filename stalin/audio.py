"""Mix narration, sound effects and music; the music ducks under the voice.

Reads build/stalin/voice/manifest.json, build/stalin/sfx_events.json and the
music cues in plan.MUSIC. Writes build/stalin/mix.wav and stems/.
"""
import json
import os
import subprocess
import sys

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vox as V  # noqa: E402

SR = 48000
GAIN = {  # per-effect level (linear) so whooshes sit under the voice and booms land
    "whoosh": 0.28, "whoosh_big": 0.4, "pop": 0.3, "paper": 0.4, "paper_slide": 0.35, "stamp": 0.55,
    "shutter": 0.4, "typewriter": 0.3, "marker": 0.32, "pen": 0.3, "ping": 0.3, "tick": 0.16,
    "hit": 0.45, "impact": 0.6, "boom": 0.55, "riser": 0.35, "explosion": 0.8, "sub": 0.55, "crowd": 0.3,
    "chisel": 0.35, "projector": 0.2, "metronome": 0.45, "wind": 0.3, "heartbeat": 0.45, "glitch": 0.3,
    "door": 0.5, "gas": 0.3, "applause": 0.3, "radio": 0.3, "jackhammer": 0.4, "cash": 0.45, "scratch": 0.4,
    "murmur": 0.35, "wood_crack": 0.4, "pour": 0.3, "drum": 0.6, "hammer_wood": 0.4, "rattle": 0.4,
    "guitar": 0.45, "helicopter": 0.35, "beep": 0.35, "drip": 0.45,
}


def decode(path):
    """Any audio file -> float32 stereo at 48 kHz."""
    tmp = os.path.join(V.BUILD, "tmp_decode.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-ar", str(SR), "-ac", "2", "-f", "wav", tmp],
                   check=True)
    x, _ = sf.read(tmp, dtype="float32")
    os.remove(tmp)
    return x


_CACHE = {}


def sfx(name):
    if name not in _CACHE:
        _CACHE[name] = decode(os.path.join(V.BUILD, "sfx", f"{name}.wav"))
    return _CACHE[name]


def add(track, x, t, gain=1.0, fade_out=0.0):
    i = int(t * SR)
    if i >= len(track) or i + len(x) <= 0:
        return
    if i < 0:
        x, i = x[-i:], 0
    n = min(len(x), len(track) - i)
    seg = x[:n] * gain
    if fade_out:
        k = min(int(fade_out * SR), n)
        seg[n - k:] *= np.linspace(1, 0, k)[:, None]
    track[i:i + n] += seg


def envelope(x, attack=0.03, release=0.45):
    """Smoothed amplitude envelope of a mono signal (for ducking)."""
    hop = 480
    m = np.sqrt(np.mean(x[: len(x) // hop * hop].reshape(-1, hop) ** 2, axis=1))
    env = np.zeros_like(m)
    a, r = np.exp(-hop / (attack * SR)), np.exp(-hop / (release * SR))
    e = 0.0
    for k, v in enumerate(m):
        e = a * e + (1 - a) * v if v > e else r * e + (1 - r) * v
        env[k] = e
    return np.repeat(env, hop)


def music_track(n, cues):
    out = np.zeros((n, 2), np.float32)
    for c in cues:
        x = decode(c["file"])
        if c.get("offset"):
            x = x[int(c["offset"] * SR):]
        length = int((c["end"] - c["start"]) * SR)
        if len(x) < length and c.get("loop", True):
            x = np.concatenate([x] * (length // len(x) + 1))
        x = x[:length].copy()
        fi, fo = int(c.get("fade_in", 1.0) * SR), int(c.get("fade_out", 1.5) * SR)
        if fi:
            x[:fi] *= np.linspace(0, 1, min(fi, len(x)))[:, None]
        if fo:
            k = min(fo, len(x))
            x[len(x) - k:] *= np.linspace(1, 0, k)[:, None]
        add(out, x, c["start"], 10 ** (c.get("db", 0) / 20))
    return out


def main():
    import plan
    tl = plan.timeline_info()
    n = int((tl["duration"] + 1.0) * SR)
    voice = np.zeros((n, 2), np.float32)
    for blk in tl["voice"]:
        add(voice, decode(blk["mp3"]) * 1.0, blk["start"])
    for clip in tl.get("archival_audio", []):
        add(voice, decode(clip["file"])[int(clip.get("in", 0) * SR):int(clip.get("out", 999) * SR)],
            clip["start"], 10 ** (clip.get("db", 0) / 20), 0.2)
    fx = np.zeros((n, 2), np.float32)
    events = json.load(open(os.path.join(V.BUILD, "sfx_events.json"))) + [list(e) for e in tl.get("sfx", [])]
    last = {}
    for t, name, gain in sorted(events):
        if t - last.get(name, -9) < 0.06:      # identical sounds on the same frame: play once
            continue
        last[name] = t
        add(fx, sfx(name), t, GAIN.get(name, 0.5) * gain)
    music = music_track(n, plan.MUSIC)
    env = envelope(voice.mean(1))[:n]
    env = np.pad(env, (0, n - len(env)))
    duck_db = -11.0 * np.clip(env / 0.05, 0, 1)
    for t0, t1, db in tl.get("music_holes", []):      # extra dips (silence before the climax etc.)
        i0, i1 = int(t0 * SR), int(t1 * SR)
        duck_db[i0:i1] = np.minimum(duck_db[i0:i1], db)
    music *= (10 ** (duck_db / 20))[:, None]
    mix = voice * 1.0 + fx * 0.7 + music * 0.7
    peak = np.abs(mix).max()
    if peak > 0.98:
        mix *= 0.98 / peak
    os.makedirs(os.path.join(V.BUILD, "stems"), exist_ok=True)
    sf.write(os.path.join(V.BUILD, "mix.wav"), mix, SR, subtype="PCM_24")
    sf.write(os.path.join(V.BUILD, "stems", "voice.wav"), voice, SR, subtype="PCM_24")
    sf.write(os.path.join(V.BUILD, "stems", "music.wav"), music * 0.7, SR, subtype="PCM_24")
    sf.write(os.path.join(V.BUILD, "stems", "sfx.wav"), fx * 0.7, SR, subtype="PCM_24")
    print("wrote mix.wav", f"{n / SR:.1f}s")


if __name__ == "__main__":
    main()
