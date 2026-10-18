"""Descriptive cloud-source agreement, never a probability or model confidence."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from zoneinfo import ZoneInfo
from app.services.cloud_forecast_service import cloud_value


def location_key(context):
    return sha256(f'{context.latitude!r}|{context.longitude!r}'.encode()).hexdigest()


def utc(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (AttributeError, TypeError, ValueError):
        return None


def summarize_agreement(weather, context, start, end):
    start, end = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
    result = dict(state='unavailable', label='Comparison unavailable',
        start=start.isoformat(), end=end.isoformat(), compared_minutes=0.0,
        coverage_percent=0.0, average_spread_points=None, maximum_spread_points=None,
        providers=[], independence='Underlying model independence not verified',
        basis='Cloud-cover percentage-point spread for matching hours and location; not a clear-sky probability.')
    if end <= start or weather.get('cache_status') == 'stale':
        return dict(result, reason='Forecast is stale or the night window is unavailable.')
    expected_location = location_key(context)
    intervals = []
    provider_set = set()
    single_source = False
    for timestamp, row in weather.get('hourly_forecast', {}).items():
        at = utc(timestamp)
        if at is None:
            try:
                local = datetime.fromisoformat(timestamp)
                zone = ZoneInfo(context.timezone_name)
                if local.tzinfo is not None or local.replace(tzinfo=zone, fold=0).utcoffset() != local.replace(tzinfo=zone, fold=1).utcoffset():
                    continue  # A repeated/missing local hour needs an explicit offset.
                at = local.replace(tzinfo=zone).astimezone(timezone.utc)
            except (TypeError, ValueError):
                continue
        until = at + timedelta(hours=1)
        left, right = max(start, at), min(end, until)
        if right <= left:
            continue
        sources = {}
        for source in row.get('cloud_forecast_sources', []):
            name = str(source.get('provider', '')).strip().lower()
            value = cloud_value(source.get('cloud_cover_percent'))
            valid_from, valid_to = utc(source.get('valid_from')), utc(source.get('valid_to'))
            if (name not in {'open-meteo', 'weatherapi', 'nws'} or value is None
                    or source.get('location_key') != expected_location
                    or valid_from is None or valid_to is None
                    or valid_from > left or valid_to < right):
                continue
            # Duplicate provider entries cannot be counted as independent votes.
            if name in sources and sources[name] != value:
                sources[name] = None
            elif name not in sources:
                sources[name] = value
        sources = {name: value for name, value in sources.items() if value is not None}
        single_source |= len(sources) == 1
        if len(sources) < 2:
            continue
        # Never count duplicate or overlapping forecast hours twice.
        if any(left < b and right > a for a, b, _ in intervals):
            return dict(result, reason='Overlapping forecast hours cannot be compared reliably.')
        values = list(sources.values())
        intervals.append((left, right, max(values)-min(values)))
        provider_set.update(sources)
    seconds = sum((b-a).total_seconds() for a,b,_ in intervals)
    if not seconds:
        return dict(result, reason='Only one forecast source is available.' if single_source else 'Matching forecast hours from two sources are unavailable.')
    spread = sum((b-a).total_seconds()*v for a,b,v in intervals)/seconds
    coverage = seconds/(end-start).total_seconds()*100
    state = 'close' if spread <= 15 else 'mixed' if spread < 30 else 'split'
    labels = {'close':'Forecasts broadly agree', 'mixed':'Forecasts differ', 'split':'Forecasts disagree'}
    return dict(result, state=state, label=labels[state],
        compared_minutes=round(seconds/60,1), coverage_percent=round(coverage,1),
        average_spread_points=round(spread,1), maximum_spread_points=round(max(v for _,_,v in intervals),1),
        providers=sorted(provider_set), partial=coverage < 90,
        reason='Comparison covers only part of the night.' if coverage < 90 else 'Compared across the dark window.')
