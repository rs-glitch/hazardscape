"""Shared paths, cached HTTP with a provenance manifest, and projection helpers."""
import hashlib
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
WEB = ROOT / "web"
WEB_DATA = WEB / "data"
MANIFEST = RAW / "manifest.jsonl"
UA = "CAFireYears/0.1 (open-data wildfire visualization; contact via project README)"
R_EARTH = 6378137.0

RAW.mkdir(parents=True, exist_ok=True)
WEB_DATA.mkdir(parents=True, exist_ok=True)


def _key(url, params, data):
    blob = json.dumps([url, params, data], sort_keys=True, default=str)
    return hashlib.sha1(blob.encode()).hexdigest()[:16]


def fetch(url, *, params=None, data=None, source, name=None, ext="bin", timeout=180, retries=4, headers=None):
    """GET (or POST when data is given) with an on-disk cache.

    Every network fetch is appended to data/raw/manifest.jsonl with the URL,
    parameters, UTC retrieval time, byte count and sha256, so SOURCES.md can be
    generated from what was actually downloaded.
    """
    # shortcut: the cache key is `name` when given, not the params; delete data/raw/<source>/ after changing a query
    sub = RAW / source
    sub.mkdir(parents=True, exist_ok=True)
    path = sub / f"{name or _key(url, params, data)}.{ext}"
    if path.exists() and path.stat().st_size > 0:
        return path
    last = None
    for attempt in range(retries):
        try:
            if data is None:
                r = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": UA, **(headers or {})})
            else:
                r = requests.post(url, data=data, timeout=timeout, headers={"User-Agent": UA})
            if r.status_code == 200:
                path.write_bytes(r.content)
                rec = dict(source=source, url=r.url if data is None else url, params=params,
                           post=bool(data), file=str(path.relative_to(ROOT)).replace("\\", "/"),
                           bytes=len(r.content), sha256=hashlib.sha256(r.content).hexdigest(),
                           retrieved_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"))
                with MANIFEST.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(rec) + "\n")
                return path
            last = f"HTTP {r.status_code}: {r.text[:200]}"
            if r.status_code in (404, 400):
                break
        except requests.RequestException as e:
            last = repr(e)
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"fetch failed {url}: {last}")


def fetch_json(url, **kw):
    path = fetch(url, ext="json", **kw)
    d = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(d, dict) and "error" in d and not d.get("features"):   # ArcGIS answers errors with HTTP 200
        path.unlink()
        raise RuntimeError(f"{url}: {d['error']}")
    return d


# --- Web Mercator (EPSG:3857) -------------------------------------------------
def lonlat_to_merc(lon, lat):
    x = R_EARTH * math.radians(lon)
    y = R_EARTH * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return x, y


def merc_to_lonlat(x, y):
    lon = math.degrees(x / R_EARTH)
    lat = math.degrees(2 * math.atan(math.exp(y / R_EARTH)) - math.pi / 2)
    return lon, lat


def lonlat_to_tile(lon, lat, z):
    n = 2 ** z
    xt = (lon + 180) / 360 * n
    yt = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return xt, yt


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, separators=(",", ":")), encoding="utf-8")
