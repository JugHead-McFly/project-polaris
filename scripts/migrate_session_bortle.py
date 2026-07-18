"""Add the per-session Bortle column required by historical observing logs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect
from sqlalchemy import text

from app.database.database import engine


def migrate() -> bool:
    columns = {
        column["name"]
        for column in inspect(engine).get_columns("sessions")
    }
    if "bortle_class" in columns:
        return False

    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE sessions ADD COLUMN bortle_class INTEGER")
        )
    return True


if __name__ == "__main__":
    changed = migrate()
    print(
        "Added sessions.bortle_class."
        if changed
        else "sessions.bortle_class already exists."
    )
