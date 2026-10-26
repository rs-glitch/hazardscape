# Actionable scope: Earthquakes and Drought tabs

Probed 2026-10-20/21 from Windows Git Bash, Python 3.14 + requests. Probe scripts: scratchpad `probe.py`, `p2.py` ... `p11.py`.
Tags: **V** = I downloaded a sample and parsed it (HTTP 200). **R** = read-only (found in metadata or docs, download not confirmed). **X** = excluded (login, blocked, or unreachable).
"Measured / simulated / estimated" tags follow the Facts rule.

## 0. Source status board (what actually worked)

| Source | Result |
|---|---|
| USGS ComCat event JSON `https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&eventid=ci38457511` | V, 156 KB, lists every product URL below |
| Product files are served from `https://earthquake.usgs.gov/product/...` with a **version-stamped path** taken from the event JSON. Guessing `.../us/1/...` gives 403 AccessDenied. Always read the URL from `properties.products`. | V |
| DYFI, OAF, ground-failure, PAGER, ShakeMap, finite-fault files | V (details below) |
| IRIS FDSN station `https://service.iris.edu/fdsnws/station/1/query?net=CI&...&format=text` | V |
| NCEDC FDSN station `https://service.ncedc.org/fdsnws/station/1/query?net=BK&level=station&format=text` | V |
| USGS new Water Data OGC API `https://api.waterdata.usgs.gov/ogcapi/v0/collections/{field-measurements,monitoring-locations,daily}/items` | V |
| **Legacy NWIS `waterservices.usgs.gov/nwis/gwlevels` is decommissioned** (returns a blog page). `nwis/dv` and `nwis/stat` still answer. | V (negative) |
| NASA GRACE Drought Indicator, `nasagrace.unl.edu/data/YYYYMMDD/...tif`, no login | V |
| NRCS AWDB REST (SNOTEL) `wcc.sc.egov.usda.gov/awdbRestApi/services/v1/data` | V |
| Open-Meteo archive (ERA5 / ERA5-Land) | V |
| US Drought Monitor county CSV `usdmdataservices.unl.edu/api/CountyStatistics/...` | V |
| DWR GWL "recently measured" FeatureServer (latest value per well only) | V |
| CGS liquefaction / landslide zones on `services2.arcgis.com/zr3KAIbsRSUyARHG/...` | V (counts only) |
| NGL GNSS `https://geodesy.unr.edu/gps_timeseries/IGS14/tenv3/IGS14/CCCC.tenv3` | V, 1.7 MB |
| OSM Overpass (hospitals/schools) | V (count query) |
| **`data.cnra.ca.gov/.../download/*.csv`** (DWR periodic GWL, dry-well reports, DWR CGPS displacement, TRE Altamira points) | **X: Cloudflare 403 from Python and curl**, even with browser UA and Referer. CKAN metadata on `data.ca.gov/api/3/action/package_show` works (V), the file hosts do not. A user-side manual browser download could unblock them. |
| DWR `gis.water.ca.gov` (TRE InSAR image service) | X: connection fails |
| CDEC `cdec.water.ca.gov` | X: connection fails (as expected) |
| `gis.conservation.ca.gov` "SeismicHazardZones" service | X: token required. Use the data.ca.gov / services2.arcgis.com mirror instead. |
| HIFLD hospitals (ArcGIS) | X: URLs return Invalid URL (HIFLD open data is gone). Use OSM. |
| NASA ARIA DPM, GRACE-FO mascons (JPL/PO.DAAC), SMAP | X: login or unreachable. GRACE through the Nebraska drought-indicator mirror replaces it. |

## 1. EARTHQUAKES (Ridgecrest M7.1, 2019-07-06 03:19:53 UTC, ci38457511)

Verified product URLs (read the stamp from the event JSON; stamps today):
- DYFI: `.../product/dyfi/ci38457511/us/1785244957753/{dyfi_zip.geojson (569 KB), dyfi_geo_10km.geojson (1.1 MB), dyfi_geo_1km.geojson (9.8 MB), cdi_geo.txt (110 KB)}`
- OAF: `.../product/oaf/ci38457511/us/1788406203671/forecast.json` (15 KB)
- Ground failure: `.../product/ground-failure/38457511/us/1609800308114/{info.json (6 KB), jessee_2018_model.tif (26 MB), zhu_2017_general_model.tif (0.6 MB), godt_2008_model.tif (44 KB)}`
- PAGER: `.../product/losspager/ci38457511/us/1562429005114/json/{exposures,losses,cities}.json`
- ShakeMap (atlas): `.../product/shakemap/ci38457511/atlas/1594160054783/download/{stationlist.json (14 MB), rupture.json (4.7 KB), grid.xml, raster.zip}`
- Finite fault: `.../product/finite-fault/us70004bn0/us/1562395252786/FFM.geojson` (486 KB)
- Licence for all USGS products: US Government work, public domain.

### Candidates

**E1. Warning-time map (ShakeAlert-style "seconds you would have")**
- Lesson: facility managers (rail, hospitals, schools, factories) and residents decide what can be done in N seconds. Drop-Cover-Hold needs about 2 s; slowing a train, opening fire-station doors, pausing surgery or gas shutoff need 5 to 20 s. The map shows where those actions are possible and where the "blind zone" is.
- Visual: the existing 3.5 km/s S-ring keeps expanding. Add a P ring (about 6 km/s), a "alert issued" moment, and colour the terrain by seconds-of-warning when the S ring reaches each cell (green over 10 s, amber 3 to 10 s, red under 3 s, grey blind zone). Station pillars light when P reaches them. A slider sets alert latency. Chart: warning seconds versus distance with action bars (DCH, train brake, surgery).
- Data: station locations V (IRIS: 92 CI stations with HN/HH channels near Ridgecrest on 2019-07-01; 2,069 lines for CI+BK+NC statewide, 9 KB to 120 KB). Epicentre, depth, origin time V (ComCat). ShakeMap `stationlist.json` V gives the stations that actually recorded (PGA, PGV, distance).
- Simulated vs measured: all timing is **simulated**; stations and event are measured.
- Formula: `t_P4 = 4th-nearest-station P time = d4/Vp`; `t_alert = t_P4 + t_proc + t_tele` (assume 4 s + 1 s, estimated; ShakeAlert's published goal is "a few seconds"); `warning(x) = hypo_dist(x)/Vs - t_alert`. Vp 6.0, Vs 3.5 km/s (crust, estimated, matches the existing 3.5 km/s ring). About 40 lines of NumPy.
- Honesty label: "Illustrative what-if. ShakeAlert was not yet public in Los Angeles in July 2019. Times use assumed 5 s alert latency and uniform wave speeds; real alerts vary by station geometry and event."
- Effort: **S**. Rank: **1** (it re-uses the ring already in the app and teaches a decision).

**E2. Aftershock forecast clock (probability of M5+ shrinks with time)**
- Lesson: emergency managers and building officials decide when to reopen damaged structures, lift evacuations, and hold crews in the field. The curve shows risk dropping from percent-per-hour toward weeks.
- Visual: scrub the time slider; the 5,151 aftershock points (already in the app) keep appearing, and a gauge shows "chance of at least one M5+ in the next 24 h / 7 d / 30 d" computed at that moment. Chart: Omori rate curve with observed daily counts as dots, forecast fan.
- Data: aftershock catalogue already baked. Parameters V from `forecast.json`: `a=-2.1, b=1.0, p=1.1, c=0.00232, Mmain 7.1, Mcat 3.0, circle r=60 km at (35.808, -117.625)`. Observed counts in file: M3+ 1251, M4+ 112, M5+ 4 (sequence to date).
- Simulated vs measured: events measured; probabilities **computed** by the Reasenberg-Jones form `lambda(t,M) = 10^(a + b(Mm - M)) (t + c)^-p`, `P = 1 - exp(-integral over [t1,t2])`. Closed form for p != 1. 15 lines.
- Honesty label: "Statistical forecast fitted to this sequence after the fact (USGS OAF parameters). Not a prediction of any single earthquake. At the time, USGS issued 7-day forecasts with generic parameters."
- Effort: **S**. Rank: **2**.

**E3. "Did You Feel It?" vs ShakeMap, the felt-versus-modelled gap**
- Lesson: shows emergency responders where modelled shaking and human reports disagree, i.e. where to send assessment teams and where crowdsourced reports should be trusted first. Also teaches that reports arrive fast (minutes) while instruments are sparse.
- Visual: DYFI points (height = intensity CDI, colour = CDI minus ShakeMap MMI) appear in time order over the existing MMI surface; residual map. Chart: response count versus minutes after origin (that time series sits in `dyfi_plot_numresp.json`, 2.7 MB V).
- Data V: `dyfi_zip.geojson` points with `cdi, nresp, dist, population` (e.g. 93562 CDI 8.3 at 25 km), `cdi_geo.txt` with UTM box, CDI, count, lat, lon, city. Licence public domain. Period: the 2019 event; responses cover days after.
- All **measured**; only the residual is computed.
- Honesty label: "Self-reported felt intensity; clustered where people live, so empty areas are blank, not calm."
- Effort: **S**. Rank: **4**.

**E4. Ground failure: liquefaction and landslide hazard on the terrain**
- Lesson: planners, lifeline operators, and county building departments choose which roads, canals, pipelines and slopes to inspect first. Ridgecrest is mostly desert, so it also teaches the "low hazard" case.
- Visual: draped colour layer on the block (probability), toggle landslide / liquefaction; overlay the CGS Seismic Hazard Zone polygons as outlines.
- Data V: ground-failure GeoTIFFs (Jessee 2018 landslide model 26 MB, Zhu 2017 liquefaction 0.6 MB, Godt 2008 44 KB; `info.json` gives alert level: landslide hazard yellow, aggregate 6.4 km2, population exposure 1 person). CGS statutory zones: `https://services2.arcgis.com/zr3KAIbsRSUyARHG/arcgis/rest/services/CGS_Liquefaction_Zones/FeatureServer/0/query` (2,034 polygons statewide, 0 in the Ridgecrest box) and `CGS_Landslide_Zones/FeatureServer/0` (41,769 polygons). Licence: USGS public domain; CGS CC-BY.
- Measured/modelled: USGS grids are **modelled** products (V); I add nothing.
- Honesty label: "USGS empirical ground-failure model, 2021 run. Probability of ground failure, not a map of observed damage."
- Effort: **M** (reproject tif, clip). Rank: **5**. Weak for Ridgecrest because zone counts are zero there; stronger for a Bay Area/LA scenario (needs a ShakeMap scenario, not verified).

**E5. Ground displacement: GNSS offsets and surface rupture**
- Lesson: surveyors, pipeline and rail owners, and utilities learn how much the ground actually moved across the fault, hence how far to re-survey and which alignments to inspect.
- Visual: GNSS station arrows jump at the mainshock moment (scaled, with a legend); rupture trace from `rupture.json` and CGS rupture mapping layer.
- Data V: NGL daily time series `https://geodesy.unr.edu/gps_timeseries/IGS14/tenv3/IGS14/CCCC.tenv3` (1.7 MB per station). Parsed: station CCCC north coordinate steps from 0.894 m (4 Jul 2019) to 1.109 m (7 Jul), about 0.21 m north. 16 stations within the box from `https://geodesy.unr.edu/NGLStationPages/llh.out` (1 MB, longitudes may be 0 to 360). Licence: NGL data free with citation (R on exact terms).
- **Measured**.
- Honesty label: "Daily GNSS positions, IGS14 frame, arrows exaggerated 1000x."
- Effort: **M**. Rank: **3**. Teaches amount of slip, but "who acts" is narrow (surveyors/lifelines).

**E6. Exposure: what was inside the shaking (people, hospitals, schools, lifelines)**
- Lesson: hospital and school administrators, utilities, and county emergency managers see how many facilities sat above MMI 6 and so need inspection first.
- Visual: facility pins pop up in the order the S ring reaches them, coloured by local MMI from the ShakeMap grid; running tally chart "people exposed by MMI". PAGER exposure V: population by MMI 1..10 = 0, 10.6 M, 17.9 M, 21.5 M, 0.60 M, 1,721, 44,915, 200, 0, 0 (MMI 7 about 45,000 people; this array is as published, note the MMI 6 and 7 values look non-monotone and need re-checking before display).
- Data: OSM Overpass `https://overpass-api.de/api/interpreter?data=[out:json];nwr[amenity~"hospital|school"](35.0,-118.5,36.5,-116.5);out center;` V (count query only; needs a `User-Agent`; ODbL). Roads and pipelines via OSM `highway`, `man_made=pipeline`. No building-age field; skip building-age vulnerability (not verified, not free in bulk).
- Measured positions, modelled MMI. Effort **M**. Rank: **6** (Ridgecrest is sparse; better as a LA scenario).

**E7. Station-density "who would hear it first" (network sensor view)**
- Lesson: network operators and legislators see where adding stations buys seconds. Drops out of E1 as a toggle: add a hypothetical station set and recompute warning.
- Effort **S** on top of E1. Not ranked separately.

**E8. Building-age vulnerability / DYFI-to-damage**: not verified. No open bulk building-age layer was found in this pass (R). Skip.

### Top 3 for Earthquakes
1. **E1 warning-time map** (S). 2. **E2 aftershock probability clock** (S). 3. **E5 GNSS offsets + rupture** (M), or E3 if the user prefers the cheaper S build. E4 and E6 are better for a scenario that is not a desert.

## 2. DROUGHT (California 2020 to 2023)

Verified sample facts:
- USGS OGC field measurements: `https://api.waterdata.usgs.gov/ogcapi/v0/collections/field-measurements/items?f=json&parameter_code=72019&bbox=-122.5,35,-118,40&time=2020-01-01/2023-12-31&limit=1000` returns 1,000 records (1.2 MB per page; paged with `next` links). Record: `monitoring_location_id USGS-363645119420701, value 92.16 ft below land surface, time 2021-08-25`. Licence: USGS public domain.
- USGS site metadata: `.../collections/monitoring-locations/items?f=json&state_code=06&site_type_code=GW`.
- USGS daily streamflow V: `.../collections/daily/items?f=json&monitoring_location_id=USGS-11303500&parameter_code=00060&time=2021-01-01/2021-01-05` (Stanislaus, 1000 ft3/s on 2021-01-02). Legacy `nwis/stat` monthly percentiles V (46 KB per site).
- DWR GWL "recently measured" (latest only): `https://services.arcgis.com/aa38u6OgfNoCkTJ6/arcgis/rest/services/GWL_Recently_Measured_v3/FeatureServer/0/query?where=1=1&outFields=*&f=geojson` V, 8,381 wells, fields `WELL_DEPTH, TOP_PRF, BOT_PRF, LAST_GWE, LAST_GSE_GWE, LAST_MSMT_DATE`; page size 2,000. Gives well depth and screen interval, so the well-screen drawing is real. No history here.
- NASA GRACE Drought Indicator V: `https://nasagrace.unl.edu/data/20200106/gws_perc_0125deg_US_20200106.tif` (0.125 deg, 464x224, float32, percentile 0 to 100, nodata -999, opens with PIL, 300 KB). Also `sfsm_perc_...` (surface soil moisture) and `rtzsm_perc_...` (root zone). 1,281 weekly folders from 2002-04-01 to 2026-10-19. Layers are GRACE-assimilated Catchment model output from the University of Nebraska; public. Cell size is about 12 km, so California is about 40 x 40 cells.
- SNOTEL V: `https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1/data?stationTriplets=*:CA:SNTL&elements=WTEQ&duration=DAILY&beginDate=2021-04-01&endDate=2021-04-01` returns all California stations in one call. Station metadata `.../stations?networkCds=SNTL&stateCds=CA`. Public domain.
- Open-Meteo ERA5 archive V: `https://archive-api.open-meteo.com/v1/archive?latitude=36.7&longitude=-119.8&start_date=2020-01-01&end_date=2023-12-31&daily=precipitation_sum,et0_fao_evapotranspiration&timezone=auto`, with `hourly=soil_moisture_0_to_7cm,soil_moisture_28_to_100cm` also V. Licence CC-BY 4.0 (non-commercial free tier; fair-use limits, batch and cache).
- USDM county CSV V (`usdmdataservices.unl.edu/api/CountyStatistics/GetDroughtSeverityStatisticsByAreaPercent?aoi=06019&startdate=1/1/2021&enddate=1/31/2021&statisticsType=1`; already in the app as DSCI).

### Candidates

**D1. Groundwater "sensor wells": water-table surface and a cross-section**
- Lesson: farmers, water districts and GSA managers decide when to pump less, where to deepen wells, and which domestic wells are at risk. Seeing the table fall under valley wells while mountains stay wet shows why dry wells appear after a lag.
- Visual: well pillars (height of water column = well depth minus depth-to-water) with a moving water line; a semi-transparent water-table sheet interpolated (IDW / natural neighbour) under the terrain; a slice plane showing percolation depth versus screen intervals; wells whose water level falls below the screen top turn red ("at risk of going dry"). Chart: hydrograph of the selected well beside DSCI.
- Data: history from USGS OGC field-measurements (V; manual measurements, typically 1 to 4 per year, so use seasonal stepped lines, not daily), depth from DWR FeatureServer (V). The DWR periodic GWL CSV (about 70 MB? size unknown) is X from here (Cloudflare 403). Coverage on USGS side for 2020 to 2023: bbox page of 1,000 records returned for the central valley alone, so a few hundred wells is realistic (count not yet measured).
- **Measured** at the wells, **interpolated** between them. Formula: IDW power 2, 12 nearest wells, masked to alluvial basins only (otherwise the sheet claims water under mountains).
- Honesty label: "Water levels are manual field measurements at monitoring wells, 1 to 4 times a year. The surface between wells is interpolated and has no value far from a well."
- Effort: **M to L**. Rank: **1**. This is the user's own example.

**D2. Bucket-model percolation animation (cheap simulation, validated against wells)**
- Lesson: land and water managers see how much of a wet winter reaches groundwater versus is lost to ET; why one wet month does not cure a 3-year deficit; irrigation planners learn the lag. Also teaches the difference between "soil is wet" and "aquifer is full".
- Visual: on the block, a 3D column grid (about 40 x 40 or 1 km points over the Central Valley and Sierra foothills) with droplets/particles moving downward in the column when modelled drainage is positive, soil layer colour = moisture, and a deep "reserve" bar that charges or drains. Chart: modelled recharge cumulative curve versus well hydrographs from D1.
- Data V: daily precip and ET0 from Open-Meteo per point (4 years x 1,461 days per point is a few tens of KB; 100 to 400 points means 100 to 400 calls, so batch with comma-separated lat/lon, which the API accepts). Validation: ERA5-Land soil moisture V (same call) and GRACE root-zone percentile V (D3) and D1 wells.
- **Simulated.** Formula per cell and day: `S' = S + P - ETa - D`, `ETa = ET0 * Kc * min(1, S/(0.5*Smax))`, `D = k*max(0, S + P - Smax)` where `Smax` (mm, 150 to 300), `Kc` (0.6 to 1.0) are per land class (estimated, from published FAO-56 ranges); Sierra snow handled with a degree-day melt (rain/snow split at 0 C, melt 3 mm/C/day, requires `temperature_2m_mean` from same API). About 60 lines vectorised.
- Honesty label: "Illustrative water-balance model driven by ERA5 reanalysis, not a groundwater model. Parameters are textbook values, checked only against ERA5-Land soil moisture and a handful of wells."
- Effort: **M**. Rank: **2**. (cheap, strongest "simulate for visuals" case; must be labelled.)

**D3. Whole-state "water in the ground" (GRACE groundwater and soil percentile)**
- Lesson: state and federal drought officials and water markets see that groundwater drought lags and outlasts the surface drought. Compare percentile versus DSCI.
- Visual: coarse 12 km tile mosaic animated weekly 2020 to 2023 under the terrain: groundwater percentile (blue to red), toggle soil moisture. Chart: statewide mean percentile versus DSCI versus reservoir storage.
- Data V: weekly GeoTIFFs (about 300 KB each, 208 weeks = 62 MB total for gws; fetch only California rows). Licence: public (University of Nebraska / NASA GRACE, cite). Coverage 2002 to now.
- **Modelled with GRACE assimilation**, not a direct measurement. Raw GRACE-FO mascons are X (Earthdata login).
- Honesty label: "NASA GRACE-based data-assimilation product, about 12 km, groundwater percentile versus 1948-2012 record; shows regional trend, not individual wells."
- Effort: **S**. Rank: **3**.

**D4. Snowpack as a white volume that feeds the reservoirs**
- Lesson: reservoir operators, irrigation districts and cities decide releases and allocations from April 1 snow water equivalent. Shows the 2021 April collapse (snowpack ran off into dry soils rather than reservoirs).
- Visual: white columns at SNOTEL sites over the Sierra, height = SWE; melts through spring; link line to Shasta/Oroville tank levels already in the app; chart SWE versus inflow.
- Data V: AWDB REST wildcard query above. About 100 California stations, 1,461 days each, a few hundred KB. Reservoir levels already baked in the app.
- **Measured.** Surface between stations is not interpolated (pillars only), or a lapse-rate elevation fit if wanted.
- Honesty label: "Point measurements at SNOTEL pillows; snow volume between stations not shown."
- Effort: **S**. Rank: **4**.

**D5. Streamflow percent of normal ("rivers as sensors")**
- Lesson: fisheries managers, farmers with surface rights, and downstream cities see which rivers dropped below the 10th percentile and when curtailment orders matter.
- Visual: gauge markers along rivers on the block; ribbon thickness or colour = flow percentile versus monthly record; chart daily flow with percentile bands.
- Data V: `.../collections/daily/items` for daily flow (public domain) and `nwis/stat` monthly percentiles for the baseline (V, 46 KB per site). 15 to 30 gauges is enough.
- **Measured** with computed percentile. Effort **S to M**. Rank: **5**.

**D6. Dry wells and shortage risk (point pop-ups)**
- Lesson: county officials and nonprofits pre-position bottled water and well drilling support. Reports pop up in the weeks after the water table drops below domestic well depth.
- Data: DWR Household Water Supply Shortage Reporting System CSV (R, X from here: Cloudflare 403 on `data.cnra.ca.gov`; metadata V). Available alternative V: DWR "Water Shortage Vulnerability" sections count 25,607 PLSS sections (static risk score, CC-BY) via `https://utility.arcgis.com/usrsvcs/servers/4f8a6a51140d492ca3ea7299de492a3d/rest/services/Environment/i07_Water_Shortage_Social_Vulnerability_BlockGroups/MapServer/0` (block groups) — static, not time-resolved.
- Effort **M**, blocked on a manual download. Rank: **6** (unverified).

**D7. Land subsidence (Central Valley sinking)**
- Lesson: canal and rail operators, SGMA agencies learn that overpumping permanently lowers land and damages infrastructure; justification for pumping limits.
- Data: DWR TRE Altamira InSAR 2015 to 2022 (CC/DWR; rasters on Box, point data on `data.cnra.ca.gov`, image service at `gis.water.ca.gov`): **all three unreachable here (X)**. Alternative R: NGL GNSS (V host) for 2 to 5 Central Valley CGPS sites (e.g. a P-station near Corcoran) as sinking-point pillars; need station IDs from `llh.out`.
- Effort **L** (rasters) or **M** (GNSS points). Rank: **7** (needs the manual download).

**D8. Fallowed cropland / ET**: CropScape WMS capabilities V (53 KB), but multi-year classification maps are heavy. Rank 8, not built in the first pass.

**D9. Wildfire-drought link**: the Fires tab already holds acreage; a joint chart with DSCI is easy but teaches little new. Fold into charts, not a candidate.

### Top 3 for Drought
1. **D1 sensor wells + water-table slice** (M to L; measured, matches the user's example).
2. **D2 bucket-model percolation** (M; simulation, labelled), reusing D1's wells for validation.
3. **D3 GRACE groundwater mosaic** (S) as the cheap statewide context. D4 snowpack is the next-best S build.

## 3. Cross-cutting notes
- Do all Python fetching with a `User-Agent`; USGS CDN returns 403 for guessed product paths.
- Cache raw files under `data/raw/` with a download script; do not commit them (USGS GeoTIFFs 26 MB, ShakeMap grid 16 MB, stationlist 14 MB).
- Each added layer needs a one-line label in the UI from the "Honesty label" entries above; simulated layers carry a visible "MODEL" chip.
- Numbers flagged for checking before display: PAGER exposure array (MMI 6 vs 7), OAF counts (these are to-date, not at the time of the event), ShakeAlert latency (assumed).
- Not yet measured: number of California wells with 2020 to 2023 USGS measurements; GRACE file size for all weeks; Overpass full-extract size.
