"""
TDD: Password hashing module
Run: pytest tests/core/test_password.py -v
"""
import pytest
from core.auth.password import hash_password, verify_password


class TestHashPassword:
    def test_hashes_plain_password(self):
        hashed = hash_password("mysecret123")
        assert isinstance(hashed, str)
        assert len(hashed) > 20
        assert hashed != "mysecret123"

    def test_same_password_different_hash(self):
        h1 = hash_password("mysecret123")
        h2 = hash_password("mysecret123")
        assert h1 != h2  # bcrypt salts should differ

    def test_hashes_unicode_password(self):
        hashed = hash_password("密码123!@#")
        assert isinstance(hashed, str)
        assert len(hashed) > 20


class TestVerifyPassword:
    def test_correct_password_verifies(self):
        hashed = hash_password("mysecret123")
        assert verify_password("mysecret123", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("mysecret123")
        assert verify_password("wrongpassword", hashed) is False

    def test_empty_password_fails(self):
        hashed = hash_password("mysecret123")
        assert verify_password("", hashed) is False

    def test_unicode_password_verifies(self):
        plain = "密码123!@#"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_compat_with_existing_bcrypt(self):
        """Must verify hashes created by existing passlib bcrypt usage"""
        # Pre-generated bcrypt hash for "admin123" (compatible with both passlib and bcrypt lib)
        existing = "$2b$12$T4HrOSkBiqmoTmaSINyv9erJMaA8llYKieoywAo2MPI5cMckS2SLe"
        assert verify_password("admin123", existing) is True
