from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.database.database import get_tenant_db
from app.schemas.hosted_recommendation import (
    RecommendationFeedbackResponse,
)
from app.schemas.hosted_recommendation import (
    RecommendationFeedbackUpdate,
)
from app.services.hosted_recommendation_service import (
    save_recommendation_feedback,
)


router = APIRouter(
    prefix="/recommendations",
    tags=["Recommendations"],
)


@router.put(
    "/{recommendation_run_id}/feedback",
    response_model=RecommendationFeedbackResponse,
)
def update_recommendation_feedback(
    recommendation_run_id: UUID,
    update: RecommendationFeedbackUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_tenant_db),
):
    feedback = save_recommendation_feedback(
        db,
        user_id=current_user.user_id,
        recommendation_run_id=recommendation_run_id,
        useful=update.useful,
        reason=update.reason,
    )
    if feedback is None:
        raise HTTPException(
            status_code=404,
            detail="Recommendation not found.",
        )
    return feedback
