"""JWKS mode (newer Supabase projects sign with asymmetric keys, e.g. ES256)."""

import time
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

from app.api import auth
from app.config import Settings

SETTINGS = Settings(supabase_url="https://proj.supabase.co", supabase_jwt_secret="")


@pytest.fixture
def es256(monkeypatch):
    key = ec.generate_private_key(ec.SECP256R1())

    class FakeJwks:
        def get_signing_key_from_jwt(self, token):
            return type("K", (), {"key": key.public_key()})()

    monkeypatch.setattr(auth, "_jwks_client", lambda url: FakeJwks())
    return key


def sign(key, **claims):
    base = {"sub": str(uuid4()), "aud": "authenticated", "exp": int(time.time()) + 60}
    return jwt.encode({**base, **claims}, key, algorithm="ES256")


def test_valid_es256_token(es256):
    uid = uuid4()
    user = auth.verify_token(sign(es256, sub=str(uid), email="farmer@example.com"), SETTINGS)
    assert user.id == uid and user.email == "farmer@example.com"


def test_token_signed_by_another_key_is_rejected(es256):
    other = ec.generate_private_key(ec.SECP256R1())
    with pytest.raises(HTTPException) as e:
        auth.verify_token(sign(other), SETTINGS)
    assert e.value.status_code == 401


def test_expired_es256_token(es256):
    with pytest.raises(HTTPException) as e:
        auth.verify_token(sign(es256, exp=int(time.time()) - 5), SETTINGS)
    assert e.value.detail == "Token expired"


def test_hs256_token_not_accepted_in_jwks_mode(es256):
    forged = jwt.encode({"sub": str(uuid4()), "aud": "authenticated", "exp": int(time.time()) + 60},
                        "guessed-secret-guessed-secret-1234", algorithm="HS256")
    with pytest.raises(HTTPException) as e:
        auth.verify_token(forged, SETTINGS)
    assert e.value.status_code == 401
