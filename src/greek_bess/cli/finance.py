"""Unlevered project-finance screening arithmetic."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from ..finance import evaluate_project_finance
from ._registry import Command
from ._support import _read_finance_config, _sibling_path, _write_json, _write_plain_csv


def configure_evaluate_project_finance(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "daily_results",
        type=Path,
        help="Daily dispatch results with margin, discharge and augmentation columns",
    )
    parser.add_argument(
        "--finance-config", required=True, type=Path, help="Finance assumptions JSON"
    )
    parser.add_argument("--output", required=True, type=Path, help="Annual cash-flow CSV")
    parser.add_argument("--daily-output", type=Path)
    parser.add_argument("--summary", type=Path)


def run_evaluate_project_finance(args: argparse.Namespace) -> int:
    finance_result = evaluate_project_finance(
        pd.read_csv(args.daily_results),
        _read_finance_config(args.finance_config),
    )
    daily_path = args.daily_output or _sibling_path(args.output, ".daily.csv")
    summary_path = args.summary or args.output.with_suffix(".summary.json")
    _write_plain_csv(finance_result.annual_cash_flows, args.output)
    _write_plain_csv(finance_result.daily_cash_flows, daily_path)
    _write_json(finance_result.summary, summary_path)
    print(json.dumps(finance_result.summary, indent=2))
    return 0


COMMANDS: tuple[Command, ...] = (
    Command(
        name="evaluate-project-finance",
        help="Calculate unlevered pre-tax project cash flows, NPV, IRR, payback "
            "and break-even outputs from a complete daily operating path",
        configure=configure_evaluate_project_finance,
        run=run_evaluate_project_finance,
    ),
)
