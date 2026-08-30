import os
import subprocess
from pathlib import Path
from typing import Optional


def _clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _git_value(base_dir: Path, *args: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=base_dir,
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return _clean(result.stdout)


def build_info(base_dir: Path) -> dict:
    commit = _clean(os.getenv("RENDER_GIT_COMMIT"))
    branch = _clean(os.getenv("RENDER_GIT_BRANCH"))
    source = "render" if commit or branch else "local"

    if commit is None:
        commit = _git_value(base_dir, "rev-parse", "HEAD")
    if branch is None:
        branch = _git_value(base_dir, "branch", "--show-current")

    return {
        "source": source,
        "commit": commit,
        "short_commit": commit[:7] if commit else None,
        "branch": branch,
    }
