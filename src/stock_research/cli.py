"""Kommandozeilen-Interface.

Beispiele:
    research AAPL                 # Standard-Analyse
    research AAPL --deep          # ausfuehrlichere Analyse
    research --compare AAPL MSFT  # Vergleichsreport
    research AAPL --offline       # Fixture-Daten + Offline-Analyst (ohne Keys)
"""

from __future__ import annotations

import argparse
import sys

from .analysis import prompts
from .analysis.pipeline import TemplateAnalyst, make_analyst, run_pipeline
from .config import get_settings
from .data.collect import collect
from .data.models import DataBundle
from .report import write_comparison, write_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="research",
        description="KI-gestuetzter Aktien-Research-Assistent "
                    "(keine Anlageberatung - siehe Disclaimer im Report).",
    )
    parser.add_argument("tickers", nargs="+", metavar="TICKER",
                        help="Ein oder mehrere Ticker-Symbole, z. B. AAPL MSFT")
    parser.add_argument("--deep", action="store_true",
                        help="Ausfuehrlichere Analyse (laengere Sektionen)")
    parser.add_argument("--compare", action="store_true",
                        help="Vergleichsreport ueber alle angegebenen Ticker")
    parser.add_argument("--offline", action="store_true",
                        help="Fixture-Daten und Offline-Analyst verwenden "
                             "(kein Netzwerk, keine API-Keys noetig)")
    parser.add_argument("--out", default=None, metavar="DIR",
                        help="Zielverzeichnis fuer Reports (Default: reports/)")
    return parser


def _template_compare_text(bundles: list[DataBundle]) -> str:
    lines = ["Regelbasierter Kennzahlenvergleich (Offline-Modus):", ""]
    for key, label in [("trailing_pe", "KGV (trailing)"),
                       ("revenue_growth", "Umsatzwachstum"),
                       ("profit_margin", "Nettomarge"),
                       ("debt_to_equity", "Debt/Equity")]:
        vals = []
        for b in bundles:
            v = b.fundamentals.metrics.get(key)
            vals.append(f"{b.fundamentals.ticker}: {'n/a' if v is None else round(v, 2)}")
        lines.append(f"- {label}: " + " | ".join(vals))
    lines.append("")
    lines.append("Detailwerte siehe Kennzahlen-Tabellen unten.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings(reports_dir=args.out)

    if args.compare and len(args.tickers) < 2:
        print("--compare benoetigt mindestens zwei Ticker.", file=sys.stderr)
        return 2

    if not settings.has_anthropic and not args.offline:
        print("Hinweis: ANTHROPIC_API_KEY nicht gesetzt - verwende den "
              "regelbasierten Offline-Analysten (kein LLM).", file=sys.stderr)

    bundles: list[DataBundle] = []
    for ticker in args.tickers:
        print(f"[{ticker.upper()}] Sammle Daten "
              f"({'Fixture' if args.offline else 'live: yfinance + FRED'}) ...")
        try:
            bundles.append(collect(ticker, settings, offline=args.offline))
        except Exception as exc:
            print(f"[{ticker.upper()}] Fehler beim Datenabruf: {exc}", file=sys.stderr)
            return 1

    exit_code = 0
    for bundle in bundles:
        t = bundle.fundamentals.ticker
        try:
            analyst = make_analyst(settings, bundle, force_template=args.offline)
            print(f"[{t}] Analysiere ({analyst.name}"
                  f"{', deep' if args.deep else ''}) ...")
            result = run_pipeline(bundle, analyst, deep=args.deep)
            md_path, json_path = write_report(bundle, result, settings.reports_dir)
            print(f"[{t}] Report:   {md_path}")
            print(f"[{t}] Rohdaten: {json_path}")
        except Exception as exc:
            print(f"[{t}] Fehler bei der Analyse: {exc}", file=sys.stderr)
            exit_code = 1

    if args.compare and len(bundles) >= 2:
        try:
            if args.offline or not settings.has_anthropic:
                text, mode = _template_compare_text(bundles), "template"
            else:
                from .analysis.pipeline import ClaudeAnalyst
                text = ClaudeAnalyst(settings).complete(prompts.compare_prompt(bundles))
                mode = f"claude ({settings.model})"
            path = write_comparison(bundles, text, mode, settings.reports_dir)
            print(f"[Vergleich] Report: {path}")
        except Exception as exc:
            print(f"[Vergleich] Fehler: {exc}", file=sys.stderr)
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
