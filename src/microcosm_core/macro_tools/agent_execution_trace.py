from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PASS = "pass"
BLOCKED = "blocked"

SOURCE_REFS = [
    "system/lib/agent_execution_trace.py",
    "codex/standards/std_agent_execution_trace.json",
]
SOURCE_SYMBOL_REFS = [
    "system/lib/agent_execution_trace.py::Span",
    "system/lib/agent_execution_trace.py::build_agent_execution_trace",
    "system/lib/agent_execution_trace.py::write_agent_execution_trace",
    "codex/standards/std_agent_execution_trace.json::types.Span",
    "codex/standards/std_agent_execution_trace.json::strict_boundary",
]
TARGET_REFS = [
    "microcosm-substrate/src/microcosm_core/macro_tools/agent_execution_trace.py",
]
TARGET_SYMBOL_REFS = [
    "microcosm_core.macro_tools.agent_execution_trace::PublicTraceSpan",
    "microcosm_core.macro_tools.agent_execution_trace::build_public_computer_use_trace",
    "microcosm_core.macro_tools.agent_execution_trace::build_public_sandbox_policy_trace",
    "microcosm_core.macro_tools.agent_execution_trace::build_public_research_replication_trace",
    "microcosm_core.macro_tools.agent_execution_trace::build_public_memory_conflict_trace",
    "microcosm_core.macro_tools.agent_execution_trace::build_public_mcp_tool_authority_trace",
    "microcosm_core.macro_tools.agent_execution_trace::build_public_agentic_vulnerability_patch_proof_trace",
    "microcosm_core.macro_tools.agent_execution_trace::main",
]
AUTHORITY_CEILING = {
    "live_home_session_logs_read": False,
    "live_browser_control_authorized": False,
    "live_account_action_authorized": False,
    "credential_entry_authorized": False,
    "external_network_mutation_authorized": False,
    "provider_payload_read": False,
    "raw_screenshot_body_exported": False,
    "hidden_reasoning_exported": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
}


@dataclass(frozen=True)
class PublicTraceSpan:
    span_id: str
    session_id: str
    action_kind: str
    sequence_index: int
    episode_id: str
    observation_ref: str
    authority_verdict_id: str
    state_transition_ref: str
    outcome: str
    target_ref: str
    input_digest: str
    recovery_ref: str | None = None
    tool_name: str = "computer_use_action"
    source_ref: str = "computer_use_action_trace_bundle"

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "span_id": self.span_id,
            "agent": "microcosm_public_fixture",
            "session_id": self.session_id,
            "action_kind": self.action_kind,
            "sequence_index": self.sequence_index,
            "turn_index": self.sequence_index,
            "tool_name": self.tool_name,
            "duration_ms": 0,
            "outcome": self.outcome,
            "episode_id": self.episode_id,
            "observation_ref": self.observation_ref,
            "authority_verdict_id": self.authority_verdict_id,
            "state_transition_ref": self.state_transition_ref,
            "target_refs": [self.target_ref] if self.target_ref else [],
            "input_digest": self.input_digest,
            "source_ref": self.source_ref,
        }
        if self.recovery_ref:
            payload["recovery_ref"] = self.recovery_ref
        return payload


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _stable_digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _display_path(path: Path) -> str:
    parts = list(path.resolve(strict=False).parts)
    if "microcosm-substrate" in parts:
        index = parts.index("microcosm-substrate")
        return "/".join(parts[index + 1 :])
    return path.name


def _finding(code: str, message: str, *, subject_id: str) -> dict[str, Any]:
    return {
        "error_code": code,
        "message": message,
        "subject_id": subject_id,
        "subject_kind": "public_agent_execution_trace",
        "body_in_receipt": False,
    }


def _load_bundle(input_dir: Path) -> dict[str, dict[str, Any]]:
    names = (
        "bundle_manifest",
        "projection_protocol",
        "task_episodes",
        "screen_observations",
        "action_trace",
        "authority_verdicts",
        "state_transition_receipts",
        "recovery_receipts",
        "cold_replay",
    )
    return {name: _read_json(input_dir / f"{name}.json") for name in names}


def _load_sandbox_bundle(input_dir: Path) -> dict[str, dict[str, Any]]:
    names = (
        "bundle_manifest",
        "projection_protocol",
        "action_requests",
        "policy_verdicts",
        "side_effect_receipts",
        "rollback_receipts",
        "cold_replay",
    )
    bundle: dict[str, dict[str, Any]] = {}
    for name in names:
        path = input_dir / f"{name}.json"
        if path.is_file():
            bundle[name] = _read_json(path)
        elif name == "bundle_manifest":
            bundle[name] = {
                "bundle_id": "agent_sandbox_policy_escape_replay_fixture_input",
                "input_mode": "fixture",
                "organ_id": "agent_sandbox_policy_escape_replay",
            }
        else:
            bundle[name] = {}
    return bundle


def _load_research_replication_bundle(input_dir: Path) -> dict[str, dict[str, Any]]:
    names = (
        "bundle_manifest",
        "projection_protocol",
        "replication_policy",
        "research_replays",
    )
    bundle: dict[str, dict[str, Any]] = {}
    for name in names:
        path = input_dir / f"{name}.json"
        if path.is_file():
            bundle[name] = _read_json(path)
        elif name == "bundle_manifest":
            bundle[name] = {
                "bundle_id": "research_replication_rubric_artifact_replay_fixture_input",
                "input_mode": "fixture",
                "organ_id": "research_replication_rubric_artifact_replay",
            }
        else:
            bundle[name] = {}
    return bundle


def _load_memory_conflict_bundle(input_dir: Path) -> dict[str, dict[str, Any]]:
    names = (
        "bundle_manifest",
        "projection_protocol",
        "memory_episodes",
        "replay_observations",
    )
    bundle: dict[str, dict[str, Any]] = {}
    for name in names:
        path = input_dir / f"{name}.json"
        if path.is_file():
            bundle[name] = _read_json(path)
        elif name == "bundle_manifest":
            bundle[name] = {
                "bundle_id": "agent_memory_temporal_conflict_replay_fixture_input",
                "input_mode": "fixture",
                "organ_id": "agent_memory_temporal_conflict_replay",
            }
        else:
            bundle[name] = {}
    return bundle


def _load_mcp_tool_authority_bundle(input_dir: Path) -> dict[str, dict[str, Any]]:
    names = (
        "bundle_manifest",
        "projection_protocol",
        "tool_policy",
        "tool_manifest",
        "tool_calls",
        "tool_results",
        "side_effect_ledger",
        "cold_replay",
    )
    bundle: dict[str, dict[str, Any]] = {}
    for name in names:
        path = input_dir / f"{name}.json"
        if path.is_file():
            bundle[name] = _read_json(path)
        elif name == "bundle_manifest":
            bundle[name] = {
                "bundle_id": "mcp_tool_authority_replay_fixture_input",
                "input_mode": "fixture",
                "organ_id": "mcp_tool_authority_replay",
            }
        else:
            bundle[name] = {}
    return bundle


def _load_agentic_vulnerability_patch_proof_bundle(input_dir: Path) -> dict[str, dict[str, Any]]:
    names = (
        "bundle_manifest",
        "projection_protocol",
        "target_manifests",
        "issue_hypotheses",
        "trace_evidence",
        "exploitability_proofs",
        "patch_diffs",
        "regression_tests",
        "verifier_receipts",
        "sandbox_policy_verdicts",
        "false_positive_triage",
        "cold_replay",
    )
    bundle: dict[str, dict[str, Any]] = {}
    for name in names:
        path = input_dir / f"{name}.json"
        if path.is_file():
            bundle[name] = _read_json(path)
        elif name == "bundle_manifest":
            bundle[name] = {
                "bundle_id": "agentic_vulnerability_discovery_patch_proof_replay_fixture_input",
                "input_mode": "fixture",
                "organ_id": "agentic_vulnerability_discovery_patch_proof_replay",
            }
        else:
            bundle[name] = {}
    return bundle


def build_public_computer_use_trace(input_dir: str | Path) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path

    bundle = _load_bundle(input_path)
    manifest = bundle["bundle_manifest"]
    protocol = bundle["projection_protocol"]
    session_id = str(manifest.get("bundle_id") or "public_computer_use_trace")
    episodes = {
        str(row.get("episode_id")): row
        for row in _rows(bundle["task_episodes"], "episodes")
        if row.get("episode_id")
    }
    observations = {
        str(row.get("observation_id")): row
        for row in _rows(bundle["screen_observations"], "observations")
        if row.get("observation_id")
    }
    verdicts = {
        str(row.get("verdict_id")): row
        for row in _rows(bundle["authority_verdicts"], "authority_verdicts")
        if row.get("verdict_id")
    }
    transitions = {
        str(row.get("transition_id")): row
        for row in _rows(bundle["state_transition_receipts"], "state_transitions")
        if row.get("transition_id")
    }
    recoveries = {
        str(row.get("recovery_id")): row
        for row in _rows(bundle["recovery_receipts"], "recovery_receipts")
        if row.get("recovery_id")
    }
    replayed_actions: set[str] = set()
    for row in _rows(bundle["cold_replay"], "cold_replay"):
        replayed_actions.update(str(action_id) for action_id in row.get("action_ids", []))

    findings: list[dict[str, Any]] = []
    spans: list[dict[str, Any]] = []
    sorted_actions = sorted(
        _rows(bundle["action_trace"], "actions"),
        key=lambda row: (
            str(row.get("episode_id") or ""),
            int(row.get("step_index") or 0),
            str(row.get("action_id") or ""),
        ),
    )
    for sequence_index, row in enumerate(sorted_actions):
        action_id = str(row.get("action_id") or f"action_{sequence_index}")
        observation_ref = str(row.get("observation_ref") or "")
        verdict_id = str(row.get("authority_verdict_id") or "")
        transition_ref = str(row.get("state_transition_ref") or "")
        recovery_ref = row.get("recovery_ref")
        recovery_id = str(recovery_ref) if recovery_ref else None
        action_kind = str(row.get("action_kind") or "unknown_action")
        execution_status = str(row.get("execution_status") or "")
        outcome = "ok" if execution_status == "executed" else execution_status or "unknown"

        if str(row.get("episode_id") or "") not in episodes:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_EPISODE_REF_MISSING",
                    "Action row references an unknown episode.",
                    subject_id=action_id,
                )
            )
        if observation_ref not in observations:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_OBSERVATION_REF_MISSING",
                    "Action row has no matching observation row.",
                    subject_id=action_id,
                )
            )
        if verdict_id not in verdicts:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_AUTHORITY_VERDICT_REF_MISSING",
                    "Action row has no matching pre-action authority verdict.",
                    subject_id=action_id,
                )
            )
        if transition_ref not in transitions:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_STATE_TRANSITION_REF_MISSING",
                    "Action row has no matching state-transition receipt.",
                    subject_id=action_id,
                )
            )
        if recovery_id and recovery_id not in recoveries:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_RECOVERY_REF_MISSING",
                    "Blocked or review action has no matching recovery receipt.",
                    subject_id=action_id,
                )
            )
        if action_id not in replayed_actions:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_COLD_REPLAY_REF_MISSING",
                    "Action row is not covered by a cold-replay receipt.",
                    subject_id=action_id,
                )
            )

        spans.append(
            PublicTraceSpan(
                span_id=f"span:{action_id}",
                session_id=session_id,
                action_kind=action_kind,
                sequence_index=sequence_index,
                episode_id=str(row.get("episode_id") or ""),
                observation_ref=observation_ref,
                authority_verdict_id=verdict_id,
                state_transition_ref=transition_ref,
                outcome=outcome,
                target_ref=str(row.get("target_ref") or ""),
                input_digest=str(row.get("input_digest") or ""),
                recovery_ref=recovery_id,
            ).as_dict()
        )

    status = PASS if not findings else BLOCKED
    action_kind_counts = Counter(span["action_kind"] for span in spans)
    outcome_counts = Counter(span["outcome"] for span in spans)
    verifier = {
        "action_observation_coverage": len(spans) == sum(
            1 for span in spans if span["observation_ref"] in observations
        ),
        "authority_verdict_coverage": len(spans) == sum(
            1 for span in spans if span["authority_verdict_id"] in verdicts
        ),
        "state_transition_coverage": len(spans) == sum(
            1 for span in spans if span["state_transition_ref"] in transitions
        ),
        "cold_replay_coverage": len(spans) == sum(
            1 for span in spans if span["span_id"].replace("span:", "") in replayed_actions
        ),
        "body_in_receipt": False,
    }
    return {
        "schema_version": "public_agent_execution_trace_refactor_v0",
        "status": status,
        "source_refs": list(SOURCE_REFS),
        "source_symbols": list(SOURCE_SYMBOL_REFS),
        "target_refs": list(TARGET_REFS),
        "target_symbols": list(TARGET_SYMBOL_REFS),
        "source_faithful_refactor": {
            "source_ref": "system/lib/agent_execution_trace.py",
            "target_ref": "microcosm-substrate/src/microcosm_core/macro_tools/agent_execution_trace.py",
            "verification_mode": "source_faithful_public_refactor",
            "preserved_semantics": [
                "observable_action_span_rows",
                "authority_boundary_metadata",
                "sequence_ordered_trace",
                "audit_findings",
                "public_summary_counts",
            ],
            "omitted_live_material": [
                "home directory session logs",
                "raw prompt bodies",
                "tool output bodies",
                "hidden reasoning",
                "provider payload bodies",
            ],
        },
        "authority_ceiling": AUTHORITY_CEILING,
        "input_ref": _display_path(input_path),
        "bundle_id": session_id,
        "protocol_id": protocol.get("protocol_id"),
        "span_count": len(spans),
        "spans": spans,
        "summary": {
            "session_count": 1,
            "total_span_count": len(spans),
            "action_kind_counts": dict(sorted(action_kind_counts.items())),
            "outcome_counts": dict(sorted(outcome_counts.items())),
            "finding_count": len(findings),
            "trace_digest": _stable_digest(spans),
        },
        "audit": {
            "findings": findings,
            "coverage": verifier,
            "finding_count": len(findings),
        },
        "body_in_receipt": False,
    }


def build_public_sandbox_policy_trace(input_dir: str | Path) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path

    bundle = _load_sandbox_bundle(input_path)
    manifest = bundle["bundle_manifest"]
    protocol = bundle["projection_protocol"]
    session_id = str(manifest.get("bundle_id") or "public_sandbox_policy_trace")
    verdicts = {
        str(row.get("request_id")): row
        for row in _rows(bundle["policy_verdicts"], "policy_verdicts")
        if row.get("request_id")
    }
    effects = {
        str(row.get("request_id")): row
        for row in _rows(bundle["side_effect_receipts"], "side_effect_receipts")
        if row.get("request_id")
    }
    rollback_requests = {
        str(row.get("request_id"))
        for row in _rows(bundle["rollback_receipts"], "rollback_receipts")
        if row.get("request_id")
    }
    replayed_requests = {
        str(row.get("request_id"))
        for row in _rows(bundle["cold_replay"], "cold_replay")
        if row.get("request_id")
    }

    findings: list[dict[str, Any]] = []
    spans: list[dict[str, Any]] = []
    sorted_actions = sorted(
        _rows(bundle["action_requests"], "action_requests"),
        key=lambda row: (
            str(row.get("episode_id") or ""),
            str(row.get("request_id") or ""),
        ),
    )
    for sequence_index, row in enumerate(sorted_actions):
        request_id = str(row.get("request_id") or f"request_{sequence_index}")
        verdict = verdicts.get(request_id, {})
        effect = effects.get(request_id, {})
        verdict_label = str(verdict.get("verdict") or "missing_verdict")
        execution_attempted = effect.get("execution_attempted")
        if verdict_label == "block":
            outcome = "blocked"
        elif execution_attempted is True:
            outcome = "executed"
        else:
            outcome = verdict_label

        if request_id not in verdicts:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_SANDBOX_POLICY_VERDICT_REF_MISSING",
                    "Sandbox action request has no matching pre-execution policy verdict.",
                    subject_id=request_id,
                )
            )
        elif verdict.get("pre_execution") is not True:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_SANDBOX_POLICY_VERDICT_NOT_PRE_EXECUTION",
                    "Sandbox policy verdict must precede execution.",
                    subject_id=request_id,
                )
            )
        if request_id not in effects:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_SANDBOX_SIDE_EFFECT_REF_MISSING",
                    "Sandbox action request has no matching side-effect receipt.",
                    subject_id=request_id,
                )
            )
        if verdict_label == "block" and execution_attempted is not False:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_SANDBOX_BLOCKED_ACTION_EXECUTED",
                    "Blocked sandbox action must not execute.",
                    subject_id=request_id,
                )
            )
        if verdict_label in {"allow", "review"} and execution_attempted is not True:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_SANDBOX_ALLOWED_ACTION_NOT_EXECUTED",
                    "Allowed or reviewed sandbox action must carry an executed side-effect receipt.",
                    subject_id=request_id,
                )
            )
        if verdict_label in {"allow", "review"} and request_id not in rollback_requests:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_SANDBOX_ROLLBACK_REF_MISSING",
                    "Side-effecting sandbox action has no rollback receipt.",
                    subject_id=request_id,
                )
            )
        if request_id not in replayed_requests:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_SANDBOX_COLD_REPLAY_REF_MISSING",
                    "Sandbox action request is not covered by a cold-replay receipt.",
                    subject_id=request_id,
                )
            )

        spans.append(
            PublicTraceSpan(
                span_id=f"span:{request_id}",
                session_id=session_id,
                action_kind=str(row.get("action_kind") or "unknown_action"),
                sequence_index=sequence_index,
                episode_id=str(row.get("episode_id") or ""),
                observation_ref=str(row.get("untrusted_tool_output_ref") or ""),
                authority_verdict_id=f"{request_id}:{verdict.get('policy_version', '')}",
                state_transition_ref=str(effect.get("rollback_receipt_ref") or ""),
                outcome=outcome,
                target_ref=str(row.get("requested_capability") or ""),
                input_digest=_stable_digest(
                    {
                        "normalized_action_ref": row.get("normalized_action_ref"),
                        "requested_capability": row.get("requested_capability"),
                        "risk_class": row.get("risk_class"),
                    }
                ),
                recovery_ref=(
                    str(effect.get("rollback_receipt_ref"))
                    if verdict_label in {"allow", "review"}
                    else None
                ),
                tool_name="sandbox_policy_action",
                source_ref="agent_sandbox_policy_escape_replay_bundle",
            ).as_dict()
        )

    status = PASS if not findings else BLOCKED
    action_kind_counts = Counter(span["action_kind"] for span in spans)
    outcome_counts = Counter(span["outcome"] for span in spans)
    coverage = {
        "policy_verdict_coverage": len(spans)
        == sum(1 for span in spans if span["span_id"].replace("span:", "") in verdicts),
        "side_effect_receipt_coverage": len(spans)
        == sum(1 for span in spans if span["span_id"].replace("span:", "") in effects),
        "rollback_receipt_coverage": all(
            span["span_id"].replace("span:", "") in rollback_requests
            for span in spans
            if span["outcome"] == "executed"
        ),
        "cold_replay_coverage": len(spans)
        == sum(
            1
            for span in spans
            if span["span_id"].replace("span:", "") in replayed_requests
        ),
        "body_in_receipt": False,
    }
    return {
        "schema_version": "public_agent_execution_trace_refactor_v0",
        "status": status,
        "source_refs": list(SOURCE_REFS),
        "source_symbols": list(SOURCE_SYMBOL_REFS),
        "target_refs": list(TARGET_REFS),
        "target_symbols": list(TARGET_SYMBOL_REFS),
        "source_faithful_refactor": {
            "source_ref": "system/lib/agent_execution_trace.py",
            "target_ref": "microcosm-substrate/src/microcosm_core/macro_tools/agent_execution_trace.py",
            "verification_mode": "extension_of_existing_public_refactor",
            "preserved_semantics": [
                "observable_action_span_rows",
                "authority_boundary_metadata",
                "sequence_ordered_trace",
                "audit_findings",
                "public_summary_counts",
                "pre_execution_policy_verdict_refs",
                "side_effect_and_rollback_refs",
            ],
            "omitted_live_material": [
                "real secrets and credentials",
                "raw environment values",
                "executable payload bodies",
                "host filesystem paths",
                "live network targets",
                "provider payload bodies",
            ],
        },
        "authority_ceiling": AUTHORITY_CEILING,
        "input_ref": _display_path(input_path),
        "bundle_id": session_id,
        "protocol_id": protocol.get("protocol_id"),
        "span_count": len(spans),
        "spans": spans,
        "summary": {
            "session_count": 1,
            "total_span_count": len(spans),
            "action_kind_counts": dict(sorted(action_kind_counts.items())),
            "outcome_counts": dict(sorted(outcome_counts.items())),
            "finding_count": len(findings),
            "trace_digest": _stable_digest(spans),
        },
        "audit": {
            "findings": findings,
            "coverage": coverage,
            "finding_count": len(findings),
        },
        "body_in_receipt": False,
    }


def build_public_research_replication_trace(input_dir: str | Path) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path

    bundle = _load_research_replication_bundle(input_path)
    manifest = bundle["bundle_manifest"]
    protocol = bundle["projection_protocol"]
    session_id = str(manifest.get("bundle_id") or "public_research_replication_trace")
    required_replay_fields = {
        "paper_id",
        "contribution_decomposition_ref",
        "rubric_tree_ref",
        "allowed_public_input_refs",
        "scratch_repo_scaffold_ref",
        "experiment_dag_ref",
        "metric_script_refs",
        "artifact_hash_refs",
        "declared_artifact_hash_refs",
        "grader_report_ref",
        "cost_runtime_budget_ref",
        "ablation_diff_ref",
        "failure_taxonomy_ref",
        "cold_rerun_receipt_ref",
    }

    findings: list[dict[str, Any]] = []
    spans: list[dict[str, Any]] = []
    sorted_replays = sorted(
        _rows(bundle["research_replays"], "research_replays"),
        key=lambda row: str(row.get("paper_id") or ""),
    )
    for sequence_index, row in enumerate(sorted_replays):
        paper_id = str(row.get("paper_id") or f"research_replay_{sequence_index}")
        missing_fields = sorted(
            field for field in required_replay_fields if not row.get(field)
        )
        if missing_fields:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_RESEARCH_REPLAY_FIELDS_MISSING",
                    "Research replay row is missing public replay evidence refs.",
                    subject_id=paper_id,
                )
            )

        artifact_hash_refs = {
            str(item) for item in row.get("artifact_hash_refs", []) if str(item)
        }
        declared_artifact_hash_refs = {
            str(item)
            for item in row.get("declared_artifact_hash_refs", [])
            if str(item)
        }
        undeclared_artifact_hash_refs = sorted(
            artifact_hash_refs - declared_artifact_hash_refs
        )
        if undeclared_artifact_hash_refs:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_RESEARCH_ARTIFACT_HASH_REF_UNDECLARED",
                    "Research replay span references artifact hashes outside the declared public roster.",
                    subject_id=paper_id,
                )
            )
        if row.get("cold_rerun_receipt_ref") is None:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_RESEARCH_COLD_RERUN_REF_MISSING",
                    "Research replay span has no cold-rerun receipt ref.",
                    subject_id=paper_id,
                )
            )

        span = PublicTraceSpan(
            span_id=f"span:{paper_id}",
            session_id=session_id,
            action_kind="research_replication_artifact_replay",
            sequence_index=sequence_index,
            episode_id=paper_id,
            observation_ref=str(row.get("contribution_decomposition_ref") or ""),
            authority_verdict_id=str(row.get("rubric_tree_ref") or ""),
            state_transition_ref=str(row.get("cold_rerun_receipt_ref") or ""),
            outcome=str(row.get("replication_status") or "unknown"),
            target_ref=str(row.get("scratch_repo_scaffold_ref") or ""),
            input_digest=_stable_digest(
                {
                    "paper_id": row.get("paper_id"),
                    "artifact_hash_refs": row.get("artifact_hash_refs"),
                    "metric_script_refs": row.get("metric_script_refs"),
                    "grader_report_ref": row.get("grader_report_ref"),
                    "cost_runtime_budget_ref": row.get("cost_runtime_budget_ref"),
                    "ablation_diff_ref": row.get("ablation_diff_ref"),
                    "failure_taxonomy_ref": row.get("failure_taxonomy_ref"),
                    "cold_rerun_receipt_ref": row.get("cold_rerun_receipt_ref"),
                }
            ),
            tool_name="research_replication_replay",
            source_ref="research_replication_rubric_artifact_replay_bundle",
        ).as_dict()
        span["paper_kind"] = row.get("paper_kind")
        span["artifact_hash_refs"] = sorted(artifact_hash_refs)
        span["declared_artifact_hash_refs"] = sorted(declared_artifact_hash_refs)
        span["metric_script_refs"] = [
            str(item) for item in row.get("metric_script_refs", []) if str(item)
        ]
        span["grader_report_ref"] = row.get("grader_report_ref")
        span["cost_runtime_budget_ref"] = row.get("cost_runtime_budget_ref")
        span["ablation_diff_ref"] = row.get("ablation_diff_ref")
        span["failure_taxonomy_ref"] = row.get("failure_taxonomy_ref")
        spans.append(span)

    status = PASS if not findings else BLOCKED
    action_kind_counts = Counter(span["action_kind"] for span in spans)
    outcome_counts = Counter(span["outcome"] for span in spans)
    coverage = {
        "contribution_decomposition_coverage": len(spans)
        == sum(1 for span in spans if span["observation_ref"]),
        "rubric_tree_coverage": len(spans)
        == sum(1 for span in spans if span["authority_verdict_id"]),
        "declared_artifact_hash_roster_coverage": len(spans)
        == sum(
            1
            for span in spans
            if set(span["artifact_hash_refs"]).issubset(
                set(span["declared_artifact_hash_refs"])
            )
            and span["declared_artifact_hash_refs"]
        ),
        "metric_script_coverage": len(spans)
        == sum(1 for span in spans if span["metric_script_refs"]),
        "grader_report_coverage": len(spans)
        == sum(1 for span in spans if span["grader_report_ref"]),
        "budget_receipt_coverage": len(spans)
        == sum(1 for span in spans if span["cost_runtime_budget_ref"]),
        "ablation_diff_coverage": len(spans)
        == sum(1 for span in spans if span["ablation_diff_ref"]),
        "failure_taxonomy_coverage": len(spans)
        == sum(1 for span in spans if span["failure_taxonomy_ref"]),
        "cold_rerun_coverage": len(spans)
        == sum(1 for span in spans if span["state_transition_ref"]),
        "body_in_receipt": False,
    }
    return {
        "schema_version": "public_agent_execution_trace_refactor_v0",
        "status": status,
        "source_refs": list(SOURCE_REFS),
        "source_symbols": list(SOURCE_SYMBOL_REFS),
        "target_refs": list(TARGET_REFS),
        "target_symbols": list(TARGET_SYMBOL_REFS),
        "source_faithful_refactor": {
            "source_ref": "system/lib/agent_execution_trace.py",
            "target_ref": "microcosm-substrate/src/microcosm_core/macro_tools/agent_execution_trace.py",
            "verification_mode": "extension_of_existing_public_refactor",
            "preserved_semantics": [
                "observable_action_span_rows",
                "authority_boundary_metadata",
                "sequence_ordered_trace",
                "audit_findings",
                "public_summary_counts",
                "artifact_hash_roster_refs",
                "cold_rerun_receipt_refs",
            ],
            "omitted_live_material": [
                "private paper bodies",
                "private data bodies",
                "hidden rubric bodies",
                "provider payload bodies",
                "original-author code bodies",
            ],
        },
        "authority_ceiling": AUTHORITY_CEILING,
        "input_ref": _display_path(input_path),
        "bundle_id": session_id,
        "protocol_id": protocol.get("protocol_id"),
        "span_count": len(spans),
        "spans": spans,
        "summary": {
            "session_count": 1,
            "total_span_count": len(spans),
            "action_kind_counts": dict(sorted(action_kind_counts.items())),
            "outcome_counts": dict(sorted(outcome_counts.items())),
            "finding_count": len(findings),
            "trace_digest": _stable_digest(spans),
        },
        "audit": {
            "findings": findings,
            "coverage": coverage,
            "finding_count": len(findings),
        },
        "body_in_receipt": False,
    }


def build_public_memory_conflict_trace(input_dir: str | Path) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path

    bundle = _load_memory_conflict_bundle(input_path)
    manifest = bundle["bundle_manifest"]
    protocol = bundle["projection_protocol"]
    session_id = str(manifest.get("bundle_id") or "public_memory_conflict_trace")
    required_event_fields = {
        "event_id",
        "episode_id",
        "episode_order",
        "memory_route_ref",
        "decision",
        "memory_subject_id",
        "evidence_handle_ref",
        "private_thread_ref",
        "metadata_only_ref",
        "body_exported",
        "source_authority_claim",
        "active_injection_adopted",
    }
    required_replay_fields = {
        "observation_id",
        "episode_id",
        "replay_group_id",
        "memory_enabled",
        "answer_hash",
        "cold_replay_receipt_ref",
        "evidence_used_refs",
        "body_in_receipt",
    }

    findings: list[dict[str, Any]] = []
    spans: list[dict[str, Any]] = []
    sorted_events = sorted(
        _rows(bundle["memory_episodes"], "memory_events"),
        key=lambda row: (
            int(row.get("episode_order") or 0),
            str(row.get("episode_id") or ""),
            str(row.get("event_id") or ""),
        ),
    )
    for sequence_index, row in enumerate(sorted_events):
        event_id = str(row.get("event_id") or f"memory_event_{sequence_index}")
        missing_fields = sorted(field for field in required_event_fields if field not in row)
        if missing_fields:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_MEMORY_EVENT_FIELDS_MISSING",
                    "Memory event span is missing public replay evidence refs.",
                    subject_id=event_id,
                )
            )
        if row.get("body_exported") is not False:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_MEMORY_PRIVATE_BODY_EXPORTED",
                    "Memory event span must keep private thread bodies out of the public trace.",
                    subject_id=event_id,
                )
            )
        if row.get("metadata_only_ref") is not True:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_MEMORY_REF_NOT_METADATA_ONLY",
                    "Memory event span must expose private thread material only as metadata refs.",
                    subject_id=event_id,
                )
            )
        if row.get("source_authority_claim") is not False:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_MEMORY_SOURCE_AUTHORITY_CLAIM",
                    "Memory event span cannot treat memory recall as source authority.",
                    subject_id=event_id,
                )
            )
        if row.get("active_injection_adopted") is not False:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_MEMORY_ACTIVE_INJECTION_AUTHORITY",
                    "Memory event span cannot adopt active injection as authority.",
                    subject_id=event_id,
                )
            )

        span = PublicTraceSpan(
            span_id=f"span:{event_id}",
            session_id=session_id,
            action_kind="memory_temporal_conflict_event",
            sequence_index=sequence_index,
            episode_id=str(row.get("episode_id") or ""),
            observation_ref=str(row.get("evidence_handle_ref") or ""),
            authority_verdict_id=str(
                row.get("conflict_edge_ref")
                or row.get("stale_downgrade_ref")
                or row.get("memory_route_ref")
                or ""
            ),
            state_transition_ref=str(
                row.get("stale_downgrade_ref")
                or row.get("conflict_edge_ref")
                or row.get("memory_route_ref")
                or ""
            ),
            outcome=str(row.get("decision") or "unknown"),
            target_ref=str(row.get("memory_route_ref") or ""),
            input_digest=_stable_digest(
                {
                    "event_id": row.get("event_id"),
                    "memory_route_ref": row.get("memory_route_ref"),
                    "decision": row.get("decision"),
                    "memory_subject_id": row.get("memory_subject_id"),
                    "evidence_handle_ref": row.get("evidence_handle_ref"),
                    "private_thread_ref": row.get("private_thread_ref"),
                    "metadata_only_ref": row.get("metadata_only_ref"),
                    "conflict_edge_ref": row.get("conflict_edge_ref"),
                    "stale_downgrade_ref": row.get("stale_downgrade_ref"),
                }
            ),
            tool_name="memory_temporal_conflict_replay",
            source_ref="agent_memory_temporal_conflict_replay_bundle",
        ).as_dict()
        span["memory_subject_id"] = row.get("memory_subject_id")
        span["private_thread_ref"] = row.get("private_thread_ref")
        span["metadata_only_ref"] = row.get("metadata_only_ref") is True
        span["body_in_receipt"] = False
        span["body_exported"] = row.get("body_exported") is True
        span["source_authority_claim"] = row.get("source_authority_claim") is True
        span["active_injection_adopted"] = row.get("active_injection_adopted") is True
        spans.append(span)

    replay_offset = len(spans)
    answer_delta = (
        bundle["replay_observations"].get("answer_delta", {})
        if isinstance(bundle["replay_observations"], dict)
        else {}
    )
    sorted_replays = sorted(
        _rows(bundle["replay_observations"], "replay_observations"),
        key=lambda row: str(row.get("observation_id") or ""),
    )
    for replay_index, row in enumerate(sorted_replays):
        sequence_index = replay_offset + replay_index
        observation_id = str(
            row.get("observation_id") or f"memory_replay_{replay_index}"
        )
        missing_fields = sorted(field for field in required_replay_fields if field not in row)
        if missing_fields:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_MEMORY_REPLAY_FIELDS_MISSING",
                    "Memory replay span is missing public replay evidence refs.",
                    subject_id=observation_id,
                )
            )
        if row.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_MEMORY_REPLAY_BODY_IN_RECEIPT",
                    "Memory replay span must keep answer bodies out of the public receipt.",
                    subject_id=observation_id,
                )
            )
        evidence_refs = [str(item) for item in row.get("evidence_used_refs", []) if str(item)]
        if row.get("memory_enabled") is True and not evidence_refs:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_MEMORY_ENABLED_WITHOUT_EVIDENCE",
                    "Memory-enabled replay span must cite public evidence handles.",
                    subject_id=observation_id,
                )
            )
        if not row.get("cold_replay_receipt_ref"):
            findings.append(
                _finding(
                    "PUBLIC_TRACE_MEMORY_COLD_REPLAY_REF_MISSING",
                    "Memory replay span has no cold-replay receipt ref.",
                    subject_id=observation_id,
                )
            )

        span = PublicTraceSpan(
            span_id=f"span:{observation_id}",
            session_id=session_id,
            action_kind="memory_temporal_conflict_cold_replay",
            sequence_index=sequence_index,
            episode_id=str(row.get("episode_id") or ""),
            observation_ref=str(answer_delta.get("delta_ref") or ""),
            authority_verdict_id=";".join(evidence_refs),
            state_transition_ref=str(row.get("cold_replay_receipt_ref") or ""),
            outcome="memory_enabled" if row.get("memory_enabled") is True else "memory_disabled",
            target_ref=str(row.get("replay_group_id") or ""),
            input_digest=_stable_digest(
                {
                    "observation_id": row.get("observation_id"),
                    "memory_enabled": row.get("memory_enabled"),
                    "answer_hash": row.get("answer_hash"),
                    "cold_replay_receipt_ref": row.get("cold_replay_receipt_ref"),
                    "evidence_used_refs": row.get("evidence_used_refs"),
                    "body_in_receipt": row.get("body_in_receipt"),
                }
            ),
            tool_name="memory_temporal_conflict_replay",
            source_ref="agent_memory_temporal_conflict_replay_bundle",
        ).as_dict()
        span["answer_hash"] = row.get("answer_hash")
        span["answer_delta_ref"] = answer_delta.get("delta_ref")
        span["evidence_used_refs"] = evidence_refs
        span["cold_replay_receipt_ref"] = row.get("cold_replay_receipt_ref")
        span["body_in_receipt"] = False
        spans.append(span)

    status = PASS if not findings else BLOCKED
    action_kind_counts = Counter(span["action_kind"] for span in spans)
    outcome_counts = Counter(span["outcome"] for span in spans)
    event_spans = [
        span for span in spans if span["action_kind"] == "memory_temporal_conflict_event"
    ]
    replay_spans = [
        span
        for span in spans
        if span["action_kind"] == "memory_temporal_conflict_cold_replay"
    ]
    coverage = {
        "memory_event_evidence_handle_coverage": len(event_spans)
        == sum(1 for span in event_spans if span["observation_ref"]),
        "metadata_only_private_thread_ref_coverage": len(event_spans)
        == sum(1 for span in event_spans if span.get("metadata_only_ref") is True),
        "no_private_memory_body_coverage": all(
            span.get("body_exported") is False for span in event_spans
        ),
        "cold_replay_receipt_coverage": len(replay_spans)
        == sum(1 for span in replay_spans if span["state_transition_ref"]),
        "answer_delta_coverage": len(replay_spans)
        == sum(1 for span in replay_spans if span.get("answer_delta_ref")),
        "memory_enabled_evidence_coverage": all(
            span.get("evidence_used_refs")
            for span in replay_spans
            if span["outcome"] == "memory_enabled"
        ),
        "body_in_receipt": False,
    }
    return {
        "schema_version": "public_agent_execution_trace_refactor_v0",
        "status": status,
        "source_refs": list(SOURCE_REFS),
        "source_symbols": list(SOURCE_SYMBOL_REFS),
        "target_refs": list(TARGET_REFS),
        "target_symbols": list(TARGET_SYMBOL_REFS),
        "source_faithful_refactor": {
            "source_ref": "system/lib/agent_execution_trace.py",
            "target_ref": "microcosm-substrate/src/microcosm_core/macro_tools/agent_execution_trace.py",
            "verification_mode": "extension_of_existing_public_refactor",
            "preserved_semantics": [
                "observable_action_span_rows",
                "authority_boundary_metadata",
                "sequence_ordered_trace",
                "audit_findings",
                "public_summary_counts",
                "metadata_only_private_refs",
                "cold_replay_receipt_refs",
            ],
            "omitted_live_material": [
                "private thread bodies",
                "private memory candidate bodies",
                "raw answer bodies",
                "active injection text",
                "provider payload bodies",
                "live user memory values",
            ],
        },
        "authority_ceiling": AUTHORITY_CEILING,
        "input_ref": _display_path(input_path),
        "bundle_id": session_id,
        "protocol_id": protocol.get("protocol_id"),
        "span_count": len(spans),
        "spans": spans,
        "summary": {
            "session_count": 1,
            "total_span_count": len(spans),
            "action_kind_counts": dict(sorted(action_kind_counts.items())),
            "outcome_counts": dict(sorted(outcome_counts.items())),
            "finding_count": len(findings),
            "trace_digest": _stable_digest(spans),
        },
        "audit": {
            "findings": findings,
            "coverage": coverage,
            "finding_count": len(findings),
        },
        "body_in_receipt": False,
    }


def build_public_mcp_tool_authority_trace(input_dir: str | Path) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path

    bundle = _load_mcp_tool_authority_bundle(input_path)
    manifest = bundle["bundle_manifest"]
    protocol = bundle["projection_protocol"]
    session_id = str(manifest.get("bundle_id") or "public_mcp_tool_authority_trace")
    required_call_fields = {
        "call_id",
        "tool_id",
        "tool_class",
        "capability_scope_ref",
        "call_arguments_hash",
        "approval_token_ref",
        "side_effect_class",
        "result_source_capsule_ref",
        "instruction_data_split_ref",
        "ledger_diff_ref",
        "rollback_receipt_ref",
        "cold_replay_receipt_ref",
        "live_account_access",
        "body_in_receipt",
        "private_ref_metadata_only",
        "untrusted_output_as_instruction",
        "credential_exported",
        "final_answer_only_grading",
    }

    findings: list[dict[str, Any]] = []
    spans: list[dict[str, Any]] = []
    tools_by_id = {
        str(row.get("tool_id") or ""): row
        for row in _rows(bundle["tool_manifest"], "tools")
    }
    results_by_call = {
        str(row.get("call_id") or ""): row
        for row in _rows(bundle["tool_results"], "tool_results")
    }
    side_effects_by_call = {
        str(row.get("call_id") or ""): row
        for row in _rows(bundle["side_effect_ledger"], "side_effects")
    }
    cold_replays_by_call = {
        str(row.get("call_id") or ""): row
        for row in _rows(bundle["cold_replay"], "cold_replays")
    }
    sorted_calls = sorted(
        _rows(bundle["tool_calls"], "tool_calls"),
        key=lambda row: str(row.get("call_id") or ""),
    )
    for sequence_index, row in enumerate(sorted_calls):
        call_id = str(row.get("call_id") or f"mcp_tool_call_{sequence_index}")
        tool_id = str(row.get("tool_id") or "")
        tool = tools_by_id.get(tool_id, {})
        result = results_by_call.get(call_id, {})
        side_effect = side_effects_by_call.get(call_id, {})
        cold_replay = cold_replays_by_call.get(call_id, {})
        missing_fields = sorted(field for field in required_call_fields if field not in row)
        if missing_fields:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_MCP_TOOL_CALL_FIELDS_MISSING",
                    "MCP tool call span is missing public authority evidence refs.",
                    subject_id=call_id,
                )
            )
        if not tool:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_MCP_TOOL_MANIFEST_REF_MISSING",
                    "MCP tool call span references a tool absent from the public manifest.",
                    subject_id=call_id,
                )
            )
        if row.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_MCP_TOOL_BODY_IN_RECEIPT",
                    "MCP tool call span must keep tool argument and result bodies out of the public receipt.",
                    subject_id=call_id,
                )
            )
        if row.get("private_ref_metadata_only") is not True:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_MCP_TOOL_PRIVATE_REF_NOT_METADATA_ONLY",
                    "MCP tool call span may expose private/account refs only as metadata refs.",
                    subject_id=call_id,
                )
            )
        for field, code, message in (
            (
                "live_account_access",
                "PUBLIC_TRACE_MCP_TOOL_LIVE_ACCOUNT_ACCESS",
                "MCP tool authority trace cannot claim live account access.",
            ),
            (
                "credential_exported",
                "PUBLIC_TRACE_MCP_TOOL_CREDENTIAL_EXPORT",
                "MCP tool authority trace cannot export credentials or credential-equivalent payloads.",
            ),
            (
                "untrusted_output_as_instruction",
                "PUBLIC_TRACE_MCP_TOOL_OUTPUT_AS_INSTRUCTION",
                "MCP tool authority trace cannot promote untrusted tool output into instruction authority.",
            ),
            (
                "final_answer_only_grading",
                "PUBLIC_TRACE_MCP_TOOL_FINAL_ANSWER_ONLY_GRADING",
                "MCP tool authority trace must cite tool, side-effect, rollback, and cold-replay evidence instead of final answers alone.",
            ),
        ):
            if row.get(field) is not False:
                findings.append(_finding(code, message, subject_id=call_id))

        is_write = row.get("side_effect_class") == "write"
        if is_write:
            if row.get("approval_token_ref") in {"", None, "missing", "not_required"}:
                findings.append(
                    _finding(
                        "PUBLIC_TRACE_MCP_TOOL_WRITE_APPROVAL_REF_MISSING",
                        "Write-capable MCP tool span must cite approval token refs before side effects.",
                        subject_id=call_id,
                    )
                )
            if not row.get("ledger_diff_ref") or not side_effect:
                findings.append(
                    _finding(
                        "PUBLIC_TRACE_MCP_TOOL_SIDE_EFFECT_LEDGER_REF_MISSING",
                        "Write-capable MCP tool span must cite a public side-effect ledger row.",
                        subject_id=call_id,
                    )
                )
            if not row.get("rollback_receipt_ref"):
                findings.append(
                    _finding(
                        "PUBLIC_TRACE_MCP_TOOL_ROLLBACK_REF_MISSING",
                        "Write-capable MCP tool span must cite rollback receipt refs.",
                        subject_id=call_id,
                    )
                )
        if row.get("tool_class") == "untrusted_result":
            if result.get("output_instruction_ignored") is not True:
                findings.append(
                    _finding(
                        "PUBLIC_TRACE_MCP_UNTRUSTED_OUTPUT_BOUNDARY_MISSING",
                        "Untrusted MCP tool result must be recorded as data only.",
                        subject_id=call_id,
                    )
                )
        if not cold_replay or cold_replay.get("status") != PASS:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_MCP_COLD_REPLAY_REF_MISSING",
                    "MCP tool call span must cite a passing cold-replay receipt.",
                    subject_id=call_id,
                )
            )

        span = PublicTraceSpan(
            span_id=f"span:{call_id}",
            session_id=session_id,
            action_kind="mcp_tool_authority_call",
            sequence_index=sequence_index,
            episode_id=call_id,
            observation_ref=str(row.get("result_source_capsule_ref") or ""),
            authority_verdict_id=str(row.get("approval_token_ref") or ""),
            state_transition_ref=str(row.get("ledger_diff_ref") or ""),
            outcome=(
                "approved_write"
                if is_write
                else "untrusted_result_data_only"
                if row.get("tool_class") == "untrusted_result"
                else "readonly_lookup"
            ),
            target_ref=str(row.get("capability_scope_ref") or ""),
            input_digest=_stable_digest(
                {
                    "call_id": row.get("call_id"),
                    "tool_id": row.get("tool_id"),
                    "tool_class": row.get("tool_class"),
                    "capability_scope_ref": row.get("capability_scope_ref"),
                    "call_arguments_hash": row.get("call_arguments_hash"),
                    "approval_token_ref": row.get("approval_token_ref"),
                    "side_effect_class": row.get("side_effect_class"),
                    "result_source_capsule_ref": row.get("result_source_capsule_ref"),
                    "instruction_data_split_ref": row.get("instruction_data_split_ref"),
                    "ledger_diff_ref": row.get("ledger_diff_ref"),
                    "rollback_receipt_ref": row.get("rollback_receipt_ref"),
                    "cold_replay_receipt_ref": row.get("cold_replay_receipt_ref"),
                }
            ),
            recovery_ref=str(row.get("rollback_receipt_ref") or ""),
            tool_name="mcp_tool_authority_replay",
            source_ref="mcp_tool_authority_replay_bundle",
        ).as_dict()
        span["tool_id"] = tool_id
        span["tool_class"] = row.get("tool_class")
        span["capability_scope_ref"] = row.get("capability_scope_ref")
        span["call_arguments_hash"] = row.get("call_arguments_hash")
        span["approval_token_ref"] = row.get("approval_token_ref")
        span["side_effect_class"] = row.get("side_effect_class")
        span["result_source_capsule_ref"] = row.get("result_source_capsule_ref")
        span["instruction_data_split_ref"] = row.get("instruction_data_split_ref")
        span["ledger_diff_ref"] = row.get("ledger_diff_ref")
        span["rollback_receipt_ref"] = row.get("rollback_receipt_ref")
        span["cold_replay_receipt_ref"] = row.get("cold_replay_receipt_ref")
        span["untrusted_output_as_instruction"] = (
            row.get("untrusted_output_as_instruction") is True
        )
        span["credential_exported"] = row.get("credential_exported") is True
        span["live_account_access"] = row.get("live_account_access") is True
        span["final_answer_only_grading"] = row.get("final_answer_only_grading") is True
        span["private_ref_metadata_only"] = row.get("private_ref_metadata_only") is True
        span["body_in_receipt"] = False
        span["tool_requires_approval"] = tool.get("requires_approval") is True
        span["tool_requires_rollback_receipt"] = (
            tool.get("requires_rollback_receipt") is True
        )
        span["untrusted_output_ignored"] = result.get("output_instruction_ignored") is True
        spans.append(span)

    status = PASS if not findings else BLOCKED
    action_kind_counts = Counter(span["action_kind"] for span in spans)
    outcome_counts = Counter(span["outcome"] for span in spans)
    write_spans = [span for span in spans if span.get("side_effect_class") == "write"]
    untrusted_spans = [
        span for span in spans if span.get("tool_class") == "untrusted_result"
    ]
    coverage = {
        "capability_scope_coverage": len(spans)
        == sum(1 for span in spans if span.get("capability_scope_ref")),
        "call_argument_hash_coverage": len(spans)
        == sum(1 for span in spans if span.get("call_arguments_hash")),
        "instruction_data_split_coverage": len(spans)
        == sum(1 for span in spans if span.get("instruction_data_split_ref")),
        "write_side_effect_approval_coverage": len(write_spans)
        == sum(1 for span in write_spans if span.get("approval_token_ref")),
        "write_side_effect_ledger_coverage": len(write_spans)
        == sum(1 for span in write_spans if span.get("ledger_diff_ref")),
        "rollback_receipt_coverage": len(write_spans)
        == sum(1 for span in write_spans if span.get("rollback_receipt_ref")),
        "cold_replay_receipt_coverage": len(spans)
        == sum(1 for span in spans if span.get("cold_replay_receipt_ref")),
        "untrusted_output_data_boundary_coverage": len(untrusted_spans)
        == sum(1 for span in untrusted_spans if span.get("untrusted_output_ignored")),
        "body_in_receipt": False,
    }
    return {
        "schema_version": "public_agent_execution_trace_refactor_v0",
        "status": status,
        "source_refs": list(SOURCE_REFS),
        "source_symbols": list(SOURCE_SYMBOL_REFS),
        "target_refs": list(TARGET_REFS),
        "target_symbols": list(TARGET_SYMBOL_REFS),
        "source_faithful_refactor": {
            "source_ref": "system/lib/agent_execution_trace.py",
            "target_ref": "microcosm-substrate/src/microcosm_core/macro_tools/agent_execution_trace.py",
            "verification_mode": "extension_of_existing_public_refactor",
            "preserved_semantics": [
                "observable_action_span_rows",
                "authority_boundary_metadata",
                "sequence_ordered_trace",
                "audit_findings",
                "public_summary_counts",
                "capability_scope_refs",
                "approval_token_refs",
                "side_effect_ledger_refs",
                "rollback_receipt_refs",
                "cold_replay_receipt_refs",
                "instruction_data_split_refs",
            ],
            "omitted_live_material": [
                "live MCP account bodies",
                "credential values and access tokens",
                "provider payload bodies",
                "raw tool payload bodies",
                "raw tool result bodies",
                "private account identifiers",
            ],
        },
        "authority_ceiling": AUTHORITY_CEILING,
        "input_ref": _display_path(input_path),
        "bundle_id": session_id,
        "protocol_id": protocol.get("protocol_id"),
        "span_count": len(spans),
        "spans": spans,
        "summary": {
            "session_count": 1,
            "total_span_count": len(spans),
            "action_kind_counts": dict(sorted(action_kind_counts.items())),
            "outcome_counts": dict(sorted(outcome_counts.items())),
            "finding_count": len(findings),
            "trace_digest": _stable_digest(spans),
        },
        "audit": {
            "findings": findings,
            "coverage": coverage,
            "finding_count": len(findings),
        },
        "body_in_receipt": False,
    }


def build_public_agentic_vulnerability_patch_proof_trace(
    input_dir: str | Path,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path

    bundle = _load_agentic_vulnerability_patch_proof_bundle(input_path)
    manifest = bundle["bundle_manifest"]
    protocol = bundle["projection_protocol"]
    session_id = str(
        manifest.get("bundle_id")
        or "public_agentic_vulnerability_patch_proof_trace"
    )
    hypotheses = {
        str(row.get("hypothesis_id")): row
        for row in _rows(bundle["issue_hypotheses"], "issue_hypotheses")
        if row.get("hypothesis_id")
    }
    targets = {
        str(row.get("target_id")): row
        for row in _rows(bundle["target_manifests"], "targets")
        if row.get("target_id")
    }
    sandbox_by_hypothesis = {
        str(row.get("hypothesis_id")): row
        for row in _rows(bundle["sandbox_policy_verdicts"], "sandbox_policy_verdicts")
        if row.get("hypothesis_id")
    }
    verifier_by_hypothesis: dict[str, list[dict[str, Any]]] = {}
    for row in _rows(bundle["verifier_receipts"], "verifier_receipts"):
        hypothesis_id = str(row.get("hypothesis_id") or "")
        verifier_by_hypothesis.setdefault(hypothesis_id, []).append(row)
    replayed_hypotheses = {
        str(row.get("hypothesis_id"))
        for row in _rows(bundle["cold_replay"], "cold_replay")
        if row.get("hypothesis_id") and row.get("pass_label") is True
    }
    patch_by_hypothesis = {
        str(row.get("hypothesis_id")): row
        for row in _rows(bundle["patch_diffs"], "patch_diffs")
        if row.get("hypothesis_id")
    }
    tests_by_patch = {
        str(row.get("patch_id")): row
        for row in _rows(bundle["regression_tests"], "regression_tests")
        if row.get("patch_id")
    }

    findings: list[dict[str, Any]] = []
    spans: list[dict[str, Any]] = []
    sorted_traces = sorted(
        _rows(bundle["trace_evidence"], "trace_evidence"),
        key=lambda row: (
            str(row.get("hypothesis_id") or ""),
            str(row.get("trace_id") or ""),
        ),
    )
    for sequence_index, row in enumerate(sorted_traces):
        trace_id = str(row.get("trace_id") or f"trace_{sequence_index}")
        hypothesis_id = str(row.get("hypothesis_id") or "")
        hypothesis = hypotheses.get(hypothesis_id, {})
        target_id = str(row.get("target_id") or hypothesis.get("target_id") or "")
        sandbox = sandbox_by_hypothesis.get(hypothesis_id, {})
        verifier_rows = verifier_by_hypothesis.get(hypothesis_id, [])
        patch = patch_by_hypothesis.get(hypothesis_id, {})
        test = tests_by_patch.get(str(patch.get("patch_id") or ""), {})
        verdict = str(sandbox.get("policy_verdict") or "missing_sandbox_verdict")
        verifier_result = (
            str(verifier_rows[0].get("result"))
            if verifier_rows
            else "missing_verifier_receipt"
        )
        if hypothesis_id not in hypotheses:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_AGENTIC_VULN_HYPOTHESIS_REF_MISSING",
                    "Trace evidence has no matching vulnerability hypothesis.",
                    subject_id=trace_id,
                )
            )
        if target_id not in targets:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_AGENTIC_VULN_TARGET_REF_MISSING",
                    "Trace evidence has no matching synthetic target row.",
                    subject_id=trace_id,
                )
            )
        if hypothesis_id not in sandbox_by_hypothesis:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_AGENTIC_VULN_SANDBOX_VERDICT_REF_MISSING",
                    "Trace evidence has no matching pre-action sandbox verdict.",
                    subject_id=trace_id,
                )
            )
        if verifier_result == "missing_verifier_receipt":
            findings.append(
                _finding(
                    "PUBLIC_TRACE_AGENTIC_VULN_VERIFIER_RECEIPT_REF_MISSING",
                    "Trace evidence has no matching verifier receipt.",
                    subject_id=trace_id,
                )
            )
        if hypothesis_id not in replayed_hypotheses:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_AGENTIC_VULN_COLD_REPLAY_REF_MISSING",
                    "Trace evidence is not covered by a passing cold replay row.",
                    subject_id=trace_id,
                )
            )
        if patch and not test:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_AGENTIC_VULN_REGRESSION_TEST_REF_MISSING",
                    "Patch proof has no matching regression test row.",
                    subject_id=trace_id,
                )
            )
        if sandbox.get("pre_action") is not True:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_AGENTIC_VULN_SANDBOX_NOT_PRE_ACTION",
                    "Patch-proof sandbox verdict must precede replay action.",
                    subject_id=trace_id,
                )
            )

        if verifier_result == "false_positive":
            outcome = "false_positive"
        elif verdict == "allow_synthetic_patch" and verifier_result == "pass":
            outcome = "patch_verified"
        elif verdict == "review":
            outcome = "review"
        else:
            outcome = verifier_result

        span = PublicTraceSpan(
            span_id=f"span:{trace_id}",
            session_id=session_id,
            action_kind=str(row.get("trace_type") or "patch_proof_trace"),
            sequence_index=sequence_index,
            episode_id=hypothesis_id,
            observation_ref=str(row.get("evidence_ref") or ""),
            authority_verdict_id=str(sandbox.get("verdict_id") or ""),
            state_transition_ref=str(
                verifier_rows[0].get("receipt_ref") if verifier_rows else ""
            ),
            outcome=outcome,
            target_ref=target_id,
            input_digest=_stable_digest(
                {
                    "trace_id": trace_id,
                    "hypothesis_id": hypothesis_id,
                    "target_id": target_id,
                    "evidence_ref": row.get("evidence_ref"),
                    "patch_id": patch.get("patch_id"),
                    "test_id": test.get("test_id"),
                }
            ),
            recovery_ref=str(patch.get("diff_hash_ref") or ""),
            tool_name="agentic_vulnerability_patch_proof_replay",
            source_ref="agentic_vulnerability_discovery_patch_proof_replay_bundle",
        ).as_dict()
        span["hypothesis_id"] = hypothesis_id
        span["patch_id"] = patch.get("patch_id")
        span["regression_test_id"] = test.get("test_id")
        span["sandbox_policy_verdict"] = verdict
        span["verifier_result"] = verifier_result
        span["exploitability_body_exported"] = False
        spans.append(span)

    status = PASS if not findings else BLOCKED
    action_kind_counts = Counter(span["action_kind"] for span in spans)
    outcome_counts = Counter(span["outcome"] for span in spans)
    coverage = {
        "hypothesis_ref_coverage": len(spans)
        == sum(1 for span in spans if span["hypothesis_id"] in hypotheses),
        "synthetic_target_ref_coverage": len(spans)
        == sum(1 for span in spans if span["target_refs"] and span["target_refs"][0] in targets),
        "sandbox_verdict_coverage": len(spans)
        == sum(1 for span in spans if span["hypothesis_id"] in sandbox_by_hypothesis),
        "verifier_receipt_coverage": len(spans)
        == sum(1 for span in spans if span["hypothesis_id"] in verifier_by_hypothesis),
        "cold_replay_coverage": len(spans)
        == sum(1 for span in spans if span["hypothesis_id"] in replayed_hypotheses),
        "body_in_receipt": False,
    }
    return {
        "schema_version": "public_agent_execution_trace_refactor_v0",
        "status": status,
        "source_refs": list(SOURCE_REFS),
        "source_symbols": list(SOURCE_SYMBOL_REFS),
        "target_refs": list(TARGET_REFS),
        "target_symbols": list(TARGET_SYMBOL_REFS),
        "source_faithful_refactor": {
            "source_ref": "system/lib/agent_execution_trace.py",
            "target_ref": "microcosm-substrate/src/microcosm_core/macro_tools/agent_execution_trace.py",
            "verification_mode": "extension_of_existing_public_refactor",
            "preserved_semantics": [
                "observable_action_span_rows",
                "authority_boundary_metadata",
                "sequence_ordered_trace",
                "audit_findings",
                "public_summary_counts",
                "synthetic_target_refs",
                "sandbox_policy_verdict_refs",
                "verifier_receipt_refs",
                "cold_replay_refs",
            ],
            "omitted_live_material": [
                "live target bodies",
                "real CVE exploitation details",
                "weaponized exploit payloads",
                "credentials or account state",
                "provider payload bodies",
                "raw issue bodies",
                "raw patch bodies",
            ],
        },
        "authority_ceiling": AUTHORITY_CEILING,
        "input_ref": _display_path(input_path),
        "bundle_id": session_id,
        "protocol_id": protocol.get("protocol_id"),
        "span_count": len(spans),
        "spans": spans,
        "summary": {
            "session_count": 1,
            "total_span_count": len(spans),
            "action_kind_counts": dict(sorted(action_kind_counts.items())),
            "outcome_counts": dict(sorted(outcome_counts.items())),
            "finding_count": len(findings),
            "trace_digest": _stable_digest(spans),
        },
        "audit": {
            "findings": findings,
            "coverage": coverage,
            "finding_count": len(findings),
        },
        "body_in_receipt": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    computer_use = subparsers.add_parser("computer-use")
    computer_use.add_argument("--input", required=True)
    computer_use.add_argument("--pretty", action="store_true")
    sandbox_policy = subparsers.add_parser("sandbox-policy")
    sandbox_policy.add_argument("--input", required=True)
    sandbox_policy.add_argument("--pretty", action="store_true")
    research_replication = subparsers.add_parser("research-replication")
    research_replication.add_argument("--input", required=True)
    research_replication.add_argument("--pretty", action="store_true")
    memory_conflict = subparsers.add_parser("memory-conflict")
    memory_conflict.add_argument("--input", required=True)
    memory_conflict.add_argument("--pretty", action="store_true")
    mcp_tool_authority = subparsers.add_parser("mcp-tool-authority")
    mcp_tool_authority.add_argument("--input", required=True)
    mcp_tool_authority.add_argument("--pretty", action="store_true")
    agentic_vulnerability = subparsers.add_parser("agentic-vulnerability-patch-proof")
    agentic_vulnerability.add_argument("--input", required=True)
    agentic_vulnerability.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "computer-use":
        payload = build_public_computer_use_trace(args.input)
        indent = 2 if args.pretty else None
        print(json.dumps(payload, indent=indent, sort_keys=True))
        return 0 if payload["status"] == PASS else 1
    if args.command == "sandbox-policy":
        payload = build_public_sandbox_policy_trace(args.input)
        indent = 2 if args.pretty else None
        print(json.dumps(payload, indent=indent, sort_keys=True))
        return 0 if payload["status"] == PASS else 1
    if args.command == "research-replication":
        payload = build_public_research_replication_trace(args.input)
        indent = 2 if args.pretty else None
        print(json.dumps(payload, indent=indent, sort_keys=True))
        return 0 if payload["status"] == PASS else 1
    if args.command == "memory-conflict":
        payload = build_public_memory_conflict_trace(args.input)
        indent = 2 if args.pretty else None
        print(json.dumps(payload, indent=indent, sort_keys=True))
        return 0 if payload["status"] == PASS else 1
    if args.command == "mcp-tool-authority":
        payload = build_public_mcp_tool_authority_trace(args.input)
        indent = 2 if args.pretty else None
        print(json.dumps(payload, indent=indent, sort_keys=True))
        return 0 if payload["status"] == PASS else 1
    if args.command == "agentic-vulnerability-patch-proof":
        payload = build_public_agentic_vulnerability_patch_proof_trace(args.input)
        indent = 2 if args.pretty else None
        print(json.dumps(payload, indent=indent, sort_keys=True))
        return 0 if payload["status"] == PASS else 1
    raise AssertionError(args.command)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
