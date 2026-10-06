"""Every on-screen string, and the narration words that cue it, in each language.

L(key) returns the text for the current FILM_LANG; N(key) returns the spoken
word the animation is timed to (looked up inside the narration sentence).
"""
import os

LANG = os.environ.get("FILM_LANG", "en")

TEXT = {
    # hook
    "w_hijacked": ("HIJACKED", "UNESL"),
    "w_money": ("$200,000", "200 000 $"),
    "w_vanished": ("VANISHED", "ZMIZEL"),
    "never": ("NEVER SEEN AGAIN.", "UŽ HO NIKDO NEVIDĚL."),
    "calm": ("CALM.", "KLID."),
    # title
    "title1": ("THE CALMEST MAN", "NEJKLIDNĚJŠÍ MUŽ"),
    "title2": ("ON THE PLANE", "V LETADLE"),
    "title3": ("THE D.B. COOPER HIJACKING  ·  1971", "ÚNOS D. B. COOPERA  ·  1971"),
    # note
    "lt_date": ("NOVEMBER 24, 1971", "24. LISTOPADU 1971"),
    "lt_flight": ("PORTLAND, OREGON  ·  NORTHWEST ORIENT FLIGHT 305",
                  "PORTLAND, OREGON  ·  LET NORTHWEST ORIENT 305"),
    "pass_label": ("PASSENGER", "CESTUJÍCÍ"),
    "pass_name": ('"DAN COOPER"', "„DAN COOPER“"),
    "pass_sub": ("ONE-WAY TICKET  ·  PAID CASH", "JEDNOSMĚRNÁ LETENKA  ·  HOTOVĚ"),
    "aircraft": ("THE AIRCRAFT: BOEING 727, N467US", "LETADLO: BOEING 727, N467US"),
    "bourbon": ("BOURBON & SODA", "BOURBON SE SODOU"),
    "a_note": ("— A NOTE", "— VZKAZ"),
    "note1": ("I HAVE A BOMB", "MÁM BOMBU"),
    "note2": ("IN MY BRIEFCASE.", "V AKTOVCE."),
    "note_cap": ("Note wording as later recalled by the flight attendant",
                 "Znění vzkazu podle pozdější výpovědi letušky"),
    "quote_attr": ("— to flight attendant Florence Schaffner",
                   "— letušce Florence Schaffnerové"),
    # demands
    "analysis": ("BEHAVIOUR ANALYSIS", "ANALÝZA CHOVÁNÍ"),
    "notice1": ("NOTICE WHAT HE", "VŠIMNĚTE SI,"),
    "notice2": ("DOESN'T DO.", "CO NEDĚLÁ."),
    "item_shout": ("SHOUTING", "KŘIK"),
    "item_threat": ("THREATS", "VÝHRŮŽKY"),
    "item_aware": ("PASSENGERS AWARE", "VYDĚŠENÍ CESTUJÍCÍ"),
    "demands": ("DEMANDS", "POŽADAVKY"),
    "d_money": ("$200,000", "200 000 $"),
    "d_money_sub": ('"negotiable American currency"', "„v obchodovatelné americké měně“"),
    "d_chutes": ("4 PARACHUTES", "4 PADÁKY"),
    "d_chutes_sub": ("two main, two reserve", "dva hlavní, dva záložní"),
    "d_fuel": ("FUEL TRUCK", "CISTERNA"),
    "d_fuel_sub": ("waiting in Seattle", "připravená v Seattlu"),
    "him": ("HIM", "ON"),
    "hostage": ("A HOSTAGE COULD BE FORCED TO JUMP TOO", "RUKOJMÍ BY MUSEL SKOČIT S NÍM"),
    "tamper": ("— NO ONE DARES TAMPER WITH THE CHUTES", "— NIKDO SE NEODVÁŽÍ PADÁKY POŠKODIT"),
    "deception": ("STRATEGIC DECEPTION", "STRATEGICKÝ KLAM"),
    "not_panic": ("NOT PANIC.", "ŽÁDNÁ PANIKA."),
    "a_plan": ("A PLAN", "PLÁN"),
    # orders
    "crew_cap": ("THE CREW OF FLIGHT 305  ·  NEVADA STATE JOURNAL, 1971",
                 "POSÁDKA LETU 305  ·  NEVADA STATE JOURNAL, 1971"),
    "released": ("PASSENGERS  — RELEASED", "CESTUJÍCÍ  — PROPUŠTĚNI"),
    "onboard": ("$200,000 + 4 PARACHUTES  — ON BOARD", "200 000 $ + 4 PADÁKY  — NA PALUBĚ"),
    "instr": ("HIJACKER'S INSTRUCTIONS", "POKYNY ÚNOSCE"),
    "r_dest": (("DESTINATION", "MEXICO CITY"), ("CÍL", "MEXIKO")),
    "r_alt": (("ALTITUDE", "BELOW 10,000 FT"), ("VÝŠKA", "POD 10 000 STOP")),
    "r_speed": (("AIRSPEED", "MINIMUM"), ("RYCHLOST", "MINIMÁLNÍ")),
    "r_gear": (("LANDING GEAR", "DOWN"), ("PODVOZEK", "VYSUNUTÝ")),
    "r_flaps": (("WING FLAPS", "15°"), ("KLAPKY", "15°")),
    "r_cabin": (("CABIN", "UNPRESSURIZED"), ("KABINA", "BEZ PŘETLAKU")),
    "plane": ("BOEING 727", "BOEING 727"),
    "plane_sub": ("Side view (illustration)", "Boční pohled (ilustrace)"),
    "stair": ("AFT AIRSTAIR", "ZADNÍ SCHODY"),
    "stair_sub": ("CAN BE LOWERED IN FLIGHT", "LZE SPUSTIT ZA LETU"),
    # jump
    "time": ("8:13 PM", "20:13"),
    "date": ("NOVEMBER 24, 1971", "24. LISTOPADU 1971"),
    "jump_area": ("ESTIMATED JUMP AREA", "ODHADOVANÉ MÍSTO SESKOKU"),
    "sw_wa": ("SOUTHWEST WASHINGTON", "JIHOZÁPADNÍ WASHINGTON"),
    "jolt": ("THE TAIL JOLTS UPWARD", "OCAS TRHNE VZHŮRU"),
    "empty": ("CABIN: EMPTY", "KABINA: PRÁZDNÁ"),
    "st_wa": ("WASHINGTON", "WASHINGTON"),
    "st_or": ("OREGON", "OREGON"),
    "st_nv": ("NEVADA", "NEVADA"),
    "st_id": ("IDAHO", "IDAHO"),
    "st_ca": ("CALIFORNIA", "KALIFORNIE"),
    # profile
    "bulletin": ("FBI BULLETIN, 1971", "BULLETIN FBI, 1971"),
    "theory": ("THE FBI'S FIRST THEORY", "PRVNÍ TEORIE FBI"),
    "expert1": ("AN EXPERT", "ZKUŠENÝ"),
    "expert2": ("SKYDIVER", "PARAŠUTISTA"),
    "wrong": ("WRONG", "OMYL"),
    "carr": (['"No experienced parachutist would have',
              'jumped in the pitch-black night, in the rain,',
              'with a 200-mile-an-hour wind in his face,',
              'wearing loafers and a trench coat."'],
             ["„Žádný zkušený parašutista by neskočil",
              "za tmy jako v pytli, v dešti,",
              "s větrem 320 km/h v obličeji,",
              "v mokasínech a v trenčkotu.“"]),
    "carr_attr": ("— FBI Special Agent Larry Carr, 2007", "— zvláštní agent FBI Larry Carr, 2007"),
    "contradiction": ("THE CONTRADICTION", "ROZPOR"),
    "hijacking": ("THE HIJACKING", "ÚNOS"),
    "landing": ("THE LANDING", "PŘISTÁNÍ"),
    "left": (["THE NOTE", "THE DEMANDS", "FOUR PARACHUTES", "THE FLIGHT PLAN", "THE REAR STAIRS"],
             ["VZKAZ", "POŽADAVKY", "ČTYŘI PADÁKY", "LETOVÝ PLÁN", "ZADNÍ SCHODY"]),
    "right": (["JUMPED AT NIGHT", "INTO A RAINSTORM", "IN LOAFERS", "RESERVE CHUTE SEWN SHUT*"],
              ["SKOK V NOCI", "DO BOUŘKY", "V MOKASÍNECH", "ZÁLOŽNÍ PADÁK ZAŠITÝ*"]),
    "chute_note": ("*per the FBI: one reserve chute was a training dummy, sewn shut",
                   "*podle FBI: jeden záložní padák byl cvičný a zašitý"),
    # money
    "tena": ("TENA BAR, COLUMBIA RIVER", "TENA BAR, ŘEKA COLUMBIA"),
    "feb": ("FEBRUARY 1980", "ÚNOR 1980"),
    "found_by": ("FOUND BY AN 8-YEAR-OLD BOY", "NAŠEL JE OSMILETÝ CHLAPEC"),
    "match": ("SERIAL NUMBERS MATCH", "SÉRIOVÁ ČÍSLA SEDÍ"),
    "rest": ("$194,200", "194 200 $"),
    "never_found": ("NEVER FOUND.", "NIKDY NENALEZENO."),
    "unsolved": ("UNSOLVED", "NEVYŘEŠENO"),
    "fbi_end": ("FBI ENDED ITS ACTIVE INVESTIGATION IN JULY 2016",
                "FBI UKONČILA AKTIVNÍ VYŠETŘOVÁNÍ V ČERVENCI 2016"),
    # end
    "end_title": ("THE CALMEST MAN ON THE PLANE", "NEJKLIDNĚJŠÍ MUŽ V LETADLE"),
    "credits": ([("NARRATION", "Synthetic voice · {voice}"),
                 ("ARCHIVAL", "FBI sketches, bulletin & evidence photo (public domain)"),
                 ("", "Crew photo: Nevada State Journal, 1971 (public domain)"),
                 ("", "N467US photo: Clint Groves via Wikimedia Commons (GFDL 1.2)"),
                 ("B-ROLL", "NASA (public domain, illustrative)"),
                 ("MAP DATA", "Natural Earth")],
                [("VYPRÁVĚNÍ", "Syntetický hlas · {voice}"),
                 ("ARCHIV", "Kresby, bulletin a důkazní foto FBI (volné dílo)"),
                 ("", "Foto posádky: Nevada State Journal, 1971 (volné dílo)"),
                 ("", "Foto N467US: Clint Groves, Wikimedia Commons (GFDL 1.2)"),
                 ("ZÁBĚRY", "NASA (volné dílo, ilustrační)"),
                 ("MAPY", "Natural Earth")]),
}

# Words in the narration that each animation waits for.
NEEDLE = {
    "hijacked": ("hijacked", "unesl"),
    "money": ("two hundred", "dvě stě"),
    "jumped": ("jumped", "seskočil"),
    "calm": ("calm", "klid"),
    "dan": ("dan cooper", "dan cooper"),
    "bourbon": ("bourbon", "bourbon"),
    "note": ("a note", "vzkaz"),
    "isnt": ("it isn't", "nedává"),
    "bomb": ("bomb", "bombu"),
    "doesnt": ("doesn't do", "nedělá"),
    "shout": ("shout", "nekřičí"),
    "threaten": ("threaten", "nevyhrožuje"),
    "realize": ("never realize", "nepostřehne"),
    "two_hundred": ("two hundred", "dvě stě"),
    "four_chutes": ("four parachutes", "čtyři padáky"),
    "hostage": ("hostage", "rukojmí"),
    "sabotaged": ("sabotaged", "poškozený"),
    "panic": ("panic", "panika"),
    "plan": ("plan", "plán"),
    "trades": ("trades", "vymění"),
    "cash": ("for the cash", "za peníze"),
    "mexico": ("mexico", "mexika"),
    "low": ("low and", "nízko"),
    "slow": ("slow", "pomalu"),
    "gear": ("landing gear", "podvozek"),
    "cabin": ("cabin", "kabina"),
    "stair": ("rear staircase", "zadní schody"),
    "jolts": ("jolts", "trhne"),
    "gone": ("gone", "pryč"),
    "expert": ("expert", "zkušeného"),
    "skydiver": ("skydiver", "parašutistu"),
    "opposite": ("opposite", "opaku"),
    "night": ("at night", "v noci"),
    "rain": ("rain", "dešti"),
    "loafers": ("loafers", "mokasínech"),
    "trench": ("trench", "trenčkotu"),
    "planned": ("planned", "naplánoval"),
    "nothing": ("almost nothing", "skoro nic"),
    "neither": ("neither", "stejně"),
    "unsolved": ("unsolved", "nevyřešený"),
}

# Words of the "I have a bomb" line shown in red, and the Carr-quote words
# highlighted as they are spoken: {quote word prefix: needle key}.
QUOTE_HOT = ({"i", "have", "a", "bomb"}, {"mám", "bombu"})
CARR_HOT = ({"pitch-black": "night", "rain,": "rain", "loafers": "loafers", "trench": "trench"},
            {"tmy": "night", "dešti,": "rain", "mokasínech": "loafers", "trenčkotu.“": "trench"})

_I = 0 if LANG == "en" else 1


def L(key):
    return TEXT[key][_I]


def N(key):
    return NEEDLE[key][_I]


def money(n):
    return f"${n:,}" if LANG == "en" else f"{n:,} $".replace(",", " ")


QUOTE_HOT_WORDS = QUOTE_HOT[_I]
CARR_HOT_WORDS = CARR_HOT[_I]
