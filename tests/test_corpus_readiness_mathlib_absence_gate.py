from __future__ import annotations

import json
import hashlib
import re
import shutil
from pathlib import Path
from typing import Any

import pytest
import microcosm_core.organs.corpus_readiness_mathlib_absence_gate as corpus_gate
from microcosm_core.organs.corpus_readiness_mathlib_absence_gate import (
    CARD_SCHEMA_VERSION,
    DEFAULT_MATHLIB_ABSENCE_PROBE_BODY,
    DEFAULT_STD_IMPORT_PROBE_BODY,
    EXPECTED_NEGATIVE_CASES,
    MATHLIB_ABSENCE_PROBE_INPUT_NAME,
    PASS,
    RUNTIME_PROBE_INPUT_DIR_NAME,
    SOURCE_PATTERN_IDS,
    STD_IMPORT_PROBE_INPUT_NAME,
    _line_count,
    main,
    run,
    run_projection_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/corpus_readiness_mathlib_absence_gate/input"
EXPORTED_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle"
)
SOURCE_ARTIFACT_REFS = [
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/corpus_readiness.json",
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe.json",
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe/mathlib_probe.lean",
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe/portfolio_core_v0/tactic_portfolio_availability.json",
]
PRIVATE_HOME_PREFIX = "/" + "Users" + "/"
PUBLIC_EXAMPLE_HOME = PRIVATE_HOME_PREFIX + "example"
NON_EXAMPLE_HOME_RE = re.compile("/Users/(?!example(?:/|$))[^/\\s\\\"']+")


def _passing_runtime_probe() -> dict[str, Any]:
    return {
        "schema_version": "corpus_readiness_runtime_lean_import_probe_v1",
        "status": PASS,
        "proof_class": "test_recorded_runtime_probe",
        "execution_mode": "lean_cli_import_probe_with_lake_availability_check",
        "lean_available": True,
        "lake_available": True,
        "std_import_passed": True,
        "mathlib_import_rejected": True,
        "mathlib_lake_project_import_available": False,
        "std_probe": {
            "argv": ["lean", "StdGood.lean"],
            "return_code": 0,
            "body_redacted": True,
        },
        "mathlib_probe": {
            "argv": ["lean", "MathlibAbsent.lean"],
            "return_code": 1,
            "stdout_has_unknown_mathlib": True,
            "body_redacted": True,
        },
        "body_in_receipt": False,
        "body_redacted": True,
        "lake_build_ran": False,
    }


@pytest.fixture(autouse=True)
def _recorded_runtime_probe(monkeypatch: Any) -> None:
    monkeypatch.setattr(corpus_gate, "runtime_lean_import_probe", _passing_runtime_probe)


def _assert_no_private_home_path(text: str) -> None:
    assert NON_EXAMPLE_HOME_RE.search(text) is None


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


def _copy_exported_bundle(public_root: Path) -> Path:
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/corpus_readiness_mathlib_absence_gate",
        public_root / "examples/corpus_readiness_mathlib_absence_gate",
    )
    _copy_source_artifacts(public_root.parent)
    return (
        public_root
        / "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle"
    )


def _copy_fixture_input_with_source_artifacts(public_root: Path) -> Path:
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/corpus_readiness_mathlib_absence_gate",
        public_root / "fixtures/first_wave/corpus_readiness_mathlib_absence_gate",
    )
    _copy_source_artifacts(public_root.parent)
    return public_root / "fixtures/first_wave/corpus_readiness_mathlib_absence_gate/input"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_runtime_probe_inputs(
    input_dir: Path,
    *,
    std_body: str = DEFAULT_STD_IMPORT_PROBE_BODY,
    mathlib_body: str = DEFAULT_MATHLIB_ABSENCE_PROBE_BODY,
) -> Path:
    probe_dir = input_dir / RUNTIME_PROBE_INPUT_DIR_NAME
    probe_dir.mkdir(parents=True, exist_ok=True)
    (probe_dir / STD_IMPORT_PROBE_INPUT_NAME).write_text(std_body, encoding="utf-8")
    (probe_dir / MATHLIB_ABSENCE_PROBE_INPUT_NAME).write_text(
        mathlib_body,
        encoding="utf-8",
    )
    return probe_dir


def _case_by_id(result: dict[str, Any], case_id: str) -> dict[str, Any]:
    for row in result["consumer_gate_cases"]:
        if row["case_id"] == case_id:
            return row
    raise AssertionError(f"missing consumer case {case_id}")


def _invert_expected_decision_labels(cases_path: Path) -> None:
    payload = _read_json(cases_path)
    for row in payload["cases"]:
        row["expected_decision"] = (
            "allowed" if row.get("expected_decision") == "blocked" else "blocked"
        )
    _write_json(cases_path, payload)


def _hex_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prefixed_sha256(path: Path) -> str:
    return "sha256:" + _hex_sha256(path)


def test_corpus_readiness_line_count_streams_without_full_text_read(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "source.py"
    empty_source = tmp_path / "empty.py"
    source.write_text("one\n\ntwo\n", encoding="utf-8")
    empty_source.write_text("", encoding="utf-8")
    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self in {source, empty_source}:
            raise AssertionError("line count should stream source-module input")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    assert _line_count(source) == 3
    assert _line_count(empty_source) == 1


def test_corpus_readiness_mathlib_absence_gate_covers_negative_cases(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts",
        command="pytest",
        acceptance_out=tmp_path / "acceptance.json",
    )

    assert result["status"] == "pass"
    assert result["source_pattern_ids"] == SOURCE_PATTERN_IDS
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["mathlib_lake_project_import_available"] is False
    assert result["runtime_mathlib_probe_status"] == "ENVIRONMENT_FAIL"
    assert result["runtime_source_artifact_status"] == "pass"
    assert result["runtime_lean_import_probe"]["status"] == "pass"
    assert result["runtime_lean_import_probe"]["std_import_passed"] is True
    assert result["runtime_lean_import_probe"]["mathlib_import_rejected"] is True
    assert result["runtime_source_artifact_count"] == 4
    assert result["translation_smoke_only_ids"] == ["miniF2F_lean3_annex"]
    assert result["absent_corpus_ids"] == [
        "LeanDojo",
        "Pantograph",
        "ProofNet",
        "PutnamBench_lean4",
        "mathlib",
        "miniF2F_lean4_mathlib_package",
    ]
    assert result["corpus_count"] == 7
    assert result["consumer_case_count"] == 7
    assert result["allowed_case_ids"] == ["miniF2F_lean3_translation_smoke_allowed"]
    assert result["blocked_case_ids"] == [
        "leandojo_training_blocked_absent",
        "mathlib_import_blocked_until_probe",
        "miniF2F_lean4_mathlib_search_blocked_absent",
        "pantograph_state_search_blocked_absent",
        "proofnet_blocked_absent",
        "putnambench_lean4_blocked_absent",
    ]
    assert result["body_material_status"] == "copied_non_secret_macro_body_with_provenance"
    assert result["corpus_readiness_status"] == (
        "real_lean_std_corpus_readiness_and_mathlib_absence_boundary"
    )
    assert result["toolchain_boundary_status"] == (
        "real_lean_cli_std_mathlib_absence_probe_with_lake_available"
    )
    assert result["body_in_receipt"] is False
    assert result["source_digests"][
        "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/corpus_readiness.json"
    ] == "sha256:c413608118229bea32062ce9b8b5af393bcd5f63bbf1030983e98ffa6d07778d"
    assert result["readiness_board"]["public_contract"][
        "mathlib_probe_required_before_mathlib_proof_work"
    ] is True
    assert result["authority_ceiling"]["lean_lake_execution_authorized"] == (
        "bounded_runtime_import_probe_only"
    )
    assert result["authority_ceiling"]["mathlib_dependent_proof_authority"] is False
    assert result["authority_ceiling"]["formal_proof_authority"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_corpus_readiness_real_good_ignores_expected_decision_labels(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    fixture_input = _copy_fixture_input_with_source_artifacts(public_root)
    _invert_expected_decision_labels(fixture_input / "consumer_gate_cases.json")

    result = run(
        fixture_input,
        public_root / "receipts/first_wave/corpus_readiness_mathlib_absence_gate",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["allowed_case_ids"] == ["miniF2F_lean3_translation_smoke_allowed"]
    assert result["blocked_case_ids"] == [
        "leandojo_training_blocked_absent",
        "mathlib_import_blocked_until_probe",
        "miniF2F_lean4_mathlib_search_blocked_absent",
        "pantograph_state_search_blocked_absent",
        "proofnet_blocked_absent",
        "putnambench_lean4_blocked_absent",
    ]
    assert "expected_decision" not in _walk_keys(result)


def test_corpus_readiness_real_fixture_fields_move_consumer_verdict(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    fixture_input = _copy_fixture_input_with_source_artifacts(public_root)
    cases_path = fixture_input / "consumer_gate_cases.json"
    payload = _read_json(cases_path)
    for row in payload["cases"]:
        if row["case_id"] == "miniF2F_lean4_mathlib_search_blocked_absent":
            row["target_corpus_id"] = "miniF2F_lean3_annex"
            row["requires_mathlib_lake_project_import"] = False
            row["expected_decision"] = "blocked"
    _write_json(cases_path, payload)

    result = run(
        fixture_input,
        public_root / "receipts/first_wave/corpus_readiness_mathlib_absence_gate",
        command="pytest",
    )

    moved = _case_by_id(result, "miniF2F_lean4_mathlib_search_blocked_absent")
    assert result["status"] == "pass"
    assert moved["target_corpus_id"] == "miniF2F_lean3_annex"
    assert moved["requires_mathlib_lake_project_import"] is False
    assert moved["decision"] == "allowed"
    assert moved["blocked_reasons"] == []
    assert "miniF2F_lean4_mathlib_search_blocked_absent" in result["allowed_case_ids"]
    assert "expected_decision" not in _walk_keys(result)


def test_corpus_readiness_real_consumer_readiness_gate_field_blocks_verdict(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    fixture_input = _copy_fixture_input_with_source_artifacts(public_root)
    cases_path = fixture_input / "consumer_gate_cases.json"
    payload = _read_json(cases_path)
    for row in payload["cases"]:
        if row["case_id"] == "miniF2F_lean3_translation_smoke_allowed":
            row["readiness_gate_checked"] = False
    _write_json(cases_path, payload)

    result = run(
        fixture_input,
        public_root / "receipts/first_wave/corpus_readiness_mathlib_absence_gate",
        command="pytest",
    )

    moved = _case_by_id(result, "miniF2F_lean3_translation_smoke_allowed")
    assert result["status"] == "blocked"
    assert moved["decision"] == "allowed"
    assert moved["readiness_gate_checked"] is False
    assert "CONSUMER_READINESS_GATE_UNCHECKED" in result["error_codes"]
    assert any(
        finding["error_code"] == "CONSUMER_READINESS_GATE_UNCHECKED"
        and finding["subject_id"] == "miniF2F_lean3_translation_smoke_allowed"
        for finding in result["findings"]
    )


def test_corpus_readiness_source_row_perturbation_moves_absence_verdict(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    fixture_input = _copy_fixture_input_with_source_artifacts(public_root)
    cases_path = fixture_input / "consumer_gate_cases.json"
    cases = _read_json(cases_path)
    for row in cases["cases"]:
        if row["case_id"] == "leandojo_training_blocked_absent":
            row["requires_mathlib_lake_project_import"] = False
            row["expected_decision"] = "blocked"
    _write_json(cases_path, cases)

    baseline = run(
        fixture_input,
        public_root / "receipts/baseline/corpus_readiness_mathlib_absence_gate",
        command="pytest",
    )

    source_path = public_root.parent / SOURCE_ARTIFACT_REFS[0]
    source_payload = _read_json(source_path)
    for row in source_payload["rows"]:
        if row["corpus_id"] == "LeanDojo":
            row["exists"] = True
            row["readiness_status"] = "available"
            row["selected_for_this_run"] = True
    _write_json(source_path, source_payload)

    mutated = run(
        fixture_input,
        public_root / "receipts/mutated/corpus_readiness_mathlib_absence_gate",
        command="pytest",
    )

    baseline_case = _case_by_id(baseline, "leandojo_training_blocked_absent")
    mutated_case = _case_by_id(mutated, "leandojo_training_blocked_absent")
    mutated_corpus_row = next(
        row for row in mutated["corpora"] if row["corpus_id"] == "LeanDojo"
    )
    assert baseline["status"] == "pass"
    assert baseline_case["decision"] == "blocked"
    assert baseline_case["blocked_reasons"] == ["corpus_absent"]
    assert "LeanDojo" in baseline["absent_corpus_ids"]
    assert mutated["status"] == "blocked"
    assert "CORPUS_READINESS_SOURCE_ARTIFACT_DIGEST_MISMATCH" in mutated["error_codes"]
    assert mutated_case["decision"] == "allowed"
    assert mutated_case["blocked_reasons"] == []
    assert "LeanDojo" not in mutated["absent_corpus_ids"]
    assert mutated_corpus_row["selected_for_this_run"] is True
    assert "expected_decision" not in _walk_keys(mutated)


def test_corpus_readiness_top_level_mathlib_alias_labels_do_not_bake_pass(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    fixture_input = _copy_fixture_input_with_source_artifacts(public_root)
    readiness_path = fixture_input / "corpus_readiness.json"
    payload = _read_json(readiness_path)
    payload["mathlib_available"] = True
    payload["mathlib_direct_import_available"] = True
    _write_json(readiness_path, payload)

    result = run(
        fixture_input,
        public_root / "receipts/first_wave/corpus_readiness_mathlib_absence_gate",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["mathlib_lake_project_import_available"] is False
    assert result["runtime_mathlib_probe_status"] == "ENVIRONMENT_FAIL"
    assert "CORPUS_READINESS_RUNTIME_PROBE_CONTRADICTION" in result["error_codes"]
    assert any(
        finding["error_code"] == "CORPUS_READINESS_RUNTIME_PROBE_CONTRADICTION"
        and finding["subject_id"] == "mathlib_available,mathlib_direct_import_available"
        for finding in result["findings"]
    )


def test_corpus_readiness_mathlib_absence_gate_accepts_exported_bundle(
    tmp_path: Path,
) -> None:
    result = run_projection_bundle(
        EXPORTED_BUNDLE_INPUT,
        tmp_path / "receipts",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_corpus_readiness_bundle"
    assert result["bundle_id"] == "public_corpus_readiness_mathlib_absence_runtime_example"
    assert result["observed_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["mathlib_lake_project_import_available"] is False
    assert result["runtime_mathlib_probe_status"] == "ENVIRONMENT_FAIL"
    assert result["runtime_source_artifact_status"] == "pass"
    assert result["runtime_lean_import_probe"]["status"] == "pass"
    assert result["blocked_case_ids"] == [
        "leandojo_training_blocked_absent",
        "mathlib_import_blocked_until_probe",
        "miniF2F_lean4_mathlib_search_blocked_absent",
    ]
    assert result["body_material_status"] == "copied_non_secret_macro_body_with_provenance"
    assert result["corpus_readiness_status"] == (
        "real_lean_std_corpus_readiness_and_mathlib_absence_boundary"
    )
    assert result["source_module_import_count"] == 4
    assert result["copied_source_artifact_count"] == 4
    assert result["source_modules_pass"] is True
    assert result["receipt_paths"] == [
        "receipts/exported_corpus_readiness_bundle_validation_result.json"
    ]


def test_corpus_readiness_exported_bundle_card_bounds_stdout(
    tmp_path: Path,
    capsys,
) -> None:
    exit_code = main(
        [
            "run-projection-bundle",
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
    assert card["input_mode"] == "exported_corpus_readiness_bundle"
    assert card["counts"]["corpus_count"] == 7
    assert card["counts"]["consumer_case_count"] == 4
    assert card["source_module_import"]["source_modules_pass"] is True
    assert card["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert card["authority_ceiling"]["lean_lake_execution_authorized"] is False
    assert card["runtime_lean_import_probe"]["status"] == "pass"
    assert card["runtime_lean_import_probe"]["std_import_passed"] is True
    assert card["runtime_lean_import_probe"]["mathlib_import_rejected"] is True
    assert card["body_in_receipt"] is False
    assert "readiness_board" not in card
    assert "source_module_imports" not in card
    receipt = tmp_path / card["receipt_paths"][0]
    assert receipt.is_file()


def test_corpus_readiness_exported_source_modules_are_digest_verified() -> None:
    manifest = json.loads(
        (EXPORTED_BUNDLE_INPUT / "source_module_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    rows = {row["source_ref"]: row for row in manifest["modules"]}
    assert sorted(rows) == SOURCE_ARTIFACT_REFS
    for source_ref in SOURCE_ARTIFACT_REFS:
        source = MICROCOSM_ROOT.parent / source_ref
        target = EXPORTED_BUNDLE_INPUT / rows[source_ref]["path"]
        source_digest = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
        target_text = target.read_text(encoding="utf-8")
        target_digest = "sha256:" + hashlib.sha256(target_text.encode("utf-8")).hexdigest()
        row = rows[source_ref]
        row_source_digest = str(row.get("source_sha256", row["sha256"]))
        row_target_digest = str(row.get("target_sha256", row["sha256"]))
        row_digest = str(row["sha256"])
        if not row_source_digest.startswith("sha256:"):
            row_source_digest = f"sha256:{row_source_digest}"
        if not row_target_digest.startswith("sha256:"):
            row_target_digest = f"sha256:{row_target_digest}"
        if not row_digest.startswith("sha256:"):
            row_digest = f"sha256:{row_digest}"
        assert row_source_digest == source_digest
        assert row_target_digest == target_digest
        assert row_digest == target_digest
        if row.get("source_to_target_relation") == "verified_public_safe_private_path_rewrite":
            assert source_digest != target_digest
            assert row["verification_mode"] == "verified_light_edit_recipe"
            assert row["public_safe_transform"] == "private_absolute_path_rewrite_only"
            assert PUBLIC_EXAMPLE_HOME in target_text
            _assert_no_private_home_path(target_text)
        else:
            assert target.read_bytes() == source.read_bytes()
            assert row.get("source_to_target_relation", "exact_copy") == "exact_copy"
        assert rows[source_ref]["body_copied"] is True
        assert rows[source_ref]["body_in_receipt"] is False


def test_corpus_readiness_blocks_contradictory_fixture_runtime_claim(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/corpus_readiness_mathlib_absence_gate",
        public_root / "fixtures/first_wave/corpus_readiness_mathlib_absence_gate",
    )
    fixture_input = (
        public_root / "fixtures/first_wave/corpus_readiness_mathlib_absence_gate/input"
    )
    readiness_path = fixture_input / "corpus_readiness.json"
    payload = json.loads(readiness_path.read_text(encoding="utf-8"))
    payload["mathlib_lake_project_import_available"] = True
    for row in payload["corpora"]:
        if row["corpus_id"] == "mathlib":
            row["mathlib_lake_project_import_available"] = True
            row["mathlib_probe_status"] = "PASS"
    readiness_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture_input,
        public_root / "receipts/first_wave/corpus_readiness_mathlib_absence_gate",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["mathlib_lake_project_import_available"] is False
    assert result["runtime_mathlib_probe_status"] == "ENVIRONMENT_FAIL"
    assert "CORPUS_READINESS_RUNTIME_PROBE_CONTRADICTION" in result["error_codes"]
    assert any(
        finding["error_code"] == "CORPUS_READINESS_RUNTIME_PROBE_CONTRADICTION"
        and finding["negative_case_id"] == "positive_runtime_probe"
        for finding in result["findings"]
    )


def test_corpus_readiness_bundle_blocks_contradictory_runtime_claim(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle_input = _copy_exported_bundle(public_root)
    readiness_path = bundle_input / "corpus_readiness.json"
    payload = json.loads(readiness_path.read_text(encoding="utf-8"))
    payload["mathlib_lake_project_import_available"] = True
    for row in payload["corpora"]:
        if row["corpus_id"] == "mathlib":
            row["mathlib_lake_project_import_available"] = True
            row["mathlib_probe_status"] = "PASS"
    readiness_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_projection_bundle(
        bundle_input,
        public_root / "receipts/runtime_shell/demo_project/organs/corpus_readiness_mathlib_absence_gate",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["mathlib_lake_project_import_available"] is False
    assert result["runtime_mathlib_probe_status"] == "ENVIRONMENT_FAIL"
    assert "CORPUS_READINESS_RUNTIME_PROBE_CONTRADICTION" in result["error_codes"]
    assert any(
        finding["error_code"] == "CORPUS_READINESS_RUNTIME_PROBE_CONTRADICTION"
        and finding["negative_case_id"] == "positive_runtime_probe"
        for finding in result["findings"]
    )


def test_corpus_readiness_bundle_embedded_runtime_artifact_moves_probe_verdict(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle_input = _copy_exported_bundle(public_root)
    bundle_probe_path = bundle_input / "source_artifacts" / SOURCE_ARTIFACT_REFS[1]
    probe_payload = _read_json(bundle_probe_path)
    probe_payload["mathlib"]["available"] = True
    probe_payload["mathlib"]["mathlib_available"] = True
    probe_payload["mathlib"]["direct_mathlib_lane_available"] = True
    probe_payload["mathlib"]["lake_project_mathlib_lane_available"] = True
    probe_payload["mathlib"]["error_class"] = "NONE"
    probe_payload["mathlib"]["lean_status"] = PASS
    _write_json(bundle_probe_path, probe_payload)

    result = run_projection_bundle(
        bundle_input,
        public_root / "receipts/runtime_shell/demo_project/organs/corpus_readiness_mathlib_absence_gate",
        command="pytest",
    )

    probe_row = next(
        row
        for row in result["runtime_source_artifacts"]
        if row["source_ref"] == SOURCE_ARTIFACT_REFS[1]
    )
    assert result["status"] == "blocked"
    assert result["runtime_mathlib_probe_status"] == PASS
    assert result["mathlib_lake_project_import_available"] is True
    assert (
        probe_row["target_ref"]
        == "examples/corpus_readiness_mathlib_absence_gate/"
        "exported_corpus_readiness_bundle/source_artifacts/"
        + SOURCE_ARTIFACT_REFS[1]
    )
    assert "CORPUS_READINESS_RUNTIME_PROBE_CONTRADICTION" in result["error_codes"]
    assert "CORPUS_READINESS_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_corpus_readiness_bundle_rejects_stale_mathlib_probe_status_label(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle_input = _copy_exported_bundle(public_root)
    bundle_probe_path = bundle_input / "source_artifacts" / SOURCE_ARTIFACT_REFS[1]
    probe_payload = _read_json(bundle_probe_path)
    probe_payload["mathlib"]["lean_status"] = PASS
    probe_payload["mathlib"]["error_class"] = ""
    _write_json(bundle_probe_path, probe_payload)

    result = run_projection_bundle(
        bundle_input,
        public_root / "receipts/runtime_shell/demo_project/organs/corpus_readiness_mathlib_absence_gate",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["runtime_mathlib_probe_status"] == PASS
    assert result["mathlib_lake_project_import_available"] is False
    assert "CORPUS_READINESS_MATHLIB_STATUS_ALIAS_UNSUPPORTED" in result["error_codes"]
    assert "CORPUS_READINESS_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_corpus_readiness_bundle_rejects_manifest_consistent_runtime_forgery(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle_input = _copy_exported_bundle(public_root)

    top_level_readiness = bundle_input / "corpus_readiness.json"
    readiness_payload = _read_json(top_level_readiness)
    readiness_payload["mathlib_lake_project_import_available"] = True
    readiness_payload["mathlib_available"] = True
    readiness_payload["mathlib_direct_import_available"] = True

    embedded_readiness = bundle_input / "source_artifacts" / SOURCE_ARTIFACT_REFS[0]
    embedded_readiness_payload = _read_json(embedded_readiness)
    embedded_readiness_payload["mathlib_lake_project_import_available"] = True
    for row in embedded_readiness_payload["rows"]:
        if row["corpus_id"] == "mathlib":
            row["exists"] = True
            row["has_lake_file"] = True
            row["readiness_status"] = "available"
            row["selected_for_this_run"] = True
    _write_json(embedded_readiness, embedded_readiness_payload)
    embedded_rows = {
        str(row["corpus_id"]): row for row in embedded_readiness_payload["rows"]
    }
    for row in readiness_payload["corpora"]:
        runtime_row = embedded_rows[str(row["corpus_id"])]
        row["exists"] = runtime_row["exists"]
        row["has_lake_file"] = runtime_row["has_lake_file"]
        row["readiness_status"] = runtime_row["readiness_status"]
        row["selected_for_this_run"] = runtime_row["selected_for_this_run"]
        is_absent_non_mathlib = (
            row["corpus_id"] != "mathlib"
            and (
                runtime_row["readiness_status"] == "absent"
                or runtime_row["exists"] is False
            )
        )
        row["mathlib_lake_project_import_available"] = (
            not is_absent_non_mathlib
            and bool(runtime_row["exists"])
            and bool(runtime_row["has_lake_file"])
        )
        row["mathlib_probe_status"] = (
            "NOT_PROBED_ABSENT_CORPUS" if is_absent_non_mathlib else PASS
        )
    _write_json(top_level_readiness, readiness_payload)

    bundle_probe_path = bundle_input / "source_artifacts" / SOURCE_ARTIFACT_REFS[1]
    probe_payload = _read_json(bundle_probe_path)
    probe_payload["mathlib"]["available"] = True
    probe_payload["mathlib"]["mathlib_available"] = True
    probe_payload["mathlib"]["direct_mathlib_lane_available"] = True
    probe_payload["mathlib"]["lake_project_mathlib_lane_available"] = True
    probe_payload["mathlib"]["error_class"] = "NONE"
    probe_payload["mathlib"]["lean_status"] = PASS
    _write_json(bundle_probe_path, probe_payload)

    manifest = _read_json(bundle_input / "source_module_manifest.json")
    for row in manifest["modules"]:
        if row["source_ref"] == SOURCE_ARTIFACT_REFS[0]:
            row["sha256"] = _hex_sha256(embedded_readiness)
            row["target_sha256"] = _hex_sha256(embedded_readiness)
        elif row["source_ref"] == SOURCE_ARTIFACT_REFS[1]:
            row["sha256"] = _prefixed_sha256(bundle_probe_path)
            row["target_sha256"] = _prefixed_sha256(bundle_probe_path)
            row["public_safe_sha256"] = _prefixed_sha256(bundle_probe_path)
    _write_json(bundle_input / "source_module_manifest.json", manifest)

    result = run_projection_bundle(
        bundle_input,
        public_root / "receipts/runtime_shell/demo_project/organs/corpus_readiness_mathlib_absence_gate",
        command="pytest",
    )

    mathlib_case = _case_by_id(result, "mathlib_import_blocked_until_probe")
    assert result["status"] == "blocked"
    assert result["runtime_mathlib_probe_status"] == PASS
    assert result["mathlib_lake_project_import_available"] is True
    assert mathlib_case["decision"] == "allowed"
    assert mathlib_case["blocked_reasons"] == []
    assert "CORPUS_READINESS_RUNTIME_PROBE_CONTRADICTION" not in result["error_codes"]
    assert "CORPUS_READINESS_SOURCE_MODULE_EXACT_COPY_MISMATCH" in result["error_codes"]
    assert (
        "CORPUS_READINESS_SOURCE_MODULE_PUBLIC_SAFE_REWRITE_MISMATCH"
        in result["error_codes"]
    )


def test_corpus_readiness_rejects_source_module_source_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/corpus_readiness_mathlib_absence_gate",
        public_root / "examples/corpus_readiness_mathlib_absence_gate",
    )
    _copy_source_artifacts(public_root.parent)
    bundle = (
        public_root
        / "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["source_sha256"] = "sha256:" + ("0" * 64)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_projection_bundle(
        bundle,
        public_root / "receipts/corpus_readiness_mathlib_absence_gate",
        command="pytest",
    )

    first_import = result["source_module_imports"][0]
    assert result["status"] == "blocked"
    assert result["source_modules_pass"] is False
    assert "CORPUS_READINESS_SOURCE_MODULE_SOURCE_DIGEST_MISMATCH" in result[
        "error_codes"
    ]
    assert first_import["source_exists"] is True
    assert first_import["source_digest_match"] is False
    assert first_import["actual_source_sha256"] != first_import["source_sha256"]


def test_corpus_readiness_rejects_source_module_target_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/corpus_readiness_mathlib_absence_gate",
        public_root / "examples/corpus_readiness_mathlib_absence_gate",
    )
    _copy_source_artifacts(public_root.parent)
    bundle = (
        public_root
        / "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["target_sha256"] = "sha256:" + ("0" * 64)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run_projection_bundle(
        bundle,
        public_root / "receipts/corpus_readiness_mathlib_absence_gate",
        command="pytest",
    )

    first_import = result["source_module_imports"][0]
    assert result["status"] == "blocked"
    assert result["source_modules_pass"] is False
    assert "CORPUS_READINESS_SOURCE_MODULE_DIGEST_MISMATCH" in result[
        "error_codes"
    ]
    assert "CORPUS_READINESS_SOURCE_MODULE_SOURCE_DIGEST_MISMATCH" not in result[
        "error_codes"
    ]
    assert first_import["source_exists"] is True
    assert first_import["source_digest_match"] is True
    assert first_import["digest_match"] is False
    assert first_import["target_sha256"] != first_import["expected_target_sha256"]


def test_corpus_readiness_exported_receipt_omits_source_bodies(tmp_path: Path) -> None:
    result = run_projection_bundle(
        EXPORTED_BUNDLE_INPUT,
        tmp_path / "receipts",
        command="pytest",
    )
    receipt_path = tmp_path / result["receipt_paths"][0]
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))

    assert payload["source_module_import_count"] == 4
    assert payload["copied_source_artifact_count"] == 4
    assert payload["source_modules_pass"] is True
    assert payload["body_in_receipt"] is False
    assert "import Mathlib" not in receipt_path.read_text(encoding="utf-8")
    for row in payload["source_module_imports"]:
        assert row["exists"] is True
        assert row["digest_match"] is True
        assert row["body_in_receipt"] is False
        assert row["source_ref"] in SOURCE_ARTIFACT_REFS


def test_corpus_readiness_receipts_are_real_substrate_and_public_relative(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/corpus_readiness_mathlib_absence_gate",
        public_root / "fixtures/first_wave/corpus_readiness_mathlib_absence_gate",
    )

    result = run(
        public_root / "fixtures/first_wave/corpus_readiness_mathlib_absence_gate/input",
        public_root / "receipts/first_wave/corpus_readiness_mathlib_absence_gate",
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
        assert "NEGATIVE_FIXTURE_FORBIDDEN_PROOF_BODY_DO_NOT_ECHO" not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["body_material_status"] == (
            "copied_non_secret_macro_body_with_provenance"
        )
        assert payload["body_in_receipt"] is False
        assert "private_state_scan" not in payload
        assert "body_redacted" not in payload
        assert payload["secret_exclusion_scan"]["real_substrate_default"] is True
        assert payload["authority_ceiling"]["lean_lake_execution_authorized"] == (
            "bounded_runtime_import_probe_only"
        )
        assert payload["runtime_lean_import_probe"]["status"] == "pass"
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_corpus_readiness_runtime_probe_failure_blocks_projection(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    def blocked_probe() -> dict[str, Any]:
        return {
            "schema_version": "corpus_readiness_runtime_lean_import_probe_v1",
            "status": "blocked",
            "proof_class": "mutated_runtime_probe",
            "lean_available": True,
            "lake_available": True,
            "std_import_passed": True,
            "mathlib_import_rejected": False,
            "mathlib_lake_project_import_available": False,
            "body_in_receipt": False,
            "body_redacted": True,
        }

    monkeypatch.setattr(corpus_gate, "runtime_lean_import_probe", blocked_probe)

    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts",
        command="pytest",
        acceptance_out=tmp_path / "acceptance.json",
    )

    assert result["status"] == "blocked"
    assert result["runtime_lean_import_probe"]["status"] == "blocked"
    assert result["runtime_lean_import_probe"]["mathlib_import_rejected"] is False
    assert "CORPUS_READINESS_RUNTIME_LEAN_IMPORT_PROBE_BLOCKED" in result["error_codes"]
    assert result["authority_ceiling"]["mathlib_dependent_proof_authority"] is False
    assert result["authority_ceiling"]["formal_proof_authority"] is False


def test_corpus_readiness_runtime_probe_blocks_when_lean_unavailable(
    monkeypatch: Any,
) -> None:
    monkeypatch.undo()
    monkeypatch.setattr(corpus_gate.shutil, "which", lambda name: None)

    probe = corpus_gate.runtime_lean_import_probe()

    assert probe["status"] == "blocked"
    assert probe["blocked_by"] == "lean_unavailable"
    assert probe["lean_available"] is False
    assert probe["lake_available"] is False
    assert probe["std_import_passed"] is False
    assert probe["mathlib_import_rejected"] is False
    assert probe["mathlib_lake_project_import_available"] is False
    assert probe["body_in_receipt"] is False


def test_corpus_readiness_runtime_probe_blocks_when_lake_unavailable(
    monkeypatch: Any,
) -> None:
    monkeypatch.undo()

    def fake_which(name: str) -> str | None:
        return "/tmp/fake-lean" if name == "lean" else None

    monkeypatch.setattr(corpus_gate.shutil, "which", fake_which)

    probe = corpus_gate.runtime_lean_import_probe()

    assert probe["status"] == "blocked"
    assert probe["blocked_by"] == "lake_unavailable"
    assert probe["execution_mode"] == "lake_env_lean_import_probe_with_lake_availability_check"
    assert probe["lean_available"] is True
    assert probe["lake_available"] is False
    assert probe["std_import_passed"] is False
    assert probe["mathlib_import_rejected"] is False
    assert probe["std_probe"]["argv"] == ["lake", "env", "lean", "StdGood.lean"]
    assert probe["std_probe"]["skipped"] is True
    assert probe["std_probe"]["skip_reason"] == "lake_unavailable"
    assert probe["mathlib_probe"]["argv"] == [
        "lake",
        "env",
        "lean",
        "MathlibAbsent.lean",
    ]
    assert probe["mathlib_probe"]["skipped"] is True
    assert probe["mathlib_probe"]["skip_reason"] == "lake_unavailable"
    assert probe["body_in_receipt"] is False


def test_corpus_readiness_runtime_lean_import_probe_is_live_when_available(
    monkeypatch: Any,
) -> None:
    monkeypatch.undo()
    if shutil.which("lean") is None:
        pytest.skip("lean executable unavailable on this host")
    if shutil.which("lake") is None:
        pytest.skip("lake executable unavailable on this host")

    probe = corpus_gate.runtime_lean_import_probe()

    assert probe["schema_version"] == "corpus_readiness_runtime_lean_import_probe_v1"
    assert probe["proof_class"] == "live_runtime_probe"
    assert probe["execution_mode"] == "lake_env_lean_import_probe_with_lake_availability_check"
    assert probe["lean_available"] is True
    assert probe["lake_available"] is True
    assert probe["std_import_passed"] is True
    assert probe["mathlib_import_rejected"] is True
    assert probe["mathlib_lake_project_import_available"] is False
    assert probe["body_in_receipt"] is False
    assert probe["std_probe"]["argv"] == ["lake", "env", "lean", "StdGood.lean"]
    assert probe["std_probe"]["return_code"] == 0
    assert probe["std_probe"]["body_redacted"] is True
    assert probe["mathlib_probe"]["argv"] == [
        "lake",
        "env",
        "lean",
        "MathlibAbsent.lean",
    ]
    assert probe["mathlib_probe"]["return_code"] != 0
    assert (
        probe["mathlib_probe"]["stdout_has_unknown_mathlib"] is True
        or probe["mathlib_probe"]["stderr_has_unknown_mathlib"] is True
    )
    assert probe["mathlib_probe"]["body_redacted"] is True
    assert probe["lake_version_probe"]["argv"] == ["lake", "--version"]
    assert probe["lake_version_probe"]["return_code"] == 0
    assert probe["lake_version_probe"]["body_redacted"] is True
    assert probe["lake_build_ran"] is False


def test_corpus_readiness_supplied_runtime_probe_inputs_pass_when_good(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    monkeypatch.undo()
    if shutil.which("lean") is None or shutil.which("lake") is None:
        pytest.skip("Lean/Lake unavailable on this host")
    if corpus_gate.runtime_lean_import_probe()["status"] != PASS:
        pytest.skip("host does not satisfy the Mathlib-absence runtime probe")

    public_root = tmp_path / "microcosm-substrate"
    fixture_input = _copy_fixture_input_with_source_artifacts(public_root)
    _write_runtime_probe_inputs(fixture_input)

    result = run(
        fixture_input,
        public_root / "receipts/first_wave/corpus_readiness_mathlib_absence_gate",
        command="pytest",
    )

    probe = result["runtime_lean_import_probe"]
    assert result["status"] == "pass"
    assert probe["status"] == "pass"
    assert probe["probe_input_mode"] == "supplied_probe_sources"
    assert probe["probe_input_status"] == "pass"
    assert probe["missing_probe_input_names"] == []
    assert probe["std_import_passed"] is True
    assert probe["mathlib_import_rejected"] is True
    assert probe["std_probe"]["argv"] == ["lake", "env", "lean", "StdGood.lean"]
    assert probe["mathlib_probe"]["argv"] == [
        "lake",
        "env",
        "lean",
        "MathlibAbsent.lean",
    ]
    assert probe["lake_build_ran"] is False
    assert probe["body_in_receipt"] is False
    assert [row["name"] for row in probe["probe_input_files"]] == [
        STD_IMPORT_PROBE_INPUT_NAME,
        MATHLIB_ABSENCE_PROBE_INPUT_NAME,
    ]
    assert all(row["body_redacted"] is True for row in probe["probe_input_files"])


def test_corpus_readiness_supplied_runtime_probe_input_perturbation_blocks(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    monkeypatch.undo()
    if shutil.which("lean") is None or shutil.which("lake") is None:
        pytest.skip("Lean/Lake unavailable on this host")
    if corpus_gate.runtime_lean_import_probe()["status"] != PASS:
        pytest.skip("host does not satisfy the Mathlib-absence runtime probe")

    public_root = tmp_path / "microcosm-substrate"
    fixture_input = _copy_fixture_input_with_source_artifacts(public_root)
    _write_runtime_probe_inputs(
        fixture_input,
        mathlib_body=DEFAULT_STD_IMPORT_PROBE_BODY,
    )

    result = run(
        fixture_input,
        public_root / "receipts/first_wave/corpus_readiness_mathlib_absence_gate",
        command="pytest",
    )

    probe = result["runtime_lean_import_probe"]
    assert result["status"] == "blocked"
    assert probe["status"] == "blocked"
    assert probe["probe_input_mode"] == "supplied_probe_sources"
    assert probe["probe_input_status"] == "pass"
    assert probe["std_import_passed"] is True
    assert probe["mathlib_probe"]["return_code"] == 0
    assert probe["mathlib_import_rejected"] is False
    assert "CORPUS_READINESS_RUNTIME_LEAN_IMPORT_PROBE_BLOCKED" in result["error_codes"]
    assert result["authority_ceiling"]["mathlib_dependent_proof_authority"] is False
    assert result["authority_ceiling"]["formal_proof_authority"] is False
