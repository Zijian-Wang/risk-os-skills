# risk-os-skills

Claude Code slash commands and Python scripts for structured trade analysis — three-tier pipeline across US, HK, and CN markets.

## Commands

| Command | Description |
|---|---|
| `/analyze-trade <SYMBOL> <MARKET> --account <path>` | Full three-tier BUY / NO_BUY analysis for a single ticker |
| `/watch-list <SYM1> [SYM2 ...] --account <path>` | Parallel analysis + ranked comparison table for a basket |
| `/validate-account <path>` | Validate an account JSON file against the canonical schema |
| `/show-risk-config` | Display current risk defaults from `config/defaults.json` |

## Setup

```bash
# 1. Clone
git clone <repo-url>
cd risk-os-skills

# 2. Create venv and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure credentials
cp .env.example .env
# Edit .env — add Schwab credentials and optional NewsAPI key

# 4. Create your account JSON
cp account_schema_example.json my_account.json
# Edit my_account.json — fill in your portfolio values and positions

# 5. Link commands globally into Claude Code
bash setup.sh
```

After running `setup.sh`, the slash commands are available in **any** Claude Code project on this machine.

## Account JSON

Pass your portfolio data as a JSON file matching this schema (see `account_schema_example.json`):

```json
{
  "source": "schwab-sync-processed",
  "generatedAt": "2025-01-15T10:00:00Z",
  "accountSummary": {
    "portfolioValue": 150000,
    "accountEquity": 145000,
    "cashBalance": 25000
  },
  "positions": [
    {
      "instrument": { "symbol": "AAPL", "assetType": "EQUITY" },
      "direction": "long",
      "quantity": 100,
      "averagePrice": 180.0,
      "costBasis": 18000.0,
      "marketValue": 19500.0,
      "currentPrice": 195.0,
      "target": 210.0,
      "stop": 175.0
    }
  ]
}
```

Run `/validate-account /path/to/my_account.json` to check your file before using it with the other commands.

## Pipeline overview

```
/analyze-trade AAPL US --account ~/my_account.json
       │
       ├── Tier 1 — Computation (sequential)
       │     fetch_account.py  →  validates + loads account JSON
       │     fetch_data.py     →  OHLCV + news JSON
       │     compute_indicators.py  →  technical indicators
       │     check_rules.py    →  risk gate + trade plan
       │
       ├── Tier 2 — Analysis (parallel sub-agents)
       │     Technical analyst  →  trend / S&R / MA assessment
       │     News analyst       →  sentiment + catalysts
       │
       └── Tier 3 — Synthesis
             Conviction score (0-100), BUY requires ≥ 65
             Final trade plan: entry / stop / resistance / size / R:R
```

## Risk defaults (`config/defaults.json`)

| Parameter | Default |
|---|---|
| Risk per trade | 1% equity |
| Max position size | 10% equity |
| Max concurrent positions | 10 |
| Min R/R ratio | 1.8 |
| ATR stop multiplier | 1.5× |
| Buy conviction threshold | 70 / 100 |

Run `/show-risk-config` to see the full table, or edit `config/defaults.json` directly.

## Environment variables

```
# .env
NEWSAPI_KEY=           # optional — news skipped if not set

# Schwab API — required for US market OHLCV data
SCHWAB_CLIENT_ID=
SCHWAB_CLIENT_SECRET=
SCHWAB_REFRESH_TOKEN=

# Local proxy — optional, for geo-blocked APIs
HTTPS_PROXY=socks5://127.0.0.1:1082
HTTP_PROXY=socks5://127.0.0.1:1082
```

## Project structure

```
risk-os-skills/
├── .claude/
│   └── commands/              # Slash command definitions
│       ├── analyze-trade.md
│       ├── watch-list.md
│       ├── validate-account.md
│       └── show-risk-config.md
├── config/
│   └── defaults.json          # Risk parameters and market profiles
├── scripts/
│   ├── fetch_account.py       # Load and validate account JSON
│   ├── fetch_data.py          # Fetch OHLCV bars + news (Schwab / Stooq / NewsAPI)
│   ├── compute_indicators.py  # RSI, MACD, ATR, Bollinger, SMA/EMA
│   └── check_rules.py         # Risk gate + stop/resistance/size computation
├── account_schema_example.json  # Template — copy and fill in your data
├── .env.example
├── requirements.txt
└── setup.sh
```
