"""Compute ground truth for a thesis: 6-month forward return vs Ibovespa, ±5% dead zone."""
from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

PRICES_PATH = Path("data/processed/prices_daily.parquet")
IBOV_TICKER = "IBOV"
HOLDING_DAYS = 180
DEAD_ZONE_PCT = 5.0  # |alpha| < 5% → inconclusive


@lru_cache(maxsize=1)
def _prices() -> pd.DataFrame:
    if not PRICES_PATH.exists():
        raise FileNotFoundError(f"Missing prices file: {PRICES_PATH}")
    df = pd.read_parquet(PRICES_PATH)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df[["date", "ticker", "close"]].sort_values(["ticker", "date"]).reset_index(drop=True)


def _last_price_date() -> date:
    return _prices()["date"].max()


def _close_on_or_after(ticker: str, target: date) -> tuple[date | None, float | None]:
    """Closing price on the next available trading day at or after `target`."""
    df = _prices()
    sub = df[(df["ticker"] == ticker) & (df["date"] >= target)]
    if sub.empty:
        return None, None
    row = sub.iloc[0]
    return row["date"], float(row["close"])


def _outcome(direction: str, alpha_pct: float) -> str:
    """Map alpha (in %, e.g. 7.3 means +7.3pp) to outcome with ±DEAD_ZONE_PCT."""
    if abs(alpha_pct) < DEAD_ZONE_PCT:
        return "inconclusive"
    if direction == "bullish":
        return "sustained" if alpha_pct >= DEAD_ZONE_PCT else "failed"
    if direction == "bearish":
        return "sustained" if alpha_pct <= -DEAD_ZONE_PCT else "failed"
    raise ValueError(f"Invalid direction: {direction!r}")


def compute_ground_truth(ticker: str, publication_date: str, direction: str) -> dict[str, Any]:
    """Compute 6m alpha vs Ibovespa.

    Returns dict with publication_date, evaluation_date, ticker_return_pct,
    ibov_return_pct, alpha_pct (in pp), outcome (sustained/failed/inconclusive/out_of_sample).
    """
    pub = date.fromisoformat(publication_date)
    target_eval = pub + timedelta(days=HOLDING_DAYS)
    last_avail = _last_price_date()

    if target_eval > last_avail:
        return {
            "publication_date": pub.isoformat(),
            "evaluation_date": None,
            "ticker_return_pct": None,
            "ibov_return_pct": None,
            "alpha_pct": None,
            "outcome": "out_of_sample",
        }

    pub_dt, p0 = _close_on_or_after(ticker, pub)
    eval_dt, p1 = _close_on_or_after(ticker, target_eval)
    pub_ib_dt, ib0 = _close_on_or_after(IBOV_TICKER, pub)
    eval_ib_dt, ib1 = _close_on_or_after(IBOV_TICKER, target_eval)

    if None in (p0, p1, ib0, ib1):
        return {
            "publication_date": pub.isoformat(),
            "evaluation_date": eval_dt.isoformat() if eval_dt else None,
            "ticker_return_pct": None,
            "ibov_return_pct": None,
            "alpha_pct": None,
            "outcome": "out_of_sample",
        }

    ticker_ret = (p1 / p0 - 1.0) * 100.0
    ibov_ret = (ib1 / ib0 - 1.0) * 100.0
    alpha = ticker_ret - ibov_ret

    return {
        "publication_date": pub.isoformat(),
        "evaluation_date": eval_dt.isoformat(),
        "ticker_return_pct": round(ticker_ret, 2),
        "ibov_return_pct": round(ibov_ret, 2),
        "alpha_pct": round(alpha, 2),
        "outcome": _outcome(direction, alpha),
    }


def assert_ibov_available() -> None:
    df = _prices()
    if IBOV_TICKER not in set(df["ticker"].unique()):
        raise RuntimeError(
            f"Ibovespa ticker {IBOV_TICKER!r} not present in {PRICES_PATH}. "
            "Cannot run validation without benchmark — see Step 5 of validation runbook."
        )
