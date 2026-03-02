#!/usr/bin/env python3
"""Fetch live positions from risk-os Firestore and output canonical account JSON.

Usage:
    python scripts/fetch_account.py
    python scripts/fetch_account.py > /tmp/account.json

Required env vars (set in .env or environment):
    FIREBASE_PROJECT_ID
    FIREBASE_CLIENT_EMAIL
    FIREBASE_PRIVATE_KEY
    FIREBASE_USER_UID
"""

import json
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()


def _build_credentials() -> dict:
    """Build Firebase service account dict from env vars."""
    private_key = os.environ["FIREBASE_PRIVATE_KEY"].replace("\\n", "\n")
    return {
        "type": "service_account",
        "project_id": os.environ["FIREBASE_PROJECT_ID"],
        "private_key": private_key,
        "client_email": os.environ["FIREBASE_CLIENT_EMAIL"],
        "token_uri": "https://oauth2.googleapis.com/token",
    }


def fetch_account() -> dict:
    """Pull account + active positions from Firestore."""
    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        cred = credentials.Certificate(_build_credentials())
        firebase_admin.initialize_app(cred)

    db = firestore.client()
    uid = os.environ["FIREBASE_USER_UID"]

    # Fetch account balances from root user doc
    user_doc = db.collection("users").document(uid).get()
    if not user_doc.exists:
        raise RuntimeError(f"User document not found for uid={uid}")

    user_data = user_doc.to_dict()
    schwab_accounts = user_data.get("schwabAccounts", [])
    acct = schwab_accounts[0] if schwab_accounts else {}

    portfolio_value = float(acct.get("accountValue", 0))
    account_equity = float(acct.get("accountEquity", portfolio_value))
    cash_balance = float(acct.get("cashBalance", 0))

    # Fetch active synced trades
    trades_ref = (
        db.collection("users")
        .document(uid)
        .collection("trades")
        .where("syncedFromBroker", "==", True)
        .where("status", "==", "ACTIVE")
    )
    trade_docs = trades_ref.stream()

    positions = []
    for doc in trade_docs:
        trade = doc.to_dict()
        symbol = trade.get("symbol", "")
        entry = float(trade.get("entry", 0))
        size = int(trade.get("positionSize", 0))
        current_price = trade.get("currentPrice")
        mkt_val = float(current_price) * size if current_price is not None else entry * size
        positions.append(
            {
                "instrument": {
                    "symbol": symbol,
                    "assetType": trade.get("instrumentType", "EQUITY"),
                },
                "direction": trade.get("direction", "long"),
                "quantity": size,
                "averagePrice": entry,
                "costBasis": round(entry * size, 2),
                "marketValue": round(mkt_val, 2),
                "currentPrice": float(current_price) if current_price is not None else None,
                "target": trade.get("target"),
                "stop": trade.get("stop"),
            }
        )

    return {
        "source": "schwab-sync-processed",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "accountSummary": {
            "portfolioValue": portfolio_value,
            "accountEquity": account_equity,
            "cashBalance": cash_balance,
        },
        "positions": positions,
    }


def main() -> None:
    required = ["FIREBASE_PROJECT_ID", "FIREBASE_CLIENT_EMAIL", "FIREBASE_PRIVATE_KEY", "FIREBASE_USER_UID"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"Error: missing env vars: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    try:
        account = fetch_account()
        print(json.dumps(account, indent=2))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
