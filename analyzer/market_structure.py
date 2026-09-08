from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import numpy as np
from config.settings import settings


@dataclass
class SupportResistance:
    level: float
    touches: int
    is_support: bool
    strength: float


@dataclass
class MarketStructure:
    trend: str
    trend_strength: float
    support_levels: List[SupportResistance]
    resistance_levels: List[SupportResistance]
    nearest_support: Optional[float]
    nearest_resistance: Optional[float]


def find_swing_points(
    highs: List[float],
    lows: List[float],
    lookback: int = 5
) -> Tuple[List[int], List[int]]:
    swing_highs = []
    swing_lows = []
    for i in range(lookback, len(highs) - lookback):
        if all(highs[i] >= highs[i - j] for j in range(1, lookback + 1)) and \
           all(highs[i] >= highs[i + j] for j in range(1, lookback + 1)):
            swing_highs.append(i)
        if all(lows[i] <= lows[i - j] for j in range(1, lookback + 1)) and \
           all(lows[i] <= lows[i + j] for j in range(1, lookback + 1)):
            swing_lows.append(i)
    return swing_highs, swing_lows


def cluster_levels(
    levels: List[float],
    proximity_pct: float = 0.5
) -> List[Tuple[float, int]]:
    if not levels:
        return []
    sorted_levels = sorted(levels)
    clusters = []
    current_cluster = [sorted_levels[0]]
    for level in sorted_levels[1:]:
        if abs(level - current_cluster[-1]) / current_cluster[-1] * 100 <= proximity_pct:
            current_cluster.append(level)
        else:
            avg_level = np.mean(current_cluster)
            clusters.append((avg_level, len(current_cluster)))
            current_cluster = [level]
    if current_cluster:
        avg_level = np.mean(current_cluster)
        clusters.append((avg_level, len(current_cluster)))
    return clusters


def detect_support_resistance(
    candles: List[Dict[str, float]],
    lookback: int = 50,
    min_touches: int = 2,
    proximity_pct: float = 0.5
) -> Tuple[List[SupportResistance], List[SupportResistance]]:
    recent = candles[-lookback:] if len(candles) >= lookback else candles
    highs = [c["high"] for c in recent]
    lows = [c["low"] for c in recent]
    current_price = recent[-1]["close"]

    swing_highs, swing_lows = find_swing_points(highs, lows)

    resistance_levels_raw = [highs[i] for i in swing_highs if highs[i] > current_price]
    support_levels_raw = [lows[i] for i in swing_lows if lows[i] < current_price]

    resistance_clusters = cluster_levels(resistance_levels_raw, proximity_pct)
    support_clusters = cluster_levels(support_levels_raw, proximity_pct)

    resistances = [
        SupportResistance(level=level, touches=touches, is_support=False,
                          strength=touches * (1 + (level - current_price) / current_price))
        for level, touches in resistance_clusters if touches >= min_touches
    ]
    supports = [
        SupportResistance(level=level, touches=touches, is_support=True,
                          strength=touches * (1 + (current_price - level) / current_price))
        for level, touches in support_clusters if touches >= min_touches
    ]

    resistances.sort(key=lambda x: x.level)
    supports.sort(key=lambda x: -x.level)

    return supports, resistances


def detect_trend(
    candles: List[Dict[str, float]],
    ema_short: List[float],
    ema_long: List[float]
) -> Tuple[str, float]:
    if len(candles) < 2 or np.isnan(ema_short[-1]) or np.isnan(ema_long[-1]):
        return "neutral", 0.0

    current_price = candles[-1]["close"]
    ema_short_val = ema_short[-1]
    ema_long_val = ema_long[-1]
    ema_short_prev = ema_short[-2] if len(ema_short) > 1 else ema_short_val
    ema_long_prev = ema_long[-2] if len(ema_long) > 1 else ema_long_val

    if ema_short_val > ema_long_val and ema_short_prev <= ema_long_prev:
        trend = "bullish"
    elif ema_short_val < ema_long_val and ema_short_prev >= ema_long_prev:
        trend = "bearish"
    elif ema_short_val > ema_long_val:
        trend = "bullish"
    elif ema_short_val < ema_long_val:
        trend = "bearish"
    else:
        trend = "neutral"

    distance_pct = abs(ema_short_val - ema_long_val) / ema_long_val * 100
    trend_strength = min(distance_pct * 10, 100)

    return trend, trend_strength


def analyze_market_structure(
    candles: List[Dict[str, float]],
    indicators
) -> MarketStructure:
    trend, trend_strength = detect_trend(candles, indicators.ema_short, indicators.ema_long)
    supports, resistances = detect_support_resistance(
        candles,
        lookback=settings.SR_LOOKBACK,
        min_touches=settings.SR_TOUCHES_MIN,
        proximity_pct=settings.SR_PROXIMITY_PCT
    )
    current_price = candles[-1]["close"]

    nearest_support = None
    for s in supports:
        if s.level < current_price:
            nearest_support = s.level
            break

    nearest_resistance = None
    for r in resistances:
        if r.level > current_price:
            nearest_resistance = r.level
            break

    return MarketStructure(
        trend=trend,
        trend_strength=trend_strength,
        support_levels=supports,
        resistance_levels=resistances,
        nearest_support=nearest_support,
        nearest_resistance=nearest_resistance
    )


def is_near_level(price: float, level: float, proximity_pct: float = 0.5) -> bool:
    return abs(price - level) / price * 100 <= proximity_pct