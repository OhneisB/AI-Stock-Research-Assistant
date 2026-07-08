"""Prompt building blocks for the four-stage analysis pipeline."""

from __future__ import annotations

import json

from ..data.models import DataBundle
from .formatting import macro_summary, metrics_table_markdown, news_summary

SYSTEM_PROMPT = """You are an experienced equity analyst writing precise, \
sober research notes in English for technically minded retail investors.

Rules:
- Rely EXCLUSIVELY on the data provided in the prompt. Never invent numbers.
- When you cite a metric, copy it exactly from the provided data (decimal-point \
notation, e.g. 32.5). Do not estimate missing values ("n/a"); state that they \
are missing instead.
- No price targets, no buy/sell recommendations, no investment advice.
- Write factually and in structured Markdown, without your own top-level \
heading (the report generator adds it)."""


def data_block(bundle: DataBundle) -> str:
    """Serializes the raw data for the prompt (table + JSON)."""
    f = bundle.fundamentals
    return f"""## Raw data for {f.name} ({f.ticker})
Sector: {f.sector or 'n/a'} | Industry: {f.industry or 'n/a'} | Currency: {f.currency}

### Key metrics
{metrics_table_markdown(bundle)}

### Macro environment
{macro_summary(bundle)}

### Recent headlines
{news_summary(bundle)}

### Raw metrics (JSON)
```json
{json.dumps(bundle.fundamentals.metrics, indent=2)}
```"""


def fundamental_prompt(bundle: DataBundle, deep: bool = False) -> str:
    extra = (
        "\nAdditionally, discuss how the metrics interact (e.g. valuation vs. "
        "growth, margins vs. capital intensity) and put them roughly into an "
        "industry-typical context."
        if deep else ""
    )
    return f"""{data_block(bundle)}

Task: Write a fundamental analysis (about {"400" if deep else "250"} words) focusing on:
1. Valuation metrics (P/E, P/B, P/S, EV/EBITDA, PEG)
2. Growth (revenue and earnings growth)
3. Margins and profitability (gross, operating, net margin, ROE)
4. Leverage and balance-sheet quality (debt/equity, current ratio, free cash flow){extra}"""


def qualitative_prompt(bundle: DataBundle, deep: bool = False) -> str:
    return f"""{data_block(bundle)}

Task: Write a qualitative assessment (about {"350" if deep else "200"} words):
1. Possible moat: brand strength, network effects, switching costs, economies of scale
2. Key risks (company- and industry-specific, macro sensitivity)
3. Industry landscape and competitive environment, taking the macro environment \
and the headlines into account
Clearly mark judgments as such."""


def bull_bear_prompt(bundle: DataBundle, deep: bool = False) -> str:
    n = 5 if deep else 3
    return f"""{data_block(bundle)}

Task: Formulate a bull case and a bear case with {n} arguments each.
Format:
### Bull Case
- ...
### Bear Case
- ...
Each argument 1-2 sentences, referring to the provided metrics where possible."""


def memo_prompt(bundle: DataBundle, sections: dict[str, str], deep: bool = False) -> str:
    return f"""{data_block(bundle)}

Analysis results so far:

## Fundamental Analysis
{sections.get('fundamental_analysis', '')}

## Qualitative Assessment
{sections.get('qualitative_assessment', '')}

## Bull Case / Bear Case
{sections.get('bull_bear', '')}

Task: Condense everything into an executive summary in the style of an \
analyst memo (about {"250" if deep else "150"} words): core thesis, key \
strengths and risks, what investors should watch. No recommendation, no price target."""


def compare_prompt(bundles: list[DataBundle]) -> str:
    blocks = "\n\n".join(data_block(b) for b in bundles)
    names = ", ".join(f"{b.fundamentals.name} ({b.fundamentals.ticker})" for b in bundles)
    return f"""{blocks}

Task: Compare {names} along valuation, growth, profitability, leverage and \
risk profile (about 300 words). Highlight the most important differences. \
No recommendation as to which investment is "better" - a factual side-by-side \
comparison only."""
