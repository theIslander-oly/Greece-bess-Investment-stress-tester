"""The versioned run manifest and report contract.

The contract's whole purpose is to make two things impossible: exporting a figure without the
sentence that says what it is not, and reading a manifest from a newer contract as though its
fields still mean the same thing. These tests pin both, and pin the deliberate scoping of the
distributional-term check, which is the one place a blunter rule would refuse honest arithmetic.
"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path
from typing import Any

import greek_bess
from greek_bess.analysis import decompose_annual_replay
from greek_bess.backtest import backtest_forecast_dispatch
from greek_bess.cli import main
from greek_bess.data.admie_timing import ADMIE_TIMING_LABEL
from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.dispatch import (
    BatteryDispatchConfig,
    optimize_daily_perfect_foresight,
    optimize_perfect_foresight,
)
from greek_bess.dispatch.perfect_foresight import UPPER_BOUND_LABEL
from greek_bess.reporting import (
    REPORT_CONTRACT_VERSION,
    RESULT_BASES,
    RESULT_KINDS,
    STANDING_EXCLUSIONS,
    ReportContractError,
    build_run_manifest,
    read_run_manifest,
    write_run_manifest,
)


def _dispatch_summary(**overrides: Any) -> dict[str, Any]:
    summary = {
        "result_label": UPPER_BOUND_LABEL,
        "interval_count": 96,
        "net_market_margin_eur": 1234.5,
    }
    summary.update(overrides)
    return summary


def _build(summary: dict[str, Any], **overrides: Any) -> Any:
    parameters: dict[str, Any] = {
        "kind_id": "perfect_foresight_dispatch",
        "manifest_id": "run-1",
        "produced_by": "optimize-perfect-foresight",
        "created_at_utc": "2026-08-31T12:00:00+00:00",
    }
    parameters.update(overrides)
    return build_run_manifest(summary, **parameters)


class RegistryTests(unittest.TestCase):
    def test_every_declared_kind_reports_on_a_known_basis(self) -> None:
        for kind in RESULT_KINDS.values():
            self.assertIn(kind.basis, RESULT_BASES)
            self.assertIn("result_label", kind.required_summary_keys)

    def test_the_registry_covers_each_result_basis(self) -> None:
        covered = {kind.basis for kind in RESULT_KINDS.values()}
        self.assertEqual(covered, set(RESULT_BASES))

    def test_only_the_scenario_ensemble_forbids_distributional_terms(self) -> None:
        forbidding = {
            kind_id for kind_id, kind in RESULT_KINDS.items()
            if kind.forbids_distributional_terms
        }
        self.assertEqual(forbidding, {"scenario_ensemble_range"})


class BuildTests(unittest.TestCase):
    def test_a_manifest_carries_the_summary_verbatim_and_the_standing_exclusions(self) -> None:
        summary = _dispatch_summary(horizon_start_utc="2026-01-01T00:00:00+00:00")
        manifest = _build(summary).to_dict()

        self.assertEqual(manifest["schema_version"], REPORT_CONTRACT_VERSION)
        self.assertEqual(manifest["summary"], summary)
        self.assertEqual(manifest["basis"], "historical_replay_upper_bound")
        self.assertEqual(manifest["result_label"], UPPER_BOUND_LABEL)
        self.assertEqual(manifest["project_version"], greek_bess.__version__)
        self.assertEqual(manifest["standing_exclusions"], list(STANDING_EXCLUSIONS))

    def test_a_result_without_its_label_cannot_be_recorded(self) -> None:
        summary = _dispatch_summary()
        del summary["result_label"]
        with self.assertRaisesRegex(ReportContractError, "does not carry: result_label"):
            _build(summary)

    def test_an_empty_label_is_refused(self) -> None:
        with self.assertRaisesRegex(ReportContractError, "empty result_label"):
            _build(_dispatch_summary(result_label="   "))

    def test_a_kind_missing_its_guaranteed_keys_is_refused(self) -> None:
        summary = _dispatch_summary()
        del summary["net_market_margin_eur"]
        with self.assertRaisesRegex(ReportContractError, "net_market_margin_eur"):
            _build(summary)

    def test_an_unknown_result_kind_names_the_closed_registry(self) -> None:
        with self.assertRaisesRegex(ReportContractError, "registry is closed"):
            _build(_dispatch_summary(), kind_id="revenue_forecast")

    def test_blank_identifiers_are_refused(self) -> None:
        with self.assertRaisesRegex(ReportContractError, "manifest_id"):
            _build(_dispatch_summary(), manifest_id="  ")
        with self.assertRaisesRegex(ReportContractError, "produced_by"):
            _build(_dispatch_summary(), produced_by="")

    def test_a_summary_contradicting_a_standing_claim_is_refused(self) -> None:
        with self.assertRaisesRegex(ReportContractError, "standing exclusions"):
            _build(_dispatch_summary(is_probabilistic=True))
        with self.assertRaisesRegex(ReportContractError, "scope change"):
            _build(_dispatch_summary(is_investment_evidence=True))

    def test_a_summary_that_declares_the_claims_correctly_is_accepted(self) -> None:
        manifest = _build(
            _dispatch_summary(
                is_probabilistic=False, is_forecast=False, is_investment_evidence=False
            )
        )
        self.assertEqual(manifest.result_kind, "perfect_foresight_dispatch")


def _ensemble_summary(**overrides: Any) -> dict[str, Any]:
    """A summary carrying every key the ensemble kind guarantees, including the nesting."""

    summary: dict[str, Any] = {
        "result_label": "non-probabilistic range across named scenarios",
        "scenario_count": 2,
        "scenario_names": ["a", "b"],
        "scenarios": [
            {
                "scenario_name": "a",
                "input_run_id": "run-a",
                "transformation": {"method": "none", "transformation_id": None},
                "availability": {"type": "constant", "fraction": 1.0},
                "path_count": 1,
            },
            {
                "scenario_name": "b",
                "input_run_id": "run-b",
                "transformation": {"method": "none", "transformation_id": None},
                "availability": {"type": "constant", "fraction": 1.0},
                "path_count": 1,
            },
        ],
        "equivalent_basis": {"path_identity": {"path_count": 1, "path_ids": [0]}},
        "path_count": 1,
        "path_ranges": [
            {
                "path_id": 0,
                "scenario_count": 2,
                "minimum_net_market_margin_eur": 10.0,
                "minimum_scenario_name": "a",
                "maximum_net_market_margin_eur": 12.0,
                "maximum_scenario_name": "b",
                "spread_net_market_margin_eur": 2.0,
            }
        ],
    }
    summary.update(overrides)
    return summary


class DistributionalTermScopeTests(unittest.TestCase):
    def test_the_ensemble_refuses_a_distributional_key(self) -> None:
        with self.assertRaisesRegex(ReportContractError, "reads as 'mean'"):
            build_run_manifest(
                _ensemble_summary(mean_net_market_margin_eur=10.0),
                kind_id="scenario_ensemble_range",
                manifest_id="run-2",
                produced_by="report-scenario-ensemble",
            )

    def test_the_ensemble_refuses_a_distributional_key_nested_in_a_table(self) -> None:
        """The check reaches the depth a report renders, because a report renders nested keys.

        A per-path range table becomes visible column headings. A scan that stopped at the top
        level of the summary would clear a manifest whose headings claim a percentile, and the
        heading is what a reader takes away.
        """

        summary = _ensemble_summary()
        summary["path_ranges"][0]["p95_net_market_margin_eur"] = 11.0
        with self.assertRaisesRegex(ReportContractError, "reads as 'p95'"):
            build_run_manifest(
                summary,
                kind_id="scenario_ensemble_range",
                manifest_id="run-2b",
                produced_by="report-scenario-ensemble",
            )

    def test_the_ensemble_records_its_composition_keys(self) -> None:
        """The per-path ranges, the per-scenario provenance and the basis are guaranteed."""

        manifest = build_run_manifest(
            _ensemble_summary(),
            kind_id="scenario_ensemble_range",
            manifest_id="run-2c",
            produced_by="report-scenario-ensemble",
        )
        for key in ("scenarios", "equivalent_basis", "path_count", "path_ranges"):
            self.assertIn(key, RESULT_KINDS["scenario_ensemble_range"].required_summary_keys)
            self.assertIn(key, manifest.summary)

    def test_an_ensemble_summary_without_its_per_path_ranges_is_refused(self) -> None:
        summary = _ensemble_summary()
        del summary["path_ranges"]
        with self.assertRaisesRegex(ReportContractError, "path_ranges"):
            build_run_manifest(
                summary,
                kind_id="scenario_ensemble_range",
                manifest_id="run-2d",
                produced_by="report-scenario-ensemble",
            )

    def test_a_forecast_benchmark_may_report_a_mean_absolute_error(self) -> None:
        # The term list bans claims about the distribution of outcomes, not accuracy
        # statistics about a model. Scoping the check is deliberate, not an oversight.
        manifest = build_run_manifest(
            {"result_label": "research forecast benchmark", "mean_absolute_error": 12.3},
            kind_id="ml_forecast_benchmark",
            manifest_id="run-3",
            produced_by="run-ml-forecast-benchmark",
        )
        self.assertEqual(manifest.basis, "historical_forecast_backtest")

    def test_the_admie_audit_may_report_a_median_lead_time(self) -> None:
        manifest = build_run_manifest(
            {
                "result_label": ADMIE_TIMING_LABEL,
                "timing_accepted": True,
                "quarantine_lifted": False,
                "median_decision_time_lead_minutes": 180.0,
            },
            kind_id="admie_publication_timing_audit",
            manifest_id="run-4",
            produced_by="audit-admie-publication-timing",
        )
        self.assertEqual(manifest.basis, "data_acceptance_evidence")


def _small_battery() -> BatteryDispatchConfig:
    return BatteryDispatchConfig(
        charge_power_mw=1.0,
        discharge_power_mw=1.0,
        energy_capacity_mwh=2.0,
        soc_min_fraction=0.0,
        soc_max_fraction=1.0,
        initial_soc_fraction=0.0,
        terminal_soc_fraction=0.0,
        charge_efficiency=0.95,
        discharge_efficiency=0.95,
    )


class RealSummaryTests(unittest.TestCase):
    """The registry must accept what the modules actually emit, not what a fixture says.

    A hand-written fixture can satisfy a registry that no real summary satisfies. This builds a
    manifest from a summary the optimizer genuinely produced.
    """

    def test_a_real_optimizer_summary_satisfies_its_declared_kind(self) -> None:
        prices = generate_synthetic_prices(
            date(2026, 1, 5), date(2026, 1, 7), negative_price_share=0
        )
        result = optimize_perfect_foresight(
            prices,
            BatteryDispatchConfig(
                charge_power_mw=1.0,
                discharge_power_mw=1.0,
                energy_capacity_mwh=2.0,
                soc_min_fraction=0.0,
                soc_max_fraction=1.0,
                initial_soc_fraction=0.0,
                terminal_soc_fraction=0.0,
                charge_efficiency=0.95,
                discharge_efficiency=0.95,
            ),
        )
        manifest = build_run_manifest(
            result.summary,
            kind_id="perfect_foresight_dispatch",
            manifest_id="real-run",
            produced_by="optimize_perfect_foresight",
        )

        self.assertEqual(manifest.result_label, UPPER_BOUND_LABEL)
        self.assertEqual(manifest.summary, result.summary)

    def test_a_real_backtest_summary_satisfies_the_kind_the_report_workflow_declares(
        self,
    ) -> None:
        """`Render a report from the accepted replay` records this summary under this kind.

        The workflow maps each accepted summary file to a result kind by name. A renamed key or
        a dropped label would break it only when someone dispatched it against real evidence,
        which is the worst place to find out; this fails in the suite instead.
        """

        prices = generate_synthetic_prices(
            date(2026, 1, 5), date(2026, 1, 18), negative_price_share=0
        )
        result = backtest_forecast_dispatch(
            prices, _small_battery(), method="daily_persistence", rolling_window_days=3
        )
        manifest = build_run_manifest(
            result.summary,
            kind_id="forecast_dispatch_backtest",
            manifest_id="real-backtest",
            produced_by="backtest-forecast-dispatch",
        )

        self.assertEqual(manifest.basis, "historical_forecast_backtest")
        self.assertEqual(manifest.summary, result.summary)
        self.assertTrue(manifest.result_label.strip())

    def test_a_real_annual_decomposition_satisfies_the_kind_the_report_workflow_declares(
        self,
    ) -> None:
        prices = generate_synthetic_prices(
            date(2026, 1, 5), date(2026, 1, 18), negative_price_share=0
        )
        ceiling = optimize_daily_perfect_foresight(prices, _small_battery())
        decomposition = decompose_annual_replay(
            prices,
            perfect_foresight_schedule=ceiling.schedule,
            energy_capacity_mwh=2.0,
        )
        manifest = build_run_manifest(
            decomposition.summary,
            kind_id="annual_replay_decomposition",
            manifest_id="real-annual",
            produced_by="decompose-annual-replay",
        )

        self.assertEqual(manifest.basis, "historical_replay_upper_bound")
        self.assertEqual(manifest.summary, decomposition.summary)
        self.assertTrue(manifest.result_label.strip())

    def test_the_real_summary_carries_a_term_a_blanket_ban_would_refuse(self) -> None:
        # `average_charge_price_eur_per_mwh` is a settled input price, not a claim about the
        # distribution of outcomes. It is the concrete reason the distributional-term check is
        # scoped to the kinds that declare it rather than applied to every manifest.
        prices = generate_synthetic_prices(
            date(2026, 1, 5), date(2026, 1, 7), negative_price_share=0
        )
        result = optimize_perfect_foresight(
            prices,
            BatteryDispatchConfig(
                charge_power_mw=1.0,
                discharge_power_mw=1.0,
                energy_capacity_mwh=2.0,
                soc_min_fraction=0.0,
                soc_max_fraction=1.0,
                initial_soc_fraction=0.0,
                terminal_soc_fraction=0.0,
                charge_efficiency=0.95,
                discharge_efficiency=0.95,
            ),
        )

        self.assertIn("average_charge_price_eur_per_mwh", result.summary)
        self.assertFalse(RESULT_KINDS["perfect_foresight_dispatch"].forbids_distributional_terms)


class AcceptedReplayPublicationWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = Path(".github/workflows/render-accepted-replay-report.yml").read_text(
            encoding="utf-8"
        )

    def test_pages_publication_cannot_run_until_the_refusal_gated_render_job_passes(self) -> None:
        publish = self.workflow.split("\n  publish:\n", maxsplit=1)[1]

        self.assertIn("    needs: render\n", publish)
        self.assertIn("      pages: write\n", publish)
        self.assertIn("      id-token: write\n", publish)
        self.assertIn("uses: actions/deploy-pages@v4", publish)

    def test_pages_artifact_contains_only_the_aggregate_report_and_index(self) -> None:
        publish = self.workflow.split("\n  publish:\n", maxsplit=1)[1]

        self.assertIn(
            "cp report/accepted_replay_report.html site/accepted-replay/index.html", publish
        )
        self.assertIn(
            "site/accepted-replay/accepted_replay_report.index.json\\n"
            "site/accepted-replay/index.html",
            publish,
        )
        self.assertNotIn("cp report/manifests", publish)
        self.assertNotIn("cp report/source_custody_verification", publish)

    def test_complete_evidence_bundle_remains_a_private_actions_artifact(self) -> None:
        render = self.workflow.split("\n  publish:\n", maxsplit=1)[0]

        self.assertIn("report/manifests/*.manifest.json", render)
        self.assertIn("report/source_custody_verification.json", render)
        self.assertIn("retention-days: 90", render)


class RoundTripTests(unittest.TestCase):
    def test_a_manifest_round_trips(self) -> None:
        manifest = _build(_dispatch_summary(), declared_inputs={"prices": "history.csv"})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.manifest.json"
            write_run_manifest(path, manifest)
            restored = read_run_manifest(path)

        self.assertEqual(restored.to_dict(), manifest.to_dict())

    def test_a_newer_schema_version_is_refused_rather_than_read(self) -> None:
        manifest = _build(_dispatch_summary()).to_dict()
        manifest["schema_version"] = REPORT_CONTRACT_VERSION + 1
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ReportContractError, "newer contract is refused"):
                read_run_manifest(path)

    def test_a_basis_that_disagrees_with_its_kind_is_refused(self) -> None:
        manifest = _build(_dispatch_summary()).to_dict()
        manifest["basis"] = "synthetic_scenario"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ReportContractError, "which reports on"):
                read_run_manifest(path)

    def test_a_manifest_missing_required_fields_is_refused(self) -> None:
        manifest = _build(_dispatch_summary()).to_dict()
        del manifest["result_label"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ReportContractError, "missing required fields"):
                read_run_manifest(path)


class ReadPathClaimTests(unittest.TestCase):
    """What reading refuses, and what it deliberately does not.

    Building a manifest is not the only way one reaches a consumer: a manifest travels, and a
    reader has only the file. The checks that are properties of the recorded content therefore
    run on read as well, while the guaranteed-key check — a promise about what a producing
    module recorded at the time — stays a record-time check so that a manifest written before a
    kind guaranteed a key still verifies.
    """

    def _written(self, directory: str, manifest: dict[str, Any]) -> Path:
        path = Path(directory) / "run.manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def test_a_summary_contradicting_a_standing_claim_is_refused_on_read(self) -> None:
        manifest = _build(_dispatch_summary()).to_dict()
        manifest["summary"]["is_probabilistic"] = True
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ReportContractError, "contradicting the standing"):
                read_run_manifest(self._written(directory, manifest))

    def test_a_distributional_key_is_refused_on_read_for_a_kind_that_forbids_it(self) -> None:
        manifest = _build(
            _ensemble_summary(), kind_id="scenario_ensemble_range", manifest_id="ensemble-1"
        ).to_dict()
        manifest["summary"]["path_ranges"][0]["p95_margin_eur"] = 1.0
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ReportContractError, "p95"):
                read_run_manifest(self._written(directory, manifest))

    def test_declared_inputs_that_are_not_an_object_are_refused_on_read(self) -> None:
        manifest = _build(_dispatch_summary()).to_dict()
        manifest["declared_inputs"] = ["prices.csv"]
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ReportContractError, "declared_inputs must be an object"):
                read_run_manifest(self._written(directory, manifest))

    def test_a_manifest_missing_a_guaranteed_summary_key_still_reads(self) -> None:
        """The record-time guarantee is not retroactively applied to a recorded manifest."""

        manifest = _build(_dispatch_summary()).to_dict()
        del manifest["summary"]["interval_count"]
        with tempfile.TemporaryDirectory() as directory:
            restored = read_run_manifest(self._written(directory, manifest))

        self.assertNotIn("interval_count", restored.summary)
        self.assertEqual(restored.result_kind, "perfect_foresight_dispatch")


class CliTests(unittest.TestCase):
    def test_record_and_verify_round_trip_through_the_cli(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary = root / "dispatch.summary.json"
            summary.write_text(json.dumps(_dispatch_summary()), encoding="utf-8")
            output = root / "dispatch.manifest.json"
            with redirect_stdout(io.StringIO()):
                record_code = main(
                    [
                        "record-run-manifest",
                        str(summary),
                        "--result-kind",
                        "perfect_foresight_dispatch",
                        "--manifest-id",
                        "cli-run",
                        "--produced-by",
                        "optimize-perfect-foresight",
                        "--output",
                        str(output),
                    ]
                )
            written = json.loads(output.read_text(encoding="utf-8"))
            verify_out = io.StringIO()
            with redirect_stdout(verify_out):
                verify_code = main(["verify-run-manifest", str(output)])

        self.assertEqual(record_code, 0)
        self.assertEqual(verify_code, 0)
        self.assertEqual(written["result_kind"], "perfect_foresight_dispatch")
        self.assertEqual(written["basis"], "historical_replay_upper_bound")
        verified = json.loads(verify_out.getvalue())
        self.assertEqual(verified["basis"], "historical_replay_upper_bound")

    def test_the_cli_reports_a_contract_refusal_as_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary = root / "dispatch.summary.json"
            payload = _dispatch_summary()
            del payload["result_label"]
            summary.write_text(json.dumps(payload), encoding="utf-8")
            errors = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(errors):
                code = main(
                    [
                        "record-run-manifest",
                        str(summary),
                        "--result-kind",
                        "perfect_foresight_dispatch",
                        "--manifest-id",
                        "cli-run",
                        "--produced-by",
                        "optimize-perfect-foresight",
                        "--output",
                        str(root / "out.json"),
                    ]
                )

        self.assertEqual(code, 1)
        self.assertIn("result_label", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
