# Final quality gate (2026-10-20)

Verdict: SHIP WITH NOTES. No BLOCK issues.

Ran: test_raster.py (ok), validate.py (all gates pass, 12 fires), selftest.py state august dixie palisades york (10/10 ok, screenshots in data/selftest/).

Audit findings addressed: FEDS +12 h shift (README:27; validation.json FEDS-VIIRS -9.4..-10.2 h at shift0, +1.7..+3.0 h at shift12), esc() on all innerHTML, S.seq race guard (index.html:365-376), float arrival texture (347-356), weather clipped h>=0 (646), building KPI label (618), statewide chart relabelled, August merged (state.json perimeters: August Complex 1,032,648), CAL FIRE acres shown (index.html:637), Pacific dates (build_state.py:23), credit wording (SOURCES.md:8, sources.json).

Notes
1. meta.json dixie official_gis_acres still 968,397 (Fly double count); not displayed in UI, only stale metadata.
2. PLAN.md KPI row for FEDS cross-check is stale: says r 0.994-0.999, IoU 0.88-0.96; validate.py now reports r 0.998-1.0, IoU-mid 0.928-0.972.
3. README states FEDS labels the window start as fact; the audit could not confirm this. The shift is supported empirically (vs own VIIRS) only. Say "consistent with".
4. York: 60% of area never flagged by satellite (raw 41k vs 93k acres); timing there is mostly interpolation. Disclosed on page.
5. Phone (520 px render): 3D view crops the fire on the left for Dixie and Palisades; hint text overlaps a place label on desktop (August, "Brocktrails").
6. Not verified: overflow at exactly 400 px (headless Chrome minimum width is 520); CSS reading shows minmax(0,1fr), no overflow sources.
