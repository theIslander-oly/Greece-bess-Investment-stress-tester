"""Stage 9: compare selecting a forecast by price error against selecting it by battery value."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from ..dispatch import BatteryDispatchConfig
from ..forecast.ml import MLForecastConfig
from ..selection import (
    DECLARED_CANDIDATES,
    compare_selection_objectives,
    generate_candidate_forecasts,
)
from ..selection.experiment import EVIDENCE_CLASSES, RETROSPECTIVE_EVIDENCE
from ._registry import Command
from ._support import (
    _read_battery_config,
    _read_canonical_csv,
    _sibling_path,
    _write_json,
    _write_plain_csv,
)


def configure_compare_selection_objectives(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("prices", type=Path, help="Canonical price CSV")
    parser.add_argument("--battery", required=True, type=Path, help="Battery config JSON")
    parser.add_argument(
        "--validation-start-day",
        required=True,
        type=date.fromisoformat,
        help="First day of the window both objectives are scored on",
    )
    parser.add_argument(
        "--evaluation-start-day",
        required=True,
        type=date.fromisoformat,
        help="First day of the held-out window, settled only after selection is frozen",
    )
    parser.add_argument("--feature-window-days", type=int, default=28)
    parser.add_argument("--refit-frequency-days", type=int, default=7)
    parser.add_argument("--min-training-days", type=int, default=28)
    parser.add_argument("--training-window-days", type=int)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument(
        "--evidence-class",
        choices=list(EVIDENCE_CLASSES),
        default=RETROSPECTIVE_EVIDENCE,
        help=(
            "Declare what the evaluation window can support. A window this repository has "
            "already inspected is retrospective supplementary evidence."
        ),
    )
    parser.add_argument(
        "--output", required=True, type=Path, help="Evaluation scoreboard CSV"
    )
    parser.add_argument(
        "--validation-scoreboard",
        type=Path,
        help="Validation scoreboard CSV; defaults beside the output",
    )
    parser.add_argument(
        "--summary", type=Path, help="Result summary JSON; defaults beside the output"
    )
    parser.add_argument(
        "--forecasts", type=Path, help="Candidate forecast CSV; written when given"
    )


def run_compare_selection_objectives(args: argparse.Namespace) -> int:
    prices = _read_canonical_csv(args.prices)
    battery: BatteryDispatchConfig = _read_battery_config(args.battery)
    base_config = MLForecastConfig(
        validation_start_day=args.validation_start_day,
        test_start_day=args.evaluation_start_day,
        feature_window_days=args.feature_window_days,
        refit_frequency_days=args.refit_frequency_days,
        min_training_days=args.min_training_days,
        training_window_days=args.training_window_days,
        random_seed=args.random_seed,
    )
    forecasts = generate_candidate_forecasts(prices, base_config, DECLARED_CANDIDATES)
    result = compare_selection_objectives(
        prices,
        battery,
        forecasts,
        candidates=DECLARED_CANDIDATES,
        evidence_class=args.evidence_class,
    )

    _write_plain_csv(result.evaluation_scoreboard, args.output)
    _write_plain_csv(
        result.validation_scoreboard,
        args.validation_scoreboard or _sibling_path(args.output, "_validation.csv"),
    )
    _write_json(
        {"summary": result.summary, "frozen_selection": result.frozen_selection},
        args.summary or _sibling_path(args.output, "_summary.json"),
    )
    if args.forecasts:
        _write_plain_csv(forecasts, args.forecasts)

    summary = result.summary
    print(f"Selected by validation RMSE: {summary['selected_by_validation_rmse']}")
    print(
        "Selected by validation settled margin: "
        f"{summary['selected_by_validation_settled_margin']}"
    )
    print(
        "Evaluation margin, margin-selection minus RMSE-selection: "
        f"EUR {summary['margin_minus_rmse_selection_eur']:.2f}"
    )
    print(f"Evidence class: {summary['evidence_class']}")
    return 0


COMMANDS: tuple[Command, ...] = (
    Command(
        name="compare-selection-objectives",
        help="Compare validation-RMSE and validation-settled-margin model selection",
        configure=configure_compare_selection_objectives,
        run=run_compare_selection_objectives,
    ),
)
