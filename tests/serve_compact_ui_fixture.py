"""In-memory compact UI review; synthetic sky/history, port 8110 only."""
from datetime import timedelta
from unittest.mock import patch
import uvicorn
from serve_import_plan_fixture import add_browser_fixture
from import_plan_fixture import workflow, START

NAMES = ["M27", "M57", "M31"]

def visibility(object_name, **kwargs):
    offsets = {"M27": (0, 2), "M57": (2, 3), "M31": (7, 8)}
    start, end = offsets[object_name]
    return {"known_position": True, "usable_dark_minutes": (end-start)*60,
            "usable_dark_hours": end-start, "maximum_dark_altitude": 60,
            "average_dark_altitude": 50, "recommended_start_datetime": START+timedelta(hours=start),
            "recommended_end_datetime": START+timedelta(hours=end), "target_geometry": None}

if __name__ == "__main__":
    with workflow() as flow, patch("app.services.planner_service.TARGETS", NAMES), \
            patch("app.services.planner_service.get_dark_visibility", visibility):
        add_browser_fixture(flow)
        uvicorn.run(flow.app, host="127.0.0.1", port=8110, access_log=False)
