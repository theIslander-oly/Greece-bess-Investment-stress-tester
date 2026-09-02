"""Availability of point-in-time feature values against a declared decision cutoff.

Mirrors `tests/test_admie_timing.py` in intent and structure: the refusals are pinned as firmly
as the arithmetic, because an audit that assumed a cutoff, promoted inferred evidence, inferred
one forecast step's availability from another's, or counted a thin day as complete would be worse
than no audit at all. Design section 11 cases 6 and 9 are here by name, alongside the two facts
the source spike turned into requirements: per-step checking, and a genuinely late run.
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

import pandas as pd

from greek_bess.cli import main
from greek_bess.data.availability_audit import (
    ACCEPTABLE_FEATURE_DAY_STATUSES,
    ALL_PUBLICATIONS_AFTER_CUTOFF,
    ASSUMED_GRADE_EXPLORATORY,
    GRADE_NOT_ADMITTED,
    INCOMPLETE_BEFORE_CUTOFF,
    NO_PUBLICATION,
    PROVIDER_DECLARED_BEFORE_CUTOFF,
    WITNESSED_BEFORE_CUTOFF,
    FeatureAvailabilityError,
    audit_feature_availability,
    effective_evidence_grade,
    expected_feature_interval_count,
)
from greek_bess.data.decision_cutoff import (
    DecisionCutoffError,
    GateClosureRegime,
    GateClosureSchedule,
)
from greek_bess.data.point_in_time import (
    ADMISSIBLE_EVIDENCE_GRADES,
    ASSUMED,
    PROVIDER_DECLARED,
    UNAVAILABLE,
    WITNESSED,
    ensure_point_in_time,
    write_point_in_time_csv,
)
from greek_bess.data.timezones import UTC, market_day_starts

DELIVERY_DAY = date(2026, 8, 26)
# Noon Athens on 25 August 2026 is 09:00 UTC; with a 30-minute lead the cutoff is 08:30 UTC.
DECLARED_REGIME: dict[str, Any] = {
    "effective_from_delivery_day": "2020-11-01",
    "closure_day_offset": -1,
    "closure_local_time": "12:00:00",
    "closure_timezone": "Europe/Athens",
    "reference": "Declared for tests; the operator supplies the market rule citation.",
}
CUTOFF_AT_LEAD_30 = pd.Timestamp("2026-08-25T08:30:00+00:00")


def _schedule() -> GateClosureSchedule:
    return GateClosureSchedule.from_dict(
        {"schedule_id": "test-cutoff", "regimes": [DECLARED_REGIME]}
    )


def _rows(
    delivery_day: date = DELIVERY_DAY,
    *,
    published: str = "2026-08-25T04:00:00+00:00",
    retrieved: str = "2026-08-26T12:00:00+00:00",
    grade: str = PROVIDER_DECLARED,
    variable: str = "temperature_2m",
    intervals: int | None = None,
    late_interval: int | None = None,
    late_published: str = "2026-08-25T10:00:00+00:00",
) -> pd.DataFrame:
    """One complete hourly day, optionally with one interval published late."""

    starts = market_day_starts(delivery_day, 60).tz_convert(UTC)
    if intervals is not None:
        starts = starts[:intervals]
    rows = []
    for index, start in enumerate(starts):
        instant = late_published if index == late_interval else published
        rows.append(
            {
                "delivery_start_utc": start,
                "delivery_end_utc": start + pd.Timedelta(60, unit="min"),
                "market_day": None,
                "source": "noaa_gfs",
                "dataset": "gfs.0p25",
                "variable": variable,
                "area": "GR",
                "unit": "K" if variable == "temperature_2m" else "W/m2",
                "resolution_minutes": 60,
                "value": 300.0 + index,
                "published_at_utc": pd.Timestamp(instant),
                "retrieved_at_utc": pd.Timestamp(retrieved),
                "source_document_id": f"gfs.20260825/00/atmos/f{index:03d}",
                "source_revision": None,
                "raw_sha256": f"{index:064x}",
                "forecast_issue_time_utc": pd.Timestamp("2026-08-25T00:00:00+00:00"),
                "forecast_horizon_minutes": None,
                "availability_evidence_grade": grade,
                "availability_evidence_detail": "s3_last_modified",
            }
        )
    return ensure_point_in_time(pd.DataFrame(rows))


def _audit(features: pd.DataFrame, **overrides: Any) -> Any:
    parameters: dict[str, Any] = {
        "schedule": _schedule(),
        "decision_lead_minutes": 30,
        "variables": ["temperature_2m"],
        "area": "GR",
        "start_day": DELIVERY_DAY,
        "end_day": DELIVERY_DAY,
    }
    parameters.update(overrides)
    return audit_feature_availability(features, **parameters)


class EffectiveGradeTests(unittest.TestCase):
    """The grade is derived from the row's own instants, and quarantine is never lifted."""

    def test_a_retrieval_before_the_cutoff_witnesses_availability(self) -> None:
        self.assertEqual(
            effective_evidence_grade(
                PROVIDER_DECLARED,
                pd.Timestamp("2026-08-25T04:00:00+00:00"),
                pd.Timestamp("2026-08-25T05:00:00+00:00"),
                CUTOFF_AT_LEAD_30,
            ),
            WITNESSED,
        )

    def test_a_retrieval_after_the_cutoff_only_carries_the_provider_instant(self) -> None:
        self.assertEqual(
            effective_evidence_grade(
                WITNESSED,
                pd.Timestamp("2026-08-25T04:00:00+00:00"),
                pd.Timestamp("2026-08-27T05:00:00+00:00"),
                CUTOFF_AT_LEAD_30,
            ),
            PROVIDER_DECLARED,
        )

    def test_a_publication_at_the_cutoff_is_late(self) -> None:
        """Design section 11, case 6."""

        self.assertEqual(
            effective_evidence_grade(
                PROVIDER_DECLARED, CUTOFF_AT_LEAD_30, CUTOFF_AT_LEAD_30, CUTOFF_AT_LEAD_30
            ),
            UNAVAILABLE,
        )
        self.assertEqual(
            effective_evidence_grade(
                PROVIDER_DECLARED,
                CUTOFF_AT_LEAD_30 - pd.Timedelta(1, unit="s"),
                CUTOFF_AT_LEAD_30,
                CUTOFF_AT_LEAD_30,
            ),
            PROVIDER_DECLARED,
        )

    def test_the_quarantined_grade_is_never_earned_back_by_early_timestamps(self) -> None:
        self.assertEqual(
            effective_evidence_grade(
                ASSUMED,
                pd.Timestamp("2020-01-01T00:00:00+00:00"),
                pd.Timestamp("2020-01-01T00:00:00+00:00"),
                CUTOFF_AT_LEAD_30,
            ),
            ASSUMED,
        )


class DayVerdictTests(unittest.TestCase):
    def test_a_complete_day_published_in_time_is_provider_declared(self) -> None:
        audit = _audit(_rows())
        self.assertEqual(audit.delivery_days.at[0, "day_status"], PROVIDER_DECLARED_BEFORE_CUTOFF)
        self.assertEqual(audit.delivery_days.at[0, "covered_interval_count"], 24)
        self.assertEqual(audit.delivery_days.at[0, "expected_interval_count"], 24)
        self.assertTrue(audit.summary["availability_accepted"])
        self.assertEqual(
            audit.summary["evidence_basis"], "provider_declared_publication_instants"
        )

    def test_a_day_retrieved_before_the_cutoff_is_witnessed_and_reported_separately(
        self,
    ) -> None:
        audit = _audit(_rows(retrieved="2026-08-25T05:00:00+00:00"))
        self.assertEqual(audit.delivery_days.at[0, "day_status"], WITNESSED_BEFORE_CUTOFF)
        self.assertEqual(audit.summary["witnessed_day_count"], 1)
        self.assertEqual(audit.summary["evidence_basis"], "contemporaneous_retrieval_witness")
        self.assertTrue(
            audit.summary["availability_accepted_with_contemporaneous_witness"]
        )

    def test_one_late_forecast_step_makes_the_whole_day_incomplete(self) -> None:
        """The spike's 14 June 2021 case: one object late, and the day is excluded by name."""

        audit = _audit(_rows(late_interval=7))
        self.assertEqual(audit.delivery_days.at[0, "day_status"], INCOMPLETE_BEFORE_CUTOFF)
        self.assertEqual(audit.delivery_days.at[0, "covered_interval_count"], 23)
        self.assertFalse(audit.summary["availability_accepted"])
        self.assertEqual(audit.summary["findings"][0]["code"], INCOMPLETE_BEFORE_CUTOFF)

    def test_one_step_being_in_time_does_not_speak_for_another(self) -> None:
        """Upload order is not monotone in step, so availability is per interval."""

        early_then_late = _audit(_rows(late_interval=0))
        late_then_early = _audit(_rows(late_interval=23))
        for audit in (early_then_late, late_then_early):
            self.assertEqual(
                audit.delivery_days.at[0, "day_status"], INCOMPLETE_BEFORE_CUTOFF
            )
            self.assertEqual(audit.delivery_days.at[0, "covered_interval_count"], 23)

    def test_a_day_with_every_publication_after_the_cutoff_is_named_as_such(self) -> None:
        audit = _audit(_rows(published="2026-08-25T10:00:00+00:00"))
        self.assertEqual(
            audit.delivery_days.at[0, "day_status"], ALL_PUBLICATIONS_AFTER_CUTOFF
        )
        self.assertEqual(audit.delivery_days.at[0, "covered_interval_count"], 0)

    def test_a_day_with_no_rows_is_a_gap_never_a_compliant_day(self) -> None:
        audit = _audit(_rows(), start_day=date(2026, 8, 25), end_day=DELIVERY_DAY)
        statuses = dict(
            zip(
                audit.delivery_days["market_day"],
                audit.delivery_days["day_status"],
                strict=True,
            )
        )
        self.assertEqual(statuses["2026-08-25"], NO_PUBLICATION)
        self.assertEqual(statuses["2026-08-26"], PROVIDER_DECLARED_BEFORE_CUTOFF)
        self.assertNotIn(NO_PUBLICATION, ACCEPTABLE_FEATURE_DAY_STATUSES)

    def test_a_partial_day_is_incomplete_rather_than_a_shorter_day(self) -> None:
        audit = _audit(_rows(intervals=20))
        self.assertEqual(audit.delivery_days.at[0, "day_status"], INCOMPLETE_BEFORE_CUTOFF)
        self.assertEqual(audit.delivery_days.at[0, "expected_interval_count"], 24)

    def test_a_variable_with_no_rows_at_all_is_audited_and_reported(self) -> None:
        audit = _audit(_rows(), variables=["temperature_2m", "dswrf_surface"])
        statuses = dict(
            zip(audit.delivery_days["variable"], audit.delivery_days["day_status"], strict=True)
        )
        self.assertEqual(statuses["dswrf_surface"], NO_PUBLICATION)
        self.assertFalse(audit.summary["availability_accepted"])


class DecisionTimeSelectionTests(unittest.TestCase):
    """Later revisions are counted and excluded; the decision-time one is the latest in time."""

    def _with_revisions(self) -> pd.DataFrame:
        base = _rows()
        early = base.copy()
        early["source_revision"] = "1"
        late = base.copy()
        late["source_revision"] = "2"
        late["published_at_utc"] = pd.Timestamp("2026-08-25T06:00:00+00:00")
        late["value"] = late["value"] + 1.0
        late["raw_sha256"] = late["raw_sha256"].str.replace("^0", "1", regex=True)
        after = base.copy()
        after["source_revision"] = "3"
        after["published_at_utc"] = pd.Timestamp("2026-08-25T11:00:00+00:00")
        after["value"] = after["value"] + 2.0
        after["raw_sha256"] = after["raw_sha256"].str.replace("^0", "2", regex=True)
        return ensure_point_in_time(pd.concat([early, late, after], ignore_index=True))

    def test_the_latest_publication_before_the_cutoff_decides_the_interval(self) -> None:
        audit = _audit(self._with_revisions())
        selected = audit.observations.loc[
            (audit.observations["delivery_start_utc"] == "2026-08-25T22:00:00+00:00")
            & (audit.observations["effective_evidence_grade"] != "unavailable")
        ]
        self.assertEqual(sorted(selected["source_revision"].tolist()), ["1", "2"])
        self.assertEqual(
            audit.delivery_days.at[0, "day_status"], PROVIDER_DECLARED_BEFORE_CUTOFF
        )
        self.assertEqual(audit.delivery_days.at[0, "covered_interval_count"], 24)

    def test_a_publication_after_the_cutoff_is_counted_and_excluded(self) -> None:
        audit = _audit(self._with_revisions())
        # One revision per interval was published after the cutoff, so every interval has one.
        self.assertEqual(audit.delivery_days.at[0, "superseded_after_cutoff_count"], 24)
        self.assertEqual(
            audit.summary["per_variable"]["temperature_2m"][
                "days_with_publications_after_cutoff"
            ],
            1,
        )


class QuarantineTests(unittest.TestCase):
    def test_the_assumed_grade_is_not_admitted_by_default(self) -> None:
        audit = _audit(_rows(grade=ASSUMED))
        self.assertEqual(audit.delivery_days.at[0, "day_status"], GRADE_NOT_ADMITTED)
        self.assertFalse(audit.summary["availability_accepted"])
        self.assertFalse(audit.summary["is_exploratory"])

    def test_admitting_it_makes_the_run_exploratory_and_never_accepted(self) -> None:
        audit = _audit(
            _rows(grade=ASSUMED),
            admitted_grades=(*ADMISSIBLE_EVIDENCE_GRADES, ASSUMED),
        )
        self.assertEqual(audit.delivery_days.at[0, "day_status"], ASSUMED_GRADE_EXPLORATORY)
        self.assertNotIn(ASSUMED_GRADE_EXPLORATORY, ACCEPTABLE_FEATURE_DAY_STATUSES)
        self.assertTrue(audit.summary["is_exploratory"])
        self.assertFalse(audit.summary["availability_accepted"])
        self.assertIn(ASSUMED, audit.summary["evidence_grades_admitted"])

    def test_the_absence_of_evidence_cannot_be_admitted_as_evidence(self) -> None:
        with self.assertRaisesRegex(FeatureAvailabilityError, "absence of evidence"):
            _audit(_rows(), admitted_grades=(UNAVAILABLE,))


class DeclarationTests(unittest.TestCase):
    def test_the_decision_lead_has_no_default(self) -> None:
        with self.assertRaisesRegex(DecisionCutoffError, "no default"):
            _audit(_rows(), decision_lead_minutes=None)

    def test_a_cutoff_inside_a_daylight_saving_gap_is_refused(self) -> None:
        """Design section 11, case 9."""

        schedule = GateClosureSchedule(
            schedule_id="gap",
            regimes=(
                GateClosureRegime(
                    effective_from_delivery_day=date(2020, 1, 1),
                    closure_day_offset=-1,
                    closure_local_time=time(3, 30),
                    closure_timezone="Europe/Athens",
                    reference="Declared for tests.",
                ),
            ),
        )
        with self.assertRaisesRegex(DecisionCutoffError, "does not exist exactly once"):
            _audit(
                _rows(date(2026, 3, 30)),
                schedule=schedule,
                start_day=date(2026, 3, 30),
                end_day=date(2026, 3, 30),
            )

    def test_the_lead_changes_which_publications_are_in_time(self) -> None:
        """Design section 11, case 6, at both declared leads."""

        borderline = _rows(published="2026-08-25T08:45:00+00:00")
        self.assertEqual(
            _audit(borderline, decision_lead_minutes=0).delivery_days.at[0, "day_status"],
            PROVIDER_DECLARED_BEFORE_CUTOFF,
        )
        self.assertEqual(
            _audit(borderline, decision_lead_minutes=30).delivery_days.at[0, "day_status"],
            ALL_PUBLICATIONS_AFTER_CUTOFF,
        )

    def test_an_end_day_before_the_start_day_is_refused(self) -> None:
        with self.assertRaisesRegex(FeatureAvailabilityError, "must not precede"):
            _audit(_rows(), start_day=DELIVERY_DAY, end_day=date(2026, 8, 25))


class TransitionDayTests(unittest.TestCase):
    def test_the_expected_interval_count_follows_the_market_calendar(self) -> None:
        self.assertEqual(expected_feature_interval_count(date(2026, 3, 29), 60), 23)
        self.assertEqual(expected_feature_interval_count(date(2026, 10, 25), 60), 25)

    def test_a_resolution_that_does_not_tile_a_transition_day_is_refused(self) -> None:
        with self.assertRaisesRegex(FeatureAvailabilityError, "does not tile"):
            expected_feature_interval_count(date(2026, 3, 29), 1440)

    def test_a_twenty_five_hour_day_needs_twenty_five_covered_intervals(self) -> None:
        day = date(2026, 10, 25)
        audit = _audit(
            _rows(
                day,
                published="2026-10-23T04:00:00+00:00",
                retrieved="2026-10-26T12:00:00+00:00",
            ),
            start_day=day,
            end_day=day,
        )
        self.assertEqual(audit.delivery_days.at[0, "expected_interval_count"], 25)
        self.assertEqual(audit.delivery_days.at[0, "day_status"], PROVIDER_DECLARED_BEFORE_CUTOFF)


class SummaryTests(unittest.TestCase):
    def test_the_summary_states_what_it_does_not_establish(self) -> None:
        summary = _audit(_rows()).summary
        self.assertTrue(summary["establishes_only_availability"])
        self.assertFalse(summary["quarantine_lifted"])
        self.assertTrue(summary["does_not_establish"])
        self.assertIn("not a value acceptance", summary["result_label"])

    def test_the_summary_carries_the_declared_cutoff_and_lead(self) -> None:
        summary = _audit(_rows()).summary
        self.assertEqual(summary["decision_cutoff_schedule_id"], "test-cutoff")
        self.assertEqual(summary["decision_lead_minutes"], 30)
        self.assertEqual(
            summary["decision_cutoff_schedule"]["regimes"][0]["reference"],
            DECLARED_REGIME["reference"],
        )

    def test_row_order_does_not_change_the_verdicts(self) -> None:
        features = _rows()
        shuffled = features.iloc[::-1].reset_index(drop=True)
        pd.testing.assert_frame_equal(
            _audit(features).delivery_days, _audit(shuffled).delivery_days
        )


class CommandTests(unittest.TestCase):
    def _write_inputs(self, directory: Path, **overrides: Any) -> tuple[Path, Path]:
        features = directory / "features.csv"
        write_point_in_time_csv(_rows(**overrides), features)
        cutoff = directory / "cutoff.json"
        cutoff.write_text(
            json.dumps({"schedule_id": "operator-cutoff", "regimes": [DECLARED_REGIME]}),
            encoding="utf-8",
        )
        return features, cutoff

    def _run(self, directory: Path, features: Path, cutoff: Path, *extra: str) -> int:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            return main(
                [
                    "audit-feature-availability",
                    str(features),
                    "--decision-cutoff",
                    str(cutoff),
                    "--decision-lead-minutes",
                    "30",
                    "--variables",
                    "temperature_2m",
                    "--start-day",
                    DELIVERY_DAY.isoformat(),
                    "--end-day",
                    DELIVERY_DAY.isoformat(),
                    "--output",
                    str(directory / "delivery_days.csv"),
                    *extra,
                ]
            )

    def test_an_accepted_window_exits_zero_and_writes_three_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            features, cutoff = self._write_inputs(directory)
            code = self._run(directory, features, cutoff)
            summary = json.loads(
                (directory / "delivery_days.summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(code, 0)
            self.assertTrue((directory / "delivery_days.csv").exists())
            self.assertTrue((directory / "delivery_days.observations.csv").exists())
            self.assertTrue(summary["availability_accepted"])

    def test_a_finding_exits_two_with_the_evidence_still_written(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            features, cutoff = self._write_inputs(directory, late_interval=3)
            code = self._run(directory, features, cutoff)
            self.assertEqual(code, 2)
            self.assertTrue((directory / "delivery_days.csv").exists())

    def test_the_committed_example_cutoff_is_refused_by_the_command(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            features, _ = self._write_inputs(directory)
            example = (
                Path(__file__).resolve().parents[1] / "config" / "decision_cutoff.example.json"
            )
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = self._run(directory, features, example)
            self.assertEqual(code, 1)
            self.assertIn("example-not-a-declaration", stderr.getvalue())
            self.assertFalse((directory / "delivery_days.csv").exists())


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    unittest.main()
