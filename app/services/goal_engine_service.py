"""Explainable starter integration goals for deep-sky imaging projects.

These goals are planning baselines, not predictions of final image quality.
They intentionally use broad target classes and a small, reviewed set of
object-specific adjustments so every number can be explained to the operator.
"""

from typing import Dict, List, Optional

from app.data.targets import get_target_profile


DEFAULT_GOAL_TIER = "detailed"

GOAL_TIER_MULTIPLIERS = {
    "quick": 0.5,
    "detailed": 1.0,
    "showcase": 2.0,
}

GOAL_TIER_LABELS = {
    "quick": "Quick",
    "detailed": "Detailed",
    "showcase": "Showcase",
}

GOAL_TIER_DESCRIPTIONS = {
    "quick": "A first complete result and an early processing review.",
    "detailed": "A balanced project for stronger detail and cleaner processing.",
    "showcase": "A deeper project for lower noise and more processing latitude.",
}

TARGET_CLASS_GOALS = {
    "emission_nebula": {
        "hours": 6.0,
        "label": "emission or reflection nebula",
        "reason": "Extended glowing gas and dust usually benefit from sustained integration.",
    },
    "planetary_nebula": {
        "hours": 5.0,
        "label": "planetary nebula",
        "reason": "Small bright structure is accessible, while faint outer detail needs more time.",
    },
    "galaxy": {
        "hours": 8.0,
        "label": "galaxy",
        "reason": "Faint arms, dust lanes, and outer structure generally need deeper integration.",
    },
    "globular_cluster": {
        "hours": 3.0,
        "label": "globular cluster",
        "reason": "The bright stellar core develops sooner than faint nebular or galactic detail.",
    },
    "open_cluster": {
        "hours": 2.0,
        "label": "open cluster",
        "reason": "Bright separated stars usually reach a useful project depth relatively quickly.",
    },
    "solar_system": {
        "hours": 1.0,
        "label": "solar-system target",
        "reason": "Sharp frames and atmospheric steadiness matter more than a long deep-sky integration.",
    },
    "transient": {
        "hours": 2.0,
        "label": "transient target",
        "reason": "A shorter session goal fits an object whose position and appearance change over time.",
    },
    "unknown": {
        "hours": 4.0,
        "label": "uncategorized target",
        "reason": "Polaris lacks enough catalog detail for a more specific starting goal.",
    },
}

# Only use an adjustment when the reason is clear enough to show to the user.
TARGET_GOAL_ADJUSTMENTS = {
    "C 20": {
        "hours": 2.0,
        "reason": "Its exceptionally broad emission structure adds 2 hours.",
    },
    "M20": {
        "hours": 1.0,
        "reason": "Its combined emission, reflection, and dark-dust detail adds 1 hour.",
    },
    "M31": {
        "hours": -1.0,
        "reason": "Its bright central structure reduces the starter goal by 1 hour.",
    },
    "M57": {
        "hours": -1.0,
        "reason": "Its compact, bright ring reduces the starter goal by 1 hour.",
    },
    "M97": {
        "hours": 1.0,
        "reason": "Its faint planetary-nebula structure adds 1 hour.",
    },
}


def _round_goal_hours(hours: float) -> float:
    """Round to a practical half-hour planning increment."""
    return round(max(hours, 0.5) * 2) / 2


def _classify_target(object_name: str, object_type: Optional[str]) -> str:
    if object_name == "JUPITER":
        return "solar_system"
    if object_name.startswith("C ") and object_name != "C 20":
        return "transient"
    normalized = (object_type or "").lower()
    if "emission" in normalized or "reflection" in normalized:
        return "emission_nebula"
    if "planetary" in normalized:
        return "planetary_nebula"
    if "galaxy" in normalized:
        return "galaxy"
    if "globular" in normalized:
        return "globular_cluster"
    if "open cluster" in normalized:
        return "open_cluster"
    return "unknown"


def build_integration_goal(
    object_name: str,
    tier: str = DEFAULT_GOAL_TIER,
) -> Dict:
    normalized_name = object_name.strip().upper()
    normalized_tier = tier.strip().lower()
    if normalized_tier not in GOAL_TIER_MULTIPLIERS:
        raise ValueError(f"Unknown integration-goal tier: {tier}")

    profile = get_target_profile(normalized_name) or {}
    target_class = _classify_target(normalized_name, profile.get("object_type"))
    class_goal = TARGET_CLASS_GOALS[target_class]
    adjustment = TARGET_GOAL_ADJUSTMENTS.get(normalized_name)
    detailed_hours = class_goal["hours"]
    factors: List[str] = [
        f"{class_goal['label'].capitalize()} starter: {class_goal['hours']:g} hours.",
        class_goal["reason"],
    ]
    if adjustment:
        detailed_hours += adjustment["hours"]
        factors.append(adjustment["reason"])
    detailed_hours = _round_goal_hours(detailed_hours)

    options = []
    for option_tier, multiplier in GOAL_TIER_MULTIPLIERS.items():
        options.append(
            {
                "tier": option_tier,
                "label": GOAL_TIER_LABELS[option_tier],
                "hours": _round_goal_hours(detailed_hours * multiplier),
                "description": GOAL_TIER_DESCRIPTIONS[option_tier],
            }
        )

    selected = next(option for option in options if option["tier"] == normalized_tier)
    article = "an" if class_goal["label"][0].lower() in "aeiou" else "a"
    note = (
        f"{selected['label']} starter goal for {article} {class_goal['label']}. "
        f"{class_goal['reason']} "
        "This is a planning baseline, not an image-quality score or guarantee."
    )
    if adjustment:
        note = (
            f"{selected['label']} starter goal for {article} {class_goal['label']}. "
            f"{adjustment['reason']} "
            "This is a planning baseline, not an image-quality score or guarantee."
        )

    return {
        "tier": normalized_tier,
        "label": selected["label"],
        "hours": selected["hours"],
        "source": "Polaris target-class starter",
        "note": note,
        "factors": factors,
        "options": options,
    }
