"""Drought tab, actionable layers -> web/data/ca-drought/ (run after build_drought.py; it adds keys to meta.json).

1. Wells: USGS OGC API field-measurements (parameter 72019, depth to water, ft below land surface), static manual readings
   2020-2023, joined with USGS monitoring-location metadata (constructed depth, land altitude) and DWR GWL well metadata
   (depth, perforated interval) where a DWR well lies within 150 m.
2. Bucket model (MODELLED): daily Open-Meteo/ERA5 precipitation, ET0, mean temperature on a 0.5 degree grid.
3. GRACE groundwater percentile (NASA GRACE-DA, University of Nebraska), weekly GeoTIFFs cropped to the block.
"""
import base64
import glob
import json
import math
import time
from collections import defaultdict
from datetime import date, datetime, timedelta

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

import build_fire as B
from build_drought import BOX
from common import ROOT, RAW, WEB_DATA, fetch, fetch_json, write_json

OUT = WEB_DATA / "ca-drought"
OGC = "https://api.waterdata.usgs.gov/ogcapi/v0/collections"
DWR = "https://services.arcgis.com/aa38u6OgfNoCkTJ6/arcgis/rest/services/GWL_Recently_Measured_v3/FeatureServer/0/query"
METEO = "https://archive-api.open-meteo.com/v1/archive"
FT = 0.3048

# bucket-model parameters (textbook values; stated in the app)
SMAX, KC, FC, KDRAIN, MELT, SPIN = 200.0, 0.7, 0.5, 0.02, 3.0, date(2019, 10, 1)


def b64(a):
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode("ascii")


# ------------------------------------------------------------------ wells
def pull_wells():
    url = f"{OGC}/field-measurements/items"
    params = dict(f="json", parameter_code="72019", bbox="-124.6,32.4,-114,42.1", time="2020-01-01/2023-12-31", limit=1000,
                  properties="monitoring_location_id,value,unit_of_measure,time,qualifier,approval_status,observing_procedure_code")
    n, nxt = 0, None
    while True:
        p = fetch(nxt or url, params=None if nxt else params, source="usgs_ogc", name=f"fm72019_p{n}", ext="json")
        d = json.loads(p.read_text())
        yield from d["features"]
        n += 1
        nxt = next((l["href"] for l in d["links"] if l["rel"] == "next"), None)
        if not nxt or not d["features"]:
            break


def build_wells(grid, weeks, cid):
    by, xy, total, kept = defaultdict(list), {}, 0, 0
    for ft in pull_wells():
        p = ft["properties"]
        total += 1
        q = p["qualifier"] or []
        if p["value"] is None or "Static" not in q or "Pumping" in q:   # drop dry/obstructed (no value) and pumping readings
            continue
        v = float(p["value"])
        if not 0 <= v <= 1500:
            continue
        by[p["monitoring_location_id"]].append((p["time"][:10], v)); xy[p["monitoring_location_id"]] = ft["geometry"]["coordinates"]; kept += 1
    cand = [k for k, v in by.items() if len(v) >= 8 and min(d for d, _ in v) <= "2020-07-31" and max(d for d, _ in v) >= "2023-06-01"
            and len({d[:4] for d, _ in v}) == 4]
    # USGS site metadata (constructed depth, land altitude)
    meta = {}
    cand.sort()
    for i in range(0, len(cand), 50):
        d = fetch_json(f"{OGC}/monitoring-locations/items", source="usgs_ogc", name=f"loc_{i // 50}", params=dict(
            f="json", id=",".join(cand[i:i + 50]), limit=100, properties="id,altitude,well_constructed_depth,hole_constructed_depth,monitoring_location_name,county_name,aquifer_code,national_aquifer_code"))
        for f in d["features"]:
            meta[f["properties"]["id"]] = f["properties"]
    # DWR well metadata (depth and perforated interval), nearest within 150 m
    dwr = []
    for i, off in enumerate(range(0, 10000, 2000)):
        d = fetch_json(DWR, source="dwr_gwl", name=f"recent_{i}", params=dict(where="1=1", outFields="*", f="geojson", resultOffset=off, resultRecordCount=2000))
        dwr += d["features"]
        if len(d["features"]) < 2000:
            break
    P = np.array([[f["properties"]["LONGITUDE"] or 0, f["properties"]["LATITUDE"] or 0] for f in dwr]) * [0.8, 1]
    tree = cKDTree(P)
    rows = []
    for k in cand:
        m = meta.get(k)
        if not m:
            continue
        dd, j = tree.query(np.array(xy[k]) * [0.8, 1])
        dp = dwr[j]["properties"] if dd * 111000 < 150 else None
        depth = m.get("well_constructed_depth") or (dp and dp["WELL_DEPTH"])
        mx = max(v for _, v in by[k])
        if not depth or depth < 1.05 * mx or m.get("altitude") is None:
            continue
        x, y = grid.px(*xy[k])
        if not (0 <= int(y) < grid.H and 0 <= int(x) < grid.W) or cid[int(y), int(x)] == 0:
            continue
        rows.append(dict(id=k, lon=xy[k][0], lat=xy[k][1], x=x, y=y, alt_ft=m["altitude"], depth_ft=float(depth), name=m["monitoring_location_name"],
                         county=m["county_name"].replace(" County", ""), n=len(by[k]), dwr=dp, r=sorted(by[k])))
    # Central Valley = within 0.7 deg of the valley axis and below 800 ft
    a, b = np.array([-122.2, 40.3]), np.array([-118.6, 35.0])
    for r in rows:
        p = np.array([r["lon"], r["lat"]]) - a; ab = b - a
        t = np.clip(p @ ab / (ab @ ab), 0, 1); r["valley"] = bool(np.hypot(*((p - t * ab) * [0.8, 1])) < 0.7 and r["alt_ft"] < 800)
    # farthest-point sampling: 60 valley + 40 elsewhere
    pick = []
    for grp, n in ((True, 60), (False, 40)):
        pool = [r for r in rows if r["valley"] == grp]
        if not pool:
            continue
        pts = np.array([[r["lon"] * 0.8, r["lat"]] for r in pool])
        ch = [int(np.argmax([r["n"] for r in pool]))]
        dist = np.hypot(*(pts - pts[ch[0]]).T)
        while len(ch) < min(n, len(pool)):
            j = int(np.argmax(dist)); ch.append(j); dist = np.minimum(dist, np.hypot(*(pts - pts[j]).T))
        pick += [pool[j] for j in ch]
    print(f"wells: {total} OGC records, {kept} static readings, {len(cand)} wells with 4-year cover, {len(rows)} usable, {len(pick)} picked, "
          f"{sum(bool(r['dwr']) for r in pick)} matched in DWR")
    day = lambda s: date.fromisoformat(s).toordinal()
    wd = np.array([day(w) for w in weeks])
    D = np.zeros((len(pick), len(weeks)), np.int16); base = []
    for i, r in enumerate(pick):
        dd = defaultdict(list)
        for d_, v in r["r"]:
            dd[d_].append(v)
        ds = sorted(dd); xs = np.array([day(d_) for d_ in ds]); vs = np.array([np.mean(dd[d_]) for d_ in ds])
        D[i] = np.round(np.interp(wd, xs, vs) * 10)     # linear between readings, held flat before the first and after the last
        b0 = float(np.median([v for d_, v in r["r"] if d_.startswith("2020")])); base.append(b0)
        r["first"], r["last"] = ds[0], ds[-1]
    chg = D / 10 - np.array(base)[:, None]          # ft; positive = water table deeper than the well's own 2020 median
    valley = np.array([r["valley"] for r in pick])
    wells = []
    for i, r in enumerate(pick):
        dp = r["dwr"]
        wells.append(dict(id=r["id"], name=r["name"], county=r["county"], x=round(r["x"], 1), y=round(r["y"], 1), alt_ft=r["alt_ft"], depth_ft=r["depth_ft"],
                          base_ft=round(base[i], 1), n=r["n"], first=r["first"], last=r["last"], valley=r["valley"],
                          screen=[dp["TOP_PRF"], dp["BOT_PRF"]] if dp and dp["TOP_PRF"] is not None and dp["BOT_PRF"] is not None else None,
                          dwr_depth=dp["WELL_DEPTH"] if dp else None))
    cnt = dict(n_records=total, n_static=kept, n_cand=len(cand), n_usable=len(rows), n_screen=sum(1 for w in wells if w['screen']), n_dwr=sum(1 for r in pick if r['dwr']))
    return wells, D, chg, valley, cnt


# ------------------------------------------------------------------ bucket model
def run_bucket(P, E, T):
    """Vectorised over points. Returns S (mm), drainage (mm/day), SWE (mm) per day."""
    n, nd = P.shape
    S = np.full(n, 0.5 * SMAX); snow = np.zeros(n)
    So, Do, Wo = np.zeros((n, nd)), np.zeros((n, nd)), np.zeros((n, nd))
    for t in range(nd):
        cold = T[:, t] < 0
        snow += np.where(cold, P[:, t], 0)
        melt = np.minimum(snow, MELT * np.maximum(T[:, t], 0)); snow -= melt
        inflow = np.where(cold, 0, P[:, t]) + melt
        eta = E[:, t] * KC * np.minimum(1, S / (FC * SMAX))
        S = np.maximum(0, S + inflow - eta)
        over = np.maximum(0, S - SMAX); S -= over
        slow = KDRAIN * np.maximum(0, S - FC * SMAX); S -= slow
        So[:, t], Do[:, t], Wo[:, t] = S, over + slow, snow
    return So, Do, Wo


def re_q(p):   # latitude/longitude lists of a cached request, from the manifest
    import re
    rel = str(p.relative_to(ROOT)).replace("\\", "/")
    for l in open(RAW / "manifest.jsonl", encoding="utf-8"):
        if rel in l:
            rec = json.loads(l); q = rec["url"]
            la = re.search(r"latitude=([^&]+)", q).group(1).replace("%2C", ",").split(","); lo = re.search(r"longitude=([^&]+)", q).group(1).replace("%2C", ",").split(",")
            return list(zip(la, lo))
    raise KeyError(p)


def build_bucket(grid, weeks, cid):
    lons = np.arange(-124.5, -113.9, 0.5); lats = np.arange(32.5, 42.1, 0.5)
    nx, ny = len(lons), len(lats)
    pts = [(la, lo) for la in lats[::-1] for lo in lons]          # row 0 = north
    near = []
    for la, lo in pts:
        x, y = grid.px(lo, la); xi, yi = int(x), int(y)
        r = 14                                                     # px; ~0.25 deg
        win = cid[max(0, yi - r):yi + r, max(0, xi - r):xi + r]
        near.append(win.size > 0 and bool((win > 0).any()))
    use = [i for i, k in enumerate(near) if k]
    print("bucket grid", nx, "x", ny, "points near California:", len(use))
    days = (date(2023, 12, 31) - SPIN).days + 1
    Pm, Em, Tm, Lm = (np.full((len(pts), days), np.nan) for _ in range(4)); elev = np.zeros(len(pts))
    KEYS = (("precipitation_sum", Pm), ("et0_fao_evapotranspiration", Em), ("temperature_2m_mean", Tm), ("soil_moisture_0_to_100cm_mean", Lm))
    have = {}
    import hashlib
    for p in sorted(OUTC.glob("drought_bucket_*.json")):          # first, bigger requests from 2019-01-01 (kept: they are real downloads)
        d = json.loads(p.read_text())
        for r, (la, lo) in zip(d, re_q(p)):
            r["latitude_in"], r["longitude_in"] = float(la), float(lo); have[(round(float(la), 2), round(float(lo), 2))] = (r, (SPIN - date(2019, 1, 1)).days)
    todo = [i for i in use if (round(pts[i][0], 2), round(pts[i][1], 2)) not in have]
    print("points cached:", len(use) - len(todo), "to fetch:", len(todo))
    for b in range(0, len(todo), 5):
        idx = todo[b:b + 5]
        la, lo = ",".join(f"{pts[i][0]:.2f}" for i in idx), ",".join(f"{pts[i][1]:.2f}" for i in idx)
        name = "drought_pts_" + hashlib.sha1((la + lo).encode()).hexdigest()[:10]
        cached = (OUTC / f"{name}.json").exists()
        for attempt in range(12):
            try:
                d = fetch_json(METEO, source="open_meteo", name=name, params=dict(latitude=la, longitude=lo, start_date=SPIN.isoformat(), end_date="2023-12-31", timezone="UTC",
                                                                              daily="precipitation_sum,et0_fao_evapotranspiration,temperature_2m_mean,soil_moisture_0_to_100cm_mean"))
                break
            except RuntimeError as e:
                print("wait:", str(e)[-90:], flush=True); time.sleep(300)
        for i, r in zip(idx, d if isinstance(d, list) else [d]):
            have[(round(pts[i][0], 2), round(pts[i][1], 2))] = (r, 0)
        if not cached:
            time.sleep(9)
    for i in use:
        r, off = have[(round(pts[i][0], 2), round(pts[i][1], 2))]
        dl = r["daily"]
        for key, arr in KEYS:
            v = [np.nan if x is None else x for x in dl[key]][off:]
            assert len(v) == days, (len(v), days)
            arr[i] = v
        elev[i] = r.get("elevation", 0)
    ok = [i for i in use if not np.isnan(Pm[i]).any() and not np.isnan(Em[i]).any() and not np.isnan(Tm[i]).any()]
    print("points with complete forcing:", len(ok), "of", len(use))
    Pm[np.isnan(Pm)] = 0
    S, D, W = run_bucket(Pm[ok], Em[ok], Tm[ok])
    # weekly values on the USDM dates; drainage = mean of the 7 days to the date
    wi = np.array([(date.fromisoformat(w) - SPIN).days for w in weeks])
    Sw = S[:, wi]; Dw = np.stack([D[:, i - 6:i + 1].mean(1) for i in wi], 1); Ww = W[:, wi]
    # fill the points with no forcing (ocean / no data) from the nearest modelled point
    full = np.zeros((len(pts), len(weeks), 3), np.float32)
    okp = np.array([pts[i] for i in ok]); tr = cKDTree(okp * [1, 0.8])
    for i, (la, lo) in enumerate(pts):
        j = tr.query([la, lo * 0.8])[1]
        full[i, :, 0], full[i, :, 1], full[i, :, 2] = Sw[j] / SMAX, Dw[j], Ww[j]
    # land mask for statewide means: points whose own cell centre is in California
    inca = np.array([cid[min(grid.H - 1, max(0, int(grid.px(lo, la)[1]))), min(grid.W - 1, max(0, int(grid.px(lo, la)[0])))] > 0 for la, lo in pts])
    okset = {i: k for k, i in enumerate(ok)}
    sel = [okset[i] for i in ok if inca[i]]
    print("California-land points:", len(sel))
    state_S = (Sw[sel] / SMAX).mean(0); state_D = Dw[sel].mean(0); state_W = Ww[sel].mean(0)
    # ERA5-Land check: weekly volumetric soil moisture 0-100 cm vs modelled S/Smax at the same points
    L = Lm[ok][:, wi]; okL = ~np.isnan(L).any(1)
    rr = [np.corrcoef(Sw[k] / SMAX, L[k])[0, 1] for k in range(len(ok)) if okL[k]]
    woy = np.array([date.fromisoformat(w).isocalendar()[1] for w in weeks])
    def anom(x):
        y = x.copy()
        for wk in np.unique(woy):
            y[..., woy == wk] -= x[..., woy == wk].mean(-1, keepdims=True)
        return y
    ra = [np.corrcoef(anom(Sw[k] / SMAX), anom(L[k]))[0, 1] for k in range(len(ok)) if okL[k]]
    Ls = np.nanmean(L[[okset[i] for i in ok if inca[i] and okL[okset[i]]]], 0)
    chk = dict(n_points=len(rr), r_median=float(np.nanmedian(rr)), r_p10=float(np.nanpercentile(rr, 10)), r_p90=float(np.nanpercentile(rr, 90)),
               r_anom_median=float(np.nanmedian(ra)), r_state=float(np.corrcoef(state_S, Ls)[0, 1]), r_state_anom=float(np.corrcoef(anom(state_S), anom(Ls))[0, 1]))
    print("ERA5-Land check", {k: round(v, 3) for k, v in chk.items()})
    wet = lambda s, a, b: float(s[a:b].mean())
    return dict(n_model=len(ok), nx=nx, ny=ny, lon0=float(lons[0]), lat0=float(lats[-1]), step=0.5, full=full, state_S=state_S, state_D=state_D, state_W=state_W,
                era5land=Ls, chk=chk, elev=elev)


OUTC = RAW / "open_meteo"


# ------------------------------------------------------------------ GRACE
def build_grace(grid, weeks, cid):
    lo0, la0, lo1, la1 = BOX
    c0, c1 = int((lo0 + 125) / 0.125), math.ceil((lo1 + 125) / 0.125)
    r0, r1 = int((53 - la1) / 0.125), math.ceil((53 - la0) / 0.125)
    A = np.full((len(weeks), r1 - r0, c1 - c0), 255, np.uint8); first = None
    for k, w in enumerate(weeks):
        m = (date.fromisoformat(w) - timedelta(days=1)).strftime("%Y%m%d")
        p = RAW / "nasa_grace" / f"gws_{m}.tif"
        im = Image.open(p); t = im.tag_v2
        if first is None:
            first = (t[33550][:2], t[33922][3:5], im.size)
            assert first == ((0.125, 0.125), (-125.0, 53.0), (464, 224)), first     # georeferencing: top-left corner -125, 53; 0.125 deg cells
        a = np.array(im)[r0:r1, c0:c1]
        A[k] = np.where(a < -900, 255, np.clip(np.round(a), 0, 100)).astype(np.uint8)
    # statewide / valley means over cells whose centre is in California
    rows, cols = np.mgrid[r0:r1, c0:c1]
    lon = -125 + (cols + 0.5) * 0.125; lat = 53 - (rows + 0.5) * 0.125
    inca = np.zeros(lon.shape, bool)
    for (i, j), lo in np.ndenumerate(lon):
        x, y = grid.px(lo, lat[i, j]); xi, yi = int(x), int(y)
        inca[i, j] = 0 <= xi < grid.W and 0 <= yi < grid.H and cid[yi, xi] > 0
    valid = inca[None] & (A < 255)
    state = np.array([A[k][valid[k]].mean() for k in range(len(weeks))])
    # Central Valley: cells within 0.7 deg of the valley axis
    a_, b_ = np.array([-122.2, 40.3]), np.array([-118.6, 35.0]); ab = b_ - a_
    pp = np.stack([lon - a_[0], lat - a_[1]], -1); tt = np.clip((pp @ ab) / (ab @ ab), 0, 1)
    inv = np.hypot((pp[..., 0] - tt * ab[0]) * 0.8, pp[..., 1] - tt * ab[1]) < 0.7
    vv = valid & inv[None]
    valley = np.array([A[k][vv[k]].mean() for k in range(len(weeks))])
    print("GRACE crop", A.shape, "rows", r0, r1, "cols", c0, c1, "CA cells", int(inca.sum()), "state mean first/last", state[0].round(1), state[-1].round(1))
    return dict(A=A, c0=c0, r0=r0, nx=c1 - c0, ny=r1 - r0, lon0=-125 + c0 * 0.125, lat0=53 - r0 * 0.125, state=state, valley=valley, n_ca=int(inca.sum()))


if __name__ == "__main__":
    meta = json.loads((OUT / "meta.json").read_text(encoding="utf-8"))
    weeks = meta["weeks"]; g = meta["grid"]
    grid = B.Grid(BOX)
    cid = np.frombuffer(base64.b64decode((OUT / "counties.txt").read_text()), np.uint8).reshape(grid.H, grid.W)
    wells, D, chg, valley, cnt = build_wells(grid, weeks, cid)
    bk = build_bucket(grid, weeks, cid)
    gr = build_grace(grid, weeks, cid)

    # --- statistics that the panel text quotes
    wk = lambda s: weeks.index(next(w for w in weeks if w >= s))
    med = np.median(chg, 0); medv = np.median(chg[valley], 0)
    def sc(x, p=1): return [None if v is None else round(float(v), p) for v in x]
    st = dict(**cnt, n_wells=len(wells), n_valley=int(valley.sum()), med_end=float(med[-1]), medv_end=float(medv[-1]),
              share_lower=float((chg[:, -1] > 0).mean()), medv_peak=float(medv.max()), medv_peak_week=weeks[int(medv.argmax())])
    print(json.dumps(st, indent=1))

    # --- validation: modelled drainage/soil water vs wells (loose)
    wkly = np.arange(len(weeks))
    cumD = np.cumsum(bk["state_D"]) / 7
    r_wells_S = float(np.corrcoef(bk["state_S"], medv)[0, 1])
    r_wells_G = float(np.corrcoef(gr["valley"], medv)[0, 1])
    r_wells_Gs = float(np.corrcoef(gr["state"], med)[0, 1])
    print("r(valley median well change, state soil water) =", round(r_wells_S, 2), "; r(valley GRACE, valley wells) =", round(r_wells_G, 2), "; r(state GRACE, all wells) =", round(r_wells_Gs, 2))

    # --- write
    OUT.mkdir(exist_ok=True, parents=True)
    (OUT / "wells.txt").write_text(b64(D), encoding="ascii")                       # int16 [nWells, nWeeks], depth to water x10 ft
    full = bk["full"]                                                                # [pts, weeks, 3]  S fraction, drainage mm/d, SWE mm
    ny, nx = bk["ny"], bk["nx"]
    Sb = np.clip(np.round(full[..., 0] * 255), 0, 255).astype(np.uint8).reshape(ny, nx, -1).transpose(2, 0, 1)
    Db = np.clip(np.round(full[..., 1] * 20), 0, 255).astype(np.uint8).reshape(ny, nx, -1).transpose(2, 0, 1)      # 0.05 mm/day steps
    Wb = np.clip(np.round(full[..., 2] / 4), 0, 255).astype(np.uint8).reshape(ny, nx, -1).transpose(2, 0, 1)       # 4 mm steps, to 1,020 mm
    (OUT / "bucket.txt").write_text(b64(np.stack([Sb, Db, Wb])), encoding="ascii")  # uint8 [3, nWeeks, ny, nx]
    (OUT / "grace.txt").write_text(b64(gr["A"]), encoding="ascii")                  # uint8 [nWeeks, ny, nx], 255 = no data
    meta["wells"] = dict(items=wells, med=sc(med), med_valley=sc(medv), sd=dict(zip(["n_wells", "n_valley"], [len(wells), int(valley.sum())])), stats=st,
                         source="USGS OGC API field-measurements, parameter 72019, static readings 2020-2023")
    meta["bucket"] = dict(nx=nx, ny=ny, lon0=bk["lon0"], lat0=bk["lat0"], step=bk["step"], smax=SMAX, kc=KC, fc=FC, kdrain=KDRAIN, melt=MELT, spin=SPIN.isoformat(),
                          state_S=sc(bk["state_S"] * 100), state_era5land=sc(bk["era5land"], 3), state_D=sc(bk["state_D"], 3), state_swe=sc(bk["state_W"], 1), check=bk["chk"], n_model=bk["n_model"],
                          r_valley_wells_vs_state_soil=r_wells_S)
    meta["grace"] = dict(nx=gr["nx"], ny=gr["ny"], lon0=gr["lon0"], lat0=gr["lat0"], step=0.125, state=sc(gr["state"]), valley=sc(gr["valley"]),
                         n_ca=gr["n_ca"], r_valley_wells=r_wells_G, r_state_wells=r_wells_Gs)
    write_json(OUT / "meta.json", meta)
    import os
    tot = sum(os.path.getsize(p) for p in glob.glob(str(OUT / "*")))
    print("ca-drought folder:", round(tot / 1e6, 2), "MB")
