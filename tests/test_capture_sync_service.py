import hashlib
from pathlib import Path

from astropy.io import fits
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.models import Capture
from app.services.capture_sync_service import (
    inspect_capture_library,
    synchronize_capture_library,
)


def create_test_database():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def create_library_fits(
    library_root: Path,
    target: str,
    polaris_id: str,
) -> Path:
    path = library_root / "targets" / target / "fits" / f"{polaris_id}.fits"
    path.parent.mkdir(parents=True)
    hdu = fits.PrimaryHDU()
    hdu.header["OBJECT"] = target
    hdu.header["DATE-OBS"] = "2026-07-17T04:00:00"
    hdu.header["EXPTIME"] = 900.0
    hdu.header["GAIN"] = 100
    hdu.header["FILTER"] = "Duo-Band"
    hdu.header["RA"] = 283.3962
    hdu.header["DEC"] = 33.02914
    hdu.header["TELESCOP"] = "DWARF mini"
    hdu.writeto(path)
    return path


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_sync_is_dry_run_by_default_and_apply_is_idempotent(tmp_path):
    db = create_test_database()
    fits_path = create_library_fits(
        tmp_path,
        "M57",
        "POL-2026-000001",
    )
    original_digest = file_digest(fits_path)

    dry_run = synchronize_capture_library(
        db=db,
        library_root=tmp_path,
    )
    assert dry_run["mode"] == "dry-run"
    assert dry_run["orphan_count"] == 1
    assert db.query(Capture).count() == 0

    applied = synchronize_capture_library(
        db=db,
        library_root=tmp_path,
        apply=True,
    )
    assert applied["registered_count"] == 1
    assert applied["clean_after_apply"]
    assert applied["remaining_orphan_count"] == 0
    capture = db.query(Capture).one()
    assert capture.polaris_id == "POL-2026-000001"
    assert capture.object_name == "M57"
    assert capture.total_integration_seconds == 900
    assert capture.asset_path == str(fits_path)

    repeated = inspect_capture_library(
        db=db,
        library_root=tmp_path,
    )
    assert repeated["clean"]
    assert repeated["matched_count"] == 1
    assert file_digest(fits_path) == original_digest
    db.close()


def test_duplicate_library_ids_are_reported_as_conflicts(tmp_path):
    db = create_test_database()
    create_library_fits(tmp_path, "M57", "POL-2026-000001")
    create_library_fits(tmp_path, "M27", "POL-2026-000001")

    report = synchronize_capture_library(
        db=db,
        library_root=tmp_path,
        apply=True,
    )

    assert report["conflict_count"] == 1
    assert report["conflicts"][0]["type"] == "duplicate_library_id"
    assert report["apply_blocked"]
    assert report["registered_count"] == 0
    assert db.query(Capture).count() == 0
    db.close()
