"""Statewide context: CAL FIRE incidents, WFIGS final perimeters, daily VIIRS detections in California.

Output: web/data/state.json (lon/lat rounded to ~100 m).
"""
import csv
import json
from collections import Counter
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
from matplotlib.path import Path as MPath

import fetch as F
from common import WEB_DATA, write_json
from fires import FIRES

YEARS = range(2020, 2027)
FIRMS_YEARS = range(2020, 2026)     # yearly archive files exist through 2025 (2026 returns 404)


PACIFIC = ZoneInfo("America/Los_Angeles")


def nice(name):
    """Agency names come in ALL CAPS or Title Case; normalise without breaking 'McFarland'."""
    name = name.strip()
    return re.sub(r"\bMc(\w)", lambda m: "Mc" + m.group(1).upper(), name.title()) if name.isupper() else name


def r4(v):
    return round(v, 3)


def outline():
    g = F.ca_boundary()["features"][0]["geometry"]
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    return [[[r4(x), r4(y)] for x, y in poly[0]] for poly in polys if len(poly[0]) > 20]


def incidents():
    out = []
    for y in YEARS:
        for d in F.calfire_incidents(y):
            if d.get("Type") not in (None, "", "Wildfire", "Fire") or not d.get("Latitude") or not d.get("AcresBurned"):
                continue
            out.append(dict(name=d["Name"], y=y, start=d.get("StartedDateOnly"), acres=d["AcresBurned"],
                            county=d.get("County"), lon=r4(d["Longitude"]), lat=r4(d["Latitude"]),
                            url=d.get("Url"), contained=d.get("PercentContained")))
    return out


def perimeters():
    where = ("attr_POOState='US-CA' AND poly_GISAcres>1000 AND "
             "attr_FireDiscoveryDateTime >= DATE '2020-01-01'")
    feats = F.wfigs_query("WFIGS_Interagency_Perimeters", where, "ca_finals_1000ac",
                          fields="poly_IncidentName,poly_GISAcres,attr_FireDiscoveryDateTime", offset=0.004)
    out = []
    for x in feats:
        g, p = x.get("geometry"), x["properties"]
        if not g:
            continue
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        rings = [[[r4(a), r4(b)] for a, b, *_ in poly[0]] for poly in polys if len(poly[0]) >= 4]
        t = datetime.fromtimestamp(p["attr_FireDiscoveryDateTime"] / 1000, PACIFIC)
        out.append(dict(name=nice(p["poly_IncidentName"]), acres=round(p["poly_GISAcres"]),
                        y=t.year, start=t.date().isoformat(), rings=rings))
    out.sort(key=lambda d: -d["acres"])
    return out


def detections_per_day(ca_rings):
    paths = [MPath(np.array(r)) for r in ca_rings]
    days = Counter()
    for y in FIRMS_YEARS:
        p = F.fetch(f"{F.FIRMS}/viirs-snpp/{y}/viirs-snpp_{y}_United_States.csv", source="nasa_firms",
                    name=f"viirs-snpp_{y}_US", ext="csv", timeout=900)
        pts, dates = [], []
        with p.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                lat, lon = float(r["latitude"]), float(r["longitude"])
                if 32.4 <= lat <= 42.1 and -124.6 <= lon <= -114.0 and r["confidence"] in ("n", "h"):
                    pts.append((lon, lat))
                    dates.append(r["acq_date"])
        inside = np.zeros(len(pts), bool)
        for pa in paths:
            inside |= pa.contains_points(pts)
        days.update(d for d, ok in zip(dates, inside) if ok)
        print(" ", y, int(inside.sum()), "CA detections")
    return sorted(days.items())


if __name__ == "__main__":
    ca = outline()
    inc = incidents()
    per = perimeters()
    det = detections_per_day(ca)
    acres_by_year = {y: round(sum(d["acres"] for d in inc if d["y"] == y)) for y in YEARS}
    featured = []
    for f in sorted(FIRES, key=lambda f: (f["year"], f["name"])):
        v = json.loads((WEB_DATA / f["id"] / "meta.json").read_text(encoding="utf-8"))["validation"]
        featured.append(dict(id=f["id"], name=f["name"], year=f["year"],
                             acres=round(v.get("calfire_acres") or v["official_gis_acres"]),
                             parts=[nice(n) for n in v["official_parts"]]))
    # a complex is stored as several named parts: show it once, under its own name
    for f in featured:
        if len(f["parts"]) > 1:
            mine = [p for p in per if p["y"] == f["year"] and p["name"] in f["parts"]]
            if mine:
                per = [p for p in per if p not in mine] + [dict(name=f["name"], acres=f["acres"], y=f["year"],
                       start=min(p["start"] for p in mine), rings=[r for p in mine for r in p["rings"]])]
                f["parts"] = [f["name"]]
    per.sort(key=lambda d: -d["acres"])
    write_json(WEB_DATA / "state.json", dict(outline=ca, incidents=inc, perimeters=per, detections=det,
                                             acres_by_year=acres_by_year, featured=featured))
    print(len(inc), "incidents;", len(per), "perimeters;", len(det), "days;", acres_by_year)
