from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.formal_evidence_cell_anchor_resolver import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    SOURCE_REFS,
    _line_count,
    _sha256_file,
    main,
    run,
    run_anchor_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT / "fixtures/first_wave/formal_evidence_cell_anchor_resolver/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/formal_evidence_cell_anchor_resolver/exported_evidence_cell_anchor_bundle"
)


def _ref_path(ref: str) -> str:
    return ref.split("::", 1)[0]


def _copy_public_ref(public_root: Path, ref: str) -> None:
    repo_root = MICROCOSM_ROOT.parent
    path_ref = _ref_path(ref)
    if path_ref.startswith("microcosm-substrate/"):
        source = repo_root / path_ref
        target = public_root / path_ref.removeprefix("microcosm-substrate/")
    elif (MICROCOSM_ROOT / path_ref).is_file():
        source = MICROCOSM_ROOT / path_ref
        target = public_root / path_ref
    else:
        source = repo_root / path_ref
        target = public_root.parent / path_ref
    if not source.is_file():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _materialize_public_anchor_refs(public_root: Path, input_dir: Path) -> None:
    projection = json.loads((input_dir / "projection_protocol.json").read_text())
    registry = json.loads((input_dir / "evidence_cell_registry.json").read_text())
    refs = [
        *projection.get("real_ring2_anchor_refs", []),
        *projection.get("projection_receipt_refs", []),
        *projection.get("public_runtime_refs", []),
    ]
    for cell in registry.get("evidence_cells", []):
        refs.extend(cell.get("source_anchor_refs", []))
    for ref in refs:
        _copy_public_ref(public_root, ref)


def _copy_exported_bundle(public_root: Path) -> Path:
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/formal_evidence_cell_anchor_resolver/"
        "exported_evidence_cell_anchor_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    _materialize_public_anchor_refs(public_root, bundle)
    for ref in SOURCE_REFS:
        _copy_public_ref(public_root, ref)
    return bundle


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


def test_formal_evidence_cell_anchor_line_count_streams_source_modules(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "source_module.py"
    empty_source = tmp_path / "empty_source_module.py"
    source.write_text("one\n\ntwo", encoding="utf-8")
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


def test_formal_evidence_cell_anchor_digest_streams_source_modules(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "source_module.py"
    body = b"macro body\n" * 1024
    source.write_bytes(body)
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(self: Path, *args: Any, **kwargs: Any) -> bytes:
        if self == source:
            raise AssertionError("digest should stream source-module input")
        return original_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    assert _sha256_file(source) == hashlib.sha256(body).hexdigest()


def test_formal_evidence_cell_anchor_resolver_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/formal_evidence_cell_anchor_resolver",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/formal_evidence_cell_anchor_resolver_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["claim_count"] == 3
    assert result["resolved_cell_count"] == 3
    assert result["unresolved_cell_count"] == 0
    assert result["evidence_cell_count"] == 3
    assert result["source_anchor_count"] == 8
    assert result["machine_anchor_count"] == 3
    assert result["source_modules_pass"] is True
    assert result["source_module_count"] == 0
    assert result["source_open_body_imports"] == {}
    assert result["evidence_anchor_status"] == (
        "real_ring2_verifier_trace_repair_receipt_refs"
    )
    assert (
        result["source_digests"][
            "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
            "premise_retrieval_graph_v0/failure_taxonomy_report.json"
        ]
        == "sha256:8b054c57001c432942a7ed97cbd4dca2a2e2b174d9cd31d9121c38c5ecc933af"
    )
    assert any(
        "formal_math_verifier_trace_repair_loop_result.json" in ref
        for ref in result["projection_receipt_refs"]
    )
    verifier_row = next(
        row
        for row in result["claim_resolution_rows"]
        if row["claim_id"] == "claim.verifier_trace_has_runtime_receipt_anchor"
    )
    assert verifier_row["claim_strength"] == "ring2_failure_taxonomy_anchor_present"
    assert verifier_row["machine_anchor_class"] == (
        "real_ring2_verifier_trace_repair_receipt"
    )
    assert any(
        "formal_math_verifier_trace_repair_loop/verifier_trace_repair_board.json"
        in ref
        for ref in verifier_row["source_anchor_refs"]
    )
    assert result["authority_ceiling"]["theorem_correctness_authority"] is False
    assert result["authority_ceiling"]["formal_proof_authority"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_formal_evidence_cell_anchor_receipts_are_public_relative_with_secret_exclusion(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/formal_evidence_cell_anchor_resolver",
        public_root / "fixtures/first_wave/formal_evidence_cell_anchor_resolver",
    )
    _materialize_public_anchor_refs(
        public_root,
        public_root / "fixtures/first_wave/formal_evidence_cell_anchor_resolver/input",
    )

    result = run(
        public_root / "fixtures/first_wave/formal_evidence_cell_anchor_resolver/input",
        public_root / "receipts/first_wave/formal_evidence_cell_anchor_resolver",
        command="pytest",
        acceptance_out=(
            public_root
            / "receipts/acceptance/first_wave/formal_evidence_cell_anchor_resolver_fixture_acceptance.json"
        ),
    )

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "private://macro-formal-lab" not in text
        assert "synthetic forbidden proof body" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["body_in_receipt"] is False
        assert payload["real_runtime_receipt"] is True
        assert payload["synthetic_receipt_standin_allowed"] is False
        assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert "private_state_scan" not in payload
        assert "body_redacted" not in _walk_keys(payload)
        assert "proof_body" not in _walk_keys(payload)
        assert "private_source_ref" not in _walk_keys(payload)
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_formal_evidence_cell_anchor_resolver_recomputes_public_anchor_refs(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/formal_evidence_cell_anchor_resolver",
        public_root / "fixtures/first_wave/formal_evidence_cell_anchor_resolver",
    )
    input_dir = (
        public_root / "fixtures/first_wave/formal_evidence_cell_anchor_resolver/input"
    )
    _materialize_public_anchor_refs(public_root, input_dir)

    good = run(
        input_dir,
        public_root / "receipts/good/formal_evidence_cell_anchor_resolver",
        command="pytest",
    )

    assert good["status"] == "pass"
    assert good["anchor_resolution_status"] == "pass"
    assert good["resolved_anchor_ref_count"] >= 10
    assert all(row["body_in_receipt"] is False for row in good["anchor_resolution_rows"])
    assert all(
        cell["anchor_resolution_status"] == "pass" for cell in good["evidence_cells"]
    )

    board = (
        public_root
        / "receipts/first_wave/formal_math_verifier_trace_repair_loop/"
        "verifier_trace_repair_board.json"
    )
    board.write_text(
        board.read_text(encoding="utf-8").replace(
            "failure_mode_ledger",
            "removed_marker_for_test",
        ),
        encoding="utf-8",
    )
    mutated = run(
        input_dir,
        public_root / "receipts/mutated/formal_evidence_cell_anchor_resolver",
        command="pytest",
    )

    assert mutated["status"] == "blocked"
    assert "EVIDENCE_CELL_SOURCE_ANCHOR_MARKER_MISSING" in mutated["error_codes"]
    assert any(
        row["ref"].endswith("verifier_trace_repair_board.json::failure_mode_ledger")
        and row["status"] == "blocked"
        for row in mutated["anchor_resolution_rows"]
    )
    for receipt_ref in mutated["receipt_paths"]:
        text = (public_root / receipt_ref).read_text(encoding="utf-8")
        assert "removed_marker_for_test" not in text
        assert '"body":' not in text
        assert "matched_excerpt" not in text


def test_formal_evidence_cell_anchor_resolver_rejects_missing_public_anchor_ref(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/formal_evidence_cell_anchor_resolver",
        public_root / "fixtures/first_wave/formal_evidence_cell_anchor_resolver",
    )
    input_dir = (
        public_root / "fixtures/first_wave/formal_evidence_cell_anchor_resolver/input"
    )
    _materialize_public_anchor_refs(public_root, input_dir)
    (
        public_root / "receipts/runtime_shell/public_formal_evidence_cell_lens.json"
    ).unlink()

    result = run(
        input_dir,
        public_root / "receipts/missing/formal_evidence_cell_anchor_resolver",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "EVIDENCE_CELL_SOURCE_ANCHOR_REF_MISSING" in result["error_codes"]
    assert any(
        row["ref"] == "receipts/runtime_shell/public_formal_evidence_cell_lens.json"
        and row["status"] == "blocked"
        for row in result["anchor_resolution_rows"]
    )
    assert result["body_in_receipt"] is False


def test_formal_evidence_cell_anchor_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_anchor_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/formal_evidence_cell_anchor_resolver",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_evidence_cell_anchor_bundle"
    assert result["bundle_id"] == "formal_evidence_cell_anchor_resolver_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["claim_count"] == 3
    assert result["resolved_cell_count"] == 3
    assert result["evidence_cell_count"] == 3
    assert result["source_anchor_count"] == 5
    assert result["source_modules_pass"] is True
    assert result["source_module_count"] == 6
    assert result["verified_source_module_count"] == 6
    assert result["source_open_body_imports"]["body_material_count"] == 6
    assert result["source_open_body_imports"]["body_in_receipt"] is False
    assert result["source_module_secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["source_module_secret_exclusion_scan"]["scanned_path_count"] == 6
    imported_ids = set(result["source_open_body_imports"]["body_material_ids"])
    assert "paper_module_formal_evidence_auditor_source_body_import" in imported_ids
    assert "formal_evidence_cell_registry_builder_source_body_import" in imported_ids
    assert "formal_evidence_cell_registry_state_body_import" in imported_ids
    assert all(row["body_in_receipt"] is False for row in result["source_modules"])
    assert all(row["digest_matches"] is True for row in result["source_modules"])
    assert result["evidence_anchor_status"] == (
        "real_ring2_verifier_trace_repair_receipt_refs"
    )
    assert any(
        "formal_math_verifier_trace_repair_loop/verifier_trace_repair_board.json"
        in ref
        for ref in result["projection_receipt_refs"]
    )
    assert result["authority_ceiling"]["theorem_correctness_authority"] is False


def test_formal_evidence_cell_anchor_bundle_rejects_theorem_correctness_overclaim(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle = _copy_exported_bundle(public_root)
    claims_path = bundle / "paper_claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][0]["claims_theorem_correctness"] = True
    claims_path.write_text(
        json.dumps(claims, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_anchor_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "formal_evidence_cell_anchor_resolver",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "EVIDENCE_CELL_THEOREM_CORRECTNESS_OVERCLAIM" in result["error_codes"]
    assert result["source_modules_pass"] is True
    assert result["body_in_receipt"] is False


def test_formal_evidence_cell_anchor_bundle_rejects_textual_theorem_correctness_overclaim(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle = _copy_exported_bundle(public_root)
    claims_path = bundle / "paper_claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["claims"][0]["claim_text"] = (
        "This evidence cell proves theorem correctness for the declaration."
    )
    claims_path.write_text(
        json.dumps(claims, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_anchor_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "formal_evidence_cell_anchor_resolver",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "EVIDENCE_CELL_THEOREM_CORRECTNESS_OVERCLAIM" in result["error_codes"]
    assert result["source_modules_pass"] is True
    assert result["body_in_receipt"] is False


def test_formal_evidence_cell_anchor_bundle_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle = _copy_exported_bundle(public_root)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    corrupted_module = manifest["modules"][0]
    corrupted_module_id = corrupted_module["module_id"]
    corrupted_module["sha256"] = "0" * 64
    corrupted_module["target_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_anchor_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "formal_evidence_cell_anchor_resolver",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "EVIDENCE_CELL_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_modules_pass"] is False
    assert result["source_module_count"] == 6
    assert result["verified_source_module_count"] == 5
    assert result["source_open_body_imports"]["body_material_count"] == 5
    source_module = next(
        row for row in result["source_modules"] if row["module_id"] == corrupted_module_id
    )
    assert source_module["digest_matches"] is False
    assert source_module["body_in_receipt"] is False
    assert result["source_module_secret_exclusion_scan"]["blocking_hit_count"] == 0


def test_formal_evidence_cell_anchor_bundle_rejects_rehashed_source_body_swap(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle = _copy_exported_bundle(public_root)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    swapped_module = manifest["modules"][0]
    swapped_module_id = swapped_module["module_id"]
    target = bundle / swapped_module["path"]
    target.write_text(
        target.read_text(encoding="utf-8")
        + "\n# rehashed copied body swap must not become source authority\n",
        encoding="utf-8",
    )
    swapped_digest = _sha256_file(target)
    swapped_module["sha256"] = swapped_digest
    swapped_module["target_sha256"] = swapped_digest
    swapped_module["source_sha256"] = swapped_digest
    swapped_module["line_count"] = _line_count(target)
    swapped_module["byte_count"] = target.stat().st_size
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_anchor_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "formal_evidence_cell_anchor_resolver",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert (
        "EVIDENCE_CELL_SOURCE_MODULE_SOURCE_AUTHORITY_DIGEST_MISMATCH"
        in result["error_codes"]
    )
    assert result["source_modules_pass"] is False
    assert result["source_module_count"] == 6
    assert result["verified_source_module_count"] == 5
    source_module = next(
        row for row in result["source_modules"] if row["module_id"] == swapped_module_id
    )
    assert source_module["digest_matches"] is True
    assert source_module["source_authority_digest_matches"] is False
    assert source_module["body_in_receipt"] is False
    assert result["source_module_secret_exclusion_scan"]["blocking_hit_count"] == 0


def test_formal_evidence_cell_anchor_bundle_card_is_compact(
    tmp_path: Path,
    capsys: Any,
) -> None:
    out_dir = tmp_path / "bundle-card"

    rc = main(
        [
            "run-anchor-bundle",
            "--input",
            str(BUNDLE_INPUT),
            "--out",
            str(out_dir),
            "--card",
        ]
    )

    captured = capsys.readouterr().out
    card = json.loads(captured)
    full_receipt = out_dir / "exported_evidence_cell_anchor_bundle_validation_result.json"

    assert rc == 0
    assert len(captured.encode("utf-8")) < 6000
    assert full_receipt.is_file()
    assert card["schema_version"] == CARD_SCHEMA_VERSION
    assert card["status"] == "pass"
    assert card["organ_id"] == "formal_evidence_cell_anchor_resolver"
    assert card["input_mode"] == "exported_evidence_cell_anchor_bundle"
    assert card["bundle_id"] == "formal_evidence_cell_anchor_resolver_runtime_example"
    assert card["counts"]["claim_count"] == 3
    assert card["counts"]["resolved_cell_count"] == 3
    assert card["counts"]["source_anchor_count"] == 5
    assert card["source_summary"]["source_ref_count"] == 14
    assert card["source_summary"]["source_refs_exported"] is False
    assert card["source_module_summary"]["source_modules_pass"] is True
    assert card["source_module_summary"]["source_module_count"] == 6
    assert card["source_module_summary"]["verified_source_module_count"] == 6
    assert card["source_module_summary"]["source_module_rows_exported"] is False
    assert (
        card["source_module_summary"]["source_open_body_imports"][
            "body_material_ids_exported"
        ]
        is False
    )
    assert (
        card["source_module_summary"][
            "source_module_secret_exclusion_scan_summary"
        ]["blocking_hit_count"]
        == 0
    )
    assert card["secret_exclusion_scan_summary"]["blocking_hit_count"] == 0
    assert card["secret_exclusion_scan_summary"]["scan_scope_exported"] is False
    assert card["authority_ceiling"]["theorem_correctness_authority"] is False
    assert card["authority_ceiling"]["formal_proof_authority"] is False
    assert card["no_export_guards"]["proof_bodies_exported"] is False
    assert "source_modules" not in card
    assert "source_refs" not in card
    assert "claim_resolution_rows" not in card
