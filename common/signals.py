"""
signals.py
Multi-timeframe confluence scoring, BUY/SELL/NEUTRAL determination,
and trade-setup generation.
"""

from __future__ import annotations
from common.indicators import compute_all_indicators

# ── Timeframe weights (must sum to 1.0) ───────────────────────────────────────
TF_WEIGHTS: dict[str, float] = {
    "15m": 0.05,
    "1h":  0.10,
    "4h":  0.20,
    "1d":  0.30,
    "1w":  0.25,
    "1M":  0.10,
}

# ── Individual indicator scorers (each returns a value in [-1, +1]) ───────────

def score_ema(close, ema20, ema50, ema200) -> float:
    """Trend alignment: +1 fully bullish, -1 fully bearish."""
    if any(v is None for v in [close, ema20, ema50, ema200]):
        return 0.0
    score = 0.0
    score += 1.0 if close  > ema20  else -1.0
    score += 1.0 if ema20  > ema50  else -1.0
    score += 1.0 if ema50  > ema200 else -1.0
    return score / 3.0


def score_rsi(rsi_val) -> float:
    """RSI-based momentum score."""
    if rsi_val is None:
        return 0.0
    if   rsi_val < 20:  return  1.00
    elif rsi_val < 30:  return  0.75
    elif rsi_val < 40:  return  0.35
    elif rsi_val < 60:  return  0.00
    elif rsi_val < 70:  return -0.35
    elif rsi_val < 80:  return -0.75
    else:               return -1.00


def score_macd(macd_val, signal_val, histogram) -> float:
    """MACD crossover + histogram direction."""
    if any(v is None for v in [macd_val, signal_val, histogram]):
        return 0.0
    cross  = 1.0 if macd_val > signal_val else -1.0
    hist_d = 1.0 if histogram > 0         else -1.0
    return (cross + hist_d) / 2.0


def score_bb(close, upper, lower) -> float:
    """Bollinger Band percent-B position."""
    if any(v is None for v in [close, upper, lower]):
        return 0.0
    band_width = upper - lower
    if band_width <= 0:
        return 0.0
    pct_b = (close - lower) / band_width          # 0 = at lower, 1 = at upper
    if   pct_b < 0.0:   return  1.00
    elif pct_b < 0.10:  return  0.75
    elif pct_b < 0.40:  return  0.25
    elif pct_b < 0.60:  return  0.00
    elif pct_b < 0.90:  return -0.25
    elif pct_b < 1.00:  return -0.75
    else:               return -1.00


def volume_multiplier(volume_current, volume_sma_val) -> float:
    """
    Volume confirmation multiplier [0.7 – 1.0].
    High volume amplifies signals; low volume dampens them.
    """
    if volume_current is None or volume_sma_val is None or volume_sma_val == 0:
        return 0.85
    ratio = volume_current / volume_sma_val
    if   ratio > 2.0: return 1.00
    elif ratio > 1.5: return 0.95
    elif ratio > 1.2: return 0.90
    elif ratio > 0.8: return 0.85
    else:             return 0.75


# ── Per-timeframe scoring ─────────────────────────────────────────────────────

def score_timeframe(ind: dict) -> dict:
    """
    Combine all indicator scores into a single [-1,+1] value for this timeframe.
    Returns a result dict with individual sub-scores and the aggregate.
    """
    if not ind:
        return {"score": 0.0, "signal": "NEUTRAL", "strength": "WEAK",
                "ema_score": 0.0, "rsi_score": 0.0,
                "macd_score": 0.0, "bb_score": 0.0}

    ema_s  = score_ema(ind.get("close"), ind.get("ema20"),
                       ind.get("ema50"), ind.get("ema200"))
    rsi_s  = score_rsi(ind.get("rsi"))
    macd_s = score_macd(ind.get("macd"), ind.get("macd_signal"), ind.get("macd_hist"))
    bb_s   = score_bb(ind.get("close"), ind.get("bb_upper"), ind.get("bb_lower"))
    vol_m  = volume_multiplier(ind.get("volume"), ind.get("volume_sma"))

    # Weighted average of directional indicators
    raw = (ema_s * 0.35 + rsi_s * 0.20 + macd_s * 0.25 + bb_s * 0.20)
    combined = raw * vol_m
    combined = max(-1.0, min(1.0, combined))

    if   combined >  0.25: signal = "BULLISH"
    elif combined < -0.25: signal = "BEARISH"
    else:                   signal = "NEUTRAL"

    abs_c = abs(combined)
    if   abs_c > 0.65: strength = "STRONG"
    elif abs_c > 0.40: strength = "MODERATE"
    else:               strength = "WEAK"

    return {
        "score":      combined,
        "signal":     signal,
        "strength":   strength,
        "ema_score":  ema_s,
        "rsi_score":  rsi_s,
        "macd_score": macd_s,
        "bb_score":   bb_s,
        "vol_mult":   vol_m,
    }


# ── Overall signal ────────────────────────────────────────────────────────────

def compute_overall_signal(
    tf_scores: dict[str, dict],
    all_indicators: dict[str, dict],
) -> dict:
    """
    Weighted combination of per-timeframe scores → final BUY/SELL/NEUTRAL.
    """
    weighted_sum = 0.0
    total_weight = 0.0
    bullish = bearish = neutral = 0

    for tf, w in TF_WEIGHTS.items():
        ts = tf_scores.get(tf, {})
        s  = ts.get("score", 0.0)
        weighted_sum += s * w
        total_weight += w

        sig = ts.get("signal", "NEUTRAL")
        if   sig == "BULLISH": bullish += 1
        elif sig == "BEARISH": bearish += 1
        else:                  neutral += 1

    overall_score = weighted_sum / total_weight if total_weight else 0.0

    if   overall_score >  0.35: signal = "BUY"
    elif overall_score < -0.35: signal = "SELL"
    else:                        signal = "NEUTRAL"

    strength_pct = min(100, int(abs(overall_score) * 100 / 0.65 * 100) // 100)
    strength_pct = min(100, int(abs(overall_score) / 0.65 * 100))

    if   abs(overall_score) > 0.65: strength_label = "STRONG"
    elif abs(overall_score) > 0.40: strength_label = "MODERATE"
    else:                            strength_label = "WEAK"

    # Dominant timeframe (highest absolute weighted contribution)
    dom_tf = max(TF_WEIGHTS, key=lambda tf: abs(tf_scores.get(tf, {}).get("score", 0)) * TF_WEIGHTS[tf])

    return {
        "score":          overall_score,
        "signal":         signal,
        "strength_pct":   strength_pct,
        "strength_label": strength_label,
        "bullish_count":  bullish,
        "bearish_count":  bearish,
        "neutral_count":  neutral,
        "dominant_tf":    dom_tf,
    }


# ── Trade setup generation ────────────────────────────────────────────────────

def generate_trade_setup(
    symbol: str,
    overall: dict,
    all_indicators: dict[str, dict],
    account_size: float = 100_000.0,
    risk_pct: float = 0.01,
) -> dict | None:
    """
    Generates a concrete trade plan for BUY/SELL signals.
    Returns None for NEUTRAL.
    """
    from common.position_sizing import full_trade_plan

    signal = overall.get("signal", "NEUTRAL")
    if signal == "NEUTRAL":
        return None

    # Pick ATR from the most relevant timeframe (prefer 1h, fallback 4h, 1d)
    atr_val = None
    for tf in ("1h", "4h", "1d"):
        ind = all_indicators.get(tf, {})
        if ind.get("atr") and ind.get("close"):
            atr_val = ind["atr"]
            atr_tf  = tf
            entry   = ind["close"]
            break

    if atr_val is None or entry is None:
        return None

    direction = "LONG" if signal == "BUY" else "SHORT"
    plan = full_trade_plan(
        account=account_size,
        risk_pct=risk_pct,
        entry=entry,
        atr=atr_val,
        direction=direction,
        atr_mult=1.5,
    )
    plan["atr_tf"]    = atr_tf
    plan["direction"] = direction
    plan["signal"]    = signal
    plan["symbol"]    = symbol
    plan["risk_pct"]  = risk_pct
    plan["account"]   = account_size
    return plan
