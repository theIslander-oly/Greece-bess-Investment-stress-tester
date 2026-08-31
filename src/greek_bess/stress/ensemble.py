"""Non-probabilistic range reporting across named, already-dispatched scenarios.

An ensemble here is a set of named judgments, not a sample from a distribution. Each scenario
is a bootstrap-path dispatch that has already been solved and recorded; this module composes
those accepted outputs and reports the minimum, maximum and spread of the margin outcomes
across the named scenarios. It computes no price, dispatch, forecast or finance quantity of
its own.

Two rules follow from that framing and are enforced rather than documented:

- No probability, percentile, likelihood, expected value, loss metric, ranking or central
  case is produced. A range over named judgments carries no weight over its members, so any
  such figure would be an invention. ``FORBIDDEN_REPORT_TERMS`` is checked against every
  emitted column and summary key, so the invariant fails loudly instead of eroding.
- Scenarios are aggregated only on an equivalent basis. Comparing strategies only under
  equivalent physical and terminal-energy constraints is a standing project invariant, so a
  difference in battery parameters, terminal-energy basis, source era or path identity is
  refused by name rather than reconciled.

The line the basis draws is between the asset and what is done to it. Battery parameters, the
terminal-energy constraint, the source era and the path identities describe the asset and the
sample, and must match. The price transformation and the availability schedule describe the
judgment being examined, and are expected to differ: they are carried as provenance on every
reported figure instead. An ensemble that refused a differing availability schedule could never
compare a declared outage against a baseline, which is the comparison an outage scenario exists
to make.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

MARGIN_COLUMN = "net_market_margin_eur"

NO_TRANSFORMATION = "none (untransformed bootstrap replay)"

ENSEMBLE_POLICY = (
    "A scenario ensemble reports the minimum, maximum and spread of margin outcomes across "
    "two or more scenarios that the caller has named. It is not probabilistic: the scenarios "
    "carry no weights, no likelihoods and no ordering that means anything about the future, "
    "so no probability, percentile, expected value, loss metric, ranking or central case is "
    "produced. There is no default scenario set and no implicit baseline; every scenario is "
    "named and supplied by the caller. Scenarios are combined only on an equivalent basis: "
    "identical battery parameters, terminal-energy constraint, source-era selection and path "
    "identity. Any mismatch is refused and named. The price transformation and the "
    "availability schedule are the judgments under examination rather than part of the basis, "
    "and are recorded as provenance on every reported figure."
)

FORBIDDEN_REPORT_TERMS = (
    "average",
    "central",
    "confidence",
    "cvar",
    "distribution",
    "expected",
    "likelihood",
    "loss",
    "mean",
    "median",
    "odds",
    "p50",
    "p95",
    "percentile",
    "probability",
    "probable",
    "quantile",
    "rank",
    "risk",
    "std",
    "value_at_risk",
    "variance",
    "weight",
)

_TERMINAL_ENERGY_FIELDS = (
    "energy_capacity_mwh",
    "soc_min_fraction",
    "soc_max_fraction",
    "initial_soc_fraction",
    "terminal_soc_fraction",
)


class ScenarioEnsembleInputError(ValueError):
    """Raised when named scenarios cannot be combined into one auditable range."""


@dataclass(frozen=True)
class ScenarioRun:
    """One named, already-dispatched scenario offered to an ensemble.

    ``path_summaries`` and ``dispatch_summary`` are the two outputs of
    ``dispatch_bootstrap_paths``; ``bootstrap_summary`` is the output of
    ``generate_seasonal_bootstrap_paths`` that produced the paths, and supplies the source-era
    selection. ``transformation_summary`` is the summary of the price transformation applied
    between them, or ``None`` for an untransformed replay — which is a scenario the caller
    named like any other, not a default or an implicit baseline. ``run_id`` is the caller's
    identity for the run that produced these results, so a reported figure can be traced back
    to it.
    """

    name: str
    run_id: str
    path_summaries: pd.DataFrame
    dispatch_summary: Mapping[str, Any]
    bootstrap_summary: Mapping[str, Any]
    transformation_summary: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ScenarioEnsembleResult:
    """Per-scenario margins with provenance, the per-path ranges, and the method summary."""

    scenario_margins: pd.DataFrame
    scenario_ranges: pd.DataFrame
    summary: dict[str, Any] = field(default_factory=dict)


def report_scenario_ensemble(scenarios: Sequence[ScenarioRun]) -> ScenarioEnsembleResult:
    """Report the range of margin outcomes across two or more named scenarios.

    The range is taken per bootstrap path: for each path identity the scenarios share, the
    report gives the lowest and highest margin any named scenario produced for that path, the
    spread between them and which scenarios attained each end. Nothing is aggregated across
    paths, because a total or an average over sampled paths would read as an expectation that
    the uniform block resampling does not support.

    The composition is deterministic. Identical inputs produce identical frames and summary,
    scenario order is normalized to the caller's declaration order, and no random component
    is involved.
    """

    runs = _validated_scenarios(scenarios)
    basis = _equivalent_basis(runs)
    margins = _scenario_margins(runs)
    ranges = _scenario_ranges(margins)
    summary = _summary(runs, basis, margins, ranges)

    _refuse_forbidden_terms(margins.columns, "scenario_margins column")
    _refuse_forbidden_terms(ranges.columns, "scenario_ranges column")
    _refuse_forbidden_terms(_summary_keys(summary), "summary key")
    return ScenarioEnsembleResult(
        scenario_margins=margins, scenario_ranges=ranges, summary=summary
    )


def _validated_scenarios(scenarios: Sequence[ScenarioRun]) -> list[ScenarioRun]:
    if isinstance(scenarios, ScenarioRun) or not isinstance(scenarios, Sequence):
        raise ScenarioEnsembleInputError("Scenarios must be supplied as a sequence of runs")
    runs = list(scenarios)
    if len(runs) < 2:
        raise ScenarioEnsembleInputError(
            "A scenario ensemble needs at least two named scenarios; a range across one "
            f"scenario is that scenario, not a range (received {len(runs)})"
        )

    seen: set[str] = set()
    for run in runs:
        if not isinstance(run, ScenarioRun):
            raise ScenarioEnsembleInputError("Every ensemble member must be a ScenarioRun")
        for label, value in (("name", run.name), ("run_id", run.run_id)):
            if not isinstance(value, str) or not value.strip():
                raise ScenarioEnsembleInputError(
                    f"Every scenario must declare a non-empty {label}; there is no default "
                    "scenario set and no implicit baseline"
                )
            if value != value.strip():
                raise ScenarioEnsembleInputError(
                    f"Scenario {label} must not have surrounding whitespace"
                )
        if run.name in seen:
            raise ScenarioEnsembleInputError(f"Duplicate scenario name: {run.name}")
        seen.add(run.name)
        _validated_summary(run, "dispatch_summary", run.dispatch_summary)
        _validated_summary(run, "bootstrap_summary", run.bootstrap_summary)
        if run.transformation_summary is not None:
            _validated_summary(run, "transformation_summary", run.transformation_summary)
    return runs


def _validated_summary(run: ScenarioRun, label: str, summary: Mapping[str, Any]) -> None:
    if not isinstance(summary, Mapping):
        raise ScenarioEnsembleInputError(
            f"Scenario {run.name} must supply {label} as a recorded summary object"
        )


def _path_margins(run: ScenarioRun) -> pd.DataFrame:
    """Return one validated ``path_id``/margin row per path of a scenario."""

    frame = run.path_summaries
    if not isinstance(frame, pd.DataFrame):
        raise ScenarioEnsembleInputError(
            f"Scenario {run.name} must supply path_summaries as a data frame"
        )
    missing = [column for column in ("path_id", MARGIN_COLUMN) if column not in frame.columns]
    if missing:
        raise ScenarioEnsembleInputError(
            f"Scenario {run.name} path summaries are missing columns: {', '.join(missing)}"
        )
    if frame.empty:
        raise ScenarioEnsembleInputError(f"Scenario {run.name} has no dispatched paths")

    path_ids = pd.to_numeric(frame["path_id"], errors="coerce")
    if path_ids.isna().any() or (path_ids % 1 != 0).any() or (path_ids < 0).any():
        raise ScenarioEnsembleInputError(
            f"Scenario {run.name} path_id values must be non-negative integers"
        )
    margins = pd.to_numeric(frame[MARGIN_COLUMN], errors="coerce")
    if margins.isna().any() or not margins.map(math.isfinite).all():
        raise ScenarioEnsembleInputError(
            f"Scenario {run.name} has a missing or non-finite {MARGIN_COLUMN}; a missing "
            "margin is refused rather than filled"
        )
    result = pd.DataFrame(
        {"path_id": path_ids.astype(int), MARGIN_COLUMN: margins.astype(float)}
    )
    if result["path_id"].duplicated().any():
        raise ScenarioEnsembleInputError(f"Scenario {run.name} repeats a path_id")
    return result.sort_values("path_id").reset_index(drop=True)


def _equivalent_basis(runs: Sequence[ScenarioRun]) -> dict[str, Any]:
    """Refuse any scenario that does not share the first scenario's comparison basis."""

    reference = runs[0]
    battery = _battery_configuration(reference)
    checks = (
        ("battery parameters", _battery_basis),
        ("terminal-energy constraint", _terminal_energy_basis),
        ("source-era selection", _source_era_basis),
        ("path count and path identity", _path_basis),
    )
    for label, extract in checks:
        expected = extract(reference)
        for run in runs[1:]:
            found = extract(run)
            if found != expected:
                raise ScenarioEnsembleInputError(
                    f"Scenarios are not on an equivalent basis and cannot be combined: "
                    f"{label} differs between {reference.name} and {run.name} "
                    f"({_render(expected)} versus {_render(found)}). Comparing strategies "
                    "only under equivalent physical and terminal-energy constraints is a "
                    "standing project invariant."
                )
    return {
        "battery_configuration": battery,
        "terminal_energy_basis": _terminal_energy_basis(reference),
        "source_era": _source_era_basis(reference),
        "path_identity": _path_basis(reference),
    }


def _battery_configuration(run: ScenarioRun) -> dict[str, Any]:
    configuration = run.dispatch_summary.get("battery_configuration")
    if not isinstance(configuration, Mapping):
        raise ScenarioEnsembleInputError(
            f"Scenario {run.name} dispatch summary must record battery_configuration; only "
            "recorded bootstrap-path dispatch results can enter an ensemble"
        )
    return {str(key): _plain(value) for key, value in configuration.items()}


def _battery_basis(run: ScenarioRun) -> dict[str, Any]:
    configuration = _battery_configuration(run)
    return {
        key: value
        for key, value in configuration.items()
        if key not in _TERMINAL_ENERGY_FIELDS
    }


def _terminal_energy_basis(run: ScenarioRun) -> dict[str, Any]:
    configuration = _battery_configuration(run)
    missing = [name for name in _TERMINAL_ENERGY_FIELDS if name not in configuration]
    if missing:
        raise ScenarioEnsembleInputError(
            f"Scenario {run.name} battery configuration is missing terminal-energy fields: "
            f"{', '.join(missing)}"
        )
    basis = {name: configuration[name] for name in _TERMINAL_ENERGY_FIELDS}
    terminal_fraction = basis["terminal_soc_fraction"]
    if terminal_fraction is None:
        terminal_fraction = basis["initial_soc_fraction"]
    capacity = basis["energy_capacity_mwh"]
    if not isinstance(terminal_fraction, (int, float)) or not isinstance(
        capacity, (int, float)
    ):
        raise ScenarioEnsembleInputError(
            f"Scenario {run.name} terminal-energy fields must be numeric"
        )
    basis["terminal_energy_mwh"] = float(terminal_fraction) * float(capacity)
    return basis


def _availability_declaration(run: ScenarioRun) -> dict[str, Any]:
    """Return the availability a scenario declared, as provenance rather than as basis.

    A differing schedule is expected — it is the judgment under examination — but an
    unrecorded one is refused, because a margin whose availability assumption is unknown
    cannot be placed in a range against one whose assumption is known.
    """

    availability = run.dispatch_summary.get("availability_assumption")
    if not isinstance(availability, Mapping):
        raise ScenarioEnsembleInputError(
            f"Scenario {run.name} dispatch summary must record availability_assumption; "
            "availability is a declared scenario input and has no default"
        )
    return {str(key): _plain(value) for key, value in availability.items()}


def _source_era_basis(run: ScenarioRun) -> dict[str, Any]:
    era = run.bootstrap_summary.get("selected_source_era")
    if not isinstance(era, Mapping):
        raise ScenarioEnsembleInputError(
            f"Scenario {run.name} bootstrap summary must record selected_source_era; the "
            "source era is part of the comparison basis and has no default"
        )
    return {str(key): _plain(value) for key, value in era.items()}


def _path_basis(run: ScenarioRun) -> dict[str, Any]:
    margins = _path_margins(run)
    path_ids = margins["path_id"].tolist()
    declared = run.dispatch_summary.get("path_count")
    if declared is not None and int(declared) != len(path_ids):
        raise ScenarioEnsembleInputError(
            f"Scenario {run.name} declares path_count {int(declared)} but supplies "
            f"{len(path_ids)} dispatched paths"
        )
    return {"path_count": len(path_ids), "path_ids": path_ids}


def _transformation(run: ScenarioRun) -> dict[str, Any]:
    """Return the transformation parameters a reported figure must carry."""

    if run.transformation_summary is None:
        return {"method": NO_TRANSFORMATION, "transformation_id": None, "parameters": {}}
    summary = run.transformation_summary
    configuration = summary.get("configuration")
    parameters = (
        {str(key): _plain(value) for key, value in configuration.items()}
        if isinstance(configuration, Mapping)
        else {}
    )
    if not parameters:
        raise ScenarioEnsembleInputError(
            f"Scenario {run.name} transformation summary must record its configuration, so "
            "the reported range names the parameters it came from"
        )
    return {
        "method": str(summary.get("method", "unrecorded")),
        "transformation_id": parameters.get("transformation_id"),
        "parameters": parameters,
    }


def _scenario_margins(runs: Sequence[ScenarioRun]) -> pd.DataFrame:
    """Build the long-form table: one fully provenanced row per scenario and path."""

    records: list[dict[str, Any]] = []
    for order, run in enumerate(runs):
        transformation = _transformation(run)
        availability = _availability_declaration(run)
        era = _source_era_basis(run)
        bootstrap_configuration = run.bootstrap_summary.get("configuration")
        seed = (
            bootstrap_configuration.get("random_seed")
            if isinstance(bootstrap_configuration, Mapping)
            else None
        )
        for row in _path_margins(run).itertuples(index=False):
            records.append(
                {
                    "scenario_name": run.name,
                    "scenario_order": order,
                    "path_id": int(row.path_id),
                    MARGIN_COLUMN: float(getattr(row, MARGIN_COLUMN)),
                    "transformation_method": transformation["method"],
                    "transformation_id": transformation["transformation_id"],
                    "transformation_parameters": json.dumps(
                        transformation["parameters"], sort_keys=True
                    ),
                    "availability_type": str(availability.get("type", "unrecorded")),
                    "availability_schedule_id": availability.get("schedule_id"),
                    "availability_declaration": json.dumps(availability, sort_keys=True),
                    "source_era_resolution_minutes": era.get("resolution_minutes"),
                    "source_era_first_day": era.get("first_day"),
                    "source_era_last_day": era.get("last_day"),
                    "input_run_id": run.run_id,
                    "input_bootstrap_random_seed": seed,
                    "result_label": (
                        "perfect-foresight gross-margin upper bound on synthetic bootstrap "
                        "paths under a named scenario; not a forecast, a probability or "
                        "investment evidence"
                    ),
                }
            )
    return pd.DataFrame.from_records(records)


def _scenario_ranges(margins: pd.DataFrame) -> pd.DataFrame:
    """Reduce the long-form table to one minimum/maximum/spread row per bootstrap path."""

    records: list[dict[str, Any]] = []
    for path_id, group in margins.groupby("path_id", sort=True):
        ordered = group.sort_values(["scenario_order"]).reset_index(drop=True)
        lowest = ordered.loc[ordered[MARGIN_COLUMN].idxmin()]
        highest = ordered.loc[ordered[MARGIN_COLUMN].idxmax()]
        records.append(
            {
                "path_id": int(path_id),
                "scenario_count": int(len(ordered)),
                "minimum_net_market_margin_eur": float(lowest[MARGIN_COLUMN]),
                "minimum_scenario_name": str(lowest["scenario_name"]),
                "minimum_scenario_transformation_id": lowest["transformation_id"],
                "minimum_scenario_transformation_method": str(lowest["transformation_method"]),
                "minimum_scenario_transformation_parameters": str(
                    lowest["transformation_parameters"]
                ),
                "minimum_scenario_availability_type": str(lowest["availability_type"]),
                "minimum_scenario_availability_schedule_id": lowest["availability_schedule_id"],
                "minimum_scenario_input_run_id": str(lowest["input_run_id"]),
                "maximum_net_market_margin_eur": float(highest[MARGIN_COLUMN]),
                "maximum_scenario_name": str(highest["scenario_name"]),
                "maximum_scenario_transformation_id": highest["transformation_id"],
                "maximum_scenario_transformation_method": str(highest["transformation_method"]),
                "maximum_scenario_transformation_parameters": str(
                    highest["transformation_parameters"]
                ),
                "maximum_scenario_availability_type": str(highest["availability_type"]),
                "maximum_scenario_availability_schedule_id": highest["availability_schedule_id"],
                "maximum_scenario_input_run_id": str(highest["input_run_id"]),
                "spread_net_market_margin_eur": float(
                    highest[MARGIN_COLUMN] - lowest[MARGIN_COLUMN]
                ),
                "source_era_resolution_minutes": lowest["source_era_resolution_minutes"],
                "source_era_first_day": lowest["source_era_first_day"],
                "source_era_last_day": lowest["source_era_last_day"],
            }
        )
    return pd.DataFrame.from_records(records)


def _summary(
    runs: Sequence[ScenarioRun],
    basis: Mapping[str, Any],
    margins: pd.DataFrame,
    ranges: pd.DataFrame,
) -> dict[str, Any]:
    lowest = margins.loc[margins[MARGIN_COLUMN].idxmin()]
    highest = margins.loc[margins[MARGIN_COLUMN].idxmax()]
    widest = ranges.loc[ranges["spread_net_market_margin_eur"].idxmax()]
    narrowest = ranges.loc[ranges["spread_net_market_margin_eur"].idxmin()]
    return {
        "result_label": (
            "non-probabilistic range of perfect-foresight gross-margin upper bounds across "
            "named scenarios; not a distribution, a forecast or investment evidence"
        ),
        "method": "minimum, maximum and spread across named scenarios, per bootstrap path",
        "policy": ENSEMBLE_POLICY,
        "is_probabilistic": False,
        "is_forecast": False,
        "is_investment_evidence": False,
        "margin_column": MARGIN_COLUMN,
        "scenario_count": len(runs),
        "scenario_names": [run.name for run in runs],
        "scenarios": [
            {
                "scenario_name": run.name,
                "input_run_id": run.run_id,
                "transformation": _transformation(run),
                "availability": _availability_declaration(run),
                "source_era": _source_era_basis(run),
                "bootstrap_configuration": _plain(run.bootstrap_summary.get("configuration")),
                "path_count": _path_basis(run)["path_count"],
            }
            for run in runs
        ],
        "equivalent_basis": dict(basis),
        "path_count": int(len(ranges)),
        "reported_figure_count": int(len(margins)),
        "lowest_net_market_margin_eur": float(lowest[MARGIN_COLUMN]),
        "lowest_scenario_name": str(lowest["scenario_name"]),
        "lowest_path_id": int(lowest["path_id"]),
        "highest_net_market_margin_eur": float(highest[MARGIN_COLUMN]),
        "highest_scenario_name": str(highest["scenario_name"]),
        "highest_path_id": int(highest["path_id"]),
        "widest_path_spread_eur": float(widest["spread_net_market_margin_eur"]),
        "widest_spread_path_id": int(widest["path_id"]),
        "narrowest_path_spread_eur": float(narrowest["spread_net_market_margin_eur"]),
        "narrowest_spread_path_id": int(narrowest["path_id"]),
    }


def _summary_keys(payload: Any) -> list[str]:
    """Collect every key name a reader could mistake for a reported statistic."""

    keys: list[str] = []
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            keys.append(str(key))
            keys.extend(_summary_keys(value))
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            keys.extend(_summary_keys(item))
    return keys


def _refuse_forbidden_terms(names: Iterable[Any], label: str) -> None:
    for name in names:
        text = str(name).lower()
        for term in FORBIDDEN_REPORT_TERMS:
            if term in text:
                raise ScenarioEnsembleInputError(
                    f"Refusing to emit {label} {name!r}: it reads as {term!r}, and a range "
                    "across named scenarios carries no probability, percentile, expected "
                    "value, loss metric or ranking"
                )


def _plain(value: Any) -> Any:
    """Return a JSON-comparable copy, so bases compare by value rather than by object."""

    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _render(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)
