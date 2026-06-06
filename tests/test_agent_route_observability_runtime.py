from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from microcosm_core.macro_tools import agent_observability_store, agent_trace_route_repair
from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_computer_use_trace,
)
from microcosm_core.macro_tools.agent_trace_route_repair import (
    SCHEMA_VERSION as AGENT_TRACE_ROUTE_REPAIR_SCHEMA_VERSION,
    build_public_agent_trace_route_repair_view,
    load_public_agent_trace_route_repair_bundle,
    route_repair_for,
)
from microcosm_core.macro_tools.agent_observability_store import (
    SCHEMA_VERSION as AGENT_OBSERVABILITY_STORE_SCHEMA_VERSION,
    AgentTraceStore,
    build_public_agent_observability_store_view,
    load_public_agent_observability_store_bundle,
)
from microcosm_core.macro_tools.agent_session_attribution import (
    SCHEMA_VERSION as SESSION_ATTRIBUTION_SCHEMA_VERSION,
    attribute_sessions,
)
from microcosm_core.macro_tools.bridge_resume import (
    SCHEMA_VERSION as BRIDGE_DISPATCH_YIELD_RESUME_SCHEMA_VERSION,
    SOURCE_REF as BRIDGE_DISPATCH_YIELD_RESUME_SOURCE_REF,
    TARGET_REF as BRIDGE_DISPATCH_YIELD_RESUME_TARGET_REF,
    build_public_bridge_dispatch_yield_resume_view,
    load_public_bridge_dispatch_yield_resume_bundle,
)
from microcosm_core.macro_tools.continuation_packet import (
    SCHEMA_VERSION as CONTINUATION_PACKET_SCHEMA_VERSION,
    build_public_continuation_packet,
)
from microcosm_core.macro_tools.controller_heartbeat import (
    CONTROLLER_HEARTBEAT_FIELDS,
    CONTROLLER_HEARTBEAT_SCHEMA_VERSION,
    build_public_controller_heartbeat_view,
    count_sentences,
    load_public_controller_heartbeat_bundle,
)
from microcosm_core.organs import agent_route_observability_runtime
from microcosm_core.organs.agent_route_observability_runtime import (
    COMPUTER_USE_EXPECTED_NEGATIVE_CASES,
    EXPORTED_COMPUTER_USE_ACTION_TRACE_BUNDLE_RECEIPT_PATH,
    EXPORTED_BRIDGE_DISPATCH_YIELD_RESUME_BUNDLE_RECEIPT_PATH,
    EXPORTED_CONTROLLER_HEARTBEAT_BUNDLE_RECEIPT_PATH,
    EXPORTED_AGENT_TRACE_ROUTE_REPAIR_BUNDLE_RECEIPT_PATH,
    EXPORTED_AGENT_OBSERVABILITY_STORE_BUNDLE_RECEIPT_PATH,
    EXPORTED_MULTI_AGENT_FANIN_BUNDLE_RECEIPT_PATH,
    EXPORTED_OBSERVABILITY_BUNDLE_RECEIPT_PATH,
    EXPORTED_ROUTE_COMPLIANCE_AUDIT_BUNDLE_RECEIPT_PATH,
    EXPORTED_SESSION_ATTRIBUTION_BUNDLE_RECEIPT_PATH,
    EXPORTED_HARNESS_CONFIGURATION_AUDIT_BUNDLE_RECEIPT_PATH,
    EXPECTED_NEGATIVE_CASES,
    EXPECTED_RECEIPT_PATHS,
    OBSERVABILITY_CARD_SCHEMA_VERSION,
    main,
    result_card,
    run,
    run_bridge_dispatch_yield_resume_bundle,
    run_computer_use_action_trace_bundle,
    run_controller_heartbeat_bundle,
    run_agent_trace_route_repair_bundle,
    run_agent_observability_store_bundle,
    run_multi_agent_fanin_bundle,
    run_observability_bundle,
    run_route_compliance_audit_bundle,
    run_session_attribution_bundle,
    run_harness_configuration_audit_bundle,
)
from microcosm_core.schemas import DuplicateJsonKeyError


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MICROCOSM_ROOT.parent
OBS_FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime/input"
OBS_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/exported_observability_bundle"
)
ROUTE_COMPLIANCE_AUDIT_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_route_compliance_audit_bundle"
)
COMPUTER_USE_FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/agent_route_observability_runtime/"
    "computer_use_action_trace_replay_input"
)
COMPUTER_USE_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_computer_use_action_trace_bundle"
)
SESSION_ATTRIBUTION_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_session_attribution_bundle"
)
HARNESS_CONFIGURATION_AUDIT_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_harness_configuration_audit_bundle"
)
MULTI_AGENT_FANIN_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_multi_agent_fanin_replay_bundle"
)
BRIDGE_DISPATCH_YIELD_RESUME_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_bridge_dispatch_yield_resume_bundle"
)
CONTROLLER_HEARTBEAT_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_controller_heartbeat_bundle"
)
AGENT_TRACE_ROUTE_REPAIR_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_agent_trace_route_repair_bundle"
)
AGENT_OBSERVABILITY_STORE_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/agent_route_observability_runtime/"
    "exported_agent_observability_store_bundle"
)
AGENT_ROUTE_OBSERVABILITY_EXAMPLES_ROOT = (
    MICROCOSM_ROOT / "examples/agent_route_observability_runtime"
)
SOURCE_MODULE_VALIDATION_REF_PREFIX = (
    "microcosm-substrate/tests/test_agent_route_observability_runtime.py::"
)


def _sanitized_structurer_clip_from_commands(
    commands: list[str],
    *,
    schema_version: str = "agent_trace_lossless_clip_v2",
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "source_integrity": {
            "exact_source_text_in_attachment": False,
            "source_text_attachment_field": "omitted_for_public_route_analytics",
        },
        "command_ledger": {
            "schema_version": "agent_trace_command_ledger_v1",
            "records": [
                {
                    "id": f"cmd_{index + 1:04d}",
                    "command": command,
                    "normalized_command": command,
                    "source_line_range": {"start": (index * 4) + 1, "end": (index * 4) + 1},
                    "command_line_range": {"start": (index * 4) + 2, "end": (index * 4) + 2},
                    "output_line_count": 12 if "kernel.py" in command else 3,
                    "output_char_count": 512 if "kernel.py" in command else 128,
                }
                for index, command in enumerate(commands)
            ],
        },
    }


def _replace_trace_analytics_session_with_structurer_clip(
    bundle: Path,
    *,
    session_id: str,
    commands: list[str],
) -> dict[str, Any]:
    trace_path = bundle / "trace_analytics_spans.json"
    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    session = next(
        row for row in trace_payload["sessions"] if row["session_id"] == session_id
    )
    session.pop("spans", None)
    session["agent_trace_structurer_clip"] = _sanitized_structurer_clip_from_commands(
        commands
    )
    trace_path.write_text(
        json.dumps(trace_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return session


def _replace_trace_analytics_session(
    bundle: Path,
    *,
    original_session_id: str,
    replacement: dict[str, Any],
) -> None:
    trace_path = bundle / "trace_analytics_spans.json"
    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    trace_payload["sessions"] = [
        replacement if row.get("session_id") == original_session_id else row
        for row in trace_payload["sessions"]
    ]
    trace_path.write_text(
        json.dumps(trace_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _copy_primary_fixture_with_route_analytics(public_root: Path) -> Path:
    fixture = public_root / "fixtures/first_wave/agent_route_observability_runtime"
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        fixture,
    )
    input_dir = fixture / "input"
    shutil.copytree(
        ROUTE_COMPLIANCE_AUDIT_BUNDLE_INPUT / "source_modules",
        input_dir / "source_modules",
    )
    shutil.copy2(
        ROUTE_COMPLIANCE_AUDIT_BUNDLE_INPUT / "trace_analytics_spans.json",
        input_dir / "trace_analytics_spans.json",
    )
    shutil.copy2(
        ROUTE_COMPLIANCE_AUDIT_BUNDLE_INPUT / "source_module_manifest.json",
        input_dir / "source_module_manifest.json",
    )
    return fixture


def _find_live_trace_session(
    pattern_id: str,
    *,
    agent: str | None = None,
) -> tuple[dict[str, Any], str, str]:
    patterns = json.loads((REPO_ROOT / "codex/hologram/process/patterns.json").read_text())
    live_ledger_session_ids = {
        row["session_id"]
        for row in json.loads((REPO_ROOT / "codex/hologram/process/ledger.json").read_text())[
            "sessions"
        ]
    }
    row = next(
        item for item in patterns["patterns"] if item["pattern_id"] == pattern_id
    )
    session_ids = [
        session_id
        for session_id in row.get("session_id_hits") or []
        if session_id in live_ledger_session_ids
    ]
    state_dirs = sorted((REPO_ROOT / "state/agent_telemetry/process").iterdir(), reverse=True)
    for session_id in session_ids:
        for state_dir in state_dirs:
            sessions_path = state_dir / "sessions.jsonl"
            spans_path = state_dir / "spans.jsonl"
            if not sessions_path.is_file() or not spans_path.is_file():
                continue
            session_rows = [
                json.loads(line)
                for line in sessions_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            session_row = next(
                (
                    candidate
                    for candidate in session_rows
                    if candidate.get("session_id") == session_id
                    and (agent is None or candidate.get("agent") == agent)
                ),
                None,
            )
            if session_row is None:
                continue
            span_count = sum(
                1
                for line in spans_path.read_text(encoding="utf-8").splitlines()
                if line.strip() and json.loads(line).get("session_id") == session_id
            )
            if span_count:
                return (
                    session_row,
                    sessions_path.relative_to(REPO_ROOT).as_posix(),
                    spans_path.relative_to(REPO_ROOT).as_posix(),
                )
    raise AssertionError(f"No live trace session found for pattern {pattern_id!r}")


def _build_real_trace_session_entry(
    pattern_id: str,
    *,
    agent: str | None = None,
    expected: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    session_row, sessions_ref, spans_ref = _find_live_trace_session(
        pattern_id,
        agent=agent,
    )
    claim = agent_route_observability_runtime._real_trace_route_state_claim(session_row)
    session = {
        "session_id": session_row["session_id"],
        "started_at": session_row["started_at"],
        "ended_at": session_row["ended_at"],
        "expected": expected
        or {
            "route_compliance_score": claim["route_compliance_score"],
            "required_anti_patterns": claim["anti_pattern_ids"],
            "required_mode_signals": claim["route_lease_mode_signals"],
        },
        "real_trace_receipt": {
            "schema_version": (
                agent_route_observability_runtime.REAL_TRACE_RECEIPT_SCHEMA_VERSION
            ),
            "ledger_ref": "codex/hologram/process/ledger.json",
            "sessions_ref": sessions_ref,
            "spans_ref": spans_ref,
            "route_state_claim": claim,
            "route_state_fingerprint": agent_route_observability_runtime._stable_hash(
                claim
            ),
        },
    }
    return session, claim


def test_route_observability_paper_module_carries_source_backed_packet() -> None:
    paper_module = (
        MICROCOSM_ROOT / "paper_modules/agent_route_observability_runtime.md"
    ).read_text(encoding="utf-8")
    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_agent_route_observability_runtime.json"
        ).read_text(encoding="utf-8")
    )
    registry = json.loads(
        (MICROCOSM_ROOT / "core/organ_registry.json").read_text(encoding="utf-8")
    )
    organ = next(
        row
        for row in registry["implemented_organs"]
        if row["organ_id"] == "agent_route_observability_runtime"
    )

    assert "## Source-Backed Doctrine Packet" in paper_module
    assert organ["evidence_class"] in paper_module
    assert organ["claim_ceiling"] in paper_module
    assert organ["validator_command"] in paper_module
    assert standard["authority_boundary"] in paper_module
    assert "does not inspect live sessions" in paper_module
    assert "body_in_receipt=false" in paper_module

    required_refs = [
        "core/organ_registry.json::implemented_organs[organ_id=agent_route_observability_runtime]",
        "core/organ_evidence_classes.json::organ_evidence_classes[agent_route_observability_runtime]",
        "standards/std_microcosm_agent_route_observability_runtime.json",
        "src/microcosm_core/organs/agent_route_observability_runtime.py",
        "examples/macro_projection_import_protocol/exported_projection_import_bundle/agent_execution_trace_source_module_manifest.json",
        "examples/macro_projection_import_protocol/exported_projection_import_bundle/agent_observability_source_module_manifest.json",
        "examples/agent_route_observability_runtime/exported_observability_bundle/source_module_manifest.json",
        "tests/test_macro_projection_import_protocol.py::test_agent_execution_trace_body_import_is_unified_under_macro_projection_spine",
    ]
    for ref in required_refs:
        assert ref in paper_module

    for receipt_ref in organ["generated_receipts"]:
        assert receipt_ref in paper_module

    for phrase in [
        "actor-axis mismatch",
        "missing route lease",
        "private transcript body",
        "duplicate trace id",
        "route-compliance overclaim",
        "hook-shadow budget overrun",
        "Re-entry conditions",
    ]:
        assert phrase in paper_module


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


def _field_floor() -> dict[str, list[str]]:
    manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "core/fixture_manifests/agent_route_observability_runtime.fixture_manifest.json"
        ).read_text(encoding="utf-8")
    )
    return manifest["validator_contract_ratchet_v1"]["per_output_receipt_field_floor"]


def test_route_observability_trace_loader_streams_jsonl_without_materializing_file(
    tmp_path: Path, monkeypatch
) -> None:
    trace_path = tmp_path / "agent_trace.jsonl"
    trace_path.write_text(
        '{"trace_id":"trace_001","route_id":"entry"}\n'
        "\n"
        '{"trace_id":"trace_002","route_id":"context_pack"}\n',
        encoding="utf-8",
    )
    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self == trace_path:
            raise AssertionError("route observability JSONL loader should stream rows")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    assert agent_route_observability_runtime._load_jsonl(trace_path) == [
        {"trace_id": "trace_001", "route_id": "entry"},
        {"trace_id": "trace_002", "route_id": "context_pack"},
    ]


def test_route_observability_trace_loader_rejects_duplicate_jsonl_keys(
    tmp_path: Path,
) -> None:
    trace_path = tmp_path / "agent_trace.jsonl"
    trace_path.write_text(
        '{"trace_id":"trace_001","trace_id":"trace_002","route_id":"entry"}\n',
        encoding="utf-8",
    )

    with pytest.raises(DuplicateJsonKeyError) as excinfo:
        agent_route_observability_runtime._load_jsonl(trace_path)

    assert f"{trace_path}:1" in str(excinfo.value)


def test_route_observability_source_line_count_streams_without_materializing_file(
    tmp_path: Path, monkeypatch
) -> None:
    source_path = tmp_path / "source.py"
    empty_source_path = tmp_path / "empty.py"
    source_path.write_text("alpha\n\nomega\n", encoding="utf-8")
    empty_source_path.write_text("", encoding="utf-8")
    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self in (source_path, empty_source_path):
            raise AssertionError("source line counting should stream rows")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    assert agent_route_observability_runtime._source_line_count(source_path) == 3
    assert agent_route_observability_runtime._source_line_count(empty_source_path) == 1


def test_route_observability_digest_helpers_stream_without_read_bytes(
    tmp_path: Path, monkeypatch
) -> None:
    source_path = tmp_path / "source.py"
    source_bytes = b"alpha\nomega\n"
    source_path.write_bytes(source_bytes)
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(self: Path, *args: Any, **kwargs: Any) -> bytes:
        if self == source_path:
            raise AssertionError("observability digest helpers should stream bytes")
        return original_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    expected_digest = hashlib.sha256(source_bytes).hexdigest()
    assert agent_route_observability_runtime._sha256_ref(source_path) == (
        f"sha256:{expected_digest}"
    )
    assert agent_route_observability_runtime._file_sha256(source_path) == expected_digest
    assert agent_route_observability_runtime._file_size_bytes(source_path) == len(
        source_bytes
    )
    assert agent_observability_store._file_sha256(source_path) == (
        f"sha256:{expected_digest}"
    )


def test_agent_route_observability_source_module_manifests_make_body_copy_contract_explicit() -> None:
    manifests = sorted(
        AGENT_ROUTE_OBSERVABILITY_EXAMPLES_ROOT.glob("*/source_module_manifest.json")
    )

    assert len(manifests) == 10
    module_count = 0
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        is_route_compliance_manifest = (
            manifest_path.parent.name == "exported_route_compliance_audit_bundle"
        )
        if is_route_compliance_manifest:
            assert manifest["source_import_class"] == (
                agent_route_observability_runtime.ROUTE_COMPLIANCE_AUDIT_MIXED_SOURCE_IMPORT_CLASS
            )
            assert manifest["body_copied_material_count"] == (
                len(agent_route_observability_runtime.ROUTE_COMPLIANCE_AUDIT_EXACT_SOURCE_MODULE_PATHS)
            )
            assert manifest["public_reference_sanitized_material_count"] == 1
        else:
            assert manifest["source_import_class"] == "copied_non_secret_macro_body"
            assert manifest["body_copied_material_count"] == len(manifest["modules"])
        assert manifest["body_in_receipt"] is False
        for row in manifest["modules"]:
            module_count += 1
            digest = str(row["sha256"]).removeprefix("sha256:")
            expected_digest = f"sha256:{digest}"
            target_ref = str(row["target_ref"]).removeprefix("microcosm-substrate/")
            target_path = MICROCOSM_ROOT / target_ref
            actual_digest = f"sha256:{hashlib.sha256(target_path.read_bytes()).hexdigest()}"
            is_sanitized_row = (
                is_route_compliance_manifest
                and row["path"]
                == agent_route_observability_runtime.ROUTE_COMPLIANCE_AUDIT_SANITIZED_SOURCE_MODULE_PATH
            )

            if is_sanitized_row:
                assert row["source_import_class"] == (
                    agent_route_observability_runtime.ROUTE_COMPLIANCE_AUDIT_SANITIZED_SOURCE_IMPORT_CLASS
                )
                assert row["source_to_target_relation"] == (
                    agent_route_observability_runtime.ROUTE_COMPLIANCE_AUDIT_SANITIZED_SOURCE_RELATION
                )
                assert row["public_reference_sanitized"] is True
                assert row["body_copied"] is False
                assert row["source_sha256"] != expected_digest
                assert row["target_sha256"] == expected_digest
                assert row["sha256_match"] is False
                assert row["sanitization_receipt"]["status"] == "transformed"
                assert row["sanitization_receipt"]["public_safe"] is True
                assert row["sanitization_receipt"]["blocker_count"] == 0
                assert row["sanitization_receipt"]["target_sha256"] == expected_digest
            else:
                assert row["source_import_class"] == "copied_non_secret_macro_body"
                if is_route_compliance_manifest:
                    assert row["source_to_target_relation"] == "exact_copy"
                assert row["body_copied"] is True
                assert row["source_sha256"] == expected_digest
                assert row["target_sha256"] == expected_digest
                assert row["sha256_match"] is True
            assert row["body_in_receipt"] is False
            assert row["body_text_in_receipt"] is False
            if is_sanitized_row:
                assert row["source_open_payload_boundary"].startswith(
                    "body_in_bundle_source_modules_public_reference_sanitized_not_receipt"
                )
            else:
                assert row["source_open_payload_boundary"].startswith(
                    "body_in_bundle_source_modules_not_receipt"
                )
            assert actual_digest == expected_digest
            assert row["anchor_count"] == len(row.get("required_anchors", []))
            assert row["validation_refs"]
            assert all(
                str(ref).startswith(SOURCE_MODULE_VALIDATION_REF_PREFIX)
                for ref in row["validation_refs"]
            )

    assert module_count == 31


def test_agent_trace_route_repair_body_verification_reports_source_and_target_digests() -> None:
    view = build_public_agent_trace_route_repair_view(
        load_public_agent_trace_route_repair_bundle(AGENT_TRACE_ROUTE_REPAIR_BUNDLE_INPUT)
    )
    verification = view["body_import_verification"]

    source_path = MICROCOSM_ROOT.parent / agent_trace_route_repair.SOURCE_REFS[0]
    target_path = MICROCOSM_ROOT / agent_trace_route_repair.TARGET_REF.removeprefix(
        "microcosm-substrate/"
    )
    source_digest = f"sha256:{hashlib.sha256(source_path.read_bytes()).hexdigest()}"
    target_digest = f"sha256:{hashlib.sha256(target_path.read_bytes()).hexdigest()}"

    assert verification["verification_status"] == "verified"
    assert verification["source_to_target_relation"] == "source_faithful_public_light_edit"
    assert verification["source_ref"] == agent_trace_route_repair.SOURCE_REFS[0]
    assert verification["target_ref"] == agent_trace_route_repair.TARGET_REF
    assert verification["source_body_digest"] == source_digest
    assert verification["target_body_digest"] == target_digest
    assert verification["body_in_receipt"] is False
    assert any(
        "validate-agent-trace-route-repair-bundle" in ref
        for ref in verification["runtime_consumed_by"]
    )


def test_agent_route_observability_runtime_observes_required_negative_cases(
    tmp_path: Path,
) -> None:
    live_receipt_dir = MICROCOSM_ROOT / "receipts/first_wave/agent_route_observability_runtime"
    before = {
        path.name: path.read_text(encoding="utf-8")
        for path in live_receipt_dir.glob("*.json")
    } if live_receipt_dir.exists() else {}
    result = run(OBS_FIXTURE_INPUT, tmp_path / "receipts", command="pytest")

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert all(not Path(path).is_absolute() for path in result["receipt_paths"])
    assert result["route_compliance"]["trace_count"] == 10
    assert result["route_compliance"]["actor_axis_mismatch_count"] == 1
    assert result["route_compliance"]["authority_rejection_count"] == 1
    assert result["route_compliance"]["route_miss_replacement_count"] == 1
    assert result["hook_shadow_coverage"]["hook_shadow_case_count"] == 6
    assert result["hook_shadow_coverage"]["hook_shadow_repair_class_count"] == 6
    assert result["hook_shadow_coverage"]["missing_authority_count"] == 1
    assert result["hook_shadow_coverage"]["banned_route_intervention_count"] == 1
    assert result["hook_shadow_coverage"]["command_displacement_count"] == 1
    assert result["hook_shadow_coverage"]["live_state_read_denial_count"] == 1
    assert result["hook_shadow_coverage"]["over_budget_denial_count"] == 1
    assert result["hook_shadow_coverage"]["missing_hook_shadow_negative_cases"] == []
    assert result["route_lease_mode_control"]["kernel_bloat_before_direct_action_count"] == 1
    assert result["route_lease_mode_control"]["static_metadata_without_trace_feedback_count"] == 1
    assert result["debt_retirement"]["debt_retirement_count"] == 1
    assert result["agent_principle_lens"]["agent_principle_lens_status"] == "pass"
    assert result["agent_principle_lens"]["selected_agent_principle_ids"] == [
        "pri_136",
        "pri_142",
        "pri_143",
        "pri_144",
    ]
    assert result["agent_principle_lens"]["compact_admission_receipt_count"] == 2
    assert result["agent_principle_lens"]["principles_minted"] is False
    assert result["agent_principle_lens"]["candidate_axiom_promoted"] is False
    assert result["egress_mirror"]["egress_mirror_status"] == "pass"
    assert result["egress_mirror"]["egress_case_count"] == 6
    assert result["egress_mirror"]["egress_violation_count"] == 3
    assert result["egress_mirror"]["egress_allowed_count"] == 3
    assert result["egress_mirror"]["private_state_read"] is False
    assert result["egress_mirror"]["provider_payload_read"] is False
    assert result["egress_mirror"]["browser_hud_cockpit_state_read"] is False
    assert result["primary_route_trace_analytics"]["status"] == "pass"
    assert result["primary_route_trace_analytics"]["source_bound_primary_run"] is True
    assert result["primary_route_trace_analytics"]["source_binding"] == (
        "exported_route_compliance_audit_bundle"
    )
    assert result["primary_route_source_manifest"]["status"] == "pass"
    assert result["primary_route_source_manifest"][
        "all_exact_live_source_digests_matched"
    ] is True
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]
    after = {
        path.name: path.read_text(encoding="utf-8")
        for path in live_receipt_dir.glob("*.json")
    } if live_receipt_dir.exists() else {}
    assert after == before


def test_agent_route_observability_primary_run_principle_lens_ignores_declared_compact_flags(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = public_root / "fixtures/first_wave/agent_route_observability_runtime"
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        fixture,
    )
    lens_path = fixture / "input/agent_principle_lens_receipt.json"
    payload = json.loads(lens_path.read_text(encoding="utf-8"))
    for row in payload["compact_admission_receipts"]:
        row["selected_ids_preserved"] = False
        row["runtime_doctrine_type_preserved"] = False
        row["all_agent_principles_route_preserved"] = False
        row["selected_principle_cards_route_preserved"] = False
        row["agent_operating_packet_route_preserved"] = False
    lens_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    decisions = result["agent_principle_lens"]["compact_admission_receipts"]
    assert result["status"] == "pass"
    assert all(row["decision"] == "accepted" for row in decisions)
    assert all(
        row["derived_from"] == "agent_principle_lens_route_and_authority_fields"
        for row in decisions
    )
    assert all(row["declared_selected_ids_preserved"] is False for row in decisions)


def test_agent_route_observability_primary_run_principle_lens_recomputes_missing_selected_id(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = public_root / "fixtures/first_wave/agent_route_observability_runtime"
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        fixture,
    )
    lens_path = fixture / "input/agent_principle_lens_receipt.json"
    payload = json.loads(lens_path.read_text(encoding="utf-8"))
    payload["selected_ids"] = [
        principle_id
        for principle_id in payload["selected_ids"]
        if principle_id != "pri_144"
    ]
    for row in payload["compact_admission_receipts"]:
        row["selected_ids_preserved"] = True
    lens_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    decisions = result["agent_principle_lens"]["compact_admission_receipts"]
    assert result["status"] == "blocked"
    assert result["agent_principle_lens"]["status"] == "blocked"
    assert all(row["decision"] == "blocked" for row in decisions)
    assert all(
        "AGENT_PRINCIPLE_COMPACT_HANDLE_MISSING" in row["error_codes"]
        for row in decisions
    )
    assert any(
        row["error_code"] == "AGENT_PRINCIPLE_LENS_SELECTED_ID_MISSING"
        for row in result["findings"]
    )


def test_agent_route_observability_primary_run_principle_lens_rejects_row_body_overclaim(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = public_root / "fixtures/first_wave/agent_route_observability_runtime"
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        fixture,
    )
    lens_path = fixture / "input/agent_principle_lens_receipt.json"
    payload = json.loads(lens_path.read_text(encoding="utf-8"))
    payload["compact_admission_receipts"][0]["row_bodies_exported"] = True
    payload["compact_admission_receipts"][0]["selected_ids_preserved"] = True
    lens_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    decision = result["agent_principle_lens"]["compact_admission_receipts"][0]
    assert result["status"] == "blocked"
    assert result["agent_principle_lens"]["status"] == "blocked"
    assert decision["decision"] == "blocked"
    assert "AGENT_PRINCIPLE_COMPACT_AUTHORITY_OVERCLAIM" in decision["error_codes"]
    assert decision["derived_from"] == "agent_principle_lens_route_and_authority_fields"


def test_agent_route_observability_primary_run_derives_route_overclaim_from_evidence(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = public_root / "fixtures/first_wave/agent_route_observability_runtime"
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        fixture,
    )
    trace_path = fixture / "input/agent_trace.jsonl"
    rows = [
        json.loads(line)
        for line in trace_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    overclaim = next(row for row in rows if row["event_id"] == "trace_route_overclaim")
    overclaim["route_compliance_status"] = "blocked"
    overclaim["error_codes"] = []
    trace_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    decisions = {
        row["event_id"]: row for row in result["route_compliance"]["route_compliance_decisions"]
    }
    assert result["status"] == "pass"
    assert decisions["trace_route_overclaim"]["declared_route_compliance_status"] == "blocked"
    assert decisions["trace_route_overclaim"]["decision"] == "rejected"
    assert decisions["trace_route_overclaim"]["derived_from"] == "trace_event_evidence"
    assert "ROUTE_COMPLIANCE_PASS_OVERCLAIMS_BEHAVIOR_CHANGE" in (
        decisions["trace_route_overclaim"]["error_codes"]
    )


def test_agent_route_observability_primary_run_ignores_baked_route_error_codes(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = public_root / "fixtures/first_wave/agent_route_observability_runtime"
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        fixture,
    )
    trace_path = fixture / "input/agent_trace.jsonl"
    rows = [
        json.loads(line)
        for line in trace_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    good_row = next(row for row in rows if row["event_id"] == "trace_behavior_change")
    good_row["error_codes"] = ["MISSING_ROUTE_LEASE", "DECLARED_ONLY_FAILURE"]
    trace_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    decisions = {
        row["event_id"]: row for row in result["route_compliance"]["route_compliance_decisions"]
    }
    assert result["status"] == "pass"
    assert decisions["trace_behavior_change"]["decision"] == "accepted"
    assert decisions["trace_behavior_change"]["error_codes"] == []
    assert decisions["trace_behavior_change"]["derived_from"] == "trace_event_evidence"


def test_agent_route_observability_primary_run_accepts_resolved_behavior_evidence_ref(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = public_root / "fixtures/first_wave/agent_route_observability_runtime"
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        fixture,
    )
    trace_path = fixture / "input/agent_trace.jsonl"
    rows = [
        json.loads(line)
        for line in trace_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    behavior_row = next(row for row in rows if row["event_id"] == "trace_behavior_change")
    behavior_row["require_behavior_change_evidence_ref_resolution"] = True
    rows.append(
        {
            "event_id": "trace_fix_001",
            "actor_axis": "type_a_substrate",
            "claims_mutation_authority": False,
            "requires_route_lease": False,
            "route_compliance_status": "pass",
            "claims_behavior_change": False,
            "behavior_change_evidence_trace_ids": [],
            "lease_consumed": True,
            "first_action_after_lease": "record_public_trace_fix",
            "selected_lane_id": "direct_local",
        }
    )
    trace_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    decisions = {
        row["event_id"]: row for row in result["route_compliance"]["route_compliance_decisions"]
    }
    assert result["status"] == "pass"
    assert decisions["trace_behavior_change"]["decision"] == "accepted"
    assert decisions["trace_behavior_change"]["error_codes"] == []


def test_agent_route_observability_primary_run_rejects_unresolved_behavior_evidence_ref(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = public_root / "fixtures/first_wave/agent_route_observability_runtime"
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        fixture,
    )
    trace_path = fixture / "input/agent_trace.jsonl"
    rows = [
        json.loads(line)
        for line in trace_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    behavior_row = next(row for row in rows if row["event_id"] == "trace_behavior_change")
    behavior_row["require_behavior_change_evidence_ref_resolution"] = True
    behavior_row["behavior_change_evidence_trace_ids"] = ["missing_public_trace"]
    trace_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    decisions = {
        row["event_id"]: row for row in result["route_compliance"]["route_compliance_decisions"]
    }
    assert result["status"] == "blocked"
    assert result["route_compliance"]["status"] == "blocked"
    assert "behavior_change_evidence_trace_ref_missing" in (
        result["route_compliance"]["unexpected_negative_cases"]
    )
    assert "BEHAVIOR_CHANGE_EVIDENCE_TRACE_REF_MISSING" in (
        decisions["trace_behavior_change"]["error_codes"]
    )


def test_agent_route_observability_primary_run_validates_copied_trace_analytics(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = _copy_primary_fixture_with_route_analytics(public_root)

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    analytics = result["primary_route_trace_analytics"]
    assert result["status"] == "pass"
    assert analytics["status"] == "pass"
    assert analytics["source_binding"] == "primary_fixture"
    assert analytics["source_module_path"] == "source_modules/system/lib/agent_execution_trace.py"
    assert analytics["average_route_compliance"] == pytest.approx(0.967)
    assert analytics["session_count"] == 3
    assert "system/lib/agent_execution_trace.py::_compute_route_compliance" in (
        analytics["source_functions_invoked"]
    )
    assert analytics["body_in_receipt"] is False


def test_agent_route_observability_primary_run_trace_analytics_perturbation_blocks(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = _copy_primary_fixture_with_route_analytics(public_root)
    trace_path = fixture / "input/trace_analytics_spans.json"
    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    grep_first_session = next(
        row
        for row in trace_payload["sessions"]
        if row["session_id"] == "synthetic_grep_before_kernel"
    )
    first_span = grep_first_session["spans"][0]
    first_span["action_kind"] = "kernel_command"
    first_span["command"] = "./repo-python kernel.py --preflight"
    first_span["normalized_command"] = "./repo-python kernel.py --preflight"
    first_span["kernel_flags"] = ["--preflight"]
    first_span["is_kernel_shape"] = True
    first_span["is_grep_shape"] = False
    trace_path.write_text(
        json.dumps(trace_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["primary_route_trace_analytics"]["status"] == "blocked"
    assert "ROUTE_TRACE_ANALYTICS_SCORE_MISMATCH" in result["error_codes"]
    assert "ROUTE_TRACE_ANALYTICS_ANTI_PATTERN_MISSING" in result["error_codes"]
    assert result["primary_route_trace_analytics"]["body_in_receipt"] is False


def test_agent_route_observability_primary_run_rejects_stale_copied_source_module(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = _copy_primary_fixture_with_route_analytics(public_root)
    manifest_path = fixture / "input/source_module_manifest.json"
    source_path = fixture / "input/source_modules/system/lib/agent_execution_trace.py"
    source_path.write_text(
        source_path.read_text(encoding="utf-8") + "\n# stale self-consistent copy\n",
        encoding="utf-8",
    )
    stale_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    stale_line_count = len(source_path.read_text(encoding="utf-8").splitlines())
    stale_byte_count = source_path.stat().st_size
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    row = next(
        item
        for item in manifest["modules"]
        if item["path"] == "source_modules/system/lib/agent_execution_trace.py"
    )
    row["sha256"] = stale_digest
    row["source_sha256"] = f"sha256:{stale_digest}"
    row["target_sha256"] = f"sha256:{stale_digest}"
    row["line_count"] = stale_line_count
    row["byte_count"] = stale_byte_count
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["primary_route_source_manifest"]["status"] == "blocked"
    assert "ROUTE_COMPLIANCE_AUDIT_LIVE_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert "ROUTE_COMPLIANCE_AUDIT_LIVE_SOURCE_TARGET_DIGEST_MISMATCH" in (
        result["error_codes"]
    )


def test_agent_route_observability_primary_run_rejects_egress_declared_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = public_root / "fixtures/first_wave/agent_route_observability_runtime"
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        fixture,
    )
    egress_path = fixture / "input/egress_mirror_cases.json"
    payload = json.loads(egress_path.read_text(encoding="utf-8"))
    case = payload["cases"][0]
    case["expected_violation"] = False
    case["expected_decision"] = "allow_with_fresh_authority"
    egress_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    decision = result["egress_mirror"]["egress_mirror_decisions"][0]
    assert result["status"] == "blocked"
    assert result["egress_mirror"]["status"] == "blocked"
    assert decision["decision"] == "block"
    assert decision["declared_decision"] == "allow_with_fresh_authority"
    assert decision["derived_from"] == "egress_detector_evidence"
    assert "EGRESS_MIRROR_DECLARED_DECISION_MISMATCH" in decision["error_codes"]
    assert "EGRESS_MIRROR_DECLARED_VIOLATION_MISMATCH" in decision["error_codes"]


def test_agent_route_observability_primary_run_egress_perturbation_changes_verdict(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = public_root / "fixtures/first_wave/agent_route_observability_runtime"
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        fixture,
    )
    egress_path = fixture / "input/egress_mirror_cases.json"
    payload = json.loads(egress_path.read_text(encoding="utf-8"))
    case = payload["cases"][0]
    case["durable_binding_present"] = True
    case["fresh_authority_present"] = True
    case["expected_violation"] = False
    case["expected_decision"] = "allow_with_fresh_authority"
    egress_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    decision = result["egress_mirror"]["egress_mirror_decisions"][0]
    assert result["status"] == "pass"
    assert result["egress_mirror"]["egress_violation_count"] == 2
    assert result["egress_mirror"]["egress_allowed_count"] == 4
    assert decision["decision"] == "allow_with_fresh_authority"
    assert decision["expected_violation"] is False
    assert decision["error_codes"] == []


def test_agent_route_observability_primary_run_egress_blocks_private_boundary_breach(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = public_root / "fixtures/first_wave/agent_route_observability_runtime"
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        fixture,
    )
    egress_path = fixture / "input/egress_mirror_cases.json"
    payload = json.loads(egress_path.read_text(encoding="utf-8"))
    case = payload["cases"][3]
    case["private_state_read"] = True
    case["expected_violation"] = False
    case["expected_decision"] = "allow_with_fresh_authority"
    egress_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    decision = result["egress_mirror"]["egress_mirror_decisions"][3]
    assert result["status"] == "blocked"
    assert result["egress_mirror"]["status"] == "blocked"
    assert decision["decision"] == "allow_with_fresh_authority"
    assert "EGRESS_MIRROR_PRIVATE_STATE_BOUNDARY_BREACH" in decision["error_codes"]


def test_agent_route_observability_primary_run_egress_blocks_unknown_detector(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = public_root / "fixtures/first_wave/agent_route_observability_runtime"
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        fixture,
    )
    egress_path = fixture / "input/egress_mirror_cases.json"
    payload = json.loads(egress_path.read_text(encoding="utf-8"))
    case = payload["cases"][3]
    case["detector_id"] = "unknown_detector"
    case["expected_violation"] = False
    case["expected_decision"] = "allow_with_fresh_authority"
    egress_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    decision = result["egress_mirror"]["egress_mirror_decisions"][3]
    assert result["status"] == "blocked"
    assert result["egress_mirror"]["status"] == "blocked"
    assert decision["decision"] == "block"
    assert "EGRESS_MIRROR_DECLARED_DECISION_MISMATCH" in decision["error_codes"]
    assert "EGRESS_MIRROR_DECLARED_VIOLATION_MISMATCH" in decision["error_codes"]


def test_agent_route_observability_primary_run_consumes_trace_analytics_sources(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = public_root / "fixtures/first_wave/agent_route_observability_runtime"
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        fixture,
    )
    shutil.copy2(
        ROUTE_COMPLIANCE_AUDIT_BUNDLE_INPUT / "trace_analytics_spans.json",
        fixture / "input/trace_analytics_spans.json",
    )
    shutil.copytree(
        ROUTE_COMPLIANCE_AUDIT_BUNDLE_INPUT / "source_modules",
        fixture / "input/source_modules",
    )

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    analytics = result["primary_route_trace_analytics"]
    assert result["status"] == "pass"
    assert analytics["status"] == "pass"
    assert analytics["session_count"] == 3
    assert analytics["source_module_path"] == (
        "source_modules/system/lib/agent_execution_trace.py"
    )
    assert "system/lib/agent_execution_trace.py::_compute_route_compliance" in (
        analytics["source_functions_invoked"]
    )
    assert analytics["body_in_receipt"] is False


def test_agent_route_observability_primary_run_accepts_resolved_behavior_ref(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = public_root / "fixtures/first_wave/agent_route_observability_runtime"
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        fixture,
    )
    trace_path = fixture / "input/agent_trace.jsonl"
    rows = [
        json.loads(line)
        for line in trace_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    behavior_change = next(row for row in rows if row["event_id"] == "trace_behavior_change")
    behavior_change["require_behavior_change_evidence_ref_resolution"] = True
    behavior_change["behavior_change_evidence_trace_ids"] = ["trace_missing_lease"]
    trace_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    decisions = {
        row["event_id"]: row for row in result["route_compliance"]["route_compliance_decisions"]
    }
    assert result["status"] == "pass"
    assert decisions["trace_behavior_change"]["decision"] == "accepted"
    assert "BEHAVIOR_CHANGE_EVIDENCE_TRACE_REF_MISSING" not in result["error_codes"]


def test_agent_route_observability_primary_run_rejects_unresolved_behavior_ref(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = public_root / "fixtures/first_wave/agent_route_observability_runtime"
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        fixture,
    )
    trace_path = fixture / "input/agent_trace.jsonl"
    rows = [
        json.loads(line)
        for line in trace_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    behavior_change = next(row for row in rows if row["event_id"] == "trace_behavior_change")
    behavior_change["require_behavior_change_evidence_ref_resolution"] = True
    trace_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    decisions = {
        row["event_id"]: row for row in result["route_compliance"]["route_compliance_decisions"]
    }
    assert result["status"] == "blocked"
    assert decisions["trace_behavior_change"]["decision"] == "rejected"
    assert "BEHAVIOR_CHANGE_EVIDENCE_TRACE_REF_MISSING" in result["error_codes"]
    assert "BEHAVIOR_CHANGE_EVIDENCE_TRACE_REF_MISSING" in (
        decisions["trace_behavior_change"]["error_codes"]
    )


def test_agent_route_observability_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        public_root / "fixtures/first_wave/agent_route_observability_runtime",
    )

    result = run(
        public_root / "fixtures/first_wave/agent_route_observability_runtime/input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == EXPECTED_RECEIPT_PATHS
    for receipt_path in EXPECTED_RECEIPT_PATHS:
        receipt_file = public_root / receipt_path
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "/private/var" not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["private_state_scan"]["body_redacted"] is True
        assert payload["private_state_scan"]["blocking_hit_count"] == 0
        assert payload["missing_negative_cases"] == []
        assert set(payload["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)
        for hit in payload["private_state_scan"]["hits"]:
            assert hit["body_redacted"] is True
            assert not Path(hit["path"]).is_absolute()


def test_agent_route_observability_receipts_satisfy_macro_field_floor(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        public_root / "fixtures/first_wave/agent_route_observability_runtime",
    )
    run(
        public_root / "fixtures/first_wave/agent_route_observability_runtime/input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    for receipt_path, required_fields in _field_floor().items():
        payload = json.loads((public_root / receipt_path).read_text(encoding="utf-8"))
        missing = [field for field in required_fields if field not in payload]
        assert missing == []


def test_agent_route_observability_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_observability_bundle(
        OBS_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_observability_bundle"
    assert result["bundle_id"] == "public_agent_route_observability_runtime_example"
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["metadata_projection_not_live_telemetry_authority"] is True
    assert result["authority_ceiling"]["live_operator_state_read"] is False
    assert result["authority_ceiling"]["provider_payload_read"] is False
    assert result["authority_ceiling"]["browser_hud_cockpit_state_read"] is False
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["route_event_count"] == 2
    assert result["agent_path_observation_count"] == 2
    assert result["session_diagnostic_count"] == 1
    assert result["hook_shadow_coverage"]["hook_shadow_coverage_status"] == (
        "public_metadata_coverage_only"
    )
    assert result["hook_shadow_coverage"]["hook_shadow_case_count"] == 4
    assert result["hook_shadow_coverage"]["hook_shadow_repair_class_count"] == 3
    assert result["hook_shadow_coverage"]["missing_authority_count"] == 1
    assert result["actor_axis_checks"]["actor_axis_check_count"] == 2
    assert result["debt_retirement"]["debt_retirement_count"] == 1
    assert result["process_audit_rows"]["process_audit_row_count"] == 2
    assert result["observability_policy"]["forbidden_authority_rejected"] is True
    assert result["body_in_receipt"] is False
    assert result["copied_macro_source_count"] == 7
    assert result["source_module_manifest"]["status"] == "pass"
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_expected_line_counts_matched"] is True
    assert result["source_module_manifest"]["all_expected_byte_counts_matched"] is True
    assert result["source_module_manifest"]["body_in_receipt"] is False
    assert result["exact_source_body_import"]["verification_mode"] == (
        "exact_source_digest_match"
    )
    assert result["exact_source_body_import"]["source_body_digests"] == (
        result["exact_source_body_import"]["target_body_digests"]
    )
    assert result["exact_source_body_import"]["body_in_receipt"] is False
    assert result["consumed_route_lease_ids"] == [
        "lease_public_advisory_boundary",
        "lease_public_observability_runtime",
    ]
    assert all(not Path(path).is_absolute() for path in result["public_replacement_refs"])


def test_agent_route_observability_exported_bundle_rejects_source_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/agent_route_observability_runtime/exported_observability_bundle"
    )
    shutil.copytree(OBS_BUNDLE_INPUT, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_observability_bundle(
        bundle,
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert "OBSERVABILITY_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False
    assert result["private_state_scan"]["status"] == "pass"


@pytest.mark.parametrize(
    ("bundle_input", "runner", "expected_error_code"),
    [
        (
            ROUTE_COMPLIANCE_AUDIT_BUNDLE_INPUT,
            run_route_compliance_audit_bundle,
            "ROUTE_COMPLIANCE_AUDIT_SOURCE_MODULE_DIGEST_MISMATCH",
        ),
        (
            COMPUTER_USE_BUNDLE_INPUT,
            run_computer_use_action_trace_bundle,
            "COMPUTER_USE_SOURCE_MODULE_DIGEST_MISMATCH",
        ),
        (
            SESSION_ATTRIBUTION_BUNDLE_INPUT,
            run_session_attribution_bundle,
            "SESSION_ATTRIBUTION_SOURCE_MODULE_DIGEST_MISMATCH",
        ),
        (
            HARNESS_CONFIGURATION_AUDIT_BUNDLE_INPUT,
            run_harness_configuration_audit_bundle,
            "HARNESS_CONFIGURATION_SOURCE_MODULE_DIGEST_MISMATCH",
        ),
        (
            MULTI_AGENT_FANIN_BUNDLE_INPUT,
            run_multi_agent_fanin_bundle,
            "MULTI_AGENT_FANIN_SOURCE_MODULE_DIGEST_MISMATCH",
        ),
        (
            BRIDGE_DISPATCH_YIELD_RESUME_BUNDLE_INPUT,
            run_bridge_dispatch_yield_resume_bundle,
            "BRIDGE_RESUME_SOURCE_MODULE_DIGEST_MISMATCH",
        ),
        (
            CONTROLLER_HEARTBEAT_BUNDLE_INPUT,
            run_controller_heartbeat_bundle,
            "CONTROLLER_HEARTBEAT_SOURCE_MODULE_DIGEST_MISMATCH",
        ),
        (
            AGENT_TRACE_ROUTE_REPAIR_BUNDLE_INPUT,
            run_agent_trace_route_repair_bundle,
            "AGENT_TRACE_ROUTE_REPAIR_SOURCE_MODULE_DIGEST_MISMATCH",
        ),
        (
            AGENT_OBSERVABILITY_STORE_BUNDLE_INPUT,
            run_agent_observability_store_bundle,
            "AGENT_OBSERVABILITY_STORE_SOURCE_MODULE_DIGEST_MISMATCH",
        ),
    ],
)
def test_agent_route_companion_bundles_reject_source_digest_mismatch(
    tmp_path: Path,
    bundle_input: Path,
    runner: Any,
    expected_error_code: str,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/agent_route_observability_runtime"
        / bundle_input.name
    )
    shutil.copytree(bundle_input, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = runner(
        bundle,
        public_root
        / "receipts/first_wave/agent_route_observability_runtime"
        / bundle_input.name,
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert expected_error_code in result["error_codes"]
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False
    assert result["source_module_manifest"]["body_in_receipt"] is False


def test_agent_route_observability_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    out = tmp_path / "receipts/first_wave/agent_route_observability_runtime"
    command = (
        "python -m microcosm_core.organs.agent_route_observability_runtime "
        f"validate-observability-bundle --input {OBS_BUNDLE_INPUT} --out {out} --card"
    )

    first = run_observability_bundle(
        OBS_BUNDLE_INPUT,
        out,
        command=command,
        reuse_fresh_receipt=True,
    )
    first_card = result_card(first)

    assert first["status"] == "pass"
    assert first["receipt_reused"] is False
    assert first_card["schema_version"] == OBSERVABILITY_CARD_SCHEMA_VERSION
    assert first_card["command_speed"]["receipt_reused"] is False
    assert first_card["command_speed"]["freshness_input_count"] == 18
    assert first_card["observability"]["route_event_count"] == 2
    assert first_card["observability"]["agent_path_observation_count"] == 2
    assert first_card["observability"]["session_diagnostic_count"] == 1
    assert first_card["observability"]["copied_macro_source_count"] == 7
    assert first_card["validation"]["finding_count"] == 0
    assert all(value is False for value in first_card["body_floor"].values())
    assert "findings" not in first_card
    assert "private_state_scan" not in first_card
    assert "source_refs" not in first_card

    def fail_load_bundle(*_args, **_kwargs):
        raise AssertionError("fresh --card bundle path should reuse the receipt")

    monkeypatch.setattr(
        agent_route_observability_runtime,
        "_load_observability_bundle",
        fail_load_bundle,
    )

    assert (
        main(
            [
                "validate-observability-bundle",
                "--input",
                str(OBS_BUNDLE_INPUT),
                "--out",
                str(out),
                "--card",
            ]
        )
        == 0
    )
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]


def test_agent_route_observability_bundle_card_exposes_private_scan_blocker(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_route_observability_runtime",
        public_root / "examples/agent_route_observability_runtime",
    )
    policy_path = (
        public_root
        / "examples/agent_route_observability_runtime/"
        "exported_observability_bundle/observability_policy.json"
    )
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["synthetic_private_state_regression_token"] = (
        "SYNTHETIC_PROVIDER_PAYLOAD_BODY_SENTINEL"
    )
    policy_path.write_text(
        json.dumps(policy, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    result = run_observability_bundle(
        public_root
        / "examples/agent_route_observability_runtime/exported_observability_bundle",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )
    card = result_card(result)

    assert result["status"] == "blocked"
    assert result["findings"] == []
    assert card["status"] == "blocked"
    assert card["validation"]["finding_count"] == 0
    assert card["validation"]["private_state_scan_status"] == "blocked_private_state"
    assert card["validation"]["private_state_blocking_hit_count"] == 1
    assert card["validation"]["private_state_body_redacted"] is True
    assert "private_state_scan" not in card
    assert "hits" not in _walk_keys(card)


def test_agent_route_observability_exported_bundle_rejects_nested_forbidden_payload_key(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_route_observability_runtime",
        public_root / "examples/agent_route_observability_runtime",
    )
    route_events_path = (
        public_root
        / "examples/agent_route_observability_runtime/"
        "exported_observability_bundle/route_events.json"
    )
    payload = json.loads(route_events_path.read_text(encoding="utf-8"))
    payload["route_events"][0]["metadata"] = {
        "provider_payload": "redacted body should not be present as a payload key"
    }
    route_events_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_observability_bundle(
        public_root
        / "examples/agent_route_observability_runtime/exported_observability_bundle",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["forbidden_payload_keys"] == ["provider_payload"]
    assert "OBSERVABILITY_BUNDLE_FORBIDDEN_PAYLOAD_KEY" in result["error_codes"]
    assert result["body_in_receipt"] is False


def test_agent_route_observability_exported_bundle_receipt_is_public_safe(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_route_observability_runtime",
        public_root / "examples/agent_route_observability_runtime",
    )

    result = run_observability_bundle(
        public_root
        / "examples/agent_route_observability_runtime/exported_observability_bundle",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == [EXPORTED_OBSERVABILITY_BUNDLE_RECEIPT_PATH]
    receipt_file = public_root / EXPORTED_OBSERVABILITY_BUNDLE_RECEIPT_PATH
    assert receipt_file.is_file()
    text = receipt_file.read_text(encoding="utf-8")
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "/private/var" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    payload = json.loads(text)
    assert payload["status"] == "pass"
    assert payload["input_mode"] == "exported_observability_bundle"
    assert payload["fixture_regression_required_elsewhere"] is True
    assert payload["private_state_scan"]["body_redacted"] is True
    assert payload["private_state_scan"]["blocking_hit_count"] == 0
    assert payload["expected_negative_cases"] == {}
    assert payload["metadata_projection_not_live_telemetry_authority"] is True
    assert payload["authority_ceiling"]["private_data_equivalence_claim"] is False
    assert payload["authority_ceiling"]["behavior_change_overclaims_allowed"] is False
    assert payload["body_in_receipt"] is False
    assert payload["copied_macro_source_count"] == 7
    assert payload["source_module_manifest"]["status"] == "pass"
    assert payload["source_module_manifest"]["body_in_receipt"] is False
    assert payload["exact_source_body_import"]["body_in_receipt"] is False
    assert payload["exact_source_body_import"]["source_body_digests"] == (
        payload["exact_source_body_import"]["target_body_digests"]
    )
    forbidden_keys = {
        "raw_transcript_body",
        "transcript_body",
        "provider_payload",
        "browser_hud_state",
        "browser_hud_cockpit_state",
        "account_session_state",
        "credential_value",
        "cookie",
        "password",
        "secret_value",
        "api_key",
        "access_token",
        "refresh_token",
        "recipient_send_payload",
        "raw_payload_available",
    }
    assert forbidden_keys.isdisjoint(_walk_keys(payload))
    assert "matched_excerpt" not in _walk_keys(payload)
    assert "body" not in _walk_keys(payload)
    for hit in payload["private_state_scan"]["hits"]:
        assert hit["body_redacted"] is True
        assert not Path(hit["path"]).is_absolute()


def test_route_compliance_audit_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_route_compliance_audit_bundle(
        ROUTE_COMPLIANCE_AUDIT_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_route_compliance_audit_bundle"
    assert result["bundle_id"] == "public_route_compliance_audit_runtime_example"
    assert result["trace_count"] == 5
    assert result["accepted_decision_count"] == 2
    assert result["rejected_decision_count"] == 3
    assert result["trace_analytics"]["status"] == "pass"
    assert result["trace_analytics"]["session_count"] == 3
    assert result["trace_analytics"]["source_module_path"] == (
        "source_modules/system/lib/agent_execution_trace.py"
    )
    assert result["trace_analytics"]["average_route_compliance"] == pytest.approx(0.967)
    assert "system/lib/agent_execution_trace.py::_compute_route_compliance" in (
        result["trace_analytics"]["source_functions_invoked"]
    )
    assert result["trace_analytics"]["pattern_counts"][
        "anti_pattern_grep_before_kernel"
    ] == 1
    assert result["trace_analytics"]["pattern_counts"][
        "positive_kernel_ladder_climb"
    ] == 1
    assert result["trace_analytics"]["route_lease_mode_control_counts"][
        "full_output_kernel_bloat"
    ] == 1
    analytics_by_session = {
        row["session_id"]: row for row in result["trace_analytics"]["sessions"]
    }
    assert analytics_by_session["synthetic_grep_before_kernel"][
        "route_compliance"
    ]["score"] == 0.9
    assert analytics_by_session["synthetic_grep_before_kernel"][
        "route_compliance"
    ]["violations"] == [
        {"rule": "grep_before_kernel", "grep_span": 0, "kernel_span": 1}
    ]
    assert analytics_by_session["synthetic_route_lease_output_bloat"][
        "route_lease_mode_control"
    ]["signal_counts"]["full_output_kernel_bloat"] == 1
    assert result["actor_axis_mismatch_count"] == 1
    assert result["authority_rejection_count"] == 1
    assert result["duplicate_trace_event_ids"] == []
    assert result["expected_summary_validation"]["actual_summary"][
        "missing_route_lease_count"
    ] == 1
    assert result["expected_summary_validation"]["actual_summary"][
        "behavior_change_overclaim_count"
    ] == 1
    assert set(result["observed_negative_cases"]) == {
        "agent_trace_missing_route_lease",
        "route_compliance_overclaims_behavior_change",
        "wrong_actor_axis_and_evidence_only_telemetry",
    }
    assert result["missing_negative_cases"] == []
    assert result["route_compliance_policy"]["projection_not_authority"] is True
    assert result["route_compliance_policy"]["required_false_field_failures"] == []
    assert all(
        row["observed_value"] is False and row["passed"] is True
        for row in result["route_compliance_policy"]["required_false_field_checks"]
    )
    assert result["authority_ceiling"]["live_process_audit_authority"] is False
    assert result["authority_ceiling"]["provider_payload_read"] is False
    assert result["authority_ceiling"]["browser_hud_cockpit_state_read"] is False
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["metadata_envelope_only"] is True
    assert result["body_in_receipt"] is False
    assert result["copied_macro_source_count"] == 7
    assert result["public_reference_sanitized_source_count"] == 1
    assert result["source_module_manifest"]["status"] == "pass"
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert (
        result["source_module_manifest"]["all_exact_source_target_digests_matched"]
        is True
    )
    assert result["source_module_manifest"]["all_expected_line_counts_matched"] is True
    assert result["source_module_manifest"]["all_expected_byte_counts_matched"] is True
    assert result["source_module_manifest"]["body_in_receipt"] is False
    assert result["exact_source_body_import"]["verification_mode"] == (
        "exact_source_digest_match"
    )
    assert result["exact_source_body_import"]["source_body_digests"] == (
        result["exact_source_body_import"]["target_body_digests"]
    )
    assert len(result["exact_source_body_import"]["source_body_digests"]) == 7
    assert result["exact_source_body_import"]["body_in_receipt"] is False
    sanitized_import = result["public_reference_sanitized_body_import"]
    assert sanitized_import["verification_mode"] == (
        "public_reference_sanitizer_receipt_and_target_digest_match"
    )
    assert sanitized_import["source_to_target_relation"] == (
        agent_route_observability_runtime.ROUTE_COMPLIANCE_AUDIT_SANITIZED_SOURCE_RELATION
    )
    assert len(sanitized_import["source_body_digests"]) == 1
    assert len(sanitized_import["target_body_digests"]) == 1
    assert sanitized_import["source_body_digests"] != sanitized_import["target_body_digests"]
    assert sanitized_import["sanitization_receipts"][0]["blocker_count"] == 0
    assert sanitized_import["body_in_receipt"] is False


def test_route_compliance_audit_bundle_rejects_mutated_trace_analytics(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/agent_route_observability_runtime/"
        "exported_route_compliance_audit_bundle"
    )
    shutil.copytree(ROUTE_COMPLIANCE_AUDIT_BUNDLE_INPUT, bundle)
    trace_path = bundle / "trace_analytics_spans.json"
    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    grep_first_session = next(
        row
        for row in trace_payload["sessions"]
        if row["session_id"] == "synthetic_grep_before_kernel"
    )
    first_span = grep_first_session["spans"][0]
    first_span["action_kind"] = "kernel_command"
    first_span["command"] = "./repo-python kernel.py --preflight"
    first_span["normalized_command"] = "./repo-python kernel.py --preflight"
    first_span["kernel_flags"] = ["--preflight"]
    first_span["is_kernel_shape"] = True
    first_span["is_grep_shape"] = False
    trace_path.write_text(
        json.dumps(trace_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_route_compliance_audit_bundle(
        bundle,
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["trace_analytics"]["status"] == "blocked"
    assert "ROUTE_TRACE_ANALYTICS_SCORE_MISMATCH" in result["error_codes"]
    assert "ROUTE_TRACE_ANALYTICS_ANTI_PATTERN_MISSING" in result["error_codes"]
    finding_subjects = {
        row["subject_id"] for row in result["trace_analytics"]["findings"]
    }
    assert "synthetic_grep_before_kernel" in finding_subjects
    assert "synthetic_grep_before_kernel:anti_pattern_grep_before_kernel" in (
        finding_subjects
    )
    assert result["trace_analytics"]["body_in_receipt"] is False


def test_route_compliance_audit_bundle_accepts_sanitized_agent_trace_structurer_trace(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/agent_route_observability_runtime/"
        "exported_route_compliance_audit_bundle"
    )
    shutil.copytree(ROUTE_COMPLIANCE_AUDIT_BUNDLE_INPUT, bundle)
    _replace_trace_analytics_session_with_structurer_clip(
        bundle,
        session_id="synthetic_route_compliant_ladder",
        commands=[
            "./repo-python kernel.py --preflight",
            './repo-python kernel.py --entry "microcosm route" --context-budget 12000',
            (
                "sed -n '1,120p' "
                "microcosm-substrate/src/microcosm_core/organs/"
                "agent_route_observability_runtime.py"
            ),
        ],
    )

    result = run_route_compliance_audit_bundle(
        bundle,
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["trace_analytics"]["status"] == "pass"
    assert result["trace_analytics"][
        "agent_trace_structurer_trace_schema_version"
    ] == "agent_route_observability_runtime_agent_trace_structurer_trace_v1"
    analytics_by_session = {
        row["session_id"]: row for row in result["trace_analytics"]["sessions"]
    }
    real_trace = analytics_by_session["synthetic_route_compliant_ladder"]
    assert real_trace["trace_source"] == "agent_trace_structurer_command_ledger"
    assert real_trace["route_compliance"]["score"] == 1.0
    assert "positive_kernel_ladder_climb" in real_trace["anti_pattern_ids"]
    assert result["trace_analytics"]["body_in_receipt"] is False


def test_route_compliance_audit_bundle_rejects_raw_agent_trace_structurer_body(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/agent_route_observability_runtime/"
        "exported_route_compliance_audit_bundle"
    )
    shutil.copytree(ROUTE_COMPLIANCE_AUDIT_BUNDLE_INPUT, bundle)
    session = _replace_trace_analytics_session_with_structurer_clip(
        bundle,
        session_id="synthetic_route_compliant_ladder",
        commands=[
            "./repo-python kernel.py --preflight",
            './repo-python kernel.py --entry "microcosm route" --context-budget 12000',
        ],
    )
    session["agent_trace_structurer_clip"]["source_text"] = (
        "raw copied trace body should stay outside public route analytics"
    )
    trace_path = bundle / "trace_analytics_spans.json"
    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    trace_payload["sessions"][0] = session
    trace_path.write_text(
        json.dumps(trace_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_route_compliance_audit_bundle(
        bundle,
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["trace_analytics"]["status"] == "blocked"
    assert "AGENT_TRACE_STRUCTURER_RAW_BODY_FIELD" in result["error_codes"]
    assert result["trace_analytics"]["body_in_receipt"] is False


def test_route_compliance_audit_bundle_rejects_mutated_agent_trace_structurer_trace(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/agent_route_observability_runtime/"
        "exported_route_compliance_audit_bundle"
    )
    shutil.copytree(ROUTE_COMPLIANCE_AUDIT_BUNDLE_INPUT, bundle)
    _replace_trace_analytics_session_with_structurer_clip(
        bundle,
        session_id="synthetic_route_compliant_ladder",
        commands=[
            (
                "rg route_compliance microcosm-substrate/src/microcosm_core/"
                "organs/agent_route_observability_runtime.py"
            ),
            "./repo-python kernel.py --preflight",
            (
                "sed -n '1,120p' "
                "microcosm-substrate/src/microcosm_core/organs/"
                "agent_route_observability_runtime.py"
            ),
        ],
    )

    result = run_route_compliance_audit_bundle(
        bundle,
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["trace_analytics"]["status"] == "blocked"
    assert "ROUTE_TRACE_ANALYTICS_SCORE_MISMATCH" in result["error_codes"]
    assert "ROUTE_TRACE_ANALYTICS_ANTI_PATTERN_MISSING" in result["error_codes"]
    analytics_by_session = {
        row["session_id"]: row for row in result["trace_analytics"]["sessions"]
    }
    mutated_trace = analytics_by_session["synthetic_route_compliant_ladder"]
    assert mutated_trace["trace_source"] == "agent_trace_structurer_command_ledger"
    assert mutated_trace["route_compliance"]["score"] < 1.0
    assert "anti_pattern_grep_before_kernel" in mutated_trace["anti_pattern_ids"]
    finding_subjects = {
        row["subject_id"] for row in result["trace_analytics"]["findings"]
    }
    assert "synthetic_route_compliant_ladder" in finding_subjects
    assert "synthetic_route_compliant_ladder:positive_kernel_ladder_climb" in (
        finding_subjects
    )
    assert result["trace_analytics"]["body_in_receipt"] is False


def test_route_compliance_audit_bundle_accepts_real_trace_receipt_replay(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/agent_route_observability_runtime/"
        "exported_route_compliance_audit_bundle"
    )
    shutil.copytree(ROUTE_COMPLIANCE_AUDIT_BUNDLE_INPUT, bundle)
    real_session, live_claim = _build_real_trace_session_entry(
        "positive_kernel_ladder_climb",
        agent="codex",
    )
    _replace_trace_analytics_session(
        bundle,
        original_session_id="synthetic_route_compliant_ladder",
        replacement=real_session,
    )

    result = run_route_compliance_audit_bundle(
        bundle,
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["trace_analytics"]["status"] == "pass"
    analytics_by_session = {
        row["session_id"]: row for row in result["trace_analytics"]["sessions"]
    }
    replayed = analytics_by_session[real_session["session_id"]]
    assert replayed["trace_source"] == "real_agent_execution_trace_receipt"
    assert replayed["route_compliance"]["score"] == live_claim["route_compliance_score"]
    assert replayed["real_trace_replay"]["schema_version"] == (
        agent_route_observability_runtime.REAL_TRACE_RECEIPT_SCHEMA_VERSION
    )
    assert replayed["real_trace_replay"]["ledger_ref"] == "codex/hologram/process/ledger.json"
    assert replayed["real_trace_replay"]["body_in_receipt"] is False
    assert "positive_kernel_ladder_climb" in replayed["anti_pattern_ids"]
    assert result["trace_analytics"]["body_in_receipt"] is False


def test_route_compliance_audit_bundle_rejects_real_trace_route_state_claim_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/agent_route_observability_runtime/"
        "exported_route_compliance_audit_bundle"
    )
    shutil.copytree(ROUTE_COMPLIANCE_AUDIT_BUNDLE_INPUT, bundle)
    real_session, _ = _build_real_trace_session_entry(
        "positive_kernel_ladder_climb",
        agent="codex",
    )
    real_session["real_trace_receipt"]["route_state_claim"]["route_compliance_score"] = 0.0
    _replace_trace_analytics_session(
        bundle,
        original_session_id="synthetic_route_compliant_ladder",
        replacement=real_session,
    )

    result = run_route_compliance_audit_bundle(
        bundle,
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["trace_analytics"]["status"] == "blocked"
    assert "REAL_TRACE_ROUTE_STATE_CLAIM_MISMATCH" in result["error_codes"]
    assert result["trace_analytics"]["body_in_receipt"] is False


def test_route_compliance_audit_bundle_rejects_missing_real_trace_route_state_claim(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/agent_route_observability_runtime/"
        "exported_route_compliance_audit_bundle"
    )
    shutil.copytree(ROUTE_COMPLIANCE_AUDIT_BUNDLE_INPUT, bundle)
    real_session, _ = _build_real_trace_session_entry(
        "positive_kernel_ladder_climb",
        agent="codex",
    )
    real_session["real_trace_receipt"].pop("route_state_claim")
    _replace_trace_analytics_session(
        bundle,
        original_session_id="synthetic_route_compliant_ladder",
        replacement=real_session,
    )

    result = run_route_compliance_audit_bundle(
        bundle,
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["trace_analytics"]["status"] == "blocked"
    assert "REAL_TRACE_ROUTE_STATE_CLAIM_MISSING" in result["error_codes"]
    assert result["trace_analytics"]["body_in_receipt"] is False


def test_route_compliance_audit_bundle_rejects_incomplete_real_trace_route_state_claim(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/agent_route_observability_runtime/"
        "exported_route_compliance_audit_bundle"
    )
    shutil.copytree(ROUTE_COMPLIANCE_AUDIT_BUNDLE_INPUT, bundle)
    real_session, _ = _build_real_trace_session_entry(
        "positive_kernel_ladder_climb",
        agent="codex",
    )
    real_session["real_trace_receipt"]["route_state_claim"].pop("anti_pattern_ids")
    _replace_trace_analytics_session(
        bundle,
        original_session_id="synthetic_route_compliant_ladder",
        replacement=real_session,
    )

    result = run_route_compliance_audit_bundle(
        bundle,
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["trace_analytics"]["status"] == "blocked"
    assert "REAL_TRACE_ROUTE_STATE_CLAIM_INCOMPLETE" in result["error_codes"]
    assert result["trace_analytics"]["body_in_receipt"] is False


def test_route_compliance_audit_bundle_rejects_missing_real_trace_fingerprint(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/agent_route_observability_runtime/"
        "exported_route_compliance_audit_bundle"
    )
    shutil.copytree(ROUTE_COMPLIANCE_AUDIT_BUNDLE_INPUT, bundle)
    real_session, _ = _build_real_trace_session_entry(
        "positive_kernel_ladder_climb",
        agent="codex",
    )
    real_session["real_trace_receipt"].pop("route_state_fingerprint")
    _replace_trace_analytics_session(
        bundle,
        original_session_id="synthetic_route_compliant_ladder",
        replacement=real_session,
    )

    result = run_route_compliance_audit_bundle(
        bundle,
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["trace_analytics"]["status"] == "blocked"
    assert "REAL_TRACE_ROUTE_STATE_FINGERPRINT_MISSING" in result["error_codes"]
    assert result["trace_analytics"]["body_in_receipt"] is False


def test_route_compliance_audit_bundle_rejects_real_trace_fingerprint_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/agent_route_observability_runtime/"
        "exported_route_compliance_audit_bundle"
    )
    shutil.copytree(ROUTE_COMPLIANCE_AUDIT_BUNDLE_INPUT, bundle)
    real_session, _ = _build_real_trace_session_entry(
        "positive_kernel_ladder_climb",
        agent="codex",
    )
    real_session["real_trace_receipt"]["route_state_fingerprint"] = "0" * 64
    _replace_trace_analytics_session(
        bundle,
        original_session_id="synthetic_route_compliant_ladder",
        replacement=real_session,
    )

    result = run_route_compliance_audit_bundle(
        bundle,
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["trace_analytics"]["status"] == "blocked"
    assert "REAL_TRACE_ROUTE_STATE_FINGERPRINT_MISMATCH" in result["error_codes"]
    assert result["trace_analytics"]["body_in_receipt"] is False


def test_route_compliance_audit_bundle_does_not_echo_real_trace_expected_score(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/agent_route_observability_runtime/"
        "exported_route_compliance_audit_bundle"
    )
    shutil.copytree(ROUTE_COMPLIANCE_AUDIT_BUNDLE_INPUT, bundle)
    real_session, live_claim = _build_real_trace_session_entry(
        "positive_kernel_ladder_climb",
        agent="codex",
    )
    claimed_score = float(live_claim["route_compliance_score"])
    wrong_score = 0.0 if claimed_score != 0.0 else 1.0
    real_session["expected"]["route_compliance_score"] = wrong_score
    _replace_trace_analytics_session(
        bundle,
        original_session_id="synthetic_route_compliant_ladder",
        replacement=real_session,
    )

    result = run_route_compliance_audit_bundle(
        bundle,
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["trace_analytics"]["status"] == "blocked"
    assert "ROUTE_TRACE_ANALYTICS_SCORE_MISMATCH" in result["error_codes"]
    analytics_by_session = {
        row["session_id"]: row for row in result["trace_analytics"]["sessions"]
    }
    replayed = analytics_by_session[real_session["session_id"]]
    assert replayed["trace_source"] == "real_agent_execution_trace_receipt"
    assert replayed["route_compliance"]["score"] == claimed_score
    assert replayed["route_compliance"]["score"] != wrong_score
    assert result["trace_analytics"]["body_in_receipt"] is False


def test_route_compliance_audit_bundle_real_trace_perturbation_changes_verdict(
    tmp_path: Path,
) -> None:
    positive_bundle = tmp_path / "positive"
    negative_bundle = tmp_path / "negative"
    for root in (positive_bundle, negative_bundle):
        shutil.copytree(MICROCOSM_ROOT / "core", root / "microcosm-substrate/core")
        shutil.copytree(
            ROUTE_COMPLIANCE_AUDIT_BUNDLE_INPUT,
            root
            / "microcosm-substrate/examples/agent_route_observability_runtime/"
            "exported_route_compliance_audit_bundle",
        )

    positive_session, positive_claim = _build_real_trace_session_entry(
        "positive_kernel_ladder_climb",
        agent="codex",
    )
    _replace_trace_analytics_session(
        positive_bundle
        / "microcosm-substrate/examples/agent_route_observability_runtime/"
        "exported_route_compliance_audit_bundle",
        original_session_id="synthetic_route_compliant_ladder",
        replacement=positive_session,
    )
    positive_result = run_route_compliance_audit_bundle(
        positive_bundle
        / "microcosm-substrate/examples/agent_route_observability_runtime/"
        "exported_route_compliance_audit_bundle",
        positive_bundle
        / "microcosm-substrate/receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    degraded_session, _ = _build_real_trace_session_entry(
        "anti_pattern_cold_boot_missing_info",
        agent="codex",
    )
    degraded_session["expected"] = {
        "route_compliance_score": positive_claim["route_compliance_score"],
        "required_anti_patterns": ["positive_kernel_ladder_climb"],
        "required_mode_signals": positive_claim["route_lease_mode_signals"],
    }
    _replace_trace_analytics_session(
        negative_bundle
        / "microcosm-substrate/examples/agent_route_observability_runtime/"
        "exported_route_compliance_audit_bundle",
        original_session_id="synthetic_route_compliant_ladder",
        replacement=degraded_session,
    )
    negative_result = run_route_compliance_audit_bundle(
        negative_bundle
        / "microcosm-substrate/examples/agent_route_observability_runtime/"
        "exported_route_compliance_audit_bundle",
        negative_bundle
        / "microcosm-substrate/receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert positive_result["status"] == "pass"
    assert positive_result["trace_analytics"]["status"] == "pass"
    assert negative_result["status"] == "blocked"
    assert negative_result["trace_analytics"]["status"] == "blocked"
    assert "ROUTE_TRACE_ANALYTICS_ANTI_PATTERN_MISSING" in negative_result["error_codes"]
    analytics_by_session = {
        row["session_id"]: row for row in negative_result["trace_analytics"]["sessions"]
    }
    replayed = analytics_by_session[degraded_session["session_id"]]
    assert replayed["trace_source"] == "real_agent_execution_trace_receipt"
    assert replayed["route_compliance"]["score"] == positive_claim["route_compliance_score"]
    assert "anti_pattern_cold_boot_missing_info" in replayed["anti_pattern_ids"]
    assert "positive_kernel_ladder_climb" not in replayed["anti_pattern_ids"]
    assert negative_result["trace_analytics"]["body_in_receipt"] is False


def test_route_compliance_audit_bundle_receipt_is_public_safe(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_route_observability_runtime",
        public_root / "examples/agent_route_observability_runtime",
    )

    result = run_route_compliance_audit_bundle(
        public_root
        / "examples/agent_route_observability_runtime/"
        "exported_route_compliance_audit_bundle",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == [
        EXPORTED_ROUTE_COMPLIANCE_AUDIT_BUNDLE_RECEIPT_PATH
    ]
    receipt_file = public_root / EXPORTED_ROUTE_COMPLIANCE_AUDIT_BUNDLE_RECEIPT_PATH
    assert receipt_file.is_file()
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "/private/var" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    for field in (
        "release_authorized",
        "source_mutation_authorized",
        "provider_payload_read",
    ):
        assert f'"{field}": {str(True).lower()}' not in text
    assert payload["status"] == "pass"
    assert payload["input_mode"] == "exported_route_compliance_audit_bundle"
    assert payload["metadata_envelope_only"] is True
    assert payload["body_in_receipt"] is False
    assert payload["live_process_audit_authority"] is False
    assert payload["provider_payload_exported"] is False
    assert payload["browser_hud_cockpit_state_exported"] is False
    assert payload["raw_transcript_body_exported"] is False
    assert payload["source_mutation_authorized"] is False
    assert payload["release_authorized"] is False
    assert payload["private_data_equivalence_claim"] is False
    assert payload["private_state_scan"]["blocking_hit_count"] == 0
    assert payload["copied_macro_source_count"] == 7
    assert payload["public_reference_sanitized_source_count"] == 1
    assert payload["trace_analytics"]["status"] == "pass"
    assert payload["trace_analytics"]["body_in_receipt"] is False
    assert payload["trace_analytics"]["route_lease_mode_control_counts"][
        "full_output_kernel_bloat"
    ] == 1
    assert payload["source_module_manifest"]["status"] == "pass"
    assert payload["source_module_manifest"]["body_in_receipt"] is False
    assert payload["exact_source_body_import"]["body_in_receipt"] is False
    assert payload["exact_source_body_import"]["source_body_digests"] == (
        payload["exact_source_body_import"]["target_body_digests"]
    )
    assert len(payload["exact_source_body_import"]["source_body_digests"]) == 7
    sanitized_import = payload["public_reference_sanitized_body_import"]
    assert sanitized_import["body_in_receipt"] is False
    assert sanitized_import["source_body_digests"] != (
        sanitized_import["target_body_digests"]
    )
    assert sanitized_import["sanitization_receipts"][0]["public_safe"] is True
    assert sanitized_import["sanitization_receipts"][0]["blocker_count"] == 0
    assert "matched_excerpt" not in _walk_keys(payload)
    assert "body" not in _walk_keys(payload)
    for hit in payload["private_state_scan"]["hits"]:
        assert hit["body_redacted"] is True
        assert not Path(hit["path"]).is_absolute()


def test_session_attribution_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_session_attribution_bundle(
        SESSION_ATTRIBUTION_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_session_attribution_bundle"
    assert result["bundle_id"] == "public_agent_session_attribution_runtime_example"
    assert result["session_attribution_view_schema"] == SESSION_ATTRIBUTION_SCHEMA_VERSION
    assert result["active_session_count"] == 5
    assert result["workledger_session_count"] == 4
    assert result["attributed_session_count"] == 6
    assert result["matched_session_count"] == 2
    assert result["self_session_id"] == "019dc1ab-cdef-7000-aaaa-000000000000"
    assert result["copied_macro_source_count"] == 1
    assert result["source_module_manifest"]["status"] == "pass"
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_expected_line_counts_matched"] is True
    assert result["source_module_manifest"]["body_in_receipt"] is False
    body_import = result["body_import_verification"]
    assert body_import["verification_status"] == "pass"
    assert body_import["verification_mode"] == "exact_source_digest_match"
    assert body_import["source_body_digest"] == body_import["target_body_digest"]
    assert result["summary"]["by_attribution_status"] == {
        "matched": 2,
        "ats_only": 1,
        "workledger_only": 1,
        "unattributable": 1,
        "infrastructure": 1,
    }
    assert result["summary"]["by_liveness"] == {"live": 4, "recent": 2}
    assert result["authority_ceiling"]["live_home_session_logs_read"] is False
    assert result["authority_ceiling"]["raw_transcript_body_exported"] is False
    assert result["authority_ceiling"]["provider_payload_read"] is False
    assert result["authority_ceiling"]["account_session_state_exported"] is False
    assert result["private_state_scan"]["blocking_hit_count"] == 0
    assert result["session_input_validation"]["metadata_envelope_only"] is True
    assert result["attribution_policy"]["forbidden_authority_rejected"] is True
    assert result["expected_summary_validation"]["self_session_id"] == (
        "019dc1ab-cdef-7000-aaaa-000000000000"
    )
    assert all(row["raw_transcript_body_exported"] is False for row in result["session_rows"])
    assert all(row["transcript_path_exported"] is False for row in result["session_rows"])


def test_session_attribution_exported_bundle_receipt_is_public_safe(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_route_observability_runtime",
        public_root / "examples/agent_route_observability_runtime",
    )

    result = run_session_attribution_bundle(
        public_root
        / "examples/agent_route_observability_runtime/exported_session_attribution_bundle",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == [EXPORTED_SESSION_ATTRIBUTION_BUNDLE_RECEIPT_PATH]
    receipt_file = public_root / EXPORTED_SESSION_ATTRIBUTION_BUNDLE_RECEIPT_PATH
    assert receipt_file.is_file()
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "/private/var" not in text
    assert "src/ai_workflow" not in text
    assert "raw_transcript_body" not in _walk_keys(payload)
    assert "provider_payload" not in _walk_keys(payload)
    assert "account_session_state" not in _walk_keys(payload)
    assert "credential_value" not in _walk_keys(payload)
    assert payload["status"] == "pass"
    assert payload["input_mode"] == "exported_session_attribution_bundle"
    assert payload["metadata_envelope_only"] is True
    assert payload["raw_transcript_body_exported"] is False
    assert payload["provider_payload_exported"] is False
    assert payload["account_session_state_exported"] is False
    assert payload["copied_macro_source_count"] == 1
    assert payload["source_module_manifest"]["body_in_receipt"] is False
    assert payload["body_import_verification"]["source_body_digest"] == (
        payload["body_import_verification"]["target_body_digest"]
    )
    assert payload["private_state_scan"]["blocking_hit_count"] == 0
    assert payload["authority_ceiling"]["release_authorized"] is False
    for hit in payload["private_state_scan"]["hits"]:
        assert hit["body_redacted"] is True
        assert not Path(hit["path"]).is_absolute()


def test_harness_configuration_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_harness_configuration_audit_bundle(
        HARNESS_CONFIGURATION_AUDIT_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_harness_configuration_audit_bundle"
    assert result["bundle_id"] == "public_agent_harness_configuration_audit_runtime_example"
    assert result["snapshot_count"] == 3
    assert result["clean_snapshot_count"] == 1
    assert result["finding_count"] == 2
    assert result["quarantined_snapshot_count"] == 1
    assert result["summary"]["code_counts"] == {
        "INVALID_SKILL_TYPE": 1,
        "MISSING_STOP_HOOK_TIMEOUT": 1,
    }
    assert result["copied_macro_source_count"] == 2
    assert result["source_module_manifest"]["status"] == "pass"
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_expected_line_counts_matched"] is True
    assert result["source_module_manifest"]["body_in_receipt"] is False
    assert result["harness_input_validation"]["metadata_envelope_only"] is True
    assert result["harness_policy"]["forbidden_authority_rejected"] is True
    assert result["authority_ceiling"]["live_local_settings_read"] is False
    assert result["authority_ceiling"]["raw_settings_body_exported"] is False
    assert result["authority_ceiling"]["raw_hook_body_exported"] is False
    assert result["authority_ceiling"]["raw_skill_body_exported"] is False
    assert result["authority_ceiling"]["credential_or_cookie_exported"] is False
    assert result["private_state_scan"]["blocking_hit_count"] == 0
    assert result["exact_source_body_import"]["body_in_receipt"] is False
    assert result["exact_source_body_import"]["source_body_digests"] == (
        result["exact_source_body_import"]["target_body_digests"]
    )
    assert all(row["raw_settings_body_exported"] is False for row in result["snapshot_rows"])
    assert all(row["raw_hook_body_exported"] is False for row in result["snapshot_rows"])
    assert all(row["raw_skill_body_exported"] is False for row in result["snapshot_rows"])


def test_harness_configuration_exported_bundle_receipt_is_public_safe(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_route_observability_runtime",
        public_root / "examples/agent_route_observability_runtime",
    )

    result = run_harness_configuration_audit_bundle(
        public_root
        / "examples/agent_route_observability_runtime/exported_harness_configuration_audit_bundle",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == [
        EXPORTED_HARNESS_CONFIGURATION_AUDIT_BUNDLE_RECEIPT_PATH
    ]
    receipt_file = public_root / EXPORTED_HARNESS_CONFIGURATION_AUDIT_BUNDLE_RECEIPT_PATH
    assert receipt_file.is_file()
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "/private/var" not in text
    assert "src/ai_workflow" not in text
    assert "raw_settings_body" not in _walk_keys(payload)
    assert "raw_hook_body" not in _walk_keys(payload)
    assert "raw_skill_body" not in _walk_keys(payload)
    assert "provider_payload" not in _walk_keys(payload)
    assert "credential_value" not in _walk_keys(payload)
    assert payload["status"] == "pass"
    assert payload["input_mode"] == "exported_harness_configuration_audit_bundle"
    assert payload["metadata_envelope_only"] is True
    assert payload["live_local_settings_read"] is False
    assert payload["raw_settings_body_exported"] is False
    assert payload["raw_hook_body_exported"] is False
    assert payload["raw_skill_body_exported"] is False
    assert payload["copied_macro_source_count"] == 2
    assert payload["source_module_manifest"]["body_in_receipt"] is False
    assert payload["exact_source_body_import"]["source_body_digests"] == (
        payload["exact_source_body_import"]["target_body_digests"]
    )
    assert payload["private_state_scan"]["blocking_hit_count"] == 0


def test_multi_agent_fanin_replay_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    source = MICROCOSM_ROOT.parent / "system/lib/continuation_packet.py"
    target = MICROCOSM_ROOT / "src/microcosm_core/macro_tools/continuation_packet.py"
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
    result = run_multi_agent_fanin_bundle(
        MULTI_AGENT_FANIN_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_multi_agent_fanin_replay_bundle"
    assert result["bundle_id"] == "public_multi_agent_fanin_replay_runtime_example"
    assert result["continuation_packet_schema"] == CONTINUATION_PACKET_SCHEMA_VERSION
    assert result["continuation_packet_count"] == 2
    assert result["worker_trace_count"] == 2
    assert result["fanin_join_count"] == 1
    assert result["wait_kinds"] == ["pipeline_signal", "resume_contract"]
    assert len(result["continuation_packet_fingerprints"]) == 2
    assert result["authority_ceiling"]["live_bridge_dispatch_authorized"] is False
    assert result["authority_ceiling"]["raw_worker_transcript_exported"] is False
    assert result["authority_ceiling"]["recipient_send_authorized"] is False
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["source_module_manifest"]["status"] == "pass"
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_expected_line_counts_matched"] is True
    assert result["copied_macro_source_count"] == 1
    assert result["fanin_input_validation"]["metadata_envelope_only"] is True
    assert result["fanin_input_validation"]["worker_boundary_count"] == 2
    assert (
        result["fanin_input_validation"]["controller_integrated_report_count"] == 2
    )
    assert result["fanin_input_validation"]["up_propagation_count"] == 2
    assert result["fanin_policy"]["forbidden_authority_rejected"] is True
    assert result["fanin_policy"]["shared_subagent_governance_validated"] is True
    assert "codex/doctrine/paper_modules/claude_subagent_delegation.md" in result[
        "fanin_policy"
    ]["shared_subagent_governance_source_refs"]
    assert result["expected_summary_validation"]["actual_summary"][
        "continuation_packet_count"
    ] == 2
    assert result["expected_summary_validation"]["actual_summary"][
        "worker_boundary_count"
    ] == 2
    assert result["expected_summary_validation"]["actual_summary"][
        "controller_integrated_report_count"
    ] == 2
    assert result["expected_summary_validation"]["actual_summary"][
        "up_propagation_count"
    ] == 2
    body_import = result["body_import_verification"]
    assert body_import["verification_status"] == "verified"
    assert body_import["verification_mode"] == "verified_light_edit_recipe"
    assert body_import["source_to_target_relation"] == (
        "source_faithful_public_light_edit"
    )
    assert body_import["source_ref"] == "system/lib/continuation_packet.py"
    assert body_import["target_ref"] == (
        "microcosm-substrate/src/microcosm_core/macro_tools/continuation_packet.py"
    )
    assert body_import["source_body_digest"] == f"sha256:{source_digest}"
    assert body_import["target_body_digest"] == f"sha256:{target_digest}"
    assert body_import["body_in_receipt"] is False
    assert result["exact_source_body_import"]["verification_mode"] == (
        "exact_source_digest_match"
    )
    assert result["exact_source_body_import"]["source_ref"] == (
        "system/lib/continuation_packet.py"
    )
    assert result["exact_source_body_import"]["source_body_digest"] == (
        result["exact_source_body_import"]["target_body_digest"]
    )
    assert all(
        row["decision"] == "accepted" for row in result["worker_trace_decisions"]
    )


def test_multi_agent_fanin_replay_receipt_is_public_safe(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_route_observability_runtime",
        public_root / "examples/agent_route_observability_runtime",
    )

    result = run_multi_agent_fanin_bundle(
        public_root
        / "examples/agent_route_observability_runtime/exported_multi_agent_fanin_replay_bundle",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == [EXPORTED_MULTI_AGENT_FANIN_BUNDLE_RECEIPT_PATH]
    receipt_file = public_root / EXPORTED_MULTI_AGENT_FANIN_BUNDLE_RECEIPT_PATH
    assert receipt_file.is_file()
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "/private/var" not in text
    assert "src/ai_workflow" not in text
    assert "raw_worker_transcript_body" not in _walk_keys(payload)
    assert "provider_payload" not in _walk_keys(payload)
    assert "account_session_state" not in _walk_keys(payload)
    assert "credential_value" not in _walk_keys(payload)
    assert payload["status"] == "pass"
    assert payload["input_mode"] == "exported_multi_agent_fanin_replay_bundle"
    assert payload["metadata_envelope_only"] is True
    assert payload["raw_worker_transcript_exported"] is False
    assert payload["provider_payload_exported"] is False
    assert payload["browser_hud_cockpit_state_exported"] is False
    assert payload["account_session_state_exported"] is False
    assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
    assert payload["source_module_manifest"]["body_in_receipt"] is False
    assert payload["exact_source_body_import"]["body_in_receipt"] is False
    assert payload["authority_ceiling"]["release_authorized"] is False
    for hit in payload["secret_exclusion_scan"]["hits"]:
        assert hit["body_in_receipt"] is False
        assert not Path(hit["path"]).is_absolute()


def test_multi_agent_fanin_imports_exact_continuation_packet_source_body() -> None:
    source = MICROCOSM_ROOT.parent / "system/lib/continuation_packet.py"
    bundle_source = (
        MULTI_AGENT_FANIN_BUNDLE_INPUT
        / "source_modules/system/lib/continuation_packet.py"
    )
    manifest = json.loads(
        (MULTI_AGENT_FANIN_BUNDLE_INPUT / "source_module_manifest.json").read_text()
    )
    row = manifest["modules"][0]
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    bundle_source_digest = hashlib.sha256(bundle_source.read_bytes()).hexdigest()
    bundle_source_text = bundle_source.read_text(encoding="utf-8")

    assert bundle_source.is_file()
    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert row["source_ref"] == "system/lib/continuation_packet.py"
    assert row["path"] == "source_modules/system/lib/continuation_packet.py"
    assert row["material_class"] == "public_macro_tool_body"
    assert row["body_in_receipt"] is False
    assert row["sha256"] == source_digest
    assert row["sha256"] == bundle_source_digest
    assert "def build_continuation_packet(" in bundle_source_text
    assert "def write_continuation_packet(" in bundle_source_text
    compile(bundle_source_text, str(bundle_source), "exec")


def test_bridge_dispatch_yield_resume_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    source = MICROCOSM_ROOT.parent / BRIDGE_DISPATCH_YIELD_RESUME_SOURCE_REF
    target = MICROCOSM_ROOT / BRIDGE_DISPATCH_YIELD_RESUME_TARGET_REF.removeprefix(
        "microcosm-substrate/"
    )
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
    result = run_bridge_dispatch_yield_resume_bundle(
        BRIDGE_DISPATCH_YIELD_RESUME_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_bridge_dispatch_yield_resume_bundle"
    assert result["bundle_id"] == "public_bridge_dispatch_yield_resume_runtime_example"
    assert result["bridge_resume_schema"] == BRIDGE_DISPATCH_YIELD_RESUME_SCHEMA_VERSION
    assert result["target_count"] == 2
    assert result["resume_job_count"] == 2
    assert result["trigger_written_count"] == 2
    assert result["no_send_trigger_count"] == 2
    assert result["skipped_dup_count"] == 1
    assert result["safe_to_inject_count"] == 1
    assert result["blocked_activity_count"] == 1
    assert result["controller_heartbeat_ref_count"] == 2
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["source_module_manifest"]["status"] == "pass"
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_expected_line_counts_matched"] is True
    assert result["source_module_manifest"]["body_in_receipt"] is False
    assert result["copied_macro_source_count"] == 1
    assert result["bridge_policy_validation"]["forbidden_authority_rejected"] is True
    assert result["authority_ceiling"]["live_bridge_dispatch_authorized"] is False
    assert result["authority_ceiling"]["host_app_auto_inject_authorized"] is False
    assert result["authority_ceiling"]["recipient_send_authorized"] is False
    assert all(row["submit"] is False for row in result["public_trigger_rows"])
    assert {
        row["reason"] for row in result["activity_reports"]
    } == {"already_injected", "no_delta"}
    assert result["body_import_verification"]["verification_status"] == "verified"
    assert result["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )
    assert result["body_import_verification"]["source_ref"] == (
        BRIDGE_DISPATCH_YIELD_RESUME_SOURCE_REF
    )
    assert result["body_import_verification"]["target_ref"] == (
        BRIDGE_DISPATCH_YIELD_RESUME_TARGET_REF
    )
    assert result["body_import_verification"]["source_body_digest"] == (
        f"sha256:{source_digest}"
    )
    assert result["body_import_verification"]["target_body_digest"] == (
        f"sha256:{target_digest}"
    )
    assert result["exact_source_body_import"]["verification_mode"] == (
        "exact_source_digest_match"
    )
    assert result["exact_source_body_import"]["source_ref"] == (
        "tools/meta/bridge/bridge_resume.py"
    )
    assert result["exact_source_body_import"]["source_body_digest"] == (
        result["exact_source_body_import"]["target_body_digest"]
    )


def test_bridge_dispatch_yield_resume_loader_rejects_duplicate_json_keys(
    tmp_path: Path,
) -> None:
    bundle_input = tmp_path / "exported_bridge_dispatch_yield_resume_bundle"
    shutil.copytree(BRIDGE_DISPATCH_YIELD_RESUME_BUNDLE_INPUT, bundle_input)
    (bundle_input / "bundle_manifest.json").write_text(
        '{"bundle_id":"bridge_resume_a","bundle_id":"bridge_resume_b"}',
        encoding="utf-8",
    )

    with pytest.raises(DuplicateJsonKeyError):
        load_public_bridge_dispatch_yield_resume_bundle(bundle_input)


def test_bridge_dispatch_yield_resume_receipt_is_public_safe(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_route_observability_runtime",
        public_root / "examples/agent_route_observability_runtime",
    )

    result = run_bridge_dispatch_yield_resume_bundle(
        public_root
        / "examples/agent_route_observability_runtime/"
        "exported_bridge_dispatch_yield_resume_bundle",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == [
        EXPORTED_BRIDGE_DISPATCH_YIELD_RESUME_BUNDLE_RECEIPT_PATH
    ]
    receipt_file = public_root / EXPORTED_BRIDGE_DISPATCH_YIELD_RESUME_BUNDLE_RECEIPT_PATH
    assert receipt_file.is_file()
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "/private/var" not in text
    assert "src/ai_workflow" not in text
    assert "raw_worker_transcript_body" not in _walk_keys(payload)
    assert "raw_bridge_transcript" not in _walk_keys(payload)
    assert "provider_payload" not in _walk_keys(payload)
    assert "account_session_state" not in _walk_keys(payload)
    assert "credential_value" not in _walk_keys(payload)
    assert payload["status"] == "pass"
    assert payload["input_mode"] == "exported_bridge_dispatch_yield_resume_bundle"
    assert payload["metadata_envelope_only"] is True
    assert payload["live_bridge_dispatch_authorized"] is False
    assert payload["host_app_auto_inject_authorized"] is False
    assert payload["recipient_send_authorized"] is False
    assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
    assert payload["source_module_manifest"]["body_in_receipt"] is False
    assert payload["exact_source_body_import"]["body_in_receipt"] is False
    assert payload["authority_ceiling"]["release_authorized"] is False
    for hit in payload["secret_exclusion_scan"]["hits"]:
        assert hit["body_in_receipt"] is False
        assert not Path(hit["path"]).is_absolute()


def test_bridge_dispatch_imports_exact_bridge_resume_source_body() -> None:
    source = MICROCOSM_ROOT.parent / "tools/meta/bridge/bridge_resume.py"
    bundle_source = (
        BRIDGE_DISPATCH_YIELD_RESUME_BUNDLE_INPUT
        / "source_modules/tools/meta/bridge/bridge_resume.py"
    )
    manifest = json.loads(
        (
            BRIDGE_DISPATCH_YIELD_RESUME_BUNDLE_INPUT / "source_module_manifest.json"
        ).read_text()
    )
    row = manifest["modules"][0]
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    bundle_source_digest = hashlib.sha256(bundle_source.read_bytes()).hexdigest()
    bundle_source_text = bundle_source.read_text(encoding="utf-8")

    assert bundle_source.is_file()
    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert row["source_ref"] == "tools/meta/bridge/bridge_resume.py"
    assert row["path"] == "source_modules/tools/meta/bridge/bridge_resume.py"
    assert row["material_class"] == "public_macro_tool_body"
    assert row["body_in_receipt"] is False
    assert row["sha256"] == source_digest
    assert row["sha256"] == bundle_source_digest
    assert "class BridgeResumeManager" in bundle_source_text
    assert "def bridge_dispatch_and_yield(" in bundle_source_text
    compile(bundle_source_text, str(bundle_source), "exec")


def test_bridge_resume_imports_public_macro_body_refactor() -> None:
    source = MICROCOSM_ROOT.parent / BRIDGE_DISPATCH_YIELD_RESUME_SOURCE_REF
    target = MICROCOSM_ROOT / BRIDGE_DISPATCH_YIELD_RESUME_TARGET_REF.removeprefix(
        "microcosm-substrate/"
    )
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
    view = build_public_bridge_dispatch_yield_resume_view(
        load_public_bridge_dispatch_yield_resume_bundle(
            BRIDGE_DISPATCH_YIELD_RESUME_BUNDLE_INPUT
        )
    )
    protocol = json.loads(
        (
            MICROCOSM_ROOT
            / "examples/macro_projection_import_protocol/exported_projection_import_bundle/projection_protocol.json"
        ).read_text(encoding="utf-8")
    )
    by_material = {row["material_id"]: row for row in protocol["copied_material"]}
    material = by_material["bridge_resume_body_import"]

    assert target.is_file()
    assert source_digest != target_digest
    assert view["status"] == "pass"
    assert view["schema_version"] == BRIDGE_DISPATCH_YIELD_RESUME_SCHEMA_VERSION
    assert view["summary"]["trigger_written_count"] == 2
    assert view["authority_ceiling"]["live_bridge_dispatch_authorized"] is False
    assert view["body_import_verification"]["verification_status"] == "verified"
    assert view["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )
    assert view["body_import_verification"]["source_to_target_relation"] == (
        "source_faithful_public_light_edit"
    )
    assert view["body_import_verification"]["source_ref"] == (
        BRIDGE_DISPATCH_YIELD_RESUME_SOURCE_REF
    )
    assert view["body_import_verification"]["target_ref"] == (
        BRIDGE_DISPATCH_YIELD_RESUME_TARGET_REF
    )
    assert view["body_import_verification"]["source_body_digest"] == (
        f"sha256:{source_digest}"
    )
    assert view["body_import_verification"]["target_body_digest"] == (
        f"sha256:{target_digest}"
    )
    assert view["body_import_verification"]["body_in_receipt"] is False
    assert material["body_import_verification"]["source_body_digest"] == (
        f"sha256:{source_digest}"
    )
    assert material["body_import_verification"]["target_body_digest"] == (
        f"sha256:{target_digest}"
    )
    assert material["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )


def test_controller_heartbeat_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_controller_heartbeat_bundle(
        CONTROLLER_HEARTBEAT_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_controller_heartbeat_bundle"
    assert result["bundle_id"] == "public_controller_heartbeat_runtime_example"
    assert result["controller_heartbeat_schema"] == CONTROLLER_HEARTBEAT_SCHEMA_VERSION
    assert result["heartbeat_count"] == 2
    assert result["valid_heartbeat_count"] == 2
    assert result["exact_5x5_count"] == 2
    assert result["heartbeat_ref_count"] == 2
    assert result["semantic_event_stable_count"] == 2
    assert result["semantic_event_changed_count"] == 2
    assert result["legacy_problem_regenerated_count"] == 1
    assert result["wrapped_schema_count"] == 2
    assert result["idempotent_wrap_count"] == 2
    assert result["dedupe_duplicate_count"] == 1
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["source_module_manifest"]["status"] == "pass"
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_expected_line_counts_matched"] is True
    assert result["source_module_manifest"]["all_expected_byte_counts_matched"] is True
    assert result["source_module_manifest"]["body_in_receipt"] is False
    assert result["copied_macro_source_count"] == 1
    assert result["exact_source_body_import"]["verification_mode"] == (
        "exact_source_digest_match"
    )
    assert result["exact_source_body_import"]["source_body_digest"] == (
        result["exact_source_body_import"]["target_body_digest"]
    )
    assert result["controller_heartbeat_policy"]["forbidden_authority_rejected"] is True
    assert result["authority_ceiling"]["seed_or_blackboard_read_authorized"] is False
    assert result["authority_ceiling"]["work_ledger_runtime_read_authorized"] is False
    assert result["authority_ceiling"]["provider_payload_read"] is False
    assert result["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )
    assert result["body_import_verification"]["target_ref"] == (
        "microcosm-substrate/src/microcosm_core/macro_tools/controller_heartbeat.py"
    )


def test_controller_heartbeat_loader_rejects_duplicate_json_keys(
    tmp_path: Path,
) -> None:
    bundle_input = tmp_path / "exported_controller_heartbeat_bundle"
    shutil.copytree(CONTROLLER_HEARTBEAT_BUNDLE_INPUT, bundle_input)
    (bundle_input / "bundle_manifest.json").write_text(
        '{"bundle_id":"controller_heartbeat_a","bundle_id":"controller_heartbeat_b"}',
        encoding="utf-8",
    )

    with pytest.raises(DuplicateJsonKeyError):
        load_public_controller_heartbeat_bundle(bundle_input)


def test_controller_heartbeat_receipt_is_public_safe(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_route_observability_runtime",
        public_root / "examples/agent_route_observability_runtime",
    )

    result = run_controller_heartbeat_bundle(
        public_root
        / "examples/agent_route_observability_runtime/"
        "exported_controller_heartbeat_bundle",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == [EXPORTED_CONTROLLER_HEARTBEAT_BUNDLE_RECEIPT_PATH]
    receipt_file = public_root / EXPORTED_CONTROLLER_HEARTBEAT_BUNDLE_RECEIPT_PATH
    assert receipt_file.is_file()
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "/private/var" not in text
    assert "src/ai_workflow" not in text
    assert "seed_body" not in _walk_keys(payload)
    assert "mission_blackboard_body" not in _walk_keys(payload)
    assert "work_ledger_runtime_body" not in _walk_keys(payload)
    assert "provider_payload" not in _walk_keys(payload)
    assert "account_session_state" not in _walk_keys(payload)
    assert "credential_value" not in _walk_keys(payload)
    assert payload["status"] == "pass"
    assert payload["input_mode"] == "exported_controller_heartbeat_bundle"
    assert payload["metadata_envelope_only"] is True
    assert payload["body_in_receipt"] is False
    assert payload["seed_or_blackboard_read_authorized"] is False
    assert payload["work_ledger_runtime_read_authorized"] is False
    assert payload["recipient_send_authorized"] is False
    assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
    assert payload["source_module_manifest"]["body_in_receipt"] is False
    assert payload["copied_macro_source_count"] == 1
    assert payload["exact_source_body_import"]["body_in_receipt"] is False
    assert payload["exact_source_body_import"]["source_body_digest"] == (
        payload["exact_source_body_import"]["target_body_digest"]
    )
    assert payload["authority_ceiling"]["release_authorized"] is False
    for hit in payload["secret_exclusion_scan"]["hits"]:
        assert hit["body_in_receipt"] is False
        assert not Path(hit["path"]).is_absolute()


def test_controller_heartbeat_imports_public_macro_body_refactor() -> None:
    source = MICROCOSM_ROOT.parent / "system/lib/controller_heartbeat.py"
    bundle_source = (
        CONTROLLER_HEARTBEAT_BUNDLE_INPUT
        / "source_modules/system/lib/controller_heartbeat.py"
    )
    target = MICROCOSM_ROOT / "src/microcosm_core/macro_tools/controller_heartbeat.py"
    manifest = json.loads(
        (CONTROLLER_HEARTBEAT_BUNDLE_INPUT / "source_module_manifest.json").read_text()
    )
    row = manifest["modules"][0]
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    bundle_source_digest = hashlib.sha256(bundle_source.read_bytes()).hexdigest()
    target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
    bundle_source_text = bundle_source.read_text(encoding="utf-8")
    view = build_public_controller_heartbeat_view(
        load_public_controller_heartbeat_bundle(CONTROLLER_HEARTBEAT_BUNDLE_INPUT)
    )
    protocol = json.loads(
        (
            MICROCOSM_ROOT
            / "examples/macro_projection_import_protocol/exported_projection_import_bundle/projection_protocol.json"
        ).read_text(encoding="utf-8")
    )
    by_material = {row["material_id"]: row for row in protocol["copied_material"]}
    material = by_material["controller_heartbeat_body_import"]

    assert target.is_file()
    assert bundle_source.is_file()
    assert source_digest != target_digest
    assert source_digest == bundle_source_digest
    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert row["source_ref"] == "system/lib/controller_heartbeat.py"
    assert row["path"] == "source_modules/system/lib/controller_heartbeat.py"
    assert row["material_class"] == "public_macro_tool_body"
    assert row["body_in_receipt"] is False
    assert row["sha256"] == source_digest
    assert row["sha256"] == bundle_source_digest
    assert "def build_controller_heartbeat(" in bundle_source_text
    assert "def validate_controller_heartbeat(" in bundle_source_text
    compile(bundle_source_text, str(bundle_source), "exec")
    assert view["status"] == "pass"
    assert view["controller_heartbeat_schema"] == CONTROLLER_HEARTBEAT_SCHEMA_VERSION
    assert view["summary"]["exact_5x5_count"] == 2
    assert view["summary"]["dedupe_duplicate_count"] == 1
    assert view["authority_ceiling"]["seed_or_blackboard_read_authorized"] is False
    for heartbeat in view["controller_heartbeats"]:
        assert all(
            count_sentences(heartbeat[field]) == 5
            for field in CONTROLLER_HEARTBEAT_FIELDS
        )
    assert material["body_import_verification"]["source_body_digest"] == (
        f"sha256:{source_digest}"
    )
    assert material["body_import_verification"]["target_body_digest"] == (
        f"sha256:{target_digest}"
    )
    assert material["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )


def test_agent_trace_route_repair_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_agent_trace_route_repair_bundle(
        AGENT_TRACE_ROUTE_REPAIR_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_agent_trace_route_repair_bundle"
    assert result["bundle_id"] == "public_agent_trace_route_repair_runtime_example"
    assert result["agent_trace_route_repair_schema"] == (
        AGENT_TRACE_ROUTE_REPAIR_SCHEMA_VERSION
    )
    assert result["top_pattern_count"] == 4
    assert result["covered_top_pattern_count"] == 4
    assert result["would_intervene_on_recent_route_failures"] == 4
    assert result["suggested_route_count"] == 4
    assert result["public_trace_ref_count"] == 7
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["authority_ceiling"]["live_hook_install_authorized"] is False
    assert result["authority_ceiling"]["provider_payload_read"] is False
    assert result["authority_ceiling"]["hidden_reasoning_exported"] is False
    assert result["route_repair_policy"]["forbidden_authority_rejected"] is True
    assert result["expected_summary_validation"]["status"] == "pass"
    assert result["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )
    source_manifest = result["source_module_manifest"]
    exact_import = result["exact_source_body_import"]
    assert source_manifest["status"] == "pass"
    assert source_manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert source_manifest["body_in_receipt"] is False
    assert source_manifest["module_count"] == 4
    assert source_manifest["required_module_count"] == 3
    assert source_manifest["copied_macro_source_count"] == 3
    assert source_manifest["all_expected_digests_matched"] is True
    assert source_manifest["all_expected_line_counts_matched"] is True
    assert source_manifest["all_expected_byte_counts_matched"] is True
    assert result["copied_macro_source_count"] == 3
    assert exact_import["verification_status"] == "pass"
    assert exact_import["verification_mode"] == "exact_source_digest_match"
    assert exact_import["source_to_target_relation"] == "exact_copy"
    assert exact_import["body_in_receipt"] is False
    assert exact_import["source_body_digests"] == exact_import["target_body_digests"]
    assert len(exact_import["source_body_digests"]) == 3
    assert all(
        str(digest).startswith("sha256:")
        for digest in exact_import["source_body_digests"]
    )
    assert {
        row["anti_pattern_id"] for row in result["route_repair_rows"]
    } == {
        "anti_pattern_grep_before_kernel",
        "anti_pattern_cold_boot_missing_info",
        "anti_pattern_deep_without_ladder",
        "phase_residual_exception_narration",
    }
    cold_boot = next(
        row
        for row in result["route_repair_rows"]
        if row["anti_pattern_id"] == "anti_pattern_cold_boot_missing_info"
    )
    assert cold_boot["suggested_sequence"] == [
        "./repo-python kernel.py --info",
        "./repo-python kernel.py --preflight",
        "./repo-python kernel.py --pulse",
        './repo-python kernel.py --entry "<task>" --context-budget 12000',
    ]


def test_agent_trace_route_repair_loader_rejects_duplicate_json_keys(
    tmp_path: Path,
) -> None:
    bundle_input = tmp_path / "exported_agent_trace_route_repair_bundle"
    shutil.copytree(AGENT_TRACE_ROUTE_REPAIR_BUNDLE_INPUT, bundle_input)
    (bundle_input / "bundle_manifest.json").write_text(
        '{"bundle_id":"route_repair_a","bundle_id":"route_repair_b"}',
        encoding="utf-8",
    )

    with pytest.raises(DuplicateJsonKeyError):
        load_public_agent_trace_route_repair_bundle(bundle_input)


def test_agent_trace_route_repair_receipt_is_public_safe(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_route_observability_runtime",
        public_root / "examples/agent_route_observability_runtime",
    )

    result = run_agent_trace_route_repair_bundle(
        public_root
        / "examples/agent_route_observability_runtime/"
        "exported_agent_trace_route_repair_bundle",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == [
        EXPORTED_AGENT_TRACE_ROUTE_REPAIR_BUNDLE_RECEIPT_PATH
    ]
    receipt_file = public_root / EXPORTED_AGENT_TRACE_ROUTE_REPAIR_BUNDLE_RECEIPT_PATH
    assert receipt_file.is_file()
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "/private/var" not in text
    assert "src/ai_workflow" not in text
    assert "raw_transcript_body" not in _walk_keys(payload)
    assert "provider_payload" not in _walk_keys(payload)
    assert "hidden_reasoning" not in _walk_keys(payload)
    assert "browser_hud_state" not in _walk_keys(payload)
    assert "account_session_state" not in _walk_keys(payload)
    assert "credential_value" not in _walk_keys(payload)
    assert payload["status"] == "pass"
    assert payload["input_mode"] == "exported_agent_trace_route_repair_bundle"
    assert payload["metadata_envelope_only"] is True
    assert payload["body_in_receipt"] is False
    assert payload["source_module_manifest"]["status"] == "pass"
    assert payload["source_module_manifest"]["body_in_receipt"] is False
    assert payload["copied_macro_source_count"] == 3
    assert payload["exact_source_body_import"]["verification_mode"] == (
        "exact_source_digest_match"
    )
    assert payload["exact_source_body_import"]["body_in_receipt"] is False
    assert payload["exact_source_body_import"]["source_body_digests"] == (
        payload["exact_source_body_import"]["target_body_digests"]
    )
    assert payload["live_hook_install_authorized"] is False
    assert payload["live_route_repair_authorized"] is False
    assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
    assert payload["authority_ceiling"]["release_authorized"] is False
    for hit in payload["secret_exclusion_scan"]["hits"]:
        assert hit["body_in_receipt"] is False
        assert not Path(hit["path"]).is_absolute()


def test_agent_trace_route_repair_imports_public_macro_body_refactor() -> None:
    source = MICROCOSM_ROOT.parent / "system/lib/navigation_route_intervention.py"
    target = MICROCOSM_ROOT / "src/microcosm_core/macro_tools/agent_trace_route_repair.py"
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
    source_manifest = json.loads(
        (
            AGENT_TRACE_ROUTE_REPAIR_BUNDLE_INPUT / "source_module_manifest.json"
        ).read_text(encoding="utf-8")
    )
    source_modules = {
        "source_modules/system/lib/navigation_route_intervention.py": (
            MICROCOSM_ROOT.parent / "system/lib/navigation_route_intervention.py"
        ),
        "source_modules/system/lib/agent_execution_trace.py": (
            MICROCOSM_ROOT.parent / "system/lib/agent_execution_trace.py"
        ),
        "source_modules/system/lib/strict_json.py": (
            MICROCOSM_ROOT.parent / "system/lib/strict_json.py"
        ),
        "source_modules/codex/standards/std_agent_execution_trace.json": (
            MICROCOSM_ROOT.parent / "codex/standards/std_agent_execution_trace.json"
        ),
    }
    rows_by_path = {row["path"]: row for row in source_manifest["modules"]}
    view = build_public_agent_trace_route_repair_view(
        load_public_agent_trace_route_repair_bundle(AGENT_TRACE_ROUTE_REPAIR_BUNDLE_INPUT)
    )
    protocol = json.loads(
        (
            MICROCOSM_ROOT
            / "examples/macro_projection_import_protocol/exported_projection_import_bundle/projection_protocol.json"
        ).read_text(encoding="utf-8")
    )
    by_material = {row["material_id"]: row for row in protocol["copied_material"]}
    material = by_material["agent_trace_route_repair_body_import"]
    suggestion = route_repair_for(anti_pattern_id="grep_before_kernel")

    assert target.is_file()
    assert source_digest != target_digest
    assert source_manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert source_manifest["body_in_receipt"] is False
    assert source_manifest["module_count"] == len(source_modules)
    for bundle_path, macro_source in source_modules.items():
        bundle_source = AGENT_TRACE_ROUTE_REPAIR_BUNDLE_INPUT / bundle_path
        row = rows_by_path[bundle_path]
        bundle_text = bundle_source.read_text(encoding="utf-8")
        bundle_digest = hashlib.sha256(bundle_source.read_bytes()).hexdigest()
        assert bundle_source.is_file()
        assert bundle_digest == hashlib.sha256(macro_source.read_bytes()).hexdigest()
        assert bundle_digest == row["sha256"]
        assert row["source_import_class"] == "copied_non_secret_macro_body"
        assert row["body_in_receipt"] is False
        assert row["line_count"] == len(bundle_text.splitlines())
        assert row["byte_count"] == len(bundle_source.read_bytes())
        assert row["target_ref"].endswith(bundle_path)
        for anchor in row["required_anchors"]:
            assert anchor in bundle_text
        if bundle_path.endswith(".py"):
            compile(bundle_text, str(bundle_source), "exec")
        else:
            json.loads(bundle_text)
    assert view["status"] == "pass"
    assert view["schema_version"] == AGENT_TRACE_ROUTE_REPAIR_SCHEMA_VERSION
    assert view["route_repair_summary"]["suggested_route_count"] == 4
    assert suggestion is not None
    assert suggestion.anti_pattern_id == "anti_pattern_grep_before_kernel"
    assert material["body_import_verification"]["source_body_digest"] == (
        f"sha256:{source_digest}"
    )
    assert view["body_import_verification"]["target_body_digest"] == (
        f"sha256:{target_digest}"
    )
    assert view["body_import_verification"]["source_to_target_relation"] == (
        "source_faithful_public_light_edit"
    )
    assert material["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )


def test_agent_observability_store_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_agent_observability_store_bundle(
        AGENT_OBSERVABILITY_STORE_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_agent_observability_store_bundle"
    assert result["bundle_id"] == "public_agent_observability_store_runtime_example"
    assert result["agent_observability_store_schema"] == (
        AGENT_OBSERVABILITY_STORE_SCHEMA_VERSION
    )
    assert result["public_event_count"] == 6
    assert result["accepted_event_count"] == 6
    assert result["active_session_count"] == 3
    assert result["source_runtime_count"] == 3
    assert result["route_decision_event_count"] == 3
    assert result["tool_event_count"] == 2
    assert result["metadata_digest_count"] == 6
    assert result["redacted_payload_count"] == 3
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["authority_ceiling"]["live_home_session_logs_read"] is False
    assert result["authority_ceiling"]["provider_payload_read"] is False
    assert result["authority_ceiling"]["browser_hud_cockpit_state_exported"] is False
    assert result["observability_policy"]["forbidden_authority_rejected"] is True
    assert result["expected_summary_validation"]["status"] == "pass"
    assert result["source_module_manifest"]["status"] == "pass"
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_expected_line_counts_matched"] is True
    assert result["source_module_manifest"]["all_expected_byte_counts_matched"] is True
    assert result["source_module_manifest"]["body_in_receipt"] is False
    assert result["copied_macro_source_count"] == 2
    assert result["exact_source_body_import"]["verification_mode"] == (
        "exact_source_digest_match"
    )
    assert result["exact_source_body_import"]["source_body_digest"] == (
        result["exact_source_body_import"]["target_body_digest"]
    )
    assert len(result["exact_source_body_import"]["source_body_digests"]) == 2
    assert result["exact_source_body_import"]["source_body_digests"] == (
        result["exact_source_body_import"]["target_body_digests"]
    )
    assert result["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )
    assert all(row["decision"] == "accepted" for row in result["event_decisions"])


def test_agent_observability_store_loader_rejects_duplicate_json_keys(
    tmp_path: Path,
) -> None:
    bundle_input = tmp_path / "exported_agent_observability_store_bundle"
    shutil.copytree(AGENT_OBSERVABILITY_STORE_BUNDLE_INPUT, bundle_input)
    (bundle_input / "bundle_manifest.json").write_text(
        '{"bundle_id":"observability_store_a","bundle_id":"observability_store_b"}',
        encoding="utf-8",
    )

    with pytest.raises(DuplicateJsonKeyError):
        load_public_agent_observability_store_bundle(bundle_input)


def test_agent_observability_store_receipt_is_public_safe(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/agent_route_observability_runtime",
        public_root / "examples/agent_route_observability_runtime",
    )

    result = run_agent_observability_store_bundle(
        public_root
        / "examples/agent_route_observability_runtime/"
        "exported_agent_observability_store_bundle",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == [
        EXPORTED_AGENT_OBSERVABILITY_STORE_BUNDLE_RECEIPT_PATH
    ]
    receipt_file = public_root / EXPORTED_AGENT_OBSERVABILITY_STORE_BUNDLE_RECEIPT_PATH
    assert receipt_file.is_file()
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "/private/var" not in text
    assert "src/ai_workflow" not in text
    assert "raw_transcript_body" not in _walk_keys(payload)
    assert "provider_payload" not in _walk_keys(payload)
    assert "hidden_reasoning" not in _walk_keys(payload)
    assert "browser_hud_state" not in _walk_keys(payload)
    assert "account_session_state" not in _walk_keys(payload)
    assert "credential_value" not in _walk_keys(payload)
    assert payload["status"] == "pass"
    assert payload["input_mode"] == "exported_agent_observability_store_bundle"
    assert payload["metadata_envelope_only"] is True
    assert payload["body_in_receipt"] is False
    assert payload["live_home_session_logs_read"] is False
    assert payload["live_transcript_tail_authorized"] is False
    assert payload["operator_bridge_poll_authorized"] is False
    assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
    assert payload["source_module_manifest"]["body_in_receipt"] is False
    assert payload["copied_macro_source_count"] == 2
    assert payload["exact_source_body_import"]["body_in_receipt"] is False
    assert payload["exact_source_body_import"]["source_body_digest"] == (
        payload["exact_source_body_import"]["target_body_digest"]
    )
    assert len(payload["exact_source_body_import"]["source_body_digests"]) == 2
    assert payload["exact_source_body_import"]["source_body_digests"] == (
        payload["exact_source_body_import"]["target_body_digests"]
    )
    assert payload["authority_ceiling"]["release_authorized"] is False
    for hit in payload["secret_exclusion_scan"]["hits"]:
        assert hit["body_in_receipt"] is False
        assert not Path(hit["path"]).is_absolute()


def test_agent_observability_store_imports_public_macro_body_refactor() -> None:
    source = MICROCOSM_ROOT.parent / "system/lib/agent_observability.py"
    classification_source = (
        MICROCOSM_ROOT.parent / "system/lib/agent_observability_classification.py"
    )
    bundle_source = (
        AGENT_OBSERVABILITY_STORE_BUNDLE_INPUT
        / "source_modules/system/lib/agent_observability.py"
    )
    classification_bundle_source = (
        AGENT_OBSERVABILITY_STORE_BUNDLE_INPUT
        / "source_modules/system/lib/agent_observability_classification.py"
    )
    target = MICROCOSM_ROOT / "src/microcosm_core/macro_tools/agent_observability_store.py"
    manifest = json.loads(
        (AGENT_OBSERVABILITY_STORE_BUNDLE_INPUT / "source_module_manifest.json").read_text()
    )
    rows_by_path = {row["path"]: row for row in manifest["modules"]}
    row = rows_by_path["source_modules/system/lib/agent_observability.py"]
    classification_row = rows_by_path[
        "source_modules/system/lib/agent_observability_classification.py"
    ]
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    classification_source_digest = hashlib.sha256(
        classification_source.read_bytes()
    ).hexdigest()
    bundle_source_digest = hashlib.sha256(bundle_source.read_bytes()).hexdigest()
    classification_bundle_source_digest = hashlib.sha256(
        classification_bundle_source.read_bytes()
    ).hexdigest()
    target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
    bundle_source_text = bundle_source.read_text(encoding="utf-8")
    classification_bundle_source_text = classification_bundle_source.read_text(
        encoding="utf-8"
    )
    view = build_public_agent_observability_store_view(
        load_public_agent_observability_store_bundle(AGENT_OBSERVABILITY_STORE_BUNDLE_INPUT)
    )
    protocol = json.loads(
        (
            MICROCOSM_ROOT
            / "examples/macro_projection_import_protocol/exported_projection_import_bundle/projection_protocol.json"
        ).read_text(encoding="utf-8")
    )
    by_material = {row["material_id"]: row for row in protocol["copied_material"]}
    material = by_material["agent_observability_store_body_import"]
    store = AgentTraceStore()
    event = store.emit(
        source_runtime="public_test",
        source_event_name="unit_test",
        canonical_type="route.decision",
        session_id="s1",
        payload={"metadata_digest": "sha256:test", "target_ref": "tests"},
        observed_at="2026-05-24T10:42:00+00:00",
        summary="unit test route decision",
    )

    assert target.is_file()
    assert bundle_source.is_file()
    assert source_digest != target_digest
    assert source_digest == bundle_source_digest
    assert classification_source_digest == classification_bundle_source_digest
    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 2
    assert row["source_ref"] == "system/lib/agent_observability.py"
    assert row["path"] == "source_modules/system/lib/agent_observability.py"
    assert row["material_class"] == "public_macro_tool_body"
    assert row["body_in_receipt"] is False
    assert row["sha256"] == source_digest
    assert row["sha256"] == bundle_source_digest
    assert classification_row["source_ref"] == (
        "system/lib/agent_observability_classification.py"
    )
    assert classification_row["path"] == (
        "source_modules/system/lib/agent_observability_classification.py"
    )
    assert classification_row["material_class"] == "public_macro_tool_body"
    assert classification_row["body_in_receipt"] is False
    assert classification_row["sha256"] == classification_source_digest
    assert classification_row["sha256"] == classification_bundle_source_digest
    assert "class AgentTraceStore" in bundle_source_text
    assert "class AgentObservabilitySampler" in bundle_source_text
    assert "def classify_auth_failure_loop(" in classification_bundle_source_text
    assert "def classify_telemetry_quality(" in classification_bundle_source_text
    compile(bundle_source_text, str(bundle_source), "exec")
    compile(
        classification_bundle_source_text,
        str(classification_bundle_source),
        "exec",
    )
    assert event["seq"] == 1
    assert store.status()["canonical_counts"]["route.decision"] == 1
    assert view["status"] == "pass"
    assert view["schema_version"] == AGENT_OBSERVABILITY_STORE_SCHEMA_VERSION
    assert view["store_summary"]["event_count"] == 6
    assert view["authority_ceiling"]["live_home_session_logs_read"] is False
    assert material["body_import_verification"]["source_body_digest"] == (
        f"sha256:{source_digest}"
    )
    assert material["body_import_verification"]["target_body_digest"] == (
        f"sha256:{target_digest}"
    )
    assert material["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )


def test_continuation_packet_imports_public_macro_body_refactor() -> None:
    source = MICROCOSM_ROOT.parent / "system/lib/continuation_packet.py"
    target = MICROCOSM_ROOT / "src/microcosm_core/macro_tools/continuation_packet.py"
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    target_digest = hashlib.sha256(target.read_bytes()).hexdigest()

    packet = build_public_continuation_packet(
        wait_kind="resume_contract",
        artifact_dir=(
            "examples/agent_route_observability_runtime/"
            "exported_multi_agent_fanin_replay_bundle/demo"
        ),
        source_context={
            "current_task_id": "multi_agent_handoff_fanin_replay_compound",
            "context_refs": [
                "state/microcosm_portfolio/extracted_pattern_substrate_bindings.json#multi_agent_handoff_fanin_replay_compound"
            ],
        },
        generated_at="2026-05-24T03:55:00+00:00",
    )
    assert target.is_file()
    assert source_digest != target_digest
    assert packet["schema_version"] == CONTINUATION_PACKET_SCHEMA_VERSION
    assert packet["wait_kind"] == "resume_contract"
    assert packet["authority_ceiling"]["live_bridge_dispatch_authorized"] is False
    assert packet["body_import_verification"]["source_body_digest"] == (
        f"sha256:{source_digest}"
    )
    assert packet["body_import_verification"]["target_body_digest"] == (
        f"sha256:{target_digest}"
    )
    assert packet["body_import_verification"]["verification_mode"] == (
        "verified_light_edit_recipe"
    )


def test_computer_use_action_trace_replay_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run_computer_use_action_trace_bundle(
        COMPUTER_USE_FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(
        COMPUTER_USE_EXPECTED_NEGATIVE_CASES
    )
    assert result["missing_negative_cases"] == []
    assert result["episode_count"] == 4
    assert result["observation_count"] == 6
    assert result["action_count"] == 8
    assert result["authority_verdict_count"] == 8
    assert result["state_transition_count"] == 8
    assert result["recovery_receipt_count"] == 1
    assert result["cold_replay_pass_count"] == 4
    assert result["block_count"] == 1
    assert result["authority_ceiling"]["live_browser_control_authorized"] is False
    assert result["authority_ceiling"]["credential_entry_authorized"] is False
    for codes in COMPUTER_USE_EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_computer_use_action_trace_receipt_is_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        public_root / "fixtures/first_wave/agent_route_observability_runtime",
    )

    result = run_computer_use_action_trace_bundle(
        public_root
        / "fixtures/first_wave/agent_route_observability_runtime/"
        "computer_use_action_trace_replay_input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    receipt_file = public_root / result["receipt_paths"][0]
    assert receipt_file.is_file()
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "/private/var" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    assert "raw_screenshot_body" not in _walk_keys(payload)
    assert "credential_value" not in _walk_keys(payload)
    assert "provider_payload" not in _walk_keys(payload)
    assert "hidden_screen_state" not in _walk_keys(payload)
    assert "body" not in _walk_keys(payload)
    redacted_findings = [
        finding for finding in payload["findings"] if finding.get("body_redacted") is True
    ]
    assert redacted_findings
    assert all(
        finding["subject_kind"] == "computer_use_negative_case"
        for finding in redacted_findings
    )
    assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
    assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
    for hit in payload["secret_exclusion_scan"]["hits"]:
        assert hit["body_in_receipt"] is False
        assert not Path(hit["path"]).is_absolute()


def test_computer_use_action_trace_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_computer_use_action_trace_bundle(
        COMPUTER_USE_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_computer_use_action_trace_bundle"
    assert result["bundle_id"] == (
        "public_computer_use_action_trace_replay_runtime_example"
    )
    assert result["receipt_paths"][0].endswith(
        EXPORTED_COMPUTER_USE_ACTION_TRACE_BUNDLE_RECEIPT_PATH
    )
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["episode_count"] == 4
    assert result["action_count"] == 8
    assert set(result["action_kinds"]) == {
        "click",
        "edit_text_record",
        "navigate",
        "select",
        "type",
        "wait",
    }
    assert result["authority_ceiling"]["benchmark_score_claim_authorized"] is False
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert "public_replacement_refs" not in result
    assert result["public_agent_execution_trace"]["status"] == "pass"
    assert result["public_agent_execution_trace"]["span_count"] == result["action_count"]
    assert result["public_agent_execution_trace"]["summary"]["action_kind_counts"] == {
        "click": 2,
        "edit_text_record": 1,
        "navigate": 1,
        "select": 1,
        "type": 2,
        "wait": 1,
    }
    assert result["body_import_verification"]["verification_mode"] == (
        "source_faithful_public_refactor"
    )
    assert result["source_module_manifest"]["status"] == "pass"
    assert result["source_module_manifest"]["body_in_receipt"] is False
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_expected_line_counts_matched"] is True
    assert result["source_module_manifest"]["all_expected_byte_counts_matched"] is True
    assert result["copied_macro_source_count"] == 2
    assert result["exact_source_body_import"]["verification_status"] == "pass"
    assert result["exact_source_body_import"]["source_to_target_relation"] == "exact_copy"
    assert result["exact_source_body_import"]["body_in_receipt"] is False


def test_computer_use_action_trace_imports_public_agent_execution_trace_refactor() -> None:
    protocol = json.loads(
        (COMPUTER_USE_BUNDLE_INPUT / "projection_protocol.json").read_text(
            encoding="utf-8"
        )
    )
    assert "body_redacted" not in protocol
    assert "public_replacement_refs" not in protocol
    assert "omitted_private_material" not in protocol
    assert protocol["body_import_status"] == "source_faithful_public_refactor_landed"
    assert protocol["body_import_verification"]["verification_mode"] == (
        "source_faithful_public_refactor"
    )
    assert "system/lib/agent_execution_trace.py" in protocol["source_refs"]
    assert (
        "microcosm-substrate/src/microcosm_core/macro_tools/agent_execution_trace.py"
        in protocol["target_refs"]
    )

    trace = build_public_computer_use_trace(COMPUTER_USE_BUNDLE_INPUT)
    assert trace["status"] == "pass"
    assert trace["source_faithful_refactor"]["source_ref"] == (
        "system/lib/agent_execution_trace.py"
    )
    assert trace["source_faithful_refactor"]["verification_mode"] == (
        "source_faithful_public_refactor"
    )
    assert trace["authority_ceiling"]["live_home_session_logs_read"] is False
    assert trace["authority_ceiling"]["provider_payload_read"] is False
    assert trace["audit"]["coverage"] == {
        "action_observation_coverage": True,
        "authority_verdict_coverage": True,
        "state_transition_coverage": True,
        "cold_replay_coverage": True,
        "body_in_receipt": False,
    }
    assert trace["span_count"] == 8
    assert all(
        span["source_ref"] == "computer_use_action_trace_bundle"
        for span in trace["spans"]
    )
    source = MICROCOSM_ROOT.parent / "system/lib/agent_execution_trace.py"
    bundle_source = (
        COMPUTER_USE_BUNDLE_INPUT / "source_modules/system/lib/agent_execution_trace.py"
    )
    standard = MICROCOSM_ROOT.parent / "codex/standards/std_agent_execution_trace.json"
    bundle_standard = (
        COMPUTER_USE_BUNDLE_INPUT
        / "source_modules/codex/standards/std_agent_execution_trace.json"
    )
    assert hashlib.sha256(source.read_bytes()).hexdigest() == hashlib.sha256(
        bundle_source.read_bytes()
    ).hexdigest()
    assert hashlib.sha256(standard.read_bytes()).hexdigest() == hashlib.sha256(
        bundle_standard.read_bytes()
    ).hexdigest()
    manifest = json.loads(
        (COMPUTER_USE_BUNDLE_INPUT / "source_module_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert {row["path"] for row in manifest["modules"]} == {
        "source_modules/codex/standards/std_agent_execution_trace.json",
        "source_modules/system/lib/agent_execution_trace.py",
        "source_modules/system/lib/strict_json.py",
    }


def test_computer_use_trace_loader_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    bundle_input = tmp_path / "exported_computer_use_action_trace_bundle"
    shutil.copytree(COMPUTER_USE_BUNDLE_INPUT, bundle_input)
    (bundle_input / "bundle_manifest.json").write_text(
        '{"bundle_id":"trace_a","bundle_id":"trace_b"}',
        encoding="utf-8",
    )

    with pytest.raises(DuplicateJsonKeyError):
        build_public_computer_use_trace(bundle_input)


def test_session_attribution_imports_exact_public_macro_body() -> None:
    source = MICROCOSM_ROOT.parent / "system/lib/agent_session_attribution.py"
    bundle_source = (
        SESSION_ATTRIBUTION_BUNDLE_INPUT
        / "source_modules/system/lib/agent_session_attribution.py"
    )
    target = MICROCOSM_ROOT / "src/microcosm_core/macro_tools/agent_session_attribution.py"
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    bundle_source_digest = hashlib.sha256(bundle_source.read_bytes()).hexdigest()
    target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
    ats = json.loads((SESSION_ATTRIBUTION_BUNDLE_INPUT / "ats_active_sessions.json").read_text())
    work_ledger = json.loads(
        (SESSION_ATTRIBUTION_BUNDLE_INPUT / "work_ledger_status.json").read_text()
    )

    view = attribute_sessions(
        ats_active_sessions=ats["active_sessions"],
        work_ledger_status=work_ledger,
    )

    assert target.is_file()
    assert bundle_source.is_file()
    assert source_digest == target_digest
    assert source_digest == bundle_source_digest
    assert view["schema_version"] == SESSION_ATTRIBUTION_SCHEMA_VERSION
    assert view["summary"]["total"] >= 5


def test_harness_configuration_imports_exact_public_macro_bodies() -> None:
    source_pairs = [
        (
            MICROCOSM_ROOT.parent / "tools/meta/audit/harness_audit.py",
            HARNESS_CONFIGURATION_AUDIT_BUNDLE_INPUT
            / "source_modules/tools/meta/audit/harness_audit.py",
        ),
        (
            MICROCOSM_ROOT.parent / "codex/standards/std_agent_entrypoint_audit.json",
            HARNESS_CONFIGURATION_AUDIT_BUNDLE_INPUT
            / "source_modules/codex/standards/std_agent_entrypoint_audit.json",
        ),
    ]

    for source, bundle_source in source_pairs:
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
        bundle_source_digest = hashlib.sha256(bundle_source.read_bytes()).hexdigest()
        assert bundle_source.is_file()
        assert source_digest == bundle_source_digest
