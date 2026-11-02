"""Construit brands.json : marque de chaque station du flux officiel des prix.

Correspondance station officielle ↔ station OpenStreetMap :
 1. tag OSM ref:FR:prix-carburants = identifiant officiel (exact) ;
 2. sinon la station OSM la plus proche à moins de 300 m.
Format : {"b": [[nom, QID], ...], "s": {id_station: index_dans_b}}
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import france_fuel_stations, get_json  # noqa: E402

API = ("https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/"
       "prix-des-carburants-en-france-flux-instantane-v2/exports/json?select=id,latitude,longitude,geom")
OUT = sys.argv[1] if len(sys.argv) > 1 else "brands.json"


def coords(r):
    g = r.get("geom") or {}
    if g.get("lat") is not None:
        return float(g["lat"]), float(g["lon"])
    try:
        la, lo = float(r["latitude"]), float(r["longitude"])
    except (KeyError, TypeError, ValueError):
        return None
    return (la / 1e5, lo / 1e5) if abs(la) > 90 else (la, lo)


def dist(a, b):
    dy = (a[0] - b[0]) * 111320
    dx = (a[1] - b[1]) * 111320 * math.cos(math.radians(a[0]))
    return math.hypot(dx, dy)


def main():
    stations = get_json(API, timeout=300)
    print(f"{len(stations)} stations officielles")
    osm = france_fuel_stations()

    by_ref, grid = {}, {}
    for lat, lon, t in osm:
        label = t.get("brand") or t.get("name") or t.get("operator")
        if not label:
            continue
        item = ((lat, lon), label.strip()[:60], t.get("brand:wikidata", "") if t.get("brand") else "")
        for ref in str(t.get("ref:FR:prix-carburants", "")).split(";"):
            if ref.strip():
                by_ref[ref.strip()] = item
        grid.setdefault((round(lat * 100), round(lon * 100)), []).append(item)

    pairs, index, out, exact, near = [], {}, {}, 0, 0
    for r in stations:
        sid = str(r.get("id"))
        hit = by_ref.get(sid)
        if hit:
            exact += 1
        else:
            c = coords(r)
            if not c:
                continue
            best, bd = None, 300
            gy, gx = round(c[0] * 100), round(c[1] * 100)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    for it in grid.get((gy + dy, gx + dx), []):
                        d = dist(c, it[0])
                        if d < bd:
                            best, bd = it, d
            if not best:
                continue
            hit = best
            near += 1
        key = (hit[1], hit[2])
        if key not in index:
            index[key] = len(pairs)
            pairs.append(list(key))
        out[sid] = index[key]

    print(f"Marques trouvées : {exact} par référence, {near} par proximité, "
          f"{len(stations) - exact - near} sans marque")
    if len(out) < 1000:
        raise SystemExit("Trop peu de correspondances, brands.json non écrit")
    with open(OUT, "w") as f:
        json.dump({"b": pairs, "s": out}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{OUT} : {os.path.getsize(OUT) // 1024} Ko")


if __name__ == "__main__":
    main()
