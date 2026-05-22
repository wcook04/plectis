from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.macro_projection_import_protocol import (
    EXPECTED_NEGATIVE_CASES,
    preview_import_plan,
    run,
    run_projection_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/macro_projection_import_protocol/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
)


def _walk_keys(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        keys = list(payload)
        for value in payload.values():
            keys.extend(_walk_keys(value))
        return keys
    if isinstance(payload, list):
        keys: list[str] = []
        for item in payload:
            keys.extend(_walk_keys(item))
        return keys
    return []


def test_macro_projection_import_protocol_observes_negative_cases(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/macro_projection_import_protocol",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/macro_projection_import_protocol_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["projection_cell_count"] == 3
    assert result["ready_projection_cell_count"] == 3
    assert result["blocked_projection_cell_count"] == 0
    assert result["source_ref_count"] >= 2
    assert result["public_replacement_ref_count"] >= 2
    assert result["validation_ref_count"] >= 2
    assert result["authority_ceiling"]["private_source_bodies_exported"] is False
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["projection_board"]["next_best_lane"] == "real_substrate_import_tranche"
    assert result["projection_board"]["intake_board_ref"] == "projection_import_intake_board.json"
    assert result["projection_intake_board"]["ready_cell_count"] == 3
    assert result["projection_intake_board"]["blocked_cell_count"] == 0
    assert result["projection_intake_board"]["open_actionable_cell_count"] == 0
    assert result["projection_intake_board"]["landed_cell_count"] == 3
    assert result["projection_intake_board"]["projection_status_counts"] == {
        "public_replacement_landed": 1,
        "runtime_bridge_landed": 1,
        "self_hosted_status_protocol_landed": 1,
    }
    assert result["projection_intake_board"]["omitted_material_count"] == 2
    assert result["projection_intake_board"]["negative_case_coverage_status"] == "pass"
    assert (
        result["projection_intake_board"]["projection_status_protocol"]["status_field"]
        == "projection_status"
    )
    assert all(
        row["copy_policy"] == "metadata_fixture_receipt_ref_only"
        for row in result["projection_intake_board"]["projection_cells"]
    )
    by_cell = {
        row["cell_id"]: row for row in result["projection_intake_board"]["projection_cells"]
    }
    assert by_cell["projection_protocol_self_host"]["projection_status"] == (
        "self_hosted_status_protocol_landed"
    )
    assert by_cell["projection_protocol_self_host"]["action_required"] is False
    assert by_cell["runtime_reveal_import_bridge"]["projection_status"] == "runtime_bridge_landed"
    assert any(
        receipt_ref.endswith("projection_import_intake_board.json")
        for receipt_ref in result["receipt_paths"]
    )


def test_macro_projection_import_protocol_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/macro_projection_import_protocol",
        public_root / "fixtures/first_wave/macro_projection_import_protocol",
    )

    result = run(
        public_root / "fixtures/first_wave/macro_projection_import_protocol/input",
        public_root / "receipts/first_wave/macro_projection_import_protocol",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["private_state_scan"]["body_redacted"] is True
        assert payload["private_state_scan"]["blocking_hit_count"] == 0
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_macro_projection_exported_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_projection_bundle(
        BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_projection_import_bundle"
    assert result["bundle_id"] == "macro_projection_import_protocol_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["projection_cell_count"] == 3
    assert result["projection_intake_board"]["ready_cell_count"] == 3
    assert result["projection_intake_board"]["open_actionable_cell_count"] == 0
    assert result["projection_board"]["release_authorized"] is False
    assert result["projection_board"]["private_data_equivalence_claim"] is False


def test_macro_projection_import_plan_preview_is_non_writing() -> None:
    result = preview_import_plan(BUNDLE_INPUT, command="pytest")

    assert result["status"] == "pass"
    assert result["schema_version"] == "macro_projection_import_intake_preview_v1"
    assert result["input_mode"] == "exported_projection_import_bundle"
    assert result["projection_intake_board"]["ready_cell_count"] == 3
    assert result["projection_intake_board"]["blocked_cell_count"] == 0
    assert result["projection_intake_board"]["projection_status_counts"][
        "self_hosted_status_protocol_landed"
    ] == 1
    assert result["projection_intake_board"]["open_actionable_cell_count"] == 0
    assert result["projection_intake_board"]["release_authorized"] is False
    assert "pattern_metadata" in result["projection_intake_board"]["allowed_material_classes"]
    assert all(
        row["selected_pattern_ids"]
        for row in result["projection_intake_board"]["projection_cells"]
    )
    assert "receipt_paths" not in result
