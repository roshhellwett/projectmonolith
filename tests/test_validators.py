from core.validators import (
    validate_days,
    validate_ethereum_address,
    validate_price,
    validate_token_symbol,
    validate_user_id,
)


class TestValidateEthereumAddress:
    def test_valid_address(self):
        result = validate_ethereum_address("0x742d35Cc6634C0532925a3b844Bc9e7595f2bD18")
        assert result.is_valid
        assert result.sanitized_value == "0x742d35Cc6634C0532925a3b844Bc9e7595f2bD18".lower()

    def test_empty_address(self):
        result = validate_ethereum_address("")
        assert not result.is_valid
        assert result.error_code == "EMPTY_ADDRESS"

    def test_missing_prefix(self):
        result = validate_ethereum_address("742d35Cc6634C0532925a3b844Bc9e7595f2bD18")
        assert not result.is_valid
        assert result.error_code == "INVALID_PREFIX"

    def test_short_address(self):
        result = validate_ethereum_address("0x1234")
        assert not result.is_valid
        assert result.error_code == "INVALID_LENGTH"

    def test_invalid_hex(self):
        result = validate_ethereum_address("0xGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG")
        assert not result.is_valid

    def test_whitespace_handling(self):
        result = validate_ethereum_address("  0x742d35Cc6634C0532925a3b844Bc9e7595f2bD18  ")
        assert result.is_valid


class TestValidatePrice:
    def test_valid_price(self):
        result = validate_price("100.50")
        assert result.is_valid
        assert result.sanitized_value == "100.5"

    def test_valid_price_with_commas(self):
        result = validate_price("1,000")
        assert result.is_valid

    def test_empty_price(self):
        result = validate_price("")
        assert not result.is_valid
        assert result.error_code == "EMPTY_PRICE"

    def test_negative_price(self):
        result = validate_price("-10")
        assert not result.is_valid
        assert result.error_code == "NEGATIVE_PRICE"

    def test_zero_price(self):
        result = validate_price("0")
        assert not result.is_valid

    def test_invalid_format(self):
        result = validate_price("abc")
        assert not result.is_valid
        assert result.error_code == "INVALID_FORMAT"

    def test_exceeds_max(self):
        result = validate_price("999999999999")
        assert not result.is_valid
        assert result.error_code == "EXCEEDS_MAX"


class TestValidateTokenSymbol:
    def test_valid_symbol(self):
        result = validate_token_symbol("btc")
        assert result.is_valid
        assert result.sanitized_value == "BTC"

    def test_empty_symbol(self):
        result = validate_token_symbol("")
        assert not result.is_valid
        assert result.error_code == "EMPTY_SYMBOL"

    def test_symbol_too_long(self):
        result = validate_token_symbol("ABCDEFGHIJK")
        assert not result.is_valid
        assert result.error_code == "SYMBOL_TOO_LONG"

    def test_invalid_characters(self):
        result = validate_token_symbol("BTC!")
        assert not result.is_valid
        assert result.error_code == "INVALID_SYMBOL"

    def test_valid_numeric_symbol(self):
        result = validate_token_symbol("BTC1")
        assert result.is_valid


class TestValidateDays:
    def test_valid_days(self):
        result = validate_days("30")
        assert result.is_valid
        assert int(result.sanitized_value) == 30

    def test_empty_days(self):
        result = validate_days("")
        assert not result.is_valid

    def test_zero_days(self):
        result = validate_days("0")
        assert not result.is_valid

    def test_exceeds_max(self):
        result = validate_days("5000")
        assert not result.is_valid

    def test_invalid_format(self):
        result = validate_days("abc")
        assert not result.is_valid


class TestValidateUserId:
    def test_valid_id(self):
        result = validate_user_id("123456789")
        assert result.is_valid

    def test_empty_id(self):
        result = validate_user_id("")
        assert not result.is_valid

    def test_negative_id(self):
        result = validate_user_id("-1")
        assert not result.is_valid

    def test_invalid_format(self):
        result = validate_user_id("abc")
        assert not result.is_valid
