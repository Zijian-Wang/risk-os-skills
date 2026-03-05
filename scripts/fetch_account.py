#!/usr/bin/env python3
"""Load account JSON from a local file and output canonical account data.

Usage:
    python scripts/fetch_account.py --account-path /path/to/account.json
    python scripts/fetch_account.py --account-path /path/to/account.json > /tmp/account.json

If --account-path is omitted, prints the expected JSON schema to stderr and exits.
Copy account_schema_example.json at the repo root to get started.

Schema fields:
    source          — string (e.g. "schwab-sync-processed")
    generatedAt     — ISO 8601 datetime string
    accountSummary  — { portfolioValue, accountEquity, cashBalance }
    positions       — array of position objects (see account_schema_example.json)
"""

import argparse
import json
import os
import sys

SCHEMA_HINT = """\
Expected account JSON schema:

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

Copy account_schema_example.json from the repo root and fill in your values.
Pass the path via: --account-path /path/to/your/account.json
"""


def load_account(path: str) -> dict:
    """Load and return account JSON from a file."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Account file not found: {path}")
    with open(path) as f:
        data = json.load(f)

    # Basic structural validation
    required_top = {"source", "generatedAt", "accountSummary", "positions"}
    missing = required_top - data.keys()
    if missing:
        raise ValueError(f"Account JSON missing required fields: {', '.join(sorted(missing))}")

    summary = data["accountSummary"]
    for field in ("portfolioValue", "accountEquity", "cashBalance"):
        if field not in summary:
            raise ValueError(f"accountSummary missing field: {field}")

    if not isinstance(data["positions"], list):
        raise ValueError("positions must be an array")

    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Load account JSON from a local file")
    parser.add_argument("--account-path", required=False, help="Path to account JSON file")
    args = parser.parse_args()

    if not args.account_path:
        print("Error: --account-path is required.\n", file=sys.stderr)
        print(SCHEMA_HINT, file=sys.stderr)
        sys.exit(1)

    try:
        account = load_account(args.account_path)
        print(json.dumps(account, indent=2))
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
