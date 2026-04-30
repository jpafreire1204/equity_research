"""Consistency scorer — semantic similarity + deterministic point system."""
from __future__ import annotations

from src.agent.tools import get_full_score
from src.auditor.contracts import Tension, ThesisInput

_MODEL = None
_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def _model():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer(_MODEL_NAME)
    return _MODEL


def _fmt(v, suffix: str = "") -> str:
    if v is None:
        return "n/d"
    try:
        if suffix == "%":
            return f"{v * 100:.1f}%" if -10 < v < 10 else f"{v:.1f}%"
        return f"{v:.1f}{suffix}"
    except Exception:
        return "n/d"


def _build_narrative(ticker: str) -> str:
    try:
        s = get_full_score(ticker)
    except Exception as e:
        return f"Empresa {ticker}: dados indisponíveis ({e})."
    fund = s.get("fundamental_score")
    txt = s.get("textual_index")
    val = s.get("valuation_score")
    score = s.get("ultimate_score")
    rec = s.get("recommendation", "n/d")
    return (
        f"Empresa {ticker}: score fundamental {_fmt(fund)}/100, "
        f"índice textual {_fmt(txt)}/100, score valuation {_fmt(val)}/100, "
        f"recomendação {rec}, score final {_fmt(score)}/100."
    )


def semantic_similarity(thesis_text: str, ticker: str) -> float:
    """Cosine similarity between user thesis and a data-driven narrative for this ticker."""
    narrative = _build_narrative(ticker)
    model = _model()
    emb = model.encode([thesis_text, narrative], convert_to_numpy=True, normalize_embeddings=True)
    sim = float((emb[0] * emb[1]).sum())
    return max(0.0, min(1.0, sim))


_TENSION_COST = {"high": 25, "medium": 10, "low": 5}


def compute_score(
    thesis: ThesisInput, tensions: list[Tension], similarity: float
) -> tuple[float, str]:
    """Return (score 0-100, verdict)."""
    score = 100.0
    for t in tensions:
        score -= _TENSION_COST.get(t.severity, 0)
    score = score * (0.5 + 0.5 * similarity)
    score = max(0.0, min(100.0, score))
    if score >= 70:
        verdict = "sustentavel"
    elif score >= 40:
        verdict = "sustentavel_com_ressalvas"
    else:
        verdict = "fragilizada"
    return round(score, 1), verdict
