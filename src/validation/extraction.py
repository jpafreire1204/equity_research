"""Convert curated article text into ThesisInput dataclasses.

The actual classification (direction + drivers) happens during human-in-the-loop triage;
this module just packages the curated rows into ThesisInput-compatible records and
preserves the author's original voice in the rationale field.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.auditor.contracts import DriverKey, ThesisInput

DATA_DIR = Path("data/validation")
CURATED_PATH = DATA_DIR / "curated_theses.json"

VALID_DRIVERS: tuple[DriverKey, ...] = (
    "fundamentals_quality",
    "valuation_attractive",
    "momentum_positive",
    "sentiment_supportive",
    "macro_tailwind",
)


def clip_rationale(text: str, max_chars: int = 400) -> str:
    """Trim to ≤max_chars without breaking words, preserving original phrasing."""
    if not text:
        return ""
    t = " ".join(text.split())
    if len(t) <= max_chars:
        return t
    cut = t[:max_chars]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(".,;: ") + "…"


def to_thesis_input(row: dict[str, Any]) -> ThesisInput:
    drivers = [d for d in row.get("drivers", []) if d in VALID_DRIVERS]
    direction = row["direction"]
    if direction not in ("bullish", "bearish"):
        raise ValueError(f"Invalid direction {direction!r} for url={row.get('url')}")
    return ThesisInput(
        ticker=row["ticker"],
        rationale=clip_rationale(row["rationale"]),
        direction=direction,
        drivers=drivers,
    )


def save_curated(rows: list[dict[str, Any]]) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CURATED_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return CURATED_PATH


def load_curated() -> list[dict[str, Any]]:
    if not CURATED_PATH.exists():
        return []
    return json.loads(CURATED_PATH.read_text(encoding="utf-8"))
