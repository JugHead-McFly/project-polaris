"""Create and update v1.6 candidate-site storage without altering capture history."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect
from sqlalchemy import text

from app.database.database import engine
from app.models.candidate_site import CandidateSite


def migrate() -> bool:
    CandidateSite.__table__.create(bind=engine, checkfirst=True)
    columns = {
        column["name"]
        for column in inspect(engine).get_columns("candidate_sites")
    }
    missing_columns = {
        "visited_at": "DATETIME",
        "access_hours": "VARCHAR",
        "vehicle_requirement": "VARCHAR",
        "property_access": "VARCHAR",
        "parking_setup_confirmed": "BOOLEAN NOT NULL DEFAULT 0",
        "horizon_confirmed": "BOOLEAN NOT NULL DEFAULT 0",
        "access_confirmed": "BOOLEAN NOT NULL DEFAULT 0",
        "amenities_confirmed": "BOOLEAN NOT NULL DEFAULT 0",
        "star_rating": "INTEGER",
    }
    changes = [
        (name, definition)
        for name, definition in missing_columns.items()
        if name not in columns
    ]
    if not changes:
        return False
    with engine.begin() as connection:
        for name, definition in changes:
            connection.execute(
                text(f"ALTER TABLE candidate_sites ADD COLUMN {name} {definition}")
            )
    return True


if __name__ == "__main__":
    changed = migrate()
    print(
        "Updated candidate_sites columns."
        if changed
        else "Candidate-site table is ready."
    )
