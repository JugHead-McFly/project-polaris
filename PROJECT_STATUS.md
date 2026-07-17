# Project Polaris Status

Last updated: 2026-07-17

## Project locations

- Application repository: `/Users/doug/dougs-observatory`
- Capture and image library: `/Users/doug/ProjectPolaris`
- Active development branch: `develop`

The image library is source data, not an application repository. Do not move,
rename, or rewrite it as part of application changes.

## Current planner

Planner V3 is an advisory night scheduler exposed at:

    GET /planner/schedule

It builds chronological, non-overlapping blocks from Planner V2 target rankings.
It excludes unobservable targets and blocks shorter than 30 minutes. It does not
control observatory equipment.

Safety behavior:

- A `Do Not Image` weather decision produces no schedule blocks.
- Unavailable live weather fails closed with an observing rating of zero.
- Targets without a reliable position for the requested date are excluded.
- Moving objects must not use coordinates copied from an old capture.
- JPL lookup failures and timeouts exclude the affected moving target without
  interrupting the rest of the nightly plan.

## Target positioning

- Fixed deep-sky targets use the catalog in `app/data/targets.py`.
- Jupiter uses an Astropy solar-system position calculated for the requested
  observation time.
- C20 uses the fixed coordinates confirmed by Polaris capture metadata.
- C 2026 B3 PANSTARRS uses a batched, date-specific observer ephemeris from
  NASA JPL Horizons. Results are cached only in memory for exact UTC instants.

## Completed checkpoints

- `ca8f922` - Planner V3 advisory night scheduler
- `4f74905` - Safe C20 and dynamic Jupiter positioning
- `6c1ae7a` - Fail-safe JPL Horizons comet ephemeris support

## Verification status

The scheduler, route registration, safe weather fallback, C20 coordinates,
dynamic Jupiter position, Moon separation, transit calculations, batched comet
ephemerides, cache reuse, and ephemeris failure behavior have focused regression
checks. The current virtual environment does not include `pytest`, so the test
functions were also executed directly during development.

The live validation on 2026-07-17 returned `Proceed`, selected M57 for the full
astronomical-darkness window and ranked C20 as a valid alternative. A second
live validation using JPL Horizons successfully positioned the comet without
changing the recommended M57 schedule.

## Next planned work

1. Add equipment and filter constraints to scheduled blocks.
2. Add a documented development-test dependency and run the full API suite.
3. Improve capture synchronization from the image library without modifying
   the original files.
