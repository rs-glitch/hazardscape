# Audit: Helene hurricane and flood tabs (2026-10-20)

Selftest: `python selftest.py helene helene@60 helene-wnc helene-wnc@60 dixie` gave 10/10 ok, no console errors. Dixie is unchanged.

## Ranked findings
1. Required. web/index.html about L822-831 and L947 (hurricane track ribbon). The track leaves the map at hours 95-97 (y < 0 at 38.1 N). Segments touching those points are skipped, so the ribbon draws a chord that skips point P(b). `setDrawRange(0, 6*(floor(T)-seg0))` assumes one segment per hour, so the "past" ribbon runs about 3 h ahead of the eye after the gap. Fix: build the ribbon from every `on` point (clamp to the map edge) or map hour to segment index.
2. Required. pipeline/build_flood.py L157 vs the shader at index.html L1015-1020. Python uses `hand < rise` with a hard `wgt > 0.5` cutoff (about 12.5 km). The shader uses smoothstep(0, 0.25 m) and a fade to 15 km. The comment "same formula as the app" is false at low water. Result: chart and KPI show 2.8 km² on 25 Sep 00:00 and 11.4 km² at 07:00 EDT (rises of 6-7 cm, no gauge near flood stage) while the map draws about 0 (my recomputation: app rule 0.0 km² at hour 7). The peak matches: 115.4 km² (Python rule, from hand.png), 113 (shader rule), meta 115.0, developed 28.15. Fix: compute area as `smoothstep(0, .25, rise-hand)*wgt > 0.5`.
3. Required. meta note, both build_hurricane.py L180 and the panel. "Late on 26 September" is EDT; the panel elsewhere says 27 Sep 03:10 UTC. NWS TAE and NHC: 11:10 PM EDT, 0310 UTC, Taylor County, east of the Aucilla River, Big Bend, Cat 4. Fix: write "late on 26 September (EDT)". The app prints 120 kt as 138 mph and NHC says 140 mph (rounded to 5 mph); add "NHC rounds to 140 mph". HURDAT2 shows 939 mb; the NWS TAE summary says 938 mb (checked by search only). The NHC TCR PDF was too large to fetch, so the TCR figures are not read directly.
4. Optional. index.html about L990: `fmt(c.rm / HU.sc)`. HU.sc = size/2000 (display scale), but the pipeline scaled rmw by k/cos(lat). At 20-35 N the shown RMW is off by up to about 7%. The same name `sc` holds two meanings. Fix: store rmw in true km and scale in the app, or divide by the pipeline sc.
5. Optional. Labels (L1343 loop). There is no declutter. Gauge labels "French Broad at Asheville", "Swannanoa at Biltmore" and "Woodfin" overlap (PNG, desktop and phone). "Tampa" and "St. Petersburg" overlap. The phone shows 7 city labels plus 8 gauge labels. The Asheville city label is missing on the flood tab. Fix: greedy hide by priority using screen-box overlap; use short gauge names on the phone.
6. Optional. hurWind and hurTick. Streak colour uses ground-relative speed (adds 0.5 of storm motion, up to about 16 kt) but the legend and rings use vortex-only speed. hurWind allocates arrays per streak per frame (6500 streaks), which creates GC pressure on phones. Fix: preallocate the knots and cache the per-frame quadrant interpolation.
7. Optional. ERA5 label. 362.5 mm (14.3 in) is the 24-29 Sep total at the 0.25° cell nearest Asheville. NASA and NWS give 13.98 in for 25-27 Sep. The label "(ERA5)" is honest. But the highest observations were Busick 31.33 in and Black Mountain 21.07 in (NC State Climate Office, NOAA), far above the ERA5 maximum of 362.5 mm. Fix: add a line comparing with observed totals and state the window (6 days).
8. Optional. hand.png texture (about L420). It uses default mipmaps and anisotropy 4, which blur and bleed 0 m river cells at oblique angles. Fix: `minFilter = LinearFilter; generateMipmaps = false`. 74% of HAND pixels sit at the 63.75 m clip.
9. Nit. Flood `dayn` shows "Day 6" at T = 120. `g.site` is not escaped in innerHTML (local data only). Peak time shown with cfs is the stage-peak time.

## Verified
- Wind model:
  - Rotation is counter-clockwise: tangent (-n, e)/r.
  - Inflow is 0.35 rad = 20.05°.
  - Quadrants are NE, SE, SW, NW with centres at 45°, 135°, 225°, 315°, matching HURDAT2 order.
  - Core is linear to the RMW.
  - Between radii it uses a log-log power law; beyond the last radius it decays as r^-0.6, disclosed as an assumption.
  - nm to km uses 1.852. Scene scale is k/cos(lat), which is correct.
  - HURDAT2 output has no -999 values (min radii 0, min RMW 36.9 km).
  - Storm motion is added to the streak direction.
- Hurricane facts: the 25 closed rows and the L, R, R records are as stated. Landfall: 120 kt, 939 mb. Saffir-Simpson thresholds are correct. The eye is south of the map until hour 28 (25 Sep 04 UTC). The last best-track point is 28 Sep 18 UTC. "Weakened quickly" is supported: 120 to 95 to 60 kt within 6 h. The path through Georgia and Tennessee is fine, and it ends in southern Kentucky.
- NWS wording: "6 inches of fast-moving flood water can knock over an adult", "12 inches of rushing water to carry away most cars", "2 feet ... SUVs and trucks". The panel paraphrases the first two; it could add the 2 ft line.
- Flood categories for AVLN7 (18, 13, 9.5, 6.5) match the live NWPS API.
- "7 of 8" spot checks against the USGS peak files:
  - Asheville 113,000 cfs against 110,000 (1916).
  - Hot Springs 134,000 against 110,000 (1916).
  - Blantyre 29,200 against 30,000 (1964), which is the one gauge that does not beat its record on flow, although its stage does.
  - Asheville stage 24.82 ft here against 24.67 ft in the USGS provisional alert (17:30 EDT). The pipeline reads later IV data. The panel says "provisional".
- Units: ft to m is 0.3048, mm to in is 25.4, mph is kt*1.15078. The time zone is labelled everywhere (EDT in the headline, UTC in the sub-line and chart ticks).
- Disposal: uRain and uHand are disposed on the next load (about L416), and the seq guard disposes hand.png on an abandoned load. Data3DTexture is half-float R16F with an alignment of 2, which is fine on WebGL2. three 0.169 is WebGL2-only, and the renderer try/catch shows a message. All 4 NWS categories exist for every gauge, so there are no NaN ring positions. HAND is labelled illustrative in the panel, the method text and the README. The toggles are native labelled checkboxes. Panel strings use esc().
- Not run: build_flood.py and build_hurricane.py (they would rewrite web/data), and screen-reader checks on the charts.
