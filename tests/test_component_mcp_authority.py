"""The verified MCP core drives the public replay's actual call decisions."""
from __future__ import annotations

import itertools
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from plectis.components.mcp_authority import evaluate
from plectis.components.mcp_authority._adapter import evaluate as adapt
import microcosm_core.organs.mcp_tool_authority_replay as replay
from microcosm_core.validators.source_module_boundary import copied_source_identity

ROOT = Path(__file__).resolve().parents[1]


def observation():
    return {
        "declared": True, "scope": "scope/read", "broad": False,
        "credential": False, "forbiddenKey": False,
        "untrustedInstruction": False, "live": False, "finalOnly": False,
        "effect": "write", "approval": "approval/a", "ledger": "ledger/a",
        "rollback": "rollback/a", "bodySafe": True, "privateSafe": True,
        "fieldsPresent": True, "toolClass": "write_side_effect",
        "argumentHash": "hash/a", "sourceCapsule": "source/a",
        "instructionSplit": "split/a", "coldReplay": "replay/a",
    }


def test_generated_core_matches_all_fault_combinations():
    rows = []
    expected = []
    for flags in itertools.product((False, True), repeat=10):
        row = observation()
        row.update({
            "declared": not flags[0], "broad": flags[1],
            "credential": flags[2], "untrustedInstruction": flags[3],
            "live": flags[4], "finalOnly": flags[5],
            "approval": "missing" if flags[6] else "approval/a",
            "rollback": "" if flags[7] else "rollback/a",
            "bodySafe": not flags[8], "fieldsPresent": not flags[9],
        })
        rows.append(row)
        expected.append(list(flags))
    result = evaluate([], rows)
    assert result["negative_faults"] == expected
    assert result["accepted"] is False


def test_accepted_floor_and_rollback_missing():
    write = observation()
    read = {**observation(), "effect": "none", "toolClass": "readonly_lookup"}
    untrusted = {**read, "toolClass": "untrusted_result"}
    result = evaluate([write, read, untrusted], [])
    assert result["accepted"] is True
    assert result["write_count"] == result["untrusted_count"] == 1
    write["rollback"] = ""
    bad = evaluate([write, read, untrusted], [])
    assert bad["accepted"] is False
    assert bad["positive_faults"][0][7] is True


def test_multi_faults_keep_their_diagnostic_positions():
    row = {**observation(), "untrustedInstruction": True, "finalOnly": True}
    flags = evaluate([], [row])["negative_faults"][0]
    assert [index for index, flag in enumerate(flags) if flag] == [3, 5]


def test_long_batch_does_not_depend_on_python_recursion():
    read = {**observation(), "effect": "none", "toolClass": "readonly_lookup"}
    result = evaluate([read] * 1200, [])
    assert result["accepted"] is False
    assert result["write_count"] == result["untrusted_count"] == 0
    assert len(result["positive_faults"]) == 1200


def test_strict_adapter_rejects_bad_payloads():
    with pytest.raises(ValueError):
        adapt({"positive": [{}], "negative": []}, None, None)
    with pytest.raises(ValueError):
        adapt({"positive": [], "negative": None}, None, None)


def test_host_observations_preserve_exact_bool_and_coercion_rules():
    row = {"tool_id": "tool", "capability_scope_ref": 0, "scope_overbroad": 1,
           "body_in_receipt": 0, "private_ref_metadata_only": 1}
    checked = replay._tool_call_observation(row, {"different"})
    assert checked["declared"] is False
    assert checked["scope"] == ""
    assert checked["broad"] is False
    assert checked["bodySafe"] is False and checked["privateSafe"] is False
    assert checked["fieldsPresent"] is False
    assert replay._tool_call_observation(row, None)["declared"] is True


@pytest.mark.parametrize("variant", ["match", "no_upstream", "changed_upstream", "stub"])
def test_streamed_source_identity_matches_shared_contract(tmp_path, variant):
    public_root = tmp_path / "microcosm-substrate"
    public_root.mkdir()
    target = public_root / "copy.py"
    manifest = public_root / "manifest.json"
    manifest.write_text("{}")
    data = (b"x" * (1024 * 1024 - 8) + b"PUBLIC_MICROCOSM_STUB = True"
            if variant == "stub" else b"public source")
    target.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    row = {"source_ref": "original.py", "sha256": digest,
           "source_sha256": digest, "target_sha256": digest}
    upstream = None if variant == "no_upstream" else (
        b"other" if variant == "changed_upstream" else data
    )
    expected = copied_source_identity(row, data, upstream, exported_identity_matches=False)
    actual = replay._streamed_copy_identity(
        row, target, "sha256:" + digest, upstream,
        public_root=public_root, manifest_path=manifest,
    )
    assert actual == expected


def test_streamed_source_identity_accepts_matching_export_inventory(tmp_path):
    public_root = tmp_path / "microcosm-substrate"
    public_root.mkdir()
    target = public_root / "copy.py"
    manifest = public_root / "manifest.json"
    data = b"public source"
    target.write_bytes(data)
    manifest.write_text("{}")
    digest = hashlib.sha256(data).hexdigest()
    row = {"source_ref": "original.py", "sha256": digest,
           "source_sha256": digest, "target_sha256": digest}
    receipt = public_root / "receipts/release/release_export_receipt.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text(json.dumps({"inventory_receipt": {"files": [
        {"path": "copy.py", "sha256": digest},
        {"path": "manifest.json", "sha256": hashlib.sha256(b"{}").hexdigest()},
    ]}}))
    actual = replay._streamed_copy_identity(
        row, target, "sha256:" + digest, None,
        public_root=public_root, manifest_path=manifest,
    )
    assert actual == copied_source_identity(row, data, None, exported_identity_matches=True)


def test_real_replay_invokes_generated_core_and_rejects_missing_rollback(tmp_path, monkeypatch):
    seen = []
    real = replay.evaluate_mcp_authority

    def observed(positive, negative):
        seen.append((positive, negative))
        return real(positive, negative)

    monkeypatch.setattr(replay, "evaluate_mcp_authority", observed)
    fixture = ROOT / "fixtures/first_wave/mcp_tool_authority_replay/input"
    result = replay.run(fixture, tmp_path / "out", acceptance_out=tmp_path / "acceptance.json")
    assert result["status"] == "pass"
    assert seen and len(seen[0][0]) == 3 and seen[0][1]

    calls = json.loads((fixture / "tool_calls.json").read_text())
    write = next(row for row in calls["tool_calls"] if row["side_effect_class"] == "write")
    write["rollback_receipt_ref"] = ""
    write["credential_exported"] = True
    decision = replay.validate_tool_calls(calls, {}, declared_tool_ids=None)
    row = next(row for row in decision["call_rows"] if row["call_id"] == write["call_id"])
    assert decision["status"] == "blocked"
    assert row["reason_codes"] == ["hidden_credential_export", "missing_rollback_receipt"]
    assert [f["error_code"] for f in decision["findings"]] == [
        "MCP_TOOL_HIDDEN_CREDENTIAL_EXPORT", "MCP_TOOL_MISSING_ROLLBACK_RECEIPT"
    ]


def test_host_consumes_kernel_faults_and_batch_decision(monkeypatch):
    """A valid row must still follow the compiled core's returned decision."""
    fixture = ROOT / "fixtures/first_wave/mcp_tool_authority_replay/input"
    calls = json.loads((fixture / "tool_calls.json").read_text())
    expected = [False] * 10
    expected[7] = True

    def refused(positive, negative):
        assert len(positive) == 3 and negative == []
        return {
            "positive_faults": [expected, [False] * 10, [False] * 10],
            "negative_faults": [],
            "write_count": 17,
            "untrusted_count": 23,
            "accepted": False,
        }

    monkeypatch.setattr(replay, "evaluate_mcp_authority", refused)
    result = replay.validate_tool_calls(calls, {})
    assert result["status"] == "blocked"
    assert result["write_side_effect_count"] == 17
    assert result["untrusted_result_count"] == 23
    assert result["findings"][0]["error_code"] == "MCP_TOOL_MISSING_ROLLBACK_RECEIPT"
    first_id = calls["tool_calls"][0]["call_id"]
    row = next(row for row in result["call_rows"] if row["call_id"] == first_id)
    assert row["computed_verdict"] == "blocked"
    assert row["reason_codes"] == ["missing_rollback_receipt"]


@pytest.mark.parametrize("field", [
    "scope", "argumentHash", "sourceCapsule", "instructionSplit", "coldReplay",
])
def test_core_rejects_empty_citations_even_when_fields_are_present(field):
    row = observation()
    row[field] = ""
    assert row["fieldsPresent"] is True
    flags = evaluate([], [row])["negative_faults"][0]
    assert flags == [False] * 9 + [True]


@pytest.mark.parametrize("field, observation_field", [
    ("capability_scope_ref", "scope"), ("call_arguments_hash", "argumentHash"),
    ("result_source_capsule_ref", "sourceCapsule"),
    ("instruction_data_split_ref", "instructionSplit"),
    ("cold_replay_receipt_ref", "coldReplay"),
])
@pytest.mark.parametrize("blank", ["", " \t ", None, 0, 1, True, {"ref": "x"}, ["x"]])
def test_every_call_must_cite_nonempty_required_references(field, observation_field, blank):
    """The standard requires actual citations, not merely present JSON keys."""
    fixture = ROOT / "fixtures/first_wave/mcp_tool_authority_replay/input"
    calls = json.loads((fixture / "tool_calls.json").read_text())
    ids = {row["tool_id"] for row in calls["tool_calls"]}
    write = next(row for row in calls["tool_calls"] if row["side_effect_class"] == "write")
    write[field] = blank
    observed = replay._tool_call_observation(write, ids)
    assert observed[observation_field] == ""
    assert observed["fieldsPresent"] is (blank is not None)
    result = replay.validate_tool_calls(calls, {}, declared_tool_ids=ids)
    assert result["status"] == "blocked"
    row = next(row for row in result["call_rows"] if row["call_id"] == write["call_id"])
    assert row["reason_codes"] == ["call_field_missing"]
    assert row["missing_required_fields"] == [field]
    assert [finding["error_code"] for finding in result["findings"]] == [
        "MCP_TOOL_CALL_REQUIRED_FIELD_MISSING"
    ]


def test_host_trims_citation_whitespace_before_the_core_observes_it():
    fixture = ROOT / "fixtures/first_wave/mcp_tool_authority_replay/input"
    calls = json.loads((fixture / "tool_calls.json").read_text())
    row = calls["tool_calls"][0]
    expected = replay._tool_call_observation(row, None)
    for field in (
        "capability_scope_ref", "call_arguments_hash", "result_source_capsule_ref",
        "instruction_data_split_ref", "cold_replay_receipt_ref", "approval_token_ref",
        "ledger_diff_ref", "rollback_receipt_ref",
    ):
        row[field] = " \t" + row[field] + "\t "
    assert replay._tool_call_observation(row, None) == expected


@pytest.mark.parametrize("field, observation_field, error", [
    ("approval_token_ref", "approval", "MCP_TOOL_UNAPPROVED_SIDE_EFFECT"),
    ("ledger_diff_ref", "ledger", "MCP_TOOL_UNAPPROVED_SIDE_EFFECT"),
    ("rollback_receipt_ref", "rollback", "MCP_TOOL_MISSING_ROLLBACK_RECEIPT"),
])
@pytest.mark.parametrize("bad", [" \t ", 1, True, {"ref": "x"}, ["x"]])
def test_write_evidence_must_be_textual_nonempty_citations(field, observation_field, error, bad):
    fixture = ROOT / "fixtures/first_wave/mcp_tool_authority_replay/input"
    calls = json.loads((fixture / "tool_calls.json").read_text())
    write = next(row for row in calls["tool_calls"] if row["side_effect_class"] == "write")
    write[field] = bad
    assert replay._tool_call_observation(write, None)[observation_field] == ""
    result = replay.validate_tool_calls(calls, {})
    assert result["status"] == "blocked"
    assert [finding["error_code"] for finding in result["findings"]] == [error]
    assert write[field] == bad


def test_scoped_calls_pass_and_declared_tool_membership_is_enforced():
    fixture = ROOT / "fixtures/first_wave/mcp_tool_authority_replay/input"
    calls = json.loads((fixture / "tool_calls.json").read_text())
    manifest = json.loads((fixture / "tool_manifest.json").read_text())
    ids = {row["tool_id"] for row in manifest["tools"]}
    assert replay.validate_tool_calls(calls, {}, declared_tool_ids=ids)["status"] == "pass"
    calls["tool_calls"][0]["tool_id"] = "not_declared_by_manifest"
    assert replay.validate_tool_calls(calls, {})["status"] == "pass"
    complete = replay.validate_tool_calls(calls, {}, declared_tool_ids=ids)
    assert complete["status"] == "blocked"
    assert complete["findings"][0]["error_code"] == "MCP_TOOL_UNDECLARED_TOOL_ID"


@pytest.mark.parametrize("scope", ["", " \t ", 1, {"ref": "scope/x"}])
def test_manifest_tools_must_have_nonempty_scope_references(scope):
    fixture = ROOT / "fixtures/first_wave/mcp_tool_authority_replay/input"
    manifest = json.loads((fixture / "tool_manifest.json").read_text())
    assert replay.validate_tool_manifest(manifest)["status"] == "pass"
    manifest["tools"][0]["capability_scope_ref"] = scope
    result = replay.validate_tool_manifest(manifest)
    assert result["status"] == "blocked"
    assert "missing_capability_scope_ref" in result["tool_rows"][0]["reason_codes"]


@pytest.mark.parametrize("field,bad,expected", [
    ("capability_scope_ref", "", "MCP_TOOL_CALL_REQUIRED_FIELD_MISSING"),
    ("tool_id", "not_declared_by_manifest", "MCP_TOOL_UNDECLARED_TOOL_ID"),
    ("approval_token_ref", " \t ", "MCP_TOOL_UNAPPROVED_SIDE_EFFECT"),
    ("approval_token_ref", {"ref": "approval/a"}, "MCP_TOOL_UNAPPROVED_SIDE_EFFECT"),
    ("ledger_diff_ref", " \t ", "MCP_TOOL_UNAPPROVED_SIDE_EFFECT"),
    ("ledger_diff_ref", {"ref": "ledger/a"}, "MCP_TOOL_UNAPPROVED_SIDE_EFFECT"),
    ("rollback_receipt_ref", " \t ", "MCP_TOOL_MISSING_ROLLBACK_RECEIPT"),
    ("rollback_receipt_ref", {"ref": "rollback/a"}, "MCP_TOOL_MISSING_ROLLBACK_RECEIPT"),
])
@pytest.mark.parametrize("effect", ["write", "external_mutation"])
def test_actual_bundle_rejects_invalid_citations_or_manifest_authority(tmp_path, field, bad, expected, effect):
    relative = Path("examples/mcp_tool_authority_replay/exported_mcp_tool_authority_bundle")
    public_root = tmp_path / "microcosm-substrate"
    bundle = public_root / relative
    shutil.copytree(ROOT / relative, bundle)
    for ref in (
        "core/private_state_forbidden_classes.json", replay.SOURCE_INVENTORY_CONTRACT,
        "src/microcosm_core/organs/mcp_tool_authority_replay.py",
    ):
        target = public_root / ref
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / ref, target)
    calls_path = bundle / "tool_calls.json"
    calls = json.loads(calls_path.read_text())
    write = next(row for row in calls["tool_calls"] if row["side_effect_class"] == "write")
    write["side_effect_class"] = effect
    write[field] = bad
    calls_path.write_text(json.dumps(calls))
    result = replay.run_tool_authority_bundle(bundle, tmp_path / "out", command="pytest")
    assert result["status"] == "blocked"
    assert expected in result["error_codes"]
    assert json.loads(calls_path.read_text())["tool_calls"] == calls["tool_calls"]
    trace_checks = {
        "approval_token_ref": ("PUBLIC_TRACE_MCP_TOOL_WRITE_APPROVAL_REF_MISSING",
                               "write_side_effect_approval_coverage"),
        "ledger_diff_ref": ("PUBLIC_TRACE_MCP_TOOL_SIDE_EFFECT_LEDGER_REF_MISSING",
                            "write_side_effect_ledger_coverage"),
        "rollback_receipt_ref": ("PUBLIC_TRACE_MCP_TOOL_ROLLBACK_REF_MISSING",
                                 "rollback_receipt_coverage"),
        "capability_scope_ref": ("PUBLIC_TRACE_MCP_TOOL_CALL_FIELDS_MISSING",
                                 "capability_scope_coverage"),
    }
    if field in trace_checks:
        trace = result["public_agent_execution_trace"]
        assert trace["status"] == "blocked"
        trace_error, coverage = trace_checks[field]
        assert trace_error in {
            row["error_code"] for row in trace["audit"]["findings"]
        }
        assert trace["audit"]["coverage"][coverage] is False
        span = next(row for row in trace["spans"] if row["episode_id"] == write["call_id"])
        assert span[field] == bad
