# Project Polaris Status

Last updated: 2026-07-17

## Project locations

- Application repository: `/Users/doug/dougs-observatory`
- Capture and image library: `/Users/doug/ProjectPolaris`
- Active development branch: `develop`
- Application version: `1.3.0`

The image library is source data, not an application repository. Do not move,
rename, or rewrite it as part of application changes.

Version `1.3.0` is defined once in `app/core/config.py` and is shared by the
root API response, OpenAPI metadata, `GET /system`, and the dashboard API.
The code is release-ready, but the `v1.3.0` Git tag and remote push remain
explicit release actions and have not been performed.

## Operator dashboard

Version 1.2 adds a responsive, read-only night operations dashboard at:

    GET /operator

The dashboard uses the consolidated `GET /tonight`, typed `GET /dashboard`, and
read-only `GET /system` responses. It makes the safety decision the primary
visual, shows the recommended target or weather-safe fallback, renders
chronological schedule blocks and equipment settings, and summarizes weather,
Moon, darkness, planner notes, capture-library health, target progress, recent
captures, and recent observing sessions. Its only interaction is a manual data
refresh; it has no equipment-control or database-write action.

Version 1.3 replaces the duplicated v0.6 calculations formerly embedded in
`GET /dashboard` with a typed response service. Integration totals, quality,
capture settings, and portfolio progress now use the same shared helpers as the
target and planner APIs. The endpoint returns metrics for the complete library,
all captured targets, the eight most recent captures, and the six most recent
sessions.

The dashboard is served by the existing local FastAPI application. No external
hosting or deployment was performed.

## Current planner

Planner V3 is an advisory night scheduler exposed at:

    GET /planner/schedule

The compatibility endpoint is exposed at:

    GET /tonight

It builds chronological, non-overlapping blocks from Planner V2 target rankings.
It excludes unobservable targets and blocks shorter than 30 minutes. It does not
control observatory equipment.

`GET /tonight` now computes Planner V3 once and derives its legacy target,
night-plan, Moon, weather, darkness, and night-rating fields from that result.
It also includes the complete typed V3 schedule. The legacy response shape is
preserved for existing clients while the duplicated earlier planning workflow
has been removed.

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
The read-only `GET /system` endpoint exposes compact library-health counts. It
does not expose any database-changing synchronization route.

## Completed checkpoints

- `ca8f922` - Planner V3 advisory night scheduler
- `4f74905` - Safe C20 and dynamic Jupiter positioning
- `6c1ae7a` - Fail-safe JPL Horizons comet ephemeris support
- `b1496e1` - Equipment-aware, goal-limited schedule blocks
- `980e44a` - Repeatable automated test suite and API checks
- `64eba37` - Dry-run-first capture library synchronization
- `88f6d4c` - Read-only capture-library health in system status
- `6005397` - Legacy tonight workflow consolidated on Planner V3
- `21e8a5b` - Centralized v1.1 application version metadata
- `232dd7e` - v1.2 read-only night operations dashboard
- `e97fa28` - v1.3 typed dashboard history consolidation

## Verification status

The scheduler, route registration, safe weather fallback, C20 coordinates,
dynamic Jupiter position, Moon separation, transit calculations, batched comet
ephemerides, cache reuse, and ephemeris failure behavior have focused regression
checks. Equipment-change suppression, setup allowances, subframe counts,
integration-goal handoffs, darkness coverage, weather failure, and the live API
response contract also have focused checks. The `/tonight` compatibility layer
is covered for its required legacy target fields, embedded V3 schedule, and
missing-recommendation weather path.

The Python 3.9-compatible development environment pins pytest 8.4.2 in
`requirements-dev.txt`. The complete suite currently has 24 passing tests and is
run with `.venv/bin/python -m pytest`.

The root response, OpenAPI metadata, `GET /system`, and dashboard API all
report version `1.3.0` from the shared application setting. The dashboard HTML,
local assets, GET-only route, and JavaScript syntax have focused checks.
The typed dashboard service also has an isolated database regression check for
integration totals, quality, target history, capture ordering, and sessions.

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

The live `GET /system` validation reports 19 captures, 19 matched FITS files,
zero orphans, missing assets, or conflicts, and an overall `Healthy` status.

The live `GET /tonight` compatibility validation now returns HTTP 200 instead
of its previous response-validation error. On 2026-07-17 the weather decision
was `Do Not Image`, so both the V3 schedule and legacy target sequence safely
contained no imaging blocks while M57 remained available as the fallback.

The live v1.2 dashboard validation returned HTTP 200 from `/operator`,
`/tonight`, and `/system`. Current conditions produced `Do Not Image`, zero
schedule blocks, M57 as the fallback, and a `Healthy` capture library, which is
the intended fail-safe display path.

The live v1.3 dashboard response reports 19 captures across 18 targets and 21
sessions, 19 analysis records, and 32.66 total integration hours. It returns
eight recent captures and six recent sessions through the typed contract.

## Next planned work

1. Begin v1.4 operational readiness: expose data-freshness and degraded-service
   diagnostics, improve runtime logging and failure visibility, expand date and
   night-boundary tests, and document startup, backup, and recovery procedures.
