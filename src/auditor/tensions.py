"""Tension detector — deterministic rules comparing thesis vs. evidence."""
from __future__ import annotations

from src.auditor.contracts import DriverKey, Tension, ThesisInput


def _amplify_severity(base_severity: str, conviction: int | None) -> str:
    """Conviction 9-10 bumps severity up one level. Conviction 1-3 dampens it down."""
    if conviction is None:
        return base_severity
    order = ["low", "medium", "high"]
    idx = order.index(base_severity)
    if conviction >= 9 and idx < 2:
        idx += 1
    elif conviction <= 3 and idx > 0:
        idx -= 1
    return order[idx]


def _pct(v) -> str:
    return f"{v * 100:+.1f}%" if isinstance(v, (int, float)) else "n/d"


def _pct_abs(v) -> str:
    return f"{v * 100:.1f}%" if isinstance(v, (int, float)) else "n/d"


def _err_tension(driver: DriverKey, ev: dict) -> Tension:
    return Tension(
        driver=driver,
        severity="medium",
        finding="Evidência indisponível para este driver.",
        evidence=ev,
    )


def _t_fundamentals(direction: str, ev: dict) -> Tension | None:
    roe24, roe23 = ev.get("roe_2024"), ev.get("roe_2023")
    nm24, nm23 = ev.get("net_margin_2024"), ev.get("net_margin_2023")
    if any(v is None for v in (roe24, roe23, nm24, nm23)):
        return None
    roe_delta = roe24 - roe23
    nm_delta = nm24 - nm23
    if direction == "bullish":
        roe_bad = roe_delta < -0.02
        nm_bad = nm_delta < -0.01
        if roe_bad and nm_bad:
            return Tension(
                driver="fundamentals_quality",
                severity="high",
                finding=f"ROE caiu de {_pct_abs(roe23)} para {_pct_abs(roe24)} e margem de {_pct_abs(nm23)} para {_pct_abs(nm24)} YoY; tese de qualidade fundamental enfraquecida.",
                evidence=ev,
            )
        if roe_bad or nm_bad:
            return Tension(
                driver="fundamentals_quality",
                severity="medium",
                finding=f"ROE {_pct_abs(roe23)} → {_pct_abs(roe24)}, margem {_pct_abs(nm23)} → {_pct_abs(nm24)}; deterioração parcial nos fundamentos.",
                evidence=ev,
            )
        return None
    # bearish
    roe_bad = roe_delta > 0.02
    nm_bad = nm_delta > 0.01
    if roe_bad and nm_bad:
        return Tension(
            driver="fundamentals_quality",
            severity="high",
            finding=f"ROE subiu de {_pct_abs(roe23)} para {_pct_abs(roe24)} e margem de {_pct_abs(nm23)} para {_pct_abs(nm24)} YoY; fundamentos contradizem a tese bearish.",
            evidence=ev,
        )
    if roe_bad or nm_bad:
        return Tension(
            driver="fundamentals_quality",
            severity="medium",
            finding=f"ROE {_pct_abs(roe23)} → {_pct_abs(roe24)}, margem {_pct_abs(nm23)} → {_pct_abs(nm24)}; melhora parcial nos fundamentos contradiz tese bearish.",
            evidence=ev,
        )
    return None


def _t_valuation(direction: str, ev: dict) -> Tension | None:
    dvs = ev.get("discount_vs_sector")
    if dvs is None:
        return None
    if direction == "bullish":
        if dvs < -0.10:
            return Tension(
                driver="valuation_attractive",
                severity="high",
                finding=f"Múltiplo P/L {_pct(-dvs)} acima da mediana setorial; tese de valuation atrativo contradita.",
                evidence=ev,
            )
        if dvs < 0:
            return Tension(
                driver="valuation_attractive",
                severity="medium",
                finding=f"Múltiplo P/L {_pct(-dvs)} acima da mediana setorial; valuation pouco descontado.",
                evidence=ev,
            )
        return None
    # bearish (claim: overvalued)
    if dvs > 0.10:
        return Tension(
            driver="valuation_attractive",
            severity="high",
            finding=f"Ação negocia {_pct(dvs)} abaixo da mediana setorial; tese bearish de sobrevaluation contradita.",
            evidence=ev,
        )
    if dvs > 0:
        return Tension(
            driver="valuation_attractive",
            severity="medium",
            finding=f"Ação negocia {_pct(dvs)} abaixo da mediana setorial; valuation não suporta tese bearish.",
            evidence=ev,
        )
    return None


def _t_momentum(direction: str, ev: dict) -> Tension | None:
    m6 = ev.get("momentum_6m")
    m12 = ev.get("momentum_12m")
    if m6 is None and m12 is None:
        return None
    if direction == "bullish":
        sixm_bad = m6 is not None and m6 < -0.10
        twelve_bad = m12 is not None and m12 < 0
        if sixm_bad and twelve_bad:
            return Tension(
                driver="momentum_positive",
                severity="high",
                finding=f"Momentum 6m em {_pct(m6)} e 12m em {_pct(m12)}; tese de momentum positivo não suportada pelos dados.",
                evidence=ev,
            )
        if sixm_bad or twelve_bad:
            return Tension(
                driver="momentum_positive",
                severity="medium",
                finding=f"Momentum 6m {_pct(m6)} / 12m {_pct(m12)}; sinal de força parcial.",
                evidence=ev,
            )
        return None
    # bearish (claim: weak momentum)
    sixm_bad = m6 is not None and m6 > 0.10
    twelve_bad = m12 is not None and m12 > 0
    if sixm_bad and twelve_bad:
        return Tension(
            driver="momentum_positive",
            severity="high",
            finding=f"Momentum 6m em {_pct(m6)} e 12m em {_pct(m12)}; tese bearish contradita pela força de preço.",
            evidence=ev,
        )
    if sixm_bad or twelve_bad:
        return Tension(
            driver="momentum_positive",
            severity="medium",
            finding=f"Momentum 6m {_pct(m6)} / 12m {_pct(m12)}; tendência parcialmente positiva contradiz tese bearish.",
            evidence=ev,
        )
    return None


def _t_sentiment(direction: str, ev: dict) -> Tension | None:
    ti = ev.get("textual_index")
    if ti is None:
        return None
    neg = ev.get("top_negative_keywords") or []
    pos = ev.get("top_positive_keywords") or []
    if direction == "bullish":
        if ti < 30:
            return Tension(
                driver="sentiment_supportive",
                severity="high",
                finding=f"Índice textual em {ti:.0f}/100 com keywords negativas dominantes ({', '.join(neg[:3]) or 'n/d'}); sentimento não suporta tese.",
                evidence=ev,
            )
        if ti < 50:
            return Tension(
                driver="sentiment_supportive",
                severity="medium",
                finding=f"Índice textual em {ti:.0f}/100; sentimento misto, suporte fraco à tese bullish.",
                evidence=ev,
            )
        return None
    # bearish (claim: negative sentiment)
    if ti > 70:
        return Tension(
            driver="sentiment_supportive",
            severity="high",
            finding=f"Índice textual em {ti:.0f}/100 com keywords positivas dominantes ({', '.join(pos[:3]) or 'n/d'}); sentimento contradita tese bearish.",
            evidence=ev,
        )
    if ti > 50:
        return Tension(
            driver="sentiment_supportive",
            severity="medium",
            finding=f"Índice textual em {ti:.0f}/100; sentimento positivo enfraquece tese bearish.",
            evidence=ev,
        )
    return None


def _t_macro(direction: str, ev: dict) -> Tension | None:
    bear = ev.get("bear_upside")
    base = ev.get("base_upside")
    bull = ev.get("bull_upside")
    if bear is None and base is None:
        return None
    if direction == "bullish":
        if bear is not None and bear < -0.05:
            return Tension(
                driver="macro_tailwind",
                severity="high",
                finding=f"Cenário Bear implica downside de {_pct(bear)}; tese de tailwind macro frágil.",
                evidence=ev,
            )
        if base is not None and base < 0.01:
            return Tension(
                driver="macro_tailwind",
                severity="medium",
                finding=f"Cenário Base com upside de apenas {_pct(base)}; tailwind macro limitado.",
                evidence=ev,
            )
        return None
    # bearish (claim: macro headwind)
    if bull is not None and bull > 0.05:
        return Tension(
            driver="macro_tailwind",
            severity="high",
            finding=f"Cenário Bull implica upside de {_pct(bull)}; tese bearish macro contradita pela assimetria positiva.",
            evidence=ev,
        )
    if base is not None and base > 0.01:
        return Tension(
            driver="macro_tailwind",
            severity="medium",
            finding=f"Cenário Base com upside de {_pct(base)}; tese bearish enfraquecida.",
            evidence=ev,
        )
    return None


_RULES = {
    "fundamentals_quality": _t_fundamentals,
    "valuation_attractive": _t_valuation,
    "momentum_positive": _t_momentum,
    "sentiment_supportive": _t_sentiment,
    "macro_tailwind": _t_macro,
}


def detect_tensions(thesis: ThesisInput, evidence: dict) -> list[Tension]:
    """Compare user claims against evidence; return tensions where data contradicts thesis.

    Each tension's severity is amplified or dampened by the declared conviction
    for that driver: 9-10 bumps up one level, 1-3 dampens down one level.
    """
    out: list[Tension] = []
    for driver in thesis.drivers:
        ev = evidence.get(driver, {})
        if "error" in ev:
            out.append(_err_tension(driver, ev))
            continue
        rule = _RULES.get(driver)
        if rule is None:
            continue
        t = rule(thesis.direction, ev)
        if t is None:
            continue
        conv = thesis.convictions.get(driver)
        t.severity = _amplify_severity(t.severity, conv)
        if conv is not None and conv >= 8:
            t.finding += f" Convicção declarada {conv}/10 amplifica o gap."
        elif conv is not None and conv <= 3:
            t.finding += f" Convicção declarada {conv}/10 ja era moderada."
        out.append(t)
    return out
