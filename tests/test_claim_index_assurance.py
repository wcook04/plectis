"""Adversarial v3 joins plus the actual existing static-resource consumer."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

CANDIDATE = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get("PLECTIS_PROTOTYPE_SOURCE_ROOT", str(CANDIDATE))).resolve()
from microcosm_core.projections import component_assurance as builder
from microcosm_core import component_index


def _current_runner_lens(root, registry):
    """Use the public lens parser on registered runner files, without a project scan."""
    from microcosm_core.project_substrate import _python_span_projection

    refs = sorted({builder._runner_source_ref(row.get("runner"))
                   for row in registry["implemented_organs"]} - {None})
    rows = []
    for ref in refs:
        projection = _python_span_projection(ref, (root / ref).read_text())
        assert projection["parse_status"] == "parsed", ref
        rows.extend(projection["symbol_capsule_rows"])
    return {"payload_boundary": {"source_bodies_exported": False}, "symbol_capsule_rows": rows}


@pytest.fixture(scope="session")
def owners():
    captured = sys.modules.get("_claim_index_validated_state")
    if captured is not None:
        return captured.owners
    registry = json.loads((SOURCE / "core/organ_registry.json").read_text())
    atlas = json.loads((SOURCE / "core/organ_atlas.json").read_text())
    proposals = {path.parent.name: json.loads(path.read_text())
                 for path in (CANDIDATE / "formal/components").glob("*/metadata.json")}
    tools = __import__("runpy").run_path(str(SOURCE / "scripts/check/check_component_kernels.py"))
    assurance = builder.collect_claim_assurance_inputs(SOURCE, registry, atlas, proof_tools=tools,
                                                     metadata_proposals=proposals)
    # The stable published resource is v3 after integration. Build the strict v2
    # input from current source evidence instead of treating that output as input.
    routes = json.loads((SOURCE / "atlas/agent_task_routes.json").read_text())
    base = builder.build_join_index(_current_runner_lens(SOURCE, registry), registry,
                                    atlas=atlas, routes=routes, capsules=assurance["capsules"])
    return base, registry, atlas, assurance


def _index(owners):
    return builder.extend_claim_index(*owners)


def test_fixture_base_comes_from_current_lens_not_the_published_resource(owners):
    base, registry, _, _ = owners
    assert base["schema_version"] == builder.SCHEMA_VERSION
    lens = _current_runner_lens(SOURCE, registry)
    expected = builder._file_rollups(lens["symbol_capsule_rows"])
    assert base["nodes"]["source_file"]
    for row in base["nodes"]["source_file"]:
        assert row == {"path": row["path"], **expected[row["path"]]}


@pytest.fixture
def join_cli():
    path = CANDIDATE / "scripts/build/build_code_lens_join_index.py"
    spec = importlib.util.spec_from_file_location("claim_assurance_cli", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_default_lens_build_stays_v2(owners, join_cli, tmp_path):
    lens = tmp_path / "lens.json"
    lens.write_text(json.dumps(_current_runner_lens(SOURCE, owners[1])))
    out = tmp_path / "index.json"
    assert join_cli.main(["--lens", str(lens), "--registry", str(SOURCE / "core/organ_registry.json"),
                          "--atlas", str(SOURCE / "core/organ_atlas.json"),
                          "--routes", str(SOURCE / "atlas/agent_task_routes.json"),
                          "--capsules", str(SOURCE / "core/paper_module_capsules.json"),
                          "--out", str(out)]) == 0
    assert json.loads(out.read_text())["schema_version"] == builder.SCHEMA_VERSION


@pytest.mark.parametrize("source_kind", ["lens", "v2_base"])
def test_cli_explicit_assurance_can_regenerate_without_a_saved_v2_master(owners, join_cli, monkeypatch, tmp_path, source_kind):
    monkeypatch.setattr(join_cli, "proof_binding_tools", lambda root: {})
    monkeypatch.setattr(join_cli, "collect_claim_assurance_inputs", lambda *args, **kwargs: copy.deepcopy(owners[3]))
    source = tmp_path / "source.json"
    source.write_text(json.dumps(_current_runner_lens(SOURCE, owners[1]) if source_kind == "lens" else owners[0]))
    out = tmp_path / "index.json"
    args = ["--claim-assurance", "--repo-root", str(SOURCE), "--out", str(out),
            "--lens" if source_kind == "lens" else "--base-index", str(source)]
    assert join_cli.main(args) == 0
    first = out.read_bytes()
    component_index.validate_index(json.loads(first))
    assert join_cli.main(args) == 0
    assert out.read_bytes() == first


def test_cli_v3_output_is_not_a_v2_base_or_a_reason_to_collect_proofs(owners, join_cli, monkeypatch, tmp_path, capsys):
    def unexpected(*args, **kwargs):
        raise AssertionError("invalid base must be rejected before proof collection")

    monkeypatch.setattr(join_cli, "proof_binding_tools", unexpected)
    monkeypatch.setattr(join_cli, "collect_claim_assurance_inputs", unexpected)
    out = tmp_path / "published.json"
    out.write_text(json.dumps(_index(owners)))
    before = out.read_bytes()
    with pytest.raises(SystemExit) as exc:
        join_cli.main(["--claim-assurance", "--repo-root", str(SOURCE), "--base-index", str(out), "--out", str(out)])
    assert exc.value.code == 2
    assert "saved v2 join index" in capsys.readouterr().err
    assert out.read_bytes() == before


def test_published_navigation_matches_current_route_owner():
    published = json.loads((SOURCE / component_index.INDEX_REF).read_text())
    source = json.loads((SOURCE / "atlas/agent_task_routes.json").read_text())
    current = {row["task_class"]: row for row in source["routes"]}
    actual = {row["task_class"]: row for row in published["nodes"]["route"]}
    assert set(actual) == set(current)
    for task_class, row in actual.items():
        for field in ("primary_organ_id", "first_command", "allowed_scope", "stop_condition"):
            assert row.get(field) == current[task_class].get(field), (task_class, field)


def test_exact_universe_and_narrow_proof_nodes(owners):
    index = _index(owners)
    base, registry, _, _ = owners
    ids = {row["organ_id"] for row in registry["implemented_organs"]}
    assert index["schema_version"] == "microcosm_code_lens_join_index_v3"
    assert {row["claim_id"] for row in index["nodes"]["claim"]} == {"claim::" + oid for oid in ids}
    assert len(index["nodes"]["claim"]) == len(ids)
    assert index["nodes"]["source_file"] == base["nodes"]["source_file"]
    assert len(index["nodes"]["subclaim"]) == len(index["nodes"]["proof"]) == len(owners[3]["proofs"])
    assert index["rollup"]["claim_node_count"] == len(ids)
    assert index["source_bodies_exported"] is False
    assert "proof_internal_structure" not in index["graph"]["resolved_edge_classes"]
    assert any(row["edge_class"] == "proof_internal_structure" for row in index["graph"]["deferred_edge_classes"])
    assert all(row["fresh_prover_result"] == {"status": "not_run_by_index"} for row in index["nodes"]["proof"])
    assert all(row["requirements_review"] == {"status": "unrecorded"} for row in index["nodes"]["subclaim"])
    assert all("verified" not in row["card"] for row in index["nodes"]["claim"])
    legacy = [edge for edge in index["edges"] if edge["kind"] == "proven_by"]
    assert legacy == [edge for edge in base["edges"] if edge["kind"] == "proven_by"]
    assert "never a domain theorem" in index["graph"]["edge_semantics"]["proven_by"]


def test_coverage_facets_have_exact_units_and_unknown_whole_claim_scope(owners):
    index = _index(owners)
    coverage = component_index.coverage_view(index)
    total = len(owners[1]["implemented_organs"])
    selected = {binding["organ_id"] for row in owners[3]["proofs"] for binding in row["contract"]["component_bindings"]}
    metric = coverage["component_presence"]["narrow_domain_contracts"]
    assert (metric["numerator"], metric["denominator"], metric["percentage"]) == (len(selected), total, round(100 * len(selected) / total, 1))
    assert coverage["whole_claim_coverage"] == {"status": "not_exhaustively_mapped", "numerator": None, "denominator": None, "percentage": None}
    assert sum(coverage["evidence_class_counts"].values()) == total
    assert coverage["component_presence"]["configured_replay_routes"]["numerator"] == total
    assert "not execution" in coverage["component_presence"]["configured_replay_routes"]["kind"]
    assert coverage["fresh_results"]["prover"]["recorded_count"] == coverage["fresh_results"]["replay"]["recorded_count"] == 0
    control_count = sum(len(row["metadata"]["negative_sources"]) for row in owners[3]["proofs"])
    assert coverage["component_presence"]["source_linked_mutation_controls"]["record_count"] == control_count
    assert all(row["card"]["assurance_facets"]["requirements_review"] == {"status": "unrecorded"} for row in index["nodes"]["claim"])


def test_batch_views_match_standalone_and_do_not_share_mutable_state(owners):
    index = _index(owners)
    views = component_index.compile_views(index)
    assert views["list"] == component_index.list_components(index)
    assert views["by_component"]["mcp_tool_authority_replay"] == component_index.get_component(index, "mcp_tool_authority_replay")
    assert views["coverage"] == component_index.coverage_view(index)
    views["by_component"]["mcp_tool_authority_replay"]["claim"]["card"]["summary"] = "changed by client"
    assert component_index.get_component(index, "mcp_tool_authority_replay")["claim"]["card"]["summary"] != "changed by client"


@pytest.mark.parametrize("defect", ["foreign_native", "duplicate_native", "foreign_result"])
def test_historical_observations_cannot_be_reassigned_or_counted_twice(owners, defect):
    index = _index(owners)
    native = next(row for row in index["nodes"]["claim"] if row["organ_id"] == "formal_math_lean_proof_witness")
    ordinary = next(row for row in index["nodes"]["claim"] if row["organ_id"] == "belief_state_process_reward_replay")
    records = native["card"]["assurance_facets"]["native_verification"]["historical_native_records"]
    if defect == "foreign_native":
        ordinary["card"]["assurance_facets"]["native_verification"]["historical_native_records"] = copy.deepcopy(records)
    elif defect == "duplicate_native":
        records.append(copy.deepcopy(records[0]))
    else:
        replay = next(row for row in index["nodes"]["replay"] if row["organ_id"] == ordinary["organ_id"])
        replay["last_result"] = copy.deepcopy(next(row for row in index["nodes"]["replay"] if row["organ_id"] == native["organ_id"])["last_result"])
        ordinary["card"]["assurance_facets"]["replay"]["last_result"] = copy.deepcopy(replay["last_result"])
    index["assurance"]["coverage"] = component_index._coverage_from_facets(index)
    with pytest.raises(ValueError):
        component_index.validate_index(index)


def test_universe_is_registry_not_magic_count_or_capsule_subjects(owners):
    _, registry, atlas, assurance = copy.deepcopy(owners)
    # This fixture deliberately builds a smaller source universe. Its optional
    # explorer projection was collected for the full registry and is not reused.
    assurance.pop("explorer", None)
    ids = {"belief_state_process_reward_replay", "formal_math_lean_proof_witness"}
    registry["implemented_organs"] = [row for row in registry["implemented_organs"] if row["organ_id"] in ids]
    atlas["organs"] = [row for row in atlas["organs"] if row["organ_id"] in ids]
    for row in atlas["organs"]:
        row["wires_to"] = []
    assurance["evidence_classes"]["organ_evidence_classes"] = [
        row for row in assurance["evidence_classes"]["organ_evidence_classes"] if row["organ_id"] in ids]
    assurance["replays"] = [row for row in assurance["replays"] if row["organ_id"] in ids]
    assurance["proofs"] = []
    directories = {row["example_rel"] for row in assurance["replays"]}
    directories.update(row["declared_route"]["example_rel"] for row in assurance["replays"] if "declared_route" in row)
    histories = {ref for row in registry["implemented_organs"] for ref in [row["current_authority_receipt"], *row["generated_receipts"],
                 *([row["historical_source_authority_receipt"]] if row.get("historical_source_authority_receipt") else [])]}
    assurance["references"] = {ref: fact for ref, fact in assurance["references"].items()
                               if (fact["kind"] != "directory" or ref in directories)
                               and (fact["kind"] != "historical_asset" or ref in histories)}
    base = builder.build_join_index({}, registry, atlas=atlas)
    result = builder.extend_claim_index(base, registry, atlas, assurance)
    assert result["assurance"]["component_count"] == 2
    assert len(result["nodes"]["claim"]) == 2
    assert result["nodes"]["proof"] == []


def test_primary_guide_uses_atlas_pointer_even_without_subject(owners):
    base, registry, atlas, assurance = copy.deepcopy(owners)
    selected = "batch7_oracle_sibling_capsule"
    capsule = builder._primary_guides(builder._unique(atlas["organs"], "organ_id", "atlas"), assurance["capsules"])[selected]
    capsule["subjects"] = []
    index = builder.extend_claim_index(base, registry, atlas, assurance)
    claim = next(row for row in index["nodes"]["claim"] if row["organ_id"] == selected)
    assert claim["card"]["primary_guide_ref"] == capsule["legacy_markdown_projection"]


def test_actual_consumer_reads_v3_via_stable_resource_path(owners, tmp_path):
    from microcosm_core import comprehension

    index = _index(owners)
    resources = {"receipts/code_lens/code_lens_join_index_v0.json": index,
                 "core/organ_atlas.json": owners[2], "core/paper_module_capsules.json": owners[3]["capsules"]}
    for relative, value in resources.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
    inputs = comprehension.load_inputs(tmp_path)
    for oid in ("mcp_tool_authority_replay", "belief_state_process_reward_replay", "formal_math_lean_proof_witness"):
        trace = comprehension.compile_claim_trace(inputs, oid)
        assert trace["found"]
        assert trace["selected_nodes"][0]["card"]["title"]
        assert trace["selected_nodes"][0]["card"]["evidence"]["fresh_run_status"] == "not_run_by_index"
        assert trace["graph_backed"]["source_schema"] == "microcosm_code_lens_join_index_v3"
        assert comprehension.compile_flow(inputs, oid)["found"]
        assert comprehension.compile_organ(inputs, oid)["organ_id"] == oid
    assert set(inputs["join_by_organ"]) == {row["organ_id"] for row in owners[1]["implemented_organs"]}
    # Existing readers filter edge kinds; the data is retained, without claiming
    # that a new frontend or multi-hop proof browser has been implemented.
    assert "has_retained_formal_proof" not in trace["edge_kinds_included"]
    assert inputs["join_index"]["graph"]["edge_kind_counts"]["has_retained_formal_proof"] > 0
    old_path = tmp_path / "receipts/code_lens/code_lens_join_index_v0.json"
    old_path.write_text(json.dumps(owners[0]))
    old = comprehension.load_inputs(tmp_path)
    assert old["join_index"]["schema_version"] == "microcosm_code_lens_join_index_v2"
    for oid in ("mcp_tool_authority_replay", "belief_state_process_reward_replay", "formal_math_lean_proof_witness"):
        assert comprehension.compile_claim_trace(old, oid)["found"]
        assert comprehension.compile_flow(old, oid)["found"]
        assert comprehension.compile_organ(old, oid)["organ_id"] == oid


def test_runtime_library_views_and_current_check_are_distinct(owners):
    index = _index(owners)
    component_index.validate_index(index)
    rows = component_index.list_components(index)
    assert len(rows) == len(owners[1]["implemented_organs"])
    view = component_index.get_component(index, "mcp_tool_authority_replay")
    assert view["evidence_state"]["current_backend_binding"] == {"status": "not_checked"}
    assert view["proofs"][0]["proof"]["current_binding"]["assessment_time_basis"] == "index_generation_only"
    checked = component_index.check_component_bindings(index, SOURCE, view["component_id"])
    assert checked["status"] == "indexed_file_hashes_match"
    assert checked["fresh_prover"] == checked["fresh_replay"] == {"status": "not_run"}
    stale = copy.deepcopy(index)
    guide = view["claim"]["card"]["primary_guide_ref"]
    next(row for row in stale["nodes"]["artifact"] if row["ref"] == guide)["sha256"] = "0" * 64
    # The explorer retains each guide's text with its hash, so an index whose
    # artifact hash no longer matches that retained guide is refused outright.
    with pytest.raises(ValueError, match="guide source binding mismatch"):
        component_index.check_component_bindings(stale, SOURCE, view["component_id"])
    assert view["evidence_state"]["fresh_prover"]["status"] == "not_recorded_by_index"
    for value in ("../arbitrary", "invented_component"):
        with pytest.raises(component_index.UnknownComponent):
            component_index.get_component(index, value)


def test_pure_join_never_reads_files(owners, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("pure join attempted filesystem IO")
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    assert _index(owners)["schema_version"] == "microcosm_code_lens_join_index_v3"


def test_pure_join_returns_detached_nested_values(owners):
    before = json.dumps(owners, sort_keys=True)
    result = _index(owners)
    result["nodes"]["proof"][0]["current_binding"]["generated_python"].clear()
    result["nodes"]["proof"][0]["entry_theorem_refs"].clear()
    result["assurance"]["owner_refs"].clear()
    assert json.dumps(owners, sort_keys=True) == before
    assert _index(owners)["nodes"]["proof"]


def test_reference_map_order_does_not_change_export(owners):
    base, registry, atlas, assurance = copy.deepcopy(owners)
    assurance["references"] = dict(reversed(list(assurance["references"].items())))
    assert builder.extend_claim_index(base, registry, atlas, assurance) == _index(owners)


def test_replay_descriptor_does_not_execute_configuration(owners, monkeypatch):
    import subprocess
    def forbidden(*args, **kwargs):
        raise AssertionError("descriptor collection attempted to execute a command")
    monkeypatch.setattr(subprocess, "run", forbidden)
    registry = builder._unique(owners[1]["implemented_organs"], "organ_id", "components")
    rows = builder._read_replay_descriptors(SOURCE, registry)
    assert len(rows) == len(registry)


def test_collector_rejects_a_replacement_registry_before_loading_proof_tools(owners):
    registry = copy.deepcopy(owners[1])
    registry["implemented_organs"][0]["claim_ceiling"] = "invented replacement authority"
    with pytest.raises(ValueError, match="canonical source owner"):
        builder.collect_claim_assurance_inputs(SOURCE, registry, owners[2], proof_tools={})


@pytest.mark.parametrize("defect", ["body", "fake_fresh", "unknown_proof_field", "unknown_endpoint",
                                    "downgrade_required", "drop_owners", "proof_hash", "generated_hash",
                                    "claim_digest", "contract_digest", "nested_card", "nested_graph", "wrong_command"])
def test_runtime_reader_rejects_unbounded_or_forged_state(owners, defect):
    index = _index(owners)
    if defect == "body":
        index["nodes"]["source_file"][0]["source_body"] = "not allowed"
    elif defect == "fake_fresh":
        index["nodes"]["proof"][0]["fresh_prover_result"] = {"status": "pass"}
    elif defect == "unknown_proof_field":
        index["nodes"]["proof"][0]["arbitrary_payload"] = "not allowed"
    elif defect == "unknown_endpoint":
        index["edges"][0]["from"] = "unknown_endpoint"
    elif defect == "downgrade_required":
        fact = next(row for row in index["nodes"]["artifact"] if row["ref"] == "core/organ_registry.json")
        fact["kind"] = "directory"
        fact.pop("sha256")
    elif defect == "drop_owners":
        index["assurance"]["owner_refs"] = []
    elif defect == "proof_hash":
        index["nodes"]["proof"][0]["current_binding"]["source_sha256"] = "0" * 64
    elif defect == "generated_hash":
        manifest = index["nodes"]["proof"][0]["current_binding"]["generated_python"]
        manifest[next(iter(manifest))] = "0" * 64
    elif defect == "claim_digest":
        index["nodes"]["claim"][0]["card"]["summary"] += " changed"
    elif defect == "contract_digest":
        index["nodes"]["subclaim"][0]["statement"] += " changed"
    elif defect == "nested_card":
        index["nodes"]["claim"][0]["card"]["content"] = "def leaked(): pass"
    elif defect == "nested_graph":
        index["graph"]["content"] = "def leaked(): pass"
    elif defect == "wrong_command":
        index["nodes"]["replay"][0]["primary_execution"]["argv"] = ["sh", "-c", "echo wrong"]
    with pytest.raises(ValueError):
        component_index.validate_index(index)


@pytest.mark.parametrize("defect", ["duplicate_registry", "unknown_class", "missing_replay", "wrong_class",
                                    "duplicate_guide", "unknown_component", "wrong_guide", "stale_source",
                                    "stale_generated", "zero_proof", "forged_status", "source_body_fact", "stale_claim",
                                    "base_body", "unknown_edge_source", "dangling_edge_claim",
                                    "duplicate_edge", "escaping_receipt", "base_graph_body", "base_metadata_body", "base_nested_lens_body"])
def test_fail_closed_joins_and_proof_bindings(owners, defect):
    base, registry, atlas, assurance = copy.deepcopy(owners)
    proof = assurance["proofs"][0]
    if defect == "duplicate_registry":
        registry["implemented_organs"].append(registry["implemented_organs"][0])
    elif defect == "unknown_class":
        assurance["evidence_classes"]["organ_evidence_classes"][0]["organ_id"] = "invented_component"
    elif defect == "missing_replay":
        assurance["replays"].pop()
    elif defect == "wrong_class":
        assurance["evidence_classes"]["organ_evidence_classes"][0]["evidence_class"] = "unproved_invented_class"
    elif defect == "duplicate_guide":
        assurance["capsules"]["paper_modules"].append(assurance["capsules"]["paper_modules"][0])
    elif defect == "unknown_component":
        proof["contract"]["component_bindings"][0]["organ_id"] = "invented_component"
    elif defect == "wrong_guide":
        proof["contract"]["component_bindings"][0]["primary_guide_ref"] = "paper_modules/verifier_lab_kernel.md"
    elif defect == "stale_source":
        proof["metadata"]["source_sha256"] = "0" * 64
    elif defect == "stale_generated":
        proof["metadata"]["generated_python"][proof["module"] + ".py"] = "0" * 64
    elif defect == "zero_proof":
        proof["metadata"]["verified_tasks"] = 0
    elif defect == "forged_status":
        proof["contract"]["requirements_reviewed"] = True
    elif defect == "source_body_fact":
        next(iter(assurance["references"].values()))["source_body"] = "must never be exported"
    elif defect == "stale_claim":
        base["nodes"]["claim"][0]["claim_id"] = "claim::invented_component"
    elif defect == "base_body":
        base["nodes"]["source_file"][0]["source_body"] = "def leaked_body(): return True"
    elif defect == "unknown_edge_source":
        base["edges"][0]["from"] = "invented_component"
    elif defect == "dangling_edge_claim":
        next(edge for edge in base["edges"] if edge["to_type"] == "claim")["to"] = "claim::invented_component"
    elif defect == "duplicate_edge":
        base["edges"].append(copy.deepcopy(base["edges"][0]))
    elif defect == "escaping_receipt":
        assurance["replays"][0]["receipt_name"] = ".."
    elif defect == "base_graph_body":
        base["graph"]["content"] = "def leaked(): pass"
    elif defect == "base_metadata_body":
        base["generated_from"]["python_lens"] = {"content": "def leaked(): pass"}
    elif defect == "base_nested_lens_body":
        base["nodes"]["organ"][0]["runner_specificity"] = {"content": "def leaked(): pass"}
    with pytest.raises(ValueError):
        builder.extend_claim_index(base, registry, atlas, assurance)


def test_cached_evidence_is_reconstructed_from_canonical_registry(owners):
    base, registry, atlas, assurance = copy.deepcopy(owners)
    selected = base["nodes"]["organ"][0]["organ_id"]
    base["nodes"]["organ"][0].update(evidence_strength_rank=999, evidence_class="invented", authority_receipt="old/missing.json")
    next(row for row in base["nodes"]["claim"] if row["organ_id"] == selected)["claim_ceiling_restated"] = "obsolete prose"
    result = builder.extend_claim_index(base, registry, atlas, assurance)
    canonical = next(row for row in registry["implemented_organs"] if row["organ_id"] == selected)
    organ = next(row for row in result["nodes"]["organ"] if row["organ_id"] == selected)
    assert organ["evidence_strength_rank"] == canonical["evidence_strength_rank"]
    assert organ["evidence_class"] == canonical["evidence_class"]
    assert organ["authority_receipt"] == canonical["current_authority_receipt"]


def test_optional_private_history_is_unavailable_not_a_link_or_pass(owners):
    index = _index(owners)
    missing = index["assurance"]["optional_unavailable_assets"]
    assert any(row["original_ref"].endswith("macro_pattern_autonomy_process_runs_v1.jsonl") for row in missing)
    assert all("href" not in row and row["availability"] == "unavailable" for row in missing)
    assert all("state/microcosm_portfolio" in row["original_ref"] for row in missing)
    claim = next(row for row in index["nodes"]["claim"] if row["organ_id"] == "pattern_assimilation_step")
    assert claim["card"]["evidence"]["fresh_run_status"] == "not_run_by_index"
    replay = next(row for row in index["nodes"]["replay"] if row["organ_id"] == claim["organ_id"])
    assert replay["runner_ref"].startswith("src/microcosm_core/validators/acceptance.py#")


def test_native_lean_route_is_distinct_from_declared_exported_bundle(owners):
    index = _index(owners)
    replay = next(row for row in index["nodes"]["replay"] if row["organ_id"] == "formal_math_lean_proof_witness")
    assert replay["native_witness_requested"] is True
    assert replay["input_ref"] == "fixtures/first_wave/formal_math_lean_proof_witness/input"
    assert replay["declared_route"]["example_rel"].startswith("examples/")
    assert replay["runner_ref"].endswith("#run")
    assert replay["execution_status"] == "not_run_by_index"
    assert replay["fresh_receipt_template"].endswith("/formal_math_lean_proof_witness/formal_math_lean_proof_witness_result.json")
    assert replay["primary_execution"]["argv"] == ["plectis", "component-replay", "formal_math_lean_proof_witness"]
    assert replay["guide_example"]["writes_retained_receipts"] is True
    assert replay["guide_example"]["usage"] == "verbatim_source_example_only"


@pytest.mark.parametrize("reference", ["../outside.json", "/tmp/outside.json", "a/../../escape.py", "https://example.com/a", "a\\b.py", "a\nb.py"])
def test_references_cannot_escape(reference):
    with pytest.raises(ValueError):
        builder._ref_parts(reference)


def test_missing_named_symbol_and_linked_file_rejected(tmp_path):
    source = tmp_path / "unit.py"
    source.write_text("def real_symbol():\n    return True\n")
    with pytest.raises(ValueError, match="dangling named"):
        builder._reference_fact(tmp_path, "unit.py#invented_symbol")
    (tmp_path / "linked.py").symlink_to(source)
    with pytest.raises(ValueError, match="linked"):
        builder._reference_fact(tmp_path, "linked.py")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_unit.py").write_text("test_fake = True\n\ndef test_actual():\n    assert True\n")
    with pytest.raises(ValueError, match="collectable pytest"):
        builder._reference_fact(tmp_path, "tests/test_unit.py::test_fake")
    assert builder._reference_fact(tmp_path, "tests/test_unit.py::test_actual")["symbol_kind"] == "test_function"


def test_claim_and_contract_edits_change_identity_without_review_pass(owners):
    first = _index(owners)
    base, registry, atlas, assurance = copy.deepcopy(owners)
    capsule = builder._primary_guides(builder._unique(atlas["organs"], "organ_id", "atlas"), assurance["capsules"])["mcp_tool_authority_replay"]
    capsule["compression"]["one_line"] += " A changed claim."
    proof = next(row for row in assurance["proofs"] if row["slug"] == "mcp_authority")
    proof["contract"]["limits"] += " A changed model limit."
    second = builder.extend_claim_index(base, registry, atlas, assurance)
    def card(index):
        return next(row["card"] for row in index["nodes"]["claim"] if row["organ_id"] == "mcp_tool_authority_replay")
    assert card(first)["claim_text_sha256"] != card(second)["claim_text_sha256"]
    before = next(row for row in first["nodes"]["subclaim"] if row["subclaim_id"] == "subclaim::mcp_authority")
    after = next(row for row in second["nodes"]["subclaim"] if row["subclaim_id"] == before["subclaim_id"])
    assert before["contract_sha256"] != after["contract_sha256"]
    assert after["requirements_review"] == {"status": "unrecorded"}


@pytest.mark.parametrize("text", ["/Users/private-person/secret", "/Volumes/private-backend/session/secret.json",
                                  "C:\\private-backend\\secret.json", "file:///private/cache/secret.json",
                                  "sk-abcdefghijklmnopqrstuvwxyz"])
def test_private_paths_and_secret_shapes_cannot_be_exported(owners, text):
    base, registry, atlas, assurance = copy.deepcopy(owners)
    assurance["proofs"][0]["contract"]["limits"] = text
    with pytest.raises(ValueError, match="unsafe public"):
        builder.extend_claim_index(base, registry, atlas, assurance)
