# Engagement report: Hazard Replays

Reviewer: independent engagement review, 2026-10-21. No file in `web/` or `pipeline/` was edited. The review scripts and screenshots are not included in this repo.

**Tested file:** `web/index.html`, modified 2026-10-20 22:37:35 (-0700), 142,184 bytes. It was not modified during the review.
**Method:** headless Chrome with SwiftShader at 1400x900 and at 400x860, which is a 400 px iframe because Chrome will not open a window that narrow. I also read the UI text and the panel code. I saw each tab at its default frame, and some at a later time (`#ridgecrest@60`, `#dixie@120`). I did **not** play any replay through, use touch, or use sound. Everything below about people is my judgement, not a measurement. Scores are 1 (poor) to 5 (strong).

## 0. Answer first

1. **The app as it stands on disk does not run.** `web/index.html` line 1047 declares `const mercY` a second time (the first is at line 557). Chrome logs `Uncaught SyntaxError: Identifier 'mercY' has already been declared`, so the whole module fails. The user sees the header and an empty page, on every tab. I confirmed this in a screenshot, and I confirmed the console error twice. This looks like leftover from the paused hurricane or drought edits.
2. **Drought is also broken after that is fixed.** I tested a copy with line 1047 and its use at 1063 renamed (`review/engagement/index_fixed.html`, served by `serve.py` with the real `web/data`). Drought then shows "Could not load the data: data/ca-drought/wells.txt: HTTP 404". `web/data/ca-drought/` has no `wells.txt`. The code expects the new wells layer, and the data build (A.1 of the plan) has not produced it.
3. **With those two fixed, the other tabs work and look strong.** Fires, Earthquakes, Hurricanes and Floods all render. The visuals are the best part of the app. The weak spots are the first 10 seconds, phone layout, and the long, jargon-heavy panel. Nothing in the app asks the reader to think or guess.
4. **The plan's "Key moments" strip is the best item in section B. "What happened" cards are the worst.** Several other B items already exist in the app.

## 1. Persona walkthroughs

Time-to-first-insight (TTFI) is what I think each persona learns in the first 10 s and 60 s. Estimated, not measured.

### Persona-by-tab scorecard (1 to 5; "lesson" = does the decision lesson come across)

| Tab | (a) Curious reader, iPhone | (b) County emergency manager | (c) HS earth-science teacher | (d) Skeptic checking numbers | Lesson comes across? |
|---|---|---|---|---|---|
| Fires | 3 | 3 | 4 | 4 | 2 (no lesson stated) |
| Earthquakes | 2 | 4 | 4 | 4 | 3 (warning what-if is good but buried) |
| Hurricanes | 3 | 3 | 4 | 4 | 2 |
| Floods | 3 | 4 | 4 | 4 | 3 (the "never drive into flood water" box is the only lesson, and it is generic) |
| Drought | 1 (broken now) | 1 (broken now) | 1 | 1 | not testable |

Why the iPhone reader scores low: the page makes them read before it shows them anything move (see 2).

### Fires (Statewide, then Dixie)
- **First 10 s.** Statewide: a dark map of orange and white blobs with town names, and the hint "Hover a perimeter for details. Click a highlighted fire to replay it in 3D." On a phone nobody can hover. Dixie opens already at day 23 of the replay, with a burned area, glowing fire line and smoke, which is a good first frame.
- **First 60 s.** Press play, watch the line grow, read 364,260 acres. The chart has a clear jump (the 7,650 acres/hour spike) but nothing says "this is the night the fire blew up".
- **Main confusion.** What to do first: three rows of nav chips, then a map, then a play button. KPI labels such as "fire radiative power, MW (sum, this 12 h)" are expert wording.
- **Stay or leave.** Stays: 3D terrain, glowing fire line, towns. Leaves: nothing tells them why this fire matters for a decision (evacuation time, ember spread, fuel).
- **Lesson.** Absent. The note is a one-line fact ("destroyed Greenville").

### Earthquakes (Ridgecrest)
- **First 10 s.** A static, dim terrain with orange fault lines, all counters at 0, and "Day 1 of the replay". Nothing moves. The reader must find the small orange play button. This is the weakest first frame of the tabs I saw.
- **First 60 s.** Press play and the map fills with white dots; by hour 60 the blooms hide the terrain (`quake60_phone.png`). The 34-hour wait between the M6.4 and the M7.1 is the story, but the app only tells it in one sentence.
- **Main confusion.** "MMI", "depth drawn at 1.6x", "ALOS-2", "ShakeAlert issued an alert in 7.4 seconds" with the source name pasted into the panel. The warning what-if starts below the fold, after the shocks list and the MMI legend.
- **Stay or leave.** Stays: the ring, the what-if slider (it is the only real interaction in the app), the aftershock clock. Leaves: dim empty first frame; a wall of text on a phone.
- **Lesson.** Strongest in the app for the emergency manager: "in N seconds you can do X". But it sits below the fold on desktop and several screens down on a phone.

### Hurricanes (Helene)
- **First 10 s.** Opens at hour 70 of 120, a bright eye with wind streaks, rain colours, rings and city names. It looks striking. It also shows five layers at once.
- **First 60 s.** Read "115 kt, Category 4". The surprise, that Asheville, 500 km inland, has more rain so far (199 mm) than the landfall area (73 mm) at this moment, is in two small KPI tiles that look equal to the others.
- **Main confusion.** Wind streaks are "modelled", rain is "reanalysis", the numbers differ from NWS gauges. The caveat paragraph under the charts says gauge totals are far above the model in the mountains. A skeptic will like that honesty; a curious reader will not know which number to believe.
- **Stay or leave.** Stays: the visual. Leaves: the "what should I take away?" gap. The decision lesson (inland flooding kills more people than wind) is never stated.
- **Lesson.** Absent.

### Floods (Western NC)
- **First 10 s.** Opens at day 3 (27 Sep, noon) with magenta gauge columns, rings and blue flood overlay near Fletcher. Clear and dramatic. A safety box tells the reader to never drive into flood water.
- **First 60 s.** "8 of 8 gauges at or above flood stage", "7.0 m rise at Asheville, measured". Good numbers.
- **Main confusion.** "Illustrative, not a flood map" appears twice, and "HAND" in the method; the reader may not trust the blue area but cannot tell which parts are measured. Magenta columns have no label for what the colour means until the legend further down.
- **Stay or leave.** Stays: seeing the river rise at each gauge. Leaves: the overlay is hard to judge against reality.
- **Lesson.** Partly: the safety box. A time-to-crest lesson (how long between the rain peak and the crest downstream) is in the data but not shown.

### Drought (California 2020-2023)
- **Broken in the tested build** (see 0). From reading the code: KPIs for D2+ and D4 share, reservoir storage, three map modes (DSCI, soil water model, GRACE), three layers and a cut-away. That is a lot of controls before a reader knows what "DSCI" is. Opening with a single clear map and one sentence would work better.

## 2. First frame and onboarding

- **Purpose without reading.** The header says "Hazard Replays" and there are five tab chips. That gives the topic but not the promise ("watch it unfold, then see what you could have done"). There is no one-line tagline and no cue to press play.
- **Controls.** The play button is clear on desktop. On a 400 px phone the page scrolls: the nav takes three chip rows on Fires (about 265 px before the map starts, `fires_phone.png`), the scene is about 35 % of the screen, and the play button is below the scene. The 3D hint ("Drag to rotate, right-drag or two fingers to pan") is helpful but is the only teaching text.
- **Legibility at phone size.** Text is readable and nothing overflowed in the frames I saw. The layout is a single long column, so the date, KPIs and charts require a lot of scrolling. I did not measure panel length.
- **Empty first frame.** Earthquakes opens at hour 0 with all counters at 0. Fires and Hurricanes open mid-replay, which works better. Make Earthquakes do the same (or autoplay a short intro).

## 3. Pattern audit against `mini-globe/scout/ENGAGEMENT.md`

| Pattern | Present? | Evidence |
|---|---|---|
| 1 Author-driven spine | No | Free replay only. No chapters. |
| 2 Animated transitions | Partly | Time playback is smooth. Tab changes are page swaps (not checked for animation). |
| 3 Short, user-started guidance | No guidance at all | Only the drag hint. This is cheap to fix with 2-3 steps, user-started. |
| 4 Predict then reveal | No | No guesses anywhere. |
| 5 Closeness feedback | No | |
| 6 Place-based serendipity | Yes | Town labels; fire tooltips on the statewide map. Hover is useless on a phone. |
| 7 One layer at a time | Partly | Hurricane and Drought show many layers at once; Fires shows few. |
| 8 Short captions that change with time | No | The note is static. Only numbers change. |
| 12 Juice | Partly | Eye bloom, ring and fire glow are strong. |
| 15 Explorable explanation | Yes, once | The quake alert-delay slider. It should be the model for the other tabs. |

Anti-patterns present: **#4 many layers at once** (Hurricane: streaks + rain + rings + eye bloom + labels; Quake at hour 60: white blooms hide the terrain). **#5 settings before value** (Drought: three map modes and three layers). **#2 static or empty first screen** (Earthquakes). **#3 all reading, no doing** (every tab except the quake slider). **#11 no visible end** (I did not test what happens at the end of a replay).

## 4. The plan's section B: will it add engagement or clutter?

Ranked best to worst:

| Rank | Item | Verdict | Why |
|---|---|---|---|
| 1 | **Key moments strip** (4-8 chips, deep links) | Adds engagement, high | It is the missing author-driven spine. It also fixes "what do I click". Keep one sentence each and put it **under the timeline**, not in the long panel. Cap at 5-6 chips. |
| 2 | **"What it teaches" decision card** | Adds engagement, high, if short | It is the only item that gives the reader a reason to care. Keep to 40 words, directly under the date line, with one action verb ("With 10 s of warning you can stop a train"). A long card becomes more panel text. |
| 3 | Flood: per-gauge peak stage vs flood stage and record, time-to-crest | Medium | Per-gauge cards with peak, record and stage already exist. What is new is the **order of crests** (who crested first, how long after the rain). That is a real insight. A plain table is clutter. |
| 4 | Drought: reservoir % of capacity with historical-average line | Medium | % of capacity is easier to read than acre-feet. Only the source gives an average; label it. |
| 5 | Drought: D2/D3/D4 share per week | Low | A weekly stacked bar for "this week" and a D2 chart already exist in the code. Add D3/D4 lines to the existing chart rather than a new one. |
| 6 | Hurricane: peak wind and pressure over time with landfall marked | Low | Wind and pressure charts already exist (`c-hw`, `c-hp`), and the landfall is already in the note and the cursor. Add only a landfall marker line. |
| 7 | Hurricane: 34/50/64 kt radii | Low as new work | Already drawn as rings with legend. Skip. |
| 8 | Earthquake: counts by magnitude band over time | Low | A magnitude-count chart (`c-qc`) and 6-hour chart exist. A third chart adds clutter. |
| 9 | Hurricane rainfall totals | Low | ERA5 totals exist and the panel already says they are lower than NWS gauges. More numbers will confuse. Add NWS gauge totals (13.98 in Asheville, 31.33 in Busick) only as the key-moment text. |
| 10 | **"What happened" summary card** (peak values) | Clutter | It repeats the KPI tiles, the charts and the note. Cut it. Show the peak as a key moment chip instead. |
| 11 | Fires: leave as is | Disagree in part | The Fires tab has no lesson and no hook either. It needs the same chips and teach card. |

### Up to 5 better or cheaper ideas (free data named)

1. **Quake "how many seconds?" guess.** Before the what-if reveals, ask "How many seconds of warning would Ridgecrest have had?" with four buttons (0, 5, 10, 20+). Then show the true value and place the guess on the same gauge. Data: USGS ShakeMap and IRIS FDSN stations, already in the app. Cost: S.
2. **Hurricane "where was the most rain?" guess.** Ask "Coast, or the mountains 500 km inland?" then show Asheville 199 mm vs the landfall area 73 mm at hour 70, and the later NWS 13.98 in. Data: ERA5 via Open-Meteo (in the app) and NWS/NC State Climate Office totals (already cited). Cost: S.
3. **"Did you feel it?" overlay for Ridgecrest.** Real felt-reports (a human voice) next to the modelled shaking. Data: USGS DYFI `dyfi_geo_10km.geojson` (1.1 MB, tested V in ACTIONABLE_SCOPE E3). Cost: M.
4. **"When did it reach my town?" for fires.** A search box or tap on a town label shows the day and hour the perimeter reached it, with the time to the next 12 h step. Data: the app's own arrival times plus Census TIGER places (already loaded). Cost: S-M.
5. **Flood "crest race."** One chart ordering the 8 gauges by time of peak, upstream to downstream, with rain peak marked. This shows the warning window downstream towns had. Data: USGS instantaneous values already in the app, plus the ERA5 peak-rain hour. Cost: S.

## 5. Top 10 changes, ranked by impact over effort

| # | Change | Where | What | Why |
|---|---|---|---|---|
| 1 | **Fix the two blockers** | `web/index.html:1047` and the drought build | Rename the second `mercY` (or reuse the first with a scale factor). Run `build_drought_extra.py` so `data/ca-drought/wells.txt` exists, or hide the wells layer when the file is missing. | Nothing else matters if the page is blank. Add a visible error message in the page for module failures, since right now there is none. |
| 2 | **Non-empty first frame for Earthquakes** | `showFire` for `ridgecrest` | Start at hour ~33 (just before the M7.1) or autoplay the first 10 s once. Add a caption "Two earthquakes, 34 hours apart. Press play." | Fixes the worst first frame. Cheap. |
| 3 | **Key moments strip** | Under the timeline, all tabs | 4-6 chips. Example Ridgecrest: "M6.4 foreshock", "34 h quiet", "M7.1", "Alert what-if", "Aftershock clock". Example Helene: "Landfall", "Rain reaches Asheville", "Peak rain". | The plan's best item. Also doubles as the guide the app lacks. |
| 4 | **"What it teaches" card at the top** | First block of the panel | 30-40 words, one action. Example: "In the first 3.4 s the P wave is still far from most towns. A 5 s delay means towns within about 20 km get no warning." | Gives the emergency-manager and teacher personas their reason to stay. |
| 5 | **Phone layout** | `@media (max-width: 860px)` | One scrolling row of chips for hazards and events instead of 3 wrapped rows; put play and the time slider on top of the scene; hide the nav on scroll. | On 400 px the Fires nav is about 265 px tall and the scene about a third of the screen. Replays are the product, so they should be first. |
| 6 | **One guess before one reveal per tab** | Ideas 1 and 2 above; the same pattern for Floods and Drought | A single question with 3-4 buttons, then the reveal and the true value. Skippable. | The app has no predict-then-reveal at all. It is the strongest pull in the research file. |
| 7 | **Plain wording first, source second** | Panel text | Replace "MMI", "DSCI", "HAND", "ERA5" with plain labels, with the term in brackets. Move "UC Berkeley news (17 Oct 2019) reports..." and similar source lines into "Method and checks". | The alert paragraph runs about 90 words in the main flow. The skeptic persona needs the sources, but they can sit in the details. |
| 8 | **One layer at a time on Hurricane and Drought** | Layer checkboxes | Open Hurricane with wind **or** rain, not both, plus a caption telling which. Open Drought with only the DSCI map; put the soil and GRACE modes under "More layers". | Layer overload and settings-before-value are on the anti-pattern list. |
| 9 | **Changing caption on the scene** | Over the 3D view | One short line that changes at key moments (for example "Hour 70: more rain inland than at landfall"). | Gives the replay a narrator without more panel text. Research file pattern 8. |
| 10 | **Make the panel shorter by default** | Panel | Keep date, teach card, 4 KPIs, one chart. Put the other charts and the method under "More charts and checks". | The panel is a long column on a phone. I did not measure its length. |

## 6. What needs real users to verify

- Whether people press play unprompted when the first frame is static (my guess: many will not).
- Whether the quake what-if is found, read and understood by non-specialists, on a phone and a desktop.
- Time spent and drop-off by tab. Log: first interaction, play pressed, tab switches, chips tapped, panel scroll depth.
- Whether the "illustrative" and "modelled" labels build trust or put people off (the skeptic persona and a general reader may disagree).
- Whether predict-then-reveal helps or feels like a quiz in an app that is currently calm.
- Real iPhone behaviour: touch rotate, the page scroll inside the iframe-free layout, Safari WebGL load time, data per tab on cellular.
- The end of a replay, sound (none tested), and reduced-motion behaviour.

## Limits of this review

- Headless Chrome with software WebGL; the 400 px frames use an iframe.
- I tested the **file as it stood** (modified 2026-10-20 22:37:35). A builder may already have changed it.
- Rendering of Fires, Earthquakes, Hurricanes and Floods was tested through a patched copy, not the file on disk.
- Persona scores and time-to-insight are my judgement. Nothing here is user data.
