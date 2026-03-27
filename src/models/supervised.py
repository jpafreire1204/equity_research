"""
Trilha A — Supervised learning with walk-forward validation.
Predicts which tickers will outperform the Ibovespa over the next 12 months.
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

RANDOM_STATE = 42
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

FEATURE_COLS = [
    "net_margin", "roe", "roa", "ebit_margin",
    "debt_to_equity", "net_debt_to_ebit", "current_ratio", "cash_to_revenue",
    "revenue_cagr", "net_income_cagr",
    "volatility_annualized", "max_drawdown", "momentum_6m", "momentum_12m",
    "beta_vs_ibovespa",
    "selic_mean", "ipca_mean", "usdbrl_mean",
]

MODELS = {
    "LogisticRegression": LogisticRegression(
        max_iter=1000, random_state=RANDOM_STATE, solver="lbfgs"
    ),
    "RandomForest": RandomForestClassifier(
        n_estimators=100, max_depth=4, random_state=RANDOM_STATE
    ),
    "GradientBoosting": GradientBoostingClassifier(
        n_estimators=100, max_depth=3, random_state=RANDOM_STATE
    ),
}


def _safe_roc_auc(y_true, y_prob):
    """Return roc_auc or NaN if only one class in y_true."""
    if len(set(y_true)) < 2:
        return np.nan
    return roc_auc_score(y_true, y_prob)


# ---------------------------------------------------------------------------
# Walk-forward validation
# ---------------------------------------------------------------------------

def walk_forward_validation(
    feature_matrix_path: Path | None = None,
) -> tuple[pd.DataFrame, dict]:
    """
    Walk-forward cross-validation. Returns (metrics_df, fitted_models_last_fold).
    """
    feature_matrix_path = feature_matrix_path or DATA_DIR / "feature_matrix.parquet"
    df = pd.read_parquet(feature_matrix_path)

    # Only use 2020-2023 for walk-forward (2024 is inference-only)
    df = df[df["year"] <= 2023].dropna(subset=["label_outperform"]).copy()
    df["label_outperform"] = df["label_outperform"].astype(int)

    years = sorted(df["year"].unique())  # [2020, 2021, 2022, 2023]
    print(f"Walk-forward years available: {years}")

    all_metrics = []

    for i in range(1, len(years)):
        train_years = years[:i]
        test_year = years[i]
        train = df[df["year"].isin(train_years)]
        test = df[df["year"] == test_year]

        if len(train) < 4:
            warnings.warn(
                f"Fold {i}: train has only {len(train)} samples (years {train_years}), skipping."
            )
            continue

        X_train = train[FEATURE_COLS].fillna(0).values
        y_train = train["label_outperform"].values
        X_test = test[FEATURE_COLS].fillna(0).values
        y_test = test["label_outperform"].values

        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)

        for name, model in MODELS.items():
            model_clone = model.__class__(**model.get_params())
            model_clone.fit(X_train, y_train)
            y_pred = model_clone.predict(X_test)
            y_prob = model_clone.predict_proba(X_test)[:, 1]

            metrics = {
                "fold": i,
                "train_years": str(train_years),
                "test_year": test_year,
                "model": name,
                "n_train": len(train),
                "n_test": len(test),
                "accuracy": round(accuracy_score(y_test, y_pred), 3),
                "precision": round(precision_score(y_test, y_pred, zero_division=0), 3),
                "recall": round(recall_score(y_test, y_pred, zero_division=0), 3),
                "f1": round(f1_score(y_test, y_pred, zero_division=0), 3),
                "roc_auc": round(_safe_roc_auc(y_test, y_prob), 3),
            }
            all_metrics.append(metrics)

    metrics_df = pd.DataFrame(all_metrics)
    return metrics_df


def aggregate_metrics(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """Mean ± std of metrics per model across folds."""
    metric_cols = ["accuracy", "precision", "recall", "f1", "roc_auc"]
    rows = []
    for model_name, grp in metrics_df.groupby("model"):
        row = {"model": model_name}
        for col in metric_cols:
            vals = grp[col].dropna()
            row[f"{col}_mean"] = round(vals.mean(), 3)
            row[f"{col}_std"] = round(vals.std(), 3)
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Feature importance
# ---------------------------------------------------------------------------

def extract_feature_importance(
    feature_matrix_path: Path | None = None,
    best_model_name: str | None = None,
    output_path: Path | None = None,
) -> pd.DataFrame:
    """Train best model on 2020-2023 and extract feature importances."""
    feature_matrix_path = feature_matrix_path or DATA_DIR / "feature_matrix.parquet"
    output_path = output_path or DATA_DIR / "feature_importance.parquet"

    df = pd.read_parquet(feature_matrix_path)
    df = df[df["year"] <= 2023].dropna(subset=["label_outperform"]).copy()
    df["label_outperform"] = df["label_outperform"].astype(int)

    X = df[FEATURE_COLS].fillna(0).values
    y = df["label_outperform"].values

    scaler = StandardScaler()
    X = scaler.fit_transform(X)

    if best_model_name is None:
        best_model_name = "GradientBoosting"

    model = MODELS[best_model_name].__class__(**MODELS[best_model_name].get_params())
    model.fit(X, y)

    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    else:
        # LogisticRegression: use absolute coefficients as importance proxy
        importances = np.abs(model.coef_[0])
    fi = pd.DataFrame({
        "feature": FEATURE_COLS,
        "importance": np.round(importances, 3),
    })
    fi = fi.sort_values("importance", ascending=False).reset_index(drop=True)
    fi["rank"] = fi.index + 1

    fi.to_parquet(output_path, index=False)
    print(f"Feature importance saved: {output_path}")
    return fi, model, scaler


# ---------------------------------------------------------------------------
# 2024 Predictions
# ---------------------------------------------------------------------------

def predict_2024(
    feature_matrix_path: Path | None = None,
    output_path: Path | None = None,
) -> pd.DataFrame:
    """Train best model on all labeled data, predict 2024."""
    feature_matrix_path = feature_matrix_path or DATA_DIR / "feature_matrix.parquet"
    output_path = output_path or DATA_DIR / "supervised_predictions_2024.parquet"

    df = pd.read_parquet(feature_matrix_path)

    # Training set: 2020-2023 only (no 2024 leakage)
    train = df[df["year"] <= 2023].dropna(subset=["label_outperform"]).copy()
    train["label_outperform"] = train["label_outperform"].astype(int)

    # Inference set: 2024
    predict_df = df[df["year"] == 2024].copy()

    X_train = train[FEATURE_COLS].fillna(0).values
    y_train = train["label_outperform"].values
    X_pred = predict_df[FEATURE_COLS].fillna(0).values

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_pred = scaler.transform(X_pred)

    # Use GradientBoosting as default best model
    model = GradientBoostingClassifier(
        n_estimators=100, max_depth=3, random_state=RANDOM_STATE
    )
    model.fit(X_train, y_train)

    predict_df = predict_df[["ticker", "sector"]].copy()
    predict_df["label_outperform_pred"] = model.predict(X_pred)
    predict_df["outperform_probability"] = np.round(
        model.predict_proba(X_pred)[:, 1], 3
    )

    predict_df = predict_df.sort_values("outperform_probability", ascending=False).reset_index(drop=True)
    predict_df.to_parquet(output_path, index=False)
    print(f"2024 predictions saved: {output_path}")
    return predict_df


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def run_supervised_pipeline(
    feature_matrix_path: Path | None = None,
) -> dict:
    """Run the full supervised pipeline and return all results."""
    feature_matrix_path = feature_matrix_path or DATA_DIR / "feature_matrix.parquet"

    print("=" * 60)
    print("TRILHA A — Supervised Learning Pipeline")
    print("=" * 60)

    # 1. Walk-forward validation
    print("\n--- Walk-Forward Validation ---")
    metrics_df = walk_forward_validation(feature_matrix_path)
    print(metrics_df.to_string(index=False))

    # 2. Aggregate metrics
    print("\n--- Aggregated Metrics (mean ± std) ---")
    agg = aggregate_metrics(metrics_df)
    print(agg.to_string(index=False))

    # 3. Pick best model by mean roc_auc
    best_row = agg.sort_values("roc_auc_mean", ascending=False).iloc[0]
    best_model_name = best_row["model"]
    print(f"\nBest model: {best_model_name} (mean roc_auc={best_row['roc_auc_mean']})")

    # 4. Feature importance
    print("\n--- Feature Importance ---")
    fi, _, _ = extract_feature_importance(
        feature_matrix_path, best_model_name=best_model_name
    )
    print(fi.head(10).to_string(index=False))

    # 5. 2024 predictions
    print("\n--- 2024 Predictions ---")
    preds = predict_2024(feature_matrix_path)
    print(preds.to_string(index=False))

    return {
        "metrics": metrics_df,
        "aggregated": agg,
        "best_model": best_model_name,
        "feature_importance": fi,
        "predictions_2024": preds,
    }


if __name__ == "__main__":
    run_supervised_pipeline()
