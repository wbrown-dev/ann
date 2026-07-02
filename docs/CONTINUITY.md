# Continuity & Development Roadmap

Living plan for finishing ANN beyond its core pipeline. Each numbered session is
scoped to be completable in a single working session. Sessions are ordered by
priority but are mostly independent — pick the next one, or reorder as needed.

## Current state (2026-07-02)

- **Core pipeline complete:** fetch (`ann_app/fetch.py`) -> Claude filter,
  index-only/no-fabrication (`ann_app/filter.py`) -> render
  (`ann_app/render.py`) -> `headlines-YYYY-MM-DD.md` -> Streamlit dashboard
  (`streamlit_app.py`).
- **Quality gate:** 28 tests passing, ruff clean. CI/CD green (lint + test
  matrix + Docker build/health smoke). Dockerized (`docker compose up` -> :8501).
  Daily digest automated via `.github/workflows/daily-digest.yml` (Session 4).
- **Latest commit:** `cdf7f4e` on `origin/main` (dashboard XSS hardening,
  cross-feed title dedup, transient-fetch retry).
- **No open bugs or code TODOs.** Everything below is enhancement or ops work.

Run tests with `.venv/bin/python -m pytest` (system Python 3.14 lacks
`feedparser`).

## Priority summary

| # | Session | Priority | Type | Rough effort |
|---|---------|----------|------|--------------|
| 4 | Daily automation (scheduled digest) | P0 | Ops | S |
| 5 | Google News -> canonical AP URLs | P0 | Quality | M (spike first) |
| 6 | Candidate caching + deterministic filter tests | P1 | Testability | M |
| 7 | Optional extra outlets behind config flag | P2 | Feature | S |
| 8 | Weekly "what still mattered" retrospective | P2 | Feature | M |
| 9 | Dashboard auto-refresh + polish (minors) | P3 | Polish | S |

Rationale for ordering: automation is what makes ANN a *daily* product rather
than a manual script (P0 functional gap). AP URL resolution is the clearest
*reader-facing* quality gap (P0). Caching unlocks real test coverage of the one
untested step (P1). Extra outlets and the retrospective are additive features
(P2). Auto-refresh and small polish items are last (P3).

---

## Session 4 - Daily automation (scheduled digest)

**Goal:** ANN generates today's digest automatically each day without a human
running the CLI.

**Rationale:** The product is a *daily* digest, but nothing currently runs
`ann.py run` on a schedule. This is the biggest functional gap.

**Approach:** GitHub Actions scheduled workflow (`cron`) that runs `ann.py run`,
commits the new `headlines-YYYY-MM-DD.md` + README link update, and pushes.
`ANTHROPIC_API_KEY` supplied as a repo secret. (Alternative for local-only:
launchd plist — document but do not default to it.)

**Files:**
- `.github/workflows/daily-digest.yml` (new)
- `docs/DEVOPS.md` (document the schedule, secret, and manual re-run)

**Tasks:**
- [x] Add scheduled workflow (pick a fixed UTC time; document the local
      equivalent).
- [x] Configure `ANTHROPIC_API_KEY` as a GitHub Actions secret (document; the
      secret itself is set by the maintainer, not committed).
- [x] Commit + push the generated digest from the workflow (bot identity,
      `[skip ci]` on the digest commit to avoid loops).
- [x] Add a `workflow_dispatch` trigger for manual runs.
- [x] Guard against empty/failed generation (do not commit an empty digest;
      fail the job with a clear message).

**Status:** Done (commit `567968c`). Shipped
`.github/workflows/daily-digest.yml` (cron `0 11 * * *` + `workflow_dispatch`,
`[skip ci]` digest commits as `ann-bot`) and an empty-digest guard in `ann.py`
(exit code 2, writes nothing). 28 tests passing (was 26); DEVOPS.md documents
schedule, secret, manual re-run, and launchd alternative.

**Acceptance criteria:**
- Workflow runs on schedule and on manual dispatch.
- A successful run produces a committed `headlines-YYYY-MM-DD.md` and updated
  README link.
- A failed fetch/model call fails the job loudly and commits nothing.
- No secret is ever printed in logs.

**Risks / notes:** avoid CI loops (digest commit must not retrigger the digest
workflow); handle the API key securely; consider cost of a daily model call.

---

## Session 5 - Google News -> canonical AP URLs

**Goal:** AP headlines link to canonical `apnews.com` article URLs instead of
opaque `news.google.com/rss/articles/...` redirect URLs.

**Rationale:** Clearest reader-facing quality gap. Current AP links are opaque
and carry Google tracking.

**Important:** Google changed the Google News RSS article URL encoding in 2024;
the old base64 decode no longer works and now requires a resolving request to a
Google endpoint. **Start with a timeboxed spike** to determine whether reliable
resolution is feasible before committing to full implementation.

**Files:**
- `ann_app/fetch.py` (resolution helper + wire into AP path)
- `ann_app/config.py` (feature flag / toggle if resolution is opt-in)
- `tests/test_fetch.py` (tests for the resolver with mocked responses)
- `docs/DEVELOPMENT.md` (remove from R&D once shipped; document limitations)

**Tasks:**
- [x] Spike: confirm a reliable method to resolve a Google News RSS link to its
      canonical publisher URL (document findings even if negative).
- [x] If feasible: add `_resolve_google_news_url(link)` with timeout + graceful
      fallback to the original link on failure.
- [x] Apply only to Google-News-sourced entries (AP); leave direct feeds
      untouched.
- [x] Cache/deduplicate resolution within a run to limit extra requests.
- [x] Tests: successful resolution, failure fallback, non-Google links pass
      through unchanged.

**Status:** Done (commit `5f0f4f6`). Spike was positive: the post-2024
Google News scheme resolves via the article page's `data-n-a-{id,sg,ts}` tokens
plus one `batchexecute` RPC. Shipped `ann_app/resolve.py`
(`resolve_google_news_url` + `resolve_selection`), wired into `ann.py` after
selection so only the <=5 selected AP links are resolved (two requests each,
per-run cached). Graceful fallback to the original link on any error; kill
switch `ANN_RESOLVE_URLS=0`. 37 tests passing (was 28). Verified live: real AP
entries resolve to `apnews.com/article/...`.

**Acceptance criteria:**
- AP digest entries link to `apnews.com` (or the canonical publisher) when
  resolution succeeds.
- On resolution failure or timeout, the original link is used and the run still
  succeeds.
- No unbounded latency added (bounded timeout + retries reuse existing policy).

**Risks / notes:** resolution may be fragile or rate-limited; must degrade
gracefully. If the spike shows it is not reliably feasible, document that
conclusion and close this session as "won't do (blocked upstream)".

---

## Session 6 - Candidate caching + deterministic filter tests

**Goal:** Cache fetched candidates so runs are replayable offline, and give
`filter.select_headlines` real test coverage.

**Rationale:** The model-selection step is currently untested against the
network by design, leaving the one behaviorally-critical step uncovered.
Caching enables deterministic replay and testing without live network or API
calls.

**Files:**
- `ann_app/fetch.py` or new `ann_app/cache.py` (write/read a candidates
  snapshot, e.g. JSON keyed by date)
- `ann.py` (flags: `--use-cache` / `--save-cache` or similar)
- `ann_app/filter.py` (make the client injectable / mockable if not already)
- `tests/test_filter.py` (drive `select_headlines` with a stubbed client and a
  cached candidate set; assert index-only, no-fabrication, ranking, truncation
  to `HEADLINES_PER_OUTLET`, out-of-range index rejection)

**Tasks:**
- [x] Define a serializable candidate snapshot format (round-trips `Candidate`).
- [x] Add save/load of candidates keyed by date to a cache dir (gitignored).
- [x] CLI flags to save on fetch and to run from cache without fetching.
- [x] Make the Anthropic client injectable so tests can stub the response.
- [x] Add filter tests covering selection, ranking, bounds, and truncation.

**Status:** Done (commit `541270e`). Shipped `ann_app/cache.py` (versioned JSON
snapshot keyed by date, round-trips `Candidate` incl. `published`; stale/missing
caches raise `CacheError`). `ann.py run` gained mutually-exclusive
`--save-cache` / `--use-cache`; `.cache/` gitignored. `filter.select_headlines`
now takes an optional injectable `client`, enabling stubbed-model tests of
selection, ranking, truncation to `HEADLINES_PER_OUTLET`, and out-of-range /
non-int index rejection. New `tests/test_cache.py` (3) + filter (4) + run (1) →
**45 tests passing** (was 37); ruff clean.

**Acceptance criteria:**
- `ann.py run --use-cache` produces a digest without any network fetch.
- New tests exercise `select_headlines` end-to-end with a stubbed model.
- Test count increases; ruff clean.

**Risks / notes:** keep cache files out of git; ensure cache format versioned so
stale caches fail clearly rather than silently.

---

## Session 7 - Optional extra outlets behind a config flag

**Goal:** Allow additional outlets (e.g. Reuters, Bloomberg, FT) to be enabled
without changing the default four.

**Rationale:** Additive, low-risk feature; broadens coverage for users who want
it while keeping the curated default lean.

**Files:**
- `ann_app/config.py` (extra-outlet feed definitions + enable mechanism, e.g.
  `ANN_EXTRA_OUTLETS` env var or config toggle)
- `ann_app/render.py` / `streamlit_app.py` (accent colors + display names for
  any enabled extra outlets)
- `tests/` (config resolution: default set vs. extended set)
- `docs/DEVELOPMENT.md` (document how to enable extra outlets)

**Tasks:**
- [x] Add feed URLs for the candidate extra outlets (verify each RSS is live).
- [x] Add an opt-in mechanism (default remains the current four).
- [x] Ensure display names + accent colors exist for enabled outlets.
- [x] Tests for enabled vs. disabled resolution.

**Status:** Done (commit `b72201c`). Shipped `ANN_EXTRA_OUTLETS` (comma-
separated, case-insensitive) enabling any of `GUARDIAN`/`BBC`/`NPR` on top of
the default four; unknown names ignored. Live RSS verified for all three
(Guardian 45 / BBC 36 / NPR 10 items). Config now exposes
`DEFAULT_/EXTRA_OUTLET_{FEEDS,DISPLAY_NAMES,ACCENTS}` plus a pure
`resolve_outlet_config` helper; `OUTLET_ACCENTS` moved from `streamlit_app.py`
into `ann_app/config.py` so extras get colors through the dashboard. New
`tests/test_config.py` (7) + a render test for an enabled extra (+1) →
**53 tests passing** (was 45); ruff clean. Chose clean direct-RSS outlets over
Reuters/Bloomberg (which only exist as opaque Google News redirects and are not
resolved outside the AP path).

**Acceptance criteria:**
- Default behavior unchanged (four outlets).
- Enabling extra outlets adds them through the full pipeline (fetch -> filter
  -> render -> dashboard) with correct labels/colors.

**Risks / notes:** paywalled outlets (WSJ/FT/Bloomberg) may have thin or
truncated RSS; verify each feed actually yields usable candidates.

---

## Session 8 - Weekly "what still mattered" retrospective

**Goal:** A weekly digest built from the past ~7 daily digests highlighting the
stories that proved durably significant.

**Rationale:** Directly expresses the project thesis ("significant in 30 days,
not viral today") and reuses existing digest history.

**Files:**
- `ann_app/retrospective.py` (new: load recent digests, dedupe/cluster,
  re-rank)
- `ann.py` (new subcommand, e.g. `ann.py retro`)
- `ann_app/parse.py` (reuse `parse_digest` / add multi-file loading helper)
- `streamlit_app.py` (optional: a retrospective view/tab)
- `tests/` (retrospective assembly from fixture digests)
- `docs/` (document the feature)

**Tasks:**
- [ ] Load the last N daily digests via existing parser.
- [ ] Cluster/dedupe recurring stories across days (normalized-title reuse from
      `fetch._normalize_title`).
- [ ] Produce a ranked weekly summary (model-assisted re-ranking optional,
      index-only to preserve no-fabrication guarantee).
- [ ] Write `retrospective-YYYY-Www.md` (or similar) + optional dashboard view.
- [ ] Tests over fixture digests (no network).

**Acceptance criteria:**
- `ann.py retro` produces a weekly retrospective file from existing digests.
- No fabrication: every item traces to a real prior digest headline.
- Tests cover assembly from fixtures.

**Risks / notes:** define "week" boundary and minimum-digests threshold; decide
whether re-ranking uses the model or pure heuristics (keep no-fabrication
guarantee either way).

---

## Session 9 - Dashboard auto-refresh + polish (minors)

**Goal:** Small quality-of-life improvements; clear the minor backlog.

**Rationale:** Low-priority polish, batched into one session.

**Items:**
- [ ] Dashboard auto-refreshes (or clearly signals) when a newer digest lands,
      rather than requiring the manual Refresh button.
- [ ] Any small UX/copy fixes discovered during earlier sessions.
- [ ] Revisit `docs/DEVELOPMENT.md` R&D list and prune anything now shipped.

**Acceptance criteria:**
- Dashboard reflects a newly generated digest without a manual full restart
  (auto-detect newest `headlines-*.md`).
- R&D notes in docs match reality.

**Risks / notes:** keep auto-refresh cheap (poll newest file mtime; avoid heavy
reruns). Streamlit rerun semantics — verify no flicker in the rotation
component.

---

## How to use this doc

1. Pick the top unfinished session (or the next by priority).
2. Complete its tasks; satisfy the acceptance criteria; keep tests green
   (>= current count) and ruff clean.
3. Update `CHANGELOG.md` under `[Unreleased]`.
4. Check the session's boxes here and note the commit hash.
5. Update `memory/ann_status.md` with the new state.
6. Commit at the end of every session (this is mandatory, not optional); push
   when confirmed.
