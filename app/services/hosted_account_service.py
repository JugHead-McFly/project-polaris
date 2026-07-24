from typing import List
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import HostedObservatory
from app.models import Profile
from app.schemas.hosted_account import ObservatoryCreate
from app.schemas.hosted_account import ObservatoryUpdate
from app.schemas.hosted_account import ProfileUpdate


def get_profile(
    db: Session,
    *,
    user_id: UUID,
) -> Optional[Profile]:
    return (
        db.query(Profile)
        .filter(Profile.user_id == user_id)
        .one_or_none()
    )


def upsert_profile(
    db: Session,
    *,
    user_id: UUID,
    update: ProfileUpdate,
) -> Profile:
    profile = get_profile(db, user_id=user_id)
    if profile is None:
        profile = Profile(
            user_id=user_id,
            display_name=update.display_name,
            onboarding_state=update.onboarding_state,
        )
        db.add(profile)
    else:
        profile.display_name = update.display_name
        profile.onboarding_state = update.onboarding_state

    db.commit()
    db.refresh(profile)
    return profile


def list_observatories(
    db: Session,
    *,
    user_id: UUID,
) -> List[HostedObservatory]:
    return (
        db.query(HostedObservatory)
        .filter(HostedObservatory.user_id == user_id)
        .order_by(HostedObservatory.created_at, HostedObservatory.id)
        .all()
    )


def get_observatory(
    db: Session,
    *,
    user_id: UUID,
    observatory_id: UUID,
) -> Optional[HostedObservatory]:
    return (
        db.query(HostedObservatory)
        .filter(
            HostedObservatory.id == observatory_id,
            HostedObservatory.user_id == user_id,
        )
        .one_or_none()
    )


def create_observatory(
    db: Session,
    *,
    user_id: UUID,
    create: ObservatoryCreate,
) -> HostedObservatory:
    observatory = HostedObservatory(
        user_id=user_id,
        **create.model_dump(),
    )
    db.add(observatory)
    db.commit()
    db.refresh(observatory)
    return observatory


def update_observatory(
    db: Session,
    *,
    user_id: UUID,
    observatory_id: UUID,
    update: ObservatoryUpdate,
) -> Optional[HostedObservatory]:
    observatory = get_observatory(
        db,
        user_id=user_id,
        observatory_id=observatory_id,
    )
    if observatory is None:
        return None

    for field_name, value in update.model_dump(
        exclude_unset=True
    ).items():
        setattr(observatory, field_name, value)
    db.commit()
    db.refresh(observatory)
    return observatory


def delete_observatory(
    db: Session,
    *,
    user_id: UUID,
    observatory_id: UUID,
) -> bool:
    observatory = get_observatory(
        db,
        user_id=user_id,
        observatory_id=observatory_id,
    )
    if observatory is None:
        return False

    db.delete(observatory)
    db.commit()
    return True
