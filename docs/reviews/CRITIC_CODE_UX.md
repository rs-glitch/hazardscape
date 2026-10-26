# Critic: code and UX gate (2026-10-21)

**Verdict: SHIP** (no blocker found). Four medium or low items below should be fixed in the next pass.

## Checks run
- Module script extracted, `node --check`: OK.
- `pipeline/selftest.py` for state plus 16 events (ca-drought, helene, helene-wnc, ridgecrest and all 12 fires) at 1400 and 400 px: all ok, no console errors. PNGs read for ridgecrest 400, dixie 1400, ca-drought 400: first frame, teach card and chips render; phone layout legible, no horizontal overflow.
- Own headless driver (iframe, same origin, port 8790): 3 rounds of rapid hazard and event switching (21 hazard clicks plus event clicks, 60 ms apart). Final state consistent: one `.mom` card, one `details.more`, no duplicate panels, zero console or unhandled-rejection errors. Chip click on the last chip of Earthquakes, Hurricanes, Floods and Drought: slider moved to the chip hour, caption set, URL updated.
- XSS: every moments/meta string goes through `esc()` (index.html:1669-1671, LESSONS_HTML 701-707); chip text uses textContent. No issue.
- Publish files: each at most 1.85 MB (grace.txt 1,847,560 largest); no file in web/ over 16 MB; 16 moments.json present; no stray `_phone.html` left in web/.

## Engagement report items
- #2 Ridgecrest first frame: MET (opens at hour 33, caption "Two earthquakes, 34 hours apart. Press play.").
- #3 Key moments chips: MET on all tabs (3-7 chips, derived from meta). Weakness F4.
- #4 "What it teaches" card: MET (27-36 words, one action).
- #10 Shorter default panel: MET (fold closed under 860 px, open above). Weakness F3.

## Findings, ranked
1. **MEDIUM** index.html:1685 (and boot 1649): chips write `#id@h` but tab and category clicks never update or clear the hash. Repro: open Drought, click a chip, click Fires: URL stays `#ca-drought@34944` (measured). Reload or share opens the wrong view. Fix: in `showFire`/`showState`, call `history.replaceState(null,"",id?"#"+id:location.pathname)`.
2. **MEDIUM** index.html:419: wells.txt, bucket.txt and grace.txt are loaded in one `Promise.all`, so any missing file fails the whole Drought tab ("Could not load this event"). Not optional. Fine while all three are published, but a partial publish gives a dead tab. Fix: `.catch(() => null)` per file and hide the matching layer or mode.
3. **LOW** index.html:1679-1688: on phones the teach card straddles the fold (scene is 56vh) and the chips sit below it; user must scroll to find them. Phone items #5 and #9 from the engagement report are still not done. Fix: put the chips row directly under the timeline on <=860 px.
4. **LOW** data: duplicate-hour chips: bridge 72/72, eaton 12/12, palisades 24/24, york 48/48, helene 75/75.17. Two chips do the same jump. Fix in `pipeline/build_moments.py`: drop a moment whose hour is within 1 h of the previous one.
5. **LOW** index.html:1685: `replaceState` overwrites the hash, so deep-link flags (`,warn`, `,wells,table`, `,soil`) are lost after a chip click. Fix: keep the suffix after the first comma.
6. **LOW** index.html:1688: the scene caption stays after play moves past that moment (known #9, not done); it can describe a time that is no longer on screen. Fix: hide `#cap` in the play loop when |T - chip hour| > 12 h.
7. **INFO** No `hashchange` listener (stress F6 half-fixed: chips use setT, as asked; pasting a new hash into an open page does nothing).
8. **INFO** BUILD_REPORT.md file list covers the changed files only. It does not list each event's unchanged meta/tex/dem files; confirm the host already has them.
