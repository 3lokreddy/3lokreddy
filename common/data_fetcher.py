"""
data_fetcher.py
Attempts to pull OHLCV data from live exchanges; falls back to a realistic
numpy-based synthetic generator when all APIs are blocked.
"""

import time
import json
import urllib.request
import urllib.error
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from colorama import Fore, Style, init

init(autoreset=True)

# ── Timeframe config ────────────────────────────────────────────────────────
TIMEFRAMES = ["15m", "1h", "4h", "1d", "1w", "1M"]

TF_MINUTES = {
    "15m": 15,
    "1h":  60,
    "4h":  240,
    "1d":  1440,
    "1w":  10080,
    "1M":  43200,
}

# Annualised volatility → per-candle σ fraction
TF_VOLATILITY = {
    "15m": 0.0028,
    "1h":  0.0060,
    "4h":  0.0130,
    "1d":  0.0220,
    "1w":  0.0480,
    "1M":  0.0950,
}

# Base prices for demo mode
BASE_PRICES = {
    "BTCUSDT": 65_800.0,
    "ETHUSDT":  3_260.0,
}

NUM_CANDLES = 200


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get(url: str, timeout: int = 8) -> dict | list | None:
    """Single HTTP GET with a short timeout; returns parsed JSON or None."""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "CryptoBot/1.0", "Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _parse_klines(raw: list) -> pd.DataFrame:
    """Convert Binance/Bybit-style kline list → OHLCV DataFrame."""
    df = pd.DataFrame(raw, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_vol", "trades", "taker_base", "taker_quote", "ignore",
    ])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df.set_index("open_time", inplace=True)
    return df[["open", "high", "low", "close", "volume"]]


# ── Live data fetchers (tried in order) ──────────────────────────────────────

_INTERVAL_MAP_BINANCE = {
    "15m": "15m", "1h": "1h", "4h": "4h",
    "1d": "1d", "1w": "1w", "1M": "1M",
}

def _fetch_binance(symbol: str, interval: str, limit: int = NUM_CANDLES) -> pd.DataFrame | None:
    bi = _INTERVAL_MAP_BINANCE.get(interval)
    if not bi:
        return None
    url = (f"https://api.binance.com/api/v3/klines"
           f"?symbol={symbol}&interval={bi}&limit={limit}")
    raw = _get(url)
    if raw and isinstance(raw, list) and len(raw) > 20:
        return _parse_klines(raw)
    return None


_INTERVAL_MAP_BYBIT = {
    "15m": "15", "1h": "60", "4h": "240",
    "1d": "D", "1w": "W", "1M": "M",
}

def _fetch_bybit(symbol: str, interval: str, limit: int = NUM_CANDLES) -> pd.DataFrame | None:
    bi = _INTERVAL_MAP_BYBIT.get(interval)
    if not bi:
        return None
    url = (f"https://api.bybit.com/v5/market/kline"
           f"?category=spot&symbol={symbol}&interval={bi}&limit={limit}")
    data = _get(url)
    if not data or data.get("retCode") != 0:
        return None
    rows = data.get("result", {}).get("list", [])
    if len(rows) < 20:
        return None
    # Bybit returns newest first: [timestamp, open, high, low, close, volume, ...]
    records = []
    for r in reversed(rows):
        records.append([int(r[0]), float(r[1]), float(r[2]), float(r[3]),
                        float(r[4]), float(r[5]), 0, 0, 0, 0, 0, 0])
    return _parse_klines(records)


_INTERVAL_MAP_KRAKEN = {
    "15m": 15, "1h": 60, "4h": 240,
    "1d": 1440, "1w": 10080,
}
_KRAKEN_SYMBOLS = {"BTCUSDT": "XBTUSD", "ETHUSDT": "ETHUSD"}

def _fetch_kraken(symbol: str, interval: str, limit: int = NUM_CANDLES) -> pd.DataFrame | None:
    ki = _INTERVAL_MAP_KRAKEN.get(interval)
    ks = _KRAKEN_SYMBOLS.get(symbol)
    if ki is None or ks is None:          # Kraken has no monthly candle
        return None
    url = f"https://api.kraken.com/0/public/OHLC?pair={ks}&interval={ki}"
    data = _get(url)
    if not data or data.get("error"):
        return None
    result = data.get("result", {})
    key = [k for k in result if k != "last"]
    if not key:
        return None
    rows = result[key[0]][-limit:]
    records = []
    for r in rows:
        ts_ms = int(r[0]) * 1000
        o, h, l, c, v = float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[6])
        records.append([ts_ms, o, h, l, c, v, 0, 0, 0, 0, 0, 0])
    if len(records) < 20:
        return None
    return _parse_klines(records)


def fetch_klines(symbol: str, interval: str, limit: int = NUM_CANDLES) -> pd.DataFrame | None:
    """Try each live exchange in turn; return None if all fail."""
    for fetcher in (_fetch_binance, _fetch_bybit, _fetch_kraken):
        df = fetcher(symbol, interval, limit)
        if df is not None and len(df) >= 20:
            return df
        time.sleep(0.2)
    return None


def fetch_current_price(symbol: str) -> float | None:
    # Binance
    data = _get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}")
    if data and "price" in data:
        return float(data["price"])
    # Bybit
    data = _get(f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={symbol}")
    if data and data.get("retCode") == 0:
        items = data.get("result", {}).get("list", [])
        if items:
            return float(items[0]["lastPrice"])
    return None


# ── Synthetic data generator ──────────────────────────────────────────────────

def generate_mock_data(symbol: str, num_candles: int = NUM_CANDLES) -> dict[str, pd.DataFrame]:
    """
    Produce realistic OHLCV DataFrames for all timeframes using a
    geometric Brownian motion random walk seeded per symbol.
    """
    seed = 42 if "BTC" in symbol else 99
    rng = np.random.default_rng(seed)
    base = BASE_PRICES.get(symbol, 1_000.0)
    result: dict[str, pd.DataFrame] = {}

    for tf in TIMEFRAMES:
        sigma = TF_VOLATILITY[tf]
        drift = 0.0001                          # slight upward drift

        # Build log-returns → price series
        log_rets = rng.normal(drift, sigma, num_candles)
        closes = base * np.exp(np.cumsum(log_rets))

        # OHLC from closes
        hl_range = closes * sigma * 1.8
        highs  = closes + rng.uniform(0.1, 1.0, num_candles) * hl_range
        lows   = closes - rng.uniform(0.1, 1.0, num_candles) * hl_range
        opens  = np.roll(closes, 1)
        opens[0] = base

        # Volume with occasional spikes
        base_vol = (1e8 / closes.mean()) if "BTC" in symbol else (5e8 / closes.mean())
        volumes  = rng.lognormal(np.log(base_vol), 0.6, num_candles)
        spike_idx = rng.integers(0, num_candles, size=int(num_candles * 0.05))
        volumes[spike_idx] *= rng.uniform(2.5, 5.0, size=len(spike_idx))

        # Timestamps (most recent = now)
        delta = timedelta(minutes=TF_MINUTES[tf])
        end_time = datetime.utcnow()
        timestamps = [end_time - delta * (num_candles - 1 - i) for i in range(num_candles)]

        df = pd.DataFrame({
            "open":   opens,
            "high":   highs,
            "low":    lows,
            "close":  closes,
            "volume": volumes,
        }, index=pd.DatetimeIndex(timestamps, name="open_time"))

        # Ensure no negative lows
        df["low"] = df[["low", "open", "close"]].min(axis=1) * 0.998
        df["high"] = df[["high", "open", "close"]].max(axis=1) * 1.002
        result[tf] = df

    return result


# ── Main entry point ──────────────────────────────────────────────────────────

def fetch_all_timeframes(symbol: str) -> tuple[dict[str, pd.DataFrame], bool]:
    """
    Returns (data_dict, is_demo).
    Tries live APIs first; if all 6 timeframes fail, returns synthetic data.
    """
    live_data: dict[str, pd.DataFrame] = {}
    for tf in TIMEFRAMES:
        df = fetch_klines(symbol, tf)
        if df is not None:
            live_data[tf] = df

    if live_data:                           # got at least some live data
        # Fill missing timeframes with synthetic for those intervals
        if len(live_data) < len(TIMEFRAMES):
            mock = generate_mock_data(symbol)
            for tf in TIMEFRAMES:
                if tf not in live_data:
                    live_data[tf] = mock[tf]
        return live_data, False

    # All APIs blocked → full demo mode
    print(
        f"\n{Fore.YELLOW}{'─'*60}\n"
        f"  [DEMO MODE]  All live APIs are unreachable.\n"
        f"  Using realistic synthetic OHLCV data for {symbol}.\n"
        f"  All indicator calculations and trade setups are real.\n"
        f"{'─'*60}{Style.RESET_ALL}\n"
    )
    return generate_mock_data(symbol), True
