# Project Polaris Status

Last updated: 2026-07-18

## Project locations

- Application repository: `/Users/doug/dougs-observatory`
- Capture and image library: `/Users/doug/ProjectPolaris`
- Active development branch: `develop`
- Application version: `1.5.1` (in development)
- Current release tag: `v1.5.0`
- Release commit: `5bee291`

The image library is source data, not an application repository. Do not move,
rename, or rewrite it as part of application changes.

Version `1.5.1` is defined once in `app/core/config.py` and is shared by the
root API response, OpenAPI metadata, `GET /system`, and the dashboard API.
Version 1.5.1 is under development on `develop`. Version 1.5.0 was verified
against a genuine encrypted timestamped backup and released from commit
`5bee291`; the annotated `v1.5.0` tag remains the current published release.

## Operational readiness

Version 1.4 expands `GET /system` with read-only runtime diagnostics:

- Process uptime and database availability.
- Latest capture, database, session, and analysis timestamps.
- Capture-history freshness classified as Current, Recent, Stale, or Empty.
- Last-known Open-Meteo and NASA JPL Horizons service state without additional
  health-check network requests.
- Last successful external-service timestamp preserved across later failures.

Weather and ephemeris calls update this process-local diagnostic state. Service
failure remains fail-safe: unavailable weather produces `Do Not Image`, and an
unavailable ephemeris excludes affected moving targets.

Every API response includes a twelve-character `X-Request-ID`. Runtime logs
record that ID with request method, path, result, and elapsed time. Unhandled
failures return a safe error body containing the same ID while the private log
retains the exception detail.

The operator dashboard shows capture freshness, weather state, JPL state, and
runtime uptime. `docs/OPERATIONS.md` documents startup verification, diagnostic
states, logging, matched database/library backups, recovery, and failure
response.

## Release hardening

Version 1.5 release-hardening implementation is complete. Its checkpoints add
backup-pair verification, startup preflight, and combined release gates:

    .venv/bin/python scripts/verify_backup_pair.py /path/to/timestamped-backup
    .venv/bin/python scripts/check_startup.py
    .venv/bin/python scripts/release_check.py --expected-version 1.5.0 \
        --backup-root /path/to/timestamped-backup

The verifier requires both a copied `polaris.db` and `ProjectPolaris` library,
opens SQLite in read-only mode, runs `PRAGMA quick_check`, and reconciles capture
IDs, targets, and managed FITS locations. A backup is valid only when both halves
are present, every database capture and FITS file is matched, and there are no
conflicts. Relocating a matched pair does not create false asset-path failures.

The startup preflight checks the application root, required dashboard assets,
database path and URL agreement, SQLite health and required schema, capture
library paths, and log level. The API runs the same preflight during its lifespan
startup and refuses to serve requests when a required check fails. The checks
are read-only so advisory planning remains available without requiring capture
ingestion permissions.

The release check requires a clean expected branch and exact version, then runs
the startup preflight, complete test suite, backup-pair verification, and five
live endpoint smoke checks. It is read-only with respect to project data and
does not tag or push. `docs/RELEASE_CHECKLIST.md` defines the operator approval,
backup, tag, publish, and rollback sequence.

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

Version 1.5.1 is an operator-usability refinement based on the first guided
v1.5 rehearsal. The top panel is an imaging recommendation rather than a
safety-decision claim, and its planner context is kept with the recommendation
instead of in a separate card. The panel is more compact, an empty Scheduled
Imaging summary is hidden, and the redundant System summary has been removed.
It makes unsafe-weather reasons prominent, distinguishes the
fallback target's usable window from astronomical darkness, exposes proven
sub-exposure/gain/filter settings, adds plain-language Moon phase and timing
context with a phase-shaped illumination visual, and separates page refresh
time from source-data timestamps. Capture
and observing-session history is ordered by observation time instead of
database insertion order. History cards use labeled operational facts and
common target names while internal IDs and the misleading stacked-capture count
are removed from the visible tiles. Target Progress uses capture-library JPGs
as small lazy-loaded thumbnails. Empty session records no longer displace
sessions that produced captures. Bronze, Silver, Gold, and Platinum are now
explicitly labeled as integration-time tiers, while the displayed image's
quality score and interpretation are shown separately. Filter names include a
plain-language purpose, expanded object profiles report the number of stars
detected in the displayed capture, and History identifies the capture location.
Each historical session also retains its Bortle class, so the location context
does not change when the observatory is moved.
The desktop layout keeps the primary Tonight workflow compact while Portfolio,
Quality, History, and Data Status remain separate views.

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
- `5a0694e` - v1.4 operational diagnostics, logging, and recovery runbook
- `d71dbff` - v1.5 read-only backup-pair verification
- `86d2643` - v1.5 startup configuration preflight
- `25a6c32` - v1.5 repeatable release-readiness gates
- `5bee291` - v1.5.0 release candidate and checklist

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
`requirements-dev.txt`. The complete suite currently has 55 passing tests and is
run with `.venv/bin/python -m pytest`.

The root response, OpenAPI metadata, `GET /system`, and dashboard API all
report version `1.5.1` from the shared application setting. The dashboard HTML,
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

The live v1.4 validation began with weather and JPL diagnostics at
`Not Checked`. After one `/tonight` plan both services reported `Healthy`
without a separate probe. The system remained `Healthy`, capture freshness was
`Recent` at 209.3 hours, and the root, plan, and system responses each emitted
a request ID. The current safety decision remained `Do Not Image` because healthy
weather connectivity does not imply suitable imaging conditions.

The first v1.5 live verification opened the current database/library pair in
read-only mode, passed SQLite's quick check, and matched all 19 database captures
to all 19 FITS files with zero orphans, missing assets, or conflicts.

The v1.5 startup preflight passed all seven checks against the live Polaris
installation. An application-lifespan validation then completed startup and
returned HTTP 200 from the root endpoint.

The final v1.5 release workflow passed all six gates using the genuine encrypted
backup `2026-07-18-v1.5.0-5bee291`: clean source state, exact version, all seven
startup checks, all 43 tests, 19 database captures matched to 19 FITS files, and
HTTP 200 from all five live endpoints. The backup also contains a verified,
complete Git bundle and an identical database checksum. The annotated `v1.5.0`
tag and `develop` branch were then published to GitHub at commit `5bee291`.

## Next planned work

1. Complete the v1.5.1 operator-dashboard visual rehearsal and address any
   remaining usability regressions.
2. Run the documented release gates against a fresh verified backup before
   tagging or publishing v1.5.1.
3. Plan v1.6 Locations: an opt-in interactive world map for potential
   observing sites, straight-line distance rings from a selected observatory,
   public dark-sky/place references, and saved site notes. Do not collect or
   expose an exact home address by default; road distance and routing are a
   later separately sourced capability.
4. Plan a future Goal Engine: replace generic integration defaults with
   target-specific, explainable starting goals for quick, detailed, and
   showcase results. Adjust recommendations from the user's equipment,
   sky profile, and capture-quality history, while always allowing a user
   override.
5. Plan Quality Scoring v2: add explainable sharpness, star-roundness, and
   noise measures to the capture score. Record Sky Quality Meter (SQM) values
   with the observing session for context, rather than mixing site darkness
   into an individual capture score.
6. Before public distribution, replace the hard-coded Doug's Observatory
   location with an installation profile covering observatory name, postal
   code, coordinates, elevation, timezone, and storage location. The operator
   banner already reads the name from the observatory API response.
7. Keep actual observatory equipment control outside the approved scope. It
   requires a separate v2 safety and architecture decision.
