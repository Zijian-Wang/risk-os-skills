# Validate Account

Validate an account JSON file against the risk-os canonical schema.

## Usage

```
/validate-account <path/to/account.json>
```

Examples:
- `/validate-account /tmp/account.json`
- `/validate-account ~/Developer/risk-os-skills/tests/fixtures/sample_account.json`

---

## Instructions for Claude

Parse `$ARGUMENTS` to get the file path. Read the file.

Validate the following:

### Required top-level fields
- `source` — string, must be `"schwab-sync-processed"`
- `generatedAt` — string, must be a valid ISO 8601 datetime
- `accountSummary` — object
- `positions` — array (may be empty but must exist)

### accountSummary checks
- `portfolioValue` — number, must be > 0
- `accountEquity` — number, must be > 0
- `cashBalance` — number, must be >= 0
- `cashBalance` must be <= `portfolioValue`

### positions array checks (for each position)
- `instrument.symbol` — non-empty string
- `instrument.assetType` — string (warn if not "EQUITY")
- `direction` — must be "long" or "short"
- `quantity` — integer > 0
- `averagePrice` — number > 0
- `costBasis` — number > 0
- `stop` — number > 0 (warn if missing/null)
- `target` — number (warn if missing/null)
- `currentPrice` — number (warn if missing/null)

### Portfolio-level checks
- Warn if no positions (valid but unusual)
- Warn if any position has no stop loss set
- Warn if cashBalance / portfolioValue < 0.05 (less than 5% cash — tight)
- Warn if any single position marketValue / portfolioValue > 0.25 (>25% concentration)

### Output format

```markdown
## Account Validation: /path/to/account.json

**Status: VALID** ✓
[or: **Status: INVALID** ✗]

### Summary
| Field | Value |
|---|---|
| Generated | 2025-01-15T10:00:00Z |
| Portfolio value | $150,000 |
| Account equity | $145,000 |
| Cash balance | $25,000 (16.7%) |
| Positions | 2 |

### Errors
[List any schema violations that make the file INVALID. Empty if none.]

### Warnings
[List non-blocking issues. Empty if none.]
- Position AAPL: no target price set
- Cash ratio 4.2% is below recommended 5%
```

The account is INVALID only if required fields are missing or have wrong types. Warnings do not affect validity.
