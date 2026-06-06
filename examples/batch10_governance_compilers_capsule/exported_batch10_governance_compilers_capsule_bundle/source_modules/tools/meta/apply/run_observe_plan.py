#!/usr/bin/env python3
"""
[PURPOSE]
- Teleology: Run grouped observe plans from the CLI/runtime surface and persist browseable observe history plus bridge/runtime sidecars.
- Mechanism: Validate and enrich observe-plan payloads, execute tools.meta.apply in observe mode, optionally dispatch grouped bridge prompts, validate responses, and write result/history/runtime artifacts.

[INTERFACE]
- Exports: preflight_observe_plan, run_once, main.
- Reads: observe plan JSON, referenced target/context files, prompt catalog state, bridge/runtime policy, and optional resume metadata.
- Writes: observe_result.json, grouped observe dumps and response artifacts, grouped runtime manifests, bridge dispatch sidecars, and observe history index pages.

[FLOW]
- Orders: preflight_observe_plan() checks file/dependency/runtime readiness -> run_once() enriches and executes the grouped observe plan -> bridge helpers persist per-group runtime and response surfaces -> main() exposes the CLI contract and exit semantics.
- When-needed: Open when a grouped observe plan needs direct CLI execution, preflight diagnostics, bridge prompt shaping, or observe-history persistence outside the ObserveSessionPlan runtime.
- When-needed: Open when tracing terminal-state gating that depends on the exact `TERMINAL_GROUP_STATUSES` constant shared across grouped observe dispatch, dependency release, and resume-aware completion checks.
- Escalates-to: tools/meta/apply/observe_session.py::MetaSessionOrchestratorImpl.run; tools/meta/apply/observe_session_runner.py::run_session_once.
- Navigation-group: observe_apply.

[DEPENDENCIES]
- Couples: tools/meta/apply/observe_session.py reuses this module's prompt construction, bridge dispatch, continuation, and response-validation helpers.
- Couples: tools/meta/bridge/dispatch_validator.py adds bridge capability-matrix gating to the local preflight path.

[CONSTRAINTS]
- Guarantee: Supports optional sentence caps for prompt shaping, with uncapped prompts by default, while always persisting grouped observe artifacts on disk.
- Orders: Group dependency state, bridge runtime manifests, and result-note routing are derived from the authored plan before downstream continuation surfaces are emitted.
- Non-goal: This module does not replace the ObserveSessionPlan runtime for phase-aware orchestration; it remains the grouped observe-plan execution surface.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
from collections import Counter
import hashlib
import json
import os
import re
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from system.lib.observe_memory import (
    _extract_heading_sections,
    _section_items,
    extract_pending_items_from_text,
)
from system.lib.json_payloads import (
    json_candidate_blocks,
    repair_unescaped_inner_quotes,
)
from system.lib.observe_prompt_catalog import load_prompt_catalog, prompt_contract_metadata
from system.lib.bridge_routes import bridge_timeout_seconds, merge_bridge_config_with_route
from system.lib.observe_runtime import (
    append_jsonl,
    grouped_observe_waves,
    grouped_runtime_path,
    latest_bridge_transport,
    load_grouped_runtime_manifest,
    normalize_context_merge_mode,
    normalize_launch_profile,
    now_iso,
    observe_runtime_policy,
    observe_cycle_timeline_path,
    promote_grouped_observe_state,
    resolve_effective_workers,
    resolve_bridge_prompt_budget,
    resolve_group_evidence_contract,
    resolve_grouped_runtime_manifest_path,
    write_json as write_runtime_json,
    write_grouped_runtime_manifest,
)
from system.lib.observe_visuals import observe_lane_color
from system.lib.agent_providers import resolve_provider_callable
from system.lib.markdown_routing import (
    apply_reference_to_text,
    apply_promotion_to_text,
    create_note_from_payload,
    extract_observe_artifact_payload,
    extract_section,
    format_repo_path,
    markdown_kind,
    normalize_route_config,
    normalize_repo_relative_path,
    render_markdown_document,
    resolve_reference_maps,
    validate_route_payload,
)
from system.lib.observe_surfaces import build_grouped_observe_continuation
from system.lib.response_surfaces import (
    parse_surface_response,
    project_response_surface_payload,
    render_response_surface_template,
    resolve_response_surface,
    response_surface_sidecar_path,
)
from system.lib.bridge_provider_pressure import (
    call_with_provider_claim,
    provider_unavailable_failure,
    record_provider_interrupt,
)
from tools.meta.bridge.provider_capabilities import CapabilityError, get_provider


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "master_config.json").exists():
            return parent
    return Path.cwd().resolve()


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_prompt_catalog_for_repo(repo_root: Path) -> dict[str, dict[str, Any]]:
    path = repo_root / "codex" / "standards" / "observe" / "observe_prompts.json"
    if not path.exists():
        return {}
    try:
        return load_prompt_catalog(path)
    except Exception:
        return {}


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    write_runtime_json(path, payload)


def _text_sha256(text: str) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()


def _bridge_dispatch_sidecar_path(primary_artifact_path: Path) -> Path:
    return primary_artifact_path.with_name(f"{primary_artifact_path.stem}_bridge_dispatch.json")


TERMINAL_GROUP_STATUSES = {"success", "quality_error", "error", "aborted", "blocked", "skipped_no_dump", "skipped_missing_dump"}
FAILED_GROUP_STATUSES = {"quality_error", "error", "aborted", "blocked"}
# Statuses that should block downstream groups. quality_error is excluded because
# the probe DID produce a response file with usable content — downstream synthesis
# groups can still consume it. Only hard failures (no response at all) block.
BLOCKING_GROUP_STATUSES = {"error", "aborted", "blocked"}
SUCCESS_GROUP_STATUSES = {"success"}
_RETRY_RESET_GROUP_FIELDS = (
    "runtime_state",
    "response_status",
    "response_file",
    "response_dump_chars",
    "response_prompt_chars",
    "response_dump_truncated",
    "response_body",
    "response_error",
    "response_error_category",
    "response_error_stage",
    "response_quality_status",
    "response_quality_issues",
    "response_quality_detected_issues",
    "response_quality_repair_actions",
    "response_quality_required_sections",
    "response_quality_missing_sections",
    "response_surface_kind",
    "response_kind",
    "response_surface_file",
    "response_receipt_file",
    "response_dispatch_file",
    "next_fork",
    "next_fork_block",
    "next_action",
    "continuation_hint",
    "continuation_source",
    "operator_decisions_pending",
    "agent_followups_pending",
)


def _response_receipt_sidecar_path(response_artifact: Path) -> Path:
    return response_artifact.with_name(f"{response_artifact.stem}.receipt.json")


def _json_candidate_blocks(text: str) -> List[str]:
    return json_candidate_blocks(text)


def _normalize_payload_keys(
    payload: Any,
    schema: Mapping[str, Any],
) -> Any:
    """Return *payload* with top-level keys renamed to match *schema* fields.

    ChatGPT often uses Title Case or space-separated keys (``"Files Examined"``)
    instead of the snake_case names the schema declares (``"files_examined"``).
    This function normalises both the payload and the schema keys to
    ``lower_snake_case`` and renames mismatched payload keys to their canonical
    schema names so that downstream validation succeeds.

    Only top-level keys are normalised; nested payloads are returned as-is.
    """
    if not isinstance(payload, Mapping) or not isinstance(schema, Mapping):
        return payload

    def to_snake(k: str) -> str:
        return str(k).lower().replace(" ", "_").replace("-", "_")

    props: Mapping[str, Any] = schema.get("properties") or {}
    required: List[str] = [str(r) for r in (schema.get("required") or [])]
    canonical_keys = set(props.keys()) | set(required)

    # Build lookup: normalised_form → canonical schema key
    canonical_norm: Dict[str, str] = {to_snake(k): k for k in canonical_keys}

    result: Dict[str, Any] = {}
    for key, value in payload.items():
        norm = to_snake(key)
        canonical = canonical_norm.get(norm, key)  # remap if known, else keep
        result[canonical] = value
    return result


def _extract_schema_payload(
    response_text: str,
    schema: Mapping[str, Any] | None = None,
) -> Tuple[Any, List[str]]:
    """Extract JSON from *response_text*.  When *schema* is provided, all
    candidates are tried and the one with fewest schema violations wins.
    This prevents small JSON fragments in prethinking prose from shadowing
    the actual receipt payload deeper in the response.

    Two extra passes are applied when plain candidates fail:

    * **Repair pass** — the full source text is repaired with
      :func:`repair_unescaped_inner_quotes` (handles ChatGPT anchor strings
      containing embedded double-quotes that prevent ``raw_decode`` from
      finding the top-level ``{``).
    * **Key-normalisation** — each extracted object is passed through
      :func:`_normalize_payload_keys` so Title-Case / space-separated keys
      from the AI are mapped to the snake_case names the schema declares.
    """

    def _candidates_for(text: str) -> List[str]:
        return _json_candidate_blocks(text)

    def _extract_named_value(source_text: str, field_name: str) -> Any:
        pattern = re.compile(rf'"{re.escape(field_name)}"\s*:\s*')
        decoder = json.JSONDecoder()
        for match in pattern.finditer(source_text):
            suffix = source_text[match.end():].lstrip()
            if not suffix:
                continue
            repaired_suffix = repair_unescaped_inner_quotes(suffix)
            try:
                value, _end = decoder.raw_decode(repaired_suffix)
                return value
            except json.JSONDecodeError:
                continue
        return None

    def _salvage_object_payload(source_text: str, object_schema: Mapping[str, Any]) -> Any:
        if str(object_schema.get("type") or "").strip() != "object":
            return None
        properties = object_schema.get("properties") if isinstance(object_schema.get("properties"), Mapping) else {}
        required = [str(item).strip() for item in object_schema.get("required", []) if str(item).strip()]
        field_names = list(dict.fromkeys([*required, *properties.keys()]))
        recovered: Dict[str, Any] = {}
        for field_name in field_names:
            value = _extract_named_value(source_text, field_name)
            if value is not None:
                recovered[field_name] = value
        return recovered or None

    def _candidate_score(payload: Any, issues: List[str], *, expected_type: str) -> Tuple[int, int, int, int, int]:
        type_penalty = 0
        if expected_type == "object" and not isinstance(payload, Mapping):
            type_penalty = 1
        elif expected_type == "array" and not isinstance(payload, list):
            type_penalty = 1

        required_hits = 0
        property_hits = 0
        payload_size = 0
        if isinstance(payload, Mapping) and isinstance(schema, Mapping):
            payload_keys = set(payload.keys())
            required = [str(item).strip() for item in schema.get("required", []) if str(item).strip()]
            properties = schema.get("properties") if isinstance(schema.get("properties"), Mapping) else {}
            required_hits = sum(1 for key in required if key in payload_keys)
            property_hits = sum(1 for key in properties if key in payload_keys)
            payload_size = len(payload_keys)
        elif isinstance(payload, list):
            payload_size = len(payload)
        return (type_penalty, len(issues), -required_hits, -property_hits, -payload_size)

    def _try_candidates(
        cands: List[str],
        *,
        expected_type: str,
        normalize: bool = False,
    ) -> Tuple[Any, List[str], bool]:
        """Return (best_payload, best_issues, found_any_parseable)."""
        best_payload: Any = None
        best_score: Tuple[int, int] | None = None
        best_issues: List[str] | None = None
        any_parsed = False
        for candidate in cands:
            try:
                payload = json.loads(candidate)
                any_parsed = True
            except json.JSONDecodeError:
                continue
            if schema and normalize and isinstance(payload, Mapping):
                payload = _normalize_payload_keys(payload, schema)
            if schema:
                payload = _coerce_payload_to_schema(payload, schema)
            if not schema:
                return payload, [], True
            issues = _validate_schema_node(payload, schema)
            if not issues:
                return payload, [], True  # perfect — stop immediately
            score = _candidate_score(payload, issues, expected_type=expected_type)
            if best_score is None or score < best_score:
                best_payload = payload
                best_score = score
                best_issues = list(issues)
        return best_payload, best_issues or [], any_parsed

    source = str(response_text or "").strip()
    raw_candidates = _candidates_for(source)

    if not raw_candidates:
        return None, ["invalid_json"]

    expected_type = str((schema or {}).get("type") or "").strip() if schema else ""

    # Pass 1: raw candidates, no key normalisation
    best, issues, found = _try_candidates(raw_candidates, expected_type=expected_type)
    if schema is None and best is not None:
        return best, []
    if not issues:
        return best, []

    # Pass 2: raw candidates with key normalisation
    best2, issues2, found2 = _try_candidates(
        raw_candidates, expected_type=expected_type, normalize=True
    )
    if not issues2 and best2 is not None:
        return best2, []
    if best2 is not None and (best is None or len(issues2) < len(issues)):
        best, issues = best2, issues2
        found = found or found2

    # Pass 3: repair full source text, re-collect candidates, try both
    repaired = repair_unescaped_inner_quotes(source)
    if repaired != source:
        rep_candidates = _candidates_for(repaired)
        best3, issues3, found3 = _try_candidates(
            rep_candidates, expected_type=expected_type
        )
        if not issues3 and best3 is not None:
            return best3, []
        if best3 is not None and (best is None or len(issues3) < len(issues)):
            best, issues = best3, issues3
            found = found or found3

        best4, issues4, found4 = _try_candidates(
            rep_candidates, expected_type=expected_type, normalize=True
        )
        if not issues4 and best4 is not None:
            return best4, []
        if best4 is not None and (best is None or len(issues4) < len(issues)):
            best, issues = best4, issues4
            found = found or found4

    if schema and expected_type == "object":
        for candidate_source in (source, repaired):
            salvaged = _salvage_object_payload(candidate_source, schema)
            if salvaged is None:
                continue
            salvaged = _coerce_payload_to_schema(salvaged, schema)
            salvaged_issues = _validate_schema_node(salvaged, schema)
            if not salvaged_issues:
                return salvaged, []
            if best is None or _candidate_score(salvaged, salvaged_issues, expected_type=expected_type) < _candidate_score(best, issues, expected_type=expected_type):
                best, issues = salvaged, salvaged_issues

    if best is not None:
        return best, issues
    if not found:
        return None, ["invalid_json"]
    return None, issues or ["invalid_json"]


_KEY_SYNONYM_MAP: Dict[str, tuple] = {
    "summary": ("update", "description", "text", "comment", "message", "note"),
    "findings": ("confirmed_facts", "facts", "observations"),
    "file": ("path", "file_path", "filepath"),
    "status": ("state", "result"),
}


def _apply_key_synonyms(
    payload: Dict[str, Any],
    missing_keys: set,
    properties: Mapping[str, Any],
) -> Dict[str, Any]:
    """Fill *missing_keys* by renaming synonym keys found in *payload*."""
    result = dict(payload)
    payload_keys = set(result.keys())
    for target in missing_keys:
        synonyms = _KEY_SYNONYM_MAP.get(target, ())
        for syn in synonyms:
            if syn in payload_keys and syn not in properties:
                result[target] = result.pop(syn)
                payload_keys.discard(syn)
                payload_keys.add(target)
                break
    return result


def _coerce_payload_to_schema(payload: Any, schema: Mapping[str, Any]) -> Any:
    """Best-effort coercion of *payload* to match *schema* types.

    Handles common ChatGPT structural deviations:
    - Objects where strings expected → extract string via priority key lookup
      (e.g. ``{"path": "foo.py", "scope": "full"}`` → ``"foo.py"``)
    - Key name mismatches in nested objects → recursive normalization +
      synonym resolution (e.g. ``update`` → ``summary``)
    - Nested arrays of typed items are coerced recursively.
    """
    expected_type = str(schema.get("type") or "").strip()

    if expected_type == "string":
        if isinstance(payload, str):
            return payload
        if isinstance(payload, Mapping):
            for key in (
                "path", "file", "summary", "name", "id", "text",
                "statement", "value", "description", "why_needed",
            ):
                if key in payload and isinstance(payload[key], str):
                    return payload[key]
            for v in payload.values():
                if isinstance(v, str):
                    return v
        if payload is not None:
            return str(payload)
        return ""

    if expected_type == "array":
        if not isinstance(payload, list):
            return payload
        item_schema = schema.get("items")
        if isinstance(item_schema, Mapping):
            return [_coerce_payload_to_schema(item, item_schema) for item in payload]
        return payload

    if expected_type == "object":
        if not isinstance(payload, Mapping):
            return payload
        properties = schema.get("properties")
        if not isinstance(properties, Mapping):
            return dict(payload)
        # Normalize keys at this level
        result = dict(_normalize_payload_keys(payload, schema))
        # Apply key synonyms for schema properties missing from payload
        all_schema_keys = set(properties.keys())
        missing = all_schema_keys - set(result.keys())
        if missing:
            result = _apply_key_synonyms(result, missing, properties)
        # Recursively coerce each matching property
        for key, subschema in properties.items():
            if key in result and isinstance(subschema, Mapping):
                result[key] = _coerce_payload_to_schema(result[key], subschema)
        return result

    return payload


def _validate_schema_node(payload: Any, schema: Mapping[str, Any], *, path: str = "$") -> List[str]:
    issues: List[str] = []
    expected_type = str(schema.get("type") or "").strip()
    if not expected_type:
        if isinstance(schema.get("required"), list) or isinstance(schema.get("properties"), Mapping):
            expected_type = "object"
        elif isinstance(schema.get("items"), Mapping):
            expected_type = "array"
    if expected_type == "object":
        if not isinstance(payload, Mapping):
            return [f"{path}: expected object"]
        required = [str(item).strip() for item in schema.get("required", []) if str(item).strip()]
        properties = schema.get("properties") if isinstance(schema.get("properties"), Mapping) else {}
        for key in required:
            if key not in payload:
                issues.append(f"{path}.{key}: missing required field")
        for key, subschema in properties.items():
            if key not in payload or not isinstance(subschema, Mapping):
                continue
            issues.extend(_validate_schema_node(payload[key], subschema, path=f"{path}.{key}"))
    elif expected_type == "array":
        if not isinstance(payload, list):
            return [f"{path}: expected array"]
        item_schema = schema.get("items") if isinstance(schema.get("items"), Mapping) else {}
        for index, item in enumerate(payload):
            if item_schema:
                issues.extend(_validate_schema_node(item, item_schema, path=f"{path}[{index}]"))
    elif expected_type == "string":
        if not isinstance(payload, str):
            return [f"{path}: expected string"]
    elif expected_type == "number":
        if not isinstance(payload, (int, float)) or isinstance(payload, bool):
            return [f"{path}: expected number"]
    elif expected_type == "integer":
        if not isinstance(payload, int) or isinstance(payload, bool):
            return [f"{path}: expected integer"]
    elif expected_type == "boolean":
        if not isinstance(payload, bool):
            return [f"{path}: expected boolean"]
    elif expected_type == "null":
        if payload is not None:
            return [f"{path}: expected null"]
    min_length = schema.get("minLength")
    if isinstance(min_length, int) and isinstance(payload, str) and len(payload) < min_length:
        issues.append(f"{path}: expected string length >= {min_length}")
    min_items = schema.get("minItems")
    if isinstance(min_items, int) and isinstance(payload, list) and len(payload) < min_items:
        issues.append(f"{path}: expected at least {min_items} items")
    enum = schema.get("enum")
    if isinstance(enum, list) and payload not in enum:
        issues.append(f"{path}: value {payload!r} not in enum")
    any_of = schema.get("anyOf")
    if isinstance(any_of, list) and any_of:
        branch_issues: List[str] = []
        matched = False
        for index, option in enumerate(any_of):
            if not isinstance(option, Mapping):
                continue
            option_issues = _validate_schema_node(payload, option, path=path)
            if not option_issues:
                matched = True
                break
            if option_issues:
                branch_issues.append(
                    f"branch {index}: {option_issues[0]}"
                )
        if not matched:
            issues.append(f"{path}: did not satisfy anyOf")
            if branch_issues:
                issues.append(f"{path}: " + "; ".join(branch_issues[:3]))
    one_of = schema.get("oneOf")
    if isinstance(one_of, list) and one_of:
        matched_indexes: List[int] = []
        branch_issues: List[str] = []
        for index, option in enumerate(one_of):
            if not isinstance(option, Mapping):
                continue
            option_issues = _validate_schema_node(payload, option, path=path)
            if not option_issues:
                matched_indexes.append(index)
            elif option_issues:
                branch_issues.append(f"branch {index}: {option_issues[0]}")
        if len(matched_indexes) != 1:
            issues.append(f"{path}: expected exactly one oneOf branch match")
            if branch_issues and not matched_indexes:
                issues.append(f"{path}: " + "; ".join(branch_issues[:3]))
    return issues


def _coerce_group_runtime_state(value: Any) -> str:
    status = str(value or "").strip() or "pending"
    if status in {"pending", "running", "success", "quality_error", "error", "aborted", "blocked", "skipped_no_dump", "skipped_missing_dump"}:
        return status
    return "pending"


def _resolved_group_runtime_state(group: Mapping[str, Any]) -> str:
    runtime_state = _coerce_group_runtime_state(group.get("runtime_state"))
    response_status = _coerce_group_runtime_state(group.get("response_status"))
    if runtime_state in TERMINAL_GROUP_STATUSES:
        return runtime_state
    if response_status in TERMINAL_GROUP_STATUSES:
        return response_status
    if runtime_state == "running" or response_status == "running":
        return "running"
    return "pending"


def _normalize_group_label_set(labels: Optional[List[str]]) -> set[str]:
    return {str(label).strip() for label in (labels or []) if str(label).strip()}


def _group_label(group: Mapping[str, Any], default: str = "") -> str:
    return str(group.get("label") or default).strip() or default


def _group_dependencies(group: Mapping[str, Any]) -> List[str]:
    deps = group.get("depends_on")
    if not isinstance(deps, list):
        return []
    return [str(dep).strip() for dep in deps if str(dep).strip()]


def _expand_dispatch_scope_labels(
    groups_payload: List[Dict[str, Any]],
    target_labels: Optional[List[str]],
) -> set[str]:
    labels_by_group = {
        _group_label(group): dict(group)
        for group in groups_payload
        if _group_label(group)
    }
    if not labels_by_group:
        return set()

    roots = _normalize_group_label_set(target_labels)
    if not roots:
        return {
            label
            for label, group in labels_by_group.items()
            if _resolved_group_runtime_state(group) not in TERMINAL_GROUP_STATUSES
        }

    children: Dict[str, List[str]] = {}
    for label, group in labels_by_group.items():
        for dep in _group_dependencies(group):
            children.setdefault(dep, []).append(label)

    expanded = {label for label in roots if label in labels_by_group}
    frontier = list(expanded)
    while frontier:
        current = frontier.pop()
        for child in children.get(current, []):
            if child in expanded:
                continue
            expanded.add(child)
            frontier.append(child)
    return expanded


def _earliest_nonterminal_wave_index(
    groups_payload: List[Dict[str, Any]],
    wave_by_label: Mapping[str, int],
    *,
    default: int,
) -> int:
    indices = [
        int(wave_by_label.get(label, default))
        for group in groups_payload
        if _resolved_group_runtime_state(group) not in TERMINAL_GROUP_STATUSES
        for label in [_group_label(group)]
        if label
    ]
    if not indices:
        return int(default)
    return min(indices)


def _resolve_blocked_groups(groups_payload: List[Dict[str, Any]]) -> int:
    """Mark groups whose dependencies have hard-failed as 'blocked'.

    Only hard failures (error, aborted, blocked) block downstream groups.
    quality_error is NOT a blocking status because the probe still produced
    a response file with usable content that downstream groups can consume.

    Synthesis/evaluation groups use a softer policy: they are only blocked
    if ALL dependencies failed. This allows synthesis to run with partial
    probe results (e.g., 3/5 probes succeeded).

    Returns the number of groups newly marked blocked.
    """
    label_to_state = {
        str(g.get("label") or "").strip(): _resolved_group_runtime_state(g)
        for g in groups_payload
    }
    blocked_count = 0
    for group in groups_payload:
        state = _resolved_group_runtime_state(group)
        if state in TERMINAL_GROUP_STATUSES:
            continue
        deps = [str(d).strip() for d in (group.get("depends_on") or []) if str(d).strip()]
        if not deps:
            continue
        dep_states = [label_to_state.get(d, "pending") for d in deps]
        role = str(group.get("role", "probe")).strip().lower()
        if role in ("synthesis", "evaluation"):
            # Synthesis only blocked if ALL dependencies failed (no usable content at all)
            usable_count = sum(1 for s in dep_states if s not in BLOCKING_GROUP_STATUSES)
            if usable_count == 0:
                group["runtime_state"] = "blocked"
                group["response_status"] = "blocked"
                group["response_error"] = "all_dependencies_failed"
                group["response_error_category"] = "blocked_by_upstream"
                group["response_error_stage"] = "pre_dispatch"
                blocked_count += 1
        else:
            # Regular groups: block if any dependency truly failed
            if any(s in BLOCKING_GROUP_STATUSES for s in dep_states):
                group["runtime_state"] = "blocked"
                group["response_status"] = "blocked"
                group["response_error"] = "dependency_failed"
                group["response_error_category"] = "blocked_by_upstream"
                group["response_error_stage"] = "pre_dispatch"
                blocked_count += 1
    return blocked_count


def _coerce_pending_to_terminal(groups_payload: List[Dict[str, Any]], reason: str) -> int:
    """Force any remaining non-terminal groups to a real terminal state.

    Called during finalization to eliminate fake 'pending' in completed sessions.
    Returns the count of groups coerced.
    """
    coerced = 0
    for group in groups_payload:
        state = _resolved_group_runtime_state(group)
        if state in TERMINAL_GROUP_STATUSES:
            continue
        # Determine appropriate terminal state
        deps = [str(d).strip() for d in (group.get("depends_on") or []) if str(d).strip()]
        label_to_state = {
            str(g.get("label") or "").strip(): _resolved_group_runtime_state(g)
            for g in groups_payload
        }
        dep_states = [label_to_state.get(d, "pending") for d in deps] if deps else []
        if any(s in BLOCKING_GROUP_STATUSES for s in dep_states):
            terminal = "blocked"
            error_cat = "blocked_by_upstream"
        elif reason == "cancelled":
            terminal = "aborted"
            error_cat = "session_cancelled"
        else:
            terminal = "aborted"
            error_cat = "session_ended_before_dispatch"
        group["runtime_state"] = terminal
        group["response_status"] = terminal
        group["response_error"] = reason
        group["response_error_category"] = error_cat
        group["response_error_stage"] = "pre_dispatch"
        coerced += 1
    return coerced


def preflight_observe_plan(
    repo_root: Path,
    plan: Dict[str, Any],
    bridge_enabled: bool = True,
    launch_metadata: Optional[Mapping[str, Any]] = None,
    bridge_provider: Optional[str] = None,
    bridge_workers: Any = None,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Reject obviously broken grouped observe plans before the runner builds dumps or touches bridge/runtime surfaces.
    - Mechanism: Expand factory targets, verify dependency labels and cycles, confirm target/context paths and writable destinations, probe bridge reachability, and attach bridge capability-matrix validator decisions.
    - Reads: repo_root, plan, filesystem existence/writability, observe wave computation, bridge preflight state, and bridge validator rules.
    - Guarantee: Returns a `{ok, errors, warnings}` dict where `ok` is false when blocking plan defects were found and warnings includes non-fatal bridge/runtime risk signals.
    - Fails: None — bridge and filesystem probe exceptions are converted into warning strings instead of escaping.
    - When-needed: Open when diagnosing why a grouped observe launch was rejected before dispatch or why a plan is missing files, labels, or bridge readiness.
    - Escalates-to: tools/meta/bridge/dispatch_validator.py::validate_plan; tools/meta/apply/observe_session_runner.py::run_session_once.
    - Navigation-group: observe_apply.
    """
    errors: List[str] = []
    warnings: List[str] = []
    launch_metadata = dict(launch_metadata or {})
    groups = plan.get("groups", [])
    from system.lib.observe_plan_enrichment import expand_factory_batch_targets_in_plan

    expand_factory_batch_targets_in_plan(repo_root, plan)
    groups = plan.get("groups", [])
    labels = {str(g.get("label", "")).strip() for g in groups if str(g.get("label", "")).strip()}

    # Check dependencies
    for group in groups:
        label = str(group.get("label", "")).strip()
        deps = [str(d).strip() for d in (group.get("depends_on") or []) if str(d).strip()]
        for dep in deps:
            if dep not in labels:
                errors.append(f"group '{label}' depends_on '{dep}' which does not exist in plan")
            if dep == label:
                errors.append(f"group '{label}' depends on itself")

    # Check for cycles via wave computation
    try:
        from system.lib.observe_runtime import grouped_observe_waves
        grouped_observe_waves(groups)
    except ValueError as e:
        errors.append(f"dependency cycle: {e}")

    # Check target files exist
    missing_targets = []
    for group in groups:
        label = str(group.get("label", "")).strip()
        for target in (group.get("targets") or []):
            fpath = str(target.get("file", "")).strip()
            if fpath and not (repo_root / fpath).exists():
                missing_targets.append(f"group '{label}': target '{fpath}' does not exist")
    if missing_targets:
        for mt in missing_targets[:10]:
            errors.append(mt)
        if len(missing_targets) > 10:
            errors.append(f"... and {len(missing_targets) - 10} more missing targets")

    # Check context files exist
    for ctx in (plan.get("context_files") or []):
        if ctx and not (repo_root / ctx).exists():
            errors.append(f"context file '{ctx}' does not exist")
    for group in groups:
        for ctx in (group.get("context_files") or []):
            if ctx and not (repo_root / ctx).exists():
                label = str(group.get("label", "")).strip()
                warnings.append(f"group '{label}': context file '{ctx}' does not exist")

    # Check dump dir parent writable
    dump_dir = str(plan.get("dump_dir", "")).strip()
    if dump_dir:
        dump_parent = (repo_root / dump_dir).parent
        if dump_parent.exists() and not os.access(dump_parent, os.W_OK):
            errors.append(f"dump dir parent '{dump_parent}' is not writable")

    # Check result note path parent writable
    result_note = str(plan.get("result_note_path", "")).strip()
    if result_note:
        result_parent = (repo_root / result_note).parent
        if result_parent.exists() and not os.access(result_parent, os.W_OK):
            errors.append(f"result note parent '{result_parent}' is not writable")

    codex_transport_guard: Optional[Dict[str, Any]] = None
    detached_codex_auto_resume = (
        str(launch_metadata.get("launch_mode") or "").strip() == "detached"
        and bool(launch_metadata.get("codex_auto_resume_requested"))
        and not bool(launch_metadata.get("codex_auto_resume_suppressed"))
    )
    if bridge_enabled and detached_codex_auto_resume:
        try:
            from tools.meta.bridge.codex_session_transport import (
                TRANSPORT_PATH as _CODEX_TRANSPORT_PATH,
                blocking_launch_record as _blocking_launch_record,
            )

            raw_transport_path = str(launch_metadata.get("codex_transport_path") or "").strip()
            transport_path = Path(raw_transport_path) if raw_transport_path else _CODEX_TRANSPORT_PATH
            if not transport_path.is_absolute():
                transport_path = repo_root / transport_path
            codex_transport_guard = _blocking_launch_record(path=transport_path)
            if codex_transport_guard is not None:
                job_id = codex_transport_guard.get("job_id_or_signal_fingerprint") or "unknown"
                failure_reason = codex_transport_guard.get("failure_reason") or "unresolved_failed_transport"
                errors.append(
                    "codex continuity: unresolved failed transport blocks detached auto-resume "
                    f"launch at '{transport_path}'. status=failed job={job_id} "
                    f"reason={failure_reason}. Resolve or clear the persisted transport before "
                    "launching another detached Codex-resume session."
                )
        except Exception as exc:
            warnings.append(f"codex continuity preflight failed (non-fatal): {exc}")

    # Check bridge reachable
    if bridge_enabled:
        try:
            from system.core.bridge import bridge_preflight
            pf = bridge_preflight(repo_root)
            if not pf.get("browser_reachable"):
                warnings.append(
                    "bridge: browser not reachable (CDP endpoint down). "
                    "FIX: run `./repo-python run_bridge_preflight.py --fast` to boot Chrome and verify selectors. "
                    "This is not a fatal error — preflight takes ~10 seconds."
                )
            if pf.get("stale"):
                warnings.append(
                    f"bridge: provider is stale ({pf.get('stale_reason', 'unknown')}). "
                    "FIX: run `./repo-python run_bridge_preflight.py --fast` to refresh."
                )
        except Exception as e:
            warnings.append(
                f"bridge preflight check failed: {e}. "
                "FIX: run `./repo-python run_bridge_preflight.py --fast` to boot Chrome."
            )

    # --- Bridge operating system: capability matrix validator ---
    # Reject plans that would violate measured caps BEFORE they hit the wire.
    # This is the enforcement arm of the Type-A/Type-B doctrine.
    bridge_os_decisions: List[Dict[str, Any]] = []
    if bridge_enabled:
        try:
            from tools.meta.bridge.dispatch_validator import validate_plan as _bridge_os_validate
            # Discover requested provider + workers from the plan or fall back to defaults.
            requested_provider = str(
                bridge_provider
                or plan.get("bridge_provider")
                or plan.get("provider")
                or "chatgpt"
            ).lower().strip()
            if _is_bridge_provider(requested_provider):
                requested_workers = int(bridge_workers or plan.get("bridge_workers") or 2)
                os_result = _bridge_os_validate(
                    plan,
                    repo_root=repo_root,
                    provider=requested_provider,
                    requested_workers=requested_workers,
                )
                for d in os_result.decisions:
                    bridge_os_decisions.append({
                        "rule_id": d.rule_id,
                        "outcome": d.outcome,
                        "group_label": d.group_label,
                        "message": d.message,
                    })
                for e in os_result.errors:
                    errors.append(f"bridge_os: {e}")
                for w in os_result.warnings:
                    warnings.append(f"bridge_os: {w}")
        except Exception as exc:
            warnings.append(f"bridge_os validator failed (non-fatal): {exc}")

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "group_count": len(groups),
        "label_count": len(labels),
        "dependency_edges": sum(len(g.get("depends_on") or []) for g in groups),
        "target_file_count": sum(len(g.get("targets") or []) for g in groups),
        "context_file_count": len(plan.get("context_files") or []) + sum(len(g.get("context_files") or []) for g in groups),
        "bridge_os_decisions": bridge_os_decisions,
        "codex_transport_guard": codex_transport_guard,
    }


def _reset_group_for_retry(group: Mapping[str, Any]) -> Dict[str, Any]:
    cleared = dict(group)
    for key in _RETRY_RESET_GROUP_FIELDS:
        cleared.pop(key, None)
    cleared["runtime_state"] = "pending"
    return cleared


_RESPONSE_META_RE = re.compile(r"(?m)^-\s+([a-z_]+):\s+`([^`]*)`\s*$")


def _coerce_bool_token(value: Any) -> Optional[bool]:
    token = str(value or "").strip().lower()
    if token in {"true", "yes", "1"}:
        return True
    if token in {"false", "no", "0"}:
        return False
    return None


def _coerce_int_token(value: Any) -> Optional[int]:
    token = str(value or "").strip()
    if not token:
        return None
    try:
        return int(token)
    except (TypeError, ValueError):
        return None


def _response_artifact_for_group(repo_root: Path, group: Mapping[str, Any]) -> tuple[Optional[str], Optional[Path]]:
    response_rel = str(group.get("response_file") or "").strip()
    if response_rel:
        response_path = (repo_root / response_rel).resolve()
        return response_rel, response_path
    dump_rel = str(group.get("dump_file") or "").strip()
    if not dump_rel:
        return None, None
    dump_path = (repo_root / dump_rel).resolve()
    response_path = dump_path.with_name(f"{dump_path.stem}_response.md")
    try:
        response_rel = str(response_path.relative_to(repo_root))
    except ValueError:
        response_rel = str(response_path)
    return response_rel, response_path


def _extract_response_markdown_body(text: str) -> str:
    marker = "\n## Response"
    source = str(text or "")
    if marker not in source:
        return source.strip()
    return source.split(marker, 1)[1].strip()


def _parse_response_markdown(text: str) -> Dict[str, Any]:
    source = str(text or "")
    meta = {match.group(1): match.group(2) for match in _RESPONSE_META_RE.finditer(source)}
    sections = _extract_heading_sections(source)
    response_body = _extract_response_markdown_body(source)
    next_action = _extract_next_action(source) or _extract_next_action(response_body or "")
    parsed: Dict[str, Any] = {
        "response_status": _coerce_group_runtime_state(meta.get("status")),
        "response_error_category": (None if meta.get("error_category") in {None, "", "none"} else meta.get("error_category")),
        "response_error_stage": (None if meta.get("error_stage") in {None, "", "none"} else meta.get("error_stage")),
        "response_quality_status": str(meta.get("quality_status") or "").strip() or None,
        "response_surface_kind": (None if meta.get("response_surface_kind") in {None, "", "none"} else meta.get("response_surface_kind")),
        "response_kind": (None if meta.get("response_kind") in {None, "", "none"} else meta.get("response_kind")),
        "response_surface_file": (None if meta.get("response_surface_file") in {None, "", "none"} else meta.get("response_surface_file")),
        "response_prompt_chars": _coerce_int_token(meta.get("bridge_prompt_chars")),
        "response_dump_truncated": _coerce_bool_token(meta.get("dump_truncated")),
        "response_body": response_body,
        "response_error": sections.get("BRIDGE ERROR") or None,
        "next_action": next_action,
        "next_fork": _extract_next_fork_kind(response_body or source),
        "next_fork_block": _extract_next_fork_block(response_body or source),
    }
    pending = extract_pending_items_from_text(response_body)
    parsed["operator_decisions_pending"] = pending.get("operator_decisions_pending", [])
    parsed["agent_followups_pending"] = pending.get("agent_followups_pending", [])
    return parsed


def _recover_group_state_from_response_artifact(
    *,
    repo_root: Path,
    group: Mapping[str, Any],
) -> Dict[str, Any]:
    response_rel, response_path = _response_artifact_for_group(repo_root, group)
    if not response_rel or response_path is None or not response_path.exists():
        return {}
    try:
        text = response_path.read_text(encoding="utf-8")
    except OSError:
        return {}
    recovered = _parse_response_markdown(text)
    status = _coerce_group_runtime_state(recovered.get("response_status"))
    if status not in TERMINAL_GROUP_STATUSES:
        return {}
    continuation = _build_continuation_contract(
        response_text=str(recovered.get("response_body") or ""),
        artifact_rel_path=response_rel,
        label=str(group.get("label") or "group"),
        role=str(group.get("role") or "probe"),
        status=status,
    )
    recovered["response_file"] = response_rel
    recovered["runtime_state"] = status
    recovered["next_action"] = str(recovered.get("next_action") or continuation["next_action"]).strip() or continuation["next_action"]
    recovered["continuation_hint"] = continuation["hint"]
    recovered["continuation_source"] = continuation["source"]
    return {key: value for key, value in recovered.items() if value is not None}


def _merge_runtime_group_state(
    *,
    repo_root: Path,
    fresh_groups: List[Dict[str, Any]],
    runtime_manifest: Optional[Dict[str, Any]],
    recover_response_artifacts: bool,
    retry_group_labels: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    existing_by_label: Dict[str, Dict[str, Any]] = {}
    retry_labels = _normalize_group_label_set(retry_group_labels)
    if isinstance(runtime_manifest, dict):
        for item in runtime_manifest.get("groups", []):
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            if label:
                existing_by_label[label] = dict(item)

    merged: List[Dict[str, Any]] = []
    for group in fresh_groups:
        label = str(group.get("label") or "").strip()
        existing = existing_by_label.get(label, {})
        merged_group = dict(group)
        for key in (
            "response_status",
            "response_file",
            "response_dump_chars",
            "response_prompt_chars",
            "response_dump_truncated",
            "response_body",
            "response_error",
            "response_error_category",
            "response_error_stage",
            "response_quality_status",
            "response_quality_issues",
            "response_quality_detected_issues",
            "response_quality_repair_actions",
            "response_quality_required_sections",
            "response_quality_missing_sections",
            "response_surface_kind",
            "response_kind",
            "response_surface_file",
            "prompt_response_mode",
            "next_fork",
            "next_fork_block",
            "next_action",
            "continuation_hint",
            "continuation_source",
            "operator_decisions_pending",
            "agent_followups_pending",
            "runtime_state",
            "wave_index",
        ):
            if key in existing and existing.get(key) is not None:
                merged_group[key] = existing.get(key)
        if label in retry_labels:
            merged.append(_reset_group_for_retry(merged_group))
            continue
        if recover_response_artifacts:
            recovered = _recover_group_state_from_response_artifact(repo_root=repo_root, group=merged_group)
            if recovered:
                merged_group.update(recovered)
        merged_group["runtime_state"] = _resolved_group_runtime_state(merged_group)
        merged.append(merged_group)
    return merged


def _runtime_group_counts(groups_payload: List[Dict[str, Any]]) -> Tuple[int, int]:
    total = len(groups_payload)
    completed = sum(
        1
        for group in groups_payload
        if _resolved_group_runtime_state(group) in TERMINAL_GROUP_STATUSES
    )
    return total, completed


def _build_grouped_runtime_manifest(
    *,
    repo_root: Path,
    history_dir: Path,
    observe_id: str,
    launch_profile: str,
    requested_workers: Any,
    effective_workers: int,
    wave_index: int,
    wave_total: int,
    state: str,
    groups_payload: List[Dict[str, Any]],
    artifacts: Dict[str, Any],
    launch_metadata: Dict[str, Any],
    error: Optional[str] = None,
    cancel_requested_at: Optional[str] = None,
    started_at: Optional[str] = None,
    session_slug: Optional[str] = None,
) -> Dict[str, Any]:
    total_groups, completed_groups = _runtime_group_counts(groups_payload)
    provider = str(
        launch_metadata.get("bridge_provider_used")
        or launch_metadata.get("bridge_provider_requested")
        or artifacts.get("bridge_provider")
        or ""
    ).strip() or None
    return {
        "kind": "grouped_observe",
        "observe_id": observe_id,
        "session_slug": session_slug,
        "state": state,
        "launch_profile": launch_profile,
        "requested_workers": str(requested_workers or "auto"),
        "effective_workers": int(max(1, effective_workers)),
        "wave_index": int(max(0, wave_index)),
        "wave_total": int(max(0, wave_total)),
        "total_groups": total_groups,
        "completed_groups": completed_groups,
        "groups": groups_payload,
        "pid": launch_metadata.get("pid"),
        "log_file": launch_metadata.get("log_file"),
        "launch_receipt": dict(launch_metadata.get("launch_receipt") or {}),
        "launch_dispatch": str(launch_metadata.get("launch_dispatch") or "").strip() or None,
        "started_at": started_at or now_iso(),
        "updated_at": now_iso(),
        "artifacts": artifacts,
        "cancel_requested_at": cancel_requested_at,
        "error": error,
        "history_entry": artifacts.get("history_entry"),
        "provider": provider,
        "provider_transport": latest_bridge_transport(history_dir, provider),
        "runtime_manifest": str(grouped_runtime_path(history_dir, observe_id).relative_to(repo_root)),
    }


def _start_cancel_watcher(
    *,
    repo_root: Path,
    history_dir: Path,
    observe_id: str,
    cancel_event: threading.Event,
    stop_event: threading.Event,
) -> threading.Thread:
    manifest_path = grouped_runtime_path(history_dir, observe_id)

    def _watch() -> None:
        last_seen = ""
        while not stop_event.is_set():
            payload = load_grouped_runtime_manifest(repo_root, history_dir, str(manifest_path))
            cancel_requested_at = str(payload.get("cancel_requested_at") or "").strip()
            if cancel_requested_at and cancel_requested_at != last_seen:
                cancel_event.set()
                last_seen = cancel_requested_at
            stop_event.wait(0.5)

    thread = threading.Thread(target=_watch, name=f"grouped-observe-cancel-{observe_id}", daemon=True)
    thread.start()
    return thread


def _safe_text(value: Any) -> str:
    text = str(value or "").strip()
    return re.sub(r"\s+", " ", text)


def _group_standard_summary_lines(bundle: Mapping[str, Any] | None) -> List[str]:
    if not isinstance(bundle, Mapping):
        return []
    matched_kinds = [
        str(item).strip()
        for item in (bundle.get("matched_artifact_kinds") or [])
        if str(item).strip()
    ]
    applicable = [
        dict(item)
        for item in (bundle.get("applicable_standards") or [])
        if isinstance(item, Mapping)
    ]
    if not matched_kinds and not applicable:
        return []
    lines: List[str] = []
    if matched_kinds:
        lines.append(f"- matched_artifact_kinds: `{', '.join(matched_kinds)}`")
    authority_index = str(bundle.get("authority_index") or "").strip()
    if authority_index:
        lines.append(f"- authority_index: `{authority_index}`")
    if applicable:
        lines.append("- standards:")
        for card in applicable[:6]:
            artifact_kind = str(card.get("artifact_kind") or "").strip() or "artifact"
            standard_kind = str(card.get("kind") or "").strip() or "standard"
            rel_path = str(card.get("path") or "").strip() or "unknown"
            lines.append(f"  - {artifact_kind} {standard_kind}: `{rel_path}`")
    return lines


def _first_sentence(value: str, fallback: str) -> str:
    text = _safe_text(value)
    if not text:
        return fallback
    parts = re.split(r"(?<=[.!?])\s+", text)
    first = parts[0].strip()
    if not first:
        return fallback
    if first[-1] not in ".!?":
        first = f"{first}."
    return first


def _snapshot_bridge_log_to_dump(
    repo_root: Path,
    observe_id: str,
    meta: Dict[str, Any],
    plan: Dict[str, Any],
) -> Optional[str]:
    """Copy bridge events for this session into dump as ``observe_bridge_log.jsonl``."""
    dump_dir_rel = str(meta.get("dump_dir") or plan.get("dump_dir") or "").strip()
    if not dump_dir_rel:
        return None
    dump_path = (repo_root / dump_dir_rel).resolve()
    if not dump_path.is_dir():
        return None
    try:
        from system.core.bridge import snapshot_bridge_events_for_session
        out_path = dump_path / "observe_bridge_log.jsonl"
        event_count = snapshot_bridge_events_for_session(
            session_id=observe_id,
            out_path=out_path,
        )
        if event_count <= 0:
            return None
        return str(out_path.relative_to(repo_root))
    except Exception:
        return None


def _sentence_count(text: str) -> int:
    return len(re.findall(r"[.!?](?=\s|$)", text.strip()))


def _enforce_sentence_count(text: str, count: int) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    found = _sentence_count(cleaned)
    if found == count:
        return cleaned
    if found > count:
        parts = re.split(r"(?<=[.!?])\s+", cleaned)
        out = " ".join(parts[:count]).strip()
        if _sentence_count(out) < count:
            out = out.rstrip(".!?") + "."
        return out
    missing = count - found
    suffix = " ".join(["Stay strictly evidence-grounded."] * missing)
    merged = f"{cleaned} {suffix}".strip()
    parts = re.split(r"(?<=[.!?])\s+", merged)
    return " ".join(parts[:count]).strip()


def _build_group_prompt(
    *,
    label: str,
    role: str = "probe",
    notes: str,
    files: List[str],
    context_files: List[str] = (),
    depends_on: List[str] = (),
    wait_notes: str,
    prompt_style: str,
    goal_question: str = "",
    success_criteria: str = "",
    group_question: str = "",
    acceptance: str = "",
    response_mode: str = "structured_sections",
    sentence_count: Optional[int],
    json_only: bool = False,
) -> str:
    full_wait = _safe_text(wait_notes) or "Use an evidence-first posture with no fix proposals."
    full_style = _safe_text(prompt_style) or "Use a comprehensive, citable diagnostic style."
    full_notes = _safe_text(notes) or "Focus on the assigned group scope and its key contracts."
    full_goal = _safe_text(goal_question)
    full_success = _safe_text(success_criteria)
    full_group_question = _safe_text(group_question)
    full_acceptance = _safe_text(acceptance)
    unique_files: List[str] = []
    for item in files:
        token = str(item or "").strip()
        if not token or token in unique_files:
            continue
        unique_files.append(token)
    file_count = len(unique_files)
    target_count = len([item for item in files if str(item or "").strip()])
    scope_phrase = (
        f"{file_count} distinct files across {target_count} attached target excerpts"
        if target_count and target_count != file_count
        else f"{file_count} attached file excerpts"
    )
    normalized_role = _safe_text(role).lower() or "probe"
    if normalized_role == "probe":
        execution_semantics = "Execution semantics: this is a one-shot isolated probe call with no access to other group outputs."
    else:
        attached_surfaces: List[str] = ["the current-node observe dump"]
        if depends_on:
            attached_surfaces.append("declared upstream group artifacts")
        if context_files:
            attached_surfaces.append("injected context files")
        execution_semantics = (
            "Execution semantics: this is a bounded group-local join/evaluation call. "
            f"Use only {', '.join(attached_surfaces)} as evidence and do not assume hidden probe outputs."
        )

    lines = [
        f"You are assigned group '{label}' with {scope_phrase}, and you may only use the attached dump excerpts plus injected context as evidence.",
        execution_semantics,
        *([f"Pass goal: {full_goal}"] if full_goal else []),
        *([f"Pass success criteria: {full_success}"] if full_success else []),
        *([f"Bounded group question: {full_group_question}"] if full_group_question else []),
    ]
    if json_only:
        # When JSON output is required, suppress prose-style instructions that
        # cause the model to write narrative markdown instead of the schema.
        lines += [
            "Your response MUST be a single valid JSON object matching the schema in [OUTPUT_SHAPE].",
            "Do not add any prose, markdown fences, NEXT_ACTION lines, or commentary outside the JSON value.",
            *([f"Acceptance condition: {full_acceptance}"] if full_acceptance else []),
        ]
    else:
        lines += [
            f"Global pass posture: {full_wait}",
            f"Reporting style: {full_style}",
            f"Group focus: {full_notes} Cite every non-trivial claim with file path plus symbol, section, or exact quoted anchor from the dump.",
            *([f"Acceptance condition: {full_acceptance}"] if full_acceptance else []),
            "Keep output group-local only; do not write global synthesis/final strategy sections and do not restate the full problem statement.",
            (
                "Do not propose fixes; separate facts, inferences, and unknowns; avoid duplicate sections; end with 3-7 risk-ordered next-probe questions."
                if response_mode != "epistemic_tags"
                else "Think freely but stay evidence-bounded; tag substantive claims as [FACT], [INFERENCE], [TENSION], or [UNKNOWN], choose headings that fit the material, and end with a BEST NEXT QUESTIONS block containing 3-5 leverage-ordered questions."
            ),
        ]

    if not json_only:
        lines.append(
            'Optional: if it fits without breaking the required output shape, you MAY include a JSON block '
            'like {"_summary": {"teleology": "one sentence: what this response IS", '
            '"outcome": "one sentence: what to DO with it", "confidence": "HIGH|MEDIUM|LOW"}} '
            "immediately before the final NEXT_ACTION line. Omit it if it conflicts with the contract."
        )

    prompt = " ".join(lines)
    if sentence_count is not None and sentence_count > 0:
        return _enforce_sentence_count(prompt, sentence_count)
    return prompt


def _build_standard_prompt(
    *,
    target_count: int,
    wait_notes: str,
    prompt_style: str,
    sentence_count: Optional[int],
) -> str:
    full_wait = _safe_text(wait_notes) or "Use an evidence-first posture with no fix proposals."
    full_style = _safe_text(prompt_style) or "Use a comprehensive, citable diagnostic style."
    lines = [
        f"You are assigned a standard observe pass over {target_count} targets and must restrict evidence to the listed files plus injected context.",
        f"Global pass posture: {full_wait}",
        f"Reporting style: {full_style}",
        "Cite every non-trivial claim with file path plus symbol, section, or exact quoted anchor from the dump, and do not propose implementation steps.",
        "Separate facts, inferences, and unknowns, and end with 3-7 risk-ordered next-probe questions.",
    ]
    prompt = " ".join(lines)
    if sentence_count is not None and sentence_count > 0:
        return _enforce_sentence_count(prompt, sentence_count)
    return prompt


def _obs_id(seed: str) -> str:
    stamp = _now_iso().replace(":", "-")
    short = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]
    return f"OBS_{stamp}_{short}"


def _load_apply_module(repo_root: Path):
    root_str = str(repo_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    from tools.meta import apply as meta_apply  # pylint: disable=import-outside-toplevel
    return meta_apply


def _sticky_dump_dir_marker(repo_root: Path) -> Path:
    return repo_root / "tools" / "meta" / "apply" / "observe_history" / "sticky_dump_dir.txt"


def _apply_sticky_dump_dir_policy(
    *,
    repo_root: Path,
    plan: Dict[str, Any],
    sticky_enabled: bool,
) -> Dict[str, Any]:
    if not sticky_enabled:
        return {
            "enabled": False,
            "applied": False,
            "marker_file": str(_sticky_dump_dir_marker(repo_root).relative_to(repo_root)),
            "active_dump_dir": str(plan.get("dump_dir") or "").strip() or None,
            "source": "plan",
        }

    if not isinstance(plan.get("groups"), list) or not plan.get("groups"):
        return {
            "enabled": True,
            "applied": False,
            "marker_file": str(_sticky_dump_dir_marker(repo_root).relative_to(repo_root)),
            "active_dump_dir": str(plan.get("dump_dir") or "").strip() or None,
            "source": "non_grouped_or_empty_groups",
        }

    marker = _sticky_dump_dir_marker(repo_root)
    marker.parent.mkdir(parents=True, exist_ok=True)

    plan_dump_dir = str(plan.get("dump_dir") or "").strip()
    marker_dump_dir = ""
    if marker.exists():
        marker_dump_dir = marker.read_text(encoding="utf-8").strip()

    if marker_dump_dir:
        applied = False
        if plan_dump_dir != marker_dump_dir:
            plan["dump_dir"] = marker_dump_dir
            applied = True
        return {
            "enabled": True,
            "applied": applied,
            "marker_file": str(marker.relative_to(repo_root)),
            "active_dump_dir": marker_dump_dir,
            "source": "marker",
        }

    active_dump_dir = plan_dump_dir or "tools/meta/apply/observe_dumps/active_observe_dump"
    plan["dump_dir"] = active_dump_dir
    marker.write_text(active_dump_dir + "\n", encoding="utf-8")
    return {
        "enabled": True,
        "applied": True,
        "marker_file": str(marker.relative_to(repo_root)),
        "active_dump_dir": active_dump_dir,
        "source": "initialized_from_plan" if plan_dump_dir else "initialized_default",
    }


def _inject_prompts_into_group_dumps(
    *,
    repo_root: Path,
    groups_payload: List[Dict[str, Any]],
    sentence_count: Optional[int],
) -> int:
    updated = 0
    for group in groups_payload:
        dump_file = group.get("dump_file")
        prompt = group.get("prompt")
        if not isinstance(dump_file, str) or not dump_file:
            continue
        if not isinstance(prompt, str) or not prompt.strip():
            continue
        dump_path = (repo_root / dump_file).resolve()
        if not dump_path.exists():
            continue
        try:
            payload = _read_json(dump_path)
            if not isinstance(payload, dict):
                continue
            meta = payload.get("__meta")
            meta, _prompt_contract_audit = _reconcile_group_prompt_meta(
                meta=meta if isinstance(meta, Mapping) else None,
                prompt=prompt,
                sentence_count=sentence_count,
            )
            payload["__meta"] = meta
            _write_json(dump_path, payload)
            updated += 1
        except Exception:
            continue
    return updated


def _reconcile_group_prompt_meta(
    *,
    meta: Mapping[str, Any] | None,
    prompt: str,
    sentence_count: Optional[int] = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    prompt_text = str(prompt or "").strip()
    updated_meta = dict(meta or {})
    previous_notes = str(updated_meta.get("notes") or "").strip()
    previous_agent_prompt = str(updated_meta.get("agent_prompt") or "").strip()
    previous_group_notes = str(updated_meta.get("group_notes") or "").strip()
    mismatch_fields: list[str] = []
    if previous_notes and previous_notes != prompt_text:
        mismatch_fields.append("notes")
    if previous_agent_prompt and previous_agent_prompt != prompt_text:
        mismatch_fields.append("agent_prompt")

    updated_meta["notes"] = prompt_text
    updated_meta["agent_prompt"] = prompt_text
    if sentence_count is not None:
        updated_meta["prompt_sentence_requirement"] = sentence_count if sentence_count > 0 else None
    elif "prompt_sentence_requirement" not in updated_meta:
        updated_meta["prompt_sentence_requirement"] = None
    if previous_group_notes and not str(updated_meta.get("group_notes_original") or "").strip():
        updated_meta["group_notes_original"] = previous_group_notes
    updated_meta["prompt_contract_sha256"] = _text_sha256(prompt_text) if prompt_text else None
    if mismatch_fields:
        updated_meta["prompt_contract_last_reconciled_at"] = _now_iso()

    audit = {
        "canonical_prompt_sha256": updated_meta.get("prompt_contract_sha256"),
        "notes_present": bool(previous_notes),
        "agent_prompt_present": bool(previous_agent_prompt),
        "notes_matches_prompt": None if not previous_notes else previous_notes == prompt_text,
        "agent_prompt_matches_prompt": None if not previous_agent_prompt else previous_agent_prompt == prompt_text,
        "mismatch_fields": mismatch_fields,
        "previous_notes": previous_notes if previous_notes and previous_notes != prompt_text else None,
        "previous_agent_prompt": (
            previous_agent_prompt
            if previous_agent_prompt and previous_agent_prompt != prompt_text
            else None
        ),
    }
    if mismatch_fields:
        updated_meta["prompt_contract_last_audit"] = dict(audit)
    return updated_meta, audit


def _sync_group_dump_prompt_meta(
    *,
    dump_path: Path,
    prompt_text: str,
    sentence_count: Optional[int] = None,
) -> dict[str, Any]:
    prompt_text = str(prompt_text or "").strip()
    if not prompt_text or not dump_path.exists():
        return {}
    try:
        payload = _read_json(dump_path)
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    updated_meta, prompt_contract_audit = _reconcile_group_prompt_meta(
        meta=payload.get("__meta") if isinstance(payload.get("__meta"), Mapping) else None,
        prompt=prompt_text,
        sentence_count=sentence_count,
    )
    if (
        (not prompt_contract_audit or not prompt_contract_audit.get("mismatch_fields"))
        and isinstance(updated_meta.get("prompt_contract_last_audit"), Mapping)
    ):
        prompt_contract_audit = dict(updated_meta.get("prompt_contract_last_audit") or {})
    payload["__meta"] = updated_meta
    _write_json(dump_path, payload)
    return dict(prompt_contract_audit or {})


def _refresh_group_dump_context(
    *,
    repo_root: Path,
    group: Mapping[str, Any],
    prompt_text: Optional[str] = None,
) -> Dict[str, Any]:
    dump_file = str(group.get("dump_file") or "").strip()
    if not dump_file:
        return {"refreshed": False, "reason": "missing_dump_file"}

    context_files = [
        str(item).strip()
        for item in (group.get("context_files") or [])
        if str(item).strip()
    ]
    if not context_files:
        return {"refreshed": False, "reason": "no_context_files"}

    dump_path = (repo_root / dump_file).resolve()
    if not dump_path.exists():
        return {"refreshed": False, "reason": "missing_dump_on_disk"}

    try:
        payload = _read_json(dump_path)
    except Exception as exc:
        return {"refreshed": False, "reason": f"invalid_dump_json:{exc}"}
    if not isinstance(payload, dict):
        return {"refreshed": False, "reason": "dump_not_object"}

    meta = payload.get("__meta") if isinstance(payload.get("__meta"), Mapping) else {}
    print_format = str(meta.get("print_format") or "python").strip() or "python"
    print_shape = str(meta.get("print_shape") or "compact").strip() or "compact"
    previous_context = payload.get("__context") if isinstance(payload.get("__context"), Mapping) else {}
    previous_keys = set(previous_context.keys())

    try:
        meta_apply = _load_apply_module(repo_root)
        surgeon = meta_apply.SourceSurgeon(str(repo_root))
        refreshed_context = surgeon._format_context_map(  # type: ignore[attr-defined]
            surgeon._read_context(context_files),  # type: ignore[attr-defined]
            print_format=print_format,
            print_shape=print_shape,
        )
    except Exception as exc:
        return {"refreshed": False, "reason": f"context_refresh_failed:{exc}"}

    updated_meta = dict(meta)
    prompt_contract_audit = None
    if prompt_text and prompt_text.strip():
        updated_meta, prompt_contract_audit = _reconcile_group_prompt_meta(
            meta=updated_meta,
            prompt=prompt_text,
        )
    if (
        (not prompt_contract_audit or not prompt_contract_audit.get("mismatch_fields"))
        and isinstance(updated_meta.get("prompt_contract_last_audit"), Mapping)
    ):
        prompt_contract_audit = dict(updated_meta.get("prompt_contract_last_audit") or {})
    updated_meta["context_files"] = context_files
    updated_meta["injected_context_files"] = list(refreshed_context.keys())
    updated_meta["context_refresh_at"] = _now_iso()
    payload["__meta"] = updated_meta
    payload["__context"] = refreshed_context
    _write_json(dump_path, payload)
    return {
        "refreshed": True,
        "reason": "ok",
        "context_file_count": len(context_files),
        "context_entry_count": len(refreshed_context),
        "new_entries": sorted(set(refreshed_context.keys()) - previous_keys),
        "prompt_contract_audit": prompt_contract_audit,
    }


def _build_dump_prompt_card_markdown(
    *,
    dump_dir: str,
    wait_notes: str,
    prompt_style: str,
    plan_notes: str,
    total_groups: int,
    total_files: int,
    groups_payload: List[Dict[str, Any]],
) -> str:
    lines = [
        "# Observe Dump Prompt Card",
        "",
        "This file records the effective prompt contract for this grouped observe dump.",
        "",
        "## Global Pass Posture",
        wait_notes.strip() or "_No wait_notes provided._",
        "",
        "## Prompt Style",
        prompt_style.strip() or "_No prompt style provided._",
        "",
        "## Plan Notes",
        plan_notes.strip() or "_No plan notes provided._",
        "",
        "## Dump Metadata",
        f"- dump_dir: `{dump_dir}`",
        f"- total_groups: `{total_groups}`",
        f"- total_files: `{total_files}`",
        f"- generated_at: `{_now_iso()}`",
        "",
        "## Group Prompts",
        "",
    ]
    for group in groups_payload:
        label = str(group.get("label", "group")).strip() or "group"
        file_count = int(group.get("file_count", 0) or 0)
        dump_file = str(group.get("dump_file", "") or "").strip() or "n/a"
        prompt = str(group.get("prompt", "") or "").strip() or "_No prompt generated._"
        standards_lines = _group_standard_summary_lines(
            group.get("standards") if isinstance(group.get("standards"), Mapping) else None
        )
        lines.extend(
            [
                f"### {label}",
                f"- file_count: `{file_count}`",
                f"- dump_file: `{dump_file}`",
                "",
            ]
        )
        if standards_lines:
            lines.extend(
                [
                    "#### Matched Standards",
                    *standards_lines,
                    "",
                ]
            )
        lines.extend(
            [
                prompt,
                "",
            ]
        )
    return "\n".join(lines)


def _ensure_grouped_dump_prompt_artifacts(
    *,
    repo_root: Path,
    plan: Dict[str, Any],
    observe_meta: Dict[str, Any],
    groups_payload: List[Dict[str, Any]],
    wait_notes: str,
    prompt_style: str,
    plan_notes: str,
) -> Dict[str, Any]:
    mode = str(observe_meta.get("mode", "")).strip()
    if mode != "grouped_observe":
        return {
            "checked": False,
            "reason": "non_grouped_mode",
            "card_created": False,
            "contents_updated": False,
            "card_file": None,
        }

    dump_dir_rel = str(observe_meta.get("dump_dir") or plan.get("dump_dir") or "").strip()
    if not dump_dir_rel:
        return {
            "checked": False,
            "reason": "missing_dump_dir",
            "card_created": False,
            "contents_updated": False,
            "card_file": None,
        }

    dump_dir = (repo_root / dump_dir_rel).resolve()
    if not dump_dir.exists():
        return {
            "checked": False,
            "reason": "dump_dir_not_found",
            "card_created": False,
            "contents_updated": False,
            "card_file": None,
        }

    card_name = "00_meta_instruction.md"
    card_path = dump_dir / card_name
    total_groups = int(observe_meta.get("total_groups", len(groups_payload)))
    total_files = int(observe_meta.get("total_files", sum(int(g.get("file_count", 0) or 0) for g in groups_payload)))

    card_created = False
    if not card_path.exists():
        card_md = _build_dump_prompt_card_markdown(
            dump_dir=dump_dir_rel,
            wait_notes=wait_notes,
            prompt_style=prompt_style,
            plan_notes=plan_notes,
            total_groups=total_groups,
            total_files=total_files,
            groups_payload=groups_payload,
        )
        card_path.write_text(card_md, encoding="utf-8")
        card_created = True

    contents_updated = False
    contents_path = dump_dir / "00_contents.json"
    if contents_path.exists():
        try:
            contents = _read_json(contents_path)
            if isinstance(contents, dict) and contents.get("meta_instruction_file") != card_name:
                contents["meta_instruction_file"] = card_name
                _write_json(contents_path, contents)
                contents_updated = True
        except Exception:
            contents_updated = False

    card_file: Optional[str] = None
    try:
        card_file = str(card_path.relative_to(repo_root))
    except Exception:
        card_file = str(card_path)

    return {
        "checked": True,
        "reason": "ok",
        "card_created": card_created,
        "contents_updated": contents_updated,
        "card_file": card_file,
    }


def _json_fence(payload: Any) -> str:
    return "```json\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n```"


def _trim_response_markdown(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].strip() == "# Observe Group Response":
        lines = lines[1:]
    return "\n".join(lines).strip()


def _slugify_label(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower())
    return text.strip("_") or "group"


def _normalize_bridge_failure(exc: Exception) -> Dict[str, Optional[str]]:
    category = str(getattr(exc, "category", "") or "").strip() or "bridge_error"
    stage = str(getattr(exc, "stage", "") or "").strip() or None
    message = str(exc).strip() or exc.__class__.__name__
    if category == "bridge_error":
        lowered = message.lower()
        if "cdp endpoint" in lowered or "chrome launched but cdp" in lowered:
            category = "cdp_unreachable"
        elif "launch chrome" in lowered or "chrome launcher exited" in lowered or "chrome binary" in lowered:
            category = "browser_launch_failed"
        elif "cloudflare" in lowered or "cf_challenge" in lowered:
            category = "provider_challenge"
        elif "timeout waiting for ai response" in lowered:
            category = "provider_timeout"
        elif "send button" in lowered or "editor not found" in lowered or "extraction" in lowered:
            category = "provider_selector_failure"
    if stage is None:
        if category in {"browser_launch_failed", "cdp_unreachable"}:
            stage = "browser"
        elif category == "provider_timeout":
            stage = "provider_wait"
        elif category == "provider_challenge":
            stage = "provider_open"
        elif category == "provider_selector_failure":
            stage = "provider_interaction"
    return {"category": category, "stage": stage, "message": message}


_KNOWN_RESPONSE_HEADINGS = (
    "FILE SYNOPSIS",
    "PROBLEM SPACE MAP",
    "LOCKED FACTS",
    "SURFACED QUESTIONS",
    "TARGET DELTAS",
    "NEXT FORK",
    "RECOVERY BOUNDARY",
    "OPERATOR OR AGENT ACTION MODEL",
    "FIRST PROOF DELTAS",
    "OPEN QUESTIONS",
    "CONFIRMED FACTS",
    "INFERRED CONTRACTS",
    "CONTRADICTIONS AND TENSIONS",
    "UNKNOWNS",
    "NEXT-PROBE QUESTIONS",
    "COMPATIBLE",
    "RISKY",
    "UNCOVERED",
    "CONFIRMED",
    "RISKS",
    "MISSING",
    "HIGH-CONFIDENCE FINDINGS",
    "CROSS-GROUP CONTRADICTIONS",
    "DECISION LIST",
)


def _normalize_contract_heading(name: str) -> str:
    return re.sub(r"\s+", " ", str(name or "").strip()).upper()


def _coerce_output_contract(output_contract: object) -> List[str]:
    if not isinstance(output_contract, list):
        return []
    normalized: List[str] = []
    for item in output_contract:
        heading = _normalize_contract_heading(str(item or ""))
        if heading:
            normalized.append(heading)
    return list(dict.fromkeys(normalized))


def _extract_output_contract_from_text(text: str) -> List[str]:
    ordered_hits: List[Tuple[int, str]] = []
    source = str(text or "")
    for heading in _KNOWN_RESPONSE_HEADINGS:
        pattern = re.compile(
            rf"(?im)(?:^|[`(])(?:#{{1,6}}\s*)?(?:\d+[\.\)]\s*)?{re.escape(heading)}(?=$|[`):;\n])"
        )
        match = pattern.search(source)
        if not match:
            continue
        ordered_hits.append((match.start(), heading))
    ordered_hits.sort(key=lambda item: item[0])
    return list(dict.fromkeys(name for _, name in ordered_hits))


def _resolve_output_contract(prompt_text: str, output_contract: object = None) -> List[str]:
    explicit = _coerce_output_contract(output_contract)
    if explicit:
        return explicit
    derived = _extract_output_contract_from_text(prompt_text)
    if derived:
        return derived
    upper = (prompt_text or "").upper()
    if "CONFIRMED FACTS" in upper:
        return [
            "CONFIRMED FACTS",
            "INFERRED CONTRACTS",
            "CONTRADICTIONS AND TENSIONS",
            "UNKNOWNS",
            "NEXT-PROBE QUESTIONS",
        ]
    return []


def _required_response_sections(prompt_text: str, output_contract: object = None) -> List[str]:
    return _resolve_output_contract(prompt_text, output_contract)


def _resolve_response_mode(prompt_metadata: Mapping[str, Any] | None) -> str:
    token = str((prompt_metadata or {}).get("response_mode", "structured_sections")).strip()
    return token or "structured_sections"


def _coerce_required_epistemic_tags(prompt_metadata: Mapping[str, Any] | None) -> List[str]:
    tags = (prompt_metadata or {}).get("required_epistemic_tags")
    if not isinstance(tags, list) or not tags:
        return ["FACT", "INFERENCE", "TENSION", "UNKNOWN"]
    output: List[str] = []
    for item in tags:
        token = re.sub(r"[^A-Z_]+", "", str(item or "").upper())
        if token:
            output.append(token)
    return list(dict.fromkeys(output)) or ["FACT", "INFERENCE", "TENSION", "UNKNOWN"]


def _epistemic_closing_section(prompt_metadata: Mapping[str, Any] | None) -> str:
    token = str((prompt_metadata or {}).get("closing_section", "BEST NEXT QUESTIONS")).strip()
    return re.sub(r"\s+", " ", token).upper() or "BEST NEXT QUESTIONS"


_STRUCTURAL_ONLY_ISSUES = {
    "meta_preface",
    "section_order_drift",
    "surface_extra_text",
    "surface_relaxed_parse",
    "unclosed_code_fence",
    "unexpected_preface",
    "unterminated_tail",
}
_SEMANTIC_ISSUES = {
    "empty_response",
    "invalid_best_next_questions_count",
    "invalid_next_action_tail",
    "invalid_surface_field",
    "missing_best_next_questions",
    "missing_epistemic_tags",
    "missing_next_action",
    "missing_required_headings",
    "missing_surfaced_question_subsections",
    "missing_surface_fields",
    "provider_error",
    "response_too_short",
}
_SEMANTIC_DEGRADED_STATUSES = {"degraded_content", "degraded_semantic"}


def _is_semantic_issue(issue: str) -> bool:
    token = str(issue or "").strip()
    if not token:
        return False
    if token in _STRUCTURAL_ONLY_ISSUES:
        return False
    if token in _SEMANTIC_ISSUES:
        return True
    return token.startswith(("provider_error:", "response_too_short:"))


def _section_heading_pattern(name: str) -> re.Pattern[str]:
    escaped = re.escape(name)
    return re.compile(rf"(?im)^\s*(?:#{{1,6}}\s*)?(?:\d+[\.\)]\s*)?{escaped}\s*:?\s*$")


def _response_marker_specs(required_sections: List[str]) -> List[Tuple[str, str]]:
    specs: List[Tuple[str, str]] = []
    for name in required_sections:
        specs.append((name, "##"))
        if name == "SURFACED QUESTIONS":
            specs.extend(
                [
                    ("USER DECISIONS", "###"),
                    ("AGENT FOLLOWUPS", "###"),
                ]
            )
    specs.append(("NEXT_ACTION:", "NEXT_ACTION"))
    return specs


def _response_marker_pattern(name: str) -> re.Pattern[str]:
    if name == "NEXT_ACTION:":
        return re.compile(r"(?i)NEXT_ACTION:\s*")
    escaped = re.escape(name)
    return re.compile(rf"(?i)(?:#{{1,6}}\s*)?(?:\d+[\.\)]\s*)?{escaped}\s*:?\s*")


def _marker_token_present(text: str, name: str) -> bool:
    return bool(_response_marker_pattern(name).search(text or ""))


def _has_inline_heading_collapse(text: str, marker_specs: List[Tuple[str, str]]) -> bool:
    for name, _level in marker_specs:
        if name == "NEXT_ACTION:":
            if re.search(r"(?i)NEXT_ACTION:(?=\S)", text or ""):
                return True
            continue
        escaped = re.escape(name)
        if re.search(rf"(?i){escaped}(?=[^\s:\n])", text or ""):
            return True
    return False


def _rewrite_response_from_markers(text: str, marker_specs: List[Tuple[str, str]]) -> Optional[str]:
    matches: List[Tuple[str, str, int, int]] = []
    cursor = 0
    for name, level in marker_specs:
        match = _response_marker_pattern(name).search(text or "", cursor)
        if not match:
            continue
        matches.append((name, level, match.start(), match.end()))
        cursor = match.end()
    if len(matches) < 2:
        return None

    lines: List[str] = []
    prefix = (text or "")[:matches[0][2]].strip()
    if prefix:
        lines.extend([prefix, ""])

    for index, (name, level, _start, end) in enumerate(matches):
        next_start = matches[index + 1][2] if index + 1 < len(matches) else len(text or "")
        body = ((text or "")[end:next_start]).strip()
        if level == "NEXT_ACTION":
            action = _safe_text(body)
            if action and not action.lower().startswith("on continue, i will"):
                action = f"On continue, I will {action}"
            action = _normalize_next_action(action) if action else ""
            lines.append(f"NEXT_ACTION: {action}".rstrip())
            continue
        lines.append(f"{level} {name}")
        if body:
            lines.append(body)
        lines.append("")
    return "\n".join(lines).strip()


def _normalize_group_response_text(
    prompt_text: str,
    response_text: str,
    output_contract: object = None,
    prompt_metadata: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    text = str(response_text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\u200b-\u200d\ufeff]", "", text)
    repair_actions: List[str] = []
    response_mode = _resolve_response_mode(prompt_metadata)
    if response_mode == "epistemic_tags":
        next_action = _extract_next_action(text)
        if next_action:
            text_without_tail = _NEXT_ACTION_RE.sub("", text).rstrip()
            rebuilt = f"{text_without_tail}\n\nNEXT_ACTION: {next_action}".strip()
            if rebuilt != text.strip():
                repair_actions.append("next_action_tail_normalized")
            text = rebuilt
        return {
            "text": text.strip(),
            "repair_actions": list(dict.fromkeys(repair_actions)),
        }
    required_sections = _resolve_output_contract(prompt_text, output_contract)
    marker_specs = _response_marker_specs(required_sections)
    _positions, missing_headings = _find_section_heading_positions(text, required_sections)
    should_rewrite = _has_inline_heading_collapse(text, marker_specs) or any(
        _marker_token_present(text, name) for name in missing_headings
    )
    if should_rewrite:
        rewritten = _rewrite_response_from_markers(text, marker_specs)
        if rewritten and rewritten != text.strip():
            text = rewritten
            repair_actions.append("inline_headings_split")

    for name, level in marker_specs:
        if level not in {"##", "###"}:
            continue
        pattern = _section_heading_pattern(name)
        normalized_heading = f"{level} {name}"
        rewritten, count = pattern.subn(normalized_heading, text)
        if count > 0 and rewritten != text:
            text = rewritten
            repair_actions.append("markdown_heading_normalized")

    next_action = _extract_next_action(text)
    if next_action:
        text_without_tail = _NEXT_ACTION_RE.sub("", text).rstrip()
        rebuilt = f"{text_without_tail}\n\nNEXT_ACTION: {next_action}".strip()
        if rebuilt != text.strip():
            repair_actions.append("next_action_tail_normalized")
        text = rebuilt

    deduped_actions = list(dict.fromkeys(repair_actions))
    return {
        "text": text.strip(),
        "repair_actions": deduped_actions,
    }


def _find_section_heading_positions(text: str, sections: List[str]) -> Tuple[List[Tuple[str, int]], List[str]]:
    positions: List[Tuple[str, int]] = []
    missing: List[str] = []
    for name in sections:
        match = _section_heading_pattern(name).search(text or "")
        if not match:
            missing.append(name)
            continue
        positions.append((name, match.start()))
    return positions, missing


def _extract_next_fork_block(text: str) -> Optional[str]:
    if not text.strip():
        return None
    pattern = re.compile(
        r"(?ims)(?:^|\n)(?:#{1,6}\s*)?NEXT FORK\b[:\s]*\n?(.*?)(?=\n(?:#{1,6}\s*[A-Z][^\n]*|NEXT_ACTION:|\Z))"
    )
    match = pattern.search(text)
    if not match:
        return None
    block = re.sub(r"\s+", " ", match.group(1) or "").strip()
    return block or None


def _extract_next_fork_kind(text: str) -> Optional[str]:
    block = _extract_next_fork_block(text)
    search_text = block or text
    match = re.search(r"\b(stop|next_observe|synthesis|patch|validate|review)\b", search_text, re.IGNORECASE)
    return match.group(1).lower() if match else None


def _surface_json_block_candidates(text: str) -> List[str]:
    return json_candidate_blocks(text)


def _decode_surface_json_candidate(text: str) -> Any:
    decoder = json.JSONDecoder()
    payload, end = decoder.raw_decode(str(text or "").strip())
    if str(text or "").strip()[end:].strip():
        raise ValueError("json candidate had trailing content")
    return payload


def _surface_diff_block_candidates(text: str) -> List[str]:
    source = str(text or "")
    stripped = source.strip()
    candidates: List[str] = []
    if stripped.startswith("--- "):
        candidates.append(stripped)

    for match in re.finditer(r"```(?:diff|patch)?\s*(.*?)```", source, flags=re.IGNORECASE | re.DOTALL):
        block = match.group(1).strip()
        if block.startswith("--- "):
            candidates.append(block)

    diff_start = None
    lines = source.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("--- "):
            diff_start = index
            break
    if diff_start is not None:
        tail = "\n".join(lines[diff_start:]).strip()
        if tail.startswith("--- "):
            candidates.append(tail)

    return list(dict.fromkeys(candidates))


def _surface_fieldspecs(response_surface: Mapping[str, Any]) -> List[dict[str, Any]]:
    fields: List[dict[str, Any]] = []
    for item in [
        *(response_surface.get("required_fields", []) if isinstance(response_surface.get("required_fields"), list) else []),
        *(response_surface.get("optional_fields", []) if isinstance(response_surface.get("optional_fields"), list) else []),
    ]:
        if isinstance(item, Mapping):
            fields.append(dict(item))
    return fields


def _extract_surface_payload_from_json(
    payload: Any,
    *,
    response_surface: Mapping[str, Any],
) -> Dict[str, Any]:
    fields = _surface_fieldspecs(response_surface)
    field_ids = {
        str(item.get("field_id") or "").strip()
        for item in fields
        if str(item.get("field_id") or "").strip()
    }
    required_ids = [
        str(item.get("field_id") or "").strip()
        for item in (response_surface.get("required_fields", []) if isinstance(response_surface.get("required_fields"), list) else [])
        if isinstance(item, Mapping) and str(item.get("field_id") or "").strip()
    ]

    def _from_mapping(mapping: Mapping[str, Any]) -> Dict[str, Any]:
        extracted = {
            field_id: mapping[field_id]
            for field_id in field_ids
            if field_id in mapping
        }
        if extracted:
            return extracted

        embedded = mapping.get("payload")
        if isinstance(embedded, Mapping):
            extracted = {
                field_id: embedded[field_id]
                for field_id in field_ids
                if field_id in embedded
            }
            if extracted:
                return extracted

        if required_ids == ["operations"]:
            for key in ("operations",):
                value = mapping.get(key)
                if isinstance(value, list):
                    return {"operations": value}
            apply_plan = mapping.get("apply_plan")
            if isinstance(apply_plan, Mapping) and isinstance(apply_plan.get("operations"), list):
                return {"operations": apply_plan.get("operations")}
            plan = mapping.get("plan")
            if isinstance(plan, Mapping) and isinstance(plan.get("operations"), list):
                return {"operations": plan.get("operations")}

        return {}

    if isinstance(payload, Mapping):
        return _from_mapping(payload)
    if isinstance(payload, list) and required_ids == ["operations"]:
        return {"operations": payload}
    return {}


_PLAIN_SURFACE_KEY_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*):(?:\s*(?P<value>.*))?$")


def _coerce_plain_surface_scalar(value: str) -> Any:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith(('"', "'")) and text.endswith(('"', "'")) and len(text) >= 2:
        try:
            return json.loads(text)
        except Exception:
            return text[1:-1]
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None
    if text.startswith("{") or text.startswith("["):
        try:
            return json.loads(text)
        except Exception:
            return text
    return text


def _finalize_plain_surface_block(lines: Sequence[str]) -> Any:
    normalized = [str(line).strip() for line in lines if str(line).strip()]
    if not normalized:
        return ""
    if all(item.startswith("- ") for item in normalized):
        return [_coerce_plain_surface_scalar(item[2:]) for item in normalized if item[2:].strip()]
    if len(normalized) == 1:
        return _coerce_plain_surface_scalar(normalized[0])
    return [_coerce_plain_surface_scalar(item) for item in normalized]


def _parse_plain_surface_mapping(lines: Sequence[str]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    current_key: str | None = None
    current_lines: List[str] = []

    def flush() -> None:
        nonlocal current_key, current_lines
        if current_key is None:
            return
        payload[current_key] = _finalize_plain_surface_block(current_lines)
        current_key = None
        current_lines = []

    for raw_line in lines:
        stripped = str(raw_line).strip()
        if not stripped:
            if current_key is not None:
                current_lines.append("")
            continue
        match = _PLAIN_SURFACE_KEY_RE.match(stripped)
        if match:
            flush()
            key = str(match.group("key") or "").strip()
            inline_value = str(match.group("value") or "").strip()
            if inline_value:
                payload[key] = _coerce_plain_surface_scalar(inline_value)
            else:
                current_key = key
                current_lines = []
            continue
        if current_key is not None:
            current_lines.append(stripped)
    flush()
    return payload


def _parse_plain_surface_sequence(lines: Sequence[str]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    current_lines: List[str] = []
    first_key: str | None = None

    def flush() -> None:
        nonlocal current_lines
        item = _parse_plain_surface_mapping(current_lines)
        if item:
            items.append(item)
        current_lines = []

    for raw_line in lines:
        stripped = str(raw_line).strip()
        if not stripped:
            if current_lines:
                current_lines.append("")
            continue
        match = _PLAIN_SURFACE_KEY_RE.match(stripped)
        if match:
            key = str(match.group("key") or "").strip()
            if first_key is None:
                first_key = key
            elif key == first_key and current_lines:
                flush()
        current_lines.append(str(raw_line))
    flush()
    return items


def _split_plain_surface_blocks(response_text: str, *, field_ids: Sequence[str]) -> Dict[str, str]:
    wanted = {str(field_id).strip() for field_id in field_ids if str(field_id).strip()}
    if not wanted:
        return {}

    blocks: Dict[str, List[str]] = {}
    current_field: str | None = None
    current_lines: List[str] = []

    def flush() -> None:
        nonlocal current_field, current_lines
        if current_field is None:
            return
        blocks[current_field] = list(current_lines)
        current_field = None
        current_lines = []

    for raw_line in str(response_text or "").splitlines():
        stripped = raw_line.strip()
        match = _PLAIN_SURFACE_KEY_RE.match(stripped)
        if raw_line == raw_line.lstrip() and match:
            key = str(match.group("key") or "").strip()
            if key in wanted:
                flush()
                current_field = key
                inline_value = str(match.group("value") or "").strip()
                current_lines = [inline_value] if inline_value else []
                continue
        if current_field is not None:
            current_lines.append(raw_line)
    flush()
    return {
        field_id: "\n".join(lines).strip()
        for field_id, lines in blocks.items()
        if any(str(line).strip() for line in lines)
    }


def _parse_plain_surface_block(block_text: str, *, field_spec: Mapping[str, Any]) -> Any:
    lines = str(block_text or "").splitlines()
    value_shape = str(field_spec.get("value_shape") or "").strip().lower()
    field_format = str(field_spec.get("format") or "").strip().lower()

    if value_shape == "array":
        return _parse_plain_surface_sequence(lines)
    if field_format == "json" or value_shape in {"object", "json"}:
        return _parse_plain_surface_mapping(lines)
    return _finalize_plain_surface_block(lines)


def _relaxed_surface_parse(
    response_text: str,
    *,
    response_surface: Mapping[str, Any],
) -> Optional[Dict[str, Any]]:
    fields = _surface_fieldspecs(response_surface)
    required_ids = [
        str(item.get("field_id") or "").strip()
        for item in (response_surface.get("required_fields", []) if isinstance(response_surface.get("required_fields"), list) else [])
        if isinstance(item, Mapping) and str(item.get("field_id") or "").strip()
    ]
    if not fields or not required_ids:
        return None

    surface_kind = str(response_surface.get("surface_kind") or "").strip() or "fill_form_v1"
    if surface_kind == "unified_diff_v1":
        compile_fields = [
            item
            for item in fields
            if str(item.get("merge_mode") or "").strip() == "compile_apply"
            and str(item.get("field_id") or "").strip()
        ]
        if len(compile_fields) != 1:
            return None
        field_id = str(compile_fields[0].get("field_id") or "").strip()
        if not field_id:
            return None
        diff_candidates = _surface_diff_block_candidates(response_text)
        if not diff_candidates:
            return None
        return {
            "payload": {field_id: diff_candidates[0]},
            "missing_fields": [],
            "field_errors": [],
            "extra_text": "",
            "issues": ["surface_relaxed_parse"],
            "repair_actions": ["surface_relaxed_parse"],
        }

    for candidate in _surface_json_block_candidates(response_text):
        try:
            decoded = _decode_surface_json_candidate(candidate)
        except Exception:
            continue
        payload = _extract_surface_payload_from_json(
            decoded,
            response_surface=response_surface,
        )
        if not payload:
            continue
        missing = [field_id for field_id in required_ids if field_id not in payload]
        if missing:
            continue
        return {
            "payload": payload,
            "missing_fields": [],
            "field_errors": [],
            "extra_text": "",
            "issues": ["surface_relaxed_parse"],
            "repair_actions": ["surface_relaxed_parse"],
        }

    field_specs = {
        str(item.get("field_id") or "").strip(): dict(item)
        for item in fields
        if str(item.get("field_id") or "").strip()
    }
    keyed_blocks = _split_plain_surface_blocks(response_text, field_ids=field_specs.keys())
    if keyed_blocks:
        payload: Dict[str, Any] = {}
        for field_id, block_text in keyed_blocks.items():
            spec = field_specs.get(field_id, {})
            parsed_value = _parse_plain_surface_block(block_text, field_spec=spec)
            if parsed_value in (None, "", [], {}):
                continue
            payload[field_id] = parsed_value
        missing = [field_id for field_id in required_ids if field_id not in payload]
        if not missing:
            return {
                "payload": payload,
                "missing_fields": [],
                "field_errors": [],
                "extra_text": "",
                "issues": ["surface_relaxed_parse"],
                "repair_actions": ["surface_relaxed_parse"],
            }
    return None


def _collect_group_response_issues(
    prompt_text: str,
    response_text: str,
    output_contract: object = None,
    prompt_metadata: Mapping[str, Any] | None = None,
    response_surface: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    issues: List[str] = []

    # --- Provider error checks happen before structural analysis. Size-based
    # gating lives in observe_resilience, not in contract validation here. ---
    from system.lib.observe_resilience import detect_provider_error
    provider_error = detect_provider_error(response_text)
    if provider_error:
        issues.append(f"provider_error:{provider_error}")
    if response_surface:
        heading_by_field = {
            str(item.get("field_id")).strip(): str(item.get("heading") or item.get("field_id") or "").strip()
            for item in response_surface.get("required_fields", [])
            if isinstance(item, Mapping) and str(item.get("field_id", "")).strip()
        }
        fallback_used = False
        repair_actions: List[str] = []
        try:
            parsed_surface = parse_surface_response(
                response_text,
                response_surface=response_surface,
            )
        except Exception:
            parsed_surface = _relaxed_surface_parse(
                response_text,
                response_surface=response_surface,
            )
            fallback_used = parsed_surface is not None
            if parsed_surface is None:
                parsed_surface = {
                    "payload": {},
                    "missing_fields": [
                        str(item.get("field_id")).strip()
                        for item in response_surface.get("required_fields", [])
                        if isinstance(item, Mapping) and str(item.get("field_id", "")).strip()
                    ],
                    "field_errors": ["surface_parse_failed"],
                    "extra_text": "",
                    "repair_actions": [],
                }
                issues.append("invalid_surface_field")
        else:
            if (
                parsed_surface.get("missing_fields")
                or parsed_surface.get("field_errors")
            ):
                relaxed = _relaxed_surface_parse(
                    response_text,
                    response_surface=response_surface,
                )
                if relaxed is not None:
                    parsed_surface = relaxed
                    fallback_used = True
            if parsed_surface.get("missing_fields"):
                issues.append("missing_surface_fields")
            if parsed_surface.get("field_errors"):
                issues.append("invalid_surface_field")
            if parsed_surface.get("extra_text"):
                issues.append("surface_extra_text")
        repair_actions.extend(
            str(item).strip()
            for item in parsed_surface.get("repair_actions", [])
            if str(item).strip()
        )
        issues.extend(
            str(item).strip()
            for item in parsed_surface.get("issues", [])
            if str(item).strip()
        )
        if fallback_used and not parsed_surface.get("extra_text"):
            issues.append("surface_relaxed_parse")
        return {
            "issues": list(dict.fromkeys(issues)),
            "repair_actions": list(dict.fromkeys(repair_actions)),
            "required_sections": [
                str(item.get("heading") or item.get("field_id") or "").strip()
                for item in response_surface.get("required_fields", [])
                if isinstance(item, Mapping) and str(item.get("heading") or item.get("field_id") or "").strip()
            ],
            "missing_sections": [
                heading_by_field.get(str(item).strip(), str(item).strip())
                for item in parsed_surface.get("missing_fields", [])
                if str(item).strip()
            ],
            "next_fork": _extract_next_fork_kind(
                project_response_surface_payload(response_surface, payload=parsed_surface.get("payload", {}))
            ),
            "next_fork_block": _extract_next_fork_block(
                project_response_surface_payload(response_surface, payload=parsed_surface.get("payload", {}))
            ),
            "surface_payload": parsed_surface.get("payload", {}),
            "surface_missing_fields": parsed_surface.get("missing_fields", []),
            "surface_field_errors": parsed_surface.get("field_errors", []),
            "surface_extra_text": parsed_surface.get("extra_text", ""),
            "surface_projection": project_response_surface_payload(
                response_surface,
                payload=parsed_surface.get("payload", {}),
            ),
        }
    response_mode = _resolve_response_mode(prompt_metadata)
    if response_mode == "epistemic_tags":
        required_tags = _coerce_required_epistemic_tags(prompt_metadata)
        missing_tags = [
            tag
            for tag in required_tags
            if f"[{tag}]" not in str(response_text or "").upper()
        ]
        if missing_tags:
            issues.append("missing_epistemic_tags")
        closing_section = _epistemic_closing_section(prompt_metadata)
        sections = _extract_heading_sections(response_text or "")
        closing_items = _section_items(sections.get(closing_section, ""))
        if closing_section not in sections:
            issues.append("missing_best_next_questions")
        elif not 3 <= len(closing_items) <= 5:
            issues.append("invalid_best_next_questions_count")
        if "NEXT_ACTION:" not in (response_text or ""):
            issues.append("missing_next_action")
        last_nonempty_line = ""
        for line in reversed((response_text or "").splitlines()):
            stripped_line = line.strip()
            if stripped_line:
                last_nonempty_line = stripped_line
                break
        valid_next_action_tail = bool(
            last_nonempty_line
            and re.fullmatch(r"NEXT_ACTION:\s*On continue, I will .+", last_nonempty_line)
        )
        if last_nonempty_line and not valid_next_action_tail:
            issues.append("invalid_next_action_tail")
        if (response_text or "").rstrip().count("```") % 2 == 1:
            issues.append("unclosed_code_fence")
        if not str(response_text or "").strip():
            issues.append("empty_response")
        return {
            "issues": issues,
            "required_sections": [closing_section],
            "missing_sections": [closing_section] if closing_section not in sections else [],
            "next_fork": _extract_next_fork_kind(response_text),
            "next_fork_block": _extract_next_fork_block(response_text),
        }
    required_sections = _resolve_output_contract(prompt_text, output_contract)
    heading_positions, missing_headings = _find_section_heading_positions(response_text or "", required_sections)
    if missing_headings:
        issues.append("missing_required_headings")
    heading_offsets = [offset for _, offset in heading_positions]
    if heading_offsets and heading_offsets != sorted(heading_offsets):
        issues.append("section_order_drift")
    first_heading_offset = heading_offsets[0] if heading_offsets else None
    if first_heading_offset is not None:
        prefix = (response_text or "")[:first_heading_offset].strip()
        if prefix:
            issues.append("unexpected_preface")
            normalized_prefix = prefix.lower()
            meta_markers = (
                "defining the task",
                "clarifying re-entry rules",
                "clarifying re-entry",
                "refining bridge resumption",
                "gemini said",
                "i now understand",
                "i've clarified",
            )
            if any(marker in normalized_prefix for marker in meta_markers):
                issues.append("meta_preface")
    if "SURFACED QUESTIONS" in required_sections:
        surfaced_subsections = []
        for name in ("USER DECISIONS", "AGENT FOLLOWUPS"):
            if _section_heading_pattern(name).search(response_text or ""):
                surfaced_subsections.append(name)
        if len(surfaced_subsections) != 2:
            issues.append("missing_surfaced_question_subsections")
    if "NEXT_ACTION:" not in (response_text or ""):
        issues.append("missing_next_action")
    last_nonempty_line = ""
    for line in reversed((response_text or "").splitlines()):
        stripped_line = line.strip()
        if stripped_line:
            last_nonempty_line = stripped_line
            break
    valid_next_action_tail = bool(
        last_nonempty_line
        and re.fullmatch(r"NEXT_ACTION:\s*On continue, I will .+", last_nonempty_line)
    )
    if last_nonempty_line and not valid_next_action_tail:
        issues.append("invalid_next_action_tail")
    stripped = (response_text or "").rstrip()
    if stripped:
        if stripped.count("```") % 2 == 1:
            issues.append("unclosed_code_fence")
        if not valid_next_action_tail and stripped[-1] not in ".!?)`]":
            issues.append("unterminated_tail")
    else:
        issues.append("empty_response")
    return {
        "issues": issues,
        "required_sections": required_sections,
        "missing_sections": missing_headings,
        "next_fork": _extract_next_fork_kind(response_text),
        "next_fork_block": _extract_next_fork_block(response_text),
    }


def _validate_group_response(
    prompt_text: str,
    response_text: str,
    output_contract: object = None,
    prompt_metadata: Mapping[str, Any] | None = None,
    response_surface: Mapping[str, Any] | None = None,
    response_schema: Mapping[str, Any] | None = None,
    json_only: bool = False,
) -> Dict[str, Any]:
    if response_schema:
        payload, parse_issues = _extract_schema_payload(response_text, schema=response_schema)
        # Coerce structural deviations before validation — objects where
        # strings expected, synonym keys (e.g. update→summary), etc.
        if payload is not None and isinstance(payload, Mapping):
            payload = _coerce_payload_to_schema(payload, response_schema)
        issues = list(parse_issues)
        if not parse_issues:
            issues.extend(_validate_schema_node(payload, response_schema))
        blocking_issues = [issue for issue in issues if issue]
        status = "ok" if not blocking_issues else "degraded_semantic"
        normalized_text = (
            json.dumps(payload, indent=2, ensure_ascii=False)
            if payload is not None and not blocking_issues
            else str(response_text or "").strip()
        )
        return {
            "status": status,
            "issues": blocking_issues,
            "detected_issues": blocking_issues,
            "repair_actions": [],
            "required_sections": list(response_schema.get("required", [])) if isinstance(response_schema.get("required"), list) else [],
            "missing_sections": [],
            "normalized_text": normalized_text,
            "receipt_payload": payload if not blocking_issues else None,
            "response_schema": dict(response_schema),
            "json_only": bool(json_only),
        }

    if response_surface:
        surface_quality = _collect_group_response_issues(
            prompt_text,
            response_text,
            output_contract=output_contract,
            prompt_metadata=prompt_metadata,
            response_surface=response_surface,
        )
        issues = [
            str(item).strip()
            for item in surface_quality.get("issues", [])
            if str(item).strip()
        ]
        blocking_issues = [issue for issue in issues if _is_semantic_issue(issue)]
        status = "ok"
        if blocking_issues:
            status = "degraded_semantic"
        elif issues:
            status = "degraded_structural"
        normalized_text = str(surface_quality.get("surface_projection", "") or "").strip()
        return {
            "status": status,
            "issues": issues,
            "detected_issues": issues,
            "repair_actions": [
                str(item).strip()
                for item in surface_quality.get("repair_actions", [])
                if str(item).strip()
            ],
            "required_sections": surface_quality.get("required_sections", []),
            "missing_sections": surface_quality.get("missing_sections", []),
            "next_fork": surface_quality.get("next_fork"),
            "next_fork_block": surface_quality.get("next_fork_block"),
            "normalized_text": normalized_text,
            "surface_payload": surface_quality.get("surface_payload", {}),
            "surface_kind": str(response_surface.get("surface_kind") or "").strip() or None,
            "response_kind": str(response_surface.get("response_kind") or "").strip() or None,
        }

    normalized = _normalize_group_response_text(
        prompt_text,
        response_text,
        output_contract=output_contract,
        prompt_metadata=prompt_metadata,
    )
    normalized_text = str(normalized.get("text", "") or "")
    repair_actions = [
        str(item).strip()
        for item in normalized.get("repair_actions", [])
        if str(item).strip()
    ]
    raw_quality = _collect_group_response_issues(
        prompt_text,
        response_text,
        output_contract=output_contract,
        prompt_metadata=prompt_metadata,
        response_surface=response_surface,
    )
    normalized_quality = _collect_group_response_issues(
        prompt_text,
        normalized_text,
        output_contract=output_contract,
        prompt_metadata=prompt_metadata,
        response_surface=response_surface,
    )
    unresolved_issues = [
        str(item).strip()
        for item in normalized_quality.get("issues", [])
        if str(item).strip()
    ]
    raw_issues = [
        str(item).strip()
        for item in raw_quality.get("issues", [])
        if str(item).strip()
    ]
    blocking_issues = [issue for issue in unresolved_issues if _is_semantic_issue(issue)]

    if not normalized_text.strip() or blocking_issues:
        status = "degraded_semantic"
    elif unresolved_issues or repair_actions or raw_issues:
        status = "degraded_structural"
    else:
        status = "ok"

    return {
        "status": status,
        "issues": unresolved_issues,
        "detected_issues": raw_issues,
        "repair_actions": repair_actions,
        "required_sections": normalized_quality.get("required_sections", []),
        "missing_sections": normalized_quality.get("missing_sections", []),
        "next_fork": normalized_quality.get("next_fork"),
        "next_fork_block": normalized_quality.get("next_fork_block"),
        "normalized_text": normalized_text,
    }


def _build_group_outputs_markdown(
    *,
    repo_root: Path,
    groups_payload: List[Dict[str, Any]],
    concatenate_group_outputs: bool,
) -> str:
    if not groups_payload:
        return "_No group outputs recorded._"

    lines: List[str] = []
    for group in groups_payload:
        label = str(group.get("label", "group")).strip() or "group"
        response_file = str(group.get("response_file", "")).strip()
        response_dispatch_file = str(group.get("response_dispatch_file", "")).strip()
        dump_file = str(group.get("dump_file", "")).strip()
        status = str(group.get("response_status", "")).strip() or "not_run"
        quality_status = str(group.get("response_quality_status", "")).strip() or None
        raw_next_fork = group.get("next_fork")
        next_fork = None if raw_next_fork in {None, ""} else str(raw_next_fork).strip() or None
        lines.append(f"### {label}")
        lines.append(f"- status: `{status}`")
        if quality_status:
            lines.append(f"- quality: `{quality_status}`")
        if next_fork:
            lines.append(f"- next_fork: `{next_fork}`")
        if response_file:
            lines.append(f"- response_file: `{response_file}`")
            if response_dispatch_file:
                lines.append(f"- bridge_dispatch_file: `{response_dispatch_file}`")
            if dump_file:
                lines.append(f"- dump_file: `{dump_file}`")
            issues = group.get("response_quality_issues", [])
            if isinstance(issues, list) and issues:
                lines.append(f"- quality_issues: `{', '.join(str(item) for item in issues)}`")
            if concatenate_group_outputs:
                response_path = (repo_root / response_file).resolve()
                if response_path.exists():
                    response_text = _trim_response_markdown(response_path.read_text(encoding="utf-8"))
                    preview = response_text.split("## Response", 1)[-1].strip() if "## Response" in response_text else response_text
                    preview = re.sub(r"\s+", " ", preview).strip()
                    if preview:
                        lines.append(f"- response_preview: {preview[:320]}")
            else:
                lines.append("- response_preview: _Stored separately; not concatenated here._")
        else:
            if dump_file:
                lines.append(f"- dump_file: `{dump_file}`")
            lines.append("- response_preview: _No bridge response was available._")
        lines.append("")
    return "\n".join(lines).strip() or "_No group outputs recorded._"


def _build_group_quality_summary(groups_payload: List[Dict[str, Any]]) -> Dict[str, Any]:
    status_counts = Counter(str(group.get("response_status", "") or "not_run") for group in groups_payload)
    quality_counts = Counter(str(group.get("response_quality_status", "") or "unknown") for group in groups_payload)
    degraded_labels = [
        str(group.get("label", "group")).strip() or "group"
        for group in groups_payload
        if str(group.get("response_quality_status", "")).strip() in {
            "degraded_format",
            "degraded_content",
            "degraded_structural",
            "degraded_semantic",
        }
    ]
    degraded_structural_labels = [
        str(group.get("label", "group")).strip() or "group"
        for group in groups_payload
        if str(group.get("response_quality_status", "")).strip() in {"degraded_format", "degraded_structural"}
    ]
    degraded_semantic_labels = [
        str(group.get("label", "group")).strip() or "group"
        for group in groups_payload
        if str(group.get("response_quality_status", "")).strip() in _SEMANTIC_DEGRADED_STATUSES
    ]
    return {
        "response_status_counts": dict(status_counts),
        "quality_status_counts": dict(quality_counts),
        "degraded_groups": degraded_labels,
        "degraded_structural_groups": degraded_structural_labels,
        "degraded_semantic_groups": degraded_semantic_labels,
        "degraded_format_groups": degraded_structural_labels,
        "degraded_content_groups": degraded_semantic_labels,
    }


def _group_failure_stage(groups_payload: List[Dict[str, Any]]) -> Optional[str]:
    for group in groups_payload:
        status = str(group.get("response_status", "")).strip()
        if status in {"error", "quality_error"}:
            return str(group.get("response_error_stage", "") or group.get("response_failure_stage") or "").strip() or "group_dispatch"
    return None


def _synthesis_markdown(summary: Dict[str, Any]) -> str:
    canonical = summary.get("canonical_next_fork")
    lines = [
        "# Observe Run Synthesis",
        "",
        f"- observe_id: `{summary.get('observe_id')}`",
        f"- canonical_next_fork: `{canonical or 'none'}`",
        f"- canonical_next_action: {summary.get('run_next_action') or '_none_'}",
        "",
        "## Recommendation Counts",
        "",
    ]
    counts = summary.get("next_fork_counts", {})
    if isinstance(counts, dict) and counts:
        for key, value in sorted(counts.items(), key=lambda item: (-int(item[1]), item[0])):
            lines.append(f"- `{key}`: `{value}`")
    else:
        lines.append("- _No NEXT FORK recommendations detected._")
    lines.extend(["", "## Group Decisions", ""])
    recommendations = summary.get("recommendations", [])
    if isinstance(recommendations, list) and recommendations:
        for item in recommendations:
            if not isinstance(item, dict):
                continue
            label = item.get("label") or "group"
            next_fork = item.get("next_fork") or "none"
            action = item.get("next_action") or "_none_"
            finding_summary = item.get("finding_summary") or "_no finding summary_"
            lines.append(f"- `{label}` -> `{next_fork}` :: {finding_summary} :: {action}")
    else:
        lines.append("- _No group decisions recorded._")
    return "\n".join(lines).rstrip() + "\n"


def _summarize_group_finding(response_body: str) -> Optional[str]:
    text = str(response_body or "").strip()
    if not text:
        return None
    # Prefer the first non-heading content line from the first section.
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("NEXT_ACTION:"):
            continue
        if re.fullmatch(r"(stop|next_observe|synthesis|patch|validate|review)", stripped, re.IGNORECASE):
            continue
        return re.sub(r"\s+", " ", stripped).strip()[:220]
    return None


def _synthesize_group_results(
    *,
    repo_root: Path,
    observe_id: str,
    dump_dir: Optional[str],
    groups_payload: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if not dump_dir:
        return {"created": False}
    if not any(str(group.get("response_file", "")).strip() for group in groups_payload):
        return {"created": False}
    dump_path = (repo_root / dump_dir).resolve()
    if not dump_path.exists():
        return {"created": False}
    recommendations: List[Dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for group in groups_payload:
        raw_next_fork = group.get("next_fork")
        next_fork = None
        if raw_next_fork not in {None, ""}:
            next_fork = str(raw_next_fork).strip().lower() or None
        if not next_fork:
            next_fork = _extract_next_fork_kind(str(group.get("response_body", "") or ""))
        next_action = str(group.get("next_action", "")).strip() or None
        label = str(group.get("label", "group")).strip() or "group"
        status = str(group.get("response_status", "")).strip() or "not_run"
        quality_status = str(group.get("response_quality_status", "")).strip() or "unknown"
        finding_summary = _summarize_group_finding(str(group.get("response_body", "") or ""))
        recommendations.append(
            {
                "label": label,
                "next_fork": next_fork or None,
                "next_action": next_action,
                "finding_summary": finding_summary,
                "response_status": status,
                "response_quality_status": quality_status,
            }
        )
        if status == "success" and quality_status not in _SEMANTIC_DEGRADED_STATUSES and next_fork:
            counts[next_fork] += 1
    canonical = None
    if counts:
        canonical = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    if canonical == "next_observe":
        run_next_action = (
            "On continue, read the typed result note first, write the assimilation note, refresh the owning reference note "
            "and active observe seed, then compile the next bounded observe pass."
        )
    elif canonical:
        run_next_action = (
            f"On continue, read the typed result note first, write the assimilation note, refresh the owning reference note "
            f"and active observe seed, then execute the synthesized `{canonical}` path."
        )
    else:
        run_next_action = (
            "On continue, read the typed result note first, inspect the synthesis artifact, write the assimilation note, "
            "refresh the owning reference note and active observe seed, then choose the next bounded pass."
        )
    summary: Dict[str, Any] = {
        "created": True,
        "observe_id": observe_id,
        "canonical_next_fork": canonical,
        "next_fork_counts": dict(counts),
        "recommendations": recommendations,
        "run_next_action": run_next_action,
    }
    synthesis_name = f"00_{_slugify_label(observe_id)}_synthesis.md"
    synthesis_path = dump_path / synthesis_name
    synthesis_path.write_text(_synthesis_markdown(summary), encoding="utf-8")
    summary["path"] = str(synthesis_path.relative_to(repo_root))
    return summary


def _build_routing_markdown(
    *,
    result_note_path: str,
    route_config: Dict[str, Any],
    promotion_summary: Dict[str, Any],
    reference_maps: List[Dict[str, Any]],
) -> str:
    lines = [
        f"- result_note_path: `{result_note_path}`",
        f"- reference_map_count: `{len(reference_maps)}`",
        f"- promotion_target_path: `{promotion_summary.get('target_path') or 'none'}`",
        f"- promotion_target_kind: `{promotion_summary.get('target_kind') or 'none'}`",
        f"- promotion_mode: `{promotion_summary.get('mode') or 'none'}`",
        f"- promotion_section: `{promotion_summary.get('section') or 'none'}`",
        f"- promotion_gate: `{promotion_summary.get('gate') or route_config.get('promotion_gate')}`",
        f"- promotion_status: `{promotion_summary.get('status')}`",
    ]
    if reference_maps:
        lines.append("- reference_maps:")
        for entry in reference_maps:
            detail_parts = []
            if entry.get("id"):
                detail_parts.append(f"id `{entry['id']}`")
            if entry.get("boundary"):
                detail_parts.append(f"boundary `{entry['boundary']}`")
            if entry.get("resolution") and entry.get("reference") != entry.get("path"):
                detail_parts.append(f"via `{entry['reference']}`")
            details = f" ({'; '.join(detail_parts)})" if detail_parts else ""
            lines.append(f"  - `{entry.get('path')}`{details}")
    else:
        lines.append("- reference_maps: `none`")
    error_text = str(promotion_summary.get("error", "") or "").strip()
    if error_text:
        lines.append(f"- promotion_error: `{error_text}`")
    return "\n".join(lines)


def _build_result_note_frontmatter(
    *,
    repo_root: Path,
    observe_id: str,
    generated_at: str,
    plan_path: Path,
    history_entry_rel: str,
    dump_dir: Optional[str],
    groups_payload: List[Dict[str, Any]],
    route_config: Dict[str, Any],
    reference_maps: List[Dict[str, Any]],
    output_status: str,
    bridge_enabled: bool,
    launch_metadata: Dict[str, Any],
    synthesis_summary: Dict[str, Any],
    group_quality_summary: Dict[str, Any],
) -> Dict[str, Any]:
    frontmatter = dict(route_config.get("result_note_frontmatter", {}))
    frontmatter.update(
        {
            "id": observe_id,
            "kind": route_config["result_note_kind"],
            "observe_id": observe_id,
            "generated_at": generated_at,
            "source_plan": format_repo_path(plan_path, repo_root),
            "source_history_entry": history_entry_rel,
            "dump_dir": dump_dir,
            "group_order": [str(group.get("label", "")).strip() for group in groups_payload if str(group.get("label", "")).strip()],
            "bridge_enabled": bridge_enabled,
            "output_status": output_status,
            "bridge_provider_requested": launch_metadata.get("bridge_provider_requested"),
            "bridge_provider_used": launch_metadata.get("bridge_provider_used"),
            "preflight_status": launch_metadata.get("preflight_status"),
            "preflight_ran": launch_metadata.get("preflight_ran"),
            "reference_maps": [str(entry.get("path")) for entry in reference_maps if str(entry.get("path") or "").strip()],
            "promotion_target": route_config.get("promotion_target_path"),
            "promotion_mode": route_config.get("promotion_mode"),
            "promotion_gate": route_config.get("promotion_gate"),
            "group_quality_summary": group_quality_summary,
            "synthesis_artifact": synthesis_summary.get("path"),
        }
    )
    return frontmatter


def _build_result_note_text(
    *,
    repo_root: Path,
    observe_id: str,
    generated_at: str,
    plan: Dict[str, Any],
    plan_path: Path,
    history_entry_rel: str,
    dump_dir: Optional[str],
    groups_payload: List[Dict[str, Any]],
    route_config: Dict[str, Any],
    reference_maps: List[Dict[str, Any]],
    group_outputs_markdown: str,
    promotion_summary: Dict[str, Any],
    bridge_enabled: bool,
    launch_metadata: Dict[str, Any],
    synthesis_summary: Dict[str, Any],
    group_quality_summary: Dict[str, Any],
    run_next_action: str,
) -> str:
    output_status = "bridge_responses" if any(str(group.get("response_file", "")).strip() for group in groups_payload) else "dump_refs_only"
    frontmatter = _build_result_note_frontmatter(
        repo_root=repo_root,
        observe_id=observe_id,
        generated_at=generated_at,
        plan_path=plan_path,
        history_entry_rel=history_entry_rel,
        dump_dir=dump_dir,
        groups_payload=groups_payload,
        route_config=route_config,
        reference_maps=reference_maps,
        output_status=output_status,
        bridge_enabled=bridge_enabled,
        launch_metadata=launch_metadata,
        synthesis_summary=synthesis_summary,
        group_quality_summary=group_quality_summary,
    )
    promotion_payload_lines = [
        f"- canonical_next_fork: `{synthesis_summary.get('canonical_next_fork') or 'none'}`",
        f"- run_next_action: {run_next_action or '_none_'}",
    ]
    degraded_groups = group_quality_summary.get("degraded_groups", [])
    if isinstance(degraded_groups, list) and degraded_groups:
        promotion_payload_lines.append(
            f"- degraded_groups: `{', '.join(str(item) for item in degraded_groups)}`"
        )
    recommendations = synthesis_summary.get("recommendations", [])
    if isinstance(recommendations, list) and recommendations:
        promotion_payload_lines.append("- recommendation_index:")
        for item in recommendations:
            if not isinstance(item, dict):
                continue
            label = item.get("label") or "group"
            next_fork = item.get("next_fork") or "none"
            promotion_payload_lines.append(f"  - `{label}` -> `{next_fork}`")
    promotion_payload_markdown = "\n".join(promotion_payload_lines)
    sections = [
        "# Observe Result Artifact",
        "",
        f"- observe_id: `{observe_id}`",
        f"- generated_at: `{generated_at}`",
        f"- source_plan: `{format_repo_path(plan_path, repo_root)}`",
        f"- source_history_entry: `{history_entry_rel}`",
        f"- launch_command: `{launch_metadata.get('launch_command') or 'internal'}`",
        f"- bridge_provider_requested: `{launch_metadata.get('bridge_provider_requested') or 'default'}`",
        f"- bridge_provider_used: `{launch_metadata.get('bridge_provider_used') or 'none'}`",
        f"- preflight_status: `{launch_metadata.get('preflight_status') or 'not_run'}`",
        "",
    ]
    if route_config["embed_original_plan"]:
        sections.extend(
            [
                "## Original Plan",
                "",
                _json_fence(plan),
                "",
            ]
        )
    # --- Inline actual synthesis and combined content from dump dir ---
    inline_synthesis = ""
    inline_combined = ""
    if dump_dir:
        dump_path = (repo_root / dump_dir).resolve()
        synthesis_file = dump_path / "_synthesis.md"
        combined_file = dump_path / "_combined.md"
        if synthesis_file.exists():
            try:
                inline_synthesis = synthesis_file.read_text(encoding="utf-8").strip()
            except Exception:
                inline_synthesis = ""
        if combined_file.exists():
            try:
                inline_combined = combined_file.read_text(encoding="utf-8").strip()
            except Exception:
                inline_combined = ""

    sections.extend(
        [
            "## Group Outputs",
            "",
            group_outputs_markdown,
            "",
        ]
    )
    if inline_synthesis:
        sections.extend(
            [
                "## Synthesis",
                "",
                inline_synthesis,
                "",
            ]
        )
    if inline_combined:
        sections.extend(
            [
                "## Combined probe output",
                "",
                inline_combined,
                "",
            ]
        )
    sections.extend(
        [
            "## Promotion Payload",
            "",
            promotion_payload_markdown,
            "",
            "## Routing",
            "",
            _build_routing_markdown(
                result_note_path=str(route_config["result_note_path"]),
                route_config=route_config,
                promotion_summary=promotion_summary,
                reference_maps=reference_maps,
            ),
            "",
        ]
    )
    body = "\n".join(sections).rstrip() + "\n"
    return render_markdown_document(frontmatter, body)


def _execute_promotion(
    *,
    repo_root: Path,
    observe_id: str,
    generated_at: str,
    result_note_rel: str,
    route_config: Dict[str, Any],
    promotion_payload: str,
) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "declared": bool(route_config.get("promotion_target_path") and route_config.get("promotion_mode")),
        "target_path": route_config.get("promotion_target_path"),
        "mode": route_config.get("promotion_mode"),
        "section": route_config.get("promotion_section"),
        "target_kind": None,
        "gate": route_config.get("promotion_gate"),
        "status": "not_requested",
        "error": None,
        "source_artifact": result_note_rel,
    }
    if not summary["declared"]:
        return summary
    if summary["gate"] != "auto":
        summary["status"] = "manual_pending"
        return summary

    target_rel = str(summary["target_path"])
    target_path = (repo_root / target_rel).resolve()
    payload_markdown = promotion_payload.strip()
    try:
        if summary["mode"] == "create_note":
            if target_path.exists():
                summary["status"] = "target_exists"
                summary["error"] = f"Target already exists: {target_rel}"
                return summary
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(
                create_note_from_payload(
                    observe_id=observe_id,
                    source_artifact=result_note_rel,
                    generated_at=generated_at,
                    payload_markdown=payload_markdown,
                ),
                encoding="utf-8",
            )
            summary["status"] = "applied"
            return summary

        if not target_path.exists():
            summary["status"] = "missing_target"
            summary["error"] = f"Target not found: {target_rel}"
            return summary

        existing = target_path.read_text(encoding="utf-8")
        target_kind = markdown_kind(existing) or ""
        summary["target_kind"] = target_kind or None
        if summary["mode"] == "reference_artifact":
            artifact = extract_observe_artifact_payload(
                source_text=(repo_root / result_note_rel).read_text(encoding="utf-8"),
                source_artifact=result_note_rel,
            )
            new_text, promotion_state = apply_reference_to_text(
                existing_text=existing,
                target_kind=target_kind,
                target_path=target_rel,
                source_key=str(artifact.get("source_key") or result_note_rel),
                source_artifact=result_note_rel,
                observe_id=str(artifact.get("observe_id") or observe_id),
                generated_at=str(artifact.get("generated_at") or generated_at),
                payload_markdown=str(artifact.get("payload_markdown") or payload_markdown),
                section_title=summary.get("section"),
                summary=artifact.get("summary"),
            )
        else:
            new_text, promotion_state = apply_promotion_to_text(
                existing_text=existing,
                mode=str(summary["mode"]),
                observe_id=observe_id,
                source_artifact=result_note_rel,
                generated_at=generated_at,
                payload_markdown=payload_markdown,
                section_title=summary.get("section"),
            )
        summary["status"] = promotion_state
        if promotion_state == "applied":
            target_path.write_text(new_text, encoding="utf-8")
        return summary
    except ValueError as exc:
        summary["status"] = "section_error"
        summary["error"] = str(exc)
        return summary
    except Exception as exc:  # pragma: no cover - defensive runtime protection
        summary["status"] = "error"
        summary["error"] = str(exc)
        return summary


def _load_master_config(repo_root: Path) -> Dict[str, Any]:
    from system.lib.kernel.config import load_master_config_at
    return load_master_config_at(repo_root)


def _default_bridge_timeout_s(repo_root: Path, bridge_route: str | None = None) -> float:
    master_config = _load_master_config(repo_root)
    return bridge_timeout_seconds(
        master_config,
        default=1500.0,
        route_name=bridge_route,
    )


def _resolve_bridge_config(
    repo_root: Path,
    bridge_provider: Optional[str],
    bridge_timeout_s: float,
    bridge_route: str | None = None,
) -> Tuple[Dict[str, Any], str]:
    master_config = _load_master_config(repo_root)
    merged, _route_name = merge_bridge_config_with_route(master_config, explicit_route=bridge_route)
    bridge_cfg = merged.get("bridge", {}) if isinstance(merged, dict) else {}
    if not isinstance(bridge_cfg, dict):
        bridge_cfg = {}
    else:
        bridge_cfg = dict(bridge_cfg)
    if bridge_timeout_s > 0:
        bridge_cfg["monitor_timeout_s"] = float(bridge_timeout_s)

    platform = str(bridge_provider or "").strip()
    if not platform:
        default_target = bridge_cfg.get("default_target")
        if isinstance(default_target, str) and default_target.strip():
            platform = default_target.strip()
    if not platform:
        platform = "chatgpt"

    runtime_config = dict(merged) if isinstance(merged, dict) else {}
    runtime_config["bridge"] = bridge_cfg
    runtime_config["platform"] = platform
    return runtime_config, platform


def _load_bridge_callable(repo_root: Path) -> Callable[[str, Optional[Dict[str, Any]]], str]:
    root_str = str(repo_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    from system.core.bridge import ask_ai  # pylint: disable=import-outside-toplevel
    return ask_ai


_BRIDGE_PROVIDER_ALIASES = {"", "bridge", "chatgpt", "gemini"}


def _is_bridge_provider(provider: Optional[str]) -> bool:
    return str(provider or "").strip().lower() in _BRIDGE_PROVIDER_ALIASES


def _normalize_bridge_provider_token(provider: Optional[str]) -> str:
    return str(provider or "").strip().lower()


def _alternate_bridge_provider(provider: Optional[str]) -> str:
    normalized = _normalize_bridge_provider_token(provider)
    if normalized == "chatgpt":
        return "gemini"
    if normalized == "gemini":
        return "chatgpt"
    return ""


def _bridge_failure_supports_failover(category: Optional[str], stage: Optional[str]) -> bool:
    category_token = str(category or "").strip().lower()
    stage_token = str(stage or "").strip().lower()
    return category_token in {
        "provider_timeout",
        "provider_selector_failure",
        "provider_challenge",
        "provider_unavailable",
    } or stage_token in {
        "provider_wait",
        "provider_open",
        "provider_interaction",
        "provider_import",
    }


def _resolve_group_provider_runtime(
    *,
    repo_root: Path,
    requested_provider: Optional[str],
    default_bridge_callable: Optional[Callable[[str, Optional[Dict[str, Any]]], str]],
    default_bridge_config: Optional[Mapping[str, Any]],
    default_bridge_error: str,
    default_bridge_provider: Optional[str],
    bridge_timeout_s: float,
    provider_config: Optional[Mapping[str, Any]] = None,
) -> Tuple[Optional[Callable[[str, Optional[Dict[str, Any]]], str]], Dict[str, Any], str, str]:
    config = dict(provider_config) if isinstance(provider_config, Mapping) else {}
    requested = str(requested_provider or "").strip()
    normalized = requested.lower()

    def _apply_provider_gate(
        provider_callable: Optional[Callable[[str, Optional[Dict[str, Any]]], str]],
        provider_config_payload: Dict[str, Any],
        resolved_provider: str,
        error_text: str,
    ) -> Tuple[Optional[Callable[[str, Optional[Dict[str, Any]]], str]], Dict[str, Any], str, str]:
        # Provider pressure is enforced by call_with_provider_claim(), which can
        # wait for short cooldowns or existing same-provider claims to clear.
        # Gating here turns queue pressure into immediate group failure before
        # the wait loop can do its job.
        return provider_callable, provider_config_payload, resolved_provider, error_text

    if normalized in ("", "bridge"):
        bridge_config = dict(default_bridge_config) if isinstance(default_bridge_config, Mapping) else {}
        bridge_config.update(config)
        resolved_provider = str(default_bridge_provider or "").strip() or "chatgpt"
        if bridge_timeout_s > 0:
            bridge_config.setdefault("monitor_timeout_s", float(bridge_timeout_s))
        return _apply_provider_gate(
            default_bridge_callable,
            bridge_config,
            resolved_provider,
            default_bridge_error,
        )

    if normalized in ("chatgpt", "gemini"):
        if requested == str(default_bridge_provider or "").strip() and isinstance(default_bridge_config, Mapping):
            merged_config = dict(default_bridge_config)
            resolved_provider = requested
        else:
            bridge_config, resolved_provider = _resolve_bridge_config(
                repo_root=repo_root,
                bridge_provider=requested,
                bridge_timeout_s=bridge_timeout_s,
            )
            merged_config = dict(bridge_config)
        merged_config.update(config)
        return _apply_provider_gate(
            default_bridge_callable,
            merged_config,
            resolved_provider,
            default_bridge_error,
        )

    try:
        provider_callable = resolve_provider_callable(requested, repo_root=repo_root)
    except Exception as exc:
        return None, config, requested or "unknown", str(exc)

    if bridge_timeout_s > 0:
        config.setdefault("timeout_s", max(1, int(round(float(bridge_timeout_s)))))
    if normalized in ("codex", "codex-cli", "codex_cli"):
        config.setdefault("cwd", str(repo_root))
        config.setdefault("writable_root", str(repo_root))

    return _apply_provider_gate(provider_callable, config, requested, "")


def _build_excerpt_envelope(text: str, *, budget: int, head_chars: int, tail_chars: int) -> str:
    head = text[:head_chars]
    tail = text[-tail_chars:] if tail_chars > 0 else ""
    excerpt = {
        "__observe_dump_excerpt__": True,
        "truncated": True,
        "strategy": "head_tail",
        "original_chars": len(text),
        "original_sha256": _text_sha256(text),
        "excerpt_budget_chars": budget,
        "head_chars": len(head),
        "tail_chars": len(tail),
        "head": head,
        "tail": tail,
    }
    return json.dumps(excerpt, ensure_ascii=False, indent=2)


def _minimal_excerpt_envelope(text: str) -> str:
    return json.dumps(
        {
            "__observe_dump_excerpt__": True,
            "truncated": True,
            "strategy": "omitted_for_budget",
            "original_chars": len(text),
            "original_sha256": _text_sha256(text),
        },
        ensure_ascii=False,
        indent=2,
    )


_DEFAULT_PROVIDER_RUNTIME_PROMPT_BUDGETS = {
    "chatgpt": 200_000,
    "gemini": 32_000,
}


def _provider_runtime_prompt_budget(provider: Optional[str]) -> int:
    normalized_provider = _normalize_bridge_provider_token(provider)
    if not normalized_provider:
        return 0
    default_budget = int(_DEFAULT_PROVIDER_RUNTIME_PROMPT_BUDGETS.get(normalized_provider, 0) or 0)
    try:
        provider_record = get_provider(normalized_provider)
    except CapabilityError:
        return default_budget
    raw_budget = provider_record.get("runtime_prompt_budget_chars")
    try:
        resolved_budget = int(raw_budget)
    except (TypeError, ValueError):
        return default_budget
    return resolved_budget if resolved_budget > 0 else default_budget


def _truncate(text: str, max_chars: int) -> Tuple[str, bool]:
    if max_chars <= 0:
        return text, False
    if len(text) <= max_chars:
        return text, False
    budget = max(256, int(max_chars))
    head_budget = max(64, int(budget * 0.6))
    tail_budget = max(32, int(budget * 0.2))
    for _ in range(12):
        excerpt = _build_excerpt_envelope(
            text,
            budget=budget,
            head_chars=head_budget,
            tail_chars=tail_budget,
        )
        if len(excerpt) <= budget:
            return excerpt, True
        overflow = len(excerpt) - budget
        total = max(1, head_budget + tail_budget)
        reduce_head = max(1, int((overflow + 32) * (head_budget / float(total))))
        reduce_tail = max(1, int((overflow + 32) * (tail_budget / float(total))))
        next_head = max(8, head_budget - reduce_head)
        next_tail = max(8, tail_budget - reduce_tail)
        if next_head == head_budget and next_tail == tail_budget:
            break
        head_budget, tail_budget = next_head, next_tail
    return _minimal_excerpt_envelope(text), True


def _resolve_effective_bridge_prompt_budget(
    repo_root: Path,
    max_chars: int,
    provider: Optional[str] = None,
) -> int:
    explicit_budget = max(0, int(max_chars or 0))
    provider_budget = _provider_runtime_prompt_budget(provider)
    if explicit_budget > 0 and provider_budget > 0:
        return min(explicit_budget, provider_budget)
    if explicit_budget > 0:
        return explicit_budget
    budget = resolve_bridge_prompt_budget(repo_root)
    recommended = max(0, int(budget.get("recommended_prompt_chars") or 0))
    hard = max(recommended, int(budget.get("hard_prompt_chars") or 0))
    if provider_budget > 0:
        return provider_budget
    return recommended or hard


def _excerpt_is_omitted_for_budget(text: str) -> bool:
    try:
        payload = json.loads(text)
    except Exception:
        return False
    if not isinstance(payload, Mapping):
        return False
    return bool(payload.get("__observe_dump_excerpt__")) and str(payload.get("strategy") or "").strip() == "omitted_for_budget"


def _fit_probe_prompt_to_budget(
    *,
    repo_root: Path,
    label: str,
    group_prompt: str,
    dump_rel_path: str,
    dump_text: str,
    max_chars: int,
    provider_hint: Optional[str] = None,
    sibling_focuses: Sequence[str] | None = None,
    incoming_queries: Sequence[Mapping[str, Any]] | None = None,
    upstream_artifacts: Sequence[tuple[str, str]] | None = None,
    declared_dependencies: Sequence[str] | None = None,
    output_contract: object = None,
    prompt_metadata: Mapping[str, Any] | None = None,
    response_surface: Mapping[str, Any] | None = None,
    response_schema: Mapping[str, Any] | None = None,
    json_only: bool = False,
    external_research_allowed: bool = False,
) -> tuple[str, bool, str, int]:
    prompt_budget = _resolve_effective_bridge_prompt_budget(repo_root, max_chars, provider_hint)
    sibling_options = [list(sibling_focuses or [])]
    if sibling_focuses:
        sibling_options.append([])

    def _render_prompt(current_dump_excerpt: str, current_truncated: bool, current_siblings: Sequence[str]) -> str:
        return _build_bridge_prompt(
            label=label,
            group_prompt=group_prompt,
            dump_rel_path=dump_rel_path,
            dump_json=current_dump_excerpt,
            truncated=current_truncated,
            max_chars=prompt_budget,
            sibling_focuses=current_siblings,
            incoming_queries=incoming_queries,
            upstream_artifacts=upstream_artifacts,
            declared_dependencies=declared_dependencies,
            output_contract=output_contract,
            prompt_metadata=prompt_metadata,
            response_surface=response_surface,
            response_schema=response_schema,
            json_only=json_only,
            external_research_allowed=external_research_allowed,
        )

    if prompt_budget <= 0:
        dump_excerpt, truncated = _truncate(dump_text, 0)
        bridge_prompt = _render_prompt(dump_excerpt, truncated, sibling_focuses or [])
        return dump_excerpt, truncated, bridge_prompt, prompt_budget
    last_result = ("", True, _render_prompt("", True, []), prompt_budget)
    for current_siblings in sibling_options:
        empty_prompt = _render_prompt("", True, current_siblings)
        available_dump_chars = max(0, prompt_budget - len(empty_prompt) - 64)
        if available_dump_chars > 0:
            attempt_budget = available_dump_chars
            while True:
                dump_excerpt, truncated = _truncate(dump_text, attempt_budget)
                bridge_prompt = _render_prompt(dump_excerpt, truncated, current_siblings)
                last_result = (dump_excerpt, truncated, bridge_prompt, prompt_budget)
                if len(bridge_prompt) <= prompt_budget or attempt_budget <= 256:
                    break
                shrink_ratio = prompt_budget / float(max(len(bridge_prompt), 1))
                next_budget = max(256, int(attempt_budget * shrink_ratio) - 256)
                if next_budget >= attempt_budget:
                    next_budget = max(256, attempt_budget // 2)
                attempt_budget = next_budget
            if len(bridge_prompt) <= prompt_budget:
                return dump_excerpt, truncated, bridge_prompt, prompt_budget
        dump_excerpt = _minimal_excerpt_envelope(dump_text)
        truncated = True
        bridge_prompt = _render_prompt(dump_excerpt, truncated, current_siblings)
        last_result = (dump_excerpt, truncated, bridge_prompt, prompt_budget)
        if len(bridge_prompt) <= prompt_budget:
            return dump_excerpt, truncated, bridge_prompt, prompt_budget
    return last_result


_NEXT_ACTION_RE = re.compile(r"(?im)^NEXT_ACTION:\s*(.+)$")


def _normalize_next_action(value: str) -> str:
    text = _safe_text(value)
    if not text:
        return ""
    if text[-1] not in ".!?":
        text += "."
    return text


def _extract_next_action(response_text: str) -> Optional[str]:
    matches = _NEXT_ACTION_RE.findall(response_text or "")
    if not matches:
        return None
    next_action = _normalize_next_action(matches[-1])
    return next_action or None


def _default_next_action(
    *,
    artifact_rel_path: str,
    label: str,
    role: str,
    status: str,
) -> str:
    if status != "success":
        return _normalize_next_action(
            f"On continue, I will reopen `{artifact_rel_path}` and recover the failed {role} step for `{label}`"
        )
    if role == "evaluation":
        return _normalize_next_action(
            f"On continue, I will read `{artifact_rel_path}` and decide whether this session should iterate once more or move into apply"
        )
    if role == "synthesis":
        return _normalize_next_action(
            f"On continue, I will read `{artifact_rel_path}` and convert the synthesized findings into an implementation-ready apply slice"
        )
    return _normalize_next_action(
        f"On continue, I will read `{artifact_rel_path}` and use it to choose the next synthesis or implementation slice for `{label}`"
    )


def _build_continuation_contract(
    *,
    response_text: str,
    artifact_rel_path: str,
    label: str,
    role: str,
    status: str,
) -> Dict[str, str]:
    next_action = _extract_next_action(response_text)
    source = "model"
    if not next_action:
        next_action = _default_next_action(
            artifact_rel_path=artifact_rel_path,
            label=label,
            role=role,
            status=status,
        )
        source = "fallback"
    hint = _normalize_next_action(
        f"On continue, read `{artifact_rel_path}` first. {next_action}"
    )
    return {
        "next_action": next_action,
        "hint": hint,
        "source": source,
    }


def _build_bridge_prompt(
    *,
    label: str,
    group_prompt: str,
    dump_rel_path: str,
    dump_json: str,
    truncated: bool,
    max_chars: int,
    sibling_focuses: Sequence[str] | None = None,
    incoming_queries: Sequence[Mapping[str, Any]] | None = None,
    upstream_artifacts: Sequence[tuple[str, str]] | None = None,
    declared_dependencies: Sequence[str] | None = None,
    output_contract: object = None,
    prompt_metadata: Mapping[str, Any] | None = None,
    response_surface: Mapping[str, Any] | None = None,
    response_schema: Mapping[str, Any] | None = None,
    json_only: bool = False,
    external_research_allowed: bool = False,
) -> str:
    if max_chars <= 0:
        truncation_line = "Observe dump content is complete (no prompt-size truncation)."
    else:
        truncation_line = (
            f"Observe dump content was replaced with a valid JSON excerpt envelope capped at {max_chars} chars due to prompt budget."
            if truncated
            else "Observe dump content is complete."
        )
    response_mode = _resolve_response_mode(prompt_metadata)
    output_shape_lines = ["[OUTPUT_SHAPE]"]
    explicit_sections = _resolve_output_contract(group_prompt, output_contract)
    if json_only and response_schema:
        output_shape_lines.extend(
            [
                "Return ONLY a valid JSON value matching this schema.",
                "Do not wrap it in markdown fences or add any surrounding prose.",
                "Do not add NEXT_ACTION or any extra commentary.",
                "",
                "CRITICAL JSON RULES:",
                "- Use ONLY the exact property names shown in the schema (snake_case).",
                "- All string values must be plain human-readable text.",
                "- NEVER embed raw source code, Python expressions, or dict literals inside JSON string values.",
                "- For code evidence, describe what the code does in plain English instead of quoting it verbatim.",
                "- Keep string values short (under 200 characters each).",
                "",
                "```json",
                json.dumps(response_schema, indent=2, ensure_ascii=False),
                "```",
            ]
        )
    elif response_surface:
        surface_kind = str(response_surface.get("surface_kind") or "fill_form_v1").strip() or "fill_form_v1"
        response_kind = str(response_surface.get("response_kind") or "observe_group_sections").strip() or "observe_group_sections"
        output_shape_lines.extend(
            [
                "The model-authored layer for this group is a bounded response surface.",
                "Return the exact sentinel blocks below and nothing outside them.",
                "The runtime will project the stored markdown response note, continuation contract, and any sidecar artifacts.",
                f"- surface_kind: `{surface_kind}`",
                f"- response_kind: `{response_kind}`",
                "```text",
                render_response_surface_template(response_surface),
                "```",
            ]
        )
    elif response_mode == "epistemic_tags":
        required_tags = ", ".join(f"[{tag}]" for tag in _coerce_required_epistemic_tags(prompt_metadata))
        closing_section = _epistemic_closing_section(prompt_metadata)
        output_shape_lines.extend(
            [
                "Use headings that fit what you actually found rather than forcing a rigid fixed template.",
                f"Required epistemic tags: {required_tags}",
                f"Your closing block MUST be headed `## {closing_section}` and contain 3-5 leverage-ordered questions.",
                "Keep facts distinct from inferences and tensions; never smuggle uncertainty into confident prose.",
                "NEXT_ACTION: On continue, I will read `<stored-artifact-path>` next.",
            ]
        )
    elif explicit_sections:
        output_shape_lines.extend(
            [
                "Your response MUST match this exact markdown skeleton:",
                "",
            ]
        )
        for name in explicit_sections:
            output_shape_lines.append(f"## {name}")
            if name == "SURFACED QUESTIONS":
                output_shape_lines.extend(
                    [
                        "### USER DECISIONS",
                        "- [DECISION|QUESTION|RISK|ASSUMPTION] item with citation",
                        "",
                        "### AGENT FOLLOWUPS",
                        "- [DECISION|QUESTION|RISK|ASSUMPTION] item with citation",
                    ]
                )
            elif name == "NEXT FORK":
                output_shape_lines.append("stop|next_observe|synthesis|patch|validate|review")
            elif name == "TARGET DELTAS":
                output_shape_lines.append("- KEEP|ADD|REWRITE|DELETE target -> 1-3 sentence sketch")
            else:
                output_shape_lines.append("- tagged item with citation")
            output_shape_lines.append("")
        output_shape_lines.append("NEXT_ACTION: On continue, I will read `<stored-artifact-path>` next.")
    else:
        output_shape_lines.extend(
            [
                "Follow section order and detail level from [PROMPT_INSTRUCTION] exactly.",
                "If [PROMPT_INSTRUCTION] has no explicit section order, use:",
                "1) Confirmed Facts",
                "2) Inferred Contracts",
                "3) Contradictions and Tensions",
                "4) Unknowns",
                "5) Next-Probe Questions",
            ]
        )
    sibling_lines: List[str] = []
    roster = [str(item).strip() for item in (sibling_focuses or []) if str(item).strip()]
    if roster:
        sibling_lines = [
            "[GROUP_FAMILY_CONTEXT]",
            "You are one jigsaw piece of a larger grouped observe pass.",
            "Other groups are reading different slices in parallel; use this compact roster only to avoid duplication and to phrase clean handoffs.",
            "Do not claim evidence from those groups and do not attempt cross-group synthesis here.",
        ]
        sibling_lines.extend(f"- {item}" for item in roster)
        sibling_lines.append("")
    incoming_query_lines: List[str] = []
    normalized_queries = [
        dict(item)
        for item in (incoming_queries or [])
        if isinstance(item, Mapping)
    ]
    if normalized_queries:
        incoming_query_lines = [
            "[INCOMING_QUERIES]",
            "Sibling groups surfaced these targeted follow-up questions for this slice.",
            "Answer them only if the attached evidence supports it; otherwise carry the insufficiency forward explicitly.",
        ]
        for item in normalized_queries:
            source_label = str(item.get("source_label") or "").strip()
            question = str(item.get("question") or "").strip()
            rationale = str(item.get("rationale") or "").strip()
            if not question:
                continue
            prefix = f"{source_label}: " if source_label else ""
            line = f"- {prefix}{question}"
            if rationale:
                line += f" ({rationale})"
            incoming_query_lines.append(line)
        incoming_query_lines.append("")
    upstream_lines: List[str] = []
    upstream_parts = [
        f"--- START UPSTREAM: {rel_path} ---\n{text}\n--- END UPSTREAM: {rel_path} ---\n"
        for rel_path, text in (upstream_artifacts or [])
    ]
    declared_labels = [str(item).strip() for item in (declared_dependencies or []) if str(item).strip()]
    if upstream_parts:
        upstream_lines = ["[UPSTREAM_CHUNK_CONTEXT]", *upstream_parts]
    elif declared_labels:
        upstream_lines = [
            "[WARNING: Declared upstream chunk responses were not found. Use the current dump JSON as primary evidence.]",
            "",
        ]
    external_research_lines: list[str] = []
    if external_research_allowed:
        external_research_lines = [
            "External research is allowed for this group. You may actively search online/provider-accessible sources, open URLs, query search engines, and read external documentation.",
            "Return cited findings with replayable evidence URLs. Do not install, download, clone, import, or claim adoption.",
            "",
        ]
    lines = [
        "You are producing a grouped observe report from a single observe dump JSON.",
        *(
            external_research_lines
            if external_research_allowed
            else [
                "Use only evidence inside this prompt. Do not assume access to repo files, paths, or artifacts that are not pasted below.",
            ]
        ),
        "This call is bounded to the current dump plus any explicitly attached upstream chunk context. Do not attempt global synthesis here.",
        "The [PROMPT_INSTRUCTION] block is the primary contract and overrides any generic defaults below.",
        (
            "Start immediately with the JSON object. Do not add setup text, worklog text, or task restatement before it."
            if json_only and response_schema
            else "Start immediately with the first response-surface block. Do not add setup text, worklog text, or task restatement before it."
            if response_surface
            else "Start immediately with the first required section heading. Do not add setup text, worklog text, or task restatement before it."
        ),
        (
            "Use the exact JSON shape required by the schema."
            if json_only and response_schema
            else "Use the exact sentinel response-surface blocks in the required order."
            if response_surface
            else (
                "Use the exact required section headings on their own lines in the required order."
                if response_mode != "epistemic_tags"
                else "Use headings that match the material, but keep the required epistemic tags and closing question block intact."
            )
        ),
        "Cite non-trivial claims with file path plus symbol, section, or exact quoted anchor only when that evidence is present in this prompt.",
        (
            "Do not invent claims, routes, files, or doctrine targets that are not evidenced in this prompt. Use empty arrays or empty strings when the schema allows them rather than filling unknown fields with fabricated content."
            if json_only and response_schema
            else "Do not propose fixes. Separate facts, inferences, contradictions/tensions, and unknowns. Do not repeat sections."
        ),
        "Do not emit meta commentary such as `Defining the Task`, `Clarifying ...`, `Refining ...`, `I now understand`, or `Gemini said`.",
        (
            "Keep all content inside the JSON object only."
            if json_only and response_schema
            else
            "Keep the authored payload inside the response surface only; the runtime owns markdown projection and NEXT_ACTION."
            if response_surface
            else "End with 3-7 risk-ordered next-probe questions."
        ),
        (
            "Do not author NEXT_ACTION."
            if json_only and response_schema
            else
            "Do not author NEXT_ACTION inside the response surface."
            if response_surface
            else "End the final line exactly as `NEXT_ACTION: On continue, I will ...` and make it specific to the stored artifact that should be read next."
        ),
        "",
        f"[GROUP_LABEL]\n{label}",
        "",
        f"[PROMPT_INSTRUCTION]\n{group_prompt}",
        "",
        *sibling_lines,
        *incoming_query_lines,
        *upstream_lines,
        f"[DUMP_BUDGET]\n{truncation_line}",
        "",
        *output_shape_lines,
        "",
        "[OBSERVE_DUMP_JSON]",
        dump_json,
    ]
    return "\n".join(lines)


def _build_join_bridge_prompt(
    *,
    label: str,
    role: str,
    group_prompt: str,
    dump_rel_path: str,
    dump_json: str,
    truncated: bool,
    max_chars: int,
    upstream_artifacts: Sequence[tuple[str, str]] | None = None,
    declared_dependencies: Sequence[str] | None = None,
    response_schema: Mapping[str, Any] | None = None,
    json_only: bool = False,
) -> str:
    if max_chars <= 0:
        truncation_line = "Observe dump content is complete (no prompt-size truncation)."
    else:
        truncation_line = (
            f"Observe dump content was replaced with a valid JSON excerpt envelope capped at {max_chars} chars due to prompt budget."
            if truncated
            else "Observe dump content is complete."
        )

    join_output_lines = ["[OUTPUT_SHAPE]"]
    if json_only and response_schema:
        join_output_lines.extend(
            [
                "Return ONLY a valid JSON value matching this schema.",
                "Do not wrap it in markdown fences or add any surrounding prose.",
                "Do not add NEXT_ACTION or any extra commentary.",
                "",
                "CRITICAL JSON RULES:",
                "- Use ONLY the exact property names shown in the schema (snake_case).",
                "- All string values must be plain human-readable text.",
                "- NEVER embed raw source code, Python expressions, or dict literals inside JSON string values.",
                "- For code evidence, describe what the code does in plain English instead of quoting it verbatim.",
                "- Keep string values short (under 200 characters each).",
                "",
                "```json",
                json.dumps(response_schema, indent=2, ensure_ascii=False),
                "```",
            ]
        )
    else:
        join_output_lines.extend(
            [
                "Follow the instruction block exactly.",
                "If no explicit section order is provided, use:",
                "1) Confirmed Facts",
                "2) Inferred Contracts",
                "3) Contradictions and Tensions",
                "4) Unknowns",
                "5) Next-Probe Questions",
                "End the final line exactly as `NEXT_ACTION: On continue, I will ...` and make it specific.",
            ]
        )

    upstream_parts: list[str] = []
    for rel_path, text in (upstream_artifacts or []):
        upstream_parts.append(f"--- START UPSTREAM: {rel_path} ---\n{text}\n--- END UPSTREAM: {rel_path} ---\n")

    role_label = str(role or "synthesis").strip() or "synthesis"
    declared_labels = [str(item).strip() for item in (declared_dependencies or []) if str(item).strip()]
    lines = [
        f"You are a meta-observe join node ({role_label}).",
        "Use the current-node observe dump JSON as the primary evidence surface for this node.",
        "Use upstream probe response artifacts only when they are attached below.",
        "Ground every non-trivial claim in file paths, code symbols, or exact quoted anchors only when that evidence is present in this prompt.",
        (
            "Start immediately with the JSON object. Do not add setup text, worklog text, or task restatement before it."
            if json_only and response_schema
            else "Start immediately with the first required section heading. Do not add setup text, worklog text, or task restatement before it."
        ),
        (
            "Use the exact JSON shape required by the schema."
            if json_only and response_schema
            else "Follow the exact section order required by the instruction block."
        ),
        (
            "Keep all content inside the JSON object only."
            if json_only and response_schema
            else "End with 3-7 risk-ordered next-probe questions."
        ),
        (
            "Do not author NEXT_ACTION."
            if json_only and response_schema
            else "End the final line exactly as `NEXT_ACTION: On continue, I will ...` and make it specific to the stored artifact that should be read next."
        ),
        "",
        f"[GROUP_LABEL]\n{label}",
        "",
        f"[PROMPT_INSTRUCTION]\n{group_prompt}",
        "",
        *join_output_lines,
        "",
    ]
    if upstream_parts:
        lines.extend(["[UPSTREAM_PROBE_ARTIFACTS]", *upstream_parts])
    elif declared_labels:
        lines.extend(
            [
                "[WARNING: Declared upstream probe responses were not found. Use the current-node observe dump JSON and injected context below as primary evidence.]",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "[INFO: No in-session upstream probe responses are attached for this node. Use the current-node observe dump JSON and injected context below as primary evidence.]",
                "",
            ]
        )
    lines.extend(
        [
            f"[DUMP_BUDGET]\n{truncation_line}",
            "",
            "[OBSERVE_DUMP_JSON]",
            dump_json,
        ]
    )
    return "\n".join(lines)


def _prompt_text_excerpt(value: Any, *, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if limit <= 0 or len(text) <= limit:
        return text
    if limit <= 24:
        return text[:limit].rstrip()
    head = max(16, limit - 12)
    return text[:head].rstrip() + " ..."


def _compact_prompt_value(
    value: Any,
    *,
    string_limit: int,
    list_limit: int,
    max_depth: int,
    depth: int = 0,
) -> Any:
    if depth >= max_depth:
        if isinstance(value, (Mapping, list)):
            rendered = json.dumps(value, ensure_ascii=False)
            return _prompt_text_excerpt(rendered, limit=string_limit)
        if isinstance(value, str):
            return _prompt_text_excerpt(value, limit=string_limit)
        return value

    if isinstance(value, Mapping):
        compacted: Dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key).strip()
            if not key_text:
                continue
            if key_text in {"projected_markdown", "prompt_used", "bridge_prompt"}:
                continue
            compacted[key_text] = _compact_prompt_value(
                item,
                string_limit=max(64, string_limit - 24),
                list_limit=max(2, list_limit - 1),
                max_depth=max_depth,
                depth=depth + 1,
            )
        return compacted

    if isinstance(value, list):
        items: List[Any] = []
        limit = max(1, list_limit)
        for item in value[:limit]:
            items.append(
                _compact_prompt_value(
                    item,
                    string_limit=max(64, string_limit - 24),
                    list_limit=max(2, list_limit - 1),
                    max_depth=max_depth,
                    depth=depth + 1,
                )
            )
        hidden_count = len(value) - len(items)
        if hidden_count > 0:
            items.append({"__truncated_items__": hidden_count})
        return items

    if isinstance(value, str):
        return _prompt_text_excerpt(value, limit=string_limit)

    return value


def _serialize_compact_prompt_payload(
    payload: Mapping[str, Any],
    *,
    max_chars: int,
) -> str:
    if max_chars <= 0:
        return json.dumps(dict(payload), ensure_ascii=False, indent=2)

    profiles = (
        (320, 8, 5),
        (240, 6, 4),
        (180, 5, 4),
        (140, 4, 3),
        (100, 3, 2),
    )
    for string_limit, list_limit, max_depth in profiles:
        compacted = _compact_prompt_value(
            payload,
            string_limit=string_limit,
            list_limit=list_limit,
            max_depth=max_depth,
        )
        text = json.dumps(compacted, ensure_ascii=False, indent=2)
        if len(text) <= max_chars:
            return text

    fallback = json.dumps(
        _compact_prompt_value(payload, string_limit=72, list_limit=2, max_depth=2),
        ensure_ascii=False,
        indent=2,
    )
    truncated, _did_truncate = _truncate(fallback, max_chars)
    return truncated


def _load_join_artifact_text(
    *,
    repo_root: Path,
    group: Mapping[str, Any],
    budget: int,
) -> tuple[str, str] | None:
    label = str(group.get("label") or "group").strip() or "group"
    response_file = str(group.get("response_file") or "").strip() or None
    receipt_rel = str(group.get("response_receipt_file") or "").strip()
    if receipt_rel:
        receipt_path = (repo_root / receipt_rel).resolve()
        if receipt_path.exists():
            payload = _read_json(receipt_path)
            payload_body = payload.get("payload") if isinstance(payload.get("payload"), Mapping) else {}
            schema_payload = payload.get("response_schema") if isinstance(payload.get("response_schema"), Mapping) else {}
            artifact = {
                "artifact_kind": "typed_receipt",
                "group_label": label,
                "response_file": response_file,
                "response_schema_id": str(schema_payload.get("schema_id") or "").strip() or None,
                "payload": payload_body,
            }
            return receipt_rel, _serialize_compact_prompt_payload(artifact, max_chars=budget)

    surface_rel = str(group.get("response_surface_file") or "").strip()
    if surface_rel:
        surface_path = (repo_root / surface_rel).resolve()
        if surface_path.exists():
            payload = _read_json(surface_path)
            surface_payload = payload.get("payload") if isinstance(payload.get("payload"), Mapping) else {}
            artifact = {
                "artifact_kind": "response_surface",
                "group_label": label,
                "response_file": response_file,
                "surface_kind": str(payload.get("surface_kind") or "").strip() or None,
                "response_kind": str(payload.get("response_kind") or "").strip() or None,
                "payload": surface_payload,
            }
            return surface_rel, _serialize_compact_prompt_payload(artifact, max_chars=budget)

    if response_file:
        response_path = (repo_root / response_file).resolve()
        if response_path.exists():
            response_text = response_path.read_text(encoding="utf-8")
            response_marker = "\n## Response\n"
            if response_marker in response_text:
                response_text = response_text[response_text.index(response_marker) + len(response_marker):]
            response_text, _ = _truncate(response_text, budget) if budget > 0 else (response_text, False)
            return response_file, response_text

    return None


def _resolve_join_prompt_budgets(
    *,
    label: str,
    role: str,
    group_prompt: str,
    dump_rel_path: str,
    max_chars: int,
    declared_dependencies: Sequence[str],
    response_schema: Mapping[str, Any] | None,
    json_only: bool,
) -> dict[str, int]:
    if max_chars <= 0:
        return {
            "available_budget": 0,
            "dump_budget": 0,
            "upstream_total_budget": 0,
            "per_dependency_budget": 0,
        }

    placeholder_upstreams = [
        (f"{dep}.artifact", "<UPSTREAM_ARTIFACT>")
        for dep in declared_dependencies
    ]
    placeholder_prompt = _build_join_bridge_prompt(
        label=label,
        role=role,
        group_prompt=group_prompt,
        dump_rel_path=dump_rel_path,
        dump_json="<OBSERVE_DUMP_JSON>",
        truncated=False,
        max_chars=max_chars,
        upstream_artifacts=placeholder_upstreams,
        declared_dependencies=declared_dependencies,
        response_schema=response_schema,
        json_only=json_only,
    )
    placeholder_chars = len("<OBSERVE_DUMP_JSON>") + len(placeholder_upstreams) * len("<UPSTREAM_ARTIFACT>")
    overhead = max(0, len(placeholder_prompt) - placeholder_chars)
    available = max(2048, max_chars - overhead - 512)
    if placeholder_upstreams:
        upstream_total = max(2048, int(available * 0.45))
        dump_budget = max(2048, available - upstream_total)
        per_dependency = max(1200, int(upstream_total / max(1, len(placeholder_upstreams))))
    else:
        upstream_total = 0
        dump_budget = available
        per_dependency = 0
    return {
        "available_budget": available,
        "dump_budget": dump_budget,
        "upstream_total_budget": upstream_total,
        "per_dependency_budget": per_dependency,
    }


def _build_response_markdown(
    *,
    observe_id: str,
    group_label: str,
    dump_file: str,
    prompt_used: str,
    bridge_provider: str,
    bridge_prompt_chars: int,
    dump_truncated: bool,
    status: str,
    response_text: str,
    error_text: str,
    error_category: str,
    error_stage: str,
    quality_status: str,
    response_surface_kind: str = "",
    response_kind: str = "",
    response_surface_file: str = "",
    response_receipt_file: str = "",
    bridge_dispatch_file: str = "",
    quality_issues: List[str] | None = None,
    quality_detected_issues: List[str] | None = None,
    quality_repair_actions: List[str] | None = None,
    next_action: str = "",
    continuation_source: str = "",
) -> str:
    quality_issues = quality_issues or []
    quality_detected_issues = quality_detected_issues or []
    quality_repair_actions = quality_repair_actions or []
    lines = [
        "# Observe Group Response",
        "",
        f"- observe_id: `{observe_id}`",
        f"- group_label: `{group_label}`",
        f"- dump_file: `{dump_file}`",
        f"- generated_at: `{_now_iso()}`",
        f"- bridge_provider: `{bridge_provider}`",
        f"- bridge_prompt_chars: `{bridge_prompt_chars}`",
        f"- dump_truncated: `{str(dump_truncated).lower()}`",
        f"- status: `{status}`",
        f"- error_category: `{error_category or 'none'}`",
        f"- error_stage: `{error_stage or 'none'}`",
        f"- quality_status: `{quality_status or 'unknown'}`",
        f"- response_surface_kind: `{response_surface_kind or 'none'}`",
        f"- response_kind: `{response_kind or 'none'}`",
        f"- response_surface_file: `{response_surface_file or 'none'}`",
        f"- response_receipt_file: `{response_receipt_file or 'none'}`",
        f"- bridge_dispatch_file: `{bridge_dispatch_file or 'none'}`",
        f"- continuation_source: `{continuation_source}`",
        "",
        "## Prompt",
        "",
        prompt_used.strip(),
        "",
    ]
    if quality_issues or quality_detected_issues or quality_repair_actions:
        lines.extend(
            [
                "## Quality",
                "",
            ]
        )
        if quality_issues:
            lines.append(f"- unresolved_issues: `{', '.join(quality_issues)}`")
        if quality_detected_issues:
            lines.append(f"- detected_issues: `{', '.join(quality_detected_issues)}`")
        if quality_repair_actions:
            lines.append(f"- repair_actions: `{', '.join(quality_repair_actions)}`")
        lines.append("")
    if error_text.strip():
        lines.extend(
            [
                "## Bridge Error",
                "",
                error_text.strip(),
                "",
            ]
        )
    lines.extend(
        [
            "## Continuation",
            "",
            f"NEXT_ACTION: {next_action}",
            "",
            "## Response",
            "",
            response_text.strip() if response_text.strip() else "_No response body generated._",
            "",
        ]
    )
    return "\n".join(lines)


def _build_bridge_dispatch_record(
    *,
    observe_id: str,
    group_label: str,
    role: str,
    bridge_provider: str,
    bridge_route: str,
    bridge_meta: Mapping[str, Any] | None,
    source_kind: str,
    source_artifact: Optional[str],
    prompt_used: str,
    bridge_prompt: str,
    source_excerpt: str = "",
    source_excerpt_truncated: bool = False,
    raw_response_text: str = "",
    normalized_response_text: str = "",
    status: str,
    error_text: str = "",
    error_category: str = "",
    error_stage: str = "",
    quality_status: str = "unknown",
    quality_issues: Sequence[str] = (),
    quality_detected_issues: Sequence[str] = (),
    quality_repair_actions: Sequence[str] = (),
    required_sections: Sequence[str] = (),
    missing_sections: Sequence[str] = (),
    prompt_contract_audit: Mapping[str, Any] | None = None,
    response_artifact: Optional[str] = None,
    response_surface_file: str = "",
    response_receipt_file: str = "",
) -> dict[str, Any]:
    bridge_meta_summary: dict[str, Any] = {}
    for key in ("session_id", "node_id", "lane", "lane_color", "run_kind", "launch_profile"):
        value = None if bridge_meta is None else bridge_meta.get(key)
        cleaned = str(value).strip() if isinstance(value, str) else value
        if cleaned not in (None, "", [], {}):
            bridge_meta_summary[key] = cleaned
    prompt_audit = {
        key: value
        for key, value in dict(prompt_contract_audit or {}).items()
        if value not in (None, "", [], {})
    }
    return {
        "observe_id": observe_id,
        "group_label": group_label,
        "role": role,
        "generated_at": _now_iso(),
        "bridge_provider": bridge_provider,
        "bridge_route": bridge_route or None,
        "bridge_meta": bridge_meta_summary,
        "source_kind": source_kind,
        "source_artifact": source_artifact or None,
        "prompt_used": prompt_used,
        "prompt_used_sha256": _text_sha256(prompt_used),
        "prompt_contract_audit": prompt_audit,
        "bridge_prompt_chars": len(bridge_prompt),
        "bridge_prompt_sha256": _text_sha256(bridge_prompt),
        "bridge_prompt": bridge_prompt,
        "source_excerpt_chars": len(source_excerpt),
        "source_excerpt_sha256": _text_sha256(source_excerpt) if source_excerpt else None,
        "source_excerpt_truncated": bool(source_excerpt_truncated),
        "source_excerpt": source_excerpt or None,
        "raw_response_chars": len(raw_response_text),
        "raw_response_sha256": _text_sha256(raw_response_text) if raw_response_text else None,
        "raw_response_text": raw_response_text,
        "normalized_response_chars": len(normalized_response_text),
        "normalized_response_sha256": (
            _text_sha256(normalized_response_text) if normalized_response_text else None
        ),
        "normalized_response_text": normalized_response_text,
        "status": status,
        "error_text": error_text or None,
        "error_category": error_category or None,
        "error_stage": error_stage or None,
        "quality_status": quality_status or "unknown",
        "quality_issues": [str(item).strip() for item in quality_issues if str(item).strip()],
        "quality_detected_issues": [
            str(item).strip() for item in quality_detected_issues if str(item).strip()
        ],
        "quality_repair_actions": [
            str(item).strip() for item in quality_repair_actions if str(item).strip()
        ],
        "required_sections": [str(item).strip() for item in required_sections if str(item).strip()],
        "missing_sections": [str(item).strip() for item in missing_sections if str(item).strip()],
        "response_artifact": response_artifact or None,
        "response_surface_file": response_surface_file or None,
        "response_receipt_file": response_receipt_file or None,
    }


def _bridge_group_node_id(*, group_index: Any, label: str) -> str:
    try:
        prefix = f"OBS-{int(group_index):02d}"
    except Exception:
        prefix = "OBS"
    slug = re.sub(r"[^A-Za-z0-9]+", "-", str(label or "").strip()).strip("-").upper()
    if not slug:
        slug = "GROUP"
    return f"{prefix}-{slug[:40]}"


def _summarize_groups_continuation(groups_payload: List[Dict[str, Any]]) -> Dict[str, Any]:
    response_files = [
        str(group.get("response_file", "")).strip()
        for group in groups_payload
        if isinstance(group, dict) and str(group.get("response_file", "")).strip()
    ]
    latest_group = None
    for group in groups_payload:
        if not isinstance(group, dict):
            continue
        if str(group.get("response_file", "")).strip():
            latest_group = group
    if latest_group is None:
        return {
            "read_paths": [],
            "latest_response_file": None,
            "next_action": None,
            "hint": None,
        }
    return {
        "read_paths": response_files,
        "latest_response_file": latest_group.get("response_file"),
        "next_action": latest_group.get("next_action"),
        "hint": latest_group.get("continuation_hint"),
    }


def _build_run_continuation(
    *,
    result_note_rel: Optional[str],
    synthesis_summary: Dict[str, Any],
    groups_payload: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return build_grouped_observe_continuation(
        result_note_rel=result_note_rel,
        synthesis_summary=synthesis_summary,
        groups_payload=groups_payload,
    )


def _grouped_observe_contract_errors(groups_payload: List[Dict[str, Any]]) -> List[str]:
    errors: List[str] = []
    for group in groups_payload:
        if not isinstance(group, dict):
            continue
        label = str(group.get("label") or "?").strip() or "?"
        role = str(group.get("role") or "probe").strip().lower() or "probe"
        depends_on = (
            [str(item).strip() for item in group.get("depends_on", []) if str(item).strip()]
            if isinstance(group.get("depends_on", []), list)
            else []
        )
        # Synthesis/evaluation groups with depends_on are now supported via
        # the session orchestrator's wave computation.  Kept as advisory only.
        if role not in ("probe", "synthesis", "evaluation", "advisory"):
            errors.append(
                f"unrecognised group role '{role}' on group '{label}'; expected probe, synthesis, evaluation, or advisory"
            )
    return errors


def _dispatch_groups_to_bridge(
    *,
    repo_root: Path,
    observe_id: str,
    groups_payload: List[Dict[str, Any]],
    plan_path: Optional[Path] = None,
    bridge_provider: Optional[str],
    bridge_max_chars: int,
    bridge_timeout_s: float,
    bridge_workers: int,
    launch_profile: str,
    stagger_ms: int,
    target_labels: Optional[List[str]] = None,
    run_kind: Optional[str] = None,
    cancel_event: Optional[threading.Event] = None,
    on_group_dispatch: Optional[Callable[[Dict[str, Any]], None]] = None,
    on_group_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Dispatch grouped observe-plan slices through the bridge runtime and persist per-group execution state for downstream continuation handling.
    - Mechanism: Resolve bridge configuration, sweep stale provider tabs, derive transport policy, launch each eligible group through the bridge callable, and collect per-group runtime/status payloads.
    - Reads: repo_root, groups_payload, bridge provider/runtime settings, bridge capability metadata, and optional cancellation/dispatch callbacks.
    - Writes: Group response metadata, runtime-state payloads, bridge dispatch artifacts, and continuation-ready status fields returned in the dispatch summary.
    - Guarantee: Returns a dispatch summary dict covering each attempted group plus bridge/runtime metadata needed by the grouped observe runner.
    - Fails: Degrades bridge callable bootstrap failures into recorded dispatch errors and propagates unexpected runtime exceptions that escape per-group handling.
    - When-needed: Open when you need the exact `_dispatch_groups_to_bridge` helper that fans grouped observe work into bridge dispatch, especially while tracing group-level launch or completion state.
    - Escalates-to: tools/meta/apply/observe_session.py::MetaSessionOrchestratorImpl.run; tools/meta/apply/observe_session_runner.py::run_session_once.
    - Navigation-group: observe_apply.
    """
    ask_ai_error = ""
    ask_ai: Optional[Callable[[str, Optional[Dict[str, Any]]], str]] = None
    try:
        ask_ai = _load_bridge_callable(repo_root)
    except Exception as exc:  # pragma: no cover - runtime dependency availability
        ask_ai_error = str(exc)
    bridge_config, resolved_provider = _resolve_bridge_config(
        repo_root=repo_root,
        bridge_provider=bridge_provider,
        bridge_timeout_s=bridge_timeout_s,
        bridge_route="kernel_probe",
    )
    # Sweep stale provider tabs before any dispatch to prevent cross-run
    # contamination (orphan tabs with old responses confuse the dispatcher).
    try:
        from system.core.bridge import _BRIDGE as _bridge_singleton  # noqa: E402
        swept = _bridge_singleton.sweep_provider_tabs(resolved_provider)
        if swept:
            import logging as _sweep_logging
            _sweep_logging.getLogger("observe_dispatch").info(
                "Pre-dispatch sweep: closed %d stale %s tab(s)", swept, resolved_provider,
            )
    except Exception:
        pass  # Non-fatal: sweep is best-effort hygiene
    bridge_config = dict(bridge_config)
    bridge_meta = bridge_config.get("meta")
    if not isinstance(bridge_meta, dict):
        bridge_meta = {}
    normalized_launch_profile = normalize_launch_profile(launch_profile)
    preferred_transport_order = bridge_meta.get("preferred_transport_order")
    if not isinstance(preferred_transport_order, list) or not preferred_transport_order:
        preferred_transport_order = (
            ["dom_inject_click", "cdp_input"]
            if normalized_launch_profile == "safe"
            else ["dom_inject_click", "cdp_input", "native_macos_input"]
        )
    else:
        preferred_transport_order = [
            str(item).strip()
            for item in preferred_transport_order
            if str(item).strip()
        ]

    explicit_global_input = bridge_meta.get("allow_global_input_transport")
    if explicit_global_input is None:
        allow_global_input_transport = normalized_launch_profile != "safe"
    else:
        allow_global_input_transport = bool(explicit_global_input)

    if not allow_global_input_transport:
        preferred_transport_order = [
            item for item in preferred_transport_order
            if item != "native_macos_input"
        ]

    bridge_meta["launch_profile"] = normalized_launch_profile
    bridge_meta["preferred_transport_order"] = preferred_transport_order
    bridge_meta["allow_global_input_transport"] = allow_global_input_transport
    bridge_config["meta"] = bridge_meta
    compact_roster_by_label: Dict[str, List[str]] = {}
    for group in groups_payload:
        if not isinstance(group, Mapping):
            continue
        label = str(group.get("label", "")).strip()
        if not label:
            continue
        roster = (
            [
                str(item).strip()
                for item in group.get("sibling_scope_roster", [])
                if str(item).strip()
            ]
            if isinstance(group.get("sibling_scope_roster"), list)
            else []
        )
        if not roster:
            roster = []
            for sibling in groups_payload:
                if not isinstance(sibling, Mapping):
                    continue
                sibling_label = str(sibling.get("label", "")).strip()
                if not sibling_label or sibling_label == label:
                    continue
                sibling_question = str(sibling.get("question", "")).strip()
                sibling_notes = str(sibling.get("notes", "")).strip()
                sibling_focus = sibling_question or sibling_notes or "bounded parallel slice"
                roster.append(f"{sibling_label}: {sibling_focus}")
        if roster:
            compact_roster_by_label[label] = roster

    selected_labels = {
        str(label).strip()
        for label in (target_labels or [])
        if str(label).strip()
    }

    class _BridgeGroupCancel:
        def __init__(self, *events: Optional[threading.Event]) -> None:
            self._events = tuple(event for event in events if event is not None)

        def is_set(self) -> bool:
            return any(event.is_set() for event in self._events)

        def wait(self, timeout: Optional[float] = None) -> bool:
            if self.is_set():
                return True
            if timeout is None:
                while not self.is_set():
                    time.sleep(0.05)
                return True
            deadline = time.monotonic() + max(float(timeout), 0.0)
            while time.monotonic() < deadline:
                if self.is_set():
                    return True
                time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
            return self.is_set()

    group_timeout_s = float(bridge_timeout_s) if bridge_timeout_s and bridge_timeout_s > 0 else None
    wait_tick_s = min(1.0, max(0.05, (group_timeout_s or 1.0) / 20.0))

    def _mark_group_timeout(group: Mapping[str, Any], *, elapsed_s: float) -> Dict[str, Any]:
        group_out = dict(group)
        timeout_value = group_timeout_s or elapsed_s
        group_out["response_status"] = "error"
        group_out["runtime_state"] = "error"
        group_out["response_error"] = (
            f"Bridge group timed out after {timeout_value:.3g}s without a terminal result."
        )
        group_out["response_error_category"] = "bridge_group_timeout"
        group_out["response_error_stage"] = "observe_dispatch"
        group_out["response_timeout_s"] = timeout_value
        group_out["response_elapsed_s"] = elapsed_s
        group_out["response_timed_out"] = True
        return group_out

    def _dispatch_single(
        group: Dict[str, Any],
        current_groups_payload: Optional[List[Dict[str, Any]]] = None,
        group_cancel_event: Optional[threading.Event] = None,
    ) -> Dict[str, Any]:
        group_out = dict(group)
        effective_cancel_event: Any = (
            _BridgeGroupCancel(cancel_event, group_cancel_event)
            if group_cancel_event is not None
            else cancel_event
        )
        groups_view = current_groups_payload if isinstance(current_groups_payload, list) else groups_payload
        dump_file = group.get("dump_file")
        if not isinstance(dump_file, str) or not dump_file.strip():
            group_out["response_status"] = "skipped_no_dump"
            group_out["runtime_state"] = "skipped_no_dump"
            return group_out

        dump_rel = dump_file.strip()
        dump_path = (repo_root / dump_rel).resolve()
        if not dump_path.exists():
            group_out["response_status"] = "skipped_missing_dump"
            group_out["response_error"] = f"Dump file not found: {dump_rel}"
            group_out["runtime_state"] = "skipped_missing_dump"
            return group_out

        prompt_used = str(group.get("prompt", "")).strip()
        prompt_contract_audit = _sync_group_dump_prompt_meta(
            dump_path=dump_path,
            prompt_text=prompt_used,
        )
        group_out["context_refresh"] = _refresh_group_dump_context(
            repo_root=repo_root,
            group=group_out,
            prompt_text=prompt_used,
        )
        if (
            not prompt_contract_audit
            and isinstance(group_out.get("context_refresh"), Mapping)
            and isinstance(group_out["context_refresh"].get("prompt_contract_audit"), Mapping)
        ):
            prompt_contract_audit = dict(group_out["context_refresh"].get("prompt_contract_audit") or {})
        dump_text = dump_path.read_text(encoding="utf-8")
        label = str(group.get("label", "group")).strip() or "group"
        role = str(group.get("role", "probe")).strip() or "probe"
        output_contract = _coerce_output_contract(group.get("output_contract"))
        prompt_metadata = group.get("prompt_metadata") if isinstance(group.get("prompt_metadata"), Mapping) else None
        response_surface = resolve_response_surface(
            repo_root,
            group.get("response_surface"),
            output_contract=output_contract,
        )
        response_schema = group.get("response_schema") if isinstance(group.get("response_schema"), Mapping) else None
        json_only = bool(group.get("json_only")) and response_schema is not None
        requested_provider = str(group.get("provider") or "").strip()
        provider_config = (
            group.get("provider_config")
            if isinstance(group.get("provider_config"), Mapping)
            else None
        )
        prompt_budget = _resolve_effective_bridge_prompt_budget(
            repo_root,
            bridge_max_chars,
            requested_provider or bridge_provider or resolved_provider,
        )
        group_ask_ai, provider_runtime_config, provider_used, provider_error = _resolve_group_provider_runtime(
            repo_root=repo_root,
            requested_provider=requested_provider,
            default_bridge_callable=ask_ai,
            default_bridge_config=bridge_config,
            default_bridge_error=ask_ai_error or "bridge provider unavailable",
            default_bridge_provider=resolved_provider,
            bridge_timeout_s=bridge_timeout_s,
            provider_config=provider_config,
        )

        # --- Synthesis/Evaluation: build join prompt with current-node dump and upstream probe content ---
        if role in ("synthesis", "evaluation"):
            depends_on_labels = group.get("depends_on", [])
            join_budgets = _resolve_join_prompt_budgets(
                label=label,
                role=role,
                group_prompt=prompt_used,
                dump_rel_path=dump_rel,
                max_chars=prompt_budget,
                declared_dependencies=depends_on_labels,
                response_schema=response_schema,
                json_only=json_only,
            )
            dump_budget = int(join_budgets.get("dump_budget") or prompt_budget)
            dump_excerpt, truncated = _truncate(dump_text, dump_budget)
            upstream_artifacts: list[tuple[str, str]] = []
            upstream_found = 0
            per_dependency_budget = int(join_budgets.get("per_dependency_budget") or 0)
            for dep_label in depends_on_labels:
                dep_label_clean = str(dep_label).strip()
                if not dep_label_clean:
                    continue
                for other_group in groups_view:
                    other_label = str(other_group.get("label", "")).strip()
                    if other_label != dep_label_clean:
                        continue
                    artifact = _load_join_artifact_text(
                        repo_root=repo_root,
                        group=other_group,
                        budget=per_dependency_budget,
                    )
                    if artifact is not None:
                        upstream_artifacts.append(artifact)
                        upstream_found += 1
                    break
            def _render_join_prompt(current_dump_excerpt: str, current_truncated: bool, artifacts: list[tuple[str, str]]) -> str:
                return _build_join_bridge_prompt(
                    label=label,
                    role=role,
                    group_prompt=prompt_used,
                    dump_rel_path=dump_rel,
                    dump_json=current_dump_excerpt,
                    truncated=current_truncated,
                    max_chars=prompt_budget,
                    upstream_artifacts=artifacts,
                    declared_dependencies=depends_on_labels,
                    response_schema=response_schema,
                    json_only=json_only,
                )

            bridge_prompt = _render_join_prompt(dump_excerpt, truncated, upstream_artifacts)
            if prompt_budget > 0 and len(bridge_prompt) > prompt_budget:
                tighter_dump_budget = max(1024, dump_budget - (len(bridge_prompt) - prompt_budget) - 512)
                dump_excerpt, truncated = _truncate(dump_text, tighter_dump_budget)
                bridge_prompt = _render_join_prompt(dump_excerpt, truncated, upstream_artifacts)
            if prompt_budget > 0 and len(bridge_prompt) > prompt_budget and upstream_artifacts:
                tighter_artifacts: list[tuple[str, str]] = []
                tighter_budget = max(800, int(max(per_dependency_budget, 1200) * 0.6))
                for dep_label in depends_on_labels:
                    dep_label_clean = str(dep_label).strip()
                    if not dep_label_clean:
                        continue
                    for other_group in groups_view:
                        if str(other_group.get("label", "")).strip() != dep_label_clean:
                            continue
                        artifact = _load_join_artifact_text(
                            repo_root=repo_root,
                            group=other_group,
                            budget=tighter_budget,
                        )
                        if artifact is not None:
                            tighter_artifacts.append(artifact)
                        break
                upstream_artifacts = tighter_artifacts
                bridge_prompt = _render_join_prompt(dump_excerpt, truncated, upstream_artifacts)
            print(
                f"[SYNTHESIS_JOIN] label={label} depends_on={depends_on_labels} "
                f"upstream_found={upstream_found}/{len(depends_on_labels)} "
                f"prompt_chars={len(bridge_prompt)} dump_budget={dump_budget}",
                flush=True,
            )
        else:
            depends_on_labels = [
                str(item).strip()
                for item in (group.get("depends_on", []) if isinstance(group.get("depends_on"), list) else [])
                if str(item).strip()
            ]
            upstream_artifacts = []
            if depends_on_labels and prompt_budget > 0:
                upstream_total_budget = max(12_000, prompt_budget // 5)
                per_dependency_budget = max(4_000, upstream_total_budget // max(1, len(depends_on_labels)))
                for dep_label in depends_on_labels:
                    for other_group in groups_view:
                        if str(other_group.get("label", "")).strip() != dep_label:
                            continue
                        artifact = _load_join_artifact_text(
                            repo_root=repo_root,
                            group=other_group,
                            budget=per_dependency_budget,
                        )
                        if artifact is not None:
                            upstream_artifacts.append(artifact)
                        break
            dump_excerpt, truncated, bridge_prompt, prompt_budget = _fit_probe_prompt_to_budget(
                repo_root=repo_root,
                label=label,
                group_prompt=prompt_used,
                dump_rel_path=dump_rel,
                dump_text=dump_text,
                max_chars=bridge_max_chars,
                provider_hint=requested_provider or bridge_provider or resolved_provider,
                sibling_focuses=compact_roster_by_label.get(label, []),
                incoming_queries=group.get("incoming_queries") if isinstance(group.get("incoming_queries"), list) else [],
                upstream_artifacts=upstream_artifacts,
                declared_dependencies=depends_on_labels,
                output_contract=output_contract,
                prompt_metadata=prompt_metadata,
                response_surface=response_surface,
                response_schema=response_schema,
                json_only=json_only,
            )

        raw_response_text = ""
        normalized_response_text = ""
        error_text = ""
        status = "success"
        error_category = ""
        error_stage = ""
        quality_status = "unknown"
        quality_issues: List[str] = []
        quality_detected_issues: List[str] = []
        quality_repair_actions: List[str] = []
        quality_meta: Dict[str, Any] = {}
        response_surface_file = ""
        response_receipt_file = ""
        did_schema_retry = False
        omitted_source_evidence = _excerpt_is_omitted_for_budget(dump_excerpt)
        group_bridge_config = dict(provider_runtime_config)
        existing_meta = group_bridge_config.get("meta")
        if isinstance(existing_meta, dict):
            group_bridge_meta = dict(bridge_meta)
            group_bridge_meta.update(existing_meta)
        elif _is_bridge_provider(requested_provider or provider_used):
            group_bridge_meta = dict(bridge_meta)
        else:
            group_bridge_meta = {}
        group_bridge_meta["node_id"] = _bridge_group_node_id(
            group_index=group.get("index"),
            label=label,
        )
        group_bridge_meta["session_id"] = str(observe_id)
        if run_kind:
            group_bridge_meta["run_kind"] = run_kind
        group_bridge_meta.setdefault("lane", "GROUPED_OBSERVE")
        group_bridge_meta.setdefault(
            "lane_color",
            observe_lane_color(role=role, lane=group_bridge_meta.get("lane")),
        )
        if _normalize_bridge_provider_token(requested_provider or provider_used) == "gemini":
            # Keep grouped-observe Gemini launches on the preflighted target unless the
            # caller explicitly opts back into multi-account rotation.
            group_bridge_meta.setdefault("allow_account_rotation", False)
        group_bridge_config["meta"] = group_bridge_meta

        if omitted_source_evidence:
            status = "quality_error"
            error_text = (
                "Observe dispatch omitted the current dump evidence due to prompt budget. "
                "Split the file or reduce repeated prompt scaffolding before retrying."
            )
            error_category = "prompt_budget_omitted_evidence"
            error_stage = "prompt_build"
            quality_status = "degraded_semantic"
            quality_issues = ["source_evidence_omitted_for_budget"]
            quality_detected_issues = list(quality_issues)
            quality_meta = {
                "status": quality_status,
                "issues": list(quality_issues),
                "detected_issues": list(quality_detected_issues),
                "repair_actions": [],
                "required_sections": [],
                "missing_sections": [],
                "normalized_text": "",
            }
        elif group_ask_ai is None:
            status = "error"
            failure_meta = provider_unavailable_failure(
                provider_used or requested_provider,
                provider_error or requested_provider or provider_used,
            )
            error_text = f"Provider unavailable: {failure_meta['message']}"
            error_category = failure_meta["category"]
            error_stage = failure_meta["stage"]
        else:
            provider_claim_source = f"run_observe:{observe_id}:{label}"
            provider_claim_wait_timeout_s = max(
                30.0,
                min(
                    float(group_bridge_config.get("monitor_timeout_s") or bridge_timeout_s or 300.0),
                    300.0,
                ),
            )
            provider_claim_ttl_seconds = max(
                int(float(group_bridge_config.get("monitor_timeout_s") or bridge_timeout_s or 300.0)) + 120,
                300,
            )
            try:
                raw_response_text = call_with_provider_claim(
                    repo_root,
                    provider=provider_used or requested_provider,
                    source=provider_claim_source,
                    action=lambda: group_ask_ai(bridge_prompt, config=group_bridge_config, cancel=effective_cancel_event),
                    metadata={
                        "observe_id": observe_id,
                        "group_label": label,
                        "lane": "run_observe",
                    },
                    wait_timeout_s=provider_claim_wait_timeout_s,
                    ttl_seconds=provider_claim_ttl_seconds,
                    cancel_event=effective_cancel_event,
                    raise_on_unavailable=True,
                )["value"]
                quality_meta = _validate_group_response(
                    prompt_used,
                    raw_response_text,
                    output_contract=output_contract,
                    prompt_metadata=prompt_metadata,
                    response_surface=response_surface,
                    response_schema=response_schema,
                    json_only=json_only,
                )
                if response_schema and quality_meta.get("status") != "ok":
                    retry_prompt = "\n".join(
                        [
                            bridge_prompt,
                            "",
                            "[REPAIR]",
                            "Your previous response failed JSON/schema validation.",
                            "Return ONLY corrected JSON matching the schema below.",
                            f"Issues: {', '.join(str(item) for item in quality_meta.get('issues', []) if str(item).strip()) or 'invalid_json'}",
                            "Previous response:",
                            raw_response_text.strip() or "<empty>",
                            "",
                            json.dumps(response_schema, indent=2, ensure_ascii=False),
                        ]
                    )
                    repaired_response_text = call_with_provider_claim(
                        repo_root,
                        provider=provider_used or requested_provider,
                        source=provider_claim_source,
                        action=lambda: group_ask_ai(retry_prompt, config=group_bridge_config, cancel=effective_cancel_event),
                        metadata={
                            "observe_id": observe_id,
                            "group_label": label,
                            "lane": "run_observe_repair",
                        },
                        wait_timeout_s=provider_claim_wait_timeout_s,
                        ttl_seconds=provider_claim_ttl_seconds,
                        cancel_event=effective_cancel_event,
                        raise_on_unavailable=True,
                    )["value"]
                    repaired_quality = _validate_group_response(
                        prompt_used,
                        repaired_response_text,
                        output_contract=output_contract,
                        prompt_metadata=prompt_metadata,
                        response_surface=response_surface,
                        response_schema=response_schema,
                        json_only=json_only,
                    )
                    did_schema_retry = True
                    raw_response_text = repaired_response_text
                    quality_meta = repaired_quality
                # Surface-level retry: when a response_surface requires
                # 'operations' and the response returned an empty array [],
                # retry once with an explicit repair instruction.
                if (
                    response_surface
                    and not did_schema_retry
                    and quality_meta.get("status") != "ok"
                ):
                    _surface_ops_field = next(
                        (
                            item
                            for item in (response_surface.get("required_fields") or [])
                            if isinstance(item, Mapping)
                            and str(item.get("field_id", "")).strip() == "operations"
                        ),
                        None,
                    )
                    _surface_payload = quality_meta.get("surface_payload") or {}
                    _surface_ops = _surface_payload.get("operations")
                    if _surface_ops_field is not None and (
                        _surface_ops is None
                        or (isinstance(_surface_ops, list) and len(_surface_ops) == 0)
                    ):
                        surface_retry_prompt = "\n".join(
                            [
                                bridge_prompt,
                                "",
                                "[REPAIR — EMPTY OPERATIONS]",
                                "Your previous response returned an empty operations array.",
                                "You MUST emit at least one valid operation for the assigned files.",
                                "Each operation must be a JSON object with at minimum: op, target, and the relevant payload.",
                                f"Issues: {', '.join(str(i) for i in quality_meta.get('issues', []) if str(i).strip()) or 'empty_operations'}",
                            ]
                        )
                        repaired_response_text = call_with_provider_claim(
                            repo_root,
                            provider=provider_used or requested_provider,
                            source=provider_claim_source,
                            action=lambda: group_ask_ai(
                                surface_retry_prompt, config=group_bridge_config, cancel=effective_cancel_event,
                            ),
                            metadata={
                                "observe_id": observe_id,
                                "group_label": label,
                                "lane": "run_observe_surface_repair",
                            },
                            wait_timeout_s=provider_claim_wait_timeout_s,
                            ttl_seconds=provider_claim_ttl_seconds,
                            cancel_event=effective_cancel_event,
                            raise_on_unavailable=True,
                        )["value"]
                        repaired_quality = _validate_group_response(
                            prompt_used,
                            repaired_response_text,
                            output_contract=output_contract,
                            prompt_metadata=prompt_metadata,
                            response_surface=response_surface,
                            response_schema=response_schema,
                            json_only=json_only,
                        )
                        did_schema_retry = True
                        raw_response_text = repaired_response_text
                        quality_meta = repaired_quality
                quality_status = str(quality_meta.get("status", "unknown"))
                quality_issues = [
                    str(item).strip()
                    for item in quality_meta.get("issues", [])
                    if str(item).strip()
                ]
                quality_detected_issues = [
                    str(item).strip()
                    for item in quality_meta.get("detected_issues", [])
                    if str(item).strip()
                ]
                quality_repair_actions = [
                    str(item).strip()
                    for item in quality_meta.get("repair_actions", [])
                    if str(item).strip()
                ]
                if did_schema_retry:
                    quality_repair_actions = list(dict.fromkeys([*quality_repair_actions, "schema_repair_retry"]))
                normalized_response_text = str(
                    quality_meta.get("normalized_text", raw_response_text) or ""
                )
                if quality_status in _SEMANTIC_DEGRADED_STATUSES:
                    status = "quality_error"
                    error_category = "response_incomplete"
                    error_stage = "response_validation"
                    error_text = (
                        "Observe response failed quality checks: "
                        + ", ".join(quality_issues)
                    )
            except Exception as exc:  # pragma: no cover - depends on runtime bridge availability
                if effective_cancel_event and effective_cancel_event.is_set():
                    status = "aborted"
                    error_text = "Observe run aborted by user."
                    error_category = "observe_aborted"
                    error_stage = "observe_dispatch"
                else:
                    status = "error"
                    normalized = _normalize_bridge_failure(exc)
                    error_text = str(normalized["message"] or "")
                    error_category = str(normalized["category"] or "")
                    error_stage = str(normalized["stage"] or "")
                    record_provider_interrupt(
                        repo_root,
                        provider=provider_used or requested_provider,
                        message=error_text,
                        category=error_category,
                        stage=error_stage,
                        payload={
                            "observe_id": observe_id,
                            "group_label": label,
                        },
                    )

        response_path = dump_path.with_name(f"{dump_path.stem}_response.md")
        response_rel = str(response_path.relative_to(repo_root))
        dispatch_path = _bridge_dispatch_sidecar_path(response_path)
        dispatch_rel = str(dispatch_path.relative_to(repo_root))
        surface_payload = quality_meta.get("surface_payload") if isinstance(quality_meta.get("surface_payload"), Mapping) else None
        receipt_payload = quality_meta.get("receipt_payload") if isinstance(quality_meta.get("receipt_payload"), Mapping) else None
        if response_surface and surface_payload is not None:
            surface_path = response_surface_sidecar_path(response_path)
            surface_payload_artifact = {
                "observe_id": observe_id,
                "group_label": label,
                "dump_file": dump_rel,
                "generated_at": _now_iso(),
                "surface_kind": str(response_surface.get("surface_kind") or "").strip() or None,
                "response_kind": str(response_surface.get("response_kind") or "").strip() or None,
                "response_surface": dict(response_surface),
                "payload": dict(surface_payload),
                "projected_markdown": normalized_response_text,
            }
            surface_path.write_text(
                json.dumps(surface_payload_artifact, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            response_surface_file = str(surface_path.relative_to(repo_root))
        if response_schema and receipt_payload is not None:
            receipt_path = _response_receipt_sidecar_path(response_path)
            receipt_artifact = {
                "observe_id": observe_id,
                "group_label": label,
                "dump_file": dump_rel,
                "generated_at": _now_iso(),
                "response_schema": dict(response_schema),
                "payload": dict(receipt_payload),
                "projected_markdown": normalized_response_text,
            }
            receipt_path.write_text(
                json.dumps(receipt_artifact, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            response_receipt_file = str(receipt_path.relative_to(repo_root))
        continuation = _build_continuation_contract(
            response_text=normalized_response_text,
            artifact_rel_path=response_rel,
            label=label,
            role=role,
            status=status,
        )
        response_md = _build_response_markdown(
            observe_id=observe_id,
            group_label=label,
            dump_file=dump_rel,
            prompt_used=prompt_used,
            bridge_provider=provider_used,
            bridge_prompt_chars=len(bridge_prompt),
            dump_truncated=truncated,
            status=status,
            response_text=normalized_response_text,
            error_text=error_text,
            error_category=error_category,
            error_stage=error_stage,
            quality_status=quality_status,
            response_surface_kind=str(response_surface.get("surface_kind") or "") if response_surface else "",
            response_kind=str(response_surface.get("response_kind") or "") if response_surface else "",
            response_surface_file=response_surface_file,
            response_receipt_file=response_receipt_file,
            bridge_dispatch_file=dispatch_rel,
            quality_issues=quality_issues,
            quality_detected_issues=quality_detected_issues,
            quality_repair_actions=quality_repair_actions,
            next_action=continuation["next_action"],
            continuation_source=continuation["source"],
        )
        response_path.write_text(response_md, encoding="utf-8")
        dispatch_payload = _build_bridge_dispatch_record(
            observe_id=observe_id,
            group_label=label,
            role=role,
            bridge_provider=provider_used,
            bridge_route=str(group_bridge_config.get("bridge_route") or ""),
            bridge_meta=group_bridge_meta,
            source_kind="observe_dump_json",
            source_artifact=dump_rel,
            prompt_used=prompt_used,
            bridge_prompt=bridge_prompt,
            source_excerpt=dump_excerpt,
            source_excerpt_truncated=truncated,
            raw_response_text=raw_response_text,
            normalized_response_text=normalized_response_text,
            status=status,
            error_text=error_text,
            error_category=error_category,
            error_stage=error_stage,
            quality_status=quality_status,
            quality_issues=quality_issues,
            quality_detected_issues=quality_detected_issues,
            quality_repair_actions=quality_repair_actions,
            required_sections=quality_meta.get("required_sections", []),
            missing_sections=quality_meta.get("missing_sections", []),
            prompt_contract_audit=prompt_contract_audit,
            response_artifact=response_rel,
            response_surface_file=response_surface_file,
            response_receipt_file=response_receipt_file,
        )
        dispatch_path.write_text(
            json.dumps(dispatch_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        # --- Bridge operating system: per-dispatch prompt manifest ---
        # Emit a prompt_manifest.json beside this dump so the run is auditable.
        # The manifest captures every file injected, byte counts, hashes, sentinel
        # tokens, validator decisions, and over/under cap flags. If this file does
        # not exist for a run, the run is not auditable.
        try:
            from tools.meta.bridge.prompt_manifest import (
                build_file_entries as _bos_build_file_entries,
                build_manifest as _bos_build_manifest,
                manifest_path_for as _bos_manifest_path_for,
                write_manifest as _bos_write_manifest,
            )
            _bos_contract = resolve_group_evidence_contract(
                repo_root,
                plan_context_files=[],
                group_context_files=group.get("context_files", []),
                targets=group.get("targets", []),
                context_merge_mode="group_only",
            )
            _bos_entries = [
                *_bos_build_file_entries(repo_root, _bos_contract["target_files"], role="target"),
                *_bos_build_file_entries(repo_root, _bos_contract["effective_context_files"], role="context"),
            ]
            _bos_notes = []
            _bos_overlap_paths = [
                str(item).strip()
                for item in (group.get("context_target_overlaps") or [])
                if str(item).strip()
            ]
            if _bos_overlap_paths:
                _bos_notes.append(
                    "Dropped context paths already present as targets: "
                    + ", ".join(_bos_overlap_paths)
                )
            _bos_task_shape = str(group.get("task_shape", "structural") or "structural").lower().strip()
            if _bos_task_shape not in ("orientation", "structural", "implementation"):
                _bos_task_shape = "structural"
            _bos_manifest = _bos_build_manifest(
                dispatch_id=observe_id,
                group_label=label,
                provider=provider_used or "chatgpt",
                task_shape_name=_bos_task_shape,
                prompt_body=bridge_prompt,
                file_entries=_bos_entries,
                plan_path=str(plan_path) if plan_path else None,
                notes=_bos_notes,
            )
            _bos_manifest_file = _bos_manifest_path_for(dispatch_path.parent, label)
            _bos_write_manifest(_bos_manifest, _bos_manifest_file)
            group_out["response_prompt_manifest"] = str(_bos_manifest_file.relative_to(repo_root)) if _bos_manifest_file.is_relative_to(repo_root) else str(_bos_manifest_file)
        except Exception as _bos_exc:
            group_out["response_prompt_manifest_error"] = f"manifest emission failed: {_bos_exc}"

        group_out["response_status"] = status
        group_out["runtime_state"] = status
        group_out["provider"] = provider_used
        group_out["provider_requested"] = requested_provider or None
        group_out["response_file"] = response_rel
        group_out["response_dispatch_file"] = dispatch_rel
        group_out["response_dump_chars"] = len(dump_excerpt)
        group_out["response_prompt_chars"] = len(bridge_prompt)
        group_out["response_dump_truncated"] = truncated
        group_out["response_body"] = normalized_response_text
        group_out["response_error_category"] = error_category or None
        group_out["response_error_stage"] = error_stage or None
        group_out["response_quality_status"] = quality_status
        group_out["response_quality_issues"] = quality_issues
        group_out["response_quality_detected_issues"] = quality_detected_issues
        group_out["response_quality_repair_actions"] = quality_repair_actions
        group_out["response_quality_required_sections"] = quality_meta.get("required_sections", [])
        group_out["response_quality_missing_sections"] = quality_meta.get("missing_sections", [])
        group_out["response_surface_kind"] = (
            str(response_surface.get("surface_kind") or "").strip() or None
            if response_surface
            else None
        )
        group_out["response_kind"] = (
            str(response_surface.get("response_kind") or "").strip() or None
            if response_surface
            else None
        )
        group_out["response_surface_file"] = response_surface_file or None
        group_out["response_receipt_file"] = response_receipt_file or None
        group_out["response_receipt_payload"] = dict(receipt_payload) if receipt_payload is not None else None
        group_out["response_schema"] = dict(response_schema) if response_schema else None
        group_out["json_only"] = json_only or None
        group_out["output_contract"] = output_contract
        group_out["prompt_response_mode"] = _resolve_response_mode(prompt_metadata)
        group_out["next_fork"] = quality_meta.get("next_fork")
        group_out["next_fork_block"] = quality_meta.get("next_fork_block")
        group_out["next_action"] = continuation["next_action"]
        group_out["continuation_hint"] = continuation["hint"]
        group_out["continuation_source"] = continuation["source"]
        pending = extract_pending_items_from_text(normalized_response_text)
        group_out["operator_decisions_pending"] = pending.get("operator_decisions_pending", [])
        group_out["agent_followups_pending"] = pending.get("agent_followups_pending", [])
        if error_text:
            group_out["response_error"] = error_text
        return group_out

    if not groups_payload:
        return {
            "enabled": True,
            "provider": resolved_provider,
            "workers": max(1, bridge_workers),
            "attempted_groups": 0,
            "response_files_written": 0,
            "failure_count": 0,
            "dispatch_scope_labels": [],
            "settled_group_labels": [],
            "pending_scope_labels": [],
            "same_pass_promoted_labels": [],
            "settle_passes": 0,
            "settle_launch_sequence": [],
            "quiescent": True,
            "groups": [],
        }

    groups_out: List[Dict[str, Any]] = [dict(group) for group in groups_payload]
    for group in groups_out:
        label = _group_label(group)
        if label in selected_labels and _resolved_group_runtime_state(group) == "running":
            group["runtime_state"] = "pending"
    candidate_labels = _expand_dispatch_scope_labels(groups_out, target_labels)
    attempted_labels: set[str] = set()
    terminal_notified: set[str] = set()
    settle_passes = 0
    settle_launch_sequence: List[str] = []
    initial_ready_labels: set[str] = set()

    def _snapshot_groups() -> List[Dict[str, Any]]:
        return [dict(group) for group in groups_out]

    def _notify_dispatch(group: Dict[str, Any]) -> None:
        if on_group_dispatch is None:
            return
        try:
            on_group_dispatch(dict(group))
        except Exception:
            pass

    def _notify_complete(group: Dict[str, Any]) -> None:
        label = _group_label(group)
        if not label or label in terminal_notified:
            return
        terminal_notified.add(label)
        if on_group_complete is None:
            return
        try:
            on_group_complete(dict(group))
        except Exception:
            pass

    def _mark_newly_blocked() -> None:
        before = {
            _group_label(group): _resolved_group_runtime_state(group)
            for group in groups_out
            if _group_label(group) in candidate_labels
        }
        _resolve_blocked_groups(groups_out)
        for group in groups_out:
            label = _group_label(group)
            if label not in candidate_labels:
                continue
            if _resolved_group_runtime_state(group) == "blocked" and before.get(label) != "blocked":
                _notify_complete(group)

    def _ready_indices() -> List[int]:
        label_to_state = {
            _group_label(group): _resolved_group_runtime_state(group)
            for group in groups_out
            if _group_label(group)
        }
        ready: List[int] = []
        for idx, group in enumerate(groups_out):
            label = _group_label(group)
            if not label or label not in candidate_labels:
                continue
            if label in attempted_labels:
                continue
            if _resolved_group_runtime_state(group) != "pending":
                continue
            if all(label_to_state.get(dep, "pending") in TERMINAL_GROUP_STATUSES for dep in _group_dependencies(group)):
                ready.append(idx)
        return ready

    max_workers = min(max(1, bridge_workers), max(1, len(candidate_labels) or len(groups_out)))
    if candidate_labels:
        initial_ready_labels = {
            _group_label(groups_out[idx])
            for idx in _ready_indices()
            if _group_label(groups_out[idx])
        }
        future_map: Dict[concurrent.futures.Future[Dict[str, Any]], Tuple[int, str]] = {}
        future_started_at: Dict[concurrent.futures.Future[Dict[str, Any]], float] = {}
        future_cancel_events: Dict[concurrent.futures.Future[Dict[str, Any]], threading.Event] = {}
        inflight_labels: set[str] = set()
        detached_shutdown = False

        def _launch_ready(executor: concurrent.futures.ThreadPoolExecutor) -> bool:
            nonlocal settle_passes
            launched = False
            while len(future_map) < max_workers and not (cancel_event and cancel_event.is_set()):
                _mark_newly_blocked()
                ready = [
                    idx
                    for idx in _ready_indices()
                    if _group_label(groups_out[idx]) not in inflight_labels
                ]
                if not ready:
                    break
                idx = ready[0]
                group = dict(groups_out[idx])
                label = _group_label(group, f"group_{idx + 1}")
                group["runtime_state"] = "running"
                groups_out[idx] = dict(group)
                attempted_labels.add(label)
                inflight_labels.add(label)
                settle_launch_sequence.append(label)
                _notify_dispatch(group)
                group_cancel_event = threading.Event()
                future = executor.submit(_dispatch_single, dict(group), _snapshot_groups(), group_cancel_event)
                future_map[future] = (idx, label)
                future_started_at[future] = time.monotonic()
                future_cancel_events[future] = group_cancel_event
                launched = True
                if stagger_ms > 0 and len(future_map) < max_workers:
                    time.sleep(float(stagger_ms) / 1000.0)
            if launched:
                settle_passes += 1
            return launched

        def _retire_future(future: concurrent.futures.Future[Dict[str, Any]]) -> Tuple[int, str]:
            idx, label = future_map.pop(future)
            inflight_labels.discard(label)
            future_started_at.pop(future, None)
            future_cancel_events.pop(future, None)
            return idx, label

        def _retire_timed_out_futures() -> None:
            nonlocal detached_shutdown
            if group_timeout_s is None:
                return
            now = time.monotonic()
            timed_out = [
                future
                for future, started_at in list(future_started_at.items())
                if not future.done() and (now - started_at) >= group_timeout_s
            ]
            for future in timed_out:
                started_at = future_started_at.get(future, now)
                group_cancel_event = future_cancel_events.get(future)
                idx, label = _retire_future(future)
                if group_cancel_event is not None:
                    group_cancel_event.set()
                future.cancel()
                elapsed_s = now - started_at
                groups_out[idx] = _mark_group_timeout(groups_out[idx], elapsed_s=max(elapsed_s, group_timeout_s))
                detached_shutdown = True
                _notify_complete(groups_out[idx])

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        try:
            _mark_newly_blocked()
            _launch_ready(executor)
            while future_map:
                done, _pending = concurrent.futures.wait(
                    tuple(future_map.keys()),
                    timeout=wait_tick_s,
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )
                if not done:
                    _retire_timed_out_futures()
                    _mark_newly_blocked()
                    _launch_ready(executor)
                    continue
                for future in done:
                    idx, label = _retire_future(future)
                    try:
                        result = future.result()
                    except Exception as exc:  # pragma: no cover - runtime safety net
                        result = dict(groups_out[idx])
                        normalized = _normalize_bridge_failure(exc)
                        result["response_status"] = "error"
                        result["runtime_state"] = "error"
                        result["response_error"] = str(normalized["message"] or exc)
                        result["response_error_category"] = str(normalized["category"] or "bridge_error")
                        result["response_error_stage"] = str(normalized["stage"] or "observe_dispatch")
                    groups_out[idx] = dict(result)
                    _notify_complete(groups_out[idx])
                _retire_timed_out_futures()
                _mark_newly_blocked()
                _launch_ready(executor)
        finally:
            executor.shutdown(wait=not detached_shutdown, cancel_futures=True)
    else:
        max_workers = max(1, bridge_workers)

    finalized_groups = _snapshot_groups()
    groups_payload = finalized_groups
    root_labels = selected_labels or initial_ready_labels or set(candidate_labels)
    settled_group_labels = sorted(
        label
        for group in finalized_groups
        for label in [_group_label(group)]
        if label in candidate_labels and _resolved_group_runtime_state(group) in TERMINAL_GROUP_STATUSES
    )
    pending_scope_labels = sorted(
        label
        for group in finalized_groups
        for label in [_group_label(group)]
        if label in candidate_labels and _resolved_group_runtime_state(group) not in TERMINAL_GROUP_STATUSES
    )
    same_pass_promoted_labels = sorted(label for label in attempted_labels if label not in root_labels)
    dispatched = len(attempted_labels)
    written = sum(
        1
        for group in finalized_groups
        if _group_label(group) in attempted_labels and str(group.get("response_file", "")).strip()
    )
    failures = sum(
        1
        for group in finalized_groups
        if _group_label(group) in attempted_labels
        and str(group.get("response_status", "")).strip() in {"error", "quality_error"}
    )
    providers_used = sorted(
        {
            str(group.get("provider") or "").strip()
            for group in finalized_groups
            if _group_label(group) in attempted_labels and str(group.get("provider") or "").strip()
        }
    )
    summary_provider = resolved_provider
    if len(providers_used) == 1:
        summary_provider = providers_used[0]
    elif len(providers_used) > 1:
        summary_provider = "mixed"

    return {
        "enabled": True,
        "provider": summary_provider,
        "providers_used": providers_used,
        "workers": max_workers,
        "attempted_groups": dispatched,
        "response_files_written": written,
        "failure_count": failures,
        "dispatch_scope_labels": sorted(candidate_labels),
        "settled_group_labels": settled_group_labels,
        "pending_scope_labels": pending_scope_labels,
        "same_pass_promoted_labels": same_pass_promoted_labels,
        "settle_passes": settle_passes,
        "settle_launch_sequence": list(settle_launch_sequence),
        "quiescent": not pending_scope_labels,
        "groups": finalized_groups,
    }


def run_once(
    *,
    repo_root: Path,
    plan_path: Path,
    result_path: Path,
    history_dir: Path,
    sentence_count: Optional[int],
    sticky_dump_dir: bool,
    bridge_enabled: bool,
    bridge_provider: Optional[str],
    bridge_max_chars: int,
    bridge_timeout_s: float,
    bridge_workers: Any,
    launch_profile: Optional[str] = None,
    launch_metadata: Optional[Dict[str, Any]] = None,
    resume_observe_id: Optional[str] = None,
    retry_group_labels: Optional[List[str]] = None,
    run_kind: Optional[str] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Execute one grouped observe-plan run from validated plan JSON through result/history artifact emission.
    - Mechanism: Load and preflight the plan, normalize routing and sticky dump policy, invoke tools.meta.apply observe mode, then continue through grouped bridge/runtime handling and result-note/history persistence.
    - Reads: plan_path, referenced route configuration, prompt/runtime policy, optional resume metadata, and tools.meta.apply observe-mode outputs.
    - Writes: result_path, history_dir, grouped dump/response artifacts, runtime manifests, and resume/continuation sidecars derived from the run.
    - Guarantee: Returns the final run summary dict written by the grouped observe pipeline after successful preflight and execution.
    - Fails: Raises RuntimeError on preflight, route-validation, or observe-mode failures and propagates later grouped runtime exceptions.
    - When-needed: Open when you need the authoritative grouped observe execution path from plan file to result JSON, especially for bridge-enabled runs and resume-aware retries.
    - When-needed: Open when diagnosing bridge prompt truncation or sizing behavior; `bridge_max_chars` flows from here into per-group budget resolution.
    - Escalates-to: tools/meta/apply/observe_session.py::MetaSessionOrchestratorImpl.run; tools/meta/apply/observe_session_runner.py::run_session_once.
    - Navigation-group: observe_apply.
    """
    plan = _read_json(plan_path)

    # --- Preflight validation: reject broken plans before dispatch ---
    preflight = preflight_observe_plan(
        repo_root,
        plan,
        bridge_enabled=bridge_enabled,
        launch_metadata=launch_metadata,
        bridge_provider=bridge_provider,
        bridge_workers=bridge_workers,
    )
    if not preflight["ok"]:
        raise RuntimeError(
            "Observe plan preflight failed:\n  " + "\n  ".join(preflight["errors"])
        )

    route_errors, route_warnings = validate_route_payload(plan, repo_root=repo_root)
    if route_errors:
        raise RuntimeError("Observe plan route validation failed: " + "; ".join(route_errors))
    sticky_summary = _apply_sticky_dump_dir_policy(
        repo_root=repo_root,
        plan=plan,
        sticky_enabled=sticky_dump_dir,
    )
    from system.lib.observe_plan_enrichment import enrich_observe_plan_dict

    enrich_observe_plan_dict(repo_root, plan)
    route_config = normalize_route_config(plan)
    # If no explicit result_note_path, infer from context_files phase directory
    if not route_config.get("result_note_path"):
        from tools.meta.apply.observe_session import _infer_phase_dir_from_context_files
        context_files = plan.get("context_files", [])
        if isinstance(context_files, list):
            phase_dir = _infer_phase_dir_from_context_files(context_files)
            if phase_dir:
                round_idx = plan.get("round_index") or 1
                route_config["result_note_path"] = f"{phase_dir}/Pass {round_idx} Observe Result.md"
    route_config["result_note_path"] = normalize_repo_relative_path(
        route_config.get("result_note_path"),
        repo_root=repo_root,
    )
    route_config["promotion_target_path"] = normalize_repo_relative_path(
        route_config.get("promotion_target_path"),
        repo_root=repo_root,
    )
    resolved_reference_maps, _, _ = resolve_reference_maps(
        plan.get("reference_maps"),
        repo_root=repo_root,
    )
    meta_apply = _load_apply_module(repo_root)

    config = {
        "mode": "observe",
        "root_hint": str(repo_root),
        "plan": plan,
    }
    envelope = meta_apply.run(config)
    if envelope.get("metadata", {}).get("status") != "success":
        raise RuntimeError(f"Observe run failed: {envelope.get('metadata', {}).get('error', 'unknown error')}")

    data = envelope.get("data", {})
    meta = data.get("__meta", {})
    manifest = data.get("manifest", [])
    mode = meta.get("mode", "standard_observe")
    plan_notes = str(meta.get("plan_notes") or plan.get("notes") or "").strip()
    wait_notes = str(meta.get("wait_notes") or plan.get("wait_notes") or plan.get("notes") or "").strip()
    prompt_style = str(meta.get("prompt") or plan.get("prompt") or "").strip()
    sentence_cap_active = sentence_count is not None and sentence_count > 0
    prompt_clear = (
        f"Use exactly {sentence_count} sentences per group prompt; cite file path + symbol/section anchor; "
        "no broad sweeps; no fixes unless explicitly requested."
        if sentence_cap_active
        else "No sentence cap enforced; preserve full instruction detail and cite file path + symbol/section anchor."
    )
    launch_metadata = dict(launch_metadata or {})
    launch_metadata.setdefault("pid", None)

    groups_payload: List[Dict[str, Any]] = []
    prompt_catalog = _load_prompt_catalog_for_repo(repo_root)
    prompt_meta = prompt_contract_metadata(prompt_style, prompt_catalog)
    goal_question = str(plan.get("goal_question", "")).strip()
    success_criteria = str(plan.get("success_criteria", "")).strip()
    if mode == "grouped_observe" and isinstance(manifest, list):
        plan_context_files = [
            str(item).strip()
            for item in (plan.get("context_files") or [])
            if str(item).strip()
        ] if isinstance(plan.get("context_files", []), list) else []
        context_merge_mode = normalize_context_merge_mode(plan.get("context_merge_mode"))
        notes_by_label = {}
        roles_by_label = {}
        questions_by_label = {}
        acceptance_by_label = {}
        output_contract_by_label: Dict[str, List[str]] = {}
        response_surface_by_label: Dict[str, Any] = {}
        downstream_by_label = {}
        context_files_by_label: Dict[str, List[str]] = {}
        context_overlaps_by_label: Dict[str, List[str]] = {}
        targets_by_label: Dict[str, List[Dict[str, Any]]] = {}
        sibling_roster_by_label: Dict[str, List[str]] = {}
        incoming_queries_by_label: Dict[str, List[Dict[str, Any]]] = {}
        depends_on_by_label: Dict[str, List[str]] = {}
        json_only_by_label: Dict[str, bool] = {}
        schema_by_label: Dict[str, Dict[str, Any]] = {}
        standards_by_label: Dict[str, Dict[str, Any]] = {}
        for group in plan.get("groups", []):
            if isinstance(group, dict):
                label = str(group.get("label", ""))
                notes_by_label[label] = str(group.get("notes", "")).strip()
                roles_by_label[label] = str(group.get("role", "probe")).strip() or "probe"
                questions_by_label[label] = str(group.get("question", "")).strip()
                acceptance_by_label[label] = str(group.get("acceptance", "")).strip()
                output_contract_by_label[label] = _coerce_output_contract(group.get("output_contract"))
                response_surface_by_label[label] = copy.deepcopy(group.get("response_surface"))
                downstream_by_label[label] = str(group.get("downstream_consumer", "")).strip()
                targets_by_label[label] = [
                    copy.deepcopy(item)
                    for item in group.get("targets", [])
                    if isinstance(item, Mapping)
                ] if isinstance(group.get("targets", []), list) else []
                evidence_contract = resolve_group_evidence_contract(
                    repo_root,
                    plan_context_files=plan_context_files,
                    group_context_files=group.get("context_files", []),
                    targets=targets_by_label[label],
                    context_merge_mode=context_merge_mode,
                )
                context_files_by_label[label] = list(evidence_contract["effective_context_files"])
                context_overlaps_by_label[label] = list(evidence_contract["context_target_overlaps"])
                sibling_roster_by_label[label] = [
                    str(item).strip()
                    for item in group.get("sibling_scope_roster", [])
                    if str(item).strip()
                ] if isinstance(group.get("sibling_scope_roster", []), list) else []
                incoming_queries_by_label[label] = [
                    dict(item)
                    for item in group.get("incoming_queries", [])
                    if isinstance(item, Mapping)
                ] if isinstance(group.get("incoming_queries", []), list) else []
                depends_on_by_label[label] = [
                    str(item).strip()
                    for item in group.get("depends_on", [])
                    if str(item).strip()
                ] if isinstance(group.get("depends_on", []), list) else []
                standards_by_label[label] = (
                    copy.deepcopy(group.get("standards"))
                    if isinstance(group.get("standards"), Mapping)
                    else {}
                )
                grp_schema = group.get("response_schema") if isinstance(group.get("response_schema"), Mapping) else None
                json_only_by_label[label] = bool(group.get("json_only")) and grp_schema is not None
                if grp_schema is not None:
                    schema_by_label[label] = copy.deepcopy(grp_schema)
        for item in manifest:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "group"))
            files = [str(v) for v in item.get("files", []) if isinstance(v, str)]
            resolved_context_files = [
                str(v).strip()
                for v in item.get("context_files", [])
                if str(v).strip()
            ] if isinstance(item.get("context_files"), list) else list(context_files_by_label.get(label, []))
            resolved_context_overlaps = [
                str(v).strip()
                for v in item.get("context_target_overlaps", [])
                if str(v).strip()
            ] if isinstance(item.get("context_target_overlaps"), list) else list(context_overlaps_by_label.get(label, []))
            resolved_targets = copy.deepcopy(targets_by_label.get(label)) or [
                {"file": path, "scope": "full"}
                for path in files
            ]
            group_prompt = _build_group_prompt(
                label=label,
                role=roles_by_label.get(label, "probe"),
                notes=notes_by_label.get(label, ""),
                files=files,
                context_files=resolved_context_files,
                depends_on=depends_on_by_label.get(label, []),
                wait_notes=wait_notes,
                prompt_style=prompt_style,
                goal_question=goal_question,
                success_criteria=success_criteria,
                group_question=questions_by_label.get(label, ""),
                acceptance=acceptance_by_label.get(label, ""),
                response_mode=_resolve_response_mode(prompt_meta),
                sentence_count=sentence_count,
                json_only=json_only_by_label.get(label, False),
            )
            groups_payload.append(
                {
                    "index": item.get("index"),
                    "label": label,
                    "role": roles_by_label.get(label, "probe"),
                    "file_count": int(item.get("file_count", len(files))),
                    "dump_file": item.get("dump_file"),
                    "prompt": group_prompt,
                    "prompt_key": prompt_meta.get("key"),
                    "prompt_metadata": dict(prompt_meta),
                    "question": questions_by_label.get(label) or None,
                    "acceptance": acceptance_by_label.get(label) or None,
                    "output_contract": output_contract_by_label.get(label, []),
                    "response_surface": response_surface_by_label.get(label),
                    "downstream_consumer": downstream_by_label.get(label) or None,
                    "context_files": resolved_context_files,
                    "context_target_overlaps": resolved_context_overlaps,
                    "targets": resolved_targets,
                    "sibling_scope_roster": sibling_roster_by_label.get(label, []),
                    "incoming_queries": incoming_queries_by_label.get(label, []),
                    "depends_on": depends_on_by_label.get(label, []),
                    "standards": standards_by_label.get(label, {}),
                    "response_schema": schema_by_label.get(label),
                    "json_only": json_only_by_label.get(label, False) or None,
                    "sentence_count": _sentence_count(group_prompt),
                }
            )
    else:
        targets = plan.get("targets", [])
        standard_prompt = _build_standard_prompt(
            target_count=len(targets) if isinstance(targets, list) else 0,
            wait_notes=wait_notes,
            prompt_style=prompt_style,
            sentence_count=sentence_count,
        )
        groups_payload.append(
            {
                "index": 1,
                "label": "standard_observe",
                "role": "probe",
                "file_count": len(targets) if isinstance(targets, list) else 0,
                "dump_file": None,
                "prompt": standard_prompt,
                "depends_on": [],
                "standards": copy.deepcopy(plan.get("standards")) if isinstance(plan.get("standards"), Mapping) else {},
                "sentence_count": _sentence_count(standard_prompt),
            }
        )

    grouped_contract_errors = _grouped_observe_contract_errors(groups_payload) if mode == "grouped_observe" else []
    if grouped_contract_errors:
        raise ValueError("; ".join(grouped_contract_errors))

    dumps_prompt_injected = _inject_prompts_into_group_dumps(
        repo_root=repo_root,
        groups_payload=groups_payload,
        sentence_count=sentence_count,
    )

    history_dir.mkdir(parents=True, exist_ok=True)
    entries_dir = history_dir / "entries"
    prompts_dir = history_dir / "prompts"
    entries_dir.mkdir(parents=True, exist_ok=True)
    prompts_dir.mkdir(parents=True, exist_ok=True)

    seed = json.dumps(
        {
            "plan_path": str(plan_path),
            "timestamp": envelope.get("metadata", {}).get("timestamp"),
            "groups": [g.get("label") for g in groups_payload],
        },
        sort_keys=True,
    )
    observe_id = str(resume_observe_id or _obs_id(seed)).strip()
    timeline_rel: Optional[str] = None
    timeline_path: Optional[Path] = None
    timeline_lock = threading.Lock()
    dump_dir_for_timeline = str(meta.get("dump_dir") or plan.get("dump_dir") or "").strip()
    if dump_dir_for_timeline:
        timeline_path = observe_cycle_timeline_path(repo_root, dump_dir_for_timeline)
        try:
            timeline_rel = str(timeline_path.relative_to(repo_root))
        except ValueError:
            timeline_rel = str(timeline_path)

    def _emit_cycle_event(event: str, **fields: Any) -> None:
        if timeline_path is None:
            return
        payload = {
            "timestamp": _now_iso(),
            "observe_id": observe_id,
            "event": event,
            "mode": mode,
            "phase": str(plan.get("phase") or "").strip() or None,
            "round_index": plan.get("round_index"),
        }
        payload.update(fields)
        with timeline_lock:
            append_jsonl(timeline_path, payload)

    runtime_manifest = load_grouped_runtime_manifest(repo_root, history_dir, observe_id)
    groups_payload = _merge_runtime_group_state(
        repo_root=repo_root,
        fresh_groups=groups_payload,
        runtime_manifest=runtime_manifest,
        recover_response_artifacts=bool(resume_observe_id),
        retry_group_labels=retry_group_labels,
    )
    waves, wave_by_label = grouped_observe_waves(groups_payload)
    for group in groups_payload:
        label = str(group.get("label") or "").strip()
        group["wave_index"] = int(wave_by_label.get(label, 0))
        group["runtime_state"] = _resolved_group_runtime_state(group)

    runtime_policy = observe_runtime_policy(repo_root)
    launch_profile = normalize_launch_profile(launch_profile, default=str(runtime_policy["default_launch_profile"]))
    requested_workers = str(bridge_workers or "auto").strip() or "auto"
    stagger_ms = int(
        runtime_policy["experimental_launch_stagger_ms"]
        if launch_profile == "experimental"
        else runtime_policy["safe_launch_stagger_ms"]
    )

    pending_waves = [
        wave
        for index, wave in enumerate(waves)
        if any(
            _resolved_group_runtime_state(group) not in TERMINAL_GROUP_STATUSES
            for group in groups_payload
            if str(group.get("label") or "").strip() in set(wave)
        )
    ]
    next_wave_labels = pending_waves[0] if pending_waves else []
    dispatch_labels = [
        str(group.get("label") or "").strip()
        for group in groups_payload
        if str(group.get("label") or "").strip() in set(next_wave_labels)
        and _resolved_group_runtime_state(group) not in TERMINAL_GROUP_STATUSES
    ]
    dispatch_scope_labels = _expand_dispatch_scope_labels(groups_payload, dispatch_labels)
    worker_resolution = resolve_effective_workers(
        repo_root=repo_root,
        requested_workers=requested_workers,
        launch_profile=launch_profile,
        wave_size=max(1, len(dispatch_scope_labels) or len(dispatch_labels) or len(groups_payload) or 1),
        provider=bridge_provider or plan.get("bridge_provider") or plan.get("provider"),
    )
    effective_workers = int(worker_resolution["effective_workers"])
    current_wave_index = int(wave_by_label.get(next_wave_labels[0], len(waves))) if next_wave_labels else len(waves)
    last_executed_wave_index = max(0, len(waves) - 1) if waves and not next_wave_labels else max(0, current_wave_index)
    entry_path = entries_dir / f"{observe_id}.json"
    entry_rel = str(entry_path.relative_to(repo_root))
    prompts_md_path = prompts_dir / f"{observe_id}.md"
    started_at = str(runtime_manifest.get("started_at") or now_iso()).strip() or now_iso()
    artifacts_payload: Dict[str, Any] = {
        "history_entry": entry_rel,
        "result_file": str(result_path.relative_to(repo_root)),
        "prompts_file": str(prompts_md_path.relative_to(repo_root)),
        "plan_file": str(plan_path.relative_to(repo_root)) if str(plan_path).startswith(str(repo_root)) else str(plan_path),
        "cycle_timeline": timeline_rel,
    }
    plan_standards = plan.get("standards") if isinstance(plan.get("standards"), Mapping) else {}
    if plan_standards:
        artifacts_payload["standards_authority_index"] = str(plan_standards.get("authority_index") or "").strip() or None
        artifacts_payload["standards_matched_artifact_kinds"] = [
            str(item).strip()
            for item in (plan_standards.get("matched_artifact_kinds") or [])
            if str(item).strip()
        ]
        artifacts_payload["standards_context_files"] = [
            str(item).strip()
            for item in (plan_standards.get("context_files") or [])
            if str(item).strip()
        ]
    prompts_md_lines = [
        "# Observe Group Prompts",
        "",
        f"- observe_id: `{observe_id}`",
        f"- prompt_sentence_requirement: `{sentence_count if sentence_cap_active else 'none'}`",
        f"- prompt_clear: {prompt_clear}",
        "",
    ]
    for group in groups_payload:
        prompts_md_lines.extend(
            [
                f"## {group.get('label')}",
                f"- sentence_count: {group.get('sentence_count')}",
                f"- dump_file: `{group.get('dump_file')}`",
                f"- question: {group.get('question') or '_none_'}",
                f"- acceptance: {group.get('acceptance') or '_none_'}",
                f"- output_contract: `{', '.join(group.get('output_contract', [])) or 'none'}`",
                f"- downstream_consumer: {group.get('downstream_consumer') or '_none_'}",
                f"- response_mode: `{group.get('prompt_response_mode') or group.get('prompt_metadata', {}).get('response_mode') or 'structured_sections'}`",
                "",
                group.get("prompt", ""),
                "",
            ]
        )
    prompts_md_path.write_text("\n".join(prompts_md_lines), encoding="utf-8")

    bridge_summary: Dict[str, Any]
    if cancel_event is None:
        cancel_event = threading.Event()
    # Link to global cancel from signal handler if present
    if _GLOBAL_CANCEL_EVENT is not None and _GLOBAL_CANCEL_EVENT.is_set():
        cancel_event.set()
    cancel_watch_stop = threading.Event()
    cancel_watcher: Optional[threading.Thread] = None
    cancel_requested_at = str(runtime_manifest.get("cancel_requested_at") or "").strip() or None
    if resume_observe_id and cancel_requested_at:
        cancel_requested_at = None
    checkpoint_lock = threading.Lock()

    def _provisional_continuation(current_groups: List[Dict[str, Any]]) -> Dict[str, Any]:
        continuation = build_grouped_observe_continuation(
            result_note_rel=None,
            synthesis_summary={},
            groups_payload=current_groups,
        )
        if continuation.get("read_paths"):
            return continuation
        return {
            **continuation,
            "next_action": (
                f"On continue, read `{str(meta.get('dump_dir') or plan.get('dump_dir') or 'the dump index')}` first, "
                "then reopen only the relevant grouped dump or stored response."
            ),
            "source": "dump_index",
        }

    def _write_provisional_history_entry(
        *,
        current_groups: List[Dict[str, Any]],
        current_state: str,
        current_wave_index: int,
        current_effective_workers: int,
        current_failure_count: int,
    ) -> None:
        continuation_summary = _provisional_continuation(current_groups)
        output_source = "bridge_responses" if any(str(group.get("response_file", "")).strip() for group in current_groups) else "dump_refs_only"
        provisional_payload: Dict[str, Any] = {
            "__meta": {
                "schema_version": "2.0.0",
                "generated_at": _now_iso(),
                "id": observe_id,
                "runner": "tools/meta/apply/run_observe_plan.py",
            },
            "observe_id": observe_id,
            "mode": mode,
            "goal_question": goal_question or None,
            "success_criteria": success_criteria or None,
            "result_file": str(result_path.relative_to(repo_root)),
            "plan_file": str(plan_path.relative_to(repo_root)) if str(plan_path).startswith(str(repo_root)) else str(plan_path),
            "dump_dir": meta.get("dump_dir"),
            "total_groups": int(meta.get("total_groups", len(current_groups))),
            "total_files": int(meta.get("total_files", sum(int(g.get("file_count", 0)) for g in current_groups))),
            "wait_notes": wait_notes,
            "prompt_style": prompt_style,
            "prompt_clear": prompt_clear,
            "prompt_sentence_requirement": sentence_count if sentence_cap_active else None,
            "route_warnings": route_warnings,
            "group_dumps_prompt_injected": dumps_prompt_injected,
            "sticky_dump_dir": sticky_summary,
            "launch_command": launch_metadata.get("launch_command"),
            "log_file": launch_metadata.get("log_file"),
            "launch_receipt": dict(launch_metadata.get("launch_receipt") or {}),
            "bridge_provider_requested": launch_metadata.get("bridge_provider_requested"),
            "bridge_provider_used": launch_metadata.get("bridge_provider_used"),
            "preflight_ran": launch_metadata.get("preflight_ran"),
            "preflight_status": launch_metadata.get("preflight_status"),
            "preflight": launch_metadata.get("preflight"),
            "bridge": {
                "enabled": bool(bridge_enabled),
                "provider": launch_metadata.get("bridge_provider_used") or launch_metadata.get("bridge_provider_requested"),
                "attempted_groups": sum(
                    1
                    for group in current_groups
                    if str(group.get("response_file", "")).strip()
                    or _resolved_group_runtime_state(group) in TERMINAL_GROUP_STATUSES
                ),
                "response_files_written": sum(1 for group in current_groups if str(group.get("response_file", "")).strip()),
                "failure_count": int(current_failure_count),
                "workers": int(max(1, current_effective_workers)),
                "requested_workers": requested_workers,
                "launch_profile": launch_profile,
                "stagger_ms": stagger_ms if bridge_enabled else None,
                "max_dump_chars": (None if bridge_max_chars <= 0 else bridge_max_chars) if bridge_enabled else None,
                "timeout_s": bridge_timeout_s if bridge_enabled else None,
            },
            "result_note": {
                "declared": bool(route_config.get("result_note_path")),
                "path": None,
                "kind": route_config.get("result_note_kind") if route_config.get("result_note_path") else None,
                "created": False,
                "promotion_payload_section": "Promotion Payload" if route_config.get("result_note_path") else None,
                "output_source": output_source,
            },
            "reference_maps": {
                "declared": list(route_config.get("reference_maps", [])),
                "resolved": resolved_reference_maps,
            },
            "promotion": {
                "declared": bool(route_config.get("promotion_target_path")),
                "target_path": route_config.get("promotion_target_path"),
                "mode": route_config.get("promotion_mode"),
                "section": route_config.get("promotion_section"),
                "gate": route_config.get("promotion_gate"),
                "status": "not_requested",
                "error": None,
                "source_artifact": None,
            },
            "run_next_action": str(continuation_summary.get("next_action") or "").strip() or None,
            "run_latest_artifact": str(continuation_summary.get("latest_artifact") or "").strip() or None,
            "runtime": {
                "state": current_state,
                "launch_profile": launch_profile,
                "requested_workers": requested_workers,
                "effective_workers": int(max(1, current_effective_workers)),
                "wave_index": current_wave_index,
                "wave_total": len(waves),
                "cancel_requested_at": cancel_requested_at,
                "pid": launch_metadata.get("pid"),
            },
            "continuation": continuation_summary,
            "groups": current_groups,
        }
        _write_json(entry_path, provisional_payload)

    def _checkpoint_group_dispatch(dispatched_group: Dict[str, Any], *, workers_value: int) -> None:
        nonlocal groups_payload
        with checkpoint_lock:
            target_label = str(dispatched_group.get("label") or "").strip()
            updated_groups: List[Dict[str, Any]] = []
            for existing_group in groups_payload:
                if str(existing_group.get("label") or "").strip() == target_label:
                    merged_group = dict(existing_group)
                    merged_group.update(dispatched_group)
                    merged_group["runtime_state"] = _resolved_group_runtime_state(merged_group)
                    updated_groups.append(merged_group)
                else:
                    updated_groups.append(dict(existing_group))
            groups_payload = updated_groups
            checkpoint_wave_index = _earliest_nonterminal_wave_index(
                groups_payload,
                wave_by_label,
                default=current_wave_index if waves else 0,
            )
            checkpoint_runtime = _build_grouped_runtime_manifest(
                repo_root=repo_root,
                history_dir=history_dir,
                observe_id=observe_id,
                launch_profile=launch_profile,
                requested_workers=requested_workers,
                effective_workers=workers_value,
                wave_index=checkpoint_wave_index,
                wave_total=len(waves),
                state="dispatching",
                groups_payload=groups_payload,
                artifacts=artifacts_payload,
                launch_metadata=launch_metadata,
                cancel_requested_at=cancel_requested_at,
                started_at=started_at,
            )
            write_grouped_runtime_manifest(history_dir, checkpoint_runtime)
            _write_provisional_history_entry(
                current_groups=groups_payload,
                current_state="dispatching",
                current_wave_index=checkpoint_wave_index,
                current_effective_workers=workers_value,
                current_failure_count=sum(
                    1
                    for group in groups_payload
                    if str(group.get("response_status", "")).strip() in {"error", "quality_error"}
                ),
            )
            _emit_cycle_event(
                "group_dispatch_started",
                group_label=target_label,
                role=str(dispatched_group.get("role") or "").strip() or None,
                wave_index=int(wave_by_label.get(target_label, checkpoint_wave_index)),
                runtime_state=str(dispatched_group.get("runtime_state") or "").strip() or None,
            )

    def _checkpoint_group_completion(completed_group: Dict[str, Any], *, workers_value: int) -> None:
        nonlocal groups_payload
        with checkpoint_lock:
            target_label = str(completed_group.get("label") or "").strip()
            updated_groups: List[Dict[str, Any]] = []
            for existing_group in groups_payload:
                if str(existing_group.get("label") or "").strip() == target_label:
                    merged_group = dict(existing_group)
                    merged_group.update(completed_group)
                    merged_group["runtime_state"] = _resolved_group_runtime_state(merged_group)
                    updated_groups.append(merged_group)
                else:
                    updated_groups.append(dict(existing_group))
            groups_payload = updated_groups
            checkpoint_wave_index = _earliest_nonterminal_wave_index(
                groups_payload,
                wave_by_label,
                default=current_wave_index if waves else 0,
            )
            failure_count = sum(
                1
                for group in groups_payload
                if str(group.get("response_status", "")).strip() in {"error", "quality_error"}
            )
            checkpoint_runtime = _build_grouped_runtime_manifest(
                repo_root=repo_root,
                history_dir=history_dir,
                observe_id=observe_id,
                launch_profile=launch_profile,
                requested_workers=requested_workers,
                effective_workers=workers_value,
                wave_index=checkpoint_wave_index,
                wave_total=len(waves),
                state="dispatching",
                groups_payload=groups_payload,
                artifacts=artifacts_payload,
                launch_metadata=launch_metadata,
                cancel_requested_at=cancel_requested_at,
                started_at=started_at,
            )
            write_grouped_runtime_manifest(history_dir, checkpoint_runtime)
            _write_provisional_history_entry(
                current_groups=groups_payload,
                current_state="dispatching",
                current_wave_index=checkpoint_wave_index,
                current_effective_workers=workers_value,
                current_failure_count=failure_count,
            )
            _emit_cycle_event(
                "group_completed",
                group_label=target_label,
                role=str(completed_group.get("role") or "").strip() or None,
                wave_index=int(wave_by_label.get(target_label, checkpoint_wave_index)),
                response_status=str(completed_group.get("response_status") or "").strip() or None,
                runtime_state=str(completed_group.get("runtime_state") or "").strip() or None,
                provider=str(completed_group.get("provider") or "").strip() or None,
                prompt_chars=completed_group.get("response_prompt_chars"),
                response_file=str(completed_group.get("response_file") or "").strip() or None,
                response_receipt_file=str(completed_group.get("response_receipt_file") or "").strip() or None,
                error_category=str(completed_group.get("response_error_category") or "").strip() or None,
                error_stage=str(completed_group.get("response_error_stage") or "").strip() or None,
            )

    try:
        initial_runtime_state = "dispatching"
        if not bridge_enabled or not dispatch_labels:
            initial_runtime_state = "completed" if not next_wave_labels else "compiled"
        runtime_payload = _build_grouped_runtime_manifest(
            repo_root=repo_root,
            history_dir=history_dir,
            observe_id=observe_id,
            launch_profile=launch_profile,
            requested_workers=requested_workers,
            effective_workers=effective_workers,
            wave_index=current_wave_index,
            wave_total=len(waves),
            state=initial_runtime_state,
            groups_payload=groups_payload,
            artifacts=artifacts_payload,
            launch_metadata=launch_metadata,
            cancel_requested_at=cancel_requested_at,
            started_at=started_at,
        )
        write_grouped_runtime_manifest(history_dir, runtime_payload)
        _emit_cycle_event(
            "observe_runtime_initialized",
            runtime_state=initial_runtime_state,
            launch_profile=launch_profile,
            requested_workers=requested_workers,
            effective_workers=effective_workers,
            wave_index=current_wave_index,
            wave_total=len(waves),
            next_wave_labels=list(dispatch_labels),
            bridge_enabled=bool(bridge_enabled),
            cycle_timeline=timeline_rel,
        )
        _write_provisional_history_entry(
            current_groups=groups_payload,
            current_state=initial_runtime_state,
            current_wave_index=current_wave_index,
            current_effective_workers=effective_workers,
            current_failure_count=0,
        )

        if bridge_enabled and dispatch_labels:
            cancel_watcher = _start_cancel_watcher(
                repo_root=repo_root,
                history_dir=history_dir,
                observe_id=observe_id,
                cancel_event=cancel_event,
                stop_event=cancel_watch_stop,
            )
            bridge_summary = {
                "enabled": True,
                "provider": None,
                "attempted_groups": 0,
                "response_files_written": 0,
                "failure_count": 0,
                "workers": effective_workers,
                "launch_profile": launch_profile,
                "requested_workers": requested_workers,
                "wave_index": current_wave_index,
                "wave_total": len(waves),
                "stagger_ms": stagger_ms,
                "dispatch_scope_labels": sorted(dispatch_scope_labels),
                "settled_group_labels": [],
                "pending_scope_labels": sorted(dispatch_scope_labels),
                "same_pass_promoted_labels": [],
                "settle_passes": 0,
                "settle_launch_sequence": [],
                "quiescent": not dispatch_scope_labels,
                "groups": groups_payload,
            }
            dispatch_set = set(dispatch_labels)
            for group in groups_payload:
                label = str(group.get("label") or "").strip()
                if label in dispatch_set:
                    group["runtime_state"] = "running"
            runtime_payload = _build_grouped_runtime_manifest(
                repo_root=repo_root,
                history_dir=history_dir,
                observe_id=observe_id,
                launch_profile=launch_profile,
                requested_workers=requested_workers,
                effective_workers=effective_workers,
                wave_index=current_wave_index,
                wave_total=len(waves),
                state="dispatching",
                groups_payload=groups_payload,
                artifacts=artifacts_payload,
                launch_metadata=launch_metadata,
                cancel_requested_at=cancel_requested_at,
                started_at=started_at,
            )
            write_grouped_runtime_manifest(history_dir, runtime_payload)
            _emit_cycle_event(
                "wave_dispatch_started",
                wave_index=current_wave_index,
                wave_labels=list(dispatch_labels),
                dispatch_scope_labels=sorted(dispatch_scope_labels),
                effective_workers=effective_workers,
                requested_workers=requested_workers,
                launch_profile=launch_profile,
            )
            wave_summary = _dispatch_groups_to_bridge(
                repo_root=repo_root,
                observe_id=observe_id,
                groups_payload=groups_payload,
                plan_path=plan_path,
                bridge_provider=bridge_provider,
                bridge_max_chars=bridge_max_chars,
                bridge_timeout_s=bridge_timeout_s,
                bridge_workers=effective_workers,
                launch_profile=launch_profile,
                stagger_ms=stagger_ms,
                target_labels=list(dispatch_labels),
                run_kind=run_kind,
                cancel_event=cancel_event,
                on_group_dispatch=lambda dispatched_group, workers_value=effective_workers: _checkpoint_group_dispatch(
                    dispatched_group,
                    workers_value=workers_value,
                ),
                on_group_complete=lambda completed_group, workers_value=effective_workers: _checkpoint_group_completion(
                    completed_group,
                    workers_value=workers_value,
                ),
            )
            groups_payload = wave_summary.get("groups", groups_payload)
            for group in groups_payload:
                if not isinstance(group, dict):
                    continue
                group["runtime_state"] = _resolved_group_runtime_state(group)
            _resolve_blocked_groups(groups_payload)
            last_executed_wave_index = _earliest_nonterminal_wave_index(
                groups_payload,
                wave_by_label,
                default=current_wave_index,
            )
            bridge_summary["provider"] = wave_summary.get("provider")
            bridge_summary["attempted_groups"] = int(wave_summary.get("attempted_groups", 0))
            bridge_summary["response_files_written"] = int(wave_summary.get("response_files_written", 0))
            bridge_summary["failure_count"] = int(wave_summary.get("failure_count", 0))
            bridge_summary["groups"] = groups_payload
            bridge_summary["wave_index"] = last_executed_wave_index
            bridge_summary["dispatch_scope_labels"] = list(wave_summary.get("dispatch_scope_labels") or [])
            bridge_summary["settled_group_labels"] = list(wave_summary.get("settled_group_labels") or [])
            bridge_summary["pending_scope_labels"] = list(wave_summary.get("pending_scope_labels") or [])
            bridge_summary["same_pass_promoted_labels"] = list(wave_summary.get("same_pass_promoted_labels") or [])
            bridge_summary["settle_passes"] = int(wave_summary.get("settle_passes", 0) or 0)
            bridge_summary["settle_launch_sequence"] = list(wave_summary.get("settle_launch_sequence") or [])
            bridge_summary["quiescent"] = bool(wave_summary.get("quiescent", False))
            _emit_cycle_event(
                "wave_dispatch_completed",
                wave_index=current_wave_index,
                wave_labels=list(dispatch_labels),
                dispatch_scope_labels=sorted(dispatch_scope_labels),
                attempted_groups=int(wave_summary.get("attempted_groups", 0)),
                response_files_written=int(wave_summary.get("response_files_written", 0)),
                failure_count=int(wave_summary.get("failure_count", 0)),
                provider=str(wave_summary.get("provider") or "").strip() or None,
            )
            cancel_requested_at = str(
                load_grouped_runtime_manifest(repo_root, history_dir, observe_id).get("cancel_requested_at") or cancel_requested_at or ""
            ).strip() or None
        else:
            bridge_summary = {
                "enabled": bool(bridge_enabled),
                "provider": None,
                "attempted_groups": 0,
                "response_files_written": 0,
                "failure_count": 0,
                "workers": effective_workers,
                "launch_profile": launch_profile,
                "requested_workers": requested_workers,
                "wave_index": current_wave_index,
                "wave_total": len(waves),
                "stagger_ms": stagger_ms,
                "dispatch_scope_labels": sorted(dispatch_scope_labels),
                "settled_group_labels": [],
                "pending_scope_labels": sorted(dispatch_scope_labels),
                "same_pass_promoted_labels": [],
                "settle_passes": 0,
                "settle_launch_sequence": [],
                "quiescent": not dispatch_scope_labels,
                "groups": groups_payload,
            }
    finally:
        cancel_watch_stop.set()
        if cancel_watcher is not None:
            cancel_watcher.join(timeout=1.0)
        # Close bridge tabs so they don't dangle after the run
        try:
            from system.core.bridge import close as _bridge_close
            _bridge_close(terminate_browser=False)
        except Exception:
            pass

    dump_prompt_artifacts = _ensure_grouped_dump_prompt_artifacts(
        repo_root=repo_root,
        plan=plan,
        observe_meta=meta,
        groups_payload=groups_payload,
        wait_notes=wait_notes,
        prompt_style=prompt_style,
        plan_notes=plan_notes,
    )
    # --- Copy session-relevant bridge events into the dump folder ---
    bridge_log_artifact = _snapshot_bridge_log_to_dump(repo_root, observe_id, meta, plan)

    continuation_summary = _summarize_groups_continuation(groups_payload)
    generated_at = _now_iso()
    dump_dir_rel = str(meta.get("dump_dir") or plan.get("dump_dir") or "").strip() or None
    # --- Final state coercion: no group may remain in non-terminal state ---
    _resolve_blocked_groups(groups_payload)
    _coerce_reason = "cancelled" if cancel_event.is_set() else "session_finalized"
    _coerced_count = _coerce_pending_to_terminal(groups_payload, _coerce_reason)

    pending_groups = [
        group
        for group in groups_payload
        if _resolved_group_runtime_state(group) not in TERMINAL_GROUP_STATUSES
    ]
    remaining_waves = [
        wave
        for wave in waves
        if any(
            _resolved_group_runtime_state(group) not in TERMINAL_GROUP_STATUSES
            for group in groups_payload
            if str(group.get("label") or "").strip() in set(wave)
        )
    ]
    next_pending_wave_index = (
        int(wave_by_label.get(remaining_waves[0][0], last_executed_wave_index))
        if remaining_waves
        else (max(0, len(waves) - 1) if waves else 0)
    )
    if cancel_event.is_set():
        runtime_state = "aborted"
    elif int(bridge_summary.get("failure_count", 0) or 0) > 0:
        runtime_state = "error"
    elif pending_groups:
        runtime_state = "awaiting_review"
    else:
        runtime_state = "completed"
    if not bridge_enabled:
        runtime_state = "completed"
    if runtime_state == "awaiting_review":
        final_wave_index = next_pending_wave_index
    elif runtime_state == "completed":
        final_wave_index = max(0, len(waves) - 1) if waves else 0
    else:
        final_wave_index = max(0, min(last_executed_wave_index, max(0, len(waves) - 1))) if waves else 0
    bridge_summary["wave_index"] = final_wave_index
    group_quality_summary = _build_group_quality_summary(groups_payload)
    synthesis_summary = _synthesize_group_results(
        repo_root=repo_root,
        observe_id=observe_id,
        dump_dir=dump_dir_rel,
        groups_payload=groups_payload,
    )
    output_source = "bridge_responses" if any(str(group.get("response_file", "")).strip() for group in groups_payload) else "dump_refs_only"
    result_note_summary: Dict[str, Any] = {
        "declared": bool(route_config.get("result_note_path")),
        "path": None,
        "kind": route_config.get("result_note_kind") if route_config.get("result_note_path") else None,
        "created": False,
        "promotion_payload_section": "Promotion Payload" if route_config.get("result_note_path") else None,
        "output_source": output_source,
    }
    reference_maps_summary: Dict[str, Any] = {
        "declared": list(route_config.get("reference_maps", [])),
        "resolved": resolved_reference_maps,
    }
    promotion_summary: Dict[str, Any] = {
        "declared": False,
        "target_path": route_config.get("promotion_target_path"),
        "mode": route_config.get("promotion_mode"),
        "section": route_config.get("promotion_section"),
        "gate": route_config.get("promotion_gate"),
        "status": "not_requested",
        "error": None,
        "source_artifact": None,
    }
    if route_config.get("result_note_path"):
        result_note_rel = str(route_config["result_note_path"])
        result_note_path = (repo_root / result_note_rel).resolve()
        result_note_path.parent.mkdir(parents=True, exist_ok=True)
        group_outputs_markdown = _build_group_outputs_markdown(
            repo_root=repo_root,
            groups_payload=groups_payload,
            concatenate_group_outputs=bool(route_config.get("concatenate_group_outputs")),
        )
        provisional_note = _build_result_note_text(
            repo_root=repo_root,
            observe_id=observe_id,
            generated_at=generated_at,
            plan=plan,
            plan_path=plan_path,
            history_entry_rel=entry_rel,
            dump_dir=dump_dir_rel,
            groups_payload=groups_payload,
            route_config=route_config,
            reference_maps=resolved_reference_maps,
            group_outputs_markdown=group_outputs_markdown,
            promotion_summary=promotion_summary,
            bridge_enabled=bool(bridge_summary.get("enabled")),
            launch_metadata=launch_metadata,
            synthesis_summary=synthesis_summary,
            group_quality_summary=group_quality_summary,
            run_next_action=str(synthesis_summary.get("run_next_action", "")).strip(),
        )
        result_note_path.write_text(provisional_note, encoding="utf-8")
        promotion_payload = extract_section(provisional_note, "Promotion Payload") or ""
        promotion_summary = _execute_promotion(
            repo_root=repo_root,
            observe_id=observe_id,
            generated_at=generated_at,
            result_note_rel=result_note_rel,
            route_config=route_config,
            promotion_payload=promotion_payload,
        )
        final_note = _build_result_note_text(
            repo_root=repo_root,
            observe_id=observe_id,
            generated_at=generated_at,
            plan=plan,
            plan_path=plan_path,
            history_entry_rel=entry_rel,
            dump_dir=dump_dir_rel,
            groups_payload=groups_payload,
            route_config=route_config,
            reference_maps=resolved_reference_maps,
            group_outputs_markdown=group_outputs_markdown,
            promotion_summary=promotion_summary,
            bridge_enabled=bool(bridge_summary.get("enabled")),
            launch_metadata=launch_metadata,
            synthesis_summary=synthesis_summary,
            group_quality_summary=group_quality_summary,
            run_next_action=str(synthesis_summary.get("run_next_action", "")).strip(),
        )
        result_note_path.write_text(final_note, encoding="utf-8")
        result_note_summary.update(
            {
                "path": result_note_rel,
                "created": True,
            }
        )
        continuation_summary = _build_run_continuation(
            result_note_rel=result_note_rel,
            synthesis_summary=synthesis_summary,
            groups_payload=groups_payload,
        )
    elif synthesis_summary.get("created"):
        continuation_summary = _build_run_continuation(
            result_note_rel=None,
            synthesis_summary=synthesis_summary,
            groups_payload=groups_payload,
        )

    run_next_action = str(continuation_summary.get("next_action") or synthesis_summary.get("run_next_action") or "").strip() or None
    run_latest_artifact = str(continuation_summary.get("latest_artifact") or result_note_summary.get("path") or synthesis_summary.get("path") or "").strip() or None
    failure_stage = _group_failure_stage(groups_payload)
    operator_decisions_pending = list(
        dict.fromkeys(
            item
            for group in groups_payload
            for item in (group.get("operator_decisions_pending", []) if isinstance(group.get("operator_decisions_pending"), list) else [])
            if str(item).strip()
        )
    )
    agent_followups_pending = list(
        dict.fromkeys(
            item
            for group in groups_payload
            for item in (group.get("agent_followups_pending", []) if isinstance(group.get("agent_followups_pending"), list) else [])
            if str(item).strip()
        )
    )
    entry_payload = {
        "__meta": {
            "schema_version": "2.0.0",
            "generated_at": generated_at,
            "id": observe_id,
            "runner": "tools/meta/apply/run_observe_plan.py",
        },
        "observe_id": observe_id,
        "mode": mode,
        "goal_question": goal_question or None,
        "success_criteria": success_criteria or None,
        "result_file": str(result_path.relative_to(repo_root)),
        "plan_file": str(plan_path.relative_to(repo_root)) if str(plan_path).startswith(str(repo_root)) else str(plan_path),
        "dump_dir": meta.get("dump_dir"),
        "total_groups": int(meta.get("total_groups", len(groups_payload))),
        "total_files": int(meta.get("total_files", sum(int(g.get("file_count", 0)) for g in groups_payload))),
        "wait_notes": wait_notes,
        "prompt_style": prompt_style,
        "prompt_clear": prompt_clear,
        "prompt_sentence_requirement": sentence_count if sentence_cap_active else None,
        "route_warnings": route_warnings,
        "group_dumps_prompt_injected": dumps_prompt_injected,
        "dump_prompt_artifacts": dump_prompt_artifacts,
        "bridge_log_file": bridge_log_artifact,
        "sticky_dump_dir": sticky_summary,
        "launch_command": launch_metadata.get("launch_command"),
        "log_file": launch_metadata.get("log_file"),
        "launch_receipt": dict(launch_metadata.get("launch_receipt") or {}),
        "launch_dispatch": str(launch_metadata.get("launch_dispatch") or "").strip() or None,
        "bridge_provider_requested": launch_metadata.get("bridge_provider_requested"),
        "bridge_provider_used": launch_metadata.get("bridge_provider_used") or bridge_summary.get("provider"),
        "preflight_ran": launch_metadata.get("preflight_ran"),
        "preflight_status": launch_metadata.get("preflight_status"),
        "preflight": launch_metadata.get("preflight"),
        "failure_stage": failure_stage,
        "group_quality_summary": group_quality_summary,
        "operator_decisions_pending": operator_decisions_pending,
        "agent_followups_pending": agent_followups_pending,
        "run_next_action": run_next_action,
        "run_latest_artifact": run_latest_artifact,
        "runtime": {
            "state": runtime_state,
            "launch_profile": launch_profile,
            "requested_workers": requested_workers,
            "effective_workers": int(bridge_summary.get("workers", effective_workers) or effective_workers),
            "wave_index": final_wave_index,
            "wave_total": len(waves),
            "cancel_requested_at": cancel_requested_at,
            "pid": launch_metadata.get("pid"),
        },
        "bridge": {
            "enabled": bool(bridge_summary.get("enabled")),
            "provider": bridge_summary.get("provider"),
            "attempted_groups": int(bridge_summary.get("attempted_groups", 0)),
            "response_files_written": int(bridge_summary.get("response_files_written", 0)),
            "failure_count": int(bridge_summary.get("failure_count", 0)),
            "workers": int(bridge_summary.get("workers", 1) or 1),
            "requested_workers": requested_workers,
            "launch_profile": launch_profile,
            "stagger_ms": stagger_ms if bridge_enabled else None,
            "max_dump_chars": (None if bridge_max_chars <= 0 else bridge_max_chars) if bridge_enabled else None,
            "timeout_s": bridge_timeout_s if bridge_enabled else None,
            "dispatch_scope_labels": list(bridge_summary.get("dispatch_scope_labels") or []),
            "settled_group_labels": list(bridge_summary.get("settled_group_labels") or []),
            "pending_scope_labels": list(bridge_summary.get("pending_scope_labels") or []),
            "same_pass_promoted_labels": list(bridge_summary.get("same_pass_promoted_labels") or []),
            "settle_passes": int(bridge_summary.get("settle_passes", 0) or 0),
            "settle_launch_sequence": list(bridge_summary.get("settle_launch_sequence") or []),
            "quiescent": bool(bridge_summary.get("quiescent", False)),
        },
        "result_note": result_note_summary,
        "synthesis": synthesis_summary,
        "reference_maps": reference_maps_summary,
        "promotion": promotion_summary,
        "continuation": continuation_summary,
        "groups": groups_payload,
    }
    for field_name in (
        "cycle_id",
        "pass_index",
        "max_passes",
        "assimilation_gate",
        "prior_synthesis_path",
        "prior_synthesis_waiver",
        "reorientation_note_path",
    ):
        if field_name in plan:
            entry_payload[field_name] = plan.get(field_name)

    artifacts_payload.update(
        {
            "result_note": result_note_summary.get("path"),
            "synthesis": synthesis_summary.get("path"),
            "latest_stable_artifact": run_latest_artifact,
            "digest": entry_payload.get("digest", {}).get("path") if isinstance(entry_payload.get("digest"), dict) else None,
            "bridge_provider": launch_metadata.get("bridge_provider_used") or bridge_summary.get("provider"),
            "bridge_log_file": bridge_log_artifact,
        }
    )
    runtime_payload = _build_grouped_runtime_manifest(
        repo_root=repo_root,
        history_dir=history_dir,
        observe_id=observe_id,
        launch_profile=launch_profile,
        requested_workers=requested_workers,
        effective_workers=int(bridge_summary.get("workers", effective_workers) or effective_workers),
        wave_index=final_wave_index,
        wave_total=len(waves),
        state=runtime_state,
        groups_payload=groups_payload,
        artifacts=artifacts_payload,
        launch_metadata=launch_metadata,
        error=(failure_stage if runtime_state == "error" else None),
        cancel_requested_at=cancel_requested_at,
        started_at=started_at,
    )
    write_grouped_runtime_manifest(history_dir, runtime_payload)
    _emit_cycle_event(
        "observe_runtime_finalized",
        runtime_state=runtime_state,
        wave_index=final_wave_index,
        wave_total=len(waves),
        failure_stage=failure_stage,
        latest_artifact=run_latest_artifact,
        result_note=result_note_summary.get("path"),
        synthesis_artifact=synthesis_summary.get("path"),
        response_files_written=int(bridge_summary.get("response_files_written", 0)),
        failure_count=int(bridge_summary.get("failure_count", 0)),
    )

    result_pointer = {
        "source": "grouped_observe_runtime_pointer",
        "observe_id": observe_id,
        "state": runtime_state,
        "history_entry": entry_rel,
        "runtime_manifest": runtime_payload.get("runtime_manifest"),
        "latest_artifact": run_latest_artifact,
        "result_note": result_note_summary.get("path"),
        "synthesis": synthesis_summary.get("path"),
        "updated_at": generated_at,
    }
    promotion_artifacts = promote_grouped_observe_state(
        repo_root=repo_root,
        history_dir=history_dir,
        observe_id=observe_id,
        entry_path=entry_path,
        entry_payload=entry_payload,
        runtime_payload=runtime_payload,
        result_path=result_path,
        result_pointer=result_pointer,
    )
    entry_payload = dict(promotion_artifacts.get("entry_payload") or entry_payload)
    runtime_payload = dict(promotion_artifacts.get("runtime_payload") or runtime_payload)

    return {
        "observe_id": observe_id,
        "entry_file": str(entry_path.relative_to(repo_root)),
        "prompts_file": str(prompts_md_path.relative_to(repo_root)),
        "runtime_manifest": runtime_payload.get("runtime_manifest"),
        "state": runtime_state,
        "launch_profile": launch_profile,
        "requested_workers": requested_workers,
        "effective_workers": int(bridge_summary.get("workers", effective_workers) or effective_workers),
        "groups": groups_payload,
        "group_dumps_prompt_injected": dumps_prompt_injected,
        "dump_prompt_artifacts": dump_prompt_artifacts,
        "bridge_log_file": bridge_log_artifact,
        "sticky_dump_dir": sticky_summary,
        "bridge": {
            "enabled": bool(bridge_summary.get("enabled")),
            "provider": bridge_summary.get("provider"),
            "attempted_groups": int(bridge_summary.get("attempted_groups", 0)),
            "response_files_written": int(bridge_summary.get("response_files_written", 0)),
            "failure_count": int(bridge_summary.get("failure_count", 0)),
            "workers": int(bridge_summary.get("workers", 1) or 1),
            "dispatch_scope_labels": list(bridge_summary.get("dispatch_scope_labels") or []),
            "settled_group_labels": list(bridge_summary.get("settled_group_labels") or []),
            "pending_scope_labels": list(bridge_summary.get("pending_scope_labels") or []),
            "same_pass_promoted_labels": list(bridge_summary.get("same_pass_promoted_labels") or []),
            "settle_passes": int(bridge_summary.get("settle_passes", 0) or 0),
            "settle_launch_sequence": list(bridge_summary.get("settle_launch_sequence") or []),
            "quiescent": bool(bridge_summary.get("quiescent", False)),
        },
        "result_note": result_note_summary,
        "synthesis": synthesis_summary,
        "reference_maps": reference_maps_summary,
        "promotion": promotion_summary,
        "continuation": continuation_summary,
        "launch_command": launch_metadata.get("launch_command"),
        "bridge_provider_requested": launch_metadata.get("bridge_provider_requested"),
        "bridge_provider_used": launch_metadata.get("bridge_provider_used") or bridge_summary.get("provider"),
        "preflight_ran": launch_metadata.get("preflight_ran"),
        "preflight_status": launch_metadata.get("preflight_status"),
        "preflight": launch_metadata.get("preflight"),
        "launch_dispatch": str(launch_metadata.get("launch_dispatch") or "").strip() or None,
        "failure_stage": failure_stage,
        "group_quality_summary": group_quality_summary,
        "operator_decisions_pending": operator_decisions_pending,
        "agent_followups_pending": agent_followups_pending,
        "digest": entry_payload.get("digest"),
        "run_next_action": run_next_action,
        "run_latest_artifact": run_latest_artifact,
        "result_file": str(result_path.relative_to(repo_root)),
        "route_warnings": route_warnings,
    }


_GLOBAL_CANCEL_EVENT: Optional[threading.Event] = None


def _extract_group_summaries(summary: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract _summary blocks from group response files.

    Each bridge response may contain a JSON block like:
        {"_summary": {"teleology": "...", "outcome": "...", "confidence": "HIGH"}}

    We search the response text for the last occurrence and extract it.
    Returns a list of {label, teleology, outcome} dicts.
    """
    import re
    results = []
    groups = summary.get("groups") or []
    dump_dir = summary.get("dump_dir") or summary.get("session_dump_dir") or ""
    for g in groups:
        if not isinstance(g, dict):
            continue
        label = str(g.get("label", "?"))
        # Try to find the response file
        response_file = g.get("response_artifact") or g.get("bridge_dispatch_file") or ""
        if not response_file and dump_dir:
            # Convention: <NN>_<label>_response_bridge_dispatch.json
            import glob
            candidates = glob.glob(os.path.join(str(dump_dir), f"*{label}*response*bridge*.json"))
            if candidates:
                response_file = candidates[0]
        if not response_file or not os.path.exists(str(response_file)):
            continue
        try:
            with open(str(response_file), "r", encoding="utf-8") as f:
                data = json.load(f)
            response_text = str(data.get("normalized_response_text", "") or data.get("response", "") or "")
            # Find last _summary JSON block
            matches = list(re.finditer(r'\{["\s]*_summary["\s]*:', response_text))
            if not matches:
                continue
            last_match = matches[-1]
            # Extract the JSON object starting at the match
            depth = 0
            start = last_match.start()
            for i in range(start, len(response_text)):
                if response_text[i] == '{':
                    depth += 1
                elif response_text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        try:
                            block = json.loads(response_text[start:i + 1])
                            s = block.get("_summary", {})
                            results.append({
                                "label": label,
                                "teleology": str(s.get("teleology", "")).strip(),
                                "outcome": str(s.get("outcome", "")).strip(),
                                "confidence": str(s.get("confidence", "")).strip(),
                            })
                        except json.JSONDecodeError:
                            pass
                        break
        except Exception:
            continue
    return results


def _summary_to_resume_lines(summary: Dict[str, Any]) -> List[str]:
    """Extract a SHORT (<=10 lines) human-readable status from a run_once
    summary. Stays factual: counts, status, dump_dir, failure_stage. The
    agent reading the resumed turn opens the artifact for full detail.
    """
    lines: List[str] = []
    bridge = summary.get("bridge") or {}
    if bridge:
        lines.append(
            "bridge: "
            f"provider={bridge.get('provider') or 'n/a'} "
            f"attempted={bridge.get('attempted_groups', 0)} "
            f"written={bridge.get('response_files_written', 0)} "
            f"failed={bridge.get('failure_count', 0)} "
            f"workers={bridge.get('workers', 1)}"
        )
    groups = summary.get("groups") or []
    if isinstance(groups, list) and groups:
        lines.append(f"groups: {len(groups)}")
        # First few group labels with their response_status if present.
        for g in groups[:5]:
            if not isinstance(g, dict):
                continue
            label = str(g.get("label", "?"))
            status = str(g.get("response_status", "")) or "?"
            quality = str(g.get("response_quality_status", "")) or ""
            qpart = f" ({quality})" if quality and quality != "unknown" else ""
            lines.append(f"- {label}: {status}{qpart}")
        if len(groups) > 5:
            lines.append(f"- ... and {len(groups) - 5} more")
    failure_stage = summary.get("failure_stage")
    if failure_stage:
        lines.append(f"failure_stage: {failure_stage}")
    pending = summary.get("operator_decisions_pending")
    if pending:
        if isinstance(pending, list):
            lines.append(f"operator_decisions_pending: {len(pending)}")
        else:
            lines.append(f"operator_decisions_pending: {pending}")
    return lines


def _summary_to_artifact_paths(summary: Dict[str, Any]) -> List[str]:
    """Extract the disk paths the agent should open if it wants detail."""
    paths: List[str] = []
    for key in (
        "result_file",
        "prompts_file",
        "bridge_log_file",
        "run_latest_artifact",
    ):
        v = summary.get(key)
        if isinstance(v, str) and v:
            paths.append(v)
        elif isinstance(v, dict):
            for inner_k in ("path", "file", "result_path"):
                if isinstance(v.get(inner_k), str) and v[inner_k]:
                    paths.append(v[inner_k])
                    break
    return paths


def _emit_bridge_resume_trigger(
    *,
    summary: Dict[str, Any],
    resume_mode: str,
    resume_job_id: Optional[str],
    resume_plan_id: Optional[str],
    repo_root: Path,
) -> None:
    """Build a ResumeJob from a run_once summary and emit it via the
    BridgeResumeManager. This is the post-completion hook installed by
    `main()` when --resume-mode is set to manual or auto_inject.

    Modes:
      - manual: writes the trigger JSON to tools/meta/bridge/resume_manifests/
        instead of the live injector inbox. A human (or another tool) can
        review and `mv` it into injector_inbox/ to actually inject.
      - auto_inject: writes the trigger directly into injector_inbox/ so the
        running daemon picks it up within ~1.5s.
    """
    from tools.meta.bridge.bridge_resume import (
        BridgeResumeManager,
        ResumeJob,
        ResumeTarget,
        discover_resume_target,
        default_inbox_dir,
        default_ledger_path,
    )

    target = discover_resume_target()
    if target is None:
        sys.stderr.write(
            "[run_observe_plan] --resume-mode requested but no resume "
            "target persisted; skip. Run "
            "`./repo-python -m tools.meta.bridge.bridge_resume set-target "
            "--switch-tab 3 --session-id auto` first.\n"
        )
        return

    if resume_mode == "manual":
        inbox_dir = repo_root / "tools/meta/bridge/resume_manifests"
    else:  # auto_inject
        inbox_dir = default_inbox_dir()

    manager = BridgeResumeManager(
        target,
        inbox_dir=inbox_dir,
        ledger_path=default_ledger_path(),
    )

    failure_stage = summary.get("failure_stage")
    bridge_block = summary.get("bridge") or {}
    failure_count = int(bridge_block.get("failure_count", 0) or 0)
    if failure_stage:
        status = "error"
    elif failure_count > 0:
        status = "partial"
    else:
        status = "ok"

    job_id = resume_job_id or ResumeJob.new_id(prefix="bridge_run")
    # Extract per-group _summary teleology from responses for resume context.
    group_summaries = _extract_group_summaries(summary)

    resume_lines = _summary_to_resume_lines(summary)
    if group_summaries:
        resume_lines.append("")
        for gs in group_summaries:
            resume_lines.append(f"[{gs['label']}] {gs['teleology']} → {gs['outcome']}")

    job = ResumeJob(
        job_id=job_id,
        plan_id=resume_plan_id,
        group_label=None,
        status=status,
        summary_lines=resume_lines,
        artifact_paths=_summary_to_artifact_paths(summary),
        continue_instruction=(
            summary.get("run_next_action")
            or "Open the result_file for full detail; decide the next step."
        ),
    )

    # --- dispatch loop integration: advance state and inject preamble ---
    try:
        from tools.meta.bridge.dispatch_loop import (
            load_state as load_loop_state,
            advance as advance_loop,
            format_loop_preamble,
            should_continue as loop_should_continue,
        )
        loop_state = load_loop_state()
        if loop_state is not None and loop_state.armed:
            loop_state = advance_loop(
                loop_state, job_id=job.job_id, job_status=status,
            )
            job.extras["dispatch_loop_preamble"] = format_loop_preamble(loop_state)
            if loop_should_continue(loop_state):
                plan_hint = ""
                if loop_state.plan_path:
                    plan_hint = f" Read plan at {loop_state.plan_path} first."
                job.continue_instruction = (
                    f"Dispatch loop active (iteration {loop_state.iteration}"
                    f"/{loop_state.max_iterations}).{plan_hint}"
                )
            elif not loop_state.armed:
                job.continue_instruction = (
                    f"Loop ended: {loop_state.disarm_reason or 'done'}. Summarize and stop."
                )
            sys.stderr.write(
                f"[run_observe_plan] dispatch_loop advanced: "
                f"iteration={loop_state.iteration}/{loop_state.max_iterations} "
                f"armed={loop_state.armed}\n"
            )
    except ImportError:
        pass  # dispatch_loop module not present
    except Exception as exc:
        sys.stderr.write(
            f"[run_observe_plan] dispatch_loop advance failed: {exc}\n"
        )

    path = manager.emit_trigger(job)
    sys.stderr.write(
        "[run_observe_plan] resume trigger "
        f"mode={resume_mode} job_id={job.job_id} status={status} "
        f"path={path or '(deduped)'}\n"
    )


def _install_signal_handlers(cancel_event: threading.Event) -> None:
    """Install SIGTERM/SIGINT handlers that set cancel_event and close the bridge.

    This ensures that when the monitor sends SIGTERM, the bridge tabs are
    closed immediately rather than left dangling mid-generation.
    """
    global _GLOBAL_CANCEL_EVENT
    _GLOBAL_CANCEL_EVENT = cancel_event

    def _shutdown_handler(signum: int, frame: Any) -> None:
        cancel_event.set()
        try:
            from system.core.bridge import close as bridge_close
            bridge_close(terminate_browser=False)
        except Exception:
            pass
        raise SystemExit(128 + signum)

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, _shutdown_handler)
        except (OSError, ValueError):
            pass


def main() -> None:
    """
    [ACTION]
    - Teleology: Provide the shell entrypoint for running or resuming grouped observe plans with the legacy/current observe-plan runtime.
    - Mechanism: Parse CLI flags, validate launch metadata and worker settings, call run_once(), and emit resume triggers when configured.
    - Reads: CLI args, optional launch-metadata JSON, and the referenced observe plan/result/history paths.
    - Writes: stdout/stderr process output plus all artifacts produced by run_once().
    - Guarantee: Exits after one grouped observe run attempt using the requested bridge/runtime settings and emits operator-facing errors as SystemExit or downstream exceptions.
    - Fails: Raises SystemExit for invalid CLI inputs and propagates run_once() failures.
    - When-needed: Open when you need the exact CLI contract for the grouped observe-plan runner, including bridge, resume, and launch-metadata flags.
    - Escalates-to: tools/meta/apply/observe_session_runner.py::main; tools/meta/apply/observe_session.py::MetaSessionOrchestratorImpl.run.
    - Navigation-group: observe_apply.
    """
    root = _repo_root()
    default_bridge_timeout_s = _default_bridge_timeout_s(root, bridge_route="kernel_probe")
    parser = argparse.ArgumentParser(description="Run observe_plan.json and write structured observe history artifacts.")
    parser.add_argument("--plan", default="tools/meta/apply/observe_plan.json")
    parser.add_argument("--result", default="tools/meta/apply/observe_result.json")
    parser.add_argument("--history-dir", default="tools/meta/apply/observe_history")
    parser.add_argument("--sentence-count", type=int, default=0, help="Optional sentence cap per generated prompt. Use 0 (default) for no sentence cap.")
    parser.add_argument(
        "--no-sticky-dump-dir",
        action="store_true",
        help="Disable sticky dump_dir policy and honor plan dump_dir directly for this run.",
    )
    parser.add_argument("--bridge", action="store_true", help="Dispatch each grouped observe dump to Bridge and write *_response.md files.")
    parser.add_argument("--provider", "--bridge-provider", dest="bridge_provider", default="", help="Optional provider override (for example: chatgpt or gemini).")
    parser.add_argument(
        "--bridge-max-chars",
        type=int,
        default=0,
        help="Max dump chars included in each Bridge prompt. Use 0 (default) to disable truncation.",
    )
    parser.add_argument(
        "--bridge-timeout-s",
        type=float,
        default=default_bridge_timeout_s,
        help=f"Per-group Bridge monitor timeout in seconds (default: {int(default_bridge_timeout_s)}).",
    )
    parser.add_argument(
        "--bridge-workers",
        default="auto",
        help="Parallel bridge tasks for grouped observe. Use 'auto' (default) or an explicit positive integer.",
    )
    parser.add_argument(
        "--launch-profile",
        default="",
        help="Observe launch profile. Use 'experimental' or 'safe'; defaults to master_config observe.default_launch_profile.",
    )
    parser.add_argument(
        "--resume-observe",
        default="",
        help="Resume a previously launched grouped observe runtime by observe_id.",
    )
    parser.add_argument(
        "--retry-label",
        action="append",
        default=[],
        help="Requeue a specific grouped observe label when resuming an observe_id. May be supplied multiple times.",
    )
    parser.add_argument(
        "--run-kind",
        default="",
        help="Optional run kind metadata (e.g. 'fresh' or 'resume'). Passed to bridge as metadata.",
    )
    parser.add_argument(
        "--launch-metadata-json",
        default="",
        help="Optional JSON payload from kernel launch time describing provider/preflight/command metadata.",
    )
    parser.add_argument(
        "--resume-mode",
        default="none",
        choices=("none", "manual", "auto_inject"),
        help=(
            "Bridge -> Claude.app resume protocol. 'none' (default) does "
            "nothing. 'manual' writes a resume manifest to "
            "tools/meta/bridge/resume_manifests/ for human review. "
            "'auto_inject' writes a trigger directly to the injector inbox "
            "so the daemon will paste a short summary back into the "
            "running Claude.app Code-tab session. Requires a persisted "
            "ResumeTarget — see "
            "`./repo-python -m tools.meta.bridge.bridge_resume set-target`."
        ),
    )
    parser.add_argument(
        "--resume-job-id",
        default="",
        help="Optional explicit job_id for the resume trigger. Auto-generated if omitted.",
    )
    parser.add_argument(
        "--resume-plan-id",
        default="",
        help="Optional plan label injected into the resume message.",
    )
    args = parser.parse_args()

    plan_path = (root / args.plan).resolve()
    result_path = (root / args.result).resolve()
    history_dir = (root / args.history_dir).resolve()

    if not plan_path.exists():
        raise SystemExit(f"Plan file not found: {plan_path}")
    if args.sentence_count < 0:
        raise SystemExit("--sentence-count must be >= 0")
    if args.bridge_timeout_s <= 0:
        raise SystemExit("--bridge-timeout-s must be > 0")
    if str(args.bridge_workers).strip().lower() != "auto":
        try:
            if int(str(args.bridge_workers).strip()) <= 0:
                raise SystemExit("--bridge-workers must be 'auto' or > 0")
        except ValueError as exc:
            raise SystemExit("--bridge-workers must be 'auto' or > 0") from exc

    launch_metadata: Optional[Dict[str, Any]] = None
    if str(args.launch_metadata_json).strip():
        try:
            payload = json.loads(args.launch_metadata_json)
        except Exception as exc:
            raise SystemExit(f"--launch-metadata-json must be valid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise SystemExit("--launch-metadata-json must decode to a JSON object")
        launch_metadata = payload
    if launch_metadata is None:
        launch_metadata = {}
    launch_metadata["pid"] = os.getpid()

    # Install signal handlers so SIGTERM from monitor cleanly shuts down bridge
    _main_cancel_event = threading.Event()
    _install_signal_handlers(_main_cancel_event)

    summary = run_once(
        repo_root=root,
        plan_path=plan_path,
        result_path=result_path,
        history_dir=history_dir,
        sentence_count=(args.sentence_count if args.sentence_count > 0 else None),
        sticky_dump_dir=(not args.no_sticky_dump_dir),
        bridge_enabled=args.bridge,
        bridge_provider=str(args.bridge_provider).strip() or None,
        bridge_max_chars=args.bridge_max_chars,
        bridge_timeout_s=args.bridge_timeout_s,
        bridge_workers=str(args.bridge_workers).strip() or "auto",
        launch_profile=str(args.launch_profile).strip() or str(observe_runtime_policy(root)["default_launch_profile"]),
        launch_metadata=launch_metadata,
        resume_observe_id=str(args.resume_observe).strip() or None,
        retry_group_labels=[str(label).strip() for label in args.retry_label if str(label).strip()],
        run_kind=str(args.run_kind).strip() or None,
        cancel_event=_main_cancel_event,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    # --- Bridge -> Claude.app resume hook (opt-in) -----------------------
    # If launched with --resume-mode auto_inject or manual, format a short
    # summary of the run and emit a resume trigger. Default behaviour
    # (resume_mode=none) is unchanged. Failures here NEVER abort the run —
    # the bridge run already succeeded; resume is best-effort.
    if args.resume_mode != "none":
        try:
            _emit_bridge_resume_trigger(
                summary=summary,
                resume_mode=args.resume_mode,
                resume_job_id=args.resume_job_id.strip() or None,
                resume_plan_id=args.resume_plan_id.strip() or None,
                repo_root=root,
            )
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(
                f"[run_observe_plan] resume trigger emission failed: {exc}\n"
            )


if __name__ == "__main__":
    main()
