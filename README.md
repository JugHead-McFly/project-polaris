# Project Polaris

Project Polaris is the engine behind Doug's Observatory.

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for the current implementation state,
safety rules, and next planned work.

See [PROJECT_TIME.md](PROJECT_TIME.md) for the cumulative development-time log
and coding-timer state.

Current Version: v1.5.0

## Features

- FastAPI API
- FITS parser
- Dwarf Mini metadata extraction
- Google Sheets integration (coming soon)
- AI astrophotography analysis (coming soon)
- Planner V3 advisory night schedule at `GET /planner/schedule`
- Read-only night operations dashboard at `GET /operator`
- Typed portfolio and recent-history feed at `GET /dashboard`

## Run

Activate the virtual environment:

    source .venv/bin/activate

Check the required startup configuration:

    python scripts/check_startup.py

Start the API:

    uvicorn app.main:app --reload

Then open `http://127.0.0.1:8000/operator` for the read-only night operations
dashboard.

## Test

Install the development dependencies once:

    .venv/bin/pip install -r requirements-dev.txt

Run the complete automated suite:

    .venv/bin/python -m pytest

## Capture-library sync

Audit the capture library without changing files or the database:

    .venv/bin/python scripts/sync_capture_library.py /Users/doug/ProjectPolaris

After reviewing a dry-run report, register valid orphan FITS files with:

    .venv/bin/python scripts/sync_capture_library.py /Users/doug/ProjectPolaris --apply

Apply mode only adds database records that reference existing FITS files. It
does not copy, rename, modify, or delete library files.

The read-only `GET /system` endpoint includes compact capture-library health
counts. Database-changing synchronization remains available only through the
explicit CLI command above.

See [docs/OPERATIONS.md](docs/OPERATIONS.md) for startup verification,
diagnostics, logging, matched database/library backups, and recovery guidance.

## Backup-pair verification

Verify a timestamped backup folder containing both `polaris.db` and a copied
`ProjectPolaris` capture-library folder:

    .venv/bin/python scripts/verify_backup_pair.py /path/to/timestamped-backup

The verifier is read-only. It runs SQLite's quick check and reconciles every
database capture with the copied FITS library. It exits successfully only when
the pair is complete and consistent.

## Release readiness

With a clean candidate branch, a verified timestamped backup, and the local API
running, execute all release gates together:

    .venv/bin/python scripts/release_check.py \
        --expected-version 1.5.0 \
        --backup-root /path/to/timestamped-backup \
        --base-url http://127.0.0.1:8000

See [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) for the required
release sequence, approval boundary, and rollback guidance.
