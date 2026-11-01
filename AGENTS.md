# Agent instructions

## Project

This Home Assistant integration connects to PiKVM's kvmd API and can optionally use SSH for host status and controls. It exposes device status, screen snapshots, and supported controls as Home Assistant entities.

## Working in this repository

- Read `README.md` before changing API, SSH, camera/OCR, or shutdown behavior.
- Keep SSH-backed features optional and preserve the README's distinction between API-only and SSH-backed entities.
- Before changing CI, check [pschmitt/ci-workflows](https://github.com/pschmitt/ci-workflows) for reusable components and preserve this repository's existing checks.

## Validation

- Run `uvx ruff check .` and `uvx ruff format --check .` for Python changes.
- CI runs Hassfest and the shared Ruff checks; it currently has no test job.
