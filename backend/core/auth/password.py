"""
Password hashing / verification — wrapper around bcrypt library
Compatible with existing passlib bcrypt hashes.
"""
import bcrypt as _bcrypt


def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return _bcrypt.hashpw(plain.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False
