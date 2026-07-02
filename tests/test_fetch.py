from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
import requests

import ann_app.fetch as fetch
from ann_app.fetch import (
    _clean_google_news_title,
    _fetch_feed,
    _normalize_title,
    fetch_outlet,
)


def _feed(entries):
    return SimpleNamespace(bozo=0, bozo_exception=None, entries=entries)


def _recent_struct():
    return datetime.now(UTC).timetuple()


def test_clean_google_news_title_strips_publisher_suffix():
    assert _clean_google_news_title("Big story - The Associated Press") == "Big story"


def test_clean_google_news_title_keeps_hyphenated_headline_without_suffix():
    assert _clean_google_news_title("No suffix here") == "No suffix here"


def test_clean_google_news_title_does_not_empty_title():
    assert _clean_google_news_title(" - AP") == " - AP"


def test_fetch_outlet_dedupes_and_applies_google_cleanup(monkeypatch):
    entries = [
        {"link": "https://x/1", "title": "Alpha - AP News", "published_parsed": _recent_struct()},
        {"link": "https://x/1", "title": "Alpha dup", "published_parsed": _recent_struct()},
        {"link": "https://x/2", "title": "Beta - AP News", "published_parsed": _recent_struct()},
    ]
    monkeypatch.setattr(fetch, "_fetch_feed", lambda url: _feed(entries))

    candidates, error = fetch_outlet(
        "AP", ["https://news.google.com/rss/search?q=site:apnews.com"], within_hours=36
    )

    assert error is None
    assert [c.title for c in candidates] == ["Alpha", "Beta"]


def test_normalize_title_collapses_whitespace_and_trailing_punctuation():
    assert _normalize_title("  Big   Story!  ") == "big story"
    assert _normalize_title("Big Story") == _normalize_title("big story.")


def test_fetch_outlet_dedupes_same_title_across_overlapping_feeds(monkeypatch):
    world = [{"link": "https://wsj/world/1", "title": "Fed holds rates", "published_parsed": _recent_struct()}]
    markets = [{"link": "https://wsj/markets/9", "title": "Fed holds rates.", "published_parsed": _recent_struct()}]
    feeds = {"https://wsj/world": world, "https://wsj/markets": markets}
    monkeypatch.setattr(fetch, "_fetch_feed", lambda url: _feed(feeds[url]))

    candidates, error = fetch_outlet(
        "WSJ", ["https://wsj/world", "https://wsj/markets"], within_hours=36
    )

    assert error is None
    assert [c.title for c in candidates] == ["Fed holds rates"]


def test_fetch_feed_retries_transient_failures(monkeypatch):
    monkeypatch.setattr(fetch.time, "sleep", lambda _s: None)
    calls = {"n": 0}

    def flaky_get(url, timeout):
        calls["n"] += 1
        if calls["n"] < 3:
            raise requests.ConnectionError("boom")
        return SimpleNamespace(
            content=b"<rss></rss>", raise_for_status=lambda: None
        )

    monkeypatch.setattr(fetch._SESSION, "get", flaky_get)

    _fetch_feed("https://feed.example/rss")
    assert calls["n"] == 3


def test_fetch_feed_raises_after_exhausting_retries(monkeypatch):
    monkeypatch.setattr(fetch.time, "sleep", lambda _s: None)

    def always_fail(url, timeout):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(fetch._SESSION, "get", always_fail)

    with pytest.raises(requests.ConnectionError):
        _fetch_feed("https://feed.example/rss")


def test_fetch_outlet_drops_entries_older_than_cutoff(monkeypatch):
    old = (datetime.now(UTC) - timedelta(hours=100)).timetuple()
    entries = [
        {"link": "https://x/old", "title": "Stale", "published_parsed": old},
        {"link": "https://x/new", "title": "Fresh", "published_parsed": _recent_struct()},
    ]
    monkeypatch.setattr(fetch, "_fetch_feed", lambda url: _feed(entries))

    candidates, error = fetch_outlet("NYT", ["https://rss.example/feed"], within_hours=36)

    assert error is None
    assert [c.title for c in candidates] == ["Fresh"]


def test_fetch_outlet_records_error_when_all_feeds_fail(monkeypatch):
    def boom(url):
        raise RuntimeError("network down")

    monkeypatch.setattr(fetch, "_fetch_feed", boom)

    candidates, error = fetch_outlet("WSJ", ["https://rss.example/feed"], within_hours=36)

    assert candidates == []
    assert error is not None and "network down" in error
