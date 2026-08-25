from __future__ import annotations

import unittest
from datetime import date

import numpy as np
import pandas as pd

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

    def test_multiple_annual_sign_changes_are_disclosed(self) -> None:
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
            "not_evaluable_multiple_sign_changes",
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
