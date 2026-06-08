from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from microcosm_core.resource_root import microcosm_root
from microcosm_core.schemas import read_json_strict


SCHEMA = "microcosm_route_candidate_read_model_v0"
VALIDATION_SCHEMA = "microcosm_route_candidate_read_model_validation_v0"
DEFAULT_OUT_NAME = "route_candidate_read_model.json"
DEFAULT_RECEIPT_NAME = "route_candidate_read_model_receipt.json"
AUTHORITY_POSTURE = "derived_projection_not_source_authority"
SOURCE_REFS = [
    "atlas/agent_task_routes.json::routes",
    "core/organ_registry.json::implemented_organs",
    "core/organ_evidence_classes.json::organ_evidence_classes",
    "receipts/first_wave/agent_route_observability_runtime/exported_agent_trace_route_repair_bundle_validation_result.json",
    "receipts/first_wave/agent_route_observability_runtime/exported_agent_observability_store_bundle_validation_result.json",
]
TARGET_CONSUMER = "route_mining_controller_candidate_selector"
ROUTE_MINING_ORGAN_IDS = {
    "agent_route_observability_runtime",
    "navigation_hologram_route_plane",
    "cold_reader_route_map",
    "pattern_binding_contract",
}
MECHANISM_SPINE_ORGAN_IDS = {
    "certificate_kernel_execution_lab",
    "cognitive_operator_registry",
    "doctrine_fact_claim_audit",
    "durable_agent_work_landing_replay",
    "engine_room_demo",
    "finance_forecast_evaluation_spine",
    "mission_transaction_work_spine",
    "proof_derived_governed_mutation_authorization",
}
REQUIRED_ROW_FIELDS = (
    "candidate_id",
    "organ_id",
    "rank",
    "score",
    "evidence_class",
    "evidence_strength_rank",
    "claim_ceiling",
    "first_command",
    "receipt_refs",
    "source_refs",
    "task_route_ref",
    "route_role",
    "stop_condition",
    "reentry_condition",
    "authority_boundary",
)
BANNED_AUTHORITY_TRUE_KEYS = {
    "generated_projection_is_source_authority",
    "generated_projection_authority",
    "release_authorized",
    "source_mutation_authorized",
    "chat_memory_authority",
}


def _as_dict(value: Any) -> dict[str, Any]:
    """Coerce an arbitrary JSON value to a dict, defaulting non-dicts to empty.

    - Teleology: defensive read helper so the projection tolerates malformed/missing source nodes without raising.
    - Guarantee: returns value unchanged when it is a dict, otherwise an empty dict; never None.
    - Fails: never raises; non-dict input -> {} (silent empty-result envelope).
    """
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    """Coerce an arbitrary JSON value to a list, defaulting non-lists to empty.

    - Teleology: defensive read helper so iteration over source arrays is total even on malformed input.
    - Guarantee: returns value unchanged when it is a list, otherwise an empty list; never None.
    - Fails: never raises; non-list input -> [] (silent empty-result envelope).
    """
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    """Extract the non-empty string members of an arbitrary JSON value.

    - Teleology: normalize ref/string arrays (receipt_refs, source_refs) dropping blanks and non-strings.
    - Guarantee: returns only str items whose stripped form is truthy, preserving source order.
    - Fails: never raises; non-list or all-blank input -> [] (silent empty-result envelope).
    """
    return [item for item in _as_list(value) if isinstance(item, str) and item.strip()]


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    """Read the dict-typed rows under payload[key].

    - Teleology: single accessor for the array-of-objects shape the read model reads from every source manifest.
    - Guarantee: returns only the dict members of payload[key], in source order; non-dicts and missing key are dropped.
    - Fails: never raises; missing key or non-list value -> [] (silent empty-result envelope).
    """
    return [item for item in _as_list(payload.get(key)) if isinstance(item, dict)]


def _load_optional_json(path: Path) -> dict[str, Any]:
    """Read an optional JSON receipt, tolerating absence.

    - Teleology: receipts (trace-repair, observability store) may not exist on a given root; the projection must still build.
    - Guarantee: returns the parsed dict when path is a readable JSON file, else {}; coerces non-dict JSON to {}.
    - Reads: the receipt path passed in (e.g. receipts/first_wave/agent_route_observability_runtime/*.json).
    - Fails: missing file -> {}; malformed/unreadable JSON -> read_json_strict raises (propagates, not swallowed).
    - Non-goal: does not authorize source-body export, release, or treat the receipt as source-of-truth authority.
    """
    if not path.is_file():
        return {}
    return _as_dict(read_json_strict(path))


def _public_microcosm_command(command: str) -> str:
    """Rewrite an internal `python -m microcosm_core...` command to its public `microcosm` form.

    - Teleology: candidate first_command must be the public-safe CLI surface, not the internal module path.
    - Guarantee: returns the `microcosm <organ-or-subcommand> ...` form when the input is a recognized organ/cli module invocation; otherwise returns the input string unchanged.
    - Fails: never raises; unrecognized shape -> command returned verbatim (identity envelope).
    - Non-goal: does not validate that the rewritten command exists, authorize execution, or guarantee public-safe equivalence beyond the literal prefix swap.
    """
    parts = command.split()
    if len(parts) >= 4 and parts[0] in {"python", "python3"} and parts[1] == "-m":
        module = parts[2]
        if module.startswith("microcosm_core.organs."):
            organ = module.rsplit(".", 1)[-1].replace("_", "-")
            return " ".join(["microcosm", organ, *parts[3:]])
        if module == "microcosm_core.cli":
            return " ".join(["microcosm", *parts[3:]])
    return command


def _by_organ_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index registry rows by their organ_id.

    - Teleology: O(1) lookup of an organ's registry record while scoring candidates.
    - Guarantee: returns a dict keyed by stripped non-empty organ_id; on duplicate ids the last row wins; blank ids dropped.
    - Fails: never raises; empty input or all-blank ids -> {} (silent empty-result envelope).
    """
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        organ_id = str(row.get("organ_id") or "").strip()
        if organ_id:
            result[organ_id] = row
    return result


def _route_organ_ids(row: dict[str, Any]) -> list[str]:
    """Collect every organ_id referenced by a single agent-task-route row.

    - Teleology: a route can name a primary organ plus several relevant organs; this flattens them for index building.
    - Guarantee: returns deduplicated stripped organ_ids in first-seen order across organ_id, primary_organ_id, and relevant_organs (dict or string members).
    - Reads: route row fields organ_id / primary_organ_id / relevant_organs from atlas/agent_task_routes.json.
    - Fails: never raises; row with no usable ids -> [] (silent empty-result envelope).
    """
    organ_ids: list[str] = []
    for key in ("organ_id", "primary_organ_id"):
        organ_id = str(row.get(key) or "").strip()
        if organ_id:
            organ_ids.append(organ_id)
    for item in _as_list(row.get("relevant_organs")):
        if isinstance(item, dict):
            organ_id = str(item.get("organ_id") or "").strip()
        else:
            organ_id = str(item or "").strip()
        if organ_id:
            organ_ids.append(organ_id)
    return sorted(set(organ_ids), key=organ_ids.index)


def _route_index(routes_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build an organ_id -> route-row index, preferring primary routes over relevant/legacy matches.

    - Teleology: lets the builder attach the most authoritative task route to each candidate organ.
    - Guarantee: returns a dict keyed by organ_id where each row carries a `_candidate_route_relation` tag of primary > relevant > legacy_ref; primary mappings override relevant ones for the same organ.
    - Reads: routes_payload["routes"] from atlas/agent_task_routes.json (primary_organ_id, relevant_organs, evidence_ref, drilldown_target).
    - Fails: never raises; no routes -> {} (silent empty-result envelope).
    - Non-goal: does not validate route correctness or authorize the routes as source authority.
    """
    primary_by_organ: dict[str, dict[str, Any]] = {}
    relevant_by_organ: dict[str, dict[str, Any]] = {}
    for row in _rows(routes_payload, "routes"):
        primary_organ_id = str(row.get("primary_organ_id") or row.get("organ_id") or "").strip()
        if primary_organ_id and primary_organ_id not in primary_by_organ:
            primary_by_organ[primary_organ_id] = {**row, "_candidate_route_relation": "primary"}
        for organ_id in _route_organ_ids(row):
            if organ_id and organ_id not in relevant_by_organ:
                relevant_by_organ[organ_id] = {**row, "_candidate_route_relation": "relevant"}
        evidence_ref = str(row.get("evidence_ref") or "")
        drilldown = str(row.get("drilldown_target") or "")
        for candidate in ROUTE_MINING_ORGAN_IDS:
            if candidate in relevant_by_organ:
                continue
            if f"organ_id={candidate}" in evidence_ref or candidate.replace("_", "-") in drilldown:
                relevant_by_organ[candidate] = {**row, "_candidate_route_relation": "legacy_ref"}
    return {**relevant_by_organ, **primary_by_organ}


def _task_route_ref(route_row: dict[str, Any]) -> str:
    """Render the canonical source-ref string pointing at a route's task_class entry.

    - Teleology: gives each candidate a stable, greppable provenance pointer back into the routes manifest.
    - Guarantee: returns "atlas/agent_task_routes.json::routes[task_class=<task_class>]" when task_class is non-empty, else "".
    - Reads: route row field task_class.
    - Fails: never raises; missing/blank task_class -> "" (empty-result envelope).
    """
    task_class = str(route_row.get("task_class") or "").strip()
    if not task_class:
        return ""
    return f"atlas/agent_task_routes.json::routes[task_class={task_class}]"


def _evidence_profiles(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Normalize the organ_evidence_classes map to organ_id -> profile dict.

    - Teleology: attaches each candidate its evidence profile so the read model exposes evidence class/strength provenance.
    - Guarantee: returns a dict keyed by stringified organ_id with dict-coerced profile values when organ_evidence_classes is a mapping, else {}.
    - Reads: payload["organ_evidence_classes"] from core/organ_evidence_classes.json.
    - Fails: never raises; missing or non-dict node -> {} (empty-result envelope).
    """
    profiles = payload.get("organ_evidence_classes")
    if isinstance(profiles, dict):
        return {str(key): _as_dict(value) for key, value in profiles.items()}
    return {}


def _source_module_summary(receipt: dict[str, Any]) -> dict[str, Any]:
    """Summarize the observed source-module manifest carried by an observability receipt.

    - Teleology: surfaces how many real source modules backed the observability store, with their source refs, as evidence depth.
    - Guarantee: returns {source_module_count, source_refs (sorted unique), body_in_receipt (bool), body_import_verification (dict)} read from receipt["source_module_manifest"].
    - Reads: receipt fields source_module_manifest.observed_modules|modules (source_ref|path|target_ref), body_in_receipt, body_import_verification.
    - Fails: never raises; missing manifest -> count 0, empty refs (empty-result envelope).
    - Non-goal: reports the receipt's own body_in_receipt flag; does not itself export source bodies or authorize public-safe equivalence.
    """
    manifest = _as_dict(receipt.get("source_module_manifest"))
    observed = _rows(manifest, "observed_modules")
    if not observed:
        observed = _rows(manifest, "modules")
    source_refs: list[str] = []
    for row in observed:
        ref = str(row.get("source_ref") or row.get("path") or row.get("target_ref") or "").strip()
        if ref:
            source_refs.append(ref)
    return {
        "source_module_count": len(observed),
        "source_refs": sorted(set(source_refs)),
        "body_in_receipt": receipt.get("body_in_receipt") is True,
        "body_import_verification": _as_dict(receipt.get("body_import_verification")),
    }


def _trace_repair_summary(receipt: dict[str, Any]) -> dict[str, Any]:
    """Summarize the route-repair receipt into the support block for the observability candidate.

    - Teleology: gives the route-mining controller evidence that this organ would have repaired recent route failures.
    - Guarantee: returns {receipt_ref=SOURCE_REFS[3], route_repair_row_count, would_intervene_on_recent_route_failures, suggested_routes[...]} drawn from receipt["route_repair_rows"] (only rows that carry a suggested_route).
    - Reads: receipt fields route_repair_rows, route_repair_summary.would_intervene_on_recent_route_failures.
    - Fails: never raises; empty/missing receipt -> count 0, empty suggested_routes (empty-result envelope).
    - Escalates-to: the named source receipt at SOURCE_REFS[3] for full row fidelity.
    """
    rows = _rows(receipt, "route_repair_rows")
    return {
        "receipt_ref": SOURCE_REFS[3],
        "route_repair_row_count": len(rows),
        "would_intervene_on_recent_route_failures": _as_dict(
            receipt.get("route_repair_summary")
        ).get("would_intervene_on_recent_route_failures", 0),
        "suggested_routes": [
            {
                "anti_pattern_id": row.get("anti_pattern_id"),
                "repair_class": row.get("repair_class"),
                "suggested_route": row.get("suggested_route"),
                "fallback_surface": row.get("fallback_surface"),
                "confidence": row.get("confidence"),
            }
            for row in rows
            if row.get("suggested_route")
        ],
    }


def _observability_summary(receipt: dict[str, Any]) -> dict[str, Any]:
    """Summarize the observability-store receipt into the support block for the observability candidate.

    - Teleology: gives the candidate evidence of live route-decision events and active sessions plus its source-module footprint.
    - Guarantee: returns {receipt_ref=SOURCE_REFS[4], route_decision_event_count, active_session_count, source_module=_source_module_summary(receipt)}, preferring top-level counts then store_summary fallbacks then 0.
    - Reads: receipt fields store_summary, route_decision_event_count, active_session_count, source_module_manifest.
    - Fails: never raises; empty/missing receipt -> counts 0, empty source_module (empty-result envelope).
    - Escalates-to: the named source receipt at SOURCE_REFS[4] for full store fidelity.
    """
    summary = _as_dict(receipt.get("store_summary"))
    return {
        "receipt_ref": SOURCE_REFS[4],
        "route_decision_event_count": receipt.get(
            "route_decision_event_count", summary.get("route_decision_event_count", 0)
        ),
        "active_session_count": receipt.get("active_session_count", summary.get("active_session_count", 0)),
        "source_module": _source_module_summary(receipt),
    }


def _score_candidate(
    registry_row: dict[str, Any],
    route_row: dict[str, Any],
    *,
    receipt_count: int,
    source_module_count: int,
    trace_repair_count: int,
) -> int:
    """Compute the integer ranking score for one route candidate from registry + route + receipt evidence.

    - Teleology: deterministic, evidence-weighted score that orders candidates for the route-mining selector.
    - Guarantee: returns a non-negative int = 10*evidence_strength_rank plus bounded bonuses for first_command (+8), current_authority_receipt (+8), capped receipt/source-module/trace-repair counts, accepted_current_authority status (+8), and counts_as_real_substrate_progress (+4).
    - Reads: registry_row evidence_strength_rank/current_authority_receipt/status/counts_as_real_substrate_progress and route_row first_command.
    - Fails: never raises; missing/non-numeric fields coerce to 0, yielding a low but valid score.
    - Non-goal: a higher score is a ranking signal only; it does not assert release-readiness or substrate authority.
    """
    score = int(registry_row.get("evidence_strength_rank") or 0) * 10
    if route_row.get("first_command"):
        score += 8
    if registry_row.get("current_authority_receipt"):
        score += 8
    score += min(receipt_count, 6) * 3
    score += min(source_module_count, 8) * 2
    score += min(trace_repair_count, 4) * 2
    if registry_row.get("status") == "accepted_current_authority":
        score += 8
    if registry_row.get("counts_as_real_substrate_progress") is True:
        score += 4
    return score


def build_route_candidate_read_model(root: str | Path | None = None) -> dict[str, Any]:
    """Build the ranked, projection-only route-candidate read model from the live substrate.

    - Teleology: derives the route_mining_controller_candidate_selector's input — a ranked roster of route-mining + mechanism-spine organs with evidence, first commands, and authority boundaries.
    - Guarantee: returns a schema=SCHEMA dict with candidate_rows sorted by descending score (rank reassigned 1..N), authority_posture=AUTHORITY_POSTURE, and every banned authority key (generated_projection_is_source_authority, chat_memory_authority, source_mutation_authorized, release_authorized) hard-set False.
    - Reads: <root>/atlas/agent_task_routes.json, core/organ_registry.json, core/organ_evidence_classes.json, and the two optional agent_route_observability_runtime receipts.
    - When-needed: when refreshing or auditing which public route candidates the selector should mine next.
    - Fails: missing required manifests -> read_json_strict raises (propagates); missing optional receipts -> empty support blocks, build still succeeds.
    - Escalates-to: validate_route_candidate_read_model / compile_paths for the validated, persisted form; SOURCE_REFS for upstream fidelity.
    - Non-goal: this is a GENERATED derived projection; it does not authorize release, source mutation, or treat itself as source-of-truth authority.
    """
    resolved_root = Path(root).resolve() if root is not None else microcosm_root()
    routes_payload = _as_dict(read_json_strict(resolved_root / "atlas/agent_task_routes.json"))
    registry_payload = _as_dict(read_json_strict(resolved_root / "core/organ_registry.json"))
    evidence_payload = _as_dict(read_json_strict(resolved_root / "core/organ_evidence_classes.json"))
    trace_repair_receipt = _load_optional_json(
        resolved_root
        / "receipts/first_wave/agent_route_observability_runtime/"
        "exported_agent_trace_route_repair_bundle_validation_result.json"
    )
    store_receipt = _load_optional_json(
        resolved_root
        / "receipts/first_wave/agent_route_observability_runtime/"
        "exported_agent_observability_store_bundle_validation_result.json"
    )

    registry_by_id = _by_organ_id(_rows(registry_payload, "implemented_organs"))
    route_by_id = _route_index(routes_payload)
    evidence_profiles = _evidence_profiles(evidence_payload)
    trace_summary = _trace_repair_summary(trace_repair_receipt)
    store_summary = _observability_summary(store_receipt)
    source_module_count = int(_as_dict(store_summary.get("source_module")).get("source_module_count") or 0)
    trace_repair_count = int(trace_summary.get("route_repair_row_count") or 0)

    candidates: list[dict[str, Any]] = []
    candidate_ids = sorted(ROUTE_MINING_ORGAN_IDS | MECHANISM_SPINE_ORGAN_IDS)
    for organ_id in candidate_ids:
        registry_row = registry_by_id.get(organ_id, {})
        route_row = route_by_id.get(organ_id, {})
        receipt_refs = _strings(registry_row.get("generated_receipts"))
        current_receipt = str(registry_row.get("current_authority_receipt") or "").strip()
        if current_receipt:
            receipt_refs.insert(0, current_receipt)
        if organ_id == "agent_route_observability_runtime":
            receipt_refs.extend([SOURCE_REFS[3], SOURCE_REFS[4]])
        source_refs = [
            "core/organ_registry.json::implemented_organs[organ_id="
            f"{organ_id}]",
            "atlas/agent_task_routes.json::routes",
            str(registry_row.get("evidence_profile_ref") or ""),
        ]
        source_refs.extend(_strings(registry_row.get("source_refs")))
        if organ_id == "agent_route_observability_runtime":
            source_refs.extend(_as_dict(store_summary.get("source_module")).get("source_refs", []))

        route_relation = str(route_row.get("_candidate_route_relation") or "").strip()
        route_is_primary = route_relation == "primary"
        first_command = _public_microcosm_command(
            str(
                (
                    route_row.get("first_command")
                    if route_is_primary
                    else registry_row.get("validator_command")
                )
                or route_row.get("first_command")
                or registry_row.get("validator_command")
                or ""
            ).strip()
        )
        task_route_ref = _task_route_ref(route_row)
        route_refs = {
            "task_route_ref": task_route_ref,
            "task_class": route_row.get("task_class"),
            "route_role": route_row.get("route_role"),
            "route_relation": route_relation or None,
            "primary_organ_id": route_row.get("primary_organ_id") or route_row.get("organ_id"),
            "evidence_ref": route_row.get("evidence_ref"),
            "receipt_ref": route_row.get("receipt_ref"),
            "drilldown_target": route_row.get("drilldown_target"),
            "stop_condition": route_row.get("stop_condition"),
            "selector_first_command": route_row.get("first_command"),
        }
        score = _score_candidate(
            registry_row,
            route_row,
            receipt_count=len([ref for ref in receipt_refs if ref]),
            source_module_count=source_module_count if organ_id == "agent_route_observability_runtime" else 0,
            trace_repair_count=trace_repair_count if organ_id == "agent_route_observability_runtime" else 0,
        )
        candidates.append(
            {
                "candidate_id": f"route_candidate:{organ_id}",
                "candidate_group": (
                    "route_mining"
                    if organ_id in ROUTE_MINING_ORGAN_IDS
                    else "mechanism_spine"
                ),
                "organ_id": organ_id,
                "rank": 0,
                "score": score,
                "evidence_class": registry_row.get("evidence_class"),
                "evidence_strength_rank": registry_row.get("evidence_strength_rank"),
                "evidence_profile": evidence_profiles.get(organ_id, {}),
                "claim_ceiling": registry_row.get("claim_ceiling"),
                "first_command": first_command,
                "task_class": route_row.get("task_class"),
                "task_route_ref": task_route_ref,
                "route_role": route_row.get("route_role"),
                "stop_condition": route_row.get("stop_condition"),
                "receipt_refs": sorted(set(ref for ref in receipt_refs if ref)),
                "source_refs": sorted(set(ref for ref in source_refs if ref)),
                "route_refs": route_refs,
                "reentry_condition": (
                    "safe_to_mine_next_lane_when_work_ledger_claims_clear_and_candidate "
                    "retains first_command, receipt_refs, source_refs, and claim_ceiling"
                ),
                "authority_boundary": (
                    "projection ranks public route candidates; generated projections, chat memory, "
                    "and route names alone are not source authority"
                ),
                "trace_repair_support": trace_summary if organ_id == "agent_route_observability_runtime" else {},
                "observability_store_support": store_summary if organ_id == "agent_route_observability_runtime" else {},
            }
        )

    candidates.sort(key=lambda row: (-int(row["score"]), str(row["organ_id"])))
    for index, row in enumerate(candidates, start=1):
        row["rank"] = index

    return {
        "schema_version": SCHEMA,
        "status": "pass",
        "authority_posture": AUTHORITY_POSTURE,
        "consumer_id": TARGET_CONSUMER,
        "source_refs": SOURCE_REFS,
        "candidate_count": len(candidates),
        "top_candidate_id": candidates[0]["candidate_id"] if candidates else None,
        "route_mining_controller_ready": bool(candidates),
        "generated_projection_is_source_authority": False,
        "chat_memory_authority": False,
        "source_mutation_authorized": False,
        "release_authorized": False,
        "field_preservation_contract": {
            "required_row_fields": list(REQUIRED_ROW_FIELDS),
            "banned_authority_true_keys": sorted(BANNED_AUTHORITY_TRUE_KEYS),
        },
        "candidate_rows": candidates,
    }


def validate_route_candidate_read_model(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a route-candidate read model against its schema, authority, and ranking invariants.

    - Teleology: the guard that keeps the projection projection-only, source-backed, and correctly ranked before any consumer trusts it.
    - Guarantee: returns a schema=VALIDATION_SCHEMA dict with status "pass" iff zero errors else "blocked", plus error_count and per-error {path, code, message}; checks schema_version, authority_posture, banned-true authority keys, required row fields, receipt+source backing, and descending-score ordering.
    - When-needed: after building/editing the read model, to confirm it is safe for the route-mining controller.
    - Fails: never raises; each violation appends an error and flips status to "blocked" (status-field envelope, not an exception).
    - Escalates-to: REQUIRED_ROW_FIELDS / BANNED_AUTHORITY_TRUE_KEYS for the exact contract; the projection's test suite for regression coverage.
    - Non-goal: validates shape and authority posture only; does not authorize release or assert whole-system correctness.
    """
    errors: list[dict[str, str]] = []
    if payload.get("schema_version") != SCHEMA:
        errors.append(
            {
                "path": "schema_version",
                "code": "unexpected_schema_version",
                "message": f"Expected {SCHEMA}.",
            }
        )
    if payload.get("authority_posture") != AUTHORITY_POSTURE:
        errors.append(
            {
                "path": "authority_posture",
                "code": "authority_posture_not_projection_only",
                "message": "Route candidates must stay projection-only.",
            }
        )
    for key in BANNED_AUTHORITY_TRUE_KEYS:
        if payload.get(key) is True:
            errors.append(
                {
                    "path": key,
                    "code": "banned_authority_claim_true",
                    "message": "Route candidate read model cannot authorize this authority.",
                }
            )
    rows = _rows(payload, "candidate_rows")
    if not rows:
        errors.append(
            {
                "path": "candidate_rows",
                "code": "no_route_candidates",
                "message": "At least one source-backed route candidate is required.",
            }
        )
    previous_score: int | None = None
    for index, row in enumerate(rows):
        for field in REQUIRED_ROW_FIELDS:
            if row.get(field) in (None, "", [], {}):
                errors.append(
                    {
                        "path": f"candidate_rows[{index}].{field}",
                        "code": "candidate_missing_required_field",
                        "message": f"Candidate row must preserve {field}.",
                    }
                )
        if not _strings(row.get("receipt_refs")) or not _strings(row.get("source_refs")):
            errors.append(
                {
                    "path": f"candidate_rows[{index}]",
                    "code": "candidate_not_source_backed",
                    "message": "Candidate rows need both receipt refs and source refs.",
                }
            )
        score = int(row.get("score") or 0)
        if previous_score is not None and score > previous_score:
            errors.append(
                {
                    "path": f"candidate_rows[{index}].score",
                    "code": "candidate_rows_not_ranked",
                    "message": "Candidates must be sorted by descending score.",
                }
            )
        previous_score = score
    return {
        "schema_version": VALIDATION_SCHEMA,
        "status": "pass" if not errors else "blocked",
        "error_count": len(errors),
        "errors": errors,
        "candidate_count": len(rows),
    }


def compile_paths(root: str | Path | None = None, out: str | Path | None = None) -> dict[str, Any]:
    """Build, validate, fold validation into the payload, and optionally persist the read model + receipt.

    - Teleology: one-call compile that produces the validated projection and its on-disk artifacts for downstream consumers.
    - Guarantee: returns the payload with payload["validation"] attached and payload["status"] set to the validation status; when out is given, writes sorted-keys JSON for both files and creates the directory.
    - Reads: same substrate as build_route_candidate_read_model (atlas routes, organ registry, evidence classes, observability receipts).
    - Writes: <out>/route_candidate_read_model.json (DEFAULT_OUT_NAME) and <out>/route_candidate_read_model_receipt.json (DEFAULT_RECEIPT_NAME) with body_in_receipt=False.
    - When-needed: when the selector or a test needs the validated read model materialized on disk.
    - Fails: required-manifest read errors propagate from the builder; out-path write/mkdir errors propagate (OSError); a "blocked" validation still returns + writes but with status "blocked".
    - Escalates-to: the written receipt JSON and validate_route_candidate_read_model for the authoritative status.
    - Non-goal: writing these GENERATED artifacts does not authorize release or make the projection source-of-truth authority.
    """
    payload = build_route_candidate_read_model(root=root)
    validation = validate_route_candidate_read_model(payload)
    payload["validation"] = validation
    payload["status"] = validation["status"]
    if out is not None:
        out_path = Path(out)
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / DEFAULT_OUT_NAME).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        receipt = {
            "schema_version": "microcosm_route_candidate_read_model_receipt_v0",
            "status": payload["status"],
            "source_refs": SOURCE_REFS,
            "candidate_count": payload["candidate_count"],
            "top_candidate_id": payload["top_candidate_id"],
            "authority_posture": AUTHORITY_POSTURE,
            "body_in_receipt": False,
        }
        (out_path / DEFAULT_RECEIPT_NAME).write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return payload


def main(argv: list[str] | None = None) -> int:
    """CLI entry: build and validate the Microcosm route-candidate read model.

    - Teleology: command-line front door producing the ranked route-candidate projection consumed by the route-mining controller.
    - Guarantee: prints the validated payload as JSON and, when --out is given, writes the read model plus receipt; returns 0 iff status is "pass".
    - Reads: --root microcosm-substrate (atlas routes, organ registry, evidence classes, observability receipts).
    - Writes: optional --out directory (route_candidate_read_model.json + receipt) via compile_paths.
    - When-needed: refreshing the projection-only route-candidate ranking for the selector.
    - Fails: validation status != "pass" -> nonzero exit -> return code 1.
    """
    parser = argparse.ArgumentParser(description="Build the Microcosm route-candidate read model.")
    parser.add_argument("--root", default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    payload = compile_paths(root=args.root, out=args.out)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
