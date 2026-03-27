"""
Macro scenario sensitivity analysis: bull / base / bear for 2025 outlook.

Banks: sensitive to Selic (spread income) and credit growth.
Utilities: sensitive to BRL depreciation (cost), tariff revisions, and discount rate.
"""

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

SCENARIOS = {
    "bull": {"selic": 0.10, "ipca": 0.04, "usdbrl": 5.20, "gdp_growth": 0.025},
    "base": {"selic": 0.135, "ipca": 0.055, "usdbrl": 5.80, "gdp_growth": 0.015},
    "bear": {"selic": 0.155, "ipca": 0.075, "usdbrl": 6.50, "gdp_growth": -0.005},
}

# Credit growth assumption per scenario
CREDIT_GROWTH = {"bull": 0.08, "base": 0.04, "bear": -0.02}

# Tariff revision assumption per scenario (utilities only)
TARIFF_REVISION = {"bull": 0.05, "base": 0.02, "bear": 0.00}

BASE_SELIC = SCENARIOS["base"]["selic"]
BASE_USDBRL = SCENARIOS["base"]["usdbrl"]


def _adjust_bank(
    base_net_income: float,
    base_pl: float,
    scenario_name: str,
    scenario: dict,
) -> tuple[float, float]:
    """
    Apply bank sensitivity rules.

    - Selic: each 1pp increase → P/L contracts by 0.8x
    - Credit growth: scales net_income proportionally
    """
    # Credit growth effect on net income
    cg = CREDIT_GROWTH[scenario_name]
    adjusted_ni = base_net_income * (1 + cg)

    # Selic effect on P/L
    selic_delta_pp = (scenario["selic"] - BASE_SELIC) * 100
    pl_multiplier = 1 + (selic_delta_pp * -0.008)  # -0.8x per 1pp
    pl_multiplier = max(pl_multiplier, 0.3)  # floor to avoid extreme negatives
    adjusted_pl = base_pl * pl_multiplier if pd.notna(base_pl) else np.nan

    return adjusted_ni, adjusted_pl


def _adjust_utility(
    base_net_income: float,
    base_pl: float,
    scenario_name: str,
    scenario: dict,
) -> tuple[float, float]:
    """
    Apply utility sensitivity rules.

    - BRL depreciation: each 10% weaker → costs +3% (reduces net income)
    - Tariff revision: revenue boost
    - Selic: each 1pp increase → discount rate +0.5pp → P/L contracts by 0.6x
    """
    # FX effect on costs
    fx_change_pct = (scenario["usdbrl"] - BASE_USDBRL) / BASE_USDBRL
    cost_impact = fx_change_pct * 0.30  # 3% per 10% = 0.30 coefficient
    ni_fx = base_net_income * (1 - cost_impact)

    # Tariff revision effect (revenue boost → flows through to NI proportionally)
    tariff = TARIFF_REVISION[scenario_name]
    adjusted_ni = ni_fx * (1 + tariff)

    # Selic effect on P/L
    selic_delta_pp = (scenario["selic"] - BASE_SELIC) * 100
    pl_multiplier = 1 + (selic_delta_pp * -0.006)  # -0.6x per 1pp
    pl_multiplier = max(pl_multiplier, 0.3)
    adjusted_pl = base_pl * pl_multiplier if pd.notna(base_pl) else np.nan

    return adjusted_ni, adjusted_pl


def compute_scenarios(
    multiples_path: Path | None = None,
    income_path: Path | None = None,
    output_path: Path | None = None,
) -> pd.DataFrame:
    """
    Compute adjusted net income, P/L, and implied upside for each ticker × scenario.

    Implied upside = (fair_price / current_price) - 1
    where fair_price = adjusted_net_income / shares × adjusted_pl.
    """
    multiples_path = multiples_path or DATA_DIR / "multiples_2024.parquet"
    income_path = income_path or DATA_DIR / "income_long.parquet"
    output_path = output_path or DATA_DIR / "scenarios_2024.parquet"

    mult = pd.read_parquet(multiples_path)
    income = pd.read_parquet(income_path)

    # Shares outstanding (imported from multiples module)
    from src.valuation.multiples import SHARES_OUTSTANDING, _get_income_2024

    inc24 = _get_income_2024(income)

    rows = []
    for _, mrow in mult.iterrows():
        ticker = mrow["ticker"]
        sector = mrow["sector"]
        close = mrow["close_2024"]
        base_pl = mrow["pl"]

        inc_row = inc24[inc24["ticker"] == ticker]
        base_ni = inc_row["net_income"].values[0] if len(inc_row) > 0 else np.nan
        shares = SHARES_OUTSTANDING.get(ticker, np.nan)
        is_bank = sector == "Bancos"

        for scenario_name, scenario in SCENARIOS.items():
            if is_bank:
                adj_ni, adj_pl = _adjust_bank(
                    base_ni, base_pl, scenario_name, scenario
                )
            else:
                adj_ni, adj_pl = _adjust_utility(
                    base_ni, base_pl, scenario_name, scenario
                )

            # Implied upside: fair_price = EPS_adjusted × adjusted_PL
            if (
                pd.notna(adj_ni)
                and pd.notna(adj_pl)
                and pd.notna(shares)
                and shares > 0
                and close > 0
            ):
                eps_adj = adj_ni * 1_000 / shares  # BRL thousands → BRL per share
                fair_price = eps_adj * adj_pl
                implied_upside = round((fair_price / close) - 1, 3)
            else:
                implied_upside = np.nan

            rows.append({
                "ticker": ticker,
                "sector": sector,
                "scenario": scenario_name,
                "adjusted_net_income": round(adj_ni, 0) if pd.notna(adj_ni) else np.nan,
                "adjusted_pl": round(adj_pl, 2) if pd.notna(adj_pl) else np.nan,
                "implied_upside_pct": implied_upside,
            })

    df = pd.DataFrame(rows)

    # Scenario score: 0–100 (percentile rank of implied_upside within each scenario)
    scores = []
    for scenario_name, grp in df.groupby("scenario"):
        grp = grp.copy()
        valid = grp["implied_upside_pct"].dropna()
        if len(valid) < 2:
            grp["scenario_score"] = 50.0
        else:
            grp["scenario_score"] = (
                grp["implied_upside_pct"]
                .rank(pct=True, method="average")
                .mul(100)
                .round(1)
            )
        scores.append(grp)
    df = pd.concat(scores, ignore_index=True)
    df["scenario_score"] = df["scenario_score"].fillna(0).round(1)

    df.to_parquet(output_path, index=False)
    print(f"Scenarios saved: {output_path}  shape={df.shape}")
    return df


if __name__ == "__main__":
    compute_scenarios()
