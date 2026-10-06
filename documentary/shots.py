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
    "kumbakonam_temple": ["kumbakonam_mahamaham_festival_1909", "kumbakonam_sarangapani_temple_towers",
                          "kumbakonam_sarangapani_gopuram_street", "kumbakonam_potramarai_tank",
                          "kumbakonam_mahamaham_tank", "sarangapani_temple"],
    "kaveri": ["kumbakonam_kaveri"],
    "ramanujan_house": ["ramanujan_house_exterior", "ramanujan_home_2007", "ramanujan_house", "sarangapani_temple_street"],
    "ramanujan_house2": ["ramanujan_house_courtyard", "ramanujan_bedroom", "kumbakonam_house_well", "kumbakonam_house_roof"],
    "school": ["town_high_school", "school"],
    "house_interior": ["kumbakonam_house_museum_hall"],
    "erode_birthplace": ["erode_ramanujan_birthplace"],
    "carr_synopsis": ["carr", "synopsis"],
    "notebook": ["ramanujan_notebook", "manuscript", "squaring"],
    "college": ["government_arts_college", "government_college", "college_kumbakonam"],
    "pachaiyappa": ["pachaiyappa"],
    "janaki": ["janaki"],
    "ramachandra_rao": ["ramachandra_rao"],
    "madras_port": ["madras_harbour_1913", "madras_view_from_harbour", "madras_city_and_harbour",
                    "madras_harbour_locomotive", "madras_catamaran", "madras_port", "chennai_port"],
    "madras_city": ["madras_high_court_1913", "madras_esplanade", "madras_marina", "madras_general_post_office",
                    "madras_central_station", "madras_blacktown_street", "madras_egmore", "madras_public_buildings",
                    "madras_street_view"],
    "francis_spring": ["francis_spring", "madras_harbour_locomotive", "madras_city_and_harbour"],
    "trinity_great_court": ["trinity_great_court_photochrom", "trinity_great_gate_1897", "trinity_great_court_fountain",
                            "trinity_great_court_modern", "trinity_great_court_drone"],
    "trinity": ["trinity_neviles_court_arches_1915", "trinity_wren_library_exterior", "trinity_bridge_wren",
                "cambridge_senate_house_caius_1910", "trinity_great_gate_2019", "trinity_chapel",
                "cambridge_senate_house_caius_photochrom", "trinity_neviles_court_wren_library_modern"],
    "littlewood": ["littlewood"],
    "neville": ["neville"],
    "nevasa": ["ss_nevasa"],
    "whewell": ["whewell"],
    "ramanujan_cambridge_group": ["senate_house_cambridge", "ramanujan_group", "ramanujan_with"],
    "cambridge_war": ["cadets_drilling", "first_eastern_general_hospital_staff", "cloisters_military_hospital",
                      "trinity_great_court_soldiers", "cambridge_kings_parade_ww1", "trinity_great_court_church_parade",
                      "trinity_cloister_soldiers", "cambridge_cadets_at_lunch", "trinity_great_court_cadets_fountain",
                      "trinity_neviles_court_cloister_cadets", "first_eastern"],
    "illness": ["matlock_smedleys_hydro_historic", "london_fitzroy_square_2007", "matlock", "fitzroy"],
    "matlock": ["matlock_smedleys_hydro_historic", "matlock"],
    "putney": ["putney", "colinette", "blue_plaque"],
    "royal_society": ["london_burlington_house_piccadilly", "royal_society", "burlington"],
    "wren_library": ["trinity_wren_library_interior_1902", "trinity_wren_library_interior", "wren"],
    "legacy": ["ramanujan_bust_tirupati", "ramanujan_bust_kolkata", "kumbakonam_house_museum_bust",
               "sastra_ramanujan_statue", "sastra_ramanujan_museum", "stamp"],
}

FOOTAGE_KEYS = {
    "india_period": ["film_india_street_1906", "film_varanasi", "film_delhi_great_capital", "film_ruins_of_delhi",
                     "film_delhi_durbar", "mea_temple_procession", "mea_village"],
    "kumbakonam": ["mea_temple_tank", "mea_temple_procession"],
    "madras": ["madras"],
    "notebook": ["mea_notebook_cover", "mea_notebook_pages"],
    "journal": ["mea_journal", "mea_journal_formulas"],
    "reporter": ["mea_reporter"],
    "ship": ["film_lusitania_departing", "film_lusitania_passengers", "film_suez"],
    "suez": ["film_suez", "film_lusitania_departing"],
    "cambridge": ["mea_trinity_court", "mea_trinity_fountain", "mea_trinity_arms", "mea_cambridge_building"],
    "war": ["film_london_streets_1917", "film_southwark_london_1917", "ww1", "soldier", "troops", "zeppelin"],
    "armistice": ["armistice", "film_london_streets_1917"],
    "london": ["film_london_1912", "film_london_street_scenes_1903", "film_southwark_london_1917",
               "film_london_traffic", "film_london_streets_1917"],
    "london_taxi": ["film_london_traffic", "film_london_1912", "film_london_street_scenes_1903"],
    "london_dark": ["film_southwark_london_1917", "film_london_streets_1917", "film_london_1912"],
}

FALLBACK = {
    "photo:ramanujan_portrait2": "photo:ramanujan_portrait",
    "photo:school": "footage:india_period",
    "photo:carr_synopsis": "anim:formula_wall",
    "photo:notebook": "anim:slate",
    "photo:college": "footage:india_period",
    "photo:pachaiyappa": "photo:madras_city",
    "photo:janaki": "photo:house_interior",
    "photo:house_interior": "photo:ramanujan_house2",
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
    "photo:putney": "footage:london",
    "photo:kaveri": "footage:kumbakonam",
    "photo:nevasa": "footage:ship",
    "footage:suez": "footage:ship",
    "photo:royal_society": "photo:ramanujan_portrait",
    "photo:wren_library": "photo:trinity",
    "photo:legacy": "photo:ramanujan_house",
    "photo:kumbakonam_temple": "footage:india_period",
    "photo:ramanujan_house2": "photo:ramanujan_house",
    "photo:ramanujan_cambridge_group": "photo:trinity",
    "photo:hardy": "anim:formula_wall",
    "footage:madras": "photo:madras_city",
    "photo:madras_city": "footage:india_period",
    "footage:armistice": "footage:war",
    "footage:london_taxi": "footage:london",
    "footage:london_dark": "footage:london",
    "footage:london": "footage:war",
    "footage:war": "photo:cambridge_war",
    "footage:ship": "photo:madras_port",
    "footage:cambridge": "photo:trinity_great_court",
    "footage:india_period": "photo:kumbakonam_temple",
    "footage:kumbakonam": "photo:kumbakonam_temple",
    "footage:notebook": "photo:notebook",
    "footage:journal": "anim:slate",
    "footage:reporter": "photo:ramanujan_cambridge_group",
    "photo:erode_birthplace": "footage:india_period",
}


# Clean segments (real places and documents only) from the CC BY 3.0 documentary
# "Srinivasa Ramanujan: The Mathematician & His Legacy" (Ministry of External Affairs, India, 2016).
MEA = "ramanujan_mea_documentary_abridged_2016"
SEGMENTS = {
    "mea_village": (MEA, 80.2, 82.0, "Tamil Nadu countryside \u00b7 today"),
    "mea_notebook_pages": (MEA, 152.0, 156.4, "Ramanujan's notebook \u00b7 original manuscript"),
    "mea_notebook_cover": (MEA, 156.8, 161.9, "Manuscript Book 2 of Srinivasa Ramanujan"),
    "mea_temple_tank": (MEA, 177.8, 182.3, "Temple tank, Kumbakonam \u00b7 today"),
    "mea_temple_procession": (MEA, 182.7, 199.1, "Temple festival, Kumbakonam \u00b7 today"),
    "mea_journal": (MEA, 252.5, 261.9, "Journal of the Indian Mathematical Society"),
    "mea_journal_formulas": (MEA, 262.3, 266.3, "Journal of the Indian Mathematical Society"),
    "mea_trinity_fountain": (MEA, 275.0, 277.7, "Great Court, Trinity College, Cambridge \u00b7 today"),
    "mea_trinity_arms": (MEA, 278.2, 281.5, "Trinity College, Cambridge \u00b7 today"),
    "mea_trinity_court": (MEA, 290.0, 297.2, "Trinity College, Cambridge \u00b7 today"),
    "mea_cambridge_building": (MEA, 297.8, 302.6, "Cambridge \u00b7 today"),
    "mea_reporter": (MEA, 304.8, 308.3, "Cambridge University Reporter, 18 March 1916"),
}

ANIM_ALIAS = {"map:erode": "map_erode", "map:voyage": "map_voyage", "map:return": "map_return"}

# Optional per-file on-screen captions (lower thirds) and archive tags, keyed by local filename stem.
# Filled from the manifest review; anything missing simply gets no caption.
CAPTIONS = {
    "ramanujan_portrait_opc1": ("Srinivasa Ramanujan", "1887 \u2013 1920"),
    "ramanujan_passport_photo_1913": ("Srinivasa Ramanujan", "Passport photograph, 1913"),
    "ramanujan_group_senate_house_cambridge": ("Ramanujan at Cambridge", "Senate House, between 1914 and 1919"),
    "ramanujan_with_ananda_rau_group": ("Ramanujan with K. Ananda Rau and colleagues", "Cambridge, c. 1914 \u2013 1919"),
    "janakiammal_framed_photo_kumbakonam_house": ("Janakiammal", "Ramanujan's wife \u00b7 photograph displayed in his house"),
    "kumbakonam_ramanujan_house_exterior": ("Ramanujan's home, Kumbakonam", "Sarangapani Sannidhi Street \u00b7 today a museum"),
    "erode_ramanujan_birthplace_1": ("Erode, Tamil Nadu", "The house where Ramanujan was born \u00b7 today"),
    "kumbakonam_mahamaham_festival_1909": ("Kumbakonam", "Mahamaham festival, 1909"),
    "kumbakonam_kaveri_river_2015": ("The Kaveri river", "Kumbakonam \u00b7 today"),
    "kumbakonam_kaveri_panorama_2020": ("The Kaveri river", "Kumbakonam \u00b7 today"),
    "hardy_portrait_c1927": ("G. H. Hardy", "1877 \u2013 1947"),
    "littlewood_portrait_1905": ("J. E. Littlewood", "1885 \u2013 1977"),
    "madras_harbour_1913": ("Madras harbour", "1913"),
    "madras_high_court_1913": ("Madras", "High Court, 1913"),
    "ss_nevasa_southampton_1927": ("SS Nevasa", "The ship that carried Ramanujan to England \u00b7 seen in 1927"),
    "trinity_great_court_photochrom_1890s": ("Great Court, Trinity College", "Cambridge, 1890s"),
    "trinity_whewells_court_modern": ("Whewell's Court, Trinity College", "Where Ramanujan lived \u00b7 today"),
    "trinity_great_court_cadets_drilling_ww1_archway": ("Trinity College at war", "Cadets drilling, First World War"),
    "cambridge_first_eastern_general_hospital_staff_ww1": ("First Eastern General Hospital", "Cambridge, First World War"),
    "matlock_smedleys_hydro_historic": ("Smedley's Hydro, Matlock", "Derbyshire"),
    "london_fitzroy_square_2007": ("Fitzroy Square, London", "Site of the Fitzroy House nursing home \u00b7 today"),
    "london_burlington_house_piccadilly_early1900s": ("Burlington House, London", "Home of the Royal Society, early 1900s"),
    "trinity_wren_library_interior_1902": ("The Wren Library, Trinity College", "c. 1902"),
    "ramanujan_notebook_master_theorem_page": ("Ramanujan's notebook", "A page of results"),
    "ramanujan_bust_tirupati_science_centre": ("Ramanujan remembered", "Bust at a science centre, Tirupati"),
}
EXCLUDE = {"janakiammal_framed_photo_kumbakonam_house", "film_bombay_street_scenes_1929"}

# per-photo tone overrides (e.g. a colour-cast photo of a photo)
TONE = {"janakiammal_framed_photo_kumbakonam_house": "sepia"}

# extra zoom to push archive logos (e.g. a corner watermark) out of frame
CLIP_ZOOM = {"film_southwark_london_1917": 1.3, "film_london_traffic_1896_1903": 1.3}

TAGS = {
    "film_india_street_1906": "Archive film \u00b7 India, 1906",
    "film_varanasi_ghats_from_boat_1899": "Archive film \u00b7 Benares (Varanasi), 1899",
    "film_delhi_durbar_1911_kinemacolor": "Archive film \u00b7 Delhi Durbar, 1911 (Kinemacolor)",
    "film_ruins_of_delhi_1910": "Archive film \u00b7 Delhi, 1910",
    "film_delhi_great_capital_1909": "Archive film \u00b7 Delhi, 1909",
    "film_bombay_street_scenes_1929": "Archive film \u00b7 Bombay, 1929",
    "film_lusitania_departing_new_york_1915": "Archive film \u00b7 an ocean liner departs, 1915",
    "film_lusitania_passengers_boarding_1915": "Archive film \u00b7 passengers boarding a liner, 1915",
    "film_suez_canal_1928": "Archive film \u00b7 Suez Canal, 1928",
    "film_london_street_scenes_1903": "Archive film \u00b7 London, 1903",
    "film_london_traffic_1896_1903": "Archive film \u00b7 London traffic, c. 1900",
    "film_london_1912": "Archive film \u00b7 London, 1912",
    "film_southwark_london_1917": "Archive film \u00b7 Southwark, London, 1917",
    "film_london_streets_1917_ww1": "Archive film \u00b7 London in wartime, 1917",
}

LETTER_1913 = ("Madras, 16th January 1913", None)
LETTER_1920 = ("Madras, 12th January 1920",
               r"f(q)=1+\frac{q}{(1+q)^2}+\frac{q^4}{(1+q)^2(1+q^2)^2}+\cdots")


def analyze_clip(path, cache_dir):
    """Detect letterbox/pillarbox crop and per-second usability (not black, not an intertitle). Cached."""
    import subprocess
    import numpy as np
    os.makedirs(cache_dir, exist_ok=True)
    key = hashlib.md5((path + str(os.path.getsize(path))).encode()).hexdigest()
    cpath = os.path.join(cache_dir, f"clip2_{key}.json")
    if os.path.exists(cpath):
        return json.load(open(cpath))
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:format=duration", "-of", "json", path], capture_output=True, text=True)
    info = json.loads(out.stdout)
    w, h = info["streams"][0]["width"], info["streams"][0]["height"]
    dur = float(info["format"]["duration"])
    cd = subprocess.run(["ffmpeg", "-v", "info", "-ss", str(dur * 0.2), "-i", path, "-t", str(min(40, dur * 0.6)),
                         "-vf", "fps=2,cropdetect=limit=28:round=2:reset=0", "-an", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    crops = [l.split("crop=")[-1].strip() for l in cd.splitlines() if "crop=" in l]
    crop = crops[-1] if crops else f"{w}:{h}:0:0"
    cw, ch, cx, cy = map(int, crop.split(":"))
    if cw < w * 0.5 or ch < h * 0.5:  # implausible; keep the full frame
        cw, ch, cx, cy = w, h, 0, 0
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf",
                          f"crop={cw}:{ch}:{cx}:{cy},fps=2,scale=64:36,format=gray", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8)
    n = len(fr) // (64 * 36)
    fr = fr[: n * 64 * 36].reshape(n, 36, 64).astype(np.float32)
    dark = (fr < 32).mean(axis=(1, 2))
    mean = fr.mean(axis=(1, 2))
    std = fr.std(axis=(1, 2))
    good = (dark < 0.6) & (mean > 38) & (mean < 200) & (std > 24)
    # title cards / freeze frames: almost no change over >= 1.5 s
    motion = np.concatenate([[99.0], np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))])
    still = motion < 1.2
    for i in range(len(still)):
        if still[max(0, i - 1):i + 2].all():
            good[max(0, i - 2):i + 3] = False
    # skip opening titles and closing credits
    good[: max(12, int(len(good) * 0.08))] = False
    good[-10:] = False
    res = dict(w=w, h=h, dur=dur, crop=[cw, ch, cx, cy], good=good.astype(int).tolist())
    json.dump(res, open(cpath, "w"))
    return res


def good_runs(a, min_len_s):
    """Return [(start_s, end_s)] runs of usable half-second samples at least min_len_s long."""
    runs, s = [], None
    g = a["good"]
    for i, v in enumerate(g + [0]):
        if v and s is None:
            s = i
        elif not v and s is not None:
            if (i - s) / 2 >= min_len_s + 1.2:
                runs.append((s / 2 + 0.6, i / 2 - 0.6))
            s = None
    return runs


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
        # files whose underlying rights are unclear (e.g. a photo of a privately held portrait) are never used
        self.excluded = {f for f in self.photos + self.videos
                         if os.path.splitext(os.path.basename(f))[0] in EXCLUDE}
        self.uses = {}
        self.clip_pos = {}
        self.used = []
        self.seen_caption = set()

    # -------------------------------------------------------------- helpers
    def _match(self, files, keys):
        out = []
        for k in keys:
            for f in files:
                stem = f[4:] if f.startswith("seg:") else os.path.splitext(os.path.basename(f))[0].lower()
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
            tone = TONE.get(stem, "warm" if modern else "sepia")
            spec = dict(type="photo", path=os.path.abspath(f), z0=z0, z1=z1, p0=p0, p1=p1,
                        tone=tone, contrast=1.0 if modern else 1.05)
            if stem in CAPTIONS and stem not in self.seen_caption:
                self.seen_caption.add(stem)
                t, s = CAPTIONS[stem]
                spec["caption"] = dict(title=t, sub=s)
            return spec
        if kind == "footage":
            pool = [v for v in self.videos if os.path.splitext(os.path.basename(v))[0] != MEA]
            pool += ["seg:" + k for k, (stem, *_r) in SEGMENTS.items()
                     if any(os.path.splitext(os.path.basename(v))[0] == stem for v in self.videos)]
            cands = self._match(pool, FOOTAGE_KEYS.get(name, [name]))
            if not cands:
                return self._fallback(key, dur, beat, depth)
            f = self._pick(cands)
            if f.startswith("seg:"):
                stem, a, b, label = SEGMENTS[f[4:]]
                path = next(v for v in self.videos if os.path.splitext(os.path.basename(v))[0] == stem)
                if path not in self.used:
                    self.used.append(path)
                speed = max(0.5, min(1.0, (b - a) / dur))
                return dict(type="footage", path=os.path.abspath(path), start=a, seg_end=b, speed=speed,
                            tone="warm", contrast=1.0, tag=label)
            stem = os.path.splitext(os.path.basename(f))[0]
            info = analyze_clip(f, os.path.join(os.environ.get("DOC_CACHE", "/tmp"), "clips"))
            # archival film runs slightly slow (silent-era speed); avoid black/intertitle stretches and reuse
            speed = 0.85
            need = dur * speed
            runs = good_runs(info, min(need, 5.0))
            used = self.clip_pos.setdefault(f, [])
            best = None
            for a, b in runs:
                x = a
                for (ua, ub) in sorted(used):
                    if x < ub and min(b, x + need) > ua:
                        x = ub
                if x >= b - 3.0:
                    continue
                cand = (x, min(b, x + need))
                if best is None or cand[1] - cand[0] > best[1] - best[0]:
                    best = cand
                if cand[1] - cand[0] >= need - 0.01:
                    best = cand
                    break
            if best is None:
                best = max(runs, key=lambda r: r[1] - r[0]) if runs else (0.0, info["dur"])
            pos, seg_end = best
            seg_end = min(seg_end, pos + need)
            if seg_end - pos < need:
                speed = max(0.5, (seg_end - pos) / dur)
            used.append((pos, seg_end))
            m = self.meta.get(os.path.relpath(f, self.media_dir), {})
            modern = any(x in (m.get("date") or "") for x in ("199", "200", "201", "202"))
            spec = dict(type="footage", path=os.path.abspath(f), start=pos, seg_end=seg_end, speed=speed,
                        crop=info["crop"], zoom=CLIP_ZOOM.get(stem, 1.08), tone="warm" if modern else "sepia",
                        contrast=1.0 if modern else 1.1)
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
