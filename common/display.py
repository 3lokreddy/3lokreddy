"""
display.py
Terminal rendering: colored headers, multi-timeframe tables,
trade setup boxes, and support/resistance levels.
Uses colorama + tabulate only.
"""

from __future__ import annotations
import os
from datetime import datetime
from tabulate import tabulate
from colorama import Fore, Back, Style, init

init(autoreset=True)

# ── Color shortcuts ───────────────────────────────────────────────────────────
G  = Fore.GREEN
R  = Fore.RED
Y  = Fore.YELLOW
C  = Fore.CYAN
W  = Fore.WHITE
M  = Fore.MAGENTA
DIM = Style.DIM
RST = Style.RESET_ALL
BLD = Style.BRIGHT


def _divider(char: str = "─", width: int = 72) -> str:
    return char * width


def _signal_color(signal: str) -> str:
    return {
        "BUY":     BLD + G,
        "BULLISH": G,
        "SELL":    BLD + R,
        "BEARISH": R,
        "NEUTRAL": Y,
    }.get(signal, W)


def _strength_bar(score: float, width: int = 24) -> str:
    """Unicode progress bar; green for long, red for short."""
    filled = int(abs(score) * width)
    filled = min(filled, width)
    empty  = width - filled
    color  = G if score >= 0 else R
    return color + "█" * filled + DIM + "░" * empty + RST


# ── Header ────────────────────────────────────────────────────────────────────

def print_header(
    symbol: str,
    current_price: float,
    overall: dict,
    is_demo: bool = False,
) -> None:
    signal        = overall["signal"]
    strength_pct  = overall["strength_pct"]
    strength_lbl  = overall["strength_label"]
    score         = overall["score"]
    bullish_cnt   = overall["bullish_count"]
    bearish_cnt   = overall["bearish_count"]
    neutral_cnt   = overall["neutral_count"]
    dom_tf        = overall["dominant_tf"]
    ts            = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    sc = _signal_color(signal)
    bar = _strength_bar(score)
    demo_tag = f"{Y} [DEMO DATA]{RST}" if is_demo else ""

    print()
    print(BLD + C + _divider("═"))
    print(f"  {BLD}{W}{symbol}  |  {C}${current_price:,.2f}  {DIM}|  {ts}{demo_tag}")
    print(C + _divider("─"))
    print(f"  Signal : {sc}{BLD}{signal:8s}{RST}  {strength_lbl}  ({strength_pct}%)")
    print(f"  Score  : {bar}  {score:+.3f}")
    print(f"  Count  : {G}Bullish {bullish_cnt}{RST}  {R}Bearish {bearish_cnt}{RST}  {Y}Neutral {neutral_cnt}{RST}  (across 6 TFs)")
    print(f"  Driver : {C}{dom_tf}{RST} timeframe has strongest confluence")
    print(BLD + C + _divider("═"))


# ── Timeframe table ───────────────────────────────────────────────────────────

def _ema_arrow(ema_score: float) -> str:
    if   ema_score >  0.5: return G + "↑↑↑" + RST
    elif ema_score >  0.1: return G + " ↑ " + RST
    elif ema_score < -0.5: return R + "↓↓↓" + RST
    elif ema_score < -0.1: return R + " ↓ " + RST
    else:                  return Y + " ─ " + RST


def _rsi_cell(rsi_val) -> str:
    if rsi_val is None:
        return "  N/A "
    v = f"{rsi_val:.1f}"
    if   rsi_val < 30:  return G + v + RST
    elif rsi_val > 70:  return R + v + RST
    else:               return W + v + RST


def _macd_cell(macd_score: float) -> str:
    if   macd_score > 0.4:  return G + "▲ Bull" + RST
    elif macd_score > 0:    return G + "▲ Weak" + RST
    elif macd_score < -0.4: return R + "▼ Bear" + RST
    else:                    return R + "▼ Weak" + RST


def _bb_cell(close, upper, lower) -> str:
    if any(v is None for v in [close, upper, lower]):
        return "  N/A "
    bw = upper - lower
    if bw <= 0:
        return "  MID "
    pct_b = (close - lower) / bw
    if   pct_b < 0.20: return G + f"LOW {pct_b*100:.0f}%" + RST
    elif pct_b > 0.80: return R + f"HI  {pct_b*100:.0f}%" + RST
    else:              return W + f"MID {pct_b*100:.0f}%" + RST


def _vol_cell(volume, vol_sma) -> str:
    if volume is None or vol_sma is None or vol_sma == 0:
        return "  N/A "
    ratio = volume / vol_sma
    if   ratio > 2.0: return G + f"↑↑ {ratio:.1f}x" + RST
    elif ratio > 1.2: return G + f"↑  {ratio:.1f}x" + RST
    elif ratio > 0.8: return W + f"   {ratio:.1f}x" + RST
    else:             return DIM + f"↓  {ratio:.1f}x" + RST


def print_timeframe_table(
    tf_scores: dict[str, dict],
    all_indicators: dict[str, dict],
) -> None:
    print(f"\n{BLD}{C}  MULTI-TIMEFRAME ANALYSIS{RST}")
    print(C + "  " + _divider("─", 70))

    rows = []
    for tf in ("15m", "1h", "4h", "1d", "1w", "1M"):
        ts  = tf_scores.get(tf, {})
        ind = all_indicators.get(tf, {})
        if not ts:
            continue

        sig      = ts.get("signal", "NEUTRAL")
        strength = ts.get("strength", "WEAK")
        sc       = _signal_color(sig)
        bar      = _strength_bar(ts.get("score", 0), width=12)

        rows.append([
            BLD + W + tf + RST,
            _rsi_cell(ind.get("rsi")),
            _macd_cell(ts.get("macd_score", 0)),
            _bb_cell(ind.get("close"), ind.get("bb_upper"), ind.get("bb_lower")),
            _ema_arrow(ts.get("ema_score", 0)),
            _vol_cell(ind.get("volume"), ind.get("volume_sma")),
            sc + f"{sig:8s}" + RST,
            bar + f" {strength}",
        ])

    headers = [
        BLD + "TF" + RST,
        BLD + " RSI " + RST,
        BLD + "  MACD  " + RST,
        BLD + "  BB Pos  " + RST,
        BLD + "EMA" + RST,
        BLD + " Volume " + RST,
        BLD + " Signal " + RST,
        BLD + " Strength" + RST,
    ]

    print(tabulate(rows, headers=headers, tablefmt="simple", colalign=(
        "left", "right", "left", "left", "center", "right", "left", "left"
    )))


# ── Trade setup box ───────────────────────────────────────────────────────────

def print_trade_setup(setup: dict | None) -> None:
    print(f"\n{BLD}{C}  TRADE SETUP & POSITION SIZING{RST}")
    print(C + "  " + _divider("─", 70))

    if setup is None:
        print(f"  {Y}No directional trade setup — signal is NEUTRAL.{RST}")
        print(f"  {DIM}Wait for a stronger confluence before entering.{RST}")
        return

    direction = setup["direction"]
    dc = G if direction == "LONG" else R
    arrow = "▲" if direction == "LONG" else "▼"

    entry  = setup["entry"]
    sl     = setup["stop_loss"]
    tp1    = setup["take_profit_1"]
    tp2    = setup["take_profit_2"]
    sl_pct = abs(entry - sl) / entry * 100
    tp1_pct = abs(tp1 - entry) / entry * 100
    tp2_pct = abs(tp2 - entry) / entry * 100

    units    = setup.get("position_units", 0)
    notional = setup.get("notional_usd", 0)
    risk_usd = setup.get("risk_amount", 0)
    leverage = setup.get("leverage_required", 0)
    atr      = setup.get("atr", 0)
    atr_tf   = setup.get("atr_tf", "1h")
    account  = setup.get("account", 100_000)
    risk_pct = setup.get("risk_pct", 0.01)

    rows = [
        ["Direction",     dc + f"{arrow} {direction}" + RST,                    ""],
        ["Entry Price",   W  + f"${entry:,.2f}" + RST,                          ""],
        ["Stop Loss",     R  + f"${sl:,.2f}" + RST,       DIM + f"({sl_pct:.2f}% away)" + RST],
        ["Take Profit 1", G  + f"${tp1:,.2f}" + RST,      DIM + f"({tp1_pct:.2f}% | 1:{setup['risk_reward_1']:.0f} R/R)" + RST],
        ["Take Profit 2", G  + f"${tp2:,.2f}" + RST,      DIM + f"({tp2_pct:.2f}% | 1:{setup['risk_reward_2']:.0f} R/R)" + RST],
        ["──────────────", "", ""],
        ["Account Size",  W  + f"${account:,.0f}" + RST,  ""],
        ["Risk Per Trade",Y  + f"${risk_usd:,.2f} ({risk_pct*100:.1f}%)" + RST, ""],
        ["Position Size", BLD + W + f"{units:.6f} units" + RST, DIM + f"= ${notional:,.2f} notional" + RST],
        ["Leverage Req.", C  + f"{leverage:.2f}×" + RST,  ""],
        ["ATR ({})".format(atr_tf), DIM + f"${atr:,.2f}" + RST, DIM + f"(×{setup.get('atr_mult',1.5)} for stop)" + RST],
    ]

    for row in rows:
        if row[0].startswith("──"):
            print(f"  {DIM}" + _divider("─", 68) + RST)
        else:
            label = f"{BLD}{row[0]:18s}{RST}"
            val   = f"{row[1]:28s}"
            note  = row[2]
            print(f"  {label}  {val}  {note}")


# ── Support / Resistance ──────────────────────────────────────────────────────

def print_support_resistance(
    all_indicators: dict[str, dict],
    current_price: float,
) -> None:
    print(f"\n{BLD}{C}  KEY SUPPORT & RESISTANCE LEVELS{RST}")
    print(C + "  " + _divider("─", 70))

    levels: list[tuple[float, str, str]] = []   # (price, label, direction)

    # Collect levels from indicators
    _add_level = levels.append
    ind_1h = all_indicators.get("1h", {})
    ind_4h = all_indicators.get("4h", {})
    ind_1d = all_indicators.get("1d", {})
    ind_1w = all_indicators.get("1w", {})

    for ind, tf_label in [(ind_1h, "1h"), (ind_4h, "4h"), (ind_1d, "1d"), (ind_1w, "1w")]:
        for key, label in [("ema20","EMA20"), ("ema50","EMA50"), ("ema200","EMA200")]:
            v = ind.get(key)
            if v:
                _add_level((v, f"EMA{key[3:]}({tf_label})", "S" if v < current_price else "R"))
        for key, label in [("bb_upper","BB Upper"), ("bb_lower","BB Lower")]:
            v = ind.get(key)
            if v:
                _add_level((v, f"{label}({tf_label})", "S" if v < current_price else "R"))

    # Filter to within 12% of current price and deduplicate nearby levels
    filtered: list[tuple[float, str, str]] = []
    for price, label, direction in sorted(levels, key=lambda x: x[0]):
        pct_away = abs(price - current_price) / current_price * 100
        if pct_away > 12:
            continue
        # Deduplicate: skip if within 0.5% of an already-added level
        too_close = any(abs(p - price) / current_price < 0.005 for p, _, _ in filtered)
        if not too_close:
            filtered.append((price, label, direction))

    if not filtered:
        print(f"  {DIM}No significant levels within 12% of current price.{RST}")
        return

    # Sort: support below (descending), resistance above (ascending)
    supports    = sorted([(p, l, d) for p, l, d in filtered if d == "S"], reverse=True)
    resistances = sorted([(p, l, d) for p, l, d in filtered if d == "R"])

    if resistances:
        print(f"  {BLD}{R}Resistance Levels:{RST}")
        for price, label, _ in resistances[:4]:
            pct = (price - current_price) / current_price * 100
            print(f"    {R}${price:,.2f}{RST}  {DIM}{label:25s}{RST}  {pct:+.2f}%")

    print(f"  {DIM}{'─'*50}{RST}")
    print(f"  {BLD}{C}  → Current Price: ${current_price:,.2f}{RST}")
    print(f"  {DIM}{'─'*50}{RST}")

    if supports:
        print(f"  {BLD}{G}Support Levels:{RST}")
        for price, label, _ in supports[:4]:
            pct = (price - current_price) / current_price * 100
            print(f"    {G}${price:,.2f}{RST}  {DIM}{label:25s}{RST}  {pct:+.2f}%")

    print()
