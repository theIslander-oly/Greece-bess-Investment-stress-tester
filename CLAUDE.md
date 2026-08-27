# Claude Code project notes

Read `AGENTS.md` first — it is the canonical instruction file for this repository (mission,
non-negotiable interpretation rules, modeling invariants, workflow). This file only adds
environment mechanics.

## Environment

- Python **3.12+** is required (`pyproject.toml`). On hosts where `python` is older, use
  `python3.12 -m venv .venv` and work from `.venv/bin`.
- A SessionStart hook (`.claude/hooks/session-start.sh`) prepares `.venv` automatically in
  Claude Code on the web sessions.

## Commands

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy
pytest -v
python -m build --wheel
```

All four checks must pass before a milestone PR (see `DECISIONS.md`, 2026-08-26).

## Hard rules (summary — full text in AGENTS.md)

- Never commit official market data, retrieval artifacts, tokens, `.env`, or generated
  research outputs. Tests use synthetic fixtures only.
- Perfect foresight is a labelled historical gross-margin upper bound, never expected revenue.
- Forecast paths must be leakage-safe; forecast-planned schedules settle at realized prices.
- Preserve zero and negative prices; never silently interpolate missing official prices.
- Scenario outputs are named deterministic scenarios; no probabilities, percentiles or loss
  metrics without an independently justified calibration (decision entry 2026-08-27).
