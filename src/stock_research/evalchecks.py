"""Automatisierte Qualitaetspruefungen fuer generierte Reports.

Drei Checks pro Report (genutzt von evals/run_evals.py und den Unit-Tests):

(a) Pflicht-Sektionen: alle REQUIRED_SECTIONS und der Disclaimer sind enthalten.
(b) Kennzahlen-Konsistenz: die Werte in der Kennzahlenuebersicht des Markdown-
    Reports stimmen (mit Toleranz) mit den Rohdaten ueberein.
(c) Halluzinations-Check: jede Zahl im Fliesstext des Analysten laesst sich
    (mit Toleranz) auf einen Rohdatenwert zurueckfuehren.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import DISCLAIMER
from .analysis.pipeline import AnalysisResult
from .data.models import PERCENT_FIELDS, DataBundle
from .report import REQUIRED_SECTIONS

# Zahlen wie "34.70" oder "108"; ein Satzende-Punkt ("... bei 999.99.")
# gehoert nicht zur Zahl und darf das Match nicht verhindern.
NUMBER_RE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(?!\.?\d)(?!\w)")

# Zahlen, die im Text erlaubt sind, ohne Kennzahl zu sein
_YEAR_MIN, _YEAR_MAX = 1900, 2100
_SMALL_INT_MAX = 12  # Aufzaehlungen, "3 Argumente", "10 Jahre" etc.


# ---------------------------------------------------------------- (a) Sektionen

def check_sections(markdown: str) -> tuple[bool, list[str]]:
    """Prueft, ob alle Pflicht-Sektionen und der Disclaimer vorhanden sind."""
    missing = [s for s in REQUIRED_SECTIONS if s not in markdown]
    if "Disclaimer" not in markdown or "KEINE Anlageberatung" not in markdown:
        missing.append("Disclaimer")
    return (not missing, missing)


# ------------------------------------------------------- (b) Kennzahlen-Tabelle

@dataclass
class MetricCheck:
    label: str
    report_value: float
    raw_value: float
    ok: bool


def _table_numbers(markdown: str) -> list[tuple[str, float]]:
    """Extrahiert (Label, erster Zahlwert) aus der Kennzahlenuebersicht."""
    section = markdown.split("## Kennzahlenuebersicht", 1)
    if len(section) < 2:
        return []
    table = section[1].split("\n## ", 1)[0]
    out: list[tuple[str, float]] = []
    for line in table.splitlines():
        if not line.startswith("|") or line.startswith("|---") or "Kennzahl" in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2 or cells[1] == "n/a":
            continue
        m = NUMBER_RE.search(cells[1].replace(",", ""))
        if m:
            out.append((cells[0], float(m.group(1))))
    return out


def acceptable_values(bundle: DataBundle) -> set[float]:
    """Alle Zahlwerte, die legitim aus den Rohdaten zitiert werden koennen.

    Enthaelt pro Kennzahl auch skalierte Varianten (Prozent x100,
    Mrd./Mio./Bio.-Skalierung), da Reports Werte formatiert wiedergeben.
    """
    values: set[float] = set()

    def add(v: float | None) -> None:
        if v is None:
            return
        v = abs(float(v))
        for variant in (v, v * 100, v / 1e6, v / 1e9, v / 1e12):
            if 0 < variant < 1e15:
                values.add(round(variant, 4))

    for name, v in bundle.fundamentals.metrics.items():
        add(v)
        if name in PERCENT_FIELDS and v is not None:
            add(v * 100)
    ps = bundle.price_stats
    for v in (ps.return_1y_pct, ps.volatility_ann_pct, ps.last_close):
        add(v)
    m = bundle.macro
    for v in (m.ten_year_treasury_pct, m.fed_funds_rate_pct,
              m.cpi_inflation_yoy_pct, m.unemployment_rate_pct):
        add(v)
    return values


def _matches(number: float, values: set[float], rel_tol: float) -> bool:
    for v in values:
        if v == 0:
            continue
        # Rundungstoleranz: formatierte Werte sind auf 1-2 Nachkommastellen
        # gerundet, daher zusaetzlich eine kleine absolute Toleranz.
        if abs(number - v) <= max(rel_tol * abs(v), 0.06):
            return True
    return False


def check_metrics_table(markdown: str, bundle: DataBundle,
                        rel_tol: float = 0.005) -> tuple[bool, list[MetricCheck]]:
    """Prueft die Kennzahlenuebersicht im Report gegen die Rohdaten."""
    values = acceptable_values(bundle)
    checks: list[MetricCheck] = []
    for label, number in _table_numbers(markdown):
        ok = _matches(number, values, rel_tol)
        checks.append(MetricCheck(label=label, report_value=number,
                                  raw_value=number if ok else float("nan"), ok=ok))
    all_ok = bool(checks) and all(c.ok for c in checks)
    return all_ok, checks


# -------------------------------------------------- (c) Halluzinations-Check

@dataclass
class HallucinationReport:
    numbers_checked: int = 0
    unmatched: list[float] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.unmatched


def _is_exempt(n: float) -> bool:
    if n == int(n):
        i = int(n)
        if i <= _SMALL_INT_MAX or _YEAR_MIN <= i <= _YEAR_MAX:
            return True
    return False


def check_hallucinations(result: AnalysisResult, bundle: DataBundle,
                         rel_tol: float = 0.05) -> HallucinationReport:
    """Prueft alle Zahlen in den Analysten-Sektionen gegen die Rohdaten.

    Eine Zahl gilt als belegt, wenn sie (mit relativer Toleranz) einem
    Rohdatenwert oder einer ueblichen Skalierung davon entspricht.
    """
    values = acceptable_values(bundle)
    report = HallucinationReport()
    text = "\n".join(result.sections.values())
    # 52-Wochen-Spannen u. ae. koennen als "123.45-234.56" auftreten
    text = text.replace("–", "-")
    for m in NUMBER_RE.finditer(text):
        n = float(m.group(1))
        if _is_exempt(n):
            continue
        report.numbers_checked += 1
        if not _matches(n, values, rel_tol):
            report.unmatched.append(n)
    return report
