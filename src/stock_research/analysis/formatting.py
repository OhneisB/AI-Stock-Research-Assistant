"""Deterministische Formatierung von Kennzahlen fuer Reports und Prompts.

Die Kennzahlenuebersicht in jedem Report wird bewusst NICHT vom Sprachmodell
erzeugt, sondern hier deterministisch aus den Rohdaten gerendert. Damit ist
die Tabelle garantiert konsistent mit den Rohdaten; das Sprachmodell liefert
nur die Interpretation.

Hinweis Zahlformat: Dezimalpunkt (32.5 statt 32,5), damit die Eval-Suite
Zahlen eindeutig parsen kann.
"""

from __future__ import annotations

from ..data.models import PERCENT_FIELDS, DataBundle

METRIC_LABELS: dict[str, str] = {
    "price": "Kurs",
    "market_cap": "Marktkapitalisierung",
    "trailing_pe": "KGV (trailing)",
    "forward_pe": "KGV (forward)",
    "price_to_book": "Kurs-Buchwert-Verhaeltnis (P/B)",
    "price_to_sales": "Kurs-Umsatz-Verhaeltnis (P/S)",
    "ev_to_ebitda": "EV/EBITDA",
    "peg_ratio": "PEG-Ratio",
    "profit_margin": "Nettomarge",
    "operating_margin": "Operative Marge",
    "gross_margin": "Bruttomarge",
    "revenue_growth": "Umsatzwachstum (YoY)",
    "earnings_growth": "Gewinnwachstum (YoY)",
    "return_on_equity": "Eigenkapitalrendite (ROE)",
    "debt_to_equity": "Verschuldungsgrad (Debt/Equity)",
    "current_ratio": "Current Ratio",
    "free_cashflow": "Free Cashflow",
    "total_revenue": "Umsatz (TTM)",
    "dividend_yield": "Dividendenrendite",
    "beta": "Beta",
    "fifty_two_week_high": "52-Wochen-Hoch",
    "fifty_two_week_low": "52-Wochen-Tief",
}

LARGE_NUMBER_FIELDS = {"market_cap", "free_cashflow", "total_revenue"}


def format_large_number(value: float, currency: str = "USD") -> str:
    sign = "-" if value < 0 else ""
    v = abs(value)
    for threshold, suffix in ((1e12, "Bio."), (1e9, "Mrd."), (1e6, "Mio.")):
        if v >= threshold:
            return f"{sign}{v / threshold:.2f} {suffix} {currency}"
    return f"{sign}{v:,.0f} {currency}"


def format_metric(field: str, value: float | None, currency: str = "USD") -> str:
    if value is None:
        return "n/a"
    if field in LARGE_NUMBER_FIELDS:
        return format_large_number(value, currency)
    if field in PERCENT_FIELDS:
        return f"{value * 100:.1f} %"
    if field == "dividend_yield":
        # yfinance liefert die Dividendenrendite je nach Version als Bruch
        # (0.005) oder bereits in Prozent (0.5). Werte < 0.5 interpretieren
        # wir als Bruch.
        return f"{value * 100:.2f} %" if value < 0.5 else f"{value:.2f} %"
    if field == "price" or field.startswith("fifty_two"):
        return f"{value:.2f} {currency}"
    return f"{value:.2f}"


def metrics_table_markdown(bundle: DataBundle) -> str:
    """Rendert die deterministische Kennzahlenuebersicht als Markdown-Tabelle."""
    f = bundle.fundamentals
    lines = ["| Kennzahl | Wert |", "|---|---|"]
    for field, label in METRIC_LABELS.items():
        lines.append(f"| {label} | {format_metric(field, f.metrics.get(field), f.currency)} |")
    ps = bundle.price_stats
    if ps.return_1y_pct is not None:
        lines.append(f"| Kursentwicklung 1 Jahr | {ps.return_1y_pct:.1f} % |")
    if ps.volatility_ann_pct is not None:
        lines.append(f"| Volatilitaet (annualisiert) | {ps.volatility_ann_pct:.1f} % |")
    return "\n".join(lines)


def macro_summary(bundle: DataBundle) -> str:
    m = bundle.macro
    parts = []
    if m.ten_year_treasury_pct is not None:
        parts.append(f"10J-US-Rendite: {m.ten_year_treasury_pct:.2f} %")
    if m.fed_funds_rate_pct is not None:
        parts.append(f"US-Leitzins: {m.fed_funds_rate_pct:.2f} %")
    if m.cpi_inflation_yoy_pct is not None:
        parts.append(f"CPI-Inflation (YoY): {m.cpi_inflation_yoy_pct:.2f} %")
    if m.unemployment_rate_pct is not None:
        parts.append(f"US-Arbeitslosenquote: {m.unemployment_rate_pct:.2f} %")
    return " | ".join(parts) if parts else "Keine Makro-Daten verfuegbar."


def news_summary(bundle: DataBundle, limit: int = 8) -> str:
    if not bundle.news:
        return "Keine aktuellen News verfuegbar."
    lines = []
    for n in bundle.news[:limit]:
        pub = f" ({n.publisher})" if n.publisher else ""
        lines.append(f"- {n.title}{pub}")
    return "\n".join(lines)
