# Independent data audit: CA Fire Years

Audited 2026-10-20. No project files were edited. Evidence is tagged: [measured] from the built files, [published] from a web source, [inferred] from reasoning.
Web access limits: fire.ca.gov returned HTTP 403 and the Nature article redirected to a cookie login, so CAL FIRE annual totals come via Wikipedia's table that cites the CAL FIRE incident archives.

## Verdict by item

| # | Item | Result |
|---|---|---|
| 1 | Fire notes | PASS for 6 of 7, with two wording nits |
| 2 | Timing realism | FAIL for the four FEDS fires (August, Creek, Dixie, Caldor); PASS for Park, Palisades, Eaton |
| 3 | Official acres | PASS for the CAL FIRE comparison; FAIL for the Dixie "official GIS acres" shown on the page |
| 4 | Statewide acres-per-year chart | FAIL (label misleading; real undercount) |
| 5 | Licences, citation | PASS with two corrections |
| 6 | Physical sanity | PASS (one suspicious land-cover share) |
| 7 | Other | see findings 5 to 11 |

## Findings ranked by severity

### 1. HIGH: FEDS-based fires run ahead of real time, by roughly 12 to 24 h

**Evidence A, Caldor and Grizzly Flats.**
- Wikipedia says Grizzly Flats was destroyed in the early morning of 17 Aug 2021. News reports say it burned overnight 16 to 17 Aug (https://en.wikipedia.org/wiki/Caldor_Fire).
- `web/data/caldor/arrival.bin` puts the Grizzly Flats cell at 45.5 h after t0. That is 2021-08-16 21:30Z, or 14:30 PDT on 16 Aug [measured].
- The first VIIRS detection within 1.5 km of the town is 2021-08-17 09:24Z, or 02:24 PDT. That matches the documentation [measured].
- So the replay shows the town burning about 12 h before any satellite saw fire there.

**Evidence B, Caldor area against reported acres.**

| Time | App | Reported |
|---|---|---|
| 17 Aug 05:00 PDT | 47,975 ac | about 6,500 ac (17 Aug morning update) |
| 17 Aug 17:00 PDT | 76,296 ac | about 30,000 ac (17 Aug evening update) |
| 18 Aug 07:00 PDT | not tabulated | 53,772 ac |

Sources are Wikipedia's growth table and the Sacramento Bee/CBS reports.

**Evidence C, Dixie.**
- Wikipedia's daily table gives 253,052 (3 Aug), 274,139 (4 Aug) and 322,502 (5 Aug). Verisk gives 432,813 on the morning of 6 Aug.
- The app shows 364,260 ac at 4 Aug 17:00 PDT and 453,761 ac at 5 Aug 05:00 PDT, about one day ahead.
- Greenville burned the evening of 4 Aug (Wikipedia, Plumas News, Wildfire Today 19:13 PDT). The app's cell arrival is 2021-08-04 18:00Z, or 11:00 PDT, so it is 6 to 9 h early.
- The step series is flat at 272,456 ac for 48 h (2 Aug 12Z to 4 Aug 12Z), then jumps by 91,804 ac and 89,501 ac. The spread-rate chart will show a dead stretch followed by two spikes.

**Evidence D, Creek.**
- The app shows 88,837 ac at 6 Sep 00Z (5 Sep 17:00 PDT). The 24 h and 36 h steps are identical (88,837).
- Reported: 36,000 ac on 5 Sep, about 45,500 on the morning of 6 Sep, 73,278 for 6 Sep (Wikipedia table, South Tahoe Now).
- Ignition 18:45 PDT on 4 Sep matches the app (discovery 01:33Z).

**Evidence E, systematic test.** For every burned cell with a stored VIIRS detection, I compared the cell's first detection with the end of its 12 h bin [measured]:

| Fire | Method | Cells whose first detection falls after their bin edge | Median lag |
|---|---|---|---|
| August | FEDS | 86 % | 10 h |
| Creek | FEDS | 94 % | 22 h |
| Dixie | FEDS | 89 % | 10 h |
| Caldor | FEDS | 97 % | 22 h |
| Park | VIIRS | 39 % | -1.7 h |
| Palisades | VIIRS | 50 % | 8 h |
| Eaton | VIIRS | 45 % | -2 h |

- The FEDS fires mark cells burned before the first VIIRS detection there. The VIIRS-built fires do not show this.
- Most likely cause [inferred, not confirmed]: the FEDS `t` field is read as the end of a 12 h window, but it behaves like the start. `feds_spread` in `pipeline/build_fire.py` treats `t <= edge` as burned by the edge.
- I could not fetch the FEDS timestamp definition to confirm. NASA's ArcGIS layer metadata (veda_public_eis_fire_lf) lists `t_st` as a display field, which hints at a start time.
- The `gate_timing: true` flag in `validation.json` does not test absolute time. Its mid-fire IoU of 0.88 to 0.96 compares two same-indexed reconstructions.

**Suggested fix.** Shift FEDS step times by +12 h (or use the next 12 h edge), then re-run the Caldor and Dixie checks above. Until then, state "timing within a day" for the 2020 and 2021 fires.

### 2. HIGH: the "Acres burned per year" chart undercounts

`web/data/state.json` `acres_by_year` is the sum of `AcresBurned` over CAL FIRE incident-list rows with `Type` null or "Wildfire". The CAL FIRE incident list is not all jurisdictions.

| Year | App | CAL FIRE archive (via Wikipedia) | App as share of CAL FIRE |
|---|---|---|---|
| 2020 | 2,941,860 | 4,397,809 | 67 % |
| 2021 | 2,069,258 | 2,568,948 | 81 % |
| 2022 | 277,502 | 362,455 | 77 % |
| 2023 | 322,947 | 324,917 | 99 % |
| 2024 | 1,025,596 | 1,050,012 | 98 % |
| 2025 | 527,607 | 525,223 | 100 % |

Causes [measured in `data/raw/calfire/incidents_*.json`]:
- The 2020 list has 259 rows against 9,639 fires in the annual statistics. It lacks federal-jurisdiction fires such as North Complex, Slater, Castle, Dolan, Bobcat and Red Salmon. Those perimeters are in the WFIGS data on the same page.
- The `Type` filter drops 18 rows labelled "Fire" in 2021, worth 220,556 ac, including McFarland at 122,653 ac. It also drops 8 rows in 2022.
- Rows without a latitude are dropped.

The label "Sum of acres on the CAL FIRE incident list" is literally true. The title "Acres burned per year" is misleading, because a reader will compare it with the 4.3 to 4.4 M acres widely reported for 2020.

**Suggested wording.** Title: "Acres on CAL FIRE-listed wildfire incidents". Footnote: "Counts only incidents on the CAL FIRE incident list. Federal-jurisdiction fires are mostly missing, so 2020 to 2022 fall below statewide totals (CAL FIRE all-jurisdiction: 2020 about 4.4 M, 2021 about 2.6 M acres). 2026 is year to date."

**Better fix.** Remove the `Type` filter, or accept "Fire", and chart the all-jurisdiction totals from the CAL FIRE statistics page, citing them.

### 3. MEDIUM: the August Complex never appears as the largest fire in the statewide view

- The statewide "Largest in selection" list is built from WFIGS parts (`pipeline/build_state.py`).
- The 2020 entries are "Doe 589,835" and "Hopkins 328,363", not "August Complex 1,031,997".
- With "All years" selected, the top of the list is Dixie 963,309, then Doe 589,835. This sits next to the August note "Largest wildfire in California's recorded history".
- The 3D list uses 1,031,997, which comes from summing parts. CAL FIRE's figure is 1,032,648 (confirmed by Wikipedia).
- Fix: merge the August parts into one entry in `state.json` perimeters, or label the parts.

### 4. MEDIUM: Dixie "official GIS acres" 968,397 double counts the Fly Fire

- `validation.json` sums parts: Fly 5,088 + Dixie 963,309 = 968,397.
- The union area of the same polygons (`albers_acres`) is 963,406. So Fly lies inside Dixie and the sum overcounts [measured].
- The state-tab button says "Dixie Fire, 2021 · 968,397 acres (official perimeter)". The map tooltip and CAL FIRE both say 963,309. The 3D "Method and checks" line also prints 968,397.
- The raster's 973,502 ac equals the union of the polygons (+1.05 % projection factor), so it is not an error.
- Fix: use the union area, or `calfire_published_acres`, for `featured.acres` and `official_gis_acres`.

### 5. MEDIUM: the "discovered" date is a UTC date

- The map tooltip shows Eaton as discovered 2025-01-08. It ignited on the evening of 7 Jan (18:18 PST).
- Dixie shows 2021-07-14 (CAL FIRE says 13 Jul), Creek 2020-09-05 (ignition 4 Sep 18:45 PDT), Caldor 2021-08-15.
- CAL FIRE's own `StartedDateOnly` carries the same UTC dates, so the tooltip is not copying a CAL FIRE error, but readers will see it as one.
- Fix: convert to America/Los_Angeles, or label the date "UTC".

### 6. MEDIUM-LOW: Park early-phase area error

- Against 68 NIFC infrared perimeters, the median absolute difference is 1.05 %. That is a good result.
- The first rows are +19 % (25 Jul 19:30Z: 71,489 official, 85,118 app) and +11 % (26 Jul).
- 27 to 28 Jul runs -7 % to -10 %.
- The README and `gate_timing` summary should quote the range, not just the median.

### 7. LOW-MEDIUM: citation and credits corrections in `pipeline/make_sources.py`

- DOI 10.1038/s41597-022-01343-0 resolves (302 to nature.com/articles/s41597-022-01343-0). It is Chen et al. 2022, "California wildfire spread derived using VIIRS satellite observations and an object-based tracking system", Sci Data 9:249, open access under CC BY. The citation is correct. PASS.
- The credit text says "perimeters for 2018-2021 fires (Chen et al. 2022)". The paper's dataset covers 2012 to 2020 fires. Dixie and Caldor (2021) come from the NASA/VEDA FEDS archive, not from the paper.
- Suggested text: "FEDS algorithm described in Chen et al. 2022; 12-hourly perimeters served by NASA VEDA."
- Open-Meteo: the data licence is CC BY 4.0, but the free API is for non-commercial use only. Add "free API is for non-commercial use".
- Licence statements for the other sources:
  - NASA FEDS, NASA FIRMS: open with a request to acknowledge FIRMS/LANCE. The "no restrictions" wording could not be confirmed from NASA's policy page [UNVERIFIED]. Add the FIRMS acknowledgement text.
  - NIFC WFIGS, NLCD and Census TIGER: public domain. Consistent with agency statements.
  - OSM: ODbL 1.0, correct.
  - AWS Terrarium: attribution to the source providers, correct.
  - CAL FIRE incident list: "State of California public information" [UNVERIFIED]. The endpoint (`incidents.fire.ca.gov/umbraco/api/IncidentApi/List`) is undocumented, and I found no stated licence.

### 8. LOW: wording nits in `pipeline/fires.py` notes

- August: Wikipedia's lead says 38 fires, its infobox says 37. Use "about 38".
- Eaton: "on the same night as Palisades" is loose. Palisades started at 10:30 PST on 7 Jan, Eaton at 18:18 PST. Use "the same windstorm" or "that evening".
- Dixie "largest single (non-complex)": consistent with CAL FIRE's list, where the August Complex is #1 and Dixie #2. Wikipedia's August article calls the Doe Fire the single largest at the time. PASS with that nuance.
- Creek: ignition 6:45 pm PDT 4 Sep. The USFS dead-tree figure of 80 % mortality in the footprint is via Wikipedia. Mammoth Pool: about 207 to 214 airlifted, 5 to 6 Sep. PASS.
- Caldor: crossed the Sierra crest 30 Aug; South Lake Tahoe evacuated 30 Aug 10:59 (Wikipedia). PASS. Dixie crossed first (18 Aug), so "crossed the Sierra crest" is not unique.
- Park: started about 2:44 pm PDT 24 Jul, Upper Bidwell Park, Butte County, arson. The app's discovery 21:52Z (14:52 PDT) is 8 min later than the Wikipedia time, which is fine. PASS.
- Palisades: 10:30 PST, 23,448 ac, 12 deaths. Eaton: 18:18 PST, 14,021 ac, 19 deaths. PASS.

### 9. LOW: land-cover share for the August Complex

- Burned classes sum to the final area for every fire (August 4211.9 vs 4211.87 km2, Creek 1550.1, Dixie 3939.6, Caldor 903.2, Park 1746.4, Palisades 95.6, Eaton 57.2). PASS.
- August shows "developed" at 210.7 km2 (5 %), against 0.9 % for Dixie. That is odd for the Mendocino/Shasta-Trinity wilderness. The class group includes NLCD 21 "Developed, open space" (`GROUPS` in `build_fire.py`). Likely road corridors and misclassified open space. [UNVERIFIED]
- Also `agriculture` is exactly 0.0 for five fires, which looks like a mapping gap, not a measurement.

### 10. LOW: page weight

- Built `web/data` is 14.05 MB [measured] against the PLAN KPI of at most 8 MB (largest: tex.webp 1.27 MB, hotspots.bin 1.0 MB, state.json 0.96 MB).
- State this as "KPI not met", or compress.

### 11. LOW: cosmetic

- The `.title()` call mangles names: "Mcfarland", "Mccash".
- The statewide 2026 hotspot chart ends in 2025 because FIRMS 2026 was unavailable, while the acres chart includes 2026.
- The WFIGS statewide query has no incident-type filter. The header "Every final fire perimeter over 1,000 acres" and "wildfire incidents" may include prescribed burns. [UNVERIFIED]

## Item 2 detail: town arrival times

Local time: PDT is UTC-7, PST is UTC-8. Arrivals are cell values from `arrival.bin` [measured].

| Fire / place | Documented | App arrival | Verdict |
|---|---|---|---|
| Dixie / Greenville | evening 4 Aug 2021 | 4 Aug 18:00Z = 11:00 PDT | early by about 6 to 9 h, FAIL-marginal |
| Caldor / Grizzly Flats | early morning 17 Aug | 16 Aug 21:30Z = 14:30 PDT | early by about 12 h, FAIL |
| Creek / Big Creek | origin area, 4 to 5 Sep | 5 Sep 11:00Z = 04:00 PDT | plausible, first detection 09:12Z |
| Creek / Shaver Lake | threatened, not destroyed | unburned (65535) | consistent |
| Park / Cohasset | 25 Jul | 26 Jul 02:54Z = 25 Jul 19:54 PDT | plausible |
| Park / Forest Ranch | 25 to 26 Jul | 26 Jul 11:12Z = 04:12 PDT | plausible |
| Eaton / Altadena (city centroid) | east Altadena evening 7 Jan, west Altadena about 03:00 PST 8 Jan | 8 Jan 11:48Z = 03:48 PST | plausible for the centroid, 12 h bins |
| Eaton ignition | 18:18 PST | discovery 02:18:47Z = 18:18 PST | PASS |
| Palisades ignition | about 10:30 PST | 18:30Z = 10:30 PST | PASS |

Growth shares [measured]:
- Palisades: 66 % of the final area by 24 h, 75 % by 36 h.
- Eaton: 83 % by 24 h, 89 % by 36 h.
- Park: 53,446 ac at 25 Jul 12Z, with 68 NIFC infrared matches.
- The Palisades "most growth in first 24 to 36 h" claim holds. The 17,234 ac by 23:10 on 8 Jan matches the app's 17,663 at 36 h.

## Item 3: acres, validation.json against CAL FIRE

| Fire | `calfire_published_acres` | Public figure | App raster | Verdict |
|---|---|---|---|---|
| August Complex | 1,032,648 | 1,032,648 | 1,040,774 (+0.8 %) | PASS |
| Creek | 379,895 | 379,895 | 383,030 (+0.8 %) | PASS |
| Dixie | 963,309 | 963,309 | 973,502 (+1.05 %) | PASS (see finding 4) |
| Caldor | 221,835 | 221,835 | 223,185 (+0.6 %) | PASS |
| Park | 429,603 | 429,603 | 431,554 (+0.5 %) | PASS |
| Palisades | 23,448 | 23,448 (CAL FIRE's destruction list shows 23,707) | 23,618 (+0.7 %) | PASS |
| Eaton | 14,021 | 14,021 | 14,125 (+0.7 %) | PASS |

The raster areas use the mercator-corrected cell area. The 0.5 to 1.1 % excess over the equal-area polygon area (`extent_ratio`) is the grid's rasterisation, within the ±2 % gate. The app uses its own raster area in the KPIs and the official perimeter area in the lists. Both are labelled. PASS.

## Item 6: physical sanity

- km2 to acres factor 247.105 is correct, and the arrival raster area matches the step area within 0.2 % (Dixie 3931.4 vs 3939.6 km2).
- DEM min/max against terrain (mesh, metres):

| Fire | zmin to zmax | Check |
|---|---|---|
| August | 61 to 2,356 | plausible (Yolla Bolly peaks) |
| Creek | 163 to 3,898 | plausible (Sierra crest) |
| Dixie | 122 to 3,117 | Lassen Peak is 3,187 m; the downsampled mesh smooths it |
| Caldor | 365 to 3,257 | plausible (Freel Peak 3,317 m) |
| Park | 34 to 2,792 | valley floor to Lassen foothills |
| Palisades | 0 to 847 | sea level to Santa Monica Mountains |
| Eaton | 128 to 1,865 | San Gabriel front range |

- ERA5 weather (UTC, hourly; point is the burned-area centroid):

| Fire | Gust max (km/h) | RH min | Temp range | Verdict |
|---|---|---|---|---|
| Eaton | 117.7 at 8 Jan 07Z (23:00 PST on 7 Jan) | 6 % | 6 to 19.5 C | below the 160 km/h at Mt Lukens, as expected for a reanalysis |
| Palisades | 86.0 | 6 % | 6 to 20.9 C | plausible |
| Creek | 101.5 on 26 Oct | 4 % | -1.9 to 35.2 C | plausible, the window runs into December |
| Park | 73.8 | 4 % | 12.8 to 38.3 C | plausible |
| Dixie | 51.8 | 4 % | 10.9 to 37.7 C | plausible |
| Caldor | 63.7 | 9 % | 3.9 to 34.4 C | plausible |

All values are plausible. The page says "a ~10 to 30 km grid, not a station". That is honest.
