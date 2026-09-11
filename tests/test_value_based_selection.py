"""Stage 9: selecting a forecast by price error against selecting it by battery value.

The case that matters here is the one where the two objectives disagree. If a lower RMSE always
settled more margin, Stage 9 would be measuring nothing and the existing rule would be right by
construction. So the first test builds a day where a candidate with a *better* RMSE settles
*less* margin, and pins that the two rules then select different candidates.

The construction is deliberately transparent rather than tuned. A battery earns from the
ordering of prices inside a delivery day, so a forecast that is wrong by a constant keeps every
ordering and dispatches perfectly, while a forecast that is right almost everywhere but moves
the cheapest hour buys at the wrong time. The second is closer on price and worse on value.
"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from greek_bess.cli import main
from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.dispatch import BatteryDispatchConfig
from greek_bess.forecast import generate_naive_forecasts
from greek_bess.forecast.ml import MLForecastConfig
from greek_bess.selection import (
    SelectionCandidate,
    SelectionCandidateError,
    ValueSelectionInputError,
    compare_selection_objectives,
    generate_candidate_forecasts,
)
from greek_bess.selection.candidates import FORECAST_INDEX_COLUMNS

#: One flat day with a single deep trough and a single peak. The trough is negative because a
#: negative price is a real Greek DAM outcome this repository preserves rather than floors.
FLAT_PRICE = 50.0
TROUGH_PRICE = -20.0
PEAK_PRICE = 150.0
TROUGH_HOUR = 3
PEAK_HOUR = 20
#: The hour the low-RMSE candidate mistakes for the trough.
DECOY_HOUR = 12


def battery() -> BatteryDispatchConfig:
    # Lossless and fee-free so that the margin difference the test reads is the dispatch
    # decision and not a round-trip efficiency term.
    return BatteryDispatchConfig(
        charge_power_mw=1.0,
        discharge_power_mw=1.0,
        energy_capacity_mwh=2.0,
        soc_min_fraction=0.1,
        soc_max_fraction=0.9,
        initial_soc_fraction=0.5,
        terminal_soc_fraction=0.5,
        charge_efficiency=1.0,
        discharge_efficiency=1.0,
    )


def shaped_prices(start: date, day_count: int) -> pd.DataFrame:
    """A canonical hourly frame whose every market day carries the same trough and peak."""

    prices = generate_synthetic_prices(
        start, start + timedelta(days=day_count), seed=11
    )
    hour = prices["delivery_start_market"].dt.hour.to_numpy()
    shaped = np.full(len(prices), FLAT_PRICE)
    shaped[hour == TROUGH_HOUR] = TROUGH_PRICE
    shaped[hour == PEAK_HOUR] = PEAK_PRICE
    prices = prices.copy()
    prices["price_eur_per_mwh"] = shaped
    return prices


def divergent_forecasts(prices: pd.DataFrame, evaluation_start: date) -> pd.DataFrame:
    """Two candidates: one closer on price, one right about which hour is cheapest."""

    # Built from the naive forecast table rather than the raw price frame, because that is
    # where the slot and occurrence columns a candidate forecast table carries come from, and a
    # fixture shaped differently from the real path would test the wrong thing.
    table = generate_naive_forecasts(prices).forecasts.copy()
    table["split"] = np.where(
        table["market_day"] < evaluation_start, "validation", "evaluation"
    )
    hour = table["delivery_start_market"].dt.hour.to_numpy()
    actual = table["actual_price_eur_per_mwh"].to_numpy(dtype=float)

    # Right almost everywhere, but it moves the trough to a decoy hour: small error, wrong
    # decision.
    low_rmse = actual.copy()
    low_rmse[hour == TROUGH_HOUR] = FLAT_PRICE
    low_rmse[hour == DECOY_HOUR] = TROUGH_PRICE
    table["low_rmse_wrong_order"] = low_rmse

    # Wrong by a constant everywhere: large error, and every ordering preserved.
    table["high_rmse_right_order"] = actual + 30.0
    return table.loc[
        :, [*FORECAST_INDEX_COLUMNS, "low_rmse_wrong_order", "high_rmse_right_order"]
    ].reset_index(drop=True)


DIVERGENT_GRID = (
    SelectionCandidate("low_rmse_wrong_order", "ridge"),
    SelectionCandidate("high_rmse_right_order", "ridge"),
)


class RmseAndValueCanDisagreeTests(unittest.TestCase):
    """The synthetic case Stage 9's acceptance checks require."""

    def setUp(self) -> None:
        self.evaluation_start = date(2026, 3, 5)
        self.prices = shaped_prices(date(2026, 3, 1), 8)
        self.forecasts = divergent_forecasts(self.prices, self.evaluation_start)
        self.result = compare_selection_objectives(
            self.prices, battery(), self.forecasts, candidates=DIVERGENT_GRID
        )

    def test_the_better_rmse_candidate_settles_less_margin(self) -> None:
        board = self.result.validation_scoreboard.set_index("candidate")
        low = board.loc["low_rmse_wrong_order"]
        high = board.loc["high_rmse_right_order"]

        self.assertLess(low["rmse_eur_per_mwh"], high["rmse_eur_per_mwh"])
        self.assertGreater(high["realized_margin_eur"], low["realized_margin_eur"])

    def test_the_two_objectives_select_different_candidates(self) -> None:
        summary = self.result.summary

        self.assertEqual(summary["selected_by_validation_rmse"], "low_rmse_wrong_order")
        self.assertEqual(
            summary["selected_by_validation_settled_margin"], "high_rmse_right_order"
        )
        self.assertFalse(summary["objectives_agree"])

    def test_value_selection_settles_more_on_the_held_out_window(self) -> None:
        summary = self.result.summary
        by_margin = self.result.objective_results["validation_settled_margin"]
        by_rmse = self.result.objective_results["validation_rmse"]

        self.assertGreater(summary["margin_minus_rmse_selection_eur"], 0.0)
        self.assertTrue(summary["margin_selection_favoured"])
        # The headline difference is computed where the basis lives, not by subtracting two
        # reported totals downstream.
        self.assertAlmostEqual(
            summary["margin_minus_rmse_selection_eur"],
            by_margin["realized_margin_eur"] - by_rmse["realized_margin_eur"],
            places=9,
        )

    def test_the_order_preserving_candidate_reaches_the_ceiling(self) -> None:
        # A forecast wrong by a constant keeps every ordering, so it should dispatch exactly as
        # perfect foresight does. That is what makes this construction a fair demonstration
        # rather than a rigged one: the high-RMSE arm wins on value for a stated reason.
        by_margin = self.result.objective_results["validation_settled_margin"]

        self.assertAlmostEqual(by_margin["perfect_foresight_regret_eur"], 0.0, places=6)

    def test_cycling_and_capacity_are_reported_beside_the_margin(self) -> None:
        for objective, record in self.result.objective_results.items():
            with self.subTest(objective=objective):
                for key in (
                    "equivalent_full_cycles",
                    "grid_charge_mwh",
                    "grid_discharge_mwh",
                    "energy_capacity_mwh",
                    "charge_power_mw",
                    "discharge_power_mw",
                    "rmse_eur_per_mwh",
                    "mae_eur_per_mwh",
                    "retrospective_best_regret_eur",
                ):
                    self.assertIn(key, record)

    def test_the_window_is_labelled_retrospective_by_default(self) -> None:
        self.assertEqual(
            self.result.summary["evidence_class"], "retrospective_supplementary"
        )


class FrozenSelectionTests(unittest.TestCase):
    def test_selection_does_not_move_when_the_evaluation_window_changes(self) -> None:
        # The strongest available statement that selection cannot see the evaluation window:
        # change the evaluation prices, leave validation untouched, and the sealed record must
        # be byte-identical.
        evaluation_start = date(2026, 3, 5)
        prices = shaped_prices(date(2026, 3, 1), 8)
        forecasts = divergent_forecasts(prices, evaluation_start)

        moved = prices.copy()
        evaluation_rows = moved["delivery_start_market"].dt.date >= evaluation_start
        moved.loc[evaluation_rows, "price_eur_per_mwh"] = (
            moved.loc[evaluation_rows, "price_eur_per_mwh"] * 3.0
        )

        first = compare_selection_objectives(
            prices, battery(), forecasts, candidates=DIVERGENT_GRID
        )
        second = compare_selection_objectives(
            moved, battery(), forecasts, candidates=DIVERGENT_GRID
        )

        self.assertEqual(
            first.summary["frozen_selection_sha256"],
            second.summary["frozen_selection_sha256"],
        )
        self.assertEqual(first.frozen_selection, second.frozen_selection)
        # The evaluation result did move, so the invariance above is a property of the freeze
        # rather than of an experiment that ignored its own inputs.
        self.assertNotAlmostEqual(
            first.summary["margin_minus_rmse_selection_eur"],
            second.summary["margin_minus_rmse_selection_eur"],
            places=6,
        )

    def test_the_forecast_digest_names_the_table_the_figures_came_from(self) -> None:
        prices = shaped_prices(date(2026, 3, 1), 8)
        forecasts = divergent_forecasts(prices, date(2026, 3, 5))
        nudged = forecasts.copy()
        nudged.loc[0, "high_rmse_right_order"] += 0.5

        first = compare_selection_objectives(
            prices, battery(), forecasts, candidates=DIVERGENT_GRID
        ).summary
        again = compare_selection_objectives(
            prices, battery(), forecasts, candidates=DIVERGENT_GRID
        ).summary
        changed = compare_selection_objectives(
            prices, battery(), nudged, candidates=DIVERGENT_GRID
        ).summary

        self.assertEqual(first["candidate_forecast_sha256"], again["candidate_forecast_sha256"])
        self.assertNotEqual(
            first["candidate_forecast_sha256"], changed["candidate_forecast_sha256"]
        )

    def test_a_tie_breaks_by_declared_order_and_is_recorded(self) -> None:
        evaluation_start = date(2026, 3, 5)
        prices = shaped_prices(date(2026, 3, 1), 8)
        forecasts = divergent_forecasts(prices, evaluation_start)
        # Two candidates carrying identical forecasts: every objective ties exactly.
        forecasts = forecasts.copy()
        forecasts["twin_second"] = forecasts["low_rmse_wrong_order"]
        forecasts = forecasts.rename(columns={"low_rmse_wrong_order": "twin_first"})
        grid = (
            SelectionCandidate("twin_first", "ridge"),
            SelectionCandidate("twin_second", "ridge"),
        )

        result = compare_selection_objectives(
            prices,
            battery(),
            forecasts.loc[:, [*FORECAST_INDEX_COLUMNS, "twin_first", "twin_second"]],
            candidates=grid,
        )

        for objective, selection in result.frozen_selection["selections"].items():
            with self.subTest(objective=objective):
                self.assertTrue(selection["tie_occurred"])
                self.assertEqual(
                    selection["tied_candidates"], ["twin_first", "twin_second"]
                )
                self.assertEqual(selection["selected_candidate"], "twin_first")
                self.assertEqual(selection["selected_declared_index"], 0)

    def test_both_objectives_selecting_one_candidate_is_reported_as_distinguishing_nothing(
        self,
    ) -> None:
        evaluation_start = date(2026, 3, 5)
        prices = shaped_prices(date(2026, 3, 1), 8)
        forecasts = divergent_forecasts(prices, evaluation_start)
        forecasts = forecasts.copy()
        forecasts["twin_second"] = forecasts["low_rmse_wrong_order"]
        forecasts = forecasts.rename(columns={"low_rmse_wrong_order": "twin_first"})
        grid = (
            SelectionCandidate("twin_first", "ridge"),
            SelectionCandidate("twin_second", "ridge"),
        )

        summary = compare_selection_objectives(
            prices,
            battery(),
            forecasts.loc[:, [*FORECAST_INDEX_COLUMNS, "twin_first", "twin_second"]],
            candidates=grid,
        ).summary

        self.assertTrue(summary["objectives_agree"])
        self.assertAlmostEqual(summary["margin_minus_rmse_selection_eur"], 0.0, places=9)
        self.assertIn("distinguishes nothing", summary["headline_note"])


class SelectionRefusalTests(unittest.TestCase):
    def test_overlapping_windows_are_refused(self) -> None:
        prices = shaped_prices(date(2026, 3, 1), 8)
        forecasts = divergent_forecasts(prices, date(2026, 3, 5))
        # Mark one evaluation day as validation, so the windows interleave.
        forecasts = forecasts.copy()
        forecasts.loc[forecasts["market_day"].eq(date(2026, 3, 6)), "split"] = "validation"

        with self.assertRaises(ValueSelectionInputError) as raised:
            compare_selection_objectives(
                prices, battery(), forecasts, candidates=DIVERGENT_GRID
            )

        self.assertIn("must precede", str(raised.exception))

    def test_a_missing_forecast_interval_is_refused_rather_than_excluded(self) -> None:
        prices = shaped_prices(date(2026, 3, 1), 8)
        forecasts = divergent_forecasts(prices, date(2026, 3, 5)).copy()
        forecasts.loc[0, "low_rmse_wrong_order"] = np.nan

        with self.assertRaises(ValueSelectionInputError) as raised:
            compare_selection_objectives(
                prices, battery(), forecasts, candidates=DIVERGENT_GRID
            )

        self.assertIn("different calendars", str(raised.exception))

    def test_one_candidate_is_not_a_choice(self) -> None:
        prices = shaped_prices(date(2026, 3, 1), 8)
        forecasts = divergent_forecasts(prices, date(2026, 3, 5))

        with self.assertRaises(SelectionCandidateError):
            compare_selection_objectives(
                prices,
                battery(),
                forecasts,
                candidates=(SelectionCandidate("low_rmse_wrong_order", "ridge"),),
            )

    def test_an_unknown_evidence_class_is_refused(self) -> None:
        prices = shaped_prices(date(2026, 3, 1), 8)
        forecasts = divergent_forecasts(prices, date(2026, 3, 5))

        with self.assertRaises(ValueSelectionInputError):
            compare_selection_objectives(
                prices,
                battery(),
                forecasts,
                candidates=DIVERGENT_GRID,
                evidence_class="confirmatory",
            )


class CandidateGridTests(unittest.TestCase):
    def test_a_candidate_may_not_move_the_schedule_the_seed_or_the_features(self) -> None:
        protected = (
            "validation_start_day",
            "test_start_day",
            "random_seed",
            "feature_window_days",
        )
        for field in protected:
            with self.subTest(field=field):
                with self.assertRaises(SelectionCandidateError):
                    SelectionCandidate("candidate", "ridge", {field: 1})

    def test_an_unknown_configuration_field_is_refused(self) -> None:
        with self.assertRaises(SelectionCandidateError):
            SelectionCandidate("candidate", "ridge", {"learning_rate": 0.1})

    def test_an_unsupported_model_family_is_refused(self) -> None:
        with self.assertRaises(SelectionCandidateError):
            SelectionCandidate("candidate", "random_forest")

    def test_duplicate_candidate_names_are_refused(self) -> None:
        prices = shaped_prices(date(2026, 3, 1), 8)
        forecasts = divergent_forecasts(prices, date(2026, 3, 5))

        with self.assertRaises(SelectionCandidateError):
            compare_selection_objectives(
                prices,
                battery(),
                forecasts,
                candidates=(
                    SelectionCandidate("low_rmse_wrong_order", "ridge"),
                    SelectionCandidate("low_rmse_wrong_order", "ridge"),
                ),
            )


class WalkForwardSelectionTests(unittest.TestCase):
    """The same comparison over genuinely fitted candidates rather than constructed columns."""

    def test_fitted_candidates_are_scored_selected_and_evaluated(self) -> None:
        prices = generate_synthetic_prices(date(2026, 1, 1), date(2026, 2, 20), seed=37)
        base = MLForecastConfig(
            validation_start_day=date(2026, 2, 1),
            test_start_day=date(2026, 2, 12),
            min_training_days=28,
            refit_frequency_days=3,
        )
        grid = (
            SelectionCandidate("ridge_alpha_1", "ridge", {"ridge_alpha": 1.0}),
            SelectionCandidate("ridge_alpha_100", "ridge", {"ridge_alpha": 100.0}),
        )

        forecasts = generate_candidate_forecasts(prices, base, grid)
        result = compare_selection_objectives(
            prices, battery(), forecasts, candidates=grid
        )

        self.assertEqual(set(forecasts["split"]), {"validation", "evaluation"})
        self.assertFalse(forecasts[[c.name for c in grid]].isna().any().any())
        self.assertEqual(len(result.validation_scoreboard), len(grid))
        self.assertEqual(len(result.evaluation_scoreboard), len(grid))
        # Every candidate faced one ceiling on each window, which is what makes the two
        # settled margins comparable at all.
        for board in (result.validation_scoreboard, result.evaluation_scoreboard):
            ceilings = board["perfect_foresight_margin_eur"].round(6).unique()
            self.assertEqual(len(ceilings), 1)
        self.assertIn(
            result.summary["selected_by_validation_rmse"], [c.name for c in grid]
        )
        self.assertIn(
            result.summary["selected_by_validation_settled_margin"],
            [c.name for c in grid],
        )

    def test_walk_forward_candidates_read_an_identical_feature_table(self) -> None:
        # Two candidates of the same family differing only in regularization must not produce
        # identical forecasts (they are different options) while still being scored on exactly
        # the same intervals.
        prices = generate_synthetic_prices(date(2026, 1, 1), date(2026, 2, 20), seed=37)
        base = MLForecastConfig(
            validation_start_day=date(2026, 2, 1),
            test_start_day=date(2026, 2, 12),
            min_training_days=28,
            refit_frequency_days=3,
        )
        grid = (
            SelectionCandidate("ridge_alpha_1", "ridge", {"ridge_alpha": 1.0}),
            SelectionCandidate("ridge_alpha_100", "ridge", {"ridge_alpha": 100.0}),
        )

        forecasts = generate_candidate_forecasts(prices, base, grid)

        self.assertFalse(
            np.allclose(
                forecasts["ridge_alpha_1"].to_numpy(dtype=float),
                forecasts["ridge_alpha_100"].to_numpy(dtype=float),
            )
        )
        self.assertEqual(len(forecasts), len(forecasts.drop_duplicates("delivery_start_utc")))


class SelectionCommandTests(unittest.TestCase):
    def test_the_command_writes_both_scoreboards_and_the_frozen_selection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prices_path = root / "prices.csv"
            with redirect_stdout(io.StringIO()):
                main(
                    [
                        "generate-synthetic",
                        "--start-day",
                        "2026-01-01",
                        "--end-day",
                        "2026-02-20",
                        "--output",
                        str(prices_path),
                    ]
                )
            battery_path = root / "battery.json"
            battery_path.write_text(
                json.dumps(
                    {
                        "charge_power_mw": 1.0,
                        "discharge_power_mw": 1.0,
                        "energy_capacity_mwh": 2.0,
                        "soc_min_fraction": 0.1,
                        "soc_max_fraction": 0.9,
                        "initial_soc_fraction": 0.5,
                        "terminal_soc_fraction": 0.5,
                    }
                ),
                encoding="utf-8",
            )
            output = root / "evaluation.csv"

            with redirect_stdout(io.StringIO()):
                exit_code = main(
                    [
                        "compare-selection-objectives",
                        str(prices_path),
                        "--battery",
                        str(battery_path),
                        "--validation-start-day",
                        "2026-02-01",
                        "--evaluation-start-day",
                        "2026-02-12",
                        "--refit-frequency-days",
                        "3",
                        "--output",
                        str(output),
                    ]
                )

            self.assertEqual(exit_code, 0)
            evaluation = pd.read_csv(output)
            validation = pd.read_csv(root / "evaluation_validation.csv")
            payload = json.loads((root / "evaluation_summary.json").read_text("utf-8"))

        self.assertEqual(len(evaluation), len(validation))
        self.assertIn("frozen_selection_sha256", payload["summary"])
        self.assertEqual(
            payload["summary"]["frozen_selection_sha256"],
            payload["frozen_selection"]["frozen_selection_sha256"],
        )
        self.assertIn("selections", payload["frozen_selection"])


if __name__ == "__main__":
    unittest.main()
