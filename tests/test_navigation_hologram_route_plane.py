from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs import navigation_hologram_route_plane as route_plane
from microcosm_core.organs.navigation_hologram_route_plane import (
    EXPORTED_ROUTE_PLANE_BUNDLE_RECEIPT_PATH,
    EXPECTED_NEGATIVE_CASES,
    EXPECTED_RECEIPT_PATHS,
    result_card,
    run,
    run_route_plane_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
MACRO_ROOT = MICROCOSM_ROOT.parent
NAV_FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/navigation_hologram_route_plane/input"
NAV_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/navigation_hologram_route_plane/exported_route_plane_bundle"
)
SOURCE_MODULE_MANIFEST = NAV_BUNDLE_INPUT / "source_module_manifest.json"
PAPER_MODULE = MICROCOSM_ROOT / "paper_modules/navigation_hologram_route_plane.md"
ORGAN_REGISTRY = MICROCOSM_ROOT / "core/organ_registry.json"
ORGAN_ATLAS = MICROCOSM_ROOT / "core/organ_atlas.json"
ORGAN_STANDARD = MICROCOSM_ROOT / "standards/std_microcosm_navigation_hologram_route_plane.json"
FIXTURE_MANIFEST = (
    MICROCOSM_ROOT
    / "core/fixture_manifests/navigation_hologram_route_plane.fixture_manifest.json"
)
ROUTE_PLANE_SOURCE_MODULE_IDS = [
    "navigation_route_plane_intervention_source_body_import",
    "navigation_route_plane_context_pack_source_body_import",
    "navigation_route_plane_entry_packet_source_body_import",
    "navigation_route_plane_option_surface_source_body_import",
    "navigation_route_plane_navigation_contract_source_body_import",
]
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


def _navigation_organ_registry_row() -> dict[str, Any]:
    registry = json.loads(ORGAN_REGISTRY.read_text(encoding="utf-8"))
    return next(
        row
        for row in registry["implemented_organs"]
        if row["organ_id"] == "navigation_hologram_route_plane"
    )


def _navigation_organ_atlas_row() -> dict[str, Any]:
    atlas = json.loads(ORGAN_ATLAS.read_text(encoding="utf-8"))
    return next(
        row
        for row in atlas["organs"]
        if row["organ_id"] == "navigation_hologram_route_plane"
    )


def test_navigation_hologram_route_plane_observes_required_negative_cases(
    tmp_path: Path,
) -> None:
    live_preflight = MICROCOSM_ROOT / "receipts/preflight/navigation_hologram_route_plane.json"
    live_preflight_before = (
        live_preflight.read_text(encoding="utf-8") if live_preflight.exists() else None
    )
    result = run(NAV_FIXTURE_INPUT, tmp_path / "receipts", command="pytest")

    assert result["status"] == "pass"
    assert all(not Path(path).is_absolute() for path in result["receipt_paths"])
    card = result_card(result)
    assert card["input_mode"] == "fixture_regression"
    assert card["real_lane_witness"] == {
        "current_input_is_exported_bundle_witness": False,
        "witness_action": "run-route-plane-bundle",
        "witness_input_ref": "examples/navigation_hologram_route_plane/exported_route_plane_bundle",
        "source_body_imports_required_for_witness": True,
        "current_source_module_manifest_status": "not_present",
        "current_source_module_digest_status": "not_present",
        "current_source_module_anchor_status": "not_present",
        "current_source_module_count": 0,
    }
    assert (tmp_path / "receipts/preflight/navigation_hologram_route_plane.json").is_file()
    live_preflight_after = (
        live_preflight.read_text(encoding="utf-8") if live_preflight.exists() else None
    )
    assert live_preflight_after == live_preflight_before
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
        assert "/Users/example" not in text
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


def test_navigation_hologram_route_plane_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_route_plane_bundle(
        NAV_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/navigation_hologram_route_plane",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_route_plane_bundle"
    assert result["bundle_id"] == "public_navigation_hologram_route_plane_runtime_example"
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["source_coupling_status"] == "pass"
    assert result["authority_allowed"] is False
    assert result["authority_ceiling"]["atlas_projection_control_entry_rejected"] is True
    assert result["route_rows_projection_not_authority"] is True
    assert result["body_material_status"] == (
        "copied_non_secret_macro_route_substrate_with_provenance"
    )
    assert result["source_module_manifest_status"] == "pass"
    assert result["source_module_digest_status"] == "pass"
    assert result["source_module_anchor_status"] == "pass"
    assert result["source_module_count"] == len(ROUTE_PLANE_SOURCE_MODULE_IDS)
    card = result_card(result)
    assert card["input_mode"] == "exported_route_plane_bundle"
    assert card["real_lane_witness"] == {
        "current_input_is_exported_bundle_witness": True,
        "witness_action": "run-route-plane-bundle",
        "witness_input_ref": "examples/navigation_hologram_route_plane/exported_route_plane_bundle",
        "source_body_imports_required_for_witness": True,
        "current_source_module_manifest_status": "pass",
        "current_source_module_digest_status": "pass",
        "current_source_module_anchor_status": "pass",
        "current_source_module_count": len(ROUTE_PLANE_SOURCE_MODULE_IDS),
    }
    assert [
        row["module_id"] for row in result["source_module_results"]
    ] == ROUTE_PLANE_SOURCE_MODULE_IDS
    assert all(row["sha256_match"] for row in result["source_module_results"])
    assert all(row["anchor_status"] == "pass" for row in result["source_module_results"])
    assert result["route_row_count"] == 41
    assert result["selected_row_ids"] == ["entry_control_packet"]
    assert result["route_lease"]["selected_lane_id"] == "public_runtime_option_surface"
    assert result["route_lease"]["authority_allowed"] is False
    assert result["entry_payload_admission"]["dropped_control_fields"] == []
    assert result["card"]["band_payload"]["route_command"].startswith(
        "./repo-python kernel.py --entry"
    )
    assert (
        result["affordance_passport_selection"]["selected_row_id"]
        == "route_card_candidate"
    )
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert "private_state_scan" not in result
    assert all(not Path(path).is_absolute() for path in result["real_substrate_refs"])
    assert any(
        path.endswith("source_modules/system/lib/navigation_context_pack.py")
        for path in result["real_substrate_refs"]
    )


def test_navigation_hologram_route_plane_rejects_commandless_route_rows() -> None:
    rows_payload = json.loads((NAV_BUNDLE_INPUT / "route_rows.json").read_text(encoding="utf-8"))
    contract = json.loads(
        (NAV_BUNDLE_INPUT / "option_surface_contract.json").read_text(encoding="utf-8")
    )
    row = rows_payload["rows"][0]
    row.pop("route_command", None)
    row["band_payloads"]["card"].pop("route_command", None)

    result = route_plane.validate_exported_route_rows(rows_payload, contract)

    assert result["status"] == "blocked"
    assert "ROUTE_PLANE_BUNDLE_ROUTE_COMMAND_MISSING" in {
        finding["error_code"] for finding in result["findings"]
    }


def test_navigation_hologram_route_plane_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/navigation_hologram_route_plane",
        public_root / "examples/navigation_hologram_route_plane",
    )
    bundle = (
        public_root
        / "examples/navigation_hologram_route_plane/exported_route_plane_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["target_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_route_plane_bundle(
        bundle,
        public_root / "receipts/first_wave/navigation_hologram_route_plane",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert result["source_module_digest_status"] == "blocked"
    assert "ROUTE_PLANE_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_navigation_hologram_route_plane_rejects_mutated_copied_source_body(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/navigation_hologram_route_plane",
        public_root / "examples/navigation_hologram_route_plane",
    )
    bundle = (
        public_root
        / "examples/navigation_hologram_route_plane/exported_route_plane_bundle"
    )
    manifest = json.loads((bundle / "source_module_manifest.json").read_text(encoding="utf-8"))
    target_ref = manifest["modules"][0]["target_ref"]
    target = public_root / target_ref
    target.write_text(
        f"{target.read_text(encoding='utf-8')}\n# mutated copied source body\n",
        encoding="utf-8",
    )

    result = run_route_plane_bundle(
        bundle,
        public_root / "receipts/first_wave/navigation_hologram_route_plane",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert result["source_module_digest_status"] == "blocked"
    assert result["source_module_anchor_status"] == "pass"
    assert "ROUTE_PLANE_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_module_results"][0]["sha256_match"] is False


def test_navigation_hologram_route_plane_rejects_missing_source_import_boundary(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/navigation_hologram_route_plane",
        public_root / "examples/navigation_hologram_route_plane",
    )
    bundle = (
        public_root
        / "examples/navigation_hologram_route_plane/exported_route_plane_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0].pop("source_import_class", None)
    manifest["modules"][0].pop("body_text_in_receipt", None)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_route_plane_bundle(
        bundle,
        public_root / "receipts/first_wave/navigation_hologram_route_plane",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "ROUTE_PLANE_SOURCE_MODULE_IMPORT_BOUNDARY_INVALID" in result["error_codes"]


def test_navigation_hologram_route_plane_source_manifest_matches_exact_macro_sources() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))
    modules = manifest["modules"]

    assert manifest["classification"] == "copied_non_secret_macro_body"
    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_text_in_receipt"] is False
    assert manifest["module_count"] == len(ROUTE_PLANE_SOURCE_MODULE_IDS)
    assert [module["module_id"] for module in modules] == ROUTE_PLANE_SOURCE_MODULE_IDS
    for module in modules:
        source = MACRO_ROOT / module["source_ref"]
        target = MICROCOSM_ROOT / module["target_ref"]
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        target_text = target.read_text(encoding="utf-8")

        assert source.is_file()
        assert target.is_file()
        assert target.read_bytes() == source.read_bytes()
        assert module["source_sha256"] == digest
        assert module["target_sha256"] == digest
        assert module["sha256_match"] is True
        assert module["body_copied"] is True
        assert module["body_in_receipt"] is False
        assert module["source_import_class"] == "copied_non_secret_macro_body"
        assert module["body_text_in_receipt"] is False
        for anchor in module["required_anchors"]:
            assert anchor in target_text


def test_navigation_hologram_route_plane_fixture_manifest_counts_source_open_body_floor() -> None:
    fixture_manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "core/fixture_manifests/navigation_hologram_route_plane.fixture_manifest.json"
        ).read_text(encoding="utf-8")
    )
    source_manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))
    body_imports = fixture_manifest["source_open_body_imports"]

    assert fixture_manifest["body_copied_material_count"] == len(ROUTE_PLANE_SOURCE_MODULE_IDS)
    assert body_imports["status"] == "pass"
    assert body_imports["body_material_count"] == len(ROUTE_PLANE_SOURCE_MODULE_IDS)
    assert body_imports["body_in_receipt"] is False
    assert body_imports["body_text_exported_in_workingness"] is False
    assert body_imports["aggregate_floor_ref"] == (
        "examples/navigation_hologram_route_plane/exported_route_plane_bundle/"
        "source_module_manifest.json::modules"
    )
    assert body_imports["body_material_ids"] == [
        module["module_id"] for module in source_manifest["modules"]
    ] == ROUTE_PLANE_SOURCE_MODULE_IDS


def test_navigation_hologram_route_plane_exported_bundle_receipt_is_public_safe(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/navigation_hologram_route_plane",
        public_root / "examples/navigation_hologram_route_plane",
    )

    result = run_route_plane_bundle(
        public_root / "examples/navigation_hologram_route_plane/exported_route_plane_bundle",
        public_root / "receipts/first_wave/navigation_hologram_route_plane",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == [EXPORTED_ROUTE_PLANE_BUNDLE_RECEIPT_PATH]
    receipt_file = public_root / EXPORTED_ROUTE_PLANE_BUNDLE_RECEIPT_PATH
    assert receipt_file.is_file()
    text = receipt_file.read_text(encoding="utf-8")
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "/Users/example" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    payload = json.loads(text)
    assert payload["status"] == "pass"
    assert payload["input_mode"] == "exported_route_plane_bundle"
    assert payload["fixture_regression_required_elsewhere"] is True
    assert payload["body_material_status"] == (
        "copied_non_secret_macro_route_substrate_with_provenance"
    )
    assert payload["source_module_manifest_status"] == "pass"
    assert payload["source_module_count"] == len(ROUTE_PLANE_SOURCE_MODULE_IDS)
    assert [
        row["module_id"] for row in payload["source_module_results"]
    ] == ROUTE_PLANE_SOURCE_MODULE_IDS
    assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
    assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert "private_state_scan" not in payload
    assert "public_replacement_refs" not in payload
    assert payload["expected_negative_cases"] == {}
    assert payload["route_rows_projection_not_authority"] is True
    assert payload["authority_allowed"] is False
    assert "matched_excerpt" not in _walk_keys(payload)
    assert "body" not in _walk_keys(payload)
    for hit in payload["secret_exclusion_scan"]["hits"]:
        assert hit["body_in_receipt"] is False
        assert not Path(hit["path"]).is_absolute()


def test_navigation_hologram_route_plane_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    out_dir = tmp_path / "receipts/first_wave/navigation_hologram_route_plane"
    result = run_route_plane_bundle(
        NAV_BUNDLE_INPUT,
        out_dir,
        command="pytest --card",
        reuse_fresh_receipt=True,
    )
    assert result["status"] == "pass"
    assert result["receipt_reused"] is False

    def fail_if_rebuilt(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(route_plane, "validate_exported_route_rows", fail_if_rebuilt)

    cached = run_route_plane_bundle(
        NAV_BUNDLE_INPUT,
        out_dir,
        command="pytest --card",
        reuse_fresh_receipt=True,
    )
    card = result_card(cached)

    assert cached["receipt_reused"] is True
    assert card["receipt_reused"] is True
    assert card["real_lane_witness"]["current_input_is_exported_bundle_witness"] is True
    assert card["real_lane_witness"]["current_source_module_digest_status"] == "pass"
    assert card["route_row_count"] == 41
    assert card["source_module_count"] == len(ROUTE_PLANE_SOURCE_MODULE_IDS)
    assert card["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert "route_rows" not in json.dumps(card, sort_keys=True)


def test_navigation_hologram_route_plane_paper_module_carries_source_backed_packet() -> None:
    module = PAPER_MODULE.read_text(encoding="utf-8")
    organ = _navigation_organ_registry_row()
    atlas = _navigation_organ_atlas_row()
    standard = json.loads(ORGAN_STANDARD.read_text(encoding="utf-8"))
    fixture_manifest = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    source_manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    required_strings = [
        "## Source-Backed Doctrine Packet",
        "## Re-entry Conditions",
        "core/organ_registry.json::implemented_organs[navigation_hologram_route_plane]",
        "core/organ_atlas.json::organs[navigation_hologram_route_plane]",
        "standards/std_microcosm_navigation_hologram_route_plane.json",
        "src/microcosm_core/organs/navigation_hologram_route_plane.py",
        "core/fixture_manifests/navigation_hologram_route_plane.fixture_manifest.json",
        "examples/navigation_hologram_route_plane/exported_route_plane_bundle/source_module_manifest.json",
        "tests/test_navigation_hologram_route_plane.py",
        organ["evidence_class"],
        organ["claim_ceiling"],
        organ["validator_command"],
        standard["authority_boundary"],
        standard["validator_contract"]["runtime_bundle_command"],
        fixture_manifest["body_material_status"],
        "body_in_receipt=false",
        atlas["claim_ceiling_restated"],
    ]
    missing = [value for value in required_strings if value not in module]
    assert missing == []

    for receipt_path in organ["generated_receipts"]:
        assert receipt_path in module

    for module_row in source_manifest["modules"]:
        assert module_row["module_id"] in module
        assert module_row["source_ref"] in module
        assert module_row["target_ref"] in module

    for code in fixture_manifest["stable_error_codes"]:
        assert code in module

    for phrase in [
        "does not prove live route freshness",
        "grant live macro-kernel authority",
        "authorize source mutation",
        "authorize provider calls",
        "export account/session state",
        "browser/HUD live access",
        "authorize publication or release",
        "whole-system correctness",
        "private-root equivalence",
    ]:
        assert phrase in module
