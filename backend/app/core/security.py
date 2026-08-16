"""Password hashing and session-token primitives.

- Passwords are hashed with Argon2id (argon2-cffi).
- Session tokens are random, high-entropy strings. Only their SHA-256 hash is
  ever persisted; the raw token lives only in the client's HttpOnly cookie.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, Exception):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except Exception:
        return False


def generate_session_token() -> str:
    """Return a fresh, URL-safe session token (raw secret for the cookie)."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """Deterministic hash used to look sessions up without storing the raw token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)
