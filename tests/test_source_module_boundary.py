from __future__ import annotations

import json

from microcosm_core.validators.source_module_boundary import (
    BLOCKED,
    PASS,
    evaluate_source_module_boundary,
    extract_source_ref_rows,
    main,
)


def test_boundary_passes_public_relative_source_module_refs() -> None:
    manifest = {
        "schema_version": "microcosm_source_module_manifest_v1",
        "modules": [
            {
                "module_id": "public_synthetic_runtime",
                "source_ref": "public_examples/synthetic_runtime.py",
                "target_ref": (
                    "microcosm-substrate/examples/demo/source_modules/"
                    "public_examples/synthetic_runtime.py"
                ),
                "path": "source_modules/public_examples/synthetic_runtime.py",
                "validation_refs": [
                    "microcosm-substrate/tests/test_demo.py::test_source_copy"
                ],
            },
            {
                "module_id": "raw_seed_public_tools",
                "source_ref": "public_examples/raw_seed_keyphrase.py",
                "target_ref": "source_modules/public_examples/raw_seed_keyphrase.py",
            },
        ],
    }

    card = evaluate_source_module_boundary([("fixture_manifest.json", manifest)])

    assert card["status"] == PASS
    assert card["blocked_ref_count"] == 0
    assert card["safe_ref_count"] == 6
    assert card["input_manifest_refs"] == ["fixture_manifest.json"]
    assert "source-open by default" in card["boundary_policy"]


def test_boundary_blocks_restricted_private_control_plane_refs() -> None:
    card = evaluate_source_module_boundary(
        direct_refs=[
            "tools/meta/factory/work_ledger.py",
            "system/lib/work_ledger.py",
            (
                "microcosm-substrate/examples/demo/source_modules/"
                "tools/meta/factory/work_ledger.py"
            ),
            "kernel.py",
        ]
    )

    assert card["status"] == BLOCKED
    assert card["blocked_ref_count"] == 4
    error_codes = {row["error_code"] for row in card["blocked_refs"]}
    assert (
        "source_ref_restricted_private_control_plane:tools/meta/"
        in error_codes
    )
    assert (
        "source_ref_restricted_private_control_plane:system/lib/"
        in error_codes
    )
    assert "source_ref_restricted_private_control_plane:kernel.py" in error_codes


def test_boundary_blocks_private_provider_session_and_raw_seed_refs() -> None:
    card = evaluate_source_module_boundary(
        direct_refs=[
            "/" + "Users" + "/willcook/.env",
            "raw_seed/raw_seed.md",
            "state/provider_payloads/run_1/request.json",
            "browser/session_cookies.json",
            "operator_chrome_hud/session.json",
            "../state/secrets/token.json",
        ]
    )

    assert card["status"] == BLOCKED
    assert card["blocked_ref_count"] == 6
    error_codes = {row["error_code"] for row in card["blocked_refs"]}
    assert "source_ref_absolute_or_home_private_root" in error_codes
    assert "source_ref_raw_operator_voice" in error_codes
    assert "source_ref_forbidden_component:provider_payloads" in error_codes
    assert "source_ref_forbidden_component:session_cookies" in error_codes
    assert "source_ref_forbidden_component:operator_chrome_hud" in error_codes
    assert "source_ref_parent_traversal" in error_codes
    assert card["next_action"] == "exclude_blocked_source_refs_before_exact_copy_refresh_write"
    assert "does not certify secret absence" in card["anti_claim"]


def test_boundary_extracts_nested_manifest_source_refs_without_policy_prose() -> None:
    payload = {
        "source_open_payload_boundary": "provider payloads and session material omitted",
        "groups": [
            {
                "material_id": "kernel_route",
                "source_refs": [
                    "kernel.py",
                    "system/lib/navigation.py",
                ],
                "source_artifact_refs": {
                    "public_state": "state/microcosm_portfolio/extracted_patterns_ledger.jsonl",
                    "blocked_state": "state/private_prover_lab/oracle_receipt.json",
                },
            }
        ],
    }

    rows = extract_source_ref_rows(payload, manifest_ref="nested.json")
    card = evaluate_source_module_boundary([("nested.json", payload)])

    assert [row["ref"] for row in rows] == [
        "kernel.py",
        "system/lib/navigation.py",
        "state/microcosm_portfolio/extracted_patterns_ledger.jsonl",
        "state/private_prover_lab/oracle_receipt.json",
    ]
    assert card["status"] == BLOCKED
    assert card["blocked_refs"][0]["row_id"] == "kernel_route"
    assert (
        card["blocked_refs"][0]["error_code"]
        == "source_ref_forbidden_component:private_prover_lab"
    )


def test_boundary_blocks_source_module_body_in_receipt_claim() -> None:
    manifest = {
        "schema_version": "microcosm_source_module_manifest_v1",
        "modules": [
            {
                "module_id": "receipt_body_liar",
                "source_ref": "public_examples/navigation_context_pack.py",
                "target_ref": (
                    "source_modules/public_examples/navigation_context_pack.py"
                ),
                "source_to_target_relation": "exact_copy",
                "body_copied": True,
                "body_in_receipt": True,
            }
        ],
    }

    card = evaluate_source_module_boundary([("source_module_manifest.json", manifest)])

    assert card["status"] == BLOCKED
    assert card["blocked_ref_count"] == 1
    assert card["blocked_source_module_claim_count"] == 1
    assert card["blocked_refs"][0]["row_id"] == "receipt_body_liar"
    assert (
        card["blocked_refs"][0]["error_code"]
        == "source_module_body_in_receipt_claim"
    )
    assert (
        card["blocked_refs"][0]["coordination_action"]
        == "move_body_to_source_module_target_and_keep_receipt_body_false"
    )


def test_boundary_blocks_copied_body_claim_without_target_ref() -> None:
    manifest = {
        "schema_version": "microcosm_source_module_manifest_v1",
        "modules": [
            {
                "module_id": "targetless_copy_claim",
                "source_ref": "public_examples/synthetic_runtime.py",
                "source_to_target_relation": "exact_copy",
                "body_copied": True,
                "body_in_receipt": False,
            }
        ],
    }

    card = evaluate_source_module_boundary([("source_module_manifest.json", manifest)])

    assert card["status"] == BLOCKED
    assert card["blocked_ref_count"] == 1
    assert card["safe_ref_count"] == 1
    assert card["blocked_source_module_claim_count"] == 1
    assert card["blocked_refs"][0]["row_id"] == "targetless_copy_claim"
    assert (
        card["blocked_refs"][0]["error_code"]
        == "source_module_target_ref_missing"
    )
    assert (
        card["blocked_refs"][0]["coordination_action"]
        == "add_public_source_module_target_or_demote_body_claim"
    )


def test_boundary_blocks_source_module_path_target_ref_mismatch() -> None:
    manifest = {
        "schema_version": "microcosm_source_module_manifest_v1",
        "modules": [
            {
                "module_id": "drifted_source_module_target",
                "source_ref": "public_examples/navigation_context_pack.py",
                "target_ref": (
                    "microcosm-substrate/examples/demo/source_modules/"
                    "public_examples/navigation_context_pack.py"
                ),
                "path": "source_modules/public_examples/wrong_target.py",
                "source_to_target_relation": "exact_copy",
                "body_copied": True,
                "body_in_receipt": False,
            }
        ],
    }

    card = evaluate_source_module_boundary([("source_module_manifest.json", manifest)])

    assert card["status"] == BLOCKED
    assert card["blocked_ref_count"] == 1
    assert card["blocked_source_module_claim_count"] == 1
    finding = card["blocked_refs"][0]
    assert finding["row_id"] == "drifted_source_module_target"
    assert finding["error_code"] == "source_module_path_target_ref_mismatch"
    assert finding["path_tail"] == "public_examples/wrong_target.py"
    assert finding["target_tail"] == "public_examples/navigation_context_pack.py"
    assert (
        finding["coordination_action"]
        == "align_path_and_target_ref_to_same_source_modules_body"
    )


def test_boundary_keeps_distinct_structural_findings_for_same_row() -> None:
    manifest = {
        "schema_version": "microcosm_source_module_manifest_v1",
        "modules": [
            {
                "module_id": "receipt_body_targetless_claim",
                "source_ref": "public_examples/navigation_context_pack.py",
                "source_to_target_relation": "exact_copy",
                "body_copied": True,
                "body_in_receipt": True,
            }
        ],
    }

    card = evaluate_source_module_boundary([("source_module_manifest.json", manifest)])

    assert card["status"] == BLOCKED
    assert card["blocked_ref_count"] == 2
    assert card["blocked_source_module_claim_count"] == 2
    error_codes = {row["error_code"] for row in card["blocked_refs"]}
    assert error_codes == {
        "source_module_body_in_receipt_claim",
        "source_module_target_ref_missing",
    }


def test_cli_check_returns_nonzero_for_blocked_manifest(tmp_path, capsys) -> None:
    manifest_path = tmp_path / "source_module_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "modules": [
                    {
                        "module_id": "provider_payload_negative",
                        "source_ref": "state/provider_payloads/run_1/response.json",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    code = main(["--manifest", str(manifest_path), "--check"])

    assert code == 1
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == BLOCKED
    assert output["blocked_refs"][0]["manifest_ref"] == str(manifest_path)
    assert (
        output["blocked_refs"][0]["coordination_action"]
        == "exclude_ref_or_replace_with_public_non_secret_source_module"
    )
