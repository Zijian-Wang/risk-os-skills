# risk-os-skills

Claude Code slash commands and Python scripts for the **risk-os** universe — structured trade analysis with a three-tier pipeline across US, HK, and CN markets.

## Commands

| Command | Description |
|---|---|
| `/analyze-trade <SYMBOL> <MARKET>` | Full three-tier BUY / NO_BUY analysis for a single ticker |
| `/watch-list <SYM1> [SYM2 ...]` | Parallel analysis + ranked comparison table for a basket |
| `/validate-account <path>` | Validate a risk-os account JSON against the canonical schema |
| `/show-risk-config` | Display current risk defaults from `config/defaults.json` |

## Setup

```bash
# 1. Clone and install dependencies
git clone <repo-url> ~/Developer/trade-skills
cd ~/Developer/trade-skills
pip install -r requirements.txt

# 2. Configure credentials
cp .env.example .env
# Edit .env — add Firebase credentials and optional NewsAPI key

# 3. Link commands globally into Claude Code
bash setup.sh
```

After running `setup.sh`, the slash commands are available in **any** Claude Code project on this machine.

## Pipeline overview

```
/analyze-trade AAPL US
       │
       ├── Tier 1 — Computation (sequential)
       │     fetch_account.py  →  account JSON
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
             Final trade plan: entry / stop / TP / size / R:R
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
# .env.example
NEWSAPI_KEY=           # optional — news skipped if not set
FIREBASE_PROJECT_ID=
FIREBASE_CLIENT_EMAIL=
FIREBASE_PRIVATE_KEY=
FIREBASE_USER_UID=     # Firebase Auth UID to query positions under

# Schwab API — required for fetch_data.py (US market price data)
SCHWAB_CLIENT_ID=
SCHWAB_CLIENT_SECRET=
# Tokens are read from Firebase (schwabAccounts[0]) and auto-refreshed at runtime

# Local proxy — required if Yahoo/Schwab APIs are geo-blocked
HTTPS_PROXY=socks5://127.0.0.1:1082
HTTP_PROXY=socks5://127.0.0.1:1082
```

## Project structure

```
risk-os-skills/
├── .claude/
│   └── commands/          # Slash command definitions
│       ├── analyze-trade.md
│       ├── watch-list.md
│       ├── validate-account.md
│       └── show-risk-config.md
├── config/
│   └── defaults.json      # Risk parameters and market profiles
├── scripts/
│   ├── fetch_account.py   # Pull account JSON from Firebase
│   ├── fetch_data.py      # Fetch OHLCV bars + news (Schwab API / Stooq fallback / NewsAPI)
│   ├── compute_indicators.py  # RSI, MACD, ATR, Bollinger, SMA/EMA
│   └── check_rules.py     # Risk gate + stop/TP/size computation
├── tests/
│   └── fixtures/
│       └── sample_account.json
├── .env.example
├── requirements.txt
└── setup.sh
```

## OpenClaw native skills (added)

This repo now also includes OpenClaw-native skill definitions at:

- `.agents/skills/analyze-trade/SKILL.md`
- `.agents/skills/watch-list/SKILL.md`
- `.agents/skills/validate-account/SKILL.md`
- `.agents/skills/show-risk-config/SKILL.md`

These mirror the Claude slash-command intents so OpenClaw can trigger them natively.

## Part of the risk-os universe

This repo contains the Claude Code skill layer plus OpenClaw-native skill definitions. Other components in the risk-os universe live in their own repos.
