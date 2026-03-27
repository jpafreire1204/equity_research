"""
KPI engineering module (Aula 3).

Reads the parquet files produced by the ingestion pipeline and computes
financial KPIs per ticker per year:

  Profitability : net_margin, roe, roa, ebit_margin
  Leverage      : debt_to_equity, net_debt_to_ebit
  Liquidity     : current_ratio, cash_to_revenue
  Growth        : revenue_cagr, net_income_cagr  (2020-2024 CAGR)
  Market        : volatility_annualized, max_drawdown, momentum_6m, momentum_12m

CVM account-code mapping
========================
Utilities (standard CVM layout):
  Total Assets ........... 1
  Current Assets ......... 1.01 (Ativo Circulante)
  Cash ................... 1.01.01
  Current Liabilities .... 2.01 (Passivo Circulante)
  Total Equity (PL) ...... 2.03
  Short-term Debt ........ 2.01.04 (Empréstimos e Financiamentos)
  Long-term Debt ......... 2.02.01 (Empréstimos e Financiamentos)

Banks (COSIF-derived layout):
  Total Assets ........... 1
  Cash ................... 1.01 (Caixa e Equivalentes de Caixa)
  Total Equity (PL) ...... 2.07 or 2.08 (varies — resolved by name match)
  Debt / Current ratio ... N/A — set to NaN (banks fund via deposits, not loans)

Known limitations
-----------------
- ABCB4 has no 2024 fundamentals in the DFP dataset; last available year is 2023.
- ITUB4 has NaN for net_income in all years (account 3.11 absent in DFP).
- net_debt_to_ebit is a proxy for Net Debt/EBITDA (EBITDA not directly available).
- current_ratio and net_debt_to_ebit are meaningless for banks — set to NaN.
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# ── Sector classification ─────────────────────────────────────────────────
BANKS = {"ITUB4", "BBDC4", "BBAS3", "SANB11", "ABCB4"}
UTILITIES = {"EGIE3", "EQTL3", "CPFE3", "TAEE11", "CMIG4"}
SECTOR_MAP = {t: "Bancos" for t in BANKS} | {t: "Energia Elétrica" for t in UTILITIES}

YEARS = [2020, 2021, 2022, 2023, 2024]


# ═══════════════════════════════════════════════════════════════════════════
# Helpers to extract balance-sheet items
# ═══════════════════════════════════════════════════════════════════════════

def _load_fundamentals() -> pd.DataFrame:
    """Load fundamentals and deduplicate (keep last row per ticker/year/account)."""
    df = pd.read_parquet(PROCESSED_DIR / "fundamentals_long.parquet")
    # CVM files contain beginning-of-period and end-of-period rows.
    # Keep the **last** occurrence per group (end-of-period balance).
    df = df.drop_duplicates(subset=["ticker", "year", "account_code"], keep="last")
    return df


def _get_account(fund: pd.DataFrame, ticker: str, year: int,
                 account_code: str) -> float | None:
    """Return the value for a specific account code, or None."""
    row = fund[(fund["ticker"] == ticker) &
               (fund["year"] == year) &
               (fund["account_code"] == account_code)]
    if row.empty:
        return None
    return row["value"].iloc[0]


def _get_equity(fund: pd.DataFrame, ticker: str, year: int) -> float | None:
    """
    Return total equity (Patrimônio Líquido Consolidado).

    Banks use 2.07 or 2.08 depending on the institution; utilities use 2.03.
    We resolve by searching for the name pattern.
    """
    candidates = fund[
        (fund["ticker"] == ticker) &
        (fund["year"] == year) &
        (fund["account_name"].str.contains("Patrimônio Líquido Consolidado", na=False))
    ]
    if candidates.empty:
        # Fallback: try encoded variant (latin-1 artifacts)
        candidates = fund[
            (fund["ticker"] == ticker) &
            (fund["year"] == year) &
            (fund["account_name"].str.contains("Patrim", na=False)) &
            (fund["account_name"].str.contains("quido", na=False)) &
            (fund["account_code"].str.match(r"^2\.(03|07|08)$"))
        ]
    if candidates.empty:
        return None
    return candidates["value"].iloc[0]


# ═══════════════════════════════════════════════════════════════════════════
# Balance-sheet extraction per sector
# ═══════════════════════════════════════════════════════════════════════════

def _extract_bs_items(fund: pd.DataFrame, ticker: str, year: int) -> dict:
    """
    Extract key balance-sheet items for *ticker*/*year*.

    Returns a dict with keys: total_assets, cash, equity,
    current_assets, current_liabilities, total_debt.
    """
    items = {
        "total_assets": _get_account(fund, ticker, year, "1"),
        "equity": _get_equity(fund, ticker, year),
    }

    if ticker in BANKS:
        # Banks: cash = 1.01, debt/current ratio not applicable
        items["cash"] = _get_account(fund, ticker, year, "1.01")
        items["current_assets"] = np.nan      # not meaningful for banks
        items["current_liabilities"] = np.nan  # not meaningful for banks
        items["total_debt"] = np.nan           # banks fund via deposits
    else:
        # Utilities: standard CVM layout
        items["cash"] = _get_account(fund, ticker, year, "1.01.01")
        items["current_assets"] = _get_account(fund, ticker, year, "1.01")
        items["current_liabilities"] = _get_account(fund, ticker, year, "2.01")
        st_debt = _get_account(fund, ticker, year, "2.01.04") or 0
        lt_debt = _get_account(fund, ticker, year, "2.02.01") or 0
        items["total_debt"] = st_debt + lt_debt

    return items


# ═══════════════════════════════════════════════════════════════════════════
# Profitability KPIs
# ═══════════════════════════════════════════════════════════════════════════

def _safe_div(a, b):
    """Return a/b, or NaN when b is None/0/NaN."""
    if a is None or b is None:
        return np.nan
    if np.isnan(a) or np.isnan(b) or b == 0:
        return np.nan
    return a / b


def compute_profitability(income: pd.DataFrame, fund: pd.DataFrame) -> pd.DataFrame:
    """
    Compute profitability KPIs per ticker per year.

    Returns: DataFrame[ticker, year, net_margin, roe, roa, ebit_margin]
    """
    rows = []
    for _, inc in income.iterrows():
        ticker, year = inc["ticker"], inc["year"]
        revenue = inc["revenue"]
        net_income = inc["net_income"]
        ebit = inc["ebit"]

        bs = _extract_bs_items(fund, ticker, year)

        rows.append({
            "ticker": ticker,
            "year": year,
            "net_margin": _safe_div(net_income, revenue),
            "roe": _safe_div(net_income, bs["equity"]),
            "roa": _safe_div(net_income, bs["total_assets"]),
            "ebit_margin": _safe_div(ebit, revenue),
        })

    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════
# Leverage KPIs
# ═══════════════════════════════════════════════════════════════════════════

def compute_leverage(income: pd.DataFrame, fund: pd.DataFrame) -> pd.DataFrame:
    """
    Compute leverage KPIs per ticker per year.

    Returns: DataFrame[ticker, year, debt_to_equity, net_debt_to_ebit]

    Note: For banks, both KPIs are set to NaN (banks use deposits, not
    traditional debt financing).
    """
    rows = []
    for _, inc in income.iterrows():
        ticker, year = inc["ticker"], inc["year"]
        ebit = inc["ebit"]
        bs = _extract_bs_items(fund, ticker, year)

        debt_to_equity = _safe_div(bs["total_debt"], bs["equity"])

        # Net debt = total_debt - cash
        cash = bs["cash"] if bs["cash"] is not None else 0
        total_debt = bs["total_debt"]
        if total_debt is not None and not np.isnan(total_debt):
            net_debt = total_debt - (cash if not np.isnan(cash) else 0)
            net_debt_to_ebit = _safe_div(net_debt, ebit)
        else:
            net_debt_to_ebit = np.nan

        rows.append({
            "ticker": ticker,
            "year": year,
            "debt_to_equity": debt_to_equity,
            "net_debt_to_ebit": net_debt_to_ebit,
        })

    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════
# Liquidity KPIs
# ═══════════════════════════════════════════════════════════════════════════

def compute_liquidity(income: pd.DataFrame, fund: pd.DataFrame) -> pd.DataFrame:
    """
    Compute liquidity KPIs per ticker per year.

    Returns: DataFrame[ticker, year, current_ratio, cash_to_revenue]

    Note: current_ratio is NaN for banks.
    """
    rows = []
    for _, inc in income.iterrows():
        ticker, year = inc["ticker"], inc["year"]
        revenue = inc["revenue"]
        bs = _extract_bs_items(fund, ticker, year)

        rows.append({
            "ticker": ticker,
            "year": year,
            "current_ratio": _safe_div(bs["current_assets"], bs["current_liabilities"]),
            "cash_to_revenue": _safe_div(bs["cash"], revenue),
        })

    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════
# Growth KPIs (CAGR 2020-2024)
# ═══════════════════════════════════════════════════════════════════════════

def compute_growth(income: pd.DataFrame) -> pd.DataFrame:
    """
    Compute CAGR for revenue and net income over 2020-2024.

    Returns: DataFrame[ticker, revenue_cagr, net_income_cagr]
    (one row per ticker, applied to all years in the final merge).
    """
    rows = []
    for ticker in income["ticker"].unique():
        sub = income[income["ticker"] == ticker].sort_values("year")

        first_year = sub["year"].min()
        last_year = sub["year"].max()
        n_years = last_year - first_year
        if n_years <= 0:
            rows.append({"ticker": ticker, "revenue_cagr": np.nan, "net_income_cagr": np.nan})
            continue

        rev_first = sub.loc[sub["year"] == first_year, "revenue"].iloc[0]
        rev_last = sub.loc[sub["year"] == last_year, "revenue"].iloc[0]

        ni_first = sub.loc[sub["year"] == first_year, "net_income"].iloc[0]
        ni_last = sub.loc[sub["year"] == last_year, "net_income"].iloc[0]

        def _cagr(v0, vn, n):
            """Compute CAGR; handle negative or zero base."""
            if v0 is None or vn is None or np.isnan(v0) or np.isnan(vn):
                return np.nan
            if v0 <= 0 or vn <= 0:
                return np.nan
            return (vn / v0) ** (1 / n) - 1

        rows.append({
            "ticker": ticker,
            "revenue_cagr": _cagr(rev_first, rev_last, n_years),
            "net_income_cagr": _cagr(ni_first, ni_last, n_years),
        })

    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════
# Market KPIs
# ═══════════════════════════════════════════════════════════════════════════

def compute_market_kpis(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Compute market-based KPIs per ticker per year.

    Returns: DataFrame[ticker, year, volatility_annualized, max_drawdown,
                        momentum_6m, momentum_12m]

    - volatility: annualized std of daily returns (rolling 252d, last value)
    - max_drawdown: worst peak-to-trough drop within the year
    - momentum_6m/12m: return over last 126/252 trading days of each year
    """
    # Exclude benchmark
    stock_prices = prices[prices["ticker"] != "IBOV"].copy()
    stock_prices = stock_prices.sort_values(["ticker", "date"])

    rows = []

    for ticker, grp in stock_prices.groupby("ticker"):
        grp = grp.sort_values("date").reset_index(drop=True)

        for year in YEARS:
            year_data = grp[grp["date"].dt.year == year]
            if year_data.empty:
                rows.append({
                    "ticker": ticker, "year": year,
                    "volatility_annualized": np.nan,
                    "max_drawdown": np.nan,
                    "momentum_6m": np.nan,
                    "momentum_12m": np.nan,
                })
                continue

            # --- Volatility (rolling 252d on full history, take last value of year) ---
            # Use all data up to end of year for the rolling window
            data_up_to_year = grp[grp["date"].dt.year <= year].copy()
            if len(data_up_to_year) >= 20:
                rolling_vol = data_up_to_year["daily_return"].rolling(
                    window=min(252, len(data_up_to_year))
                ).std() * np.sqrt(252)
                vol = rolling_vol.iloc[-1]
            else:
                vol = np.nan

            # --- Max Drawdown (within the year) ---
            close_year = year_data["close"].values
            peak = np.maximum.accumulate(close_year)
            drawdown = (close_year / peak) - 1
            mdd = drawdown.min()

            # --- Momentum 6m (last 126 trading days of the year) ---
            n_year = len(year_data)
            if n_year >= 2:
                lookback_6m = min(126, n_year)
                mom_6m = (year_data["close"].iloc[-1] / year_data["close"].iloc[-lookback_6m]) - 1
            else:
                mom_6m = np.nan

            # --- Momentum 12m (last 252 trading days ending at year-end) ---
            # Use full history to get 252 days back
            end_idx = data_up_to_year.index[-1]
            if len(data_up_to_year) >= 252:
                start_idx_12m = data_up_to_year.index[-252]
                mom_12m = (data_up_to_year.loc[end_idx, "close"] /
                           data_up_to_year.loc[start_idx_12m, "close"]) - 1
            elif len(data_up_to_year) >= 2:
                mom_12m = (data_up_to_year["close"].iloc[-1] /
                           data_up_to_year["close"].iloc[0]) - 1
            else:
                mom_12m = np.nan

            rows.append({
                "ticker": ticker,
                "year": year,
                "volatility_annualized": vol,
                "max_drawdown": mdd,
                "momentum_6m": mom_6m,
                "momentum_12m": mom_12m,
            })

    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════
# Main pipeline
# ═══════════════════════════════════════════════════════════════════════════

def build_kpis() -> pd.DataFrame:
    """
    Build the full KPI table by merging all categories.

    Saves to data/processed/kpis_wide.parquet.
    Returns the merged DataFrame.
    """
    print(f"[{datetime.now()}] === KPI Engineering Start ===")

    # Load data
    fund = _load_fundamentals()
    income = pd.read_parquet(PROCESSED_DIR / "income_long.parquet")
    prices = pd.read_parquet(PROCESSED_DIR / "prices_daily.parquet")

    print(f"[{datetime.now()}] Loaded: fundamentals={len(fund)}, income={len(income)}, prices={len(prices)}")

    # Compute each KPI group
    print(f"[{datetime.now()}] Computing profitability KPIs ...")
    prof = compute_profitability(income, fund)

    print(f"[{datetime.now()}] Computing leverage KPIs ...")
    lev = compute_leverage(income, fund)

    print(f"[{datetime.now()}] Computing liquidity KPIs ...")
    liq = compute_liquidity(income, fund)

    print(f"[{datetime.now()}] Computing growth KPIs ...")
    growth = compute_growth(income)

    print(f"[{datetime.now()}] Computing market KPIs ...")
    market = compute_market_kpis(prices)

    # Merge all
    kpis = prof.merge(lev, on=["ticker", "year"], how="outer")
    kpis = kpis.merge(liq, on=["ticker", "year"], how="outer")
    kpis = kpis.merge(market, on=["ticker", "year"], how="outer")

    # Growth is ticker-level (not per year) — broadcast to all years
    kpis = kpis.merge(growth, on="ticker", how="left")

    # Add sector
    kpis["sector"] = kpis["ticker"].map(SECTOR_MAP)

    # Reorder columns
    cols = [
        "ticker", "sector", "year",
        "net_margin", "roe", "roa", "ebit_margin",
        "debt_to_equity", "net_debt_to_ebit",
        "current_ratio", "cash_to_revenue",
        "revenue_cagr", "net_income_cagr",
        "volatility_annualized", "max_drawdown",
        "momentum_6m", "momentum_12m",
    ]
    kpis = kpis[cols].sort_values(["ticker", "year"]).reset_index(drop=True)

    # Warn if >30% NaN for any ticker
    for ticker in kpis["ticker"].unique():
        ticker_data = kpis[kpis["ticker"] == ticker].drop(columns=["ticker", "sector", "year"])
        nan_pct = ticker_data.isna().mean().mean()
        if nan_pct > 0.3:
            print(f"[{datetime.now()}] WARNING: {ticker} has {nan_pct:.0%} NaN across KPIs")

    # Save
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    kpis.to_parquet(PROCESSED_DIR / "kpis_wide.parquet", index=False)
    print(f"[{datetime.now()}] Saved kpis_wide.parquet — {len(kpis)} rows")
    print(f"[{datetime.now()}] === KPI Engineering Complete ===")
    return kpis


def run():
    """Entry point."""
    return build_kpis()


if __name__ == "__main__":
    run()
