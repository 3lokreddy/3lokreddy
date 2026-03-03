"""
position_sizing.py
ATR-based stop placement and fixed-fractional position size calculator.

Default account: $100,000
Default risk:      1 % per trade
Stop multiplier:   1.5× ATR
R:R targets:       TP1 = 1:2,  TP2 = 1:3
"""

from __future__ import annotations


def calculate_atr_stops(
    entry: float,
    atr: float,
    direction: str,          # "LONG" or "SHORT"
    atr_mult: float = 1.5,
    rr1: float = 2.0,
    rr2: float = 3.0,
) -> dict:
    """
    Place SL and two TPs relative to entry using ATR multiples.

    Returns
    -------
    {
        stop_loss, take_profit_1, take_profit_2,
        stop_distance, tp1_distance, tp2_distance,
        risk_reward_1, risk_reward_2
    }
    """
    stop_dist = atr * atr_mult
    tp1_dist  = stop_dist * rr1
    tp2_dist  = stop_dist * rr2

    if direction == "LONG":
        sl  = entry - stop_dist
        tp1 = entry + tp1_dist
        tp2 = entry + tp2_dist
    else:                           # SHORT
        sl  = entry + stop_dist
        tp1 = entry - tp1_dist
        tp2 = entry - tp2_dist

    return {
        "entry":          entry,
        "stop_loss":      sl,
        "take_profit_1":  tp1,
        "take_profit_2":  tp2,
        "stop_distance":  stop_dist,
        "tp1_distance":   tp1_dist,
        "tp2_distance":   tp2_dist,
        "risk_reward_1":  rr1,
        "risk_reward_2":  rr2,
    }


def calculate_position_size(
    account_size: float,
    risk_pct: float,          # e.g. 0.01 = 1 %
    entry: float,
    stop_loss: float,
) -> dict:
    """
    Fixed-fractional position sizing.

    position_units = risk_amount / stop_distance
    notional       = position_units × entry

    Returns
    -------
    {
        risk_amount, stop_distance_usd, position_units,
        notional_usd, leverage_required, portfolio_pct
    }
    """
    risk_amount   = account_size * risk_pct
    stop_dist_usd = abs(entry - stop_loss)

    if stop_dist_usd == 0:
        return {}

    units     = risk_amount / stop_dist_usd
    notional  = units * entry
    leverage  = notional / account_size
    port_pct  = (notional / account_size) * 100.0

    return {
        "risk_amount":       risk_amount,
        "stop_distance_usd": stop_dist_usd,
        "position_units":    units,
        "notional_usd":      notional,
        "leverage_required": leverage,
        "portfolio_pct":     port_pct,
    }


def full_trade_plan(
    account: float,
    risk_pct: float,
    entry: float,
    atr: float,
    direction: str,
    atr_mult: float = 1.5,
    rr1: float = 2.0,
    rr2: float = 3.0,
) -> dict:
    """
    One-call convenience wrapper that returns the combined stop + sizing dict.
    """
    stops   = calculate_atr_stops(entry, atr, direction, atr_mult, rr1, rr2)
    sizing  = calculate_position_size(account, risk_pct, entry, stops["stop_loss"])
    return {**stops, **sizing, "atr": atr, "atr_mult": atr_mult}
