from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from time import monotonic
from typing import Dict, Optional


PROCESS_STARTED_AT = datetime.now(timezone.utc)
PROCESS_STARTED_MONOTONIC = monotonic()

SERVICE_NAMES = {
    "weather": "Open-Meteo weather",
    "jpl_horizons": "NASA JPL Horizons",
}

_service_lock = RLock()
_service_states: Dict[str, Dict] = {
    key: {
        "service": label,
        "status": "Not Checked",
        "checked_at": None,
        "last_success_at": None,
        "message": "No request has been made during this process.",
    }
    for key, label in SERVICE_NAMES.items()
}


def _utc_iso(value: Optional[datetime] = None) -> str:
    timestamp = value or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc).isoformat()


def record_service_success(
    service_key: str,
    message: str,
    checked_at: Optional[datetime] = None,
) -> None:
    timestamp = _utc_iso(checked_at)
    with _service_lock:
        state = _service_states[service_key]
        state.update(
            {
                "status": "Healthy",
                "checked_at": timestamp,
                "last_success_at": timestamp,
                "message": message,
            }
        )


def record_service_failure(
    service_key: str,
    message: str,
    checked_at: Optional[datetime] = None,
) -> None:
    timestamp = _utc_iso(checked_at)
    with _service_lock:
        _service_states[service_key].update(
            {
                "status": "Degraded",
                "checked_at": timestamp,
                "message": message,
            }
        )


def get_service_diagnostics() -> list:
    with _service_lock:
        return [
            deepcopy(_service_states[key])
            for key in SERVICE_NAMES
        ]


def reset_service_diagnostics() -> None:
    with _service_lock:
        for key, label in SERVICE_NAMES.items():
            _service_states[key] = {
                "service": label,
                "status": "Not Checked",
                "checked_at": None,
                "last_success_at": None,
                "message": "No request has been made during this process.",
            }


def get_uptime_seconds() -> int:
    return max(int(monotonic() - PROCESS_STARTED_MONOTONIC), 0)
