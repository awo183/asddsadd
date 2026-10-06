"""English narration for "The 28-Volt Switch" (Apollo 13, 1970).

One string per sentence; each sentence is recorded separately by ElevenLabs.
Every factual claim is sourced in apollo13/SCRIPT.md.
"""

SEGMENTS = [
    ("hook", [
        "On April 13th, 1970, an oxygen tank on Apollo 13 blew apart, 200,000 miles from Earth.",
        "You know the line that came next.",
        "\"Houston, we've had a problem.\"",
        "But the problem didn't start in space.",
        "It started on the ground, two weeks before launch, with a tiny switch built for 28 volts.",
        "So how does one small switch nearly kill three astronauts?",
    ]),
    ("switch", [
        "The switch sat on a heater inside oxygen tank number two.",
        "At 80 degrees Fahrenheit, it was supposed to click open and cut the power.",
    ]),
    ("volts", [
        "The tank was designed for the spacecraft's 28 volts.",
        "Then the specs changed, and on the launch pad its heaters got 65 volts.",
        "Nobody upgraded the switches, and for years, nobody caught it.",
    ]),
    ("drop", [
        "The second mistake came in 1968, at a factory in California, when workers dropped "
        "the tank's shelf about two inches.",
        "The jolt probably knocked a loose tube out of place inside.",
    ]),
    ("detank", [
        "So in March 1970, at Kennedy Space Center, tank two wouldn't empty.",
        "The engineers improvised, and left the heaters running at 65 volts for about eight hours.",
    ]),
    ("weld", [
        "When the switches finally tried to open, the voltage welded them shut.",
        "Parts of the heater tube probably hit about 1,000 degrees, and the heat cooked the "
        "insulation on the fan's wires.",
        "Nobody noticed, and the tank flew.",
    ]),
    ("blast", [
        "Nearly 56 hours in, Mission Control asked the crew to stir the tanks.",
        "About 2.7 seconds after the fans came on, the wires shorted, the insulation caught fire "
        "in pure oxygen, and the blast tore a panel off the spacecraft.",
    ]),
    ("lifeboat", [
        "The crew made it home in the lunar module, built for two men for two days, stretched "
        "to three men for four.",
    ]),
    ("verdict", [
        "The review board blamed \"an unusual combination of mistakes.\"",
        "And the last one hurts the most.",
        "The heater controls at Kennedy had current meters on them.",
        "Anyone watching during those eight hours would've seen the switches never opened.",
        "The warning was right there, on a meter.",
    ]),
]

# How the subtitles should print what the narrator says (EN is already written as displayed).
SUBTITLE = []
