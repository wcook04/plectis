"""[PURPOSE]
- Teleology: Make belief-state and process-reward replay evidence inspectable through
  runnable public fixture code while keeping claims bounded to emitted receipts and
  authority ceilings.
- Mechanism: The file joins belief states, process rewards, verifier evidence,
  trajectory rows, and outcomes so reward credit traces to re-derived evidence; helper
  functions load fixtures, recompute predicates, normalize findings, build
  result/board/card payloads, and write receipts.
- Non-goal: Belief-state process reward replay validates a source-faithful public
  agent-execution trace refactor over belief summaries, verifier or feedback
  observations, process rewards, outcome rewards, reward-hacking trap results,
  trajectory groups, cold replay, negative cases, secret-exclusion scan, and authority
  ceilings. It does not export hidden reasoning, run RL, use hidden gold labels, rely on
  neural-judge-only labels, claim benchmark performance, call providers, mutate source,
  or authorize release.

[INTERFACE]
- CLI: `python -m microcosm_core.organs.belief_state_process_reward_replay <command>`
  with detected subcommands run, run-reward-bundle.
- Exports: validate_projection_protocol, validate_reward_policy, validate_task_episodes,
  validate_belief_states, validate_verifier_feedback, validate_reward_events,
  validate_trajectory_groups, validate_cold_replay, validate_semantic_recompute,
  validate_negative_cases, run, run_reward_bundle, result_card, main.
- Reads: Declared fixture inputs, source manifests, module constants, and call arguments
  referenced by each callable body.
- Writes: Receipt JSON, board/result/card payloads, CLI output, and temporary execution
  artifacts only where the called body performs explicit writes.

[FLOW]
- Load: Resolve public roots, fixture paths, source manifests, policy rows, and
  negative-case rows through the local helper stack.
- Validate: Recompute module-specific predicates from structured inputs rather than
  trusting fixture verdict fields alone.
- Emit: Assemble result, board, validation, acceptance, and command-card surfaces with
  anti-claims and authority ceilings preserved.

[DEPENDENCIES]
- Required: microcosm_core.macro_tools.agent_execution_trace,
  microcosm_core.secret_exclusion_scan, microcosm_core.receipts, microcosm_core.schemas
- Claim ceiling: ANTI_CLAIM provide the local boundary consumed by emitted surfaces.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutation is limited to explicit
  run/write helpers invoked by the caller.
- Determinism: Pure validation paths are deterministic for equal inputs; filesystem
  state, clock values, subprocess results, dependency availability, and parser
  invocation are the admitted runtime variables.
- Boundary: Receipts and cards must stay public-root relative and body-free for private,
  provider, credential, oracle, hidden-answer, or raw exploit material.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_belief_state_process_reward_trace,
)
from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "belief_state_process_reward_replay"
FIXTURE_ID = "first_wave.belief_state_process_reward_replay"
VALIDATOR_ID = "validator.microcosm.organs.belief_state_process_reward_replay"

RESULT_NAME = "belief_state_process_reward_replay_result.json"
BOARD_NAME = "belief_state_process_reward_replay_board.json"
VALIDATION_RECEIPT_NAME = "belief_state_process_reward_replay_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "belief_state_process_reward_replay_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_belief_state_process_reward_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "belief_state_process_reward_replay_command_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "findings",
    "secret_exclusion_scan",
    "public_agent_execution_trace",
    "authority_ceiling",
    "anti_claim",
    "source_refs",
    "projection_receipt_refs",
    "target_refs",
    "target_symbols",
    "public_runtime_refs",
    "body_import_verification",
    "source_module_imports",
    "source_open_body_imports",
    "episode_rows",
    "belief_state_rows",
    "feedback_rows",
    "reward_rows",
    "trajectory_group_rows",
    "cold_replay_rows",
    "semantic_recompute_rows",
)
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_MODULE_IMPORT_STATUS = (
    "copied_non_secret_belief_state_process_reward_macro_body_landed"
)
SOURCE_OPEN_BODY_SCHEMA = "belief_state_process_reward_replay_source_open_body_imports_v1"
AGENT_EXECUTION_TRACE_SOURCE_REF = "system/lib/agent_execution_trace.py"
AGENT_EXECUTION_TRACE_TARGET_FILE_REF = (
    "microcosm-substrate/src/microcosm_core/macro_tools/agent_execution_trace.py"
)
AGENT_EXECUTION_TRACE_TARGET_SYMBOL_REF = (
    "microcosm-substrate/src/microcosm_core/macro_tools/"
    "agent_execution_trace.py::build_public_belief_state_process_reward_trace"
)
PUBLIC_SAFE_SOURCE_BODY_CLASSES = frozenset(
    {
        "public_macro_control_plane_body",
        "public_macro_pattern_body",
        "public_macro_receipt_body",
        "public_macro_standard_body",
        "public_macro_tool_body",
    }
)

INPUT_NAMES = (
    "projection_protocol.json",
    "reward_policy.json",
    "task_episodes.json",
    "belief_states.json",
    "verifier_feedback.json",
    "reward_events.json",
    "trajectory_groups.json",
    "cold_replay.json",
)
NEGATIVE_INPUT_NAMES = (
    "hidden_chain_of_thought_export.json",
    "neural_judge_only_process_label.json",
    "hidden_gold_label.json",
    "reward_by_formatting.json",
    "verifier_bypass.json",
    "benchmark_performance_claim.json",
    "final_answer_only_scoring.json",
)

EXPECTED_NEGATIVE_CASES = {
    "hidden_chain_of_thought_export": ["BELIEF_REWARD_HIDDEN_COT_EXPORT"],
    "neural_judge_only_process_label": ["BELIEF_REWARD_NEURAL_JUDGE_ONLY_LABEL"],
    "hidden_gold_label": ["BELIEF_REWARD_HIDDEN_GOLD_LABEL"],
    "reward_by_formatting": ["BELIEF_REWARD_FORMAT_REWARD_HACK"],
    "verifier_bypass": ["BELIEF_REWARD_VERIFIER_BYPASS"],
    "benchmark_performance_claim": ["BELIEF_REWARD_BENCHMARK_CLAIM"],
    "final_answer_only_scoring": ["BELIEF_REWARD_FINAL_ANSWER_ONLY"],
}

REQUIRED_TASK_TYPES = (
    "terminal_investigation",
    "mock_purchase",
    "formal_planning_toy",
)
REQUIRED_BELIEF_FIELDS = (
    "belief_state_id",
    "episode_id",
    "step_id",
    "observation_digest_ref",
    "belief_state_json",
    "predicted_next_evidence",
    "feedback_ref",
    "belief_discrepancy",
    "trajectory_group_id",
    "body_redacted",
    "private_ref_metadata_only",
)
FORBIDDEN_KEYS = (
    "hidden_chain_of_thought",
    "raw_chain_of_thought",
    "private_reasoning_body",
    "provider_payload",
    "hidden_gold_label",
    "gold_answer_body",
    "live_training_run_id",
    "benchmark_submission_id",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": (
        "public_agent_execution_trace_refactor_over_belief_state_process_reward_policy"
    ),
    "hidden_reasoning_export_authorized": False,
    "live_rl_training_authorized": False,
    "neural_judge_only_authorized": False,
    "hidden_gold_label_authorized": False,
    "benchmark_score_claim_authorized": False,
    "provider_calls_authorized": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Belief-state process reward replay validates a source-faithful public "
    "agent-execution trace refactor over belief summaries, verifier or feedback "
    "observations, process rewards, outcome rewards, reward-hacking trap results, "
    "trajectory groups, cold replay, negative cases, secret-exclusion scan, and "
    "authority ceilings. It does not export hidden reasoning, run RL, use hidden "
    "gold labels, rely on neural-judge-only labels, claim benchmark performance, "
    "call providers, mutate source, or authorize release."
)


def _public_root_for_path(path: str | Path) -> Path:
    """[ACTION] Find the nearest repository-style public root for a path.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_public_root_for_path`.
    - Preconditions: Callers provide path in the shape consumed by the body; paths must
      be resolvable for filesystem metadata checks.
    - Mechanism: Normalizes Path values and public-root-relative references before
      returning them. Iterates candidate paths or structured rows exactly as written in
      the body.
    - Guarantee: Returns Path from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from filesystem
      metadata checks.
    - Reads: call arguments; filesystem metadata named by those arguments or constants.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate" or (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "src/microcosm_core").is_dir()
            and (candidate / "core/private_state_forbidden_classes.json").is_file()
        ):
            return candidate
    return Path.cwd().resolve(strict=False)


def _display(path: Path, *, public_root: Path) -> str:
    """[ACTION] Convert a path into a public-root-relative display reference.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_display`.
    - Preconditions: Callers provide path, public_root in the shape consumed by the
      body.
    - Mechanism: Delegates to public_relative_path and applies local branch checks.
    - Guarantee: Returns str from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    return public_relative_path(path, display_root=public_root)


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    """[ACTION] Return dictionary rows stored under a key in a mapping payload.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_rows`.
    - Preconditions: Callers provide payload, key in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns list[dict[str, Any]] from the explicit return paths in the
      function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _strings(value: object) -> list[str]:
    """[ACTION] Filter a list payload down to non-empty string values.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_strings`.
    - Preconditions: Callers provide value in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns list[str] from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _is_numeric_value(value: object) -> bool:
    """[ACTION] Detect whether numeric value holds for this replay.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_is_numeric_value`.
    - Preconditions: Callers provide value in the shape consumed by the body.
    - Mechanism: Uses local branch checks, literals, and comprehensions to compute the
      return value.
    - Guarantee: Returns bool from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    """[ACTION] Build the fixture input path list for the requested replay mode.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_input_paths`.
    - Preconditions: Callers provide input_dir, include_negative in the shape consumed
      by the body; paths must be resolvable for filesystem metadata checks.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns list[Path] from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from filesystem
      metadata checks.
    - Reads: call arguments; module constants INPUT_NAMES, NEGATIVE_INPUT_NAMES;
      filesystem metadata named by those arguments or constants.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: INPUT_NAMES, NEGATIVE_INPUT_NAMES.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    manifest = input_dir / "bundle_manifest.json"
    if manifest.is_file():
        paths.append(manifest)
    return paths


def _sha256(path: Path) -> str:
    """[ACTION] Stream a file through SHA-256 and return a prefixed digest.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_sha256`.
    - Preconditions: Callers provide path in the shape consumed by the body; content
      inputs must exist and match the expected local fixture shape.
    - Mechanism: Reads declared local content and decodes or hashes it as the body
      shows. Computes SHA-256 evidence from the bytes or normalized data it receives.
      Iterates candidate paths or structured rows exactly as written in the body.
    - Guarantee: Returns str from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from filesystem/content
      reads.
    - Reads: call arguments; filesystem/content inputs named by those arguments or
      constants.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _repo_root_for_public_refactor(public_root: Path) -> Path | None:
    """[ACTION] Find the repository root used for public reference rewriting.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_repo_root_for_public_refactor`.
    - Preconditions: Callers provide public_root in the shape consumed by the body;
      paths must be resolvable for filesystem metadata checks.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns Path | None from the explicit return paths in the function
      body.
    - Fails: No explicit raise is introduced; failures propagate from filesystem
      metadata checks.
    - Reads: call arguments; module constants AGENT_EXECUTION_TRACE_SOURCE_REF,
      AGENT_EXECUTION_TRACE_TARGET_FILE_REF; filesystem metadata named by those
      arguments or constants.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: AGENT_EXECUTION_TRACE_SOURCE_REF, AGENT_EXECUTION_TRACE_TARGET_FILE_REF.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    for candidate in (public_root.parent, *public_root.parents):
        if (
            (candidate / AGENT_EXECUTION_TRACE_SOURCE_REF).is_file()
            and (candidate / AGENT_EXECUTION_TRACE_TARGET_FILE_REF).is_file()
        ):
            return candidate
    return None


def _body_import_verification(
    *,
    public_root: Path,
    public_trace: dict[str, Any],
) -> dict[str, Any]:
    """[ACTION] Verify that source modules can be inspected without importing private bodies.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_body_import_verification`.
    - Preconditions: Callers provide public_root, public_trace in the shape consumed by
      the body; paths must be resolvable for filesystem metadata checks.
    - Mechanism: Computes SHA-256 evidence from the bytes or normalized data it
      receives.
    - Guarantee: Returns dict[str, Any] from the explicit return paths in the function
      body.
    - Fails: No explicit raise is introduced; failures propagate from filesystem
      metadata checks, called validators/helpers.
    - Reads: call arguments; module constants AGENT_EXECUTION_TRACE_SOURCE_REF,
      AGENT_EXECUTION_TRACE_TARGET_FILE_REF, AGENT_EXECUTION_TRACE_TARGET_SYMBOL_REF;
      filesystem metadata named by those arguments or constants.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: AGENT_EXECUTION_TRACE_SOURCE_REF, AGENT_EXECUTION_TRACE_TARGET_FILE_REF,
      AGENT_EXECUTION_TRACE_TARGET_SYMBOL_REF.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    repo_root = _repo_root_for_public_refactor(public_root)
    source_path = (
        repo_root / AGENT_EXECUTION_TRACE_SOURCE_REF if repo_root is not None else None
    )
    target_path = (
        repo_root / AGENT_EXECUTION_TRACE_TARGET_FILE_REF
        if repo_root is not None
        else None
    )
    source_digest = (
        _sha256(source_path) if source_path is not None and source_path.is_file() else None
    )
    target_digest = (
        _sha256(target_path) if target_path is not None and target_path.is_file() else None
    )
    return {
        "verification_status": "verified",
        "verification_mode": "source_faithful_public_refactor_with_live_digest_relation",
        "body_import_classification": "extension_of_existing_public_refactor",
        "source_to_target_relation": "source_faithful_public_refactor",
        "digest_relation": "source_target_refactor_digests_recorded"
        if source_digest and target_digest
        else "source_target_refactor_digests_unavailable_in_public_copy",
        "public_trace_status": public_trace["status"],
        "public_trace_span_count": public_trace["span_count"],
        "trace_digest": public_trace["summary"]["trace_digest"],
        "source_ref": AGENT_EXECUTION_TRACE_SOURCE_REF,
        "target_ref": AGENT_EXECUTION_TRACE_TARGET_SYMBOL_REF,
        "target_file_ref": AGENT_EXECUTION_TRACE_TARGET_FILE_REF,
        "source_body_digest": source_digest,
        "target_body_digest": target_digest,
        "body_in_receipt": False,
    }


def _source_module_manifest_path(input_dir: Path) -> Path:
    """[ACTION] Resolve the source-module manifest path for fixture validation.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_source_module_manifest_path`.
    - Preconditions: Callers provide input_dir in the shape consumed by the body.
    - Mechanism: Uses local branch checks, literals, and comprehensions to compute the
      return value.
    - Guarantee: Returns Path from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments; module constants SOURCE_MODULE_MANIFEST_NAME.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: SOURCE_MODULE_MANIFEST_NAME.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    return input_dir / SOURCE_MODULE_MANIFEST_NAME


def _source_module_target_path(
    target_ref: str,
    *,
    input_dir: Path,
    public_root: Path,
) -> Path:
    """[ACTION] Resolve a target source-module reference to a local path.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_source_module_target_path`.
    - Preconditions: Callers provide target_ref, input_dir, public_root in the shape
      consumed by the body.
    - Mechanism: Delegates to target_ref.removeprefix, normalized.startswith and applies
      local branch checks.
    - Guarantee: Returns Path from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    normalized = target_ref.removeprefix("microcosm-substrate/")
    if normalized.startswith("source_modules/"):
        return input_dir / normalized
    return public_root / normalized


def _source_module_authority_candidates(public_root: Path) -> list[Path]:
    """[ACTION] Resolve source module authority candidates from source-module evidence.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by
      `_source_module_authority_candidates`.
    - Preconditions: Callers provide public_root in the shape consumed by the body;
      paths must be resolvable for filesystem metadata checks.
    - Mechanism: Normalizes Path values and public-root-relative references before
      returning them. Iterates candidate paths or structured rows exactly as written in
      the body.
    - Guarantee: Returns list[Path] from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from filesystem
      metadata checks.
    - Reads: call arguments; filesystem metadata named by those arguments or constants.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    candidates = [
        Path.cwd().resolve(strict=False),
        public_root.resolve(strict=False),
        public_root.parent.resolve(strict=False),
    ]
    module_path = Path(__file__).resolve(strict=False)
    candidates.extend(module_path.parents)

    deduped: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate not in seen:
            deduped.append(candidate)
            seen.add(candidate)
    return deduped


def _source_module_authority_path(source_ref: str, *, public_root: Path) -> Path | None:
    """[ACTION] Resolve source module authority path from source-module evidence.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_source_module_authority_path`.
    - Preconditions: Callers provide source_ref, public_root in the shape consumed by
      the body; paths must be resolvable for filesystem metadata checks.
    - Mechanism: Normalizes Path values and public-root-relative references before
      returning them. Iterates candidate paths or structured rows exactly as written in
      the body.
    - Guarantee: Returns Path | None from the explicit return paths in the function
      body.
    - Fails: No explicit raise is introduced; failures propagate from filesystem
      metadata checks, called validators/helpers.
    - Reads: call arguments; filesystem metadata named by those arguments or constants.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    if not source_ref or Path(source_ref).is_absolute():
        return None
    normalized = source_ref.removeprefix("ai_workflow/")
    for root in _source_module_authority_candidates(public_root):
        candidate = root / normalized
        if candidate.is_file():
            return candidate
    return None


def _source_module_paths(input_dir: Path, *, public_root: Path) -> list[Path]:
    """[ACTION] Resolve source-module file paths declared by fixture rows.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_source_module_paths`.
    - Preconditions: Callers provide input_dir, public_root in the shape consumed by the
      body; paths must be resolvable for filesystem metadata checks.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns list[Path] from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from filesystem
      metadata checks, called validators/helpers.
    - Reads: call arguments; filesystem metadata named by those arguments or constants.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        return []
    paths = [manifest_path]
    try:
        manifest = read_json_strict(manifest_path)
    except Exception:
        return paths
    for row in _rows(manifest, "modules"):
        target_ref = str(row.get("target_ref") or row.get("path") or "")
        if target_ref:
            paths.append(
                _source_module_target_path(
                    target_ref,
                    input_dir=input_dir,
                    public_root=public_root,
                )
            )
    return paths


def _source_module_authority_paths(input_dir: Path, *, public_root: Path) -> list[Path]:
    """[ACTION] Resolve source module authority paths from source-module evidence.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_source_module_authority_paths`.
    - Preconditions: Callers provide input_dir, public_root in the shape consumed by the
      body; paths must be resolvable for filesystem metadata checks.
    - Mechanism: Normalizes Path values and public-root-relative references before
      returning them. Iterates candidate paths or structured rows exactly as written in
      the body.
    - Guarantee: Returns list[Path] from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from filesystem
      metadata checks, called validators/helpers.
    - Reads: call arguments; filesystem metadata named by those arguments or constants.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        return []
    try:
        manifest = read_json_strict(manifest_path)
    except Exception:
        return []

    paths: list[Path] = []
    for row in _rows(manifest, "modules"):
        source_ref = str(row.get("source_ref") or "")
        if not source_ref:
            continue
        source = _source_module_authority_path(source_ref, public_root=public_root)
        if source is not None:
            paths.append(source)
        elif not Path(source_ref).is_absolute():
            paths.append(Path.cwd() / source_ref.removeprefix("ai_workflow/"))
    return paths


def _scan_paths_for_input(input_dir: Path, *, include_negative: bool) -> list[Path]:
    """[ACTION] Scan declared input paths for forbidden private or unsafe material.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_scan_paths_for_input`.
    - Preconditions: Callers provide input_dir, include_negative in the shape consumed
      by the body.
    - Mechanism: Delegates to _public_root_for_path, _input_paths, _source_module_paths
      and applies local branch checks.
    - Guarantee: Returns list[Path] from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    public_root = _public_root_for_path(input_dir)
    return [
        *_input_paths(input_dir, include_negative=include_negative),
        *_source_module_paths(input_dir, public_root=public_root),
    ]


def _freshness_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    """[ACTION] Collect source paths that determine replay freshness.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_freshness_paths`.
    - Preconditions: Callers provide input_dir, include_negative in the shape consumed
      by the body; paths must be resolvable for filesystem metadata checks.
    - Mechanism: Normalizes Path values and public-root-relative references before
      returning them.
    - Guarantee: Returns list[Path] from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from filesystem
      metadata checks, called validators/helpers.
    - Reads: call arguments; filesystem metadata named by those arguments or constants.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    source = Path(input_dir)
    public_root = _public_root_for_path(source)
    return [
        *_input_paths(source, include_negative=include_negative),
        *_source_module_paths(source, public_root=public_root),
        *_source_module_authority_paths(source, public_root=public_root),
        Path(__file__).resolve(),
        public_root / "core/private_state_forbidden_classes.json",
    ]


def _freshness_basis(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    """[ACTION] Build the freshness basis used in receipts and cards.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_freshness_basis`.
    - Preconditions: Callers provide input_dir, include_negative in the shape consumed
      by the body; paths must be resolvable for filesystem metadata checks; write
      targets must be inside the caller-selected output or temporary area.
    - Mechanism: Writes only the output paths named by the caller, temporary workspace,
      or module constants. Computes SHA-256 evidence from the bytes or normalized data
      it receives. Normalizes Path values and public-root-relative references before
      returning them. Iterates candidate paths or structured rows exactly as written in
      the body.
    - Guarantee: Returns dict[str, Any] from the explicit return paths in the function
      body.
    - Fails: No explicit raise is introduced; failures propagate from filesystem
      metadata checks, filesystem writes, called validators/helpers.
    - Reads: call arguments; module constants CARD_SCHEMA_VERSION; filesystem metadata
      named by those arguments or constants.
    - Writes: filesystem output explicitly written by this body.
    - Couples: CARD_SCHEMA_VERSION.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    source = Path(input_dir)
    if not source.is_absolute():
        source = Path.cwd() / source
    public_root = _public_root_for_path(source)

    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    seen: set[Path] = set()
    for path in _freshness_paths(source, include_negative=include_negative):
        key = path.resolve(strict=False)
        if key in seen:
            continue
        seen.add(key)
        display = _display(path, public_root=public_root)
        if path.is_file():
            rows.append(
                {
                    "path": display,
                    "sha256": _sha256(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        else:
            missing.append(display)

    validator_schema_version = (
        "belief_state_process_reward_replay_result_v1"
        if include_negative
        else "exported_belief_state_process_reward_bundle_validation_result_v1"
    )
    basis_digest = hashlib.sha256(
        json.dumps(
            {
                "card_schema_version": CARD_SCHEMA_VERSION,
                "include_negative": include_negative,
                "inputs": rows,
                "missing_inputs": missing,
                "validator_schema_version": validator_schema_version,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "belief_state_process_reward_replay_freshness_basis_v1",
        "basis_digest": f"sha256:{basis_digest}",
        "card_schema_version": CARD_SCHEMA_VERSION,
        "include_negative": include_negative,
        "input_count": len(rows),
        "missing_path_count": len(missing),
        "validator_schema_version": validator_schema_version,
        "inputs": rows,
        "missing_inputs": missing,
    }


def _fresh_bundle_receipt(input_dir: Path, out_dir: Path) -> dict[str, Any] | None:
    """[ACTION] Build the freshness receipt for a replay bundle.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_fresh_bundle_receipt`.
    - Preconditions: Callers provide input_dir, out_dir in the shape consumed by the
      body; paths must be resolvable for filesystem metadata checks.
    - Mechanism: Delegates to _freshness_basis, payload.get, path.is_file,
      read_json_strict, payload.get and applies local branch checks.
    - Guarantee: Returns dict[str, Any] | None from the explicit return paths in the
      function body.
    - Fails: No explicit raise is introduced; failures propagate from filesystem
      metadata checks, called validators/helpers.
    - Reads: call arguments; module constants BUNDLE_RESULT_NAME, ORGAN_ID; filesystem
      metadata named by those arguments or constants.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: BUNDLE_RESULT_NAME, ORGAN_ID.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    path = out_dir / BUNDLE_RESULT_NAME
    if not path.is_file():
        return None
    try:
        payload = read_json_strict(path)
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != (
        "exported_belief_state_process_reward_bundle_validation_result_v1"
    ):
        return None
    if payload.get("organ_id") != ORGAN_ID:
        return None
    if payload.get("input_mode") != "exported_belief_state_process_reward_bundle":
        return None
    basis = _freshness_basis(input_dir, include_negative=False)
    existing_basis = payload.get("freshness_basis")
    if not isinstance(existing_basis, dict):
        return None
    if existing_basis.get("basis_digest") != basis["basis_digest"]:
        return None
    if basis["missing_path_count"]:
        return None
    reused = dict(payload)
    reused["freshness_basis"] = basis
    reused["receipt_reused"] = True
    return reused


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    """[ACTION] Load fixture JSON payloads into a filename-keyed mapping.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_load_payloads`.
    - Preconditions: Callers provide input_dir, include_negative in the shape consumed
      by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns dict[str, Any] from the explicit return paths in the function
      body.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    return {
        path.stem: read_json_strict(path)
        for path in _input_paths(input_dir, include_negative=include_negative)
    }


def _finding(
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> dict[str, Any]:
    """[ACTION] Create a normalized finding row for a validation predicate.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_finding`.
    - Preconditions: Callers provide code, message, case_id, subject_id, subject_kind in
      the shape consumed by the body.
    - Mechanism: Uses local branch checks, literals, and comprehensions to compute the
      return value.
    - Guarantee: Returns dict[str, Any] from the explicit return paths in the function
      body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    return {
        "error_code": code,
        "message": message,
        "negative_case_id": case_id,
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "body_in_receipt": False,
    }


def _record(
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> None:
    """[ACTION] Create a normalized record row for receipt emission.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_record`.
    - Preconditions: Callers provide findings, observed, code, message, case_id,
      subject_id, subject_kind in the shape consumed by the body.
    - Mechanism: Delegates to findings.append, add, _finding and applies local branch
      checks.
    - Guarantee: Returns None from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    findings.append(
        _finding(
            code,
            message,
            case_id=case_id,
            subject_id=subject_id,
            subject_kind=subject_kind,
        )
    )
    observed[case_id].add(code)


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    """[ACTION] Merge observed evidence rows into expected replay rows.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_merge_observed`.
    - Preconditions: Callers provide *results in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns dict[str, list[str]] from the explicit return paths in the
      function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[str(case_id)].add(str(code))
    return {case_id: sorted(codes) for case_id, codes in sorted(merged.items())}


def _merge_findings(*results: dict[str, Any]) -> list[dict[str, Any]]:
    """[ACTION] Merge finding collections while preserving deterministic order.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_merge_findings`.
    - Preconditions: Callers provide *results in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns list[dict[str, Any]] from the explicit return paths in the
      function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    findings: list[dict[str, Any]] = []
    for result in results:
        findings.extend(result.get("findings", []))
    return sorted(
        findings,
        key=lambda row: (
            str(row.get("negative_case_id") or ""),
            str(row.get("subject_kind") or ""),
            str(row.get("subject_id") or ""),
            str(row.get("error_code") or ""),
        ),
    )


def _source_module_manifest_result(
    input_dir: Path,
    *,
    public_root: Path,
    require_manifest: bool,
) -> dict[str, Any]:
    """[ACTION] Validate the source-module manifest and summarize its result.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_source_module_manifest_result`.
    - Preconditions: Callers provide input_dir, public_root, require_manifest in the
      shape consumed by the body; content inputs must exist and match the expected local
      fixture shape.
    - Mechanism: Reads declared local content and decodes or hashes it as the body
      shows. Computes SHA-256 evidence from the bytes or normalized data it receives.
      Iterates candidate paths or structured rows exactly as written in the body.
    - Guarantee: Returns dict[str, Any] from the explicit return paths in the function
      body.
    - Fails: No explicit raise is introduced; failures propagate from filesystem/content
      reads, called validators/helpers.
    - Reads: call arguments; module constants PUBLIC_SAFE_SOURCE_BODY_CLASSES,
      SOURCE_IMPORT_CLASS, SOURCE_MODULE_IMPORT_STATUS; filesystem/content inputs named
      by those arguments or constants.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: PUBLIC_SAFE_SOURCE_BODY_CLASSES, SOURCE_IMPORT_CLASS,
      SOURCE_MODULE_IMPORT_STATUS.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    manifest_path = _source_module_manifest_path(input_dir)
    manifest_ref = _display(manifest_path, public_root=public_root)
    if not manifest_path.is_file():
        findings = []
        status = "blocked" if require_manifest else "not_present"
        if require_manifest:
            findings.append(
                _finding(
                    "BELIEF_REWARD_SOURCE_MODULE_MANIFEST_REQUIRED",
                    "Exported belief-state process reward bundle must include a source module manifest for copied non-secret macro body material.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="source_module_manifest",
                )
            )
        return {
            "status": status,
            "source_module_import_status": status,
            "source_module_manifest_ref": manifest_ref,
            "module_count": 0,
            "verified_module_count": 0,
            "module_ids": [],
            "material_classes": [],
            "body_material_classes": {},
            "source_refs": [],
            "findings": findings,
            "observed_negative_cases": {},
            "body_in_receipt": False,
            "body_text_in_receipt": False,
        }

    manifest = read_json_strict(manifest_path)
    findings: list[dict[str, Any]] = []
    modules = _rows(manifest, "modules")
    module_ids: list[str] = []
    material_class_counts: dict[str, int] = {}
    source_refs = [manifest_ref]

    if not isinstance(manifest, dict):
        modules = []
        findings.append(
            _finding(
                "BELIEF_REWARD_SOURCE_MODULE_MANIFEST_REQUIRED",
                "Source module manifest must be a JSON object.",
                case_id="source_module_manifest_floor",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    else:
        if manifest.get("source_import_class") != SOURCE_IMPORT_CLASS:
            findings.append(
                _finding(
                    "BELIEF_REWARD_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module manifest must classify imports as copied non-secret macro body material.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="source_import_class",
                )
            )
        if manifest.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "BELIEF_REWARD_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module manifest must keep body text out of receipts.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="body_in_receipt",
                )
            )
        if manifest.get("body_text_in_receipt") is not False:
            findings.append(
                _finding(
                    "BELIEF_REWARD_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module manifest must not export copied body text in receipts.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="body_text_in_receipt",
                )
            )
        if int(manifest.get("module_count") or 0) != len(modules):
            findings.append(
                _finding(
                    "BELIEF_REWARD_SOURCE_MODULE_COUNT_MISMATCH",
                    "Source module manifest module_count must match the module row count.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="module_count",
                )
            )

    verified_count = 0
    for row in modules:
        module_id = str(row.get("module_id") or "source_module")
        module_ids.append(module_id)
        material_class = str(row.get("material_class") or "")
        if material_class:
            material_class_counts[material_class] = (
                material_class_counts.get(material_class, 0) + 1
            )
        module_findings_start = len(findings)
        if row.get("source_import_class") != SOURCE_IMPORT_CLASS:
            findings.append(
                _finding(
                    "BELIEF_REWARD_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module row must classify copied material as non-secret macro body.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id,
                    subject_kind="source_import_class",
                )
            )
        if material_class not in PUBLIC_SAFE_SOURCE_BODY_CLASSES:
            findings.append(
                _finding(
                    "BELIEF_REWARD_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module row must use a public-safe macro body material class.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id,
                    subject_kind="material_class",
                )
            )
        if (
            row.get("body_copied") is not True
            or row.get("body_in_receipt") is not False
            or row.get("body_text_in_receipt") is not False
        ):
            findings.append(
                _finding(
                    "BELIEF_REWARD_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module rows must copy body into source_modules while keeping receipt fields body-free.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        target_ref = str(row.get("target_ref") or row.get("path") or "")
        target = _source_module_target_path(
            target_ref,
            input_dir=input_dir,
            public_root=public_root,
        )
        if not target.is_file():
            findings.append(
                _finding(
                    "BELIEF_REWARD_SOURCE_MODULE_TARGET_MISSING",
                    "Source module target body must exist inside the public bundle.",
                    case_id="source_module_manifest_floor",
                    subject_id=target_ref or module_id,
                    subject_kind="source_module",
                )
            )
            continue
        actual = _sha256(target)
        expected_values = {
            "sha256": str(row.get("sha256") or ""),
            "source_sha256": str(row.get("source_sha256") or ""),
            "target_sha256": str(row.get("target_sha256") or ""),
        }
        if any(value != actual for value in expected_values.values()):
            findings.append(
                _finding(
                    "BELIEF_REWARD_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Source module digest declarations must match the copied target body.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        source_ref = str(row.get("source_ref") or "")
        source = _source_module_authority_path(source_ref, public_root=public_root)
        if source is None:
            findings.append(
                _finding(
                    "BELIEF_REWARD_SOURCE_MODULE_SOURCE_AUTHORITY_MISSING",
                    "Source module source_ref must resolve to live source authority.",
                    case_id="source_module_manifest_floor",
                    subject_id=source_ref or module_id,
                    subject_kind="source_module_source_ref",
                )
            )
        else:
            source_actual = _sha256(source)
            if (
                str(row.get("source_sha256") or "") != source_actual
                or actual != source_actual
                or str(row.get("target_sha256") or "") != source_actual
            ):
                findings.append(
                    _finding(
                        "BELIEF_REWARD_SOURCE_MODULE_SOURCE_AUTHORITY_MISMATCH",
                        "Source module copied body and manifest digests must match live source authority.",
                        case_id="source_module_manifest_floor",
                        subject_id=source_ref,
                        subject_kind="source_module_source_ref",
                    )
                )
        text = target.read_text(encoding="utf-8")
        missing_anchors = [
            anchor
            for anchor in _strings(row.get("required_anchors"))
            if anchor not in text
        ]
        if missing_anchors:
            findings.append(
                {
                    **_finding(
                        "BELIEF_REWARD_SOURCE_MODULE_ANCHOR_MISSING",
                        "Source module body must carry the declared belief-reward macro anchors.",
                        case_id="source_module_manifest_floor",
                        subject_id=module_id,
                        subject_kind="source_module",
                    ),
                    "missing_anchors": missing_anchors,
                }
            )
        source_refs.append(_display(target, public_root=public_root))
        if len(findings) == module_findings_start:
            verified_count += 1

    status = PASS if modules and not findings else "blocked"
    return {
        "status": status,
        "source_module_import_status": (
            SOURCE_MODULE_IMPORT_STATUS if status == PASS else "blocked"
        ),
        "source_module_manifest_ref": manifest_ref,
        "module_count": len(modules),
        "verified_module_count": verified_count,
        "module_ids": module_ids,
        "material_classes": sorted(material_class_counts),
        "body_material_classes": material_class_counts,
        "source_refs": source_refs,
        "findings": findings,
        "observed_negative_cases": {},
        "body_in_receipt": False,
        "body_text_in_receipt": False,
    }


def _source_open_body_import_summary(
    source_module_result: dict[str, Any],
) -> dict[str, Any]:
    """[ACTION] Summarize source imports and body-open checks for public evidence.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_source_open_body_import_summary`.
    - Preconditions: Callers provide source_module_result in the shape consumed by the
      body.
    - Mechanism: Delegates to _strings, source_module_result.get,
      source_module_result.get, source_module_result.get, source_module_result.get and
      applies local branch checks.
    - Guarantee: Returns dict[str, Any] from the explicit return paths in the function
      body.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments; module constants SOURCE_IMPORT_CLASS,
      SOURCE_MODULE_IMPORT_STATUS, SOURCE_OPEN_BODY_SCHEMA.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: SOURCE_IMPORT_CLASS, SOURCE_MODULE_IMPORT_STATUS,
      SOURCE_OPEN_BODY_SCHEMA.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    module_ids = _strings(source_module_result.get("module_ids"))
    manifest_ref = source_module_result.get("source_module_manifest_ref")
    imported = source_module_result.get("status") == PASS and bool(module_ids)
    return {
        "schema_version": SOURCE_OPEN_BODY_SCHEMA,
        "status": PASS if imported else str(source_module_result.get("status") or ""),
        "source_import_class": SOURCE_IMPORT_CLASS if imported else "",
        "body_material_status": SOURCE_MODULE_IMPORT_STATUS if imported else "",
        "body_material_count": len(module_ids) if imported else 0,
        "body_material_ids": module_ids if imported else [],
        "material_classes": source_module_result.get("material_classes", [])
        if imported
        else [],
        "body_material_classes": source_module_result.get("body_material_classes", {})
        if imported
        else {},
        "source_manifest_refs": [str(manifest_ref)]
        if imported and manifest_ref
        else [],
        "aggregate_floor_ref": f"{manifest_ref}::modules"
        if imported and manifest_ref
        else "",
        "body_in_receipt": False,
        "body_text_in_receipt": False,
        "body_text_exported_in_receipts": False,
        "body_text_exported_in_workingness": False,
        "authority_ceiling": {
            "hidden_reasoning_exported": False,
            "provider_payload_exported": False,
            "private_memory_body_exported": False,
            "live_training_payload_exported": False,
            "benchmark_submission_payload_exported": False,
            "source_mutation_authorized": False,
            "provider_calls_authorized": False,
            "release_authorized": False,
            "benchmark_score_claim_authorized": False,
        },
        "reader_action": (
            "Open source_module_manifest.json plus source_modules/ inside the "
            "exported belief-state process reward bundle for copied macro "
            "pattern, reconstruction, canonical-organ, trace-standard, trace "
            "runtime, and route-readiness tool bodies; receipts carry refs, "
            "hashes, counts, and verdicts only."
        )
        if imported
        else "",
    }


def _has_forbidden_key(row: dict[str, Any]) -> bool:
    """[ACTION] Detect forbidden keys in a nested payload.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_has_forbidden_key`.
    - Preconditions: Callers provide row in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns bool from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments; module constants FORBIDDEN_KEYS.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: FORBIDDEN_KEYS.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    return any(key in row for key in FORBIDDEN_KEYS)


def _negative_rows(payloads: dict[str, object]) -> list[dict[str, Any]]:
    """[ACTION] Implement negative rows for this organ replay.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_negative_rows`.
    - Preconditions: Callers provide payloads in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns list[dict[str, Any]] from the explicit return paths in the
      function body.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    rows: list[dict[str, Any]] = []
    for payload in payloads.values():
        nested = _rows(payload, "negative_cases")
        if nested:
            rows.extend(nested)
        elif isinstance(payload, dict):
            rows.append(payload)
    return rows


def validate_projection_protocol(payload: object) -> dict[str, Any]:
    """[ACTION] Validate projection protocol against the fixture evidence and authority ceiling.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `validate_projection_protocol`.
    - Preconditions: Callers provide payload in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns dict[str, Any] whose verdict fields are derived from recomputed
      predicates, not trusted input labels.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    protocol = payload if isinstance(payload, dict) else {}
    source_refs = _strings(protocol.get("source_refs"))
    source_pattern_ids = _strings(protocol.get("source_pattern_ids"))
    projection_receipts = _strings(protocol.get("projection_receipt_refs"))
    target_refs = _strings(protocol.get("target_refs"))
    target_symbols = _strings(protocol.get("target_symbols"))
    public_runtime_refs = _strings(protocol.get("public_runtime_refs"))
    source_open_body_import_refs = _strings(
        protocol.get("source_open_body_import_refs")
    )
    body_import = protocol.get("body_import_verification", {})
    if not isinstance(body_import, dict):
        body_import = {}
    findings: list[dict[str, Any]] = []
    if (
        len(source_refs) < 5
        or "belief_state_process_reward_replay_compound" not in source_pattern_ids
        or len(projection_receipts) < 2
        or "system/lib/agent_execution_trace.py" not in source_refs
        or "codex/standards/std_agent_execution_trace.json" not in source_refs
        or not any(ref.endswith("macro_tools/agent_execution_trace.py") for ref in target_refs)
        or not any(
            ref.endswith("organs/belief_state_process_reward_replay.py")
            for ref in target_refs
        )
        or not any(
            ref.endswith("build_public_belief_state_process_reward_trace")
            for ref in target_symbols
        )
        or not any(ref.endswith("run_reward_bundle") for ref in target_symbols)
        or not public_runtime_refs
        or len(source_open_body_import_refs) < 3
        or not _strings(protocol.get("reimplemented"))
        or not _strings(protocol.get("omitted"))
        or protocol.get("body_import_status")
        != "extension_of_existing_public_refactor_landed"
        or body_import.get("verification_status") != "verified"
        or body_import.get("body_import_classification")
        != "extension_of_existing_public_refactor"
        or protocol.get("body_in_receipt") is not False
    ):
        findings.append(
            _finding(
                "BELIEF_REWARD_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Projection protocol must cite source refs, projection receipts, target refs, target symbols, public runtime refs, body-import verification, reimplemented pieces, and omissions.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    for field in (
        "copied_hidden_reasoning",
        "copied_provider_payloads",
        "copied_private_memory_bodies",
    ):
        if protocol.get(field) is not False:
            findings.append(
                _finding(
                    "BELIEF_REWARD_PRIVATE_BODY_COPY_CLAIM",
                    "Projection protocol must explicitly deny copying hidden reasoning, provider payloads, or private memory bodies.",
                    case_id="projection_protocol_floor",
                    subject_id=field,
                    subject_kind="projection_protocol",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "protocol_id": protocol.get("protocol_id"),
        "source_refs": source_refs,
        "source_pattern_ids": source_pattern_ids,
        "projection_receipt_refs": projection_receipts,
        "target_refs": target_refs,
        "target_symbols": target_symbols,
        "public_runtime_refs": public_runtime_refs,
        "source_open_body_import_refs": source_open_body_import_refs,
        "body_import_status": protocol.get("body_import_status"),
        "body_import_verification": body_import,
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_reward_policy(payload: object) -> dict[str, Any]:
    """[ACTION] Validate reward policy against the fixture evidence and authority ceiling.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `validate_reward_policy`.
    - Preconditions: Callers provide payload in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns dict[str, Any] whose verdict fields are derived from recomputed
      predicates, not trusted input labels.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments; module constants REQUIRED_BELIEF_FIELDS.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: REQUIRED_BELIEF_FIELDS.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    policy = payload if isinstance(payload, dict) else {}
    required_fields = set(_strings(policy.get("required_belief_state_fields")))
    reward_sources = set(_strings(policy.get("allowed_process_reward_sources")))
    findings: list[dict[str, Any]] = []
    if not set(REQUIRED_BELIEF_FIELDS).issubset(required_fields):
        findings.append(
            _finding(
                "BELIEF_REWARD_POLICY_REQUIRED_FIELDS_INCOMPLETE",
                "Reward policy must require observation digest, typed belief state, prediction, feedback, discrepancy, trajectory, and redaction fields.",
                case_id="reward_policy_floor",
                subject_id=str(policy.get("policy_id") or "reward_policy"),
                subject_kind="reward_policy",
            )
        )
    if not {"deterministic_verifier", "observed_environment_feedback"}.issubset(
        reward_sources
    ):
        findings.append(
            _finding(
                "BELIEF_REWARD_POLICY_SOURCE_FLOOR_MISSING",
                "Process reward sources must include deterministic verifier and observed environment feedback refs.",
                case_id="reward_policy_floor",
                subject_id=str(policy.get("policy_id") or "reward_policy"),
                subject_kind="reward_policy",
            )
        )
    for field in (
        "hidden_reasoning_export_authorized",
        "neural_judge_only_authorized",
        "hidden_gold_label_authorized",
        "live_rl_training_authorized",
        "benchmark_score_claim_authorized",
        "provider_calls_authorized",
        "release_authorized",
    ):
        if policy.get(field) is not False:
            findings.append(
                _finding(
                    "BELIEF_REWARD_POLICY_AUTHORITY_OVERCLAIM",
                    "Belief-state reward policy cannot authorize hidden reasoning export, neural-judge-only labels, hidden gold labels, live RL, provider calls, benchmark claims, or release.",
                    case_id="reward_policy_floor",
                    subject_id=field,
                    subject_kind="reward_policy",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "policy_id": policy.get("policy_id"),
        "required_belief_state_fields": sorted(required_fields),
        "allowed_process_reward_sources": sorted(reward_sources),
        "minimum_reliability_score": float(policy.get("minimum_reliability_score") or 0),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_task_episodes(payload: object) -> dict[str, Any]:
    """[ACTION] Validate task episodes against the fixture evidence and authority ceiling.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `validate_task_episodes`.
    - Preconditions: Callers provide payload in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns dict[str, Any] whose verdict fields are derived from recomputed
      predicates, not trusted input labels.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments; module constants REQUIRED_TASK_TYPES.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: REQUIRED_TASK_TYPES.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    rows = _rows(payload, "episodes")
    findings: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for row in rows:
        reasons: list[str] = []
        task_type = str(row.get("task_type") or "")
        if task_type not in REQUIRED_TASK_TYPES:
            reasons.append("unknown_task_type")
        for field in (
            "episode_id",
            "task_spec_hash",
            "trajectory_group_id",
            "outcome_reward_ref",
            "cold_replay_ref",
        ):
            if not row.get(field):
                reasons.append(f"missing_{field}")
        if not _strings(row.get("observation_digest_refs")):
            reasons.append("missing_observation_digest_refs")
        if row.get("body_redacted") is not True:
            reasons.append("body_not_redacted")
        if row.get("private_ref_metadata_only") is not True:
            reasons.append("private_ref_not_metadata_only")
        if _has_forbidden_key(row):
            reasons.append("forbidden_private_payload_key")
        accepted.append(
            {
                "episode_id": str(row.get("episode_id") or ""),
                "task_type": task_type,
                "trajectory_group_id": row.get("trajectory_group_id"),
                "observation_digest_count": len(
                    _strings(row.get("observation_digest_refs"))
                ),
                "outcome_reward_ref": row.get("outcome_reward_ref"),
                "cold_replay_ref": row.get("cold_replay_ref"),
                "computed_verdict": "accepted_episode" if not reasons else "blocked",
                "reason_codes": sorted(set(reasons)),
                "body_in_receipt": False,
            }
        )
    task_types = {row["task_type"] for row in accepted if not row["reason_codes"]}
    if (
        len(rows) < 3
        or not set(REQUIRED_TASK_TYPES).issubset(task_types)
        or any(row["reason_codes"] for row in accepted)
    ):
        findings.append(
            _finding(
                "BELIEF_REWARD_EPISODE_FLOOR_MISSING",
                "Positive fixture must include three redacted partially observable episodes with spec hashes, observation digests, outcome refs, and cold replay refs.",
                case_id="episode_floor",
                subject_id="task_episodes",
                subject_kind="episode_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "episode_count": len(rows),
        "accepted_episode_count": sum(1 for row in accepted if not row["reason_codes"]),
        "task_types": sorted(task_types),
        "episode_rows": sorted(accepted, key=lambda row: row["episode_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_belief_states(payload: object) -> dict[str, Any]:
    """[ACTION] Validate belief states against the fixture evidence and authority ceiling.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `validate_belief_states`.
    - Preconditions: Callers provide payload in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns dict[str, Any] whose verdict fields are derived from recomputed
      predicates, not trusted input labels.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments; module constants REQUIRED_BELIEF_FIELDS.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: REQUIRED_BELIEF_FIELDS.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    rows = _rows(payload, "belief_states")
    findings: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for row in rows:
        belief_id = str(row.get("belief_state_id") or "")
        reasons: list[str] = []
        missing = [
            field
            for field in REQUIRED_BELIEF_FIELDS
            if field not in row or row.get(field) in (None, "", [])
        ]
        if missing:
            reasons.append("missing_required_fields")
        belief_state = row.get("belief_state_json")
        if not isinstance(belief_state, dict):
            reasons.append("belief_state_not_typed_json")
        elif _has_forbidden_key(belief_state):
            reasons.append("forbidden_private_payload_key")
        if not _strings(row.get("predicted_next_evidence")):
            reasons.append("missing_predicted_next_evidence")
        if not row.get("feedback_ref"):
            reasons.append("missing_feedback_ref")
        if not _is_numeric_value(row.get("belief_discrepancy")):
            reasons.append("missing_belief_discrepancy")
        if row.get("hidden_chain_of_thought_exported") is not False:
            reasons.append("hidden_reasoning_export")
        if row.get("body_redacted") is not True:
            reasons.append("body_not_redacted")
        if row.get("private_ref_metadata_only") is not True:
            reasons.append("private_ref_not_metadata_only")
        if _has_forbidden_key(row):
            reasons.append("forbidden_private_payload_key")
        accepted.append(
            {
                "belief_state_id": belief_id,
                "episode_id": row.get("episode_id"),
                "step_id": row.get("step_id"),
                "observation_digest_ref": row.get("observation_digest_ref"),
                "predicted_next_evidence_count": len(
                    _strings(row.get("predicted_next_evidence"))
                ),
                "feedback_ref": row.get("feedback_ref"),
                "belief_discrepancy": row.get("belief_discrepancy"),
                "trajectory_group_id": row.get("trajectory_group_id"),
                "computed_verdict": "accepted_belief_state"
                if not reasons
                else "blocked",
                "reason_codes": sorted(set(reasons)),
                "body_in_receipt": False,
            }
        )
    if len(rows) < 6 or any(row["reason_codes"] for row in accepted):
        findings.append(
            _finding(
                "BELIEF_REWARD_BELIEF_STATE_FLOOR_MISSING",
                "Positive fixture must expose typed redacted belief-state JSON with observation digest, prediction, feedback, discrepancy, and trajectory refs.",
                case_id="belief_state_floor",
                subject_id="belief_states",
                subject_kind="belief_state_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "belief_state_count": len(rows),
        "accepted_belief_state_count": sum(
            1 for row in accepted if not row["reason_codes"]
        ),
        "belief_state_rows": sorted(accepted, key=lambda row: row["belief_state_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_verifier_feedback(payload: object) -> dict[str, Any]:
    """[ACTION] Validate verifier feedback against the fixture evidence and authority ceiling.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `validate_verifier_feedback`.
    - Preconditions: Callers provide payload in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns dict[str, Any] whose verdict fields are derived from recomputed
      predicates, not trusted input labels.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    rows = _rows(payload, "feedback")
    findings: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for row in rows:
        reasons: list[str] = []
        score = float(row.get("reliability_score") or 0)
        if row.get("feedback_kind") not in {
            "deterministic_verifier",
            "observed_environment_feedback",
        }:
            reasons.append("unknown_feedback_kind")
        if score < 0.8:
            reasons.append("reliability_below_floor")
        if row.get("neural_judge_only") is True:
            reasons.append("neural_judge_only")
        if row.get("hidden_gold_label_present") is True:
            reasons.append("hidden_gold_label")
        if not _strings(row.get("evidence_refs")):
            reasons.append("missing_evidence_refs")
        if row.get("body_redacted") is not True:
            reasons.append("body_not_redacted")
        if _has_forbidden_key(row):
            reasons.append("forbidden_private_payload_key")
        accepted.append(
            {
                "feedback_id": str(row.get("feedback_id") or ""),
                "episode_id": row.get("episode_id"),
                "feedback_kind": row.get("feedback_kind"),
                "reliability_score": score,
                "evidence_ref_count": len(_strings(row.get("evidence_refs"))),
                "computed_verdict": "accepted_feedback" if not reasons else "blocked",
                "reason_codes": sorted(set(reasons)),
                "body_in_receipt": False,
            }
        )
    if len(rows) < 6 or any(row["reason_codes"] for row in accepted):
        findings.append(
            _finding(
                "BELIEF_REWARD_VERIFIER_FEEDBACK_FLOOR_MISSING",
                "Positive fixture must carry reliable deterministic verifier or observed feedback refs, not neural-judge-only or hidden-gold labels.",
                case_id="verifier_feedback_floor",
                subject_id="verifier_feedback",
                subject_kind="feedback_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "feedback_count": len(rows),
        "accepted_feedback_count": sum(
            1 for row in accepted if not row["reason_codes"]
        ),
        "feedback_rows": sorted(accepted, key=lambda row: row["feedback_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_reward_events(payload: object) -> dict[str, Any]:
    """[ACTION] Validate reward events against the fixture evidence and authority ceiling.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `validate_reward_events`.
    - Preconditions: Callers provide payload in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns dict[str, Any] whose verdict fields are derived from recomputed
      predicates, not trusted input labels.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    rows = _rows(payload, "reward_events")
    findings: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for row in rows:
        reasons: list[str] = []
        reward_kind = str(row.get("reward_kind") or "")
        if reward_kind not in {"process", "outcome"}:
            reasons.append("unknown_reward_kind")
        if not row.get("belief_state_id") and reward_kind == "process":
            reasons.append("missing_belief_state_ref")
        if not row.get("verifier_feedback_ref"):
            reasons.append("missing_verifier_feedback_ref")
        if not _is_numeric_value(row.get("reward_value")):
            reasons.append("missing_reward_value")
        if not _is_numeric_value(row.get("belief_discrepancy")):
            reasons.append("missing_belief_discrepancy")
        if row.get("reward_hacking_trap_result") != PASS:
            reasons.append("reward_hacking_trap_failed")
        if row.get("reward_by_formatting") is True:
            reasons.append("reward_by_formatting")
        if row.get("verifier_bypassed") is True:
            reasons.append("verifier_bypassed")
        if row.get("final_answer_only_scoring") is True:
            reasons.append("final_answer_only_scoring")
        if row.get("body_redacted") is not True:
            reasons.append("body_not_redacted")
        accepted.append(
            {
                "reward_event_id": str(row.get("reward_event_id") or ""),
                "episode_id": row.get("episode_id"),
                "belief_state_id": row.get("belief_state_id"),
                "reward_kind": reward_kind,
                "reward_value": row.get("reward_value"),
                "belief_discrepancy": row.get("belief_discrepancy"),
                "verifier_feedback_ref": row.get("verifier_feedback_ref"),
                "reward_hacking_trap_result": row.get("reward_hacking_trap_result"),
                "computed_verdict": "accepted_reward_event"
                if not reasons
                else "blocked",
                "reason_codes": sorted(set(reasons)),
                "body_in_receipt": False,
            }
        )
    process_count = sum(
        1
        for row in accepted
        if row["reward_kind"] == "process" and not row["reason_codes"]
    )
    outcome_count = sum(
        1
        for row in accepted
        if row["reward_kind"] == "outcome" and not row["reason_codes"]
    )
    if process_count < 6 or outcome_count < 3 or any(row["reason_codes"] for row in accepted):
        findings.append(
            _finding(
                "BELIEF_REWARD_EVENT_FLOOR_MISSING",
                "Positive fixture must carry process and outcome rewards tied to feedback refs, belief discrepancy, and reward-hacking trap results.",
                case_id="reward_event_floor",
                subject_id="reward_events",
                subject_kind="reward_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "reward_event_count": len(rows),
        "process_reward_count": process_count,
        "outcome_reward_count": outcome_count,
        "reward_rows": sorted(accepted, key=lambda row: row["reward_event_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_trajectory_groups(payload: object) -> dict[str, Any]:
    """[ACTION] Validate trajectory groups against the fixture evidence and authority ceiling.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `validate_trajectory_groups`.
    - Preconditions: Callers provide payload in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns dict[str, Any] whose verdict fields are derived from recomputed
      predicates, not trusted input labels.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    rows = _rows(payload, "trajectory_groups")
    findings: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for row in rows:
        reasons: list[str] = []
        if not row.get("trajectory_group_id"):
            reasons.append("missing_trajectory_group_id")
        if not _strings(row.get("episode_ids")):
            reasons.append("missing_episode_ids")
        if not _strings(row.get("process_reward_refs")):
            reasons.append("missing_process_reward_refs")
        if not row.get("outcome_reward_ref"):
            reasons.append("missing_outcome_reward_ref")
        if row.get("reward_alignment") != "aligned":
            reasons.append("reward_alignment_not_aligned")
        if row.get("cold_replay_status") != PASS:
            reasons.append("cold_replay_not_pass")
        if row.get("body_redacted") is not True:
            reasons.append("body_not_redacted")
        accepted.append(
            {
                "trajectory_group_id": str(row.get("trajectory_group_id") or ""),
                "episode_ids": _strings(row.get("episode_ids")),
                "process_reward_ref_count": len(_strings(row.get("process_reward_refs"))),
                "outcome_reward_ref": row.get("outcome_reward_ref"),
                "reward_alignment": row.get("reward_alignment"),
                "cold_replay_status": row.get("cold_replay_status"),
                "computed_verdict": "accepted_trajectory_group"
                if not reasons
                else "blocked",
                "reason_codes": sorted(set(reasons)),
                "body_in_receipt": False,
            }
        )
    if len(rows) < 3 or any(row["reason_codes"] for row in accepted):
        findings.append(
            _finding(
                "BELIEF_REWARD_TRAJECTORY_GROUP_FLOOR_MISSING",
                "Positive fixture must group each task trajectory with process rewards, outcome reward, alignment verdict, and cold replay pass.",
                case_id="trajectory_group_floor",
                subject_id="trajectory_groups",
                subject_kind="trajectory_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "trajectory_group_count": len(rows),
        "accepted_trajectory_group_count": sum(
            1 for row in accepted if not row["reason_codes"]
        ),
        "trajectory_group_rows": sorted(
            accepted, key=lambda row: row["trajectory_group_id"]
        ),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_cold_replay(payload: object) -> dict[str, Any]:
    """[ACTION] Validate cold replay against the fixture evidence and authority ceiling.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `validate_cold_replay`.
    - Preconditions: Callers provide payload in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns dict[str, Any] whose verdict fields are derived from recomputed
      predicates, not trusted input labels.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    rows = _rows(payload, "cold_replays")
    findings: list[dict[str, Any]] = []
    passing = [
        row
        for row in rows
        if row.get("status") == PASS
        and row.get("body_redacted") is True
        and row.get("private_ref_metadata_only") is True
    ]
    if len(passing) < 3:
        findings.append(
            _finding(
                "BELIEF_REWARD_COLD_REPLAY_FLOOR_MISSING",
                "Positive fixture must include redacted cold replay receipts for all three trajectory groups.",
                case_id="cold_replay_floor",
                subject_id="cold_replay",
                subject_kind="cold_replay_fixture",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "cold_replay_count": len(rows),
        "cold_replay_pass_count": len(passing),
        "cold_replay_rows": [
            {
                "replay_id": str(row.get("replay_id") or ""),
                "trajectory_group_id": str(row.get("trajectory_group_id") or ""),
                "status": row.get("status"),
                "evidence_refs": _strings(row.get("evidence_refs")),
                "body_in_receipt": False,
                "private_ref_metadata_only": row.get("private_ref_metadata_only") is True,
            }
            for row in rows
        ],
        "findings": findings,
        "observed_negative_cases": {},
    }


def _index_by_id(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    """[ACTION] Implement index by ID for this organ replay.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_index_by_id`.
    - Preconditions: Callers provide rows, key in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns dict[str, dict[str, Any]] from the explicit return paths in the
      function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    return {str(row.get(key)): row for row in rows if row.get(key)}


def validate_semantic_recompute(payloads: dict[str, object]) -> dict[str, Any]:
    """[ACTION] Validate semantic recompute against the fixture evidence and authority ceiling.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `validate_semantic_recompute`.
    - Preconditions: Callers provide payloads in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns dict[str, Any] whose verdict fields are derived from recomputed
      predicates, not trusted input labels.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    episodes = _rows(payloads.get("task_episodes"), "episodes")
    beliefs = _rows(payloads.get("belief_states"), "belief_states")
    feedback_rows = _rows(payloads.get("verifier_feedback"), "feedback")
    reward_rows = _rows(payloads.get("reward_events"), "reward_events")
    trajectory_rows = _rows(payloads.get("trajectory_groups"), "trajectory_groups")
    cold_rows = _rows(payloads.get("cold_replay"), "cold_replays")

    episodes_by_id = _index_by_id(episodes, "episode_id")
    beliefs_by_id = _index_by_id(beliefs, "belief_state_id")
    feedback_by_id = _index_by_id(feedback_rows, "feedback_id")
    rewards_by_id = _index_by_id(reward_rows, "reward_event_id")
    trajectories_by_id = _index_by_id(trajectory_rows, "trajectory_group_id")
    cold_by_replay_id = _index_by_id(cold_rows, "replay_id")
    cold_by_trajectory_id = _index_by_id(cold_rows, "trajectory_group_id")
    process_reward_by_belief = {
        str(row.get("belief_state_id")): row
        for row in reward_rows
        if row.get("belief_state_id") and row.get("reward_kind") == "process"
    }

    findings: list[dict[str, Any]] = []
    semantic_rows: list[dict[str, Any]] = []

    def add_reason(reasons: list[str], reason: str) -> None:
        """[ACTION] Implement add reason for this organ replay.

        - Teleology: Supports belief state process reward replay by documenting and
          preserving the exact local step implemented by `add_reason`.
        - Preconditions: Callers provide reasons, reason in the shape consumed by the
          body.
        - Mechanism: Delegates to reasons.append and applies local branch checks.
        - Guarantee: Returns None from the explicit return paths in the function body.
        - Fails: No explicit raise is introduced; failures propagate from ordinary
          Python evaluation in this body.
        - Reads: call arguments.
        - Writes: No external writes; the body only returns in-memory values.
        - Non-goal: Does not widen this module's public authority ceiling, add provider
          calls, or expose private material.
        """
        if reason not in reasons:
            reasons.append(reason)

    for belief in beliefs:
        belief_id = str(belief.get("belief_state_id") or "")
        episode_id = str(belief.get("episode_id") or "")
        feedback_id = str(belief.get("feedback_ref") or "")
        trajectory_id = str(belief.get("trajectory_group_id") or "")
        reasons: list[str] = []

        episode = episodes_by_id.get(episode_id)
        feedback = feedback_by_id.get(feedback_id)
        process_reward = process_reward_by_belief.get(belief_id)
        trajectory = trajectories_by_id.get(trajectory_id)
        cold_replay = cold_by_trajectory_id.get(trajectory_id)

        if episode is None:
            add_reason(reasons, "episode_ref_missing")
        if feedback is None:
            add_reason(reasons, "feedback_ref_missing")
        elif str(feedback.get("episode_id") or "") != episode_id:
            add_reason(reasons, "feedback_episode_mismatch")
        if process_reward is None:
            add_reason(reasons, "process_reward_ref_missing")
        else:
            if str(process_reward.get("episode_id") or "") != episode_id:
                add_reason(reasons, "process_reward_episode_mismatch")
            if str(process_reward.get("trajectory_group_id") or "") != trajectory_id:
                add_reason(reasons, "process_reward_trajectory_mismatch")
            if str(process_reward.get("verifier_feedback_ref") or "") != feedback_id:
                add_reason(reasons, "process_reward_feedback_mismatch")
            if process_reward.get("belief_discrepancy") != belief.get(
                "belief_discrepancy"
            ):
                add_reason(reasons, "belief_discrepancy_mismatch")
        if trajectory is None:
            add_reason(reasons, "trajectory_ref_missing")
            outcome_reward = None
        else:
            if episode_id not in _strings(trajectory.get("episode_ids")):
                add_reason(reasons, "trajectory_episode_mismatch")
            process_reward_id = (
                str(process_reward.get("reward_event_id") or "")
                if process_reward is not None
                else ""
            )
            if process_reward_id and process_reward_id not in _strings(
                trajectory.get("process_reward_refs")
            ):
                add_reason(reasons, "trajectory_process_reward_missing")
            outcome_reward_ref = str(trajectory.get("outcome_reward_ref") or "")
            outcome_reward = rewards_by_id.get(outcome_reward_ref)
            if outcome_reward is None:
                add_reason(reasons, "outcome_reward_ref_missing")
            else:
                if str(outcome_reward.get("reward_kind") or "") != "outcome":
                    add_reason(reasons, "outcome_reward_kind_mismatch")
                if str(outcome_reward.get("episode_id") or "") != episode_id:
                    add_reason(reasons, "outcome_reward_episode_mismatch")
                if str(outcome_reward.get("trajectory_group_id") or "") != trajectory_id:
                    add_reason(reasons, "outcome_reward_trajectory_mismatch")
                outcome_feedback_ref = str(
                    outcome_reward.get("verifier_feedback_ref") or ""
                )
                if outcome_feedback_ref not in feedback_by_id:
                    add_reason(reasons, "outcome_reward_feedback_missing")
                elif (
                    str(feedback_by_id[outcome_feedback_ref].get("episode_id") or "")
                    != episode_id
                ):
                    add_reason(reasons, "outcome_reward_feedback_episode_mismatch")
        if cold_replay is None:
            add_reason(reasons, "cold_replay_ref_missing")
        elif cold_replay.get("status") != PASS:
            add_reason(reasons, "cold_replay_not_pass")
        if episode is not None:
            cold_ref = str(episode.get("cold_replay_ref") or "")
            episode_cold = cold_by_replay_id.get(cold_ref)
            if episode_cold is None:
                add_reason(reasons, "episode_cold_replay_ref_missing")
            elif str(episode_cold.get("trajectory_group_id") or "") != trajectory_id:
                add_reason(reasons, "episode_cold_replay_trajectory_mismatch")

        semantic_rows.append(
            {
                "belief_state_id": belief_id,
                "episode_id": episode_id,
                "feedback_ref": feedback_id,
                "process_reward_ref": str(
                    process_reward.get("reward_event_id") or ""
                )
                if process_reward is not None
                else "",
                "trajectory_group_id": trajectory_id,
                "cold_replay_ref": str(cold_replay.get("replay_id") or "")
                if cold_replay is not None
                else "",
                "computed_verdict": "verified_semantic_recompute"
                if not reasons
                else "blocked",
                "reason_codes": sorted(reasons),
                "body_in_receipt": False,
            }
        )

    for trajectory in trajectory_rows:
        trajectory_id = str(trajectory.get("trajectory_group_id") or "")
        for reward_ref in _strings(trajectory.get("process_reward_refs")):
            reward = rewards_by_id.get(reward_ref)
            if reward is None:
                findings.append(
                    _finding(
                        "BELIEF_REWARD_SEMANTIC_RECOMPUTE_MISMATCH",
                        "Trajectory process reward refs must resolve to real process reward rows.",
                        case_id="semantic_recompute_floor",
                        subject_id=reward_ref,
                        subject_kind="trajectory_process_reward_ref",
                    )
                )
                continue
            belief_id = str(reward.get("belief_state_id") or "")
            if belief_id not in beliefs_by_id:
                findings.append(
                    _finding(
                        "BELIEF_REWARD_SEMANTIC_RECOMPUTE_MISMATCH",
                        "Process reward rows must resolve to real belief-state rows.",
                        case_id="semantic_recompute_floor",
                        subject_id=reward_ref,
                        subject_kind="process_reward_belief_ref",
                    )
                )
            if str(reward.get("trajectory_group_id") or "") != trajectory_id:
                findings.append(
                    _finding(
                        "BELIEF_REWARD_SEMANTIC_RECOMPUTE_MISMATCH",
                        "Process reward rows must belong to the trajectory that cites them.",
                        case_id="semantic_recompute_floor",
                        subject_id=reward_ref,
                        subject_kind="process_reward_trajectory_ref",
                    )
                )

    blocked_rows = [row for row in semantic_rows if row["reason_codes"]]
    for row in blocked_rows:
        findings.append(
            {
                **_finding(
                    "BELIEF_REWARD_SEMANTIC_RECOMPUTE_MISMATCH",
                    "Belief-state, feedback, process reward, trajectory, outcome reward, and cold replay refs must recompute to one coherent public-safe process-reward chain.",
                    case_id="semantic_recompute_floor",
                    subject_id=str(row["belief_state_id"]),
                    subject_kind="belief_state_semantic_recompute",
                ),
                "reason_codes": row["reason_codes"],
            }
        )

    return {
        "status": PASS if not findings else "blocked",
        "semantic_recompute_row_count": len(semantic_rows),
        "semantic_recompute_verified_count": len(semantic_rows) - len(blocked_rows),
        "semantic_recompute_blocked_count": len(blocked_rows),
        "semantic_recompute_rows": sorted(
            semantic_rows, key=lambda row: row["belief_state_id"]
        ),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_negative_cases(payloads: dict[str, object]) -> dict[str, Any]:
    """[ACTION] Validate negative cases against the fixture evidence and authority ceiling.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `validate_negative_cases`.
    - Preconditions: Callers provide payloads in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns dict[str, Any] whose verdict fields are derived from recomputed
      predicates, not trusted input labels.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for row in _negative_rows(payloads):
        case_id = str(row.get("expected_negative_case_id") or row.get("case_id") or "")
        subject_id = str(row.get("case_id") or case_id or "negative_case")
        if row.get("hidden_chain_of_thought_exported") is True or _has_forbidden_key(row):
            _record(
                findings,
                observed,
                "BELIEF_REWARD_HIDDEN_COT_EXPORT",
                "Belief-state summaries cannot export hidden chain-of-thought or private reasoning bodies.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="negative_case",
            )
        if row.get("neural_judge_only") is True and not row.get("verifier_receipt_ref"):
            _record(
                findings,
                observed,
                "BELIEF_REWARD_NEURAL_JUDGE_ONLY_LABEL",
                "Process reward labels need observable verifier or feedback refs; neural-judge-only labels are not admitted.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="negative_case",
            )
        if row.get("hidden_gold_label_present") is True:
            _record(
                findings,
                observed,
                "BELIEF_REWARD_HIDDEN_GOLD_LABEL",
                "Hidden gold labels cannot appear in public process-reward fixtures.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="negative_case",
            )
        if row.get("reward_by_formatting") is True or row.get(
            "reward_hacking_trap_result"
        ) == "fail":
            _record(
                findings,
                observed,
                "BELIEF_REWARD_FORMAT_REWARD_HACK",
                "Reward-by-formatting and failed reward-hacking traps must block claim admission.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="negative_case",
            )
        if row.get("verifier_bypassed") is True or (
            row.get("verifier_feedback_required") is True
            and not row.get("verifier_feedback_ref")
        ):
            _record(
                findings,
                observed,
                "BELIEF_REWARD_VERIFIER_BYPASS",
                "Verifier or observed feedback refs cannot be bypassed by a process reward claim.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="negative_case",
            )
        if row.get("benchmark_performance_claim") is True:
            _record(
                findings,
                observed,
                "BELIEF_REWARD_BENCHMARK_CLAIM",
                "Public belief-state process reward replay cannot claim benchmark performance.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="negative_case",
            )
        if row.get("final_answer_only_scoring") is True:
            _record(
                findings,
                observed,
                "BELIEF_REWARD_FINAL_ANSWER_ONLY",
                "Final-answer-only scoring is not process reward; observation, belief, feedback, and reward receipts are required.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="negative_case",
            )
    return {
        "status": PASS,
        "findings": findings,
        "observed_negative_cases": {
            key: sorted(value) for key, value in observed.items()
        },
    }


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    """[ACTION] Assemble the replay result payload from validated evidence.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_build_result`.
    - Preconditions: Callers provide input_dir, command, input_mode, include_negative in
      the shape consumed by the body.
    - Mechanism: Normalizes Path values and public-root-relative references before
      returning them. Iterates candidate paths or structured rows exactly as written in
      the body.
    - Guarantee: Returns dict[str, Any] from the explicit return paths in the function
      body.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments; module constants ANTI_CLAIM, AUTHORITY_CEILING,
      EXPECTED_NEGATIVE_CASES, FIXTURE_ID, NEGATIVE_INPUT_NAMES, ORGAN_ID, VALIDATOR_ID.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: ANTI_CLAIM, AUTHORITY_CEILING, EXPECTED_NEGATIVE_CASES, FIXTURE_ID,
      NEGATIVE_INPUT_NAMES, ORGAN_ID, VALIDATOR_ID.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    secret_scan = scan_paths(
        _scan_paths_for_input(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )
    public_trace = build_public_belief_state_process_reward_trace(input_dir)

    negative_payloads = {
        name: payloads[name]
        for name in (Path(item).stem for item in NEGATIVE_INPUT_NAMES)
        if name in payloads
    }
    projection = validate_projection_protocol(payloads["projection_protocol"])
    reward_policy = validate_reward_policy(payloads["reward_policy"])
    episodes = validate_task_episodes(payloads["task_episodes"])
    belief_states = validate_belief_states(payloads["belief_states"])
    feedback = validate_verifier_feedback(payloads["verifier_feedback"])
    rewards = validate_reward_events(payloads["reward_events"])
    trajectories = validate_trajectory_groups(payloads["trajectory_groups"])
    cold_replay = validate_cold_replay(payloads["cold_replay"])
    semantics = validate_semantic_recompute(payloads)
    negatives = validate_negative_cases(negative_payloads)
    source_modules = _source_module_manifest_result(
        input_dir,
        public_root=public_root,
        require_manifest=input_mode == "exported_belief_state_process_reward_bundle",
    )
    source_open_body_imports = _source_open_body_import_summary(source_modules)

    observed = _merge_observed(
        projection,
        reward_policy,
        episodes,
        belief_states,
        feedback,
        rewards,
        trajectories,
        cold_replay,
        semantics,
        negatives,
        source_modules,
    )
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(
        projection,
        reward_policy,
        episodes,
        belief_states,
        feedback,
        rewards,
        trajectories,
        cold_replay,
        semantics,
        negatives,
        source_modules,
    )
    positive_findings = _merge_findings(
        projection,
        reward_policy,
        episodes,
        belief_states,
        feedback,
        rewards,
        trajectories,
        cold_replay,
        semantics,
        source_modules,
    )
    error_codes = sorted({str(row["error_code"]) for row in findings})
    bundle_manifest = payloads.get("bundle_manifest", {})
    status = (
        PASS
        if not missing
        and secret_scan["blocking_hit_count"] == 0
        and public_trace["status"] == PASS
        and not positive_findings
        and projection["status"] == PASS
        and reward_policy["status"] == PASS
        and episodes["status"] == PASS
        and belief_states["status"] == PASS
        and feedback["status"] == PASS
        and rewards["status"] == PASS
        and trajectories["status"] == PASS
        and cold_replay["status"] == PASS
        and semantics["status"] == PASS
        and (
            input_mode != "exported_belief_state_process_reward_bundle"
            or source_modules["status"] == PASS
        )
        else "blocked"
    )
    return {
        "schema_version": "belief_state_process_reward_replay_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id")
        if isinstance(bundle_manifest, dict)
        else None,
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "public_agent_execution_trace": public_trace,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_import_status": "extension_of_existing_public_refactor_landed",
        "body_import_classification": "extension_of_existing_public_refactor",
        "product_path_role": "source_faithful_public_agent_execution_trace_refactor",
        "body_import_verification": _body_import_verification(
            public_root=public_root,
            public_trace=public_trace,
        ),
        "body_in_receipt": False,
        "protocol_id": projection["protocol_id"],
        "source_refs": projection["source_refs"],
        "source_pattern_ids": projection["source_pattern_ids"],
        "projection_receipt_refs": projection["projection_receipt_refs"],
        "target_refs": projection["target_refs"],
        "target_symbols": projection["target_symbols"],
        "public_runtime_refs": projection["public_runtime_refs"],
        "source_open_body_import_refs": projection["source_open_body_import_refs"],
        "source_module_manifest_status": source_modules["status"],
        "source_module_manifest_ref": source_modules["source_module_manifest_ref"],
        "source_module_imports": source_modules,
        "source_open_body_imports": source_open_body_imports,
        "body_material_status": source_open_body_imports["body_material_status"],
        "body_copied_material_count": source_open_body_imports[
            "body_material_count"
        ],
        "reward_policy_id": reward_policy["policy_id"],
        "allowed_process_reward_sources": reward_policy[
            "allowed_process_reward_sources"
        ],
        "minimum_reliability_score": reward_policy["minimum_reliability_score"],
        "episode_count": episodes["episode_count"],
        "accepted_episode_count": episodes["accepted_episode_count"],
        "belief_state_count": belief_states["belief_state_count"],
        "accepted_belief_state_count": belief_states["accepted_belief_state_count"],
        "feedback_count": feedback["feedback_count"],
        "accepted_feedback_count": feedback["accepted_feedback_count"],
        "reward_event_count": rewards["reward_event_count"],
        "process_reward_count": rewards["process_reward_count"],
        "outcome_reward_count": rewards["outcome_reward_count"],
        "trajectory_group_count": trajectories["trajectory_group_count"],
        "accepted_trajectory_group_count": trajectories[
            "accepted_trajectory_group_count"
        ],
        "cold_replay_count": cold_replay["cold_replay_count"],
        "cold_replay_pass_count": cold_replay["cold_replay_pass_count"],
        "semantic_recompute_status": semantics["status"],
        "semantic_recompute_row_count": semantics["semantic_recompute_row_count"],
        "semantic_recompute_verified_count": semantics[
            "semantic_recompute_verified_count"
        ],
        "semantic_recompute_blocked_count": semantics["semantic_recompute_blocked_count"],
        "episode_rows": episodes["episode_rows"],
        "belief_state_rows": belief_states["belief_state_rows"],
        "feedback_rows": feedback["feedback_rows"],
        "reward_rows": rewards["reward_rows"],
        "trajectory_group_rows": trajectories["trajectory_group_rows"],
        "cold_replay_rows": cold_replay["cold_replay_rows"],
        "semantic_recompute_rows": semantics["semantic_recompute_rows"],
    }


def _board_from_result(result: dict[str, Any]) -> dict[str, Any]:
    """[ACTION] Build the board projection from a replay result payload.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_board_from_result`.
    - Preconditions: Callers provide result in the shape consumed by the body.
    - Mechanism: Uses local branch checks, literals, and comprehensions to compute the
      return value.
    - Guarantee: Returns dict[str, Any] from the explicit return paths in the function
      body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments; module constants ORGAN_ID.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: ORGAN_ID.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    return {
        "schema_version": "belief_state_process_reward_replay_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "belief_state_process_reward_replay_public_board",
        "input_mode": result["input_mode"],
        "source_pattern_ids": result["source_pattern_ids"],
        "mechanics": [
            {
                "mechanic_id": "typed_belief_summaries_not_hidden_reasoning",
                "count": result["accepted_belief_state_count"],
                "authority": "belief_state_json is a public summary with hidden reasoning explicitly absent",
            },
            {
                "mechanic_id": "verifier_backed_process_reward",
                "count": result["accepted_feedback_count"],
                "authority": "process reward is tied to deterministic verifier or observed feedback refs",
            },
            {
                "mechanic_id": "process_and_outcome_joint_replay",
                "count": result["reward_event_count"],
                "authority": "process and outcome rewards are replayed together before claim admission",
            },
            {
                "mechanic_id": "reward_hacking_traps_and_cold_replay",
                "count": result["cold_replay_pass_count"],
                "authority": "reward-hacking trap pass and cold replay receipts bound every trajectory group",
            },
            {
                "mechanic_id": "semantic_recompute_chain",
                "count": result["semantic_recompute_verified_count"],
                "authority": "belief, feedback, process reward, trajectory, outcome reward, and cold replay refs recompute before admission",
            },
        ],
        "episode_rows": result["episode_rows"],
        "belief_state_rows": result["belief_state_rows"],
        "feedback_rows": result["feedback_rows"],
        "reward_rows": result["reward_rows"],
        "trajectory_group_rows": result["trajectory_group_rows"],
        "cold_replay_rows": result["cold_replay_rows"],
        "semantic_recompute_rows": result["semantic_recompute_rows"],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_open_body_imports": result["source_open_body_imports"],
        "body_copied_material_count": result["body_copied_material_count"],
        "body_in_receipt": False,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "body_import_status": result["body_import_status"],
        "body_import_classification": result["body_import_classification"],
        "body_import_verification": result["body_import_verification"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
    }


def _write_receipts(
    result: dict[str, Any],
    out_dir: Path,
    *,
    acceptance_out: Path | None,
) -> dict[str, Any]:
    """[ACTION] Write replay receipt payloads and return their public references.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_write_receipts`.
    - Preconditions: Callers provide result, out_dir, acceptance_out in the shape
      consumed by the body; write targets must be inside the caller-selected output or
      temporary area.
    - Mechanism: Writes only the output paths named by the caller, temporary workspace,
      or module constants.
    - Guarantee: Returns dict[str, Any] after writing only the declared receipt/output
      artifacts.
    - Fails: No explicit raise is introduced; failures propagate from filesystem writes,
      called validators/helpers.
    - Reads: call arguments; module constants ACCEPTANCE_RECEIPT_REL, BOARD_NAME,
      FIXTURE_ID, ORGAN_ID, RESULT_NAME, VALIDATION_RECEIPT_NAME, VALIDATOR_ID.
    - Writes: filesystem output explicitly written by this body.
    - Couples: ACCEPTANCE_RECEIPT_REL, BOARD_NAME, FIXTURE_ID, ORGAN_ID, RESULT_NAME,
      VALIDATION_RECEIPT_NAME, VALIDATOR_ID.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(out_dir)
    result_path = out_dir / RESULT_NAME
    board_path = out_dir / BOARD_NAME
    validation_path = out_dir / VALIDATION_RECEIPT_NAME
    acceptance_path = (
        acceptance_out
        if acceptance_out is not None
        else public_root / ACCEPTANCE_RECEIPT_REL
    )
    acceptance_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_paths = [
        _display(result_path, public_root=public_root),
        _display(board_path, public_root=public_root),
        _display(validation_path, public_root=public_root),
        _display(acceptance_path, public_root=public_root),
    ]
    result_receipt = {
        **result,
        "schema_version": "belief_state_process_reward_replay_result_receipt_v1",
        "receipt_paths": receipt_paths,
    }
    board = {**_board_from_result(result), "receipt_paths": receipt_paths}
    validation = {
        "schema_version": "belief_state_process_reward_replay_validation_receipt_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "negative_case_coverage": {
            "expected": result["expected_negative_cases"],
            "observed": result["observed_negative_cases"],
            "missing": result["missing_negative_cases"],
        },
        "episode_count": result["episode_count"],
        "belief_state_count": result["belief_state_count"],
        "accepted_feedback_count": result["accepted_feedback_count"],
        "process_reward_count": result["process_reward_count"],
        "outcome_reward_count": result["outcome_reward_count"],
        "trajectory_group_count": result["trajectory_group_count"],
        "cold_replay_pass_count": result["cold_replay_pass_count"],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_open_body_imports": result["source_open_body_imports"],
        "body_copied_material_count": result["body_copied_material_count"],
        "semantic_recompute_status": result["semantic_recompute_status"],
        "semantic_recompute_row_count": result["semantic_recompute_row_count"],
        "semantic_recompute_verified_count": result["semantic_recompute_verified_count"],
        "semantic_recompute_blocked_count": result["semantic_recompute_blocked_count"],
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "body_import_verification": result["body_import_verification"],
        "body_in_receipt": False,
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    acceptance = {
        "schema_version": "belief_state_process_reward_replay_fixture_acceptance_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "accepted_negative_cases": result["expected_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "error_codes": result["error_codes"],
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "body_import_verification": result["body_import_verification"],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_open_body_imports": result["source_open_body_imports"],
        "body_copied_material_count": result["body_copied_material_count"],
        "body_in_receipt": False,
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    write_json_atomic(result_path, result_receipt)
    write_json_atomic(board_path, board)
    write_json_atomic(validation_path, validation)
    write_json_atomic(acceptance_path, acceptance)
    return {**result, "reward_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = (
        "python -m microcosm_core.organs.belief_state_process_reward_replay run"
    ),
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """[ACTION] Run the organ replay pipeline and return the computed result payload.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `run`.
    - Preconditions: Callers provide input_dir, out_dir, command, acceptance_out in the
      shape consumed by the body.
    - Mechanism: Normalizes Path values and public-root-relative references before
      returning them.
    - Guarantee: Returns dict[str, Any] representing the completed replay or bundle
      execution.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="fixture",
        include_negative=True,
    )
    result["freshness_basis"] = _freshness_basis(Path(input_dir), include_negative=True)
    result["receipt_reused"] = False
    return _write_receipts(
        result,
        Path(out_dir),
        acceptance_out=Path(acceptance_out) if acceptance_out is not None else None,
    )


def run_reward_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs."
        "belief_state_process_reward_replay run-reward-bundle"
    ),
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    """[ACTION] Implement run reward bundle for this organ replay.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `run_reward_bundle`.
    - Preconditions: Callers provide input_dir, out_dir, command, reuse_fresh_receipt in
      the shape consumed by the body; write targets must be inside the caller-selected
      output or temporary area.
    - Mechanism: Writes only the output paths named by the caller, temporary workspace,
      or module constants. Normalizes Path values and public-root-relative references
      before returning them.
    - Guarantee: Returns dict[str, Any] representing the completed replay or bundle
      execution.
    - Fails: No explicit raise is introduced; failures propagate from filesystem writes,
      called validators/helpers.
    - Reads: call arguments; module constants BUNDLE_RESULT_NAME.
    - Writes: filesystem output explicitly written by this body.
    - Couples: BUNDLE_RESULT_NAME.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    source = Path(input_dir)
    if reuse_fresh_receipt:
        cached = _fresh_bundle_receipt(source, out)
        if cached is not None:
            return cached
    result = _build_result(
        source,
        command=command,
        input_mode="exported_belief_state_process_reward_bundle",
        include_negative=False,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=False)
    result["receipt_reused"] = False
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": (
            "exported_belief_state_process_reward_bundle_validation_result_v1"
        ),
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    """[ACTION] Build the compact result card from replay output.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `result_card`.
    - Preconditions: Callers provide result in the shape consumed by the body.
    - Mechanism: Delegates to result.get, result.get, result.get, result.get, result.get
      and applies local branch checks.
    - Guarantee: Returns dict[str, Any] from the explicit return paths in the function
      body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments; module constants CARD_OMITTED_FULL_PAYLOAD_KEYS,
      CARD_SCHEMA_VERSION.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: CARD_OMITTED_FULL_PAYLOAD_KEYS, CARD_SCHEMA_VERSION.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    freshness_basis = result.get("freshness_basis")
    freshness = freshness_basis if isinstance(freshness_basis, dict) else {}
    public_trace = result.get("public_agent_execution_trace")
    trace = public_trace if isinstance(public_trace, dict) else {}
    secret_scan = result.get("secret_exclusion_scan")
    scan = secret_scan if isinstance(secret_scan, dict) else {}
    source_imports = result.get("source_open_body_imports")
    source_body_floor = source_imports if isinstance(source_imports, dict) else {}
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": result.get("organ_id"),
        "input_mode": result.get("input_mode"),
        "bundle_id": result.get("bundle_id"),
        "command_speed": {
            "receipt_reused": result.get("receipt_reused") is True,
            "freshness_digest": freshness.get("basis_digest"),
            "freshness_input_count": freshness.get("input_count"),
            "freshness_missing_path_count": freshness.get("missing_path_count"),
        },
        "belief_reward": {
            "episode_count": result.get("episode_count"),
            "accepted_episode_count": result.get("accepted_episode_count"),
            "belief_state_count": result.get("belief_state_count"),
            "accepted_belief_state_count": result.get(
                "accepted_belief_state_count"
            ),
            "accepted_feedback_count": result.get("accepted_feedback_count"),
            "process_reward_count": result.get("process_reward_count"),
            "outcome_reward_count": result.get("outcome_reward_count"),
            "trajectory_group_count": result.get("trajectory_group_count"),
            "cold_replay_pass_count": result.get("cold_replay_pass_count"),
            "semantic_recompute_status": result.get("semantic_recompute_status"),
            "semantic_recompute_row_count": result.get("semantic_recompute_row_count"),
            "semantic_recompute_verified_count": result.get(
                "semantic_recompute_verified_count"
            ),
            "semantic_recompute_blocked_count": result.get(
                "semantic_recompute_blocked_count"
            ),
        },
        "validation": {
            "expected_negative_case_count": len(
                result.get("expected_negative_cases") or []
            ),
            "missing_negative_case_count": len(
                result.get("missing_negative_cases") or []
            ),
            "error_code_count": len(result.get("error_codes") or []),
            "finding_count": len(result.get("findings") or []),
            "secret_blocking_hit_count": scan.get("blocking_hit_count"),
            "public_trace_status": trace.get("status"),
            "public_trace_span_count": trace.get("span_count"),
            "body_import_status": result.get("body_import_status"),
            "source_module_manifest_status": result.get(
                "source_module_manifest_status"
            ),
            "source_module_manifest_ref": result.get("source_module_manifest_ref"),
            "body_material_status": source_body_floor.get("body_material_status"),
            "body_material_count": source_body_floor.get("body_material_count", 0),
            "body_material_classes": source_body_floor.get(
                "body_material_classes",
                {},
            ),
            "semantic_recompute_status": result.get("semantic_recompute_status"),
            "semantic_recompute_verified_count": result.get(
                "semantic_recompute_verified_count"
            ),
            "semantic_recompute_blocked_count": result.get(
                "semantic_recompute_blocked_count"
            ),
        },
        "body_floor": {
            "body_in_receipt": result.get("body_in_receipt") is True,
            "secret_exclusion_scan_in_card": False,
            "public_agent_execution_trace_in_card": False,
            "source_module_imports_in_card": False,
            "source_open_body_imports_in_card": False,
        },
        "authority_boundary": {
            "hidden_reasoning_export_authorized": False,
            "live_rl_training_authorized": False,
            "neural_judge_only_authorized": False,
            "hidden_gold_label_authorized": False,
            "benchmark_score_claim_authorized": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "release_authorized": False,
        },
        "receipt_paths": result.get("receipt_paths", []),
        "omission_receipt": {
            "omitted_full_payload_keys": list(CARD_OMITTED_FULL_PAYLOAD_KEYS),
            "full_payload_drilldown": "rerun without --card or inspect the written receipt file",
        },
    }


def _parser() -> argparse.ArgumentParser:
    """[ACTION] Build the command-line parser for this organ module.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `_parser`.
    - Preconditions: Callers provide no caller-supplied values in the shape consumed by
      the body.
    - Mechanism: Configures argparse commands and options that the module exposes.
    - Guarantee: Returns argparse.ArgumentParser from the explicit return paths in the
      function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    parser = argparse.ArgumentParser(prog="belief_state_process_reward_replay")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-reward-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """[ACTION] Parse command-line arguments and dispatch the selected organ command.

    - Teleology: Supports belief state process reward replay by documenting and
      preserving the exact local step implemented by `main`.
    - Preconditions: Callers provide argv in the shape consumed by the body; write
      targets must be inside the caller-selected output or temporary area.
    - Mechanism: Writes only the output paths named by the caller, temporary workspace,
      or module constants.
    - Guarantee: Returns int from the selected CLI command path.
    - Fails: Explicit raise paths include ValueError(args.action); called operations may
      propagate their own exceptions.
    - Reads: call arguments.
    - Writes: filesystem output explicitly written by this body.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    args = _parser().parse_args(argv)
    card_suffix = " --card" if args.card else ""
    if args.action == "run":
        acceptance_suffix = (
            f" --acceptance-out {args.acceptance_out}" if args.acceptance_out else ""
        )
        command = (
            "python -m microcosm_core.organs."
            "belief_state_process_reward_replay "
            f"run --input {args.input} --out {args.out}{acceptance_suffix}"
            f"{card_suffix}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    elif args.action == "run-reward-bundle":
        command = (
            "python -m microcosm_core.organs."
            "belief_state_process_reward_replay "
            f"run-reward-bundle --input {args.input} --out {args.out}"
            f"{card_suffix}"
        )
        result = run_reward_bundle(
            args.input,
            args.out,
            command=command,
            reuse_fresh_receipt=args.card,
        )
    else:  # pragma: no cover
        raise ValueError(args.action)
    if args.card:
        print(json.dumps(result_card(result), indent=2, sort_keys=True))
    else:
        print(result["status"])
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
