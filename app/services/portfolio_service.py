from typing import Any, Dict, List

from app.data.targets import TARGETS
from app.services.goal_engine_service import build_integration_goal

INTEGRATION_GOALS_HOURS = {
    object_name: build_integration_goal(object_name)["hours"]
    for object_name in TARGETS
}

TARGET_PRIORITY = [
    "M16",
    "M20",
    "M17",
    "M11",
    "M22",
]

SCIENCE_PRIORITY = {
    "M16": 30,
    "M17": 25,
    "M20": 20,
    "M11": 10,
    "M22": 10,
}

TARGET_METADATA = {
    "M16": {
        "constellation": "Serpens",
        "target_type": "Emission Nebula",
        "difficulty": "Intermediate",
        "recommended_filter": "Dual Narrowband",
        "exposure_seconds": 15,
        "gain": 80,
        "best_window": "Summer",
    },
    "M17": {
        "constellation": "Sagittarius",
        "target_type": "Emission Nebula",
        "difficulty": "Intermediate",
        "recommended_filter": "Dual Narrowband",
        "exposure_seconds": 15,
        "gain": 80,
        "best_window": "Summer",
    },
    "M20": {
        "constellation": "Sagittarius",
        "target_type": "Emission Nebula",
        "difficulty": "Intermediate",
        "recommended_filter": "Dual Narrowband",
        "exposure_seconds": 15,
        "gain": 80,
        "best_window": "Summer",
    },
    "M11": {
        "constellation": "Scutum",
        "target_type": "Open Cluster",
        "difficulty": "Easy",
        "recommended_filter": "UV/IR Cut",
        "exposure_seconds": 10,
        "gain": 60,
        "best_window": "Summer / Early Fall",
    },
    "M22": {
        "constellation": "Sagittarius",
        "target_type": "Globular Cluster",
        "difficulty": "Easy",
        "recommended_filter": "UV/IR Cut",
        "exposure_seconds": 10,
        "gain": 60,
        "best_window": "Summer / Early Fall",
    },
}


def get_portfolio_level(progress_percent: float) -> str:
    if progress_percent >= 125:
        return "Platinum"
    if progress_percent >= 100:
        return "Gold"
    if progress_percent >= 60:
        return "Silver"
    if progress_percent > 0:
        return "Bronze"
    return "Not Started"


def get_target_metadata(object_name: str) -> Dict[str, Any]:
    return TARGET_METADATA.get(
        object_name,
        {
            "constellation": "Unknown",
            "target_type": "Unknown",
            "difficulty": "Unknown",
            "recommended_filter": "Unknown",
            "exposure_seconds": 15,
            "gain": 60,
            "best_window": "Unknown",
        },
    )


def calculate_readiness_score(
    object_name: str,
    progress_percent: float,
    remaining_hours: float,
) -> int:
    metadata = get_target_metadata(object_name)

    score = 100 + SCIENCE_PRIORITY.get(object_name, 0)
    score += 10  # Current summer-season placeholder

    if progress_percent >= 100:
        score -= 60

    if progress_percent == 0:
        score += 15
    elif remaining_hours <= 2:
        score += 5

    if metadata["difficulty"] == "Easy":
        score += 5

    return score


def get_recommended_exposure(
    object_name: str,
    goal_hours: float,
) -> Dict[str, int]:
    metadata = get_target_metadata(object_name)
    exposure_seconds = metadata["exposure_seconds"]

    return {
        "exposure_seconds": exposure_seconds,
        "gain": metadata["gain"],
        "goal_subframes": int(
            goal_hours * 3600 / exposure_seconds
        ),
    }

def get_target_status(progress_percent: float) -> str:
    if progress_percent == 0:
        return "Planned"
    if progress_percent < 100:
        return "In Progress"
    return "Complete"


def get_next_action(progress_percent: float) -> str:
    if progress_percent == 0:
        return "Start imaging"
    if progress_percent < 100:
        return "Continue imaging"
    return "Complete"

def get_estimated_nights_remaining(
    remaining_hours: float,
    hours_per_night: float = 4.0,
) -> float:
    if remaining_hours <= 0:
        return 0

    return round(
        remaining_hours / hours_per_night,
        1,
    )

def get_season_score(object_name: str) -> int:
    if object_name in INTEGRATION_GOALS_HOURS:
        return 10

    return 5

def build_portfolio_target(
    object_name: str,
    total_hours: float,
):
    integration_goal = build_integration_goal(object_name)
    goal_hours = integration_goal["hours"]

    progress = min(
        round((total_hours / goal_hours) * 100, 1),
        125.0,
    )

    remaining_hours = round(
        max(goal_hours - total_hours, 0),
        2,
    )

    metadata = get_target_metadata(object_name)

    return {
        "object": object_name,
        "constellation": metadata["constellation"],
        "target_type": metadata["target_type"],
        "difficulty": metadata["difficulty"],
        "recommended_filter": metadata["recommended_filter"],
        "recommended_exposure": get_recommended_exposure(
            object_name,
            goal_hours,
        ),
        "season_score": get_season_score(object_name),
        "science_priority": SCIENCE_PRIORITY.get(object_name, 0),
        "readiness_score": calculate_readiness_score(
            object_name,
            progress,
            remaining_hours,
        ),
        "status": get_target_status(progress),
        "best_window": metadata["best_window"],
        "progress_percent": progress,
        "portfolio_level": get_portfolio_level(progress),
        "next_action": get_next_action(progress),
        "current_hours": total_hours,
        "goal_hours": goal_hours,
        "goal_tier": integration_goal["tier"],
        "goal_source": integration_goal["source"],
        "goal_options": integration_goal["options"],
        "goal_factors": integration_goal["factors"],
        "integration_goal_note": integration_goal["note"],
        "remaining_hours": remaining_hours,
        "estimated_nights_remaining": get_estimated_nights_remaining(
            remaining_hours
        ),
        "observable": True,
        "current_altitude": None,
        "transit_time": None,
        "moon_warning": None,
        "recommended_start": None,
        "recommended_end": None,
    }
