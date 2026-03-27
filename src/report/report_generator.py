"""
Generate a professional 6-page PDF equity research report using reportlab.

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
    # Normalize 0-1
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
    # Gray out NaN cells
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
    story.append(Paragraph("AI Equity Research Lab -- FGV EAESP", ParagraphStyle(
        "CoverAuthor", parent=ss["Normal"], fontSize=11, alignment=TA_CENTER,
        textColor=NAVY)))
    story.append(PageBreak())


def _page_methodology(story, ss):
    story.append(Paragraph("1. Metodologia", ss["SectionTitle"]))

    subs = [
        ("1.1 Fontes de Dados",
         "Os dados fundamentalistas foram obtidos via CVM Dados Abertos (DFP consolidado), "
         "abrangendo balancos patrimoniais e demonstracoes de resultado de 2020 a 2024. "
         "Dados de mercado (precos diarios, volumes) foram coletados via Yahoo Finance API. "
         "Indicadores macroeconomicos (Selic, IPCA, USD/BRL) foram extraidos do BCB/SGS. "
         "Textos para analise de sentimento vieram do Google News RSS."),
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
    ]
    for title, text in subs:
        story.append(Paragraph(title, ss["Sub"]))
        story.append(Paragraph(text, ss["Body"]))

    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "<b>Limitacoes:</b> Universo restrito (n=10), proxy EBITDA (EBIT x 1.15), "
        "dados faltantes ITUB4 (net_income NaN), ABCB4 sem DFP 2024, "
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
    # Color-code Rec column (index 5)
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

    # Justification paragraph
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


def _page_scenarios(story, ss):
    story.append(Paragraph("4. Analise de Cenarios Macro", ss["SectionTitle"]))

    # Assumptions mini-table
    assumptions = [
        ["Parametro", "Bull", "Base", "Bear"],
        ["Selic", "10.0%", "13.5%", "15.5%"],
        ["IPCA", "4.0%", "5.5%", "7.5%"],
        ["USD/BRL", "5.20", "5.80", "6.50"],
        ["PIB", "+2.5%", "+1.5%", "-0.5%"],
    ]
    at = Table(assumptions, colWidths=[70, 60, 60, 60])
    at.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.lightgrey),
    ]))
    story.append(at)
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


def _page_conclusion(story, ss):
    story.append(Paragraph("5. Conclusao e Limitacoes", ss["SectionTitle"]))

    story.append(Paragraph("<b>Conclusao</b>", ss["Sub"]))
    story.append(Paragraph(
        "A analise integrada de dados fundamentalistas, sentimento de mercado e modelos de "
        "machine learning identifica ITUB4, EGIE3, CMIG4 e CPFE3 como as melhores oportunidades "
        "no universo avaliado, com scores acima de 65 e recomendacao Buy. ITUB4 lidera apesar "
        "de dados incompletos (net_income NaN), sustentado por forte probabilidade de outperformance "
        "do modelo supervisionado (98.5%) e sentimento extremamente positivo. No setor eletrico, "
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
        ["ITUB4 net_income faltando", "Score parcial",
         "Verificar CNPJ no DFP"],
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
    """Build the 6-page PDF report and return the output path."""
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
    _page_cover(story, ss)
    _page_methodology(story, ss)
    _page_heatmap(story, ss)
    _page_ranking(story, ss)
    _page_scenarios(story, ss)
    _page_conclusion(story, ss)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)

    # Cleanup temp images
    shutil.rmtree(TMP_DIR, ignore_errors=True)

    print(f"Report generated: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_report()
