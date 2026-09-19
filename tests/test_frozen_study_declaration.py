"""The prospective experiment pins its implementation and isolates declared changes."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from greek_bess.study import read_integrated_study_config

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs/frozen_selection_run_declaration_2026-09-19.md"
SPEC = importlib.util.spec_from_file_location(
    "frozen_study_declaration", ROOT / "scripts/verify_frozen_study_declaration.py"
)
assert SPEC is not None and SPEC.loader is not None
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


def test_reviewed_declaration_and_configuration_pair():
    declared = GUARD.verify(ROOT, DOCUMENT, GUARD.digest(DOCUMENT))
    configs = [read_integrated_study_config(ROOT / p) for p in declared["study_configs"]]
    baseline, aged = configs
    original = json.loads((ROOT / "examples/battery_50mw_100mwh.json").read_text())
    for config in configs:
        assert config.battery.to_dict() == baseline.battery.to_dict()
        for key, value in original.items():
            assert config.battery.to_dict()[key] == value
        assert config.selection_evidence_index_sha256 == declared["selection_evidence_index_sha256"]
        assert str(config.window_start_day) == declared["study_first_day"]
        assert str(config.window_end_day) == declared["study_last_day"]
        assert len(config.window_days) == declared["study_day_count"]
        assert [s.planner for s in config.strategies] == list(declared["selected_candidates"])
    left, right = baseline.to_dict(), aged.to_dict()
    assert {k for k in left if left[k] != right[k]} == {"study_id", "degradation", "finance"}
    changed_fade = {
        k for k in left["degradation"] if left["degradation"][k] != right["degradation"][k]
    }
    assert changed_fade == {
        "calendar_fade_fraction_per_year", "cycle_fade_fraction_per_equivalent_cycle",
    }
    cost_fields = {
        "fixed_opex_eur_per_year", "insurance_eur_per_year", "asset_management_eur_per_year",
        "variable_opex_eur_per_mwh_discharged",
    }
    changed_costs = {k for k in left["finance"] if left["finance"][k] != right["finance"][k]}
    assert changed_costs == cost_fields | {"total_fixed_opex_eur_per_year"}
    assert all(left["finance"][k] == 0 for k in cost_fields)
    assert left["degradation"]["calendar_fade_fraction_per_year"] == 0
    assert left["degradation"]["cycle_fade_fraction_per_equivalent_cycle"] == 0


@pytest.fixture
def declared_fixture(tmp_path):
    package = tmp_path / "src" / "greek_bess"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("# Synthetic test module\n")
    (package / "py.typed").touch()
    config = tmp_path / "config.json"
    config.write_text('{"synthetic": true}\n')
    document = tmp_path / "declaration.md"
    payload = {
        "evidence_class": "retrospective_supplementary",
        "source_tree_sha256": GUARD.source_tree_digest(tmp_path),
        "input_sha256": {"config.json": GUARD.digest(config)},
    }
    document.write_text("```json\n" + json.dumps(payload) + "\n```\n")
    return tmp_path, document, GUARD.digest(document)


@pytest.mark.parametrize("mutation", ["config", "source", "added_module", "deleted_module"])
def test_declared_input_mutations_are_refused(declared_fixture, mutation):
    root, document, pin = declared_fixture
    assert GUARD.verify(root, document, pin)
    package = root / "src" / "greek_bess"
    if mutation == "config":
        (root / "config.json").write_text("{}")
    elif mutation == "source":
        (package / "__init__.py").write_text("# Changed synthetic module\n")
    elif mutation == "added_module":
        (package / "extra.py").touch()
    else:
        (package / "__init__.py").unlink()
    with pytest.raises(ValueError, match="changed"):
        GUARD.verify(root, document, pin)


def test_changed_document_is_refused(declared_fixture):
    root, document, pin = declared_fixture
    document.write_text(document.read_text() + "Changed protocol\n")
    with pytest.raises(ValueError, match="reviewed digest"):
        GUARD.verify(root, document, pin)


def test_input_outside_repository_is_refused(declared_fixture):
    root, document, _ = declared_fixture
    payload = json.loads(document.read_text().split("```json\n")[1].split("```")[0])
    payload["input_sha256"] = {"../outside": "0" * 64}
    document.write_text("```json\n" + json.dumps(payload) + "\n```\n")
    with pytest.raises(ValueError, match="inside the repository"):
        GUARD.verify(root, document, GUARD.digest(document))
