"""Read-only mutation governance gates for agent task framing.

The guards here answer a question that ordinary artifact validators cannot:
was mutation the correct response to the latest operator intent?  They are
pure helpers so entry routing, seed skills, continuation packets, and preflight
CLIs can share the same latest-intent, stutter-loop, budget, idempotency, diff,
and closeout framing without each route inventing local rules.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from system.lib.git_state_snapshot import build_git_state_snapshot


LATEST_INTENT_GATE_SCHEMA = "latest_intent_gate_v0"
PAYLOAD_INSTRUCTION_SEPARATION_SCHEMA = "payload_instruction_separation_v0"
STUTTER_LOOP_DETECTOR_SCHEMA = "stutter_loop_detector_v0"
LEDGER_GROWTH_BUDGET_SCHEMA = "ledger_growth_budget_v0"
MUTATION_IDEMPOTENCY_KEY_SCHEMA = "mutation_idempotency_key_v0"
OPERATOR_GOAL_SATISFACTION_SCHEMA = "operator_goal_satisfaction_v0"
COMPACTION_RESUME_CAPSULE_SCHEMA = "compaction_resume_capsule_v0"
DIFF_SAFETY_GATE_SCHEMA = "diff_safety_gate_v0"
LANDING_PREFLIGHT_GATE_SCHEMA = "landing_preflight_gate_v0"
CANDIDATE_ROW_PREFLIGHT_SCHEMA = "candidate_row_preflight_v0"
MUTATION_GOVERNANCE_PACKET_SCHEMA = "mutation_governance_packet_v0"

INTENT_DIAGNOSE_SYSTEM_FROM_TRANSCRIPT = "diagnose_system_from_transcript"
INTENT_MUTATE_PATTERN_LEDGER = "mutate_pattern_ledger"
INTENT_SUMMARIZE_PRIOR_RUN = "summarize_prior_run"
INTENT_CONTINUE_INTERRUPTED_RUN = "continue_interrupted_run"
INTENT_IMPLEMENT_SYSTEM_PATCHES = "implement_system_patches"
INTENT_GENERAL_TASK = "general_task"

PATTERN_LEDGER_ROUTE_IDS = {
    "public_microcosm_pattern_ledger_growth",
    "public_microcosm_evolution_seed",
    "microcosm_extracted_pattern_ledger",
    "pattern_ledger_growth",
}

DEFAULT_MAX_NEW_LEDGER_ROWS = 4
DEFAULT_MAX_GROWTH_PASSES_PER_OPERATOR_SEED = 1
DEFAULT_MAX_GENERATED_SIDECARS_TOUCHED = 6
DEFAULT_HIGH_NOVELTY_LOW_RISK_BACKLOG_LIMIT = 50

_DIAGNOSTIC_PHRASES = (
    "spot improvements",
    "agent troubles",
    "agents troubles",
    "agent trouble",
    "what went wrong",
    "why did this loop",
    "why did agents fail",
    "diagnose",
    "diagnostic",
    "given the attached",
    "attached transcript",
    "attached trace",
    "transcript shows",
    "prior run",
    "previous run",
)

_LEDGER_MUTATION_PHRASES = (
    "refine or grow our pattern ledger",
    "grow our pattern ledger",
    "pattern ledger growth",
    "ledger-growth",
    "ledger growth",
    "append another tranche",
    "append rows",
    "append more rows",
    "add pattern rows",
    "mutate pattern ledger",
    "public microcosm flagship-pattern",
)

_MUTATION_PROMOTER_PHRASES = (
    "do the ledger growth",
    "continue the run",
    "continue the ledger growth",
    "apply these changes",
    "edit the repo",
    "implement this",
    "please implement",
)

_SUMMARIZE_PHRASES = (
    "summarize prior run",
    "summarise prior run",
    "summarize the transcript",
    "summarise the transcript",
    "recap what happened",
)

_CONTINUE_PHRASES = (
    "continue",
    "resume",
    "keep going",
)

_IMPLEMENT_PHRASES = (
    "please implement",
    "implement this",
    "implement the",
    "wire this",
    "add this",
    "patch this",
    "edit the repo",
)

_TRACE_DIAGNOSTICS_PHRASES = (
    "attached",
    "attcahed",
    "attached trace",
    "attached traces",
    "agent trace",
    "agent traces",
    "other agent trace",
    "other agent traces",
    "session trace",
    "session traces",
    "trace summary",
    "trace summaries",
    "meta diagnostic",
    "meta diagnostics",
    "session diagnostic",
    "session diagnostics",
    "diagnostic summary",
    "diagnostics summary",
)

_TRACE_GENERALIZATION_PHRASES = (
    "generalize",
    "generalise",
    "generalized",
    "generalised",
    "generalizing",
    "generalising",
    "generalization",
    "generalisation",
    "generalize skill",
    "generalise skill",
    "local to general",
    "up propagate",
    "up propagation",
    "uppropagate",
    "uppropagation",
    "failure class",
    "non overfit",
    "non-overfit",
    "nonoverfit",
    "system refinement",
    "system refinements",
    "improve routing",
    "routing repair",
    "genrealise",
    "genrealize",
    "geenralise",
    "geenralize",
    "geineralise",
    "geineralize",
)

_PAYLOAD_EVIDENCE_PHRASES = (
    "attached",
    "attcahed",
    "attached transcript",
    "attached trace",
    "given the attached",
    "given attached",
    "given the agents troubles attached",
    "given attached agent troubles",
    "shows agents were",
    "transcript contains",
)

_SYSTEM_IMPROVEMENT_ACTION_WORDS = {
    "make",
    "implement",
    "apply",
    "patch",
    "edit",
    "fix",
    "wire",
}

_SYSTEM_IMPROVEMENT_WORDS = {
    "improve",
    "improvement",
    "improvements",
    "refine",
    "refinement",
    "refinements",
    "patch",
    "patches",
    "change",
    "changes",
}

_SYSTEM_IMPROVEMENT_TARGET_WORDS = {
    "system",
    "repo",
    "substrate",
    "routing",
    "route",
    "routes",
    "skill",
    "skills",
    "standard",
    "standards",
    "checker",
    "checkers",
    "tool",
    "tools",
    "governance",
}


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip().casefold()
    return re.sub(r"\s+", " ", text)


def _contains_any(text: str, phrases: Sequence[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _word_tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text)


def _edit_distance_at_most(left: str, right: str, limit: int) -> bool:
    if abs(len(left) - len(right)) > limit:
        return False
    if left == right:
        return True

    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current = [i]
        row_min = i
        for j, right_char in enumerate(right, start=1):
            cost = 0 if left_char == right_char else 1
            value = min(
                previous[j] + 1,
                current[j - 1] + 1,
                previous[j - 1] + cost,
            )
            current.append(value)
            row_min = min(row_min, value)
        if row_min > limit:
            return False
        previous = current
    return previous[-1] <= limit


def _token_matches_any(token: str, targets: set[str], *, typo_limit: int = 1) -> bool:
    if token in targets:
        return True
    if len(token) < 5:
        return False
    return any(_edit_distance_at_most(token, target, typo_limit) for target in targets)


def _is_system_improvement_request(text: str) -> bool:
    tokens = _word_tokens(text)
    if not tokens:
        return False
    has_action = any(token in _SYSTEM_IMPROVEMENT_ACTION_WORDS for token in tokens)
    has_improvement = any(
        _token_matches_any(token, _SYSTEM_IMPROVEMENT_WORDS, typo_limit=2)
        for token in tokens
    )
    has_target = any(
        _token_matches_any(token, _SYSTEM_IMPROVEMENT_TARGET_WORDS, typo_limit=1)
        for token in tokens
    )
    return has_action and has_improvement and has_target


def _is_trace_diagnostics_generalization_request(text: str) -> bool:
    return _contains_any(text, _TRACE_DIAGNOSTICS_PHRASES) and _contains_any(
        text,
        _TRACE_GENERALIZATION_PHRASES,
    )


def _stable_digest(value: Any, *, length: int = 16) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:length]


def stable_prompt_hash(prompt: str) -> str:
    """Return a deterministic hash for near-identical prompt-loop detection."""
    return _stable_digest(_normalize_text(prompt), length=24)


def classify_latest_user_intent(latest_user_message: str | None) -> str:
    """Classify the latest operator message, not imperative text inside payload."""
    text = _normalize_text(latest_user_message)
    if not text:
        return INTENT_GENERAL_TASK

    implement_requested = _contains_any(text, _IMPLEMENT_PHRASES)
    diagnostic_requested = _contains_any(text, _DIAGNOSTIC_PHRASES)
    ledger_mutation_text = _contains_any(text, _LEDGER_MUTATION_PHRASES)
    payload_evidence = _contains_any(text, _PAYLOAD_EVIDENCE_PHRASES)
    trace_generalization_requested = _is_trace_diagnostics_generalization_request(text)
    system_improvement_requested = _is_system_improvement_request(text)

    # "please implement this: <diagnostic spec>" is a repo-change request about
    # the spec itself.  Do not downgrade it just because the quoted spec includes
    # diagnostic trigger phrases.
    if implement_requested and text.startswith(("please implement", "implement this", "implement the")):
        return INTENT_IMPLEMENT_SYSTEM_PATCHES
    if system_improvement_requested:
        return INTENT_IMPLEMENT_SYSTEM_PATCHES
    if trace_generalization_requested:
        return INTENT_IMPLEMENT_SYSTEM_PATCHES

    if diagnostic_requested and (payload_evidence or ledger_mutation_text):
        return INTENT_DIAGNOSE_SYSTEM_FROM_TRANSCRIPT
    if diagnostic_requested and not implement_requested:
        return INTENT_DIAGNOSE_SYSTEM_FROM_TRANSCRIPT

    if ledger_mutation_text:
        return INTENT_MUTATE_PATTERN_LEDGER
    if _contains_any(text, _SUMMARIZE_PHRASES):
        return INTENT_SUMMARIZE_PRIOR_RUN
    if _contains_any(text, _CONTINUE_PHRASES):
        return INTENT_CONTINUE_INTERRUPTED_RUN
    if implement_requested:
        return INTENT_IMPLEMENT_SYSTEM_PATCHES
    return INTENT_GENERAL_TASK


def task_mentions_agent_trouble_diagnosis(task_text: str | None) -> bool:
    return classify_latest_user_intent(task_text) == INTENT_DIAGNOSE_SYSTEM_FROM_TRANSCRIPT


def build_payload_instruction_separation(latest_user_message: str | None) -> dict[str, Any]:
    text = _normalize_text(latest_user_message)
    latest_intent = classify_latest_user_intent(latest_user_message)
    historical_seed_detected = _contains_any(text, _LEDGER_MUTATION_PHRASES)
    evidence_context_detected = _contains_any(text, _PAYLOAD_EVIDENCE_PHRASES)
    explicit_payload_promotion = (
        _contains_any(text, _MUTATION_PROMOTER_PHRASES)
        and latest_intent == INTENT_MUTATE_PATTERN_LEDGER
        and not evidence_context_detected
    )
    quoted_context_not_operator_order = bool(
        latest_intent == INTENT_DIAGNOSE_SYSTEM_FROM_TRANSCRIPT
        and historical_seed_detected
    )
    return {
        "schema": PAYLOAD_INSTRUCTION_SEPARATION_SCHEMA,
        "latest_user_message_precedence": 1,
        "explicitly_referenced_attachment_as_evidence_precedence": 2,
        "pasted_prior_agent_prompt_precedence": 3,
        "historical_agent_output_precedence": 4,
        "latest_intent": latest_intent,
        "historical_ledger_seed_detected": historical_seed_detected,
        "evidence_context_detected": evidence_context_detected,
        "latest_message_explicitly_promotes_payload": explicit_payload_promotion,
        "latest_message_explicitly_requests_system_patch": (
            latest_intent == INTENT_IMPLEMENT_SYSTEM_PATCHES
        ),
        "quoted_context_not_operator_order": quoted_context_not_operator_order,
        "rule": (
            "Imperative prior prompts inside attached/transcript evidence remain payload "
            "unless the latest user message explicitly promotes them as the live task."
        ),
    }


def _route_requests_pattern_ledger_mutation(route_id: str | None, latest_user_message: str | None) -> bool:
    route = _normalize_text(route_id)
    if route and any(marker in route for marker in PATTERN_LEDGER_ROUTE_IDS):
        return True
    text = _normalize_text(latest_user_message)
    return _contains_any(text, _LEDGER_MUTATION_PHRASES)


def build_latest_intent_gate(
    latest_user_message: str | None,
    *,
    requested_route: str | None = None,
) -> dict[str, Any]:
    separation = build_payload_instruction_separation(latest_user_message)
    latest_intent = str(separation["latest_intent"])
    route_requests_ledger = _route_requests_pattern_ledger_mutation(requested_route, latest_user_message)
    pattern_ledger_mutation_allowed = (
        latest_intent == INTENT_MUTATE_PATTERN_LEDGER
        and not separation["quoted_context_not_operator_order"]
    )
    diagnostic_mode = latest_intent == INTENT_DIAGNOSE_SYSTEM_FROM_TRANSCRIPT
    repo_patch_allowed = latest_intent in {
        INTENT_IMPLEMENT_SYSTEM_PATCHES,
        INTENT_MUTATE_PATTERN_LEDGER,
        INTENT_CONTINUE_INTERRUPTED_RUN,
    }
    prohibit_file_writes = diagnostic_mode or (
        route_requests_ledger and not pattern_ledger_mutation_allowed
    )
    return {
        "schema": LATEST_INTENT_GATE_SCHEMA,
        "status": "blocked" if prohibit_file_writes else "clear",
        "latest_intent": latest_intent,
        "requested_route": requested_route,
        "route_requests_pattern_ledger_mutation": route_requests_ledger,
        "pattern_ledger_mutation_allowed": pattern_ledger_mutation_allowed,
        "repo_patch_allowed": repo_patch_allowed and not diagnostic_mode,
        "prohibit_file_writes": prohibit_file_writes,
        "prohibit_seed_reentry": route_requests_ledger and not pattern_ledger_mutation_allowed,
        "force_mode": "audit_only" if diagnostic_mode else None,
        "route_override": "agent_trouble_diagnosis_seed" if diagnostic_mode else None,
        "payload_instruction_separation": separation,
        "allowed_modes_if_blocked": ["audit_only", "dry_run", "patch_bundle_only"],
        "disallowed_if_blocked": [
            "mutate_pattern_ledger",
            "seed_reentry",
            "finalize_as_landed",
        ],
    }


def build_stutter_loop_detector(
    *,
    prompt_events: Sequence[str] = (),
    route_events: Sequence[str] = (),
    context_compaction_count: int = 0,
    steer_count: int = 0,
) -> dict[str, Any]:
    prompt_hashes = [stable_prompt_hash(item) for item in prompt_events if str(item or "").strip()]
    route_tokens = [_normalize_text(item) for item in route_events if str(item or "").strip()]
    prompt_counts = Counter(prompt_hashes)
    route_counts = Counter(route_tokens)
    max_prompt_count = max(prompt_counts.values(), default=0)
    max_route_count = max(route_counts.values(), default=0)
    same_route_reentered = max_route_count >= 2
    signals: list[str] = []
    if max_prompt_count >= 2:
        signals.append("same_user_prompt_hash_seen>=2")
    if same_route_reentered:
        signals.append("same_seed_route_seen>=2")
    if context_compaction_count >= 1 and same_route_reentered:
        signals.append("context_compaction_count>=1_and_same_route_reentered")
    if steer_count >= 1 and max_prompt_count >= 2:
        signals.append("repeated_steer_with_same_payload")
    blocked = bool(signals)
    return {
        "schema": STUTTER_LOOP_DETECTOR_SCHEMA,
        "status": "blocked" if blocked else "clear",
        "signals": signals,
        "same_user_prompt_hash_seen": max_prompt_count,
        "same_seed_route_seen": max_route_count,
        "context_compaction_count": int(context_compaction_count),
        "steer_count": int(steer_count),
        "action": "stop_mutating_and_diagnose" if blocked else "continue_if_latest_intent_allows",
        "required_output": [
            "current_state_summary",
            "suspected_loop_cause",
            "proposed_next_safe_action",
        ] if blocked else [],
    }


def build_ledger_growth_budget(
    *,
    new_rows_requested: int = 0,
    growth_passes_for_operator_seed: int = 0,
    generated_sidecars_touched: int = 0,
    previous_successful_append: bool = False,
    context_compaction_count: int = 0,
    commit_blocker_seen: bool = False,
    high_novelty_low_risk_backlog_count: int | None = None,
) -> dict[str, Any]:
    violations: list[str] = []
    reauthorization_reasons: list[str] = []
    if new_rows_requested > DEFAULT_MAX_NEW_LEDGER_ROWS:
        violations.append("max_new_rows_exceeded")
    if growth_passes_for_operator_seed >= DEFAULT_MAX_GROWTH_PASSES_PER_OPERATOR_SEED:
        violations.append("max_growth_passes_per_operator_seed_exceeded")
    if generated_sidecars_touched > DEFAULT_MAX_GENERATED_SIDECARS_TOUCHED:
        violations.append("max_generated_sidecars_touched_exceeded")
    if previous_successful_append:
        reauthorization_reasons.append("successful_append_already_recorded")
    if context_compaction_count:
        reauthorization_reasons.append("context_compaction_seen")
    if commit_blocker_seen:
        reauthorization_reasons.append("commit_blocker_seen")
    default_action = "append_more_patterns"
    disallowed_default_action = None
    if (
        high_novelty_low_risk_backlog_count is not None
        and high_novelty_low_risk_backlog_count > DEFAULT_HIGH_NOVELTY_LOW_RISK_BACKLOG_LIMIT
    ):
        default_action = "rank_existing_patterns"
        disallowed_default_action = "append_more_patterns"
        violations.append("high_novelty_low_risk_backlog_saturated")
    status = "blocked" if violations or reauthorization_reasons else "clear"
    return {
        "schema": LEDGER_GROWTH_BUDGET_SCHEMA,
        "status": status,
        "default_max_new_rows": DEFAULT_MAX_NEW_LEDGER_ROWS,
        "max_growth_passes_per_operator_seed": DEFAULT_MAX_GROWTH_PASSES_PER_OPERATOR_SEED,
        "max_generated_sidecars_touched": DEFAULT_MAX_GENERATED_SIDECARS_TOUCHED,
        "new_rows_requested": int(new_rows_requested),
        "growth_passes_for_operator_seed": int(growth_passes_for_operator_seed),
        "generated_sidecars_touched": int(generated_sidecars_touched),
        "violations": violations,
        "require_operator_reauthorization_after": reauthorization_reasons,
        "default_action": default_action,
        "disallowed_default_action": disallowed_default_action,
    }


def mutation_idempotency_key(
    *,
    route: str,
    latest_user_seed: str,
    tranche_themes: Sequence[str] = (),
    ledger_start_count: int | None = None,
) -> dict[str, Any]:
    seed_hash = stable_prompt_hash(latest_user_seed)
    theme_hash = _stable_digest(sorted(str(item).strip() for item in tranche_themes if str(item).strip()), length=16)
    key = _stable_digest(
        {
            "route": route,
            "seed_hash": seed_hash,
            "tranche_theme_hash": theme_hash,
            "ledger_start_count": ledger_start_count,
        },
        length=24,
    )
    return {
        "schema": MUTATION_IDEMPOTENCY_KEY_SCHEMA,
        "key": key,
        "route": route,
        "seed_hash": seed_hash,
        "tranche_theme_hash": theme_hash,
        "ledger_start_count": ledger_start_count,
    }


def build_operator_goal_satisfaction(
    *,
    latest_user_intent: str,
    performed_mutation: bool,
    answer_addresses_latest_user: bool = True,
    quoted_context_executed: bool = False,
) -> dict[str, Any]:
    quoted_context_not_executed = not quoted_context_executed
    ok = bool(answer_addresses_latest_user and quoted_context_not_executed)
    if latest_user_intent == INTENT_DIAGNOSE_SYSTEM_FROM_TRANSCRIPT and performed_mutation:
        ok = False
    return {
        "schema": OPERATOR_GOAL_SATISFACTION_SCHEMA,
        "status": "ok" if ok else "failed",
        "ok": ok,
        "latest_user_intent": latest_user_intent,
        "performed_mutation": bool(performed_mutation),
        "answer_addresses_latest_user": bool(answer_addresses_latest_user),
        "quoted_context_not_executed": quoted_context_not_executed,
        "failure_reasons": [] if ok else [
            reason
            for reason, present in (
                ("diagnostic_intent_performed_mutation", latest_user_intent == INTENT_DIAGNOSE_SYSTEM_FROM_TRANSCRIPT and performed_mutation),
                ("answer_did_not_address_latest_user", not answer_addresses_latest_user),
                ("quoted_context_executed", quoted_context_executed),
            )
            if present
        ],
    }


def build_compaction_resume_capsule(
    *,
    latest_user_intent: str,
    active_transaction_id: str | None = None,
    appended_rows: Sequence[str] = (),
    refreshed_sidecars: Sequence[str] = (),
    blockers_seen: Sequence[str] = (),
    successful_append: bool = False,
) -> dict[str, Any]:
    prohibited_next_actions = ["rerun_same_seed"]
    if successful_append or appended_rows or latest_user_intent != INTENT_MUTATE_PATTERN_LEDGER:
        prohibited_next_actions.append("append_more_rows_without_new_authorization")
    safe_next_action = (
        "summarize_or_validate_current_state"
        if latest_user_intent == INTENT_DIAGNOSE_SYSTEM_FROM_TRANSCRIPT
        else "ask_for_authorization_if_mutation_needed"
        if successful_append or appended_rows
        else "validate_current_state"
    )
    return {
        "schema": COMPACTION_RESUME_CAPSULE_SCHEMA,
        "latest_user_intent": latest_user_intent,
        "active_transaction_id": active_transaction_id,
        "already_completed": {
            "appended_rows": list(appended_rows),
            "refreshed_sidecars": list(refreshed_sidecars),
            "blockers_seen": list(blockers_seen),
        },
        "prohibited_next_actions": prohibited_next_actions,
        "safe_next_action": safe_next_action,
    }


def _is_generated_like_path(path: str) -> bool:
    token = str(path or "").strip("/")
    return (
        token.startswith(("codex/derived/", "state/", "docs/system_atlas/generated_"))
        or token.endswith(("_index.json", "_projection.json", "_registry.json"))
        or ".generated." in token
        or "/generated/" in token
    )


def _count_file_lines(path: Path, *, max_bytes: int = 5_000_000) -> int:
    try:
        if not path.is_file() or path.stat().st_size > max_bytes:
            return 0
        with path.open("rb") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return 0


def _git_untracked_paths(repo_root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _git_diff_numstat(repo_root: Path) -> tuple[int, int, list[str], str | None]:
    proc = subprocess.run(
        ["git", "diff", "--numstat", "HEAD", "--"],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        return 0, 0, [], proc.stderr.strip()[:500] or f"git diff exited {proc.returncode}"
    added = 0
    deleted = 0
    paths: list[str] = []
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        raw_added, raw_deleted, path = parts[0], parts[1], parts[2]
        paths.append(path)
        if raw_added.isdigit():
            added += int(raw_added)
        if raw_deleted.isdigit():
            deleted += int(raw_deleted)
    for path in _git_untracked_paths(repo_root):
        paths.append(path)
        added += _count_file_lines(repo_root / path)
    return added, deleted, paths, None


def build_diff_safety_gate(
    repo_root: Path,
    *,
    expected_owned_paths: Sequence[str] = (),
    added_line_limit: int = 50_000,
    deleted_line_limit: int = 10_000,
    generated_file_churn_ratio_limit: float = 0.10,
    touched_files_slack: int = 3,
) -> dict[str, Any]:
    repo_root = Path(repo_root).resolve()
    added, deleted, paths, error = _git_diff_numstat(repo_root)
    expected = {str(path).strip("/") for path in expected_owned_paths if str(path).strip()}
    generated_paths = [path for path in paths if _is_generated_like_path(path)]
    ratio = (len(generated_paths) / len(paths)) if paths else 0.0
    fail_reasons: list[str] = []
    if error:
        fail_reasons.append("diff_unavailable")
    if added > added_line_limit:
        fail_reasons.append("added_lines_over_limit")
    if deleted > deleted_line_limit:
        fail_reasons.append("deleted_lines_over_limit")
    if paths and ratio > generated_file_churn_ratio_limit:
        fail_reasons.append("generated_file_churn_ratio_over_limit")
    touched_limit = len(expected) + touched_files_slack if expected else touched_files_slack
    if len(paths) > touched_limit:
        fail_reasons.append("touched_files_over_expected_scope")
    return {
        "schema": DIFF_SAFETY_GATE_SCHEMA,
        "status": "blocked" if fail_reasons else "clear",
        "fail_reasons": fail_reasons,
        "added_lines": added,
        "deleted_lines": deleted,
        "touched_files": len(paths),
        "expected_owned_paths": sorted(expected),
        "expected_touched_file_limit": touched_limit,
        "generated_file_churn_ratio": ratio,
        "generated_path_count": len(generated_paths),
        "generated_paths_preview": generated_paths[:12],
        "on_fail": {
            "revert_generated_artifact_churn": True,
            "switch_to_patch_summary": True,
            "require_human_review": True,
        } if fail_reasons else {},
        "error": error,
    }


def build_landing_preflight_gate(
    repo_root: Path,
    *,
    owned_paths: Sequence[str] = (),
    git_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo_root = Path(repo_root).resolve()
    snapshot = dict(git_snapshot or build_git_state_snapshot(repo_root, path_limit=20, recent_limit=2))
    metadata = snapshot.get("git_metadata_write") if isinstance(snapshot.get("git_metadata_write"), Mapping) else {}
    index_state = snapshot.get("index_state") if isinstance(snapshot.get("index_state"), Mapping) else {}
    metadata_writable = bool(metadata.get("writable", metadata.get("status") != "blocked"))
    staged_paths = [str(path) for path in index_state.get("staged_paths_preview") or snapshot.get("staged_paths_preview") or []]
    owned = {str(path).strip("/") for path in owned_paths if str(path).strip()}
    unowned_staged = [path for path in staged_paths if owned and path not in owned]
    status = "blocked" if not metadata_writable else ("watch" if unowned_staged else "clear")
    return {
        "schema": LANDING_PREFLIGHT_GATE_SCHEMA,
        "status": status,
        "before_file_writes": [
            "can_write_git_metadata",
            "can_stage_owned_paths",
            "can_create_commit_or_patch_bundle",
        ],
        "can_write_git_metadata": metadata_writable,
        "git_metadata_write": dict(metadata),
        "owned_paths": sorted(owned),
        "staged_paths_preview": staged_paths[:12],
        "unowned_staged_paths_preview": unowned_staged[:12],
        "allowed_modes_if_commit_blocked": ["dry_run", "patch_bundle_only", "audit_only"],
        "disallowed_if_commit_blocked": ["mutate_and_finalize_as_done"],
    }


def _load_jsonl_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    if not path.is_file():
        return ids
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ids
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, Mapping):
            for key in ("pattern_id", "id", "row_id"):
                token = str(row.get(key) or "").strip()
                if token:
                    ids.add(token)
                    break
    return ids


def build_candidate_row_preflight(
    repo_root: Path,
    *,
    candidate_rows: Sequence[Mapping[str, Any]],
    ledger_path: str | None = None,
) -> dict[str, Any]:
    repo_root = Path(repo_root).resolve()
    existing_ids = _load_jsonl_ids(repo_root / ledger_path) if ledger_path else set()
    errors: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, row in enumerate(candidate_rows):
        pattern_id = str(row.get("pattern_id") or row.get("id") or "").strip()
        if not pattern_id:
            errors.append({"row_index": index, "error": "pattern_id_missing"})
        elif pattern_id in existing_ids or pattern_id in seen_ids:
            errors.append({"row_index": index, "pattern_id": pattern_id, "error": "pattern_id_duplicate"})
        if pattern_id:
            seen_ids.add(pattern_id)
        refs = row.get("source_refs") or row.get("source_ref") or []
        if isinstance(refs, str):
            refs = [refs]
        for ref in refs if isinstance(refs, Iterable) else []:
            token = str(ref or "").split("::", 1)[0].strip()
            if token and not (repo_root / token).exists():
                errors.append({"row_index": index, "pattern_id": pattern_id or None, "source_ref": token, "error": "source_ref_missing"})
        organ_path = str(row.get("organ_path") or row.get("fixture_path") or "").split("::", 1)[0].strip()
        if organ_path and not (repo_root / organ_path).exists():
            errors.append({"row_index": index, "pattern_id": pattern_id or None, "organ_path": organ_path, "error": "organ_path_missing"})
        if row.get("public_safe") is False:
            errors.append({"row_index": index, "pattern_id": pattern_id or None, "error": "candidate_fixture_not_public_safe"})
    return {
        "schema": CANDIDATE_ROW_PREFLIGHT_SCHEMA,
        "status": "blocked" if errors else "clear",
        "row_count": len(candidate_rows),
        "ledger_path": ledger_path,
        "errors": errors,
    }


def build_mutation_governance_packet(
    repo_root: Path,
    *,
    latest_user_message: str | None,
    requested_route: str | None = None,
    expected_owned_paths: Sequence[str] = (),
) -> dict[str, Any]:
    gate = build_latest_intent_gate(latest_user_message, requested_route=requested_route)
    return {
        "schema": MUTATION_GOVERNANCE_PACKET_SCHEMA,
        "latest_intent_gate": gate,
        "diff_safety_gate": build_diff_safety_gate(repo_root, expected_owned_paths=expected_owned_paths),
        "landing_preflight_gate": build_landing_preflight_gate(repo_root, owned_paths=expected_owned_paths),
        "operator_goal_satisfaction": build_operator_goal_satisfaction(
            latest_user_intent=str(gate["latest_intent"]),
            performed_mutation=False,
            quoted_context_executed=False,
        ),
    }
