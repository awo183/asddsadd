# Archival material, licences, and what's illustrative

Every outside file used in *Twenty Boats* / *Dvacet člunů* is listed here, with where it
appears, its source, its licence and the credit shown on the end card. I checked each
licence on its source page. The files themselves are downloaded into
`build/titanic/assets/` (not committed), together with a `manifest.json`.

## Archival (shows the real subject)

| Used in | File | What it is | Source | Licence / rights |
|---|---|---|---|---|
| Hook, the rule, last line | `titanic_departing_southampton_1912-04-10.jpg` | The Titanic leaving Southampton, 10 April 1912 (die-cut) | F. G. O. Stuart, [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:RMS_Titanic_3.jpg) | Public domain (author died 1923; published before 1931) |
| Hook | `newyork-sun_1912-04-16_p1.jpg` | *The Sun* (New York), 16 April 1912, front page: "1,500 MISSING AFTER TITANIC FOUNDERED" | [Chronicling America, Library of Congress](https://www.loc.gov/resource/sn83030272/1912-04-16/ed-1/?sp=1) | Public domain (LOC rights statement for Chronicling America) |
| Hook | `iceberg_viewed_from_carpathia_1912.jpg` | "View from S.S. Carpathia of iceberg which sank the Titanic", 1912 (cropped to the berg) | [Library of Congress, P&P, LC-DIG-ds-17921](https://www.loc.gov/item/2002721381/) | No known restrictions on publication |
| The rule (seats) | `titanic_collapsible_d_from_carpathia_1912-04-15.jpg` | A Titanic lifeboat (collapsible D) photographed from the Carpathia, 15 April 1912 | [U.S. National Archives, NAID 278338](https://catalog.archives.gov/id/278338), via Wikimedia Commons | NARA: unrestricted; public domain |
| Why | `washington-times_1912-04-15_p1.jpg` | *The Washington Times*, 15 April 1912: "LINER TITANIC KEPT AFLOAT BY WATER-TIGHT COMPARTMENTS…" (an early, **false** report; the caption says so on screen) | [Chronicling America](https://www.loc.gov/resource/sn84026749/1912-04-15/ed-1/?sp=1) | Public domain |
| Why | `washington-times_1909-01-23_p1_republic.jpg` | *The Washington Times*, 23 January 1909: "LINER REPUBLIC RAMMED IN HEAVY FOG; PASSENGERS ARE SAVED BY WIRELESS CALLS" | [Chronicling America](https://www.loc.gov/resource/sn84026749/1909-01-23/ed-1/?sp=1) | Public domain |
| Why, the radio | `titanic_disaster_newsreel_1912_loc.mp4` | 1912 newsreel "Titanic disaster". Two excerpts are used; see below | [Library of Congress, George Kleine Collection](https://www.loc.gov/item/mp73125400/) | LOC: "not aware of any U.S. copyright or other restrictions"; released 1912 |
| The night | `titanic_vs_mauretania_subdivision_diagram_1912.jpg` | "Comparison of Subdivision in Two Famous Ships" (the Titanic's 16 compartments), from J. B. Walker, *An Unsinkable Titanic* (1912) | [Internet Archive](https://archive.org/details/unsinkabletitani00walkrich/page/n149/mode/1up) | Public domain (1912 US book; NOT_IN_COPYRIGHT) |
| The radio | `californian_from_carpathia_1912-04-15.jpg` | The *Californian* at the wreck site, probably photographed from the Carpathia, 15 April 1912 | [U.S. National Archives, NAID 278339](https://catalog.archives.gov/id/278339), via Wikimedia Commons | NARA: unrestricted |
| The boats | `titanic_lifeboats_approaching_carpathia_1912-04-15.jpg` | "TITANIC life boats on way to CARPATHIA" | [Library of Congress, Bain Collection, LC-DIG-ggbain-11212](https://www.loc.gov/item/2014691299/) | No known restrictions on publication |
| After | `crowd_awaiting_titanic_survivors_1912-04.jpg` | "Crowd awaiting TITANIC survivors", New York, April 1912 | [Library of Congress, Bain Collection, LC-DIG-ggbain-10346](https://www.loc.gov/item/2014690329/) | No known restrictions on publication |
| After | `international_ice_patrol_1948_usn.jpg` | The International Ice Patrol at work, 1948 | National Museum of the U.S. Navy, [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Lot_2282-12_(21871433408).jpg) | Public domain (US government work) |

**Newsreel excerpts.** These are real 1912 film, captioned honestly on screen:
- **0:41–0:56, lifeboats on davits (the "Why" scene):** the LOC catalogue says this was
  filmed on the **Olympic**, the Titanic's sister ship, not the Titanic. The caption reads
  "Filmed on the Olympic, the Titanic's sister ship · 1912 newsreel". It shows what the
  same boat deck and boats looked like. It isn't the Titanic.
- **4:57–5:07, the Carpathia at her New York pier after the rescue (the radio scene):**
  captioned as such.

**The quote** in the rule scene ("…as to all such vessels, whatever their size might be, the
minimum number of boats under davits was fixed by the table at 16…") is from the 1912
*Report* of the British Wreck Commissioner's Inquiry, transcribed at
[titanicinquiry.org](https://www.titanicinquiry.org/BOTInq/BOTReport/botRepBOT.php). In the
Czech cut it's shown in Czech translation.

## Illustrative (drawn for this film)

- **Maps** (night and radio scenes) are drawn from Natural Earth land data (public domain).
  The ship positions in the radio scene are approximate, and the screen says so. The
  Titanic is at her CQD position, the Californian about 15 nautical miles north (estimates
  range from about 5 to 19), and the Carpathia 58 nautical miles to the south-east.
- **Charts:** the 1894 tonnage scale, the seat bars and the seat grids use the figures sourced
  in [SCRIPT.md](SCRIPT.md). The 1894 table's rows below 10,000 tons aren't drawn; only
  its top category is shown.
- **The flat compartment diagram** is simplified: equal compartments, the first five flooding
  from the bow. It's labelled "Simplified diagram".
- **Icons:** the ship silhouettes in the "lifeboats = ferries" diagram, the lifeboat icons, the
  radio mast and the clock are illustrations.
- **The SOLAS 1914 card** summarises the treaty's provisions. It isn't a facsimile of the
  document.
- **Paper, grid, tape strips, highlighter and marks** are all generated in code
  (`titanic/look.py`).

## Downloaded but not used

The agent's manifest also lists other front pages (*New-York Tribune*, *San Francisco Call*,
*Evening World*), Carpathia stills, Captain Smith, survivors, wireless operators, a 1912
cartoon, a cutter photo and an ice-patrol mural. They aren't in the film. Two of them have
licence doubts that kept them out: the *Prinz Adalbert* iceberg photo (no documented first
publication) and the 1938 mural (the mural's own copyright isn't stated).

## Voice, music, fonts

- **Narration:** ElevenLabs `eleven_v4`, voice "Christian", synthetic; it's used under the
  account's ElevenLabs plan.
- **Music and sound effects:** original, synthesized in `titanic/audio.py`. No samples.
- **Fonts:** Archivo, Libre Caslon Text, Playfair Display and Caveat, all SIL Open Font
  Licence, from the Google Fonts repository. The licence files are in `assets/fonts/`.
