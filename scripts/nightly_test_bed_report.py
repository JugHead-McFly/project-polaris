import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.services.existing_data_test_bed_service import (
    build_existing_data_test_bed_report,
)


def render_text_report(report: dict) -> str:
    lines = [
        f"Project Polaris {report['test_bed_version']} existing-data test beds",
        (
            f"Result: {report['passed_scenarios']} of "
            f"{report['scenario_count']} nightly scenarios passed"
        ),
        "",
    ]
    for scenario in report["scenarios"]:
        marker = "PASS" if scenario["passed"] else "FAIL"
        actual = scenario["actual"]
        lines.append(
            f"[{marker}] {scenario['name']}: {actual['decision']}; "
            f"{actual['block_count']} schedule block(s); "
            f"Opportunity Score {actual['opportunity_score']}."
        )
        for check in scenario["checks"]:
            if not check["passed"]:
                lines.append(
                    f"  Expected {check['field']}={check['expected']!r}; "
                    f"got {check['actual']!r}."
                )

    evidence = report["local_evidence"]
    lines.extend(["", "Read-only local evidence"])
    if evidence["status"] == "ready":
        lines.extend(
            [
                f"- Database integrity: {evidence['integrity_check']}",
                (
                    f"- {evidence['captures']} captures across "
                    f"{evidence['targets']} targets and "
                    f"{evidence['sessions']} sessions"
                ),
                f"- {evidence['integration_hours']} integration hours",
                (
                    f"- {evidence['quality_v2_analyses']} version-2 quality "
                    "analyses"
                ),
                (
                    f"- {evidence['invalid_session_dates']} session date value(s) "
                    "need cleanup"
                ),
                f"- {evidence['privacy_note']}",
            ]
        )
    else:
        lines.append(f"- {evidence['message']}")

    lines.extend(
        [
            "",
            (
                "Overall: READY"
                if report["ready"]
                else "Overall: NEEDS ATTENTION"
            ),
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run privacy-safe nightly decision scenarios and inventory the "
            "existing local Polaris database without changing it."
        )
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=PROJECT_ROOT / "polaris.db",
        help="Local Polaris SQLite database to inventory in read-only mode.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the complete machine-readable report.",
    )
    args = parser.parse_args()
    report = build_existing_data_test_bed_report(args.database)
    print(json.dumps(report, indent=2) if args.json else render_text_report(report))
    if not report["ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
