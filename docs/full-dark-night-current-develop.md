# Full-night scheduler: current-develop verification

## Verified revisions

On 2026-10-17, `git fetch origin --prune` and a successful `git ls-remote`
confirmed `develop` at `eef60886de2b75029a275d7836358492caf5096b`.
The public production `/health/live` endpoint independently reported that same
commit, branch `develop`, version `1.6.0`, and status `alive`.

The earlier fix was based on `49e93b553091db4dcd4b61597304b01120ab61b2` and
is retained at `394d7496990fa906bf76c5c6552eeb5523ccdea0` on
`codex/full-dark-night`. The replacement feature branch is
`codex/full-dark-night-current`, based directly on current `eef6088`.

`5cab047ab60a57875c3d7103a104d3648d98abe3` is the separate
`origin/codex/local-sky-view` tip. `d67180cc99b8b920a0a627ab0046feba28e4547b`
is the separate `origin/codex/overnight-review` tip. These features are not in
current develop. The sky-view branch diverges at `b654568` and includes saved
obstruction-spot work at `9313fc5`.

## Current defects and focused port

The scheduler, planner, `/tonight` API and observing-context source are identical
between the earlier base and current develop. All diagnosed truncation defects
therefore remain present in the deployed revision: only four selections are
serialized; only the top-six shortlist reaches scheduling; local planning cannot
replace exhausted library targets from the catalog; short selections are charged
then discarded. Visibility also extended beyond its last verified sample.

Only applicable scheduling changes were ported. The port retains all selections,
passes the full observable pool separately from the UI shortlist, validates
minimum blocks before allocation, uses later-rising and catalog replacements,
preserves finite flexible goals behind earlier-ending windows, retains separate
visibility windows, clips to darkness, and reports gaps. ISO instants accompany
local labels; the standalone route forwards the rig profile. Completed goals,
weather stops and existing equipment/setup constraints remain in force.

The newer legacy-history models, migration, service, backup behavior and dashboard
content from develop are preserved. The port applied without conflicts. No
account, authorization, survey, or database-persistence controls were changed.
Synthetic import fixtures from `49e93b5` were copied solely into `tests/`.

## Horizon integration finding

Current develop has no obstruction-profile field in ObservatoryContext and no
saved survey model, migration or account-to-plan resolution path. The live build
revision confirms that this source is deployed, although the live database schema
was not queried. The planner now explicitly says local obstructions are not
modeled on this release rather than implying survey clearance.

The unmerged sky-view branch DOES have persisted spots and explicit Tonight
selection. It calls `resolve_spot` with user, observing home, spot ID and revision,
requires ID and revision together, rejects local-mode saved spots, and invalidates
home bindings when geometry/equipment settings change. Those controls must remain
intact if that branch is integrated later. None were bypassed or imported piecemeal.
The prior fix's standalone obstruction-prototype files are deliberately excluded
from this current-base port.

## Evidence

`python tests/full_night_evidence.py` loads the actual `eef6088` scheduler:

| Version | Blocks | Allocated | Unallocated | End |
|---|---:|---:|---:|---|
| Current develop / deployed `eef6088` | 4 | 180 minutes | 180 minutes | 11 PM |
| Current-base port | 8 | 360 minutes | 0 minutes | 2 AM dawn |

107 unique Python tests passed across scheduler, seasonal synthetic windows,
spring/fall offset-qualified time arithmetic, API, history import, astronomy,
equipment, legacy history, backups, staging and migrations. The first combined
run passed 98 with nine fixture-setup errors caused by the system pytest temporary
directory. All nine passed using a new task-local temporary directory (11 tests
in that retry, including two already passed). Three capture-history UI tests,
JavaScript syntax validation and `git diff --check` also passed.

The seasonal tests are synthetic, not a replay of live weather or account settings.
Use `python tests/serve_full_night_fixture.py` for the current-base in-memory
preview at `http://127.0.0.1:8109/operator`. Port 8108 belongs to the earlier-base
preview. Neither preview reads production data or controls equipment.

## Release limits

Production build identity is verified. Doug's exact authenticated observing home,
rig, integration history and reported plan have not been retrieved. No database
credential was read or used. Visual browser automation is unavailable in this
session; preview verification is through the API and source render path.

This remains a heuristic under existing goals/minimums, not a proof of optimal
packing or guaranteed usable weather. No persisted horizon support is claimed
for current develop. Deployment review must retain those distinctions.

No push, merge or deployment is authorized or performed. The original checkout,
all observations, calibration output and backups remain untouched. Rollback is
the unchanged current base `eef6088`; the earlier feature branch is also retained.
`develop` auto-deploys on Render and must not be merged without approval.
