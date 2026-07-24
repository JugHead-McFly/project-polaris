from typing import List
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Response
from fastapi import status
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.database.database import get_tenant_db
from app.schemas.hosted_account import ObservatoryCreate
from app.schemas.hosted_account import ObservatoryResponse
from app.schemas.hosted_account import ObservatoryUpdate
from app.schemas.hosted_account import ProfileResponse
from app.schemas.hosted_account import ProfileUpdate
from app.services.hosted_account_service import create_observatory
from app.services.hosted_account_service import delete_observatory
from app.services.hosted_account_service import get_observatory
from app.services.hosted_account_service import get_profile
from app.services.hosted_account_service import list_observatories
from app.services.hosted_account_service import update_observatory
from app.services.hosted_account_service import upsert_profile


router = APIRouter(tags=["Hosted Account"])


@router.get("/profile", response_model=ProfileResponse)
def read_profile(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_tenant_db),
):
    profile = get_profile(db, user_id=current_user.user_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Profile was not found.",
        )
    return profile


@router.put("/profile", response_model=ProfileResponse)
def write_profile(
    update: ProfileUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_tenant_db),
):
    return upsert_profile(
        db,
        user_id=current_user.user_id,
        update=update,
    )


@router.get(
    "/observatories",
    response_model=List[ObservatoryResponse],
)
def read_observatories(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_tenant_db),
):
    return list_observatories(
        db,
        user_id=current_user.user_id,
    )


@router.post(
    "/observatories",
    response_model=ObservatoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def write_observatory(
    create: ObservatoryCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_tenant_db),
):
    if get_profile(db, user_id=current_user.user_id) is None:
        raise HTTPException(
            status_code=409,
            detail="Create a profile before adding an observatory.",
        )
    return create_observatory(
        db,
        user_id=current_user.user_id,
        create=create,
    )


@router.get(
    "/observatories/{observatory_id}",
    response_model=ObservatoryResponse,
)
def read_observatory(
    observatory_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_tenant_db),
):
    observatory = get_observatory(
        db,
        user_id=current_user.user_id,
        observatory_id=observatory_id,
    )
    if observatory is None:
        raise HTTPException(
            status_code=404,
            detail="Observatory was not found.",
        )
    return observatory


@router.patch(
    "/observatories/{observatory_id}",
    response_model=ObservatoryResponse,
)
def revise_observatory(
    observatory_id: UUID,
    update: ObservatoryUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_tenant_db),
):
    observatory = update_observatory(
        db,
        user_id=current_user.user_id,
        observatory_id=observatory_id,
        update=update,
    )
    if observatory is None:
        raise HTTPException(
            status_code=404,
            detail="Observatory was not found.",
        )
    return observatory


@router.delete(
    "/observatories/{observatory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_observatory(
    observatory_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_tenant_db),
):
    deleted = delete_observatory(
        db,
        user_id=current_user.user_id,
        observatory_id=observatory_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Observatory was not found.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
