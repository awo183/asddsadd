"""Shot plan for "Stalin na splátky": one entry per visual cue of SCRIPT.md.

Every shot starts on its cue's word (see layout.py) and runs until the next
cue that has a shot here; cues without an entry are folded into the shot
before them. Inside a shot, a("word") gives the local time a word is spoken.
"""
import os

import layout as LY
import script
import vox as V
from vox import H, RED, W

ASSETS = os.path.join(V.BUILD, "assets")
L = LY.layout()
CUE = {c["id"]: c for c in L["cues"]}
WORDS = [w for blk in L["voice"] for w in blk["words"]]


def word_t(sub, after=0.0, n=1):
    """Global start time of the n-th spoken word containing sub (case-insensitive) after `after`."""
    sub = sub.lower()
    for w in WORDS:
        if w["t0"] >= after - 0.05 and sub in w["w"].lower():
            n -= 1
            if n == 0:
                return w["t0"]
    raise KeyError(f"word {sub!r} not found after {after:.2f}")


def have(name):
    return os.path.exists(os.path.join(ASSETS, "img", name))


def pick(*names):
    for n in names:
        if n and have(n):
            return "img/" + n
    return None


def person(name, x, y, size=620, at=0.0, rot=-2, **kw):
    """Cutout of a person when one exists, else a white-border print."""
    cut = f"{name}_cut.png"
    if have(cut):
        return dict(kind="cutout", img="img/" + cut, x=x, y=y, size=size, at=at, rot=rot, **kw)
    return dict(kind="card", img=pick(f"{name}.jpg"), x=x, y=y, size=size, at=at, rot=rot, **kw)


def tag(text, at, x=90, y=H - 130, **kw):
    return dict(text=text, at=at, x=x, y=y, **kw)


def hand(text, at, x=W - 120, y=150, **kw):
    return dict(text=text, at=at, x=x, y=y, hand=True, **kw)


SH = {}


def shot(*cids):
    def deco(fn):
        for c in cids:
            SH[c] = fn
        return fn
    return deco


# ============================================================ HOOK
@shot("c000")
def _(T, a):
    return dict(type="photo", img=pick("demolition_scaffold.jpg", "monument_from_river.jpg"), z0=1.3, z1=1.9,
                c0=(0.43, 0.25), c1=(0.42, 0.17), flash=True,
                tags=[tag("ŘÍJEN 1962", 0.25, size=60)],
                marks=[dict(kind="circle", nx=0.415, ny=0.13, rx=170, ry=140, at=a("hlavu") - 0.1)])


@shot("c003")
def _(T, a):
    return dict(type="counter", to=15.5, decimals=1, unit="m", count=1.1, at=0.05,
                bg=pick("monument_low_sepia.jpg"), caption="výška Stalinovy sochy")


@shot("c004")
def _(T, a):
    return dict(type="photo", img=pick("metronome_today.jpg", "metronome_today2.jpg"), grade="muted",
                z0=1.12, z1=1.0, c0=(0.5, 0.45), sfx=[(0.0, "scratch", 0.8)],
                tags=[tag("LETNÁ, DNES", 0.2), hand("„sraz na Stalinu“", a("sejdete") - 0.2)])


@shot("c006")
def _(T, a):
    return dict(type="section", statue_img="img/monument_side_cut.png",
                show={"statue": 0.0, "bridge": 0.0, "head_roll": a("skutálela") - 0.3},
                z0=1.12, z1=1.18, focus=(1000, 540),
                labels=[dict(text="LETNÁ", x=300, y=420, at=0.15), dict(text="VLTAVA", x=1760, y=960, at=0.4,
                                                                         color=(70, 90, 100))])


@shot("c007")
def _(T, a):
    return dict(type="highlight", sfx=[(0.0, "shutter", 1.0)],
                phrase=dict(lines=["ŽÁDNÝ FILM,", "ŽÁDNÉ FOTKY."], font="anton", size=170, align="center",
                            y=H / 2 - 200, at=0.0, stagger=0.06, hi=[(1, 0, 1)], hl_at=0.45))


@shot("c009")
def _(T, a):
    rp = pick("rude_pravo_oct1962.jpg")
    if rp:
        return dict(type="photo", img=rp, z0=1.0, z1=1.15, c0=(0.5, 0.1), c1=(0.5, 0.2), contrast=1.1,
                    tags=[hand("ani slovo", a("slovo") - 0.1, x=W - 160, y=H - 200, size=110)])
    return dict(type="slam", bg="paper", lines=["ANI SLOVO", "V NOVINÁCH"], accent=0, size=180, at=0.05,
                sound="paper")


@shot("c010")
def _(T, a):
    return dict(type="photo", img=pick("mayday_1955.jpg", "unveiling_1955.jpg"), z0=1.0, z1=1.1,
                c0=(0.5, 0.5), c1=(0.5, 0.42), tags=[tag("1955", 0.15)],
                sfx=[(0.1, "crowd", 0.6)])


@shot("c011")
def _(T, a):
    return dict(type="photo", img=pick("demolition_blast.jpg"), z0=1.0, z1=1.12, c0=(0.5, 0.42), flash=True,
                shakes=[0.0], shake_sound="explosion")


@shot("c012")
def _(T, a):
    return dict(type="counter", to=140000000, unit="Kčs", count=1.2, at=0.05, size=210,
                caption="cena pomníku", sfx=[(1.25, "cash", 0.9)])


@shot("c014")
def _(T, a):
    return dict(type="collage", z1=1.07, pan=(-30, 0), items=[
        person("svec_portrait", 760, 560, 760, 0.0),
        dict(kind="tag", text="Otakar Švec", role="sochař, autor pomníku", x=1180, y=760, at=0.25,
             ax=0, enter="slide"),
        dict(kind="stamp", text="† 1955", x=1380, y=400, at=a("nedožil") - 0.1, rot=-8, size=130)])


@shot("c015")
def _(T, a):
    return dict(type="photo", img=pick("monument_full_a.jpg"), z0=1.0, z1=1.1, c0=(0.55, 0.45),
                tags=[hand("jen 7 let", a("sedmi") - 0.1, x=W - 140, y=170, size=110)])


@shot("c016")
def _(T, a):
    return dict(type="collage", z1=1.06, items=[
        dict(kind="video", src="footage/norm/ig_metronome.mp4", **{"in": 74.4}, speed=0.5, crop=(0, 0.02, 1, 0.5),
             x=W / 2 - 120, y=H / 2, size=1000, at=0.0, rot=-2),
        dict(kind="stamp", text="SPLÁCÍ DODNES", x=W / 2 + 320, y=H - 220, at=a("splácí") - 0.05, rot=-9,
             size=100)],
        tags=[tag("METRONOM, LETNÁ", 0.2, x=120, y=150)])


@shot("c018")
def _(T, a):
    return dict(type="slam", bg=pick("monument_full_a.jpg"), lines=["STALIN", "NA SPLÁTKY"], accent=1,
                sizes=[250, 190], at=0.0, flash=True, sfx=[(0.0, "boom", 0.6)])


# ============================================================ 1. OBJEDNÁVKA
def chapter(text, sub=None, bg=None):
    def make(T, a):
        return dict(type="chapter", text=text, sub=sub, bg=bg, at=0.08, fade_in=0.06)
    return make


SH["c019"] = chapter("1. OBJEDNÁVKA")
SH["c037"] = chapter("2. SKLEP")
SH["c062"] = chapter("3. SOCHAŘ")
SH["c080"] = chapter("4. ODSTŘEL")
SH["c111"] = chapter("5. ÚČET")


@shot("c020")
def _(T, a):
    return dict(type="map", keys=[(0.0, 15.0, 50.5, 42), (1.6, 15.6, 49.8, 17), (3.2, 15.8, 49.6, 12)],
                fills=[{"group": "CS", "color": RED, "at": 0.6}],
                labels=[dict(lon=19.5, lat=49.0, text="ČESKOSLOVENSKO", at=1.1, size=40, color=(255, 255, 255)),
                        dict(lon=10.0, lat=54.5, text="EVROPA", at=0.2, size=56)],
                pins=[dict(lon=14.42, lat=50.09, at=2.0, label="PRAHA, LETNÁ")])


@shot("c021")
def _(T, a):
    return dict(type="timeline", gap=470, years=[
        dict(year=1949, label="soutěž", at=0.05), dict(year=1952, label="stavba", at=0.45),
        dict(year=1955, label="odhalení", at=0.8), dict(year=1962, label="odstřel", at=1.15)],
        focus=[(2.0, 0)], sfx=[(0.0, "paper_slide", 0.7)],
        marks=[dict(kind="label", text="Stalinovy 70. narozeniny", x=W / 2, y=260, at=a("sedmdesátiny") - 0.3,
                    size=70)])


@shot("c023")
def _(T, a):
    return dict(type="collage", z1=1.08, items=[
        dict(kind="card", img=pick("stalin70_poster.jpg", "stalin_portrait.jpg"), x=W / 2 - 160, y=H / 2, size=860,
             at=0.0, rot=-3),
        dict(kind="stamp", text="SOUTĚŽ", x=W / 2 + 420, y=H / 2 + 220, at=a("soutěž") - 0.1, rot=-10, size=130)])


@shot("c024")
def _(T, a):
    return dict(type="counter", to=55, unit="sochařů", count=1.0, at=0.05,
                caption="účast povinná, ať chtěli, nebo ne", red=True,
                sfx=[(a("muselo") - 0.1, "stamp", 0.6)])


@shot("c026")
def _(T, a):
    img = pick("competition_models.jpg")
    if img:
        return dict(type="photo", img=img, z0=1.0, z1=1.1, c0=(0.5, 0.5),
                    tags=[hand("stojí, nebo sedí", a("stojí") - 0.2, x=W - 120, y=H - 170)])
    return dict(type="compare", px_per_m=40, items=[
        dict(kind="person", h_m=7, x=500, label="stojící Stalin", at=0.1),
        dict(kind="person", h_m=5, x=1000, label="sedící Stalin", at=0.5),
        dict(kind="person", h_m=7, x=1500, label="zase stojící", at=0.9)])


@shot("c027")
def _(T, a):
    return dict(type="collage", z1=1.06, items=[
        person("svec_portrait", 520, 560, 660, 0.0, rot=-3),
        dict(kind="tag", text="Otakar Švec", role="sochař", x=290, y=930, at=0.2, ax=0, enter="slide"),
        dict(kind="card", img=pick("monument_side.jpg"), x=1330, y=520, size=900, at=a("dvě") - 0.3, rot=2)],
        marks=[dict(kind="arrow", p0=(860, 300), p1=(1000, 420), at=a("řady") - 0.1)])


@shot("c028")
def _(T, a):
    return dict(type="layout", at=0.05, rows_at=a("čtyři") - 0.2)


@shot("c029")
def _(T, a):
    return dict(type="collage", z1=1.05, items=[
        dict(kind="text", text="KOMISE:", font="anton", size=200, x=W / 2, y=H / 2 - 120, at=0.0, shadow=False),
        dict(kind="stamp", text="NADŠENÁ", x=W / 2 + 40, y=H / 2 + 140, at=a("nadšená") - 0.1, rot=-7,
             size=150)])


@shot("c031")
def _(T, a):
    return dict(type="photo", img=pick("monument_side.jpg"), z0=1.15, z1=1.3, c0=(0.62, 0.42), c1=(0.38, 0.42),
                marks=[dict(kind="arrow", p0=(1650, 820), p1=(560, 820), at=0.4, d=0.9)])


@shot("c032")
def _(T, a):
    q = pick("meat_queue_1950s.jpg")
    items = [dict(kind="card", img=pick("monument_side.jpg"), x=620, y=500, size=760, at=0.0, rot=-3)]
    if q:
        items.append(dict(kind="card", img=q, x=1320, y=560, size=760, at=0.12, rot=3))
    return dict(type="collage", z1=1.04, items=items, sfx=[(0.0, "murmur", 0.7)],
                tags=[hand("„fronta na maso“", 0.15, x=W / 2, y=H - 150, ax=0.5, size=120)])


@shot("c034")
def _(T, a):
    return dict(type="collage", z1=1.07, items=[
        dict(kind="card", img=pick("slavia_stadium_letna.jpg", "monument_from_river.jpg"), x=W / 2, y=H / 2 - 20,
             size=1150, at=0.0, rot=-2),
        dict(kind="tag", text="Stadion Slavie", role="Letná", x=230, y=880, at=0.3, ax=0, enter="slide"),
        dict(kind="stamp", text="DOSTAVĚNO 1948", x=W / 2 + 330, y=300, at=a("dostavěný") - 0.1, rot=-8,
             size=96)],
        marks=[dict(kind="cross", x=W / 2, y=H / 2 - 20, r=330, w=16, at=a("zemi") - 0.15, d=0.6)],
        sfx=[(a("dostavěný") - 0.1, "wood_crack", 0.8)])


# ============================================================ 2. SKLEP
@shot("c038")
def _(T, a):
    return dict(type="timeline", gap=520, years=[
        dict(year=1949, label="soutěž", at=0.0), dict(year=1952, label="únor: kopat!", at=0.35,
                                                      img=pick("construction_1953.jpg"))])


@shot("c039")
def _(T, a):
    return dict(type="counter", to=600, unit="lidí", count=1.0, at=0.05, bg=pick("construction_1953.jpg"),
                caption="na stavbě denně")


@shot("c041")
def _(T, a):
    return dict(type="section", show={"statue": 0.0, "granite": 0.0, "skeleton": 0.25, "basement": None},
                z0=1.9, z1=2.0, focus=(855, 260),
                labels=[dict(text="ŽELEZOBETONOVÁ KOSTRA", x=1000, y=230, at=0.4, bg=True, ax=0.0, size=52)])


@shot("c042")
def _(T, a):
    return dict(type="map", keys=[(0.0, 15.2, 50.3, 6.0), (2.5, 14.75, 50.35, 3.2)],
                fills=[{"group": "CS", "color": (205, 120, 110), "at": 0.0}],
                pins=[dict(lon=15.06, lat=50.77, at=0.4, label="LIBEREC"),
                      dict(lon=14.42, lat=50.09, at=0.6, label="PRAHA", side="left")],
                routes=[dict(pts=[(15.06, 50.77), (14.8, 50.45), (14.42, 50.09)], at=1.0, d=1.6)],
                labels=[dict(lon=15.6, lat=49.85, text="235 ŽULOVÝCH KVÁDRŮ", at=a("dvě") - 0.1, size=56,
                             color=(255, 255, 255))])


@shot("c043")
def _(T, a):
    return dict(type="counter", to=17000, unit="tun", count=1.0, at=0.05, bg=pick("granite_blocks.jpg"),
                caption="žula + beton", sfx=[(1.05, "impact", 0.7)])


@shot("c045")
def _(T, a):
    return dict(type="section", statue_img="img/monument_side_cut.png",
                show={"statue": 0.0, "cracks": a("neunesl") - 0.3}, z0=1.25, z1=1.32, focus=(880, 430),
                labels=[dict(text="SVAH BY TO NEUNESL", x=1300, y=640, at=a("neunesl") - 0.1, color=RED, size=50)])


@shot("c046")
def _(T, a):
    return dict(type="section", statue_img="img/monument_side_cut.png",
                show={"statue": 0.0, "basement": 0.1, "pillars": a("sloupy") - 0.5}, z0=1.3, z1=1.4,
                focus=(860, 520), sfx=[(0.1, "pour", 0.6)],
                labels=[dict(text="DVOUPATROVÝ SKLEP", x=1150, y=600, at=a("dvoupatrový") - 0.1, bg=True, ax=0.0)])


@shot("c048")
def _(T, a):
    return dict(type="collage", z1=1.06, items=[
        person("lukes_portrait", 560, 540, 700, 0.0),
        dict(kind="tag", text="Zdeněk Lukeš", role="historik architektury", x=900, y=330, at=0.2, ax=0,
             enter="slide")],
        headline=dict(lines=["„monumentální", "sál“"], font="play", size=110, x=920, y=560,
                      at=a("monumentální") - 0.15, hi=[(0, 0, 0)], hl_at=a("monumentální") + 0.3))


@shot("c049")
def _(T, a):
    return dict(type="slam", bg="black", lines=["KOMUNISTICKÉ", "MAUZOLEUM?"], accent=1, sizes=[170, 210],
                at=0.0)


@shot("c050")
def _(T, a):
    return dict(type="photo", img=pick("underground_hall.jpg", "underground_damage.jpg"), z0=1.0, z1=1.12,
                sfx=[(0.0, "heartbeat", 0.6)],
                tags=[hand("zapamatujte si!", a("zapamatujte") - 0.1, x=W - 130, y=160)])


@shot("c052")
def _(T, a):
    return dict(type="slam", bg="paper", lines=["A KDO TO", "STAVĚL?"], accent=1, sizes=[170, 210], at=0.0,
                sound="hit")


@shot("c053")
def _(T, a):
    return dict(type="photo", img=pick("archaeology_letna.jpg", "construction_1954.jpg"), grade="muted",
                z0=1.0, z1=1.12, c0=(0.5, 0.5),
                tags=[tag("LETNÁ, 2021", 0.2), hand("dřevěné ubytovny", a("ubytoven") - 0.3, x=W - 120, y=170)])


@shot("c054")
def _(T, a):
    return dict(type="collage", z1=1.06, items=[
        person("hasil_portrait", 700, 560, 700, 0.0, rot=2),
        dict(kind="tag", text="Jan Hasil", role="archeolog, AV ČR", x=1080, y=560, at=0.2, ax=0,
             enter="slide")])


@shot("c055")
def _(T, a):
    return dict(type="area", px_per_m=150, items=[
        dict(w=1.87, h=1.87, x=620, at=0.05, label="3,5 m²", sub="na jednoho člověka", person=True),
        dict(w=2.5, h=5.0, x=1300, at=a("metru") - 0.6, label="12,5 m²", sub="parkovací místo",
             color=(150, 146, 138))])


@shot("c056")
def _(T, a):
    return dict(type="highlight", style="doc", sfx=[(a("vězeňská") - 0.1, "door", 0.8)],
                phrase=dict(lines=["„…na nějaké", "vězeňské normě.“"], font="type", size=120, x=230, y=330,
                            at=0.0, stagger=0.05, hi=[(1, 0, 1)], hl_at=a("vězeňská") - 0.1, color=(30, 28, 26)),
                marks=[dict(kind="label", text="— Jan Hasil", x=1500, y=760, at=0.5, size=64)])


@shot("c058")
def _(T, a):
    return dict(type="collage", z1=1.07, items=[
        dict(kind="card", img=pick("stalin_mourning_1953.jpg", "stalin_portrait.jpg"), x=760, y=540, size=820,
             at=0.0, rot=-2),
        dict(kind="text", text="5. 3. 1953", font="anton", size=150, x=1450, y=420, at=0.2, shadow=False),
        dict(kind="stamp", text="ZEMŘEL", x=1450, y=650, at=a("umřel") - 0.1, rot=-8, size=120)],
        sfx=[(0.0, "drum", 0.9)])


@shot("c061")
def _(T, a):
    return dict(type="photo", img=pick("construction_1954.jpg"), z0=1.0, z1=1.12, c0=(0.5, 0.4),
                tags=[hand("…a stavba jede dál", a("jela") - 0.2, x=W - 120, y=H - 170)],
                sfx=[(0.2, "chisel", 0.6)])


# ============================================================ 3. SOCHAŘ
@shot("c063")
def _(T, a):
    return dict(type="collage", z1=1.08, items=[
        person("svec_portrait", W / 2 - 200, 560, 820, 0.0, rot=-1),
        dict(kind="tag", text="Otakar Švec", role="1892–1955", x=1180, y=600, at=0.3, ax=0, enter="slide")])


@shot("c064")
def _(T, a):
    return dict(type="collage", z1=1.07, items=[
        dict(kind="card", img=pick("svec_young.jpg", "svec_portrait.jpg"), x=760, y=540, size=760, at=0.0,
             rot=-3)],
        tags=[hand("hvězda!", a("hvězda") - 0.15, x=1500, y=420, size=130)])


@shot("c065")
def _(T, a):
    return dict(type="collage", z1=1.07, items=[
        dict(kind="card", img=pick("masaryk_bust_svec.jpg"), x=W / 2 - 150, y=530, size=820, at=0.0, rot=2),
        dict(kind="tag", text="T. G. Masaryk", role="socha od Otakara Švece", x=1250, y=760, at=a("Masaryka") - 0.2,
             ax=0, enter="slide")])


@shot("c066")
def _(T, a):
    return dict(type="collage", z1=1.07, items=[
        dict(kind="card", img=pick("motocyklista.jpg"), x=W / 2 - 120, y=520, size=980, at=0.0, rot=-2,
             grade=False),
        dict(kind="tag", text="Sluneční paprsek", role="1924", x=200, y=880, at=0.3, ax=0, enter="slide"),
        dict(kind="stamp", text="NÁRODNÍ GALERIE", x=1300, y=260, at=a("Národní") - 0.1, rot=-6, size=80)])


@shot("c068")
def _(T, a):
    return dict(type="photo", img=pick("svec_studio_model.jpg"), z0=1.0, z1=1.12, c0=(0.5, 0.42),
                tags=[hand("pomalu…", a("pomalu") - 0.15, x=W - 140, y=170), tag("1953", 0.2)])


@shot("c069")
def _(T, a):
    return dict(type="highlight", style="doc",
                phrase=dict(lines=["ČASTÉ KONTROLY", "STÁTNÍ BEZPEČNOSTI"], font="type", size=120, x=200, y=360,
                            at=0.0, stagger=0.05, hi=[(1, 0, 1)], hl_at=a("Státní") - 0.05, color=(30, 28, 26)),
                marks=[dict(kind="circle", x=1440, y=760, rx=170, ry=95, at=a("ateliér") - 0.3)],
                sfx=[(0.0, "typewriter", 0.7)])


@shot("c071")
def _(T, a):
    return dict(type="collage", z1=1.05, items=[
        person("svec_portrait", W / 2, 560, 640, 0.0),
        dict(kind="png", img="img/silhouette.png", x=420, y=600, size=420, at=0.0, out=a("přestala") - 0.2,
             shadow=False),
        dict(kind="png", img="img/silhouette.png", x=1500, y=600, size=420, at=0.0, out=a("přestala"),
             shadow=False)])


@shot("c072")
def _(T, a):
    return dict(type="photo", img=pick("construction_1954.jpg", "construction_1953.jpg"), z0=1.08, z1=1.0,
                darken=(0.0, 0.55), tags=[tag("1954", 0.3)])


@shot("c074")
def _(T, a):
    return dict(type="photo", img=pick("svec_portrait.jpg"), z0=1.05, z1=1.22, c0=(0.5, 0.35),
                darken=(0.5, 0.35))


@shot("c075")
def _(T, a):
    return dict(type="slam", bg="black", lines=["3. BŘEZNA 1955?", "NEBO 4. DUBNA?"], sizes=[130, 130],
                at=0.0, stagger=0.6, sound=None, font="oswald")


@shot("c076")
def _(T, a):
    return dict(type="photo", img=pick("unveiling_1955.jpg", "mayday_1955.jpg"), z0=1.0, z1=1.1,
                tags=[tag("1. KVĚTNA 1955", 0.25)], sfx=[(0.0, "crowd", 0.9)])


@shot("c079")
def _(T, a):
    return dict(type="timeline", gap=640, years=[
        dict(year=1953, label="† Stalin", at=0.0, img=pick("stalin_portrait.jpg")),
        dict(year=1955, label="† Švec · odhalení", at=a("sochař") - 0.3, img=pick("svec_portrait.jpg"))])


# ============================================================ 4. ODSTŘEL
@shot("c081")
def _(T, a):
    return dict(type="collage", z1=1.06, items=[
        dict(kind="card", img=pick("unveiling_1955.jpg", "monument_full_a.jpg"), x=W / 2, y=520, size=1000,
             at=0.0, rot=-2)],
        tags=[hand("ani rok", 0.3, x=W - 160, y=H - 160, size=120)])


@shot("c083")
def _(T, a):
    items = [dict(kind="card", img=pick("congress_1956.jpg"), x=W / 2 - 80, y=500, size=1240, at=0.0, rot=-1.5),
             dict(kind="tag", text="Nikita Chruščov", role="XX. sjezd KSSS, Moskva", x=180, y=900, at=0.3, ax=0,
                  enter="slide"),
             dict(kind="stamp", text="KULT OSOBNOSTI", x=1380, y=860, at=a("kult") - 0.1, rot=-6, size=96)]
    return dict(type="collage", z1=1.07, items=items, tags=[tag("ÚNOR 1956", a("únoru") - 0.2, x=1460, y=120)])


@shot("c084")
def _(T, a):
    return dict(type="photo", img=pick("prague_1950s_street.jpg", "monument_bridge_street.jpg",
                                       "monument_parizska.jpg"), z0=1.0, z1=1.25, c0=(0.5, 0.45),
                c1=(0.5, 0.3), sfx=[(a("trapasu") - 0.3, "scratch", 0.8)],
                tags=[hand("17 000 tun trapasu", a("trapasu") - 0.2, x=W - 120, y=H - 170, size=96)])


@shot("c086")
def _(T, a):
    return dict(type="subscribe", at=0.1, click=a("odběr") - 0.1)


@shot("c088")
def _(T, a):
    return dict(type="timeline", gap=560, years=[
        dict(year=1956, label="projev", at=0.0), dict(year=1961, label="rozhodnutí", at=a("šedesát") - 0.2)],
        marks=[dict(kind="label", text="…nic se neděje…", x=W / 2, y=260, at=0.5, size=120)],
        sfx=[(0.4, "tick", 0.5), (0.9, "tick", 0.5), (1.4, "tick", 0.5)])


@shot("c090")
def _(T, a):
    return dict(type="photo", img=pick("demolition_scaffold.jpg", "monument_from_river.jpg"), z0=1.25, z1=1.4,
                c0=(0.45, 0.3), c1=(0.43, 0.25), tags=[tag("PODZIM 1962", 0.2)], sfx=[(0.3, "hammer_wood", 0.8)],
                marks=[dict(kind="arrow", np0=(0.62, 0.05), np1=(0.5, 0.2), at=a("ohradou") - 0.4)])


@shot("c092")
def _(T, a):
    heads = [(0.235, 0.085), (0.455, 0.14), (0.575, 0.175), (0.67, 0.215), (0.8, 0.225)]
    t0 = a("hlavy") - 0.3
    return dict(type="photo", img=pick("monument_side.jpg"), z0=1.0, z1=1.05, c0=(0.5, 0.4),
                sfx=[(t0, "jackhammer", 0.8), (t0 + 1.2, "jackhammer", 0.6)],
                marks=[dict(kind="cross", nx=x, ny=y, r=50, w=11, at=t0 + k * 0.35, d=0.35)
                       for k, (x, y) in enumerate(heads)])


@shot("c094")
def _(T, a):
    return dict(type="photo", img=pick("demolition_blast.jpg"), z0=1.0, z1=1.1, c0=(0.5, 0.45), flash=True,
                shakes=[0.0], shake_sound="explosion", tags=[tag("19. ŘÍJNA 1962", 0.2)])


@shot("c097")
def _(T, a):
    return dict(type="slam", bg="black", lines=["ODSTŘEL", "1 / 3"], accent=1, sizes=[150, 260], at=0.0,
                sound="hit")


@shot("c098")
def _(T, a):
    return dict(type="photo", img=pick("demolition_blast2.jpg", "demolition_blast.jpg"), z0=1.0, z1=1.12,
                c0=(0.5, 0.45), flash=True, shakes=[0.0, 0.9], shake_sound="explosion",
                tags=[tag("6. LISTOPADU 1962", 0.2)])


@shot("c101")
def _(T, a):
    return dict(type="city", z=15, nx=12, ny=8, keys=[(0.0, 14.425, 50.09, 15.7), (2.5, 14.425, 50.09, 15.15)],
                pins=[dict(lon=14.4172, lat=50.0944, at=0.0)],
                rings=[dict(lon=14.4172, lat=50.0944, at=0.1, n=5, every=0.35, d=1.5, r=1300)],
                labels=[dict(lon=14.4215, lat=50.0870, text="STARÉ MĚSTO", at=0.6, size=40),
                        dict(lon=14.4045, lat=50.0905, text="HRADČANY", at=0.8, size=40)],
                sfx=[(0.3, "rattle", 0.8)])


@shot("c103")
def _(T, a):
    return dict(type="collage", z1=1.05, items=[
        dict(kind="stamp", text="PŘÍSNĚ TAJNÉ", x=W / 2, y=H / 2 - 40, at=0.0, rot=-6, size=150)],
        tags=[hand("…moc ne", a("nevyšlo") - 0.2, x=W / 2 + 200, y=H / 2 + 230, size=130, ax=0.5)])


@shot("c104")
def _(T, a):
    return dict(type="collage", z1=1.06, items=[
        person("klimes_portrait", 640, 560, 900, 0.0),
        dict(kind="tag", text="Josef Klimeš", role="sochař", x=1100, y=540, at=0.25, ax=0, enter="slide")])


@shot("c105")
def _(T, a):
    t1 = a("fotil") - 0.15
    return dict(type="collage", z1=1.05, items=[
        person("klimes_portrait", 520, 600, 820, 0.0),
        dict(kind="stamp", text="PŘEVLEK", x=520, y=240, at=a("dělníka") - 0.2, rot=-9, size=100),
        dict(kind="card", img=pick("demolition_closeup.jpg", "demolition_blast2.jpg"), x=1350, y=520, size=760,
             at=t1, rot=3)],
        sfx=[(t1, "shutter", 0.9), (t1 + 0.25, "shutter", 0.8), (t1 + 0.5, "shutter", 0.8)])


@shot("c107")
def _(T, a):
    return dict(type="counter", to=4500000, unit="Kčs", count=1.1, at=0.05,
                bg=pick("demolition_blast2.jpg"), caption="cena demolice",
                sfx=[(1.2, "cash", 0.9)])


@shot("c110")
def _(T, a):
    return dict(type="slam", bg="paper", lines=["SPLÁTKA", "Č. 2"], accent=1, sizes=[200, 240], at=0.0,
                sound="stamp")


# ============================================================ 5. ÚČET
@shot("c112")
def _(T, a):
    return dict(type="photo", img=pick("rubble_1962.jpg", "demolition_closeup.jpg"), z0=1.0, z1=1.12,
                sfx=[(a("smazat") - 0.4, "sub", 0.6)])


@shot("c114")
def _(T, a):
    return dict(type="slam", bg="paper", lines=["KAM ZMIZELA", "ŽULA?"], accent=1, sizes=[160, 220], at=0.0,
                sound="hit")


@shot("c115")
def _(T, a):
    return dict(type="section", show={"basement": 0.0, "pillars": 0.0, "rubble": a("shrnuly") - 0.4},
                z0=1.25, z1=1.32, focus=(860, 520),
                labels=[dict(text="NEJSPÍŠ", x=1180, y=560, at=a("nejspíš") - 0.1, color=RED, size=60, ax=0.0)])


@shot("c116")
def _(T, a):
    return dict(type="photo", img=pick("underground_hall.jpg", "underground_damage.jpg"), z0=1.08, z1=1.0,
                tags=[tag("SKLADIŠTĚ", a("skladiště") - 0.2)])


@shot("c117")
def _(T, a):
    return dict(type="photo", img=pick("rock_club_1990.jpg", "underground_hall.jpg"), z0=1.0, z1=1.1,
                tags=[tag("1990", 0.15)], sfx=[(0.0, "guitar", 0.8)])


@shot("c119")
def _(T, a):
    return dict(type="slam", bg="black", lines=["PRVNÍ SOUKROMÉ", "RÁDIO"], accent=1, sizes=[150, 230],
                at=0.0, sound="radio")


@shot("c120")
def _(T, a):
    return dict(type="photo", img=pick("metronome_1991.jpg", "metronome_today2.jpg", "metronome_today.jpg"),
                grade="muted", z0=1.0, z1=1.1, tags=[tag("METRONOM · OD 1991", 0.15)])


@shot("c122")
def _(T, a):
    return dict(type="compare", px_per_m=28, items=[
        dict(kind="statue", h_m=15.5, x=620, label="Stalin 15,5 m", at=0.0),
        dict(kind="metronome", h_m=25, x=1250, label="metronom 25 m · 7 t", at=0.3)],
        ruler=dict(h_m=25, at=0.4, d=0.9, x=1650))


@shot("c123")
def _(T, a):
    return dict(type="section", show={"basement": 0.0, "pillars": 0.0, "rubble": 0.0, "cracks": 0.2,
                                      "crane_x": a("jeřáb") - 0.2},
                z0=1.0, z1=1.05, focus=(860, 420))


@shot("c124")
def _(T, a):
    if pick("helicopter_1991.jpg"):
        return dict(type="photo", img=pick("helicopter_1991.jpg"), grade="muted", z0=1.0, z1=1.12,
                    tags=[tag("15. 5. 1991", 0.15)], sfx=[(0.0, "helicopter", 0.8)])
    return dict(type="section", show={"basement": 0.0, "pillars": 0.0, "rubble": 0.0, "heli": 0.0}, z0=1.0,
                z1=1.04, focus=(860, 420), sfx=[(0.0, "helicopter", 0.9)],
                labels=[dict(text="15. 5. 1991", x=300, y=200, at=0.1, bg=True, size=50),
                        dict(text="vrtulníkem!", x=1320, y=330, at=a("Vrtulníkem") - 0.1, color=RED, size=96,
                             font="caveat")])


@shot("c127")
def _(T, a):
    return dict(type="collage", z1=1.06, items=[
        dict(kind="card", img=pick("barrier_2019.jpg", "underground_damage.jpg"), x=560, y=520, size=860, at=0.0,
             rot=-2, grade=False),
        dict(kind="stamp", text="UZAVŘENO", x=600, y=320, at=a("zavřít") - 0.15, rot=-10, size=120)],
        headline=dict(lines=["„konstrukci", "hrozí zřícení“"], font="play", size=96, x=1110, y=560,
                      at=a("hrozilo") - 0.4, hi=[(1, 0, 1)], hl_at=a("zřícení") - 0.1),
        tags=[tag("2019", 0.15, x=1110, y=440, ax=0)], sfx=[(a("hrozilo") - 0.2, "beep", 0.7)])


@shot("c130")
def _(T, a):
    return dict(type="photo", img=pick("stalin_club.jpg", "metronome_today.jpg"), grade="muted", z0=1.0, z1=1.1,
                tags=[tag("2026", 0.15)])


@shot("c131")
def _(T, a):
    return dict(type="slam", bg="black", lines=["STALIN"], accent=0, sizes=[340], at=0.0, sound="hit")


@shot("c132")
def _(T, a):
    return dict(type="highlight", style="doc", sfx=[(0.3, "drip", 0.8), (1.8, "drip", 0.6)],
                phrase=dict(lines=["STATICKÝ POSUDEK:", "zatékání i narušení", "nosných prvků"], font="type",
                            size=104, x=220, y=280, at=0.0, stagger=0.05, hi=[(1, 0, 0), (2, 0, 1)],
                            hl_at=a("zatéká") - 0.1, color=(30, 28, 26)))


@shot("c134")
def _(T, a):
    return dict(type="photo", img=pick("underground_damage.jpg", "underground_hall.jpg"), grade="muted", z0=1.0,
                z1=1.1, tags=[hand("každý rok", a("každý") - 0.1, x=W - 140, y=170)])


@shot("c135")
def _(T, a):
    return dict(type="collage", z1=1.06, items=[
        person("zabransky_portrait", 600, 580, 900, 0.0),
        dict(kind="tag", text="Adam Zábranský", role="pražský radní", x=980, y=360, at=0.2, ax=0,
             enter="slide"),
        dict(kind="stamp", text="ZALÍT PĚNOBETONEM", x=1300, y=700, at=a("pěnobetonem") - 0.2, rot=-6,
             size=88)])


@shot("c137")
def _(T, a):
    return dict(type="footage", src="footage/norm/px_dusk_river.mp4", **{"in": 8.0}, grade="muted", z0=1.15,
                z1=1.0, film=False)


@shot("c138")
def _(T, a):
    t_end = a("další") - 0.1
    return dict(type="section", show={"basement": 0.0, "pillars": 0.0, "rubble": 0.0, "metronome": 0.0,
                                      "person": 0.3, "glow": a("splácí") - 0.3, "bridge": 0.0},
                z0=1.0, z1=1.12, focus=(900, 470),
                labels=[dict(text="VY", x=1020, y=290, at=0.5, color=RED, size=56),
                        dict(text="SKLEP, KTERÝ PRAHA SPLÁCÍ", x=1100, y=600, at=a("splácí") - 0.2, bg=True,
                             ax=0.0),
                        dict(text="70+ LET", x=1100, y=680, at=a("sedmdesát") - 0.1, color=RED, size=64,
                             ax=0.0)],
                split=[(t_end, dict(type="slam", bg="paper", lines=["DALŠÍ PŘÍBĚH", "Z PADESÁTÝCH LET"],
                                    accent=1, sizes=[170, 120], at=0.0, sound="whoosh", fade_out=0.8))],
                sfx=[(t_end + 1.6, "metronome", 0.6)])


# ============================================================ sound and music
SFX_CUES = {}          # script [SFX] cues are realised inside the shots above (see sfx=...)
MUSIC_PLAN = [
    ("hook", 0.0, "c018", dict(db=-2, fade_in=0.3, fade_out=0.4)),
    ("order", "c019", "c062", dict(db=-1)),
    ("sculptor", "c062", "c080", dict(db=-1)),
    ("blast", "c080", "c111", dict(db=-2)),
    ("bill", "c111", None, dict(db=-1, fade_out=3.5)),
]


def _ct(x):
    return x if isinstance(x, (int, float)) else CUE[x]["t"]


def music():
    out = []
    for name, a, b, kw in MUSIC_PLAN:
        out.append(dict(file=os.path.join(V.BUILD, "music", f"{name}.mp3"), start=_ct(a),
                        end=_ct(b) + 0.4 if b else L["duration"], **kw))
    return out


MUSIC = music()


def timeline_info():
    blast = CUE["c094"]["t"]
    return {"voice": L["voice"], "duration": L["duration"],
            "music_holes": [(CUE["c072"]["t"], CUE["c076"]["t"], -40.0),     # silence for Švec's family
                            (blast - 0.45, blast, -45.0)],                     # held breath before the blast
            "sfx": [(blast - 3.2, "riser", 0.9), (CUE["c018"]["t"], "impact", 1.0)]}


def timeline():
    """Shot specs with start, dur and frame ranges."""
    vis = [c for c in L["cues"] if c["id"] in SH]
    specs = []
    for k, c in enumerate(vis):
        T = c["t"] if k else 0.0
        end = vis[k + 1]["t"] if k + 1 < len(vis) else L["duration"]

        def a(sub, after=None, n=1, T=T):
            return word_t(sub, T - 0.3 if after is None else after, n) - T
        spec = SH[c["id"]](T, a)
        spec["id"] = c["id"]
        splits = spec.pop("split", [])
        bounds = [T] + [T + s for s, _ in splits] + [end]
        parts = [spec] + [s for _, s in splits]
        for p, (t0, t1) in zip(parts, zip(bounds, bounds[1:])):
            p.setdefault("id", f"{c['id']}b")
            p["start"] = t0
            specs.append(p)
            p["_end"] = t1
    for s in specs:
        f0 = round(s["start"] * V.FPS)
        f1 = round(s.pop("_end") * V.FPS)
        s["f0"], s["frames"] = f0, f1 - f0
        s["dur"] = s["frames"] / V.FPS
    return specs


if __name__ == "__main__":
    sp = timeline()
    for s in sp:
        miss = [k for k in ("img", "bg") if k in s and s[k] is None]
        print(f"{s['id']:6s} {s['start']:7.2f} {s['dur']:5.2f}s {s['type']:10s} "
              f"{s.get('img') or s.get('bg') or s.get('src') or ''} {'MISSING ' + str(miss) if miss else ''}")
    print(len(sp), "shots,", sum(s["frames"] for s in sp), "frames")
