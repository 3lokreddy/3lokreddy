"""
btc_bot.py  —  Bitcoin (BTC/USDT) Trading Analysis Bot
─────────────────────────────────────────────────────────────────────────────
Delivers instant trade recommendations across 6 timeframes:
  15m  |  1h  |  4h  |  1d  |  1w  |  1M

Indicators per timeframe:
  RSI · MACD · EMA 20/50/200 · Bollinger Bands · ATR · Volume

Position sizing:  ATR-based stops  |  Fixed-fractional risk
Default account:  $100,000  |  Risk: 1% per trade

Usage:
  python btc_bot.py
  python btc_bot.py --account 50000 --risk 2
"""

import sys
import argparse
from colorama import Fore, Style, init

init(autoreset=True)

from common.data_fetcher  import fetch_all_timeframes, fetch_current_price
from common.indicators    import compute_all_indicators
from common.signals       import score_timeframe, compute_overall_signal, generate_trade_setup
from common.display       import (
    print_header, print_timeframe_table,
    print_trade_setup, print_support_resistance,
)

# ── Bot configuration ─────────────────────────────────────────────────────────
SYMBOL       = "BTCUSDT"
DISPLAY_NAME = "BTC/USDT  (Bitcoin)"
ACCOUNT_SIZE = 100_000.0
RISK_PCT     = 0.01            # 1% risk per trade


# ── Core analysis pipeline ────────────────────────────────────────────────────

def run_btc_bot(account_size: float = ACCOUNT_SIZE, risk_pct: float = RISK_PCT) -> None:
    print(f"\n{Style.BRIGHT}{Fore.CYAN}  Loading {DISPLAY_NAME} analysis...{Style.RESET_ALL}")

    # 1. Fetch OHLCV data for all 6 timeframes
    all_data, is_demo = fetch_all_timeframes(SYMBOL)

    # Try to get a live price for the header; fall back to last synthetic close
    current_price = fetch_current_price(SYMBOL)
    if current_price is None:
        last_tf = "1d" if "1d" in all_data else list(all_data.keys())[0]
        current_price = float(all_data[last_tf]["close"].iloc[-1])

    # 2. Compute indicators for every timeframe
    all_indicators: dict = {}
    for tf, df in all_data.items():
        all_indicators[tf] = compute_all_indicators(df)

    # 3. Score each timeframe
    tf_scores: dict = {}
    for tf, ind in all_indicators.items():
        tf_scores[tf] = score_timeframe(ind)

    # 4. Compute the overall multi-timeframe signal
    overall = compute_overall_signal(tf_scores, all_indicators)

    # 5. Generate trade setup with position sizing
    setup = generate_trade_setup(
        symbol=SYMBOL,
        overall=overall,
        all_indicators=all_indicators,
        account_size=account_size,
        risk_pct=risk_pct,
    )

    # ── Output ────────────────────────────────────────────────────────────────
    print_header(DISPLAY_NAME, current_price, overall, is_demo=is_demo)
    print_timeframe_table(tf_scores, all_indicators)
    print_trade_setup(setup)
    print_support_resistance(all_indicators, current_price)

    # Risk disclaimer
    print(
        f"{Style.DIM}  DISCLAIMER: This tool is for educational purposes only. "
        f"Not financial advice.\n"
        f"  All recommendations are based on technical analysis and carry risk.\n"
        f"{Style.RESET_ALL}"
    )


# ── CLI entry ─────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="BTC/USDT Trading Analysis Bot — instant multi-timeframe recommendations"
    )
    p.add_argument(
        "--account", type=float, default=ACCOUNT_SIZE,
        help=f"Account size in USD (default: {ACCOUNT_SIZE:,.0f})"
    )
    p.add_argument(
        "--risk", type=float, default=RISK_PCT * 100,
        help="Risk per trade as %% (default: 1.0)"
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_btc_bot(
        account_size=args.account,
        risk_pct=args.risk / 100.0,
    )
