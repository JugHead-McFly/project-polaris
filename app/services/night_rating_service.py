def calculate_night_rating(weather, moon, target):
    score = 100

    cloud_cover = weather.get("cloud_cover_percent")
    if cloud_cover is not None:
        score -= cloud_cover * 0.5

    if weather.get("humidity_percent", 0) > 75:
        score -= 10

    if weather.get("wind_speed_mph", 0) > 15:
        score -= 10

    if moon.get("illumination_percent", 100) > 75:
        score -= 20

    if target.get("moon_separation_degrees", 180) < 20:
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