"""Eval suite: analyzes 10 well-known tickers and checks the reports automatically.

Checks per ticker (details in stock_research.evalchecks):
  (a) all mandatory sections + disclaimer present
  (b) metrics in the report match the raw data (tolerance check)
  (c) no hallucinated numbers in the analyst text

Usage:
  python evals/run_evals.py            # offline: fixtures + template analyst
  python evals/run_evals.py --live     # live: yfinance/FRED + Anthropic API
                                       # (requires network + API keys)

Result: evals/results.json
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
    except Exception as exc:  # errors count as fail but do not abort the suite
        entry["error"] = f"{type(exc).__name__}: {exc}"
        entry["passed"] = False
    return entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true",
                        help="Use live data (yfinance/FRED) and the Anthropic API")
    parser.add_argument("--deep", action="store_true", help="Test deep mode")
    args = parser.parse_args(argv)

    settings = get_settings()
    if args.live and not settings.has_anthropic:
        print("--live requires ANTHROPIC_API_KEY.", file=sys.stderr)
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
                else "offline (fixtures + rule-based template analyst)",
        "note": (None if args.live else
                 "This run uses recorded data snapshots and the deterministic "
                 "offline analyst. It validates the complete pipeline mechanics "
                 "(sections, metric consistency, number provenance). For a run "
                 "against the real Anthropic API: --live with keys configured."),
        "tickers": len(results),
        "passed": passed,
        "pass_rate": round(passed / len(results) * 100, 1),
        "checks_definition": {
            "sections": "All mandatory sections and the disclaimer are present in the Markdown.",
            "metrics_table": "Numeric values of the key-metrics table match the raw data "
                             "(relative tolerance 0.5 % + rounding tolerance).",
            "hallucinations": "Every number in the analyst text can be traced back to a "
                              "raw-data value (relative tolerance 5 %).",
        },
        "results": results,
    }
    RESULTS_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False),
                            encoding="utf-8")

    print(f"\nResult: {passed}/{len(results)} tickers passed "
          f"({summary['pass_rate']} %) -> {RESULTS_PATH}")
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        detail = r.get("error", "")
        print(f"  [{status}] {r['ticker']} {detail}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
