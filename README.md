# Project Polaris

Project Polaris is the engine behind Doug's Observatory.

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for the current implementation state,
safety rules, and next planned work.

Current Version: v0.1

## Features

- FastAPI API
- FITS parser
- Dwarf Mini metadata extraction
- Google Sheets integration (coming soon)
- AI astrophotography analysis (coming soon)
- Planner V3 advisory night schedule at `GET /planner/schedule`

## Run

Activate the virtual environment:

    source .venv/bin/activate

Start the API:

    uvicorn app.main:app --reload

## Test

Install the development dependencies once:

    .venv/bin/pip install -r requirements-dev.txt

Run the complete automated suite:

    .venv/bin/python -m pytest
