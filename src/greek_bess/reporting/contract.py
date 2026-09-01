"""Versioned run manifest and report contract.

The completed-v0.7 review found the domain APIs interface-ready but their result summaries
"dictionaries rather than a versioned presentation schema", and recommended defining a
versioned run manifest and report contract before any consumer couples to incidental summary
keys. This module is that contract.

It is deliberately a thin wrapper rather than a new result format. Fifteen of the project's
sixteen result-producing modules already emit a ``result_label`` stating what the figure is
and is not; that convention is the thing worth making enforceable, not replacing. A manifest
carries the producing module's summary verbatim and adds a stable projection over it:

- a declared ``result_kind`` from a closed registry, and the ``basis`` that kind reports on,
  so a consumer can tell a historical replay upper bound from a synthetic scenario without
  knowing which of sixteen modules produced it;
- the ``result_label``, required and non-empty, so a figure cannot be exported stripped of the
  sentence that says what it is not;
- the project's three standing negative claims, attached to every manifest rather than
  remembered by each consumer;
- ``schema_version``, refused on read when it is not a version this code understands.

`PROMPT.md` requires that "model outputs must retain their source and limitation labels
through downstream analysis". Before this module that was a convention a downstream consumer
could quietly drop. Building a manifest without a label now raises.

The distributional-term check is deliberately **scoped to the result kinds that declare it**,
not applied to every manifest. ``FORBIDDEN_REPORT_TERMS`` bans claims about the distribution of
outcomes; it is not a ban on the words themselves. A forecast benchmark's mean absolute error
is an accuracy statistic about a model, and a publication audit's median lead time is a
statistic about a publisher — neither asserts a distribution over investment outcomes. Applying
one list everywhere would refuse honest arithmetic and teach a reader that the check is noise.

Where the check does apply it reaches every key name at any depth, because a report renders
nested keys as visible column headings. A summary that recorded a per-path table whose columns
claimed a percentile would otherwise pass a top-level scan and reach a reader as a heading.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .. import __version__
from ..data.provenance import utc_now_iso
from ..stress.ensemble import FORBIDDEN_REPORT_TERMS

REPORT_CONTRACT_VERSION = 1

#: What a result describes. This is the discriminator a consumer needs before it can render a
#: figure responsibly: the same euro amount means something different in each of these.
RESULT_BASES = (
    "historical_replay_upper_bound",
    "historical_forecast_backtest",
    "synthetic_scenario",
    "screening_arithmetic",
    "data_acceptance_evidence",
)

#: The project's standing negative claims. They hold for every result kind in the registry, so
#: they are attached to every manifest rather than restated by each consumer. A future kind that
#: could not carry one of these would be a scope change requiring a recorded decision, not a
#: quiet exception here.
STANDING_EXCLUSIONS = (
    "not a probability-calibrated estimate",
    "not expected or forecast investment revenue",
    "not investment evidence, financial advice or a bankable study",
)


class ReportContractError(ValueError):
    """Raised when a result cannot be recorded under the contract exactly as declared."""


@dataclass(frozen=True)
class ResultKind:
    """One recordable result kind and the guarantees a consumer may rely on."""

    kind_id: str
    basis: str
    description: str
    required_summary_keys: tuple[str, ...] = ("result_label",)
    forbids_distributional_terms: bool = False

    def __post_init__(self) -> None:
        if self.basis not in RESULT_BASES:
            raise ReportContractError(
                f"Result kind {self.kind_id} declares unknown basis {self.basis!r}"
            )
        if "result_label" not in self.required_summary_keys:
            raise ReportContractError(
                f"Result kind {self.kind_id} must require result_label; a result that may be "
                "exported without its label is exactly what this contract exists to prevent"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind_id": self.kind_id,
            "basis": self.basis,
            "description": self.description,
            "required_summary_keys": list(self.required_summary_keys),
            "forbids_distributional_terms": self.forbids_distributional_terms,
        }


def _kinds() -> dict[str, ResultKind]:
    declared = (
        ResultKind(
            "perfect_foresight_dispatch",
            "historical_replay_upper_bound",
            "Whole-horizon perfect-foresight Greek DAM gross-margin upper bound.",
            ("result_label", "interval_count", "net_market_margin_eur"),
        ),
        ResultKind(
            "daily_perfect_foresight_dispatch",
            "historical_replay_upper_bound",
            "Perfect-foresight upper bound composed from independent daily solves.",
            ("result_label", "interval_count", "net_market_margin_eur"),
        ),
        ResultKind(
            "degradation_dispatch",
            "historical_replay_upper_bound",
            "Daily perfect-foresight upper bound under an illustrative degradation state.",
        ),
        ResultKind(
            "annual_replay_decomposition",
            "historical_replay_upper_bound",
            "Per-delivery-year decomposition of an accepted replay.",
        ),
        ResultKind(
            "forecast_dispatch_backtest",
            "historical_forecast_backtest",
            "Walk-forward forecast-planned dispatch settled at realized prices.",
        ),
        ResultKind(
            "ml_forecast_benchmark",
            "historical_forecast_backtest",
            "Leakage-safe walk-forward ML price-forecast benchmark.",
        ),
        ResultKind(
            "ml_dispatch_benchmark",
            "historical_forecast_backtest",
            "Held-out like-for-like ML forecast-dispatch benchmark.",
        ),
        ResultKind(
            "bootstrap_paths",
            "synthetic_scenario",
            "Seeded seasonal block-bootstrap synthetic price paths.",
        ),
        ResultKind(
            "bootstrap_path_dispatch",
            "synthetic_scenario",
            "Independent deterministic dispatch across validated bootstrap paths.",
        ),
        ResultKind(
            "price_level_shock",
            "synthetic_scenario",
            "Declared additive price-level transformation of bootstrap paths.",
        ),
        ResultKind(
            "spread_compression",
            "synthetic_scenario",
            "Declared within-day spread compression about a daily reference level.",
        ),
        ResultKind(
            "negative_price_events",
            "synthetic_scenario",
            "Declared interval-aligned negative-price event transformation.",
        ),
        ResultKind(
            "availability_profile",
            "synthetic_scenario",
            "Declared availability baseline and outage windows applied to a run.",
        ),
        ResultKind(
            "scenario_ensemble_range",
            "synthetic_scenario",
            "Non-probabilistic minimum, maximum and spread across named scenarios.",
            (
                "result_label",
                "scenario_count",
                "scenario_names",
                "scenarios",
                "equivalent_basis",
                "path_count",
                "path_ranges",
            ),
            forbids_distributional_terms=True,
        ),
        ResultKind(
            "degradation_state",
            "screening_arithmetic",
            "Illustrative cohort degradation and augmentation state model.",
        ),
        ResultKind(
            "project_finance",
            "screening_arithmetic",
            "Unlevered pre-tax, pre-subsidy project-finance screening arithmetic.",
            ("result_label", "operating_margin_case"),
        ),
        ResultKind(
            "admie_publication_timing_audit",
            "data_acceptance_evidence",
            "Pre-auction publication-timing audit of quarantined ADMIE forecast files.",
            ("result_label", "timing_accepted", "quarantine_lifted"),
        ),
    )
    return {kind.kind_id: kind for kind in declared}


RESULT_KINDS: dict[str, ResultKind] = _kinds()


@dataclass(frozen=True)
class RunManifest:
    """One recorded analytical run, readable without knowing which module produced it."""

    manifest_id: str
    result_kind: str
    basis: str
    result_label: str
    produced_by: str
    project_version: str
    created_at_utc: str
    summary: Mapping[str, Any]
    declared_inputs: Mapping[str, Any] = field(default_factory=dict)
    schema_version: int = REPORT_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": int(self.schema_version),
            "manifest_id": self.manifest_id,
            "result_kind": self.result_kind,
            "basis": self.basis,
            "result_label": self.result_label,
            "produced_by": self.produced_by,
            "project_version": self.project_version,
            "created_at_utc": self.created_at_utc,
            "standing_exclusions": list(STANDING_EXCLUSIONS),
            "declared_inputs": dict(self.declared_inputs),
            "summary": dict(self.summary),
        }


def build_run_manifest(
    summary: Mapping[str, Any],
    *,
    kind_id: str,
    manifest_id: str,
    produced_by: str,
    declared_inputs: Mapping[str, Any] | None = None,
    created_at_utc: str | None = None,
) -> RunManifest:
    """Record one result under the contract, or refuse to record it.

    ``summary`` is the producing module's own summary and is carried verbatim: the contract
    adds a projection over a result, it does not reshape or reinterpret one.
    """

    kind = RESULT_KINDS.get(kind_id)
    if kind is None:
        known = ", ".join(sorted(RESULT_KINDS))
        raise ReportContractError(
            f"Unknown result_kind {kind_id!r}. The registry is closed so that a consumer can "
            f"rely on it; add a kind deliberately. Known kinds: {known}"
        )
    for name, value in (("manifest_id", manifest_id), ("produced_by", produced_by)):
        if not isinstance(value, str) or not value.strip():
            raise ReportContractError(f"{name} must be a non-empty string")
        if value != value.strip():
            raise ReportContractError(f"{name} must not have surrounding whitespace")
    if not isinstance(summary, Mapping):
        raise ReportContractError("summary must be a mapping produced by a result module")

    missing = [key for key in kind.required_summary_keys if key not in summary]
    if missing:
        raise ReportContractError(
            f"Result kind {kind_id} requires summary keys the supplied summary does not carry: "
            f"{', '.join(sorted(missing))}"
        )
    label = summary["result_label"]
    if not isinstance(label, str) or not label.strip():
        raise ReportContractError(
            f"Result kind {kind_id} carries an empty result_label; a figure is not exportable "
            "without the sentence stating what it is and is not"
        )
    if kind.forbids_distributional_terms:
        _refuse_distributional_terms(kind_id, summary)
    _refuse_contradicted_standing_claims(kind_id, summary)

    if declared_inputs is not None and not isinstance(declared_inputs, Mapping):
        raise ReportContractError("declared_inputs must be a mapping when supplied")

    return RunManifest(
        manifest_id=manifest_id,
        result_kind=kind.kind_id,
        basis=kind.basis,
        result_label=label,
        produced_by=produced_by,
        project_version=__version__,
        created_at_utc=created_at_utc or utc_now_iso(),
        summary=dict(summary),
        declared_inputs=dict(declared_inputs or {}),
    )


def write_run_manifest(path: Path, manifest: RunManifest) -> None:
    """Write a deterministic JSON manifest beside the result it describes."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=False, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def read_run_manifest(path: Path) -> RunManifest:
    """Read a manifest, refusing a schema version or result kind this code cannot honor."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ReportContractError("A run manifest must contain one JSON object")
    version = payload.get("schema_version")
    if version != REPORT_CONTRACT_VERSION:
        raise ReportContractError(
            f"Run manifest declares schema_version {version!r}; this build understands "
            f"{REPORT_CONTRACT_VERSION}. A manifest from a newer contract is refused rather "
            "than read on the assumption that its fields still mean the same thing"
        )
    required = {
        "manifest_id",
        "result_kind",
        "basis",
        "result_label",
        "produced_by",
        "project_version",
        "created_at_utc",
        "summary",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ReportContractError(
            f"Run manifest is missing required fields: {', '.join(missing)}"
        )
    kind_id = str(payload["result_kind"])
    kind = RESULT_KINDS.get(kind_id)
    if kind is None:
        raise ReportContractError(
            f"Run manifest declares unknown result_kind {kind_id!r}; the registry is closed"
        )
    if str(payload["basis"]) != kind.basis:
        raise ReportContractError(
            f"Run manifest declares basis {payload['basis']!r} for result kind {kind_id}, "
            f"which reports on {kind.basis!r}"
        )
    summary = payload["summary"]
    if not isinstance(summary, Mapping):
        raise ReportContractError("Run manifest summary must be an object")
    return RunManifest(
        manifest_id=str(payload["manifest_id"]),
        result_kind=kind_id,
        basis=kind.basis,
        result_label=str(payload["result_label"]),
        produced_by=str(payload["produced_by"]),
        project_version=str(payload["project_version"]),
        created_at_utc=str(payload["created_at_utc"]),
        summary=dict(summary),
        declared_inputs=dict(payload.get("declared_inputs") or {}),
    )


def _refuse_distributional_terms(kind_id: str, summary: Mapping[str, Any]) -> None:
    """Check every key name a consumer could render, at any depth of the summary.

    The check reaches nested keys because a report does. A scenario ensemble records its
    per-path ranges and its per-scenario provenance as nested objects, and a renderer that
    displays a nested key displays its name; a check that stopped at the top level would clear
    a manifest whose visible column headings claim a distribution the kind forbids.
    """

    for name in _nested_key_names(summary):
        lowered = name.lower()
        for term in FORBIDDEN_REPORT_TERMS:
            if term in lowered:
                raise ReportContractError(
                    f"Refusing to record {kind_id} summary key {name!r}: it reads as {term!r}, "
                    "and this result kind reports a range across named judgments rather than a "
                    "distribution over outcomes"
                )


def _nested_key_names(payload: Any) -> list[str]:
    """Collect every mapping key name in a summary, at any depth."""

    names: list[str] = []
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            names.append(str(key))
            names.extend(_nested_key_names(value))
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            names.extend(_nested_key_names(item))
    return names


def _refuse_contradicted_standing_claims(kind_id: str, summary: Mapping[str, Any]) -> None:
    """Cross-check a summary that declares the standing claims itself.

    Only the scenario ensemble declares these today. Where a summary does declare one, the
    contract verifies rather than ignores it: a module that began reporting a probabilistic
    result would otherwise be recorded under a manifest still asserting the opposite.
    """

    for key in ("is_probabilistic", "is_forecast", "is_investment_evidence"):
        if key in summary and summary[key] is not False:
            raise ReportContractError(
                f"Result kind {kind_id} carries {key}={summary[key]!r}, contradicting the "
                "standing exclusions every manifest asserts. A result that is genuinely "
                "probabilistic, a forecast or investment evidence is a scope change requiring "
                "a recorded decision, not a manifest"
            )
