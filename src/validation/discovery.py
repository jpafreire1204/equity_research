"""Exa-driven discovery of candidate investment theses from Brazilian financial media.

The actual MCP calls (`mcp__exa__web_search_exa`, `mcp__exa__web_fetch_exa`) are driven
from the Claude Code session — this module provides pure helpers: query construction,
result normalization, deduplication, date filtering, and JSON persistence.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

DATA_DIR = Path("data/validation")

# Tickers in the universe → company name used in PT-BR queries.
COMPANY_NAMES: dict[str, str] = {
    "ITUB4":  "Itaú Unibanco",
    "BBDC4":  "Bradesco",
    "BBAS3":  "Banco do Brasil",
    "SANB11": "Santander Brasil",
    "ABCB4":  "Banco ABC Brasil",
    "EGIE3":  "Engie Brasil",
    "EQTL3":  "Equatorial Energia",
    "CPFE3":  "CPFL Energia",
    "TAEE11": "Taesa",
    "CMIG4":  "Cemig",
}

# Domains we trust as opinion/analysis sources.
PREFERRED_DOMAINS = (
    "infomoney.com.br",
    "moneytimes.com.br",
    "seudinheiro.com",
    "valor.globo.com",
    "sunoresearch.com.br",
    "investidor10.com.br",
)

DATE_MIN = date(2022, 1, 1)
DATE_MAX = date(2024, 6, 30)


@dataclass
class Candidate:
    url: str
    ticker: str
    title: str
    published_date: str  # ISO yyyy-mm-dd
    author: str
    full_text: str
    source_query: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "ticker": self.ticker,
            "title": self.title,
            "published_date": self.published_date,
            "author": self.author,
            "full_text": self.full_text,
            "source_query": self.source_query,
        }


def build_queries(ticker: str) -> list[str]:
    """Three queries per ticker, each constrained to the preferred domain set."""
    name = COMPANY_NAMES[ticker]
    site_filter = " OR ".join(f"site:{d}" for d in PREFERRED_DOMAINS)
    return [
        f"Análise fundamentalista {ticker} {name} 2023 tese de investimento ({site_filter})",
        f"Recomendação compra venda {ticker} {name} valuation ({site_filter})",
        f"{ticker} {name} resultado trimestre projeção 2024 ({site_filter})",
    ]


def _parse_date(raw: str | None) -> str | None:
    """Best-effort ISO yyyy-mm-dd extraction from Exa published_date strings."""
    if not raw:
        return None
    s = str(raw).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:len(fmt) + 4] if "%" in fmt else s, fmt).date().isoformat()
        except ValueError:
            continue
    if len(s) >= 10 and s[:4].isdigit() and s[4] == "-":
        return s[:10]
    return None


def in_date_window(iso_date: str | None) -> bool:
    if not iso_date:
        return False
    try:
        d = date.fromisoformat(iso_date)
    except ValueError:
        return False
    return DATE_MIN <= d <= DATE_MAX


def is_paywall_stub(text: str | None) -> bool:
    if not text:
        return True
    t = text.strip()
    if len(t) < 400:
        return True
    needles = ("assine", "para continuar lendo", "conteúdo exclusivo para assinantes",
               "leia também", "subscribe to read")
    low = t.lower()
    paywall_hits = sum(n in low for n in needles)
    return paywall_hits >= 2 and len(t) < 1200


def normalize_search_result(raw: dict, ticker: str, query: str) -> dict | None:
    """Map a raw Exa search-result item to a partial candidate dict (no full_text yet)."""
    url = raw.get("url") or raw.get("id")
    if not url:
        return None
    title = (raw.get("title") or "").strip()
    pub = _parse_date(raw.get("publishedDate") or raw.get("published_date"))
    author = (raw.get("author") or "").strip()
    return {
        "url": url,
        "ticker": ticker,
        "title": title,
        "published_date": pub or "",
        "author": author,
        "full_text": "",
        "source_query": query,
    }


def attach_full_text(candidate: dict, fetched: dict) -> dict:
    """Merge fetched text/metadata into a candidate dict."""
    text = fetched.get("text") or fetched.get("content") or ""
    if not candidate.get("published_date"):
        candidate["published_date"] = _parse_date(
            fetched.get("publishedDate") or fetched.get("published_date")
        ) or ""
    if not candidate.get("author"):
        candidate["author"] = (fetched.get("author") or "").strip()
    candidate["full_text"] = text.strip()
    return candidate


def dedupe(candidates: Iterable[dict]) -> list[dict]:
    """Deduplicate by URL, keep first occurrence."""
    seen: set[str] = set()
    out: list[dict] = []
    for c in candidates:
        u = c.get("url", "")
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(c)
    return out


def filter_candidates(candidates: list[dict]) -> tuple[list[dict], dict[str, int]]:
    """Apply date window + paywall stub filter. Returns (kept, drop_reasons)."""
    kept: list[dict] = []
    drops = {"no_date": 0, "out_of_window": 0, "paywall_stub": 0}
    for c in candidates:
        pub = c.get("published_date") or ""
        if not pub:
            drops["no_date"] += 1
            continue
        if not in_date_window(pub):
            drops["out_of_window"] += 1
            continue
        if is_paywall_stub(c.get("full_text", "")):
            drops["paywall_stub"] += 1
            continue
        kept.append(c)
    return kept, drops


def save_candidates(ticker: str, candidates: list[dict]) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"candidates_{ticker}.json"
    path.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_candidates(ticker: str) -> list[dict]:
    path = DATA_DIR / f"candidates_{ticker}.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))
