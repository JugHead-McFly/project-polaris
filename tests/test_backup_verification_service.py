import hashlib
import sqlite3
from pathlib import Path

from app.services.backup_verification_service import verify_backup_pair


def create_backup_database(path: Path, captures) -> None:
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE captures ("
        "polaris_id TEXT, object_name TEXT, filename TEXT, asset_path TEXT"
        ")"
    )
    connection.executemany(
        "INSERT INTO captures "
        "(polaris_id, object_name, filename, asset_path) "
        "VALUES (?, ?, ?, ?)",
        captures,
    )
    connection.commit()
    connection.close()


def create_backup_fits(
    library_root: Path,
    target: str,
    polaris_id: str,
) -> Path:
    path = library_root / "targets" / target / "fits" / f"{polaris_id}.fits"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"read-only backup verification fixture")
    return path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_valid_relocated_backup_pair_is_verified_without_writes(tmp_path):
    backup_root = tmp_path / "2026-07-18"
    library_root = backup_root / "ProjectPolaris"
    fits_path = create_backup_fits(
        library_root,
        "M57",
        "POL-2026-000001",
    )
    database_path = backup_root / "polaris.db"
    create_backup_database(
        database_path,
        [
            (
                "POL-2026-000001",
                "M57",
                "original-camera-filename.fits",
                "/Users/doug/ProjectPolaris/targets/M57/fits/"
                "POL-2026-000001.fits",
            )
        ],
    )
    database_digest = digest(database_path)
    fits_digest = digest(fits_path)

    report = verify_backup_pair(backup_root)

    assert report["mode"] == "read-only"
    assert report["valid"]
    assert report["database_quick_check"] == ["ok"]
    assert report["database_capture_count"] == 1
    assert report["library_fits_count"] == 1
    assert report["matched_count"] == 1
    assert report["conflict_count"] == 0
    assert digest(database_path) == database_digest
    assert digest(fits_path) == fits_digest


def test_missing_library_counterpart_is_invalid(tmp_path):
    backup_root = tmp_path / "missing-library"
    backup_root.mkdir()
    create_backup_database(backup_root / "polaris.db", [])

    report = verify_backup_pair(backup_root)

    assert not report["valid"]
    assert report["database_present"]
    assert not report["library_present"]
    assert "Backup capture library was not found" in report["errors"][0]


def test_missing_and_orphan_captures_are_reported(tmp_path):
    backup_root = tmp_path / "mismatched"
    library_root = backup_root / "ProjectPolaris"
    create_backup_fits(library_root, "M27", "POL-2026-000002")
    database_path = backup_root / "polaris.db"
    create_backup_database(
        database_path,
        [
            (
                "POL-2026-000001",
                "M57",
                "POL-2026-000001.fits",
                "/Users/doug/ProjectPolaris/targets/M57/fits/"
                "POL-2026-000001.fits",
            )
        ],
    )

    report = verify_backup_pair(backup_root)

    assert not report["valid"]
    assert report["orphan_count"] == 1
    assert report["missing_asset_count"] == 1
    assert report["orphan_files"][0]["polaris_id"] == "POL-2026-000002"
    assert report["missing_database_assets"][0]["polaris_id"] == (
        "POL-2026-000001"
    )


def test_capture_target_and_asset_path_conflicts_block_verification(tmp_path):
    backup_root = tmp_path / "conflict"
    library_root = backup_root / "ProjectPolaris"
    create_backup_fits(library_root, "M27", "POL-2026-000001")
    create_backup_fits(library_root, "M31", "POL-2026-000002")
    create_backup_database(
        backup_root / "polaris.db",
        [
            (
                "POL-2026-000001",
                "M57",
                "wrong-name.fits",
                "/Users/doug/ProjectPolaris/targets/M57/fits/wrong-name.fits",
            ),
            (
                "POL-2026-000002",
                "M31",
                "original-name.fits",
                "/Users/doug/ProjectPolaris/targets/M57/fits/"
                "POL-2026-000002.fits",
            ),
        ],
    )

    report = verify_backup_pair(backup_root)

    assert not report["valid"]
    assert report["conflict_count"] == 2
    assert {conflict["type"] for conflict in report["conflicts"]} == {
        "target_mismatch",
        "asset_path_mismatch",
    }


def test_database_without_capture_schema_fails_cleanly(tmp_path):
    backup_root = tmp_path / "bad-schema"
    library_root = backup_root / "ProjectPolaris" / "targets"
    library_root.mkdir(parents=True)
    database_path = backup_root / "polaris.db"
    connection = sqlite3.connect(database_path)
    connection.execute("CREATE TABLE unexpected (id INTEGER)")
    connection.commit()
    connection.close()

    report = verify_backup_pair(backup_root)

    assert not report["valid"]
    assert not report["database_quick_check_ok"]
    assert "no such table: captures" in report["errors"][0]
