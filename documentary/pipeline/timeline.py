"""Edit decision list: which pictures play under which line of narration.

Builds build/timeline.json (shots with absolute times, narration placement,
music sections and sound-effect cues) from narration durations.
"""
import json, os, sys
from common import BUILD

VOICE = os.path.join(BUILD, "voice")
PD, BY, BYSA = "Public domain", "CC BY", "CC BY-SA"


def P(key, cap=None, w=1.0, **kw):          # still photograph
    return dict(type="photo", key=key, cap=cap, w=w, **kw)


def V(key, t_in, cap=None, w=1.0, **kw):    # archive film
    return dict(type="video", key=key, t_in=t_in, cap=cap, w=w, **kw)


def A(anim, fixed=None, w=1.0, **params):   # motion graphic
    return dict(type="anim", anim=anim, fixed=fixed, w=w, params=params)


def card(num, name, years):
    return ("card", A("chapter", 3.4, num=num, name=name, years=years))


# Captions: (what it shows, source · licence). Full credits roll at the end.
EDL = [
    ("music", "cold_open"),
    ("seg", "c01", [A("dateline", 4.6, lines=["29 AUGUST 1949 · 07:00", "SEMIPALATINSK TEST SITE · KAZAKH SSR"]),
                    V("rds1_site", 2.0, ("Semipalatinsk test site, Kazakhstan", "Present-day footage · Carl Willis · CC BY 3.0"), trans="black")]),
    ("seg", "c02", [P("rds1_museum", ("RDS-1, the first Soviet atomic bomb", "Museum replica · Wikimedia Commons · CC BY-SA 2.0"),
                      z0=1.0, z1=1.18, c1=(0.45, 0.5)),
                    V("rds1_site", 10.0, None),
                    A("dateline", 1.1, lines=[], flash_at=0.0)]),
    ("sfx", "explosion"),
    ("seg", "c03", [P("rds1_cloud", ("RDS-1 casing", "Polytechnic Museum, Moscow · CC0"), trans="white", td=1.6, z1=1.1),
                    V("hiroshima_dmg", 247.0, ("Hiroshima after the bombing, 1945–46", "U.S. Air Force film · Public domain"), crop="1440:1080:240:0")]),
    ("seg", "c04", [A("map_distance", 9.0),
                    V("jachymov_valley", 0.0, ("Jáchymov, Ore Mountains", "Wikimedia Commons · CC BY-SA 3.0"), speed=0.75)], 0.9),
    ("music", "title"),
    ("card", A("title", 7.5)),

    ("music", "ch1"),
    card("I", "The Valley of Silver", "1516 – 1945"),
    ("seg", "s101", [A("map_zoom_jachymov", w=1)]),
    ("seg", "s102", [P("thaler_obv", ("Joachimsthaler silver coin", "Electrotype copy · Wikimedia Commons · CC BY 2.0"), z0=1.05, z1=1.25),
                     A("etymology", 6.6)]),
    ("seg", "s103", [P("pitchblende2", ("Pitchblende (uraninite)", "Wikimedia Commons · CC BY-SA 3.0"), z0=1.0, z1=1.2),
                     P("svornost_1928", ("Svornost mine, Jáchymov, 1928", "Wikimedia Commons · Public domain"))]),
    ("seg", "s104", [P("curies", ("Pierre and Marie Curie in their laboratory", "Wikimedia Commons · Public domain"), c0=(0.5, 0.4), c1=(0.55, 0.45)),
                     A("elements", 6.0),
                     P("radium_palace_1926", ("Radium Palace spa hotel, Jáchymov, 1926", "Prager Presse · Public domain"))]),
    ("seg", "s105", [P("radium_palace_1949", ("Radium Palace, 1949", "Spa almanac · Public domain"), z1=1.08),
                     A("radon", 8.5)]),
    ("seg", "s106", [P("uran_museum", ("Uranium glass, Royal Mint Museum, Jáchymov", "Wikimedia Commons · CC BY-SA 4.0"), z0=1.0, z1=1.15),
                     P("uran_factory_1922", ("Uranium and radium factory, Jáchymov, 1922", "Prager Presse · Public domain"))], 1.0),

    ("music", "ch2"),
    card("II", "The Race for the Bomb", "1945"),
    ("seg", "s201", [V("truman_1945", 86.0, ("President Truman announces the Hiroshima bomb, 1945", "U.S. National Archives · Public domain")),
                     V("hiroshima_dmg", 475.0, ("Hiroshima, 1945–46", "U.S. Air Force film · Public domain"), crop="1440:1080:240:0"),
                     P("stalin", ("Joseph Stalin", "Official portrait, 1940s · CC0"), fit="contain")]),
    ("seg", "s202", [V("october_1937", 195.0, ("Soviet leaders on the Lenin Mausoleum, 1937", "Soviet newsreel · Public domain"), crop="960:720:160:0"),
                     P("beria", ("Lavrentiy Beria", "NKVD chief · Public domain"), fit="contain"),
                     P("kurchatov_1943", ("Igor Kurchatov, 1943", "Wikimedia Commons · Public domain"), c0=(0.5, 0.35), c1=(0.5, 0.3))]),
    ("seg", "s203", [V("trinity", 0.0, ("Trinity test, New Mexico, July 1945", "U.S. Army film · Public domain")),
                     P("pitchblende", ("Uranium ore", "Wikimedia Commons · CC BY-SA 2.0"), c0=(0.5, 0.35), c1=(0.5, 0.32), z0=1.0, z1=1.12)]),
    ("seg", "s204", [P("svornost_modern", ("Svornost mine, Jáchymov — in use since the 16th century", "Wikimedia Commons · CC BY-SA 4.0")),
                     V("jachymov_valley", 3.0, None, speed=0.75)]),
    ("seg", "s205", [A("agreement", 9.5),
                     P("pitchblende2", ("Pitchblende from the Ore Mountains", "Wikimedia Commons · CC BY-SA 3.0"), z0=1.3, z1=1.1)]),
    ("seg", "s206", [P("gottwald_stalin", ("Communist rally: “With Gottwald we won”", "Czechoslovakia, late 1940s · Public domain"), z0=1.0, z1=1.1)], 1.0),

    ("music", "ch3"),
    card("III", "Ore for Moscow", "1946 – 1949"),
    ("seg", "s301", [P("ortho_eduard_nikolaj", ("Eduard and Nikolaj mines, Jáchymov", "Aerial survey, 1950s · CENIA / GEODIS · CC BY 4.0"), z0=1.0, z1=1.25, c1=(0.4, 0.5)),
                     V("anthracite", 95.0, ("Underground mining in the 1940s (illustrative)", "U.S. Bureau of Mines film · Public domain"))]),
    ("seg", "s302", [V("anthracite", 405.0, ("Loading rail wagons, 1940s (illustrative)", "U.S. Bureau of Mines film · Public domain")),
                     A("train_route", 10.0)]),
    ("seg", "s303", [A("bar_chart", w=1)]),
    ("seg", "s304", [P("pitchblende2", ("Pitchblende", "Wikimedia Commons · CC BY-SA 3.0"), z0=1.1, z1=1.35, c0=(0.3, 0.6), c1=(0.6, 0.4)),
                     A("bar_chart", 6.0)]),
    ("seg", "s305", [A("plutonium_chain", 12.5),
                     P("kurchatov_1943", None, z0=1.25, z1=1.05, c0=(0.5, 0.3)),
                     P("rds1_mockup", ("RDS-1 replica", "Polytechnic Museum, Moscow · CC0"))]),
    ("seg", "s306", [P("rds1_cloud", None, z0=1.15, z1=1.0),
                     P("joe1_map", ("U.S. chart predicting fallout from the Soviet test, 1949", "U.S. government · Public domain"), z0=1.0, z1=1.3, c1=(0.45, 0.4)),
                     V("crossroads_hd", 250.0, ("U.S. nuclear test, Bikini, 1946", "U.S. National Archives · Public domain"), crop="1440:1080:240:0")], 1.0),

    ("music", "ch4"),
    card("IV", "Victorious February", "1948"),
    ("seg", "s401", [P("gottwald", ("Klement Gottwald", "Official portrait · ČTK · Public domain"), fit="contain"),
                     P("gottwald_stalin", None, z0=1.25, z1=1.05, c0=(0.55, 0.3))]),
    ("seg", "s402", [A("timeline_1948", w=1)]),
    ("seg", "s403", [P("gottwald_1951", ("Gottwald with his ministers, 1951", "Wikimedia Commons · Public domain")),
                     P("vojna_05", ("Memorial room, Vojna camp", "Wikimedia Commons · CC BY-SA 3.0"))]),
    ("seg", "s404", [V("october_1937", 316.0, ("Red Square, Moscow, 1937", "Soviet newsreel · Public domain"), crop="960:720:160:0"),
                     P("vojna_02", ("Vojna camp, Příbram", "Wikimedia Commons · CC BY-SA 3.0"))], 1.0),

    ("music", "ch5"),
    card("V", "The Hell of Jáchymov", "1949 – 1961"),
    ("seg", "s501", [A("camp_map", 8.0), A("camp_names", w=1)]),
    ("seg", "s502", [A("prisoners", w=1)]),
    ("seg", "s503", [A("mukl", w=1)]),
    ("seg", "s504", [V("anthracite", 55.0, ("Underground mining (illustrative)", "U.S. Bureau of Mines film · Public domain")),
                     P("ortho_nikolaj", ("Nikolaj mine and labour camp", "Aerial survey, 1950s · CENIA / GEODIS · CC BY 4.0"), z0=1.0, z1=1.3, c1=(0.55, 0.45))]),
    ("seg", "s505", [V("anthracite", 118.0, ("Underground mining (illustrative)", "U.S. Bureau of Mines film · Public domain")),
                     P("ortho_bratrstvi", ("Bratrství mine, Jáchymov", "Aerial survey, 1950s · CENIA / GEODIS · CC BY 4.0"), z0=1.0, z1=1.25)]),
    ("seg", "s506", [P("mauthausen_stairs", ("Memorial sign at the “Mauthausen stairs”", "Svornost camp · Wikimedia Commons · CC BY-SA 4.0"), z0=1.0, z1=1.35, c0=(0.5, 0.5), c1=(0.35, 0.72)),
                     P("svornost_camp", ("Memorial sign, Svornost camp", "Wikimedia Commons · CC BY-SA 4.0"))]),
    ("seg", "s507", [P("elias", ("Memorial cross at the Eliáš camp", "Wikimedia Commons · CC BY-SA 4.0"), fit="contain"),
                     P("nikolaj_05", ("Foundations of the Nikolaj camp", "Wikimedia Commons · CC BY-SA 4.0")),
                     P("ustredni_01", ("Site of the Central camp, Jáchymov", "Wikimedia Commons · CC BY-SA 4.0")),
                     P("rovnost", ("Memorial sign, Rovnost camp", "Wikimedia Commons · CC BY-SA 4.0"))], 1.0),

    ("music", "ch6"),
    card("VI", "The Tower of Death", "Vykmanov · Ostrov"),
    ("seg", "s601", [P("tower_night", ("The Red Tower of Death, Ostrov", "Wikimedia Commons · CC BY 4.0"), z0=1.0, z1=1.12),
                     P("tower_05", None)]),
    ("seg", "s602", [A("tower_diagram", 9.0), V("anthracite", 165.0, ("Ore sorting, 1940s (illustrative)", "U.S. Bureau of Mines film · Public domain")),
                     P("tower_03", ("Inside the Tower of Death", "Wikimedia Commons · CC BY-SA 4.0"))]),
    ("seg", "s603", [P("tower_04", ("“The final workplace of political prisoners of the 1950s destined for liquidation”", "Memorial plaque, 1993 · Wikimedia Commons · CC BY-SA 4.0"), z0=1.0, z1=1.1),
                     P("tower_01", ("Red Tower of Death — national cultural monument", "Wikimedia Commons · CC BY-SA 4.0"))], 1.0),

    ("music", "ch7"),
    card("VII", "Vojna", "Příbram"),
    ("seg", "s701", [P("vojna_01", ("Vojna Memorial near Příbram", "Wikimedia Commons · CC BY-SA 3.0")),
                     P("vojna_02", None), P("vojna_10", None),
                     P("pribram_poster", ("“Příbram uranium mines seek new workers!”", "Recruitment poster · Public domain"), fit="contain")], 1.0),

    ("music", "ch8"),
    card("VIII", "The Price", "1960 – today"),
    ("seg", "s801", [P("vojna_17", ("Vojna Memorial", "Wikimedia Commons · CC BY-SA 3.0")), P("nikolaj_02", ("Site of the Nikolaj camp today", "Wikimedia Commons · CC BY-SA 4.0"))]),
    ("seg", "s802", [A("production_counter", 8.5), P("svornost_modern", None, z0=1.15, z1=1.0)]),
    ("seg", "s803", [P("vojna_19", ("Prisoners’ quarters, Vojna Memorial", "Wikimedia Commons · CC BY-SA 3.0")), P("vojna_28", None)]),
    ("seg", "s804", [P("nikolaj_01", ("“Jáchymov Hell” memorial trail", "Wikimedia Commons · CC BY-SA 4.0"), fit="contain"),
                     V("jachymov_valley", 1.0, None, speed=0.75)]),
    ("seg", "s805", [V("rds1_site", 176.0, None), P("mauthausen_stairs", None, z0=1.2, z1=1.0), P("tower_night", None, z0=1.12, z1=1.0)]),
    ("seg", "s806", [P("thaler_rev", None, z0=1.0, z1=1.18)], 1.6),
    ("music", "end"),
    ("card", A("dedication", 5.5)),
    ("card", A("credits_roll", 20.0, pages=[])),
]

LEAD = 0.25      # silence before a line starts
GAP = 0.45       # breath after each line


def build():
    durs = json.load(open(os.path.join(VOICE, "durations.json")))
    t = 0.0
    shots, narration, music, sfx = [], [], [], []
    pending_trans = None
    for item in EDL:
        kind = item[0]
        if kind == "music":
            music.append({"t": round(t, 3), "mood": item[1]})
            continue
        if kind == "sfx":
            sfx.append({"t": round(t, 3), "kind": item[1]})
            continue
        if kind == "card":
            s = dict(item[1])
            s["dur"] = s.pop("fixed")
            s["start"] = t
            s.setdefault("trans", "black")
            s["td"] = s.get("td", 0.8)
            shots.append(s)
            t += s["dur"]
            continue
        _, sid, plan = item[:3]
        extra = item[3] if len(item) > 3 else 0.0
        seg_dur = LEAD + durs[sid] + GAP + extra
        narration.append({"id": sid, "start": round(t + LEAD, 3), "dur": round(durs[sid], 3)})
        fixed = sum(s.get("fixed") or 0 for s in plan)
        flex = [s for s in plan if not s.get("fixed")]
        rest = max(0.0, seg_dur - fixed)
        wsum = sum(s["w"] for s in flex) or 1
        if not flex:  # all fixed: stretch the last one to fill the line
            plan[-1]["fixed"] = plan[-1]["fixed"] + max(0.0, seg_dur - fixed)
        for s in plan:
            s = dict(s)
            d = s.pop("fixed", None) or rest * s["w"] / wsum
            s.pop("w", None)
            s["dur"] = d
            s["start"] = t
            if s.get("cap") is None:
                s.pop("cap", None)
            shots.append(s)
            t += d
    total = t
    # sound cues derived from the pictures
    for s in shots:
        if s.get("anim") == "dateline" and s["params"].get("lines"):
            sfx.append({"t": s["start"] + 0.4, "kind": "typewriter", "dur": sum(len(l) for l in s["params"]["lines"]) / 22 + 0.3})
        if s.get("anim") == "agreement":
            sfx.append({"t": s["start"] + 0.8, "kind": "typewriter", "dur": 4.6})
            sfx.append({"t": s["start"] + 0.8 + 155 / 34 + 0.3, "kind": "stamp"})
        if s.get("anim") in ("radon", "tower_diagram"):
            sfx.append({"t": s["start"] + 2.5, "kind": "geiger", "dur": s["dur"] - 2.5})
        if s.get("anim") == "train_route":
            sfx.append({"t": s["start"] + 0.8, "kind": "train", "dur": s["dur"] - 0.8})
        if s.get("anim") == "prisoners":
            sfx.append({"t": s["start"], "kind": "wind", "dur": s["dur"]})
    for i, s in enumerate(shots):
        s["id"] = i
    tl = {"duration": total, "shots": shots, "narration": narration, "music": music, "sfx": sorted(sfx, key=lambda x: x["t"])}
    return tl


def credits_pages(tl):
    """Fill the credits roll from the captions actually used + Commons metadata."""
    cred_path = os.path.join(BUILD, "assets", "credits.json")
    meta = json.load(open(cred_path)) if os.path.exists(cred_path) else {}
    used = []
    for s in tl["shots"]:
        k = s.get("key")
        if k and k not in used:
            used.append(k)
    lines = []
    for k in used:
        m = meta.get(k, {})
        title = (m.get("title") or k).replace("File:", "")
        artist = (m.get("artist") or "").replace("\n", " ").strip()
        lic = m.get("license") or ""
        lines.append(f"{title} — {artist + ', ' if artist else ''}{lic}, via Wikimedia Commons")
    third = (len(lines) + 2) // 3
    pages = [
        ("Uranium for Stalin", [
            "Written, edited and produced with open tools",
            "Narration: Kokoro-82M neural voice (Apache-2.0)",
            "Music and sound design: original synthesised score",
            "Maps: Natural Earth (public domain)",
            "Typefaces: Big Shoulders Stencil, Big Shoulders, Source Serif 4, Special Elite, Courier Prime, Playfair Display (SIL OFL / Apache-2.0)",
            "Historical sources: Czech Radio (radio.cz); Political Prisoners (politicalprisoners.eu); Platform of European Memory and Conscience; Wilson Center Cold War International History Project; histories of the Soviet atomic project",
            "Figures for prisoners and uranium output are historians' estimates; illustrative footage is labelled on screen.",
        ]),
        ("Archive footage and photographs (1/3)", lines[:third]),
        ("Archive footage and photographs (2/3)", lines[third:2 * third]),
        ("Archive footage and photographs (3/3)", lines[2 * third:]),
    ]
    return pages


if __name__ == "__main__":
    tl = build()
    for s in tl["shots"]:
        if s.get("anim") == "credits_roll":
            s["params"]["pages"] = credits_pages(tl)
    out = os.path.join(BUILD, "timeline.json")
    json.dump(tl, open(out, "w"), indent=1, ensure_ascii=False)
    m, s = divmod(tl["duration"], 60)
    print(f"timeline: {len(tl['shots'])} shots, {int(m)}:{s:04.1f}")
