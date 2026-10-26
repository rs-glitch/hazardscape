# Audit: Earthquakes tab (Ridgecrest)

Scope: pipeline/build_quake.py, web/index.html (quake branch), web/data/ridgecrest/meta.json. Files not edited.
Checked by reading, by re-deriving from data/raw, and by `selftest.py ridgecrest ridgecrest@60 dixie state` (all four report ok; the selftest misses finding 1, see below).

## Data verification (measured against data/raw USGS files)
1. Note text: M6.4 at 2019-07-04 17:33:49 UTC, M7.1 at 2019-07-06 03:19:53 UTC, gap 33.8 h ("34 hours" correct). "Largest in California in 20 years" matches USGS wording (largest since 1999 Hector Mine M7.1). OK.
2. Shocks: M6.4 depth 10.5 km (35.7053, -117.5038), M7.1 depth 8 km (35.7695, -117.5993), both match the ComCat detail JSON. h = 17.564 and 51.331 match. OK. Local times (10:33 AM and 8:19 PM PDT) correct.
3. MMI orientation is CORRECT. covjson axes are [y, x], y ascending (south to north); sample() divides by the signed step, so both orders work. Max MMI cell sits at the epicentre (M6.4: 8.3 at 35.65 N, ~6 km S of epicentre; M7.1: 8.6 at 35.733 N). Our webp at the M6.4 epicentre pixel decodes to MMI ~7.7, which equals the ShakeMap value there (mirrored row gives a different colour). Not flipped.
4. Aftershock depth sign is correct (ComCat positive down, code subtracts). Placement problems are listed below (floor, exaggeration).
5. Mixing of both events is not labelled (finding 6).

## Findings, ranked

### Critical / Required
1. index.html:503-504 and :568. buildQuakeScene runs BEFORE `S.ex = 1.6`; S has no `ex` at first load, so fault heights are `x * undefined = NaN`. Fault lines never render on a first visit or deep link (confirmed: console "computeBoundingSphere(): Computed radius is NaN", no yellow lines in ridgecrest_1400x900.png). Later visits use a stale S.ex (the fire relief slider value). Fix: set `S.ex = 1.6` before buildQuakeScene.
2. index.html:554 vs :505. Aftershocks use `heightAt(...,1)` while terrain is drawn at S.ex 1.6, so dots sit up to ~1 km deeper than "true depth" under the exaggerated surface. Fix: pass S.ex or draw the terrain at 1 in quake mode; and say "relief x1.6" in the note.
3. index.html:445 (skirt) with data. Depth max is 29.6 km, 3,025 of 5,151 events are deeper than 4.1 km, but the skirt floor is at -0.035*size = -4.1 km. Most dots hang below the model block. Fix: in quake mode set the base to -(max depth + margin) or clip the dot depths and label.
4. index.html:878 and :210. Chart clicks/drags call setT only: no stop(), no quakeSync. Seeking forward on a chart makes quakeTick fire the foreshock wave and snap S.T back to 17.6 h; seeking back leaves MMI revealed from the future. Fix: route chart seek through the same handler as the slider (stop + quakeSync when quake).
5. index.html:875 play(). Replay after the end calls setT(0) without quakeSync: shocks stay fired, so the full M7.1 shaking is visible at hour 0 and no wave pauses occur. Fix: in play(), after setT(0), call quakeSync(0, true) for quakes.
6. index.html:589, :583. If the user presses Pause during a wave, resumeAfterWave is still true, so play() runs at the wave end against the user's pause. Fix: clear QK.resumeAfterWave in the user Play/Pause/Space/scrub handlers (not in quakeTick's own stop()).
7. index.html:572, :587. maxKm = full grid diagonal (161 km) so each wave freezes playback ~46 s, but the farthest corner is ~84 km (~24 s); the last ~22 s show nothing. Fix: use the distance from the epicentre to the farthest grid corner per shock.
8. Shaking colour for both shocks (shader :545-547, panel :612). No MMI colour legend anywhere. After the M7.1 wave passes, its colours replace the M6.4 colours (r2 wins everywhere m2.a > 0), so the map is a mosaic of two events. Fix: add an MMI key and a caption "colours show the latest shock's shaking; ahead of the wave front you still see the M6.4 map", or take max(MMI) of the two grids.
9. build_quake.py:108-110. Qfaults query returned exactly 2,000 features and `exceededTransferLimit: true` (raw file): faults are truncated. 126 of 10,390 vertices also lie outside the grid, so lines extend beyond the block (heightAt clamps). Fix: page with resultOffset, or filter by fault class, and clip to the BOX.
10. index.html:612. `Math.floor(mmi_max)` labels the M7.1 (8.6) as MMI VIII; USGS rounds to IX. Use Math.round and add "violent" for >= 9.
11. index.html:398-400. S.cat is set and tabs() called before the `seq !== S.seq` check, so a stale load flips the header pressed state. Move the seq check up. The stale path also leaks the MMI textures.
12. GLSL :549 `pow((d - uR)/1.6, 2.0)` has a negative base inside the ring; undefined per spec and NaN on some drivers (it rendered under SwiftShader but was not seen mid-wave). Use `float k = (d1-uR1)/1.6; exp(-k*k)`.

### Optional
- :583 quakeTick sets S.T = s.h but does not call setT: the panel and slider show the overshoot (up to 4.8 h at 2 days/s) for the wave duration. Call setT(s.h).
- :595 camera shake adds to camera.position after controls.update with no restore; residual drift of a few hundred metres. Use an offset that is removed after render.
- :414/:533 uM1/uM2 textures are never disposed (leak per quake load); `meta.shocks` length 2 is hard-wired (uE1/uE2).
- Quake scene still builds two 1-particle systems (:501); harmless, but skip them. toHalfTexture is skipped correctly; X-ray cannot leak because materials are rebuilt per load.
- Catalogue is incomplete in the first hours after the M7.1; the per-6-hour chart under-counts early on. Add a sentence in "Method and checks".
- Method text says medium resolution ~3.7 km; the M6.4 grid is 1.85 km, the M7.1 grid 3.7 km.
- Default X-ray opacity 0.42 dulls the MMI colours; consider starting with opacity ~0.7.
- Hash `#ridgecrest@-5` is not clamped to 0.

### Nits / accessibility / mobile / XSS
- CSS :36 vs :51: `.tip { max-width:240px }` comes later and overrides `.qtoast` max-width, so the toast is 240 px. Use `.tip.qtoast`. The toast also stays up to 6 s after leaving the quake view.
- "Soon" buttons use `disabled`: not focusable, so keyboard and screen-reader users cannot discover them; consider `aria-disabled` and aria-current instead of aria-pressed for navigation. Emoji labels are read aloud; add aria-hidden to the emoji.
- Static labels stay wrong in quake mode: slider label "Time since ignition" (:118), canvas aria-label "fire spread" (:108).
- Phone (520 px shot): header wraps into three rows, town labels overlap (Inyokern/China Lake Acres/Ridgecrest); acceptable, but cap labels at 8 on small screens.
- XSS: none found. Names, notes, labels, and place names go through esc(); the hash is only compared against known ids; `s.mag` in the toast is numeric JSON from our own file.
- Selftest gap: it only greps for "error|uncaught|failed", so the NaN warning in finding 1 passes. Add `NaN|warn` to the regex and a test that steps the wave.
