"""
Test configuration and fixtures
"""
import os
import sys
import pytest

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set required env vars for config module
os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("ADMIN_INITIAL_PASSWORD", "testadmin")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DB_TYPE", "postgres")

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Fresh TestClient for API tests."""
    from api_adapter import adapter_app
    return TestClient(adapter_app)
