from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from microcosm_core.schemas import read_json_strict


ALLOWED_RESIDUAL_DISPOSITIONS = {
    "already_valid_projection_consumer",
    "captured_for_later_owner",
    "closed_as_stale_parallel_index",
    "redirected_to_projection_consumer",
}

DEFAULT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ENTRY_PACKET = DEFAULT_ROOT / "atlas/entry_packet.json"
DEFAULT_PRESSURE = DEFAULT_ROOT / "core/public_standard_pressure.json"

RESOLVED_TARGET_STATUSES = {
    "declared_receipt_id",
    "declared_receipt_ref",
    "resolved_code_locus",
    "resolved_json_instance",
    "resolved_receipt_ref",
    "resolved_registry_or_atlas_target",
}

PLANNED_TARGET_PREFIXES = (
    "planned_",
)

MECHANISM_POPULATION_BINDING_REQUIRED = (
    "mechanism_role",
    "concept_pair_ref",
    "source_refs",
    "transformation_shape",
    "state_or_proof_effect",
    "omission_receipt",
    "anti_claims",
    "validator_refs",
)

CONCEPT_CLUSTER_FLAG_REQUIRED = (
    "schema_version",
    "cluster_id",
    "kind",
    "concept_id",
    "claim",
    "source_ref",
    "specimen_id",
    "mechanism_count",
    "principle_count",
    "axiom_count",
    "drilldown",
    "authority_boundary",
)


def _load_json(path: Path) -> dict[str, Any]:
    return read_json_strict(path)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _add_error(
    errors: list[dict[str, str]], *, path: str, code: str, message: str
) -> None:
    errors.append({"path": path, "code": code, "message": message})


def _has_text(row: dict[str, Any], key: str) -> bool:
    return isinstance(row.get(key), str) and bool(row[key].strip())


def _has_ref_list(row: dict[str, Any], key: str) -> bool:
    refs = row.get(key)
    return isinstance(refs, list) and any(isinstance(ref, str) and ref.strip() for ref in refs)


def _is_planned_target_status(status: Any) -> bool:
    return isinstance(status, str) and status.startswith(PLANNED_TARGET_PREFIXES)


def _validator_ref_is_inspectable(ref: str) -> bool:
    prefixes = ("microcosm ", "python ", "./", "tests/")
    return ref.startswith(prefixes) or "::test_" in ref or "/tests/" in ref


def _required_fields(standard: dict[str, Any]) -> list[str]:
    return [field for field in _as_list(standard.get("required_fields")) if isinstance(field, str)]


def _receipt_ref_path(root: Path, ref: str) -> Path | None:
    if not ref.startswith("receipts/"):
        return None
    return root / ref


def _record_receipt_index(root: Path, receipt_refs: list[str]) -> dict[str, set[str]]:
    indexed: dict[str, set[str]] = {}
    for ref in receipt_refs:
        path = _receipt_ref_path(root, ref)
        if path is None or not path.is_file():
            continue
        try:
            payload = _load_json(path)
        except Exception:
            continue
        ids: set[str] = set()
        for row in _as_list(payload.get("record_receipts")):
            if isinstance(row, dict) and isinstance(row.get("record_id"), str):
                ids.add(row["record_id"])
        if ids:
            indexed[ref] = ids
    return indexed


def _receipt_refs_cover_record(
    *,
    root: Path,
    record_id: str,
    receipt_refs: list[str],
    receipt_index: dict[str, set[str]],
) -> bool:
    for ref in receipt_refs:
        if ref.startswith("receipt."):
            return True
        path = _receipt_ref_path(root, ref)
        if path is not None and path.is_file() and (
            not receipt_index.get(ref) or record_id in receipt_index.get(ref, set())
        ):
            return True
    return False


def _validate_record_edges(
    *,
    record: dict[str, Any],
    path: Path,
    errors: list[dict[str, str]],
) -> None:
    for index, edge in enumerate(_as_list(_as_dict(record.get("relationships")).get("edges"))):
        edge_path = f"{path.as_posix()}.relationships.edges[{index}]"
        if not isinstance(edge, dict):
            _add_error(
                errors,
                path=edge_path,
                code="edge_not_object",
                message="Relationship edge must be an object.",
            )
            continue
        justification = _as_dict(edge.get("justification"))
        if not _has_text(justification, "source_ref") or not _has_text(
            justification, "summary"
        ):
            _add_error(
                errors,
                path=f"{edge_path}.justification",
                code="edge_missing_justification",
                message="Forward source edge must carry justification.source_ref and justification.summary.",
            )
        status = edge.get("target_status")
        if status not in RESOLVED_TARGET_STATUSES and not _is_planned_target_status(status):
            _add_error(
                errors,
                path=f"{edge_path}.target_status",
                code="edge_target_unresolved_not_planned",
                message="Unresolved concept/mechanism-owned edge targets must resolve or be marked planned.",
            )


def _validate_mechanism_population_binding(
    *,
    record: dict[str, Any],
    path: Path,
    errors: list[dict[str, str]],
) -> None:
    binding = _as_dict(_as_dict(record.get("mechanism_payload")).get("population_binding"))
    for key in MECHANISM_POPULATION_BINDING_REQUIRED:
        if key in {"source_refs", "anti_claims", "validator_refs"}:
            if not _has_ref_list(binding, key):
                _add_error(
                    errors,
                    path=f"{path.as_posix()}.mechanism_payload.population_binding.{key}",
                    code="missing_mechanism_population_binding_ref_list",
                    message=f"Mechanism population binding must carry non-empty {key}.",
                )
        elif key == "omission_receipt":
            if not _has_text(_as_dict(binding.get(key)), "drilldown"):
                _add_error(
                    errors,
                    path=f"{path.as_posix()}.mechanism_payload.population_binding.omission_receipt",
                    code="missing_mechanism_population_binding_omission",
                    message="Mechanism population binding must carry omission_receipt.drilldown.",
                )
        elif not _has_text(binding, key):
            _add_error(
                errors,
                path=f"{path.as_posix()}.mechanism_payload.population_binding.{key}",
                code="missing_mechanism_population_binding_field",
                message="Mechanism population binding must name role, concept pair, transformation shape, and state/proof effect.",
            )


def _validate_concept_cluster_flag(
    *,
    record: dict[str, Any],
    path: Path,
    errors: list[dict[str, str]],
) -> bool:
    flag = _as_dict(record.get("cluster_flag"))
    flag_path = f"{path.as_posix()}.cluster_flag"
    if not flag:
        _add_error(
            errors,
            path=flag_path,
            code="concept_cluster_flag_missing",
            message="Concept records must expose a source-backed cluster_flag row.",
        )
        return False
    for key in CONCEPT_CLUSTER_FLAG_REQUIRED:
        if flag.get(key) in (None, "", []):
            _add_error(
                errors,
                path=f"{flag_path}.{key}",
                code="concept_cluster_flag_missing_field",
                message=f"Concept cluster_flag is missing required field {key}.",
            )
    relationships = _as_dict(record.get("relationships"))
    count_expectations = {
        "mechanism_count": len(_as_list(relationships.get("mechanism_refs"))),
        "principle_count": len(_as_list(relationships.get("principle_refs"))),
        "axiom_count": len(_as_list(relationships.get("axiom_refs"))),
    }
    if flag.get("kind") != "concept":
        _add_error(
            errors,
            path=f"{flag_path}.kind",
            code="concept_cluster_flag_kind_mismatch",
            message="Concept cluster_flag.kind must be concept.",
        )
    if flag.get("concept_id") != record.get("id"):
        _add_error(
            errors,
            path=f"{flag_path}.concept_id",
            code="concept_cluster_flag_id_mismatch",
            message="Concept cluster_flag.concept_id must match the record id.",
        )
    if flag.get("specimen_id") != relationships.get("specimen_id"):
        _add_error(
            errors,
            path=f"{flag_path}.specimen_id",
            code="concept_cluster_flag_specimen_mismatch",
            message="Concept cluster_flag.specimen_id must match relationships.specimen_id.",
        )
    for key, expected in count_expectations.items():
        if flag.get(key) != expected:
            _add_error(
                errors,
                path=f"{flag_path}.{key}",
                code="concept_cluster_flag_count_mismatch",
                message=f"Concept cluster_flag.{key} must match relationships refs.",
            )
    if not str(flag.get("drilldown", "")).startswith("concepts/"):
        _add_error(
            errors,
            path=f"{flag_path}.drilldown",
            code="concept_cluster_flag_drilldown_not_local",
            message="Concept cluster_flag.drilldown must point at the local concept record.",
        )
    if "not_source_authority" not in str(flag.get("authority_boundary", "")):
        _add_error(
            errors,
            path=f"{flag_path}.authority_boundary",
            code="concept_cluster_flag_authority_boundary_missing",
            message="Concept cluster_flag must state that it is not source authority.",
        )
    return True


def _validate_record_corpus(root: Path, errors: list[dict[str, str]]) -> dict[str, Any]:
    concept_standard = _load_json(root / "standards/std_microcosm_concept.json")
    mechanism_standard = _load_json(root / "standards/std_microcosm_mechanism.json")
    concept_required = _required_fields(concept_standard)
    mechanism_required = _required_fields(mechanism_standard)
    concept_paths = sorted((root / "concepts").glob("*.json"))
    mechanism_paths = sorted((root / "mechanisms").glob("*.json"))
    concepts = {path: _load_json(path) for path in concept_paths}
    mechanisms = {path: _load_json(path) for path in mechanism_paths}
    concept_ids = {row.get("id") for row in concepts.values()}
    mechanism_ids = {row.get("id") for row in mechanisms.values()}
    receipt_refs = sorted(
        {
            ref
            for row in [*concepts.values(), *mechanisms.values()]
            for ref in _as_list(row.get("receipt_refs"))
            if isinstance(ref, str) and ref.strip()
        }
    )
    receipt_index = _record_receipt_index(root, receipt_refs)

    draft_or_seed_count = 0
    empty_receipt_count = 0
    planned_target_count = 0
    unresolved_target_count = 0
    cluster_flag_count = 0

    for path, record in concepts.items():
        record_id = str(record.get("id") or path.stem)
        status = str(record.get("status") or "")
        if status in {"draft", "seed"}:
            draft_or_seed_count += 1
            _add_error(
                errors,
                path=f"{path.as_posix()}.status",
                code="concept_not_active",
                message="Concept records must be active, not draft or seed.",
            )
        for key in concept_required:
            if record.get(key) in (None, "", []):
                _add_error(
                    errors,
                    path=f"{path.as_posix()}.{key}",
                    code="concept_missing_required_field",
                    message=f"Concept record is missing required field {key}.",
                )
        refs = [ref for ref in _as_list(record.get("receipt_refs")) if isinstance(ref, str)]
        if not refs:
            empty_receipt_count += 1
        if not _receipt_refs_cover_record(
            root=root, record_id=record_id, receipt_refs=refs, receipt_index=receipt_index
        ):
            _add_error(
                errors,
                path=f"{path.as_posix()}.receipt_refs",
                code="concept_receipt_not_bound",
                message="Concept record must point to a declared or local receipt that covers this record.",
            )
        if not _has_ref_list(record, "validator_refs"):
            _add_error(
                errors,
                path=f"{path.as_posix()}.validator_refs",
                code="concept_validator_refs_missing",
                message="Concept record must carry validator_refs.",
            )
        if _validate_concept_cluster_flag(record=record, path=path, errors=errors):
            cluster_flag_count += 1
        _validate_record_edges(record=record, path=path, errors=errors)
        for mechanism_id in _as_list(_as_dict(record.get("relationships")).get("mechanism_refs")):
            if mechanism_id not in mechanism_ids:
                _add_error(
                    errors,
                    path=f"{path.as_posix()}.relationships.mechanism_refs",
                    code="concept_mechanism_ref_unresolved",
                    message=f"Concept mechanism ref {mechanism_id} must resolve to a mechanism record.",
                )

    concept_mechanism_refs = {
        str(record.get("id")): set(_as_list(_as_dict(record.get("relationships")).get("mechanism_refs")))
        for record in concepts.values()
    }
    for path, record in mechanisms.items():
        record_id = str(record.get("id") or path.stem)
        status = str(record.get("status") or "")
        if status in {"draft", "seed"}:
            draft_or_seed_count += 1
            _add_error(
                errors,
                path=f"{path.as_posix()}.status",
                code="mechanism_not_active",
                message="Mechanism records must be active, not draft or seed.",
            )
        for key in mechanism_required:
            if record.get(key) in (None, "", []):
                _add_error(
                    errors,
                    path=f"{path.as_posix()}.{key}",
                    code="mechanism_missing_required_field",
                    message=f"Mechanism record is missing required field {key}.",
                )
        refs = [ref for ref in _as_list(record.get("receipt_refs")) if isinstance(ref, str)]
        if not refs:
            empty_receipt_count += 1
        if not _receipt_refs_cover_record(
            root=root, record_id=record_id, receipt_refs=refs, receipt_index=receipt_index
        ):
            _add_error(
                errors,
                path=f"{path.as_posix()}.receipt_refs",
                code="mechanism_receipt_not_bound",
                message="Mechanism record must point to a declared or local receipt that covers this record.",
            )
        if not _has_ref_list(record, "validator_refs"):
            _add_error(
                errors,
                path=f"{path.as_posix()}.validator_refs",
                code="mechanism_validator_refs_missing",
                message="Mechanism record must carry validator_refs.",
            )
        _validate_mechanism_population_binding(record=record, path=path, errors=errors)
        _validate_record_edges(record=record, path=path, errors=errors)
        for edge in _as_list(_as_dict(record.get("relationships")).get("edges")):
            if isinstance(edge, dict):
                status = edge.get("target_status")
                if _is_planned_target_status(status):
                    planned_target_count += 1
                elif status not in RESOLVED_TARGET_STATUSES:
                    unresolved_target_count += 1
        for concept_id in _as_list(_as_dict(record.get("relationships")).get("concept_refs")):
            if concept_id not in concept_ids:
                _add_error(
                    errors,
                    path=f"{path.as_posix()}.relationships.concept_refs",
                    code="mechanism_concept_ref_unresolved",
                    message=f"Mechanism concept ref {concept_id} must resolve to a concept record.",
                )
            elif record_id not in concept_mechanism_refs.get(concept_id, set()):
                _add_error(
                    errors,
                    path=f"{path.as_posix()}.relationships.concept_refs",
                    code="concept_missing_mechanism_backref",
                    message=f"Concept {concept_id} must list mechanism {record_id} back.",
                )

    return {
        "concept_count": len(concept_paths),
        "mechanism_count": len(mechanism_paths),
        "draft_or_seed_status_count": draft_or_seed_count,
        "empty_receipt_ref_count": empty_receipt_count,
        "planned_target_count": planned_target_count,
        "unresolved_target_count": unresolved_target_count,
        "receipt_ref_count": len(receipt_refs),
        "cluster_flag_count": cluster_flag_count,
    }


def _validate_concept_binding(
    *,
    binding: dict[str, Any],
    path: str,
    errors: list[dict[str, str]],
    require_pair_ref: bool,
) -> None:
    required = ["concept_role", "relationship_shape", "payload_shape_ref", "anti_glossary_rule"]
    if require_pair_ref:
        required.append("mechanism_pair_ref")
    for key in required:
        if not _has_text(binding, key):
            _add_error(
                errors,
                path=f"{path}.{key}",
                code="missing_concept_binding_field",
                message="Concept binding must carry role, relation, payload, anti-glossary rule, and mechanism pair when it is an activation receipt.",
            )
    if "glossary" not in str(binding.get("anti_glossary_rule", "")).lower():
        _add_error(
            errors,
            path=f"{path}.anti_glossary_rule",
            code="concept_binding_not_anti_glossary",
            message="Concept binding must explicitly reject glossary-only population.",
        )


def _validate_mechanism_binding(
    *,
    binding: dict[str, Any],
    expected_pair_ref: str,
    path: str,
    errors: list[dict[str, str]],
) -> None:
    required = [
        "mechanism_role",
        "concept_pair_ref",
        "transformation_shape",
        "state_or_proof_effect",
        "anti_feature_prose_rule",
    ]
    for key in required:
        if not _has_text(binding, key):
            _add_error(
                errors,
                path=f"{path}.{key}",
                code="missing_mechanism_binding_field",
                message="Mechanism binding must carry role, concept pair, transformation, proof effect, and anti-feature-prose rule.",
            )
    if binding.get("concept_pair_ref") != expected_pair_ref:
        _add_error(
            errors,
            path=f"{path}.concept_pair_ref",
            code="mechanism_pair_ref_mismatch",
            message=f"Mechanism binding must point back to {expected_pair_ref}.",
        )
    if "feature prose" not in str(binding.get("anti_feature_prose_rule", "")).lower():
        _add_error(
            errors,
            path=f"{path}.anti_feature_prose_rule",
            code="mechanism_binding_not_anti_feature_prose",
            message="Mechanism binding must explicitly reject feature-prose population.",
        )


def _validate_specimens(route: dict[str, Any], errors: list[dict[str, str]]) -> set[str]:
    specimens = _as_list(route.get("population_specimens"))
    specimen_ids: set[str] = set()
    if not specimens:
        _add_error(
            errors,
            path="concept_mechanism_entry_route.population_specimens",
            code="missing_population_specimens",
            message="Population route must carry at least one specimen.",
        )
        return specimen_ids

    for index, specimen_value in enumerate(specimens):
        specimen = _as_dict(specimen_value)
        specimen_id = str(specimen.get("specimen_id") or f"index_{index}")
        specimen_path = f"population_specimens[{specimen_id}]"
        if not _has_text(specimen, "specimen_id"):
            _add_error(
                errors,
                path=f"{specimen_path}.specimen_id",
                code="missing_specimen_id",
                message="Specimen must carry a stable specimen_id.",
            )
        else:
            specimen_ids.add(specimen["specimen_id"])

        concept_binding = _as_dict(specimen.get("concept_binding"))
        mechanism_binding = _as_dict(specimen.get("mechanism_binding"))
        _validate_concept_binding(
            binding=concept_binding,
            path=f"{specimen_path}.concept_binding",
            errors=errors,
            require_pair_ref=False,
        )
        _validate_mechanism_binding(
            binding=mechanism_binding,
            expected_pair_ref=f"{specimen_id}.concept_binding",
            path=f"{specimen_path}.mechanism_binding",
            errors=errors,
        )
        if concept_binding.get("concept_role") == mechanism_binding.get("mechanism_role"):
            _add_error(
                errors,
                path=specimen_path,
                code="concept_mechanism_roles_collapsed",
                message="Concept and mechanism roles must remain distinct.",
            )
        for key in ("source_refs", "validator_refs", "anti_claims"):
            if not _has_ref_list(specimen, key):
                _add_error(
                    errors,
                    path=f"{specimen_path}.{key}",
                    code="missing_specimen_ref_list",
                    message=f"Specimen must carry non-empty {key}.",
                )
        if not any(
            _validator_ref_is_inspectable(ref)
            for ref in _as_list(specimen.get("validator_refs"))
            if isinstance(ref, str)
        ):
            _add_error(
                errors,
                path=f"{specimen_path}.validator_refs",
                code="specimen_validator_not_inspectable",
                message="Specimen needs at least one runnable or inspectable validator ref.",
            )
        if not _has_text(_as_dict(specimen.get("omission_receipt")), "drilldown"):
            _add_error(
                errors,
                path=f"{specimen_path}.omission_receipt",
                code="missing_omission_drilldown",
                message="Specimen omission receipt must point to a drilldown.",
            )
    return specimen_ids


def _validate_activation_receipts(
    route: dict[str, Any], specimen_ids: set[str], errors: list[dict[str, str]]
) -> list[str]:
    receipts = _as_list(route.get("activation_receipts"))
    receipt_ids: list[str] = []
    if not receipts:
        _add_error(
            errors,
            path="concept_mechanism_entry_route.activation_receipts",
            code="missing_activation_receipts",
            message="Activated population route must record at least one pressure receipt.",
        )
        return receipt_ids

    for index, receipt_value in enumerate(receipts):
        receipt = _as_dict(receipt_value)
        receipt_id = str(receipt.get("receipt_id") or f"index_{index}")
        receipt_path = f"activation_receipts[{receipt_id}]"
        if not _has_text(receipt, "receipt_id"):
            _add_error(
                errors,
                path=f"{receipt_path}.receipt_id",
                code="missing_activation_receipt_id",
                message="Activation receipt must carry a stable receipt_id.",
            )
        else:
            receipt_ids.append(receipt["receipt_id"])
        for key in (
            "pressure_id",
            "classification",
            "selected_specimen_id",
            "source_ref",
            "residual_disposition",
            "reentry_condition",
            "receipt_ref",
            "authority_boundary",
        ):
            if not _has_text(receipt, key):
                _add_error(
                    errors,
                    path=f"{receipt_path}.{key}",
                    code="missing_activation_receipt_field",
                    message="Activation receipt must bind pressure, specimen, source, disposition, reentry, receipt, and authority fields.",
                )
        if receipt.get("selected_specimen_id") not in specimen_ids:
            _add_error(
                errors,
                path=f"{receipt_path}.selected_specimen_id",
                code="activation_receipt_unknown_specimen",
                message="Activation receipt must choose an existing population specimen.",
            )
        if receipt.get("residual_disposition") not in ALLOWED_RESIDUAL_DISPOSITIONS:
            _add_error(
                errors,
                path=f"{receipt_path}.residual_disposition",
                code="activation_receipt_bad_disposition",
                message="Residual disposition must be an allowed projection/retirement/capture state, never a new parallel index.",
            )
        boundary_text = str(receipt.get("authority_boundary", "")).lower().replace("_", " ")
        if "parallel concept index" not in boundary_text and (
            "concept_index" in str(receipt.get("pressure_id", "")).lower()
            or "concept index" in str(receipt.get("pressure_label", "")).lower()
        ):
            _add_error(
                errors,
                path=f"{receipt_path}.authority_boundary",
                code="concept_index_pressure_boundary_missing",
                message="Concept-index pressure receipts must explicitly reject parallel concept-index authority.",
            )
        concept_binding = _as_dict(receipt.get("concept_binding"))
        mechanism_binding = _as_dict(receipt.get("mechanism_binding"))
        _validate_concept_binding(
            binding=concept_binding,
            path=f"{receipt_path}.concept_binding",
            errors=errors,
            require_pair_ref=True,
        )
        _validate_mechanism_binding(
            binding=mechanism_binding,
            expected_pair_ref=f"{receipt_id}.concept_binding",
            path=f"{receipt_path}.mechanism_binding",
            errors=errors,
        )
        if concept_binding.get("mechanism_pair_ref") != f"{receipt_id}.mechanism_binding":
            _add_error(
                errors,
                path=f"{receipt_path}.concept_binding.mechanism_pair_ref",
                code="concept_pair_ref_mismatch",
                message="Activation concept binding must point to the same receipt's mechanism binding.",
            )
        for key in ("validator_refs", "anti_claims"):
            if not _has_ref_list(receipt, key):
                _add_error(
                    errors,
                    path=f"{receipt_path}.{key}",
                    code="missing_activation_ref_list",
                    message=f"Activation receipt must carry non-empty {key}.",
                )
        if not any(
            _validator_ref_is_inspectable(ref)
            for ref in _as_list(receipt.get("validator_refs"))
            if isinstance(ref, str)
        ):
            _add_error(
                errors,
                path=f"{receipt_path}.validator_refs",
                code="activation_validator_not_inspectable",
                message="Activation receipt needs at least one runnable or inspectable validator ref.",
            )
        if not _has_text(_as_dict(receipt.get("omission_receipt")), "drilldown"):
            _add_error(
                errors,
                path=f"{receipt_path}.omission_receipt",
                code="missing_activation_omission_drilldown",
                message="Activation receipt omission receipt must point to a drilldown.",
            )
    return receipt_ids


def _validate_pressure(
    pressure_payload: dict[str, Any] | None, errors: list[dict[str, str]]
) -> bool:
    if pressure_payload is None:
        return False
    rows = _as_list(pressure_payload.get("rows"))
    row_by_id = {
        row.get("standard_id"): row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("standard_id"), str)
    }
    row = row_by_id.get("concept_mechanism_requires_activation_receipt_loop")
    if not isinstance(row, dict):
        _add_error(
            errors,
            path="core/public_standard_pressure.rows",
            code="missing_activation_pressure_row",
            message="Public pressure must expose the activation receipt loop.",
        )
        return False
    route_refs = _as_list(row.get("route_refs"))
    required_refs = [
        "atlas/entry_packet.json::concept_mechanism_entry_route.activation_receipts",
        "python -m microcosm_core.validators.concept_mechanism_population",
    ]
    for required_ref in required_refs:
        if required_ref not in route_refs:
            _add_error(
                errors,
                path="core/public_standard_pressure.concept_mechanism_requires_activation_receipt_loop.route_refs",
                code="activation_pressure_route_ref_missing",
                message=f"Activation pressure row must include {required_ref}.",
            )
    return True


def validate_concept_mechanism_population(
    *,
    entry_packet: dict[str, Any],
    pressure_payload: dict[str, Any] | None = None,
    root: Path | None = None,
    command: str = "concept-mechanism-population-validator",
) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    route = _as_dict(entry_packet.get("concept_mechanism_entry_route"))
    if not route:
        _add_error(
            errors,
            path="concept_mechanism_entry_route",
            code="missing_route",
            message="Entry packet must carry concept_mechanism_entry_route.",
        )
    specimen_ids = _validate_specimens(route, errors)
    receipt_ids = _validate_activation_receipts(route, specimen_ids, errors)
    pressure_checked = _validate_pressure(pressure_payload, errors)
    validation_commands = _as_list(route.get("validation_commands"))
    validator_command_present = any(
        isinstance(command_ref, str)
        and "microcosm_core.validators.concept_mechanism_population" in command_ref
        for command_ref in validation_commands
    )
    if not validator_command_present:
        _add_error(
            errors,
            path="concept_mechanism_entry_route.validation_commands",
            code="activation_validator_command_missing",
            message="Validation commands must expose the activation population validator.",
        )
    record_validation = None
    if root is not None:
        record_validation = _validate_record_corpus(root, errors)

    return {
        "schema": "microcosm_concept_mechanism_population_validation_v0",
        "status": "pass" if not errors else "blocked",
        "command": command,
        "specimen_count": len(specimen_ids),
        "activation_receipt_count": len(receipt_ids),
        "activation_receipt_ids": receipt_ids,
        "pressure_checked": pressure_checked,
        "record_validation": record_validation,
        "parallel_index_authorized": False,
        "anti_claim": (
            "This validator checks specimen/activation route shape only; it does not "
            "authorize a parallel concept index, release readiness, provider calls, or "
            "private-data equivalence."
        ),
        "errors": errors,
    }


def validate_paths(
    *,
    entry_packet_path: Path,
    pressure_path: Path | None,
    out: Path | None,
    root: Path | None = None,
    command: str,
) -> dict[str, Any]:
    pressure_payload = _load_json(pressure_path) if pressure_path else None
    receipt = validate_concept_mechanism_population(
        entry_packet=_load_json(entry_packet_path),
        pressure_payload=pressure_payload,
        root=root,
        command=command,
    )
    if out:
        out.mkdir(parents=True, exist_ok=True)
        (out / "concept_mechanism_population_validation.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate Microcosm concept/mechanism population specimens and activation receipts."
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--entry-packet", type=Path)
    parser.add_argument("--pressure", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    entry_packet_path = args.entry_packet or root / "atlas/entry_packet.json"
    pressure_path = args.pressure
    if pressure_path is None and (root / "core/public_standard_pressure.json").is_file():
        pressure_path = root / "core/public_standard_pressure.json"
    command = (
        "python -m microcosm_core.validators.concept_mechanism_population "
        f"--root {root} --entry-packet {entry_packet_path}"
        + (f" --pressure {pressure_path}" if pressure_path else "")
        + (f" --out {args.out}" if args.out else "")
    )
    receipt = validate_paths(
        entry_packet_path=entry_packet_path,
        pressure_path=pressure_path,
        out=args.out,
        root=root,
        command=command,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
