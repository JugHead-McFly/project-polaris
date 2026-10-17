from unittest.mock import patch
from fastapi.testclient import TestClient
from import_plan_fixture import workflow
from app.services import forecast_accuracy_service as forecast

def test_hosted_post_reads_forecast_history_only_after_recording():
    with workflow() as flow, TestClient(flow.app) as client, \
            patch('app.api.tonight.forecast_accuracy_summary', side_effect=AssertionError('Redundant pre-write summary')), \
            patch.object(forecast, 'forecast_accuracy_summary', wraps=forecast.forecast_accuracy_summary) as summary:
        response = client.post('/tonight')
        assert response.status_code == 200, response.text
        assert summary.call_count == 1
        assert response.json()['forecast_accuracy'] is not None
