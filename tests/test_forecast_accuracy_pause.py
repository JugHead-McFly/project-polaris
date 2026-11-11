"""Retirement boundaries using synthetic, account-owned in-memory evidence."""
import builtins
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, select
from sqlalchemy.engine import Engine

from app.core.config import settings
from app.database.database import get_db
from app.models import (
    ForecastAccuracySnapshot, HostedCaptureSession, HostedObservatory,
    LegacyCapture, NightlyForecast, RecommendationRun,
)
from app.services.forecast_accuracy_service import unavailable_forecast_accuracy_summary
from app.services import planner_service
from import_plan_fixture import ALICE, BOB, workflow


ARCHIVES = (ForecastAccuracySnapshot, NightlyForecast, HostedCaptureSession, LegacyCapture)


@contextmanager
def session_for(flow):
    provider = flow.app.dependency_overrides[get_db]()
    try:
        yield next(provider)
    finally:
        provider.close()


def seed_archive(flow):
    # Older than the existing 90-day retention cutoff, so an accidental call to
    # tracking would both query history and remove this evidence.
    stamp = datetime.now(timezone.utc) - timedelta(days=200)
    with session_for(flow) as db:
        for owner, digest, seconds in ((ALICE, "c", 900), (BOB, "d", 1800)):
            home = db.scalar(select(HostedObservatory).where(HostedObservatory.user_id == owner))
            db.add(ForecastAccuracySnapshot(user_id=owner, observatory_id=home.id,
                forecast_for=stamp, forecast_created_at=stamp-timedelta(hours=6),
                forecast_lead_hour=6, expires_at=stamp+timedelta(hours=2),
                status="matched", created_at=stamp, observed_at=stamp,
                forecast_cloud_cover_percent=12, observed_cloud_cover_percent=12,
                satellite_cloud_observation={"status": "usable", "retained_evidence": digest * 1000}))
            db.add(NightlyForecast(user_id=owner, observatory_id=home.id,
                night_date=stamp.date(), window_start=stamp, window_end=stamp+timedelta(hours=8),
                latitude=home.latitude, longitude=home.longitude, timezone_name=home.timezone_name,
                forecasts={"afternoon": {"status": "saved", "average": 12,
                    "source_mix": ["synthetic"], "method": "dark-window-v1"}},
                observation={"complete": True, "adequate": True, "average": 12,
                    "method": "dark-window-v1", "cells": [{"retained_evidence": digest * 1000}]}))
            db.add(HostedCaptureSession(user_id=owner, source_key=digest * 64,
                target="M27", session_name="Archived synthetic capture", captured_at=stamp,
                filter_name="Astro", frame_count=30, integration_seconds=seconds, evidence_hash=digest * 64))
            db.add(LegacyCapture(user_id=owner, source_key=digest * 64, target="M27",
                original_observation_time="unverified", reported_integration_seconds=999999,
                evidence_hash=digest * 64, review_flags=["retained"]))
        db.commit()


def archive_snapshot(flow):
    with session_for(flow) as db:
        values = {model.__tablename__: [dict(row) for row in db.execute(
            select(model.__table__).order_by(*model.__table__.primary_key.columns)).mappings()]
            for model in ARCHIVES}
    return json.dumps(values, default=str, sort_keys=True)


def core(payload):
    return {key: value for key, value in payload.items()
            if key not in {"forecast_accuracy", "recommendation_run_id"}}


def test_repeated_tonight_requests_preserve_archives_and_core_plans_without_accuracy_work(monkeypatch):
    monkeypatch.setattr(settings, "FORECAST_ACCURACY_ENABLED", False)
    statements = []
    def record(_conn, _cursor, statement, _params, _context, _many):
        statements.append(statement.lower())
    with workflow() as flow, TestClient(flow.app) as client:
        seed_archive(flow)
        before = archive_snapshot(flow)
        event.listen(Engine, "before_cursor_execute", record)
        try:
            with (
                patch("app.api.tonight.forecast_accuracy_summary", side_effect=AssertionError("Accuracy scan")),
                patch("app.api.tonight.track_forecast_accuracy", side_effect=AssertionError("Accuracy tracking/retention")),
                patch("app.services.satellite_cloud_service.fetch_reference", side_effect=AssertionError("Satellite download")),
                patch("app.services.planner_service.get_weather_summary",
                      wraps=planner_service.get_weather_summary) as weather,
            ):
                payloads = []
                for method in ("get", "post", "get", "post"):
                    response = getattr(client, method)("/tonight?equatorial_mode_enabled=true")
                    assert response.status_code == 200, response.text
                    payload = response.json()
                    assert payload["forecast_accuracy"]["state"] == "paused"
                    assert payload["recommended_target"]["object"] == "M27"
                    assert payload["recommended_target"]["synced_capture_history"]["total_integration_seconds"] == 900
                    assert payload["schedule"]["blocks"] and payload["weather"]["status"] == "Synthetic clear forecast"
                    if method == "post":
                        assert payload["recommendation_run_id"]
                    payloads.append(payload)
                assert weather.call_count == 4
                assert all(core(payload) == core(payloads[0]) for payload in payloads)
            # Changing the switch cannot change the weather/target decision.
            monkeypatch.setattr(settings, "FORECAST_ACCURACY_ENABLED", True)
            with patch("app.api.tonight.forecast_accuracy_summary", return_value=unavailable_forecast_accuracy_summary()):
                enabled = flow.plan(client)
            assert core(enabled) == core(payloads[0])
        finally:
            event.remove(Engine, "before_cursor_execute", record)
        assert not any(table in sql for sql in statements
                       for table in ("forecast_accuracy_snapshots", "nightly_forecasts"))
        assert archive_snapshot(flow) == before
        with session_for(flow) as db:
            assert len(db.scalars(select(RecommendationRun)).all()) == 2


def test_opt_in_reads_existing_history_and_return_to_pause_leaves_it_intact(monkeypatch):
    with workflow() as flow, TestClient(flow.app) as client:
        seed_archive(flow)
        before = archive_snapshot(flow)
        monkeypatch.setattr(settings, "FORECAST_ACCURACY_ENABLED", True)
        enabled = flow.plan(client)
        assert enabled["forecast_accuracy"]["matched_samples"] == 1
        assert enabled["forecast_accuracy"]["nightly"]["completed_nights"] == 1
        monkeypatch.setattr(settings, "FORECAST_ACCURACY_ENABLED", False)
        assert flow.plan(client)["forecast_accuracy"]["state"] == "paused"
        assert archive_snapshot(flow) == before


@pytest.mark.parametrize("minute", [0, 15, 19, 20, 55])
def test_scheduled_pause_is_successful_no_op_even_at_hourly_boundary(monkeypatch, capsys, minute):
    from scripts import collect_forecast_accuracy as cli
    monkeypatch.setattr(settings, "FORECAST_ACCURACY_ENABLED", False)
    monkeypatch.setenv(cli.USER_IDS_ENV, "invalid-and-must-not-be-parsed")
    monkeypatch.setattr(cli, "datetime", SimpleNamespace(now=lambda *a: datetime(2026, 11, 3, 12, minute, tzinfo=timezone.utc)))
    original_import = builtins.__import__
    def guarded_import(name, *args, **kwargs):
        assert not name.startswith(("app.services", "app.database")), "Paused cron imported collection/database code"
        return original_import(name, *args, **kwargs)
    with patch("builtins.__import__", side_effect=guarded_import):
        cli.main()
    assert json.loads(capsys.readouterr().out) == {"status": "paused", "collection_enabled": False}


def test_fresh_cron_process_needs_no_database_or_providers_while_paused():
    command = """
import importlib.abc, runpy, sys
class BlockCollection(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('app.database', 'app.services')):
            raise AssertionError('Paused cron loaded ' + fullname)
sys.meta_path.insert(0, BlockCollection())
runpy.run_path('scripts/collect_forecast_accuracy.py', run_name='__main__')
"""
    environment = {**os.environ, "POLARIS_ENVIRONMENT": "test", "POLARIS_AUTH_MODE": "local",
                   "POLARIS_DATABASE_URL": "sqlite://", "POLARIS_FORECAST_ACCURACY_ENABLED": "false",
                   "POLARIS_FORECAST_ACCURACY_USER_IDS": "invalid-and-unused"}
    result = subprocess.run([sys.executable, "-c", command], cwd=Path(__file__).resolve().parents[1],
                            env=environment, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"status": "paused", "collection_enabled": False}


def test_opt_in_restores_nightly_and_hourly_collection_entrypoints(monkeypatch, capsys):
    from scripts import collect_forecast_accuracy as cli
    from app.database import database
    from app.services import forecast_accuracy_collection_service as hourly
    from app.services import nightly_forecast_service as nightly
    from test_forecast_accuracy_collection_service import _session_factory, ALICE_ID
    monkeypatch.setattr(settings, "FORECAST_ACCURACY_ENABLED", True)
    monkeypatch.setenv(cli.USER_IDS_ENV, str(ALICE_ID))
    monkeypatch.setattr(database, "SessionLocal", _session_factory())
    monkeypatch.setattr(cli, "datetime", SimpleNamespace(now=lambda *a: datetime(2026, 11, 3, 12, 15, tzinfo=timezone.utc)))
    calls = []
    monkeypatch.setattr(nightly, "collect_nightly", lambda db, **kw: calls.append(("nightly", kw["user_id"])) or {})
    monkeypatch.setattr(hourly, "collect_forecast_accuracy", lambda owners: calls.append(("hourly", tuple(owners))) or {"failed_tenants": 0})
    cli.main()
    assert calls == [("nightly", ALICE_ID), ("hourly", (ALICE_ID,))]
    assert json.loads(capsys.readouterr().out)["failed_tenants"] == 0
