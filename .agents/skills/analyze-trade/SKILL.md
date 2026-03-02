---
name: analyze-trade
description: Run full three-tier BUY/NO_BUY trade analysis for a single ticker in US/HK/CN using risk-os scripts (fetch_data, compute_indicators, check_rules), then synthesize technical/news/portfolio context into conviction score and trade plan.
---
# Analyze Trade

Use repo root: `/data/workspace/risk-os-skills`.

## Inputs
- `symbol` (required)
- `market` (required: `US|HK|CN`)
- optional: `accountPath`, `riskPct`, `timeframe` (`1d|1h|1w`), `entry`

## Workflow
1. Load account JSON.
   - If `accountPath` provided, read it.
   - Else run:
   - `python3 scripts/fetch_account.py`
2. Fetch market data:
   - `python3 scripts/fetch_data.py --symbol <symbol> --market <market> --timeframe <timeframe>`
3. Compute indicators:
   - `python3 scripts/compute_indicators.py --input <data-json-path>`
4. Risk/plan gate:
   - `python3 scripts/check_rules.py --indicators <ind-json-path> --account <account-json-path> --market <market> [--entry <entry>] [--risk-pct <riskPct>]`
5. If `passed=false`, return `NO_BUY` with violations and stop.
6. If passed, produce concise synthesis with:
   - decision (`BUY|NO_BUY`)
   - conviction score (0-100)
   - entry/stop/resistance/R:R-to-resistance (if available)/size/risk amount
   - technical summary + news summary + portfolio context.

## Conviction guidance
- Base 50.
- Strong bullish technical +15~20; moderate bullish +8~12; bearish -15~-20.
- Strong positive news +8~12; negative -8~-12; degraded news = 0.
- Healthy portfolio cash/positioning +5; tight portfolio -5.
- R/R > 2.0 +5.
- Clamp 0..100. `BUY` normally requires >=65.

## Output
Return:
- Decision + conviction
- Trade plan table
- Signal summary bullets
- 2-3 sentence rationale
- Risk check status
