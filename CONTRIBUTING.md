# Contributing

Contributions should preserve the project's transparent pre-feasibility scope.

## Development setup

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e .
```

Activate the virtual environment before installing on systems where that is required.

## Before submitting a change

Run the complete test suite:

```bash
python -m unittest discover -s tests -v
```

Changes should include tests for new behavior and update the README or implementation
report when assumptions, outputs or limitations change.

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
