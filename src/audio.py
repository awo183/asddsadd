"""Synthesize the score and sound effects, and mix them under the narration.

Everything here is generated from scratch with numpy/scipy: no samples.
Writes build/mix.wav (48 kHz stereo).
"""
import json
import os
import sys

import numpy as np
import soundfile as sf
from scipy.signal import butter, fftconvolve, resample_poly, sosfilt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline  # noqa: E402
from fx import BUILD  # noqa: E402

SR = 48000
rng = np.random.default_rng(2026)


def note(name):
    names = {"C": 0, "C#": 1, "D": 2, "Eb": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "Ab": 8, "A": 9,
             "Bb": 10, "B": 11}
    pitch, octave = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[pitch] + 12 * (octave + 1) - 69) / 12)


def env_adsr(n, a, r):
    e = np.ones(n)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    e[:na] = np.linspace(0, 1, na) ** 2
    e[n - nr:] *= np.linspace(1, 0, nr) ** 2
    return e


def lowpass(x, f, order=2):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x, axis=0)


def highpass(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x, axis=0)


def bandpass(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x, axis=0)


def add(buf, sig, t, gain=1.0, pan=0.0):
    """Mix mono or stereo sig into the stereo buffer at time t."""
    i = int(t * SR)
    if i >= len(buf):
        return
    if sig.ndim == 1:
        sig = np.stack([sig * (1 - pan) ** 0.5, sig * (1 + pan) ** 0.5], 1) / np.sqrt(2) * 1.414
    j = min(len(buf), i + len(sig))
    if i < 0:
        sig, i = sig[-i:], 0
    buf[i:j] += sig[: j - i] * gain


# ------------------------------------------------------------------ instruments
def saw_voice(freq, dur, detune=0.0):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f = freq * 2 ** (detune / 1200)
    out = np.zeros(n)
    for h in range(1, 14):
        if f * h > 9000:
            break
        out += np.sin(2 * np.pi * f * h * tt + h * 0.7) / h
    return out


def pad(freqs, dur, attack=1.2, release=1.8, cutoff=900):
    n = int(dur * SR)
    left, right = np.zeros(n), np.zeros(n)
    for f in freqs:
        left += saw_voice(f, dur, -6) + 0.6 * saw_voice(f, dur, 3)
        right += saw_voice(f, dur, 6) + 0.6 * saw_voice(f, dur, -3)
    st = np.stack([left, right], 1)
    st = lowpass(st, cutoff, 2)
    return st * env_adsr(n, attack, release)[:, None] / (len(freqs) * 2.5)


def pluck(freq, dur=0.9, bright=1.0):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    x = (np.sin(2 * np.pi * freq * tt) + 0.35 * bright * np.sin(4 * np.pi * freq * tt)
         + 0.12 * bright * np.sin(6 * np.pi * freq * tt))
    return x * np.exp(-tt * 5.5) * np.minimum(tt / 0.004, 1)


def kick(dur=0.45):
    tt = np.arange(int(dur * SR)) / SR
    f = 45 + 80 * np.exp(-tt * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9)


def noise(dur):
    return rng.standard_normal(int(dur * SR))


def hat(dur=0.05):
    x = highpass(noise(dur), 7000)
    return x * np.exp(-np.arange(len(x)) / SR * 70)


def sine_sweep(f0, f1, dur, decay=0.0):
    tt = np.arange(int(dur * SR)) / SR
    f = f0 * (f1 / f0) ** (tt / dur)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR)
    return x * (np.exp(-tt * decay) if decay else 1)


def whoosh(dur, rise=0.7):
    n = int(dur * SR)
    x = noise(dur)
    tt = np.linspace(0, 1, n)
    e = np.where(tt < rise, (tt / rise) ** 2, ((1 - tt) / (1 - rise)) ** 1.5)
    lo = bandpass(x, 300, 2500) * e
    return lowpass(lo, 3000)


# ------------------------------------------------------------------ sound cues
def sfx(kind):
    if kind in ("type", "key"):
        click = bandpass(noise(0.012), 1800, 5000) * np.exp(-np.arange(576) / SR * 400)
        thunk = sine_sweep(180, 90, 0.03, 60) * 0.5
        out = np.zeros(1440)
        out[: len(click)] += click * (1.0 if kind == "type" else 0.45)
        if kind == "type":
            out[: len(thunk)] += thunk
        return out * rng.uniform(0.7, 1.0)
    if kind == "carriage":
        tt = np.arange(int(0.8 * SR)) / SR
        return (np.sin(2 * np.pi * 2093 * tt) + 0.4 * np.sin(2 * np.pi * 4186 * tt)) * \
            np.exp(-tt * 5) * 0.25
    if kind == "stamp":
        out = kick(0.3) * 0.9
        out[:7200] += lowpass(noise(0.15), 1200) * np.exp(-np.arange(7200) / SR * 25) * 0.6
        return out
    if kind == "count":
        out = np.zeros(int(1.6 * SR))
        t = 0.0
        while t < 1.5:
            add_mono(out, sfx("tick") * 0.6, t)
            t += 0.03 + 0.09 * (t / 1.5) ** 2
        return out
    if kind == "tick":
        return bandpass(noise(0.006), 3000, 9000) * 0.6
    if kind in ("blip", "blip_hi"):
        f0 = 1500 if kind == "blip" else 2100
        return sine_sweep(f0, f0 * 0.8, 0.09, 30) * 0.5
    if kind == "blip_many":
        out = np.zeros(int(1.0 * SR))
        for k in range(14):
            add_mono(out, sine_sweep(1300 + 900 * rng.random(), 1100, 0.07, 35) * 0.3,
                     rng.random() * 0.8)
        return out
    if kind == "whoosh":
        return whoosh(0.9)
    if kind == "whoosh_long":
        return whoosh(3.0, 0.85) * 0.8
    if kind == "flip":
        return whoosh(0.35, 0.5) * 0.9
    if kind == "hit":
        tail = lowpass(noise(2.5), 400) * np.exp(-np.arange(int(2.5 * SR)) / SR * 2.2) * 0.35
        x = np.zeros(int(2.5 * SR))
        k = kick(1.2) * 1.2
        x[: len(k)] += k
        return x + tail
    if kind == "cut":
        return highpass(noise(0.05), 2000) * np.exp(-np.arange(2400) / SR * 60) * 0.35
    if kind == "zoom":
        n = int(3.0 * SR)
        tt = np.arange(n) / SR
        x = sine_sweep(110, 880, 3.0) * 0.25 + bandpass(noise(3.0), 400, 4000) * 0.4
        return x * np.minimum(tt / 2.5, 1) ** 2 * np.minimum((3.0 - tt) / 0.15, 1)
    if kind == "scan":
        tt = np.arange(int(0.7 * SR)) / SR
        f = 300 + 2400 * tt / 0.7
        x = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR))
        return lowpass(x, 3500) * np.sin(np.pi * tt / 0.7) * 0.18
    if kind == "ticks":
        out = np.zeros(int(0.9 * SR))
        for k in range(18):
            add_mono(out, sfx("tick") * 0.5, k * 0.04 + rng.random() * 0.02)
        return out
    if kind == "confirm":
        a, b = sine_sweep(880, 880, 0.1, 18), sine_sweep(1320, 1320, 0.22, 14)
        out = np.zeros(int(0.35 * SR))
        out[: len(a)] += a
        out[int(0.1 * SR): int(0.1 * SR) + len(b)] += b
        return out * 0.4
    if kind == "error":
        tt = np.arange(int(0.5 * SR)) / SR
        f = np.where(tt < 0.22, 260, 196)
        x = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR))
        return lowpass(x, 1800) * np.exp(-tt * 3) * 0.3
    if kind == "glitch":
        x = noise(0.3)
        x = np.repeat(x[::40], 40)[: len(x)]
        return bandpass(x, 200, 6000) * 0.45
    if kind == "bar":
        return sine_sweep(330, 660, 0.45, 5) * 0.22
    if kind == "sweep":
        return sine_sweep(400, 1200, 0.8, 2) * 0.22
    if kind == "alarm":
        out = np.zeros(int(1.9 * SR))
        for k in range(3):
            for j, f in enumerate((988, 784)):
                tt = np.arange(int(0.28 * SR)) / SR
                x = lowpass(np.sign(np.sin(2 * np.pi * f * tt)), 2500) * np.minimum(tt / 0.01, 1)
                add_mono(out, x * 0.22 * np.minimum((0.28 - tt) / 0.03, 1), k * 0.62 + j * 0.31)
        return out
    raise KeyError(kind)


def add_mono(buf, sig, t):
    i = int(t * SR)
    j = min(len(buf), i + len(sig))
    if i < len(buf):
        buf[i:j] += sig[: j - i]


def reverb(x, seconds=2.4, wet=0.3):
    n = int(seconds * SR)
    tt = np.arange(n) / SR
    ir = np.stack([rng.standard_normal(n), rng.standard_normal(n)], 1) * np.exp(-tt * 3.2)[:, None]
    ir = lowpass(ir, 5000)
    ir /= np.sqrt((ir ** 2).sum(0))
    out = np.stack([fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], 1)
    return x * (1 - wet) + out * wet * 1.6


# ------------------------------------------------------------------ the score
PROG_A = [["D2", "D3", "A3", "F4", "E4"], ["Bb1", "Bb2", "F3", "D4", "A4"],
          ["F2", "C3", "A3", "G4"], ["C2", "G2", "E3", "D4"]]
PROG_B = [["G1", "G2", "D3", "Bb3", "F4"], ["D2", "A2", "F3", "E4"],
          ["Bb1", "F2", "D3", "C4"], ["A1", "E2", "C#3", "E4"]]
ARP = {0: ["D4", "F4", "A4", "E5"], 1: ["D4", "F4", "Bb4", "A4"], 2: ["C4", "F4", "A4", "G4"],
       3: ["C4", "E4", "G4", "D5"]}


def score(T, scenes):
    st = {s["key"]: s for s in scenes}
    music = np.zeros((int(T * SR) + SR, 2))
    bpm = 96
    beat = 60 / bpm

    def at(key, dt=0.0):
        return st[key]["start"] + dt

    # drone through the whole film, dark at both ends
    n = len(music)
    tt = np.arange(n) / SR
    drone = (np.sin(2 * np.pi * note("D2") * tt) + 0.5 * np.sin(2 * np.pi * note("A2") * tt)) * \
        (0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * tt))
    air = lowpass(bandpass(rng.standard_normal(n), 400, 3000), 2500) * 0.25
    lvl = np.interp(tt, [0, 2, at("title"), at("summer_1966"), at("pixels"), at("watch"),
                         at("watch", 4), at("end", 3), T],
                    [0, 0.6, 0.7, 0.35, 0.25, 0.35, 0.7, 0.5, 0])
    music += np.stack([drone + air, drone * 0.97 + np.roll(air, 999)], 1) * (lvl * 0.16)[:, None]

    # chord pads, 2 bars per chord
    def chords(t0, t1, prog, gain, cutoff=900):
        t, k = t0, 0
        bar = 4 * beat
        while t < t1 - 0.5:
            dur = min(2 * bar, t1 - t) + 1.5
            add(music, pad([note(x) for x in prog[k % len(prog)]], dur, cutoff=cutoff), t, gain)
            t += 2 * bar
            k += 1

    chords(at("title", 0.5), at("pixels"), PROG_A, 0.55, 700)
    chords(at("pixels"), at("learning"), PROG_A, 0.5, 900)
    chords(at("learning"), at("watch"), PROG_A, 0.6, 1300)
    chords(at("watch"), at("end"), PROG_B, 0.5, 600)
    add(music, pad([note(x) for x in ("D2", "A2", "F3", "E4", "A4")], 6.5, 0.4, 4.0, 900),
        at("end", 0.1), 0.6)

    # pulse arpeggio — enters with the pixels, builds through ImageNet and today
    def arps(t0, t1, gain0, gain1, prog_offset=0, eighths=True):
        step = beat / 2 if eighths else beat
        t, i = t0, 0
        while t < t1:
            u = (t - t0) / max(t1 - t0, 1e-6)
            chord = (int((t - at("title", 0.5)) / (8 * beat)) + prog_offset) % 4
            f = note(ARP[chord][i % 4])
            add(music, pluck(f * (2 if i % 8 == 7 else 1), 0.8, 0.6 + 0.6 * u),
                t, lerp(gain0, gain1, u), pan=0.35 * np.sin(i * 1.3))
            t += step
            i += 1

    arps(at("pixels", 2.9), at("rules", 12.6), 0.05, 0.11)
    arps(at("learning", 2.6), at("imagenet"), 0.06, 0.12)
    arps(at("imagenet"), at("today"), 0.1, 0.16)
    arps(at("today"), at("watch"), 0.15, 0.16)

    # beat: soft kick + hats from ImageNet's chart to the end of "today"
    t = at("imagenet", 6.8)
    while t < at("watch") - 0.1:
        add(music, kick(), t, 0.32)
        add(music, hat(), t + beat / 2, 0.1, pan=0.3)
        t += beat
    # heartbeat under "watch"
    t = at("watch", 0.4)
    while t < at("watch", 11.0):
        add(music, kick(0.5), t, 0.22)
        add(music, kick(0.5), t + 0.28, 0.14)
        t += 1.25

    # title riser
    r_t = at("title", 0.75)
    add(music, whoosh(2.5, 0.98) * 0.6, r_t - 2.45, 0.6)
    return reverb(music, 2.6, 0.32)


def lerp(a, b, u):
    return a + (b - a) * u


def moving_average(x, win):
    c = np.cumsum(np.concatenate([np.zeros(win // 2 + 1), x, np.zeros(win)]))
    return (c[win:win + len(x)] - c[:len(x)]) / win


def main():
    scenes = timeline.build()
    T = sum(s["dur"] for s in scenes)
    n = int(T * SR)
    # narration
    voice = np.zeros((n + SR, 2))
    for s in scenes:
        if s["voice"] is None:
            continue
        v, sr = sf.read(os.path.join(BUILD, "voice", f"{s['key']}.wav"))
        v = resample_poly(v, SR, sr)
        add(voice, np.stack([v, v], 1), s["start"] + s["voice"], 1.0)
    voice = reverb(voice, 0.6, 0.06)
    # duck the music under the voice
    env = moving_average(np.abs(voice[:, 0]), int(0.25 * SR))
    env = np.clip(env / (env.max() * 0.25), 0, 1)
    env = moving_average(env, int(0.4 * SR))
    duck = 1.0 - 0.65 * env
    music = score(T, scenes)[: len(voice)]
    # sound effects
    fx = np.zeros_like(voice)
    with open(os.path.join(BUILD, "sfx.json")) as f:
        cues = json.load(f)
    for key, items in cues.items():
        for t, kind, gain in items:
            add(fx, sfx(kind), t, gain * 0.5, pan=float(rng.uniform(-0.25, 0.25)))
    fx = reverb(fx, 1.2, 0.18)
    music = music * duck[:, None] * 0.25
    fx = fx * 0.4
    if os.environ.get("STEMS"):
        os.makedirs(os.path.join(BUILD, "stems"), exist_ok=True)
        for name, stem in (("voice", voice), ("music", music), ("fx", fx)):
            sf.write(os.path.join(BUILD, "stems", f"{name}.wav"), stem[:n].astype(np.float32), SR)
    mix = voice + music + fx
    mix = mix[:n]
    fade = int(0.05 * SR)
    mix[:fade] *= np.linspace(0, 1, fade)[:, None]
    mix /= max(np.abs(mix).max(), 1e-9) / 0.89
    sf.write(os.path.join(BUILD, "mix.wav"), mix.astype(np.float32), SR, subtype="PCM_24")
    print(f"mix.wav: {T:.2f}s, {sum(len(v) for v in cues.values())} sound cues")


if __name__ == "__main__":
    main()
