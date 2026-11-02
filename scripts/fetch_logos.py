"""Télécharge les logos officiels des principales enseignes dans logos/.

Sources, dans l'ordre :
 1. Wikidata de la marque (tag OSM brand:wikidata) : icône (P8972, P2910) puis
    logo (P154) actuels, le plus carré, fichier sur Wikimedia Commons rendu en PNG ;
 2. le logo de l'infobox de la page Wikipédia (fr, puis en) de la marque —
    utile pour les logos non libres (Carrefour, Système U…) absents de Commons ;
 3. l'icône « apple-touch-icon » du site officiel (P856).
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
# Pages Wikipédia à utiliser quand la marque n'a pas sa propre page (ex. « Station U »).
WIKI_TITLES = {
    "Q2529029": ["Système U"],
}
# Fichiers imposés quand la source automatique donne un mauvais logo.
OVERRIDES = {
    "Q217599": ("fr.wikipedia.org", "Logo Carrefour.svg"),   # Carrefour
    "Q2689639": ("fr.wikipedia.org", "Logo Carrefour.svg"),  # Carrefour Market
    "Q2940188": ("fr.wikipedia.org", "Logo Carrefour.svg"),  # Carrefour Contact
}


def wiki_file(host, file, width=256):
    """Télécharge un fichier d'un wiki (Commons ou Wikipédia) rendu en PNG. → (octets, largeur, hauteur)"""
    j = get_json(f"https://{host}/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "titles": "File:" + file, "prop": "imageinfo", "iiprop": "url|size",
         "iiurlwidth": str(width), "format": "json"}))
    info = next(iter(j["query"]["pages"].values()))["imageinfo"][0]
    body, ctype = http(info.get("thumburl") or info["url"], timeout=60)
    if not ctype.startswith("image/"):
        raise ValueError(f"type inattendu {ctype}")
    return body, info["width"], info["height"]


def infobox_logo(lang, title):
    """Fichier indiqué dans le paramètre « logo » de l'infobox de la page Wikipédia."""
    j = get_json(f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "parse", "page": title, "prop": "wikitext", "section": "0", "redirects": "1", "format": "json"}))
    wt = j["parse"]["wikitext"]["*"]
    m = re.search(r"\|\s*logo\s*=\s*(?:\[\[)?\s*(?:(?:File|Fichier|Image)\s*:)?\s*([^\]|\n}=]+?\.(?:svg|png|jpe?g|gif))", wt, re.I)
    if not m:
        raise ValueError("pas de logo dans l'infobox")
    return m.group(1).strip()


def trim(body):
    """Retire les marges transparentes ou blanches autour du logo."""
    from PIL import Image  # installé par le workflow
    import io
    im = Image.open(io.BytesIO(body)).convert("RGBA")
    px = im.load()
    mask = Image.new("L", im.size, 0)
    mp = mask.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a > 16 and not (r > 240 and g > 240 and b > 240):
                mp[x, y] = 255
    box = mask.getbbox()
    if box:
        im = im.crop(box)
    pad = max(2, int(max(im.size) * 0.04))
    out = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    out.paste(im, (pad, pad))
    buf = io.BytesIO()
    out.save(buf, "PNG", optimize=True)
    return buf.getvalue(), out.width, out.height


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
            {"action": "wbgetentities", "ids": "|".join(batch), "props": "claims|labels|sitelinks", "languages": "fr|en", "format": "json"}))
        ents.update(j.get("entities", {}))

    def claim(e, p):
        cs = [c for c in e.get("claims", {}).get(p, []) if c.get("rank") != "deprecated" and c["mainsnak"].get("datavalue")]
        cs.sort(key=lambda c: c.get("rank") != "preferred")
        return cs[0]["mainsnak"]["datavalue"]["value"] if cs else None

    def current_logos(e):
        """Fichiers logo/icône actuels (sans date de fin P582) de l'entité Wikidata."""
        files, old = [], []
        for p in ("P8972", "P2910", "P154"):
            for c in e.get("claims", {}).get(p, []):
                if c.get("rank") == "deprecated" or not c["mainsnak"].get("datavalue"):
                    continue
                (old if "P582" in c.get("qualifiers", {}) else files).append(c["mainsnak"]["datavalue"]["value"])
        return files or old

    index = {}
    for q in top:
        e = ents.get(q, {})
        name = names[q]
        body = source = None
        if q in OVERRIDES:
            host, file = OVERRIDES[q]
            try:
                body, _, _ = wiki_file(host, file)
                source = f"{host}:{file}"
            except Exception as ex:  # noqa: BLE001
                print(f"  {q} {name}: fichier imposé KO ({ex})")
        if body is None:
            # Le plus « carré » des logos actuels : il tient mieux dans le rond du marqueur.
            sized = []
            for f in current_logos(e):
                try:
                    b, w, h = wiki_file("commons.wikimedia.org", f)
                    sized.append((max(w / h, h / w), f, b))
                except Exception as ex:  # noqa: BLE001
                    print(f"  {q} {name}: Commons « {f} » KO ({ex})")
            if sized:
                _, f, body = min(sized)
                source = f"commons:{f}"
        if body is None:
            links = e.get("sitelinks", {})
            tries = [(l, t) for t in WIKI_TITLES.get(q, []) for l in ("fr", "en")]
            tries += [(l, links[f"{l}wiki"]["title"]) for l in ("fr", "en") if f"{l}wiki" in links]
            for lang, title in tries:
                try:
                    f = infobox_logo(lang, title)
                    body, _, _ = wiki_file(f"{lang}.wikipedia.org", f)
                    source = f"{lang}.wikipedia:{f}"
                    break
                except Exception as ex:  # noqa: BLE001
                    print(f"  {q} {name}: {lang}.wikipedia « {title} » KO ({ex})")
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
        body, w, h = trim(body)
        fn = f"{q}.png"
        with open(os.path.join(OUT, fn), "wb") as f:
            f.write(body)
        index[q] = {"name": name, "file": fn, "w": w, "h": h, "source": source, "count": counts[q]}
        print(f"✓ {q} {name} ({counts[q]} stations) ← {source}")

    with open(os.path.join(OUT, "index.json"), "w") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
