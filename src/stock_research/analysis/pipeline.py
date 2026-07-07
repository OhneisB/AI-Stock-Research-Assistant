"""Vierstufige Analyse-Pipeline.

Zwei Analysten-Implementierungen:

- ClaudeAnalyst: ruft die Anthropic API (Modell aus der Konfiguration,
  Default claude-sonnet-5). Benoetigt ANTHROPIC_API_KEY.
- TemplateAnalyst: deterministischer Offline-Analyst, der die Sektionen
  regelbasiert aus den Rohdaten erzeugt. Er dient fuer Tests, die Eval-Suite
  und Umgebungen ohne API-Key. Die Texte sind bewusst schematisch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..config import Settings
from ..data.models import PERCENT_FIELDS, DataBundle
from . import prompts
from .formatting import format_metric, macro_summary

SECTION_ORDER = ["fundamentalanalyse", "qualitative_einschaetzung", "bull_bear", "memo"]


@dataclass
class AnalysisResult:
    ticker: str
    sections: dict[str, str] = field(default_factory=dict)
    mode: str = "claude"       # "claude" oder "template"
    model: str = ""
    deep: bool = False


class Analyst(Protocol):
    name: str

    def complete(self, prompt: str) -> str: ...


class ClaudeAnalyst:
    """Analyst auf Basis der Anthropic Messages API."""

    def __init__(self, settings: Settings):
        if not settings.has_anthropic:
            raise RuntimeError(
                "ANTHROPIC_API_KEY ist nicht gesetzt. Key in .env eintragen "
                "oder --offline fuer den Template-Modus verwenden."
            )
        import anthropic  # lazy import

        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.model
        self.name = f"claude:{settings.model}"

    def complete(self, prompt: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=prompts.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("Die Anfrage wurde vom Modell abgelehnt (refusal).")
        return "\n".join(b.text for b in response.content if b.type == "text").strip()


class TemplateAnalyst:
    """Deterministischer Offline-Analyst (kein LLM).

    Erzeugt schematische, aber datenkonsistente Texte direkt aus den Rohdaten.
    complete() wird hier nicht ueber Prompts gesteuert; stattdessen rendert
    run_pipeline() die Sektionen direkt ueber die section_*-Methoden.
    """

    name = "template (offline, ohne LLM)"

    def __init__(self, bundle: DataBundle):
        self._b = bundle

    def complete(self, prompt: str) -> str:  # Protocol-Kompatibilitaet
        return "(Template-Analyst: siehe section_*-Methoden)"

    # -- Hilfsfunktionen -------------------------------------------------

    def _m(self, field_name: str) -> float | None:
        return self._b.fundamentals.metrics.get(field_name)

    def _fmt(self, field_name: str) -> str:
        return format_metric(field_name, self._m(field_name), self._b.fundamentals.currency)

    def _pct(self, field_name: str) -> float | None:
        v = self._m(field_name)
        if v is None:
            return None
        return v * 100 if field_name in PERCENT_FIELDS else v

    # -- Sektionen --------------------------------------------------------

    def section_fundamental(self) -> str:
        f = self._b.fundamentals
        pe = self._m("trailing_pe")
        bewertung = (
            "Die Bewertung ist anhand der Daten nicht bestimmbar." if pe is None
            else f"Mit einem KGV (trailing) von {self._fmt('trailing_pe')} "
            + ("liegt die Bewertung im hohen Bereich." if pe > 30
               else "liegt die Bewertung im moderaten Bereich." if pe > 15
               else "erscheint die Bewertung optisch guenstig.")
        )
        growth = self._pct("revenue_growth")
        wachstum = (
            "Zum Umsatzwachstum liegen keine Daten vor." if growth is None
            else f"Das Umsatzwachstum liegt bei {self._fmt('revenue_growth')} gegenueber dem Vorjahr."
        )
        marge = (
            f"Die Nettomarge betraegt {self._fmt('profit_margin')}, "
            f"die operative Marge {self._fmt('operating_margin')} und die "
            f"Bruttomarge {self._fmt('gross_margin')}."
        )
        dte = self._m("debt_to_equity")
        schulden = (
            "Zur Verschuldung liegen keine Daten vor." if dte is None
            else f"Der Verschuldungsgrad (Debt/Equity) betraegt {self._fmt('debt_to_equity')}, "
            f"die Current Ratio {self._fmt('current_ratio')} und der Free Cashflow {self._fmt('free_cashflow')}."
        )
        return (
            f"{f.name} wird mit einer Marktkapitalisierung von {self._fmt('market_cap')} bewertet. "
            f"{bewertung} Das Kurs-Buchwert-Verhaeltnis liegt bei {self._fmt('price_to_book')}, "
            f"EV/EBITDA bei {self._fmt('ev_to_ebitda')}.\n\n"
            f"{wachstum} Das Gewinnwachstum liegt bei {self._fmt('earnings_growth')}.\n\n"
            f"{marge} Die Eigenkapitalrendite (ROE) liegt bei {self._fmt('return_on_equity')}.\n\n"
            f"{schulden}"
        )

    def section_qualitative(self) -> str:
        f = self._b.fundamentals
        gm = self._pct("gross_margin")
        moat = (
            f"Die Bruttomarge von {self._fmt('gross_margin')} deutet auf eine gewisse "
            "Preissetzungsmacht hin." if gm is not None and gm > 40
            else "Aus den Margen laesst sich kein ausgepraegter Burggraben ableiten."
        )
        beta = self._m("beta")
        risiko = (
            f"Mit einem Beta von {self._fmt('beta')} schwankt die Aktie "
            + ("staerker als der Gesamtmarkt." if beta is not None and beta > 1.1
               else "etwa im Rahmen des Gesamtmarkts." if beta is not None
               else "- Beta nicht verfuegbar.")
        )
        return (
            f"{f.name} ist im Sektor {f.sector or 'n/a'} (Branche: {f.industry or 'n/a'}) taetig. "
            f"{moat}\n\n"
            f"Risiken: {risiko} "
            f"Das Makro-Umfeld ({macro_summary(self._b)}) beeinflusst Bewertungsniveaus und "
            "Finanzierungskosten.\n\n"
            "Hinweis: Diese qualitative Einschaetzung wurde regelbasiert aus Kennzahlen "
            "abgeleitet (Offline-Modus) und ersetzt keine inhaltliche Analyse von "
            "Geschaeftsmodell und Wettbewerb."
        )

    def section_bull_bear(self) -> str:
        bull, bear = [], []
        rg = self._pct("revenue_growth")
        if rg is not None:
            (bull if rg > 5 else bear).append(
                f"Umsatzwachstum von {self._fmt('revenue_growth')} (YoY)."
            )
        pm = self._pct("profit_margin")
        if pm is not None:
            (bull if pm > 15 else bear).append(f"Nettomarge von {self._fmt('profit_margin')}.")
        pe = self._m("trailing_pe")
        if pe is not None:
            (bear if pe > 30 else bull).append(
                f"KGV (trailing) von {self._fmt('trailing_pe')}."
            )
        dte = self._m("debt_to_equity")
        if dte is not None:
            (bear if dte > 100 else bull).append(
                f"Verschuldungsgrad (Debt/Equity) von {self._fmt('debt_to_equity')}."
            )
        fcf = self._m("free_cashflow")
        if fcf is not None:
            (bull if fcf > 0 else bear).append(f"Free Cashflow von {self._fmt('free_cashflow')}.")
        bull = bull or ["Keine eindeutig positiven Kennzahlen-Signale in den Daten."]
        bear = bear or ["Keine eindeutig negativen Kennzahlen-Signale in den Daten."]
        return (
            "### Bull Case\n" + "\n".join(f"- {x}" for x in bull)
            + "\n\n### Bear Case\n" + "\n".join(f"- {x}" for x in bear)
        )

    def section_memo(self) -> str:
        f = self._b.fundamentals
        return (
            f"{f.name} ({f.ticker}) notiert bei {self._fmt('price')} mit einer "
            f"Marktkapitalisierung von {self._fmt('market_cap')}. Die Bewertung "
            f"(KGV trailing {self._fmt('trailing_pe')}) trifft auf ein Umsatzwachstum von "
            f"{self._fmt('revenue_growth')} und eine Nettomarge von {self._fmt('profit_margin')}. "
            f"Wesentliche Beobachtungspunkte sind die Entwicklung von Wachstum und Margen "
            f"sowie das Zinsumfeld. Dieses Memo wurde im Offline-Modus regelbasiert erzeugt."
        )


def run_pipeline(bundle: DataBundle, analyst: Analyst | TemplateAnalyst,
                 deep: bool = False) -> AnalysisResult:
    """Fuehrt die vier Analyse-Stufen aus und sammelt die Sektionen."""
    result = AnalysisResult(ticker=bundle.fundamentals.ticker, deep=deep)

    if isinstance(analyst, TemplateAnalyst):
        result.mode = "template"
        result.model = analyst.name
        result.sections = {
            "fundamentalanalyse": analyst.section_fundamental(),
            "qualitative_einschaetzung": analyst.section_qualitative(),
            "bull_bear": analyst.section_bull_bear(),
        }
        result.sections["memo"] = analyst.section_memo()
        return result

    result.mode = "claude"
    result.model = analyst.name
    result.sections["fundamentalanalyse"] = analyst.complete(
        prompts.fundamental_prompt(bundle, deep))
    result.sections["qualitative_einschaetzung"] = analyst.complete(
        prompts.qualitative_prompt(bundle, deep))
    result.sections["bull_bear"] = analyst.complete(prompts.bull_bear_prompt(bundle, deep))
    result.sections["memo"] = analyst.complete(
        prompts.memo_prompt(bundle, result.sections, deep))
    return result


def make_analyst(settings: Settings, bundle: DataBundle,
                 force_template: bool = False) -> Analyst | TemplateAnalyst:
    if force_template or not settings.has_anthropic:
        return TemplateAnalyst(bundle)
    return ClaudeAnalyst(settings)
