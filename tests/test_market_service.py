import pytest

from zenith_crypto_bot.market_service import close_market_client, resolve_token_id


@pytest.mark.asyncio
async def test_close_market_client():
    await close_market_client()


class TestResolveTokenId:
    def test_btc_resolves_to_bitcoin(self):
        assert resolve_token_id("btc") == "bitcoin"
        assert resolve_token_id("BTC") == "bitcoin"

    def test_eth_resolves_to_ethereum(self):
        assert resolve_token_id("eth") == "ethereum"

    def test_sol_resolves_to_solana(self):
        assert resolve_token_id("sol") == "solana"

    def test_unknown_symbol_passes_through(self):
        assert resolve_token_id("unknown-token") == "unknown-token"

    def test_already_id_passes_through(self):
        assert resolve_token_id("bitcoin") == "bitcoin"

    def test_case_insensitive(self):
        assert resolve_token_id("BTC") == "bitcoin"
        assert resolve_token_id("Btc") == "bitcoin"
        assert resolve_token_id("Eth") == "ethereum"
