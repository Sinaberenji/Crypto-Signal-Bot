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

QUALITY_ORDER = {SignalQuality.STRONG: 3, SignalQuality.MODERATE: 2, SignalQuality.WEAK: 1}

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
            trend_candles = await self.client.get_klines(symbol, settings.TIMEFRAME_TREND, limit=250)
            entry_candles = await self.client.get_klines(symbol, settings.TIMEFRAME_ENTRY, limit=250)
            if len(trend_candles) < 210 or len(entry_candles) < 210:
                return None
            
            trend_candles_parsed = [self.client.parse_kline(c) for c in trend_candles]
            entry_candles_parsed = [self.client.parse_kline(c) for c in entry_candles]
            
            trend_indicators = compute_all_indicators(trend_candles_parsed, ema_short_period=settings.EMA_SHORT, ema_long_period=settings.EMA_LONG, rsi_period=settings.RSI_PERIOD, macd_fast=settings.MACD_FAST, macd_slow=settings.MACD_SLOW, macd_signal=settings.MACD_SIGNAL, volume_sma_period=settings.VOLUME_SMA_PERIOD)
            entry_indicators = compute_all_indicators(entry_candles_parsed, ema_short_period=settings.EMA_SHORT, ema_long_period=settings.EMA_LONG, rsi_period=settings.RSI_PERIOD, macd_fast=settings.MACD_FAST, macd_slow=settings.MACD_SLOW, macd_signal=settings.MACD_SIGNAL, volume_sma_period=settings.VOLUME_SMA_PERIOD)
            
            trend_structure = analyze_market_structure(trend_candles_parsed, trend_indicators)
            entry_structure = analyze_market_structure(entry_candles_parsed, entry_indicators)
            
            current_price = entry_candles_parsed[-1]["close"]
            current_volume = entry_candles_parsed[-1]["volume"]
            atr = entry_indicators.atr[-1] if not np.isnan(entry_indicators.atr[-1]) else current_price * 0.02
            
            long_signal = self._check_long_conditions(symbol, current_price, atr, current_volume, trend_structure, entry_structure, entry_indicators)
            if long_signal: return long_signal
            
            short_signal = self._check_short_conditions(symbol, current_price, atr, current_volume, trend_structure, entry_structure, entry_indicators)
            if short_signal: return short_signal
            
            return None
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            return None

    def _check_long_conditions(self, symbol, price, atr, volume, trend_s, entry_s, ind) -> Optional[TradeSignal]:
        if trend_s.trend != "bullish": return None
        rsi = ind.rsi[-1]
        macd = ind.macd[-1]
        macd_sig = ind.macd_signal[-1]
        if np.isnan(rsi) or rsi > 70 or macd < macd_sig: return None
        
        # Simple signal creation
        return TradeSignal(symbol, SignalType.LONG, price, price-(atr*1.5), price+(atr*3), 2.0, SignalQuality.MODERATE, "Bullish Trend", int(time.time()), {})

    def _check_short_conditions(self, symbol, price, atr, volume, trend_s, entry_s, ind) -> Optional[TradeSignal]:
        if trend_s.trend != "bearish": return None
        rsi = ind.rsi[-1]
        macd = ind.macd[-1]
        macd_sig = ind.macd_signal[-1]
        if np.isnan(rsi) or rsi < 30 or macd > macd_sig: return None
        
        return TradeSignal(symbol, SignalType.SHORT, price, price+(atr*1.5), price-(atr*3), 2.0, SignalQuality.MODERATE, "Bearish Trend", int(time.time()), {})

    async def scan_all(self) -> List[TradeSignal]:
        signals = []
        for symbol in settings.TRADING_PAIRS:
            signal = await self.analyze_symbol(symbol)
            if signal: signals.append(signal)
            await asyncio.sleep(0.1)
        return signals[:settings.MAX_SIGNALS_PER_RUN]

    async def close(self):
        await self.client.close()
