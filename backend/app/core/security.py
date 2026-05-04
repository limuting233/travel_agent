import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

from app.core.config import settings

PASSWORD_ALGORITHM = "sha256"
PASSWORD_ITERATIONS = 100_000


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("utf-8")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(f"{raw}{padding}".encode("utf-8"))


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        PASSWORD_ALGORITHM,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"pbkdf2_{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}${salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, iterations, salt, expected_digest = password_hash.split("$", maxsplit=3)
    except ValueError:
        return False

    if scheme != f"pbkdf2_{PASSWORD_ALGORITHM}":
        return False

    digest = hashlib.pbkdf2_hmac(
        PASSWORD_ALGORITHM,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    ).hex()
    return hmac.compare_digest(digest, expected_digest)


def create_access_token(user_id: str, username: str) -> dict:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.AUTH_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": user_id,
        "username": username,
        "exp": int(expires_at.timestamp()),
    }
    payload_bytes = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)
    signature = hmac.new(
        settings.AUTH_SECRET.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return {
        "access_token": f"{payload_b64}.{_b64url_encode(signature)}",
        "token_type": "bearer",
        "expires_at": payload["exp"],
    }


def decode_access_token(access_token: str) -> dict:
    try:
        payload_b64, signature_b64 = access_token.split(".", maxsplit=1)
    except ValueError as exc:
        raise ValueError("invalid access token format") from exc

    expected_signature = hmac.new(
        settings.AUTH_SECRET.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    actual_signature = _b64url_decode(signature_b64)
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise ValueError("invalid access token signature")

    payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    exp = payload.get("exp")
    sub = payload.get("sub")
    username = payload.get("username")
    if not isinstance(exp, int) or not isinstance(sub, str) or not isinstance(username, str):
        raise ValueError("invalid access token payload")

    if exp <= int(datetime.now(timezone.utc).timestamp()):
        raise ValueError("access token expired")

    return payload
