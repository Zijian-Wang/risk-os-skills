#!/usr/bin/env python3
"""Apply hard risk rules, compute exit levels, and size the position.

Usage:
    python scripts/check_rules.py \
        --indicators /tmp/indicators.json \
        --account /tmp/account.json \
        [--entry 197.4] \
        [--risk-pct 0.01] \
        [--market US]

Output JSON:
    {
      "passed": true,
      "violations": [],
      "entry": 197.4,
      "stop_loss": 190.2,
      "take_profit": 210.8,
      "stop_pct": -3.6,
      "tp_pct": 6.8,
      "rr_ratio": 1.86,
      "position_size": 80,
      "risk_amount": 576.0,
      "reward_amount": 1072.0,
      "risk_pct_equity": 0.40
    }

Violations list items: { "rule": "...", "message": "..." }
"""

import argparse
import json
import sys

from dotenv import load_dotenv

load_dotenv()

MARKET_PROFILES = {
    "US": {"lot_size": 1, "price_limit": None, "tick_size": 0.01},
    "HK": {"lot_size": 100, "price_limit": None, "tick_size": 0.01},
    "CN": {"lot_size": 100, "price_limit": 0.10, "tick_size": 0.01},
}


def load_defaults() -> dict:
    import os
    defaults_path = os.path.join(os.path.dirname(__file__), "..", "config", "defaults.json")
    with open(defaults_path) as f:
        return json.load(f)


def compute_stop_loss(entry: float, atr: float, nearest_support: float | None, defaults: dict) -> float:
    """ATR stop vs structure stop — take the more conservative (higher) value."""
    multiplier = defaults["atr_stop_multiplier"]
    buffer = defaults["atr_structure_buffer"]

    atr_stop = entry - multiplier * atr
    if nearest_support is not None:
        structure_stop = nearest_support - buffer * atr
        return max(atr_stop, structure_stop)
    return atr_stop


def compute_take_profit(
    entry: float,
    stop_loss: float,
    nearest_resistance: float | None,
    defaults: dict,
) -> float:
    """Target TP at default_tp_rr; use resistance level if it clears min_rr."""
    risk = entry - stop_loss
    min_rr = defaults["min_rr"]
    target_rr = defaults["default_tp_rr"]
    tp_rr = entry + target_rr * risk

    if nearest_resistance is not None and nearest_resistance > entry:
        resistance_rr = (nearest_resistance - entry) / risk if risk > 0 else 0
        if resistance_rr >= min_rr:
            return nearest_resistance

    return tp_rr


def enforce_price_limit(price: float, entry: float, price_limit: float | None, is_stop: bool) -> float:
    if price_limit is None:
        return price
    limit_down = entry * (1 - price_limit)
    limit_up = entry * (1 + price_limit)
    return max(price, limit_down) if is_stop else min(price, limit_up)


def round_to_tick(price: float, tick_size: float) -> float:
    return round(round(price / tick_size) * tick_size, 10)


def compute_position_size(
    entry: float,
    stop_loss: float,
    equity: float,
    cash: float,
    risk_pct: float,
    max_position_pct: float,
    lot_size: int,
) -> int:
    risk_per_share = entry - stop_loss
    if risk_per_share <= 0:
        return 0

    risk_amount = equity * risk_pct
    size_from_risk = int(risk_amount / risk_per_share)

    max_position_value = equity * max_position_pct
    size_from_position = int(max_position_value / entry) if entry > 0 else 0

    size_from_cash = int(cash / entry) if entry > 0 else 0

    size = min(size_from_risk, size_from_position, size_from_cash)
    size = (size // lot_size) * lot_size
    return max(0, size)


def run_checks(
    indicators: dict,
    account: dict,
    entry: float,
    risk_pct: float,
    market: str,
    defaults: dict,
) -> dict:
    profile = MARKET_PROFILES[market]
    lot_size = profile["lot_size"]
    price_limit = profile["price_limit"]
    tick_size = profile["tick_size"]

    summary = account.get("accountSummary", {})
    equity = float(summary.get("accountEquity", summary.get("portfolioValue", 0)))
    cash = float(summary.get("cashBalance", 0))
    num_positions = len(account.get("positions", []))

    atr = indicators.get("atr_14") or 0.0
    supports = indicators.get("support") or []
    resistances = indicators.get("resistance") or []
    nearest_support = supports[0] if supports else None
    nearest_resistance = resistances[0] if resistances else None

    stop_loss = compute_stop_loss(entry, atr, nearest_support, defaults)
    stop_loss = enforce_price_limit(stop_loss, entry, price_limit, is_stop=True)
    stop_loss = round_to_tick(stop_loss, tick_size)

    take_profit = compute_take_profit(entry, stop_loss, nearest_resistance, defaults)
    take_profit = enforce_price_limit(take_profit, entry, price_limit, is_stop=False)
    take_profit = round_to_tick(take_profit, tick_size)

    position_size = compute_position_size(
        entry, stop_loss, equity, cash, risk_pct, defaults["max_position_pct"], lot_size
    )

    risk_amount = (entry - stop_loss) * position_size
    reward_amount = (take_profit - entry) * position_size
    rr_ratio = reward_amount / risk_amount if risk_amount > 0 else 0.0

    violations = []

    min_cost = entry * lot_size
    if cash < min_cost:
        violations.append({
            "rule": "cash_sufficiency",
            "message": f"Insufficient cash: {cash:.2f} < min lot cost {min_cost:.2f}",
        })

    if position_size < lot_size:
        violations.append({
            "rule": "lot_constraint",
            "message": f"Position size {position_size} below minimum lot size {lot_size}",
        })

    max_risk = equity * defaults["risk_per_trade_pct"]
    if risk_amount > max_risk:
        violations.append({
            "rule": "risk_cap",
            "message": (
                f"Risk amount {risk_amount:.2f} exceeds max {max_risk:.2f} "
                f"({defaults['risk_per_trade_pct'] * 100:.2f}% of equity)"
            ),
        })

    if rr_ratio < defaults["min_rr"]:
        violations.append({
            "rule": "min_rr",
            "message": f"R/R ratio {rr_ratio:.2f} below minimum {defaults['min_rr']}",
        })

    max_positions = defaults["max_concurrent_positions"]
    if num_positions >= max_positions:
        violations.append({
            "rule": "max_positions",
            "message": f"Already at max positions: {num_positions} >= {max_positions}",
        })

    stop_pct = (stop_loss - entry) / entry * 100
    tp_pct = (take_profit - entry) / entry * 100
    risk_pct_equity = risk_amount / equity * 100 if equity > 0 else 0

    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "entry": round(entry, 4),
        "stop_loss": round(stop_loss, 4),
        "take_profit": round(take_profit, 4),
        "stop_pct": round(stop_pct, 2),
        "tp_pct": round(tp_pct, 2),
        "rr_ratio": round(rr_ratio, 2),
        "position_size": position_size,
        "risk_amount": round(risk_amount, 2),
        "reward_amount": round(reward_amount, 2),
        "risk_pct_equity": round(risk_pct_equity, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Check risk rules and compute trade plan")
    parser.add_argument("--indicators", "-I", required=True, help="Indicators JSON file (from compute_indicators.py)")
    parser.add_argument("--account", "-a", required=True, help="Account JSON file (risk-os format)")
    parser.add_argument("--entry", "-e", type=float, help="Entry price (default: current_price from indicators)")
    parser.add_argument("--risk-pct", type=float, help="Risk per trade as decimal (default: from config/defaults.json)")
    parser.add_argument("--market", "-m", default="US", choices=["US", "HK", "CN"])
    args = parser.parse_args()

    with open(args.indicators) as f:
        indicators = json.load(f)
    with open(args.account) as f:
        account = json.load(f)

    defaults = load_defaults()

    entry = args.entry if args.entry is not None else indicators.get("current_price")
    if entry is None:
        print("Error: --entry required (current_price not in indicators)", file=sys.stderr)
        sys.exit(1)

    risk_pct = args.risk_pct if args.risk_pct is not None else defaults["risk_per_trade_pct"]
    market = args.market or indicators.get("market", "US")

    try:
        result = run_checks(indicators, account, float(entry), risk_pct, market, defaults)
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
