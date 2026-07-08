"""Four-stage analysis pipeline.

Two analyst implementations:

- ClaudeAnalyst: calls the Anthropic API (model from the configuration,
  default claude-sonnet-5). Requires ANTHROPIC_API_KEY.
- TemplateAnalyst: deterministic offline analyst that generates the sections
  rule-based from the raw data. It serves tests, the eval suite and
  environments without an API key. The texts are intentionally schematic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..config import Settings
from ..data.models import PERCENT_FIELDS, DataBundle
from . import prompts
from .formatting import format_metric, macro_summary

SECTION_ORDER = ["fundamental_analysis", "qualitative_assessment", "bull_bear", "memo"]


@dataclass
class AnalysisResult:
    ticker: str
    sections: dict[str, str] = field(default_factory=dict)
    mode: str = "claude"       # "claude" or "template"
    model: str = ""
    deep: bool = False


class Analyst(Protocol):
    name: str

    def complete(self, prompt: str) -> str: ...


class ClaudeAnalyst:
    """Analyst based on the Anthropic Messages API."""

    def __init__(self, settings: Settings):
        if not settings.has_anthropic:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add the key to .env "
                "or use --offline for template mode."
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
            raise RuntimeError("The request was declined by the model (refusal).")
        return "\n".join(b.text for b in response.content if b.type == "text").strip()


class TemplateAnalyst:
    """Deterministic offline analyst (no LLM).

    Generates schematic but data-consistent texts directly from the raw data.
    complete() is not driven by prompts here; instead run_pipeline() renders
    the sections directly via the section_* methods.
    """

    name = "template (offline, no LLM)"

    def __init__(self, bundle: DataBundle):
        self._b = bundle

    def complete(self, prompt: str) -> str:  # Protocol compatibility
        return "(template analyst: see section_* methods)"

    # -- helpers -----------------------------------------------------------

    def _m(self, field_name: str) -> float | None:
        return self._b.fundamentals.metrics.get(field_name)

    def _fmt(self, field_name: str) -> str:
        return format_metric(field_name, self._m(field_name), self._b.fundamentals.currency)

    def _pct(self, field_name: str) -> float | None:
        v = self._m(field_name)
        if v is None:
            return None
        return v * 100 if field_name in PERCENT_FIELDS else v

    # -- sections -----------------------------------------------------------

    def section_fundamental(self) -> str:
        f = self._b.fundamentals
        pe = self._m("trailing_pe")
        valuation = (
            "The valuation cannot be determined from the available data." if pe is None
            else f"With a trailing P/E of {self._fmt('trailing_pe')}, "
            + ("the valuation is in elevated territory." if pe > 30
               else "the valuation is in a moderate range." if pe > 15
               else "the valuation appears optically cheap.")
        )
        growth = self._pct("revenue_growth")
        growth_text = (
            "No revenue-growth data is available." if growth is None
            else f"Revenue growth stands at {self._fmt('revenue_growth')} year over year."
        )
        margins = (
            f"The net margin is {self._fmt('profit_margin')}, the operating margin "
            f"{self._fmt('operating_margin')} and the gross margin {self._fmt('gross_margin')}."
        )
        dte = self._m("debt_to_equity")
        leverage = (
            "No leverage data is available." if dte is None
            else f"The debt/equity ratio is {self._fmt('debt_to_equity')}, the current "
            f"ratio {self._fmt('current_ratio')} and free cash flow {self._fmt('free_cashflow')}."
        )
        return (
            f"{f.name} is valued at a market capitalization of {self._fmt('market_cap')}. "
            f"{valuation} The price-to-book ratio is {self._fmt('price_to_book')}, "
            f"EV/EBITDA is {self._fmt('ev_to_ebitda')}.\n\n"
            f"{growth_text} Earnings growth stands at {self._fmt('earnings_growth')}.\n\n"
            f"{margins} Return on equity (ROE) is {self._fmt('return_on_equity')}.\n\n"
            f"{leverage}"
        )

    def section_qualitative(self) -> str:
        f = self._b.fundamentals
        gm = self._pct("gross_margin")
        moat = (
            f"The gross margin of {self._fmt('gross_margin')} points to a degree of "
            "pricing power." if gm is not None and gm > 40
            else "The margin profile does not indicate a pronounced moat."
        )
        beta = self._m("beta")
        risk = (
            f"With a beta of {self._fmt('beta')}, the stock fluctuates "
            + ("more than the overall market." if beta is not None and beta > 1.1
               else "roughly in line with the overall market." if beta is not None
               else "- beta not available.")
        )
        return (
            f"{f.name} operates in the {f.sector or 'n/a'} sector "
            f"(industry: {f.industry or 'n/a'}). {moat}\n\n"
            f"Risks: {risk} The macro environment ({macro_summary(self._b)}) affects "
            "valuation levels and funding costs.\n\n"
            "Note: This qualitative assessment was derived rule-based from metrics "
            "(offline mode) and does not replace a substantive analysis of the "
            "business model and competition."
        )

    def section_bull_bear(self) -> str:
        bull, bear = [], []
        rg = self._pct("revenue_growth")
        if rg is not None:
            (bull if rg > 5 else bear).append(
                f"Revenue growth of {self._fmt('revenue_growth')} (YoY)."
            )
        pm = self._pct("profit_margin")
        if pm is not None:
            (bull if pm > 15 else bear).append(f"Net margin of {self._fmt('profit_margin')}.")
        pe = self._m("trailing_pe")
        if pe is not None:
            (bear if pe > 30 else bull).append(
                f"Trailing P/E of {self._fmt('trailing_pe')}."
            )
        dte = self._m("debt_to_equity")
        if dte is not None:
            (bear if dte > 100 else bull).append(
                f"Debt/equity ratio of {self._fmt('debt_to_equity')}."
            )
        fcf = self._m("free_cashflow")
        if fcf is not None:
            (bull if fcf > 0 else bear).append(f"Free cash flow of {self._fmt('free_cashflow')}.")
        bull = bull or ["No clearly positive metric signals in the data."]
        bear = bear or ["No clearly negative metric signals in the data."]
        return (
            "### Bull Case\n" + "\n".join(f"- {x}" for x in bull)
            + "\n\n### Bear Case\n" + "\n".join(f"- {x}" for x in bear)
        )

    def section_memo(self) -> str:
        f = self._b.fundamentals
        return (
            f"{f.name} ({f.ticker}) trades at {self._fmt('price')} with a market "
            f"capitalization of {self._fmt('market_cap')}. The valuation (trailing P/E "
            f"{self._fmt('trailing_pe')}) meets revenue growth of "
            f"{self._fmt('revenue_growth')} and a net margin of {self._fmt('profit_margin')}. "
            f"Key things to watch are the trajectory of growth and margins as well as "
            f"the interest-rate environment. This memo was generated rule-based in offline mode."
        )


def run_pipeline(bundle: DataBundle, analyst: Analyst | TemplateAnalyst,
                 deep: bool = False) -> AnalysisResult:
    """Runs the four analysis stages and collects the sections."""
    result = AnalysisResult(ticker=bundle.fundamentals.ticker, deep=deep)

    if isinstance(analyst, TemplateAnalyst):
        result.mode = "template"
        result.model = analyst.name
        result.sections = {
            "fundamental_analysis": analyst.section_fundamental(),
            "qualitative_assessment": analyst.section_qualitative(),
            "bull_bear": analyst.section_bull_bear(),
        }
        result.sections["memo"] = analyst.section_memo()
        return result

    result.mode = "claude"
    result.model = analyst.name
    result.sections["fundamental_analysis"] = analyst.complete(
        prompts.fundamental_prompt(bundle, deep))
    result.sections["qualitative_assessment"] = analyst.complete(
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
