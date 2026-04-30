"""Evidence collector — wraps the 6 agent tools per driver."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.agent.tools import (
    get_kpis,
    get_macro_snapshot,
    get_price_history,
    get_sentiment,
    get_valuation,
)
from src.auditor.contracts import DriverKey

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        return {"error": str(e)}


def _fundamentals(ticker: str) -> dict:
    cur = _safe(get_kpis, ticker, year=2024)
    prev = _safe(get_kpis, ticker, year=2023)
    if "error" in cur:
        return cur
    keys = ["roe", "net_margin", "debt_to_equity", "current_ratio", "revenue_cagr"]
    out = {f"{k}_2024": cur.get(k) for k in keys}
    if "error" not in prev:
        out.update({f"{k}_2023": prev.get(k) for k in keys})
    return out


def _valuation(ticker: str) -> dict:
    v = _safe(get_valuation, ticker)
    if "error" in v:
        return v
    dpp = v.get("discount_premium_pl")
    return {
        "pe_ratio": v.get("pl"),
        "pvp": v.get("pvp"),
        "ev_ebitda": v.get("ev_ebitda"),
        "discount_premium_pl": dpp,
        "discount_vs_sector": (-dpp) if dpp is not None else None,
    }


def _momentum(ticker: str) -> dict:
    p = _safe(get_price_history, ticker, window_days=252)
    if "error" in p:
        return p
    return {
        "momentum_6m": None,
        "momentum_12m": p.get("momentum_12m"),
        "max_drawdown": p.get("max_drawdown"),
        "current_price": p.get("current_price"),
    } | _momentum_6m_from_kpis(ticker)


def _momentum_6m_from_kpis(ticker: str) -> dict:
    k = _safe(get_kpis, ticker, year=2024)
    if "error" in k:
        return {}
    return {"momentum_6m": k.get("momentum_6m")}


def _sentiment(ticker: str) -> dict:
    s = _safe(get_sentiment, ticker)
    if "error" in s:
        return s
    return {
        "textual_index": s.get("textual_index"),
        "sentiment_label": s.get("sentiment_label"),
        "top_positive_keywords": s.get("top_positive_keywords", []),
        "top_negative_keywords": s.get("top_negative_keywords", []),
        "text_count": s.get("text_count"),
    }


def _macro(ticker: str) -> dict:
    m = _safe(get_macro_snapshot)
    out: dict = {}
    if "error" not in m:
        out["current_selic"] = m.get("selic_current")
        out["ipca_last_12m"] = m.get("ipca_last_12m")
        out["usdbrl"] = m.get("usdbrl_current")
    try:
        scen = pd.read_parquet(DATA_DIR / "scenarios_2024.parquet")
        for label in ["bull", "base", "bear"]:
            row = scen[(scen["ticker"] == ticker) & (scen["scenario"] == label)]
            if not row.empty:
                v = row.iloc[0]["implied_upside_pct"]
                out[f"{label}_upside"] = float(v) if pd.notna(v) else None
            else:
                out[f"{label}_upside"] = None
    except Exception as e:
        out["scenarios_error"] = str(e)
    return out


_COLLECTORS = {
    "fundamentals_quality": _fundamentals,
    "valuation_attractive": _valuation,
    "momentum_positive": _momentum,
    "sentiment_supportive": _sentiment,
    "macro_tailwind": _macro,
}


def collect_evidence(ticker: str, drivers: list[DriverKey]) -> dict:
    """For each requested driver, call the relevant agent tools and return structured evidence."""
    out: dict[str, dict] = {}
    for d in drivers:
        fn = _COLLECTORS.get(d)
        if fn is None:
            out[d] = {"error": f"unknown driver: {d}"}
            continue
        try:
            out[d] = fn(ticker)
        except Exception as e:
            out[d] = {"error": str(e)}
    return out
