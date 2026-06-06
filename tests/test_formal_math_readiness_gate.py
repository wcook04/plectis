from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from microcosm_core.organs.formal_math_readiness_gate import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    SELECTED_PATTERN_IDS,
    _line_count,
    _sha256,
    main,
    plan_readiness_extensions,
    run,
    run_readiness_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/formal_math_readiness_gate/input"
EXPORTED_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/formal_math_readiness_gate/exported_formal_math_readiness_bundle"
)
PROVER_SMOKE_RUN_REF = "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke"
SOURCE_ARTIFACT_REFS = [
    f"{PROVER_SMOKE_RUN_REF}/corpus_readiness.json",
    f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe.json",
    f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe/mathlib_probe.lean",
    f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe/trace_state_probe.lean",
    f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe/portfolio_core_v0/aesop.lean",
    f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe/portfolio_core_v0/decide.lean",
    f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe/portfolio_core_v0/grind.lean",
    f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe/portfolio_core_v0/native_decide.lean",
    f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe/portfolio_core_v0/omega.lean",
    f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe/portfolio_core_v0/rfl.lean",
    f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe/portfolio_core_v0/simp.lean",
    f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe/portfolio_core_v0/simp_all.lean",
    (
        f"{PROVER_SMOKE_RUN_REF}/tactic_affordance_probe/portfolio_core_v0/"
        "tactic_portfolio_availability.json"
    ),
]
PRIVATE_HOME_PREFIX = "/" + "Users" + "/"
PUBLIC_EXAMPLE_HOME = PRIVATE_HOME_PREFIX + "example"
NON_EXAMPLE_HOME_RE = re.compile("/Users/(?!example(?:/|$))[^/\\s\\\"']+")


def _assert_no_private_home_path(text: str) -> None:
    assert NON_EXAMPLE_HOME_RE.search(text) is None


def _sha256_prefixed(value: str) -> str:
    return value if value.startswith("sha256:") else f"sha256:{value}"


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


def _copy_source_artifacts(root: Path) -> None:
    for source_ref in SOURCE_ARTIFACT_REFS:
        source = MICROCOSM_ROOT.parent / source_ref
        target = root / source_ref
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _copy_fixture_public_root(
    tmp_path: Path,
    *,
    include_realness_artifacts: bool = True,
) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/formal_math_readiness_gate",
        public_root / "fixtures/first_wave/formal_math_readiness_gate",
    )
    if include_realness_artifacts:
        shutil.copytree(
            MICROCOSM_ROOT / "examples/formal_math_readiness_gate",
            public_root / "examples/formal_math_readiness_gate",
        )
    return public_root


def _fixture_input(public_root: Path) -> Path:
    return public_root / "fixtures/first_wave/formal_math_readiness_gate/input"


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_formal_math_readiness_line_count_streams_without_full_text_read(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "readiness_source.py"
    empty_source = tmp_path / "empty_readiness_source.py"
    source.write_text("one\n\ntwo\n", encoding="utf-8")
    empty_source.write_text("", encoding="utf-8")
    guarded_paths = {source, empty_source}
    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self in guarded_paths:
            raise AssertionError("line count should stream source-module input")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    assert _line_count(source) == 3
    assert _line_count(empty_source) == 1


def test_formal_math_readiness_digest_streams_without_read_bytes(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "readiness_source.py"
    body = b"readiness macro body\n" * 1024
    source.write_bytes(body)
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(self: Path, *args: Any, **kwargs: Any) -> bytes:
        if self == source:
            raise AssertionError("digest should stream source-module input")
        return original_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    assert _sha256(source) == _sha256_prefixed(hashlib.sha256(body).hexdigest())


def test_formal_math_readiness_gate_covers_negative_cases(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts",
        command="pytest",
        acceptance_out=tmp_path / "acceptance.json",
    )

    assert result["status"] == "pass"
    assert result["realness_evidence"]["tactic_probe_evidence_bound"] is True
    local_evidence = result["realness_evidence"]["candidate_bindings"][1][
        "local_lean_lake_mathlib_evidence"
    ]
    assert local_evidence["local_evidence_bound"] is True
    assert local_evidence["manifest_refs_exist"] is True
    assert local_evidence["lean_available"] is True
    assert local_evidence["lake_available"] is True
    assert local_evidence["mathlib_available"] is False
    assert local_evidence["mathlib_probe_import_seen"] is True
    assert local_evidence["lean_probe_file_count"] == 10
    assert local_evidence["std_probe_file_count"] == 9
    assert local_evidence["missing_target_refs"] == []
    assert (
        result["realness_evidence"]["candidate_bindings"][1]["source"]
        == "fixture_manifest_source_open_body_imports"
    )
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["blocked_capabilities"] == ["lean_std_synthetic_core:mathlib"]
    assert "aesop" in result["unavailable_tactic_ids"]
    assert result["premise_count"] == 11
    assert result["route_case_count"] == 5
    assert result["recipe_count"] == 3
    assert result["projection_cell_id"] == "formal_math_readiness_extensions"
    assert result["selected_pattern_ids"] == SELECTED_PATTERN_IDS
    extension = result["readiness_extension_board"]
    assert extension["source_intake_ref"].endswith("#formal_math_readiness_extensions")
    assert extension["projection_status"] == "public_runtime_import_landed"
    assert extension["projection_contract"]["real_substrate_receipt"] is True
    assert extension["projection_contract"]["synthetic_receipt_standin_allowed"] is False
    assert extension["premise_index_projection"]["namespace_counts"] == {
        "Bool": 2,
        "Iff": 3,
        "List": 3,
        "Nat": 3,
    }
    assert extension["premise_index_projection"]["split_eligibility_counts"] == {
        "dev": 11,
        "test": 11,
        "train": 11,
    }
    assert extension["tactic_portfolio_projection"]["available_tactic_count"] == 6
    assert extension["tactic_portfolio_projection"][
        "mathlib_dependent_unavailable_tactic_ids"
    ] == ["aesop"]
    assert extension["target_shape_routing_projection"]["blocked_route_case_ids"] == [
        "mathlib_search_uses_aesop_without_probe"
    ]
    assert result["authority_ceiling"]["lean_lake_execution_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_formal_math_readiness_rejects_unbound_synthetic_probe_fixture(
    tmp_path: Path,
) -> None:
    public_root = _copy_fixture_public_root(tmp_path)
    fixture_input = _fixture_input(public_root)
    good = run(
        fixture_input,
        public_root / "receipts/first_wave/formal_math_readiness_gate",
        command="pytest",
    )
    assert good["status"] == "pass"
    assert good["realness_evidence"]["tactic_probe_evidence_bound"] is True

    manifest_path = (
        public_root
        / "core/fixture_manifests/formal_math_readiness_gate.fixture_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_open = manifest["source_open_body_imports"]
    source_open["status"] = "blocked"
    source_open["source_refs"] = []
    source_open["target_refs"] = []
    source_open["body_material_count"] = 0
    manifest["body_copied_material_count"] = 0
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    bad = run(
        fixture_input,
        public_root / "receipts/first_wave/formal_math_readiness_gate_bad",
        command="pytest",
    )

    assert bad["status"] == "blocked"
    assert bad["realness_evidence"]["tactic_probe_evidence_bound"] is False
    assert "TACTIC_PROBE_SYNTHETIC_UNBOUND" in bad["error_codes"]


def test_formal_math_readiness_rejects_label_only_fixture_without_local_evidence(
    tmp_path: Path,
) -> None:
    public_root = _copy_fixture_public_root(tmp_path, include_realness_artifacts=False)
    result = run(
        _fixture_input(public_root),
        public_root / "receipts/first_wave/formal_math_readiness_gate",
        command="pytest",
    )

    local_evidence = result["realness_evidence"]["candidate_bindings"][1][
        "local_lean_lake_mathlib_evidence"
    ]
    assert result["status"] == "blocked"
    assert result["realness_evidence"]["tactic_probe_evidence_bound"] is False
    assert local_evidence["local_evidence_bound"] is False
    assert local_evidence["manifest_refs_exist"] is False
    assert local_evidence["existing_target_ref_count"] == 0
    assert local_evidence["missing_target_refs"]
    assert "TACTIC_PROBE_SYNTHETIC_UNBOUND" in result["error_codes"]


def test_formal_math_readiness_rejects_positive_unavailable_tactic_route(
    tmp_path: Path,
) -> None:
    public_root = _copy_fixture_public_root(tmp_path)
    fixture_input = _fixture_input(public_root)
    routing_path = fixture_input / "target_shape_tactic_routing.json"
    payload = json.loads(routing_path.read_text(encoding="utf-8"))
    payload["route_cases"][0]["allowed_tactic_ids"].append("aesop")
    routing_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture_input,
        public_root / "receipts/first_wave/formal_math_readiness_gate",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "ROUTING_ALLOWS_UNAVAILABLE_TACTIC" in result["error_codes"]
    route = next(
        row
        for row in result["readiness_extension_board"][
            "target_shape_routing_projection"
        ]["routes"]
        if row["route_case_id"] == "closed_nat_mod_decision"
    )
    assert route["blocked_unavailable_tactic_ids"] == ["aesop"]


def test_formal_math_readiness_namespace_projection_recomputes_after_namespace_move(
    tmp_path: Path,
) -> None:
    public_root = _copy_fixture_public_root(tmp_path)
    fixture_input = _fixture_input(public_root)
    premise_path = fixture_input / "premise_index.json"
    premise_payload = json.loads(premise_path.read_text(encoding="utf-8"))
    premises = premise_payload["premises"]
    moved = next(row for row in premises if row["namespace"] == "Nat")
    old_namespace = moved["namespace"]
    moved["namespace"] = "Algebra"
    expected_counts = Counter(row["namespace"] for row in premises)
    _write_json(premise_path, premise_payload)

    result = run(
        fixture_input,
        public_root / "receipts/first_wave/formal_math_readiness_gate",
        command="pytest",
    )

    projection = result["readiness_extension_board"]["premise_index_projection"]
    assert result["status"] == "pass"
    assert projection["premise_count"] == len(premises)
    assert projection["namespace_counts"] == dict(sorted(expected_counts.items()))
    assert projection["namespace_counts"][old_namespace] == expected_counts[
        old_namespace
    ]
    assert projection["namespace_counts"]["Algebra"] == 1


def test_formal_math_readiness_tactic_availability_flip_moves_count_and_verdict(
    tmp_path: Path,
) -> None:
    public_root = _copy_fixture_public_root(tmp_path)
    fixture_input = _fixture_input(public_root)
    baseline = run(
        fixture_input,
        public_root / "receipts/first_wave/formal_math_readiness_gate_baseline",
        command="pytest",
    )
    tactic_path = fixture_input / "tactic_portfolio_availability.json"
    tactic_payload = json.loads(tactic_path.read_text(encoding="utf-8"))
    routing_payload = json.loads(
        (fixture_input / "target_shape_tactic_routing.json").read_text(encoding="utf-8")
    )
    route_case = next(
        row
        for row in routing_payload["route_cases"]
        if row["allowed_tactic_ids"]
        and row["allowed_tactic_ids"][0]
        in baseline["readiness_extension_board"]["tactic_portfolio_projection"][
            "available_tactic_ids"
        ]
    )
    tactic_id = route_case["allowed_tactic_ids"][0]
    tactic_row = next(
        row for row in tactic_payload["tactics"] if row["tactic_id"] == tactic_id
    )
    tactic_row["availability_status"] = "environment_fail"
    tactic_row["failure_class"] = "availability_flip_test"
    _write_json(tactic_path, tactic_payload)

    result = run(
        fixture_input,
        public_root / "receipts/first_wave/formal_math_readiness_gate",
        command="pytest",
    )

    baseline_projection = baseline["readiness_extension_board"][
        "tactic_portfolio_projection"
    ]
    projection = result["readiness_extension_board"]["tactic_portfolio_projection"]
    routing = result["readiness_extension_board"]["target_shape_routing_projection"]
    blocked_route = next(
        row
        for row in routing["routes"]
        if row["route_case_id"] == route_case["route_case_id"]
    )
    assert result["status"] == "blocked"
    assert projection["available_tactic_count"] == (
        baseline_projection["available_tactic_count"] - 1
    )
    assert projection["unavailable_tactic_count"] == (
        baseline_projection["unavailable_tactic_count"] + 1
    )
    assert tactic_id not in projection["available_tactic_ids"]
    assert tactic_id in projection["unavailable_tactic_ids"]
    assert route_case["route_case_id"] in routing["blocked_route_case_ids"]
    assert blocked_route["blocked_unavailable_tactic_ids"] == [tactic_id]
    assert "ROUTING_ALLOWS_UNAVAILABLE_TACTIC" in result["error_codes"]


def test_formal_math_readiness_rejects_pass_tactic_without_probe_receipt(
    tmp_path: Path,
) -> None:
    public_root = _copy_fixture_public_root(tmp_path)
    fixture_input = _fixture_input(public_root)
    baseline = run(
        fixture_input,
        public_root / "receipts/first_wave/formal_math_readiness_gate_baseline",
        command="pytest",
    )
    tactic_path = fixture_input / "tactic_portfolio_availability.json"
    tactic_payload = json.loads(tactic_path.read_text(encoding="utf-8"))
    tactic_row = next(
        row
        for row in tactic_payload["tactics"]
        if row["availability_status"] == "pass" and row.get("probe_receipt_ref")
    )
    tactic_id = tactic_row["tactic_id"]
    tactic_row.pop("probe_receipt_ref")
    _write_json(tactic_path, tactic_payload)

    result = run(
        fixture_input,
        public_root / "receipts/first_wave/formal_math_readiness_gate",
        command="pytest",
    )

    baseline_projection = baseline["readiness_extension_board"][
        "tactic_portfolio_projection"
    ]
    projection = result["readiness_extension_board"]["tactic_portfolio_projection"]
    assert result["status"] == "blocked"
    assert projection["available_tactic_count"] == baseline_projection[
        "available_tactic_count"
    ]
    assert tactic_id in projection["available_tactic_ids"]
    assert "TACTIC_AVAILABILITY_UNPROBED" in result["error_codes"]
    assert result["observed_negative_cases"][
        f"{tactic_id}:positive_tactic_availability"
    ] == ["TACTIC_AVAILABILITY_UNPROBED"]


def test_formal_math_readiness_premise_and_tactic_mutation_moves_projection(
    tmp_path: Path,
) -> None:
    public_root = _copy_fixture_public_root(tmp_path)
    fixture_input = _fixture_input(public_root)
    premise_path = fixture_input / "premise_index.json"
    premise_payload = json.loads(premise_path.read_text(encoding="utf-8"))
    premise_payload["premises"].append(
        {
            "premise_id": "Algebra.fake_unit",
            "namespace": "Algebra",
            "retrieval_terms": ["algebra", "unit"],
            "allowed_for_split": ["train"],
            "source_ref": "Init/Algebra",
        }
    )
    _write_json(premise_path, premise_payload)

    tactic_path = fixture_input / "tactic_portfolio_availability.json"
    payload = json.loads(tactic_path.read_text(encoding="utf-8"))
    for row in payload["tactics"]:
        if row["tactic_id"] == "rfl":
            row["availability_status"] = "environment_fail"
            row["failure_class"] = "synthetic_probe_mutated_unavailable"
            break
    _write_json(tactic_path, payload)

    result = run(
        fixture_input,
        public_root / "receipts/first_wave/formal_math_readiness_gate",
        command="pytest",
    )

    premise_projection = result["readiness_extension_board"]["premise_index_projection"]
    projection = result["readiness_extension_board"]["tactic_portfolio_projection"]
    routing = result["readiness_extension_board"]["target_shape_routing_projection"]
    assert result["status"] == "blocked"
    assert premise_projection["premise_count"] == 12
    assert premise_projection["namespace_counts"] == {
        "Algebra": 1,
        "Bool": 2,
        "Iff": 3,
        "List": 3,
        "Nat": 3,
    }
    assert premise_projection["split_eligibility_counts"] == {
        "dev": 11,
        "test": 11,
        "train": 12,
    }
    assert premise_projection["retrieval_term_total"] == 35
    assert projection["available_tactic_count"] == 5
    assert projection["available_tactic_ids"] == [
        "decide",
        "grind",
        "omega",
        "simp",
        "simp_all",
    ]
    assert projection["unavailable_tactic_count"] == 2
    assert projection["unavailable_tactic_ids"] == ["aesop", "rfl"]
    assert projection["availability_status_counts"] == {
        "environment_fail": 2,
        "pass": 5,
    }
    assert routing["blocked_route_case_ids"] == [
        "mathlib_search_uses_aesop_without_probe",
        "true_intro",
    ]


def test_formal_math_readiness_local_probe_perturbation_moves_verdict(
    tmp_path: Path,
) -> None:
    public_root = _copy_fixture_public_root(tmp_path)
    fixture_input = _fixture_input(public_root)
    mathlib_probe = (
        public_root
        / "examples/formal_math_readiness_gate/exported_formal_math_readiness_bundle/source_artifacts/state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe/mathlib_probe.lean"
    )
    mathlib_probe.unlink()

    result = run(
        fixture_input,
        public_root / "receipts/first_wave/formal_math_readiness_gate",
        command="pytest",
    )

    local_evidence = result["realness_evidence"]["candidate_bindings"][1][
        "local_lean_lake_mathlib_evidence"
    ]
    assert result["status"] == "blocked"
    assert result["realness_evidence"]["tactic_probe_evidence_bound"] is False
    assert local_evidence["local_evidence_bound"] is False
    assert local_evidence["mathlib_probe_import_seen"] is False
    assert any(ref.endswith("/mathlib_probe.lean") for ref in local_evidence["missing_target_refs"])
    assert "TACTIC_PROBE_SYNTHETIC_UNBOUND" in result["error_codes"]


def test_formal_math_readiness_gate_accepts_exported_bundle(tmp_path: Path) -> None:
    result = run_readiness_bundle(
        EXPORTED_BUNDLE_INPUT,
        tmp_path / "receipts",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["realness_evidence"]["tactic_probe_evidence_bound"] is True
    local_evidence = result["realness_evidence"]["candidate_bindings"][0][
        "local_lean_lake_mathlib_evidence"
    ]
    assert local_evidence["local_evidence_bound"] is True
    assert local_evidence["lean_available"] is True
    assert local_evidence["lake_available"] is True
    assert local_evidence["mathlib_available"] is False
    assert local_evidence["mathlib_probe_import_seen"] is True
    assert (
        result["realness_evidence"]["candidate_bindings"][0]["source"]
        == "source_module_imports"
    )
    assert result["input_mode"] == "exported_formal_math_readiness_bundle"
    assert result["bundle_id"] == "public_formal_math_readiness_runtime_example"
    assert result["observed_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["blocked_capabilities"] == ["lean_std_synthetic_core:mathlib"]
    assert result["readiness_board"]["lean_lake_execution_authorized"] is False
    assert result["readiness_board"]["formal_proof_authority"] is False
    assert result["readiness_extension_board"]["cell_id"] == "formal_math_readiness_extensions"
    assert result["readiness_extension_board"]["target_shape_routing_projection"][
        "blocked_route_case_count"
    ] == 0
    assert result["body_material_status"] == (
        "copied_non_secret_macro_readiness_probe_body_with_provenance"
    )
    assert (
        result["source_module_import_status"]
        == "copied_formal_readiness_source_modules_verified"
    )
    assert result["source_module_import_count"] == len(SOURCE_ARTIFACT_REFS)
    assert result["copied_source_artifact_count"] == len(SOURCE_ARTIFACT_REFS)
    assert result["source_modules_pass"] is True
    assert all(row["exists"] is True for row in result["source_module_imports"])
    assert all(row["digest_match"] is True for row in result["source_module_imports"])
    assert result["readiness_extension_board"]["projection_contract"][
        "body_copied"
    ] is True
    assert result["readiness_extension_board"]["source_body_import_projection"][
        "copied_source_artifact_count"
    ] == len(SOURCE_ARTIFACT_REFS)
    assert result["receipt_paths"] == [
        "receipts/exported_formal_math_readiness_bundle_validation_result.json"
    ]


def test_formal_math_readiness_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/formal_math_readiness_gate",
        public_root / "examples/formal_math_readiness_gate",
    )
    bundle = (
        public_root
        / "examples/formal_math_readiness_gate/exported_formal_math_readiness_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["target_sha256"] = "sha256:" + ("0" * 64)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_readiness_bundle(
        bundle,
        public_root / "receipts/formal_math_readiness_gate",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_modules_pass"] is False
    assert "FORMAL_READINESS_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_formal_math_readiness_rejects_source_module_target_ref_path_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/formal_math_readiness_gate",
        public_root / "examples/formal_math_readiness_gate",
    )
    bundle = (
        public_root
        / "examples/formal_math_readiness_gate/exported_formal_math_readiness_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["target_ref"] = manifest["modules"][1]["target_ref"]
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_readiness_bundle(
        bundle,
        public_root / "receipts/formal_math_readiness_gate",
        command="pytest",
    )

    first_import = result["source_module_imports"][0]
    assert result["status"] == "blocked"
    assert result["source_modules_pass"] is False
    assert first_import["digest_match"] is True
    assert first_import["target_ref_matches_path"] is False
    assert (
        "FORMAL_READINESS_SOURCE_MODULE_TARGET_REF_PATH_MISMATCH"
        in result["error_codes"]
    )
    assert (
        "FORMAL_READINESS_SOURCE_MODULE_DIGEST_MISMATCH"
        not in result["error_codes"]
    )


def test_formal_math_readiness_rejects_source_module_source_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/formal_math_readiness_gate",
        public_root / "examples/formal_math_readiness_gate",
    )
    _copy_source_artifacts(public_root.parent)
    bundle = (
        public_root
        / "examples/formal_math_readiness_gate/exported_formal_math_readiness_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["source_sha256"] = "sha256:" + ("0" * 64)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_readiness_bundle(
        bundle,
        public_root / "receipts/formal_math_readiness_gate",
        command="pytest",
    )

    first_import = result["source_module_imports"][0]
    assert result["status"] == "blocked"
    assert result["source_modules_pass"] is False
    assert "FORMAL_READINESS_SOURCE_MODULE_SOURCE_DIGEST_MISMATCH" in result[
        "error_codes"
    ]
    assert first_import["source_exists"] is True
    assert first_import["source_digest_match"] is False
    assert first_import["actual_source_sha256"] != first_import["source_sha256"]


def test_formal_math_readiness_exported_bundle_card_bounds_stdout(
    tmp_path: Path,
    capsys,
) -> None:
    exit_code = main(
        [
            "run-readiness-bundle",
            "--input",
            str(EXPORTED_BUNDLE_INPUT),
            "--out",
            str(tmp_path / "receipts"),
            "--card",
        ]
    )
    stdout = capsys.readouterr().out
    card = json.loads(stdout)

    assert exit_code == 0
    assert len(stdout.encode("utf-8")) < 6000
    assert card["schema_version"] == CARD_SCHEMA_VERSION
    assert card["status"] == "pass"
    assert card["input_mode"] == "exported_formal_math_readiness_bundle"
    assert card["counts"]["premise_count"] == 11
    assert card["counts"]["route_case_count"] == 4
    assert card["source_module_import"]["source_modules_pass"] is True
    assert card["source_module_import"]["source_module_import_count"] == len(
        SOURCE_ARTIFACT_REFS
    )
    assert card["source_module_import"]["digest_match_count"] == len(
        SOURCE_ARTIFACT_REFS
    )
    assert card["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert card["authority_ceiling"]["lean_lake_execution_authorized"] is False
    assert card["body_in_receipt"] is False
    assert "readiness_board" not in card
    assert "readiness_extension_board" not in card
    assert "source_module_imports" not in card
    receipt = tmp_path / card["receipt_paths"][0]
    assert receipt.is_file()


def test_formal_math_readiness_exported_source_modules_are_digest_verified() -> None:
    manifest = json.loads(
        (EXPORTED_BUNDLE_INPUT / "source_module_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    modules = {row["source_ref"]: row for row in manifest["modules"]}
    assert sorted(modules) == sorted(SOURCE_ARTIFACT_REFS)
    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False

    bundle_manifest = json.loads(
        (EXPORTED_BUNDLE_INPUT / "bundle_manifest.json").read_text(encoding="utf-8")
    )
    assert bundle_manifest["source_module_manifest_ref"] == "source_module_manifest.json"
    assert len(bundle_manifest["copied_macro_body_artifacts"]) == len(
        SOURCE_ARTIFACT_REFS
    )

    for source_ref in SOURCE_ARTIFACT_REFS:
        source = MICROCOSM_ROOT.parent / source_ref
        target = EXPORTED_BUNDLE_INPUT / "source_artifacts" / source_ref
        assert target.is_file()
        source_bytes = source.read_bytes()
        target_bytes = target.read_bytes()
        source_digest = "sha256:" + hashlib.sha256(source_bytes).hexdigest()
        target_digest = "sha256:" + hashlib.sha256(target_bytes).hexdigest()
        row = modules[source_ref]
        row_source_digest = _sha256_prefixed(row.get("source_sha256", row["sha256"]))
        row_target_digest = _sha256_prefixed(row.get("target_sha256", row["sha256"]))
        assert row_source_digest == source_digest
        assert row_target_digest == target_digest
        assert _sha256_prefixed(row["sha256"]) == target_digest
        if row.get("source_to_target_relation") == "verified_public_safe_private_path_rewrite":
            assert source_digest != target_digest
            assert row["verification_mode"] == "verified_light_edit_recipe"
            assert row["public_safe_transform"] == "private_absolute_path_rewrite_only"
            target_text = target.read_text(encoding="utf-8")
            assert PUBLIC_EXAMPLE_HOME in target_text
            _assert_no_private_home_path(target_text)
        else:
            assert source_bytes == target_bytes
            assert row.get("source_to_target_relation", "exact_copy") == "exact_copy"
        assert modules[source_ref]["body_in_receipt"] is False


def test_formal_math_readiness_exported_bundle_receipt_omits_source_bodies(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/formal_math_readiness_gate",
        public_root / "examples/formal_math_readiness_gate",
    )

    result = run_readiness_bundle(
        public_root / "examples/formal_math_readiness_gate/exported_formal_math_readiness_bundle",
        public_root / "receipts/formal_math_readiness_gate",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert PRIVATE_HOME_PREFIX not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert "import Mathlib" not in text
        assert "\n  trace_state" not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["source_module_import_count"] == len(SOURCE_ARTIFACT_REFS)
        assert payload["copied_source_artifact_count"] == len(SOURCE_ARTIFACT_REFS)
        assert payload["source_modules_pass"] is True
        assert "body_redacted" not in _walk_keys(payload)
        assert "private_state_scan" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_formal_math_readiness_receipts_use_secret_exclusion_and_public_relative(
    tmp_path: Path,
) -> None:
    public_root = _copy_fixture_public_root(tmp_path)

    result = run(
        public_root / "fixtures/first_wave/formal_math_readiness_gate/input",
        public_root / "receipts/first_wave/formal_math_readiness_gate",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert PRIVATE_HOME_PREFIX not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert "synthetic redacted proof payload" not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert "body_redacted" not in _walk_keys(payload)
        assert "private_state_scan" not in _walk_keys(payload)
        assert payload["authority_ceiling"]["lean_lake_execution_authorized"] is False
        if payload["schema_version"] == "formal_math_readiness_extension_board_receipt_v1":
            assert payload["cell_id"] == "formal_math_readiness_extensions"
            assert payload["projection_contract"]["body_copied"] is False
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_formal_math_readiness_plan_is_non_writing_extension_preview(
    tmp_path: Path,
) -> None:
    result = plan_readiness_extensions(FIXTURE_INPUT, command="pytest")

    assert result["status"] == "pass"
    assert result["schema_version"] == "formal_math_readiness_extension_preview_v1"
    assert result["projection_cell_id"] == "formal_math_readiness_extensions"
    assert result["selected_pattern_ids"] == SELECTED_PATTERN_IDS
    assert result["readiness_extension_board"]["projection_status"] == "public_runtime_import_landed"
    assert result["readiness_extension_board"]["provider_context_projection"][
        "provider_calls_authorized"
    ] is False
    assert not any(tmp_path.iterdir())
