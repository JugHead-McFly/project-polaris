from typing import Any, Dict, List


INTEGRATION_GOALS_HOURS = {
    "M16": 6.0,
    "M17": 6.0,
    "M20": 4.0,
    "M11": 2.0,
    "M22": 2.0,
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
    goal_hours = INTEGRATION_GOALS_HOURS.get(object_name, 4.0)

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
        "remaining_hours": remaining_hours,
        "estimated_nights_remaining": get_estimated_nights_remaining(
            remaining_hours
        ),
    }