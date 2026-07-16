PLANNER_WEIGHTS = {
    "advisor_confidence": 0.7,
    "portfolio_priority": 0.2,
    "maximum_altitude": 0.8,
    "average_altitude": 1.2,
    "usable_dark_time": 1.0,
    "moon_conditions": 1.0,
}

PLANNER_PENALTIES = {
    "completed_target": 75,
    "not_observable": 100,
}

ALTITUDE_SCORES = {
    "70_plus": 30,
    "55_plus": 24,
    "40_plus": 16,
    "30_plus": 10,
    "20_plus": 4,
    "below_20": -50,
    "unknown": -60,
}

DARK_TIME_SCORES = {
    "240_plus": 25,
    "180_plus": 20,
    "120_plus": 14,
    "60_plus": 7,
    "45_plus": 2,
    "below_45": -40,
}