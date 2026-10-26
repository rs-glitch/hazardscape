"""Hurricane Helene flooding, western North Carolina, 25-29 Sep 2024 -> web/data/helene-wnc/.

Measured: USGS NWIS instantaneous values (gage height 00065, discharge 00060, 15 min) at 8 gauges; NWS flood categories
(NWPS API); the USGS annual-peak lists for record context. Rivers: US Census TIGERweb linear hydrography.
Modelled (illustrative only): HAND (to the named rivers, not creeks) = height of each cell above the nearest river cell (from the DEM), compared in the browser
with each gauge's rise above its own pre-storm stage, within 15 km of that gauge. It is not a flood map.
"""
import math
from datetime import datetime, timedelta, timezone

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

import build_fire as B
import fetch as F
from common import WEB_DATA, fetch, fetch_json, merc_to_lonlat, write_json

BOX = (-83.05, 35.2, -82.05, 36.0)
EDT = timezone(timedelta(hours=-4))
T0 = datetime(2024, 9, 25, tzinfo=EDT)
HOURS, STEP_MIN = 120, 15
NWIS = "https://waterservices.usgs.gov/nwis/iv/"
NWPS = "https://api.water.noaa.gov/nwps/v1/gauges/"
PEAK = "https://nwis.waterdata.usgs.gov/nwis/peak"
GAUGES = ["03451500", "03451000", "03447687", "03443000", "03456991", "03454500", "03463300", "03453000"]
R_NEAR, R_FAR = 10.0, 15.0     # km: full effect inside R_NEAR, fading to zero at R_FAR (the app uses the same numbers)
FT = 0.3048
LABELS = {"03451500": "French Broad at Asheville", "03451000": "Swannanoa at Biltmore", "03447687": "French Broad near Fletcher", "03443000": "French Broad at Blantyre",
          "03456991": "Pigeon near Canton", "03454500": "French Broad at Hot Springs", "03463300": "South Toe near Celo", "03453000": "Ivy near Marshall"}


def series(ts, t_grid):
    pts = [(datetime.fromisoformat(v["dateTime"]).timestamp(), float(v["value"]), v["qualifiers"])
           for b in ts["values"] for v in b["value"] if v["value"] not in ("", "-999999")]
    pts.sort()
    t = np.array([p[0] for p in pts]); y = np.array([p[1] for p in pts])
    if not len(t):
        return [None] * len(t_grid), 0.0, pts
    out = np.interp(t_grid, t, y)
    gap = np.array([np.abs(t - g).min() for g in t_grid])
    out = np.where(gap <= 45 * 60, out, np.nan)
    est = sum(1 for p in pts if "e" in p[2]) / len(pts)
    return out, est, pts


if __name__ == "__main__":
    grid = B.Grid(BOX)
    ground = grid.cell * grid.k
    sample_dem, z = B.dem_sampler(grid, ground / 2)
    MW, MH = int(round(grid.W / B.GRID_LONG * B.MESH_LONG)) + 1, int(round(grid.H / B.GRID_LONG * B.MESH_LONG)) + 1
    dem_mesh = sample_dem(MW, MH, edges=True)
    TW, TH = grid.W * 4, grid.H * 4
    dem_tex = sample_dem(TW, TH)
    cls, layer = B.nlcd_classes(grid, dict(id="helene-wnc", year=2024), TW, TH)
    pal = np.zeros((256, 3), np.float32)
    for c, v in B.PALETTE.items():
        pal[c] = [(v >> 16) & 255, (v >> 8) & 255, v & 255]
    rgb = ndi.gaussian_filter(pal[cls], sigma=(0.9, 0.9, 0)) * (0.5 + 0.62 * B.hillshade(dem_tex, ground * B.GRID_LONG / B.TEX_LONG))[..., None]
    tex = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    near = np.ones((grid.H, grid.W), bool)
    n_roads, places, _, _ = B.context_layers(grid, dict(id="helene-wnc"), "2024-09-24", 999, near, tex)
    places = [p for p in places if p["kind"] == "city" or (p.get("pop") or 0) > 3000]
    print("grid", grid.W, "x", grid.H, "ground m", round(ground, 1), "roads", n_roads, "places", len(places))

    # --- rivers (Census TIGERweb linear hydrography) ---
    lon0, lat0 = merc_to_lonlat(grid.x0, grid.y0); lon1, lat1 = merc_to_lonlat(grid.x1, grid.y1)
    hyd = F.tiger("Hydro", 0, (lon0, lat0, lon1, lat1), "hydro_wnc", "BASENAME,NAME,MTFCC", offset=0.0003)
    rivers, creeks = [], []
    for f in hyd:
        nm = f["properties"].get("NAME") or ""
        g = f.get("geometry") or {}
        lines = g.get("coordinates", []) if g.get("type") == "MultiLineString" else [g.get("coordinates", [])]
        if " Riv" in " " + nm or nm.endswith("Riv"):
            rivers += [l for l in lines if len(l) > 1]
        elif nm.endswith("Crk"):
            creeks += [l for l in lines if len(l) > 1]
    print("TIGER linear water features", len(hyd), "-> named rivers", len(rivers), "named creeks", len(creeks))

    # --- HAND on a 2x grid ---
    S = 2
    HW, HH = grid.W * S, grid.H * S
    sample_hi, zh = B.dem_sampler(grid, 30)
    dem_hi = ndi.gaussian_filter(sample_hi(HW, HH), 0.7)
    mimg = Image.new("L", (HW, HH), 0)
    dr = ImageDraw.Draw(mimg)
    for ln in rivers:
        dr.line([grid.px(lo, la, S) for lo, la in ln], fill=255, width=1)
    mask = np.array(mimg) > 0
    bed = np.where(mask, ndi.minimum_filter(dem_hi, 5), 0)
    dist, idx = ndi.distance_transform_edt(~mask, return_indices=True)
    raw_h = dem_hi - bed[idx[0], idx[1]]
    hand = np.where(raw_h < -2.0, 63.75, np.maximum(0, raw_h))      # far below the nearest river bed: a different drainage, not flooded by it
    cellm = ground / S
    print("DEM zoom (mesh/hand)", z, zh, "river cells", int(mask.sum()), "HAND median m", round(float(np.median(hand)), 1),
          "share < 3 m", round(float((hand < 3).mean()), 3))

    # --- gauges ---
    t_grid = np.array([(T0 + timedelta(minutes=STEP_MIN * i)).timestamp() for i in range((HOURS * 60) // STEP_MIN + 1)])
    d = fetch_json(NWIS, source="usgs_nwis", name="helene_iv_8gauges", params=dict(
        format="json", sites=",".join(GAUGES), parameterCd="00060,00065",
        startDT="2024-09-24T00:00-04:00", endDT="2024-09-30T00:00-04:00"), timeout=300)
    by = {}
    for ts in d["value"]["timeSeries"]:
        s = ts["sourceInfo"]["siteCode"][0]["value"]
        by.setdefault(s, dict(name=ts["sourceInfo"]["siteName"], geo=ts["sourceInfo"]["geoLocation"]["geogLocation"]))
        by[s][ts["variable"]["variableCode"][0]["value"]] = ts
    gl = []
    for s in GAUGES:
        g = by[s]
        stage, est_h, raw_h = series(g["00065"], t_grid)
        q, est_q, raw_q = series(g["00060"], t_grid)
        t_raw = np.array([p[0] for p in raw_h]); y_raw = np.array([p[1] for p in raw_h])
        base = float(np.median(y_raw[(t_raw >= t_grid[0]) & (t_raw <= t_grid[0] + 12 * 3600)]))
        pk = int(np.nanargmax(stage)); pq = int(np.nanargmax(q))
        i_peak_raw = int(np.argmax(y_raw))
        nw = fetch_json(NWPS + s, source="noaa_nwps", name=f"nwps_{s}")
        cats = {k: v["stage"] for k, v in nw["flood"]["categories"].items()}
        rdb = fetch(PEAK, source="usgs_nwis", name=f"peak_{s}", ext="rdb", params=dict(site_no=s, agency_cd="USGS", format="rdb")).read_text().splitlines()
        rows = [l.split("\t") for l in rdb if not l.startswith("#")][2:]
        old = [(r[2], float(r[4]), float(r[6])) for r in rows if len(r) > 6 and r[4] and r[6] and r[2] < "2024-09-24"]
        prev_q = max(old, key=lambda r: r[1]); prev_h = max(old, key=lambda r: r[2])
        qmax = float(max(p[1] for p in raw_q)); hmax = float(y_raw.max())
        x, y = grid.px(g["geo"]["longitude"], g["geo"]["latitude"])
        gl.append(dict(site=s, label=LABELS[s], name=g["name"].title().replace(", Nc", ", NC").replace(" Nr ", " near ").replace(" At ", " at ").replace(" Ab ", " above "),
                       lid=nw["lid"], lat=g["geo"]["latitude"], lon=g["geo"]["longitude"], x=round(x, 1), y=round(y, 1),
                       base_ft=round(base, 2), cats=cats,
                       stage=[None if np.isnan(v) else round(float(v), 2) for v in stage],
                       q=[None if np.isnan(v) else int(round(float(v))) for v in q],
                       peak_ft=round(hmax, 2), peak_cfs=int(round(qmax)),
                       peak_time=datetime.fromtimestamp(t_raw[i_peak_raw], EDT).isoformat(timespec="minutes"),
                       est_share=round(est_q, 3), last_valid=datetime.fromtimestamp(t_raw[-1], EDT).isoformat(timespec="minutes"),
                       prev=dict(q=prev_q[1], q_date=prev_q[0], h=prev_h[2], h_date=prev_h[0],
                                 beats_q=qmax > prev_q[1], beats_h=hmax > prev_h[2]),
                       nwps_note="NWS flood categories: " + nw["name"]))
        print(s, g["name"][:34], "base", round(base, 2), "peak", hmax, "ft", int(qmax), "cfs", gl[-1]["peak_time"][5:16],
              "cats", cats, "prev", prev_q[:2], prev_h[::2], "est", round(est_q, 2), "valid pts", int((~np.isnan(stage)).sum()))

    # --- the HAND model: exactly the rule in the app's shader (wet where smoothstep(0, .25, rise - HAND) * weight > 0.5), for the area chart ---
    gx = np.array([grid.px(g["lon"], g["lat"], S) for g in gl])        # gauge positions in HAND pixels
    yy, xx = np.mgrid[0:HH, 0:HW]
    dkm = np.stack([np.hypot(xx - px, yy - py) * cellm / 1000 for px, py in gx])        # (8, HH, HW)
    wgt = 1 - np.clip((dkm - R_NEAR) / (R_FAR - R_NEAR), 0, 1)
    wgt = wgt * wgt * (3 - 2 * wgt)
    clsH = np.array(Image.fromarray(cls).resize((HW, HH), Image.NEAREST))
    dev = np.isin(clsH, (21, 22, 23, 24))
    cell_km2 = (cellm / 1000) ** 2
    area, area_dev = [], []
    for h in range(HOURS + 1):
        i = h * 60 // STEP_MIN
        wet = np.zeros((HH, HW), bool)
        for k, g in enumerate(gl):
            st = g["stage"][i]
            if st is None:      # no reading: carry the last one
                st = next((v for v in reversed(g["stage"][:i + 1]) if v is not None), g["base_ft"])
            rise = max(0.0, st - g["base_ft"]) * FT
            sm = np.clip((rise - hand) / 0.25, 0, 1); wet |= (sm * sm * (3 - 2 * sm) * wgt[k]) > 0.5
        area.append(round(float(wet.sum() * cell_km2), 2)); area_dev.append(round(float((wet & dev).sum() * cell_km2), 2))
    print("modelled flooded area km2 (illustrative): max", max(area), "of which developed", max(area_dev), "reach-area within 15 km of a gauge",
          round(float(((wgt > 0.5).any(axis=0)).sum() * cell_km2), 0))

    out = WEB_DATA / "helene-wnc"
    out.mkdir(parents=True, exist_ok=True)
    tex.save(out / "tex.webp", quality=82, method=6)
    B.save_b64(np.round(dem_mesh).astype(np.int16), out / "dem.txt")
    Image.fromarray(np.clip(np.round(hand / 0.25), 0, 255).astype(np.uint8), "L").save(out / "hand.png", optimize=True)
    def lines_px(ls):
        return [[round(v, 1) for p in (grid.px(lo, la) for lo, la in ln) for v in p] for ln in ls]
    meta = dict(id="helene-wnc", kind="flood", name="Helene floods, western NC", year=2024,
                t0=T0.isoformat(), hours=HOURS, step_min=STEP_MIN,
                note=f"Rain from Hurricane Helene sent western North Carolina rivers to their peaks on 27 September 2024 (28 September at Blantyre). At {sum(g['prev']['beats_q'] for g in gl)} of these {len(gl)} gauges the peak flow was the highest in the USGS annual-peak list for the gauge.",
                grid=dict(W=grid.W, H=grid.H, cell_ground_m=round(ground, 2), lat0=grid.lat0, bbox_ll=[lon0, lat0, lon1, lat1]),
                mesh=dict(W=MW, H=MH, zmin=int(dem_mesh.min()), zmax=int(dem_mesh.max()), terrarium_z=z),
                tex=dict(W=TW, H=TH, nlcd=layer), hand=dict(W=HW, H=HH, step_m=0.25, dem_zoom=zh, river_cells=int(mask.sum())),
                near_km=R_NEAR, far_km=R_FAR, gauges=gl, rivers=lines_px(rivers), creeks=lines_px(creeks),
                flooded=dict(area_km2=area, developed_km2=area_dev), places=places)
    write_json(out / "meta.json", meta)
    print("meta kB", round((out / "meta.json").stat().st_size / 1024), "hand.png kB", round((out / "hand.png").stat().st_size / 1024))
