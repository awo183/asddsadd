"""Narration script for "How Machines Learned to See".

Each segment is a list of sentences. Sentences are voiced separately so the
renderer knows exactly when each one starts and can cut visuals to it.
Years are spelled out so the voice reads them naturally.
"""

SEGMENTS = [
    ("cold_open", [
        "There are now billions of cameras on Earth.",
        "They watch our streets, our shops, our workplaces.",
        "But for most of history, not one of them understood a single thing it saw.",
    ]),
    ("summer_1966", [
        "In the summer of nineteen sixty-six, researchers at M.I.T. set out to teach "
        "a computer to pick out objects in a picture.",
        "They gave themselves one summer.",
        "It would take nearly half a century.",
    ]),
    ("pixels", [
        "Because a computer doesn't see a face, or a street.",
        "It sees a grid of numbers. Millions of them.",
        "Each one, just a measure of red, green, or blue light.",
    ]),
    ("rules", [
        "For decades, engineers tried to write the rules by hand.",
        "Find the edges.",
        "Find the corners.",
        "Describe exactly what a person looks like.",
        "But change the lighting, the angle, or the shadows, and the rules fall apart.",
    ]),
    ("learning", [
        "So researchers flipped the problem.",
        "Instead of writing the rules, let the machine learn them, from examples.",
        "Layers of artificial neurons, tuning themselves across millions of images.",
    ]),
    ("imagenet", [
        "In two thousand nine, a project called ImageNet gathered more than fourteen "
        "million labeled photos.",
        "In twenty twelve, a neural network called AlexNet slashed the error rate in "
        "the ImageNet challenge.",
        "Three years later, machines were making fewer mistakes on that test than a "
        "trained human.",
    ]),
    ("today", [
        "Today, that ability is everywhere.",
        "Faster than you can blink, a machine scans each frame and draws a box.",
        "Person.",
        "Car.",
        "Bicycle.",
        "It counts shoppers in a store, and warns when a worker steps into a danger zone.",
    ]),
    ("watch", [
        "But a machine that can see can also watch.",
        "The same technology that finds a face in a crowd can be used to recognize "
        "whose face it is.",
        "Machines have learned to see.",
        "The question now is what we let them look at.",
    ]),
]
