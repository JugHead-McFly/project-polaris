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

Each block includes proven exposure, gain, and filter settings from capture
history, a five-minute setup allowance, planned imaging minutes, and the number
of subframes needed. The scheduler avoids marginal equipment changes and moves
to an alternative target when the current target reaches its integration goal.

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

## Capture-library synchronization

`scripts/sync_capture_library.py` audits `/Users/doug/ProjectPolaris` in dry-run
mode by default. Explicit `--apply` mode can register valid orphan FITS files in
the database, but it never copies, renames, modifies, or deletes library files.
Duplicate IDs, target mismatches, and asset-path mismatches block apply mode.

## Completed checkpoints

- `ca8f922` - Planner V3 advisory night scheduler
- `4f74905` - Safe C20 and dynamic Jupiter positioning
- `6c1ae7a` - Fail-safe JPL Horizons comet ephemeris support
- `b1496e1` - Equipment-aware, goal-limited schedule blocks
- `980e44a` - Repeatable automated test suite and API checks
- `64eba37` - Dry-run-first capture library synchronization

## Verification status

The scheduler, route registration, safe weather fallback, C20 coordinates,
dynamic Jupiter position, Moon separation, transit calculations, batched comet
ephemerides, cache reuse, and ephemeris failure behavior have focused regression
checks. Equipment-change suppression, setup allowances, subframe counts,
integration-goal handoffs, darkness coverage, weather failure, and the live API
response contract also have focused checks.

The Python 3.9-compatible development environment pins pytest 8.4.2 in
`requirements-dev.txt`. The complete suite currently has 16 passing tests and is
run with `.venv/bin/python -m pytest`.

The live validation on 2026-07-17 returned `Proceed`, selected M57 for the full
astronomical-darkness window and ranked C20 as a valid alternative. A second
live validation using JPL Horizons successfully positioned the comet without
changing the recommended M57 schedule.

The equipment-aware validation schedules M57 until its remaining 497 subframes
are complete, then M27, then M13. It reports the final 22 dark minutes as
unscheduled because they do not meet the 30-minute minimum block requirement.

The capture-library dry run found 19 database captures and 19 matching FITS
files, with zero orphans, missing assets, or conflicts. A before/after file-state
checksum confirmed the audit did not alter the library.

## Next planned work

1. Expose read-only capture-library health in the system-status API while
   keeping database-changing synchronization restricted to the explicit CLI.
