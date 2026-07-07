"""Report-Generierung: Markdown-Memo + JSON mit allen Rohkennzahlen."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from . import DISCLAIMER, __version__
from .analysis.formatting import macro_summary, metrics_table_markdown, news_summary
from .analysis.pipeline import AnalysisResult
from .data.models import DataBundle

# Pflicht-Sektionen jedes Reports - die Eval-Suite prueft genau diese Liste.
REQUIRED_SECTIONS: list[str] = [
    "## Executive Summary",
    "## Kennzahlenuebersicht",
    "## Makro-Umfeld",
    "## Fundamentalanalyse",
    "## Qualitative Einschaetzung",
    "### Bull Case",
    "### Bear Case",
    "## Aktuelle News",
    "## Datenquellen & Methodik",
]


def render_markdown(bundle: DataBundle, result: AnalysisResult) -> str:
    f = bundle.fundamentals
    created = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    bull_bear = result.sections.get("bull_bear", "")
    if "### Bull Case" not in bull_bear:
        bull_bear = "### Bull Case\n" + bull_bear
    parts = [
        f"# Research-Memo: {f.name} ({f.ticker})",
        f"*Erstellt: {created} | Analyst: {result.model} | "
        f"Datenstand: {bundle.collected_at or 'n/a'} | Datenquelle: {bundle.data_source} | "
        f"stock-research v{__version__}*",
        DISCLAIMER,
        "## Executive Summary",
        result.sections.get("memo", ""),
        "## Kennzahlenuebersicht",
        metrics_table_markdown(bundle),
        "## Makro-Umfeld",
        macro_summary(bundle),
        "## Fundamentalanalyse",
        result.sections.get("fundamentalanalyse", ""),
        "## Qualitative Einschaetzung",
        result.sections.get("qualitative_einschaetzung", ""),
        "## Bull Case / Bear Case",
        bull_bear,
        "## Aktuelle News",
        news_summary(bundle),
        "## Datenquellen & Methodik",
        "- Kurs- und Fundamentaldaten: Yahoo Finance (via yfinance)\n"
        "- Makro-Daten: FRED (Federal Reserve Bank of St. Louis)\n"
        "- News: Yahoo-Finance-News-Feed\n"
        "- Analyse: "
        + ("Anthropic API, Modell " + result.model.removeprefix("claude:")
           if result.mode == "claude"
           else "regelbasierter Offline-Analyst (kein LLM)")
        + "\n- Die Kennzahlenuebersicht wird deterministisch aus den Rohdaten erzeugt, "
        "nicht vom Sprachmodell.",
    ]
    return "\n\n".join(p for p in parts if p is not None)


def write_report(bundle: DataBundle, result: AnalysisResult,
                 reports_dir: Path) -> tuple[Path, Path]:
    """Schreibt Markdown-Memo und JSON-Rohdaten nach reports/."""
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
        f"# Vergleich: {' vs. '.join(b.fundamentals.ticker for b in bundles)}",
        f"*Erstellt: {created} | Modus: {mode}*",
        DISCLAIMER,
        "## Vergleichsanalyse",
        text,
    ]
    for b in bundles:
        parts.append(f"## Kennzahlen {b.fundamentals.ticker}")
        parts.append(metrics_table_markdown(b))
    path = reports_dir / f"{tickers}_{dt.date.today().isoformat()}.md"
    path.write_text("\n\n".join(parts), encoding="utf-8")
    return path
