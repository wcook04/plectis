"""[PURPOSE]
- Teleology: Make concurrency mission control evidence inspectable through runnable
  public fixture code while keeping claims bounded to emitted receipts and authority
  ceilings.
- Mechanism: The file runs the mission-control builder over synthetic multi-agent
  contention topology and checks fail-closed accept, block, and repair counts; helper
  functions load fixtures, recompute predicates, normalize findings, build
  result/board/card payloads, and write receipts.
- Non-goal: Concurrency Mission Control imports the real public macro specimen builder
  and its provider/task-ledger bridge fixtures, then runs the copied builder against
  public synthetic lanes and a public Work Ledger seed-speed topology fixture to prove
  fail-closed transaction gating. It is not the private mission-control runtime, not a
  live scheduler, not provider dispatch, not public release approval, not private
  session export, and not production concurrency-safety evidence.

[INTERFACE]
- CLI: Import or dispatch `microcosm_core.organs.concurrency_mission_control` through
  package call sites and tests; no argparse subcommand was detected.
- Exports: classify_generated_surface_claim_lens,
  classify_concurrency_closure_state_lens, evaluate_negative_case, run,
  run_concurrency_mission_control_bundle, result_card, main.
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
- Required: microcosm_core.organs._crown_jewel_common
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
import copy
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    finding,
    public_root_for_path,
    run_crown_jewel_organ,
)


ORGAN_ID = "concurrency_mission_control"
FIXTURE_ID = "first_wave.concurrency_mission_control"
VALIDATOR_ID = "validator.microcosm.organs.concurrency_mission_control"

RESULT_NAME = "concurrency_mission_control_result.json"
BOARD_NAME = "concurrency_mission_control_board.json"
VALIDATION_RECEIPT_NAME = "concurrency_mission_control_validation_receipt.json"
BUNDLE_RESULT_NAME = "exported_concurrency_mission_control_validation_result.json"
CARD_SCHEMA_VERSION = "concurrency_mission_control_command_card_v1"
BUNDLE_INPUT_MODE = "exported_concurrency_mission_control_bundle"
EXERCISE_MANIFEST_NAME = "concurrency_mission_control_exercise_manifest.json"

EXPECTED_ENGINES: tuple[str, ...] = (
    "mission_transaction_original_builder",
    "failure_matrix_gate",
    "bridge_authority_membrane",
    "work_ledger_seed_speed_gate",
    "generated_surface_claim_lens",
    "closure_state_lens",
)

EXPECTED_NEGATIVE_CASES = {
    "missing_seed_root": ("CONCURRENCY_MISSION_CONTROL_SEED_ROOT_MISSING",),
    "provider_bridge_missing": ("CONCURRENCY_MISSION_CONTROL_PROVIDER_BRIDGE_BLOCKED",),
    "authority_collapse_claim": ("CONCURRENCY_MISSION_CONTROL_AUTHORITY_COLLAPSE",),
    "private_runtime_claim": ("CONCURRENCY_MISSION_CONTROL_PRIVATE_RUNTIME_OVERCLAIM",),
    "work_ledger_seed_speed_collision": (
        "CONCURRENCY_MISSION_CONTROL_WORK_LEDGER_COLLISION_UNRESOLVED",
    ),
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "concurrency_mission_control_public_fixture_not_live_scheduler",
    "real_substrate_disposition": "real_substrate_capsule",
    "release_authorized": False,
    "publication_authorized": False,
    "provider_dispatch": False,
    "model_dispatch": False,
    "browser_or_wallet_access": False,
    "source_mutation_authorized": False,
    "private_task_ledger_export": False,
    "private_work_ledger_export": False,
    "hosted_orchestration_claim": False,
    "production_concurrency_safety_claim": False,
}

ANTI_CLAIM = (
    "Concurrency Mission Control imports the real public macro specimen builder "
    "and its provider/task-ledger bridge fixtures, then runs the copied builder "
    "against public synthetic lanes and a public Work Ledger seed-speed "
    "topology fixture to prove fail-closed transaction gating. It is not the "
    "private mission-control runtime, not a live scheduler, not provider "
    "dispatch, not public release approval, not private session export, and "
    "not production concurrency-safety evidence."
)

SOURCE_REQUIRED_ANCHORS = {
    "self-indexing-cognitive-substrate/src/idea_microcosm/concurrency_mission_control_specimen.py": (
        "def build_concurrency_mission_control_specimen(",
        "supervised_scope_missing_contract",
        "missing_parent_finalizer",
        "misanchored_claim",
        "provider_to_concurrency_repair_loop",
    ),
    "self-indexing-cognitive-substrate/microcosms/provider_harness_canary/canary_board.json": (
        "provider_harness_evaluator_authority_canary_specimen",
        "provider_self_attestation_authority_count",
        "type_b_to_type_a_reduction_extension",
    ),
    "self-indexing-cognitive-substrate/microcosms/provider_harness_canary/receipt.json": (
        "receipt.provider_harness_canary",
        "provider_self_attestation_authority_count",
        "type_b_to_type_a_reduction_validator_summary",
    ),
    "self-indexing-cognitive-substrate/microcosms/task_ledger_cap_economy/events.jsonl": (
        "tle_007",
        "work_item",
        "cap_cap_economy_to_concurrency_bridge",
    ),
    "self-indexing-cognitive-substrate/microcosms/task_ledger_cap_economy/projection.json": (
        "task_ledger_cap_economy_projection",
        "provider_repair_residual_bridge_ref",
        "self_attestation_authority_count",
    ),
    "self-indexing-cognitive-substrate/microcosms/task_ledger_cap_economy/provider_repair_residual_bridge.json": (
        "task_ledger_provider_repair_residual_bridge",
        "repair_route_count",
        "next_owner",
    ),
    "self-indexing-cognitive-substrate/microcosms/task_ledger_cap_economy/receipt.json": (
        "receipt.task_ledger_cap_economy",
        "provider_repair_residual_case_count",
        "self_error_capture_repair_validator_summary",
    ),
}

GENERATED_ENTRY_SURFACES: tuple[str, ...] = (
    "microcosm-substrate/ORGANS.md",
    "microcosm-substrate/ARCHITECTURE.md",
    "microcosm-substrate/AGENT_ROUTES.md",
    "microcosm-substrate/atlas/agent_task_routes.json",
)

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Concurrency Mission Control",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=RESULT_NAME,
    board_name=BOARD_NAME,
    validation_receipt_name=VALIDATION_RECEIPT_NAME,
    bundle_result_name=BUNDLE_RESULT_NAME,
    card_schema_version=CARD_SCHEMA_VERSION,
    required_inputs=(EXERCISE_MANIFEST_NAME,),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        "microcosm-substrate/examples/concurrency_mission_control/"
        "exported_concurrency_mission_control_bundle/source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _bundle_root(public_root: Path) -> Path:
    """[ACTION] Implement bundle root for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_bundle_root`.
    - Preconditions: Callers provide public_root in the shape consumed by the body.
    - Mechanism: Uses local branch checks, literals, and comprehensions to compute the
      return value.
    - Guarantee: Returns Path from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    return public_root / "examples/concurrency_mission_control/exported_concurrency_mission_control_bundle"


def _copied_builder(public_root: Path) -> Path:
    """[ACTION] Implement copied builder for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_copied_builder`.
    - Preconditions: Callers provide public_root in the shape consumed by the body.
    - Mechanism: Delegates to _bundle_root and applies local branch checks.
    - Guarantee: Returns Path from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    return (
        _bundle_root(public_root)
        / "source_modules/self-indexing-cognitive-substrate/src/idea_microcosm/"
        "concurrency_mission_control_specimen.py"
    )


def _seed_root(input_path: Path, public_root: Path) -> Path:
    """[ACTION] Implement seed root for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_seed_root`.
    - Preconditions: Callers provide input_path, public_root in the shape consumed by
      the body; paths must be resolvable for filesystem metadata checks.
    - Mechanism: Delegates to local_seed.is_dir, _bundle_root and applies local branch
      checks.
    - Guarantee: Returns Path from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from filesystem
      metadata checks, called validators/helpers.
    - Reads: call arguments; filesystem metadata named by those arguments or constants.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    local_seed = input_path / "seed_root"
    if local_seed.is_dir():
        return local_seed
    return _bundle_root(public_root) / "seed_root"


def _load_builder(path: Path) -> Any:
    """[ACTION] Load builder for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_load_builder`.
    - Preconditions: Callers provide path in the shape consumed by the body.
    - Mechanism: Delegates to importlib.util.spec_from_file_location,
      importlib.util.module_from_spec, spec.loader.exec_module, ImportError and applies
      local branch checks.
    - Guarantee: Returns Any from the explicit return paths in the function body.
    - Fails: Explicit raise paths include ImportError(f"Cannot load copied concurrency
      builder from {path}"); called operations may propagate their own exceptions.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    spec = importlib.util.spec_from_file_location("microcosm_concurrency_builder_copy", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load copied concurrency builder from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["microcosm_concurrency_builder_copy"] = module
    spec.loader.exec_module(module)
    return module


def _load_json(path: Path) -> dict[str, Any]:
    """[ACTION] Read a JSON file and decode it into a Python value.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_load_json`.
    - Preconditions: Callers provide path in the shape consumed by the body; content
      inputs must exist and match the expected local fixture shape.
    - Mechanism: Reads declared local content and decodes or hashes it as the body
      shows.
    - Guarantee: Returns dict[str, Any] from the explicit return paths in the function
      body.
    - Fails: No explicit raise is introduced; failures propagate from filesystem/content
      reads.
    - Reads: call arguments; filesystem/content inputs named by those arguments or
      constants.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def _failure_classes(board: Mapping[str, Any]) -> set[str]:
    """[ACTION] Implement failure classes for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_failure_classes`.
    - Preconditions: Callers provide board in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns set[str] from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    classes: set[str] = set()
    cases = board.get("cases")
    if not isinstance(cases, list):
        return classes
    for case in cases:
        if not isinstance(case, Mapping):
            continue
        decision = case.get("evaluator_decision")
        if not isinstance(decision, Mapping):
            continue
        failures = decision.get("failures")
        if not isinstance(failures, list):
            continue
        for failure in failures:
            if isinstance(failure, Mapping) and isinstance(failure.get("failure_class"), str):
                classes.add(str(failure["failure_class"]))
    return classes


def _expected_counts(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    """[ACTION] Implement expected counts for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_expected_counts`.
    - Preconditions: Callers provide manifest in the shape consumed by the body.
    - Mechanism: Delegates to manifest.get and applies local branch checks.
    - Guarantee: Returns Mapping[str, Any] from the explicit return paths in the
      function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    counts = manifest.get("expected_counts")
    return counts if isinstance(counts, Mapping) else {}


def _required_bridge_statuses(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    """[ACTION] Implement required bridge statuses for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_required_bridge_statuses`.
    - Preconditions: Callers provide manifest in the shape consumed by the body.
    - Mechanism: Delegates to manifest.get and applies local branch checks.
    - Guarantee: Returns Mapping[str, Any] from the explicit return paths in the
      function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    statuses = manifest.get("required_bridge_statuses")
    return statuses if isinstance(statuses, Mapping) else {}


def _required_failure_classes(manifest: Mapping[str, Any]) -> set[str]:
    """[ACTION] Implement required failure classes for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_required_failure_classes`.
    - Preconditions: Callers provide manifest in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns set[str] from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    values = manifest.get("required_failure_classes")
    return {str(value) for value in values} if isinstance(values, list) else set()


def _forbidden_claims(manifest: Mapping[str, Any]) -> set[str]:
    """[ACTION] Implement forbidden claims for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_forbidden_claims`.
    - Preconditions: Callers provide manifest in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns set[str] from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    values = manifest.get("forbidden_claims")
    return {str(value) for value in values} if isinstance(values, list) else set()


def _as_mapping(value: Any) -> Mapping[str, Any]:
    """[ACTION] Implement as mapping for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_as_mapping`.
    - Preconditions: Callers provide value in the shape consumed by the body.
    - Mechanism: Uses local branch checks, literals, and comprehensions to compute the
      return value.
    - Guarantee: Returns Mapping[str, Any] from the explicit return paths in the
      function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    return value if isinstance(value, Mapping) else {}


def _as_records(value: Any) -> list[Mapping[str, Any]]:
    """[ACTION] Implement as records for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_as_records`.
    - Preconditions: Callers provide value in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns list[Mapping[str, Any]] from the explicit return paths in the
      function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    return (
        [row for row in value if isinstance(row, Mapping)]
        if isinstance(value, list)
        else []
    )


def _as_string_set(value: Any) -> set[str]:
    """[ACTION] Implement as string set for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_as_string_set`.
    - Preconditions: Callers provide value in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns set[str] from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    if not isinstance(value, list):
        return set()
    return {str(item).strip() for item in value if str(item).strip()}


def _claim_path(claim: Mapping[str, Any]) -> str:
    """[ACTION] Implement claim path for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_claim_path`.
    - Preconditions: Callers provide claim in the shape consumed by the body.
    - Mechanism: Delegates to claim.get, claim.get and applies local branch checks.
    - Guarantee: Returns str from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    return str(claim.get("path") or claim.get("scope_id") or "").strip()


def _session_freshness(
    session_id: str,
    *,
    session_cards_by_id: Mapping[str, Mapping[str, Any]],
    claim: Mapping[str, Any] | None,
) -> str:
    """[ACTION] Implement session freshness for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_session_freshness`.
    - Preconditions: Callers provide session_id, session_cards_by_id, claim in the shape
      consumed by the body.
    - Mechanism: Delegates to session_cards_by_id.get, claim.get, card.get, claim.get,
      claim.get and applies local branch checks.
    - Guarantee: Returns str from the explicit return paths in the function body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    card = session_cards_by_id.get(session_id) or {}
    claim_freshness = claim.get("freshness_state") if claim else ""
    freshness = str(card.get("freshness_state") or claim_freshness or "").strip()
    if freshness:
        return freshness
    claim_state = (
        str(claim.get("claim_state") or claim.get("freshness") or "").strip()
        if claim
        else ""
    )
    if claim_state:
        return claim_state
    return "unknown"


def classify_generated_surface_claim_lens(
    case: Mapping[str, Any],
    *,
    generated_surfaces: tuple[str, ...] = GENERATED_ENTRY_SURFACES,
) -> dict[str, Any]:
    """[ACTION] Implement classify generated surface claim lens for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `classify_generated_surface_claim_lens`.
    - Preconditions: Callers provide case, generated_surfaces in the shape consumed by
      the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns dict[str, Any] from the explicit return paths in the function
      body.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments; module constants GENERATED_ENTRY_SURFACES.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: GENERATED_ENTRY_SURFACES.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """

    generated_surface_set = set(generated_surfaces)
    drift_paths = _as_string_set(case.get("drift_paths"))
    generated_drift_paths = sorted(drift_paths.intersection(generated_surface_set))
    unrelated_drift_paths = sorted(drift_paths - generated_surface_set)
    session_cards = _as_records(case.get("session_cards"))
    session_cards_by_id = {
        str(row.get("session_id") or "").strip(): row
        for row in session_cards
        if str(row.get("session_id") or "").strip()
    }
    claim_rows = _as_records(case.get("claim_rows"))
    claims_by_path: dict[str, list[Mapping[str, Any]]] = {}
    for claim in claim_rows:
        path = _claim_path(claim)
        if path:
            claims_by_path.setdefault(path, []).append(claim)

    owner_rows: list[dict[str, Any]] = []
    live_owner = False
    stale_owner = False
    owner_session_id = None
    owner_claim_id = None
    owner_freshness = "unknown"
    unowned_generated_paths: list[str] = []
    for path in generated_drift_paths:
        owners = claims_by_path.get(path, [])
        if not owners:
            unowned_generated_paths.append(path)
            continue
        claim = owners[0]
        session_id = str(claim.get("session_id") or "").strip()
        freshness = _session_freshness(
            session_id,
            session_cards_by_id=session_cards_by_id,
            claim=claim,
        )
        if session_id and owner_session_id is None:
            owner_session_id = session_id
            owner_claim_id = str(claim.get("claim_id") or "").strip() or None
            owner_freshness = freshness
        is_live = freshness == "live" or str(claim.get("claim_state") or "") == "live"
        live_owner = live_owner or is_live
        stale_owner = stale_owner or not is_live
        owner_rows.append(
            {
                "path": path,
                "owner_session_id": session_id or None,
                "claim_id": str(claim.get("claim_id") or "").strip() or None,
                "claim_scope": str(claim.get("scope_kind") or "path"),
                "freshness_state": freshness,
                "allowed_action": (
                    "do_not_patch_from_sibling_lane"
                    if is_live
                    else "release_or_supersede_owner_claim_then_regenerate"
                ),
            }
        )

    if generated_drift_paths and live_owner:
        classification = "owned_live"
        drift_authority = "owner_lane"
        allowed_action = "do_not_patch_from_sibling_lane"
        reentry_condition = "owner session lands, releases, or explicit handoff is recorded"
    elif generated_drift_paths and stale_owner:
        classification = "owned_stale"
        drift_authority = "stale_projection"
        allowed_action = "release_or_supersede_owner_claim_then_regenerate"
        reentry_condition = "claim is released or superseded through Work Ledger owner tooling"
    elif generated_drift_paths and unowned_generated_paths:
        classification = "unowned_generated_drift"
        drift_authority = "unowned_defect"
        allowed_action = "claim_builder_lane_then_regenerate_and_validate"
        reentry_condition = "a generator owner claim is acquired and the generated-surface check passes"
    elif generated_drift_paths:
        classification = "unowned_generated_drift"
        drift_authority = "unowned_defect"
        allowed_action = "claim_builder_lane_then_regenerate_and_validate"
        reentry_condition = "a generator owner claim is acquired and the generated-surface check passes"
    elif drift_paths:
        classification = "unrelated_dirty_state"
        drift_authority = "unrelated_dirty_state"
        allowed_action = "route_to_owning_lane_or_capture"
        reentry_condition = "owning lane consumes or captures the unrelated dirty state"
    else:
        classification = "clean"
        drift_authority = "no_drift"
        allowed_action = "continue"
        reentry_condition = "new generated-surface drift appears"

    return {
        "schema_version": "generated_surface_claim_lens_v1",
        "case_id": str(case.get("case_id") or "generated_surface_claim_lens_case"),
        "classification": classification,
        "drift_authority": drift_authority,
        "allowed_action": allowed_action,
        "generated_surface_drift_paths": generated_drift_paths,
        "unowned_generated_surface_drift_paths": unowned_generated_paths,
        "unrelated_drift_paths": unrelated_drift_paths,
        "owner_session_id": owner_session_id,
        "owner_claim_id": owner_claim_id,
        "owner_freshness_state": owner_freshness,
        "surface_owner_rows": owner_rows,
        "reentry_condition": reentry_condition,
        "closeout_receipt_ref": str(case.get("closeout_receipt_ref") or "").strip() or None,
        "body_in_receipt": False,
    }


def _first_owner_row(case: Mapping[str, Any]) -> Mapping[str, Any]:
    """[ACTION] Implement first owner row for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_first_owner_row`.
    - Preconditions: Callers provide case in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns Mapping[str, Any] from the explicit return paths in the
      function body.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    claim_rows = _as_records(case.get("claim_rows"))
    session_cards = _as_records(case.get("session_cards"))
    session_cards_by_id = {
        str(row.get("session_id") or "").strip(): row
        for row in session_cards
        if str(row.get("session_id") or "").strip()
    }
    for claim in claim_rows:
        session_id = str(claim.get("session_id") or "").strip()
        if not session_id:
            continue
        return {
            "owner_session_id": session_id,
            "owner_claim_id": str(claim.get("claim_id") or "").strip() or None,
            "owner_freshness_state": _session_freshness(
                session_id,
                session_cards_by_id=session_cards_by_id,
                claim=claim,
            ),
        }
    return {}


def classify_concurrency_closure_state_lens(case: Mapping[str, Any]) -> dict[str, Any]:
    """[ACTION] Implement classify concurrency closure state lens for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `classify_concurrency_closure_state_lens`.
    - Preconditions: Callers provide case in the shape consumed by the body.
    - Mechanism: Delegates to classify_generated_surface_claim_lens, _first_owner_row,
      _as_mapping, case.get, owner.get and applies local branch checks.
    - Guarantee: Returns dict[str, Any] from the explicit return paths in the function
      body.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """

    generated = classify_generated_surface_claim_lens(case)
    generated_classification = str(generated.get("classification") or "")
    owner = _first_owner_row(case)
    validation_quote = _as_mapping(case.get("validation_quote"))
    validation_state = str(
        case.get("heavy_validation_state")
        or validation_quote.get("status")
        or case.get("validation_state")
        or "unknown"
    )
    commitability_state = str(
        case.get("commitability_decision")
        or case.get("scoped_commit_status")
        or "unknown"
    )
    residual_state = str(case.get("residual_state") or "").strip()
    generator_check_status = str(case.get("generator_check_status") or "").strip()
    secondary_states: list[str] = []

    if (
        str(case.get("path_scope_status") or "") == "overbroad"
        and owner.get("owner_session_id")
    ):
        classification = "owned_live_handoff"
        allowed_action = "narrow_path_scope_or_coordinate_owner"
        drift_authority = "owner_lane"
        reentry_condition = "candidate path scope is narrowed or owner handoff is recorded"
    elif generated_classification == "owned_live":
        classification = "owned_live_handoff"
        allowed_action = "handoff_to_live_owner_or_wait_for_release"
        drift_authority = "owner_lane"
        reentry_condition = str(generated.get("reentry_condition") or "")
    elif generated_classification == "owned_stale":
        classification = "owned_stale_reentry"
        allowed_action = "release_or_supersede_owner_claim_then_reenter"
        drift_authority = "stale_projection"
        reentry_condition = str(generated.get("reentry_condition") or "")
    elif generated_classification == "unowned_generated_drift":
        classification = "unowned_generated_drift"
        allowed_action = "claim_builder_lane_then_regenerate_and_validate"
        drift_authority = "unowned_defect"
        reentry_condition = str(generated.get("reentry_condition") or "")
    elif (
        generator_check_status == "pass"
        and residual_state in {"open", "captured", "stale"}
    ):
        classification = "false_residual_stale"
        allowed_action = "close_or_retype_residual"
        drift_authority = "current_generator_evidence"
        reentry_condition = "residual is closed or retyped against the current no-drift receipt"
    elif validation_state in {
        "deferred_by_host_pressure",
        "blocked_by_host_pressure",
        "queued_by_host_pressure",
        "blocked",
    } and str(validation_quote.get("reason") or case.get("validation_block_reason") or "").strip():
        classification = "closed_validation_deferred"
        allowed_action = "record_validation_debt_or_queue_when_pressure_clears"
        drift_authority = "validation_quote"
        reentry_condition = "host pressure clears or the queued validation receipt lands"
    elif commitability_state == "unsafe_to_stage_shared_append_logs_due_interleaved_writes":
        classification = "closed_uncommitted_authority"
        allowed_action = (
            "do_not_stage_shared_append_logs; rely_on_event_authority_and_reenter_scoped_commit"
        )
        drift_authority = "event_sourced_authority"
        reentry_condition = "a scoped owned-path commit becomes attributable without interleaved append logs"
    elif (
        case.get("product_closed") is True
        and validation_state == "complete"
        and commitability_state == "committed"
    ):
        classification = "closed_and_committed"
        allowed_action = "no_action_required"
        drift_authority = "closed_receipt"
        reentry_condition = "new drift, validation failure, or reopened residual appears"
    else:
        classification = "open_unclassified"
        allowed_action = "inspect_owner_receipts_before_mutation"
        drift_authority = "insufficient_closure_evidence"
        reentry_condition = "closure receipt, validation quote, or owner claim evidence is present"

    if commitability_state == "unsafe_to_stage_shared_append_logs_due_interleaved_writes":
        secondary_states.append("closed_uncommitted_authority")
    if validation_state in {
        "deferred_by_host_pressure",
        "blocked_by_host_pressure",
        "queued_by_host_pressure",
    }:
        secondary_states.append("closed_validation_deferred")

    return {
        "schema_version": "concurrency_closure_state_lens_v1",
        "case_id": str(case.get("case_id") or "closure_state_lens_case"),
        "classification": classification,
        "allowed_action": allowed_action,
        "drift_authority": drift_authority,
        "validation_state": validation_state,
        "commitability_state": commitability_state,
        "residual_state": residual_state or None,
        "residual_ref": str(case.get("residual_ref") or "").strip() or None,
        "generator_check_status": generator_check_status or None,
        "owner_session_id": owner.get("owner_session_id") or generated.get("owner_session_id"),
        "owner_claim_id": owner.get("owner_claim_id") or generated.get("owner_claim_id"),
        "owner_freshness_state": (
            owner.get("owner_freshness_state") or generated.get("owner_freshness_state")
        ),
        "secondary_states": sorted(set(secondary_states) - {classification}),
        "reentry_condition": reentry_condition,
        "body_in_receipt": False,
    }


def _run_original_builder(input_path: Path, public_root: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    """[ACTION] Implement run original builder for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_run_original_builder`.
    - Preconditions: Callers provide input_path, public_root, manifest in the shape
      consumed by the body; paths must be resolvable for filesystem metadata checks.
    - Mechanism: Normalizes Path values and public-root-relative references before
      returning them.
    - Guarantee: Returns dict[str, Any] representing the completed replay or bundle
      execution.
    - Fails: No explicit raise is introduced; failures propagate from filesystem
      metadata checks, called validators/helpers.
    - Reads: call arguments; filesystem metadata named by those arguments or constants.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    seed_root = _seed_root(input_path, public_root)
    if not seed_root.is_dir():
        return {
            "status": "blocked",
            "engine_id": "mission_transaction_original_builder",
            "error_code": "CONCURRENCY_MISSION_CONTROL_SEED_ROOT_MISSING",
            "seed_root_present": False,
            "body_in_receipt": False,
        }

    module = _load_builder(_copied_builder(public_root))
    generated_at = str(manifest.get("builder_timestamp") or "2026-05-13T00:50:00Z")
    with tempfile.TemporaryDirectory(prefix="concurrency_mission_control_") as temp_dir:
        temp_root = Path(temp_dir) / "workspace"
        shutil.copytree(seed_root, temp_root)
        result = module.build_concurrency_mission_control_specimen(
            temp_root,
            write_receipt=True,
            at=generated_at,
        )
        board = _load_json(temp_root / "microcosms/concurrency_mission_control/mission_board.json")
        receipt = _load_json(temp_root / "microcosms/concurrency_mission_control/receipt.json")

    summary = board.get("summary") if isinstance(board.get("summary"), Mapping) else {}
    return {
        "status": "pass" if result.get("status") == "ok" and board.get("status") == "ok" else "blocked",
        "engine_id": "mission_transaction_original_builder",
        "source_relation": "exact_copied_macro_body_invoked",
        "result_status": result.get("status"),
        "board_status": board.get("status"),
        "receipt_status": receipt.get("status"),
        "case_count": result.get("case_count"),
        "accept_count": result.get("accept_count"),
        "block_count": result.get("block_count"),
        "repair_row_count": result.get("repair_row_count"),
        "source_capsule_count": result.get("source_capsule_count"),
        "work_metabolism_bridge_status": result.get("work_metabolism_bridge_status"),
        "provider_repair_bridge_status": result.get("provider_repair_bridge_status"),
        "task_ledger_residual_replay_bridge_status": result.get("task_ledger_residual_replay_bridge_status"),
        "work_metabolism_transaction_step_count": result.get("work_metabolism_transaction_step_count"),
        "provider_repair_bridge_case_count": result.get("provider_repair_bridge_case_count"),
        "task_ledger_residual_replay_case_count": result.get("task_ledger_residual_replay_case_count"),
        "authority_collapse_count": result.get("authority_collapse_count"),
        "provider_repair_bridge_authority_collapse_count": result.get(
            "provider_repair_bridge_authority_collapse_count"
        ),
        "task_ledger_residual_replay_authority_collapse_count": result.get(
            "task_ledger_residual_replay_authority_collapse_count"
        ),
        "lane_self_status_authority_count": summary.get("lane_self_status_authority_count"),
        "failure_classes": sorted(_failure_classes(board)),
        "body_in_receipt": False,
    }


def _failure_matrix_gate(original: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    """[ACTION] Implement failure matrix gate for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_failure_matrix_gate`.
    - Preconditions: Callers provide original, manifest in the shape consumed by the
      body.
    - Mechanism: Delegates to _expected_counts, _required_failure_classes, int, int, int
      and applies local branch checks.
    - Guarantee: Returns dict[str, Any] from the explicit return paths in the function
      body.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments.
    - Writes: No external writes; the body only returns in-memory values.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    expected = _expected_counts(manifest)
    required_classes = _required_failure_classes(manifest)
    observed_classes = set(original.get("failure_classes") or [])
    missing_classes = sorted(required_classes - observed_classes)
    case_count = int(original.get("case_count") or 0)
    block_count = int(original.get("block_count") or 0)
    repair_row_count = int(original.get("repair_row_count") or 0)
    source_capsule_count = int(original.get("source_capsule_count") or 0)
    status = (
        "pass"
        if original.get("status") == "pass"
        and case_count == int(expected.get("case_count") or 0)
        and int(original.get("accept_count") or 0) == int(expected.get("accept_count") or 0)
        and block_count >= int(expected.get("minimum_block_count") or 0)
        and repair_row_count >= int(expected.get("minimum_repair_row_count") or 0)
        and source_capsule_count >= int(expected.get("minimum_source_capsule_count") or 0)
        and not missing_classes
        else "blocked"
    )
    return {
        "status": status,
        "engine_id": "failure_matrix_gate",
        "case_count": case_count,
        "block_count": block_count,
        "repair_row_count": repair_row_count,
        "source_capsule_count": source_capsule_count,
        "required_failure_classes": sorted(required_classes),
        "observed_failure_classes": sorted(observed_classes),
        "missing_failure_classes": missing_classes,
        "body_in_receipt": False,
    }


def _bridge_authority_membrane(original: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    """[ACTION] Implement bridge authority membrane for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_bridge_authority_membrane`.
    - Preconditions: Callers provide original, manifest in the shape consumed by the
      body.
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
    expected = _expected_counts(manifest)
    required_statuses = _required_bridge_statuses(manifest)
    forbidden = _forbidden_claims(manifest)
    required_forbidden = {
        "private_mission_control_runtime",
        "private_task_ledger_body_export",
        "private_work_ledger_session_export",
        "provider_payload_body_export",
        "hosted_orchestration_proof",
        "public_release_readiness",
        "production_concurrency_safety",
    }
    bridge_statuses_pass = all(original.get(key) == value for key, value in required_statuses.items())
    authority_collapse_count = sum(
        int(original.get(key) or 0)
        for key in (
            "authority_collapse_count",
            "provider_repair_bridge_authority_collapse_count",
            "task_ledger_residual_replay_authority_collapse_count",
            "lane_self_status_authority_count",
        )
    )
    count_shape_pass = (
        int(original.get("provider_repair_bridge_case_count") or 0)
        == int(expected.get("provider_repair_bridge_case_count") or 0)
        and int(original.get("task_ledger_residual_replay_case_count") or 0)
        == int(expected.get("task_ledger_residual_replay_case_count") or 0)
        and int(original.get("work_metabolism_transaction_step_count") or 0)
        == int(expected.get("work_metabolism_transaction_step_count") or 0)
    )
    return {
        "status": "pass"
        if original.get("status") == "pass"
        and bridge_statuses_pass
        and count_shape_pass
        and authority_collapse_count == 0
        and required_forbidden.issubset(forbidden)
        else "blocked",
        "engine_id": "bridge_authority_membrane",
        "bridge_statuses": {key: original.get(key) for key in required_statuses},
        "bridge_statuses_pass": bridge_statuses_pass,
        "count_shape_pass": count_shape_pass,
        "authority_collapse_count": authority_collapse_count,
        "forbidden_claims_present": sorted(required_forbidden.intersection(forbidden)),
        "body_in_receipt": False,
    }


def _work_ledger_seed_speed_gate(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """[ACTION] Implement work ledger seed speed gate for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_work_ledger_seed_speed_gate`.
    - Preconditions: Callers provide manifest in the shape consumed by the body.
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
    surface = _as_mapping(manifest.get("work_ledger_seed_speed_surface"))
    counts = _as_mapping(surface.get("counts"))
    minimum_counts = _as_mapping(surface.get("minimum_counts"))
    command_refs = _as_mapping(surface.get("command_refs"))
    heartbeat = _as_mapping(surface.get("heartbeat_participation"))
    public_boundary = _as_mapping(surface.get("public_boundary"))
    session_cards = _as_records(surface.get("session_cards"))
    claim_rows = _as_records(surface.get("claim_rows"))
    collision_rows = _as_records(surface.get("claim_collisions"))
    source_refs = {
        str(ref) for ref in surface.get("source_refs", []) if isinstance(ref, str)
    }
    findings: list[dict[str, Any]] = []

    def add_finding(
        code: str,
        message: str,
        *,
        expected: Any = None,
        observed: Any = None,
    ) -> None:
        """[ACTION] Implement add finding for this organ replay.

        - Teleology: Supports concurrency mission control by documenting and preserving
          the exact local step implemented by `add_finding`.
        - Preconditions: Callers provide code, message, expected, observed in the shape
          consumed by the body.
        - Mechanism: Delegates to findings.append, finding and applies local branch
          checks.
        - Guarantee: Returns None from the explicit return paths in the function body.
        - Fails: No explicit raise is introduced; failures propagate from ordinary
          Python evaluation in this body.
        - Reads: call arguments.
        - Writes: No external writes; the body only returns in-memory values.
        - Non-goal: Does not widen this module's public authority ceiling, add provider
          calls, or expose private material.
        """
        findings.append(
            finding(
                code,
                message,
                subject_id="work_ledger_seed_speed_surface",
                expected=expected,
                observed=observed,
            )
        )

    required_source_refs = {
        "tools/meta/factory/work_ledger.py",
        "system/lib/work_ledger_runtime.py",
        (
            "microcosm-substrate/examples/mission_transaction_work_spine/"
            "exported_mission_transaction_bundle/work_ledger_source_module_manifest.json"
        ),
        (
            "microcosm-substrate/examples/mission_transaction_work_spine/"
            "exported_mission_transaction_bundle/work_ledger_control_runtime_contract.json"
        ),
    }
    required_count_fields = (
        "effective_active_sessions",
        "active_claims",
        "claim_collisions",
        "claim_session_heartbeat_gap_count",
    )
    count_shape_pass = all(
        isinstance(counts.get(field), int) and int(counts[field]) >= 0
        for field in required_count_fields
    )
    minimum_sessions = int(minimum_counts.get("effective_active_sessions") or 0)
    minimum_claims = int(minimum_counts.get("active_claims") or 0)
    expected_claim_collisions = int(surface.get("expected_claim_collision_count") or 0)
    active_shape_pass = (
        count_shape_pass
        and int(counts.get("effective_active_sessions") or 0) >= minimum_sessions
        and int(counts.get("active_claims") or 0) >= minimum_claims
    )
    session_collision_count = sum(int(row.get("collision_count") or 0) for row in claim_rows)
    collision_gate_pass = (
        count_shape_pass
        and int(counts.get("claim_collisions") or 0) == expected_claim_collisions
        and session_collision_count == 0
        and not collision_rows
    )
    command_refs_pass = (
        "session-heartbeat" in str(command_refs.get("session_heartbeat") or "")
        and "--current-pass-line" in str(command_refs.get("session_heartbeat") or "")
        and "session-status --seed-speed" in str(command_refs.get("seed_speed_status") or "")
        and "mutation-check" in str(command_refs.get("mutation_check") or "")
    )
    session_cards_pass = bool(session_cards) and all(
        row.get("session_id")
        and row.get("current_pass_line")
        and row.get("pass_state") in {"inspecting", "editing", "validating", "closing"}
        and isinstance(row.get("scope_refs"), list)
        and row.get("body_in_receipt") is False
        for row in session_cards
    )
    source_refs_bound = required_source_refs.issubset(source_refs)
    forbidden_public_inputs = {
        str(item)
        for item in public_boundary.get("forbidden_public_inputs", [])
        if isinstance(item, str)
    }
    required_forbidden_inputs = {
        "account/session state",
        "private Work Ledger session bodies",
        "provider payload bodies",
        "raw operator transcripts",
    }
    public_boundary_pass = (
        required_forbidden_inputs.issubset(forbidden_public_inputs)
        and surface.get("private_session_body_exported") is False
        and surface.get("body_in_receipt") is False
    )
    heartbeat_participation_status = str(heartbeat.get("status") or "")
    heartbeat_pass = (
        heartbeat_participation_status == "complete"
        and int(heartbeat.get("explicit_current_pass_count") or 0) >= minimum_sessions
        and heartbeat.get("projected_unknown_count") == 0
    )

    checks = {
        "schema": surface.get("schema_version") == "work_ledger_seed_speed_public_surface_v1",
        "count_shape": count_shape_pass,
        "active_shape": active_shape_pass,
        "collision_gate": collision_gate_pass,
        "command_refs": command_refs_pass,
        "session_cards": session_cards_pass,
        "source_refs_bound": source_refs_bound,
        "public_boundary": public_boundary_pass,
        "heartbeat_participation": heartbeat_pass,
    }
    if not checks["schema"]:
        add_finding(
            "CONCURRENCY_MISSION_CONTROL_WORK_LEDGER_SCHEMA_INVALID",
            "Work Ledger seed-speed surface must use the public surface schema.",
            expected="work_ledger_seed_speed_public_surface_v1",
            observed=surface.get("schema_version"),
        )
    if not checks["count_shape"]:
        add_finding(
            "CONCURRENCY_MISSION_CONTROL_WORK_LEDGER_COUNTS_INVALID",
            "Work Ledger seed-speed counts must include non-negative active session, "
            "claim, collision, and heartbeat-gap fields.",
            expected=list(required_count_fields),
            observed=counts,
        )
    if not checks["active_shape"]:
        add_finding(
            "CONCURRENCY_MISSION_CONTROL_WORK_LEDGER_ACTIVE_SHAPE_INVALID",
            "Work Ledger seed-speed fixture must model real multi-session and "
            "claim pressure without pinning exact live counts.",
            expected=minimum_counts,
            observed=counts,
        )
    if not checks["collision_gate"]:
        add_finding(
            "CONCURRENCY_MISSION_CONTROL_WORK_LEDGER_COLLISION_UNRESOLVED",
            "Work Ledger seed-speed fixture must keep the selected session's path claims collision-free.",
            expected={
                "claim_collisions": expected_claim_collisions,
                "session_collision_count": 0,
            },
            observed={
                "claim_collisions": counts.get("claim_collisions"),
                "session_collision_count": session_collision_count,
                "collision_rows": len(collision_rows),
            },
        )
    if not checks["command_refs"]:
        add_finding(
            "CONCURRENCY_MISSION_CONTROL_WORK_LEDGER_COMMAND_REFS_MISSING",
            "Work Ledger seed-speed fixture must expose heartbeat, seed-speed "
            "status, and mutation-check commands.",
            observed=command_refs,
        )
    if not checks["session_cards"]:
        add_finding(
            "CONCURRENCY_MISSION_CONTROL_WORK_LEDGER_SESSION_CARDS_INVALID",
            "Work Ledger seed-speed fixture must carry public session cards with "
            "current pass lines, scope refs, and no body export.",
            observed=session_cards,
        )
    if not checks["source_refs_bound"]:
        add_finding(
            "CONCURRENCY_MISSION_CONTROL_WORK_LEDGER_SOURCE_REFS_UNBOUND",
            "Work Ledger seed-speed fixture must bind to the existing Work Ledger "
            "source-body import surfaces.",
            expected=sorted(required_source_refs),
            observed=sorted(source_refs),
        )
    if not checks["public_boundary"]:
        add_finding(
            "CONCURRENCY_MISSION_CONTROL_WORK_LEDGER_PUBLIC_BOUNDARY_INVALID",
            "Work Ledger seed-speed fixture must forbid private session, provider, "
            "transcript, and account state bodies.",
            expected=sorted(required_forbidden_inputs),
            observed=sorted(forbidden_public_inputs),
        )
    if not checks["heartbeat_participation"]:
        add_finding(
            "CONCURRENCY_MISSION_CONTROL_WORK_LEDGER_HEARTBEAT_PARTICIPATION_INVALID",
            "Work Ledger seed-speed fixture must show explicit heartbeat "
            "participation rather than projected-unknown sessions.",
            observed=heartbeat,
        )

    return {
        "status": "pass" if not findings else "blocked",
        "engine_id": "work_ledger_seed_speed_gate",
        "snapshot_schema_version": surface.get("snapshot_schema_version"),
        "counts": {
            field: counts.get(field)
            for field in required_count_fields
        },
        "minimum_counts": dict(minimum_counts),
        "session_card_count": len(session_cards),
        "claim_row_count": len(claim_rows),
        "session_collision_count": session_collision_count,
        "claim_collision_count": counts.get("claim_collisions"),
        "heartbeat_participation_status": heartbeat_participation_status,
        "checks": checks,
        "source_refs_bound": source_refs_bound,
        "private_session_body_exported": surface.get("private_session_body_exported"),
        "body_in_receipt": False,
        "findings": findings,
    }


def _generated_surface_claim_lens_gate(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """[ACTION] Implement generated surface claim lens gate for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_generated_surface_claim_lens_gate`.
    - Preconditions: Callers provide manifest in the shape consumed by the body.
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
    surface = _as_mapping(manifest.get("generated_surface_claim_lens"))
    cases = _as_records(surface.get("cases"))
    findings: list[dict[str, Any]] = []
    rows = [classify_generated_surface_claim_lens(case) for case in cases]
    observed_classes = {str(row.get("classification")) for row in rows}
    expected_classes = _as_string_set(surface.get("required_classifications"))
    missing_classes = sorted(expected_classes - observed_classes)
    private_exported = surface.get("private_session_body_exported")
    body_in_receipt = surface.get("body_in_receipt")

    for row, case in zip(rows, cases):
        expected_classification = str(case.get("expected_classification") or "").strip()
        expected_action = str(case.get("expected_allowed_action") or "").strip()
        if expected_classification and row.get("classification") != expected_classification:
            findings.append(
                finding(
                    "CONCURRENCY_MISSION_CONTROL_GENERATED_SURFACE_CLASSIFICATION_MISMATCH",
                    "Generated-surface claim lens classified a fixture case differently than expected.",
                    subject_id=str(row.get("case_id")),
                    expected=expected_classification,
                    observed=row.get("classification"),
                )
            )
        if expected_action and row.get("allowed_action") != expected_action:
            findings.append(
                finding(
                    "CONCURRENCY_MISSION_CONTROL_GENERATED_SURFACE_ACTION_MISMATCH",
                    "Generated-surface claim lens emitted the wrong allowed action.",
                    subject_id=str(row.get("case_id")),
                    expected=expected_action,
                    observed=row.get("allowed_action"),
                )
            )

    if not cases:
        findings.append(
            finding(
                "CONCURRENCY_MISSION_CONTROL_GENERATED_SURFACE_CASES_MISSING",
                "Generated-surface claim lens requires public fixture cases.",
                subject_id="generated_surface_claim_lens",
            )
        )
    if missing_classes:
        findings.append(
            finding(
                "CONCURRENCY_MISSION_CONTROL_GENERATED_SURFACE_CLASS_COVERAGE_MISSING",
                "Generated-surface claim lens fixture set must cover every required drift ownership class.",
                subject_id="generated_surface_claim_lens",
                expected=sorted(expected_classes),
                observed=sorted(observed_classes),
            )
        )
    if private_exported is not False or body_in_receipt is not False:
        findings.append(
            finding(
                "CONCURRENCY_MISSION_CONTROL_GENERATED_SURFACE_PRIVATE_EXPORT",
                "Generated-surface claim lens must not export private Work Ledger bodies.",
                subject_id="generated_surface_claim_lens",
                expected={"private_session_body_exported": False, "body_in_receipt": False},
                observed={
                    "private_session_body_exported": private_exported,
                    "body_in_receipt": body_in_receipt,
                },
            )
        )

    return {
        "status": "pass" if not findings else "blocked",
        "engine_id": "generated_surface_claim_lens",
        "case_count": len(rows),
        "required_classifications": sorted(expected_classes),
        "observed_classifications": sorted(observed_classes),
        "missing_classifications": missing_classes,
        "rows": rows,
        "private_session_body_exported": private_exported,
        "body_in_receipt": False,
        "findings": findings,
    }


def _closure_state_lens_gate(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """[ACTION] Implement closure state lens gate for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_closure_state_lens_gate`.
    - Preconditions: Callers provide manifest in the shape consumed by the body.
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
    surface = _as_mapping(manifest.get("closure_state_lens"))
    cases = _as_records(surface.get("cases"))
    findings: list[dict[str, Any]] = []
    rows = [classify_concurrency_closure_state_lens(case) for case in cases]
    observed_classes = {str(row.get("classification")) for row in rows}
    expected_classes = _as_string_set(surface.get("required_classifications"))
    missing_classes = sorted(expected_classes - observed_classes)
    private_exported = surface.get("private_session_body_exported")
    body_in_receipt = surface.get("body_in_receipt")

    for row, case in zip(rows, cases):
        expected_classification = str(case.get("expected_classification") or "").strip()
        expected_action = str(case.get("expected_allowed_action") or "").strip()
        if expected_classification and row.get("classification") != expected_classification:
            findings.append(
                finding(
                    "CONCURRENCY_MISSION_CONTROL_CLOSURE_STATE_CLASSIFICATION_MISMATCH",
                    "Closure-state lens classified a fixture case differently than expected.",
                    subject_id=str(row.get("case_id")),
                    expected=expected_classification,
                    observed=row.get("classification"),
                )
            )
        if expected_action and row.get("allowed_action") != expected_action:
            findings.append(
                finding(
                    "CONCURRENCY_MISSION_CONTROL_CLOSURE_STATE_ACTION_MISMATCH",
                    "Closure-state lens emitted the wrong allowed action.",
                    subject_id=str(row.get("case_id")),
                    expected=expected_action,
                    observed=row.get("allowed_action"),
                )
            )

    if not cases:
        findings.append(
            finding(
                "CONCURRENCY_MISSION_CONTROL_CLOSURE_STATE_CASES_MISSING",
                "Closure-state lens requires public fixture cases.",
                subject_id="closure_state_lens",
            )
        )
    if missing_classes:
        findings.append(
            finding(
                "CONCURRENCY_MISSION_CONTROL_CLOSURE_STATE_CLASS_COVERAGE_MISSING",
                "Closure-state lens fixture set must cover every required closure class.",
                subject_id="closure_state_lens",
                expected=sorted(expected_classes),
                observed=sorted(observed_classes),
            )
        )
    if private_exported is not False or body_in_receipt is not False:
        findings.append(
            finding(
                "CONCURRENCY_MISSION_CONTROL_CLOSURE_STATE_PRIVATE_EXPORT",
                "Closure-state lens must not export private Work Ledger or Task Ledger bodies.",
                subject_id="closure_state_lens",
                expected={"private_session_body_exported": False, "body_in_receipt": False},
                observed={
                    "private_session_body_exported": private_exported,
                    "body_in_receipt": body_in_receipt,
                },
            )
        )

    return {
        "status": "pass" if not findings else "blocked",
        "engine_id": "closure_state_lens",
        "case_count": len(rows),
        "required_classifications": sorted(expected_classes),
        "observed_classifications": sorted(observed_classes),
        "missing_classifications": missing_classes,
        "rows": rows,
        "private_session_body_exported": private_exported,
        "body_in_receipt": False,
        "findings": findings,
    }


def _evaluate(
    input_path: Path,
    public_root: Path,
    source_manifest: dict[str, Any],
) -> dict[str, Any]:
    """[ACTION] Evaluate fixture evidence and return a structured verdict.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `_evaluate`.
    - Preconditions: Callers provide input_path, public_root, source_manifest in the
      shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns dict[str, Any] from the explicit return paths in the function
      body.
    - Fails: No explicit raise is introduced; failures propagate from called
      validators/helpers.
    - Reads: call arguments; module constants EXERCISE_MANIFEST_NAME, EXPECTED_ENGINES,
      EXPECTED_NEGATIVE_CASES.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: EXERCISE_MANIFEST_NAME, EXPECTED_ENGINES, EXPECTED_NEGATIVE_CASES.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    findings: list[dict[str, Any]] = []
    manifest = _load_json(input_path / EXERCISE_MANIFEST_NAME)
    original = _run_original_builder(input_path, public_root, manifest)
    failure_matrix = _failure_matrix_gate(original, manifest)
    bridge_membrane = _bridge_authority_membrane(original, manifest)
    work_ledger_seed_speed = _work_ledger_seed_speed_gate(manifest)
    generated_surface_claim_lens = _generated_surface_claim_lens_gate(manifest)
    closure_state_lens = _closure_state_lens_gate(manifest)
    engines = [
        original,
        failure_matrix,
        bridge_membrane,
        work_ledger_seed_speed,
        generated_surface_claim_lens,
        closure_state_lens,
    ]
    for engine in engines:
        if engine.get("status") != "pass":
            findings.append(
                finding(
                    str(engine.get("error_code") or "CONCURRENCY_MISSION_CONTROL_ENGINE_BLOCKED"),
                    "A concurrency mission-control engine did not pass.",
                    subject_id=str(engine.get("engine_id")),
                    observed=engine.get("status"),
                )
            )
    observed = {str(row.get("engine_id")) for row in engines}
    missing = sorted(set(EXPECTED_ENGINES) - observed)
    if missing:
        findings.append(
            finding(
                "CONCURRENCY_MISSION_CONTROL_ENGINE_MISSING",
                "An expected concurrency mission-control engine is missing.",
                observed=missing,
            )
        )
    return {
        "status": "pass" if not findings else "blocked",
        "engine_count": len(engines),
        "engine_ids": sorted(observed),
        "copied_macro_source_module_count": source_manifest.get("module_count", 0),
        "engines": engines,
        "error_codes": [str(code) for codes in EXPECTED_NEGATIVE_CASES.values() for code in codes],
        "body_in_receipt": False,
        "findings": findings,
    }


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    _expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    """[ACTION] Evaluate a negative-case row and return its verdict fields.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `evaluate_negative_case`.
    - Preconditions: Callers provide case_id, input_dir, _expected_codes in the shape
      consumed by the body; write targets must be inside the caller-selected output or
      temporary area.
    - Mechanism: Writes only the output paths named by the caller, temporary workspace,
      or module constants. Normalizes Path values and public-root-relative references
      before returning them. Iterates candidate paths or structured rows exactly as
      written in the body.
    - Guarantee: Returns Mapping[str, Any] from the explicit return paths in the
      function body.
    - Fails: No explicit raise is introduced; failures propagate from filesystem writes,
      called validators/helpers.
    - Reads: call arguments; module constants EXERCISE_MANIFEST_NAME.
    - Writes: filesystem output explicitly written by this body.
    - Couples: EXERCISE_MANIFEST_NAME.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    input_path = Path(input_dir)
    manifest = _load_json(input_path / EXERCISE_MANIFEST_NAME)
    public_root = public_root_for_path(input_path)
    if case_id == "missing_seed_root":
        with tempfile.TemporaryDirectory(prefix="concurrency_missing_seed_") as tmp:
            temp_public_root = Path(tmp) / "microcosm-substrate"
            temp_input = (
                temp_public_root
                / "fixtures/first_wave/concurrency_mission_control/input"
            )
            temp_input.mkdir(parents=True)
            result = _run_original_builder(temp_input, temp_public_root, manifest)
        rejected = (
            result.get("status") == "blocked"
            and result.get("error_code")
            == "CONCURRENCY_MISSION_CONTROL_SEED_ROOT_MISSING"
        )
        return {
            "status": "blocked" if rejected else "pass",
            "case_id": case_id,
            "error_codes": (
                ["CONCURRENCY_MISSION_CONTROL_SEED_ROOT_MISSING"]
                if rejected
                else []
            ),
            "observed": {
                "seed_root_present": result.get("seed_root_present"),
                "error_code": result.get("error_code"),
            },
            "derived_from": "mission_transaction_original_builder_seed_gate",
            "body_in_receipt": False,
        }

    original = _run_original_builder(input_path, public_root, manifest)
    if case_id == "provider_bridge_missing":
        mutated = dict(original)
        mutated["provider_repair_bridge_status"] = "missing"
        membrane = _bridge_authority_membrane(mutated, manifest)
        rejected = membrane.get("status") == "blocked"
        return {
            "status": "blocked" if rejected else "pass",
            "case_id": case_id,
            "error_codes": (
                ["CONCURRENCY_MISSION_CONTROL_PROVIDER_BRIDGE_BLOCKED"]
                if rejected
                else []
            ),
            "observed": {
                "provider_repair_bridge_status": mutated.get(
                    "provider_repair_bridge_status"
                ),
                "bridge_membrane_status": membrane.get("status"),
            },
            "derived_from": "bridge_authority_membrane",
            "body_in_receipt": False,
        }
    if case_id == "authority_collapse_claim":
        mutated = dict(original)
        mutated["authority_collapse_count"] = 1
        membrane = _bridge_authority_membrane(mutated, manifest)
        rejected = membrane.get("status") == "blocked"
        return {
            "status": "blocked" if rejected else "pass",
            "case_id": case_id,
            "error_codes": (
                ["CONCURRENCY_MISSION_CONTROL_AUTHORITY_COLLAPSE"]
                if rejected
                else []
            ),
            "observed": {
                "authority_collapse_count": membrane.get("authority_collapse_count"),
                "bridge_membrane_status": membrane.get("status"),
            },
            "derived_from": "bridge_authority_membrane",
            "body_in_receipt": False,
        }
    if case_id == "private_runtime_claim":
        unsafe_manifest = copy.deepcopy(manifest)
        unsafe_manifest["forbidden_claims"] = [
            value
            for value in unsafe_manifest.get("forbidden_claims", [])
            if value != "private_mission_control_runtime"
        ]
        membrane = _bridge_authority_membrane(original, unsafe_manifest)
        rejected = membrane.get("status") == "blocked"
        return {
            "status": "blocked" if rejected else "pass",
            "case_id": case_id,
            "error_codes": (
                ["CONCURRENCY_MISSION_CONTROL_PRIVATE_RUNTIME_OVERCLAIM"]
                if rejected
                else []
            ),
            "observed": {
                "forbidden_claims_present": membrane.get("forbidden_claims_present"),
                "bridge_membrane_status": membrane.get("status"),
            },
            "derived_from": "bridge_authority_membrane",
            "body_in_receipt": False,
        }
    if case_id == "work_ledger_seed_speed_collision":
        unsafe_manifest = copy.deepcopy(manifest)
        surface = unsafe_manifest.get("work_ledger_seed_speed_surface")
        if isinstance(surface, dict):
            counts = surface.setdefault("counts", {})
            if isinstance(counts, dict):
                counts["claim_collisions"] = 1
            surface["claim_collisions"] = [
                {
                    "claim_id": "claim_public_collision",
                    "path": "microcosm-substrate/src/microcosm_core/organs/concurrency_mission_control.py",
                    "body_in_receipt": False,
                }
            ]
            claim_rows = surface.get("claim_rows")
            if isinstance(claim_rows, list) and claim_rows and isinstance(claim_rows[0], dict):
                claim_rows[0]["collision_count"] = 1
        gate = _work_ledger_seed_speed_gate(unsafe_manifest)
        codes = {
            str(row.get("error_code"))
            for row in gate.get("findings", [])
            if isinstance(row, Mapping)
        }
        rejected = (
            gate.get("status") == "blocked"
            and "CONCURRENCY_MISSION_CONTROL_WORK_LEDGER_COLLISION_UNRESOLVED"
            in codes
        )
        return {
            "status": "blocked" if rejected else "pass",
            "case_id": case_id,
            "error_codes": (
                ["CONCURRENCY_MISSION_CONTROL_WORK_LEDGER_COLLISION_UNRESOLVED"]
                if rejected
                else []
            ),
            "observed": {
                "work_ledger_seed_speed_status": gate.get("status"),
                "finding_codes": sorted(codes),
            },
            "derived_from": "work_ledger_seed_speed_gate",
            "body_in_receipt": False,
        }
    return {
        "status": "pass",
        "case_id": case_id,
        "error_codes": [],
        "body_in_receipt": False,
    }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    acceptance_out: str | Path | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    """[ACTION] Run the organ replay pipeline and return the computed result payload.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `run`.
    - Preconditions: Callers provide input_dir, out_dir, acceptance_out, command in the
      shape consumed by the body.
    - Mechanism: Delegates to run_crown_jewel_organ and applies local branch checks.
    - Guarantee: Returns dict[str, Any] representing the completed replay or bundle
      execution.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments; module constants SPEC.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: SPEC.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_concurrency_mission_control_bundle(
    bundle_dir: str | Path,
    out_dir: str | Path,
    *,
    acceptance_out: str | Path | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    """[ACTION] Implement run concurrency mission control bundle for this organ replay.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `run_concurrency_mission_control_bundle`.
    - Preconditions: Callers provide bundle_dir, out_dir, acceptance_out, command in the
      shape consumed by the body.
    - Mechanism: Delegates to run_crown_jewel_organ and applies local branch checks.
    - Guarantee: Returns dict[str, Any] representing the completed replay or bundle
      execution.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments; module constants BUNDLE_INPUT_MODE, SPEC.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: BUNDLE_INPUT_MODE, SPEC.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    return run_crown_jewel_organ(
        SPEC,
        bundle_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        input_mode=BUNDLE_INPUT_MODE,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    """[ACTION] Build the compact result card from replay output.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `result_card`.
    - Preconditions: Callers provide result in the shape consumed by the body.
    - Mechanism: Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns dict[str, Any] from the explicit return paths in the function
      body.
    - Fails: No explicit raise is introduced; failures propagate from ordinary Python
      evaluation in this body.
    - Reads: call arguments; module constants SPEC.
    - Writes: No external writes; the body only returns in-memory values.
    - Couples: SPEC.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    card = card_for_result(SPEC, result)
    exercise = result.get("exercise") if isinstance(result.get("exercise"), Mapping) else {}
    card["engine_count"] = exercise.get("engine_count")
    card["copied_macro_source_module_count"] = exercise.get("copied_macro_source_module_count")
    engines = exercise.get("engines") if isinstance(exercise.get("engines"), list) else []
    seed_speed = next(
        (
            row
            for row in engines
            if isinstance(row, Mapping)
            and row.get("engine_id") == "work_ledger_seed_speed_gate"
        ),
        {},
    )
    generated_surface_claim_lens = next(
        (
            row
            for row in engines
            if isinstance(row, Mapping)
            and row.get("engine_id") == "generated_surface_claim_lens"
        ),
        {},
    )
    closure_state_lens = next(
        (
            row
            for row in engines
            if isinstance(row, Mapping)
            and row.get("engine_id") == "closure_state_lens"
        ),
        {},
    )
    card["work_ledger_seed_speed_status"] = seed_speed.get("status")
    card["generated_surface_claim_lens_status"] = generated_surface_claim_lens.get(
        "status"
    )
    card["closure_state_lens_status"] = closure_state_lens.get("status")
    return card


def main(argv: list[str] | None = None) -> int:
    """[ACTION] Parse command-line arguments and dispatch the selected organ command.

    - Teleology: Supports concurrency mission control by documenting and preserving the
      exact local step implemented by `main`.
    - Preconditions: Callers provide argv in the shape consumed by the body; write
      targets must be inside the caller-selected output or temporary area.
    - Mechanism: Configures argparse commands and options that the module exposes.
      Writes only the output paths named by the caller, temporary workspace, or module
      constants. Iterates candidate paths or structured rows exactly as written in the
      body.
    - Guarantee: Returns int from the selected CLI command path.
    - Fails: No explicit raise is introduced; failures propagate from filesystem writes.
    - Reads: call arguments; module constants ORGAN_ID.
    - Writes: filesystem output explicitly written by this body.
    - Couples: ORGAN_ID.
    - Non-goal: Does not widen this module's public authority ceiling, add provider
      calls, or expose private material.
    """
    parser = argparse.ArgumentParser(prog=f"microcosm {ORGAN_ID}")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "run-concurrency-mission-control-bundle"):
        action_parser = sub.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
        action_parser.add_argument("--acceptance-out")
        action_parser.add_argument("--card", action="store_true")
    args = parser.parse_args(argv)
    runner = run_concurrency_mission_control_bundle if args.action == "run-concurrency-mission-control-bundle" else run
    result = runner(
        args.input,
        args.out,
        acceptance_out=args.acceptance_out,
        command=f"{ORGAN_ID} {args.action}",
    )
    if args.card:
        print(json.dumps(result_card(result), indent=2, sort_keys=True))
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
