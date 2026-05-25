from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from microcosm_core.macro_tools.command_output_projection import (
    ENVELOPE_KIND,
    REQUIRED_FIELDS,
    command_projection,
    envelope_field_present,
    make_currentness,
    make_omission_receipt,
    make_validation_contract,
)
from microcosm_core.macro_tools.command_output_sidecar import (
    ENV_VAR,
    RECEIPT_KIND,
    RECEIPT_SCHEMA_VERSION,
    SIDECAR_ROOT,
    maybe_route_to_sidecar,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MICROCOSM_ROOT.parent
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
)
TRACE_CAPSULE_MANIFEST = BUNDLE_INPUT / "trace_capsule_source_module_manifest.json"
ROUTE_SELECTION_CONTROL_MANIFEST = (
    BUNDLE_INPUT / "route_selection_control_source_module_manifest.json"
)
BOOTSTRAP_ROUTE_SURFACE_MANIFEST = (
    BUNDLE_INPUT / "bootstrap_route_surface_source_module_manifest.json"
)
AGENT_OPERATING_PACKET_MANIFEST = (
    BUNDLE_INPUT / "agent_operating_packet_source_module_manifest.json"
)
ACTIVE_EXECUTION_CONSTELLATION_MANIFEST = (
    BUNDLE_INPUT / "active_execution_constellation_source_module_manifest.json"
)
NAVIGATION_COVERAGE_MATRIX_MANIFEST = (
    BUNDLE_INPUT / "navigation_coverage_matrix_source_module_manifest.json"
)
NAVIGATION_METABOLISM_LEDGER_MANIFEST = (
    BUNDLE_INPUT / "navigation_metabolism_ledger_source_module_manifest.json"
)
NAVIGATION_SURFACE_AUDIT_MANIFEST = (
    BUNDLE_INPUT / "navigation_surface_audit_source_module_manifest.json"
)
COMMAND_NODE_CACHE_MANIFEST = (
    BUNDLE_INPUT / "command_node_cache_source_module_manifest.json"
)
NAVIGATION_CLUSTERABILITY_MANIFEST = (
    BUNDLE_INPUT / "navigation_clusterability_source_module_manifest.json"
)
ANNEX_ROUTING_COVERAGE_MANIFEST = (
    BUNDLE_INPUT / "annex_routing_coverage_source_module_manifest.json"
)
ANNEX_CURRENTNESS_MANIFEST = (
    BUNDLE_INPUT / "annex_currentness_source_module_manifest.json"
)
ENTRYPOINT_HEALTH_MANIFEST = (
    BUNDLE_INPUT / "entrypoint_health_source_module_manifest.json"
)
AGENT_ENTRYPOINT_AUDIT_MANIFEST = (
    BUNDLE_INPUT / "agent_entrypoint_audit_source_module_manifest.json"
)
NAVIGATION_FITNESS_MANIFEST = (
    BUNDLE_INPUT / "navigation_fitness_source_module_manifest.json"
)
DYNAMIC_PAPER_LATTICE_MANIFEST = (
    BUNDLE_INPUT / "dynamic_paper_lattice_source_module_manifest.json"
)
KIND_ATLAS_MANIFEST = BUNDLE_INPUT / "kind_atlas_source_module_manifest.json"
SEMANTIC_ROUTING_MANIFEST = (
    BUNDLE_INPUT / "semantic_routing_source_module_manifest.json"
)
EMBEDDING_SUBSTRATE_MANIFEST = (
    BUNDLE_INPUT / "embedding_substrate_source_module_manifest.json"
)
NVIDIA_NIM_PROVIDER_BOUNDARY_MANIFEST = (
    BUNDLE_INPUT / "nvidia_nim_provider_boundary_source_module_manifest.json"
)
AGENT_PROVIDER_ROUTER_MANIFEST = (
    BUNDLE_INPUT / "agent_provider_router_source_module_manifest.json"
)
BRIDGE_ROUTE_CONFIG_MANIFEST = (
    BUNDLE_INPUT / "bridge_route_config_source_module_manifest.json"
)
KERNEL_BRIDGE_CONFIG_MANIFEST = (
    BUNDLE_INPUT / "kernel_bridge_config_source_module_manifest.json"
)
OBSERVE_RUNTIME_MANIFEST = (
    BUNDLE_INPUT / "observe_runtime_source_module_manifest.json"
)
KERNEL_STATE_REGISTRY_MANIFEST = (
    BUNDLE_INPUT / "kernel_state_registry_source_module_manifest.json"
)


def test_command_output_projection_macro_tool_emits_required_projection_envelope() -> None:
    envelope = command_projection(
        command="--demo",
        band="card",
        selector="public-fixture",
        summary={"row_count": 1},
        currentness=make_currentness(
            generated_at="2026-05-25T00:00:00Z",
            source_refs_checked=["microcosm-substrate/tests"],
        ),
        drilldown_command="microcosm command-output-projection-fixture --band full",
        evidence_command="microcosm command-output-projection-fixture --band full",
        omission_receipt=make_omission_receipt(
            omitted=["rows"],
            reason="card band keeps only count-level command-output evidence",
            drilldown="microcosm command-output-projection-fixture --band full",
        ),
        validation_contract=make_validation_contract(
            freshness_probe="pytest microcosm-substrate/tests/test_command_output_projection_runtime.py",
        ),
    )

    assert envelope["kind"] == ENVELOPE_KIND
    assert envelope["row_id"] == "kernel:demo:public-fixture::card"
    for field in REQUIRED_FIELDS:
        assert envelope_field_present(envelope, field), field
    assert envelope["omission_receipt"]["omitted"] == ["rows"]


def test_command_output_sidecar_macro_tool_writes_bounded_receipt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(ENV_VAR, "0")
    payload = {
        "kind": "public_command_output_fixture",
        "schema_version": "public_command_output_fixture_v0",
        "summary": {"row_count": 3},
        "rows": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
    }

    receipt = maybe_route_to_sidecar(
        payload,
        surface="microcosm.command_output_projection.fixture",
        repo_root=tmp_path,
    )

    assert receipt is not None
    assert receipt["kind"] == RECEIPT_KIND
    assert receipt["schema_version"] == RECEIPT_SCHEMA_VERSION
    assert receipt["status"] == "written_to_sidecar"
    assert receipt["payload_summary"]["summary"] == {"row_count": 3}
    sidecar_path = tmp_path / receipt["output_path"]
    assert sidecar_path.is_file()
    assert sidecar_path.parent.parent == tmp_path / SIDECAR_ROOT
    assert json.loads(sidecar_path.read_text(encoding="utf-8")) == payload
    assert all("--command-output" in command for command in receipt["read_next"])


def test_command_output_source_manifest_matches_exact_macro_sources() -> None:
    manifest = json.loads(
        (BUNDLE_INPUT / "command_output_source_module_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["manifest_id"] == "command_output_projection_source_modules_import"
    assert manifest["module_count"] == 4
    for row in manifest["modules"]:
        source = REPO_ROOT / row["source_ref"]
        target_ref = str(row["target_ref"]).removeprefix("microcosm-substrate/")
        target = MICROCOSM_ROOT / target_ref
        assert source.is_file()
        assert target.is_file()
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
        target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
        assert row["source_sha256"] == source_digest
        assert row["target_sha256"] == target_digest
        assert source_digest == target_digest
        target_text = target.read_text(encoding="utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in target_text


def test_trace_capsule_source_manifest_matches_exact_macro_sources() -> None:
    manifest = json.loads(TRACE_CAPSULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["manifest_id"] == "trace_capsule_prompt_edit_capture_source_modules_import"
    assert manifest["module_count"] == 4
    assert manifest["public_runtime_policy"].startswith("public validation uses fixture")
    for row in manifest["modules"]:
        source = REPO_ROOT / row["source_ref"]
        target_ref = str(row["target_ref"]).removeprefix("microcosm-substrate/")
        target = MICROCOSM_ROOT / target_ref
        assert source.is_file()
        assert target.is_file()
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
        target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
        assert row["source_sha256"] == source_digest
        assert row["target_sha256"] == target_digest
        assert source_digest == target_digest
        target_text = target.read_text(encoding="utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in target_text


def test_route_selection_control_source_manifest_matches_exact_macro_sources() -> None:
    manifest = json.loads(ROUTE_SELECTION_CONTROL_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["manifest_id"] == "route_selection_control_source_modules_import"
    assert manifest["module_count"] == 5
    assert manifest["public_runtime_policy"].startswith("public validation uses exact")
    for row in manifest["modules"]:
        source = REPO_ROOT / row["source_ref"]
        target_ref = str(row["target_ref"]).removeprefix("microcosm-substrate/")
        target = MICROCOSM_ROOT / target_ref
        assert source.is_file()
        assert target.is_file()
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
        target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
        assert row["source_sha256"] == source_digest
        assert row["target_sha256"] == target_digest
        assert source_digest == target_digest
        target_text = target.read_text(encoding="utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in target_text


def test_bootstrap_route_surface_source_manifest_matches_exact_macro_sources() -> None:
    manifest = json.loads(BOOTSTRAP_ROUTE_SURFACE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["manifest_id"] == "bootstrap_route_surface_source_modules_import"
    assert manifest["module_count"] == 4
    assert manifest["public_runtime_policy"].startswith("public validation uses exact")
    for row in manifest["modules"]:
        source = REPO_ROOT / row["source_ref"]
        target_ref = str(row["target_ref"]).removeprefix("microcosm-substrate/")
        target = MICROCOSM_ROOT / target_ref
        assert source.is_file()
        assert target.is_file()
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
        target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
        assert row["source_sha256"] == source_digest
        assert row["target_sha256"] == target_digest
        assert source_digest == target_digest
        target_text = target.read_text(encoding="utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in target_text


def test_bootstrap_route_surface_projection_sources_have_route_rows() -> None:
    bootstrap_payload = json.loads(
        (
            BUNDLE_INPUT
            / "source_modules/codex/doctrine/agent_bootstrap_live.json"
        ).read_text(encoding="utf-8")
    )
    routing_payload = json.loads(
        (
            BUNDLE_INPUT
            / "source_modules/codex/doctrine/routing_hologram.json"
        ).read_text(encoding="utf-8")
    )

    route_ids = {
        row["situation_id"]
        for row in bootstrap_payload["situation_routes"]
        if isinstance(row, dict)
    }
    assert "entry_control_packet" in route_ids
    assert "task_conditioned_context_pack_entry" in route_ids
    assert len(bootstrap_payload["situation_routes"]) >= 40
    assert len(routing_payload["situation_rows"]) == 10
    assert str(routing_payload["entry_protocol"][0]).startswith(
        "`./repo-python kernel.py --info`"
    )
    for source_rel in (
        "source_modules/system/lib/agent_bootstrap_projection.py",
        "source_modules/system/lib/routing_projection.py",
    ):
        source_path = BUNDLE_INPUT / source_rel
        compile(source_path.read_text(encoding="utf-8"), str(source_path), "exec")


def test_agent_operating_packet_source_manifest_matches_exact_macro_sources() -> None:
    manifest = json.loads(AGENT_OPERATING_PACKET_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["manifest_id"] == "agent_operating_packet_source_modules_import"
    assert manifest["module_count"] == 2
    assert manifest["public_runtime_policy"].startswith("public validation uses exact")
    for row in manifest["modules"]:
        source = REPO_ROOT / row["source_ref"]
        target_ref = str(row["target_ref"]).removeprefix("microcosm-substrate/")
        target = MICROCOSM_ROOT / target_ref
        assert source.is_file()
        assert target.is_file()
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
        target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
        assert row["source_sha256"] == source_digest
        assert row["target_sha256"] == target_digest
        assert source_digest == target_digest
        target_text = target.read_text(encoding="utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in target_text


def test_agent_operating_packet_sources_have_runtime_principle_packet() -> None:
    packet = json.loads(
        (
            BUNDLE_INPUT
            / "source_modules/codex/doctrine/agent_operating_packet.json"
        ).read_text(encoding="utf-8")
    )

    assert packet["kind"] == "agent_operating_packet"
    assert packet["authority_posture"] == "generated_projection_not_source_authority"
    assert len(packet["global_runtime_capsule"]["principles"]) >= 7
    assert len(packet["agent_principles"]["rows"]) >= 16
    assert packet["candidate_axiom_pressure"]["authority_posture"].startswith(
        "candidate"
    )
    assert packet["budget_metrics"]["entry_strip_bytes"] > 0

    source_path = (
        BUNDLE_INPUT / "source_modules/system/lib/agent_operating_packet.py"
    )
    source_text = source_path.read_text(encoding="utf-8")
    compile(source_text, str(source_path), "exec")
    assert "def build_agent_operating_packet_strip(" in source_text


def test_active_execution_constellation_source_manifest_matches_exact_macro_sources() -> None:
    manifest = json.loads(ACTIVE_EXECUTION_CONSTELLATION_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["manifest_id"] == "active_execution_constellation_source_modules_import"
    assert manifest["module_count"] == 2
    assert manifest["public_runtime_policy"].startswith("public validation uses exact")
    for row in manifest["modules"]:
        source = REPO_ROOT / row["source_ref"]
        target_ref = str(row["target_ref"]).removeprefix("microcosm-substrate/")
        target = MICROCOSM_ROOT / target_ref
        assert source.is_file()
        assert target.is_file()
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
        target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
        assert row["source_sha256"] == source_digest
        assert row["target_sha256"] == target_digest
        assert source_digest == target_digest
        target_text = target.read_text(encoding="utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in target_text


def test_active_execution_constellation_sources_compile_and_carry_liveness_contract() -> None:
    projection_source = (
        BUNDLE_INPUT
        / "source_modules/system/lib/active_execution_constellation.py"
    )
    test_source = (
        BUNDLE_INPUT
        / "source_modules/system/server/tests/test_active_execution_constellation.py"
    )

    projection_text = projection_source.read_text(encoding="utf-8")
    test_text = test_source.read_text(encoding="utf-8")

    compile(projection_text, str(projection_source), "exec")
    compile(test_text, str(test_source), "exec")
    assert "SCHEMA_VERSION = \"active_execution_constellation_v0\"" in projection_text
    assert "def build_active_execution_constellation(" in projection_text
    assert "def compact_active_execution_constellation_for_entry(" in projection_text
    assert "\"demotion_guard\"" in projection_text
    assert "\"claim_topology\"" in projection_text
    assert "test_pulse_snapshot_includes_active_execution_constellation" in test_text


def test_navigation_coverage_matrix_source_manifest_matches_exact_macro_sources() -> None:
    manifest = json.loads(NAVIGATION_COVERAGE_MATRIX_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["manifest_id"] == "navigation_coverage_matrix_source_modules_import"
    assert manifest["module_count"] == 2
    assert manifest["public_runtime_policy"].startswith("public validation uses exact")
    for row in manifest["modules"]:
        source = REPO_ROOT / row["source_ref"]
        target_ref = str(row["target_ref"]).removeprefix("microcosm-substrate/")
        target = MICROCOSM_ROOT / target_ref
        assert source.is_file()
        assert target.is_file()
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
        target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
        assert row["source_sha256"] == source_digest
        assert row["target_sha256"] == target_digest
        assert source_digest == target_digest
        target_text = target.read_text(encoding="utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in target_text


def test_navigation_coverage_matrix_sources_compile_and_carry_coverage_contract() -> None:
    projection_source = (
        BUNDLE_INPUT
        / "source_modules/system/lib/navigation_coverage_matrix.py"
    )
    test_source = (
        BUNDLE_INPUT
        / "source_modules/system/server/tests/test_navigation_coverage_matrix.py"
    )

    projection_text = projection_source.read_text(encoding="utf-8")
    test_text = test_source.read_text(encoding="utf-8")

    compile(projection_text, str(projection_source), "exec")
    compile(test_text, str(test_source), "exec")
    assert "def build_coverage_enforcement_matrix(" in projection_text
    assert "\"schema_version\": \"coverage_enforcement_matrix_v0" in projection_text
    assert "process_audit_fast_path" in projection_text
    assert "type_plane_resolution" in projection_text
    assert "latency_profile" in projection_text
    assert (
        "test_coverage_enforcement_matrix_marks_skill_find_as_drilldown_only"
        in test_text
    )
    assert "test_coverage_enforcement_matrix_cli_emits_json" in test_text


def test_navigation_metabolism_ledger_source_manifest_matches_exact_macro_sources() -> None:
    manifest = json.loads(NAVIGATION_METABOLISM_LEDGER_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["manifest_id"] == "navigation_metabolism_ledger_source_modules_import"
    assert manifest["module_count"] == 2
    assert manifest["public_runtime_policy"].startswith("public validation uses exact")
    for row in manifest["modules"]:
        source = REPO_ROOT / row["source_ref"]
        target_ref = str(row["target_ref"]).removeprefix("microcosm-substrate/")
        target = MICROCOSM_ROOT / target_ref
        assert source.is_file()
        assert target.is_file()
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
        target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
        assert row["source_sha256"] == source_digest
        assert row["target_sha256"] == target_digest
        assert source_digest == target_digest
        target_text = target.read_text(encoding="utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in target_text


def test_navigation_metabolism_ledger_sources_compile_and_carry_metabolism_contract() -> None:
    projection_source = (
        BUNDLE_INPUT
        / "source_modules/system/lib/navigation_metabolism_ledger.py"
    )
    test_source = (
        BUNDLE_INPUT
        / "source_modules/system/server/tests/test_navigation_metabolism_ledger.py"
    )

    projection_text = projection_source.read_text(encoding="utf-8")
    test_text = test_source.read_text(encoding="utf-8")

    compile(projection_text, str(projection_source), "exec")
    compile(test_text, str(test_source), "exec")
    assert "def build_navigation_metabolism_ledger(" in projection_text
    assert "\"schema_version\": \"navigation_metabolism_ledger_v0\"" in projection_text
    assert "behavior_debt" in projection_text
    assert "actor_delivery_debt" in projection_text
    assert "route_lifecycle" in projection_text
    assert "test_navigation_metabolism_ledger_unifies_debt_classes" in test_text
    assert "test_actor_delivery_debt_rows_include_decision_coverage_gaps" in test_text


def test_navigation_surface_audit_source_manifest_matches_exact_macro_sources() -> None:
    manifest = json.loads(NAVIGATION_SURFACE_AUDIT_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["manifest_id"] == "navigation_surface_audit_source_modules_import"
    assert manifest["module_count"] == 3
    assert manifest["public_runtime_policy"].startswith("public validation uses exact")
    for row in manifest["modules"]:
        source = REPO_ROOT / row["source_ref"]
        target_ref = str(row["target_ref"]).removeprefix("microcosm-substrate/")
        target = MICROCOSM_ROOT / target_ref
        assert source.is_file()
        assert target.is_file()
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
        target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
        assert row["source_sha256"] == source_digest
        assert row["target_sha256"] == target_digest
        assert source_digest == target_digest
        target_text = target.read_text(encoding="utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in target_text


def test_navigation_surface_audit_sources_compile_and_carry_surface_contract() -> None:
    audit_source = (
        BUNDLE_INPUT
        / "source_modules/system/lib/navigation_surface_audit.py"
    )
    contracts_source = (
        BUNDLE_INPUT
        / "source_modules/system/lib/navigation_surface_contracts.py"
    )
    test_source = (
        BUNDLE_INPUT
        / "source_modules/system/server/tests/test_navigation_surface_audit.py"
    )

    audit_text = audit_source.read_text(encoding="utf-8")
    contracts_text = contracts_source.read_text(encoding="utf-8")
    test_text = test_source.read_text(encoding="utf-8")

    compile(audit_text, str(audit_source), "exec")
    compile(contracts_text, str(contracts_source), "exec")
    compile(test_text, str(test_source), "exec")
    assert "def build_navigation_surface_audit(" in audit_text
    assert "\"kind\": \"navigation_surface_audit\"" in audit_text
    assert "contract_status" in audit_text
    assert "CONTROL_ENTRY = \"CONTROL_ENTRY\"" in contracts_text
    assert "def debug_trace_contract(" in contracts_text
    assert (
        "test_navigation_surface_audit_separates_size_measurement_from_contract_status"
        in test_text
    )


def test_command_node_cache_source_manifest_matches_exact_macro_sources() -> None:
    manifest = json.loads(COMMAND_NODE_CACHE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["manifest_id"] == "command_node_cache_source_modules_import"
    assert manifest["module_count"] == 2
    assert manifest["public_runtime_policy"].startswith("public validation uses exact")
    for row in manifest["modules"]:
        source = REPO_ROOT / row["source_ref"]
        target_ref = str(row["target_ref"]).removeprefix("microcosm-substrate/")
        target = MICROCOSM_ROOT / target_ref
        assert source.is_file()
        assert target.is_file()
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
        target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
        assert row["source_sha256"] == source_digest
        assert row["target_sha256"] == target_digest
        assert source_digest == target_digest
        target_text = target.read_text(encoding="utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in target_text


def test_command_node_cache_sources_compile_and_carry_cache_contract() -> None:
    cache_source = (
        BUNDLE_INPUT
        / "source_modules/system/lib/command_node_cache.py"
    )
    test_source = (
        BUNDLE_INPUT
        / "source_modules/system/server/tests/test_command_node_cache.py"
    )

    cache_text = cache_source.read_text(encoding="utf-8")
    test_text = test_source.read_text(encoding="utf-8")

    compile(cache_text, str(cache_source), "exec")
    compile(test_text, str(test_source), "exec")
    assert "SCHEMA_VERSION = \"command_node_cache_v1\"" in cache_text
    assert "def cached_command_node(" in cache_text
    assert "def peek_cached_command_node(" in cache_text
    assert "AIW_COMMAND_CACHE_REFRESH" in cache_text
    assert (
        "test_command_node_cache_singleflights_across_processes"
        in test_text
    )
    assert "dynamic_inputs_manifested" in test_text


def _assert_source_manifest_matches_exact_macro_sources(
    manifest_path: Path,
    *,
    manifest_id: str,
    module_count: int,
) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["manifest_id"] == manifest_id
    assert manifest["module_count"] == module_count
    assert manifest["public_runtime_policy"].startswith("public validation uses exact")
    for row in manifest["modules"]:
        source = REPO_ROOT / row["source_ref"]
        target_ref = str(row["target_ref"]).removeprefix("microcosm-substrate/")
        target = MICROCOSM_ROOT / target_ref
        assert source.is_file()
        assert target.is_file()
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
        target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
        assert row["source_sha256"] == source_digest
        assert row["target_sha256"] == target_digest
        assert source_digest == target_digest
        target_text = target.read_text(encoding="utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in target_text
    return manifest


def test_navigation_clusterability_source_manifest_matches_exact_macro_sources() -> None:
    _assert_source_manifest_matches_exact_macro_sources(
        NAVIGATION_CLUSTERABILITY_MANIFEST,
        manifest_id="navigation_clusterability_source_modules_import",
        module_count=2,
    )


def test_navigation_clusterability_sources_compile_and_carry_clusterability_contract() -> None:
    clusterability_source = (
        BUNDLE_INPUT / "source_modules/system/lib/navigation_clusterability.py"
    )
    test_source = (
        BUNDLE_INPUT
        / "source_modules/system/server/tests/test_navigation_clusterability.py"
    )

    clusterability_text = clusterability_source.read_text(encoding="utf-8")
    test_text = test_source.read_text(encoding="utf-8")

    compile(clusterability_text, str(clusterability_source), "exec")
    compile(test_text, str(test_source), "exec")
    assert "def build_navigation_clusterability_audit(" in clusterability_text
    assert '"kind": "navigation_clusterability_audit"' in clusterability_text
    assert "HIGH_CARDINALITY_THRESHOLD" in clusterability_text
    assert "cluster_flag_status" in clusterability_text
    assert (
        "test_clusterability_quick_profile_defers_measuring_implemented_cluster_payloads"
        in test_text
    )


def test_annex_routing_coverage_source_manifest_matches_exact_macro_sources() -> None:
    _assert_source_manifest_matches_exact_macro_sources(
        ANNEX_ROUTING_COVERAGE_MANIFEST,
        manifest_id="annex_routing_coverage_source_modules_import",
        module_count=2,
    )


def test_annex_routing_coverage_sources_compile_and_carry_routing_contract() -> None:
    routing_source = BUNDLE_INPUT / "source_modules/system/lib/annex_routing_coverage.py"
    test_source = (
        BUNDLE_INPUT
        / "source_modules/system/server/tests/test_annex_routing_coverage.py"
    )

    routing_text = routing_source.read_text(encoding="utf-8")
    test_text = test_source.read_text(encoding="utf-8")

    compile(routing_text, str(routing_source), "exec")
    compile(test_text, str(test_source), "exec")
    assert "DEFAULT_UNROUTED_RATE_THRESHOLD" in routing_text
    assert "def build_annex_routing_coverage(" in routing_text
    assert '"kind": "annex_routing_coverage"' in routing_text
    assert "routing_coverage:annex_patterns:unrouted" in routing_text
    assert "test_annex_routing_coverage_cli_emits_json" in test_text


def test_annex_currentness_source_manifest_matches_exact_macro_sources() -> None:
    _assert_source_manifest_matches_exact_macro_sources(
        ANNEX_CURRENTNESS_MANIFEST,
        manifest_id="annex_currentness_source_modules_import",
        module_count=2,
    )


def test_annex_currentness_sources_compile_and_carry_currentness_contract() -> None:
    currentness_source = BUNDLE_INPUT / "source_modules/system/lib/annex_currentness.py"
    test_source = (
        BUNDLE_INPUT / "source_modules/system/server/tests/test_annex_currentness.py"
    )

    currentness_text = currentness_source.read_text(encoding="utf-8")
    test_text = test_source.read_text(encoding="utf-8")

    compile(currentness_text, str(currentness_source), "exec")
    compile(test_text, str(test_source), "exec")
    assert 'SCHEMA_VERSION = "annex_currentness_v0"' in currentness_text
    assert "def build_annex_currentness(" in currentness_text
    assert "annex_sync_digest" in currentness_text
    assert "movement_to_row_job" in currentness_text
    assert "test_kernel_annex_currentness_cli_emits_packet" in test_text


def test_entrypoint_health_source_manifest_matches_exact_macro_sources() -> None:
    _assert_source_manifest_matches_exact_macro_sources(
        ENTRYPOINT_HEALTH_MANIFEST,
        manifest_id="entrypoint_health_source_modules_import",
        module_count=2,
    )


def test_entrypoint_health_sources_compile_and_carry_entrypoint_contract() -> None:
    entrypoint_source = BUNDLE_INPUT / "source_modules/system/lib/entrypoint_health.py"
    test_source = (
        BUNDLE_INPUT / "source_modules/system/server/tests/test_entrypoint_health.py"
    )

    entrypoint_text = entrypoint_source.read_text(encoding="utf-8")
    test_text = test_source.read_text(encoding="utf-8")

    compile(entrypoint_text, str(entrypoint_source), "exec")
    compile(test_text, str(test_source), "exec")
    assert '"schema_version": "entrypoint_health_v0"' in entrypoint_text
    assert "def build_entrypoint_health(" in entrypoint_text
    assert "def project_entry_surface_diagnostics(" in entrypoint_text
    assert "FORBIDDEN_ROUTE_PATTERNS" in entrypoint_text
    assert (
        "test_repo_entrypoint_health_is_budget_safe_and_route_clean"
        in test_text
    )
    assert (
        "test_entry_surface_diagnostic_first_contact_uses_fast_source_coupling_receipt"
        in test_text
    )


def test_agent_entrypoint_audit_source_manifest_matches_exact_macro_sources() -> None:
    _assert_source_manifest_matches_exact_macro_sources(
        AGENT_ENTRYPOINT_AUDIT_MANIFEST,
        manifest_id="agent_entrypoint_audit_source_modules_import",
        module_count=2,
    )


def test_agent_entrypoint_audit_sources_compile_and_carry_audit_contract() -> None:
    audit_source = BUNDLE_INPUT / "source_modules/system/lib/agent_entrypoint_audit.py"
    test_source = (
        BUNDLE_INPUT
        / "source_modules/system/server/tests/test_agent_entrypoint_audit.py"
    )

    audit_text = audit_source.read_text(encoding="utf-8")
    test_text = test_source.read_text(encoding="utf-8")

    compile(audit_text, str(audit_source), "exec")
    compile(test_text, str(test_source), "exec")
    assert "GENERATED_BLOCK_MARKERS = (" in audit_text
    assert "def build_agent_entrypoint_audit(" in audit_text
    assert "def write_agent_entrypoint_audit(" in audit_text
    assert '"kind": "agent_entrypoint_audit"' in audit_text
    assert "test_kernel_route_emits_audit_shape" in test_text
    assert "test_generated_block_drift_compares_against_rendered_projection" in test_text


def test_navigation_fitness_source_manifest_matches_exact_macro_sources() -> None:
    _assert_source_manifest_matches_exact_macro_sources(
        NAVIGATION_FITNESS_MANIFEST,
        manifest_id="navigation_fitness_source_modules_import",
        module_count=2,
    )


def test_navigation_fitness_sources_compile_and_carry_fitness_contract() -> None:
    fitness_source = BUNDLE_INPUT / "source_modules/system/lib/navigation_fitness.py"
    test_source = (
        BUNDLE_INPUT
        / "source_modules/system/server/tests/test_navigation_fitness.py"
    )

    fitness_text = fitness_source.read_text(encoding="utf-8")
    test_text = test_source.read_text(encoding="utf-8")

    compile(fitness_text, str(fitness_source), "exec")
    compile(test_text, str(test_source), "exec")
    assert "FITNESS_TASKS: tuple[FitnessTask, ...] = (" in fitness_text
    assert "HELDOUT_TASKS: tuple[FitnessTask, ...] = (" in fitness_text
    assert "ADVERSARIAL_TASKS: tuple[FitnessTask, ...] = (" in fitness_text
    assert "def build_navigation_fitness(" in fitness_text
    assert '"schema_version": "navigation_fitness_v0"' in fitness_text
    assert (
        "test_navigation_fitness_smoke_proves_expected_ids_without_legacy_first_routes"
        in test_text
    )
    assert "test_navigation_fitness_cli_and_semantic_modes_are_explicit" in test_text


def test_dynamic_paper_lattice_source_manifest_matches_exact_macro_sources() -> None:
    _assert_source_manifest_matches_exact_macro_sources(
        DYNAMIC_PAPER_LATTICE_MANIFEST,
        manifest_id="dynamic_paper_lattice_source_modules_import",
        module_count=2,
    )


def test_dynamic_paper_lattice_sources_compile_and_carry_lattice_contract() -> None:
    lattice_source = (
        BUNDLE_INPUT / "source_modules/system/lib/dynamic_paper_lattice.py"
    )
    test_source = (
        BUNDLE_INPUT
        / "source_modules/system/server/tests/test_dynamic_paper_lattice.py"
    )

    lattice_text = lattice_source.read_text(encoding="utf-8")
    test_text = test_source.read_text(encoding="utf-8")

    compile(lattice_text, str(lattice_source), "exec")
    compile(test_text, str(test_source), "exec")
    assert 'DEFAULT_SLUG = "navigation_hologram_theory"' in lattice_text
    assert "RAW_SEED_PATH = Path(" in lattice_text
    assert "def build_dynamic_paper_lattice(" in lattice_text
    assert '"schema_version": "dynamic_paper_lattice_v0"' in lattice_text
    assert '"paper_module_profile_id": paper_contract.get("profile_id")' in lattice_text
    assert (
        "test_dynamic_paper_lattice_projects_source_anchored_affordance_rows"
        in test_text
    )
    assert "test_dynamic_paper_lattice_cli_emits_budgeted_json" in test_text
    assert (
        "test_dynamic_paper_lattice_unsupported_slug_is_structured_exemplar_error"
        in test_text
    )


def test_kind_atlas_source_manifest_matches_exact_macro_sources() -> None:
    _assert_source_manifest_matches_exact_macro_sources(
        KIND_ATLAS_MANIFEST,
        manifest_id="kind_atlas_source_modules_import",
        module_count=2,
    )


def test_kind_atlas_sources_compile_and_carry_option_surface_contract() -> None:
    atlas_source = BUNDLE_INPUT / "source_modules/system/lib/kind_atlas.py"
    test_source = (
        BUNDLE_INPUT / "source_modules/system/server/tests/test_kind_atlas.py"
    )

    atlas_text = atlas_source.read_text(encoding="utf-8")
    test_text = test_source.read_text(encoding="utf-8")

    compile(atlas_text, str(atlas_source), "exec")
    compile(test_text, str(test_source), "exec")
    assert "PAPER_MODULE_INDEX = Path(" in atlas_text
    assert 'SUPPORTED_BANDS = {"flag", "card"}' in atlas_text
    assert "def build_kind_atlas(" in atlas_text
    assert '"schema_version": "kind_atlas_v0"' in atlas_text
    assert '"not_keyword_search": True' in atlas_text
    assert "test_kind_atlas_marks_supported_rows_and_projection_gaps" in test_text
    assert "test_kind_atlas_kernel_command_emits_json" in test_text
    assert "test_option_surface_kinds_alias_uses_kind_atlas" in test_text


def test_semantic_routing_source_manifest_matches_exact_macro_sources() -> None:
    _assert_source_manifest_matches_exact_macro_sources(
        SEMANTIC_ROUTING_MANIFEST,
        manifest_id="semantic_routing_source_modules_import",
        module_count=2,
    )


def test_semantic_routing_sources_compile_and_carry_route_contract() -> None:
    routing_source = BUNDLE_INPUT / "source_modules/system/lib/semantic_routing.py"
    test_source = (
        BUNDLE_INPUT
        / "source_modules/system/server/tests/test_semantic_routing.py"
    )

    routing_text = routing_source.read_text(encoding="utf-8")
    test_text = test_source.read_text(encoding="utf-8")

    compile(routing_text, str(routing_source), "exec")
    compile(test_text, str(test_source), "exec")
    assert (
        'STANDARD_PATH = "codex/standards/std_semantic_routing.json"'
        in routing_text
    )
    assert 'STATE_DIR = "state/semantic_routing"' in routing_text
    assert (
        'EVIDENCE_LEDGER_PATH = "codex/ledger/semantic_routing/route_evidence.jsonl"'
        in routing_text
    )
    assert "def default_activation_ladder(" in routing_text
    assert "def refresh_routes(" in routing_text
    assert "def query_routes(" in routing_text
    assert "def confirm_route(" in routing_text
    assert "def append_operation_route_evidence(" in routing_text
    assert "test_refresh_routes_builds_deterministic_bounded_graph" in test_text
    assert (
        "test_incremental_refresh_tracks_changed_ids_and_impacted_neighbors"
        in test_text
    )
    assert "test_query_routes_falls_back_when_python_routes_are_stale" in test_text
    assert "test_run_action_appends_operation_route_evidence_results" in test_text
    assert (
        "test_routing_metabolism_status_reports_digest_cache_and_runner_health"
        in test_text
    )


def test_embedding_substrate_source_manifest_matches_exact_macro_sources() -> None:
    _assert_source_manifest_matches_exact_macro_sources(
        EMBEDDING_SUBSTRATE_MANIFEST,
        manifest_id="embedding_substrate_source_modules_import",
        module_count=3,
    )


def test_embedding_substrate_sources_compile_and_carry_faceted_embedding_contract() -> None:
    substrate_source = (
        BUNDLE_INPUT / "source_modules/system/lib/embedding_substrate.py"
    )
    sources_source = BUNDLE_INPUT / "source_modules/system/lib/embedding_sources.py"
    test_source = (
        BUNDLE_INPUT
        / "source_modules/system/server/tests/test_embedding_substrate.py"
    )

    substrate_text = substrate_source.read_text(encoding="utf-8")
    sources_text = sources_source.read_text(encoding="utf-8")
    test_text = test_source.read_text(encoding="utf-8")

    compile(substrate_text, str(substrate_source), "exec")
    compile(sources_text, str(sources_source), "exec")
    compile(test_text, str(test_source), "exec")
    assert 'SCHEMA_VERSION = "embedding_substrate_v2_faceted"' in substrate_text
    assert 'OVERLAY_SCHEMA_VERSION = "embedding_substrate_overlay_v1"' in substrate_text
    assert "class EmbeddingSubstrate:" in substrate_text
    assert "def embed_texts_default(" in substrate_text
    assert "def refresh(" in substrate_text
    assert "def search_ladder(" in substrate_text
    assert "def alignment(" in substrate_text
    assert "class DoctrineSource(SourceAdapter):" in sources_text
    assert "class PaperModuleSource(SourceAdapter):" in sources_text
    assert "class RawSeedNavigationSource(SourceAdapter):" in sources_text
    assert "def parse_std_python_atoms(" in sources_text
    assert "class PythonHolographicSource(SourceAdapter):" in sources_text
    assert "SOURCE_ADAPTERS: dict[str, type[SourceAdapter]] = {" in sources_text
    assert "def build_adapter(" in sources_text
    assert "test_refresh_embeds_all_facet_rows" in test_text
    assert "test_search_ladder_narrows_via_activation_gradient" in test_text
    assert "test_raw_seed_navigation_source_indexes_runtime_groups" in test_text
    assert "test_std_python_atom_parser_splits_contract_atoms" in test_text


def test_nvidia_nim_provider_boundary_source_manifest_matches_exact_macro_sources() -> None:
    _assert_source_manifest_matches_exact_macro_sources(
        NVIDIA_NIM_PROVIDER_BOUNDARY_MANIFEST,
        manifest_id="nvidia_nim_provider_boundary_source_modules_import",
        module_count=2,
    )


def test_nvidia_nim_provider_boundary_sources_compile_and_expose_no_live_probe_status() -> None:
    nvidia_source = BUNDLE_INPUT / "source_modules/system/lib/nvidia_nim.py"
    registry_source = BUNDLE_INPUT / "source_modules/system/lib/model_profile_registry.py"
    source_modules_root = BUNDLE_INPUT / "source_modules"

    nvidia_text = nvidia_source.read_text(encoding="utf-8")
    registry_text = registry_source.read_text(encoding="utf-8")

    compile(nvidia_text, str(nvidia_source), "exec")
    compile(registry_text, str(registry_source), "exec")
    assert "def runtime_status(" in nvidia_text
    assert "def chat_completion(" in nvidia_text
    assert "def embed_texts(" in nvidia_text
    assert "def rerank_passages(" in nvidia_text
    assert "def nvidia_model_id(" in registry_text
    assert "def build_free_claude_code_env(" in registry_text

    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json, sys; "
                f"sys.path.insert(0, {str(source_modules_root)!r}); "
                "from system.lib import nvidia_nim; "
                "status = nvidia_nim.runtime_status("
                "config={'api_key': 'public-test-redacted', 'model': 'glm5'}, "
                "probe_live=False); "
                "print(json.dumps(status, sort_keys=True))"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    status = json.loads(probe.stdout)
    assert status["live_probe"] == {
        "status": "not_run",
        "reason": "probe_live_disabled",
    }
    assert status["configured"]["api_key_present"] is True
    assert status["configured"]["chat_model"] == "z-ai/glm5"


def test_agent_provider_router_source_manifest_matches_exact_macro_sources() -> None:
    _assert_source_manifest_matches_exact_macro_sources(
        AGENT_PROVIDER_ROUTER_MANIFEST,
        manifest_id="agent_provider_router_source_modules_import",
        module_count=2,
    )


def test_agent_provider_router_sources_compile_and_expose_no_live_probe_dispatch() -> None:
    provider_source = BUNDLE_INPUT / "source_modules/system/lib/agent_providers.py"
    openrouter_source = (
        BUNDLE_INPUT / "source_modules/system/lib/openrouter_free_runtime.py"
    )
    source_modules_root = BUNDLE_INPUT / "source_modules"

    provider_text = provider_source.read_text(encoding="utf-8")
    openrouter_text = openrouter_source.read_text(encoding="utf-8")

    compile(provider_text, str(provider_source), "exec")
    compile(openrouter_text, str(openrouter_source), "exec")
    assert "def resolve_provider_callable(" in provider_text
    assert "def ask_openrouter(" in provider_text
    assert "def runtime_status(" in openrouter_text
    assert "DEFAULT_CHAT_MODEL = FREE_ROUTER_MODEL_ID = \"openrouter/free\"" in openrouter_text

    code = f"""
import json
import sys

sys.path.insert(0, {str(source_modules_root)!r})
from system.lib import agent_providers, openrouter_free_runtime

status = openrouter_free_runtime.runtime_status(
    config={{"api_key": "public-test-redacted"}},
    probe_live=False,
)
resolved = {{
    name: agent_providers.resolve_provider_callable(name).__name__
    for name in ["claude", "codex", "nvidia", "openrouter-free"]
}}
paid_blocked = False
try:
    openrouter_free_runtime.chat_completion_packet(
        "fixture",
        config={{"api_key": "public-test-redacted", "model": "openai/gpt-4o"}},
    )
except RuntimeError as exc:
    paid_blocked = "paid model call blocked" in str(exc)

print(
    json.dumps(
        {{"status": status, "resolved": resolved, "paid_blocked": paid_blocked}},
        sort_keys=True,
    )
)
"""
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(probe.stdout)
    status = payload["status"]
    assert status["live_probe"] == {
        "status": "not_run",
        "reason": "probe_live_disabled",
    }
    assert status["configured"]["api_key_present"] is True
    assert status["policy"]["no_spend_default"] is True
    assert status["policy"]["chat_completion"]["default_model"] == "openrouter/free"
    assert payload["resolved"] == {
        "claude": "ask_claude",
        "codex": "ask_codex",
        "nvidia": "ask_nvidia",
        "openrouter-free": "ask_openrouter",
    }
    assert payload["paid_blocked"] is True


def test_bridge_route_config_source_manifest_matches_exact_macro_sources() -> None:
    _assert_source_manifest_matches_exact_macro_sources(
        BRIDGE_ROUTE_CONFIG_MANIFEST,
        manifest_id="bridge_route_config_source_modules_import",
        module_count=2,
    )


def test_bridge_route_config_sources_compile_and_preserve_route_overlay_behavior() -> None:
    bridge_source = BUNDLE_INPUT / "source_modules/system/lib/bridge_routes.py"
    test_source = (
        BUNDLE_INPUT
        / "source_modules/system/server/tests/test_bridge_routes.py"
    )
    source_modules_root = BUNDLE_INPUT / "source_modules"

    bridge_text = bridge_source.read_text(encoding="utf-8")
    test_text = test_source.read_text(encoding="utf-8")

    compile(bridge_text, str(bridge_source), "exec")
    compile(test_text, str(test_source), "exec")
    assert "def merge_bridge_config_with_route(" in bridge_text
    assert "def bridge_timeout_seconds(" in bridge_text
    assert "test_merge_bridge_config_with_route_merges_timings_and_meta" in test_text
    assert "test_bridge_timeout_seconds_prefers_route_override" in test_text

    code = f"""
import json
import sys

sys.path.insert(0, {str(source_modules_root)!r})
from system.lib import bridge_routes

config = {{
    "platform": "gemini",
    "meta": {{"launch_profile": "experimental"}},
    "bridge": {{
        "monitor_timeout_s": {{"value": 1500}},
        "timings": {{
            "post_paste_sleep": {{"value": 1.5}},
            "transport_retry_sleep": {{"value": 0.75}},
        }},
        "routes": {{
            "kernel_probe": {{
                "meta": {{"lane": "kernel_probe"}},
                "monitor_timeout_s": {{"value": 2400}},
                "timings": {{
                    "post_paste_sleep": {{"value": 1.75}},
                }},
            }}
        }},
    }},
}}
merged, route_name = bridge_routes.merge_bridge_config_with_route(
    config,
    explicit_route="kernel_probe",
)
payload = {{
    "route_name": route_name,
    "bridge_route": merged["bridge_route"],
    "meta": merged["meta"],
    "timings": merged["bridge"]["timings"],
    "timeout": bridge_routes.bridge_timeout_seconds(
        config,
        default=1500.0,
        route_name="kernel_probe",
    ),
    "original_post_paste_sleep": config["bridge"]["timings"]["post_paste_sleep"]["value"],
}}
print(json.dumps(payload, sort_keys=True))
"""
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(probe.stdout)
    assert payload["route_name"] == "kernel_probe"
    assert payload["bridge_route"] == "kernel_probe"
    assert payload["meta"] == {
        "lane": "kernel_probe",
        "launch_profile": "experimental",
    }
    assert payload["timings"]["post_paste_sleep"]["value"] == 1.75
    assert payload["timings"]["transport_retry_sleep"]["value"] == 0.75
    assert payload["timeout"] == 2400.0
    assert payload["original_post_paste_sleep"] == 1.5


def test_kernel_bridge_config_source_manifest_matches_exact_macro_sources() -> None:
    _assert_source_manifest_matches_exact_macro_sources(
        KERNEL_BRIDGE_CONFIG_MANIFEST,
        manifest_id="kernel_bridge_config_source_modules_import",
        module_count=3,
    )


def test_kernel_bridge_config_sources_compile_and_preserve_master_config_runtime_contract() -> None:
    config_source = BUNDLE_INPUT / "source_modules/system/lib/kernel/config.py"
    state_source = BUNDLE_INPUT / "source_modules/system/lib/kernel/state.py"
    test_source = (
        BUNDLE_INPUT
        / "source_modules/system/server/tests/test_master_config_loader_parity.py"
    )
    source_modules_root = BUNDLE_INPUT / "source_modules"

    config_text = config_source.read_text(encoding="utf-8")
    state_text = state_source.read_text(encoding="utf-8")
    test_text = test_source.read_text(encoding="utf-8")

    compile(config_text, str(config_source), "exec")
    compile(state_text, str(state_source), "exec")
    compile(test_text, str(test_source), "exec")
    assert "def load_master_config_at(" in config_text
    assert "def resolve_bridge_runtime_config(" in config_text
    assert "def coerce_bridge_workers_arg(" in config_text
    assert "DEFAULT_BRIDGE_TIMEOUT_S = 1500.0" in state_text
    assert "def init(repo_root: Path) -> None:" in state_text
    assert "test_master_config_loader_parity" in test_text

    code = f"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, {str(source_modules_root)!r})
from system.lib.kernel import config as kernel_config
from system.lib.kernel import state as kernel_state

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp).resolve()
    kernel_state.REPO_ROOT = root
    (root / "master_config.json").write_text(
        json.dumps({{
            "bridge": {{
                "default_target": {{"value": "gemini"}},
                "monitor_timeout_s": {{"value": 1200}},
                "routes": {{
                    "kernel_probe": {{
                        "default_target": {{"value": "codex"}},
                        "monitor_timeout_s": {{"value": 44}},
                        "timings": {{"post_paste_sleep": {{"value": 1.25}}}},
                    }}
                }},
            }}
        }}),
        encoding="utf-8",
    )
    runtime_config, provider = kernel_config.resolve_bridge_runtime_config(
        provider="",
        timeout_s=33,
        bridge_route="kernel_probe",
    )
    invalid_workers = "not_checked"
    try:
        kernel_config.coerce_bridge_workers_arg("0")
    except ValueError:
        invalid_workers = "rejected"
    payload = {{
        "loaded_default_target": kernel_config.load_master_config()["bridge"]["default_target"]["value"],
        "missing_fallback": kernel_config.config_value(None, "fallback"),
        "workers_auto": kernel_config.coerce_bridge_workers_arg("auto"),
        "workers_two": kernel_config.coerce_bridge_workers_arg("2"),
        "invalid_workers": invalid_workers,
        "route_timeout": kernel_config.default_bridge_timeout_s(bridge_route="kernel_probe"),
        "provider": provider,
        "runtime_platform": runtime_config["platform"],
        "runtime_timeout": runtime_config["bridge"]["monitor_timeout_s"],
        "route_name": runtime_config["bridge_route"],
        "route_timing": runtime_config["bridge"]["timings"]["post_paste_sleep"]["value"],
    }}
    print(json.dumps(payload, sort_keys=True))
"""
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(probe.stdout)
    assert payload == {
        "invalid_workers": "rejected",
        "loaded_default_target": "gemini",
        "missing_fallback": "fallback",
        "provider": "codex",
        "route_name": "kernel_probe",
        "route_timeout": 44.0,
        "route_timing": 1.25,
        "runtime_platform": "codex",
        "runtime_timeout": 33,
        "workers_auto": "auto",
        "workers_two": "2",
    }


def test_observe_runtime_source_manifest_matches_exact_macro_sources() -> None:
    _assert_source_manifest_matches_exact_macro_sources(
        OBSERVE_RUNTIME_MANIFEST,
        manifest_id="observe_runtime_source_modules_import",
        module_count=5,
    )


def test_observe_runtime_sources_compile_and_preserve_grouped_runtime_contract() -> None:
    source_modules_root = BUNDLE_INPUT / "source_modules"
    source_paths = [
        source_modules_root / "system/lib/codex_paths.py",
        source_modules_root / "system/lib/markdown_routing.py",
        source_modules_root / "system/lib/observe_memory.py",
        source_modules_root / "system/lib/observe_surfaces.py",
        source_modules_root / "system/lib/observe_runtime.py",
    ]
    for source_path in source_paths:
        compile(source_path.read_text(encoding="utf-8"), str(source_path), "exec")

    observe_runtime_text = source_paths[-1].read_text(encoding="utf-8")
    observe_surfaces_text = source_paths[-2].read_text(encoding="utf-8")
    assert "def resolve_group_evidence_contract(" in observe_runtime_text
    assert "def grouped_runtime_status_payload(" in observe_runtime_text
    assert "def request_grouped_runtime_cancel(" in observe_runtime_text
    assert "def build_observe_resume_surface(" in observe_surfaces_text

    code = f"""
import json
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, {str(source_modules_root)!r})
from system.lib import observe_runtime, observe_surfaces

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / "master_config.json").write_text(
        json.dumps({{
            "observe": {{
                "max_recommended_prompt_chars": {{"value": 12345}},
                "max_hard_prompt_chars": {{"value": 45678}},
            }},
            "execution": {{"max_workers": {{"value": 4}}}},
        }}),
        encoding="utf-8",
    )
    budget = observe_runtime.resolve_bridge_prompt_budget(root)
    workers = observe_runtime.resolve_effective_workers(
        repo_root=root,
        requested_workers="auto",
        launch_profile="safe",
        wave_size=10,
    )
    evidence = observe_runtime.resolve_group_evidence_contract(
        root,
        plan_context_files=["docs/plan.md", "src/app.py"],
        group_context_files=["docs/group.md"],
        targets=[{{"file": "src/app.py", "scope": "full"}}],
    )
    waves, wave_by_label = observe_runtime.grouped_observe_waves([
        {{"label": "first"}},
        {{"label": "second", "depends_on": ["first"]}},
    ])
    history_dir = root / "tools/meta/apply/observe_history"
    history_entry = history_dir / "entries/OBS_PUBLIC.json"
    history_entry.parent.mkdir(parents=True, exist_ok=True)
    history_entry.write_text(
        json.dumps({{
            "observe_id": "OBS_PUBLIC",
            "result_note": {{"path": "obsidian/results/final.md"}},
            "continuation": {{"read_paths": ["obsidian/results/final.md"]}},
            "groups": [
                {{
                    "label": "done",
                    "role": "probe",
                    "response_file": "responses/done.md",
                    "response_status": "success",
                }}
            ],
        }}),
        encoding="utf-8",
    )
    observe_runtime.write_grouped_runtime_manifest(
        history_dir,
        {{
            "kind": "grouped_observe",
            "observe_id": "OBS_PUBLIC",
            "state": "dispatching",
            "launch_profile": "safe",
            "requested_workers": "auto",
            "effective_workers": 2,
            "wave_index": 0,
            "wave_total": 1,
            "total_groups": 2,
            "completed_groups": 1,
            "pid": None,
            "updated_at": "2026-05-25T00:00:00+00:00",
            "groups": [
                {{"label": "done", "runtime_state": "success", "response_status": "success"}},
                {{"label": "pending", "runtime_state": "running"}},
            ],
            "artifacts": {{
                "history_entry": "tools/meta/apply/observe_history/entries/OBS_PUBLIC.json",
                "latest_stable_artifact": "obsidian/results/final.md",
            }},
        }},
    )
    status = observe_runtime.grouped_runtime_status_payload(root, history_dir, "OBS_PUBLIC")
    continuation = observe_surfaces.build_grouped_observe_continuation(
        result_note_rel="obsidian/results/final.md",
        synthesis_summary={{"path": "obsidian/results/_synthesis.md"}},
        groups_payload=[
            {{
                "label": "done",
                "response_surface_file": "responses/done.surface.json",
                "response_file": "responses/done.md",
            }}
        ],
    )
    payload = {{
        "budget": budget,
        "workers": workers,
        "evidence": evidence,
        "waves": waves,
        "wave_by_label": wave_by_label,
        "status": status,
        "continuation": continuation,
    }}
    print(json.dumps(payload, sort_keys=True))
"""
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(probe.stdout)
    assert payload["budget"] == {
        "recommended_prompt_chars": 12345,
        "hard_prompt_chars": 45678,
    }
    assert payload["workers"]["effective_workers"] == 4
    assert payload["workers"]["launch_profile"] == "safe"
    assert payload["evidence"]["effective_context_files"] == [
        "docs/plan.md",
        "docs/group.md",
    ]
    assert payload["evidence"]["context_target_overlaps"] == ["src/app.py"]
    assert payload["waves"] == [["first"], ["second"]]
    assert payload["wave_by_label"] == {"first": 0, "second": 1}
    assert payload["status"]["state"] == "dispatching"
    assert payload["status"]["latest_stable_artifact"] == "obsidian/results/final.md"
    assert payload["status"]["can_continue"] is True
    assert payload["status"]["continue_mode"] == "resume_pending"
    assert payload["status"]["pending_group_labels"] == ["pending"]
    assert payload["status"]["progress"]["percent_complete"] == 50
    assert payload["status"]["resume_surface"]["preferred_artifact"] == (
        "obsidian/results/final.md"
    )
    assert payload["continuation"]["read_paths"] == [
        "obsidian/results/final.md",
        "obsidian/results/_synthesis.md",
        "responses/done.surface.json",
        "responses/done.md",
    ]


def test_kernel_state_registry_source_manifest_matches_exact_macro_sources() -> None:
    _assert_source_manifest_matches_exact_macro_sources(
        KERNEL_STATE_REGISTRY_MANIFEST,
        manifest_id="kernel_state_registry_source_modules_import",
        module_count=2,
    )


def test_kernel_state_registry_sources_compile_and_preserve_path_and_registry_contract() -> None:
    source_modules_root = BUNDLE_INPUT / "source_modules"
    source_paths = [
        source_modules_root / "system/lib/observe_assets.py",
        source_modules_root / "system/lib/standards_registry.py",
    ]
    for source_path in source_paths:
        compile(source_path.read_text(encoding="utf-8"), str(source_path), "exec")

    observe_assets_text = source_paths[0].read_text(encoding="utf-8")
    standards_registry_text = source_paths[1].read_text(encoding="utf-8")
    assert "def observe_asset_paths(" in observe_assets_text
    assert "OBSERVE_TREE_RUNTIME_RELS = (" in observe_assets_text
    assert "def build_standards_catalog(" in standards_registry_text
    assert "STANDARDS_REGISTRY_PATH" in standards_registry_text

    code = f"""
import json
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, {str(source_modules_root)!r})
from system.lib import observe_assets, standards_registry

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp).resolve()
    authority_index = root / "codex/standards/observe/authority_index.json"
    authority_index.parent.mkdir(parents=True, exist_ok=True)
    authority_index.write_text(
        json.dumps({{
            "artifacts": {{
                "observe_plan": {{
                    "description": "fixture observe plan",
                    "json_standard": "codex/standards/observe/std_observe_general.json",
                    "path_globs": ["tools/meta/apply/observe_plans/*.json"],
                    "lifecycle": "runtime_fixture",
                    "authority_rule": "source_only_fixture",
                }}
            }},
            "supporting_assets": {{"template": {{"path": "templates/observe.json"}}}},
        }}),
        encoding="utf-8",
    )
    registry = root / standards_registry.STANDARDS_REGISTRY_PATH
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        json.dumps({{
            "root": "codex/standards",
            "purpose": "fixture registry",
            "kernel_navigation_hints": ["fixture"],
            "groups": [
                {{
                    "group_id": "observe",
                    "title": "Observe",
                    "group_root": "codex/standards/observe",
                    "authority_index": "codex/standards/observe/authority_index.json",
                    "summary": "fixture group",
                    "storage_status": "local_fixture",
                    "kernel_navigation_hints": ["observe"],
                }}
            ],
        }}),
        encoding="utf-8",
    )
    assets = observe_assets.observe_asset_paths(root)
    catalog = standards_registry.build_standards_catalog(repo_root=root)
    payload = {{
        "observe_plan": str(assets.observe_plan.relative_to(root)),
        "tree_manifest": str(assets.tree_manifest.relative_to(root)),
        "runtime_rel_count": len(observe_assets.OBSERVE_TREE_RUNTIME_RELS),
        "canonical_doc_count": len(observe_assets.OBSERVE_TREE_CANONICAL_DOC_RELS),
        "registry_path": catalog["registry_path"],
        "group_count": len(catalog["groups"]),
        "artifact_count": catalog["groups"][0]["artifact_count"],
        "supporting_asset_count": catalog["groups"][0]["supporting_asset_count"],
        "artifact_kind": catalog["groups"][0]["artifacts"][0]["artifact_kind"],
    }}
    print(json.dumps(payload, sort_keys=True))
"""
    probe = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(probe.stdout)
    assert payload == {
        "artifact_count": 1,
        "artifact_kind": "observe_plan",
        "canonical_doc_count": 13,
        "group_count": 1,
        "observe_plan": "tools/meta/apply/observe_plan.json",
        "registry_path": "codex/standards/standards_registry.json",
        "runtime_rel_count": 14,
        "supporting_asset_count": 1,
        "tree_manifest": "codex/derived/observe/tree_manifest.json",
    }


def _load_trace_capsule_source_module():
    module_path = (
        BUNDLE_INPUT
        / "source_modules/tools/meta/observability/cli_prompt_trace.py"
    )
    spec = importlib.util.spec_from_file_location(
        "microcosm_trace_capsule_source_module",
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def _load_route_selection_intervention_source_module():
    module_path = (
        BUNDLE_INPUT
        / "source_modules/system/lib/navigation_route_intervention.py"
    )
    spec = importlib.util.spec_from_file_location(
        "microcosm_route_selection_intervention_source_module",
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def test_trace_capsule_cli_prompt_trace_source_module_renders_public_fixture() -> None:
    module = _load_trace_capsule_source_module()
    output = "Process exited with code 0\nOutput:\ncompiled fixture"
    turn = module.Turn(
        provider="codex",
        session_id="public-fixture-session",
        session_file="public-fixture-session.jsonl",
        turn_id="turn_public_fixture",
        turn_index=1,
        cwd="microcosm-substrate",
        started_at="2026-05-25T00:00:00Z",
        completed_at="2026-05-25T00:01:00Z",
        prompt_text="Render a public Trace Capsule fixture.",
        prompt_char_count=len("Render a public Trace Capsule fixture."),
        prompt_sha256_16="fixturepromptsha",
        tool_events=[
            module.ToolEvent(
                index=1,
                name="functions.exec_command",
                input={"cmd": "./repo-python -m py_compile public_fixture.py"},
                tool_call_id="call_public_fixture",
                started_at="2026-05-25T00:00:01Z",
                completed_at="2026-05-25T00:00:02Z",
                duration_ms=1000,
                is_error=False,
                output_text=output,
                output_char_count=len(output),
                output_sha256_16=module._sha16(output),
                exit_code=0,
                source_record_indices=[10, 11],
            )
        ],
        assistant_text="Validation passed.",
        assistant_events=[module.AssistantEvent("Validation passed.", 12)],
        is_complete=True,
        source_record_indices=[1, 2, 10, 11, 12],
        source_ref={"raw_authority": "public_fixture"},
    )

    text, meta = module.render_trace_capsule_text(
        turn,
        title="Public Trace Capsule Fixture",
    )

    assert text.startswith("TRACE CAPSULE v3\n")
    assert "final_validation: passed" in text
    assert "terminal_checks: pass=1 fail=0 other=0 total=1" in text
    assert "not_included: hidden_reasoning" in text
    assert meta["terminal_validation_pass_count"] == 1
    assert meta["closeout_present"] is True
    assert "/Users/" not in text


def test_route_selection_intervention_source_module_builds_public_route_repair_suggestion() -> None:
    module = _load_route_selection_intervention_source_module()

    suggestion = module.route_repair_for(
        anti_pattern_id="anti_pattern_grep_before_kernel"
    )

    assert suggestion is not None
    payload = suggestion.to_dict()
    assert payload["repair_class"] == "hook_steering_plus_context_pack_first_contact"
    assert payload["suggested_sequence"][0].startswith("./repo-python kernel.py --entry")
    assert "skills:navigation_metabolism" in payload["expected_artifacts"]


def test_agent_trace_structurer_parser_source_module_runs_node_fixture_tests() -> None:
    parser_test = (
        BUNDLE_INPUT
        / "source_modules/tools/agent_trace_structurer/parser.test.mjs"
    )

    result = subprocess.run(
        ["node", "--test", str(parser_test.name)],
        cwd=parser_test.parent,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stdout + result.stderr
