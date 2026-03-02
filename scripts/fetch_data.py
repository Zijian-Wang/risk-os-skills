#!/usr/bin/env python3
"""Fetch OHLCV bars and news for a symbol.

Usage:
    python scripts/fetch_data.py --symbol AAPL --market US
    python scripts/fetch_data.py --symbol AAPL --market US --timeframe 1d --news-days 7

Outputs JSON to stdout:
    { "symbol": "AAPL", "market": "US", "ohlcv": [...], "news": [...], "provider": "yfinance" }

OHLCV bar fields: timestamp (ISO), open, high, low, close, volume
News item fields: title, published_at (ISO), source, url, summary (optional)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

TIMEFRAME_MAP = {
    "1d": ("1d", "1y"),
    "1h": ("1h", "6mo"),
    "4h": ("1h", "6mo"),   # yfinance has no 4h; fetch 1h and caller can resample
    "1w": ("1wk", "5y"),
}
MIN_BARS = 120


def fetch_ohlcv(symbol: str, timeframe: str = "1d") -> list[dict]:
    """Fetch OHLCV bars via yfinance."""
    import yfinance as yf

    interval, period = TIMEFRAME_MAP.get(timeframe, ("1d", "1y"))
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval, auto_adjust=True)

    if df.empty:
        raise RuntimeError(f"No OHLCV data returned for {symbol}")

    df = df.reset_index()
    bars = []
    for _, row in df.iterrows():
        ts = row["Datetime"] if "Datetime" in row else row["Date"]
        if hasattr(ts, "tzinfo") and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        bars.append(
            {
                "timestamp": ts.isoformat(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]),
            }
        )

    return bars


def fetch_news(symbol: str, days: int = 7) -> list[dict]:
    """Fetch recent news via NewsAPI. Returns [] if NEWSAPI_KEY not set."""
    api_key = os.environ.get("NEWSAPI_KEY")
    if not api_key:
        return []

    import httpx

    from_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": symbol,
        "from": from_date,
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": 20,
        "apiKey": api_key,
    }

    try:
        response = httpx.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        print(f"Warning: news fetch failed: {exc}", file=sys.stderr)
        return []

    articles = data.get("articles", [])
    news = []
    for article in articles:
        published = article.get("publishedAt") or ""
        news.append(
            {
                "title": article.get("title") or "",
                "published_at": published,
                "source": (article.get("source") or {}).get("name") or "",
                "url": article.get("url") or "",
                "summary": article.get("description") or "",
            }
        )
    return news


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch OHLCV + news for a symbol")
    parser.add_argument("--symbol", required=True, help="Ticker symbol (e.g. AAPL)")
    parser.add_argument("--market", default="US", choices=["US", "HK", "CN"], help="Market")
    parser.add_argument("--timeframe", default="1d", choices=["1d", "1h", "4h", "1w"], help="Bar timeframe")
    parser.add_argument("--news-days", type=int, default=7, help="Look-back days for news")
    args = parser.parse_args()

    try:
        bars = fetch_ohlcv(args.symbol, args.timeframe)
        news = fetch_news(args.symbol, args.news_days)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if len(bars) < MIN_BARS:
        print(
            f"Warning: only {len(bars)} bars returned (need {MIN_BARS}+). Indicators may be unreliable.",
            file=sys.stderr,
        )

    result = {
        "symbol": args.symbol,
        "market": args.market,
        "timeframe": args.timeframe,
        "ohlcv": bars,
        "news": news,
        "provider": "yfinance",
        "bars_count": len(bars),
        "news_count": len(news),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
