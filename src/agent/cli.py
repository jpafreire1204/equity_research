"""Command-line interface for the equity research agent."""

from __future__ import annotations

import argparse
import sys

from src.agent.agent import EquityResearchAgent
from src.agent.company_names import COMPANY_NAMES


def main(argv: list[str] | None = None) -> None:
    """Entry point for ``python -m src.agent.cli``."""
    parser = argparse.ArgumentParser(
        description="AI Equity Research Agent — generate investment dossiers"
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        required=True,
        help='Space-separated tickers or "all" for the full universe',
    )
    parser.add_argument(
        "--profile",
        default="base",
        choices=["conservative", "base", "aggressive"],
        help="Investor profile (default: base)",
    )
    parser.add_argument(
        "--output",
        default="txt",
        choices=["txt", "pdf"],
        help="Output format (default: txt)",
    )
    args = parser.parse_args(argv)

    tickers: list[str] = (
        list(COMPANY_NAMES.keys()) if args.tickers == ["all"] else args.tickers
    )

    agent = EquityResearchAgent(profile=args.profile)
    dossier = agent.generate_dossier(tickers)

    if args.output == "pdf":
        _export_pdf(dossier, agent.profile)
    else:
        print(dossier)


def _export_pdf(dossier: str, profile: str) -> None:
    """Export the dossier text to a PDF using reportlab."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas
    except ImportError:
        print("[ERROR] reportlab not installed. Run: pip install reportlab")
        print("Falling back to txt output.\n")
        print(dossier)
        return

    import datetime as dt
    from pathlib import Path

    out_dir = Path(__file__).resolve().parents[2] / "data" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    pdf_path = out_dir / f"dossier_{today}_{profile}.pdf"

    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4
    margin = 2 * cm
    y = height - margin
    line_height = 12

    c.setFont("Courier", 8)
    for line in dossier.splitlines():
        if y < margin:
            c.showPage()
            c.setFont("Courier", 8)
            y = height - margin
        c.drawString(margin, y, line)
        y -= line_height

    c.save()
    print(f"PDF saved: {pdf_path}")


if __name__ == "__main__":
    main()
