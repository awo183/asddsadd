"""Narration for "Twenty Boats" (why so many died on the Titanic).

One string per sentence; numbers are written the way they should be spoken.
Every factual claim is sourced in titanic/SCRIPT.md.
"""

SEGMENTS = [
    ("hook", [
        "The Titanic carried more lifeboats than the law required.",
        "So why did about fifteen hundred people die?",
        "The iceberg sank the ship. An old rule explains why so many died with it.",
    ]),
    ("rules", [
        "British lifeboat rules went by a ship's size, in a table last updated in eighteen "
        "ninety-four.",
        "Back then, the biggest liner was about thirteen thousand tons. So the table stopped "
        "at ten thousand and up.",
        "The Titanic was forty-six thousand. To the law, it was the same as a ship a fifth "
        "its size.",
        "So the rules asked for nine hundred and sixty-two seats. The Titanic had eleven "
        "hundred and seventy-eight.",
        "On board: more than twenty-two hundred people.",
    ]),
    ("ferry", [
        "Why not update it? Ships now had watertight compartments. And radio could call for "
        "help.",
        "Lifeboats weren't meant to hold everyone. They were ferries, out to rescue ships.",
        "In nineteen-oh-nine, it worked. The liner Republic, struck in fog, radioed for help, "
        "and about fifteen hundred people were ferried to safety.",
    ]),
    ("night", [
        "At eleven forty p.m. on April fourteenth, the Titanic hit an iceberg.",
        "Five compartments flooded. It was built to survive four.",
        "It had two hours and forty minutes.",
    ]),
    ("radio", [
        "The nearest ship, the Californian, was less than twenty miles away. Its only radio "
        "operator had gone to bed.",
        "The Carpathia heard the call, fifty-eight miles away. It arrived more than an hour "
        "and a half too late.",
    ]),
    ("boats", [
        "The ferry plan fell apart. And the boats left half empty.",
        "The first one lowered could hold sixty-five. It carried twenty-eight.",
        "About seven hundred and ten people survived, in boats with room for eleven hundred "
        "and seventy-eight.",
    ]),
    ("after", [
        "Within two years, nations signed the first treaty on safety at sea: a lifeboat seat "
        "for everyone, and radios staffed day and night.",
        "And an ice patrol that still watches the North Atlantic today.",
        "The Titanic didn't break the rules. That was the problem.",
    ]),
]
