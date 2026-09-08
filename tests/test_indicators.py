import pytest
import numpy as np
from analyzer.technical import (
    calculate_ema,
    calculate_rsi,
    calculate_macd,
    calculate_sma,
    calculate_atr,
    compute_all_indicators
)


def generate_test_candles(n: int = 250) -> list:
    np.random.seed(42)
    base = 50000
    candles = []
    for i in range(n):
        change = np.random.normal(0, 0.01)
        base *= (1 + change)
        high = base * (1 + abs(np.random.normal(0, 0.005)))
        low = base * (1 - abs(np.random.normal(0, 0.005)))
        volume = np.random.uniform(100, 1000)
        candles.append({
            "timestamp": 1700000000 + i * 3600,
            "open": base,
            "close": base * (1 + np.random.normal(0, 0.002)),
            "high": high,
            "low": low,
            "volume": volume,
            "turnover": base * volume
        })
    return candles


def test_ema():
    values = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
    ema = calculate_ema(values, 5)
    assert len(ema) == len(values)
    assert np.isnan(ema[0])
    assert not np.isnan(ema[-1])
    assert ema[-1] > ema[-2]


def test_rsi():
    values = [10] * 5 + [15] * 5 + [10] * 5
    rsi = calculate_rsi(values, 5)
    assert len(rsi) == len(values)
    assert np.isnan(rsi[0])
    assert 0 <= rsi[-1] <= 100


def test_macd():
    values = list(range(100, 200))
    macd, signal, hist = calculate_macd(values, 12, 26, 9)
    assert len(macd) == len(values)
    assert len(signal) == len(values)
    assert len(hist) == len(values)


def test_sma():
    values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    sma = calculate_sma(values, 3)
    assert len(sma) == len(values)
    assert np.isnan(sma[0])
    assert np.isnan(sma[1])
    assert sma[2] == 2.0
    assert sma[-1] == 9.0


def test_atr():
    high = [11, 12, 13, 14, 15] * 10
    low = [9, 10, 11, 12, 13] * 10
    close = [10, 11, 12, 13, 14] * 10
    atr = calculate_atr(high, low, close, 5)
    assert len(atr) == len(high)
    assert not np.isnan(atr[-1])


def test_compute_all_indicators():
    candles = generate_test_candles(250)
    indicators = compute_all_indicators(candles)

    assert len(indicators.ema_short) == 250
    assert len(indicators.ema_long) == 250
    assert len(indicators.rsi) == 250
    assert len(indicators.macd) == 250
    assert len(indicators.macd_signal) == 250
    assert len(indicators.macd_hist) == 250
    assert len(indicators.volume_sma) == 250
    assert len(indicators.atr) == 250

    assert not np.isnan(indicators.ema_short[-1])
    assert not np.isnan(indicators.rsi[-1])
    assert 0 <= indicators.rsi[-1] <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])