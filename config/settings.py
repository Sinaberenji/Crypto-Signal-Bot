import os
from dataclasses import dataclass
from typing import List


@dataclass
class Settings:
    COINEX_BASE_URL: str = "https://api.coinex.com/v2"
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    UPSTASH_REDIS_REST_URL: str = os.getenv("UPSTASH_REDIS_REST_URL", "")
    UPSTASH_REDIS_REST_TOKEN: str = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
    SIGNAL_COOLDOWN_HOURS: int = 4
    MAX_SIGNALS_PER_RUN: int = 3
    RISK_REWARD_MIN: float = 2.0
    TRADING_PAIRS: List[str] = None
    TIMEFRAME_TREND: str = "4hour"
    TIMEFRAME_ENTRY: str = "1hour"
    EMA_SHORT: int = 50
    EMA_LONG: int = 200
    RSI_PERIOD: int = 14
    RSI_OVERBOUGHT: float = 70
    RSI_OVERSOLD: float = 30
    MACD_FAST: int = 12
    MACD_SLOW: int = 26
    MACD_SIGNAL: int = 9
    VOLUME_SMA_PERIOD: int = 20
    VOLUME_MULTIPLIER: float = 1.2
    SR_LOOKBACK: int = 50
    SR_TOUCHES_MIN: int = 2
    SR_PROXIMITY_PCT: float = 0.5

    def __post_init__(self):
        if self.TRADING_PAIRS is None:
            self.TRADING_PAIRS = [
                "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
                "ADAUSDT", "DOGEUSDT", "TRXUSDT", "TONUSDT", "AVAXUSDT"
            ]


settings = Settings()