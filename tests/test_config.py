from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.config import normalize_database_url


def test_local_settings_preserve_existing_database_default(tmp_path: Path):
    configured = Settings(base_dir=tmp_path)

    assert configured.ENVIRONMENT == "local"
    assert configured.DATABASE_FILE == tmp_path / "polaris.db"
    assert configured.DATABASE_URL == f"sqlite:///{tmp_path / 'polaris.db'}"
    assert configured.REQUIRE_LOCAL_CAPTURE_LIBRARY


@pytest.mark.parametrize(
    ("provided", "expected"),
    [
        (
            "postgres://user:pass@db.example/polaris",
            "postgresql+psycopg://user:pass@db.example/polaris",
        ),
        (
            "postgresql://user:pass@db.example/polaris",
            "postgresql+psycopg://user:pass@db.example/polaris",
        ),
        (
            "postgresql+psycopg://user:pass@db.example/polaris",
            "postgresql+psycopg://user:pass@db.example/polaris",
        ),
    ],
)
def test_postgresql_urls_select_psycopg_3(provided, expected):
    assert normalize_database_url(provided) == expected


def test_hosted_environment_rejects_sqlite(tmp_path: Path):
    with pytest.raises(ValueError, match="require PostgreSQL"):
        Settings(
            environment="production",
            base_dir=tmp_path,
        )


def test_hosted_environment_does_not_require_local_archive():
    configured = Settings(
        environment="staging",
        database_url="postgresql://user:pass@db.example/polaris",
        auth_mode="supabase",
        supabase_url="https://project-ref.supabase.co",
        supabase_publishable_key="sb_publishable_test",
    )

    assert not configured.REQUIRE_LOCAL_CAPTURE_LIBRARY


def test_hosted_environment_rejects_local_authentication():
    with pytest.raises(
        ValueError,
        match="require Supabase authentication",
    ):
        Settings(
            environment="staging",
            database_url="postgresql://user:pass@db.example/polaris",
        )


def test_supabase_authentication_builds_verification_endpoints():
    configured = Settings(
        environment="test",
        auth_mode="supabase",
        supabase_url="https://project-ref.supabase.co/",
    )

    assert configured.SUPABASE_URL == "https://project-ref.supabase.co"
    assert (
        configured.SUPABASE_ISSUER
        == "https://project-ref.supabase.co/auth/v1"
    )
    assert (
        configured.SUPABASE_JWKS_URL
        == (
            "https://project-ref.supabase.co/auth/v1/"
            ".well-known/jwks.json"
        )
    )
    assert configured.SUPABASE_AUDIENCE == "authenticated"


def test_hosted_supabase_authentication_requires_publishable_key():
    with pytest.raises(ValueError, match="PUBLISHABLE_KEY"):
        Settings(
            environment="staging",
            database_url="postgresql://user:pass@db.example/polaris",
            auth_mode="supabase",
            supabase_url="https://project-ref.supabase.co",
        )


def test_supabase_authentication_requires_project_url():
    with pytest.raises(ValueError, match="POLARIS_SUPABASE_URL"):
        Settings(
            environment="test",
            auth_mode="supabase",
            supabase_url="",
        )


def test_hosted_supabase_url_requires_https():
    with pytest.raises(ValueError, match="requires an HTTPS"):
        Settings(
            environment="production",
            database_url="postgresql://user:pass@db.example/polaris",
            auth_mode="supabase",
            supabase_url="http://project-ref.supabase.co",
        )


def test_local_user_id_must_be_a_uuid():
    with pytest.raises(ValueError, match="valid UUID"):
        Settings(
            environment="test",
            local_user_id="not-a-uuid",
        )
