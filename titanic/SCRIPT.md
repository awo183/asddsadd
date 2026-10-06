# Twenty Boats / Dvacet člunů — script

A two-minute history explainer, in English and Czech. The Titanic carried *more*
lifeboats than the law required, so why did about 1,500 people die? The answer
lies in a lifeboat table from 1894, the "boats are ferries" thinking behind it,
and a rescue that came too late.

- **Voice:** ElevenLabs `eleven_v4`, voice "Christian" (`6xPz2opT0y5qtoRh1U1Y`), the same voice in
  both languages. It's recorded one sentence at a time with character timestamps, so every
  animation is cued to the word as it's actually spoken in that language.
- **Running time:** English about 2:12, Czech about 2:24. The Czech cut runs longer because Czech
  takes longer to say the same thing; nothing was trimmed to fit.
- **Style:** see [`STYLE.md`](STYLE.md).

## English script

| # | Scene | Narration |
|---|---|---|
| 1 | Hook | The Titanic carried more lifeboats than the law required. So why did about fifteen hundred people die? The iceberg sank the ship. An old rule explains why so many died with it. |
| 2 | Title | *(no voice)* TWENTY BOATS · Why the Titanic ran out of lifeboats |
| 3 | The rule | British lifeboat rules went by a ship's size, in a table last updated in 1894. Back then, the biggest liner was about 13,000 tons. So the table stopped at 10,000 and up. The Titanic was 46,000. To the law, it was the same as a ship a fifth its size. So the rules asked for 962 seats. The Titanic had 1,178. On board: more than 2,200 people. |
| 4 | Why | Why not update it? Ships now had watertight compartments. And radio could call for help. Lifeboats weren't meant to hold everyone. They were ferries, out to rescue ships. In 1909, it worked. The liner Republic, struck in fog, radioed for help, and about 1,500 people were ferried to safety. |
| 5 | The night | At 11:40 p.m. on April 14th, the Titanic hit an iceberg. Five compartments flooded. It was built to survive four. It had two hours and forty minutes. |
| 6 | The radio | The nearest ship, the Californian, was less than twenty miles away. Its only radio operator had gone to bed. The Carpathia heard the call, 58 miles away. It arrived more than an hour and a half too late. |
| 7 | The boats | The ferry plan fell apart. And the boats left half empty. The first one lowered could hold 65. It carried 28. About 710 people survived, in boats with room for 1,178. |
| 8 | After | Within two years, nations signed the first treaty on safety at sea: a lifeboat seat for everyone, and radios staffed day and night. And an ice patrol that still watches the North Atlantic today. The Titanic didn't break the rules. That was the problem. |
| 9 | End | *(no voice)* Credits |

## Czech script (Česká verze)

This is a natural translation, not word for word. Numbers are written out in
[`narration_cs.py`](narration_cs.py) so they're spoken correctly.

| # | Scéna | Text |
|---|---|---|
| 1 | Úvod | Titanic vezl víc záchranných člunů, než mu předepisoval zákon. Tak proč zahynulo asi tisíc pět set lidí? Loď potopil ledovec. Jenže to, že s ní zemřelo tolik lidí, má na svědomí jedno staré pravidlo. |
| 2 | Titulek | *(bez hlasu)* DVACET ČLUNŮ · Proč na Titanicu nebylo dost člunů |
| 3 | Pravidlo | Britský zákon určoval počet člunů podle velikosti lodi, a to tabulkou, kterou naposledy upravili v roce 1894. Největší parník měl tehdy kolem třinácti tisíc tun. Tabulka proto končila kategorií deset tisíc tun a víc. Titanic měl čtyřicet šest tisíc. Pro zákon se ale nelišil od lodi pětkrát menší. Předpisy tak žádaly 962 míst. Titanic jich měl 1 178. Na palubě ale bylo přes 2 200 lidí. |
| 4 | Proč | Proč to nikdo nezměnil? Lodě už měly vodotěsné oddíly. A rádiem se dala přivolat pomoc. Čluny neměly pojmout všechny najednou. Měly lidi jen převážet na záchranné lodě. V roce 1909 to fungovalo. Parník Republic se v mlze srazil s jinou lodí, rádiem přivolal pomoc a čluny převezly do bezpečí zhruba 1 500 lidí. |
| 5 | Noc | Čtrnáctého dubna, dvacet minut před půlnocí, narazil Titanic na ledovec. Voda zaplavila pět oddílů. Loď přitom vydržela nanejvýš čtyři. Zbývaly jí dvě hodiny a čtyřicet minut. |
| 6 | Rádio | Nejbližší loď, Californian, byla necelých dvacet mil daleko. Její jediný radista ale už spal. Carpathia volání zachytila, jenže byla 58 mil daleko. Dorazila víc než hodinu a půl pozdě. |
| 7 | Čluny | Plán s převážením se zhroutil. A čluny odplouvaly poloprázdné. První spuštěný člun měl místo pro 65 lidí. Sedělo v něm 28. Přežilo asi 710 lidí, v člunech, kam se vešlo 1 178. |
| 8 | Potom | Do dvou let státy podepsaly první úmluvu o bezpečnosti na moři: místo ve člunu pro každého a radiostanice v provozu ve dne v noci. A také ledovou hlídku, která severní Atlantik sleduje dodnes. Titanic žádné pravidlo neporušil. A právě v tom byl ten problém. |
| 9 | Konec | *(bez hlasu)* Titulky a zdroje |

## Shot list

All scenes are built on one warm graph-paper collage. Text, labels and numbers come from
[`strings.py`](strings.py) in the current language. Archival items are real and captioned;
see [ASSETS.md](ASSETS.md).

1. **Hook.** A die-cut photo of the Titanic leaving Southampton (1912) slides in over a coral
   disc. Twenty lifeboat icons pop in, and MORE THAN THE LAW REQUIRED gets a yellow
   highlighter sweep on MORE. *The Sun* front page of 16 April 1912 follows: the
   highlighter crosses "1,500 MISSING AFTER TITANIC FOUNDERED" and a coral loop circles the
   number, with ≈1,500 on a coral disc beside it. Then the iceberg photographed from the
   Carpathia (1912), circled, and a torn strip reading 1894.
2. **Title.** TWENTY BOATS / DVACET ČLUNŮ, with twenty boat icons and a tape strip carrying
   the subtitle.
3. **The rule.** A tonnage scale from 0 to 50,000; the part the 1894 table covered is shaded.
   A small liner rides the "biggest liner in 1894 ≈13,000" bar, a die-cut Titanic rides its
   bar to 46,328, and a strip reads "10,000 and up = 16 boats". Then the 1912 British
   report quote with "whatever their size might be" highlighted. Then the seat bars (962
   required, 1,178 carried, 2,200+ on board) with a hand-drawn bracket reading "1,000+
   without a seat", next to the photo of a Titanic lifeboat taken from the Carpathia.
4. **Why.** *The Washington Times* of 15 April 1912 and its false "KEPT AFLOAT BY
   WATER-TIGHT COMPARTMENTS" headline, highlighted and captioned as an early, wrong report.
   A wireless mast pulses. 1912 newsreel of lifeboats on davits follows, captioned as
   filmed on the sister ship *Olympic*. Then the flat diagram: lifeboats as ferries
   between a ship in trouble and a rescue ship. Then *The Washington Times* of 23 January
   1909 ("LINER REPUBLIC RAMMED IN HEAVY FOG; PASSENGERS ARE SAVED BY WIRELESS CALLS")
   and ≈1,500 SAVED.
5. **The night.** A flat night map of the North Atlantic. The route draws on from
   Southampton via Cherbourg and Queenstown to a pulsing marker reading 11:40 PM · APRIL
   14, 1912. Then 16 watertight compartments: the 1912 diagram from *An Unsinkable Titanic*
   above a simplified one in which five compartments flood, with a bracket reading BUILT
   TO SURVIVE 4 and a coral cross. Then a clock arc from 11:40 to 2:20 and "2 h 40 min".
6. **The radio.** The map zooms in to a few miles of sea. The Californian sits inside a
   "< 20 miles" ring with its real photo and RADIO OFF · OPERATOR ASLEEP. Morse "CQD" plays
   as the rings reach the Carpathia, 58 miles away, shown in 1912 newsreel at her New York
   pier. A timeline marks SANK 2:20 AM against CARPATHIA ARRIVES ≈4:00 AM, then a TOO LATE
   stamp.
7. **The boats.** The Bain photo of Titanic lifeboats on their way to the Carpathia, with
   "half empty". Lifeboat 7 seen from above: 65 seats, 28 filled in coral. Then a grid of
   1,178 seats with about 710 filled and about 470 left empty.
8. **After.** The SOLAS 1914 card ticks off a seat for everyone, radio day and night, and
   an ice patrol, next to a 1912 photo of crowds waiting for news, then a 1948 photo of the
   International Ice Patrol at work. Last card: THE TITANIC DIDN'T BREAK THE RULES, with the
   highlighter on BREAK THE RULES, then THAT WAS THE PROBLEM.
9. **End card** with credits for every source, in the current language.

## Fact sources

- **Lifeboat table of 1894, the "10,000 and upwards" top category, 16 boats, the 962 persons
  required, 1,178 carried, the 46,328 gross tons, and the largest emigrant steamer in 1894
  (*Lucania*, 12,952 tons):** British Wreck Commissioner's Inquiry, *Report*, "Board of Trade's
  Administration" and "Life-Saving Appliances",
  [titanicinquiry.org](https://www.titanicinquiry.org/BOTInq/BOTReport/botRepBOT.php).
  [Law Library of Congress, "Failure to Update the Law: A Titanic Mistake"](https://blogs.loc.gov/law/2012/04/failure-to-update-the-law-a-titanic-mistake/)
  covers the same points.
- **Why the rules weren't changed** (stronger ships with watertight compartments, wireless,
  boats as transfer craft): the testimony of Sir Alfred Chalmers, Board of Trade nautical
  adviser, quoted in the same section of the British report.
- **Boats as ferries, and the 1909 *Republic* rescue** (struck in fog by the *Florida*, CQD
  radio call, about 1,500 saved, deaths only in the collision): Wikipedia,
  [Lifeboats of the Titanic](https://en.wikipedia.org/wiki/Lifeboats_of_the_Titanic) and
  [RMS Republic](https://en.wikipedia.org/wiki/RMS_Republic).
- **Collision at 11:40 p.m. on April 14; designed to float with four forward compartments
  flooded, while the first five were flooded; sank at 2:20 a.m., two hours forty minutes
  later:** Wikipedia, [Sinking of the Titanic](https://en.wikipedia.org/wiki/Sinking_of_the_Titanic),
  and the British report ("Account of the Ship's Journey", "Flooding").
- **On board and saved:** the British report gives 2,201 on board and 711 saved; the US Senate
  inquiry gives 2,223 on board and 706 saved; Wikipedia says "more than 2,200" on board and 710
  survivors. "About 1,500" died covers the range in these sources: 1,490 (British) and 1,517
  (US).
- **The *Californian*:** her sole wireless operator, Cyril Evans, turned in at 11:30 p.m.
  (British report, "The Californian"; Wikipedia). Distance estimates run from about 5–10 miles
  (British report) to Captain Lord's 19 miles; the script says "less than twenty".
- **The *Carpathia*:** 58 miles away; picked up the first boat at 4:10 a.m. (British report,
  "Rescue by the SS Carpathia"); "arrived about an hour and a half after the sinking"
  (Wikipedia).
- **Lifeboat 7:** the first launched, at about 12:45 a.m., with a capacity of 65 and about 28
  aboard (Wikipedia, *Lifeboats of the Titanic*). There were 20 boats: 14 × 65, 2 × 40 and
  4 × 47 = 1,178.
- **SOLAS 1914**, signed in London on 20 January 1914: lifeboats and lifejackets for everyone on
  board, and continuous radio watch. It never formally entered into force because of the
  First World War, though its rules were widely adopted.
  [UK National Archives](https://www.nationalarchives.gov.uk/explore-the-collection/stories/the-convention-for-the-safety-of-life-at-sea/),
  [Wikipedia](https://en.wikipedia.org/wiki/International_Convention_for_the_Safety_of_Life_at_Sea).
- **The International Ice Patrol**, set up under the 1914 convention and still operating:
  [US Coast Guard NAVCEN](https://www.navcen.uscg.gov/international-ice-patrol-history),
  [Wikipedia](https://en.wikipedia.org/wiki/International_Ice_Patrol).

## Archival material, licences, and what's illustrative

See [`ASSETS.md`](ASSETS.md) for every file used, its source, its licence and its credit.
