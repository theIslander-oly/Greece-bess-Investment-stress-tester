#!/bin/bash
# Prepare the project's Python 3.12 development environment.
#
# The project requires Python >=3.12 (pyproject.toml) while a host's default
# interpreter may be older, so Ruff, mypy, pytest and the wheel build all run
# from .venv rather than from whatever `python` resolves to.
#
# Usage:
#   scripts/bootstrap-dev-env.sh            # create/update .venv
#   scripts/bootstrap-dev-env.sh --export-to FILE
#                                           # additionally append VIRTUAL_ENV and
#                                           # PATH exports to FILE, for callers that
#                                           # source an environment file
#
# This script is editor- and service-neutral. Any local session tooling that wants
# an environment prepared automatically should call it rather than reimplement it.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

EXPORT_TO=""
while [ $# -gt 0 ]; do
  case "$1" in
    --export-to)
      EXPORT_TO="${2:-}"
      if [ -z "$EXPORT_TO" ]; then
        echo "--export-to requires a file path" >&2
        exit 2
      fi
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

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

if [ -n "$EXPORT_TO" ]; then
  {
    echo "export VIRTUAL_ENV=\"$PROJECT_DIR/.venv\""
    echo "export PATH=\"$PROJECT_DIR/.venv/bin:\$PATH\""
  } >> "$EXPORT_TO"
fi
