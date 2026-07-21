import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from core.database import db_retry, get_engine, get_session


class TestDatabaseEngine:
    def test_get_engine_returns_async_engine(self):
        engine = get_engine()
        assert isinstance(engine, AsyncEngine)

    def test_get_session_returns_sessionmaker(self):
        session = get_session()
        assert callable(session)

    def test_get_engine_postgres_connect_args(self):
        import core.database as db_mod
        from unittest.mock import patch

        old_engine = db_mod._engine
        try:
            db_mod._engine = None
            with patch("core.database.create_async_engine") as mock_create:
                mock_create.return_value = "mock_engine"
                with patch("core.database.DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db"):
                    eng = db_mod.get_engine()
                    assert eng == "mock_engine"
                    assert mock_create.call_count == 1
                    kwargs = mock_create.call_args[1]
                    assert kwargs["connect_args"] == {"statement_cache_size": 0}
        finally:
            db_mod._engine = old_engine


class TestDatabaseConnection:
    @pytest.mark.asyncio
    async def test_connection_executes_query(self):
        engine = get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_session_crud(self):
        session = get_session()
        async with session() as s:
            assert isinstance(s, AsyncSession)
            result = await s.execute(text("SELECT 1 AS val"))
            row = result.fetchone()
            assert row is not None


class TestDbRetry:
    @pytest.mark.asyncio
    async def test_retry_success_first_attempt(self):
        call_count = 0

        @db_retry
        async def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await succeed()
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_raises_after_three_failures(self):
        call_count = 0

        @db_retry
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("fail")

        with pytest.raises(ConnectionError, match="fail"):
            await always_fail()
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_does_not_retry_logic_errors(self):
        call_count = 0

        @db_retry
        async def logic_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("invalid logic")

        with pytest.raises(ValueError, match="invalid logic"):
            await logic_error()
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_retry(self):
        call_count = 0

        @db_retry
        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("transient")
            return "recovered"

        result = await fail_then_succeed()
        assert result == "recovered"
        assert call_count == 2
