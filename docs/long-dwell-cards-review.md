# Long dwell observing plan and compact target cards

Base: `7cc8ff1ae1023691fdee290d4bd15d62ee5e6514`, isolated branch `codex/long-dwell-cards`. Local review only; not released.

## Confirmed changes

The old scheduler substituted the earliest-setting target for the highest-ranked target whenever its integration goal was finite. Reconsidering at visibility boundaries caused short switches. The new policy selects the highest-ranked currently viable target and holds it until its remaining goal or continuous visibility window ends. Later risers do not interrupt it. Setup and whole-frame budgets still apply. Short final goals may finish without an arbitrary 30-minute minimum; the planner admission gate now permits these as well.

The planner altitude floor is 35°, with threshold crossings refined to one-minute samples and conservative inward time rounding. Existing disjoint windows, location/timezone context and exact exposure accounting remain. Real horizon obstructions are still not modeled in this branch, and the UI continues to disclose that limitation.

Three to four targets is a preference achieved through long dwell, not a forced quota. One or two targets can be appropriate. If more than four are selected to use remaining windows/goals, the UI says so; the scheduler never silently truncates. Best-target-first can leave later gaps that an earliest-setting policy could have avoided. It does not claim globally optimized coverage.

Mosaics remain explicitly manual visibility opportunities. They do not claim panel counts, exposure settings, setup times or verified imaging credit. Completed scalar integration goals still exclude them. A positive scalar goal does not establish a per-panel mosaic completion time.

## Persistent gap

Independent review verified intact mosaic propagation on the released base. An isolated reproduction with real default-Arizona October 17 astronomy and synthetic completed M31 history exactly reproduced the reported five-block sequence and approximately 346-minute internal gap. Changing only M31 to unfinished filled that gap with a manual mosaic opportunity. This is evidence of a reproducible explanation, not confirmation of the account's actual history. The new 35° floor also shortens catalog visibility, so genuine gaps can remain. Gap disclosures now identify visible targets whose goals are complete or already allocated.

## Layout

One proportional darkness axis sits above two desktop columns of compact target cards, becoming one column on mobile. Each card has original Polaris artwork, a data-backed altitude mini-chart when samples exist, visible settings and expandable setup/reasons. No fixed card heights. The conditions panel has compact aligned measurements; date, site, rig and timezone remain nearby. Long account names and mobile controls retain the header fix. Best imaging window, Session plan, Notify me and verbose unallocated panels remain absent. Whole-minute display preserves precise scheduling data.

Functional research references supplied by the parent research task:

- [Telescopius deep-sky planner](https://telescopius.com/deep-sky-objects): compact imagery/identity/altitude cards. Its homepage reports 45,000+ monthly users; this is self-reported, not an independent popularity ranking.
- [Clear Outside](https://clearoutside.com/forecast/50.7/-3.52): aligned conditions, informing compact measurement grouping. No fabricated hourly weather series was added.
- [NINA Scheduler preview](https://tcpalmer.github.io/nina-scheduler/scheduler-preview.html) and [planning engine](https://tcpalmer.github.io/nina-scheduler/concepts/planning-engine.html): expandable reasons and reduced switching/completion patterns.

No third-party imagery, logos or code were copied.

## Validation and preview

- 109 related Python cases passed, including scheduler, hosted history/import, API, plan consistency, UI structure and new long-dwell regressions.
- Nine Node tests passed; JavaScript syntax and git whitespace checks passed.
- Independent code review and desktop/390px screenshot review found no remaining blockers. It independently reran five policy tests; the hosted short-goal regression also passed in the main suite. Review wording corrections were rechecked with all six new policy tests.
- Fresh headless Chrome checks passed at 1440, 320, 375, 390, 430 and 844 pixels: desktop columns, mobile single column, timeline/mini-charts, no page errors or horizontal overflow, long-email header, 44px header controls, refresh/sign-out, keyboard disclosures, chronological gaps and removed sections.
- Preview: `http://127.0.0.1:8111/operator`, backed only by synthetic in-memory data. Run `python tests/serve_long_dwell_fixture.py` to reproduce. `tests/long_dwell_visual_check.cjs` uses Playwright and `CHROME_EXECUTABLE`.
- Screenshot evidence is saved outside the checkout as `long-dwell-desktop.png` and `long-dwell-390.png` (additional phone sizes also retained).

Physical Safari and the authenticated production account plan remain unverified. No live observations, backups, calibration output, database history, permissions or deployment settings were changed.

## Forecast evidence update

The user's current screenshot reports afternoon 9/30 and dusk 10/30. This confirms accumulation beyond the old stored audit. October 11's 88.7% satellite coverage is below the unchanged 90% threshold and correctly excluded. Actual Render cron schedule and execution health remain unverified; this UI/policy change does not claim to repair them.
