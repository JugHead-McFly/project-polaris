import json

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.main import live_health
from app.main import ready_health


class AvailableDatabase:
    def execute(self, statement):
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


def test_readiness_fails_without_disclosing_database_details():
    response = ready_health(UnavailableDatabase())

    assert response.status_code == 503
    assert json.loads(response.body) == {
        "status": "not_ready",
        "version": settings.VERSION,
    }
    assert b"database unavailable" not in response.body
