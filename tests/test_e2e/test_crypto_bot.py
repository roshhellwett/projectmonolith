import pytest

from zenith_crypto_bot.market_service import resolve_token_id


class TestResolveTokenId:
    def test_btc_resolves_to_bitcoin(self):
        assert resolve_token_id("btc") == "bitcoin"

    def test_eth_resolves_to_ethereum(self):
        assert resolve_token_id("eth") == "ethereum"

    def test_sol_resolves_to_solana(self):
        assert resolve_token_id("sol") == "solana"

    def test_usdt_resolves_to_tether(self):
        assert resolve_token_id("usdt") == "tether"

    def test_usdc_resolves_to_usd_coin(self):
        assert resolve_token_id("usdc") == "usd-coin"

    def test_doge_resolves_to_dogecoin(self):
        assert resolve_token_id("doge") == "dogecoin"

    def test_xrp_resolves_to_ripple(self):
        assert resolve_token_id("xrp") == "ripple"

    def test_ada_resolves_to_cardano(self):
        assert resolve_token_id("ada") == "cardano"

    def test_dot_resolves_to_polkadot(self):
        assert resolve_token_id("dot") == "polkadot"

    def test_unknown_symbol_passes_through(self):
        assert resolve_token_id("unknown-coin") == "unknown-coin"

    def test_already_full_id_passes_through(self):
        assert resolve_token_id("bitcoin") == "bitcoin"

    def test_case_insensitive(self):
        assert resolve_token_id("BTC") == "bitcoin"
        assert resolve_token_id("Btc") == "bitcoin"
        assert resolve_token_id("Eth") == "ethereum"

    def test_empty_string_returns_empty(self):
        assert resolve_token_id("") == ""


class TestCryptoModels:
    def test_crypto_user_model_exists(self):
        from zenith_crypto_bot.models import CryptoUser

        assert hasattr(CryptoUser, "__tablename__")
        assert CryptoUser.__tablename__ == "crypto_users"

    def test_price_alert_model_exists(self):
        from zenith_crypto_bot.models import PriceAlert

        assert PriceAlert.__tablename__ == "crypto_price_alerts"

    def test_watchlist_model_exists(self):
        from zenith_crypto_bot.models import WatchlistToken

        assert WatchlistToken.__tablename__ == "crypto_watchlist"


class TestCryptoMarketService:
    def test_close_market_client(self):
        from zenith_crypto_bot.market_service import close_market_client

        assert callable(close_market_client)


class TestCryptoSubscriptions:
    def test_subscription_model(self):
        from zenith_crypto_bot.models import Subscription

        assert Subscription.__tablename__ == "crypto_subscriptions"
        assert hasattr(Subscription, "expires_at")
