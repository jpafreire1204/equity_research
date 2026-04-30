"""Orchestrator: curated theses → audits → ground truth → results.csv."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.auditor.audit import audit_thesis
from src.validation.extraction import load_curated, to_thesis_input
from src.validation.ground_truth import compute_ground_truth

DATA_DIR = Path("data/validation")
RESULTS_PATH = DATA_DIR / "results.csv"

# Auditor verdict → predicted ground-truth outcome
VERDICT_TO_PREDICTION = {
    "sustentavel": "sustained",
    "sustentavel_com_ressalvas": "inconclusive",
    "fragilizada": "failed",
}


def _match(prediction: str, outcome: str) -> str:
    if outcome in ("out_of_sample",):
        return "n/a"
    if prediction == outcome:
        return "yes"
    # Soft credit: predicted inconclusive (ressalvas) and either side won by a margin.
    if prediction == "inconclusive" and outcome in ("sustained", "failed"):
        return "partial"
    if outcome == "inconclusive" and prediction in ("sustained", "failed"):
        return "partial"
    return "no"


def run_validation() -> pd.DataFrame:
    rows: list[dict[str, Any]] = load_curated()
    if not rows:
        raise RuntimeError(
            f"No curated theses in {DATA_DIR / 'curated_theses.json'}. "
            "Run Step 4 (extraction) first."
        )

    out: list[dict[str, Any]] = []
    for row in rows:
        thesis = to_thesis_input(row)
        result = audit_thesis(thesis)
        gt = compute_ground_truth(thesis.ticker, row["published_date"], thesis.direction)
        prediction = VERDICT_TO_PREDICTION[result.verdict]
        out.append({
            "url": row.get("url", ""),
            "ticker": thesis.ticker,
            "direction": thesis.direction,
            "drivers": "|".join(thesis.drivers),
            "publication_date": row["published_date"],
            "rationale": thesis.rationale,
            "consistency_score": result.consistency_score,
            "verdict": result.verdict,
            "num_tensions": len(result.tensions),
            "tensions_drivers": "|".join(t.driver for t in result.tensions),
            "tensions_severity": "|".join(t.severity for t in result.tensions),
            "semantic_similarity": result.semantic_similarity,
            "ticker_return_pct": gt["ticker_return_pct"],
            "ibov_return_pct": gt["ibov_return_pct"],
            "alpha_pct": gt["alpha_pct"],
            "evaluation_date": gt["evaluation_date"],
            "ground_truth_outcome": gt["outcome"],
            "auditor_prediction": prediction,
            "match": _match(prediction, gt["outcome"]),
        })

    df = pd.DataFrame(out)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RESULTS_PATH, index=False, encoding="utf-8")
    return df
