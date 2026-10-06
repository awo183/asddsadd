"""Assemble and render the documentary.

    python3 build.py --vo VO_DIR --media MEDIA_DIR --out OUT_DIR [--encoder auto|nvenc|cpu] [--jobs 4]

Steps: plan timeline -> render video segments in parallel -> mix audio -> mux with subtitles/chapters.
The video encoder is NVIDIA NVENC (GPU) when one is available, otherwise libx264 (CPU).
"""
import argparse
import json
import math
import multiprocessing as mp
import os
import re
import subprocess
import sys
import time

import numpy as np
import soundfile as sf

import engine
from engine import FPS, H, W

XF = 0.8           # crossfade between shots (s)
LEAD = 0.45        # silence before each narrated beat (s)
TAIL = 0.55        # silence after each narrated beat (s)
CHAPTER_CARD = 5.5


# ----------------------------------------------------------------------------- planning
def plan(vo_dir, media_dir):
    import script
    import shots
    resolver = shots.Resolver(media_dir)
    durs = json.load(open(os.path.join(vo_dir, "durations.json")))
    items, audio, subs, sections, overlays, chapters = [], [], [], [], [], []
    t = 0.0
    prev_ch = None
    sec_start = 0.0
    for b in script.BEATS:
        ch = b["ch"]
        if ch != prev_ch:
            if prev_ch is not None:
                sections.append((sec_start, t, prev_ch))
            sec_start = t
            info = script.CHAPTERS.get(ch)
            if info:
                num, name, years = info
                items.append(dict(t0=t, dur=CHAPTER_CARD + XF, spec=dict(type="anim", name="chapter",
                                                                       kw=dict(num=num, name=name, years=years))))
                chapters.append((t, f"{num}. {name}"))
                t += CHAPTER_CARD
            elif ch == 0:
                chapters.append((0.0, "Prologue"))
            prev_ch = ch
        if b["voice"]:
            d = LEAD + durs[b["id"]] + TAIL + b.get("pause", 0.0)
            audio.append((t + LEAD, os.path.join(vo_dir, b["id"] + ".wav")))
            subs += subtitle_cues(b["text"], t + LEAD, durs[b["id"]])
        else:
            d = b["dur"]
        vis = [v for v in b["vis"] if v != "quote"]
        weights = [1.6 if v.startswith(("anim:", "map:")) else 1.0 for v in vis]
        tw = sum(weights)
        s = t
        for v, wgt in zip(vis, weights):
            sd = d * wgt / tw
            spec = resolver.resolve(v, sd + XF, beat=b)
            items.append(dict(t0=s, dur=sd + XF, spec=spec))
            cap = spec.get("caption")
            if cap:
                overlays.append(dict(t0=s + 0.9, dur=min(6.0, sd - 0.6), spec=dict(type="caption", **cap)))
            tag = spec.get("tag")
            if tag:
                overlays.append(dict(t0=s + 0.4, dur=sd - 0.2, spec=dict(type="tag", text=tag)))
            s += sd
        if "quote" in b["vis"]:
            who = {"H": "G. H. Hardy", "R": "Srinivasa Ramanujan"}.get(b["voice"], "")
            for (qs, qe, txt) in quote_chunks(b["text"], t + LEAD, durs[b["id"]]):
                overlays.append(dict(t0=qs - 0.2, dur=qe - qs + 0.5, spec=dict(type="quote", text=txt, who=who)))
        t += d
    sections.append((sec_start, t, prev_ch))
    total = t + 0.5
    return dict(items=items, audio=audio, subs=subs, sections=sections, overlays=overlays, chapters=chapters,
                total=total, credits=resolver.credits())


def _split_sentences(text):
    return [s for s in re.split(r"(?<=[.;?!])\s+", text.strip()) if s]


def subtitle_cues(text, start, dur, maxc=84):
    """Split narration into subtitle cues (<= 2 lines of ~42 chars), timed by character count."""
    pieces = []
    for s in _split_sentences(text):
        if len(s) <= maxc:
            pieces.append(s)
            continue
        words, cur = s.split(), ""
        # split long sentences at commas when possible, else by length
        for w in words:
            if len(cur) + len(w) + 1 > maxc or (cur.endswith(",") and len(cur) > maxc * 0.45):
                pieces.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur:
            pieces.append(cur)
    total = sum(len(p) for p in pieces)
    cues, t = [], start
    for p in pieces:
        d = dur * len(p) / total
        cues.append((t, t + d, p))
        t += d
    return cues


def quote_chunks(text, start, dur, maxc=190):
    sents = _split_sentences(text)
    chunks, cur = [], ""
    for s in sents:
        if cur and len(cur) + len(s) > maxc:
            chunks.append(cur)
            cur = s
        else:
            cur = (cur + " " + s).strip()
    if cur:
        chunks.append(cur)
    total = sum(len(c) for c in chunks)
    out, t = [], start
    for c in chunks:
        d = dur * len(c) / total
        out.append((t, t + d, c))
        t += d
    return out


def srt_time(x):
    ms = int(round(x * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(cues, path):
    with open(path, "w") as f:
        for i, (a, b, txt) in enumerate(cues, 1):
            lines = _two_lines(txt)
            f.write(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{lines}\n\n")


def _two_lines(txt, width=44):
    if len(txt) <= width:
        return txt
    words = txt.split()
    best, best_diff = txt, 1e9
    for k in range(1, len(words)):
        a, b = " ".join(words[:k]), " ".join(words[k:])
        diff = abs(len(a) - len(b))
        if diff < best_diff:
            best, best_diff = a + "\n" + b, diff
    return best


# ----------------------------------------------------------------------------- overlays
def render_overlay(spec):
    """Return (x, y, premultiplied BGRA array) for a static overlay."""
    import skia
    from anims import CREAM, GOLD
    from engine import SANS, SERIF, SERIF_I, draw_text, font, paint, wrap
    kind = spec["type"]
    if kind == "caption":
        w, h = 1100, 170
        s = skia.Surface(w, h)
        c = s.getCanvas()
        c.clear(skia.Color(0, 0, 0, 0))
        c.drawRect(skia.Rect.MakeXYWH(0, 20, 5, 120), paint(GOLD, 0.95))
        draw_text(c, spec["title"], 30, 78, font(SERIF, 54, 600), (250, 245, 235), 1.0, shadow=10)
        if spec.get("sub"):
            draw_text(c, spec["sub"].upper(), 32, 128, font(SANS, 22, 500), GOLD, 1.0, shadow=6, tracking=4)
        return 90, H - 230, s.makeImageSnapshot().toarray()
    if kind == "tag":
        w, h = 1300, 60
        s = skia.Surface(w, h)
        c = s.getCanvas()
        c.clear(skia.Color(0, 0, 0, 0))
        draw_text(c, spec["text"].upper(), 4, 38, font(SANS, 20, 500), (235, 228, 210), 0.85, shadow=6, tracking=4)
        return 70, 52, s.makeImageSnapshot().toarray()
    if kind == "quote":
        s = skia.Surface(W, H)
        c = s.getCanvas()
        c.clear(skia.Color(0, 0, 0, 0))
        c.drawPaint(skia.Paint(Shader=skia.GradientShader.MakeLinear(
            points=[(W * 0.35, 0), (W * 0.62, 0)], colors=[skia.Color(0, 0, 0, 0), skia.Color(5, 5, 8, 215)])))
        f = font(SERIF_I, 50, 400)
        lines = wrap("“" + spec["text"] + "”", f, 760)
        lh = 66
        y0 = H / 2 - len(lines) * lh / 2 + 30
        for i, ln in enumerate(lines):
            draw_text(c, ln, 1080, y0 + i * lh, f, CREAM, 1.0, shadow=8)
        draw_text(c, "— " + spec["who"], 1080, y0 + len(lines) * lh + 40, font(SANS, 26, 500), GOLD, 1.0,
                  tracking=3)
        return 0, 0, s.makeImageSnapshot().toarray()
    raise ValueError(kind)


# ----------------------------------------------------------------------------- rendering
def make_shot(spec):
    import anims
    k = spec["type"]
    if k == "anim":
        return engine.Anim(anims.REGISTRY[spec["name"]], spec["_dur"], **spec.get("kw", {}))
    if k == "photo":
        return engine.Photo(spec["path"], spec["_dur"], z0=spec.get("z0", 1.0), z1=spec.get("z1", 1.12),
                            p0=tuple(spec.get("p0", (0.5, 0.5))), p1=tuple(spec.get("p1", (0.5, 0.5))),
                            tone=spec.get("tone", "sepia"), fit=spec.get("fit"))
    if k == "footage":
        return engine.Footage(spec["path"], spec["_dur"], start=spec.get("start", 0.0),
                              speed=spec.get("speed", 1.0), tone=spec.get("tone", "sepia"),
                              clip_len=spec.get("clip_len"), hflip=spec.get("hflip", False))
    raise ValueError(k)


def render_segment(args):
    idx, f0, f1, plan_path, out_path, enc = args
    P = json.load(open(plan_path))
    items = P["items"]
    ovs = P["overlays"]
    live = {}
    ov_cache = {}
    name, proc = engine.open_encoder(out_path, enc)
    t_start = time.time()
    for fi in range(f0, f1):
        t = fi / FPS
        act = [i for i, it in enumerate(items) if it["t0"] <= t < it["t0"] + it["dur"]]
        for i in list(live):
            if i not in act:
                live.pop(i).close()
        layers = []
        for i in act[-2:]:
            if i not in live:
                spec = dict(items[i]["spec"])
                spec["_dur"] = items[i]["dur"]
                live[i] = make_shot(spec)
            sh = live[i]
            lt = t - items[i]["t0"]
            img = sh.frame(lt)
            if sh.look != "anim":
                img = engine.film_look(img, fi, amount=3.0 if sh.look == "photo" else 2.0)
            layers.append((items[i], img))
        if not layers:
            frame = np.zeros((H, W, 3), np.uint8)
        elif len(layers) == 1:
            frame = layers[0][1]
        else:
            (_, a), (it_b, b) = layers
            k = engine.smooth((t - it_b["t0"]) / XF)
            frame = (a.astype(np.float32) * (1 - k) + b.astype(np.float32) * k).astype(np.uint8)
        for j, ov in enumerate(ovs):
            lt = t - ov["t0"]
            if 0 <= lt < ov["dur"]:
                if j not in ov_cache:
                    ov_cache[j] = render_overlay(ov["spec"])
                x, y, arr = ov_cache[j]
                op = engine.fade_env(lt, ov["dur"], 0.5, 0.5)
                h, w = arr.shape[:2]
                x2, y2 = min(W, x + w), min(H, y + h)
                region = frame[y:y2, x:x2]
                frame = frame.copy() if not frame.flags.writeable else frame
                frame[y:y2, x:x2] = engine.blend_bgra(region, arr[: y2 - y, : x2 - x], op)
        proc.stdin.write(np.ascontiguousarray(frame).tobytes())
        if (fi - f0) % 500 == 0:
            el = time.time() - t_start
            print(f"[seg {idx}] {fi - f0}/{f1 - f0} frames, {el:.0f}s", flush=True)
    for s in live.values():
        s.close()
    proc.stdin.close()
    proc.wait()
    return out_path, name


def mix_audio(P, out_wav, tmp):
    import music
    sr = 24000
    total = P["total"]
    narr = np.zeros(int(total * sr) + sr, np.float32)
    for t, path in P["audio"]:
        a, r = sf.read(path, dtype="float32")
        assert r == sr
        i = int(t * sr)
        narr[i:i + len(a)] += a[: len(narr) - i]
    narr /= max(1e-6, np.abs(narr).max()) / 0.89
    nwav = os.path.join(tmp, "narration_24k.wav")
    sf.write(nwav, narr, sr)
    n48 = os.path.join(tmp, "narration_48k.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", nwav, "-ar", "48000", "-ac", "1", n48], check=True)
    narr48, _ = sf.read(n48, dtype="float32")
    sections = [tuple(s) for s in P["sections"]]
    mus = music.score(sections, total)
    n = min(len(mus), len(narr48))
    mus, narr48 = mus[:n], narr48[:n]
    # duck the music under speech
    env = np.abs(narr48)
    win = int(0.05 * music.SR)
    env = np.convolve(env, np.ones(win) / win, "same")
    speech = (env > 0.01).astype(np.float32)
    att, rel = int(0.35 * music.SR), int(1.2 * music.SR)
    duck = np.zeros_like(speech)
    level = 0.0
    step = 64
    for i in range(0, n, step):  # block-wise attack/release follower
        target = speech[i]
        rate = step / att if target > level else step / rel
        level += (target - level) * min(1.0, rate * 3)
        duck[i:i + step] = level
    gain = 0.55 - 0.40 * duck   # music at ~ -5 dB between lines, ~ -16 dB under speech
    mix = mus * gain[:, None] + narr48[:, None] * 0.92
    mix /= max(1.0, np.abs(mix).max() / 0.97)
    sf.write(out_wav, mix, music.SR, subtype="PCM_24")
    sf.write(os.path.join(tmp, "music_only.wav"), mus, music.SR, subtype="PCM_16")


def write_ffmeta(P, path):
    total_ms = int(P["total"] * 1000)
    ch = P["chapters"]
    with open(path, "w") as f:
        f.write(";FFMETADATA1\ntitle=Ramanujan: The Mind That Reached for Infinity\nartist=Documentary\n"
                "language=eng\ncomment=English documentary on Srinivasa Ramanujan (1887-1920)\n\n")
        for i, (t, name) in enumerate(ch):
            end = int(ch[i + 1][0] * 1000) if i + 1 < len(ch) else total_ms
            f.write(f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={int(t * 1000)}\nEND={end}\ntitle={name}\n\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vo", required=True)
    ap.add_argument("--media", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--encoder", default="auto", choices=["auto", "nvenc", "gpu", "cpu"])
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2)))
    ap.add_argument("--only", default=None, help="render only a time range a:b (seconds) for previews")
    ap.add_argument("--skip-video", action="store_true")
    ap.add_argument("--skip-audio", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    tmp = os.path.join(args.out, "tmp")
    os.makedirs(tmp, exist_ok=True)

    P = plan(args.vo, args.media)
    # credits are the last item; inject the resolved credit lines
    for it in P["items"]:
        if it["spec"].get("name") == "credits":
            it["spec"]["kw"] = dict(lines=P["credits"])
    plan_path = os.path.join(tmp, "plan.json")
    json.dump(P, open(plan_path, "w"), indent=1)
    print(f"timeline: {P['total'] / 60:.2f} min, {len(P['items'])} shots, {len(P['overlays'])} overlays")
    write_srt(P["subs"], os.path.join(args.out, "ramanujan_documentary.en.srt"))
    write_ffmeta(P, os.path.join(tmp, "chapters.ffmeta"))

    enc = "cpu" if args.encoder == "cpu" else args.encoder
    enc_name, _ = engine.encoder_args(enc if enc != "cpu" else "x264")
    print("video encoder:", enc_name)

    nframes = int(P["total"] * FPS)
    f_start, f_end = 0, nframes
    if args.only:
        a, b = map(float, args.only.split(":"))
        f_start, f_end = int(a * FPS), int(b * FPS)
    if not args.skip_video:
        jobs = args.jobs
        bounds = np.linspace(f_start, f_end, jobs + 1).astype(int)
        tasks = [(i, int(bounds[i]), int(bounds[i + 1]), plan_path, os.path.join(tmp, f"seg_{i:02d}.mp4"),
                  enc if enc != "cpu" else "x264") for i in range(jobs)]
        t0 = time.time()
        with mp.get_context("spawn").Pool(jobs) as pool:
            results = pool.map(render_segment, tasks)
        print(f"rendered video in {time.time() - t0:.0f}s with {results[0][1]}")
        with open(os.path.join(tmp, "segments.txt"), "w") as f:
            for p, _ in results:
                f.write(f"file '{os.path.abspath(p)}'\n")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i",
                        os.path.join(tmp, "segments.txt"), "-c", "copy", os.path.join(tmp, "video.mp4")], check=True)
    if not args.skip_audio:
        mix_audio(P, os.path.join(tmp, "mix.wav"), tmp)
    final = os.path.join(args.out, "ramanujan_documentary_1080p.mp4" if not args.only else "preview.mp4")
    audio_args = ["-ss", str(f_start / FPS), "-t", str((f_end - f_start) / FPS)] if args.only else []
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", os.path.join(tmp, "video.mp4")] + audio_args + [
        "-i", os.path.join(tmp, "mix.wav"), "-i", os.path.join(args.out, "ramanujan_documentary.en.srt"),
        "-i", os.path.join(tmp, "chapters.ffmeta"),
        "-map", "0:v", "-map", "1:a", "-map", "2:s", "-map_metadata", "3", "-map_chapters", "3",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-c:s", "mov_text",
        "-metadata:s:a:0", "language=eng", "-metadata:s:s:0", "language=eng", "-metadata:s:s:0", "title=English",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-movflags", "+faststart", "-shortest", final]
    subprocess.run(cmd, check=True)
    print("wrote", final)


if __name__ == "__main__":
    main()
