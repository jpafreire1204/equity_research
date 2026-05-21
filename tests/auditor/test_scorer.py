from src.auditor.contracts import ThesisInput, Tension
from src.auditor.scorer import compute_score


def _thesis(convs):
    return ThesisInput(
        ticker="ITUB4",
        direction="bullish",
        drivers=list(convs.keys()),
        convictions=convs,
    )


def test_no_tensions_perfect_score():
    t = _thesis({"fundamentals_quality": 8})
    score, gap, verdict = compute_score(t, [])
    assert score == 100.0
    assert gap == 0.0
    assert verdict == "sustentavel"


def test_high_conviction_with_tension_amplifies_gap():
    t = _thesis({"fundamentals_quality": 10})
    tens = [
        Tension(
            driver="fundamentals_quality",
            severity="high",
            finding="x",
            evidence={},
        )
    ]
    score, gap, verdict = compute_score(t, tens)
    assert score == 75.0
    assert gap == 100.0
    assert verdict == "sustentavel"


def test_low_conviction_with_tension_no_gap():
    t = _thesis({"fundamentals_quality": 3})
    tens = [
        Tension(
            driver="fundamentals_quality",
            severity="high",
            finding="x",
            evidence={},
        )
    ]
    score, gap, verdict = compute_score(t, tens)
    assert score == 75.0
    assert gap == 0.0
