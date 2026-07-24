from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker
from typing import Generator

from app.core.config import settings


def engine_options(database_url: str):
    options = {
        "pool_pre_ping": True,
    }
    if database_url.startswith("sqlite:"):
        options["connect_args"] = {
            "check_same_thread": False,
        }
    return options


engine = create_engine(
    settings.DATABASE_URL,
    **engine_options(settings.DATABASE_URL),
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Yield one database session per request and always release it."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        rollback = getattr(db, "rollback", None)
        if callable(rollback):
            rollback()
        raise
    finally:
        db.close()
