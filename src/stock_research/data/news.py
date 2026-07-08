"""Recent company news via the yfinance news feed."""

from __future__ import annotations

import datetime as dt
from typing import Any

from .models import NewsItem


def parse_news(raw_items: list[dict[str, Any]], limit: int = 8) -> list[NewsItem]:
    """Normalizes the yfinance news structure.

    yfinance has changed the format several times: older versions return flat
    dicts (title/publisher/providerPublishTime/link), newer versions nest
    everything under 'content'. Both variants are supported.
    """
    items: list[NewsItem] = []
    for raw in raw_items or []:
        content = raw.get("content") if isinstance(raw.get("content"), dict) else raw

        title = content.get("title") or ""
        if not title:
            continue

        publisher = ""
        provider = content.get("provider")
        if isinstance(provider, dict):
            publisher = provider.get("displayName") or ""
        else:
            publisher = content.get("publisher") or ""

        published = content.get("pubDate") or content.get("displayTime") or ""
        if not published and content.get("providerPublishTime"):
            try:
                published = dt.datetime.fromtimestamp(
                    int(content["providerPublishTime"]), tz=dt.timezone.utc
                ).isoformat()
            except (TypeError, ValueError, OSError):
                published = ""

        link = ""
        url = content.get("canonicalUrl") or content.get("clickThroughUrl")
        if isinstance(url, dict):
            link = url.get("url") or ""
        else:
            link = content.get("link") or ""

        items.append(NewsItem(title=str(title), publisher=str(publisher),
                              published=str(published), link=str(link)))
        if len(items) >= limit:
            break
    return items


def fetch_news(ticker: str, limit: int = 8) -> list[NewsItem]:
    import yfinance as yf  # lazy import

    try:
        raw = yf.Ticker(ticker).news or []
    except Exception:
        return []
    return parse_news(raw, limit=limit)
