# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `ann_app/resolve.py` — resolves selected AP headlines from opaque
  `news.google.com/rss/articles/...` redirect links to canonical `apnews.com`
  article URLs via Google's `batchexecute` endpoint. Runs on selected headlines
  only (two requests per link, per-run cached), degrades gracefully to the
  original link on failure, and can be disabled with `ANN_RESOLVE_URLS=0`.
- `.github/workflows/daily-digest.yml` — scheduled GitHub Actions workflow that
  runs `ann.py run` daily at 11:00 UTC (and on manual `workflow_dispatch`),
  commits the new `headlines-YYYY-MM-DD.md` + README link as `ann-bot`, and
  pushes. The digest commit carries `[skip ci]` to avoid retriggering CI.
- `ann.py run` now refuses to write an empty digest: if zero headlines are
  selected it exits non-zero and writes nothing, so a failed scheduled run
  commits nothing.
- `ann_app/parse.py` — structured parser that turns a `headlines-YYYY-MM-DD.md`
  digest into typed outlet/headline objects, plus a helper to locate the latest
  digest.
- `streamlit_app.py` — a Streamlit dashboard with an ANN-style dark UI that
  rotates every headline in the main window, 10 seconds each, with no repeats
  until all headlines in the digest have been shown.
- OSS repository infrastructure: MIT `LICENSE`, `NOTICE` (attribution to the
  original concept author), `CONTRIBUTING`, `CODE_OF_CONDUCT`, `SECURITY`,
  Dockerfile, `docker-compose.yml`, and GitHub Actions CI/CD.
- Project documentation under `docs/` (architecture, development, dev-ops).
- Parser, filter, and fetch test coverage.
- `fetch._clean_google_news_title` strips the trailing `" - <Publisher>"`
  suffix that Google News search RSS appends to every entry title (used for
  the AP feed).
- `fetch._fetch_feed` now retries transient network failures (2 retries with
  linear backoff) and reuses a pooled `requests.Session` across all feeds.

### Changed
- `fetch.fetch_outlet` now deduplicates by normalized title in addition to
  link, so the same story appearing across an outlet's overlapping feeds
  (e.g. WSJ World + US + Markets) is only sent to the model once.
- Hardened `ann_app/filter._parse_response` to extract JSON from fenced code
  blocks with surrounding prose and from bare `{...}` objects embedded in text.
- `render.render_markdown` now derives the short-outlet note threshold from
  `HEADLINES_PER_OUTLET` instead of a hardcoded `5`.

### Fixed
- Escaped RSS-sourced headline titles and validated link schemes (http/https
  only) in the Streamlit dashboard, closing an HTML/script injection vector in
  both the rotating hero component and the outlet cards.
- Replaced the Refresh button's `on_click=st.rerun` callback (a no-op/error in
  modern Streamlit) with a guarded `st.rerun()` on button press.

## [0.1.0] - 2026-07-02

### Added
- Initial CLI (`ann.py`): fetch candidate headlines from outlet RSS feeds,
  filter to the five most significant per outlet via Claude, and render the
  daily `headlines-YYYY-MM-DD.md` digest.
