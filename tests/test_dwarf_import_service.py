from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.observatory import BORTLE
from app.config.observatory import CAPTURE_LOCATION
from app.database.database import Base
from app.services.dwarf_import_service import get_or_create_session


def create_test_database():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_new_dwarf_session_uses_configured_capture_home_when_metadata_is_missing():
    database = create_test_database()

    session, created = get_or_create_session(
        db=database,
        session_info={
            "session_id": "SES-20260726-212636-875",
            "session_date": "2026-07-26",
        },
        source_folder=Path("DWARF_RAW_TELE_C_20"),
    )

    assert created is True
    assert session.location == CAPTURE_LOCATION
    assert session.bortle_class == BORTLE
    database.close()
