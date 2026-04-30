"""
Generate a professional 8-page PDF equity research report using reportlab.

Usage:
    python -m src.report.report_generator
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import seaborn as sns
from reportlab.lib import colors as rl_colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "output"
TMP_DIR = OUTPUT_DIR / "tmp"

NAVY = rl_colors.HexColor("#1a3c5e")
GREEN = rl_colors.HexColor("#16a34a")
YELLOW = rl_colors.HexColor("#eab308")
RED = rl_colors.HexColor("#e11d48")
LIGHT_GRAY = rl_colors.HexColor("#f3f4f6")
WHITE = rl_colors.white

COMPANY = {
    "ITUB4": "Itau Unibanco", "BBDC4": "Bradesco", "BBAS3": "Banco do Brasil",
    "SANB11": "Santander Brasil", "ABCB4": "Banco ABC Brasil",
    "EGIE3": "Engie Brasil", "EQTL3": "Equatorial Energia",
    "CPFE3": "CPFL Energia", "TAEE11": "Taesa", "CMIG4": "Cemig",
}

PAGE_W, PAGE_H = A4
DISCLAIMER = "Relatorio gerado automaticamente -- nao constitui recomendacao de investimento"


# ── Styles ──────────────────────────────────────────────────────────────────

def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("SectionTitle", parent=ss["Heading1"], fontSize=14,
                          textColor=NAVY, spaceAfter=8, spaceBefore=12))
    ss.add(ParagraphStyle("Sub", parent=ss["Heading2"], fontSize=11,
                          textColor=NAVY, spaceAfter=4, spaceBefore=8))
    ss.add(ParagraphStyle("Body", parent=ss["BodyText"], fontSize=9,
                          leading=13, alignment=TA_JUSTIFY, spaceAfter=6))
    ss.add(ParagraphStyle("Caption", parent=ss["Italic"], fontSize=8,
                          textColor=rl_colors.gray, alignment=TA_CENTER,
                          spaceAfter=10))
    ss.add(ParagraphStyle("LimitBox", parent=ss["BodyText"], fontSize=8,
                          leading=11, backColor=LIGHT_GRAY, borderPadding=6,
                          spaceAfter=8))
    ss.add(ParagraphStyle("Footer", parent=ss["Normal"], fontSize=7,
                          textColor=rl_colors.gray, alignment=TA_CENTER))
    return ss


# ── Footer callback ─────────────────────────────────────────────────────────

def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(rl_colors.gray)
    canvas.drawCentredString(PAGE_W / 2, 1.2 * cm,
                             f"{DISCLAIMER}  |  Pagina {doc.page}")
    canvas.restoreState()


# ── Standard table style ────────────────────────────────────────────────────

def _navy_table(data, col_widths):
    """Return a Table with navy header and striped rows."""
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


# ── Figures ─────────────────────────────────────────────────────────────────

def _make_heatmap() -> str:
    """Generate KPI heatmap and return path to PNG."""
    kpis = pd.read_parquet(DATA_DIR / "kpis_wide.parquet")
    k24 = kpis[kpis["year"] == 2024].set_index("ticker")
    cols = ["roe", "net_margin", "revenue_cagr", "debt_to_equity",
            "momentum_12m", "volatility_annualized"]
    display_names = ["ROE", "Net Margin", "Rev CAGR", "D/E",
                     "Momentum 12m", "Volatility"]

    data = k24[cols].copy()
    normed = data.copy()
    for c in normed.columns:
        cmin, cmax = normed[c].min(), normed[c].max()
        if cmax != cmin:
            normed[c] = (normed[c] - cmin) / (cmax - cmin)
        else:
            normed[c] = 0.5

    fig, ax = plt.subplots(figsize=(8, 4.5))
    mask = data.isna()
    sns.heatmap(normed, annot=data.round(3).values, fmt="", cmap="RdYlGn",
                linewidths=0.5, ax=ax, mask=mask,
                xticklabels=display_names,
                cbar_kws={"label": "Normalizado (0=min, 1=max)"})
    sns.heatmap(mask.astype(float), cmap=["#d1d5db"], cbar=False,
                linewidths=0.5, ax=ax, alpha=0.4,
                xticklabels=display_names)
    ax.set_title("KPIs por Empresa (2024)", fontsize=13)
    ax.set_ylabel("")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    path = str(TMP_DIR / "heatmap.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _make_scenario_heatmap() -> str:
    """Generate scenario upside heatmap."""
    scen = pd.read_parquet(DATA_DIR / "scenarios_2024.parquet")
    pivot = scen.pivot_table(index="ticker", columns="scenario",
                             values="implied_upside_pct")[["bull", "base", "bear"]]

    fig, ax = plt.subplots(figsize=(6, 4.5))
    sns.heatmap(pivot * 100, annot=True, fmt=".1f", center=0, cmap="RdYlGn",
                linewidths=0.5, ax=ax,
                cbar_kws={"label": "Upside Implicito (%)"},
                xticklabels=["Bull", "Base", "Bear"])
    ax.set_title("Upside Implicito por Cenario (%)", fontsize=12)
    ax.set_ylabel("")
    plt.tight_layout()
    path = str(TMP_DIR / "scenarios.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _make_feature_importance() -> str:
    """Generate feature importance horizontal bar chart."""
    df = pd.read_parquet(DATA_DIR / "feature_importance.parquet")
    top10 = df.nlargest(10, "importance").sort_values("importance")

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(top10["feature"], top10["importance"], color="#1a3c5e")
    ax.set_xlabel("Importancia Relativa")
    ax.set_title("Top 10 Features — Modelo Supervisionado (LogisticRegression)", fontsize=12)
    plt.tight_layout()
    path = str(TMP_DIR / "feature_importance.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _make_pca_scatter() -> str:
    """Generate PCA 2D scatter plot with cluster labels."""
    df = pd.read_parquet(DATA_DIR / "clusters_2024.parquet")
    colors = {"Quality": "#2ecc71", "Growth": "#3498db", "Risk": "#e74c3c"}

    fig, ax = plt.subplots(figsize=(7, 5))
    for cluster, group in df.groupby("cluster_label"):
        ax.scatter(group["pca_x"], group["pca_y"],
                   label=cluster, color=colors.get(cluster, "gray"), s=120,
                   edgecolors="white", zorder=5)
        for _, row in group.iterrows():
            ax.annotate(row["ticker"], (row["pca_x"], row["pca_y"]),
                        textcoords="offset points", xytext=(8, 4), fontsize=9,
                        fontweight="bold")
    ax.set_xlabel("PCA Componente 1")
    ax.set_ylabel("PCA Componente 2")
    ax.set_title("Clusters por Perfil Financeiro (KMeans k=3, 2024)", fontsize=12)
    ax.legend(title="Cluster")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    path = str(TMP_DIR / "pca_clusters.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _make_agent_diagram() -> str:
    """Generate agent architecture flow diagram."""
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")

    boxes = [
        (0.9, 2.0, "INPUT\n(tickers + perfil)", "#1a3c5e"),
        (3.0, 2.0, "6 TOOLS\n(KPIs, Precos,\nMacro, Sentiment,\nValuation, Score)", "#2980b9"),
        (5.4, 2.0, "ORQUESTRADOR\n(EquityResearch\nAgent)", "#1a3c5e"),
        (7.6, 2.0, "RISK FLAGS\n+ Score ajustado\npor perfil", "#e67e22"),
        (9.4, 2.0, "DOSSIER\n(TXT/PDF)", "#27ae60"),
    ]
    for x, y, label, color in boxes:
        ax.add_patch(mpatches.FancyBboxPatch(
            (x - 0.85, y - 0.7), 1.7, 1.4,
            boxstyle="round,pad=0.1", facecolor=color, alpha=0.85,
            edgecolor="white"))
        ax.text(x, y, label, ha="center", va="center", color="white",
                fontsize=7.5, fontweight="bold")

    for i in range(len(boxes) - 1):
        ax.annotate("", xy=(boxes[i + 1][0] - 0.85, boxes[i + 1][1]),
                    xytext=(boxes[i][0] + 0.85, boxes[i][1]),
                    arrowprops=dict(arrowstyle="->", color="#555", lw=2))

    ax.set_title("Arquitetura do Agente de IA (Tool-Using)",
                 fontsize=12, fontweight="bold", pad=10)
    plt.tight_layout()
    path = str(TMP_DIR / "agent_diagram.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


# ── Pages ───────────────────────────────────────────────────────────────────

def _page_cover(story, ss):
    story.append(Spacer(1, 6 * cm))
    story.append(Paragraph(
        "AI Equity Research Report", ParagraphStyle(
            "CoverTitle", parent=ss["Title"], fontSize=26, textColor=NAVY,
            alignment=TA_CENTER)))
    story.append(Paragraph(
        "Bancos &amp; Energia Eletrica", ParagraphStyle(
            "CoverSub1", parent=ss["Title"], fontSize=18, textColor=NAVY,
            alignment=TA_CENTER, spaceAfter=6)))

    # Color bar
    bar_data = [["" * 80]]
    bar = Table(bar_data, colWidths=[PAGE_W - 4 * cm], rowHeights=[4 * mm])
    bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY)]))
    story.append(bar)
    story.append(Spacer(1, 1 * cm))

    story.append(Paragraph(
        "Avaliacao Quantitativa e Qualitativa com IA",
        ParagraphStyle("CoverSub2", parent=ss["Heading2"], fontSize=13,
                       textColor=rl_colors.gray, alignment=TA_CENTER,
                       spaceAfter=12)))
    story.append(Paragraph("Data: 2026-03-27", ParagraphStyle(
        "CoverDate", parent=ss["Normal"], fontSize=11, alignment=TA_CENTER,
        spaceAfter=6)))
    story.append(Paragraph("Joao Paulo Freire", ParagraphStyle(
        "CoverAuthor", parent=ss["Normal"], fontSize=11, alignment=TA_CENTER,
        textColor=NAVY, spaceAfter=4)))
    story.append(Paragraph("AI Equity Research Lab -- FGV EAESP", ParagraphStyle(
        "CoverInst", parent=ss["Normal"], fontSize=10, alignment=TA_CENTER,
        textColor=rl_colors.gray)))
    story.append(PageBreak())


def _page_methodology(story, ss):
    story.append(Paragraph("1. Metodologia", ss["SectionTitle"]))

    subs = [
        ("1.1 Fontes de Dados",
         "Os dados fundamentalistas foram obtidos via CVM Dados Abertos (DFP consolidado), "
         "abrangendo balancos patrimoniais e demonstracoes de resultado de 2020 a 2024. "
         "Dados de mercado (precos diarios, volumes) foram coletados via Yahoo Finance API. "
         "Indicadores macroeconomicos (Selic, IPCA, USD/BRL) foram extraidos do BCB/SGS. "
         "Textos para analise de sentimento vieram do Google News RSS. "
         "Datas de coleta: DFP baixado em 2026-03-27 via portal dados.cvm.gov.br. "
         "Precos coletados via Yahoo Finance API (2026-03-27). "
         "Macro BCB/SGS: serie historica ate fev/2026. "
         "Codigo versionado via Git com commits por etapa do pipeline."),
        ("1.2 Engenharia de KPIs",
         "Foram calculados 14 indicadores financeiros por empresa por ano: ROE, ROA, net margin, "
         "EBIT margin, debt-to-equity, net debt/EBIT, current ratio, cash/revenue, revenue CAGR, "
         "net income CAGR, volatilidade anualizada, max drawdown, momentum 6m e 12m. "
         "Para bancos, ratios de divida sao NaN (funding via depositos). EBITDA usa proxy EBIT x 1.15."),
        ("1.3 NLP e Sentimento",
         "O modelo DistilBERT multilingual (distilbert-base-multilingual-cased-sentiments-student) "
         "classifica textos em positivo/negativo/neutro. Um dicionario de 18 keywords de dominio "
         "pondera riscos e oportunidades. O textual index (0-100) combina ambos com peso de recencia "
         "(half-life 90 dias). O score final incorpora 30% textual + 70% fundamental."),
        ("1.4 Modelos de IA",
         "Trilha supervisionada: walk-forward validation (3 folds temporais) com Logistic Regression, "
         "Random Forest e Gradient Boosting. Melhor modelo: LogisticRegression (ROC AUC medio 0.591). "
         "Trilha nao-supervisionada: KMeans (k=3, silhouette=0.294) identifica clusters Quality, "
         "Growth e Risk via PCA 2D."),
        ("1.5 Valuation",
         "Multiplos calculados: P/L, P/VP, EV/EBITDA (proxy). Analise de desconto/premio vs mediana "
         "setorial. Tres cenarios macro (Bull/Base/Bear) estimam upside implicito via sensibilidade "
         "a Selic, cambio, crescimento de credito e revisoes tarifarias."),
        ("1.6 Score Final",
         "O ultimate score pondera: fundamental+NLP (50%) + valuation (30%) + probabilidade ML (20%). "
         "Recomendacoes: Buy (>=65), Hold (45-64), Sell (<45). O agente de IA integra todos os "
         "sinais em um dossier automatizado."),
        ("1.7 Tratamento de Outliers",
         "Multiplos (P/L, EV/EBITDA) foram truncados em 100x e 50x respectivamente para evitar "
         "distorcao por empresas com lucro marginal. KPIs com mais de 30% de valores ausentes "
         "para um ticker geraram aviso automatico no pipeline. Scores NaN foram substituidos "
         "pela mediana setorial antes da modelagem nao-supervisionada."),
    ]
    for title, text in subs:
        story.append(Paragraph(title, ss["Sub"]))
        story.append(Paragraph(text, ss["Body"]))

    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "<b>Limitacoes:</b> Universo restrito (n=10), proxy EBITDA (EBIT x 1.15), "
        "ABCB4 sem DFP 2024, account_codes bancarios variam por instituicao, "
        "sentimento via RSS (cobertura limitada), walk-forward com apenas 4 anos.",
        ss["LimitBox"]))
    story.append(PageBreak())


def _page_heatmap(story, ss):
    story.append(Paragraph("2. KPIs por Empresa (2024)", ss["SectionTitle"]))
    story.append(Spacer(1, 4 * mm))

    heatmap_path = _make_heatmap()
    story.append(Image(heatmap_path, width=450, height=260))
    story.append(Paragraph(
        "Normalizado 0-1 dentro do universo. Valores ausentes em cinza.",
        ss["Caption"]))
    story.append(PageBreak())


def _page_ranking(story, ss):
    story.append(Paragraph("3. Ranking Final e Recomendacoes", ss["SectionTitle"]))

    ult = pd.read_parquet(DATA_DIR / "ultimate_scores_2024.parquet").sort_values("ultimate_rank")

    header = ["Rank", "Ticker", "Empresa", "Setor", "Score", "Rec", "Upside Base"]
    rows = [header]
    for _, r in ult.iterrows():
        up = r["base_upside_pct"]
        up_str = f"{up*100:+.1f}%" if pd.notna(up) else "N/A"
        sector_short = "Bancos" if r["sector"] == "Bancos" else "Energia"
        rows.append([
            str(int(r["ultimate_rank"])),
            r["ticker"],
            COMPANY.get(r["ticker"], r["ticker"]),
            sector_short,
            f"{r['ultimate_score']:.1f}",
            str(r["recommendation"]),
            up_str,
        ])

    t = Table(rows, colWidths=[30, 50, 100, 50, 40, 35, 60])
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
    ]
    for i, row in enumerate(rows[1:], start=1):
        rec = row[5]
        if rec == "Buy":
            style_cmds.append(("TEXTCOLOR", (5, i), (5, i), GREEN))
        elif rec == "Sell":
            style_cmds.append(("TEXTCOLOR", (5, i), (5, i), RED))
        else:
            style_cmds.append(("TEXTCOLOR", (5, i), (5, i), rl_colors.HexColor("#b45309")))
    t.setStyle(TableStyle(style_cmds))
    story.append(t)
    story.append(Spacer(1, 8 * mm))

    top3 = ult.head(3)
    bot2 = ult.tail(2)
    t1, t2, t3 = top3["ticker"].values
    b1, b2 = bot2["ticker"].values

    story.append(Paragraph(
        f"<b>Top 3:</b> {t1} lidera com score {top3.iloc[0]['ultimate_score']:.1f}, "
        f"combinando alta probabilidade de outperformance e sentimento positivo robusto. "
        f"{t2} e {t3} se beneficiam de valuations atrativos e perfis de qualidade/crescimento. "
        f"<b>Bottom 2:</b> {b1} (score {bot2.iloc[0]['ultimate_score']:.1f}) e "
        f"{b2} ({bot2.iloc[1]['ultimate_score']:.1f}) apresentam fraca combinacao de "
        f"fundamentos, sentimento neutro e momentum negativo.",
        ss["Body"]))
    story.append(PageBreak())


# ── NEW PAGE 4b: Agent ──────────────────────────────────────────────────────

def _page_agent(story, ss):
    story.append(Paragraph("3b. Agente de IA (Tool-Using)", ss["SectionTitle"]))

    # Agent diagram
    diagram_path = _make_agent_diagram()
    story.append(Image(diagram_path, width=440, height=175))
    story.append(Spacer(1, 4 * mm))

    # Tools table
    story.append(Paragraph("Ferramentas do Agente", ss["Sub"]))
    tools_data = [
        ["Tool", "Input", "Output"],
        ["get_kpis", "ticker, year", "14 KPIs dict"],
        ["get_price_history", "ticker, window_days", "price stats dict"],
        ["get_macro_snapshot", "\u2014", "Selic, IPCA, USD/BRL live"],
        ["get_sentiment", "ticker", "textual_index, keywords"],
        ["get_valuation", "ticker", "multiples, upside scenarios"],
        ["get_full_score", "ticker", "ultimate_score, recommendation"],
    ]
    story.append(_navy_table(tools_data, [95, 100, 170]))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph(
        "O agente aceita como input uma lista de tickers e um perfil de risco "
        "(conservador/base/agressivo), orquestra as 6 ferramentas sequencialmente com "
        "tratamento de erros em cada chamada (try/except com fallback para "
        "\"DATA UNAVAILABLE\"), detecta automaticamente risk flags, computa um score "
        "ajustado ao perfil e gera um dossier estruturado. O CLI permite execucao via: "
        "<b>python -m src.agent.cli --tickers ITUB4 EGIE3 --profile base</b>",
        ss["Body"]))

    # Profile weights table
    story.append(Paragraph("Pesos por Perfil de Investidor", ss["Sub"]))
    profile_data = [
        ["Componente", "Conservador", "Base", "Agressivo"],
        ["valuation_score", "35%", "25%", "20%"],
        ["fundamental_score", "30%", "35%", "30%"],
        ["textual_index", "25%", "25%", "15%"],
        ["outperform_prob", "10%", "15%", "35%"],
    ]
    story.append(_navy_table(profile_data, [100, 80, 80, 80]))

    story.append(PageBreak())


def _page_scenarios(story, ss):
    story.append(Paragraph("4. Analise de Cenarios Macro", ss["SectionTitle"]))

    assumptions = [
        ["Parametro", "Bull", "Base", "Bear"],
        ["Selic", "10.0%", "13.5%", "15.5%"],
        ["IPCA", "4.0%", "5.5%", "7.5%"],
        ["USD/BRL", "5.20", "5.80", "6.50"],
        ["PIB", "+2.5%", "+1.5%", "-0.5%"],
    ]
    story.append(_navy_table(assumptions, [70, 60, 60, 60]))
    story.append(Spacer(1, 6 * mm))

    scenario_path = _make_scenario_heatmap()
    story.append(Image(scenario_path, width=360, height=270))
    story.append(Paragraph(
        "Valores em % de upside implicito sobre preco atual.",
        ss["Caption"]))

    story.append(Paragraph(
        "Bancos apresentam maior upside no cenario Bull (ate +11.0%) devido a sensibilidade "
        "positiva ao spread de credito em ambiente de Selic mais baixa. Empresas do setor "
        "eletrico mostram maior resiliencia no cenario Bear, com quedas limitadas a -4.8%, "
        "refletindo receitas reguladas e demanda inelastica por energia. No cenario Base, "
        "todos os tickers apresentam upside modesto (+2% a +4%), consistente com um ambiente "
        "de juros altos e crescimento moderado.",
        ss["Body"]))
    story.append(PageBreak())


# ── NEW PAGE 5b: Explainability + Clusters ──────────────────────────────────

def _page_explainability(story, ss):
    story.append(Paragraph("4b. Explicabilidade e Clusters", ss["SectionTitle"]))

    # Feature importance
    story.append(Paragraph("Feature Importance", ss["Sub"]))
    fi_path = _make_feature_importance()
    story.append(Image(fi_path, width=380, height=220))
    story.append(Paragraph(
        "As 3 features mais importantes foram beta_vs_ibovespa, usdbrl_mean e momentum_12m, "
        "confirmando que em mercados emergentes o risco sistemico e macro dominam o retorno relativo.",
        ss["Caption"]))

    # PCA scatter
    story.append(Paragraph("Clusters PCA 2D", ss["Sub"]))
    pca_path = _make_pca_scatter()
    story.append(Image(pca_path, width=330, height=220))
    story.append(Paragraph(
        "KMeans k=3 (silhouette=0.294) identifica 3 perfis: Quality (EGIE3, TAEE11), "
        "Growth (CMIG4) e Risk (bancos + CPFE3, EQTL3).",
        ss["Caption"]))

    # Walk-forward table
    story.append(Paragraph("Walk-Forward Validation", ss["Sub"]))
    wf_data = [
        ["Fold", "Treino", "Teste", "ROC AUC"],
        ["1", "2020", "2021", "0.875"],
        ["2", "2020-2021", "2022", "0.524"],
        ["3", "2020-2022", "2023", "0.375"],
        ["Media", "\u2014", "\u2014", "0.591 +/- 0.257"],
    ]
    story.append(_navy_table(wf_data, [40, 80, 60, 100]))
    story.append(PageBreak())


def _page_conclusion(story, ss):
    story.append(Paragraph("5. Conclusao e Limitacoes", ss["SectionTitle"]))

    story.append(Paragraph("<b>Conclusao</b>", ss["Sub"]))
    story.append(Paragraph(
        "A analise integrada de dados fundamentalistas, sentimento de mercado e modelos de "
        "machine learning identifica ITUB4, EGIE3, CMIG4 e CPFE3 como as melhores oportunidades "
        "no universo avaliado, com scores acima de 65 e recomendacao Buy. ITUB4 lidera com "
        "score 72.6, sustentado por ROE de 19.0%, net margin de 12.6%, forte probabilidade de "
        "outperformance (98.5%) e sentimento extremamente positivo. No setor eletrico, "
        "EGIE3 combina qualidade financeira (ROE 35%, cluster Quality) com desconto de P/L vs "
        "setor. SANB11 e EQTL3, com scores abaixo de 45, sao os unicos Sell, penalizados por "
        "momentum negativo e posicao relativa fraca nos multiplos setoriais. "
        "Recomenda-se cautela com tickers de perfil Risk e atencao ao cenario macro Bear, "
        "que impacta desproporcionalmente empresas com alta alavancagem.",
        ss["Body"]))

    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("<b>Limitacoes</b>", ss["Sub"]))

    lim_data = [
        ["Limitacao", "Impacto", "Mitigacao"],
        ["Universo n=10", "Baixo poder estatistico",
         "Ampliar para Ibovespa completo"],
        ["Proxy EBITDA (+15% sobre EBIT)", "Multiplos imprecisos",
         "Usar DFC para D&A real"],
        ["NLP via RSS", "Cobertura limitada",
         "Integrar CVM Fatos Relevantes"],
        ["Walk-forward com 4 anos", "Overfitting possivel",
         "Expandir janela historica"],
        ["Universo bancario", "account_codes DRE variam por instituicao",
         "Mapear codigos por setor antes da ingestao"],
    ]
    lt = Table(lim_data, colWidths=[140, 120, 150])
    lt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(lt)


# ── Main ────────────────────────────────────────────────────────────────────

def generate_report(output_path: Path | None = None) -> Path:
    """Build the 8-page PDF report and return the output path."""
    output_path = output_path or OUTPUT_DIR / "relatorio_final.pdf"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    ss = _styles()
    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2.5 * cm,
    )

    story: list = []
    _page_cover(story, ss)          # Page 1
    _page_methodology(story, ss)    # Page 2
    _page_heatmap(story, ss)        # Page 3
    _page_ranking(story, ss)        # Page 4
    _page_agent(story, ss)          # Page 4b (NEW)
    _page_scenarios(story, ss)      # Page 5
    _page_explainability(story, ss) # Page 5b (NEW)
    _page_conclusion(story, ss)     # Page 6

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)

    # Cleanup temp images
    shutil.rmtree(TMP_DIR, ignore_errors=True)

    print(f"Report generated: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_report()
