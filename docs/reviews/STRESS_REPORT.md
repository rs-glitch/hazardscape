# Stress report: Hazard Replays (independent review)

Date: 2026-10-21. Independent review; no app or pipeline file was edited. The review scripts and raw results are not included in this repo.

**Version tested:** `web/index.html`, 142,184 bytes, modified 2026-10-20 22:37:35, unchanged during the whole test. `web/data/ca-drought/*` modified 2026-10-20 21:18. The builder had not changed anything yet, so this is the pre-build baseline.

## Verdicts

| Area | Verdict | Why |
|---|---|---|
| App robustness | **FAIL as shipped on disk, good once two defects are fixed** | The page does not boot (duplicate `const mercY`). With that one line patched in memory, 15 of 16 events run clean at three sizes. The Drought tab still fails because its data files do not exist. |
| Claims | **Mostly sound, three real problems** | 12,122 of 12,122 drought cells, all 8 flood categories, Helene peak wind, pressure and landfall, and Dixie acres match the raw files. The aftershock gauge is about 3.4× too high for M5+, Blantyre's "peak" is not the crest, and York is 60 % imputed. |
| Decisions | **Two confirmed, five need changes** | See the decision table. |

## Ranked findings

### F1. CRITICAL: the page does not boot
- **Evidence (measured):** `web/index.html` declares `const mercY` twice at module top level: line 557 (drought, unitless) and line 1047 (hurricane, metres). Chrome reports `SyntaxError: Identifier 'mercY' has already been declared`. The whole module fails, so there is no tab, no state view and no event. The page weighs 140 KB and shows an empty shell. `pipeline/selftest.py` would catch it, but it was last run before the 22:37 edit.
- **Repro:** serve `web/`, open `index.html`, read the console. Script: `review/stress/run_matrix.mjs dixie` against a plain `http.server`.
- **Fix:** rename the hurricane one to `mercYm`, and change its uses after line 1046 (lines 1063 onward). The two functions return different units, so deleting one would be wrong. Run `node --check` on the extracted module, or `selftest.py`, as a gate before every publish.
- **Root cause (design):** one 1,700-line module scope for five hazards. See decision D1.
- **My workaround:** `review/stress/patched_server.py` renames the second `mercY` in memory only. All results below use it.

### F2. HIGH: the Drought tab cannot load
- **Evidence (measured):** `showFire` fetches `wells.txt`, `bucket.txt` and `grace.txt` for the drought event (index.html line 405). `web/data/ca-drought/` holds only `counties.txt`, `dem.txt`, `dsci.txt`, `meta.json`, `tex.webp`. Result: `Could not load the data: data/ca-drought/wells.txt: HTTP 404`, with the overlay stuck and no tab highlighted. This happens at all three sizes (12 console errors in the matrix). The builder's Open-Meteo download hit HTTP 429 (`data/scratch/extra2.log`).
- **Repro:** open `#ca-drought`.
- **Fix:** (a) do not publish `index.html` before `build_drought_extra.py` finishes and the files exist. (b) Make the three layers optional: `getBin(...).catch(() => null)`, hide their toggles, and keep the DSCI view working. The current published v4 drought tab works only because it has the older `index.html`.

### F3. HIGH: the aftershock "chance of M5+" gauge is about 3.4× too high late in the sequence
- **Evidence (computed from USGS OAF `forecast.json`; model reproduced):** with the USGS parameters (a −2.1, b 1.0, p 1.1, c 0.00232), the model expects 1,280 M3+ in year one (observed 1,251), about 128 M4+ (observed 112) and **13.8 M5+ up to the forecast date (observed 4)**. For a Poisson mean of 13.8, P(N ≤ 4) = 0.21 %. My implementation matches USGS's own table: 1-day M5+ probability 1.9e-4 (USGS 1.86e-4); 1-year 5.7 % (USGS 6.1 %). So the formula is right and the fit is poor for M5. The observed b value between M4 and M5 is about 1.45 (n = 4, noisy), against the model's 1.0.
- **Repro:** `review/stress/claims.py`; the M5 numbers are in the OAF check in this report's source notes (formula `10^(a+b(Mm−M))·((t2+c)^(1−p)−(t1+c)^(1−p))/(1−p)`).
- **Fix:** keep the M3 and M4 gauges, which fit. For M5+, add the line "this model expected 13.8 and the sequence had 4; treat as an upper bound" (the audit already asked for an "M5 upper-bound note"; this is the number to quote). Or plot USGS's published 1-day, 1-week, 1-month and 1-year table as the gauge, with the label "fitted after the fact".

### F4. HIGH: the Blantyre "peak stage" is not the crest (matters for the planned per-gauge peak panel)
- **Evidence (measured, USGS IV in `data/raw/usgs_nwis/helene_iv_8gauges.json` and the flood meta):** French Broad at Blantyre (03443000) has no readings from index 258 to 312 (27 Sep 16:30 to 28 Sep 06:00 EDT) and again from index 320. The stage was still rising at 27.43 ft when the gauge dropped out. The app's maximum, 28.43 ft, is the first reading after the gap. USGS lists no 2024 annual peak for this site (`peak_03443000.rdb`). Two more gauges have gaps near the crest: Swannanoa (160 null values) and Ivy (88). The other five peaks match USGS annual peaks to within 0.05 ft (Swannanoa 27.33, Fletcher 30.46, Canton 26.96, Hot Springs 22.30, Celo 26.06; Ivy 28.15 vs 28.20; Asheville 24.67 vs 24.82 because the series is 15-minute).
- **Fix:** compute "peak" as "highest recorded", and write "gauge out 16:30 to 06:00; crest not recorded" for Blantyre. Do not compute time-to-crest for gauges with a gap that contains the rise or the maximum.

### F5. HIGH: the 3 MB per-fire budget is exceeded, and deep links add 0.97 MB
- **Evidence (measured, localhost, cache off, no gzip, `encodedDataLength`):** event folder sizes: Dixie 3.70 MB, August 3.40 MB (PLAN KPI says each fire ≤ 3 MB and "1.3 to 3.0 MB"). Every deep link also fetches `state.json` (972,318 B), even for Helene or Ridgecrest, which do not use it. Page load per event: Helene 2.32 MB, Drought 2.39 MB (before the failure), Ridgecrest 3.00 MB, Dixie 5.21 MB. Table at the end of this report.
- **Estimate (not measured):** on a 1.6 Mbit/s phone link, 5.2 MB takes about 26 s uncompressed. I did not test gzip on the real host.
- **Fix:** load `state.json` only for the Fires tab or the statewide view. Gzip or brotli the base64 text files on the host. Drop `hotspots.txt` for Dixie, August and Creek to half resolution, or send it after first paint.

### F6. MEDIUM: "Key moments" deep links cannot work as the plan assumes
- **Evidence (measured, `review/stress/hash_live.mjs`):** the hash is read once at boot (index.html line 1652). There is no `hashchange` listener. Changing `location.hash` to `#dixie@100` in an open page does nothing (the view stays "Statewide"). Clicking a tab does not write the hash, and `history.back()` does not change the view. A chip that sets `location.hash` would be dead, and the address bar never shows the current view, so people cannot share what they see.
- **Fix:** chips call `setT()` directly and update the URL with `history.replaceState`. Add a `hashchange` handler that routes through the same boot code.

### F7. MEDIUM: York is mostly imputed, and the README's "satellites overstate small fires" is false for it
- **Evidence (measured from `web/data/york/meta.json`):** raw VIIRS area 41,423 acres against 93,675 official (−56 %). `never_flagged_share` 0.604. `share_detected_before_arrival` 0.671. Eight 12-hour steps. Park is also low (−9 %). Eleven of 12 fires overstate, which is where the README claim comes from.
- **Impact:** the York fire line looks as measured as the others, but 60 % of its area takes the time of "the nearest flagged ground".
- **Fix:** show "60 % of this fire's timing is estimated" as an on-screen chip when `never_flagged_share` > 0.25. Reword the README claim to "most fires".

### F8. MEDIUM: simulated values appear without an on-screen label (labels live in collapsed `<details>`)
- **Evidence (code read):** the `Method and checks` blocks are `<details>` without `open`, and they hold the key honesty text:
  - Hurricane wind streaks and rings: "Wind field: modelled" (assumed r^-0.6 decay, 20° inflow). The legend line on screen mentions only "NHC best-track radii".
  - Rain layer: "ERA5 reanalysis, 25 km, local peaks smoothed".
  - Fire line between steps: "interpolated by distance".
  - Fire weather: "ERA5 ... not a station".
- Things that are labelled on screen: the flood overlay ("Illustrative flood overlay"), the water-table sheet (INTERPOLATED chip), the soil bucket (MODEL chip), the quake ring (Simulated).
- **Concrete case:** the rain note says "the largest total on the map grid is 362 mm". That equals the Asheville cell (14.3 in, 362.5 mm). The NWS Greenville-Spartanburg list (via search result, not opened in full) gives Busick 30.78 in (782 mm) for 24 to 28 Sep. ERA5 smooths the maximum by more than a factor of 2, and "largest on the map" reads as a measurement.
- **Fix:** one fixed badge per tab ("Modelled wind field", "ERA5 reanalysis, smoothed") visible without opening anything, and add measured station totals (NWS, Busick 30.78 in) as point markers.

### F9. LOW: smaller items
- Labels overlap at all sizes on the phone and on landscape (Chester/Westwood and Susanville/Johnstonville/Janesville in `shots/dixie_844x390.png`). The audit for Helene found the same.
- On 844×390 the header, the two tab rows and the slider take about 170 of 390 px, so the 3D view gets about 220 px (see `shots/dixie_844x390.png`).
- Reservoir extremes come from weekly samples: Shasta min 974,000 ac-ft on 19 Oct 2021 (daily raw: 967,400 on 21 Oct), Oroville min 788,100 on 21 Sep (daily raw: 787,700 on 1 Oct). The date is 10 days off for Oroville. "% of its 2020–23 high" uses the weekly maximum (Shasta 4.461 M vs daily 4.467 M). Say "weekly sample", or take extremes from the daily file.
- A missing `favicon.ico` logs a 404 (the selftest regex matches "failed", so it can produce a false FAIL).
- GNSS P595 shown 628.0 E / −250.9 N (676 mm). My raw recomputation with 3 Jul to 7 or 8 Jul windows gives 624.7 to 625.5 E / −248.2 N (672 to 673 mm): within 5 mm and dependent on the post-event window. State the window.

## Robustness results (measured)

- **Matrix:** 16 events × 3 sizes (1400×900, 844×390, 390×844) = 48 loads, using Chrome device emulation (real narrow `innerWidth`, mobile flag on the two phone sizes) rather than an iframe. 45 of 48 loads gave 0 console errors (the favicon 404 excluded). The 3 failures are all Drought (F2). No text contained `NaN`, `undefined`, `Infinity` or `[object` after scrubbing to 0, 50 and 100 %. No horizontal overflow at any size.
- **Bad inputs (16 hashes):** `#nonsense`, `#@`, `#__proto__`, `#constructor@5` all land on the statewide view with no error. `@-50` clamps to 0, `@1e9` clamps to the maximum (1416 h), `@abc` and `@NaN` give 0, `@100@200` gives 100. The HTML-injection hash did not execute (`window.__xss` stayed unset). `#ca-drought...` fails (F2).
- **Scrubbing:** 300 rapid input events plus the values `-5`, `1e9`, `NaN`, `abc` and empty on Ridgecrest: 1.6 s, no errors, no NaN text.
- **Rapid tab switching:** 91 clicks at 30 to 40 ms across hazards and events, with the broken Drought tab included. The page settled on the last tab clicked (Caldor), the overlay was hidden, and no exception was thrown. The `seq` guard in `showFire` works.
- **Memory:** JS heap after forced GC across three rounds of seven views: 5.8, 5.9, 6.1 MB, with 560 DOM nodes and 45 listeners each time. No leak seen in JS. **Not measured:** GPU and WebGL memory (the module hides `renderer`), and real-device behaviour.
- **Load time (localhost, cache off):** 0.87 to 2.8 s to the last network response (August is slowest at 2.8 s). On a real network this is dominated by the 3 to 5 MB (F5).

| event | folder MB | page load MB (incl. 0.97 state.json) | ready ms 1400 / 844 / 390 | errors |
|---|---|---|---|---|
| august | 3.40 | 4.90 | 2801 / 2215 / 1281 | 0 |
| creek | 2.55 | 4.06 | 910 / 869 / 872 | 0 |
| caldor | 1.91 | 3.41 | 871 / 866 / 874 | 0 |
| dixie | 3.70 | 5.21 | 1348 / 1295 / 1297 | 0 |
| monument | 2.76 | 4.26 | 1317 / 1281 / 1305 | 0 |
| mosquito | 2.21 | 3.71 | 1316 / 1298 / 868 | 0 |
| york | 1.53 | 3.03 | 866 / 1402 / 1195 | 0 |
| bridge | 1.95 | 3.45 | 1291 / 1224 / 1387 | 0 |
| park | 1.91 | 3.42 | 1248 / 1198 / 1034 | 0 |
| eaton | 2.15 | 3.65 | 1267 / 1447 / 1272 | 0 |
| gifford | 2.09 | 3.59 | 1274 / 1275 / 1233 | 0 |
| palisades | 1.98 | 3.48 | 1272 / 1276 / 1009 | 0 |
| helene | 0.82 | 2.32 | 1219 / 1348 / 1127 | 0 |
| helene-wnc | 2.17 | 3.67 | 1403 / 2443 / 1503 | 0 |
| ridgecrest | 1.50 | 3.00 | 2014 / 1212 / 1888 | 0 |
| ca-drought | 1.40 | 2.39 | failed | 12 |

## Claims spot-check (14 checks)

| # | Displayed value | Raw source | Result |
|---|---|---|---|
| 1 | 5,151 quake dots | `usgs_quakes/ridgecrest_m2_jul4_20.json`: 5,151 features | match |
| 2 | GNSS P595 628.0 E, −250.9 N, 676 mm | `ngl_gnss/tenv3_P595.tenv3` | within 5 mm; window-dependent (F9) |
| 3 | Helene peak 120 kt | HURDAT2 AL092024 | match |
| 4 | Helene min 939 mb | HURDAT2 | match |
| 5 | Landfall 03:10 UTC, 30.0 N 83.7 W, 120 kt, 939 mb | HURDAT2 "L" record | match |
| 6 | Dixie CAL FIRE 963,309 acres | `calfire/incidents_2021.json` | match |
| 7 | DSCI, 58 counties × 209 weeks | `usdm/county_*.json` | **12,122 of 12,122 exact** |
| 8 | Statewide D4 peak 48.97 % on 2021-08-17 | `stats` (area-weighted by the pipeline) | consistent with the audit's cross-check; no independent published figure found |
| 9 | 8 gauges' flood categories | `noaa_nwps/nwps_*.json` | 8 of 8 match |
| 10 | 8 gauges' peak stage | `usgs_nwis/peak_*.rdb` | 6 match, 1 close (Ivy), Blantyre not a crest (F4) |
| 11 | Asheville rain 14.3 in (ERA5 cell, 24 to 29 Sep) | NWS airport 13.98 in, 25 to 27 Sep (published, via search) | within about 2 %, different windows |
| 12 | OAF parameters a, b, p, c, counts 1251/112/4 | `usgs_oaf/oaf_ci38457511.json` | match |
| 13 | RJ model reproduces the USGS 1-day, 1-week, 1-month and 1-year M5+ probabilities | same file | match within 10 % |
| 14 | Reservoir min and max | `usgs_nwis/storage_*.json` | weekly samples, not true extremes (F9) |

**Not comparable, not counted as a pass:** the OAF counts are for the sequence up to 2026-09-03; my raw catalogue covers 4 to 20 July 2019.

**Honesty labels, tried to break:** I found no simulated number shown as measured in the code, but several modelled layers have their only label inside a closed `<details>` (F8), and York's timing is mostly estimated (F7).

## Decisions challenged

| # | Decision | Verdict | Evidence and alternative |
|---|---|---|---|
| D1 | One `index.html` for all hazards | **Change** | F1 is this decision failing: two hazards defined the same top-level name. The builder is about to add Key moments, summary and decision cards to five tabs in the same scope. Alternative: `engine.js` plus one module per hazard, loaded with `import()` on tab select (also lazy-loads shader code), or at minimum wrap each hazard in a block scope. Add a pre-publish `node --check` gate. EXTENDING.md already proposes the split for "the second user"; there are now four. |
| D2 | VIIRS rebuild as the independent timing check, plus the +12 h FEDS shift | **Change the check** | FEDS is itself built from VIIRS 375 m detections, so agreement with the project's rebuild tests the labelling convention, not the truth. The shift of 12 h leaves FEDS 1.7 to 3.0 h late; the unshifted gap is 8.9 to 10.2 h, so the fitted shift would be about 9.7 h. Both are small against 12 h steps. Alternative: use NIFC daily infrared perimeters for 2020–21 where they exist, as already done for Park (1.0 % median area difference, n = 68). |
| D3 | Reasenberg-Jones "what-if" clock | **Confirm the formula, change the M5 gauge** | Formula and units correct; reproduces USGS's table. Sequence-specific parameters were fitted in 2026, so "what a manager knew on day 1" is not shown. M5+ is 3.4× high (F3). Alternative: show the USGS table, or bin-specific empirical rates with a Poisson interval. |
| D4 | Soil-water "bucket" model (single layer, textbook SMAX 200 mm, KC 0.7, FC 0.5) | **Change** | The pipeline already downloads ERA5-Land soil moisture for 0 to 100 cm (`soil_moisture_0_to_100cm_mean`) and plans to compare against it. If the fit is poor, the bucket adds an unvalidated model next to a better-validated variable. Alternative: show ERA5-Land soil moisture itself (label MODEL, reanalysis) and keep the bucket only if the weekly correlation, per-week-of-year anomaly correlation and bias are printed in the app. I could not see those numbers (the build never completed). |
| D5 | "Key moments" chips as `#event@hours` links | **Change** | F6: no `hashchange` handler, tabs do not update the hash. Use `setT()` and `history.replaceState`. |
| D6 | "Reservoir storage as % of capacity with a historical-average line where the source gives one" | **Reduce** | USGS NWIS gives storage only. The historical-average source (CDEC) was unreachable in the scout (`ACTIONABLE_SCOPE.md`). The app already uses "% of its 2020–23 high", which is honest. Capacity (Shasta 4.552 M, Oroville 3.537 M ac-ft) would be new, cited constants. Do not use the record maximum as capacity: Shasta's is 4.467 M, below capacity. Skip the average line unless a downloadable source is found. |
| D7 | "Per-gauge peak stage and time-to-crest" | **Change** | F4: peak must mean "highest recorded" and exclude gauges with a gap around the rise. |
| D8 | "Fires: leave as they are" | **Partly change** | The 3 MB KPI is breached (F5) and York needs the estimated-timing chip (F7). |
| D9 | Hurricane "34/50/64-kt wind radii as quadrant shading if HURDAT2 has them" | **Already done** | The code uses the four-quadrant radii (`Wind field: modelled` note). The open task is the label (F8). |
| D10 | USDM "share of state in D2/D3/D4" | **Confirm, fix wording** | The values are cumulative (D2 means D2 or worse; `d0 ≥ d1 ≥ ... ≥ d4` in all rows, per the earlier audit). Label them "D2 or worse". The numbers already exist in `meta.stats`. |

## What I could not test

- A real iPhone or any real GPU (SwiftShader only), so frame rate, touch gestures and thermal behaviour are unknown.
- GPU memory growth across tab switches (renderer not reachable); only the JS heap was measured.
- Real-network load time and gzip behaviour on the host (localhost only).
- The Drought wells, bucket and GRACE layers, the Key moments strip, summary and decision cards, and all builder changes: none exist yet in the tested version.
- The ERA5 Busick figure was read from a search snippet, not from the NWS page. The NHC Tropical Cyclone Report and the "strongest landfalling hurricane in the Florida Big Bend since about 1900" wording were not checked directly.
- The 11 rupture rings and other quake fixes: some wording changes (7.4 s, "not shown to feed ShakeAlert") are present in the code, but I did not re-render the ring layer.
- Retest after the builder finishes: run `review/stress/run_matrix.mjs`, `run_abuse.mjs` and `hash_live.mjs` against a plain `http.server` (delete `patched_server.py` use once F1 is fixed).

## Files

`review/stress/`: `cdp.mjs` (Chrome driver), `run_matrix.mjs`, `run_abuse.mjs`, `hash_live.mjs`, `claims.py`, `patched_server.py`, `matrix.log` / `matrix.json`, `abuse.json`, `shots/` (PNG per event).
