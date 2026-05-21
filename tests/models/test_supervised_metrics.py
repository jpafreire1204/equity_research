import math

import pytest

from src.models.supervised import (
    MODELS,
    _safe_gini,
    _safe_ks,
    walk_forward_validation,
)


def test_ks_basic():
    assert _safe_ks([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]) == pytest.approx(1.0)
    assert math.isnan(_safe_ks([1, 1, 1], [0.5, 0.6, 0.7]))


def test_gini_from_auc():
    assert _safe_gini([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]) == pytest.approx(1.0)
    g = _safe_gini([0, 1, 0, 1, 0, 1], [0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
    assert math.isnan(g) or abs(g) < 0.5


def test_walk_forward_includes_ks_and_gini():
    results = walk_forward_validation(MODELS["GradientBoosting"])
    assert all("ks" in r for r in results)
    assert all("gini" in r for r in results)


def test_fold3_roc_auc_locked():
    """Regression test: lock the published fold-3 ROC AUC for GradientBoosting.

    If a legitimate data refresh moves this beyond tolerance, update the
    expected value AND the WALK_FORWARD table in
    app/components/methodology_content.py in the same commit.
    """
    results = walk_forward_validation(MODELS["GradientBoosting"])
    fold3 = [r for r in results if r.get("test_year") == 2023]
    assert len(fold3) == 1, "expected exactly one fold-3 record"
    expected = 0.417
    actual = fold3[0]["roc_auc"]
    assert abs(actual - expected) < 0.05, (
        f"fold-3 ROC AUC drifted: expected ~{expected}, got {actual}. "
        "If this is a legitimate data refresh, update the expected value "
        "AND the methodology tab table."
    )
