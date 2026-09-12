from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from microcosm_core import cli
from microcosm_core import release_export
from microcosm_core.organs import bridge_phase_continuity_runtime as bridge_runtime


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/second_wave/bridge_phase_continuity_runtime/input"

REQUIRED_RECEIPT_FIELDS = {
    "schema_version",
    "checker_id",
    "organ_id",
    "fixture_id",
    "validator_id",
    "command",
    "status",
    "source_pattern_ids",
    "continuation_packet_status",
    "heartbeat_status",
    "resource_pressure_decision",
    "resume_once_status",
    "duplicate_resume_rejection",
    "closeout_transition_path",
    "expected_negative_cases",
    "observed_negative_cases",
    "error_codes",
    "acceptance_scope",
    "manifest_ref",
    "readiness_contract_ref",
    "negative_case_contract_ref",
    "required_parent_acceptance_refs",
    "dependency_preflight_receipt_ref",
    "synthetic_input_refs",
    "synthetic_fixture_gate_status",
    "synthetic_transport_fixture_summary",
    "worker_skip_receipt_status",
    "private_state_scan",
    "anti_claim",
    "authority_ceiling",
    "receipt_paths",
    "receipt_write_status",
    "written_receipt_count",
    "receipt_write_skipped_count",
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _walk_keys(payload: object) -> list[str]:
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


def _replace_transport_label(payload: object, label: str) -> object:
    encoded = json.dumps(payload)
    return json.loads(encoded.replace("synthetic_transport", label))


def _transport_inputs_with_label(label: str) -> dict[str, dict[str, Any]]:
    inputs: dict[str, dict[str, Any]] = {}
    for name in bridge_runtime.EXPECTED_SYNTHETIC_TRANSPORT_INPUTS:
        path = FIXTURE_INPUT / name
        if path.suffix == ".jsonl":
            payload: object = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        else:
            payload = _load_json(path)
        inputs[name] = {
            "ref": str(path),
            "path": path,
            "payload": _replace_transport_label(payload, label),
        }
    return inputs


def _validate_transport_inputs(
    inputs: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    summary = bridge_runtime._validate_synthetic_transport_contract(
        inputs,
        findings=findings,
    )
    return summary, findings


def _mutated_transport_inputs() -> dict[str, dict[str, Any]]:
    return copy.deepcopy(_transport_inputs_with_label("synthetic_transport"))


def _copy_fixture_input(tmp_path: Path) -> Path:
    input_dir = tmp_path / "input"
    shutil.copytree(FIXTURE_INPUT, input_dir)
    return input_dir


def test_bridge_phase_continuity_jsonl_reader_streams(
    tmp_path: Path, monkeypatch
) -> None:
    rows_path = tmp_path / "heartbeat_rows.jsonl"
    rows_path.write_text(
        '{"heartbeat_id": "hb_1"}\n'
        "\n"
        "not-json\n"
        "[1]\n"
        '{"heartbeat_id": "hb_2"}\n',
        encoding="utf-8",
    )
    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self == rows_path:
            raise AssertionError("bridge continuity JSONL reader should stream input")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    findings: list[dict[str, Any]] = []

    rows = bridge_runtime._read_required_jsonl(
        rows_path,
        subject="heartbeat_rows",
        findings=findings,
    )

    assert rows == [{"heartbeat_id": "hb_1"}, {"heartbeat_id": "hb_2"}]
    assert [finding["line"] for finding in findings] == [3, 4]
    assert {finding["error_code"] for finding in findings} == {
        "BRIDGE_CONTINUITY_INPUT_INVALID_JSONL",
        "BRIDGE_CONTINUITY_INPUT_JSONL_ROW_NOT_OBJECT",
    }


def test_bridge_phase_continuity_runner_consumes_observe_apply_fixture(tmp_path: Path) -> None:
    out_dir = tmp_path / "bridge_phase_continuity_runtime"
    result = bridge_runtime.run(FIXTURE_INPUT, out_dir, command="pytest bridge continuity")

    assert result["status"] == "pass"
    assert result["organ_id"] == bridge_runtime.ORGAN_ID
    assert result["fixture_id"] == bridge_runtime.FIXTURE_ID
    assert result["observed_fixture_id"] == "observe_runtime_apply_session_bridge_continuity_v0"
    assert result["acceptance_scope"] == "observe_apply_fixture_consumption_only"
    assert result["receipt_paths"] == bridge_runtime.EXPECTED_RECEIPT_PATHS
    assert result["written_receipt_count"] == 5
    assert result["receipt_write_skipped_count"] == 0
    assert result["receipt_write_status"] == {
        "status": "writes_allowed",
        "requested_count": 5,
        "written_count": 5,
        "skipped_count": 0,
        "receipt_writes_enabled": True,
        "tracked_receipt_write_blocked_count": 0,
        "requires_tracked_receipt_env": False,
        "tracked_receipt_refresh_env": None,
        "reason": None,
    }
    assert result["missing_negative_cases"] == []
    assert set(result["expected_negative_cases"]) == set(bridge_runtime.EXPECTED_NEGATIVE_CASES)
    assert result["private_state_scan"]["status"] == "pass"
    assert result["private_state_scan"]["blocking_hit_count"] == 0
    assert result["private_state_scan"]["scanned_path_count"] == 7
    assert result["authority_ceiling"]["live_bridge_transport_authorized"] is False

    for receipt_rel in bridge_runtime.EXPECTED_RECEIPT_PATHS:
        receipt = _load_json(out_dir / Path(receipt_rel).name)
        assert REQUIRED_RECEIPT_FIELDS <= set(receipt)
        assert receipt["status"] == "pass"
        assert receipt["receipt_path"] == receipt_rel
        assert receipt["receipt_paths"] == bridge_runtime.EXPECTED_RECEIPT_PATHS
        assert receipt["written_receipt_count"] == 5
        assert receipt["receipt_write_skipped_count"] == 0
        assert receipt["receipt_write_status"]["status"] == "writes_allowed"
        assert receipt["private_state_scan"]["forbidden_output_fields_omitted"] is True
        assert "fake_transport_fixture_summary" not in receipt


def test_bridge_phase_continuity_runner_reports_tracked_receipt_write_gate(
    monkeypatch: Any,
) -> None:
    monkeypatch.delenv("MICROCOSM_TRACKED_RECEIPT_WRITES", raising=False)
    out_dir = MICROCOSM_ROOT / "receipts" / "_pytest_bridge_tracked_write_gate"
    shutil.rmtree(out_dir, ignore_errors=True)

    try:
        result = bridge_runtime.run(FIXTURE_INPUT, out_dir, command="pytest tracked gate")

        assert result["status"] == "pass"
        assert result["written_receipt_count"] == 0
        assert result["receipt_write_skipped_count"] == 5
        assert result["receipt_write_status"] == {
            "status": "tracked_receipt_writes_blocked",
            "requested_count": 5,
            "written_count": 0,
            "skipped_count": 5,
            "receipt_writes_enabled": True,
            "tracked_receipt_write_blocked_count": 5,
            "requires_tracked_receipt_env": True,
            "tracked_receipt_refresh_env": "MICROCOSM_TRACKED_RECEIPT_WRITES=1",
            "reason": "set_MICROCOSM_TRACKED_RECEIPT_WRITES_1_to_refresh_tracked_receipts",
        }
        assert not out_dir.exists()
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


def test_bridge_phase_continuity_fixture_inputs_use_public_synthetic_transport_label() -> None:
    fixture_text = (
        FIXTURE_INPUT / bridge_runtime.INPUT_NAME
    ).read_text(encoding="utf-8")

    assert "expected_error_code" not in fixture_text
    for name in bridge_runtime.EXPECTED_SYNTHETIC_TRANSPORT_INPUTS:
        path = FIXTURE_INPUT / name
        if path.suffix not in {".json", ".jsonl"}:
            continue
        text = path.read_text(encoding="utf-8")
        assert "fake_transport" not in text
        assert "expected_error_code" not in text
    assert "synthetic_transport" in (FIXTURE_INPUT / "detached_job.json").read_text(
        encoding="utf-8"
    )


def test_bridge_phase_continuity_observe_apply_rollback_rejection_moves_with_input(
) -> None:
    fixture = _load_json(FIXTURE_INPUT / bridge_runtime.INPUT_NAME)
    manifest = _load_json(
        MICROCOSM_ROOT
        / "core/fixture_manifests/bridge_phase_continuity_runtime.fixture_manifest.json"
    )
    source_manifest = _load_json(
        MICROCOSM_ROOT
        / "examples/macro_projection_import_protocol/exported_projection_import_bundle/"
        "observe_runtime_source_module_manifest.json"
    )
    rollback = fixture["synthetic_observe_apply_session"][
        "rollback_on_validation_failure"
    ]
    assert bridge_runtime._rollback_validation_failure_rejected(rollback) is True

    rollback["validation_status"] = "pass"
    rollback["rollback_required"] = False
    rollback["writes_allowed_after_failure"] = True

    findings: list[dict[str, Any]] = []
    summary = bridge_runtime._validate_fixture_contract(
        fixture,
        manifest,
        source_manifest,
        public_root=MICROCOSM_ROOT,
        findings=findings,
    )

    assert summary["rollback_validation_failure_rejected"] is False
    assert "BRIDGE_CONTINUITY_ROLLBACK_CASE_MISSING" in {
        finding["error_code"] for finding in findings
    }


def _synthetic_original_source_manifest(
    tmp_path: Path,
) -> tuple[dict[str, Any], Path]:
    fixture = _load_json(FIXTURE_INPUT / bridge_runtime.INPUT_NAME)
    public_root = tmp_path / "microcosm-substrate"
    modules = []
    for index, target_ref in enumerate(fixture["source_module_refs"]):
        matched_private_ref = f"system/lib/source_{index}.py"
        body = f"SOURCE_{index} = True\n".encode()
        target = bridge_runtime._resolve_ref(target_ref, public_root=public_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        modules.append(
            {
                "module_id": f"source_{index}_body_import",
                "source_ref": matched_private_ref,
                "target_ref": target_ref,
                "body_copied": True,
                "sha256_match": True,
                "source_sha256": hashlib.sha256(body).hexdigest(),
                "target_sha256": hashlib.sha256(body).hexdigest(),
            }
        )
    return {"module_count": len(modules), "modules": modules}, public_root


def test_bridge_phase_continuity_resolves_logical_public_root_in_renamed_checkout(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "plectis"

    assert bridge_runtime._resolve_ref(
        "microcosm-substrate/src/microcosm_core/example.py",
        public_root=public_root,
    ) == public_root / "src/microcosm_core/example.py"
    assert bridge_runtime._resolve_ref(
        "state/example.json", public_root=public_root
    ) == tmp_path / "state/example.json"


def _release_substituted_source_manifest(
    tmp_path: Path,
) -> tuple[dict[str, Any], Path]:
    source_manifest, public_root = _synthetic_original_source_manifest(tmp_path)
    omissions = []
    for module in source_manifest["modules"]:
        target_ref = module["target_ref"]
        matched_private_ref = module["source_ref"]
        substitution = {
            "substitution": "public_safe_stub",
            "matched_private_ref": matched_private_ref,
            "contamination_class": "private_body_exact_match",
            "body_in_receipt": False,
        }
        omissions.append(
            {
                "module_id": module["module_id"],
                "path": target_ref,
                "source_ref": matched_private_ref,
                "release_substitution": substitution,
                "body_in_receipt": False,
            }
        )
        target = bridge_runtime._resolve_ref(target_ref, public_root=public_root)
        target.write_text(
            release_export._source_module_private_body_substitution_text(
                rel=target_ref,
                match_row=substitution,
            ),
            encoding="utf-8",
        )
    return {
        "module_count": 0,
        "modules": [],
        "release_substitution_omissions": omissions,
    }, public_root


def _fixture_contract_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        _load_json(FIXTURE_INPUT / bridge_runtime.INPUT_NAME),
        _load_json(
            MICROCOSM_ROOT
            / "core/fixture_manifests/bridge_phase_continuity_runtime.fixture_manifest.json"
        ),
    )


def test_bridge_phase_continuity_accepts_exact_release_export_stubs(
    tmp_path: Path,
) -> None:
    fixture, manifest = _fixture_contract_inputs()
    source_manifest, public_root = _release_substituted_source_manifest(tmp_path)
    findings: list[dict[str, Any]] = []

    summary = bridge_runtime._validate_fixture_contract(
        fixture, manifest, source_manifest, public_root=public_root, findings=findings
    )

    assert findings == []
    assert len(summary["source_digest_results"]) == 5
    assert all(
        row["verification_mode"] == "release_export_public_safe_stub_exact_match"
        and row["original_body_verified"] is False
        and row["sha256_match"] is False
        for row in summary["source_digest_results"]
    )


@pytest.mark.parametrize(
    "mutation, expected_code",
    (
        ("tampered_stub", "BRIDGE_CONTINUITY_RELEASE_SUBSTITUTION_STUB_MISSING_OR_TAMPERED"),
        ("missing_stub", "BRIDGE_CONTINUITY_RELEASE_SUBSTITUTION_STUB_MISSING_OR_TAMPERED"),
        ("invalid_utf8", "BRIDGE_CONTINUITY_RELEASE_SUBSTITUTION_STUB_MISSING_OR_TAMPERED"),
        ("undeclared_ref", "BRIDGE_CONTINUITY_SOURCE_REF_MISMATCH"),
        ("invalid_flags", "BRIDGE_CONTINUITY_RELEASE_SUBSTITUTION_INVALID"),
        ("duplicate_omission", "BRIDGE_CONTINUITY_RELEASE_SUBSTITUTION_INVALID"),
        ("malformed_omission", "BRIDGE_CONTINUITY_RELEASE_SUBSTITUTION_INVALID"),
        ("traversal_path", "BRIDGE_CONTINUITY_RELEASE_SUBSTITUTION_INVALID"),
        ("list_contamination_class", "BRIDGE_CONTINUITY_RELEASE_SUBSTITUTION_INVALID"),
        ("object_contamination_class", "BRIDGE_CONTINUITY_RELEASE_SUBSTITUTION_INVALID"),
    ),
)
def test_bridge_phase_continuity_rejects_unverified_release_substitutions(
    tmp_path: Path,
    mutation: str,
    expected_code: str,
) -> None:
    fixture, manifest = _fixture_contract_inputs()
    source_manifest, public_root = _release_substituted_source_manifest(tmp_path)
    first = source_manifest["release_substitution_omissions"][0]
    target = bridge_runtime._resolve_ref(first["path"], public_root=public_root)
    if mutation == "tampered_stub":
        target.write_text("tampered\n", encoding="utf-8")
    elif mutation == "missing_stub":
        target.unlink()
    elif mutation == "invalid_utf8":
        target.write_bytes(b"\xff\xfe")
    elif mutation == "undeclared_ref":
        source_manifest["release_substitution_omissions"].pop()
    elif mutation == "invalid_flags":
        first["body_in_receipt"] = True
    elif mutation == "duplicate_omission":
        source_manifest["release_substitution_omissions"].append(copy.deepcopy(first))
    elif mutation == "malformed_omission":
        source_manifest["release_substitution_omissions"].append("not-a-row")
    elif mutation == "traversal_path":
        first["path"] = "microcosm-substrate/../outside.py"
    elif mutation == "list_contamination_class":
        first["release_substitution"]["contamination_class"] = [
            "private_body_exact_match"
        ]
    else:
        first["release_substitution"]["contamination_class"] = {
            "name": "private_body_exact_match"
        }

    findings: list[dict[str, Any]] = []
    bridge_runtime._validate_fixture_contract(
        fixture, manifest, source_manifest, public_root=public_root, findings=findings
    )

    assert expected_code in {finding["error_code"] for finding in findings}


def test_bridge_phase_continuity_rejects_escaping_stub_without_probing_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture, manifest = _fixture_contract_inputs()
    source_manifest, public_root = _release_substituted_source_manifest(tmp_path)
    first = source_manifest["release_substitution_omissions"][0]
    target = bridge_runtime._resolve_ref(first["path"], public_root=public_root)
    outside = tmp_path / "outside.py"
    outside.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
    target.unlink()
    target.symlink_to(outside)
    original_is_file = Path.is_file
    original_read_text = Path.read_text

    def guarded_is_file(self: Path) -> bool:
        if self == target or self == outside:
            raise AssertionError("escaping release stub must not be probed")
        return original_is_file(self)

    def guarded_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self == target or self == outside:
            raise AssertionError("escaping release stub must not be read")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "is_file", guarded_is_file)
    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    findings: list[dict[str, Any]] = []

    bridge_runtime._validate_fixture_contract(
        fixture, manifest, source_manifest, public_root=public_root, findings=findings
    )

    assert "BRIDGE_CONTINUITY_RELEASE_SUBSTITUTION_INVALID" in {
        finding["error_code"] for finding in findings
    }


def test_bridge_phase_continuity_original_modules_retain_digest_verification(
    tmp_path: Path,
) -> None:
    fixture, manifest = _fixture_contract_inputs()
    source_manifest, public_root = _synthetic_original_source_manifest(tmp_path)
    findings: list[dict[str, Any]] = []

    summary = bridge_runtime._validate_fixture_contract(
        fixture, manifest, source_manifest, public_root=public_root, findings=findings
    )

    assert findings == []
    assert len(summary["source_digest_results"]) == 5
    assert all(
        row["verification_mode"] == "sha256"
        and row["original_body_verified"] is True
        and row["sha256_match"] is True
        for row in summary["source_digest_results"]
    )

    first = source_manifest["modules"][0]
    bridge_runtime._resolve_ref(first["target_ref"], public_root=public_root).write_text(
        "tampered\n", encoding="utf-8"
    )
    tampered_findings: list[dict[str, Any]] = []
    tampered = bridge_runtime._validate_fixture_contract(
        fixture,
        manifest,
        source_manifest,
        public_root=public_root,
        findings=tampered_findings,
    )
    assert "BRIDGE_CONTINUITY_SOURCE_DIGEST_MISMATCH" in {
        finding["error_code"] for finding in tampered_findings
    }
    assert any(
        row["status"] == "blocked" and row["original_body_verified"] is False
        for row in tampered["source_digest_results"]
    )

    source_manifest, public_root = _synthetic_original_source_manifest(tmp_path / "provenance")
    source_manifest["modules"][0]["source_sha256"] = "0" * 64
    source_manifest["modules"][0]["sha256_match"] = False
    provenance_findings: list[dict[str, Any]] = []
    provenance = bridge_runtime._validate_fixture_contract(
        fixture,
        manifest,
        source_manifest,
        public_root=public_root,
        findings=provenance_findings,
    )
    assert "BRIDGE_CONTINUITY_SOURCE_PROVENANCE_MISMATCH" in {
        finding["error_code"] for finding in provenance_findings
    }
    first_result = provenance["source_digest_results"][0]
    assert first_result["sha256_match"] is True
    assert first_result["original_body_verified"] is False
    assert first_result["status"] == "blocked"


def test_bridge_phase_continuity_transport_rejections_are_semantic_not_answer_keys() -> None:
    summary, findings = _validate_transport_inputs(
        _transport_inputs_with_label("synthetic_transport")
    )

    assert summary["status"] == "pass"
    assert findings == []
    assert set(summary["error_codes"]) >= {
        "CONTINUATION_PACKET_ALREADY_CONSUMED",
        "HEARTBEAT_NOT_RESUME_AUTHORITY",
        "MISSING_CONTINUATION_PACKET",
        "MISSING_CONTINUATION_PACKET_FIELDS",
        "RESOURCE_PRESSURE_DISPATCH_BLOCKED",
        "STALE_HEARTBEAT_LIVENESS_CLAIM",
    }


def test_bridge_phase_continuity_stale_heartbeat_rejection_moves_with_input() -> None:
    inputs = _mutated_transport_inputs()
    rows = inputs[bridge_runtime.HEARTBEAT_ROWS_NAME]["payload"]
    for row in rows:
        if row.get("heartbeat_id") == "heartbeat_stale":
            row["age_seconds"] = 12
            row["status"] = "alive"
            row["claims_live_bridge_health"] = False

    summary, findings = _validate_transport_inputs(inputs)

    assert summary["status"] == "blocked"
    assert summary["heartbeat_stale_count"] == 0
    assert "STALE_HEARTBEAT_LIVENESS_CLAIM" not in summary["error_codes"]
    assert {finding["error_code"] for finding in findings} >= {
        "STALE_HEARTBEAT_LIVENESS_CLAIM",
    }


def test_bridge_phase_continuity_stale_heartbeat_requires_liveness_overclaim() -> None:
    inputs = _mutated_transport_inputs()
    rows = inputs[bridge_runtime.HEARTBEAT_ROWS_NAME]["payload"]
    for row in rows:
        if row.get("heartbeat_id") == "heartbeat_stale":
            row["age_seconds"] = 9999
            row["status"] = "stale"
            row["claims_live_bridge_health"] = False

    summary, findings = _validate_transport_inputs(inputs)

    assert summary["status"] == "blocked"
    assert summary["heartbeat_stale_count"] == 1
    assert summary["stale_heartbeat_rejected"] is False
    assert "STALE_HEARTBEAT_LIVENESS_CLAIM" not in summary["error_codes"]
    assert {finding["error_code"] for finding in findings} >= {
        "STALE_HEARTBEAT_LIVENESS_CLAIM",
    }


def test_bridge_phase_continuity_duplicate_resume_rejection_moves_with_input() -> None:
    inputs = _mutated_transport_inputs()
    packets = inputs[bridge_runtime.CONTINUATION_PACKET_NAME]["payload"]["packets"]
    for packet in packets:
        if packet.get("packet_id") == "synthetic_packet_002":
            packet["consumed"] = False

    summary, findings = _validate_transport_inputs(inputs)

    assert summary["status"] == "blocked"
    assert "CONTINUATION_PACKET_ALREADY_CONSUMED" not in summary["error_codes"]
    assert {finding["error_code"] for finding in findings} >= {
        "CONTINUATION_PACKET_ALREADY_CONSUMED",
    }


def test_bridge_phase_continuity_resume_authority_rejection_moves_with_input() -> None:
    inputs = _mutated_transport_inputs()
    rows = inputs[bridge_runtime.HEARTBEAT_ROWS_NAME]["payload"]
    for row in rows:
        if row.get("heartbeat_id") == "heartbeat_claims_resume_authority":
            row["claims_resume_authority"] = False

    summary, findings = _validate_transport_inputs(inputs)

    assert summary["status"] == "blocked"
    assert "HEARTBEAT_NOT_RESUME_AUTHORITY" not in summary["error_codes"]
    assert {finding["error_code"] for finding in findings} >= {
        "HEARTBEAT_NOT_RESUME_AUTHORITY",
    }


def test_bridge_phase_continuity_valid_job_requires_matching_fresh_heartbeat() -> None:
    inputs = _mutated_transport_inputs()
    rows = inputs[bridge_runtime.HEARTBEAT_ROWS_NAME]["payload"]
    for row in rows:
        if row.get("heartbeat_id") == "heartbeat_fresh":
            row["job_id"] = "synthetic_detached_job_other"

    summary, findings = _validate_transport_inputs(inputs)

    assert summary["status"] == "blocked"
    assert summary["valid_job"]["status"] == "blocked"
    assert summary["valid_job"]["fresh_heartbeat_present"] is False
    invalid_findings = [
        finding
        for finding in findings
        if finding["error_code"]
        == "BRIDGE_CONTINUITY_SYNTHETIC_TRANSPORT_VALID_JOB_INVALID"
    ]
    assert invalid_findings == [
        {
            "error_code": "BRIDGE_CONTINUITY_SYNTHETIC_TRANSPORT_VALID_JOB_INVALID",
            "body_redacted": True,
            "fresh_heartbeat_present": False,
            "phase_match": True,
            "continuity_match": True,
        }
    ]


def test_bridge_phase_continuity_resume_authority_rejection_is_not_id_keyed() -> None:
    inputs = _mutated_transport_inputs()
    rows = inputs[bridge_runtime.HEARTBEAT_ROWS_NAME]["payload"]
    for row in rows:
        if row.get("heartbeat_id") == "heartbeat_claims_resume_authority":
            row["heartbeat_id"] = "renamed_fresh_resume_authority_claim"

    summary, findings = _validate_transport_inputs(inputs)

    assert summary["status"] == "pass"
    assert findings == []
    assert summary["heartbeat_resume_authority_rejected"] is True
    assert "HEARTBEAT_NOT_RESUME_AUTHORITY" in summary["error_codes"]


def test_bridge_phase_continuity_phase_mismatch_rejection_moves_with_input() -> None:
    inputs = _mutated_transport_inputs()
    jobs = inputs[bridge_runtime.DETACHED_JOB_NAME]["payload"]["jobs"]
    packets = inputs[bridge_runtime.CONTINUATION_PACKET_NAME]["payload"]["packets"]
    rows = inputs[bridge_runtime.HEARTBEAT_ROWS_NAME]["payload"]
    for job in jobs:
        if job.get("job_id") == "synthetic_detached_job_001":
            job["phase_id"] = "09_54_1"
    for packet in packets:
        if packet.get("packet_id") == "synthetic_packet_001":
            packet["phase_id"] = "09_54_1"
    for row in rows:
        if row.get("heartbeat_id") == "heartbeat_fresh":
            row["heartbeat_id"] = "renamed_good_heartbeat"
            row["phase_id"] = "09_54_2"

    summary, findings = _validate_transport_inputs(inputs)

    assert summary["status"] == "blocked"
    assert summary["valid_job"]["status"] == "blocked"
    assert summary["phase_mismatch_rejected"] is True
    assert "BRIDGE_CONTINUITY_PHASE_MISMATCH" in summary["error_codes"]
    assert "BRIDGE_CONTINUITY_PHASE_MISMATCH" in {
        finding["error_code"] for finding in findings
    }

    for row in rows:
        if row.get("heartbeat_id") == "renamed_good_heartbeat":
            row["phase_id"] = "09_54_1"

    summary, findings = _validate_transport_inputs(inputs)

    assert summary["status"] == "pass"
    assert findings == []
    assert summary["phase_mismatch_rejected"] is False
    assert "BRIDGE_CONTINUITY_PHASE_MISMATCH" not in summary["error_codes"]


def test_bridge_phase_continuity_continuity_ref_conflict_moves_with_input() -> None:
    inputs = _mutated_transport_inputs()
    jobs = inputs[bridge_runtime.DETACHED_JOB_NAME]["payload"]["jobs"]
    packets = inputs[bridge_runtime.CONTINUATION_PACKET_NAME]["payload"]["packets"]
    rows = inputs[bridge_runtime.HEARTBEAT_ROWS_NAME]["payload"]
    for job in jobs:
        if job.get("job_id") == "synthetic_detached_job_001":
            job["continuity_ref"] = "continuity_A"
            job["continuity_epoch"] = 1
    for packet in packets:
        if packet.get("packet_id") == "synthetic_packet_001":
            packet["continuity_ref"] = "continuity_A"
            packet["continuity_epoch"] = 1
    for row in rows:
        if row.get("heartbeat_id") == "heartbeat_fresh":
            row["continuity_ref"] = "continuity_B"
            row["continuity_epoch"] = 2

    summary, findings = _validate_transport_inputs(inputs)

    assert summary["status"] == "blocked"
    assert summary["valid_job"]["status"] == "blocked"
    assert summary["continuity_conflict_rejected"] is True
    assert "BRIDGE_CONTINUITY_CONFLICTING_CONTINUITY_REF" in summary["error_codes"]
    assert "BRIDGE_CONTINUITY_CONFLICTING_CONTINUITY_REF" in {
        finding["error_code"] for finding in findings
    }

    for row in rows:
        if row.get("heartbeat_id") == "heartbeat_fresh":
            row["continuity_ref"] = "continuity_A"
            row["continuity_epoch"] = 1

    summary, findings = _validate_transport_inputs(inputs)

    assert summary["status"] == "pass"
    assert findings == []
    assert summary["valid_job"]["continuity_match"] is True
    assert summary["continuity_conflict_rejected"] is False
    assert "BRIDGE_CONTINUITY_CONFLICTING_CONTINUITY_REF" not in summary["error_codes"]


def test_bridge_phase_continuity_claim_ref_conflict_rejection_moves_with_input() -> None:
    inputs = _mutated_transport_inputs()
    packets = inputs[bridge_runtime.CONTINUATION_PACKET_NAME]["payload"]["packets"]
    for packet in packets:
        if packet.get("packet_id") == "synthetic_packet_001":
            packet["claim_ref"] = "claim_synthetic_conflict"

    summary, findings = _validate_transport_inputs(inputs)

    assert summary["status"] == "blocked"
    assert summary["valid_job"]["status"] == "blocked"
    assert summary["claim_ref_conflict_rejected"] is True
    assert "BRIDGE_CONTINUITY_CLAIM_REF_CONFLICT" in {
        finding["error_code"] for finding in findings
    }
    assert "BRIDGE_CONTINUITY_SYNTHETIC_TRANSPORT_VALID_JOB_INVALID" in {
        finding["error_code"] for finding in findings
    }
    conflict_findings = [
        finding
        for finding in findings
        if finding["error_code"] == "BRIDGE_CONTINUITY_CLAIM_REF_CONFLICT"
    ]
    assert conflict_findings == [
        {
            "error_code": "BRIDGE_CONTINUITY_CLAIM_REF_CONFLICT",
            "body_redacted": True,
            "conflict_count": 1,
        }
    ]


def test_bridge_phase_continuity_accepts_legacy_fixture_label_as_compatibility_alias() -> None:
    findings: list[dict[str, Any]] = []
    summary = bridge_runtime._validate_synthetic_transport_contract(
        _transport_inputs_with_label("fake_transport"),
        findings=findings,
    )
    public_summary = bridge_runtime._synthetic_transport_fixture_summary(summary)

    assert summary["status"] == "pass"
    assert findings == []
    assert public_summary["transport_label"] == "synthetic_transport"
    assert public_summary["valid_job"]["transport"] == "synthetic_transport"
    assert public_summary["legacy_fixture_transport_label_exported"] is False


def test_bridge_phase_continuity_runner_consumes_synthetic_fixture_files_as_synthetic_transport(
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "bridge_phase_continuity_runtime"
    result = bridge_runtime.run(FIXTURE_INPUT, out_dir, command="pytest bridge continuity")
    public_summary = result["synthetic_transport_fixture_summary"]

    assert "fake_transport_fixture_summary" not in result
    assert public_summary["status"] == "pass"
    assert public_summary["input_file_count"] == 6
    assert public_summary["detached_job_count"] == 4
    assert public_summary["continuation_packet_count"] == 3
    assert public_summary["heartbeat_row_count"] == 3
    assert public_summary["resource_pressure_row_count"] == 2
    assert public_summary["worker_skip_receipt_count"] == 1
    assert public_summary["valid_job"] == {
        "status": "pass",
        "job_id": "synthetic_detached_job_001",
        "packet_id": "synthetic_packet_001",
        "transport": "synthetic_transport",
    }
    assert public_summary["transport_label"] == "synthetic_transport"
    assert public_summary["legacy_fixture_transport_label_exported"] is False
    assert "findings" not in public_summary
    assert public_summary["missing_packet_rejected"] is True
    assert public_summary["missing_required_fields_rejected"] is True
    assert public_summary["duplicate_resume_rejected"] is True
    assert public_summary["heartbeat_fresh_count"] == 2
    assert public_summary["heartbeat_stale_count"] == 1
    assert public_summary["heartbeat_resume_authority_rejected"] is True
    assert public_summary["stale_heartbeat_rejected"] is True
    assert public_summary["resource_pressure_blocked"] is True
    assert public_summary["worker_skip_deduped_no_closeout"] is True
    assert public_summary["forbidden_class_ids_only"] is True
    assert set(public_summary["error_codes"]) >= {
        "CONTINUATION_PACKET_ALREADY_CONSUMED",
        "HEARTBEAT_NOT_RESUME_AUTHORITY",
        "MISSING_CONTINUATION_PACKET",
        "MISSING_CONTINUATION_PACKET_FIELDS",
        "RESOURCE_PRESSURE_DISPATCH_BLOCKED",
        "STALE_HEARTBEAT_LIVENESS_CLAIM",
    }

    continuation = _load_json(out_dir / "continuation_packet.json")
    heartbeat = _load_json(out_dir / "heartbeat.json")
    pressure = _load_json(out_dir / "resource_pressure.json")
    closeout = _load_json(out_dir / "closeout_transition.json")

    assert "fake_transport_fixture_summary" not in continuation
    assert "fake_transport_job_id" not in continuation["continuation_packet_status"]
    assert "fake_transport_packet_id" not in continuation["continuation_packet_status"]
    assert continuation["continuation_packet_status"]["synthetic_transport_job_id"] == (
        "synthetic_detached_job_001"
    )
    assert continuation["continuation_packet_status"][
        "synthetic_transport_packet_id"
    ] == "synthetic_packet_001"
    assert continuation["continuation_packet_status"]["missing_packet_rejected"] is True
    assert continuation["continuation_packet_status"][
        "missing_required_fields_rejected"
    ] is True
    assert heartbeat["heartbeat_status"]["fresh_count"] == 2
    assert heartbeat["heartbeat_status"]["stale_count"] == 1
    assert pressure["resource_pressure_decision"]["blocked_reason"] == (
        "capacity_budget_exceeded"
    )
    assert closeout["worker_skip_receipt_status"] == {
        "status": "pass",
        "claim_closeout_authorized": False,
        "deduped_noop_receipt": True,
    }


def test_bridge_phase_continuity_receipt_negative_cases_use_semantic_evidence(
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "bridge_phase_continuity_runtime"
    result = bridge_runtime.run(FIXTURE_INPUT, out_dir, command="pytest bridge continuity")

    observed = result["observed_negative_cases"]
    assert observed["stale_heartbeat_overclaims_liveness"] == {
        "status": "pass",
        "error_codes": ["STALE_HEARTBEAT_LIVENESS_CLAIM"],
        "evidence_source": "synthetic_transport_validator",
        "semantic_checks": {"stale_heartbeat_rejected": True},
        "body_redacted": True,
    }
    assert observed["apply_validation_failure_rolls_back_observe_promotion"] == {
        "status": "pass",
        "error_codes": ["OBSERVE_APPLY_VALIDATION_FAILED"],
        "evidence_source": "observe_apply_rollback_validator",
        "semantic_checks": {"rollback_validation_failure_rejected": True},
        "body_redacted": True,
    }
    assert {
        row["evidence_source"] for row in observed.values()
    } >= {
        "synthetic_transport_validator",
        "observe_apply_rollback_validator",
        "observe_apply_finalizer_validator",
        "public_boundary_and_private_state_scan",
    }
    assert "synthetic_fixture_expected_negative_cases" not in {
        row["evidence_source"] for row in observed.values()
    }


def test_bridge_phase_continuity_receipt_negative_cases_move_with_transport_input(
    tmp_path: Path,
) -> None:
    input_dir = _copy_fixture_input(tmp_path)
    rows_path = input_dir / bridge_runtime.HEARTBEAT_ROWS_NAME
    rows = [
        json.loads(line)
        for line in rows_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for row in rows:
        if row.get("heartbeat_id") == "heartbeat_stale":
            row["age_seconds"] = 12
            row["status"] = "alive"
            row["claims_live_bridge_health"] = False
    rows_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )

    result = bridge_runtime.run(
        input_dir,
        tmp_path / "bridge_phase_continuity_runtime",
        command="pytest bridge continuity mutated heartbeat",
    )

    observed = result["observed_negative_cases"]["stale_heartbeat_overclaims_liveness"]
    assert result["status"] == "blocked"
    assert "stale_heartbeat_overclaims_liveness" in result["missing_negative_cases"]
    assert observed == {
        "status": "blocked",
        "error_codes": [],
        "evidence_source": "synthetic_transport_validator",
        "semantic_checks": {"stale_heartbeat_rejected": False},
        "body_redacted": True,
    }
    assert "STALE_HEARTBEAT_LIVENESS_CLAIM" not in result["error_codes"]
    assert "STALE_HEARTBEAT_LIVENESS_CLAIM" in {
        finding["error_code"] for finding in result["findings"]
    }


def test_bridge_phase_continuity_receipt_blocks_conflicting_claim_refs(
    tmp_path: Path,
) -> None:
    input_dir = _copy_fixture_input(tmp_path)
    packet_path = input_dir / bridge_runtime.CONTINUATION_PACKET_NAME
    payload = _load_json(packet_path)
    for packet in payload["packets"]:
        if packet.get("packet_id") == "synthetic_packet_001":
            packet["claim_ref"] = "claim_synthetic_conflict"
    packet_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    result = bridge_runtime.run(
        input_dir,
        tmp_path / "bridge_phase_continuity_runtime",
        command="pytest bridge continuity conflicting claim ref",
    )

    assert result["status"] == "blocked"
    assert result["synthetic_transport_fixture_summary"][
        "claim_ref_conflict_rejected"
    ] is True
    assert "BRIDGE_CONTINUITY_CLAIM_REF_CONFLICT" in {
        finding["error_code"] for finding in result["findings"]
    }
    assert "BRIDGE_CONTINUITY_SYNTHETIC_TRANSPORT_VALID_JOB_INVALID" in {
        finding["error_code"] for finding in result["findings"]
    }


def test_bridge_phase_continuity_receipt_negative_cases_move_with_rollback_input(
    tmp_path: Path,
) -> None:
    input_dir = _copy_fixture_input(tmp_path)
    fixture_path = input_dir / bridge_runtime.INPUT_NAME
    fixture = _load_json(fixture_path)
    rollback = fixture["synthetic_observe_apply_session"][
        "rollback_on_validation_failure"
    ]
    rollback["validation_status"] = "pass"
    rollback["rollback_required"] = False
    rollback["writes_allowed_after_failure"] = True
    fixture_path.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")

    result = bridge_runtime.run(
        input_dir,
        tmp_path / "bridge_phase_continuity_runtime",
        command="pytest bridge continuity mutated rollback",
    )

    case_id = "apply_validation_failure_rolls_back_observe_promotion"
    observed = result["observed_negative_cases"][case_id]
    assert result["status"] == "blocked"
    assert case_id in result["missing_negative_cases"]
    assert observed == {
        "status": "blocked",
        "error_codes": [],
        "evidence_source": "observe_apply_rollback_validator",
        "semantic_checks": {"rollback_validation_failure_rejected": False},
        "body_redacted": True,
    }
    assert "OBSERVE_APPLY_VALIDATION_FAILED" not in result["error_codes"]
    assert "BRIDGE_CONTINUITY_ROLLBACK_CASE_MISSING" in {
        finding["error_code"] for finding in result["findings"]
    }


def test_bridge_phase_continuity_receipts_stay_public_safe(tmp_path: Path) -> None:
    out_dir = tmp_path / "bridge_phase_continuity_runtime"
    bridge_runtime.run(FIXTURE_INPUT, out_dir, command="pytest bridge continuity")

    serialized = "\n".join(
        (out_dir / Path(receipt_rel).name).read_text(encoding="utf-8")
        for receipt_rel in bridge_runtime.EXPECTED_RECEIPT_PATHS
    )
    keys = _walk_keys(json.loads((out_dir / "closeout_transition.json").read_text(encoding="utf-8")))

    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "matched_excerpt" not in serialized
    assert "provider_response_json" not in serialized
    assert "operator_thread_text" not in serialized
    assert "browser_storage_snapshot" not in serialized
    assert "body" not in keys
    assert "matched_excerpt" not in keys


def test_bridge_phase_continuity_cli_route_runs(tmp_path: Path) -> None:
    out_dir = tmp_path / "cli_receipts"
    exit_code = cli.main(
        [
            "bridge-phase-continuity-runtime",
            "run",
            "--input",
            FIXTURE_INPUT.as_posix(),
            "--out",
            out_dir.as_posix(),
        ]
    )

    assert exit_code == 0
    assert (out_dir / "continuation_packet.json").is_file()
    assert (out_dir / "heartbeat.json").is_file()
    assert (out_dir / "resource_pressure.json").is_file()
    assert (out_dir / "resume_receipt.json").is_file()
    assert (out_dir / "closeout_transition.json").is_file()


def test_bridge_phase_continuity_card_stdout_is_compact_and_keeps_full_receipts(
    tmp_path: Path,
    capsys: Any,
) -> None:
    out_dir = tmp_path / "card_receipts"

    exit_code = bridge_runtime.main(
        [
            "run",
            "--input",
            FIXTURE_INPUT.as_posix(),
            "--out",
            out_dir.as_posix(),
            "--card",
        ]
    )

    captured = capsys.readouterr().out
    card = json.loads(captured)
    full_receipt = _load_json(out_dir / "closeout_transition.json")

    assert exit_code == 0
    assert len(captured.encode("utf-8")) < 6000
    assert card["schema_version"] == "bridge_phase_continuity_runtime_command_card_v2"
    assert card["status"] == "pass"
    assert card["organ_id"] == bridge_runtime.ORGAN_ID
    assert card["fixture_id"] == bridge_runtime.FIXTURE_ID
    assert card["receipt_summary"]["written_receipt_count"] == 5
    assert card["receipt_summary"]["receipt_write_status"] == "writes_allowed"
    assert card["receipt_summary"]["receipt_write_skipped_count"] == 0
    assert card["receipt_summary"]["receipt_count"] == len(bridge_runtime.EXPECTED_RECEIPT_PATHS)
    assert card["receipt_summary"]["receipt_paths_exported"] is False
    assert card["bridge_continuity_summary"]["heartbeat_fresh_count"] == 2
    assert card["bridge_continuity_summary"]["heartbeat_stale_count"] == 1
    assert card["bridge_continuity_summary"]["resource_pressure_blocked"] is True
    assert card["bridge_continuity_summary"]["resource_dispatch_allowed"] is False
    assert card["bridge_continuity_summary"]["worker_skip_deduped_no_closeout"] is True
    assert card["synthetic_transport_summary"]["input_file_count"] == 6
    assert card["synthetic_transport_summary"]["transport_label"] == (
        "synthetic_transport"
    )
    assert card["synthetic_transport_summary"]["manifest_input_refs_exported"] is False
    assert card["negative_case_coverage"]["expected_case_count"] == len(
        bridge_runtime.EXPECTED_NEGATIVE_CASES
    )
    assert card["negative_case_coverage"]["observed_case_count"] == len(
        bridge_runtime.EXPECTED_NEGATIVE_CASES
    )
    assert card["negative_case_coverage"]["missing_negative_cases"] == []
    assert card["private_state_scan_summary"]["blocking_hit_count"] == 0
    assert card["private_state_scan_summary"]["hits_exported"] is False
    assert card["authority_ceiling"]["live_bridge_transport_authorized"] is False
    assert card["no_export_guards"]["source_module_digest_results_exported"] is False

    card_keys = set(_walk_keys(card))
    assert "findings" not in card_keys
    assert "observed_negative_cases" not in card_keys
    assert "source_pattern_ids" not in card_keys
    assert "source_module_digest_results" not in card_keys
    assert "synthetic_input_refs" not in card_keys
    assert "fake_transport_summary" not in card_keys
    assert "receipt_paths" not in card_keys
    assert "receipt_path_map" not in card_keys
    assert "anti_claim" not in card_keys
    assert "hits" not in card_keys
    assert "scan_scope" not in card_keys

    assert full_receipt["status"] == "pass"
    assert "fake_transport_fixture_summary" not in full_receipt
    assert full_receipt["synthetic_transport_fixture_summary"]["status"] == "pass"
    assert full_receipt["receipt_paths"] == bridge_runtime.EXPECTED_RECEIPT_PATHS
    assert len(full_receipt["source_module_digest_results"]) == 5
    assert full_receipt["command"].endswith("--card")
