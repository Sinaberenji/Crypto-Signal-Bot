import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Indicators:
    ema_short: List[float]
    ema_long: List[float]
    rsi: List[float]
    macd: List[float]
    macd_signal: List[float]
    macd_hist: List[float]
    volume_sma: List[float]
    atr: List[float]


def calculate_ema(values: List[float], period: int) -> List[float]:
    if len(values) < period:
        return [np.nan] * len(values)
    ema = [np.nan] * (period - 1)
    multiplier = 2 / (period + 1)
    ema.append(np.mean(values[:period]))
    for i in range(period, len(values)):
        ema.append((values[i] - ema[-1]) * multiplier + ema[-1])
    return ema


def calculate_rsi(values: List[float], period: int = 14) -> List[float]:
    if len(values) < period + 1:
        return [np.nan] * len(values)
    deltas = np.diff(values)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    rsi = [np.nan] * period
    rsi.append(100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss != 0 else 100)
    for i in range(period + 1, len(values)):
        gain = gains[i - 1]
        loss = losses[i - 1]
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        rs = avg_gain / avg_loss if avg_loss != 0 else 100
        rsi.append(100 - (100 / (1 + rs)))
    return rsi


def calculate_macd(
    values: List[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> Tuple[List[float], List[float], List[float]]:
    ema_fast = calculate_ema(values, fast)
    ema_slow = calculate_ema(values, slow)
    macd_line = [f - s if not np.isnan(f) and not np.isnan(s) else np.nan
                 for f, s in zip(ema_fast, ema_slow)]
    macd_signal_line = calculate_ema([m for m in macd_line if not np.isnan(m)], signal)
    macd_signal_padded = [np.nan] * (len(macd_line) - len(macd_signal_line)) + macd_signal_line
    macd_hist = [m - s if not np.isnan(m) and not np.isnan(s) else np.nan
                 for m, s in zip(macd_line, macd_signal_padded)]
    return macd_line, macd_signal_padded, macd_hist


def calculate_sma(values: List[float], period: int) -> List[float]:
    if len(values) < period:
        return [np.nan] * len(values)
    sma = [np.nan] * (period - 1)
    for i in range(period - 1, len(values)):
        sma.append(np.mean(values[i - period + 1:i + 1]))
    return sma


def calculate_atr(
    high: List[float],
    low: List[float],
    close: List[float],
    period: int = 14
) -> List[float]:
    if len(high) < period + 1:
        return [np.nan] * len(high)
    tr = [np.nan]
    for i in range(1, len(high)):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i - 1])
        lc = abs(low[i] - close[i - 1])
        tr.append(max(hl, hc, lc))
    atr = [np.nan] * period
    atr.append(np.mean(tr[1:period + 1]))
    for i in range(period + 1, len(high)):
        atr.append((atr[-1] * (period - 1) + tr[i]) / period)
    return atr


def compute_all_indicators(
    candles: List[Dict[str, float]],
    ema_short_period: int = 50,
    ema_long_period: int = 200,
    rsi_period: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    volume_sma_period: int = 20,
    atr_period: int = 14
) -> Indicators:
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    volumes = [c["volume"] for c in candles]

    return Indicators(
        ema_short=calculate_ema(closes, ema_short_period),
        ema_long=calculate_ema(closes, ema_long_period),
        rsi=calculate_rsi(closes, rsi_period),
        macd=calculate_macd(closes, macd_fast, macd_slow, macd_signal)[0],
        macd_signal=calculate_macd(closes, macd_fast, macd_slow, macd_signal)[1],
        macd_hist=calculate_macd(closes, macd_fast, macd_slow, macd_signal)[2],
        volume_sma=calculate_sma(volumes, volume_sma_period),
        atr=calculate_atr(highs, lows, closes, atr_period)
    )