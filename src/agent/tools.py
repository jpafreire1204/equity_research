"""
Six research tools the agent can call to gather data for the investment dossier.

Each tool reads from processed parquets and returns a plain dict.
All tools have docstrings, type hints, and raise ValueError on bad input.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


def _to_list(val) -> list[str]:
    """Coerce numpy arrays, strings, or lists into a plain Python list of strings."""
    if val is None:
        return []
    if hasattr(val, "tolist"):  # numpy array
        return [str(x) for x in val.tolist()]
    if isinstance(val, list):
        return [str(x) for x in val]
    if isinstance(val, str) and val.strip():
        # "lucro(10), dividendo(6)" → ["lucro", "dividendo"]
        return [part.split("(")[0].strip() for part in val.split(",") if part.strip()]
    return []


# ── Tool 1 ─────────────────────────────────────────────────────────────────

def get_kpis(ticker: str, year: int = 2024) -> dict:
    """Return all KPIs for *ticker* in *year* from kpis_wide.parquet.

    Raises ``ValueError`` when ticker/year combination is not found.
    """
    df = pd.read_parquet(DATA_DIR / "kpis_wide.parquet")
    row = df[(df["ticker"] == ticker) & (df["year"] == year)]
    if row.empty:
        raise ValueError(f"No KPI data for {ticker} in {year}")
    rec = row.iloc[0].to_dict()
    # Convert numpy types to native Python for clean serialisation
    return {k: (v.item() if hasattr(v, "item") else v) for k, v in rec.items()}


# ── Tool 2 ─────────────────────────────────────────────────────────────────

def get_price_history(ticker: str, window_days: int = 252) -> dict:
    """Return price summary for *ticker* over the last *window_days* trading days.

    Keys: current_price, price_52w_high, price_52w_low,
          volatility_annualized, momentum_12m, max_drawdown.
    """
    df = pd.read_parquet(DATA_DIR / "prices_daily.parquet")
    t = df[df["ticker"] == ticker].sort_values("date")
    if t.empty:
        raise ValueError(f"No price data for {ticker}")

    t = t.tail(window_days)
    current = t["close"].iloc[-1]
    high = t["close"].max()
    low = t["close"].min()
    vol = t["daily_return"].std() * np.sqrt(252)
    mom = (current / t["close"].iloc[0]) - 1

    cum = (1 + t["daily_return"].fillna(0)).cumprod()
    running_max = cum.cummax()
    dd = ((cum - running_max) / running_max).min()

    return {
        "current_price": round(float(current), 2),
        "price_52w_high": round(float(high), 2),
        "price_52w_low": round(float(low), 2),
        "volatility_annualized": round(float(vol), 4),
        "momentum_12m": round(float(mom), 4),
        "max_drawdown": round(float(dd), 4),
    }


# ── Tool 3 ─────────────────────────────────────────────────────────────────

def get_macro_snapshot() -> dict:
    """Return latest macro indicators.

    Tries the BCB PTAX/Selic API first; falls back to macro_monthly.parquet.
    Keys: selic_current, ipca_last_12m, usdbrl_current.
    """
    df = pd.read_parquet(DATA_DIR / "macro_monthly.parquet")
    last = df.sort_values("date").iloc[-1]

    selic = float(last["selic_daily"])
    ipca_12m = float(df.tail(12)["ipca_monthly"].sum())
    usdbrl = float(last["usdbrl"])

    # Attempt live Selic from BCB API (código 11 — Selic target meta)
    try:
        import requests

        url = (
            "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1"
            "?formato=json"
        )
        resp = requests.get(url, timeout=5)
        if resp.ok:
            data = resp.json()
            if data:
                selic = float(data[-1]["valor"]) / 100
    except Exception:
        pass  # keep parquet value

    return {
        "selic_current": round(selic, 4),
        "ipca_last_12m": round(ipca_12m, 2),
        "usdbrl_current": round(usdbrl, 4),
    }


# ── Tool 4 ─────────────────────────────────────────────────────────────────

def get_sentiment(ticker: str) -> dict:
    """Return NLP sentiment data for *ticker*.

    Keys: textual_index, sentiment_label, top_positive_keywords,
          top_negative_keywords, text_count.
    """
    sent = pd.read_parquet(DATA_DIR / "sentiment_scores.parquet")
    text = pd.read_parquet(DATA_DIR / "textual_index.parquet")

    s_row = sent[sent["ticker"] == ticker]
    t_row = text[text["ticker"] == ticker]
    if s_row.empty and t_row.empty:
        raise ValueError(f"No sentiment data for {ticker}")

    result: dict = {}
    if not t_row.empty:
        r = t_row.iloc[0]
        result["textual_index"] = round(float(r["textual_index"]), 1)
        result["sentiment_label"] = str(r["sentiment_label"])
        # key_positives / key_risks may be numpy arrays, lists, or strings
        result["top_positive_keywords"] = _to_list(r.get("key_positives"))
        result["top_negative_keywords"] = _to_list(r.get("key_risks"))
    if not s_row.empty:
        r = s_row.iloc[0]
        result["text_count"] = int(r["text_count"])
        # Fall back to sentiment_scores string format if textual_index was empty
        if not result.get("top_positive_keywords"):
            result["top_positive_keywords"] = _to_list(r.get("top_positive_keywords"))
        if not result.get("top_negative_keywords"):
            result["top_negative_keywords"] = _to_list(r.get("top_negative_keywords"))
    result.setdefault("text_count", 0)
    result.setdefault("top_positive_keywords", [])
    result.setdefault("top_negative_keywords", [])
    return result


# ── Tool 5 ─────────────────────────────────────────────────────────────────

def get_valuation(ticker: str) -> dict:
    """Return valuation multiples, scenario upside, and recommendation.

    Keys: pl, pvp, ev_ebitda, discount_premium_pl, bull_upside,
          base_upside, bear_upside, recommendation, ultimate_score.
    """
    mult = pd.read_parquet(DATA_DIR / "multiples_2024.parquet")
    scen = pd.read_parquet(DATA_DIR / "scenarios_2024.parquet")
    ult = pd.read_parquet(DATA_DIR / "ultimate_scores_2024.parquet")

    m = mult[mult["ticker"] == ticker]
    u = ult[ult["ticker"] == ticker]
    if m.empty and u.empty:
        raise ValueError(f"No valuation data for {ticker}")

    result: dict = {}
    if not m.empty:
        mr = m.iloc[0]
        for col in ["pl", "pvp", "ev_ebitda", "discount_premium_pl"]:
            v = mr[col]
            result[col] = round(float(v), 2) if pd.notna(v) else None

    # Scenario upside
    for scenario, key in [("bull", "bull_upside"), ("base", "base_upside"), ("bear", "bear_upside")]:
        row = scen[(scen["ticker"] == ticker) & (scen["scenario"] == scenario)]
        if not row.empty:
            v = row.iloc[0]["implied_upside_pct"]
            result[key] = round(float(v), 3) if pd.notna(v) else None
        else:
            result[key] = None

    if not u.empty:
        ur = u.iloc[0]
        result["recommendation"] = str(ur["recommendation"])
        result["ultimate_score"] = round(float(ur["ultimate_score"]), 1)

    return result


# ── Tool 6 ─────────────────────────────────────────────────────────────────

def get_full_score(ticker: str) -> dict:
    """Return the complete scoring breakdown for *ticker*.

    Keys: fundamental_score, textual_index, valuation_score, ultimate_score,
          recommendation, cluster_label, outperform_probability, rank_overall.
    """
    ult = pd.read_parquet(DATA_DIR / "ultimate_scores_2024.parquet")
    clust = pd.read_parquet(DATA_DIR / "clusters_2024.parquet")
    sup = pd.read_parquet(DATA_DIR / "supervised_predictions_2024.parquet")

    u = ult[ult["ticker"] == ticker]
    if u.empty:
        raise ValueError(f"No score data for {ticker}")
    ur = u.iloc[0]

    result = {
        "fundamental_score": round(float(ur["fundamental_score"]), 1),
        "textual_index": round(float(ur["textual_index"]), 1),
        "valuation_score": round(float(ur["valuation_score"]), 1),
        "ultimate_score": round(float(ur["ultimate_score"]), 1),
        "recommendation": str(ur["recommendation"]),
        "rank_overall": int(ur["ultimate_rank"]),
    }

    c = clust[clust["ticker"] == ticker]
    result["cluster_label"] = str(c.iloc[0]["cluster_label"]) if not c.empty else "N/A"

    s = sup[sup["ticker"] == ticker]
    result["outperform_probability"] = (
        round(float(s.iloc[0]["outperform_probability"]), 3)
        if not s.empty
        else None
    )
    return result
