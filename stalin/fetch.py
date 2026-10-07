"""Find and download source material: archival photos (Google Images via Serper),
stock and real footage (Pexels, yt-dlp), plus background-removal cutouts.

usage:
  fetch.py images "query" [n]         search, download candidates, write a contact sheet
  fetch.py pexels "query" [n]         list Pexels videos and download previews
  fetch.py cutout SRC DEST            remove the background (person or object)
"""
import hashlib
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vox as V  # noqa: E402

CAND = os.path.join(V.BUILD, "candidates")
ASSETS = os.path.join(V.BUILD, "assets")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"


def _post(url, payload):
    req = urllib.request.Request(url, json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def _get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
        return json.load(r)


def serper_images(query, n=20):
    d = _post("https://google.serper.dev/images", {"q": query, "num": n, "gl": "cz", "hl": "cs"})
    return d.get("images", [])


def serper_videos(query, n=10):
    return _post("https://google.serper.dev/videos", {"q": query, "num": n}).get("videos", [])


def serper_search(query, n=10):
    return _post("https://google.serper.dev/search", {"q": query, "num": n}).get("organic", [])


def download(url, dest, min_side=300):
    """Download an image; keep it only if it decodes and is big enough."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://www.google.com/"})
        with urllib.request.urlopen(req, timeout=25) as r:
            data = r.read()
    except Exception as e:  # noqa: BLE001
        return None, f"download failed: {e}"
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return None, "not an image"
    if min(img.shape[:2]) < min_side:
        return None, f"too small {img.shape[1]}x{img.shape[0]}"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    cv2.imwrite(dest, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return dest, f"{img.shape[1]}x{img.shape[0]}"


def slug(s):
    return hashlib.md5(s.encode()).hexdigest()[:10]


def contact_sheet(paths, out, cols=4, cell=(460, 300)):
    rows = (len(paths) + cols - 1) // cols
    sheet = np.full((rows * (cell[1] + 34), cols * cell[0], 3), 30, np.uint8)
    for k, p in enumerate(paths):
        img = V.load_rgb(p)
        h, w = img.shape[:2]
        s = min(cell[0] / w, cell[1] / h)
        im = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
        x, y = (k % cols) * cell[0], (k // cols) * (cell[1] + 34)
        sheet[y + 34: y + 34 + im.shape[0], x: x + im.shape[1]] = im
        cv2.putText(sheet, f"{k}  {w}x{h}", (x + 6, y + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 220, 60), 2)
    cv2.imwrite(out, cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 80])
    return out


def images(query, n=16, tag=None):
    """Search Google Images, download up to n candidates, write a contact sheet.
    Returns (sheet_path, [(index, path, url, title, source)])."""
    tag = tag or slug(query)
    folder = os.path.join(CAND, tag)
    os.makedirs(folder, exist_ok=True)
    meta_path = os.path.join(folder, "meta.json")
    if os.path.exists(meta_path):
        meta = json.load(open(meta_path))
    else:
        meta = []
        for r in serper_images(query, 30):
            if len(meta) >= n:
                break
            url = r.get("imageUrl")
            if not url:
                continue
            dest = os.path.join(folder, f"{len(meta):02d}.jpg")
            got, info = download(url, dest)
            if got:
                meta.append({"path": got, "url": url, "title": r.get("title"), "source": r.get("link"),
                             "size": info})
        json.dump(meta, open(meta_path, "w"), ensure_ascii=False, indent=1)
    sheet = contact_sheet([m["path"] for m in meta], os.path.join(folder, "sheet.jpg")) if meta else None
    return sheet, meta


def pexels(query, n=8, orientation="landscape"):
    q = urllib.parse.urlencode({"query": query, "per_page": n, "orientation": orientation})
    d = _get_json(f"https://api.pexels.com/videos/search?{q}")
    out = []
    for v in d.get("videos", []):
        files = sorted([f for f in v["video_files"] if f.get("height") and f["height"] <= 1080],
                       key=lambda f: -f["height"])
        if files:
            out.append({"id": v["id"], "dur": v["duration"], "url": v["url"], "file": files[0]["link"],
                        "w": files[0]["width"], "h": files[0]["height"], "image": v["image"],
                        "user": v["user"]["name"]})
    return out


def pexels_sheet(query, n=8):
    tag = "pexels_" + slug(query)
    folder = os.path.join(CAND, tag)
    os.makedirs(folder, exist_ok=True)
    vids = pexels(query, n)
    paths = []
    for k, v in enumerate(vids):
        dest = os.path.join(folder, f"{k:02d}.jpg")
        if not os.path.exists(dest):
            download(v["image"], dest, 100)
        if os.path.exists(dest):
            paths.append(dest)
    json.dump(vids, open(os.path.join(folder, "meta.json"), "w"), indent=1)
    return contact_sheet(paths, os.path.join(folder, "sheet.jpg")) if paths else None, vids


def fetch_video(url, dest):
    """Download a video file over HTTP (Pexels / Internet Archive / direct links)."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if not os.path.exists(dest):
        subprocess.run(["curl", "-sSL", "--retry", "3", "-A", UA, "-o", dest, url], check=True)
    return dest


_SESSIONS = {}


def cutout(src, dest, model="u2net_human_seg"):
    """Remove the background; writes an RGBA PNG."""
    if os.path.exists(dest):
        return dest
    from PIL import Image
    from rembg import new_session, remove
    if model not in _SESSIONS:
        _SESSIONS[model] = new_session(model)
    out = remove(Image.open(src).convert("RGB"), session=_SESSIONS[model])
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    out.save(dest)
    return dest


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "images":
        sheet, meta = images(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 16)
        print(sheet)
        for k, m in enumerate(meta):
            print(k, m["size"], (m["title"] or "")[:70], "|", m["source"])
    elif cmd == "pexels":
        sheet, vids = pexels_sheet(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 8)
        print(sheet)
        for k, v in enumerate(vids):
            print(k, v["id"], f"{v['dur']}s", f"{v['w']}x{v['h']}", v["url"])
    elif cmd == "cutout":
        print(cutout(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "u2net_human_seg"))
