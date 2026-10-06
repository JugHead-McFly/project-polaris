"""Cloud-only forecast blend; source spread is not a calibrated confidence bound."""
import json
import math
import re
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError
from zoneinfo import ZoneInfo


def cloud_value(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) and 0 <= number <= 100 else None
    except (ValueError, TypeError):
        return None


def _request(url):
    if not url.startswith("https://api.weather.gov/"):
        raise ValueError("Unexpected NWS endpoint")
    with urlopen(Request(url, headers={
        "User-Agent": "ProjectPolaris/1.6 (astronomy planning)",
        "Accept": "application/geo+json",
    }), timeout=4) as response:
        return json.load(response)


def parse_nws_clouds(properties, checked_at):
    updated = datetime.fromisoformat(properties["updateTime"].replace("Z", "+00:00"))
    if updated.tzinfo is None or not timedelta(minutes=-10) <= checked_at-updated <= timedelta(hours=12):
        raise ValueError("NWS forecast is stale")
    intervals = []
    for row in properties.get("skyCover", {}).get("values", []):
        value = cloud_value(row.get("value"))
        if value is None:
            continue
        try:
            timestamp, duration = row["validTime"].split("/")
            start = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            match = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", duration)
            if not match or start.tzinfo is None:
                continue
            days, hours, minutes, seconds = (int(v or 0) for v in match.groups())
            end = start+timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
            if end > start:
                intervals.append((start, end, value))
        except (KeyError, ValueError, TypeError):
            continue
    return intervals, updated.isoformat()


def get_nws_clouds(context, checked_at):
    try:
        point = _request(f"https://api.weather.gov/points/{context.latitude:.4f},{context.longitude:.4f}")
        grid_url = point["properties"]["forecastGridData"]
        properties = _request(grid_url)["properties"]
        intervals, updated = parse_nws_clouds(properties, checked_at)
        return {"intervals": intervals, "updated_at": updated,
                "status": "available" if intervals else "unavailable"}
    except (URLError, TimeoutError, ValueError, KeyError, TypeError, OSError):
        return {"intervals": [], "updated_at": None, "status": "unavailable"}


def blend_cloud_forecasts(weather, context, checked_at):
    nws = get_nws_clouds(context, checked_at)
    weather["cloud_forecast_status"] = (
        f"{weather.get('provider', 'Primary')} + NWS where both cover the hour; equal-weight mean."
        if nws["status"] == "available" else
        "NWS unavailable or outside coverage; one forecast source only."
    )
    for timestamp, conditions in weather.get("hourly_forecast", {}).items():
        try:
            when = datetime.fromisoformat(timestamp)
            if when.tzinfo is None:
                when = when.replace(tzinfo=ZoneInfo(context.timezone_name))
        except (ValueError, TypeError):
            continue
        sources = []
        original = cloud_value(conditions.get("cloud_cover_percent"))
        if original is not None:
            sources.append({"provider": weather.get("provider") or "primary",
                            "cloud_cover_percent": original,
                            "fetched_at": weather.get("fetched_at")})
        values = [v for start, end, v in nws["intervals"] if start <= when < end]
        if values:
            sources.append({"provider": "nws", "cloud_cover_percent": values[-1],
                            "updated_at": nws["updated_at"], "fetched_at": checked_at.isoformat()})
        conditions["cloud_forecast_sources"] = sources
        conditions["cloud_cover_percent"] = None
        conditions["cloud_forecast_spread"] = None
        if sources:
            numbers = [s["cloud_cover_percent"] for s in sources]
            conditions["cloud_cover_percent"] = sum(numbers)/len(numbers)
            conditions["cloud_forecast_spread"] = max(numbers)-min(numbers)
    return weather


def summarize_dark_window(weather, start, end):
    """Time-weight hourly blended values, explicitly reporting missing hours."""
    total=(end-start).total_seconds()
    covered=weighted=multi=0
    for timestamp, row in weather.get("hourly_forecast", {}).items():
        try:
            t=datetime.fromisoformat(timestamp)
        except (TypeError, ValueError):
            continue
        if t.tzinfo is None:
            t=t.replace(tzinfo=start.tzinfo)
        elif start.tzinfo is not None:
            t=t.astimezone(start.tzinfo)
        else:
            continue
        a=max(start,t);b=min(end,t+timedelta(hours=1))
        seconds=max(0,(b-a).total_seconds());value=cloud_value(row.get("cloud_cover_percent"))
        if value is not None:
            covered+=seconds;weighted+=seconds*value
            if len(row.get("cloud_forecast_sources", []))>=2:multi+=seconds
    return {"start": start.isoformat(), "end": end.isoformat(),
            "average_cloud_cover_percent": weighted/covered if covered and total>0 and covered/total>=.9 else None,
            "coverage_percent": min(100,100*covered/total) if total>0 else 0,
            "multi_source_coverage_percent": min(100,100*multi/total) if total>0 else 0}
