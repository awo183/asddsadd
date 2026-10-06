"""Score, sound design and mix for "Twenty Boats".

An original, synthesized explainer score: a curious plucked ostinato over warm
pads (D dorian), which builds at the collision and the "too late" beat, drops
away for the last line, and resolves on the end card. Paper slides, pops,
marker squeaks, counters, whooshes and a Morse "CQD" are synthesized too.
Music ducks under the voice. The mix is mastered to -16 LUFS with one fixed
gain and a gentle look-ahead peak limiter (no dynamic loudness processing).
Writes build/titanic/<lang>/mix.wav, voice_master.wav (+ stems).
"""
import json
import os
import sys

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import timeline  # noqa: E402
from common import load  # noqa: E402

A = load("synth", os.path.join("..", "src", "audio.py"))     # the first film's synth helpers
SR = A.SR
rng = np.random.default_rng(1912)
note, add, add_mono = A.note, A.add, A.add_mono
BPM = 92
BEAT = 60 / BPM


# ------------------------------------------------------------------ instruments
def env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(t / max(attack, 1e-4), 1) * np.exp(-t * decay)


def marimba(freq, dur=1.2, bright=1.0):
    t = np.arange(int(dur * SR)) / SR
    x = (np.sin(2 * np.pi * freq * t) * np.exp(-t * 5.0)
         + 0.35 * bright * np.sin(2 * np.pi * freq * 4.0 * t) * np.exp(-t * 18)
         + 0.12 * bright * np.sin(2 * np.pi * freq * 9.2 * t) * np.exp(-t * 40))
    return x * np.minimum(t / 0.002, 1)


def piano(freq, dur=3.0):
    t = np.arange(int(dur * SR)) / SR
    x = sum(np.sin(2 * np.pi * freq * h * t) * a * np.exp(-t * (1.1 + h * 0.8))
            for h, a in ((1, 1.0), (2, 0.42), (3, 0.18), (4, 0.07)))
    return x * np.minimum(t / 0.004, 1)


def bass(freq, dur):
    t = np.arange(int(dur * SR)) / SR
    x = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * freq * 2 * t)
    return A.lowpass(x * env(len(t), 0.01, 2.2), 600)


def soft_kick():
    return A.lowpass(A.kick(0.5), 220) * 0.9


def shaker(dur=0.06):
    x = A.highpass(A.noise(dur), 5000)
    return x * np.exp(-np.arange(len(x)) / SR * 60) * 0.35


# ------------------------------------------------------------------ sound effects
def sfx(kind):
    n = lambda d: int(d * SR)  # noqa: E731
    if kind == "pop":
        t = np.arange(n(0.12)) / SR
        f = 900 * np.exp(-t * 22) + 380
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 34) * 0.55
    if kind == "paper":
        d = 0.55
        e = np.sin(np.linspace(0, np.pi, n(d))) ** 1.5
        crack = (rng.random(n(d)) > 0.985) * rng.standard_normal(n(d)) * 3
        x = A.bandpass(A.noise(d) * (0.6 + 0.4 * rng.random(n(d))) + crack, 1500, 9000)
        return x * e * 0.32
    if kind == "whoosh":
        return A.whoosh(0.7, 0.55) * 0.9
    if kind == "zoom":
        return A.whoosh(1.6, 0.8) * 0.8
    if kind == "marker":          # highlighter: a soft felt-tip swish
        d = 0.5
        e = np.sin(np.linspace(0, np.pi, n(d))) ** 0.7
        x = A.bandpass(A.noise(d), 1200, 5000) * (0.7 + 0.3 * np.sin(np.linspace(0, 40, n(d))))
        return x * e * 0.32
    if kind == "squeak":          # marker squeak on drawn circles and lines
        d = 0.42
        t = np.arange(n(d)) / SR
        f = 1700 + 500 * np.sin(2 * np.pi * 3.2 * t) + 300 * rng.standard_normal(n(d)).cumsum() / n(d)
        tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.2
        scratch = A.bandpass(A.noise(d), 2500, 7000) * 0.25
        return (tone + scratch) * np.sin(np.linspace(0, np.pi, n(d))) ** 0.8 * 0.7
    if kind == "draw":
        d = 0.8
        x = A.bandpass(A.noise(d), 900, 4000) * (0.5 + 0.5 * np.sin(np.linspace(0, 30, n(d))) ** 2)
        return x * np.sin(np.linspace(0, np.pi, n(d))) * 0.22
    if kind == "swipe":
        return A.whoosh(0.45, 0.5) * 0.5
    if kind in ("grow", "grow_long"):
        d = 0.8 if kind == "grow" else 1.2
        t = np.arange(n(d)) / SR
        f = 260 * (2 ** (t / d * 1.0))
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.18 + A.bandpass(A.noise(d), 600, 3000) * 0.12
        return x * np.minimum(t / 0.05, 1) * np.exp(-((t - d * 0.7) / (d * 0.5)) ** 2) * 0.9
    if kind in ("count", "count_long"):
        d = 0.9 if kind == "count" else 1.6
        out = np.zeros(n(d + 0.1))
        t = 0.0
        while t < d:
            add_mono(out, A.sfx("tick") * 0.7, t)
            t += 0.035 + 0.06 * (t / d) ** 2
        return out
    if kind == "ripple":
        out = np.zeros(n(1.2))
        for k in range(20):
            add_mono(out, sfx("pop") * 0.3, k * 0.04 + rng.random() * 0.01)
        return out
    if kind == "thud":
        k = A.kick(0.6) * 1.0
        return k + A.lowpass(A.noise(0.6), 260) * np.exp(-np.arange(len(k)) / SR * 10) * 0.5
    if kind == "impact":          # the iceberg: a deep hit with a grinding tail
        d = 2.6
        x = np.zeros(n(d))
        k = A.sine_sweep(70, 28, 1.8, 2.0) * 1.2
        x[:len(k)] += k
        grind = A.bandpass(A.noise(d), 150, 1800) * np.exp(-np.arange(n(d)) / SR * 1.6)
        grind *= 0.5 + 0.5 * (rng.random(n(d)) > 0.6)
        return x + grind * 0.45
    if kind == "water":
        d = 0.6
        out = np.zeros(n(d))
        for k in range(10):
            t0 = rng.random() * 0.45
            f0 = rng.uniform(300, 900)
            b = A.sine_sweep(f0, f0 * 1.8, 0.06, 40) * 0.25
            add_mono(out, b, t0)
        return A.lowpass(out + A.lowpass(A.noise(d), 500) * 0.15 * np.sin(np.linspace(0, np.pi, n(d))),
                         3000)
    if kind == "x":
        return sfx("squeak")[: n(0.3)] * 1.2
    if kind == "clock":
        out = np.zeros(n(3.2))
        for k in range(8):
            c = A.bandpass(A.noise(0.02), 2500, 6000) * np.exp(-np.arange(n(0.02)) / SR * 200)
            add_mono(out, c * (0.6 if k % 2 else 0.4), k * 0.4)
        return out
    if kind == "morse":           # C Q D in Morse at ~22 wpm, 640 Hz
        dot = 0.055
        code = "-.-. --.- -.."
        out, t = np.zeros(n(2.6)), 0.0
        for ch in code:
            if ch == " ":
                t += dot * 2
                continue
            d = dot * (3 if ch == "-" else 1)
            tt = np.arange(n(d)) / SR
            beep = np.sin(2 * np.pi * 640 * tt) * np.minimum(np.minimum(tt, d - tt) / 0.004, 1)
            add_mono(out, beep * 0.32, t)
            t += d + dot
        return A.bandpass(out, 300, 3000) + A.bandpass(A.noise(2.6), 800, 2600) * 0.02
    if kind == "projector":       # a soft film-projector rattle under the newsreel
        d = 2.2
        out = np.zeros(n(d))
        for k in range(int(d * 24)):
            c = A.bandpass(A.noise(0.012), 1500, 6000) * np.exp(-np.arange(n(0.012)) / SR * 300)
            add_mono(out, c * (0.5 if k % 2 else 0.3), k / 24)
        hum = A.lowpass(A.noise(d), 300) * 0.15
        return (out + hum) * np.minimum(np.linspace(0, 4, n(d)), 1) * np.minimum(np.linspace(4, 0, n(d)), 1)
    if kind == "radio_off":
        d = 0.5
        x = A.bandpass(A.noise(d), 600, 4000) * np.exp(-np.arange(n(d)) / SR * 12) * 0.3
        x[:n(0.01)] += 0.4
        return x
    return A.sfx(kind)


# ------------------------------------------------------------------ score
CHORDS = {   # D dorian colours: curious, unresolved, warm
    "Dm": ["D3", "A3", "F4", "C5"], "Bb": ["Bb2", "F3", "D4", "A4"], "F": ["F2", "C4", "A4", "E5"],
    "C": ["C3", "G3", "E4", "D5"], "Gm": ["G2", "D4", "Bb4", "F5"], "Am": ["A2", "E4", "C5", "G5"],
}
PROG_A = ["Dm", "Bb", "F", "C"]
PROG_B = ["Dm", "Gm", "Bb", "Am"]          # darker, for the night and the radio
PROG_C = ["F", "C", "Dm", "Bb"]            # resolving, for the aftermath


def score(T, scenes):
    st = {s["key"]: s for s in scenes}
    nS = int(T * SR) + SR * 4
    mus = np.zeros((nS, 2))
    t = np.arange(nS) / SR

    def at(key, dt=0.0):
        return st[key]["start"] + dt

    sections = [(0.0, at("night"), PROG_A), (at("night"), at("boats"), PROG_B),
                (at("boats"), at("after"), PROG_A), (at("after"), T + 4, PROG_C)]
    bar = 4 * BEAT
    # energy curve: how busy the arrangement is (0..1)
    energy_pts = [(0, 0.35), (at("title"), 0.55), (at("rules"), 0.45), (at("ferry"), 0.55),
                  (at("night"), 0.8), (at("night", 3.5), 1.0), (at("radio"), 0.9),
                  (at("radio", st["radio"]["dur"] - 1.0), 1.0), (at("boats"), 0.4),
                  (at("after"), 0.55), (at("after", st["after"]["sentences"][2] - 0.4), 0.15),
                  (at("end"), 0.5), (T, 0.3)]
    ex, ey = zip(*energy_pts)

    def energy(x):
        return float(np.interp(x, ex, ey))

    b = 0.0
    ib = 0
    while b < T + 2:
        sec = next(s for s in sections if s[0] <= b < s[1]) if b < T + 4 else sections[-1]
        ch = CHORDS[sec[2][ib % 4]]
        e = energy(b)
        # pad
        add(mus, A.pad([note(x) for x in ch[:3]], bar + 1.2, 0.6, 1.4, 700 + 900 * e), b,
            0.55 + 0.3 * e)
        # bass on 1 and the "and" of 3
        add(mus, bass(note(ch[0]) / (2 if note(ch[0]) > 110 else 1), 1.4), b, 0.55 + 0.25 * e)
        if e > 0.5:
            add(mus, bass(note(ch[0]) / (2 if note(ch[0]) > 110 else 1), 0.8), b + 2.5 * BEAT, 0.35)
        # plucked ostinato in eighths: chord tones, up and back
        pattern = [1, 2, 3, 2, 1, 3, 2, 3] if ib % 2 == 0 else [1, 3, 2, 3, 1, 2, 3, 2]
        for k, idx in enumerate(pattern):
            if e < 0.4 and k % 2:
                continue
            fq = note(ch[idx]) * (2 if idx == 1 else 1)
            add(mus, marimba(fq, 0.9, 0.6 + 0.4 * e), b + k * BEAT / 2,
                0.16 + 0.10 * e, pan=0.35 * np.sin(k * 1.3))
        # shaker eighths and a soft kick when it builds
        if e > 0.5:
            for k in range(8):
                add(mus, shaker(), b + k * BEAT / 2 + (0.012 if k % 2 else 0), 0.5 * e,
                    pan=0.3)
        if e > 0.75:
            for k in (0, 2):
                add(mus, soft_kick(), b + k * BEAT, 0.45 * e)
        b += bar
        ib += 1
    # swell into the collision and a held low note after it
    tb = at("night", 0.4 + (st["night"]["words"][0][1] if st["night"]["words"] else 0))
    add(mus, A.whoosh(2.5, 0.95) * 0.5, at("night") + 0.5, 0.6)
    add(mus, A.pad([note("D2"), note("A2")], 6.0, 0.05, 4.0, 400), tb + 3.0, 0.6)
    # piano motif at the open and the close
    motif = ["D4", "F4", "A4", "E4", "F4", "D4"]
    for i, nm in enumerate(motif):
        add(mus, piano(note(nm)), 0.4 + i * BEAT * 1.5, 0.14, pan=0.25 * np.sin(i))
    for i, nm in enumerate(["F4", "A4", "C5", "E5", "D5"]):
        add(mus, piano(note(nm), 4.0), at("end", 0.2) + i * BEAT, 0.16, pan=-0.2 * np.sin(i))
    # fade in/out
    fade = np.minimum(t / 1.2, 1) * np.clip((T + 0.5 - t) / 2.5, 0, 1)
    mus *= fade[:, None]
    return A.reverb(mus, 2.2, 0.28)


# ------------------------------------------------------------------ mastering
TARGET_LUFS = -16.0
CEILING_DB = -2.0           # sample-peak ceiling; leaves room for AAC overshoot


def lufs(x):
    import pyloudnorm
    return pyloudnorm.Meter(SR).integrated_loudness(x)


def limit(x, ceiling_db=CEILING_DB, lookahead=0.006, release=0.12, block=32):
    """Transparent look-ahead peak limiter: only touches the rare peaks above the
    ceiling, with a smooth 6 ms attack and 120 ms release (no pumping)."""
    c = 10 ** (ceiling_db / 20)
    peak = np.abs(x).max(axis=1) if x.ndim > 1 else np.abs(x)
    nb = int(np.ceil(len(peak) / block))
    pk = np.pad(peak, (0, nb * block - len(peak))).reshape(nb, block).max(axis=1)
    need = np.clip(1 - c / np.maximum(pk, 1e-9), 0, 1)          # gain reduction needed per block
    la = max(1, int(lookahead * SR / block))
    held = np.array([need[i:i + la + 1].max() for i in range(nb)])  # look ahead
    dec = np.exp(-block / (release * SR))
    red = np.empty(nb)
    r = 0.0
    for i in range(nb):
        r = max(held[i], r * dec)
        red[i] = r
    red = np.convolve(red, np.ones(la) / la, mode="same")             # smooth the attack
    red = np.maximum(red, need)                                       # never under-limit a block
    g = 1 - np.interp(np.arange(len(peak)), np.arange(nb) * block + block / 2, red)
    return x * (g[:, None] if x.ndim > 1 else g)


def master(x, target=TARGET_LUFS):
    """A fixed gain to the target loudness, then the peak limiter; repeated
    once so the limited result still lands on the target."""
    for _ in range(3):
        x = x * 10 ** ((target - lufs(x)) / 20)
        x = limit(x)
        if abs(lufs(x) - target) < 0.1:
            break
    return x


def main():
    scenes = timeline.build()
    T = sum(s["dur"] for s in scenes)
    nS = int(T * SR)
    voice = np.zeros((nS + SR, 2))
    for s in scenes:
        if s["voice"] is None:
            continue
        v, sr = sf.read(os.path.join(timeline.CBUILD, "voice", f"{s['key']}.wav"))
        if v.ndim > 1:
            v = v.mean(axis=1)
        v = resample_poly(v, SR, sr) if sr != SR else v
        add(voice, np.stack([v, v], 1), s["start"] + s["voice"], 1.0)
    envv = A.moving_average(np.abs(voice[:, 0]), int(0.2 * SR))
    envv = np.clip(envv / (np.percentile(envv[envv > 1e-4], 90) * 0.5 + 1e-9), 0, 1)
    duck = 1.0 - 0.72 * A.moving_average(envv, int(0.35 * SR))       # about -11 dB under speech
    music = score(T, scenes)[: len(voice)]
    fx = np.zeros_like(voice)
    with open(os.path.join(timeline.CBUILD, "sfx.json")) as fh:
        cues = json.load(fh)
    for items in cues.values():
        for t0, kind, gain in items:
            add(fx, sfx(kind), t0, gain * 0.55, pan=float(rng.uniform(-0.25, 0.25)))
    fx = A.reverb(fx, 1.2, 0.16)
    music = music * duck[:, None] * 0.13
    fx = fx * 0.42
    if os.environ.get("STEMS"):
        os.makedirs(os.path.join(timeline.CBUILD, "stems"), exist_ok=True)
        for name, stem in (("voice", voice), ("music", music), ("fx", fx)):
            sf.write(os.path.join(timeline.CBUILD, "stems", f"{name}.wav"),
                     stem[:nS].astype(np.float32), SR, subtype="FLOAT")
    mix = (voice + music + fx)[:nS]
    mix[: int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))[:, None]
    mix = master(mix)
    sf.write(os.path.join(timeline.CBUILD, "mix.wav"), mix.astype(np.float32), SR, subtype="FLOAT")
    vo = master(voice[:nS].copy())
    sf.write(os.path.join(timeline.CBUILD, "voice_master.wav"), vo.astype(np.float32), SR,
             subtype="FLOAT")
    print(f"mix.wav: {T:.2f}s, {sum(len(v) for v in cues.values())} sound cues, "
          f"{lufs(mix):.1f} LUFS, peak {20 * np.log10(np.abs(mix).max()):.1f} dBFS")


if __name__ == "__main__":
    main()
