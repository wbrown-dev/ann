# Security Policy

## Supported Versions

ANN is a small, actively developed project. Security fixes are applied to the
`main` branch and the latest tagged release.

## Reporting a Vulnerability

Please **do not** open a public issue for security vulnerabilities.

Instead, report privately via one of:

- GitHub's [private vulnerability reporting](https://github.com/wbrown-dev/ann/security/advisories/new)
- Email: **contact@imetwill.com**

Include a description of the issue, steps to reproduce, and any relevant logs
(with secrets redacted). We aim to acknowledge reports within 72 hours.

## Handling of Secrets

- The only secret this project needs is `ANTHROPIC_API_KEY`, supplied via a
  local `.env` file that is **git-ignored** and never committed.
- CI and container builds read secrets from the environment, never from the
  repository.
- Never paste API keys, tokens, or `.env` contents into issues or pull requests.
