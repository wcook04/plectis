from __future__ import annotations

import json
import shutil
from pathlib import Path

from microcosm_core.organs.self_ignorance_coverage_ledger import (
    EXPECTED_NEGATIVE_CASES,
    evaluate,
    run,
    run_self_ignorance_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/self_ignorance_coverage_ledger/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/self_ignorance_coverage_ledger/"
    "exported_self_ignorance_coverage_ledger_bundle"
)


def _copy_public_bundle(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/self_ignorance_coverage_ledger/"
        "exported_self_ignorance_coverage_ledger_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    return bundle


def _public_root_for_bundle(bundle: Path) -> Path:
    for candidate in bundle.parents:
        if candidate.name == "microcosm-substrate":
            return candidate
    raise AssertionError(f"bundle is not under a public root: {bundle}")


def _materialize_standard_entity(
    bundle: Path,
    standard_id: str,
    *,
    require_source: bool,
) -> None:
    source_ref = MICROCOSM_ROOT.parent / "codex/standards" / f"{standard_id}.json"
    if require_source:
        assert source_ref.is_file()
    else:
        assert not source_ref.exists()

    graph_path = bundle / "system_atlas_graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    assert all(
        (row.get("id") or row.get("entity_id")) != standard_id
        for row in graph["entities"]
        if isinstance(row, dict)
    )
    graph["entities"].append(
        {
            "id": standard_id,
            "kind": "Standard",
            "title": standard_id.removeprefix("std_").replace("_", " ").title(),
        }
    )
    graph_path.write_text(json.dumps(graph, sort_keys=True), encoding="utf-8")

    rows_path = bundle / "kind_atlas_rows.json"
    rows = json.loads(rows_path.read_text(encoding="utf-8"))
    standards_row = next(
        row for row in rows["rows"] if row.get("kind_id") == "standards"
    )
    standards_row["expected_entity_ids"].append(standard_id)
    standards_debt = next(
        row for row in rows["expected_known_debt"] if row.get("kind_id") == "standards"
    )
    standards_debt["expected_debt_count"] -= 1
    standards_debt["reason"] = (
        "Live Kind Atlas exposes 201 standards rows while the System Atlas graph "
        "excerpt materializes 30 row-level entities."
    )
    rows_path.write_text(json.dumps(rows, sort_keys=True), encoding="utf-8")

    materialized_path = bundle / "materialized_entities.json"
    materialized = json.loads(materialized_path.read_text(encoding="utf-8"))
    standards_materialization = next(
        row
        for row in materialized["materialization_rows"]
        if row.get("kind_id") == "standards"
    )
    standards_materialization["system_atlas_materialized_entity_count"] += 1
    materialized_path.write_text(
        json.dumps(materialized, sort_keys=True),
        encoding="utf-8",
    )


def _materialize_real_standard_entity(bundle: Path, standard_id: str) -> None:
    _materialize_standard_entity(bundle, standard_id, require_source=True)


def _remove_materialized_standard_entity(bundle: Path) -> str:
    graph_path = bundle / "system_atlas_graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    entities = graph["entities"]
    removed_entity = None
    for index in range(len(entities) - 1, -1, -1):
        entity_id = entities[index].get("id") or entities[index].get("entity_id")
        if str(entity_id).startswith("std_"):
            removed_entity = entities.pop(index)
            break
    assert removed_entity is not None
    removed_entity_id = removed_entity.get("id") or removed_entity.get("entity_id")
    graph_path.write_text(json.dumps(graph, sort_keys=True), encoding="utf-8")

    materialized_path = bundle / "materialized_entities.json"
    materialized = json.loads(materialized_path.read_text(encoding="utf-8"))
    standards_materialization = next(
        row
        for row in materialized["materialization_rows"]
        if row.get("kind_id") == "standards"
    )
    standards_materialization["system_atlas_materialized_entity_count"] -= 1
    materialized_path.write_text(
        json.dumps(materialized, sort_keys=True),
        encoding="utf-8",
    )

    rows_path = bundle / "kind_atlas_rows.json"
    rows = json.loads(rows_path.read_text(encoding="utf-8"))
    standards_row = next(
        row for row in rows["rows"] if row.get("kind_id") == "standards"
    )
    standards_row["expected_entity_ids"].remove(removed_entity_id)
    standards_debt = next(
        row for row in rows["expected_known_debt"] if row.get("kind_id") == "standards"
    )
    standards_debt["expected_debt_count"] += 1
    rows_path.write_text(json.dumps(rows, sort_keys=True), encoding="utf-8")
    return removed_entity_id


def test_self_ignorance_static_fixture_blocks_without_real_graph(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/self_ignorance_coverage_ledger",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "CROWN_JEWEL_INPUT_MISSING" in result["error_codes"]
    assert "SELF_IGNORANCE_REAL_ATLAS_GRAPH_EMPTY" in result["error_codes"]


def test_self_ignorance_coverage_ledger_projects_real_bundle_known_debt(
    tmp_path: Path,
) -> None:
    result = run_self_ignorance_bundle(
        BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/self_ignorance_coverage_ledger",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["exercise"]["known_coverage_debt_count"] == 196
    assert result["exercise"]["known_coverage_debt_by_kind"] == {
        "concepts": 11,
        "mechanisms": 8,
        "paper_modules": 5,
        "standards": 172,
    }
    assert result["exercise"]["required_entity_count"] == 503
    assert result["exercise"]["expected_entity_id_count_by_kind"] == {
        "concepts": 30,
        "mechanisms": 28,
        "paper_modules": 220,
        "standards": 29,
    }
    assert result["exercise"]["materialized_entity_count"] == 307
    assert result["exercise"]["system_atlas_graph_materialization"]["entity_count"] == 307
    assert result["exercise"]["system_atlas_graph_ref"] == "system_atlas_graph.json"
    assert result["exercise"]["projection_protocol_receipt"] == {
        "body_in_receipt": False,
        "coverage_scope": "live_kind_atlas_vs_generated_system_atlas_materialization_snapshot",
        "status": "pass",
        "system_atlas_check_command": "./repo-python tools/meta/factory/build_system_atlas.py --check",
        "system_atlas_check_status": "blocked_source_inputs_changed_since_artifact_generation",
        "system_atlas_refresh_blocked_by_active_source_claims": True,
    }
    assert result["exercise"]["live_kind_atlas_recompute_used"] is True
    assert result["exercise"]["expected_entity_ids_source_backed"] is True
    assert result["exercise"]["realness_evidence"] == {
        "baked_expected_entity_ids_sufficient": False,
        "coverage_debt_recomputed_from_projection_counts": True,
        "kind_atlas_recompute_bound": True,
        "live_system_atlas_graph_crosscheck_bound": True,
        "rank_basis": [
            "live System Kind Atlas row counts",
            "build_system_atlas.py graph materialized entity ids",
            "live System Atlas graph cross-check when macro repo is available",
            "source-backed expected entity id provenance",
            "count-debt recompute from projection rows",
            "projection protocol build_system_atlas.py check receipt",
        ],
        "realness_rank": 4,
        "realness_rung": "R4",
        "rung_state": "real_kind_atlas_vs_system_atlas_projection_recompute",
        "source_backed_expected_entity_ids": True,
        "system_atlas_graph_materialization_bound": True,
    }
    assert result["exercise"]["kind_atlas_recompute"]["source"] == (
        "system.lib.kind_atlas.build_kind_atlas"
    )
    assert result["exercise"]["live_system_atlas_graph_crosscheck_used"] is True
    assert result["exercise"]["live_system_atlas_graph_materialization"][
        "source_ref"
    ] == "state/system_atlas/system_atlas.graph.json"
    assert result["exercise"]["live_system_atlas_graph_mismatches"] == {}
    assert result["exercise"]["live_kind_atlas_row_count_by_kind"] == {
        "concepts": 41,
        "mechanisms": 36,
        "paper_modules": 225,
        "standards": 201,
    }
    assert (
        result["exercise"]["copied_build_system_atlas_bundle_evidence"]["status"]
        == "present"
    )
    assert result["exercise"]["literal_unknown_unknown_omniscience_authorized"] is False
    assert (
        result["exercise"]["coverage_scope"]
        == "live_kind_atlas_vs_generated_system_atlas_materialization_snapshot"
    )
    assert result["exercise"]["system_atlas_refresh_blocked_by_active_source_claims"] is True
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True


def test_self_ignorance_coverage_ledger_projects_isolated_graph_as_r3(
    tmp_path: Path,
) -> None:
    bundle = _copy_public_bundle(tmp_path)

    result = evaluate(bundle, _public_root_for_bundle(bundle), {})

    assert result["status"] == "pass"
    assert result["known_coverage_debt_count"] == 196
    assert result["known_coverage_debt_by_kind"] == {
        "concepts": 11,
        "mechanisms": 8,
        "paper_modules": 5,
        "standards": 172,
    }
    assert result["system_atlas_graph_materialization"]["entity_count"] == 307
    assert result["kind_atlas_recompute"] == {
        "reason": "macro_kind_atlas_builder_not_available",
        "status": "unavailable",
        "used": False,
    }
    assert result["live_system_atlas_graph_crosscheck_used"] is False
    assert result["realness_evidence"]["realness_rank"] == 3
    assert result["realness_evidence"]["realness_rung"] == "R3"
    assert result["realness_evidence"]["kind_atlas_recompute_bound"] is False
    assert result["realness_evidence"]["system_atlas_graph_materialization_bound"] is True
    assert result["realness_evidence"]["live_system_atlas_graph_crosscheck_bound"] is False
    assert (
        result["realness_evidence"]["coverage_debt_recomputed_from_projection_counts"]
        is True
    )
    assert result["realness_evidence"]["baked_expected_entity_ids_sufficient"] is False


def test_self_ignorance_coverage_debt_moves_with_isolated_graph_r3(
    tmp_path: Path,
) -> None:
    bundle = _copy_public_bundle(tmp_path)
    removed_entity_id = _remove_materialized_standard_entity(bundle)

    result = evaluate(bundle, _public_root_for_bundle(bundle), {})

    assert removed_entity_id.startswith("std_")
    assert result["status"] == "pass"
    assert result["realness_evidence"]["realness_rung"] == "R3"
    assert result["known_coverage_debt_count"] == 197
    assert result["known_coverage_debt_by_kind"] == {
        "concepts": 11,
        "mechanisms": 8,
        "paper_modules": 5,
        "standards": 173,
    }
    assert result["materialized_entity_count"] == 306
    assert result["system_atlas_graph_materialization"]["entity_count"] == 306
    assert result["expected_entity_id_count_by_kind"]["standards"] == 28
    assert (
        result["fixture_declared_known_debt_floor_by_kind"]["standards"]
        == 173
    )


def test_self_ignorance_coverage_ledger_rejects_absence_omniscience(
    tmp_path: Path,
) -> None:
    bundle = _copy_public_bundle(tmp_path)
    rows_path = bundle / "kind_atlas_rows.json"
    rows = json.loads(rows_path.read_text(encoding="utf-8"))
    rows["absence_policy"]["claims_unknown_unknowns_exhaustive"] = True
    rows_path.write_text(json.dumps(rows, sort_keys=True), encoding="utf-8")

    result = run_self_ignorance_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/self_ignorance_coverage_ledger",
    )

    assert result["status"] == "blocked"
    assert "SELF_IGNORANCE_FORBIDDEN_ABSENCE_INFERENCE" in result["error_codes"]


def test_self_ignorance_coverage_ledger_rejects_coverage_debt_mismatch(
    tmp_path: Path,
) -> None:
    bundle = _copy_public_bundle(tmp_path)
    rows_path = bundle / "kind_atlas_rows.json"
    rows = json.loads(rows_path.read_text(encoding="utf-8"))
    rows["rows"][0]["expected_entity_ids"] = rows["rows"][0]["expected_entity_ids"][1:]
    rows_path.write_text(json.dumps(rows, sort_keys=True), encoding="utf-8")

    result = run_self_ignorance_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/self_ignorance_coverage_ledger",
    )

    assert result["status"] == "blocked"
    assert "SELF_IGNORANCE_EXPECTED_ENTITY_IDS_MISMATCH" in result["error_codes"]


def test_self_ignorance_coverage_ledger_rejects_baked_expected_ids_without_source(
    tmp_path: Path,
) -> None:
    bundle = _copy_public_bundle(tmp_path)
    rows_path = bundle / "kind_atlas_rows.json"
    rows = json.loads(rows_path.read_text(encoding="utf-8"))
    rows["materialized_entity_id_source_ref"] = "legacy_baked_expected_entity_ids"
    rows_path.write_text(json.dumps(rows, sort_keys=True), encoding="utf-8")

    result = run_self_ignorance_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/self_ignorance_coverage_ledger",
    )

    assert result["status"] == "blocked"
    assert (
        "SELF_IGNORANCE_EXPECTED_ENTITY_IDS_NOT_SOURCE_BACKED"
        in result["error_codes"]
    )
    assert result["exercise"]["realness_evidence"]["realness_rank"] == 3
    assert (
        result["exercise"]["realness_evidence"][
            "baked_expected_entity_ids_sufficient"
        ]
        is False
    )


def test_self_ignorance_coverage_ledger_rejects_declared_entity_id_substitution(
    tmp_path: Path,
) -> None:
    bundle = _copy_public_bundle(tmp_path)
    rows_path = bundle / "kind_atlas_rows.json"
    rows = json.loads(rows_path.read_text(encoding="utf-8"))
    first_row = rows["rows"][0]
    original_entity_id = first_row["expected_entity_ids"][0]
    first_row["expected_entity_ids"][0] = "concept_con_999999"
    rows_path.write_text(json.dumps(rows, sort_keys=True), encoding="utf-8")

    result = run_self_ignorance_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/self_ignorance_coverage_ledger",
    )

    assert result["status"] == "blocked"
    assert "SELF_IGNORANCE_EXPECTED_ENTITY_IDS_MISMATCH" in result["error_codes"]
    mismatches = result["exercise"]["expected_entity_id_mismatches"]["concepts"]
    assert mismatches["expected_entity_ids_missing_from_graph"] == ["concept_con_999999"]
    assert mismatches["graph_materialized_ids_missing_from_expected"] == [
        original_entity_id
    ]


def test_self_ignorance_coverage_ledger_rejects_materialized_count_tamper(
    tmp_path: Path,
) -> None:
    bundle = _copy_public_bundle(tmp_path)
    materialized_path = bundle / "materialized_entities.json"
    materialized = json.loads(materialized_path.read_text(encoding="utf-8"))
    materialized["materialization_rows"][0][
        "system_atlas_materialized_entity_count"
    ] += 1
    materialized_path.write_text(json.dumps(materialized, sort_keys=True), encoding="utf-8")

    result = run_self_ignorance_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/self_ignorance_coverage_ledger",
    )

    assert result["status"] == "blocked"
    assert "SELF_IGNORANCE_MATERIALIZATION_COUNT_NOT_GRAPH_DERIVED" in result["error_codes"]


def test_self_ignorance_coverage_ledger_rejects_graph_materialization_tamper(
    tmp_path: Path,
) -> None:
    bundle = _copy_public_bundle(tmp_path)
    graph_path = bundle / "system_atlas_graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    graph["entities"] = graph["entities"][:-1]
    graph_path.write_text(json.dumps(graph, sort_keys=True), encoding="utf-8")

    result = run_self_ignorance_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/self_ignorance_coverage_ledger",
    )

    assert result["status"] == "blocked"
    assert "SELF_IGNORANCE_EXPECTED_ENTITY_IDS_MISMATCH" in result["error_codes"]
    assert result["exercise"]["known_coverage_debt_count"] == 197
    assert result["exercise"]["known_coverage_debt_by_kind"] == {
        "concepts": 11,
        "mechanisms": 8,
        "paper_modules": 5,
        "standards": 173,
    }


def test_self_ignorance_coverage_debt_moves_with_materialized_entity_graph(
    tmp_path: Path,
) -> None:
    baseline = run_self_ignorance_bundle(
        BUNDLE_INPUT,
        tmp_path / "receipts/baseline/organs/self_ignorance_coverage_ledger",
        command="pytest",
    )

    bundle = _copy_public_bundle(tmp_path)
    _materialize_real_standard_entity(bundle, "std_agent_entry_surface")

    result = run_self_ignorance_bundle(
        bundle,
        tmp_path / "receipts/mutated/organs/self_ignorance_coverage_ledger",
        command="pytest",
    )

    assert baseline["status"] == "pass"
    assert baseline["exercise"]["known_coverage_debt_count"] == 196
    assert result["status"] == "pass"
    assert all(
        row.get("error_code") != "SELF_IGNORANCE_COVERAGE_DEBT_MISMATCH"
        for row in result["exercise"].get("findings", [])
    )
    assert result["exercise"]["known_coverage_debt_count"] == 195
    assert result["exercise"]["known_coverage_debt_by_kind"] == {
        "concepts": 11,
        "mechanisms": 8,
        "paper_modules": 5,
        "standards": 171,
    }
    assert result["exercise"]["materialized_entity_count"] == 308
    assert result["exercise"]["system_atlas_graph_materialization"]["entity_count"] == 308
    assert result["exercise"]["expected_entity_id_count_by_kind"]["standards"] == 30
    assert (
        result["exercise"]["fixture_declared_known_debt_floor_by_kind"]["standards"]
        == 171
    )


def test_self_ignorance_coverage_ledger_rejects_coherent_fake_standard_entity(
    tmp_path: Path,
) -> None:
    bundle = _copy_public_bundle(tmp_path)
    _materialize_standard_entity(
        bundle,
        "std_materialized_perturbation_probe",
        require_source=False,
    )

    result = run_self_ignorance_bundle(
        bundle,
        tmp_path / "receipts/fake_standard/organs/self_ignorance_coverage_ledger",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert (
        "SELF_IGNORANCE_EXPECTED_ENTITY_ID_SOURCE_MISSING"
        in result["error_codes"]
    )
    assert result["exercise"]["known_coverage_debt_count"] == 195
    assert result["exercise"]["expected_entity_id_source_validation"][
        "unsupported_entity_ids"
    ] == {"standards": ["std_materialized_perturbation_probe"]}


def test_self_ignorance_coverage_ledger_rejects_graph_builder_tamper(
    tmp_path: Path,
) -> None:
    bundle = _copy_public_bundle(tmp_path)
    graph_path = bundle / "system_atlas_graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    graph["generated_by"] = "legacy_fixture_writer.py"
    graph_path.write_text(json.dumps(graph, sort_keys=True), encoding="utf-8")

    result = run_self_ignorance_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/self_ignorance_coverage_ledger",
    )

    assert result["status"] == "blocked"
    assert "SELF_IGNORANCE_ATLAS_GRAPH_BUILDER_MISMATCH" in result["error_codes"]
    assert (
        "SELF_IGNORANCE_EXPECTED_ENTITY_IDS_NOT_SOURCE_BACKED"
        in result["error_codes"]
    )


def test_self_ignorance_coverage_ledger_rejects_projection_scope_tamper(
    tmp_path: Path,
) -> None:
    bundle = _copy_public_bundle(tmp_path)
    protocol_path = bundle / "projection_protocol.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    protocol["coverage_scope"] = "hand_authored_demo_kind_rows"
    protocol_path.write_text(json.dumps(protocol, sort_keys=True), encoding="utf-8")

    result = run_self_ignorance_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/self_ignorance_coverage_ledger",
    )

    assert result["status"] == "blocked"
    assert (
        "SELF_IGNORANCE_PROJECTION_PROTOCOL_SCOPE_MISMATCH"
        in result["error_codes"]
    )
    assert result["exercise"]["realness_evidence"]["realness_rank"] == 3


def test_self_ignorance_coverage_ledger_rejects_system_atlas_receipt_tamper(
    tmp_path: Path,
) -> None:
    bundle = _copy_public_bundle(tmp_path)
    protocol_path = bundle / "projection_protocol.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    protocol["system_atlas_check_command"] = "python legacy_fixture_writer.py"
    protocol["system_atlas_check_status"] = "not_run"
    protocol_path.write_text(json.dumps(protocol, sort_keys=True), encoding="utf-8")

    result = run_self_ignorance_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/self_ignorance_coverage_ledger",
    )

    assert result["status"] == "blocked"
    assert (
        "SELF_IGNORANCE_SYSTEM_ATLAS_CHECK_RECEIPT_INVALID"
        in result["error_codes"]
    )
    assert result["exercise"]["projection_protocol_receipt"]["status"] == "blocked"
    assert result["exercise"]["realness_evidence"]["realness_rank"] == 3


def test_self_ignorance_negative_cases_are_semantic_not_declared_labels(
    tmp_path: Path,
) -> None:
    bundle = _copy_public_bundle(tmp_path)
    for name in (
        "forbidden_absence_inference.json",
        "coverage_debt_mismatch.json",
    ):
        case_path = bundle / name
        payload = json.loads(case_path.read_text(encoding="utf-8"))
        payload["status"] = "pass"
        payload["error_codes"] = ["BOGUS_DECLARED_ERROR"]
        case_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    result = run_self_ignorance_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/self_ignorance_coverage_ledger",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["semantic_negative_case_evaluator_used"] is True
    assert all(
        row["semantic_evaluator_used"] for row in result["negative_case_semantics"]
    )
    assert "BOGUS_DECLARED_ERROR" not in result["error_codes"]
    assert "SELF_IGNORANCE_FORBIDDEN_ABSENCE_INFERENCE" in result["error_codes"]
    assert "SELF_IGNORANCE_COVERAGE_DEBT_MISMATCH" in result["error_codes"]


def test_self_ignorance_bundle_runs(tmp_path: Path) -> None:
    result = run_self_ignorance_bundle(
        BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/self_ignorance_coverage_ledger",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["exercise"]["known_coverage_debt_count"] == 196
    assert result["exercise"]["known_coverage_debt_by_kind"] == {
        "concepts": 11,
        "mechanisms": 8,
        "paper_modules": 5,
        "standards": 172,
    }
    assert result["exercise"]["live_kind_atlas_recompute_used"] is True
    assert result["exercise"]["realness_evidence"]["realness_rung"] == "R4"
    assert result["input_mode"] == "exported_self_ignorance_coverage_ledger_bundle"


def test_self_ignorance_bundle_source_module_is_public_safe_sanitized() -> None:
    manifest = json.loads((BUNDLE_INPUT / "source_module_manifest.json").read_text())
    module = manifest["modules"][0]

    assert module["module_id"] == "build_system_atlas_public_safe_body_import"
    assert module["source_to_target_relation"] == (
        "source_faithful_public_safe_path_normalized_copy"
    )
    assert module["source_ref"] == "tools/meta/factory/build_system_atlas.py"
    assert module["original_source_ref"] == "tools/meta/factory/build_system_atlas.py"
    assert module["original_source_sha256"]
    assert module["source_sha256"] == module["original_source_sha256"]
    assert module["target_sha256"] == module["sha256"]
    assert module["source_sha256"] != module["target_sha256"]
    assert module["source_target_sha256_match"] is False
    assert module["target_expected_digest_match"] is True
    assert module["public_safe_mode"] == "verified_public_macro_body_light_edit"
    assert module["public_safe_transform"]["public_safe"] is True
    assert {
        item["treatment_class"] for item in module["public_safe_transform"]["replacements"]
    } >= {
        "private_raw_seed_root_transform",
        "private_macro_source_ref_transform",
    }

    blocked_tokens = (
        "obsidian/okay lets do this",
        "self-indexing-cognitive-substrate",
    )
    for path in BUNDLE_INPUT.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for token in blocked_tokens:
            assert token not in text, path


def test_self_ignorance_bundle_rejects_stale_copied_target_source_ref(
    tmp_path: Path,
) -> None:
    bundle = _copy_public_bundle(tmp_path)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    module = manifest["modules"][0]
    module["source_ref"] = module["target_ref"]
    module["source_sha256"] = module["target_sha256"]
    module["source_to_target_relation"] = "public_bound_sanitized_source_authority_self_ref"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_self_ignorance_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/self_ignorance_coverage_ledger",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_SELF_REFERENCE_UNVERIFIED" in result["error_codes"]


def test_self_ignorance_bundle_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/self_ignorance_coverage_ledger/"
        "exported_self_ignorance_coverage_ledger_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_self_ignorance_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/self_ignorance_coverage_ledger",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False
