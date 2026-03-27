"""
Composite fundamental score module (Aula 3).

Builds a 0-100 score per ticker for the reference year (2024) by:
1. Percentile-ranking each KPI across the full 10-company universe
2. Inverting KPIs where lower is better (volatility, drawdown, debt)
3. Applying fixed weights and scaling to 0-100

Weight table
------------
  KPI                          Weight  Direction
  roe                          20%     higher is better
  net_margin                   15%     higher is better
  revenue_cagr                 15%     higher is better
  net_income_cagr              10%     higher is better
  volatility_annualized        10%     lower is better (inverted)
  max_drawdown                 10%     lower is better (inverted)
  momentum_12m                 10%     higher is better
  debt_to_equity               10%     lower is better (inverted)
  ─────────────────────────────────
  Total                       100%
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import percentileofscore

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

REFERENCE_YEAR = 2024

# KPI weights: (kpi_name, weight, invert)
# invert=True means lower is better
WEIGHTS = [
    ("roe",                     0.20, False),
    ("net_margin",              0.15, False),
    ("revenue_cagr",            0.15, False),
    ("net_income_cagr",         0.10, False),
    ("volatility_annualized",   0.10, True),
    ("max_drawdown",            0.10, True),
    ("momentum_12m",            0.10, False),
    ("debt_to_equity",          0.10, True),
]


def _percentile_score(series: pd.Series, value: float, invert: bool) -> float:
    """
    Compute the percentile rank of *value* within *series* (0-1 scale).

    If invert=True, the score is 1 - percentile (lower raw value = higher score).
    NaN values in the series are ignored; NaN input returns NaN.
    """
    if pd.isna(value):
        return np.nan
    clean = series.dropna()
    if len(clean) == 0:
        return np.nan
    pct = percentileofscore(clean, value, kind="rank") / 100
    return (1 - pct) if invert else pct


def build_scores() -> pd.DataFrame:
    """
    Build composite scores for the reference year.

    Reads kpis_wide.parquet, filters to REFERENCE_YEAR, scores each KPI,
    computes weighted composite, and ranks overall and within sector.

    Saves to data/processed/scores_2024.parquet.
    Returns the scores DataFrame.
    """
    print(f"[{datetime.now()}] === Score Computation Start ===")

    kpis = pd.read_parquet(PROCESSED_DIR / "kpis_wide.parquet")
    df = kpis[kpis["year"] == REFERENCE_YEAR].copy()

    if df.empty:
        print(f"[{datetime.now()}] ERROR: No KPI data for year {REFERENCE_YEAR}")
        return pd.DataFrame()

    print(f"[{datetime.now()}] Tickers in {REFERENCE_YEAR}: {sorted(df['ticker'].unique())}")

    # For tickers missing 2024 data, fall back to most recent available year
    all_tickers = set(kpis["ticker"].unique())
    present_tickers = set(df["ticker"].unique())
    missing = all_tickers - present_tickers
    if missing:
        print(f"[{datetime.now()}] Tickers missing {REFERENCE_YEAR}: {missing} — using most recent year")
        for ticker in missing:
            ticker_data = kpis[kpis["ticker"] == ticker].sort_values("year")
            if not ticker_data.empty:
                fallback = ticker_data.iloc[[-1]].copy()
                fallback["year"] = REFERENCE_YEAR
                df = pd.concat([df, fallback], ignore_index=True)

    # Compute individual KPI scores
    for kpi_name, weight, invert in WEIGHTS:
        col_score = f"{kpi_name}_score"
        series = df[kpi_name]
        df[col_score] = df[kpi_name].apply(
            lambda x, s=series, inv=invert: _percentile_score(s, x, inv)
        )

    # Compute weighted composite score (0-100)
    score_cols = [f"{kpi}_score" for kpi, _, _ in WEIGHTS]
    weight_vals = [w for _, w, _ in WEIGHTS]

    def _weighted_score(row):
        """Weighted average ignoring NaN scores; rescale weights accordingly."""
        vals = []
        wts = []
        for col, w in zip(score_cols, weight_vals):
            v = row[col]
            if not pd.isna(v):
                vals.append(v)
                wts.append(w)
        if not wts:
            return np.nan
        total_w = sum(wts)
        return sum(v * w / total_w for v, w in zip(vals, wts)) * 100

    df["composite_score"] = df.apply(_weighted_score, axis=1)

    # Rankings
    df["rank_overall"] = df["composite_score"].rank(ascending=False, method="min").astype("Int64")

    df["rank_sector"] = (
        df.groupby("sector")["composite_score"]
        .rank(ascending=False, method="min")
        .astype("Int64")
    )

    # Select output columns
    out_cols = (
        ["ticker", "sector", "composite_score", "rank_overall", "rank_sector"]
        + score_cols
    )
    result = df[out_cols].sort_values("rank_overall").reset_index(drop=True)

    # Save
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    result.to_parquet(PROCESSED_DIR / "scores_2024.parquet", index=False)
    print(f"[{datetime.now()}] Saved scores_2024.parquet — {len(result)} rows")
    print(f"[{datetime.now()}] === Score Computation Complete ===")
    return result


def run():
    """Entry point."""
    return build_scores()


if __name__ == "__main__":
    run()
