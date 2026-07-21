from core.config import (
    ADMIN_BOT_TOKEN,
    ADMIN_USER_ID,
    AI_BOT_TOKEN,
    CRYPTO_BOT_TOKEN,
    DATABASE_URL,
    DB_POOL_SIZE,
    GROUP_BOT_TOKEN,
    LOG_LEVEL,
    PORT,
    SUPPORT_BOT_TOKEN,
    WEBHOOK_SECRET,
    WEBHOOK_URL,
)


class TestConfigValues:
    def test_port_is_valid(self):
        assert isinstance(PORT, int)
        assert 1024 <= PORT <= 65535

    def test_db_pool_size_is_positive(self):
        assert isinstance(DB_POOL_SIZE, int)
        assert DB_POOL_SIZE > 0

    def test_log_level_is_valid(self):
        assert LOG_LEVEL in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

    def test_webhook_url_format(self):
        if WEBHOOK_URL:
            assert WEBHOOK_URL.startswith("http")

    def test_webhook_secret_format(self):
        if WEBHOOK_SECRET:
            assert len(WEBHOOK_SECRET) >= 8

    def test_admin_user_id_is_valid(self):
        assert isinstance(ADMIN_USER_ID, int)

    def test_bot_tokens_are_strings(self):
        assert isinstance(ADMIN_BOT_TOKEN, str)
        assert isinstance(AI_BOT_TOKEN, str)
        assert isinstance(CRYPTO_BOT_TOKEN, str)
        assert isinstance(GROUP_BOT_TOKEN, str)
        assert isinstance(SUPPORT_BOT_TOKEN, str)


class TestConfigHelpers:
    def test_is_owner_positive(self):
        from core.config import is_owner

        assert is_owner(ADMIN_USER_ID) is True

    def test_is_owner_negative(self):
        from core.config import is_owner

        assert is_owner(999999999) is False

    def test_is_owner_zero(self):
        from core.config import is_owner

        assert is_owner(0) is False

    def test_get_user_tier_owner(self):
        from core.config import get_user_tier

        assert get_user_tier(ADMIN_USER_ID) == "owner"

    def test_get_user_tier_pro(self):
        from core.config import get_user_tier

        # Use a non-admin user ID (ADMIN_USER_ID=12345 in conftest)
        assert get_user_tier(99999, days_left=30) == "pro"

    def test_get_user_tier_free(self):
        from core.config import get_user_tier

        # Use a non-admin user ID (ADMIN_USER_ID=12345 in conftest)
        assert get_user_tier(99999, days_left=0) == "free"

    def test_database_url_format(self):
        if DATABASE_URL:
            assert "postgresql" in DATABASE_URL or "sqlite" in DATABASE_URL

    def test_ai_search_triggers(self):
        from core.config import AI_SEARCH_TRIGGERS

        assert isinstance(AI_SEARCH_TRIGGERS, list)
        assert len(AI_SEARCH_TRIGGERS) > 0
