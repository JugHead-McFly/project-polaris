from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel
from app.models import Capture
from app.database.database import SessionLocal
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
def create_session(payload: SessionCreate):
    db = SessionLocal()

    try:
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

    finally:
        db.close()


@router.get("")
def list_sessions():
    db = SessionLocal()

    try:
        return db.query(ObservingSession).order_by(ObservingSession.id).all()

    finally:
        db.close()

@router.get("/{session_id}")
def get_session(session_id: str):
    db = SessionLocal()

    try:
        session = (
            db.query(ObservingSession)
            .filter(ObservingSession.session_id == session_id)
            .first()
        )

        if session is None:
            return {"error": "Session not found"}

        captures = (
            db.query(Capture)
            .filter(Capture.session_id == session.id)
            .order_by(Capture.id)
            .all()
        )

        return {
            "session_id": session.session_id,
            "date": session.date,
            "location": session.location,
            "observatory": session.observatory,
            "moon_phase": session.moon_phase,
            "weather_summary": session.weather_summary,
            "notes": session.notes,
            "captures": [
                {
                    "polaris_id": c.polaris_id,
                    "object_name": c.object_name,
                    "filename": c.filename,
                    "status": c.status,
                }
                for c in captures
            ],
        }

    finally:
        db.close()