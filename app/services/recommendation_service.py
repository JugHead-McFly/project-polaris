from app.services.portfolio_service import TARGET_PRIORITY


def get_recommended_targets(portfolio_by_target: dict):
    unfinished = [
        target
        for target in TARGET_PRIORITY
        if portfolio_by_target[target]["progress_percent"] < 100
    ]

    recommended = unfinished[0] if unfinished else None
    backup = unfinished[1] if len(unfinished) > 1 else None

    return recommended, backup


def get_recommendation_reason(object_name: str) -> str:
    reasons = {
        "M16": "Highest priority target not yet completed.",
        "M17": "Continue building integration time.",
        "M20": "Strong summer target still pending.",
        "M11": "Excellent cluster target.",
        "M22": "Bright globular cluster target.",
    }

    return reasons.get(
        object_name,
        "Continue building your portfolio.",
    )


def get_backup_reason(object_name: str) -> str:
    reasons = {
        "M16": "Strong secondary target if the primary is unavailable.",
        "M17": "Continue building toward the integration goal.",
        "M20": "Good summer alternative target.",
        "M11": "Bright cluster that handles moonlight well.",
        "M22": "Bright globular cluster and reliable backup.",
    }

    return reasons.get(
        object_name,
        "No backup recommendation.",
    )