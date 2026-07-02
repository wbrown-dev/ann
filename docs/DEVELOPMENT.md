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

New behavior should ship with tests. `ann_app/fetch.py` and the live model call
in `ann_app/filter.py` are intentionally not unit-tested against the network;
test the pure functions (`_parse_response`, `render_markdown`, `parse_digest`)
instead.

## Environment safety

- Never run `source .env`; the app loads it via `python-dotenv`.
- Never commit `.env` or print secrets in logs.

## R&D notes

Areas open for exploration:

- Resolving Google News redirect URLs to canonical `apnews.com` links.
- Optional additional outlets (Reuters, Bloomberg, FT) behind a config flag.
- Caching fetched candidates to make repeated runs deterministic for testing.
- A weekly "what still mattered" retrospective built from past digests.
