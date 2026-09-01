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

from greek_bess.cli import main
from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.dispatch import BatteryDispatchConfig, optimize_perfect_foresight
from greek_bess.reporting import (
    BASIS_WORDING,
    DECLARATION_CHECKLIST,
    RESULT_BASES,
    RESULT_KINDS,
    STANDING_EXCLUSIONS,
    ReportContractError,
    ReportRenderError,
    ResultKind,
    build_run_manifest,
    render_report,
    write_report,
    write_run_manifest,
)
from greek_bess.stress.ensemble import FORBIDDEN_REPORT_TERMS

#: One realistic value for each guaranteed summary key in the registry, so a manifest can be
#: built for every kind without running sixteen modules.
GUARANTEED_VALUES: dict[str, Any] = {
    "interval_count": 96,
    "net_market_margin_eur": 1234.5,
    "scenario_count": 2,
    "scenario_names": ["baseline", "declared_outage"],
    "operating_margin_case": "illustrative_supplied_operating_margin",
    "timing_accepted": True,
    "quarantine_lifted": False,
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
    manifest = build_run_manifest(
        _summary_for(kind),
        kind_id=kind.kind_id,
        manifest_id=identifier,
        produced_by=f"{kind.kind_id}-command",
        created_at_utc="2026-09-01T12:00:00+00:00",
    )
    path = directory / f"{identifier}.manifest.json"
    write_run_manifest(path, manifest)
    return path


def _blocks(document: str) -> dict[str, str]:
    return {match.group("anchor"): match.group("body") for match in FIGURE_BLOCK.finditer(document)}


def _main_text(document: str) -> str:
    body = MAIN_REGION.search(document)
    assert body is not None
    return html_module.unescape(TAG.sub(" ", body.group("body")))


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
            self.assertEqual(len(report.figures), sum(len(s) - 1 for s in recorded.values()))
            for figure in report.figures:
                summary = recorded[figure.manifest_id]
                self.assertIn(figure.key, summary)
                value = summary[figure.key]
                expected = value if isinstance(value, str) else json.dumps(value, default=str)
                self.assertEqual(figure.value_text, expected)

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
                self.assertIn(figure.value_text, json.dumps(recorded, default=str))

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
