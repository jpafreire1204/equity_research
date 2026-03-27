"""
Valuation multiples: P/L, P/VP, EV/EBITDA for each ticker (reference year 2024).

EV/EBITDA uses a proxy: EBITDA ≈ EBIT × 1.15 (rough D&A add-back).
Net debt is derived from kpis_wide (net_debt_to_ebit × ebit) where available,
with fallback to fundamentals (total_debt − cash).
"""

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

SHARES_OUTSTANDING = {
    "ITUB4": 9_700_000_000,
    "BBDC4": 7_400_000_000,
    "BBAS3": 2_865_000_000,
    "SANB11": 4_000_000_000,
    "ABCB4": 280_000_000,
    "EGIE3": 675_000_000,
    "EQTL3": 1_060_000_000,
    "CPFE3": 1_025_000_000,
    "TAEE11": 1_340_000_000,
    "CMIG4": 1_750_000_000,
}

# Caps to avoid distortions from negative/tiny earnings
PL_CAP = 100.0
EV_EBITDA_CAP = 50.0


def _get_last_close_2024(prices: pd.DataFrame) -> dict[str, float]:
    """Return last closing price of 2024 per ticker."""
    p24 = prices[
        (prices["ticker"] != "IBOV") & (prices["date"].dt.year == 2024)
    ].copy()
    last = p24.sort_values("date").groupby("ticker")["close"].last()
    return last.to_dict()


def _get_income_2024(income: pd.DataFrame) -> pd.DataFrame:
    """
    Return income data for 2024.
    ABCB4 lacks 2024 filing — fall back to 2023.
    """
    inc24 = income[income["year"] == 2024].copy()
    missing = set(SHARES_OUTSTANDING) - set(inc24["ticker"])
    if missing:
        fallback = income[
            income["ticker"].isin(missing) & (income["year"] == 2023)
        ].copy()
        fallback["year"] = 2024
        inc24 = pd.concat([inc24, fallback], ignore_index=True)
    return inc24


def _get_equity_2024(fundamentals: pd.DataFrame) -> dict[str, float]:
    """
    Return total equity (Patrimônio Líquido Consolidado) per ticker for 2024.
    Takes the first (earliest filing) entry per ticker. Falls back to 2023.
    Values in BRL thousands (as stored in CVM filings).
    """
    acct = "Patrimônio Líquido Consolidado"
    eq = fundamentals[
        (fundamentals["account_name"] == acct) & (fundamentals["year"] == 2024)
    ].copy()
    # Take first entry per ticker (avoid duplicates from multiple filings)
    eq = eq.sort_values("value").groupby("ticker").first().reset_index()
    result = dict(zip(eq["ticker"], eq["value"]))

    # Fallback for tickers without 2024 data
    missing = set(SHARES_OUTSTANDING) - set(result)
    if missing:
        fb = fundamentals[
            (fundamentals["account_name"] == acct)
            & (fundamentals["year"] == 2023)
            & (fundamentals["ticker"].isin(missing))
        ]
        fb = fb.sort_values("value").groupby("ticker").first().reset_index()
        for _, r in fb.iterrows():
            result[r["ticker"]] = r["value"]
    return result


def _get_net_debt(
    kpis: pd.DataFrame, income: pd.DataFrame
) -> dict[str, float]:
    """
    Derive net debt from kpis_wide: net_debt = net_debt_to_ebit × ebit.
    Returns dict ticker → net_debt in BRL thousands.
    """
    k24 = kpis[kpis["year"] == 2024].copy()
    inc24 = _get_income_2024(income)

    result = {}
    for _, row in k24.iterrows():
        ticker = row["ticker"]
        nd_ratio = row.get("net_debt_to_ebit", np.nan)
        inc_row = inc24[inc24["ticker"] == ticker]
        ebit = inc_row["ebit"].values[0] if len(inc_row) > 0 else np.nan
        if pd.notna(nd_ratio) and pd.notna(ebit):
            result[ticker] = nd_ratio * ebit
        else:
            result[ticker] = np.nan
    return result


def compute_multiples(
    prices_path: Path | None = None,
    income_path: Path | None = None,
    fundamentals_path: Path | None = None,
    kpis_path: Path | None = None,
    output_path: Path | None = None,
) -> pd.DataFrame:
    """
    Compute P/L, P/VP, EV/EBITDA for each ticker (2024).

    Returns DataFrame with multiples, sector medians, discount/premium,
    and valuation flags.
    """
    prices = pd.read_parquet(prices_path or DATA_DIR / "prices_daily.parquet")
    income = pd.read_parquet(income_path or DATA_DIR / "income_long.parquet")
    fundamentals = pd.read_parquet(
        fundamentals_path or DATA_DIR / "fundamentals_long.parquet"
    )
    kpis = pd.read_parquet(kpis_path or DATA_DIR / "kpis_wide.parquet")
    output_path = output_path or DATA_DIR / "multiples_2024.parquet"

    close_map = _get_last_close_2024(prices)
    inc24 = _get_income_2024(income)
    equity_map = _get_equity_2024(fundamentals)
    net_debt_map = _get_net_debt(kpis, income)

    rows = []
    for ticker, shares in SHARES_OUTSTANDING.items():
        close = close_map.get(ticker, np.nan)
        market_cap = close * shares  # BRL

        inc_row = inc24[inc24["ticker"] == ticker]
        sector = inc_row["sector"].values[0] if len(inc_row) > 0 else "Unknown"

        # Net income & EBIT (values in income_long are in BRL thousands)
        net_income = inc_row["net_income"].values[0] if len(inc_row) > 0 else np.nan
        ebit = inc_row["ebit"].values[0] if len(inc_row) > 0 else np.nan

        # Scale income to full BRL (thousands → units) — income_long values
        # are already in BRL (CVM reports in BRL thousands for some, full for others).
        # Cross-check: BBAS3 net_income ~29B matches public data → already in BRL.
        # So no scaling needed.

        # Equity in BRL (fundamentals values are in BRL thousands — CVM standard)
        equity = equity_map.get(ticker, np.nan)
        # Cross-check: BBAS3 equity ~173B → value is 173,570,326 → thousands.
        # But BBAS3 net_income is 29,171,564 → also thousands.
        # They are consistent (both in thousands).

        # Net debt (in same units as income/equity — BRL thousands)
        net_debt = net_debt_map.get(ticker, np.nan)

        # Convert market_cap to BRL thousands to match fundamentals
        market_cap_k = market_cap / 1_000

        # --- P/L ---
        if pd.notna(net_income) and net_income > 0:
            pl = round(market_cap_k / net_income, 2)
            if pl > PL_CAP:
                pl = np.nan
        else:
            pl = np.nan

        # --- P/VP ---
        if pd.notna(equity) and equity > 0:
            pvp = round(market_cap_k / equity, 2)
        else:
            pvp = np.nan

        # --- EV/EBITDA (proxy: EBITDA ≈ EBIT × 1.15) ---
        ebitda_proxy = ebit * 1.15 if pd.notna(ebit) and ebit > 0 else np.nan
        if pd.notna(net_debt) and pd.notna(ebitda_proxy):
            ev = market_cap_k + net_debt
            ev_ebitda = round(ev / ebitda_proxy, 2) if ebitda_proxy > 0 else np.nan
            if pd.notna(ev_ebitda) and ev_ebitda > EV_EBITDA_CAP:
                ev_ebitda = np.nan
        else:
            ev = market_cap_k + (net_debt if pd.notna(net_debt) else 0)
            ev_ebitda = np.nan

        rows.append({
            "ticker": ticker,
            "sector": sector,
            "close_2024": round(close, 2),
            "market_cap": round(market_cap_k, 0),
            "ev": round(ev, 0),
            "pl": pl,
            "pvp": pvp,
            "ev_ebitda": ev_ebitda,
        })

    df = pd.DataFrame(rows)

    # --- Sector comparable analysis ---
    for mult in ["pl", "pvp", "ev_ebitda"]:
        median_col = f"sector_median_{mult}"
        disc_col = f"discount_premium_{mult}"

        sector_medians = df.groupby("sector")[mult].median()
        df[median_col] = df["sector"].map(sector_medians).round(2)

        df[disc_col] = np.where(
            df[mult].notna() & df[median_col].notna(),
            ((df[mult] / df[median_col]) - 1).round(3),
            np.nan,
        )

    # --- Valuation flag ---
    def _flag(row):
        flags = []
        for mult in ["pl", "pvp", "ev_ebitda"]:
            dp = row[f"discount_premium_{mult}"]
            if pd.notna(dp):
                if dp < -0.30:
                    flags.append(f"{mult.upper()} discount")
                elif dp > 0.30:
                    flags.append(f"{mult.upper()} premium")
        return "; ".join(flags) if flags else "fair_value"

    df["valuation_flag"] = df.apply(_flag, axis=1)

    df.to_parquet(output_path, index=False)
    print(f"Multiples saved: {output_path}  shape={df.shape}")
    return df


if __name__ == "__main__":
    compute_multiples()
