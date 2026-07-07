"""Prompt-Bausteine fuer die vierstufige Analyse-Pipeline."""

from __future__ import annotations

import json

from ..data.models import DataBundle
from .formatting import macro_summary, metrics_table_markdown, news_summary

SYSTEM_PROMPT = """Du bist ein erfahrener Aktienanalyst und schreibst praezise, \
nuechterne Research-Texte auf Deutsch fuer technisch interessierte Privatanleger.

Regeln:
- Stuetze dich AUSSCHLIESSLICH auf die im Prompt gelieferten Daten. Erfinde keine Zahlen.
- Wenn du eine Kennzahl nennst, uebernimm sie exakt aus den gelieferten Daten \
(Dezimalpunkt-Schreibweise, z. B. 32.5). Fehlende Werte ("n/a") nicht schaetzen, \
sondern als fehlend benennen.
- Keine Kursziele, keine Kauf-/Verkaufsempfehlungen, keine Anlageberatung.
- Schreibe sachlich und strukturiert in Markdown, ohne eigene Ueberschrift der \
obersten Ebene (die setzt der Report-Generator)."""


def data_block(bundle: DataBundle) -> str:
    """Serialisiert die Rohdaten fuer den Prompt (Tabelle + JSON)."""
    f = bundle.fundamentals
    return f"""## Rohdaten fuer {f.name} ({f.ticker})
Sektor: {f.sector or 'n/a'} | Branche: {f.industry or 'n/a'} | Waehrung: {f.currency}

### Kennzahlen
{metrics_table_markdown(bundle)}

### Makro-Umfeld
{macro_summary(bundle)}

### Aktuelle Schlagzeilen
{news_summary(bundle)}

### Rohkennzahlen (JSON)
```json
{json.dumps(bundle.fundamentals.metrics, indent=2)}
```"""


def fundamental_prompt(bundle: DataBundle, deep: bool = False) -> str:
    extra = (
        "\nGehe zusaetzlich auf das Zusammenspiel der Kennzahlen ein (z. B. Bewertung "
        "vs. Wachstum, Marge vs. Kapitalintensitaet) und ordne sie grob branchentypisch ein."
        if deep else ""
    )
    return f"""{data_block(bundle)}

Aufgabe: Schreibe eine Fundamentalanalyse (ca. {"400" if deep else "250"} Woerter) mit den Schwerpunkten:
1. Bewertungskennzahlen (KGV, P/B, P/S, EV/EBITDA, PEG)
2. Wachstum (Umsatz- und Gewinnwachstum)
3. Margen und Profitabilitaet (Brutto-, operative, Nettomarge, ROE)
4. Verschuldung und Bilanzqualitaet (Debt/Equity, Current Ratio, Free Cashflow){extra}"""


def qualitative_prompt(bundle: DataBundle, deep: bool = False) -> str:
    return f"""{data_block(bundle)}

Aufgabe: Schreibe eine qualitative Einschaetzung (ca. {"350" if deep else "200"} Woerter):
1. Moeglicher Burggraben (Moat): Markenstaerke, Netzwerkeffekte, Wechselkosten, Skalenvorteile
2. Wesentliche Risiken (unternehmens- und branchenspezifisch, Makro-Sensitivitaet)
3. Branchenlage und Wettbewerbsumfeld, unter Beruecksichtigung des Makro-Umfelds und der Schlagzeilen
Kennzeichne Einschaetzungen klar als solche."""


def bull_bear_prompt(bundle: DataBundle, deep: bool = False) -> str:
    n = 5 if deep else 3
    return f"""{data_block(bundle)}

Aufgabe: Formuliere einen Bull Case und einen Bear Case mit je {n} Argumenten.
Format:
### Bull Case
- ...
### Bear Case
- ...
Jedes Argument 1-2 Saetze, wo moeglich mit Bezug auf die gelieferten Kennzahlen."""


def memo_prompt(bundle: DataBundle, sections: dict[str, str], deep: bool = False) -> str:
    return f"""{data_block(bundle)}

Bisherige Analyse-Ergebnisse:

## Fundamentalanalyse
{sections.get('fundamentalanalyse', '')}

## Qualitative Einschaetzung
{sections.get('qualitative_einschaetzung', '')}

## Bull Case / Bear Case
{sections.get('bull_bear', '')}

Aufgabe: Verdichte alles zu einem Executive Summary im Stil eines Analysten-Memos \
(ca. {"250" if deep else "150"} Woerter): Kernthese, wichtigste Staerken und Risiken, \
worauf Anleger achten sollten. Keine Empfehlung, kein Kursziel."""


def compare_prompt(bundles: list[DataBundle]) -> str:
    blocks = "\n\n".join(data_block(b) for b in bundles)
    names = ", ".join(f"{b.fundamentals.name} ({b.fundamentals.ticker})" for b in bundles)
    return f"""{blocks}

Aufgabe: Vergleiche {names} entlang Bewertung, Wachstum, Profitabilitaet, \
Verschuldung und Risikoprofil (ca. 300 Woerter). Arbeite die wichtigsten \
Unterschiede heraus. Keine Empfehlung, welches Investment "besser" ist - \
nur eine sachliche Gegenueberstellung."""
