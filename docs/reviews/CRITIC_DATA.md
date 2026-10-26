# CRITIC_DATA (data and claims gate), 2026-10-21

**Verdict: BLOCK.** Three items must be fixed before publishing (B1 to B3). The rest are small wording fixes.

Method: re-read raw files in data/raw and compared them with web/data/*/moments.json, meta.json and web/index.html. Web check: drought.gov (D4 share); USGS ComCat values come from the raw event details.

## Blockers
- **B1 (missing honesty label): the M5+ aftershock gauge.** index.html (lines 981-982, 1058) shows the modelled 24 h / 7 d / 30 d chance and "M5+ aftershocks so far in the catalogue" (rj-obs). There is no "upper bound" note and no model-versus-observed figure anywhere (grep for "upper" and "expected" finds nothing relevant). BUILD_REPORT says the page "already has the upper-bound note"; that is false. meta.oaf.obs gives 4 M5+ observed in the first year against 13.8 expected by the model (stress report F3, reproduced).
  Fix text, add after the existing note in the M5+ gauge: "For M5 and larger this model runs high for this sequence: it expected about 13.8 in the first year and 4 were catalogued. Treat the M5+ chances as an upper bound. The M3+ and M4+ counts fit (1,251 observed against about 1,280 expected for M3+; 112 against about 128 for M4+)."
- **B2 (unsupported sentence): Blantyre chip says "peaked".** helene-wnc/moments.json chip "Crest: French Broad at Blantyre" says "peaked at 28.4 ft ... 2024-09-28 at 07:00". The gauge has no readings 27 Sep 16:30 to 28 Sep 06:00; 07:00 is the first reading after the gap (177 null values in the series). The crest was not recorded. Fix text: label "Highest recorded: French Broad at Blantyre"; text "Highest recorded value 28.4 ft (major starts at 23.0 ft) on 2024-09-28 at 07:00 local. The gauge was out from 27 Sep 16:30 to 28 Sep 06:00, so the true crest is not known." Change the "Crest times, first to last" row to "Highest-reading times". Fix build_moments.py so any gauge with nulls near its maximum (Blantyre 177, Swannanoa 160, Ivy 88) gets "highest recorded" wording.
- **B3 (false label): York "measured (satellite)".** york/moments.json "Final area 379 km2 (93,675 acres, rasterised)" is tagged "measured (satellite)" and the chips cite "NASA FEDS/VIIRS satellite detections". meta shows raw VIIRS area = 41,423 acres, official = 93,078, iou_vs_official = 1.0, never_flagged_share = 0.604. So the final shape is the official perimeter and 60 % of its area is imputed. The chips "Half the final area (190 km2)", "90 % of final area" and "Most detections in one step" inherit this. The flag text is correct but sits in the panel only, not on the chips. Fix text: tag "official perimeter (93,078 acres), timed by satellite where seen"; chip source "Official perimeter, timed by NASA VIIRS detections (60 % of the area imputed)"; add "Satellite detections alone cover 41,423 acres". Flag wording: replace "filled in from the official perimeter" with "given the time of the nearest satellite-flagged ground inside the official perimeter (imputed)", to match the Method list (index.html line 1556).

## Claims checked
| # | Claim | Evidence | Verdict | Exact fix text |
|---|---|---|---|---|
| 1 | D4 first covers 1.2 % in week 2020-12-15 | meta.stats: d4 = 1.19 on 2020-12-15, first nonzero | OK | none |
| 2 | D3+ peaks 89 % (2021-07-27); D2+ 98 % (2022-05-24); D4 49 % (2021-08-17) | stats max: 88.59, 97.56, 48.97 on those weeks. County DSCI, area weighted. drought.gov reports 45.66 % D4 for California on 2021-09-14 (official, area based) | FIX (label) | Add "county-weighted estimate; the official state figure can differ by a few points (USDM reported 45.7 % D4 on 14 Sep 2021)". Source line should say "computed from county data" |
| 3 | D2+ is 0 % at 2023-12-26 | stats[-1].d2 = 0.0 | OK | none |
| 4 | Shasta 0.97 M acre-ft low, week 2021-10-19 | meta.reservoirs: 974,000 acre-ft at index 94 = 2021-10-19 | OK | none |
| 5 | Oroville 0.79 M acre-ft low, week 2021-09-21 | 788,100 acre-ft at index 90 = 2021-09-21 | OK (weekly sample, not the daily minimum) | Add "weekly value" |
| 6 | Median Central Valley well deeper than its 2020 level at end | wells.stats.medv_end = +14.7 ft from 18 valley wells; median of all 58 wells -0.27 ft; 47 % of wells lower | FIX (overgeneralised card) | Teaches text: "In the 18 Central Valley wells shown, the median level is still about 15 ft deeper than in 2020, although the Drought Monitor reads 0 % D2 or worse. Wells elsewhere are mixed." Say the wells were picked by farthest-point sampling, not at random |
| 7 | Wells MEASURED, sheet INTERPOLATED, bucket MODEL, GRACE modelled | Chips in index.html 764-777 and method 795-799; parameter 72019, ft below land surface | OK | none |
| 8 | Bucket vs ERA5-Land | r median 0.78 (p10 0.02, p90 0.93), state r 0.96; vs wells r = 0.13, stated in method | OK | none |
| 9 | GRACE "about 12 km", percentile vs 1948-2012 | 0.125 deg cells (11 to 14 km); SOURCES.md lists the gws_perc files | OK | Optional: "0.125 degrees (11 to 14 km)" |
| 10 | D3+/D4 chart | Label says dashed = D4 scaled to its own peak; values cumulative | OK | Keep "D2 or worse / D3 or worse" wording |
| 11 | M6.4 at 10.5 km, M7.1 at 8 km, 34 h apart | ComCat raw: 2019-07-04 17:33:49 UTC depth 10.5; 07-06 03:19:53 depth 8; gap 33.8 h | OK | none |
| 12 | ShakeMap peak MMI 8.3 (M6.4), 8.6 (M7.1) | ComCat event details: mmi 8.377 and 8.73 (8.4 and 8.7) | FIX (number) | "USGS ShakeMap peak intensity MMI 8.4" and "MMI 8.7", or "8.3 and 8.6 on the grid drawn here" |
| 13 | Largest shock after M7.1 is M5.5, 0.5 h later | raw: M5.5 at 03:47:53, 0.47 h after | OK | none |
| 14 | 2233 M2+ in first 24 h; 3811 in 7 days | raw count excluding the M7.1: 2232 and 3810; the app counts the M7.1 itself | FIX (off by one) | "2232 other shocks of M2 or more in the first 24 hours after the M7.1" and "3810 ... 7 days" |
| 15 | 5151 shocks; bands 4132/915/99/5; "5+" in first 24 h = 3 | Total 5151 OK. The 5+ band holds M6.4, 5.37, 7.1, 5.5, 5.44. The 24 h count of 3 includes the M7.1 | FIX (clarify) | "5 of M5 or more (includes the M6.4 and M7.1)"; "first 24 h: 2 aftershocks of M5 or more (3 counting the M7.1)" |
| 16 | Caption "Two earthquakes, 34 hours apart. Press play." | 33.8 h | OK | none |
| 17 | Teach card: "A few seconds of warning is enough to start drop, cover and hold on" | No source line; layer is a simulation | FIX (unsupported) | "A few seconds of warning can be enough to start drop, cover and hold on (ShakeAlert guidance). In this simulated what-if, towns closest to the epicentre get none." |
| 18 | Celo 26.1 ft and Hot Springs 22.3 ft; major 19.0 and 21.0 ft | Pipeline peaks 26.06 and 22.30; NWPS raw: Celo major 19, Hot Springs major 21, Blantyre major 23 | OK | none |
| 19 | Fletcher highest crest 30.5 ft; "8 of 8 above record" | Peak 30.46; stress report matched 5 gauges to USGS annual peaks within 0.05 ft | OK, with caveat (Blantyre, Ivy, Swannanoa have gaps) | "8 of 8 highest recorded values above the previous record" |
| 20 | Gauge gap note on cards | index.html line 1361: shown when nulls fall within 48 samples of the maximum | OK in card; chip contradicts it (B2) | none for card |
| 21 | York flag "60 % never seen by satellite" | never_flagged_share 0.604 | OK (number); wording differs from method (B3) | see B3 |
| 22 | York official area 93,078 acres | meta.calfire_acres 93078 (pipeline value, not re-fetched) | OK | none |
| 23 | Flood crest lag "26 to 47 h" (not shown in UI) | Mixed ERA5 rain and gauge | OK (hidden) | If shown later, exclude Blantyre |
| 24 | Aftershock model note ("fitted after the fact, created 2026-09-03") | meta.oaf a -2.1, b 1.0, p 1.1, c 0.00232 | OK | none |

## Other notes
- The M3 and M4 gauges fit the data. Only M5+ is off.
- Not verified: the official USDM weekly state D4 series (no archive reached from search); York acreage from CAL FIRE was not re-fetched.

## Round 2 (2026-10-21)

**Verdict: SHIP**. B1 to B3 and the six FIX items are applied; two small wording notes below are not blockers.

**Dispute 12.8 vs 13.8: both are correct, for different windows.** I integrated n = 10^(a+b(Mm-5)) * [(t1+c)^(1-p) - (t2+c)^(1-p)] / (p-1) with a=-2.1, b=1.0, p=1.1, c=0.00232, Mm 7.1:
- t = 0 to 365 d: **12.80** (365.25 d: 12.80). The builder is right for "first year".
- t = 0 to 2616 d (M7.1 to the OAF product date 2026-09-03, 7.2 years): **13.79**. This is the window the stress report used ("up to the forecast date"), so 13.8 was mislabelled as first-year in my first report.
- The page formula (index.html line 985) is the same integral and shows 12.8. Correct.

**Note N1 (wording, not a blocker).** The observed "4" in meta.oaf.obs comes from the USGS product (observations to the product date, 1-year forecast window), so it is a to-date count, not a first-year count. In the ComCat file only 2 M5+ shocks follow the M7.1 (M5.5, M5.44), both on day 1. The sentence "expected about 12.8 in the first year and 4 were catalogued" still holds as an upper-bound statement (first-year observed is at most 4), but the like-for-like pair is 13.8 expected against 4 observed, both up to 2026-09. Suggested text: "it expected about 12.8 in the first year (13.8 up to the forecast date) and 4 were catalogued up to that date."

| Item | Check | Result |
|---|---|---|
| B1 M5+ gauge note | index.html 985 "Upper bound for M5 and larger", computed expectation, M3+/M4+ fit line | OK (see N1) |
| B2 Blantyre | chip now "Highest recorded: ... the true crest is not known"; row "Highest-reading times"; "8 of 8" row reworded | OK |
| B3 York | chips and "Final area" tag read "official perimeter, timed by satellite"; 41,423 vs 93,078 acres note; flag wording matches Method | OK |
| MMI | 8.4 and 8.7 with "grid 8.3 and 8.6" | OK |
| Counts | 2232 and 3810, "M7.1 not counted"; band "includes the M6.4 and M7.1"; first-24 h 5+ = 2 matches raw | OK |
| D4 label | "county-weighted estimate; official about 46 % on 14 Sep 2021" | OK. Minor: the dl row tag still says "measured" for a county-weighted figure |
| Wells card | LESSONS_HTML says "of the 18 Central Valley wells shown (farthest-point sampling)" per builder; moments.json teach card still says "wells and groundwater lag" without the 18-well scope | OK, minor (add "in the Central Valley") |
| Warning card | Cites ShakeOut, still says "is enough" | OK, minor (prefer "can be enough") |
