def calculate_night_rating(weather, moon, target):
    target = target or {}
    deductions = []

    def planned_or_current(field):
        return weather.get(f"planned_{field}", weather.get(field))

    if all(
        planned_or_current(field) is None
        for field in (
            "cloud_cover_percent",
            "humidity_percent",
            "wind_speed_mph",
        )
    ):
        return {
            "score": 0,
            "quality": "Unavailable",
            "deductions": [],
        }

    score = 100

    cloud_cover = planned_or_current("cloud_cover_percent")
    if cloud_cover is not None:
        cloud_penalty = cloud_cover * 0.5
        score -= cloud_penalty
        if cloud_penalty > 0:
            deductions.append({"label": "Cloud cover", "points": cloud_penalty})

    humidity = planned_or_current("humidity_percent")
    if humidity is not None and humidity > 75:
        score -= 10
        deductions.append({"label": "High humidity", "points": 10})

    wind_speed = planned_or_current("wind_speed_mph")
    if wind_speed is not None and wind_speed > 15:
        score -= 10
        deductions.append({"label": "Strong wind", "points": 10})

    illumination = moon.get("illumination_percent")
    if illumination is not None:
        moon_penalty = round(max(0, min(100, illumination)) / 100 * 15, 1)
        score -= moon_penalty
        if moon_penalty > 0:
            deductions.append({"label": "Moon illumination", "points": moon_penalty})

    moon_separation = target.get("moon_separation_degrees")
    if moon_separation is not None and moon_separation < 20:
        score -= 15
        deductions.append({"label": "Moon close to target", "points": 15})

    score = max(0, min(100, round(score)))

    if score >= 90:
        quality = "Excellent"

    elif score >= 75:
        quality = "Good"

    elif score >= 60:
        quality = "Fair"

    elif score >= 40:
        quality = "Poor"

    else:
        quality = "Very Poor"

    return {
        "score": score,
        "quality": quality,
        "deductions": deductions,
    }
