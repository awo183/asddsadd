# The Calmest Man on the Plane — script

A two-minute true-crime breakdown of the 1971 D.B. Cooper hijacking. It's in
the style of a psychological-analysis channel: a calm narrator, beat-by-beat
behaviour analysis, red annotations and hard-hitting reveals.

Running time: **2:03** · Voice: synthetic (Kokoro TTS, blend of `am_michael` and `am_onyx`)

**Czech version, "Nejklidnější muž v letadle":** this has the same scenes, with Czech
narration ([`narration_cs.py`](narration_cs.py)) and Czech on-screen text
([`strings.py`](strings.py)). It runs about **2:38**, because the Czech script is longer
and is spoken at a natural pace. Voice: synthetic (Piper, `cs_CZ-jirka-medium`).

**Look:** all on-screen text uses typewriter type (Special Elite for headlines and Courier
Prime for captions, both open-licensed) and types itself on with a cursor and keystroke
sounds.

| Time | Picture | Narration |
|---|---|---|
| 0:00 | **Hook.** The FBI composite sketch, with HIJACKED / $200,000 / VANISHED punching in. The screen drops to black on NEVER SEEN AGAIN, then a red circle is drawn around his eyes and CALM. appears | This man hijacked a passenger jet, collected two hundred thousand dollars, and jumped into the night. He was never seen again. But what's most unsettling isn't what he did. It's how calm he was. |
| 0:13 | **Title.** THE CALMEST MAN ON THE PLANE (glitch-in) | — |
| 0:16 | **The note.** A jetliner taking off in rain, with a typewriter caption: Nov 24 1971, Portland, Flight 305, passenger "Dan Cooper". Then a photo of the actual aircraft (N467US), and the folded note opening to I HAVE A BOMB IN MY BRIEFCASE. The quote follows as word-by-word subtitles | Portland, 1971. A man calling himself Dan Cooper boards a flight to Seattle. He orders a bourbon and soda, then hands the flight attendant a note. She thinks it's his phone number. It isn't. "Miss, you'd better look at that note. I have a bomb." |
| 0:32 | **Behaviour analysis.** The sketch, with a checklist crossing out shouting, threats and passengers being aware. Then a typed DEMANDS sheet with "4 PARACHUTES" circled. A big red 4 and four parachute icons: HIM, ?, ?, ?. Then NOT PANIC. is struck through and stamped A PLAN | Now, notice what he doesn't do. He doesn't shout. He doesn't threaten anyone. Most passengers never realize they're being hijacked. He asks for two hundred thousand dollars, and four parachutes. Four. Extra parachutes imply he might take a hostage, so no one can risk giving him a sabotaged one. This isn't panic. It's a plan. |
| 0:54 | **The orders.** The 1971 photo of the Flight 305 crew. A green cockpit readout of his instructions: Mexico City, below 10,000 ft, minimum airspeed, gear down, flaps 15°, cabin unpressurized. A 727 diagram whose rear airstair lowers in red | In Seattle, he trades the passengers for the cash, and gives the crew his orders. Fly to Mexico. Low and slow. Landing gear down. Cabin unpressurized. He knows this plane has a rear staircase that can open in flight. |
| 1:08 | **The jump.** An animated map of the route from Seattle with 8:13 PM and a pulse over the estimated jump area. Rain over dark Washington forest, and the frame jolts with THE TAIL JOLTS UPWARD. A wide map to Reno: CABIN: EMPTY | At 8:13 p.m., over the forests of southwest Washington, the tail of the plane jolts upward. When it lands in Reno, he's gone. |
| 1:18 | **The profile.** The FBI's 1971 bulletin and its first theory, AN EXPERT SKYDIVER, which gets stamped WRONG. Agent Larry Carr's 2007 quote, word for word. Then THE CONTRADICTION: what he planned (ticked) against what he didn't (crossed) | The FBI first assumed he was an expert skydiver. Later, they concluded the opposite. As one agent put it, no experienced parachutist would jump at night, in the rain, wearing loafers and a trench coat. A man who planned every detail of the hijacking, and almost nothing about the landing. |
| 1:37 | **The money.** A map zoom to Tena Bar on the Columbia River, February 1980. The FBI photo of the recovered bills, with $5,800 and a SERIAL NUMBERS MATCH stamp. $194,200 NEVER FOUND over dark forest. The bulletin stamped UNSOLVED (active investigation ended July 2016). A final slow push into the composite | In 1980, a boy found $5,800 of the ransom on the bank of the Columbia River. The rest was never found. Neither was he. It's still the only unsolved hijacking in American aviation history. Maybe he died that night in the woods. Or maybe the calmest man on that plane got exactly what he planned. |
| 1:59 | End card and credits | — |

## Fact sources

- Date, flight, demands ($200,000 and four parachutes), Seattle exchange, route to
  Mexico City via Reno: FBI case history, and the
  [D. B. Cooper article on Wikipedia](https://en.wikipedia.org/wiki/D._B._Cooper).
- "Miss, you'd better look at that note", bourbon and soda, and the instructions
  (no higher than 10,000 ft, gear down, flaps 15°, unpressurized, minimum airspeed):
  [HistoryNet](https://historynet.com/legend-of-d-b-cooper-what-happened-to-historys-most-famous-hijacker/),
  [USPA *Parachutist*](https://www.uspa.org/the-secrets-of-db-cooper-part-one-notorious-flight-305).
- 8:13 p.m. upward movement of the tail:
  [The Legend of D.B. Cooper](https://everything-everywhere.com/the-legend-of-d-b-cooper/).
- The Larry Carr quote and the sewn-shut training reserve chute:
  [FBI, "D.B. Cooper Redux" (2007)](https://www.fbi.gov/news/stories/2007/december/dbcooper_123107/),
  [Seattle Times (2008)](https://archive.seattletimes.com/archive/20080101/dbcooper01m/fbi-makes-new-plea-in-db-cooper-case).
- Money found in February 1980 on the Columbia River, with matching serial numbers; the
  FBI ending its active investigation in July 2016; "America's only unsolved airplane hijacking":
  [CS Monitor (2016)](https://csmonitor.com/USA/Justice/2016/0713/D.B.-Cooper-FBI-closes-notorious-unsolved-skyjacking-case),
  [UPI (2016)](https://www.upi.com/Top_News/US/2016/07/13/FBI-ends-45-year-search-for-infamous-DB-Cooper-plane-hijacker/5101468404616/).

## What's real and what's illustrative

- **Archival (real):** the FBI composite sketches, the 1971 FBI bulletin, the FBI photo of
  the recovered money, and the photo of the Flight 305 crew (*Nevada State Journal*, 1971).
  These are all public domain. The aircraft photo shows the actual hijacked 727, N467US
  (Clint Groves, GFDL 1.2).
- **Illustrative:** the takeoff, in-flight and forest footage is NASA b-roll (a DC-8 in
  Washington State), not footage of Flight 305. The note, the demands sheet, the cockpit
  readout, the 727 diagram and the maps are graphics drawn for this film. The jump area is
  the commonly cited estimate, not a known point.
- **No suspects are named.** He was never identified.
- **Style.** This is an original video in the *style* of true-crime psychology channels. It
  doesn't use any channel's name, logo or voice.
