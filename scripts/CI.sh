#!/usr/bin/env bash
# Lint, format check, type check and tests. Exits non-zero on the first failure.
set -euo pipefail

project="$(dirname "$0")/.."

uv --directory "$project" run ruff check
uv --directory "$project" run ruff format --check
uv --directory "$project" run pyrefly check
uv --directory "$project" run pytest -q
