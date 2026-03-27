"""
Feature engineering: build unified feature matrix for supervised + unsupervised modeling.
Merges KPIs, macro indicators, and market data into a single table per ticker-year.
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

RANDOM_STATE = 42
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


# ---------------------------------------------------------------------------
# Price-derived features
# ---------------------------------------------------------------------------

def _compute_beta(prices: pd.DataFrame) -> pd.DataFrame:
    """Compute annual beta of each ticker vs IBOV."""
    ibov = (
        prices[prices["ticker"] == "IBOV"][["date", "daily_return"]]
        .rename(columns={"daily_return": "daily_return_ibov"})
    )

    tickers = prices[prices["ticker"] != "IBOV"].copy()
    tickers = tickers.merge(ibov, on="date", how="inner")
    tickers["year"] = tickers["date"].dt.year

    records = []
    for (ticker, year), grp in tickers.groupby(["ticker", "year"]):
        rets = grp[["daily_return", "daily_return_ibov"]].dropna()
        if len(rets) < 20:
            beta = np.nan
        else:
            cov = rets.cov()
            beta = (
                cov.loc["daily_return", "daily_return_ibov"]
                / rets["daily_return_ibov"].var()
            )
        records.append({"ticker": ticker, "year": year, "beta_vs_ibovespa": beta})

    return pd.DataFrame(records)


def _compute_forward_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Compute forward 12-month return per ticker per year.
    forward_return_12m = price(end of year T+1) / price(end of year T) - 1
    """
    # Last trading day price per ticker per year
    prices = prices.copy()
    prices["year"] = prices["date"].dt.year

    year_end = (
        prices.sort_values("date")
        .groupby(["ticker", "year"])
        .last()
        .reset_index()[["ticker", "year", "close"]]
    )

    # Self-join to get next year's close
    year_end_next = year_end.copy()
    year_end_next["year"] = year_end_next["year"] - 1
    year_end_next = year_end_next.rename(columns={"close": "close_next_year"})

    merged = year_end.merge(year_end_next[["ticker", "year", "close_next_year"]],
                            on=["ticker", "year"], how="left")
    merged["forward_return_12m"] = merged["close_next_year"] / merged["close"] - 1

    # IBOV forward return for outperform label
    ibov = merged[merged["ticker"] == "IBOV"][["year", "forward_return_12m"]].rename(
        columns={"forward_return_12m": "ibov_return_12m"}
    )

    result = merged[merged["ticker"] != "IBOV"].merge(ibov, on="year", how="left")
    result["label_outperform"] = (
        result["forward_return_12m"] > result["ibov_return_12m"]
    ).astype("Int64")

    # Where forward return is NaN, label is also NaN
    result.loc[result["forward_return_12m"].isna(), "label_outperform"] = pd.NA

    return result[["ticker", "year", "forward_return_12m", "label_outperform"]]


# ---------------------------------------------------------------------------
# Macro features (annual)
# ---------------------------------------------------------------------------

def _compute_macro_annual(macro: pd.DataFrame) -> pd.DataFrame:
    """Aggregate monthly macro indicators to annual means."""
    macro = macro.copy()
    macro["year"] = macro["date"].dt.year
    annual = macro.groupby("year").agg(
        selic_mean=("selic_daily", "mean"),
        ipca_mean=("ipca_monthly", "mean"),
        usdbrl_mean=("usdbrl", "mean"),
    ).reset_index()
    return annual


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def build_feature_matrix(
    kpis_path: Path | None = None,
    prices_path: Path | None = None,
    macro_path: Path | None = None,
    output_path: Path | None = None,
) -> pd.DataFrame:
    """Build and save the unified feature matrix."""
    kpis_path = kpis_path or DATA_DIR / "kpis_wide.parquet"
    prices_path = prices_path or DATA_DIR / "prices_daily.parquet"
    macro_path = macro_path or DATA_DIR / "macro_monthly.parquet"
    output_path = output_path or DATA_DIR / "feature_matrix.parquet"

    # --- Load ---
    kpis = pd.read_parquet(kpis_path)
    prices = pd.read_parquet(prices_path)
    macro = pd.read_parquet(macro_path)

    # --- Beta ---
    beta = _compute_beta(prices)
    df = kpis.merge(beta, on=["ticker", "year"], how="left")

    # --- Macro annual ---
    macro_annual = _compute_macro_annual(macro)
    df = df.merge(macro_annual, on="year", how="left")

    # --- Forward returns & label ---
    fwd = _compute_forward_returns(prices)
    df = df.merge(fwd, on=["ticker", "year"], how="left")

    # --- Sort & save ---
    df = df.sort_values(["year", "ticker"]).reset_index(drop=True)
    df.to_parquet(output_path, index=False)
    print(f"Feature matrix saved: {output_path}  shape={df.shape}")
    return df


if __name__ == "__main__":
    build_feature_matrix()
