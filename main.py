"""
main.py  —  Combined BTC + ETH Trading Analysis Runner
─────────────────────────────────────────────────────────────────────────────
Runs BtcBot and/or EthBot sequentially and prints full analysis for each.

Usage:
  python main.py                         # run both
  python main.py --btc                   # BTC only
  python main.py --eth                   # ETH only
  python main.py --account 100000        # custom account size
  python main.py --risk 2                # 2% risk per trade
  python main.py --btc --account 50000 --risk 1.5
"""

import argparse
from colorama import Fore, Style, init

init(autoreset=True)


def _banner() -> None:
    print(Style.BRIGHT + Fore.CYAN + """
╔══════════════════════════════════════════════════════════════════════════╗
║          CRYPTO TRADING ANALYSIS BOT  —  BTC & ETH                     ║
║   Multi-Timeframe  |  RSI · MACD · EMA · Bollinger · ATR · Volume      ║
║   Timeframes: 15m  1h  4h  1D  1W  1M                                  ║
║   Position Sizing: ATR-based stops  |  Fixed-fractional risk            ║
╚══════════════════════════════════════════════════════════════════════════╝
""" + Style.RESET_ALL)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="BTC & ETH trading analysis with multi-timeframe confluence"
    )
    p.add_argument("--btc",     action="store_true", help="Run BTC bot only")
    p.add_argument("--eth",     action="store_true", help="Run ETH bot only")
    p.add_argument("--account", type=float, default=100_000.0,
                   help="Account size in USD (default: 100000)")
    p.add_argument("--risk",    type=float, default=1.0,
                   help="Risk per trade as %% (default: 1.0)")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    _banner()

    run_btc = args.btc or (not args.btc and not args.eth)
    run_eth = args.eth or (not args.btc and not args.eth)

    account  = args.account
    risk_pct = args.risk / 100.0

    if run_btc:
        from btc_bot import run_btc_bot
        run_btc_bot(account_size=account, risk_pct=risk_pct)

    if run_btc and run_eth:
        print(
            f"\n{Style.BRIGHT}{Fore.CYAN}"
            f"{'═'*72}\n"
            f"{'═'*72}{Style.RESET_ALL}\n"
        )

    if run_eth:
        from eth_bot import run_eth_bot
        run_eth_bot(account_size=account, risk_pct=risk_pct)


if __name__ == "__main__":
    main()
