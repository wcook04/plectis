"""Axiom support-cover evaluator (the Axiom Reflexion Kernel core).

Read-only evaluator for ``validator.microcosm.axiom_support_cover``. It computes
*bounded* support for piloted axiom obligations from evidence that already exists
on disk, derives principle support by inheritance, and emits candidate-axiom
pressure. It mutates no law and authorizes nothing.

Honesty contract (this evaluator is itself a Microcosm artifact, so AX-12 applies
to it): it never certifies ``strong``. The ceiling lattice in
``std_microcosm_axiom.json::axiom_payload_contract.evidence_ceiling_lattice`` names
eight components. ``core/axiom_support_ceiling_dimensions.json`` source-registers
all eight components today. ``freshness_state`` is deliberately order-owned but
still computes an ``unknown_`` value until a source-owned refresh contract exists:
not bottom, not strong, and not live freshness proof.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from microcosm_core.schemas import read_json_strict


CHECKER_ID = "checker.microcosm.validators.axiom_support_cover"
ROUTING_REL = Path("core/axiom_organ_routing.json")
PRINCIPLES_REL = Path("PRINCIPLES.md")
EVIDENCE_CLASSES_REL = Path("core/organ_evidence_classes.json")
ORGAN_REGISTRY_REL = Path("core/organ_registry.json")
AXIOM_STANDARD_REL = Path("standards/std_microcosm_axiom.json")
CEILING_DIMENSIONS_REL = Path("core/axiom_support_ceiling_dimensions.json")
CHECKER_SCOPE_ORDER_REL = Path("core/axiom_support_checker_scope_order.json")
AUTHORITY_SCOPE_ORDER_REL = Path("core/axiom_support_authority_scope_order.json")
PROJECTION_SCOPE_ORDER_REL = Path("core/axiom_support_projection_scope_order.json")
DOMAIN_SCOPE_ORDER_REL = Path("core/axiom_support_domain_scope_order.json")
FRESHNESS_STATE_ORDER_REL = Path("core/axiom_support_freshness_state_order.json")
PROVENANCE_ORDER_REL = Path("core/axiom_support_provenance_order.json")
EXAMPLES_REL = Path("examples")
RECEIPTS_FIRST_WAVE_REL = Path("receipts/first_wave")

# Component order named in std_microcosm_axiom.json::evidence_ceiling_lattice.
DEFAULT_CEILING_COMPONENTS = (
    "evidence_class",
    "checker_scope",
    "provenance_class",
    "freshness_state",
    "domain_scope",
    "negative_case_status",
    "authority_scope",
    "projection_scope",
)
# Dimensions with evaluator code that can consume an order-owner registry today.
COMPUTED_ORDER_OWNED_COMPONENTS = (
    "evidence_class",
    "checker_scope",
    "provenance_class",
    "freshness_state",
    "domain_scope",
    "negative_case_status",
    "authority_scope",
    "projection_scope",
)
# negative_case_status is the gating dimension after evidence_class: the routing
# strength_scale defines "strong" as computing the property AND having a negative
# case that rejects the anti-axiom, so a negative-case order is what makes "strong"
# computable rather than rhetorical.
NEGATIVE_CASE_STATUS_ORDER = ("absent", "declared_only", "referenced_in_bound_checker")
# anti_axiom_rejection is the JUDGMENT side (not just presence). No v0 tier certifies
# a per-obligation rejection: 'organ_receipt_coverage_present' means the witness organ's
# receipt records a complete negative-case suite, but mapping that endpoint/shape coverage
# to THIS obligation's anti-axiom slice is left explicitly unverified (endpoint coverage is
# not propagation rejection).
ANTI_AXIOM_REJECTION_ORDER = (
    "absent",
    "declared_only",
    "referenced_in_bound_checker",
    "organ_receipt_coverage_present",
)
MAPPING_RELATION_ENUM = (
    "unmapped",
    "orthogonal",
    "illustrative_only",
    "partial_overlap",
    "subsumes_obligation",
    "exact_obligation_rejection",
    "conflict_detected",
)
CHECKER_SCOPE_ORDER = (
    "no_checker_surface_bound",
    "non_checker_source_surface_refs_only",
    "checker_surface_refs_bound",
    "checker_surface_refs_with_negative_case_reference",
)
AUTHORITY_SCOPE_ORDER = (
    "read_only_validator_projection_authority",
    "source_binding_with_read_only_validator_authority",
)
PROJECTION_SCOPE_ORDER = (
    "generated_support_projection_boundary_only",
    "source_binding_with_generated_projection_boundary",
)
FRESHNESS_STATE_ORDER = (
    "unknown_live_freshness_no_refresh_contract",
    "source_refresh_contract_checked",
)
DOMAIN_SCOPE_ORDER = (
    "declared_obligation_domain_only",
    "declared_obligation_domain_with_bound_witness_material",
)
PROVENANCE_CLASS_ORDER = (
    "declared_negative_case_only_no_positive_witness_material",
    "checker_surface_refs_only",
    "accepted_organ_material_chain",
    "accepted_organ_material_chain_with_checker_surfaces",
)


def _default_root() -> Path:
    # src/microcosm_core/validators/axiom_support_cover.py -> microcosm-substrate root
    return Path(__file__).resolve().parents[3]


def _obligation_sort_key(value: str) -> tuple[int, int, str]:
    match = re.match(r"^AX-(\d+)\.O(\d+)\.([A-Za-z0-9_]+)$", value)
    if match:
        return (int(match.group(1)), int(match.group(2)), match.group(3))
    return (9999, 9999, value)


def _axiom_sort_key(value: str) -> tuple[int, str]:
    match = re.match(r"^AX-(\d+)$", value)
    if match:
        return (int(match.group(1)), value)
    return (9999, value)


def _principle_obligation_groundings(root: Path) -> dict[str, list[str]]:
    path = root / PRINCIPLES_REL
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    body = text.split("## Anti-Claim", 1)[0]
    matches = list(re.finditer(r"^## (P-\d+) .+$", body, flags=re.MULTILINE))
    result: dict[str, list[str]] = {}
    for index, match in enumerate(matches):
        section_start = match.end()
        section_end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        section = body[section_start:section_end]
        obligation_match = re.search(
            r"^Obligation grounding:\s*(.+)$", section, flags=re.MULTILINE
        )
        if obligation_match:
            refs = re.findall(
                r"\bAX-\d+\.O\d+\.[A-Za-z0-9_]+\b",
                obligation_match.group(1),
            )
            result[match.group(1)] = sorted(set(refs), key=_obligation_sort_key)
    return result


def _basis_digest(root: Path, rels: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for rel in rels:
        digest.update(rel.as_posix().encode("utf-8"))
        try:
            digest.update((root / rel).read_bytes())
        except OSError:
            digest.update(b"<missing>")
    return "sha256:" + digest.hexdigest()


def _provenance_order_registry(root: Path) -> dict[str, Any]:
    payload = read_json_strict(root / PROVENANCE_ORDER_REL)
    if not isinstance(payload, dict):
        raise ValueError(f"{PROVENANCE_ORDER_REL.as_posix()} must be a JSON object")
    if payload.get("component_id") != "provenance_class":
        raise ValueError(
            f"{PROVENANCE_ORDER_REL.as_posix()}::component_id must be provenance_class"
        )
    order_values = tuple(str(item) for item in payload.get("order_values", []))
    if order_values != PROVENANCE_CLASS_ORDER:
        raise ValueError(
            f"{PROVENANCE_ORDER_REL.as_posix()}::order_values must match the "
            "validator provenance class order"
        )
    return {
        "payload": payload,
        "order_values": order_values,
        "source_ref": PROVENANCE_ORDER_REL.as_posix(),
        "basis_digest": _basis_digest(root, (PROVENANCE_ORDER_REL,)),
    }


def _checker_scope_order_registry(root: Path) -> dict[str, Any]:
    payload = read_json_strict(root / CHECKER_SCOPE_ORDER_REL)
    if not isinstance(payload, dict):
        raise ValueError(f"{CHECKER_SCOPE_ORDER_REL.as_posix()} must be a JSON object")
    if payload.get("component_id") != "checker_scope":
        raise ValueError(
            f"{CHECKER_SCOPE_ORDER_REL.as_posix()}::component_id must be checker_scope"
        )
    order_values = tuple(str(item) for item in payload.get("order_values", []))
    if order_values != CHECKER_SCOPE_ORDER:
        raise ValueError(
            f"{CHECKER_SCOPE_ORDER_REL.as_posix()}::order_values must match the "
            "validator checker-scope order"
        )
    return {
        "payload": payload,
        "order_values": order_values,
        "source_ref": CHECKER_SCOPE_ORDER_REL.as_posix(),
        "basis_digest": _basis_digest(root, (CHECKER_SCOPE_ORDER_REL,)),
    }


def _authority_scope_order_registry(root: Path) -> dict[str, Any]:
    payload = read_json_strict(root / AUTHORITY_SCOPE_ORDER_REL)
    if not isinstance(payload, dict):
        raise ValueError(f"{AUTHORITY_SCOPE_ORDER_REL.as_posix()} must be a JSON object")
    if payload.get("component_id") != "authority_scope":
        raise ValueError(
            f"{AUTHORITY_SCOPE_ORDER_REL.as_posix()}::component_id must be authority_scope"
        )
    order_values = tuple(str(item) for item in payload.get("order_values", []))
    if order_values != AUTHORITY_SCOPE_ORDER:
        raise ValueError(
            f"{AUTHORITY_SCOPE_ORDER_REL.as_posix()}::order_values must match the "
            "validator authority-scope order"
        )
    return {
        "payload": payload,
        "order_values": order_values,
        "source_ref": AUTHORITY_SCOPE_ORDER_REL.as_posix(),
        "basis_digest": _basis_digest(root, (AUTHORITY_SCOPE_ORDER_REL,)),
    }


def _projection_scope_order_registry(root: Path) -> dict[str, Any]:
    payload = read_json_strict(root / PROJECTION_SCOPE_ORDER_REL)
    if not isinstance(payload, dict):
        raise ValueError(f"{PROJECTION_SCOPE_ORDER_REL.as_posix()} must be a JSON object")
    if payload.get("component_id") != "projection_scope":
        raise ValueError(
            f"{PROJECTION_SCOPE_ORDER_REL.as_posix()}::component_id must be projection_scope"
        )
    order_values = tuple(str(item) for item in payload.get("order_values", []))
    if order_values != PROJECTION_SCOPE_ORDER:
        raise ValueError(
            f"{PROJECTION_SCOPE_ORDER_REL.as_posix()}::order_values must match the "
            "validator projection-scope order"
        )
    return {
        "payload": payload,
        "order_values": order_values,
        "source_ref": PROJECTION_SCOPE_ORDER_REL.as_posix(),
        "basis_digest": _basis_digest(root, (PROJECTION_SCOPE_ORDER_REL,)),
    }


def _freshness_state_order_registry(root: Path) -> dict[str, Any]:
    payload = read_json_strict(root / FRESHNESS_STATE_ORDER_REL)
    if not isinstance(payload, dict):
        raise ValueError(f"{FRESHNESS_STATE_ORDER_REL.as_posix()} must be a JSON object")
    if payload.get("component_id") != "freshness_state":
        raise ValueError(
            f"{FRESHNESS_STATE_ORDER_REL.as_posix()}::component_id must be freshness_state"
        )
    order_values = tuple(str(item) for item in payload.get("order_values", []))
    if order_values != FRESHNESS_STATE_ORDER:
        raise ValueError(
            f"{FRESHNESS_STATE_ORDER_REL.as_posix()}::order_values must match the "
            "validator freshness-state order"
        )
    return {
        "payload": payload,
        "order_values": order_values,
        "source_ref": FRESHNESS_STATE_ORDER_REL.as_posix(),
        "basis_digest": _basis_digest(root, (FRESHNESS_STATE_ORDER_REL,)),
    }


def _domain_scope_order_registry(root: Path) -> dict[str, Any]:
    payload = read_json_strict(root / DOMAIN_SCOPE_ORDER_REL)
    if not isinstance(payload, dict):
        raise ValueError(f"{DOMAIN_SCOPE_ORDER_REL.as_posix()} must be a JSON object")
    if payload.get("component_id") != "domain_scope":
        raise ValueError(
            f"{DOMAIN_SCOPE_ORDER_REL.as_posix()}::component_id must be domain_scope"
        )
    order_values = tuple(str(item) for item in payload.get("order_values", []))
    if order_values != DOMAIN_SCOPE_ORDER:
        raise ValueError(
            f"{DOMAIN_SCOPE_ORDER_REL.as_posix()}::order_values must match the "
            "validator domain-scope order"
        )
    return {
        "payload": payload,
        "order_values": order_values,
        "source_ref": DOMAIN_SCOPE_ORDER_REL.as_posix(),
        "basis_digest": _basis_digest(root, (DOMAIN_SCOPE_ORDER_REL,)),
    }


def _ceiling_dimension_registry(root: Path) -> dict[str, Any]:
    payload = read_json_strict(root / CEILING_DIMENSIONS_REL)
    if not isinstance(payload, dict):
        raise ValueError(f"{CEILING_DIMENSIONS_REL.as_posix()} must be a JSON object")
    rows = payload.get("components", [])
    if not isinstance(rows, list):
        raise ValueError(f"{CEILING_DIMENSIONS_REL.as_posix()}::components must be a list")
    by_id = {
        str(row.get("component_id")): row
        for row in rows
        if isinstance(row, dict) and row.get("component_id")
    }
    component_order = tuple(str(item) for item in payload.get("component_order", []))
    if component_order != DEFAULT_CEILING_COMPONENTS:
        raise ValueError(
            f"{CEILING_DIMENSIONS_REL.as_posix()}::component_order must match "
            "std_microcosm_axiom evidence_ceiling_lattice"
        )
    if set(by_id) != set(component_order):
        raise ValueError(
            f"{CEILING_DIMENSIONS_REL.as_posix()}::components must name every "
            "ceiling component exactly once"
        )
    order_owned = tuple(
        component
        for component in component_order
        if by_id[component].get("owner_status") == "order_owned"
    )
    explicitly_unowned = tuple(
        component
        for component in component_order
        if by_id[component].get("owner_status") == "explicitly_unowned"
    )
    if set(order_owned) != set(COMPUTED_ORDER_OWNED_COMPONENTS):
        raise ValueError(
            f"{CEILING_DIMENSIONS_REL.as_posix()} declares order-owned dimensions "
            "that this evaluator does not compute"
        )
    if len(order_owned) + len(explicitly_unowned) != len(component_order):
        raise ValueError(
            f"{CEILING_DIMENSIONS_REL.as_posix()} has components without an "
            "allowed owner_status"
        )
    checker_scope_order = (
        _checker_scope_order_registry(root)
        if "checker_scope" in order_owned
        else None
    )
    provenance_order = (
        _provenance_order_registry(root)
        if "provenance_class" in order_owned
        else None
    )
    authority_scope_order = (
        _authority_scope_order_registry(root)
        if "authority_scope" in order_owned
        else None
    )
    projection_scope_order = (
        _projection_scope_order_registry(root)
        if "projection_scope" in order_owned
        else None
    )
    freshness_state_order = (
        _freshness_state_order_registry(root)
        if "freshness_state" in order_owned
        else None
    )
    domain_scope_order = (
        _domain_scope_order_registry(root)
        if "domain_scope" in order_owned
        else None
    )
    return {
        "payload": payload,
        "component_order": component_order,
        "components_by_id": by_id,
        "order_owned": order_owned,
        "explicitly_unowned": explicitly_unowned,
        "checker_scope_order": checker_scope_order,
        "provenance_order": provenance_order,
        "authority_scope_order": authority_scope_order,
        "projection_scope_order": projection_scope_order,
        "freshness_state_order": freshness_state_order,
        "domain_scope_order": domain_scope_order,
        "source_ref": CEILING_DIMENSIONS_REL.as_posix(),
        "basis_digest": _basis_digest(
            root,
            tuple(
                rel
                for rel, registry in (
                    (CEILING_DIMENSIONS_REL, True),
                    (CHECKER_SCOPE_ORDER_REL, checker_scope_order is not None),
                    (PROVENANCE_ORDER_REL, provenance_order is not None),
                    (AUTHORITY_SCOPE_ORDER_REL, authority_scope_order is not None),
                    (PROJECTION_SCOPE_ORDER_REL, projection_scope_order is not None),
                    (FRESHNESS_STATE_ORDER_REL, freshness_state_order is not None),
                    (DOMAIN_SCOPE_ORDER_REL, domain_scope_order is not None),
                )
                if registry
            )
        ),
    }


def _evidence_class_by_organ(root: Path) -> dict[str, dict[str, Any]]:
    classes = read_json_strict(root / EVIDENCE_CLASSES_REL)
    profiles = classes.get("class_profiles", {}) if isinstance(classes, dict) else {}
    rank_by_class: dict[str, int] = {}
    for cls, profile in profiles.items():
        if isinstance(profile, dict) and isinstance(profile.get("evidence_strength_rank"), int):
            rank_by_class[cls] = profile["evidence_strength_rank"]
    by_organ: dict[str, dict[str, Any]] = {}
    for row in classes.get("organ_evidence_classes", []) if isinstance(classes, dict) else []:
        if isinstance(row, dict) and row.get("organ_id"):
            cls = row.get("evidence_class")
            by_organ[str(row["organ_id"])] = {"evidence_class": cls, "rank": rank_by_class.get(cls)}
    return by_organ


def _registry_organ_ids(root: Path) -> set[str]:
    registry = read_json_strict(root / ORGAN_REGISTRY_REL)
    rows = registry.get("implemented_organs", []) if isinstance(registry, dict) else []
    return {str(row.get("organ_id")) for row in rows if isinstance(row, dict) and row.get("organ_id")}


def _binding_issues(binding: dict[str, Any], row: dict[str, Any], root: Path, organ_ids: set[str]) -> list[str]:
    issues: list[str] = []
    for organ in binding.get("witness_organs", []):
        if organ not in organ_ids:
            issues.append(f"organ_not_in_registry:{organ}")
    for surface in binding.get("witness_surfaces", []):
        ref = str(surface).split("::", 1)[0]
        if "*" in ref:
            if not list(root.glob(ref)):
                issues.append(f"surface_glob_unresolved:{surface}")
        elif not (root / ref).exists():
            issues.append(f"surface_missing:{surface}")
    row_negatives = set(row.get("negative_case_codes", []))
    for code in binding.get("negative_case_codes", []):
        if code not in row_negatives:
            issues.append(f"negative_code_not_on_row:{code}")
    return issues


def _evidence_class_component(binding: dict[str, Any], by_organ: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ranks = [
        by_organ[organ]["rank"]
        for organ in binding.get("witness_organs", [])
        if organ in by_organ and by_organ[organ]["rank"] is not None
    ]
    if not ranks:
        return {"value": None, "status": "unknown_no_organ_evidence_class_in_binding"}
    # join over alternative organ witnesses for this single component.
    return {"value": max(ranks), "status": "computed_from_organ_evidence_class"}


def _checker_scope_component(
    binding: dict[str, Any],
    root: Path,
    registry: dict[str, Any] | None,
) -> dict[str, Any]:
    """Classify the checker/source-surface reach named by the obligation binding."""
    surfaces = [str(surface).split("::", 1)[0] for surface in binding.get("witness_surfaces", [])]
    negative_codes = list(binding.get("negative_case_codes", []))
    checker_surfaces = [surface for surface in surfaces if surface.endswith(".py")]
    negative_found = False
    for surface in checker_surfaces:
        try:
            text = (root / surface).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(code in text for code in negative_codes):
            negative_found = True
            break

    if checker_surfaces and negative_found:
        value = "checker_surface_refs_with_negative_case_reference"
        status = "computed_from_bound_checker_surface_and_negative_case_code"
    elif checker_surfaces:
        value = "checker_surface_refs_bound"
        status = "computed_from_bound_checker_surface_refs"
    elif surfaces:
        value = "non_checker_source_surface_refs_only"
        status = "computed_from_non_checker_source_surface_refs"
    else:
        value = "no_checker_surface_bound"
        status = "computed_absent_checker_surface_binding"

    order_values = set(registry.get("order_values", ())) if registry else set()
    if value not in order_values:
        return {
            "value": None,
            "status": f"unknown_checker_scope_not_in_source_order:{value}",
            "source_ref": CHECKER_SCOPE_ORDER_REL.as_posix(),
        }
    return {
        "value": value,
        "status": status,
        "source_ref": CHECKER_SCOPE_ORDER_REL.as_posix(),
        "material_counts": {
            "witness_surface_ref_count": len(surfaces),
            "checker_surface_ref_count": len(checker_surfaces),
            "negative_case_ref_count": len(negative_codes),
            "negative_case_code_found_in_checker": int(negative_found),
        },
    }


def _authority_scope_component(
    binding: dict[str, Any],
    registry: dict[str, Any] | None,
) -> dict[str, Any]:
    """Classify read-only authority boundaries without granting mutation rights."""
    witness_organs = list(binding.get("witness_organs", []))
    witness_surfaces = list(binding.get("witness_surfaces", []))
    negative_codes = list(binding.get("negative_case_codes", []))
    material_count = len(witness_organs) + len(witness_surfaces) + len(negative_codes)
    if material_count:
        value = "source_binding_with_read_only_validator_authority"
        status = "computed_from_source_binding_and_read_only_validator_contract"
    else:
        value = "read_only_validator_projection_authority"
        status = "computed_from_read_only_validator_contract_without_binding_material"

    order_values = set(registry.get("order_values", ())) if registry else set()
    if value not in order_values:
        return {
            "value": None,
            "status": f"unknown_authority_scope_not_in_source_order:{value}",
            "source_ref": AUTHORITY_SCOPE_ORDER_REL.as_posix(),
        }
    return {
        "value": value,
        "status": status,
        "source_ref": AUTHORITY_SCOPE_ORDER_REL.as_posix(),
        "material_counts": {
            "witness_organ_ref_count": len(witness_organs),
            "witness_surface_ref_count": len(witness_surfaces),
            "negative_case_ref_count": len(negative_codes),
        },
        "non_laundering_boundary": (
            "read-only validator authority does not become source mutation, release, "
            "public-readiness, or anti-axiom rejection authority"
        ),
    }


def _projection_scope_component(
    binding: dict[str, Any],
    registry: dict[str, Any] | None,
) -> dict[str, Any]:
    """Classify source/projection boundary without making output evidence."""
    witness_organs = list(binding.get("witness_organs", []))
    witness_surfaces = list(binding.get("witness_surfaces", []))
    negative_codes = list(binding.get("negative_case_codes", []))
    material_count = len(witness_organs) + len(witness_surfaces) + len(negative_codes)
    if material_count:
        value = "source_binding_with_generated_projection_boundary"
        status = "computed_from_source_binding_and_generated_projection_boundary"
    else:
        value = "generated_support_projection_boundary_only"
        status = "computed_generated_projection_boundary_without_binding_material"

    order_values = set(registry.get("order_values", ())) if registry else set()
    if value not in order_values:
        return {
            "value": None,
            "status": f"unknown_projection_scope_not_in_source_order:{value}",
            "source_ref": PROJECTION_SCOPE_ORDER_REL.as_posix(),
        }
    return {
        "value": value,
        "status": status,
        "source_ref": PROJECTION_SCOPE_ORDER_REL.as_posix(),
        "material_counts": {
            "witness_organ_ref_count": len(witness_organs),
            "witness_surface_ref_count": len(witness_surfaces),
            "negative_case_ref_count": len(negative_codes),
        },
        "non_laundering_boundary": (
            "generated support-cover output, Markdown, atlas cards, public copy, and "
            "generated doctrine-lattice projections do not become source evidence"
        ),
    }


def _freshness_state_component(
    registry: dict[str, Any] | None,
) -> dict[str, Any]:
    """Classify reproducible basis state without claiming live freshness."""
    value = "unknown_live_freshness_no_refresh_contract"
    order_values = set(registry.get("order_values", ())) if registry else set()
    if value not in order_values:
        return {
            "value": None,
            "status": f"unknown_freshness_state_not_in_source_order:{value}",
            "source_ref": FRESHNESS_STATE_ORDER_REL.as_posix(),
        }
    return {
        "value": value,
        "status": "computed_from_deterministic_basis_without_live_refresh_contract",
        "source_ref": FRESHNESS_STATE_ORDER_REL.as_posix(),
        "basis_inputs": [
            "basis_digest",
            "rederive",
            "as_of",
        ],
        "non_laundering_boundary": (
            "basis digest determinism, current file existence, receipts, and "
            "generated output do not become live freshness proof"
        ),
    }


def _domain_scope_component(
    binding: dict[str, Any],
    registry: dict[str, Any] | None,
) -> dict[str, Any]:
    """Classify local declared domain reach without generalizing it."""
    witness_organs = list(binding.get("witness_organs", []))
    witness_surfaces = list(binding.get("witness_surfaces", []))
    negative_codes = list(binding.get("negative_case_codes", []))
    material_count = len(witness_organs) + len(witness_surfaces) + len(negative_codes)
    if material_count:
        value = "declared_obligation_domain_with_bound_witness_material"
        status = "computed_from_declared_obligation_domain_and_bound_witness_material"
    else:
        value = "declared_obligation_domain_only"
        status = "computed_from_declared_obligation_domain_without_binding_material"

    order_values = set(registry.get("order_values", ())) if registry else set()
    if value not in order_values:
        return {
            "value": None,
            "status": f"unknown_domain_scope_not_in_source_order:{value}",
            "source_ref": DOMAIN_SCOPE_ORDER_REL.as_posix(),
        }
    return {
        "value": value,
        "status": status,
        "source_ref": DOMAIN_SCOPE_ORDER_REL.as_posix(),
        "material_counts": {
            "witness_organ_ref_count": len(witness_organs),
            "witness_surface_ref_count": len(witness_surfaces),
            "negative_case_ref_count": len(negative_codes),
        },
        "non_laundering_boundary": (
            "fixture, endpoint, organ-local, public-copy, and local obligation "
            "coverage do not become substrate-general proof"
        ),
    }


def _provenance_class_component(
    binding: dict[str, Any],
    root: Path,
    registry: dict[str, Any] | None,
) -> dict[str, Any]:
    """Classify only the provenance material already bound to the obligation.

    This is not provenance quality proof. It orders whether the obligation is tied
    to source/checker refs, accepted-organ bundle/receipt material, or only a
    declared negative-code route. Freshness, authority, domain scope, and
    anti-axiom rejection remain separate ceiling dimensions.
    """
    surfaces = list(binding.get("witness_surfaces", []))
    negatives = list(binding.get("negative_case_codes", []))
    example_bundle_refs: list[str] = []
    receipt_refs: list[str] = []
    for organ in binding.get("witness_organs", []):
        chain = _organ_evidence_chain(root, str(organ))
        example_bundle_refs.extend(chain["example_bundle_refs"])
        receipt_refs.extend(chain["receipt_refs"])

    if example_bundle_refs and receipt_refs and surfaces:
        value = "accepted_organ_material_chain_with_checker_surfaces"
        status = "computed_from_organ_receipt_bundle_and_checker_surface_refs"
    elif example_bundle_refs and receipt_refs:
        value = "accepted_organ_material_chain"
        status = "computed_from_organ_receipt_and_bundle_refs"
    elif surfaces:
        value = "checker_surface_refs_only"
        status = "computed_from_checker_surface_refs"
    elif negatives:
        value = "declared_negative_case_only_no_positive_witness_material"
        status = "computed_from_negative_case_code_without_positive_witness_material"
    else:
        return {
            "value": None,
            "status": "unknown_no_provenance_material_in_binding",
            "source_ref": PROVENANCE_ORDER_REL.as_posix(),
        }

    order_values = set(registry.get("order_values", ())) if registry else set()
    if value not in order_values:
        return {
            "value": None,
            "status": f"unknown_provenance_class_not_in_source_order:{value}",
            "source_ref": PROVENANCE_ORDER_REL.as_posix(),
        }
    return {
        "value": value,
        "status": status,
        "source_ref": PROVENANCE_ORDER_REL.as_posix(),
        "material_counts": {
            "witness_surface_ref_count": len(surfaces),
            "example_bundle_ref_count": len(set(example_bundle_refs)),
            "receipt_ref_count": len(set(receipt_refs)),
            "negative_case_ref_count": len(negatives),
        },
    }


def _negative_case_status_component(binding: dict[str, Any], root: Path) -> dict[str, Any]:
    """Order-owned by routing negative_case_codes + the bound checker/test surfaces.

    'strong' (per the routing strength_scale) requires a negative case that rejects
    the anti-axiom; this resolves how strongly that gate is actually wired, never
    claiming more than the bound surfaces show.
    """
    codes = list(binding.get("negative_case_codes", []))
    if not codes:
        return {"value": "absent", "status": "no_negative_case_in_binding"}
    for surface in binding.get("witness_surfaces", []):
        ref = str(surface).split("::", 1)[0]
        if not ref.endswith(".py"):
            continue
        try:
            text = (root / ref).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(code in text for code in codes):
            return {
                "value": "referenced_in_bound_checker",
                "status": "negative_case_code_found_in_bound_checker_surface",
            }
    return {"value": "declared_only", "status": "negative_case_code_declared_not_found_in_bound_checker"}


def _organ_receipt_negative_coverage_payload(root: Path, organ: str) -> dict[str, Any] | None:
    """Return a complete, passing first-wave negative-case suite for an organ."""
    receipt = root / RECEIPTS_FIRST_WAVE_REL / organ / f"{organ}_validation_receipt.json"
    try:
        payload = read_json_strict(receipt)
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    coverage = payload.get("negative_case_coverage")
    if (
        isinstance(coverage, dict)
        and "expected" in coverage
        and coverage.get("missing") == []
        and payload.get("status") == "pass"
    ):
        return {
            "organ_id": organ,
            "receipt_ref": receipt.relative_to(root).as_posix(),
            "expected": list(coverage.get("expected", [])),
            "observed": coverage.get("observed", {}),
            "status": payload.get("status"),
        }
    return None


def _organ_receipt_negative_coverage(root: Path, organ: str) -> bool:
    """True iff the organ's first-wave validation receipt records a complete, passing
    negative-case suite (negative_case_coverage with empty 'missing' and pass status)."""
    return _organ_receipt_negative_coverage_payload(root, organ) is not None


def _negative_case_coverage_records(root: Path, organs: list[str]) -> list[dict[str, Any]]:
    records = []
    for organ in sorted(set(organs)):
        payload = _organ_receipt_negative_coverage_payload(root, organ)
        if payload is not None:
            records.append(payload)
    return records


def _source_mapping_for_obligation(row: dict[str, Any], obligation_id: str) -> dict[str, Any] | None:
    for mapping in row.get("anti_axiom_rejection_mappings", []):
        if isinstance(mapping, dict) and mapping.get("obligation_ref") == obligation_id:
            return mapping
    return None


def _anti_axiom_rejection_mapping(
    obligation: dict[str, Any],
    row: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    """Map receipt-observed negative coverage to one obligation slice.

    This is deliberately conservative. It prefers source-owned mapping rows when
    present, still recomputes receipt material from disk, and never treats a
    non-exact/non-subsuming row as verified rejection.
    """
    obligation_id = str(obligation.get("obligation_id", ""))
    binding = obligation.get("binding", {})
    surfaces = list(binding.get("witness_surfaces", []))
    negative_codes = list(binding.get("negative_case_codes", []))
    organs = list(binding.get("witness_organs", [])) + list(row.get("witness_organs", []))
    records = _negative_case_coverage_records(root, organs)
    receipt_refs = sorted({record["receipt_ref"] for record in records})
    observed_negative_case_refs = sorted(
        {
            f"{family}:{code}"
            for record in records
            for family, codes in (record.get("observed") or {}).items()
            for code in (codes if isinstance(codes, list) else [])
        }
    )
    observed_families = {ref.split(":", 1)[0] for ref in observed_negative_case_refs}
    relation = "unmapped"
    reason = (
        "No standard-owned mapping rule maps available receipt coverage to this "
        "obligation's anti-axiom slice."
    )
    checker_boundary = (
        "declared witness debt; checker does not close the obligation"
        if obligation.get("coverage_status") == "layer_debt"
        else "bounded checker witness over declared surfaces and negative-case codes"
    )
    mapping_verified = False
    mapping_source = "evaluator_inferred_fallback"
    source_authority_ref = None
    anti_claims = [
        "This mapping relation is an evaluator-inferred fallback, not source law.",
        "No exact or subsuming rejection is certified without a source-owned declared mapping row.",
        "Generated support-cover output cannot be read back as evidence for itself.",
    ]

    source_mapping = _source_mapping_for_obligation(row, obligation_id)
    if source_mapping is not None:
        mapping_source = "source_owned_anti_axiom_rejection_mapping_row"
        source_authority_ref = (
            (source_mapping.get("basis_env") or {}).get("source_authority_ref")
            or "core/axiom_organ_routing.json::rows[].anti_axiom_rejection_mappings[]"
        )
        relation = str(source_mapping.get("mapping_relation", "unmapped"))
        reason = str(
            source_mapping.get("reason")
            or "Source-owned mapping row does not provide a reason."
        )
        checker_boundary = str(source_mapping.get("checker_boundary") or checker_boundary)
        declared_verified = bool(source_mapping.get("mapping_verified"))
        mapping_verified = declared_verified and relation in (
            "exact_obligation_rejection",
            "subsumes_obligation",
        )
        if relation not in MAPPING_RELATION_ENUM:
            relation = "conflict_detected"
            reason = (
                "Source-owned mapping row declares a mapping_relation outside "
                "std_microcosm_axiom mapping_relation_enum."
            )
            mapping_verified = False
        anti_claims = list(source_mapping.get("anti_claims") or [])
        if not anti_claims:
            anti_claims = [
                "This source-owned mapping row is non-certifying unless it declares exact or subsuming rejection.",
                "Generated support-cover output cannot be read back as evidence for itself.",
            ]
        if declared_verified and not mapping_verified:
            anti_claims.append(
                "mapping_verified was not honored because only exact_obligation_rejection or "
                "subsumes_obligation may verify rejection."
            )
    else:
        if obligation_id == "AX-8.O1.label_propagation":
            relation = "unmapped"
            reason = (
                "Receipt coverage exercises endpoint/organ cases, but this obligation is "
                "general source->transform->sink label propagation and still carries "
                "AX8-general-taint-propagation layer debt."
            )
        elif (
            obligation_id == "AX-8.O2.sink_policy"
            and "untrusted_to_privileged_sink" in observed_families
            and "RELEASE_EXPORT_PRIVATE_PATH_LEAK" in negative_codes
        ):
            relation = "partial_overlap"
            reason = (
                "The receipt observes untrusted-to-privileged-sink blocking and the bound "
                "checker references RELEASE_EXPORT_PRIVATE_PATH_LEAK, so the evidence "
                "overlaps sink-policy rejection. It is not exact or subsuming without a "
                "declared mapping row."
            )
        elif (
            obligation_id == "AX-8.O3.lying_endpoint_rejected"
            and "PUBLIC_SAFE_IMPORT_TRUE_FORBIDDEN_CLASS" in negative_codes
        ):
            relation = "illustrative_only"
            reason = (
                "The bound checker references the forbidden-class endpoint code, but the "
                "available receipt suite does not declare an endpoint-label assertion "
                "mapping for this obligation."
            )

    material_refs = sorted(set(receipt_refs) | {str(surface).split("::", 1)[0] for surface in surfaces})
    basis_env = {
        "basis_digest": _basis_digest_for_refs(root, material_refs),
        "rederive": "python -m microcosm_core.validators.axiom_support_cover --root <microcosm-substrate>",
        "as_of": "see basis_digest; timestamp intentionally omitted for reproducibility",
    }
    if source_authority_ref:
        basis_env["source_authority_ref"] = source_authority_ref
    return {
        "mapping_id": f"{obligation_id}.anti_axiom_rejection_mapping",
        "axiom_ref": row.get("axiom_id"),
        "obligation_ref": obligation.get("obligation_id"),
        "anti_axiom_ref": row.get("anti_axiom"),
        "receipt_ref": receipt_refs[0] if len(receipt_refs) == 1 else None,
        "receipt_refs": receipt_refs,
        "observed_negative_case_refs": observed_negative_case_refs,
        "receipt_coverage_basis": (
            "complete_passing_negative_case_suite" if receipt_refs else "no_receipt_material"
        ),
        "obligation_failure_shape": obligation.get("predicate"),
        "mapping_relation": relation,
        "checker_boundary": checker_boundary,
        "basis_env": basis_env,
        "mapping_verified": mapping_verified,
        "mapping_source": mapping_source,
        "reason": reason,
        "anti_claims": anti_claims,
    }


def _anti_axiom_rejection(
    obligation: dict[str, Any],
    row: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    """The anti-axiom rejection JUDGMENT, tracked separately from positive support.

    strength_scale defines 'strong' as computing the property AND rejecting the named
    anti-axiom. This resolves how strongly that rejection is evidenced -- and refuses to
    call organ-level receipt coverage a per-obligation rejection, because an organ receipt
    can catch endpoint shapes without rejecting this obligation's specific slice (e.g.
    AX-8.O1 general propagation). That mapping is left explicitly unverified.
    """
    binding = obligation.get("binding", {})
    tier = _negative_case_status_component(binding, root)["value"]
    if any(_organ_receipt_negative_coverage(root, organ) for organ in binding.get("witness_organs", [])):
        tier = "organ_receipt_coverage_present"
    mapping = _anti_axiom_rejection_mapping(obligation, row, root)
    return {
        "anti_axiom_ref": row.get("anti_axiom"),
        "tier": tier,
        "mapping_relation": mapping["mapping_relation"],
        "mapping_verified": mapping["mapping_verified"],
        "mapping": mapping,
        "note": (
            "Rejection is not certified for this obligation. Organ/endpoint receipt "
            "coverage is not mapped to this obligation's anti-axiom slice; no v0 tier "
            "certifies per-obligation rejection."
        ),
    }


def _ceiling_vector(
    binding: dict[str, Any],
    root: Path,
    by_organ: dict[str, dict[str, Any]],
    dimension_registry: dict[str, Any],
) -> dict[str, str]:
    order_owned = set(dimension_registry["order_owned"])
    owned: dict[str, str] = {}
    if "evidence_class" in order_owned:
        owned["evidence_class"] = _evidence_class_component(binding, by_organ)["status"]
    if "checker_scope" in order_owned:
        owned["checker_scope"] = _checker_scope_component(
            binding, root, dimension_registry.get("checker_scope_order")
        )["value"] or "unknown_no_checker_scope_material"
    if "provenance_class" in order_owned:
        owned["provenance_class"] = _provenance_class_component(
            binding, root, dimension_registry.get("provenance_order")
        )["value"] or "unknown_no_provenance_material"
    if "freshness_state" in order_owned:
        owned["freshness_state"] = _freshness_state_component(
            dimension_registry.get("freshness_state_order")
        )["value"] or "unknown_no_freshness_state_material"
    if "domain_scope" in order_owned:
        owned["domain_scope"] = _domain_scope_component(
            binding, dimension_registry.get("domain_scope_order")
        )["value"] or "unknown_no_domain_scope_material"
    if "negative_case_status" in order_owned:
        owned["negative_case_status"] = _negative_case_status_component(binding, root)["value"]
    if "authority_scope" in order_owned:
        owned["authority_scope"] = _authority_scope_component(
            binding, dimension_registry.get("authority_scope_order")
        )["value"] or "unknown_no_authority_scope_material"
    if "projection_scope" in order_owned:
        owned["projection_scope"] = _projection_scope_component(
            binding, dimension_registry.get("projection_scope_order")
        )["value"] or "unknown_no_projection_scope_material"
    return {
        component: owned.get(component, "unknown_no_order_owner")
        for component in dimension_registry["component_order"]
    }


def _witness_gap(gap_id: str, detail: str, claim_effect: str) -> dict[str, str]:
    return {
        "gap_id": gap_id,
        "gap_class": gap_id.split(":", 1)[0],
        "detail": detail,
        "claim_effect": claim_effect,
    }


def _claim_ceiling_for_obligation(
    *,
    computed: str,
    binding_issues: list[str],
    negative_case_status: str,
    anti_axiom_rejection: dict[str, Any],
    ceiling_vector: dict[str, str],
    layer_debt_ref: str | None,
) -> dict[str, Any]:
    """Compute the obligation-local claim ceiling and witness gaps.

    This is deliberately a read-model over evaluated evidence. It does not raise
    support from generated output; it only explains what blocks a stronger claim.
    """
    gaps: list[dict[str, str]] = []
    for issue in binding_issues:
        gaps.append(
            _witness_gap(
                f"binding_unresolved:{issue}",
                issue,
                "blocks obligation support until the binding resolves or becomes declared layer debt",
            )
        )
    if computed == "layer_debt":
        gaps.append(
            _witness_gap(
                f"layer_debt:{layer_debt_ref or 'unspecified'}",
                layer_debt_ref or "layer debt declared without a specific ref",
                "caps the obligation and axiom at partial support",
            )
        )
    if negative_case_status == "absent":
        gaps.append(
            _witness_gap(
                "negative_case_absent",
                "no negative-case code is bound to this obligation",
                "prevents a strong claim under strength_scale",
            )
        )
    elif negative_case_status == "declared_only":
        gaps.append(
            _witness_gap(
                "negative_case_declared_only",
                "negative-case code is declared but not found in a bound checker surface",
                "prevents a strong claim until checker-bound evidence resolves",
            )
        )

    for component, status in ceiling_vector.items():
        if status == "unknown_no_order_owner":
            gaps.append(
                _witness_gap(
                    f"ceiling_component_no_order_owner:{component}",
                    f"{component} has no order-owner registry in this evaluator",
                    "keeps support uncomputable rather than strong",
                )
            )
        elif str(status).startswith("unknown"):
            gaps.append(
                _witness_gap(
                    f"ceiling_component_uncomputed:{component}",
                    status,
                    f"prevents the {component} component from raising the claim ceiling",
                )
            )

    mapping_relation = anti_axiom_rejection.get("mapping_relation", "unmapped")
    if mapping_relation == "conflict_detected":
        gaps.append(
            _witness_gap(
                "anti_axiom_rejection_conflict_detected",
                "anti-axiom rejection mapping declares a conflict",
                "blocks the axiom until the source mapping is repaired",
            )
        )
    elif not anti_axiom_rejection.get("mapping_verified"):
        gaps.append(
            _witness_gap(
                f"anti_axiom_rejection_unverified:{mapping_relation}",
                (
                    "anti-axiom rejection is not verified for this obligation "
                    f"(relation {mapping_relation})"
                ),
                "prevents receipt or endpoint coverage from raising support to strong",
            )
        )

    if mapping_relation == "conflict_detected":
        strongest_allowed_claim = "blocked_conflict_detected"
    elif computed == "blocked_binding_unresolved":
        strongest_allowed_claim = "blocked_binding_unresolved"
    elif computed == "layer_debt":
        strongest_allowed_claim = "partial_capped_by_layer_debt"
    elif not anti_axiom_rejection.get("mapping_verified"):
        strongest_allowed_claim = "not_strong_rejection_mapping_unverified"
    elif any(status == "unknown_no_order_owner" for status in ceiling_vector.values()):
        strongest_allowed_claim = "resolved_strength_uncomputable"
    else:
        strongest_allowed_claim = "resolved_strength_uncomputable"

    return {
        "schema_version": "microcosm_axiom_obligation_claim_ceiling_v1",
        "computed_by": CHECKER_ID,
        "positive_support_status": computed,
        "anti_axiom_rejection_status": (
            "verified" if anti_axiom_rejection.get("mapping_verified") else "unverified"
        ),
        "strongest_allowed_claim": strongest_allowed_claim,
        "strong_certified": False,
        "witness_gaps": gaps,
        "authority_boundary": (
            "computed read-model over core/axiom_organ_routing.json, witness surfaces, "
            "and receipt material; generated support-cover output is not source evidence"
        ),
    }


def _evaluate_obligation(
    obligation: dict[str, Any],
    row: dict[str, Any],
    root: Path,
    organ_ids: set[str],
    by_organ: dict[str, dict[str, Any]],
    dimension_registry: dict[str, Any],
) -> dict[str, Any]:
    binding = obligation.get("binding", {})
    issues = _binding_issues(binding, row, root, organ_ids)
    declared = obligation.get("coverage_status")
    evidence_class = _evidence_class_component(binding, by_organ)
    negative_case_status = _negative_case_status_component(binding, root)
    anti_axiom_rejection = _anti_axiom_rejection(obligation, row, root)
    ceiling_vector = _ceiling_vector(binding, root, by_organ, dimension_registry)

    if declared == "layer_debt":
        computed = "layer_debt"
    elif issues:
        computed = "blocked_binding_unresolved"
    else:
        # Bindings resolve, but support strength is NOT certifiable beyond
        # resolution: most ceiling components still lack an order owner, and a
        # required obligation may carry no negative-case gate. Refusing to claim
        # more is AX-1.O3.
        computed = "resolved_strength_uncomputable"
    claim_ceiling = _claim_ceiling_for_obligation(
        computed=computed,
        binding_issues=issues,
        negative_case_status=negative_case_status["value"],
        anti_axiom_rejection=anti_axiom_rejection,
        ceiling_vector=ceiling_vector,
        layer_debt_ref=obligation.get("layer_debt_ref"),
    )

    return {
        "obligation_id": obligation.get("obligation_id"),
        "required": bool(obligation.get("required")),
        "declared_status": declared,
        "computed": computed,
        "binding_issues": issues,
        "evidence_class_component": evidence_class,
        "negative_case_status": negative_case_status["value"],
        "anti_axiom_rejection": anti_axiom_rejection,
        "ceiling_vector": ceiling_vector,
        "claim_ceiling": claim_ceiling,
        "witness_gaps": claim_ceiling["witness_gaps"],
        "layer_debt_ref": obligation.get("layer_debt_ref"),
    }


def _axiom_verdict(obligations: list[dict[str, Any]], hand_stamped: str | None) -> dict[str, Any]:
    required = [item for item in obligations if item["required"]]
    if any(
        (item.get("anti_axiom_rejection") or {}).get("mapping_relation") == "conflict_detected"
        for item in required
    ):
        verdict = "blocked_conflict_detected"
    elif any(item["computed"] == "blocked_binding_unresolved" for item in required):
        verdict = "blocked"
    elif any(item["computed"] == "layer_debt" for item in required):
        verdict = "partial_capped_by_layer_debt"
    elif required and all(item["computed"] == "resolved_strength_uncomputable" for item in required):
        verdict = "bound_resolved_strength_uncomputable"
    else:
        verdict = "unknown"
    # Even with negative_case_status now computed, v0 does not certify "strong"
    # until every required obligation has a passing negative gate and all required
    # dimensions are order-owned. Make the blocking reasons explicit instead.
    hand_stamped_strong_not_certifiable = hand_stamped == "strong"
    strong_blocked_reasons: list[str] = []
    for item in required:
        rejection = item.get("anti_axiom_rejection") or {}
        if rejection.get("mapping_relation") == "conflict_detected":
            strong_blocked_reasons.append(
                f"{item['obligation_id']}: anti-axiom rejection conflict detected"
            )
            continue
        if item["computed"] == "layer_debt":
            strong_blocked_reasons.append(
                f"{item['obligation_id']}: layer_debt {item.get('layer_debt_ref')}"
            )
        elif item.get("negative_case_status") in (None, "absent") and rejection.get("tier") in (None, "absent"):
            strong_blocked_reasons.append(
                f"{item['obligation_id']}: no negative case bound "
                "(strength_scale requires one for 'strong')"
            )
        elif not rejection.get("mapping_verified"):
            relation = rejection.get("mapping_relation", "unmapped")
            strong_blocked_reasons.append(
                f"{item['obligation_id']}: anti-axiom rejection unverified "
                f"(tier {rejection.get('tier')}; relation {relation}; "
                "not mapped to this obligation's anti-axiom slice)"
            )
    return {
        "verdict": verdict,
        "hand_stamped_witness_strength": hand_stamped,
        "hand_stamped_strong_not_certifiable": hand_stamped_strong_not_certifiable,
        "strong_blocked_reasons": strong_blocked_reasons,
    }


def _strong_gate_summary(obligations: list[dict[str, Any]], verdict: dict[str, Any]) -> dict[str, Any]:
    required = [item for item in obligations if item["required"]]
    relations = [
        (item.get("anti_axiom_rejection") or {}).get("mapping_relation", "unmapped")
        for item in required
    ]
    if any(item["computed"] == "blocked_binding_unresolved" for item in required):
        positive_support_status = "blocked_binding_unresolved"
    elif any(item["computed"] == "layer_debt" for item in required):
        positive_support_status = "layer_debt_present"
    elif required and all(item["computed"] == "resolved_strength_uncomputable" for item in required):
        positive_support_status = "resolved_strength_uncomputable"
    else:
        positive_support_status = "unknown"

    if "conflict_detected" in relations:
        rejection_mapping_status = "conflict_detected"
        conflict_status = "conflict_detected"
    elif all((item.get("anti_axiom_rejection") or {}).get("mapping_verified") for item in required):
        rejection_mapping_status = "verified"
        conflict_status = "none"
    elif any(relation not in ("unmapped", "orthogonal") for relation in relations):
        rejection_mapping_status = "partial_or_illustrative_unverified"
        conflict_status = "none"
    else:
        rejection_mapping_status = "unmapped"
        conflict_status = "none"

    if conflict_status != "none":
        strongest_allowed_claim = "blocked_conflict_detected"
    elif positive_support_status == "layer_debt_present":
        strongest_allowed_claim = "partial_capped_by_layer_debt"
    elif rejection_mapping_status != "verified":
        strongest_allowed_claim = "not_strong_rejection_mapping_unverified"
    else:
        strongest_allowed_claim = verdict["verdict"]

    return {
        "positive_support_status": positive_support_status,
        "rejection_mapping_status": rejection_mapping_status,
        "conflict_status": conflict_status,
        "strongest_allowed_claim": strongest_allowed_claim,
    }


def _increment(counter: dict[str, int], key: object) -> None:
    label = str(key if key is not None else "unknown")
    counter[label] = counter.get(label, 0) + 1


def _truth_calculus_summary(
    support_frontiers: dict[str, Any],
    strong_gate_summary: dict[str, Any],
    anti_axiom_rejection_mappings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compact computed truth calculus over all piloted axiom obligations.

    This is the operator-facing rollup for the bilattice split: positive support
    status and anti-axiom rejection status are counted separately, and the final
    claim ceiling is the meet of both. It intentionally reports zero verified
    rejection mappings in v0 instead of laundering receipt coverage into proof.
    """
    verdict_counts: dict[str, int] = {}
    strongest_allowed_claim_counts: dict[str, int] = {}
    positive_support_status_counts: dict[str, int] = {}
    rejection_mapping_status_counts: dict[str, int] = {}
    obligation_computed_counts: dict[str, int] = {}
    anti_axiom_rejection_tier_counts: dict[str, int] = {}
    negative_case_status_counts: dict[str, int] = {}
    mapping_relation_counts: dict[str, int] = {}
    mapping_source_counts: dict[str, int] = {}
    witness_gap_counts: dict[str, int] = {}
    witness_gap_id_counts: dict[str, int] = {}
    per_axiom: list[dict[str, Any]] = []
    verified_rejection_mapping_count = 0
    source_owned_mapping_count = 0
    obligation_count = 0
    required_obligation_count = 0

    for axiom_id in sorted(support_frontiers, key=_axiom_sort_key):
        frontier = support_frontiers[axiom_id]
        obligations = list(frontier.get("obligations", []))
        required = [item for item in obligations if item.get("required")]
        summary = strong_gate_summary.get(axiom_id, {})
        obligation_count += len(obligations)
        required_obligation_count += len(required)
        _increment(verdict_counts, frontier.get("verdict"))
        _increment(positive_support_status_counts, summary.get("positive_support_status"))
        _increment(rejection_mapping_status_counts, summary.get("rejection_mapping_status"))
        _increment(strongest_allowed_claim_counts, summary.get("strongest_allowed_claim"))

        axiom_verified_rejections = 0
        axiom_mapping_relations: dict[str, int] = {}
        axiom_witness_gap_counts: dict[str, int] = {}
        for obligation in obligations:
            _increment(obligation_computed_counts, obligation.get("computed"))
            _increment(negative_case_status_counts, obligation.get("negative_case_status"))
            rejection = obligation.get("anti_axiom_rejection") or {}
            _increment(anti_axiom_rejection_tier_counts, rejection.get("tier"))
            relation = rejection.get("mapping_relation", "unmapped")
            _increment(axiom_mapping_relations, relation)
            for gap in obligation.get("witness_gaps", []):
                _increment(witness_gap_counts, gap.get("gap_class"))
                _increment(witness_gap_id_counts, gap.get("gap_id"))
                _increment(axiom_witness_gap_counts, gap.get("gap_class"))
            if rejection.get("mapping_verified") is True:
                axiom_verified_rejections += 1

        per_axiom.append(
            {
                "axiom_id": axiom_id,
                "verdict": frontier.get("verdict"),
                "positive_support_status": summary.get("positive_support_status"),
                "rejection_mapping_status": summary.get("rejection_mapping_status"),
                "strongest_allowed_claim": summary.get("strongest_allowed_claim"),
                "required_obligation_count": len(required),
                "verified_rejection_mapping_count": axiom_verified_rejections,
                "unverified_required_rejection_mapping_count": len(required)
                - axiom_verified_rejections,
                "mapping_relation_counts": dict(sorted(axiom_mapping_relations.items())),
                "witness_gap_counts": dict(sorted(axiom_witness_gap_counts.items())),
                "hand_stamped_strong_not_certifiable": bool(
                    frontier.get("hand_stamped_strong_not_certifiable")
                ),
            }
        )

    for mapping in anti_axiom_rejection_mappings:
        _increment(mapping_relation_counts, mapping.get("mapping_relation"))
        _increment(mapping_source_counts, mapping.get("mapping_source"))
        if mapping.get("mapping_verified") is True:
            verified_rejection_mapping_count += 1
        if mapping.get("mapping_source") == "source_owned_anti_axiom_rejection_mapping_row":
            source_owned_mapping_count += 1

    return {
        "schema_version": "microcosm_axiom_truth_calculus_summary_v1",
        "axiom_count": len(support_frontiers),
        "obligation_count": obligation_count,
        "required_obligation_count": required_obligation_count,
        "verdict_counts": dict(sorted(verdict_counts.items())),
        "strongest_allowed_claim_counts": dict(sorted(strongest_allowed_claim_counts.items())),
        "positive_support_status_counts": dict(sorted(positive_support_status_counts.items())),
        "rejection_mapping_status_counts": dict(sorted(rejection_mapping_status_counts.items())),
        "obligation_computed_counts": dict(sorted(obligation_computed_counts.items())),
        "negative_case_status_counts": dict(sorted(negative_case_status_counts.items())),
        "anti_axiom_rejection_tier_counts": dict(sorted(anti_axiom_rejection_tier_counts.items())),
        "witness_gap_counts": dict(sorted(witness_gap_counts.items())),
        "witness_gap_id_counts": dict(sorted(witness_gap_id_counts.items())),
        "mapping_relation_counts": dict(sorted(mapping_relation_counts.items())),
        "mapping_source_counts": dict(sorted(mapping_source_counts.items())),
        "source_owned_mapping_count": source_owned_mapping_count,
        "verified_rejection_mapping_count": verified_rejection_mapping_count,
        "verified_rejection_mapping_policy": (
            "zero_is_expected_until_source_rows_and_receipts prove exact_obligation_rejection "
            "or subsumes_obligation for each required obligation"
        ),
        "support_and_rejection_are_separate": True,
        "authority_boundary": (
            "computed_from_source_bindings_receipts_and_checker_material; projection_output_is_not_source_evidence"
        ),
        "claim_ceiling_rule": (
            "The allowed axiom claim is the meet of positive_support_status and "
            "rejection_mapping_status; receipt or endpoint coverage never raises a "
            "rejection mapping without verified source authority."
        ),
        "per_axiom": per_axiom,
    }


def _organ_evidence_chain(root: Path, organ: str) -> dict[str, list[str]]:
    """Resolve an organ's on-disk evidence chain to relative paths that exist."""
    bundles: list[str] = []
    for name in ("bundle_manifest.json", "source_module_manifest.json"):
        for path in sorted((root / EXAMPLES_REL / organ).glob(f"exported_*_bundle/{name}")):
            bundles.append(path.relative_to(root).as_posix())
    receipts: list[str] = []
    receipt_dir = root / RECEIPTS_FIRST_WAVE_REL / organ
    if receipt_dir.is_dir():
        for path in sorted(receipt_dir.glob("*.json")):
            receipts.append(path.relative_to(root).as_posix())
    return {"example_bundle_refs": bundles, "receipt_refs": receipts}


def _basis_digest_for_refs(root: Path, refs: list[str]) -> str:
    digest = hashlib.sha256()
    for ref in sorted(set(refs)):
        digest.update(ref.encode("utf-8"))
        try:
            digest.update((root / ref.split("::", 1)[0]).read_bytes())
        except OSError:
            digest.update(b"<missing>")
    return "sha256:" + digest.hexdigest()


def _compile_support_case(
    obligation: dict[str, Any],
    row: dict[str, Any],
    root: Path,
    by_organ: dict[str, dict[str, Any]],
    dimension_registry: dict[str, Any],
) -> dict[str, Any]:
    """Compile one obligation binding into a citation/attestation envelope.

    The envelope cites only material that resolves on disk (PROV/SLSA-style: point
    at artifacts, do not re-prove them). It populates the registry order-owned
    ceiling components and leaves explicitly unowned components unknown.
    """
    binding = obligation.get("binding", {})
    organs = list(binding.get("witness_organs", []))
    surfaces = list(binding.get("witness_surfaces", []))
    negatives = list(binding.get("negative_case_codes", []))

    example_bundle_refs: list[str] = []
    receipt_refs: list[str] = []
    for organ in organs:
        chain = _organ_evidence_chain(root, organ)
        example_bundle_refs.extend(chain["example_bundle_refs"])
        receipt_refs.extend(chain["receipt_refs"])
    example_bundle_refs = sorted(set(example_bundle_refs))
    receipt_refs = sorted(set(receipt_refs))

    evidence_class = _evidence_class_component(binding, by_organ)
    checker_scope = _checker_scope_component(
        binding, root, dimension_registry.get("checker_scope_order")
    )
    authority_scope = _authority_scope_component(
        binding, dimension_registry.get("authority_scope_order")
    )
    projection_scope = _projection_scope_component(
        binding, dimension_registry.get("projection_scope_order")
    )
    freshness_state = _freshness_state_component(
        dimension_registry.get("freshness_state_order")
    )
    domain_scope = _domain_scope_component(
        binding, dimension_registry.get("domain_scope_order")
    )
    provenance_class = _provenance_class_component(
        binding, root, dimension_registry.get("provenance_order")
    )
    ceiling_vector = _ceiling_vector(binding, root, by_organ, dimension_registry)

    declared = obligation.get("coverage_status")
    relation_kind = "partial_witness_layer_debt" if declared == "layer_debt" else "bound_witness"
    anti_claims = ["Support case is a citation/attestation envelope, not certified strength."]
    if obligation.get("layer_debt_ref"):
        anti_claims.append(
            f"Does not close layer debt {obligation['layer_debt_ref']}; caps the axiom, does not weaken it."
        )

    material_refs = sorted(set(surfaces) | set(example_bundle_refs) | set(receipt_refs))
    return {
        "case_id": f"{obligation.get('obligation_id')}.support_case",
        "axiom_ref": row["axiom_id"],
        "obligation_ref": obligation.get("obligation_id"),
        "relation_kind": relation_kind,
        "subject": f"claim:{obligation.get('obligation_id')}",
        "code_logic": {
            "predicate": obligation.get("predicate"),
            "checker_boundary": (
                "declared witness debt; checker does not yet close the obligation"
                if declared == "layer_debt"
                else "bounded checker witness over the declared domain, not general proof"
            ),
        },
        "materials": {
            "witness_organs": organs,
            "source_refs": surfaces,
            "example_bundle_refs": example_bundle_refs,
            "receipt_refs": receipt_refs,
            "negative_case_refs": negatives,
            "checker_provenance_refs": [f"core/organ_registry.json#{organ}" for organ in organs],
        },
        "evidence_class_component": evidence_class,
        "checker_scope_component": checker_scope,
        "authority_scope_component": authority_scope,
        "projection_scope_component": projection_scope,
        "freshness_state_component": freshness_state,
        "domain_scope_component": domain_scope,
        "provenance_class_component": provenance_class,
        "ceiling_vector": ceiling_vector,
        "basis_env": {
            "basis_digest": _basis_digest_for_refs(root, material_refs),
            "rederive": "python -m microcosm_core.validators.axiom_support_cover --root <microcosm-substrate>",
            "as_of": "see basis_digest; timestamp intentionally omitted for reproducibility",
            "declared_domain": row.get("title"),
        },
        "anti_claims": anti_claims,
    }


def evaluate_axiom_support_cover(public_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(public_root).resolve() if public_root is not None else _default_root()
    routing = read_json_strict(root / ROUTING_REL)
    rows = routing.get("rows", []) if isinstance(routing, dict) else []
    dimension_registry = _ceiling_dimension_registry(root)
    organ_ids = _registry_organ_ids(root)
    by_organ = _evidence_class_by_organ(root)

    # principle -> grounding axioms (reverse of row.principle_ids), over ALL rows.
    principle_to_axioms: dict[str, list[str]] = {}
    for row in rows:
        for principle_id in row.get("principle_ids", []):
            principle_to_axioms.setdefault(principle_id, []).append(row["axiom_id"])

    support_frontiers: dict[str, Any] = {}
    pressures: list[dict[str, Any]] = []
    witness_violations: list[dict[str, Any]] = []

    piloted_axioms: list[str] = []
    support_cases: list[dict[str, Any]] = []
    anti_axiom_rejection_mappings: list[dict[str, Any]] = []
    strong_gate_summary: dict[str, Any] = {}
    obligation_index_by_axiom: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        obligations = row.get("obligations")
        if not obligations:
            continue
        axiom_id = row["axiom_id"]
        piloted_axioms.append(axiom_id)
        evaluated = [
            _evaluate_obligation(
                obligation, row, root, organ_ids, by_organ, dimension_registry
            )
            for obligation in obligations
        ]
        verdict = _axiom_verdict(evaluated, row.get("witness_strength"))
        support_frontiers[axiom_id] = {"obligations": evaluated, **verdict}
        obligation_index_by_axiom[axiom_id] = {
            str(item.get("obligation_id")): item for item in evaluated
        }
        strong_gate_summary[axiom_id] = _strong_gate_summary(evaluated, verdict)
        support_frontiers[axiom_id]["claim_ceiling"] = {
            "schema_version": "microcosm_axiom_node_claim_ceiling_v1",
            "computed_by": CHECKER_ID,
            "positive_support_status": strong_gate_summary[axiom_id][
                "positive_support_status"
            ],
            "rejection_mapping_status": strong_gate_summary[axiom_id][
                "rejection_mapping_status"
            ],
            "strongest_allowed_claim": strong_gate_summary[axiom_id][
                "strongest_allowed_claim"
            ],
            "strong_certified": False,
            "authority_boundary": (
                "node ceiling is computed as the meet of obligation support and "
                "anti-axiom rejection mapping status; generated projections do not "
                "raise source support"
            ),
        }
        anti_axiom_rejection_mappings.extend(
            (item.get("anti_axiom_rejection") or {}).get("mapping", {})
            for item in evaluated
            if (item.get("anti_axiom_rejection") or {}).get("mapping")
        )
        for obligation in obligations:
            support_cases.append(
                _compile_support_case(obligation, row, root, by_organ, dimension_registry)
            )

        for item in evaluated:
            # principles must never appear as witnesses (AX-12 / claim-ceiling guard).
            binding = next(
                (o.get("binding", {}) for o in obligations if o.get("obligation_id") == item["obligation_id"]),
                {},
            )
            for ref_list_key in ("witness_organs", "witness_surfaces", "negative_case_codes"):
                for ref in binding.get(ref_list_key, []):
                    if isinstance(ref, str) and ref.startswith("P-") and ref[2:].split(".")[0].isdigit():
                        witness_violations.append(
                            {"axiom_ref": axiom_id, "obligation_ref": item["obligation_id"], "principle_ref": ref}
                        )
            if item["computed"] == "layer_debt":
                pressures.append(
                    {
                        "pressure_type": "witness_debt",
                        "axiom_ref": axiom_id,
                        "obligation_ref": item["obligation_id"],
                        "layer_debt_ref": item["layer_debt_ref"],
                        "forbidden_action": "do_not_lower_axiom_bar_to_make_coverage_green",
                        "recommended_route": "candidate_axiom_curation_or_witness_work",
                    }
                )
            elif item["computed"] == "blocked_binding_unresolved":
                pressures.append(
                    {
                        "pressure_type": "witness_debt",
                        "axiom_ref": axiom_id,
                        "obligation_ref": item["obligation_id"],
                        "detail": item["binding_issues"],
                        "recommended_route": "fix_binding_or_declare_layer_debt",
                    }
                )
            rejection = item.get("anti_axiom_rejection") or {}
            if item.get("required") and not rejection.get("mapping_verified"):
                mapping = rejection.get("mapping") or {}
                mapping_source = mapping.get("mapping_source", "evaluator_inferred_fallback")
                source_owned = mapping_source == "source_owned_anti_axiom_rejection_mapping_row"
                pressures.append(
                    {
                        "pressure_type": "rejection_mapping_debt",
                        "axiom_ref": axiom_id,
                        "obligation_ref": item["obligation_id"],
                        "mapping_relation": rejection.get("mapping_relation", "unmapped"),
                        "mapping_source": mapping_source,
                        "detail": mapping.get("reason"),
                        "forbidden_action": "do_not_lower_axiom_bar_to_make_coverage_green",
                        "mapping_forbidden_action": "do_not_launder_receipt_coverage_into_obligation_rejection",
                        "next_required_authority": (
                            "receipt-level per-obligation mapping fields or a stronger exact/subsuming row"
                            if source_owned
                            else "source-owned exact/subsuming mapping row or receipt-level "
                            "per-obligation mapping fields"
                        ),
                        "recommended_route": (
                            "receipt_level_per_obligation_rejection_evidence"
                            if source_owned
                            else "source_owned_anti_axiom_rejection_mapping_rows"
                        ),
                    }
                )
        if verdict["hand_stamped_strong_not_certifiable"]:
            pressures.append(
                {
                    "pressure_type": "sharpen",
                    "axiom_ref": axiom_id,
                    "detail": (
                        "row witness_strength='strong' but the evaluator cannot certify strong; "
                        "either build the missing ceiling-dimension order owners plus a negative-case "
                        "gate, or demote the row claim"
                    ),
                    "forbidden_action": "do_not_lower_axiom_bar_to_make_coverage_green",
                    "recommended_route": "candidate_axiom_curation",
                }
            )

    missing_dimensions = list(dimension_registry["explicitly_unowned"])
    if piloted_axioms and missing_dimensions:
        pressures.append(
            {
                "pressure_type": "extend",
                "scope": "evaluator_dimensions",
                "detail": (
                    f"{len(missing_dimensions)}/{len(dimension_registry['component_order'])} ceiling "
                    "components are source-registered unowned in "
                    f"{CEILING_DIMENSIONS_REL.as_posix()}: {missing_dimensions}. Full antichain "
                    "support frontiers are not computable until those owners exist."
                ),
                "recommended_route": "reuse_existing_owners_or_add_axiom_support_dimensions_registry",
            }
        )
    freshness_gap_count = sum(
        1
        for frontier in support_frontiers.values()
        for obligation in frontier.get("obligations", [])
        for gap in obligation.get("witness_gaps", [])
        if gap.get("gap_id") == "ceiling_component_uncomputed:freshness_state"
    )
    if freshness_gap_count:
        pressures.append(
            {
                "pressure_type": "freshness_debt",
                "scope": "evaluator_dimensions",
                "detail": (
                    f"{freshness_gap_count} axiom obligations have an order-owned "
                    "freshness_state component that remains unknown because no "
                    "source-owned refresh contract is bound."
                ),
                "forbidden_action": "do_not_treat_basis_digest_as_live_freshness_proof",
                "recommended_route": "add_source_owned_axiom_support_refresh_contract",
            }
        )

    principle_to_obligations = _principle_obligation_groundings(root)
    principle_support_index = []
    for principle_id, axioms in sorted(principle_to_axioms.items()):
        piloted_grounding = [axiom for axiom in axioms if axiom in support_frontiers]
        if not piloted_grounding:
            continue
        source_obligation_refs = principle_to_obligations.get(principle_id, [])
        obligation_refs_by_axiom = {
            axiom: [
                obligation_ref
                for obligation_ref in source_obligation_refs
                if obligation_ref.startswith(axiom + ".")
            ]
            for axiom in piloted_grounding
        }
        unresolved_obligation_refs = []
        for obligation_ref in source_obligation_refs:
            axiom_ref = obligation_ref.split(".", 1)[0]
            if obligation_ref not in obligation_index_by_axiom.get(axiom_ref, {}):
                unresolved_obligation_refs.append(obligation_ref)
        inherited_obligation_statuses = {
            obligation_ref: obligation_index_by_axiom[axiom][obligation_ref]["computed"]
            for axiom, obligation_refs in obligation_refs_by_axiom.items()
            for obligation_ref in obligation_refs
            if obligation_ref in obligation_index_by_axiom.get(axiom, {})
        }
        grounding_granularity = (
            "obligation_level_source_owned"
            if source_obligation_refs and not unresolved_obligation_refs
            else "axiom_level_only_obligation_level_grounding_not_in_data_yet"
        )
        principle_support_index.append(
            {
                "principle_id": principle_id,
                "grounding_axioms": axioms,
                "piloted_grounding_axioms": piloted_grounding,
                "grounding_obligation_refs": source_obligation_refs,
                "grounding_obligation_refs_by_axiom": obligation_refs_by_axiom,
                "unresolved_grounding_obligation_refs": unresolved_obligation_refs,
                "inherited_obligation_statuses": inherited_obligation_statuses,
                "inherited_support_verdicts": {
                    axiom: support_frontiers[axiom]["verdict"] for axiom in piloted_grounding
                },
                "grounding_granularity": grounding_granularity,
                "anti_claims": [
                    "This principle governs behavior; it does not witness the axiom.",
                    "Principle support is bounded by its grounding obligations and never amplifies them.",
                ],
            }
        )

    return {
        "schema_version": "microcosm_axiom_support_cover_v0",
        "checker_id": CHECKER_ID,
        "authority_posture": "read_only_evaluator_projection_not_source_of_record",
        "status": "computed",
        "piloted_axioms": sorted(piloted_axioms),
        "support_frontiers": support_frontiers,
        "support_cases": support_cases,
        "anti_axiom_rejection_mappings": anti_axiom_rejection_mappings,
        "strong_gate_summary": strong_gate_summary,
        "truth_calculus_summary": _truth_calculus_summary(
            support_frontiers, strong_gate_summary, anti_axiom_rejection_mappings
        ),
        "ceiling_dimension_registry": {
            "schema_version": dimension_registry["payload"].get("schema_version"),
            "source_ref": dimension_registry["source_ref"],
            "component_order": list(dimension_registry["component_order"]),
            "order_owned_component_ids": list(dimension_registry["order_owned"]),
            "explicitly_unowned_component_ids": list(dimension_registry["explicitly_unowned"]),
            "unknown_no_order_owner_count": len(dimension_registry["explicitly_unowned"]),
            "basis_digest": dimension_registry["basis_digest"],
            "authority_boundary": dimension_registry["payload"].get("authority_boundary"),
        },
        "principle_support_index": principle_support_index,
        "candidate_axiom_pressure": pressures,
        "principle_as_witness_violations": witness_violations,
        "coverage_state_semantics": {
            "blocked": "in declared domain, a required obligation has no admissible support (AX-5 fail-closed)",
            "layer_debt": "required obligation declared as known witness debt; caps the axiom, does not weaken it",
            "unknown_no_order_owner": (
                "a source-registered explicitly unowned ceiling component cannot be ordered yet "
                "(AX-6); not bottom, not strong"
            ),
        },
        "self_attestation": {
            "basis_digest": _basis_digest(
                root,
                (
                    ROUTING_REL,
                    EVIDENCE_CLASSES_REL,
                    ORGAN_REGISTRY_REL,
                    AXIOM_STANDARD_REL,
                    CEILING_DIMENSIONS_REL,
                    CHECKER_SCOPE_ORDER_REL,
                    AUTHORITY_SCOPE_ORDER_REL,
                    PROJECTION_SCOPE_ORDER_REL,
                    FRESHNESS_STATE_ORDER_REL,
                    DOMAIN_SCOPE_ORDER_REL,
                    PROVENANCE_ORDER_REL,
                ),
            ),
            "basis_refs": [
                ROUTING_REL.as_posix(),
                EVIDENCE_CLASSES_REL.as_posix(),
                ORGAN_REGISTRY_REL.as_posix(),
                AXIOM_STANDARD_REL.as_posix(),
                CEILING_DIMENSIONS_REL.as_posix(),
                CHECKER_SCOPE_ORDER_REL.as_posix(),
                AUTHORITY_SCOPE_ORDER_REL.as_posix(),
                PROJECTION_SCOPE_ORDER_REL.as_posix(),
                FRESHNESS_STATE_ORDER_REL.as_posix(),
                DOMAIN_SCOPE_ORDER_REL.as_posix(),
                PROVENANCE_ORDER_REL.as_posix(),
            ],
            "rederive": "python -m microcosm_core.validators.axiom_support_cover --root <microcosm-substrate>",
            "as_of": "see basis_digest; timestamp intentionally omitted for reproducibility",
        },
        "anti_claims": [
            "This evaluator computes bounded support from existing pilot bindings; it does not certify "
            "'strong', authorize release, or mutate axioms.",
            "Generated output is a projection below source authority and is never evidence for itself (AX-12).",
            "No ceiling components are source-registered unowned; freshness_state is order-owned but still "
            "computes an unknown live-freshness value until a source-owned refresh contract exists.",
            "A blocked or layer-debt obligation is candidate-axiom pressure or witness debt, never a license "
            "to weaken the axiom so coverage turns green.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=None, help="Path to the microcosm-substrate root.")
    parser.add_argument("--out", help="Optional JSON receipt path.")
    args = parser.parse_args(argv)

    receipt = evaluate_axiom_support_cover(args.root)
    if args.out:
        Path(args.out).write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    else:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
