from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_render_blueprint_preserves_approved_web_plan_and_deploy_constraints():
    blueprint = yaml.safe_load(
        (PROJECT_ROOT / "render.yaml").read_text()
    )
    service = blueprint["services"][0]

    assert service["type"] == "web"
    assert service["runtime"] == "python"
    # d75336de aligned the Blueprint with the approved compute trial.
    assert service["plan"] == "0.5c-512mb"
    assert service["branch"] == "develop"
    assert service["autoDeployTrigger"] == "commit"
    assert service["healthCheckPath"] == "/health/ready"
    assert "$PORT" in service["startCommand"]
    assert "preDeployCommand" not in service


def test_render_blueprint_prompts_for_secrets_instead_of_storing_them():
    blueprint = yaml.safe_load(
        (PROJECT_ROOT / "render.yaml").read_text()
    )
    environment = {
        item["key"]: item
        for item in blueprint["services"][0]["envVars"]
    }

    for secret_name in (
        "POLARIS_DATABASE_URL",
        "POLARIS_SUPABASE_URL",
        "POLARIS_SUPABASE_PUBLISHABLE_KEY",
    ):
        assert environment[secret_name] == {
            "key": secret_name,
            "sync": False,
        }

    assert environment["POLARIS_ENVIRONMENT"]["value"] == "production"
    assert (
        environment["POLARIS_SENTRY_ALLOW_TRANSMISSION"]["value"]
        == "false"
    )


def test_render_blueprint_schedules_nightly_snapshot_checks_every_five_minutes():
    blueprint = yaml.safe_load(
        (PROJECT_ROOT / "render.yaml").read_text()
    )
    services = {
        service["name"]: service
        for service in blueprint["services"]
    }
    cron = services["project-polaris-forecast-accuracy"]

    assert cron["type"] == "cron"
    assert cron["runtime"] == "python"
    assert cron["plan"] == "0.5c-512mb"
    assert cron["branch"] == "develop"
    assert cron["autoDeployTrigger"] == "commit"
    assert cron["schedule"] == "*/5 * * * *"
    assert cron["startCommand"] == (
        "python scripts/collect_forecast_accuracy.py"
    )

    environment = {item["key"]: item for item in cron["envVars"]}
    assert environment["POLARIS_FORECAST_ACCURACY_USER_IDS"] == {
        "key": "POLARIS_FORECAST_ACCURACY_USER_IDS",
        "sync": False,
    }
    for secret_name in (
        "POLARIS_DATABASE_URL",
        "POLARIS_SUPABASE_URL",
        "POLARIS_SUPABASE_PUBLISHABLE_KEY",
    ):
        assert environment[secret_name]["fromService"] == {
            "type": "web",
            "name": "project-polaris-private-alpha",
            "envVarKey": secret_name,
        }


def test_web_and_cron_release_configuration_keep_accuracy_paused():
    blueprint = yaml.safe_load((PROJECT_ROOT / "render.yaml").read_text())
    for service in blueprint["services"]:
        environment = {item["key"]: item for item in service["envVars"]}
        assert environment["POLARIS_FORECAST_ACCURACY_ENABLED"] == {
            "key": "POLARIS_FORECAST_ACCURACY_ENABLED", "value": "false"}
