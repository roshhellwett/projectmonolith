import os

import pytest
from sqlalchemy import text

from core.database import get_engine


@pytest.mark.asyncio
async def test_database_reachable():
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_database_tables_exist():
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT tablename FROM pg_tables " "WHERE schemaname='public' ORDER BY tablename")
        )
        tables = [row[0] for row in result]
    required = [
        "zenith_group_settings",
        "zenith_ai_conversations",
        "crypto_users",
        "admin_audit_log",
        "zenith_support_tickets",
    ]
    for table in required:
        assert table in tables, f"Missing required table: {table}"


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_service_registry_exists(client):
    response = await client.get("/health")
    data = response.json()
    assert "services" in data
    assert isinstance(data["services"], dict)


@pytest.mark.asyncio
async def test_env_vars_for_production():
    required = ["ADMIN_BOT_TOKEN", "DATABASE_URL", "WEBHOOK_SECRET"]
    for var in required:
        assert os.getenv(var), f"Missing required env var: {var}"
