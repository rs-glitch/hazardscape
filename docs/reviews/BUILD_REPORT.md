# Build report (builder, 2026-10-21)

## What was done and why
- **A1 Drought layers.** Re-ran `pipeline/build_drought_extra.py` (cache resumed; the Open-Meteo hourly limit cost about 1 h of waiting). Wrote wells.txt, bucket.txt, grace.txt and the wells/bucket/grace keys in meta.json. The ERA5-Land check had NaN (constant-series points), which broke JSON parsing, so the medians now use nanmedian. Added the missing `LESSONS_HTML` function (data-derived lessons: map vs aquifer, soil, GRACE).
- **Blocker.** `const mercY` was declared twice, so the page did not boot. The drought copy is now `dMercY`. The module script passes `node --check`.
- **A2 Quake audit.** Checked every item against index.html: 11 rupture rings drawn one line per ring and labelled ALOS-2 InSAR; M5 upper-bound note; GNSS 676 mm labelled cumulative with the 109 mm M6.4 share; "reports 7.4 seconds" wording; depth drawn at 1.6x; floor for "<1 s" and ">=10 s"; chart ticks anchored at the right edge. All were already present. No edit needed.
- **A3 Selftest.** See below.
- **B (chosen with the engagement report).** New `pipeline/build_moments.py` derives chips only from each meta.json (no typed numbers). In the panel: "What it teaches" card first (30-40 words, one action), then 4-7 key-moment chips (click: stop, setT, quakeSync, history.replaceState, scene caption), then everything else folded in "Numbers, layers, charts and method" (open on desktop, closed under 860 px). Ridgecrest opens at hour 33 with the caption "Two earthquakes, 34 hours apart. Press play." Fires get the same chips; York shows an imputed-data flag (60 % never seen by satellite). Blantyre-type gauge cards say "highest recorded value, gaps near the crest". Drought gets a D3+/D4 chart.
- **Cut as clutter (engagement report section 4):** "What happened" card (it is still in moments.json as `happened` but not shown), the quake magnitude-band chart, the hurricane radii rework, and the new hurricane peak-wind chart (they already exist). Flood crest-lag vs the wettest ERA5 hour is in moments.json (26 to 47 h, modelled rain, measured crest) but not shown.

## Files changed
web/index.html; pipeline/build_moments.py (new); pipeline/build_drought_extra.py; web/data/ca-drought/{meta.json, wells.txt, bucket.txt, grace.txt, moments.json}; web/data/*/moments.json (16 events); web/data/sources.json; PROGRESS.md; review/BUILD_REPORT.md.

## Selftest (pipeline/selftest.py, 1400 and 400 px, no console errors)
ok: state, ca-drought (plus deep links @14000 with wells+table, soil, grace), helene, helene-wnc, ridgecrest, dixie, york, august, bridge, caldor, creek, eaton, gifford, monument, mosquito, palisades, park. Final index.html was re-tested on ca-drought, ridgecrest, helene, helene-wnc after the last edits; the fire views ran before the last small edits (moments card only, shared code).

## Skipped or not done
- Reservoir % of capacity with a historical-average line: the page already shows % of the 2020-23 maximum; capacity and averages need CDEC (blocked, 403/connection fails) and I could not verify capacity figures.
- Hurricane radii and wind/pressure rework: already drawn.
- Not done from the review lists: phone layout (#5, one chip row, slider over scene); changing caption at times (#9; only on chip click and at first frame for quakes); guess-then-reveal (#6); plain-wording pass for MMI/DSCI/HAND/ERA5 (#7, partial: the teach card and chips use plain words; panel text unchanged); one-layer-at-a-time for Hurricane (#8: Drought already opens with only the DSCI map; Hurricane unchanged).
- Stress item 3: M5 gauge already has the upper-bound note and an observed counter (`rj-obs`); not re-worded.
- Weight: Dixie folder about 4 MB (over the 3 MB budget) and state.json 0.97 MB: noted, not fixed.
- Soil-water bucket check against wells is weak (r = 0.13 valley wells vs state soil); this is stated in the Method text.

## Published files to update (sizes in bytes)
index.html 147,433; data/sources.json 6,158; data/ridgecrest/meta.json 381,031 (unchanged since last publish plan, update if not yet published); data/ca-drought/meta.json 49,706; wells.txt 32,328; bucket.txt 367,840; grace.txt 1,847,560; moments.json for each of the 16 events (about 1.6 to 2.0 KB each, 64 KB total on disk blocks). All are far below 16 MB.

## Fix round (after CRITIC_DATA and CRITIC_CODE_UX)
- **B1:** the M5+ gauge now carries "Upper bound for M5 and larger" with the model's first-year expectation computed from the USGS parameters (12.8; the stress and data reports said 13.8, my integral from t=0 to 365 d gives 12.8, so the page shows the computed value) against 4 catalogued, plus the M3+/M4+ fit line. My earlier report was wrong that this existed.
- **B2:** chips for gauges with gaps near the maximum (Blantyre) now read "Highest recorded ... the true crest is not known"; the row "Crest times" is now "Highest-reading times". The generic text does not repeat the exact outage hours.
- **B3:** York (any fire with more than 30 % never flagged) chips carry source "Official perimeter, timed by NASA FEDS/VIIRS detections (60 % of the area imputed)", the 41,423 vs 93,078 acre note, and the new flag wording.
- **Numbers:** MMI 8.4 and 8.7 (USGS; grid 8.3 and 8.6 stated); 24 h and 7 d counts exclude the M7.1 (2232, 3810); 5+ band labelled as including the M6.4 and M7.1; drought D4 chip says county-weighted with about 46 % official on 14 Sep 2021; wells lesson says "of the 18 Central Valley wells shown (farthest-point sampling)"; the warning teach card cites ShakeOut and no longer says "is enough" alone.
- **Code:** showFire sets `#id` unless the page came from a deep link (`S.deep`); the three drought files load with `.catch`, a missing file is replaced by zeros and its toggle is hidden instead of killing the tab (not tested with a file actually removed).
- **Checks:** `node --check` ok; selftest ok at 1400 and 400 px on ridgecrest, ca-drought (+ wells/table deep link), helene-wnc, york, dixie.
