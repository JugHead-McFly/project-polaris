from functools import lru_cache
from typing import Optional
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer
from jwt import InvalidTokenError
from jwt import PyJWKClient
from jwt import PyJWKClientError
from pydantic import BaseModel

from app.core.config import Settings
from app.core.config import settings


ALLOWED_SUPABASE_ALGORITHMS = ("ES256", "RS256")
bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    user_id: UUID
    email: Optional[str] = None
    auth_mode: str


class AuthenticationError(Exception):
    """Raised when supplied credentials cannot establish a user identity."""


class LocalAuthService:
    def __init__(self, user_id: str):
        self.user = CurrentUser(
            user_id=UUID(user_id),
            email=None,
            auth_mode="local",
        )

    def authenticate(self, token: Optional[str]) -> CurrentUser:
        return self.user


class SupabaseAuthService:
    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks_url: str,
        jwks_client=None,
    ):
        self.issuer = issuer
        self.audience = audience
        self.jwks_client = jwks_client or PyJWKClient(
            jwks_url,
            cache_jwk_set=True,
            cache_keys=False,
            lifespan=300,
            timeout=5,
        )

    def authenticate(self, token: Optional[str]) -> CurrentUser:
        if not token:
            raise AuthenticationError("Bearer token is required.")

        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=list(ALLOWED_SUPABASE_ALGORITHMS),
                audience=self.audience,
                issuer=self.issuer,
                options={
                    "require": [
                        "aud",
                        "exp",
                        "iat",
                        "iss",
                        "role",
                        "sub",
                    ],
                },
            )
            if claims["role"] != "authenticated":
                raise AuthenticationError(
                    "Token does not represent an authenticated user."
                )
            user_id = UUID(claims["sub"])
        except AuthenticationError:
            raise
        except (
            InvalidTokenError,
            PyJWKClientError,
            TypeError,
            ValueError,
        ) as error:
            raise AuthenticationError("Bearer token is invalid.") from error

        return CurrentUser(
            user_id=user_id,
            email=claims.get("email"),
            auth_mode="supabase",
        )


def build_auth_service(config: Settings):
    if config.AUTH_MODE == "local":
        return LocalAuthService(config.LOCAL_USER_ID)
    return SupabaseAuthService(
        issuer=config.SUPABASE_ISSUER,
        audience=config.SUPABASE_AUDIENCE,
        jwks_url=config.SUPABASE_JWKS_URL,
    )


@lru_cache(maxsize=1)
def get_auth_service():
    return build_auth_service(settings)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        bearer_scheme
    ),
    auth_service=Depends(get_auth_service),
) -> CurrentUser:
    token = credentials.credentials if credentials else None
    try:
        return auth_service.authenticate(token)
    except AuthenticationError as error:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
