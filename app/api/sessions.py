from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.models import Capture
from app.database.database import get_db
from app.models import ObservingSession

router = APIRouter(prefix="/sessions", tags=["Sessions"])


class SessionCreate(BaseModel):
    date: str
    location: str
    observatory: str = "Doug's Observatory"
    moon_phase: str = ""
    weather_summary: str = ""
    notes: str = ""


def _next_session_id():
    return f"SES-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"


@router.post("")
def create_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
):
    session = ObservingSession(
        session_id=_next_session_id(),
        date=payload.date,
        location=payload.location,
        observatory=payload.observatory,
        moon_phase=payload.moon_phase,
        weather_summary=payload.weather_summary,
        notes=payload.notes,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


@router.get("")
def list_sessions(db: Session = Depends(get_db)):
    return db.query(ObservingSession).order_by(ObservingSession.id).all()

@router.get(
    "/{session_id}",
    responses={
        404: {
            "description": "Session not found",
        }
    },
)
def get_session(
    session_id: str = Path(
        ...,
        title="Session ID",
        description="Observing session identifier, for example SES-20260712-195949",
        examples=["SES-20260712-195949"],
    ),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ObservingSession)
        .filter(ObservingSession.session_id == session_id)
        .first()
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' was not found.",
        )

    return session
