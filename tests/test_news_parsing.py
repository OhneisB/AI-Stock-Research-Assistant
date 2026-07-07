"""Tests fuer das Parsing des yfinance-News-Feeds (altes und neues Format)."""

from stock_research.data.news import parse_news

NEW_FORMAT = [
    {
        "id": "abc",
        "content": {
            "title": "Beispiel-Schlagzeile",
            "pubDate": "2026-07-01T09:00:00Z",
            "provider": {"displayName": "Reuters"},
            "canonicalUrl": {"url": "https://example.com/a"},
        },
    }
]

OLD_FORMAT = [
    {
        "title": "Alte Schlagzeile",
        "publisher": "Bloomberg",
        "providerPublishTime": 1751360400,
        "link": "https://example.com/b",
    }
]


def test_parse_new_format():
    items = parse_news(NEW_FORMAT)
    assert len(items) == 1
    assert items[0].title == "Beispiel-Schlagzeile"
    assert items[0].publisher == "Reuters"
    assert items[0].link == "https://example.com/a"
    assert items[0].published.startswith("2026-07-01")


def test_parse_old_format():
    items = parse_news(OLD_FORMAT)
    assert items[0].title == "Alte Schlagzeile"
    assert items[0].publisher == "Bloomberg"
    assert items[0].link == "https://example.com/b"
    assert items[0].published.startswith("2025-07-01")


def test_parse_news_skips_empty_and_limits():
    raw = [{"content": {"title": ""}}] + NEW_FORMAT * 20
    items = parse_news(raw, limit=5)
    assert len(items) == 5


def test_parse_news_handles_garbage():
    assert parse_news([]) == []
    assert parse_news([{"unexpected": 1}]) == []
