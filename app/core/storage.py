from pathlib import Path


POLARIS_ROOT = Path.home() / "ProjectPolaris"

SESSIONS_ROOT = POLARIS_ROOT / "sessions"
TARGETS_ROOT = POLARIS_ROOT / "targets"
CALIBRATION_ROOT = POLARIS_ROOT / "calibration"

DARKS_ROOT = CALIBRATION_ROOT / "darks"
FLATS_ROOT = CALIBRATION_ROOT / "flats"
BIAS_ROOT = CALIBRATION_ROOT / "bias"
DARK_FLATS_ROOT = CALIBRATION_ROOT / "dark_flats"

PROCESSED_ROOT = POLARIS_ROOT / "processed"
PORTFOLIO_ROOT = POLARIS_ROOT / "portfolio"
EXPORTS_ROOT = POLARIS_ROOT / "exports"
LOGS_ROOT = POLARIS_ROOT / "logs"
AI_ROOT = POLARIS_ROOT / "ai"


def ensure_storage_directories() -> None:
    directories = [
        SESSIONS_ROOT,
        TARGETS_ROOT,
        DARKS_ROOT,
        FLATS_ROOT,
        BIAS_ROOT,
        DARK_FLATS_ROOT,
        PROCESSED_ROOT,
        PORTFOLIO_ROOT,
        EXPORTS_ROOT,
        LOGS_ROOT,
        AI_ROOT,
    ]

    for directory in directories:
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )


def get_target_root(object_name: str) -> Path:
    target_root = TARGETS_ROOT / object_name.upper()

    target_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    return target_root


def ensure_target_directories(object_name: str) -> dict:
    target_root = get_target_root(object_name)

    directories = {
        "root": target_root,
        "fits": target_root / "fits",
        "jpg": target_root / "jpg",
        "png": target_root / "png",
        "stacks": target_root / "stacks",
    }

    for directory in directories.values():
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    return directories


def get_light_capture_path(
    object_name: str,
    polaris_id: str,
    suffix: str = ".fits",
) -> Path:
    directories = ensure_target_directories(
        object_name
    )

    return directories["fits"] / f"{polaris_id}{suffix}"


def get_preview_path(
    object_name: str,
    polaris_id: str,
    suffix: str,
) -> Path:
    directories = ensure_target_directories(
        object_name
    )

    normalized_suffix = suffix.lower()

    if normalized_suffix in (".jpg", ".jpeg"):
        return directories["jpg"] / f"{polaris_id}{normalized_suffix}"

    if normalized_suffix == ".png":
        return directories["png"] / f"{polaris_id}{normalized_suffix}"

    raise ValueError(
        f"Unsupported preview suffix: {suffix}"
    )