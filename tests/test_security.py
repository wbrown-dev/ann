"""Regression tests for ANN's security boundaries.

These lock in protections that a refactor could silently drop: script-context
escaping in the dashboard, link-scheme allowlists on every rendered URL, the
resolver's host allowlist, and feedparser's external-entity posture.
"""

from __future__ import annotations

import json

import feedparser
import pytest

from ann_app.render import _safe_markdown_url, render_markdown
from ann_app.resolve import _is_google_news_url, _is_safe_resolved_url
from streamlit_app import _safe_url, _script_json


class TestScriptJson:
    def test_closing_script_tag_cannot_break_out(self):
        title = "</script><img src=x onerror=alert(1)>"
        encoded = _script_json([{"title": title}])
        assert "</script>" not in encoded
        assert "<" not in encoded
        assert ">" not in encoded

    def test_ampersand_is_escaped(self):
        assert "&" not in _script_json("a & b")

    def test_js_line_terminators_are_escaped(self):
        encoded = _script_json("a\u2028b\u2029c")
        assert "\u2028" not in encoded
        assert "\u2029" not in encoded

    @pytest.mark.parametrize(
        "value",
        [
            "</script>",
            {"title": "a & b", "link": "https://x/?a=1&b=2"},
            [" ", "<b>", "plain"],
            "quotes \" and ' and \\ backslash",
        ],
    )
    def test_round_trips_to_original_value(self, value):
        """Escaping must be transparent: the browser parses back the exact value."""
        assert json.loads(_script_json(value)) == value


class TestSafeUrl:
    @pytest.mark.parametrize(
        "link",
        [
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "vbscript:msgbox(1)",
            "file:///etc/passwd",
            "https://",  # no netloc
            "",
            None,
        ],
    )
    def test_rejects_dangerous_or_empty_schemes(self, link):
        assert _safe_url(link) is None

    @pytest.mark.parametrize(
        "link",
        ["https://apnews.com/article/x", "http://example.com/a?b=1#c"],
    )
    def test_allows_http_and_https(self, link):
        assert _safe_url(link) == link


class TestSafeMarkdownUrl:
    @pytest.mark.parametrize(
        "link",
        ["javascript:alert(1)", "data:text/html,x", "file:///etc/passwd", "", None],
    )
    def test_rejects_dangerous_schemes(self, link):
        assert _safe_markdown_url(link) is None

    def test_escapes_angle_brackets_that_would_close_the_link(self):
        assert _safe_markdown_url("https://x.test/a>b") == "https://x.test/a%3Eb"


class TestRenderMarkdownEscaping:
    def test_dangerous_link_renders_as_plain_text_not_a_link(self):
        from ann_app.fetch import Candidate

        selections = {"WSJ": [Candidate(outlet="WSJ", title="T", link="javascript:alert(1)")]}
        out = render_markdown(selections, {})
        assert "javascript:" not in out
        assert "1. T" in out

    def test_brackets_in_title_are_escaped(self):
        from ann_app.fetch import Candidate

        selections = {"WSJ": [Candidate(outlet="WSJ", title="a [x](y) b", link="https://x.test/a")]}
        out = render_markdown(selections, {})
        assert r"a \[x\](y) b" in out


class TestResolverHostAllowlist:
    @pytest.mark.parametrize(
        "link",
        [
            "http://news.google.com/rss/articles/x",  # http, not https
            "https://evil.test/news.google.com/x",
            "https://news.google.com.evil.test/x",
            "file://news.google.com/etc/passwd",
            "https://169.254.169.254/latest/meta-data/",
        ],
    )
    def test_only_https_news_google_com_is_resolved(self, link):
        assert _is_google_news_url(link) is False

    def test_canonical_google_news_url_is_resolved(self):
        assert _is_google_news_url("https://news.google.com/rss/articles/x") is True

    @pytest.mark.parametrize(
        "link",
        ["javascript:alert(1)", "file:///etc/passwd", "data:text/html,x", "not-a-url"],
    )
    def test_unsafe_resolved_urls_are_rejected(self, link):
        assert _is_safe_resolved_url(link) is False

    def test_safe_resolved_url_is_accepted(self):
        assert _is_safe_resolved_url("https://apnews.com/article/x") is True


class TestFeedparserExternalEntities:
    def test_xxe_entity_is_not_resolved(self):
        xxe = (
            b'<?xml version="1.0"?>\n'
            b'<!DOCTYPE r [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>\n'
            b'<rss version="2.0"><channel><item>'
            b"<title>&xxe;</title><link>http://x.test/</link>"
            b"</item></channel></rss>"
        )
        parsed = feedparser.parse(xxe)
        titles = [e.get("title", "") for e in parsed.entries]
        assert not any("root:" in t for t in titles)
