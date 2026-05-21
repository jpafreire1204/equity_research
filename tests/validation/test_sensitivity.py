from src.validation.sensitivity import run_sensitivity_analysis


_REQUIRED_COLS = {
    "thesis_id", "ticker", "driver_perturbed", "direction_perturbation",
    "baseline_verdict", "new_verdict", "delta_score", "delta_gap",
    "verdict_changed",
}


def test_sensitivity_runs_and_returns_dataframe(tmp_path):
    out = tmp_path / "sens.parquet"
    df = run_sensitivity_analysis(output_path=out)
    assert len(df) > 0
    assert out.exists()
    assert _REQUIRED_COLS.issubset(set(df.columns))


def test_perturbations_are_balanced(tmp_path):
    df = run_sensitivity_analysis(output_path=tmp_path / "x.parquet")
    up = (df["direction_perturbation"] == "up").sum()
    down = (df["direction_perturbation"] == "down").sum()
    assert up == down
