"""Price data and fundamentals via yfinance.

Network access is deliberately separated from the parsing logic so the
parsing can be unit-tested with fixtures.
"""

from __future__ import annotations

import math
from typing import Any

from .models import FUNDAMENTAL_FIELDS, Fundamentals, PriceStats


def _clean_number(value: Any) -> float | None:
    """Robustly converts yfinance values to float (None for garbage)."""
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
    """Extracts the relevant metrics from a yfinance info dict."""
    metrics: dict[str, float | None] = {}
    for field, yf_key in FUNDAMENTAL_FIELDS.items():
        metrics[field] = _clean_number(info.get(yf_key))
    # Fallback: currentPrice is missing for some tickers
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
    """Computes 1-year return and annualized volatility from closing prices."""
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
    """Loads the info dict and 1 year of price history from Yahoo Finance."""
    import yfinance as yf  # lazy import: tests/offline mode do not need it

    t = yf.Ticker(ticker)
    info = t.info or {}
    if not info.get("longName") and not info.get("shortName") and not info.get("regularMarketPrice"):
        raise ValueError(f"No data found for ticker '{ticker}' - please check the symbol.")
    fundamentals = parse_info(ticker, info)

    history = t.history(period="1y", auto_adjust=True)
    closes = [float(c) for c in history["Close"].tolist()] if len(history) else []
    price_stats = compute_price_stats(closes)

    return fundamentals, price_stats
