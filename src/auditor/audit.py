"""Orchestrator — single entry point for thesis audit."""
from __future__ import annotations

import datetime as dt

from src.auditor.contracts import AuditResult, DriverKey, ThesisInput
from src.auditor.evidence import collect_evidence
from src.auditor.scorer import compute_score, semantic_similarity
from src.auditor.tensions import detect_tensions

_SUPPORT_TEMPLATES: dict[DriverKey, str] = {
    "fundamentals_quality": "Fundamentos consistentes: ROE {roe} e margem líquida {nm} em 2024.",
    "valuation_attractive": "Valuation alinhado: P/L {pl}x e desconto vs. setor de {dvs}.",
    "momentum_positive": "Momentum a favor: 12m em {m12}, 6m em {m6}.",
    "sentiment_supportive": "Sentimento favorável: índice textual em {ti}/100.",
    "macro_tailwind": "Cenário macro favorável: upside Base de {base} e Bull de {bull}.",
}


def _pct(v) -> str:
    return f"{v * 100:+.1f}%" if isinstance(v, (int, float)) else "n/d"


def _pct_abs(v) -> str:
    return f"{v * 100:.1f}%" if isinstance(v, (int, float)) else "n/d"


def _support_sentence(driver: DriverKey, ev: dict) -> str | None:
    if "error" in ev:
        return None
    if driver == "fundamentals_quality":
        return _SUPPORT_TEMPLATES[driver].format(
            roe=_pct_abs(ev.get("roe_2024")),
            nm=_pct_abs(ev.get("net_margin_2024")),
        )
    if driver == "valuation_attractive":
        pl = ev.get("pe_ratio")
        dvs = ev.get("discount_vs_sector")
        return _SUPPORT_TEMPLATES[driver].format(
            pl=f"{pl:.1f}" if isinstance(pl, (int, float)) else "n/d",
            dvs=_pct(dvs),
        )
    if driver == "momentum_positive":
        return _SUPPORT_TEMPLATES[driver].format(
            m12=_pct(ev.get("momentum_12m")),
            m6=_pct(ev.get("momentum_6m")),
        )
    if driver == "sentiment_supportive":
        ti = ev.get("textual_index")
        return _SUPPORT_TEMPLATES[driver].format(
            ti=f"{ti:.0f}" if isinstance(ti, (int, float)) else "n/d",
        )
    if driver == "macro_tailwind":
        return _SUPPORT_TEMPLATES[driver].format(
            base=_pct(ev.get("base_upside")),
            bull=_pct(ev.get("bull_upside")),
        )
    return None


def audit_thesis(thesis: ThesisInput) -> AuditResult:
    """Full pipeline: collect evidence → detect tensions → score → return result."""
    evidence = collect_evidence(thesis.ticker, thesis.drivers)
    tensions = detect_tensions(thesis, evidence)
    similarity = semantic_similarity(thesis.rationale, thesis.ticker)
    score, verdict = compute_score(thesis, tensions, similarity)

    drivers_with_tension = {t.driver for t in tensions}
    supporting: list[str] = []
    for driver in thesis.drivers:
        if driver in drivers_with_tension:
            continue
        sentence = _support_sentence(driver, evidence.get(driver, {}))
        if sentence:
            supporting.append(sentence)
        if len(supporting) >= 3:
            break

    return AuditResult(
        ticker=thesis.ticker,
        consistency_score=score,
        verdict=verdict,
        semantic_similarity=round(similarity, 4),
        tensions=tensions,
        supporting_evidence=supporting,
        auditado_em=dt.datetime.now().isoformat(timespec="seconds"),
    )
