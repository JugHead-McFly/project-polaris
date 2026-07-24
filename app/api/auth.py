from fastapi import APIRouter
from fastapi import Depends

from app.core.auth import CurrentUser
from app.core.auth import get_current_user


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me", response_model=CurrentUser)
def current_identity(
    current_user: CurrentUser = Depends(get_current_user),
):
    return current_user
