"""Eval-Suite: analysiert 10 bekannte Ticker und prueft die Reports automatisiert.

Checks pro Ticker (Details in stock_research.evalchecks):
  (a) alle Pflicht-Sektionen + Disclaimer vorhanden
  (b) Kennzahlen im Report stimmen mit den Rohdaten ueberein (Toleranzpruefung)
  (c) keine halluzinierten Zahlen im Analysten-Text

Ausfuehrung:
  python evals/run_evals.py            # Offline: Fixtures + Template-Analyst
  python evals/run_evals.py --live     # Live: yfinance/FRED + Anthropic API
                                       # (benoetigt Netzwerk + API-Keys)

Ergebnis: evals/results.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from stock_research import __version__  # noqa: E402
from stock_research.analysis.pipeline import make_analyst, run_pipeline  # noqa: E402
from stock_research.config import get_settings  # noqa: E402
from stock_research.data.collect import collect  # noqa: E402
from stock_research.evalchecks import (  # noqa: E402
    check_hallucinations,
    check_metrics_table,
    check_sections,
)
from stock_research.report import render_markdown, write_report  # noqa: E402

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "JNJ", "XOM"]
OUTPUT_DIR = ROOT / "evals" / "output"
RESULTS_PATH = ROOT / "evals" / "results.json"


def evaluate_ticker(ticker: str, live: bool, deep: bool) -> dict:
    settings = get_settings(reports_dir=OUTPUT_DIR)
    entry: dict = {"ticker": ticker}
    try:
        bundle = collect(ticker, settings, offline=not live)
        analyst = make_analyst(settings, bundle, force_template=not live)
        result = run_pipeline(bundle, analyst, deep=deep)
        markdown = render_markdown(bundle, result)
        write_report(bundle, result, OUTPUT_DIR)

        sections_ok, missing = check_sections(markdown)
        metrics_ok, metric_checks = check_metrics_table(markdown, bundle)
        halluc = check_hallucinations(result, bundle)

        entry.update({
            "mode": result.mode,
            "model": result.model,
            "checks": {
                "sections": {"ok": sections_ok, "missing": missing},
                "metrics_table": {
                    "ok": metrics_ok,
                    "values_checked": len(metric_checks),
                    "mismatches": [
                        {"label": c.label, "report_value": c.report_value}
                        for c in metric_checks if not c.ok
                    ],
                },
                "hallucinations": {
                    "ok": halluc.ok,
                    "numbers_checked": halluc.numbers_checked,
                    "unmatched": halluc.unmatched,
                },
            },
        })
        entry["passed"] = sections_ok and metrics_ok and halluc.ok
    except Exception as exc:  # Fehler zaehlen als Fail, brechen die Suite aber nicht ab
        entry["error"] = f"{type(exc).__name__}: {exc}"
        entry["passed"] = False
    return entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true",
                        help="Live-Daten (yfinance/FRED) und Anthropic API verwenden")
    parser.add_argument("--deep", action="store_true", help="Deep-Modus testen")
    args = parser.parse_args(argv)

    settings = get_settings()
    if args.live and not settings.has_anthropic:
        print("--live benoetigt ANTHROPIC_API_KEY.", file=sys.stderr)
        return 2

    results = []
    for ticker in TICKERS:
        print(f"[eval] {ticker} ...", flush=True)
        results.append(evaluate_ticker(ticker, live=args.live, deep=args.deep))

    passed = sum(1 for r in results if r["passed"])
    summary = {
        "run_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "version": __version__,
        "mode": "live (yfinance/FRED + Anthropic API)" if args.live
                else "offline (Fixtures + regelbasierter Template-Analyst)",
        "note": (None if args.live else
                 "Dieser Lauf verwendet aufgezeichnete Daten-Snapshots und den "
                 "deterministischen Offline-Analysten. Er validiert die komplette "
                 "Pipeline-Mechanik (Sektionen, Kennzahlen-Konsistenz, Zahlen-Herkunft). "
                 "Fuer einen Lauf gegen die echte Anthropic API: --live mit gesetzten Keys."),
        "tickers": len(results),
        "passed": passed,
        "pass_rate": round(passed / len(results) * 100, 1),
        "checks_definition": {
            "sections": "Alle Pflicht-Sektionen und der Disclaimer sind im Markdown enthalten.",
            "metrics_table": "Zahlwerte der Kennzahlenuebersicht stimmen mit den Rohdaten "
                             "ueberein (relative Toleranz 0.5 % + Rundungstoleranz).",
            "hallucinations": "Jede Zahl im Analysten-Text ist auf einen Rohdatenwert "
                              "zurueckfuehrbar (relative Toleranz 5 %).",
        },
        "results": results,
    }
    RESULTS_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False),
                            encoding="utf-8")

    print(f"\nErgebnis: {passed}/{len(results)} Ticker bestanden "
          f"({summary['pass_rate']} %) -> {RESULTS_PATH}")
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        detail = r.get("error", "")
        print(f"  [{status}] {r['ticker']} {detail}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
