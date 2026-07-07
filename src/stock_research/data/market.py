"""Kursdaten und Fundamentals via yfinance.

Der Netzwerkzugriff ist bewusst von der Parsing-Logik getrennt, damit das
Parsing mit Fixtures unit-getestet werden kann.
"""

from __future__ import annotations

import math
from typing import Any

from .models import FUNDAMENTAL_FIELDS, Fundamentals, PriceStats


def _clean_number(value: Any) -> float | None:
    """Konvertiert yfinance-Werte robust nach float (None bei Muell)."""
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def parse_info(ticker: str, info: dict[str, Any]) -> Fundamentals:
    """Extrahiert die relevanten Kennzahlen aus einem yfinance-Info-Dict."""
    metrics: dict[str, float | None] = {}
    for field, yf_key in FUNDAMENTAL_FIELDS.items():
        metrics[field] = _clean_number(info.get(yf_key))
    # Fallback: currentPrice fehlt bei manchen Tickern
    if metrics.get("price") is None:
        metrics["price"] = _clean_number(
            info.get("regularMarketPrice") or info.get("previousClose")
        )
    return Fundamentals(
        ticker=ticker.upper(),
        name=str(info.get("longName") or info.get("shortName") or ticker.upper()),
        sector=str(info.get("sector") or ""),
        industry=str(info.get("industry") or ""),
        currency=str(info.get("currency") or "USD"),
        metrics=metrics,
    )


def compute_price_stats(closes: list[float], trading_days_per_year: int = 252) -> PriceStats:
    """Berechnet 1-Jahres-Rendite und annualisierte Volatilitaet aus Schlusskursen."""
    closes = [c for c in (_clean_number(c) for c in closes) if c is not None and c > 0]
    if len(closes) < 2:
        return PriceStats(last_close=closes[-1] if closes else None)

    ret = (closes[-1] / closes[0] - 1.0) * 100.0

    daily_returns = [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes))]
    mean = sum(daily_returns) / len(daily_returns)
    var = sum((r - mean) ** 2 for r in daily_returns) / max(len(daily_returns) - 1, 1)
    vol = math.sqrt(var) * math.sqrt(trading_days_per_year) * 100.0

    return PriceStats(
        return_1y_pct=round(ret, 2),
        volatility_ann_pct=round(vol, 2),
        last_close=round(closes[-1], 2),
    )


def fetch_market_data(ticker: str) -> tuple[Fundamentals, PriceStats]:
    """Laedt Info-Dict und 1 Jahr Kurshistorie von Yahoo Finance."""
    import yfinance as yf  # lazy import: Tests/Offline-Modus brauchen es nicht

    t = yf.Ticker(ticker)
    info = t.info or {}
    if not info.get("longName") and not info.get("shortName") and not info.get("regularMarketPrice"):
        raise ValueError(f"Keine Daten fuer Ticker '{ticker}' gefunden - Symbol pruefen.")
    fundamentals = parse_info(ticker, info)

    history = t.history(period="1y", auto_adjust=True)
    closes = [float(c) for c in history["Close"].tolist()] if len(history) else []
    price_stats = compute_price_stats(closes)

    return fundamentals, price_stats
