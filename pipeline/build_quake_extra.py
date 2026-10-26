"""Actionable layers for the Ridgecrest tab, added to web/data/ridgecrest/meta.json (run after build_quake.py).

1. Warning-time what-if: CI seismic stations (IRIS FDSN, HH/HN channels, operating on 6 Jul 2019) -> distance to the 4th-nearest
   station. The app computes warning = hypocentral distance / Vs - (d4 / Vp + latency). All timing is simulated.
2. Aftershock clock: Reasenberg-Jones parameters from the USGS operational aftershock forecast product (forecast.json).
3. GNSS offsets: NGL daily IGS14 positions (tenv3), mean of 3 Jul-minus-6 days vs 8-13 Jul; USGS ShakeMap rupture polygon.
"""
import json
import math
from datetime import date, datetime, timedelta, timezone

import numpy as np

import build_fire as B
from common import RAW, WEB_DATA, fetch, fetch_json, write_json

EV = "ci38457511"
IRIS = "https://service.iris.edu/fdsnws/station/1/query"
NGL = "https://geodesy.unr.edu/gps_timeseries/IGS14/tenv3/IGS14/{}.tenv3"
VP, VS = 6.0, 3.5


def hav(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    a = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(a))


def decyear_date(s):          # "19JUL06" -> date
    return datetime.strptime(s, "%y%b%d").date()


if __name__ == "__main__":
    meta = json.loads((WEB_DATA / "ridgecrest" / "meta.json").read_text(encoding="utf-8"))
    bb = meta["grid"]["bbox_ll"]
    grid = B.Grid((bb[0], bb[1], bb[2], bb[3]))
    det = json.loads((RAW / "usgs_quakes" / f"detail_{EV}.json").read_text(encoding="utf-8"))
    lon0, lat0, dep = det["geometry"]["coordinates"]
    pr = det["properties"]["products"]

    # --- 1. stations ---
    p = fetch(IRIS, source="iris_fdsn", name="ci_stations_20190706", ext="txt", params=dict(
        net="CI", channel="HN?,HH?", starttime="2019-07-06T03:00:00", endtime="2019-07-06T04:00:00", level="station", format="text",
        minlatitude=33.5, maxlatitude=38.0, minlongitude=-120.5, maxlongitude=-114.5))
    st = []
    for l in p.read_text().splitlines()[1:]:
        f = l.split("|")
        la, lo = float(f[2]), float(f[3])
        d = math.hypot(hav(lat0, lon0, la, lo), dep)
        x, y = grid.px(lo, la)
        st.append(dict(code=f[1], lat=la, lon=lo, d_hypo=round(d, 2), x=round(x, 1), y=round(y, 1)))
    st.sort(key=lambda s: s["d_hypo"])
    d4 = st[3]["d_hypo"]
    print(len(st), "CI HH/HN stations; nearest four (km):", [(s["code"], s["d_hypo"]) for s in st[:4]], "-> t_P at 4th =", round(d4 / VP, 2), "s")
    near = [s for s in st if 0 <= s["x"] < grid.W and 0 <= s["y"] < grid.H]
    meta["warn"] = dict(vp=VP, vs=VS, d4_km=d4, nearest4=[s["code"] for s in st[:4]], latency_s=5.0, n_stations=len(st),
                        stations=near, depth_km=dep, source="IRIS FDSN station service, net CI, channels HH?/HN?, operating 2019-07-06",
                        real_alert_s=7.4)

    # --- 2. aftershock forecast ---
    oaf = [v["url"] for n, v in pr["oaf"][0]["contents"].items() if n.endswith("forecast.json")][0]
    f = fetch_json(oaf, source="usgs_oaf", name="oaf_ci38457511")
    pm = f["model"]["parameters"]
    meta["oaf"] = dict(a=pm["a"], b=pm["b"], p=pm["p"], c=pm["c"], mag_main=pm["magMain"], mcat=pm["Mcat"], radius_km=pm["regionRadius"],
                       center=[pm["regionCenterLat"], pm["regionCenterLon"]], obs={str(int(o["magnitude"])): o["count"] for o in f["observations"]},
                       model=f["model"]["name"], created=datetime.fromtimestamp(f["creationTime"] / 1000, timezone.utc).date().isoformat())
    print("OAF", meta["oaf"])

    # --- 3a. rupture polygon ---
    ru = [v["url"] for n, v in pr["shakemap"][0]["contents"].items() if n.endswith("rupture.json")][0]
    r = fetch_json(ru, source="usgs_shakemap", name=f"rupture_{EV}")
    polys = []
    for ft in r["features"]:
        g = ft["geometry"]
        rings = g["coordinates"] if g["type"] == "Polygon" else [rr for pl in g["coordinates"] for rr in pl]
        for ring in rings:
            polys.append([[*(round(v, 1) for v in grid.px(c[0], c[1])), round(c[2] if len(c) > 2 else 0, 1)] for c in ring])
    meta["rupture"] = polys
    print("rupture rings", len(polys), "points", sum(len(p) for p in polys))

    # --- 3b. GNSS offsets ---
    t = fetch("https://geodesy.unr.edu/NGLStationPages/llh.out", source="ngl_gnss", name="llh", ext="txt").read_text().splitlines()
    cand = []
    for l in t:
        w = l.split()
        if len(w) < 3:
            continue
        la, lo = float(w[1]), float(w[2])
        lo = ((lo + 180) % 360) - 180
        d = hav(lat0, lon0, la, lo)
        if d < 130:
            cand.append((d, w[0], la, lo))
    cand.sort()
    out = []
    pre0, pre1, post0, post1 = date(2019, 6, 27), date(2019, 7, 3), date(2019, 7, 8), date(2019, 7, 13)
    for d, code, la, lo in cand:
        try:
            tx = fetch(NGL.format(code), source="ngl_gnss", name=f"tenv3_{code}", ext="tenv3", timeout=120).read_text().splitlines()
        except RuntimeError:
            continue
        pre, mid, post = [], [], []
        for l in tx[1:]:
            w = l.split()
            try:
                dt = decyear_date(w[1])
            except ValueError:
                continue
            e, n, u = float(w[7]) + float(w[8]), float(w[9]) + float(w[10]), float(w[11]) + float(w[12])
            if pre0 <= dt <= pre1:
                pre.append((e, n, u))
            elif post0 <= dt <= post1:
                post.append((e, n, u))
            elif dt == date(2019, 7, 5):
                mid.append((e, n, u))
        if len(pre) >= 3 and len(post) >= 3 and mid:
            dv = (np.mean(post, axis=0) - np.mean(pre, axis=0)) * 1000
            dm = (np.mean(mid, axis=0) - np.mean(pre, axis=0)) * 1000        # 5 Jul: after the M6.4 (4 Jul), before the M7.1 (6 Jul)
            x, y = grid.px(lo, la)
            if 0 <= x < grid.W and 0 <= y < grid.H:
                out.append(dict(code=code, lat=round(la, 4), lon=round(lo, 4), x=round(x, 1), y=round(y, 1), dist_km=round(d, 1),
                                dE=round(float(dv[0]), 1), dN=round(float(dv[1]), 1), dU=round(float(dv[2]), 1),
                                mE=round(float(dm[0]), 1), mN=round(float(dm[1]), 1)))
        if len(out) >= 24:
            break
    meta["gnss"] = dict(stations=out, windows=dict(pre=[pre0.isoformat(), pre1.isoformat()], mid="2019-07-05", post=[post0.isoformat(), post1.isoformat()]),
                        frame="IGS14", source="Nevada Geodetic Laboratory daily solutions (tenv3)")
    mx = max(out, key=lambda s: math.hypot(s["dE"], s["dN"]))
    print(len(out), "GNSS stations; largest horizontal offset", mx["code"], round(math.hypot(mx["dE"], mx["dN"])), "mm", "at", mx["dist_km"], "km")
    write_json(WEB_DATA / "ridgecrest" / "meta.json", meta)
