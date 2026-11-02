"""Télécharge les logos officiels des principales enseignes dans logos/.

Source : la marque Wikidata (tag OSM brand:wikidata) → propriété « logo » (P154)
→ fichier sur Wikimedia Commons (rendu en PNG). À défaut, l'icône
« apple-touch-icon » du site officiel de la marque (P856).
Résultat : logos/<QID>.png + logos/index.json {QID: {name, file, source, count}}.
"""
import collections
import json
import os
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from common import france_fuel_stations, get_json, http  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "logos")
MIN_STATIONS = int(os.environ.get("MIN_STATIONS", "10"))
MAX_BRANDS = int(os.environ.get("MAX_BRANDS", "60"))


def commons_png(filename, width=256):
    url = "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(filename.replace(" ", "_")) + f"?width={width}"
    body, ctype = http(url, timeout=60)
    if not ctype.startswith("image/"):
        raise ValueError(f"type inattendu {ctype}")
    return body, ctype


def site_icon(site):
    html, _ = http(site, timeout=30, headers={"Accept": "text/html"})
    html = html.decode("utf-8", "ignore")
    best = None
    for m in re.finditer(r"<link[^>]+>", html, re.I):
        tag = m.group(0)
        if re.search(r'rel=["\'][^"\']*apple-touch-icon', tag, re.I):
            href = re.search(r'href=["\']([^"\']+)', tag, re.I)
            if href:
                best = urllib.parse.urljoin(site, href.group(1))
                break
    if not best:
        best = urllib.parse.urljoin(site, "/apple-touch-icon.png")
    body, ctype = http(best, timeout=30)
    if not ctype.startswith("image/") or len(body) < 500:
        raise ValueError("pas d'icône")
    return body, ctype


def main():
    os.makedirs(OUT, exist_ok=True)
    counts, names = collections.Counter(), {}
    for _, _, t in france_fuel_stations():
        q = t.get("brand:wikidata", "")
        if re.fullmatch(r"Q\d+", q):
            counts[q] += 1
            names.setdefault(q, t.get("brand") or t.get("name") or q)
    top = [q for q, n in counts.most_common(MAX_BRANDS) if n >= MIN_STATIONS]
    print(f"{len(top)} enseignes retenues")

    ents = {}
    for i in range(0, len(top), 50):
        batch = top[i:i + 50]
        j = get_json("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(
            {"action": "wbgetentities", "ids": "|".join(batch), "props": "claims|labels", "languages": "fr|en", "format": "json"}))
        ents.update(j.get("entities", {}))

    def claim(e, p):
        cs = [c for c in e.get("claims", {}).get(p, []) if c.get("rank") != "deprecated" and c["mainsnak"].get("datavalue")]
        cs.sort(key=lambda c: c.get("rank") != "preferred")
        return cs[0]["mainsnak"]["datavalue"]["value"] if cs else None

    index = {}
    for q in top:
        e = ents.get(q, {})
        name = names[q]
        body = source = None
        logo = claim(e, "P154")
        if logo:
            try:
                body, _ = commons_png(logo)
                source = f"commons:{logo}"
            except Exception as ex:  # noqa: BLE001
                print(f"  {q} {name}: Commons KO ({ex})")
        if body is None:
            site = claim(e, "P856")
            if site:
                try:
                    body, _ = site_icon(site)
                    source = f"site:{site}"
                except Exception as ex:  # noqa: BLE001
                    print(f"  {q} {name}: site KO ({ex})")
        if body is None:
            print(f"✗ {q} {name} ({counts[q]} stations) : aucun logo")
            continue
        fn = f"{q}.png"
        with open(os.path.join(OUT, fn), "wb") as f:
            f.write(body)
        index[q] = {"name": name, "file": fn, "source": source, "count": counts[q]}
        print(f"✓ {q} {name} ({counts[q]} stations) ← {source}")

    with open(os.path.join(OUT, "index.json"), "w") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
