from datetime import datetime
from datetime import timedelta
from datetime import timezone
from uuid import UUID

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from jwt import PyJWK

from app.core.auth import AuthenticationError
from app.core.auth import CurrentUser
from app.core.auth import LocalAuthService
from app.core.auth import SupabaseAuthService
from app.core.auth import get_auth_service
from app.main import app


ISSUER = "https://project-ref.supabase.co/auth/v1"
AUDIENCE = "authenticated"
USER_ID = UUID("d8938f0c-6afd-4647-92bd-74d42b46ee88")


class StaticJwksClient:
    def __init__(self, signing_key):
        self.signing_key = signing_key

    def get_signing_key_from_jwt(self, token):
        return self.signing_key


class RejectingAuthService:
    def authenticate(self, token):
        raise AuthenticationError("invalid")


class AcceptingAuthService:
    def authenticate(self, token):
        assert token == "valid-token"
        return CurrentUser(
            user_id=USER_ID,
            email="observer@example.com",
            auth_mode="supabase",
        )


@pytest.fixture
def signing_material():
    private_key = ec.generate_private_key(ec.SECP256R1())
    jwk_json = jwt.algorithms.ECAlgorithm.to_jwk(
        private_key.public_key()
    )
    return private_key, PyJWK.from_json(jwk_json)


def make_token(private_key, **overrides):
    now = datetime.now(timezone.utc)
    claims = {
        "aud": AUDIENCE,
        "email": "observer@example.com",
        "exp": now + timedelta(minutes=10),
        "iat": now,
        "iss": ISSUER,
        "role": "authenticated",
        "sub": str(USER_ID),
    }
    claims.update(overrides)
    return jwt.encode(
        claims,
        private_key,
        algorithm="ES256",
        headers={"kid": "test-key"},
    )


def test_local_authentication_returns_stable_operator_identity():
    service = LocalAuthService(str(USER_ID))

    user = service.authenticate(None)

    assert user.user_id == USER_ID
    assert user.auth_mode == "local"
    assert user.email is None


def test_supabase_authentication_validates_and_returns_identity(
    signing_material,
):
    private_key, signing_key = signing_material
    service = SupabaseAuthService(
        issuer=ISSUER,
        audience=AUDIENCE,
        jwks_url=f"{ISSUER}/.well-known/jwks.json",
        jwks_client=StaticJwksClient(signing_key),
    )

    user = service.authenticate(make_token(private_key))

    assert user.user_id == USER_ID
    assert user.email == "observer@example.com"
    assert user.auth_mode == "supabase"


@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": "wrong-audience"},
        {"iss": "https://attacker.invalid/auth/v1"},
        {"exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        {"role": "anon"},
        {"sub": "not-a-uuid"},
    ],
)
def test_supabase_authentication_rejects_invalid_claims(
    signing_material,
    overrides,
):
    private_key, signing_key = signing_material
    service = SupabaseAuthService(
        issuer=ISSUER,
        audience=AUDIENCE,
        jwks_url=f"{ISSUER}/.well-known/jwks.json",
        jwks_client=StaticJwksClient(signing_key),
    )

    with pytest.raises(AuthenticationError):
        service.authenticate(make_token(private_key, **overrides))


def test_supabase_authentication_rejects_missing_token(
    signing_material,
):
    _, signing_key = signing_material
    service = SupabaseAuthService(
        issuer=ISSUER,
        audience=AUDIENCE,
        jwks_url=f"{ISSUER}/.well-known/jwks.json",
        jwks_client=StaticJwksClient(signing_key),
    )

    with pytest.raises(AuthenticationError):
        service.authenticate(None)


def test_identity_probe_returns_local_user_without_token():
    response = TestClient(app).get("/auth/me")

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "00000000-0000-0000-0000-000000000001",
        "email": None,
        "auth_mode": "local",
    }


def test_identity_probe_rejects_missing_token_in_supabase_mode():
    app.dependency_overrides[get_auth_service] = (
        lambda: RejectingAuthService()
    )
    try:
        response = TestClient(app).get("/auth/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}
    assert response.headers["www-authenticate"] == "Bearer"


def test_identity_probe_accepts_bearer_token():
    app.dependency_overrides[get_auth_service] = (
        lambda: AcceptingAuthService()
    )
    try:
        response = TestClient(app).get(
            "/auth/me",
            headers={"Authorization": "Bearer valid-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["user_id"] == str(USER_ID)
    assert response.json()["email"] == "observer@example.com"


def test_data_api_uses_authentication_boundary():
    app.dependency_overrides[get_auth_service] = (
        lambda: RejectingAuthService()
    )
    try:
        response = TestClient(app).get("/dashboard")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401


def test_operator_shell_remains_public_for_future_sign_in():
    app.dependency_overrides[get_auth_service] = (
        lambda: RejectingAuthService()
    )
    try:
        response = TestClient(app).get("/operator")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "Project Polaris" in response.text


def test_capture_preview_uses_authentication_boundary():
    app.dependency_overrides[get_auth_service] = (
        lambda: RejectingAuthService()
    )
    try:
        response = TestClient(app).get(
            "/operator-preview/does-not-matter"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
