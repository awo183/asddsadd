"""Score, sound design and mix for "The Calmest Man on the Plane".

Dark true-crime palette: low drones, a heartbeat, a ticking clock, rain,
impacts on every reveal, and a sparse piano motif. All synthesized here.
Writes build/cooper/mix.wav (+ stems with STEMS=1).
"""
import json
import os

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


timeline = _load("cooper_timeline", os.path.join(HERE, "timeline.py"))
A = _load("synth", os.path.join(os.path.dirname(HERE), "src", "audio.py"))  # first film's synths

SR = A.SR
rng = np.random.default_rng(1971)
note, add, add_mono = A.note, A.add, A.add_mono


def tone_env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(t / max(attack, 1e-4), 1) * np.exp(-t * decay)


def sfx(kind):
    if kind == "thud":
        k = A.kick(0.6) * 1.1
        return k + A.lowpass(A.noise(0.6), 300) * np.exp(-np.arange(len(k)) / SR * 9) * 0.4
    if kind == "boom":
        n = int(3.0 * SR)
        x = np.zeros(n)
        k = A.sine_sweep(90, 32, 1.6, 2.2) * 1.2
        x[: len(k)] += k
        x += A.lowpass(A.noise(3.0), 220) * np.exp(-np.arange(n) / SR * 1.6) * 0.8
        return x
    if kind == "x":
        return A.highpass(A.noise(0.08), 1500) * np.exp(-np.arange(3840) / SR * 50) * 0.5 + \
            A.sine_sweep(320, 160, 0.08, 30) * 0.3
    if kind == "shutter":
        out = np.zeros(int(0.25 * SR))
        for t0 in (0.0, 0.07):
            c = A.bandpass(A.noise(0.03), 1500, 7000) * np.exp(-np.arange(1440) / SR * 140)
            add_mono(out, c * 0.8, t0)
        return out
    if kind == "paper":
        n = int(0.6 * SR)
        e = np.sin(np.linspace(0, np.pi, n)) ** 2
        return A.bandpass(A.noise(0.6), 2000, 9000) * e * 0.35 * (0.6 + 0.4 * rng.random(n))
    if kind == "type":
        return A.sfx("type")
    if kind == "type_heavy":       # a hard keystroke on a big headline
        out = np.zeros(int(0.12 * SR))
        add_mono(out, A.sfx("type") * 1.2, 0.0)
        add_mono(out, A.lowpass(A.noise(0.04), 900) * np.exp(-np.arange(1920) / SR * 90) * 0.5, 0.0)
        return out
    if kind == "carriage_soft":    # end-of-line bell, quiet
        t = np.arange(int(0.6 * SR)) / SR
        return np.sin(2 * np.pi * 2093 * t) * np.exp(-t * 7) * 0.18
    if kind == "type_burst":
        out = np.zeros(int(0.5 * SR))
        for k in range(8):
            add_mono(out, A.sfx("type"), k * 0.05 + rng.random() * 0.015)
        return out
    if kind == "marker":
        n = int(0.45 * SR)
        return A.bandpass(A.noise(0.45), 800, 4000) * np.sin(np.linspace(0, np.pi, n)) * 0.3
    if kind == "riser":
        n = int(1.2 * SR)
        x = A.sine_sweep(80, 400, 1.2) * 0.3 + A.bandpass(A.noise(1.2), 300, 3000) * 0.4
        return x * np.linspace(0, 1, n) ** 2
    if kind == "beep":
        return A.sine_sweep(1200, 1200, 0.07, 25) * 0.35
    if kind == "static":
        n = int(1.0 * SR)
        x = A.bandpass(A.noise(1.0), 500, 3500) * (0.5 + 0.5 * (rng.random(n) > 0.6))
        return x * np.minimum(np.linspace(0, 6, n), 1) * np.linspace(1, 0, n) * 0.35
    if kind == "hydraulic":
        n = int(1.4 * SR)
        x = A.lowpass(A.noise(1.4), 600) * 0.5 + A.sine_sweep(110, 70, 1.4) * 0.25
        return x * np.sin(np.linspace(0, np.pi, n))
    if kind == "clock":
        out = np.zeros(int(3.2 * SR))
        for k in range(7):
            c = A.bandpass(A.noise(0.02), 2500, 6000) * np.exp(-np.arange(960) / SR * 200)
            add_mono(out, c * (0.7 if k % 2 else 0.45), k * 0.5)
        return out
    if kind == "rain":
        n = int(4.0 * SR)
        x = A.lowpass(A.highpass(A.noise(4.0), 400), 6000) * 0.25
        drops = (rng.random(n) > 0.9993) * rng.random(n)
        x += A.bandpass(drops, 1500, 6000) * 4
        e = np.minimum(np.linspace(0, 4, n), 1) * np.minimum(np.linspace(4, 0, n), 1)
        return x * e
    if kind == "ping":
        t = np.arange(int(1.2 * SR)) / SR
        return np.sin(2 * np.pi * 1318 * t) * np.exp(-t * 4) * 0.3
    if kind == "drone_end":
        n = int(7.0 * SR)
        t = np.arange(n) / SR
        x = (np.sin(2 * np.pi * note("D2") * t) + 0.6 * np.sin(2 * np.pi * note("A2") * t)
             + 0.25 * np.sin(2 * np.pi * note("Eb3") * t))
        return A.lowpass(x, 500) * np.minimum(t / 1.5, 1) * np.minimum((7 - t) / 3, 1) * 0.5
    return A.sfx(kind)


def piano(freq, dur=3.0):
    t = np.arange(int(dur * SR)) / SR
    x = sum(np.sin(2 * np.pi * freq * h * t) * a * np.exp(-t * (1.2 + h * 0.9))
            for h, a in ((1, 1.0), (2, 0.45), (3, 0.2), (4, 0.08)))
    return x * np.minimum(t / 0.004, 1)


def heartbeat():
    out = np.zeros(int(0.9 * SR))
    add_mono(out, A.kick(0.4) * 0.9, 0.0)
    add_mono(out, A.kick(0.4) * 0.6, 0.24)
    return A.lowpass(out, 180)


def score(T, scenes):
    st = {s["key"]: s for s in scenes}
    n = int(T * SR) + SR
    music = np.zeros((n, 2))
    t = np.arange(n) / SR

    def at(key, dt=0.0):
        return st[key]["start"] + dt

    # bed: low drone + air, swelling through the story
    drone = (np.sin(2 * np.pi * note("D1") * t) + 0.8 * np.sin(2 * np.pi * note("D2") * t)
             + 0.35 * np.sin(2 * np.pi * note("A2") * t)) * (0.75 + 0.25 * np.sin(2 * np.pi * 0.05 * t))
    air = A.lowpass(A.bandpass(rng.standard_normal(n), 200, 2400), 1800) * 0.35
    lvl = np.interp(t, [0, 1.5, at("title"), at("note"), at("demands"), at("orders"), at("jump"),
                        at("profile"), at("money"), at("end"), T],
                    [0, 0.7, 0.9, 0.55, 0.7, 0.8, 1.0, 0.75, 0.7, 0.6, 0])
    music += np.stack([drone + air, drone + np.roll(air, 777)], 1) * (lvl * 0.14)[:, None]
    # dissonant shimmer that creeps in under the analysis sections
    shimmer = (np.sin(2 * np.pi * note("Eb5") * t) + np.sin(2 * np.pi * note("D5") * t)) * 0.04
    sh_lvl = np.interp(t, [0, at("demands"), at("demands", 4), at("orders"), at("profile"),
                           at("profile", 3), at("money"), T], [0, 0, 1, 0.3, 0.3, 1, 0.4, 0])
    music += np.stack([shimmer, shimmer], 1) * sh_lvl[:, None]
    # piano motif: hook and ending
    motif = ["D4", "F4", "A4", "C#5", "D5", "A4", "F4", "E4"]
    for i, nm in enumerate(motif):
        add(music, piano(note(nm)), 0.6 + i * 1.45, 0.16, pan=0.3 * np.sin(i))
    for i, nm in enumerate(motif[:6]):
        add(music, piano(note(nm) / 2), at("money", st["money"]["sentences"][3]) + i * 1.3, 0.14,
            pan=-0.3 * np.sin(i))
    # heartbeat in the hook and around the jump
    for t0, t1, period in ((0.6, at("title") - 0.3, 1.05), (at("jump"), at("profile"), 0.8)):
        x = t0
        while x < t1:
            add(music, heartbeat(), x, 0.3)
            x += period
    # ticking clock under the demands
    x = at("demands", 0.3)
    while x < at("orders"):
        add(music, sfx("clock")[: int(0.05 * SR)], x, 0.5, pan=0.2)
        x += 0.5
    # low pulse under the orders and profile
    for sec in ("orders", "profile"):
        x = at(sec)
        while x < at(sec) + st[sec]["dur"] - 0.3:
            k = A.lowpass(A.saw_voice(note("D2"), 0.35), 400) * tone_env(int(0.35 * SR), 0.01, 7)
            add(music, k, x, 0.22)
            x += 0.5
    # long pads for weight
    add(music, A.pad([note(x) for x in ("D2", "A2", "F3")], at("title") + 1.0, 2.0, 2.0, 500), 0, 0.5)
    add(music, A.pad([note(x) for x in ("Bb1", "F2", "D3")], st["jump"]["dur"] + 2, 1.0, 2.0, 500),
        at("jump"), 0.6)
    add(music, A.pad([note(x) for x in ("D2", "A2", "F3", "E4")], st["money"]["dur"] + 4, 2.0,
                     4.0, 600), at("money"), 0.45)
    return A.reverb(music, 3.0, 0.38)


def main():
    scenes = timeline.build()
    T = sum(s["dur"] for s in scenes)
    n = int(T * SR)
    voice = np.zeros((n + SR, 2))
    for s in scenes:
        if s["voice"] is None:
            continue
        v, sr = sf.read(os.path.join(timeline.CBUILD, "voice", f"{s['key']}.wav"))
        v = resample_poly(v, SR, sr)
        add(voice, np.stack([v, v], 1), s["start"] + s["voice"], 1.0)
    # a touch of low-end warmth and room on the narrator
    voice = A.reverb(voice, 0.5, 0.05)
    env = A.moving_average(np.abs(voice[:, 0]), int(0.25 * SR))
    env = np.clip(env / (env.max() * 0.25), 0, 1)
    duck = 1.0 - 0.6 * A.moving_average(env, int(0.4 * SR))
    music = score(T, scenes)[: len(voice)]
    fx = np.zeros_like(voice)
    with open(os.path.join(timeline.CBUILD, "sfx.json")) as fh:
        cues = json.load(fh)
    for items in cues.values():
        for t0, kind, gain in items:
            add(fx, sfx(kind), t0, gain * 0.5, pan=float(rng.uniform(-0.2, 0.2)))
    fx = A.reverb(fx, 1.6, 0.22)
    music = music * duck[:, None] * 0.26
    fx = fx * 0.45
    if os.environ.get("STEMS"):
        os.makedirs(os.path.join(timeline.CBUILD, "stems"), exist_ok=True)
        for name, stem in (("voice", voice), ("music", music), ("fx", fx)):
            sf.write(os.path.join(timeline.CBUILD, "stems", f"{name}.wav"),
                     stem[:n].astype(np.float32), SR)
    mix = (voice + music + fx)[:n]
    mix[: int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))[:, None]
    mix /= max(np.abs(mix).max(), 1e-9) / 0.89
    sf.write(os.path.join(timeline.CBUILD, "mix.wav"), mix.astype(np.float32), SR, subtype="PCM_24")
    print(f"mix.wav: {T:.2f}s, {sum(len(v) for v in cues.values())} sound cues")


if __name__ == "__main__":
    main()
