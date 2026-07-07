"""End-to-End-Tests fuer Offline-Pipeline, Report-Generierung und Eval-Checks."""

import json

from stock_research.analysis.formatting import format_metric, metrics_table_markdown
from stock_research.analysis.pipeline import TemplateAnalyst, run_pipeline
from stock_research.evalchecks import (
    check_hallucinations,
    check_metrics_table,
    check_sections,
)
from stock_research.report import REQUIRED_SECTIONS, render_markdown, write_report


def test_format_metric():
    assert format_metric("trailing_pe", None) == "n/a"
    assert format_metric("trailing_pe", 22.5) == "22.50"
    assert format_metric("profit_margin", 0.263) == "26.3 %"
    assert format_metric("market_cap", 3.45e12) == "3.45 Bio. USD"
    assert format_metric("free_cashflow", 1.08e11) == "108.00 Mrd. USD"
    assert format_metric("price", 228.5, "USD") == "228.50 USD"
    assert format_metric("dividend_yield", 0.0044) == "0.44 %"


def test_metrics_table_contains_labels(aapl_bundle):
    table = metrics_table_markdown(aapl_bundle)
    assert "| KGV (trailing) | 34.70 |" in table
    assert "| Nettomarge | 26.3 % |" in table
    assert "Marktkapitalisierung" in table


def test_template_pipeline_and_report(aapl_bundle, tmp_path):
    result = run_pipeline(aapl_bundle, TemplateAnalyst(aapl_bundle))
    assert result.mode == "template"
    assert set(result.sections) == {
        "fundamentalanalyse", "qualitative_einschaetzung", "bull_bear", "memo"
    }

    markdown = render_markdown(aapl_bundle, result)
    for section in REQUIRED_SECTIONS:
        assert section in markdown
    assert "KEINE Anlageberatung" in markdown

    md_path, json_path = write_report(aapl_bundle, result, tmp_path)
    assert md_path.exists() and json_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["ticker"] == "AAPL"
    assert payload["raw_data"]["fundamentals"]["metrics"]["trailing_pe"] == 34.7


def test_eval_checks_pass_for_template_report(aapl_bundle):
    result = run_pipeline(aapl_bundle, TemplateAnalyst(aapl_bundle))
    markdown = render_markdown(aapl_bundle, result)

    ok, missing = check_sections(markdown)
    assert ok, missing

    ok, checks = check_metrics_table(markdown, aapl_bundle)
    assert ok, [c.label for c in checks if not c.ok]
    assert len(checks) > 10

    halluc = check_hallucinations(result, aapl_bundle)
    assert halluc.ok, halluc.unmatched
    assert halluc.numbers_checked > 5


def test_eval_checks_detect_problems(aapl_bundle):
    result = run_pipeline(aapl_bundle, TemplateAnalyst(aapl_bundle))

    # fehlende Sektion wird erkannt
    markdown = render_markdown(aapl_bundle, result).replace("## Fundamentalanalyse", "## Kaputt")
    ok, missing = check_sections(markdown)
    assert not ok and "## Fundamentalanalyse" in missing

    # halluzinierte Zahl wird erkannt
    result.sections["memo"] += " Das KGV liegt bei 999.99."
    halluc = check_hallucinations(result, aapl_bundle)
    assert not halluc.ok and 999.99 in halluc.unmatched
