"""Makro-Kontext (Zinsen, Inflation, Arbeitsmarkt) via FRED API.

Docs: https://fred.stlouisfed.org/docs/api/fred/series_observations.html
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import requests

from .models import MacroData

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

SERIES = {
    "ten_year_treasury_pct": "DGS10",     # 10-jaehrige US-Staatsanleihe (%)
    "fed_funds_rate_pct": "FEDFUNDS",     # US-Leitzins (%)
    "unemployment_rate_pct": "UNRATE",    # US-Arbeitslosenquote (%)
}
CPI_SERIES = "CPIAUCSL"  # CPI-Index; Inflation = Veraenderung ggue. Vorjahr


def parse_observations(payload: dict[str, Any]) -> list[tuple[str, float]]:
    """Extrahiert (Datum, Wert)-Paare; FRED markiert fehlende Werte mit '.'."""
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
    """Berechnet die Veraenderung des letzten Werts ggue. dem Wert vor `months` Monaten."""
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
    """Laedt den Makro-Kontext. Ohne API-Key werden leere Werte zurueckgegeben."""
    macro = MacroData(as_of=dt.date.today().isoformat())
    if not api_key:
        macro.source = "FRED (kein API-Key gesetzt - Makro-Daten uebersprungen)"
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
