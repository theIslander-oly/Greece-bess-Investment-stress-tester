"""Parser construction and the single dispatch point for every subcommand."""

from __future__ import annotations

import argparse
import sys

from ..analysis import AnnualDecompositionError
from ..data.admie import AdmieError
from ..data.admie_timing import AdmiePublicationTimingError
from ..data.availability_audit import FeatureAvailabilityError
from ..data.custody import CustodyError
from ..data.decision_cutoff import DecisionCutoffError
from ..data.entsoe import EntsoeError
from ..data.gfs import NoaaGfsError
from ..data.henex import HenexParseError
from ..data.henex_archive import HenexArchiveError
from ..data.henex_daily import HenexDailyError
from ..data.http import OfficialDataDownloadError
from ..data.point_in_time import PointInTimeSchemaError
from ..dispatch import DispatchInputError, DispatchSolveError
from ..forecast.point_in_time_join import PointInTimeJoinError
from ..reporting import ReportContractError
from ..stress import (
    AvailabilityInputError,
    BootstrapDispatchInputError,
    BootstrapInputError,
    PriceLevelShockInputError,
    ScenarioEnsembleInputError,
)
from . import (
    admie,
    analysis,
    custody,
    demo,
    dispatch,
    finance,
    forecast,
    fundamentals,
    ingest,
    manifests,
    stress,
)
from ._registry import Command

# Declaration order here is the order `greek-bess --help` lists the subcommands,
# which follows the order of the workflow rather than the alphabet: retrieve a
# history, record and render it, optimize against it, forecast, then stress.
COMMAND_MODULES = (
    demo,
    ingest,
    admie,
    manifests,
    dispatch,
    forecast,
    fundamentals,
    finance,
    stress,
    analysis,
    custody,
)

COMMANDS: tuple[Command, ...] = tuple(
    command for module in COMMAND_MODULES for command in module.COMMANDS
)

# Reported by the CLI as a failed run rather than a traceback. Every one of these
# means the inputs or the sources were unacceptable, which is a result the tool is
# supposed to produce; anything else is a defect and keeps its traceback.
HANDLED_ERRORS = (
    ValueError,
    DispatchInputError,
    DispatchSolveError,
    EntsoeError,
    HenexParseError,
    HenexArchiveError,
    HenexDailyError,
    AdmieError,
    AdmiePublicationTimingError,
    DecisionCutoffError,
    FeatureAvailabilityError,
    PointInTimeSchemaError,
    PointInTimeJoinError,
    NoaaGfsError,
    OfficialDataDownloadError,
    BootstrapInputError,
    AvailabilityInputError,
    BootstrapDispatchInputError,
    PriceLevelShockInputError,
    ScenarioEnsembleInputError,
    AnnualDecompositionError,
    CustodyError,
    ReportContractError,
    OSError,
)


def _registry() -> dict[str, Command]:
    registry: dict[str, Command] = {}
    for command in COMMANDS:
        if command.name in registry:
            raise AssertionError(f"Duplicate subcommand: {command.name}")
        registry[command.name] = command
    return registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="greek-bess",
        description="Ingest and validate Greek Day-Ahead Market prices.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in _registry().values():
        subparser = subparsers.add_parser(command.name, help=command.help)
        command.configure(subparser)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    command = _registry()[args.command]
    try:
        return command.run(args)
    except HANDLED_ERRORS as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
