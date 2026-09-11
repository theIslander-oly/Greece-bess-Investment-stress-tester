"""Small independent counterexamples for cash and stored-energy accounting."""

from dataclasses import replace
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from greek_bess.backtest import backtest_forecast_dispatch, simulate_degradation_dispatch
from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.degradation import AugmentationEvent, DegradationConfig, DegradationInputError
from greek_bess.dispatch import BatteryDispatchConfig, optimize_daily_perfect_foresight
from greek_bess.finance import FinanceConfig, FinanceInputError, evaluate_project_finance
from greek_bess.finance.model import _project_irr
from greek_bess.study import (
    IntegratedStudyConfig,
    StrategySpec,
    assemble_integrated_study,
    run_integrated_study,
)


def finance_case(start="2025-01-01", end="2026-06-30", **changes):
    config = dict(
        project_start_day=date.fromisoformat(start),
        project_end_day=date.fromisoformat(end),
        operating_margin_case="user_supplied_scenario",
        discount_rate_fraction=0.0,
        battery_system_capex_eur=365.0,
    )
    config.update(changes)
    daily = pd.DataFrame({
        "market_day": pd.date_range(start, end).date,
        "net_market_margin_eur": 0.0,
        "grid_discharge_mwh": 0.0,
    })
    return daily, FinanceConfig(**config)


def test_two_irr_roots_are_not_misreported_as_no_root():
    daily, config = finance_case(end="2026-12-31", battery_system_capex_eur=100.0)
    daily.loc[364, "net_market_margin_eur"] = 200.0
    daily.loc[729, "net_market_margin_eur"] = -50.0
    result = evaluate_project_finance(daily, config)
    for rate in [(1 + sign / np.sqrt(2)) ** (365.25 / 365) - 1 for sign in (-1, 1)]:
        residual = -100 + 200 / (1 + rate) ** (365 / 365.25)
        residual -= 50 / (1 + rate) ** (730 / 365.25)
        assert abs(residual) < 1e-10
    assert result.summary["irr_fraction"] is None
    assert result.summary["irr_status"] == "not_evaluable_multiple_rates"


def test_close_roots_never_become_a_false_unique_rate():
    # Three polynomial roots, two closer than the old scan spacing.
    discount_roots = np.array([1 / 1.1, 1 / 1.100001, 1 / 1.5])
    amounts = np.polynomial.polynomial.polyfromroots(discount_roots)
    rate, status = _project_irr(np.arange(4, dtype=float), amounts)
    assert rate is None
    assert status in {"not_evaluable_multiple_rates", "not_evaluable_uniqueness_not_established"}


def test_tangent_root_is_not_declared_absent():
    rate, status = _project_irr(np.array([0., 1., 2.]), np.array([-100., 200., -100.]))
    assert status != "not_evaluable_no_root_in_search_range"
    assert rate is None or abs(rate) < 1e-10


@pytest.mark.parametrize("end", ["2025-01-01", "2025-12-31", "2026-06-30", "2028-02-29"])
@pytest.mark.parametrize("discount", [0.0, 0.08])
def test_annual_break_even_margin_zeros_the_same_daily_npv(end, discount):
    daily, config = finance_case(end=end, discount_rate_fraction=discount)
    result = evaluate_project_finance(daily, config)
    annual_margin = result.summary["break_even_average_annual_market_margin_eur"]
    times = np.arange(1, len(daily) + 1) / 365.25
    expected = 365.0 / np.sum((1 + discount) ** (-times) / 365.25)
    assert annual_margin == pytest.approx(expected)
    daily["net_market_margin_eur"] = annual_margin / 365.25
    assert evaluate_project_finance(daily, config).summary["npv_eur"] == pytest.approx(0, abs=1e-8)


def test_margin_haircut_does_not_shrink_losses_and_break_even_reconciles():
    daily, config = finance_case(end="2025-01-02", battery_system_capex_eur=30,
                                 market_margin_realization_fraction=0.65)
    daily["net_market_margin_eur"] = [200., -100.]
    result = evaluate_project_finance(daily, config)
    assert result.daily_cash_flows["realized_market_margin_eur"].tolist() == [130., -100.]
    assert result.summary["npv_eur"] == pytest.approx(0)
    assert result.summary["break_even_market_margin_realization_fraction"] == pytest.approx(.65)


def test_wear_penalty_is_not_cash_and_commissioning_is_paid_once():
    daily, config = finance_case(end="2025-01-01", battery_system_capex_eur=100)
    daily["net_market_margin_eur"] = 80.
    daily["monetary_degradation_adder_eur"] = 20.
    daily["market_cash_margin_eur"] = 100.
    daily["augmentation_cost_eur"] = 30.
    daily["commissioning_energy_cost_eur"] = 10.
    result = evaluate_project_finance(daily, config)
    assert result.summary["npv_eur"] == pytest.approx(-40.)
    assert result.summary["dispatch_wear_penalty_eur"] == pytest.approx(20.)
    # Existing degradation CSVs have the penalty but no explicit cash-margin column.
    legacy = evaluate_project_finance(daily.drop(columns="market_cash_margin_eur"), config)
    assert legacy.summary["npv_eur"] == pytest.approx(-40.)
    daily["market_cash_margin_eur"] = 999.
    with pytest.raises(FinanceInputError, match="reconcile"):
        evaluate_project_finance(daily, config)


def degradation_case(*, fade=0., events=(), price=50., end=date(2025, 1, 3)):
    prices = generate_synthetic_prices(date(2025, 1, 1), end, negative_price_share=0)
    prices["price_eur_per_mwh"] = price
    battery = BatteryDispatchConfig(charge_power_mw=50, discharge_power_mw=50,
                                   energy_capacity_mwh=100, initial_soc_fraction=.5,
                                   soc_min_fraction=0, soc_max_fraction=1,
                                   charge_efficiency=.9, discharge_efficiency=.8)
    degradation = DegradationConfig(project_start_day=date(2025, 1, 1),
                                    calendar_fade_fraction_per_year=fade,
                                    cycle_fade_fraction_per_equivalent_cycle=0,
                                    power_fade_exponent=0, augmentation_events=events)
    return prices, battery, degradation


def test_empty_energy_only_augmentation_is_charged_from_the_grid():
    event = AugmentationEvent("add", date(2025, 1, 2), 100, 0, 0)
    result = simulate_degradation_dispatch(*degradation_case(events=(event,)))
    day = result.daily_results.iloc[1]
    assert day["initial_energy_mwh"] == pytest.approx(50.)
    assert day["terminal_energy_mwh"] == pytest.approx(100.)
    assert day["grid_charge_mwh"] == pytest.approx(50 / .9)
    assert day["market_cash_margin_eur"] == pytest.approx(-50 * 50 / .9)
    assert day["usable_charge_power_mw_start"] == pytest.approx(50.)
    assert abs(day["energy_balance_residual_mwh"]) < 1e-7


def test_retirement_commissioning_and_calendar_fade_have_an_energy_ledger():
    event = AugmentationEvent("replace", date(2025, 1, 2), 100, 50, 50,
                              retired_cohort_ids=("initial",),
                              commissioning_energy_mwh=20, commissioning_energy_cost_eur=7)
    result = simulate_degradation_dispatch(*degradation_case(fade=.02, events=(event,)))
    daily = result.daily_results
    assert daily.iloc[1]["retired_stored_energy_mwh"] == pytest.approx(50)
    assert daily.iloc[1]["commissioning_energy_mwh"] == pytest.approx(20)
    assert daily.iloc[1]["grid_charge_mwh"] == pytest.approx(30 / .9)
    assert daily["commissioning_energy_cost_eur"].sum() == 7
    for row in daily.itertuples():
        balance = (row.opening_stored_energy_mwh + row.commissioning_energy_mwh
                   + row.grid_charge_mwh - row.grid_discharge_mwh
                   - row.retired_stored_energy_mwh - row.calendar_fade_energy_loss_mwh
                   - row.cycle_fade_energy_loss_mwh - row.conversion_loss_mwh
                   - row.self_discharge_loss_mwh - row.closing_stored_energy_mwh)
        assert balance == pytest.approx(0, abs=1e-7)


def test_calendar_fade_preserves_power_and_records_unavailable_energy():
    result = simulate_degradation_dispatch(*degradation_case(fade=.02))
    day = result.daily_results.iloc[1]
    assert day["usable_charge_power_mw_start"] == 50
    assert day["calendar_fade_energy_loss_mwh"] == pytest.approx(50 * .02 / 365.25)
    assert day["initial_energy_mwh"] == pytest.approx(day["opening_stored_energy_mwh"]
                                                     - day["calendar_fade_energy_loss_mwh"])


def test_cycle_fade_is_recorded_after_dispatch():
    prices, battery, degradation = degradation_case(price=0.)
    prices.loc[prices.index % 24 == 23, "price_eur_per_mwh"] = 100.
    degradation = replace(degradation, cycle_fade_fraction_per_equivalent_cycle=.1)
    result = simulate_degradation_dispatch(prices, battery, degradation)
    assert result.daily_results.iloc[0]["cycle_fade_energy_loss_mwh"] > 0
    assert result.daily_results["energy_balance_residual_mwh"].abs().max() < 1e-7
    assert result.daily_results.iloc[1]["opening_stored_energy_mwh"] == pytest.approx(
        result.daily_results.iloc[0]["closing_stored_energy_mwh"])


def test_zero_fade_preserves_the_existing_daily_dispatch_policy():
    prices, battery, degradation = degradation_case()
    prices.loc[prices.index % 24 == 23, "price_eur_per_mwh"] = 120.
    baseline = optimize_daily_perfect_foresight(prices, battery)
    aged = simulate_degradation_dispatch(prices, battery, degradation)
    for column in ("charge_mw", "discharge_mw", "energy_start_mwh", "energy_end_mwh"):
        np.testing.assert_allclose(
            baseline.schedule[column], aged.interval_schedule[column], atol=1e-7
        )
    assert aged.summary["net_market_margin_eur"] == pytest.approx(
        baseline.summary["net_market_margin_eur"])


def test_energy_ledger_includes_self_discharge_at_quarter_hour_resolution():
    _, battery, degradation = degradation_case()
    prices = generate_synthetic_prices(date(2025, 1, 1), date(2025, 1, 3),
                                       resolution_minutes=15, negative_price_share=0)
    battery = replace(battery, self_discharge_per_hour=.001)
    result = simulate_degradation_dispatch(prices, battery, degradation)
    assert result.daily_results["self_discharge_loss_mwh"].sum() > 0
    assert result.summary["maximum_energy_balance_residual_mwh"] < 1e-7


def test_cash_margin_in_forecast_results_uses_realized_prices_and_excludes_wear():
    prices, battery, _ = degradation_case(end=date(2025, 1, 5))
    prices.loc[prices.index % 24 == 23, "price_eur_per_mwh"] = 120.
    battery = replace(battery, degradation_cost_eur_per_mwh_discharged=10.)
    result = backtest_forecast_dispatch(prices, battery, method="daily_persistence")
    schedule = result.interval_schedule
    expected = (schedule["realized_price_eur_per_mwh"]
                * (schedule["discharge_grid_mwh"] - schedule["charge_grid_mwh"])
                - schedule["buy_fee_eur"] - schedule["sell_fee_eur"])
    np.testing.assert_allclose(schedule["market_cash_margin_eur"], expected)
    assert result.daily_results["monetary_degradation_adder_eur"].sum() > 0
    assert result.summary["market_cash_margin_eur"] == pytest.approx(expected.sum())
    start = str(result.daily_results["market_day"].iloc[0])
    end = str(result.daily_results["market_day"].iloc[-1])
    _, config = finance_case(start, end)
    financed = evaluate_project_finance(result.daily_results, config)
    assert financed.summary["realized_market_margin_eur"] == pytest.approx(expected.sum())


def test_same_day_retired_commissioning_energy_is_not_lost_from_the_ledger():
    events = (
        AugmentationEvent("a-temporary", date(2025, 1, 2), 10, 0, 0,
                          commissioning_energy_mwh=5),
        AugmentationEvent("b-replacement", date(2025, 1, 2), 10, 0, 0,
                          retired_cohort_ids=("a-temporary",)),
    )
    result = simulate_degradation_dispatch(*degradation_case(events=events))
    day = result.daily_results.iloc[1]
    assert day["commissioning_energy_mwh"] == 5
    assert day["retired_stored_energy_mwh"] == 5
    assert abs(day["energy_balance_residual_mwh"]) < 1e-7


def test_cash_only_finance_input_and_invalid_commissioning_cost():
    daily, config = finance_case(end="2025-01-01")
    daily = daily.rename(columns={"net_market_margin_eur": "market_cash_margin_eur"})
    assert evaluate_project_finance(daily, config).summary["npv_eur"] == -365
    daily["commissioning_energy_cost_eur"] = -1
    with pytest.raises(FinanceInputError, match="commissioning_energy_cost_eur"):
        evaluate_project_finance(daily, config)


def test_augmentation_cannot_overwrite_initial_energy_ledger():
    with pytest.raises(DegradationInputError, match="reserved"):
        AugmentationEvent("initial", date(2025, 1, 2), 100.0, 0.0, 0.0)


def study_case(*, adder=0., fade=0., events=(), window=(date(2026, 2, 1), date(2026, 2, 7))):
    """One short integrated study on synthetic prices, declared strategy by strategy."""

    start, end = window
    battery = BatteryDispatchConfig(charge_power_mw=50, discharge_power_mw=50,
                                    energy_capacity_mwh=100, initial_soc_fraction=.5,
                                    terminal_soc_fraction=.5,
                                    degradation_cost_eur_per_mwh_discharged=adder)
    config = IntegratedStudyConfig(
        study_id="accounting-regression", window_start_day=start, window_end_day=end,
        price_source="synthetic",
        strategies=(StrategySpec("pf", "perfect_foresight", "realized_delivery_day_prices"),),
        battery=battery,
        degradation=DegradationConfig(project_start_day=date(2026, 1, 1),
                                      calendar_fade_fraction_per_year=fade,
                                      cycle_fade_fraction_per_equivalent_cycle=0,
                                      power_fade_exponent=0, augmentation_events=events),
        finance=FinanceConfig(project_start_day=start, project_end_day=end,
                              operating_margin_case="daily_policy_degraded_simulation",
                              discount_rate_fraction=0., battery_system_capex_eur=1_000.),
        result_label="Deterministic synthetic prices; a test fixture and not market evidence.")
    prices = generate_synthetic_prices(date(2026, 1, 1), end + timedelta(days=1),
                                       resolution_minutes=60, seed=7)
    return assemble_integrated_study(run_integrated_study(prices, config))


def test_integrated_study_does_not_pay_the_dispatch_wear_penalty_in_cash():
    """A shadow wear penalty steers the plan; it is not an expense anyone settles."""

    summary = study_case(adder=5.).strategy_summaries.iloc[0]
    wear = summary["monetary_degradation_adder_eur"]
    assert wear > 0
    assert summary["market_cash_margin_eur"] == pytest.approx(
        summary["net_market_margin_eur"] + wear
    )
    # Finance reads the cash line, so NPV is better than the wear-as-cash figure by the
    # whole penalty. At a zero discount rate the difference is exactly the penalty.
    assert summary["realized_market_margin_eur"] == pytest.approx(
        summary["market_cash_margin_eur"]
    )
    assert summary["npv_eur"] == pytest.approx(
        summary["market_cash_margin_eur"] - 1_000.
    )


def test_integrated_study_augmentation_does_not_create_stored_energy():
    """Added capacity is empty. Restoring the configured SOC would invent energy."""

    event = AugmentationEvent("add", date(2026, 2, 4), 100, 0, 0, cost_eur=10.)
    daily = study_case(events=(event,)).daily_results
    carried = daily["initial_energy_mwh"].to_numpy()[1:]
    closed = daily["terminal_energy_mwh"].to_numpy()[:-1]
    assert carried == pytest.approx(closed)
    augmented = daily.loc[daily["market_day"] == date(2026, 2, 4)].iloc[0]
    assert augmented["usable_energy_mwh_start"] == pytest.approx(200.)
    assert augmented["initial_energy_mwh"] == pytest.approx(50.)
    assert augmented["commissioning_energy_mwh"] == pytest.approx(0.)
    assert daily["energy_balance_residual_mwh"].abs().max() < 1e-7


def test_integrated_study_charges_declared_commissioning_energy_once():
    """Energy that arrives with the new capacity is declared, and paid for once."""

    event = AugmentationEvent("add", date(2026, 2, 4), 100, 0, 0, cost_eur=10.,
                              commissioning_energy_mwh=40.,
                              commissioning_energy_cost_eur=400.)
    result = study_case(events=(event,))
    augmented = result.daily_results.loc[
        result.daily_results["market_day"] == date(2026, 2, 4)
    ].iloc[0]
    assert augmented["initial_energy_mwh"] == pytest.approx(90.)
    assert augmented["commissioning_energy_cost_eur"] == pytest.approx(400.)
    summary = result.strategy_summaries.iloc[0]
    assert summary["commissioning_energy_cost_eur"] == pytest.approx(400.)
    assert summary["npv_eur"] == pytest.approx(
        summary["market_cash_margin_eur"] - 1_000. - 10. - 400.
    )
