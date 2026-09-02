"""Shared reading, writing and configuration helpers for the subcommands."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import pandas as pd

from ..analysis import AnnualDecompositionError
from ..data.admie import AdmieClient, AdmieError
from ..data.admie_timing import GateClosureSchedule
from ..data.decision_cutoff import read_decision_cutoff_schedule
from ..data.http import OfficialDataDownloadError
from ..data.point_in_time import SamplingGeography, read_sampling_geography
from ..data.quality import QualityReport
from ..data.schema import ensure_canonical, read_canonical_csv
from ..data.timezones import GREECE_TZ, MARKET_TZ
from ..degradation import DegradationConfig
from ..dispatch import BatteryDispatchConfig
from ..finance import FinanceConfig
from ..forecast import (
    ML_MODELS,
    MLForecastConfig,
)
from ..stress import (
    AvailabilityScheduleConfig,
    BootstrapConfig,
    BootstrapDispatchInputError,
    NegativePriceEventConfig,
    PriceLevelShockConfig,
    ScenarioEnsembleInputError,
    ScenarioRun,
    SpreadCompressionConfig,
)


def report_ingestion(
    frame: pd.DataFrame, report: QualityReport, output: Path
) -> int:
    """Write an ingested history with its quality report and pick the exit code.

    Every command that produces canonical price history ends here, so that a
    retrieval whose quality gate failed exits 2 from all of them rather than from
    whichever ones remembered to check.
    """

    _write_outputs(frame, report, output)
    print(json.dumps(report.to_dict(), indent=2))
    return 0 if report.is_valid else 2


def _write_outputs(frame: pd.DataFrame, report: QualityReport, output: Path) -> None:
    if output.suffix.lower() != ".csv":
        raise ValueError("The ingestion foundation currently writes .csv outputs")
    output.parent.mkdir(parents=True, exist_ok=True)
    export = frame.copy()
    export["quality_flags"] = export["quality_flags"].map(json.dumps)

    temporary_csv = output.with_suffix(output.suffix + ".tmp")
    export.to_csv(temporary_csv, index=False)
    temporary_csv.replace(output)

    quality_path = output.with_suffix(".quality.json")
    temporary_quality = quality_path.with_suffix(quality_path.suffix + ".tmp")
    temporary_quality.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    temporary_quality.replace(quality_path)


def _add_ml_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--validation-start-day", required=True, type=date.fromisoformat)
    parser.add_argument("--test-start-day", required=True, type=date.fromisoformat)
    parser.add_argument("--models", nargs="+", choices=ML_MODELS, default=list(ML_MODELS))
    parser.add_argument("--feature-window-days", type=int, default=28)
    parser.add_argument("--refit-frequency-days", type=int, default=7)
    parser.add_argument("--min-training-days", type=int, default=28)
    parser.add_argument("--training-window-days", type=int)
    parser.add_argument("--ridge-alpha", type=float, default=10.0)
    parser.add_argument("--gradient-max-iter", type=int, default=150)
    parser.add_argument("--random-seed", type=int, default=42)


def _ml_config_from_args(args: argparse.Namespace) -> MLForecastConfig:
    return MLForecastConfig(
        validation_start_day=args.validation_start_day,
        test_start_day=args.test_start_day,
        models=tuple(args.models),
        feature_window_days=args.feature_window_days,
        refit_frequency_days=args.refit_frequency_days,
        min_training_days=args.min_training_days,
        training_window_days=args.training_window_days,
        ridge_alpha=args.ridge_alpha,
        gradient_max_iter=args.gradient_max_iter,
        random_seed=args.random_seed,
    )


def _sibling_path(output: Path, suffix: str) -> Path:
    return output.with_name(output.stem + suffix)


def _read_canonical_csv(path: Path) -> pd.DataFrame:
    return read_canonical_csv(path)


def _read_bootstrap_paths_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if "path_id" not in frame:
        raise BootstrapDispatchInputError("Missing bootstrap path columns: path_id")
    path_frames: list[pd.DataFrame] = []
    for path_id, group in frame.groupby("path_id", sort=True):
        group = group.drop(columns="path_id").copy()
        group["delivery_start_utc"] = pd.to_datetime(group["delivery_start_utc"], utc=True)
        group["delivery_end_utc"] = pd.to_datetime(group["delivery_end_utc"], utc=True)
        group["retrieved_at_utc"] = pd.to_datetime(group["retrieved_at_utc"], utc=True)
        group["delivery_start_market"] = group["delivery_start_utc"].dt.tz_convert(MARKET_TZ)
        group["delivery_start_greece"] = group["delivery_start_utc"].dt.tz_convert(GREECE_TZ)
        group["quality_flags"] = group["quality_flags"].map(
            lambda value: json.loads(value) if isinstance(value, str) else []
        )
        canonical = ensure_canonical(group)
        canonical.insert(0, "path_id", path_id)
        path_frames.append(canonical)
    return pd.concat(path_frames, ignore_index=True)


def _read_schedule_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if "delivery_start_utc" not in frame:
        raise AnnualDecompositionError(
            "Perfect-foresight schedule is missing columns: delivery_start_utc"
        )
    frame["delivery_start_utc"] = pd.to_datetime(frame["delivery_start_utc"], utc=True)
    return frame


def _read_daily_results(pairs: list[str]) -> dict[str, pd.DataFrame]:
    daily_results: dict[str, pd.DataFrame] = {}
    for pair in pairs:
        method, separator, raw_path = pair.partition("=")
        if not separator or not method or not raw_path:
            raise AnnualDecompositionError(
                f"--daily-results expects METHOD=PATH pairs, not {pair!r}"
            )
        if method in daily_results:
            raise AnnualDecompositionError(f"--daily-results repeats the method {method!r}")
        daily_results[method] = pd.read_csv(Path(raw_path))
    return daily_results


def _write_dispatch_outputs(
    schedule: pd.DataFrame,
    summary: dict[str, object],
    output: Path,
    summary_path: Path,
) -> None:
    _write_dispatch_csv(schedule, output)
    _write_json(summary, summary_path)


def _read_battery_config(path: Path) -> BatteryDispatchConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Battery config JSON must contain one object")
    return BatteryDispatchConfig(**payload)


def _read_degradation_config(path: Path) -> DegradationConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return DegradationConfig.from_dict(payload)


def _read_finance_config(path: Path) -> FinanceConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return FinanceConfig.from_dict(payload)


def _read_bootstrap_config(path: Path) -> BootstrapConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return BootstrapConfig.from_dict(payload)


def _read_price_level_config(path: Path) -> PriceLevelShockConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return PriceLevelShockConfig.from_dict(payload)


def _admie_empty_discovery_message(
    client: AdmieClient, filetypes: list[str], start_day: date, end_day: date
) -> str:
    """Explain an empty ADMIE discovery, distinguishing a wrong name from a quiet publisher.

    An empty retrieval used to write an empty manifest and exit zero. Downstream, every audited
    delivery day then reported ``no_record``, which reads as "the publisher published nothing" —
    one of the four things the timing audit explicitly does not establish. A misspelled or
    renamed filetype must not be able to impersonate that finding, so the live catalog is
    consulted and the two cases are named apart.
    """

    window = f"{start_day.isoformat()}..{end_day.isoformat()}"
    try:
        catalog = sorted(
            {str(entry.get("filetype", "")) for entry in client.list_filetypes()} - {""}
        )
    except (AdmieError, OfficialDataDownloadError):
        catalog = []
    if not catalog:
        return (
            f"ADMIE returned no files for {', '.join(filetypes)} over {window}, and the filetype "
            "catalog could not be read to check the names. An empty retrieval is refused rather "
            "than written as an empty manifest."
        )
    unknown = [name for name in filetypes if name not in catalog]
    if unknown:
        return (
            f"ADMIE publishes no filetype named {', '.join(unknown)}. The live catalog offers: "
            f"{', '.join(catalog)}. A retrieval naming a filetype the provider does not publish "
            "is refused, because downstream it is indistinguishable from a delivery day the "
            "provider genuinely never published for."
        )
    return (
        f"ADMIE published no {', '.join(filetypes)} file covering {window}. The filetype names "
        "are valid, so this is an empty window rather than a wrong name. An empty retrieval is "
        "refused rather than written as an empty manifest; widen the window or record the "
        "absence deliberately."
    )


def _read_gate_closure_schedule(path: Path) -> GateClosureSchedule:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return GateClosureSchedule.from_dict(payload)


def _read_availability_config(path: Path) -> AvailabilityScheduleConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return AvailabilityScheduleConfig.from_dict(payload)


def _read_scenario_manifest(path: Path) -> list[ScenarioRun]:
    """Read the explicit list of named scenarios an ensemble is built from.

    Every field is required, including ``transformation_summary_json``: a scenario with no
    transformation states that as ``null`` rather than omitting the key, so an untransformed
    replay is a declared member of the ensemble and never an implicit baseline. Relative
    paths resolve against the manifest's own directory.
    """

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ScenarioEnsembleInputError("Scenario manifest JSON must contain one object")
    unknown = sorted(set(payload) - {"scenarios"})
    if unknown:
        raise ScenarioEnsembleInputError(f"Unknown scenario manifest fields: {', '.join(unknown)}")
    declared = payload.get("scenarios")
    if not isinstance(declared, list):
        raise ScenarioEnsembleInputError("Scenario manifest must declare a scenarios list")

    root = path.parent
    required = {
        "name",
        "run_id",
        "path_summaries_csv",
        "dispatch_summary_json",
        "bootstrap_summary_json",
        "transformation_summary_json",
    }
    runs: list[ScenarioRun] = []
    for entry in declared:
        if not isinstance(entry, dict):
            raise ScenarioEnsembleInputError("Every manifest scenario must be one object")
        unknown = sorted(set(entry) - required)
        missing = sorted(required - set(entry))
        if unknown:
            raise ScenarioEnsembleInputError(f"Unknown scenario fields: {', '.join(unknown)}")
        if missing:
            raise ScenarioEnsembleInputError(f"Missing scenario fields: {', '.join(missing)}")
        transformation = entry["transformation_summary_json"]
        runs.append(
            ScenarioRun(
                name=entry["name"],
                run_id=entry["run_id"],
                path_summaries=pd.read_csv(root / str(entry["path_summaries_csv"])),
                dispatch_summary=_read_summary_json(root / str(entry["dispatch_summary_json"])),
                bootstrap_summary=_read_summary_json(root / str(entry["bootstrap_summary_json"])),
                transformation_summary=(
                    None
                    if transformation is None
                    else _read_summary_json(root / str(transformation))
                ),
            )
        )
    return runs


def _read_summary_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ScenarioEnsembleInputError(f"{path.name} must contain one summary object")
    return payload


def _read_spread_compression_config(path: Path) -> SpreadCompressionConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return SpreadCompressionConfig.from_dict(payload)


def _read_negative_price_event_config(path: Path) -> NegativePriceEventConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return NegativePriceEventConfig.from_dict(payload)


def _write_dispatch_csv(schedule: pd.DataFrame, output: Path) -> None:
    export = schedule.copy()
    export["quality_flags"] = export["quality_flags"].map(json.dumps)
    _write_plain_csv(export, output)


def _write_plain_csv(frame: pd.DataFrame, output: Path) -> None:
    if output.suffix.lower() != ".csv":
        raise ValueError("Tabular output must be .csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(output)


def _write_json(payload: object, output: Path) -> None:
    if output.suffix.lower() != ".json":
        raise ValueError("JSON output must be .json")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)


def _read_decision_cutoff_schedule(path: Path) -> GateClosureSchedule:
    """Read a declared v0.9 decision-cutoff schedule, refusing the committed example."""

    return read_decision_cutoff_schedule(path)


def _read_sampling_geography(path: Path) -> SamplingGeography:
    """Read a declared gridded-feature sampling geography, refusing the committed example."""

    return read_sampling_geography(path)
