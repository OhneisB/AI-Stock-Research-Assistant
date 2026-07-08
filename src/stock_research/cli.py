"""Command-line interface.

Examples:
    research AAPL                 # standard analysis
    research AAPL --deep          # more detailed analysis
    research --compare AAPL MSFT  # comparison report
    research AAPL --offline       # fixture data + offline analyst (no keys)
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
        description="AI-powered stock research assistant "
                    "(not investment advice - see the disclaimer in every report).",
    )
    parser.add_argument("tickers", nargs="+", metavar="TICKER",
                        help="One or more ticker symbols, e.g. AAPL MSFT")
    parser.add_argument("--deep", action="store_true",
                        help="More detailed analysis (longer sections)")
    parser.add_argument("--compare", action="store_true",
                        help="Comparison report across all given tickers")
    parser.add_argument("--offline", action="store_true",
                        help="Use fixture data and the offline analyst "
                             "(no network, no API keys required)")
    parser.add_argument("--out", default=None, metavar="DIR",
                        help="Target directory for reports (default: reports/)")
    return parser


def _template_compare_text(bundles: list[DataBundle]) -> str:
    lines = ["Rule-based metric comparison (offline mode):", ""]
    for key, label in [("trailing_pe", "P/E (trailing)"),
                       ("revenue_growth", "Revenue growth"),
                       ("profit_margin", "Net margin"),
                       ("debt_to_equity", "Debt/equity")]:
        vals = []
        for b in bundles:
            v = b.fundamentals.metrics.get(key)
            vals.append(f"{b.fundamentals.ticker}: {'n/a' if v is None else round(v, 2)}")
        lines.append(f"- {label}: " + " | ".join(vals))
    lines.append("")
    lines.append("See the metric tables below for details.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings(reports_dir=args.out)

    if args.compare and len(args.tickers) < 2:
        print("--compare requires at least two tickers.", file=sys.stderr)
        return 2

    if not settings.has_anthropic and not args.offline:
        print("Note: ANTHROPIC_API_KEY is not set - using the rule-based "
              "offline analyst (no LLM).", file=sys.stderr)

    bundles: list[DataBundle] = []
    for ticker in args.tickers:
        print(f"[{ticker.upper()}] Collecting data "
              f"({'fixture' if args.offline else 'live: yfinance + FRED'}) ...")
        try:
            bundles.append(collect(ticker, settings, offline=args.offline))
        except Exception as exc:
            print(f"[{ticker.upper()}] Data fetch failed: {exc}", file=sys.stderr)
            return 1

    exit_code = 0
    for bundle in bundles:
        t = bundle.fundamentals.ticker
        try:
            analyst = make_analyst(settings, bundle, force_template=args.offline)
            print(f"[{t}] Analyzing ({analyst.name}"
                  f"{', deep' if args.deep else ''}) ...")
            result = run_pipeline(bundle, analyst, deep=args.deep)
            md_path, json_path = write_report(bundle, result, settings.reports_dir)
            print(f"[{t}] Report:   {md_path}")
            print(f"[{t}] Raw data: {json_path}")
        except Exception as exc:
            print(f"[{t}] Analysis failed: {exc}", file=sys.stderr)
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
            print(f"[compare] Report: {path}")
        except Exception as exc:
            print(f"[compare] Failed: {exc}", file=sys.stderr)
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
