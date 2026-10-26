# Code audit: CA Fire Years (now Hazard Replays)

Scope: pipeline/*.py and web/index.html (618 lines). Line numbers are real file lines.
Verified by running: `python pipeline/test_raster.py` (pass, "raster ok 2904 2883.9") and `python pipeline/validate.py` (all gates pass). I also read `web/data/*/meta.json` and the .bin sizes. I did NOT run the page in a browser, so every JS finding is from reading the code.

Method note: severity is for the published page. "Medium" means a wrong or broken result a viewer can reach in normal use.

## High

### H1. Untrusted upstream text goes into innerHTML (XSS)
- web/index.html:242 (`p.name` from WFIGS), :302 (tooltip `h.p.name`, `h.p.start`), :456 (Census `BASENAME` as place label), :482 (`meta.note`), :604 (`s.home`, `s.name`, `s.what`).
- Failure: a perimeter or place name containing `<img src=x onerror=...>` runs script in the page origin. Today's data has no `<>&"` characters (checked state.json and all meta places), so this is latent. It becomes live the day a feed is poisoned or a rebuild picks up a different record. The sandbox CSP limits script sources, but inline handlers may still run.
- Fix: add `const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));` and wrap every interpolated data string. For labels, build with `textContent`.

## Medium

### M1. Selected tab is highlighted one load late (wrong aria-pressed)
- web/index.html:344 calls `tabs()` before `S.fire` is replaced (:459). `tabs()` reads `S.fire?.meta.id` (:159).
- Failure: open Dixie from Statewide, and no tab is pressed (Statewide is false because `S.view` is already "fire"). Then open Creek, and Dixie shows as pressed. This is wrong for sighted users and for screen readers.
- Fix: `tabs(id)` takes the target id, and `showFire` calls `tabs(id)` after the await. Better, update `aria-pressed` in place instead of rebuilding the buttons (see L3).

### M2. showFire has no cancel token, and `#loading` is never hidden by showState
- web/index.html:341-353, 191-196, 346-348, 353.
- Failure A: click fire A, then fire B quickly, or click Statewide while a fire loads. Whichever fetch resolves last wins. `showFire` then rebuilds the scene and panel while `S.view` says "state", so the map tab shows a fire panel and `#gl` is shown over the map.
- Failure B: if WebGL is off (:348) or a fire fails to load (:353), the `#loading` overlay (`.overlay`, inset:0, opaque) stays visible. `showState()` never hides it, so the "statewide view still works" message is false and the map is covered. The overlay text also stays "Could not load..." on the next attempt, because it is never reset to "Loading fire data...".
- Failure C: on a failed load `S.fire` still points to the old fire, while the tab is already switched.
- Fix: `let seq = 0;` and in showFire `const my = ++seq;` after `await Promise.all` do `if (my !== seq || S.view !== "fire") return;`. In `showState` do `seq++; $("#loading").hidden = true;`. In `showFire` set `$("#loading").textContent = "Loading fire data…"` before showing it.

### M3. Half-float arrival texture loses the sub-hour front on long fires
- web/index.html:331-338 and shader :374; pipeline writes 0.1 h units (build_fire.py:433).
- Numbers: half floats have 11 significant bits. At 1024-2048 h the spacing is 1 h, at 2048-4096 h it is 2 h. Measured Tmax: Creek 1440 h, Dixie 1404 h, August 1308 h. So for the last ~1/3 of those replays arrival values are quantised to 1 h while the shader blends over +/-0.5 h (`smoothstep(uT-0.5,uT+0.5)`) and the glow runs over `uFront`=12 h. The front steps in 1 h blocks and glow brightness bands in 1/12 steps. Anything up to 2,500 h would be 2 h steps, wider than the blend.
- Fix: store arrival relative to an offset per half (two textures), or use FloatType with NearestFilter and 4-tap bilinear in the shader (no OES_texture_float_linear dependency). Smallest change: `FloatType` + LinearFilter when `renderer.extensions.has("OES_texture_float_linear")`, else keep half-float.

### M4. Weather charts draw outside the plot (negative time)
- web/index.html:516-517 pass `xs: w.h`, and weather h starts at -24 (build_fire.py:468 keeps -24..end). `chart` maps with `X = L + x/xmax*(W-L-R)` (:166) and the SVG has `overflow: visible` (CSS :67).
- Failure: for Eaton (xmax 84 h) the first point is at X = 34 - 86 = -52 px, so the line pokes left over the y-axis labels and out of the SVG. Smaller effect on long fires (24 h of 1400).
- Fix: in `chart`, drop points with `x < 0` (`const keep = xs.map((x,i)=>x>=0)`), or add a `clipPath` over the plot rectangle. The y-scale `ymax` should also use only the kept points.

### M5. Building KPI denominator is wrong
- web/index.html:487 ("of N mapped buildings inside the fire line"); N = `meta.n_buildings` = buildings within the 2 km buffer (build_fire.py:385, 347).
- Measured: Eaton N = 59,740 but only 11,961 are ever inside the line (80% are not). Palisades N = 27,748 vs 9,724 inside (65% not). A reader sees "11,961 of 59,740" and reads 80% survived.
- Fix: label it "of N mapped buildings within 2 km of the fire", or better, drop the denominator and show only the running count with the final inside-count (`bArr` entries `< 1e9`) as the denominator.

### M6. Hotspots from trimmed-off steps pile up at t = 0
- build_fire.py:505-508: filter is `h["t"] <= edges[-1]` only. Time is clamped by `max(0, ...)`. After trimming (:410-416, `first` may be > 0), detections earlier than the new `t0` are kept and encoded as time 0.
- Failure: all of them show as active flames at T = 0..12 h, and they contaminate the first-moment view. Steps' `det` counts (:477) correctly exclude them, so the dots and the "detections this 12 h" number disagree.
- Fix: `for h in hs if edges[0] < h["t"] <= edges[-1]`.

### M7. Crashes on edge-case input in the build
- build_fire.py:411-412: if no step has `grow > 0.002*final_a` (empty VIIRS masks, or `final_a == 0`), `active[0]` raises IndexError. A VIIRS fire with no attributed detections dies here.
- build_fire.py:424: `next(h for h in hs if h["t"] > edges[0])` raises StopIteration if every detection is at or before the trimmed `edges[0]` (can happen for FEDS fires with FIRMS gaps).
- build_state.py:181: `p["attr_FireDiscoveryDateTime"] / 1000` raises TypeError when the attribute is null for any >1000 ac perimeter.
- validate.py:310-311: `union_all([])` gives an empty geometry, then ZeroDivision at :347 if no parts matched.
- Fix: guard each (`if not active.size: raise SystemExit("no growth")`; `next(..., None)` and skip the seed; `if not disc: continue`; `if not geoms: fails.append(...)`).

### M8. The extent gate is tautological and hides how far the reconstruction is off
- validate.py:349 compares `final_acres` against the Albers area of the same official polygons. `final_acres` = `steps[-1].km2` = cells with finite arrival, which are masks clipped to `off_mask` (build_fire.py:419) plus nearest-neighbour fill of the rest of `off_mask` (:429-431). So the ratio only tests the rasteriser (1.004-1.010 in every fire).
- The independent number is `raw_satellite_acres` (build_fire.py:417, 494), which validate prints but does not gate. Against official GIS acres: Palisades 34,369 vs 23,448 (+47%), Eaton 18,127 vs 14,021 (+29%), Creek 437,553 vs 379,802 (+15.2%). Against PLAN's "within +/-15%" KPI that would fail for three fires. For FEDS fires `raw_satellite_acres` is actually the FEDS area, not satellite, so the name is wrong (build_fire.py:417 uses `masks`, which are FEDS masks).
- The UI (index.html:478, 505) says the Palisades/Eaton/Park line is "reconstructed from VIIRS", and shows only the clipped final acres. Extent is the official perimeter; only timing is from satellites.
- Also validate.py:353 / build_fire.py:502 use Pearson r on cumulative area curves; two monotone S-curves almost always give r >= 0.95, so that gate cannot fail meaningfully. The IoU mid-check is inflated because both masks are clipped to the same `off_mask`.
- Fix: gate on `raw_satellite_acres / official` with the PLAN tolerance (or change PLAN), rename the field `raw_pre_clip_acres`, state "extent = official perimeter, timing = VIIRS" in the Method box, and compute r on per-step growth.

### M9. Cache ignores parameters and caches HTTP-200 error bodies
- common.py:37 builds the cache path from `name` when given, ignoring `params`/`data`. Every call site passes a name (`perim_{id}`, `wx_{id}`, `final_{id}`...). Changing a fire's search box, date window or the weather dates in fires.py/build_fire.py silently reuses old downloads.
- common.py:47-55: any HTTP 200 is cached and logged to the provenance manifest. ArcGIS returns 200 with `{"error":...}`, and Overpass returns 200 with `"remark": "runtime error"` and partial or empty elements. The page then builds with zero perimeters or zero buildings (fetch.py:35 `d.get("features", [])`), and the bad body is permanent.
- Fix: put a short hash of `(url, params, data)` into the filename even when `name` is given, and reject bodies that parse as JSON with an `error` key or a non-empty `remark` before writing.

### M10. Crash-on-null in the UI
- web/index.html:133 `fmt(v)` calls `v.toLocaleString` and throws on null/undefined.
  - :537/:560: `wxAt` returns `undefined` if the weather arrays are empty (`i = -1`), and `null` when Open-Meteo returns a null hour. `setT` throws halfway; during play `frame()` throws before `render` and the canvas freezes (:582).
  - :238: `fmt(f.acres)` throws if `official_gis_acres` is null (build_fire.py:492 emits None when no parts match), and the whole Statewide view fails to render.
- No null appears in the current data (checked). Fix: `const fmt = (v,d=0) => v == null ? "n/a" : ...`.

## Low

- **L1. Tail trimming folds real growth into the last kept step** (build_fire.py:407-414). Steps after `last` are dropped when each is < 0.2% of final area, but the sum of a long creep can be several percent. Those cells then get the arrival of their nearest burned cell via the fill at :429-431, so the area is right but the timing is wrong, with no note in the UI. Fix: log the dropped fraction `1 - areas[last]/areas[-1]` into `validation` and show it.
- **L2. First-step interpolation ignores the ignition time** (build_fire.py:216-230). `tprev` starts at 0 and is not advanced when a step has an empty mask, so with the `first-1` trim, cells in the first non-empty step interpolate from t0 rather than the previous edge or the seed time (up to 12 h too early). Fix: set `tprev = tk` in the empty-mask branch, or use the seed's detection time as the first `tprev`.
- **L3. Rebuilding the nav drops keyboard focus** (index.html:150, 216: `nav.innerHTML = ""`, `showState()` re-renders the whole panel). After pressing a tab or year with the keyboard, focus falls to `<body>`. Fix: update `aria-pressed` in place and re-render only the changed region.
- **L4. "Town names" toggle desyncs** (index.html:521, 585). `#labels.hidden` persists across fires, but the new checkbox is rendered `checked`. Fix: set `$("#labels").hidden = false` in `showFire`, or render the checkbox state from `$("#labels").hidden`.
- **L5. Touch scrubbing on charts is unreliable** (index.html:185-186). The SVG has no `touch-action`, so a horizontal drag may be taken by the browser as a pan or scroll (`pointercancel`). Fix: `.chart svg { touch-action: pan-y; }` and handle `pointercancel`. The statewide map tooltip works only on `pointermove`, so on touch devices the perimeter details are not reachable (a tap fires `click`, which only handles featured fires).
- **L6. No `<!doctype>` and no viewport meta in the file** (index.html:1-3). Standalone via `python -m http.server` it renders in quirks mode, and on a phone without a viewport meta the `max-width: 860px` rule (:92) never fires. A hosting wrapper may add both; confirm, or add them (cost: two lines).
- **L7. `cls_grid` takes the top-left sample, not the mode** (build_fire.py:454-455). Comment says "mode of the 4x4 block" but `[:, 0, :, 0]` picks one texel in the NW corner. Burned land-cover shares carry a 1.5-texel NW bias. Fix: `[:, 2, :, 2]` (centre) or a real mode.
- **L8. Time-step edge risk** (build_fire.py:204). FEDS perimeters are assigned with `t <= edges[k]`, with no tolerance. A perimeter stamped 12:03 UTC lands in the next step (a 12 h shift). Fix: add a 20-30 minute tolerance.
- **L9. The final frame is not fully burned** (index.html:374, 461). Cells that arrive within 0.5 h of `Tmax` are rendered half-burned at T = Tmax (smoothstep centre). Fix: set slider max to `Tmax + 0.5`, or clamp `uT` to `Tmax + 0.5` for rendering.
- **L10. Statewide detection chart joins across zero days** (build_state.py:204 omits days with 0 detections; index.html:230-232 draws a line between neighbours). It also counts S-NPP only (:198), while per-fire numbers count S-NPP + NOAA-20, so the two are not comparable. The readout (:234) names S-NPP, which is honest, but the panel header does not.
- **L11. Space-bar handler blocks `<select>`** (index.html:600). It excludes INPUT and BUTTON only, so Space on the speed `<select>` toggles playback and `preventDefault` stops the dropdown opening. Add `SELECT`.
- **L12. Accessibility basics** are partly there (aria-pressed, labels, focus ring, offscreen slider label), but: the canvas is not keyboard-operable (no `controls.listenToKeyEvents`), the slider has no `aria-valuetext` (it announces hours), the flicker and autoplay ignore `prefers-reduced-motion` (:96 only removes transitions), and charts are scrub-only by pointer.
- **L13. Stale bounding spheres** (index.html:386-390, 438). Changing the Relief slider moves vertices but never recomputes bounding spheres, so culling is based on the first render's heights. Effect is negligible except at extreme relief near the frame edge.
- **L14. selftest.py**
  - :406 writes `web/_phone.html` into the served (and publishable) folder, with no try/finally, so a timeout leaves it behind (:413 can raise `TimeoutExpired`).
  - :413 `text=True` uses the Windows locale codec, so non-ASCII console output can raise `UnicodeDecodeError`; use `encoding="utf-8", errors="replace"`.
  - It only checks console errors on first load. It never switches fires, scrubs, plays, or checks the canvas is non-blank.
  - The error regex (:415) includes "failed", which also matches harmless `Failed to load resource` lines for optional files.
- **L15. Test coverage** (test_raster.py). It covers only `fill_rings`. `arrival_hours`, trimming, the binary encodings (x*64, t/360, frp*10, arrival*10), and the JS decode have no test. Cheapest high-value test: two nested squares through `arrival_hours` assert strict monotone arrival in `(tprev, tk]` and `inf` only outside `m`.
- **L16. Overpass mirrors** (fetch.py:81-82) include maps.mail.ru and overpass.private.coffee; the manifest records the URL, but mirrors may serve a different data snapshot than the `[date:...]` attic query implies. Low risk; note it in SOURCES.
- **L17. Buildings are `way["building"]` only** (build_fire.py:339). Multipolygon building relations and node-only buildings are missing, so counts are lower bounds. Sheds and garages count as separate buildings. The "does not mean destroyed" note is there; add "OSM polygons, not homes".

## Needless complexity (safe to delete)

- index.html:327, 369-381: `uFront` is a uniform that is never changed (constant 12); inline it as a `const float`.
- build_fire.py:484 (`bld` per step) and `n_road_segments` (:527) are never read by the page; `steps[].bld` also duplicates the client's binary-search count (index.html:554).
- build_fire.py:526 `wx.get("hourly_units") and "..."` is a convoluted constant string; use the string.
- fetch.py:16 `TIGER` and :108 `TIGERWEB` both point at TIGERweb; fetch.py:12 `NLCD_WMS` (URL) and build_fire.py:28 `NLCD_WMS` (colour dict) share a name.
- selftest.py `_phone.html` iframe workaround: use `--window-size=400,860` with `--force-device-scale-factor` or Chrome's mobile emulation flag, or just drop the phone check and test narrow layout in a jsdom or Playwright script.
- index.html:225-226 recomputes `Math.max(...ay)` for every bar (:223); hoist it.
- index.html:556: `#stack.innerHTML` is rebuilt every frame during play (setT at 60 fps); update 6 `style.width` values instead.
- index.html:585-592: label placement calls `getBoundingClientRect()` and `heightAt` for every label every frame; the layout read forces a reflow per frame. Cache the box on `resize`.

## What is solid (checked, no change needed)

- Grid/texture/mesh orientation: PlaneGeometry row 0 = north, `rotateX(-pi/2)` maps north to -Z, `toZ(gy)` agrees, DEM row-major north-first matches vertex order, `sample(edges=True)` puts vertices on box edges, `fuv = (u, 1-v)` with `flipY=false` DataTexture lines up with the flipY=true colour texture. `heightAt` bilinear indexing and its clamp (`m.W-1.001`) are correct; `dem.bin` and `arrival.bin` sizes match the meta for all 7 fires.
- DataTexture sets `unpackAlignment = 1` by default, so the odd width of Creek (339) is safe.
- Encodings fit: x,y*64 <= 32768, time*10 <= 65534 for all current fires (max Tmax 1440 h = 14,400), frp*10 capped at 65535.
- Resource handling when switching fires is good: geometry, material, map texture and the arrival texture are all disposed (index.html:354, 365); a single `frame` loop and single global listeners; no listener accumulation.
- Fire with no buildings (Dixie etc. have a 0-byte `buildings.bin`), no detections in a step, a one-step fire: all handled without exceptions in the code paths I traced.
- Hillshade aspect/azimuth convention, ellipsoidal `cell_km2` correction, and the scanline fill are correct.
