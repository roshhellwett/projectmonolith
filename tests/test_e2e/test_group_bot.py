import pytest

from zenith_group_bot.flood_control import (
    add_warning,
    check_bot_command_limit,
    clear_warnings,
    get_flood_action,
    get_warning_count,
    is_flooding,
)
from zenith_group_bot.word_list import BANNED_WORDS, SPAM_DOMAINS


class TestWordList:
    def test_banned_words_not_empty(self):
        assert len(BANNED_WORDS) > 0

    def test_spam_domains_not_empty(self):
        assert len(SPAM_DOMAINS) > 0

    def test_banned_words_are_strings(self):
        for w in BANNED_WORDS:
            assert isinstance(w, str)

    def test_spam_domains_are_strings(self):
        for d in SPAM_DOMAINS:
            assert isinstance(d, str)


class TestFloodControl:
    def test_is_flooding_first_message(self):
        result, reason = is_flooding(user_id=99999)
        assert result is False
        assert reason == ""

    def test_is_flooding_with_idempotent_media(self):
        result, reason = is_flooding(user_id=88888, media_group_id="grp1")
        assert result is False

    def test_is_flooding_duplicate_media_skips(self):
        is_flooding(user_id=77777, media_group_id="grp2")
        result, reason = is_flooding(user_id=77777, media_group_id="grp2")
        assert result is False

    def test_check_bot_command_limit_free_user(self):
        limited, msg, _ = check_bot_command_limit(user_id=11111, is_pro=False)
        assert limited is False

    def test_warning_cycle(self):
        assert get_warning_count(user_id=22222) == 0
        add_warning(user_id=22222)
        assert get_warning_count(user_id=22222) == 1
        clear_warnings(user_id=22222)
        assert get_warning_count(user_id=22222) == 0

    def test_get_flood_action_free_user(self):
        action, duration = get_flood_action(warning_count=1, is_pro=False)
        assert isinstance(action, str)
        assert isinstance(duration, int)

    def test_raid_mode_on_model(self):
        from zenith_group_bot.models import GroupSettings

        assert hasattr(GroupSettings, "raid_mode")
        assert hasattr(GroupSettings, "raid_expires_at")


class TestGroupFilters:
    def test_filters_module_imports(self):
        import zenith_group_bot.filters

    def test_scan_for_abuse_profanity(self):
        from zenith_group_bot.filters import scan_for_abuse

        assert scan_for_abuse("this is shit") is True

    def test_scan_for_abuse_clean(self):
        from zenith_group_bot.filters import scan_for_abuse

        assert scan_for_abuse("hello world") is False

    def test_scan_for_spam_link(self):
        from zenith_group_bot.filters import scan_for_spam

        assert scan_for_spam("join now t.me/joinchat/abc") is True

    def test_scan_for_spam_clean(self):
        from zenith_group_bot.filters import scan_for_spam

        assert scan_for_spam("hello world") is False


class TestGroupModels:
    def test_group_settings_model(self):
        from zenith_group_bot.models import GroupSettings

        assert GroupSettings.__tablename__ == "zenith_group_settings"

    def test_group_strike_model(self):
        from zenith_group_bot.models import GroupStrike

        assert GroupStrike.__tablename__ == "zenith_group_strikes"


class TestGroupApp:
    def test_group_app_imports(self):
        from zenith_group_bot.group_app import cmd_verify_callback, handle_message, handle_new_member

        assert callable(handle_message)
        assert callable(handle_new_member)
        assert callable(cmd_verify_callback)


class TestGroupAiShield:
    @pytest.mark.asyncio
    async def test_scan_ai_spam_shield_fallback_and_short_text(self, monkeypatch):
        from zenith_group_bot.ai_group_handlers import scan_ai_spam_shield

        # Short text should bypass quickly
        is_scam, reason, risk = await scan_ai_spam_shield("hi")
        assert is_scam is False
        assert risk == 0

        # Missing key fallback
        monkeypatch.setattr("zenith_group_bot.ai_group_handlers.get_groq_api_key", lambda prefer_support=False: None)
        is_scam, reason, risk = await scan_ai_spam_shield("Visit this suspicious link right away!")
        assert is_scam is False
        assert risk == 0


class TestGroupVerification:
    def test_clear_quarantine_method_exists(self):
        from zenith_group_bot.repository import MemberRepo

        assert hasattr(MemberRepo, "clear_quarantine")
        assert callable(MemberRepo.clear_quarantine)
