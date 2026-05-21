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
        "--convictions",
        nargs="+",
        required=True,
        help="Convicção 1-10 por driver, formato driver=N (ex: fundamentals_quality=9)",
    )
    args = parser.parse_args(argv)

    convictions: dict[str, int] = {}
    for pair in args.convictions:
        if "=" not in pair:
            parser.error(f"formato inválido para convicção: {pair} (esperado driver=N)")
        k, v = pair.split("=", 1)
        if k not in _ALLOWED_DRIVERS:
            parser.error(f"driver inválido: {k}")
        try:
            iv = int(v)
        except ValueError:
            parser.error(f"convicção não é inteiro: {pair}")
        if not 1 <= iv <= 10:
            parser.error(f"convicção fora do range 1-10: {pair}")
        convictions[k] = iv

    for d in args.drivers:
        if d not in convictions:
            parser.error(f"falta convicção para driver: {d}")

    thesis = ThesisInput(
        ticker=args.ticker.upper(),
        direction=args.direction,
        drivers=args.drivers,
        convictions=convictions,
    )
    result = audit_thesis(thesis)
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
