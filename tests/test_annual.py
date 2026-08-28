from __future__ import annotations

import unittest
from datetime import date

import numpy as np
import pandas as pd

from greek_bess.analysis import AnnualDecompositionError, decompose_annual_replay
from greek_bess.backtest import backtest_forecast_dispatch
from greek_bess.dispatch import BatteryDispatchConfig, optimize_perfect_foresight
from tests.test_forecast import repeating_prices


def battery(**overrides) -> BatteryDispatchConfig:
    values = {
        "charge_power_mw": 1.0,
        "discharge_power_mw": 1.0,
        "energy_capacity_mwh": 1.0,
        "soc_min_fraction": 0.0,
        "soc_max_fraction": 1.0,
        "initial_soc_fraction": 0.0,
        "terminal_soc_fraction": 0.0,
        "charge_efficiency": 1.0,
        "discharge_efficiency": 1.0,
    }
    values.update(overrides)
    return BatteryDispatchConfig(**values)


def year_boundary_prices() -> pd.DataFrame:
    """Three market days straddling a New Year: 30, 31 December and 1 January."""

    return repeating_prices(date(2025, 12, 30), date(2026, 1, 2))


class AnnualMarketClockTests(unittest.TestCase):
    def test_delivery_years_follow_the_market_clock_not_utc(self) -> None:
        prices = year_boundary_prices()
        result = decompose_annual_replay(prices)
        overview = result.annual_overview.set_index("delivery_year")

        self.assertEqual(overview.loc[2025, "interval_count"], 48)
        self.assertEqual(overview.loc[2026, "interval_count"], 24)
        self.assertEqual(overview.loc[2025, "market_day_count"], 2)
        self.assertEqual(overview.loc[2026, "market_day_count"], 1)

        utc_counts = prices["delivery_start_utc"].dt.year.value_counts().to_dict()
        self.assertEqual(utc_counts[2025], 49)
        self.assertEqual(utc_counts[2026], 23)

    def test_every_year_records_its_coverage_and_partial_status(self) -> None:
        result = decompose_annual_replay(year_boundary_prices())
        overview = result.annual_overview.set_index("delivery_year")

        self.assertTrue(bool(overview.loc[2025, "is_partial_year"]))
        self.assertTrue(bool(overview.loc[2026, "is_partial_year"]))
        self.assertEqual(overview.loc[2025, "calendar_day_count"], 365)
        self.assertAlmostEqual(
            float(overview.loc[2025, "market_day_coverage_fraction"]), 2 / 365
        )
        self.assertEqual(result.summary["partial_delivery_years"], [2025, 2026])
        self.assertEqual(result.summary["first_market_day"], "2025-12-30")
        self.assertEqual(result.summary["last_market_day"], "2026-01-01")

    def test_price_context_preserves_zero_and_negative_prices(self) -> None:
        prices = year_boundary_prices()
        market_day = prices["delivery_start_market"].dt.date
        prices.loc[market_day.eq(date(2026, 1, 1)), "price_eur_per_mwh"] = [
            -5.0,
            0.0,
        ] + [80.0] * 22

        overview = decompose_annual_replay(prices).annual_overview.set_index("delivery_year")
        self.assertEqual(overview.loc[2026, "negative_price_interval_count"], 1)
        self.assertEqual(overview.loc[2026, "zero_price_interval_count"], 1)
        self.assertEqual(overview.loc[2026, "missing_price_interval_count"], 0)
        self.assertAlmostEqual(float(overview.loc[2026, "minimum_price_eur_per_mwh"]), -5.0)
        self.assertAlmostEqual(
            float(overview.loc[2026, "mean_daily_price_range_eur_per_mwh"]), 85.0
        )

    def test_a_duplicated_accepted_history_is_rejected(self) -> None:
        prices = year_boundary_prices()
        duplicated = pd.concat([prices, prices.head(1)], ignore_index=True)

        with self.assertRaisesRegex(AnnualDecompositionError, "repeats 1 canonical"):
            decompose_annual_replay(duplicated)

        schedule = optimize_perfect_foresight(prices, battery()).schedule
        with self.assertRaisesRegex(AnnualDecompositionError, "double-count"):
            decompose_annual_replay(duplicated, perfect_foresight_schedule=schedule)

    def test_missing_prices_are_counted_and_never_filled(self) -> None:
        prices = year_boundary_prices()
        prices.loc[0, "price_eur_per_mwh"] = np.nan

        overview = decompose_annual_replay(prices).annual_overview.set_index("delivery_year")
        self.assertEqual(overview.loc[2025, "missing_price_interval_count"], 1)
        self.assertEqual(overview.loc[2025, "interval_count"], 48)


class AnnualPerfectForesightTests(unittest.TestCase):
    def test_annual_ceilings_sum_to_the_accepted_total(self) -> None:
        prices = year_boundary_prices()
        schedule = optimize_perfect_foresight(prices, battery()).schedule

        result = decompose_annual_replay(
            prices, perfect_foresight_schedule=schedule, energy_capacity_mwh=1.0
        )
        overview = result.annual_overview.set_index("delivery_year")

        self.assertAlmostEqual(
            result.summary["perfect_foresight_margin_reconciliation_residual_eur"], 0.0
        )
        self.assertEqual(result.summary["perfect_foresight_dispatch_interval_count"], 72)
        self.assertEqual(overview.loc[2025, "dispatch_market_day_count"], 2)
        self.assertGreater(overview.loc[2026, "perfect_foresight_net_market_margin_eur"], 0.0)
        self.assertAlmostEqual(
            float(overview.loc[2025, "perfect_foresight_net_market_margin_eur_per_market_day"]),
            float(overview.loc[2025, "perfect_foresight_net_market_margin_eur"]) / 2,
        )
        self.assertAlmostEqual(
            float(overview.loc[2026, "perfect_foresight_equivalent_full_cycles"]),
            float(overview.loc[2026, "perfect_foresight_grid_discharge_mwh"]),
        )

    def test_equivalent_full_cycles_are_omitted_without_a_capacity(self) -> None:
        prices = year_boundary_prices()
        schedule = optimize_perfect_foresight(prices, battery()).schedule
        result = decompose_annual_replay(prices, perfect_foresight_schedule=schedule)
        self.assertNotIn(
            "perfect_foresight_equivalent_full_cycles", result.annual_overview.columns
        )

    def test_schedule_settled_on_other_prices_is_rejected(self) -> None:
        prices = year_boundary_prices()
        schedule = optimize_perfect_foresight(prices, battery()).schedule
        schedule.loc[0, "price_eur_per_mwh"] = 999.0

        with self.assertRaisesRegex(AnnualDecompositionError, "does not publish"):
            decompose_annual_replay(prices, perfect_foresight_schedule=schedule)

    def test_schedule_covering_unknown_intervals_is_rejected(self) -> None:
        prices = year_boundary_prices()
        schedule = optimize_perfect_foresight(prices, battery()).schedule
        schedule.loc[0, "delivery_start_utc"] = schedule.loc[
            0, "delivery_start_utc"
        ] - pd.Timedelta(400, unit="D")

        with self.assertRaisesRegex(AnnualDecompositionError, "absent from the"):
            decompose_annual_replay(prices, perfect_foresight_schedule=schedule)

    def test_repeated_schedule_intervals_are_rejected(self) -> None:
        prices = year_boundary_prices()
        schedule = optimize_perfect_foresight(prices, battery()).schedule
        duplicated = pd.concat([schedule, schedule.head(1)], ignore_index=True)

        with self.assertRaisesRegex(AnnualDecompositionError, "repeats a canonical"):
            decompose_annual_replay(prices, perfect_foresight_schedule=duplicated)


class AnnualForecastCaptureTests(unittest.TestCase):
    def decomposition(self, methods: tuple[str, ...] = ("daily_persistence", "rolling_mean")):
        prices = repeating_prices(date(2025, 12, 25), date(2026, 1, 6))
        daily = {
            method: backtest_forecast_dispatch(
                prices, battery(), method=method, rolling_window_days=3
            ).daily_results
            for method in methods
        }
        return prices, daily, decompose_annual_replay(prices, daily_results_by_method=daily)

    def test_annual_capture_uses_each_method_own_backtested_days(self) -> None:
        _, daily, result = self.decomposition()
        forecast = result.annual_forecast.set_index(["delivery_year", "forecast_method"])

        for method, table in daily.items():
            for year in (2025, 2026):
                expected = table.loc[
                    table["market_day"].map(lambda day: day.year) == year
                ]
                row = forecast.loc[(year, method)]
                self.assertEqual(row["backtested_market_day_count"], len(expected))
                if len(expected):
                    self.assertAlmostEqual(
                        float(row["realized_margin_eur"]),
                        float(expected["realized_margin_eur"].sum()),
                    )
                    self.assertAlmostEqual(
                        float(row["perfect_foresight_margin_eur"]),
                        float(expected["perfect_foresight_margin_eur"].sum()),
                    )

    def test_annual_error_metrics_are_interval_weighted(self) -> None:
        _, daily, result = self.decomposition(("rolling_mean",))
        forecast = result.annual_forecast.set_index(["delivery_year", "forecast_method"])
        table = daily["rolling_mean"]
        subset = table.loc[table["market_day"].map(lambda day: day.year) == 2026]
        weights = subset["interval_count"].to_numpy(dtype=float)

        expected_mae = float(
            (subset["forecast_mae_eur_per_mwh"].to_numpy(dtype=float) * weights).sum()
            / weights.sum()
        )
        expected_rmse = float(
            np.sqrt(
                (subset["forecast_rmse_eur_per_mwh"].to_numpy(dtype=float) ** 2 * weights).sum()
                / weights.sum()
            )
        )
        row = forecast.loc[(2026, "rolling_mean")]
        self.assertAlmostEqual(float(row["forecast_mae_eur_per_mwh"]), expected_mae)
        self.assertAlmostEqual(float(row["forecast_rmse_eur_per_mwh"]), expected_rmse)

    def test_common_day_ceiling_is_identical_across_methods(self) -> None:
        _, _, result = self.decomposition()
        common = result.annual_common_day

        self.assertTrue((common["perfect_foresight_margin_spread_eur"].abs() < 1e-6).all())
        self.assertAlmostEqual(result.summary["maximum_common_day_ceiling_spread_eur"], 0.0)
        for year in (2025, 2026):
            year_rows = common.loc[common["delivery_year"] == year]
            self.assertEqual(year_rows["common_market_day_count"].nunique(), 1)

    def test_a_year_without_backtested_days_reports_no_margin(self) -> None:
        prices = repeating_prices(date(2025, 12, 25), date(2026, 1, 6))
        daily = backtest_forecast_dispatch(
            prices, battery(), method="daily_persistence"
        ).daily_results
        only_2026 = daily.loc[daily["market_day"].map(lambda day: day.year) == 2026]

        result = decompose_annual_replay(
            prices, daily_results_by_method={"daily_persistence": only_2026}
        )
        forecast = result.annual_forecast.set_index(["delivery_year", "forecast_method"])
        row = forecast.loc[(2025, "daily_persistence")]

        self.assertEqual(row["backtested_market_day_count"], 0)
        self.assertEqual(row["not_backtested_market_day_count"], 7)
        self.assertTrue(pd.isna(row["realized_margin_eur"]))
        self.assertTrue(pd.isna(row["perfect_foresight_capture_ratio"]))
        self.assertNotEqual(row["realized_margin_eur"], 0.0)

    def test_a_year_with_no_common_days_reports_no_ceiling_spread(self) -> None:
        prices = repeating_prices(date(2025, 12, 25), date(2026, 1, 6))
        daily = backtest_forecast_dispatch(
            prices, battery(), method="daily_persistence"
        ).daily_results
        only_2026 = daily.loc[daily["market_day"].map(lambda day: day.year) == 2026]

        result = decompose_annual_replay(
            prices, daily_results_by_method={"daily_persistence": only_2026}
        )
        common = result.annual_common_day.set_index("delivery_year")
        self.assertEqual(common.loc[2025, "common_market_day_count"], 0)
        self.assertTrue(pd.isna(common.loc[2025, "perfect_foresight_margin_spread_eur"]))
        self.assertIsNone(result.summary["common_day_ceiling_spread_by_year"]["2025"])
        self.assertAlmostEqual(result.summary["maximum_common_day_ceiling_spread_eur"], 0.0)

    def test_daily_results_describing_another_history_are_rejected(self) -> None:
        prices = repeating_prices(date(2025, 12, 25), date(2026, 1, 6))
        daily = backtest_forecast_dispatch(
            prices, battery(), method="daily_persistence"
        ).daily_results
        stray = daily.head(1).copy()
        stray["market_day"] = [date(2019, 5, 1)]
        mutated = pd.concat([daily, stray], ignore_index=True)

        with self.assertRaisesRegex(AnnualDecompositionError, "different history"):
            decompose_annual_replay(
                prices, daily_results_by_method={"daily_persistence": mutated}
            )

    def test_repeated_market_days_are_rejected(self) -> None:
        prices = repeating_prices(date(2025, 12, 25), date(2026, 1, 6))
        daily = backtest_forecast_dispatch(
            prices, battery(), method="daily_persistence"
        ).daily_results
        duplicated = pd.concat([daily, daily.head(1)], ignore_index=True)

        with self.assertRaisesRegex(AnnualDecompositionError, "repeat a market day"):
            decompose_annual_replay(
                prices, daily_results_by_method={"daily_persistence": duplicated}
            )

    def test_missing_daily_columns_are_rejected(self) -> None:
        prices = year_boundary_prices()
        with self.assertRaisesRegex(AnnualDecompositionError, "missing columns"):
            decompose_annual_replay(
                prices,
                daily_results_by_method={
                    "daily_persistence": pd.DataFrame({"market_day": [date(2025, 12, 30)]})
                },
            )


class AnnualLabellingTests(unittest.TestCase):
    def test_summary_carries_the_upper_bound_and_normalization_labels(self) -> None:
        result = decompose_annual_replay(year_boundary_prices())
        self.assertIn("upper bound", result.summary["result_label"])
        self.assertIn("CET/CEST market-day start", result.summary["delivery_year_policy"])
        self.assertIn("annualized", result.summary["normalization_policy"])
        for forbidden in ("percentile", "probability", "loss_probability"):
            self.assertNotIn(forbidden, json_keys(result.summary))

    def test_positive_energy_capacity_is_required_when_supplied(self) -> None:
        with self.assertRaisesRegex(AnnualDecompositionError, "must be positive"):
            decompose_annual_replay(year_boundary_prices(), energy_capacity_mwh=0.0)


def json_keys(payload: dict) -> str:
    return " ".join(payload)


if __name__ == "__main__":
    unittest.main()
