# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-07-10

Production-readiness release: completes the security review that `0.3.0` left
open and reshapes the container from a development convenience into a
deployable, immutable artifact.

### Security
- **Fixed a stored XSS in the dashboard.** `_dashboard_component` interpolated
  `json.dumps(headlines)` directly into a `<script>` block. The HTML tokenizer
  terminates a script element at a literal `</script>` even inside a JavaScript
  string, and `json.dumps` escapes neither `<` nor `/`, so a feed title
  containing `</script>` could close the tag and inject markup. The surrounding
  `textContent` writes did not protect this sink. All script-context values now
  go through `_script_json`, which escapes `<`, `>`, and `&`.
- The Google News resolver now requires the exact `https://news.google.com`
  origin (scheme *and* host) before issuing a request, and validates that the
  resolved publisher URL is `http`/`https` before it is adopted, falling back to
  the original link otherwise.
- Added `tests/test_security.py`: regression coverage for script-context
  escaping, `_safe_url` / `_safe_markdown_url` scheme allowlists, markdown link
  escaping, the resolver host allowlist, and feedparser's external-entity
  posture, so a refactor cannot silently drop these protections.
- Confirmed the pinned `feedparser` does not resolve external entities (XXE),
  and locked that behavior in with a test.
- Runtime dependencies are pinned to exact versions for reproducible builds. CI
  gained a `pip-audit` job over `requirements.txt`.

### Added
- `ANN_DIGEST_DIR` selects where generated `headlines-*.md` and
  `retrospective-*.md` files are written and read. It defaults to the repo root,
  so local use is unchanged; containers point it at a mounted volume.
- A `digest` Compose service (`docker compose run --rm digest`) generates a
  digest into the same volume the dashboard reads.

### Changed
- **The container is now production-shaped.** It runs as a non-root user
  (uid `10001`), installs runtime dependencies only (`pytest` and `ruff` no
  longer ship in the image), and no longer bakes digests into image layers.
  Compose runs it with a read-only root filesystem, `cap_drop: ALL`,
  `no-new-privileges`, and memory/PID limits.
- Compose no longer bind-mounts the working tree over `/app`. That mount made
  the image mutable at runtime and exposed `.env` to the container; digests now
  live on a named `ann-digests` volume.
- `ann.py run` only rewrites the README link when a README is present, so a
  container writing into a mounted digest volume no longer requires a checkout.
- Dev and test tooling moved to `requirements-dev.txt`; CI installs that.
- CI asserts the image runs as non-root and contains no test tooling.

### Fixed
- The test suite no longer writes generated digests into the repository root
  when exercising `ann.run`.

## [0.3.0] - 2026-07-02

### Added
- Google Gemini as a third model provider for index-only selection. Set
  `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) and run with `ANN_MODEL_PROVIDER=gemini`
  or `--model-provider gemini`; the default model is `gemini-2.5-flash`. The
  Gemini adapter in `ann_app/providers.py` calls `models.generate_content` and
  returns raw text only, so `filter._parse_response` remains the single
  validation gate and the no-fabrication guarantee is preserved. Keys stay
  env-only and are never persisted.
- The daily-digest GitHub Actions workflow now recognizes `gemini`: the provider
  validation step accepts it and requires `GEMINI_API_KEY` (or `GOOGLE_API_KEY`),
  and both the validation and generate steps inject those secrets. DEVOPS.md and
  DEVELOPMENT.md document the Gemini secret, repository variable, and Docker run
  invocation alongside the existing providers.

### Fixed
- Disabled Gemini thinking (`thinking_config.thinking_budget = 0`) for
  index-only selection. `gemini-2.5-flash` is a thinking model whose reasoning
  tokens count against `max_output_tokens`; with the default budget those tokens
  could consume the entire allowance and return empty text, causing the selection
  parse to fail and no digest to be written. Selection needs no reasoning, so
  thinking is turned off.

## [0.2.0] - 2026-07-02

### Added
- Optional provider-assisted retrospective re-ranking. `ann.py retro
  --rerank-model` sends clustered retrospective stories to the configured model
  as numbered candidates and accepts only a `{"stories": [...]}` index list.
  ANN resolves those indices back to existing story objects, ignores invalid or
  duplicate indices, appends omitted stories in heuristic order, and renders the
  original prior-digest headline text and links unchanged. `--model-provider`
  and `--model` are available on `retro` for this opt-in model call.
- The Streamlit dashboard now has separate tabs for the daily headline rotation
  and the latest `retrospective-*.md` weekly retrospective. The dashboard
  auto-checks both file families for filename or mtime changes, and
  retrospective parsing preserves the generated verbatim headline text,
  metadata, dates, and source links without rewriting story content.
- Model/provider flexibility for daily headline selection. `ANN_MODEL_PROVIDER`
  or `ann.py run --model-provider` can select `anthropic` or `openai`, with
  `ANN_MODEL` / `--model` controlling the model name. Provider-specific SDK
  calls live behind `ann_app/providers.py`, while `filter.select_headlines`
  still accepts only normalized model text and resolves selections back to
  candidate indices. Missing keys and malformed provider JSON fail clearly
  before writing a digest; tests use stub clients only.
- The Streamlit dashboard now auto-checks the latest `headlines-*.md` digest
  every 30 seconds using a timed fragment. It tracks both filename and mtime, so
  a newly generated digest or an overwritten current-day digest is reflected
  without using the manual Refresh button or restarting the dashboard.
- `ann_app/retrospective.py` + `ann.py retro` — a weekly "what still mattered"
  digest built from the recent daily `headlines-YYYY-MM-DD.md` files. Headlines
  are clustered into stories by salient-token overlap (reusing
  `fetch._normalize_title`) and ranked by how many distinct days each story
  appeared, then by best daily rank — a pure, deterministic, offline heuristic
  (no model call). Writes `retrospective-YYYY-Www.md` (ISO year-week of the
  newest digest); `--days`, `--top`, and `--dry-run` flags. Every line is a
  verbatim headline carried from a real prior digest (no fabrication); the
  command refuses to write with fewer than two recent digests or no stories.
- Optional extra outlets behind a config flag. `ANN_EXTRA_OUTLETS` (comma-
  separated, case-insensitive) enables any of `GUARDIAN`, `BBC`, `NPR` on top of
  the default four (WSJ/NYT/NBC/AP); unknown names are ignored. Each extra has a
  live, non-paywalled RSS feed plus a display name and accent color, and flows
  through the full pipeline (fetch -> filter -> render -> dashboard). Config
  resolution is a pure `resolve_outlet_config` helper; `OUTLET_ACCENTS` now lives
  in `ann_app/config.py` (imported by the dashboard) so extras get colors too.
- `ann_app/cache.py` — versioned JSON snapshot of fetched candidates keyed by
  date (round-trips `Candidate`, including the `published` timestamp). Stale or
  mismatched cache versions fail loudly instead of silently. `ann.py run
  --save-cache` writes the snapshot after fetch; `ann.py run --use-cache`
  replays a digest entirely offline with no network fetch. The two flags are
  mutually exclusive and the `.cache/` dir is gitignored.
- `ann_app/filter.select_headlines` now accepts an injectable Anthropic
  `client`, enabling deterministic tests of selection, ranking, truncation, and
  index-bounds/type rejection against a stubbed model (no live network or key).
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
- Bumped project metadata to `0.2.0` and expanded Dev-Ops release/production
  documentation with a scheduled digest readiness checklist.
- The daily digest workflow now validates the selected provider and required
  secret before fetching feeds, and passes optional `ANN_EXTRA_OUTLETS` through
  from repository variables for scheduled production runs.
- Refreshed the resume prompt and continuity/status verification baseline now
  that Session 12 is shipped and the test suite contains 83 tests.
- Compressed completed continuity docs into a final-state archive, updated the
  resume prompt for post-roadmap work, and refreshed architecture docs to cover
  the shipped cache, resolver, retrospective, and auto-refresh components.
- `fetch.fetch_outlet` now deduplicates by normalized title in addition to
  link, so the same story appearing across an outlet's overlapping feeds
  (e.g. WSJ World + US + Markets) is only sent to the model once.
- Hardened `ann_app/filter._parse_response` to extract JSON from fenced code
  blocks with surrounding prose and from bare `{...}` objects embedded in text.
- `render.render_markdown` now derives the short-outlet note threshold from
  `HEADLINES_PER_OUTLET` instead of a hardcoded `5`.

### Fixed
- Blank `ANN_MODEL_PROVIDER` or `ANN_MODEL` environment variables now fall back
  to the default provider/model instead of overriding defaults with empty
  strings, matching GitHub Actions behavior for unset repository variables.
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
