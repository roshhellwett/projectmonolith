from core.formatters import format_address, format_divider, format_progress_bar


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


class TestFormatAddress:
    def test_normal_address(self):
        result = format_address("0x742d35Cc6634C0532925a3b844Bc9e7595f2bD18")
        assert "0x742d" in result
        assert "bD18" in result

    def test_short_address(self):
        result = format_address("0x1234")
        assert result == "0x1234"

    def test_empty_address(self):
        result = format_address("")
        assert result == ""


class TestFormatDivider:
    def test_default(self):
        result = format_divider()
        assert len(result) == 20

    def test_custom_length(self):
        result = format_divider(length=10)
        assert len(result) == 10

    def test_custom_char(self):
        result = format_divider(char="-", length=5)
        assert result == "-----"
