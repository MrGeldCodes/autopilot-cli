#!/usr/bin/env python3
"""Live test for Capitol Trades scraper."""
import sys
from autopilot_cli.sources.capitol_trades import fetch_politician_trades, fetch_trades_by_ticker, list_politicians

def test_politician_trades():
    print("Testing fetch_politician_trades (nancy-pelosi)...")
    trades = fetch_politician_trades("nancy-pelosi", page_size=5)
    print(f"  Got {len(trades)} trades")
    if trades:
        t = trades[0]
        print(f"  First: {t.politician} | {t.ticker} | {t.trade_type} | {t.amount}")
    return len(trades) > 0

def test_ticker_trades():
    print("Testing fetch_trades_by_ticker (NVDA)...")
    trades = fetch_trades_by_ticker("NVDA", page_size=5)
    print(f"  Got {len(trades)} trades")
    if trades:
        t = trades[0]
        print(f"  First: {t.politician} | {t.ticker} | {t.trade_type}")
    return len(trades) > 0

def test_list_politicians():
    print("Testing list_politicians()...")
    politicians = list_politicians()
    print(f"  Got {len(politicians)} politicians")
    return len(politicians) > 0

if __name__ == "__main__":
    results = [
        test_list_politicians(),
        test_politician_trades(),
        test_ticker_trades(),
    ]
    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} tests passed")
    sys.exit(0 if passed == total else 1)
