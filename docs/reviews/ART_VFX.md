# ART_VFX: Drought and Floods

Read: both screenshots, buildDroughtScene, droughtLayers (start), floodShader, buildFloodScene, floodSetT.
Current state. Drought: flat translucent red/brown DSCI polygons on the satellite terrain, two glass tanks, a 3,200-point blue percolation Points layer (already uses R.U.uClock). Floods: HAND threshold tinted into the terrain material (`diffuseColor` mix plus a sin shimmer), 8 magenta gauge columns, 1-px river lines. Both read as map overlays, not as places. The fire tab has additive ember points and NormalBlending smoke, so "particles as data" is already the house style.

Common budget: 20k particles total on screen, one draw call per system, all motion in the vertex shader from `uClock` (no CPU per-frame loops), `pixelRatio` capped at 2, bloom half-resolution (UnrealBloomPass at 0.5 scale, or skip and fake it with additive points). Phone cost below is relative to a ~2 ms/frame budget on a mid-range GPU (estimated, not measured; test with the headless harness).

## DROUGHT (ranked by impact/effort)

**D1. Cracked-earth and dried-vegetation terrain shader (high impact, low effort).**
- Sees: as DSCI rises, the green satellite texture desaturates to straw and then to bare ochre, and polygonal desiccation cracks cut in. This replaces the flat red polygons as the main drought signal.
- Data: per-county weekly DSCI, already rasterised into the overlay texture (cidArr to DSCI). Measured.
- Sketch: patch the terrain material like `floodShader` (`onBeforeCompile`, `map_fragment`). Sample the DSCI texture `d` (0..1). `col = mix(col, dryTint*luma(col), smoothstep(.2,.8,d))`. Cracks: Voronoi edge distance of `vMapUv*180` (cell hash, 3x3 search), `crack = 1-smoothstep(0,.06,edge)`, scaled by `d^2`, darken plus a normal-ish bump via `dFdx`. Keep the colour-coded D0-D4 as thin contour lines so the legend stays honest.
- Phone: one extra texture read plus 9 hash taps per pixel. Low (~0.3 ms). Particles: 0.

**D2. Heat shimmer and dust haze (high impact, low-medium).**
- Sees: warm air wobbling over D3/D4 counties and slow dust plumes drifting across the Central Valley.
- Data: DSCI texture masks where dust spawns and sets density. Wind is the ERA5 field the fire tab already loads (measured). Label "illustrative: dust shown where drought is severe, not measured dust".
- Sketch: 6,000 Points (`aSeed`, `aUv`), position = base + wind*uClock*seed, wrapped with `fract`. Size 20-60 px, NormalBlending, alpha = `texture(uDsci,aUv).r^2*0.12`. Shimmer: render-target-free trick, a screen-space UV warp in a final ShaderPass, amplitude from the average DSCI under the view centre (one number), kept under 2 px.
- Phone: 6k soft points are overdraw-bound; cap point size at 40 px. Medium-low. Skip the shimmer pass on phones.

**D3. Evaporating reservoirs with bathtub rings (high impact, low effort).**
- Sees: Shasta and Oroville tanks become real basins. Water level falls, a pale mineral ring is left at past high-water marks, and a mist of evaporation particles rises off the surface.
- Data: `reservoirs[].acft` over `max_acft`, weekly. Measured. Replace the glass cylinders with a carved bowl (height field dug into the terrain around each x,y).
- Sketch: a disc mesh of water at `y0 + frac*h` with a fresnel and normal-scroll shader; rock-wall cone with a fragment band: `ring = smoothstep(...)` on `vY` between the current level and the record maximum, pale `vec3(.85,.8,.7)`. 400 Points per reservoir, `rise = fract(uClock*.3+seed)`, alpha scaled by `1-frac`.
- Phone: trivial (<0.2 ms, 800 particles).

**D4. Water table as a descending glowing aquifer, with seepage drips (medium-high, medium).**
- Sees: below the cut-away, a blue-to-amber sheet that sinks as wells deepen, with droplets that stop falling where it is dry.
- Data: well depth-to-water (measured, already in `droughtLayers`) for the sheet; bucket drainage `b.g` (model) for drips. The code already does this; the upgrade is visual.
- Sketch: add a fresnel plus scrolling caustic noise to the sheet material (`MeshBasicMaterial` to `ShaderMaterial`), a glow edge at the cut plane, and a stronger drip shader with a streak (stretch `gl_PointSize` by velocity, 1x4 sprite). Raise NP to 5,000 and tag them "MODEL".
- Phone: low.

**D5. Soil-water haze and bloom grade (medium, low).**
- Sees: a thin, cool low-fog where the soil is wet and a hot, glowing horizon at peak drought.
- Data: bucket soil state (model), DSCI mean (measured). Label the fog "model".
- Sketch: `FogExp2` colour and density keyed to the state-mean DSCI (one uniform tween), plus a half-res bloom with a threshold of 0.85 so only gauges, droplets and the sun-lit ridgelines glow.
- Phone: bloom ~1 ms; make it desktop-only if the FPS dips below 30.

## FLOODS (ranked)

**F1. Real water surface plus shoreline foam from HAND (highest impact, medium effort).**
- Sees: blue-tinted cells become a moving water plane: scrolling normals, specular sun glint, depth-dependent colour, and white foam along the wet/dry edge.
- Data: HAND raster and per-gauge stage rise (`uG[i].z`), already in the shader. Foam = band where `abs(di) < 0.15`. Measured stage, illustrative extent (keep the existing "illustrative" label).
- Sketch: in `floodShader` replace the flat `wc` with `n = normalFromTwoScrollingNoise(vMapUv*600, uClock)`, `fres = pow(1-dot(N,V),3)`, `foam = band * fbm(uv*900+uClock*.5)`. Make the edge animate by adding `0.05*sin(uClock)` to `di`. Add a `uFloodDepthAlpha` ramp so deeper water goes darker and more opaque.
- Phone: fragment-only, ~12 texture/noise taps on wet pixels only (gate with `if(wet>0.01)`). Low-medium. Particles: 0.

**F2. River-flow particles advected along the polylines (highest impact, medium effort).**
- Sees: glowing dashes streaming down every river, thickening and speeding up as the flood arrives.
- Data: discharge `q` at the nearest gauge (15-minute, measured) sets speed and density; rivers from `meta.rivers` (TIGERweb). Between gauges the value is the nearest-gauge value, labelled so.
- Sketch: pre-bake each polyline to a cumulative-length table; per particle attributes `aLine`, `aS` (arc-length offset), `aSeed`. A DataTexture (RGBA float, one row per polyline) holds the xyz at uniform arc-length steps; the vertex shader reads `pos = texture(uPath, vec2(fract(aS + uClock*speed), line))`, `speed = k*sqrt(Q/Qmax)`. Uniform `uQ[8]` is updated in `floodSetT`; each particle picks its gauge by `aGauge`. 9,000 additive Points, 3-5 px, streak along the tangent.
- Phone: vertex-bound texture fetch, ~0.4 ms. Medium-low.

**F3. Rain streaks and storm cloud deck (high impact, low-medium).**
- Sees: slanted streaks falling over the basin and a dark cloud layer at peak.
- Data: no rain field in the supplied meta. Either add a measured source (NOAA Stage IV or Multi-Radar MRMS hourly total) or drive the intensity from the **rate of rise** dQ/dt of the gauges and label it "storm intensity proxy from river rise, not measured rain". Do not use fake rain.
- Sketch: 6,000 line-sprite Points in a box over the terrain, `y = fract(-uClock*v+seed)`, stretched `gl_PointSize` plus rotation by a wind vector; a large noise-textured plane at +0.25 size units, alpha = intensity.
- Phone: low if streaks are points, not lines.

**F4. Splash and turbulence at the gauges (medium, low).**
- Sees: spray puffs and rings around each gauge column that scale with discharge.
- Data: `q` (measured) mapped to emission count; colour from the flood category.
- Sketch: 250 Points x 8 gauges = 2,000, a ballistic arc in the shader `y = v*t - 0.5*g*t^2`, with `t=fract(uClock*r+seed)`.
- Phone: negligible.

**F5. Mist, wet-ground darkening and bloom (medium, low).**
- Sees: valley fog rising off the water; saturated, darker ground that persists after the water recedes; glowing gauges.
- Data: `wet` and the stage rise from the existing shader; persistence by a decaying max (`uWetMemory`, a texture ping-pong or a CPU scalar per gauge). Measured stage, illustrative extent.
- Sketch: darken `diffuseColor` by `0.35*wetMemory`, 2,000 low-alpha billboard Points over cells where `wet>0.3`, and half-res bloom.
- Phone: low.

## Do first (3)
1. **F1 + D1 shaders.** They are fragment-only patches to material code that already exists (`floodShader`, terrain material). No new particles, no new data, and they fix the "flat overlay" look at once.
2. **F2 river-flow particles.** The strongest "data is alive" effect. All inputs (polylines, discharge) are already in meta.json.
3. **D3 reservoir basins with bathtub rings and mist.** It uses measured storage, costs under 1k particles, and replaces the weakest asset in the drought scene (glass test tubes).

Then D2/F3 particles, then the bloom pass last, tested against the 30 fps target on a real phone.
