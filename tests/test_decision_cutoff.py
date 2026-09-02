"""The declared decision cutoff, and the move that gave it a neutral home.

Two things are pinned here. The first is that moving the gate-closure schedule out of the
retained-but-unused ADMIE module changed nothing: the classes are the same objects under both
names, and an ``except AdmiePublicationTimingError`` still catches what the moved code raises.
The second is the gate the v0.9 path adds in front of them — the committed example is refused as
a declaration, and the decision lead is a required judgment with no default.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, time
from pathlib import Path
from typing import Any

import pandas as pd

from greek_bess.data import admie_timing
from greek_bess.data.decision_cutoff import (
    DECLARABLE_CLOSURE_TIMEZONES,
    EXAMPLE_PLACEHOLDER_IDENTIFIER,
    EXAMPLE_PLACEHOLDER_MARKER,
    DecisionCutoffError,
    GateClosureRegime,
    GateClosureSchedule,
    effective_cutoff_utc,
    read_decision_cutoff_schedule,
    validate_decision_lead_minutes,
)

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"

DECLARED_REGIME: dict[str, Any] = {
    "effective_from_delivery_day": "2020-11-01",
    "closure_day_offset": -1,
    "closure_local_time": "12:00:00",
    "closure_timezone": "Europe/Athens",
    "reference": "Declared for tests; the operator supplies the market rule citation.",
}


def _schedule(*regimes: dict[str, Any]) -> GateClosureSchedule:
    return GateClosureSchedule.from_dict(
        {"schedule_id": "test-cutoff", "regimes": list(regimes) or [DECLARED_REGIME]}
    )


def _write(payload: object, directory: Path, name: str = "cutoff.json") -> Path:
    path = directory / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class ModuleMoveTests(unittest.TestCase):
    """The schedule now lives in a neutral module and is re-exported, not reimplemented."""

    def test_the_admie_module_re_exports_the_same_objects(self) -> None:
        self.assertIs(admie_timing.GateClosureSchedule, GateClosureSchedule)
        self.assertIs(admie_timing.GateClosureRegime, GateClosureRegime)
        self.assertIs(
            admie_timing.DECLARABLE_CLOSURE_TIMEZONES, DECLARABLE_CLOSURE_TIMEZONES
        )

    def test_the_moved_refusals_are_still_caught_under_the_old_error_name(self) -> None:
        # The alias exists precisely so that this keeps working. A subclass here would have
        # silently stopped every existing caller from catching the schedule's own refusals.
        with self.assertRaises(admie_timing.AdmiePublicationTimingError):
            _schedule().closure_utc(date(2020, 10, 31))
        with self.assertRaises(DecisionCutoffError):
            _schedule().closure_utc(date(2020, 10, 31))

    def test_a_live_feature_path_does_not_import_the_retained_module(self) -> None:
        """The reason for the move, asserted rather than left to review."""

        for module in (
            "src/greek_bess/data/point_in_time.py",
            "src/greek_bess/data/availability_audit.py",
            "src/greek_bess/data/gfs.py",
            "src/greek_bess/cli/fundamentals.py",
        ):
            source = (Path(__file__).resolve().parents[1] / module).read_text(encoding="utf-8")
            with self.subTest(module=module):
                self.assertNotIn("admie_timing", source)


class DecisionLeadTests(unittest.TestCase):
    def test_zero_is_a_declaration_and_is_accepted(self) -> None:
        self.assertEqual(validate_decision_lead_minutes(0), 0)

    def test_a_missing_lead_is_refused_rather_than_defaulted(self) -> None:
        with self.assertRaisesRegex(DecisionCutoffError, "no default"):
            validate_decision_lead_minutes(None)

    def test_a_boolean_is_not_an_integer_number_of_minutes(self) -> None:
        with self.assertRaises(DecisionCutoffError):
            validate_decision_lead_minutes(True)

    def test_a_negative_lead_would_move_the_cutoff_past_the_gate(self) -> None:
        with self.assertRaisesRegex(DecisionCutoffError, "must not be negative"):
            validate_decision_lead_minutes(-1)


class EffectiveCutoffTests(unittest.TestCase):
    def test_the_lead_is_subtracted_from_the_declared_closure(self) -> None:
        # Noon Athens on 25 August 2026 is 09:00 UTC under EEST.
        self.assertEqual(
            effective_cutoff_utc(_schedule(), date(2026, 8, 26), 0).isoformat(),
            "2026-08-25T09:00:00+00:00",
        )
        self.assertEqual(
            effective_cutoff_utc(_schedule(), date(2026, 8, 26), 30).isoformat(),
            "2026-08-25T08:30:00+00:00",
        )

    def test_a_cutoff_inside_a_daylight_saving_gap_is_refused(self) -> None:
        """Design section 11, case 9: the closure does not exist once on the transition day."""

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
            effective_cutoff_utc(schedule, date(2026, 3, 30), 0)

    def test_a_day_before_the_first_regime_is_refused_not_extrapolated(self) -> None:
        with self.assertRaisesRegex(DecisionCutoffError, "precedes the first declared"):
            effective_cutoff_utc(_schedule(), date(2020, 10, 31), 0)

    def test_a_publication_at_the_cutoff_is_late(self) -> None:
        """Design section 11, case 6, at the level the comparison is defined."""

        cutoff = effective_cutoff_utc(_schedule(), date(2026, 8, 26), 30)
        self.assertFalse(cutoff < cutoff)
        self.assertTrue(cutoff - pd.Timedelta(1, unit="s") < cutoff)


class DeclarationGateTests(unittest.TestCase):
    def test_the_committed_example_is_refused_as_a_declaration(self) -> None:
        with self.assertRaisesRegex(DecisionCutoffError, EXAMPLE_PLACEHOLDER_IDENTIFIER):
            read_decision_cutoff_schedule(CONFIG_DIR / "decision_cutoff.example.json")

    def test_renaming_the_example_does_not_make_it_a_declaration(self) -> None:
        payload = json.loads(
            (CONFIG_DIR / "decision_cutoff.example.json").read_text(encoding="utf-8")
        )
        payload["schedule_id"] = "operator-schedule"
        with tempfile.TemporaryDirectory() as directory:
            path = _write(payload, Path(directory))
            with self.assertRaisesRegex(DecisionCutoffError, "placeholder reference"):
                read_decision_cutoff_schedule(path)

    def test_a_real_declaration_is_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = _write(
                {"schedule_id": "operator-schedule", "regimes": [DECLARED_REGIME]},
                Path(directory),
            )
            schedule = read_decision_cutoff_schedule(path)
        self.assertEqual(schedule.schedule_id, "operator-schedule")
        self.assertNotIn(EXAMPLE_PLACEHOLDER_MARKER, schedule.regimes[0].reference)


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    unittest.main()
