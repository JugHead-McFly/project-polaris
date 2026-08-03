import argparse
import statistics
import time
from dataclasses import dataclass
from typing import Iterable
from typing import Optional
from urllib import error
from urllib import request


DEFAULT_BASE_URL = "https://project-polaris-private-alpha.onrender.com"
DEFAULT_PATHS = ("/health/live", "/health/ready", "/operator")


@dataclass(frozen=True)
class TimingResult:
    path: str
    status: Optional[int]
    elapsed_ms: float
    ok: bool
    error: Optional[str] = None


def time_endpoint(base_url: str, path: str, timeout: float) -> TimingResult:
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    started = time.perf_counter()
    try:
        response = request.urlopen(url, timeout=timeout)
        with response:
            response.read(256)
            status = response.getcode()
        elapsed_ms = (time.perf_counter() - started) * 1000
        return TimingResult(
            path=path,
            status=status,
            elapsed_ms=elapsed_ms,
            ok=200 <= status < 400,
        )
    except (error.HTTPError, error.URLError, TimeoutError, OSError) as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        status = exc.code if isinstance(exc, error.HTTPError) else None
        return TimingResult(
            path=path,
            status=status,
            elapsed_ms=elapsed_ms,
            ok=False,
            error=str(exc),
        )


def run_baseline(
    base_url: str,
    paths: Iterable[str],
    samples: int,
    timeout: float,
) -> dict[str, list[TimingResult]]:
    results: dict[str, list[TimingResult]] = {}
    for path in paths:
        results[path] = [
            time_endpoint(base_url=base_url, path=path, timeout=timeout)
            for _ in range(samples)
        ]
    return results


def render_report(results: dict[str, list[TimingResult]]) -> str:
    lines = ["Project Polaris alpha performance baseline", ""]
    for path, timings in results.items():
        elapsed = [timing.elapsed_ms for timing in timings]
        ok_count = sum(1 for timing in timings if timing.ok)
        status_values = ", ".join(
            str(timing.status or "error") for timing in timings
        )
        lines.extend(
            [
                path,
                f"- Samples: {len(timings)}",
                f"- Successful: {ok_count}/{len(timings)}",
                f"- Statuses: {status_values}",
                f"- Median: {statistics.median(elapsed):.0f} ms",
                f"- Fastest: {min(elapsed):.0f} ms",
                f"- Slowest: {max(elapsed):.0f} ms",
            ]
        )
        errors = [timing.error for timing in timings if timing.error]
        if errors:
            lines.append(f"- Errors: {'; '.join(errors)}")
        lines.append("")
    lines.append(
        "Scope: public endpoint timing only. Do not ask alpha testers to collect these numbers."
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Time public hosted-alpha endpoints for a lightweight baseline."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument(
        "--path",
        action="append",
        dest="paths",
        help="Path to time. May be provided more than once.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    paths = tuple(args.paths or DEFAULT_PATHS)
    results = run_baseline(
        base_url=args.base_url,
        paths=paths,
        samples=max(1, args.samples),
        timeout=args.timeout,
    )
    print(render_report(results))
    return 0 if all(timing.ok for group in results.values() for timing in group) else 1


if __name__ == "__main__":
    raise SystemExit(main())
