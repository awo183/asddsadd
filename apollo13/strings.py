"""Every on-screen string of "The 28-Volt Switch", in English and Czech, and the
narration words each animation is cued to.

L(key) -> text for the current FILM_LANG.  CUE[key] -> (English phrase, Czech phrase):
the scene looks the phrase up in ElevenLabs' word timings and starts the animation
when that word is actually spoken. Nothing English appears in the Czech cut except
proper names and the genuine archival documents (which get Czech captions).
"""
import os

LANG = os.environ.get("FILM_LANG", "en")
_I = 0 if LANG == "en" else 1

TEXT = {
    # ---- hook
    "date_13": ("APRIL 13, 1970", "13. DUBNA 1970"),
    "earth": ("EARTH", "ZEMĚ"),
    "moon": ("MOON", "MĚSÍC"),
    "boom": ("OXYGEN TANK NO. 2 EXPLODES", "VYBUCHNE KYSLÍKOVÁ NÁDRŽ Č. 2"),
    "dist": ("200,000 MILES FROM EARTH", "320 000 KM OD ZEMĚ"),
    "route": ("APOLLO 13", "APOLLO 13"),
    "map_note": ("Not to scale", "Není v měřítku"),
    "quote": ("“Houston, we've had a problem.”", "„Houstone, máme problém.“"),
    "quote_hot": ("we've had a problem.”", "máme problém.“"),
    "quote_attr": ("The Apollo 13 crew to Mission Control, April 13, 1970",
                   "Posádka Apolla 13 řídicímu středisku, 13. dubna 1970"),
    "mcc_cap": ("Mission Control, Houston, April 1970", "Řídicí středisko v Houstonu, duben 1970"),
    "ground": ("IT STARTED ON THE GROUND", "ZAČALO TO NA ZEMI"),
    "pad_cap": ("Apollo 13 on the pad during its countdown test, Kennedy Space Center, March 24, 1970",
                "Apollo 13 na rampě během zkušebního odpočítávání, Kennedyho středisko, 24. března 1970"),
    "two_weeks": ("2 WEEKS BEFORE LAUNCH", "2 TÝDNY PŘED STARTEM"),
    "rated28": ("BUILT FOR 28 VOLTS", "STAVĚNÝ NA 28 VOLTŮ"),
    "q": (["HOW DOES", "ONE SMALL SWITCH", "NEARLY KILL", "THREE ASTRONAUTS?"],
          ["JAK MŮŽE", "JEDNA MALÁ SOUČÁSTKA", "MÁLEM ZABÍT", "TŘI ASTRONAUTY?"]),
    "crew_cap": ("The crew heads to the pad, April 11, 1970", "Posádka cestou na rampu, 11. dubna 1970"),
    "crew_names": ("LOVELL · SWIGERT · HAISE", "LOVELL · SWIGERT · HAISE"),
    # ---- title
    "title1": ("THE 28-VOLT", "SPÍNAČ"),
    "title2": ("SWITCH", "NA 28 VOLTŮ"),
    "title_hot": ("28-VOLT", "28 VOLTŮ"),
    "title_sub": ("Why Apollo 13's oxygen tank exploded", "Proč na Apollu 13 vybuchla kyslíková nádrž"),
    # ---- switch
    "tank": ("OXYGEN TANK NO. 2", "KYSLÍKOVÁ NÁDRŽ Č. 2"),
    "heater": ("HEATER", "TOPENÍ"),
    "fan": ("FAN", "VENTILÁTOR"),
    "tswitch": ("THERMOSTATIC SWITCH", "TERMOSTATICKÝ SPÍNAČ"),
    "diagram": ("Simplified diagram", "Zjednodušené schéma"),
    "limit": ("80 °F", "27 °C"),
    "opens": ("OPENS: HEATER OFF", "ROZPOJÍ SE: TOPENÍ VYPNUTO"),
    # ---- volts
    "power": ("HEATER POWER", "NAPÁJENÍ TOPENÍ"),
    "bar1": ("1962 DESIGN", "NÁVRH 1962"),
    "bar1_sub": ("spacecraft power", "palubní síť lodi"),
    "bar2": ("1965 CHANGE", "ZMĚNA 1965"),
    "bar2_sub": ("launch-pad power", "napájení na rampě"),
    "volts_unit": ("V", "V"),
    "times": ("2.3×", "2,3×"),
    "switch_rated": ("SWITCHES STILL RATED FOR 28 V", "SPÍNAČE ZŮSTALY NA 28 V"),
    "doc_src_52": ("Report of Apollo 13 Review Board, NASA, June 1970, p. 5-2",
                   "Zpráva vyšetřovací komise Apolla 13, NASA, červen 1970, s. 5-2"),
    "tr_nochange": ("", "„…nezměnila specifikaci spínačů, aby odpovídala 65 V.“"),
    "tr_oversight": ("", "„Bylo to vážné přehlédnutí, na kterém se podílely všechny strany.“"),
    "doc_label": ("ORIGINAL DOCUMENT", "PŮVODNÍ DOKUMENT"),
    # ---- drop
    "boulder": ("BOULDER, COLORADO", "BOULDER, COLORADO"),
    "boulder_sub": ("Beech Aircraft builds the tank", "Beech Aircraft vyrábí nádrž"),
    "downey": ("DOWNEY, CALIFORNIA", "DOWNEY, KALIFORNIE"),
    "downey_sub": ("North American Rockwell plant", "Závod North American Rockwell"),
    "date_drop": ("OCTOBER 21, 1968", "21. ŘÍJNA 1968"),
    "drop_amt": ("SHELF DROPS ~2 INCHES", "POLICE SPADNE O ~5 CM"),
    "tube": ("A LOOSE FILL TUBE, PROBABLY KNOCKED OUT OF PLACE",
             "UVOLNĚNÁ PLNICÍ TRUBIČKA, NEJSPÍŠ POSUNUTÁ"),
    "pacific": ("PACIFIC OCEAN", "TICHÝ OCEÁN"),
    "atlantic": ("ATLANTIC OCEAN", "ATLANTSKÝ OCEÁN"),
    "usa": ("UNITED STATES", "SPOJENÉ STÁTY"),
    "mistake2": ("MISTAKE NO. 2", "CHYBA Č. 2"),
    "mistake1": ("MISTAKE NO. 1", "CHYBA Č. 1"),
    "mistake3": ("MISTAKE NO. 3", "CHYBA Č. 3"),
    # ---- detank
    "ksc": ("KENNEDY SPACE CENTER, FLORIDA", "KENNEDYHO VESMÍRNÉ STŘEDISKO, FLORIDA"),
    "date_detank": ("MARCH 27–28, 1970", "27.–28. BŘEZNA 1970"),
    "wont_empty": ("TANK NO. 2 WON'T EMPTY", "NÁDRŽ Č. 2 NEJDE VYPRÁZDNIT"),
    "heaters_on": ("HEATERS ON AT 65 V", "TOPENÍ ZAPNUTÉ NA 65 V"),
    "hours": ("HOURS", "HODIN"),
    "hours_n": ("{n} H", "{n} H"),
    "firing_cap": ("Launch control, Kennedy Space Center (NASA film, April 1970)",
                   "Řízení startu, Kennedyho vesmírné středisko (film NASA, duben 1970)"),
    # ---- weld
    "fused_cap": ("A switch welded shut when NASA re-ran the Kennedy test, June 1970",
                  "Spínač svařený, když NASA zopakovala test z Kennedyho střediska, červen 1970"),
    "welded": ("WELDED SHUT", "SVAŘENO"),
    "temp_title": ("HEATER TUBE TEMPERATURE, ESTIMATE", "TEPLOTA TOPNÉ TRUBKY, ODHAD"),
    "temp_limit": ("SWITCH LIMIT 80 °F", "LIMIT SPÍNAČE 27 °C"),
    "temp_peak": ("~1,000 °F", "~540 °C"),
    "temp_axis": ("HOURS OF HEATING", "HODINY OHŘEVU"),
    "insul": ("FAN WIRE INSULATION: DAMAGED", "IZOLACE DRÁTŮ VENTILÁTORU: POŠKOZENÁ"),
    "chart_note": ("Illustration of the review board's estimate", "Ilustrace podle odhadu vyšetřovací komise"),
    "wire": ("FAN WIRES", "DRÁTY VENTILÁTORU"),
    "nobody": ("NOBODY NOTICED", "NIKDO SI NEVŠIML"),
    "launch_cap": ("Apollo 13 lifts off, April 11, 1970 (NASA film)",
                   "Start Apolla 13, 11. dubna 1970 (film NASA)"),
    # ---- blast
    "met": ("MISSION TIME", "ČAS MISE"),
    "stir": ("“STIR THE TANKS”", "„PROMÍCHAT NÁDRŽE“"),
    "plus27": ("+2.7 S", "+2,7 S"),
    "short": ("SHORT CIRCUIT", "ZKRAT"),
    "fire": ("FIRE IN PURE OXYGEN", "POŽÁR V ČISTÉM KYSLÍKU"),
    "sm_cap": ("The service module, photographed by the crew as they cast it off, April 17, 1970",
               "Servisní modul, jak ho posádka vyfotila při odhození, 17. dubna 1970"),
    "panel": ("PANEL BLOWN OFF", "UTRŽENÝ PANEL"),
    "mcc2_cap": ("Mission Control during the oxygen failure, April 14, 1970",
                 "Řídicí středisko během havárie, 14. dubna 1970"),
    # ---- lifeboat
    "lm_cap": ("Jim Lovell inside the lunar module", "Jim Lovell v lunárním modulu"),
    "built": ("BUILT FOR", "STAVĚNÝ PRO"),
    "built_v": ("2 PEOPLE × 2 DAYS", "2 MUŽE × 2 DNY"),
    "used": ("STRETCHED TO", "NAKONEC"),
    "used_v": ("3 PEOPLE × 4 DAYS", "3 MUŽE × 4 DNY"),
    "load": ("3× THE LOAD", "3× VĚTŠÍ ZÁTĚŽ"),
    "splash": ("SPLASHDOWN, APRIL 17, 1970", "PŘISTÁNÍ NA HLADINĚ, 17. DUBNA 1970"),
    "spac": ("SOUTH PACIFIC", "JIŽNÍ PACIFIK"),
    "chutes_cap": ("Splashdown in the South Pacific, April 17, 1970", "Přistání v jižním Pacifiku, 17. dubna 1970"),
    "samoa": ("SAMOA", "SAMOA"),
    "fiji": ("FIJI", "FIDŽI"),
    "nz": ("NEW ZEALAND", "NOVÝ ZÉLAND"),
    "aus": ("AUSTRALIA", "AUSTRÁLIE"),
    # ---- verdict
    "doc_src_51": ("Report of Apollo 13 Review Board, p. 5-1", "Zpráva vyšetřovací komise Apolla 13, s. 5-1"),
    "doc_src_ammeter": ("Report of Apollo 13 Review Board, ch. 5, findings", "Zpráva vyšetřovací komise Apolla 13, kap. 5, zjištění"),
    "tr_combo": ("", "„…neobvyklá kombinace chyb…“"),
    "tr_ammeter": ("", "„Ovládání topení … mělo ampérmetry, které by ukázaly činnost termostatických spínačů.“"),
    "meter": ("HEATER CURRENT", "PROUD TOPENÍ"),
    "meter_note": ("Illustration", "Ilustrace"),
    "never_dropped": ("NEVER DROPPED", "NIKDY NEKLESL"),
    "final1": ("THE WARNING", "VAROVÁNÍ"),
    "final2": ("WAS ON A METER.", "BYLO NA MĚŘÁKU."),
    "final_hot": ("ON A METER.", "NA MĚŘÁKU."),
    # ---- end
    "end1": ("THE 28-VOLT SWITCH", "SPÍNAČ NA 28 VOLTŮ"),
    "credits": ([
        ("NARRATION", "Synthetic voice, ElevenLabs (Multilingual v2, “Jarnathan”)"),
        ("ARCHIVAL", "NASA photographs and film, public domain"),
        ("", "Report of Apollo 13 Review Board, NASA, June 1970, public domain"),
        ("MAPS", "Natural Earth, public domain"),
        ("GRAPHICS", "Diagrams and charts are illustrations based on the report"),
        ("TYPE", "Archivo and Libre Caslon Text (SIL Open Font License)"),
        ("MUSIC & SOUND", "Original, synthesized for this film"),
    ], [
        ("VYPRÁVĚNÍ", "Syntetický hlas, ElevenLabs (Multilingual v2, „Jarnathan“)"),
        ("ARCHIV", "Fotografie a filmy NASA, volné dílo"),
        ("", "Zpráva vyšetřovací komise Apolla 13, NASA, červen 1970, volné dílo"),
        ("MAPY", "Natural Earth, volné dílo"),
        ("GRAFIKA", "Schémata a grafy jsou ilustrace podle zprávy komise"),
        ("PÍSMO", "Archivo a Libre Caslon Text (SIL Open Font License)"),
        ("HUDBA A ZVUK", "Původní, syntetizované pro tento film"),
    ]),
    "photo_ids": ("NASA photo IDs: S70-34902, S70-32990, S70-40850, 108-KSC-70PC-105, S70-34852, "
                  "7010516, AS13-59-8484, S70-35638 · Film: KSC launch and recovery reels, April 1970",
                  "ID fotografií NASA: S70-34902, S70-32990, S70-40850, 108-KSC-70PC-105, S70-34852, "
                  "7010516, AS13-59-8484, S70-35638 · Film: záznamy startu a přistání, duben 1970"),
}

# Narration words that cue the animations: (English, Czech). Matched against the
# ElevenLabs word timings of each scene; "^" means the phrase must start a sentence.
CUE = {
    # hook
    "april": ("on april", "třináctého dubna"),
    "blew": ("blew apart", "vybuchla"),
    "miles": ("200,000 miles", "tři sta dvacet"),
    "know": ("you know", "větu"),
    "houston": ("houston", "houstone"),
    "problem": ("had a problem", "máme problém"),
    "space": ("didn't start in space", "nezačal ve vesmíru"),
    "ground": ("on the ground", "na zemi"),
    "two_weeks": ("two weeks", "dva týdny"),
    "tiny": ("tiny switch", "drobného spínače"),
    "28v": ("28 volts", "dvacet osm voltů"),
    "how": ("so how", "jak je možné"),
    "small": ("one small switch", "jedna malá"),
    "kill": ("nearly kill", "málem zabila"),
    "three": ("three astronauts", "tři astronauty"),
    # switch
    "heater": ("on a heater", "na topném"),
    "tank2": ("oxygen tank number", "kyslíkové nádrže"),
    "80f": ("80 degrees", "dvaceti sedmi"),
    "click": ("click open", "rozpojit"),
    "cut": ("cut the power", "vypnout proud"),
    # volts
    "design28": ("28 volts", "dvacet osm voltů"),
    "changed": ("specs changed", "změnily požadavky"),
    "65": ("65 volts", "šedesát pět voltů"),
    "upgraded": ("nobody upgraded", "spínače nikdo"),
    "caught": ("nobody caught", "nikdo nevšiml"),
    # drop
    "second": ("second mistake", "druhá chyba"),
    "y1968": ("in 1968", "šedesát osm"),
    "california": ("factory in california", "továrně v kalifornii"),
    "dropped": ("dropped the", "spadla"),
    "inches": ("two inches", "pět centimetrů"),
    "jolt": ("the jolt", "otřes"),
    "tube": ("loose tube", "uvolněnou trubičku"),
    # detank
    "march": ("march 1970", "v březnu"),
    "kennedy": ("kennedy space", "kennedyho"),
    "empty": ("wouldn't empty", "vyprázdnit"),
    "improvised": ("engineers improvised", "technici improvizovali"),
    "running": ("heaters running", "topení běžet"),
    "eight": ("eight hours", "osm hodin"),
    # weld
    "tried": ("tried to open", "pokusily rozpojit"),
    "welded": ("welded them", "svařilo"),
    "1000": ("1,000 degrees", "pět set čtyřicet"),
    "insulation": ("cooked the insulation", "spálilo izolaci"),
    "noticed": ("nobody noticed", "nikdo si"),
    "flew": ("tank flew", "nádrž letěla"),
    # blast
    "56": ("56 hours", "padesát šest"),
    "stir": ("stir the tanks", "promíchala"),
    "2.7": ("2.7 seconds", "dvě celé sedm"),
    "fans": ("fans came on", "zapnutí ventilátorů"),
    "shorted": ("wires shorted", "zkratovaly"),
    "fire": ("caught fire", "vzplanula"),
    "blast": ("the blast", "výbuch"),
    "panel": ("a panel", "celý panel"),
    # lifeboat
    "lm": ("lunar module", "lunárním modulu"),
    "two_men": ("two men", "dva muže"),
    "three_men": ("three men", "tři muže"),
    "four": ("for four", "čtyři dny"),
    # verdict
    "board": ("review board", "vyšetřovací komise"),
    "combo": ("unusual combination", "neobvyklou kombinaci"),
    "last": ("the last one", "ta poslední"),
    "controls": ("heater controls", "ovládání topení"),
    "meters": ("current meters", "ampérmetry"),
    "watching": ("anyone watching", "kdo by"),
    "never": ("never opened", "nikdy nerozpojily"),
    "warning": ("the warning", "varování"),
    "on_meter": ("on a meter", "na měřáku"),
}


def L(key):
    return TEXT[key][_I]


def C(key):
    return CUE[key][_I]


def num(n, decimals=0):
    """1,000 vs 1 000; 2.7 vs 2,7."""
    s = f"{n:,.{decimals}f}"
    if LANG == "cs":
        s = s.replace(",", " ").replace(".", ",")
    return s


def temp(f_value):
    """Temperatures: °F in English, °C in Czech."""
    if LANG == "en":
        return f"{num(f_value)} °F"
    return f"{num(round((f_value - 32) * 5 / 9))} °C"
