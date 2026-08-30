import json

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.build_info import build_info
from app.main import live_health
from app.main import ready_health


class AvailableDatabase:
    def __init__(self):
        self.statements = []

    def execute(self, statement):
        self.statements.append(str(statement))
        return statement


class UnavailableDatabase:
    def execute(self, statement):
        raise SQLAlchemyError("database unavailable")


def test_liveness_reports_the_running_release():
    payload = live_health()

    assert payload["status"] == "alive"
    assert payload["version"] == settings.VERSION
    assert payload["build"]["source"] in {"local", "render"}
    assert payload["build"]["short_commit"]


def test_readiness_passes_when_database_is_reachable():
    payload = ready_health(AvailableDatabase())

    assert payload["status"] == "ready"
    assert payload["version"] == settings.VERSION
    assert payload["build"]["source"] in {"local", "render"}
    assert payload["build"]["short_commit"]


def test_production_readiness_checks_hosted_observatory_schema(monkeypatch):
    database = AvailableDatabase()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    payload = ready_health(database)

    assert payload["status"] == "ready"
    assert payload["version"] == settings.VERSION
    assert payload["build"]["source"] in {"local", "render"}
    assert database.statements == [
        "SELECT 1",
        "SELECT rig_profile_key FROM observatories LIMIT 1",
    ]


def test_readiness_fails_without_disclosing_database_details():
    response = ready_health(UnavailableDatabase())

    assert response.status_code == 503
    assert json.loads(response.body) == {
        "status": "not_ready",
        "version": settings.VERSION,
        "build": build_info(settings.BASE_DIR),
    }
    assert b"database unavailable" not in response.body


def test_build_info_uses_render_runtime_metadata(monkeypatch):
    monkeypatch.setenv(
        "RENDER_GIT_COMMIT",
        "abcdef1234567890abcdef1234567890abcdef12",
    )
    monkeypatch.setenv("RENDER_GIT_BRANCH", "develop")

    assert build_info(settings.BASE_DIR) == {
        "source": "render",
        "commit": "abcdef1234567890abcdef1234567890abcdef12",
        "short_commit": "abcdef1",
        "branch": "develop",
    }
