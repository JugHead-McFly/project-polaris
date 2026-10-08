from uuid import UUID
from fastapi import APIRouter, Depends, Request, Response, Query
from sqlalchemy.orm import Session
from app.core.auth import CurrentUser, get_current_user
from app.database.database import get_tenant_db
from app.api.obstructions import read_bounded_model
from app.schemas.obstruction_spot import SpotWrite
from app.services.obstruction_spot_service import owned_home, spot_query, describe, save_spot, delete_spot

router = APIRouter(prefix="/observatories/{home_id}/obstruction-spots", tags=["Saved obstruction spots"])


@router.get("")
def list_spots(home_id: UUID, response: Response, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_tenant_db)):
    response.headers["Cache-Control"] = "no-store"
    home = owned_home(db, user, home_id)
    return [describe(spot, home) for spot in spot_query(db, user, home_id).order_by("created_at", "id").all()]


@router.post("", status_code=201)
async def create_spot(home_id: UUID, request: Request, response: Response, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_tenant_db)):
    response.headers["Cache-Control"] = "no-store"
    return save_spot(db, user, home_id, await read_bounded_model(request, SpotWrite))


@router.put("/{spot_id}")
async def edit_spot(home_id: UUID, spot_id: UUID, request: Request, response: Response, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_tenant_db)):
    response.headers["Cache-Control"] = "no-store"
    return save_spot(db, user, home_id, await read_bounded_model(request, SpotWrite), spot_id)


@router.delete("/{spot_id}", status_code=204)
def remove_spot(home_id: UUID, spot_id: UUID, response: Response, expected_revision: int = Query(ge=1), user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_tenant_db)):
    response.headers["Cache-Control"] = "no-store"
    delete_spot(db, user, home_id, spot_id, expected_revision)
