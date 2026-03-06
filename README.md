# portfolio-prices

Public price feed for the portfolio dashboard. Contains no personal data — only market prices and FX rates.

## What this is

A GitHub Actions job runs every 30 minutes on weekdays and commits `prices.json` with current market data. The dashboard fetches this file directly via the raw GitHub URL.

## Data sources

| Data | Source | API key required |
|------|--------|-----------------|
| BTC/EUR | CoinGecko | No |
| EUR/CZK, USD/CZK | Frankfurter.app (ECB) | No |
| Stocks (ASML, RHM, VUSA, DRS, PLTR, NW0) | Yahoo Finance via yfinance | No |

## prices.json format

```json
{
  "BTC": 82000,
  "ASML": 672.00,
  "RHM": 1820.00,
  "VUSA": 107.00,
  "DRS": 44.00,
  "PLTR": 88.00,
  "NW0": 30.50,
  "EURCZK": 25.20,
  "USDCZK": 23.18,
  "updated_at": "2026-03-06T14:30:00Z"
}
```

## Running locally

```bash
pip install -r requirements.txt
python fetch_prices.py
```
