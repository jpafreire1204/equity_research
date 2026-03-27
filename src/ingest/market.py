"""
Market data ingestion module.

Downloads daily OHLCV data from Yahoo Finance v8 chart API for the
10-company universe plus Ibovespa (^BVSP), computes returns, and saves
to parquet.

Uses the raw Yahoo Finance API instead of the yfinance library to avoid
SSL/encoding issues on Windows with non-ASCII usernames.
"""

import json
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# ── Project paths ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# ── Universe ───────────────────────────────────────────────────────────────
TICKERS_B3 = [
    "ITUB4", "BBDC4", "BBAS3", "SANB11", "ABCB4",
    "EGIE3", "EQTL3", "CPFE3", "TAEE11", "CMIG4",
]
BENCHMARK = "^BVSP"

# Yahoo Finance requires .SA suffix for B3 tickers
YF_TICKERS = [f"{t}.SA" for t in TICKERS_B3] + [BENCHMARK]

# Date range (Unix timestamps)
START_DATE = "2020-01-01"
END_DATE = "2025-12-31"

_HEADERS = {"User-Agent": "Mozilla/5.0"}


def _to_unix(date_str: str) -> int:
    """Convert YYYY-MM-DD to Unix timestamp."""
    return int(pd.Timestamp(date_str).timestamp())


def _fetch_yahoo_chart(yf_ticker: str) -> pd.DataFrame | None:
    """
    Fetch daily OHLCV from Yahoo Finance v8 chart API.
    Returns a DataFrame or None on failure.
    """
    encoded = urllib.parse.quote(yf_ticker, safe="")
    period1 = _to_unix(START_DATE)
    period2 = _to_unix(END_DATE)
    url = (
        f"https://query2.finance.yahoo.com/v8/finance/chart/{encoded}"
        f"?period1={period1}&period2={period2}&interval=1d"
        f"&includeAdjustedClose=true&events=div"
    )

    ctx = ssl.create_default_context()
    ctx.load_default_certs()
    req = urllib.request.Request(url, headers=_HEADERS)

    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[{datetime.now()}] WARNING: Failed to fetch {yf_ticker} — {e}")
        return None

    try:
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        quote = result["indicators"]["quote"][0]
        adj = result["indicators"].get("adjclose", [{}])[0]

        df = pd.DataFrame({
            "date": pd.to_datetime(timestamps, unit="s", utc=True),
            "close": adj.get("adjclose", quote["close"]),
            "volume": quote["volume"],
        })
        df["date"] = df["date"].dt.tz_localize(None).dt.normalize()
        return df
    except (KeyError, IndexError, TypeError) as e:
        print(f"[{datetime.now()}] WARNING: Failed to parse {yf_ticker} response — {e}")
        return None


def download_prices() -> pd.DataFrame:
    """
    Download daily OHLCV for all tickers from Yahoo Finance.
    Returns a long-format DataFrame with computed return columns.
    Saves to data/processed/prices_daily.parquet.
    """
    print(f"[{datetime.now()}] Downloading market data for {len(YF_TICKERS)} tickers ...")

    all_frames = []

    for yf_ticker in YF_TICKERS:
        print(f"[{datetime.now()}]   Fetching {yf_ticker} ...")
        raw = _fetch_yahoo_chart(yf_ticker)

        if raw is None or raw.empty:
            print(f"[{datetime.now()}] WARNING: No data for {yf_ticker}")
            continue

        ticker_label = (
            yf_ticker.replace(".SA", "") if yf_ticker != BENCHMARK else "IBOV"
        )
        raw["ticker"] = ticker_label

        raw = raw.dropna(subset=["close"])
        raw = raw.sort_values("date").reset_index(drop=True)

        # Compute returns
        raw["daily_return"] = raw["close"].pct_change()
        raw["log_return"] = np.log(raw["close"] / raw["close"].shift(1))
        raw["cumulative_return"] = (1 + raw["daily_return"]).cumprod() - 1

        raw = raw[["date", "ticker", "close", "volume", "daily_return", "log_return", "cumulative_return"]]
        all_frames.append(raw)

        # Small delay to be respectful to Yahoo's API
        time.sleep(0.5)

    if not all_frames:
        print(f"[{datetime.now()}] ERROR: No market data collected!")
        return pd.DataFrame()

    result = pd.concat(all_frames, ignore_index=True)
    result["date"] = pd.to_datetime(result["date"])

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    result.to_parquet(PROCESSED_DIR / "prices_daily.parquet", index=False)
    print(f"[{datetime.now()}] Saved prices_daily.parquet — {len(result)} rows")
    return result


def run():
    """Run full market data ingestion."""
    print(f"[{datetime.now()}] === Market Data Ingestion Start ===")
    prices = download_prices()
    print(f"[{datetime.now()}] === Market Data Ingestion Complete ===")
    return prices


if __name__ == "__main__":
    run()
