"""Reproduce the old three-hour truncation with entirely synthetic inputs."""
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.scheduler_service import build_tonight_schedule

def compare():
    old = ModuleType("baseline_scheduler")
    source = subprocess.check_output(["git", "show", "eef6088:app/services/scheduler_service.py"],
                                     cwd=ROOT, text=True, encoding="utf-8")
    exec(compile(source, "baseline_scheduler", "exec"), old.__dict__)
    start = datetime(2026, 10, 17, 20, tzinfo=timezone.utc)
    candidates = []
    for index in range(8):
        candidates.append({"advisor": {"object": f"SYNTHETIC-{index}", "remaining_seconds": 2400},
            "observable": True, "planner_score": 100-index,
            "recommended_start": (start + timedelta(minutes=45*index)).strftime("%Y-%m-%d %I:%M %p"),
            "recommended_end": (start + timedelta(minutes=45*(index+1))).strftime("%Y-%m-%d %I:%M %p")})
    planner = {"recommended_target": candidates[0], "alternatives": candidates[1:6],
        "schedule_candidates": candidates, "decision": "Proceed", "notes": [], "weather": {}, "moon": {},
        "darkness": {"astronomical_darkness_start": "2026-10-17 08:00 PM",
                     "astronomical_darkness_end": "2026-10-18 02:00 AM"}}
    result = {}
    for label, build in [("current_develop_eef6088", old.build_tonight_schedule), ("fixed", build_tonight_schedule)]:
        schedule = build(planner, timezone_name="UTC")
        result[label] = {"block_count": len(schedule["blocks"]),
                         "allocated_minutes": schedule["allocated_minutes"],
                         "unscheduled_dark_minutes": schedule["unscheduled_dark_minutes"],
                         "last_end": schedule["blocks"][-1]["end"]}
    return result

if __name__ == "__main__":
    print(json.dumps(compare(), indent=2))
