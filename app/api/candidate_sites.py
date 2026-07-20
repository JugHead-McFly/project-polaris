from datetime import datetime
from typing import List

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

from app.database.database import SessionLocal
from app.models import CandidateSite
from app.schemas.candidate_site import CandidateSiteCreate
from app.schemas.candidate_site import CandidateSiteResponse
from app.schemas.candidate_site import CandidateSiteUpdate


router = APIRouter(prefix="/candidate-sites", tags=["Candidate Sites"])


@router.get("", response_model=List[CandidateSiteResponse])
def list_candidate_sites():
    db = SessionLocal()
    try:
        return db.query(CandidateSite).order_by(CandidateSite.created_at.desc()).all()
    finally:
        db.close()


@router.post("", response_model=CandidateSiteResponse, status_code=status.HTTP_201_CREATED)
def create_candidate_site(payload: CandidateSiteCreate):
    db = SessionLocal()
    try:
        site = CandidateSite(**payload.model_dump())
        db.add(site)
        db.commit()
        db.refresh(site)
        return site
    finally:
        db.close()


@router.patch("/{site_id}", response_model=CandidateSiteResponse)
def update_candidate_site(site_id: int, payload: CandidateSiteUpdate):
    db = SessionLocal()
    try:
        site = db.query(CandidateSite).filter(CandidateSite.id == site_id).first()
        if site is None:
            raise HTTPException(status_code=404, detail="Candidate site was not found.")
        updates = payload.model_dump(exclude_unset=True)
        for field in (
            "access_hours",
            "vehicle_requirement",
            "property_access",
            "parking_setup_confirmed",
            "horizon_confirmed",
            "access_confirmed",
            "amenities_confirmed",
            "notes",
        ):
            if field in updates:
                setattr(site, field, updates[field])
        if "visited" in updates:
            site.visited_at = datetime.utcnow() if updates["visited"] else None
            if not updates["visited"]:
                site.star_rating = None
        if "star_rating" in updates:
            if site.visited_at is None:
                raise HTTPException(
                    status_code=422,
                    detail="A site can be rated after it has been visited.",
                )
            site.star_rating = updates["star_rating"]
        db.commit()
        db.refresh(site)
        return site
    finally:
        db.close()


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate_site(site_id: int):
    db = SessionLocal()
    try:
        site = db.query(CandidateSite).filter(CandidateSite.id == site_id).first()
        if site is None:
            raise HTTPException(status_code=404, detail="Candidate site was not found.")
        db.delete(site)
        db.commit()
    finally:
        db.close()
