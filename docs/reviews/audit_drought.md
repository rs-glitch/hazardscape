# Audit: Drought tab (read-only review, no project files edited)

## Data checks
1. DSCI: USDM defines cumulative DSCI = D0+D1+D2+D3+D4 (0-500); matches pipeline/build_drought.py:62. statisticsType=1 returns cumulative (traditional) values: verified on all 58 county files and 209 state rows (d0>=d1>=...>=d4 everywhere). All counties share identical 209 dates. Area-weighted county DSCI at 2021-08-17 = 433.5 vs state-stat sum 432.9 (independent consistency check passes).
2. Peak: meta.json stats 2021-08-17 d4=48.97 (matches raw API). I could not find an independent published figure by web search (only May 2021 26 %, June ~33 %); mark as "API value, not cross-checked".
3. Reservoirs: Oroville min 788,100 ac-ft on 2021-09-21 (weekly sample) vs published 787,578 in Sep 2021: good. Date is September, not October as in the brief. Shasta min 974,000 on 2021-10-19: could not be confirmed (sources found: ~1.19 M "26 %" undated); verify against CDEC SHA. Maxima 4.461 M (Shasta, May 2023) and 3.535 M (Oroville, Jun 2023) are plausible vs capacities 4.552 M / 3.537 M.
4. Note sentence: no source in SOURCES.md or meta. "Driest 3-year period" is supported by DWR/NOAA statements for 2020-22; "wet winter 2023 ended most of it" fits the data (D0 3 % left in Dec 2023, D1+ 0) but the wet winter began Dec 2022. Add a citation.
5. Raster: 58/58 counties present, min cell count > 30; 58 % of grid is outside CA (ocean, NV, AZ, Mexico) and is uncoloured by design. Uint8 texture: W=444 (multiple of 4) and three's DataTexture sets unpackAlignment=1, so no alignment bug. Flip `1 - vMapUv.y` is the same convention as the fire shader and the screenshot shows counties aligned with coast. Week bounds: uWeek <= 208, w1 clamped: OK.

## Findings (by severity)
- MEDIUM web/index.html:546-549 (dsciColor) and 553: colour constants are sRGB values written into linear `diffuseColor`, so D3/D4 look brighter than the legend swatches (#e60000 / #730000); screenshot shows D4 as bright red. Fix: convert with pow(c, vec3(2.2)) (or three's SRGBToLinear) in the shader.
- MEDIUM web/index.html:549 ramp offset: `v/100-0.5` puts pure D0 yellow at DSCI 50, tan at 150, orange at 250. DSCI 100 is therefore a yellow-tan mix, not "D0 yellow"; the category legend (DCOL, :578) is reused for a DSCI map. Fix: add a separate DSCI colour strip (0/100/200/300/400/500) or change x to `v/100 - 1.0` with D0 at 100 and say "100 ~ all D0".
- MEDIUM web/index.html:518-520 (+ pipeline/build_drought.py:98-99): labels include Las Vegas, Henderson, North Las Vegas, Reno. Fix: in the pipeline keep only places whose grid cell has cid>0, or filter on a CA bounding polygon.
- LOW pipeline/build_drought.py:63-66: `dsci` is zero-filled; a short county response would silently show "no drought". Fix: assert len(rows)==209 and rows dates == weeks per county.
- LOW build_drought.py:80: reservoir takes first value up to 6 days AFTER the USDM date (look-ahead). Fix: look back or same day.
- LOW web/index.html:538-543: uCid/uDsci textures are never disposed on switching event (GPU leak); also water scale uses each lake's own 2020-23 max, so tanks are not comparable across lakes (stated in text).
- LOW web/index.html:617 vs 573: KPI/readout use rounded week, tanks use interpolation: small mismatch.
- NIT mobile (520 px): city labels overlap (SF/Oakland/San Jose, LA/Long Beach/Anaheim/Riverside); lower the label cap on narrow screens.
- OK: switching away resets S.speed on load (12 for fire/quake, 168 drought; 168 exists in the select), S.fire.charts replaced per panel, stop() called in showFire, `S.seq` guard present. Not run live in a browser; checked by reading code and the selftest PNGs.
