import json

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
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
    assert live_health() == {
        "status": "alive",
        "version": settings.VERSION,
    }


def test_readiness_passes_when_database_is_reachable():
    assert ready_health(AvailableDatabase()) == {
        "status": "ready",
        "version": settings.VERSION,
    }


def test_production_readiness_checks_hosted_observatory_schema(monkeypatch):
    database = AvailableDatabase()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    assert ready_health(database) == {
        "status": "ready",
        "version": settings.VERSION,
    }
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
    }
    assert b"database unavailable" not in response.body
