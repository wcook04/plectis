from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from microcosm_core.resource_root import microcosm_root
from microcosm_core.schemas import read_json_strict
from microcosm_core.validators.concept_mechanism_population import (
    validate_concept_mechanism_population,
)


SCHEMA = "microcosm_concept_mechanism_projection_read_model_v0"
VALIDATION_SCHEMA = "microcosm_concept_mechanism_projection_read_model_validation_v0"
DEFAULT_CONSUMER_ID = "frontend_view_compiler_concept_mechanism_read_model"
SOURCE_ROUTE_REF = "atlas/entry_packet.json::concept_mechanism_entry_route"
SOURCE_POPULATION_REF = f"{SOURCE_ROUTE_REF}.population_specimens"
SOURCE_ACTIVATION_REF = f"{SOURCE_ROUTE_REF}.activation_receipts"
PROJECTION_CONSUMERS_REF = f"{SOURCE_ROUTE_REF}.projection_consumers"
ORGAN_REGISTRY_REF = "core/organ_registry.json::implemented_organs"
ORGAN_ATLAS_REF = "core/organ_atlas.json::organs"
ORGAN_ACCEPTANCE_REF = (
    "core/acceptance/first_wave_acceptance.json::accepted_current_authority_organs"
)
PRESSURE_ROW_ID = "concept_mechanism_projection_consumers_preserve_loop_fields"

REQUIRED_PRESERVED_FIELDS = (
    "pressure_id",
    "selected_specimen_id",
    "residual_disposition",
    "concept_binding",
    "mechanism_binding",
    "validator_refs",
    "receipt_refs",
    "omission_receipt",
    "anti_claims",
    "authority_boundary",
)

BANNED_PARALLEL_INDEX_KEYS = {
    "concept_index",
    "concept_index_rows",
    "concept_inventory",
    "independent_concept_inventory",
    "glossary_rows",
    "term_rows",
}

COMPLETED_PRODUCT_DISPOSITIONS = {
    "completed_product_work",
    "implemented_frontend",
    "standalone_index_complete",
    "parallel_index_complete",
}


def _load_json(path: Path) -> dict[str, Any]:
    return read_json_strict(path)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    return [item for item in _as_list(value) if isinstance(item, str) and item.strip()]


def _add_error(
    errors: list[dict[str, str]], *, path: str, code: str, message: str
) -> None:
    errors.append({"path": path, "code": code, "message": message})


def _has_text(row: dict[str, Any], key: str) -> bool:
    return isinstance(row.get(key), str) and bool(row[key].strip())


def _ref_list(*values: Any) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for value in values:
        for ref in _strings(value):
            if ref not in seen:
                seen.add(ref)
                refs.append(ref)
    return refs


def _copy_json(value: Any) -> Any:
    return copy.deepcopy(value)


def _find_consumer(route: dict[str, Any], consumer_id: str) -> dict[str, Any]:
    for row in _as_list(route.get("projection_consumers")):
        if isinstance(row, dict) and row.get("consumer_id") == consumer_id:
            return row
    return {}


def _pressure_row_by_id(pressure_payload: dict[str, Any] | None) -> dict[str, Any]:
    if pressure_payload is None:
        return {}
    for row in _as_list(pressure_payload.get("rows")):
        if isinstance(row, dict) and row.get("standard_id") == PRESSURE_ROW_ID:
            return row
    return {}


def _accepted_organ_rows(root: Path) -> list[dict[str, Any]]:
    registry = _load_json(root / "core/organ_registry.json")
    return [
        row
        for row in _as_list(registry.get("implemented_organs"))
        if isinstance(row, dict)
        and row.get("status") == "accepted_current_authority"
        and row.get("organ_id")
    ]


def _organ_atlas_by_id(root: Path) -> dict[str, dict[str, Any]]:
    atlas = _load_json(root / "core/organ_atlas.json")
    return {
        str(row.get("organ_id")): row
        for row in _as_list(atlas.get("organs"))
        if isinstance(row, dict) and row.get("organ_id")
    }


def _organ_paper_module_ref(root: Path, organ_id: str, atlas_row: dict[str, Any]) -> str:
    declared = str(atlas_row.get("paper_module_ref") or "").strip()
    if declared:
        return declared
    direct = Path("paper_modules") / f"{organ_id}.md"
    if (root / direct).is_file():
        return direct.as_posix()
    return direct.as_posix()


def _first_microcosm_command(value: str) -> str:
    try:
        parts = shlex_split(value)
    except ValueError:
        return ""
    for index, part in enumerate(parts[:-1]):
        if part == "-m" and parts[index + 1] == "microcosm_core.cli":
            tail = parts[index + 2 :]
            return f"microcosm {' '.join(tail)}".strip()
    if parts and parts[0] == "microcosm":
        return " ".join(parts)
    return ""


def shlex_split(value: str) -> list[str]:
    import shlex

    return shlex.split(value)


def build_organ_doctrine_rows(root: str | Path | None = None) -> list[dict[str, Any]]:
    """Project accepted organs into concept/mechanism rows without a second registry."""

    resolved_root = Path(root).resolve() if root is not None else microcosm_root()
    accepted = _accepted_organ_rows(resolved_root)
    atlas_by_id = _organ_atlas_by_id(resolved_root)
    rows: list[dict[str, Any]] = []
    for row in accepted:
        organ_id = str(row.get("organ_id") or "")
        atlas_row = atlas_by_id.get(organ_id, {})
        evidence_class = str(row.get("evidence_class") or atlas_row.get("evidence_class") or "")
        runner = str(row.get("runner") or "")
        validator_command = str(row.get("validator_command") or "")
        first_command = str(atlas_row.get("first_command") or validator_command)
        microcosm_command = _first_microcosm_command(first_command)
        command_ref = microcosm_command or f"microcosm {organ_id.replace('_', '-')}"
        paper_module_ref = _organ_paper_module_ref(resolved_root, organ_id, atlas_row)
        standard_ref = f"standards/std_microcosm_{organ_id}.json"
        rows.append(
            {
                "row_id": f"organ_doctrine_row:{organ_id}",
                "organ_id": organ_id,
                "family": atlas_row.get("family"),
                "evidence_class": evidence_class,
                "concept_binding": {
                    "concept_role": (
                        f"{organ_id} as an accepted {evidence_class} public organ boundary"
                    ),
                    "relationship_shape": (
                        "organ registry row -> atlas card -> paper module -> "
                        "standard -> acceptance -> runtime/CLI surface"
                    ),
                    "payload_shape_ref": f"{ORGAN_ATLAS_REF}[organ_id={organ_id}]",
                    "source_gloss": atlas_row.get("human_gloss")
                    or atlas_row.get("agent_gloss"),
                    "anti_glossary_rule": (
                        "Organ concept rows are generated wiring and authority "
                        "boundaries, not a glossary, maturity score, or label list."
                    ),
                },
                "mechanism_binding": {
                    "mechanism_role": atlas_row.get("wiring_note")
                    or f"{runner} validates the organ's public fixture or bundle.",
                    "concept_pair_ref": f"organ_doctrine_row:{organ_id}.concept_binding",
                    "transformation_shape": (
                        f"{validator_command or runner} turns public inputs into "
                        "bounded receipt evidence under the organ claim ceiling."
                    ),
                    "state_or_proof_effect": (
                        f"Current authority resolves through {row.get('current_authority_receipt')} "
                        f"with claim ceiling {row.get('claim_ceiling')}."
                    ),
                    "anti_feature_prose_rule": (
                        "Organ mechanism rows name the runnable transformation, "
                        "validator, and receipt effect; they are not feature prose "
                        "or product-progress claims."
                    ),
                },
                "surface_refs": {
                    "registry": f"{ORGAN_REGISTRY_REF}[organ_id={organ_id}]",
                    "atlas": f"{ORGAN_ATLAS_REF}[organ_id={organ_id}]",
                    "paper_module": paper_module_ref,
                    "standard": standard_ref,
                    "standards_registry": (
                        "core/standards_registry.json::standards"
                        f"[standard_id=std_microcosm_{organ_id}]"
                    ),
                    "acceptance": f"{ORGAN_ACCEPTANCE_REF}[organ_id={organ_id}]",
                    "runtime": f"microcosm_core.runtime_shell.RUNTIME_STEPS::{organ_id}",
                    "cli": command_ref,
                },
                "validator_refs": [
                    ref
                    for ref in (
                        validator_command,
                        "microcosm organ-surface-contract --card",
                    )
                    if ref
                ],
                "omission_receipt": {
                    "omitted": [
                        "full organ source bodies",
                        "full fixture bodies",
                        "full receipt payloads",
                    ],
                    "reason": (
                        "Per-organ concept/mechanism rows preserve discovery "
                        "handles and authority boundaries; detailed proof stays "
                        "behind each source surface."
                    ),
                    "drilldown": f"{ORGAN_ATLAS_REF}[organ_id={organ_id}]",
                },
                "anti_claims": [
                    "This derived row proves organ discoverability, not release readiness.",
                    "This row does not prove domain correctness, private-root equivalence, or product completeness.",
                ],
                "authority_boundary": (
                    "derived_organ_concept_mechanism_projection_not_source_authority_"
                    "no_release_no_product_completeness_no_private_data_equivalence"
                ),
            }
        )
    return rows


def _projection_row(
    *,
    activation: dict[str, Any],
    specimen: dict[str, Any],
    consumer: dict[str, Any],
) -> dict[str, Any]:
    receipt_id = str(activation.get("receipt_id") or "missing_activation_receipt")
    specimen_id = str(activation.get("selected_specimen_id") or "")
    validator_refs = _ref_list(activation.get("validator_refs"), specimen.get("validator_refs"))
    anti_claims = _ref_list(activation.get("anti_claims"), specimen.get("anti_claims"))
    receipt_refs = _ref_list(
        [activation.get("receipt_ref")],
        [consumer.get("receipt_ref")],
        consumer.get("receipt_refs"),
    )
    return {
        "row_id": f"projection_consumer_row:{receipt_id}",
        "consumer_id": consumer.get("consumer_id") or DEFAULT_CONSUMER_ID,
        "consumer_role": "frontend_or_hud_read_model_projection_row",
        "consumer_disposition": "projection_consumer_guard_source_contract",
        "source_route_ref": SOURCE_ROUTE_REF,
        "source_specimen_ref": f"{SOURCE_POPULATION_REF}[specimen_id={specimen_id}]",
        "source_activation_receipt_ref": f"{SOURCE_ACTIVATION_REF}[receipt_id={receipt_id}]",
        "pressure_id": activation.get("pressure_id"),
        "pressure_label": activation.get("pressure_label"),
        "selected_specimen_id": specimen_id,
        "selected_specimen_role": specimen.get("specimen_role"),
        "residual_disposition": activation.get("residual_disposition"),
        "concept_binding": _copy_json(activation.get("concept_binding")),
        "mechanism_binding": _copy_json(activation.get("mechanism_binding")),
        "source_specimen_bindings": {
            "concept_binding": _copy_json(specimen.get("concept_binding")),
            "mechanism_binding": _copy_json(specimen.get("mechanism_binding")),
        },
        "validator_refs": validator_refs,
        "receipt_refs": receipt_refs,
        "omission_receipt": {
            "omitted": [
                "full Task Ledger event chain",
                "private operator monologue",
                "frontend visual implementation",
            ],
            "reason": "Read model preserves proof-critical fields while omitting high-volume source and UI implementation detail.",
            "drilldown": f"{SOURCE_ACTIVATION_REF}[receipt_id={receipt_id}]",
        },
        "anti_claims": anti_claims,
        "authority_boundary": (
            "derived_projection_not_source_authority_no_parallel_concept_index_"
            "no_release_or_frontend_completion_authority"
        ),
    }


def build_concept_mechanism_projection_read_model(
    *,
    entry_packet: dict[str, Any],
    pressure_payload: dict[str, Any] | None = None,
    root: str | Path | None = None,
    consumer_id: str = DEFAULT_CONSUMER_ID,
    command: str = "concept-mechanism-projection-read-model",
) -> dict[str, Any]:
    route = _as_dict(entry_packet.get("concept_mechanism_entry_route"))
    consumer = _find_consumer(route, consumer_id)
    population_receipt = validate_concept_mechanism_population(
        entry_packet=entry_packet,
        pressure_payload=pressure_payload,
        command=command,
    )
    specimen_by_id = {
        row.get("specimen_id"): row
        for row in _as_list(route.get("population_specimens"))
        if isinstance(row, dict) and row.get("specimen_id")
    }
    rows = []
    for activation in _as_list(route.get("activation_receipts")):
        if not isinstance(activation, dict):
            continue
        specimen = _as_dict(specimen_by_id.get(activation.get("selected_specimen_id")))
        rows.append(_projection_row(activation=activation, specimen=specimen, consumer=consumer))

    organ_doctrine_rows = build_organ_doctrine_rows(root)
    pressure_row = _pressure_row_by_id(pressure_payload)
    payload = {
        "schema": SCHEMA,
        "status": "draft_pending_validation",
        "consumer_id": consumer_id,
        "consumer_kind": "derived_read_model_contract",
        "route_consumer_declared": bool(consumer),
        "consumer_input_refs": _strings(consumer.get("input_refs")),
        "source_route_ref": SOURCE_ROUTE_REF,
        "source_fields": [
            "population_specimens",
            "activation_receipts",
            "organ_registry",
            "organ_atlas",
        ],
        "source_refs": [
            SOURCE_POPULATION_REF,
            SOURCE_ACTIVATION_REF,
            PROJECTION_CONSUMERS_REF,
            ORGAN_REGISTRY_REF,
            ORGAN_ATLAS_REF,
            ORGAN_ACCEPTANCE_REF,
        ],
        "authority_posture": "derived_projection_not_source_authority",
        "parallel_concept_index_authorized": False,
        "workitem_completion_authority": False,
        "source_validation": {
            "status": population_receipt.get("status"),
            "specimen_count": population_receipt.get("specimen_count"),
            "activation_receipt_count": population_receipt.get("activation_receipt_count"),
            "activation_receipt_ids": population_receipt.get("activation_receipt_ids", []),
        },
        "pressure_checked": bool(pressure_row),
        "field_preservation_contract": {
            "required_preserved_fields": list(REQUIRED_PRESERVED_FIELDS),
            "intentionally_omitted_for_readability": [
                "full source event chains",
                "private operator monologue bodies",
                "frontend layout and visual implementation detail",
            ],
            "safe_omission_validator_ref": (
                "python -m microcosm_core.projections.concept_mechanism_read_model"
            ),
        },
        "consumer_receipt": {
            "receipt_id": "frontend_view_compiler_concept_mechanism_read_model_2026_05_27",
            "pressure_id": "cap_quick_concept_index_frontend_view_compiler_sub_d34cd121c080",
            "source_route_ref": SOURCE_ROUTE_REF,
            "source_consumer_ref": (
                f"{PROJECTION_CONSUMERS_REF}[consumer_id={consumer_id}]"
            ),
            "consumed_activation_receipt_ids": population_receipt.get(
                "activation_receipt_ids", []
            ),
            "preserved_fields": list(REQUIRED_PRESERVED_FIELDS),
            "omitted_for_readability": [
                "full Task Ledger event chain",
                "private operator monologue",
                "frontend visual implementation",
            ],
            "validator_refs": [
                "python -m microcosm_core.projections.concept_mechanism_read_model --entry-packet atlas/entry_packet.json --pressure core/public_standard_pressure.json --out /tmp/microcosm-concept-mechanism-read-model",
                "tests/test_concept_mechanism_projection_read_model.py::test_projection_read_model_preserves_proof_critical_fields",
            ],
            "residual_disposition": (
                "consumer_read_model_bound_frontend_implementation_still_bounded"
            ),
            "reentry_condition": (
                "frontend or HUD work may resume only by consuming this read model "
                "or the source concept_mechanism_entry_route; do not author an "
                "independent concept inventory"
            ),
            "authority_boundary": (
                "derived_projection_receipt_not_parallel_concept_index_or_"
                "frontend_completion_authority"
            ),
        },
        "rows": rows,
        "organ_doctrine": {
            "source_refs": [
                ORGAN_REGISTRY_REF,
                ORGAN_ATLAS_REF,
                ORGAN_ACCEPTANCE_REF,
            ],
            "accepted_organ_count": len(organ_doctrine_rows),
            "row_count": len(organ_doctrine_rows),
            "authority": (
                "registry_and_atlas_derived_discoverability_projection_not_"
                "parallel_concept_inventory"
            ),
        },
        "organ_doctrine_rows": organ_doctrine_rows,
        "anti_claim": (
            "This read model is a projection over Microcosm concept/mechanism specimens "
            "and activation receipts. It does not create a concept registry, complete "
            "frontend product work, authorize release, or replace the source route."
        ),
        "command": command,
    }
    validation = validate_concept_mechanism_projection_read_model(
        payload, pressure_payload=pressure_payload
    )
    all_errors = list(population_receipt.get("errors", [])) + list(
        validation.get("errors", [])
    )
    payload["projection_validation"] = validation
    payload["errors"] = all_errors
    payload["status"] = (
        "pass"
        if population_receipt.get("status") == "pass" and validation.get("status") == "pass"
        else "blocked"
    )
    return payload


def _validate_pressure(
    pressure_payload: dict[str, Any] | None, errors: list[dict[str, str]]
) -> bool:
    row = _pressure_row_by_id(pressure_payload)
    if not row:
        _add_error(
            errors,
            path="core/public_standard_pressure.rows",
            code="missing_projection_consumer_pressure_row",
            message="Public pressure must expose the projection-consumer preservation contract.",
        )
        return False
    route_refs = _strings(row.get("route_refs"))
    for required_ref in (
        PROJECTION_CONSUMERS_REF,
        SOURCE_POPULATION_REF,
        SOURCE_ACTIVATION_REF,
        "python -m microcosm_core.projections.concept_mechanism_read_model",
    ):
        if required_ref not in route_refs:
            _add_error(
                errors,
                path=f"core/public_standard_pressure.{PRESSURE_ROW_ID}.route_refs",
                code="projection_consumer_pressure_route_ref_missing",
                message=f"Projection pressure row must include {required_ref}.",
            )
    return True


def validate_concept_mechanism_projection_read_model(
    payload: dict[str, Any],
    *,
    pressure_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    if payload.get("schema") != SCHEMA:
        _add_error(
            errors,
            path="schema",
            code="bad_projection_schema",
            message=f"Projection read model must use {SCHEMA}.",
        )
    for banned_key in BANNED_PARALLEL_INDEX_KEYS:
        if banned_key in payload:
            _add_error(
                errors,
                path=banned_key,
                code="parallel_concept_index_key_present",
                message="Projection read model must not carry an independent concept index key.",
            )
    if payload.get("source_route_ref") != SOURCE_ROUTE_REF:
        _add_error(
            errors,
            path="source_route_ref",
            code="projection_source_route_mismatch",
            message=f"Projection must derive from {SOURCE_ROUTE_REF}.",
        )
    if payload.get("authority_posture") != "derived_projection_not_source_authority":
        _add_error(
            errors,
            path="authority_posture",
            code="projection_authority_posture_missing",
            message="Projection must identify itself as derived, not source authority.",
        )
    if payload.get("parallel_concept_index_authorized") is not False:
        _add_error(
            errors,
            path="parallel_concept_index_authorized",
            code="parallel_index_authorized",
            message="Projection must explicitly refuse parallel concept-index authority.",
        )
    if payload.get("workitem_completion_authority") is not False:
        _add_error(
            errors,
            path="workitem_completion_authority",
            code="projection_claims_product_completion",
            message="Projection consumer guard is not completed frontend product work.",
        )
    if payload.get("route_consumer_declared") is not True:
        _add_error(
            errors,
            path="route_consumer_declared",
            code="projection_consumer_not_declared_by_route",
            message="Projection must be declared by concept_mechanism_entry_route.projection_consumers.",
        )

    source_fields = set(_strings(payload.get("source_fields")))
    if not {"population_specimens", "activation_receipts"} <= source_fields:
        _add_error(
            errors,
            path="source_fields",
            code="projection_missing_source_fields",
            message="Projection must read both population_specimens and activation_receipts.",
        )
    source_refs = set(_strings(payload.get("source_refs")))
    if PROJECTION_CONSUMERS_REF not in source_refs:
        _add_error(
            errors,
            path="source_refs",
            code="projection_missing_consumer_source_ref",
            message="Projection source refs must include the route's projection_consumers contract.",
        )
    for required_ref in (ORGAN_REGISTRY_REF, ORGAN_ATLAS_REF, ORGAN_ACCEPTANCE_REF):
        if required_ref not in source_refs:
            _add_error(
                errors,
                path="source_refs",
                code="projection_missing_organ_doctrine_source_ref",
                message=f"Projection source refs must include {required_ref}.",
            )
    input_refs = set(_strings(payload.get("consumer_input_refs")))
    if not {SOURCE_POPULATION_REF, SOURCE_ACTIVATION_REF} <= input_refs:
        _add_error(
            errors,
            path="consumer_input_refs",
            code="projection_consumer_input_refs_incomplete",
            message="Declared projection consumer must read both population and activation refs.",
        )

    contract = _as_dict(payload.get("field_preservation_contract"))
    required_contract_fields = set(_strings(contract.get("required_preserved_fields")))
    if not set(REQUIRED_PRESERVED_FIELDS) <= required_contract_fields:
        _add_error(
            errors,
            path="field_preservation_contract.required_preserved_fields",
            code="projection_preservation_contract_incomplete",
            message="Projection contract must list every proof-critical field.",
        )

    receipt = _as_dict(payload.get("consumer_receipt"))
    if not _has_text(receipt, "receipt_id"):
        _add_error(
            errors,
            path="consumer_receipt.receipt_id",
            code="missing_consumer_receipt",
            message="Projection must attach a consumer receipt.",
        )
    if receipt.get("residual_disposition") in COMPLETED_PRODUCT_DISPOSITIONS:
        _add_error(
            errors,
            path="consumer_receipt.residual_disposition",
            code="projection_receipt_claims_completed_product",
            message="Consumer receipt must not turn the guard into completed product work.",
        )
    if "independent concept inventory" not in str(receipt.get("reentry_condition", "")):
        _add_error(
            errors,
            path="consumer_receipt.reentry_condition",
            code="projection_reentry_missing_parallel_index_guard",
            message="Consumer receipt must forbid independent concept inventory re-entry.",
        )

    rows = _as_list(payload.get("rows"))
    if not rows:
        _add_error(
            errors,
            path="rows",
            code="missing_projection_rows",
            message="Projection must carry at least one activation-derived consumer row.",
        )
    for index, row_value in enumerate(rows):
        row = _as_dict(row_value)
        row_path = f"rows[{row.get('row_id') or index}]"
        for key in REQUIRED_PRESERVED_FIELDS:
            if key not in row or row.get(key) in (None, "", [], {}):
                _add_error(
                    errors,
                    path=f"{row_path}.{key}",
                    code="projection_row_missing_preserved_field",
                    message=f"Projection row must preserve proof-critical field {key}.",
                )
        if row.get("consumer_disposition") in COMPLETED_PRODUCT_DISPOSITIONS:
            _add_error(
                errors,
                path=f"{row_path}.consumer_disposition",
                code="projection_row_claims_completed_product",
                message="Projection row must not claim completed frontend product work.",
            )
        if row.get("source_route_ref") != SOURCE_ROUTE_REF:
            _add_error(
                errors,
                path=f"{row_path}.source_route_ref",
                code="projection_row_source_route_mismatch",
                message="Projection row must point back to the source route.",
            )
        if not any("projection_consumers" in ref for ref in _strings(row.get("receipt_refs"))):
            _add_error(
                errors,
                path=f"{row_path}.receipt_refs",
                code="projection_row_missing_consumer_receipt_ref",
                message="Projection row must preserve the route projection-consumer receipt ref.",
            )
        if "parallel concept index" not in str(row.get("authority_boundary", "")).replace(
            "_", " "
        ):
            _add_error(
                errors,
                path=f"{row_path}.authority_boundary",
                code="projection_row_boundary_missing_parallel_index_guard",
                message="Projection row authority boundary must reject parallel concept index authority.",
            )
        concept_binding = _as_dict(row.get("concept_binding"))
        mechanism_binding = _as_dict(row.get("mechanism_binding"))
        if "glossary" not in str(concept_binding.get("anti_glossary_rule", "")).lower():
            _add_error(
                errors,
                path=f"{row_path}.concept_binding.anti_glossary_rule",
                code="projection_concept_binding_not_anti_glossary",
                message="Projection concept binding must preserve the anti-glossary rule.",
            )
        if "feature prose" not in str(
            mechanism_binding.get("anti_feature_prose_rule", "")
        ).lower():
            _add_error(
                errors,
                path=f"{row_path}.mechanism_binding.anti_feature_prose_rule",
                code="projection_mechanism_binding_not_anti_feature_prose",
                message="Projection mechanism binding must preserve the anti-feature-prose rule.",
            )

    organ_doctrine = _as_dict(payload.get("organ_doctrine"))
    organ_doctrine_rows = _as_list(payload.get("organ_doctrine_rows"))
    accepted_organ_count = organ_doctrine.get("accepted_organ_count")
    if not isinstance(accepted_organ_count, int) or accepted_organ_count <= 0:
        _add_error(
            errors,
            path="organ_doctrine.accepted_organ_count",
            code="organ_doctrine_missing_accepted_count",
            message="Organ doctrine projection must record a positive accepted organ count.",
        )
    if len(organ_doctrine_rows) != accepted_organ_count:
        _add_error(
            errors,
            path="organ_doctrine_rows",
            code="organ_doctrine_row_count_mismatch",
            message="Organ doctrine row count must equal accepted organ count.",
        )
    seen_organ_ids: set[str] = set()
    for index, row_value in enumerate(organ_doctrine_rows):
        row = _as_dict(row_value)
        organ_id = str(row.get("organ_id") or "")
        row_path = f"organ_doctrine_rows[{organ_id or index}]"
        if not organ_id:
            _add_error(
                errors,
                path=f"{row_path}.organ_id",
                code="organ_doctrine_row_missing_organ_id",
                message="Organ doctrine rows must identify the accepted organ.",
            )
        if organ_id in seen_organ_ids:
            _add_error(
                errors,
                path=f"{row_path}.organ_id",
                code="organ_doctrine_row_duplicate_organ_id",
                message="Organ doctrine rows must be unique by organ_id.",
            )
        seen_organ_ids.add(organ_id)
        for key in ("concept_binding", "mechanism_binding", "surface_refs"):
            if not _as_dict(row.get(key)):
                _add_error(
                    errors,
                    path=f"{row_path}.{key}",
                    code="organ_doctrine_row_missing_projection_field",
                    message=f"Organ doctrine row must carry {key}.",
                )
        concept_binding = _as_dict(row.get("concept_binding"))
        mechanism_binding = _as_dict(row.get("mechanism_binding"))
        if "glossary" not in str(concept_binding.get("anti_glossary_rule", "")).lower():
            _add_error(
                errors,
                path=f"{row_path}.concept_binding.anti_glossary_rule",
                code="organ_doctrine_concept_binding_not_anti_glossary",
                message="Organ concept binding must reject glossary/list authority.",
            )
        if "feature prose" not in str(
            mechanism_binding.get("anti_feature_prose_rule", "")
        ).lower():
            _add_error(
                errors,
                path=f"{row_path}.mechanism_binding.anti_feature_prose_rule",
                code="organ_doctrine_mechanism_binding_not_anti_feature_prose",
                message="Organ mechanism binding must reject feature prose authority.",
            )
        surface_refs = _as_dict(row.get("surface_refs"))
        for key in (
            "registry",
            "atlas",
            "paper_module",
            "standard",
            "standards_registry",
            "acceptance",
            "runtime",
            "cli",
        ):
            if not surface_refs.get(key):
                _add_error(
                    errors,
                    path=f"{row_path}.surface_refs.{key}",
                    code="organ_doctrine_row_missing_surface_ref",
                    message=f"Organ doctrine row must expose {key} as a discoverability surface.",
                )
        if not _strings(row.get("validator_refs")):
            _add_error(
                errors,
                path=f"{row_path}.validator_refs",
                code="organ_doctrine_row_missing_validator_refs",
                message="Organ doctrine row must preserve validator refs.",
            )
        if not _strings(row.get("anti_claims")):
            _add_error(
                errors,
                path=f"{row_path}.anti_claims",
                code="organ_doctrine_row_missing_anti_claims",
                message="Organ doctrine row must carry anti-claims.",
            )

    pressure_checked = _validate_pressure(pressure_payload, errors)
    return {
        "schema": VALIDATION_SCHEMA,
        "status": "pass" if not errors else "blocked",
        "consumer_id": payload.get("consumer_id"),
        "row_count": len(rows),
        "pressure_checked": pressure_checked,
        "parallel_concept_index_authorized": False,
        "errors": errors,
    }


def compile_paths(
    *,
    entry_packet_path: Path,
    pressure_path: Path | None,
    out: Path | None,
    consumer_id: str,
    command: str,
) -> dict[str, Any]:
    pressure_payload = _load_json(pressure_path) if pressure_path else None
    root = entry_packet_path.resolve(strict=False).parent.parent
    payload = build_concept_mechanism_projection_read_model(
        entry_packet=_load_json(entry_packet_path),
        pressure_payload=pressure_payload,
        root=root,
        consumer_id=consumer_id,
        command=command,
    )
    if out:
        out.mkdir(parents=True, exist_ok=True)
        (out / "concept_mechanism_projection_read_model.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (out / "concept_mechanism_projection_read_model_receipt.json").write_text(
            json.dumps(payload["consumer_receipt"], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile a Microcosm concept/mechanism projection read model."
    )
    parser.add_argument("--entry-packet", required=True, type=Path)
    parser.add_argument("--pressure", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--consumer-id", default=DEFAULT_CONSUMER_ID)
    args = parser.parse_args(argv)
    command = (
        "python -m microcosm_core.projections.concept_mechanism_read_model "
        f"--entry-packet {args.entry_packet}"
        + (f" --pressure {args.pressure}" if args.pressure else "")
        + (f" --out {args.out}" if args.out else "")
        + (f" --consumer-id {args.consumer_id}" if args.consumer_id != DEFAULT_CONSUMER_ID else "")
    )
    payload = compile_paths(
        entry_packet_path=args.entry_packet,
        pressure_path=args.pressure,
        out=args.out,
        consumer_id=args.consumer_id,
        command=command,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
