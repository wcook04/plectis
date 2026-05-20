from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.navigation_hologram_route_plane import (
    EXPECTED_NEGATIVE_CASES,
    EXPECTED_RECEIPT_PATHS,
    run,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
NAV_FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/navigation_hologram_route_plane/input"
PER_OUTPUT_RECEIPT_FIELD_FLOOR = {
    "receipts/preflight/navigation_hologram_route_plane.json": [
        "schema_version",
        "organ_id",
        "fixture_id",
        "validator_id",
        "command",
        "status",
        "source_coupling_baseline_status",
        "banned_route_table_status",
        "route_lease_precheck_status",
        "blocked_dependency_codes",
        "anti_claim",
        "private_state_scan",
        "authority_ceiling",
        "receipt_paths",
    ],
    "receipts/first_wave/navigation_hologram_route_plane/source_coupling_result.json": [
        "schema_version",
        "organ_id",
        "fixture_id",
        "validator_id",
        "command",
        "status",
        "expected_negative_cases",
        "observed_negative_cases",
        "expected_sha256",
        "observed_sha256",
        "source_coupling_status",
        "authority_allowed",
        "error_codes",
        "anti_claim",
        "private_state_scan",
        "authority_ceiling",
        "receipt_paths",
    ],
    "receipts/first_wave/navigation_hologram_route_plane/route_lease.json": [
        "schema_version",
        "organ_id",
        "fixture_id",
        "validator_id",
        "command",
        "status",
        "lease_id",
        "selected_lane_id",
        "banned_route_replacements",
        "route_lease_ref",
        "invalidation_inputs",
        "permitted_direct_actions",
        "duplicate_route_ids",
        "expected_negative_cases",
        "observed_negative_cases",
        "error_codes",
        "anti_claim",
        "private_state_scan",
        "authority_ceiling",
        "receipt_paths",
    ],
    "receipts/first_wave/navigation_hologram_route_plane/entry_payload_admission_receipt.json": [
        "schema_version",
        "organ_id",
        "fixture_id",
        "validator_id",
        "command",
        "status",
        "entry_payload_admission_status",
        "inline_target_bytes",
        "before_bytes",
        "after_bytes",
        "saved_bytes",
        "preserved_non_negotiable_fields",
        "dropped_control_fields",
        "omission_receipts",
        "expected_negative_cases",
        "observed_negative_cases",
        "error_codes",
        "anti_claim",
        "private_state_scan",
        "authority_ceiling",
        "receipt_paths",
    ],
    "receipts/first_wave/navigation_hologram_route_plane/affordance_passport_selection_receipt.json": [
        "schema_version",
        "organ_id",
        "fixture_id",
        "validator_id",
        "command",
        "status",
        "affordance_compatibility",
        "anti_trigger_hits",
        "demotion_receipt",
        "selection_decision",
        "expected_negative_cases",
        "observed_negative_cases",
        "error_codes",
        "anti_claim",
        "private_state_scan",
        "authority_ceiling",
        "receipt_paths",
        "selected_row_id",
        "passport_coverage",
        "demoted_rows",
        "safe_drilldown",
        "validator_asserted_feeds_patterns",
    ],
    "receipts/first_wave/navigation_hologram_route_plane/code_architecture_projection_packet_receipt.json": [
        "schema_version",
        "organ_id",
        "fixture_id",
        "validator_id",
        "command",
        "status",
        "packet_producer_id",
        "source_fingerprint",
        "omission_receipt",
        "known_limits",
        "renderer_schema_match_status",
        "reverse_bfs_depth_buckets",
        "suggested_verification",
        "body_redacted",
        "expected_negative_cases",
        "observed_negative_cases",
        "error_codes",
        "anti_claim",
        "private_state_scan",
        "authority_ceiling",
        "receipt_paths",
    ],
}


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


def test_navigation_hologram_route_plane_observes_required_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(NAV_FIXTURE_INPUT, tmp_path / "receipts", command="pytest")

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["selected_row_ids"] == ["toy_route_card"]
    assert result["source_coupling_status"] == "stale"
    assert result["authority_allowed"] is False
    assert result["duplicate_route_ids"] == ["duplicate_route"]
    assert result["entry_payload_admission"]["dropped_control_fields"] == [
        "banned_routes",
        "route_lease.permitted_direct_actions",
        "ceremony_budget.required_proof",
        "surface_contract",
        "navigation_index_spine.currentness",
        "navigation_index_spine.source_coupling",
        "navigation_index_spine.omission_receipt",
    ]
    assert result["affordance_passport_selection"]["selected_row_id"] == "route_card_candidate"
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_navigation_hologram_route_plane_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/navigation_hologram_route_plane",
        public_root / "fixtures/first_wave/navigation_hologram_route_plane",
    )

    result = run(
        public_root / "fixtures/first_wave/navigation_hologram_route_plane/input",
        public_root / "receipts/first_wave/navigation_hologram_route_plane",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == EXPECTED_RECEIPT_PATHS
    for receipt_path in EXPECTED_RECEIPT_PATHS:
        receipt_file = public_root / receipt_path
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "/Users/willcook" not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["private_state_scan"]["body_redacted"] is True
        assert payload["missing_negative_cases"] == []
        assert set(payload["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)
        for hit in payload["private_state_scan"]["hits"]:
            assert hit["body_redacted"] is True
            assert not Path(hit["path"]).is_absolute()


def test_navigation_hologram_route_plane_receipts_satisfy_macro_field_floor(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/navigation_hologram_route_plane",
        public_root / "fixtures/first_wave/navigation_hologram_route_plane",
    )
    run(
        public_root / "fixtures/first_wave/navigation_hologram_route_plane/input",
        public_root / "receipts/first_wave/navigation_hologram_route_plane",
        command="pytest",
    )

    for receipt_path, required_fields in PER_OUTPUT_RECEIPT_FIELD_FLOOR.items():
        payload = json.loads((public_root / receipt_path).read_text(encoding="utf-8"))
        missing = [field for field in required_fields if field not in payload]
        assert missing == []

    route_lease = json.loads(
        (
            public_root
            / "receipts/first_wave/navigation_hologram_route_plane/route_lease.json"
        ).read_text(encoding="utf-8")
    )
    assert route_lease["banned_route_replacements"][0]["replacement_route"] == "entry_packet"
    assert route_lease["authority_ceiling"]["route_lease_source_authority_rejected"] is True
