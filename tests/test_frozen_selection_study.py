"""Accepted frozen forecasts retain their identity when coupled to ageing and finance."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import date

import numpy as np
import pandas as pd
import pytest

from greek_bess.backtest.ml_dispatch import _backtest_precomputed_forecast
from greek_bess.cli import main
from greek_bess.data.synthetic import generate_synthetic_prices
from greek_bess.degradation import DegradationConfig
from greek_bess.dispatch import BatteryDispatchConfig
from greek_bess.finance import FinanceConfig
from greek_bess.reporting import read_run_manifest
from greek_bess.selection import SelectionCandidate, compare_selection_objectives
from greek_bess.study import (
    IntegratedStudyConfig,
    IntegratedStudyInputError,
    StrategySpec,
    assemble_integrated_study,
    run_integrated_study,
)


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def bundle(tmp_path, request):
    # Include the 25-hour day. Forecasts are declared clock functions, not realized prices.
    prices = generate_synthetic_prices(
        date(2025, 10, 23),
        date(2025, 10, 28),
        resolution_minutes=getattr(request, "param", 60),
        seed=7,
    )
    prices["price_eur_per_mwh"] = np.where(prices.delivery_start_market.dt.hour < 12, -10.0, 100.0)
    prices.loc[prices.delivery_start_market.dt.hour.eq(12), "price_eur_per_mwh"] = 0.0
    forecasts = prices[
        ["delivery_start_utc", "delivery_start_market", "duration_hours", "source"]
    ].copy()
    forecasts["market_day"] = prices.delivery_start_market.dt.date
    forecasts["actual_price_eur_per_mwh"] = prices.price_eur_per_mwh
    forecasts["split"] = np.where(
        forecasts.market_day < date(2025, 10, 25), "validation", "evaluation"
    )
    forecasts["flat"] = 35.0
    forecasts["shape"] = np.where(prices.delivery_start_market.dt.hour < 12, -100.0, 200.0)
    candidates = (
        SelectionCandidate("flat", "ridge"),
        SelectionCandidate("shape", "hist_gradient_boosting"),
    )
    battery = BatteryDispatchConfig(
        charge_power_mw=1,
        discharge_power_mw=1,
        energy_capacity_mwh=2,
        initial_soc_fraction=0.5,
        terminal_soc_fraction=0.5,
    )
    selected = compare_selection_objectives(prices, battery, forecasts, candidates=candidates)
    assert selected.summary["selected_by_validation_rmse"] == "flat"
    assert selected.summary["selected_by_validation_settled_margin"] == "shape"
    forecasts.to_csv(tmp_path / "forecasts.csv", index=False)
    payload = {"summary": selected.summary, "frozen_selection": selected.frozen_selection}
    (tmp_path / "selection.summary.json").write_text(json.dumps(payload), encoding="utf-8")
    index = {
        "evidence_class": "retrospective_supplementary",
        "workflow_run_id": "synthetic-test",
        "source_commit": "synthetic-fixture",
        "frozen_selection_sha256": selected.summary["frozen_selection_sha256"],
        "candidate_forecast_sha256": selected.summary["candidate_forecast_sha256"],
        "files_sha256": {
            name: _hash(tmp_path / name) for name in ("forecasts.csv", "selection.summary.json")
        },
    }
    (tmp_path / "evidence_index.json").write_text(json.dumps(index), encoding="utf-8")
    config = IntegratedStudyConfig(
        study_id="frozen-fixture",
        window_start_day=date(2025, 10, 25),
        window_end_day=date(2025, 10, 27),
        price_source="synthetic",
        strategies=(
            StrategySpec("rmse", "frozen_validation_rmse", "accepted_frozen_causal_forecasts"),
            StrategySpec("margin", "frozen_validation_margin", "accepted_frozen_causal_forecasts"),
        ),
        battery=battery,
        degradation=DegradationConfig(date(2025, 10, 25), 0, 0),
        finance=FinanceConfig(
            project_start_day=date(2025, 10, 25),
            project_end_day=date(2025, 10, 27),
            operating_margin_case="historical_forecast_backtest",
            discount_rate_fraction=0.08,
            battery_system_capex_eur=1000,
        ),
        result_label="Synthetic regression only; not investment evidence.",
        selection_evidence_index_sha256=_hash(tmp_path / "evidence_index.json"),
    )
    return prices, forecasts, config, tmp_path


def _run(bundle):
    prices, _, config, root = bundle
    return assemble_integrated_study(
        run_integrated_study(prices, config, selection_evidence_dir=root)
    )


def _reseal(root, config):
    index = json.loads((root / "evidence_index.json").read_text())
    for name in index["files_sha256"]:
        index["files_sha256"][name] = _hash(root / name)
    (root / "evidence_index.json").write_text(json.dumps(index), encoding="utf-8")
    return replace(config, selection_evidence_index_sha256=_hash(root / "evidence_index.json"))


def test_zero_fade_reproduces_original_selected_columns_and_dst(bundle):
    prices, forecasts, config, _ = bundle
    result = _run(bundle)
    for strategy, candidate in [("rmse", "flat"), ("margin", "shape")]:
        original = _backtest_precomputed_forecast(
            prices, config.battery, forecasts[forecasts.split == "evaluation"], method=candidate
        )
        actual = result.daily_results.loc[result.daily_results.strategy_id.eq(strategy)]
        assert list(actual.interval_count) == [24, 25, 24]
        np.testing.assert_allclose(
            actual.market_cash_margin_eur,
            original.daily_results.market_cash_margin_eur,
            atol=1e-6,
            rtol=0,
        )
        np.testing.assert_allclose(
            actual.grid_discharge_mwh, original.daily_results.grid_discharge_mwh, atol=1e-6, rtol=0
        )
        np.testing.assert_allclose(
            actual.grid_charge_mwh, original.daily_results.grid_charge_mwh, atol=1e-6, rtol=0
        )
    assert (
        result.summary["selection_replay"]["selected_candidates"]["frozen_validation_rmse"]
        == "flat"
    )
    recorded = result.summary["selection_comparison"]
    rows = result.strategy_summaries.set_index("strategy_id")
    assert recorded["difference_market_cash_margin_eur"] == (
        rows.loc["margin", "market_cash_margin_eur"] - rows.loc["rmse", "market_cash_margin_eur"]
    )


def test_separate_ageing_and_order_invariance(bundle):
    prices, forecasts, config, root = bundle
    config = replace(
        config,
        degradation=replace(config.degradation, cycle_fade_fraction_per_equivalent_cycle=0.01),
    )
    first = _run((prices, forecasts, config, root))
    second = _run((prices, forecasts, replace(config, strategies=config.strategies[::-1]), root))
    capacities = first.strategy_summaries.set_index("strategy_id").final_usable_energy_mwh
    assert capacities["margin"] < capacities["rmse"]
    pd.testing.assert_frame_equal(
        first.strategy_summaries.sort_values("strategy_id").reset_index(drop=True),
        second.strategy_summaries.sort_values("strategy_id").reset_index(drop=True),
    )


def test_requires_both_planners_and_evidence(bundle):
    prices, _, config, _ = bundle
    with pytest.raises(IntegratedStudyInputError, match="Both frozen"):
        replace(config, strategies=config.strategies[:1])
    with pytest.raises(IntegratedStudyInputError, match="exactly once"):
        duplicate = replace(config.strategies[0], strategy_id="duplicate")
        replace(config, strategies=(*config.strategies, duplicate))
    with pytest.raises(IntegratedStudyInputError, match="selection_evidence"):
        replace(config, selection_evidence_index_sha256=None)
    with pytest.raises(IntegratedStudyInputError, match="evidence"):
        run_integrated_study(prices, config)


def test_rejects_changed_bytes_and_pin(bundle):
    prices, forecasts, config, root = bundle
    with pytest.raises(IntegratedStudyInputError, match="digest"):
        _run((prices, forecasts, replace(config, selection_evidence_index_sha256="0" * 64), root))
    with (root / "forecasts.csv").open("a") as stream:
        stream.write("\n")
    with pytest.raises(IntegratedStudyInputError, match="digest"):
        _run(bundle)


@pytest.mark.parametrize(
    "fault", ["duplicate", "missing", "actual", "date", "duration", "infinite"]
)
def test_rejects_inconsistent_tables_even_with_updated_file_pins(bundle, fault):
    prices, forecasts, config, root = bundle
    forecasts = forecasts.copy()
    if fault == "duplicate":
        forecasts = pd.concat([forecasts, forecasts.iloc[[-1]]])
    elif fault == "missing":
        forecasts = forecasts.iloc[:-1]
    elif fault == "actual":
        forecasts.loc[forecasts.index[-1], "actual_price_eur_per_mwh"] += 1
    elif fault == "date":
        forecasts.loc[forecasts.index[-1], "market_day"] = date(2025, 10, 26)
    elif fault == "duration":
        forecasts.loc[forecasts.index[-1], "duration_hours"] = 0.25
    else:
        forecasts.loc[forecasts.index[-1], "shape"] = np.inf
    forecasts.to_csv(root / "forecasts.csv", index=False)
    config = _reseal(root, config)
    with pytest.raises(IntegratedStudyInputError):
        _run((prices, forecasts, config, root))


def test_rejects_broken_frozen_seal(bundle):
    prices, forecasts, config, root = bundle
    path = root / "selection.summary.json"
    payload = json.loads(path.read_text())
    payload["frozen_selection"]["selections"]["validation_rmse"]["selected_candidate"] = "shape"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(IntegratedStudyInputError, match="seal"):
        _run((prices, forecasts, _reseal(root, config), root))


def test_rejects_different_evaluation_window(bundle):
    prices, forecasts, config, root = bundle
    config = replace(
        config,
        window_end_day=date(2025, 10, 26),
        finance=replace(config.finance, project_end_day=date(2025, 10, 26)),
    )
    with pytest.raises(IntegratedStudyInputError, match="window"):
        _run((prices, forecasts, config, root))


def test_later_realized_prices_cannot_change_earlier_path(bundle):
    prices, forecasts, config, root = bundle
    baseline = _run(bundle)
    prices, forecasts = prices.copy(), forecasts.copy()
    later = forecasts.market_day == date(2025, 10, 27)
    forecasts.loc[later, "actual_price_eur_per_mwh"] += 1000
    prices.loc[later, "price_eur_per_mwh"] += 1000
    forecasts.to_csv(root / "forecasts.csv", index=False)
    changed = _run((prices, forecasts, _reseal(root, config), root))
    earlier = baseline.daily_results.market_day < date(2025, 10, 27)
    pd.testing.assert_frame_equal(baseline.daily_results[earlier], changed.daily_results[earlier])
    assert (
        baseline.summary["selection_replay"]["frozen_selection_sha256"]
        == changed.summary["selection_replay"]["frozen_selection_sha256"]
    )


def test_cli_records_provenance_and_renders(bundle, tmp_path):
    prices, _, config, root = bundle
    # Input format excludes output-only configuration keys, as existing study examples do.
    payload = config.to_dict()
    payload.pop("window_day_count")
    for strategy in payload["strategies"]:
        strategy.pop("operating_margin_case")
    payload["finance"].pop("total_initial_capex_eur")
    payload["finance"].pop("total_fixed_opex_eur_per_year")
    config_path = tmp_path / "study.json"
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    export = prices.copy()
    export["quality_flags"] = export.quality_flags.map(json.dumps)
    export.to_csv(tmp_path / "input.csv", index=False)
    code = main(
        [
            "run-integrated-study",
            str(tmp_path / "input.csv"),
            "--study-config",
            str(config_path),
            "--selection-evidence-dir",
            str(root),
            "--output-dir",
            str(tmp_path / "output"),
            "--report",
            str(tmp_path / "report.html"),
        ]
    )
    assert code == 0
    manifest = read_run_manifest(tmp_path / "output/frozen-fixture.manifest.json")
    assert manifest.declared_inputs["selection_replay"] == manifest.summary["selection_replay"]
    assert "frozen_validation_rmse" in (tmp_path / "report.html").read_text(encoding="utf-8")


@pytest.mark.parametrize("bundle", [15], indirect=True)
def test_quarter_hour_dst_coverage_and_utc_row_order(bundle):
    prices, forecasts, config, root = bundle
    baseline = _run(bundle)
    forecasts.iloc[::-1].to_csv(root / "forecasts.csv", index=False)
    reordered = _run((prices, forecasts, _reseal(root, config), root))
    for strategy in ("rmse", "margin"):
        assert list(
            baseline.daily_results.loc[
                baseline.daily_results.strategy_id.eq(strategy), "interval_count"
            ]
        ) == [96, 100, 96]
    pd.testing.assert_frame_equal(baseline.daily_results, reordered.daily_results)


def test_refuses_paths_outside_evidence_directory(bundle):
    prices, forecasts, config, root = bundle
    index_path = root / "evidence_index.json"
    index = json.loads(index_path.read_text())
    index["files_sha256"]["../outside.csv"] = "0" * 64
    index_path.write_text(json.dumps(index), encoding="utf-8")
    config = replace(config, selection_evidence_index_sha256=_hash(index_path))
    with pytest.raises(IntegratedStudyInputError, match="escapes"):
        _run((prices, forecasts, config, root))


def test_rejects_naive_time_keys_and_promoted_evidence(bundle):
    prices, forecasts, config, root = bundle
    index_path = root / "evidence_index.json"
    index = json.loads(index_path.read_text())
    index["evidence_class"] = "predeclared_untouched"
    index_path.write_text(json.dumps(index), encoding="utf-8")
    changed = replace(config, selection_evidence_index_sha256=_hash(index_path))
    with pytest.raises(IntegratedStudyInputError, match="retrospective"):
        _run((prices, forecasts, changed, root))
    index["evidence_class"] = "retrospective_supplementary"
    index_path.write_text(json.dumps(index), encoding="utf-8")
    forecasts["delivery_start_utc"] = forecasts.delivery_start_utc.dt.tz_localize(None)
    forecasts.to_csv(root / "forecasts.csv", index=False)
    with pytest.raises(IntegratedStudyInputError, match="timezone-aware"):
        _run((prices, forecasts, _reseal(root, config), root))


@pytest.mark.parametrize("ending,label", [("\n", "LF"), ("\r\n", "CRLF")])
def test_legacy_semantic_digest_preserves_producer_line_ending(bundle, ending, label):
    from greek_bess.study.frozen_selection import read_frozen_selection

    prices, forecasts, config, root = bundle
    payload_path = root / "selection.summary.json"
    payload = json.loads(payload_path.read_text())
    columns = ["delivery_start_utc", "split", "flat", "shape"]
    digest = hashlib.sha256(
        forecasts[columns]
        .sort_values("delivery_start_utc")
        .to_csv(index=False, float_format="%.10f", lineterminator=ending)
        .encode()
    ).hexdigest()
    payload["summary"]["candidate_forecast_sha256"] = digest
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    index_path = root / "evidence_index.json"
    index = json.loads(index_path.read_text())
    index["candidate_forecast_sha256"] = digest
    index_path.write_text(json.dumps(index), encoding="utf-8")
    table, provenance = read_frozen_selection(root, prices, _reseal(root, config))
    assert provenance["candidate_digest_line_ending"] == label
    np.testing.assert_array_equal(
        table.frozen_validation_margin, forecasts.loc[forecasts.split.eq("evaluation"), "shape"]
    )
