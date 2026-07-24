import os
from pathlib import Path
from typing import Optional


class Settings:
    PROJECT_NAME = "Project Polaris"
    VERSION = "1.6.0"

    VALID_ENVIRONMENTS = {
        "local",
        "production",
        "staging",
        "test",
    }

    def __init__(
        self,
        *,
        environment: Optional[str] = None,
        base_dir: Optional[Path] = None,
        database_file: Optional[Path] = None,
        database_url: Optional[str] = None,
        log_level: Optional[str] = None,
        require_local_capture_library: Optional[bool] = None,
    ):
        self.ENVIRONMENT = (
            environment
            or os.getenv("POLARIS_ENVIRONMENT", "local")
        ).lower().strip()
        if self.ENVIRONMENT not in self.VALID_ENVIRONMENTS:
            choices = ", ".join(sorted(self.VALID_ENVIRONMENTS))
            raise ValueError(
                "Unsupported POLARIS_ENVIRONMENT "
                f"'{self.ENVIRONMENT}'. Choose one of: {choices}."
            )

        self.BASE_DIR = (
            base_dir or Path(__file__).resolve().parents[2]
        ).expanduser().resolve()
        self.DATABASE_FILE = (
            database_file or self.BASE_DIR / "polaris.db"
        ).expanduser().resolve()
        configured_database_url = (
            database_url
            or os.getenv("POLARIS_DATABASE_URL")
            or f"sqlite:///{self.DATABASE_FILE}"
        )
        self.DATABASE_URL = normalize_database_url(configured_database_url)
        self.LOG_LEVEL = (
            log_level
            or os.getenv("POLARIS_LOG_LEVEL", "INFO")
        ).upper().strip()
        self.REQUIRE_LOCAL_CAPTURE_LIBRARY = (
            require_local_capture_library
            if require_local_capture_library is not None
            else _environment_boolean(
                "POLARIS_REQUIRE_LOCAL_CAPTURE_LIBRARY",
                default=self.ENVIRONMENT == "local",
            )
        )

        if (
            self.ENVIRONMENT in {"production", "staging"}
            and self.DATABASE_URL.startswith("sqlite:")
        ):
            raise ValueError(
                "Hosted Polaris environments require PostgreSQL. "
                "Set POLARIS_DATABASE_URL to a PostgreSQL connection URL."
            )


def normalize_database_url(database_url: str) -> str:
    """Select psycopg 3 for ordinary PostgreSQL connection URLs."""
    normalized = database_url.strip()
    if normalized.startswith("postgres://"):
        return normalized.replace(
            "postgres://",
            "postgresql+psycopg://",
            1,
        )
    if normalized.startswith("postgresql://"):
        return normalized.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )
    return normalized


def _environment_boolean(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.lower().strip()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(
        f"{name} must be a boolean value such as true or false."
    )


settings = Settings()
