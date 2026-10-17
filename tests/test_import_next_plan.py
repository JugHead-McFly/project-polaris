"""Joined v1.12 regression: a capture changes the next plan, not its quality."""
from datetime import datetime

from fastapi.testclient import TestClient
import pytest

from import_plan_fixture import ALICE, BOB, START, END, workflow, manifest


@pytest.fixture
def scenario():
    with workflow() as flow, TestClient(flow.app) as client:
        yield flow, client


def test_import_updates_next_plan_and_reimport_is_idempotent(scenario):
    flow, client = scenario
    before = flow.plan(client)
    assert before["recommended_target"]["object"] == "M27"
    assert flow.sync(client, manifest(3)).json()["sessions_changed"] == 1
    after = flow.plan(client)
    target = after["recommended_target"]
    assert target["object"] == "M27"
    assert target["total_integration_seconds"] == 10800
    assert target["total_integration_hours"] == 3
    assert target["remaining_hours"] == 2
    assert target["session_count"] == 1
    assert target["best_quality"] is None
    assert after["capture_history"]["session_count"] == 1
    assert flow.sync(client, manifest(3)).json()["sessions_changed"] == 0
    again = flow.plan(client)
    assert again["recommended_target"] == target
    assert again["schedule"] == after["schedule"]
    assert again["capture_history"]["targets"] == after["capture_history"]["targets"]


def test_completed_goal_changes_ranking_without_inventing_quality(scenario):
    flow, client = scenario
    original = flow.plan(client)
    flow.sync(client, manifest(3))
    flow.sync(client, manifest(2, "second"))
    after = flow.plan(client)
    assert original["recommended_target"]["object"] == "M27"
    assert after["recommended_target"]["object"] == "M57"
    completed = after["backup_target"]
    assert completed["object"] == "M27"
    assert completed["remaining_hours"] == 0
    assert completed["session_count"] == 2
    assert completed["total_integration_hours"] == 5
    assert "reached" in completed["reason"].lower()
    assert completed["best_quality"] is None
    assert after["recommended_target"]["best_quality"] is None
    assert all(b["object"] != "M27" for b in after["schedule"]["blocks"])


def test_schedule_allocates_remaining_goals_and_explains_end(scenario):
    flow, client = scenario
    flow.sync(client, manifest(3))
    flow.sync(client, manifest(3, "other-target", "M57"))
    plan = flow.plan(client)
    schedule = plan["schedule"]
    blocks = schedule["blocks"]
    assert {b["object"] for b in blocks} == {"M27", "M57"}
    for name, remaining in (("M27", 120), ("M57", 60)):
        selected = [b for b in blocks if b["object"] == name]
        assert sum(b["imaging_minutes"] for b in selected) == remaining
        assert sum(b["planned_subframes"] * b["recommended_sub_exposure_seconds"] for b in selected) <= remaining * 60
    for block in blocks:
        start = datetime.strptime(block["start"], "%Y-%m-%d %I:%M %p").replace(tzinfo=START.tzinfo)
        end = datetime.strptime(block["end"], "%Y-%m-%d %I:%M %p").replace(tzinfo=START.tzinfo)
        assert START <= start < end <= END
        assert (end - start).total_seconds() == block["duration_minutes"] * 60
        assert block["duration_minutes"] == block["setup_minutes"] + block["imaging_minutes"]
    for previous, following in zip(blocks, blocks[1:]):
        assert datetime.strptime(previous["end"], "%Y-%m-%d %I:%M %p") <= datetime.strptime(following["start"], "%Y-%m-%d %I:%M %p")
    assert "integration goal is allocated" in schedule["end_reason"]
    assert "not a weather cutoff" in schedule["end_reason"]
    assert schedule["unscheduled_dark_minutes"] > 0
    assert plan["session_checklist"]["steps"][-1]["at"] == blocks[-1]["end"]


def test_other_account_does_not_inherit_sessions_or_changed_ranking(scenario):
    flow, client = scenario
    before = flow.plan(client, BOB)
    flow.sync(client, manifest(5))
    assert flow.plan(client)["recommended_target"]["object"] == "M57"
    after = flow.plan(client, BOB)
    assert after["recommended_target"] == before["recommended_target"]
    assert after["capture_history"]["session_count"] == 0
    assert after["recommended_target"]["total_integration_seconds"] == 0
    assert flow.sync(client, manifest(5), user=BOB, token_owner=ALICE).status_code == 401
    assert client.get("/capture-history", headers={"X-Test-User": str(BOB)}).json()["targets"] == []


@pytest.mark.parametrize("first,second", [(ALICE, BOB), (BOB, ALICE)])
def test_accounts_can_share_source_identifier_without_mixing_history(scenario, first, second):
    flow, client = scenario
    payloads = {ALICE: manifest(5, "shared-source"), BOB: manifest(1, "shared-source")}
    assert payloads[ALICE]["sessions"][0]["source_key"] == payloads[BOB]["sessions"][0]["source_key"]

    def saved_history(owner):
        response = client.get("/capture-history", headers={"X-Test-User": str(owner)})
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["session_count"] == 1
        assert len(data["targets"]) == 1
        assert data["targets"][0]["object"] == "M27"
        return data["targets"]

    for owner in (first, second):
        response = flow.sync(client, payloads[owner], user=owner)
        assert response.status_code == 200, response.text
        assert response.json() == {"sessions_received": 1, "sessions_changed": 1}

    alice_history, bob_history = saved_history(ALICE), saved_history(BOB)
    assert alice_history[0]["seconds"] == 18000
    assert bob_history[0]["seconds"] == 3600
    assert flow.plan(client, ALICE)["recommended_target"]["object"] == "M57"
    assert flow.plan(client, BOB)["recommended_target"]["object"] == "M27"

    for owner in (ALICE, BOB):
        response = flow.sync(client, payloads[owner], user=owner)
        assert response.status_code == 200, response.text
        assert response.json()["sessions_changed"] == 0
    assert saved_history(ALICE) == alice_history
    assert saved_history(BOB) == bob_history

    # Replace Bob's interpretation for the same source, then Alice's. Neither
    # upsert may overwrite the other owner's row or influence their next plan.
    alice_plan = flow.plan(client, ALICE)
    response = flow.sync(client, manifest(2, "shared-source"), user=BOB)
    assert response.status_code == 200, response.text
    assert response.json()["sessions_changed"] == 1
    assert saved_history(BOB)[0]["seconds"] == 7200
    assert saved_history(ALICE) == alice_history
    assert flow.plan(client, ALICE)["recommended_target"] == alice_plan["recommended_target"]
    bob_plan, bob_history = flow.plan(client, BOB), saved_history(BOB)
    response = flow.sync(client, manifest(4, "shared-source"), user=ALICE)
    assert response.status_code == 200, response.text
    assert response.json()["sessions_changed"] == 1
    assert saved_history(ALICE)[0]["seconds"] == 14400
    assert saved_history(BOB) == bob_history
    assert flow.plan(client, BOB)["recommended_target"] == bob_plan["recommended_target"]
