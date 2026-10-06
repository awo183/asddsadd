"""Resolve the script's visual cues (photo:*, footage:*, anim:*, map:*) to concrete shot specs.

Media come from MEDIA_DIR/manifest.json (Wikimedia Commons files with author + license).
Each cue lists filename keywords in order of preference; candidates are rotated so repeated
cues show different material, and every cue has a fallback so gaps never break the build.
"""
import glob
import hashlib
import json
import os
import random

PHOTO_KEYS = {
    "hardy": ["hardy"],
    "ramanujan_portrait": ["ramanujan_portrait", "ramanujan_passport_photo_1913"],
    "ramanujan_portrait2": ["ramanujan_passport", "ramanujan_seated", "ramanujan_portrait"],
    "kumbakonam_temple": ["sarangapani_temple", "kumbakonam_temple", "kumbakonam_mahamaham", "temple"],
    "ramanujan_house": ["ramanujan_house_exterior", "ramanujan_house", "sarangapani_temple_street"],
    "ramanujan_house2": ["ramanujan_house_courtyard", "ramanujan_bedroom", "ramanujan_home"],
    "school": ["town_high_school", "school"],
    "carr_synopsis": ["carr", "synopsis"],
    "notebook": ["notebook", "manuscript", "squaring", "letter", "signature"],
    "college": ["government_arts_college", "government_college", "college_kumbakonam"],
    "pachaiyappa": ["pachaiyappa"],
    "janaki": ["janaki"],
    "ramachandra_rao": ["ramachandra_rao", "ananda_rau"],
    "madras_port": ["madras_port", "chennai_port", "madras_harbour", "harbour", "port"],
    "francis_spring": ["francis_spring", "madras_port", "chennai_port"],
    "trinity_great_court": ["trinity_great_court", "great_court", "trinity_gate", "trinity"],
    "trinity": ["trinity_nevile", "trinity_wren", "trinity_chapel", "trinity", "cambridge"],
    "littlewood": ["littlewood"],
    "neville": ["neville"],
    "whewell": ["whewell", "trinity"],
    "ramanujan_cambridge_group": ["senate_house", "ramanujan_group", "ramanujan_with"],
    "cambridge_war": ["first_eastern", "cambridge_war", "cambridge_hospital", "war_cambridge", "ww1", "war"],
    "illness": ["matlock", "putney", "colinette", "fitzroy", "nursing", "sanatorium"],
    "matlock": ["matlock", "sanatorium"],
    "putney": ["putney", "colinette", "blue_plaque"],
    "royal_society": ["royal_society", "burlington"],
    "wren_library": ["wren_library", "wren", "trinity_library"],
    "legacy": ["statue", "stamp", "bust", "museum", "mathematics_day", "125"],
}

FOOTAGE_KEYS = {
    "india_period": ["film_india", "india_19", "india"],
    "madras": ["madras", "chennai", "film_india"],
    "ship": ["ship", "liner", "steamer", "steamship", "voyage", "harbour"],
    "cambridge": ["cambridge", "trinity", "punt", "river_cam"],
    "war": ["war", "ww1", "wwi", "soldier", "troops", "recruit", "zeppelin"],
    "armistice": ["armistice", "victory", "peace", "war"],
    "london": ["london"],
    "london_taxi": ["taxi", "cab", "london_street", "london"],
    "london_dark": ["london_night", "night", "london"],
}

FALLBACK = {
    "photo:ramanujan_portrait2": "photo:ramanujan_portrait",
    "photo:school": "footage:india_period",
    "photo:carr_synopsis": "anim:formula_wall",
    "photo:notebook": "anim:slate",
    "photo:college": "footage:india_period",
    "photo:pachaiyappa": "footage:madras",
    "photo:janaki": "photo:ramanujan_house2",
    "photo:ramachandra_rao": "anim:slate",
    "photo:madras_port": "footage:madras",
    "photo:francis_spring": "footage:madras",
    "photo:littlewood": "footage:cambridge",
    "photo:neville": "footage:ship",
    "photo:whewell": "photo:trinity",
    "photo:trinity_great_court": "footage:cambridge",
    "photo:trinity": "footage:cambridge",
    "photo:cambridge_war": "footage:war",
    "photo:illness": "footage:london",
    "photo:matlock": "photo:illness",
    "photo:putney": "photo:illness",
    "photo:royal_society": "photo:ramanujan_portrait",
    "photo:wren_library": "photo:trinity",
    "photo:legacy": "photo:ramanujan_house",
    "photo:kumbakonam_temple": "footage:india_period",
    "photo:ramanujan_house2": "photo:ramanujan_house",
    "photo:ramanujan_cambridge_group": "photo:trinity",
    "photo:hardy": "anim:formula_wall",
    "footage:madras": "footage:india_period",
    "footage:armistice": "footage:war",
    "footage:london_taxi": "footage:london",
    "footage:london_dark": "footage:london",
    "footage:london": "footage:war",
    "footage:war": "photo:cambridge_war",
    "footage:ship": "photo:madras_port",
    "footage:cambridge": "photo:trinity_great_court",
    "footage:india_period": "photo:kumbakonam_temple",
}

ANIM_ALIAS = {"map:erode": "map_erode", "map:voyage": "map_voyage", "map:return": "map_return"}

# Optional per-file on-screen captions (lower thirds) and archive tags, keyed by local filename stem.
# Filled from the manifest review; anything missing simply gets no caption.
CAPTIONS = {}
TAGS = {}

LETTER_1913 = ("Madras, 16th January 1913", None)
LETTER_1920 = ("Madras, 12th January 1920",
               r"f(q)=1+\frac{q}{(1+q)^2}+\frac{q^4}{(1+q)^2(1+q^2)^2}+\cdots")


class Resolver:
    def __init__(self, media_dir):
        self.media_dir = media_dir
        mpath = os.path.join(media_dir, "manifest.json")
        self.meta = {}
        if os.path.exists(mpath):
            for m in json.load(open(mpath)):
                self.meta[os.path.normpath(m["local"])] = m
        self.photos = sorted(glob.glob(os.path.join(media_dir, "photos", "*")))
        self.videos = sorted(glob.glob(os.path.join(media_dir, "video", "*")))
        # only use files with a recorded free license when a manifest exists
        if self.meta:
            ok = lambda p: os.path.relpath(p, media_dir) in self.meta
            self.photos = [p for p in self.photos if ok(p)]
            self.videos = [p for p in self.videos if ok(p)]
        self.excluded = set()
        self.uses = {}
        self.clip_pos = {}
        self.used = []
        self.seen_caption = set()

    # -------------------------------------------------------------- helpers
    def _match(self, files, keys):
        out = []
        for k in keys:
            for f in files:
                stem = os.path.splitext(os.path.basename(f))[0].lower()
                if k in stem and f not in out and f not in self.excluded:
                    out.append(f)
        return out

    def _pick(self, cands):
        # least-used first, keeping keyword preference order as tie-break
        best = min(cands, key=lambda f: (self.uses.get(f, 0), cands.index(f)))
        self.uses[best] = self.uses.get(best, 0) + 1
        if best not in self.used:
            self.used.append(best)
        return best

    def _duration(self, f):
        m = self.meta.get(os.path.relpath(f, self.media_dir), {})
        if m.get("duration_s"):
            return float(m["duration_s"])
        import subprocess
        try:
            out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                 capture_output=True, text=True).stdout
            return float(out.strip())
        except Exception:
            return 10.0

    # -------------------------------------------------------------- main
    def resolve(self, key, dur, beat=None, depth=0):
        kind, name = key.split(":", 1)
        seed = int(hashlib.md5(f"{key}{beat['id'] if beat else ''}".encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        if kind in ("anim", "map"):
            aname = ANIM_ALIAS.get(key, name)
            kw = {}
            if aname == "title":
                import script
                kw = dict(title=script.TITLE, subtitle=script.SUBTITLE)
            elif aname == "letter_text":
                kw = dict(text=beat["text"], header=LETTER_1913[0])
            elif aname == "letter_mock":
                kw = dict(text=beat["text"], header=LETTER_1920[0], formula_tex=LETTER_1920[1])
            return dict(type="anim", name=aname, kw=kw)
        if kind == "photo":
            cands = self._match(self.photos, PHOTO_KEYS.get(name, [name]))
            if not cands:
                return self._fallback(key, dur, beat, depth)
            f = self._pick(cands)
            stem = os.path.splitext(os.path.basename(f))[0]
            # gentle, varied Ken Burns move
            zin = rng.random() < 0.65
            z0, z1 = (1.0, 1.10 + rng.random() * 0.06) if zin else (1.14 + rng.random() * 0.04, 1.0)
            p0 = (0.5 + rng.uniform(-0.25, 0.25), 0.4 + rng.uniform(-0.2, 0.2))
            p1 = (0.5 + rng.uniform(-0.25, 0.25), 0.4 + rng.uniform(-0.2, 0.2))
            m = self.meta.get(os.path.relpath(f, self.media_dir), {})
            modern = any(x in (m.get("date") or "") for x in ("200", "201", "202"))
            spec = dict(type="photo", path=os.path.abspath(f), z0=z0, z1=z1, p0=p0, p1=p1,
                        tone="warm" if modern else "sepia")
            if stem in CAPTIONS and stem not in self.seen_caption:
                self.seen_caption.add(stem)
                t, s = CAPTIONS[stem]
                spec["caption"] = dict(title=t, sub=s)
            return spec
        if kind == "footage":
            cands = self._match(self.videos, FOOTAGE_KEYS.get(name, [name]))
            if not cands:
                return self._fallback(key, dur, beat, depth)
            f = self._pick(cands)
            stem = os.path.splitext(os.path.basename(f))[0]
            L = self._duration(f)
            pos = self.clip_pos.get(f, rng.uniform(0, max(0.0, L * 0.3)))
            if pos + dur > L - 0.5:
                pos = 0.0 if dur < L else 0.0
            self.clip_pos[f] = pos + dur
            m = self.meta.get(os.path.relpath(f, self.media_dir), {})
            modern = any(x in (m.get("date") or "") for x in ("199", "200", "201", "202"))
            speed = 1.0 if dur <= L else max(0.6, L / dur)
            spec = dict(type="footage", path=os.path.abspath(f), start=pos, speed=speed, clip_len=L,
                        tone="warm" if modern else "sepia")
            if stem in TAGS:
                spec["tag"] = TAGS[stem]
            return spec
        raise ValueError(key)

    def _fallback(self, key, dur, beat, depth):
        nxt = FALLBACK.get(key, "anim:formula_wall")
        if depth > 4:
            nxt = "anim:formula_wall"
        return self.resolve(nxt, dur, beat, depth + 1)

    def credits(self):
        import script
        lines = [("h", script.TITLE.title() + ": " + script.SUBTITLE), ("sp", ""),
                 ("s", "WRITTEN, ANIMATED AND ASSEMBLED"), ("t", "Generated with Claude Code"), ("sp", ""),
                 ("s", "VOICES"), ("t", "Synthesized with Kokoro-82M (Apache-2.0), voices af_heart, bm_george, am_michael"),
                 ("t", "Quotations from Ramanujan's letters (1913, 1920) and G. H. Hardy's writings"), ("sp", ""),
                 ("s", "MUSIC"), ("t", "Original procedural score (tanpura drone, strings, bells)"), ("sp", ""),
                 ("s", "MAPS"), ("t", "Natural Earth (public domain)"), ("sp", ""),
                 ("s", "FONTS"), ("t", "Cormorant Garamond, EB Garamond, Spectral, Inter, Homemade Apple, Special Elite"),
                 ("sp", ""), ("s", "ARCHIVAL PHOTOGRAPHS AND FILM"),
                 ("t", "Wikimedia Commons. Archive film shows the era and places, not Ramanujan himself: "
                       "no moving footage of Ramanujan is known to exist.")]
        for f in self.used:
            m = self.meta.get(os.path.relpath(f, self.media_dir))
            if not m:
                continue
            title = m.get("title", os.path.basename(f)).replace("File:", "")
            author = (m.get("author") or "Unknown author").strip()
            if len(author) > 70:
                author = author[:67] + "..."
            lines.append(("t", f"{title} — {author} — {m.get('license', '')}"))
        lines += [("sp", ""), ("s", "FURTHER READING"),
                  ("t", "G. H. Hardy, Ramanujan: Twelve Lectures on Subjects Suggested by His Life and Work (1940)"),
                  ("t", "Robert Kanigel, The Man Who Knew Infinity (1991)"),
                  ("t", "B. C. Berndt & R. A. Rankin, Ramanujan: Letters and Commentary (1995)"),
                  ("sp", ""), ("sp", ""), ("h", "In memory of Srinivasa Ramanujan, 1887 – 1920")]
        return lines
