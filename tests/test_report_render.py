"""The report renderer: it renders verified manifests, and only verified manifests.

These tests pin the four things v0.8.0 exists to make true rather than merely intended: a
report shows no figure that did not come out of a verified manifest, every figure carries its
label and the standing exclusions beside it, a manifest this build cannot honor refuses the
whole report instead of being quietly dropped, and identical inputs render byte-identical
output whatever order they were supplied in.
"""

from __future__ import annotations

import html as html_module
import io
import json
import re
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path
from typing import Any
from unittest import mock

import pandas as pd

from greek_bess.cli import main
from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.dispatch import BatteryDispatchConfig, optimize_perfect_foresight
from greek_bess.reporting import (
    BASIS_HEADING,
    BASIS_WORDING,
    DECLARATION_CHECKLIST,
    RESULT_BASES,
    RESULT_KINDS,
    SCENARIO_PROVENANCE_ROWS,
    STANDING_EXCLUSIONS,
    ReportContractError,
    ReportRenderError,
    ResultKind,
    build_run_manifest,
    render_report,
    write_report,
    write_run_manifest,
)
from greek_bess.stress.ensemble import (
    FORBIDDEN_REPORT_TERMS,
    PATH_RANGE_SUMMARY_COLUMNS,
    ScenarioRun,
    report_scenario_ensemble,
)

#: The shape a scenario ensemble records for each named scenario, so a fixture exercises the
#: same nesting a real ``report-scenario-ensemble`` summary carries.
ENSEMBLE_SCENARIOS: list[dict[str, Any]] = [
    {
        "scenario_name": "baseline",
        "input_run_id": "run-baseline",
        "transformation": {
            "method": "none (untransformed bootstrap replay)",
            "transformation_id": None,
            "parameters": {},
        },
        "availability": {"type": "constant", "fraction": 1.0},
        "source_era": {
            "resolution_minutes": 60,
            "first_day": "2025-01-01",
            "last_day": "2025-01-31",
        },
        "bootstrap_configuration": {"random_seed": 42, "block_days": 7, "path_count": 2},
        "path_count": 2,
    },
    {
        "scenario_name": "declared_outage",
        "input_run_id": "run-declared-outage",
        "transformation": {
            "method": "none (untransformed bootstrap replay)",
            "transformation_id": None,
            "parameters": {},
        },
        "availability": {"type": "scheduled", "schedule_id": "outage-a", "fraction": 0.0},
        "source_era": {
            "resolution_minutes": 60,
            "first_day": "2025-01-01",
            "last_day": "2025-01-31",
        },
        "bootstrap_configuration": {"random_seed": 42, "block_days": 7, "path_count": 2},
        "path_count": 2,
    },
]

ENSEMBLE_EQUIVALENT_BASIS: dict[str, Any] = {
    "battery_configuration": {
        "charge_power_mw": 25.0,
        "discharge_power_mw": 25.0,
        "energy_capacity_mwh": 50.0,
        "charge_efficiency": 0.94,
        "discharge_efficiency": 0.94,
    },
    "terminal_energy_basis": {
        "energy_capacity_mwh": 50.0,
        "soc_min_fraction": 0.05,
        "soc_max_fraction": 0.95,
        "initial_soc_fraction": 0.5,
        "terminal_soc_fraction": None,
        "terminal_energy_mwh": 25.0,
    },
    "source_era": {
        "resolution_minutes": 60,
        "first_day": "2025-01-01",
        "last_day": "2025-01-31",
    },
    "path_identity": {"path_count": 2, "path_ids": [0, 1]},
}

ENSEMBLE_PATH_RANGES: list[dict[str, Any]] = [
    {
        "path_id": 0,
        "scenario_count": 2,
        "minimum_net_market_margin_eur": 900.0,
        "minimum_scenario_name": "declared_outage",
        "maximum_net_market_margin_eur": 1000.0,
        "maximum_scenario_name": "baseline",
        "spread_net_market_margin_eur": 100.0,
    },
    {
        "path_id": 1,
        "scenario_count": 2,
        "minimum_net_market_margin_eur": 820.5,
        "minimum_scenario_name": "declared_outage",
        "maximum_net_market_margin_eur": 1100.25,
        "maximum_scenario_name": "baseline",
        "spread_net_market_margin_eur": 279.75,
    },
]

#: One realistic value for each guaranteed summary key in the registry, so a manifest can be
#: built for every kind without running sixteen modules.
GUARANTEED_VALUES: dict[str, Any] = {
    "interval_count": 96,
    "net_market_margin_eur": 1234.5,
    "scenario_count": 2,
    "scenario_names": ["baseline", "declared_outage"],
    "scenarios": ENSEMBLE_SCENARIOS,
    "equivalent_basis": {
        **ENSEMBLE_EQUIVALENT_BASIS,
        "feature_set_identity": {"feature_set_sha256": "f" * 64},
    },
    "path_count": 2,
    "path_ranges": ENSEMBLE_PATH_RANGES,
    "operating_margin_case": "illustrative_supplied_operating_margin",
    "timing_accepted": True,
    "quarantine_lifted": False,
    "availability_accepted": True,
    "evidence_basis": "provider_declared_publication_instants",
    "decision_cutoff_schedule_id": "declared-for-tests",
    "decision_lead_minutes": 30,
    "establishes_only_availability": True,
    "ablation_arms": {
        "control": {"methods": ["ridge"], "feature_columns": ["rolling_mean"]},
        "challenger": {
            "methods": ["ridge_fundamentals"],
            "feature_columns": ["rolling_mean", "temperature_2m"],
        },
    },
    "feature_set_sha256": "f" * 64,
    "evidence_grades_admitted": ["witnessed", "provider_declared"],
    "common_day_count": 42,
    "excluded_days_by_cause": {"feature_no_publication": 3},
    "metrics": {"test": {"ridge": {"rmse_eur_per_mwh": 12.5}}},
    "selected_challenger": "ridge_fundamentals",
    "is_exploratory": True,
    "comparison_methods": ["ridge", "ridge_fundamentals"],
    "common_backtest_day_count": 42,
    "perfect_foresight_margin_eur": 98765.4,
    "dispatch_ranking": [
        {"rank": 1, "method": "ridge_fundamentals", "realized_margin_eur": 71000.0},
        {"rank": 2, "method": "ridge", "realized_margin_eur": 70000.0},
    ],
    "incremental_realized_margin_eur": [
        {
            "comparison_id": "ridge_fundamentals_vs_ridge",
            "challenger_method": "ridge_fundamentals",
            "reference_method": "ridge",
            "incremental_realized_margin_eur": 1000.0,
            "days_challenger_settled_higher": 25,
        }
    ],
    "result_basis_note": (
        "Each market day is planned on the information that strategy was allowed to read and "
        "settled at realized prices under the limits it begins the day with."
    ),
    "study_id": "illustrative-study",
    "price_source": "synthetic",
    "window_start_day": "2025-01-01",
    "window_end_day": "2025-01-31",
    "window_day_count": 31,
    "strategies": [
        {
            "strategy_id": "daily-persistence",
            "planner": "daily_persistence",
            "decision_information": "price_history_before_delivery_day",
            "net_market_margin_eur": 1234.5,
            "final_usable_energy_mwh": 49.5,
        }
    ],
    "coverage": {
        "declared_window_day_count": 31,
        "built_day_count": 31,
        "excluded_day_count": 0,
        "excluded_days_by_cause": {},
    },
    "shared_ceiling_reported": False,
    "finance_horizon_policy": (
        "Finance covers exactly the declared window and nothing is annualised."
    ),
}

FIGURE_BLOCK = re.compile(
    r"<article class=\"figure-block\" id=\"(?P<anchor>[^\"]+)\">(?P<body>.*?)</article>", re.S
)
MAIN_REGION = re.compile(r"<main>(?P<body>.*)</main>", re.S)
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
TAG = re.compile(r"<[^>]+>")


def _summary_for(kind: ResultKind) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "result_label": (
            f"{kind.description} Recorded under an illustrative configuration; not expected or "
            "forecast investment revenue."
        ),
        "method": "declared by the producing module",
    }
    for key in kind.required_summary_keys:
        if key == "result_label":
            continue
        summary[key] = GUARANTEED_VALUES[key]
    if kind.kind_id == "scenario_ensemble_range":
        summary.update(
            {"is_probabilistic": False, "is_forecast": False, "is_investment_evidence": False}
        )
    return summary


def _manifest_path(directory: Path, kind: ResultKind, *, manifest_id: str | None = None) -> Path:
    identifier = manifest_id or f"run-{kind.kind_id}"
    declared_inputs = {}
    if kind.kind_id in {"fundamentals_forecast_benchmark", "fundamentals_dispatch_benchmark"}:
        declared_inputs["accepted_feature_set_sha256"] = "f" * 64
    manifest = build_run_manifest(
        _summary_for(kind),
        kind_id=kind.kind_id,
        manifest_id=identifier,
        produced_by=f"{kind.kind_id}-command",
        created_at_utc="2026-09-01T12:00:00+00:00",
        declared_inputs=declared_inputs,
    )
    path = directory / f"{identifier}.manifest.json"
    write_run_manifest(path, manifest)
    return path


def _manifest_at(path: Path, kind: ResultKind, manifest_id: str) -> Path:
    """Write one manifest at an explicit path, so the manifest ID need not name the file.

    Anchor collisions are a property of the IDs, and two IDs that differ only by case are
    distinct manifests on any platform even where their file names would not be.
    """

    write_run_manifest(
        path,
        build_run_manifest(
            _summary_for(kind),
            kind_id=kind.kind_id,
            manifest_id=manifest_id,
            produced_by=f"{kind.kind_id}-command",
            created_at_utc="2026-09-01T12:00:00+00:00",
        ),
    )
    return path


def _blocks(document: str) -> dict[str, str]:
    return {match.group("anchor"): match.group("body") for match in FIGURE_BLOCK.finditer(document)}


def _main_text(document: str) -> str:
    body = MAIN_REGION.search(document)
    assert body is not None
    return html_module.unescape(TAG.sub(" ", body.group("body")))


INDEX_SECTION = re.compile(
    r"<section class=\"report-index\">(?P<body>.*?)</section>", re.S
)
FIGURE_VALUE = re.compile(r"<span class=\"figure-value\">(?P<value>.*?)</span>", re.S)


def _index_section(document: str) -> str:
    match = INDEX_SECTION.search(document)
    assert match is not None
    return match.group("body")


def _cells(block: str) -> list[str]:
    """Every rendered figure value in a block, in document order."""

    return [
        html_module.unescape(match.group("value")) for match in FIGURE_VALUE.finditer(block)
    ]


def _format_like_manifest(value: Any) -> str:
    """Format a recorded value the way the renderer does: as the JSON it was recorded as."""

    return value if isinstance(value, str) else json.dumps(value, default=str)


def _real_scenarios() -> list[ScenarioRun]:
    """Two named scenarios in the shape ``dispatch-bootstrap-paths`` actually records."""

    battery = {
        "charge_power_mw": 25.0,
        "discharge_power_mw": 25.0,
        "energy_capacity_mwh": 50.0,
        "soc_min_fraction": 0.05,
        "soc_max_fraction": 0.95,
        "initial_soc_fraction": 0.5,
        "terminal_soc_fraction": None,
        "charge_efficiency": 0.94,
        "discharge_efficiency": 0.94,
    }
    era = {"resolution_minutes": 60, "first_day": "2025-01-01", "last_day": "2025-01-31"}

    def scenario(name: str, margins: dict[int, float], availability: dict[str, Any]) -> Any:
        return ScenarioRun(
            name=name,
            run_id=f"run-{name}",
            path_summaries=pd.DataFrame(
                {"path_id": list(margins), "net_market_margin_eur": list(margins.values())}
            ),
            dispatch_summary={
                "battery_configuration": dict(battery),
                "availability_assumption": availability,
                "path_count": len(margins),
            },
            bootstrap_summary={
                "selected_source_era": dict(era),
                "configuration": {"random_seed": 42, "block_days": 7, "path_count": 3},
            },
        )

    return [
        scenario(
            "baseline_replay",
            {0: 1000.0, 1: 1100.25, 2: 980.0},
            {"type": "constant", "fraction": 1.0},
        ),
        scenario(
            "declared_outage",
            {0: 900.0, 1: 820.5, 2: 1010.0},
            {"type": "scheduled", "schedule_id": "outage-a", "fraction": 0.0},
        ),
    ]


def _resolve(summary: dict[str, Any], path: tuple[Any, ...]) -> Any:
    """Walk a recorded summary to the exact value a rendered figure names."""

    value: Any = summary
    for step in path:
        value = value[step]
    return value


def _anchor(manifest_id: str) -> str:
    safe = "".join(
        character if character.isalnum() else "-" for character in manifest_id.lower()
    )
    return f"manifest-{safe}"


class LandingStateTests(unittest.TestCase):
    """With no manifest supplied there is no result to show, and showing one would lie."""

    def setUp(self) -> None:
        self.report = render_report()

    def test_the_landing_state_is_the_declaration_checklist(self) -> None:
        self.assertTrue(self.report.is_landing_state)
        self.assertEqual(self.report.index["state"], "declaration_checklist")
        self.assertEqual(self.report.index["manifest_count"], 0)
        self.assertEqual(self.report.index["figure_count"], 0)
        self.assertEqual(self.report.index["manifests"], [])

    def test_the_landing_state_renders_no_figure(self) -> None:
        self.assertEqual(self.report.figures, ())
        self.assertNotIn('class="figure-value"', self.report.html)

    def test_the_landing_state_contains_no_number_at_all(self) -> None:
        """A number on this page would be an example, and an example would imply a default."""

        text = ISO_DATE.sub(" ", _main_text(self.report.html))
        self.assertEqual([character for character in text if character.isdigit()], [])

    def test_every_default_free_input_names_its_decision_and_its_command(self) -> None:
        text = " ".join(_main_text(self.report.html).split())
        self.assertTrue(DECLARATION_CHECKLIST)
        for requirement in DECLARATION_CHECKLIST:
            self.assertIn(requirement.input_name, text)
            self.assertIn(requirement.decision, text)
            self.assertIn(requirement.decided_on, text)
            self.assertIn(requirement.records_a_result_with, text)


class LabelRetentionTests(unittest.TestCase):
    """Every figure carries its label, its basis in words and the standing exclusions."""

    def test_every_registry_kind_renders_its_label_beside_its_figure(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            paths = [_manifest_path(directory, kind) for kind in RESULT_KINDS.values()]
            report = render_report(paths)

            blocks = _blocks(report.html)
            self.assertEqual(len(blocks), len(RESULT_KINDS))
            for kind in RESULT_KINDS.values():
                block = blocks[_anchor(f"run-{kind.kind_id}")]
                summary = _summary_for(kind)
                self.assertIn(summary["result_label"], block)
                self.assertIn(BASIS_WORDING[kind.basis], block)
                for exclusion in STANDING_EXCLUSIONS:
                    self.assertIn(exclusion, block)

    def test_the_guaranteed_keys_of_a_kind_render_as_its_headline(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            kind = RESULT_KINDS["project_finance"]
            report = render_report([_manifest_path(directory, kind)])

            headline = [figure for figure in report.figures if figure.is_headline]
            self.assertEqual([figure.key for figure in headline], ["operating_margin_case"])

    def test_a_kind_with_no_guaranteed_key_beyond_its_label_still_renders_its_detail(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            kind = RESULT_KINDS["bootstrap_paths"]
            report = render_report([_manifest_path(directory, kind)])

            self.assertEqual([figure.is_headline for figure in report.figures], [False])
            self.assertEqual([figure.key for figure in report.figures], ["method"])

    def test_a_verified_manifest_without_a_guaranteed_key_says_so_rather_than_crashing(
        self,
    ) -> None:
        """The guaranteed-key check is a record-time promise, so a report can still meet one.

        A manifest recorded before its kind guaranteed a key still verifies, by design. Reading
        that key straight out of the summary would raise ``KeyError`` — an unhandled crash for
        a manifest the report can describe honestly — so the absence is stated instead, and no
        figure is recorded for a value that is not there.
        """

        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            kind = RESULT_KINDS["perfect_foresight_dispatch"]
            path = _manifest_path(directory, kind)
            payload = json.loads(path.read_text(encoding="utf-8"))
            del payload["summary"]["interval_count"]
            path.write_text(json.dumps(payload), encoding="utf-8")

            report = render_report([path])

            self.assertNotIn("interval_count", [figure.key for figure in report.figures])
            block = _blocks(report.html)[_anchor("run-perfect_foresight_dispatch")]
            self.assertIn("interval count", block)
            self.assertIn("not recorded", block)


class InlineSvgChartTests(unittest.TestCase):
    """The chart is deterministic rendering of one manifest's recorded values."""

    def _render_ensemble(self, mutate: Any | None = None) -> Any:
        with tempfile.TemporaryDirectory() as raw:
            path = _manifest_path(Path(raw), RESULT_KINDS["scenario_ensemble_range"])
            if mutate is not None:
                payload = json.loads(path.read_text(encoding="utf-8"))
                mutate(payload)
                path.write_text(json.dumps(payload), encoding="utf-8")
            return render_report([path])

    def test_identical_manifest_produces_byte_identical_inline_svg(self) -> None:
        first = self._render_ensemble()
        second = self._render_ensemble()

        self.assertEqual(first.html, second.html)
        self.assertIn('<svg class="manifest-chart"', first.html)
        self.assertNotIn("<script", first.html)

    def test_chart_retains_the_manifest_label_basis_and_exclusions_in_its_block(self) -> None:
        report = self._render_ensemble()
        block = _blocks(report.html)[_anchor("run-scenario_ensemble_range")]
        label = _summary_for(RESULT_KINDS["scenario_ensemble_range"])["result_label"]

        self.assertIn('<svg class="manifest-chart"', block)
        self.assertIn(label, block)
        self.assertIn(BASIS_WORDING["synthetic_scenario"], block)
        for exclusion in STANDING_EXCLUSIONS:
            self.assertIn(exclusion, block)

    def test_missing_guaranteed_chart_key_states_absence(self) -> None:
        def remove_ranges(payload: dict[str, Any]) -> None:
            del payload["summary"]["path_ranges"]

        report = self._render_ensemble(remove_ranges)
        block = _blocks(report.html)[_anchor("run-scenario_ensemble_range")]

        self.assertNotIn('<svg class="manifest-chart"', block)
        self.assertIn("records no usable <code>path_ranges</code> value", block)

    def test_non_object_chart_field_states_absence(self) -> None:
        def replace_ranges(payload: dict[str, Any]) -> None:
            payload["summary"]["path_ranges"] = "not an object sequence"

        report = self._render_ensemble(replace_ranges)
        block = _blocks(report.html)[_anchor("run-scenario_ensemble_range")]

        self.assertNotIn('<svg class="manifest-chart"', block)
        self.assertIn("records no usable <code>path_ranges</code> value", block)


class NoComputationTests(unittest.TestCase):
    """The renderer formats recorded values; it never derives one."""

    def test_every_rendered_figure_is_a_value_a_manifest_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            kinds = [
                RESULT_KINDS["perfect_foresight_dispatch"],
                RESULT_KINDS["scenario_ensemble_range"],
                RESULT_KINDS["project_finance"],
            ]
            paths = [_manifest_path(directory, kind) for kind in kinds]
            report = render_report(paths)

            recorded = {
                f"run-{kind.kind_id}": _summary_for(kind) for kind in kinds
            }
            self.assertTrue(report.figures)
            for figure in report.figures:
                summary = recorded[figure.manifest_id]
                value = _resolve(summary, figure.summary_path)
                expected = value if isinstance(value, str) else json.dumps(value, default=str)
                self.assertEqual(figure.value_text, expected)
                self.assertEqual(str(figure.summary_path[-1]), figure.key)

    def test_figures_of_different_bases_are_never_merged(self) -> None:
        """Three bases on one page, and not one value that belongs to none of them."""

        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            kinds = [
                RESULT_KINDS["perfect_foresight_dispatch"],
                RESULT_KINDS["bootstrap_path_dispatch"],
                RESULT_KINDS["project_finance"],
            ]
            report = render_report([_manifest_path(directory, kind) for kind in kinds])

            bases = {figure.basis for figure in report.figures}
            self.assertEqual(len(bases), 3)
            for figure in report.figures:
                recorded = _summary_for(RESULT_KINDS[figure.result_kind])
                value = _resolve(recorded, figure.summary_path)
                expected = value if isinstance(value, str) else json.dumps(value, default=str)
                self.assertEqual(figure.value_text, expected)

    def test_the_renderer_does_not_read_a_path_a_manifest_names(self) -> None:
        """Interval-level official prices cannot enter an export: only the summary is read."""

        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            prices = directory / "official_prices.csv"
            prices.write_text(
                "interval_start_utc,price_eur_per_mwh\n2026-01-01T00:00:00+00:00,77.7654321\n",
                encoding="utf-8",
            )
            manifest = build_run_manifest(
                _summary_for(RESULT_KINDS["perfect_foresight_dispatch"]),
                kind_id="perfect_foresight_dispatch",
                manifest_id="declares-a-price-file",
                produced_by="optimize-perfect-foresight",
                declared_inputs={"prices_csv": str(prices), "missing_csv": "/no/such/file.csv"},
                created_at_utc="2026-09-01T12:00:00+00:00",
            )
            path = directory / "run.manifest.json"
            write_run_manifest(path, manifest)

            report = render_report([path])

            self.assertIn(str(prices), report.html)
            self.assertNotIn("77.7654321", report.html)


class RefusalTests(unittest.TestCase):
    def test_a_manifest_this_build_cannot_honor_refuses_the_whole_report(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            good = _manifest_path(directory, RESULT_KINDS["perfect_foresight_dispatch"])
            bad = directory / "future.manifest.json"
            payload = json.loads(good.read_text(encoding="utf-8"))
            payload["schema_version"] = 99
            payload["manifest_id"] = "from-a-newer-contract"
            bad.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(ReportContractError) as raised:
                render_report([good, bad])
            self.assertIn("schema_version", str(raised.exception))

    def test_two_inputs_declaring_one_manifest_id_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            first = _manifest_path(directory, RESULT_KINDS["perfect_foresight_dispatch"])
            with self.assertRaises(ReportRenderError):
                render_report([first, first])

    def test_a_report_is_written_only_as_a_self_contained_html_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaises(ReportRenderError):
                write_report(render_report(), Path(raw) / "report.pdf")

    def test_renderer_vocabulary_reading_as_a_distribution_is_refused(self) -> None:
        """The check covers what the renderer itself emits for a kind that forbids the terms."""

        loaded = dict(RESULT_KINDS)
        loaded["scenario_ensemble_range"] = ResultKind(
            "scenario_ensemble_range",
            "synthetic_scenario",
            "Expected value across scenarios.",
            ("result_label", "scenario_count", "scenario_names"),
            forbids_distributional_terms=True,
        )
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            path = _manifest_path(directory, RESULT_KINDS["scenario_ensemble_range"])
            with mock.patch.dict(
                "greek_bess.reporting.render.RESULT_KINDS", loaded, clear=True
            ):
                with self.assertRaises(ReportRenderError) as raised:
                    render_report([path])
        self.assertIn("expected", str(raised.exception))

    def test_the_standing_exclusions_survive_beside_a_kind_that_forbids_the_terms(self) -> None:
        """The scoping is load-bearing: a blanket scan would refuse the disclaimer itself."""

        forbidden_in_exclusions = [
            term
            for term in FORBIDDEN_REPORT_TERMS
            if any(term in exclusion.lower() for exclusion in STANDING_EXCLUSIONS)
        ]
        self.assertEqual(sorted(forbidden_in_exclusions), ["expected", "probability"])

        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            path = _manifest_path(directory, RESULT_KINDS["scenario_ensemble_range"])
            report = render_report([path])

        block = _blocks(report.html)[_anchor("run-scenario_ensemble_range")]
        for exclusion in STANDING_EXCLUSIONS:
            self.assertIn(exclusion, block)


    def test_two_manifest_ids_that_read_alike_still_get_distinct_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            kind = RESULT_KINDS["perfect_foresight_dispatch"]
            paths = [
                _manifest_path(directory, kind, manifest_id="run_1"),
                _manifest_path(directory, kind, manifest_id="run-1"),
            ]
            report = render_report(paths)

            anchors = list(_blocks(report.html))
            self.assertEqual(len(anchors), 2)
            self.assertEqual(len(set(anchors)), 2)

    def test_a_disambiguating_anchor_that_is_itself_taken_is_advanced(self) -> None:
        """One unchecked suffix is not enough to keep anchors unique.

        ``A``, ``A-2`` and ``a`` are three distinct manifests. The first and third reduce to the
        same readable anchor, and the suffix that disambiguates the third is exactly the anchor
        the second already holds — so the index link for one manifest would jump to another
        manifest's block unless the suffixed anchor is checked too.
        """

        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            kind = RESULT_KINDS["perfect_foresight_dispatch"]
            paths = [
                _manifest_at(directory / f"m{position}.manifest.json", kind, manifest_id)
                for position, manifest_id in enumerate(("A", "A-2", "a"))
            ]
            report = render_report(paths)

            blocks = _blocks(report.html)
            self.assertEqual(len(blocks), 3)
            for manifest_id in ("A", "A-2", "a"):
                linked = re.search(
                    r'<a href="#(?P<anchor>[^"]+)">' + re.escape(html_module.escape(manifest_id))
                    + "</a>",
                    report.html,
                )
                assert linked is not None
                self.assertIn(
                    f"<h3>{html_module.escape(manifest_id)}</h3>",
                    blocks[linked.group("anchor")],
                )


class DeterminismTests(unittest.TestCase):
    def test_input_order_does_not_change_the_document(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            paths = [_manifest_path(directory, kind) for kind in RESULT_KINDS.values()]
            forward = render_report(paths)
            reversed_order = render_report(list(reversed(paths)))

            self.assertEqual(forward.html, reversed_order.html)
            self.assertEqual(forward.figures, reversed_order.figures)
            self.assertEqual(forward.index["manifests"], reversed_order.index["manifests"])

    def test_the_document_carries_no_timestamp_of_its_own(self) -> None:
        """Only the index records when rendering happened, so the document stays comparable."""

        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            path = _manifest_path(directory, RESULT_KINDS["perfect_foresight_dispatch"])
            first = render_report([path], rendered_at_utc="2026-09-01T12:00:00+00:00")
            second = render_report([path], rendered_at_utc="2027-01-01T00:00:00+00:00")

            self.assertEqual(first.html, second.html)
            self.assertNotEqual(first.index["rendered_at_utc"], second.index["rendered_at_utc"])

    def test_manifests_are_grouped_by_basis_in_the_declared_order(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            paths = [_manifest_path(directory, kind) for kind in RESULT_KINDS.values()]
            report = render_report(paths)

            rendered = [entry["basis"] for entry in report.index["manifests"]]
            self.assertEqual(rendered, sorted(rendered, key=RESULT_BASES.index))
            self.assertEqual(report.index["bases_rendered"], list(RESULT_BASES))


class SelfContainmentTests(unittest.TestCase):
    def test_the_document_has_no_script_and_fetches_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            paths = [_manifest_path(directory, kind) for kind in RESULT_KINDS.values()]
            document = render_report(paths).html

        lowered = document.lower()
        for forbidden in ("<script", "<iframe", "http://", "https://", "url("):
            self.assertNotIn(forbidden, lowered)

    def test_the_index_identifies_a_manifest_by_digest_not_by_local_path(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            path = _manifest_path(directory, RESULT_KINDS["perfect_foresight_dispatch"])
            report = render_report([path])

            entry = report.index["manifests"][0]
            self.assertEqual(len(entry["manifest_sha256"]), 64)
            self.assertNotIn(str(directory), json.dumps(report.index))


class RealSummaryTests(unittest.TestCase):
    """One end-to-end pass on a genuine optimizer summary, not a fixture of one."""

    def test_a_real_replay_summary_renders_with_its_label(self) -> None:
        prices = generate_synthetic_prices(date(2026, 1, 1), date(2026, 1, 2), seed=11)
        result = optimize_perfect_foresight(
            prices,
            BatteryDispatchConfig(
                charge_power_mw=50.0,
                discharge_power_mw=50.0,
                energy_capacity_mwh=100.0,
            ),
        )
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            manifest = build_run_manifest(
                result.summary,
                kind_id="perfect_foresight_dispatch",
                manifest_id="synthetic-replay",
                produced_by="optimize-perfect-foresight",
                created_at_utc="2026-09-01T12:00:00+00:00",
            )
            path = directory / "replay.manifest.json"
            write_run_manifest(path, manifest)
            report = render_report([path])

        block = _blocks(report.html)["manifest-synthetic-replay"]
        self.assertIn(result.summary["result_label"], block)
        self.assertIn(
            json.dumps(result.summary["net_market_margin_eur"]),
            block,
        )
        for exclusion in STANDING_EXCLUSIONS:
            self.assertIn(exclusion, block)


class RenderReportCommandTests(unittest.TestCase):
    def _run(self, arguments: list[str]) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(arguments)
        return code, out.getvalue(), err.getvalue()

    def test_the_command_writes_a_report_and_an_index(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            path = _manifest_path(directory, RESULT_KINDS["perfect_foresight_dispatch"])
            output = directory / "report.html"

            code, printed, _ = self._run(
                ["render-report", str(path), "--output", str(output)]
            )

            self.assertEqual(code, 0)
            index_path = directory / "report.index.json"
            self.assertTrue(output.exists())
            self.assertTrue(index_path.exists())
            index = json.loads(index_path.read_text(encoding="utf-8"))
            self.assertEqual(index["manifest_count"], 1)
            self.assertEqual(json.loads(printed)["index"], str(index_path))

    def test_the_command_with_no_manifest_renders_the_landing_state(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw) / "landing.html"
            code, printed, _ = self._run(["render-report", "--output", str(output)])

            self.assertEqual(code, 0)
            self.assertEqual(json.loads(printed)["state"], "declaration_checklist")
            self.assertNotIn('class="figure-value"', output.read_text(encoding="utf-8"))

    def test_the_command_writes_nothing_when_a_manifest_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            bad = directory / "bad.manifest.json"
            bad.write_text(json.dumps({"schema_version": 99}), encoding="utf-8")
            output = directory / "report.html"

            code, _, errors = self._run(["render-report", str(bad), "--output", str(output)])

            self.assertEqual(code, 1)
            self.assertIn("schema_version", errors)
            self.assertFalse(output.exists())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()


class MultiRunIndexTests(unittest.TestCase):
    """v0.8.1: an index across many manifests, and the one table that carries no figure.

    A multi-manifest report creates exactly one temptation the single-manifest report did not:
    a summary table spanning the whole document. That table is where a figure of one basis would
    first sit beside a figure of another and then be combined with it. So the index names, links
    and labels — and carries no number at all.
    """

    def _rendered(self, directory: Path) -> Any:
        return render_report(
            [_manifest_path(directory, kind) for kind in RESULT_KINDS.values()]
        )

    def test_the_index_names_every_manifest_the_report_carries(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = self._rendered(Path(raw))

        index = _index_section(report.html)
        for kind in RESULT_KINDS.values():
            self.assertIn(f"run-{kind.kind_id}", index)
            self.assertIn(kind.kind_id, index)

    def test_the_index_across_manifests_carries_no_figure(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = self._rendered(Path(raw))

        index = _index_section(report.html)
        self.assertNotIn('class="figure-value"', index)
        self.assertTrue(report.figures)

        # Every cell of the index is one of the identity, label or provenance fields the
        # manifest declares. Nothing else can appear there, so a recorded figure cannot.
        permitted = set()
        for entry in report.index["manifests"]:
            permitted.update(
                str(entry[field])
                for field in (
                    "manifest_id",
                    "result_kind",
                    "result_label",
                    "produced_by",
                    "created_at_utc",
                    "manifest_sha256",
                )
            )
        for cell in re.findall(r"<td[^>]*>(.*?)</td>", index, re.S):
            self.assertIn(html_module.unescape(TAG.sub("", cell)), permitted)

    def test_the_index_groups_by_basis_in_the_declared_order(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = self._rendered(Path(raw))

        index = _index_section(report.html)
        positions = [index.index(BASIS_HEADING[basis]) for basis in RESULT_BASES]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(report.index["bases_rendered"], list(RESULT_BASES))
        self.assertEqual(report.index["bases_absent"], [])

    def test_the_index_carries_each_manifest_label_and_digest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            path = _manifest_path(directory, RESULT_KINDS["perfect_foresight_dispatch"])
            report = render_report([path])

        index = _index_section(report.html)
        entry = report.index["manifests"][0]
        self.assertIn(entry["manifest_sha256"], index)
        self.assertIn(html_module.escape(entry["result_label"]), index)
        self.assertIn(entry["produced_by"], index)

    def test_the_index_links_to_the_block_that_holds_each_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = self._rendered(Path(raw))

        index = _index_section(report.html)
        blocks = _blocks(report.html)
        anchors = re.findall(r'<a href="#([^"]+)">', index)
        self.assertEqual(len(anchors), len(RESULT_KINDS))
        for anchor in anchors:
            self.assertIn(anchor, blocks)

    def test_the_index_names_the_bases_the_report_does_not_cover(self) -> None:
        """An absent basis is a question this report does not answer, and saying so matters."""

        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            path = _manifest_path(directory, RESULT_KINDS["project_finance"])
            report = render_report([path])

        index = _index_section(report.html)
        self.assertIn("Not represented in this report", index)
        for basis in RESULT_BASES:
            if basis == "screening_arithmetic":
                continue
            self.assertIn(BASIS_HEADING[basis].lower(), index)
        self.assertEqual(
            report.index["bases_absent"],
            [basis for basis in RESULT_BASES if basis != "screening_arithmetic"],
        )

    def test_the_machine_readable_index_groups_manifests_by_basis(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            report = self._rendered(Path(raw))

        grouped = report.index["manifests_by_basis"]
        self.assertEqual(list(grouped), list(RESULT_BASES))
        listed = [manifest_id for ids in grouped.values() for manifest_id in ids]
        self.assertEqual(
            sorted(listed), sorted(f"run-{kind_id}" for kind_id in RESULT_KINDS)
        )
        for basis, ids in grouped.items():
            for manifest_id in ids:
                self.assertEqual(RESULT_KINDS[manifest_id[4:]].basis, basis)

    def test_the_landing_state_has_no_index_across_manifests(self) -> None:
        self.assertNotIn('class="report-index"', render_report().html)


class ScenarioEnsembleCompositionTests(unittest.TestCase):
    """v0.8.1: a scenario ensemble laid out side by side, from the manifest and nothing else."""

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        path = _manifest_path(
            Path(self.directory.name), RESULT_KINDS["scenario_ensemble_range"]
        )
        self.report = render_report([path])
        self.block = _blocks(self.report.html)[_anchor("run-scenario_ensemble_range")]

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_every_recorded_per_path_range_row_is_rendered(self) -> None:
        rendered = _cells(self.block)
        for record in ENSEMBLE_PATH_RANGES:
            for column, value in record.items():
                self.assertIn(
                    _format_like_manifest(value),
                    rendered,
                    f"{column} of path {record['path_id']}",
                )

    def test_the_per_path_range_cells_walk_back_to_the_manifest(self) -> None:
        summary = _summary_for(RESULT_KINDS["scenario_ensemble_range"])
        cells = [
            figure for figure in self.report.figures if figure.summary_path[0] == "path_ranges"
        ]
        self.assertEqual(
            len(cells), len(ENSEMBLE_PATH_RANGES) * len(ENSEMBLE_PATH_RANGES[0])
        )
        for figure in cells:
            value = _resolve(summary, figure.summary_path)
            self.assertEqual(figure.value_text, _format_like_manifest(value))

    def test_nothing_is_totalled_or_reordered_across_paths(self) -> None:
        """No row, total or derived value spans the paths — only the rows the run recorded."""

        rendered = _cells(self.block)
        for derived in (
            sum(record["spread_net_market_margin_eur"] for record in ENSEMBLE_PATH_RANGES),
            sum(
                record["maximum_net_market_margin_eur"] for record in ENSEMBLE_PATH_RANGES
            ),
        ):
            self.assertNotIn(_format_like_manifest(derived), rendered)

        recorded_order = [
            figure.value_text
            for figure in self.report.figures
            if figure.summary_path[0] == "path_ranges" and figure.key == "path_id"
        ]
        self.assertEqual(
            recorded_order,
            [_format_like_manifest(record["path_id"]) for record in ENSEMBLE_PATH_RANGES],
        )

    def test_the_scenarios_are_placed_side_by_side_with_their_provenance(self) -> None:
        for scenario in ENSEMBLE_SCENARIOS:
            self.assertIn(scenario["scenario_name"], self.block)
            self.assertIn(scenario["input_run_id"], self.block)
            self.assertIn(
                html_module.escape(json.dumps(scenario["availability"])), self.block
            )
        for caption, _ in SCENARIO_PROVENANCE_ROWS:
            self.assertIn(caption, self.block)

    def test_a_scenario_cell_belongs_to_exactly_one_recorded_scenario(self) -> None:
        summary = _summary_for(RESULT_KINDS["scenario_ensemble_range"])
        cells = [
            figure for figure in self.report.figures if figure.summary_path[0] == "scenarios"
        ]
        self.assertTrue(cells)
        for figure in cells:
            position = figure.summary_path[1]
            self.assertIsInstance(position, int)
            self.assertLess(position, len(ENSEMBLE_SCENARIOS))
            recorded = _resolve(summary, figure.summary_path)
            self.assertEqual(figure.value_text, _format_like_manifest(recorded))

    def test_the_equivalent_basis_evidence_is_rendered_explicitly(self) -> None:
        self.assertIn("The basis every scenario shared", self.block)
        for group, value in ENSEMBLE_EQUIVALENT_BASIS.items():
            self.assertIn(group.replace("_", " "), self.block)
            for name, recorded in value.items():
                self.assertIn(name.replace("_", " "), self.block)
                self.assertIn(
                    html_module.escape(_format_like_manifest(recorded)), self.block
                )

    def test_a_composition_key_is_rendered_once_and_not_also_as_a_generic_row(self) -> None:
        """One recorded value appears in exactly one place, laid out rather than dumped."""

        for key in ("scenarios", "equivalent_basis", "path_ranges"):
            self.assertNotIn(f'<th scope="row">{key.replace("_", " ")}</th>', self.block)

        entry = self.report.index["manifests"][0]
        self.assertEqual(
            entry["composition_sections"],
            ["scenarios_side_by_side", "equivalent_basis", "per_path_ranges"],
        )
        keys = entry["rendered_summary_keys"]
        self.assertEqual(len(keys), len(set(keys)))
        for key in ("scenarios", "equivalent_basis", "path_ranges"):
            self.assertIn(key, keys)

    def test_a_manifest_recording_no_per_path_ranges_says_so_rather_than_filling_it_in(
        self,
    ) -> None:
        """The other half of the design tension: what a manifest does not record is not shown."""

        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            path = _manifest_path(directory, RESULT_KINDS["scenario_ensemble_range"])
            payload = json.loads(path.read_text(encoding="utf-8"))
            del payload["summary"]["path_ranges"]
            path.write_text(json.dumps(payload), encoding="utf-8")
            report = render_report([path])

        block = _blocks(report.html)[_anchor("run-scenario_ensemble_range")]
        self.assertIn("records no <code>path_ranges</code>", block)
        self.assertIn("does not open the files a run wrote beside it", block)
        self.assertEqual(
            report.index["manifests"][0]["composition_sections"],
            ["scenarios_side_by_side", "equivalent_basis"],
        )
        for figure in report.figures:
            self.assertNotEqual(figure.summary_path[0], "path_ranges")

    def test_an_empty_recorded_table_is_not_reported_as_an_absent_one(self) -> None:
        """Recording an empty table and recording no table are different facts about a run."""

        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            path = _manifest_path(directory, RESULT_KINDS["scenario_ensemble_range"])
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["summary"]["path_ranges"] = []
            path.write_text(json.dumps(payload), encoding="utf-8")
            report = render_report([path])

        block = _blocks(report.html)[_anchor("run-scenario_ensemble_range")]
        self.assertIn("records an empty <code>path_ranges</code>", block)
        self.assertNotIn("records no <code>path_ranges</code>", block)
        self.assertIn(
            "per_path_ranges", report.index["manifests"][0]["composition_sections"]
        )

    def test_ragged_recorded_range_rows_are_refused_rather_than_padded(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            path = _manifest_path(directory, RESULT_KINDS["scenario_ensemble_range"])
            payload = json.loads(path.read_text(encoding="utf-8"))
            del payload["summary"]["path_ranges"][1]["spread_net_market_margin_eur"]
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ReportRenderError, "different columns"):
                render_report([path])

    def test_the_composition_carries_the_label_and_exclusions_beside_it(self) -> None:
        self.assertIn("Range per bootstrap path", self.block)
        for exclusion in STANDING_EXCLUSIONS:
            self.assertIn(exclusion, self.block)
        self.assertIn(BASIS_WORDING["synthetic_scenario"], self.block)


class RealEnsembleCompositionTests(unittest.TestCase):
    """The whole doorway, on a summary a real ensemble produced rather than a fixture of one."""

    def test_a_real_ensemble_renders_the_ranges_it_recorded(self) -> None:
        result = report_scenario_ensemble(_real_scenarios())
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            manifest = build_run_manifest(
                result.summary,
                kind_id="scenario_ensemble_range",
                manifest_id="real-ensemble",
                produced_by="report-scenario-ensemble",
                created_at_utc="2026-09-01T12:00:00+00:00",
            )
            path = directory / "real-ensemble.manifest.json"
            write_run_manifest(path, manifest)
            report = render_report([path])

        block = _blocks(report.html)[_anchor("real-ensemble")]
        rendered = _cells(block)
        for position, row in result.scenario_ranges.iterrows():
            for column in PATH_RANGE_SUMMARY_COLUMNS:
                self.assertIn(_format_like_manifest(row[column]), rendered, column)
            self.assertLess(position, len(result.scenario_ranges))

        cells = [f for f in report.figures if f.summary_path[0] == "path_ranges"]
        for figure in cells:
            recorded = _resolve(result.summary, figure.summary_path)
            self.assertEqual(figure.value_text, _format_like_manifest(recorded))
