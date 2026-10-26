# GATE P2 UX: Drought and Floods

**Verdict: PASS WITH FIXES.** Numbers match meta.json (soil 0.423 vs 0.385, 1402 slides, reservoirs, rain, snow). Fixes 1-5 are honesty errors.

## Honesty
1. **Warning-time "Heaviest hour" mm is the wrong hour.** `max1h_mm` is the 5-day maximum. The lag uses the heaviest hour in the 24 h before the crest (`peak_h`). In `build_phase2.py` (~line 179) use `max1h_mm=round(float(loc[int(ph)]),1)`. Rebuild. Rename the column "Heaviest hour before crest".
2. **phase2_build.log is stale.** It shows 48 h lags; meta.json has 1 to 22.5 h. Rerun the build so the log matches.
3. **Soil "driest to wettest" is false.** `lo` and `hi` are the 5th and 99.5th percentiles, not extremes. Replace that sentence with: `That is ${fmt(so.mid[k]-so.clim_mid[k],2)} m³/m³ (about ${fmt(100*(so.mid[k]/so.clim_mid[k]-1),0)} %) above that date's 2014–2023 mean. September values ran from ${fmt(so.lo,2)} (5th percentile) to ${fmt(so.hi,2)} (99.5th).` The heading "wetter than usual" holds (+10 %). Add `<span class="chip model">MODEL</span>` to that h2. The sponge clamps at `hi`; Sept 2024 reached 0.516.
4. **Snow check cites two years only.** SNOTEL weekly peaks are 86, 66, 47, 264 %. Quoted DWR figures (59, 38) are the closest matches. Quote all four years, and say SNOTEL is "% of median" while DWR is "% of average". Verify the DWR 2020 and 2023 values before adding them.
5. **Chips overclaim.** Landslides: `MEASURED` becomes `MEASURED places · ILLUSTRATIVE timing`. Snowpack: `MEASURED · melt paths ILLUSTRATIVE`.

## Accessibility
6. **Landslide colours fail the validator** on the dark surface. #f99e47, #ff6b5c and #cc8c5c give worst ΔE 2.4 (deutan) and 10.8 (normal vision). Road also matches NWS minor orange, and building matches moderate red. Use road #f4f1e8, building #ff4fd8, other #b8a07e (worst ΔE 12.9 deutan, 26.5 normal). Add a 1 px dark ring. In the legend replace the "●" glyphs with the `<b>` swatches used for gauges.

## Copy and charts
7. Warning note: replace "Steep small streams gave almost no warning" with "South Toe near Celo: 1 h from heaviest rain to crest." Only that gauge supports the claim.
8. Rain KPI: append "(week to this date)". The value is interpolated between weekly points.
9. Reservoir readout: "of its record storage" becomes "of its record maximum".
10. Dual axes break the one-axis rule: D34 "scaled", soil vs ERA5-Land "scaled", GRACE vs D2+, gauge stage plus cfs. Split into small multiples. Tolerable for now because each label says "scaled" or gives both units.
11. Phone: the 12 px KPI and legend text is the floor. Let the 6 flood KPIs wrap to two columns. The `.lagbar` (max 56 px) fits.
