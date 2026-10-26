"""Build one fire's web bundle: terrain, vegetation texture, OSM layers, spread raster, stats.

Usage: python build_fire.py dixie [more ids...]
Outputs web/data/<id>/{meta.json, dem.bin, arrival.bin, tex.webp, hotspots.bin, buildings.bin}
"""
import base64
import json
import math
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
import shapely
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from shapely.geometry import mapping, shape

import fetch as F
from common import WEB_DATA, lonlat_to_merc, lonlat_to_tile, merc_to_lonlat, write_json, R_EARTH
from fires import FIRES

GRID_LONG = 512      # spread raster cells on the long side
MESH_LONG = 512      # terrain vertices on the long side
TEX_LONG = 2048      # vegetation texture pixels on the long side
STEP_H = 12          # time step (h); FEDS publishes 00 and 12 UTC perimeters
FEDS_SHIFT_H = 12    # FEDS `t` labels the start of its 12 h window; the perimeter is valid at its end (see validate.py lag gate)
UNBURNED = 65535

# NLCD colours exactly as rendered by the MRLC WMS -> class code
NLCD_WMS = {0x476ba0: 11, 0xd1def8: 12, 0xddc9c9: 21, 0xd89382: 22, 0xed0000: 23, 0xaa0000: 24,
            0xb2ada3: 31, 0x68aa63: 41, 0x1c6330: 42, 0xb5c98e: 43, 0xccba7c: 52, 0xe2e2c1: 71,
            0xdbd83d: 81, 0xaa7028: 82, 0xbad8ea: 90, 0x70a3ba: 95}
# Our display colours (vegetation-forward, quiet enough for the fire overlay to read on top)
PALETTE = {11: 0x5d86a8, 12: 0xe8eef2, 21: 0xc4bbb0, 22: 0xaa9d90, 23: 0x8f8378, 24: 0x6f655e,
           31: 0xb8ad9b, 41: 0x5b8a43, 42: 0x2f5d31, 43: 0x4f7a3e, 52: 0xa3a066, 71: 0xcfc690,
           81: 0xbdb96e, 82: 0xc9ad6c, 90: 0x73936d, 95: 0x86a592}
GROUPS = {"forest": (41, 42, 43), "shrub": (52,), "grass": (71,), "developed": (21, 22, 23, 24),
          "agriculture": (81, 82), "other": (11, 12, 31, 90, 95)}


def utc(s):
    return datetime.fromisoformat(s.replace("Z", "")).replace(tzinfo=timezone.utc)


def rings_of(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return geom["coordinates"]
    if geom["type"] == "GeometryCollection":
        return [r for g in geom["geometries"] for r in rings_of(g)]
    return []


class Grid:
    """A north-up Web Mercator grid over the fire's padded extent."""

    def __init__(self, bbox_ll):
        w, s, e, n = bbox_ll
        x0, y0 = lonlat_to_merc(w, s)
        x1, y1 = lonlat_to_merc(e, n)
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        span = max(x1 - x0, y1 - y0)
        self.cell = span / GRID_LONG
        self.W = int(round((x1 - x0) / self.cell))
        self.H = int(round((y1 - y0) / self.cell))
        self.x1, self.y1 = x0 + self.W * self.cell, y0 + self.H * self.cell
        self.lat0 = (s + n) / 2
        self.k = math.cos(math.radians(self.lat0))          # ground metres per mercator metre
        lats = [merc_to_lonlat(0, self.y1 - (r + 0.5) * self.cell)[1] for r in range(self.H)]
        cosr = np.cos(np.radians(lats))
        e2 = 0.00669437999014                                # WGS84: EPSG:3857 is spherical, the Earth is not
        ell = (1 - e2) / (1 - e2 * np.sin(np.radians(lats)) ** 2) ** 2
        self.cell_km2 = ((self.cell / 1000) ** 2 * cosr ** 2 * ell)[:, None] * np.ones((1, self.W))

    def px(self, lon, lat, scale=1.0):
        x, y = lonlat_to_merc(lon, lat)
        return (x - self.x0) / self.cell * scale, (self.y1 - y) / self.cell * scale

    def bbox3857(self):
        return (self.x0, self.y0, self.x1, self.y1)


def fill_rings(rings, W, H):
    """Even-odd scanline fill sampled at pixel centres: exact, no outline inflation, holes handled by parity."""
    e = np.concatenate([np.column_stack([r[:-1], r[1:]]) for r in rings if len(r) > 3])   # x1, y1, x2, y2
    ylo, yhi = np.minimum(e[:, 1], e[:, 3]), np.maximum(e[:, 1], e[:, 3])
    out = np.zeros((H, W), bool)
    for row in range(max(0, int(ylo.min())), min(H, int(np.ceil(yhi.max())) + 1)):
        yc = row + 0.5
        x1, y1, x2, y2 = e[(ylo <= yc) & (yhi > yc)].T
        xs = np.sort(x1 + (yc - y1) * (x2 - x1) / (y2 - y1))
        a = np.clip(np.ceil(xs[0::2] - 0.5), 0, W).astype(int)
        b = np.clip(np.ceil(xs[1::2] - 0.5), 0, W).astype(int)
        for i, j in zip(a, b):
            out[row, i:j] = True
    return out


def rasterize(grid, geoms, ss=2):
    """A cell counts as inside when at least half of its ss x ss sub-cell centres are inside."""
    W, H = grid.W * ss, grid.H * ss
    out = np.zeros((H, W), bool)
    for g in geoms:
        # official perimeters are often invalid (self-overlapping rings); agencies' acres match the valid geometry
        for poly in rings_of(mapping(shapely.make_valid(shape(g)))):
            rings = [np.array([grid.px(lon, lat, ss) for lon, lat, *_ in ring]) for ring in poly]
            if len(rings[0]) > 3:
                out |= fill_rings(rings, W, H)
    return out.reshape(grid.H, ss, grid.W, ss).mean(axis=(1, 3)) >= 0.5


def disk(r):
    r = max(1, int(round(r)))
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


# --- upstream pulls -------------------------------------------------------------
def official_final(f):
    y = f["year"]
    where = (f"attr_POOState='US-CA' AND UPPER(poly_IncidentName)='{f['wfigs'].upper()}' AND "
             f"attr_FireDiscoveryDateTime >= DATE '{y}-01-01' AND attr_FireDiscoveryDateTime < DATE '{y + 1}-01-01'")
    feats = F.wfigs_query("WFIGS_Interagency_Perimeters", where, f"final_{f['id']}")
    feats = [x for x in feats if x.get("geometry")]
    if not feats:
        return None
    best = max(feats, key=lambda x: x["properties"].get("poly_GISAcres") or 0)
    return best


def official_parts(f, grid, ref):
    """WFIGS final perimeters of the fire's year lying mostly (>=50 %) inside the reference footprint.

    A complex (August) is stored as several named parts; a single fire returns one part.
    """
    y, (w, s, e, n) = f["year"], f["search"]
    where = (f"attr_POOState='US-CA' AND poly_GISAcres>300 AND attr_FireDiscoveryDateTime >= DATE '{y}-01-01' "
             f"AND attr_FireDiscoveryDateTime < DATE '{y + 1}-01-01'")
    feats = F.wfigs_query("WFIGS_Interagency_Perimeters", where, f"parts_{f['id']}", extra=dict(
        geometry=f"{w},{s},{e},{n}", geometryType="esriGeometryEnvelope", inSR=4326,
        spatialRel="esriSpatialRelIntersects"))
    parts, mask = {}, np.zeros_like(ref)
    for x in feats:
        if not x.get("geometry"):
            continue
        m = rasterize(grid, [x["geometry"]])
        if m.sum() and (m & ref).sum() >= 0.5 * m.sum():
            p = x["properties"]
            parts[p["poly_IncidentName"].title()] = round(p["poly_GISAcres"])   # duplicates by name count once
            mask |= m
    return parts, mask


def calfire_acres(f):
    """Final acres published on the CAL FIRE incident list (None if the fire is not listed)."""
    key = f["calfire"].lower()
    rows = [d for d in F.calfire_incidents(f["year"]) if (d.get("Name") or "").lower().startswith(key)]
    return max((d["AcresBurned"] or 0 for d in rows), default=None)


def feds_steps(f):
    w, s, e, n = f["search"]
    feats = F.feds("eis_fire_lf_perimeter_archive", (w, s, e, n), f["start"], f["end"], f"perim_{f['id']}")
    by = {}
    for x in feats:
        by.setdefault(x["properties"]["fireid"], []).append(x)
    fid = max(by, key=lambda k: max(v["properties"]["farea"] for v in by[k]))
    steps = sorted(by[fid], key=lambda x: x["properties"]["t"])
    return fid, steps


def hotspots(f):
    rows = []
    for sat in ("viirs-snpp", "viirs-jpss1"):
        rows += F.firms_rows(sat, f["year"], f["search"], f["start"], f["end"])
    out = []
    for r in rows:
        if r["confidence"] not in ("n", "h", "nominal", "high"):
            continue
        t = datetime.strptime(r["acq_date"] + r["acq_time"].zfill(4), "%Y-%m-%d%H%M").replace(tzinfo=timezone.utc)
        out.append(dict(t=t, lat=float(r["latitude"]), lon=float(r["longitude"]), frp=float(r["frp"]),
                        scan=float(r["scan"]), track=float(r["track"]), sat=r["sat"], dn=r["daynight"]))
    return out


# --- spread reconstruction ---------------------------------------------------------
def viirs_spread(grid, hs, edges, allow):
    """Cumulative burned masks per step from VIIRS footprints (method B, our reconstruction)."""
    acc = np.zeros((grid.H, grid.W), bool)
    masks = []
    close = disk(375 * 1.0 / grid.k / grid.cell)
    for k in range(1, len(edges)):
        im = Image.new("L", (grid.W, grid.H), 0)
        d = ImageDraw.Draw(im)
        for h in hs:
            if edges[k - 1] < h["t"] <= edges[k]:
                cx, cy = grid.px(h["lon"], h["lat"])
                hx = h["scan"] * 500 / grid.k / grid.cell
                hy = h["track"] * 500 / grid.k / grid.cell
                d.rectangle([cx - hx, cy - hy, cx + hx, cy + hy], fill=1)
        acc |= np.array(im, bool)
        m = ndi.binary_fill_holes(ndi.binary_closing(acc, structure=close)) & allow
        acc |= m
        masks.append(acc.copy())
    return masks


def feds_spread(grid, steps, edges, shift_h=FEDS_SHIFT_H):
    acc = np.zeros((grid.H, grid.W), bool)
    masks, j = [], 0
    for k in range(1, len(edges)):
        while j < len(steps) and utc(steps[j]["properties"]["t"]) + timedelta(hours=shift_h) <= edges[k]:
            acc |= rasterize(grid, [steps[j]["geometry"]])
            j += 1
        masks.append(acc.copy())
    return masks


def arrival_hours(masks, edges, t0, seed):
    """Per-cell arrival time (h since t0). Within each step, interpolate by distance between perimeters."""
    arr = np.full(masks[0].shape, np.inf)
    prev = seed.copy()
    tprev = 0.0
    for k, m in enumerate(masks):
        tk = (edges[k + 1] - t0).total_seconds() / 3600
        new = m & ~prev
        if new.any():
            if prev.any():
                dp = ndi.distance_transform_edt(~prev)
                dn = ndi.distance_transform_edt(m)
                frac = dp / np.maximum(dp + dn, 1e-6)
            else:
                frac = np.ones_like(arr)
            arr[new] = tprev + frac[new] * (tk - tprev)
            tprev = tk
        elif m.any():
            tprev = tk
        prev = prev | m
    return arr


def save_b64(a, path):
    """Little-endian array bytes as base64 text: artifact hosting serves only web file types."""
    path.write_text(base64.b64encode(np.ascontiguousarray(a).tobytes()).decode("ascii"), encoding="ascii")


def iou(a, b):
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 0.0


# --- terrain, vegetation, OSM --------------------------------------------------------
def dem_sampler(grid, ground_px):
    lon0, lat0 = merc_to_lonlat(grid.x0, grid.y1)
    lon1, lat1 = merc_to_lonlat(grid.x1, grid.y0)
    z = int(min(13, max(8, math.ceil(math.log2(156543.03 * grid.k / ground_px)))))
    while True:
        tx0, ty0 = lonlat_to_tile(lon0, lat0, z)
        tx1, ty1 = lonlat_to_tile(lon1, lat1, z)
        nx, ny = int(tx1) - int(tx0) + 1, int(ty1) - int(ty0) + 1
        if nx * ny <= 100 or z <= 8:
            break
        z -= 1
    mos = np.zeros((ny * 256, nx * 256), np.float32)
    for j in range(ny):
        for i in range(nx):
            p = F.terrarium_tile(z, int(tx0) + i, int(ty0) + j)
            a = np.array(Image.open(p).convert("RGB"), np.float32)
            mos[j * 256:(j + 1) * 256, i * 256:(i + 1) * 256] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
    np.maximum(mos, 0, out=mos)     # Terrarium includes bathymetry; show the sea as a flat surface
    world = 2 * math.pi * R_EARTH
    scale = 256 * 2 ** z / world

    def sample(W, H, edges=False):
        # edges=True puts samples on the box edges (mesh vertices); otherwise on pixel centres (texture)
        o, dw, dh = (0, W - 1, H - 1) if edges else (0.5, W, H)
        xs = grid.x0 + (np.arange(W) + o) * (grid.x1 - grid.x0) / dw
        ys = grid.y1 - (np.arange(H) + o) * (grid.y1 - grid.y0) / dh
        X, Y = np.meshgrid(xs, ys)
        px = (X + world / 2) * scale - int(tx0) * 256 - 0.5
        py = (world / 2 - Y) * scale - int(ty0) * 256 - 0.5
        return ndi.map_coordinates(mos, [py, px], order=1, mode="nearest")
    return sample, z


def hillshade(dem, ground_cell):
    """Multi-directional hillshade (weighted NW-heavy, as in USGS practice) so no slope goes flat black."""
    gy, gx = np.gradient(dem, ground_cell)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    alt = math.radians(45)
    out = 0
    for az, w in ((315, 0.4), (270, 0.2), (360, 0.2), (225, 0.2)):
        out = out + w * np.clip(np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(math.radians(az) - aspect), 0, 1)
    return out


def nlcd_classes(grid, f, W, H):
    layer = "NLCD_2019_Land_Cover_L48" if f["year"] <= 2021 else "NLCD_2021_Land_Cover_L48"
    p = F.nlcd_png(layer, grid.bbox3857(), W, H, f"{f['id']}_{W}x{H}_{layer}")
    a = np.array(Image.open(p).convert("RGB"), np.int32)
    rgb = (a[..., 0] << 16) | (a[..., 1] << 8) | a[..., 2]
    cls = np.zeros(rgb.shape, np.uint8)
    keys = np.array(list(NLCD_WMS.keys()))
    vals = np.array(list(NLCD_WMS.values()), np.uint8)
    exact = np.isin(rgb, keys)
    lut = dict(zip(keys.tolist(), vals.tolist()))
    flat = rgb.ravel()
    out = cls.ravel()
    for kk, vv in lut.items():
        out[flat == kk] = vv
    if (~exact).any():   # rare anti-aliased or no-data pixels: nearest valid neighbour
        idx = ndi.distance_transform_edt(~exact, return_distances=False, return_indices=True)
        cls = cls[idx[0], idx[1]] if exact.any() else cls
    return cls, layer


# Road classes: TIGER layer id -> (line width in texture px, colour). Drawn local first, primary on top.
ROADS = {8: (1, (240, 234, 220, 95)), 6: (2, (250, 244, 228, 220)), 2: (3, (255, 250, 238, 255))}


def context_layers(grid, f, pre_date, span_km, near_mask, tex):
    """Roads (drawn into the texture), towns, and buildings near the fire."""
    lon0, lat0 = merc_to_lonlat(grid.x0, grid.y0)
    lon1, lat1 = merc_to_lonlat(grid.x1, grid.y1)
    env = (lon0, lat0, lon1, lat1)
    S = TEX_LONG / GRID_LONG
    simplify = grid.cell / S * 0.7 * grid.k / 111320     # ~0.7 texture px, in degrees
    over = Image.new("RGBA", tex.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    n_roads = {}
    for layer, (width, col) in ROADS.items():
        feats = F.tiger("Transportation", layer, env, f"roads{layer}_{f['id']}", "MTFCC", offset=simplify)
        n_roads[layer] = len(feats)
        for x in feats:
            g = x.get("geometry") or {}
            lines = g.get("coordinates", []) if g.get("type") == "MultiLineString" else [g.get("coordinates", [])]
            for line in lines:
                if len(line) > 1:
                    d.line([grid.px(lon, lat, S) for lon, lat in line], fill=col, width=width)
    tex.paste(Image.alpha_composite(tex.convert("RGBA"), over).convert("RGB"))
    places = []
    for layer in (25, 26):       # Census 2020 incorporated places and CDPs
        for x in F.tiger("Places_CouSub_ConCity_SubMCD", layer, env, f"places{layer}_{f['id']}",
                         "BASENAME,POP100,HU100,INTPTLAT,INTPTLON", geometry=False):
            p = x["properties"]
            px, py = grid.px(float(p["INTPTLON"]), float(p["INTPTLAT"]))
            if 0 <= px < grid.W and 0 <= py < grid.H:
                places.append(dict(name=p["BASENAME"], x=round(px, 1), y=round(py, 1),
                                   pop=p["POP100"], homes=p["HU100"], kind="city" if layer == 25 else "cdp"))
    # Buildings: OSM as of the day before ignition. Optional; Overpass is often overloaded.
    bxy, stamp = [], None
    if span_km < 70:
        bb = f"{lat0:.4f},{lon0:.4f},{lat1:.4f},{lon1:.4f}"
        q = f'[out:json][timeout:600][date:"{pre_date}T00:00:00Z"][bbox:{bb}];way["building"];out center;'
        try:
            res = F.overpass(q, f"buildings_{f['id']}")
            stamp = res.get("osm3s", {}).get("timestamp_osm_base")
            for el in res["elements"]:
                c = el.get("center")
                if c:
                    x, y = grid.px(c["lon"], c["lat"])
                    if 0 <= int(x) < grid.W and 0 <= int(y) < grid.H and near_mask[int(y), int(x)]:
                        bxy.append((x, y))
        except RuntimeError as e:
            print("  buildings skipped:", str(e)[:100])
    return n_roads, places, np.array(bxy, np.float32).reshape(-1, 2), stamp


# --- main build -------------------------------------------------------------------
def build(fid):
    f = next(x for x in FIRES if x["id"] == fid)
    print(f"== {f['name']}")
    fin = official_final(f)
    disc = fin["properties"].get("attr_FireDiscoveryDateTime") if fin else None
    t_disc = datetime.fromtimestamp(disc / 1000, timezone.utc) if disc else utc(f["start"])

    feds_fid, fsteps = (None, [])
    if f["method"] == "feds":
        feds_fid, fsteps = feds_steps(f)
        print(f"  FEDS fireid {feds_fid}: {len(fsteps)} perimeters")
    hs_all = hotspots(f)
    print(f"  VIIRS detections in search box: {len(hs_all)}")

    # extent from official final perimeter and the FEDS final perimeter
    finals = [g for g in ([fin["geometry"]] if fin else []) + ([fsteps[-1]["geometry"]] if fsteps else [])]
    lons = [p[0] for g in finals for poly in rings_of(g) for p in poly[0]]
    lats = [p[1] for g in finals for poly in rings_of(g) for p in poly[0]]
    w, e, s, n = min(lons), max(lons), min(lats), max(lats)
    padx, pady = max((e - w) * 0.12, 0.04), max((n - s) * 0.12, 0.03)
    grid = Grid((w - padx, s - pady, e + padx, n + pady))
    span_km = max(grid.W, grid.H) * grid.cell * grid.k / 1000
    print(f"  grid {grid.W}x{grid.H}, cell {grid.cell * grid.k:.0f} m ground, span {span_km:.0f} km")

    named = rasterize(grid, [fin["geometry"]]) if fin else np.zeros((grid.H, grid.W), bool)
    feds_final = rasterize(grid, [fsteps[-1]["geometry"]]) if fsteps else np.zeros_like(named)
    parts, off_mask = official_parts(f, grid, feds_final if fsteps else named)
    print(f"  official parts: {parts}")
    ref = off_mask | feds_final
    allow = ndi.binary_dilation(ref, structure=disk(1500 / grid.k / grid.cell))
    near = ndi.binary_dilation(ref, structure=disk(2000 / grid.k / grid.cell))

    # attribute detections: inside the buffered reference perimeter
    hs = []
    for h in hs_all:
        x, y = grid.px(h["lon"], h["lat"])
        if 0 <= int(x) < grid.W and 0 <= int(y) < grid.H and allow[int(y), int(x)] and h["t"] >= t_disc - timedelta(hours=6):
            h["x"], h["y"] = x, y
            hs.append(h)
    hs.sort(key=lambda h: h["t"])
    print(f"  attributed detections: {len(hs)}")

    t0 = t_disc.replace(minute=0, second=0, microsecond=0)
    e0 = t0.replace(hour=(t0.hour // STEP_H) * STEP_H)
    t_end = utc(f["end"]) + timedelta(days=1)
    edges = [e0]
    while edges[-1] < t_end:
        edges.append(edges[-1] + timedelta(hours=STEP_H))

    viirs_masks = viirs_spread(grid, hs, edges, allow)
    masks = feds_spread(grid, fsteps, edges) if f["method"] == "feds" else viirs_masks

    # trim the tail: stop 2 steps after growth drops below 0.2 % of the final area for good
    areas = np.array([(m * grid.cell_km2).sum() for m in masks])
    final_a = areas[-1]
    grow = np.diff(np.concatenate([[0], areas]))
    active = np.nonzero(grow > 0.002 * final_a)[0]
    if not len(active):
        raise RuntimeError(f"{fid}: no growth found in the window; check search box and dates")
    first, last = int(active[0]), min(len(masks) - 1, int(active[-1]) + 2)
    first = max(0, first - 1)
    masks, viirs_masks = masks[first:last + 1], viirs_masks[first:last + 1]
    edges = edges[first:last + 2]
    t0 = edges[0]
    raw_final_km2 = float((masks[-1] * grid.cell_km2).sum())
    # Extent from the official perimeter, timing from the satellites (375 m pixels inflate edges).
    masks = [m & off_mask for m in masks]
    viirs_masks = [m & off_mask for m in viirs_masks]

    seed = np.zeros_like(off_mask)
    if hs:
        h = next((h for h in hs if h["t"] > edges[0]), None)
        if h:
            seed[int(h["y"]), int(h["x"])] = True
    arr = arrival_hours(masks, edges, t0, seed)
    # official cells the satellites never flagged: take the arrival time of the nearest burned cell
    miss = off_mask & ~np.isfinite(arr)
    if miss.any() and np.isfinite(arr).any():
        iy, ix = ndi.distance_transform_edt(~np.isfinite(arr), return_distances=False, return_indices=True)
        arr[miss] = arr[iy[miss], ix[miss]]
    never_flagged = float(miss.sum() / max(1, off_mask.sum()))
    print(f"  official cells never flagged by satellite: {never_flagged:.1%}")
    hs = [h for h in hs if edges[0] < h["t"] <= edges[-1]]      # detections inside the replay only
    arr_q = np.where(np.isfinite(arr), np.clip(np.round(arr * 10), 0, UNBURNED - 1), UNBURNED).astype(np.uint16)

    # terrain
    ground_cell = grid.cell * grid.k
    sample, dem_z = dem_sampler(grid, ground_cell / 2)
    MW = int(round(grid.W / GRID_LONG * MESH_LONG)) + 1
    MH = int(round(grid.H / GRID_LONG * MESH_LONG)) + 1
    dem_mesh = sample(MW, MH, edges=True)
    TW, TH = int(grid.W * TEX_LONG / GRID_LONG), int(grid.H * TEX_LONG / GRID_LONG)
    dem_tex = sample(TW, TH)

    # vegetation texture (pre-fire NLCD), with a soft baked hillshade
    cls_tex, nlcd_layer = nlcd_classes(grid, f, TW, TH)
    pal = np.zeros((256, 3), np.float32)
    for c, v in PALETTE.items():
        pal[c] = [(v >> 16) & 255, (v >> 8) & 255, v & 255]
    rgb = ndi.gaussian_filter(pal[cls_tex], sigma=(0.9, 0.9, 0))          # soften blocky 30 m class edges
    grain = ndi.gaussian_filter(np.random.default_rng(7).standard_normal(cls_tex.shape), 0.7)
    canopy = np.isin(cls_tex, (41, 42, 43, 52))
    rgb *= (1 + np.where(canopy, 0.10, 0.035) * grain / grain.std())[..., None]   # tree-crown texture
    tex_cell = ground_cell * GRID_LONG / TEX_LONG
    shade = hillshade(dem_tex, tex_cell)
    relief = dem_tex - ndi.gaussian_filter(dem_tex, 600 / tex_cell)            # valleys < 0 < ridges, ~600 m scale
    ao = np.clip(1 + relief / 400, 0.72, 1.08)
    rgb *= ((0.5 + 0.62 * shade) * ao)[..., None]
    tex = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))

    # land-cover class on the spread grid (mode of the 4x4 block)
    cls_grid = cls_tex.reshape(grid.H, TH // grid.H, grid.W, TW // grid.W)[:, 0, :, 0]

    pre = (t_disc - timedelta(days=1)).strftime("%Y-%m-%d")
    n_roads, places, bxy, osm_stamp = context_layers(grid, f, pre, span_km, near, tex)
    b_arr = np.array([arr_q[int(y), int(x)] for x, y in bxy], np.uint16) if len(bxy) else np.zeros(0, np.uint16)
    print(f"  road segments {n_roads}, places {len(places)}, buildings near fire {len(bxy)}")

    # weather at the burned-area centroid
    yy, xx = np.nonzero(off_mask)
    clon, clat = merc_to_lonlat(grid.x0 + (xx.mean() + 0.5) * grid.cell, grid.y1 - (yy.mean() + 0.5) * grid.cell)
    wx = F.weather(clat, clon, (edges[0] - timedelta(days=1)).strftime("%Y-%m-%d"),
                   edges[-1].strftime("%Y-%m-%d"), f"wx_{f['id']}")
    hrs = [(utc(t) - t0).total_seconds() / 3600 for t in wx["hourly"]["time"]]
    keep = [i for i, h in enumerate(hrs) if -24 <= h <= (edges[-1] - t0).total_seconds() / 3600]
    weather = {k: [wx["hourly"][k][i] for i in keep] for k in wx["hourly"] if k != "time"}
    weather["h"] = [round(hrs[i], 2) for i in keep]

    # per-step stats
    steps = []
    for k in range(len(masks)):
        a, b = edges[k], edges[k + 1]
        m = arr <= (b - t0).total_seconds() / 3600
        hk = [h for h in hs if a < h["t"] <= b]
        burned_cls = {g: round(float(grid.cell_km2[m & np.isin(cls_grid, c)].sum()), 2)
                      for g, c in GROUPS.items()}
        steps.append(dict(
            h=round((b - t0).total_seconds() / 3600, 1),
            km2=round(float((m * grid.cell_km2).sum()), 2),
            det=len(hk), frp=round(sum(h["frp"] for h in hk), 1),
            cls=burned_cls))
    for k, s in enumerate(steps):
        s["grow"] = round(s["km2"] - (steps[k - 1]["km2"] if k else 0), 2)

    # validation numbers that live with the fire
    off_km2 = float((off_mask * grid.cell_km2).sum())
    val = dict(final_km2=steps[-1]["km2"], final_acres=round(steps[-1]["km2"] * 247.105),
               official_parts=parts, official_gis_acres=sum(parts.values()) or None,
               official_raster_acres=round(off_km2 * 247.105),
               raw_satellite_acres=round(raw_final_km2 * 247.105),
               iou_vs_official=round(iou(np.isfinite(arr), off_mask), 3),
               never_flagged_share=round(never_flagged, 3),
               calfire_acres=calfire_acres(f))
    # timing check: first satellite detection in a cell minus modelled arrival (should be >= 0 h for most cells)
    first = np.full(arr.shape, np.inf)
    for h in hs:
        xi, yi, th = int(h["x"]), int(h["y"]), (h["t"] - t0).total_seconds() / 3600
        first[yi, xi] = min(first[yi, xi], th)
    ok = np.isfinite(first) & np.isfinite(arr)
    lag = first[ok] - arr[ok]
    val.update(detect_minus_arrival_h_median=round(float(np.median(lag)), 1),
               share_detected_before_arrival=round(float((lag < -0.5).mean()), 3))
    if f["method"] == "feds":
        va = np.array([(m * grid.cell_km2).sum() for m in viirs_masks])
        fa = np.array([(m * grid.cell_km2).sum() for m in masks])
        mid = int(np.searchsorted(fa, 0.5 * fa[-1]))      # timing check halfway through the fire
        val.update(viirs_vs_feds_iou_final=round(iou(viirs_masks[-1], masks[-1]), 3),
                   viirs_vs_feds_iou_mid=round(iou(viirs_masks[mid], masks[mid]), 3),
                   viirs_vs_feds_area_r=round(float(np.corrcoef(va, fa)[0, 1]), 3))
        # timing calibration: per-cell arrival from FEDS minus arrival from our independent VIIRS rebuild
        arr_v = arrival_hours(viirs_masks, edges, t0, seed)
        for sh in (0, FEDS_SHIFT_H):
            a_f = arr if sh == FEDS_SHIFT_H else arrival_hours([m & off_mask for m in feds_spread(grid, fsteps, edges, sh)], edges, t0, seed)
            both = np.isfinite(a_f) & np.isfinite(arr_v)
            val[f"feds_minus_viirs_h_shift{sh}"] = round(float(np.median(a_f[both] - arr_v[both])), 1)
    print("  validation", val)

    # hotspots (binary: x,y grid float16-ish as uint16*8, time 0.1 h, frp*10)
    hsb = np.array([(min(65535, int(h["x"] * 64)), min(65535, int(h["y"] * 64)),
                     max(0, min(65535, int(round((h["t"] - t0).total_seconds() / 360)))),
                     min(65535, int(h["frp"] * 10))) for h in hs if h["t"] <= edges[-1]], np.uint16)

    out = WEB_DATA / f["id"]
    out.mkdir(parents=True, exist_ok=True)
    save_b64(arr_q, out / "arrival.txt")
    save_b64(np.round(dem_mesh).astype(np.int16), out / "dem.txt")
    tex.save(out / "tex.webp", quality=82, method=6)
    save_b64(hsb, out / "hotspots.txt")
    bq = np.column_stack([np.clip(bxy * 64, 0, 65535).astype(np.uint16), b_arr]) if len(bxy) else np.zeros((0, 3), np.uint16)
    save_b64(bq.astype(np.uint16), out / "buildings.txt")
    meta = dict(
        id=f["id"], name=f["name"], year=f["year"], note=f["note"], method=f["method"],
        feds_fireid=feds_fid, t0=t0.isoformat(), discovery=t_disc.isoformat(),
        grid=dict(W=grid.W, H=grid.H, cell_ground_m=round(ground_cell, 2), lat0=grid.lat0,
                  bbox_ll=[*merc_to_lonlat(grid.x0, grid.y0), *merc_to_lonlat(grid.x1, grid.y1)]),
        mesh=dict(W=MW, H=MH, zmin=int(dem_mesh.min()), zmax=int(dem_mesh.max()), terrarium_z=dem_z),
        tex=dict(W=TW, H=TH, nlcd=nlcd_layer),
        steps=steps, weather=weather, weather_point=[round(clon, 4), round(clat, 4)],
        weather_model=wx.get("hourly_units") and "Open-Meteo historical (ERA5/ERA5-Land reanalysis)",
        n_road_segments=n_roads, places=places, n_buildings=int(len(bxy)), n_hotspots=int(len(hsb)),
        osm_buildings_date=pre if osm_stamp else None, osm_base=osm_stamp, validation=val,
        official=dict(gis_acres=val["official_gis_acres"],
                      irwin=fin["properties"].get("attr_IrwinID") if fin else None,
                      containment=fin["properties"].get("attr_ContainmentDateTime") if fin else None),
    )
    write_json(out / "meta.json", meta)
    sizes = {p.name: p.stat().st_size // 1024 for p in out.iterdir()}
    print("  wrote", sizes, "KB")
    return meta


if __name__ == "__main__":
    for fid in sys.argv[1:]:
        build(fid)
