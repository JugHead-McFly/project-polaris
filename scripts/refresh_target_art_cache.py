#!/usr/bin/env python3
"""Refresh the server-side NASA target-reference cache."""

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.target_art_service import refresh_target_art_cache


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve curated NASA target references and generate cached "
            "Polaris SVG artwork outside the user-facing request path."
        )
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Refresh entries even when their 30-day cache is still fresh.",
    )
    args = parser.parse_args()
    print(json.dumps(refresh_target_art_cache(force=args.force), indent=2))


if __name__ == "__main__":
    main()
