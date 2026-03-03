#!/usr/bin/env python3
"""Fetch OHLCV bars and news for a symbol.

Usage:
    python scripts/fetch_data.py --symbol AAPL --market US
    python scripts/fetch_data.py --symbol AAPL --market US --timeframe 1d --news-days 7

Outputs JSON to stdout:
    { "symbol": "AAPL", "market": "US", "ohlcv": [...], "news": [...], "provider": "schwab|stooq" }

OHLCV bar fields: timestamp (ISO), open, high, low, close, volume
News item fields: title, published_at (ISO), source, url, summary (optional)

Data source priority:
  US market  → Schwab Market Data API (token from Firebase), fallback Stooq
  HK/CN market → Stooq
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

_PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or None

# Schwab timeframe → (periodType, period, frequencyType, frequency)
_SCHWAB_TIMEFRAME = {
    "1d": ("year", 1, "daily", 1),
    "1h": ("day", 10, "minute", 60),
    "4h": ("day", 10, "minute", 60),  # no native 4h; fetch 60-min
    "1w": ("year", 5, "weekly", 1),
}

MIN_BARS = 120


# ---------------------------------------------------------------------------
# Shared curl_cffi session (SOCKS5 proxy support)
# ---------------------------------------------------------------------------

def _curl_session():
    from curl_cffi.requests import Session
    kwargs = {}
    if _PROXY:
        kwargs["proxies"] = {"https": _PROXY, "http": _PROXY}
    return Session(**kwargs)


# ---------------------------------------------------------------------------
# Schwab helpers
# ---------------------------------------------------------------------------

def _schwab_access_token(session) -> str:
    """Get a fresh Schwab access token via refresh-token grant (token from Firebase)."""
    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        cred_dict = {
            "type": "service_account",
            "project_id": os.environ["FIREBASE_PROJECT_ID"],
            "private_key": os.environ["FIREBASE_PRIVATE_KEY"].replace("\\n", "\n"),
            "client_email": os.environ["FIREBASE_CLIENT_EMAIL"],
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        firebase_admin.initialize_app(credentials.Certificate(cred_dict))

    db = firestore.client()
    uid = os.environ["FIREBASE_USER_UID"]
    acct = db.collection("users").document(uid).get().to_dict()["schwabAccounts"][0]
    refresh_token = acct["refreshToken"]

    resp = session.post(
        "https://api.schwabapi.com/v1/oauth/token",
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        auth=(os.environ["SCHWAB_CLIENT_ID"], os.environ["SCHWAB_CLIENT_SECRET"]),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_ohlcv_schwab(symbol: str, timeframe: str = "1d") -> list[dict]:
    """Fetch OHLCV bars via Schwab Market Data API."""
    period_type, period, freq_type, freq = _SCHWAB_TIMEFRAME.get(timeframe, ("year", 1, "daily", 1))
    session = _curl_session()
    access_token = _schwab_access_token(session)

    resp = session.get(
        "https://api.schwabapi.com/marketdata/v1/pricehistory",
        params={
            "symbol": symbol,
            "periodType": period_type,
            "period": period,
            "frequencyType": freq_type,
            "frequency": freq,
            "needExtendedHoursData": False,
        },
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("empty") or not data.get("candles"):
        raise RuntimeError(f"No Schwab data returned for {symbol}")

    bars = []
    for c in data["candles"]:
        ts = datetime.fromtimestamp(c["datetime"] / 1000, tz=timezone.utc)
        bars.append({
            "timestamp": ts.isoformat(),
            "open": float(c["open"]),
            "high": float(c["high"]),
            "low": float(c["low"]),
            "close": float(c["close"]),
            "volume": int(c["volume"]),
        })
    return bars


# ---------------------------------------------------------------------------
# Stooq fallback
# ---------------------------------------------------------------------------

def fetch_ohlcv_stooq(symbol: str, timeframe: str = "1d") -> list[dict]:
    """Fetch OHLCV bars via Stooq (no auth required, proxy-friendly)."""
    import httpx

    interval_map = {"1d": "d", "1h": "h", "4h": "h", "1w": "w"}
    interval = interval_map.get(timeframe, "d")

    # Stooq uses symbol suffixes for non-US markets
    url = f"https://stooq.com/q/d/l/?s={symbol.lower()}&i={interval}"

    proxy_kwargs = {"proxy": _PROXY} if _PROXY else {}
    resp = httpx.get(url, timeout=15, **proxy_kwargs)
    resp.raise_for_status()

    lines = resp.text.strip().splitlines()
    if len(lines) < 2 or "No data" in resp.text:
        raise RuntimeError(f"No Stooq data for {symbol}")

    # CSV: Date,Open,High,Low,Close,Volume
    bars = []
    for line in lines[1:]:
        parts = line.split(",")
        if len(parts) < 5:
            continue
        try:
            ts = datetime.strptime(parts[0], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            bars.append({
                "timestamp": ts.isoformat(),
                "open": float(parts[1]),
                "high": float(parts[2]),
                "low": float(parts[3]),
                "close": float(parts[4]),
                "volume": int(float(parts[5])) if len(parts) > 5 and parts[5].strip() else 0,
            })
        except (ValueError, IndexError):
            continue
    if not bars:
        raise RuntimeError(f"No parseable Stooq bars for {symbol}")
    return bars


# ---------------------------------------------------------------------------
# Unified fetch with fallback
# ---------------------------------------------------------------------------

def fetch_ohlcv(symbol: str, market: str = "US", timeframe: str = "1d") -> tuple[list[dict], str]:
    """Return (bars, provider_name). US tries Schwab first, then Stooq."""
    if market == "US":
        try:
            bars = fetch_ohlcv_schwab(symbol, timeframe)
            return bars, "schwab"
        except Exception as exc:
            print(f"Warning: Schwab fetch failed ({exc}), falling back to Stooq", file=sys.stderr)

    try:
        bars = fetch_ohlcv_stooq(symbol, timeframe)
        return bars, "stooq"
    except Exception as exc:
        raise RuntimeError(f"All data sources failed for {symbol}: {exc}") from exc


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------

def fetch_news(symbol: str, days: int = 7) -> list[dict]:
    """Fetch recent news via NewsAPI. Returns [] if NEWSAPI_KEY not set."""
    api_key = os.environ.get("NEWSAPI_KEY")
    if not api_key:
        return []

    import httpx

    from_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    params = {
        "q": symbol,
        "from": from_date,
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": 20,
        "apiKey": api_key,
    }
    proxy_kwargs = {"proxy": _PROXY} if _PROXY else {}
    try:
        response = httpx.get("https://newsapi.org/v2/everything", params=params, timeout=15, **proxy_kwargs)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        print(f"Warning: news fetch failed: {exc}", file=sys.stderr)
        return []

    news = []
    for article in data.get("articles", []):
        news.append({
            "title": article.get("title") or "",
            "published_at": article.get("publishedAt") or "",
            "source": (article.get("source") or {}).get("name") or "",
            "url": article.get("url") or "",
            "summary": article.get("description") or "",
        })
    return news


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch OHLCV + news for a symbol")
    parser.add_argument("--symbol", required=True, help="Ticker symbol (e.g. AAPL)")
    parser.add_argument("--market", default="US", choices=["US", "HK", "CN"], help="Market")
    parser.add_argument("--timeframe", default="1d", choices=["1d", "1h", "4h", "1w"], help="Bar timeframe")
    parser.add_argument("--news-days", type=int, default=7, help="Look-back days for news")
    args = parser.parse_args()

    try:
        bars, provider = fetch_ohlcv(args.symbol, args.market, args.timeframe)
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
        "provider": provider,
        "bars_count": len(bars),
        "news_count": len(news),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
