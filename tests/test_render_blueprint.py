from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_render_blueprint_keeps_the_private_alpha_free_and_deliberate():
    blueprint = yaml.safe_load(
        (PROJECT_ROOT / "render.yaml").read_text()
    )
    service = blueprint["services"][0]

    assert service["type"] == "web"
    assert service["runtime"] == "python"
    assert service["plan"] == "free"
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
