# Track ideas: Drought and Floods tabs

Checked 2026-10-21 from this PC (curl plus web search). V = I fetched it or a listing of it. S = found by search only. U = unverified. Ideas already in `scout/actionable/ACTIONABLE_SCOPE.md` (wells, bucket model, GRACE, streamflow percentile) are not repeated. The app already shows DSCI, D0-D4, Shasta/Oroville, wells, bucket, GRACE, and eight gauges.

## Drought (California 2020-2023)

| # | Metric | Why a viewer cares | Visual and animation tie-in | Dataset (URL) | Licence | Size | Effort |
|---|---|---|---|---|---|---|---|
| 1 | Sierra snow water equivalent (SWE), % of 1 Apr average | Snow is the state's reservoir. 2021 melted into dry soil and little reached the lakes. | White pillars on about 100 SNOTEL sites shrink through spring. Melt particles run down the rivers into the Shasta/Oroville tanks already drawn. | NRCS AWDB REST `wcc.sc.egov.usda.gov/awdbRestApi/services/v1/data?stationTriplets=*:CA:SNTL&elements=WTEQ&duration=DAILY` (V, 200 OK) | US public domain | <1 MB | S |
| 2 | Storage as % of the historical average for the date, for more reservoirs | Shasta and Oroville alone hide the state. Percent of average says "how bad" with no acre-feet literacy. | Tank fill with a tick mark for average. Add Folsom, New Melones, Don Pedro, San Luis. | USGS NWIS daily storage, param 00054, `waterservices.usgs.gov/nwis/dv/` (V for the two sites; other sites U). CDEC is unreachable from here (TLS fail). SWP storage CSV at lab.data.ca.gov/dataset/daily-swp-reservoir-elevation-and-storage-data (S). | USGS public domain; SWP licence U | <1 MB | S-M |
| 3 | Precipitation anomaly (water-year total vs normal) | Shows that 2021 failed in winter, and that Dec 2022 - Mar 2023 flipped it. | Rain particles over the block with density from the day's rain. Statewide anomaly strip under the DSCI chart. | Open-Meteo ERA5 archive `archive-api.open-meteo.com/v1/archive` (V in scout). PRISM not tested (U). | CC-BY 4.0, free tier non-commercial | ~1 MB | S |
| 4 | Dry household wells reported | The human cost, with a lag after the water table falls. | Red dots appear by month on the map, next to the well hydrographs. | DWR Dry Well Reporting CSV, lab.data.ca.gov/dataset/dry-well-reporting-system-data (S). data.cnra.ca.gov returns 403 here. | "Not specified" in the catalog (U) | small | M, blocked |
| 5 | Land subsidence (Central Valley) | Pumping lowers the land for good. | Terrain extruded down with exaggeration; a Corcoran-area bowl grows. | DWR TRE-Altamira InSAR, point layers at `gis.water.ca.gov/arcgis/rest/services/Elevation/` (S, host timed out here); 2015 onward | Terms not found (U) | 100s MB raster | L |
| 6 | Colorado River: Lake Mead and Powell elevation | California takes about a quarter of its supply from there. | Two more tanks with "bathtub ring" lines. | Reclamation RISE, `data.usbr.gov/catalog/4370/item/6123` (S). The mirror `api.wwdh.internetofwater.app` returned 200 (V), data call not tried. | US public domain (U) | small | S-M |
| 7 | Fallowed cropland | Direct farm impact. | Field patches grey out by year. | USDA CDL, annual 30 m; fallow class by year (U, not tested) | public domain (U) | large | L |
| 8 | Wildfire overlay | Link to the Fires tab. | Fire dots on the DSCI timeline. | Already in app | n/a | 0 | S, low insight |

### Top 3 Drought
1. **#1 Snowpack.** Measured, small, and it explains the lakes you already draw. Particle melt-to-reservoir gives the tab a cause-and-effect story.
2. **#2 Reservoir percent of average.** One honest number per lake. Needs a check that USGS has storage for each extra site, since I only confirmed two.
3. **#3 Precipitation anomaly.** It is the cheapest build. It drives real rain particles instead of decoration, and it shows when the drought broke.

Stretch: #4 dry wells is the strongest human-impact idea, but it needs a manual download and has no stated licence.

## Floods (Helene, western NC, 25-30 Sep 2024)

| # | Metric | Why a viewer cares | Visual and animation tie-in | Dataset (URL) | Licence | Size | Effort |
|---|---|---|---|---|---|---|---|
| 1 | Observed hourly rain (radar plus gauge) | The cause. Replaces any modelled rain. Peaks near 1 m are possible in the mountains (U, not computed). | Rain particles with intensity from the real grid, running in sync with the hydrographs. | NOAA MRMS MultiSensor QPE 1H Pass2: AWS `noaa-mrms-pds.s3.amazonaws.com/CONUS/MultiSensor_QPE_01H_Pass2_00.00/20240927/` (V, hourly .grib2.gz present). Mirror at mtarchive.geol.iastate.edu/2024/09/27/mrms/ncep/ (V). | NOAA public domain | ~6 days x 24 files, ~1 MB each; crop to WNC | M (needs a GRIB reader; `eccodes` on Windows U) |
| 2 | Lag: rain peak to river crest, per gauge | Warning time. Small creeks crest in hours, big rivers later. | A ruler between the rain-peak mark and the crest mark on each gauge. A raindrop runs from the basin to the gauge in the lag time. | Derived from #1 plus the 8 gauges already in meta.json | n/a | 0 | S after #1 |
| 3 | Landslide points | The second killer in the mountains. Gives a reason for roads cut off. | Points pop up on steep slopes once the rain total passes a threshold; debris particles slide downhill. | USGS preliminary Helene landslide inventory, DOI 10.5066/P14CHGKS, ScienceBase item 674634a1d34e6d1dac3abddc: shapefile, GeoJSON, CSV (S). ScienceBase returned 403 to curl, so use the browser or the data.usgs.gov record. | USGS, licence text not read (U) | small | S |
| 4 | Soil wetness before the storm | A wet slope floods and slides faster. | A sponge bar fills before day 25 and is full when the storm hits. | Open-Meteo ERA5-Land `soil_moisture_*` hourly (V in scout), or MRMS 72 h totals | CC-BY 4.0 | tiny | S |
| 5 | Surveyed high-water marks | Ground truth for your HAND "illustrative" flood layer. | Pins with measured height next to the HAND depth. Shows where HAND is wrong. | USGS STN, stn.wim.usgs.gov. Exists (S, crews flagged marks in the Swannanoa, Pigeon, Watauga basins), but the API returned a web page, so the endpoint is U. USACE counted 2,587 marks in TN/NC/VA (S). | public domain (U) | small | M |
| 6 | Satellite flood extent | Observed water, not modelled. | Observed footprint toggled over HAND. | NASA OPERA DSWx-S1 via PO.DAAC / Earthdata, free login (S). The Helene ARIA folder I tried gave 404. Marked preliminary. Radar struggles in narrow wooded valleys (my judgement). | NASA open | large | L |
| 7 | Power outages (county customers out) | The lived impact, lasting days. | Counties dim; line of customers out versus time. | ORNL EAGLE-I on figshare, article 24237376 (S). Title says 2014-2024, so 2024 coverage is U. ORNL site unreachable here. 15 min, county level. | Not found (U) | tens of MB | M |
| 8 | Road closures | Isolation of towns. | Roads blink red. | NCDOT DriveNC: no open archive found (U) | U | U | L, skip |

### Top 3 Floods
1. **#1 + #2 together: observed rain and lag.** It is real data, and it ties the particles to the hydrographs. Check the GRIB reader first.
2. **#3 Landslides.** Small point file, the most striking local story, and a good "what existed vs. what this adds" slide.
3. **#4 Antecedent soil wetness.** Needs nearly no work and explains why this rain was so bad. If #5 high-water marks can be fetched, swap it in, since it checks the HAND layer.

## Caveats
- I fetched only listings and headers. I did not open any GRIB, shapefile or CSV, so formats and sizes are estimates.
- Three hosts blocked me (CDEC, data.cnra.ca.gov, gis.water.ca.gov). Retry them from another network before dropping #4 and #5 on the drought side.
- Licence text was read for none of the datasets. "Public domain" means US-government work by default, not a checked statement.
