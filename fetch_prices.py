"""
fetch_prices.py
Fetches current market prices and FX rates, writes prices.json.
Runs via GitHub Actions every 30 min on weekdays.

APIs used (all free, no API key required):
  - CoinGecko       → BTC/EUR
  - Frankfurter.app → EUR/CZK, USD/CZK  (ECB reference rates)
  - yfinance        → ASML, RHM, VUSA, DRS, PLTR, NW0
"""

import json
import datetime
import sys
import requests
import yfinance as yf

# ── Ticker map: dashboard ID → Yahoo Finance symbol ──────────────────────────
STOCK_TICKERS = {
    "ASML": "ASML.AS",   # Euronext Amsterdam
    "RHM":  "RHM.DE",    # Frankfurt
    "VUSA": "VUSA.AS",   # Euronext Amsterdam
    "DRS":  "DRS",       # NASDAQ
    "PLTR": "PLTR",      # NYSE
    "NW0":  "NW0.AS",    # Euronext Amsterdam
}


def fetch_btc_eur() -> float:
    r = requests.get(
        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur",
        timeout=10,
    )
    r.raise_for_status()
    return float(r.json()["bitcoin"]["eur"])


def fetch_fx() -> tuple[float, float]:
    """Returns (EUR/CZK, USD/CZK)"""
    r1 = requests.get("https://api.frankfurter.app/latest?from=EUR&to=CZK", timeout=10)
    r1.raise_for_status()
    eur_czk = float(r1.json()["rates"]["CZK"])

    r2 = requests.get("https://api.frankfurter.app/latest?from=USD&to=CZK", timeout=10)
    r2.raise_for_status()
    usd_czk = float(r2.json()["rates"]["CZK"])

    return eur_czk, usd_czk


def fetch_stocks() -> dict:
    prices = {}
    for key, symbol in STOCK_TICKERS.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")  # 2d buffer for late-closing markets
            if not hist.empty:
                price = round(float(hist["Close"].iloc[-1]), 2)
                prices[key] = price
                print(f"  {key} ({symbol}): {price}")
            else:
                print(f"  {key} ({symbol}): no data returned", file=sys.stderr)
        except Exception as e:
            print(f"  {key} ({symbol}): FAILED — {e}", file=sys.stderr)
    return prices


def main():
    prices = {}
    errors = []

    print("── BTC ──────────────────────────────")
    try:
        prices["BTC"] = fetch_btc_eur()
        print(f"  BTC: €{prices['BTC']:,.0f}")
    except Exception as e:
        errors.append(f"BTC: {e}")
        print(f"  BTC: FAILED — {e}", file=sys.stderr)

    print("── FX ───────────────────────────────")
    try:
        eur_czk, usd_czk = fetch_fx()
        prices["EURCZK"] = round(eur_czk, 4)
        prices["USDCZK"] = round(usd_czk, 4)
        print(f"  EUR/CZK: {eur_czk}")
        print(f"  USD/CZK: {usd_czk}")
    except Exception as e:
        errors.append(f"FX: {e}")
        print(f"  FX: FAILED — {e}", file=sys.stderr)

    print("── Stocks ───────────────────────────")
    stock_prices = fetch_stocks()
    prices.update(stock_prices)

    prices["updated_at"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    with open("prices.json", "w") as f:
        json.dump(prices, f, indent=2)

    print("\n── Output ───────────────────────────")
    print(json.dumps(prices, indent=2))

    if errors:
        print(f"\n⚠ Partial fetch — {len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        # Exit 0 anyway — partial data is better than no commit
    else:
        print(f"\n✓ All prices fetched successfully")


if __name__ == "__main__":
    main()
