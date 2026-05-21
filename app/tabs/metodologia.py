"""Aba: Metodologia."""
from __future__ import annotations

import html

import plotly.express as px
import streamlit as st

from app.components.data_loader import (
    get_data_freshness,
    load_feature_importance,
)
from app.components.html_table import render_brand_table
from app.components.methodology_content import (
    LIMITATIONS,
    PROFILE_WEIGHTS,
    SENSITIVITY_BY_DRIVER,
    SENSITIVITY_FLIP_RATE,
    SENSITIVITY_MEAN_GAP_DELTA,
    SENSITIVITY_MEAN_SCORE_DELTA,
    SENSITIVITY_NARRATIVE,
    SENSITIVITY_TOTAL_PERTURBATIONS,
    TENSION_THRESHOLDS,
    WALK_FORWARD,
    WALK_FORWARD_GINI_MEAN,
    WALK_FORWARD_GINI_STD,
    WALK_FORWARD_KS_MEAN,
    WALK_FORWARD_KS_STD,
    WALK_FORWARD_MEAN,
    WALK_FORWARD_STD,
)
from app.components.plot_theme import BRAND_BORDO, apply_brand_layout


def _metric_block(value: str, label: str) -> str:
    return (
        f'<div class="metric-block" style="margin-bottom:0.6rem;">'
        f'<div class="metric-value" style="font-size:1.8rem;">{html.escape(value)}</div>'
        f'<div class="metric-label">{html.escape(label)}</div>'
        f'</div>'
    )


def _render_pipeline_overview() -> None:
    st.subheader("Pipeline de Inferência")
    st.markdown(
        "Toda tese passa por quatro estágios determinísticos. Nenhum LLM é "
        "chamado em produção — toda a inferência roda localmente. As decisões "
        "finais são auditáveis linha a linha no código-fonte."
    )
    st.markdown(
        "1. **Coleta de evidência:** seis tools agentic (KPIs, preços, macro, "
        "sentimento, valuation, score composto) consultam parquets pré-processados. "
        "Sem chamadas externas em runtime.\n"
        "2. **Detecção de tensões:** regras determinísticas comparam a direção da "
        "tese (bullish/bearish) com slopes e thresholds dos dados, por driver "
        "declarado. Sem ML supervisionado nesta etapa.\n"
        "3. **Amplificação por convicção:** a severidade de cada tensão é "
        "ajustada pela convicção declarada (1-10) no driver correspondente. "
        "Convicção 9-10 sobe a severidade um nível; 1-3 reduz um nível. "
        "Convicções intermediárias (4-8) mantêm a severidade neutra.\n"
        "4. **Score de consistência:** começa em 100, subtrai por tensão "
        "(HIGH -25, MEDIUM -10, LOW -5). Veredito: ≥70 sustentável, 40-69 com "
        "ressalvas, <40 fragilizada. Em paralelo, Gap de Convicção (0-100) "
        "mede o quanto a convicção declarada nos drivers contradiz a evidência "
        "coletada."
    )


def _supervised_verdict(gini_mean: float) -> str:
    if gini_mean < 0.20:
        return "Sinal fraco"
    if gini_mean < 0.40:
        return "Sinal moderado"
    return "Sinal forte"


def _metric_block_with_caption(value: str, label: str, caption: str) -> str:
    return (
        f'<div class="metric-block" style="margin-bottom:0.6rem;">'
        f'<div class="metric-value" style="font-size:1.8rem;">{html.escape(value)}</div>'
        f'<div class="metric-label">{html.escape(label)}</div>'
        f'<div class="metric-caption">{html.escape(caption)}</div>'
        f'</div>'
    )


def _render_supervised_performance() -> None:
    st.subheader("Performance do Modelo Supervisionado")
    st.markdown(
        "O auditor não depende deste modelo para o veredito principal. Ele é "
        "exposto aqui por completude — usuários técnicos avaliam por si próprios "
        "a qualidade da etapa de probabilidade de outperformance, que entra no "
        "score composto com peso de 10-35% dependendo do perfil de investidor. "
        "Modelo documentado: GradientBoosting."
    )
    st.dataframe(
        WALK_FORWARD,
        column_config={
            "Fold": st.column_config.NumberColumn("Fold", format="%d", width="small"),
            "ROC AUC": st.column_config.NumberColumn("ROC AUC", format="%.3f"),
            "KS": st.column_config.NumberColumn("KS", format="%.3f"),
            "Gini": st.column_config.NumberColumn("Gini", format="%.3f"),
        },
        hide_index=True,
        use_container_width=True,
    )

    cols = st.columns(4)
    with cols[0]:
        st.markdown(
            _metric_block_with_caption(
                f"{WALK_FORWARD_MEAN:.3f}",
                "ROC AUC Médio",
                f"± {WALK_FORWARD_STD:.3f}",
            ),
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown(
            _metric_block_with_caption(
                f"{WALK_FORWARD_KS_MEAN:.3f}",
                "KS Médio",
                f"± {WALK_FORWARD_KS_STD:.3f}",
            ),
            unsafe_allow_html=True,
        )
    with cols[2]:
        st.markdown(
            _metric_block_with_caption(
                f"{WALK_FORWARD_GINI_MEAN:.3f}",
                "Gini Médio",
                f"± {WALK_FORWARD_GINI_STD:.3f}",
            ),
            unsafe_allow_html=True,
        )
    with cols[3]:
        st.markdown(
            _metric_block(
                _supervised_verdict(WALK_FORWARD_GINI_MEAN),
                "Veredito interno",
            ),
            unsafe_allow_html=True,
        )

    st.markdown(
        "- **ROC AUC:** probabilidade do modelo ordenar corretamente um par "
        "outperform/underperform sorteado ao acaso.\n"
        "- **KS:** separação máxima entre a distribuição de scores das classes "
        "(prática padrão em credit scoring).\n"
        "- **Gini:** derivado linear do AUC (2×AUC − 1); convenção do mercado "
        "financeiro para risco de crédito."
    )

    st.warning(
        "O fold 3 (treino 2020-2022, teste 2023) caiu para ROC AUC 0.417 com "
        "Gini negativo — pior que aleatório. Esse comportamento, esperado em "
        "janelas curtas com mudança de regime macro, é a razão pela qual o "
        "auditor delega a decisão final a regras determinísticas, não ao modelo."
    )


def _render_feature_importance() -> None:
    st.subheader("Features Mais Relevantes")
    df = load_feature_importance().copy()
    df = df.nlargest(10, "importance").sort_values("importance", ascending=True)

    st.markdown(
        "O feature dominante é macro/sistêmico: beta vs. Ibovespa. Logo abaixo "
        "aparecem crescimento histórico de lucro líquido e USD/BRL — confirmando "
        "um padrão conhecido em mercados emergentes: em janelas de 1-2 anos, o "
        "risco sistêmico e a trajetória recente de resultados explicam mais "
        "retorno relativo do que múltiplos individuais."
    )

    fig = px.bar(
        df,
        x="importance",
        y="feature",
        orientation="h",
        text=df["importance"].map(lambda v: f"{v:.2f}"),
        color_discrete_sequence=[BRAND_BORDO],
    )
    fig.update_traces(
        textposition="outside",
        textfont=dict(color="#1C1C1C", size=11),
        cliponaxis=False,
        hovertemplate="%{y}: %{x:.3f}<extra></extra>",
    )
    fig.update_xaxes(range=[0, df["importance"].max() * 1.15], title_text="")
    fig.update_yaxes(title_text="")
    fig.update_layout(legend_title_text="", showlegend=False)
    apply_brand_layout(
        fig,
        title="Importância de Features no Modelo Supervisionado",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_profile_weights() -> None:
    with st.expander("Como os pesos do score mudam por perfil de investidor"):
        st.markdown(
            "O score composto é uma combinação ponderada de quatro componentes. "
            "O peso de cada componente muda conforme o perfil declarado pelo "
            "investidor — conservador prioriza valuation e fundamentos; agressivo "
            "prioriza probabilidade de outperformance."
        )
        render_brand_table(PROFILE_WEIGHTS, emphasis_col="Componente")
        st.markdown(
            "O Auditor de Tese atual usa o perfil **Base**. Versões futuras "
            "permitirão override pelo usuário."
        )


def _render_tension_thresholds() -> None:
    with st.expander("Regras determinísticas de detecção de tensões"):
        st.markdown(
            "Para cada driver declarado pelo usuário, o auditor compara a direção "
            "da tese com a evidência observada. As regras abaixo são o código-fonte "
            "traduzido para PT-BR, não uma simplificação."
        )
        render_brand_table(TENSION_THRESHOLDS, emphasis_col="Driver")
        st.caption(
            "Para teses bearish, todas as regras são invertidas (e.g. HIGH em "
            "fundamentos vira ROE +2pp YoY E Margem +1pp YoY)."
        )


def _render_sensitivity() -> None:
    st.subheader("Análise de Sensibilidade")
    st.markdown(SENSITIVITY_NARRATIVE)

    cols = st.columns(3)
    with cols[0]:
        st.markdown(
            _metric_block_with_caption(
                f"{SENSITIVITY_FLIP_RATE:.1%}",
                "Taxa de Flip de Veredito",
                f"{SENSITIVITY_TOTAL_PERTURBATIONS} perturbações",
            ),
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown(
            _metric_block_with_caption(
                f"{SENSITIVITY_MEAN_SCORE_DELTA:.2f} pts",
                "|Δ Score| Médio",
                "Impacto da convicção no score",
            ),
            unsafe_allow_html=True,
        )
    with cols[2]:
        st.markdown(
            _metric_block_with_caption(
                f"{SENSITIVITY_MEAN_GAP_DELTA:.2f} pts",
                "|Δ Gap| Médio",
                "Impacto da convicção no gap",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("**Sensibilidade por driver**")
    st.dataframe(
        SENSITIVITY_BY_DRIVER,
        column_config={
            "Flip rate": st.column_config.NumberColumn("Flip rate", format="%.1%"),
            "|Δ Score| médio": st.column_config.NumberColumn(
                "|Δ Score| médio", format="%.2f"
            ),
            "|Δ Gap| médio": st.column_config.NumberColumn(
                "|Δ Gap| médio", format="%.2f"
            ),
            "N": st.column_config.NumberColumn("N", format="%d", width="small"),
        },
        hide_index=True,
        use_container_width=True,
    )
    st.caption(
        "Drivers com flip rate alto teriam maior peso causal no veredito. "
        "Com flip rate de 0% em todas as categorias, a convicção declarada "
        "modula o Gap mas não consegue forçar o veredito quando contradiz a "
        "evidência — propriedade desejada para resistir a auto-inflação."
    )


def _render_limitations() -> None:
    st.subheader("Limitações")
    st.markdown(
        "Cada uma das limitações abaixo afeta materialmente o resultado final. "
        "Nenhuma é mitigada completamente. O usuário é a última camada de filtro."
    )
    render_brand_table(LIMITATIONS, emphasis_col="Limitação")


def _render_reproducibility() -> None:
    st.subheader("Reprodutibilidade")
    st.markdown(
        "Todo o pipeline é determinístico e versionado. Para reproduzir os "
        "resultados visíveis nesta interface:"
    )
    st.markdown(
        "- Repositório: `https://github.com/jpafreire1204/equity_research`\n"
        "- Branch atual: `feat/thesis-auditor`\n"
        "- Ambiente: Python 3.12 + dependências em `requirements.txt`\n"
        "- Pipeline completo: `python -m src.ingest.market` → "
        "`python -m src.ingest.cvm` → `python -m src.ingest.macro` → ... → "
        "`python -m src.valuation.valuation_score`\n"
        "- Auditor CLI: `python -m src.auditor --ticker ITUB4 "
        "--direction bullish --drivers fundamentals_quality momentum_positive "
        "--convictions fundamentals_quality=9 momentum_positive=7`"
    )


def render() -> None:
    st.markdown(
        '<h3 style="margin-top:1rem; color:#6B6B6B; font-weight:500;">'
        "Como o Auditor funciona, onde acerta e onde falha</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "Este produto não recomenda ações. Audita teses de investimento contra "
        "dados estruturados. Esta seção documenta exatamente como cada componente "
        "decide, com qual margem de erro, e o que o sistema explicitamente não "
        "pode fazer. A transparência é o produto."
    )

    _render_pipeline_overview()
    st.markdown("")
    _render_supervised_performance()
    st.markdown("")
    _render_feature_importance()
    st.markdown("")
    _render_profile_weights()
    _render_tension_thresholds()
    st.markdown("")
    _render_sensitivity()
    st.markdown("")
    _render_limitations()
    st.markdown("")
    _render_reproducibility()
    st.markdown("")
    st.caption(
        f"Dados atualizados em {get_data_freshness()}. "
        "Inferência 100% determinística — sem embeddings, sem LLM em runtime."
    )
