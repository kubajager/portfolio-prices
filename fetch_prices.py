"""
fetch_prices.py
Fetches current market prices and FX rates, writes prices.json.
Runs via GitHub Actions every 30 min on weekdays.

APIs used (all free, no API key required):
  - CoinGecko       → BTC/EUR
  - Frankfurter.app → EUR/CZK, USD/CZK  (ECB reference rates)
  - Yahoo Finance   → stocks via direct API call with browser headers
                      (avoids rate-limiting on GitHub Actions IPs)
"""

import json
import time
import datetime
import sys
import requests

# ── Ticker map: dashboard ID → Yahoo Finance symbol ──────────────────────────
STOCK_TICKERS = {
    "ASML": "ASML.AS",   # Euronext Amsterdam
    "RHM":  "RHM.DE",    # Frankfurt
    "VUSA": "VUSA.AS",   # Euronext Amsterdam
    "DRS":  "DRS",       # NASDAQ
    "PLTR": "PLTR",      # NYSE
    "NW0":  "CSG.AS",    # Euronext Amsterdam (CSG N.V.)
}

# Browser-like headers — prevents Yahoo Finance from blocking GitHub Actions IPs
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://finance.yahoo.com/",
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


def fetch_yahoo_price(symbol: str) -> float:
    """Fetch latest price directly from Yahoo Finance v8 API."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"interval": "1d", "range": "5d"}
    r = requests.get(url, headers=HEADERS, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
    # Filter out None values (market closed days) and return latest
    closes = [c for c in closes if c is not None]
    if not closes:
        raise ValueError(f"No close prices returned for {symbol}")
    return round(float(closes[-1]), 2)


def fetch_stocks() -> dict:
    prices = {}
    for key, symbol in STOCK_TICKERS.items():
        try:
            price = fetch_yahoo_price(symbol)
            prices[key] = price
            print(f"  {key} ({symbol}): {price}")
            time.sleep(0.3)  # be polite — avoid burst rate limiting
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
    else:
        print(f"\n✓ All prices fetched successfully")


if __name__ == "__main__":
    main()
