"""Zentrale Konfiguration.

Alle Secrets kommen ausschliesslich aus Umgebungsvariablen (bzw. einer lokalen
.env-Datei, die via python-dotenv geladen wird). Es gibt keine hardcodierten Keys.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "claude-sonnet-5"


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None
    fred_api_key: str | None
    model: str
    reports_dir: Path

    @property
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def has_fred(self) -> bool:
        return bool(self.fred_api_key)


def get_settings(reports_dir: str | Path | None = None) -> Settings:
    return Settings(
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
        fred_api_key=os.environ.get("FRED_API_KEY") or None,
        model=os.environ.get("STOCK_RESEARCH_MODEL", DEFAULT_MODEL),
        reports_dir=Path(reports_dir or os.environ.get("STOCK_RESEARCH_REPORTS_DIR", "reports")),
    )
