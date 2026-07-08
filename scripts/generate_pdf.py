"""Generates the project documentation as a PDF (docs/documentation.pdf).

Usage:  python scripts/generate_pdf.py    (requires: pip install .[docs])
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parents[1] / "docs" / "documentation.pdf"

styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1x", parent=styles["Heading1"], spaceBefore=18, spaceAfter=8)
H2 = ParagraphStyle("H2x", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6)
BODY = ParagraphStyle("Bodyx", parent=styles["BodyText"], fontSize=10.5, leading=15,
                      spaceAfter=6)
CODE = ParagraphStyle("Codex", parent=styles["Code"], fontSize=9, leading=12,
                      backColor=colors.whitesmoke, borderPadding=6, spaceAfter=8)
NOTE = ParagraphStyle("Notex", parent=BODY, backColor=colors.Color(1, 0.96, 0.88),
                      borderPadding=8, spaceBefore=6, spaceAfter=10)


def p(text: str, style=BODY) -> Paragraph:
    return Paragraph(text, style)


def bullets(items: list[str]) -> ListFlowable:
    return ListFlowable(
        [ListItem(p(i), leftIndent=6) for i in items],
        bulletType="bullet", start="•", spaceAfter=8,
    )


def build() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT), pagesize=A4,
        leftMargin=2.2 * cm, rightMargin=2.2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title="AI Stock Research Assistant – Documentation",
        author="AI Stock Research Assistant",
    )
    e: list = []

    # Title
    e.append(Paragraph("AI Stock Research Assistant", styles["Title"]))
    e.append(p(f"<i>Technical documentation – as of {dt.date.today().isoformat()}</i>"))
    e.append(Spacer(1, 6))
    e.append(p(
        "<b>Important note:</b> This tool and all reports generated with it are "
        "provided for informational and educational purposes only. They do "
        "<b>not constitute investment advice</b> or a recommendation to buy or "
        "sell any security. AI-generated analyses can contain errors. Target "
        "audience of this documentation: technically minded retail investors.",
        NOTE))

    # 1. What does the tool do?
    e.append(p("1. What does the tool do?", H1))
    e.append(p(
        "The AI Stock Research Assistant is a command-line tool (with an "
        "optional local web UI) that turns a single ticker symbol (e.g. "
        "<b>AAPL</b>) into a structured research memo in the style of an "
        "analyst report. To do so, it automatically collects price data, "
        "fundamental metrics, the macroeconomic context and recent company "
        "news, and has the data interpreted by a large language model "
        "(Anthropic Claude)."))
    e.append(p("Typical invocations:", BODY))
    e.append(p(
        "research AAPL<br/>"
        "research AAPL --deep<br/>"
        "research --compare AAPL MSFT<br/>"
        "research AAPL --offline", CODE))
    e.append(p(
        "Per ticker, two files are written to the <b>reports/</b> directory: a "
        "Markdown memo (for humans) and a JSON file with all raw metrics (for "
        "machines and your own analyses)."))

    # 2. Pipeline
    e.append(p("2. How the pipeline works – step by step", H1))
    e.append(p("Step 1: Data acquisition", H2))
    e.append(bullets([
        "<b>Price data &amp; fundamentals (yfinance):</b> current price, market "
        "capitalization, valuation metrics (P/E, P/B, P/S, EV/EBITDA, PEG), "
        "margins (gross, operating, net), growth (revenue, earnings), leverage "
        "(debt/equity, current ratio), free cash flow, dividend yield, beta and "
        "the 52-week range. In addition, the 1-year return and annualized "
        "volatility are computed from one year of price history.",
        "<b>Macro context (FRED API):</b> 10-year US Treasury yield (DGS10), "
        "US federal funds rate (FEDFUNDS), CPI inflation year over year "
        "(CPIAUCSL) and the US unemployment rate (UNRATE).",
        "<b>News (yfinance news feed):</b> the most recent headlines about the "
        "company with source and timestamp.",
    ]))
    e.append(p(
        "All data is combined into a <i>DataBundle</i> – the single source of "
        "data for all subsequent steps. In offline mode (--offline) a recorded "
        "snapshot is loaded instead."))
    e.append(p("Steps 2 to 5: Four-stage AI analysis", H2))
    e.append(bullets([
        "<b>Fundamental analysis:</b> interpretation of valuation, growth, "
        "margins and leverage.",
        "<b>Qualitative assessment:</b> possible moat, key risks, industry "
        "landscape – taking the macro environment and headlines into account.",
        "<b>Bull case / bear case:</b> three (standard) or five (--deep) "
        "arguments each for the positive and the negative scenario.",
        "<b>Research memo:</b> an executive summary condensing all previous "
        "stages – deliberately without a price target and without a recommendation.",
    ]))
    e.append(p(
        "Each stage is a separate API call to the Anthropic Messages API "
        "(default model: <b>claude-sonnet-5</b>, configurable via the "
        "STOCK_RESEARCH_MODEL environment variable). The memo stage receives "
        "the results of the previous stages as context."))
    e.append(p("Step 6: Report generation", H2))
    e.append(p(
        "The report generator assembles the Markdown memo. Importantly, the "
        "<b>key-metrics table is not produced by the language model</b> – it is "
        "rendered deterministically from the raw data. The model only provides "
        "the interpretation, so the table is guaranteed to be consistent with "
        "the raw data. Every report starts with a clear disclaimer."))

    # 3. Data sources
    e.append(p("3. Data sources in detail", H1))
    table = Table(
        [
            ["Source", "Content", "Access"],
            ["Yahoo Finance\n(via yfinance)", "prices, fundamentals, news",
             "no key (unofficial API)"],
            ["FRED\n(St. Louis Fed)", "rates, inflation,\nlabor market",
             "free API key\n(FRED_API_KEY)"],
            ["Anthropic API", "AI analysis\n(claude-sonnet-5)",
             "API key (ANTHROPIC_API_KEY)"],
        ],
        colWidths=[4.2 * cm, 6.0 * cm, 5.6 * cm],
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.15, 0.25, 0.45)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    e.append(table)
    e.append(Spacer(1, 8))
    e.append(p(
        "All keys are loaded exclusively from environment variables or a local "
        ".env file (python-dotenv). The repository only contains a .env.example "
        "with placeholders; the real .env is excluded via .gitignore."))

    # 4. Prompt structure
    e.append(p("4. How are the prompts structured?", H1))
    e.append(p(
        "Every API call consists of a <b>system prompt</b> and a <b>data "
        "prompt</b>. The system prompt defines the role (sober equity analyst) "
        "and the safety rules:"))
    e.append(bullets([
        "Use only the data provided in the prompt – never invent numbers.",
        "Copy metrics exactly (decimal-point notation, e.g. 32.5); state "
        "missing values as missing instead of estimating them.",
        "No price targets, no buy/sell recommendations, no investment advice.",
        "Factual, structured Markdown.",
    ]))
    e.append(p(
        "The data prompt contains the complete raw data in three forms: as a "
        "formatted metrics table, as a macro/news summary and additionally as a "
        "JSON block – followed by the concrete task of the respective pipeline "
        "stage (including desired length and structure). The memo stage "
        "additionally receives the texts of the three previous stages."))
    e.append(p(
        "This redundancy (table + JSON) reduces transposition errors; the "
        "strict decimal-point requirement makes the outputs machine-checkable "
        "(see section 6, hallucination check)."))

    # 5. Reading a report
    e.append(PageBreak())
    e.append(p("5. How to read a report", H1))
    e.append(bullets([
        "<b>Header:</b> creation time, analyst used (Claude model or offline "
        "template), data timestamp and data source (live/fixture).",
        "<b>Disclaimer:</b> deliberately at the very top – please take it seriously.",
        "<b>Executive summary:</b> the core thesis in a few sentences. A good "
        "starting point, but no substitute for the details.",
        "<b>Key metrics:</b> generated deterministically from the raw data. "
        "“n/a” means Yahoo Finance does not provide this value for "
        "the company (common for banks, e.g. debt/equity).",
        "<b>Macro environment:</b> the interest-rate and inflation context that "
        "frames valuations (especially P/E multiples).",
        "<b>Fundamental analysis / qualitative assessment:</b> the AI "
        "interpretation. Statements are judgments, not facts.",
        "<b>Bull/bear case:</b> read both sides! The structure enforces a "
        "balanced view.",
        "<b>Recent news:</b> headlines as context – check details in the "
        "original source.",
        "<b>Data sources &amp; methodology:</b> where the data comes from and "
        "how the report was produced.",
    ]))
    e.append(p(
        "Rule of thumb: the metrics table is “hard” (straight from "
        "the data), the prose is “soft” (AI interpretation). If you "
        "reuse a number from the prose, verify it against the table or the "
        "JSON file."))

    # 6. Quality assurance
    e.append(p("6. Quality assurance: tests and eval suite", H1))
    e.append(p(
        "Besides classic unit tests (data parsing, formatting, CLI), the "
        "project ships an eval suite that analyzes ten well-known tickers and "
        "automatically checks every generated report:"))
    e.append(bullets([
        "<b>(a) Mandatory sections:</b> executive summary, key metrics, macro "
        "environment, fundamental analysis, qualitative assessment, bull/bear "
        "case, news, methodology and the disclaimer must be present.",
        "<b>(b) Metric consistency:</b> every numeric value of the key-metrics "
        "table is checked against the raw data (relative tolerance 0.5 % plus "
        "rounding tolerance).",
        "<b>(c) Hallucination check:</b> every number in the AI prose must be "
        "traceable to a raw-data value (or a common scaling such as percent or "
        "billions) within a relative tolerance of 5 %. Unsubstantiated numbers "
        "fail the check.",
    ]))
    e.append(p(
        "The results are written to evals/results.json; the pass rate is "
        "documented in the README. The suite runs either offline (recorded "
        "snapshots + rule-based analyst, e.g. in CI) or with --live against "
        "real data and the real Anthropic API."))

    # 7. Known limits
    e.append(p("7. Known limits", H1))
    e.append(bullets([
        "<b>Not investment advice</b> and not audited financial analysis.",
        "<b>Data quality:</b> yfinance uses unofficial Yahoo Finance endpoints; "
        "values can be missing, delayed or wrong. The news-feed format changes "
        "occasionally.",
        "<b>LLM limits:</b> the hallucination check validates numbers, not the "
        "logic of the argument. Misinterpretations remain possible.",
        "<b>US focus:</b> the macro series come from US sources (FRED); for "
        "non-US stocks the macro context is only partially meaningful.",
        "<b>Snapshot in time:</b> a report reflects the data at fetch time – "
        "it goes stale quickly.",
        "<b>No backtest:</b> the eval suite measures report quality and data "
        "consistency, not the predictive power of the analyses.",
        "<b>Costs:</b> every analysis incurs API costs (four calls per ticker, "
        "more in --compare mode).",
    ]))

    doc.build(e)
    print(f"PDF written: {OUT}")


if __name__ == "__main__":
    build()
