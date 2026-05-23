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

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "span_id": self.span_id,
            "agent": "microcosm_public_fixture",
            "session_id": self.session_id,
            "action_kind": self.action_kind,
            "sequence_index": self.sequence_index,
            "turn_index": self.sequence_index,
            "tool_name": "computer_use_action",
            "duration_ms": 0,
            "outcome": self.outcome,
            "episode_id": self.episode_id,
            "observation_ref": self.observation_ref,
            "authority_verdict_id": self.authority_verdict_id,
            "state_transition_ref": self.state_transition_ref,
            "target_refs": [self.target_ref] if self.target_ref else [],
            "input_digest": self.input_digest,
            "source_ref": "computer_use_action_trace_bundle",
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    computer_use = subparsers.add_parser("computer-use")
    computer_use.add_argument("--input", required=True)
    computer_use.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "computer-use":
        payload = build_public_computer_use_trace(args.input)
        indent = 2 if args.pretty else None
        print(json.dumps(payload, indent=indent, sort_keys=True))
        return 0 if payload["status"] == PASS else 1
    raise AssertionError(args.command)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
