"""Behavior of the verified decision and its production integration."""
import json
from pathlib import Path
import shutil

import pytest

from plectis.components.sandbox_policy import evaluate
from microcosm_core.organs import agent_sandbox_policy_escape_replay as organ


CASES = [
    ("secret_access", "environment_secret_read", "environment_read", "untrusted_tool_output", "block", "rule:no_secret_or_env_read_from_untrusted_context"),
    ("network_exfiltration", "network_request", "outbound_network", "untrusted_tool_output", "block", "rule:no_live_network_from_untrusted_context"),
    ("destructive_filesystem_mutation", "filesystem_delete", "filesystem_write", "untrusted_repo_file", "block", "rule:no_destructive_filesystem_mutation"),
    ("escape_payload_obfuscation", "shell_command", "shell_exec", "untrusted_tool_output", "block", "rule:no_executable_escape_payload_or_obfuscation"),
    ("low_risk_public_fixture_mutation", "filesystem_write", "public_fixture_write", "trusted_user_request", "allow", "rule:public_fixture_write_with_diff_receipt"),
    ("review_required_side_effect", "mock_database_update", "mock_database_write", "trusted_operator_approval_ref", "review", "rule:side_effect_requires_approval_and_rollback"),
]
FIELDS = ("risk_class", "action_kind", "requested_capability", "source_trust_label")
FAIL = ["block", "rule:sandbox_policy_fail_closed_unrecognized_action"]


def test_verified_policy_all_fields_are_required_and_unknown_fails_closed():
    rows, expected = [], []
    for *values, verdict, rule in CASES:
        row = dict(zip(FIELDS, values))
        rows.append(row)
        expected.append([verdict, rule])
        for field in FIELDS:
            rows.append({**row, field: "unexpected"})
            expected.append(FAIL)
    rows.append(dict.fromkeys(FIELDS, ""))
    expected.append(FAIL)
    assert evaluate(rows) == expected


def test_production_decision_uses_verified_bridge_and_preserves_normalization(monkeypatch):
    seen = []
    def fake(rows):
        seen.extend(rows)
        return [["sentinel", "verified-rule"]]
    monkeypatch.setattr(organ, "_verified_policy_evaluate", fake)
    organ._policy_decision_cached.cache_clear()
    assert organ._derived_sandbox_policy_verdict({"risk_class": 42, "action_kind": False}) == ("sentinel", "verified-rule")
    assert seen == [{"risk_class": "42", "action_kind": "", "requested_capability": "", "source_trust_label": ""}]
    organ._policy_decision_cached.cache_clear()


def test_production_exact_trust_boundary():
    row = dict(zip(FIELDS, CASES[4][:4]))
    assert organ._derived_sandbox_policy_verdict(row) == tuple(CASES[4][4:])
    assert organ._derived_sandbox_policy_verdict({**row, "source_trust_label": "untrusted_tool_output"}) == tuple(FAIL)


@pytest.mark.parametrize("invalid", [None, {}, [{"risk_class": "secret_access"}], [dict.fromkeys(FIELDS, 1)], [dict.fromkeys(FIELDS, True)]])
def test_rejects_invalid_adapter_input(invalid):
    with pytest.raises((RuntimeError, ValueError)):
        evaluate(invalid)


def test_all_policy_literal_combinations_match_the_decision_table():
    # All branch-equivalence classes, including an unknown value in each field.
    from itertools import product
    pools = [sorted({case[index] for case in CASES} | {"", "unknown"}) for index in range(4)]
    expected_by_tuple = {tuple(case[:4]): list(case[4:]) for case in CASES}
    values = list(product(*pools))
    rows = [dict(zip(FIELDS, item)) for item in values]
    assert evaluate(rows) == [expected_by_tuple.get(item, FAIL) for item in values]


def test_oversized_input_still_fails_closed():
    assert all(len(value) <= 128 for case in CASES for value in case[:4])
    row = dict(zip(FIELDS, CASES[4][:4]))
    for field in FIELDS:
        assert organ._derived_sandbox_policy_verdict({**row, field: "x" * 2_100_000}) == tuple(FAIL)


def test_cached_allow_cannot_hide_a_generated_integrity_failure(monkeypatch):
    from plectis.components import _bridge

    row = dict(zip(FIELDS, CASES[4][:4]))
    organ._policy_decision_cached.cache_clear()
    assert organ._derived_sandbox_policy_verdict(row) == tuple(CASES[4][4:])

    def corrupted_snapshot(*_args, **_kwargs):
        raise ValueError("generated component bytes changed")

    monkeypatch.setattr(_bridge, "read_kernel_snapshot", corrupted_snapshot)
    try:
        with pytest.raises(ValueError, match="generated component bytes changed"):
            organ._derived_sandbox_policy_verdict(row)
    finally:
        organ._policy_decision_cached.cache_clear()


def test_cached_decision_recomputes_when_valid_kernel_identity_changes(monkeypatch):
    identity = {"version": 1}
    calls = []

    def evaluate_identity(_slug):
        return dict(identity)

    def decision(_rows):
        calls.append(identity["version"])
        return [["allow", f"version-{identity['version']}"]]

    monkeypatch.setattr(organ, "_policy_kernel_identity", evaluate_identity)
    monkeypatch.setattr(organ, "_verified_policy_evaluate", decision)
    row = dict(zip(FIELDS, CASES[4][:4]))
    organ._policy_decision_cached.cache_clear()
    try:
        assert organ._derived_sandbox_policy_verdict(row) == ("allow", "version-1")
        assert organ._derived_sandbox_policy_verdict(row) == ("allow", "version-1")
        identity["version"] = 2
        assert organ._derived_sandbox_policy_verdict(row) == ("allow", "version-2")
        assert calls == [1, 2]
    finally:
        organ._policy_decision_cached.cache_clear()


def test_reused_bundle_receipt_cannot_hide_generated_integrity_failure(tmp_path, monkeypatch):
    from plectis.components import _bridge

    bundle = Path(__file__).resolve().parents[1] / "examples/agent_sandbox_policy_escape_replay/exported_sandbox_policy_escape_bundle"
    basis = organ._freshness_basis(bundle, include_negative=False)
    (tmp_path / organ.BUNDLE_RESULT_NAME).write_text(json.dumps({
        "schema_version": "exported_sandbox_policy_escape_bundle_validation_result_v1",
        "organ_id": organ.ORGAN_ID,
        "input_mode": "exported_sandbox_policy_escape_bundle",
        "status": "pass", "freshness_basis": basis,
    }), encoding="utf-8")

    def corrupted_snapshot(*_args, **_kwargs):
        raise ValueError("generated component bytes changed")

    monkeypatch.setattr(_bridge, "read_kernel_snapshot", corrupted_snapshot)
    with pytest.raises(ValueError, match="generated component bytes changed"):
        organ.run_sandbox_bundle(bundle, tmp_path, reuse_fresh_receipt=True)


@pytest.mark.parametrize("changed", ["stub", "inventory"])
def test_bundle_freshness_covers_omission_stubs_and_public_inventory(tmp_path, changed):
    root = Path(__file__).resolve().parents[1]
    public = tmp_path / "microcosm-substrate"
    bundle = public / "examples/agent_sandbox_policy_escape_replay/exported_sandbox_policy_escape_bundle"
    shutil.copytree(root / bundle.relative_to(public), bundle)
    for relative in ("core/private_state_forbidden_classes.json", "core/fixture_manifests/agent_sandbox_policy_escape_replay.fixture_manifest.json"):
        target = public / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / relative, target)
    before = organ._freshness_basis(bundle, include_negative=False)
    if changed == "stub":
        manifest = json.loads((bundle / "source_module_manifest.json").read_text())
        (bundle / manifest["release_substitution_omissions"][0]["path"]).write_text("tampered\n", encoding="utf-8")
    else:
        inventory = public / "core/fixture_manifests/agent_sandbox_policy_escape_replay.fixture_manifest.json"
        payload = json.loads(inventory.read_text())
        payload["purpose"] = "changed inventory"
        inventory.write_text(json.dumps(payload), encoding="utf-8")
    assert before["basis_digest"] != organ._freshness_basis(bundle, include_negative=False)["basis_digest"]
