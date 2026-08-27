#!/bin/bash
# Prepare a Python 3.12 environment for Claude Code on the web sessions.
# The project requires Python >=3.12 while the default remote interpreter
# may be older; tests, Ruff and mypy all need the project venv on PATH.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

PY=python3.12
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "python3.12 not found; this project requires Python >=3.12" >&2
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  "$PY" -m venv .venv
fi

.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -e ".[dev]"

{
  echo "export VIRTUAL_ENV=\"$CLAUDE_PROJECT_DIR/.venv\""
  echo "export PATH=\"$CLAUDE_PROJECT_DIR/.venv/bin:\$PATH\""
} >> "$CLAUDE_ENV_FILE"
