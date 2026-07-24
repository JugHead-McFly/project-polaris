import os
from pathlib import Path
from typing import Optional
from uuid import UUID


class Settings:
    PROJECT_NAME = "Project Polaris"
    VERSION = "1.6.0"

    VALID_ENVIRONMENTS = {
        "local",
        "production",
        "staging",
        "test",
    }
    VALID_AUTH_MODES = {
        "local",
        "supabase",
    }
    DEFAULT_LOCAL_USER_ID = "00000000-0000-0000-0000-000000000001"

    def __init__(
        self,
        *,
        environment: Optional[str] = None,
        base_dir: Optional[Path] = None,
        database_file: Optional[Path] = None,
        database_url: Optional[str] = None,
        log_level: Optional[str] = None,
        require_local_capture_library: Optional[bool] = None,
        auth_mode: Optional[str] = None,
        supabase_url: Optional[str] = None,
        supabase_audience: Optional[str] = None,
        local_user_id: Optional[str] = None,
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
        self.AUTH_MODE = (
            auth_mode
            or os.getenv("POLARIS_AUTH_MODE", "local")
        ).lower().strip()
        if self.AUTH_MODE not in self.VALID_AUTH_MODES:
            choices = ", ".join(sorted(self.VALID_AUTH_MODES))
            raise ValueError(
                "Unsupported POLARIS_AUTH_MODE "
                f"'{self.AUTH_MODE}'. Choose one of: {choices}."
            )

        configured_supabase_url = (
            supabase_url
            if supabase_url is not None
            else os.getenv("POLARIS_SUPABASE_URL")
        )
        self.SUPABASE_URL = (
            configured_supabase_url.rstrip("/")
            if configured_supabase_url
            else None
        )
        self.SUPABASE_AUDIENCE = (
            supabase_audience
            or os.getenv("POLARIS_SUPABASE_AUDIENCE", "authenticated")
        ).strip()
        self.LOCAL_USER_ID = (
            local_user_id
            or os.getenv(
                "POLARIS_LOCAL_USER_ID",
                self.DEFAULT_LOCAL_USER_ID,
            )
        ).strip()
        try:
            UUID(self.LOCAL_USER_ID)
        except ValueError as error:
            raise ValueError(
                "POLARIS_LOCAL_USER_ID must be a valid UUID."
            ) from error

        self.SUPABASE_ISSUER = (
            f"{self.SUPABASE_URL}/auth/v1"
            if self.SUPABASE_URL
            else None
        )
        self.SUPABASE_JWKS_URL = (
            f"{self.SUPABASE_ISSUER}/.well-known/jwks.json"
            if self.SUPABASE_ISSUER
            else None
        )

        if (
            self.ENVIRONMENT in {"production", "staging"}
            and self.DATABASE_URL.startswith("sqlite:")
        ):
            raise ValueError(
                "Hosted Polaris environments require PostgreSQL. "
                "Set POLARIS_DATABASE_URL to a PostgreSQL connection URL."
            )
        if (
            self.ENVIRONMENT in {"production", "staging"}
            and self.AUTH_MODE != "supabase"
        ):
            raise ValueError(
                "Hosted Polaris environments require Supabase authentication. "
                "Set POLARIS_AUTH_MODE=supabase."
            )
        if self.AUTH_MODE == "supabase" and not self.SUPABASE_URL:
            raise ValueError(
                "Supabase authentication requires POLARIS_SUPABASE_URL."
            )
        if (
            self.AUTH_MODE == "supabase"
            and self.ENVIRONMENT in {"production", "staging"}
            and not self.SUPABASE_URL.startswith("https://")
        ):
            raise ValueError(
                "Hosted Supabase authentication requires an HTTPS "
                "POLARIS_SUPABASE_URL."
            )
        if not self.SUPABASE_AUDIENCE:
            raise ValueError("POLARIS_SUPABASE_AUDIENCE cannot be empty.")


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
