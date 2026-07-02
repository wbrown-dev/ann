# Development

## Prerequisites

- Python 3.11 or 3.12
- An `ANTHROPIC_API_KEY` (only needed to generate new digests; the dashboard
  can run against an existing digest without one)

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env        # add ANTHROPIC_API_KEY
```

## Generating a digest

```bash
.venv/bin/python ann.py run              # writes headlines-YYYY-MM-DD.md, updates README link
.venv/bin/python ann.py run --dry-run    # prints the digest without writing anything
.venv/bin/python ann.py run --within-hours 24
```

## Running the dashboard

```bash
.venv/bin/streamlit run streamlit_app.py
```

Open http://localhost:8501. The main window rotates through every headline in
the latest digest, 10 seconds each, no repeats until all have been shown.

## Tests and linting

```bash
.venv/bin/python -m pytest        # unit tests
.venv/bin/ruff check .            # lint (install ruff if needed: pip install ruff)
```

New behavior should ship with tests. `ann_app/fetch.py` is intentionally not
unit-tested against the network; test the pure functions (`_parse_response`,
`render_markdown`, `parse_digest`) instead. `filter.select_headlines` accepts an
injectable `client`, so its selection/ranking/bounds logic is tested against a
stubbed model rather than a live API call.

## Candidate caching

`ann.py run --save-cache` writes the fetched candidates to a versioned JSON
snapshot under `.cache/candidates-YYYY-MM-DD.json` (gitignored). `ann.py run
--use-cache` rebuilds a digest from that snapshot without touching the network,
which makes runs replayable offline. The two flags are mutually exclusive. A
missing snapshot or a cache written by an incompatible version fails loudly
(`CacheError`) rather than silently producing a stale or empty digest.

## AP URL resolution

AP has no public RSS feed, so AP candidates come from a Google News query and
arrive as opaque `news.google.com/rss/articles/...` redirect links. After the
model selects headlines, `ann_app/resolve.py` resolves the selected AP links to
their canonical `apnews.com` article URLs via Google's `batchexecute` endpoint
(fetch the article page for a signed token, then one RPC call — two requests per
link, run on selected headlines only).

Resolution degrades gracefully: on any timeout, HTTP error, or scheme change the
original Google News link is used and the run still succeeds. Set
`ANN_RESOLVE_URLS=0` to disable it entirely (kill switch if Google changes the
encoding again). The scheme is undocumented and has changed before (2024), so
treat this as best-effort.

## Environment safety

- Never run `source .env`; the app loads it via `python-dotenv`.
- Never commit `.env` or print secrets in logs.

## R&D notes

Areas open for exploration:

- Optional additional outlets (Reuters, Bloomberg, FT) behind a config flag.
- A weekly "what still mattered" retrospective built from past digests.
