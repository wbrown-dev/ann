# Dev-Ops

## Continuous integration

CI runs on every push and pull request to `main`
([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)):

1. **lint-and-test** — on Python 3.11 and 3.12: `ruff check .` then
   `pytest -q`.
2. **docker** — builds the image with Buildx (GitHub Actions layer cache),
   starts the container, and polls Streamlit's `/_stcore/health` endpoint to
   prove the app boots.

## Scheduled daily digest

The digest is generated automatically by
[`.github/workflows/daily-digest.yml`](../.github/workflows/daily-digest.yml):

- **Schedule:** `cron: "0 11 * * *"` — 11:00 UTC daily (06:00 US Eastern /
  03:00 US Pacific). The 36-hour default lookback window keeps timing
  non-critical. Adjust the cron line to move the run.
- **Manual re-run:** the workflow also exposes `workflow_dispatch`, so a
  maintainer can trigger it from the Actions tab at any time.
- **What it does:** installs deps, runs `python ann.py run`, then stages the new
  `headlines-YYYY-MM-DD.md` and the updated `README.md` link and pushes them as
  `ann-bot`.
- **Failure is loud and safe:** `ann.py run` exits non-zero on a fetch/model
  failure or when zero headlines are selected (it refuses to write an empty
  digest). A non-zero exit stops the job before the commit step, so a failed run
  commits nothing.
- **No CI loop:** the digest commit message ends with `[skip ci]`, and
  `daily-digest.yml` is not triggered by `push`, so the generated commit does not
  retrigger CI or the digest workflow.

### Required secret

The workflow needs the API key for the selected provider as a repository
Actions secret (Settings -> Secrets and variables -> Actions -> New repository
secret): `ANTHROPIC_API_KEY` for the default Anthropic provider,
`OPENAI_API_KEY` when `ANN_MODEL_PROVIDER=openai`, or `GEMINI_API_KEY` (or
`GOOGLE_API_KEY`) when `ANN_MODEL_PROVIDER=gemini`. Optional repository
variables `ANN_MODEL_PROVIDER` and `ANN_MODEL` can switch provider/model without
editing source, and optional variable `ANN_EXTRA_OUTLETS` can enable
`GUARDIAN`, `BBC`, and/or `NPR` for scheduled production runs. Secrets are
injected into workflow steps via `env:` and masked by GitHub in logs; they are
never committed and never printed by `ann.py`.

The workflow validates the selected provider and required secret immediately
after dependency installation. If the selected provider is unsupported or its
secret is missing, the job exits before fetching feeds or attempting a model
call.

Blank `ANN_MODEL_PROVIDER` or `ANN_MODEL` variables are treated the same as
unset variables, so the scheduled workflow safely falls back to Anthropic and
`claude-sonnet-5` unless a maintainer explicitly configures another provider or
model.

### Production readiness checklist

Before relying on the scheduled digest:

1. Confirm Actions are enabled for the repository.
2. Add one provider secret: `ANTHROPIC_API_KEY` for the default provider,
   `OPENAI_API_KEY` plus repository variable `ANN_MODEL_PROVIDER=openai`, or
   `GEMINI_API_KEY` plus repository variable `ANN_MODEL_PROVIDER=gemini`.
3. Optionally set repository variable `ANN_MODEL` to pin a specific model.
4. Optionally set `ANN_EXTRA_OUTLETS` in the workflow if production should
   include `GUARDIAN`, `BBC`, or `NPR` beyond the default four outlets.
5. Run the `Daily digest` workflow manually from the Actions tab.
6. Confirm the run commits a new `headlines-YYYY-MM-DD.md` file and updates the
   README headline link, or exits before the commit step with a clear error.
7. Confirm CI remains green after the digest commit.

### Local alternative (launchd)

For a local-only cadence instead of GitHub Actions, schedule
`~/.venv/bin/python ann.py run` from the repo root with a launchd agent (macOS)
or cron (Linux) at the equivalent local time. This is documented as an option;
the shipped default is the GitHub Actions workflow above.

## Container

The image is defined in [`Dockerfile`](../Dockerfile):

- Base: `python:3.12-slim`.
- Installs `requirements.txt` (runtime only — `pytest` and `ruff` live in
  `requirements-dev.txt` and never enter the image) and copies the app.
- Runs as non-root user `ann` (uid `10001`).
- Runs Streamlit headless on port **8501** with a container `HEALTHCHECK`
  against `/_stcore/health`.

### Digests are runtime state, not image layers

Generated `headlines-*.md` and `retrospective-*.md` files live in the directory
named by `ANN_DIGEST_DIR`. It defaults to the repo root for local use; the image
sets it to `/data`, which Compose backs with the named `ann-digests` volume.

This keeps the image immutable: the source tree is never bind-mounted over
`/app` (which would also expose `.env` to the container), and digests are never
baked into layers. `ann.py run` skips the README link update when no README is
present, so a container writing into `/data` does not need a checkout.

### Runtime hardening

Compose runs the dashboard with a read-only root filesystem, `cap_drop: ALL`,
`no-new-privileges`, `mem_limit`, and `pids_limit`. Streamlit's writable scratch
(`/tmp`, `/home/ann/.streamlit`) is provided by `tmpfs`. CI additionally asserts
that the image runs as uid `10001` and that `pytest` is not importable inside it.

### Build and run locally

```bash
docker build -t ann:latest .
docker run --rm -p 8501:8501 -e ANTHROPIC_API_KEY=sk-... ann:latest
```

For OpenAI:

```bash
docker run --rm -p 8501:8501 \
  -e ANN_MODEL_PROVIDER=openai \
  -e ANN_MODEL=gpt-4.1-mini \
  -e OPENAI_API_KEY=sk-... \
  ann:latest
```

For Gemini:

```bash
docker run --rm -p 8501:8501 \
  -e ANN_MODEL_PROVIDER=gemini \
  -e ANN_MODEL=gemini-2.5-flash \
  -e GEMINI_API_KEY=... \
  ann:latest
```

Or with Compose (digests persist on the `ann-digests` volume):

```bash
export ANTHROPIC_API_KEY=sk-...
docker compose up --build
```

App: <http://localhost:8501>

### Generating a digest inside the container

The `digest` service writes into the same volume the dashboard reads:

```bash
docker compose run --rm digest
```

### CI container checks

The `docker` job builds the image, asserts it does not run as root, asserts test
tooling is absent, then starts it and polls `/_stcore/health`. A separate
`audit` job runs `pip-audit` against the pinned `requirements.txt`.

## Secrets

- Provider secrets are `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, and/or
  `GEMINI_API_KEY` (or `GOOGLE_API_KEY`), injected via environment variables.
- Never bake secrets into the image; `.env` is git-ignored and excluded from the
  build context via `.dockerignore`.

## Releases

- Update [`CHANGELOG.md`](../CHANGELOG.md), move shipped entries from
  `[Unreleased]` into a dated version section, and bump
  [`pyproject.toml`](../pyproject.toml).
- Run `.venv/bin/python -m pytest` and `.venv/bin/ruff check .`.
- Commit the release prep with a clear message.
- Create an annotated tag:

  ```bash
  git tag -a vX.Y.Z -m "ANN vX.Y.Z"
  ```

- Push the branch and tag:

  ```bash
  git push origin main
  git push origin vX.Y.Z
  ```

Digest files are data snapshots, not release artifacts.
