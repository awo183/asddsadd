"""Download archival footage and photos from Wikimedia Commons and record their licences.

Phase 1 downloads files straight from upload.wikimedia.org (the path is derived
from the MD5 of the file name, so no API call is needed). Images are fetched as
standard-width thumbnails (https://w.wiki/GHai). Phase 2 asks the Commons API
for author/licence metadata, backing off hard because the API rate-limits
shared cloud IPs.
"""
import hashlib, html, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

UA = "JachymovDocBuilder/0.2 (https://github.com/awo183/asddsadd; educational documentary)"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "build", "assets")
UPLOAD = "https://upload.wikimedia.org/wikipedia/commons"


# Commons keeps VP9 transcodes of every video; they are far smaller than the masters.
VIDEO_RES = {"rds1_site": 720, "crossroads_hd": 1080, "hiroshima_dmg": 1080, "truman_1945": 1080,
             "october_1937": 720, "anthracite": 480, "jachymov_valley": 1080, "trinity": 240}


def file_urls(title, kind, key=None):
    name = title.split(":", 1)[1].replace(" ", "_")
    h = hashlib.md5(name.encode()).hexdigest()
    q = urllib.parse.quote(name)
    orig = f"{UPLOAD}/{h[0]}/{h[:2]}/{q}"
    if kind == "videos":
        res = VIDEO_RES.get(key)
        if not res:
            return [orig]
        tc = lambda r: f"{UPLOAD}/transcoded/{h[0]}/{h[:2]}/{q}/{q}.{r}p.vp9.webm"
        return [tc(res)] + [tc(r) for r in (720, 480, 360, 240) if r < res] + [orig]
    thumb = lambda w: f"{UPLOAD}/thumb/{h[0]}/{h[:2]}/{q}/{w}px-{q}"
    # largest standard width first; Commons refuses thumbnails bigger than the original
    return [thumb(3840), thumb(1920), orig]


def get(url, path=None, tries=12):
    """Fetch url (to path, or return bytes). Honours Retry-After on 429.
    Returns False when a thumbnail size does not exist."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                if path is None:
                    return r.read()
                with open(path + ".part", "wb") as f:
                    while chunk := r.read(1 << 20):
                        f.write(chunk)
                os.rename(path + ".part", path)
                return True
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get("Retry-After") or 10) + 2
                print(f"429, waiting {wait}s", url[-60:], flush=True)
                time.sleep(wait)
                continue
            if ("thumb/" in url or "transcoded/" in url) and e.code in (400, 404, 500, 503):
                return False          # thumbnail wider than the original: try the next size
            print("http", e.code, url[-80:], flush=True)
        except Exception as e:
            print("retry", e, url[-80:], flush=True)
        time.sleep(5 * (attempt + 1))
    return False


def download_all(man):
    for kind in ("images", "videos"):
        for key, title in man[kind].items():
            ext = os.path.splitext(title)[1].lower()
            if kind == "videos" and key in VIDEO_RES:
                ext = ".webm"
            path = os.path.join(OUT, key + (".jpg" if ext in (".jpeg",) else ext))
            if os.path.exists(path) and os.path.getsize(path) > 0:
                continue
            for url in file_urls(title, kind, key):
                if get(url, path):
                    print("ok", key, flush=True)
                    break
            else:
                print("FAILED", key, flush=True)
            time.sleep(2)


def strip_html(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def fetch_credits(man):
    cache = os.path.join(OUT, "credits.json")
    credits = json.load(open(cache)) if os.path.exists(cache) else {}
    todo = [(kind, k, t) for kind in ("images", "videos") for k, t in man[kind].items() if k not in credits]
    for i in range(0, len(todo), 20):
        chunk = todo[i:i + 20]
        params = {"action": "query", "format": "json", "prop": "imageinfo", "titles": "|".join(t for _, _, t in chunk),
                  "iiprop": "url|size|extmetadata",
                  "iiextmetadatafilter": "LicenseShortName|Artist|ImageDescription|DateTimeOriginal"}
        url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
        for attempt in range(12):
            body = get(url, tries=1)
            if body:
                break
            time.sleep(60)
        else:
            print("credits: API unavailable, giving up for now", flush=True)
            return
        d = json.loads(body)
        norm = {n["to"]: n["from"] for n in d["query"].get("normalized", [])}
        by_title = {norm.get(p["title"], p["title"]): p for p in d["query"]["pages"].values()}
        for kind, k, t in chunk:
            ii = (by_title.get(t, {}).get("imageinfo") or [{}])[0]
            md = ii.get("extmetadata", {})
            credits[k] = {"title": t, "kind": kind, "page": ii.get("descriptionurl"),
                          "license": strip_html(md.get("LicenseShortName", {}).get("value")),
                          "artist": strip_html(md.get("Artist", {}).get("value"))[:200],
                          "description": strip_html(md.get("ImageDescription", {}).get("value"))[:300],
                          "date": strip_html(md.get("DateTimeOriginal", {}).get("value"))[:60],
                          "width": ii.get("width"), "height": ii.get("height"), "duration": ii.get("duration")}
        json.dump(credits, open(cache, "w"), indent=1, ensure_ascii=False)
        time.sleep(5)
    print("credits done", len(credits), flush=True)


if __name__ == "__main__":
    man = json.load(open(os.path.join(HERE, "assets_manifest.json")))
    os.makedirs(OUT, exist_ok=True)
    download_all(man)
    fetch_credits(man)
