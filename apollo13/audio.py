"""Score, sound design and mix for "The 28-Volt Switch".

An original, synthesized score: curious and thoughtful (light plucks, a soft
piano motif, a gentle pulse), building into the explosion and again under the
verdict. Sound effects for paper, marker, pen, pops and whooshes. The music is
ducked well under the narration; finalize.py sets the loudness to -16 LUFS.
Writes build/apollo13[_cs]/mix.wav (and stems with STEMS=1).
"""
import importlib.util
import json
import os

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


timeline = _load("a13_timeline", os.path.join(HERE, "timeline.py"))
A = _load("synth", os.path.join(os.path.dirname(HERE), "src", "audio.py"))     # shared synth helpers

SR = A.SR
rng = np.random.default_rng(1970)
note, add = A.note, A.add
BPM = 92
BEAT = 60 / BPM
BAR = 4 * BEAT


def env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(t / max(attack, 1e-4), 1) * np.exp(-t * decay)


def mono_add(buf, sig, t):
    i = int(t * SR)
    if i < 0 or i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[:j - i]


# ------------------------------------------------------------------ sound effects
def sfx(kind):
    if kind == "paper":                    # a sheet sliding over paper
        n = int(0.55 * SR)
        x = A.bandpass(A.noise(0.55), 1200, 9000)
        am = 0.55 + 0.45 * (rng.random(n) > 0.82)
        am = A.lowpass(am, 60)
        return x * am * np.sin(np.linspace(0, np.pi, n)) ** 1.5 * 0.45
    if kind == "marker":                   # felt-tip squeak
        n = int(0.38 * SR)
        t = np.arange(n) / SR
        x = A.bandpass(A.noise(0.38), 2300, 3600) * (0.6 + 0.4 * np.sin(2 * np.pi * 23 * t))
        return x * np.sin(np.linspace(0, np.pi, n)) * 0.35
    if kind == "pen":                      # a quick scribble (circles, arrows)
        n = int(0.7 * SR)
        t = np.arange(n) / SR
        x = A.bandpass(A.noise(0.7), 1500, 5000) * (0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 7 * t)))
        return x * np.sin(np.linspace(0, np.pi, n)) * 0.28
    if kind == "pop":                      # a label popping in
        n = int(0.09 * SR)
        t = np.arange(n) / SR
        f = 950 * np.exp(-t * 14) + 420
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 38) * 0.45
    if kind == "whoosh":
        return A.whoosh(0.55, 0.6) * 0.55
    if kind == "click":                    # the thermostat snapping open
        out = np.zeros(int(0.12 * SR))
        for t0, g in ((0.0, 1.0), (0.045, 0.6)):
            c = A.bandpass(A.noise(0.012), 2000, 7000) * np.exp(-np.arange(576) / SR * 380)
            mono_add(out, c * g, t0)
        return out * 0.9
    if kind == "rise":
        return A.sine_sweep(220, 660, 0.7, 2.0) * 0.12 * np.sin(np.linspace(0, np.pi, int(0.7 * SR)))
    if kind == "thud":
        k = A.lowpass(A.kick(0.4), 400)
        return k * 0.8 + A.lowpass(A.noise(0.4), 500) * np.exp(-np.arange(len(k)) / SR * 14) * 0.25
    if kind == "tick":
        return A.bandpass(A.noise(0.02), 3000, 7000) * np.exp(-np.arange(960) / SR * 220) * 0.4
    if kind == "tick_run":                 # a clock racing through eight hours
        out = np.zeros(int(2.4 * SR))
        for k in range(16):
            c = A.bandpass(A.noise(0.02), 2500, 6500) * np.exp(-np.arange(960) / SR * 200)
            mono_add(out, c * (0.5 if k % 2 else 0.32), k * 0.15)
        return out
    if kind == "stamp":
        out = sfx("thud") * 0.9
        mono_add(out, sfx("paper")[: int(0.2 * SR)] * 0.6, 0.0)
        return out
    if kind == "rumble":                   # launch, heard from far away
        n = int(2.6 * SR)
        x = A.lowpass(A.noise(2.6), 140) * 2.2 + A.lowpass(A.noise(2.6), 900) * 0.2
        return x * np.minimum(np.linspace(0, 3, n), 1) * np.minimum(np.linspace(2.6, 0, n), 1) * 0.55
    if kind == "spark":
        n = int(0.45 * SR)
        x = np.zeros(n)
        for _ in range(26):
            i = rng.integers(0, n - 300)
            x[i:i + 300] += A.highpass(A.noise(300 / SR), 3000) * np.exp(-np.arange(300) / 40) * rng.uniform(0.3, 1)
        return x * 0.5
    if kind == "whoomp":                   # fire catching
        n = int(0.7 * SR)
        x = A.lowpass(A.noise(0.7), 900) * np.sin(np.linspace(0, np.pi, n)) ** 0.7
        return x * 0.6
    if kind in ("boom", "boom_soft"):
        dur = 3.0 if kind == "boom" else 1.6
        n = int(dur * SR)
        x = np.zeros(n)
        k = A.sine_sweep(80, 30, 1.4, 2.4)
        x[:len(k)] += k * 1.1
        x += A.lowpass(A.noise(dur), 260 if kind == "boom" else 180) * np.exp(-np.arange(n) / SR * 1.8) * 1.4
        return x * (0.9 if kind == "boom" else 0.45)
    return A.sfx(kind)


# ------------------------------------------------------------------ instruments
def piano(freq, dur=3.2, vel=1.0):
    t = np.arange(int(dur * SR)) / SR
    x = sum(np.sin(2 * np.pi * freq * h * t + h) * a * np.exp(-t * (1.0 + h * 0.8))
            for h, a in ((1, 1.0), (2, 0.42), (3, 0.16), (4, 0.06)))
    hammer = A.bandpass(A.noise(0.01), 1500, 6000) * np.exp(-np.arange(480) / SR * 600) * 0.05
    x[:len(hammer)] += hammer
    return x * np.minimum(t / 0.003, 1) * vel


def soft_pluck(freq, vel=1.0):
    x = A.pluck(freq, 1.1, 0.7)
    return A.lowpass(x, 3200) * vel


def pulse_hit():
    k = A.lowpass(A.kick(0.35), 220) * 0.9
    return k


# chord progression (bars): curious, a little unresolved
PROG = [
    ("D3", ["D4", "F#4", "A4", "E5"]),       # Dadd9
    ("B2", ["D4", "F#4", "A4", "B4"]),       # Bm7
    ("G2", ["D4", "F#4", "B4", "D5"]),       # Gmaj7
    ("A2", ["C#4", "E4", "A4", "B4"]),       # Asus2
]
DARK = [("D3", ["D4", "F4", "A4", "E5"]), ("Bb2", ["D4", "F4", "A4", "Bb4"]),
        ("G2", ["D4", "G4", "Bb4", "D5"]), ("A2", ["C#4", "E4", "G4", "A4"])]
MOTIF = ["A4", "F#4", "E4", "F#4", "D4", "E4", "B3", "D4"]


def score(T, scenes):
    st = {s["key"]: s for s in scenes}
    n = int(T * SR) + SR
    music = np.zeros((n, 2))

    def at(key, dt=0.0):
        return st[key]["start"] + dt

    t_blast = at("blast") + next(a for w, a, b in st["blast"]["words"]
                                 if w.lower().strip(",.") in ("blast", "výbuch"))
    t_end = at("end")
    t_verdict = at("verdict")

    # how busy each layer is over time (0..1)
    def curve(points):
        xs, ys = zip(*points)
        return lambda t: float(np.interp(t, xs, ys))
    pluck_lvl = curve([(0, 0.0), (1.0, 0.55), (at("title"), 0.7), (at("switch"), 0.6), (at("drop"), 0.8),
                       (at("weld"), 0.9), (t_blast - 2.5, 0.9), (t_blast - 0.2, 0.0), (at("lifeboat"), 0.0),
                       (at("lifeboat", 1.0), 0.5), (t_verdict, 0.55), (t_end - 2, 0.9), (t_end + 3, 0.6),
                       (T, 0.0)])
    pulse_lvl = curve([(0, 0), (at("switch"), 0.0), (at("volts"), 0.6), (at("weld"), 0.9), (t_blast - 0.6, 1.0),
                       (t_blast - 0.3, 0.0), (t_verdict + 3, 0.0), (t_verdict + 6, 0.7), (t_end + 0.5, 0.9),
                       (t_end + 2, 0.0), (T, 0.0)])
    dark = lambda t: at("weld") - 0.5 < t < at("lifeboat") + 0.5     # noqa: E731

    # plucked arpeggio on eighth notes
    k = 0
    t = 0.0
    while t < T:
        bar = int(t // BAR)
        prog = (DARK if dark(t) else PROG)[bar % 4]
        lvl = pluck_lvl(t)
        if lvl > 0.02:
            notes = prog[1]
            pat = [0, 2, 1, 3, 2, 1, 3, 0]
            f = note(notes[pat[k % 8]]) * (2 if k % 16 in (6, 14) else 1)
            vel = (0.9 if k % 2 == 0 else 0.6) * lvl * (1 + 0.15 * rng.standard_normal())
            add(music, soft_pluck(f, max(vel, 0)), t, 0.11, pan=0.35 * np.sin(k * 0.9))
        t += BEAT / 2
        k += 1
    # soft bass / piano chord on each bar
    for b in range(int(T // BAR) + 1):
        t0 = b * BAR
        root, chord = (DARK if dark(t0) else PROG)[b % 4]
        lvl = max(pluck_lvl(t0), 0.35 if t0 < t_end + 2 else 0)
        if t0 > t_blast - 0.5 and t0 < at("lifeboat"):
            continue
        add(music, piano(note(root) / 2, 3.5, 0.9) * lvl, t0, 0.16)
        for i, nm in enumerate(chord[:3]):
            add(music, piano(note(nm), 3.0, 0.45) * lvl, t0 + i * 0.012, 0.07, pan=(i - 1) * 0.3)
    # gentle pulse: soft kick on 1 and 3, shaker on the off-beats
    t = 0.0
    while t < T:
        lv = pulse_lvl(t)
        if lv > 0.02:
            beat = int(round(t / BEAT))
            if beat % 2 == 0:
                add(music, pulse_hit() * lv, t, 0.32)
            add(music, A.hat(0.04) * lv, t + BEAT / 2, 0.05, pan=0.25)
        t += BEAT
    # the piano motif: opening, title, and the ending
    for t0, transpose, vel in ((0.8, 1.0, 0.9), (at("title", 0.2), 1.0, 1.0), (at("lifeboat", 1.6), 1.0, 0.8),
                               (t_end + 0.3, 1.0, 1.0)):
        for i, nm in enumerate(MOTIF):
            add(music, piano(note(nm) * transpose, 2.4, vel), t0 + i * BEAT / 2 * 1.5, 0.11, pan=0.2 * np.sin(i))
    # pads: warmth under everything, swelling into the blast and the ending
    for key, chord, gain in (("hook", ["D3", "A3", "E4"], 0.5), ("switch", ["G2", "D3", "B3"], 0.45),
                             ("drop", ["B2", "F#3", "D4"], 0.45), ("weld", ["D3", "F3", "A3"], 0.5),
                             ("lifeboat", ["G2", "D3", "A3", "B3"], 0.55), ("verdict", ["D3", "A3", "F#4"], 0.45),
                             ("end", ["D3", "A3", "C#4", "E4"], 0.6)):
        s = st[key]
        dur = s["dur"] + (3.0 if key == "end" else 1.0)
        add(music, A.pad([note(x) for x in chord], dur, 1.5, 2.0, 700) * gain, s["start"], 0.5)
    # the build into the explosion: a riser and a low drone, then silence before the boom
    rise = A.sine_sweep(110, 440, 3.0, 0.0) * np.linspace(0, 1, int(3.0 * SR)) ** 2 * 0.08
    rise += A.bandpass(A.noise(3.0), 400, 4000) * np.linspace(0, 1, int(3.0 * SR)) ** 3 * 0.12
    add(music, rise, t_blast - 3.05, 1.0)
    drone_t = np.arange(int((t_blast - at("weld")) * SR)) / SR
    drone = (np.sin(2 * np.pi * note("D2") * drone_t) + 0.5 * np.sin(2 * np.pi * note("A2") * drone_t)) * 0.06
    drone *= np.minimum(drone_t / 3, 1)
    add(music, drone, at("weld"), 1.0)
    # after the blast: a long low pad that slowly opens up
    add(music, A.pad([note(x) for x in ("D2", "A2", "F3")], 6.0, 0.3, 4.0, 500) * 0.7, t_blast + 0.1, 0.6)
    return A.reverb(music, 2.6, 0.3)


def main():
    scenes = timeline.build()
    T = sum(s["dur"] for s in scenes)
    n = int(T * SR)
    voice = np.zeros((n + SR, 2))
    for s in scenes:
        if s["voice"] is None:
            continue
        v, sr = sf.read(os.path.join(timeline.ABUILD, "voice", f"{s['key']}.wav"))
        v = resample_poly(v, SR, sr)
        add(voice, np.stack([v, v], 1) * 0.707, s["start"] + s["voice"], 1.0)
    voice = A.reverb(voice, 0.4, 0.04)
    env_v = A.moving_average(np.abs(voice[:, 0]), int(0.2 * SR))
    env_v = np.clip(env_v / (np.percentile(env_v, 95) + 1e-9), 0, 1)
    duck = 1.0 - 0.55 * A.moving_average(env_v, int(0.5 * SR))
    music = score(T, scenes)[: len(voice)]
    fx = np.zeros_like(voice)
    with open(os.path.join(timeline.ABUILD, "sfx.json")) as fh:
        cues = json.load(fh)
    for items in cues.values():
        for t0, kind, gain in items:
            add(fx, sfx(kind), t0, gain * 0.55, pan=float(rng.uniform(-0.25, 0.25)))
    fx = A.reverb(fx, 1.2, 0.18)
    # keep the music clearly under the voice
    v_rms = np.sqrt(np.mean(voice[voice[:, 0] != 0] ** 2)) if np.any(voice) else 0.1
    m_rms = np.sqrt(np.mean(music ** 2)) + 1e-9
    music *= (v_rms * 0.30) / m_rms
    music *= duck[:, None]
    fx *= 0.36                      # effects sit ~8 dB under the voice
    if os.environ.get("STEMS"):
        os.makedirs(os.path.join(timeline.ABUILD, "stems"), exist_ok=True)
        for name, stem in (("voice", voice), ("music", music), ("fx", fx)):
            sf.write(os.path.join(timeline.ABUILD, "stems", f"{name}.wav"), stem[:n].astype(np.float32), SR)
    mix = (voice + music + fx)[:n]
    fade = int(1.5 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 1.5
    mix[: int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))[:, None]
    mix /= max(np.abs(mix).max(), 1e-9) / 0.89
    sf.write(os.path.join(timeline.ABUILD, "mix.wav"), mix.astype(np.float32), SR, subtype="PCM_24")
    print(f"mix.wav: {T:.2f}s, {sum(len(v) for v in cues.values())} sound cues")


if __name__ == "__main__":
    main()
