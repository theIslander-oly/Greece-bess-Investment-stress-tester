from __future__ import annotations

import unittest
from datetime import date

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from greek_bess.finance import (
    FinanceConfig,
    FinanceInputError,
    evaluate_project_finance,
)


def _config(**overrides: object) -> FinanceConfig:
    values: dict[str, object] = {
        "project_start_day": date(2026, 1, 1),
        "project_end_day": date(2026, 12, 31),
        "operating_margin_case": "perfect_foresight_upper_bound",
        "discount_rate_fraction": 0.10,
        "battery_system_capex_eur": 1_000.0,
        "market_margin_realization_fraction": 0.8,
        "fixed_opex_eur_per_year": 365.0,
        "variable_opex_eur_per_mwh_discharged": 1.0,
        "decommissioning_cost_eur": 20.0,
        "residual_value_eur": 50.0,
    }
    values.update(overrides)
    return FinanceConfig(**values)


def _daily(
    start: str = "2026-01-01",
    end: str = "2026-12-31",
    *,
    margin: float = 10.0,
    discharge: float = 2.0,
) -> pd.DataFrame:
    days = pd.date_range(start, end, freq="D")
    return pd.DataFrame(
        {
            "market_day": days.date,
            "net_market_margin_eur": margin,
            "grid_discharge_mwh": discharge,
            "augmentation_cost_eur": 0.0,
        }
    )


class ProjectFinanceTests(unittest.TestCase):
    def test_exact_cash_flow_components_npv_and_break_even_outputs(self) -> None:
        operating = _daily()
        operating.loc[99, "augmentation_cost_eur"] = 100.0
        config = _config()

        result = evaluate_project_finance(operating, config)
        daily = result.daily_cash_flows
        summary = result.summary

        self.assertAlmostEqual(daily["realized_market_margin_eur"].sum(), 2_920.0)
        self.assertAlmostEqual(daily["fixed_opex_eur"].sum(), 365.0)
        self.assertAlmostEqual(daily["variable_opex_eur"].sum(), 730.0)
        self.assertAlmostEqual(daily["augmentation_cost_eur"].sum(), 100.0)
        self.assertAlmostEqual(daily["operating_net_cash_flow_eur"].sum(), 1_755.0)
        expected_npv = -1_000.0 + float(
            daily["operating_net_cash_flow_eur"].div(
                daily["discount_factor"]
            ).sum()
        )
        self.assertAlmostEqual(summary["npv_eur"], expected_npv)
        self.assertEqual(summary["irr_status"], "calculated")
        self.assertIsNotNone(summary["simple_payback_day"])
        self.assertIsNotNone(summary["discounted_payback_day"])
        self.assertGreater(
            summary["maximum_initial_capex_for_zero_npv_eur"], 1_000.0
        )
        self.assertTrue(summary["positive_npv_at_configured_discount_rate"])
        self.assertIn("upper bound", summary["operating_margin_interpretation"])
        self.assertEqual(len(result.annual_cash_flows), 2)
        self.assertEqual(result.annual_cash_flows.iloc[0]["project_year"], 0)

    def test_no_payback_or_irr_when_cash_flows_never_change_sign(self) -> None:
        result = evaluate_project_finance(
            _daily(margin=-1.0, discharge=0.0),
            _config(
                market_margin_realization_fraction=1.0,
                fixed_opex_eur_per_year=0.0,
                variable_opex_eur_per_mwh_discharged=0.0,
                decommissioning_cost_eur=0.0,
                residual_value_eur=0.0,
            ),
        )
        self.assertIsNone(result.summary["simple_payback_day"])
        self.assertIsNone(result.summary["discounted_payback_day"])
        self.assertIsNone(result.summary["irr_fraction"])
        self.assertEqual(
            result.summary["irr_status"], "not_evaluable_no_sign_change"
        )
        self.assertFalse(result.summary["positive_npv_at_configured_discount_rate"])

    def test_a_series_with_several_rates_is_disclosed_rather_than_quoted(self) -> None:
        operating = _daily("2026-01-01", "2027-12-31", margin=0.0, discharge=0.0)
        first_year = operating["market_day"] <= date(2026, 12, 31)
        operating.loc[first_year, "net_market_margin_eur"] = 3_000.0 / 365.0
        operating.loc[~first_year, "net_market_margin_eur"] = -2_500.0 / 365.0
        result = evaluate_project_finance(
            operating,
            _config(
                project_end_day=date(2027, 12, 31),
                market_margin_realization_fraction=1.0,
                fixed_opex_eur_per_year=0.0,
                variable_opex_eur_per_mwh_discharged=0.0,
                decommissioning_cost_eur=0.0,
                residual_value_eur=0.0,
            ),
        )
        self.assertIsNone(result.summary["irr_fraction"])
        self.assertEqual(
            result.summary["irr_status"],
            "not_evaluable_multiple_rates",
        )

    def test_missing_day_duplicate_and_unsorted_paths_are_rejected(self) -> None:
        config = _config()
        missing = _daily().drop(index=10).reset_index(drop=True)
        with self.assertRaisesRegex(FinanceInputError, "every calendar day"):
            evaluate_project_finance(missing, config)

        duplicate = pd.concat([_daily(), _daily().iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(FinanceInputError, "duplicate"):
            evaluate_project_finance(duplicate, config)

        unsorted = _daily().iloc[::-1].reset_index(drop=True)
        with self.assertRaisesRegex(FinanceInputError, "sorted"):
            evaluate_project_finance(unsorted, config)

    def test_optional_augmentation_column_defaults_to_zero(self) -> None:
        operating = _daily().drop(columns=["augmentation_cost_eur"])
        result = evaluate_project_finance(operating, _config())
        self.assertTrue(
            np.allclose(result.daily_cash_flows["augmentation_cost_eur"], 0.0)
        )

    def test_invalid_finance_assumptions_are_rejected(self) -> None:
        with self.assertRaisesRegex(FinanceInputError, "cannot precede"):
            _config(project_end_day=date(2025, 12, 31))
        with self.assertRaisesRegex(FinanceInputError, "operating_margin_case"):
            _config(operating_margin_case="expected_revenue")
        with self.assertRaisesRegex(FinanceInputError, "between 0 and 1"):
            _config(market_margin_realization_fraction=1.1)
        with self.assertRaisesRegex(FinanceInputError, "greater than zero"):
            _config(battery_system_capex_eur=0.0)
        with self.assertRaisesRegex(FinanceInputError, "nonnegative"):
            _config(fixed_opex_eur_per_year=-1.0)


if __name__ == "__main__":
    unittest.main()


class DatedCashFlowMetricTests(unittest.TestCase):
    """NPV and IRR read one dated series, so they cannot describe different timings."""

    def _evenly_paid_year(self) -> tuple[pd.DataFrame, FinanceConfig]:
        """EUR 1,000 paid initially, EUR 1,200 received evenly across 365 daily periods."""

        operating = _daily(margin=1_200.0 / 365.0, discharge=0.0)
        config = _config(
            battery_system_capex_eur=1_000.0,
            market_margin_realization_fraction=1.0,
            fixed_opex_eur_per_year=0.0,
            variable_opex_eur_per_mwh_discharged=0.0,
            decommissioning_cost_eur=0.0,
            residual_value_eur=0.0,
        )
        return operating, config

    def test_the_irr_agrees_with_an_independent_root_on_the_same_dates(self) -> None:
        operating, config = self._evenly_paid_year()
        result = evaluate_project_finance(operating, config)
        irr = result.summary["irr_fraction"]
        self.assertEqual(result.summary["irr_status"], "calculated")

        # Solved here from the dates the daily table itself carries, with no reference to the
        # model's own solver. Relocating the year's receipts to its final day, which is what the
        # annual table does, answers about 20% instead.
        times = result.daily_cash_flows["years_from_project_start"].to_numpy(dtype=float)
        amounts = result.daily_cash_flows["operating_net_cash_flow_eur"].to_numpy(dtype=float)

        def objective(rate: float) -> float:
            return -1_000.0 + float(np.sum(amounts / (1.0 + rate) ** times))

        independent = brentq(objective, -0.9999, 1_000.0, xtol=1e-14)
        self.assertAlmostEqual(irr, independent, places=9)
        # The figure the execution plan names for this fixture under the 365.25-day convention.
        self.assertAlmostEqual(irr, 0.4559, places=4)

    def test_the_dated_npv_at_the_reported_irr_is_zero_within_tolerance(self) -> None:
        operating, config = self._evenly_paid_year()
        result = evaluate_project_finance(operating, config)
        irr = result.summary["irr_fraction"]
        assert irr is not None

        times = result.daily_cash_flows["years_from_project_start"].to_numpy(dtype=float)
        amounts = result.daily_cash_flows["operating_net_cash_flow_eur"].to_numpy(dtype=float)
        residual = -config.total_initial_capex_eur + float(
            np.sum(amounts / (1.0 + irr) ** times)
        )
        self.assertLessEqual(
            abs(residual), 1e-7 * max(1.0, config.total_initial_capex_eur)
        )

    def test_a_partial_year_is_dated_by_its_own_days(self) -> None:
        operating = _daily("2026-01-01", "2026-06-30", margin=1_200.0 / 365.0, discharge=0.0)
        config = _config(
            project_end_day=date(2026, 6, 30),
            battery_system_capex_eur=500.0,
            market_margin_realization_fraction=1.0,
            fixed_opex_eur_per_year=0.0,
            variable_opex_eur_per_mwh_discharged=0.0,
            decommissioning_cost_eur=0.0,
            residual_value_eur=0.0,
        )
        result = evaluate_project_finance(operating, config)
        irr = result.summary["irr_fraction"]
        assert irr is not None
        self.assertEqual(result.summary["irr_status"], "calculated")

        times = result.daily_cash_flows["years_from_project_start"].to_numpy(dtype=float)
        amounts = result.daily_cash_flows["operating_net_cash_flow_eur"].to_numpy(dtype=float)
        residual = -config.total_initial_capex_eur + float(
            np.sum(amounts / (1.0 + irr) ** times)
        )
        self.assertLessEqual(abs(residual), 1e-7 * max(1.0, config.total_initial_capex_eur))
        # The horizon is half a year, so the last flow is dated near 0.5, not at 1.0.
        self.assertAlmostEqual(float(times[-1]), 181 / 365.25, places=12)

    def test_leap_year_dates_are_dated_by_their_own_days(self) -> None:
        # 2028 is a leap year: 366 daily periods, and the 29 February flow is one of them.
        operating = _daily("2028-01-01", "2028-12-31", margin=1_200.0 / 366.0, discharge=0.0)
        config = _config(
            project_start_day=date(2028, 1, 1),
            project_end_day=date(2028, 12, 31),
            battery_system_capex_eur=1_000.0,
            market_margin_realization_fraction=1.0,
            fixed_opex_eur_per_year=0.0,
            variable_opex_eur_per_mwh_discharged=0.0,
            decommissioning_cost_eur=0.0,
            residual_value_eur=0.0,
        )
        result = evaluate_project_finance(operating, config)
        daily = result.daily_cash_flows
        self.assertEqual(len(daily), 366)
        self.assertIn(date(2028, 2, 29), set(daily["market_day"]))

        irr = result.summary["irr_fraction"]
        assert irr is not None
        times = daily["years_from_project_start"].to_numpy(dtype=float)
        amounts = daily["operating_net_cash_flow_eur"].to_numpy(dtype=float)
        residual = -config.total_initial_capex_eur + float(
            np.sum(amounts / (1.0 + irr) ** times)
        )
        self.assertLessEqual(abs(residual), 1e-7 * max(1.0, config.total_initial_capex_eur))
        self.assertAlmostEqual(float(times[-1]), 366 / 365.25, places=12)

    def test_a_series_that_never_recovers_still_reports_its_single_rate(self) -> None:
        # This series fails the cumulative-balance criterion — it never repays its outlay — and
        # still has exactly one rate. Refusing it would withhold a real figure, so the scan
        # settles it from the root structure actually present.
        operating = _daily(margin=1.0, discharge=0.0)
        operating.loc[::7, "net_market_margin_eur"] = -1.0
        config = _config(
            battery_system_capex_eur=1_000.0,
            market_margin_realization_fraction=1.0,
            fixed_opex_eur_per_year=0.0,
            variable_opex_eur_per_mwh_discharged=0.0,
            decommissioning_cost_eur=0.0,
            residual_value_eur=0.0,
        )
        result = evaluate_project_finance(operating, config)
        self.assertEqual(result.summary["irr_status"], "calculated")
        irr = result.summary["irr_fraction"]
        assert irr is not None
        self.assertLess(irr, 0.0)

    def test_totals_fees_and_augmentation_are_unchanged_by_the_metric_change(self) -> None:
        # The timing correction must not move, drop or double-count any euro.
        operating = _daily()
        operating.loc[99, "augmentation_cost_eur"] = 100.0
        result = evaluate_project_finance(operating, _config())
        daily = result.daily_cash_flows
        summary = result.summary

        self.assertAlmostEqual(float(daily["augmentation_cost_eur"].sum()), 100.0, places=9)
        self.assertAlmostEqual(summary["augmentation_cost_eur"], 100.0, places=9)
        # Realized margin is the supplied margin times the declared realization fraction, once.
        self.assertAlmostEqual(
            summary["realized_market_margin_eur"],
            summary["market_margin_input_eur"] * 0.8,
            places=9,
        )
        # The undiscounted project cash flow reconciles from its own components.
        expected = (
            summary["realized_market_margin_eur"]
            - summary["fixed_opex_eur"]
            - summary["variable_opex_eur"]
            - summary["augmentation_cost_eur"]
            - summary["decommissioning_cost_eur"]
            + summary["residual_value_eur"]
            - summary["initial_capex_eur"]
        )
        self.assertAlmostEqual(
            summary["undiscounted_project_cash_flow_eur"], expected, places=6
        )

    def test_the_annual_table_remains_a_summary_and_does_not_drive_the_irr(self) -> None:
        # The annual table still reports a year's total at that year's end. That is a legitimate
        # summary; what changed is that no monetary metric is derived from it.
        operating = _daily()
        result = evaluate_project_finance(operating, _config())
        annual = result.annual_cash_flows
        daily = result.daily_cash_flows

        self.assertAlmostEqual(
            float(annual["net_cash_flow_eur"].iloc[1:].sum()),
            float(daily["operating_net_cash_flow_eur"].sum()),
            places=6,
        )
        # Solving on the annual table gives a different answer, which is the defect this
        # milestone removes; the reported IRR must not be that one.
        annual_times = annual["years_from_project_start"].to_numpy(dtype=float)
        annual_amounts = annual["net_cash_flow_eur"].to_numpy(dtype=float)

        def annual_objective(rate: float) -> float:
            return float(np.sum(annual_amounts / (1.0 + rate) ** annual_times))

        annual_irr = brentq(annual_objective, -0.9999, 1_000.0, xtol=1e-14)
        self.assertNotAlmostEqual(result.summary["irr_fraction"], annual_irr, places=3)
