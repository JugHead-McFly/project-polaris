from dataclasses import dataclass
from typing import List

from app.data.rig_profiles import RIG_PROFILES
from app.data.rig_profiles import RigProfile


@dataclass(frozen=True)
class RigProfileSummary:
    key: str
    label: str
    manufacturer: str
    has_field_of_view: bool
    has_battery_limit: bool
    has_storage_limit: bool
    has_temperature_limit: bool
    has_frame_limit: bool
    confidence: str


@dataclass(frozen=True)
class RigProfileCatalogSummary:
    total_profiles: int
    manufacturers: List[str]
    profiles_with_field_of_view: int
    profiles_with_battery_limit: int
    profiles_with_storage_limit: int
    profiles_with_temperature_limit: int
    profiles_with_frame_limit: int


def summarize_rig_profile(profile: RigProfile) -> RigProfileSummary:
    return RigProfileSummary(
        key=profile.key,
        label=f"{profile.manufacturer} {profile.model}",
        manufacturer=profile.manufacturer,
        has_field_of_view=profile.native_fov_degrees is not None,
        has_battery_limit=profile.battery_life_hours is not None,
        has_storage_limit=profile.storage_gb is not None,
        has_temperature_limit=profile.operating_temperature_c is not None,
        has_frame_limit=profile.frame_limit is not None,
        confidence=profile.confidence,
    )


def list_rig_profile_summaries() -> List[RigProfileSummary]:
    return [
        summarize_rig_profile(profile)
        for profile in sorted(
            RIG_PROFILES.values(),
            key=lambda item: (item.manufacturer.lower(), item.model.lower()),
        )
    ]


def summarize_rig_profile_catalog() -> RigProfileCatalogSummary:
    summaries = list_rig_profile_summaries()
    return RigProfileCatalogSummary(
        total_profiles=len(summaries),
        manufacturers=sorted({summary.manufacturer for summary in summaries}),
        profiles_with_field_of_view=sum(
            1 for summary in summaries if summary.has_field_of_view
        ),
        profiles_with_battery_limit=sum(
            1 for summary in summaries if summary.has_battery_limit
        ),
        profiles_with_storage_limit=sum(
            1 for summary in summaries if summary.has_storage_limit
        ),
        profiles_with_temperature_limit=sum(
            1 for summary in summaries if summary.has_temperature_limit
        ),
        profiles_with_frame_limit=sum(1 for summary in summaries if summary.has_frame_limit),
    )
