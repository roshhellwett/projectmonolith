"""
Database of known Smart Money, VCs, Exchanges, and prominent figures.
Keys must be lowercase for reliable matching.
"""

KNOWN_WALLETS = {
    # Exchanges
    "0x28c6c06298d514db089934071355e5743bf21d60": "Binance 14 (Cold Storage)",
    "0xeae7380dd4cef6fbd1144f49e4d1e6964258a4f4": "Binance (Hot Wallet)",
    "0x5a52e96bacd65b16222880f074a3f169dbac16b0": "Binance 8",
    "0x4e6533cd0a89d714b62db8ea54d3bb9e88bf0c68": "Kraken (Hot Wallet)",
    "0x5c985e89dde482efa97ea4e13731f8f226c09ce9": "Coinbase 10",
    "0xa090e606e30bd747d4e6245a1517ebe430f0057e": "OKX (Hot Wallet)",
    
    # Market Makers / VCs
    "0x9696f59e4d72e237be84ffd425dcad154bf96976": "Wintermute Trading",
    "0x00000000219ab540356cbb839cbe05303d7705fa": "Wintermute (Market Maker)",
    "0xfb89a973aebb59ca2f8510847ca0108b1309fa8e": "Jump Trading (Hot)",
    "0xb25fa5f9aa1dc4e9c71c4c1a8e1cb6df1f52d4dd": "a16z Crypto",
    "0x55c9b3a0e633d7b90b8f413d78da4b10fa770c06": "Paradigm",
    
    # Prominent Figures
    "0xd8da6bf26964af9d7eed9e03e53415d37aa96045": "Vitalik.eth (Ethereum Founder)",
    "0x220866b1a2219f40e72f5c628b65d54268ca3a9d": "Justin Sun",
    
    # Smart Contracts
    "0xdef1c0ded9bec7f1a1670819833240f027b25eff": "0x (ZeroEx) Proxy",
    "0x1111111254fb6c44bac0bed2854e76f90643097d": "1inch Router",
    "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad": "Uniswap V3 Router",
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "Uniswap V2 Router",
    "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": "Uniswap V3 Router 2",
}

def identify_wallet(address: str) -> str | None:
    """Returns the known label for a wallet, or None if unknown."""
    if not address:
        return None
    return KNOWN_WALLETS.get(address.lower())
