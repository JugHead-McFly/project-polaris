"""Memory-only preview with synthetic sky and history, port 8111."""
from datetime import timedelta
from unittest.mock import patch
import uvicorn
from serve_import_plan_fixture import add_browser_fixture
from import_plan_fixture import workflow, START, END

NAMES = ["M27", "M57", "M31"]

def visibility(object_name, **kwargs):
    start, end = {"M27": (0, 3), "M57": (1, 6), "M31": (5, 8)}[object_name]
    samples = [{"at": (START+timedelta(hours=i/2)).isoformat(),
                "altitude_degrees": max(0, 70-abs(i/2-(start+end)/2)*70/(end-start)),
                "label": (START+timedelta(hours=i/2)).strftime("%H:%M")}
               for i in range(17)]
    return {"known_position": True, "usable_dark_minutes": (end-start)*60,
            "usable_dark_hours": end-start, "maximum_dark_altitude": 70,
            "average_dark_altitude": 50, "recommended_start_datetime": START+timedelta(hours=start),
            "recommended_end_datetime": START+timedelta(hours=end),
            "target_geometry": {"samples":samples,"peak_altitude_degrees":70,
                "peak_label":"Synthetic peak", "peak_at":(START+timedelta(hours=(start+end)/2)).isoformat()}}

if __name__ == "__main__":
    with workflow() as flow, patch("app.services.planner_service.TARGETS", NAMES), \
            patch("app.services.planner_service.get_dark_visibility", visibility), \
            patch("app.services.planner_service.get_darkness_info", return_value={
                "sunset":"2025-01-15 07:00 PM", "astronomical_darkness_start":"2025-01-15 08:00 PM",
                "astronomical_darkness_end":"2025-01-16 04:00 AM",
                "astronomical_darkness_start_at":START.isoformat(),
                "astronomical_darkness_end_at":END.isoformat()}):
        add_browser_fixture(flow)
        uvicorn.run(flow.app, host="127.0.0.1", port=8111, access_log=False)
