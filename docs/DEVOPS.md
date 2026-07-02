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
secret): `ANTHROPIC_API_KEY` for the default Anthropic provider, or
`OPENAI_API_KEY` when `ANN_MODEL_PROVIDER=openai`. Optional repository
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
2. Add one provider secret: `ANTHROPIC_API_KEY` for the default provider, or
   `OPENAI_API_KEY` plus repository variable `ANN_MODEL_PROVIDER=openai`.
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
- Installs `requirements.txt`, copies the app and any existing digests.
- Runs Streamlit headless on port **8501** with a container `HEALTHCHECK`
  against `/_stcore/health`.

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

Or with Compose (mounts the working tree so freshly generated digests appear):

```bash
export ANTHROPIC_API_KEY=sk-...
docker compose up --build
```

App: http://localhost:8501

### Generating a digest inside the container

```bash
docker compose run --rm ann python ann.py run
```

## Secrets

- Provider secrets are `ANTHROPIC_API_KEY` and/or `OPENAI_API_KEY`, injected via
  environment variables.
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
