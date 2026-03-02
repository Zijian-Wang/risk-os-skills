#!/usr/bin/env python3
"""Compute technical indicators from OHLCV bars.

Usage:
    python scripts/fetch_data.py --symbol AAPL --market US | python scripts/compute_indicators.py
    python scripts/compute_indicators.py --input /tmp/data.json

Input JSON (from fetch_data.py): { "ohlcv": [...], ... }

Output JSON:
    {
      "symbol": "AAPL",
      "rsi_14": 62.3,
      "macd_line": 1.2,
      "macd_signal": 0.8,
      "macd_histogram": 0.4,
      "atr_14": 3.2,
      "sma_20": 195.0,
      "sma_50": 188.0,
      "sma_200": 175.0,
      "ema_12": 196.0,
      "ema_26": 191.0,
      "volume_sma_20": 45000000,
      "current_price": 197.4,
      "current_volume": 52000000,
      "support": [185.0, 178.5],
      "resistance": [205.0, 212.0],
      "bars_count": 252
    }
"""

import argparse
import json
import math
import sys


def _safe_float(value) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return float(value)


def find_support_resistance(
    lows: list[float],
    highs: list[float],
    current_price: float,
    window: int = 20,
    num_levels: int = 3,
) -> tuple[list[float], list[float]]:
    """Find support/resistance by detecting local extrema, then clustering."""

    def cluster_levels(levels: list[float], tolerance: float = 0.01) -> list[float]:
        if not levels:
            return []
        sorted_levels = sorted(levels)
        clusters: list[list[float]] = [[sorted_levels[0]]]
        for level in sorted_levels[1:]:
            if abs(level - clusters[-1][-1]) / clusters[-1][-1] <= tolerance:
                clusters[-1].append(level)
            else:
                clusters.append([level])
        return [sum(c) / len(c) for c in clusters]

    supports: list[float] = []
    for i in range(window, len(lows) - window):
        if lows[i] == min(lows[i - window : i + window + 1]):
            supports.append(lows[i])

    resistances: list[float] = []
    for i in range(window, len(highs) - window):
        if highs[i] == max(highs[i - window : i + window + 1]):
            resistances.append(highs[i])

    supports = cluster_levels(supports)
    resistances = cluster_levels(resistances)

    supports = sorted([s for s in supports if s < current_price], reverse=True)[:num_levels]
    resistances = sorted([r for r in resistances if r > current_price])[:num_levels]

    return supports, resistances


def compute_indicators(data: dict) -> dict:
    """Compute all technical indicators from the fetch_data.py output dict."""
    import pandas as pd
    from ta.momentum import RSIIndicator
    from ta.trend import MACD, EMAIndicator, SMAIndicator
    from ta.volatility import AverageTrueRange

    bars = data["ohlcv"]
    if not bars:
        raise ValueError("No OHLCV bars in input")

    df = pd.DataFrame(bars)
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["close"] = df["close"].astype(float)
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["volume"] = df["volume"].astype(float)

    rsi = RSIIndicator(close=df["close"], window=14).rsi()
    macd_obj = MACD(close=df["close"], window_slow=26, window_fast=12, window_sign=9)
    macd_line = macd_obj.macd()
    macd_signal = macd_obj.macd_signal()
    macd_hist = macd_obj.macd_diff()
    atr = AverageTrueRange(high=df["high"], low=df["low"], close=df["close"], window=14).average_true_range()
    sma_20 = SMAIndicator(close=df["close"], window=20).sma_indicator()
    sma_50 = SMAIndicator(close=df["close"], window=50).sma_indicator()
    sma_200 = SMAIndicator(close=df["close"], window=200).sma_indicator()
    ema_12 = EMAIndicator(close=df["close"], window=12).ema_indicator()
    ema_26 = EMAIndicator(close=df["close"], window=26).ema_indicator()
    vol_sma = SMAIndicator(close=df["volume"], window=20).sma_indicator()

    last = len(df) - 1
    current_price = float(df["close"].iloc[last])

    lows = df["low"].tolist()
    highs = df["high"].tolist()
    supports, resistances = find_support_resistance(lows, highs, current_price)

    return {
        "symbol": data.get("symbol", ""),
        "market": data.get("market", "US"),
        "rsi_14": _safe_float(rsi.iloc[last]),
        "macd_line": _safe_float(macd_line.iloc[last]),
        "macd_signal": _safe_float(macd_signal.iloc[last]),
        "macd_histogram": _safe_float(macd_hist.iloc[last]),
        "atr_14": _safe_float(atr.iloc[last]),
        "sma_20": _safe_float(sma_20.iloc[last]),
        "sma_50": _safe_float(sma_50.iloc[last]),
        "sma_200": _safe_float(sma_200.iloc[last]),
        "ema_12": _safe_float(ema_12.iloc[last]),
        "ema_26": _safe_float(ema_26.iloc[last]),
        "volume_sma_20": _safe_float(vol_sma.iloc[last]),
        "current_price": current_price,
        "current_volume": int(df["volume"].iloc[last]),
        "support": supports,
        "resistance": resistances,
        "bars_count": len(df),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute technical indicators from OHLCV JSON")
    parser.add_argument("--input", "-i", help="Input JSON file (default: stdin)")
    args = parser.parse_args()

    if args.input:
        with open(args.input) as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    try:
        result = compute_indicators(data)
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
