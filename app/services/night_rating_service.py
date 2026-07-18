def calculate_night_rating(weather, moon, target):
    target = target or {}

    if all(
        weather.get(field) is None
        for field in (
            "cloud_cover_percent",
            "humidity_percent",
            "wind_speed_mph",
        )
    ):
        return {
            "score": 0,
            "quality": "Unavailable",
        }

    score = 100

    cloud_cover = weather.get("cloud_cover_percent")
    if cloud_cover is not None:
        score -= cloud_cover * 0.5

    humidity = weather.get("humidity_percent")
    if humidity is not None and humidity > 75:
        score -= 10

    wind_speed = weather.get("wind_speed_mph")
    if wind_speed is not None and wind_speed > 15:
        score -= 10

    illumination = moon.get("illumination_percent")
    if illumination is not None and illumination > 75:
        score -= 20

    moon_separation = target.get("moon_separation_degrees")
    if moon_separation is not None and moon_separation < 20:
        score -= 15

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
    }
