"""Text-level refusal and ordering contract for the private official workflow."""
from pathlib import Path

WORKFLOW = Path('.github/workflows/benchmark-fundamentals.yml')


def test_workflow_is_manual_private_and_fixes_every_operator_declaration() -> None:
    text = WORKFLOW.read_text()
    for required in (
        'workflow_dispatch:', 'decision_lead_minutes.txt)" = "0"',
        'dswrf_surface temperature_2m wind_speed_10m',
        '--validation-start-day 2024-10-01', '--test-start-day 2025-10-01',
        '--price-regime-bands 0 50 100 200',
        'examples/battery_50mw_100mwh.json',
        'witnessed provider_declared', 'retention-days: 90',
        'accepted_feature_set_sha256', 'acceptance_document_sha256',
    ):
        assert required in text
    assert 'battery_representative_gr_25mw_100mwh.json' not in text
    assert 'permissions:\n  contents: read\n  actions: read' in text


def test_acceptance_and_custody_precede_every_benchmark() -> None:
    text = WORKFLOW.read_text()
    custody = text.index('Verify price-history and feature-table custody')
    audit = text.index('Re-run availability acceptance audit')
    forecast = text.index('Run fixed forecast benchmark')
    dispatch = text.index('Run fixed settled dispatch comparison')
    assert custody < audit < forecast < dispatch
    assert text.index("assert s['feature_set_sha256']") < forecast


def test_summary_contains_labels_and_no_investment_figures() -> None:
    text = WORKFLOW.read_text().split('Write artifact index and interpretation labels only', 1)[1]
    assert 'gross-margin upper bound only' in text
    assert 'not expected revenue' in text
    for forbidden in ('incremental_realized_margin_eur', 'perfect_foresight_margin_eur', 'EUR'):
        assert forbidden not in text


def test_feature_custody_parameterizes_both_existing_paths() -> None:
    for path in (Path('.github/workflows/record-artifact-custody.yml'),
                 Path('.github/workflows/publish-encrypted-custody.yml')):
        text = path.read_text()
        assert 'feature_run_id:' in text
        assert '.github/scripts/custody_step.sh accepted-fundamentals-feature-table' in text
