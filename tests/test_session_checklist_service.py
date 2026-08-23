from app.services.session_checklist_service import build_session_checklist


TIMEZONE = "America/Phoenix"
DEFAULT_TARGET = object()


def _block(**overrides):
    block = {
        "object": "M31",
        "start": "2026-08-23 09:00 PM",
        "end": "2026-08-24 01:00 AM",
        "setup_minutes": 5,
        "recommended_filter": "Duo-Band",
    }
    block.update(overrides)
    return block


def _schedule(decision="Proceed", blocks=None):
    return {
        "date": "2026-08-23",
        "decision": decision,
        "blocks": [_block()] if blocks is None else blocks,
    }


def _target(**overrides):
    target = {
        "object": "M31",
        "recommended_start": "2026-08-23 09:00 PM",
        "recommended_end": "2026-08-24 01:00 AM",
        "recommended_settings": {"filter_name": "Duo-Band"},
    }
    target.update(overrides)
    return target


def _checklist(
    *,
    schedule=None,
    recommended_target=DEFAULT_TARGET,
    backup_target=None,
    dew_level="low",
    dew_action="No special dew action is indicated.",
    eq=False,
):
    return build_session_checklist(
        schedule=schedule or _schedule(),
        recommended_target=(
            _target()
            if recommended_target is DEFAULT_TARGET
            else recommended_target
        ),
        backup_target=backup_target,
        dew_risk={"level": dew_level, "action": dew_action},
        timezone_name=TIMEZONE,
        equatorial_mode_enabled=eq,
    )


def test_good_night_uses_real_setup_start_and_stop_times():
    result = _checklist(eq=True)

    assert result["status"] == "ready"
    assert [step["time_label"] for step in result["steps"]] == [
        "9:00 PM",
        "9:05 PM",
        "1:00 AM next day",
    ]
    assert result["steps"][1]["instruction"] == (
        "Begin imaging M31 after setup is complete."
    )
    assert result["actions"] == [
        "Use EQ tracking mode tonight.",
        "Use the Duo-Band filter recommended for tonight's target.",
    ]


def test_caution_night_prioritizes_recheck_and_dew_action():
    dew_action = "Use dew control from the start and check for condensation."
    result = _checklist(
        schedule=_schedule(decision="Use Caution"),
        dew_level="high",
        dew_action=dew_action,
        eq=True,
    )

    assert result["status"] == "caution"
    assert "recheck live conditions" in result["summary"].lower()
    assert result["actions"] == [
        "Recheck live conditions before starting imaging.",
        dew_action,
    ]
    assert len(result["actions"]) == 2


def test_unsuitable_night_waits_and_uses_only_verified_reassess_time():
    schedule = _schedule(decision="Do Not Image", blocks=[])
    result = _checklist(
        schedule=schedule,
        recommended_target=None,
        backup_target=_target(),
    )

    assert result["status"] == "wait"
    assert [step["label"] for step in result["steps"]] == [
        "Set up",
        "Reassess",
        "Stop",
    ]
    assert result["steps"][0]["at"] is None
    assert result["steps"][1]["time_label"] == "9:00 PM"
    assert "image only if Polaris changes" in result["steps"][1]["instruction"]
    assert result["steps"][2]["at"] is None
    assert result["actions"] == [
        "Wait and reassess; do not begin imaging while this recommendation remains in effect."
    ]


def test_no_target_and_no_blocks_does_not_create_session_timing():
    result = _checklist(
        schedule=_schedule(blocks=[]),
        recommended_target=None,
        backup_target=None,
    )

    assert result["status"] == "unavailable"
    assert all(step["at"] is None for step in result["steps"])
    assert all(step["time_label"] is None for step in result["steps"])
    assert result["actions"] == [
        "Refresh the plan before committing to setup."
    ]


def test_missing_schedule_fields_are_reported_as_unavailable():
    result = _checklist(
        schedule=_schedule(
            blocks=[_block(start=None, setup_minutes=None)]
        )
    )

    assert result["status"] == "unavailable"
    assert result["steps"][0]["instruction"] == "Setup time is unavailable."
    assert result["steps"][1]["instruction"] == "Start time is unavailable."
    assert result["steps"][2]["instruction"] == "Stop time is unavailable."


def test_setup_minutes_crossing_midnight_gets_next_day_label():
    result = _checklist(
        schedule=_schedule(
            blocks=[
                _block(
                    start="2026-08-23 11:58 PM",
                    end="2026-08-24 02:00 AM",
                    setup_minutes=7,
                )
            ]
        )
    )

    assert [step["time_label"] for step in result["steps"]] == [
        "11:58 PM",
        "12:05 AM next day",
        "2:00 AM next day",
    ]
    assert result["steps"][1]["at"] == "2026-08-24 12:05 AM"
