from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ALLOWED_RESIDUAL_DISPOSITIONS = {
    "already_valid_projection_consumer",
    "captured_for_later_owner",
    "closed_as_stale_parallel_index",
    "redirected_to_projection_consumer",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _validator_ref_is_inspectable(ref: str) -> bool:
    prefixes = ("microcosm ", "python ", "./", "tests/")
    return ref.startswith(prefixes) or "::test_" in ref or "/tests/" in ref


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

    return {
        "schema": "microcosm_concept_mechanism_population_validation_v0",
        "status": "pass" if not errors else "blocked",
        "command": command,
        "specimen_count": len(specimen_ids),
        "activation_receipt_count": len(receipt_ids),
        "activation_receipt_ids": receipt_ids,
        "pressure_checked": pressure_checked,
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
    command: str,
) -> dict[str, Any]:
    pressure_payload = _load_json(pressure_path) if pressure_path else None
    receipt = validate_concept_mechanism_population(
        entry_packet=_load_json(entry_packet_path),
        pressure_payload=pressure_payload,
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
    parser.add_argument("--entry-packet", required=True, type=Path)
    parser.add_argument("--pressure", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    command = (
        "python -m microcosm_core.validators.concept_mechanism_population "
        f"--entry-packet {args.entry_packet}"
        + (f" --pressure {args.pressure}" if args.pressure else "")
        + (f" --out {args.out}" if args.out else "")
    )
    receipt = validate_paths(
        entry_packet_path=args.entry_packet,
        pressure_path=args.pressure,
        out=args.out,
        command=command,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
