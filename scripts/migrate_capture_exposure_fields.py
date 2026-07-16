import sqlite3
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from app.core.config import settings


NEW_COLUMNS = {
    "sub_exposure_seconds": "INTEGER",
    "subframe_count": "INTEGER",
    "total_integration_seconds": "INTEGER",
    "filter_name": "TEXT",
}


def get_existing_columns(
    connection: sqlite3.Connection,
) -> set:
    rows = connection.execute(
        "PRAGMA table_info(captures)"
    ).fetchall()

    return {
        row[1]
        for row in rows
    }


def add_missing_columns(
    connection: sqlite3.Connection,
) -> None:
    existing_columns = get_existing_columns(
        connection
    )

    for column_name, column_type in (
        NEW_COLUMNS.items()
    ):
        if column_name in existing_columns:
            print(
                f"Already exists: {column_name}"
            )
            continue

        connection.execute(
            f"ALTER TABLE captures "
            f"ADD COLUMN {column_name} "
            f"{column_type}"
        )

        print(
            f"Added: {column_name}"
        )


def migrate_existing_values(
    connection: sqlite3.Connection,
) -> None:
    rows = connection.execute(
        """
        SELECT
            id,
            polaris_id,
            filename,
            exposure_seconds
        FROM captures
        ORDER BY id
        """
    ).fetchall()

    for (
        capture_id,
        polaris_id,
        filename,
        exposure_seconds,
    ) in rows:
        if exposure_seconds is None:
            continue

        filename_lower = (
            filename or ""
        ).lower()

        if filename_lower.startswith(
            "stacked-"
        ):
            sub_exposure_seconds = (
                exposure_seconds
            )
            total_integration_seconds = None
        else:
            sub_exposure_seconds = None
            total_integration_seconds = (
                exposure_seconds
            )

        connection.execute(
            """
            UPDATE captures
            SET
                sub_exposure_seconds = COALESCE(
                    sub_exposure_seconds,
                    ?
                ),
                total_integration_seconds = COALESCE(
                    total_integration_seconds,
                    ?
                )
            WHERE id = ?
            """,
            (
                sub_exposure_seconds,
                total_integration_seconds,
                capture_id,
            ),
        )

        print(
            f"Migrated {polaris_id}: "
            f"sub={sub_exposure_seconds}, "
            f"total={total_integration_seconds}"
        )


def main() -> None:
    database_path = Path(
        settings.DATABASE_FILE
    ).resolve()

    if not database_path.exists():
        raise FileNotFoundError(
            "Polaris database was not found:\n"
            f"{database_path}"
        )

    backup_path = database_path.with_suffix(
        ".before_exposure_migration.db"
    )

    if not backup_path.exists():
        backup_path.write_bytes(
            database_path.read_bytes()
        )

        print(
            f"Backup created: {backup_path}"
        )
    else:
        print(
            f"Backup already exists: {backup_path}"
        )

    connection = sqlite3.connect(
        database_path
    )

    try:
        add_missing_columns(
            connection
        )

        migrate_existing_values(
            connection
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    print(
        "Capture exposure migration complete."
    )


if __name__ == "__main__":
    main()