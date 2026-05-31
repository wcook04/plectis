"""
Reusable strict JSON helpers and artifact classification.

This module owns duplicate-key JSON parsing and lightweight artifact-class
reporting for authority/projection surfaces. Ledger-specific event-chain rules
stay in their owning ledgers.
"""
from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


class StrictJsonError(ValueError):
    """Raised when a strict JSON artifact cannot be parsed safely."""


class DuplicateJsonKeyError(StrictJsonError):
    """Raised when a JSON object repeats the same key."""


class StrictJsonObjectError(StrictJsonError):
    """Raised when a JSONL row must be an object but is not."""


@dataclass(frozen=True)
class JsonArtifactRule:
    artifact_class: str
    authority: str
    duplicate_key_policy: str
    event_chain_policy: str
    rebuild_check: str
    owner_tool: str | None
    dirty_tree_policy: str
    failure_behavior: str
    patterns: tuple[str, ...]

    def to_row(self) -> dict[str, Any]:
        return {
            "artifact_class": self.artifact_class,
            "authority": self.authority,
            "duplicate_key_policy": self.duplicate_key_policy,
            "event_chain_policy": self.event_chain_policy,
            "rebuild_check": self.rebuild_check,
            "owner_tool": self.owner_tool,
            "dirty_tree_policy": self.dirty_tree_policy,
            "failure_behavior": self.failure_behavior,
            "patterns": list(self.patterns),
        }


ARTIFACT_RULES: tuple[JsonArtifactRule, ...] = (
    JsonArtifactRule(
        artifact_class="task_ledger_event_jsonl",
        authority="state/task_ledger/events.jsonl",
        duplicate_key_policy="fail",
        event_chain_policy="validate_previous_event_hash_and_event_hash",
        rebuild_check="./repo-python tools/meta/factory/task_ledger_project.py rebuild --check",
        owner_tool="./repo-python tools/meta/factory/task_ledger_apply.py",
        dirty_tree_policy="strict_validation_if_touched",
        failure_behavior="block_commit_until_repaired_or_residual_captured",
        patterns=("state/task_ledger/events.jsonl",),
    ),
    JsonArtifactRule(
        artifact_class="prompt_trace_event_jsonl",
        authority="state/prompt_ledger/events.jsonl",
        duplicate_key_policy="fail",
        event_chain_policy="validate_previous_event_hash_and_event_hash",
        rebuild_check="./repo-python tools/meta/observability/prompt_ledger.py rebuild --check",
        owner_tool="./repo-python tools/meta/observability/prompt_ledger.py",
        dirty_tree_policy="strict_validation_if_touched",
        failure_behavior="block_commit_until_repaired_or_residual_captured",
        patterns=("state/prompt_ledger/events.jsonl",),
    ),
    JsonArtifactRule(
        artifact_class="work_ledger_event_jsonl",
        authority="codex/ledger/*/work_ledger.jsonl",
        duplicate_key_policy="fail",
        event_chain_policy="owner_tool_validation_when_available",
        rebuild_check="./repo-python tools/meta/factory/work_ledger.py session-status --overview",
        owner_tool="./repo-python tools/meta/factory/work_ledger.py",
        dirty_tree_policy="strict_validation_if_touched",
        failure_behavior="block_destructive_or_conflicting_session_mutation",
        patterns=("codex/ledger/*/work_ledger.jsonl",),
    ),
    JsonArtifactRule(
        artifact_class="generated_projection_json",
        authority="owning event log or source artifact",
        duplicate_key_policy="fail",
        event_chain_policy="not_applicable",
        rebuild_check="owner_tool_rebuild_check_required",
        owner_tool="owner_tool_registry",
        dirty_tree_policy="owner_tool_or_adoption_receipt_required_if_targeted",
        failure_behavior="do_not_hand_edit_projection",
        patterns=(
            "state/task_ledger/ledger.json",
            "state/task_ledger/sign_offs.json",
            "state/task_ledger/views/*.json",
            "state/prompt_ledger/ledger.json",
            "state/prompt_ledger/views/*.json",
            "codex/ledger/*/work_ledger_index.json",
        ),
    ),
    JsonArtifactRule(
        artifact_class="standard_json",
        authority="codex/standards/*.json",
        duplicate_key_policy="fail",
        event_chain_policy="not_applicable",
        rebuild_check="strict_json_parse",
        owner_tool=None,
        dirty_tree_policy="strict_validation_if_touched",
        failure_behavior="block_commit_until_schema_or_duplicate_key_failure_is_fixed",
        patterns=("codex/standards/*.json", "codex/standards/**/*.json"),
    ),
    JsonArtifactRule(
        artifact_class="provider_receipt_json",
        authority="provider receipt event log or receipt file",
        duplicate_key_policy="fail",
        event_chain_policy="drift_fuse_required_when_adopted",
        rebuild_check="provider_owner_tool_when_available",
        owner_tool=None,
        dirty_tree_policy="strict_validation_if_touched_once_adopted",
        failure_behavior="block_adoption_until_receipt_is_valid",
        patterns=("state/provider_receipts/**/*.json", "state/provider_receipts/**/*.jsonl"),
    ),
    JsonArtifactRule(
        artifact_class="runtime_run_artifact_json",
        authority="run-producing tool and run summary under state/runs/<run_id>",
        duplicate_key_policy="fail",
        event_chain_policy="not_applicable_unless_declared",
        rebuild_check="run_artifact_owner_or_strict_json_parse",
        owner_tool=None,
        dirty_tree_policy="preserve_unrelated_runtime_receipts_validate_if_adopted",
        failure_behavior="do_not_treat_index_named_run_receipts_as_generated_projection_owner_gaps",
        patterns=("state/runs/**/*.json", "state/runs/**/*.jsonl"),
    ),
    JsonArtifactRule(
        artifact_class="raw_seed_projection_json",
        authority="raw seed owner lane",
        duplicate_key_policy="fail",
        event_chain_policy="not_applicable",
        rebuild_check="raw_seed_owner_tool_required",
        owner_tool="raw_seed_projection_owner_tool",
        dirty_tree_policy="preserve_unless_owner_tool_scoped",
        failure_behavior="do_not_hand_edit_raw_operator_voice_or_generated_projection",
        patterns=("obsidian/**/raw_seed/**/*.json", "codex/hologram/raw_seed_projection/*.json"),
    ),
    JsonArtifactRule(
        artifact_class="synth_seed_json",
        authority="phase synth_seed.json",
        duplicate_key_policy="fail",
        event_chain_policy="not_applicable",
        rebuild_check="./repo-python kernel.py --sync-synth <phase>",
        owner_tool="./repo-python kernel.py --sync-synth",
        dirty_tree_policy="strict_validation_if_touched",
        failure_behavior="block_sync_until_duplicate_key_or_schema_failure_is_fixed",
        patterns=("obsidian/**/synth_seed.json",),
    ),
)


def _reject_duplicate_keys(source: str):
    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        seen: dict[str, Any] = {}
        for key, value in pairs:
            if key in seen:
                raise DuplicateJsonKeyError(f"{source}: duplicate JSON key {key!r}")
            seen[key] = value
        return seen

    return hook


def loads_json_strict(text: str, *, source: str = "<json>") -> Any:
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys(source))
    except DuplicateJsonKeyError:
        raise
    except json.JSONDecodeError as exc:
        raise StrictJsonError(f"{source}: invalid JSON: {exc}") from exc


def read_json_strict(path: Path) -> Any:
    return loads_json_strict(path.read_text(encoding="utf-8"), source=str(path))


def read_jsonl_strict(path: Path, *, require_object: bool = True) -> list[Any]:
    rows: list[Any] = []
    if not path.exists():
        return rows
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        item = loads_json_strict(line, source=f"{path}:{line_number}")
        if require_object and not isinstance(item, dict):
            raise StrictJsonObjectError(f"{path}:{line_number} is not a JSON object")
        rows.append(item)
    return rows


def _matches_pattern(rel_path: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(rel_path, pattern) or Path(rel_path).match(pattern) or rel_path == pattern


def artifact_rule_for_path(path: str | Path) -> JsonArtifactRule | None:
    rel_path = str(path).lstrip("./")
    for rule in ARTIFACT_RULES:
        if any(_matches_pattern(rel_path, pattern) for pattern in rule.patterns):
            return rule
    return None


def artifact_class_for_path(path: str | Path) -> str:
    rule = artifact_rule_for_path(path)
    return rule.artifact_class if rule is not None else "unknown_json_artifact"


def strict_json_artifact_report(paths: Iterable[str | Path]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    class_counts: dict[str, int] = {}
    unknown_paths: list[str] = []
    for raw_path in paths:
        rel_path = str(raw_path).lstrip("./")
        rule = artifact_rule_for_path(rel_path)
        if rule is None:
            artifact_class = "unknown_json_artifact"
            row: dict[str, Any] = {
                "path": rel_path,
                "artifact_class": artifact_class,
                "strict_validation_required": rel_path.endswith((".json", ".jsonl")),
                "owner_tool_required": False,
            }
            unknown_paths.append(rel_path)
        else:
            artifact_class = rule.artifact_class
            row = rule.to_row()
            row.update(
                {
                    "path": rel_path,
                    "strict_validation_required": rule.duplicate_key_policy == "fail",
                    "owner_tool_required": bool(rule.owner_tool),
                }
            )
        rows.append(row)
        class_counts[artifact_class] = class_counts.get(artifact_class, 0) + 1

    return {
        "schema_version": "strict_json_artifact_report_v1",
        "checked_count": len(rows),
        "class_counts": class_counts,
        "unknown_paths": unknown_paths,
        "items": rows,
    }


def artifact_rules_payload() -> list[dict[str, Any]]:
    return [rule.to_row() for rule in ARTIFACT_RULES]
