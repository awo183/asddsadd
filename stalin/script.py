"""Parse the FacelessOS script (Traditional mode) into narration paragraphs and
timed visual cues.

Format: cue lines start with "[" ("[PHOTO: ...]", "[SFX: ...]", "[PAUSE: 0.8s ...]"),
"## " lines are section headings, everything else is spoken narration.
Each cue is anchored to the first narration word that follows it.
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "SCRIPT.md")
CUE = re.compile(r"^\[([A-ZÁ-Ž_ ]+):?\s*(.*?)\]\s*$")
VISUAL = {"PHOTO", "FOOTAGE", "MAP", "TEXT", "HIGHLIGHT", "COUNTER", "COMPARE", "TIMELINE", "PORTRAIT",
          "DIAGRAM", "TITLECARD", "CHAPTER", "CLIPPING", "B-ROLL", "CLIP"}
MAX_PARA = 650        # characters per TTS request


def items(path=SCRIPT):
    """[(kind, payload)] in order: ("cue", (TYPE, text)) / ("text", line) / ("head", title)."""
    out = []
    for raw in open(path, encoding="utf-8"):
        line = raw.strip()
        if not line or line.startswith("<!--") or line.startswith("---"):
            continue
        if line.startswith("#"):
            out.append(("head", line.lstrip("#").strip()))
            continue
        m = CUE.match(line)
        if m:
            out.append(("cue", (m.group(1).strip().upper(), m.group(2).strip())))
            continue
        if line.startswith("["):          # a cue followed by text on the same line
            close = line.index("]")
            m = CUE.match(line[:close + 1])
            if m:
                out.append(("cue", (m.group(1).strip().upper(), m.group(2).strip())))
                line = line[close + 1:].strip()
                if not line:
                    continue
        out.append(("text", line))
    return out


def blocks(path=SCRIPT):
    """Narration paragraphs for TTS. A block breaks at headings, PAUSE/TITLECARD/CHAPTER cues
    and when it grows past MAX_PARA characters (at a sentence end).
    Returns [{text, cues: [(char_pos, type, text)], pause_before}]."""
    out = []
    cur = {"text": "", "cues": [], "pause_before": 0.0}

    def flush():
        nonlocal cur
        if cur["text"].strip():
            out.append(cur)
            cur = {"text": "", "cues": [], "pause_before": 0.0}
        return cur

    pending = []
    for kind, val in items(path):
        if kind == "head":
            flush()
        elif kind == "cue":
            typ, txt = val
            if typ in ("PAUSE", "TITLECARD", "CHAPTER"):
                flush()
                if typ == "PAUSE":
                    m = re.search(r"([\d.,]+)\s*s", txt)
                    cur["pause_before"] += float(m.group(1).replace(",", ".")) if m else 0.8
            pending.append((typ, txt))
        else:
            if len(cur["text"]) > MAX_PARA and re.search(r"[.!?…]$", cur["text"].strip()):
                flush()
            if cur["text"]:
                cur["text"] += " "
            pos = len(cur["text"])
            for typ, txt in pending:
                cur["cues"].append((pos, typ, txt))
            pending = []
            cur["text"] += val
    flush()
    if pending and out:          # cues after the last line anchor to its end
        for typ, txt in pending:
            out[-1]["cues"].append((len(out[-1]["text"]), typ, txt))
    return out


def paragraphs(path=SCRIPT):
    return [b["text"] for b in blocks(path)]


def word_index(text, pos):
    """Index of the word that starts at or after character pos."""
    return len(text[:pos].split())


if __name__ == "__main__":
    bs = blocks()
    nw = sum(len(b["text"].split()) for b in bs)
    vis = sum(1 for b in bs for c in b["cues"] if c[1] in VISUAL)
    sfx = sum(1 for b in bs for c in b["cues"] if c[1] == "SFX")
    print(f"{len(bs)} paragraphs, {nw} words, {vis} visual cues, {sfx} sfx cues")
    k = 0
    for i, b in enumerate(bs):
        print(f"--- para {i} ({len(b['text'])} chars, pause {b['pause_before']})")
        for pos, typ, txt in b["cues"]:
            w = b["text"][pos:pos + 30].replace("\n", " ")
            print(f"   c{k:03d} {typ:10s} {txt[:60]:60s} @ «{w}»")
            k += 1
