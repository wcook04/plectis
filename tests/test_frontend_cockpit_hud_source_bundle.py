from __future__ import annotations

import hashlib
import json
from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MICROCOSM_ROOT.parent
MANIFEST_PATH = (
    MICROCOSM_ROOT
    / "examples/macro_projection_import_protocol/exported_projection_import_bundle/frontend_cockpit_source_bundle_manifest.json"
)
PROTOCOL_PATH = (
    MICROCOSM_ROOT
    / "examples/macro_projection_import_protocol/exported_projection_import_bundle/frontend_cockpit_source_projection_protocol.json"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_path(ref: str) -> Path:
    return REPO_ROOT / ref


def _microcosm_path(ref: str) -> Path:
    return MICROCOSM_ROOT / ref


def test_frontend_cockpit_source_modules_are_exact_macro_imports() -> None:
    manifest = _load_json(MANIFEST_PATH)

    assert manifest["schema_version"] == "public_microcosm_source_module_manifest_v1"
    assert manifest["manifest_id"] == "frontend_cockpit_hud_source_modules_import"
    assert manifest["classification"] == "copied_non_secret_macro_body"
    assert manifest["module_count"] == 6
    assert manifest["total_line_count"] > 2000
    assert manifest["body_storage_policy"].startswith("exact_non_secret_frontend_cockpit_source_modules")
    assert manifest["receipt_body_policy"] == "target_body_text_is_never_embedded_in_receipts"

    module_ids = {row["module_id"] for row in manifest["modules"]}
    assert module_ids == {
        "attention_queue_source_body_import",
        "raw_trace_drawer_source_body_import",
        "session_inspector_panel_source_body_import",
        "station_surface_registry_source_body_import",
        "station_top_bar_source_body_import",
        "workstream_board_source_body_import",
    }

    forbidden_fragments = (
        "/Users/",
        "src/ai_workflow",
        "file://",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GITHUB_TOKEN",
    )

    for module in manifest["modules"]:
        source_path = _repo_path(module["source_ref"])
        target_path = _repo_path(module["target_ref"])

        assert source_path.is_file(), module["source_ref"]
        assert target_path.is_file(), module["target_ref"]
        assert source_path.read_bytes() == target_path.read_bytes()
        assert module["body_copied"] is True
        assert module["body_in_receipt"] is False
        assert module["sha256_match"] is True
        assert module["missing_required_anchors"] == []
        assert module["source_sha256"] == _sha256(source_path)
        assert module["target_sha256"] == _sha256(target_path)
        assert module["source_sha256"] == module["target_sha256"]
        assert module["line_count"] == len(source_path.read_text(encoding="utf-8").splitlines())

        target_text = target_path.read_text(encoding="utf-8")
        for anchor in module["required_anchors"]:
            assert anchor in target_text
        for forbidden in forbidden_fragments:
            assert forbidden not in target_text


def test_frontend_cockpit_source_projection_protocol_preserves_import_membrane() -> None:
    manifest = _load_json(MANIFEST_PATH)
    protocol = _load_json(PROTOCOL_PATH)

    assert protocol["schema_version"] == "macro_projection_import_protocol_v1"
    assert protocol["protocol_id"] == "frontend_cockpit_hud_source_projection_import"
    assert protocol["parent_protocol_ref"] == (
        "examples/macro_projection_import_protocol/exported_projection_import_bundle/projection_protocol.json"
    )
    assert protocol["source_module_manifest_ref"] == (
        "examples/macro_projection_import_protocol/exported_projection_import_bundle/frontend_cockpit_source_bundle_manifest.json"
    )
    assert protocol["body_in_receipt"] is False

    assert all(value is False for value in protocol["authority_ceiling"].values())
    assert "metadata-only" in protocol["claim"]
    assert "exact public-safe source capsules" in protocol["claim"]

    omission_ids = {row["omission_id"] for row in protocol["omission_receipts"]}
    assert omission_ids == {
        "live_operator_browser_state_excluded",
        "private_paths_excluded",
        "provider_payloads_excluded",
        "raw_operator_voice_excluded",
    }

    manifest_rows = {row["module_id"]: row for row in manifest["modules"]}
    copied_rows = {row["material_id"]: row for row in protocol["copied_material"]}
    assert copied_rows.keys() == manifest_rows.keys()

    for material_id, copied in copied_rows.items():
        manifest_row = manifest_rows[material_id]
        verification = copied["body_import_verification"]
        target_path = _microcosm_path(copied["target_ref"])

        assert target_path.is_file(), copied["target_ref"]
        assert copied["body_copied"] is True
        assert copied["body_in_receipt"] is False
        assert copied["material_class"] == "public_macro_frontend_body"
        assert copied["public_safe_mode"] == "direct_verified_macro_frontend_body"
        assert copied["body_digest"] == f"sha256:{manifest_row['target_sha256']}"
        assert verification["verification_mode"] == "exact_source_digest_match"
        assert verification["verification_status"] == "verified"
        assert verification["source_to_target_relation"] == "exact_copy"
        assert verification["source_body_digest"] == f"sha256:{manifest_row['source_sha256']}"
        assert verification["target_body_digest"] == f"sha256:{manifest_row['target_sha256']}"
        assert verification["source_line_count"] == manifest_row["line_count"]
        assert verification["target_line_count"] == manifest_row["line_count"]
