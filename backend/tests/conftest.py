"""
Test configuration and fixtures
"""
import pytest
import sys
sys.path.insert(0, 'D:\\tools\\消费看板5（前端）\\backend')

from tortoise import Tortoise


@pytest.fixture(scope="function", autouse=True)
async def init_db():
    """Initialize test database with SQLite in-memory"""
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={'ai_db': ['ai_db.models']}
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()
