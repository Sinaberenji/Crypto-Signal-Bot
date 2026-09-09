import httpx
import time
from typing import List, Dict, Any, Optional
from config.settings import settings


class CoinexClient:
    def __init__(self):
        self.base_url = settings.COINEX_BASE_URL
        self.client = httpx.AsyncClient(timeout=30.0)

    KLINE_ENDPOINTS = [
        "/v2/market/kline",
        "/v2/market/klines",
        "/market/kline",
        "/market/klines",
        "/api/v2/market/kline",
        "/api/v2/market/klines",
    ]

    TICKER_ENDPOINTS = [
        "/v2/market/ticker",
        "/market/ticker",
        "/api/v2/market/ticker",
    ]

    INFO_ENDPOINTS = [
        "/v2/market/info",
        "/market/info",
        "/api/v2/market/info",
    ]

    TIMEFRAME_ALIASES = {
        "1min": ["1min", "1m"],
        "3min": ["3min", "3m"],
        "5min": ["5min", "5m"],
        "15min": ["15min", "15m"],
        "30min": ["30min", "30m"],
        "1hour": ["1hour", "1h", "60min"],
        "2hour": ["2hour", "2h", "120min"],
        "4hour": ["4hour", "4h", "240min"],
        "6hour": ["6hour", "6h", "360min"],
        "12hour": ["12hour", "12h", "720min"],
        "1day": ["1day", "1d", "1440min"],
        "1week": ["1week", "1w", "10080min"],
    }

    def _get_market_variants(self, market: str) -> List[str]:
        variants = [market]
        if market.endswith("USDT"):
            variants.append(market.replace("USDT", "-USDT"))
            variants.append(market.replace("USDT", "_USDT"))
            variants.append(market.lower())
            variants.append(market.lower().replace("usdt", "-usdt"))
        return variants

    async def _try_endpoints(self, endpoints: List[str], params: Dict) -> Optional[Dict]:
        for endpoint in endpoints:
            url = f"{self.base_url}{endpoint}"
            try:
                response = await self.client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 0:
                        return data
                elif response.status_code == 404:
                    continue
            except Exception:
                continue
        return None

    async def get_klines(
        self,
        market: str,
        timeframe: str,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        timeframe_variants = self.TIMEFRAME_ALIASES.get(timeframe, [timeframe])
        
        for tf in timeframe_variants:
            for mkt in self._get_market_variants(market):
                params = {"market": mkt, "type": tf, "limit": limit}
                data = await self._try_endpoints(self.KLINE_ENDPOINTS, params)
                if data:
                    result = data.get("data", [])
                    if result:
                        return result
        
        raise Exception(f"Coinex API: all format attempts failed for {market} {timeframe}")

    async def get_ticker(self, market: str) -> Dict[str, Any]:
        for mkt in self._get_market_variants(market):
            params = {"market": mkt}
            data = await self._try_endpoints(self.TICKER_ENDPOINTS, params)
            if data:
                return data.get("data", {})
        raise Exception(f"Coinex ticker: all market formats failed for {market}")

    async def get_market_list(self) -> List[Dict[str, Any]]:
        data = await self._try_endpoints(self.INFO_ENDPOINTS, {})
        if data:
            return data.get("data", [])
        raise Exception(f"Coinex market info: all endpoints failed")

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