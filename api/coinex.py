import httpx
import time
from typing import List, Dict, Any, Optional
from config.settings import settings


class CoinexClient:
    def __init__(self):
        self.base_url = settings.COINEX_BASE_URL
        self.client = httpx.AsyncClient(timeout=30.0)

    # Multiple timeframe format attempts for Coinex V2 API
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

    # Market format attempts
    def _get_market_variants(self, market: str) -> List[str]:
        variants = [market]
        if market.endswith("USDT"):
            variants.append(market.replace("USDT", "-USDT"))
            variants.append(market.replace("USDT", "_USDT"))
            variants.append(market.lower())
            variants.append(market.lower().replace("usdt", "-usdt"))
        return variants

    async def get_klines(
        self,
        market: str,
        timeframe: str,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/market/kline"
        
        # Try multiple timeframe formats
        timeframe_variants = self.TIMEFRAME_ALIASES.get(timeframe, [timeframe])
        
        for tf in timeframe_variants:
            for mkt in self._get_market_variants(market):
                params = {"market": mkt, "type": tf, "limit": limit}
                try:
                    response = await self.client.get(url, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("code") == 0:
                            result = data.get("data", [])
                            if result:
                                print(f"Coinex OK: market={mkt}, timeframe={tf}, count={len(result)}")
                                return result
                    elif response.status_code == 404:
                        continue
                except Exception as e:
                    print(f"Coinex try failed: market={mkt}, timeframe={tf}, error={e}")
                    continue
        
        # If all failed, raise last error
        raise Exception(f"Coinex API: all format attempts failed for {market} {timeframe}")

    async def get_ticker(self, market: str) -> Dict[str, Any]:
        url = f"{self.base_url}/market/ticker"
        for mkt in self._get_market_variants(market):
            params = {"market": mkt}
            try:
                response = await self.client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 0:
                        return data.get("data", {})
            except Exception:
                continue
        raise Exception(f"Coinex ticker: all market formats failed for {market}")

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