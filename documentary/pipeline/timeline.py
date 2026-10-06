"""Build build/timeline.json from the narration timings and the edit decision list (edl_<lang>.py).

EDL items:
  ("music", mood)                       start a score section here
  ("sfx", kind)                         one-off sound effect here
  ("card", shot)                        full-screen shot with its own fixed duration (no narration)
  ("seg", id, [shots], extra_seconds)   shots that play under narration segment <id>

Shot timing inside a segment: shots with "fixed" keep that length; a shot with
"at_word": "<word>" starts exactly when that word is spoken (cut on the word); the
remaining time is shared by weight "w". Overlays may also use "word" instead of "t0".
Word times come from build/voice/alignment.json when available (ElevenLabs), otherwise
they are estimated from the character position in the segment.
"""
import importlib, json, os, re, sys
from common import BUILD

HERE = os.path.dirname(os.path.abspath(__file__))
LANG = os.environ.get("DOC_LANG", "cs")
VOICE = os.path.join(BUILD, "voice")
LEAD = 0.2       # silence before a line starts
GAP = 0.35       # breath after each line


def P(key, w=1.0, **kw):          # still photograph
    return dict(type="photo", key=key, w=w, **kw)


def V(key, t_in, w=1.0, **kw):    # archive film
    return dict(type="video", key=key, t_in=t_in, w=w, **kw)


def A(anim, fixed=None, w=1.0, **params):   # motion graphic
    shot = dict(type="anim", anim=anim, w=w, params=params)
    if fixed:
        shot["fixed"] = fixed
    return shot


def word_time(seg_text, dur, word, align=None):
    """Seconds from segment start at which <word> is spoken."""
    i = seg_text.find(word)
    if i < 0:
        i = seg_text.lower().find(word.lower())
    if i < 0:
        raise KeyError(f"word {word!r} not in: {seg_text[:60]}")
    if align and "chars" in align:
        # ElevenLabs alignment: list of (char, start, end) over the spoken text
        return align["starts"][min(i, len(align["starts"]) - 1)]
    # estimate: speech time is roughly proportional to letters, pauses at punctuation
    def weight(s):
        return len(re.sub(r"[^\w]", "", s)) + 6 * len(re.findall(r"[.!?]", s)) + 3 * len(re.findall(r"[,;:–]", s))
    return dur * weight(seg_text[:i]) / max(1, weight(seg_text))


def build():
    edl = importlib.import_module(f"edl_{LANG}").EDL
    segs = {s["id"]: s for s in json.load(open(os.path.join(HERE, f"narration_{LANG}.json")))["segments"]}
    durs = json.load(open(os.path.join(VOICE, "durations.json")))
    align_path = os.path.join(VOICE, "alignment.json")
    aligns = json.load(open(align_path)) if os.path.exists(align_path) else {}
    t = 0.0
    shots, narration, music, sfx = [], [], [], []
    for item in edl:
        kind = item[0]
        if kind == "music":
            music.append({"t": round(t, 3), "mood": item[1]})
            continue
        if kind == "sfx":
            sfx.append({"t": round(t, 3), "kind": item[1], **(item[2] if len(item) > 2 else {})})
            continue
        if kind == "card":
            s = dict(item[1])
            s["dur"] = s.pop("fixed")
            s.pop("w", None)
            s["start"] = t
            shots.append(s)
            t += s["dur"]
            continue
        _, sid, plan = item[:3]
        extra = item[3] if len(item) > 3 else 0.0
        text, dur = segs[sid]["text"], durs[sid]
        seg_start = t
        seg_dur = LEAD + dur + GAP + extra
        narration.append({"id": sid, "start": round(t + LEAD, 3), "dur": round(dur, 3)})
        wt = lambda w: LEAD + word_time(text, dur, w, aligns.get(sid))
        # split the segment into blocks at "at_word" anchors, share time by weight inside each block
        anchors = [0.0] + [wt(s["at_word"]) for s in plan[1:] if s.get("at_word")] + [seg_dur]
        if any(b <= a for a, b in zip(anchors, anchors[1:])):
            raise ValueError(f"{sid}: cut words out of order: {[s.get('at_word') for s in plan]}")
        blocks, cur = [], []
        for i, s in enumerate(plan):
            if i > 0 and s.get("at_word"):
                blocks.append(cur)
                cur = []
            cur.append(s)
        blocks.append(cur)
        for bi, block in enumerate(blocks):
            b_len = anchors[bi + 1] - anchors[bi]
            fixed = sum(s.get("fixed") or 0 for s in block)
            flex = [s for s in block if not s.get("fixed")]
            rest = max(0.0, b_len - fixed)
            wsum = sum(s["w"] for s in flex) or 1
            stretch = (b_len - fixed) if not flex else 0.0
            for j, s in enumerate(block):
                s = json.loads(json.dumps(s))
                d = s.pop("fixed", None) or rest * s["w"] / wsum
                if not flex and j == len(block) - 1:
                    d += max(0.0, stretch)
                s.pop("w", None)
                s.pop("at_word", None)
                s.setdefault("trans", "cut")  # inside narration, cut on the word unless told otherwise
                s["dur"] = d
                s["start"] = t
                for o in s.get("overlays", []):
                    if "word" in o:
                        o["t0"] = round(seg_start + wt(o.pop("word")) - t, 3)
                        o.setdefault("t1", o["t0"] + o.pop("hold", 2.2))
                shots.append(s)
                t += d
    total = t
    shots = subdivide(shots)
    sfx += auto_sfx(shots)
    for i, s in enumerate(shots):
        s["id"] = i
    return {"duration": total, "shots": shots, "narration": narration, "music": music,
            "sfx": sorted(sfx, key=lambda x: x["t"])}


CLIP_LEN = {"rds1_site": 185, "crossroads_hd": 642, "hiroshima_dmg": 912, "truman_1945": 217,
            "october_1937": 721, "anthracite": 534, "trinity": 12.9, "jachymov_valley": 12.5}
# punch-in windows used to cover a long still with several "camera set-ups"
PUNCH = [((0.5, 0.5), 1.0, 1.08), ((0.36, 0.42), 1.45, 1.55), ((0.64, 0.58), 1.5, 1.62),
         ((0.5, 0.35), 1.7, 1.8), ((0.42, 0.62), 1.35, 1.45)]


def subdivide(shots, max_len=3.0, piece=2.4):
    """Split long stills/films into ~2.4 s pieces so the picture changes every 1.5-3 s."""
    out = []
    for s in shots:
        d = s["dur"]
        long_clip = s["type"] == "video" and CLIP_LEN.get(s["key"], 0) > 40
        if s["type"] not in ("photo", "video") or d <= max_len or (s["type"] == "video" and not long_clip) \
                or s.get("no_split"):
            out.append(s)
            continue
        n = max(2, round(d / piece))
        step = d / n
        for k in range(n):
            q = json.loads(json.dumps(s))
            q["start"] = s["start"] + k * step
            q["dur"] = step if k < n - 1 else d - k * step
            a0, a1 = k * step, k * step + q["dur"]
            ovs = []
            for o in s.get("overlays", []):
                o = dict(o)
                if o["kind"] in ("illustrative",):
                    ovs.append(o)
                    continue
                if o["kind"] == "tag" and k > 0:
                    continue
                t0, t1 = o.get("t0", 0.0), o.get("t1", 99.0)
                if t1 <= a0 or t0 >= a1:
                    continue
                o["t0"], o["t1"] = round(t0 - a0, 3), round(t1 - a0, 3)
                ovs.append(o)
            q["overlays"] = ovs
            q["shake"] = [h - a0 for h in s.get("shake", []) if a0 <= h < a1]
            if k > 0:
                q["trans"], q["td"] = "cut", 0.0
                if s["type"] == "photo":
                    (cx, cy), z0, z1 = PUNCH[k % len(PUNCH)]
                    q.pop("fit", None)
                    q.update(c0=[cx, cy], c1=[cx + 0.02, cy - 0.01], z0=z0, z1=z1)
                else:
                    q["t_in"] = s["t_in"] + k * (step * s.get("speed", 1.0) + 5.0)
            elif s["type"] == "photo" and s.get("fit") is None:
                q["z1"] = q.get("z0", 1.0) + (q.get("z1", 1.12) - q.get("z0", 1.0)) * 0.6
            out.append(q)
    return out


def auto_sfx(shots):
    """Sound design that follows the picture: whooshes on whips, hits on stamps and flashes."""
    out = []
    for s in shots:
        t0, tr = s["start"], s.get("trans", "dissolve")
        if s.get("sfx"):
            out.append({"t": t0, "kind": s["sfx"]})
        if tr in ("whip", "whip_l", "zoom"):
            out.append({"t": t0 + s.get("td", 0.5) / 2, "kind": "whoosh", "dur": 0.55})
        elif tr == "flash":
            out.append({"t": t0 + s.get("td", 0.4) / 2, "kind": "impact"})
        elif tr == "glitch":
            out.append({"t": t0 + s.get("td", 0.4) / 2, "kind": "glitch"})
        elif tr == "burn":
            out.append({"t": t0 + s.get("td", 0.8) / 2, "kind": "whoosh_soft", "dur": 0.9})
        for h in s.get("shake", []):
            out.append({"t": t0 + h, "kind": "impact"})
        for o in s.get("overlays", []):
            if o["kind"] == "words" and o.get("style") == "stamp":
                out.append({"t": t0 + o["t0"] + 0.12, "kind": "stamp"})
            elif o["kind"] == "words" and o.get("style") == "big" and o.get("hit", True):
                out.append({"t": t0 + o["t0"], "kind": "impact"})
            elif o["kind"] == "words" and o.get("style") == "type":
                out.append({"t": t0 + o["t0"], "kind": "typewriter", "dur": len(o["text"]) / o.get("cps", 26)})
            elif o["kind"] == "countdown":
                for k in range(o.get("from", 5)):
                    out.append({"t": t0 + o.get("t0", 0) + k * o.get("step", 1.0), "kind": "tick"})
            elif o["kind"] == "dosimeter":
                out.append({"t": t0 + o.get("t0", 0.3), "kind": "geiger", "dur": min(s["dur"], o.get("t1", 99)) - o.get("t0", 0.3)})
        a = s.get("anim")
        if a == "chapter2":
            out.append({"t": t0, "kind": "whoosh", "dur": 0.5})
            out.append({"t": t0 + 0.2, "kind": "impact"})
        elif a == "title_slam":
            out.append({"t": t0 + 0.35, "kind": "riser", "dur": 1.6})
            out.append({"t": t0 + 0.35, "kind": "impact_big"})
        elif a == "agreement":
            out.append({"t": t0 + 0.8, "kind": "typewriter", "dur": 4.4})
            out.append({"t": t0 + 0.8 + 170 / 34 + 0.3, "kind": "stamp"})
        elif a == "teletype":
            out.append({"t": t0 + 0.3, "kind": "typewriter", "dur": min(s["dur"] - 0.3, 5.0)})
        elif a == "evidence_board":
            for i in range(len(s["params"].get("items", [])) + len(s["params"].get("cards", []))):
                out.append({"t": t0 + 0.2 + i * 0.35, "kind": "pin"})
        elif a in ("radon", "tower_diagram"):
            start = min(1.0, s["dur"] * 0.3)
            out.append({"t": t0 + start, "kind": "geiger", "dur": s["dur"] - start})
        elif a == "train_route":
            out.append({"t": t0 + 0.8, "kind": "train", "dur": s["dur"] - 0.8})
        elif a == "prisoners":
            out.append({"t": t0, "kind": "wind", "dur": s["dur"]})
        elif a == "dateline" and s["params"].get("lines"):
            n = sum(len(l) for l in s["params"]["lines"])
            out.append({"t": t0 + 0.4, "kind": "typewriter", "dur": n / 22 + 0.3})
    return out


def credits_pages(tl):
    cred_path = os.path.join(BUILD, "assets", "credits.json")
    meta = json.load(open(cred_path)) if os.path.exists(cred_path) else {}
    used = []
    for s in tl["shots"]:
        keys = [s.get("key")] + [s.get("params", {}).get(k) for k in ("left", "right")]
        keys += [it[0] for it in s.get("params", {}).get("items", [])]
        for k in keys:
            if k and k not in used:
                used.append(k)
    lines = []
    for k in used:
        m = meta.get(k, {})
        title = (m.get("title") or k).replace("File:", "")
        artist = (m.get("artist") or "").replace("\n", " ").strip()
        artist = artist.replace("AnonymousUnknown author", "Unknown author").replace("Unknown authorUnknown author", "Unknown author")
        lic = m.get("license") or ""
        lines.append(f"{title} — {artist + ', ' if artist else ''}{lic}, Wikimedia Commons")
    third = (len(lines) + 2) // 3
    return [
        ("Uran pro Stalina", [
            "Scénář, střih a grafika: otevřené nástroje (pipeline v tomto repozitáři)",
            "Hudba a zvuky: původní syntetizovaná hudba",
            "Mapy: Natural Earth (volné dílo)",
            "Písma: Big Shoulders Stencil, Big Shoulders, Source Serif 4, Special Elite, Courier Prime, IBM Plex Sans, Playfair Display (SIL OFL / Apache-2.0)",
            "Prameny: Český rozhlas (radio.cz); politicalprisoners.eu; Platforma evropské paměti a svědomí; Wilson Center CWIHP; dějiny sovětského atomového projektu",
            "Počty vězňů a vytěženého uranu jsou odhady historiků. Ilustrační záběry jsou v obraze označeny.",
        ]),
        ("Archivní záběry a fotografie (1/3)", lines[:third]),
        ("Archivní záběry a fotografie (2/3)", lines[third:2 * third]),
        ("Archivní záběry a fotografie (3/3)", lines[2 * third:]),
    ]


if __name__ == "__main__":
    tl = build()
    for s in tl["shots"]:
        if s.get("anim") == "credits_roll":
            s["params"]["pages"] = credits_pages(tl)
    out = os.path.join(BUILD, "timeline.json")
    json.dump(tl, open(out, "w"), indent=1, ensure_ascii=False)
    m, s = divmod(tl["duration"], 60)
    durs = [x["dur"] for x in tl["shots"]]
    print(f"timeline: {len(tl['shots'])} shots, {int(m)}:{s:04.1f}, median shot {sorted(durs)[len(durs)//2]:.1f}s")
