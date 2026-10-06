"""Czech narration for "Spínač na 28 voltů" (Apollo 13, 1970).

A natural Czech adaptation of narration.py, not a word-for-word translation.
Units are Czech (°C, km, cm). Numbers are written out as words so the voice
declines them correctly; SUBTITLE turns them back into digits for the .srt.
"""

SEGMENTS = [
    ("hook", [
        "Třináctého dubna tisíc devět set sedmdesát vybuchla na Apollu třináct kyslíková nádrž, "
        "víc než tři sta dvacet tisíc kilometrů od Země.",
        "Větu, která pak zazněla, znáte.",
        "„Houstone, máme problém.“",
        "Jenže ten problém nezačal ve vesmíru.",
        "Začal na zemi, dva týdny před startem, u drobného spínače stavěného na dvacet osm voltů.",
        "Jak je možné, že jedna malá součástka málem zabila tři astronauty?",
    ]),
    ("switch", [
        "Spínač seděl na topném tělese uvnitř kyslíkové nádrže číslo dvě.",
        "Při dvaceti sedmi stupních Celsia se měl rozpojit a vypnout proud.",
    ]),
    ("volts", [
        "Nádrž byla navržená na palubních dvacet osm voltů.",
        "Pak se ale změnily požadavky a na startovní rampě dostávalo topení šedesát pět voltů.",
        "Spínače nikdo nevyměnil a celé roky si toho nikdo nevšiml.",
    ]),
    ("drop", [
        "Druhá chyba přišla v roce tisíc devět set šedesát osm v továrně v Kalifornii, kde "
        "dělníkům spadla police s nádrží asi o pět centimetrů.",
        "Otřes nejspíš posunul uvolněnou trubičku uvnitř nádrže.",
    ]),
    ("detank", [
        "V březnu tisíc devět set sedmdesát proto na Kennedyho vesmírném středisku nešla "
        "nádrž číslo dvě vyprázdnit.",
        "Technici improvizovali a nechali topení běžet na šedesát pět voltů zhruba osm hodin.",
    ]),
    ("weld", [
        "Když se spínače konečně pokusily rozpojit, napětí je svařilo.",
        "Části topné trubky se nejspíš rozpálily asi na pět set čtyřicet stupňů a horko "
        "spálilo izolaci na drátech ventilátoru.",
        "Nikdo si ničeho nevšiml a nádrž letěla.",
    ]),
    ("blast", [
        "Skoro padesát šest hodin po startu požádalo řídicí středisko posádku, aby nádrže "
        "promíchala.",
        "Zhruba dvě celé sedm sekundy po zapnutí ventilátorů dráty zkratovaly, izolace "
        "v čistém kyslíku vzplanula a výbuch utrhl z lodi celý panel.",
    ]),
    ("lifeboat", [
        "Posádka se vrátila domů v lunárním modulu, který byl stavěný pro dva muže na dva dny, "
        "a nakonec musel udržet naživu tři muže po čtyři dny.",
    ]),
    ("verdict", [
        "Vyšetřovací komise to shrnula jako „neobvyklou kombinaci chyb“.",
        "A ta poslední mrzí nejvíc.",
        "Ovládání topení na Kennedyho středisku mělo ampérmetry.",
        "Kdo by se během těch osmi hodin díval, viděl by, že se spínače nikdy nerozpojily.",
        "Varování bylo celou dobu na očích, přímo na měřáku.",
    ]),
]

# Spoken form -> how the subtitles print it.
SUBTITLE = [
    ("Třináctého dubna tisíc devět set sedmdesát", "13. dubna 1970"),
    ("Apollu třináct", "Apollu 13"),
    ("tři sta dvacet tisíc kilometrů", "320 000 km"),
    ("dvacet osm voltů", "28 voltů"),
    ("dvaceti sedmi stupních Celsia", "27 °C"),
    ("šedesát pět voltů", "65 voltů"),
    ("v roce tisíc devět set šedesát osm", "v roce 1968"),
    ("pět centimetrů", "5 cm"),
    ("V březnu tisíc devět set sedmdesát", "V březnu 1970"),
    ("pět set čtyřicet stupňů", "540 °C"),
    ("padesát šest hodin", "56 hodin"),
    ("dvě celé sedm sekundy", "2,7 sekundy"),
]
