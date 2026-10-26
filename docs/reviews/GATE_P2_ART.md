# Gate P2 art review: drought and flood layers

**Verdict: PASS WITH FIXES.** The data is honest and the layers read as skins, but three things hurt: card and legend clutter, the landslide confetti, and the melt smear. Fix the six items below, then ship.

**What works:** The "% of avg" cards with a bar and tick are the clearest new idea in the app. The floods rain streaks and drifting cloud deck give Helene real weather. Blue rivers stay legible under the rain.

## Top 6 fixes, by visual impact

1. **Landslide confetti (floods, all frames).** 1,402 orange dots at ~26 px pop size turn the map into noise and fight the blue rivers. In the Helene shader (~line 1802): `clamp(..., 3.0, 26.0)` becomes `clamp(..., 2.0, 14.0)`, and `uR` size*0.0028 becomes size*0.0018. Fragment (line 1808): body alpha `0.95` becomes `0.78`. Keep the flash ring, since the pop is the story. Change "other" tan (line 1804) from `0.80,0.55,0.36` to `0.62,0.50,0.40`, so road (#FA9E47) and building (#FF6B5C) stand out against it.

2. **Legend overlaps the Blantyre gauge card and the hint text (floods, desktop and phone).** Move the legend to `right:12px; bottom:56px` or hide it below `max-width:700px`. If it stays at the bottom left, shift gauge cards up with a `translateY(-60px)` offset for pins whose projected y > 0.8 of the viewport. Drop the "Drag to rotate" hint's opacity to 0.5 while any card sits behind it.

3. **Reservoir cards hide the valley and only 3 of 6 are visible (drought).** They cover Sacramento and Oroville, and the basins under them are invisible. Shrink the card to 11px type and the bar to 36x3px. Offset each card 28px up and left with a 1px leader line to its basin. Fade a card to 0.35 alpha when the camera distance is more than 1.4x the default. On phone, show only the two lowest percentages.

4. **Melt motes read as a white comet, not water (drought, Apr 2021).** Additive blending piles 3,000 motes onto the same path (line 905). Change the colour to `vec3(0.30,0.55,0.75) * vA * 0.6`, cut `NM` to 1800, raise the jitter `size*0.006` to `size*0.012`, and lower the peak alpha `0.9` to `0.6` (line 919). The result should be a faint blue thread, not a glowing streak.

5. **Snow discs look like cumulus (drought, Feb 2023).** Soft white puffs read as clouds standing on the map. At line 889 change `disc * (0.45 + 0.3*core)` to `disc * (0.30 + 0.15*core)`, make the colours cooler (`0.55,0.68,0.82` to `0.78,0.86,0.94`), and thicken the median ring: `smoothstep(0.0, 0.025, ...)` becomes `0.04`, ring alpha `0.9` stays. The gold ring must carry the reading, and the disc must stay a faint fill.

6. **Cloud deck greys out the whole terrain at peak rain (floods @57).** It hides the top-left gauge and kills terrain contrast. At line 1771 change `uD * 0.38` to `uD * 0.24`. Change the deck colour `0.32,0.36,0.40` to `0.40,0.45,0.52` so it reads as mist and not a shadow. Raise streak alpha `0.45` (line 1758) to `0.6` so the rain, not the deck, carries the intensity.

## Phone note
At 520 px the cards occupy about 60% of the map. Apply fix 3 and cap visible flood cards at 4, chosen by the largest rain-to-crest gap. The measured/model rule holds: hatched blue is still labelled "model".
