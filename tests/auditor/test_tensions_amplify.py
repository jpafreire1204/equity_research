from src.auditor.contracts import ThesisInput
from src.auditor.tensions import detect_tensions


def test_high_conviction_amplifies_medium_to_high():
    thesis = ThesisInput(
        ticker="ITUB4",
        direction="bullish",
        drivers=["fundamentals_quality"],
        convictions={"fundamentals_quality": 10},
    )
    evidence = {
        "fundamentals_quality": {
            "roe_2024": 0.15,
            "roe_2023": 0.18,
            "net_margin_2024": 0.10,
            "net_margin_2023": 0.10,
        }
    }
    tens = detect_tensions(thesis, evidence)
    assert len(tens) == 1
    assert tens[0].severity == "high"
    assert "10/10" in tens[0].finding


def test_low_conviction_dampens_high_to_medium():
    thesis = ThesisInput(
        ticker="ITUB4",
        direction="bullish",
        drivers=["fundamentals_quality"],
        convictions={"fundamentals_quality": 2},
    )
    evidence = {
        "fundamentals_quality": {
            "roe_2024": 0.15,
            "roe_2023": 0.20,
            "net_margin_2024": 0.08,
            "net_margin_2023": 0.12,
        }
    }
    tens = detect_tensions(thesis, evidence)
    assert tens[0].severity == "medium"
