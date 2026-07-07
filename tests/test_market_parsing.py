"""Tests fuer das Parsing von yfinance-Daten (ohne Netzwerk)."""

import math

from stock_research.data.market import _clean_number, compute_price_stats, parse_info

SAMPLE_INFO = {
    "longName": "Beispiel AG",
    "sector": "Technology",
    "industry": "Software",
    "currency": "EUR",
    "currentPrice": 123.45,
    "marketCap": 5_000_000_000,
    "trailingPE": 22.5,
    "forwardPE": "19.1",          # yfinance liefert gelegentlich Strings
    "profitMargins": 0.18,
    "revenueGrowth": 0.07,
    "debtToEquity": 45.2,
    "dividendYield": 0.015,
    "beta": float("nan"),          # NaN muss zu None werden
    "freeCashflow": None,
}


def test_clean_number_edge_cases():
    assert _clean_number(None) is None
    assert _clean_number(True) is None
    assert _clean_number("abc") is None
    assert _clean_number(float("nan")) is None
    assert _clean_number(float("inf")) is None
    assert _clean_number("19.1") == 19.1
    assert _clean_number(3) == 3.0


def test_parse_info_extracts_metrics():
    f = parse_info("bsp", SAMPLE_INFO)
    assert f.ticker == "BSP"
    assert f.name == "Beispiel AG"
    assert f.currency == "EUR"
    assert f.metrics["price"] == 123.45
    assert f.metrics["trailing_pe"] == 22.5
    assert f.metrics["forward_pe"] == 19.1
    assert f.metrics["beta"] is None
    assert f.metrics["free_cashflow"] is None


def test_parse_info_price_fallback():
    f = parse_info("X", {"shortName": "X Corp", "regularMarketPrice": 10.0})
    assert f.metrics["price"] == 10.0


def test_compute_price_stats():
    # 10 % Anstieg ueber die Serie
    closes = [100.0, 101.0, 102.0, 104.0, 106.0, 110.0]
    stats = compute_price_stats(closes)
    assert stats.return_1y_pct == 10.0
    assert stats.last_close == 110.0
    assert stats.volatility_ann_pct is not None and stats.volatility_ann_pct > 0


def test_compute_price_stats_degenerate():
    assert compute_price_stats([]).return_1y_pct is None
    assert compute_price_stats([100.0]).last_close == 100.0
    stats = compute_price_stats([100.0, float("nan"), 105.0])
    assert stats.return_1y_pct == 5.0
    assert not math.isnan(stats.volatility_ann_pct)
