"""The integrated study's acceptance checks, as the execution plan states them.

Section 7 of `docs/integrated_study_design.md` restates stage 8's acceptance checks as eight
testable statements. Each one has a test here under a name that says which check it is, so a
check that stops holding fails by name rather than by arithmetic nobody can place.

Two of them are worth naming again because they are the ones a plausible-looking defect would
pass: **separate evolution**, because sharing one degradation state across the strategy loop
produces believable numbers in which a cautious strategy pays for an aggressive one's
throughput; and **causality**, because a forecast that could see the days after the one it
plans would produce better figures and no error.
"""

from __future__ import annotations

import json
import unittest
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from greek_bess.backtest.forecast_dispatch import backtest_forecast_dispatch
from greek_bess.cli import main
from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.degradation import AugmentationEvent, DegradationConfig
from greek_bess.dispatch import BatteryDispatchConfig
from greek_bess.finance import FinanceConfig
from greek_bess.reporting import read_run_manifest
from greek_bess.study import (
    IntegratedStudyConfig,
    IntegratedStudyInputError,
    StrategySpec,
    assemble_integrated_study,
    read_integrated_study_config,
    run_integrated_study,
)
from greek_bess.study.results import _refuse_shared_state

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"

HISTORY_START = date(2026, 1, 1)
HISTORY_END = date(2026, 3, 1)
WINDOW_START = date(2026, 2, 1)
WINDOW_END = date(2026, 2, 14)

PERFECT_FORESIGHT = StrategySpec(
    "ceiling-under-own-state", "perfect_foresight", "realized_delivery_day_prices"
)
DAILY_PERSISTENCE = StrategySpec(
    "daily-persistence", "daily_persistence", "price_history_before_delivery_day"
)
WEEKLY_PERSISTENCE = StrategySpec(
    "weekly-persistence", "weekly_persistence", "price_history_before_delivery_day"
)


def _prices(seed: int = 7) -> pd.DataFrame:
    return generate_synthetic_prices(
        HISTORY_START, HISTORY_END, resolution_minutes=60, seed=seed
    )


def _battery(**overrides: object) -> BatteryDispatchConfig:
    defaults: dict[str, object] = {
        "charge_power_mw": 50.0,
        "discharge_power_mw": 50.0,
        "energy_capacity_mwh": 100.0,
        "initial_soc_fraction": 0.5,
        "terminal_soc_fraction": 0.5,
    }
    defaults.update(overrides)
    return BatteryDispatchConfig(**defaults)  # type: ignore[arg-type]


def _degradation(**overrides: object) -> DegradationConfig:
    defaults: dict[str, object] = {
        "project_start_day": HISTORY_START,
        "calendar_fade_fraction_per_year": 0.015,
        "cycle_fade_fraction_per_equivalent_cycle": 0.00004,
    }
    defaults.update(overrides)
    return DegradationConfig(**defaults)  # type: ignore[arg-type]


def _finance(
    start: date = WINDOW_START, end: date = WINDOW_END, **overrides: object
) -> FinanceConfig:
    defaults: dict[str, object] = {
        "project_start_day": start,
        "project_end_day": end,
        "operating_margin_case": "historical_forecast_backtest",
        "discount_rate_fraction": 0.08,
        "battery_system_capex_eur": 30_000_000.0,
    }
    defaults.update(overrides)
    return FinanceConfig(**defaults)  # type: ignore[arg-type]


def _config(
    strategies: tuple[StrategySpec, ...] = (PERFECT_FORESIGHT, DAILY_PERSISTENCE),
    *,
    window_start: date = WINDOW_START,
    window_end: date = WINDOW_END,
    battery: BatteryDispatchConfig | None = None,
    degradation: DegradationConfig | None = None,
    finance: FinanceConfig | None = None,
    study_id: str = "acceptance-study",
) -> IntegratedStudyConfig:
    return IntegratedStudyConfig(
        study_id=study_id,
        window_start_day=window_start,
        window_end_day=window_end,
        price_source="synthetic",
        strategies=strategies,
        battery=battery or _battery(),
        degradation=degradation or _degradation(),
        finance=finance or _finance(window_start, window_end),
        result_label="Deterministic synthetic prices; a test fixture and not market evidence.",
    )


def _run(config: IntegratedStudyConfig, prices: pd.DataFrame | None = None):
    return assemble_integrated_study(
        run_integrated_study(_prices() if prices is None else prices, config)
    )


class DeclaredStudyTests(unittest.TestCase):
    """A study that cannot be run exactly as declared is refused before it runs."""

    def test_finance_must_cover_exactly_the_declared_window(self) -> None:
        with self.assertRaises(IntegratedStudyInputError) as raised:
            _config(finance=_finance(WINDOW_START, WINDOW_END + timedelta(days=30)))
        self.assertIn("exactly the declared study window", str(raised.exception))
        self.assertIn("does not annualise", str(raised.exception))

    def test_terminal_soc_must_restore_the_initial_soc(self) -> None:
        with self.assertRaises(IntegratedStudyInputError) as raised:
            _config(battery=_battery(terminal_soc_fraction=0.6))
        self.assertIn("borrow energy across days", str(raised.exception))

    def test_a_strategy_cannot_misdescribe_what_it_reads(self) -> None:
        with self.assertRaises(IntegratedStudyInputError) as raised:
            StrategySpec(
                "mislabelled", "perfect_foresight", "price_history_before_delivery_day"
            )
        self.assertIn("misdescribes what it knows", str(raised.exception))

    def test_strategy_identifiers_must_be_unique(self) -> None:
        with self.assertRaises(IntegratedStudyInputError):
            _config((DAILY_PERSISTENCE, replace(DAILY_PERSISTENCE, planner="ensemble")))

    def test_the_window_cannot_begin_before_the_project_starts(self) -> None:
        with self.assertRaises(IntegratedStudyInputError) as raised:
            _config(degradation=_degradation(project_start_day=date(2026, 2, 2)))
        self.assertIn("degradation project_start_day", str(raised.exception))

    def test_the_committed_example_parses_through_the_reader(self) -> None:
        config = read_integrated_study_config(
            EXAMPLES / "integrated_study_synthetic_demonstration.json"
        )
        self.assertEqual(config.price_source, "synthetic")
        self.assertEqual(len(config.strategies), 3)
        self.assertEqual(config.finance.project_start_day, config.window_start_day)
        self.assertEqual(config.finance.project_end_day, config.window_end_day)


class CheckOneOneCommandOneConfiguration(unittest.TestCase):
    """Check 1: one command and one configuration produce a complete study."""

    def test_the_command_writes_the_five_declared_artifacts(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            prices_path = root / "prices.csv"
            export = _prices().copy()
            export["quality_flags"] = export["quality_flags"].map(json.dumps)
            export.to_csv(prices_path, index=False)

            config_path = root / "study.json"
            payload = json.loads(
                (EXAMPLES / "integrated_study_synthetic_demonstration.json").read_text(
                    encoding="utf-8"
                )
            )
            payload["study_id"] = "cli-study"
            payload["window_start_day"] = WINDOW_START.isoformat()
            payload["window_end_day"] = WINDOW_END.isoformat()
            payload["finance"]["project_start_day"] = WINDOW_START.isoformat()
            payload["finance"]["project_end_day"] = WINDOW_END.isoformat()
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            exit_code = main(
                [
                    "run-integrated-study",
                    str(prices_path),
                    "--study-config",
                    str(config_path),
                    "--output-dir",
                    str(root / "outputs"),
                ]
            )
            self.assertEqual(exit_code, 0)
            outputs = root / "outputs"
            for suffix in (
                ".daily.csv",
                ".strategies.csv",
                ".cash_flows.csv",
                ".summary.json",
                ".manifest.json",
            ):
                with self.subTest(artifact=suffix):
                    self.assertTrue((outputs / f"cli-study{suffix}").exists())

            manifest = read_run_manifest(outputs / "cli-study.manifest.json")
            self.assertEqual(manifest.result_kind, "integrated_study")
            self.assertEqual(manifest.basis, "historical_replay_simulation")
            self.assertIn("not investment evidence", manifest.result_label)
            daily = pd.read_csv(outputs / "cli-study.daily.csv")
            self.assertEqual(daily["strategy_id"].nunique(), 3)
            self.assertEqual(len(daily), 3 * 14)


class CheckTwoZeroFadeReproduction(unittest.TestCase):
    """Check 2: with no fade, the study reproduces the existing fixed-battery backtest."""

    def test_a_zero_fade_study_reproduces_the_forecast_dispatch_backtest(self) -> None:
        battery = _battery()
        config = _config(
            (PERFECT_FORESIGHT, DAILY_PERSISTENCE),
            battery=battery,
            degradation=_degradation(
                calendar_fade_fraction_per_year=0.0,
                cycle_fade_fraction_per_equivalent_cycle=0.0,
            ),
        )
        study = _run(config)
        reference = backtest_forecast_dispatch(
            _prices(), battery, method="daily_persistence"
        )
        reference_daily = reference.daily_results.set_index("market_day")

        for row in study.daily_results.itertuples(index=False):
            if row.market_day not in reference_daily.index:
                continue
            expected = reference_daily.loc[row.market_day]
            if row.strategy_id == DAILY_PERSISTENCE.strategy_id:
                self.assertAlmostEqual(
                    row.net_market_margin_eur,
                    float(expected["realized_margin_eur"]),
                    places=6,
                    msg=f"{row.market_day} forecast-planned margin",
                )
            else:
                self.assertAlmostEqual(
                    row.net_market_margin_eur,
                    float(expected["perfect_foresight_margin_eur"]),
                    places=6,
                    msg=f"{row.market_day} perfect-foresight margin",
                )

    def test_no_fade_means_the_battery_never_shrinks(self) -> None:
        config = _config(
            (DAILY_PERSISTENCE,),
            degradation=_degradation(
                calendar_fade_fraction_per_year=0.0,
                cycle_fade_fraction_per_equivalent_cycle=0.0,
            ),
        )
        study = _run(config)
        self.assertTrue(
            np.allclose(
                study.daily_results["usable_energy_mwh_start"].to_numpy(dtype=float),
                config.battery.energy_capacity_mwh,
            )
        )


class CheckThreeSeparateEvolution(unittest.TestCase):
    """Check 3: strategies age separately and declaration order reaches no result."""

    def test_different_throughput_reaches_different_end_of_window_capacity(self) -> None:
        study = _run(_config((PERFECT_FORESIGHT, DAILY_PERSISTENCE)))
        summaries = study.strategy_summaries.set_index("strategy_id")
        throughput = summaries["cell_discharge_mwh"]
        capacity = summaries["final_usable_energy_mwh"]
        self.assertNotAlmostEqual(
            float(throughput.iloc[0]), float(throughput.iloc[1]), places=3
        )
        self.assertNotAlmostEqual(
            float(capacity.iloc[0]), float(capacity.iloc[1]), places=6
        )
        # The strategy that discharged more must be the one that aged more.
        heavier = throughput.idxmax()
        self.assertEqual(capacity.idxmin(), heavier)

    def test_declaration_order_does_not_change_any_strategy_result(self) -> None:
        forward = _run(_config((PERFECT_FORESIGHT, DAILY_PERSISTENCE)))
        reversed_order = _run(_config((DAILY_PERSISTENCE, PERFECT_FORESIGHT)))
        for frame in (forward, reversed_order):
            frame.strategy_summaries.sort_values("strategy_id", inplace=True)
        pd.testing.assert_frame_equal(
            forward.strategy_summaries.reset_index(drop=True),
            reversed_order.strategy_summaries.reset_index(drop=True),
        )

    def test_the_symptom_check_is_silent_where_capacity_cannot_move(self) -> None:
        # Under zero cycle fade, identical capacities are the correct answer rather than the
        # symptom of a shared state, and check 2 depends on that run being allowed.
        zero_fade = _config(
            (PERFECT_FORESIGHT, DAILY_PERSISTENCE),
            degradation=_degradation(
                calendar_fade_fraction_per_year=0.0,
                cycle_fade_fraction_per_equivalent_cycle=0.0,
            ),
        )
        shared = pd.DataFrame.from_records(
            [
                {
                    "strategy_id": "a",
                    "cell_discharge_mwh": 100.0,
                    "final_usable_energy_mwh": 99.0,
                },
                {
                    "strategy_id": "b",
                    "cell_discharge_mwh": 200.0,
                    "final_usable_energy_mwh": 99.0,
                },
            ]
        )
        _refuse_shared_state(zero_fade, shared)

    def test_a_shared_degradation_state_is_refused_on_its_symptom(self) -> None:
        shared = pd.DataFrame.from_records(
            [
                {
                    "strategy_id": "a",
                    "cell_discharge_mwh": 100.0,
                    "final_usable_energy_mwh": 99.0,
                },
                {
                    "strategy_id": "b",
                    "cell_discharge_mwh": 200.0,
                    "final_usable_energy_mwh": 99.0,
                },
            ]
        )
        with self.assertRaises(IntegratedStudyInputError) as raised:
            _refuse_shared_state(_config(), shared)
        self.assertIn("own its degradation state", str(raised.exception))


class CheckFourCausality(unittest.TestCase):
    """Check 4: modifying future information cannot change an earlier decision."""

    def test_prices_after_a_day_cannot_change_that_day_or_any_earlier_one(self) -> None:
        config = _config((PERFECT_FORESIGHT, DAILY_PERSISTENCE, WEEKLY_PERSISTENCE))
        boundary = WINDOW_START + timedelta(days=6)

        baseline = _run(config)
        mutated_prices = _prices().copy()
        future = mutated_prices["delivery_start_market"].dt.date.gt(boundary)
        self.assertTrue(bool(future.any()))
        mutated_prices.loc[future, "price_eur_per_mwh"] = (
            mutated_prices.loc[future, "price_eur_per_mwh"] * 7.0 + 250.0
        )
        mutated = _run(config, mutated_prices)

        def upto(frame: pd.DataFrame) -> pd.DataFrame:
            return (
                frame.loc[frame["market_day"].le(boundary)]
                .sort_values(["strategy_id", "market_day"])
                .reset_index(drop=True)
            )

        pd.testing.assert_frame_equal(
            upto(baseline.daily_results), upto(mutated.daily_results)
        )

    def test_prices_after_the_window_are_discarded_and_counted(self) -> None:
        study = _run(_config((DAILY_PERSISTENCE,)))
        coverage = study.summary["coverage"]
        self.assertEqual(coverage["discarded_post_window_day_count"], 14)
        self.assertGreater(coverage["discarded_post_window_interval_count"], 0)


class CheckFiveReconciliation(unittest.TestCase):
    """Check 5: energy, fees, the monetary adder and augmentation all reconcile."""

    def test_fees_the_adder_and_augmentation_reconcile_against_their_inputs(self) -> None:
        battery = _battery(
            buy_fee_eur_per_mwh=1.25,
            sell_fee_eur_per_mwh=0.75,
            degradation_cost_eur_per_mwh_discharged=2.5,
        )
        degradation = _degradation(
            augmentation_events=(
                AugmentationEvent(
                    event_id="mid-window-augmentation",
                    day=WINDOW_START + timedelta(days=5),
                    added_energy_mwh=5.0,
                    added_charge_power_mw=2.0,
                    added_discharge_power_mw=2.0,
                    cost_eur=125_000.0,
                ),
            )
        )
        study = _run(
            _config((DAILY_PERSISTENCE,), battery=battery, degradation=degradation)
        )
        daily = study.daily_results
        summary = study.strategy_summaries.iloc[0]

        self.assertAlmostEqual(
            float(summary["monetary_degradation_adder_eur"]),
            float(daily["grid_discharge_mwh"].sum())
            * battery.degradation_cost_eur_per_mwh_discharged,
            places=6,
        )
        self.assertAlmostEqual(
            float(summary["buy_fees_eur"]),
            float(daily["grid_charge_mwh"].sum()) * battery.buy_fee_eur_per_mwh,
            places=6,
        )
        self.assertAlmostEqual(float(summary["augmentation_cost_eur"]), 125_000.0, places=6)

        # Physical fade and the monetary adder are distinct quantities, reported separately.
        self.assertLess(
            float(summary["final_usable_energy_mwh"]),
            float(summary["initial_usable_energy_mwh"]) + 5.0,
        )
        self.assertNotAlmostEqual(
            float(summary["monetary_degradation_adder_eur"]),
            float(summary["augmentation_cost_eur"]),
        )
        # The adder is inside the settled margin; the augmentation cost is not. Counting it
        # twice is the error this check exists to catch.
        self.assertAlmostEqual(
            float(summary["net_market_margin_eur"]),
            float(
                daily["discharge_energy_revenue_eur"].sum()
                - daily["charging_energy_cost_eur"].sum()
                - daily["buy_fees_eur"].sum()
                - daily["sell_fees_eur"].sum()
                - daily["monetary_degradation_adder_eur"].sum()
            ),
            places=6,
        )

    def test_every_day_starts_and_ends_at_the_configured_state_of_charge(self) -> None:
        study = _run(_config((DAILY_PERSISTENCE,)))
        daily = study.daily_results
        self.assertTrue(
            np.allclose(
                daily["initial_energy_mwh"].to_numpy(dtype=float),
                daily["configured_initial_energy_mwh"].to_numpy(dtype=float),
                atol=1e-6,
            )
        )
        self.assertTrue(
            np.allclose(
                daily["terminal_energy_mwh"].to_numpy(dtype=float),
                daily["configured_terminal_energy_mwh"].to_numpy(dtype=float),
                atol=1e-6,
            )
        )


class CheckSixMissingDaysFailClearly(unittest.TestCase):
    """Check 6: a missing input day fails the run, naming the day and the cause."""

    def test_a_gap_inside_the_window_names_the_first_missing_day(self) -> None:
        gap_day = WINDOW_START + timedelta(days=3)
        prices = _prices()
        prices = prices.loc[
            prices["delivery_start_market"].dt.date.ne(gap_day)
        ].reset_index(drop=True)
        with self.assertRaises(IntegratedStudyInputError) as raised:
            _run(_config((DAILY_PERSISTENCE,)), prices)
        message = str(raised.exception)
        self.assertIn(gap_day.isoformat(), message)
        self.assertIn("refuses a gap rather than bridging it", message)

    def test_an_incomplete_forecast_day_fails_rather_than_being_excluded(self) -> None:
        # A window that starts on the first day of the supplied history leaves the weekly
        # planner with nothing to persist from. That is a refusal, not an excluded day.
        config = _config(
            (WEEKLY_PERSISTENCE,),
            window_start=HISTORY_START,
            window_end=HISTORY_START + timedelta(days=5),
            finance=_finance(HISTORY_START, HISTORY_START + timedelta(days=5)),
        )
        with self.assertRaises(IntegratedStudyInputError) as raised:
            _run(config)
        self.assertIn("weekly_persistence forecast is incomplete", str(raised.exception))
        self.assertIn("narrower window", str(raised.exception))


class CheckSevenDeterminism(unittest.TestCase):
    """Check 7: repeated execution preserves results and content identity."""

    def test_two_runs_of_one_configuration_agree_exactly(self) -> None:
        config = _config((PERFECT_FORESIGHT, DAILY_PERSISTENCE))
        first = _run(config)
        second = _run(config)
        pd.testing.assert_frame_equal(first.daily_results, second.daily_results)
        pd.testing.assert_frame_equal(
            first.strategy_summaries, second.strategy_summaries
        )
        pd.testing.assert_frame_equal(first.cash_flows, second.cash_flows)
        self.assertEqual(
            json.dumps(first.summary, sort_keys=True, default=str),
            json.dumps(second.summary, sort_keys=True, default=str),
        )


class CheckEightNoSharedCeiling(unittest.TestCase):
    """Check 8: no ceiling is asserted across strategies once their states diverge."""

    def test_the_ceiling_stays_per_strategy_and_per_day(self) -> None:
        study = _run(_config((PERFECT_FORESIGHT, DAILY_PERSISTENCE)))
        self.assertIs(study.summary["shared_ceiling_reported"], False)
        self.assertIn("under each strategy's own state", study.summary["ceiling_policy"])
        self.assertIn("day_ceiling_under_own_state_eur", study.daily_results.columns)

        # The per-day ceiling exists; no aggregate of it is recorded anywhere a reader could
        # take for a study-wide bound.
        ceiling_keys = [key for key in study.summary if "ceiling" in key]
        self.assertEqual(sorted(ceiling_keys), ["ceiling_policy", "shared_ceiling_reported"])
        self.assertEqual(
            [
                column
                for column in study.strategy_summaries.columns
                if "ceiling" in column
            ],
            [],
        )

    def test_the_result_basis_states_why_the_total_is_not_a_bound(self) -> None:
        study = _run(_config((DAILY_PERSISTENCE,)))
        note = study.summary["result_basis_note"]
        self.assertIn("not a ceiling over policies", note)
        self.assertIn("different physical states", note)


class OperatingMarginCaseTests(unittest.TestCase):
    """The finance case describes the path, so each strategy carries its own."""

    def test_each_strategy_is_financed_under_its_own_case(self) -> None:
        study = _run(_config((PERFECT_FORESIGHT, DAILY_PERSISTENCE)))
        cases = dict(
            zip(
                study.strategy_summaries["strategy_id"],
                study.strategy_summaries["operating_margin_case"],
                strict=True,
            )
        )
        self.assertEqual(
            cases[PERFECT_FORESIGHT.strategy_id], "daily_policy_degraded_simulation"
        )
        self.assertEqual(
            cases[DAILY_PERSISTENCE.strategy_id], "historical_forecast_backtest"
        )
        self.assertEqual(
            study.summary["declared_finance_operating_margin_case"],
            "historical_forecast_backtest",
        )
        self.assertIn(
            "derived from each strategy's planner",
            study.summary["operating_margin_case_policy"],
        )


if __name__ == "__main__":
    unittest.main()
