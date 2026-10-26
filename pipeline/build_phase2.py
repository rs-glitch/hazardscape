"""Phase 2 data layers for the Drought and Floods tabs (adds to meta.json; run after build_drought*.py and build_flood.py).

Drought (ca-drought):
  snow.txt   MEASURED  NRCS SNOTEL snow water equivalent (WTEQ, daily) at California SNOTEL sites, on the USDM weeks, with the
                       NRCS daily median (1991-2020 normals) for % of median.
  rain.txt   MEASURED* Open-Meteo ERA5 daily precipitation (reanalysis, already cached by the bucket model), weekly sums on the 0.5 deg grid.
  reservoirs MEASURED  USGS NWIS daily storage (00054) for 6 reservoirs, plus the 1991-2020 mean for the same day of year.
Floods (helene-wnc):
  mrms.txt   MEASURED  NOAA MRMS MultiSensor QPE 1H Pass2 (radar + gauges), hourly, cropped to the block at 0.01 deg.
  landslides MEASURED  USGS Hurricane Helene Landslide Inventory (preliminary; ArcGIS feature service, DOI 10.5066/P14CHGKS).
  soil       MODEL     Open-Meteo ERA5-Land soil moisture 0-7 / 7-28 cm (reanalysis) near Asheville, Sep 2024 vs the same days 2014-2023.
"""
import gzip
import io
import json
import struct
import time
from datetime import date, datetime, timedelta, timezone

import numpy as np
from PIL import Image

import build_fire as B
import build_drought as BD
import build_flood as BF
from build_drought_extra import b64, re_q, OUTC
from common import RAW, WEB_DATA, fetch, fetch_json, write_json

AWDB = "https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1/"
NWIS_DV = "https://waterservices.usgs.gov/nwis/dv/"
MRMS = "https://noaa-mrms-pds.s3.amazonaws.com/CONUS/MultiSensor_QPE_01H_Pass2_00.00/"
SLIDES = "https://services.arcgis.com/v01gqwM5QqNysAAi/arcgis/rest/services/USGS_Hurricane_Helene_Landslide_Inventory/FeatureServer/"
METEO = "https://archive-api.open-meteo.com/v1/archive"
RES = [("11370000", "Shasta Lake"), ("11406800", "Lake Oroville"), ("11525400", "Trinity Lake"), ("11413515", "New Bullards Bar"),
       ("11287500", "Don Pedro Reservoir"), ("11269500", "Lake McClure")]


def sc(x, p=1):
    return [None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), p) for v in x]


# ------------------------------------------------------------------ drought: snow
def snow(grid, weeks):
    st = fetch_json(AWDB + "stations", source="nrcs_awdb", name="ca_sntl_stations", params=dict(stationTriplets="*:CA:SNTL", returnForecastPointMetadata="false"))
    items, swe, med = [], [], []
    wk = [date.fromisoformat(w) for w in weeks]
    for s in st:
        if s.get("endDate", "2100")[:4] < "2024" or s.get("beginDate", "2100")[:4] > "2019":
            continue
        x, y = grid.px(s["longitude"], s["latitude"])
        if not (0 <= x < grid.W and 0 <= y < grid.H):
            continue
        d = fetch_json(AWDB + "data", source="nrcs_awdb", name="wteq_" + s["stationTriplet"].replace(":", "_"),
                       params=dict(stationTriplets=s["stationTriplet"], elements="WTEQ", duration="DAILY", beginDate="2019-12-25", endDate="2023-12-31", centralTendencyType="MEDIAN"))
        vals = {v["date"][:10]: v for blk in d for e in blk.get("data", []) for v in e.get("values", [])}
        a = [vals.get(w.isoformat(), {}) for w in wk]
        sw = [v.get("value") for v in a]; md = [v.get("median") for v in a]
        if sum(v is not None for v in sw) < 0.9 * len(wk):
            continue
        items.append(dict(id=s["stationTriplet"], name=s["name"], x=round(x, 1), y=round(y, 1), elev_ft=round(s["elevation"])))
        swe.append([np.nan if v is None else v for v in sw]); med.append([np.nan if v is None else v for v in md])
    swe, med = np.array(swe), np.array(med)
    # statewide index the way NRCS/DWR quote it: sum of SWE over sites / sum of median SWE over the same sites (only when the median is > 1 in)
    ok = (med > 1.0) & ~np.isnan(swe)
    idx = [float(np.nansum(np.where(ok[:, k], swe[:, k], 0)) / np.nansum(np.where(ok[:, k], med[:, k], 0)) * 100) if ok[:, k].sum() >= 10 else None for k in range(len(wk))]
    print("SNOTEL sites:", len(items), "peak SWE index (wk, %):", [(weeks[k], round(v)) for k, v in enumerate(idx) if v and weeks[k][5:7] == "04" and weeks[k][8:10] <= "07"])
    enc = lambda a: np.clip(np.nan_to_num(np.round(a * 10), nan=-1), -1, 32000).astype(np.int16)        # tenths of an inch, -1 = no data
    return dict(items=items, index=sc(idx, 0), unit="in", source="NRCS AWDB REST v1, SNOTEL WTEQ daily, median = NRCS daily median"), np.stack([enc(swe), enc(med)])


# ------------------------------------------------------------------ drought: rain (cached ERA5 daily precipitation)
def rain(weeks, bk):
    days = {}
    for p in sorted(OUTC.glob("drought_*.json")):
        d = json.loads(p.read_text()); d = d if isinstance(d, list) else [d]
        for r, (la, lo) in zip(d, re_q(p)):
            t, pr = r["daily"]["time"], r["daily"]["precipitation_sum"]
            days[(round(float(la), 2), round(float(lo), 2))] = dict(zip(t, pr))
    nx, ny = bk["nx"], bk["ny"]
    lons = [bk["lon0"] + i * 0.5 for i in range(nx)]; lats = [bk["lat0"] - j * 0.5 for j in range(ny)]
    out = np.full((len(weeks), ny, nx), 255, np.uint8); clim = []
    for j, la in enumerate(lats):
        for i, lo in enumerate(lons):
            s = days.get((round(la, 2), round(lo, 2)))
            if not s:
                continue
            for k, w in enumerate(weeks):
                d0 = date.fromisoformat(w)
                v = [s.get((d0 - timedelta(days=q)).isoformat()) for q in range(7)]
                if None not in v:
                    out[k, j, i] = min(254, round(sum(v) / 2))                 # 2 mm steps, to 508 mm per week
    have = out[0] < 255
    wt = np.where(out < 255, out, 0).astype(float) * 2
    state = (wt * have).sum((1, 2)) / have.sum()
    # water-year totals (Oct-Sep), statewide mean over the points
    wy = {}
    for k, w in enumerate(weeks):
        y = int(w[:4]) + (1 if int(w[5:7]) >= 10 else 0); wy[y] = wy.get(y, 0) + state[k]
    print("rain grid points:", int(have.sum()), "water-year statewide mean totals (partial years at ends):", {y: round(v) for y, v in wy.items()})
    return dict(state=sc(state, 1), wy={str(y): round(v) for y, v in wy.items()}, step_mm=2,
                source="Open-Meteo ERA5 daily precipitation_sum (reanalysis), weekly sum to each USDM date"), out


# ------------------------------------------------------------------ drought: reservoirs vs the average for the date
def reservoirs(grid, weeks):
    out = []
    for site, label in RES:
        d = fetch_json(NWIS_DV, source="usgs_nwis", name=f"storage_hist_{site}", params=dict(format="json", sites=site, parameterCd="00054", startDT="1990-10-01", endDT="2023-12-31"))
        vals = {}
        for ts in d["value"]["timeSeries"]:
            for blk in ts["values"]:
                for v in blk["value"]:
                    if float(v["value"]) >= 0:
                        vals[v["dateTime"][:10]] = float(v["value"])
        geo = d["value"]["timeSeries"][0]["sourceInfo"]["geoLocation"]["geogLocation"]
        doy = {}
        for k, v in vals.items():
            if "1991-01-01" <= k <= "2020-12-31":
                doy.setdefault(k[5:10], []).append(v)
        series, avg = [], []
        for w in weeks:
            day = date.fromisoformat(w)
            v = next((vals[(day - timedelta(days=q)).isoformat()] for q in range(7) if (day - timedelta(days=q)).isoformat() in vals), None)
            a = doy.get(w[5:10]) or doy.get((day - timedelta(days=1)).isoformat()[5:10])
            series.append(v); avg.append(float(np.mean(a)) if a and len(a) >= 20 else None)
        x, y = grid.px(geo["longitude"], geo["latitude"])
        nyr = len(doy.get("04-01", []))
        cap = max(vals.values())
        print(f"{label:22s} years in 1991-2020 normal: {nyr}  record max {cap:,.0f}  2021-10-01 {series[weeks.index(min(weeks, key=lambda w: abs(date.fromisoformat(w) - date(2021, 10, 1))))]}")
        out.append(dict(site=site, name=label, x=round(x, 1), y=round(y, 1), acft=series, avg_acft=sc(avg, 0), max_acft=max(v for v in series if v),
                        min_acft=min(v for v in series if v), cap_acft=cap, normal_years=nyr))
    return out


# ------------------------------------------------------------------ floods: MRMS hourly radar rain
def grib_png(b):
    """Minimal GRIB2 reader for MRMS fields: regular lat/lon grid (3.0), PNG packing (5.41). Returns (values[Nj,Ni], lat1, lon1, dlat, dlon)."""
    p, sec = 16, {}
    while p < len(b) - 4:
        ln, num = struct.unpack(">IB", b[p:p + 5]); sec[num] = b[p:p + ln]; p += ln
    g = sec[3]; Ni, Nj = struct.unpack(">II", g[30:38])
    la1, lo1 = struct.unpack(">ii", g[46:54]); la2, lo2 = struct.unpack(">ii", g[55:63]); di, dj = struct.unpack(">II", g[63:71])
    s5 = sec[5]; R = struct.unpack(">f", s5[11:15])[0]
    def sgn(v): return -(v & 0x7FFF) if v & 0x8000 else v
    E, D = sgn(struct.unpack(">H", s5[15:17])[0]), sgn(struct.unpack(">H", s5[17:19])[0])
    raw = np.array(Image.open(io.BytesIO(sec[7][5:])), dtype=np.float64)
    val = (R + raw * 2.0 ** E) / 10.0 ** D
    if len(sec.get(6, b"")) > 6 and sec[6][5] == 0:                     # bitmap present
        raise ValueError("bitmap not handled")
    return val.reshape(Nj, Ni), la1 / 1e6, lo1 / 1e6 - 360, dj / 1e6, di / 1e6


def mrms(meta):
    w, s, e, n = meta["grid"]["bbox_ll"]
    t0 = datetime.fromisoformat(meta["t0"]).astimezone(timezone.utc)
    frames = []
    for h in range(meta["hours"]):
        t = t0 + timedelta(hours=h + 1)                                      # file stamped at the END of its hour
        key = f"{t:%Y%m%d}/MRMS_MultiSensor_QPE_01H_Pass2_00.00_{t:%Y%m%d-%H}0000.grib2.gz"
        path = fetch(MRMS + key, source="noaa_mrms", name=f"qpe1h_{t:%Y%m%d%H}", ext="grib2.gz")
        v, la1, lo1, dla, dlo = grib_png(gzip.decompress(path.read_bytes()))
        r0, r1 = int(round((la1 - n) / dla)), int(round((la1 - s) / dla)); c0, c1 = int(round((w - lo1) / dlo)), int(round((e - lo1) / dlo))
        frames.append(v[r0:r1, c0:c1])
    A = np.stack(frames); A[A < 0] = 0                                       # -3 = no coverage; none expected here
    tot = A.sum(0); box = A.mean((1, 2))
    print("MRMS hours", A.shape, "max 1 h mm", round(float(A.max()), 1), "max event total mm", round(float(tot.max()), 1), "box-mean total", round(float(tot.mean()), 1))
    # rain-to-crest lag: centroid hour of the heaviest 24 h of box rain vs each gauge's crest
    pk = int(np.argmax(np.convolve(box, np.ones(24), "valid"))); win = np.arange(pk, pk + 24)
    cen = float((win * box[win]).sum() / box[win].sum()) + 0.5
    peak_h = int(np.argmax(box)) + 0.5
    for g in meta["gauges"]:
        # rain over the gauge's 10 km neighbourhood: a rough stand-in for its basin
        x, y = g["x"] / meta["grid"]["W"] * A.shape[2], g["y"] / meta["grid"]["H"] * A.shape[1]
        yy, xx = np.mgrid[0:A.shape[1], 0:A.shape[2]]
        m = ((xx - x) ** 2 + (yy - y) ** 2) * (meta["grid"]["cell_ground_m"] * meta["grid"]["W"] / A.shape[2] / 1000) ** 2 < 10 ** 2
        loc = A[:, m].mean(1)
        crest = (datetime.fromisoformat(g["peak_time"]) - datetime.fromisoformat(meta["t0"])).total_seconds() / 3600
        c0 = max(0, int(crest) - 24); ph = c0 + float(np.argmax(loc[c0:int(crest) + 1])) + 0.5    # heaviest hour in the 24 h before the crest
        g["rain"] = dict(total_mm=round(float(loc.sum()), 1), max1h_mm=round(float(loc[int(ph)]), 1), peak_h=ph, crest_h=round(crest, 2),
                         lag_h=round(crest - ph, 1), before_mm=round(float(loc[:int(crest)].sum()), 1))
        print(f"  {g['label'][:30]:30s} rain {g['rain']['total_mm']} mm, peak hr {g['rain']['peak_h']}, crest hr {crest:.1f}, lag {g['rain']['lag_h']} h")
    enc = np.clip(np.round(A * 4), 0, 255).astype(np.uint8)                 # 0.25 mm steps to 63.75 mm/h
    return dict(nx=A.shape[2], ny=A.shape[1], step_mm=0.25, box_mm=sc(box, 2), max_total_mm=round(float(tot.max())), box_total_mm=round(float(tot.mean())),
                centroid_h=round(cen, 1), peak_h=peak_h, source="NOAA MRMS MultiSensor_QPE_01H_Pass2 (AWS noaa-mrms-pds), hourly, 0.01 deg"), enc, np.round(tot).astype(np.uint16)


IMP = ["Road", "Building", "River", "Other", "Various", "NONE", "UNCLEAR"]


def landslides(meta, grid):
    w, s, e, n = meta["grid"]["bbox_ll"]
    info = fetch_json(SLIDES + "0", source="usgs_landslides", name="helene_layer0", params=dict(f="json"))
    fields = [f["name"] for f in info.get("fields", [])]
    print("landslide layer:", info.get("name"), "| geometry", info.get("geometryType"), "| fields", fields[:30])
    feats, off = [], 0
    while True:
        d = fetch_json(SLIDES + "0/query", source="usgs_landslides", name=f"helene_pts_{off}", params=dict(
            where="1=1", geometry=f"{w},{s},{e},{n}", geometryType="esriGeometryEnvelope", inSR="4326", spatialRel="esriSpatialRelIntersects",
            outFields="*", returnGeometry="true", outSR="4326", f="json", resultOffset=off, resultRecordCount=2000))
        feats += d.get("features", [])
        if not d.get("exceededTransferLimit"):
            break
        off += 2000
    pts = []
    for f in feats:
        gm = f["geometry"]
        lo, la = (gm["x"], gm["y"]) if "x" in gm else np.mean([q for r in gm.get("rings", gm.get("paths", [[]])) for q in r], 0)
        x, y = grid.px(lo, la)
        pts.append([round(x, 1), round(y, 1), IMP.index(f["attributes"].get("Impact") if f["attributes"].get("Impact") in IMP else "UNCLEAR")])
    print("landslides in block:", len(pts), "sample attributes:", {k: v for k, v in feats[0]["attributes"].items()} if feats else None)
    return dict(n=len(pts), xyi=[c for p in pts for c in p], impacts=IMP, layer=info.get("name"), fields=fields,
                source="USGS Hurricane Helene Landslide Inventory (preliminary), ArcGIS feature service; data release DOI 10.5066/P14CHGKS")


def soil(meta):
    la, lo = 35.6, -82.55
    cur = fetch_json(METEO, source="open_meteo", name="helene_soil_2024", params=dict(latitude=la, longitude=lo, start_date="2024-09-01", end_date="2024-09-30",
                     hourly="soil_moisture_0_to_7cm,soil_moisture_7_to_28cm", daily="precipitation_sum", timezone="America/New_York"))
    cl = fetch_json(METEO, source="open_meteo", name="helene_soil_clim", params=dict(latitude=la, longitude=lo, start_date="2014-09-01", end_date="2023-09-30",
                    daily="soil_moisture_0_to_7cm_mean,soil_moisture_7_to_28cm_mean" if False else "precipitation_sum", hourly="soil_moisture_0_to_7cm,soil_moisture_7_to_28cm", timezone="America/New_York"))
    h = cur["hourly"]; t = h["time"]
    s1 = np.array(h["soil_moisture_0_to_7cm"], float); s2 = np.array(h["soil_moisture_7_to_28cm"], float)
    daily1 = s1.reshape(-1, 24).mean(1); daily2 = s2.reshape(-1, 24).mean(1)
    ch = cl["hourly"]; ct = np.array([x[5:10] for x in ch["time"]])
    c1 = np.array(ch["soil_moisture_0_to_7cm"], float); c2 = np.array(ch["soil_moisture_7_to_28cm"], float)
    sep = np.char.startswith(ct, "09-")
    clim1 = [float(np.nanmean(c1[ct == f"09-{d:02d}"])) for d in range(1, 31)]
    clim2 = [float(np.nanmean(c2[ct == f"09-{d:02d}"])) for d in range(1, 31)]
    p10, p90 = float(np.nanpercentile(c2[sep], 5)), float(np.nanpercentile(c2[sep], 99.5))
    rain = cur["daily"]["precipitation_sum"]
    print("soil 7-28 cm on 24 Sep:", round(daily2[23], 3), "Sep 2014-23 mean that day:", round(clim2[23], 3), "Sep 2014-23 p99.5:", round(p90, 3), "rain 1-24 Sep mm:", round(sum(rain[:24]), 1))
    return dict(lat=la, lon=lo, d0="2024-09-01", top=sc(daily1, 3), mid=sc(daily2, 3), clim_top=sc(clim1, 3), clim_mid=sc(clim2, 3), lo=round(p10, 3), hi=round(p90, 3),
                rain=sc(rain, 1), source="Open-Meteo ERA5-Land hourly soil moisture (reanalysis), 0-7 and 7-28 cm, near Asheville; normal = same days 2014-2023")


def main():
    od = WEB_DATA / "ca-drought"; meta = json.loads((od / "meta.json").read_text())
    grid = B.Grid(BD.BOX)
    assert grid.W == meta["grid"]["W"] and grid.H == meta["grid"]["H"]
    meta["snow"], sw = snow(grid, meta["weeks"]); (od / "snow.txt").write_text(b64(sw), encoding="ascii")
    meta["rain"], rn = rain(meta["weeks"], meta["bucket"]); (od / "rain.txt").write_text(b64(rn), encoding="ascii")
    meta["reservoirs"] = reservoirs(grid, meta["weeks"])
    write_json(od / "meta.json", meta)

    of = WEB_DATA / "helene-wnc"; fm = json.loads((of / "meta.json").read_text())
    fg = B.Grid(BF.BOX)
    fm["mrms"], A, tot = mrms(fm); (of / "mrms.txt").write_text(b64(A), encoding="ascii")
    fm["slides"] = landslides(fm, fg)
    fm["soil"] = soil(fm)
    write_json(of / "meta.json", fm)
    for d in (od, of):
        print(d.name, {p.name: round(p.stat().st_size / 1e6, 2) for p in d.iterdir()})


if __name__ == "__main__":
    main()
