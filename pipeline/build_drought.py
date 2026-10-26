"""California drought 2020-2023 -> web/data/ca-drought/.

US Drought Monitor weekly county statistics (cumulative % area in D0..D4) -> DSCI per county per week
(DSCI = D0+D1+D2+D3+D4, 0-500, the USDM's own index). Reservoir storage: USGS NWIS daily values (00054).
"""
from datetime import date, datetime, timedelta

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

import build_fire as B
import fetch as F
from common import WEB_DATA, fetch_json, merc_to_lonlat, write_json

BOX = (-124.6, 32.4, -114.0, 42.1)
USDM = "https://usdmdataservices.unl.edu/api"
NWIS = "https://waterservices.usgs.gov/nwis/dv/"
RES = [("11370000", "Shasta Lake"), ("11406800", "Lake Oroville")]
D0, D1 = date(2020, 1, 1), date(2023, 12, 31)


def usdm(path, aoi, name):
    return fetch_json(f"{USDM}/{path}", source="usdm", name=name, headers={"Accept": "application/json"},
                      params=dict(aoi=aoi, startdate="1/1/2020", enddate="12/31/2023", statisticsType=1))


if __name__ == "__main__":
    grid = B.Grid(BOX)
    ground = grid.cell * grid.k
    sample_dem, z = B.dem_sampler(grid, ground / 2)
    MW, MH = int(round(grid.W / B.GRID_LONG * B.MESH_LONG)) + 1, int(round(grid.H / B.GRID_LONG * B.MESH_LONG)) + 1
    dem_mesh = sample_dem(MW, MH, edges=True)
    TW, TH = grid.W * 4, grid.H * 4
    dem_tex = sample_dem(TW, TH)
    cls, layer = B.nlcd_classes(grid, dict(id="ca-drought", year=2021), TW, TH)
    pal = np.zeros((256, 3), np.float32)
    for c, v in B.PALETTE.items():
        pal[c] = [(v >> 16) & 255, (v >> 8) & 255, v & 255]
    rgb = ndi.gaussian_filter(pal[cls], sigma=(0.9, 0.9, 0)) * (0.5 + 0.62 * B.hillshade(dem_tex, ground * B.GRID_LONG / B.TEX_LONG))[..., None]
    tex = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))

    # counties (Census TIGERweb), rasterized to the grid
    lon0, lat0 = merc_to_lonlat(grid.x0, grid.y0); lon1, lat1 = merc_to_lonlat(grid.x1, grid.y1)
    cfeat = F.tiger("State_County", 1, (lon0, lat0, lon1, lat1), "counties_ca", "STATE,COUNTY,NAME", offset=0.005)
    cfeat = [c for c in cfeat if c["properties"]["STATE"] == "06"]
    cfeat.sort(key=lambda c: c["properties"]["COUNTY"])
    cid = np.zeros((grid.H, grid.W), np.uint8)
    for i, c in enumerate(cfeat):
        cid[B.rasterize(grid, [c["geometry"]])] = i + 1
    names = [c["properties"]["NAME"] for c in cfeat]
    print(len(cfeat), "counties; land cells with a county", round(float((cid > 0).mean()), 3))

    # USDM weekly per county -> DSCI
    weeks = None
    dsci = np.zeros((len(cfeat), 209), np.uint16)
    for i, c in enumerate(cfeat):
        fips = "06" + c["properties"]["COUNTY"]
        rows = sorted(usdm("CountyStatistics/GetDroughtSeverityStatisticsByAreaPercent", fips, f"county_{fips}"), key=lambda r: r["mapDate"])
        if weeks is None:
            weeks = [r["mapDate"][:10] for r in rows]
        assert [r["mapDate"][:10] for r in rows] == weeks and len(rows) == 209, f"incomplete USDM record for {fips}"
        for k, r in enumerate(rows[:209]):
            dsci[i, k] = round(r["d0"] + r["d1"] + r["d2"] + r["d3"] + r["d4"])
    state = sorted(usdm("StateStatistics/GetDroughtSeverityStatisticsByAreaPercent", "06", "state_06"), key=lambda r: r["mapDate"])
    stats = [dict(d=r["mapDate"][:10], d0=r["d0"], d1=r["d1"], d2=r["d2"], d3=r["d3"], d4=r["d4"]) for r in state]

    # reservoirs: daily storage, sampled weekly on the USDM dates
    res = []
    for site, label in RES:
        d = fetch_json(NWIS, source="usgs_nwis", name=f"storage_{site}", params=dict(
            format="json", sites=site, parameterCd="00054", startDT=D0.isoformat(), endDT=D1.isoformat()))
        # a site's record can be split across series (Oroville: one ends Sep 2022, the next runs on); merge them all
        tss = sorted(d["value"]["timeSeries"], key=lambda ts: min((v["dateTime"] for b in ts["values"] for v in b["value"]), default=""))
        vals = {v["dateTime"][:10]: float(v["value"]) for ts in tss for blk in ts["values"] for v in blk["value"] if float(v["value"]) >= 0}
        best = tss[0]
        geo = best["sourceInfo"]["geoLocation"]["geogLocation"]
        series = []
        for w in weeks:
            day = datetime.fromisoformat(w).date()
            v = next((vals[(day - timedelta(days=k)).isoformat()] for k in range(0, 7) if (day - timedelta(days=k)).isoformat() in vals), None)   # same day or the latest before
            series.append(v)
        x, y = grid.px(geo["longitude"], geo["latitude"])
        mx = max(v for v in series if v)
        res.append(dict(site=site, name=label, x=round(x, 1), y=round(y, 1), acft=series, max_acft=mx,
                        min_acft=min(v for v in series if v)))
        print(label, "min", res[-1]["min_acft"], "max", mx)

    # roads: only highways for a whole-state block; big places only
    near = np.ones((grid.H, grid.W), bool)
    B.ROADS.pop(8, None)          # no local roads at state scale
    _, places, _, _ = B.context_layers(grid, dict(id="ca-drought"), "2019-12-31", 999, near, tex)
    places = [p for p in places if (p.get("pop") or 0) >= 150000 and cid[int(p["y"]), int(p["x"])] > 0]   # California only

    out = WEB_DATA / "ca-drought"
    out.mkdir(parents=True, exist_ok=True)
    tex.save(out / "tex.webp", quality=82, method=6)
    B.save_b64(np.round(dem_mesh).astype(np.int16), out / "dem.txt")
    B.save_b64(cid, out / "counties.txt")
    B.save_b64(dsci, out / "dsci.txt")
    t0 = datetime.fromisoformat(weeks[0])
    meta = dict(id="ca-drought", kind="drought", name="California drought", year=2021, t0=t0.isoformat() + "+00:00",
                note="State water officials called 2020–2022 California's driest three years on record. Storms from December 2022 through spring 2023 ended most of the drought.",
                grid=dict(W=grid.W, H=grid.H, cell_ground_m=round(ground, 2), lat0=grid.lat0,
                          bbox_ll=[*merc_to_lonlat(grid.x0, grid.y0), *merc_to_lonlat(grid.x1, grid.y1)]),
                mesh=dict(W=MW, H=MH, zmin=int(dem_mesh.min()), zmax=int(dem_mesh.max()), terrarium_z=z),
                tex=dict(W=TW, H=TH, nlcd=layer), weeks=weeks, counties=names, stats=stats, reservoirs=res,
                places=places, hours=(len(weeks) - 1) * 168)
    write_json(out / "meta.json", meta)
    peak = max(stats, key=lambda s: s["d4"])
    print(len(weeks), "weeks; D4 peak", peak["d"], peak["d4"], "%")
    assert len(weeks) == 209 and dsci.max() <= 500
