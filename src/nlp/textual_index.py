"""
Textual index module (Aula 4).

Combines transformer sentiment and keyword scores into a single
textual index (0-100) per ticker, then merges it with the existing
fundamental score to produce a master ranking.

Output files:
  - data/processed/textual_index.parquet
  - data/processed/master_scores_2024.parquet
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Weight split: fundamental vs textual
FUNDAMENTAL_WEIGHT = 0.70
TEXTUAL_WEIGHT = 0.30

# Minimum text count — below this we assign neutral index (50)
MIN_TEXT_COUNT = 5


def build_textual_index() -> pd.DataFrame:
    """
    Build a 0-100 textual index per ticker from sentiment_scores.parquet.

    Saves to data/processed/textual_index.parquet.
    Returns the textual index DataFrame.
    """
    print(f"[{datetime.now()}] === Textual Index Start ===")

    sent = pd.read_parquet(PROCESSED_DIR / "sentiment_scores.parquet")

    # Tickers with < MIN_TEXT_COUNT texts get neutral index
    low_text = sent["text_count"] < MIN_TEXT_COUNT

    # Scale sentiment_composite to 0-100 (min-max across tickers with enough data)
    valid = sent.loc[~low_text, "sentiment_composite"]
    if valid.empty or valid.isna().all():
        sent["textual_index"] = 50.0
    else:
        vmin, vmax = valid.min(), valid.max()
        if vmax == vmin:
            sent["textual_index"] = 50.0
        else:
            sent["textual_index"] = (
                (sent["sentiment_composite"] - vmin) / (vmax - vmin) * 100
            )

    # Override low-text tickers
    sent.loc[low_text, "textual_index"] = 50.0
    for _, row in sent[low_text].iterrows():
        print(f"[{datetime.now()}] WARNING: {row['ticker']} has {row['text_count']} texts "
              f"(< {MIN_TEXT_COUNT}) — textual_index set to 50.0 (neutral)")

    # NaN composites also get neutral
    sent.loc[sent["sentiment_composite"].isna(), "textual_index"] = 50.0

    # Sentiment label
    def _label(idx):
        if idx >= 60:
            return "Positive"
        elif idx <= 40:
            return "Negative"
        return "Neutral"

    sent["sentiment_label"] = sent["textual_index"].apply(_label)

    # Key risks / positives (from keyword columns)
    sent["key_risks"] = sent["top_negative_keywords"].apply(
        lambda x: [kw.split("(")[0] for kw in x.split(", ") if kw] if x else []
    )
    sent["key_positives"] = sent["top_positive_keywords"].apply(
        lambda x: [kw.split("(")[0] for kw in x.split(", ") if kw] if x else []
    )

    # Output columns
    out = sent[["ticker", "sector", "textual_index", "sentiment_label",
                "key_risks", "key_positives"]].copy()

    out.to_parquet(PROCESSED_DIR / "textual_index.parquet", index=False)
    print(f"[{datetime.now()}] Saved textual_index.parquet — {len(out)} rows")
    print(f"[{datetime.now()}] === Textual Index Complete ===")
    return out


def build_master_scores() -> pd.DataFrame:
    """
    Merge fundamental score (70%) with textual index (30%) into a master ranking.

    Reads scores_2024.parquet and textual_index.parquet.
    Saves to data/processed/master_scores_2024.parquet.
    Returns the master scores DataFrame.
    """
    print(f"[{datetime.now()}] === Master Score Computation Start ===")

    fund_scores = pd.read_parquet(PROCESSED_DIR / "scores_2024.parquet")
    textual = pd.read_parquet(PROCESSED_DIR / "textual_index.parquet")

    # Rename existing composite_score to fundamental_score
    master = fund_scores.rename(columns={"composite_score": "fundamental_score"})

    # Merge textual index
    master = master.merge(
        textual[["ticker", "textual_index", "sentiment_label", "key_risks", "key_positives"]],
        on="ticker",
        how="left",
    )

    # Fill missing textual_index with 50 (neutral)
    master["textual_index"] = master["textual_index"].fillna(50.0)

    # Compute final score
    master["final_score"] = (
        FUNDAMENTAL_WEIGHT * master["fundamental_score"]
        + TEXTUAL_WEIGHT * master["textual_index"]
    )

    # Rankings
    master["final_rank"] = (
        master["final_score"].rank(ascending=False, method="min").astype("Int64")
    )

    # Keep rank delta for analysis
    master["rank_delta"] = master["rank_overall"].astype(int) - master["final_rank"].astype(int)

    # Sort by final rank
    master = master.sort_values("final_rank").reset_index(drop=True)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    master.to_parquet(PROCESSED_DIR / "master_scores_2024.parquet", index=False)
    print(f"[{datetime.now()}] Saved master_scores_2024.parquet — {len(master)} rows")

    # Print summary
    print(f"\n{'Rank':<5} {'Ticker':<8} {'Fund':>6} {'Text':>6} {'Final':>6} {'Delta':>6}")
    print("-" * 40)
    for _, r in master.iterrows():
        print(f"{r['final_rank']:<5} {r['ticker']:<8} "
              f"{r['fundamental_score']:6.1f} {r['textual_index']:6.1f} "
              f"{r['final_score']:6.1f} {r['rank_delta']:>+5d}")

    print(f"\n[{datetime.now()}] === Master Score Computation Complete ===")
    return master


def run():
    """Entry point — build textual index then master scores."""
    build_textual_index()
    return build_master_scores()


if __name__ == "__main__":
    run()
