"""Consistency scorer — deterministic point system + conviction-gap measurement."""
from __future__ import annotations

from src.auditor.contracts import Tension, ThesisInput

_TENSION_COST = {"high": 25, "medium": 10, "low": 5}


def compute_score(
    thesis: ThesisInput,
    tensions: list[Tension],
) -> tuple[float, float, str]:
    """Return (consistency_score, conviction_gap_score, verdict).

    consistency_score: 100 minus tension costs, clamped to [0, 100].
    conviction_gap_score: 0-100, higher means user declared high conviction
        on drivers where evidence pushed back. Convictions <= 5 contribute 0.
    """
    score = 100.0
    for t in tensions:
        score -= _TENSION_COST.get(t.severity, 0)
    consistency_score = max(0.0, min(100.0, score))

    drivers_with_tension = {t.driver for t in tensions}
    if drivers_with_tension:
        raw_gap = sum(
            max(0, conv - 5)
            for d, conv in thesis.convictions.items()
            if d in drivers_with_tension
        )
        max_possible = 5 * len(drivers_with_tension)
        conviction_gap_score = (raw_gap / max(max_possible, 1)) * 100
    else:
        conviction_gap_score = 0.0

    if consistency_score >= 70:
        verdict = "sustentavel"
    elif consistency_score >= 40:
        verdict = "sustentavel_com_ressalvas"
    else:
        verdict = "fragilizada"

    return round(consistency_score, 1), round(conviction_gap_score, 1), verdict
