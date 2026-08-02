#!/usr/bin/env python3
"""Print a privacy-safe aggregate health report for the private alpha."""

import argparse
import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_env_file(path: Path, environ=os.environ) -> None:
    """Load simple KEY=VALUE lines before app settings are imported."""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in environ:
            environ[key] = value


def _format_rate(value) -> str:
    return "not enough data" if value is None else f"{value}%"


def render_text_report(report: dict) -> str:
    accounts = report["accounts"]
    activation = report["activation"]
    recommendations = report["recommendations"]
    feedback = report["feedback"]
    focus = report["review_focus"]

    lines = [
        "Project Polaris private-alpha review",
        "",
        f"Review focus: {focus['priority']}",
        f"Why: {focus['reason']}",
        "",
        "Accounts",
        f"- Profiles created: {accounts['profiles_created']}",
        f"- With observing home: {accounts['with_observing_home']}",
        f"- With saved plan: {accounts['with_saved_plan']}",
        (
            "- Returning for 2+ planned nights: "
            f"{accounts['returning_for_two_or_more_nights']}"
        ),
        "",
        "Activation",
        (
            "- Observing-home setup rate: "
            f"{_format_rate(activation['observing_home_rate_percent'])}"
        ),
        (
            "- First-plan rate: "
            f"{_format_rate(activation['first_plan_rate_percent'])}"
        ),
        (
            "- Second-night return rate: "
            f"{_format_rate(activation['returning_planner_rate_percent'])}"
        ),
        "",
        "Recommendations",
        f"- Saved plans: {recommendations['saved']}",
        (
            "- Outcomes: "
            + (
                ", ".join(
                    f"{outcome}={count}"
                    for outcome, count in recommendations["by_outcome"].items()
                )
                if recommendations["by_outcome"]
                else "none yet"
            )
        ),
        "",
        "Feedback",
        f"- Responses: {feedback['responses']}",
        f"- Useful: {feedback['useful']}",
        f"- Not useful: {feedback['not_useful']}",
        f"- Response rate: {_format_rate(feedback['response_rate_percent'])}",
        "",
        "Privacy: aggregate counts only; no names, emails, coordinates, target names, or comments.",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Print aggregate private-alpha health metrics without any "
            "personal observatory data."
        )
    )
    parser.add_argument(
        "--confirm-production-read",
        action="store_true",
        help=(
            "Required when POLARIS_ENVIRONMENT=production. The script is "
            "read-only and prints aggregate counts only."
        ),
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help=(
            "Load Polaris environment settings before connecting, for example "
            ".env.staging. Values are never printed."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the raw aggregate JSON instead of the plain-English review.",
    )
    arguments = parser.parse_args()

    if arguments.env_file:
        load_env_file(arguments.env_file)

    from sqlalchemy import inspect
    from sqlalchemy.exc import SQLAlchemyError

    from app.core.config import settings
    from app.database.database import SessionLocal
    from app.services.alpha_metrics_service import build_alpha_metrics_report

    if (
        settings.ENVIRONMENT == "production"
        and not arguments.confirm_production_read
    ):
        raise SystemExit(
            "Refusing a production database read without "
            "--confirm-production-read."
        )

    database = SessionLocal()
    try:
        required_tables = {
            "profiles",
            "observatories",
            "recommendation_runs",
            "recommendation_feedback",
        }
        try:
            available_tables = set(
                inspect(database.get_bind()).get_table_names()
            )
        except SQLAlchemyError as error:
            raise SystemExit(
                "Could not connect to the configured alpha database. "
                "Check network access and the selected env file; no metrics "
                "were read."
            ) from error
        missing_tables = required_tables - available_tables
        if missing_tables:
            missing_text = ", ".join(sorted(missing_tables))
            raise SystemExit(
                "The configured database is not the hosted alpha database "
                f"(missing: {missing_text})."
            )
        report = build_alpha_metrics_report(database)
    finally:
        database.close()

    if arguments.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text_report(report))


if __name__ == "__main__":
    main()
