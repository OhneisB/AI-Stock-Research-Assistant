"""Datenmodelle fuer alle gesammelten Rohdaten."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

# Kennzahlen, die aus dem yfinance-Info-Dict extrahiert werden.
# Mapping: unser Feldname -> yfinance-Key
FUNDAMENTAL_FIELDS: dict[str, str] = {
    "price": "currentPrice",
    "market_cap": "marketCap",
    "trailing_pe": "trailingPE",
    "forward_pe": "forwardPE",
    "price_to_book": "priceToBook",
    "price_to_sales": "priceToSalesTrailing12Months",
    "ev_to_ebitda": "enterpriseToEbitda",
    "peg_ratio": "pegRatio",
    "profit_margin": "profitMargins",
    "operating_margin": "operatingMargins",
    "gross_margin": "grossMargins",
    "revenue_growth": "revenueGrowth",
    "earnings_growth": "earningsGrowth",
    "return_on_equity": "returnOnEquity",
    "debt_to_equity": "debtToEquity",
    "current_ratio": "currentRatio",
    "free_cashflow": "freeCashflow",
    "total_revenue": "totalRevenue",
    "dividend_yield": "dividendYield",
    "beta": "beta",
    "fifty_two_week_high": "fiftyTwoWeekHigh",
    "fifty_two_week_low": "fiftyTwoWeekLow",
}

# Felder, die yfinance als Dezimalbruch liefert (0.25 = 25 %)
PERCENT_FIELDS = {
    "profit_margin",
    "operating_margin",
    "gross_margin",
    "revenue_growth",
    "earnings_growth",
    "return_on_equity",
}


@dataclass
class Fundamentals:
    ticker: str
    name: str = ""
    sector: str = ""
    industry: str = ""
    currency: str = "USD"
    metrics: dict[str, float | None] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PriceStats:
    """Aus der Kurshistorie abgeleitete Statistiken (1 Jahr)."""

    return_1y_pct: float | None = None
    volatility_ann_pct: float | None = None
    last_close: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MacroData:
    """Makro-Kontext aus der FRED API."""

    ten_year_treasury_pct: float | None = None
    fed_funds_rate_pct: float | None = None
    cpi_inflation_yoy_pct: float | None = None
    unemployment_rate_pct: float | None = None
    as_of: str = ""
    source: str = "FRED"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NewsItem:
    title: str
    publisher: str = ""
    published: str = ""
    link: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DataBundle:
    """Alle Rohdaten fuer einen Ticker - Input fuer die Analyse-Pipeline."""

    fundamentals: Fundamentals
    price_stats: PriceStats
    macro: MacroData
    news: list[NewsItem]
    collected_at: str = ""
    data_source: str = "live"  # "live" oder "fixture"

    def to_dict(self) -> dict[str, Any]:
        return {
            "fundamentals": self.fundamentals.to_dict(),
            "price_stats": self.price_stats.to_dict(),
            "macro": self.macro.to_dict(),
            "news": [n.to_dict() for n in self.news],
            "collected_at": self.collected_at,
            "data_source": self.data_source,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DataBundle":
        return cls(
            fundamentals=Fundamentals(**d["fundamentals"]),
            price_stats=PriceStats(**d["price_stats"]),
            macro=MacroData(**d["macro"]),
            news=[NewsItem(**n) for n in d.get("news", [])],
            collected_at=d.get("collected_at", ""),
            data_source=d.get("data_source", "fixture"),
        )
