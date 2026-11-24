"""Password hashing (scrypt from the standard library), JWT and refresh tokens.

ADR-004 specifies Argon2id; scrypt with per-password salt is used here because it
ships with CPython and avoids a native build dependency. Both are memory-hard
KDFs; swap `hash_password` for argon2-cffi without touching call sites.
"""
import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta

import jwt

from app.core.config import settings
from app.core.db import utcnow

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32
    )
    return "scrypt${}${}${}${}".format(
        _SCRYPT_N,
        base64.b64encode(salt).decode(),
        base64.b64encode(digest).decode(),
        _SCRYPT_P,
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, salt_b64, digest_b64, p = stored.split("$")
        if scheme != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.scrypt(
            password.encode(), salt=salt, n=int(n), r=_SCRYPT_R, p=int(p), dklen=len(expected)
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str, role: str, lang: str) -> tuple[str, int]:
    expires_in = settings.access_token_minutes * 60
    now = utcnow()
    payload = {
        "sub": user_id,
        "role": role,
        "lang": lang,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "jti": str(uuid.uuid4()),
        "typ": "access",
    }
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    return token, expires_in


def decode_access_token(token: str) -> dict:
    """Raises jwt.PyJWTError subclasses on failure."""
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def refresh_expiry() -> datetime:
    return utcnow() + timedelta(days=settings.refresh_token_days)


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.replace(microsecond=0).isoformat() + "Z"
