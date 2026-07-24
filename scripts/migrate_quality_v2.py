"""Add versioned Quality Scoring v2 fields without recalculating captures."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect
from sqlalchemy import text

from app.database.database import engine


QUALITY_V2_COLUMNS = {
    "median_roundness": "FLOAT",
    "median_sharpness": "FLOAT",
    "background_noise": "FLOAT",
    "relative_background_noise": "FLOAT",
    "background_gradient": "FLOAT",
    "clipped_pixel_fraction": "FLOAT",
    "star_sample_count": "INTEGER",
    "legacy_quality_score": "INTEGER",
    "scoring_version": "VARCHAR",
    "analysis_confidence": "VARCHAR",
}


def migrate() -> list:
    columns = {
        column["name"]
        for column in inspect(engine).get_columns(
            "capture_analyses"
        )
    }
    changes = [
        (name, definition)
        for name, definition in QUALITY_V2_COLUMNS.items()
        if name not in columns
    ]

    with engine.begin() as connection:
        for name, definition in changes:
            connection.execute(
                text(
                    "ALTER TABLE capture_analyses "
                    f"ADD COLUMN {name} {definition}"
                )
            )
        connection.execute(
            text(
                "UPDATE capture_analyses "
                "SET legacy_quality_score = quality_score "
                "WHERE legacy_quality_score IS NULL "
                "AND quality_score IS NOT NULL"
            )
        )
        connection.execute(
            text(
                "UPDATE capture_analyses "
                "SET scoring_version = '1.0' "
                "WHERE scoring_version IS NULL"
            )
        )

    return [name for name, _ in changes]


if __name__ == "__main__":
    added = migrate()
    if added:
        print(
            "Added Quality Scoring v2 columns: "
            + ", ".join(added)
        )
    else:
        print(
            "Quality Scoring v2 columns are ready; "
            "existing scores remain preserved as v1."
        )
