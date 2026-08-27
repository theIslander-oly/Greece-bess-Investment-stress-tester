from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

import pandas as pd

from greek_bess.cli import main
from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.stress import (
    BootstrapConfig,
    NegativePriceEventConfig,
    NegativePriceEventInputError,
    apply_negative_price_events,
    generate_seasonal_bootstrap_paths,
)


def _paths() -> pd.DataFrame:
    history = generate_synthetic_prices(
        date(2025, 1, 1), date(2025, 1, 4), seed=8, negative_price_share=0
    )
    return generate_seasonal_bootstrap_paths(
        history,
        BootstrapConfig(
            date(2026, 1, 1),
            date(2026, 1, 2),
            path_count=2,
            random_seed=3,
        ),
    ).paths


def _config(shift: float = -200.0) -> NegativePriceEventConfig:
    return NegativePriceEventConfig.from_dict(
        {
            "transformation_id": "morning_negative_event",
            "shift_eur_per_mwh": shift,
            "events": [
                {
                    "event_id": "event_1",
                    "start_utc": "2025-12-31T23:00:00+00:00",
                    "end_utc": "2026-01-01T02:00:00+00:00",
                }
            ],
        }
    )


class NegativePriceEventTests(unittest.TestCase):
    def test_event_is_deterministic_negative_and_fully_auditable(self) -> None:
        paths = _paths()
        first = apply_negative_price_events(paths, _config())
        second = apply_negative_price_events(paths, _config())

        pd.testing.assert_frame_equal(first.paths, second.paths)
        pd.testing.assert_frame_equal(first.provenance, second.provenance)
        applied = first.provenance["event_applied"]
        self.assertEqual(int(applied.sum()), 6)
        self.assertTrue((first.paths.loc[applied, "price_eur_per_mwh"] < 0).all())
        self.assertTrue(
            first.paths.loc[~applied, "price_eur_per_mwh"].equals(
                paths.loc[~applied, "price_eur_per_mwh"]
            )
        )
        self.assertEqual(first.paths["path_id"].tolist(), paths["path_id"].tolist())
        self.assertTrue(first.paths["delivery_start_utc"].equals(paths["delivery_start_utc"]))
        self.assertEqual(
            first.provenance["original_price_eur_per_mwh"].tolist(),
            paths["price_eur_per_mwh"].tolist(),
        )
        self.assertIn("not forecasts", first.summary["result_label"])

    def test_rejects_misalignment_overlap_and_nonnegative_results(self) -> None:
        paths = _paths()
        misaligned = {
            "transformation_id": "bad_boundary",
            "shift_eur_per_mwh": -200,
            "events": [
                {
                    "event_id": "bad",
                    "start_utc": "2025-12-31T23:30:00+00:00",
                    "end_utc": "2026-01-01T02:00:00+00:00",
                }
            ],
        }
        overlap = {
            "transformation_id": "overlap",
            "shift_eur_per_mwh": -200,
            "events": [
                {
                    "event_id": "one",
                    "start_utc": "2025-12-31T23:00:00+00:00",
                    "end_utc": "2026-01-01T02:00:00+00:00",
                },
                {
                    "event_id": "two",
                    "start_utc": "2026-01-01T01:00:00+00:00",
                    "end_utc": "2026-01-01T03:00:00+00:00",
                },
            ],
        }

        with self.assertRaisesRegex(NegativePriceEventInputError, "boundaries"):
            apply_negative_price_events(paths, NegativePriceEventConfig.from_dict(misaligned))
        with self.assertRaisesRegex(NegativePriceEventInputError, "overlap"):
            NegativePriceEventConfig.from_dict(overlap)
        with self.assertRaisesRegex(NegativePriceEventInputError, "every selected"):
            apply_negative_price_events(paths, _config(-0.01))

    def test_config_rejects_unknown_fields_non_utc_and_nonnegative_shift(self) -> None:
        payload = {
            "transformation_id": "bad",
            "shift_eur_per_mwh": 1,
            "events": [
                {
                    "event_id": "event",
                    "start_utc": "2026-01-01T00:00:00+02:00",
                    "end_utc": "2026-01-01T01:00:00+02:00",
                }
            ],
        }
        with self.assertRaisesRegex(NegativePriceEventInputError, "expressed in UTC"):
            NegativePriceEventConfig.from_dict(payload)
        payload["events"][0]["start_utc"] = "2026-01-01T00:00:00+00:00"
        payload["events"][0]["end_utc"] = "2026-01-01T01:00:00+00:00"
        with self.assertRaisesRegex(NegativePriceEventInputError, "negative number"):
            NegativePriceEventConfig.from_dict(payload)
        payload["extra"] = True
        with self.assertRaisesRegex(NegativePriceEventInputError, "unknown"):
            NegativePriceEventConfig.from_dict(payload)
        payload.pop("extra")
        payload["transformation_id"] = 4
        with self.assertRaisesRegex(NegativePriceEventInputError, "non-empty string"):
            NegativePriceEventConfig.from_dict(payload)

    def test_cli_writes_paths_interval_provenance_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths_csv = root / "paths.csv"
            output = root / "events.csv"
            config_path = root / "events.json"
            paths = _paths().loc[lambda frame: frame["path_id"] == 0].copy()
            paths["quality_flags"] = paths["quality_flags"].map(json.dumps)
            paths.to_csv(paths_csv, index=False)
            config_path.write_text(json.dumps(_config().to_dict()), encoding="utf-8")

            with redirect_stdout(io.StringIO()):
                exit_code = main(
                    [
                        "apply-negative-price-events",
                        str(paths_csv),
                        "--config",
                        str(config_path),
                        "--output",
                        str(output),
                    ]
                )

            provenance = pd.read_csv(root / "events.provenance.csv")
            summary = json.loads((root / "events.summary.json").read_text())
            self.assertEqual(exit_code, 0)
            self.assertEqual(len(pd.read_csv(output)), 24)
            self.assertEqual(len(provenance), 24)
            self.assertEqual(int(provenance["event_applied"].sum()), 3)
            self.assertEqual(summary["event_count"], 1)


if __name__ == "__main__":
    unittest.main()
