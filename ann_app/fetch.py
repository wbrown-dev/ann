from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import feedparser
import requests

from ann_app.config import (
    OUTLET_FEEDS,
    REQUEST_TIMEOUT_SECONDS,
    USER_AGENT,
)

FEED_FETCH_RETRIES = 2
FEED_RETRY_BACKOFF_SECONDS = 0.5

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": USER_AGENT})

_WS = re.compile(r"\s+")


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


def _clean_google_news_title(title: str) -> str:
    """Google News search RSS appends ' - <Publisher>' to every entry title."""
    head, sep, _tail = title.rpartition(" - ")
    return head.strip() if sep and head.strip() else title


def _normalize_title(title: str) -> str:
    """Collapse a title to a comparison key so the same story surfacing across an
    outlet's overlapping feeds (e.g. WSJ World + US + Markets) is not sent twice."""
    return _WS.sub(" ", title).strip().lower().rstrip(".!?…")


def _parse_published(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return datetime(*value[:6], tzinfo=UTC)
    return None


def _fetch_feed(url: str) -> feedparser.FeedParserDict:
    last_exc: Exception | None = None
    for attempt in range(FEED_FETCH_RETRIES + 1):
        try:
            response = _SESSION.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            return feedparser.parse(response.content)
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < FEED_FETCH_RETRIES:
                time.sleep(FEED_RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise last_exc  # type: ignore[misc]


def fetch_outlet(outlet: str, feed_urls: list[str], within_hours: int = 36) -> tuple[list[Candidate], str | None]:
    cutoff = datetime.now(UTC) - timedelta(hours=within_hours)
    seen_links: set[str] = set()
    seen_titles: set[str] = set()
    candidates: list[Candidate] = []
    last_error: str | None = None

    for url in feed_urls:
        is_google_news = "news.google.com" in url
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
            if is_google_news:
                title = _clean_google_news_title(title)

            title_key = _normalize_title(title)
            if title_key in seen_titles:
                continue

            published = _parse_published(entry)
            if published and published < cutoff:
                continue

            seen_links.add(link)
            seen_titles.add(title_key)
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
