from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class FakeDatabase:
    closed = False

    def close(self):
        self.closed = True


def schedule_response():
    return {
        "date": "2026-07-17",
        "decision": "Proceed",
        "advisory_only": True,
        "blocks": [
            {
                "object": "M57",
                "start": "2026-07-17 09:14 PM",
                "end": "2026-07-17 11:24 PM",
                "duration_minutes": 130,
                "setup_minutes": 5,
                "imaging_minutes": 125,
                "planner_score": 149.6,
                "reason": "Highest-ranked observable target for this time window.",
                "recommended_sub_exposure_seconds": 15,
                "recommended_gain": 100.0,
                "recommended_filter": "Duo-Band",
                "recommendation_source": "best_capture",
                "planned_subframes": 497,
                "setup_changes": [
                    "Slew to and center M57",
                    "Select Duo-Band filter",
                ],
            }
        ],
        "allocated_minutes": 130,
        "unscheduled_dark_minutes": 267,
        "weather": {
            "postal_code": "85297",
            "observing_rating": 5,
            "status": "Live weather connected.",
        },
        "moon": {
            "illumination_percent": 15.0,
            "altitude_degrees": 9.5,
            "above_horizon": True,
            "next_moonrise": "2026-07-18 10:16 AM",
            "next_moonset": "2026-07-17 09:57 PM",
        },
        "darkness": {
            "sunset": "2026-07-17 07:31 PM",
            "astronomical_darkness_start": "2026-07-17 09:14 PM",
            "astronomical_darkness_end": "2026-07-18 03:51 AM",
        },
        "notes": [],
        "fallback_target": "M57",
    }


def test_schedule_endpoint_returns_typed_equipment_plan():
    database = FakeDatabase()

    with (
        patch(
            "app.api.schedule.SessionLocal",
            return_value=database,
        ),
        patch(
            "app.api.schedule.get_tonight_schedule",
            return_value=schedule_response(),
        ),
    ):
        response = TestClient(app).get("/planner/schedule")

    assert response.status_code == 200
    payload = response.json()
    assert payload["blocks"][0]["recommended_filter"] == "Duo-Band"
    assert payload["blocks"][0]["planned_subframes"] == 497
    assert database.closed
