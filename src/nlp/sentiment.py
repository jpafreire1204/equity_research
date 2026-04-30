"""
Sentiment analysis module (Aula 4).

Two complementary approaches:

  A) Transformer-based — "lxyuan/distilbert-base-multilingual-cased-sentiments-student"
     Produces positive / negative / neutral scores per text, aggregated per ticker
     with exponential recency weighting (half-life 90 days).

  B) Keyword risk flags — a hand-crafted Portuguese dictionary of positive/negative
     financial terms.  Produces a keyword_score normalised to [-100, +100] and
     extracts the top-5 positive and top-5 negative keywords per ticker.

Output: data/processed/sentiment_scores.parquet
"""

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# ── Sector map ─────────────────────────────────────────────────────────────
SECTOR_MAP = {
    "ITUB4": "Bancos", "BBDC4": "Bancos", "BBAS3": "Bancos",
    "SANB11": "Bancos", "ABCB4": "Bancos",
    "EGIE3": "Energia Elétrica", "EQTL3": "Energia Elétrica",
    "CPFE3": "Energia Elétrica", "TAEE11": "Energia Elétrica",
    "CMIG4": "Energia Elétrica",
}

ALL_TICKERS = list(SECTOR_MAP.keys())

# ── Risk / opportunity keyword dictionary ──────────────────────────────────
RISK_KEYWORDS: dict[str, int] = {
    "alavancagem": -2,
    "endividamento": -1,
    "litígio": -2,
    "fraude": -3,
    "investigação": -2,
    "multa": -1,
    "guidance": +1,
    "crescimento": +1,
    "expansão": +1,
    "dividendo": +1,
    "lucro": +1,
    "recorde": +2,
    "inadimplência": -2,
    "prejuízo": -2,
    "rebaixamento": -3,
    "upgrade": +2,
    "aquisição": +1,
    "desinvestimento": -1,
}

REFERENCE_DATE = pd.Timestamp.today().normalize()
HALF_LIFE_DAYS = 90


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _load_texts(ticker: str) -> list[dict]:
    """Load cached texts for a ticker."""
    path = RAW_DIR / f"texts_{ticker}.json"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _parse_date(date_str: str) -> pd.Timestamp | None:
    """Best-effort date parsing."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return pd.Timestamp(datetime.strptime(date_str, fmt))
        except ValueError:
            continue
    try:
        return pd.Timestamp(date_str)
    except Exception:
        return None


def _recency_weight(date_str: str) -> float:
    """Exponential decay weight based on days from REFERENCE_DATE."""
    dt = _parse_date(date_str)
    if dt is None:
        return 0.5  # default mid-weight for undated texts
    days = max(0, (REFERENCE_DATE - dt).days)
    return np.exp(-np.log(2) * days / HALF_LIFE_DAYS)


# ═══════════════════════════════════════════════════════════════════════════
# Approach A — Transformer sentiment
# ═══════════════════════════════════════════════════════════════════════════

def _get_sentiment_pipeline():
    """Lazily load the transformer sentiment pipeline."""
    from transformers import pipeline as hf_pipeline

    print(f"[{datetime.now()}] Loading transformer sentiment model ...")
    pipe = hf_pipeline(
        "text-classification",
        model="lxyuan/distilbert-base-multilingual-cased-sentiments-student",
        top_k=None,          # return all labels (positive/negative/neutral)
        truncation=True,
        max_length=512,
    )
    print(f"[{datetime.now()}] Model loaded.")
    return pipe


def _run_transformer(texts: list[dict], pipe) -> dict:
    """
    Run transformer sentiment on a list of text dicts.

    Returns {positive_score, negative_score, neutral_score} as
    recency-weighted averages.
    """
    if not texts:
        return {"positive_score": np.nan, "negative_score": np.nan, "neutral_score": np.nan}

    pos_scores, neg_scores, neu_scores, weights = [], [], [], []

    for doc in texts:
        text = doc.get("text", "")
        if not text or len(text.strip()) < 10:
            continue

        try:
            result = pipe(text[:512])  # truncate for safety
            scores_list = result[0] if result else []
            score_map = {s["label"]: s["score"] for s in scores_list}
        except Exception:
            continue

        w = _recency_weight(doc.get("date", ""))
        pos_scores.append(score_map.get("positive", 0))
        neg_scores.append(score_map.get("negative", 0))
        neu_scores.append(score_map.get("neutral", 0))
        weights.append(w)

    if not weights:
        return {"positive_score": np.nan, "negative_score": np.nan, "neutral_score": np.nan}

    w_arr = np.array(weights)
    return {
        "positive_score": float(np.average(pos_scores, weights=w_arr)),
        "negative_score": float(np.average(neg_scores, weights=w_arr)),
        "neutral_score": float(np.average(neu_scores, weights=w_arr)),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Approach B — Keyword risk flags
# ═══════════════════════════════════════════════════════════════════════════

def _run_keywords(texts: list[dict]) -> dict:
    """
    Count risk/opportunity keywords across all texts for a ticker.

    Returns {keyword_score (-100..+100), top_positive_keywords, top_negative_keywords}.
    """
    counts: dict[str, int] = {kw: 0 for kw in RISK_KEYWORDS}

    for doc in texts:
        text_lower = doc.get("text", "").lower()
        for kw in RISK_KEYWORDS:
            # Match keyword as whole word or substring (Portuguese morphology)
            n = text_lower.count(kw.lower())
            counts[kw] += n

    # Weighted score
    raw_score = sum(counts[kw] * RISK_KEYWORDS[kw] for kw in RISK_KEYWORDS)
    max_possible = sum(abs(v) for v in RISK_KEYWORDS.values()) * max(1, len(texts))
    if max_possible > 0:
        keyword_score = (raw_score / max_possible) * 100
        keyword_score = max(-100.0, min(100.0, keyword_score))
    else:
        keyword_score = 0.0

    # Top keywords
    positive_kws = sorted(
        [(kw, counts[kw]) for kw in RISK_KEYWORDS if RISK_KEYWORDS[kw] > 0 and counts[kw] > 0],
        key=lambda x: x[1] * RISK_KEYWORDS[x[0]], reverse=True,
    )
    negative_kws = sorted(
        [(kw, counts[kw]) for kw in RISK_KEYWORDS if RISK_KEYWORDS[kw] < 0 and counts[kw] > 0],
        key=lambda x: x[1] * abs(RISK_KEYWORDS[x[0]]), reverse=True,
    )

    return {
        "keyword_score": keyword_score,
        "top_positive_keywords": ", ".join(f"{kw}({c})" for kw, c in positive_kws[:5]),
        "top_negative_keywords": ", ".join(f"{kw}({c})" for kw, c in negative_kws[:5]),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Main pipeline
# ═══════════════════════════════════════════════════════════════════════════

def build_sentiment_scores() -> pd.DataFrame:
    """
    Run both sentiment approaches on all tickers.

    Saves to data/processed/sentiment_scores.parquet.
    Returns the scores DataFrame.
    """
    print(f"[{datetime.now()}] === Sentiment Analysis Start ===")

    pipe = _get_sentiment_pipeline()
    rows = []

    for ticker in ALL_TICKERS:
        texts = _load_texts(ticker)
        text_count = len(texts)
        print(f"[{datetime.now()}] {ticker}: {text_count} texts")

        if text_count < 5:
            print(f"[{datetime.now()}] WARNING: {ticker} has < 5 texts — scores may be unreliable")

        # Transformer scores
        transformer = _run_transformer(texts, pipe)

        # Keyword scores
        keywords = _run_keywords(texts)

        # Composite: weighted blend (used by textual_index later)
        pos = transformer["positive_score"]
        kw = keywords["keyword_score"]
        if not np.isnan(pos):
            # Normalise keyword_score from [-100,100] to [0,1] for blending
            kw_norm = (kw + 100) / 200
            sentiment_composite = 0.6 * pos + 0.4 * kw_norm
        else:
            sentiment_composite = np.nan

        rows.append({
            "ticker": ticker,
            "sector": SECTOR_MAP[ticker],
            "positive_score": transformer["positive_score"],
            "negative_score": transformer["negative_score"],
            "neutral_score": transformer["neutral_score"],
            "keyword_score": keywords["keyword_score"],
            "sentiment_composite": sentiment_composite,
            "top_positive_keywords": keywords["top_positive_keywords"],
            "top_negative_keywords": keywords["top_negative_keywords"],
            "text_count": text_count,
        })

    result = pd.DataFrame(rows)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    result.to_parquet(PROCESSED_DIR / "sentiment_scores.parquet", index=False)
    print(f"[{datetime.now()}] Saved sentiment_scores.parquet — {len(result)} rows")
    print(f"[{datetime.now()}] === Sentiment Analysis Complete ===")
    return result


def run():
    """Entry point."""
    return build_sentiment_scores()


if __name__ == "__main__":
    run()
