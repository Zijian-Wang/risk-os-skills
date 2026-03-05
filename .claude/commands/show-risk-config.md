# Show Risk Config

Display the current risk configuration defaults.

## Usage

```
/show-risk-config
```

---

## Instructions for Claude

Resolve the repo root: `REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"`.

Read `$REPO_ROOT/config/defaults.json` and format it as follows:

```markdown
## Risk Configuration

**Source:** config/defaults.json

### Trade Risk Limits
| Parameter | Value | Description |
|---|---|---|
| Risk per trade | X.XX% | Max equity risked on a single trade |
| Max position size | XX% | Max equity in a single position |
| Max concurrent positions | XX | Hard cap on open trades |
| Min R/R ratio | X.X | Minimum reward-to-risk required |

### Exit Level Parameters
| Parameter | Value | Description |
|---|---|---|
| ATR stop multiplier | X.X | Stop = entry − multiplier × ATR |
| ATR structure buffer | X.X | Structure stop = support − buffer × ATR |
| Default TP R/R | X.X | Take-profit target R/R when no resistance |

### Data Thresholds
| Parameter | Value | Description |
|---|---|---|
| Min OHLCV bars | XXX | Below this → insufficient data |
| Min news items | X | Below this → news signal degraded |
| News lookback days | X | Days of news to fetch |
| Buy threshold | XX | Min conviction score for BUY |

### Market Profiles
| Market | Currency | Lot Size | Price Limit | Settlement |
|---|---|---|---|---|
| US | USD | 1 | None | T+2 |
| HK | HKD | 100 | None | T+2 |
| CN | CNY | 100 | ±10% | T+1 |

---
*Edit `config/defaults.json` to change these values.*
```

Fill in actual values from the JSON file.
