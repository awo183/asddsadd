"""Every on-screen string, and the spoken words that cue each animation, in
English and Czech.

L(key) returns the text for the current FILM_LANG; N(key) returns the spoken
word(s) the animation waits for (matched against the narration's own word
timings, so each language is cued to its own voice). Numbers, dates and times
follow each language's conventions (1,178 / 1 178; 11:40 PM / 23:40;
April 14, 1912 / 14. dubna 1912).
"""
import os
import re

LANG = os.environ.get("FILM_LANG", "en")
_I = 0 if LANG == "en" else 1

TEXT = {
    # ---- hook
    "rms": ("RMS TITANIC · 1912", "RMS TITANIC · 1912"),
    "n_boats": ("20 LIFEBOATS", "20 ZÁCHRANNÝCH ČLUNŮ"),
    "more_than": ("MORE THAN THE LAW REQUIRED", "VÍC, NEŽ ŽÁDAL ZÁKON"),
    "more_word": ("MORE", "VÍC"),
    "sun_cap": ("THE SUN · NEW YORK · APRIL 16, 1912", "THE SUN · NEW YORK · 16. DUBNA 1912"),
    "approx_1500": ("≈1,500", "≈1 500"),
    "died": ("died", "mrtvých"),
    "berg_cap": ("ICEBERG PHOTOGRAPHED FROM THE CARPATHIA, APRIL 1912",
                 "LEDOVEC VYFOCENÝ Z CARPATHIE, DUBEN 1912"),
    "old_rule": ("an old rule", "staré pravidlo"),
    # ---- title
    "title": ("TWENTY BOATS", "DVACET ČLUNŮ"),
    "subtitle": ("Why the Titanic ran out of lifeboats", "Proč na Titanicu nebylo dost člunů"),
    # ---- rules
    "chart_title": ("The 1894 lifeboat table", "Tabulka záchranných člunů z roku 1894"),
    "chart_sub": ("boats required, by a ship’s gross tonnage",
                  "povinný počet člunů podle hrubé prostornosti lodi"),
    "covered": (("COVERED BY", "THE TABLE"), ("POKRYTO", "TABULKOU")),
    "gross_tons": ("GROSS TONS", "HRUBÁ TONÁŽ (BRT)"),
    "biggest": ("Biggest liner in 1894: ≈13,000", "Největší parník v roce 1894: ≈13 000"),
    "titanic_bar": ("TITANIC", "TITANIC"),
    "and_up": ("10,000 and up = 16 boats", "10 000 a víc = 16 člunů"),
    "quote_rule": (["“…as to all such vessels, whatever",
                    "their size might be, the minimum number",
                    "of boats under davits was fixed by the",
                    "table at 16…”"],
                   ["„…u všech takových lodí, ať byla jejich",
                    "velikost jakákoli, stanovila tabulka",
                    "minimální počet člunů pod jeřábky",
                    "na 16…“"]),
    "quote_rule_hot": ("whatever their size might be", "ať byla jejich velikost jakákoli"),
    "quote_rule_src": ("British Wreck Commissioner’s report, 1912",
                       "Zpráva britské vyšetřovací komise, 1912"),
    "seats_title": ("Lifeboat seats", "Místa v záchranných člunech"),
    "seats_sub": ("people", "lidí"),
    "seat_law": ("REQUIRED BY LAW", "VYŽADOVAL ZÁKON"),
    "seat_had": ("ON THE TITANIC", "MĚL TITANIC"),
    "seat_aboard": ("PEOPLE ON BOARD", "LIDÍ NA PALUBĚ"),
    "lifeboat_cap": ("A TITANIC LIFEBOAT, PHOTOGRAPHED FROM THE CARPATHIA",
                     "ČLUN Z TITANICU, VYFOCENÝ Z CARPATHIE"),
    "crowd_cap": ("WAITING FOR NEWS, NEW YORK, APRIL 1912", "ČEKÁNÍ NA ZPRÁVY, NEW YORK, DUBEN 1912"),
    "no_seat": ("1,000+ WITHOUT A SEAT", "1 000+ BEZ MÍSTA"),
    "aboard_val": ("2,200+", "2 200+"),
    # ---- ferry
    "wt_cap": ("THE WASHINGTON TIMES · APRIL 15, 1912 · AN EARLY, WRONG REPORT",
               "THE WASHINGTON TIMES · 15. DUBNA 1912 · PRVNÍ, MYLNÁ ZPRÁVA"),
    "radio_lbl": ("WIRELESS", "RÁDIO"),
    "ferry_strip": ("lifeboats = ferries", "čluny = převoz"),
    "sinking_ship": ("SHIP IN TROUBLE", "LOĎ V NOUZI"),
    "rescue_ship": ("RESCUE SHIP", "ZÁCHRANNÁ LOĎ"),
    "rep_cap": ("THE WASHINGTON TIMES · JANUARY 23, 1909", "THE WASHINGTON TIMES · 23. LEDNA 1909"),
    "saved_num": ("≈1,500", "≈1 500"),
    "saved_lbl": ("SAVED", "ZACHRÁNĚNÝCH"),
    "rep_year": ("1909", "1909"),
    # ---- night
    "southampton": ("SOUTHAMPTON", "SOUTHAMPTON"),
    "cherbourg": ("CHERBOURG", "CHERBOURG"),
    "queenstown": ("QUEENSTOWN", "QUEENSTOWN"),
    "newyork": ("NEW YORK", "NEW YORK"),
    "north_atlantic": ("NORTH ATLANTIC", "SEVERNÍ ATLANTIK"),
    "hit_time": ("11:40 PM · APRIL 14, 1912", "23:40 · 14. DUBNA 1912"),
    "comp_title": ("16 watertight compartments", "16 vodotěsných oddílů"),
    "bow": ("BOW", "PŘÍĎ"),
    "flooded": ("FLOODED: 5", "ZAPLAVENO: 5"),
    "survive4": ("BUILT TO SURVIVE 4", "VYDRŽÍ NANEJVÝŠ 4"),
    "comp_note": ("Simplified diagram", "Zjednodušené schéma"),
    "time_left": ("2 h 40 min", "2 h 40 min"),
    "time_span": ("11:40 PM → 2:20 AM", "23:40 → 2:20"),
    # ---- radio
    "californian": ("CALIFORNIAN", "CALIFORNIAN"),
    "carpathia": ("CARPATHIA", "CARPATHIA"),
    "titanic": ("TITANIC", "TITANIC"),
    "lt20": ("< 20 MILES", "< 20 MIL"),
    "asleep": ("RADIO OFF · OPERATOR ASLEEP", "RÁDIO VYPNUTO · RADISTA SPÍ"),
    "mi58": ("58 MILES", "58 MIL"),
    "sank": ("SANK 2:20 AM", "POTOPENÍ 2:20"),
    "arrived": ("CARPATHIA ARRIVES ≈4:00 AM", "CARPATHIA DORAZÍ ≈4:00"),
    "too_late": ("TOO LATE", "POZDĚ"),
    "map_note": ("Positions approximate", "Polohy jsou přibližné"),
    "cal_cap": ("THE CALIFORNIAN, APRIL 15, 1912", "CALIFORNIAN, 15. DUBNA 1912"),
    "carp_cap": ("THE CARPATHIA IN NEW YORK · 1912 NEWSREEL", "CARPATHIA V NEW YORKU · ŽURNÁL Z ROKU 1912"),
    "olympic_cap": ("FILMED ON THE OLYMPIC, THE TITANIC’S SISTER SHIP · 1912 NEWSREEL",
                    "NATOČENO NA OLYMPICU, SESTERSKÉ LODI TITANICU · ŽURNÁL Z ROKU 1912"),
    "walker_cap": ("“AN UNSINKABLE TITANIC”, 1912", "Z KNIHY „AN UNSINKABLE TITANIC“, 1912"),
    # ---- boats
    "boats_cap": ("TITANIC LIFEBOATS NEARING THE CARPATHIA · APRIL 15, 1912",
                  "ČLUNY Z TITANICU MÍŘÍ KE CARPATHII · 15. DUBNA 1912"),
    "half_empty": ("half empty", "poloprázdné"),
    "boat7": ("LIFEBOAT 7 · FIRST LOWERED", "ČLUN Č. 7 · SPUŠTĚN PRVNÍ"),
    "seats65": ("65 SEATS", "65 MÍST"),
    "aboard28": ("28 ABOARD", "28 LIDÍ"),
    "seats1178": ("1,178 SEATS", "1 178 MÍST"),
    "surv710": ("≈710 SURVIVED", "≈710 PŘEŽILO"),
    "empty470": ("≈470 SEATS EMPTY", "≈470 MÍST ZŮSTALO VOLNÝCH"),
    # ---- after
    "solas": ("SOLAS · LONDON, JANUARY 20, 1914", "SOLAS · LONDÝN, 20. LEDNA 1914"),
    "solas_full": ("International Convention for the Safety of Life at Sea",
                   "Mezinárodní úmluva o bezpečnosti lidského života na moři"),
    "rule1": ("A LIFEBOAT SEAT FOR EVERYONE ON BOARD", "MÍSTO VE ČLUNU PRO KAŽDÉHO NA PALUBĚ"),
    "rule2": ("RADIO WATCH, DAY AND NIGHT", "RADIOVÁ SLUŽBA VE DNE V NOCI"),
    "rule3": ("AN ICE PATROL IN THE NORTH ATLANTIC", "LEDOVÁ HLÍDKA V SEVERNÍM ATLANTIKU"),
    "iip_cap": ("THE INTERNATIONAL ICE PATROL AT WORK, 1948", "MEZINÁRODNÍ LEDOVÁ HLÍDKA PŘI PRÁCI, 1948"),
    "end1": (["THE TITANIC DIDN’T", "BREAK THE RULES."], ["TITANIC ŽÁDNÉ PRAVIDLO", "NEPORUŠIL."]),
    "end1_hot": (("BREAK THE RULES.", 1), ("NEPORUŠIL.", 1)),
    "end2": ("THAT WAS THE PROBLEM.", "A PRÁVĚ V TOM BYL TEN PROBLÉM."),
    # ---- end card
    "end_title": ("TWENTY BOATS", "DVACET ČLUNŮ"),
    "credits_head": ("SOURCES & CREDITS", "ZDROJE A PODĚKOVÁNÍ"),
    "narration_credit": ("Narration: synthetic voice (ElevenLabs)",
                         "Vypravěč: syntetický hlas (ElevenLabs)"),
    "music_credit": ("Music and sound: original, synthesized for this film",
                     "Hudba a zvuky: původní, syntetizované pro tento film"),
    "maps_credit": ("Maps: Natural Earth (public domain)", "Mapy: Natural Earth (volné dílo)"),
    "fonts_credit": ("Type: Archivo, Libre Caslon Text, Playfair Display (SIL OFL)",
                     "Písma: Archivo, Libre Caslon Text, Playfair Display (SIL OFL)"),
    "illus_note": ("Diagrams, maps and charts are illustrations drawn for this film.",
                   "Schémata, mapy a grafy jsou ilustrace vytvořené pro tento film."),
}

# Spoken words each animation waits for (a word prefix, or several words).
NEEDLE = {
    # hook
    "h_lifeboats": ("lifeboats", "záchranných"),
    "h_law": ("law", "zákon"),
    "h_why": ("so why", "tak proč"),
    "h_1500": ("fifteen", "tisíc pět"),
    "h_die": ("die", "zahynulo"),
    "h_iceberg": ("iceberg", "ledovec"),
    "h_rule": ("old rule", "staré pravidlo"),
    # rules
    "r_size": ("size", "velikosti"),
    "r_1894": ("eighteen", "osmnáct"),
    "r_biggest": ("biggest", "největší"),
    "r_stopped": ("stopped", "končila"),
    "r_ten": ("ten thousand", "deset tisíc"),
    "r_titanic": ("titanic was", "titanic měl"),
    "r_same": ("same", "nelišil"),
    "r_fifth": ("fifth", "pětkrát"),
    "r_962": ("nine hundred", "devět set"),
    "r_1178": ("eleven hundred", "tisíc sto"),
    "r_board": ("board", "palubě"),
    "r_2200": ("twenty-two", "dva tisíce"),
    # ferry
    "f_why": ("why not", "proč to"),
    "f_watertight": ("watertight", "vodotěsné"),
    "f_radio": ("radio", "rádiem"),
    "f_lifeboats": ("lifeboats weren't", "čluny neměly"),
    "f_ferries": ("ferries", "převážet"),
    "f_rescue": ("rescue", "záchranné"),
    "f_1909": ("nineteen-oh-nine", "devatenáct set devět"),
    "f_republic": ("republic", "republic"),
    "f_fog": ("fog", "mlze"),
    "f_radioed": ("radioed", "rádiem přivolal"),
    "f_1500": ("fifteen", "tisíc pět"),
    "f_safety": ("safety", "bezpečí"),
    # night
    "n_eleven": ("eleven", "čtrnáctého"),
    "n_iceberg": ("iceberg", "ledovec"),
    "n_five": ("five", "pět"),
    "n_flooded": ("flooded", "oddílů"),
    "n_four": ("four", "čtyři"),
    "n_two": ("two hours", "dvě hodiny"),
    "n_forty": ("forty", "čtyřicet"),
    # radio
    "c_nearest": ("nearest", "nejbližší"),
    "c_californian": ("californian", "californian"),
    "c_twenty": ("twenty", "dvacet"),
    "c_operator": ("operator", "radista"),
    "c_bed": ("bed", "spal"),
    "c_carpathia": ("carpathia", "carpathia"),
    "c_call": ("call", "volání"),
    "c_58": ("fifty-eight", "padesát osm"),
    "c_arrived": ("arrived", "dorazila"),
    "c_late": ("too late", "pozdě"),
    # boats
    "b_plan": ("ferry plan", "plán"),
    "b_half": ("half", "poloprázdné"),
    "b_first": ("first one", "první"),
    "b_65": ("sixty-five", "šedesát pět"),
    "b_28": ("twenty-eight", "dvacet osm"),
    "b_710": ("seven hundred", "sedm set"),
    "b_room": ("room", "vešlo"),
    "b_1178": ("eleven hundred", "tisíc sto"),
    # after
    "a_two": ("within two", "do dvou"),
    "a_treaty": ("treaty", "úmluvu"),
    "a_seat": ("lifeboat seat", "místo ve"),
    "a_radios": ("radios", "radiostanice"),
    "a_ice": ("ice patrol", "ledovou hlídku"),
    "a_still": ("still", "dodnes"),
    "a_didnt": ("didn't", "žádné"),
    "a_break": ("break", "neporušil"),
    "a_problem": ("problem", "problém"),
}


def _nbsp(v):
    """Czech thousands separators become non-breaking spaces (1 178 never splits)."""
    if isinstance(v, str):
        return re.sub(r"(\d) (\d{3})", "\\1\u00a0\\2", v)
    if isinstance(v, (list, tuple)):
        return type(v)(_nbsp(x) for x in v)
    return v


def L(key):
    return _nbsp(TEXT[key][_I]) if LANG == "cs" else TEXT[key][_I]


def N(key):
    return NEEDLE[key][_I]


def num(n):
    """1,178 in English, 1 178 in Czech (non-breaking space)."""
    s = f"{n:,}"
    return s if LANG == "en" else s.replace(",", " ")
