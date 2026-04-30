"""Command-line interface for the Thesis Auditor."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from typing import get_args

from src.auditor.audit import audit_thesis
from src.auditor.contracts import DriverKey, ThesisInput

_ALLOWED_DRIVERS = list(get_args(DriverKey))


def main(argv: list[str] | None = None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="Thesis Auditor — audita uma tese de investimento contra os dados do pipeline."
    )
    parser.add_argument("--ticker", required=True, help='Ticker B3 (ex: "ITUB4")')
    parser.add_argument(
        "--direction",
        required=True,
        choices=["bullish", "bearish"],
        help="Direção da tese",
    )
    parser.add_argument(
        "--drivers",
        nargs="+",
        required=True,
        choices=_ALLOWED_DRIVERS,
        help="Drivers que o usuário alega suportar a tese",
    )
    parser.add_argument(
        "--rationale",
        required=True,
        help="Texto livre com a justificativa da tese (PT-BR)",
    )
    args = parser.parse_args(argv)

    thesis = ThesisInput(
        ticker=args.ticker.upper(),
        rationale=args.rationale,
        direction=args.direction,
        drivers=args.drivers,
    )
    result = audit_thesis(thesis)
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
