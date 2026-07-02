from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import feedparser
import requests

from ann_app.config import (
    OUTLET_FEEDS,
    REQUEST_TIMEOUT_SECONDS,
    USER_AGENT,
)


@dataclass
class Candidate:
    outlet: str
    title: str
    link: str
    summary: str = ""
    published: datetime | None = None


@dataclass
class FetchResult:
    candidates: list[Candidate] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)


def _parse_published(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return datetime(*value[:6], tzinfo=UTC)
    return None


def _fetch_feed(url: str) -> feedparser.FeedParserDict:
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return feedparser.parse(response.content)


def fetch_outlet(outlet: str, feed_urls: list[str], within_hours: int = 36) -> tuple[list[Candidate], str | None]:
    cutoff = datetime.now(UTC) - timedelta(hours=within_hours)
    seen_links: set[str] = set()
    candidates: list[Candidate] = []
    last_error: str | None = None

    for url in feed_urls:
        try:
            parsed = _fetch_feed(url)
        except Exception as exc:  # feed can fail for many reasons; keep going
            last_error = f"{url}: {exc}"
            continue

        if parsed.bozo and not parsed.entries:
            last_error = f"{url}: unparseable feed ({parsed.bozo_exception})"
            continue

        for entry in parsed.entries:
            link = entry.get("link", "")
            title = entry.get("title", "").strip()
            if not title or not link or link in seen_links:
                continue

            published = _parse_published(entry)
            if published and published < cutoff:
                continue

            seen_links.add(link)
            candidates.append(
                Candidate(
                    outlet=outlet,
                    title=title,
                    link=link,
                    summary=entry.get("summary", "").strip(),
                    published=published,
                )
            )

    error = last_error if not candidates else None
    return candidates, error


def fetch_all(within_hours: int = 36) -> FetchResult:
    result = FetchResult()
    for outlet, feed_urls in OUTLET_FEEDS.items():
        candidates, error = fetch_outlet(outlet, feed_urls, within_hours=within_hours)
        result.candidates.extend(candidates)
        if error:
            result.errors[outlet] = error
    return result
