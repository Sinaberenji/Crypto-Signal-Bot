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
                print(f"{symbol}: skipped (not enough candles: trend={len(trend_candles)}, entry={len(entry_candles)})")
                return None

            trend_candles_parsed = [self.client.parse_kline(c) for c in trend_candles]
            entry_candles_parsed = [self.client.parse_kline(c) for c in entry_candles]

            trend_indicators = compute_all_indicators(
                trend_candles_parsed,
                ema_short_period=settings.EMA_SHORT,
                ema_long_period=settings.EMA_LONG,
                rsi_period=settings.RSI_PERIOD,
                macd_fast=settings.MACD_FAST,
                macd_slow=settings.MACD_SLOW,
                macd_signal=settings.MACD_SIGNAL,
                volume_sma_period=settings.VOLUME_SMA_PERIOD
            )

            entry_indicators = compute_all_indicators(
                entry_candles_parsed,
                ema_short_period=settings.EMA_SHORT,
                ema_long_period=settings.EMA_LONG,
                rsi_period=settings.RSI_PERIOD,
                macd_fast=settings.MACD_FAST,
                macd_slow=settings.MACD_SLOW,
                macd_signal=settings.MACD_SIGNAL,
                volume_sma_period=settings.VOLUME_SMA_PERIOD
            )

            trend_structure = analyze_market_structure(trend_candles_parsed, trend_indicators)
            entry_structure = analyze_market_structure(entry_candles_parsed, entry_indicators)

            current_price = entry_candles_parsed[-1]["close"]
            current_volume = entry_candles_parsed[-1]["volume"]
            atr = entry_indicators.atr[-1] if not np.isnan(entry_indicators.atr[-1]) else current_price * 0.02

            long_signal = self._check_long_conditions(
                symbol, current_price, atr, current_volume, trend_structure, entry_structure, entry_indicators
            )
            if long_signal:
                return long_signal

            short_signal = self._check_short_conditions(
                symbol, current_price, atr, current_volume, trend_structure, entry_structure, entry_indicators
            )
            if short_signal:
                return short_signal

            rsi_val = entry_indicators.rsi[-1]
            rsi_str = f"{rsi_val:.1f}" if not np.isnan(rsi_val)={ "NaN"
            print(
                f"{symbol}: no signal "
                f"(trend={trend_structure.trend}, rsi={rsi_str}, "
                f"price={current_price:.6g})"
            )
            return None

        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            return None

    def _check_long_conditions(
        self,
        symbol: str,
        price: float,
        atr: float,
        current_volume: float,
        trend_structure: MarketStructure,
        entry_structure: MarketStructure,
        indicators: Indicators
    ) -> Optional[TradeSignal]:
        reasons = []
        score = 0

        if trend_structure.trend != "bullish":
            return None
        reasons.append("روند ۴h صعودی (EMA 50 > EMA 200)")
        score += 2

        rsi = indicators.rsi[-1]
        rsi_prev = indicators.rsi[-2] if len(indicators.rsi) > 1 else rsi
        if np.isnan(rsi):
            return None
        if rsi < settings.RSI_OVERSOLD and rsi > rsi_prev:
            reasons.append(f"RSI از اشباع فروش خارج شد ({rsi:.1f})")
            score += 3
        elif rsi < 45 and rsi > rsi_prev:
            reasons.append(f"RSI در حال برگشت از پایین ({rsi:.1f})")
            score += 1
        else:
            return None

        macd = indicators.macd[-1]
        macd_signal = indicators.macd_signal[-1]
        macd_hist = indicators.macd_hist[-1]
        macd_hist_prev = indicators.macd_hist[-2] if len(indicators.macd_hist) > 1 else macd_hist
        if np.isnan(macd) or np.isnan(macd_signal):
            return None
        if macd > macd_signal and macd_hist > macd_hist_prev:
            reasons.append("MACD کراس صعودی و هیستوگرم مثبت")
            score += 2
        elif macd > macd_signal:
            reasons.append("MACD بالای سیگنال")
            score += 1
        else:
            return None

        if entry_structure.nearest_support and is_near_level(price, entry_structure.nearest_support):
            reasons.append(f"نزدیک حمایت در {entry_structure.nearest_support:.4f}")
            score += 2

        vol_sma = indicators.volume_sma[-1]
        if not np.isnan(vol_sma) and current_volume > vol_sma * settings.VOLUME_MULTIPLIER:
            reasons.append(f"حجم بالاتر از میانگین ({current_volume/vol_sma:.1f}x)")
            score += 1

        stop_loss = price - atr * 1.5
        if entry_structure.nearest_support:
            stop_loss = min(stop_loss, entry_structure.nearest_support * 0.995)

        take_profit = price + (price - stop_loss) * settings.RISK_REWARD_MIN
        if entry_structure.nearest_resistance:
            take_profit = min(take_profit, entry_structure.nearest_resistance * 1.005)

        risk_reward = (take_profit - price) / (price - stop_loss) if price > stop_loss else 0
        if risk_reward < settings.RISK_REWARD_MIN:
            return None
        reasons.append(f"R:R = {risk_reward:.2f}")

        if score >= 7:
            quality = SignalQuality.STRONG
        elif score >= 5:
            quality = SignalQuality.MODERATE
        else:
            quality = SignalQuality.WEAK

        return TradeSignal(
            symbol=symbol,
            signal_type=SignalType.LONG,
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward=risk_reward,
            quality=quality,
            reason=" | ".join(reasons),
            timestamp=int(time.time()),
            indicators_snapshot={
                "rsi": rsi,
                "macd": macd,
                "macd_signal": macd_signal,
                "trend": trend_structure.trend,
                "trend_strength": trend_structure.trend_strength
            }
        )

    def _check_short_conditions(
        self,
        symbol: str,
        price: float,
        atr: float,
        current_volume: float,
        trend_structure: MarketStructure,
        entry_structure: MarketStructure,
        indicators: Indicators
    ) -> Optional[TradeSignal]:
        reasons = []
        score = 0

        if trend_structure.trend != "bearish":
            return None
        reasons.append("روند ۴h نزولی (EMA 50 < EMA 200)")
        score += 2

        rsi = indicators.rsi[-1]
        rsi_prev = indicators.rsi[-2] if len(indicators.rsi) > 1 else rsi
        if np.isnan(rsi):
            return None
        if rsi > settings.RSI_OVERBOUGHT and rsi < rsi_prev:
            reasons.append(f"RSI از اشباع خرید برگشت ({rsi:.1f})")
            score += 3
        elif rsi > 55 and rsi < rsi_prev:
            reasons.append(f"RSI در حال برگشت از بالا ({rsi:.1f})")
            score += 1
        else:
            return None

        macd = indicators.macd[-1]
        macd_signal = indicators.macd_signal[-1]
        macd_hist = indicators.macd_hist[-1]
        macd_hist_prev = indicators.macd_hist[-2] if len(indicators.macd_hist) > 1 else macd_hist
        if np.isnan(macd) or np.isnan(macd_signal):
            return None
        if macd < macd_signal and macd_hist < macd_hist_prev:
            reasons.append("MACD کراس نزولی و هیستوگرم منفی")
            score += 2
        elif macd < macd_signal:
            reasons.append("MACD زیر سیگنال")
            score += 1
        else:
            return None

        if entry_structure.nearest_resistance and is_near_level(price, entry_structure.nearest_resistance):
            reasons.append(f"نزدیک مقاومت در {entry_structure.nearest_resistance:.4f}")
            score += 2

        vol_sma = indicators.volume_sma[-1]
        if not            reasons(vol_sma) and current_volume > vol_sma * settings.VOLUME_MULTIPLIER:
            reasons.append(f"حجم بالاتر از میانگین ({current_volume/vol_sma:.1f}x)")
            score += 1

        stop_loss = price + atr * 1.5
        if entry_structure.nearest_resistance:
            stop_loss = max(stop_loss, entry_structure.nearest_resistance * 1.005)

        take_profit = price - (stop_loss - price) * settings.RISK_REWARD_MIN
        if entry_structure.nearest_support:
            take_profit = max(take_profit, entry_structure.nearest_support * 0.995)

        risk_reward = (price - take_profit) / (stop_loss - price) if stop_loss > price else 0
        if risk_reward < settings.RISK_REWARD_MIN:
            return None
        reasons.append(f"R:R = {risk_reward:.2f}")

        if score >= 7:
            quality = SignalQuality.STRONG
        elif score >= 5:
            quality = SignalQuality.MODERATE
        else:
            quality = SignalQuality.WEAK

        return TradeSignal(
            symbol=symbol,
            signal_type=SignalType.SHORT,
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward=risk_reward,
            quality=quality,
            reason=" | ".join(reasons),
            timestamp=int(time.time()),
            indicators_snapshot={
                "rsi": rsi,
                "macd": macd,
                "macd_signal": macd_signal,
                "trend": trend_structure.trend,
                "trend_strength": trend_structure.trend_strength
            }
        )

    async def scan_all(self) -> List[TradeSignal]:
        signals = []
        for symbol in settings.TRADING_PAIRS:
            signal = await self.analyze_symbol(symbol)
            if signal:
                signals.append(signal)
            await asyncio.sleep(0.1)

        signals.sort(
            key=lambda s: (QUALITY_ORDER[s.quality], s.risk_reward),
            reverse=True
        )
        return signals[:settings.MAX_SIGNALS_PER_RUN]

    async def close(self):
        await self.client.close()
