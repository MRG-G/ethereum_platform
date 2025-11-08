# utils/pricing.py
import aiohttp
import logging

log = logging.getLogger("pricing")

FALLBACK = {"BTC": 55832.25, "ETH": 3433.91}

async def fetch_prices():
    urls = {
        "BTC": "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
        "ETH": "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT",
    }
    out = {}
    timeout = aiohttp.ClientTimeout(total=6)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as s:
            for sym, url in urls.items():
                async with s.get(url) as r:
                    data = await r.json()
                    out[sym] = round(float(data["price"]), 4)
        return out
    except Exception as e:
        log.warning(f"Price fetch failed: {e}. Using fallback.")
        return {k: round(v, 4) for k, v in FALLBACK.items()}
