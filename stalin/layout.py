"""Place the narration paragraphs on the film's clock and time every cue to the
word it belongs to.

Title and chapter cards get their own slot in the gap before the paragraph
they open; [PAUSE] cues add silence there too.
"""
import json
import os

import script
import vox as V

LEAD = 0.5            # picture before the first word
GAP = 0.18            # breath between paragraphs
TITLE = 2.4           # title card slot
CHAPTER = 1.25        # chapter card slot
OUTRO = 2.6           # picture after the last word
PRE = 0.06            # cut this much before the word starts


def layout():
    blocks = script.blocks()
    man = json.load(open(os.path.join(V.BUILD, "voice", "manifest.json")))
    assert [b["text"] for b in blocks] == [m["text"] for m in man], "narration changed: rerun tts.py"
    t, voice, cues, n = LEAD, [], [], 0
    for k, (b, m) in enumerate(zip(blocks, man)):
        head = [c for c in b["cues"] if c[0] == 0]
        gap = (GAP if k else 0.0) + b["pause_before"]
        cards = [(typ, txt) for _, typ, txt in head if typ in ("TITLECARD", "CHAPTER")]
        slot = t + (GAP if k else 0.0) + b["pause_before"]
        card_t = {}
        for typ, txt in cards:
            card_t[(typ, txt)] = slot
            slot += TITLE if typ == "TITLECARD" else CHAPTER
            gap += TITLE if typ == "TITLECARD" else CHAPTER
        start = t + gap
        voice.append({"mp3": m["mp3"], "start": round(start, 3), "dur": m["dur"], "text": b["text"],
                      "words": [{**w, "t0": w["t0"] + start, "t1": w["t1"] + start} for w in m["words"]]})
        for pos, typ, txt in b["cues"]:
            if typ == "PAUSE":
                continue
            if (typ, txt) in card_t:
                ct = card_t[(typ, txt)]
            else:
                wi = script.word_index(b["text"], pos)
                ct = start + (m["words"][wi]["t0"] - PRE if wi < len(m["words"]) else m["dur"])
                if pos == 0 and not cards:
                    ct = max(start - (b["pause_before"] if k else 0) - (GAP if k else 0), 0) if typ in script.VISUAL \
                        and b["pause_before"] == 0 else ct
            cues.append({"id": f"c{n:03d}", "type": typ, "text": txt, "t": round(max(ct, 0), 3), "para": k})
            n += 1
        t = start + m["dur"]
    return {"voice": voice, "cues": cues, "duration": round(t + OUTRO, 3)}


if __name__ == "__main__":
    L = layout()
    vis = [c for c in L["cues"] if c["type"] in script.VISUAL]
    nxt = {c["id"]: (vis[i + 1]["t"] if i + 1 < len(vis) else L["duration"]) for i, c in enumerate(vis)}
    for c in L["cues"]:
        d = f"{nxt[c['id']] - c['t']:5.2f}s" if c["id"] in nxt else "     "
        print(f"{c['id']} {c['t']:7.2f} {d} {c['type']:9s} {c['text'][:95]}")
    print("duration", L["duration"])
