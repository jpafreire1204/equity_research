"""
EquityResearchAgent — orchestrator that calls tools, detects risks,
computes profile-adjusted scores, and produces an investment dossier.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from src.agent.company_names import COMPANY_NAMES
from src.agent.dossier_formatter import format_dossier
from src.agent.tools import (
    get_full_score,
    get_kpis,
    get_macro_snapshot,
    get_price_history,
    get_sentiment,
    get_valuation,
)

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "output"

PROFILE_WEIGHTS: dict[str, dict[str, float]] = {
    "conservative": {
        "valuation_score": 0.35,
        "fundamental_score": 0.30,
        "textual_index": 0.25,
        "outperform_probability": 0.10,
    },
    "base": {
        "fundamental_score": 0.35,
        "valuation_score": 0.25,
        "textual_index": 0.25,
        "outperform_probability": 0.15,
    },
    "aggressive": {
        "outperform_probability": 0.35,
        "fundamental_score": 0.30,
        "valuation_score": 0.20,
        "textual_index": 0.15,
    },
}


def _ts() -> str:
    """Return current timestamp for logging."""
    return dt.datetime.now().strftime("%H:%M:%S")


def _safe_call(func, *args, label: str = "", **kwargs) -> dict:
    """Call *func* with logging; return empty dict on failure."""
    print(f"[{_ts()}] Calling {label}...")
    try:
        return func(*args, **kwargs)
    except Exception as e:
        print(f"[WARNING] {label} failed: {e}")
        return {}


def _detect_risk_flags(
    kpis: dict, price: dict, sentiment: dict, valuation: dict, score: dict
) -> list[str]:
    """Generate risk/opportunity flags from collected data."""
    flags: list[str] = []

    debt = kpis.get("debt_to_equity")
    if debt is not None and debt > 3.0:
        flags.append(f"Warning: High leverage (D/E = {debt:.1f})")

    mom = kpis.get("momentum_12m") or price.get("momentum_12m")
    if mom is not None and mom < -0.10:
        flags.append(f"Warning: Negative momentum ({mom:+.1%})")

    ti = sentiment.get("textual_index")
    if ti is not None and ti < 30:
        flags.append(f"Warning: Weak sentiment (index = {ti:.0f})")

    dp_pl = valuation.get("discount_premium_pl")
    if dp_pl is not None and dp_pl > 0.30:
        flags.append(f"Warning: Premium valuation (P/L +{dp_pl:.0%} vs sector)")

    cluster = score.get("cluster_label")
    if cluster == "Quality":
        flags.append("Positive: Quality cluster")

    prob = score.get("outperform_probability")
    if prob is not None and prob > 0.60:
        flags.append(f"Positive: Outperform signal ({prob:.0%})")

    if dp_pl is not None and dp_pl < -0.20:
        flags.append(f"Positive: Discount opportunity (P/L {dp_pl:+.0%} vs sector)")

    return flags if flags else ["No special flags"]


def _profile_adjusted_score(
    score: dict, sentiment: dict, profile: str
) -> float:
    """Compute weighted score according to investor profile."""
    weights = PROFILE_WEIGHTS.get(profile, PROFILE_WEIGHTS["base"])
    components = {
        "fundamental_score": score.get("fundamental_score", 50),
        "valuation_score": score.get("valuation_score", 50),
        "textual_index": sentiment.get("textual_index", 50),
        "outperform_probability": (score.get("outperform_probability") or 0.5) * 100,
    }
    total = sum(components[k] * weights[k] for k in weights)
    return round(total, 1)


class EquityResearchAgent:
    """Autonomous agent that gathers data via tools and produces an investment dossier."""

    def __init__(self, profile: str = "base") -> None:
        if profile not in PROFILE_WEIGHTS:
            raise ValueError(f"Unknown profile '{profile}'. Use: {list(PROFILE_WEIGHTS)}")
        self.profile = profile

    def analyze(self, tickers: list[str]) -> dict:
        """Run the full analysis loop for *tickers*.

        Returns a dict with 'macro', 'tickers' (per-ticker data), and 'metadata'.
        """
        print(f"[{_ts()}] Agent started | profile={self.profile} | tickers={tickers}")

        macro = _safe_call(get_macro_snapshot, label="get_macro_snapshot()")

        ticker_results: list[dict] = []
        for ticker in tickers:
            print(f"\n{'='*50}")
            print(f"[{_ts()}] Analyzing {ticker} — {COMPANY_NAMES.get(ticker, ticker)}")
            print(f"{'='*50}")

            kpis = _safe_call(get_kpis, ticker, 2024, label=f"get_kpis({ticker}, 2024)")
            price = _safe_call(get_price_history, ticker, label=f"get_price_history({ticker})")
            sentiment = _safe_call(get_sentiment, ticker, label=f"get_sentiment({ticker})")
            valuation = _safe_call(get_valuation, ticker, label=f"get_valuation({ticker})")
            score = _safe_call(get_full_score, ticker, label=f"get_full_score({ticker})")

            risk_flags = _detect_risk_flags(kpis, price, sentiment, valuation, score)
            profile_score = _profile_adjusted_score(score, sentiment, self.profile)

            # Profile-based recommendation
            if profile_score >= 65:
                rec = "Buy"
            elif profile_score >= 45:
                rec = "Hold"
            else:
                rec = "Sell"

            ticker_results.append({
                "ticker": ticker,
                "company_name": COMPANY_NAMES.get(ticker, ticker),
                "sector": kpis.get("sector", score.get("sector", "N/A")),
                "kpis": kpis,
                "price": price,
                "sentiment": sentiment,
                "valuation": valuation,
                "score": score,
                "risk_flags": risk_flags,
                "profile_score": profile_score,
                "profile_recommendation": rec,
            })

        print(f"\n[{_ts()}] Agent finished — {len(tickers)} tickers analysed")
        return {
            "macro": macro,
            "tickers": ticker_results,
            "metadata": {
                "profile": self.profile,
                "date": dt.date.today().isoformat(),
                "n_tickers": len(tickers),
            },
        }

    def generate_dossier(self, tickers: list[str]) -> str:
        """Analyze *tickers* and return a formatted text dossier.

        Also saves the dossier to ``data/output/``.
        """
        results = self.analyze(tickers)
        dossier = format_dossier(results)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        today = dt.date.today().isoformat()
        path = OUTPUT_DIR / f"dossier_{today}_{self.profile}.txt"
        path.write_text(dossier, encoding="utf-8")
        print(f"\n[{_ts()}] Dossier saved to {path}")

        return dossier
