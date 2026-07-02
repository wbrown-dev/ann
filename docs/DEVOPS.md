# Dev-Ops

## Continuous integration

CI runs on every push and pull request to `main`
([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)):

1. **lint-and-test** — on Python 3.11 and 3.12: `ruff check .` then
   `pytest -q`.
2. **docker** — builds the image with Buildx (GitHub Actions layer cache),
   starts the container, and polls Streamlit's `/_stcore/health` endpoint to
   prove the app boots.

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

- The only secret is `ANTHROPIC_API_KEY`, injected via environment variable.
- Never bake secrets into the image; `.env` is git-ignored and excluded from the
  build context via `.dockerignore`.

## Releases

- Update [`CHANGELOG.md`](../CHANGELOG.md) and follow SemVer.
- Tag a release (`vX.Y.Z`); the digest files themselves are data, not releases.
