import json
from pathlib import Path

import pytest

from stock_research.data.models import DataBundle

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "evals" / "fixtures"


@pytest.fixture
def aapl_bundle() -> DataBundle:
    data = json.loads((FIXTURES_DIR / "AAPL.json").read_text(encoding="utf-8"))
    return DataBundle.from_dict(data)


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR
