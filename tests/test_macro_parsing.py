"""Tests fuer das Parsing der FRED-API-Antworten (ohne Netzwerk)."""

from stock_research.data.macro import latest_value, parse_observations, yoy_change_pct


def _payload(values):
    return {"observations": [{"date": d, "value": v} for d, v in values]}


def test_parse_observations_skips_missing():
    payload = _payload([("2026-01-01", "4.5"), ("2026-02-01", "."), ("2026-03-01", "4.7")])
    obs = parse_observations(payload)
    assert obs == [("2026-01-01", 4.5), ("2026-03-01", 4.7)]


def test_latest_value():
    assert latest_value(_payload([("a", "1.0"), ("b", "2.5")])) == 2.5
    assert latest_value({"observations": []}) is None
    assert latest_value({}) is None


def test_yoy_change_pct():
    # 13 Monatswerte: 100 -> 103 entspricht +3.0 %
    values = [(f"2025-{m:02d}-01", "100") for m in range(1, 13)] + [("2026-01-01", "103")]
    assert yoy_change_pct(_payload(values)) == 3.0


def test_yoy_change_needs_enough_history():
    assert yoy_change_pct(_payload([("2026-01-01", "100")])) is None
