"""
Njangi Tracker — Business models & utility logic
Step 2: generate_njangi_code, hash_pin, verify_pin

Clean production helpers with full error handling.
No frontend / styling dependencies.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import string
from typing import Optional, Tuple


# Characters deliberately exclude 0, O, 1, I to avoid visual confusion.
_NJANGI_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_PIN_RE = re.compile(r"^\d{4}$")


def generate_njangi_code(prefix: str = "NJG") -> str:
    """
    Generate a human-readable public Njangi code.

    Format: PREFIX-XXXXX  (8 visible alphanumeric characters after the dash
    when counting the whole token length is typically 8–12 chars).
    Example: NJG-X7K9P

    Uses an alphabet that excludes confusing characters (0, O, 1, I).
    Collision resistance is handled by the UNIQUE constraint on groups.njangi_code;
    callers should retry on IntegrityError.
    """
    prefix = (prefix or "NJG").strip().upper()
    if not prefix:
        prefix = "NJG"
    # 5 random chars → e.g. NJG-X7K9P  (total 9 chars including dash)
    body = "".join(secrets.choice(_NJANGI_ALPHABET) for _ in range(5))
    return f"{prefix}-{body}"


def _normalize_pin(pin: str) -> str:
    """Return a cleaned 4-digit PIN string or raise ValueError."""
    if pin is None:
        raise ValueError("PIN is required")
    cleaned = str(pin).strip()
    if not _PIN_RE.fullmatch(cleaned):
        raise ValueError("PIN must be exactly 4 digits")
    return cleaned


def hash_pin(pin: str, salt: Optional[bytes] = None) -> str:
    """
    Salted hash of a 4-digit PIN.

    Uses PBKDF2-HMAC-SHA256 (120 000 iterations) — same construction as the
    existing password hasher in server.py for consistency.

    Stored format:  <salt_hex>:<digest_hex>
    """
    cleaned = _normalize_pin(pin)
    salt_bytes = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        cleaned.encode("utf-8"),
        salt_bytes,
        120_000,
    )
    return salt_bytes.hex() + ":" + digest.hex()


def verify_pin(pin: str, stored_hash: str) -> bool:
    """
    Constant-time verification of a 4-digit PIN against a stored hash
    produced by hash_pin().

    Returns False (never raises) on malformed input or hash.
    """
    if not stored_hash or ":" not in stored_hash:
        return False
    try:
        cleaned = _normalize_pin(pin)
    except ValueError:
        return False
    try:
        salt_hex, expected_hex = stored_hash.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(expected_hex)
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256",
        cleaned.encode("utf-8"),
        salt,
        120_000,
    )
    return hmac.compare_digest(actual, expected)


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """
    Salted password hash (same scheme as server.py) for email/password logins.
    """
    if not password or not str(password).strip():
        raise ValueError("Password is required")
    salt_bytes = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        str(password).encode("utf-8"),
        salt_bytes,
        120_000,
    )
    return salt_bytes.hex() + ":" + digest.hex()


def verify_password(password: str, stored_hash: str) -> bool:
    """Constant-time password verification."""
    if not stored_hash or ":" not in stored_hash:
        return False
    try:
        salt_hex, expected_hex = stored_hash.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(expected_hex)
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256",
        str(password or "").encode("utf-8"),
        salt,
        120_000,
    )
    return hmac.compare_digest(actual, expected)


def make_member_code(member_id: int) -> str:
    """Stable Member ID shown to users, e.g. MBR-000123."""
    return f"MBR-{int(member_id):06d}"


def normalize_phone(phone: str) -> str:
    """Strip spaces and common separators; keep leading + if present."""
    if not phone:
        return ""
    cleaned = re.sub(r"[\s\-().]", "", str(phone).strip())
    return cleaned


# ---------------------------------------------------------------------------
# Lightweight domain classes (kept for compatibility with older py/ modules)
# ---------------------------------------------------------------------------

class NjangiGroup:
    def __init__(self, group_id, name, contribution_amount, frequency, njangi_code=None):
        self.group_id = group_id
        self.name = name
        self.contribution_amount = contribution_amount
        self.frequency = frequency
        self.njangi_code = njangi_code


class Member:
    def __init__(self, member_id, group_id, name, phone, pin_hash=None, role="Member"):
        self.member_id = member_id
        self.group_id = group_id
        self.name = name
        self.phone = phone
        self.pin_hash = pin_hash
        self.role = role


class Cycle:
    def __init__(self, cycle_id, member_id, cycle_number, status):
        self.cycle_id = cycle_id
        self.member_id = member_id
        self.cycle_number = cycle_number
        self.status = status


class Contribution:
    def __init__(self, contribution_id, member_id, cycle_id, amount, payment_status):
        self.contribution_id = contribution_id
        self.member_id = member_id
        self.cycle_id = cycle_id
        self.amount = amount
        self.payment_status = payment_status


if __name__ == "__main__":
    # Quick self-test
    code = generate_njangi_code()
    assert code.startswith("NJG-") and len(code) == 9, code
    h = hash_pin("1234")
    assert verify_pin("1234", h)
    assert not verify_pin("9999", h)
    assert not verify_pin("12", h)
    print("model.py self-test OK:", code)
