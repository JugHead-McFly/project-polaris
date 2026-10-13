# Legacy capture-history migration preparation

## Website release candidate, October 13

The operator authorized deployment of the legacy-history display and backup
support. The release checkout starts from production commit `b654568`; existing
preview branches, the import-regression checkout, calibration output, and the
original staging worktree are preserved. Production was healthy at that commit
before deployment. This is a hosted 1.6.0 maintenance update, not a new tagged
local/NAS release; the hosted deployment procedure and encrypted account backups
apply. The database migration is already applied and must not be rerun manually.

Validation: the complete Python suite passed (414 tests), as did all 8 JavaScript
tests. The first sandbox run stalled; subsequent setup failures were resolved by
creating the test temporary-directory parent and removing test-only environment
overrides. The successful run used the new isolated checkout with no production
configuration. Existing dependency deprecation warnings remain. The current
application exporter will include the legacy ledger after this release.

In the signed-in Tonight page, expand **Imaging progress**, then **20 older
capture records**. The older records remain separate from verified imaging time.
The new assets use the existing cache-version mechanism. Post-deployment checks
must confirm the exact served commit, readiness, and signed-in history display.

Status as of October 13, 2026: production database migration and import complete.
Production `blsfszlysklnatbkczux` is at revision `20261013_0012` and contains
20 owner-scoped legacy records across 18 targets. The 16 verified capture sessions
and all their fields are unchanged. Website display and backup-format changes
remain local and uncommitted; no application deployment was performed. Earlier
preparation/validation entries below describe the sequence before this import.

## Production completion, October 13

- Authorized by the operator to finish importing the old records into production.
- A real PostgreSQL isolation test in a disposable development schema passed:
  two accounts used the same source identifier without cross-account reads,
  inserts, updates or deletes; missing tenant context returned no rows. The
  entire transaction rolled back and schema absence was verified.
- 27 Python tests and 3 JavaScript tests passed again. A localhost browser fixture
  using the actual history render function verified collapsed-by-default display,
  expand/collapse/reopen and unchanged synthetic plan text. This is a component
  check, not a full production operator-page test.
- The previously restored account backup remains encrypted. An additional fresh
  16-session capture-history backup was encrypted and round-trip verified at
  `.cache/production-review-20261013/captures-pre-import.json.dpapi`.
- The import transaction checked the starting revision and owner, locked existing
  capture history, created the new table with forced RLS and restricted grants,
  inserted the reviewed batch twice with owner/source conflict protection,
  checked all 20 evidence hashes, and compared every existing capture row in both
  directions before committing the migration revision. Both insertion passes
  together left exactly 20 legacy records, not 40.
- Final production counts: 20 legacy records, 18 targets, 16 verified sessions,
  127470.625 verified seconds. M31 has 3 verified sessions plus 1 older record.
  Legacy records add zero verified hours; unresolved overlap/timezone flags remain.
- Production checks under `polaris_app` returned 20 rows for the intended owner
  and zero without tenant context. `polaris_runtime` membership in `polaris_app`
  was verified. Supabase refused direct `SET ROLE polaris_runtime`, so this was
  not a direct runtime-login test.
- The built-in browser blocked the Render readiness URL with
  `ERR_BLOCKED_BY_CLIENT`; post-import HTTP readiness was not independently
  verified. No application files were published, merged, committed or pushed.

Next: integrate this migration and the separate legacy-history display with the
current application branch, preserving concurrent display work, then review and
deploy the application changes. The live website does not yet render the new
legacy table. Production backups using the old application exporter still omit
legacy records until backup format 2 is deployed. Preserve the encrypted backups,
review artifact and this migration when preparing any later release.

The hosted ledger currently accepts `verified_raw_frames`. Older SQLite captures
are mostly stack-derived records; uploading them under that basis would be
incorrect. They must retain separate provenance, and quality scores must not be
represented as fresh analysis.

## Offline staging

`scripts/stage_legacy_history.py` accepts legacy backup files, an explicit owner
UUID, and a **new** destination SQLite path. It opens sources read-only, checks
integrity and source-file hashes, and preserves original sessions, captures and
analyses as JSON snapshots. It does not load app configuration or contact services.

Repeated backup rows are consolidated using the legacy capture ID. All versions
remain available. Explicit total integration metadata is preferred; a single
exposure duration is never substituted for missing total integration. Same-target,
same-day records are flagged for review, not deleted. Conflicting metadata and
timestamps without offsets are flagged. These heuristics do not establish that
different source IDs or renamed files represent distinct exposures.

The destination is an offline review artifact, not an application database. Its
owner ID is attribution, not an access-control boundary. Protect it like a database
backup: original payloads can include notes, old paths, and location metadata. Do
not commit or upload it. Re-running requires a new destination; existing files are
never overwritten. Verified integration credited by this tool is always zero.

## Inspection on October 9, 2026

- Two legacy databases contain 20 consolidated captures across 18 targets.
- Both originals and all their source rows are retained in the review artifact.
- Four records are flagged for same-target/day overlap review; these flags are
  not confirmation of duplicates.
- Twenty timestamps lack explicit offsets. The old `observation_utc` column name
  alone is not independent verification of timestamp semantics.
- M31 includes a June 12 stack reporting 3,600 integration seconds. The current
  NAS-derived history has three later sessions totaling 34,800 seconds. Date
  separation suggests additional history, but no production credit was granted.
- Correction verified October 13: the failed `.env.staging` connection targets
  **Polaris Development**, project `vqfvedywwahpqpnuivrp`, not production.
  The October 6 deployment record identifies production as `blsfszlysklnatbkczux`.
  The tenant/user-not-found error and exposed credential therefore concern the
  development connection. They do not establish a production access failure.
  The live UI on October 9 showed M31 at 9.67 hours and 16 imported sessions.

## Required before production migration

1. Coordinate with the separate display-fix work; do not overwrite it.
2. Rotate the exposed **development** runtime credential through the owning service's supported
   administration process. The operator must complete credential entry. Confirm
   the correct project, role and connection configuration without printing secrets.
3. Take a fresh account-scoped production backup including `capture_history` and
   verify its restore in isolation. Existing older backups omit that ledger.
4. Add tenant-enforced legacy provenance/storage and UI support. Show legacy
   history separately from verified raw-frame totals until overlap is resolved.
5. Match legacy captures to actual files and current account history; resolve the
   M17 candidate duplicate and confirm timezone semantics. Preserve unresolved
   records without automatically awarding integration time.
6. Rehearse an idempotent owner-scoped migration on an isolated production copy.
   Test duplicate backups, alternate IDs/renamed files, raw/stack overlap, tenant
   isolation, repeat imports, rollback, backup completeness, and plan/display
   consistency. Current staging tests do not prove production RLS or UI behavior.
7. Review exact insertion counts and progress deltas before production execution.

## Validation

October 13 follow-up: the development password was rotated by the operator and
the updated local connection passed a read-only query as `polaris_runtime`.

Backup format 2 includes capture history, legacy history, forecast snapshots and
nightly forecasts as well as the original profile/observatory/planning tables.
Version 1 exports remain supported, but do not contain the newer tables. Auth
accounts and sync credentials are intentionally outside this application-data
export; it is not a full platform/disaster-recovery backup. The legacy schema must
exist before using format 2 export against a hosted database.

`scripts/rehearse_legacy_history.py` reads the review artifact without modifying
it and imports into disposable in-memory SQLite databases using a synthetic owner.
The October 13 run restored all 20 records across 18 targets, repeated the import
with zero added records, and added zero verified hours. Source hash was unchanged.
This was NOT a rehearsal on a current production copy. PostgreSQL RLS, the live UI,
and migration execution remain unverified.

Subsequent October 13 verification: browser access recovered. A fresh read-only,
repeatable-read export from production `blsfszlysklnatbkczux` contained one owner:
1 profile, 1 observatory, 16 capture sessions, 416 recommendation runs, 10 feedback
records, 505 forecast snapshots and 8 nightly forecasts. Its owner matched the
legacy review artifact. All exported fields restored and matched in an isolated
in-memory SQLite database (datetime timezone markers normalized for SQLite).
Importing 20 legacy records and repeating added 20 then 0 rows. All 16 verified
sessions and planner progress totals were unchanged. No production writes occurred.

The export is encrypted using Windows CurrentUser DPAPI at
`.cache/production-review-20261013/account-export.json.dpapi`; decryption was
verified byte-for-byte before removing the temporary plaintext export. The
adjacent `rehearsal-result.json` records counts and SHA-256. This backup requires
the current Windows account to decrypt and excludes authentication and sync
credentials. Production schema/migration and live UI validation remain pending.

Additional validation: 27 Python tests and 3 JavaScript display tests pass.
The actual migration builds a clean SQLite database, matches model metadata,
and upgrades/downgrades while preserving existing capture history. PostgreSQL
SQL-generation checks verify forced RLS, owner checks and restricted grants;
these are NOT a real PostgreSQL RLS execution test. Display tests exercise the
render function with a simulated DOM, not an interactive browser. Browser control
timed out before the development SQL editor could be inspected. No development
or production migration was executed. Both live validation gaps remain open.

Seven synthetic staging tests pass: backup consolidation and unchanged sources;
preserved metadata/analysis; overlap retention; conflicting evidence; missing
integration; existing-destination protection; account attribution and invalid
owner rejection; missing-source rejection (some checks share a test).

Initial test attempts failed during temporary-directory setup under the sandbox.
Using a new workspace-local temporary directory resolved setup; all tests passed.
