from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from microcosm_core import cli
from microcosm_core.projections import organ_surface_contract


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _accepted_organ_count() -> int:
    return len(_accepted_registry_rows())


def test_claim_assurance_covers_every_native_component_without_implying_proof() -> None:
    payload = organ_surface_contract.build_organ_surface_contract(MICROCOSM_ROOT)
    assurance = payload["claim_assurance"]
    assert assurance["component_count"] == _accepted_organ_count()
    assert assurance["runtime_input_present_count"] == _accepted_organ_count()
    assert sum(assurance["evidence_class_counts"].values()) == _accepted_organ_count()
    assert assurance["replay_status"] == "not_run"
    for row in payload["rows"]:
        evidence = row["claim_assurance"]
        assert evidence["evidence_class"]
        assert evidence["claim_ceiling"]
        assert (MICROCOSM_ROOT / evidence["runtime_input_ref"]).is_dir()
        assert evidence["recorded_evidence_freshness"] == "not_checked"
        assert evidence["formal_proof_of_component_correctness"] == "not_established_by_this_audit"
        assert evidence["replay"] == {"status": "not_run"}


def test_replay_preserves_failures_and_continues_to_every_component(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "checkout/fixture").mkdir(parents=True)
    from microcosm_core import runtime_shell

    def passing(input_dir, out, command):
        out.mkdir(parents=True)
        (out / "result.json").write_text(json.dumps({"status":"pass", "organ_id":out.name}))
        return {"status": "pass", "organ_id": out.name}

    def blocked(input_dir, out, command):
        return {"status": "blocked", "error_codes": ["MISSING_DEPENDENCY"]}

    def broken(input_dir, out, command):
        raise RuntimeError("private body must not reach the report")

    monkeypatch.setattr(runtime_shell, "RUNTIME_STEPS", tuple(
        SimpleNamespace(organ_id=name, example_rel="fixture", receipt_name="result.json", runner=runner)
        for name, runner in [("good", passing), ("blocked", blocked), ("broken", broken)]
    ))
    rows = [{"organ_id": name, "claim_assurance": {}} for name in ["good", "blocked", "broken"]]
    result = organ_surface_contract.replay_organ_surfaces(tmp_path / "checkout", tmp_path / "out", rows)
    assert result["status"] == "blocked"
    assert result["status_counts"] == {"blocked": 1, "exception": 1, "pass": 1}
    assert rows[1]["claim_assurance"]["replay"]["error_codes"] == ["MISSING_DEPENDENCY"]
    assert rows[2]["claim_assurance"]["replay"]["exception_type"] == "RuntimeError"
    assert "private body" not in json.dumps(rows)


def test_replay_refuses_checkout_source_and_historical_receipt_outputs(tmp_path: Path) -> None:
    for target in [tmp_path, tmp_path / "receipts", tmp_path / "examples"]:
        with pytest.raises(ValueError, match="output"):
            organ_surface_contract.replay_organ_surfaces(tmp_path, target, [])


@pytest.mark.parametrize("receipt", [
    '{"status":"blocked"}', '{"status":"pass","organ_id":"another"}',
    '{"status":"pass","organ_id":null}', '{}', '[]', 'not JSON',
])
def test_replay_rejects_wrong_or_malformed_written_verdict(tmp_path, monkeypatch, receipt):
    (tmp_path / "checkout/input").mkdir(parents=True)
    from microcosm_core import runtime_shell

    def runner(source, out, command):
        out.mkdir(parents=True)
        (out / "result.json").write_text(receipt)
        return {"status": "pass", "organ_id": "probe"}

    monkeypatch.setattr(runtime_shell, "RUNTIME_STEPS", (
        SimpleNamespace(organ_id="probe", example_rel="input", receipt_name="result.json", runner=runner),))
    rows = [{"organ_id": "probe", "claim_assurance": {}}]
    result = organ_surface_contract.replay_organ_surfaces(tmp_path / "checkout", tmp_path / "out", rows)
    assert result["status"] == "blocked"
    assert rows[0]["claim_assurance"]["replay"]["status"] == "exception"
    assert receipt not in json.dumps(rows)


def test_replay_cannot_reuse_a_previous_receipt_as_fresh_output(tmp_path, monkeypatch):
    (tmp_path / "checkout/input").mkdir(parents=True)
    from microcosm_core import runtime_shell

    def write(source, out, command):
        out.mkdir(parents=True)
        (out / "result.json").write_text(json.dumps({"status":"pass", "organ_id":out.name}))
        return {"status": "pass", "organ_id": out.name}

    step = SimpleNamespace(organ_id="probe", example_rel="input", receipt_name="result.json", runner=write)
    monkeypatch.setattr(runtime_shell, "RUNTIME_STEPS", (step,))
    first = [{"organ_id": "probe", "claim_assurance": {}}]
    organ_surface_contract.replay_organ_surfaces(tmp_path / "checkout", tmp_path / "out", first)
    original = Path(first[0]["claim_assurance"]["replay"]["receipt_ref"])
    step.runner = lambda *args: {"status": "pass", "organ_id": "probe"}
    second = [{"organ_id": "probe", "claim_assurance": {}}]
    result = organ_surface_contract.replay_organ_surfaces(tmp_path / "checkout", tmp_path / "out", second)
    assert result["status"] == "blocked"
    replay = second[0]["claim_assurance"]["replay"]
    assert replay["status"] == "missing_replay_receipt"
    assert Path(replay["receipt_ref"]) != original
    assert json.loads(original.read_text()) == {"status": "pass", "organ_id": "probe"}


def test_surface_replay_uses_shared_input_mutation_admission(tmp_path, monkeypatch):
    from microcosm_core import runtime_shell
    source = tmp_path / "checkout/input"
    source.mkdir(parents=True)
    (source / "data").write_text("original")

    def runner(input_dir, out, command):
        (input_dir / "data").write_text("changed")
        out.mkdir(parents=True)
        result = {"status": "pass", "organ_id": "probe"}
        (out / "result.json").write_text(json.dumps(result))
        return result

    monkeypatch.setattr(runtime_shell, "RUNTIME_STEPS", (
        SimpleNamespace(organ_id="probe", example_rel="input", receipt_name="result.json", runner=runner),))
    rows = [{"organ_id": "probe", "claim_assurance": {}}]
    result = organ_surface_contract.replay_organ_surfaces(tmp_path / "checkout", tmp_path / "out", rows)
    assert result["status"] == "blocked"
    assert result["admission"]["accepted"] is False
    assert rows[0]["claim_assurance"]["replay"]["status"] == "input_changed"


def test_surface_replay_rejects_empty_selection(tmp_path):
    (tmp_path / "checkout").mkdir()
    result = organ_surface_contract.replay_organ_surfaces(tmp_path / "checkout", tmp_path / "out", [])
    assert result["status"] == "blocked"
    assert result["component_count"] == 0


def test_native_replay_selects_live_lean_lab_without_changing_compatibility_default():
    from microcosm_core import runtime_shell
    from microcosm_core.organs import lean_proof_search_lab_runtime as lab

    declared = next(step for step in runtime_shell.RUNTIME_STEPS if step.organ_id == lab.ORGAN_ID)
    compatibility_runner = declared.runner
    native = organ_surface_contract.native_replay_step(declared)
    assert native.runner is lab.run
    assert native.example_rel == "fixtures/first_wave/lean_proof_search_lab_runtime/input"
    assert declared.runner is compatibility_runner
    assert declared.runner.__name__ == lab.run_lean_proof_search_lab_runtime_bundle.__name__
    assert declared.example_rel.startswith("examples/")
    assert organ_surface_contract.replay_verdict(native, {"status": "pass"}) == "missing_native_lean_witness"


def test_native_replay_selects_live_lake_witness_without_changing_compatibility_default():
    from microcosm_core import runtime_shell
    from microcosm_core.organs import formal_math_lean_proof_witness as witness

    declared = next(step for step in runtime_shell.RUNTIME_STEPS if step.organ_id == witness.ORGAN_ID)
    native = organ_surface_contract.native_replay_step(declared)
    assert native.runner is witness.run
    assert native.receipt_name == witness.RESULT_NAME
    assert native.example_rel == "fixtures/first_wave/formal_math_lean_proof_witness/input"
    assert declared.runner.__name__ == witness.run_witness_bundle.__name__
    assert declared.example_rel.startswith("examples/")
    assert organ_surface_contract.replay_verdict(native, {"status": "pass"}) == "missing_native_lean_lake_witness"


@pytest.mark.parametrize("mutation", ["blocked", "wrong_component", "missing_identity", "null_identity"])
def test_current_receipt_invalid_status_or_identity_blocks_surface_audit(monkeypatch, mutation):
    registry = json.loads((MICROCOSM_ROOT / "core/organ_registry.json").read_text())
    row = organ_surface_contract._accepted_registry_rows(registry)[0]
    target = MICROCOSM_ROOT / row["current_authority_receipt"]
    original = organ_surface_contract.read_json_strict

    def altered(path):
        payload = original(path)
        if Path(path) == target:
            payload = dict(payload)
            if mutation == "blocked":
                payload["status"] = "blocked"
            elif mutation == "missing_identity":
                payload.pop("organ_id")
            else:
                payload["organ_id"] = None if mutation == "null_identity" else "another_component"
        return payload

    monkeypatch.setattr(organ_surface_contract, "read_json_strict", altered)
    payload = organ_surface_contract.build_organ_surface_contract(MICROCOSM_ROOT)
    observed = next(item for item in payload["rows"] if item["organ_id"] == row["organ_id"])
    assert observed["current_authority_receipt_status"] == (
        "blocked" if mutation == "blocked" else "wrong_component")
    assert observed["checks"]["current_authority_receipt"] is False
    assert payload["status"] == "blocked"


@pytest.mark.parametrize("identity", ["another", None, "missing"])
def test_public_runtime_index_does_not_adopt_unbound_passing_receipts(tmp_path, monkeypatch, identity):
    from microcosm_core import runtime_shell

    (tmp_path / "core/fixture_manifests").mkdir(parents=True)
    (tmp_path / "fixture").mkdir()
    forged = {"status": "pass"}
    if identity != "missing":
        forged["organ_id"] = identity
    (tmp_path / "forged.json").write_text(json.dumps(forged))
    (tmp_path / "correct.json").write_text('{"status":"pass","organ_id":"one"}')
    registry = {"implemented_organs": [{
        "organ_id": "one", "status": "accepted_current_authority", "validator_command": "python -m one",
        "current_authority_receipt": "forged.json", "generated_receipts": ["forged.json", "correct.json"]}]}
    path = tmp_path / "core/organ_registry.json"
    path.write_text(json.dumps(registry))
    monkeypatch.setattr(runtime_shell, "RUNTIME_STEPS", (
        SimpleNamespace(organ_id="one", example_rel="fixture"),))
    organ_surface_contract.refresh_public_runtime_index(tmp_path)
    row = json.loads(path.read_text())["implemented_organs"][0]
    assert row["current_authority_receipt"] == "correct.json"
    assert row["historical_source_authority_receipt"] == "forged.json"


def test_acceptance_refresh_updates_only_current_evidence_fields(tmp_path: Path) -> None:
    (tmp_path / "core/acceptance").mkdir(parents=True)
    source = {"class_profiles": {"semantic_validator": {
        "counts_as_real_substrate_progress": True, "truth_accounting_bucket": "real_import_validation",
    }}, "organ_evidence_classes": [{"organ_id": "one", "evidence_class": "semantic_validator"}]}
    (tmp_path / "core/organ_evidence_classes.json").write_text(json.dumps(source))
    path = tmp_path / organ_surface_contract.ACCEPTANCE_PLAN_REF
    path.write_text(json.dumps({"accepted_current_authority_organs": [{
        "organ_id": "one", "evidence_class": "old", "historical_receipt": "keep.json",
    }], "acceptance_commands": ["preserve command"]}))
    assert organ_surface_contract.refresh_acceptance_evidence(tmp_path) == ["one"]
    refreshed = json.loads(path.read_text())
    assert refreshed["accepted_current_authority_organs"][0]["historical_receipt"] == "keep.json"
    assert refreshed["acceptance_commands"] == ["preserve command"]
    assert organ_surface_contract.refresh_acceptance_evidence(tmp_path) == []


def test_current_runtime_index_preserves_provenance_and_requires_passing_public_evidence(tmp_path: Path, monkeypatch) -> None:
    from microcosm_core import runtime_shell

    (tmp_path / "core/fixture_manifests").mkdir(parents=True)
    (tmp_path / "fixture").mkdir()
    (tmp_path / "receipt.json").write_text('{"organ_id":"one","status":"blocked"}')
    path = tmp_path / "core/organ_registry.json"
    path.write_text(json.dumps({"implemented_organs": [{
        "organ_id": "one", "status": "accepted_current_authority", "validator_command": "python -m one",
        "current_authority_receipt": "state/old.json", "generated_receipts": ["receipt.json"],
    }]}))
    monkeypatch.setattr(runtime_shell, "RUNTIME_STEPS", (SimpleNamespace(organ_id="one", example_rel="fixture"),))
    result = organ_surface_contract.refresh_public_runtime_index(tmp_path)
    assert result == {"created_fixture_manifests": ["one"], "rebound_public_receipt_refs": []}
    assert json.loads(path.read_text())["implemented_organs"][0]["current_authority_receipt"] == "state/old.json"
    (tmp_path / "receipt.json").write_text('{"organ_id":"one","status":"pass"}')
    result = organ_surface_contract.refresh_public_runtime_index(tmp_path)
    assert result == {"created_fixture_manifests": [], "rebound_public_receipt_refs": ["one"]}
    row = json.loads(path.read_text())["implemented_organs"][0]
    assert row["historical_source_authority_receipt"] == "state/old.json"
    assert row["current_authority_receipt"] == "receipt.json"
    manifest = tmp_path / "core/fixture_manifests/one.fixture_manifest.json"
    before = manifest.read_bytes()
    organ_surface_contract.refresh_public_runtime_index(tmp_path)
    assert manifest.read_bytes() == before


def test_new_root_runtime_alias_executes_and_rejects_forged_certificates(tmp_path: Path) -> None:
    code = cli.main([
        "finite-erdos-denominator-certificate-strike", "run",
        "--input", str(MICROCOSM_ROOT / "fixtures/first_wave/finite_erdos_denominator_certificate_strike/input"),
        "--out", str(tmp_path),
    ])
    assert code == 0
    result = json.loads((tmp_path / "finite_erdos_denominator_certificate_strike_result.json").read_text())
    assert result["passed_positive_case_count"] == 2
    assert result["observed_negative_case_count"] == 2


def _accepted_registry_rows() -> list[dict[str, object]]:
    registry = json.loads(
        (MICROCOSM_ROOT / "core/organ_registry.json").read_text(encoding="utf-8")
    )
    return [
        row
        for row in registry["implemented_organs"]
        if row.get("status") == "accepted_current_authority"
    ]


def _synthetic_accepted_count() -> int:
    return sum(
        1
        for row in _accepted_registry_rows()
        if organ_surface_contract._is_synthetic_acceptance_row(row)
    )


def _disposition_count(disposition: str) -> int:
    return sum(
        1
        for row in _accepted_registry_rows()
        if row.get("real_substrate_disposition") == disposition
    )


def _atlas_wires_to(organ_id: str) -> set[str]:
    atlas = json.loads(
        (MICROCOSM_ROOT / "core/organ_atlas.json").read_text(encoding="utf-8")
    )
    row = next(item for item in atlas["organs"] if item["organ_id"] == organ_id)
    return set(row.get("wires_to", []))


def test_source_language_queries_use_actual_sources_and_ignore_bytecode(tmp_path: Path) -> None:
    sources = tmp_path / "examples/toy/source_modules"
    sources.mkdir(parents=True)
    (sources / "one.py").write_text("value = 1\n")
    (sources / "two.ts").write_text("export const value: number = 1;\n")
    (sources / "three.mjs").write_text("export const value = 1;\n")
    (sources / "__pycache__").mkdir()
    (sources / "__pycache__/one.cpython-312.pyc").write_bytes(b"generated bytecode")
    inventory = organ_surface_contract._source_language_inventory(tmp_path, ["toy"])
    assert inventory["by_organ"]["toy"]["source_module_file_count"] == 3
    assert set(inventory["by_organ"]["toy"]["language_families"]) == {"python", "typescript", "javascript"}
    adjacency = organ_surface_contract._source_language_adjacency(inventory)
    assert adjacency["query_affordances"]["python_typescript_javascript_organs"] == ["toy"]


def test_organ_surface_contract_tracks_live_accepted_organs() -> None:
    payload = organ_surface_contract.build_organ_surface_contract(MICROCOSM_ROOT)

    assert payload["status"] == "pass"
    assert payload["authority_posture"] == "derived_surface_audit_not_source_authority"
    assert payload["accepted_organ_count"] == _accepted_organ_count()
    assert len(payload["rows"]) == payload["accepted_organ_count"]
    assert all(not values for values in payload["coverage"]["missing"].values())
    rows_by_id = {row["organ_id"]: row for row in payload["rows"]}
    for organ_id in {
        "batch5_authority_systems_capsule",
        "batch7_demo_take_console_capsule",
        "batch7_oracle_sibling_capsule",
        "batch7_secondary_runtime_capsule",
    }:
        assert rows_by_id[organ_id]["checks"]["runtime_step"] is True
        assert rows_by_id[organ_id]["checks"]["cli_command"] is True
    assert payload["global_doctrine_surfaces"]["status"] == "pass"
    assert payload["coverage"]["organ_doctrine_row_count"] == _accepted_organ_count()
    assert payload["coverage"]["acceptance_plan_row_count"] == _accepted_organ_count()
    assert payload["coverage"]["acceptance_plan_order_matches_registry"] is True
    assert payload["coverage"]["unexpected_acceptance_plan_rows"] == []
    disposition_coverage = payload["coverage"]["disposition_coverage"]
    assert disposition_coverage["covered_count"] == _accepted_organ_count()
    assert disposition_coverage["synthetic_accepted_count"] == (
        _synthetic_accepted_count()
    )
    assert disposition_coverage["real_substrate_capsule_count"] == (
        _disposition_count("real_substrate_capsule")
    )
    assert disposition_coverage["retained_regression_validator_count"] == (
        _disposition_count("retained_regression_validator")
    )
    assert (
        disposition_coverage["missing_synthetic_acceptance_dispositions"] == []
    )
    assert (
        disposition_coverage["invalid_synthetic_acceptance_disposition"] == []
    )
    assert (
        disposition_coverage["synthetic_acceptance_progress_flag_mismatch"] == []
    )
    assert disposition_coverage["registry_acceptance_disposition_mismatch"] == []
    acceptance_metadata_coverage = payload["coverage"][
        "acceptance_metadata_coverage"
    ]
    assert acceptance_metadata_coverage["covered_count"] == _accepted_organ_count()
    assert acceptance_metadata_coverage["checked_fields"] == [
        "evidence_class",
        "counts_as_real_substrate_progress",
        "truth_accounting_bucket",
    ]
    assert acceptance_metadata_coverage[
        "missing_acceptance_metadata_fields"
    ] == []
    assert acceptance_metadata_coverage[
        "registry_acceptance_metadata_mismatch"
    ] == []
    source_language_inventory = payload["coverage"]["source_language_inventory"]
    assert source_language_inventory["schema_version"] == (
        "microcosm_source_language_inventory_v0"
    )
    assert source_language_inventory["accepted_organ_count"] == _accepted_organ_count()
    assert source_language_inventory["source_module_organ_count"] > 0
    assert (
        len(source_language_inventory["accepted_without_source_modules"])
        < _accepted_organ_count()
    )
    assert "bridge_phase_continuity_runtime" not in source_language_inventory[
        "accepted_without_source_modules"
    ]
    bridge_inventory = next(
        row["source_language_inventory"]
        for row in payload["rows"]
        if row["organ_id"] == "bridge_phase_continuity_runtime"
    )
    assert bridge_inventory["source_module_file_count"] == 5
    assert bridge_inventory["language_counts"]["python"] == 5
    assert "not_language_standard" in source_language_inventory["authority"]
    for language in ("python", "typescript", "javascript", "json", "lean", "swift"):
        assert source_language_inventory["language_counts"][language] > 0
        assert source_language_inventory["organs_by_language"][language]
    source_language_adjacency = payload["coverage"]["source_language_adjacency"]
    assert source_language_adjacency["schema_version"] == (
        "microcosm_source_language_adjacency_v0"
    )
    assert source_language_adjacency["source_inventory_schema_version"] == (
        source_language_inventory["schema_version"]
    )
    assert "not_source_semantics" in source_language_adjacency["authority"]
    assert "not_lattice_authority" in source_language_adjacency["authority"]
    query_affordances = source_language_adjacency["query_affordances"]
    assert query_affordances["typescript_bearing_organs"] == (
        source_language_inventory["organs_by_language"]["typescript"]
    )
    assert query_affordances["accepted_without_source_modules"] == (
        source_language_inventory["accepted_without_source_modules"]
    )
    assert "batch7_macro_engines_capsule" not in query_affordances[
        "python_typescript_javascript_organs"
    ]
    adjacency_rows = source_language_adjacency["rows"]
    macro_engines_adjacency = adjacency_rows["batch7_macro_engines_capsule"]
    assert "batch7_macro_engines_capsule" not in macro_engines_adjacency[
        "shared_language_peer_organs"
    ]
    assert macro_engines_adjacency["shared_language_peer_organ_count"] > 0
    assert set(macro_engines_adjacency["peer_organs_by_language"]) >= {
        "javascript",
        "python",
    }
    source_module_file_graph = payload["coverage"]["source_module_file_graph"]
    assert source_module_file_graph["schema_version"] == (
        "microcosm_source_module_file_graph_v0"
    )
    assert source_module_file_graph["accepted_organ_count"] == (
        _accepted_organ_count()
    )
    assert source_module_file_graph["manifest_count"] > 0
    assert source_module_file_graph["module_count"] > 0
    assert source_module_file_graph["source_ref_count"] > 0
    assert source_module_file_graph["target_ref_count"] > 0
    assert source_module_file_graph["validation_ref_count"] > 0
    assert source_module_file_graph["module_validation_ref_count"] > 0
    assert source_module_file_graph["required_anchor_count"] > 0
    assert source_module_file_graph["edge_count"] == len(
        source_module_file_graph["edges"]
    )
    assert "not_source_semantics" in source_module_file_graph["authority"]
    file_graph_relation_counts = source_module_file_graph[
        "relation_type_counts"
    ]
    assert file_graph_relation_counts[
        "source_file.copied_to_public_target"
    ] > 0
    assert file_graph_relation_counts["source_file.validated_by_ref"] > 0
    assert file_graph_relation_counts["target_file.validated_by_ref"] > 0
    assert file_graph_relation_counts[
        "target_file.shares_macro_source_with_target_file"
    ] > 0
    assert file_graph_relation_counts[
        "source_shard.retained_as_public_target_shard"
    ] > 0
    assert file_graph_relation_counts["source_shard.validated_by_ref"] > 0
    assert file_graph_relation_counts["target_shard.validated_by_ref"] > 0
    assert source_module_file_graph["query_affordances"][
        "shared_source_ref_count"
    ] > 0
    assert "bridge_phase_continuity_runtime" in source_module_file_graph[
        "query_affordances"
    ]["organs_with_source_module_manifests"]
    bridge_file_edges = [
        edge
        for edge in source_module_file_graph["edges"]
        if edge["organ_id"] == "bridge_phase_continuity_runtime"
        and edge["relation_type"] == "source_file.copied_to_public_target"
    ]
    assert len(bridge_file_edges) == 5
    assert any(
        edge["manifest_ref"].endswith("observe_runtime_source_module_manifest.json")
        and edge["source_ref"] == "system/lib/observe_runtime.py"
        and edge["target_ref"].endswith(
            "source_modules/system/lib/observe_runtime.py"
        )
        for edge in bridge_file_edges
    )
    agent_trace_file_edges = [
        edge
        for edge in source_module_file_graph["edges"]
        if edge["relation_type"] == "source_file.copied_to_public_target"
        and edge["source_ref"] == "system/lib/agent_execution_trace.py"
    ]
    assert agent_trace_file_edges
    assert any(
        edge["target_ref"].endswith("source_modules/system/lib/agent_execution_trace.py")
        for edge in agent_trace_file_edges
    )
    assert any(
        edge["relation_type"] == "source_shard.retained_as_public_target_shard"
        and edge["source_ref"] == "system/lib/agent_execution_trace.py"
        and edge["required_anchor"] == "def build_agent_execution_trace("
        for edge in source_module_file_graph["edges"]
    )
    assert any(
        edge["relation_type"] == "source_file.validated_by_ref"
        and edge["source_ref"] == "system/lib/agent_execution_trace.py"
        and edge["validation_ref"].endswith("macro_body_refactor")
        for edge in source_module_file_graph["edges"]
    )
    assert any(
        edge["relation_type"] == "source_shard.validated_by_ref"
        and edge["source_ref"] == "system/lib/agent_execution_trace.py"
        and edge["required_anchor"] == "def build_agent_execution_trace("
        and edge["validation_ref"].endswith("macro_body_refactor")
        for edge in source_module_file_graph["edges"]
    )
    organ_relationship_topology = payload["coverage"][
        "organ_relationship_topology"
    ]
    assert organ_relationship_topology["schema_version"] == (
        "microcosm_organ_relationship_topology_v0"
    )
    assert organ_relationship_topology["source"] == {
        "organ_rows": "rows",
        "source_language_adjacency": "coverage.source_language_adjacency",
        "organ_atlas_wiring": "rows[].wires_to",
        "source_module_file_graph": "coverage.source_module_file_graph",
    }
    assert organ_relationship_topology["accepted_organ_count"] == (
        _accepted_organ_count()
    )
    assert organ_relationship_topology["edge_count"] == len(
        organ_relationship_topology["edges"]
    )
    assert "not_duplicate_source_scan" in organ_relationship_topology["authority"]
    assert "not_lattice_authority" in organ_relationship_topology["authority"]
    relation_type_counts = organ_relationship_topology["relation_type_counts"]
    for relation_type in (
        "organ.has_source_language_family",
        "organ.shares_source_language_family_with",
        "organ.has_mixed_source_language_families",
        "organ.has_microcosm_standard",
        "organ.has_standards_registry_row",
        "organ.has_concept_route_ref",
        "organ.has_mechanism_route_ref",
        "organ.wires_to.organ",
        "source_file.copied_to_public_target",
        "source_file.validated_by_ref",
        "target_file.shares_macro_source_with_target_file",
        "target_file.validated_by_ref",
        "source_shard.retained_as_public_target_shard",
        "source_shard.validated_by_ref",
        "target_shard.validated_by_ref",
    ):
        assert relation_type_counts[relation_type] > 0
    assert relation_type_counts["organ.has_microcosm_standard"] == (
        _accepted_organ_count()
    )
    assert relation_type_counts.get("organ.has_no_source_modules", 0) == len(
        organ_relationship_topology["query_affordances"][
            "accepted_without_source_modules"
        ]
    )
    for edge in organ_relationship_topology["edges"]:
        assert edge["evidence_class"]
        assert edge["source_projection"]
        assert edge["authority"] == organ_relationship_topology["authority"]
    macro_engines_edges = organ_relationship_topology["edges_by_organ"][
        "batch7_macro_engines_capsule"
    ]
    assert any(
        edge["relation_type"] == "organ.has_source_language_family"
        and edge["target_id"] == "source_language_family:javascript"
        for edge in macro_engines_edges
    )
    assert any(
        edge["relation_type"] == "organ.shares_source_language_family_with"
        for edge in macro_engines_edges
    )
    route_observability_edges = organ_relationship_topology["edges_by_organ"][
        "agent_route_observability_runtime"
    ]
    assert any(
        edge["relation_type"] == "organ.wires_to.organ"
        and edge["target_organ_id"] == "macro_projection_import_protocol"
        and edge["target_status"] == "accepted_current_authority"
        for edge in route_observability_edges
    )
    assert any(
        edge["relation_type"] == "organ.has_microcosm_standard"
        for edge in macro_engines_edges
    )
    assert any(
        edge["relation_type"] == "organ.has_concept_route_ref"
        for edge in macro_engines_edges
    )
    assert any(
        edge["relation_type"] == "organ.has_mechanism_route_ref"
        for edge in macro_engines_edges
    )
    bridge_edges = organ_relationship_topology["edges_by_organ"][
        "bridge_phase_continuity_runtime"
    ]
    assert any(
        edge["relation_type"] == "source_file.copied_to_public_target"
        and edge["manifest_ref"].endswith("observe_runtime_source_module_manifest.json")
        for edge in bridge_edges
    )
    assert not any(
        edge["relation_type"] == "organ.has_no_source_modules"
        for edge in bridge_edges
    )
    accepted_without_source_modules = organ_relationship_topology["query_affordances"][
        "accepted_without_source_modules"
    ]
    if accepted_without_source_modules:
        no_source_organ_id = accepted_without_source_modules[0]
        assert any(
            edge["relation_type"] == "organ.has_no_source_modules"
            for edge in organ_relationship_topology["edges_by_organ"][
                no_source_organ_id
            ]
        )
    else:
        assert not any(
            edge["relation_type"] == "organ.has_no_source_modules"
            for edge in organ_relationship_topology["edges"]
        )

    by_organ = {row["organ_id"]: row for row in payload["rows"]}
    assert by_organ["pattern_binding_contract"]["cli_command"] == (
        "pattern-route-readiness"
    )
    assert (
        by_organ["macro_projection_import_protocol"]["paper_module_ref"]
        == "paper_modules/macro_projection_import_protocol.md"
    )
    assert by_organ["pattern_assimilation_step"]["runner"] == (
        "microcosm_core.validators.acceptance"
    )
    assert by_organ["pattern_assimilation_step"]["acceptance_plan_ref"] == (
        "core/acceptance/first_wave_acceptance.json::"
        "accepted_current_authority_organs[organ_id=pattern_assimilation_step]"
    )
    assert by_organ["macro_projection_import_protocol"]["concept_projection_ref"].endswith(
        "[organ_id=macro_projection_import_protocol].concept_binding"
    )
    assert by_organ["macro_projection_import_protocol"][
        "mechanism_projection_ref"
    ].endswith("[organ_id=macro_projection_import_protocol].mechanism_binding")
    macro_engines_inventory = by_organ["batch7_macro_engines_capsule"][
        "source_language_inventory"
    ]
    assert macro_engines_inventory["source_module_file_count"] > 0
    assert set(macro_engines_inventory["language_families"]) == {
        "javascript",
        "python",
    }
    assert macro_engines_inventory["extension_counts"][".mjs"] > 0
    assert macro_engines_inventory["extension_counts"][".py"] > 0
    assert macro_engines_inventory["extension_counts"].get(".ts", 0) == 0
    for row in payload["rows"]:
        assert all(row["checks"].values()), row["organ_id"]
        assert row["real_substrate_disposition"] in {
            "real_substrate_capsule",
            "retained_regression_validator",
        }
        assert row["concept_mechanism_route_ref"] == (
            "atlas/entry_packet.json::concept_mechanism_entry_route"
        )


def test_organ_surface_contract_reports_exact_cli_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_commands = organ_surface_contract._cli_command_names(MICROCOSM_ROOT)
    reduced_commands = set(original_commands)
    reduced_commands.remove("macro-projection-import-protocol")
    monkeypatch.setattr(
        organ_surface_contract,
        "_cli_command_names",
        lambda root: reduced_commands,
    )

    payload = organ_surface_contract.build_organ_surface_contract(MICROCOSM_ROOT)

    assert payload["status"] == "blocked"
    assert payload["coverage"]["missing"]["cli_commands"] == [
        "macro_projection_import_protocol"
    ]
    assert {
        error["code"] for error in payload["errors"]
    } == {"missing_cli_commands"}


def test_organ_surface_contract_reports_exact_acceptance_plan_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_rows = organ_surface_contract._acceptance_plan_rows(MICROCOSM_ROOT)
    reduced_rows = [
        row
        for row in original_rows
        if row.get("organ_id") != "macro_projection_import_protocol"
    ]
    monkeypatch.setattr(
        organ_surface_contract,
        "_acceptance_plan_rows",
        lambda root: reduced_rows,
    )

    payload = organ_surface_contract.build_organ_surface_contract(MICROCOSM_ROOT)

    assert payload["status"] == "blocked"
    assert payload["coverage"]["missing"]["acceptance_plan_rows"] == [
        "macro_projection_import_protocol"
    ]
    assert {
        error["code"] for error in payload["errors"]
    } == {
        "acceptance_plan_order_mismatch",
        "missing_acceptance_plan_rows",
    }


def test_organ_surface_contract_reports_missing_synthetic_disposition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_organ_id = "macro_projection_import_protocol"
    original_rows = organ_surface_contract._accepted_registry_rows(
        json.loads(
            (MICROCOSM_ROOT / "core/organ_registry.json").read_text(
                encoding="utf-8"
            )
        )
    )
    reduced_rows = [dict(row) for row in original_rows]
    for row in reduced_rows:
        if row["organ_id"] == target_organ_id:
            row["evidence_class"] = "fixture_echo_smoke"
            row["truth_accounting_bucket"] = "regression_negative_fixture"
            row["counts_as_real_substrate_progress"] = False
            row["real_substrate_disposition"] = "retained_regression_validator"
            row.pop("synthetic_acceptance_disposition", None)
            break
    monkeypatch.setattr(
        organ_surface_contract,
        "_accepted_registry_rows",
        lambda registry: reduced_rows,
    )
    original_acceptance_rows = organ_surface_contract._acceptance_plan_rows(
        MICROCOSM_ROOT
    )
    acceptance_rows = [dict(row) for row in original_acceptance_rows]
    for row in acceptance_rows:
        if row["organ_id"] == target_organ_id:
            row["evidence_class"] = "fixture_echo_smoke"
            row["truth_accounting_bucket"] = "regression_negative_fixture"
            row["counts_as_real_substrate_progress"] = False
            row["real_substrate_disposition"] = "retained_regression_validator"
            row["synthetic_acceptance_disposition"] = (
                "retained_regression_validator"
            )
            break
    monkeypatch.setattr(
        organ_surface_contract,
        "_acceptance_plan_rows",
        lambda root: acceptance_rows,
    )

    payload = organ_surface_contract.build_organ_surface_contract(MICROCOSM_ROOT)

    assert payload["status"] == "blocked"
    assert payload["coverage"]["missing"]["synthetic_acceptance_dispositions"] == [
        target_organ_id
    ]
    assert {
        error["code"] for error in payload["errors"]
    } == {"missing_synthetic_acceptance_dispositions"}


def test_organ_surface_contract_reports_invalid_synthetic_disposition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_rows = organ_surface_contract._accepted_registry_rows(
        json.loads(
            (MICROCOSM_ROOT / "core/organ_registry.json").read_text(
                encoding="utf-8"
            )
        )
    )
    invalid_rows = [dict(row) for row in original_rows]
    for row in invalid_rows:
        if row["organ_id"] == "agent_monitor_redteam_falsification_replay":
            row["synthetic_acceptance_disposition"] = {
                "disposition": "real_substrate_capsule"
            }
            break
    monkeypatch.setattr(
        organ_surface_contract,
        "_accepted_registry_rows",
        lambda registry: invalid_rows,
    )

    payload = organ_surface_contract.build_organ_surface_contract(MICROCOSM_ROOT)

    assert payload["status"] == "blocked"
    assert payload["coverage"]["disposition_coverage"][
        "invalid_synthetic_acceptance_disposition"
    ] == ["agent_monitor_redteam_falsification_replay"]
    assert {
        error["code"] for error in payload["errors"]
    } == {"invalid_synthetic_acceptance_disposition"}


def test_organ_surface_contract_reports_fixture_progress_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_organ_id = "macro_projection_import_protocol"
    original_rows = organ_surface_contract._accepted_registry_rows(
        json.loads(
            (MICROCOSM_ROOT / "core/organ_registry.json").read_text(
                encoding="utf-8"
            )
        )
    )
    mismatched_rows = [dict(row) for row in original_rows]
    for row in mismatched_rows:
        if row["organ_id"] == target_organ_id:
            row["counts_as_real_substrate_progress"] = False
            row["synthetic_acceptance_disposition"] = (
                "retained_regression_validator"
            )
            break
    monkeypatch.setattr(
        organ_surface_contract,
        "_accepted_registry_rows",
        lambda registry: mismatched_rows,
    )
    original_acceptance_rows = organ_surface_contract._acceptance_plan_rows(
        MICROCOSM_ROOT
    )
    acceptance_rows = [dict(row) for row in original_acceptance_rows]
    for row in acceptance_rows:
        if row["organ_id"] == target_organ_id:
            row["counts_as_real_substrate_progress"] = False
            row["synthetic_acceptance_disposition"] = (
                "retained_regression_validator"
            )
            break
    monkeypatch.setattr(
        organ_surface_contract,
        "_acceptance_plan_rows",
        lambda root: acceptance_rows,
    )

    payload = organ_surface_contract.build_organ_surface_contract(MICROCOSM_ROOT)

    assert payload["status"] == "blocked"
    assert payload["coverage"]["disposition_coverage"][
        "synthetic_acceptance_progress_flag_mismatch"
    ] == [target_organ_id]
    assert {
        error["code"] for error in payload["errors"]
    } == {"synthetic_acceptance_progress_flag_mismatch"}


def test_organ_surface_contract_reports_registry_acceptance_metadata_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_rows = organ_surface_contract._acceptance_plan_rows(MICROCOSM_ROOT)
    mismatched_rows = [dict(row) for row in original_rows]
    for row in mismatched_rows:
        if row["organ_id"] == "macro_projection_import_protocol":
            row["evidence_class"] = "semantic_validator"
            break
    monkeypatch.setattr(
        organ_surface_contract,
        "_acceptance_plan_rows",
        lambda root: mismatched_rows,
    )

    payload = organ_surface_contract.build_organ_surface_contract(MICROCOSM_ROOT)

    assert payload["status"] == "blocked"
    assert payload["coverage"]["acceptance_metadata_coverage"][
        "registry_acceptance_metadata_mismatch"
    ] == ["macro_projection_import_protocol"]
    assert {
        error["code"] for error in payload["errors"]
    } == {"registry_acceptance_metadata_mismatch"}


def test_organ_surface_contract_reports_registry_acceptance_disposition_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_rows = organ_surface_contract._acceptance_plan_rows(MICROCOSM_ROOT)
    mismatched_rows = [dict(row) for row in original_rows]
    for row in mismatched_rows:
        if row["organ_id"] == "macro_projection_import_protocol":
            row["real_substrate_disposition"] = "retained_regression_validator"
            break
    monkeypatch.setattr(
        organ_surface_contract,
        "_acceptance_plan_rows",
        lambda root: mismatched_rows,
    )

    payload = organ_surface_contract.build_organ_surface_contract(MICROCOSM_ROOT)

    assert payload["status"] == "blocked"
    assert payload["coverage"]["disposition_coverage"][
        "registry_acceptance_disposition_mismatch"
    ] == ["macro_projection_import_protocol"]
    assert {
        error["code"] for error in payload["errors"]
    } == {"registry_acceptance_disposition_mismatch"}


def test_organ_surface_contract_cli_emits_compact_card(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(
        ["organ-surface-contract", "--card", "--root", str(MICROCOSM_ROOT)]
    )

    assert exit_code == 0
    card = json.loads(capsys.readouterr().out)
    assert card["schema_version"] == "microcosm_organ_surface_contract_card_v0"
    assert card["status"] == "pass"
    assert card["accepted_organ_count"] == _accepted_organ_count()
    assert card["missing_surface_counts"] == {}
    assert card["disposition_coverage"][
        "missing_synthetic_acceptance_dispositions"
    ] == []
    assert card["disposition_coverage"][
        "invalid_synthetic_acceptance_disposition"
    ] == []
    assert card["disposition_coverage"][
        "synthetic_acceptance_progress_flag_mismatch"
    ] == []
    assert card["disposition_coverage"][
        "registry_acceptance_disposition_mismatch"
    ] == []
    assert card["acceptance_metadata_coverage"][
        "missing_acceptance_metadata_fields"
    ] == []
    assert card["acceptance_metadata_coverage"][
        "registry_acceptance_metadata_mismatch"
    ] == []
    source_language_inventory = card["source_language_inventory"]
    assert source_language_inventory["schema_version"] == (
        "microcosm_source_language_inventory_v0"
    )
    assert source_language_inventory["accepted_organ_count"] == _accepted_organ_count()
    assert source_language_inventory["source_module_organ_count"] > 0
    assert source_language_inventory["accepted_without_source_modules_count"] < (
        _accepted_organ_count()
    )
    assert source_language_inventory["language_counts"]["python"] > 0
    assert source_language_inventory["language_counts"]["typescript"] > 0
    assert source_language_inventory["language_counts"]["javascript"] > 0
    assert "source_body_authority_or_comment_contract" in source_language_inventory[
        "authority"
    ]
    source_language_adjacency = card["source_language_adjacency"]
    assert source_language_adjacency["schema_version"] == (
        "microcosm_source_language_adjacency_v0"
    )
    assert source_language_adjacency["source_inventory_schema_version"] == (
        "microcosm_source_language_inventory_v0"
    )
    assert source_language_adjacency["source_module_organ_count"] == (
        source_language_inventory["source_module_organ_count"]
    )
    assert source_language_adjacency["language_family_organ_counts"][
        "typescript"
    ] == len(source_language_adjacency["typescript_bearing_organs"])
    assert "batch7_macro_engines_capsule" not in source_language_adjacency[
        "python_typescript_javascript_organs"
    ]
    assert "bridge_phase_continuity_runtime" not in source_language_adjacency[
        "accepted_without_source_modules"
    ]
    assert "not_lattice_authority" in source_language_adjacency["authority"]
    source_module_file_graph = card["source_module_file_graph"]
    assert source_module_file_graph["schema_version"] == (
        "microcosm_source_module_file_graph_v0"
    )
    assert source_module_file_graph["accepted_organ_count"] == (
        _accepted_organ_count()
    )
    assert source_module_file_graph["manifest_count"] > 0
    assert source_module_file_graph["module_count"] > 0
    assert source_module_file_graph["source_ref_count"] > 0
    assert source_module_file_graph["target_ref_count"] > 0
    assert source_module_file_graph["validation_ref_count"] > 0
    assert source_module_file_graph["module_validation_ref_count"] > 0
    assert source_module_file_graph["required_anchor_count"] > 0
    assert source_module_file_graph["relation_type_counts"][
        "source_file.copied_to_public_target"
    ] > 0
    assert source_module_file_graph["relation_type_counts"][
        "source_file.validated_by_ref"
    ] > 0
    assert source_module_file_graph["relation_type_counts"][
        "source_shard.retained_as_public_target_shard"
    ] > 0
    assert source_module_file_graph["relation_type_counts"][
        "source_shard.validated_by_ref"
    ] > 0
    assert source_module_file_graph["shared_source_ref_count"] > 0
    assert source_module_file_graph["top_validation_refs"]
    assert source_module_file_graph["preview_limit"] == 5
    assert len(source_module_file_graph["top_validation_refs"]) <= 5
    assert len(source_module_file_graph["top_shared_source_refs"]) <= 5
    assert source_module_file_graph["top_validation_refs_omitted_count"] > 0
    assert source_module_file_graph["top_shared_source_refs_omitted_count"] > 0
    assert "not_source_semantics" in source_module_file_graph["authority"]
    organ_relationship_topology = card["organ_relationship_topology"]
    assert organ_relationship_topology["schema_version"] == (
        "microcosm_organ_relationship_topology_v0"
    )
    assert organ_relationship_topology["source"] == {
        "organ_rows": "rows",
        "source_language_adjacency": "coverage.source_language_adjacency",
        "organ_atlas_wiring": "rows[].wires_to",
        "source_module_file_graph": "coverage.source_module_file_graph",
    }
    assert organ_relationship_topology["source_adjacency_schema_version"] == (
        "microcosm_source_language_adjacency_v0"
    )
    assert organ_relationship_topology[
        "source_module_file_graph_schema_version"
    ] == "microcosm_source_module_file_graph_v0"
    assert organ_relationship_topology["accepted_organ_count"] == (
        _accepted_organ_count()
    )
    assert organ_relationship_topology["edge_count"] > _accepted_organ_count()
    assert organ_relationship_topology["relation_type_counts"][
        "organ.has_microcosm_standard"
    ] == _accepted_organ_count()
    assert organ_relationship_topology["relation_type_counts"][
        "organ.wires_to.organ"
    ] > 0
    assert organ_relationship_topology["relation_type_counts"][
        "source_file.copied_to_public_target"
    ] > 0
    assert organ_relationship_topology["relation_type_counts"][
        "source_file.validated_by_ref"
    ] > 0
    assert organ_relationship_topology["preview_limit"] == 5
    assert len(organ_relationship_topology["mixed_language_organs"]) <= 5
    assert organ_relationship_topology["mixed_language_organs_omitted_count"] > 0
    assert organ_relationship_topology["relation_type_counts"][
        "source_shard.retained_as_public_target_shard"
    ] > 0
    assert organ_relationship_topology["relation_type_counts"][
        "source_shard.validated_by_ref"
    ] > 0
    assert organ_relationship_topology["typescript_bearing_organs"] == (
        source_language_adjacency["typescript_bearing_organs"]
    )
    assert organ_relationship_topology["accepted_without_source_modules"] == (
        source_language_adjacency["accepted_without_source_modules"]
    )
    assert "not_lattice_authority" in organ_relationship_topology["authority"]
    assert card["global_doctrine_surfaces"]["status"] == "pass"


def test_organ_topology_cli_emits_direct_query_surface(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(["organ-topology", "--root", str(MICROCOSM_ROOT)])

    assert exit_code == 0
    card = json.loads(capsys.readouterr().out)
    assert card["schema_version"] == (
        "microcosm_organ_relationship_topology_card_v0"
    )
    assert card["status"] == "pass"
    assert card["accepted_organ_count"] == _accepted_organ_count()
    assert card["total_edge_count"] == card["edge_count"]
    assert card["filters"] == {
        "organ_id": None,
        "relation_type": None,
        "requested_relation_type": None,
        "source_ref": None,
        "target_ref": None,
        "manifest_ref": None,
        "shard_ref": None,
        "validation_ref": None,
    }
    assert "organ.has_source_language_family" in card["available_relation_types"]
    assert "organ.wires_to.organ" in card["available_relation_types"]
    assert "source_file.copied_to_public_target" in card["available_relation_types"]
    assert "source_file.validated_by_ref" in card["available_relation_types"]
    assert (
        "source_shard.retained_as_public_target_shard"
        in card["available_relation_types"]
    )
    assert "source_shard.validated_by_ref" in card["available_relation_types"]
    assert "batch7_macro_engines_capsule" not in card["query_affordances"][
        "python_typescript_javascript_organs"
    ]
    assert card["query_examples"] == [
        "microcosm organ-topology --organ batch7_macro_engines_capsule",
        "microcosm organ-topology --relation-type organ.has_source_language_family",
        (
            "microcosm organ-topology --organ batch7_macro_engines_capsule "
            "--relation-type organ.has_source_language_family"
        ),
        (
            "microcosm organ-topology --relation-type file_to_file "
            "--source-ref system/lib/agent_execution_trace.py"
        ),
        (
            "microcosm organ-topology --relation-type shard_to_shard "
            "--source-ref system/lib/agent_execution_trace.py"
        ),
        (
            "microcosm organ-topology --relation-type file_validated_by "
            "--source-ref system/lib/agent_execution_trace.py"
        ),
        (
            "microcosm organ-topology --validation-ref "
            "microcosm-substrate/tests/test_agent_route_observability_runtime.py::"
            "test_agent_trace_route_repair_imports_public_macro_body_refactor"
        ),
    ]
    assert "not_lattice_authority" in card["authority"]
    assert card["drilldown"] == "microcosm organ-surface-contract"


def test_organ_topology_cli_filters_edges_by_organ_and_relation(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(
        [
            "organ-topology",
            "--root",
            str(MICROCOSM_ROOT),
            "--organ",
            "batch7_macro_engines_capsule",
            "--relation-type",
            "organ.has_source_language_family",
        ]
    )

    assert exit_code == 0
    card = json.loads(capsys.readouterr().out)
    assert card["filters"] == {
        "organ_id": "batch7_macro_engines_capsule",
        "relation_type": "organ.has_source_language_family",
        "requested_relation_type": "organ.has_source_language_family",
        "source_ref": None,
        "target_ref": None,
        "manifest_ref": None,
        "shard_ref": None,
        "validation_ref": None,
    }
    assert card["edge_count"] == card["relation_type_counts"][
        "organ.has_source_language_family"
    ]
    assert card["edge_count"] > 0
    assert set(card["edges_by_organ"]) == {"batch7_macro_engines_capsule"}
    assert all(
        edge["organ_id"] == "batch7_macro_engines_capsule"
        and edge["relation_type"] == "organ.has_source_language_family"
        for edge in card["edges"]
    )
    assert any(
        edge["target_id"] == "source_language_family:javascript"
        for edge in card["edges"]
    )


def test_organ_topology_cli_accepts_wires_to_alias(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(
        [
            "organ-topology",
            "--root",
            str(MICROCOSM_ROOT),
            "--organ",
            "agent_route_observability_runtime",
            "--relation-type",
            "wires_to",
        ]
    )

    assert exit_code == 0
    card = json.loads(capsys.readouterr().out)
    assert card["filters"] == {
        "organ_id": "agent_route_observability_runtime",
        "relation_type": "organ.wires_to.organ",
        "requested_relation_type": "wires_to",
        "source_ref": None,
        "target_ref": None,
        "manifest_ref": None,
        "shard_ref": None,
        "validation_ref": None,
    }
    expected_targets = _atlas_wires_to("agent_route_observability_runtime")
    assert card["relation_type_counts"] == {
        "organ.wires_to.organ": len(expected_targets)
    }
    assert {
        edge["target_organ_id"]
        for edge in card["edges"]
    } == expected_targets


def test_organ_topology_cli_filters_file_and_shard_relations(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(
        [
            "organ-topology",
            "--root",
            str(MICROCOSM_ROOT),
            "--relation-type",
            "file_to_file",
            "--source-ref",
            "system/lib/agent_execution_trace.py",
        ]
    )

    assert exit_code == 0
    file_card = json.loads(capsys.readouterr().out)
    assert file_card["filters"] == {
        "organ_id": None,
        "relation_type": "source_file.copied_to_public_target",
        "requested_relation_type": "file_to_file",
        "source_ref": "system/lib/agent_execution_trace.py",
        "target_ref": None,
        "manifest_ref": None,
        "shard_ref": None,
        "validation_ref": None,
    }
    assert file_card["edge_count"] > 0
    assert file_card["relation_type_counts"] == {
        "source_file.copied_to_public_target": file_card["edge_count"]
    }
    assert all(
        edge["relation_type"] == "source_file.copied_to_public_target"
        and edge["source_ref"] == "system/lib/agent_execution_trace.py"
        for edge in file_card["edges"]
    )
    assert any(
        edge["target_ref"].endswith("source_modules/system/lib/agent_execution_trace.py")
        for edge in file_card["edges"]
    )

    shard_ref = (
        "system/lib/agent_execution_trace.py::required_anchor"
        "[def build_agent_execution_trace(]"
    )
    exit_code = cli.main(
        [
            "organ-topology",
            "--root",
            str(MICROCOSM_ROOT),
            "--relation-type",
            "shard_to_shard",
            "--shard-ref",
            shard_ref,
        ]
    )

    assert exit_code == 0
    shard_card = json.loads(capsys.readouterr().out)
    assert shard_card["filters"] == {
        "organ_id": None,
        "relation_type": "source_shard.retained_as_public_target_shard",
        "requested_relation_type": "shard_to_shard",
        "source_ref": None,
        "target_ref": None,
        "manifest_ref": None,
        "shard_ref": shard_ref,
        "validation_ref": None,
    }
    assert shard_card["edge_count"] > 0
    assert shard_card["relation_type_counts"] == {
        "source_shard.retained_as_public_target_shard": shard_card["edge_count"]
    }
    assert all(
        edge["relation_type"] == "source_shard.retained_as_public_target_shard"
        and edge["source_shard_ref"] == shard_ref
        for edge in shard_card["edges"]
    )


def test_organ_topology_cli_filters_validation_ref_relations(
    capsys: pytest.CaptureFixture[str],
) -> None:
    validation_ref = (
        "microcosm-substrate/tests/test_agent_route_observability_runtime.py::"
        "test_agent_trace_route_repair_imports_public_macro_body_refactor"
    )
    exit_code = cli.main(
        [
            "organ-topology",
            "--root",
            str(MICROCOSM_ROOT),
            "--relation-type",
            "file_validated_by",
            "--source-ref",
            "system/lib/agent_execution_trace.py",
        ]
    )

    assert exit_code == 0
    file_card = json.loads(capsys.readouterr().out)
    assert file_card["filters"] == {
        "organ_id": None,
        "relation_type": "source_file.validated_by_ref",
        "requested_relation_type": "file_validated_by",
        "source_ref": "system/lib/agent_execution_trace.py",
        "target_ref": None,
        "manifest_ref": None,
        "shard_ref": None,
        "validation_ref": None,
    }
    assert file_card["edge_count"] > 0
    assert file_card["relation_type_counts"] == {
        "source_file.validated_by_ref": file_card["edge_count"]
    }
    assert any(
        edge["validation_ref"] == validation_ref
        for edge in file_card["edges"]
    )

    shard_ref = (
        "system/lib/agent_execution_trace.py::required_anchor"
        "[def build_agent_execution_trace(]"
    )
    exit_code = cli.main(
        [
            "organ-topology",
            "--root",
            str(MICROCOSM_ROOT),
            "--relation-type",
            "shard_validated_by",
            "--shard-ref",
            shard_ref,
            "--validation-ref",
            validation_ref,
        ]
    )

    assert exit_code == 0
    shard_card = json.loads(capsys.readouterr().out)
    assert shard_card["filters"] == {
        "organ_id": None,
        "relation_type": "source_shard.validated_by_ref",
        "requested_relation_type": "shard_validated_by",
        "source_ref": None,
        "target_ref": None,
        "manifest_ref": None,
        "shard_ref": shard_ref,
        "validation_ref": validation_ref,
    }
    assert shard_card["edge_count"] > 0
    assert shard_card["relation_type_counts"] == {
        "source_shard.validated_by_ref": shard_card["edge_count"]
    }
    assert all(
        edge["source_shard_ref"] == shard_ref
        and edge["validation_ref"] == validation_ref
        for edge in shard_card["edges"]
    )
