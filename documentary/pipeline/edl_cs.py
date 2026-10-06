"""Czech edit decision list: what plays under each line of narration_cs.json.

Pacing follows the FacelessOS visual rules: a new visual every ~1.5-3 s, on-screen text for
every statistic, cuts landing on spoken words ("at_word"), and a rotating set of devices
and transitions so no look repeats back to back. Place/date tags appear only when the
place or year changes; illustrative footage is labelled.
"""
from timeline import P, V, A

C1080 = "1440:1080:240:0"   # remove baked-in pillarbox from 4:3 films in 1080p files
C720 = "960:720:160:0"
ILL = {"kind": "illustrative"}


def T(text, t0=0.25, t1=3.6):
    return {"kind": "tag", "text": text, "t0": t0, "t1": t1}


def Wd(text, word=None, style="big", hold=2.2, **kw):
    """Kinetic on-screen words; anchored to a spoken word when `word` is given."""
    o = {"kind": "words", "text": text, "style": style, **kw}
    if word:
        o["word"], o["hold"] = word, hold
    else:
        o.setdefault("t0", 0.25)
        o.setdefault("t1", o["t0"] + hold)
    return o


def card(num, name, years):
    return ("card", dict(A("chapter2", 2.1, num=num, name=name, years=years), trans="whip", td=0.45))


EDL = [
    # ------------------------------------------------------------- HOOK
    ("music", "cold_open"),
    ("seg", "h01", [
        A("dateline", 2.4, lines=["29. 8. 1949 · 7:00", "SEMIPALATINSK · KAZAŠSKÁ SSR"]),
        V("rds1_site", 2.0, overlays=[{"kind": "countdown", "from": 3, "t0": 0.1, "step": 0.75}], trans="cut"),
        dict(A("dateline", 0.45, lines=[], flash_at=0.0), at_word="vybuchla", sfx="explosion", trans="cut"),
        P("rds1_museum", z0=1.0, z1=1.18, trans="white", td=0.9, shake=[0.0], shake_amp=32),
        dict(P("rds1_mockup", z0=1.05, z1=1.2, trans="cut",
               overlays=[Wd("22 000 TUN TNT", word="22", color="amber", hold=2.6)]), at_word="22"),
    ]),
    ("seg", "h02", [
        P("tower_night", z0=1.12, z1=1.0, trans="burn", td=0.8),
        dict(P("ortho_nikolaj", z0=1.0, z1=1.25, c1=(0.55, 0.45), overlays=[T("JÁCHYMOV · 50. LÉTA")]), at_word="vykopali"),
        dict(P("vojna_05", z0=1.1, z1=1.25), at_word="kněží"),
        dict(P("vojna_19", z0=1.2, z1=1.05), at_word="sedláci"),
        dict(A("bar_chart", w=1.4), at_word="sovětská", trans="glitch", td=0.4),
        dict(P("pribram_poster", fit="print", rot=-3), at_word="archivní"),
        dict(P("tower_03", z0=1.0, z1=1.15, trans="flash", td=0.35,
               overlays=[Wd("JEŠTĚ HORŠÍ", word="horší", color="red", hold=1.6)]), at_word="jiný"),
    ]),
    ("music", "teaser"),
    ("seg", "h03", [
        A("map_distance", w=1.6),
        dict(V("anthracite", 95.0, overlays=[ILL]), at_word="kdo", trans="cut"),
        dict(P("miner_drilling", overlays=[ILL], trans="cut", z0=1.1, z1=1.25), at_word="kopal"),
        dict(P("vojna_01", trans="cut", z0=1.0, z1=1.15), at_word="desítky"),
        dict(P("nikolaj_05", trans="cut", z0=1.2, z1=1.05), at_word="dřely"),
        dict(P("tower_night", trans="cut", z0=1.3, z1=1.15,
               overlays=[{"kind": "dosimeter", "t0": 0.0, "l0": 0.6, "l1": 0.98, "rise": 1.0}]), at_word="radioaktivním"),
        dict(V("crossroads_hd", 252.0, crop=C1080, trans="flash", td=0.3, overlays=[T("BIKINI · 1946 · TEST USA")]),
             at_word="bomby"),
    ]),
    ("music", "title"),
    ("card", A("title_slam", 4.2, sub="Československý uran, sovětská bomba a jáchymovské peklo")),

    # ------------------------------------------------------------- 01 TAJNÁ SMLOUVA
    ("music", "ch2"),
    card("01", "Tajná smlouva", "1945"),
    ("seg", "s204", [
        V("hiroshima_dmg", 247.0, crop=C1080, overlays=[T("HIROŠIMA · 1945")]),
        dict(P("gottwald_stalin", z0=1.0, z1=1.15, overlays=[T("PRAHA · 23. 11. 1945")], trans="whip"), at_word="23."),
        dict(A("agreement", 6.4), at_word="tajnou", trans="cut"),
        dict(A("train_route", w=1.0), at_word="Veškerý", trans="whip_l"),
        dict(P("thaler_rev", z0=1.3, z1=1.55,
               overlays=[Wd("POD CENOU SVĚTOVÉHO TRHU", word="cenu", size=104, color="amber", hold=3.0)]), at_word="cenu"),
    ]),
    ("seg", "s201", [
        V("october_1937", 316.0, crop=C720, overlays=[T("MOSKVA · ARCHIV 1937")], trans="whip"),
        dict(V("truman_1945", 86.0), at_word="Japonsko", trans="cut"),
        dict(P("stalin", fit="contain", z1=1.08), at_word="Stalin", trans="cut"),
    ]),
    ("seg", "s202", [
        P("kurchatov_1943", c0=(0.5, 0.32), c1=(0.5, 0.28), z0=1.05, z1=1.25, trans="cut"),
        dict(P("beria", fit="contain", z1=1.1), at_word="Berija", trans="cut"),
        dict(V("trinity", 0.0, overlays=[T("NOVÉ MEXIKO · 1945 · TEST USA")]), at_word="špionům", trans="glitch", td=0.35),
        dict(A("evidence_board", w=1.6,
               items=[("stalin", 470, 430, 300, -4, "STALIN"), ("beria", 900, 470, 260, 3, "BERIJA"),
                      ("kurchatov_1943", 1320, 430, 270, -2, "KURČATOV")],
               cards=[("u", "URAN ?", 1560, 850, 4), ("j", "JÁCHYMOV", 820, 880, -3)],
               links=[("stalin", "beria"), ("beria", "kurchatov_1943"), ("kurchatov_1943", "u"), ("u", "j")]),
             at_word="Chyběla", trans="cut"),
    ]),
    ("seg", "s203", [A("map_zoom_jachymov", w=1, trans="zoom", td=0.5)]),
    ("seg", "s101", [
        V("jachymov_valley", 0.0, speed=0.75, overlays=[T("JÁCHYMOV · KRUŠNÉ HORY")], trans="burn", td=0.7),
        dict(P("thaler_obv", z0=1.0, z1=1.3, overlays=[Wd("1520", word="1520", hold=2.2)]), at_word="ledna", trans="cut"),
        dict(P("thaler_rev", fit="print", rot=3), at_word="tolary", trans="cut"),
    ]),
    ("seg", "s102", [
        A("etymology", w=2.2),
        dict(P("thaler_obv", z0=1.6, z1=1.85, c0=(0.45, 0.45), c1=(0.5, 0.5)), at_word="nevymýšlím", trans="zoom", td=0.4),
    ]),
    ("seg", "s103", [
        P("svornost_1928", trans="whip"),
        dict(P("pitchblende2", z0=1.0, z1=1.3), at_word="černý", trans="cut"),
        dict(P("pitchblende", fit="print", rot=-3,
               overlays=[Wd("SMOLINEC", word="smolinec", color="amber", hold=2.4)]), at_word="smolinec", trans="cut"),
    ]),
    ("seg", "s104", [
        P("curies", fit="print", rot=-2, trans="cut"),
        dict(A("elements", w=1.1), at_word="radium", trans="whip"),
        dict(P("radium_palace_1926", z0=1.0, z1=1.15, overlays=[T("JÁCHYMOV · 1906"),
             Wd("PRVNÍ RADONOVÉ LÁZNĚ NA SVĚTĚ", word="1906", size=86, pos="low", hit=False, hold=3.2)]),
             at_word="1906", trans="cut"),
    ]),
    ("seg", "s105", [
        A("split_compare", w=1.4, left="radium_palace_1949", right="ortho_nikolaj", llabel="LÁZNĚ", rlabel="DŮL"),
        dict(A("radon", w=1.3), at_word="zabiják", trans="cut"),
        dict(P("vojna_28", z0=1.0, z1=1.15), at_word="tohle", trans="glitch", td=0.35),
    ]),
    ("seg", "s205", [
        P("svornost_modern", z0=1.15, z1=1.0, trans="cut"),
        dict(P("pitchblende2", c0=(0.3, 0.6), c1=(0.6, 0.4), z0=1.4, z1=1.6), at_word="nejcennější", trans="cut"),
        dict(P("gottwald_stalin", c0=(0.62, 0.36), c1=(0.63, 0.34), z0=1.8, z1=2.1), at_word="Stalin", trans="zoom", td=0.4),
    ]),
    ("seg", "s206", [
        V("jachymov_valley", 6.0, speed=0.75, trans="dissolve",
          overlays=[Wd("ODBĚR", style="big", size=150, pos="low", color="uranium", t0=1.2, t1=4.6, hit=False)]),
    ], 0.5),

    # ------------------------------------------------------------- 02 KDO KOPAL URAN
    ("music", "ch3"),
    card("02", "Kdo kopal uran", "1946 – 1949"),
    ("seg", "s301", [
        P("ortho_eduard_nikolaj", z0=1.0, z1=1.25, c1=(0.4, 0.5), overlays=[T("JÁCHYMOV · 1946")]),
        dict(V("anthracite", 405.0, overlays=[ILL]), at_word="ruda", trans="cut"),
        dict(A("train_route", w=1.2), at_word="vagonech", trans="whip"),
    ]),
    ("seg", "s302", [
        P("tower_night", z0=1.15, z1=1.0, trans="glitch", td=0.4),
        dict(V("anthracite", 60.0, overlays=[ILL, Wd("1946 – 1948", word="1946", size=150, hold=2.4)]), at_word="letech", trans="cut"),
        dict(P("ortho_nikolaj", z0=1.2, z1=1.35, overlays=[Wd("ZATÍM NE", word="nekopali", style="stamp", hold=2.0)]),
             at_word="nekopali", trans="cut"),
        dict(P("miner_drill", overlays=[ILL, Wd("NĚMEČTÍ ZAJATCI", word="němečtí", size=104, pos="low", hold=2.2)]),
             at_word="němečtí", trans="whip"),
        dict(P("pribram_poster", fit="print", rot=2,
               overlays=[Wd("CIVILNÍ HORNÍCI", word="civilní", size=104, pos="low", hold=2.0)]), at_word="civilní", trans="cut"),
    ]),
    ("seg", "s303", [
        A("bar_chart", w=1, trans="zoom", td=0.4),
        dict(P("uran_museum", z0=1.0, z1=1.2, overlays=[Wd("PŘES 100 TUN", word="sto", color="amber", size=170, hold=2.4)]),
             at_word="přes", trans="cut"),
    ]),
    ("seg", "s304", [
        P("rds1_museum", c0=(0.32, 0.5), c1=(0.36, 0.5), z0=1.5, z1=1.6, trans="cut"),
        dict(P("pitchblende", c0=(0.5, 0.4), z0=1.3, z1=1.15, overlays=[T("NĚMECKO · 1945"),
             {"kind": "words", "style": "count", "text": "", "value": 100, "fmt": "{} TUN", "word": "sto", "hold": 3.0,
              "sub": "ukrytého oxidu uranu", "color": "amber"}]), at_word="Německu", trans="whip"),
        dict(P("kurchatov_1943", fit="print", rot=2, overlays=[Wd("ROK NÁSKOKU", word="ušetřilo", size=120, pos="low", hold=2.2)]),
             at_word="Kurčatov", trans="cut"),
        dict(P("wismut_poster", fit="print", rot=-3, overlays=[T("SASKO · WISMUT")]), at_word="Saska", trans="whip_l"),
        dict(P("wismut_map", z0=1.0, z1=1.2), at_word="víc", trans="cut"),
    ]),
    ("seg", "s306", [
        A("plutonium_chain", w=1.5, trans="glitch", td=0.35),
        dict(P("svornost_1928", z0=1.2, z1=1.35, overlays=[Wd("DVĚ DATA", word="dvě", size=170, hold=2.0)]),
             at_word="dokazují", trans="zoom", td=0.4),
    ]),
    ("seg", "s305", [
        V("rds1_site", 12.0, overlays=[T("URAL · REAKTOR A"), Wd("ČERVEN 1948", word="červnu", color="uranium", hold=2.8)], trans="cut"),
        dict(P("ortho_nikolaj", z0=1.35, z1=1.1, overlays=[Wd("1949", word="1949", size=240, color="red", hold=2.6)]),
             at_word="Tábory", trans="flash", td=0.3),
    ]),
    ("seg", "s307", [
        V("rds1_site", 4.0, trans="flash", td=0.4, shake=[0.15], shake_amp=18),
        dict(A("teletype", w=2.0, header="WASHINGTON · 23. 9. 1949 · PREZIDENT TRUMAN:",
               body="MÁME DŮKAZY, ŽE V POSLEDNÍCH TÝDNECH DOŠLO V SSSR K ATOMOVÉMU VÝBUCHU.",
               note="překlad prohlášení Bílého domu"), at_word="Truman", trans="whip"),
    ]),
    ("seg", "s308", [
        V("crossroads_hd", 250.0, crop=C1080, overlays=[T("BIKINI · 1946 · TEST USA")], trans="cut"),
        dict(V("crossroads_hd", 576.0, crop=C1080), at_word="závod", trans="cut"),
        dict(P("miner_shovel", overlays=[ILL], z0=1.0, z1=1.15), at_word="mnohem", trans="cut"),
    ]),

    # ------------------------------------------------------------- 03 VÍTĚZNÝ ÚNOR
    ("music", "ch4"),
    card("03", "Vítězný únor", "1948"),
    ("seg", "s401", [
        P("gottwald", fit="contain", z1=1.08, overlays=[T("PRAHA · ÚNOR 1948")]),
        dict(P("gottwald_stalin", z0=1.0, z1=1.15), at_word="Gottwalda", trans="cut"),
        dict(A("timeline_1948", w=1.6), at_word="zákon", trans="whip"),
    ]),
    ("seg", "s402", [
        P("gottwald_1951", z0=1.1, z1=1.25, overlays=[Wd("BEZ SOUDU", word="soud", style="stamp", hold=2.4)]),
        dict(P("vojna_10", z0=1.0, z1=1.15), at_word="legální", trans="whip"),
        dict(P("vojna_01", z0=1.1, z1=1.0, overlays=[Wd("ZÁKON 247/1948", word="zákon", style="type", pos="low", hold=2.4)]),
             at_word="zákon", trans="cut"),
    ]),
    ("seg", "s403", [
        P("vojna_05", z0=1.15, z1=1.3, trans="cut"),
        dict(P("vojna_19", z0=1.25, z1=1.1), at_word="skauti", trans="cut"),
        dict(P("vojna_17", z0=1.0, z1=1.15), at_word="kdokoli", trans="cut"),
        dict(V("anthracite", 125.0, overlays=[ILL]), at_word="uranovém", trans="cut"),
        dict(P("ortho_bratrstvi", z0=1.0, z1=1.25, overlays=[Wd("ŘÍJEN 1949", word="října", style="type", pos="low", hold=2.4)]),
             at_word="Podle", trans="whip"),
    ]),
    ("seg", "s404", [
        P("stalin", c0=(0.5, 0.3), c1=(0.5, 0.28), z0=1.25, z1=1.45, trans="glitch", td=0.35),
        dict(V("crossroads_hd", 258.0, crop=C1080, overlays=[Wd("PRO VŠECHNY DALŠÍ", word="všechny", color="red", size=150, hold=2.6)]),
             at_word="Jen", trans="flash", td=0.3),
    ], 0.4),

    # ------------------------------------------------------------- 04 JÁCHYMOVSKÉ PEKLO
    ("music", "ch5"),
    card("04", "Jáchymovské peklo", "1949 – 1961"),
    ("seg", "s501", [
        A("camp_map", w=1),
        dict(P("ortho_bratrstvi", z0=1.0, z1=1.2, overlays=[Wd("18 TÁBORŮ", word="osmnáct", color="red", size=190, hold=2.6)]),
             at_word="osmnáct", trans="cut"),
    ]),
    ("seg", "s502", [
        A("camp_names", w=1.3, trans="whip"),
        dict(P("svornost_camp", z0=1.2, z1=1.45, c0=(0.45, 0.3), c1=(0.45, 0.32)), at_word="ironii", trans="cut"),
    ]),
    ("seg", "s503", [
        A("prisoners", w=1.25, trans="zoom", td=0.4),
        dict(A("mukl", w=1.1), at_word="mukl", trans="glitch", td=0.35),
    ]),
    ("seg", "s504", [
        V("anthracite", 70.0, overlays=[ILL, Wd("NORMA", word="normu", style="stamp", hold=2.0)], trans="cut"),
        dict(P("miners_pause", overlays=[ILL], z0=1.0, z1=1.12), at_word="jídla", trans="cut"),
        dict(P("vojna_28", z0=1.45, z1=1.3, overlays=[Wd("KOREKCE", word="korekce", color="red", hold=2.0)]),
             at_word="korekce", trans="cut"),
    ]),
    ("seg", "s505", [
        P("pitchblende2", z0=1.1, z1=1.3, trans="glitch", td=0.35,
          overlays=[{"kind": "dosimeter", "t0": 0.2, "l0": 0.3, "l1": 0.97, "rise": 3.0}]),
        dict(P("miner_drilling", overlays=[ILL], z0=1.25, z1=1.1), at_word="prach", trans="cut"),
        dict(A("radon", w=1.0), at_word="plicích", trans="cut"),
        dict(P("vojna_19", z0=1.3, z1=1.15), at_word="spali", trans="cut"),
    ]),
    ("seg", "s506", [P("mauthausen_stairs", z0=1.0, z1=1.08, trans="black", td=0.8)]),
    ("seg", "s507", [
        P("svornost_camp", z0=1.05, z1=1.15, overlays=[T("JÁCHYMOV · 28. 9. 1950")], trans="cut"),
        dict(P("mauthausen_stairs", c0=(0.56, 0.31), c1=(0.56, 0.33), z0=2.5, z1=2.7), at_word="Rudolf", trans="cut"),
        dict(P("mauthausen_stairs", c0=(0.56, 0.36), c1=(0.56, 0.37), z0=2.6, z1=2.8), at_word="Dozorci", trans="dissolve", td=0.5),
    ], 0.8),
    ("seg", "s508", [
        P("mauthausen_stairs", c0=(0.55, 0.12), c1=(0.55, 0.14), z0=1.9, z1=1.7, trans="cut"),
        dict(P("nikolaj_05", z0=1.0, z1=1.15), at_word="Podobných", trans="cut"),
        dict(P("nikolaj_02", z0=1.15, z1=1.0), at_word="les", trans="dissolve", td=0.6),
    ]),

    # ------------------------------------------------------------- 05 VĚŽ SMRTI
    ("music", "ch6"),
    card("05", "Věž smrti", "Vykmanov · Ostrov"),
    ("seg", "s601", [
        P("tower_night", z0=1.0, z1=1.12, overlays=[T("OSTROV · VYKMANOV II")]),
        dict(P("tower_03", z0=1.0, z1=1.15), at_word="Patřila", trans="cut"),
        dict(V("anthracite", 170.0, overlays=[ILL]), at_word="drtila", trans="cut"),
    ]),
    ("seg", "s602", [
        A("tower_diagram", w=1.0, trans="whip"),
        dict(V("anthracite", 232.0, overlays=[ILL]), at_word="síta", trans="cut"),
        dict(P("tower_05", z0=1.0, z1=1.15, overlays=[{"kind": "dosimeter", "t0": 0.0, "l0": 0.7, "l1": 0.98, "rise": 1.5}]),
             at_word="prachu", trans="cut"),
    ]),
    ("seg", "s603", [
        P("tower_04", z0=1.0, z1=1.25, trans="dissolve", td=0.6),
        dict(P("tower_01", z0=1.05, z1=1.2, overlays=[Wd("NÁRODNÍ KULTURNÍ PAMÁTKA", word="2008", size=92, pos="low", hit=False, hold=3.0)]),
             at_word="2008", trans="cut"),
    ], 0.5),

    # ------------------------------------------------------------- 06 CENA
    ("music", "ch8"),
    card("06", "Cena", "1960 – dnes"),
    ("seg", "s701", [
        P("vojna_02", z0=1.0, z1=1.12),
        dict(P("vojna_17", z0=1.1, z1=1.0, overlays=[Wd("AMNESTIE 1960", word="amnestie", style="type", pos="low", hold=2.4)]),
             at_word="amnestie", trans="cut"),
    ]),
    ("seg", "s702", [
        P("svornost_modern", z0=1.0, z1=1.15, trans="whip"),
        dict(A("production_counter", w=1.8, total=112000, years="1946 – 2017",
               label="tun uranu vytěženo za šest desetiletí"), at_word="tři", trans="zoom", td=0.4),
        dict(V("october_1937", 520.0, crop=C720, overlays=[T("MOSKVA · ARCHIV 1937")]), at_word="Většina", trans="cut"),
    ]),
    ("seg", "s703", [
        P("nikolaj_01", fit="contain", z1=1.08, overlays=[T("NAUČNÁ STEZKA JÁCHYMOVSKÉ PEKLO", t1=4.5)], trans="dissolve", td=0.6),
        dict(P("elias", fit="contain", z1=1.08), at_word="květnu", trans="dissolve", td=0.6),
    ]),
    ("seg", "s704", [
        P("rds1_museum", z0=1.0, z1=1.12, trans="cut"),
        dict(P("ortho_nikolaj", z0=1.0, z1=1.2), at_word="víte", trans="cut"),
        dict(P("vojna_01", z0=1.1, z1=1.0), at_word="Slavkova", trans="cut"),
        dict(P("tower_night", z0=1.0, z1=1.15, overlays=[Wd("12 LET", word="dvanáct", color="red", size=220, hold=2.6)]),
             at_word="dvanáct", trans="cut"),
    ]),
    ("seg", "s705", [P("thaler_obv", z0=1.0, z1=1.22, trans="dissolve", td=0.8)], 1.8),
    ("music", "end"),
    ("card", dict(A("dedication", 5.0), trans="black", td=1.0)),
    ("card", dict(A("credits_roll", 20.0, pages=[]), trans="black", td=0.8)),
]
