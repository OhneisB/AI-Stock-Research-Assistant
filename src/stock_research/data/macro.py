"""Macro context (interest rates, inflation, labor market) via the FRED API.

Docs: https://fred.stlouisfed.org/docs/api/fred/series_observations.html
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import requests

from .models import MacroData

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

SERIES = {
    "ten_year_treasury_pct": "DGS10",     # 10-year US Treasury yield (%)
    "fed_funds_rate_pct": "FEDFUNDS",     # US federal funds rate (%)
    "unemployment_rate_pct": "UNRATE",    # US unemployment rate (%)
}
CPI_SERIES = "CPIAUCSL"  # CPI index; inflation = year-over-year change


def parse_observations(payload: dict[str, Any]) -> list[tuple[str, float]]:
    """Extracts (date, value) pairs; FRED marks missing values with '.'."""
    out: list[tuple[str, float]] = []
    for obs in payload.get("observations", []):
        raw = obs.get("value", ".")
        if raw in (".", "", None):
            continue
        try:
            out.append((obs.get("date", ""), float(raw)))
        except (TypeError, ValueError):
            continue
    return out


def latest_value(payload: dict[str, Any]) -> float | None:
    obs = parse_observations(payload)
    return obs[-1][1] if obs else None


def yoy_change_pct(payload: dict[str, Any], months: int = 12) -> float | None:
    """Computes the change of the latest value vs. the value `months` months ago."""
    obs = parse_observations(payload)
    if len(obs) <= months:
        return None
    current = obs[-1][1]
    year_ago = obs[-1 - months][1]
    if year_ago == 0:
        return None
    return round((current / year_ago - 1.0) * 100.0, 2)


def _fred_get(series_id: str, api_key: str, limit: int = 400) -> dict[str, Any]:
    resp = requests.get(
        FRED_BASE,
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "asc",
            "observation_start": (dt.date.today() - dt.timedelta(days=800)).isoformat(),
            "limit": limit,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_macro(api_key: str | None) -> MacroData:
    """Loads the macro context. Without an API key, empty values are returned."""
    macro = MacroData(as_of=dt.date.today().isoformat())
    if not api_key:
        macro.source = "FRED (no API key set - macro data skipped)"
        return macro

    for field, series_id in SERIES.items():
        try:
            setattr(macro, field, latest_value(_fred_get(series_id, api_key)))
        except requests.RequestException:
            pass
    try:
        macro.cpi_inflation_yoy_pct = yoy_change_pct(_fred_get(CPI_SERIES, api_key))
    except requests.RequestException:
        pass
    return macro
