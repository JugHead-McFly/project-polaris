# Project Polaris Operations

This runbook covers the local Project Polaris application at
`/Users/doug/dougs-observatory` and its capture library at
`/Users/doug/ProjectPolaris`.

Polaris is advisory software. A healthy application does not replace the
operator's weather, equipment, or safety judgment, and the application does
not control observatory equipment.

## Start and verify

From the application repository:

    source .venv/bin/activate
    uvicorn app.main:app --host 127.0.0.1 --port 8000

Open `http://127.0.0.1:8000/operator` for the night operations dashboard.

Before relying on a nightly plan, confirm:

1. The dashboard loads and clearly shows a safety decision.
2. System health is not `Attention Required`.
3. Capture-library conflicts are zero.
4. Weather is `Healthy`. If weather is degraded, Polaris deliberately returns
   `Do Not Image`.
5. Any moving target has a healthy JPL ephemeris result. A degraded JPL service
   excludes affected moving targets rather than using old coordinates.

For a more detailed check:

    .venv/bin/python -m pytest
    .venv/bin/python scripts/sync_capture_library.py /Users/doug/ProjectPolaris
    sqlite3 polaris.db "PRAGMA quick_check;"

The library command is a dry run unless `--apply` is explicitly added. Routine
health checks should not use `--apply`.

Stop the local server with `Control-C` in the terminal where it is running.

## Diagnostic states

`GET /system` and the operator dashboard expose these operational signals:

- `Healthy`: the local database and capture library are consistent, and no
  checked external service has failed most recently.
- `Degraded`: planning remains available in a fail-safe mode, but capture data
  is stale or a checked external service is unavailable.
- `Attention Required`: the capture library is unavailable or inconsistent.
- `Not Checked`: that external service has not been needed since this Polaris
  process started.

Capture freshness is classified as:

- `Current`: latest observation is no more than 24 hours old.
- `Recent`: latest observation is between 24 hours and 30 days old.
- `Stale`: latest observation is more than 30 days old.
- `Empty`: no valid capture observation time is available.

Freshness describes the age of capture history. It is not a weather forecast
and does not independently decide whether imaging is safe.

## Runtime logs

Each API request logs its request ID, method, path, status, and elapsed time.
Unhandled failures log the same request ID with an exception. The response also
includes the request ID in the `X-Request-ID` header so an operator can match a
visible failure to the corresponding log entry.

The default log level is `INFO`. For a temporary diagnostic session, set
`POLARIS_LOG_LEVEL=DEBUG` before starting the application. Return to the default
after troubleshooting so routine logs remain readable.

## Backup policy

The SQLite database and capture library are one logical collection. Back them
up as a matched pair; a database-only or library-only backup can restore into an
inconsistent state.

1. Stop Project Polaris before copying the database.
2. Create a new timestamped backup folder outside both live project locations,
   preferably on a separate disk.
3. Copy `/Users/doug/dougs-observatory/polaris.db` into that folder.
4. Copy `/Users/doug/ProjectPolaris` into the same timestamped folder without
   renaming or reorganizing its contents.
5. Record the application commit and the backup date with the pair.
6. Verify the copied pair from the application repository:

       .venv/bin/python scripts/verify_backup_pair.py /path/to/timestamped-backup

7. Keep the resulting valid report with the backup record before considering
   the backup complete.

Keep more than one dated backup. Never use the live capture library as the only
backup copy.

### Backup verification results

The verification command is read-only. By default, it expects this structure:

    timestamped-backup/
    ├── polaris.db
    └── ProjectPolaris/
        └── targets/

It opens the copied database in SQLite read-only mode, runs `PRAGMA quick_check`,
and compares every database capture with the copied FITS files by Polaris ID,
target, and managed asset location. The historical source filename stored in a
capture record is not expected to match the Polaris-managed FITS filename.

The JSON report sets `valid` to `true` and the command exits with status zero
only when both halves are present, SQLite is healthy, every capture is matched,
and there are no orphans, missing assets, or conflicts. A nonzero exit means the
backup must not be treated as recovery-ready.

For a backup that uses different names, provide paths relative to the backup
folder or absolute paths:

    .venv/bin/python scripts/verify_backup_pair.py /path/to/backup \
        --database copied-polaris.db --library CopiedProjectPolaris

## Recovery

Recovery can overwrite live data, so it should be a deliberate maintenance
operation rather than an automatic application action.

1. Stop Project Polaris.
2. Preserve the current database and capture library as a separate recovery
   copy, even if one appears damaged.
3. Select a database and capture library from the same timestamped backup.
4. Run the backup-pair verification command before restoring. For a suspected
   database problem, also run `PRAGMA integrity_check` before proceeding.
5. Restore the matched pair without changing FITS filenames, target folders,
   or Polaris IDs.
6. Start Polaris and run the capture-library synchronization command in its
   default dry-run mode.
7. Confirm `/system` reports the expected counts and zero conflicts before
   using `/tonight` operationally.

If the dry run reports conflicts, stop. Do not use `--apply`, rename files, or
delete records until the mismatch has been understood and a fresh safety copy
exists.

## Failure response

- Weather unavailable: accept the `Do Not Image` result and restore weather
  connectivity before planning an imaging run.
- JPL unavailable: continue only with fixed targets; affected moving targets
  are excluded automatically.
- Capture library inconsistent: stop synchronization and inspect the reported
  missing, orphaned, or conflicting IDs.
- Database integrity failure: stop the application and begin matched-pair
  recovery. Do not continue writing to the database.
- Repeated HTTP failure: note the `X-Request-ID`, preserve the associated log
  entry, and restart only after active requests have finished.
