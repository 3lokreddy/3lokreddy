"""
indicators.py
Pure numpy/pandas implementations of all technical indicators.
No external TA libraries required.
"""

import numpy as np
import pandas as pd


# ── Primitives ────────────────────────────────────────────────────────────────

def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average using pandas ewm (span method)."""
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


# ── RSI ───────────────────────────────────────────────────────────────────────

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index using Wilder's smoothing.
    Returns series of RSI values (0–100).
    """
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    alpha = 1.0 / period
    avg_gain = gain.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=alpha, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_vals = 100.0 - (100.0 / (1.0 + rs))
    rsi_vals = rsi_vals.fillna(100.0)   # avg_loss == 0 → pure uptrend → RSI 100
    return rsi_vals


# ── MACD ──────────────────────────────────────────────────────────────────────

def macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD Line, Signal Line, and Histogram.
    Returns (macd_line, signal_line, histogram).
    """
    ema_fast   = ema(series, fast)
    ema_slow   = ema(series, slow)
    macd_line  = ema_fast - ema_slow
    signal_line = ema(macd_line, signal_period)
    histogram  = macd_line - signal_line
    return macd_line, signal_line, histogram


# ── Bollinger Bands ───────────────────────────────────────────────────────────

def bollinger_bands(
    series: pd.Series,
    period: int = 20,
    num_std: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Upper, Middle, Lower Bollinger Bands.
    Returns (upper, middle, lower).
    """
    middle = sma(series, period)
    std    = series.rolling(window=period, min_periods=period).std(ddof=0)
    upper  = middle + num_std * std
    lower  = middle - num_std * std
    return upper, middle, lower


# ── ATR ───────────────────────────────────────────────────────────────────────

def atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """
    Average True Range using Wilder's smoothing.
    TR = max(H-L, |H-prevC|, |L-prevC|)
    """
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)

    alpha = 1.0 / period
    return tr.ewm(alpha=alpha, adjust=False, min_periods=period).mean()


# ── Volume SMA ────────────────────────────────────────────────────────────────

def volume_sma(volume: pd.Series, period: int = 20) -> pd.Series:
    return volume.rolling(window=period, min_periods=period).mean()


# ── Master indicator bundle ───────────────────────────────────────────────────

def compute_all_indicators(df: pd.DataFrame) -> dict:
    """
    Given an OHLCV DataFrame, return the latest scalar value for every
    indicator used by the signal engine.  Returns None for any indicator
    that lacks sufficient history.
    """
    if len(df) < 30:
        return {}

    close  = df["close"]
    high   = df["high"]
    low    = df["low"]
    volume = df["volume"]

    # EMAs
    ema20  = ema(close, 20)
    ema50  = ema(close, 50)
    ema200 = ema(close, 200) if len(df) >= 200 else ema(close, min(len(df) - 1, 100))

    # RSI
    rsi_vals = rsi(close, 14)

    # MACD
    macd_line, signal_line, histogram = macd(close, 12, 26, 9)

    # Bollinger Bands
    bb_upper, bb_middle, bb_lower = bollinger_bands(close, 20, 2.0)

    # ATR
    atr_vals = atr(high, low, close, 14)

    # Volume
    vol_sma = volume_sma(volume, 20)

    def last(s: pd.Series):
        v = s.dropna()
        return float(v.iloc[-1]) if not v.empty else None

    return {
        "close":         last(close),
        "high":          last(high),
        "low":           last(low),
        "ema20":         last(ema20),
        "ema50":         last(ema50),
        "ema200":        last(ema200),
        "rsi":           last(rsi_vals),
        "macd":          last(macd_line),
        "macd_signal":   last(signal_line),
        "macd_hist":     last(histogram),
        "bb_upper":      last(bb_upper),
        "bb_middle":     last(bb_middle),
        "bb_lower":      last(bb_lower),
        "atr":           last(atr_vals),
        "volume":        last(volume),
        "volume_sma":    last(vol_sma),
    }
