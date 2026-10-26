"""Hurricane Helene 2024 -> web/data/helene/.

Track and intensity: NOAA NHC HURDAT2 best track (AL092024): position, max sustained wind, central pressure,
34/50/64-kt wind radii by quadrant and radius of maximum wind (RMW), interpolated to hourly.
Rain: Open-Meteo archive (ERA5 reanalysis) hourly precipitation on a 0.5 degree grid, stored as cumulative mm.
The wind field drawn by the app is MODELLED from the best-track numbers in the browser; it is not measured wind.
"""
import math
import time
from datetime import datetime, timedelta, timezone

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.interpolate import PchipInterpolator

import build_fire as B
from common import WEB_DATA, fetch, fetch_json, merc_to_lonlat, write_json

BOX = (-89.0, 20.0, -79.0, 38.0)
T0 = datetime(2024, 9, 24, tzinfo=timezone.utc)
HOURS = 120                                   # 24 Sep 00Z -> 29 Sep 00Z
HURDAT = "https://www.nhc.noaa.gov/data/hurdat/hurdat2-1851-2024-040425.txt"
METEO = "https://archive-api.open-meteo.com/v1/archive"
KT, NMI = 0.514444, 1.852
ASHEVILLE = (35.5954, -82.5515)               # Asheville, NC (city centre)
LANDFALL = (30.0, -83.7)                      # HURDAT2 landfall record, 27 Sep 03:10 UTC


def parse_hurdat(sid="AL092024"):
    lines = fetch(HURDAT, source="noaa_hurdat2", name="hurdat2_1851_2024", ext="txt", timeout=300).read_text().splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith(sid))
    n = int(lines[i].split(",")[2])
    rows = []
    for l in lines[i + 1:i + 1 + n]:
        f = [s.strip() for s in l.split(",")]
        t = datetime.strptime(f[0] + f[1], "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
        lat = float(f[4][:-1]) * (1 if f[4][-1] == "N" else -1)
        lon = float(f[5][:-1]) * (1 if f[5][-1] == "E" else -1)
        v = [float(x) for x in f[6:]]
        rows.append(dict(t=t, ident=f[2], status=f[3], lat=lat, lon=lon, vmax=v[0], pmin=v[1], radii=v[2:14], rmw=v[14]))
    return rows


def saffir(v):
    return 0 if v < 34 else 1 if v < 64 else 2 if v < 83 else 3 if v < 96 else 4 if v < 113 else 5 if v < 137 else 6   # 0 TD, 1 TS, 2..6 = Cat 1..5


def hourly(rows, grid):
    th = np.array([(r["t"] - T0).total_seconds() / 3600 for r in rows])
    lat = PchipInterpolator(th, [r["lat"] for r in rows]); lon = PchipInterpolator(th, [r["lon"] for r in rows])
    lin = lambda ys: (lambda h: np.interp(h, th, ys))
    vmax, pmin = lin([r["vmax"] for r in rows]), lin([r["pmin"] for r in rows])
    rmw = lin([r["rmw"] for r in rows])
    rad = [lin([r["radii"][k] for r in rows]) for k in range(12)]
    out = {k: [] for k in ("x", "y", "lat", "lon", "u", "v", "vmax", "pmin", "rmw", "r34", "r50", "r64", "cat", "status", "on")}
    for h in range(HOURS + 1):
        on = th[0] <= h <= th[-1]
        hh = min(max(h, th[0]), th[-1])
        la, lo = float(lat(hh)), float(lon(hh))
        la2, lo2 = float(lat(min(hh + 0.5, th[-1]))), float(lon(min(hh + 0.5, th[-1])))
        la1, lo1 = float(lat(max(hh - 0.5, th[0]))), float(lon(max(hh - 0.5, th[0])))
        dt = (min(hh + 0.5, th[-1]) - max(hh - 0.5, th[0])) or 1
        east = (lo2 - lo1) * 111.32 * math.cos(math.radians(la)) / dt            # ground km/h
        north = (la2 - la1) * 110.57 / dt
        sc = grid.k / math.cos(math.radians(la))                                 # ground km -> scene km (see app)
        x, y = grid.px(lo, la)
        out["lat"].append(round(la, 2)); out["lon"].append(round(lo, 2)); out["x"].append(round(x, 2)); out["y"].append(round(y, 2))
        out["u"].append(round(east * sc, 2)); out["v"].append(round(north * sc, 2))
        vm = float(vmax(hh)); out["vmax"].append(round(vm, 1)); out["pmin"].append(round(float(pmin(hh)), 1))
        out["rmw"].append(round(float(rmw(hh)) * NMI * sc, 1))
        for key, o in (("r34", 0), ("r50", 4), ("r64", 8)):
            out[key].append([round(float(rad[o + q](hh)) * NMI * sc, 1) for q in range(4)])
        out["cat"].append(saffir(vm)); out["on"].append(int(on))
        idx = int(np.searchsorted(th, hh, side="right")) - 1
        out["status"].append(rows[max(0, min(idx, len(rows) - 1))]["status"])
    return out


def rain_grid():
    """ERA5 hourly precipitation (mm) at every 0.5 degree point of BOX, 24-29 Sep 2024 UTC."""
    lons = np.arange(BOX[0], BOX[2] + 1e-6, 0.5); lats = np.arange(BOX[1], BOX[3] + 1e-6, 0.5)
    pts = [(la, lo) for la in lats for lo in lons]
    cube = np.zeros((144, len(lats), len(lons)), np.float32)
    for b in range(0, len(pts), 50):
        chunk = pts[b:b + 50]
        d = fetch_json(METEO, source="open_meteo", name=f"helene_rain_{b:04d}", params=dict(
            latitude=",".join(f"{p[0]:.2f}" for p in chunk), longitude=",".join(f"{p[1]:.2f}" for p in chunk),
            start_date="2024-09-24", end_date="2024-09-29", hourly="precipitation", timezone="UTC", models="era5"), timeout=120)
        d = d if isinstance(d, list) else [d]
        assert len(d) == len(chunk), "open-meteo answered with a different point count"
        for k, rec in enumerate(d):
            la, lo = chunk[k]; j = round((la - BOX[1]) / 0.5); i = round((lo - BOX[0]) / 0.5)
            cube[:, j, i] = np.nan_to_num(np.array(rec["hourly"]["precipitation"], np.float32), nan=0.0)
        time.sleep(1.5)
    return lons, lats, cube


def point_rain(lat, lon, name):
    d = fetch_json(METEO, source="open_meteo", name=name, params=dict(
        latitude=lat, longitude=lon, start_date="2024-09-24", end_date="2024-09-29", hourly="precipitation", timezone="UTC", models="era5"))
    d = d[0] if isinstance(d, list) else d
    h = np.nan_to_num(np.array(d["hourly"]["precipitation"], np.float32), nan=0.0)
    cum = np.concatenate([[0.0], np.cumsum(h[1:])])[:HOURS + 1]       # value at hour i = rain in the hour before i
    return dict(lat=d["latitude"], lon=d["longitude"], elev=d.get("elevation"), cum=[round(float(v), 1) for v in cum],
                hourly=[round(float(v), 1) for v in h[1:HOURS + 1]])


def nlcd_cls(grid, TW, TH, dem_tex):
    """NLCD classes; outside the US (Cuba, Yucatan, open Gulf) there is no NLCD, so use the DEM: sea level = water, else shrub."""
    layer = "NLCD_2021_Land_Cover_L48"
    p = B.F.nlcd_png(layer, grid.bbox3857(), TW, TH, f"helene_{TW}x{TH}_{layer}")
    a = np.array(Image.open(p).convert("RGB"), np.int32)
    rgb = (a[..., 0] << 16) | (a[..., 1] << 8) | a[..., 2]
    cls = np.zeros(rgb.shape, np.uint8)
    for kk, vv in B.NLCD_WMS.items():
        cls[rgb == kk] = vv
    unk = cls == 0
    dist, idx = ndi.distance_transform_edt(unk, return_distances=True, return_indices=True)
    near = unk & (dist <= 3)
    cls[near] = cls[idx[0][near], idx[1][near]]
    far = cls == 0
    cls[far & (dem_tex <= 1.0)] = 11
    cls[far & (dem_tex > 1.0)] = 52
    return cls, layer, float(far.mean())


if __name__ == "__main__":
    grid = B.Grid(BOX)
    ground = grid.cell * grid.k
    sample_dem, z = B.dem_sampler(grid, ground / 2)
    MW, MH = int(round(grid.W / B.GRID_LONG * B.MESH_LONG)) + 1, int(round(grid.H / B.GRID_LONG * B.MESH_LONG)) + 1
    dem_mesh = sample_dem(MW, MH, edges=True)
    TW, TH = grid.W * 4, grid.H * 4
    dem_tex = sample_dem(TW, TH)
    cls, layer, far = nlcd_cls(grid, TW, TH, dem_tex)
    print("grid", grid.W, "x", grid.H, "cell ground km", round(ground / 1000, 2), "dem zoom", z, "no-NLCD share", round(far, 3))
    pal = np.zeros((256, 3), np.float32)
    for c, v in B.PALETTE.items():
        pal[c] = [(v >> 16) & 255, (v >> 8) & 255, v & 255]
    rgb = ndi.gaussian_filter(pal[cls], sigma=(0.9, 0.9, 0)) * (0.5 + 0.62 * B.hillshade(dem_tex, ground * B.GRID_LONG / B.TEX_LONG))[..., None]
    tex = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    B.ROADS.pop(8, None); B.ROADS.pop(6, None)             # primary highways only at this scale
    near = np.ones((grid.H, grid.W), bool)
    n_roads, places, _, _ = B.context_layers(grid, dict(id="helene"), "2024-09-23", 999, near, tex)
    def clean(n):
        return n.split(" metropolitan")[0].split("-Richmond")[0].split("-Davidson")[0]
    px_l, py_l = grid.px(LANDFALL[1], LANDFALL[0])
    best = {}
    for p in places:
        if p["kind"] != "city":
            continue
        p["name"] = clean(p["name"])
        ok = (p.get("pop") or 0) >= 250000 or p["name"] in ("Asheville", "Tallahassee")
        if p["name"] == "Perry":                      # Perry, FL is the town nearest the HURDAT2 landfall point
            ok = math.hypot(p["x"] - px_l, p["y"] - py_l) < 6
        if ok and (p["name"] not in best or (p.get("pop") or 0) > (best[p["name"]].get("pop") or 0)):
            best[p["name"]] = p
    places = list(best.values())
    print("primary roads", n_roads, "places kept", [p["name"] for p in places])

    rows = parse_hurdat()
    trk = hourly(rows, grid)
    print("HURDAT2 AL092024 rows", len(rows), "peak vmax", max(r["vmax"] for r in rows), "min pressure", min(r["pmin"] for r in rows))

    lons, lats, cube = rain_grid()
    cum = np.concatenate([np.zeros((1,) + cube.shape[1:], np.float32), np.cumsum(cube[1:HOURS + 1], axis=0)])   # hour i = rain in hours 1..i
    print("rain cube", cum.shape, "max cumulative mm at 0.5 deg", round(float(cum[-1].max()), 1))
    pa = point_rain(*ASHEVILLE, "helene_pt_asheville"); pl = point_rain(*LANDFALL, "helene_pt_landfall")
    print("ERA5 6-day-window rain: Asheville cell", pa["lat"], pa["lon"], pa["cum"][-1], "mm; landfall cell", pl["lat"], pl["lon"], pl["cum"][-1], "mm")

    out = WEB_DATA / "helene"
    out.mkdir(parents=True, exist_ok=True)
    tex.save(out / "tex.webp", quality=82, method=6)
    B.save_b64(np.round(dem_mesh).astype(np.int16), out / "dem.txt")
    B.save_b64(np.round(cum * 10).astype(np.uint16), out / "rain.txt")                 # 0.1 mm units, [hour][lat row from south][lon col]
    ax, ay = grid.px(*ASHEVILLE[::-1]); lx, ly = grid.px(*LANDFALL[::-1])
    lonL, latL = merc_to_lonlat(grid.x0, grid.y0); lonH, latH = merc_to_lonlat(grid.x1, grid.y1)
    meta = dict(id="helene", kind="hurricane", name="Hurricane Helene", year=2024, t0=T0.isoformat(), hours=HOURS,
                note="Helene made landfall about 10 n mi southwest of Perry, Florida, at about 11:10 PM EDT on 26 September 2024 (03:10 UTC on the 27th) as a category 4 hurricane with 120 kt (about 138 mph) winds, the strongest landfalling hurricane in the Florida Big Bend since about 1900 (NHC Tropical Cyclone Report). It then weakened quickly as it moved north through Georgia and Tennessee.",
                grid=dict(W=grid.W, H=grid.H, cell_ground_m=round(ground, 2), lat0=grid.lat0,
                          bbox_ll=[lonL, latL, lonH, latH]),
                mesh=dict(W=MW, H=MH, zmin=int(dem_mesh.min()), zmax=int(dem_mesh.max()), terrarium_z=z),
                tex=dict(W=TW, H=TH, nlcd=layer),
                rain=dict(nx=len(lons), ny=len(lats), nt=HOURS + 1, lon0=float(lons[0]), lat0=float(lats[0]), step=0.5, scale=10,
                          lat_s=float(lats[0]), lat_n=float(lats[-1]), model="ERA5 via Open-Meteo", max_mm=round(float(cum[-1].max()), 1)),
                track=trk, places=places,
                sites=[dict(id="asheville", name="Asheville, NC", x=round(ax, 1), y=round(ay, 1), era5=pa),
                       dict(id="landfall", name="Landfall area, FL Big Bend", x=round(lx, 1), y=round(ly, 1), era5=pl)],
                best_track=[dict(t=r["t"].isoformat(), id=r["ident"], status=r["status"], lat=r["lat"], lon=r["lon"],
                                 vmax=r["vmax"], pmin=r["pmin"]) for r in rows])
    write_json(out / "meta.json", meta)
    i = int(np.argmax(trk["vmax"]))
    print("hourly peak wind", trk["vmax"][i], "kt at hour", i, "=", T0 + timedelta(hours=i))
    assert all(np.isfinite(trk["x"])) and len(trk["x"]) == HOURS + 1
