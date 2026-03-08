#!/usr/bin/env python3
"""Live test for SEC EDGAR 13F fetcher."""
import sys
from autopilot_cli.sources.sec_edgar import fetch_13f_filings, list_hedge_fund_managers

def test_list_managers():
    print("Testing list_hedge_fund_managers()...")
    managers = list_hedge_fund_managers()
    print(f"  Got {len(managers)} managers")
    return len(managers) > 0

def test_fetch_13f():
    print("Testing fetch_13f_filings (burry)...")
    try:
        filing = fetch_13f_filings("burry")
        print(f"  Filer: {filing.filer_name}")
        print(f"  Date: {filing.filing_date}")
        print(f"  Positions: {len(filing.positions)}")
        if filing.positions:
            top = sorted(filing.positions, key=lambda p: p.value, reverse=True)[0]
            print(f"  Top holding: {top.name_of_issuer} (${top.value:,})")
        return len(filing.positions) > 0
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

if __name__ == "__main__":
    results = [
        test_list_managers(),
        test_fetch_13f(),
    ]
    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} tests passed")
    sys.exit(0 if passed == total else 1)
