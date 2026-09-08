from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
import time
import numpy as np

from config.settings import settings
from analyzer.technical import Indicators, compute_all_indicators
from analyzer.market_structure import MarketStructure, analyze_market_structure, is_near_level
from api.coinex import CoinexClient


class SignalType(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class SignalQuality(Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"


QUALITY_ORDER = {
    SignalQuality.STRONG: 3,
    SignalQuality.MODERATE: 2,
    SignalQuality.WEAK: 1,
}


@dataclass
class TradeSignal:
    symbol: str
    signal_type: SignalType
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    quality: SignalQuality
    reason: str
    timestamp: int
    indicators_snapshot: Dict[str, Any]


class SignalGenerator:
    def __init__(self):
        self.client = CoinexClient()

    async def analyze_symbol(self, symbol: str) -> Optional[TradeSignal]:
        try:
            trend_candles = await self.client.get_klines(
                symbol, settings.TIMEFRAME_TREND, limit=250
            )
            entry_candles = await self.client.get_klines(
                symbol, settings.TIMEFRAME_ENTRY, limit=250
            )

            if len(trend_candles) < 210 or len(entry_candles) < 210:
                print(f"{symbol}: skipped
