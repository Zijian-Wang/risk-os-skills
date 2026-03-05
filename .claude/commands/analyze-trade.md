# Analyze Trade

Runs a full three-tier trade analysis for a single ticker and produces a structured BUY / NO_BUY decision.

## Usage

```
/analyze-trade <SYMBOL> <MARKET> [--account /path/to/account.json] [--risk-pct 0.01] [--timeframe 1d] [--entry 197.40]
```

Examples:
- `/analyze-trade AAPL US`
- `/analyze-trade 0700 HK --account /tmp/account.json`
- `/analyze-trade AAPL US --risk-pct 0.005 --entry 195`

**Arguments:**
- `SYMBOL` — ticker symbol (required)
- `MARKET` — US | HK | CN (required)
- `--account` — path to risk-os JSON file; if omitted, runs `fetch_account.py` automatically
- `--risk-pct` — risk per trade as decimal (default: from `config/defaults.json`)
- `--timeframe` — 1d | 1h | 1w (default: 1d)
- `--entry` — override entry price (default: current market price)

---

## Instructions for Claude

Parse the arguments from `$ARGUMENTS`. Extract SYMBOL (first positional), MARKET (second positional), and any named flags.

### Bootstrap — resolve REPO_ROOT and PYTHON

Before running any script, execute this once to set up the environment:

```bash
# Repo root: use git if available, otherwise fall back to the working directory
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Find a usable Python with the project venv packages.
# Prefer the project venv, then fall back to system python3/python.
if   [ -x "$REPO_ROOT/.venv/bin/python3" ]; then PYTHON="$REPO_ROOT/.venv/bin/python3"
elif [ -x "$REPO_ROOT/venv/bin/python3" ];  then PYTHON="$REPO_ROOT/venv/bin/python3"
elif command -v python3 &>/dev/null;         then PYTHON=python3
elif command -v python  &>/dev/null;         then PYTHON=python
else echo "ERROR: no python found" >&2; exit 1; fi

# Quick sanity check — the scripts need pandas at minimum
$PYTHON -c "import pandas" 2>/dev/null || { echo "ERROR: $PYTHON is missing required packages. Activate the project venv or run: $PYTHON -m pip install -r $REPO_ROOT/requirements.txt" >&2; exit 1; }
```

Use `$REPO_ROOT` wherever paths reference the project, and `$PYTHON` to invoke scripts.

### Tier 1 — Computation (sequential Bash calls)

**Step 1: Load account JSON**

If `--account` was provided, read that file. Otherwise run:
```bash
$PYTHON $REPO_ROOT/scripts/fetch_account.py
```
Save the output as the account JSON. If this fails and no `--account` was given, stop and report the error.

**Step 2: Fetch market data**
```bash
$PYTHON $REPO_ROOT/scripts/fetch_data.py --symbol SYMBOL --market MARKET --timeframe TIMEFRAME > /tmp/ts_data_SYMBOL.json
```
Check `bars_count` in the output. If fewer than 120 bars, warn but continue.

**Step 3: Compute indicators**
```bash
$PYTHON $REPO_ROOT/scripts/compute_indicators.py --input /tmp/ts_data_SYMBOL.json > /tmp/ts_indicators_SYMBOL.json
```

**Step 4: Check rules and compute trade plan**

Save the account JSON to `/tmp/ts_account_SYMBOL.json` first, then:
```bash
$PYTHON $REPO_ROOT/scripts/check_rules.py \
  --indicators /tmp/ts_indicators_SYMBOL.json \
  --account /tmp/ts_account_SYMBOL.json \
  [--entry ENTRY_PRICE] \
  [--risk-pct RISK_PCT] \
  --market MARKET
```

**If `passed` is false:** Output a NO_BUY result immediately with the violation list and stop. Do not proceed to Tier 2.

```
## SYMBOL — MARKET — DATE

**Decision: NO_BUY**

### Risk Check: FAILED

Violations:
- [rule]: [message]
...

No further analysis performed.
```

### Tier 2 — Analysis (launch two parallel sub-agents)

Spawn these two sub-agents **simultaneously** using the Agent tool with `run_in_background: false` — wait for both before proceeding.

**Sub-agent A — Technical Analysis:**

Provide this sub-agent with:
1. The full indicators JSON (from Step 3)
2. This instruction:

> You are a technical analyst. Analyze these indicators for SYMBOL and produce a structured assessment. Be specific and data-driven.
>
> Indicators JSON: [paste full indicators JSON]
>
> Return a JSON object with these exact fields:
> - "trend_bias": "bullish" | "bearish" | "neutral"
> - "trend_strength": "strong" | "moderate" | "weak"
> - "key_signals": [list of 3-5 specific observations, e.g. "RSI 62 — mid-momentum, room to run", "MACD bullish crossover 3 days ago"]
> - "sr_context": string describing price position relative to support/resistance levels
> - "ma_alignment": string describing SMA/EMA stack alignment
> - "confidence": "high" | "medium" | "low"
> - "summary": one sentence overall assessment

**Sub-agent B — News Analysis:**

Provide this sub-agent with:
1. The news array from the fetch_data output (`/tmp/ts_data_SYMBOL.json` → `.news`)
2. This instruction:

> You are a financial news analyst. Analyze these recent news items for SYMBOL.
>
> News items: [paste news array JSON]
>
> Return a JSON object with these exact fields:
> - "overall_sentiment": "positive" | "negative" | "neutral" | "mixed"
> - "sentiment_strength": "strong" | "moderate" | "weak"
> - "key_catalysts": [list of 2-4 specific news drivers or themes]
> - "degraded": true if fewer than 3 articles, false otherwise
> - "confidence": "high" | "medium" | "low"
> - "summary": one sentence overall assessment
>
> If no news items provided, return degraded: true with neutral sentiment and low confidence.

### Tier 3 — Synthesis (main context)

Collect:
- Tier 1: indicators JSON, trade plan (stop/TP/size/R:R)
- Tier 2: technical assessment JSON, news assessment JSON
- Account context: equity, cash, number of existing positions

Synthesize into a final BUY or NO_BUY decision with conviction score (0-100).

**Conviction scoring guidance:**
- Start at 50 (neutral)
- Technical strong bullish: +15 to +20
- Technical moderate bullish: +8 to +12
- Technical bearish: -15 to -20
- News positive strong: +8 to +12
- News negative: -8 to -12
- News degraded: apply 0 (don't add or subtract)
- Portfolio healthy (>15% cash, <8 positions): +5
- Portfolio tight: -5
- Good R/R (>2.0): +5
- Clamp final score to 0-100

BUY requires conviction >= 65.

### Output Format

```markdown
## SYMBOL — MARKET — DATE

**Decision: BUY** (Conviction: XX/100)
[or: **Decision: NO_BUY** (Conviction: XX/100)]

### Trade Plan
| | |
|---|---|
| Entry ref | $XXX.XX |
| Stop loss | $XXX.XX (−X.X%) |
| Resistance | $XXX.XX (+X.X%) or N/A |
| R/R to resistance | X.XX or N/A |
| Position size | XX shares |
| Risk amount | $XXX (X.X% equity) |

### Signal Summary
- **Technical (STRENGTH):** [key_signals joined, sr_context, ma_alignment]
- **News (SENTIMENT):** [news count], [summary]; [degraded warning if applicable]
- **Portfolio:** [equity, cash%, position count, any concentration notes]

### Rationale
[2-3 sentence synthesis paragraph explaining the conviction level. Reference specific signals. Be direct about uncertainties.]

### Risk Check: PASSED
[or: ### Risk Check: FAILED — [violation summary]]
```
