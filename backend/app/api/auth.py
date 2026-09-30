"""Supabase JWT verification, applied to every /api route.

Two modes, matching how Supabase projects sign access tokens:
- SUPABASE_JWT_SECRET set -> HS256 with the project's legacy JWT secret.
- otherwise -> asymmetric keys (ES256/RS256) from SUPABASE_URL/auth/v1/.well-known/jwks.json.
If neither is configured every request is rejected (fail closed).

App roles (e.g. "expert") come from the token's `app_metadata.role`, which only the server/service
role can set. `user_metadata` is editable by the user and is never trusted for authorization.
"""

from functools import lru_cache
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.config import Settings, get_settings

AUDIENCE = "authenticated"
bearer = HTTPBearer(auto_error=False)


EXPERT_ROLE = "expert"


class AuthUser(BaseModel):
    id: UUID
    email: str | None = None
    role: str | None = None  # Supabase's Postgres role, always "authenticated" for signed-in users
    app_role: str | None = None  # our role, from app_metadata.role

    @property
    def is_expert(self) -> bool:
        return self.app_role == EXPERT_ROLE


@lru_cache
def _jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(jwks_url, cache_keys=True)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})


def verify_token(token: str, settings: Settings) -> AuthUser:
    try:
        if settings.supabase_jwt_secret:
            claims = jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"], audience=AUDIENCE)
        elif settings.supabase_url:
            url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
            key = _jwks_client(url).get_signing_key_from_jwt(token).key
            claims = jwt.decode(token, key, algorithms=["ES256", "RS256"], audience=AUDIENCE)
        else:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Auth is not configured on the server")
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Token expired")
    except (jwt.PyJWKClientError, jwt.InvalidTokenError):
        raise _unauthorized("Invalid token")
    try:
        app_metadata = claims.get("app_metadata") or {}
        return AuthUser(id=UUID(claims["sub"]), email=claims.get("email"), role=claims.get("role"),
                        app_role=app_metadata.get("role") if isinstance(app_metadata, dict) else None)
    except (KeyError, ValueError):
        raise _unauthorized("Token has no valid subject")


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    settings: Settings = Depends(get_settings),
) -> AuthUser:
    if creds is None or creds.scheme.lower() != "bearer":
        raise _unauthorized("Missing bearer token")
    return verify_token(creds.credentials, settings)


def require_expert(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if not user.is_expert:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Expert role required")
    return user
