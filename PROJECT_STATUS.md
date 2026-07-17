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

## Target positioning

- Fixed deep-sky targets use the catalog in `app/data/targets.py`.
- Jupiter uses an Astropy solar-system position calculated for the requested
  observation time.
- C20 uses the fixed coordinates confirmed by Polaris capture metadata.
- C 2026 B3 PANSTARRS remains excluded until Polaris has a reliable,
  date-specific comet ephemeris source.

## Completed checkpoints

- `ca8f922` - Planner V3 advisory night scheduler
- `4f74905` - Safe C20 and dynamic Jupiter positioning

## Verification status

The scheduler, route registration, safe weather fallback, C20 coordinates,
dynamic Jupiter position, Moon separation, and transit calculations have focused
regression checks. The current virtual environment does not include `pytest`, so
the test functions were also executed directly during development.

The live validation on 2026-07-17 returned `Proceed`, selected M57 for the full
astronomical-darkness window, ranked C20 as a valid alternative, and excluded
only the comet for missing current coordinates.

## Next planned work

1. Add a reliable comet ephemeris adapter with fail-closed behavior and tests.
2. Add equipment and filter constraints to scheduled blocks.
3. Add a documented development-test dependency and run the full API suite.
4. Improve capture synchronization from the image library without modifying
   the original files.
