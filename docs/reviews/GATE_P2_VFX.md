# Gate P2 VFX: verdict PASS WITH FIXES

Read from code and 2 desktop screenshots (drought 11000, Helene 57). Not measured: fps, phone GPU, the other screenshots.

What reads well: Helene rain streaks, cloud deck and slide dots read as intended. Streak, deck and slide colours stay below bloom threshold (alpha-blended). The melt motes are the problem (fix 1).

## Fixes, bugs first

1. **Melt motes blow out in bloom (seen: white comet near Sacramento).** All sites' paths converge on one reservoir, and the motes add up. Line ~905, change
`vec3(0.30, 0.55, 0.75) * vA * (1.0 - 1.6 * d)` to `vec3(0.30, 0.55, 0.75) * vA * 0.35 * (1.0 - 1.6 * d)`;
in droughtTick change `Math.sin(Math.PI * M.mph[q]) * 0.9` to `* 0.6`. Also raise the fade at the path end: `* (1.0 - M.mph[q] * M.mph[q])`.

2. **NaN in snow shader (line ~886).** `smoothstep(0.0, vS, d)` has equal edges when a site has no data (vS = 0). That is undefined in GLSL and NaN on some GPUs, and NaN passes `a < 0.01`. Change
`core = 1.0 - smoothstep(0.0, vS, d)` to `core = 1.0 - smoothstep(0.0, max(vS, 0.02), d)`,
and add `if (vS < 0.01 && vM < 0.0) discard;` as the first fragment line.

3. **Point sizes ignore pixel ratio.** `uScale` is built from CSS height (resize(), ~line 2183) but `gl_PointSize` is in drawing-buffer pixels. On a DPR 2 phone every uScale sprite (rain streaks, snow, slides, embers) is half the intended size, and the 3 px minimum clamp becomes 1.5 CSS px. Change
`R.U.uScale.value = box.height / (2 * Math.tan(...))` to `R.U.uScale.value = R.renderer.getPixelRatio() * box.height / (2 * Math.tan(...))`.
Check that the fire embers still look right; they will grow on DPR 2 only.

4. **Float texture filtering is not guaranteed (lines 856, 1745).** `RedFormat + FloatType` with `LinearFilter` needs `OES_texture_float_linear`. Without it, sampling returns 0 and the rain silently vanishes. Change
`rt.minFilter = rt.magFilter = THREE.LinearFilter;` to
`rt.minFilter = rt.magFilter = R.renderer.extensions.has("OES_texture_float_linear") ? THREE.LinearFilter : THREE.NearestFilter;`
(or switch to HalfFloatType with `THREE.DataUtils.toHalfFloat`). Format and type are otherwise valid on WebGL2.

5. **Slide pop is too short to see at replay speed.** At 6 h/s, `exp(-vAge*1.2)` decays in about 0.14 s, and debris lives 3 h = 0.5 s. Change
`1.0 + 1.6 * exp(-vAge * 1.2)` to `1.0 + 1.6 * exp(-vAge * 0.4)`, and `float flash = exp(-max(vAge, 0.0) * 1.2)` to `* 0.4`.
Debris: `smoothstep(2.0, 3.0, age)` to `smoothstep(5.0, 8.0, age)`.

6. **Texture upload and loops run every frame while playing.** `floodUpdate` does 3 passes over nC cells (rainBuf, cumAt sum/max) plus a texture upload each frame, and the cum table is (hours+1)*nC floats. Guard with the hour index: add `if (h === FL.lastH && f === FL.lastF) skip` or update the buffer only when `Math.floor(T*4)` changes (4 Hz is enough). Same for `droughtRain` (only changes by week). nC was not measured; check `MR.nx*MR.ny`, and if above ~60k, do the sum/max on a 4x-downsampled grid.

7. **Phone cost (estimated).** Counts are fine: rain 5k, melt 1.5k, debris 4 x N, all one draw call each. But the debris is 4 x 1,402 = 5.6k points that are mostly size 0 (`gl_PointSize = 0` still runs the vertex stage; cheap). Real phone risk is the transparent overdraw of 48 px streak quads (largest clamp 48 px, 5k of them) and the full-screen deck. Lower the streak clamp to 28 on phone: `clamp(..., 3.0, 48.0)` to `clamp(..., 3.0, ${innerWidth < 700 ? 28 : 48}.0)`. Bloom: set `bloom.resolution` half size on phone.

8. **Minor.** Melt paths are straight lines, not flow lines; they cross ridges (labelled ILLUSTRATIVE, acceptable). Snow clamp 90 px may exceed `ALIASED_POINT_SIZE_RANGE` on some mobile GPUs (often 64 to 256); clamp to 60. Deck plane: transparent, depthWrite off, renderOrder 7 draws after streaks (6), so no sort bug. Deck dims everything under it when the camera is low; acceptable.

No per-frame allocation found in droughtTick (typed arrays reused). Frustum culling is correctly off for all shader-moved Points.
