# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `ann_app/parse.py` — structured parser that turns a `headlines-YYYY-MM-DD.md`
  digest into typed outlet/headline objects, plus a helper to locate the latest
  digest.
- `streamlit_app.py` — a Streamlit dashboard with a DTS-style dark UI that
  rotates every headline in the main window, 10 seconds each, with no repeats
  until all headlines in the digest have been shown.
- OSS repository infrastructure: MIT `LICENSE`, `NOTICE` (attribution to the
  original concept author), `CONTRIBUTING`, `CODE_OF_CONDUCT`, `SECURITY`,
  Dockerfile, `docker-compose.yml`, and GitHub Actions CI/CD.
- Project documentation under `docs/` (architecture, development, dev-ops).
- Parser and filter test coverage.

### Changed
- Hardened `ann_app/filter._parse_response` to extract JSON from fenced code
  blocks with surrounding prose and from bare `{...}` objects embedded in text.

## [0.1.0] - 2026-07-02

### Added
- Initial CLI (`ann.py`): fetch candidate headlines from outlet RSS feeds,
  filter to the five most significant per outlet via Claude, and render the
  daily `headlines-YYYY-MM-DD.md` digest.
