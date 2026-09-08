import httpx
import time
from typing import List, Dict, Any, Optional
from config.settings import settings


class CoinexClient:
    def __init__(self):
        self.base_url = settings.COINEX_BASE_URL
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_klines(
        self,
        market: str,
        timeframe: str,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/market/kline"
        params = {
            "market": market,
            "type": timeframe,
            "limit": limit
        }
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            raise Exception(f"Coinex API error: {data.get('message')}")
        return data.get("data", [])

    async def get_ticker(self, market: str) -> Dict[str, Any]:
        url = f"{self.base_url}/market/ticker"
        params = {"market": market}
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            raise Exception(f"Coinex API error: {data.get('message')}")
        return data.get("data", {})

    async def get_market_list(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/market/info"
        response = await self.client.get(url)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            raise Exception(f"Coinex API error: {data.get('message')}")
        return data.get("data", [])

    async def close(self):
        await self.client.aclose()

    def parse_kline(self, kline: List) -> Dict[str, float]:
        return {
            "timestamp": int(kline[0]),
            "open": float(kline[1]),
            "close": float(kline[2]),
            "high": float(kline[3]),
            "low": float(kline[4]),
            "volume": float(kline[5]),
            "turnover": float(kline[6]),
        }