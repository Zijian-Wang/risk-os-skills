# Watch List

Run a full trade analysis for multiple tickers in parallel and render a ranked comparison table.

## Usage

```
/watch-list <SYMBOL1> [SYMBOL2 ...] [--market US] [--account /path/to/account.json] [--timeframe 1d]
```

Examples:
- `/watch-list AAPL NVDA TSM`
- `/watch-list AAPL NVDA TSM --account /tmp/account.json`
- `/watch-list 0700 0941 9988 --market HK`

**Arguments:**
- Symbols — one or more ticker symbols (required, positional)
- `--market` — US | HK | CN applied to all symbols (default: US)
- `--account` — path to risk-os JSON (if omitted, fetch_account.py is run once and shared)
- `--timeframe` — 1d | 1h | 1w (default: 1d)

---

## Instructions for Claude

Parse `$ARGUMENTS` to extract the list of symbols and any named flags.

### Bootstrap — resolve REPO_ROOT and PYTHON

Before running any script, execute this once to set up the environment:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

if   [ -x "$REPO_ROOT/.venv/bin/python3" ]; then PYTHON="$REPO_ROOT/.venv/bin/python3"
elif [ -x "$REPO_ROOT/venv/bin/python3" ];  then PYTHON="$REPO_ROOT/venv/bin/python3"
elif command -v python3 &>/dev/null;         then PYTHON=python3
elif command -v python  &>/dev/null;         then PYTHON=python
else echo "ERROR: no python found" >&2; exit 1; fi

$PYTHON -c "import pandas" 2>/dev/null || { echo "ERROR: $PYTHON is missing required packages. Activate the project venv or run: $PYTHON -m pip install -r $REPO_ROOT/requirements.txt" >&2; exit 1; }
```

Use `$REPO_ROOT` wherever paths reference the project, and `$PYTHON` to invoke scripts.

### Step 1: Load account once

If `--account` provided, read it. Otherwise run `fetch_account.py` once and save to `/tmp/ts_account_watchlist.json`.

### Step 2: Analyze all tickers in parallel

Launch one sub-agent **per ticker** using the Agent tool (`run_in_background: false` for all simultaneously, then wait for all).

Each sub-agent receives:
- The ticker symbol and market
- The account JSON path
- The repo root path and Python path
- This instruction:

> Run a complete trade analysis for SYMBOL (MARKET market) using the risk-os-skills scripts.
>
> REPO_ROOT: [path]
> Account file: [path]
>
> Steps:
> 1. `$PYTHON REPO_ROOT/scripts/fetch_data.py --symbol SYMBOL --market MARKET --timeframe TIMEFRAME > /tmp/ts_data_SYMBOL.json`
> 2. `$PYTHON REPO_ROOT/scripts/compute_indicators.py --input /tmp/ts_data_SYMBOL.json > /tmp/ts_indicators_SYMBOL.json`
> 3. `$PYTHON REPO_ROOT/scripts/check_rules.py --indicators /tmp/ts_indicators_SYMBOL.json --account ACCOUNT_PATH --market MARKET`
> 4. Based on indicators, assess: trend_bias (bullish/bearish/neutral), trend_strength (strong/moderate/weak), rsi_signal (overbought/neutral/oversold), macd_signal (bullish/bearish/neutral), news_sentiment (if news available from fetch_data output: positive/negative/neutral/mixed, else: no_data).
>
> Return a single JSON object:
> ```json
> {
>   "symbol": "AAPL",
>   "market": "US",
>   "current_price": 197.4,
>   "decision": "BUY",
>   "conviction": 74,
>   "trend_bias": "bullish",
>   "trend_strength": "strong",
>   "rsi": 62.3,
>   "rsi_signal": "neutral",
>   "macd_signal": "bullish",
>   "news_sentiment": "positive",
>   "stop_loss": 190.2,
>   "resistance": 210.8,
>   "rr_to_resistance": 1.86,
>   "position_size": 80,
>   "risk_amount": 576.0,
>   "violations": [],
>   "error": null
> }
> ```
> If any script fails, set error to the error message and decision to "ERROR".

### Step 3: Render comparison table

Collect all sub-agent results. Sort by conviction descending (BUY decisions first, then NO_BUY, then ERROR).

Output:

```markdown
## Watch List Analysis — MARKET — DATE

| Symbol | Price | Decision | Conviction | Trend | RSI | MACD | News | R/R | Size | Risk $ |
|--------|-------|----------|-----------|-------|-----|------|------|-----|------|--------|
| AAPL | $197.40 | **BUY** | 74/100 | Bullish↑ | 62 (neutral) | Bullish | Positive | 1.86 | 80 | $576 |
| NVDA | $880.00 | NO_BUY | 48/100 | Neutral→ | 71 (overbought) | Bearish | Mixed | — | — | — |
| TSM | $145.20 | NO_BUY | 55/100 | Bearish↓ | 44 (neutral) | Neutral | Positive | — | — | — |

### Top Pick: AAPL
[1-2 sentence rationale for the top-ranked BUY, if any exist]

### Pass (No Buys)
[Brief note if no tickers cleared the conviction threshold]
```

Use `—` for stop/TP/size/risk columns when decision is NO_BUY or ERROR.
Use `↑` `→` `↓` arrows for trend direction.
