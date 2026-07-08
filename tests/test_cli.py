"""CLI tests in offline mode (no network, no API keys)."""

from stock_research.cli import main


def test_cli_offline_single_ticker(tmp_path, capsys):
    code = main(["AAPL", "--offline", "--out", str(tmp_path)])
    assert code == 0
    reports = list(tmp_path.glob("AAPL_*.md"))
    raws = list(tmp_path.glob("AAPL_*.json"))
    assert len(reports) == 1 and len(raws) == 1
    content = reports[0].read_text(encoding="utf-8")
    assert "Research Memo: Apple Inc. (AAPL)" in content
    assert "NOT constitute investment advice" in content


def test_cli_offline_compare(tmp_path):
    code = main(["--compare", "AAPL", "MSFT", "--offline", "--out", str(tmp_path)])
    assert code == 0
    compare = list(tmp_path.glob("AAPL_vs_MSFT_*.md"))
    assert len(compare) == 1
    text = compare[0].read_text(encoding="utf-8")
    assert "Comparison" in text and "Key Metrics MSFT" in text


def test_cli_compare_needs_two_tickers(tmp_path):
    assert main(["--compare", "AAPL", "--offline", "--out", str(tmp_path)]) == 2


def test_cli_unknown_fixture(tmp_path):
    assert main(["NOPE", "--offline", "--out", str(tmp_path)]) == 1
