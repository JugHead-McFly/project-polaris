"""Controlled latency reproduction; no provider, account or database access."""
import json
import sys
from pathlib import Path
from time import perf_counter, sleep
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services import weather_service as weather


def astronomy(*args):
    sleep(.3)
    return {'seeing': 'Good', 'transparency': 'Good'}


def nws(payload, *args):
    sleep(.4)
    payload['cloud_forecast_status'] = 'synthetic blend'


results = []
with patch.object(weather, '_get_astro_forecast', side_effect=astronomy), \
        patch.object(weather, 'blend_cloud_forecasts', side_effect=nws):
    for mode in ('sequential_before', 'parallel_after'):
        payload = {'provider': 'synthetic'}
        started = perf_counter()
        if mode == 'sequential_before':
            payload.update(weather._get_astro_forecast(None, None))
            weather.blend_cloud_forecasts(payload, None, None)
        else:
            weather._enrich_weather(payload, None, None)
        results.append({'mode': mode, 'seconds': round(perf_counter()-started, 3), 'payload': payload})
assert results[0]['payload'] == results[1]['payload']
print(json.dumps({'scope': 'Synthetic delays: astronomy 300ms, NWS 400ms. Not production timings.', 'runs': results}, indent=2))
