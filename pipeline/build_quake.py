"""Ridgecrest 2019 earthquake sequence -> web/data/ridgecrest/.

Terrain, vegetation, roads and towns reuse build_fire. Shaking: USGS ShakeMap MMI grids for the M6.4 and M7.1,
coloured with the USGS intensity palette. Aftershocks: USGS ComCat, M>=2, 4-20 July 2019, with depth.
"""
import json
import math
from datetime import datetime, timezone

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

import build_fire as B
import fetch as F
from common import WEB_DATA, fetch_json, merc_to_lonlat, write_json

EVENTS = [("ci38443183", "M6.4 foreshock"), ("ci38457511", "M7.1 mainshock")]
BOX = (-118.25, 35.25, -116.95, 36.25)
CAT = "https://earthquake.usgs.gov/fdsnws/event/1/query"
QFAULTS = "https://earthquake.usgs.gov/arcgis/rest/services/haz/Qfaults/MapServer/21/query"
T0 = datetime(2019, 7, 4, tzinfo=timezone.utc)
# USGS ShakeMap MMI colours (I..X)
MMI_RGB = {1: (255, 255, 255), 2: (191, 204, 255), 3: (160, 230, 255), 4: (128, 255, 255), 5: (122, 255, 147),
           6: (255, 255, 0), 7: (255, 200, 0), 8: (255, 145, 0), 9: (255, 0, 0), 10: (200, 0, 0)}


def mmi_grid(eid):
    det = fetch_json(CAT, source="usgs_quakes", name=f"detail_{eid}", params=dict(eventid=eid, format="geojson"))
    sm = det["properties"]["products"]["shakemap"][0]
    url = sm["contents"]["download/coverage_mmi_medium_res.covjson"]["url"]
    cov = fetch_json(url, source="usgs_shakemap", name=f"mmi_medium_{eid}")
    ax = cov["domain"]["axes"]
    xs = np.linspace(ax["x"]["start"], ax["x"]["stop"], ax["x"]["num"])
    ys = np.linspace(ax["y"]["start"], ax["y"]["stop"], ax["y"]["num"])
    v = np.array(cov["ranges"]["MMI"]["values"], dtype=float).reshape(len(ys), len(xs))
    lon, lat, dep = det["geometry"]["coordinates"]
    p = det["properties"]
    return dict(xs=xs, ys=ys, v=v, lon=lon, lat=lat, depth=dep, mag=p["mag"],
                t=datetime.fromtimestamp(p["time"] / 1000, timezone.utc), title=p["title"], url=p["url"])


def sample(grid, ev, W, H):
    """MMI on our Mercator grid (bilinear in lon/lat)."""
    xs = grid.x0 + (np.arange(W) + 0.5) * (grid.x1 - grid.x0) / W
    ys = grid.y1 - (np.arange(H) + 0.5) * (grid.y1 - grid.y0) / H
    lon = np.array([merc_to_lonlat(x, 0)[0] for x in xs]); lat = np.array([merc_to_lonlat(0, y)[1] for y in ys])
    LON, LAT = np.meshgrid(lon, lat)
    fx = (LON - ev["xs"][0]) / (ev["xs"][1] - ev["xs"][0]); fy = (LAT - ev["ys"][0]) / (ev["ys"][1] - ev["ys"][0])
    return ndi.map_coordinates(np.nan_to_num(ev["v"], nan=1.0), [fy, fx], order=1, mode="nearest")


def mmi_rgba(m):
    out = np.zeros(m.shape + (4,), np.uint8)
    lo = np.clip(np.floor(m), 1, 10).astype(int); hi = np.clip(lo + 1, 1, 10); f = np.clip(m - lo, 0, 1)[..., None]
    pal = np.zeros((11, 3)); [pal.__setitem__(k, v) for k, v in MMI_RGB.items()]
    out[..., :3] = (pal[lo] * (1 - f) + pal[hi] * f).astype(np.uint8)
    out[..., 3] = (np.clip((m - 2.5) / 2.0, 0, 1) * 255).astype(np.uint8)       # weak shaking stays clear
    return out


if __name__ == "__main__":
    f = dict(id="ridgecrest", name="Ridgecrest earthquakes", year=2019, start="2019-07-04")
    grid = B.Grid(BOX)
    ground = grid.cell * grid.k
    sample_dem, z = B.dem_sampler(grid, ground / 2)
    MW, MH = int(round(grid.W / B.GRID_LONG * B.MESH_LONG)) + 1, int(round(grid.H / B.GRID_LONG * B.MESH_LONG)) + 1
    dem_mesh = sample_dem(MW, MH, edges=True)
    TW, TH = grid.W * 4, grid.H * 4
    dem_tex = sample_dem(TW, TH)
    cls, layer = B.nlcd_classes(grid, dict(id="ridgecrest", year=2019), TW, TH)
    pal = np.zeros((256, 3), np.float32)
    for c, v in B.PALETTE.items():
        pal[c] = [(v >> 16) & 255, (v >> 8) & 255, v & 255]
    rgb = ndi.gaussian_filter(pal[cls], sigma=(0.9, 0.9, 0))
    shade = B.hillshade(dem_tex, ground * B.GRID_LONG / B.TEX_LONG)
    rgb *= (0.5 + 0.62 * shade)[..., None]
    tex = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    near = np.ones((grid.H, grid.W), bool)
    n_roads, places, _, _ = B.context_layers(grid, dict(id="ridgecrest"), "2019-07-03", 999, near, tex)

    out = WEB_DATA / "ridgecrest"
    out.mkdir(parents=True, exist_ok=True)
    tex.save(out / "tex.webp", quality=82, method=6)
    B.save_b64(np.round(dem_mesh).astype(np.int16), out / "dem.txt")

    shocks = []
    for eid, label in EVENTS:
        ev = mmi_grid(eid)
        m = sample(grid, ev, grid.W, grid.H)
        Image.fromarray(mmi_rgba(m)).save(out / f"mmi_{eid}.webp", quality=88, method=6)
        x, y = grid.px(ev["lon"], ev["lat"])
        shocks.append(dict(id=eid, label=label, mag=ev["mag"], depth=ev["depth"], x=round(x, 2), y=round(y, 2),
                           h=round((ev["t"] - T0).total_seconds() / 3600, 3), mmi_max=round(float(np.nanmax(m)), 1),
                           mmi="mmi_" + eid + ".webp", url=ev["url"]))
        print(label, ev["mag"], ev["t"], "max MMI on grid", round(float(np.nanmax(m)), 1))

    cat = fetch_json(CAT, source="usgs_quakes", name="ridgecrest_m2_jul4_20", params=dict(
        format="geojson", starttime="2019-07-04", endtime="2019-07-20", minlatitude=BOX[1], maxlatitude=BOX[3],
        minlongitude=BOX[0], maxlongitude=BOX[2], minmagnitude=2, orderby="time-asc"), timeout=300)
    q = []
    for e in cat["features"]:
        lon, lat, dep = e["geometry"]["coordinates"]
        x, y = grid.px(lon, lat)
        if 0 <= x < grid.W and 0 <= y < grid.H:
            q.append([round((e["properties"]["time"] / 1000 - T0.timestamp()) / 3600, 4), round(x, 1), round(y, 1),
                      round(max(0.0, dep), 2), e["properties"]["mag"]])
    feats, off = [], 0
    while True:   # the service caps pages at 2000 features
        page = fetch_json(QFAULTS, source="usgs_qfaults", name=f"ridgecrest_box_{off}", params=dict(
            where="1=1", geometry=",".join(map(str, BOX)), geometryType="esriGeometryEnvelope", inSR=4326, outSR=4326,
            outFields="fault_name,slip_sense", f="geojson", resultOffset=off, resultRecordCount=2000))
        feats += page.get("features", [])
        if not page.get("properties", {}).get("exceededTransferLimit") and len(page.get("features", [])) < 2000:
            break
        off += 2000
    lines = []
    for fe in feats:
        g = fe["geometry"] or {}
        for ln in (g.get("coordinates", []) if g.get("type") == "MultiLineString" else [g.get("coordinates", [])]):
            pts = [(min(grid.W, max(0, x)), min(grid.H, max(0, y))) for x, y in (grid.px(lo, la) for lo, la, *_ in ln)]   # clip to the block
            if len(pts) > 1:
                lines.append([round(v, 1) for p in pts for v in p])
    hours = 16 * 24
    steps = []
    for h in range(6, hours + 1, 6):
        sel = [e for e in q if h - 6 < e[0] <= h]
        steps.append(dict(h=h, n=len(sel), m4=sum(1 for e in sel if e[4] >= 4), cum=sum(1 for e in q if e[0] <= h),
                          maxmag=max((e[4] for e in sel), default=0)))
    meta = dict(id="ridgecrest", kind="quake", name="Ridgecrest earthquakes", year=2019, t0=T0.isoformat(),
                note="A magnitude 6.4 quake on 4 July 2019 was followed 34 hours later by a magnitude 7.1, the largest in California in 20 years.",
                grid=dict(W=grid.W, H=grid.H, cell_ground_m=round(ground, 2), lat0=grid.lat0,
                          bbox_ll=[*merc_to_lonlat(grid.x0, grid.y0), *merc_to_lonlat(grid.x1, grid.y1)]),
                mesh=dict(W=MW, H=MH, zmin=int(dem_mesh.min()), zmax=int(dem_mesh.max()), terrarium_z=z),
                tex=dict(W=TW, H=TH, nlcd=layer), shocks=shocks, quakes=q, faults=lines, steps=steps,
                places=places, hours=hours, wave_kms=3.5)
    write_json(out / "meta.json", meta)
    print(len(q), "quakes,", len(lines), "fault lines,", len(places), "places; M>=4:", sum(1 for e in q if e[4] >= 4))
