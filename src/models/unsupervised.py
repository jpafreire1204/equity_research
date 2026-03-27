"""
Trilha B — Unsupervised clustering of tickers by financial profile (2024 KPIs).
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

RANDOM_STATE = 42
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

CLUSTER_FEATURE_COLS = [
    "net_margin", "roe", "roa", "ebit_margin",
    "debt_to_equity", "net_debt_to_ebit", "current_ratio", "cash_to_revenue",
    "revenue_cagr", "net_income_cagr",
    "volatility_annualized", "max_drawdown", "momentum_6m", "momentum_12m",
]


def _impute_sector_median(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Impute NaNs with sector median."""
    df = df.copy()
    for col in cols:
        df[col] = df.groupby("sector")[col].transform(
            lambda s: s.fillna(s.median())
        )
        # If entire sector is NaN, fill with global median
        df[col] = df[col].fillna(df[col].median())
    return df


# ---------------------------------------------------------------------------
# Elbow + silhouette
# ---------------------------------------------------------------------------

def find_optimal_k(
    X_scaled: np.ndarray, k_range: range = range(2, 7)
) -> tuple[list[float], list[float], int]:
    """Run KMeans for each k, return inertias, silhouette scores, best k."""
    inertias = []
    silhouettes = []

    for k in k_range:
        km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
        labels = km.fit_predict(X_scaled)
        inertias.append(km.inertia_)
        sil = silhouette_score(X_scaled, labels) if k > 1 else 0.0
        silhouettes.append(round(sil, 3))

    best_idx = int(np.argmax(silhouettes))
    best_k = list(k_range)[best_idx]
    return inertias, silhouettes, best_k


# ---------------------------------------------------------------------------
# Cluster labeling heuristic
# ---------------------------------------------------------------------------

def _label_clusters(profile: pd.DataFrame) -> dict[int, str]:
    """Assign human-readable labels based on cluster mean characteristics."""
    labels = {}
    for cid in profile.index:
        row = profile.loc[cid]
        # Simple heuristic: highest ROE -> "Quality", highest revenue_cagr -> "Growth",
        # highest volatility -> "Risk"
        scores = {
            "Quality": (row.get("roe", 0) or 0) + (row.get("net_margin", 0) or 0),
            "Growth": (row.get("revenue_cagr", 0) or 0) + (row.get("net_income_cagr", 0) or 0),
            "Risk": (row.get("volatility_annualized", 0) or 0) + abs(row.get("max_drawdown", 0) or 0),
        }
        # Pick the label with highest relative score, avoid duplicates
        for label in sorted(scores, key=scores.get, reverse=True):
            if label not in labels.values():
                labels[cid] = label
                break
        else:
            labels[cid] = f"Cluster_{cid}"
    return labels


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_unsupervised_pipeline(
    kpis_path: Path | None = None,
    output_path: Path | None = None,
) -> dict:
    """Run clustering pipeline on 2024 KPIs."""
    kpis_path = kpis_path or DATA_DIR / "kpis_wide.parquet"
    output_path = output_path or DATA_DIR / "clusters_2024.parquet"

    print("=" * 60)
    print("TRILHA B — Unsupervised Clustering Pipeline")
    print("=" * 60)

    # --- Load 2024 KPIs ---
    kpis = pd.read_parquet(kpis_path)
    df = kpis[kpis["year"] == 2024].copy().reset_index(drop=True)
    print(f"2024 KPIs: {len(df)} tickers")

    # --- Impute & scale ---
    df = _impute_sector_median(df, CLUSTER_FEATURE_COLS)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df[CLUSTER_FEATURE_COLS].values)

    # --- Elbow method ---
    k_range = range(2, min(7, len(df)))
    inertias, silhouettes, best_k = find_optimal_k(X_scaled, k_range)
    print(f"\nSilhouette scores: {dict(zip(k_range, silhouettes))}")
    print(f"Best k = {best_k}")

    # --- Final KMeans ---
    km = KMeans(n_clusters=best_k, random_state=RANDOM_STATE, n_init=10)
    df["cluster_id"] = km.fit_predict(X_scaled)

    # --- PCA 2D ---
    pca = PCA(n_components=2, random_state=RANDOM_STATE)
    coords = pca.fit_transform(X_scaled)
    df["pca_x"] = np.round(coords[:, 0], 3)
    df["pca_y"] = np.round(coords[:, 1], 3)
    print(f"PCA explained variance: {np.round(pca.explained_variance_ratio_, 3)}")

    # --- Cluster profiles ---
    profile = df.groupby("cluster_id")[CLUSTER_FEATURE_COLS].mean().round(3)
    cluster_labels = _label_clusters(profile)
    df["cluster_label"] = df["cluster_id"].map(cluster_labels)

    print("\n--- Cluster Profiles ---")
    profile["cluster_label"] = profile.index.map(cluster_labels)
    print(profile.to_string())

    print("\n--- Ticker Assignments ---")
    print(df[["ticker", "sector", "cluster_id", "cluster_label"]].to_string(index=False))

    # --- Save ---
    out = df[["ticker", "sector", "cluster_id", "cluster_label", "pca_x", "pca_y"]]
    out.to_parquet(output_path, index=False)
    print(f"\nClusters saved: {output_path}")

    return {
        "clusters": out,
        "profile": profile,
        "inertias": inertias,
        "silhouettes": silhouettes,
        "k_range": list(k_range),
        "best_k": best_k,
        "pca": pca,
        "scaler": scaler,
        "df_full": df,
    }


if __name__ == "__main__":
    run_unsupervised_pipeline()
