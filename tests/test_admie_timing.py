"""Publication-timing acceptance for the quarantined ADMIE forecast files.

The audit answers one question per delivery day: was a file published strictly before that
day's declared gate closure, and how strong is the evidence that it was. These tests pin the
refusals as firmly as the arithmetic, because an audit that silently assumes a closure time,
promotes an asserted timestamp to a witnessed one, or treats a missing day as a compliant one
would be worse than no audit at all.
"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, time
from pathlib import Path
from typing import Any

from greek_bess.cli import main
from greek_bess.data.admie_timing import (
    ASSERTED_PRE_GATE,
    NO_PRE_GATE_PUBLICATION,
    NO_RECORD,
    WITNESSED_PRE_GATE,
    AdmiePublicationTimingError,
    GateClosureRegime,
    GateClosureSchedule,
    audit_admie_publication_timing,
    read_retrieval_manifests,
)

ATHENS_NOON_D_MINUS_1 = {
    "effective_from_delivery_day": "2020-11-01",
    "closure_day_offset": -1,
    "closure_local_time": "12:00:00",
    "closure_timezone": "Europe/Athens",
    "reference": "Declared for tests; the operator supplies the market rule citation.",
}


def _schedule(*regimes: dict[str, Any]) -> GateClosureSchedule:
    return GateClosureSchedule.from_dict(
        {
            "schedule_id": "test-schedule",
            "regimes": list(regimes) or [ATHENS_NOON_D_MINUS_1],
        }
    )


def _record(
    *,
    published_at_utc: str,
    retrieved_at_utc: str = "2026-08-27T06:00:00+00:00",
    coverage_start: str = "2026-08-26",
    coverage_end: str = "2026-08-26",
    revision: int | None = 1,
    filetype: str = "DayAheadLoadForecast",
    sha256: str = "a" * 64,
    url: str | None = None,
) -> dict[str, Any]:
    return {
        "source": "admie",
        "dataset": filetype,
        "source_url": url
        or f"https://www.admie.gr/sites/default/files/x/{coverage_start}_{filetype}_{revision}.xlsx",
        "local_path": "x.xlsx",
        "retrieved_at_utc": retrieved_at_utc,
        "sha256": sha256,
        "size_bytes": 10,
        "coverage_start": coverage_start,
        "coverage_end": coverage_end,
        "published_at_source": "25.08.2026 09:00",
        "published_at_utc": published_at_utc,
        "revision": revision,
        "availability_classification": "requires_pre_auction_timing_validation",
    }


def _audit(records: list[dict[str, Any]], **overrides: Any) -> Any:
    parameters: dict[str, Any] = {
        "schedule": _schedule(),
        "filetypes": ["DayAheadLoadForecast"],
        "start_day": date(2026, 8, 26),
        "end_day": date(2026, 8, 26),
    }
    parameters.update(overrides)
    return audit_admie_publication_timing(records, **parameters)


class GateClosureScheduleTests(unittest.TestCase):
    def test_the_closure_is_resolved_on_the_declared_clock(self) -> None:
        # Noon Athens on 25 August 2026 is 09:00 UTC under EEST.
        closure = _schedule().closure_utc(date(2026, 8, 26))
        self.assertEqual(closure.isoformat(), "2026-08-25T09:00:00+00:00")

    def test_a_later_regime_governs_the_days_it_covers(self) -> None:
        schedule = _schedule(
            ATHENS_NOON_D_MINUS_1,
            {
                "effective_from_delivery_day": "2025-10-01",
                "closure_day_offset": -1,
                "closure_local_time": "10:30:00",
                "closure_timezone": "Europe/Brussels",
                "reference": "A later declared regime.",
            },
        )
        self.assertEqual(
            schedule.closure_utc(date(2025, 9, 30)).isoformat(), "2025-09-29T09:00:00+00:00"
        )
        self.assertEqual(
            schedule.closure_utc(date(2025, 10, 1)).isoformat(), "2025-09-30T08:30:00+00:00"
        )

    def test_a_day_before_the_first_regime_is_refused(self) -> None:
        with self.assertRaisesRegex(AdmiePublicationTimingError, "precedes the first declared"):
            _schedule().closure_utc(date(2020, 10, 31))

    def test_a_closure_inside_a_daylight_saving_gap_is_refused(self) -> None:
        schedule = _schedule(
            {
                "effective_from_delivery_day": "2020-11-01",
                "closure_day_offset": -1,
                "closure_local_time": "03:30:00",
                "closure_timezone": "Europe/Athens",
                "reference": "Deliberately inside the spring-forward gap.",
            }
        )
        with self.assertRaisesRegex(AdmiePublicationTimingError, "daylight-saving transition"):
            schedule.closure_utc(date(2026, 3, 30))

    def test_a_schedule_without_a_regime_is_refused(self) -> None:
        with self.assertRaisesRegex(AdmiePublicationTimingError, "at least one regime"):
            GateClosureSchedule.from_dict({"schedule_id": "empty", "regimes": []})

    def test_unordered_and_duplicated_regimes_are_refused(self) -> None:
        later = dict(ATHENS_NOON_D_MINUS_1, effective_from_delivery_day="2024-01-01")
        with self.assertRaisesRegex(AdmiePublicationTimingError, "ascending"):
            GateClosureSchedule.from_dict(
                {"schedule_id": "x", "regimes": [later, ATHENS_NOON_D_MINUS_1]}
            )
        with self.assertRaisesRegex(AdmiePublicationTimingError, "share an"):
            GateClosureSchedule.from_dict(
                {"schedule_id": "x", "regimes": [later, dict(later)]}
            )

    def test_a_closure_after_the_delivery_day_starts_is_refused(self) -> None:
        with self.assertRaisesRegex(AdmiePublicationTimingError, "must not be positive"):
            GateClosureRegime(
                effective_from_delivery_day=date(2020, 11, 1),
                closure_day_offset=1,
                closure_local_time=time(12, 0),
                closure_timezone="Europe/Athens",
                reference="x",
            )

    def test_an_undeclared_clock_and_a_missing_reference_are_refused(self) -> None:
        with self.assertRaisesRegex(AdmiePublicationTimingError, "closure_timezone"):
            GateClosureRegime(
                effective_from_delivery_day=date(2020, 11, 1),
                closure_day_offset=-1,
                closure_local_time=time(12, 0),
                closure_timezone="Europe/London",
                reference="x",
            )
        with self.assertRaisesRegex(AdmiePublicationTimingError, "reference must name"):
            GateClosureRegime(
                effective_from_delivery_day=date(2020, 11, 1),
                closure_day_offset=-1,
                closure_local_time=time(12, 0),
                closure_timezone="Europe/Athens",
                reference="  ",
            )

    def test_unknown_configuration_fields_are_refused(self) -> None:
        with self.assertRaisesRegex(AdmiePublicationTimingError, "Unknown gate-closure regime"):
            GateClosureSchedule.from_dict(
                {
                    "schedule_id": "x",
                    "regimes": [dict(ATHENS_NOON_D_MINUS_1, closure_minutes=10)],
                }
            )


class PublicationTimingAuditTests(unittest.TestCase):
    def test_the_decision_time_revision_is_the_latest_published_before_closure(self) -> None:
        audit = _audit(
            [
                _record(published_at_utc="2026-08-25T06:00:00+00:00", revision=1),
                _record(published_at_utc="2026-08-25T08:30:00+00:00", revision=2),
                _record(published_at_utc="2026-08-25T13:00:00+00:00", revision=3),
            ]
        )
        day = audit.delivery_days.iloc[0]

        self.assertEqual(day["day_status"], ASSERTED_PRE_GATE)
        self.assertEqual(day["decision_time_revision"], 2)
        self.assertEqual(day["pre_gate_record_count"], 2)
        self.assertEqual(day["post_gate_record_count"], 1)
        self.assertEqual(day["superseded_after_gate_closure_count"], 1)
        self.assertEqual(day["decision_time_lead_minutes"], 30.0)
        self.assertTrue(audit.summary["timing_accepted"])
        self.assertFalse(audit.summary["timing_accepted_with_contemporaneous_witness"])
        self.assertEqual(audit.summary["evidence_basis"], "publisher_asserted_timestamps")

    def test_a_retrieval_before_closure_witnesses_availability(self) -> None:
        audit = _audit(
            [
                _record(
                    published_at_utc="2026-08-25T06:00:00+00:00",
                    retrieved_at_utc="2026-08-25T07:00:00+00:00",
                )
            ]
        )
        day = audit.delivery_days.iloc[0]

        self.assertEqual(day["day_status"], WITNESSED_PRE_GATE)
        self.assertEqual(day["witnessed_pre_gate_record_count"], 1)
        self.assertEqual(day["decision_time_evidence_strength"], "witnessed_at_retrieval")
        self.assertTrue(audit.summary["timing_accepted_with_contemporaneous_witness"])
        self.assertEqual(audit.summary["evidence_basis"], "contemporaneous_retrieval_witness")

    def test_publication_exactly_at_the_closure_counts_as_late(self) -> None:
        audit = _audit([_record(published_at_utc="2026-08-25T09:00:00+00:00")])
        day = audit.delivery_days.iloc[0]

        self.assertEqual(day["day_status"], NO_PRE_GATE_PUBLICATION)
        self.assertIsNone(day["decision_time_source_url"])
        self.assertEqual(day["post_gate_record_count"], 1)
        # Nothing was superseded: there was no usable revision for a later one to replace.
        self.assertEqual(day["superseded_after_gate_closure_count"], 0)
        self.assertFalse(audit.summary["timing_accepted"])
        self.assertEqual(audit.summary["findings"][0]["code"], NO_PRE_GATE_PUBLICATION)

    def test_a_delivery_day_no_record_covers_is_reported_as_a_gap(self) -> None:
        audit = _audit(
            [_record(published_at_utc="2026-08-25T06:00:00+00:00")],
            start_day=date(2026, 8, 26),
            end_day=date(2026, 8, 27),
        )
        statuses = dict(
            zip(
                audit.delivery_days["delivery_day"],
                audit.delivery_days["day_status"],
                strict=True,
            )
        )

        self.assertEqual(statuses["2026-08-26"], ASSERTED_PRE_GATE)
        self.assertEqual(statuses["2026-08-27"], NO_RECORD)
        self.assertFalse(audit.summary["timing_accepted"])
        self.assertEqual(audit.summary["day_status_counts"][NO_RECORD], 1)

    def test_a_multi_day_file_is_judged_separately_for_each_day_it_covers(self) -> None:
        # One monthly file published on 15 August is late for 10 August and early for 20 August.
        audit = _audit(
            [
                _record(
                    published_at_utc="2026-08-15T06:00:00+00:00",
                    retrieved_at_utc="2026-08-30T06:00:00+00:00",
                    coverage_start="2026-08-01",
                    coverage_end="2026-08-31",
                )
            ],
            start_day=date(2026, 8, 10),
            end_day=date(2026, 8, 20),
        )
        statuses = dict(
            zip(
                audit.delivery_days["delivery_day"],
                audit.delivery_days["day_status"],
                strict=True,
            )
        )

        self.assertEqual(statuses["2026-08-10"], NO_PRE_GATE_PUBLICATION)
        self.assertEqual(statuses["2026-08-20"], ASSERTED_PRE_GATE)
        self.assertEqual(audit.summary["observation_count"], 11)
        self.assertFalse(audit.summary["timing_accepted"])

    def test_every_requested_filetype_is_audited_over_every_day(self) -> None:
        audit = _audit(
            [_record(published_at_utc="2026-08-25T06:00:00+00:00")],
            filetypes=["DayAheadLoadForecast", "DayAheadRESForecast"],
        )
        per_filetype = audit.summary["per_filetype"]

        self.assertEqual(per_filetype["DayAheadLoadForecast"]["accepted_day_count"], 1)
        self.assertEqual(per_filetype["DayAheadRESForecast"]["accepted_day_count"], 0)
        self.assertEqual(
            per_filetype["DayAheadRESForecast"]["day_status_counts"], {NO_RECORD: 1}
        )

    def test_records_outside_the_window_or_filetype_set_are_counted_not_audited(self) -> None:
        audit = _audit(
            [
                _record(published_at_utc="2026-08-25T06:00:00+00:00"),
                _record(
                    published_at_utc="2026-08-25T06:00:00+00:00",
                    filetype="ISP1DayAheadRESForecast",
                ),
                _record(
                    published_at_utc="2026-01-01T06:00:00+00:00",
                    coverage_start="2026-01-02",
                    coverage_end="2026-01-02",
                ),
            ]
        )
        self.assertEqual(audit.summary["ignored_record_count"], 2)
        self.assertEqual(audit.summary["observation_count"], 1)

    def test_the_summary_states_what_the_audit_does_not_establish(self) -> None:
        audit = _audit([_record(published_at_utc="2026-08-25T06:00:00+00:00")])
        summary = audit.summary

        self.assertTrue(summary["establishes_only_publication_timing"])
        self.assertFalse(summary["quarantine_lifted"])
        self.assertIn(
            "the file format, column schema or units of any audited file",
            summary["does_not_establish"],
        )
        self.assertEqual(summary["gate_closure_schedule"]["schedule_id"], "test-schedule")
        self.assertIn("declared", summary["policy"])

    def test_every_observation_carries_the_closure_and_the_rule_behind_it(self) -> None:
        audit = _audit([_record(published_at_utc="2026-08-25T06:00:00+00:00")])
        observation = audit.observations.iloc[0]

        self.assertEqual(observation["gate_closure_utc"], "2026-08-25T09:00:00+00:00")
        self.assertEqual(observation["gate_closure_regime_from"], "2020-11-01")
        self.assertIn("operator supplies", observation["gate_closure_reference"])
        self.assertEqual(observation["publication_lead_minutes"], 180.0)
        self.assertEqual(
            observation["availability_classification"], "requires_pre_auction_timing_validation"
        )

    def test_a_revision_stays_an_integer_beside_days_that_have_none(self) -> None:
        audit = _audit(
            [_record(published_at_utc="2026-08-25T06:00:00+00:00")],
            filetypes=["DayAheadLoadForecast", "DayAheadRESForecast"],
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "days.csv"
            audit.delivery_days.to_csv(path, index=False)
            exported = path.read_text(encoding="utf-8")

        self.assertIn(",1,", exported)
        self.assertNotIn("1.0", exported)

    def test_an_empty_or_duplicated_filetype_request_is_refused(self) -> None:
        with self.assertRaisesRegex(AdmiePublicationTimingError, "no default filetype set"):
            _audit([], filetypes=[])
        with self.assertRaisesRegex(AdmiePublicationTimingError, "Duplicate filetypes"):
            _audit([], filetypes=["DayAheadLoadForecast", "DayAheadLoadForecast"])

    def test_a_reversed_audit_window_is_refused(self) -> None:
        with self.assertRaisesRegex(AdmiePublicationTimingError, "must not precede start_day"):
            _audit([], start_day=date(2026, 8, 27), end_day=date(2026, 8, 26))

    def test_incoherent_and_foreign_records_are_refused(self) -> None:
        with self.assertRaisesRegex(AdmiePublicationTimingError, "not an ADMIE record"):
            _audit([dict(_record(published_at_utc="2026-08-25T06:00:00+00:00"), source="entsoe")])
        with self.assertRaisesRegex(AdmiePublicationTimingError, "cannot be retrieved before"):
            _audit(
                [
                    _record(
                        published_at_utc="2026-08-28T06:00:00+00:00",
                        retrieved_at_utc="2026-08-27T06:00:00+00:00",
                    )
                ]
            )
        with self.assertRaisesRegex(AdmiePublicationTimingError, "timezone aware"):
            _audit([_record(published_at_utc="2026-08-25T06:00:00")])
        naive = _record(published_at_utc="2026-08-25T06:00:00+00:00")
        del naive["published_at_utc"]
        with self.assertRaisesRegex(AdmiePublicationTimingError, "missing required fields"):
            _audit([naive])


class ManifestReadingTests(unittest.TestCase):
    def test_identical_records_across_manifests_are_read_once(self) -> None:
        record = _record(published_at_utc="2026-08-25T06:00:00+00:00")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for index in (1, 2):
                path = root / f"manifest_{index}.json"
                path.write_text(json.dumps({"schema_version": 1, "records": [record]}))
                paths.append(path)
            records = read_retrieval_manifests(paths)

        self.assertEqual(len(records), 1)

    def test_one_url_with_two_digests_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "a.json"
            second = root / "b.json"
            first.write_text(
                json.dumps(
                    {
                        "records": [
                            _record(published_at_utc="2026-08-25T06:00:00+00:00", sha256="a" * 64)
                        ]
                    }
                )
            )
            second.write_text(
                json.dumps(
                    {
                        "records": [
                            _record(published_at_utc="2026-08-25T06:00:00+00:00", sha256="b" * 64)
                        ]
                    }
                )
            )
            with self.assertRaisesRegex(AdmiePublicationTimingError, "replaced in place"):
                read_retrieval_manifests([first, second])

    def test_one_url_with_two_publication_timestamps_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for index, published in enumerate(
                ("2026-08-25T06:00:00+00:00", "2026-08-25T10:00:00+00:00")
            ):
                path = root / f"m{index}.json"
                path.write_text(json.dumps({"records": [_record(published_at_utc=published)]}))
                paths.append(path)
            with self.assertRaisesRegex(AdmiePublicationTimingError, "restated publication time"):
                read_retrieval_manifests(paths)

    def test_a_manifest_without_records_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps({"schema_version": 1}))
            with self.assertRaisesRegex(AdmiePublicationTimingError, "'records' list"):
                read_retrieval_manifests([path])


class CliTests(unittest.TestCase):
    def _run(self, root: Path, records: list[dict[str, Any]], **overrides: str) -> tuple[int, Any]:
        manifest = root / "retrieval_manifest.json"
        manifest.write_text(json.dumps({"schema_version": 1, "records": records}))
        closure = root / "gate_closure.json"
        closure.write_text(
            json.dumps({"schedule_id": "cli-schedule", "regimes": [ATHENS_NOON_D_MINUS_1]})
        )
        output = root / "delivery_days.csv"
        argv = [
            "audit-admie-publication-timing",
            str(manifest),
            "--gate-closure",
            str(closure),
            "--filetypes",
            "DayAheadLoadForecast",
            "--start-day",
            overrides.get("start_day", "2026-08-26"),
            "--end-day",
            overrides.get("end_day", "2026-08-26"),
            "--output",
            str(output),
        ]
        buffer = io.StringIO()
        with redirect_stdout(buffer), redirect_stderr(io.StringIO()):
            code = main(argv)
        summary = json.loads((root / "delivery_days.summary.json").read_text(encoding="utf-8"))
        return code, summary

    def test_the_command_writes_evidence_and_exits_zero_when_timing_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code, summary = self._run(
                root, [_record(published_at_utc="2026-08-25T06:00:00+00:00")]
            )
            days = (root / "delivery_days.csv").read_text(encoding="utf-8")
            observations = (root / "delivery_days.observations.csv").read_text(encoding="utf-8")

        self.assertEqual(code, 0)
        self.assertTrue(summary["timing_accepted"])
        self.assertFalse(summary["quarantine_lifted"])
        self.assertIn(ASSERTED_PRE_GATE, days)
        self.assertIn("published_before_gate_closure", observations)

    def test_the_command_exits_two_on_a_recorded_timing_finding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code, summary = self._run(
                root, [_record(published_at_utc="2026-08-25T10:00:00+00:00")]
            )

        self.assertEqual(code, 2)
        self.assertFalse(summary["timing_accepted"])
        self.assertEqual(summary["finding_count"], 1)

    def test_the_command_reports_a_configuration_refusal_as_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "m.json"
            manifest.write_text(json.dumps({"schema_version": 1, "records": []}))
            closure = root / "closure.json"
            closure.write_text(json.dumps({"schedule_id": "x", "regimes": []}))
            errors = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(errors):
                code = main(
                    [
                        "audit-admie-publication-timing",
                        str(manifest),
                        "--gate-closure",
                        str(closure),
                        "--filetypes",
                        "DayAheadLoadForecast",
                        "--start-day",
                        "2026-08-26",
                        "--end-day",
                        "2026-08-26",
                        "--output",
                        str(root / "days.csv"),
                    ]
                )

        self.assertEqual(code, 1)
        self.assertIn("at least one regime", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
