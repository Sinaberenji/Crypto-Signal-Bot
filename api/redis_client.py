import httpx
import json
import hashlib
from typing import Optional, List
from config.settings import settings


class UpstashRedis:
    def __init__(self):
        self.url = settings.UPSTASH_REDIS_REST_URL
        self.token = settings.UPSTASH_REDIS_REST_TOKEN
        self.client = httpx.AsyncClient(timeout=10.0)
        self.enabled = bool(self.url and self.token)

    def _signal_key(self, signal) -> str:
        raw = f"{signal.symbol}:{signal.signal_type.value}:{signal.entry_price}:{signal.timestamp // 3600}"
        return f"signal:{hashlib.md5(raw.encode()).hexdigest()}"

    async def is_duplicate(self, signal) -> bool:
        if not self.enabled:
            return False
        key = self._signal_key(signal)
        try:
            response = await self.client.get(
                f"{self.url}/get/{key}",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            return response.status_code == 200 and response.json().get("result") is not None
        except Exception:
            return False

    async def mark_sent(self, signal, ttl_hours: int = None) -> bool:
        if not self.enabled:
            return True
        key = self._signal_key(signal)
        ttl = ttl_hours or settings.SIGNAL_COOLDOWN_HOURS
        try:
            response = await self.client.post(
                f"{self.url}/set/{key}",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"value": "1", "ex": ttl * 3600}
            )
            return response.status_code == 200
        except Exception:
            return False

    async def check_and_mark(self, signal) -> bool:
        if await self.is_duplicate(signal):
            return False
        return await self.mark_sent(signal)

    async def close(self):
        await self.client.aclose()


redis_client = UpstashRedis()