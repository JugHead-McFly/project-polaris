from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.observatory import DEFAULT_POSTAL_CODE
from app.models import Capture
from app.services.advisor_service import get_exposure_advice
from app.services.astronomy_service import (
    get_altitude,
    get_altitude_at,
    get_darkness_info,
    get_darkness_window_datetimes,
    get_moon_info,
    get_moon_separation_at,
    get_moon_warning_at,
    get_transit_time,
)
from app.services.portfolio_service import TARGET_PRIORITY
from app.services.weather_service import get_weather_summary
from app.core.planner_config import (
    ALTITUDE_SCORES,
    DARK_TIME_SCORES,
    PLANNER_PENALTIES,
    PLANNER_WEIGHTS,
)


MINIMUM_ALTITUDE_DEGREES = 20.0
SAMPLE_INTERVAL_MINUTES = 15
MINIMUM_USABLE_DARK_MINUTES = 45


def get_priority_bonus(object_name: str) -> int:
    if object_name not in TARGET_PRIORITY:
        return 0

    position = TARGET_PRIORITY.index(object_name)
    return (len(TARGET_PRIORITY) - position) * 5


def get_moon_score_adjustment(
    moon_separation: Optional[float],
    moon_warning: Optional[str],
) -> int:
    if moon_separation is None:
        return -5

    if moon_warning is None:
        return 0

    warning = moon_warning.lower()

    if warning.startswith("none"):
        return 10
    if warning.startswith("minimal"):
        return 8
    if warning.startswith("low"):
        return 3
    if warning.startswith("moderate"):
        return -10
    if warning.startswith("high"):
        return -25

    return 0


def generate_sample_times(
    dark_start: datetime,
    dark_end: datetime,
) -> List[datetime]:
    sample_times = []
    current_time = dark_start

    while current_time <= dark_end:
        sample_times.append(current_time)
        current_time += timedelta(minutes=SAMPLE_INTERVAL_MINUTES)

    if not sample_times or sample_times[-1] < dark_end:
        sample_times.append(dark_end)

    return sample_times


def find_longest_usable_run(usable_samples: List) -> List:
    if not usable_samples:
        return []

    longest_run = []
    current_run = []
    previous_time = None

    for sample_time, altitude in usable_samples:
        if (
            previous_time is None
            or sample_time - previous_time
            <= timedelta(minutes=SAMPLE_INTERVAL_MINUTES + 1)
        ):
            current_run.append((sample_time, altitude))
        else:
            if len(current_run) > len(longest_run):
                longest_run = current_run
            current_run = [(sample_time, altitude)]

        previous_time = sample_time

    if len(current_run) > len(longest_run):
        longest_run = current_run

    return longest_run


def get_dark_visibility(
    object_name: str,
    dark_start: datetime,
    dark_end: datetime,
) -> Dict:
    sample_times = generate_sample_times(
        dark_start=dark_start,
        dark_end=dark_end,
    )

    altitude_samples = []

    for sample_time in sample_times:
        altitude = get_altitude_at(
            target_name=object_name,
            observation_datetime=sample_time,
        )

        if altitude is None:
            return {
                "known_position": False,
                "usable_dark_minutes": 0,
                "usable_dark_hours": 0.0,
                "maximum_dark_altitude": None,
                "average_dark_altitude": None,
                "recommended_start_datetime": None,
                "recommended_end_datetime": None,
            }

        altitude_samples.append((sample_time, altitude))

    all_altitudes = [altitude for _, altitude in altitude_samples]
    usable_samples = [
        (sample_time, altitude)
        for sample_time, altitude in altitude_samples
        if altitude >= MINIMUM_ALTITUDE_DEGREES
    ]

    if not usable_samples:
        return {
            "known_position": True,
            "usable_dark_minutes": 0,
            "usable_dark_hours": 0.0,
            "maximum_dark_altitude": round(max(all_altitudes), 1),
            "average_dark_altitude": round(
                sum(all_altitudes) / len(all_altitudes),
                1,
            ),
            "recommended_start_datetime": None,
            "recommended_end_datetime": None,
        }

    longest_run = find_longest_usable_run(usable_samples)

    if not longest_run:
        return {
            "known_position": True,
            "usable_dark_minutes": 0,
            "usable_dark_hours": 0.0,
            "maximum_dark_altitude": round(max(all_altitudes), 1),
            "average_dark_altitude": round(
                sum(all_altitudes) / len(all_altitudes),
                1,
            ),
            "recommended_start_datetime": None,
            "recommended_end_datetime": None,
        }

    recommended_start = longest_run[0][0]
    recommended_end = min(
        longest_run[-1][0] + timedelta(minutes=SAMPLE_INTERVAL_MINUTES),
        dark_end,
    )
    usable_minutes = int(
        (recommended_end - recommended_start).total_seconds() / 60
    )
    usable_altitudes = [altitude for _, altitude in longest_run]

    return {
        "known_position": True,
        "usable_dark_minutes": usable_minutes,
        "usable_dark_hours": round(usable_minutes / 60, 2),
        "maximum_dark_altitude": round(max(usable_altitudes), 1),
        "average_dark_altitude": round(
            sum(usable_altitudes) / len(usable_altitudes),
            1,
        ),
        "recommended_start_datetime": recommended_start,
        "recommended_end_datetime": recommended_end,
    }

def get_altitude_score(
    maximum_altitude: Optional[float],
) -> int:
    if maximum_altitude is None:
        return ALTITUDE_SCORES[
            "unknown"
        ]

    if maximum_altitude >= 70:
        return ALTITUDE_SCORES[
            "70_plus"
        ]

    if maximum_altitude >= 55:
        return ALTITUDE_SCORES[
            "55_plus"
        ]

    if maximum_altitude >= 40:
        return ALTITUDE_SCORES[
            "40_plus"
        ]

    if maximum_altitude >= 30:
        return ALTITUDE_SCORES[
            "30_plus"
        ]

    if maximum_altitude >= 20:
        return ALTITUDE_SCORES[
            "20_plus"
        ]

    return ALTITUDE_SCORES[
        "below_20"
    ]

def get_average_altitude_score(
    average_altitude: Optional[float],
) -> int:
    if average_altitude is None:
        return -60

    if average_altitude >= 65:
        return 30

    if average_altitude >= 55:
        return 24

    if average_altitude >= 45:
        return 18

    if average_altitude >= 35:
        return 10

    if average_altitude >= 20:
        return 4

    return -50

def get_dark_time_score(
    usable_dark_minutes: int,
) -> int:
    if usable_dark_minutes >= 240:
        return DARK_TIME_SCORES[
            "240_plus"
        ]

    if usable_dark_minutes >= 180:
        return DARK_TIME_SCORES[
            "180_plus"
        ]

    if usable_dark_minutes >= 120:
        return DARK_TIME_SCORES[
            "120_plus"
        ]

    if usable_dark_minutes >= 60:
        return DARK_TIME_SCORES[
            "60_plus"
        ]

    if usable_dark_minutes >= 45:
        return DARK_TIME_SCORES[
            "45_plus"
        ]

    return DARK_TIME_SCORES[
        "below_45"
    ]

def build_selection_reason(
    object_name: str,
    maximum_altitude: Optional[float],
    usable_dark_hours: float,
    remaining_hours: float,
    confidence: int,
    moon_warning: Optional[str],
) -> str:
    reasons = []

    if maximum_altitude is not None:
        reasons.append(
            f"reaches {maximum_altitude:.1f}° during astronomical darkness"
        )

    reasons.append(f"has {usable_dark_hours:.2f} usable dark hours tonight")

    if remaining_hours > 0:
        reasons.append(
            f"needs {remaining_hours:.2f} more integration hours"
        )
    else:
        reasons.append("has reached its current integration goal")

    reasons.append(f"recommendation confidence is {confidence}%")

    if moon_warning:
        reasons.append(moon_warning)

    cleaned_reasons = [reason.rstrip(".") for reason in reasons]

    return (
        f"{object_name} was ranked because it "
        + ", ".join(cleaned_reasons)
        + "."
    )


def build_target_plan(
    db: Session,
    object_name: str,
    dark_start: datetime,
    dark_end: datetime,
) -> Dict:
    advisor = get_exposure_advice(
        db=db,
        object_name=object_name,
    )

    visibility = get_dark_visibility(
        object_name=object_name,
        dark_start=dark_start,
        dark_end=dark_end,
    )

    midpoint = dark_start + (dark_end - dark_start) / 2

    altitude_at_midpoint = get_altitude_at(
        target_name=object_name,
        observation_datetime=midpoint,
    )

    moon_separation = get_moon_separation_at(
        target_name=object_name,
        observation_datetime=midpoint,
    )

    moon_warning = get_moon_warning_at(
        target_name=object_name,
        observation_datetime=midpoint,
    )

    usable_dark_minutes = visibility["usable_dark_minutes"]

    observable = (
        visibility["known_position"]
        and usable_dark_minutes >= MINIMUM_USABLE_DARK_MINUTES
    )

    confidence_score = (
        float(advisor["confidence"])
        * PLANNER_WEIGHTS[
            "advisor_confidence"
        ]
    )

    priority_score = (
        get_priority_bonus(object_name)
        * PLANNER_WEIGHTS[
            "portfolio_priority"
        ]
    )

    maximum_altitude_score = (
        get_altitude_score(
            visibility[
                "maximum_dark_altitude"
            ]
        )
        * PLANNER_WEIGHTS[
            "maximum_altitude"
        ]
    )

    average_altitude_score = (
        get_average_altitude_score(
            visibility[
                "average_dark_altitude"
            ]
        )
        * PLANNER_WEIGHTS[
            "average_altitude"
        ]
    )

    dark_time_score = (
        get_dark_time_score(
            usable_dark_minutes
        )
        * PLANNER_WEIGHTS[
            "usable_dark_time"
        ]
    )

    moon_score = (
        get_moon_score_adjustment(
            moon_separation=moon_separation,
            moon_warning=moon_warning,
        )
        * PLANNER_WEIGHTS[
            "moon_conditions"
        ]
    )

    score = (
        confidence_score
        + priority_score
        + maximum_altitude_score
        + average_altitude_score
        + dark_time_score
        + moon_score
    )

    if advisor["remaining_seconds"] == 0:
        score -= PLANNER_PENALTIES[
            "completed_target"
        ]

    if not observable:
        score -= PLANNER_PENALTIES[
            "not_observable"
        ]

    recommended_start_datetime = visibility["recommended_start_datetime"]
    recommended_end_datetime = visibility["recommended_end_datetime"]

    recommended_start = (
        recommended_start_datetime.strftime("%Y-%m-%d %I:%M %p")
        if recommended_start_datetime is not None
        else None
    )
    recommended_end = (
        recommended_end_datetime.strftime("%Y-%m-%d %I:%M %p")
        if recommended_end_datetime is not None
        else None
    )

    selection_reason = build_selection_reason(
        object_name=object_name,
        maximum_altitude=visibility["maximum_dark_altitude"],
        usable_dark_hours=visibility["usable_dark_hours"],
        remaining_hours=advisor["remaining_hours"],
        confidence=advisor["confidence"],
        moon_warning=moon_warning,
    )

    return {
        "advisor": advisor,
        "planner_score": round(score, 1),
        "observable": observable,
        "current_altitude": get_altitude(object_name),
        "altitude_at_dark_midpoint": altitude_at_midpoint,
        "maximum_dark_altitude": visibility["maximum_dark_altitude"],
        "average_dark_altitude": visibility["average_dark_altitude"],
        "usable_dark_minutes": usable_dark_minutes,
        "usable_dark_hours": visibility["usable_dark_hours"],
        "transit_time": get_transit_time(
            object_name,
            reference_datetime=dark_start,
        ),
        "recommended_start": recommended_start,
        "recommended_end": recommended_end,
        "moon_separation_degrees": moon_separation,
        "moon_warning": moon_warning,
        "selection_reason": selection_reason,
    }


def get_distinct_targets(db: Session) -> List[str]:
    rows = (
        db.query(Capture.object_name)
        .filter(Capture.object_name.isnot(None))
        .filter(Capture.object_name != "")
        .distinct()
        .all()
    )

    return sorted(
        {
            object_name.strip().upper()
            for (object_name,) in rows
            if object_name
        }
    )


def get_weather_decision(weather: Dict) -> str:
    observing_rating = weather.get("observing_rating")

    if observing_rating is None:
        return "Conditions Unknown"
    if observing_rating >= 4:
        return "Proceed"
    if observing_rating == 3:
        return "Use Caution"

    return "Do Not Image"


def get_tonight_plan(db: Session) -> Dict:
    weather = get_weather_summary(DEFAULT_POSTAL_CODE)
    moon = get_moon_info()
    darkness = get_darkness_info()

    _sunset, dark_start, dark_end = get_darkness_window_datetimes()

    plans = []
    notes = []

    for object_name in get_distinct_targets(db):
        try:
            plans.append(
                build_target_plan(
                    db=db,
                    object_name=object_name,
                    dark_start=dark_start,
                    dark_end=dark_end,
                )
            )
        except ValueError:
            continue

    plans.sort(
        key=lambda plan: plan["planner_score"],
        reverse=True,
    )

    observable_plans = [
        plan
        for plan in plans
        if plan["observable"]
    ]

    best_theoretical_target = (
        observable_plans[0]
        if observable_plans
        else None
    )
    alternatives = observable_plans[1:6]

    decision = get_weather_decision(weather)
    recommended_target = None

    if decision == "Do Not Image":
        notes.append(
            "No target was scheduled because the weather rating is unsuitable."
        )

        if best_theoretical_target is not None:
            notes.append(
                "If conditions improve, the best target during "
                "astronomical darkness is "
                f"{best_theoretical_target['advisor']['object']}."
            )

    elif best_theoretical_target is not None:
        recommended_target = best_theoretical_target

    else:
        notes.append(
            "No cataloged target has at least "
            f"{MINIMUM_USABLE_DARK_MINUTES} minutes above the minimum "
            "altitude during astronomical darkness."
        )

    unknown_position_count = sum(
        1
        for plan in plans
        if plan["maximum_dark_altitude"] is None
    )

    if unknown_position_count:
        notes.append(
            f"{unknown_position_count} target(s) were not fully ranked "
            "because Polaris has no coordinate metadata for them."
        )

    cloud_cover = weather.get("cloud_cover_percent")

    if cloud_cover is not None and cloud_cover > 50:
        notes.append(
            "Cloud cover may significantly reduce image quality."
        )

    return {
        "recommended_target": recommended_target,
        "best_theoretical_target": best_theoretical_target,
        "alternatives": alternatives,
        "weather": weather,
        "moon": moon,
        "darkness": darkness,
        "decision": decision,
        "notes": notes,
    }
