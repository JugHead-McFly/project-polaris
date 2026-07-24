from typing import Generator

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy import text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.config import settings


TENANT_SESSION_KEY = "polaris_current_user_id"


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


def apply_tenant_context(
    session: Session,
    transaction,
    connection,
) -> None:
    """Set transaction-local PostgreSQL identity before owned queries."""
    user_id = session.info.get(TENANT_SESSION_KEY)
    if (
        user_id is None
        or connection.dialect.name != "postgresql"
    ):
        return
    connection.execute(
        text(
            "SELECT set_config("
            "'app.current_user_id', :user_id, true"
            ")"
        ),
        {"user_id": str(user_id)},
    )


event.listen(Session, "after_begin", apply_tenant_context)


def _managed_session(db: Session) -> Generator[Session, None, None]:
    try:
        yield db
    except Exception:
        rollback = getattr(db, "rollback", None)
        if callable(rollback):
            rollback()
        raise
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    """Yield a request session without hosted tenant context."""
    yield from _managed_session(SessionLocal())


def get_tenant_db(
    current_user: CurrentUser = Depends(get_current_user),
) -> Generator[Session, None, None]:
    """Yield a request session bound to the authenticated user."""
    db = SessionLocal()
    if not hasattr(db, "info"):
        db.info = {}
    db.info[TENANT_SESSION_KEY] = current_user.user_id
    yield from _managed_session(db)
