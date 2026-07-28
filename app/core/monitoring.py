from pathlib import PurePath
from typing import Dict

import sentry_sdk

from app.core.config import Settings
from app.core.config import settings


REDACTED_EXCEPTION = "Internal exception details redacted."
SAFE_EVENT_FIELDS = {
    "event_id",
    "environment",
    "level",
    "platform",
    "release",
    "timestamp",
}
SAFE_FRAME_FIELDS = {
    "colno",
    "function",
    "in_app",
    "lineno",
    "module",
}
SAFE_TAGS = {
    "http.request.method",
    "polaris.request_id",
}

_monitoring_enabled = False


def _safe_frame(frame: Dict) -> Dict:
    sanitized = {
        key: frame[key]
        for key in SAFE_FRAME_FIELDS
        if key in frame
    }
    filename = frame.get("filename")
    if filename:
        parts = PurePath(str(filename)).parts
        if "app" in parts:
            sanitized["filename"] = "/".join(
                parts[parts.index("app"):]
            )
        else:
            sanitized["filename"] = PurePath(str(filename)).name
    return sanitized


def _safe_exception(exception: Dict) -> Dict:
    values = []
    for value in exception.get("values", []):
        if not isinstance(value, dict):
            continue
        sanitized_value = {
            "type": str(value.get("type") or "Exception"),
            "value": REDACTED_EXCEPTION,
        }
        stacktrace = value.get("stacktrace")
        if isinstance(stacktrace, dict):
            frames = [
                _safe_frame(frame)
                for frame in stacktrace.get("frames", [])
                if isinstance(frame, dict)
            ]
            if frames:
                sanitized_value["stacktrace"] = {"frames": frames}
        values.append(sanitized_value)
    return {"values": values}


def scrub_monitoring_event(event: Dict, hint: Dict) -> Dict:
    """Build a minimal allowlisted event before transmission."""
    sanitized = {
        key: event[key]
        for key in SAFE_EVENT_FIELDS
        if key in event
    }

    exception = event.get("exception")
    if isinstance(exception, dict):
        sanitized["exception"] = _safe_exception(exception)

    tags = event.get("tags")
    if isinstance(tags, dict):
        sanitized_tags = {
            key: tags[key]
            for key in SAFE_TAGS
            if key in tags
        }
        if sanitized_tags:
            sanitized["tags"] = sanitized_tags

    contexts = event.get("contexts")
    if isinstance(contexts, dict):
        request_context = contexts.get("polaris_request")
        if isinstance(request_context, dict):
            sanitized["contexts"] = {
                "polaris_request": {
                    key: request_context[key]
                    for key in ("request_id", "method")
                    if key in request_context
                }
            }
    return sanitized


def configure_monitoring(config: Settings = settings) -> bool:
    """Initialize optional hosted monitoring without collecting PII."""
    global _monitoring_enabled
    _monitoring_enabled = False

    if (
        not config.SENTRY_DSN
        or config.ENVIRONMENT != "production"
        or not config.SENTRY_ALLOW_TRANSMISSION
    ):
        return False

    sentry_sdk.init(
        dsn=config.SENTRY_DSN,
        default_integrations=False,
        server_name="",
        environment=config.ENVIRONMENT,
        release=f"polaris@{config.VERSION}",
        send_default_pii=False,
        include_local_variables=False,
        include_source_context=False,
        max_request_body_size="never",
        traces_sample_rate=0.0,
        profiles_sample_rate=0.0,
        before_send=scrub_monitoring_event,
    )
    _monitoring_enabled = True
    return True


def capture_request_exception(
    error: Exception,
    *,
    request_id: str,
    method: str,
    path: str,
) -> None:
    """Capture a scrubbed failure with only safe request identifiers."""
    if not _monitoring_enabled:
        return

    # The path remains available to Polaris's local structured log but is
    # intentionally not attached to the third-party monitoring event.
    del path

    with sentry_sdk.isolation_scope() as scope:
        scope.set_tag("polaris.request_id", request_id)
        scope.set_tag("http.request.method", method)
        scope.set_context(
            "polaris_request",
            {
                "request_id": request_id,
                "method": method,
            },
        )
        sentry_sdk.capture_exception(error)


def capture_monitoring_smoke_test(test_id: str) -> None:
    """Send one synthetic production check through the privacy scrubber."""
    if not _monitoring_enabled:
        return

    with sentry_sdk.isolation_scope() as scope:
        scope.set_tag("polaris.request_id", test_id)
        scope.set_tag("http.request.method", "STARTUP")
        scope.set_context(
            "polaris_request",
            {
                "request_id": test_id,
                "method": "STARTUP",
            },
        )
        sentry_sdk.capture_exception(
            RuntimeError("Polaris synthetic monitoring check.")
        )
    sentry_sdk.flush(timeout=5.0)
