# Hazards data scout (verified 2026-10-20, Windows, Python requests; samples in ./samples)
Legend: OK = downloaded and parsed here. Licences: US-government works are public domain unless noted.

## 1. Earthquakes - Ridgecrest 2019 (recommended)
- Catalog (OK, 3.5 MB, 4837 events M>=2, 4-20 Jul, 1 s timestamps in ms epoch):
  `https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime=2019-07-04&endtime=2019-07-20&minlatitude=35.4&maxlatitude=36.1&minlongitude=-118.0&maxlongitude=-117.2&minmagnitude=2`
  Fields: geometry [lon,lat,depth_km], properties mag, time, place, magType, gap, rms. M6.4 = ci38443183 (4 Jul 17:33Z, depth 10.5), M7.1 = ci38457511 (6 Jul 03:19Z, depth 8). Use minmagnitude=1 or format=csv for more; 20k-row limit per call.
- Event detail (OK): `https://earthquake.usgs.gov/fdsnws/event/1/query?eventid=ci38457511&format=geojson` -> properties.products.shakemap[0].contents[name].url.
- ShakeMap (OK): base `https://earthquake.usgs.gov/product/shakemap/ci38457511/atlas/1594160054783/download/` (version id may change; always read from detail JSON).
  - `coverage_mmi_medium_res.covjson` 277 KB (CoverageJSON, MMI, 291x237 grid, lon -122.13..-112.47, lat 31.7..39.57, ~0.033 deg = 3.7 km). Also `_low_res` 70 KB, `_high_res` 1.1 MB; same for pga, pgv, psa0p3/1p0/3p0.
  - `grid.xml` 16.6 MB (finer, full fields), `raster.zip` 10 MB (GeoTIFF), `rupture.json` 4.7 KB (finite-fault polygon), `cont_mmi.json` 81 KB (contours), `intensity_overlay.png` 205 KB, `stationlist.json` 14 MB.
- Faults (OK): ArcGIS REST, layer 21 = USGS Quaternary Fault and Fold DB:
  `https://earthquake.usgs.gov/arcgis/rest/services/haz/Qfaults/MapServer/21/query?where=1%3D1&geometry=-118.2,35.3,-117.0,36.2&geometryType=esriGeometryEnvelope&inSR=4326&outSR=4326&outFields=*&f=geojson` -> 2000 features (hit maxRecordCount; 2.2 MB; page with resultOffset or narrow the box). Fields fault_name, age, slip_rate, slip_sense, class.
- Time dynamics: arrival raster = distance to epicentre / 3.5 km/s (S-wave; P ~6 km/s) multiplied by ShakeMap MMI; aftershock points by time and depth. Not provided by USGS: wavefield (we model it).
- Licence: public domain (USGS). 

## 2. Hurricanes - Helene 2024 (recommended), Ian 2022 backup
- HURDAT2 (OK, 7.0 MB all basins 1851-2024): `https://www.nhc.noaa.gov/data/hurdat/hurdat2-1851-2024-040425.txt`. Helene = AL092024, 25 rows, 6-hourly (plus landfall record): e.g. `20240927, 0500, R, HU, 30.8N, 83.5W, 95 kt, 947 mb`, then 34/50/64-kt wind radii per quadrant (NE,SE,SW,NW) and RMW (last col). 27 Sep 06Z 31.3N 83.3W 80 kt; 12Z 34.4N 83.2W 45 kt (over NC mountains by ~27 Sep 12-18Z). Ian = AL092022, 40 rows. Wind radii exist since 2004, so a Holland-style asymmetric field can be built from radii + RMW (modelled, not observed - label it).
- Rainfall option A (OK, light): Open-Meteo archive, 36 points x 144 h in one call = 135 KB, 1.2 s:
  `https://archive-api.open-meteo.com/v1/archive?latitude=<csv>&longitude=<csv>&start_date=2024-09-24&end_date=2024-09-29&hourly=precipitation&timezone=UTC` (returns a list, one object per point). Max 6-day sum seen 343 mm in a 6x6 grid 34-36.5N, -85..-82.5W. Licence CC-BY 4.0 (ERA5/ERA5-Land derived; coarse ~9-25 km, underestimates peaks). Free tier is non-commercial; rate limits apply for 400-point calls (split in batches).
- Rainfall option B (OK, real radar-gauge): NOAA Stage IV daily, 3.7 MB each, CONUS 4 km, HDF5-based netCDF4:
  `https://water.noaa.gov/resources/downloads/precip/stageIV/2024/09/27/nws_precip_1day_20240927_conus.nc` (header \x89HDF confirmed; not parsed because h5py/netCDF4 is not installed - `pip install h5py` needed). Daily only on this path; hourly archive not found (my guess at a "last24hrs" file returned 404). Public domain.

## 3. Floods - Helene, western NC (recommended); Pajaro March 2023 (CA, verified)
- USGS Water Services IV (OK, 15-min):
  `https://waterservices.usgs.gov/nwis/iv/?format=json&sites=03451500&parameterCd=00060,00065&startDT=2024-09-24T00:00-04:00&endDT=2024-10-02T00:00-04:00`
  - French Broad at Asheville 03451500: peak 113,000 cfs, 24.82 ft at 2024-09-27 17:38 EDT (769 pts, 126 KB; baseline 738 cfs on 24 Sep). Series ends near the peak (gauge failure likely; discharge may be estimated/provisional).
  - Swannanoa at Biltmore 03451000: peak 60,800 cfs, 27.33 ft at 27 Sep 15:00 EDT (baseline 48 cfs; ~1270x rise).
  - Pajaro R. at Chittenden 11159000: 13,200 cfs on 10 Mar 2023 23:30 PST, 29.11 ft 11 Mar 04:00 (levee breach 11 Mar).
  Provisional data; multiple sites in one call comma-separated; IV window max ~1 year per call is typical. Public domain.
- STN high-water marks: NOT verified. `stn.wim.usgs.gov/STNServices/...` returned the Angular web-app HTML (8 KB), not JSON; correct endpoint/event id unknown.
- Inundation polygons for 3D shader: none verified. Practical approach: stage-based "water level over time" raster from gauge stage along the valley, intersected with DEM height-above-nearest-drainage (own computation).

## 4. Drought - California 2020-2023 (recommended)
- USDM weekly GeoJSON (OK): `https://droughtmonitor.unl.edu/data/json/usdm_YYYYMMDD.json` (Tuesdays). 14.0 MB (3 Jan 2023), 16.9 MB (27 Sep 2022); 5 MultiPolygon features (DM 0-4), CONUS-wide, unsimplified - clip to CA and simplify. Shapefile zip `https://droughtmonitor.unl.edu/data/shapefiles_m/USDM_20230103_M.zip` = 1.7 MB (much lighter). Public domain; USDM asks for credit.
- Weekly CA area percent (OK, tiny): `https://usdmdataservices.unl.edu/api/StateStatistics/GetDroughtSeverityStatisticsByAreaPercent?aoi=06&startdate=1/1/2020&enddate=12/31/2023&statisticsType=1` with header Accept: application/json (aoi=CA returned []; use FIPS 06). 209 weeks. Values cumulative. Peak: 17 Aug 2021 D2+ 95.6%, D3+ 88.4%, D4 49.0%; 28 Mar 2023 D2+ 1.95%, D0+ 44.7%.
- CDEC: NOT reachable from this machine (TLS handshake fails on every URL, python and curl, incl. TLS1.2 cap; probably IP/TLS block). Format unverified. Substitute verified: USGS NWIS daily storage (param 00054), `https://waterservices.usgs.gov/nwis/dv/?format=json&sites=11406800&parameterCd=00054&startDT=2020-01-01&endDT=2023-12-31`: Oroville (11406800) min 787,700 ac-ft 1 Oct 2021; Shasta (11370000) min 967,400 ac-ft 21 Oct 2021, max 4,467,000 ac-ft 24 May 2023 (Oroville response mixed several series; filter by qualifier). Retry CDEC from another network.
- Snow: NRCS SNOTEL REST (OK): `https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1/data?stationTriplets=1067:CA:SNTL&elements=WTEQ&duration=DAILY&beginDate=2023-01-01&endDate=2023-04-30` (4.5 KB JSON). Station list URL returned all states (4398; stateCds filter ignored) - filter ":CA:SNTL" client side; 1.6 MB.

## Other hazards
- Tornado tracks (OK): SPC `https://www.spc.noaa.gov/wcm/data/1950-2024_actual_tornadoes.csv` 8 MB (slat,slon,elat,elon,len,wid,mag,date,time; straight start-end lines) and `https://www.spc.noaa.gov/gis/svrgis/zipped/1950-2024-torn-aspath.zip` 4.5 MB. Public domain. Good for a time-synced track; 2D-ish.
- Kilauea 2018 lava: NOT verified (ScienceBase search returned 403 to scripted calls; HVO data release must be located by hand).
- Landslides: NASA LHASA catalog host unreachable (not verified).
