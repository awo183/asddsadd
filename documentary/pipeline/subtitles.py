"""English subtitles (SRT) from the narration timing in timeline.json."""
import json, os, re
from common import BUILD

MAX_CHARS = 42 * 2  # two lines of ~42 characters


def chunks(text):
    """Split narration into subtitle-sized pieces at sentence / clause boundaries."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    out = []
    for s in sentences:
        while len(s) > MAX_CHARS:
            cut = max(s.rfind(", ", 0, MAX_CHARS), s.rfind(": ", 0, MAX_CHARS))
            if cut < 20:
                cut = s.rfind(" ", 0, MAX_CHARS)
            out.append(s[:cut + 1].strip())
            s = s[cut + 1:].strip()
        if s:
            out.append(s)
    return out


def two_lines(s):
    if len(s) <= 42:
        return s
    mid = len(s) // 2
    left, right = s.rfind(" ", 0, mid + 1), s.find(" ", mid)
    cut = left if (right == -1 or mid - left <= right - mid) else right
    return s[:cut] + "\n" + s[cut + 1:]


def ts(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)) % 1000:03d}"


def main():
    tl = json.load(open(os.path.join(BUILD, "timeline.json")))
    texts = {s["id"]: s["text"] for s in json.load(open(os.path.join(os.path.dirname(__file__), "narration.json")))["segments"]}
    cues = []
    for seg in tl["narration"]:
        parts = chunks(texts[seg["id"]])
        total = sum(len(p) for p in parts)
        t = seg["start"]
        for p in parts:
            d = seg["dur"] * len(p) / total
            cues.append((t, t + d - 0.04, two_lines(p)))
            t += d
    out = os.path.join(BUILD, "subtitles.en.srt")
    with open(out, "w") as f:
        for i, (a, b, txt) in enumerate(cues, 1):
            f.write(f"{i}\n{ts(a)} --> {ts(b)}\n{txt}\n\n")
    print("subtitles ->", out, len(cues), "cues")


if __name__ == "__main__":
    main()
