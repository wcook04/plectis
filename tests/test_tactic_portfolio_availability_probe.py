from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs import tactic_portfolio_availability_probe
from microcosm_core.organs.tactic_portfolio_availability_probe import (
    BUNDLE_RESULT_NAME,
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_availability_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT / "fixtures/first_wave/tactic_portfolio_availability_probe/input"
)
EXPORTED_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle"
)


def _sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


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


def _copy_exported_bundle(public_root: Path) -> Path:
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/tactic_portfolio_availability_probe",
        public_root / "examples/tactic_portfolio_availability_probe",
    )
    return (
        public_root
        / "examples/tactic_portfolio_availability_probe/"
        "exported_tactic_portfolio_availability_bundle"
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _patch_source_digests(
    monkeypatch: Any,
    *,
    input_dir: Path,
    source_refs: list[str],
) -> None:
    digests = dict(tactic_portfolio_availability_probe.SOURCE_DIGESTS)
    for source_ref in source_refs:
        rel = tactic_portfolio_availability_probe.SOURCE_BODY_REL_BY_SOURCE_REF[source_ref]
        digests[source_ref] = _sha256(input_dir / rel)
    monkeypatch.setattr(tactic_portfolio_availability_probe, "SOURCE_DIGESTS", digests)


def _mutate_rfl_authoritative_source(input_dir: Path, *, failure_code: str) -> None:
    portfolio_ref = tactic_portfolio_availability_probe.SOURCE_REFS[1]
    probe_ref = tactic_portfolio_availability_probe.SOURCE_REFS[0]
    portfolio_path = (
        input_dir
        / tactic_portfolio_availability_probe.SOURCE_BODY_REL_BY_SOURCE_REF[portfolio_ref]
    )
    probe_path = (
        input_dir
        / tactic_portfolio_availability_probe.SOURCE_BODY_REL_BY_SOURCE_REF[probe_ref]
    )
    portfolio = _read_json(portfolio_path)
    probe = _read_json(probe_path)

    for row in portfolio["rows"]:
        if row["tactic_id"] == "rfl":
            row["available"] = False
            row["compile_status"] = "FAIL"
            row["error_class"] = failure_code
            break
    else:  # pragma: no cover - fixture contract guard
        raise AssertionError("expected rfl row in source portfolio artifact")

    portfolio["available_tactic_ids"] = [
        tactic_id for tactic_id in portfolio["available_tactic_ids"] if tactic_id != "rfl"
    ]
    portfolio["unavailable_tactic_ids"] = sorted(
        [*portfolio["unavailable_tactic_ids"], "rfl"]
    )

    for row in probe["portfolio_core_v0"]["rows"]:
        if row["tactic_id"] == "rfl":
            row["available"] = False
            row["compile_status"] = "FAIL"
            row["error_class"] = failure_code
            break
    else:  # pragma: no cover - fixture contract guard
        raise AssertionError("expected rfl row in source probe artifact")

    probe["portfolio_core_v0"]["available_tactic_ids"] = [
        tactic_id
        for tactic_id in probe["portfolio_core_v0"]["available_tactic_ids"]
        if tactic_id != "rfl"
    ]
    probe["portfolio_core_v0"]["unavailable_tactic_ids"] = sorted(
        [*probe["portfolio_core_v0"]["unavailable_tactic_ids"], "rfl"]
    )

    _write_json(portfolio_path, portfolio)
    _write_json(probe_path, probe)


def _mutate_rfl_public_projection(
    input_dir: Path,
    *,
    compile_status: str,
    source_compile_status: str,
    source_error_class: str,
    failure_classifier: str,
) -> None:
    probe_path = input_dir / "tactic_portfolio_probe.json"
    probe = _read_json(probe_path)
    for row in probe["tactics"]:
        if row["tactic_id"] == "rfl":
            row["compile_status"] = compile_status
            row["source_compile_status"] = source_compile_status
            row["source_error_class"] = source_error_class
            row["failure_classifier"] = failure_classifier
            break
    else:  # pragma: no cover - fixture contract guard
        raise AssertionError("expected rfl row in tactic portfolio projection")
    _write_json(probe_path, probe)


def _remove_simp_compile_status_from_real_probe_artifacts(input_dir: Path) -> None:
    portfolio_ref = tactic_portfolio_availability_probe.SOURCE_REFS[1]
    probe_ref = tactic_portfolio_availability_probe.SOURCE_REFS[0]
    portfolio_path = (
        input_dir
        / tactic_portfolio_availability_probe.SOURCE_BODY_REL_BY_SOURCE_REF[portfolio_ref]
    )
    probe_path = (
        input_dir
        / tactic_portfolio_availability_probe.SOURCE_BODY_REL_BY_SOURCE_REF[probe_ref]
    )
    projection_path = input_dir / "tactic_portfolio_probe.json"
    portfolio = _read_json(portfolio_path)
    probe = _read_json(probe_path)
    projection = _read_json(projection_path)

    for row in portfolio["rows"]:
        if row["tactic_id"] == "simp":
            row.pop("compile_status", None)
            break
    else:  # pragma: no cover - fixture contract guard
        raise AssertionError("expected simp row in source portfolio artifact")

    for row in probe["portfolio_core_v0"]["rows"]:
        if row["tactic_id"] == "simp":
            row.pop("compile_status", None)
            break
    else:  # pragma: no cover - fixture contract guard
        raise AssertionError("expected simp row in source probe artifact")

    for row in projection["tactics"]:
        if row["tactic_id"] == "simp":
            row.pop("compile_status", None)
            row.pop("source_compile_status", None)
            break
    else:  # pragma: no cover - fixture contract guard
        raise AssertionError("expected simp row in tactic portfolio projection")

    _write_json(portfolio_path, portfolio)
    _write_json(probe_path, probe)
    _write_json(projection_path, projection)


def _mutate_decide_authoritative_duration(input_dir: Path, *, duration_ms: int) -> None:
    portfolio_ref = tactic_portfolio_availability_probe.SOURCE_REFS[1]
    probe_ref = tactic_portfolio_availability_probe.SOURCE_REFS[0]
    portfolio_path = (
        input_dir
        / tactic_portfolio_availability_probe.SOURCE_BODY_REL_BY_SOURCE_REF[portfolio_ref]
    )
    probe_path = (
        input_dir
        / tactic_portfolio_availability_probe.SOURCE_BODY_REL_BY_SOURCE_REF[probe_ref]
    )
    portfolio = _read_json(portfolio_path)
    probe = _read_json(probe_path)

    for row in portfolio["rows"]:
        if row["tactic_id"] == "decide":
            row["duration_ms"] = duration_ms
            break
    else:  # pragma: no cover - fixture contract guard
        raise AssertionError("expected decide row in source portfolio artifact")

    for row in probe["portfolio_core_v0"]["rows"]:
        if row["tactic_id"] == "decide":
            row["duration_ms"] = duration_ms
            break
    else:  # pragma: no cover - fixture contract guard
        raise AssertionError("expected decide row in source probe artifact")

    _write_json(portfolio_path, portfolio)
    _write_json(probe_path, probe)


def _mutate_decide_public_projection_duration(
    input_dir: Path,
    *,
    duration_ms: int,
) -> None:
    probe_path = input_dir / "tactic_portfolio_probe.json"
    probe = _read_json(probe_path)
    for row in probe["tactics"]:
        if row["tactic_id"] == "decide":
            row["duration_ms"] = duration_ms
            break
    else:  # pragma: no cover - fixture contract guard
        raise AssertionError("expected decide row in tactic portfolio projection")
    _write_json(probe_path, probe)


def _mutate_authoritative_mathlib_environment_available(input_dir: Path) -> None:
    probe_ref = tactic_portfolio_availability_probe.SOURCE_REFS[0]
    corpus_ref = tactic_portfolio_availability_probe.SOURCE_REFS[2]
    probe_path = (
        input_dir
        / tactic_portfolio_availability_probe.SOURCE_BODY_REL_BY_SOURCE_REF[probe_ref]
    )
    corpus_path = (
        input_dir
        / tactic_portfolio_availability_probe.SOURCE_BODY_REL_BY_SOURCE_REF[corpus_ref]
    )
    probe = _read_json(probe_path)
    corpus = _read_json(corpus_path)

    mathlib = probe["mathlib"]
    mathlib["available"] = True
    mathlib["direct_mathlib_lane_available"] = True
    mathlib["lake_project_mathlib_lane_available"] = True
    mathlib["lean_status"] = "PASS"
    mathlib["mathlib_available"] = True
    mathlib["error_class"] = "NONE"
    mathlib["stdout_excerpt"] = ""

    corpus["mathlib_available"] = True
    corpus["mathlib_direct_import_available"] = True
    corpus["mathlib_lake_project_import_available"] = True

    _write_json(probe_path, probe)
    _write_json(corpus_path, corpus)


def test_tactic_portfolio_availability_observes_required_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/tactic_portfolio_availability_probe",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/tactic_portfolio_availability_probe_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["tactic_count"] == 8
    assert result["compile_status_counts"] == {
        "compile_pass": 7,
        "environment_fail": 1,
    }
    assert result["unavailable_reason_counts"] == {"MATHLIB_IMPORT_MISSING": 1}
    assert result["available_tactic_ids"] == [
        "decide",
        "grind",
        "native_decide",
        "omega",
        "rfl",
        "simp",
        "simp_all",
    ]
    assert result["unavailable_tactic_ids"] == ["aesop"]
    assert result["mathlib_dependent_tactic_ids"] == ["aesop"]
    assert result["mathlib_lake_project_import_available"] is False
    assert result["mathlib_absence_gate_enforced"] is True
    assert result["latency_profile_status"] == (
        "copied_probe_duration_rows_environment_scoped_not_benchmark_authority"
    )
    assert result["latency_profile_available_tactic_count"] == 7
    assert result["latency_band_counts"] == {
        "fast": 3,
        "moderate": 3,
        "slow": 1,
    }
    assert result["fastest_available_tactic_ids"] == [
        "decide",
        "native_decide",
        "simp",
    ]
    assert result["slowest_available_tactic_ids"] == [
        "rfl",
        "grind",
        "simp_all",
    ]
    assert result["available_tactic_duration_ms_min"] == 1971
    assert result["available_tactic_duration_ms_max"] == 8852
    assert result["available_tactic_duration_ms_median"] == 2567
    assert result["latency_missing_tactic_ids"] == []
    assert result["tactic_latency_profile"][0] == {
        "tactic_id": "decide",
        "duration_ms": 1971,
        "latency_band": "fast",
        "compile_status": "compile_pass",
        "requires_mathlib": False,
        "source_probe_ref": (
            "lean-toolchain://PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/"
            "tactic_affordance_probe/portfolio_core_v0/decide.lean"
        ),
    }
    assert result["body_material_status"] == "copied_non_secret_macro_body_with_provenance"
    assert result["tactic_availability_status"] == (
        "real_lean_std_tactic_affordance_probe_rows"
    )
    assert result["probe_source_body_status"] == (
        "copied_non_secret_lean_probe_source_bodies_with_digest_verification"
    )
    assert result["source_artifact_count"] == 13
    assert result["copied_source_artifact_count"] == 13
    assert result["source_body_artifact_count"] == 3
    assert result["copied_source_body_artifact_count"] == 3
    assert all(row["body_copied"] for row in result["source_artifact_imports"])
    assert any(
        row["source_ref"]
        == "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe.json"
        and row["body_copied"]
        for row in result["source_artifact_imports"]
    )
    assert result["probe_source_digest_refs"][
        "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe/portfolio_core_v0/rfl.lean"
    ] == "sha256:2d2b1800deb875c660693bd87af0715752316132da8a747c13487577feddc696"
    assert result["body_in_receipt"] is False
    assert result["source_digests"][
        "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe.json"
    ] == "sha256:20fdef8a53401f2bb21483002730895ca0295d2170bf148e8c328c041d8524c3"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["secret_exclusion_scan"]["real_substrate_default"] is True
    assert result["authority_ceiling"]["formal_proof_authority"] is False
    assert result["authority_ceiling"]["provider_calls_authorized"] is False
    assert result["authority_ceiling"]["latency_profile_is_environment_scoped"] is True
    assert (
        result["authority_ceiling"]["latency_profile_not_benchmark_authority"]
        is True
    )
    for case_id, codes in EXPECTED_NEGATIVE_CASES.items():
        for code in codes:
            assert code in result["observed_negative_cases"][case_id]


def test_tactic_portfolio_availability_moves_when_authoritative_source_row_changes(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/tactic_portfolio_availability_probe/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)
    _mutate_rfl_authoritative_source(
        input_dir,
        failure_code="MUTATED_REAL_SOURCE_COMPILE_FAIL",
    )
    _mutate_rfl_public_projection(
        input_dir,
        compile_status="compile_fail",
        source_compile_status="FAIL",
        source_error_class="MUTATED_REAL_SOURCE_COMPILE_FAIL",
        failure_classifier="MUTATED_REAL_SOURCE_COMPILE_FAIL",
    )
    _patch_source_digests(
        monkeypatch,
        input_dir=input_dir,
        source_refs=[
            tactic_portfolio_availability_probe.SOURCE_REFS[0],
            tactic_portfolio_availability_probe.SOURCE_REFS[1],
        ],
    )

    result = run(
        input_dir,
        tmp_path / "receipts/first_wave/tactic_portfolio_availability_probe",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["compile_status_counts"] == {
        "compile_pass": 6,
        "compile_fail": 1,
        "environment_fail": 1,
    }
    assert result["latency_profile_available_tactic_count"] == 6
    assert "rfl" not in result["available_tactic_ids"]
    assert "rfl" in result["unavailable_tactic_ids"]
    assert result["unavailable_reason_counts"] == {
        "MATHLIB_IMPORT_MISSING": 1,
        "MUTATED_REAL_SOURCE_COMPILE_FAIL": 1,
    }


def test_tactic_portfolio_availability_ignores_stale_public_failure_classifier(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/tactic_portfolio_availability_probe/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)
    _mutate_rfl_authoritative_source(
        input_dir,
        failure_code="MUTATED_REAL_SOURCE_COMPILE_FAIL",
    )
    _mutate_rfl_public_projection(
        input_dir,
        compile_status="compile_fail",
        source_compile_status="FAIL",
        source_error_class="MUTATED_REAL_SOURCE_COMPILE_FAIL",
        failure_classifier="STALE_PUBLIC_FAILURE_LABEL",
    )
    _patch_source_digests(
        monkeypatch,
        input_dir=input_dir,
        source_refs=[
            tactic_portfolio_availability_probe.SOURCE_REFS[0],
            tactic_portfolio_availability_probe.SOURCE_REFS[1],
        ],
    )

    result = run(
        input_dir,
        tmp_path / "receipts/first_wave/tactic_portfolio_availability_probe",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["compile_status_counts"] == {
        "compile_pass": 6,
        "compile_fail": 1,
        "environment_fail": 1,
    }
    assert "rfl" not in result["available_tactic_ids"]
    assert "rfl" in result["unavailable_tactic_ids"]
    assert result["unavailable_reason_counts"] == {
        "MATHLIB_IMPORT_MISSING": 1,
        "MUTATED_REAL_SOURCE_COMPILE_FAIL": 1,
    }
    assert "STALE_PUBLIC_FAILURE_LABEL" not in result["unavailable_reason_counts"]


def test_tactic_portfolio_availability_rejects_baked_labels_when_authoritative_source_moves(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/tactic_portfolio_availability_probe/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)
    _mutate_rfl_authoritative_source(
        input_dir,
        failure_code="MUTATED_REAL_SOURCE_COMPILE_FAIL",
    )
    _patch_source_digests(
        monkeypatch,
        input_dir=input_dir,
        source_refs=[
            tactic_portfolio_availability_probe.SOURCE_REFS[0],
            tactic_portfolio_availability_probe.SOURCE_REFS[1],
        ],
    )

    result = run(
        input_dir,
        tmp_path / "receipts/first_wave/tactic_portfolio_availability_probe",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "TACTIC_PORTFOLIO_PUBLIC_PROJECTION_CONTRADICTION" in result["error_codes"]
    assert result["compile_status_counts"] == {
        "compile_fail": 1,
        "compile_pass": 6,
        "environment_fail": 1,
    }
    assert result["latency_profile_available_tactic_count"] == 6
    assert "rfl" not in result["available_tactic_ids"]
    assert "rfl" in result["unavailable_tactic_ids"]
    assert result["unavailable_reason_counts"] == {
        "MATHLIB_IMPORT_MISSING": 1,
        "MUTATED_REAL_SOURCE_COMPILE_FAIL": 1,
    }
    assert any(
        finding["error_code"] == "TACTIC_PORTFOLIO_PUBLIC_PROJECTION_CONTRADICTION"
        and finding["subject_id"] == "rfl"
        for finding in result["findings"]
    )


def test_tactic_portfolio_availability_moves_when_authoritative_duration_changes(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/tactic_portfolio_availability_probe/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)
    _mutate_decide_authoritative_duration(input_dir, duration_ms=9300)
    _mutate_decide_public_projection_duration(input_dir, duration_ms=9300)
    _patch_source_digests(
        monkeypatch,
        input_dir=input_dir,
        source_refs=[
            tactic_portfolio_availability_probe.SOURCE_REFS[0],
            tactic_portfolio_availability_probe.SOURCE_REFS[1],
        ],
    )

    result = run(
        input_dir,
        tmp_path / "receipts/first_wave/tactic_portfolio_availability_probe",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["compile_status_counts"] == {
        "compile_pass": 7,
        "environment_fail": 1,
    }
    assert result["available_tactic_duration_ms_min"] == 1994
    assert result["available_tactic_duration_ms_max"] == 9300
    assert result["available_tactic_duration_ms_median"] == 3685
    assert result["fastest_available_tactic_ids"] == [
        "native_decide",
        "simp",
        "omega",
    ]
    assert result["slowest_available_tactic_ids"] == [
        "decide",
        "rfl",
        "grind",
    ]


def test_tactic_portfolio_availability_blocks_missing_compile_status_from_real_probe_artifact(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/tactic_portfolio_availability_probe/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)
    _remove_simp_compile_status_from_real_probe_artifacts(input_dir)
    _patch_source_digests(
        monkeypatch,
        input_dir=input_dir,
        source_refs=[
            tactic_portfolio_availability_probe.SOURCE_REFS[0],
            tactic_portfolio_availability_probe.SOURCE_REFS[1],
        ],
    )

    out_dir = tmp_path / "receipts/first_wave/tactic_portfolio_availability_probe"
    result = run(input_dir, out_dir, command="pytest")

    assert result["status"] == "blocked"
    assert "TACTIC_PORTFOLIO_MISSING_COMPILE_STATUS" in result["error_codes"]
    assert result["compile_status_counts"] == {
        "compile_pass": 6,
        "environment_fail": 1,
        "missing": 1,
    }
    assert result["latency_profile_available_tactic_count"] == 6
    assert "simp" not in result["available_tactic_ids"]
    assert result["available_tactic_duration_ms_median"] == 3126.0
    assert result["fastest_available_tactic_ids"] == [
        "decide",
        "native_decide",
        "omega",
    ]

    receipt = _read_json(out_dir / "tactic_portfolio_availability_result.json")
    assert receipt["status"] == "blocked"
    assert receipt["compile_status_counts"] == result["compile_status_counts"]
    assert any(
        finding["error_code"] == "TACTIC_PORTFOLIO_MISSING_COMPILE_STATUS"
        and finding["subject_id"] == "simp"
        for finding in receipt["findings"]
    )


def test_tactic_portfolio_availability_receipts_are_public_relative_and_real_substrate(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/tactic_portfolio_availability_probe",
        public_root / "fixtures/first_wave/tactic_portfolio_availability_probe",
    )
    result = run(
        public_root / "fixtures/first_wave/tactic_portfolio_availability_probe/input",
        public_root / "receipts/first_wave/tactic_portfolio_availability_probe",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_path in result["receipt_paths"]:
        assert not Path(receipt_path).is_absolute()
        receipt_file = public_root / receipt_path
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "NEGATIVE_FIXTURE_FORBIDDEN_PROOF_BODY_DO_NOT_ECHO" not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["body_material_status"] == (
            "copied_non_secret_macro_body_with_provenance"
        )
        assert payload["source_artifact_count"] == 13
        assert payload["copied_source_artifact_count"] == 13
        assert payload["source_body_artifact_count"] == 3
        assert payload["copied_source_body_artifact_count"] == 3
        assert payload["latency_profile_available_tactic_count"] == 7
        assert payload["latency_band_counts"] == {
            "fast": 3,
            "moderate": 3,
            "slow": 1,
        }
        assert payload["fastest_available_tactic_ids"] == [
            "decide",
            "native_decide",
            "simp",
        ]
        assert payload["latency_missing_tactic_ids"] == []
        assert all(row["body_copied"] for row in payload["source_artifact_imports"])
        assert payload["body_in_receipt"] is False
        assert "private_state_scan" not in payload
        assert "body_redacted" not in payload
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_tactic_portfolio_availability_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle_input = _copy_exported_bundle(public_root)
    result = run_availability_bundle(
        bundle_input,
        public_root
        / "receipts/runtime_shell/demo_project/organs/tactic_portfolio_availability_probe",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_tactic_portfolio_availability_bundle"
    assert result["bundle_id"] == "tactic_portfolio_availability_runtime_example"
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["tactic_count"] == 8
    assert result["mathlib_absence_gate_enforced"] is True
    assert result["latency_profile_available_tactic_count"] == 7
    assert result["latency_band_counts"] == {
        "fast": 3,
        "moderate": 3,
        "slow": 1,
    }
    assert result["fastest_available_tactic_ids"] == [
        "decide",
        "native_decide",
        "simp",
    ]
    assert result["body_material_status"] == "copied_non_secret_macro_body_with_provenance"
    assert result["tactic_availability_status"] == (
        "real_lean_std_tactic_affordance_probe_rows"
    )
    assert result["source_artifact_count"] == 13
    assert result["copied_source_artifact_count"] == 13
    assert result["source_body_artifact_count"] == 3
    assert result["copied_source_body_artifact_count"] == 3
    assert all(row["body_copied"] for row in result["source_artifact_imports"])
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["receipt_paths"] == [
        (
            "receipts/runtime_shell/demo_project/organs/"
            "tactic_portfolio_availability_probe/"
            "exported_tactic_portfolio_availability_bundle_validation_result.json"
        )
    ]


def test_tactic_portfolio_availability_exported_bundle_moves_when_authoritative_source_row_changes(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle_input = _copy_exported_bundle(public_root)
    _mutate_rfl_authoritative_source(
        bundle_input,
        failure_code="MUTATED_REAL_BUNDLE_SOURCE_COMPILE_FAIL",
    )
    _mutate_rfl_public_projection(
        bundle_input,
        compile_status="compile_fail",
        source_compile_status="FAIL",
        source_error_class="MUTATED_REAL_BUNDLE_SOURCE_COMPILE_FAIL",
        failure_classifier="MUTATED_REAL_BUNDLE_SOURCE_COMPILE_FAIL",
    )
    _patch_source_digests(
        monkeypatch,
        input_dir=bundle_input,
        source_refs=[
            tactic_portfolio_availability_probe.SOURCE_REFS[0],
            tactic_portfolio_availability_probe.SOURCE_REFS[1],
        ],
    )

    result = run_availability_bundle(
        bundle_input,
        public_root
        / "receipts/runtime_shell/demo_project/organs/tactic_portfolio_availability_probe",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["compile_status_counts"] == {
        "compile_pass": 6,
        "compile_fail": 1,
        "environment_fail": 1,
    }
    assert result["latency_profile_available_tactic_count"] == 6
    assert "rfl" not in result["available_tactic_ids"]
    assert "rfl" in result["unavailable_tactic_ids"]
    assert result["unavailable_reason_counts"] == {
        "MATHLIB_IMPORT_MISSING": 1,
        "MUTATED_REAL_BUNDLE_SOURCE_COMPILE_FAIL": 1,
    }


def test_tactic_portfolio_availability_exported_bundle_rejects_contradictory_real_probe_status(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle_input = _copy_exported_bundle(public_root)
    _mutate_rfl_public_projection(
        bundle_input,
        compile_status="compile_fail",
        source_compile_status="FAIL",
        source_error_class="MUTATED_REAL_BUNDLE_PROJECTION_ONLY_FAIL",
        failure_classifier="MUTATED_REAL_BUNDLE_PROJECTION_ONLY_FAIL",
    )

    result = run_availability_bundle(
        bundle_input,
        public_root
        / "receipts/runtime_shell/demo_project/organs/tactic_portfolio_availability_probe",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "TACTIC_PORTFOLIO_PUBLIC_PROJECTION_CONTRADICTION" in result["error_codes"]
    assert result["compile_status_counts"] == {
        "compile_pass": 7,
        "environment_fail": 1,
    }
    assert "rfl" in result["available_tactic_ids"]
    assert "rfl" not in result["unavailable_tactic_ids"]
    assert any(
        finding["error_code"] == "TACTIC_PORTFOLIO_PUBLIC_PROJECTION_CONTRADICTION"
        and finding["subject_id"] == "rfl"
        for finding in result["findings"]
    )


def test_tactic_portfolio_availability_rejects_stale_public_duration_projection(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle_input = _copy_exported_bundle(public_root)
    _mutate_decide_public_projection_duration(bundle_input, duration_ms=9300)

    result = run_availability_bundle(
        bundle_input,
        public_root
        / "receipts/runtime_shell/demo_project/organs/tactic_portfolio_availability_probe",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "TACTIC_PORTFOLIO_PUBLIC_PROJECTION_CONTRADICTION" in result["error_codes"]
    assert any(
        finding["error_code"] == "TACTIC_PORTFOLIO_PUBLIC_PROJECTION_CONTRADICTION"
        and finding["subject_id"] == "decide"
        for finding in result["findings"]
    )


def test_tactic_portfolio_availability_rejects_stale_public_environment_projection(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle_input = _copy_exported_bundle(public_root)
    _mutate_authoritative_mathlib_environment_available(bundle_input)
    _patch_source_digests(
        monkeypatch,
        input_dir=bundle_input,
        source_refs=[
            tactic_portfolio_availability_probe.SOURCE_REFS[0],
            tactic_portfolio_availability_probe.SOURCE_REFS[2],
        ],
    )

    result = run_availability_bundle(
        bundle_input,
        public_root
        / "receipts/runtime_shell/demo_project/organs/tactic_portfolio_availability_probe",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "TACTIC_PORTFOLIO_ENVIRONMENT_SOURCE_CONTRADICTION" in result["error_codes"]
    assert "TACTIC_PORTFOLIO_PUBLIC_PROJECTION_CONTRADICTION" in result["error_codes"]
    assert result["compile_status_counts"] == {
        "compile_fail": 1,
        "compile_pass": 7,
    }
    assert result["available_tactic_ids"] == [
        "decide",
        "grind",
        "native_decide",
        "omega",
        "rfl",
        "simp",
        "simp_all",
    ]
    assert result["unavailable_tactic_ids"] == ["aesop"]
    assert result["mathlib_probe_status"] == "compile_pass"
    assert result["mathlib_lake_project_import_available"] is True
    assert result["mathlib_absence_gate_enforced"] is False
    assert any(
        finding["error_code"] == "TACTIC_PORTFOLIO_ENVIRONMENT_SOURCE_CONTRADICTION"
        and finding["subject_id"] == "mathlib_lake_project_import_available"
        for finding in result["findings"]
    )
    assert any(
        finding["error_code"] == "TACTIC_PORTFOLIO_PUBLIC_PROJECTION_CONTRADICTION"
        and finding["subject_id"] == "aesop"
        for finding in result["findings"]
    )


def test_tactic_portfolio_availability_blocks_mathlib_tactic_promoted_against_environment_probe(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle_input = _copy_exported_bundle(public_root)
    probe_path = bundle_input / "tactic_portfolio_probe.json"
    probe = json.loads(probe_path.read_text(encoding="utf-8"))

    for row in probe["tactics"]:
        if row["tactic_id"] == "aesop":
            row["compile_status"] = "compile_pass"
            row["source_compile_status"] = "PASS"
            row["source_error_class"] = "NONE"
            row.pop("failure_classifier", None)
            row.pop("diagnostic", None)
            break
    else:  # pragma: no cover - fixture contract guard
        raise AssertionError("expected aesop row in exported bundle fixture")

    probe_path.write_text(json.dumps(probe, indent=2, sort_keys=True) + "\n")

    result = run_availability_bundle(
        bundle_input,
        public_root
        / "receipts/runtime_shell/demo_project/organs/tactic_portfolio_availability_probe",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "TACTIC_PORTFOLIO_PUBLIC_PROJECTION_CONTRADICTION" in result["error_codes"]
    assert result["compile_status_counts"] == {
        "compile_pass": 7,
        "environment_fail": 1,
    }
    assert result["available_tactic_ids"] == [
        "decide",
        "grind",
        "native_decide",
        "omega",
        "rfl",
        "simp",
        "simp_all",
    ]
    assert result["unavailable_tactic_ids"] == ["aesop"]
    assert any(
        finding["error_code"] == "TACTIC_PORTFOLIO_PUBLIC_PROJECTION_CONTRADICTION"
        and finding["subject_id"] == "aesop"
        for finding in result["findings"]
    )


def test_tactic_portfolio_availability_blocks_contradictory_environment_probe(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle_input = _copy_exported_bundle(public_root)
    environment_path = bundle_input / "environment_probe.json"
    environment = json.loads(environment_path.read_text(encoding="utf-8"))
    environment["mathlib_probe_status"] = "environment_fail"
    environment["mathlib_lake_project_import_available"] = True
    environment_path.write_text(
        json.dumps(environment, indent=2, sort_keys=True) + "\n"
    )

    result = run_availability_bundle(
        bundle_input,
        public_root
        / "receipts/runtime_shell/demo_project/organs/tactic_portfolio_availability_probe",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "TACTIC_PORTFOLIO_ENVIRONMENT_PROBE_CONTRADICTION" in result["error_codes"]
    assert result["available_tactic_ids"] == [
        "decide",
        "grind",
        "native_decide",
        "omega",
        "rfl",
        "simp",
        "simp_all",
    ]
    assert any(
        finding["error_code"] == "TACTIC_PORTFOLIO_ENVIRONMENT_PROBE_CONTRADICTION"
        and finding["negative_case_id"] == "positive_environment_probe"
        for finding in result["findings"]
    )


def test_tactic_portfolio_availability_blocks_perturbed_probe_source_body(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle_input = _copy_exported_bundle(public_root)
    source_path = (
        bundle_input
        / "source_artifacts/tactic_affordance_probe/portfolio_core_v0/simp.lean"
    )
    source_path.write_text(
        source_path.read_text(encoding="utf-8")
        + "\n-- mutated digest sentinel\n",
        encoding="utf-8",
    )

    result = run_availability_bundle(
        bundle_input,
        public_root
        / "receipts/runtime_shell/demo_project/organs/tactic_portfolio_availability_probe",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "TACTIC_PORTFOLIO_SOURCE_ARTIFACT_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_artifact_count"] == 13
    assert result["copied_source_artifact_count"] == 12
    assert any(
        row["source_ref"].endswith(
            "tactic_affordance_probe/portfolio_core_v0/simp.lean"
        )
        and row["body_copied"] is False
        for row in result["source_artifact_imports"]
    )
    assert result["available_tactic_ids"] == [
        "decide",
        "grind",
        "native_decide",
        "omega",
        "rfl",
        "simp",
        "simp_all",
    ]


def test_tactic_portfolio_availability_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    out_dir = tmp_path / "bundle-card"
    args = [
        "run-availability-bundle",
        "--input",
        str(EXPORTED_BUNDLE_INPUT),
        "--out",
        str(out_dir),
    ]
    assert main(args) == 0
    assert not capsys.readouterr().out

    def fail_rebuild(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh availability bundle receipt should be reused")

    monkeypatch.setattr(
        tactic_portfolio_availability_probe,
        "_build_result",
        fail_rebuild,
    )
    assert main([*args, "--card"]) == 0
    card = json.loads(capsys.readouterr().out)
    full_receipt = json.loads((out_dir / BUNDLE_RESULT_NAME).read_text())

    assert card["schema_version"] == CARD_SCHEMA_VERSION
    assert card["status"] == "pass"
    assert card["input_mode"] == "exported_tactic_portfolio_availability_bundle"
    assert card["cache_status"] == "fresh_exported_bundle_receipt_reused"
    assert card["receipt_summary"]["result_receipt_name"] == BUNDLE_RESULT_NAME
    assert card["availability_summary"]["tactic_count"] == 8
    assert card["availability_summary"]["available_tactic_count"] == 7
    assert card["availability_summary"]["unavailable_tactic_count"] == 1
    assert card["availability_summary"]["latency_profile_available_tactic_count"] == 7
    assert card["availability_summary"]["latency_band_counts"] == {
        "fast": 3,
        "moderate": 3,
        "slow": 1,
    }
    assert card["availability_summary"]["fastest_available_tactic_ids"] == [
        "decide",
        "native_decide",
        "simp",
    ]
    assert card["availability_summary"]["profile_rows_exported"] is False
    assert card["source_artifact_summary"]["source_artifact_rows_exported"] is False
    assert card["no_export_guards"]["source_artifact_imports_exported"] is False
    assert "tactic_latency_profile" not in card
    assert "source_artifact_imports" not in card
    assert "anti_claim" not in card
    assert "secret_exclusion_scan" not in card
    assert len(json.dumps(card, sort_keys=True)) < len(
        json.dumps(full_receipt, sort_keys=True)
    )


def test_tactic_portfolio_availability_bundle_recomputes_after_real_source_perturbation(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    bundle_input = _copy_exported_bundle(public_root)
    out_dir = (
        public_root
        / "receipts/runtime_shell/demo_project/organs/tactic_portfolio_availability_probe"
    )
    command = "pytest run-availability-bundle"

    baseline = run_availability_bundle(bundle_input, out_dir, command=command)
    assert baseline["status"] == "pass"
    assert baseline["cache_status"] == "rebuilt"
    assert baseline["available_tactic_ids"] == [
        "decide",
        "grind",
        "native_decide",
        "omega",
        "rfl",
        "simp",
        "simp_all",
    ]

    baseline_receipt_mtime_ns = (out_dir / BUNDLE_RESULT_NAME).stat().st_mtime_ns
    _mutate_rfl_authoritative_source(
        bundle_input,
        failure_code="MUTATED_REAL_BUNDLE_SOURCE_COMPILE_FAIL",
    )
    _patch_source_digests(
        monkeypatch,
        input_dir=bundle_input,
        source_refs=[
            tactic_portfolio_availability_probe.SOURCE_REFS[0],
            tactic_portfolio_availability_probe.SOURCE_REFS[1],
        ],
    )
    for source_ref in tactic_portfolio_availability_probe.SOURCE_REFS[:2]:
        source_path = (
            bundle_input
            / tactic_portfolio_availability_probe.SOURCE_BODY_REL_BY_SOURCE_REF[
                source_ref
            ]
        )
        os.utime(
            source_path,
            ns=(baseline_receipt_mtime_ns + 1, baseline_receipt_mtime_ns + 1),
        )

    mutated = run_availability_bundle(bundle_input, out_dir, command=command)

    assert mutated["status"] == "blocked"
    assert mutated["cache_status"] == "rebuilt"
    assert mutated["freshness_basis"]["latest_input_mtime_ns"] > baseline_receipt_mtime_ns
    assert mutated["compile_status_counts"] == {
        "compile_fail": 1,
        "compile_pass": 6,
        "environment_fail": 1,
    }
    assert mutated["latency_profile_available_tactic_count"] == 6
    assert "rfl" not in mutated["available_tactic_ids"]
    assert "rfl" in mutated["unavailable_tactic_ids"]
    assert mutated["unavailable_reason_counts"] == {
        "MATHLIB_IMPORT_MISSING": 1,
        "MUTATED_REAL_BUNDLE_SOURCE_COMPILE_FAIL": 1,
    }
    assert "TACTIC_PORTFOLIO_PUBLIC_PROJECTION_CONTRADICTION" in mutated["error_codes"]


def test_tactic_portfolio_availability_exported_source_modules_are_digest_verified() -> None:
    manifest = json.loads((EXPORTED_BUNDLE_INPUT / "source_module_manifest.json").read_text())

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 13
    assert len(manifest["modules"]) == 13

    repo_root = MICROCOSM_ROOT.parent
    for module in manifest["modules"]:
        source = repo_root / module["source_ref"]
        target = repo_root / module["target_ref"]
        source_digest = _sha256_prefixed(module.get("source_sha256") or module["sha256"])
        target_digest = _sha256_prefixed(module.get("target_sha256") or module["sha256"])
        assert source.is_file()
        assert target.is_file()
        assert _sha256(source) == source_digest
        assert _sha256(target) == target_digest
        if module["source_to_target_relation"] == "exact_copy":
            assert source_digest == target_digest
        else:
            assert module["source_to_target_relation"] == (
                "verified_public_safe_private_path_rewrite"
            )
            assert source_digest != target_digest
            assert module["verification_mode"] == "verified_light_edit_recipe"
            assert module["public_safe_transform"]["body_text_in_receipt"] is False
            assert Path.home().as_posix() not in target.read_text(encoding="utf-8")
        assert module["body_copied"] is True
        assert module["body_in_receipt"] is False
