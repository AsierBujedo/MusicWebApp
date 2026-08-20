"""Password hashing and session-token primitives.

- Passwords are hashed with Argon2id (argon2-cffi).
- Session tokens are random, high-entropy strings. Only their SHA-256 hash is
  ever persisted; the raw token lives only in the client's HttpOnly cookie.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import base64

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

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


def _token_cipher(secret_key: str) -> Fernet:
    """Derive a stable Fernet key without introducing another required secret."""
    key = base64.urlsafe_b64encode(hashlib.sha256(secret_key.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_secret(value: str, secret_key: str) -> str:
    return _token_cipher(secret_key).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str, secret_key: str) -> str | None:
    try:
        return _token_cipher(secret_key).decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeDecodeError):
        return None
