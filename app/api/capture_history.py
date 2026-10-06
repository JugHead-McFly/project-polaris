import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.core.auth import CurrentUser, get_current_user
from app.database.database import get_db, get_tenant_db, TENANT_SESSION_KEY
from app.models.capture_history import LibrarySyncCredential
from app.schemas.capture_history import CaptureManifest
from app.services.capture_history_service import import_manifest, library_summary

router = APIRouter(tags=["Capture history"])


@router.get("/capture-history")
def history(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_tenant_db)):
    return library_summary(db, user.user_id)


@router.post("/capture-history/pair")
def pair(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_tenant_db)):
    token = secrets.token_urlsafe(48)
    row = db.get(LibrarySyncCredential, user.user_id)
    if row is None:
        row = LibrarySyncCredential(user_id=user.user_id)
        db.add(row)
    row.token_hash = hashlib.sha256(token.encode()).hexdigest()
    row.expires_at = datetime.now(timezone.utc) + timedelta(days=365)
    db.commit()
    return JSONResponse({"user_id": str(user.user_id), "token": token, "expires_at": row.expires_at.isoformat()},
                        headers={"Cache-Control": "no-store"})


@router.delete("/capture-history/pair")
def revoke(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_tenant_db)):
    row = db.get(LibrarySyncCredential, user.user_id)
    if row:
        db.delete(row)
        db.commit()
    return {"revoked": True}


@router.post("/capture-sync/{user_id}")
async def sync(user_id: UUID, request: Request, db: Session = Depends(get_db)):
    # This credential authorizes only this endpoint, never general account access.
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer ") or len(auth) > 200:
        raise HTTPException(401, "Valid library sync credential required")
    db.info[TENANT_SESSION_KEY] = user_id
    row = db.get(LibrarySyncCredential, user_id)
    digest = hashlib.sha256(auth[7:].encode()).hexdigest()
    now = datetime.now(timezone.utc)
    if row is None or not secrets.compare_digest(row.token_hash, digest) or row.expires_at.replace(tzinfo=timezone.utc) <= now:
        raise HTTPException(401, "Library sync credential invalid or expired")
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 2_000_000:
            raise HTTPException(413, "Capture summary too large")
    try:
        manifest = CaptureManifest.model_validate_json(raw)
        return import_manifest(db, user_id, manifest)
    except ValueError as error:
        db.rollback()
        raise HTTPException(422, "Invalid or conflicting capture summary") from error
