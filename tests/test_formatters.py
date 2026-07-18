from core.formatters import (
    format_address,
    format_card,
    format_countdown,
    format_error_hint,
    format_list_item,
    format_pnl,
    format_price_change,
    format_progress_bar,
    format_success,
    format_usage_meter,
    format_warning,
)


class TestFormatCard:
    def test_basic_card(self):
        result = format_card("Test Title", "Body content")
        assert "<b>" in result
        assert "Test Title" in result
        assert "Body content" in result

    def test_card_with_footer(self):
        result = format_card("Title", "Body", footer="Footer text")
        assert "Footer text" in result

    def test_card_with_custom_border(self):
        result = format_card("Title", "Body", border_color="🔴")
        assert "🔴" in result


class TestFormatListItem:
    def test_basic_item(self):
        result = format_list_item(1, "Item text")
        assert "1." in result
        assert "Item text" in result

    def test_truncation(self):
        result = format_list_item(1, "A" * 100, max_length=10)
        assert result.endswith("...")
        assert len(result) <= 15


class TestFormatProgressBar:
    def test_full_bar(self):
        result = format_progress_bar(100, 100)
        assert "100%" in result

    def test_empty_bar(self):
        result = format_progress_bar(0, 100)
        assert "0%" in result

    def test_zero_total(self):
        result = format_progress_bar(0, 0)
        assert "0%" in result

    def test_half_bar(self):
        result = format_progress_bar(50, 100)
        assert "50%" in result


class TestFormatCountdown:
    def test_zero_seconds(self):
        assert format_countdown(0) == "0s"

    def test_negative_seconds(self):
        assert format_countdown(-5) == "0s"

    def test_compact_style(self):
        result = format_countdown(3661)
        assert "1h" in result
        assert "1m" in result

    def test_detailed_style(self):
        result = format_countdown(3661, style="detailed")
        assert "hour" in result
        assert "minute" in result
        assert "second" in result

    def test_emoji_style(self):
        result = format_countdown(125, style="emoji")
        assert "⏰" in result


class TestFormatUsageMeter:
    def test_with_numbers(self):
        result = format_usage_meter(5, 10, label="API Calls", show_numbers=True)
        assert "API Calls" in result
        assert "5/10" in result

    def test_without_numbers(self):
        result = format_usage_meter(5, 10, label="API Calls", show_numbers=False)
        assert "API Calls" in result
        assert "5/10" not in result


class TestFormatPriceChange:
    def test_positive_change(self):
        result = format_price_change(100.50)
        assert "+" in result
        assert "$100.50" in result

    def test_negative_change(self):
        result = format_price_change(-50.25)
        assert "$50.25" in result

    def test_with_percentage(self):
        result = format_price_change(100, percentage=5.5)
        assert "5.50%" in result


class TestFormatPnl:
    def test_profit(self):
        result = format_pnl(500)
        assert "+" in result

    def test_loss(self):
        result = format_pnl(-250)
        assert "-" in result

    def test_with_percentage(self):
        result = format_pnl(100, percentage=10.0)
        assert "10.00%" in result

    def test_no_color(self):
        result = format_pnl(100, show_color=False)
        assert result


class TestHelpers:
    def test_format_address(self):
        result = format_address("0x742d35Cc6634C0532925a3b844Bc9e7595f2bD18")
        assert "0x742d" in result

    def test_format_success(self):
        result = format_success("Operation completed")
        assert "Operation completed" in result

    def test_format_error_hint(self):
        result = format_error_hint("Try again later")
        assert "Try again later" in result

    def test_format_warning(self):
        result = format_warning("Be careful")
        assert "Be careful" in result
