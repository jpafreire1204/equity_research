"""Data contracts for the Thesis Auditor module."""
from dataclasses import dataclass, field
from typing import Literal

DriverKey = Literal[
    "fundamentals_quality",
    "valuation_attractive",
    "momentum_positive",
    "sentiment_supportive",
    "macro_tailwind",
]


@dataclass
class ThesisInput:
    ticker: str
    direction: Literal["bullish", "bearish"]
    drivers: list[DriverKey]
    convictions: dict[DriverKey, int]


@dataclass
class Tension:
    driver: DriverKey
    severity: Literal["low", "medium", "high"]
    finding: str
    evidence: dict


@dataclass
class AuditResult:
    ticker: str
    consistency_score: float
    verdict: Literal["sustentavel", "sustentavel_com_ressalvas", "fragilizada"]
    conviction_gap_score: float
    tensions: list[Tension] = field(default_factory=list)
    supporting_evidence: list[str] = field(default_factory=list)
    auditado_em: str = ""
