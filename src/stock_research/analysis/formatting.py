"""Deterministic formatting of metrics for reports and prompts.

The key-metrics table in every report is deliberately NOT produced by the
language model; it is rendered here deterministically from the raw data. The
table is therefore guaranteed to be consistent with the raw data - the
language model only provides the interpretation.

Number format note: decimal point (32.5), so the eval suite can parse numbers
unambiguously.
"""

from __future__ import annotations

from ..data.models import PERCENT_FIELDS, DataBundle

METRIC_LABELS: dict[str, str] = {
    "price": "Price",
    "market_cap": "Market cap",
    "trailing_pe": "P/E (trailing)",
    "forward_pe": "P/E (forward)",
    "price_to_book": "Price-to-book (P/B)",
    "price_to_sales": "Price-to-sales (P/S)",
    "ev_to_ebitda": "EV/EBITDA",
    "peg_ratio": "PEG ratio",
    "profit_margin": "Net margin",
    "operating_margin": "Operating margin",
    "gross_margin": "Gross margin",
    "revenue_growth": "Revenue growth (YoY)",
    "earnings_growth": "Earnings growth (YoY)",
    "return_on_equity": "Return on equity (ROE)",
    "debt_to_equity": "Debt/equity",
    "current_ratio": "Current ratio",
    "free_cashflow": "Free cash flow",
    "total_revenue": "Revenue (TTM)",
    "dividend_yield": "Dividend yield",
    "beta": "Beta",
    "fifty_two_week_high": "52-week high",
    "fifty_two_week_low": "52-week low",
}

LARGE_NUMBER_FIELDS = {"market_cap", "free_cashflow", "total_revenue"}


def format_large_number(value: float, currency: str = "USD") -> str:
    sign = "-" if value < 0 else ""
    v = abs(value)
    for threshold, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if v >= threshold:
            return f"{sign}{v / threshold:.2f}{suffix} {currency}"
    return f"{sign}{v:,.0f} {currency}"


def format_metric(field: str, value: float | None, currency: str = "USD") -> str:
    if value is None:
        return "n/a"
    if field in LARGE_NUMBER_FIELDS:
        return format_large_number(value, currency)
    if field in PERCENT_FIELDS:
        return f"{value * 100:.1f} %"
    if field == "dividend_yield":
        # Depending on the version, yfinance reports the dividend yield either
        # as a fraction (0.005) or already in percent (0.5). Values < 0.5 are
        # interpreted as fractions.
        return f"{value * 100:.2f} %" if value < 0.5 else f"{value:.2f} %"
    if field == "price" or field.startswith("fifty_two"):
        return f"{value:.2f} {currency}"
    return f"{value:.2f}"


def metrics_table_markdown(bundle: DataBundle) -> str:
    """Renders the deterministic key-metrics table as a Markdown table."""
    f = bundle.fundamentals
    lines = ["| Metric | Value |", "|---|---|"]
    for field, label in METRIC_LABELS.items():
        lines.append(f"| {label} | {format_metric(field, f.metrics.get(field), f.currency)} |")
    ps = bundle.price_stats
    if ps.return_1y_pct is not None:
        lines.append(f"| 1-year price change | {ps.return_1y_pct:.1f} % |")
    if ps.volatility_ann_pct is not None:
        lines.append(f"| Volatility (annualized) | {ps.volatility_ann_pct:.1f} % |")
    return "\n".join(lines)


def macro_summary(bundle: DataBundle) -> str:
    m = bundle.macro
    parts = []
    if m.ten_year_treasury_pct is not None:
        parts.append(f"10Y US Treasury yield: {m.ten_year_treasury_pct:.2f} %")
    if m.fed_funds_rate_pct is not None:
        parts.append(f"Fed funds rate: {m.fed_funds_rate_pct:.2f} %")
    if m.cpi_inflation_yoy_pct is not None:
        parts.append(f"CPI inflation (YoY): {m.cpi_inflation_yoy_pct:.2f} %")
    if m.unemployment_rate_pct is not None:
        parts.append(f"US unemployment rate: {m.unemployment_rate_pct:.2f} %")
    return " | ".join(parts) if parts else "No macro data available."


def news_summary(bundle: DataBundle, limit: int = 8) -> str:
    if not bundle.news:
        return "No recent news available."
    lines = []
    for n in bundle.news[:limit]:
        pub = f" ({n.publisher})" if n.publisher else ""
        lines.append(f"- {n.title}{pub}")
    return "\n".join(lines)
