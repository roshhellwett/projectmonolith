import httpx
from cachetools import TTLCache

from core.circuit_breaker import get_breaker
from core.config import ETH_RPC_URL, ETHERSCAN_API_KEY
from core.logger import setup_logger

logger = setup_logger("MARKET_SVC")
_http_client: httpx.AsyncClient | None = None

# Response caches — serve stale data when APIs are down
_price_cache: TTLCache = TTLCache(maxsize=500, ttl=90)  # 90s for prices
_movers_cache: TTLCache = TTLCache(maxsize=1, ttl=300)  # 5m for top movers
_fng_cache: TTLCache = TTLCache(maxsize=1, ttl=600)  # 10m for fear & greed
_gas_cache: TTLCache = TTLCache(maxsize=1, ttl=15)  # 15s for gas prices

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
GOPLUS_BASE = "https://api.gopluslabs.io/api/v1"
ETHERSCAN_BASE = "https://api.etherscan.io/v2/api"
FEAR_GREED_URL = "https://api.alternative.me/fng/?limit=1"

UNISWAP_V2_FACTORY = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
PAIR_CREATED_TOPIC = "0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9"

SYMBOL_TO_ID = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "bnb": "binancecoin",
    "xrp": "ripple",
    "ada": "cardano",
    "doge": "dogecoin",
    "dot": "polkadot",
    "matic": "matic-network",
    "avax": "avalanche-2",
    "link": "chainlink",
    "uni": "uniswap",
    "atom": "cosmos",
    "ltc": "litecoin",
    "near": "near",
    "apt": "aptos",
    "arb": "arbitrum",
    "op": "optimism",
    "sui": "sui",
    "pepe": "pepe",
    "shib": "shiba-inu",
    "wbtc": "wrapped-bitcoin",
    "usdt": "tether",
    "usdc": "usd-coin",
    "dai": "dai",
    "ton": "the-open-network",
    "trx": "tron",
    "xlm": "stellar",
    "inj": "injective-protocol",
    "sei": "sei-network",
    "jup": "jupiter-exchange-solana",
    "render": "render-token",
    "fet": "fetch-ai",
    "wif": "dogwifcoin",
    "bonk": "bonk",
    "floki": "floki",
}


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=15.0,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=30),
            headers={"Accept": "application/json"},
        )
    return _http_client


async def close_market_client():
    global _http_client
    if _http_client:
        await _http_client.aclose()
        _http_client = None


def resolve_token_id(symbol_or_id: str) -> str:
    key = symbol_or_id.lower().strip()
    return SYMBOL_TO_ID.get(key, key)


async def get_prices(token_ids: list[str]) -> dict:
    if not token_ids:
        return {}

    breaker = get_breaker("coingecko")
    cache_key = ",".join(sorted(set(token_ids)))

    if not breaker.can_execute():
        cached = _price_cache.get(cache_key)
        if cached:
            logger.debug("Serving cached prices (circuit open)")
            return cached
        return {}

    client = get_http_client()
    ids_str = ",".join(set(token_ids))
    try:
        resp = await client.get(
            f"{COINGECKO_BASE}/simple/price",
            params={"ids": ids_str, "vs_currencies": "usd", "include_24hr_change": "true"},
        )
        resp.raise_for_status()
        data = resp.json()
        breaker.record_success()
        _price_cache[cache_key] = data
        return data
    except Exception as e:
        breaker.record_failure()
        if "429" in str(e):
            logger.debug(f"CoinGecko price fetch rate-limited (429): {e}")
        else:
            logger.error(f"CoinGecko price fetch failed: {e}")
        cached = _price_cache.get(cache_key)
        if cached:
            logger.debug("Serving stale cached prices")
            return cached
        return {}


async def get_top_movers() -> tuple[list, list]:
    breaker = get_breaker("coingecko")

    if not breaker.can_execute():
        cached = _movers_cache.get("movers")
        if cached:
            return cached
        return [], []

    client = get_http_client()
    try:
        resp = await client.get(
            f"{COINGECKO_BASE}/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 100,
                "page": 1,
                "sparkline": "false",
                "price_change_percentage": "24h",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        sorted_by_change = sorted(data, key=lambda x: x.get("price_change_percentage_24h") or 0)
        losers = sorted_by_change[:5]
        gainers = sorted_by_change[-5:][::-1]
        breaker.record_success()
        _movers_cache["movers"] = (gainers, losers)
        return gainers, losers
    except Exception as e:
        breaker.record_failure()
        if "429" in str(e):
            logger.debug(f"CoinGecko top movers rate-limited (429): {e}")
        else:
            logger.error(f"CoinGecko top movers failed: {e}")
        cached = _movers_cache.get("movers")
        if cached:
            return cached
        return [], []


async def search_token(query: str) -> dict | None:
    breaker = get_breaker("coingecko")
    if not breaker.can_execute():
        return None

    client = get_http_client()
    try:
        resp = await client.get(f"{COINGECKO_BASE}/search", params={"query": query})
        resp.raise_for_status()
        coins = resp.json().get("coins", [])
        breaker.record_success()
        if coins:
            c = coins[0]
            return {"id": c["id"], "symbol": c["symbol"].upper(), "name": c["name"]}
    except Exception as e:
        breaker.record_failure()
        logger.error(f"CoinGecko search failed: {e}")
    return None


async def get_token_security(contract: str, chain_id: str = "1") -> dict | None:
    breaker = get_breaker("goplus")
    if not breaker.can_execute():
        return None

    client = get_http_client()
    try:
        resp = await client.get(
            f"{GOPLUS_BASE}/token_security/{chain_id}",
            params={"contract_addresses": contract.lower()},
        )
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result", {})
        breaker.record_success()
        return result.get(contract.lower())
    except Exception as e:
        breaker.record_failure()
        logger.error(f"GoPlus security scan failed: {e}")
        return None


async def get_wallet_recent_txns(wallet_address: str, last_known_hash: str = None) -> list[dict]:
    if not ETHERSCAN_API_KEY:
        return []
    breaker = get_breaker("etherscan")
    if not breaker.can_execute():
        return []
    client = get_http_client()
    try:
        resp = await client.get(
            ETHERSCAN_BASE,
            params={
                "chainid": 1,
                "module": "account",
                "action": "txlist",
                "address": wallet_address,
                "startblock": 0,
                "endblock": 99999999,
                "page": 1,
                "offset": 10,
                "sort": "desc",
                "apikey": ETHERSCAN_API_KEY,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "1":
            return []
        txns = data.get("result", [])
        breaker.record_success()
        if last_known_hash:
            new_txns = []
            for tx in txns:
                if tx.get("hash") == last_known_hash:
                    break
                new_txns.append(tx)
            return new_txns
        return txns[:5]
    except Exception as e:
        breaker.record_failure()
        logger.error(f"Etherscan wallet fetch failed: {e}")
        return []


async def get_wallet_token_txns(wallet_address: str) -> list[dict]:
    if not ETHERSCAN_API_KEY:
        return []
    breaker = get_breaker("etherscan")
    if not breaker.can_execute():
        return []
    client = get_http_client()
    try:
        resp = await client.get(
            ETHERSCAN_BASE,
            params={
                "chainid": 1,
                "module": "account",
                "action": "tokentx",
                "address": wallet_address,
                "page": 1,
                "offset": 5,
                "sort": "desc",
                "apikey": ETHERSCAN_API_KEY,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "1":
            return []
        breaker.record_success()
        return data.get("result", [])[:5]
    except Exception as e:
        breaker.record_failure()
        logger.error(f"Etherscan token tx fetch failed: {e}")
        return []


async def get_fear_greed_index() -> dict | None:
    cached = _fng_cache.get("fng")
    if cached:
        return cached

    client = get_http_client()
    try:
        resp = await client.get(FEAR_GREED_URL)
        resp.raise_for_status()
        data = resp.json()
        entry = data.get("data", [{}])[0]
        result = {
            "value": int(entry.get("value", 0)),
            "classification": entry.get("value_classification", "Unknown"),
            "timestamp": entry.get("timestamp", ""),
        }
        _fng_cache["fng"] = result
        return result
    except Exception as e:
        logger.error(f"Fear & Greed API failed: {e}")
        return cached


async def get_gas_prices() -> dict | None:
    if not ETH_RPC_URL:
        return None
    client = get_http_client()
    try:
        resp = await client.post(
            ETH_RPC_URL,
            json={"jsonrpc": "2.0", "method": "eth_gasPrice", "params": [], "id": 1},
        )
        resp.raise_for_status()
        hex_gas = resp.json().get("result", "0x0")
        gas_wei = int(hex_gas, 16)
        gas_gwei = gas_wei / 1e9

        resp2 = await client.post(
            ETH_RPC_URL,
            json={"jsonrpc": "2.0", "method": "eth_getBlockByNumber", "params": ["latest", False], "id": 2},
        )
        resp2.raise_for_status()
        block = resp2.json().get("result", {})
        base_fee_hex = block.get("baseFeePerGas", "0x0")
        base_fee_gwei = int(base_fee_hex, 16) / 1e9

        return {
            "gas_gwei": round(gas_gwei, 2),
            "base_fee_gwei": round(base_fee_gwei, 2),
            "priority_low": round(base_fee_gwei * 1.1, 2),
            "priority_medium": round(base_fee_gwei * 1.25, 2),
            "priority_high": round(base_fee_gwei * 1.5, 2),
        }
    except Exception as e:
        logger.error(f"Gas price fetch failed: {e}")
        return None


async def get_new_pairs(from_block: int = None) -> tuple[list[dict], int]:
    if not ETH_RPC_URL:
        return [], 0
    client = get_http_client()
    try:
        resp = await client.post(
            ETH_RPC_URL,
            json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
        )
        resp.raise_for_status()
        latest_block = int(resp.json().get("result", "0x0"), 16)

        if from_block is None:
            from_block = max(0, latest_block - 50)
        else:
            from_block = max(0, from_block, latest_block - 1900)

        resp2 = await client.post(
            ETH_RPC_URL,
            json={
                "jsonrpc": "2.0",
                "method": "eth_getLogs",
                "params": [
                    {
                        "address": UNISWAP_V2_FACTORY,
                        "topics": [PAIR_CREATED_TOPIC],
                        "fromBlock": hex(from_block),
                        "toBlock": hex(latest_block),
                    }
                ],
                "id": 2,
            },
        )
        resp2.raise_for_status()
        logs = resp2.json().get("result", [])

        pairs = []
        for log in logs[-5:]:
            topics = log.get("topics", [])
            if len(topics) >= 3:
                token0 = "0x" + topics[1][-40:]
                token1 = "0x" + topics[2][-40:]
                pair_address = "0x" + log.get("data", "")[26:66] if log.get("data") else "unknown"
                pairs.append(
                    {
                        "token0": token0,
                        "token1": token1,
                        "pair": pair_address,
                        "block": int(log.get("blockNumber", "0x0"), 16),
                        "tx_hash": log.get("transactionHash", ""),
                    }
                )
        return pairs, latest_block
    except Exception as e:
        logger.error(f"New pair scan failed: {e}")
        return [], from_block or 0


async def get_whale_transfers(min_value_eth: float = 50.0) -> list[dict]:
    """Fetch real large ETH transfers from Etherscan."""
    if not ETHERSCAN_API_KEY:
        return []
    breaker = get_breaker("etherscan")
    if not breaker.can_execute():
        return []
    client = get_http_client()
    try:
        resp = await client.get(
            ETHERSCAN_BASE,
            params={
                "chainid": 1,
                "module": "account",
                "action": "txlist",
                "address": "0x28C6c06298d514Db089934071355E5743bf21d60",
                "startblock": 0,
                "endblock": 99999999,
                "page": 1,
                "offset": 500,
                "sort": "desc",
                "apikey": ETHERSCAN_API_KEY,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "1":
            return []
        txns = data.get("result", [])
        whales = []
        for tx in txns:
            try:
                val_eth = int(tx.get("value", "0")) / 1e18
                if val_eth >= min_value_eth:
                    whales.append(
                        {
                            "hash": tx.get("hash", ""),
                            "from": tx.get("from", ""),
                            "to": tx.get("to", ""),
                            "value_eth": round(val_eth, 2),
                            "timestamp": tx.get("timeStamp", ""),
                        }
                    )
            except (ValueError, ZeroDivisionError):
                continue
        breaker.record_success()
        return whales[:5]
    except Exception as e:
        breaker.record_failure()
        logger.debug(f"Whale transfer fetch failed (non-critical): {e}")
        return []
