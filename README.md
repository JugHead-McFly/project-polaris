# Project Polaris

Project Polaris is the engine behind Doug's Observatory.

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for the current implementation state,
safety rules, and next planned work.

Current Version: v1.2.0

## Features

- FastAPI API
- FITS parser
- Dwarf Mini metadata extraction
- Google Sheets integration (coming soon)
- AI astrophotography analysis (coming soon)
- Planner V3 advisory night schedule at `GET /planner/schedule`
- Read-only night operations dashboard at `GET /operator`

## Run

Activate the virtual environment:

    source .venv/bin/activate

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
