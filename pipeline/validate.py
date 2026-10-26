"""KPI gates from PLAN.md. Writes data/validation.json; exits 1 if a gate fails.

Gates
- raster:   our raster area vs the equal-area (EPSG:3310) area of the official polygons, within ±2 %
            (extent is clipped to the official perimeter, so this checks rasterization and area maths only)
- timing:   FEDS fires: median per-cell arrival (FEDS, shifted) - arrival (our VIIRS rebuild) within ±6 h
            (first-detection-minus-arrival is reported only: interior burn-out days later inflates it on slow fires)
- timing:   2020–21 fires: our VIIRS reconstruction vs NASA FEDS, area-over-time r >= 0.95 and IoU at mid-fire >= 0.85
            Park 2024: our timeline vs NIFC daily IR/mixed perimeters, median |area difference| <= 20 %
- sanity:   area never decreases; weather covers the replay
Published acres (CAL FIRE incident list, WFIGS GISAcres attribute) are reported, not gated.
"""
import json
import sys
from datetime import datetime, timezone

import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import shape

import fetch as F
from common import RAW, ROOT, WEB_DATA
from fires import FIRES

ALBERS = Transformer.from_crs(4326, 3310, always_xy=True)


def area_at(meta, when):
    h = (when - datetime.fromisoformat(meta["t0"])).total_seconds() / 3600
    hs = [0] + [s["h"] for s in meta["steps"]]
    km = [0] + [s["km2"] for s in meta["steps"]]
    return float(np.interp(h, hs, km)) * 247.105


def albers_acres(fid, names):
    """Equal-area acres of the union of the official parts used for this fire."""
    geoms = []
    for p in sorted((RAW / "nifc_wfigs").glob(f"parts_{fid}_*.json")):
        for x in json.loads(p.read_text(encoding="utf-8"))["features"]:
            if x.get("geometry") and x["properties"]["poly_IncidentName"].title() in names:
                geoms.append(shapely.make_valid(shape(x["geometry"])))
    u = shapely.union_all(geoms)
    return shapely.transform(u, lambda c: np.column_stack(ALBERS.transform(c[:, 0], c[:, 1])), interleaved=True).area / 4046.856


def park_vs_ir(meta):
    where = "attr_POOState='US-CA' AND poly_IncidentName='PARK' AND poly_GISAcres>1000"
    feats = F.wfigs_query("WFIGS_Daily_Perimeters_Public", where, "park_daily", geometry=False,
                          fields="poly_GISAcres,poly_DateCurrent,poly_CreateDate,poly_MapMethod")
    rows = []
    for x in feats:
        p = x["properties"]
        t = p.get("poly_DateCurrent") or p.get("poly_CreateDate")
        if t:
            when = datetime.fromtimestamp(t / 1000, timezone.utc)
            ours = area_at(meta, when)
            rows.append(dict(t=when.isoformat(), official=round(p["poly_GISAcres"]), ours=round(ours),
                             diff=round(ours / p["poly_GISAcres"] - 1, 3), method=p["poly_MapMethod"]))
    rows.sort(key=lambda r: r["t"])
    return rows, (float(np.median([abs(r["diff"]) for r in rows])) if rows else None)


if __name__ == "__main__":
    out, fails = {}, []
    for f in FIRES:
        p = WEB_DATA / f["id"] / "meta.json"
        if not p.exists():
            fails.append(f"{f['id']}: not built")
            continue
        meta = json.loads(p.read_text(encoding="utf-8"))
        v = dict(meta["validation"])
        v["albers_acres"] = round(albers_acres(f["id"], set(v["official_parts"])))
        v["extent_ratio"] = round(v["final_acres"] / v["albers_acres"], 4)
        v["calfire_published_acres"] = v.get("calfire_acres")
        v["gate_extent_2pct"] = abs(v["extent_ratio"] - 1) <= 0.02
        if not v["gate_extent_2pct"]:
            fails.append(f"{f['id']}: extent ratio {v['extent_ratio']}")
        lag = v.get("detect_minus_arrival_h_median")
        if "feds_minus_viirs_h_shift12" in v:
            v["gate_feds_timing"] = abs(v["feds_minus_viirs_h_shift12"]) <= 6
            if not v["gate_feds_timing"]:
                fails.append(f"{f['id']}: FEDS - VIIRS arrival {v['feds_minus_viirs_h_shift12']} h")
        if "viirs_vs_feds_area_r" in v:
            v["gate_timing"] = v["viirs_vs_feds_area_r"] >= 0.95 and v["viirs_vs_feds_iou_mid"] >= 0.85
            if not v["gate_timing"]:
                fails.append(f"{f['id']}: VIIRS vs FEDS r {v['viirs_vs_feds_area_r']} IoU-mid {v['viirs_vs_feds_iou_mid']}")
        if f["id"] == "park":
            rows, med = park_vs_ir(meta)
            v["vs_nifc_daily"] = dict(n=len(rows), median_abs_diff=med, rows=rows)
            v["gate_timing"] = med is not None and med <= 0.20
            if not v["gate_timing"]:
                fails.append(f"park: median |diff| vs NIFC daily perimeters {med}")
        st = meta["steps"]
        v["sanity"] = dict(steps=len(st), hotspots=meta["n_hotspots"],
                           monotonic_area=all(b["km2"] >= a["km2"] for a, b in zip(st, st[1:])),
                           weather_covers=meta["weather"]["h"][0] <= 0 and meta["weather"]["h"][-1] >= st[-1]["h"] - 1)
        if not all(v["sanity"][k] for k in ("monotonic_area", "weather_covers")):
            fails.append(f"{f['id']}: sanity {v['sanity']}")
        out[f["id"]] = v
        print(f"{f['id']:10s} ours {v['final_acres']:>9,} ac | polygons {v['albers_acres']:>9,} ({v['extent_ratio']:.3f}) | "
              f"GIS attr {v['official_gis_acres']:>9,} | CAL FIRE {v['calfire_published_acres'] or 0:>11,.0f} | raw sat {v['raw_satellite_acres']:>9,}"
              + f" | det-arr {lag} h" + (f" | FEDS-VIIRS shift0 {v['feds_minus_viirs_h_shift0']} h, shift12 {v['feds_minus_viirs_h_shift12']} h" if "feds_minus_viirs_h_shift12" in v else "")
              + (f" | FEDS r {v['viirs_vs_feds_area_r']} IoU-mid {v['viirs_vs_feds_iou_mid']}" if "viirs_vs_feds_area_r" in v else "")
              + (f" | NIFC daily med|d| {v['vs_nifc_daily']['median_abs_diff']:.3f} n={v['vs_nifc_daily']['n']}" if "vs_nifc_daily" in v else ""))
    (ROOT / "data" / "validation.json").write_text(json.dumps(dict(fires=out, failures=fails), indent=1), encoding="utf-8")
    print("FAILURES:" if fails else "all gates pass", *fails, sep="\n  ")
    sys.exit(1 if fails else 0)
