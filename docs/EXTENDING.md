# Extending CA Fire Years

Notes for adding more later. The app is an engine for "something spreads over terrain with time".

## Add another fire (about 10 minutes, mostly download time)

1. Add one `dict(...)` to `pipeline/fires.py`:
   - `wfigs`: the incident name exactly as NIFC WFIGS has it (case does not matter). Check it with the perimeter list in `web/data/state.json`.
   - `search`: a lon/lat box with about 0.25° padding around the final perimeter.
   - `start` / `end`: the ignition date minus one day, and an end 6–8 weeks later. The tail is trimmed automatically.
   - `method`: `"feds"` for 2018–2021 fires (NASA FEDS archive), otherwise `"viirs"`.
   - `note`: one factual sentence. Have it checked against a source before publishing.
2. `python build_fire.py <id>`, `python build_state.py`, `python make_sources.py`, `python validate.py`, `python selftest.py <id>`.
3. Republish `web/index.html` with the new `data/<id>/` files. Tabs come from `state.json`, so no app code changes.

Limits: FIRMS yearly archive files exist up to the previous full year (2026 is not there yet). Complexes are found by the "parts inside the reference footprint" rule in `official_parts`.

## Add a different spreading phenomenon (lava, flood, snowline, drought)

The parts that are already general:

| Piece | Where | What it needs |
|---|---|---|
| Terrain block (DEM, hillshade, AO, diorama walls) | `dem_sampler`, `hillshade`, `skirtMesh` | a lon/lat box |
| Ground texture | `nlcd_classes` + `PALETTE` | swap NLCD for another class raster or imagery |
| Roads and towns | `context_layers` (Census TIGER) | US only; elsewhere use OSM |
| Moving front | `arrival.txt` (hours since t0 per cell) + the terrain shader in `index.html` | any per-cell "time it got there" raster |
| Particles drifting with wind | `particles()` / `updateParticles()` | emitter points with times, and a wind series |
| Time-synced stats and charts | `meta.steps`, `chart()`, `setT()` | per-step numbers |
| Provenance | `common.fetch` → `manifest.jsonl` → `SOURCES.md` | nothing |

To add, for example, Kīlauea 2018 lava:
- write a builder that turns the daily USGS lava-flow polygons into `arrival.txt`, using the same `rasterize` → `arrival_hours` functions;
- change the shader's colours (lava orange-red, cooling to black);
- point the particles at the vents.

The UI needs a `kind` field in `meta.json` to pick labels and colours.

If several such apps get built, split `index.html` into `engine.js` (terrain, shader, particles, charts) plus a small per-app file. Not done yet on purpose: wait for the second user of the engine.

## Known gaps worth fixing first

- The 3D view crops wide fires on narrow phones; a fit-to-bounds camera would fix it.
- `meta.validation.official_gis_acres` double-counts merged parts (e.g. Dixie + Fly). The page uses CAL FIRE acres instead.
- Nothing has been tested on a real iPhone.
