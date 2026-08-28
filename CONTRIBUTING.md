# Contributing

Contributions should preserve the project's transparent pre-feasibility scope.

## Development setup

The project requires **Python 3.12 or newer** (`pyproject.toml`). On hosts whose default
`python` is older, build the environment with `python3.12` and work from `.venv/bin`.

```bash
scripts/bootstrap-dev-env.sh
```

That script creates or updates `.venv` and installs the project with its development
extras. It is editor- and service-neutral: local session tooling that prepares an
environment automatically should call it rather than reimplement the steps. The equivalent
by hand:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
```

## Before submitting a change

All four gates must pass:

```bash
ruff check .
mypy
pytest -v
python -m build --wheel
```

Changes should include tests for new behavior and update the README, changelog, `STATUS.md`,
`DECISIONS.md` or the implementation report when assumptions, outputs or limitations change.

## Modeling rules

- Never present perfect foresight as expected or forecast revenue.
- Do not silently interpolate missing official prices.
- Preserve negative and zero prices.
- Prevent simultaneous charging and discharging.
- Keep market, technical and financial assumptions explicit and editable.
- Keep future market modules outside the MVP until independently validated.

## Data and credentials

Do not commit API tokens, raw official-market downloads, HEnEx workbooks, ENTSO-E XML,
user datasets or generated research outputs. Use synthetic fixtures in automated tests.

## Authorship and attribution

Repository content is contributor-neutral. Commit messages, pull request titles and
bodies, issues, code comments and documentation carry no tool or assistant attribution:
no `Co-Authored-By` trailers naming a tool, no session or transcript links, no "generated
by" footers or notices, and no tool-specific branding in prose.

This is a record-keeping convention, not a disclaimer of responsibility. The repository
records what was decided, what was validated and what the evidence is; which editor,
generator or assistant produced a draft is not part of that record. Whoever submits a
change is responsible for it however it was drafted, and every change passes the same
validation gates and the same review.
