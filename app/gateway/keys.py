"""
API Key utilities for PayFlow Gateway.
Generates Razorpay-style key_id / key_secret pairs.
"""

import secrets
import hashlib
import hmac
import bcrypt


def generate_key_pair() -> tuple[str, str]:
    """
    Returns (key_id, key_secret).
    key_id   → pf_key_<16 hex chars>   (safe to store plain)
    key_secret → pf_sec_<32 hex chars>  (shown ONCE, stored as bcrypt hash)
    """
    key_id = f"pf_key_{secrets.token_hex(8)}"
    key_secret = f"pf_sec_{secrets.token_hex(16)}"
    return key_id, key_secret


def hash_secret(key_secret: str) -> str:
    """bcrypt-hash the raw key_secret for safe DB storage."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(key_secret.encode("utf-8"), salt).decode("utf-8")


def verify_secret(plain: str, hashed: str) -> bool:
    """Verify a raw key_secret against its stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def generate_order_ref() -> str:
    return f"pf_order_{secrets.token_hex(10)}"


def generate_payment_ref() -> str:
    return f"pf_pay_{secrets.token_hex(10)}"


def generate_refund_ref() -> str:
    return f"pf_rfnd_{secrets.token_hex(10)}"


def generate_webhook_signature(payload: str, secret: str) -> str:
    """
    HMAC-SHA256 of the raw JSON payload with the key_secret.
    Merchant verifies this on their end:
        import hmac, hashlib
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        assert header_sig == expected
    """
    mac = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload.encode("utf-8"),
        digestmod=hashlib.sha256,
    )
    return mac.hexdigest()
