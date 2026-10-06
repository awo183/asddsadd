"""Narration script for "Ramanujan: The Mind That Reached for Infinity".

Each beat is one narrated paragraph. ``voice`` selects the speaker:
  N = narrator, H = G. H. Hardy (quoted), R = Ramanujan (quoted).
``vis`` is a list of visual cue keys resolved by ``shots.py``.
``pause`` is silence (seconds) added after the beat.

Quotations are from Ramanujan's letters to Hardy (1913, 1920) and from
Hardy's own writings ("Ramanujan", 1940, and his obituary notice of 1921).
Disputed biographical details are attributed ("according to family
accounts", "it was later said") rather than stated as fact.
"""

TITLE = "RAMANUJAN"
SUBTITLE = "The Mind That Reached for Infinity"

CHAPTERS = {
    0: None,
    1: ("I", "A Boy from Kumbakonam", "1887 – 1903"),
    2: ("II", "The Notebooks", "1903 – 1912"),
    3: ("III", "The Letter", "1913"),
    4: ("IV", "Crossing the Black Water", "1914"),
    5: ("V", "Two Minds", "1914 – 1916"),
    6: ("VI", "A Long Winter", "1917 – 1918"),
    7: ("VII", "Recognition", "1918"),
    8: ("VIII", "Homecoming", "1919 – 1920"),
    9: ("IX", "The Infinite Legacy", "1920 – today"),
}

BEATS = [
    # ------------------------------------------------------------------ cold open
    dict(id="open1", ch=0, voice="N", vis=["anim:letter_envelope"], text=
        "In the winter of 1913, a thick envelope arrived at Trinity College, Cambridge. "
        "It was addressed to Godfrey Harold Hardy, one of the finest mathematicians in England. "
        "The postmark was from Madras, in southern India."),
    dict(id="open2", ch=0, voice="N", vis=["anim:formula_wall"], text=
        "Inside were page after page of formulas, written in a careful, cramped hand. "
        "Some were already known. A few were wrong. "
        "But others were unlike anything Hardy had ever seen."),
    dict(id="open3", ch=0, voice="H", vis=["photo:hardy", "quote"], pause=0.8, text=
        "They defeated me completely. I had never seen anything in the least like them before. "
        "They must be true, because, if they were not true, no one would have had the imagination to invent them."),
    dict(id="open4", ch=0, voice="N", vis=["photo:ramanujan_portrait"], text=
        "The man who sent them had no degree. He had failed out of college, twice. "
        "He was a clerk in a shipping office, earning thirty rupees a month. "
        "His name was Srinivasa Ramanujan."),
    dict(id="open5", ch=0, voice="N", vis=["photo:ramanujan_portrait2"], pause=1.5, text=
        "Within five years, he would be one of the most celebrated mathematicians in the world. "
        "And within seven years, he would be dead, at the age of thirty-two."),
    dict(id="title", ch=0, voice=None, vis=["anim:title"], dur=9.0, text=""),

    # ------------------------------------------------------------------ chapter 1
    dict(id="c1a", ch=1, voice="N", vis=["map:erode", "photo:erode_birthplace"], text=
        "Srinivasa Ramanujan was born on the twenty-second of December, 1887, in the town of Erode, "
        "in what was then the Madras Presidency of British India. "
        "He was born in his grandmother's house, but he grew up in Kumbakonam, "
        "an ancient temple town in the fertile delta of the Kaveri river."),
    dict(id="c1b", ch=1, voice="N", vis=["footage:kumbakonam", "photo:kumbakonam_temple"], text=
        "His family were Tamil Brahmins: devout, respected, and poor. "
        "His father worked as a clerk in a cloth merchant's shop. "
        "His mother, Komalatammal, sang devotional songs at the local temple. "
        "She was a strong-willed woman, and the dominant force in her son's life."),
    dict(id="c1c", ch=1, voice="N", vis=["photo:ramanujan_house", "photo:ramanujan_house2"], text=
        "The family lived in a small, single-storey house on Sarangapani Sannidhi Street, "
        "in the shadow of the great temple tower. The house still stands. Today it is a museum."),
    dict(id="c1d", ch=1, voice="N", vis=["photo:kaveri", "footage:india_period"], text=
        "Life in Kumbakonam was fragile. When he was two years old, Ramanujan survived smallpox. "
        "Several of his younger brothers and sisters did not survive infancy."),
    dict(id="c1e", ch=1, voice="N", vis=["photo:school", "anim:digits_pi"], text=
        "At school, his gift appeared early. By the age of eleven, he had exhausted the mathematical knowledge "
        "of two college students who lodged with his family. At thirteen, he mastered an advanced textbook "
        "on trigonometry, and began to discover theorems of his own."),
    dict(id="c1f", ch=1, voice="N", vis=["anim:digits_pi"], pause=1.0, text=
        "Classmates remembered a quiet boy who seemed to live in a world of numbers. "
        "He could recite the digits of pi, and of the square root of two, to as many places as anyone cared to hear. "
        "Then, at the age of sixteen, a book came into his hands that would change everything."),

    # ------------------------------------------------------------------ chapter 2
    dict(id="c2a", ch=2, voice="N", vis=["photo:carr_synopsis", "anim:formula_wall"], text=
        "It was called A Synopsis of Elementary Results in Pure and Applied Mathematics, "
        "by George Shoobridge Carr, a private tutor in London. It was not a great book. "
        "It was a list: some five thousand theorems and formulas, set down with little or no proof, "
        "meant to help students cram for examinations."),
    dict(id="c2b", ch=2, voice="N", vis=["anim:slate"], text=
        "For Ramanujan, it was a doorway. With no teacher to guide him, he took each bare result "
        "and worked out for himself why it was true. Then he went further. "
        "He began to record his own discoveries: formulas for infinite series, for continued fractions, "
        "for the hidden properties of whole numbers."),
    dict(id="c2c", ch=2, voice="N", vis=["anim:slate", "footage:notebook"], text=
        "Paper was expensive, so he worked on a slate, rubbing out his calculations with his elbow, "
        "and copied only the final results into his notebooks. "
        "It was a habit that would shape the rest of his life. "
        "Ramanujan wrote down what he found, but rarely how he found it."),
    dict(id="c2d", ch=2, voice="N", vis=["photo:college", "footage:india_period"], text=
        "His passion came at a price. In 1904, he won a scholarship to the Government College in Kumbakonam. "
        "But he could think only of mathematics. He neglected his other subjects, failed his examinations, "
        "and lost the scholarship. Ashamed, he ran away from home for several weeks."),
    dict(id="c2e", ch=2, voice="N", vis=["photo:madras_city", "photo:madras_city"], text=
        "Two years later, he tried again, at Pachaiyappa's College in Madras. "
        "Once more he excelled in mathematics. Once more he failed nearly everything else. "
        "He left without a degree."),
    dict(id="c2f", ch=2, voice="N", vis=["footage:india_period", "anim:nested_radical"], text=
        "For the next five years, Ramanujan lived on the edge of poverty. "
        "He tutored students when he could, and at times he went hungry. "
        "All the while, the notebooks kept growing."),
    dict(id="c2g", ch=2, voice="N", vis=["photo:janaki"], text=
        "In 1909, following custom, his mother arranged his marriage to Janaki, a girl of ten. "
        "As was usual at the time, she remained with her own family for several more years. "
        "Now, with a household to support, Ramanujan went looking for work, "
        "carrying his notebooks from one office to the next."),
    dict(id="c2h", ch=2, voice="N", vis=["photo:ramachandra_rao", "anim:slate"], text=
        "In 1910, he found his way to Ramachandra Rao, a senior government official and a passionate patron "
        "of mathematics. Rao was sceptical of the shabbily dressed young man. "
        "But as Ramanujan led him through elliptic integrals and divergent series, "
        "his doubts gave way to astonishment. He agreed to support Ramanujan with a small monthly allowance."),
    dict(id="c2i", ch=2, voice="N", vis=["footage:journal", "photo:madras_port"], text=
        "In 1911, Ramanujan published his first paper, on Bernoulli numbers, in the Journal of the "
        "Indian Mathematical Society. And in March 1912, he found a steady job: "
        "an accounts clerk at the Madras Port Trust, at thirty rupees a month."),
    dict(id="c2j", ch=2, voice="N", vis=["photo:madras_port", "photo:madras_city"], pause=1.0, text=
        "His superiors, including the Port Trust's chairman, Sir Francis Spring, quietly encouraged his research. "
        "Ramanujan finished his office work quickly, and spent the rest of his time on mathematics. "
        "But to be truly understood, his work needed the attention of the experts in Europe."),

    # ------------------------------------------------------------------ chapter 3
    dict(id="c3a", ch=3, voice="N", vis=["anim:letter_envelope"], text=
        "With the help of his supporters, Ramanujan wrote to leading mathematicians in Britain. "
        "The replies were discouraging. One offered polite advice. Others returned his work without comment. "
        "Then, on the sixteenth of January, 1913, he wrote to G. H. Hardy at Cambridge."),
    dict(id="c3b", ch=3, voice="R", vis=["anim:letter_text"], pause=0.8, text=
        "Dear Sir, I beg to introduce myself to you as a clerk in the Accounts Department of the "
        "Port Trust Office at Madras, on a salary of only twenty pounds per annum. "
        "I have had no university education, but I have undergone the ordinary school course. "
        "I have not trodden through the conventional regular course which is followed in a university course, "
        "but I am striking out a new path for myself."),
    dict(id="c3c", ch=3, voice="N", vis=["photo:hardy", "photo:trinity_great_court"], text=
        "Hardy was thirty-five, a Fellow of Trinity, and a champion of rigour: "
        "the careful, step-by-step proof that is the bedrock of modern mathematics. "
        "Strangers often sent him papers claiming to solve great problems. Most were the work of cranks. "
        "At first, he set the letter aside."),
    dict(id="c3d", ch=3, voice="N", vis=["anim:continued_fraction"], text=
        "But the formulas would not leave him alone. There were strange infinite series, "
        "and continued fractions: fractions nested inside fractions, without end, "
        "that somehow collapsed into exact and beautiful values."),
    dict(id="c3e", ch=3, voice="N", vis=["photo:littlewood", "footage:cambridge"], text=
        "That evening, Hardy took the letter to his colleague and closest collaborator, John Edensor Littlewood. "
        "By the end of the night, the two men had reached a verdict. This was not a fraud. "
        "It was the work of a genius."),
    dict(id="c3f", ch=3, voice="N", vis=["photo:trinity", "footage:cambridge"], pause=1.0, text=
        "Some of the results were already known in Europe. A few were mistaken. "
        "But those that were new revealed a mind of extraordinary power, working entirely alone. "
        "Hardy wrote back at once. He asked for proofs. And he began to plan something bolder: "
        "to bring Ramanujan to Cambridge."),

    # ------------------------------------------------------------------ chapter 4
    dict(id="c4a", ch=4, voice="N", vis=["footage:kumbakonam", "photo:ramanujan_house2"], text=
        "There was an obstacle. For an orthodox Brahmin, crossing the sea, the kala pani, or black water, "
        "meant losing caste: being cut off from family and community. "
        "At first, Ramanujan refused, and his mother would not hear of it."),
    dict(id="c4b", ch=4, voice="N", vis=["photo:neville", "footage:india_period"], text=
        "Early in 1914, Hardy's colleague Eric Neville, visiting Madras to lecture, pressed the invitation again. "
        "This time, the answer changed. According to family accounts, Ramanujan's mother dreamed that "
        "the family goddess, Namagiri, commanded her not to stand in the way of her son's destiny."),
    dict(id="c4c", ch=4, voice="N", vis=["photo:nevasa", "footage:ship", "map:voyage"], text=
        "Ramanujan cut his long hair, learned to wear Western clothes, and on the seventeenth of March, 1914, "
        "he boarded the steamship Nevasa at Madras. He left behind his mother, his father, and his young wife. "
        "Nearly a month later, he arrived in London."),
    dict(id="c4d", ch=4, voice="N", vis=["footage:cambridge", "photo:whewell"], pause=1.2, text=
        "Neville met him and took him to Cambridge. Soon he moved into rooms at Trinity College, "
        "in Whewell's Court, a few minutes' walk from Hardy. "
        "He had arrived at one of the great centres of mathematical learning in the world. "
        "In less than four months, Britain would be at war."),

    # ------------------------------------------------------------------ chapter 5
    dict(id="c5a", ch=5, voice="N", vis=["photo:hardy", "photo:ramanujan_portrait"], text=
        "The partnership that followed is one of the most remarkable in the history of science. "
        "Hardy and Ramanujan were opposites. Hardy was an atheist, a cricket lover, "
        "a rationalist who trusted only what could be proved. Ramanujan was deeply religious. "
        "He is said to have remarked that an equation had no meaning for him unless it expressed a thought of God."),
    dict(id="c5b", ch=5, voice="N", vis=["photo:trinity", "footage:cambridge"], text=
        "Hardy soon discovered that Ramanujan's knowledge was as patchy as it was profound. "
        "Working alone, he had rediscovered results that had taken Europe's finest mathematicians a century to develop. "
        "Yet he had never learned some of the most basic ideas of modern analysis."),
    dict(id="c5c", ch=5, voice="H", vis=["photo:hardy", "quote"], pause=0.8, text=
        "The limitations of his knowledge were as startling as its profundity. "
        "Here was a man who could work out modular equations and theorems of complex multiplication, "
        "to orders unheard of; and yet he had never heard of a doubly periodic function or of Cauchy's theorem, "
        "and had indeed but the vaguest idea of what a function of a complex variable was."),
    dict(id="c5d", ch=5, voice="N", vis=["photo:ramanujan_cambridge_group", "footage:cambridge"], text=
        "Hardy faced a delicate task: to teach Ramanujan the discipline of proof, "
        "without breaking the spell of his inspiration. They found a balance. "
        "Ramanujan brought the ideas, sometimes half a dozen new theorems in a single morning. "
        "Hardy and Littlewood helped to test them, to prove them, and to set them in a form the world could understand."),
    dict(id="c5e", ch=5, voice="N", vis=["anim:partitions4"], text=
        "Consider one of their great problems: partitions. A partition is a way of writing a number "
        "as a sum of whole numbers. The number four can be written in five ways: four; three plus one; "
        "two plus two; two plus one plus one; and one plus one plus one plus one."),
    dict(id="c5f", ch=5, voice="N", vis=["anim:partition_growth"], text=
        "As numbers grow, the partitions explode. Ten has forty-two. "
        "One hundred has more than one hundred and ninety million. "
        "Two hundred has nearly four trillion. Counting them one by one is hopeless."),
    dict(id="c5g", ch=5, voice="N", vis=["anim:partition_formula"], text=
        "So Hardy and Ramanujan set out to find a formula. In 1918, they published it: "
        "a remarkable expression, built from pi, square roots, and the exponential function. "
        "To test it, their colleague Percy MacMahon worked out the partitions of two hundred by hand. "
        "Using just a handful of terms, their formula landed on the exact answer, correct to the last digit."),
    dict(id="c5h", ch=5, voice="N", vis=["anim:partition_congruence"], text=
        "Along the way, they created a powerful new technique, the circle method, which mathematicians still use today. "
        "Ramanujan also noticed patterns no one had suspected. Take any number ending in four or nine: "
        "its number of partitions is always divisible by five. Similar patterns hold for seven, and for eleven."),
    dict(id="c5i", ch=5, voice="N", vis=["anim:pi_series"], text=
        "Then there was pi. In 1914, Ramanujan published seventeen new series for one over pi. "
        "The most famous of them converges with breathtaking speed: each new term adds roughly eight correct digits. "
        "Seventy years later, in 1985, it was used to calculate pi to more than seventeen million digits."),
    dict(id="c5j", ch=5, voice="N", vis=["anim:highly_composite", "footage:reporter", "photo:ramanujan_cambridge_group"], pause=1.2, text=
        "In March 1916, Cambridge awarded Ramanujan a Bachelor of Arts degree by research, "
        "the forerunner of the modern doctorate, for his work on highly composite numbers: "
        "numbers like twelve, sixty, and three hundred and sixty, that have more divisors than any smaller number. "
        "The man who had twice failed college now held a Cambridge degree."),

    # ------------------------------------------------------------------ chapter 6
    dict(id="c6a", ch=6, voice="N", vis=["footage:war", "photo:cambridge_war"], text=
        "But Cambridge was not home. The war had emptied the university. "
        "Littlewood left to serve in the artillery. Colleges became barracks and military hospitals. "
        "And the English winters were long, dark, and cold."),
    dict(id="c6b", ch=6, voice="N", vis=["photo:whewell", "footage:war"], text=
        "Ramanujan was a strict vegetarian who cooked his own meals in his rooms. "
        "With wartime shortages, the foods he depended on were hard to find. "
        "It was said that he would sometimes work for thirty hours straight, and then sleep for twenty."),
    dict(id="c6c", ch=6, voice="N", vis=["photo:ramanujan_portrait2", "footage:london"], text=
        "He was deeply lonely. Few people in England shared his language, his faith, or his food. "
        "Hardy admired him enormously, but Hardy was a reserved man, uneasy with personal matters, "
        "and their friendship lived almost entirely in mathematics. "
        "Letters from home grew scarce. Some of his wife's letters, it was later said, never reached him at all."),
    dict(id="c6d", ch=6, voice="N", vis=["footage:london", "photo:illness"], text=
        "In the spring of 1917, Ramanujan fell seriously ill. Doctors suspected tuberculosis, then incurable. "
        "Some modern researchers believe he may instead have suffered from a parasitic liver infection, "
        "picked up years earlier in India. Whatever its cause, the illness never let him go."),
    dict(id="c6e", ch=6, voice="N", vis=["photo:matlock", "photo:illness", "footage:london"], text=
        "For the next two years, he moved between hospitals and nursing homes: in Cambridge, in the Mendip Hills, "
        "in Derbyshire, and in London. He was a difficult patient, homesick, refusing food he could not trust, "
        "and sinking into a deep depression."),
    dict(id="c6f", ch=6, voice="N", vis=["footage:london_dark"], pause=1.5, text=
        "In early 1918, at one of his lowest moments, Ramanujan tried to take his own life. "
        "He survived. Hardy, it is said, intervened with the authorities on his behalf."),
    dict(id="c6g", ch=6, voice="N", vis=["photo:putney", "footage:london_taxi"], text=
        "It was during this dark period that one of the most famous stories in mathematics took place. "
        "Hardy came to visit his friend at a nursing home in Putney, in south-west London."),
    dict(id="c6h", ch=6, voice="H", vis=["footage:london_taxi", "anim:taxi1729"], pause=0.6, text=
        "I remember once going to see him when he was lying ill at Putney. "
        "I had ridden in taxi-cab number seventeen twenty-nine, and remarked that the number seemed to me rather a dull one, "
        "and that I hoped it was not an unfavourable omen. "
        "No, he replied, it is a very interesting number; "
        "it is the smallest number expressible as the sum of two cubes in two different ways."),
    dict(id="c6i", ch=6, voice="N", vis=["anim:cubes1729"], pause=1.0, text=
        "One cubed, plus twelve cubed. Nine cubed, plus ten cubed. Both make seventeen twenty-nine. "
        "Even gravely ill, Ramanujan saw numbers as old friends. "
        "As Littlewood once put it, every positive integer was one of Ramanujan's personal friends."),

    # ------------------------------------------------------------------ chapter 7
    dict(id="c7a", ch=7, voice="N", vis=["photo:royal_society", "photo:ramanujan_portrait2"], text=
        "Even as his body failed, recognition finally came. On the second of May, 1918, "
        "Ramanujan was elected a Fellow of the Royal Society of London, one of the youngest in its history, "
        "and only the second Indian ever to receive the honour."),
    dict(id="c7b", ch=7, voice="N", vis=["photo:trinity_great_court", "photo:trinity"], text=
        "In October of the same year, he became the first Indian to be elected a Fellow of Trinity College, Cambridge. "
        "The news travelled to India, and made him famous. "
        "The clerk from the Madras Port Trust now stood among the most honoured scientists of his time."),
    dict(id="c7c", ch=7, voice="N", vis=["footage:armistice", "footage:war"], pause=1.0, text=
        "In November 1918, the war ended. Ships could once again sail safely to India. "
        "His health had improved, a little, and his doctors decided he was well enough to travel home."),

    # ------------------------------------------------------------------ chapter 8
    dict(id="c8a", ch=8, voice="N", vis=["footage:suez", "map:return"], text=
        "In late February 1919, Ramanujan sailed for India. He arrived in Bombay in March, "
        "and travelled on to Madras, where admirers waited to greet him. "
        "His wife Janaki joined him, and cared for him through the months that followed."),
    dict(id="c8b", ch=8, voice="N", vis=["footage:india_period", "photo:ramanujan_portrait2"], text=
        "He was painfully thin, and often in pain. Yet he never stopped working. "
        "Lying in bed, he filled loose sheets of paper with new mathematics. "
        "In January 1920, he wrote what would be his last letter to Hardy."),
    dict(id="c8c", ch=8, voice="R", vis=["anim:letter_mock"], pause=0.8, text=
        "I am extremely sorry for not writing you a single letter up to now. "
        "I discovered very interesting functions recently, which I call mock theta functions."),
    dict(id="c8d", ch=8, voice="N", vis=["anim:mock_theta"], text=
        "Mock theta functions. Ramanujan described seventeen of them, with no definition: "
        "only examples, and a few cryptic properties. "
        "It would take mathematicians more than eighty years to understand what he had found."),
    dict(id="c8e", ch=8, voice="N", vis=["anim:candle"], pause=4.0, text=
        "On the twenty-sixth of April, 1920, Srinivasa Ramanujan died. He was thirty-two years old."),
    dict(id="c8f", ch=8, voice="N", vis=["photo:hardy"], text=
        "Hardy was devastated. He spent much of the rest of his life studying, explaining, "
        "and championing his friend's work. He wrote:"),
    dict(id="c8g", ch=8, voice="H", vis=["photo:ramanujan_portrait", "quote"], pause=1.5, text=
        "I owe more to him than to anyone else in the world, with one exception, "
        "and my association with him is the one romantic incident in my life."),

    # ------------------------------------------------------------------ chapter 9
    dict(id="c9a", ch=9, voice="N", vis=["footage:notebook", "anim:formula_wall"], text=
        "Ramanujan left behind nearly four thousand results, almost all of them recorded without proof. "
        "For a century, mathematicians have worked to prove them. "
        "The overwhelming majority have turned out to be true."),
    dict(id="c9b", ch=9, voice="N", vis=["photo:wren_library", "footage:notebook"], text=
        "In 1976, the American mathematician George Andrews was searching through a box of old papers "
        "in the library of Trinity College. Inside, he found more than a hundred pages in Ramanujan's handwriting, "
        "from the final year of his life. It became known as the lost notebook."),
    dict(id="c9c", ch=9, voice="N", vis=["anim:mock_theta"], text=
        "And the mock theta functions? In 2002, a young Dutch mathematician, Sander Zwegers, "
        "finally revealed the hidden structure behind them. Today, they appear in places Ramanujan "
        "could never have imagined, including the mathematics of black holes, and string theory."),
    dict(id="c9d", ch=9, voice="N", vis=["anim:legacy_names"], text=
        "His ideas live on in computer algorithms, in signal processing, and in the design of networks. "
        "His name is attached to Ramanujan graphs, the Ramanujan tau function, the Ramanujan conjecture, "
        "and to the Hardy-Ramanujan number, seventeen twenty-nine."),
    dict(id="c9e", ch=9, voice="N", vis=["anim:hardy_scale"], text=
        "Hardy once rated mathematicians on a scale from zero to one hundred, for pure natural talent. "
        "He gave himself twenty-five. Littlewood, thirty. The great David Hilbert, eighty. "
        "Ramanujan, he gave one hundred."),
    dict(id="c9f", ch=9, voice="N", vis=["photo:legacy", "photo:ramanujan_house"], text=
        "In India, his birthday, the twenty-second of December, is celebrated as National Mathematics Day. "
        "His house in Kumbakonam welcomes visitors, and students around the world still open his notebooks, "
        "searching for what he saw."),
    dict(id="c9g", ch=9, voice="N", vis=["photo:ramanujan_portrait", "anim:infinity"], pause=3.0, text=
        "Srinivasa Ramanujan had no formal training, few resources, and very little time. "
        "He came from a small temple town, with a borrowed book and a slate. "
        "He lived for just thirty-two years. "
        "More than a century later, the world is still catching up with what he saw."),
    dict(id="credits", ch=9, voice=None, vis=["anim:credits"], dur=40.0, text=""),
]
