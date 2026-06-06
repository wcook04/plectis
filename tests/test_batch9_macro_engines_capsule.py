from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.batch9_macro_engines_capsule import (
    AUTHORITY_CEILING,
    APPROVAL_MODULE_ID,
    AST_MODULE_ID,
    CONFIG_AUTHORITY_MODULE_ID,
    DEPENDENCY_PIN_MODULE_ID,
    DOCTRINE_MODULE_ID,
    EXPECTED_MECHANISMS,
    EXPECTED_MODULE_IDS,
    EXPECTED_NEGATIVE_CASES,
    FINANCE_MODULE_ID,
    HETEROGENEOUS_MODULE_ID,
    HOST_PRESSURE_MODULE_ID,
    LINEAGE_MODULE_ID,
    MILESTONE_MODULE_ID,
    MISSION_GRAPH_MODULE_ID,
    PROBE_MANIFEST_NAME,
    WORKER_GATE_MODULE_ID,
    WORK_ATLAS_MODULE_ID,
    main,
    result_card,
    run,
    run_batch9_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
ORGAN_ID = "batch9_macro_engines_capsule"
FIXTURE_INPUT = MICROCOSM_ROOT / f"fixtures/first_wave/{ORGAN_ID}/input"
EXPORTED_BUNDLE = MICROCOSM_ROOT / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle"
SOURCE_MODULE_MANIFEST = EXPORTED_BUNDLE / "source_module_manifest.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _copy_public_batch9_fixture(tmp_path: Path) -> tuple[Path, Path]:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / f"examples/{ORGAN_ID}",
        public_root / f"examples/{ORGAN_ID}",
    )
    shutil.copytree(
        MICROCOSM_ROOT / f"fixtures/first_wave/{ORGAN_ID}",
        public_root / f"fixtures/first_wave/{ORGAN_ID}",
    )
    return public_root, public_root / f"fixtures/first_wave/{ORGAN_ID}/input"


def _public_source_manifest_path(public_root: Path) -> Path:
    return (
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json"
    )


def _public_source_module_path(public_root: Path, relative_path: str) -> Path:
    return (
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_modules"
        / relative_path
    )


def _rewrite_manifest_digest_for_module(
    manifest_path: Path,
    module_id: str,
    source_path: Path,
) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest = _sha256(source_path)
    line_count = len(source_path.read_text(encoding="utf-8").splitlines())
    for row in manifest["modules"]:
        if row["module_id"] != module_id:
            continue
        row["sha256"] = digest
        row["source_sha256"] = digest
        row["target_sha256"] = digest
        row["line_count"] = line_count
        break
    else:  # pragma: no cover - fixture invariant
        raise AssertionError(module_id)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_batch9_macro_engines_capsule_runs_all_public_exercises(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / f"receipts/first_wave/{ORGAN_ID}",
        acceptance_out=tmp_path
        / f"receipts/acceptance/first_wave/{ORGAN_ID}_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["real_substrate_disposition"] == "real_substrate_capsule"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["source_module_manifest"]["module_count"] == len(EXPECTED_MODULE_IDS)
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_required_anchors_present"] is True

    exercise = result["exercise"]
    assert exercise["mechanism_count"] == len(EXPECTED_MECHANISMS)
    assert {row["mechanism_id"] for row in exercise["mechanisms"]} == set(EXPECTED_MECHANISMS)
    assert all(row["status"] == "pass" for row in exercise["mechanisms"])
    assert set(exercise["runtime_exercises"]) == set(EXPECTED_MECHANISMS)
    assert all(row["status"] == "pass" for row in exercise["runtime_exercises"].values())

    runtime = exercise["runtime_exercises"]
    assert runtime["lineage_temporal_provenance_chain_resolver"]["self_loop_pruned"] is False
    assert runtime["lineage_temporal_provenance_chain_resolver"]["cycle_detected"] is False
    assert runtime["lineage_temporal_provenance_chain_resolver"]["source_body_loaded"] is True
    assert (
        runtime["lineage_temporal_provenance_chain_resolver"]["source_contract"]["module_id"]
        == LINEAGE_MODULE_ID
    )
    assert runtime["approval_sign_off_claim_adjudicator"]["preacquired_claim_refused"] is False
    assert runtime["python_ast_symbol_index_doc_tree"]["syntax_error_gap"] is False
    assert "Outer.method" in runtime["python_ast_symbol_index_doc_tree"]["qualified_symbols"]
    assert runtime["python_ast_symbol_index_doc_tree"]["source_body_loaded"] is True
    assert (
        runtime["python_ast_symbol_index_doc_tree"]["source_contract"]["module_id"]
        == AST_MODULE_ID
    )
    assert runtime["finance_news_dedup_cluster_ranker"]["duplicate_collapsed"] is False
    assert runtime["mission_graph_topological_compiler"]["missing_target_error"] is False
    assert runtime["mission_graph_topological_compiler"]["source_body_loaded"] is True
    assert (
        runtime["mission_graph_topological_compiler"]["source_contract"]["module_id"]
        == MISSION_GRAPH_MODULE_ID
    )
    assert (
        runtime["mission_graph_topological_compiler"]["source_contract"][
            "group_closure_enabled"
        ]
        is True
    )
    assert runtime["dependency_pin_drift_auditor"]["drifted_count"] == 0
    assert runtime["dependency_pin_drift_auditor"]["missing_count"] == 0
    assert runtime["dependency_pin_drift_auditor"]["source_body_loaded"] is True
    assert (
        runtime["dependency_pin_drift_auditor"]["source_contract"]["module_id"]
        == DEPENDENCY_PIN_MODULE_ID
    )
    assert runtime["config_authority_drift_audit"]["mutation_allowed_rejected"] is False
    assert runtime["heterogeneous_graph_edge_extractor"]["normalized_relation_count"] == 0
    assert runtime["heterogeneous_graph_edge_extractor"]["source_body_loaded"] is True
    assert (
        runtime["heterogeneous_graph_edge_extractor"]["source_contract"]["module_id"]
        == HETEROGENEOUS_MODULE_ID
    )
    assert (
        runtime["heterogeneous_graph_edge_extractor"]["source_contract"][
            "top_dependencies_relation"
        ]
        == "depends_on"
    )
    assert runtime["work_atlas_cell_histogram_aggregator"]["route_reason_histogram"] == {}
    assert runtime["work_atlas_cell_histogram_aggregator"]["source_body_loaded"] is True
    assert (
        runtime["work_atlas_cell_histogram_aggregator"]["source_contract"]["module_id"]
        == WORK_ATLAS_MODULE_ID
    )
    assert (
        runtime["work_atlas_cell_histogram_aggregator"]["source_contract"][
            "unrouted_route_reason_gate"
        ]
        is True
    )
    assert runtime["host_pressure_admission_decision_gate"]["auto_policy_blocked"] is False
    assert runtime["host_pressure_admission_decision_gate"]["source_body_loaded"] is True
    assert (
        runtime["host_pressure_admission_decision_gate"]["source_contract"]["schema"]
        == "admission_consumer_decision_v0"
    )
    assert runtime["doctrine_file_enrichment_multihop_join"]["miss_empty_envelope"] is False
    assert runtime["doctrine_file_enrichment_multihop_join"]["source_body_loaded"] is True
    assert (
        runtime["doctrine_file_enrichment_multihop_join"]["source_contract"]["module_id"]
        == DOCTRINE_MODULE_ID
    )
    assert runtime["worker_job_budget_forbidden_surface_gate"]["blocked_job_status"] == "pass"
    assert runtime["worker_job_budget_forbidden_surface_gate"]["source_body_loaded"] is True
    assert (
        runtime["worker_job_budget_forbidden_surface_gate"]["source_contract"]["module_id"]
        == WORKER_GATE_MODULE_ID
    )
    assert (
        runtime["milestone_relative_promotion_quality_accounting"][
            "missing_committed_at_count_since_last_milestone"
        ]
        == 0
    )

    assert result["authority_ceiling"] == AUTHORITY_CEILING
    assert result["body_in_receipt"] is False


def test_batch9_public_fixture_resolves_copied_source_manifest_not_static_baked(
    tmp_path: Path,
) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)
    result = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/fixture-source-manifest",
        command="pytest",
    )

    source_manifest = result["source_module_manifest"]
    assert result["status"] == "pass"
    assert _public_source_manifest_path(public_root).is_file()
    assert source_manifest["manifest_ref"] == (
        f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json"
    )
    assert source_manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert source_manifest["module_count"] == len(EXPECTED_MODULE_IDS)
    assert {row["module_id"] for row in source_manifest["modules"]} == set(
        EXPECTED_MODULE_IDS
    )
    assert all(row["body_copied"] is True for row in source_manifest["modules"])
    assert result["exercise"]["copied_macro_source_module_count"] == len(
        EXPECTED_MODULE_IDS
    )
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch9_finance_exercise_uses_copied_macro_body(tmp_path: Path) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)
    probe_manifest_path = fixture_input / PROBE_MANIFEST_NAME
    probe_manifest = json.loads(probe_manifest_path.read_text(encoding="utf-8"))
    probe_manifest["positive_fixture"]["finance_news"]["rows"] = [
        {
            "headline": "Fed copper inventory signal jumps",
            "confidence": 0.7,
            "relevance": 0.1,
        },
        {
            "headline": "Copper inventory signal jumps",
            "confidence": 0.6,
            "relevance": 0.1,
        },
    ]
    probe_manifest_path.write_text(
        json.dumps(probe_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    baseline = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/baseline",
        command="pytest",
    )
    baseline_finance = baseline["exercise"]["runtime_exercises"][
        "finance_news_dedup_cluster_ranker"
    ]
    assert baseline["status"] == "pass"
    assert baseline_finance["source_body_loaded"] is True
    assert baseline_finance["source_contract"]["uses_normalized_headline_key"] is True
    assert baseline_finance["duplicate_collapsed"] is False

    source_path = (
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_modules"
        / "system/server/ui/src/lib/financePresentation.ts"
    )
    source_text = source_path.read_text(encoding="utf-8")
    assert "  'fed'," not in source_text
    source_path.write_text(
        source_text.replace("  'said',\n", "  'fed',\n"),
        encoding="utf-8",
    )
    _rewrite_manifest_digest_for_module(
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json",
        "finance_news_dedup_cluster_ranker",
        source_path,
    )

    shifted = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/shifted",
        command="pytest",
    )
    shifted_finance = shifted["exercise"]["runtime_exercises"][
        "finance_news_dedup_cluster_ranker"
    ]
    assert shifted["status"] == "pass"
    assert shifted["source_module_manifest"]["all_expected_digests_matched"] is True
    assert shifted_finance["source_body_loaded"] is True
    assert shifted_finance["source_contract"]["stopword_count"] == (
        baseline_finance["source_contract"]["stopword_count"]
    )
    assert shifted_finance["duplicate_collapsed"] is True
    assert shifted_finance["clusters"][0]["item_count"] == 2


def test_batch9_fixture_blocks_tampered_copied_source_body(tmp_path: Path) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)
    source_path = _public_source_module_path(
        public_root,
        "system/server/ui/src/lib/financePresentation.ts",
    )
    source_text = source_path.read_text(encoding="utf-8")
    assert "  'fed',\n" not in source_text
    source_path.write_text(
        source_text.replace("  'said',\n", "  'fed',\n"),
        encoding="utf-8",
    )

    result = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/tampered-source-body",
        command="pytest",
    )

    finance_row = [
        row
        for row in result["source_module_manifest"]["modules"]
        if row["module_id"] == FINANCE_MODULE_ID
    ][0]
    assert result["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False
    assert finance_row["digest_status"] == "mismatch"
    assert finance_row["missing_required_anchors"] == []


def test_batch9_manifest_import_class_perturbation_blocks(tmp_path: Path) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)
    manifest_path = _public_source_manifest_path(public_root)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_import_class"] = "static_fixture_only"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/bad-import-class",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_IMPORT_CLASS_INVALID" in result["error_codes"]
    assert result["source_module_manifest"]["source_import_class"] == "static_fixture_only"
    assert result["source_module_manifest"]["module_count"] == len(EXPECTED_MODULE_IDS)


def test_batch9_required_witness_anchor_removal_blocks_with_refreshed_digest(
    tmp_path: Path,
) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)
    source_path = _public_source_module_path(public_root, "system/server/graph.py")
    source_text = source_path.read_text(encoding="utf-8")
    required_anchor = "waves.append(sorted(current_wave))"
    assert required_anchor in source_text
    source_path.write_text(
        source_text.replace(required_anchor, "waves.append(list(current_wave))"),
        encoding="utf-8",
    )
    _rewrite_manifest_digest_for_module(
        _public_source_manifest_path(public_root),
        MISSION_GRAPH_MODULE_ID,
        source_path,
    )

    result = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/missing-required-witness",
        command="pytest",
    )

    mission_row = [
        row
        for row in result["source_module_manifest"]["modules"]
        if row["module_id"] == MISSION_GRAPH_MODULE_ID
    ][0]
    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_required_anchors_present"] is False
    assert "CROWN_JEWEL_SOURCE_ANCHOR_MISSING" in result["error_codes"]
    assert mission_row["digest_status"] == "match"
    assert mission_row["missing_required_anchors"] == [required_anchor]


def test_batch9_lineage_exercise_uses_copied_macro_body(tmp_path: Path) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)
    probe_manifest_path = fixture_input / PROBE_MANIFEST_NAME
    probe_manifest = json.loads(probe_manifest_path.read_text(encoding="utf-8"))
    probe_manifest["positive_fixture"]["lineage"]["contexts"]["RUN_SELF"] = {
        "source_run_id": "RUN_SELF"
    }
    probe_manifest_path.write_text(
        json.dumps(probe_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    baseline = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/lineage-baseline",
        command="pytest",
    )
    baseline_lineage = baseline["exercise"]["runtime_exercises"][
        "lineage_temporal_provenance_chain_resolver"
    ]
    assert baseline["status"] == "pass"
    assert baseline_lineage["source_body_loaded"] is True
    assert baseline_lineage["source_contract"]["module_id"] == LINEAGE_MODULE_ID
    assert baseline_lineage["self_loop_pruned"] is True

    source_path = (
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_modules"
        / "system/server/lineage.py"
    )
    source_text = source_path.read_text(encoding="utf-8")
    assert "if value == run_id:" in source_text
    source_path.write_text(
        source_text.replace("if value == run_id:", "if False and value == run_id:"),
        encoding="utf-8",
    )
    _rewrite_manifest_digest_for_module(
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json",
        LINEAGE_MODULE_ID,
        source_path,
    )

    shifted = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/lineage-shifted",
        command="pytest",
    )
    shifted_lineage = shifted["exercise"]["runtime_exercises"][
        "lineage_temporal_provenance_chain_resolver"
    ]
    assert shifted["source_module_manifest"]["all_expected_digests_matched"] is True
    assert shifted_lineage["source_body_loaded"] is True
    assert shifted_lineage["status"] == "pass"
    assert shifted_lineage["self_loop_pruned"] is False


def test_batch9_approval_exercise_uses_copied_macro_body(tmp_path: Path) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)

    baseline = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/approval-baseline",
        command="pytest",
    )
    baseline_approval = baseline["exercise"]["runtime_exercises"][
        "approval_sign_off_claim_adjudicator"
    ]
    assert baseline["status"] == "pass"
    assert baseline_approval["source_body_loaded"] is True
    assert baseline_approval["source_contract"]["module_id"] == APPROVAL_MODULE_ID
    assert baseline_approval["source_contract"]["claim_conflict_enforced"] is True
    assert baseline_approval["ok"] is True
    assert baseline_approval["preacquired_claim_refused"] is False

    case_path = fixture_input / "approval_preacquired_claim_refused.json"
    case_payload = json.loads(case_path.read_text(encoding="utf-8"))
    case_payload["fixture_patch"]["approval"]["preacquired"] = {
        "APPROVAL_1": {"nonce": "preacquired"}
    }
    case_path.write_text(
        json.dumps(case_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    source_path = (
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_modules"
        / "system/lib/approval_registry.py"
    )
    source_text = source_path.read_text(encoding="utf-8")
    assert "if existing and not _claim_expired(existing):" in source_text
    source_path.write_text(
        source_text.replace(
            "if existing and not _claim_expired(existing):",
            "if False and existing and not _claim_expired(existing):",
        ),
        encoding="utf-8",
    )
    _rewrite_manifest_digest_for_module(
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json",
        APPROVAL_MODULE_ID,
        source_path,
    )

    shifted = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/approval-shifted",
        command="pytest",
    )
    shifted_approval = shifted["exercise"]["runtime_exercises"][
        "approval_sign_off_claim_adjudicator"
    ]
    assert shifted["status"] == "blocked"
    assert shifted["source_module_manifest"]["all_expected_digests_matched"] is True
    assert shifted_approval["source_body_loaded"] is True
    assert shifted_approval["source_contract"]["claim_conflict_enforced"] is False
    assert shifted_approval["preacquired_claim_refused"] is False
    assert "approval_preacquired_claim_refused" in shifted["missing_negative_cases"]
    assert "BATCH9_APPROVAL_PREACQUIRED_CLAIM_REFUSED" not in shifted["error_codes"]


def test_batch9_ast_exercise_uses_copied_macro_body(tmp_path: Path) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)

    baseline = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/ast-baseline",
        command="pytest",
    )
    baseline_ast = baseline["exercise"]["runtime_exercises"][
        "python_ast_symbol_index_doc_tree"
    ]
    assert baseline["status"] == "pass"
    assert baseline_ast["source_body_loaded"] is True
    assert baseline_ast["source_contract"]["module_id"] == AST_MODULE_ID
    assert "async_job" in baseline_ast["qualified_symbols"]

    source_path = (
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_modules"
        / "system/lib/python_documentation_tree.py"
    )
    source_text = source_path.read_text(encoding="utf-8")
    assert 'function_records.append(function_record)' in source_text
    source_path.write_text(
        source_text.replace(
            'function_records.append(function_record)',
            'if not function_record["is_async"]:\n            function_records.append(function_record)',
        ),
        encoding="utf-8",
    )
    _rewrite_manifest_digest_for_module(
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json",
        AST_MODULE_ID,
        source_path,
    )

    shifted = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/ast-shifted",
        command="pytest",
    )
    shifted_ast = shifted["exercise"]["runtime_exercises"][
        "python_ast_symbol_index_doc_tree"
    ]
    assert shifted["status"] == "pass"
    assert shifted["source_module_manifest"]["all_expected_digests_matched"] is True
    assert shifted_ast["source_body_loaded"] is True
    assert "async_job" not in shifted_ast["qualified_symbols"]


def test_batch9_mission_graph_exercise_uses_copied_macro_body(tmp_path: Path) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)

    baseline = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/mission-graph-baseline",
        command="pytest",
    )
    baseline_mission = baseline["exercise"]["runtime_exercises"][
        "mission_graph_topological_compiler"
    ]
    assert baseline["status"] == "pass"
    assert baseline_mission["source_body_loaded"] is True
    assert baseline_mission["source_contract"]["module_id"] == MISSION_GRAPH_MODULE_ID
    assert baseline_mission["source_contract"]["group_closure_enabled"] is True
    assert baseline_mission["source_contract"]["upstream_dependency_walk_enabled"] is True
    assert baseline_mission["nodes"] == ["feed", "sibling", "target"]

    source_path = (
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_modules"
        / "system/server/graph.py"
    )
    source_text = source_path.read_text(encoding="utf-8")
    assert "grp == target_group" in source_text
    source_path.write_text(
        source_text.replace("grp == target_group", 'grp == "__batch9_disabled_group__"'),
        encoding="utf-8",
    )

    bad = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/mission-graph-bad-digest",
        command="pytest",
    )
    assert bad["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in bad["error_codes"]
    assert bad["source_module_manifest"]["all_expected_digests_matched"] is False

    _rewrite_manifest_digest_for_module(
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json",
        MISSION_GRAPH_MODULE_ID,
        source_path,
    )

    shifted = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/mission-graph-shifted",
        command="pytest",
    )
    shifted_mission = shifted["exercise"]["runtime_exercises"][
        "mission_graph_topological_compiler"
    ]
    assert shifted["status"] == "pass"
    assert shifted["source_module_manifest"]["all_expected_digests_matched"] is True
    assert shifted_mission["source_body_loaded"] is True
    assert shifted_mission["source_contract"]["group_closure_enabled"] is False
    assert shifted_mission["source_contract"]["upstream_dependency_walk_enabled"] is True
    assert shifted_mission["nodes"] == ["feed", "target"]
    assert "sibling" not in shifted_mission["nodes"]


def test_batch9_host_pressure_exercise_uses_copied_macro_body(tmp_path: Path) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)
    probe_manifest_path = fixture_input / PROBE_MANIFEST_NAME
    probe_manifest = json.loads(probe_manifest_path.read_text(encoding="utf-8"))
    host_quote = probe_manifest["positive_fixture"]["host_pressure"]["quote"]
    host_quote["recommendation"] = "render_summary_before_launch"
    host_quote["host_pressure_admission"] = {
        "status": "available",
        "should_block_run": True,
        "decision": "allow",
        "admission": {"operator_override_required": False},
    }
    probe_manifest_path.write_text(
        json.dumps(probe_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    baseline = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/host-pressure-baseline",
        command="pytest",
    )
    baseline_host = baseline["exercise"]["runtime_exercises"][
        "host_pressure_admission_decision_gate"
    ]
    assert baseline["status"] == "pass"
    assert baseline_host["source_body_loaded"] is True
    assert baseline_host["source_contract_status"] == "pass"
    assert baseline_host["source_contract"]["summary_recommendation_blocks"] is True
    assert baseline_host["decision_status"] == "blocked"
    assert baseline_host["result"] == "summary_first"
    assert baseline_host["auto_policy_blocked"] is True

    source_path = (
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_modules"
        / "system/lib/admission_consumer.py"
    )
    source_text = source_path.read_text(encoding="utf-8")
    assert 'or "summary" in recommendation' in source_text
    source_path.write_text(
        source_text.replace(
            'or "summary" in recommendation',
            'or "__summary_disabled__" in recommendation',
        ),
        encoding="utf-8",
    )
    _rewrite_manifest_digest_for_module(
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json",
        HOST_PRESSURE_MODULE_ID,
        source_path,
    )

    shifted = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/host-pressure-shifted",
        command="pytest",
    )
    shifted_host = shifted["exercise"]["runtime_exercises"][
        "host_pressure_admission_decision_gate"
    ]
    assert shifted["status"] == "blocked"
    assert shifted["source_module_manifest"]["all_expected_digests_matched"] is True
    assert shifted_host["source_body_loaded"] is True
    assert shifted_host["status"] == "blocked"
    assert shifted_host["source_contract_status"] == "blocked"
    assert shifted_host["source_contract"]["summary_recommendation_blocks"] is False
    assert shifted_host["decision_status"] == "allowed_by_admission"
    assert shifted_host["result"] == "allow"
    assert shifted_host["auto_policy_blocked"] is False
    assert any(
        row["code"] == "host_pressure_source_anchor_missing"
        for row in shifted_host["source_contract_findings"]
    )


def test_batch9_dependency_pin_exercise_uses_copied_macro_body(tmp_path: Path) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)

    baseline = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/dependency-baseline",
        command="pytest",
    )
    baseline_deps = baseline["exercise"]["runtime_exercises"][
        "dependency_pin_drift_auditor"
    ]
    assert baseline["status"] == "pass"
    assert baseline_deps["source_body_loaded"] is True
    assert baseline_deps["source_contract"]["module_id"] == DEPENDENCY_PIN_MODULE_ID
    assert baseline_deps["source_contract"]["parsed_requirement_count"] == 2
    assert baseline_deps["drifted_count"] == 0
    assert baseline_deps["missing_count"] == 0

    source_path = (
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_modules"
        / "tools/dev/check_pin_drift.py"
    )
    source_text = source_path.read_text(encoding="utf-8")
    assert "if in_range:" in source_text
    source_path.write_text(
        source_text.replace("if in_range:", "if not in_range:"),
        encoding="utf-8",
    )

    bad = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/dependency-bad-digest",
        command="pytest",
    )
    assert bad["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in bad["error_codes"]

    case_path = fixture_input / "dependency_pin_drift_detected.json"
    case_payload = json.loads(case_path.read_text(encoding="utf-8"))
    case_payload["fixture_patch"]["dependency_pin"] = {
        "requirements": ["fastapi>=0.100,<1.0"],
        "installed": {"fastapi": "0.110.0"},
    }
    case_path.write_text(
        json.dumps(case_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _rewrite_manifest_digest_for_module(
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json",
        DEPENDENCY_PIN_MODULE_ID,
        source_path,
    )

    shifted = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/dependency-shifted",
        command="pytest",
    )
    shifted_deps = shifted["exercise"]["runtime_exercises"][
        "dependency_pin_drift_auditor"
    ]
    assert shifted["status"] == "pass"
    assert shifted["source_module_manifest"]["all_expected_digests_matched"] is True
    assert shifted_deps["source_body_loaded"] is True
    assert shifted_deps["drifted_count"] == 2
    assert shifted_deps["drifted_count"] > baseline_deps["drifted_count"]
    assert shifted_deps["source_contract"]["parsed_requirement_count"] == 2


def test_batch9_config_authority_exercise_uses_copied_macro_body(tmp_path: Path) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)

    baseline = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/config-authority-baseline",
        command="pytest",
    )
    baseline_config = baseline["exercise"]["runtime_exercises"][
        "config_authority_drift_audit"
    ]
    assert baseline["status"] == "pass"
    assert baseline_config["source_body_loaded"] is True
    assert baseline_config["source_contract_status"] == "pass"
    assert baseline_config["source_contract"]["module_id"] == CONFIG_AUTHORITY_MODULE_ID
    assert baseline_config["audit_status"] == "pass"
    assert baseline_config["mutation_allowed_rejected"] is False

    source_path = (
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_modules"
        / "system/lib/config_authority_registry.py"
    )
    source_text = source_path.read_text(encoding="utf-8")
    assert 'payload.get("kind") != "config_authority_registry"' in source_text
    source_path.write_text(
        source_text.replace(
            'payload.get("kind") != "config_authority_registry"',
            'payload.get("kind") == "config_authority_registry"',
        ),
        encoding="utf-8",
    )
    _rewrite_manifest_digest_for_module(
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json",
        CONFIG_AUTHORITY_MODULE_ID,
        source_path,
    )

    shifted = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/config-authority-shifted",
        command="pytest",
    )
    shifted_config = shifted["exercise"]["runtime_exercises"][
        "config_authority_drift_audit"
    ]
    assert shifted["status"] == "blocked"
    assert shifted["source_module_manifest"]["all_expected_digests_matched"] is True
    assert shifted_config["source_body_loaded"] is True
    assert shifted_config["audit_status"] == "blocked"
    assert any(row["code"] == "invalid_kind" for row in shifted_config["audit_findings"])


def test_batch9_milestone_quality_exercise_uses_copied_macro_body(tmp_path: Path) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)

    baseline = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/milestone-quality-baseline",
        command="pytest",
    )
    baseline_milestone = baseline["exercise"]["runtime_exercises"][
        "milestone_relative_promotion_quality_accounting"
    ]
    assert baseline["status"] == "pass"
    assert baseline_milestone["source_body_loaded"] is True
    assert baseline_milestone["source_contract_status"] == "pass"
    assert baseline_milestone["source_contract"]["module_id"] == MILESTONE_MODULE_ID
    assert "classify_blockers_and_next_action" in baseline_milestone[
        "source_contract"
    ]["required_callables"]
    assert baseline_milestone["source_contract"]["materialized_run_dir_count"] == 2
    assert baseline_milestone["live_quality_eligible_count"] == 3
    assert baseline_milestone["green_count"] == 3
    assert baseline_milestone["projection_consumption_verified_count"] == 2
    assert baseline_milestone["missing_committed_at_count_since_last_milestone"] == 0
    assert baseline_milestone["next_action"]["decision"] == (
        "cohort_apply_unlocked_run_audit_first"
    )

    source_path = (
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_modules"
        / "system/lib/population_lane_metrics.py"
    )
    source_text = source_path.read_text(encoding="utf-8")
    assert "if not _is_post_milestone(run_at, milestone_at):" in source_text
    source_path.write_text(
        source_text.replace(
            "if not _is_post_milestone(run_at, milestone_at):",
            "if _is_post_milestone(run_at, milestone_at):",
        ),
        encoding="utf-8",
    )
    _rewrite_manifest_digest_for_module(
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json",
        MILESTONE_MODULE_ID,
        source_path,
    )

    shifted = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/milestone-quality-shifted",
        command="pytest",
    )
    shifted_milestone = shifted["exercise"]["runtime_exercises"][
        "milestone_relative_promotion_quality_accounting"
    ]
    assert shifted["status"] == "blocked"
    assert shifted["source_module_manifest"]["all_expected_digests_matched"] is True
    assert shifted_milestone["source_body_loaded"] is True
    assert shifted_milestone["status"] == "blocked"
    assert shifted_milestone["live_quality_eligible_count"] == 0
    assert shifted_milestone["next_action"]["decision"] == (
        "cohort_apply_unlocked_run_audit_first"
    )
    assert any(
        row["code"] == "milestone_macro_metric_mismatch"
        for row in shifted_milestone["source_contract_findings"]
    )


def test_batch9_milestone_blocker_action_uses_copied_macro_body(
    tmp_path: Path,
) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)
    probe_manifest_path = fixture_input / PROBE_MANIFEST_NAME
    probe_manifest = json.loads(probe_manifest_path.read_text(encoding="utf-8"))
    blocker_metrics = {
        "promotion_readiness": {
            "cohort_apply": False,
            "blocking_reasons": [
                "provider_capacity_missing_for_transport_repair",
            ],
        },
        "milestone_metrics": {
            "transport_only_count_since_last_milestone": 2,
            "transport_only_by_provider_since_last_milestone": {
                "openrouter_api": 2,
            },
            "transport_only_by_status_since_last_milestone": {
                "429": 2,
            },
            "missing_run_at_count_since_last_milestone": 0,
            "missing_committed_at_count_since_last_milestone": 0,
        },
    }
    probe_manifest["positive_fixture"]["milestone_quality"][
        "blocker_metrics"
    ] = blocker_metrics
    probe_manifest_path.write_text(
        json.dumps(probe_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    baseline = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/milestone-blocker-baseline",
        command="pytest",
    )
    baseline_milestone = baseline["exercise"]["runtime_exercises"][
        "milestone_relative_promotion_quality_accounting"
    ]
    assert baseline["status"] == "pass"
    assert baseline_milestone["source_body_loaded"] is True
    assert baseline_milestone["source_contract"]["module_id"] == MILESTONE_MODULE_ID
    assert "classify_blockers_and_next_action" in baseline_milestone[
        "source_contract"
    ]["required_callables"]
    assert baseline_milestone["blockers_by_class"]["provider_capacity"] == [
        "provider_capacity_missing_for_transport_repair"
    ]
    assert baseline_milestone["next_action"]["decision"] == (
        "provider_capacity_missing_for_transport_repair"
    )
    assert (
        "provider-capacity-discovery"
        in baseline_milestone["next_action"]["command"]
    )

    source_path = (
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_modules"
        / "system/lib/population_lane_metrics.py"
    )
    source_text = source_path.read_text(encoding="utf-8")
    assert 'if "provider_capacity_missing_for_transport_repair" in b:' in source_text
    source_path.write_text(
        source_text.replace(
            'if "provider_capacity_missing_for_transport_repair" in b:',
            'if "__batch9_disabled_provider_capacity__" in b:',
            1,
        ),
        encoding="utf-8",
    )
    _rewrite_manifest_digest_for_module(
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json",
        MILESTONE_MODULE_ID,
        source_path,
    )

    shifted = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/milestone-blocker-shifted",
        command="pytest",
    )
    shifted_milestone = shifted["exercise"]["runtime_exercises"][
        "milestone_relative_promotion_quality_accounting"
    ]
    assert shifted["status"] == "pass"
    assert shifted["source_module_manifest"]["all_expected_digests_matched"] is True
    assert shifted_milestone["source_body_loaded"] is True
    assert shifted_milestone["source_contract_status"] == "pass"
    assert shifted_milestone["blockers_by_class"]["provider_capacity"] == []
    assert shifted_milestone["blockers_by_class"]["other"] == [
        "provider_capacity_missing_for_transport_repair"
    ]
    assert shifted_milestone["next_action"]["decision"] == "hold_at_current_stage"
    assert shifted_milestone["next_action"]["decision"] != baseline_milestone[
        "next_action"
    ]["decision"]


def test_batch9_work_atlas_exercise_uses_copied_macro_body(tmp_path: Path) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)
    probe_manifest_path = fixture_input / PROBE_MANIFEST_NAME
    probe_manifest = json.loads(probe_manifest_path.read_text(encoding="utf-8"))
    probe_manifest["positive_fixture"]["work_atlas"]["marks"] = [
        {
            "id": "routed_mark_with_reason",
            "work_item_type": "repair",
            "overlays": {"unrouted": False},
            "route_explanation": {
                "route_reason": "should_not_count",
                "reason_kind": "noise",
            },
        }
    ]
    probe_manifest_path.write_text(
        json.dumps(probe_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    baseline = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/work-atlas-baseline",
        command="pytest",
    )
    baseline_atlas = baseline["exercise"]["runtime_exercises"][
        "work_atlas_cell_histogram_aggregator"
    ]
    assert baseline["status"] == "pass"
    assert baseline_atlas["source_body_loaded"] is True
    assert baseline_atlas["source_contract_status"] == "pass"
    assert baseline_atlas["source_contract"]["module_id"] == WORK_ATLAS_MODULE_ID
    assert baseline_atlas["source_contract"]["unrouted_route_reason_gate"] is True
    assert baseline_atlas["route_reason_histogram"] == {}

    source_path = (
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_modules"
        / "system/server/ui/src/components/intelligence/WorkAtlas.tsx"
    )
    source_text = source_path.read_text(encoding="utf-8")
    assert "if (o.unrouted) {" in source_text
    source_path.write_text(
        source_text.replace("if (o.unrouted) {", "if (true) {", 1),
        encoding="utf-8",
    )
    _rewrite_manifest_digest_for_module(
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json",
        WORK_ATLAS_MODULE_ID,
        source_path,
    )

    shifted = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/work-atlas-shifted",
        command="pytest",
    )
    shifted_atlas = shifted["exercise"]["runtime_exercises"][
        "work_atlas_cell_histogram_aggregator"
    ]
    assert shifted["status"] == "blocked"
    assert shifted["source_module_manifest"]["all_expected_digests_matched"] is True
    assert shifted_atlas["source_body_loaded"] is True
    assert shifted_atlas["source_contract_status"] == "blocked"
    assert shifted_atlas["route_reason_histogram"] == {"should_not_count": 1}
    assert any(
        row["code"] == "work_atlas_source_anchor_missing"
        for row in shifted_atlas["source_contract_findings"]
    )


def test_batch9_heterogeneous_edges_use_copied_macro_body(tmp_path: Path) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)

    baseline = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/heterogeneous-baseline",
        command="pytest",
    )
    baseline_edges = baseline["exercise"]["runtime_exercises"][
        "heterogeneous_graph_edge_extractor"
    ]
    baseline_top_dependency = next(
        row for row in baseline_edges["edges"] if row["source_field"] == "top_dependencies"
    )
    assert baseline["status"] == "pass"
    assert baseline_edges["source_body_loaded"] is True
    assert baseline_edges["source_contract_status"] == "pass"
    assert baseline_edges["source_contract"]["module_id"] == HETEROGENEOUS_MODULE_ID
    assert baseline_edges["source_contract"]["derived_field_count"] >= 21
    assert baseline_edges["source_contract"]["top_dependencies_relation"] == "depends_on"
    assert baseline_top_dependency["relation"] == "depends_on"

    source_path = (
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_modules"
        / "system/server/ui/src/pages/RootNavigator.tsx"
    )
    source_text = source_path.read_text(encoding="utf-8")
    assert "{ field: 'top_dependencies', relation: 'depends_on'" in source_text
    source_path.write_text(
        source_text.replace(
            "{ field: 'top_dependencies', relation: 'depends_on'",
            "{ field: 'top_dependencies', relation: 'related_to'",
            1,
        ),
        encoding="utf-8",
    )
    _rewrite_manifest_digest_for_module(
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json",
        HETEROGENEOUS_MODULE_ID,
        source_path,
    )

    shifted = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/heterogeneous-shifted",
        command="pytest",
    )
    shifted_edges = shifted["exercise"]["runtime_exercises"][
        "heterogeneous_graph_edge_extractor"
    ]
    shifted_top_dependency = next(
        row for row in shifted_edges["edges"] if row["source_field"] == "top_dependencies"
    )
    assert shifted["status"] == "pass"
    assert shifted["source_module_manifest"]["all_expected_digests_matched"] is True
    assert shifted_edges["source_body_loaded"] is True
    assert shifted_edges["source_contract_status"] == "pass"
    assert shifted_edges["source_contract"]["top_dependencies_relation"] == "related_to"
    assert shifted_top_dependency["relation"] == "related_to"
    assert shifted_top_dependency["relation"] != baseline_top_dependency["relation"]


def test_batch9_heterogeneous_edges_reject_mutated_required_relation_map(
    tmp_path: Path,
) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)

    baseline = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/heterogeneous-required-baseline",
        command="pytest",
    )
    baseline_edges = baseline["exercise"]["runtime_exercises"][
        "heterogeneous_graph_edge_extractor"
    ]
    assert baseline["status"] == "pass"
    assert baseline_edges["source_body_loaded"] is True
    assert baseline_edges["source_contract_status"] == "pass"
    assert baseline_edges["source_contract"]["top_dependencies_relation"] == "depends_on"

    source_path = (
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_modules"
        / "system/server/ui/src/pages/RootNavigator.tsx"
    )
    source_text = source_path.read_text(encoding="utf-8")
    assert "{ field: 'top_dependencies', relation: 'depends_on'" in source_text
    source_path.write_text(
        source_text.replace(
            "{ field: 'top_dependencies', relation: 'depends_on'",
            "{ field: 'top_dependencies_removed', relation: 'depends_on'",
            1,
        ),
        encoding="utf-8",
    )
    _rewrite_manifest_digest_for_module(
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json",
        HETEROGENEOUS_MODULE_ID,
        source_path,
    )

    shifted = run(
        fixture_input,
        public_root
        / f"receipts/first_wave/{ORGAN_ID}/heterogeneous-required-shifted",
        command="pytest",
    )
    shifted_edges = shifted["exercise"]["runtime_exercises"][
        "heterogeneous_graph_edge_extractor"
    ]
    assert shifted["status"] == "blocked"
    assert shifted["source_module_manifest"]["all_expected_digests_matched"] is True
    assert shifted_edges["source_body_loaded"] is True
    assert shifted_edges["source_contract_status"] == "blocked"
    assert shifted_edges["source_contract"]["top_dependencies_relation"] == ""
    assert not any(
        row["source_field"] == "top_dependencies" for row in shifted_edges["edges"]
    )
    assert any(
        row["error_code"] == "BATCH9_HETEROGENEOUS_EDGE_FIELD_MISSING"
        for row in shifted_edges["source_contract_findings"]
    )


def test_batch9_doctrine_enrichment_exercise_uses_copied_macro_body(tmp_path: Path) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)

    baseline = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/doctrine-baseline",
        command="pytest",
    )
    baseline_doctrine = baseline["exercise"]["runtime_exercises"][
        "doctrine_file_enrichment_multihop_join"
    ]
    assert baseline["status"] == "pass"
    assert baseline_doctrine["source_body_loaded"] is True
    assert baseline_doctrine["source_contract"]["module_id"] == DOCTRINE_MODULE_ID
    assert baseline_doctrine["counts"]["mechanisms"] == 1
    assert baseline_doctrine["empty_envelope"] is False

    source_path = (
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_modules"
        / "system/server/doctrine_enrichment.py"
    )
    source_text = source_path.read_text(encoding="utf-8")
    assert "self._mechanisms_by_path.setdefault(path, []).append(entry)" in source_text
    source_path.write_text(
        source_text.replace(
            "self._mechanisms_by_path.setdefault(path, []).append(entry)",
            'self._mechanisms_by_path.setdefault(f"broken::{path}", []).append(entry)',
        ),
        encoding="utf-8",
    )
    _rewrite_manifest_digest_for_module(
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json",
        DOCTRINE_MODULE_ID,
        source_path,
    )

    shifted = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/doctrine-shifted",
        command="pytest",
    )
    shifted_doctrine = shifted["exercise"]["runtime_exercises"][
        "doctrine_file_enrichment_multihop_join"
    ]
    assert shifted["status"] == "blocked"
    assert shifted["source_module_manifest"]["all_expected_digests_matched"] is True
    assert shifted_doctrine["source_body_loaded"] is True
    assert shifted_doctrine["status"] == "blocked"
    assert shifted_doctrine["counts"]["mechanisms"] == 0
    assert shifted_doctrine["empty_envelope"] is True


def test_batch9_worker_gate_exercise_uses_copied_macro_body(tmp_path: Path) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)
    probe_manifest_path = fixture_input / PROBE_MANIFEST_NAME
    probe_manifest = json.loads(probe_manifest_path.read_text(encoding="utf-8"))
    probe_manifest["positive_fixture"]["worker_gate"]["blocked_job"] = {
        "provider_id": "openrouter_api",
        "model_id": "free/test:free",
        "provider_budget": {},
        "forbidden_surfaces": ["raw_seed.md"],
        "input_packet": {"path": "raw_seed.md"},
    }
    probe_manifest_path.write_text(
        json.dumps(probe_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    baseline = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/worker-baseline",
        command="pytest",
    )
    baseline_worker = baseline["exercise"]["runtime_exercises"][
        "worker_job_budget_forbidden_surface_gate"
    ]
    assert baseline["status"] == "pass"
    assert baseline_worker["source_body_loaded"] is True
    assert baseline_worker["source_contract"]["module_id"] == WORKER_GATE_MODULE_ID
    assert baseline_worker["blocked_job_status"] == "blocked"
    assert baseline_worker["blocked_job_allow"] is False
    assert baseline_worker["blocked_surface"] == "raw_seed.md"

    source_path = (
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_modules"
        / "system/lib/type_a_worker_harness.py"
    )
    source_text = source_path.read_text(encoding="utf-8")
    assert "if pattern in text:" in source_text
    source_path.write_text(
        source_text.replace("if pattern in text:", "if False and pattern in text:"),
        encoding="utf-8",
    )
    _rewrite_manifest_digest_for_module(
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json",
        WORKER_GATE_MODULE_ID,
        source_path,
    )

    shifted = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/worker-shifted",
        command="pytest",
    )
    shifted_worker = shifted["exercise"]["runtime_exercises"][
        "worker_job_budget_forbidden_surface_gate"
    ]
    assert shifted["status"] == "blocked"
    assert shifted["source_module_manifest"]["all_expected_digests_matched"] is True
    assert shifted_worker["source_body_loaded"] is True
    assert shifted_worker["status"] == "blocked"
    assert shifted_worker["source_contract_status"] == "blocked"
    assert shifted_worker["source_contract"]["forbidden_surface_scan_enabled"] is False
    assert shifted_worker["blocked_job_status"] == "blocked"
    assert shifted_worker["blocked_job_allow"] is True
    assert shifted_worker["blocked_job_reason"] == "worker_gate_source_contract_failed"
    assert shifted_worker["blocked_surface"] is None
    assert any(
        row["code"] == "worker_gate_source_anchor_missing"
        for row in shifted_worker["source_contract_findings"]
    )


def test_batch9_worker_gate_budget_input_moves_imported_macro_body(tmp_path: Path) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)
    probe_manifest_path = fixture_input / PROBE_MANIFEST_NAME
    probe_manifest = json.loads(probe_manifest_path.read_text(encoding="utf-8"))
    blocked_job = {
        "provider_id": "openrouter_api",
        "model_id": "openrouter/paid-model",
        "provider_budget": {"allow_paid": True, "free_only": False, "max_usd": 0.0},
        "forbidden_surfaces": [],
        "input_packet": {"topic": "batch9 public proof"},
    }
    probe_manifest["positive_fixture"]["worker_gate"]["blocked_job"] = blocked_job
    probe_manifest_path.write_text(
        json.dumps(probe_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    blocked = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/worker-budget-blocked",
        command="pytest",
    )
    blocked_worker = blocked["exercise"]["runtime_exercises"][
        "worker_job_budget_forbidden_surface_gate"
    ]
    assert blocked["status"] == "pass"
    assert blocked_worker["source_body_loaded"] is True
    assert blocked_worker["source_contract"]["module_id"] == WORKER_GATE_MODULE_ID
    assert blocked_worker["blocked_job_status"] == "blocked"
    assert blocked_worker["blocked_job_reason"] == (
        "openrouter_paid_model_blocked_by_provider_budget"
    )

    probe_manifest["positive_fixture"]["worker_gate"]["blocked_job"]["provider_budget"][
        "max_usd"
    ] = 0.02
    probe_manifest_path.write_text(
        json.dumps(probe_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    admitted = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/worker-budget-admitted",
        command="pytest",
    )
    admitted_worker = admitted["exercise"]["runtime_exercises"][
        "worker_job_budget_forbidden_surface_gate"
    ]
    assert admitted["status"] == "pass"
    assert admitted["source_module_manifest"]["all_expected_digests_matched"] is True
    assert admitted_worker["source_body_loaded"] is True
    assert admitted_worker["blocked_job_status"] == "pass"
    assert admitted_worker["blocked_job_reason"] is None


def test_batch9_worker_gate_budget_guard_uses_copied_macro_body(tmp_path: Path) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)
    probe_manifest_path = fixture_input / PROBE_MANIFEST_NAME
    probe_manifest = json.loads(probe_manifest_path.read_text(encoding="utf-8"))
    probe_manifest["positive_fixture"]["worker_gate"]["blocked_job"] = {
        "provider_id": "openrouter_api",
        "model_id": "openrouter/paid-model",
        "provider_budget": {"allow_paid": True, "free_only": False, "max_usd": 0.0},
        "forbidden_surfaces": [],
        "input_packet": {"topic": "batch9 public proof"},
    }
    probe_manifest_path.write_text(
        json.dumps(probe_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    baseline = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/worker-budget-guard-baseline",
        command="pytest",
    )
    baseline_worker = baseline["exercise"]["runtime_exercises"][
        "worker_job_budget_forbidden_surface_gate"
    ]
    assert baseline["status"] == "pass"
    assert baseline_worker["source_body_loaded"] is True
    assert baseline_worker["source_contract"]["module_id"] == WORKER_GATE_MODULE_ID
    assert baseline_worker["source_contract"]["budget_gate_enabled"] is True
    assert baseline_worker["source_contract"]["budget_guard_condition_enabled"] is True
    assert baseline_worker["blocked_job_status"] == "blocked"
    assert baseline_worker["blocked_job_allow"] is False
    assert baseline_worker["blocked_job_reason"] == (
        "openrouter_paid_model_blocked_by_provider_budget"
    )

    source_path = (
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_modules"
        / "system/lib/type_a_worker_harness.py"
    )
    source_text = source_path.read_text(encoding="utf-8")
    assert "if free_only or not allow_paid or max_usd <= 0:" in source_text
    source_path.write_text(
        source_text.replace(
            "if free_only or not allow_paid or max_usd <= 0:",
            "if False and (free_only or not allow_paid or max_usd <= 0):",
        ),
        encoding="utf-8",
    )
    _rewrite_manifest_digest_for_module(
        public_root
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json",
        WORKER_GATE_MODULE_ID,
        source_path,
    )

    shifted = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}/worker-budget-guard-shifted",
        command="pytest",
    )
    shifted_worker = shifted["exercise"]["runtime_exercises"][
        "worker_job_budget_forbidden_surface_gate"
    ]
    assert shifted["status"] == "blocked"
    assert shifted["source_module_manifest"]["all_expected_digests_matched"] is True
    assert shifted_worker["source_body_loaded"] is True
    assert shifted_worker["source_contract_status"] == "blocked"
    assert shifted_worker["source_contract"]["budget_gate_enabled"] is True
    assert shifted_worker["source_contract"]["budget_guard_condition_enabled"] is False
    assert shifted_worker["blocked_job_status"] == "blocked"
    assert shifted_worker["blocked_job_allow"] is True
    assert shifted_worker["blocked_job_reason"] == "worker_gate_source_contract_failed"
    assert any(
        row["code"] == "worker_gate_source_anchor_missing"
        for row in shifted_worker["source_contract_findings"]
    )


def test_batch9_negative_cases_ignore_declared_fixture_codes(tmp_path: Path) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)
    for case_id in EXPECTED_NEGATIVE_CASES:
        case_path = fixture_input / f"{case_id}.json"
        payload = json.loads(case_path.read_text(encoding="utf-8"))
        payload["error_codes"] = ["BOGUS_DECLARED_ERROR"]
        case_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    result = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert "BOGUS_DECLARED_ERROR" not in result["error_codes"]
    assert all(
        row["semantic_evaluator_used"] is True
        for row in result["negative_case_semantics"]
    )


def test_batch9_negative_cases_move_when_public_input_changes(tmp_path: Path) -> None:
    public_root, fixture_input = _copy_public_batch9_fixture(tmp_path)
    case_path = fixture_input / "finance_duplicate_headline_collapsed.json"
    payload = json.loads(case_path.read_text(encoding="utf-8"))
    payload["fixture_patch"]["finance_news"]["rows"] = [
        {
            "headline": "Copper inventories rebound after port reopenings",
            "confidence": 0.7,
            "relevance": 0.2,
        },
        {
            "headline": "Chip exports rally after earnings surprise",
            "confidence": 0.4,
            "relevance": 0.1,
        },
    ]
    case_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture_input,
        public_root / f"receipts/first_wave/{ORGAN_ID}",
        command="pytest",
    )

    finance_case = [
        row
        for row in result["negative_case_semantics"]
        if row["case_id"] == "finance_duplicate_headline_collapsed"
    ][0]
    assert result["status"] == "blocked"
    assert "finance_duplicate_headline_collapsed" in result["missing_negative_cases"]
    assert finance_case["status"] == "pass"
    assert finance_case["error_codes"] == []
    assert "CROWN_JEWEL_NEGATIVE_CASE_NOT_REJECTED" in result["error_codes"]
    assert "CROWN_JEWEL_NEGATIVE_CASE_CODE_MISSING" in result["error_codes"]
    assert "BATCH9_FINANCE_DUPLICATE_HEADLINE_COLLAPSED" not in result["error_codes"]


def test_batch9_macro_engines_capsule_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_batch9_bundle(
        EXPORTED_BUNDLE,
        tmp_path / f"receipts/runtime_shell/demo_project/organs/{ORGAN_ID}",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == f"exported_{ORGAN_ID}_bundle"
    assert result["source_module_manifest"]["module_count"] == len(EXPECTED_MODULE_IDS)
    assert result["exercise"]["copied_macro_source_module_count"] == len(EXPECTED_MODULE_IDS)
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch9_bundle_heterogeneous_edges_relation_moves_with_exported_source_body(
    tmp_path: Path,
) -> None:
    public_root, _fixture_input = _copy_public_batch9_fixture(tmp_path)
    bundle = public_root / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle"

    baseline = run_batch9_bundle(
        bundle,
        tmp_path / f"receipts/runtime_shell/demo_project/organs/{ORGAN_ID}/baseline",
        command="pytest",
    )
    baseline_edges = baseline["exercise"]["runtime_exercises"][
        "heterogeneous_graph_edge_extractor"
    ]
    baseline_top_dependency = next(
        row for row in baseline_edges["edges"] if row["source_field"] == "top_dependencies"
    )
    assert baseline["status"] == "pass"
    assert baseline["input_mode"] == f"exported_{ORGAN_ID}_bundle"
    assert baseline_edges["source_body_loaded"] is True
    assert baseline_edges["source_contract"]["top_dependencies_relation"] == "depends_on"
    assert baseline_top_dependency["relation"] == "depends_on"

    source_path = bundle / "source_modules/system/server/ui/src/pages/RootNavigator.tsx"
    source_text = source_path.read_text(encoding="utf-8")
    assert "{ field: 'top_dependencies', relation: 'depends_on'" in source_text
    source_path.write_text(
        source_text.replace(
            "{ field: 'top_dependencies', relation: 'depends_on'",
            "{ field: 'top_dependencies', relation: 'related_to'",
            1,
        ),
        encoding="utf-8",
    )
    _rewrite_manifest_digest_for_module(
        bundle / "source_module_manifest.json",
        HETEROGENEOUS_MODULE_ID,
        source_path,
    )

    shifted = run_batch9_bundle(
        bundle,
        tmp_path / f"receipts/runtime_shell/demo_project/organs/{ORGAN_ID}/shifted",
        command="pytest",
    )
    shifted_edges = shifted["exercise"]["runtime_exercises"][
        "heterogeneous_graph_edge_extractor"
    ]
    shifted_top_dependency = next(
        row for row in shifted_edges["edges"] if row["source_field"] == "top_dependencies"
    )
    assert shifted["status"] == "pass"
    assert shifted["source_module_manifest"]["all_expected_digests_matched"] is True
    assert shifted_edges["source_body_loaded"] is True
    assert shifted_edges["source_contract_status"] == "pass"
    assert shifted_edges["source_contract"]["top_dependencies_relation"] == "related_to"
    assert shifted_top_dependency["relation"] == "related_to"
    assert shifted_top_dependency["relation"] != baseline_top_dependency["relation"]


def test_batch9_bundle_rejects_bad_heterogeneous_edge_source_body(
    tmp_path: Path,
) -> None:
    public_root, _fixture_input = _copy_public_batch9_fixture(tmp_path)
    bundle = public_root / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle"

    baseline = run_batch9_bundle(
        bundle,
        tmp_path
        / f"receipts/runtime_shell/demo_project/organs/{ORGAN_ID}/required-baseline",
        command="pytest",
    )
    baseline_edges = baseline["exercise"]["runtime_exercises"][
        "heterogeneous_graph_edge_extractor"
    ]
    assert baseline["status"] == "pass"
    assert baseline_edges["source_body_loaded"] is True
    assert baseline_edges["source_contract_status"] == "pass"
    assert baseline_edges["source_contract"]["top_dependencies_relation"] == "depends_on"

    source_path = bundle / "source_modules/system/server/ui/src/pages/RootNavigator.tsx"
    source_text = source_path.read_text(encoding="utf-8")
    assert "{ field: 'top_dependencies', relation: 'depends_on'" in source_text
    source_path.write_text(
        source_text.replace(
            "{ field: 'top_dependencies', relation: 'depends_on'",
            "{ field: 'top_dependencies_removed', relation: 'depends_on'",
            1,
        ),
        encoding="utf-8",
    )
    _rewrite_manifest_digest_for_module(
        bundle / "source_module_manifest.json",
        HETEROGENEOUS_MODULE_ID,
        source_path,
    )

    shifted = run_batch9_bundle(
        bundle,
        tmp_path
        / f"receipts/runtime_shell/demo_project/organs/{ORGAN_ID}/required-shifted",
        command="pytest",
    )
    shifted_edges = shifted["exercise"]["runtime_exercises"][
        "heterogeneous_graph_edge_extractor"
    ]
    assert shifted["status"] == "blocked"
    assert shifted["input_mode"] == f"exported_{ORGAN_ID}_bundle"
    assert shifted["source_module_manifest"]["all_expected_digests_matched"] is True
    assert shifted_edges["source_body_loaded"] is True
    assert shifted_edges["source_contract_status"] == "blocked"
    assert shifted_edges["source_contract"]["top_dependencies_relation"] == ""
    assert not any(
        row["source_field"] == "top_dependencies" for row in shifted_edges["edges"]
    )
    assert any(
        row["error_code"] == "BATCH9_HETEROGENEOUS_EDGE_FIELD_MISSING"
        for row in shifted_edges["source_contract_findings"]
    )


def test_batch9_bundle_blocks_tampered_copied_source_body(tmp_path: Path) -> None:
    public_root, _fixture_input = _copy_public_batch9_fixture(tmp_path)
    bundle = public_root / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle"
    source_path = bundle / "source_modules/system/server/ui/src/lib/financePresentation.ts"
    source_text = source_path.read_text(encoding="utf-8")
    assert "  'fed',\n" not in source_text
    source_path.write_text(
        source_text.replace("  'said',\n", "  'fed',\n"),
        encoding="utf-8",
    )

    result = run_batch9_bundle(
        bundle,
        public_root / f"receipts/runtime_shell/demo_project/organs/{ORGAN_ID}",
        command="pytest",
    )

    finance_row = [
        row
        for row in result["source_module_manifest"]["modules"]
        if row["path"] == "source_modules/system/server/ui/src/lib/financePresentation.ts"
    ][0]
    assert result["status"] == "blocked"
    assert result["input_mode"] == f"exported_{ORGAN_ID}_bundle"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False
    assert finance_row["digest_status"] == "mismatch"
    assert finance_row["missing_required_anchors"] == []


def test_batch9_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["module_count"] == len(EXPECTED_MODULE_IDS)
    assert manifest["body_in_receipt"] is False
    assert {row["module_id"] for row in manifest["modules"]} == set(EXPECTED_MODULE_IDS)

    for row in manifest["modules"]:
        source = SOURCE_ROOT / row["source_ref"]
        target = EXPORTED_BUNDLE / row["path"]
        assert source.is_file(), row["source_ref"]
        assert target.is_file(), row["path"]
        assert source.read_bytes() == target.read_bytes(), row["source_ref"]
        assert row["sha256"] == _sha256(source)
        assert row["source_sha256"] == row["sha256"]
        assert row["target_sha256"] == row["sha256"]
        assert row["sha256_match"] is True
        text = target.read_text(encoding="utf-8")
        assert all(anchor in text for anchor in row["required_anchors"])


def test_batch9_card_omits_private_bodies(tmp_path: Path, capsys) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / f"receipts/first_wave/{ORGAN_ID}",
        command="pytest",
    )
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["semantic_negative_case_evaluator_used"] is True
    assert card["authority_floor"] == {
        "authority_ceiling": AUTHORITY_CEILING["authority_ceiling"],
        "real_substrate_disposition": "real_substrate_capsule",
        "standard_authority": AUTHORITY_CEILING["standard_authority"],
        "provider_dispatch": False,
        "host_state_truth": False,
        "live_doctrine_truth": False,
        "real_news_truth": False,
        "market_advice": False,
        "work_ledger_authority": False,
        "source_mutation_authorized": False,
        "publication_authorized": False,
        "release_authorized": False,
        "whole_system_correctness_claim": False,
    }
    assert card["body_floor"] == {
        "body_in_receipt": False,
        "source_module_body_in_receipt": False,
        "receipt_body_scan_status": "pass",
        "source_bodies_in_card": False,
        "secret_scan_scope_in_card": False,
    }
    assert card["source_module_count"] == len(EXPECTED_MODULE_IDS)
    assert card["observed_negative_case_count"] == len(EXPECTED_NEGATIVE_CASES)
    assert card["body_in_receipt"] is False
    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "assistant_raw_text" not in _walk_keys(result)
    assert "raw_text" not in _walk_keys(result)
    assert "body" not in _walk_keys(result)

    assert (
        main(
            [
                "run",
                "--input",
                str(FIXTURE_INPUT),
                "--out",
                str(tmp_path / "cli_card"),
                "--card",
            ]
        )
        == 0
    )
    cli_card = json.loads(capsys.readouterr().out)
    assert cli_card["authority_floor"] == card["authority_floor"]
    assert cli_card["body_floor"] == card["body_floor"]

    assert (
        main(
            [
                "validate-bundle",
                "--input",
                str(EXPORTED_BUNDLE),
                "--out",
                str(tmp_path / "cli_bundle_card"),
                "--card",
            ]
        )
        == 0
    )
    bundle_cli_card = json.loads(capsys.readouterr().out)
    assert bundle_cli_card["input_mode"] == f"exported_{ORGAN_ID}_bundle"
    assert bundle_cli_card["source_module_count"] == len(EXPECTED_MODULE_IDS)
    assert bundle_cli_card["body_floor"] == card["body_floor"]
