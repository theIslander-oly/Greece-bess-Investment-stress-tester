"""One-command, synthetic-only tour through the complete research pipeline."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import pandas as pd

from ..data.quality import assess_quality
from ..data.synthetic import generate_synthetic_prices
from ..dispatch import BatteryDispatchConfig, optimize_daily_perfect_foresight
from ..finance import FinanceConfig, evaluate_project_finance
from ..reporting import build_run_manifest, render_report, write_report, write_run_manifest
from ..stress import SpreadCompressionConfig, apply_spread_compression
from ._registry import Command

DEMO_RECORDED_AT_UTC = "2026-09-02T00:00:00+00:00"
SYNTHETIC_LABEL = (
    "Deterministic synthetic Greek DAM demonstration; not official market data, a forecast, "
    "expected revenue, investment evidence, financial advice or a bankable study."
)
SYNTHETIC_CEILING_LABEL = (
    "Perfect-foresight Greek DAM gross-margin upper bound on deterministic synthetic prices; "
    "not expected or forecast investment revenue and not investment evidence."
)


def configure_demo(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("demo-report.html"),
        help="Self-contained indexed HTML report (default: demo-report.html)",
    )


def _daily_results(schedule: pd.DataFrame) -> pd.DataFrame:
    return (
        schedule.groupby("market_day", sort=True, as_index=False)
        .agg(
            net_market_margin_eur=("net_market_margin_eur", "sum"),
            market_cash_margin_eur=("market_cash_margin_eur", "sum"),
            monetary_degradation_adder_eur=("degradation_cost_eur", "sum"),
            grid_discharge_mwh=("discharge_grid_mwh", "sum"),
        )
        .assign(augmentation_cost_eur=0.0)
    )


def run_demo(args: argparse.Namespace) -> int:
    """Run the deterministic public demonstration and write its verified-manifest report."""

    start_day = date(2025, 1, 1)
    end_day = date(2026, 1, 1)
    prices = generate_synthetic_prices(start_day, end_day, seed=42)
    prices["retrieved_at_utc"] = pd.Timestamp(DEMO_RECORDED_AT_UTC)
    quality = assess_quality(prices)
    if not quality.is_valid:
        raise ValueError("The built-in synthetic demo failed its data-quality gate")

    battery = BatteryDispatchConfig(
        charge_power_mw=50.0,
        discharge_power_mw=50.0,
        energy_capacity_mwh=100.0,
        soc_min_fraction=0.05,
        soc_max_fraction=0.95,
        initial_soc_fraction=0.5,
        terminal_soc_fraction=0.5,
        charge_efficiency=0.94,
        discharge_efficiency=0.94,
        grid_import_limit_mw=50.0,
        grid_export_limit_mw=50.0,
        max_daily_equivalent_cycles=1.5,
    )
    baseline = optimize_daily_perfect_foresight(prices, battery)

    paths = prices.copy()
    paths.insert(0, "path_id", 0)
    compression = apply_spread_compression(
        paths,
        SpreadCompressionConfig(
            compression_factor=0.7,
            reference_basis="daily_mean",
            transformation_id="demo-spreads-down-30-percent",
        ),
    )
    compressed_prices = compression.paths.drop(columns="path_id")
    stressed = optimize_daily_perfect_foresight(compressed_prices, battery)

    finance = evaluate_project_finance(
        _daily_results(stressed.schedule),
        FinanceConfig(
            project_start_day=start_day,
            project_end_day=date(2025, 12, 31),
            operating_margin_case="user_supplied_scenario",
            discount_rate_fraction=0.08,
            battery_system_capex_eur=30_000_000.0,
            power_conversion_system_capex_eur=8_000_000.0,
            grid_connection_capex_eur=5_000_000.0,
            development_and_construction_capex_eur=4_000_000.0,
            other_initial_capex_eur=3_000_000.0,
            market_margin_realization_fraction=0.65,
            fixed_opex_eur_per_year=600_000.0,
            insurance_eur_per_year=150_000.0,
            asset_management_eur_per_year=100_000.0,
            variable_opex_eur_per_mwh_discharged=0.5,
            decommissioning_cost_eur=1_000_000.0,
            residual_value_eur=2_000_000.0,
        ),
    )

    quality_summary = {
        "result_label": SYNTHETIC_LABEL,
        "interval_count": len(prices),
        "market_day_count": 365,
        "quality_gate_passed": True,
        "seed": 42,
        "resolution_minutes": 60,
    }
    baseline_summary = {**baseline.summary, "result_label": SYNTHETIC_CEILING_LABEL}
    stressed_summary = {**stressed.summary, "result_label": SYNTHETIC_CEILING_LABEL}
    finance_summary = {
        **finance.summary,
        "result_label": (
            f"{finance.summary['result_label']} The supplied operating path is a deterministic "
            "synthetic spread-compression scenario and is not investment evidence."
        ),
    }
    summaries = (
        ("synthetic-input", "synthetic_price_series", "generate-synthetic", quality_summary),
        (
            "synthetic-ceiling",
            "synthetic_perfect_foresight_dispatch",
            "optimize-perfect-foresight --daily-solves",
            baseline_summary,
        ),
        ("spread-compression", "spread_compression", "compress-spread", compression.summary),
        (
            "compressed-synthetic-ceiling",
            "synthetic_perfect_foresight_dispatch",
            "optimize-perfect-foresight --daily-solves",
            stressed_summary,
        ),
        (
            "synthetic-finance-screen",
            "project_finance",
            "evaluate-project-finance",
            finance_summary,
        ),
    )
    manifest_dir = args.output.parent / f".{args.output.stem}-manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_paths: list[Path] = []
    for manifest_id, kind, produced_by, summary in summaries:
        manifest = build_run_manifest(
            summary,
            kind_id=kind,
            manifest_id=f"demo-{manifest_id}",
            produced_by=produced_by,
            declared_inputs={"data_basis": "deterministic synthetic public demonstration"},
            created_at_utc=DEMO_RECORDED_AT_UTC,
        )
        path = manifest_dir / f"{manifest_id}.json"
        write_run_manifest(path, manifest)
        manifest_paths.append(path)

    rendered = render_report(manifest_paths, rendered_at_utc=DEMO_RECORDED_AT_UTC)
    index_path = write_report(rendered, args.output)
    for path in manifest_paths:
        path.unlink()
    manifest_dir.rmdir()
    index_path.unlink()
    print(
        json.dumps(
            {
                "report": str(args.output),
                "data_basis": "deterministic synthetic public demonstration",
                "manifest_count": len(manifest_paths),
                "result_label": SYNTHETIC_LABEL,
            },
            indent=2,
        )
    )
    return 0


COMMANDS = (
    Command(
        name="demo",
        help="Run the complete synthetic-only workflow and render one indexed report",
        configure=configure_demo,
        run=run_demo,
    ),
)
