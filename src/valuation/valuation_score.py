"""
Valuation score integration: combine multiples, scenarios, and prior scores
into a single ultimate ranking with Buy / Hold / Sell recommendations.
"""

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


def _percentile_score(series: pd.Series, invert: bool = False) -> pd.Series:
    """
    Convert a series to percentile-rank scores (0–100).

    Parameters
    ----------
    series : pd.Series
        Raw values.
    invert : bool
        If True, lower raw values get higher scores (cheaper = better).
    """
    if invert:
        ranked = (-series).rank(pct=True, method="average", na_option="bottom")
    else:
        ranked = series.rank(pct=True, method="average", na_option="bottom")
    return (ranked * 100).round(1)


def compute_valuation_score(
    multiples_path: Path | None = None,
    scenarios_path: Path | None = None,
    output_path: Path | None = None,
) -> pd.DataFrame:
    """
    Compute valuation score (0–100) per ticker.

    Components:
        discount_premium_pl (inverted)       30%
        discount_premium_pvp (inverted)      20%
        discount_premium_ev_ebitda (inverted) 20%
        base_scenario implied_upside_pct     30%
    """
    multiples_path = multiples_path or DATA_DIR / "multiples_2024.parquet"
    scenarios_path = scenarios_path or DATA_DIR / "scenarios_2024.parquet"
    output_path = output_path or DATA_DIR / "valuation_score_2024.parquet"

    mult = pd.read_parquet(multiples_path)
    scen = pd.read_parquet(scenarios_path)

    # Base scenario upside
    base = scen[scen["scenario"] == "base"][["ticker", "implied_upside_pct"]].rename(
        columns={"implied_upside_pct": "base_upside_pct"}
    )
    df = mult.merge(base, on="ticker", how="left")

    # Component scores (inverted = cheaper is better)
    s_pl = _percentile_score(df["discount_premium_pl"], invert=True)
    s_pvp = _percentile_score(df["discount_premium_pvp"], invert=True)
    s_ev = _percentile_score(df["discount_premium_ev_ebitda"], invert=True)
    s_upside = _percentile_score(df["base_upside_pct"], invert=False)

    df["valuation_score"] = (
        s_pl * 0.30 + s_pvp * 0.20 + s_ev * 0.20 + s_upside * 0.30
    ).round(1)

    df.to_parquet(output_path, index=False)
    print(f"Valuation score saved: {output_path}  shape={df.shape}")
    return df


def build_ultimate_scores(
    master_path: Path | None = None,
    valuation_path: Path | None = None,
    scenarios_path: Path | None = None,
    output_path: Path | None = None,
) -> pd.DataFrame:
    """
    Build ultimate scores with Buy/Hold/Sell recommendations.

    ultimate_score = 50% final_score + 30% valuation_score + 20% outperform_probability×100

    Recommendations:
        >= 65 → Buy
        45–64 → Hold
        < 45  → Sell
    """
    master_path = master_path or DATA_DIR / "master_scores_final.parquet"
    valuation_path = valuation_path or DATA_DIR / "valuation_score_2024.parquet"
    scenarios_path = scenarios_path or DATA_DIR / "scenarios_2024.parquet"
    output_path = output_path or DATA_DIR / "ultimate_scores_2024.parquet"

    master = pd.read_parquet(master_path)
    val = pd.read_parquet(valuation_path)
    scen = pd.read_parquet(scenarios_path)

    # Pivot scenarios for upside columns
    upside_pivot = scen.pivot_table(
        index="ticker", columns="scenario", values="implied_upside_pct"
    ).reset_index()
    upside_pivot.columns = ["ticker", "base_upside_pct", "bear_upside_pct", "bull_upside_pct"]

    # Merge valuation into master
    df = master.merge(
        val[["ticker", "valuation_score", "valuation_flag"]],
        on="ticker",
        how="left",
    )
    df = df.merge(upside_pivot, on="ticker", how="left")

    # Ultimate score
    df["ultimate_score"] = (
        df["final_score"] * 0.50
        + df["valuation_score"].fillna(50) * 0.30
        + df["outperform_probability"].fillna(0.5) * 100 * 0.20
    ).round(1)

    # Recommendation
    df["recommendation"] = pd.cut(
        df["ultimate_score"],
        bins=[-np.inf, 45, 65, np.inf],
        labels=["Sell", "Hold", "Buy"],
    )

    # Ultimate rank
    df["ultimate_rank"] = df["ultimate_score"].rank(ascending=False, method="min").astype(int)

    df = df.sort_values("ultimate_rank").reset_index(drop=True)
    df.to_parquet(output_path, index=False)
    print(f"Ultimate scores saved: {output_path}  shape={df.shape}")
    return df


def run_valuation_pipeline() -> dict:
    """Run the full valuation pipeline end-to-end."""
    from src.valuation.multiples import compute_multiples
    from src.valuation.scenarios import compute_scenarios

    print("=" * 60)
    print("VALUATION PIPELINE")
    print("=" * 60)

    print("\n--- Step 1: Multiples ---")
    mult = compute_multiples()

    print("\n--- Step 2: Scenarios ---")
    scen = compute_scenarios()

    print("\n--- Step 3: Valuation Score ---")
    val = compute_valuation_score()

    print("\n--- Step 4: Ultimate Scores ---")
    ultimate = build_ultimate_scores()

    print("\n--- Final Ranking ---")
    display = ultimate[
        ["ticker", "sector", "ultimate_rank", "ultimate_score",
         "recommendation", "final_score", "valuation_score",
         "outperform_probability", "cluster_label"]
    ]
    print(display.to_string(index=False))

    return {
        "multiples": mult,
        "scenarios": scen,
        "valuation_score": val,
        "ultimate": ultimate,
    }


if __name__ == "__main__":
    run_valuation_pipeline()
