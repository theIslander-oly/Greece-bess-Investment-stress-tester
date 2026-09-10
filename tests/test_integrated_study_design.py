"""The integrated study design's [Verified] claims still hold against the code.

A design document is a decision, and a decision made against facts that have since changed is
worse than no decision at all. Every claim the design labels [Verified] names something in this
repository, so each one is checkable — and these tests fail when the code moves out from under
the design rather than when someone remembers to re-read it.

They deliberately assert the *substance* of each claim rather than the wording of the sentence
that carries it: the design is prose and will be edited, while the contracts it depends on are
not supposed to move without a recorded decision.
"""

from __future__ import annotations

import re
import unittest
from datetime import date
from pathlib import Path

from greek_bess.backtest.degradation_dispatch import DEGRADED_DISPATCH_LABEL
from greek_bess.degradation import DegradationConfig
from greek_bess.dispatch import BatteryDispatchConfig
from greek_bess.finance.model import FinanceConfig
from greek_bess.reporting.contract import RESULT_BASES

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "docs" / "integrated_study_design.md"


class IntegratedStudyDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # The document is wrapped prose, so a phrase that reads as one sentence may be split
        # across lines. Collapsing whitespace lets these tests assert the claim rather than the
        # column the claim happened to wrap at.
        cls.text = re.sub(r"\s+", " ", DESIGN.read_text(encoding="utf-8"))

    def test_the_design_of_record_exists_and_states_what_it_does_not_do(self) -> None:
        self.assertIn("design of record for the integrated study runner", self.text)
        # A design unit that quietly authorized a run would defeat the point of separating it
        # from the implementation.
        self.assertIn("does not authorize an official-data run", self.text)
        self.assertIn("adds no source code", self.text)

    def test_the_basis_the_design_selects_exists(self) -> None:
        # Section 5.6 puts the study on the simulation basis added in stage 5. If that basis
        # were removed or renamed, the design would name a basis the contract cannot record.
        self.assertIn("historical_replay_simulation", self.text)
        self.assertIn("historical_replay_simulation", RESULT_BASES)

    def test_the_monetary_adder_the_design_names_is_a_real_field(self) -> None:
        # Section 5.3 distinguishes the dispatch-objective adder from physical fade. Both must
        # exist and remain distinct, or the double-counting rule describes nothing.
        battery = BatteryDispatchConfig(
            charge_power_mw=1.0, discharge_power_mw=1.0, energy_capacity_mwh=1.0
        )
        self.assertTrue(hasattr(battery, "degradation_cost_eur_per_mwh_discharged"))
        self.assertIn("degradation_cost_eur_per_mwh_discharged", self.text)

        degradation = DegradationConfig(
            project_start_day=date(2026, 1, 1),
            calendar_fade_fraction_per_year=0.0,
            cycle_fade_fraction_per_equivalent_cycle=0.0,
        )
        self.assertTrue(hasattr(degradation, "calendar_fade_fraction_per_year"))
        self.assertTrue(hasattr(degradation, "cycle_fade_fraction_per_equivalent_cycle"))

    def test_the_terminal_soc_rule_the_design_relies_on_is_enforced(self) -> None:
        # Section 5.4 says both existing backtests already require it, and the study inherits
        # the rule rather than restating it.
        battery = BatteryDispatchConfig(
            charge_power_mw=1.0, discharge_power_mw=1.0, energy_capacity_mwh=1.0
        )
        self.assertTrue(hasattr(battery, "effective_terminal_soc_fraction"))

    def test_the_finance_input_columns_the_design_emits_are_the_required_ones(self) -> None:
        # Section 4.5 names the columns a study day emits. They must be the columns the finance
        # model actually requires, or the composition does not connect.
        for column in ("market_day", "net_market_margin_eur", "grid_discharge_mwh"):
            self.assertIn(column, self.text)
        self.assertTrue(hasattr(FinanceConfig, "__dataclass_fields__"))

    def test_the_design_refuses_gaps_rather_than_filling_them(self) -> None:
        # The single constraint the design calls most important. Stated here so that softening
        # it in the document is a visible test change rather than an edit.
        self.assertIn("Gaps are refused, never bridged", self.text)
        self.assertIn("no forecast is imputed", self.text)

    def test_the_design_does_not_assert_a_shared_ceiling(self) -> None:
        # Section 5.2 follows from the stage 5 finding. The degraded label must still say the
        # aggregate is not a bound, or the reasoning the design cites has been reversed.
        self.assertIn("no single perfect-foresight ceiling", self.text)
        self.assertIn("not a lifetime optimum or an upper bound", DEGRADED_DISPATCH_LABEL.lower())

    def test_the_design_records_how_it_could_be_wrong(self) -> None:
        self.assertIn("What could make this design wrong", self.text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
