# Art direction: Drought and Floods tabs

Basis: screenshots of ca-drought@14000, helene-wnc@60 (desktop and phone), and the Caldor tab as the benchmark. Code not edited.

## Why Caldor works, and these two do not

Caldor keeps the terrain as the hero. Its data (glowing perimeter, smoke) is light and heat sitting on the land, the sky has a horizon, and each label earns its place. Drought paints over the land. Floods lays UI widgets on it. Rule for both tabs: **data is a skin or a light source on the terrain, never an object standing on it.**

Honesty rule for both tabs: **measured = crisp edges, solid fill; illustrative or model = soft edges, hatch or dither, lower opacity, and the "MODEL" badge repeated in the legend swatch.**

---

## DROUGHT

**Concept:** California as a landscape slowly losing its colour: a wet green-gold state bleaches, cracks and browns as the USDM classes spread, then recovers in winter 2023.

**Palette (USDM stays recognisable, applied as a tint)**
Use the official USDM hues but drive them as a multiply/soft-light tint on the satellite terrain at 45-60% strength, so ridges and rivers still show through.
- D0 abnormally dry `#FFFF00`, drawn at only 25% (it is a watch, not a drought)
- D1 moderate `#FCD37F`
- D2 severe `#FFAA00`
- D3 extreme `#E60000`
- D4 exceptional `#730000`

The current slab red is saturated and opaque, so D2 and D3 are indistinguishable. Soften the ramp for the in-scene tint (D1 `#E9C46A`, D2 `#E08A2E`, D3 `#C0392B`, D4 `#6B1414`) and keep the exact USDM hex only in the legend chip for recognition. Add a faint 1 px county outline in `#FFFFFF` at 18% opacity. Replace the flat extruded slabs with a flat draped layer at terrain height + 0.5 px. No extrusion.
- No-drought counties: leave the land untinted (not green).
- Nevada and Oregon: desaturate to 60% and darken 25% ("context, no data"). Add a small "USDM covers California only" caption, or tint the same data if the source has it.

**Lighting and sky:** Low, raking sun from the west (azimuth about 250 degrees, elevation 20 degrees) so the Sierra and Coast Range cast long shadows. Sky gradient from `#0B1320` at the zenith to a dusty `#C9A27A` at the horizon, thin haze fog `#B88F6A` at density 0.0012. As D3/D4 coverage rises, push the haze warmer and the sun slightly lower. Reverse during the 2023 recovery. This makes the timeline legible without reading a number.

**Camera and opening shot:** Open high and oblique, looking north-north-east along the Central Valley, so the valley is the central axis and the Sierra is a backdrop. Fit the state to about 85% of the viewport width. Then a slow 10-degree dolly in over the first 3 seconds and stop; drift only while paused. Phone: rotate the framing to portrait, state vertical, camera nearer top-down (60 degrees tilt).

**Markers (reservoirs):** Replace the blue cylinders with a flat "lake level gauge": a thin ring on the water body whose fill-arc shows percent of capacity (Shasta, Oroville), with a 12 px dot of `#4EA3D8` and a white arc. Small, flat, billboarded. Draw measured gauge in solid, GRACE/soil model layers as a texture (see below).

**Illustrative layers:** Soil water and groundwater (GRACE) are models, so render them as stippled or diagonal-hatch overlays at 35% opacity, never as the same solid fill as USDM. Wells: 3 px points, `#F2F2F2`, with a halo.

**Labels:** Keep six cities only (Sacramento, Fresno, Bakersfield, LA, San Francisco, San Diego). Drop Oakland, San Jose, Stockton, Anaheim and Irvine; they collide. White 12 px text, 1.5 px dark halo, no pill.

**Legend:** Move the legend off the panel's scrolled-off bottom edge. Put a 5-chip class strip, 8 px high, at the lower-left of the 3D view with a "% of state" readout under each chip. The current gradient bar sits below the fold on desktop and phone.

**Motion over time:** Colour should cross-fade between weeks over about 300 ms (no pops). Add a thin date-scrubber tick strip showing statewide D2+ area (a sparkline) behind the slider, so the arc of the drought is visible before pressing play. Slow the default speed in the peak months.

---

## FLOODS (Helene, western NC)

**Concept:** A mountain region at dusk, with rivers swelling from thin blue threads into brown, silver-lit torrents as the storm crest moves down the valleys.

**Palette**
- Normal river: `#5C8FB8`
- Rising: `#E8C547`
- Above flood stage: `#F4783A`
- Major/record: `#E5384F`
- Modelled inundation (illustrative): `#3A7CC4` at 45%, hatch-edged
- Storm-water turbid brown for the river ribbon at peak: `#8A6A44`

Remove the magenta and the orange/purple double rings. The stage ramp is a single-hue-ish sequence (blue to amber to orange to red), colour-blind safe against the green terrain.

**Lighting and sky:** Overcast storm mood: cool grey-blue sky gradient `#20303F` to `#6B7A86`, soft fog `#56646F`, a low, diffuse key light and 30% less terrain saturation. Add a faint rain streak layer driven by the rainfall data, only while rain is above threshold. At the crest, a subtle brightening of the river material (emissive `#BFE3FF`) makes water read as water. Today the water is a flat blue sliver on green and barely stands out.

**Camera and opening shot:** Start low (25 degrees above horizon) looking up-valley along the French Broad toward Asheville, so the terrain walls frame the river. Pull up to the current oblique view after about 4 seconds. Follow the crest: as the replay plays, nudge the look-at target to the gauge currently peaking (eased, 1.5 s).

**Markers (gauges):** Replace the pillars with a flat **hydrograph pin**: a 10 px circle at the gauge, coloured by stage class, with a 40 x 18 px sparkline of the last 24 h of stage in a dark rounded card. Anchored to the river by a 1 px leader line. Size is fixed on screen. Crest time shows as a small tick on the sparkline, and "CREST" appears once, not continuously. Measured gauges: solid disc. Anything modelled: dashed outline.

**Water:** Draw rivers as a ribbon whose width and brightness scale with stage ratio (measured, solid). Draw the 111 km² inundation as a separate, soft-edged polygon with hatch fill and a "MODEL" tag (illustrative). The two must never share a colour.

**Labels:** Gauge name in 11 px white text with a dark halo only for the 3 currently active gauges; others fade to 40%. Keep towns (Asheville, Hendersonville) in grey italic so they read as geography, not data. Today the blue labels compete with the pillars.

**Legend:** Bottom-left of the scene: stage ramp (4 chips) plus a "solid = measured, hatched = model" key. Not in the scrolled panel.

**Motion over time:** Crest waves should travel downstream: animate a bright pulse along the river ribbon at the observed crest travel speed. That shows the lesson in the panel's own title ("a crest takes time to arrive"). The timeline at 6 h/s is fine; ease to 1 h/s automatically around Sep 27.

---

## Top 5 changes, in order

1. **Drought: swap opaque slabs for a draped, semi-transparent tint (45-60%) with county outlines.** The terrain returns and the biggest visual complaint is gone.
2. **Floods: replace the magenta pillars with flat stage-coloured pins and sparklines.** They stop reading as UI widgets.
3. **Floods: make water visible.** Widen and brighten the river ribbon by stage, add a downstream crest pulse, and use the storm-sky mood.
4. **Both: add a real sky and haze with directional low light, and set an opening shot per tab.** This brings them to Caldor quality.
5. **Both: encode measured vs illustrative (solid vs hatched, with badges), and move the legend into the scene.** It fixes honesty and the missing legend in one pass.
