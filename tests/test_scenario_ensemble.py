"""Non-probabilistic range reporting across named scenarios.

The fixtures below carry hand-checked margins rather than solver output, so the range
arithmetic is verified against numbers a reader can confirm by eye. The end-to-end path from
generated bootstrap paths through dispatch to a reported range is covered in `test_cli.py`.
"""

from __future__ import annotations

import json
import unittest
from typing import Any

import pandas as pd

from greek_bess.stress import (
    FORBIDDEN_REPORT_TERMS,
    NO_TRANSFORMATION,
    PATH_RANGE_SUMMARY_COLUMNS,
    ScenarioEnsembleInputError,
    ScenarioRun,
    report_scenario_ensemble,
)

BATTERY: dict[str, Any] = {
    "charge_power_mw": 25.0,
    "discharge_power_mw": 25.0,
    "energy_capacity_mwh": 50.0,
    "soc_min_fraction": 0.05,
    "soc_max_fraction": 0.95,
    "initial_soc_fraction": 0.50,
    "terminal_soc_fraction": None,
    "charge_efficiency": 0.94,
    "discharge_efficiency": 0.94,
    "buy_fee_eur_per_mwh": 0.0,
    "sell_fee_eur_per_mwh": 0.0,
}

ERA: dict[str, Any] = {
    "resolution_minutes": 60,
    "first_day": "2025-01-01",
    "last_day": "2025-01-31",
    "market_day_count": 31,
}


def _dispatch_summary(**overrides: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "method": "independent deterministic dispatch per bootstrap path",
        "battery_configuration": dict(BATTERY),
        "availability_assumption": {"type": "constant", "fraction": 1.0},
        "path_count": 2,
    }
    summary.update(overrides)
    return summary


def _bootstrap_summary(**overrides: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "selected_source_era": dict(ERA),
        "configuration": {"random_seed": 42, "block_days": 7, "path_count": 2},
    }
    summary.update(overrides)
    return summary


def _run(
    name: str,
    margins: dict[int, float],
    *,
    run_id: str | None = None,
    transformation: dict[str, Any] | None = None,
    dispatch_summary: dict[str, Any] | None = None,
    bootstrap_summary: dict[str, Any] | None = None,
) -> ScenarioRun:
    path_summaries = pd.DataFrame(
        {
            "path_id": list(margins),
            "net_market_margin_eur": list(margins.values()),
            "interval_count": [48] * len(margins),
        }
    )
    return ScenarioRun(
        name=name,
        run_id=f"run-{name}" if run_id is None else run_id,
        path_summaries=path_summaries,
        dispatch_summary=dispatch_summary or _dispatch_summary(),
        bootstrap_summary=bootstrap_summary or _bootstrap_summary(),
        transformation_summary=transformation,
    )


def _baseline() -> ScenarioRun:
    return _run("baseline_replay", {0: 1000.0, 1: 800.0}, run_id="run-baseline")


def _level_shock() -> ScenarioRun:
    return _run(
        "level_shock_minus_20",
        {0: 900.0, 1: 850.0},
        run_id="run-shock",
        transformation={
            "method": "additive constant price-level transformation",
            "configuration": {
                "shift_eur_per_mwh": -20.0,
                "transformation_id": "minus_twenty",
            },
        },
    )


def _compression() -> ScenarioRun:
    return _run(
        "spread_compression_0_7",
        {0: 700.0, 1: 640.0},
        run_id="run-compression",
        transformation={
            "method": "deterministic spread compression about a declared daily reference level",
            "configuration": {
                "compression_factor": 0.7,
                "reference_basis": "daily_mean",
                "transformation_id": "seventy_percent",
            },
        },
    )


def _ensemble() -> list[ScenarioRun]:
    return [_baseline(), _level_shock(), _compression()]


class RangeArithmeticTests(unittest.TestCase):
    def test_range_matches_a_hand_checked_fixture(self) -> None:
        result = report_scenario_ensemble(_ensemble())
        ranges = result.scenario_ranges.set_index("path_id")

        # Path 0: 1000.0 baseline, 900.0 shock, 700.0 compression.
        self.assertEqual(ranges.loc[0, "minimum_net_market_margin_eur"], 700.0)
        self.assertEqual(ranges.loc[0, "minimum_scenario_name"], "spread_compression_0_7")
        self.assertEqual(ranges.loc[0, "maximum_net_market_margin_eur"], 1000.0)
        self.assertEqual(ranges.loc[0, "maximum_scenario_name"], "baseline_replay")
        self.assertEqual(ranges.loc[0, "spread_net_market_margin_eur"], 300.0)
        # Path 1: 800.0 baseline, 850.0 shock, 640.0 compression.
        self.assertEqual(ranges.loc[1, "minimum_net_market_margin_eur"], 640.0)
        self.assertEqual(ranges.loc[1, "minimum_scenario_name"], "spread_compression_0_7")
        self.assertEqual(ranges.loc[1, "maximum_net_market_margin_eur"], 850.0)
        self.assertEqual(ranges.loc[1, "maximum_scenario_name"], "level_shock_minus_20")
        self.assertEqual(ranges.loc[1, "spread_net_market_margin_eur"], 210.0)

        self.assertEqual(ranges["scenario_count"].tolist(), [3, 3])
        self.assertEqual(result.summary["lowest_net_market_margin_eur"], 640.0)
        self.assertEqual(result.summary["lowest_scenario_name"], "spread_compression_0_7")
        self.assertEqual(result.summary["lowest_path_id"], 1)
        self.assertEqual(result.summary["highest_net_market_margin_eur"], 1000.0)
        self.assertEqual(result.summary["highest_scenario_name"], "baseline_replay")
        self.assertEqual(result.summary["highest_path_id"], 0)
        self.assertEqual(result.summary["widest_path_spread_eur"], 300.0)
        self.assertEqual(result.summary["widest_spread_path_id"], 0)
        self.assertEqual(result.summary["narrowest_path_spread_eur"], 210.0)
        self.assertEqual(result.summary["narrowest_spread_path_id"], 1)
        self.assertEqual(result.summary["reported_figure_count"], 6)

    def test_the_report_is_labelled_non_probabilistic(self) -> None:
        summary = report_scenario_ensemble(_ensemble()).summary

        self.assertFalse(summary["is_probabilistic"])
        self.assertFalse(summary["is_forecast"])
        self.assertFalse(summary["is_investment_evidence"])
        self.assertIn("not a distribution", summary["result_label"])
        self.assertIn("no default scenario set", summary["policy"])

    def test_two_runs_produce_identical_output(self) -> None:
        first = report_scenario_ensemble(_ensemble())
        second = report_scenario_ensemble(_ensemble())

        pd.testing.assert_frame_equal(first.scenario_ranges, second.scenario_ranges)
        pd.testing.assert_frame_equal(first.scenario_margins, second.scenario_margins)
        self.assertEqual(
            json.dumps(first.summary, sort_keys=True, default=str),
            json.dumps(second.summary, sort_keys=True, default=str),
        )


class ProvenanceTests(unittest.TestCase):
    def test_every_reported_row_carries_full_provenance(self) -> None:
        result = report_scenario_ensemble(_ensemble())
        margins = result.scenario_margins

        self.assertEqual(len(margins), 6)
        for column in (
            "scenario_name",
            "transformation_method",
            "transformation_parameters",
            "source_era_resolution_minutes",
            "source_era_first_day",
            "source_era_last_day",
            "input_run_id",
            "result_label",
        ):
            self.assertFalse(margins[column].isna().any(), column)
        self.assertEqual(
            sorted(margins["input_run_id"].unique().tolist()),
            ["run-baseline", "run-compression", "run-shock"],
        )
        self.assertEqual(margins["source_era_first_day"].unique().tolist(), ["2025-01-01"])

        compression = margins.loc[margins["scenario_name"] == "spread_compression_0_7"]
        parameters = json.loads(compression["transformation_parameters"].iloc[0])
        self.assertEqual(parameters["compression_factor"], 0.7)
        self.assertEqual(parameters["reference_basis"], "daily_mean")
        self.assertEqual(compression["transformation_id"].iloc[0], "seventy_percent")

        baseline = margins.loc[margins["scenario_name"] == "baseline_replay"]
        self.assertEqual(baseline["transformation_method"].iloc[0], NO_TRANSFORMATION)
        self.assertTrue(baseline["transformation_id"].isna().all())

    def test_each_range_row_names_the_runs_at_both_ends(self) -> None:
        ranges = report_scenario_ensemble(_ensemble()).scenario_ranges

        self.assertEqual(
            ranges["minimum_scenario_input_run_id"].tolist(),
            ["run-compression", "run-compression"],
        )
        self.assertEqual(
            ranges["maximum_scenario_input_run_id"].tolist(), ["run-baseline", "run-shock"]
        )
        self.assertEqual(ranges["source_era_resolution_minutes"].tolist(), [60, 60])

    def test_a_transformation_without_recorded_parameters_is_refused(self) -> None:
        scenarios = [
            _baseline(),
            _run("undocumented", {0: 1.0, 1: 2.0}, transformation={"method": "unknown"}),
        ]

        with self.assertRaises(ScenarioEnsembleInputError) as raised:
            report_scenario_ensemble(scenarios)
        self.assertIn("must record its configuration", str(raised.exception))


class EquivalentBasisTests(unittest.TestCase):
    def _assert_refused(self, scenarios: list[ScenarioRun], expected: str) -> None:
        with self.assertRaises(ScenarioEnsembleInputError) as raised:
            report_scenario_ensemble(scenarios)
        message = str(raised.exception)
        self.assertIn("not on an equivalent basis", message)
        self.assertIn(expected, message)

    def test_mismatched_battery_parameters_are_refused(self) -> None:
        other = dict(BATTERY, discharge_power_mw=40.0)
        self._assert_refused(
            [
                _baseline(),
                _run(
                    "bigger_battery",
                    {0: 1.0, 1: 2.0},
                    dispatch_summary=_dispatch_summary(battery_configuration=other),
                ),
            ],
            "battery parameters",
        )

    def test_mismatched_terminal_energy_constraints_are_refused(self) -> None:
        other = dict(BATTERY, terminal_soc_fraction=0.20)
        self._assert_refused(
            [
                _baseline(),
                _run(
                    "empty_at_day_end",
                    {0: 1.0, 1: 2.0},
                    dispatch_summary=_dispatch_summary(battery_configuration=other),
                ),
            ],
            "terminal-energy constraint",
        )

    def test_mismatched_source_eras_are_refused(self) -> None:
        other = dict(ERA, resolution_minutes=15, first_day="2025-10-01", last_day="2026-08-25")
        self._assert_refused(
            [
                _baseline(),
                _run(
                    "quarter_hour_era",
                    {0: 1.0, 1: 2.0},
                    bootstrap_summary=_bootstrap_summary(selected_source_era=other),
                ),
            ],
            "source-era selection",
        )

    def test_mismatched_path_counts_are_refused(self) -> None:
        self._assert_refused(
            [
                _baseline(),
                _run(
                    "three_paths",
                    {0: 1.0, 1: 2.0, 2: 3.0},
                    dispatch_summary=_dispatch_summary(path_count=3),
                ),
            ],
            "path count and path identity",
        )

    def test_mismatched_path_identities_are_refused(self) -> None:
        self._assert_refused(
            [_baseline(), _run("shifted_ids", {0: 1.0, 2: 2.0})],
            "path count and path identity",
        )

    def test_a_declared_path_count_must_match_the_supplied_paths(self) -> None:
        scenarios = [
            _baseline(),
            _run("miscounted", {0: 1.0, 1: 2.0}, dispatch_summary=_dispatch_summary(path_count=5)),
        ]

        with self.assertRaises(ScenarioEnsembleInputError) as raised:
            report_scenario_ensemble(scenarios)
        self.assertIn("declares path_count 5", str(raised.exception))

    def test_the_refusal_names_the_standing_invariant(self) -> None:
        other = dict(BATTERY, energy_capacity_mwh=100.0)
        with self.assertRaises(ScenarioEnsembleInputError) as raised:
            report_scenario_ensemble(
                [
                    _baseline(),
                    _run(
                        "longer_duration",
                        {0: 1.0, 1: 2.0},
                        dispatch_summary=_dispatch_summary(battery_configuration=other),
                    ),
                ]
            )
        self.assertIn("equivalent physical and terminal-energy constraints", str(raised.exception))


class DeclaredAvailabilityTests(unittest.TestCase):
    """Availability is the judgment under examination, not part of the comparison basis.

    An ensemble that refused a differing availability schedule could never place a declared
    outage against a baseline, which is the comparison an outage scenario exists to make.
    """

    def _outage_scenario(self) -> ScenarioRun:
        return _run(
            "july_outage",
            {0: 600.0, 1: 500.0},
            run_id="run-outage",
            dispatch_summary=_dispatch_summary(
                availability_assumption={
                    "type": "declared_schedule",
                    "schedule_id": "july_outage",
                    "baseline_available_fraction": 1.0,
                    "declared_window_count": 1,
                    "derated_hours": 168.0,
                    "minimum_available_fraction": 0.0,
                }
            ),
        )

    def test_a_declared_outage_ranges_against_a_baseline(self) -> None:
        result = report_scenario_ensemble([_baseline(), self._outage_scenario()])
        ranges = result.scenario_ranges.set_index("path_id")

        self.assertEqual(ranges.loc[0, "minimum_scenario_name"], "july_outage")
        self.assertEqual(ranges.loc[0, "maximum_scenario_name"], "baseline_replay")
        self.assertEqual(ranges.loc[0, "spread_net_market_margin_eur"], 400.0)
        self.assertEqual(ranges.loc[1, "spread_net_market_margin_eur"], 300.0)
        self.assertEqual(
            ranges.loc[0, "minimum_scenario_availability_schedule_id"], "july_outage"
        )
        self.assertEqual(ranges.loc[0, "maximum_scenario_availability_type"], "constant")

    def test_the_declared_availability_reaches_every_margin_row(self) -> None:
        margins = report_scenario_ensemble(
            [_baseline(), self._outage_scenario()]
        ).scenario_margins

        self.assertFalse(margins["availability_type"].isna().any())
        self.assertFalse(margins["availability_declaration"].isna().any())
        outage = margins.loc[margins["scenario_name"] == "july_outage"]
        declared = json.loads(outage["availability_declaration"].iloc[0])
        self.assertEqual(declared["schedule_id"], "july_outage")
        self.assertEqual(declared["derated_hours"], 168.0)
        baseline = margins.loc[margins["scenario_name"] == "baseline_replay"]
        self.assertEqual(baseline["availability_type"].iloc[0], "constant")
        self.assertTrue(baseline["availability_schedule_id"].isna().all())

    def test_the_summary_records_each_scenario_availability(self) -> None:
        summary = report_scenario_ensemble([_baseline(), self._outage_scenario()]).summary

        declared = {entry["scenario_name"]: entry["availability"] for entry in summary["scenarios"]}
        self.assertEqual(declared["july_outage"]["type"], "declared_schedule")
        self.assertEqual(declared["baseline_replay"]["fraction"], 1.0)
        self.assertNotIn("availability_assumption", summary["equivalent_basis"])

    def test_an_unrecorded_availability_assumption_is_still_refused(self) -> None:
        scenario = _run(
            "silent",
            {0: 1.0, 1: 2.0},
            dispatch_summary={
                "battery_configuration": dict(BATTERY),
                "path_count": 2,
            },
        )

        with self.assertRaises(ScenarioEnsembleInputError) as raised:
            report_scenario_ensemble([_baseline(), scenario])
        self.assertIn("must record availability_assumption", str(raised.exception))


class RefusalTests(unittest.TestCase):
    def test_a_single_scenario_is_not_an_ensemble(self) -> None:
        with self.assertRaises(ScenarioEnsembleInputError) as raised:
            report_scenario_ensemble([_baseline()])
        self.assertIn("at least two named scenarios", str(raised.exception))

    def test_an_empty_ensemble_is_refused(self) -> None:
        with self.assertRaises(ScenarioEnsembleInputError):
            report_scenario_ensemble([])

    def test_every_scenario_must_be_named(self) -> None:
        for name in ("", "   "):
            with self.assertRaises(ScenarioEnsembleInputError) as raised:
                report_scenario_ensemble([_baseline(), _run(name, {0: 1.0, 1: 2.0})])
            self.assertIn("non-empty name", str(raised.exception))

    def test_every_scenario_must_declare_its_input_run_identity(self) -> None:
        with self.assertRaises(ScenarioEnsembleInputError) as raised:
            report_scenario_ensemble(
                [_baseline(), _run("unidentified", {0: 1.0, 1: 2.0}, run_id="")]
            )
        self.assertIn("non-empty run_id", str(raised.exception))

    def test_duplicate_scenario_names_are_refused(self) -> None:
        with self.assertRaises(ScenarioEnsembleInputError) as raised:
            report_scenario_ensemble([_baseline(), _run("baseline_replay", {0: 1.0, 1: 2.0})])
        self.assertIn("Duplicate scenario name", str(raised.exception))

    def test_a_missing_margin_is_refused_rather_than_filled(self) -> None:
        broken = _run("incomplete", {0: 1.0, 1: 2.0})
        broken.path_summaries.loc[1, "net_market_margin_eur"] = None

        with self.assertRaises(ScenarioEnsembleInputError) as raised:
            report_scenario_ensemble([_baseline(), broken])
        self.assertIn("refused rather than filled", str(raised.exception))

    def test_a_summary_without_a_battery_configuration_is_refused(self) -> None:
        scenario = _run("unrecorded", {0: 1.0, 1: 2.0}, dispatch_summary={"path_count": 2})

        with self.assertRaises(ScenarioEnsembleInputError) as raised:
            report_scenario_ensemble([_baseline(), scenario])
        self.assertIn("battery_configuration", str(raised.exception))

    def test_a_summary_without_a_selected_source_era_is_refused(self) -> None:
        scenario = _run("no_era", {0: 1.0, 1: 2.0}, bootstrap_summary={"configuration": {}})

        with self.assertRaises(ScenarioEnsembleInputError) as raised:
            report_scenario_ensemble([_baseline(), scenario])
        self.assertIn("selected_source_era", str(raised.exception))


class NoProbabilityFieldTests(unittest.TestCase):
    def _names(self) -> list[str]:
        result = report_scenario_ensemble(_ensemble())
        names = list(result.scenario_ranges.columns) + list(result.scenario_margins.columns)
        names.extend(_keys(result.summary))
        return names

    def test_no_probability_or_percentile_field_appears_in_the_schema(self) -> None:
        for name in self._names():
            for term in FORBIDDEN_REPORT_TERMS:
                self.assertNotIn(term, name.lower(), f"{name} reads as {term}")

    def test_the_forbidden_terms_cover_the_excluded_vocabulary(self) -> None:
        for term in (
            "probability",
            "percentile",
            "likelihood",
            "expected",
            "loss",
            "rank",
            "central",
            "mean",
            "median",
            "quantile",
            "p50",
            "p95",
        ):
            self.assertIn(term, FORBIDDEN_REPORT_TERMS)

    def test_the_guard_refuses_a_forbidden_field_rather_than_emitting_it(self) -> None:
        from greek_bess.stress import ensemble

        with self.assertRaises(ScenarioEnsembleInputError) as raised:
            ensemble._refuse_forbidden_terms(["p95_margin_eur"], "summary key")
        self.assertIn("carries no probability", str(raised.exception))


def _keys(payload: object) -> list[str]:
    keys: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            keys.append(str(key))
            keys.extend(_keys(value))
    elif isinstance(payload, list):
        for item in payload:
            keys.extend(_keys(item))
    return keys


if __name__ == "__main__":  # pragma: no cover
    unittest.main()


class RecordedPathRangeTests(unittest.TestCase):
    """The summary records the per-path ranges, so a report can render them.

    A report reads a run manifest and nothing else. Before this the per-path ranges lived only
    in the CSV beside the run, which meant a report could show the four extreme aggregates and
    nothing in between — or reach past the manifest for the rest, which is the one thing the
    reporting layer must never do. Recording the ranges is what closes that gap; these tests
    pin that recording it changed no number.
    """

    def test_the_summary_records_one_row_per_path_in_frame_order(self) -> None:
        result = report_scenario_ensemble(_ensemble())
        recorded = result.summary["path_ranges"]

        self.assertEqual(len(recorded), len(result.scenario_ranges))
        self.assertEqual(result.summary["path_count"], len(recorded))
        self.assertEqual(
            [row["path_id"] for row in recorded],
            result.scenario_ranges["path_id"].tolist(),
        )

    def test_every_recorded_cell_equals_the_frame_the_csv_is_written_from(self) -> None:
        result = report_scenario_ensemble(_ensemble())

        for position, row in enumerate(result.summary["path_ranges"]):
            self.assertEqual(tuple(row), PATH_RANGE_SUMMARY_COLUMNS)
            for column in PATH_RANGE_SUMMARY_COLUMNS:
                self.assertEqual(row[column], result.scenario_ranges.iloc[position][column])

    def test_recorded_cells_are_plain_json_values(self) -> None:
        """A summary is written as JSON, and a frame carries NumPy scalars."""

        result = report_scenario_ensemble(_ensemble())
        round_tripped = json.loads(json.dumps(result.summary["path_ranges"]))
        self.assertEqual(round_tripped, result.summary["path_ranges"])
        for row in result.summary["path_ranges"]:
            self.assertIsInstance(row["path_id"], int)
            self.assertIsInstance(row["spread_net_market_margin_eur"], float)
            self.assertIsInstance(row["minimum_scenario_name"], str)

    def test_the_recorded_projection_carries_no_probability_vocabulary(self) -> None:
        report_scenario_ensemble(_ensemble())
        for column in PATH_RANGE_SUMMARY_COLUMNS:
            for term in FORBIDDEN_REPORT_TERMS:
                self.assertNotIn(term, column.lower())

    def test_per_scenario_provenance_is_recorded_once_rather_than_per_path(self) -> None:
        """The scenario name is the join; repeating provenance per path adds no fact."""

        result = report_scenario_ensemble(_ensemble())
        recorded_names = {
            row["minimum_scenario_name"] for row in result.summary["path_ranges"]
        } | {row["maximum_scenario_name"] for row in result.summary["path_ranges"]}

        declared = {scenario["scenario_name"] for scenario in result.summary["scenarios"]}
        self.assertTrue(recorded_names.issubset(declared))
        for row in result.summary["path_ranges"]:
            self.assertNotIn("minimum_scenario_transformation_parameters", row)

    def test_recording_the_ranges_changed_no_reported_figure(self) -> None:
        """The recorded rows are a projection of the same frame, not a second reduction."""

        result = report_scenario_ensemble(_ensemble())
        widest = max(
            result.summary["path_ranges"],
            key=lambda row: row["spread_net_market_margin_eur"],
        )
        self.assertEqual(
            widest["spread_net_market_margin_eur"], result.summary["widest_path_spread_eur"]
        )
        self.assertEqual(widest["path_id"], result.summary["widest_spread_path_id"])
