"""Download and prepare every asset "The 28-Volt Switch" uses, into build/apollo13/assets.

All material is public domain: NASA photographs and film (NASA Image and Video
Library), the Report of Apollo 13 Review Board (NASA NTRS 19700076776) and
Natural Earth map data. Fonts are in apollo13/fonts (SIL OFL).
"""
import json
import os
import subprocess
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "build", "apollo13", "assets")
UA = {"User-Agent": "28-volt-switch-film/1.0 (documentary research)"}

PHOTOS = ["S70-34902", "S70-32990", "S70-40850", "108-KSC-70PC-105", "S70-34852", "7010516",
          "as13-59-8484", "S70-35638"]
# (NASA video id, output name, start, seconds)
FILMS = [
    ("KSC-19700411-MH-NAS01-0001-Apollo_13_Launch_Post_Launch_with_Spiro_Agnew_and_Billie_Brandt_B_0664",
     [("firing_room", "00:10:00", 20), ("liftoff", "00:19:00", 95)]),
]
REPORT = "https://ntrs.nasa.gov/api/citations/19700076776/downloads/19700076776.pdf"
REPORT_PAGES = (174, 175, 183)
MAPS = ["ne_50m_admin_0_countries", "ne_50m_admin_1_states_provinces_lakes", "ne_10m_minor_islands"]


def get(url, dst):
    if os.path.exists(dst):
        return dst
    req = urllib.request.Request(url.replace(" ", "%20"), headers=UA)
    with urllib.request.urlopen(req, timeout=300) as r, open(dst, "wb") as f:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
    return dst


def nasa_files(nid):
    url = f"https://images-api.nasa.gov/asset/{urllib.parse.quote(nid)}"
    return [x["href"] for x in json.load(urllib.request.urlopen(url, timeout=60))["collection"]["items"]]


def main():
    for d in ("nasa", "video", "report", "maps"):
        os.makedirs(os.path.join(ASSETS, d), exist_ok=True)
    for nid in PHOTOS:
        files = [f for f in nasa_files(nid) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        pick = next((f for f in files if "~orig" in f), files[0])
        get(pick, os.path.join(ASSETS, "nasa", nid + os.path.splitext(pick)[1].lower()))
        print("photo", nid)
    for nid, cuts in FILMS:
        pick = next(f for f in nasa_files(nid) if f.endswith("~orig.mp4"))
        reel = get(pick, os.path.join(ASSETS, "video", "reel.mp4"))
        for name, ss, secs in cuts:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", ss, "-i", reel, "-t", str(secs), "-an",
                            "-vf", "yadif=0:-1:0,fps=30", "-c:v", "libx264", "-crf", "15", "-pix_fmt", "yuv420p",
                            os.path.join(ASSETS, "video", name + ".mp4")], check=True)
            print("film", name)
        os.remove(reel)
    import pymupdf
    pdf = get(REPORT, os.path.join(ASSETS, "report", "a13rb.pdf"))
    doc = pymupdf.open(pdf)
    words = {}
    for pg in REPORT_PAGES:
        p = doc[pg - 1]
        pix = p.get_pixmap(dpi=220)
        pix.save(os.path.join(ASSETS, "report", f"p{pg:03d}.png"))
        k = 220 / 72
        words[pg] = {"size": [pix.width, pix.height],
                     "words": [[w[0] * k, w[1] * k, w[2] * k, w[3] * k, w[4]] for w in p.get_text("words")]}
    json.dump(words, open(os.path.join(ASSETS, "report", "words.json"), "w"))
    for m in MAPS:
        get(f"https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/{m}.geojson",
            os.path.join(ASSETS, "maps", m + ".geojson"))
    print("assets ready in", ASSETS)


if __name__ == "__main__":
    main()
