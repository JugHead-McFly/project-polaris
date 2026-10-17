"""Local synthetic preview: python tests/serve_full_night_fixture.py (port 8109)."""
from datetime import timedelta
from unittest.mock import patch
import uvicorn
from serve_import_plan_fixture import add_browser_fixture
from import_plan_fixture import workflow, START

NAMES = ["M27", "M57", "M31", "M42", "M13", "M51", "M63", "M64"]

def visibility(object_name, **kwargs):
    index = NAMES.index(object_name)
    return {"known_position": True, "usable_dark_minutes": 60, "usable_dark_hours": 1,
            "maximum_dark_altitude": 70-index, "average_dark_altitude": 70-index,
            "recommended_start_datetime": START + timedelta(hours=index),
            "recommended_end_datetime": START + timedelta(hours=index+1), "target_geometry": None}

if __name__ == "__main__":
    with workflow() as flow, patch("app.services.planner_service.TARGETS", NAMES), \
            patch("app.services.planner_service.get_dark_visibility", visibility):
        add_browser_fixture(flow)
        uvicorn.run(flow.app, host="127.0.0.1", port=8109, access_log=False)
