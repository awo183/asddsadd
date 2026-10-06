"""Original score, sound effects and final mix for the documentary.

Everything is synthesised with numpy/scipy: drones, pads, a sparse piano, pulses,
Geiger-counter crackle, typewriter, train, wind and the explosion. Music ducks
under the narration; the result is loudness-normalised with ffmpeg (EBU R128).
"""
import json, os, subprocess, sys
import numpy as np
import soundfile as sf
from scipy import signal

from common import BUILD

SR = 48000
rng = np.random.default_rng(1949)


def note(n):  # MIDI -> Hz
    return 440.0 * 2 ** ((n - 69) / 12)


def env_adsr(n, a, r):
    e = np.ones(n, dtype=np.float32)
    na, nr = int(a * SR), int(r * SR)
    if na:
        e[:na] = np.linspace(0, 1, na) ** 2
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr) ** 2
    return e


def lowpass(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), "low")
    return signal.lfilter(b, a, x, axis=0).astype(np.float32)


def highpass(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), "high")
    return signal.lfilter(b, a, x, axis=0).astype(np.float32)


def bandpass(x, f1, f2, order=2):
    b, a = signal.butter(order, [f1 / (SR / 2), f2 / (SR / 2)], "band")
    return signal.lfilter(b, a, x, axis=0).astype(np.float32)


def pad_voice(freq, dur, bright=6, detune=0.0025):
    """Soft saw-like pad: additive harmonics, three detuned oscillators, stereo."""
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    out = np.zeros((n, 2), np.float32)
    for k, dt in enumerate((-detune, 0.0, detune)):
        f = freq * (1 + dt)
        ph = rng.uniform(0, 2 * np.pi)
        wave = np.zeros(n, np.float32)
        for h in range(1, bright + 1):
            if f * h > 5000:
                break
            wave += np.sin(2 * np.pi * f * h * t + ph * h) / h ** 1.3
        pan = (k - 1) * 0.6
        out[:, 0] += wave * (1 - pan) * 0.5
        out[:, 1] += wave * (1 + pan) * 0.5
    return out / 3


def piano(freq, dur=4.0, vel=0.6):
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    w = np.zeros(n, np.float32)
    for h in range(1, 9):
        fh = freq * h * (1 + 0.0004 * h * h)
        w += np.sin(2 * np.pi * fh * t) * np.exp(-t * (1.2 + 0.9 * h)) / h ** 1.1
    hammer = rng.normal(0, 1, n).astype(np.float32) * np.exp(-t * 90) * 0.15
    w = (w + lowpass(hammer, 3000)) * vel
    w *= env_adsr(n, 0.004, 0.3)
    return np.stack([w, w], 1)


def reverb(x, secs=3.2, mix=0.35, damp=4000):
    n = int(secs * SR)
    t = np.arange(n) / SR
    ir = rng.normal(0, 1, (n, 2)).astype(np.float32) * np.exp(-t * 6.9 / secs)[:, None]
    ir = lowpass(ir, damp)
    ir[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))[:, None]
    ir /= np.sqrt((ir ** 2).sum(0, keepdims=True))
    wet = np.stack([signal.fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], 1).astype(np.float32)
    return x * (1 - mix) + wet * mix * 1.4


def place(buf, x, t, gain=1.0):
    i = int(t * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(x))
    buf[i:j] += x[: j - i] * gain


# ---------------------------------------------------------------- score
CHORDS = {  # MIDI notes (D minor world)
    "Dm": [38, 50, 53, 57, 62], "Bb": [34, 46, 50, 53, 58], "Gm": [31, 43, 50, 55, 58],
    "A": [33, 45, 49, 52, 57], "F": [29, 41, 48, 53, 57], "C": [36, 48, 52, 55, 60],
    "Eb": [39, 51, 55, 58, 63], "Dsus": [38, 50, 55, 57, 62], "D": [38, 50, 54, 57, 62],
    "Dm9": [38, 50, 53, 57, 64],
}

MOODS = {
    #            chords (cycle)             chord s  pad   drone  piano pulse  eerie
    "cold_open": (["Dm", "Bb"], 9.0, 0.10, 0.55, 0.0, 0.35, 0.10),
    "title":     (["Dm9", "Bb", "Gm", "A"], 4.0, 0.55, 0.35, 0.0, 0.0, 0.0),
    "teaser":    (["Dm", "Bb", "Gm", "A"], 2.0, 0.40, 0.45, 0.0, 0.0, 0.10),
    "ch1":       (["Dm", "Bb", "F", "C"], 6.0, 0.30, 0.25, 0.55, 0.0, 0.0),
    "ch2":       (["Dm", "Bb", "Gm", "A"], 6.0, 0.30, 0.35, 0.20, 0.30, 0.0),
    "ch3":       (["Dm", "Dm", "Bb", "A"], 5.0, 0.28, 0.35, 0.0, 0.50, 0.0),
    "ch4":       (["Gm", "Eb", "Dm", "A"], 6.0, 0.32, 0.40, 0.25, 0.15, 0.10),
    "ch5":       (["Dm", "Eb", "Dm", "A"], 8.0, 0.22, 0.60, 0.0, 0.25, 0.30),
    "ch6":       (["Dm", "Eb"], 9.0, 0.18, 0.60, 0.0, 0.0, 0.40),
    "ch7":       (["Gm", "Dm", "Bb", "A"], 7.0, 0.25, 0.40, 0.25, 0.0, 0.15),
    "ch8":       (["Bb", "F", "Gm", "Dsus", "D"], 6.0, 0.38, 0.25, 0.50, 0.0, 0.0),
    "end":       (["Bb", "F", "Gm", "D"], 7.0, 0.30, 0.15, 0.45, 0.0, 0.0),
}

PENTA = [62, 65, 67, 69, 72, 74, 77]
PERC = {"cold_open": 0.5, "teaser": 0.9, "ch2": 0.35, "ch3": 0.55, "ch5": 0.35}  # D minor pentatonic-ish melody pool


def section(mood, dur, start_abs):
    chords, clen, g_pad, g_drone, g_piano, g_pulse, g_eerie = MOODS[mood]
    n = int(dur * SR)
    out = np.zeros((n, 2), np.float32)
    # pads, crossfading chords
    t, k = 0.0, 0
    while t < dur:
        name = chords[k % len(chords)]
        L = min(clen + 2.5, dur - t + 2.5)
        v = np.zeros((int(L * SR), 2), np.float32)
        for m in CHORDS[name]:
            v += pad_voice(note(m), L, bright=5 if m < 45 else 7) * (0.7 if m < 45 else 0.5)
        v *= env_adsr(len(v), 2.0, 2.4)[:, None]
        place(out, v * g_pad * 0.22, t)
        t += clen
        k += 1
    out = lowpass(out, 2200)
    # drone on D with slow swell
    tt = np.arange(n, dtype=np.float32) / SR
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * tt / 11 + start_abs)
    dr = (np.sin(2 * np.pi * note(26) * tt) * 0.6 + np.sin(2 * np.pi * note(38) * tt) * 0.3 +
          np.sin(2 * np.pi * note(45) * tt * 1.001) * 0.15)
    noise = lowpass(rng.normal(0, 1, n).astype(np.float32), 180) * 0.6
    drone = (dr + noise) * lfo * g_drone * 0.16
    out += np.stack([drone, drone], 1)
    # sparse piano phrases
    if g_piano > 0:
        tp = 1.5
        while tp < dur - 2:
            phrase = rng.choice(PENTA, size=rng.integers(2, 4))
            for j, m in enumerate(phrase):
                place(out, piano(note(int(m)), 4.5, 0.5 + 0.3 * rng.random()) * g_piano * 0.28, tp + j * 0.75)
                if rng.random() < 0.4:
                    place(out, piano(note(int(m) - 12), 4.5, 0.4) * g_piano * 0.18, tp + j * 0.75)
            tp += rng.uniform(4.0, 7.0)
    # low pulse (heartbeat / ostinato)
    if g_pulse > 0:
        bpm = 72 if mood != "ch3" else 96
        beat = 60 / bpm
        pl = int(0.5 * SR)
        tq = np.arange(pl) / SR
        f_sweep = 70 * np.exp(-tq * 6) + 38
        thump = (np.sin(2 * np.pi * np.cumsum(f_sweep) / SR) * np.exp(-tq * 9)).astype(np.float32)
        thump = np.stack([thump, thump], 1)
        tb = 0.0
        i = 0
        while tb < dur:
            acc = 1.0 if i % 4 == 0 else (0.6 if mood == "ch3" else (0.75 if i % 2 == 0 else 0.0))
            if acc:
                place(out, thump * g_pulse * 0.5 * acc, tb)
            tb += beat
            i += 1
    # eerie high cluster with beating
    if g_eerie > 0:
        e = (np.sin(2 * np.pi * note(86) * tt) + np.sin(2 * np.pi * note(86) * 1.006 * tt) +
             0.5 * np.sin(2 * np.pi * note(93) * tt * 0.997))
        sw = 0.5 + 0.5 * np.sin(2 * np.pi * tt / 13)
        e = e * sw * g_eerie * 0.03
        out[:, 0] += e
        out[:, 1] += np.roll(e, 900)
    # war-drum percussion for the tense sections
    g_perc = PERC.get(mood, 0.0)
    if g_perc > 0:
        bpm = 84
        beat = 60 / bpm
        pl = int(0.9 * SR)
        tq = np.arange(pl) / SR
        drum = (np.sin(2 * np.pi * np.cumsum(95 * np.exp(-tq * 9) + 48) / SR) * np.exp(-tq * 5.5)
                + lowpass(rng.normal(0, 1, pl).astype(np.float32), 600) * np.exp(-tq * 25) * 0.6).astype(np.float32)
        drum = np.stack([drum, drum], 1)
        pattern = [1.0, 0, 0.55, 0, 0.8, 0, 0.55, 0.45]  # 8th notes
        tb, i = 0.0, 0
        while tb < dur:
            v = pattern[i % 8]
            if v:
                place(out, drum * v * g_perc * 0.55, tb)
            tb += beat / 2
            i += 1
    fade = env_adsr(n, 1.5, 2.5)[:, None]
    return out * fade


def score(tl):
    total = tl["duration"]
    buf = np.zeros((int((total + 4) * SR), 2), np.float32)
    cues = tl["music"] + [{"t": total, "mood": None}]
    for a, b in zip(cues, cues[1:]):
        if a["mood"] is None:
            continue
        dur = b["t"] - a["t"] + 2.5  # overlap into the next section for a crossfade
        place(buf, section(a["mood"], dur, a["t"]), a["t"])
    return reverb(buf, 3.5, 0.38)


# ---------------------------------------------------------------- sound effects
def sfx_typewriter(dur, cps=22):
    n = int(dur * SR)
    out = np.zeros((n, 2), np.float32)
    clk_n = int(0.03 * SR)
    tq = np.arange(clk_n) / SR
    t = 0.0
    while t < dur:
        click = rng.normal(0, 1, clk_n).astype(np.float32) * np.exp(-tq * 260)
        click = bandpass(click, 1500, 6000) + np.sin(2 * np.pi * 180 * tq).astype(np.float32) * np.exp(-tq * 120) * 0.4
        pan = rng.uniform(-0.3, 0.3)
        place(out, np.stack([click * (1 - pan), click * (1 + pan)], 1) * rng.uniform(0.5, 1.0), t)
        t += 1 / cps * rng.uniform(0.6, 1.5)
    return out * 0.35


def sfx_stamp():
    n = int(0.6 * SR)
    tq = np.arange(n) / SR
    thud = np.sin(2 * np.pi * (90 * np.exp(-tq * 20) + 50) * tq) * np.exp(-tq * 18)
    slap = lowpass(rng.normal(0, 1, n).astype(np.float32) * np.exp(-tq * 60), 2500)
    x = (thud * 0.9 + slap * 0.5).astype(np.float32)
    return np.stack([x, x], 1) * 0.8


def sfx_explosion():
    n = int(9 * SR)
    tq = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(55 * np.exp(-tq * 0.8) + 22) / SR) * np.exp(-tq * 0.55)
    rumble = lowpass(rng.normal(0, 1, (n, 2)).astype(np.float32), 160, 4) * np.exp(-tq * 0.35)[:, None] * 2.2
    crack = highpass(rng.normal(0, 1, (n, 2)).astype(np.float32), 800) * np.exp(-tq * 9)[:, None] * 0.25
    x = np.stack([boom, boom], 1).astype(np.float32) * 0.9 + rumble + crack
    x *= env_adsr(n, 0.01, 3.0)[:, None]
    return x * 0.9


def sfx_geiger(dur, rate=6.0):
    n = int(dur * SR)
    out = np.zeros((n, 2), np.float32)
    clk = np.zeros(int(0.004 * SR), np.float32)
    clk[0], clk[1], clk[2] = 1.0, -0.7, 0.3
    t = rng.exponential(1 / rate)
    while t < dur:
        r = rate * (1 + 1.5 * (t / dur))  # crackle intensifies
        place(out, np.stack([clk, clk], 1) * rng.uniform(0.4, 1.0), t)
        t += rng.exponential(1 / r)
    return highpass(out, 1200) * 0.5


def sfx_train(dur):
    n = int(dur * SR)
    tq = np.arange(n) / SR
    rumble = lowpass(rng.normal(0, 1, (n, 2)).astype(np.float32), 120, 3) * 0.8
    out = rumble * (0.7 + 0.3 * np.sin(2 * np.pi * tq / 3))[:, None]
    cl = int(0.08 * SR)
    tc = np.arange(cl) / SR
    clack = (bandpass(rng.normal(0, 1, cl).astype(np.float32), 300, 2500) * np.exp(-tc * 50)).astype(np.float32)
    t = 0.2
    while t < dur:
        place(out, np.stack([clack, clack], 1) * 0.6, t)
        place(out, np.stack([clack, clack], 1) * 0.45, t + 0.18)
        t += 0.95
    return out * env_adsr(n, 1.0, 1.5)[:, None] * 0.45


def sfx_wind(dur):
    n = int(dur * SR)
    tq = np.arange(n) / SR
    w = bandpass(rng.normal(0, 1, (n, 2)).astype(np.float32), 200, 900)
    mod = (0.5 + 0.5 * np.sin(2 * np.pi * tq / 5.3))[:, None] * (0.6 + 0.4 * np.sin(2 * np.pi * tq / 1.7 + 1))[:, None]
    return w * mod * env_adsr(n, 2.0, 2.0)[:, None] * 0.35


def sfx_whoosh(dur=0.6, soft=False):
    n = int(dur * SR)
    tq = np.arange(n) / SR
    noise = rng.normal(0, 1, (n, 2)).astype(np.float32)
    env = np.sin(np.pi * np.clip(tq / dur, 0, 1)) ** 2
    # sweep a band-pass upwards then down by mixing two filtered copies
    lo = bandpass(noise, 300, 1500)
    hi = bandpass(noise, 1500, 7000)
    mixk = (np.sin(np.pi * tq / dur) ** 1.5)[:, None]
    x = (lo * (1 - mixk) + hi * mixk) * env[:, None]
    pan = np.linspace(-0.7, 0.7, n)[:, None]
    x = np.concatenate([x[:, :1] * (1 - pan), x[:, 1:] * (1 + pan)], 1)
    return x * (0.35 if soft else 0.6)


def sfx_impact(big=False):
    n = int((2.5 if big else 1.2) * SR)
    tq = np.arange(n) / SR
    sub = np.sin(2 * np.pi * np.cumsum(60 * np.exp(-tq * 3) + 32) / SR) * np.exp(-tq * (1.6 if big else 3.5))
    body = lowpass(rng.normal(0, 1, n).astype(np.float32), 900) * np.exp(-tq * 14)
    crack = highpass(rng.normal(0, 1, n).astype(np.float32), 2500) * np.exp(-tq * 45) * 0.5
    x = (sub * 1.1 + body * 0.8 + crack).astype(np.float32)
    x = np.stack([x, x], 1)
    return x * (1.0 if big else 0.7)


def sfx_tick():
    n = int(0.08 * SR)
    tq = np.arange(n) / SR
    x = (np.sin(2 * np.pi * 2200 * tq) * np.exp(-tq * 90) + bandpass(rng.normal(0, 1, n).astype(np.float32), 2000, 6000)
         * np.exp(-tq * 120) * 0.4).astype(np.float32)
    return np.stack([x, x], 1) * 0.45


def sfx_riser(dur=2.0):
    n = int(dur * SR)
    tq = np.arange(n) / SR
    f = 120 * (8 ** (tq / dur))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3
    noise = highpass(rng.normal(0, 1, n).astype(np.float32), 1500) * 0.5
    env = (tq / dur) ** 2
    x = ((tone + noise) * env).astype(np.float32)
    return np.stack([x, np.roll(x, 300)], 1) * 0.5


def sfx_glitch():
    n = int(0.35 * SR)
    x = rng.normal(0, 1, n).astype(np.float32)
    gate = (np.floor(np.arange(n) / (SR * 0.02)) % 2).astype(np.float32)
    x = bandpass(x, 800, 5000) * gate
    sq = np.sign(np.sin(2 * np.pi * 180 * np.arange(n) / SR)).astype(np.float32) * 0.2
    x = (x + sq * gate) * np.linspace(1, 0.3, n)
    return np.stack([x, x], 1) * 0.35


def sfx_pin():
    n = int(0.15 * SR)
    tq = np.arange(n) / SR
    x = (bandpass(rng.normal(0, 1, n).astype(np.float32), 400, 3000) * np.exp(-tq * 60)).astype(np.float32)
    return np.stack([x, x], 1) * 0.5


def sfx_track(tl):
    buf = np.zeros((int((tl["duration"] + 10) * SR), 2), np.float32)
    for c in tl["sfx"]:
        k, t = c["kind"], c["t"]
        if "dur" in c and c["dur"] < 0.3:
            continue  # cue shorter than its own attack: skip
        if k == "typewriter":
            place(buf, sfx_typewriter(c["dur"]), t)
        elif k == "stamp":
            place(buf, sfx_stamp(), t)
        elif k == "explosion":
            place(buf, sfx_explosion(), t - 0.05)
        elif k == "geiger":
            place(buf, sfx_geiger(c["dur"]), t)
        elif k == "train":
            place(buf, sfx_train(c["dur"]), t)
        elif k == "wind":
            place(buf, sfx_wind(c["dur"]), t)
        elif k == "whoosh":
            place(buf, sfx_whoosh(c.get("dur", 0.6)), t - c.get("dur", 0.6) / 2)
        elif k == "whoosh_soft":
            place(buf, sfx_whoosh(c.get("dur", 0.9), soft=True), t - c.get("dur", 0.9) / 2)
        elif k == "impact":
            place(buf, sfx_impact(), t)
        elif k == "impact_big":
            place(buf, sfx_impact(True), t)
        elif k == "tick":
            place(buf, sfx_tick(), t)
        elif k == "riser":
            place(buf, sfx_riser(c.get("dur", 2.0)), t - c.get("dur", 2.0))
        elif k == "glitch":
            place(buf, sfx_glitch(), t - 0.15)
        elif k == "pin":
            place(buf, sfx_pin(), t)
    return buf


# ---------------------------------------------------------------- mix
def narration_track(tl):
    buf = np.zeros((int((tl["duration"] + 4) * SR), 2), np.float32)
    vad = np.zeros(len(buf), np.float32)
    for seg in tl["narration"]:
        x, sr = sf.read(os.path.join(BUILD, "voice", seg["id"] + ".wav"), dtype="float32")
        if sr != SR:
            x = signal.resample_poly(x, SR, sr).astype(np.float32)
        x = highpass(x, 70)
        place(buf, np.stack([x, x], 1), seg["start"])
        i = int(seg["start"] * SR)
        vad[i:i + len(x)] = 1.0
    return buf, vad


def duck_envelope(vad, depth_db=-9.0):
    # smooth the voice-activity mask: fast attack, slow release
    hop = 480
    v = vad[::hop]
    e = np.zeros_like(v)
    a_up, a_dn = 1 - np.exp(-1 / (0.12 * SR / hop)), 1 - np.exp(-1 / (0.8 * SR / hop))
    for i in range(1, len(v)):
        a = a_up if v[i] > e[i - 1] else a_dn
        e[i] = e[i - 1] + a * (v[i] - e[i - 1])
    e = np.repeat(e, hop)[: len(vad)]
    return (10 ** (depth_db * e / 20)).astype(np.float32)


def main():
    tl = json.load(open(os.path.join(BUILD, "timeline.json")))
    total = tl["duration"]
    voice, vad = narration_track(tl)
    music = score(tl)[: len(voice)]
    fx = sfx_track(tl)[: len(voice)]
    duck = duck_envelope(vad)[:, None]
    # silence the music for a beat at the flash, then let the explosion carry
    for c in tl["sfx"]:
        if c["kind"] == "explosion":
            i = int(c["t"] * SR)
            g = np.ones(len(music), np.float32)
            a, b = i - int(0.4 * SR), i + int(4 * SR)
            g[a:i] = np.linspace(1, 0, i - a)
            g[i:b] = np.linspace(0, 1, b - i) ** 2
            music *= g[:, None]
    mix = voice * 1.0 + music * 0.55 * duck + fx * 0.6 * (0.6 + 0.4 * duck)
    n = int(total * SR)
    mix = mix[:n]
    mix *= env_adsr(n, 0.05, 3.0)[:, None]
    mix /= max(1.0, np.abs(mix).max() / 0.95)
    raw = os.path.join(BUILD, "mix_raw.wav")
    sf.write(raw, mix, SR, subtype="PCM_24")
    # EBU R128 two-pass loudness normalisation to -16 LUFS (online-video standard)
    out = os.path.join(BUILD, "mix.wav")
    p1 = subprocess.run(["ffmpeg", "-hide_banner", "-i", raw, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
                         "-f", "null", "-"], capture_output=True, text=True).stderr
    j = json.loads(p1[p1.rindex("{"):p1.rindex("}") + 1])
    af = (f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
          f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", af, "-ar", str(SR), out], check=True)
    print("audio ->", out, f"({total:.1f}s)")


if __name__ == "__main__":
    main()
