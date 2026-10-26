# Audit: Ridgecrest actionable layers (2026-10-20)

Read-only review. No project files edited. Selftest `ridgecrest@100,warn`, `ridgecrest`, `ridgecrest@60` ran ok at 1400x900 and 520x860; PNGs in `data/selftest/`.

## Ranked findings

1. CRITICAL. pipeline/build_quake_extra.py:73-78 (rupture). The USGS rupture.json is a MultiPolygon with 11 polygons (the file is ALOS-2 interferogram "rupture extent", not a slip model). The code flattens all rings then keeps `rings[:1]`. Only the first (SE-most, about 10 km long, x 316-346, y 299-328) reaches meta.json. The PNG at T=60 shows the outline about 15 km SE of the epicentre, away from the aftershock trend. Fix: keep every ring of every polygon; in web/index.html:704-706 draw each ring as its own Line (or LineSegments), because one Line joins the rings with false edges. Relabel "USGS ShakeMap rupture extent (ALOS-2 InSAR), extruded 0-15 km", not "finite-fault model" (index.html:785).
2. REQUIRED. index.html:802-806, 846 (RJ clock). Integral, days units and t since M7.1 are correct. Formula check: M3 over 1 yr gives 1277 events vs 1251 observed, good. But M5: model gives 12.8 events/yr and 11.2 in 30 d, and the product counts 4 M5+. At t=0 it shows 99.98 percent (the readout says "> 99.9 %") and 56 percent at 0.8 d. The "check" in the Method text validates M3 only. Fix: add an M5 line to the check ("model about 11 vs 4 counted"), and say the first-day numbers are an upper bound. Before the M7.1 and after the M6.4 the clock shows "–" and "Starts at the M7.1". That is correct, though the M6.4 is not modelled. Hindsight label present (created 2026-09-03): ok.
3. REQUIRED. index.html:785 vs. GNSS. Verified against data/raw/ngl_gnss/tenv3_P595.tenv3: east +628.0, north -250.9, hypot 676 mm, correct. Column use (w[7]+w[8], etc.) is correct. Units mm, E/N to x, -z correct (toZ grows southward). Windows are fine (4 Jul and 6 Jul excluded; 5 Jul = after the M6.4 only). The gn-note (index.html:799) states "676 mm" without saying it is the cumulative M6.4 + M7.1 + 2-9 d of afterslip (the M6.4 share at P595 is 109 mm). Fix: add "cumulative, M6.4 + M7.1 + early afterslip" to the note. The arrow for P595 is 20 km long at 0.03 scene km/mm, longer than its distance to the fault; consider 1 km = 100 mm... or label only.
4. OPTIONAL. Warning numbers. Reproduced: 4th-nearest station Q0072, 20.42 km (hypocentral); P 3.40 s; alert 8.40 s; blind zone 28 km; 10 s beyond 64 km. All four nearest towns show "none" (selftest panel). Station list is "operating" in IRIS, not proven to feed ShakeAlert (Q0072 etc.). Say so in the Method text.
5. OPTIONAL. index.html:662-668, 730. The S ring uses epicentral radius = Vs*t, but the colour uses sqrt(d²+8²)/Vs. The ring leads the true S arrival by up to 1.5 s near the epicentre. No visible effect in the PNG.
6. OPTIONAL. index.html:824. `fmt(w,0)` shows "0 s" for 0 < w < 0.5 and "10 s" for 9.5-10 (amber in the map). Use floor for the town text.
7. OPTIONAL. index.html:781 says dots are "true scale, not exaggerated" but they are placed at `dep * S.ex` (1.6). Same for rupture/stations. Say "depth drawn at the same 1.6x as the relief".
8. NIT. Warning chart x label "150" and RJ chart last tick "Jul 1…" clipped at the right edge (PNG 1400x2300). Alert toast does not fire if the slider is lowered after T already passed the new alert time (harmless).

## Source checks (WebFetch on news.berkeley.edu, 20 Oct 2026)
- Berkeley news 2019-10-17 "California rolls out first statewide earthquake early warning system": quotes ShakeAlert "issued an alert in 7.4 seconds" after the M7.1. It does NOT say what the 7.4 s is measured from. The app text says "after the M7.1 began": soften to "reports 7.4 s". Verified.
- Same article: MyShake statewide launch 17 Oct 2019 (Gov. Newsom). Verified.
- Same article: ShakeAlertLA "was not set to alert them to shaking from such a distant quake"; threshold since lowered. Verified (no number given; the app text does not give one either: ok). SCEC abstract: threshold MMI IV, calls for MMI III.
- "Drop, Cover and Hold On takes only a few seconds to start" (index.html:783) has no source. The wording is reasonable; either cite ShakeOut/USGS or say "a few seconds is enough to begin".

## State, NaN, XSS, mobile
- Scrub back across shocks: quakeSync resets uR/uW/uPh/uRP/uWP and `alerted` for the M7.1, and sets full reveal when jumped forward. No bug found. Stale `resumeAfterWave` after a mid-wave scrub is harmless (overwritten at the next shock).
- Delay slider: qWarnUpdate updates uAlert, text, chart and towns live; colours follow. ok.
- NaN: p===1 branch exists; c>0; t>=0 guarded by `live`. ok. XSS: all meta strings go through esc(); the toast uses esc(s.label). ok.
- Mobile 520x860: layout holds; 3D canvas is small, panel below the fold. No overflow except the clipped chart ticks.
- Honesty labels: "Simulated what-if", "measured", "fitted after the fact" present and accurate, except items 1-3.
