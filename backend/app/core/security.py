"""
Security utilities for password hashing and verification.
"""

import hashlib
import secrets


def get_password_hash(password: str) -> str:
    """Hash a password using SHA-256 with a random salt."""
    salt = secrets.token_hex(16)
    h = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}${h}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a salted SHA-256 hash."""
    if "$" not in hashed_password:
        return False
    salt, h = hashed_password.split("$", 1)
    return hashlib.sha256(f"{salt}{plain_password}".encode()).hexdigest() == h
