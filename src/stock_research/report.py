"""Report generation: Markdown memo + JSON with all raw metrics."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from . import DISCLAIMER, __version__
from .analysis.formatting import macro_summary, metrics_table_markdown, news_summary
from .analysis.pipeline import AnalysisResult
from .data.models import DataBundle

# Mandatory sections of every report - the eval suite checks exactly this list.
REQUIRED_SECTIONS: list[str] = [
    "## Executive Summary",
    "## Key Metrics",
    "## Macro Environment",
    "## Fundamental Analysis",
    "## Qualitative Assessment",
    "### Bull Case",
    "### Bear Case",
    "## Recent News",
    "## Data Sources & Methodology",
]


def render_markdown(bundle: DataBundle, result: AnalysisResult) -> str:
    f = bundle.fundamentals
    created = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    bull_bear = result.sections.get("bull_bear", "")
    if "### Bull Case" not in bull_bear:
        bull_bear = "### Bull Case\n" + bull_bear
    parts = [
        f"# Research Memo: {f.name} ({f.ticker})",
        f"*Created: {created} | Analyst: {result.model} | "
        f"Data as of: {bundle.collected_at or 'n/a'} | Data source: {bundle.data_source} | "
        f"stock-research v{__version__}*",
        DISCLAIMER,
        "## Executive Summary",
        result.sections.get("memo", ""),
        "## Key Metrics",
        metrics_table_markdown(bundle),
        "## Macro Environment",
        macro_summary(bundle),
        "## Fundamental Analysis",
        result.sections.get("fundamental_analysis", ""),
        "## Qualitative Assessment",
        result.sections.get("qualitative_assessment", ""),
        "## Bull Case / Bear Case",
        bull_bear,
        "## Recent News",
        news_summary(bundle),
        "## Data Sources & Methodology",
        "- Price and fundamental data: Yahoo Finance (via yfinance)\n"
        "- Macro data: FRED (Federal Reserve Bank of St. Louis)\n"
        "- News: Yahoo Finance news feed\n"
        "- Analysis: "
        + ("Anthropic API, model " + result.model.removeprefix("claude:")
           if result.mode == "claude"
           else "rule-based offline analyst (no LLM)")
        + "\n- The key-metrics table is generated deterministically from the raw data, "
        "not by the language model.",
    ]
    return "\n\n".join(p for p in parts if p is not None)


def write_report(bundle: DataBundle, result: AnalysisResult,
                 reports_dir: Path) -> tuple[Path, Path]:
    """Writes the Markdown memo and the JSON raw data to reports/."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.date.today().isoformat()
    base = f"{bundle.fundamentals.ticker}_{stamp}"

    md_path = reports_dir / f"{base}.md"
    md_path.write_text(render_markdown(bundle, result), encoding="utf-8")

    json_path = reports_dir / f"{base}.json"
    json_path.write_text(
        json.dumps(
            {
                "ticker": bundle.fundamentals.ticker,
                "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "mode": result.mode,
                "model": result.model,
                "deep": result.deep,
                "raw_data": bundle.to_dict(),
                "sections": result.sections,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return md_path, json_path


def write_comparison(bundles: list[DataBundle], text: str, mode: str,
                     reports_dir: Path) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    tickers = "_vs_".join(b.fundamentals.ticker for b in bundles)
    created = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = [
        f"# Comparison: {' vs. '.join(b.fundamentals.ticker for b in bundles)}",
        f"*Created: {created} | Mode: {mode}*",
        DISCLAIMER,
        "## Comparative Analysis",
        text,
    ]
    for b in bundles:
        parts.append(f"## Key Metrics {b.fundamentals.ticker}")
        parts.append(metrics_table_markdown(b))
    path = reports_dir / f"{tickers}_{dt.date.today().isoformat()}.md"
    path.write_text("\n\n".join(parts), encoding="utf-8")
    return path
