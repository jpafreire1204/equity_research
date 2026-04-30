"""Generate publication-quality figures for the FGV final paper.

Output: 8 PNGs at 300 DPI in data/output/figures/, plus figures_index.md.
Style: white background, sans-serif (DejaVu Sans), black axes, gray gridlines.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrow, FancyBboxPatch

OUT = Path("data/output/figures")
OUT.mkdir(parents=True, exist_ok=True)

# ---------- Global academic style ----------
mpl.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "axes.edgecolor": "black",
    "axes.linewidth": 0.8,
    "axes.grid": True,
    "grid.color": "#CCCCCC",
    "grid.linewidth": 0.5,
    "grid.linestyle": "--",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})


def _save(fig: plt.Figure, name: str) -> Path:
    path = OUT / name
    fig.savefig(path, dpi=300)
    plt.close(fig)
    return path


# ---------- Figure 1: pipeline architecture ----------
def fig01_pipeline() -> Path:
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")
    ax.grid(False)

    stages = [
        ("Coleta de\nEvidência", "Fundamentos,\nValuation,\nMomentum,\nSentimento,\nMacro"),
        ("Detecção de\nTensões", "Regras\ndeterminísticas\npor driver"),
        ("Similaridade\nSemântica", "MiniLM\nmultilíngue\n(cosine)"),
        ("Score de\nConsistência", "Score 0-100\n+ veredito"),
    ]
    box_w, box_h = 1.9, 2.2
    for i, (title, body) in enumerate(stages):
        x = 0.4 + i * 2.4
        y = 0.9
        box = FancyBboxPatch((x, y), box_w, box_h,
                             boxstyle="round,pad=0.05",
                             linewidth=1.2, edgecolor="black",
                             facecolor="#F5F5F5")
        ax.add_patch(box)
        ax.text(x + box_w / 2, y + box_h - 0.45, title,
                ha="center", va="center", fontsize=11, fontweight="bold")
        ax.text(x + box_w / 2, y + 0.85, body,
                ha="center", va="center", fontsize=9)
        if i < 3:
            ax.annotate("", xy=(x + box_w + 0.45, y + box_h / 2),
                        xytext=(x + box_w + 0.05, y + box_h / 2),
                        arrowprops=dict(arrowstyle="->", lw=1.4, color="black"))
    return _save(fig, "fig01_pipeline.png")


# ---------- Figure 2: walk-forward validation ----------
def fig02_walkforward() -> Path:
    folds = ["Fold 1", "Fold 2", "Fold 3"]
    aucs = [0.875, 0.524, 0.375]
    mean_auc = float(np.mean(aucs))

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(folds, aucs, color="#3F3F3F", edgecolor="black", width=0.55)
    for b, v in zip(bars, aucs):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.3f}",
                ha="center", va="bottom", fontsize=9)

    ax.axhline(0.5, color="black", linestyle="--", linewidth=1.0,
               label="Baseline aleatório (0,500)")
    ax.axhline(mean_auc, color="#7F7F7F", linestyle=":", linewidth=1.2,
               label=f"Média ({mean_auc:.3f})")
    ax.set_ylim(0, 1)
    ax.set_ylabel("ROC AUC")
    ax.set_xlabel("Fold de validação")
    ax.legend(loc="upper right", frameon=True, framealpha=0.9)
    return _save(fig, "fig02_walkforward.png")


# ---------- Figure 3: feature importance ----------
def fig03_feature_importance() -> Path:
    df = pd.read_parquet("data/processed/feature_importance.parquet")
    df = df.sort_values("importance", ascending=False).head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(df["feature"], df["importance"], color="#3F3F3F",
            edgecolor="black", height=0.6)
    for i, v in enumerate(df["importance"]):
        ax.text(v + 0.005, i, f"{v:.3f}", va="center", fontsize=9)
    ax.set_xlabel("Importância (Gini)")
    ax.set_xlim(0, df["importance"].max() * 1.15)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    return _save(fig, "fig03_feature_importance.png")


# ---------- Figure 4: confusion matrix (validation) ----------
def fig04_confusion_matrix() -> Path:
    df = pd.read_csv("data/validation/results.csv")
    verdict_order = ["sustentavel", "sustentavel_com_ressalvas", "fragilizada"]
    outcome_order = ["sustained", "failed", "inconclusive"]
    verdict_labels = ["Sustentável", "Com Ressalvas", "Fragilizada"]
    outcome_labels = ["Sustained", "Failed", "Inconclusive"]
    mat = pd.crosstab(df["verdict"], df["ground_truth_outcome"], dropna=False)
    mat = mat.reindex(index=verdict_order, columns=outcome_order, fill_value=0)

    fig, ax = plt.subplots(figsize=(6, 4))
    z = mat.values
    im = ax.imshow(z, cmap="Greys", vmin=0, vmax=z.max() * 1.2, aspect="auto")
    ax.set_xticks(range(3))
    ax.set_yticks(range(3))
    ax.set_xticklabels(outcome_labels)
    ax.set_yticklabels(verdict_labels)
    ax.set_xlabel("Ground Truth (alpha 6m vs IBOV)")
    ax.set_ylabel("Veredito do Auditor")
    ax.grid(False)
    threshold = z.max() * 0.6
    for i in range(3):
        for j in range(3):
            color = "white" if z[i, j] > threshold else "black"
            ax.text(j, i, str(z[i, j]), ha="center", va="center",
                    fontsize=12, color=color, fontweight="bold")
    cb = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.03)
    cb.set_label("Contagem")
    return _save(fig, "fig04_confusion_matrix.png")


# ---------- Figure 5: precision and recall by verdict ----------
def fig05_precision_recall() -> Path:
    verdicts = ["Sustentável", "Com Ressalvas", "Fragilizada"]
    precisions = [0.556, 0.345, 1.000]
    recalls = [0.333, 0.769, 0.091]

    x = np.arange(len(verdicts))
    width = 0.35
    fig, ax = plt.subplots(figsize=(8, 4.5))
    b1 = ax.bar(x - width / 2, precisions, width, label="Precisão",
                color="#1F1F1F", edgecolor="black")
    b2 = ax.bar(x + width / 2, recalls, width, label="Recall",
                color="#999999", edgecolor="black")
    for bars, vals in [(b1, precisions), (b2, recalls)]:
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.2f}",
                    ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(verdicts)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Score")
    ax.legend(loc="upper center", ncol=2, frameon=True)
    return _save(fig, "fig05_precision_recall.png")


# ---------- Figure 6: KPIs heatmap by ticker ----------
def fig06_kpis_heatmap() -> Path:
    df = pd.read_parquet("data/processed/kpis_wide.parquet")
    df = df[df["year"] == 2024].copy()
    if df.empty:
        df = pd.read_parquet("data/processed/kpis_wide.parquet")
        df = df.sort_values("year").groupby("ticker").tail(1)

    kpis = ["roe", "net_margin", "revenue_cagr", "net_income_cagr",
            "momentum_12m", "max_drawdown"]
    kpi_labels = ["ROE", "Margem Líquida", "Rev. CAGR",
                  "Net Inc. CAGR", "Mom. 12m", "Max DD"]
    sub = df.set_index("ticker")[kpis]

    # Reorder rows by ultimate score descending (paper convention: best on top).
    scores = pd.read_parquet("data/processed/ultimate_scores_2024.parquet")
    order = (scores.sort_values("ultimate_score", ascending=False)["ticker"].tolist())
    sub = sub.reindex([t for t in order if t in sub.index])

    # Min-max normalize each KPI column to 0-1 within the universe of 10 tickers.
    # max_drawdown is already negative-better-is-higher; min-max preserves direction.
    norm = sub.copy()
    for c in kpis:
        col = norm[c]
        if col.notna().sum() < 2:
            norm[c] = 0.5
            continue
        lo, hi = col.min(), col.max()
        if hi == lo:
            norm[c] = 0.5
        else:
            norm[c] = (col - lo) / (hi - lo)

    fig, ax = plt.subplots(figsize=(8, 5))
    z = norm.values
    im = ax.imshow(z, cmap="Greys", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(kpis)))
    ax.set_xticklabels(kpi_labels, rotation=30, ha="right")
    ax.set_yticks(range(len(norm.index)))
    ax.set_yticklabels(norm.index)
    ax.grid(False)
    for i in range(z.shape[0]):
        for j in range(z.shape[1]):
            v = z[i, j]
            txt = "n/d" if pd.isna(v) else f"{v:.2f}"
            color = "white" if (not pd.isna(v) and v > 0.6) else "black"
            ax.text(j, i, txt, ha="center", va="center", fontsize=8, color=color)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label("Posição relativa (min-max)")
    return _save(fig, "fig06_kpis_heatmap.png")


# ---------- Figure 7: macro scenarios upside ----------
def fig07_scenarios_heatmap() -> Path:
    df = pd.read_parquet("data/processed/scenarios_2024.parquet")
    pivot = df.pivot_table(index="ticker", columns="scenario",
                           values="implied_upside_pct", aggfunc="first")
    col_order = [c for c in ["bull", "base", "bear"] if c in pivot.columns]
    pivot = pivot[col_order]
    col_labels = {"bull": "Bull", "base": "Base", "bear": "Bear"}

    fig, ax = plt.subplots(figsize=(7, 5))
    z = pivot.values
    vmax = float(np.nanmax(np.abs(z))) if z.size else 0.1
    im = ax.imshow(z, cmap="RdBu", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks(range(pivot.shape[1]))
    ax.set_xticklabels([col_labels.get(c, c) for c in pivot.columns])
    ax.set_yticks(range(pivot.shape[0]))
    ax.set_yticklabels(pivot.index)
    ax.grid(False)
    for i in range(z.shape[0]):
        for j in range(z.shape[1]):
            v = z[i, j]
            if pd.isna(v):
                continue
            color = "white" if abs(v) > vmax * 0.55 else "black"
            ax.text(j, i, f"{v * 100:+.1f}%", ha="center", va="center",
                    fontsize=8, color=color)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label("Upside implícito (DCF, 12m)")
    return _save(fig, "fig07_scenarios_heatmap.png")


# ---------- Figure 8: ITUB4 score decomposition ----------
def fig08_score_decomposition() -> Path:
    df = pd.read_parquet("data/processed/ultimate_scores_2024.parquet")
    row = df[df["ticker"] == "ITUB4"].iloc[0]
    components = [
        ("Fundamentos", float(row["fundamental_score"])),
        ("Valuation", float(row["valuation_score"])),
        ("Sentimento (textual)", float(row["textual_index"])),
        ("Prob. Outperform", float(row["outperform_probability"]) * 100.0),
    ]
    components = components[::-1]  # so highest at top after invert
    labels = [c[0] for c in components]
    values = [c[1] for c in components]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(labels, values, color="#3F3F3F", edgecolor="black", height=0.5)
    for i, v in enumerate(values):
        ax.text(v + 1.5, i, f"{v:.1f}", va="center", fontsize=9)
    ax.set_xlim(0, 105)
    ax.set_xlabel("Score (0-100)")
    ax.grid(axis="y", visible=False)
    final_score = float(row["ultimate_score"])
    ax.axvline(final_score, color="black", linestyle="--", linewidth=1.0,
               label=f"Score final ITUB4: {final_score:.1f}")
    ax.legend(loc="lower right", frameon=True)
    return _save(fig, "fig08_score_decomposition.png")


# ---------- figures_index.md ----------
INDEX_MD = """# Figures Index — FGV Final Paper

| # | Arquivo | Caption (PT-BR) |
|---|---|---|
| 1 | fig01_pipeline.png | **Figura 1.** Arquitetura do Auditor de Tese em quatro estágios determinísticos: coleta de evidência por driver, detecção de tensões via regras, similaridade semântica entre tese e narrativa data-driven, e score de consistência final. |
| 2 | fig02_walkforward.png | **Figura 2.** ROC AUC por fold no esquema de validação walk-forward. A média de 0,591 é compatível com discriminação modesta, com forte variância entre folds (0,375 a 0,875), refletindo o tamanho reduzido da amostra. |
| 3 | fig03_feature_importance.png | **Figura 3.** Top 10 features por importância (Gini) no modelo supervisionado de classificação binária outperform vs Ibovespa. Beta vs Ibovespa, CAGR de lucro líquido e taxa de câmbio média lideram. |
| 4 | fig04_confusion_matrix.png | **Figura 4.** Matriz de confusão da validação histórica do Auditor (n=39 teses, 2022-2024) contra ground truth de retorno em 6 meses vs Ibovespa com zona morta de ±5pp. O sistema concentra vereditos em "Com Ressalvas" por desenho conservador. |
| 5 | fig05_precision_recall.png | **Figura 5.** Precisão e recall por classe de veredito. O Auditor atinge precisão de 100% em Fragilizada e 55,6% em Sustentável, mas recall baixo (9,1% e 33,3%, respectivamente) — trade-off de uma calibração que recusa falsa certeza. |
| 6 | fig06_kpis_heatmap.png | **Figura 6.** Heatmap normalizado dos seis KPIs fundamentais por ticker (2024). Tons mais escuros indicam posição relativa superior dentro do universo de 10 ações. |
| 7 | fig07_scenarios_heatmap.png | **Figura 7.** Upside implícito por DCF em três cenários macro (Bull/Base/Bear) para os 10 tickers do universo. Tons azuis indicam upside positivo; vermelhos, downside. |
| 8 | fig08_score_decomposition.png | **Figura 8.** Decomposição do score final do ITUB4 nos quatro componentes do framework: fundamentos, valuation, sentimento textual e probabilidade de outperform. A linha tracejada marca o ultimate score consolidado. |
"""


def write_index() -> Path:
    p = OUT / "figures_index.md"
    p.write_text(INDEX_MD, encoding="utf-8")
    return p


# ---------- main ----------
def main() -> None:
    paths = [
        fig01_pipeline(),
        fig02_walkforward(),
        fig03_feature_importance(),
        fig04_confusion_matrix(),
        fig05_precision_recall(),
        fig06_kpis_heatmap(),
        fig07_scenarios_heatmap(),
        fig08_score_decomposition(),
        write_index(),
    ]
    for p in paths:
        size_kb = p.stat().st_size / 1024
        print(f"  {p}  ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
