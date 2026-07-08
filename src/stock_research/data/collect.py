"""Collects all raw data for one ticker into a DataBundle."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from ..config import Settings
from .macro import fetch_macro
from .market import fetch_market_data
from .models import DataBundle
from .news import fetch_news

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "evals" / "fixtures"


def collect(ticker: str, settings: Settings, offline: bool = False,
            fixtures_dir: Path | None = None) -> DataBundle:
    """Collects price, fundamental, macro and news data.

    offline=True loads a recorded data snapshot from evals/fixtures instead of
    fetching live from Yahoo/FRED - for tests, evals and environments without
    network access to the data sources.
    """
    if offline:
        return load_fixture(ticker, fixtures_dir or FIXTURES_DIR)

    fundamentals, price_stats = fetch_market_data(ticker)
    macro = fetch_macro(settings.fred_api_key)
    news = fetch_news(ticker)
    return DataBundle(
        fundamentals=fundamentals,
        price_stats=price_stats,
        macro=macro,
        news=news,
        collected_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        data_source="live",
    )


def load_fixture(ticker: str, fixtures_dir: Path) -> DataBundle:
    path = fixtures_dir / f"{ticker.upper()}.json"
    if not path.exists():
        available = sorted(p.stem for p in fixtures_dir.glob("*.json"))
        raise FileNotFoundError(
            f"No fixture for '{ticker.upper()}' under {fixtures_dir}. "
            f"Available: {', '.join(available) or '(none)'}"
        )
    bundle = DataBundle.from_dict(json.loads(path.read_text(encoding="utf-8")))
    bundle.data_source = "fixture"
    return bundle


def save_fixture(bundle: DataBundle, fixtures_dir: Path) -> Path:
    """Saves a live snapshot as a fixture (to refresh the eval data)."""
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    path = fixtures_dir / f"{bundle.fundamentals.ticker}.json"
    path.write_text(json.dumps(bundle.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return path
