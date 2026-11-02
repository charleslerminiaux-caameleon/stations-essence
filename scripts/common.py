"""Outils partagés par les scripts de génération (bibliothèque standard uniquement)."""
import json
import time
import urllib.parse
import urllib.request

UA = "stations.caameleon.com/1.0 (+https://stations.caameleon.com)"
OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def http(url, data=None, timeout=120, headers=None):
    h = {"User-Agent": UA}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type", "")


def get_json(url, **kw):
    body, _ = http(url, **kw)
    return json.loads(body)


def france_fuel_stations():
    """Toutes les stations-service (amenity=fuel) de France métropolitaine et DOM selon OpenStreetMap."""
    q = """[out:json][timeout:300];
area["ISO3166-1"="FR"][admin_level=2]->.fr;
nwr["amenity"="fuel"](area.fr);
out center tags;"""
    last = None
    for attempt in range(2):
        for url in OVERPASS:
            try:
                j = get_json(url, data=urllib.parse.urlencode({"data": q}).encode(), timeout=330)
                els = j.get("elements") or []
                if len(els) > 5000:
                    out = []
                    for e in els:
                        lat = e.get("lat", (e.get("center") or {}).get("lat"))
                        lon = e.get("lon", (e.get("center") or {}).get("lon"))
                        if lat is not None:
                            out.append((float(lat), float(lon), e.get("tags") or {}))
                    print(f"Overpass {url}: {len(out)} stations OSM")
                    return out
                last = f"{url}: {len(els)} éléments ({j.get('remark', '')})"
            except Exception as ex:  # noqa: BLE001
                last = f"{url}: {ex}"
            print("Overpass KO →", last)
        time.sleep(30)
    raise RuntimeError(f"Overpass indisponible : {last}")
