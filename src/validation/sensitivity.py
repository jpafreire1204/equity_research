"""Sensitivity analysis for the Thesis Auditor.

For each curated historical thesis, holds all drivers' convictions at a neutral
baseline (DEFAULT_CONVICTION) and perturbs one driver at a time by ±DELTA,
recording how the verdict, consistency score, and conviction-gap score move.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.auditor.audit import audit_thesis
from src.auditor.contracts import ThesisInput

DEFAULT_CONVICTION = 7
DELTA = 2

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_THESES = _REPO_ROOT / "data" / "validation" / "curated_theses.json"
_DEFAULT_OUTPUT = _REPO_ROOT / "data" / "validation" / "sensitivity_results.parquet"


def _load_theses(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _build_thesis(record: dict, override: dict[str, int] | None = None) -> ThesisInput:
    drivers = list(record["drivers"])
    convictions = {d: DEFAULT_CONVICTION for d in drivers}
    if override:
        convictions.update(override)
    return ThesisInput(
        ticker=record["ticker"],
        direction=record["direction"],
        drivers=drivers,
        convictions=convictions,
    )


def run_sensitivity_analysis(
    theses_path: Path | None = None,
    output_path: Path | None = None,
) -> pd.DataFrame:
    """Audit every (thesis, driver, ±DELTA) cell. Returns a tidy DataFrame."""
    theses_path = theses_path or _DEFAULT_THESES
    theses = _load_theses(theses_path)

    rows: list[dict] = []
    for thesis_id, t in enumerate(theses):
        baseline = audit_thesis(_build_thesis(t))
        for driver in t["drivers"]:
            for sign, label in [(+DELTA, "up"), (-DELTA, "down")]:
                new_conv = max(1, min(10, DEFAULT_CONVICTION + sign))
                perturbed = audit_thesis(
                    _build_thesis(t, override={driver: new_conv})
                )
                rows.append({
                    "thesis_id": thesis_id,
                    "ticker": t["ticker"],
                    "direction": t["direction"],
                    "driver_perturbed": driver,
                    "direction_perturbation": label,
                    "baseline_verdict": baseline.verdict,
                    "new_verdict": perturbed.verdict,
                    "baseline_score": baseline.consistency_score,
                    "new_score": perturbed.consistency_score,
                    "delta_score": perturbed.consistency_score - baseline.consistency_score,
                    "baseline_gap": baseline.conviction_gap_score,
                    "new_gap": perturbed.conviction_gap_score,
                    "delta_gap": perturbed.conviction_gap_score - baseline.conviction_gap_score,
                    "verdict_changed": perturbed.verdict != baseline.verdict,
                })

    df = pd.DataFrame(rows)
    df["driver_perturbed"] = df["driver_perturbed"].astype(str)
    df["direction_perturbation"] = df["direction_perturbation"].astype(str)

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, index=False)

    return df


def summarize(df: pd.DataFrame) -> dict:
    """Aggregate metrics for the methodology tab."""
    by_driver = (
        df.groupby("driver_perturbed")
        .agg(
            flip_rate=("verdict_changed", "mean"),
            mean_abs_score_delta=("delta_score", lambda x: x.abs().mean()),
            mean_abs_gap_delta=("delta_gap", lambda x: x.abs().mean()),
            n=("verdict_changed", "size"),
        )
        .round(3)
        .reset_index()
    )
    return {
        "total": int(len(df)),
        "flip_rate": float(df["verdict_changed"].mean()),
        "mean_abs_score_delta": float(df["delta_score"].abs().mean()),
        "mean_abs_gap_delta": float(df["delta_gap"].abs().mean()),
        "by_driver": by_driver,
    }


if __name__ == "__main__":
    df = run_sensitivity_analysis(output_path=_DEFAULT_OUTPUT)
    s = summarize(df)
    print(f"Wrote {s['total']} perturbations to {_DEFAULT_OUTPUT}")
    print("\n=== AGGREGATE ===")
    print(f"Verdict flip rate:    {s['flip_rate']:.1%}")
    print(f"Mean |delta_score|:   {s['mean_abs_score_delta']:.2f}")
    print(f"Mean |delta_gap|:     {s['mean_abs_gap_delta']:.2f}")
    print("\n=== BY DRIVER ===")
    print(s["by_driver"].to_string(index=False))
