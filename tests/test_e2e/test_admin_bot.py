from zenith_admin_bot.models import ActionType, BotStatus


class TestActionTypeEnum:
    def test_has_expected_values(self):
        actions = {e.value for e in ActionType}
        expected = {
            "keygen",
            "keygen_bulk",
            "extend",
            "revoke",
            "broadcast",
            "user_lookup",
            "user_search",
            "group_lookup",
            "ticket_reply",
            "ticket_close",
            "faq_add",
            "faq_delete",
            "canned_add",
            "canned_delete",
            "broadcast_scheduled",
            "group_disable",
            "bot_register",
            "bot_unregister",
        }
        assert actions == expected

    def test_all_members_have_unique_values(self):
        values = [e.value for e in ActionType]
        assert len(values) == len(set(values))


class TestBotStatusEnum:
    def test_has_expected_values(self):
        statuses = {e.value for e in BotStatus}
        assert statuses == {"active", "inactive", "error"}


class TestRateLimitDecorator:
    def test_rate_limit_admin_decorator_exists(self):
        from zenith_admin_bot.common import rate_limit_admin

        assert callable(rate_limit_admin)


class TestIsOwner:
    def test_admin_only_called_with_admin(self):
        from zenith_admin_bot.common import admin_only

        assert callable(admin_only)


class TestAdminRepo:
    def test_admin_repo_imports(self):
        from zenith_admin_bot.repository import AdminRepo

        assert AdminRepo is not None

    def test_bot_registry_imports(self):
        from zenith_admin_bot.repository import BotRegistryRepo

        assert BotRegistryRepo is not None

    def test_monitoring_imports(self):
        from zenith_admin_bot.monitoring import start_monitoring, stop_monitoring

        assert callable(start_monitoring)
        assert callable(stop_monitoring)
