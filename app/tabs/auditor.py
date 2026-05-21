"""Aba: Auditar Tese."""
from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

import streamlit as st

from app.components.labels import DRIVER_LABELS, VERDICT_CSS_CLASS, VERDICT_LABELS
from src.auditor.audit import audit_thesis
from src.auditor.contracts import AuditResult, ThesisInput

ALL_TICKERS = [
    "ITUB4", "BBDC4", "BBAS3", "SANB11", "ABCB4",
    "EGIE3", "EQTL3", "CPFE3", "TAEE11", "CMIG4",
]

DRIVER_OPTIONS = [
    ("fundamentals_quality", "Qualidade de fundamentos"),
    ("valuation_attractive", "Valuation atrativo"),
    ("momentum_positive", "Momentum positivo"),
    ("sentiment_supportive", "Sentimento de mercado favorável"),
    ("macro_tailwind", "Cenário macro favorável"),
]
_LABEL_TO_KEY = {label: key for key, label in DRIVER_OPTIONS}

_DATA_FILE = (
    Path(__file__).resolve().parents[2]
    / "data" / "processed" / "ultimate_scores_2024.parquet"
)


def _data_freshness() -> str:
    try:
        ts = datetime.fromtimestamp(_DATA_FILE.stat().st_mtime)
        return ts.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return "n/d"


def _gap_caption(gap: float) -> str:
    if gap == 0:
        return "Sem dissonância entre convicção e dados"
    if gap < 30:
        return "Dissonância leve"
    if gap < 70:
        return "Dissonância material"
    return "Alta dissonância — revisar tese"


def _render_form() -> ThesisInput | None:
    col_l, col_r = st.columns([1, 1])
    with col_l:
        ticker = st.selectbox(
            "Ticker", ALL_TICKERS, index=0,
            help="Empresa do universo de cobertura.",
        )
    with col_r:
        direction_label = st.radio(
            "Direção da tese",
            ["Bullish (espero alta)", "Bearish (espero queda)"],
            horizontal=True,
        )
    direction = "bullish" if direction_label.startswith("Bullish") else "bearish"

    driver_labels = st.multiselect(
        "Quais drivers sustentam sua tese? Selecione 1-5",
        options=[label for _, label in DRIVER_OPTIONS],
        default=[DRIVER_OPTIONS[0][1], DRIVER_OPTIONS[2][1]],
        max_selections=5,
    )
    selected_drivers = [_LABEL_TO_KEY[label] for label in driver_labels]

    for k in list(st.session_state.keys()):
        if k.startswith("conv_") and k[5:] not in selected_drivers:
            del st.session_state[k]

    convictions: dict[str, int] = {}
    if selected_drivers:
        st.markdown("**Convicção por driver** (1 = especulativo, 10 = altíssima)")
        cols = st.columns(min(len(selected_drivers), 3))
        for i, d in enumerate(selected_drivers):
            with cols[i % len(cols)]:
                convictions[d] = st.slider(
                    DRIVER_LABELS.get(d, d),
                    min_value=1, max_value=10, value=7, step=1,
                    key=f"conv_{d}",
                    help="Quanto você acredita neste driver, independente dos dados.",
                )
    else:
        st.caption("Selecione ao menos 1 driver acima para definir convicções.")

    submitted = st.button("Auditar Tese", type="primary")

    if not submitted:
        return None

    if not selected_drivers:
        st.error("Selecione ao menos 1 driver.")
        return None
    if not all(d in convictions for d in selected_drivers):
        st.error("Defina convicção para todos os drivers selecionados.")
        return None

    return ThesisInput(
        ticker=ticker,
        direction=direction,
        drivers=selected_drivers,
        convictions=convictions,
    )


def _metric_block(value: str, label: str, caption: str | None = None) -> str:
    caption_html = (
        f'<div class="metric-caption">{html.escape(caption)}</div>'
        if caption
        else ""
    )
    return (
        f'<div class="metric-block">'
        f'<div class="metric-value">{html.escape(value)}</div>'
        f'<div class="metric-label">{html.escape(label)}</div>'
        f'{caption_html}'
        f'</div>'
    )


def _render_metrics(result: AuditResult) -> None:
    cols = st.columns(4)
    with cols[0]:
        st.markdown(
            _metric_block(f"{result.consistency_score:.1f}", "Score de Consistência"),
            unsafe_allow_html=True,
        )
    verdict_label = VERDICT_LABELS[result.verdict]
    verdict_class = VERDICT_CSS_CLASS[result.verdict]
    with cols[1]:
        st.markdown(
            f'<div class="metric-block verdict-metric {verdict_class}">'
            f'<div class="verdict-metric-value">{html.escape(verdict_label)}</div>'
            f'<div class="metric-label">Veredito</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with cols[2]:
        st.markdown(
            _metric_block(
                f"{result.conviction_gap_score:.0f}",
                "Gap de Convicção",
                caption=_gap_caption(result.conviction_gap_score),
            ),
            unsafe_allow_html=True,
        )
    with cols[3]:
        st.markdown(
            _metric_block(str(len(result.tensions)), "Nº de Tensões"),
            unsafe_allow_html=True,
        )


def _render_verdict_card(thesis: ThesisInput, result: AuditResult) -> None:
    css_class = VERDICT_CSS_CLASS.get(result.verdict, "verdict-ressalvas")
    direction_pt = "Bullish" if thesis.direction == "bullish" else "Bearish"
    summary = (
        " ".join(result.supporting_evidence[:2])
        if result.supporting_evidence
        else "Sem evidências de apoio robustas; ver tensões abaixo."
    )
    st.markdown(
        f'<div class="verdict-card {css_class}">'
        f'<div style="font-size:0.85rem;color:#6B6B6B;text-transform:uppercase;'
        f'letter-spacing:0.05em;">{html.escape(thesis.ticker)} · {direction_pt}</div>'
        f'<div style="font-size:1.4rem;font-weight:600;margin:0.4rem 0 0.8rem;">'
        f'{html.escape(VERDICT_LABELS.get(result.verdict, result.verdict))}</div>'
        f'<div style="color:#1C1C1C;line-height:1.5;">{html.escape(summary)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_tensions(result: AuditResult) -> None:
    st.markdown("### Tensões Identificadas")
    if not result.tensions:
        st.success("Nenhuma tensão identificada — dados sustentam a tese.")
        return
    st.caption(f"{len(result.tensions)} tensão(ões) detectada(s)")
    for t in result.tensions:
        driver_label = DRIVER_LABELS.get(t.driver, t.driver)
        st.markdown(
            f'<div class="tension-item tension-{t.severity}">'
            f'<div class="tension-driver">{html.escape(driver_label)} · '
            f'{html.escape(t.severity.upper())}</div>'
            f'<div class="tension-finding">{html.escape(t.finding)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_supporting(result: AuditResult) -> None:
    st.markdown("### Evidências de Apoio")
    if not result.supporting_evidence:
        st.caption("Sem evidências de apoio neste momento.")
        return
    for sentence in result.supporting_evidence:
        st.markdown(f"- {sentence}")


def _render_metadata(result: AuditResult) -> None:
    st.caption(
        f"Auditado em {result.auditado_em} · "
        f"Pipeline determinístico (regras + amplificação por convicção) · "
        f"Dados: {_data_freshness()}"
    )


def render() -> None:
    st.markdown(
        '<h3 style="margin-top:1rem; color:#6B6B6B; font-weight:500;">Submeter tese para auditoria</h3>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Submeta uma tese de investimento e veja onde os dados a sustentam ou contradizem."
    )

    thesis = _render_form()

    if thesis is not None:
        with st.spinner("Auditando tese contra dados..."):
            result = audit_thesis(thesis)
        st.session_state["last_audit"] = (thesis, result)

    cached = st.session_state.get("last_audit")
    if cached is None:
        return

    thesis, result = cached
    st.divider()
    _render_metrics(result)
    _render_verdict_card(thesis, result)
    st.markdown("")
    _render_tensions(result)
    st.markdown("")
    _render_supporting(result)
    st.markdown("")
    _render_metadata(result)
