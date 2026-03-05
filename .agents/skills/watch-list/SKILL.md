---
name: watch-list
description: Analyze multiple tickers in parallel (US/HK/CN) with risk-os scripts, rank by conviction, and return a comparison table plus top pick.
---
# Watch List

Resolve repo root via `git rev-parse --show-toplevel` (fallback: current working directory).
Find Python: prefer `$REPO_ROOT/.venv/bin/python3`, then `$REPO_ROOT/venv/bin/python3`, then system `python3`, then `python`. Verify chosen Python can `import pandas`.

## Inputs
- `symbols` (required, 1+)
- optional: `market` (`US|HK|CN`, default US), `accountPath`, `timeframe`

## Workflow
1. Load account once.
   - If `accountPath` provided, read it.
   - Else run: `$PYTHON scripts/fetch_account.py`.
2. For each symbol, run analysis in parallel:
   - `$PYTHON scripts/fetch_data.py --symbol <sym> --market <market> --timeframe <timeframe>`
   - `$PYTHON scripts/compute_indicators.py --input <data-json>`
   - `$PYTHON scripts/check_rules.py --indicators <ind-json> --account <account-json> --market <market>`
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
