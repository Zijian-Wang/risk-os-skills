---
name: validate-account
description: Validate risk-os account JSON schema and risk warnings (required fields, account summary integrity, position-level checks, concentration/cash/stop warnings).
---
# Validate Account

Resolve repo root via `git rev-parse --show-toplevel` (fallback: current working directory).

## Input
- `accountPath` (required)

## Required checks
### Top-level (hard fail)
- `source` string and equals `schwab-sync-processed`
- `generatedAt` valid ISO datetime string
- `accountSummary` object
- `positions` array (can be empty)

### accountSummary (hard fail)
- `portfolioValue` number > 0
- `accountEquity` number > 0
- `cashBalance` number >= 0
- `cashBalance <= portfolioValue`

### Per-position
Hard fail:
- `instrument.symbol` non-empty string
- `instrument.assetType` string
- `direction` in `long|short`
- `quantity` integer > 0
- `averagePrice` > 0
- `costBasis` > 0
Warnings (not hard fail):
- `assetType` not `EQUITY`
- missing/null `stop`
- missing/null `target`
- missing/null `currentPrice`

### Portfolio warnings
- no positions
- any missing stop
- cash ratio < 5%
- any position concentration > 25% of portfolio value

## Output
Return:
- VALID/INVALID status
- summary table (generated time, portfolio/equity/cash/cash%, position count)
- errors list (blocking)
- warnings list (non-blocking)
