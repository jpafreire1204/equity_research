"""Aba: Explorar Universo."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app.components.data_loader import (
    get_data_freshness,
    load_kpis_wide,
    load_scenarios,
    load_ultimate_scores,
)
from app.components.plot_theme import (
    BRAND_BORDO,
    COLORSCALE_DIVERGING,
    COLORSCALE_SEQUENTIAL,
    apply_brand_layout,
)

COMPANY_NAMES = {
    "ITUB4": "Itaú Unibanco",
    "BBDC4": "Bradesco",
    "BBAS3": "Banco do Brasil",
    "SANB11": "Santander Brasil",
    "ABCB4": "Banco ABC Brasil",
    "EGIE3": "Engie Brasil",
    "EQTL3": "Equatorial Energia",
    "CPFE3": "CPFL Energia",
    "TAEE11": "Taesa",
    "CMIG4": "Cemig",
}

KPI_DISPLAY = {
    "roe": "ROE",
    "net_margin": "Margem Líquida",
    "revenue_cagr": "Crescimento Receita",
    "debt_to_equity": "Alavancagem (D/E)",
    "momentum_12m": "Momentum 12m",
    "volatility_annualized": "Volatilidade",
}

SCENARIO_ORDER = ["bull", "base", "bear"]
SCENARIO_LABEL = {"bull": "Bull", "base": "Base", "bear": "Bear"}

SCORE_COMPONENT_LABELS = {
    "fundamental_score": "Fundamentos",
    "valuation_score": "Valuation",
    "textual_index": "Sentimento Textual",
    "outperform_probability_pct": "Prob. Outperform",
}


def _render_ranking() -> None:
    st.markdown("### Ranking do Universo")
    df = load_ultimate_scores().copy()
    df["empresa"] = df["ticker"].map(COMPANY_NAMES).fillna(df["ticker"])
    df = df.sort_values("ultimate_score", ascending=False).reset_index(drop=True)
    df_view = df[
        ["ultimate_rank", "ticker", "empresa", "sector", "ultimate_score",
         "recommendation", "base_upside_pct"]
    ].rename(
        columns={
            "ultimate_rank": "Rank",
            "ticker": "Ticker",
            "empresa": "Empresa",
            "sector": "Setor",
            "ultimate_score": "Score",
            "recommendation": "Recomendação",
            "base_upside_pct": "Upside Base",
        }
    )
    df_view["Upside Base"] = df_view["Upside Base"] * 100
    st.dataframe(
        df_view,
        column_config={
            "Rank": st.column_config.NumberColumn("Rank", format="%d", width="small"),
            "Score": st.column_config.ProgressColumn(
                "Score", min_value=0, max_value=100, format="%.1f"
            ),
            "Upside Base": st.column_config.NumberColumn(
                "Upside Base", format="%+.1f%%"
            ),
        },
        hide_index=True,
        use_container_width=True,
    )


def _ranked_tickers() -> list[str]:
    df = load_ultimate_scores()
    return (
        df.sort_values("ultimate_score", ascending=False)["ticker"].tolist()
    )


def _render_kpis_heatmap() -> None:
    df = load_kpis_wide()
    df = df[df["year"] == 2024].copy() if "year" in df.columns else df.copy()
    cols = list(KPI_DISPLAY.keys())
    matrix = df.set_index("ticker")[cols]
    matrix = matrix.reindex(_ranked_tickers())

    normed = matrix.copy().astype(float)
    for c in normed.columns:
        cmin, cmax = normed[c].min(), normed[c].max()
        if pd.notna(cmin) and pd.notna(cmax) and cmax != cmin:
            normed[c] = (normed[c] - cmin) / (cmax - cmin)
        else:
            normed[c] = 0.5

    normed = normed.rename(columns=KPI_DISPLAY)
    fig = px.imshow(
        normed,
        color_continuous_scale=COLORSCALE_SEQUENTIAL,
        text_auto=".2f",
        aspect="auto",
        zmin=0,
        zmax=1,
    )
    fig.update_traces(
        textfont=dict(size=11, color="#1C1C1C"),
        hovertemplate="%{y} · %{x}: %{z:.2f}<extra></extra>",
    )
    apply_brand_layout(fig, title="KPIs por Empresa (normalizado 0-1, 2024)", height=460)
    fig.update_xaxes(side="top", title_text="")
    fig.update_yaxes(title_text="")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Bordô = melhor posicionamento no universo. Creme = pior.")


def _render_scenarios_heatmap() -> None:
    df = load_scenarios()
    pivot = (
        df.pivot_table(index="ticker", columns="scenario", values="implied_upside_pct")
        .reindex(columns=SCENARIO_ORDER)
        .rename(columns=SCENARIO_LABEL)
    )
    pivot = pivot.reindex(_ranked_tickers())
    pivot = pivot * 100

    abs_max = max(abs(pivot.min().min()), abs(pivot.max().max()))
    fig = px.imshow(
        pivot,
        color_continuous_scale=COLORSCALE_DIVERGING,
        color_continuous_midpoint=0,
        zmin=-abs_max,
        zmax=abs_max,
        text_auto=".1f",
        aspect="auto",
    )
    fig.update_traces(
        textfont=dict(size=11, color="#1C1C1C"),
        hovertemplate="%{y} · %{x}: %{z:+.1f}%<extra></extra>",
    )
    apply_brand_layout(fig, title="Upside Implícito por Cenário Macro (%)", height=420)
    fig.update_xaxes(side="top", title_text="")
    fig.update_yaxes(title_text="")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Bull: Selic 10%, IPCA 4%. Base: Selic 13.5%, IPCA 5.5%. Bear: Selic 15.5%, IPCA 7.5%."
    )


def _render_score_decomposition() -> None:
    st.markdown("### Decomposição do Score")
    df = load_ultimate_scores()
    tickers = (
        df.sort_values("ultimate_score", ascending=False)["ticker"].tolist()
    )
    default_idx = tickers.index("ITUB4") if "ITUB4" in tickers else 0
    ticker = st.selectbox(
        "Selecione um ticker", tickers, index=default_idx, key="universo_ticker"
    )

    row = df[df["ticker"] == ticker].iloc[0]
    components = {
        "Fundamentos": float(row["fundamental_score"]),
        "Valuation": float(row["valuation_score"]),
        "Sentimento Textual": float(row["textual_index"]),
        "Prob. Outperform": float(row["outperform_probability"]) * 100,
    }
    plot_df = pd.DataFrame(
        {"Componente": list(components.keys()), "Valor": list(components.values())}
    )

    fig = px.bar(
        plot_df,
        x="Valor",
        y="Componente",
        orientation="h",
        text=plot_df["Valor"].map(lambda v: f"{v:.1f}"),
        color_discrete_sequence=[BRAND_BORDO],
    )
    fig.update_traces(
        textposition="outside",
        textfont=dict(color="#1C1C1C", size=12),
        cliponaxis=False,
    )
    fig.update_xaxes(range=[0, 110])
    fig.update_yaxes(autorange="reversed")
    apply_brand_layout(
        fig, title=f"Decomposição do Score — {ticker}", height=320
    )
    st.plotly_chart(fig, use_container_width=True)


def render() -> None:
    st.markdown(
        '<h3 style="margin-top:1rem; color:#6B6B6B; font-weight:500;">'
        "Visão geral do universo coberto</h3>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Bancos e energia elétrica brasileiros — 10 tickers, dados de fundamentos "
        "2020-2024 e mercado até hoje."
    )

    _render_ranking()
    st.markdown("")
    _render_kpis_heatmap()
    st.markdown("")
    _render_scenarios_heatmap()
    st.markdown("")
    _render_score_decomposition()

    st.caption(f"Dados atualizados em {get_data_freshness()}.")
