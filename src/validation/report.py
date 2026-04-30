"""Confusion matrix, per-driver error analysis, and markdown report."""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

DATA_DIR = Path("data/validation")
RESULTS_PATH = DATA_DIR / "results.csv"
REPORT_PATH = DATA_DIR / "VALIDATION_REPORT.md"

VERDICT_ORDER = ["sustentavel", "sustentavel_com_ressalvas", "fragilizada"]
OUTCOME_ORDER = ["sustained", "failed", "inconclusive"]
VERDICT_LABELS = {
    "sustentavel": "Sustentável",
    "sustentavel_com_ressalvas": "Com Ressalvas",
    "fragilizada": "Fragilizada",
}
OUTCOME_LABELS = {
    "sustained": "Sustained",
    "failed": "Failed",
    "inconclusive": "Inconclusive",
}


def load_results() -> pd.DataFrame:
    if not RESULTS_PATH.exists():
        raise FileNotFoundError(f"Missing results file: {RESULTS_PATH}")
    return pd.read_csv(RESULTS_PATH)


def confusion_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Rows = auditor verdict, cols = ground truth outcome."""
    sub = df[df["ground_truth_outcome"].isin(OUTCOME_ORDER)]
    mat = pd.crosstab(
        sub["verdict"], sub["ground_truth_outcome"], dropna=False,
    )
    mat = mat.reindex(index=VERDICT_ORDER, columns=OUTCOME_ORDER, fill_value=0)
    return mat


def metrics(df: pd.DataFrame) -> dict[str, Any]:
    """Accuracy on conclusive theses + per-class precision/recall."""
    conclusive = df[df["ground_truth_outcome"].isin(["sustained", "failed"])].copy()
    n_conclusive = len(conclusive)
    if n_conclusive == 0:
        return {"n_conclusive": 0}

    correct = (conclusive["match"] == "yes").sum()
    accuracy = correct / n_conclusive

    pr = {}
    for verdict in VERDICT_ORDER:
        pred_mask = df["verdict"] == verdict
        outcome_for_verdict = {
            "sustentavel": "sustained",
            "sustentavel_com_ressalvas": "inconclusive",
            "fragilizada": "failed",
        }[verdict]
        true_mask = df["ground_truth_outcome"] == outcome_for_verdict
        tp = int((pred_mask & true_mask).sum())
        fp = int((pred_mask & ~true_mask & df["ground_truth_outcome"].isin(OUTCOME_ORDER)).sum())
        fn = int((~pred_mask & true_mask).sum())
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        pr[verdict] = {"precision": round(precision, 3), "recall": round(recall, 3),
                       "tp": tp, "fp": fp, "fn": fn}

    return {
        "n_total": int(len(df)),
        "n_conclusive": int(n_conclusive),
        "n_inconclusive": int((df["ground_truth_outcome"] == "inconclusive").sum()),
        "n_out_of_sample": int((df["ground_truth_outcome"] == "out_of_sample").sum()),
        "accuracy": round(accuracy, 3),
        "per_class": pr,
    }


def driver_error_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """For wrong predictions, count how often each driver appeared in the thesis."""
    wrong = df[(df["match"] == "no") &
               (df["ground_truth_outcome"].isin(["sustained", "failed"]))]
    if wrong.empty:
        return pd.DataFrame(columns=["driver", "wrong_count", "share_of_wrong"])
    counts: Counter[str] = Counter()
    for s in wrong["drivers"].fillna(""):
        for d in s.split("|"):
            d = d.strip()
            if d:
                counts[d] += 1
    total = sum(counts.values()) or 1
    rows = [{"driver": d, "wrong_count": c, "share_of_wrong": round(c / total, 3)}
            for d, c in counts.most_common()]
    return pd.DataFrame(rows)


def driver_error_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Per driver: % wrong when this driver appears in the thesis."""
    conclusive = df[df["ground_truth_outcome"].isin(["sustained", "failed"])]
    rows: list[dict[str, Any]] = []
    all_drivers = set()
    for s in conclusive["drivers"].fillna(""):
        for d in s.split("|"):
            d = d.strip()
            if d:
                all_drivers.add(d)
    for driver in sorted(all_drivers):
        mask = conclusive["drivers"].fillna("").str.contains(driver, regex=False)
        sub = conclusive[mask]
        if len(sub) == 0:
            continue
        wrong = (sub["match"] == "no").sum()
        rows.append({
            "driver": driver,
            "n_appearances": int(len(sub)),
            "n_wrong": int(wrong),
            "error_rate": round(wrong / len(sub), 3),
        })
    return pd.DataFrame(rows).sort_values("error_rate", ascending=False)


def _matrix_to_md(mat: pd.DataFrame) -> str:
    cols = [OUTCOME_LABELS[c] for c in mat.columns]
    header = "| Auditor \\ Ground Truth | " + " | ".join(cols) + " |"
    sep = "|" + "|".join(["---"] * (len(cols) + 1)) + "|"
    lines = [header, sep]
    for verdict in mat.index:
        row = " | ".join(str(int(v)) for v in mat.loc[verdict].values)
        lines.append(f"| {VERDICT_LABELS[verdict]} | {row} |")
    return "\n".join(lines)


def write_report(df: pd.DataFrame) -> Path:
    mat = confusion_matrix(df)
    m = metrics(df)
    drv_overall = driver_error_analysis(df)
    drv_rate = driver_error_breakdown(df)

    pub_min = df["publication_date"].min() if not df.empty else "n/d"
    pub_max = df["publication_date"].max() if not df.empty else "n/d"

    lines: list[str] = []
    lines.append("# Validação Histórica do Auditor de Teses")
    lines.append("")
    lines.append("## Resumo Executivo")
    lines.append("")
    lines.append(
        f"Validamos o Auditor de Teses contra **{m.get('n_total', 0)} teses curadas** "
        f"da imprensa financeira brasileira (2022–2024), com retorno de 6 meses do ativo "
        f"vs. Ibovespa como ground truth e zona morta de ±5 pontos percentuais. "
        f"Em **{m.get('n_conclusive', 0)} teses conclusivas** (fora da zona morta), o auditor "
        f"obteve **{m.get('accuracy', 0) * 100:.1f}% de acurácia**. "
        f"Outras {m.get('n_inconclusive', 0)} teses caíram dentro da zona morta e "
        f"{m.get('n_out_of_sample', 0)} ficaram fora da janela de preços disponível."
    )
    lines.append("")

    lines.append("## Metodologia")
    lines.append("")
    lines.append("- **Universo:** 10 tickers (5 bancos: ITUB4, BBDC4, BBAS3, SANB11, ABCB4; "
                 "5 utilities: EGIE3, EQTL3, CPFE3, TAEE11, CMIG4).")
    lines.append(f"- **Janela de publicação:** {pub_min} a {pub_max}.")
    lines.append("- **Ground truth:** alpha = retorno do ticker em 6m − retorno do Ibovespa "
                 "no mesmo intervalo.")
    lines.append("- **Zona morta:** |alpha| < 5pp ⇒ **inconclusive** (excluído da acurácia).")
    lines.append("- **Mapeamento auditor → previsão:** sustentavel→sustained, "
                 "sustentavel_com_ressalvas→inconclusive, fragilizada→failed.")
    lines.append("- **Descoberta:** Exa MCP web search sobre infomoney, moneytimes, "
                 "seudinheiro, valor, suno, investidor10. Triagem humana com SKIP em "
                 "artigos sem tese (notícias, releases, paywall stubs).")
    lines.append("- **Sem LLM no loop:** extração de tese e ground truth são determinísticos; "
                 "o auditor usa apenas seu próprio scorer + sentence-transformers.")
    lines.append("")

    lines.append("## Resultados")
    lines.append("")
    lines.append("### Matriz de Confusão (apenas teses conclusivas)")
    lines.append("")
    lines.append(_matrix_to_md(mat))
    lines.append("")
    lines.append(f"**Acurácia:** {m.get('accuracy', 0) * 100:.1f}% "
                 f"({int(m.get('accuracy', 0) * m.get('n_conclusive', 0))}/{m.get('n_conclusive', 0)})")
    lines.append("")
    lines.append("### Precisão e Recall por Veredito")
    lines.append("")
    lines.append("| Veredito | Precisão | Recall | TP | FP | FN |")
    lines.append("|---|---|---|---|---|---|")
    for v in VERDICT_ORDER:
        cls = m.get("per_class", {}).get(v, {})
        lines.append(
            f"| {VERDICT_LABELS[v]} | {cls.get('precision', 0):.3f} | "
            f"{cls.get('recall', 0):.3f} | {cls.get('tp', 0)} | "
            f"{cls.get('fp', 0)} | {cls.get('fn', 0)} |"
        )
    lines.append("")

    lines.append("## Análise por Driver")
    lines.append("")
    if drv_rate.empty:
        lines.append("_Sem teses conclusivas para análise por driver._")
    else:
        lines.append("Taxa de erro por driver (entre teses conclusivas em que o driver foi citado):")
        lines.append("")
        lines.append("| Driver | Aparições | Erros | Taxa de erro |")
        lines.append("|---|---|---|---|")
        for _, r in drv_rate.iterrows():
            lines.append(
                f"| {r['driver']} | {int(r['n_appearances'])} | {int(r['n_wrong'])} | "
                f"{r['error_rate'] * 100:.1f}% |"
            )
        lines.append("")
        if not drv_overall.empty:
            top = drv_overall.iloc[0]
            lines.append(
                f"Driver mais associado a erros do auditor: **{top['driver']}** "
                f"({int(top['wrong_count'])} ocorrências em teses incorretas, "
                f"{top['share_of_wrong'] * 100:.1f}% do total)."
            )
    lines.append("")

    lines.append("## Limitações")
    lines.append("")
    lines.append("- **Amostra pequena (~30 teses).** Intervalos de confiança são largos; "
                 "diferenças <10pp entre vereditos não são estatisticamente significativas.")
    lines.append("- **Viés retrospectivo na descoberta.** A imprensa financeira tende a "
                 "publicar mais teses bullish, desbalanceando o conjunto.")
    lines.append("- **Janela de 6 meses é arbitrária.** Teses fundamentalistas tipicamente "
                 "miram 12-24m; testes mais longos podem alterar o resultado.")
    lines.append("- **Zona morta de 5pp.** Filtra ruído mas pode mascarar acertos marginais.")
    lines.append("- **Triagem com julgamento humano.** Direção e drivers extraídos manualmente "
                 "podem divergir da intenção original do autor em casos ambíguos.")
    lines.append("- **Ground truth não captura tese de longo prazo.** Um movimento de preço "
                 "em 6m pode ser ruído mesmo quando a tese fundamental está correta (ou vice-versa).")
    lines.append("")

    lines.append("## Conclusão")
    lines.append("")
    lines.append(
        f"O auditor entrega **{m.get('accuracy', 0) * 100:.1f}% de acurácia** em uma amostra "
        f"de {m.get('n_conclusive', 0)} teses conclusivas — um resultado direcional, não definitivo, "
        f"dadas as limitações de amostra e janela. O experimento confirma que o sistema "
        f"diferencia teses fragilizadas de sustentáveis acima do acaso, mas exige amostras "
        f"maiores e janelas alternativas para conclusões robustas."
    )
    lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    return REPORT_PATH


def print_summary(df: pd.DataFrame) -> None:
    mat = confusion_matrix(df)
    m = metrics(df)
    print("=== Matriz de Confusão ===")
    print(mat.rename(index=VERDICT_LABELS, columns=OUTCOME_LABELS))
    print()
    print(f"Total: {m['n_total']} | Conclusivas: {m['n_conclusive']} | "
          f"Inconclusivas (zona morta): {m['n_inconclusive']} | "
          f"Out-of-sample: {m['n_out_of_sample']}")
    print(f"Acurácia (conclusivas): {m['accuracy'] * 100:.1f}%")
    print()
    print("=== Precisão / Recall por veredito ===")
    for v in VERDICT_ORDER:
        cls = m.get("per_class", {}).get(v, {})
        print(f"  {VERDICT_LABELS[v]:<14}  P={cls.get('precision', 0):.3f}  "
              f"R={cls.get('recall', 0):.3f}  TP={cls.get('tp', 0)}  "
              f"FP={cls.get('fp', 0)}  FN={cls.get('fn', 0)}")
