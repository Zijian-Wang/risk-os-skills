---
name: watch-list
description: Analyze multiple tickers in parallel (US/HK/CN) with risk-os scripts, rank by conviction, and return a comparison table plus top pick.
---
# Watch List

Use repo root: `/data/workspace/risk-os-skills`.

## Inputs
- `symbols` (required, 1+)
- optional: `market` (`US|HK|CN`, default US), `accountPath`, `timeframe`

## Workflow
1. Load account once.
   - If `accountPath` provided, read it.
   - Else run: `python3 scripts/fetch_account.py`.
2. For each symbol, run analysis in parallel:
   - `python3 scripts/fetch_data.py --symbol <sym> --market <market> --timeframe <timeframe>`
   - `python3 scripts/compute_indicators.py --input <data-json>`
   - `python3 scripts/check_rules.py --indicators <ind-json> --account <account-json> --market <market>`
3. Per symbol, produce JSON-like result fields:
   - symbol, price, decision, conviction, trend bias/strength, RSI signal, MACD signal, news sentiment, R/R, size, risk amount, violations/error.
4. Sort results:
   - BUY first, then NO_BUY, then ERROR.
   - Within group, conviction descending.

## Output
Return markdown:
- Watchlist comparison table (symbol/price/decision/conviction/trend/RSI/MACD/news/R:R-to-resistance/size/risk).
- Top pick summary (1-2 lines) if any BUY exists.
- Brief pass note if no BUY.

Use `—` for unavailable plan fields on NO_BUY/ERROR.
