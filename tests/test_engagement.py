"""Tests for engagement features (referral, feedback, stats, changelog)."""

from core.engagement_handlers import _RE_REFERRAL_CODE, _sanitize_text


class TestSanitize:
    def test_sanitize_removes_html(self):
        assert _sanitize_text("Hello <script>alert('xss')</script> World") == "Hello alert('xss') World"

    def test_sanitize_trims_whitespace(self):
        assert _sanitize_text("  hello  ") == "hello"

    def test_sanitize_max_len(self):
        long = "a" * 5000
        result = _sanitize_text(long, max_len=10)
        assert len(result) == 10

    def test_sanitize_empty(self):
        assert _sanitize_text("") == ""


class TestReferralCodeRegex:
    def test_valid_codes(self):
        assert _RE_REFERRAL_CODE.match("ABC123")
        assert _RE_REFERRAL_CODE.match("ABCDEFGHIJ")
        assert _RE_REFERRAL_CODE.match("123456")

    def test_invalid_codes(self):
        assert not _RE_REFERRAL_CODE.match("abc")  # lowercase
        assert not _RE_REFERRAL_CODE.match("AB")  # too short
        assert not _RE_REFERRAL_CODE.match("A" * 21)  # too long
        assert not _RE_REFERRAL_CODE.match("")  # empty
        assert not _RE_REFERRAL_CODE.match("ABC-123")  # has dash
