"""Synthetic-only tests for the v0.9.2 revision-aware as-of join."""

from __future__ import annotations

import unittest
from datetime import date

import pandas as pd

from greek_bess.data.decision_cutoff import GateClosureSchedule
from greek_bess.data.point_in_time import ASSUMED, PROVIDER_DECLARED, ensure_point_in_time
from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.forecast.point_in_time_join import (
    PointInTimeJoinError,
    join_point_in_time_features,
)

DAY = date(2026, 8, 26)


def _schedule() -> GateClosureSchedule:
    return GateClosureSchedule.from_dict(
        {
            "schedule_id": "synthetic-test-cutoff",
            "regimes": [
                {
                    "effective_from_delivery_day": "2020-11-01",
                    "closure_day_offset": -1,
                    "closure_local_time": "12:00:00",
                    "closure_timezone": "Europe/Athens",
                    "reference": "Synthetic test declaration only.",
                }
            ],
        }
    )


def _prices(resolution: int = 60) -> pd.DataFrame:
    return generate_synthetic_prices(DAY, date(2026, 8, 27), resolution_minutes=resolution)


def _features(
    *, missing: int | None = None, revisions: bool = False, grade: str = PROVIDER_DECLARED
) -> pd.DataFrame:
    starts = _prices()["delivery_start_utc"]
    rows = []
    for index, start in enumerate(starts):
        if index == missing:
            continue
        base = {
            "delivery_start_utc": start,
            "delivery_end_utc": start + pd.Timedelta(1, unit="h"),
            "market_day": DAY,
            "source": "synthetic",
            "dataset": "synthetic_forecast",
            "variable": "temperature_2m",
            "area": "GR",
            "unit": "K",
            "resolution_minutes": 60,
            "value": 280.0 + index,
            "published_at_utc": pd.Timestamp("2026-08-25T04:00:00Z"),
            "retrieved_at_utc": pd.Timestamp("2026-08-25T10:00:00Z"),
            "source_document_id": f"original-{index}",
            "source_revision": "1",
            "raw_sha256": f"{index + 1:064x}",
            "forecast_issue_time_utc": pd.Timestamp("2026-08-25T00:00:00Z"),
            "forecast_horizon_minutes": None,
            "availability_evidence_grade": grade,
            "availability_evidence_detail": "synthetic fixture",
        }
        rows.append(base)
        if revisions:
            before = dict(
                base,
                value=290.0 + index,
                published_at_utc=pd.Timestamp("2026-08-25T08:29:59Z"),
                source_document_id=f"revision-before-{index}",
                source_revision="2",
                raw_sha256=f"{index + 101:064x}",
            )
            after = dict(
                base,
                value=999.0,
                published_at_utc=pd.Timestamp("2026-08-25T08:30:00Z"),
                retrieved_at_utc=pd.Timestamp("2026-08-25T10:00:00Z"),
                source_document_id=f"revision-at-cutoff-{index}",
                source_revision="3",
                raw_sha256=f"{index + 201:064x}",
            )
            rows.extend((before, after))
    return ensure_point_in_time(pd.DataFrame(rows))


class PointInTimeJoinTests(unittest.TestCase):
    def test_latest_revision_strictly_before_cutoff_is_selected_and_later_counted(self) -> None:
        result = join_point_in_time_features(
            _prices(),
            _features(revisions=True),
            schedule=_schedule(),
            decision_lead_minutes=30,
            admitted_grades=(PROVIDER_DECLARED,),
        )
        self.assertEqual(result.summary["complete_day_count"], 1)
        self.assertEqual(
            result.feature_frame["temperature_2m"].tolist(), [290.0 + index for index in range(24)]
        )
        self.assertTrue((result.audit_table["source_revision"] == "2").all())
        self.assertTrue(
            (result.audit_table["published_at_utc"] < result.audit_table["cutoff_utc"]).all()
        )
        self.assertTrue((result.audit_table["superseded_after_cutoff"] == 1).all())
        self.assertEqual(result.summary["superseded_after_cutoff_count"], 24)

    def test_latest_revision_cannot_be_bypassed_by_admitting_an_older_grade(self) -> None:
        features = _features()
        later = features.iloc[[0]].copy()
        later["value"] = 999.0
        later["published_at_utc"] = pd.Timestamp("2026-08-25T08:00:00Z")
        later["source_document_id"] = "later-assumed-revision"
        later["source_revision"] = "2"
        later["raw_sha256"] = "f" * 64
        later["availability_evidence_grade"] = ASSUMED

        result = join_point_in_time_features(
            _prices(),
            ensure_point_in_time(pd.concat([features, later], ignore_index=True)),
            schedule=_schedule(),
            decision_lead_minutes=30,
            admitted_grades=(PROVIDER_DECLARED,),
        )

        self.assertEqual(result.summary["excluded_day_count"], 1)
        self.assertTrue(result.feature_frame["temperature_2m"].isna().all())
        self.assertEqual(
            result.summary["delivery_days"][0]["reasons"][0]["cause"],
            "grade_not_admitted",
        )

    def test_missing_interval_excludes_whole_day_without_partial_values(self) -> None:
        result = join_point_in_time_features(
            _prices(),
            _features(missing=5),
            schedule=_schedule(),
            decision_lead_minutes=30,
            admitted_grades=(PROVIDER_DECLARED,),
        )
        self.assertEqual(result.summary["excluded_day_count"], 1)
        self.assertTrue(result.feature_frame["temperature_2m"].isna().all())
        self.assertTrue(result.audit_table.empty)
        self.assertEqual(
            result.summary["delivery_days"][0]["reasons"][0]["cause"], "incomplete_day"
        )

    def test_hourly_feature_broadcast_to_quarter_hours_is_explicit(self) -> None:
        result = join_point_in_time_features(
            _prices(15),
            _features(),
            schedule=_schedule(),
            decision_lead_minutes=30,
            admitted_grades=(PROVIDER_DECLARED,),
        )
        self.assertEqual(len(result.feature_frame), 96)
        self.assertEqual(
            set(result.audit_table["resolution_relation"]), {"broadcast_coarser_feature"}
        )
        self.assertEqual(result.feature_frame["temperature_2m"].iloc[:4].tolist(), [280.0] * 4)

    def test_permuting_revisions_is_byte_deterministic(self) -> None:
        features = _features(revisions=True)
        prices = _prices()
        first = join_point_in_time_features(
            prices,
            features,
            schedule=_schedule(),
            decision_lead_minutes=30,
            admitted_grades=(PROVIDER_DECLARED,),
        )
        second = join_point_in_time_features(
            prices,
            features.sample(frac=1, random_state=7),
            schedule=_schedule(),
            decision_lead_minutes=30,
            admitted_grades=(PROVIDER_DECLARED,),
        )
        pd.testing.assert_frame_equal(first.feature_frame, second.feature_frame)
        pd.testing.assert_frame_equal(first.audit_table, second.audit_table)
        self.assertEqual(first.summary, second.summary)

    def test_assumed_grade_requires_explicit_exploratory_run(self) -> None:
        with self.assertRaisesRegex(PointInTimeJoinError, "exploratory=True"):
            join_point_in_time_features(
                _prices(),
                _features(grade=ASSUMED),
                schedule=_schedule(),
                decision_lead_minutes=30,
                admitted_grades=(ASSUMED,),
            )

    def test_finer_features_are_refused_without_aggregation_rule(self) -> None:
        features = _features()
        features["resolution_minutes"] = 15
        features["delivery_end_utc"] = features["delivery_start_utc"] + pd.Timedelta(15, unit="min")
        with self.assertRaisesRegex(PointInTimeJoinError, "finer feature"):
            join_point_in_time_features(
                _prices(),
                ensure_point_in_time(features),
                schedule=_schedule(),
                decision_lead_minutes=30,
                admitted_grades=(PROVIDER_DECLARED,),
            )


if __name__ == "__main__":
    unittest.main()
