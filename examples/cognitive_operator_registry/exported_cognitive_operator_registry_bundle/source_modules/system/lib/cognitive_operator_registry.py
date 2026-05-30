"""
Build and validate cognitive-operator registry projections.

The registry is agent-authored substrate for reusable thinking moves. It is
not raw seed and does not mutate doctrine authorities while projecting rows.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


REGISTRY_PATH = Path("codex/doctrine/cognitive_operators.json")
STANDARD_PATH = Path("codex/standards/std_cognitive_operator.json")
DOGFOOD_ROOT = Path("state/cognitive_operators/dogfood")
REQUIRED_DOGFOOD_RECEIPT_FIELDS = (
    "receipt_id",
    "operator_id",
    "live_problem",
    "evidence_surfaces",
    "candidate_set",
    "selected_operator",
    "actions_taken",
    "cognition_delta_evidence",
    "result_state",
)
COUNTEREVIDENCE_RECEIPT_FIELDS = (
    "counterevidence_checked",
    "disconfirmation_result",
    "surviving_claim",
)
CAUSAL_TRIAL_RECEIPT_FIELDS = (
    "pre_action_prediction",
    "no_effect_falsifier",
    "intervention",
    "post_action_observation",
    "prediction_result",
)
COMPOSITION_RECEIPT_FIELDS = (
    "operator_sequence",
    "composition_decision",
    "handoff_contracts",
    "sequence_result",
)
PASSPORT_PROPAGATION_RECEIPT_FIELDS = (
    "source_operator_id",
    "target_operator_passport_written",
    "coverage_before",
    "coverage_after",
    "remaining_unpassportized_operators",
    "next_propagation_rule",
)
ROUTE_LEASE_RECEIPT_FIELDS = (
    "route_lease_id",
    "lease_selected_lane",
    "direct_action_boundary",
    "consumed_by_action",
    "forbidden_followup_routes",
    "validation_return_condition",
)
PROMPT_ROUTE_ASSIMILATION_RECEIPT_FIELDS = (
    "source_lens",
    "prompt_phrase",
    "route_miss_evidence",
    "target_surface",
    "routing_mutation",
    "validation_prompt",
    "retention_check",
)
PRESSURE_REDUCTION_RECEIPT_FIELDS = (
    "pressure_surfaces",
    "selected_pressure",
    "rejected_pressures",
    "decision_axes",
    "bounded_action",
    "status_binding_target",
    "validation_return_condition",
)
OPERATOR_ACCRETION_RECEIPT_FIELDS = (
    "candidate_operator",
    "nearest_existing_operators",
    "novelty_test",
    "merge_or_extend_decision",
    "accretion_risk",
    "install_or_cap_decision",
    "future_reentry_rule",
)
ATTENTION_FRAME_RECEIPT_FIELDS = (
    "attention_frame_surface",
    "frame_binding",
    "retained_handles",
    "freshness_constraints",
    "mutation_boundary",
    "rehydration_result",
    "validation_return_condition",
)
LANDING_HANDOFF_RECEIPT_FIELDS = (
    "landing_blocker",
    "owned_path_set",
    "validation_evidence",
    "commit_authority_requirement",
    "handoff_packet",
    "status_binding",
    "reentry_rule",
)
AFFORDANCE_PASSPORT_FIELDS = (
    "cluster_keys",
    "atom",
    "when_to_open",
    "when_not_to_open",
    "safe_drilldown",
    "landmines",
    "sufficiency_claims",
)
AUTHORITY_PLANE_OPTION_SURFACES = {
    "cognitive_operators": "cognitive_operators",
    "concepts": "concepts",
    "mechanisms": "mechanisms",
    "skills": "skills",
    "standards": "standards",
}


def _safe_load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _relative(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def load_cognitive_operator_registry(repo_root: Path | str) -> dict[str, Any]:
    payload = _safe_load_json(Path(repo_root) / REGISTRY_PATH)
    return payload if isinstance(payload, dict) else {}


def cognitive_operator_rows(repo_root: Path | str) -> list[dict[str, Any]]:
    registry = load_cognitive_operator_registry(repo_root)
    operators = registry.get("operators")
    if not isinstance(operators, list):
        return []
    return [item for item in operators if isinstance(item, dict)]


def _dogfood_receipts(repo_root: Path, operator: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ref in operator.get("dogfood_receipt_refs") or []:
        rel = str(ref or "")
        payload = _safe_load_json(repo_root / rel)
        if not isinstance(payload, dict):
            rows.append({"source_ref": rel, "status": "missing_or_invalid"})
            continue
        row = dict(payload)
        row["source_ref"] = rel
        row["status"] = "available"
        rows.append(row)
    return rows


def _has_complete_affordance_passport(operator: Mapping[str, Any]) -> bool:
    compression_passport = (
        operator.get("compression_passport")
        if isinstance(operator.get("compression_passport"), Mapping)
        else {}
    )
    return all(bool(compression_passport.get(field)) for field in AFFORDANCE_PASSPORT_FIELDS)


def _operator_validation(operator: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    required = [
        "operator_id",
        "slug",
        "title",
        "status",
        "claim",
        "activation",
        "process",
        "integration",
        "validation",
        "evidence_refs",
        "dogfood_receipt_refs",
    ]
    missing = [field for field in required if not operator.get(field)]
    activation = operator.get("activation") if isinstance(operator.get("activation"), Mapping) else {}
    integration = operator.get("integration") if isinstance(operator.get("integration"), Mapping) else {}
    dogfood = _dogfood_receipts(repo_root, operator)
    counterevidence_contract = (
        operator.get("counterevidence_contract")
        if isinstance(operator.get("counterevidence_contract"), Mapping)
        else {}
    )
    causal_trial_contract = (
        operator.get("causal_trial_contract")
        if isinstance(operator.get("causal_trial_contract"), Mapping)
        else {}
    )
    composition_contract = (
        operator.get("composition_contract")
        if isinstance(operator.get("composition_contract"), Mapping)
        else {}
    )
    affordance_passport_contract = (
        operator.get("affordance_passport_contract")
        if isinstance(operator.get("affordance_passport_contract"), Mapping)
        else {}
    )
    passport_propagation_contract = (
        operator.get("passport_propagation_contract")
        if isinstance(operator.get("passport_propagation_contract"), Mapping)
        else {}
    )
    route_lease_contract = (
        operator.get("route_lease_contract")
        if isinstance(operator.get("route_lease_contract"), Mapping)
        else {}
    )
    prompt_route_assimilation_contract = (
        operator.get("prompt_route_assimilation_contract")
        if isinstance(operator.get("prompt_route_assimilation_contract"), Mapping)
        else {}
    )
    pressure_reduction_contract = (
        operator.get("pressure_reduction_contract")
        if isinstance(operator.get("pressure_reduction_contract"), Mapping)
        else {}
    )
    operator_accretion_contract = (
        operator.get("operator_accretion_contract")
        if isinstance(operator.get("operator_accretion_contract"), Mapping)
        else {}
    )
    attention_frame_contract = (
        operator.get("attention_frame_contract")
        if isinstance(operator.get("attention_frame_contract"), Mapping)
        else {}
    )
    landing_handoff_contract = (
        operator.get("landing_handoff_contract")
        if isinstance(operator.get("landing_handoff_contract"), Mapping)
        else {}
    )
    compression_passport = (
        operator.get("compression_passport")
        if isinstance(operator.get("compression_passport"), Mapping)
        else {}
    )
    required_counterevidence_fields = tuple(
        str(field)
        for field in (
            counterevidence_contract.get("required_receipt_fields")
            if isinstance(counterevidence_contract.get("required_receipt_fields"), list)
            else COUNTEREVIDENCE_RECEIPT_FIELDS
        )
        if str(field or "").strip()
    )
    required_causal_trial_fields = tuple(
        str(field)
        for field in (
            causal_trial_contract.get("required_receipt_fields")
            if isinstance(causal_trial_contract.get("required_receipt_fields"), list)
            else CAUSAL_TRIAL_RECEIPT_FIELDS
        )
        if str(field or "").strip()
    )
    required_composition_fields = tuple(
        str(field)
        for field in (
            composition_contract.get("required_receipt_fields")
            if isinstance(composition_contract.get("required_receipt_fields"), list)
            else COMPOSITION_RECEIPT_FIELDS
        )
        if str(field or "").strip()
    )
    required_passport_propagation_fields = tuple(
        str(field)
        for field in (
            passport_propagation_contract.get("required_receipt_fields")
            if isinstance(passport_propagation_contract.get("required_receipt_fields"), list)
            else PASSPORT_PROPAGATION_RECEIPT_FIELDS
        )
        if str(field or "").strip()
    )
    required_route_lease_fields = tuple(
        str(field)
        for field in (
            route_lease_contract.get("required_receipt_fields")
            if isinstance(route_lease_contract.get("required_receipt_fields"), list)
            else ROUTE_LEASE_RECEIPT_FIELDS
        )
        if str(field or "").strip()
    )
    required_prompt_route_assimilation_fields = tuple(
        str(field)
        for field in (
            prompt_route_assimilation_contract.get("required_receipt_fields")
            if isinstance(prompt_route_assimilation_contract.get("required_receipt_fields"), list)
            else PROMPT_ROUTE_ASSIMILATION_RECEIPT_FIELDS
        )
        if str(field or "").strip()
    )
    required_pressure_reduction_fields = tuple(
        str(field)
        for field in (
            pressure_reduction_contract.get("required_receipt_fields")
            if isinstance(pressure_reduction_contract.get("required_receipt_fields"), list)
            else PRESSURE_REDUCTION_RECEIPT_FIELDS
        )
        if str(field or "").strip()
    )
    required_operator_accretion_fields = tuple(
        str(field)
        for field in (
            operator_accretion_contract.get("required_receipt_fields")
            if isinstance(operator_accretion_contract.get("required_receipt_fields"), list)
            else OPERATOR_ACCRETION_RECEIPT_FIELDS
        )
        if str(field or "").strip()
    )
    required_attention_frame_fields = tuple(
        str(field)
        for field in (
            attention_frame_contract.get("required_receipt_fields")
            if isinstance(attention_frame_contract.get("required_receipt_fields"), list)
            else ATTENTION_FRAME_RECEIPT_FIELDS
        )
        if str(field or "").strip()
    )
    required_landing_handoff_fields = tuple(
        str(field)
        for field in (
            landing_handoff_contract.get("required_receipt_fields")
            if isinstance(landing_handoff_contract.get("required_receipt_fields"), list)
            else LANDING_HANDOFF_RECEIPT_FIELDS
        )
        if str(field or "").strip()
    )
    receipt_failures = [
        str(row.get("source_ref") or "")
        for row in dogfood
        if row.get("status") != "available"
        or not row.get("cognition_delta_evidence")
        or row.get("operator_id") != operator.get("operator_id")
    ]
    for row in dogfood:
        source_ref = str(row.get("source_ref") or "")
        if row.get("status") != "available":
            continue
        missing_receipt_fields = [field for field in REQUIRED_DOGFOOD_RECEIPT_FIELDS if not row.get(field)]
        if missing_receipt_fields:
            receipt_failures.extend(f"{source_ref}:missing_receipt_field:{field}" for field in missing_receipt_fields)
        if counterevidence_contract.get("required"):
            missing_counterevidence_fields = [
                field for field in required_counterevidence_fields if not row.get(field)
            ]
            if missing_counterevidence_fields:
                receipt_failures.extend(
                    f"{source_ref}:missing_counterevidence_field:{field}"
                    for field in missing_counterevidence_fields
                )
        if causal_trial_contract.get("required"):
            missing_causal_trial_fields = [
                field for field in required_causal_trial_fields if not row.get(field)
            ]
            if missing_causal_trial_fields:
                receipt_failures.extend(
                    f"{source_ref}:missing_causal_trial_field:{field}"
                    for field in missing_causal_trial_fields
                )
        if composition_contract.get("required"):
            missing_composition_fields = [
                field for field in required_composition_fields if not row.get(field)
            ]
            if missing_composition_fields:
                receipt_failures.extend(
                    f"{source_ref}:missing_composition_field:{field}"
                    for field in missing_composition_fields
                )
        if passport_propagation_contract.get("required"):
            missing_passport_propagation_fields = [
                field for field in required_passport_propagation_fields if not row.get(field)
            ]
            if missing_passport_propagation_fields:
                receipt_failures.extend(
                    f"{source_ref}:missing_passport_propagation_field:{field}"
                    for field in missing_passport_propagation_fields
                )
        if route_lease_contract.get("required"):
            missing_route_lease_fields = [
                field for field in required_route_lease_fields if not row.get(field)
            ]
            if missing_route_lease_fields:
                receipt_failures.extend(
                    f"{source_ref}:missing_route_lease_field:{field}"
                    for field in missing_route_lease_fields
                )
        if prompt_route_assimilation_contract.get("required"):
            missing_prompt_route_assimilation_fields = [
                field for field in required_prompt_route_assimilation_fields if not row.get(field)
            ]
            if missing_prompt_route_assimilation_fields:
                receipt_failures.extend(
                    f"{source_ref}:missing_prompt_route_assimilation_field:{field}"
                    for field in missing_prompt_route_assimilation_fields
                )
        if pressure_reduction_contract.get("required"):
            missing_pressure_reduction_fields = [
                field for field in required_pressure_reduction_fields if not row.get(field)
            ]
            if missing_pressure_reduction_fields:
                receipt_failures.extend(
                    f"{source_ref}:missing_pressure_reduction_field:{field}"
                    for field in missing_pressure_reduction_fields
                )
        if operator_accretion_contract.get("required"):
            missing_operator_accretion_fields = [
                field for field in required_operator_accretion_fields if not row.get(field)
            ]
            if missing_operator_accretion_fields:
                receipt_failures.extend(
                    f"{source_ref}:missing_operator_accretion_field:{field}"
                    for field in missing_operator_accretion_fields
                )
        if attention_frame_contract.get("required"):
            missing_attention_frame_fields = [
                field for field in required_attention_frame_fields if not row.get(field)
            ]
            if missing_attention_frame_fields:
                receipt_failures.extend(
                    f"{source_ref}:missing_attention_frame_field:{field}"
                    for field in missing_attention_frame_fields
                )
        if landing_handoff_contract.get("required"):
            missing_landing_handoff_fields = [
                field for field in required_landing_handoff_fields if not row.get(field)
            ]
            if missing_landing_handoff_fields:
                receipt_failures.extend(
                    f"{source_ref}:missing_landing_handoff_field:{field}"
                    for field in missing_landing_handoff_fields
                )
    hook_count = len(integration.get("task_selection_hooks") or [])
    failures = list(missing)
    if not activation.get("trigger_phrases") or not activation.get("opens_when"):
        failures.append("activation_incomplete")
    if not integration.get("navigation") or not integration.get("validation"):
        failures.append("integration_incomplete")
    if hook_count == 0:
        failures.append("task_selection_hooks_missing")
    if operator.get("status") == "active" and not dogfood:
        failures.append("dogfood_receipt_refs_missing")
    if affordance_passport_contract.get("required"):
        required_passport_fields = tuple(
            str(field)
            for field in (
                affordance_passport_contract.get("required_passport_fields")
                if isinstance(affordance_passport_contract.get("required_passport_fields"), list)
                else AFFORDANCE_PASSPORT_FIELDS
            )
            if str(field or "").strip()
        )
        for field in required_passport_fields:
            if not compression_passport.get(field):
                failures.append(f"missing_affordance_passport_field:{field}")
    failures.extend(f"dogfood_receipt_invalid:{ref}" for ref in receipt_failures)
    return {
        "ok": not failures,
        "status": "valid" if not failures else "invalid",
        "missing_or_invalid": failures,
        "dogfood_receipt_count": len([row for row in dogfood if row.get("status") == "available"]),
        "task_selection_hook_count": hook_count,
        "counterevidence_contract_required": bool(counterevidence_contract.get("required")),
        "causal_trial_contract_required": bool(causal_trial_contract.get("required")),
        "composition_contract_required": bool(composition_contract.get("required")),
        "affordance_passport_required": bool(affordance_passport_contract.get("required")),
        "passport_propagation_required": bool(passport_propagation_contract.get("required")),
        "route_lease_required": bool(route_lease_contract.get("required")),
        "prompt_route_assimilation_required": bool(prompt_route_assimilation_contract.get("required")),
        "pressure_reduction_required": bool(pressure_reduction_contract.get("required")),
        "operator_accretion_required": bool(operator_accretion_contract.get("required")),
        "attention_frame_required": bool(attention_frame_contract.get("required")),
        "landing_handoff_required": bool(landing_handoff_contract.get("required")),
        "complete_affordance_passport": _has_complete_affordance_passport(operator),
    }


def _flag_row(operator: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    operator_id = str(operator.get("operator_id") or "")
    validation = _operator_validation(operator, repo_root)
    integration = operator.get("integration") if isinstance(operator.get("integration"), Mapping) else {}
    activation = operator.get("activation") if isinstance(operator.get("activation"), Mapping) else {}
    return {
        "row_id": operator_id,
        "artifact_kind": "cognitive_operator",
        "band": "flag",
        "operator_id": operator_id,
        "slug": operator.get("slug"),
        "title": operator.get("title"),
        "status": operator.get("status"),
        "claim": operator.get("claim"),
        "activation_triggers": list(activation.get("trigger_phrases") or [])[:5],
        "task_selection_hook_count": len(integration.get("task_selection_hooks") or []),
        "dogfood_receipt_count": validation["dogfood_receipt_count"],
        "validation_status": validation["status"],
        "source_ref": f"{REGISTRY_PATH.as_posix()}::operators[{operator_id}]",
        "drilldown_command": (
            "./repo-python kernel.py --option-surface cognitive_operators "
            f"--band card --ids {operator_id}"
        ),
        "evidence_command": "./repo-python tools/meta/factory/validate_cognitive_operator_registry.py --json",
    }


def _route_miss_target_authority_handles(
    dogfood_receipts: list[dict[str, Any]],
) -> list[str]:
    handles: list[str] = []
    for receipt in dogfood_receipts:
        route_miss_evidence = (
            receipt.get("route_miss_evidence")
            if isinstance(receipt.get("route_miss_evidence"), Mapping)
            else {}
        )
        target_planes = route_miss_evidence.get("target_authority_planes")
        if isinstance(target_planes, list):
            handles.extend(str(handle or "").strip() for handle in target_planes)
        elif isinstance(target_planes, str):
            handles.append(target_planes.strip())
    return [handle for handle in handles if handle]


def _authority_plane_next_safe_move(handle: str) -> str | None:
    plane, separator, target_id = handle.partition(":")
    if not separator:
        return None
    surface = AUTHORITY_PLANE_OPTION_SURFACES.get(plane.strip())
    target = target_id.strip()
    if not surface or not target or any(character.isspace() for character in target):
        return None
    return f"./repo-python kernel.py --option-surface {surface} --band card --ids {target}"


def _deduped(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _card_row(operator: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    row = _flag_row(operator, repo_root)
    operator_id = str(operator.get("operator_id") or "")
    dogfood_receipts = _dogfood_receipts(repo_root, operator)
    row["band"] = "card"
    row["activation"] = operator.get("activation")
    row["process"] = operator.get("process")
    row["integration"] = operator.get("integration")
    row["counterevidence_contract"] = operator.get("counterevidence_contract")
    row["causal_trial_contract"] = operator.get("causal_trial_contract")
    row["composition_contract"] = operator.get("composition_contract")
    row["affordance_passport_contract"] = operator.get("affordance_passport_contract")
    row["passport_propagation_contract"] = operator.get("passport_propagation_contract")
    row["route_lease_contract"] = operator.get("route_lease_contract")
    row["prompt_route_assimilation_contract"] = operator.get("prompt_route_assimilation_contract")
    row["pressure_reduction_contract"] = operator.get("pressure_reduction_contract")
    row["operator_accretion_contract"] = operator.get("operator_accretion_contract")
    row["attention_frame_contract"] = operator.get("attention_frame_contract")
    row["landing_handoff_contract"] = operator.get("landing_handoff_contract")
    row["compression_passport"] = operator.get("compression_passport")
    row["validation"] = operator.get("validation")
    row["evidence_refs"] = operator.get("evidence_refs") or []
    row["dogfood_receipts"] = dogfood_receipts
    row["operator_validation"] = _operator_validation(operator, repo_root)
    row["omission_receipt"] = {
        "omitted": [
            "full source bodies named in evidence_refs",
            "full Task Ledger cards",
            "full command outputs from dogfood receipt evidence surfaces",
        ],
        "reason": "The card proves operator activation and evidence; source surfaces remain behind their own routes.",
    }
    target_moves = [
        move
        for handle in _route_miss_target_authority_handles(dogfood_receipts)
        for move in [_authority_plane_next_safe_move(handle)]
        if move
    ]
    row["next_safe_moves"] = _deduped(
        [
            "./repo-python kernel.py --option-surface cognitive_operators --band flag",
            f"./repo-python kernel.py --row cognitive_operators:{operator_id} --band card",
            *target_moves,
            "./repo-python tools/meta/factory/validate_cognitive_operator_registry.py --json",
        ]
    )
    return row


def build_cognitive_operator_rows(repo_root: Path | str, *, band: str) -> list[dict[str, Any]]:
    root = Path(repo_root)
    rows = cognitive_operator_rows(root)
    if band == "card":
        return [_card_row(row, root) for row in rows]
    return [_flag_row(row, root) for row in rows]


def validate_cognitive_operator_registry(repo_root: Path | str) -> dict[str, Any]:
    root = Path(repo_root)
    registry = load_cognitive_operator_registry(root)
    standard = _safe_load_json(root / STANDARD_PATH)
    operators = cognitive_operator_rows(root)
    row_results = []
    for operator in operators:
        row_results.append(
            {
                "operator_id": operator.get("operator_id"),
                "status": operator.get("status"),
                "validation": _operator_validation(operator, root),
            }
        )
    failures = [
        {
            "operator_id": row.get("operator_id"),
            "missing_or_invalid": (row.get("validation") or {}).get("missing_or_invalid") or [],
        }
        for row in row_results
        if not (row.get("validation") or {}).get("ok")
    ]
    if not registry:
        failures.append({"operator_id": None, "missing_or_invalid": ["registry_missing_or_invalid"]})
    if not isinstance(standard, dict):
        failures.append({"operator_id": None, "missing_or_invalid": ["standard_missing_or_invalid"]})
    active_operators = [row for row in operators if row.get("status") == "active"]
    passported_operator_ids = [
        str(row.get("operator_id") or "")
        for row in active_operators
        if _has_complete_affordance_passport(row)
    ]
    missing_passport_operator_ids = [
        str(row.get("operator_id") or "")
        for row in active_operators
        if not _has_complete_affordance_passport(row)
    ]
    return {
        "kind": "cognitive_operator_registry_validation",
        "schema_version": "cognitive_operator_registry_validation_v0",
        "ok": not failures,
        "registry_ref": _relative(root / REGISTRY_PATH, root),
        "standard_ref": _relative(root / STANDARD_PATH, root),
        "operator_count": len(operators),
        "active_operator_count": len(active_operators),
        "affordance_passport_coverage": {
            "active_operator_count": len(active_operators),
            "passported_operator_count": len(passported_operator_ids),
            "missing_passport_operator_count": len(missing_passport_operator_ids),
            "passported_operator_ids": passported_operator_ids,
            "missing_passport_operator_ids": missing_passport_operator_ids,
        },
        "rows": row_results,
        "failures": failures,
    }
