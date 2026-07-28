from unittest.mock import patch

from app.core.config import Settings
from app.core.monitoring import REDACTED_EXCEPTION
from app.core.monitoring import capture_monitoring_smoke_test
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
            "polaris_request": {
                "request_id": "abc123",
                "method": "POST",
                "path": "/observatories/private-id",
            },
        },
        "tags": {
            "polaris.request_id": "abc123",
            "http.request.method": "POST",
            "server_name": "Doug-MacBook-Air.local",
        },
        "exception": {
            "values": [
                {
                    "type": "DatabaseError",
                    "value": "parameters included exact coordinates",
                    "stacktrace": {
                        "frames": [
                            {
                                "filename": (
                                    "/Users/doug/dougs-observatory/"
                                    "app/service.py"
                                ),
                                "lineno": 10,
                                "function": "save_observatory",
                                "vars": {"exact_address": "private"},
                                "context_line": "save(private_address)",
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
            "unlabeled_personal_note": "Doug lives in Mesa",
        },
        "message": "observer@example.com failed at 33.25,-111.75",
    }

    sanitized = scrub_monitoring_event(event, {})

    assert "user" not in sanitized
    assert "breadcrumbs" not in sanitized
    assert "server_name" not in sanitized
    assert sanitized["contexts"] == {
        "polaris_request": {"request_id": "abc123", "method": "POST"}
    }
    assert "request" not in sanitized
    assert "extra" not in sanitized
    assert "message" not in sanitized
    assert sanitized["tags"] == {
        "polaris.request_id": "abc123",
        "http.request.method": "POST",
    }
    assert sanitized["exception"]["values"][0]["value"] == (
        REDACTED_EXCEPTION
    )
    frame = sanitized["exception"]["values"][0]["stacktrace"]["frames"][0]
    assert frame == {
        "filename": "app/service.py",
        "lineno": 10,
        "function": "save_observatory",
    }


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
        environment="production",
        database_url="postgresql://user:pass@db.example/polaris",
        auth_mode="supabase",
        supabase_url="https://example.supabase.co",
        supabase_publishable_key="sb_publishable_test",
        sentry_dsn="https://public@example.ingest.sentry.io/1",
        sentry_allow_transmission=True,
    )

    with patch("app.core.monitoring.sentry_sdk.init") as initialize:
        enabled = configure_monitoring(config)

    assert enabled
    options = initialize.call_args.kwargs
    assert not options["default_integrations"]
    assert options["server_name"] == ""
    assert not options["send_default_pii"]
    assert not options["include_local_variables"]
    assert not options["include_source_context"]
    assert options["max_request_body_size"] == "never"
    assert options["traces_sample_rate"] == 0.0
    assert options["profiles_sample_rate"] == 0.0
    assert options["before_send"] is scrub_monitoring_event


def test_monitoring_stays_disabled_outside_production(tmp_path):
    config = Settings(
        base_dir=tmp_path,
        environment="staging",
        database_url="postgresql://user:pass@db.example/polaris",
        auth_mode="supabase",
        supabase_url="https://example.supabase.co",
        supabase_publishable_key="sb_publishable_test",
        sentry_dsn="https://public@example.ingest.sentry.io/1",
        sentry_allow_transmission=True,
    )

    with patch("app.core.monitoring.sentry_sdk.init") as initialize:
        enabled = configure_monitoring(config)

    assert not enabled
    initialize.assert_not_called()


def test_monitoring_requires_explicit_transmission_approval(tmp_path):
    config = Settings(
        base_dir=tmp_path,
        environment="production",
        database_url="postgresql://user:pass@db.example/polaris",
        auth_mode="supabase",
        supabase_url="https://example.supabase.co",
        supabase_publishable_key="sb_publishable_test",
        sentry_dsn="https://public@example.ingest.sentry.io/1",
    )

    with patch("app.core.monitoring.sentry_sdk.init") as initialize:
        enabled = configure_monitoring(config)

    assert not enabled
    initialize.assert_not_called()


def test_monitoring_smoke_test_uses_only_safe_context(tmp_path):
    config = Settings(
        base_dir=tmp_path,
        environment="production",
        database_url="postgresql://user:pass@db.example/polaris",
        auth_mode="supabase",
        supabase_url="https://example.supabase.co",
        supabase_publishable_key="sb_publishable_test",
        sentry_dsn="https://public@example.ingest.sentry.io/1",
        sentry_allow_transmission=True,
    )

    with (
        patch("app.core.monitoring.sentry_sdk.init"),
        patch(
            "app.core.monitoring.sentry_sdk.isolation_scope"
        ) as isolation_scope,
        patch(
            "app.core.monitoring.sentry_sdk.capture_exception"
        ) as capture_exception,
        patch("app.core.monitoring.sentry_sdk.flush") as flush,
    ):
        configure_monitoring(config)
        capture_monitoring_smoke_test("private-alpha-smoke")

    scope = isolation_scope.return_value.__enter__.return_value
    scope.set_tag.assert_any_call(
        "polaris.request_id",
        "private-alpha-smoke",
    )
    scope.set_tag.assert_any_call("http.request.method", "STARTUP")
    scope.set_context.assert_called_once_with(
        "polaris_request",
        {
            "request_id": "private-alpha-smoke",
            "method": "STARTUP",
        },
    )
    capture_exception.assert_called_once()
    flush.assert_called_once_with(timeout=5.0)
