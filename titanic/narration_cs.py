"""Czech narration for "Dvacet člunů" (proč na Titanicu zemřelo tolik lidí).

One string per sentence; numbers are written out the way they should be spoken.
Sentence order and count match narration.py so both cuts share one scene plan.
The Czech cut is timed to its own voice and may run longer; nothing is trimmed.
"""

SEGMENTS = [
    ("hook", [
        "Titanic vezl víc záchranných člunů, než mu předepisoval zákon.",
        "Tak proč zahynulo asi tisíc pět set lidí?",
        "Loď potopil ledovec. Jenže to, že s ní zemřelo tolik lidí, má na svědomí jedno "
        "staré pravidlo.",
    ]),
    ("rules", [
        "Britský zákon určoval počet člunů podle velikosti lodi, a to tabulkou, kterou "
        "naposledy upravili v roce osmnáct set devadesát čtyři.",
        "Největší parník měl tehdy kolem třinácti tisíc tun. Tabulka proto končila kategorií "
        "deset tisíc tun a víc.",
        "Titanic měl čtyřicet šest tisíc. Pro zákon se ale nelišil od lodi pětkrát menší.",
        "Předpisy tak žádaly devět set šedesát dva míst. Titanic jich měl tisíc sto "
        "sedmdesát osm.",
        "Na palubě ale bylo přes dva tisíce dvě stě lidí.",
    ]),
    ("ferry", [
        "Proč to nikdo nezměnil? Lodě už měly vodotěsné oddíly. A rádiem se dala přivolat "
        "pomoc.",
        "Čluny neměly pojmout všechny najednou. Měly lidi jen převážet na záchranné lodě.",
        "V roce devatenáct set devět to fungovalo. Parník Republic se v mlze srazil s jinou "
        "lodí, rádiem přivolal pomoc a čluny převezly do bezpečí zhruba tisíc pět set lidí.",
    ]),
    ("night", [
        "Čtrnáctého dubna, dvacet minut před půlnocí, narazil Titanic na ledovec.",
        "Voda zaplavila pět oddílů. Loď přitom vydržela nanejvýš čtyři.",
        "Zbývaly jí dvě hodiny a čtyřicet minut.",
    ]),
    ("radio", [
        "Nejbližší loď, Californian, byla necelých dvacet mil daleko. Její jediný radista "
        "ale už spal.",
        "Carpathia volání zachytila, jenže byla padesát osm mil daleko. Dorazila víc než "
        "hodinu a půl pozdě.",
    ]),
    ("boats", [
        "Plán s převážením se zhroutil. A čluny odplouvaly poloprázdné.",
        "První spuštěný člun měl místo pro šedesát pět lidí. Sedělo v něm dvacet osm.",
        "Přežilo asi sedm set deset lidí, v člunech, kam se vešlo tisíc sto sedmdesát osm.",
    ]),
    ("after", [
        "Do dvou let státy podepsaly první úmluvu o bezpečnosti na moři: místo ve člunu pro "
        "každého a radiostanice v provozu ve dne v noci.",
        "A také ledovou hlídku, která severní Atlantik sleduje dodnes.",
        "Titanic žádné pravidlo neporušil. A právě v tom byl ten problém.",
    ]),
]
