from unittest.mock import patch

from app.core.config import Settings
from app.core.monitoring import FILTERED
from app.core.monitoring import configure_monitoring
from app.core.monitoring import scrub_monitoring_event


def test_monitoring_event_removes_personal_and_credential_data():
    event = {
        "user": {
            "email": "observer@example.com",
            "ip_address": "192.0.2.1",
        },
        "request": {
            "data": {
                "latitude": 33.25,
                "longitude": -111.75,
            },
            "cookies": {"session": "private"},
            "query_string": "token=private",
            "headers": {
                "Authorization": "Bearer private",
                "Cookie": "session=private",
            },
            "env": {"REMOTE_ADDR": "192.0.2.1"},
            "method": "POST",
            "url": "https://polaris.example/observatories",
        },
        "breadcrumbs": {
            "values": [
                {"message": "database parameters may be present"},
            ]
        },
        "server_name": "Doug-MacBook-Air.local",
        "contexts": {
            "runtime": {"name": "CPython"},
            "user": {"geo": {"city": "Mesa"}},
            "polaris_request": {"request_id": "abc123", "method": "POST"},
        },
        "exception": {
            "values": [
                {
                    "type": "DatabaseError",
                    "value": "parameters included exact coordinates",
                    "stacktrace": {
                        "frames": [
                            {
                                "filename": "app/service.py",
                                "lineno": 10,
                            }
                        ]
                    },
                }
            ]
        },
        "extra": {
            "access_token": "private",
            "observatory_address": "private",
            "safe_request_id": "abc123",
        },
    }

    sanitized = scrub_monitoring_event(event, {})

    assert "user" not in sanitized
    assert "breadcrumbs" not in sanitized
    assert "server_name" not in sanitized
    assert sanitized["contexts"] == {
        "polaris_request": {"request_id": "abc123", "method": "POST"}
    }
    assert "data" not in sanitized["request"]
    assert "cookies" not in sanitized["request"]
    assert "query_string" not in sanitized["request"]
    assert sanitized["request"]["headers"] == FILTERED
    assert sanitized["request"]["env"] == FILTERED
    assert sanitized["extra"]["access_token"] == FILTERED
    assert sanitized["extra"]["observatory_address"] == FILTERED
    assert sanitized["extra"]["safe_request_id"] == "abc123"
    assert sanitized["exception"]["values"][0]["value"] == (
        "Internal exception details redacted."
    )
    assert (
        sanitized["exception"]["values"][0]["stacktrace"]["frames"][0][
            "filename"
        ]
        == "app/service.py"
    )


def test_monitoring_stays_disabled_without_a_dsn(tmp_path):
    config = Settings(
        base_dir=tmp_path,
        environment="test",
        sentry_dsn="",
    )

    with patch("app.core.monitoring.sentry_sdk.init") as initialize:
        enabled = configure_monitoring(config)

    assert not enabled
    initialize.assert_not_called()


def test_monitoring_uses_privacy_safe_defaults(tmp_path):
    config = Settings(
        base_dir=tmp_path,
        environment="staging",
        database_url="postgresql://user:pass@db.example/polaris",
        auth_mode="supabase",
        supabase_url="https://example.supabase.co",
        supabase_publishable_key="sb_publishable_test",
        sentry_dsn="https://public@example.ingest.sentry.io/1",
    )

    with patch("app.core.monitoring.sentry_sdk.init") as initialize:
        enabled = configure_monitoring(config)

    assert enabled
    options = initialize.call_args.kwargs
    assert not options["default_integrations"]
    assert options["server_name"] == ""
    assert not options["send_default_pii"]
    assert not options["include_local_variables"]
    assert options["max_request_body_size"] == "never"
    assert options["traces_sample_rate"] == 0.0
    assert options["profiles_sample_rate"] == 0.0
    assert options["before_send"] is scrub_monitoring_event
