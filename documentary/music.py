"""Procedural score: tanpura drone (India), string pads (England), sparse bell motifs.

All sound is synthesized here, so the soundtrack carries no third-party rights.
"""
import math

import numpy as np

SR = 48000
TONIC = 146.83  # D3


def _env(n, attack, release, sr=SR):
    e = np.ones(n, np.float32)
    a = min(int(attack * sr), n)
    r = min(int(release * sr), n - a)
    if a:
        e[:a] = np.linspace(0, 1, a) ** 2
    if r:
        e[n - r:] *= np.linspace(1, 0, r) ** 2
    return e


def reverb(x, sr=SR, secs=3.2, mix=0.35, seed=1):
    """Cheap stereo convolution reverb with an exponentially decaying noise IR."""
    rng = np.random.default_rng(seed)
    n = int(secs * sr)
    t = np.arange(n) / sr
    out = []
    for ch in range(2):
        ir = rng.normal(0, 1, n) * np.exp(-t * 6.9 / secs)
        ir[: int(0.012 * sr)] = 0
        ir /= np.sqrt((ir ** 2).sum())
        # FFT convolution in blocks
        L = len(x) + n - 1
        nfft = 1 << (L - 1).bit_length()
        y = np.fft.irfft(np.fft.rfft(x[:, ch], nfft) * np.fft.rfft(ir, nfft), nfft)[: len(x)]
        out.append(y)
    wet = np.stack(out, 1).astype(np.float32)
    return (x * (1 - mix) + wet * mix * 2.2).astype(np.float32)


def tanpura(dur, tonic=TONIC, seed=0):
    """Four-string tanpura cycle (Pa Sa Sa Sa'), with slowly blooming upper partials."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    out = np.zeros((n, 2), np.float32)
    notes = [tonic * 0.75, tonic, tonic, tonic * 0.5]
    pans = [0.35, 0.55, 0.6, 0.45]
    period = 1.25
    t_note = np.arange(int(5.5 * SR)) / SR
    bank = {}
    for f in set(notes):
        for v in range(3):  # a few variants per string, reused
            f0 = f * (1 + rng.normal(0, 0.0007))
            sig = np.zeros_like(t_note)
            for h in range(1, 28):
                amp = 1.0 / h ** 0.9
                bloom = 0.12 + 0.05 * h  # jawari: higher partials peak later
                env = (1 - np.exp(-t_note / (0.004 + 0.003 * h))) * np.exp(-t_note / (2.2 + 0.4 / h))
                env *= 1 + 0.9 * np.exp(-((t_note - bloom) ** 2) / (2 * (0.25 + 0.02 * h) ** 2)) * (h > 4)
                sig += amp * env * np.sin(2 * math.pi * f0 * h * t_note * (1 + 0.00015 * h) + rng.uniform(0, 6.28))
            bank[(f, v)] = (sig * 0.06).astype(np.float32)
    k = 0
    t0 = 0.0
    while t0 < dur:
        sig = bank[(notes[k % 4], int(rng.integers(0, 3)))]
        s = int(t0 * SR)
        e = min(n, s + len(sig))
        p = pans[k % 4]
        out[s:e, 0] += sig[: e - s] * (1 - p)
        out[s:e, 1] += sig[: e - s] * p
        k += 1
        t0 += period + rng.normal(0, 0.02)
    return out


CHORDS = {
    # semitone offsets from D, voiced low
    "Dm": [-12, 0, 3, 7, 12], "Bb": [-16, -4, 2, 5, 10], "F": [-9, 3, 7, 12, 15], "C": [-14, -2, 2, 5, 10],
    "Gm": [-7, 5, 8, 12, 17], "A": [-17, -5, 1, 4, 7], "D": [-12, 0, 4, 7, 12], "G": [-7, 5, 9, 12, 14],
    "Em": [-10, 2, 5, 9, 14], "Bm": [-15, -3, 0, 4, 9],
}


def pad(dur, progression, chord_len=8.0, brightness=6, seed=0, tonic=TONIC):
    """Slow string-like pad: detuned additive voices, soft attack, gentle vibrato."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    out = np.zeros((n, 2), np.float32)
    t0, i = 0.0, 0
    while t0 < dur:
        name = progression[i % len(progression)]
        L = chord_len + 3.0
        m = int(L * SR)
        t = np.arange(m) / SR
        sig = np.zeros((m, 2), np.float32)
        for semi in CHORDS[name]:
            f = tonic * 2 ** (semi / 12)
            for det, pan in ((-0.0025, 0.3), (0.0025, 0.7), (0.0, 0.5)):
                vib = 1 + 0.002 * np.sin(2 * math.pi * (4.5 + rng.uniform(-0.5, 0.5)) * t + rng.uniform(0, 6))
                ph = 2 * math.pi * f * (1 + det) * np.cumsum(vib) / SR
                v = np.zeros(m, np.float32)
                for h in range(1, brightness + 1):
                    v += np.sin(h * ph + rng.uniform(0, 6)) / h ** 1.6
                sig[:, 0] += v * (1 - pan)
                sig[:, 1] += v * pan
        sig *= (_env(m, 2.5, 3.5) * 0.018)[:, None]
        s = int(t0 * SR)
        e = min(n, s + m)
        out[s:e] += sig[: e - s]
        t0 += chord_len
        i += 1
    return out


def bells(dur, scale=(0, 2, 4, 7, 9, 12, 14), density=0.22, seed=0, tonic=TONIC * 2):
    """Sparse, soft bell/celesta notes from a pentatonic set."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    out = np.zeros((n, 2), np.float32)
    t0 = rng.uniform(1, 3)
    while t0 < dur - 4:
        f = tonic * 2 ** (rng.choice(scale) / 12)
        m = int(4 * SR)
        t = np.arange(m) / SR
        v = (np.sin(2 * math.pi * f * t) + 0.35 * np.sin(2 * math.pi * f * 2.0 * t) * np.exp(-t * 2)
             + 0.15 * np.sin(2 * math.pi * f * 3.01 * t) * np.exp(-t * 4))
        v *= np.exp(-t * 1.1) * (1 - np.exp(-t * 200)) * 0.035
        p = rng.uniform(0.25, 0.75)
        s = int(t0 * SR)
        e = min(n, s + m)
        out[s:e, 0] += v[: e - s] * (1 - p)
        out[s:e, 1] += v[: e - s] * p
        t0 += rng.exponential(1 / density) + 1.0
    return out


SECTION_STYLE = {
    # chapter -> (tanpura level, pad progression or None, bell density)
    0: (0.7, ["Dm", "Bb", "F", "C"], 0.10),
    1: (1.0, None, 0.12),
    2: (1.0, ["Dm", "C"], 0.10),
    3: (0.8, ["Dm", "Bb", "F", "A"], 0.18),
    4: (0.6, ["F", "C", "Dm", "Bb"], 0.08),
    5: (0.0, ["D", "G", "Bm", "A"], 0.25),
    6: (0.0, ["Dm", "Gm", "A", "Dm"], 0.05),
    7: (0.0, ["F", "C", "D", "G"], 0.15),
    8: (0.8, ["Dm", "Bb", "Gm", "A"], 0.06),
    9: (0.6, ["D", "G", "Em", "A"], 0.2),
}


def score(sections, total):
    """sections: list of (start, end, chapter). Returns float32 stereo array of length total*SR."""
    n = int(total * SR)
    out = np.zeros((n, 2), np.float32)
    xf = 3.0
    for k, (s, e, ch) in enumerate(sections):
        tl, prog, dens = SECTION_STYLE.get(ch, SECTION_STYLE[0])
        s0 = max(0.0, s - xf / 2)
        e0 = min(total, e + xf / 2)
        d = e0 - s0
        part = np.zeros((int(d * SR), 2), np.float32)
        if tl:
            part += tanpura(d, seed=k) * tl
        if prog:
            part += pad(d, prog, chord_len=9.0 if ch == 6 else 8.0, brightness=4 if ch == 6 else 6, seed=k) * \
                (1.15 if not tl else 0.8)
        if dens:
            part += bells(d, density=dens, seed=k + 50)
        part *= _env(len(part), xf, xf)[:, None]
        i0 = int(s0 * SR)
        out[i0:i0 + len(part)] += part[: n - i0]
    out = reverb(out)
    out /= max(1e-6, np.abs(out).max()) / 0.7
    return out
