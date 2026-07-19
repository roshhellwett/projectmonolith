import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import Base, get_engine, get_session, init_db


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = get_engine()
    yield eng


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    await init_db()
    async with get_session()() as session:
        yield session
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f"DELETE FROM {table.name}"))


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    from gateway import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_telegram_update() -> dict[str, Any]:
    return {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "date": 1700000000,
            "chat": {"id": 12345, "type": "private", "first_name": "Test"},
            "from": {"id": 67890, "is_bot": False, "first_name": "TestUser"},
            "text": "/start",
        },
    }
