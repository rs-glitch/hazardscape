"""Key moments, 'what happened' and 'what it teaches' cards -> web/data/<event>/moments.json (derived from each meta.json).

Every chip: h (hours on the replay clock), label, text (one factual sentence), src. Every number is read from meta.json,
which already carries its own source; only the plain-language lessons are written by hand.
Run after the other builders:  python build_moments.py
"""
import json
from datetime import datetime

from common import WEB_DATA, write_json


def load(e):
    return json.loads((WEB_DATA / e / "meta.json").read_text(encoding="utf-8"))


def hrs(t, t0):
    return round((datetime.fromisoformat(t) - datetime.fromisoformat(t0)).total_seconds() / 3600, 2)


def hurricane():
    m = load("helene"); tr = m["track"]; bt = m["best_track"]; t0 = m["t0"]
    src = "NHC HURDAT2 best track"
    ip = max(range(len(tr["vmax"])), key=lambda i: tr["vmax"][i]); ipm = min(range(len(tr["pmin"])), key=lambda i: tr["pmin"][i])
    land = next(b for b in bt if b["id"] == "L")
    hl = hrs(land["t"], t0)
    sites = {s["id"]: s for s in m["sites"] if "era5" in s}
    asv, fl = sites.get("asheville"), sites.get("landfall")
    ra = lambda s: round(s["era5"]["cum"][-1])
    i0 = max(0, ip - 24)
    mom = [dict(h=i0, label="Rapid strengthening", text=f"Sustained wind rose from {tr['vmax'][i0]:.0f} kt to {tr['vmax'][ip]:.0f} kt over the 24 hours before its peak.", src=src + " (interpolated)"),
           dict(h=hl, label="Landfall, Florida Big Bend", text=f"HURDAT2 marks landfall at {land['t'][11:16]} UTC on {land['t'][:10]} with {land['vmax']:.0f} kt and {land['pmin']:.0f} mb.", src=src),
           dict(h=ip, label="Peak wind", text=f"Highest sustained wind in the replay: {tr['vmax'][ip]:.0f} kt ({tr['vmax'][ip]*1.15078:.0f} mph).", src=src + " (6-hourly, interpolated to hours)"),
           dict(h=ipm, label="Lowest pressure", text=f"Lowest central pressure in the replay: {tr['pmin'][ipm]:.0f} mb.", src=src + " (interpolated)")]
    if asv:
        hr = asv["era5"]["hourly"]; k = max(range(len(hr)), key=lambda i: hr[i])
        mom.append(dict(h=k, label="Heaviest rain at Asheville", text=f"The ERA5 reanalysis (a model, not a rain gauge) puts the wettest hour at {hr[k]:.0f} mm; {ra(asv)} mm fell in the replay window.", src="ERA5 via Open-Meteo (modelled)"))
    mom.sort(key=lambda x: x["h"])
    hap = [dict(k="Peak sustained wind", v=f"{tr['vmax'][ip]:.0f} kt", tag="interpolated", src=src),
           dict(k="Lowest pressure", v=f"{tr['pmin'][ipm]:.0f} mb", tag="interpolated", src=src),
           dict(k="Landfall", v=f"{land['vmax']:.0f} kt, {land['pmin']:.0f} mb, {land['t'][:16].replace('T', ' ')} UTC", tag="measured (best track)", src=src),
           dict(k="Rain, Asheville", v=f"{ra(asv)} mm" if asv else "n/a", tag="modelled", src="ERA5 via Open-Meteo"),
           dict(k="Rain, landfall area", v=f"{ra(fl)} mm" if fl else "n/a", tag="modelled", src="ERA5 via Open-Meteo")]
    tea = dict(title="Coast wind, mountain rain", text="Wind and surge hit the coast within hours of landfall. The rain that flooded the mountains came later and far inland. Look at the wind rings for the coast, then the rain layer for the hills.", src="Built from the HURDAT2 and ERA5 layers on this tab")
    return "helene", dict(moments=mom, happened=hap, teaches=tea)


def flood():
    m = load("helene-wnc"); t0 = m["t0"]; G = m["gauges"]
    src = "NWS NWPS flood categories / USGS NWIS gauge records"
    pk = sorted(G, key=lambda g: hrs(g["peak_time"], t0))
    mom = []
    def gappy(g):
        st = g["stage"]; k = max(range(len(st)), key=lambda i: -1 if st[i] is None else st[i])
        return any(v is None for v in st[max(0, k - 48):k + 49])
    def gaprange(g):
        st = g["stage"]; k = max(range(len(st)), key=lambda i: -1 if st[i] is None else st[i])
        a = k
        while a > 0 and st[a - 1] is None: a -= 1
        return a
    for g in (pk[0], pk[len(pk) // 2], pk[-1]):
        c = g["cats"]
        cat = "major" if g["peak_ft"] >= c["major"] else "moderate" if g["peak_ft"] >= c["moderate"] else "minor" if g["peak_ft"] >= c["minor"] else "below minor"
        if gappy(g):
            mom.append(dict(h=hrs(g["peak_time"], t0), label=f"Highest recorded: {g['label']}", text=f"Highest recorded value {g['peak_ft']:.1f} ft (major starts at {c['major']:.1f} ft) on {g['peak_time'][:10]} at {g['peak_time'][11:16]} local. The gauge record has gaps near this reading, so the true crest is not known.", src=src))
        else:
            mom.append(dict(h=hrs(g["peak_time"], t0), label=f"Crest: {g['label']}", text=f"{g['label']} peaked at {g['peak_ft']:.1f} ft, in the {cat} category (major starts at {c['major']:.1f} ft), on {g['peak_time'][:10]} at {g['peak_time'][11:16]} local time.", src=src))
    rec = [g for g in G if g.get("prev") and g["prev"].get("beats_h")]
    top = max(G, key=lambda g: g["peak_ft"] - g["cats"]["major"])
    hi = max(G, key=lambda g: g["peak_ft"])
    hm = load("helene"); asv = next(x for x in hm["sites"] if x["id"] == "asheville")["era5"]
    kr = max(range(len(asv["hourly"])), key=lambda i: asv["hourly"][i])
    rain_utc = datetime.fromisoformat(hm["t0"]).timestamp() + kr * 3600
    lag = sorted((datetime.fromisoformat(g["peak_time"]).timestamp() - rain_utc) / 3600 for g in G)
    hap = [dict(k="Gauges whose highest recorded value is above the previous record", v=f"{len(rec)} of {len(G)}", tag="measured", src="USGS peak vs previous peak of record, where the station record gives one"),
           dict(k="Highest crest", v=f"{hi['peak_ft']:.1f} ft ({hi['label']})", tag="measured", src=src),
           dict(k="Most above major stage", v=f"{top['peak_ft'] - top['cats']['major']:.1f} ft ({top['label']})", tag="measured", src=src),
           dict(k="Crest after the wettest ERA5 hour at Asheville", v=f"{lag[0]:.0f} to {lag[-1]:.0f} h (rain is modelled, crest measured)", tag="mixed", src="ERA5 via Open-Meteo; USGS gauges"),
           dict(k="Highest-reading times, first to last", v=f"{pk[0]['peak_time'][5:16].replace('T', ' ')} to {pk[-1]['peak_time'][5:16].replace('T', ' ')} local", tag="measured", src=src)]
    tea = dict(title="A flood crest takes time to arrive", text="Small creeks crested within hours of the rain, big rivers a day later. That gap is the time to warn towns downstream. Compare each gauge's crest time with the rain.", src="Built from the gauge crest times on this tab")
    return "helene-wnc", dict(moments=mom, happened=hap, teaches=tea)


def drought():
    m = load("ca-drought"); W = m["weeks"]; S = m["stats"]
    src = "US Drought Monitor county DSCI, California"
    pk = lambda k: max(range(len(S)), key=lambda i: S[i][k])
    wk = lambda i: i * 168
    mom = []
    i = next(i for i, s in enumerate(S) if s["d4"] > 0)
    mom.append(dict(h=wk(i), label="Exceptional drought (D4) appears", text=f"D4 first covers {S[i]['d4']:.1f} % of the state in the week of {W[i]}.", src=src))
    for k, lab in (("d3", "Peak extreme drought (D3+)"), ("d4", "Peak exceptional drought (D4)"), ("d2", "Peak severe drought (D2+)")):
        i = pk(k)
        mom.append(dict(h=wk(i), label=lab, text=f"{k.upper()} {'or worse ' if k != 'd4' else ''}reaches {S[i][k]:.0f} % of California in the week of {W[i]} (county-weighted estimate{'; the official area-based figure was about 46 % on 14 Sep 2021' if k == 'd4' else ''}).", src=src))
    for r in m["reservoirs"]:
        v, j = min((v, j) for j, v in enumerate(r["acft"]) if v is not None)
        mom.append(dict(h=wk(j), label=f"{r['name']} low", text=f"{r['name']} stored {v/1e6:.2f} million acre-feet in the week of {W[j]}, its lowest in the replay.", src="USGS NWIS reservoir storage"))
    i = len(S) - 1
    mom.append(dict(h=wk(i), label="End of the replay", text=f"By {W[i]}, D2 or worse covers {S[i]['d2']:.0f} % of the state.", src=src))
    mom.sort(key=lambda x: x["h"])
    hap = [dict(k=f"Peak {k.upper()}{'+' if k != 'd4' else ''}", v=f"{S[pk(k)][k]:.0f} % ({W[pk(k)]})", tag="measured", src=src) for k in ("d2", "d3", "d4")]
    for r in m["reservoirs"]:
        hap.append(dict(k=f"{r['name']} lowest", v=f"{min(v for v in r['acft'] if v is not None)/1e6:.2f} M acre-ft", tag="measured", src="USGS NWIS"))
    tea = dict(title="One wet winter does not end a drought", text="Reservoirs and soil recover after wet months, but Central Valley wells and groundwater lag. Switch on the wells and the groundwater layer to see what the map alone hides.", src="Built from the layers on this tab")
    return "ca-drought", dict(moments=mom, happened=hap, teaches=tea)


def quake():
    m = load("ridgecrest"); Q = m["quakes"]; s1, s2 = m["shocks"]
    src = "USGS ComCat"
    after = [q for q in Q if q[0] > s2["h"] + 0.01 and q[4] < s2["mag"]]
    big = max(after, key=lambda q: q[4])
    bands = [(2, 3), (3, 4), (4, 5), (5, 9)]
    cnt = lambda lo, hi, a, b: sum(1 for q in Q if lo <= q[4] < hi and a <= q[0] < b)
    d1 = s2["h"] + 24
    mom = [dict(h=round(s1["h"], 2), label="M6.4 foreshock", text=f"M{s1['mag']} at depth {s1['depth']} km; USGS peak intensity MMI 8.4 (ComCat; 8.3 on the grid drawn here).", src="USGS ComCat / ShakeMap"),
           dict(h=round(s2["h"], 2), label="M7.1 mainshock", text=f"M{s2['mag']} about {s2['h'] - s1['h']:.0f} hours later at depth {s2['depth']} km; USGS peak intensity MMI 8.7 (ComCat; 8.6 on the grid drawn here).", src="USGS ComCat / ShakeMap"),
           dict(h=round(big[0], 2), label=f"Largest aftershock M{big[4]:.1f}", text=f"The largest catalogued shock after the M7.1 was M{big[4]:.1f}, {big[0] - s2['h']:.1f} hours after it.", src=src),
           dict(h=round(d1, 2), label="One day after the M7.1", text=f"{cnt(2, 9, s2['h'] + 0.01, d1)} shocks of M2 or more were catalogued in the first 24 hours after the M7.1 (the M7.1 itself not counted).", src=src),
           dict(h=round(s2["h"] + 168, 2), label="One week after", text=f"{cnt(2, 9, s2['h'] + 0.01, s2['h'] + 168)} shocks of M2 or more in the first 7 days after the M7.1.", src=src)]
    mom = [x for x in mom if x["h"] <= m["hours"]]
    band = lambda a, b: " / ".join(str(cnt(lo, hi, a, b)) for lo, hi in bands)
    hap = [dict(k="Catalogued shocks M2+ in the map area", v=str(len(Q)), tag="measured", src=src),
           dict(k="By band M2-3 / 3-4 / 4-5 / 5+ (the 5+ band includes the M6.4 and M7.1), whole replay", v=band(0, 1e9), tag="measured", src=src),
           dict(k="By band, first 24 h after the M7.1 (M7.1 not counted)", v=band(s2["h"] + 0.01, d1), tag="measured", src=src),
           dict(k="Peak shaking, ShakeMap MMI", v="8.7 (M7.1), 8.4 (M6.4); grid drawn here 8.6 and 8.3", tag="modelled", src="USGS ShakeMap")]
    tea = dict(title="A few seconds can be enough", text="A few seconds of warning can be enough to begin drop, cover and hold on (it takes only a few seconds to start; see ShakeOut). Open the warning what-if and slide the delay: towns closest to the epicentre get none.", src="Built from the warning-time layer on this tab (simulated)")
    return "ridgecrest", dict(moments=mom, happened=hap, teaches=tea)


def fires():
    out = []
    for d in sorted(p for p in WEB_DATA.iterdir() if p.is_dir()):
        try:
            m = load(d.name)
        except Exception:
            continue
        if "steps" not in m or m.get("kind") or "validation" not in m:
            continue
        S = m["steps"]; fin = S[-1]["km2"]
        src = "NASA FEDS/VIIRS satellite detections, rasterised (this project)"
        at = lambda f: next(s for s in S if s["km2"] >= f * fin)
        dm = max(S, key=lambda s: s["det"])
        mom = [dict(h=0, label="First detection", text=f"The replay starts at the first satellite detection, {m['discovery'][:10]}.", src=src),
               dict(h=at(0.5)["h"], label="Half the final area", text=f"The burned area passes {fin * 0.5:.0f} km2 (half of the final {fin:.0f} km2) at about day {at(0.5)['h'] / 24:.0f}.", src=src),
               dict(h=at(0.9)["h"], label="90 % of final area", text=f"The burned area passes 90 % of its final size at about day {at(0.9)['h'] / 24:.0f}.", src=src),
               dict(h=dm["h"], label="Most detections in one step", text=f"The most satellite fire detections in one time step ({dm['det']}) come at about day {dm['h'] / 24:.0f}.", src=src)]
        mom.sort(key=lambda x: x["h"])
        v = m["validation"]
        imp = v["never_flagged_share"] > 0.3
        if imp:
            src = f"Official perimeter, timed by NASA FEDS/VIIRS detections ({v['never_flagged_share'] * 100:.0f} % of the area imputed)"
            for x in mom: x["src"] = src
            mom[1]["text"] += f" Satellite detections alone cover {v['raw_satellite_acres']:,.0f} acres; the official area is {v['calfire_acres']:,.0f} acres."
        hap = [dict(k="Final area", v=f"{fin:.0f} km2 ({v['final_acres']:,.0f} acres, rasterised)", tag="official perimeter, timed by satellite" if imp else "measured (satellite)", src=src),
               dict(k="Official area", v=f"{v['calfire_acres']:,.0f} acres (CAL FIRE)", tag="published", src="CAL FIRE incident list")]
        out.append((d.name, dict(moments=mom, happened=hap, teaches=dict(title="Fires grow in bursts", text="A fire grows in a few hard days, not evenly. Find the steepest part of the area curve, then check the wind and humidity charts at that time.", src="Built from this fire's area curve"), flag=(f"{v['never_flagged_share'] * 100:.0f} % of this fire's final area was never seen by satellite. It is given the time of the nearest satellite-flagged ground inside the official perimeter (imputed)." if v["never_flagged_share"] > 0.3 else ""))))
    return out


if __name__ == "__main__":
    for e, d in [hurricane(), flood(), drought(), quake(), *fires()]:
        write_json(WEB_DATA / e / "moments.json", d)
        print(e, len(d["moments"]), "moments", len(d["happened"]), "values")
