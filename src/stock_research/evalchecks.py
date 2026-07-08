"""Automated quality checks for generated reports.

Three checks per report (used by evals/run_evals.py and the unit tests):

(a) Mandatory sections: all REQUIRED_SECTIONS and the disclaimer are present.
(b) Metric consistency: the values in the report's key-metrics table match
    the raw data (within tolerance).
(c) Hallucination check: every number in the analyst's prose can be traced
    back to a raw-data value (within tolerance).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import DISCLAIMER
from .analysis.pipeline import AnalysisResult
from .data.models import PERCENT_FIELDS, DataBundle
from .report import REQUIRED_SECTIONS

# Numbers like "34.70" or "108"; a sentence-final period ("... at 999.99.")
# is not part of the number and must not prevent the match.
NUMBER_RE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(?!\.?\d)(?!\w)")

# Numbers that are allowed in the text without being a metric
_YEAR_MIN, _YEAR_MAX = 1900, 2100
_SMALL_INT_MAX = 12  # enumerations, "3 arguments", "10 years" etc.


# ---------------------------------------------------------------- (a) sections

def check_sections(markdown: str) -> tuple[bool, list[str]]:
    """Checks that all mandatory sections and the disclaimer are present."""
    missing = [s for s in REQUIRED_SECTIONS if s not in markdown]
    if "Disclaimer" not in markdown or "NOT constitute investment advice" not in markdown:
        missing.append("Disclaimer")
    return (not missing, missing)


# --------------------------------------------------------- (b) metrics table

@dataclass
class MetricCheck:
    label: str
    report_value: float
    raw_value: float
    ok: bool


def _table_numbers(markdown: str) -> list[tuple[str, float]]:
    """Extracts (label, first numeric value) from the key-metrics table."""
    section = markdown.split("## Key Metrics", 1)
    if len(section) < 2:
        return []
    table = section[1].split("\n## ", 1)[0]
    out: list[tuple[str, float]] = []
    for line in table.splitlines():
        if not line.startswith("|") or line.startswith("|---") or "Metric" in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2 or cells[1] == "n/a":
            continue
        m = NUMBER_RE.search(cells[1].replace(",", ""))
        if m:
            out.append((cells[0], float(m.group(1))))
    return out


def acceptable_values(bundle: DataBundle) -> set[float]:
    """All numeric values that can legitimately be cited from the raw data.

    Per metric this also includes scaled variants (percent x100,
    trillion/billion/million scaling), since reports render values formatted.
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
        # Rounding tolerance: formatted values are rounded to 1-2 decimal
        # places, hence an additional small absolute tolerance.
        if abs(number - v) <= max(rel_tol * abs(v), 0.06):
            return True
    return False


def check_metrics_table(markdown: str, bundle: DataBundle,
                        rel_tol: float = 0.005) -> tuple[bool, list[MetricCheck]]:
    """Checks the report's key-metrics table against the raw data."""
    values = acceptable_values(bundle)
    checks: list[MetricCheck] = []
    for label, number in _table_numbers(markdown):
        ok = _matches(number, values, rel_tol)
        checks.append(MetricCheck(label=label, report_value=number,
                                  raw_value=number if ok else float("nan"), ok=ok))
    all_ok = bool(checks) and all(c.ok for c in checks)
    return all_ok, checks


# -------------------------------------------------- (c) hallucination check

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
    """Checks all numbers in the analyst sections against the raw data.

    A number counts as substantiated if it matches a raw-data value (or a
    common scaling of one) within a relative tolerance.
    """
    values = acceptable_values(bundle)
    report = HallucinationReport()
    text = "\n".join(result.sections.values())
    # 52-week ranges etc. may appear as "123.45-234.56"
    text = text.replace("–", "-")
    for m in NUMBER_RE.finditer(text):
        n = float(m.group(1))
        if _is_exempt(n):
            continue
        report.numbers_checked += 1
        if not _matches(n, values, rel_tol):
            report.unmatched.append(n)
    return report
