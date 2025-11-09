# utils/pricing.py
import aiohttp
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional

log = logging.getLogger("pricing")

# Fallback цены на случай, если все API недоступны
FALLBACK = {"BTC": 55832.25, "ETH": 3433.91}

# Кэш цен
price_cache = {
    "last_update": None,
    "prices": None
}

from config import BINANCE_API_KEY, BINANCE_API_SECRET, COINGECKO_API_KEY

# Конфигурация API
BINANCE_URLS = {
    "BTC": "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
    "ETH": "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT"
}

COINGECKO_URLS = {
    "BTC": "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
    "ETH": "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
}

# Заголовки для API запросов
BINANCE_HEADERS = {
    "X-MBX-APIKEY": BINANCE_API_KEY
} if BINANCE_API_KEY != "YOUR_BINANCE_API_KEY" else {}

COINGECKO_HEADERS = {
    "x-cg-pro-api-key": COINGECKO_API_KEY
} if COINGECKO_API_KEY != "YOUR_COINGECKO_API_KEY" else {}

async def fetch_binance_prices() -> Dict[str, float]:
    """Получение цен с Binance"""
    out = {}
    timeout = aiohttp.ClientTimeout(total=6)
    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=BINANCE_HEADERS) as session:
            for sym, url in BINANCE_URLS.items():
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            out[sym] = float(data["price"])
                except Exception as e:
                    log.warning(f"Binance {sym} fetch failed: {e}")
        return out
    except Exception as e:
        log.warning(f"Binance session failed: {e}")
        return {}

async def fetch_coingecko_prices() -> Dict[str, float]:
    """Получение цен с Coingecko"""
    symbol_to_id = {"BTC": "bitcoin", "ETH": "ethereum"}
    out = {}
    timeout = aiohttp.ClientTimeout(total=6)
    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=COINGECKO_HEADERS) as session:
            for sym, url in COINGECKO_URLS.items():
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            crypto_id = symbol_to_id[sym]
                            out[sym] = float(data[crypto_id]["usd"])
                except Exception as e:
                    log.warning(f"Coingecko {sym} fetch failed: {e}")
        return out
    except Exception as e:
        log.warning(f"Coingecko session failed: {e}")
        return {}

def average_prices(prices_list: list[Dict[str, float]]) -> Dict[str, float]:
    """Усреднение цен из разных источников"""
    result = {}
    for symbol in ["BTC", "ETH"]:
        prices = [p[symbol] for p in prices_list if symbol in p]
        if prices:
            # Убираем экстремальные значения если больше 2 источников
            if len(prices) > 2:
                prices.remove(max(prices))
                prices.remove(min(prices))
            result[symbol] = round(sum(prices) / len(prices), 4)
    return result

async def fetch_prices() -> Dict[str, float]:
    """Получение актуальных цен с кэшированием на 30 секунд"""
    global price_cache
    
    # Проверяем кэш
    if price_cache["last_update"] is not None:
        age = datetime.now() - price_cache["last_update"]
        if age < timedelta(seconds=30) and price_cache["prices"] is not None:
            return price_cache["prices"]
    
    # Получаем цены из всех источников параллельно
    prices_list = await asyncio.gather(
        fetch_binance_prices(),
        fetch_coingecko_prices()
    )
    
    # Фильтруем пустые результаты
    prices_list = [p for p in prices_list if p]
    
    if prices_list:
        # Усредняем цены из разных источников
        prices = average_prices(prices_list)
        
        # Обновляем кэш
        price_cache["last_update"] = datetime.now()
        price_cache["prices"] = prices
        
        return prices
    else:
        # Если все API недоступны, используем резервные цены
        log.warning("All price sources failed. Using fallback prices.")
        return {k: round(v, 4) for k, v in FALLBACK.items()}
