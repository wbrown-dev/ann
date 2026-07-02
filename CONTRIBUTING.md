# Contributing to ANN

Thanks for your interest in improving **ANN (All the News You Need)**. This is
a small, focused project; contributions that keep it small and focused are the
most welcome.

## Ground rules

- **No fabricated headlines or links.** Everything the digest emits must trace
  back to a real fetched item. The filter model selects candidates *by index
  only* so titles and URLs are always verbatim from the source feed.
- **Significance over virality.** Follow the selection standard in
  [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and the project README.
- Keep dependencies minimal.

## Development setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env        # add your ANTHROPIC_API_KEY
```

See [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) for the full workflow.

## Before you open a pull request

1. Add or update tests for your change.
2. Run the test suite and the linter:
   ```bash
   .venv/bin/python -m pytest
   .venv/bin/ruff check .
   ```
3. Keep commits scoped and write a clear description.
4. Do not commit `.env` or any secret.

## Reporting bugs and ideas

Open a GitHub issue describing the problem or proposal. For anything
security-related, follow [`SECURITY.md`](SECURITY.md) instead of filing a
public issue.

## Code style

- No comments unless the *why* is non-obvious.
- Prefer small, well-named functions over docstrings for internal helpers.
- Match the style of the surrounding code.

By contributing you agree that your contributions are licensed under the
project's [MIT License](LICENSE).
