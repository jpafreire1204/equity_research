"""Historical validation of the Thesis Auditor.

Modules:
    discovery     — Exa-driven retrieval of candidate theses from BR financial media.
    extraction    — Article text → ThesisInput.
    ground_truth  — 6-month forward ticker return vs Ibovespa, ±5% dead zone.
    runner        — Orchestrator: curated theses → audits → comparison table.
    report        — Confusion matrix, per-driver error analysis, markdown report.
"""
