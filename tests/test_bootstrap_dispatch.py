from __future__ import annotations

import unittest
from datetime import date

import pandas as pd

from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.dispatch import BatteryDispatchConfig
from greek_bess.stress import (
    BootstrapConfig,
    BootstrapDispatchInputError,
    dispatch_bootstrap_paths,
    generate_seasonal_bootstrap_paths,
)


def battery() -> BatteryDispatchConfig:
    return BatteryDispatchConfig(
        charge_power_mw=1,
        discharge_power_mw=1,
        energy_capacity_mwh=1,
        soc_min_fraction=0,
        soc_max_fraction=1,
        initial_soc_fraction=0,
        terminal_soc_fraction=0,
        charge_efficiency=1,
        discharge_efficiency=1,
    )


def paths() -> pd.DataFrame:
    history = generate_synthetic_prices(
        date(2025, 1, 1), date(2025, 1, 5), seed=4, negative_price_share=0
    )
    return generate_seasonal_bootstrap_paths(
        history,
        BootstrapConfig(date(2026, 1, 1), date(2026, 1, 3), path_count=2, random_seed=8),
    ).paths


class BootstrapDispatchTests(unittest.TestCase):
    def test_paths_are_solved_independently_with_common_constraints(self) -> None:
        result = dispatch_bootstrap_paths(paths(), battery(), availability=0.75)

        self.assertEqual(result.summary["path_count"], 2)
        self.assertEqual(result.interval_results.groupby("path_id").size().tolist(), [48, 48])
        self.assertEqual(len(result.path_summaries), 2)
        self.assertTrue((result.interval_results["availability_fraction"] == 0.75).all())
        self.assertTrue(
            (result.path_summaries["initial_energy_mwh"] == 0).all()
            and (result.path_summaries["terminal_energy_mwh"] == 0).all()
        )
        self.assertTrue(
            (result.interval_results["source"] == "synthetic").all()
            and result.interval_results["quality_flags"]
            .map(lambda flags: "synthetic_not_forecast" in flags)
            .all()
        )
        self.assertIn("not forecasts", result.summary["result_label"])

    def test_duplicate_incomplete_and_inconsistent_paths_fail(self) -> None:
        frame = paths()
        duplicate = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
        incomplete = frame.drop(frame.index[frame["path_id"] == 1][0]).reset_index(drop=True)
        inconsistent = frame.copy()
        index = inconsistent.index[inconsistent["path_id"] == 1][0]
        inconsistent.loc[index, "delivery_start_utc"] += pd.Timedelta(hours=1)

        with self.assertRaisesRegex(BootstrapDispatchInputError, "Duplicate"):
            dispatch_bootstrap_paths(duplicate, battery())
        with self.assertRaisesRegex(BootstrapDispatchInputError, "quality validation"):
            dispatch_bootstrap_paths(incomplete, battery())
        with self.assertRaisesRegex(
            BootstrapDispatchInputError, "Duplicate|quality validation|inconsistent canonical"
        ):
            dispatch_bootstrap_paths(inconsistent, battery())

    def test_non_synthetic_provenance_and_per_path_availability_fail(self) -> None:
        frame = paths()
        frame.loc[0, "source"] = "entsoe"
        with self.assertRaisesRegex(BootstrapDispatchInputError, "provenance"):
            dispatch_bootstrap_paths(frame, battery())
        with self.assertRaisesRegex(BootstrapDispatchInputError, "one common profile"):
            dispatch_bootstrap_paths(paths(), battery(), availability=[1.0] * 96)


if __name__ == "__main__":
    unittest.main()
