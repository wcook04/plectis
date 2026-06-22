from __future__ import annotations

import json

from microcosm_core.validators.source_module_boundary import (
    BLOCKED,
    EXACT_COPY_SOURCE_MODULE_REFRESH_OPERATION,
    PASS,
    compile_source_module_refresh_policy,
    evaluate_source_module_boundary,
    evaluate_source_module_refresh_authority,
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
    # Uses a non-authorized tools/meta ref for the prefix check: the previous
    # example (tools/meta/factory/work_ledger.py) is now an operator-authorized
    # public exemption, covered by the dedicated test below.
    card = evaluate_source_module_boundary(
        direct_refs=[
            "tools/meta/factory/overnight_orchestrator.py",
            "system/lib/work_ledger.py",
            (
                "microcosm-substrate/examples/demo/source_modules/"
                "tools/meta/factory/overnight_orchestrator.py"
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


def test_refresh_authority_preserves_restricted_classification_for_granted_refs() -> None:
    card = evaluate_source_module_boundary(
        direct_refs=[
            "tools/meta/control/scoped_commit.py",
            "tools/meta/factory/work_ledger.py",
        ]
    )

    assert card["status"] == BLOCKED
    assert card["blocked_ref_count"] == 2
    assert {
        row["error_code"] for row in card["blocked_refs"]
    } == {
        "source_ref_restricted_private_control_plane:tools/meta/",
    }

    policy = {
        "schema_version": "source_module_refresh_policy_v0",
        "policy_id": "test_refresh_policy",
        "policy_revision": "test_policy_rev",
        "operation": EXACT_COPY_SOURCE_MODULE_REFRESH_OPERATION,
        "grants": [
            {
                "grant_id": "scoped_commit_refresh_grant",
                "status": "active",
                "operation": EXACT_COPY_SOURCE_MODULE_REFRESH_OPERATION,
                "source_ref": "tools/meta/control/scoped_commit.py",
                "target_refs": [
                    "examples/proof_bundle/source_modules/ai_workflow/tools/meta/control/scoped_commit.py"
                ],
                "source_to_target_relation": "exact_copy",
                "material_ids": ["scoped_commit_private_index_control_body_import"],
            }
        ],
    }
    authority = evaluate_source_module_refresh_authority(
        [
            {
                "material_id": "scoped_commit_private_index_control_body_import",
                "source_ref": "tools/meta/control/scoped_commit.py",
                "target_ref": (
                    "microcosm-substrate/examples/proof_bundle/source_modules/"
                    "ai_workflow/tools/meta/control/scoped_commit.py"
                ),
                "source_to_target_relation": "exact_copy",
                "source_sha256": "sha256:source",
                "target_sha256": "sha256:target",
            }
        ],
        policy=policy,
    )

    assert authority["status"] == PASS
    assert authority["allow_with_authority_count"] == 1
    decision = authority["decisions"][0]
    assert decision["classification_status"] == "restricted_private_control_plane"
    assert decision["classification_retained"] is True
    assert decision["authorization_status"] == "allow_with_authority"
    assert decision["grant_id"] == "scoped_commit_refresh_grant"


def test_refresh_authority_blocks_release_only_or_wrong_target_grants() -> None:
    release_only_policy = {
        "schema_version": "source_module_refresh_policy_v0",
        "policy_id": "test_release_only_policy",
        "policy_revision": "test_policy_rev",
        "operation": "release_reconstructability",
        "grants": [
            {
                "grant_id": "release_publicity_not_refresh_permission",
                "status": "active",
                "operation": "release_reconstructability",
                "source_ref": "tools/meta/control/scoped_commit.py",
                "target_refs": ["examples/proof_bundle/source_modules/scoped_commit.py"],
                "source_to_target_relation": "exact_copy",
                "material_ids": ["scoped_commit_private_index_control_body_import"],
            }
        ],
    }
    row = {
        "material_id": "scoped_commit_private_index_control_body_import",
        "source_ref": "tools/meta/control/scoped_commit.py",
        "target_ref": "examples/proof_bundle/source_modules/scoped_commit.py",
        "source_to_target_relation": "exact_copy",
    }

    release_only = evaluate_source_module_refresh_authority(
        [row],
        policy=release_only_policy,
    )

    assert release_only["status"] == BLOCKED
    assert release_only["policy_validation"]["status"] == BLOCKED
    assert release_only["blocked_decisions"][0]["authorization_status"] == (
        "blocked_invalid_refresh_policy"
    )

    wrong_target_policy = {
        **release_only_policy,
        "operation": EXACT_COPY_SOURCE_MODULE_REFRESH_OPERATION,
        "grants": [
            {
                **release_only_policy["grants"][0],
                "operation": EXACT_COPY_SOURCE_MODULE_REFRESH_OPERATION,
                "target_refs": ["examples/other_bundle/source_modules/scoped_commit.py"],
            }
        ],
    }
    wrong_target = evaluate_source_module_refresh_authority(
        [row],
        policy=wrong_target_policy,
    )

    assert wrong_target["status"] == BLOCKED
    assert wrong_target["blocked_decision_count"] == 1
    assert wrong_target["blocked_decisions"][0]["authorization_status"] == (
        "blocked_missing_refresh_grant"
    )


def test_refresh_authority_empty_policy_is_not_live_policy_fallback() -> None:
    authority = evaluate_source_module_refresh_authority(
        [
            {
                "material_id": "scoped_commit_private_index_control_body_import",
                "source_ref": "tools/meta/control/scoped_commit.py",
                "target_ref": "examples/proof_bundle/source_modules/scoped_commit.py",
                "source_to_target_relation": "exact_copy",
            }
        ],
        policy={},
    )

    assert authority["status"] == BLOCKED
    assert authority["policy_validation"]["status"] == BLOCKED
    assert authority["blocked_decisions"][0]["authorization_status"] == (
        "blocked_invalid_refresh_policy"
    )


def test_refresh_policy_compiler_rejects_missing_status_and_duplicate_ids() -> None:
    policy = {
        "schema_version": "source_module_refresh_policy_v0",
        "policy_id": "test_policy",
        "policy_revision": "test_rev",
        "operation": EXACT_COPY_SOURCE_MODULE_REFRESH_OPERATION,
        "grants": [
            {
                "grant_id": "duplicate",
                "operation": EXACT_COPY_SOURCE_MODULE_REFRESH_OPERATION,
                "source_ref": "tools/meta/control/scoped_commit.py",
                "source_to_target_relation": "exact_copy",
                "material_ids": ["scoped_commit_private_index_control_body_import"],
                "target_refs": ["examples/proof_bundle/source_modules/scoped_commit.py"],
            },
            {
                "grant_id": "duplicate",
                "status": "active",
                "operation": EXACT_COPY_SOURCE_MODULE_REFRESH_OPERATION,
                "source_ref": "tools/meta/control/scoped_commit.py",
                "source_to_target_relation": "exact_copy",
                "material_ids": ["scoped_commit_private_index_control_body_import"],
                "target_refs": ["examples/proof_bundle/source_modules/scoped_commit.py"],
            },
        ],
    }

    validation = compile_source_module_refresh_policy(policy)

    assert validation["status"] == BLOCKED
    finding_codes = {row["finding_code"] for row in validation["findings"]}
    assert "refresh_policy_grant_missing_status" in finding_codes
    assert "refresh_policy_duplicate_grant_id" in finding_codes


def test_refresh_authority_blocks_ambiguous_grants_and_prefix_collisions() -> None:
    row = {
        "material_id": "scoped_commit_private_index_control_body_import",
        "source_ref": "tools/meta/control/scoped_commit.py",
        "target_ref": "examples/proof_bundle/source_modules/scoped_commit.py",
        "source_to_target_relation": "exact_copy",
    }
    ambiguous_policy = {
        "schema_version": "source_module_refresh_policy_v0",
        "policy_id": "test_ambiguous_policy",
        "policy_revision": "test_rev",
        "operation": EXACT_COPY_SOURCE_MODULE_REFRESH_OPERATION,
        "grants": [
            {
                "grant_id": "exact_grant",
                "status": "active",
                "operation": EXACT_COPY_SOURCE_MODULE_REFRESH_OPERATION,
                "source_ref": "tools/meta/control/scoped_commit.py",
                "source_to_target_relation": "exact_copy",
                "material_ids": ["scoped_commit_private_index_control_body_import"],
                "target_refs": ["examples/proof_bundle/source_modules/scoped_commit.py"],
            },
            {
                "grant_id": "prefix_grant",
                "status": "active",
                "operation": EXACT_COPY_SOURCE_MODULE_REFRESH_OPERATION,
                "source_ref": "tools/meta/control/scoped_commit.py",
                "source_to_target_relation": "exact_copy",
                "material_ids": ["scoped_commit_private_index_control_body_import"],
                "target_ref_prefixes": ["examples/proof_bundle/source_modules"],
            },
        ],
    }
    ambiguous = evaluate_source_module_refresh_authority(
        [row],
        policy=ambiguous_policy,
    )

    assert ambiguous["status"] == BLOCKED
    assert ambiguous["blocked_decisions"][0]["authorization_status"] == (
        "blocked_ambiguous_refresh_grant"
    )

    collision_policy = {
        **ambiguous_policy,
        "policy_id": "test_collision_policy",
        "grants": [
            {
                **ambiguous_policy["grants"][1],
                "grant_id": "bounded_prefix",
                "target_ref_prefixes": ["examples/proof_bundle/source_modules/tool"],
            }
        ],
    }
    collision = evaluate_source_module_refresh_authority(
        [
            {
                **row,
                "target_ref": "examples/proof_bundle/source_modules/toolbox.py",
            }
        ],
        policy=collision_policy,
    )

    assert collision["status"] == BLOCKED
    assert collision["blocked_decisions"][0]["authorization_status"] == (
        "blocked_missing_refresh_grant"
    )


def test_refresh_authority_hard_denies_dominate_matching_grants() -> None:
    policy = {
        "schema_version": "source_module_refresh_policy_v0",
        "policy_id": "test_hard_deny_policy",
        "policy_revision": "test_policy_rev",
        "operation": EXACT_COPY_SOURCE_MODULE_REFRESH_OPERATION,
        "grants": [
            {
                "grant_id": "bad_secret_grant",
                "status": "active",
                "operation": EXACT_COPY_SOURCE_MODULE_REFRESH_OPERATION,
                "source_ref": "state/provider_payload.py",
                "target_refs": ["examples/proof_bundle/source_modules/provider_payload.py"],
                "source_to_target_relation": "exact_copy",
                "material_ids": ["provider_payload"],
            }
        ],
    }

    authority = evaluate_source_module_refresh_authority(
        [
            {
                "material_id": "provider_payload",
                "source_ref": "state/provider_payload.py",
                "target_ref": "examples/proof_bundle/source_modules/provider_payload.py",
                "source_to_target_relation": "exact_copy",
            }
        ],
        policy=policy,
    )

    assert authority["status"] == BLOCKED
    assert authority["blocked_decisions"][0]["authorization_status"] == (
        "blocked_hard_denial"
    )
    assert authority["hard_denies_dominate_grants"] is True


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
