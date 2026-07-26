from copy import deepcopy
from typing import Dict
from typing import Optional

import sentry_sdk

from app.core.config import Settings
from app.core.config import settings


FILTERED = "[Filtered]"
SENSITIVE_KEY_PARTS = {
    "address",
    "authorization",
    "cookie",
    "email",
    "latitude",
    "longitude",
    "password",
    "secret",
    "token",
}


def _sensitive_key(key) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def _scrub(value, *, key: Optional[str] = None):
    if key is not None and _sensitive_key(key):
        return FILTERED
    if isinstance(value, dict):
        return {
            item_key: _scrub(item_value, key=item_key)
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_scrub(item) for item in value)
    return value


def scrub_monitoring_event(event: Dict, hint: Dict) -> Dict:
    """Remove Polaris personal and credential data before transmission."""
    sanitized = _scrub(deepcopy(event))
    sanitized.pop("user", None)
    sanitized.pop("breadcrumbs", None)

    request_data = sanitized.get("request")
    if isinstance(request_data, dict):
        request_data.pop("data", None)
        request_data.pop("cookies", None)
        request_data.pop("query_string", None)
        request_data["headers"] = FILTERED
        request_data["env"] = FILTERED

    exception = sanitized.get("exception")
    if isinstance(exception, dict):
        for value in exception.get("values", []):
            if isinstance(value, dict):
                value["value"] = "Internal exception details redacted."

    return sanitized


def configure_monitoring(config: Settings = settings) -> bool:
    """Initialize optional hosted monitoring without collecting PII."""
    if not config.SENTRY_DSN:
        return False

    sentry_sdk.init(
        dsn=config.SENTRY_DSN,
        default_integrations=False,
        environment=config.ENVIRONMENT,
        release=f"polaris@{config.VERSION}",
        send_default_pii=False,
        include_local_variables=False,
        max_request_body_size="never",
        traces_sample_rate=0.0,
        profiles_sample_rate=0.0,
        before_send=scrub_monitoring_event,
    )
    return True


def capture_request_exception(
    error: Exception,
    *,
    request_id: str,
    method: str,
    path: str,
) -> None:
    """Capture a scrubbed failure with only safe request identifiers."""
    if not settings.SENTRY_DSN:
        return

    with sentry_sdk.isolation_scope() as scope:
        scope.set_tag("polaris.request_id", request_id)
        scope.set_tag("http.request.method", method)
        scope.set_context(
            "polaris_request",
            {
                "request_id": request_id,
                "method": method,
                "path": path,
            },
        )
        sentry_sdk.capture_exception(error)
