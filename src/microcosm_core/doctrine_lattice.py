"""
[PURPOSE]
Maintain Microcosm doctrine-lattice projections from governed source registries rather than hand-authored generated surfaces.

[INTERFACE]
Expose builders, validators, writers, and a CLI for axiom, principle, anti-principle, concept, mechanism, organ, skill, standard, and paper-module corpora.

[FLOW]
Load strict JSON and markdown source authority, derive expected instance corpora, validate on-disk projections, write generated JSON/Markdown/Mermaid surfaces, and report residual health.

[DEPENDENCIES]
Read the Microcosm resource root, strict JSON schema helpers, relation registries, accepted organ/source registries, and the axiom support-cover validator.

[CONSTRAINTS]
Treat lattice nodes as projections, keep public surfaces bounded by leak checks, and raise mismatches instead of silently accepting stale doctrine state.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from microcosm_core.resource_root import microcosm_root
from microcosm_core.schemas import loads_json_strict, read_json_strict
from microcosm_core.validators.axiom_support_cover import evaluate_axiom_support_cover


KIND_STANDARD_IDS = (
    "axiom",
    "principle",
    "anti_principle",
    "concept",
    "mechanism",
    "paper_module",
    "organ",
    "skill",
    "standard",
)
SOURCE_INSTANCE_NODE_AUTHORITY_BOUNDARIES = {
    kind: f"generated_projection_node_from_{kind}_instance_not_source_authority"
    for kind in KIND_STANDARD_IDS
}

SKILL_TRIAD = ("author", "refine_instance", "refine_standard_and_propagate")
VALIDATION_TRIAD = ("schema_check", "link_resolution", "projection_freshness")
PROJECTION_TRIAD = ("markdown", "mermaid", "atlas_card")
CARDINALITY_ENUM = ("one_to_one", "one_to_many", "zero_to_one", "zero_to_many")
REQUIREMENT_ENUM = ("required", "selective", "forbidden", "planned")
TARGET_RESOLUTION_ENUM = ("resolve_when_present", "must_resolve_or_marked_planned")
MECHANISM_RESOLUTION_ENUM = ("resolved", "planned_unresolved")
CODE_LOCUS_RESOLUTION_ENUM = ("resolved", "planned")
RELATION_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
PAPER_MODULE_CAPSULES_REL = "core/paper_module_capsules.json"
MECHANISM_REGISTRY_REL = "core/mechanism_sources.json"
PUBLIC_SURFACE_MANIFEST_REL = "core/public_surface_manifest.json"
CONCEPT_ENTRY_PACKET_REL = "atlas/entry_packet.json"
ENTRY_CARD_REL = "atlas/doctrine_lattice_entry_card.json"
AXIOM_ROUTING_REL = "core/axiom_organ_routing.json"
AXIOM_INSTANCE_DIR_REL = "axioms"
AXIOM_INSTANCE_SCHEMA_VERSION = "microcosm_axiom_instance_v1"
AXIOM_MIGRATION_CREATED_AT = "2026-06-02T00:00:00Z"
PRINCIPLES_REL = "PRINCIPLES.md"
ANTI_PRINCIPLES_REL = "ANTI_PRINCIPLES.md"
PRINCIPLE_INSTANCE_DIR_REL = "principles"
ANTI_PRINCIPLE_INSTANCE_DIR_REL = "anti_principles"
DOCTRINE_RECORD_RECEIPT_DIR_REL = "receipts/doctrine_records"
CONCEPT_MECHANISM_RECORDS_POPULATION_RECEIPT_REL = (
    "receipts/concept_mechanism_population/"
    "concept_mechanism_records_population_receipt_20260605T1735Z.json"
)
PRINCIPLE_INSTANCE_SCHEMA_VERSION = "microcosm_principle_instance_v1"
ANTI_PRINCIPLE_INSTANCE_SCHEMA_VERSION = "microcosm_anti_principle_instance_v1"
CONCEPT_INSTANCE_DIR_REL = "concepts"
MECHANISM_INSTANCE_DIR_REL = "mechanisms"
CONCEPT_INSTANCE_SCHEMA_VERSION = "microcosm_concept_instance_v1"
MECHANISM_INSTANCE_SCHEMA_VERSION = "microcosm_mechanism_instance_v1"
ORGAN_INSTANCE_DIR_REL = "organs"
ORGAN_INSTANCE_SCHEMA_VERSION = "microcosm_organ_instance_v1"
PAPER_MODULE_INSTANCE_DIR_REL = "paper_modules"
PAPER_MODULE_INSTANCE_SCHEMA_VERSION = "microcosm_paper_module_instance_v1"
SKILL_INSTANCE_DIR_REL = "skills"
SKILL_INSTANCE_SCHEMA_VERSION = "microcosm_skill_instance_v1"
STANDARD_INSTANCE_DIR_REL = "standards"
STANDARD_INSTANCE_SCHEMA_VERSION = "microcosm_standard_instance_projection_v1"
DOCTRINE_PROJECTION_REL = "atlas/doctrine_lattice_projection.json"
DOCTRINE_GRAPH_REL = "atlas/doctrine_lattice_graph.mmd"
DOCTRINE_HEALTH_REL = "atlas/doctrine_lattice_health.json"
SOURCE_FILES = (
    PRINCIPLES_REL,
    ANTI_PRINCIPLES_REL,
    AXIOM_ROUTING_REL,
    "core/organ_registry.json",
    "core/organ_atlas.json",
    "core/standards_registry.json",
    "core/doctrine_lattice_relations.json",
    PAPER_MODULE_CAPSULES_REL,
    MECHANISM_REGISTRY_REL,
    CONCEPT_ENTRY_PACKET_REL,
    PUBLIC_SURFACE_MANIFEST_REL,
)
PRIORITY_ORGAN_TARGETS = (
    (
        "verifier_lab_kernel",
        "Evidence rank 5 semantic validator and formal-math composition root.",
    ),
    (
        "navigation_hologram_route_plane",
        "Evidence rank 5 semantic validator and architecture/navigation backbone.",
    ),
    (
        "macro_projection_import_protocol",
        "Evidence rank 5 verified macro-body import and import gateway.",
    ),
    (
        "agent_route_observability_runtime",
        "Evidence rank 5 semantic validator and route/observability consumer.",
    ),
    (
        "pattern_binding_contract",
        "Evidence rank 5 semantic validator and pattern route-readiness root.",
    ),
    (
        "proof_diagnostic_evidence_spine",
        "Formal-math diagnostic evidence checkpoint hub.",
    ),
    (
        "durable_agent_work_landing_replay",
        "Canonical landing-contract validator paired with mission work spine.",
    ),
)


def _now() -> str:
    """
    - Teleology: stamp a single UTC ISO timestamp for generation receipts.
    - Guarantee: returns the current UTC time as an ISO-8601 string with a trailing 'Z'.
    - Fails: never raises; always returns a string.
    """
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _json(value: Any) -> Any:
    """
    - Teleology: defensively snapshot a value so emitted payloads never alias mutable source objects.
    - Guarantee: returns a deep copy of the input value.
    - Fails: raises only if copy.deepcopy fails on an uncopyable object; otherwise returns a copy.
    """
    return copy.deepcopy(value)


def _source_instance_node_authority_boundary(kind: str) -> str:
    """
    - Teleology: stamp the authority-boundary label that marks a projection node as derived, not source authority.
    - Guarantee: returns the registered boundary string for the kind, or an explicit unknown-kind boundary string.
    - Fails: never raises; unknown kinds yield the 'generated_projection_node_from_unknown_kind' fallback.
    """
    return SOURCE_INSTANCE_NODE_AUTHORITY_BOUNDARIES.get(
        kind,
        "generated_projection_node_from_unknown_kind_not_source_authority",
    )


def _as_dict(value: Any) -> dict[str, Any]:
    """
    - Teleology: coerce untrusted JSON into a dict without raising on the wrong shape.
    - Guarantee: returns the value unchanged if it is a dict, else an empty dict.
    - Fails: never raises; non-dict input yields {}.
    """
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    """
    - Teleology: coerce untrusted JSON into a list without raising on the wrong shape.
    - Guarantee: returns the value unchanged if it is a list, else an empty list.
    - Fails: never raises; non-list input yields [].
    """
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    """
    - Teleology: extract only the non-empty string members of an untrusted list.
    - Guarantee: returns a list of the stripped-non-empty str items from the input list, preserving order.
    - Fails: never raises; non-list or non-string members are dropped.
    """
    return [item for item in _as_list(value) if isinstance(item, str) and item.strip()]


def _has_resolved_relation(
    edges: list[Any],
    relation_id: str,
    resolved_statuses: set[str],
) -> bool:
    """
    - Teleology: test whether an edge list already carries a resolved edge for a given relation id.
    - Guarantee: returns True iff some edge dict has the relation_id and a target_status in resolved_statuses.
    - Fails: never raises; returns False when no such edge exists.
    """
    return any(
        isinstance(edge, dict)
        and edge.get("relation_id") == relation_id
        and edge.get("target_status") in resolved_statuses
        for edge in edges
    )


def _organ_required_edge_gap_detail_rows(
    organ_instances: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    - Teleology: enumerate, per organ instance, which required/law lattice relations are missing or unresolved.
    - Guarantee: returns one detail row per organ that has a missing required relation or missing law binding, sorted by organ id; organs with full coverage are omitted.
    - Fails: never raises; organs without an id or without gaps are skipped, yielding fewer or zero rows.
    - When-needed: building organ coverage health or explaining why an organ blocks population.
    - Escalates-to: build_organ_instance_corpus, build_lattice_health, organ instance JSON under organs/*.json.
    """
    required_statuses = {
        "resolved_paper_module_ref",
        "resolved_json_instance",
        "resolved_code_locus",
    }
    required_relation_ids = {
        "organ.explained_by.paper_module",
        "organ.operates_through.mechanism",
        "organ.implemented_by.code_locus",
    }
    law_relation_to_source_field = {
        "organ.constrained_by.axiom": "axiom_refs",
        "organ.governed_by.principle": "principle_refs",
    }
    source_field_by_relation = {
        "organ.explained_by.paper_module": "paper_module_ref",
        "organ.operates_through.mechanism": "mechanism_refs",
        "organ.implemented_by.code_locus": "code_loci",
        **law_relation_to_source_field,
    }
    rows: list[dict[str, Any]] = []
    for instance in organ_instances:
        organ_id = str(instance.get("id") or "")
        if not organ_id:
            continue
        relationships = _as_dict(instance.get("relationships"))
        edges = _as_list(relationships.get("edges"))
        residuals = [
            residual
            for residual in _as_list(relationships.get("unpopulated_selective_relations"))
            if isinstance(residual, dict)
        ]
        required_residuals = [
            residual
            for residual in residuals
            if residual.get("requirement") == "required"
            and residual.get("relation_id") in required_relation_ids
        ]
        missing_required_relation_ids = {
            str(residual.get("relation_id"))
            for residual in required_residuals
            if residual.get("relation_id")
        }
        unresolved_required_relation_ids = {
            str(edge.get("relation_id"))
            for edge in edges
            if isinstance(edge, dict)
            and edge.get("relation_id") in required_relation_ids
            and edge.get("target_status") not in required_statuses
        }
        resolved_required_relation_ids = {
            str(edge.get("relation_id"))
            for edge in edges
            if isinstance(edge, dict)
            and edge.get("relation_id") in required_relation_ids
            and edge.get("target_status") in required_statuses
        }
        missing_required_relation_ids.update(unresolved_required_relation_ids)

        missing_law_relation_ids: set[str] = set()
        if not _strings(instance.get("axiom_refs")) and not _has_resolved_relation(
            edges,
            "organ.constrained_by.axiom",
            {"resolved_json_instance"},
        ):
            missing_law_relation_ids.add("organ.constrained_by.axiom")
        if not _strings(instance.get("principle_refs")) and not _has_resolved_relation(
            edges,
            "organ.governed_by.principle",
            {"resolved_json_instance"},
        ):
            missing_law_relation_ids.add("organ.governed_by.principle")

        if not missing_required_relation_ids and not missing_law_relation_ids:
            continue

        relevant_relation_ids = missing_required_relation_ids | missing_law_relation_ids
        relevant_residuals = [
            residual
            for residual in residuals
            if residual.get("relation_id") in relevant_relation_ids
        ]
        rows.append({
            "organ_id": organ_id,
            "missing_required_relation_ids": sorted(
                missing_required_relation_ids,
                key=_id_sort_key,
            ),
            "missing_selective_law_relation_ids": sorted(
                missing_law_relation_ids,
                key=_id_sort_key,
            ),
            "resolved_required_relation_ids": sorted(
                resolved_required_relation_ids,
                key=_id_sort_key,
            ),
            "missing_source_authority_fields": sorted(
                {
                    source_field_by_relation[relation_id]
                    for relation_id in relevant_relation_ids
                    if relation_id in source_field_by_relation
                },
                key=_id_sort_key,
            ),
            "residual_pressure_refs": sorted(
                {
                    str(residual.get("pressure_ref"))
                    for residual in relevant_residuals
                    if residual.get("pressure_ref")
                },
                key=_id_sort_key,
            ),
            "residual_reasons": sorted(
                {
                    str(residual.get("reason"))
                    for residual in relevant_residuals
                    if residual.get("reason")
                },
                key=_id_sort_key,
            ),
            "source_atlas_row_ref": relationships.get("source_atlas_row_ref"),
            "source_registry_row_ref": relationships.get("source_registry_row_ref"),
            "authority_boundary": (
                "computed_from_organ_json_residuals_not_source_edge_resolution_or_law_binding"
            ),
        })
    return sorted(rows, key=lambda row: _id_sort_key(str(row["organ_id"])))


def _path(root: str | Path | None, rel: str) -> Path:
    """
    - Teleology: resolve a repo-relative path against the chosen or default microcosm root.
    - Guarantee: returns an absolute Path of root/rel, using microcosm_root() when root is None.
    - Fails: never raises here; non-existence is the caller's concern.
    """
    resolved = Path(root).resolve() if root is not None else microcosm_root()
    return resolved / rel


def _root_key(root: str | Path | None) -> str:
    """
    - Teleology: produce a stable string cache key for a root argument.
    - Guarantee: returns the resolved root path rendered as a string.
    - Fails: never raises.
    """
    return str(_root(root))


@lru_cache(maxsize=512)
def _read_source_json_cached(root_key: str, rel: str) -> Any:
    """
    - Teleology: lru-cached strict JSON read so repeated source reads do not re-parse disk.
    - Guarantee: returns the strictly-parsed JSON value for root_key/rel; identical args return the cached value.
    - Fails: propagates read_json_strict errors (missing file / malformed JSON) on first read of a key.
    - Escalates-to: microcosm_core.schemas.read_json_strict.
    """
    return read_json_strict(Path(root_key) / rel)


def _load(root: str | Path | None, rel: str) -> Any:
    """
    - Teleology: load a source JSON file relative to root via the read cache.
    - Guarantee: returns the parsed JSON value for root/rel.
    - Fails: propagates read_json_strict errors when the file is missing or malformed.
    """
    return _read_source_json_cached(_root_key(root), rel)


def _sha256(path: Path) -> str:
    """
    - Teleology: content-hash a file for source-digest freshness receipts.
    - Guarantee: returns the hex sha256 of the file's bytes, streamed in 1 MiB chunks.
    - Fails: raises OSError if the path cannot be opened/read.
    """
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_json(value: Any) -> str:
    """
    - Teleology: content-hash a JSON-serializable value with canonical key order for stable digests.
    - Guarantee: returns the hex sha256 of the sorted-keys compact UTF-8 JSON encoding of the value.
    - Fails: raises TypeError if the value is not JSON-serializable.
    """
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _standard_rel(kind: str) -> str:
    """
    - Teleology: compute the standards-dir relative path for a kind's std_microcosm_<kind>.json.
    - Guarantee: returns 'standards/std_microcosm_<kind>.json'.
    - Fails: never raises.
    """
    return f"standards/std_microcosm_{kind}.json"


def source_file_digests(root: str | Path | None = None) -> dict[str, str]:
    """
    [ACTION]
    - Teleology: build the source freshness fingerprint set for the whole doctrine-lattice source surface.
    - Guarantee: returns {relative_path: sha256_hex} for every existing source/standard/instance file under root.
    - Fails: never raises for missing files (they are filtered out); raises OSError only if an existing file cannot be read.
    - When-needed: computing projection_freshness to detect stale generated artifacts.
    - Escalates-to: build_coverage_projection projection_freshness block.
    """
    files = list(SOURCE_FILES) + [_standard_rel(kind) for kind in KIND_STANDARD_IDS]
    resolved = _root(root)
    for instance_dir_rel in (
        AXIOM_INSTANCE_DIR_REL,
        PRINCIPLE_INSTANCE_DIR_REL,
        ANTI_PRINCIPLE_INSTANCE_DIR_REL,
        CONCEPT_INSTANCE_DIR_REL,
        MECHANISM_INSTANCE_DIR_REL,
        ORGAN_INSTANCE_DIR_REL,
        PAPER_MODULE_INSTANCE_DIR_REL,
        SKILL_INSTANCE_DIR_REL,
    ):
        instance_dir = resolved / instance_dir_rel
        if instance_dir.is_dir():
            files.extend(
                path.relative_to(resolved).as_posix()
                for path in sorted(instance_dir.glob("*.json"))
            )
    skill_dir = resolved / SKILL_INSTANCE_DIR_REL
    if skill_dir.is_dir():
        files.extend(
            path.relative_to(resolved).as_posix()
                for path in sorted(skill_dir.glob("*.md"))
            if not path.name.endswith(".generated.md")
        )
    standard_dir = resolved / STANDARD_INSTANCE_DIR_REL
    if standard_dir.is_dir():
        files.extend(
            path.relative_to(resolved).as_posix()
            for path in sorted(standard_dir.glob("std_microcosm_*.json"))
        )
    return {rel: _sha256(_path(root, rel)) for rel in files if _path(root, rel).is_file()}


def load_kind_standards(root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: load the nine per-kind std_microcosm_*.json contract documents.
    - Guarantee: returns {kind: standard_dict} for every kind in KIND_STANDARD_IDS, empty dict for any kind whose file is missing/non-dict.
    - Fails: propagates read_json_strict errors when a standard file is present but malformed.
    - When-needed: validating contracts, reading required_fields, or building instances.
    - Escalates-to: standards/std_microcosm_<kind>.json.
    """
    return _load_kind_standards_cached(_root_key(root))


@lru_cache(maxsize=32)
def _load_kind_standards_cached(root_key: str) -> dict[str, dict[str, Any]]:
    """
    - Teleology: lru-cached backend for load_kind_standards keyed by root string.
    - Guarantee: returns the kind->standard dict; identical root_key returns the cached mapping.
    - Fails: propagates read_json_strict errors on first read of a malformed standard.
    """
    return {
        kind: _as_dict(_read_source_json_cached(root_key, _standard_rel(kind)))
        for kind in KIND_STANDARD_IDS
    }


def load_relation_registry(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: load the relation registry that defines allowed source.verb.target lattice relations.
    - Guarantee: returns the relation registry as a dict (empty dict if the file is missing or not a dict).
    - Fails: propagates read_json_strict errors if the registry file is malformed.
    - Escalates-to: core/doctrine_lattice_relations.json.
    """
    return _as_dict(_load(root, "core/doctrine_lattice_relations.json"))


@lru_cache(maxsize=512)
def _load_optional_dict_cached(root_key: str, rel: str) -> dict[str, Any]:
    """
    - Teleology: lru-cached optional dict read that tolerates absent files.
    - Guarantee: returns {} if the file is absent, else the parsed dict (empty dict if not a dict).
    - Fails: propagates read_json_strict errors only when the file exists but is malformed.
    """
    path = Path(root_key) / rel
    if not path.is_file():
        return {}
    return _as_dict(_read_source_json_cached(root_key, rel))


def _load_optional_dict(root: str | Path | None, rel: str) -> dict[str, Any]:
    """
    - Teleology: load an optional source dict relative to root, tolerating absence.
    - Guarantee: returns the parsed dict, or {} if the file does not exist.
    - Fails: propagates read_json_strict errors when an existing file is malformed.
    """
    return _load_optional_dict_cached(_root_key(root), rel)


def _root(root: str | Path | None) -> Path:
    """
    - Teleology: normalize the root argument to an absolute Path.
    - Guarantee: returns Path(root).resolve() when root is given, else microcosm_root().
    - Fails: never raises for a syntactically valid path.
    """
    return Path(root).resolve() if root is not None else microcosm_root()


def _relation_key(source_kind: str, edge: dict[str, Any]) -> tuple[str, str, str]:
    """
    - Teleology: derive the (source_kind, verb, target_kind) identity tuple from a standard lattice edge.
    - Guarantee: returns a 3-tuple of source_kind plus the edge's relation_verb and to_kind as strings.
    - Fails: never raises; missing edge fields become empty strings.
    """
    return (
        source_kind,
        str(edge.get("relation_verb") or ""),
        str(edge.get("to_kind") or ""),
    )


def _registry_key(row: dict[str, Any]) -> tuple[str, str, str]:
    """
    - Teleology: derive the (source_kind, forward_verb, target_kind) identity tuple from a registry row.
    - Guarantee: returns a 3-tuple of the row's source_kind, forward_verb, target_kind as strings.
    - Fails: never raises; missing fields become empty strings.
    """
    return (
        str(row.get("source_kind") or ""),
        str(row.get("forward_verb") or ""),
        str(row.get("target_kind") or ""),
    )


def _iter_standard_edges(
    standards: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    - Teleology: flatten every required/selective lattice edge across all kind standards into annotated rows.
    - Guarantee: returns a list of edge dicts each annotated with source_kind, source_standard_ref, edge_class, edge_index, and relation_key.
    - Fails: never raises; non-dict edges are skipped.
    """
    rows: list[dict[str, Any]] = []
    for source_kind, standard in standards.items():
        lattice = _as_dict(standard.get("lattice_edges"))
        for edge_class in ("required", "selective"):
            for index, edge in enumerate(_as_list(lattice.get(edge_class))):
                if not isinstance(edge, dict):
                    continue
                row = _json(edge)
                row["source_kind"] = source_kind
                row["source_standard_ref"] = _standard_rel(source_kind)
                row["edge_class"] = edge_class
                row["edge_index"] = index
                row["relation_key"] = ".".join(_relation_key(source_kind, edge))
                rows.append(row)
    return rows


def _add_error(
    errors: list[dict[str, Any]], *, code: str, path: str, message: str, **extra: Any
) -> None:
    """
    - Teleology: append a structured validation error row with a stable shape.
    - Guarantee: appends a dict carrying code/path/message plus any extra fields to the errors list (mutates in place).
    - Fails: never raises; returns None.
    """
    row: dict[str, Any] = {"code": code, "path": path, "message": message}
    row.update(extra)
    errors.append(row)


def validate_relation_registry(
    registry: dict[str, Any],
    standards: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: check that the relation registry is internally well-formed and consistent with kind-standard lattice edges.
    - Guarantee: returns {status: 'pass'|'blocked', relation_count, registered_key_count, errors[]}; status is 'pass' iff errors is empty.
    - Fails: never raises; every defect (bad id pattern, duplicate key, unknown kind, cardinality/requirement mismatch, missing registry row) is recorded as an error row.
    - When-needed: before trusting relation ids used to classify edges and residuals.
    - Escalates-to: validate_kind_standard_contracts, core/doctrine_lattice_relations.json.
    - Non-goal: passing does not authorize release or prove the lattice is fully populated; it only proves registry/edge schema consistency.
    """
    errors: list[dict[str, Any]] = []
    rows = [row for row in _as_list(registry.get("relations")) if isinstance(row, dict)]
    registered_kinds = set(KIND_STANDARD_IDS) | {"code_locus", "receipt"}
    kind_unions: dict[str, set[str]] = {}
    for index, row in enumerate(_as_list(registry.get("kind_unions"))):
        if not isinstance(row, dict):
            continue
        union_id = str(row.get("kind_union_id") or "")
        members = {member for member in _strings(row.get("members"))}
        if not union_id:
            _add_error(errors, code="kind_union_missing_id", path=f"kind_unions[{index}]", message="Kind union lacks kind_union_id.")
            continue
        if not members:
            _add_error(errors, code="kind_union_missing_members", path=f"kind_unions[{index}]", message="Kind union has no members.")
        unknown_members = sorted(members - registered_kinds)
        if unknown_members:
            _add_error(errors, code="kind_union_unknown_member", path=f"kind_unions[{index}]", message="Kind union references unknown kind members.", unknown_members=unknown_members)
        kind_unions[union_id] = members
    known_target_kinds = registered_kinds | set(kind_unions)
    registered_projection_classes = set(_strings(registry.get("projection_classes")))
    registered_target_resolutions = set(_strings(registry.get("target_resolution_classes")) or list(TARGET_RESOLUTION_ENUM))
    ids: set[str] = set()
    keys: set[tuple[str, str, str]] = set()
    relation_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}

    for index, row in enumerate(rows):
        ref = f"relations[{index}]"
        relation_id = str(row.get("relation_id") or "")
        key = _registry_key(row)
        if not relation_id:
            _add_error(errors, code="relation_missing_id", path=ref, message="Relation row lacks relation_id.")
        elif not RELATION_ID_PATTERN.match(relation_id):
            _add_error(errors, code="relation_bad_id_pattern", path=ref, message="Relation id must be source.verb.target lowercase snake segments.")
        elif relation_id in ids:
            _add_error(errors, code="duplicate_relation_id", path=ref, message=f"Duplicate relation_id {relation_id}.")
        ids.add(relation_id)

        if not all(key):
            _add_error(errors, code="relation_missing_key", path=ref, message="Relation row lacks source_kind, forward_verb, or target_kind.")
        elif relation_id and relation_id != ".".join(key):
            _add_error(errors, code="relation_id_key_mismatch", path=ref, message="relation_id must equal source_kind.forward_verb.target_kind.")
        elif key in keys:
            _add_error(errors, code="duplicate_relation_key", path=ref, message="Duplicate source/verb/target relation key.")
        keys.add(key)
        relation_by_key[key] = row

        source_kind, _, target_kind = key
        if source_kind and source_kind not in registered_kinds:
            _add_error(errors, code="relation_bad_source_kind", path=ref, message="Relation source_kind is not a registered kind.")
        if target_kind and target_kind not in known_target_kinds:
            _add_error(errors, code="relation_bad_target_kind", path=ref, message="Relation target_kind is not a registered kind or kind_union.")

        if row.get("cardinality") not in CARDINALITY_ENUM:
            _add_error(errors, code="relation_bad_cardinality", path=ref, message="Relation uses unknown cardinality.")
        if row.get("requirement") not in REQUIREMENT_ENUM:
            _add_error(errors, code="relation_bad_requirement", path=ref, message="Relation uses unknown requirement.")
        if row.get("authority_class") not in _as_list(registry.get("authority_classes")):
            _add_error(errors, code="relation_bad_authority_class", path=ref, message="Relation authority_class is not registered.")
        if row.get("target_resolution") not in registered_target_resolutions:
            _add_error(errors, code="relation_bad_target_resolution", path=ref, message="Relation target_resolution is not registered.")
        if row.get("edge_justification_required") not in (True, False):
            _add_error(errors, code="relation_bad_edge_justification_required", path=ref, message="edge_justification_required must be a boolean.")
        projection_surfaces = _strings(row.get("projection_surfaces"))
        if not projection_surfaces:
            _add_error(errors, code="relation_missing_projection_surfaces", path=ref, message="Relation has no projection surfaces.")
        unknown_surfaces = sorted(set(projection_surfaces) - registered_projection_classes)
        if unknown_surfaces:
            _add_error(errors, code="relation_bad_projection_surface", path=ref, message="Relation projection surface is not registered.", unknown_projection_surfaces=unknown_surfaces)

    if standards is not None:
        for edge in _iter_standard_edges(standards):
            key = _relation_key(str(edge["source_kind"]), edge)
            relation = relation_by_key.get(key)
            if not relation:
                _add_error(
                    errors,
                    code="lattice_edge_missing_relation_registry_row",
                    path=f"{edge['source_standard_ref']}::{edge['edge_class']}[{edge['edge_index']}]",
                    message=f"No relation registry row for {'.'.join(key)}.",
                    relation_key=".".join(key),
                )
                continue
            if relation.get("reverse_verb") != edge.get("reverse_verb"):
                _add_error(errors, code="relation_reverse_verb_mismatch", path=str(edge["relation_key"]), message="Registry reverse verb does not match standard edge.")
            if relation.get("cardinality") != edge.get("cardinality"):
                _add_error(errors, code="relation_cardinality_mismatch", path=str(edge["relation_key"]), message="Registry cardinality does not match standard edge.")
            if relation.get("requirement") != edge.get("requirement"):
                _add_error(errors, code="relation_requirement_mismatch", path=str(edge["relation_key"]), message="Registry requirement does not match standard edge.")

    return {
        "schema_version": "microcosm_relation_registry_validation_v1",
        "status": "pass" if not errors else "blocked",
        "relation_count": len(rows),
        "registered_key_count": len(keys),
        "errors": errors,
    }


def _projection_is_generated_only(value: Any) -> bool:
    """
    - Teleology: enforce that a declared projection is generated and never claims source authority.
    - Guarantee: returns True iff the value is a dict with generated is True and source_authority not True.
    - Fails: never raises; non-dict input returns False.
    """
    row = _as_dict(value)
    return row.get("generated") is True and row.get("source_authority") is not True


def validate_kind_standard_contracts(
    standards: dict[str, dict[str, Any]],
    relation_registry: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: gate that every kind standard is an active v2 JSON contract with the required skill/validation/projection triads and organ over-minting guards.
    - Guarantee: returns {status: 'pass'|'blocked', errors[], relation_registry: <sub-result>}; status 'pass' iff no errors and the embedded relation-registry validation also passes.
    - Fails: never raises; non-v2/non-active standards, missing triad members, source-authority projections, and organ edge-shape violations are recorded as errors.
    - When-needed: before building any corpus, to confirm the governing contracts are well-formed.
    - Escalates-to: std_microcosm_*.json, validate_relation_registry.
    - Non-goal: passing does not authorize release or prove instances exist; it only proves the standards/registry contract shape.
    """
    errors: list[dict[str, Any]] = []
    for kind, standard in standards.items():
        ref = _standard_rel(kind)
        if standard.get("schema_version") != "public_microcosm_standard_v2":
            _add_error(errors, code="kind_standard_not_v2", path=ref, message="Kind standard is not v2.")
        if standard.get("status") != "active":
            _add_error(errors, code="kind_standard_not_active", path=ref, message="Kind standard is not active.")
        if standard.get("source_format") != "json":
            _add_error(errors, code="kind_standard_not_json_source", path=ref, message="Kind standard lacks source_format=json.")

        instance_schema = _as_dict(standard.get("instance_schema"))
        if not _strings(instance_schema.get("required_keys")):
            _add_error(errors, code="kind_standard_missing_instance_required_keys", path=ref, message="Kind standard lacks instance_schema.required_keys.")

        skills = _as_dict(standard.get("skills"))
        for key in SKILL_TRIAD:
            if key not in skills:
                _add_error(errors, code="kind_standard_missing_skill_triad", path=f"{ref}::skills.{key}", message="Kind standard lacks required skill triad member.")

        validation = _as_dict(standard.get("validation"))
        for key in VALIDATION_TRIAD:
            if key not in validation:
                _add_error(errors, code="kind_standard_missing_validation_triad", path=f"{ref}::validation.{key}", message="Kind standard lacks validation triad member.")

        projections = _as_dict(standard.get("projections"))
        for key in PROJECTION_TRIAD:
            if not _projection_is_generated_only(projections.get(key)):
                _add_error(errors, code="projection_generated_not_source_guard", path=f"{ref}::projections.{key}", message="Projection must be generated and must not claim source authority.")

        policy = _as_dict(standard.get("provisional_policy"))
        forbidden = set(_strings(policy.get("forbidden_shipped_status")))
        if not {"candidate", "provisional", "seed", "draft"}.issubset(forbidden):
            _add_error(errors, code="public_provisional_status_guard", path=f"{ref}::provisional_policy", message="Public shipped status guard is incomplete.")

    organ = _as_dict(standards.get("organ"))
    organ_lattice = _as_dict(organ.get("lattice_edges"))
    required_targets = {str(edge.get("to_kind")) for edge in _as_list(organ_lattice.get("required")) if isinstance(edge, dict)}
    selective_targets = {str(edge.get("to_kind")) for edge in _as_list(organ_lattice.get("selective")) if isinstance(edge, dict)}
    for target in ("paper_module", "mechanism", "code_locus"):
        if target not in required_targets:
            _add_error(errors, code="organ_required_edge_missing", path="std_microcosm_organ.json::lattice_edges.required", message=f"Organ must require {target}.")
    for target in ("concept", "principle", "axiom"):
        if target in required_targets:
            _add_error(errors, code="organ_over_mints_selective_doctrine", path="std_microcosm_organ.json::lattice_edges.required", message=f"Organ must not require per-organ {target}.")
        if target not in selective_targets:
            _add_error(errors, code="organ_selective_doctrine_edge_missing", path="std_microcosm_organ.json::lattice_edges.selective", message=f"Organ must expose selective {target} edge.")
    if "mint a concept/principle/axiom per organ" not in str(organ_lattice.get("forbidden_rule") or ""):
        _add_error(errors, code="organ_over_minting_forbidden_rule_missing", path="std_microcosm_organ.json::lattice_edges.forbidden_rule", message="Organ standard lacks no-over-minting guard.")

    meta = _as_dict(standards.get("standard"))
    requirements = _as_dict(meta.get("kind_standard_requirements"))
    if "organ_core_correction" not in requirements:
        _add_error(errors, code="meta_standard_missing_organ_core_correction", path="std_microcosm_standard.json::kind_standard_requirements", message="Meta-standard lacks organ_core_correction.")

    relation_result = validate_relation_registry(relation_registry, standards)
    errors.extend(_as_list(relation_result.get("errors")))
    return {
        "schema_version": "microcosm_kind_standard_contract_validation_v1",
        "status": "pass" if not errors else "blocked",
        "errors": errors,
        "relation_registry": relation_result,
    }


def _accepted_organs(root: str | Path | None) -> list[dict[str, Any]]:
    """
    - Teleology: select the organ-registry rows that are accepted current authority.
    - Guarantee: returns the implemented_organs rows whose status == 'accepted_current_authority'.
    - Fails: never raises; missing registry or rows yield [].
    - Escalates-to: core/organ_registry.json.
    """
    registry = _as_dict(_load(root, "core/organ_registry.json"))
    return [
        row
        for row in _as_list(registry.get("implemented_organs"))
        if isinstance(row, dict) and row.get("status") == "accepted_current_authority"
    ]


def _atlas_organs(root: str | Path | None) -> list[dict[str, Any]]:
    """
    - Teleology: read the organ-atlas rows.
    - Guarantee: returns the dict rows under organ_atlas.organs.
    - Fails: never raises; missing atlas yields [].
    - Escalates-to: core/organ_atlas.json.
    """
    atlas = _as_dict(_load(root, "core/organ_atlas.json"))
    return [row for row in _as_list(atlas.get("organs")) if isinstance(row, dict)]


def _has_declared_paper_module(row: dict[str, Any]) -> bool:
    """
    - Teleology: test whether an atlas row declares a non-empty paper_module_ref.
    - Guarantee: returns True iff the row's paper_module_ref is a non-blank string.
    - Fails: never raises.
    """
    return bool(str(row.get("paper_module_ref") or "").strip())


def _mechanism_ref_rows(row: dict[str, Any]) -> list[dict[str, Any]]:
    """
    - Teleology: normalize an atlas row's mechanism references (string or dict, plus fallback singular) into uniform rows.
    - Guarantee: returns a list of {ref, resolution_status, ...} dicts for each named mechanism ref; bare strings default resolution_status to 'resolved'.
    - Fails: never raises; rows without a usable ref are dropped.
    """
    refs = row.get("mechanism_refs")
    rows: list[dict[str, Any]] = []
    if isinstance(refs, list):
        for ref in refs:
            if isinstance(ref, str) and ref.strip():
                rows.append({"ref": ref.strip(), "resolution_status": "resolved"})
            elif isinstance(ref, dict):
                value = str(ref.get("ref") or ref.get("mechanism_id") or "").strip()
                if value:
                    copy_row = _json(ref)
                    copy_row["ref"] = value
                    rows.append(copy_row)
    fallback = str(row.get("mechanism_ref") or "").strip()
    if fallback:
        rows.append({"ref": fallback, "resolution_status": "resolved"})
    return rows


def _has_mechanism_ref(row: dict[str, Any]) -> bool:
    """
    - Teleology: test whether an atlas row names any mechanism.
    - Guarantee: returns True iff _mechanism_ref_rows yields at least one row.
    - Fails: never raises.
    """
    return bool(_mechanism_ref_rows(row))


def _has_code_loci(row: dict[str, Any]) -> bool:
    """
    - Teleology: test whether an atlas row declares code loci.
    - Guarantee: returns truthiness of the row's code_loci field (non-empty list or truthy value).
    - Fails: never raises.
    """
    value = row.get("code_loci")
    if isinstance(value, list):
        return bool(value)
    return bool(value)


def _paper_module_files(root: str | Path | None, suffixes: tuple[str, ...] = (".md", ".json")) -> list[str]:
    """
    - Teleology: inventory paper-module files of given suffixes under the paper_modules directory.
    - Guarantee: returns a sorted de-duplicated list of repo-relative posix paths for matching files; [] if the directory is absent.
    - Fails: never raises.
    """
    resolved = _root(root)
    paper_dir = resolved / "paper_modules"
    if not paper_dir.is_dir():
        return []
    rows: list[str] = []
    for suffix in suffixes:
        rows.extend(path.relative_to(resolved).as_posix() for path in paper_dir.glob(f"*{suffix}"))
    return sorted(set(rows))


def _paper_capsules(root: str | Path | None) -> list[dict[str, Any]]:
    """
    - Teleology: read the JSON paper-module capsule rows.
    - Guarantee: returns the dict rows under paper_module_capsules.paper_modules.
    - Fails: never raises; missing capsule registry yields [].
    - Escalates-to: core/paper_module_capsules.json.
    """
    payload = _load_optional_dict(root, PAPER_MODULE_CAPSULES_REL)
    return [row for row in _as_list(payload.get("paper_modules")) if isinstance(row, dict)]


def _paper_module_legacy_alias_rows(root: str | Path | None) -> list[dict[str, str]]:
    """
    - Teleology: read capsule-owned Markdown alias rows that are not independent legacy paper-module sources.
    - Guarantee: returns alias rows with path/canonical id/import policy/source_ref; malformed alias rows are ignored.
    - Fails: never raises beyond the capsule registry read.
    - Escalates-to: core/paper_module_capsules.json.
    """
    rows: list[dict[str, str]] = []
    for capsule_index, capsule in enumerate(_paper_capsules(root)):
        canonical_id = str(capsule.get("id") or "").strip()
        if not canonical_id:
            continue
        for alias_index, alias in enumerate(_as_list(capsule.get("legacy_markdown_projection_aliases"))):
            if isinstance(alias, str):
                alias_path = alias.strip()
                import_policy = "suppress_legacy_row"
                reason = ""
            elif isinstance(alias, dict):
                alias_path = str(alias.get("path") or "").strip()
                import_policy = str(alias.get("import_policy") or "suppress_legacy_row").strip()
                reason = str(alias.get("reason") or "").strip()
            else:
                continue
            if not alias_path:
                continue
            rows.append(
                {
                    "path": alias_path,
                    "canonical_paper_module_id": canonical_id,
                    "import_policy": import_policy,
                    "reason": reason,
                    "source_ref": (
                        f"{PAPER_MODULE_CAPSULES_REL}::paper_modules"
                        f"[{capsule_index}:{canonical_id}].legacy_markdown_projection_aliases[{alias_index}]"
                    ),
                }
            )
    return rows


def _suppressed_legacy_markdown_aliases(root: str | Path | None) -> dict[str, dict[str, str]]:
    """
    - Teleology: index capsule-owned Markdown aliases that must not become duplicate legacy rows.
    - Guarantee: returns {repo_relative_markdown_path: alias_row} for import_policy suppress_legacy_row.
    - Fails: never raises beyond _paper_module_legacy_alias_rows.
    """
    return {
        row["path"]: row
        for row in _paper_module_legacy_alias_rows(root)
        if row.get("import_policy") == "suppress_legacy_row"
    }


def _mechanism_sources(root: str | Path | None) -> dict[str, dict[str, Any]]:
    """
    - Teleology: index mechanism-registry rows by mechanism id.
    - Guarantee: returns {mechanism_id: row} for every registry row carrying an id.
    - Fails: never raises; missing registry yields {}.
    - Escalates-to: core/mechanism_sources.json.
    """
    payload = _load_optional_dict(root, MECHANISM_REGISTRY_REL)
    rows = [row for row in _as_list(payload.get("mechanisms")) if isinstance(row, dict)]
    return {str(row.get("id") or ""): row for row in rows if row.get("id")}


def _mechanism_capsule_dependency_upstream_parity(root: str | Path | None) -> dict[str, Any]:
    """
    - Teleology: check that paper-module depends_on edges are reflected as mechanism upstream_of declarations in the mechanism registry.
    - Guarantee: returns {status: 'pass'|'deficit', covered/missing/unresolved counts and detail rows}; status 'deficit' iff any missing edge exists.
    - Fails: never raises; dependencies whose consumer/upstream lacks a resolved mechanism subject are recorded as unresolved_dependencies, not errors.
    - When-needed: auditing whether capsule dependency direction is honored by mechanism wiring.
    - Escalates-to: core/paper_module_capsules.json, core/mechanism_sources.json, mechanism.upstream_of.mechanism relation.
    - Non-goal: a 'pass' proves declared parity only, not runtime invocation order or release authority.
    """
    mechanisms = _mechanism_sources(root)
    paper_rows = _paper_capsules(root)
    paper_to_mechanism: dict[str, str] = {}
    for paper in paper_rows:
        paper_id = str(paper.get("id") or "").strip()
        if not paper_id:
            continue
        mechanism_subjects = [
            ref
            for ref in (
                str(subject.get("ref") or "").strip()
                for subject in _as_list(paper.get("subjects"))
                if isinstance(subject, dict) and subject.get("kind") == "mechanism"
            )
            if ref and ref in mechanisms
        ]
        if mechanism_subjects:
            paper_to_mechanism[paper_id] = mechanism_subjects[0]

    covered_edges: list[dict[str, str]] = []
    missing_edges: list[dict[str, str]] = []
    unresolved_dependencies: list[dict[str, str]] = []
    for paper in paper_rows:
        consumer_paper_id = str(paper.get("id") or "").strip()
        if not consumer_paper_id:
            continue
        consumer_mechanism_id = paper_to_mechanism.get(consumer_paper_id, "")
        for dependency_paper_id in _strings(paper.get("depends_on")):
            upstream_mechanism_id = paper_to_mechanism.get(dependency_paper_id, "")
            if not consumer_mechanism_id or not upstream_mechanism_id:
                unresolved_dependencies.append(
                    {
                        "dependency_paper_module": dependency_paper_id,
                        "consumer_paper_module": consumer_paper_id,
                        "reason": "dependency_or_consumer_lacks_resolved_mechanism_subject",
                    }
                )
                continue
            if upstream_mechanism_id == consumer_mechanism_id:
                continue
            edge = {
                "dependency_paper_module": dependency_paper_id,
                "consumer_paper_module": consumer_paper_id,
                "source_mechanism": upstream_mechanism_id,
                "target_mechanism": consumer_mechanism_id,
            }
            declared_targets = set(_strings(mechanisms[upstream_mechanism_id].get("upstream"))) | set(
                _strings(mechanisms[upstream_mechanism_id].get("upstream_of"))
            )
            if consumer_mechanism_id in declared_targets:
                covered_edges.append(edge)
            else:
                missing_edges.append(edge)

    covered_edges = sorted(
        covered_edges,
        key=lambda row: (
            _id_sort_key(row["source_mechanism"]),
            _id_sort_key(row["target_mechanism"]),
        ),
    )
    missing_edges = sorted(
        missing_edges,
        key=lambda row: (
            _id_sort_key(row["source_mechanism"]),
            _id_sort_key(row["target_mechanism"]),
        ),
    )
    unresolved_dependencies = sorted(
        unresolved_dependencies,
        key=lambda row: (
            _id_sort_key(row["consumer_paper_module"]),
            _id_sort_key(row["dependency_paper_module"]),
        ),
    )
    return {
        "schema_version": "mechanism_capsule_dependency_upstream_parity_v1",
        "status": "pass" if not missing_edges else "deficit",
        "authority_boundary": (
            "computed_projection_from_paper_module_capsules_and_mechanism_sources_not_source_authority"
        ),
        "relation_direction": (
            "paper_module A depends_on paper_module B maps to mechanism(B).upstream_of mechanism(A); "
            "the reverse direction is not inferred from depends_on."
        ),
        "source_refs": {
            "paper_module_capsules": PAPER_MODULE_CAPSULES_REL,
            "mechanism_registry": MECHANISM_REGISTRY_REL,
            "relation_registry": "core/doctrine_lattice_relations.json::mechanism.upstream_of.mechanism",
        },
        "resolved_mechanism_subject_count": len(paper_to_mechanism),
        "covered_edge_count": len(covered_edges),
        "missing_edge_count": len(missing_edges),
        "unresolved_dependency_count": len(unresolved_dependencies),
        "sample_covered_edges": covered_edges[:12],
        "missing_edges": missing_edges,
        "unresolved_dependencies": unresolved_dependencies[:25],
    }


def _ref_file_exists(root: str | Path | None, ref: str) -> bool:
    """
    - Teleology: test that the file portion of a (possibly fragment-suffixed) ref exists on disk.
    - Guarantee: returns True iff the pre-'#' path is non-empty and resolves to an existing file under root.
    - Fails: never raises.
    """
    rel = ref.split("#", 1)[0]
    return bool(rel) and _path(root, rel).is_file()


def _code_locus_rows(row: dict[str, Any]) -> list[dict[str, Any]]:
    """
    - Teleology: normalize a row's code_loci (string, list of strings, or list of dicts) into uniform path rows.
    - Guarantee: returns a list of {path, resolution, ...} dicts; bare strings default resolution to 'resolved'.
    - Fails: never raises; entries without a usable path are dropped.
    """
    value = row.get("code_loci")
    rows: list[dict[str, Any]] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                rows.append({"path": item.strip(), "resolution": "resolved"})
            elif isinstance(item, dict) and str(item.get("path") or "").strip():
                rows.append(_json(item))
    elif isinstance(value, str) and value.strip():
        rows.append({"path": value.strip(), "resolution": "resolved"})
    return rows


def _manifest_surface_entries(root: str | Path | None) -> list[dict[str, Any]]:
    """
    - Teleology: flatten the public-surface manifest into per-path scan entries.
    - Guarantee: returns one row per declared path carrying surface_class, path, and scan_for_codex_brand_leaks flag.
    - Fails: never raises; absent manifest yields [].
    - Escalates-to: core/public_surface_manifest.json.
    """
    manifest = _load_optional_dict(root, PUBLIC_SURFACE_MANIFEST_REL)
    classes = _as_dict(manifest.get("surface_classes"))
    rows: list[dict[str, Any]] = []
    for class_id, row in classes.items():
        if not isinstance(row, dict):
            continue
        for rel in _strings(row.get("paths")):
            rows.append(
                {
                    "surface_class": class_id,
                    "path": rel,
                    "scan_for_codex_brand_leaks": row.get("scan_for_codex_brand_leaks") is True,
                }
            )
    return rows


def check_public_codex_leaks(
    root: str | Path | None = None,
    surfaces: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: scan public-facing narrative prose for the 'Codex' brand token, distinguishing real leaks from allowed provenance refs.
    - Guarantee: returns {status: 'pass'|'blocked', brand_hits[], allowed_provenance_ref_count, ...}; status 'blocked' iff any non-provenance 'Codex' brand hit exists.
    - Fails: never raises; lines containing codex/ or source_modules/codex are classified as allowed provenance, not blocking hits.
    - When-needed: before publishing or trusting that public prose is brand-clean.
    - Escalates-to: core/public_surface_manifest.json, the surfaces it lists.
    - Non-goal: a 'pass' checks brand leakage in scanned prose only; it does not authorize publication or prove no other private content leaked.
    """
    using_manifest = surfaces is None
    if surfaces is None:
        resolved = _root(root)
        surfaces = {}
        surface_classes: dict[str, list[str]] = {}
        for entry in _manifest_surface_entries(root):
            if not entry["scan_for_codex_brand_leaks"]:
                continue
            rel = str(entry["path"])
            path = resolved / rel
            if not path.is_file():
                continue
            surfaces[rel] = path.read_text(encoding="utf-8")
            surface_classes.setdefault(str(entry["surface_class"]), []).append(rel)
    else:
        surface_classes = {"ad_hoc": sorted(surfaces)}

    brand_hits: list[dict[str, Any]] = []
    allowed_provenance_hits: list[dict[str, Any]] = []
    pattern = re.compile(r"\b[Cc]odex\b")
    for ref, text in surfaces.items():
        for line_no, line in enumerate(text.splitlines(), start=1):
            if not pattern.search(line):
                continue
            if "codex/" in line or "source_modules/codex" in line:
                allowed_provenance_hits.append({"ref": ref, "line": line_no})
            else:
                brand_hits.append({"ref": ref, "line": line_no, "snippet": line.strip()[:160]})

    return {
        "schema_version": "microcosm_public_codex_leak_guard_v1",
        "status": "pass" if not brand_hits else "blocked",
        "manifest_ref": PUBLIC_SURFACE_MANIFEST_REL if using_manifest else None,
        "scanned_surface_classes": surface_classes,
        "scanned_public_prose_surfaces": sorted(surfaces),
        "brand_leak_count": len(brand_hits),
        "allowed_provenance_ref_count": len(allowed_provenance_hits),
        "brand_hits": brand_hits,
        "anti_claim": "This guard checks public-facing narrative prose for brand leakage. Provenance refs to copied macro paths remain a separate allowed-source-ref class.",
    }


def _duplicates(values: list[str]) -> list[str]:
    """
    - Teleology: find values that occur more than once in a list.
    - Guarantee: returns the sorted set of values appearing at least twice.
    - Fails: never raises; returns [] when all values are unique.
    """
    seen: set[str] = set()
    duplicate: set[str] = set()
    for value in values:
        if value in seen:
            duplicate.add(value)
        seen.add(value)
    return sorted(duplicate)


def _paper_ref_resolves(root: str | Path | None, ref: str, capsules: dict[str, dict[str, Any]]) -> bool:
    """
    - Teleology: test that a paper-module ref resolves to a file and (if fragment-suffixed) to a known capsule.
    - Guarantee: returns True iff the file exists and, when a '#fragment' is present, the fragment is a key in capsules.
    - Fails: never raises.
    """
    if not _ref_file_exists(root, ref):
        return False
    if "#" not in ref:
        return True
    fragment = ref.split("#", 1)[1]
    return fragment in capsules


def _registry_atlas_join_health(
    root: str | Path | None,
    accepted: list[dict[str, Any]],
    atlas_rows: list[dict[str, Any]],
    *,
    mechanism_sources: dict[str, dict[str, Any]],
    paper_capsules: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    - Teleology: check organ-registry/organ-atlas join integrity and resolve declared paper/mechanism/code refs.
    - Guarantee: returns {status: 'pass'|'blocked', counts of resolved/planned mechanisms and code loci, errors[]}; status 'pass' iff no errors.
    - Fails: never raises; duplicate ids, registry/atlas mismatches, and unresolved/planned-typed refs are recorded as error rows.
    - When-needed: building coverage to confirm the organ source surfaces agree and refs resolve.
    - Escalates-to: core/organ_registry.json, core/organ_atlas.json, build_coverage_projection.
    - Non-goal: passing proves join + reference resolution only, not runtime correctness or release readiness.
    """
    errors: list[dict[str, Any]] = []
    accepted_ids = [str(row.get("organ_id") or "") for row in accepted if row.get("organ_id")]
    atlas_ids = [str(row.get("organ_id") or "") for row in atlas_rows if row.get("organ_id")]
    accepted_set = set(accepted_ids)
    atlas_set = set(atlas_ids)

    for duplicate in _duplicates(accepted_ids):
        _add_error(errors, code="duplicate_accepted_organ_id", path="core/organ_registry.json", message="Accepted organ id appears more than once.", organ_id=duplicate)
    for duplicate in _duplicates(atlas_ids):
        _add_error(errors, code="duplicate_atlas_organ_id", path="core/organ_atlas.json", message="Atlas organ id appears more than once.", organ_id=duplicate)
    for organ_id in sorted(accepted_set - atlas_set):
        _add_error(errors, code="accepted_organ_missing_atlas", path="core/organ_atlas.json", message="Accepted organ has no atlas row.", organ_id=organ_id)
    for organ_id in sorted(atlas_set - accepted_set):
        _add_error(errors, code="atlas_organ_missing_accepted_registry", path="core/organ_registry.json", message="Atlas organ has no accepted registry row.", organ_id=organ_id)

    resolved_mechanism_count = 0
    planned_mechanism_count = 0
    resolved_code_locus_count = 0
    planned_code_locus_count = 0
    atlas_by_id = {str(row.get("organ_id") or ""): row for row in atlas_rows}
    for organ_id in accepted_ids:
        row = atlas_by_id.get(organ_id, {})
        paper_ref = str(row.get("paper_module_ref") or "").strip()
        if paper_ref and not _paper_ref_resolves(root, paper_ref, paper_capsules):
            _add_error(errors, code="paper_module_ref_unresolved", path=f"core/organ_atlas.json::{organ_id}.paper_module_ref", message="paper_module_ref path or capsule fragment does not resolve.", organ_id=organ_id, ref=paper_ref)

        for mechanism_ref in _mechanism_ref_rows(row):
            ref = str(mechanism_ref.get("ref") or "")
            status = str(mechanism_ref.get("resolution_status") or "resolved")
            if status not in MECHANISM_RESOLUTION_ENUM:
                _add_error(errors, code="mechanism_ref_bad_resolution_status", path=f"core/organ_atlas.json::{organ_id}.mechanism_refs", message="Mechanism ref uses unknown resolution_status.", organ_id=organ_id, ref=ref)
                continue
            if status == "planned_unresolved":
                planned_mechanism_count += 1
                continue
            if ref in mechanism_sources:
                resolved_mechanism_count += 1
            else:
                _add_error(errors, code="mechanism_ref_unresolved", path=f"core/organ_atlas.json::{organ_id}.mechanism_refs", message="Resolved mechanism ref is not present in the mechanism registry.", organ_id=organ_id, ref=ref)

        for locus in _code_locus_rows(row):
            rel = str(locus.get("path") or "")
            resolution = str(locus.get("resolution") or "resolved")
            if resolution not in CODE_LOCUS_RESOLUTION_ENUM:
                _add_error(errors, code="code_locus_bad_resolution", path=f"core/organ_atlas.json::{organ_id}.code_loci", message="Code locus uses unknown resolution.", organ_id=organ_id, ref=rel)
                continue
            if resolution == "planned":
                planned_code_locus_count += 1
                continue
            if rel and _path(root, rel).is_file():
                resolved_code_locus_count += 1
            else:
                _add_error(errors, code="code_locus_unresolved", path=f"core/organ_atlas.json::{organ_id}.code_loci", message="Resolved code locus path does not exist.", organ_id=organ_id, ref=rel)

    for mechanism_id, mechanism in mechanism_sources.items():
        for locus in _code_locus_rows(mechanism):
            rel = str(locus.get("path") or "")
            resolution = str(locus.get("resolution") or "resolved")
            if resolution == "resolved" and rel and not _path(root, rel).is_file():
                _add_error(errors, code="mechanism_code_locus_unresolved", path=f"{MECHANISM_REGISTRY_REL}::{mechanism_id}.code_loci", message="Mechanism source declares a resolved code locus path that does not exist.", mechanism_id=mechanism_id, ref=rel)

    return {
        "schema_version": "microcosm_registry_atlas_join_health_v1",
        "status": "pass" if not errors else "blocked",
        "accepted_organ_count": len(accepted_ids),
        "atlas_organ_count": len(atlas_ids),
        "registry_missing_atlas_count": len(accepted_set - atlas_set),
        "atlas_missing_registry_count": len(atlas_set - accepted_set),
        "duplicate_accepted_organ_ids": _duplicates(accepted_ids),
        "duplicate_atlas_organ_ids": _duplicates(atlas_ids),
        "resolved_mechanism_count": resolved_mechanism_count,
        "planned_mechanism_count": planned_mechanism_count,
        "resolved_code_locus_count": resolved_code_locus_count,
        "planned_code_locus_count": planned_code_locus_count,
        "errors": errors,
    }


def _paper_module_corpus(root: str | Path | None) -> dict[str, Any]:
    """
    - Teleology: summarize paper-module migration state across legacy markdown, JSON capsules, and governed JSON instances.
    - Guarantee: returns a corpus dict of file/capsule/instance counts, missing/extra ids, gap ids, and the strangler rule; reports parity status from validate_paper_module_instance_corpus.
    - Fails: never raises; absent surfaces yield zero counts.
    - When-needed: building coverage's paper-module section.
    - Escalates-to: validate_paper_module_instance_corpus, core/paper_module_capsules.json.
    """
    markdown_files = _paper_module_files(root, suffixes=(".md",))
    json_files = _paper_module_files(root, suffixes=(".json",))
    capsules = _paper_capsules(root)
    capsule_markdown_files = sorted(
        {
            str(row.get("legacy_markdown_projection") or "").strip()
            for row in capsules
            if str(row.get("legacy_markdown_projection") or "").strip()
        }
    )
    suppressed_aliases = _suppressed_legacy_markdown_aliases(root)
    suppressed_alias_files = sorted(set(markdown_files) & set(suppressed_aliases))
    markdown_without_capsule = sorted(
        set(markdown_files) - set(capsule_markdown_files) - set(suppressed_alias_files)
    )
    expected_instances = expected_paper_module_instances(root)
    loaded_instances = load_paper_module_instances(root)
    validation = validate_paper_module_instance_corpus(root)
    legacy_only_instances = [
        instance_id
        for instance_id, instance in expected_instances.items()
        if _as_dict(instance.get("paper_module_payload")).get("source_authority") == "legacy_markdown_projection"
    ]
    required_subject_gap_instances = [
        instance_id
        for instance_id, instance in expected_instances.items()
        if any(
            isinstance(residual, dict)
            and residual.get("relation_id") == "paper_module.explains.organ_or_mechanism"
            for residual in _as_list(_as_dict(instance.get("relationships")).get("unpopulated_selective_relations"))
        )
    ]
    selective_gap_instances = [
        instance_id
        for instance_id, instance in expected_instances.items()
        if any(
            isinstance(residual, dict)
            and residual.get("requirement") == "selective"
            for residual in _as_list(_as_dict(instance.get("relationships")).get("unpopulated_selective_relations"))
        )
    ]
    source_rows: list[dict[str, str]] = []
    for rel in markdown_files:
        if rel in suppressed_aliases:
            alias = suppressed_aliases[rel]
            source_rows.append(
                {
                    "path": rel,
                    "source_class": "legacy_markdown_projection_suppressed_by_json_capsule_alias",
                    "canonical_paper_module_id": alias["canonical_paper_module_id"],
                    "source_ref": alias["source_ref"],
                }
            )
        else:
            source_class = (
                "legacy_markdown_projection_with_json_capsule"
                if rel in capsule_markdown_files
                else "legacy_markdown_projection_without_json_capsule"
            )
            source_rows.append({"path": rel, "source_class": source_class})
    if _path(root, PAPER_MODULE_CAPSULES_REL).is_file():
        source_rows.append(
            {
                "path": PAPER_MODULE_CAPSULES_REL,
                "source_class": "json_capsule_registry",
                "sha256": _sha256(_path(root, PAPER_MODULE_CAPSULES_REL)),
            }
        )
    return {
        "schema_version": "microcosm_paper_module_corpus_v1",
        "markdown_file_count": len(markdown_files),
        "markdown_files": markdown_files,
        "markdown_with_json_capsule_count": len(capsule_markdown_files),
        "markdown_with_json_capsule": capsule_markdown_files,
        "markdown_without_json_capsule_count": len(markdown_without_capsule),
        "markdown_without_json_capsule": markdown_without_capsule,
        "suppressed_legacy_markdown_alias_count": len(suppressed_alias_files),
        "suppressed_legacy_markdown_aliases": [
            suppressed_aliases[rel] for rel in suppressed_alias_files
        ],
        "json_capsule_file": PAPER_MODULE_CAPSULES_REL if _path(root, PAPER_MODULE_CAPSULES_REL).is_file() else None,
        "json_capsule_count": len(capsules),
        "json_capsule_ids": sorted(str(row.get("id") or "") for row in capsules if row.get("id")),
        "json_instance_count": len(loaded_instances),
        "expected_json_instance_count": len(expected_instances),
        "json_instance_files": json_files,
        "missing_json_ids": sorted(set(expected_instances) - set(loaded_instances), key=_id_sort_key),
        "extra_json_ids": sorted(set(loaded_instances) - set(expected_instances), key=_id_sort_key),
        "json_instance_parity_status": validation["status"],
        "legacy_only_json_instance_count": len(legacy_only_instances),
        "legacy_only_json_instance_ids": sorted(legacy_only_instances, key=_id_sort_key),
        "required_subject_gap_count": len(required_subject_gap_instances),
        "required_subject_gap_ids": sorted(required_subject_gap_instances, key=_id_sort_key),
        "unpopulated_selective_relation_count": _unpopulated_relation_count(expected_instances),
        "unpopulated_selective_relation_ids": sorted(selective_gap_instances, key=_id_sort_key),
        "json_authority_migration_status": "pilot_started" if capsules else "not_started",
        "authority_flip_status": "not_flipped",
        "source_manifest": source_rows,
        "source_manifest_digest": _sha256_json(source_rows),
        "content_digest_scope": "paper_module_json_instances_plus_capsule_registry_and_legacy_markdown_paths",
        "strangler_rule": "Markdown remains legacy/import projection until JSON instances and capsules round-trip structurally; legacy-only JSON rows are import indexes, not authority upgrades.",
    }


def _paper_module_slug(module_id: str) -> str:
    """
    - Teleology: reduce a paper-module id to its slug (strip the 'paper_module.' prefix).
    - Guarantee: returns the substring after 'paper_module.' if prefixed, else the id unchanged.
    - Fails: never raises.
    """
    if module_id.startswith("paper_module."):
        return module_id.split(".", 1)[1]
    return module_id


def _paper_module_instance_rel(module_id: str) -> str:
    """
    - Teleology: compute the governed JSON instance path for a paper module.
    - Guarantee: returns 'paper_modules/<slug>.json'.
    - Fails: never raises.
    """
    return f"{PAPER_MODULE_INSTANCE_DIR_REL}/{_paper_module_slug(module_id)}.json"


def _paper_module_source_rows(root: str | Path | None) -> list[dict[str, Any]]:
    """
    - Teleology: assemble the unified paper-module source rows from JSON capsules plus legacy-only markdown files.
    - Guarantee: returns rows sorted by id; capsule rows carry source_authority 'json_capsule', legacy-only markdown rows carry 'legacy_markdown_projection' with residual-stating compression/projection fields.
    - Fails: never raises; rows without an id are skipped.
    - Escalates-to: core/paper_module_capsules.json, paper_modules/*.md.
    """
    capsule_rows = _paper_capsules(root)
    markdown_files = _paper_module_files(root, suffixes=(".md",))
    capsule_module_ids = {
        str(row.get("id") or "").strip()
        for row in capsule_rows
        if str(row.get("id") or "").strip()
    }
    capsule_markdown_files = {
        str(row.get("legacy_markdown_projection") or "").strip()
        for row in capsule_rows
        if str(row.get("legacy_markdown_projection") or "").strip()
    }
    suppressed_aliases = _suppressed_legacy_markdown_aliases(root)
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(capsule_rows):
        module_id = str(row.get("id") or "").strip()
        if not module_id:
            continue
        copy_row = _json(row)
        copy_row["source_ref"] = f"{PAPER_MODULE_CAPSULES_REL}::paper_modules[{index}:{module_id}]"
        copy_row["source_authority"] = "json_capsule"
        legacy_path = str(copy_row.get("legacy_markdown_projection") or "").strip()
        if legacy_path:
            copy_row["legacy_markdown_projection"] = legacy_path
        rows.append(copy_row)

    for rel in markdown_files:
        module_id = f"paper_module.{Path(rel).stem}"
        if module_id in capsule_module_ids:
            continue
        if rel in capsule_markdown_files:
            continue
        if rel in suppressed_aliases:
            continue
        slug = Path(rel).stem
        rows.append(
            {
                "id": module_id,
                "kind": "paper_module",
                "title": slug.replace("_", " ").title(),
                "source_ref": rel,
                "source_authority": "legacy_markdown_projection",
                "legacy_markdown_projection": rel,
                "compression": {
                    "one_line": (
                        f"Legacy paper-module projection {slug} is indexed for migration; "
                        "capsule authority and typed subjects remain residual."
                    ),
                    "card": (
                        f"{slug} is present as legacy Markdown in the public Plectis "
                        "paper-module compatibility surface, but it has no JSON capsule yet. "
                        "The governed JSON row records "
                        "the gap without treating Markdown prose as source authority."
                    ),
                    "authority_ceiling": (
                        "Legacy Markdown path inventory only; no JSON capsule authority, "
                        "typed subject coverage, runtime correctness, or release proof."
                    ),
                },
                "subjects": [],
                "code_loci": [],
                "generated_projections": {
                    "markdown": {
                        "path": rel,
                        "status": "legacy_markdown_projection_not_generated_from_json",
                        "generated": False,
                    },
                    "mermaid": {
                        "projection_id": f"{module_id}.mermaid",
                        "status": "blocked_required_subject_gap",
                        "generated": False,
                    },
                    "atlas_card": {
                        "projection_id": f"{module_id}.atlas_card",
                        "status": "blocked_required_subject_gap",
                        "generated": False,
                    },
                },
                "strangler_note": (
                    "Legacy-only row exists so agents see the migration deficit in governed JSON; "
                    "it is not a source-authority flip."
                ),
            }
        )
    return sorted(rows, key=lambda item: _id_sort_key(str(item.get("id") or "")))


def _paper_module_target_id(value: str) -> str:
    """
    - Teleology: normalize a paper-module reference value into a canonical 'paper_module.<slug>' id.
    - Guarantee: returns the stripped value unchanged if already prefixed, else prefixes it with 'paper_module.'; empty input returns empty.
    - Fails: never raises.
    """
    stripped = value.strip()
    if not stripped:
        return stripped
    return stripped if stripped.startswith("paper_module.") else f"paper_module.{stripped}"


def _paper_module_required_residual(relation_id: str, reason: str) -> dict[str, Any]:
    """
    - Teleology: build a typed REQUIRED residual-pressure row for an unpopulated paper-module relation.
    - Guarantee: returns a dict with relation_id, status 'residual_pressure', requirement 'required', reason, and the population pressure_ref.
    - Fails: never raises.
    """
    return {
        "relation_id": relation_id,
        "status": "residual_pressure",
        "requirement": "required",
        "reason": reason,
        "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
    }


def _paper_module_selective_residual(relation_id: str, reason: str) -> dict[str, Any]:
    """
    - Teleology: build a typed SELECTIVE residual-pressure row for an unpopulated paper-module relation.
    - Guarantee: returns a dict with relation_id, status 'residual_pressure', requirement 'selective', reason, and the population pressure_ref.
    - Fails: never raises.
    """
    return {
        "relation_id": relation_id,
        "status": "residual_pressure",
        "requirement": "selective",
        "reason": reason,
        "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
    }


def _paper_module_resolution_context(root: str | Path | None) -> dict[str, Any]:
    """
    - Teleology: precompute the sets of known instance ids used to mark paper-module edges resolved vs unresolved.
    - Guarantee: returns a dict of known_organs/mechanisms/concepts/principles/axioms/paper_modules id sets for the root.
    - Fails: never raises; absent corpora yield empty sets.
    """
    return {
        "known_organs": set(expected_organ_instances(root)),
        "known_mechanisms": set(expected_mechanism_instances(root)),
        "known_concepts": set(expected_concept_instances(root)),
        "known_principles": set(expected_principle_instances(root)),
        "known_axioms": set(expected_axiom_instances(root)),
        "known_paper_modules": {
            str(row.get("id") or "")
            for row in _paper_module_source_rows(root)
            if row.get("id")
        },
    }


def build_paper_module_instance_from_source_row(
    row: dict[str, Any],
    root: str | Path | None = None,
    *,
    resolution_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: project one paper-module source row into a governed JSON instance with typed subject/law/dependency/code edges and residuals.
    - Guarantee: returns the instance dict with relationships.edges, unpopulated_selective_relations, omission_receipt, anti_claims, and paper_module_payload; targets are marked resolved only when their id is in the resolution context.
    - Fails: never raises; missing subjects/refs become required or selective residual rows rather than errors.
    - When-needed: regenerating paper-module instances or diagnosing a single module's edges.
    - Escalates-to: expected_paper_module_instances, std_microcosm_paper_module.json.
    - Non-goal: building an instance does not flip source authority off the capsule/markdown source, nor prove runtime correctness or release readiness.
    """
    module_id = str(row.get("id") or "").strip()
    source_ref = str(row.get("source_ref") or module_id)
    source_authority = str(row.get("source_authority") or "legacy_markdown_projection")
    legacy_markdown = str(row.get("legacy_markdown_projection") or "").strip()
    context = resolution_context or _paper_module_resolution_context(root)
    known_organs = _context_string_set(context.get("known_organs"))
    known_mechanisms = _context_string_set(context.get("known_mechanisms"))
    known_concepts = _context_string_set(context.get("known_concepts"))
    known_principles = _context_string_set(context.get("known_principles"))
    known_axioms = _context_string_set(context.get("known_axioms"))
    known_paper_modules = _context_string_set(context.get("known_paper_modules"))
    subjects = [item for item in _as_list(row.get("subjects")) if isinstance(item, dict)]
    code_loci = _code_locus_rows(row)
    concept_refs = _unique_strings(row.get("concept_refs"))
    principle_refs = _unique_strings(row.get("principle_refs"))
    axiom_refs = _unique_strings(row.get("axiom_refs"))
    depends_on = [_paper_module_target_id(value) for value in _unique_strings(row.get("depends_on"))]
    edges: list[dict[str, Any]] = []
    residuals: list[dict[str, Any]] = []

    for index, subject in enumerate(subjects):
        target_kind = str(subject.get("kind") or "").strip()
        target_id = str(subject.get("ref") or "").strip()
        if target_kind not in {"organ", "mechanism"} or not target_id:
            residuals.append(
                _paper_module_required_residual(
                    "paper_module.explains.organ_or_mechanism",
                    "Paper-module subject row is missing a supported organ/mechanism kind or ref.",
                )
            )
            continue
        known_targets = known_organs if target_kind == "organ" else known_mechanisms
        edges.append(
            _edge(
                relation_id="paper_module.explains.organ_or_mechanism",
                relation_verb="explains",
                reverse_verb="explained_by",
                target_kind=target_kind,
                target_id=target_id,
                source_ref=f"{source_ref}.subjects[{index}]",
                target_status=(
                    "resolved_json_instance" if target_id in known_targets else "unresolved_json_instance"
                ),
                justification="Paper-module capsule names this organ/mechanism as an explained subject.",
            )
        )
    if not subjects:
        residuals.append(
            _paper_module_required_residual(
                "paper_module.explains.organ_or_mechanism",
                "Paper module has no JSON-capsule subject rows; legacy markdown title/slug is not enough to infer a required subject.",
            )
        )

    for concept_id in concept_refs:
        edges.append(
            _edge(
                relation_id="paper_module.governed_by.concept",
                relation_verb="governed_by",
                reverse_verb="governs",
                target_kind="concept",
                target_id=concept_id,
                source_ref=f"{source_ref}.concept_refs",
                target_status="resolved_json_instance" if concept_id in known_concepts else "unresolved_json_instance",
                justification="Paper-module source row names this concept as a governing concept.",
            )
        )
    if not concept_refs:
        residuals.append(
            _paper_module_selective_residual(
                "paper_module.governed_by.concept",
                "Paper-module source row does not name governed concept ids.",
            )
        )

    for principle_id in principle_refs:
        edges.append(
            _edge(
                relation_id="paper_module.governed_by.principle",
                relation_verb="governed_by",
                reverse_verb="governs",
                target_kind="principle",
                target_id=principle_id,
                source_ref=f"{source_ref}.principle_refs",
                target_status=(
                    "resolved_json_instance" if principle_id in known_principles else "unresolved_json_instance"
                ),
                justification="Paper-module source row names this governing principle.",
            )
        )
    if not principle_refs:
        residuals.append(
            _paper_module_selective_residual(
                "paper_module.governed_by.principle",
                "Paper-module source row does not name governing principle ids.",
            )
        )

    for axiom_id in axiom_refs:
        edges.append(
            _edge(
                relation_id="paper_module.abides_by.axiom",
                relation_verb="abides_by",
                reverse_verb="constrains",
                target_kind="axiom",
                target_id=axiom_id,
                source_ref=f"{source_ref}.axiom_refs",
                target_status="resolved_json_instance" if axiom_id in known_axioms else "unresolved_json_instance",
                justification="Paper-module source row names this axiom as a law boundary.",
            )
        )
    if not axiom_refs:
        residuals.append(
            _paper_module_selective_residual(
                "paper_module.abides_by.axiom",
                "Paper-module source row does not name axiom ids.",
            )
        )

    for target_module_id in depends_on:
        edges.append(
            _edge(
                relation_id="paper_module.depends_on.paper_module",
                relation_verb="depends_on",
                reverse_verb="depended_on_by",
                target_kind="paper_module",
                target_id=target_module_id,
                source_ref=f"{source_ref}.depends_on",
                target_status=(
                    "resolved_json_instance"
                    if target_module_id in known_paper_modules
                    else "unresolved_json_instance"
                ),
                justification="Paper-module source row names this sibling/dependency paper module.",
            )
        )
    if not depends_on:
        residuals.append(
            _paper_module_selective_residual(
                "paper_module.depends_on.paper_module",
                "Paper-module source row does not name sibling/dependency module ids.",
            )
        )

    for index, locus in enumerate(code_loci):
        rel = str(locus.get("path") or "")
        edges.append(
            _edge(
                relation_id="paper_module.cites.code_locus",
                relation_verb="cites",
                reverse_verb="cited_by",
                target_kind="code_locus",
                target_id=rel,
                source_ref=f"{source_ref}.code_loci[{index}]",
                target_status=_code_locus_target_status(root, locus),
                justification=str(
                    locus.get("role")
                    or "Paper-module source row cites this code locus as an implementation/evidence path."
                ),
            )
        )
    if not code_loci:
        residuals.append(
            _paper_module_selective_residual(
                "paper_module.cites.code_locus",
                "Paper-module source row does not name code loci.",
            )
        )

    compression = _as_dict(row.get("compression"))
    title = str(row.get("title") or _paper_module_slug(module_id).replace("_", " ").title())
    one_line = str(compression.get("one_line") or title)
    authority_ceiling = str(
        compression.get("authority_ceiling")
        or "Paper-module structure only; no runtime correctness, release authority, or public-private equivalence claim."
    )
    source_refs = [
        {
            "path": source_ref,
            "role": (
                "json_capsule_source_of_record_until_instance_authority_flip"
                if source_authority == "json_capsule"
                else "legacy_markdown_projection_inventory_not_source_authority"
            ),
        },
        {
            "path": _paper_module_instance_rel(module_id),
            "role": "governed_json_parity_seed",
        },
    ]
    if legacy_markdown:
        source_refs.append(
            {
                "path": legacy_markdown,
                "role": "legacy_markdown_projection_not_source_authority",
            }
        )
    return {
        "id": module_id,
        "kind": "paper_module",
        "schema_version": PAPER_MODULE_INSTANCE_SCHEMA_VERSION,
        "title": title,
        "statement": one_line,
        "compression": _json(compression),
        "subjects": _json(subjects),
        "status": "active" if source_authority == "json_capsule" else "legacy_projection_only",
        "created_at": AXIOM_MIGRATION_CREATED_AT,
        "authority_boundary": (
            "public_paper_module_json_seeded_from_capsule_registry_not_legacy_markdown_authority"
            if source_authority == "json_capsule"
            else "legacy_markdown_indexed_as_governed_json_import_without_capsule_authority"
        ),
        "source_refs": source_refs,
        "relationships": {
            "source_ref": source_ref,
            "legacy_markdown_projection": legacy_markdown,
            "source_authority": source_authority,
            "subjects": _json(subjects),
            "concept_refs": concept_refs,
            "principle_refs": principle_refs,
            "axiom_refs": axiom_refs,
            "depends_on": depends_on,
            "code_loci": _json(code_loci),
            "edges": edges,
            "unpopulated_selective_relations": residuals,
        },
        "validator_refs": [
            "microcosm-substrate/scripts/build_doctrine_projection.py --check-paper-module-corpus"
        ],
        "receipt_refs": _strings(row.get("receipt_refs")),
        "omission_receipt": {
            "omitted": [
                "private macro source bodies",
                "raw operator voice",
                "provider payload bodies",
                "public Markdown prose body round-trip equivalence",
                "legacy-only subject edges not named by JSON capsules",
            ],
            "reason": (
                "Paper-module instance preserves capsule fields or a legacy Markdown path inventory. "
                "Legacy-only rows do not flip source authority; required subjects and selective "
                "law/neighbour/code edges remain residual unless source JSON names ids."
            ),
            "drilldown": source_ref,
            "residual_pressure": [
                {
                    "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
                    "gap_class": "paper_module_json_capsule_and_edge_population",
                    "reentry_condition": "Author JSON capsules and typed subject/edge rows from source evidence, then regenerate paper-module JSON instances and projections.",
                }
            ],
        },
        "anti_claims": [
            "This paper-module JSON row does not prove runtime correctness, release readiness, or whole-system completeness.",
            "Legacy Markdown presence is not treated as source authority or as typed subject evidence.",
            "Capsule-backed subject/code edges are structural references only; they do not prove implementation correctness.",
        ],
        "paper_module_payload": {
            "contract_version": "microcosm_paper_module_instance_payload_v1",
            "source_authority": source_authority,
            "legacy_markdown_projection": legacy_markdown,
            "authority_ceiling": authority_ceiling,
            "generated_projections": _json(_as_dict(row.get("generated_projections"))),
            "strangler_note": str(row.get("strangler_note") or ""),
            "projection_contract": {
                "source_json_rel": _paper_module_instance_rel(module_id),
                "markdown_status": (
                    "legacy_import_projection_until_roundtrip_builder"
                    if legacy_markdown
                    else "missing_legacy_projection"
                ),
                "authority_flip_status": "not_flipped",
            },
            "support_contract": {
                "computed_by": "microcosm_core.doctrine_lattice.build_doctrine_projection",
                "support_status": (
                    "json_capsule_subject_edges_computed_not_correctness_claim"
                    if source_authority == "json_capsule"
                    else "legacy_markdown_path_indexed_required_subject_gap"
                ),
            },
            "source_row": _json(row),
        },
    }


def expected_paper_module_instances(root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: compute the full expected paper-module instance corpus from source.
    - Guarantee: returns {module_id: instance} reproducibly derived from capsule/markdown source rows.
    - Fails: never raises; rows without an id are skipped.
    - Escalates-to: build_paper_module_instance_from_source_row.
    """
    return _expected_paper_module_instances_cached(_root_key(root))


@lru_cache(maxsize=32)
def _expected_paper_module_instances_cached(root_key: str) -> dict[str, dict[str, Any]]:
    """
    - Teleology: lru-cached backend for expected_paper_module_instances keyed by root string.
    - Guarantee: returns the {module_id: instance} mapping; identical root_key returns the cached mapping.
    - Fails: never raises beyond underlying source reads.
    """
    root = Path(root_key)
    source_rows = _paper_module_source_rows(root)
    context = _paper_module_resolution_context(root)
    return {
        str(row.get("id")): build_paper_module_instance_from_source_row(
            row,
            root,
            resolution_context=context,
        )
        for row in source_rows
        if row.get("id")
    }


def load_paper_module_instances(root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: load the paper-module JSON instances already written to disk.
    - Guarantee: returns {id: payload} for each parseable paper_modules/*.json carrying an id; {} if the directory is absent.
    - Fails: propagates read_json_strict errors on a malformed instance file.
    - Escalates-to: paper_modules/*.json.
    """
    paper_dir = _path(root, PAPER_MODULE_INSTANCE_DIR_REL)
    rows: dict[str, dict[str, Any]] = {}
    if not paper_dir.is_dir():
        return rows
    for path in sorted(paper_dir.glob("*.json")):
        payload = _as_dict(read_json_strict(path))
        instance_id = str(payload.get("id") or "")
        if instance_id:
            rows[instance_id] = payload
    return rows


def validate_paper_module_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: check that written paper-module instances match the source-derived expectation and carry required subjects and edge justifications.
    - Guarantee: returns {status: 'pass'|'blocked', expected_count, actual_count, errors[]}; status 'pass' iff no missing/extra/drift/required-subject/justification errors.
    - Fails: never raises; each defect is an error row.
    - When-needed: --check-paper-module-corpus or doctrine-projection validation.
    - Escalates-to: expected_paper_module_instances, build_doctrine_projection.
    - Non-goal: passing proves source-reproducible parity only, not capsule completeness or runtime correctness.
    """
    expected = expected_paper_module_instances(root)
    actual = load_paper_module_instances(root)
    errors: list[dict[str, Any]] = []
    for module_id in sorted(set(expected) - set(actual), key=_id_sort_key):
        _add_error(
            errors,
            code="paper_module_json_instance_missing",
            path=_paper_module_instance_rel(module_id),
            message="Expected paper-module JSON instance is missing.",
            paper_module_id=module_id,
        )
    for module_id in sorted(set(actual) - set(expected), key=_id_sort_key):
        _add_error(
            errors,
            code="paper_module_json_instance_extra",
            path=_paper_module_instance_rel(module_id),
            message="Paper-module JSON instance has no source capsule or legacy Markdown file.",
            paper_module_id=module_id,
        )
    for module_id in sorted(set(expected) & set(actual), key=_id_sort_key):
        if actual[module_id] != expected[module_id]:
            _add_error(
                errors,
                code="paper_module_json_instance_drift",
                path=_paper_module_instance_rel(module_id),
                message="Paper-module JSON instance is not reproducible from capsule/legacy source.",
                paper_module_id=module_id,
            )
        relationships = _as_dict(actual[module_id].get("relationships"))
        edges = [edge for edge in _as_list(relationships.get("edges")) if isinstance(edge, dict)]
        residuals = [
            residual
            for residual in _as_list(relationships.get("unpopulated_selective_relations"))
            if isinstance(residual, dict)
        ]
        if not any(edge.get("relation_id") == "paper_module.explains.organ_or_mechanism" for edge in edges) and not any(
            residual.get("relation_id") == "paper_module.explains.organ_or_mechanism"
            for residual in residuals
        ):
            _add_error(
                errors,
                code="paper_module_required_subject_unaccounted",
                path=f"{_paper_module_instance_rel(module_id)}::relationships",
                message="Paper-module required subject relation must be resolved or carried as residual pressure.",
                paper_module_id=module_id,
            )
        for index, edge in enumerate(edges):
            if not _as_dict(edge.get("justification")).get("source_ref"):
                _add_error(
                    errors,
                    code="paper_module_edge_missing_source_ref",
                    path=f"{_paper_module_instance_rel(module_id)}::relationships.edges[{index}]",
                    message="Paper-module edge is missing a source_ref justification.",
                    paper_module_id=module_id,
                )
    return {
        "schema_version": "microcosm_paper_module_instance_validation_v1",
        "status": "pass" if not errors else "blocked",
        "expected_count": len(expected),
        "actual_count": len(actual),
        "errors": errors,
    }


def build_paper_module_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: aggregate paper-module instance parity, residual detail, and migration counts into a corpus projection.
    - Guarantee: returns a corpus dict (counts, residual detail rows, legacy-only/required-subject ids, parity_status, embedded validation).
    - Fails: never raises.
    - Escalates-to: validate_paper_module_instance_corpus.
    """
    expected = expected_paper_module_instances(root)
    actual = load_paper_module_instances(root)
    validation = validate_paper_module_instance_corpus(root)
    relation_requirements = _relation_requirement_by_id(root)
    residual_details = _residual_relation_detail_rows(
        "paper_module",
        expected.values(),
        authority_boundary=(
            "computed_from_paper_module_capsule_or_legacy_residuals_not_source_edge_inference"
        ),
        requirement_by_relation_id=relation_requirements,
        source_ref_keys=("source_ref",),
    )
    selective_residual_details = [
        row for row in residual_details if row.get("requirement") == "selective"
    ]
    required_subject_gap_ids = [
        module_id
        for module_id, instance in expected.items()
        if any(
            isinstance(residual, dict)
            and residual.get("relation_id") == "paper_module.explains.organ_or_mechanism"
            for residual in _as_list(_as_dict(instance.get("relationships")).get("unpopulated_selective_relations"))
        )
    ]
    legacy_only_ids = [
        module_id
        for module_id, instance in expected.items()
        if _as_dict(instance.get("paper_module_payload")).get("source_authority") == "legacy_markdown_projection"
    ]
    return {
        "schema_version": "microcosm_paper_module_instance_corpus_v1",
        "expected_paper_module_count": len(expected),
        "json_instance_count": len(actual),
        "expected_json_ids": sorted(expected, key=_id_sort_key),
        "json_instance_ids": sorted(actual, key=_id_sort_key),
        "missing_json_ids": sorted(set(expected) - set(actual), key=_id_sort_key),
        "extra_json_ids": sorted(set(actual) - set(expected), key=_id_sort_key),
        "json_capsule_backed_count": len(expected) - len(legacy_only_ids),
        "legacy_only_count": len(legacy_only_ids),
        "legacy_only_ids": sorted(legacy_only_ids, key=_id_sort_key),
        "required_subject_gap_count": len(required_subject_gap_ids),
        "required_subject_gap_ids": sorted(required_subject_gap_ids, key=_id_sort_key),
        "unpopulated_selective_relation_count": _unpopulated_relation_count(expected),
        "residual_relation_count": len(residual_details),
        "residual_relation_counts_by_relation_id": _relation_count_by_id(
            residual_details
        ),
        "residual_relation_counts_by_requirement": _relation_count_by_requirement(
            residual_details
        ),
        "residual_relation_detail_count": len(residual_details),
        "residual_relation_details": residual_details,
        "selective_residual_relation_count": len(selective_residual_details),
        "selective_residual_relation_counts_by_relation_id": _relation_count_by_id(
            selective_residual_details
        ),
        "selective_residual_relation_detail_count": len(selective_residual_details),
        "selective_residual_relation_details": selective_residual_details,
        "parity_status": validation["status"],
        "authority_flip_status": "not_flipped",
        "validation": validation,
        "source_refs": {
            "paper_module_capsules": PAPER_MODULE_CAPSULES_REL,
            "legacy_markdown": f"{PAPER_MODULE_INSTANCE_DIR_REL}/*.md",
            "json_instances": f"{PAPER_MODULE_INSTANCE_DIR_REL}/*.json",
        },
        "anti_claim": "Paper-module JSON parity is structural migration progress; legacy-only rows remain import indexes and do not prove capsule authority, typed subjects, or runtime correctness.",
    }


def write_paper_module_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: write every expected paper-module instance to disk and return the resulting corpus.
    - Guarantee: writes paper_modules/<id>.json for expected ids whose sorted-keys JSON differs from disk, removes stale generated JSON instances with no current source row, then returns build_paper_module_instance_corpus.
    - Fails: raises OSError if a target file cannot be written.
    - When-needed: --write-style regeneration of paper-module instances.
    - Escalates-to: build_paper_module_instance_corpus.
    - Non-goal: writing instances does not flip source authority or authorize release.
    """
    resolved = _root(root)
    paper_dir = resolved / PAPER_MODULE_INSTANCE_DIR_REL
    paper_dir.mkdir(parents=True, exist_ok=True)
    expected = expected_paper_module_instances(resolved)
    for module_id, payload in expected.items():
        target = resolved / _paper_module_instance_rel(module_id)
        text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        if not target.exists() or target.read_text(encoding="utf-8") != text:
            target.write_text(text, encoding="utf-8")
    for module_id in sorted(set(load_paper_module_instances(resolved)) - set(expected), key=_id_sort_key):
        target = resolved / _paper_module_instance_rel(module_id)
        if target.exists():
            target.unlink()
    return build_paper_module_instance_corpus(resolved)


SKILL_SOURCE_DEFAULTS: dict[str, dict[str, Any]] = {
    "cold_start_navigation": {
        "triad_role": "author",
        "operates_standard": "std_microcosm_atlas_route",
        "acts_on_kind": "atlas_route",
        "trigger_summary": [
            "Fresh public clone entry into microcosm-substrate.",
            "Cold reader or Type A agent needs a first-screen route before opening receipts.",
        ],
        "workflow_summary": [
            "Run the source-root probe before install-oriented work.",
            "Open the generated first-screen route card before raw receipt trees.",
            "Use status, authority, workingness, proof-lab, observe, and serve cards as typed drilldowns.",
        ],
        "concept_refs": ["concept.first_screen_doctrine_effect_frame"],
        "mechanism_refs": [],
        "mapping_basis": (
            "The markdown names atlas/entry_packet first-screen routes and a Type A doctrine_effect_frame "
            "drilldown; this maps the skill to atlas-route operation without claiming full navigation proof."
        ),
    },
    "pattern_assimilation": {
        "triad_role": "refine_instance",
        "operates_standard": "std_microcosm_pattern_assimilation_step",
        "acts_on_kind": "pattern_assimilation_step",
        "trigger_summary": [
            "Reducer has authorized a bounded pattern_assimilation_step closeout lane.",
            "A landed public organ needs a refinement or typed nothing_to_refine receipt.",
        ],
        "workflow_summary": [
            "Check stewardship and the next-best lane before closing an organ refinement pass.",
            "Record either a concrete refinement receipt or a typed nothing_to_refine receipt.",
            "Route reusable lessons to the owning standard, skill, paper module, or ledger lane.",
        ],
        "concept_refs": [],
        "mechanism_refs": [],
        "mapping_basis": (
            "The markdown explicitly names the pattern_assimilation_step closeout lane and its receipt floor."
        ),
    },
}


def _skill_instance_rel(skill_id: str) -> str:
    """
    - Teleology: compute the governed JSON instance path for a skill id.
    - Guarantee: returns 'skills/<slug>.json' (slug strips a leading 'skill.').
    - Fails: never raises.
    """
    slug = skill_id.split(".", 1)[1] if skill_id.startswith("skill.") else skill_id
    return f"{SKILL_INSTANCE_DIR_REL}/{slug}.json"


def _skill_markdown_rel(skill_id: str) -> str:
    """
    - Teleology: compute the legacy markdown source path for a skill id.
    - Guarantee: returns 'skills/<slug>.md' (slug strips a leading 'skill.').
    - Fails: never raises.
    """
    slug = skill_id.split(".", 1)[1] if skill_id.startswith("skill.") else skill_id
    return f"{SKILL_INSTANCE_DIR_REL}/{slug}.md"


def _skill_markdown_mapping(text: str, source_ref: str) -> dict[str, Any]:
    """
    - Teleology: extract the typed-skill-mapping JSON block from a skill markdown body.
    - Guarantee: returns the parsed mapping dict, or {} when the '## Typed Skill Mapping' section or its json block is absent.
    - Fails: propagates loads_json_strict errors when the json block is present but malformed.
    - Escalates-to: skills/*.md typed skill mapping section.
    """
    section = re.search(
        r"^## Typed Skill Mapping\s*$"
        r"(?P<body>.*?)(?=^##\s+|\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not section:
        return {}
    block = re.search(
        r"```json\s*(?P<payload>.*?)\s*```",
        section.group("body"),
        flags=re.DOTALL,
    )
    if not block:
        return {}
    parsed = loads_json_strict(
        block.group("payload"),
        source=f"{source_ref}::typed_skill_mapping",
    )
    return _as_dict(parsed)


def _skill_source_rows(root: str | Path | None) -> list[dict[str, Any]]:
    """
    - Teleology: read each skill markdown file into a typed source row (identity, digest, triad role, typed mapping).
    - Guarantee: returns one row per non-generated skills/*.md carrying id, source_ref, source_digest, line count, triad_role, and mapping fields.
    - Fails: propagates loads_json_strict errors only when a present typed-mapping block is malformed.
    - Escalates-to: skills/*.md.
    """
    resolved = _root(root)
    skill_dir = resolved / SKILL_INSTANCE_DIR_REL
    if not skill_dir.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(skill_dir.glob("*.md")):
        if path.name.endswith(".generated.md"):
            continue
        slug = path.stem
        text = path.read_text(encoding="utf-8")
        source_ref = f"{SKILL_INSTANCE_DIR_REL}/{path.name}"
        title_match = re.search(r"^#\s+(.+?)\s*$", text, flags=re.MULTILINE)
        defaults = _as_dict(SKILL_SOURCE_DEFAULTS.get(slug))
        typed_mapping = {
            **defaults,
            **_skill_markdown_mapping(text, source_ref),
        }
        rows.append(
            {
                "id": f"skill.{slug}",
                "slug": slug,
                "title": title_match.group(1).strip() if title_match else slug.replace("_", " ").title(),
                "source_ref": source_ref,
                "source_digest": _sha256(path),
                "source_line_count": len(text.splitlines()),
                "triad_role": str(typed_mapping.get("triad_role") or "refine_instance"),
                "operates_standard": str(typed_mapping.get("operates_standard") or ""),
                "acts_on_kind": str(typed_mapping.get("acts_on_kind") or ""),
                "triggers": _strings(typed_mapping.get("trigger_summary")),
                "workflow": _strings(typed_mapping.get("workflow_summary")),
                "concept_refs": _strings(typed_mapping.get("concept_refs")),
                "mechanism_refs": _strings(typed_mapping.get("mechanism_refs")),
                "mapping_basis": str(
                    typed_mapping.get("mapping_basis")
                    or "No typed source mapping beyond the markdown heading is available."
                ),
            }
        )
    return rows


def _standard_contract_exists(root: str | Path | None, standard_id: str) -> bool:
    """
    - Teleology: test whether a standards/<id>.json contract file exists.
    - Guarantee: returns True iff standard_id is non-empty and the file resolves under root.
    - Fails: never raises.
    """
    return bool(standard_id) and _path(root, f"standards/{standard_id}.json").is_file()


@lru_cache(maxsize=128)
def _standard_declared_kind_ids(root_key: str) -> frozenset[str]:
    """
    - Teleology: collect the kind_ids declared across std_microcosm_*.json standard files.
    - Guarantee: returns a frozenset of declared kind_id strings; empty frozenset if the standards dir is absent.
    - Fails: propagates read_json_strict errors on a malformed standard file.
    """
    standard_dir = Path(root_key) / STANDARD_INSTANCE_DIR_REL
    if not standard_dir.is_dir():
        return frozenset()
    kind_ids: set[str] = set()
    for path in sorted(standard_dir.glob("std_microcosm_*.json")):
        payload = read_json_strict(path)
        kind_id = str(payload.get("kind_id") or "").strip()
        if kind_id:
            kind_ids.add(kind_id)
    return frozenset(kind_ids)


def _doctrine_kind_contract_exists(root: str | Path | None, kind_id: str) -> bool:
    """
    - Teleology: test whether a doctrine kind has a governing standard contract (by filename or declared kind_id).
    - Guarantee: returns True iff a std_microcosm_<kind_id>.json exists or kind_id is in the declared kind-id set.
    - Fails: never raises beyond underlying standard reads.
    """
    if not kind_id:
        return False
    return _path(root, f"standards/std_microcosm_{kind_id}.json").is_file() or (
        kind_id in _standard_declared_kind_ids(_root_key(root))
    )



def _skill_required_residual(relation_id: str, reason: str) -> dict[str, Any]:
    """
    - Teleology: build a typed REQUIRED residual-pressure row for an unpopulated skill relation.
    - Guarantee: returns a dict with relation_id, status 'residual_pressure', requirement 'required', reason, and pressure_ref.
    - Fails: never raises.
    """
    return {
        "relation_id": relation_id,
        "status": "residual_pressure",
        "requirement": "required",
        "reason": reason,
        "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
    }


def _skill_selective_residual(relation_id: str, reason: str) -> dict[str, Any]:
    """
    - Teleology: build a typed SELECTIVE residual-pressure row for an unpopulated skill relation.
    - Guarantee: returns a dict with relation_id, status 'residual_pressure', requirement 'selective', reason, and pressure_ref.
    - Fails: never raises.
    """
    return {
        "relation_id": relation_id,
        "status": "residual_pressure",
        "requirement": "selective",
        "reason": reason,
        "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
    }


def build_skill_instance_from_source_row(
    row: dict[str, Any],
    root: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: project one skill markdown source row into a governed JSON instance with operates/acts_on/uses/applies edges and residuals.
    - Guarantee: returns the skill instance dict; required relations (operates.standard, acts_on.doctrine_kind) that are absent become required residuals, optional ones become selective residuals.
    - Fails: never raises; missing mappings become residual rows.
    - When-needed: regenerating skill instances or diagnosing one skill's typed mapping.
    - Escalates-to: expected_skill_instances, std_microcosm_skill.json.
    - Non-goal: building an instance does not flip authority off the skill markdown or prove agent uptake.
    """
    skill_id = str(row.get("id") or "")
    source_ref = str(row.get("source_ref") or _skill_markdown_rel(skill_id))
    standard = load_kind_standards(root)["skill"]
    operates_standard = str(row.get("operates_standard") or "")
    acts_on_kind = str(row.get("acts_on_kind") or "")
    concept_refs = _strings(row.get("concept_refs"))
    mechanism_refs = _strings(row.get("mechanism_refs"))
    known_concepts = set(expected_concept_instances(root))
    known_mechanisms = set(expected_mechanism_instances(root))
    edges: list[dict[str, Any]] = []
    residuals: list[dict[str, Any]] = []

    if operates_standard:
        edges.append(
            _edge(
                relation_id="skill.operates.standard",
                relation_verb="operates",
                reverse_verb="operated_by",
                target_kind="standard",
                target_id=operates_standard,
                source_ref=f"{source_ref}::typed_skill_mapping.operates_standard",
                target_status=(
                    "resolved_standard_contract"
                    if _standard_contract_exists(root, operates_standard)
                    else "unresolved_standard_contract"
                ),
                justification=str(row.get("mapping_basis") or "Skill source mapping names the operated standard."),
            )
        )
    else:
        residuals.append(
            _skill_required_residual(
                "skill.operates.standard",
                "Skill markdown source does not name an operated standard.",
            )
        )

    if acts_on_kind:
        edges.append(
            _edge(
                relation_id="skill.acts_on.doctrine_kind",
                relation_verb="acts_on",
                reverse_verb="acted_on_by",
                target_kind="doctrine_kind",
                target_id=acts_on_kind,
                source_ref=f"{source_ref}::typed_skill_mapping.acts_on_kind",
                target_status=(
                    "resolved_doctrine_kind_contract"
                    if _doctrine_kind_contract_exists(root, acts_on_kind)
                    else "unresolved_doctrine_kind_contract"
                ),
                justification=str(row.get("mapping_basis") or "Skill source mapping names the acted-on doctrine kind."),
            )
        )
    else:
        residuals.append(
            _skill_required_residual(
                "skill.acts_on.doctrine_kind",
                "Skill markdown source does not name an acted-on doctrine kind.",
            )
        )

    for concept_id in concept_refs:
        edges.append(
            _edge(
                relation_id="skill.applies.concept",
                relation_verb="applies",
                reverse_verb="applied_by",
                target_kind="concept",
                target_id=concept_id,
                source_ref=f"{source_ref}::typed_skill_mapping.concept_refs",
                target_status=(
                    "resolved_json_instance" if concept_id in known_concepts else "unresolved_json_instance"
                ),
                justification="Skill source mapping names this concept as an applied doctrine boundary.",
            )
        )
    if not concept_refs:
        residuals.append(
            _skill_selective_residual(
                "skill.applies.concept",
                "Skill markdown source does not name applied concept ids.",
            )
        )

    for mechanism_id in mechanism_refs:
        edges.append(
            _edge(
                relation_id="skill.uses.mechanism",
                relation_verb="uses",
                reverse_verb="used_by",
                target_kind="mechanism",
                target_id=mechanism_id,
                source_ref=f"{source_ref}::typed_skill_mapping.mechanism_refs",
                target_status=(
                    "resolved_json_instance" if mechanism_id in known_mechanisms else "unresolved_json_instance"
                ),
                justification="Skill source mapping names this mechanism as an operational dependency.",
            )
        )
    if not mechanism_refs:
        residuals.append(
            _skill_selective_residual(
                "skill.uses.mechanism",
                "Skill markdown source does not name used mechanism ids.",
            )
        )

    return {
        "id": skill_id,
        "kind": "skill",
        "schema_version": SKILL_INSTANCE_SCHEMA_VERSION,
        "title": str(row.get("title") or skill_id),
        "statement": str(row.get("title") or skill_id),
        "triad_role": str(row.get("triad_role") or "refine_instance"),
        "operates_standard": operates_standard,
        "acts_on_kind": acts_on_kind,
        "triggers": _strings(row.get("triggers")),
        "workflow": _strings(row.get("workflow")),
        "mechanism_refs": mechanism_refs,
        "concept_refs": concept_refs,
        "validation": [
            "microcosm-substrate/scripts/build_doctrine_projection.py --check-skill-corpus",
            "microcosm-substrate/scripts/build_doctrine_projection.py --check",
        ],
        "status": "active",
        "created_at": AXIOM_MIGRATION_CREATED_AT,
        "authority_boundary": (
            "public_skill_json_seeded_from_skill_markdown_projection_not_authority_flip_until_parity_receipt"
        ),
        "source_refs": [
            {
                "path": source_ref,
                "role": "skill_markdown_source_projection_until_json_parity_flip",
            },
            {
                "path": _skill_instance_rel(skill_id),
                "role": "governed_json_parity_seed",
            },
        ],
        "relationships": {
            "source_markdown_ref": source_ref,
            "source_markdown_digest": row.get("source_digest"),
            "source_markdown_line_count": row.get("source_line_count"),
            "triad_role": str(row.get("triad_role") or "refine_instance"),
            "operates_standard": operates_standard,
            "acts_on_kind": acts_on_kind,
            "concept_refs": concept_refs,
            "mechanism_refs": mechanism_refs,
            "edges": edges,
            "unpopulated_selective_relations": residuals,
        },
        "validator_refs": ["validator.microcosm.skill"],
        "receipt_refs": [],
        "omission_receipt": {
            "omitted": [
                "private macro skill bodies",
                "provider payload bodies",
                "operator-thread examples",
                "full source markdown body",
                "mechanism or concept neighbours not named by typed source mapping",
            ],
            "reason": (
                "Skill instance preserves public-safe markdown source identity, digest, and typed route mapping only. "
                "JSON parity does not prove full skill-body completeness or runtime correctness."
            ),
            "drilldown": source_ref,
            "residual_pressure": [
                {
                    "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
                    "gap_class": "skill_selective_edges_unpopulated",
                    "reentry_condition": "Bind skill.uses mechanism and skill.applies concept edges only when source evidence names ids.",
                }
            ],
        },
        "anti_claims": [
            "This skill JSON seed does not flip source authority away from the current skill markdown projection.",
            "Resolved operated-standard and acted-on-kind edges are structural route mappings, not proof the skill is complete or used correctly by agents.",
            "Absent mechanism or concept neighbours are residual pressure, not evidence that no such neighbours exist.",
            "Generated graph, health, and atlas projections cannot be read back as source evidence.",
        ],
        "skill_payload": {
            "contract_version": "microcosm_skill_instance_payload_v1",
            "source_markdown_digest": row.get("source_digest"),
            "source_markdown_line_count": row.get("source_line_count"),
            "mapping_basis": row.get("mapping_basis"),
            "support_contract": {
                "computed_by": "microcosm_core.doctrine_lattice.build_doctrine_projection",
                "support_status": "required_skill_edges_computed_not_runtime_correctness_claim",
            },
            "projection_contract": {
                "json_status": "generated_parity_seed",
                "markdown_status": "legacy_public_projection_source_until_parity_flip",
                "source_json_rel": _skill_instance_rel(skill_id),
                "legacy_markdown_rel": source_ref,
            },
            "migration_contract": {
                "source_of_record": f"{SKILL_INSTANCE_DIR_REL}/*.md",
                "authority_flip_status": "not_flipped",
                "parity_validator": "microcosm-substrate/scripts/build_doctrine_projection.py --check-skill-corpus",
                "residual_pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
            },
        },
    }


def expected_skill_instances(root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: compute the full expected skill instance corpus from skill markdown sources.
    - Guarantee: returns {skill_id: instance} reproducibly derived from skills/*.md rows.
    - Fails: never raises; rows without an id are skipped.
    - Escalates-to: build_skill_instance_from_source_row.
    """
    return _expected_skill_instances_cached(_root_key(root))


@lru_cache(maxsize=32)
def _expected_skill_instances_cached(root_key: str) -> dict[str, dict[str, Any]]:
    """
    - Teleology: lru-cached backend for expected_skill_instances keyed by root string.
    - Guarantee: returns the {skill_id: instance} mapping; identical root_key returns the cached mapping.
    - Fails: never raises beyond underlying source reads.
    """
    root = Path(root_key)
    return {
        str(row["id"]): build_skill_instance_from_source_row(row, root)
        for row in _skill_source_rows(root)
        if row.get("id")
    }


def load_skill_instances(root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: load the skill JSON instances already written to disk.
    - Guarantee: returns {id: payload} for each parseable skills/*.json carrying an id; {} if the directory is absent.
    - Fails: propagates read_json_strict errors on a malformed instance file.
    - Escalates-to: skills/*.json.
    """
    skill_dir = _path(root, SKILL_INSTANCE_DIR_REL)
    rows: dict[str, dict[str, Any]] = {}
    if not skill_dir.is_dir():
        return rows
    for path in sorted(skill_dir.glob("*.json")):
        payload = read_json_strict(path)
        if isinstance(payload, dict) and payload.get("id"):
            rows[str(payload["id"])] = payload
    return rows


def validate_skill_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: check that written skill instances match source-derived expectation, carry required fields, and justify edges.
    - Guarantee: returns {status: 'pass'|'blocked', expected_count, json_instance_count, missing/extra ids, errors[]}; status 'pass' iff no errors.
    - Fails: never raises; missing/extra/parity/required-relation/edge-justification defects are error rows.
    - When-needed: --check-skill-corpus or doctrine-projection validation.
    - Escalates-to: expected_skill_instances, _instance_required_fields.
    - Non-goal: passing proves markdown-source parity only, not skill-body completeness or runtime use.
    """
    errors: list[dict[str, Any]] = []
    expected = expected_skill_instances(root)
    actual = load_skill_instances(root)
    expected_ids = set(expected)
    actual_ids = set(actual)
    for missing in sorted(expected_ids - actual_ids, key=_id_sort_key):
        _add_error(errors, code="skill_json_instance_missing", path=_skill_instance_rel(missing), message="Expected skill JSON instance is missing.", skill_id=missing)
    for extra in sorted(actual_ids - expected_ids, key=_id_sort_key):
        _add_error(errors, code="skill_json_instance_extra", path=_skill_instance_rel(extra), message="Skill JSON instance has no skill markdown source row.", skill_id=extra)
    required = _instance_required_fields(root, "skill")
    for skill_id in sorted(expected_ids & actual_ids, key=_id_sort_key):
        payload = actual[skill_id]
        missing_required = sorted(required - set(payload))
        if missing_required:
            _add_error(errors, code="skill_json_instance_missing_required_fields", path=_skill_instance_rel(skill_id), message="Skill JSON instance is missing required standard fields.", skill_id=skill_id, missing_required=missing_required)
        if payload != expected[skill_id]:
            _add_error(errors, code="skill_json_instance_markdown_parity_mismatch", path=_skill_instance_rel(skill_id), message="Skill JSON instance is not reproducible from skill markdown source and typed source mapping.", skill_id=skill_id)
        edges = [
            edge
            for edge in _as_list(_as_dict(payload.get("relationships")).get("edges"))
            if isinstance(edge, dict)
        ]
        residuals = [
            residual
            for residual in _as_list(_as_dict(payload.get("relationships")).get("unpopulated_selective_relations"))
            if isinstance(residual, dict)
        ]
        for relation_id in ("skill.operates.standard", "skill.acts_on.doctrine_kind"):
            if not any(edge.get("relation_id") == relation_id for edge in edges) and not any(
                residual.get("relation_id") == relation_id for residual in residuals
            ):
                _add_error(
                    errors,
                    code="skill_required_relation_unaccounted",
                    path=f"{_skill_instance_rel(skill_id)}::relationships",
                    message="Required skill relation is neither resolved nor represented as residual pressure.",
                    skill_id=skill_id,
                    relation_id=relation_id,
                )
        for index, edge in enumerate(edges):
            justification = _as_dict(edge.get("justification"))
            if not justification.get("source_ref") or not justification.get("summary"):
                _add_error(
                    errors,
                    code="skill_edge_missing_source_ref",
                    path=f"{_skill_instance_rel(skill_id)}::relationships.edges[{index}]",
                    message="Skill edge must carry source_ref and summary justification.",
                    skill_id=skill_id,
                )
    return {
        "schema_version": "microcosm_skill_instance_corpus_validation_v1",
        "status": "pass" if not errors else "blocked",
        "expected_count": len(expected),
        "json_instance_count": len(actual),
        "missing_json_ids": sorted(expected_ids - actual_ids, key=_id_sort_key),
        "extra_json_ids": sorted(actual_ids - expected_ids, key=_id_sort_key),
        "errors": errors,
    }


def build_skill_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: aggregate skill instance parity, residual detail, and group counts into a corpus projection.
    - Guarantee: returns a corpus dict (counts, residual detail rows, grouped counts, parity_status, embedded validation).
    - Fails: never raises.
    - Escalates-to: validate_skill_instance_corpus.
    """
    expected = expected_skill_instances(root)
    actual = load_skill_instances(root)
    validation = validate_skill_instance_corpus(root)
    instances = actual if actual else expected
    selective_residual_details = _skill_selective_residual_detail_rows(
        instances.values()
    )
    return {
        "schema_version": "microcosm_skill_instance_corpus_v1",
        "source_of_record": f"{SKILL_INSTANCE_DIR_REL}/*.md",
        "authority_flip_status": "not_flipped_legacy_markdown_still_source_of_record",
        "json_authority_migration_status": "parity_seeded" if validation["status"] == "pass" and actual else "not_seeded_or_not_parity_fresh",
        "expected_skill_count": len(expected),
        "json_instance_count": len(actual),
        "instance_source_class": "json_instances_with_markdown_digest_parity" if validation["status"] == "pass" and actual else "skill_markdown_source_until_json_parity",
        "instance_ids": sorted(actual or expected, key=_id_sort_key),
        "missing_json_ids": validation["missing_json_ids"],
        "extra_json_ids": validation["extra_json_ids"],
        "required_relation_gap_count": _relation_residual_count(instances, requirement="required"),
        "unpopulated_selective_relation_count": _relation_residual_count(instances, requirement="selective"),
        "unpopulated_selective_relation_counts_by_relation_id": _relation_count_by_id(
            selective_residual_details
        ),
        **_selective_residual_group_counts(
            selective_residual_details,
            instance_key="skill_id",
        ),
        "unpopulated_selective_relation_counts_by_triad_role": _count_rows_by_key(
            selective_residual_details,
            "triad_role",
        ),
        "unpopulated_selective_relation_counts_by_operates_standard": _count_rows_by_key(
            selective_residual_details,
            "operates_standard",
        ),
        "unpopulated_selective_relation_counts_by_acts_on_kind": _count_rows_by_key(
            selective_residual_details,
            "acts_on_kind",
        ),
        "unpopulated_selective_relation_detail_count": len(selective_residual_details),
        "unpopulated_selective_relation_details": selective_residual_details,
        "parity_status": validation["status"],
        "validation": validation,
        "source_refs": {
            "legacy_markdown": f"{SKILL_INSTANCE_DIR_REL}/*.md",
            "json_instances": f"{SKILL_INSTANCE_DIR_REL}/*.json",
            "standard": "standards/std_microcosm_skill.json",
        },
        "anti_claim": (
            "Skill JSON presence is migration progress, not proof that every skill has complete "
            "mechanism/concept neighbours, runtime correctness, or agent uptake."
        ),
    }


def _relation_count_by_id(rows: list[dict[str, Any]]) -> dict[str, int]:
    """
    - Teleology: tally detail rows by relation_id.
    - Guarantee: returns an id-sorted {relation_id: count} dict over rows with a relation_id.
    - Fails: never raises.
    """
    counts: dict[str, int] = {}
    for row in rows:
        relation_id = str(row.get("relation_id") or "")
        if relation_id:
            counts[relation_id] = counts.get(relation_id, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: _id_sort_key(item[0])))


def _relation_count_by_requirement(rows: list[dict[str, Any]]) -> dict[str, int]:
    """
    - Teleology: tally detail rows by requirement class.
    - Guarantee: returns a sorted {requirement: count} dict; rows without a requirement count under 'unspecified'.
    - Fails: never raises.
    """
    counts: dict[str, int] = {}
    for row in rows:
        requirement = str(row.get("requirement") or "unspecified")
        counts[requirement] = counts.get(requirement, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: _id_sort_key(item[0])))


def _count_rows_by_key(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    """
    - Teleology: tally detail rows by an arbitrary string key.
    - Guarantee: returns a sorted {value: count} dict; rows missing the key count under 'unspecified'.
    - Fails: never raises.
    """
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "unspecified")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: _id_sort_key(item[0])))


def _selective_residual_group_counts(
    rows: list[dict[str, Any]],
    *,
    instance_key: str,
) -> dict[str, Any]:
    """
    - Teleology: bundle the standard by-instance/by-pressure/by-boundary count breakdowns for selective residuals.
    - Guarantee: returns a dict with the three grouped-count maps keyed off the given instance_key.
    - Fails: never raises.
    """
    return {
        "unpopulated_selective_relation_counts_by_instance_id": _count_rows_by_key(
            rows,
            instance_key,
        ),
        "unpopulated_selective_relation_counts_by_pressure_ref": _count_rows_by_key(
            rows,
            "pressure_ref",
        ),
        "unpopulated_selective_relation_counts_by_authority_boundary": (
            _count_rows_by_key(rows, "authority_boundary")
        ),
    }


def _lattice_health_residual_pressure_rows(health: dict[str, Any]) -> list[dict[str, str]]:
    """
    - Teleology: derive the active doctrine-lattice population pressure rows from a computed health payload.
    - Guarantee: returns a list of {pressure_ref, gap_class, reentry_condition} rows, one per still-active gap class, with the umbrella population row prepended when any gap (or projection/axiom gap) is active.
    - Fails: never raises; closed gap classes are omitted.
    - When-needed: surfacing the re-entry work queue from lattice health.
    - Escalates-to: build_lattice_health.
    """
    pressure_ref = "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
    rows: list[dict[str, str]] = []

    def section(name: str) -> dict[str, Any]:
        """
        [ACTION]
        - Teleology: closure fetching a named sub-section dict from the enclosing health payload.
        - Guarantee: returns the named section coerced to a dict (empty dict if absent).
        - Fails: never raises.
        """
        return _as_dict(health.get(name))

    def count(section_name: str, key: str) -> int:
        """
        [ACTION]
        - Teleology: closure reading an integer metric from a named health section.
        - Guarantee: returns the int value at section_name[key], or 0 if missing or non-int.
        - Fails: never raises.
        """
        value = section(section_name).get(key)
        return value if isinstance(value, int) else 0

    def has_rows(section_name: str, key: str) -> bool:
        """
        [ACTION]
        - Teleology: closure testing whether a named health section list is non-empty.
        - Guarantee: returns True iff section_name[key] is a non-empty list.
        - Fails: never raises.
        """
        return bool(_as_list(section(section_name).get(key)))

    def add(gap_class: str, reentry_condition: str) -> None:
        """
        [ACTION]
        - Teleology: closure appending one gap-class pressure row to the enclosing result list.
        - Guarantee: appends {pressure_ref, gap_class, reentry_condition} to rows (mutates in place).
        - Fails: never raises; returns None.
        """
        rows.append(
            {
                "pressure_ref": pressure_ref,
                "gap_class": gap_class,
                "reentry_condition": reentry_condition,
            }
        )

    principle_or_anti_principle_active = (
        section("principles").get("parity_status") != "pass"
        or count("principles", "unpopulated_governs_edge_count") > 0
        or has_rows("principles", "unsupported_at_obligation_level")
        or section("anti_principles").get("parity_status") != "pass"
        or count("anti_principles", "unpopulated_negates_edge_count") > 0
    )
    concept_or_mechanism_active = (
        section("concepts").get("parity_status") != "pass"
        or count("concepts", "unpopulated_selective_edge_count") > 0
        or section("mechanisms").get("parity_status") != "pass"
        or count("mechanisms", "without_code_loci_count") > 0
        or count("mechanisms", "unpopulated_selective_edge_count") > 0
        or count("mechanisms", "unpopulated_selective_relation_count") > 0
    )
    organ_active = (
        section("organs").get("parity_status") != "pass"
        or count("organs", "required_edge_gap_count") > 0
        or count("organs", "unpopulated_selective_edge_count") > 0
        or has_rows("organs", "unconstrained_by_axiom")
        or has_rows("organs", "ungoverned_by_principle")
    )
    paper_module_active = (
        section("paper_modules").get("json_instance_parity_status") != "pass"
        or count("paper_modules", "legacy_only_count") > 0
        or count("paper_modules", "required_subject_gap_count") > 0
        or count("paper_modules", "without_json_capsule_count") > 0
        or count("paper_modules", "unpopulated_selective_edge_count") > 0
        or count("paper_modules", "unpopulated_selective_relation_count") > 0
    )
    skill_active = (
        section("skills").get("json_instance_parity_status") != "pass"
        or count("skills", "required_edge_gap_count") > 0
        or count("skills", "unpopulated_selective_edge_count") > 0
        or count("skills", "unpopulated_selective_relation_count") > 0
    )
    standard_active = (
        section("standards").get("json_instance_parity_status") != "pass"
        or count("standards", "legacy_or_draft_contract_count") > 0
        or count("standards", "required_edge_gap_count") > 0
        or count("standards", "required_relation_gap_count") > 0
        or count("standards", "triad_skill_planned_unresolved_edge_count") > 0
        or count("standards", "triad_skill_missing_required_count") > 0
        or count("standards", "used_by_organ_unresolved_edge_count") > 0
        or count("standards", "unregistered_standard_file_count") > 0
        or count("standards", "missing_standard_id_file_count") > 0
    )
    evidence_walkability_active = (
        count("doctrine_kinds", "gap_count") > 0
        or count("code_loci", "planned_or_unresolved_path_count") > 0
        or count("receipts", "missing_ref_count") > 0
        or count("receipts", "unresolved_nonlocal_ref_count") > 0
    )

    if principle_or_anti_principle_active:
        add(
            "principle_and_anti_principle_edge_population",
            "Populate principle.governs and anti_principle.negates_failure_of edges from source evidence; do not treat residual-free axiom guards as full obligation mapping.",
        )
    if concept_or_mechanism_active:
        add(
            "concept_and_mechanism_edge_population",
            "Populate concept and mechanism selective edges from source evidence; do not infer neighbour ids from prose-only specimen roles.",
        )
    if organ_active:
        add(
            "organ_required_and_selective_edge_population",
            "Populate missing organ paper/mechanism/code refs from source evidence, then bind concept/principle/axiom/wires_to edges only when atlas or registry rows name ids.",
        )
    if paper_module_active:
        add(
            "paper_module_json_capsule_and_edge_population",
            "Author capsule-backed paper-module JSON subject/code/law/dependency edges for legacy-only Markdown rows, then regenerate governed JSON and projections.",
        )
    if skill_active:
        add(
            "skill_selective_edge_population",
            "Bind skill.uses mechanism and skill.applies concept neighbours only when source evidence names ids; do not infer missing operational dependencies from prose.",
        )
    if standard_active:
        add(
            "standard_contract_and_triad_population",
            "Upgrade legacy/draft standard contracts and bind standard.owns_triad skill edges to governed skill JSON only when source evidence exists.",
        )
    if evidence_walkability_active:
        add(
            "evidence_walkability_population",
            "Resolve code-locus, receipt, and doctrine-kind walkability gaps from source refs; do not treat path or receipt existence as proof.",
        )

    projection_active = (
        section("projections").get("coverage_status") != "pass"
        or section("projections").get("coverage_population_status") != "complete"
    )
    axiom_active = (
        section("axioms").get("parity_status") != "pass"
        or has_rows("axioms", "unwitnessed")
        or has_rows("axioms", "not_obligation_piloted")
    )
    if rows or projection_active or axiom_active:
        rows.insert(
            0,
            {
                "pressure_ref": pressure_ref,
                "gap_class": "doctrine_lattice_population",
                "reentry_condition": "Continue corpus migration and source-evidence edge wiring only for currently computed deficits; do not keep closed gap classes in the run queue.",
            },
        )
    return rows


def _organ_wires_to_fillability_detail_rows(
    organ_instances: list[dict[str, Any]],
    mechanism_instances: list[dict[str, Any]],
    organ_selective_relation_details: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    - Teleology: classify each organ.wires_to residual by whether the mechanism upstream graph implies a missing source-declared wiring target.
    - Guarantee: returns one annotated row per organ.wires_to residual, sorted by organ id, with expected/declared/missing wires_to sets and a fillability_status.
    - Fails: never raises; organs with no upstream-implied target are labelled 'no_mechanism_upstream_wiring_target_named'.
    - When-needed: explaining organ wiring residuals in coverage detail.
    - Escalates-to: build_organ_instance_corpus, mechanism runs_in/upstream relationships.
    - Non-goal: fillability classifies source-declaration gaps only, not runtime invocation or release authority.
    """
    mechanism_to_organ: dict[str, str] = {}
    for mechanism in mechanism_instances:
        mechanism_id = str(mechanism.get("id") or "")
        relationships = _as_dict(mechanism.get("relationships"))
        host_organs = _strings(relationships.get("runs_in"))
        if mechanism_id and host_organs:
            mechanism_to_organ[mechanism_id] = host_organs[0]

    declared_by_organ = {
        str(organ.get("id") or ""): set(_strings(organ.get("wires_to")))
        for organ in organ_instances
        if organ.get("id")
    }
    known_organ_ids = set(declared_by_organ)

    expected_by_organ: dict[str, set[str]] = {}
    for mechanism in mechanism_instances:
        mechanism_id = str(mechanism.get("id") or "")
        source_organ = mechanism_to_organ.get(mechanism_id, "")
        if not source_organ:
            continue
        relationships = _as_dict(mechanism.get("relationships"))
        for target_mechanism in _strings(relationships.get("upstream_mechanism_refs")):
            target_organ = mechanism_to_organ.get(target_mechanism, "")
            if (
                target_organ
                and target_organ in known_organ_ids
                and target_organ != source_organ
            ):
                expected_by_organ.setdefault(source_organ, set()).add(target_organ)
    rows: list[dict[str, Any]] = []
    for residual in organ_selective_relation_details:
        if residual.get("relation_id") != "organ.wires_to.organ":
            continue
        organ_id = str(residual.get("organ_id") or residual.get("instance_id") or "")
        expected_targets = sorted(expected_by_organ.get(organ_id, set()), key=_id_sort_key)
        declared_targets = sorted(declared_by_organ.get(organ_id, set()), key=_id_sort_key)
        missing_targets = sorted(
            set(expected_targets) - set(declared_targets),
            key=_id_sort_key,
        )
        if missing_targets:
            fillability_status = "mechanism_upstream_wiring_missing_source_declaration"
        elif expected_targets:
            fillability_status = "mechanism_upstream_targets_already_declared"
        else:
            fillability_status = "no_mechanism_upstream_wiring_target_named"
        row = _json(residual)
        row.update({
            "mechanism_upstream_expected_wires_to": expected_targets,
            "mechanism_upstream_expected_wires_to_count": len(expected_targets),
            "declared_wires_to": declared_targets,
            "declared_wires_to_count": len(declared_targets),
            "mechanism_upstream_missing_wires_to": missing_targets,
            "mechanism_upstream_missing_wires_to_count": len(missing_targets),
            "fillability_status": fillability_status,
            "claim_ceiling": (
                "mechanism_upstream_graph_classifies_fillability_only_not_runtime_invocation_or_release_authority"
            ),
        })
        rows.append(row)
    return sorted(rows, key=lambda row: _id_sort_key(str(row.get("organ_id") or "")))


def _mechanism_upstream_residual_fillability_detail_rows(
    root: str | Path | None,
    mechanism_selective_relation_details: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    - Teleology: classify each mechanism.upstream_of residual by whether capsule dependency direction implies a missing source-declared upstream target.
    - Guarantee: returns one annotated row per mechanism.upstream_of residual, sorted by mechanism id, with expected/declared/missing upstream sets, unresolved subjects, and a fillability_status.
    - Fails: never raises; mechanisms with no implied target are labelled 'no_capsule_dependency_upstream_target_named'.
    - When-needed: explaining mechanism upstream residuals in coverage detail.
    - Escalates-to: build_mechanism_instance_corpus, core/paper_module_capsules.json.
    - Non-goal: fillability classifies source-declaration gaps only, not runtime invocation or release authority.
    """
    mechanisms = _mechanism_sources(root)
    paper_rows = _paper_capsules(root)
    paper_to_mechanism: dict[str, str] = {}
    for paper in paper_rows:
        paper_id = str(paper.get("id") or "").strip()
        if not paper_id:
            continue
        mechanism_subjects = [
            ref
            for ref in (
                str(subject.get("ref") or "").strip()
                for subject in _as_list(paper.get("subjects"))
                if isinstance(subject, dict) and subject.get("kind") == "mechanism"
            )
            if ref and ref in mechanisms
        ]
        if mechanism_subjects:
            paper_to_mechanism[paper_id] = mechanism_subjects[0]

    expected_by_mechanism: dict[str, set[str]] = {}
    unresolved_by_mechanism: dict[str, list[dict[str, str]]] = {}
    for paper in paper_rows:
        consumer_paper_id = str(paper.get("id") or "").strip()
        if not consumer_paper_id:
            continue
        consumer_mechanism_id = paper_to_mechanism.get(consumer_paper_id, "")
        for dependency_paper_id in _strings(paper.get("depends_on")):
            upstream_mechanism_id = paper_to_mechanism.get(dependency_paper_id, "")
            if not upstream_mechanism_id:
                continue
            if not consumer_mechanism_id:
                unresolved_by_mechanism.setdefault(upstream_mechanism_id, []).append(
                    {
                        "dependency_paper_module": dependency_paper_id,
                        "consumer_paper_module": consumer_paper_id,
                        "reason": "consumer_lacks_resolved_mechanism_subject",
                    }
                )
                continue
            if upstream_mechanism_id != consumer_mechanism_id:
                expected_by_mechanism.setdefault(upstream_mechanism_id, set()).add(
                    consumer_mechanism_id
                )

    rows: list[dict[str, Any]] = []
    for residual in mechanism_selective_relation_details:
        if residual.get("relation_id") != "mechanism.upstream_of.mechanism":
            continue
        mechanism_id = str(
            residual.get("mechanism_id") or residual.get("instance_id") or ""
        )
        source_row = mechanisms.get(mechanism_id, {})
        declared_targets = sorted(
            set(_strings(source_row.get("upstream")))
            | set(_strings(source_row.get("upstream_of"))),
            key=_id_sort_key,
        )
        expected_targets = sorted(
            expected_by_mechanism.get(mechanism_id, set()),
            key=_id_sort_key,
        )
        missing_targets = sorted(
            set(expected_targets) - set(declared_targets),
            key=_id_sort_key,
        )
        unresolved_dependencies = sorted(
            unresolved_by_mechanism.get(mechanism_id, []),
            key=lambda row: (
                _id_sort_key(row["consumer_paper_module"]),
                _id_sort_key(row["dependency_paper_module"]),
            ),
        )
        if missing_targets:
            fillability_status = (
                "capsule_dependency_upstream_target_missing_source_declaration"
            )
        elif expected_targets:
            fillability_status = "capsule_dependency_upstream_targets_already_declared"
        elif unresolved_dependencies:
            fillability_status = "capsule_dependency_upstream_target_unresolved_subject"
        else:
            fillability_status = "no_capsule_dependency_upstream_target_named"

        row = _json(residual)
        row.update(
            {
                "capsule_dependency_expected_upstream_of": expected_targets,
                "capsule_dependency_expected_upstream_of_count": len(
                    expected_targets
                ),
                "declared_upstream_of": declared_targets,
                "declared_upstream_of_count": len(declared_targets),
                "capsule_dependency_missing_upstream_of": missing_targets,
                "capsule_dependency_missing_upstream_of_count": len(missing_targets),
                "capsule_dependency_unresolved_subjects": unresolved_dependencies,
                "capsule_dependency_unresolved_subject_count": len(
                    unresolved_dependencies
                ),
                "fillability_status": fillability_status,
                "claim_ceiling": (
                    "capsule_dependency_graph_classifies_mechanism_upstream_fillability_only_not_runtime_invocation_or_release_authority"
                ),
            }
        )
        rows.append(row)
    return sorted(rows, key=lambda row: _id_sort_key(str(row.get("mechanism_id") or "")))


def _relation_requirement_by_id(root: str | Path | None) -> dict[str, str]:
    """
    - Teleology: index relation ids to their requirement class from the relation registry.
    - Guarantee: returns {relation_id: requirement} for every registry row carrying both.
    - Fails: never raises; missing registry yields {}.
    """
    registry = load_relation_registry(root)
    requirements: dict[str, str] = {}
    for row in _as_list(registry.get("relations")):
        if not isinstance(row, dict):
            continue
        relation_id = str(row.get("relation_id") or "")
        requirement = str(row.get("requirement") or "")
        if relation_id and requirement:
            requirements[relation_id] = requirement
    return requirements


def _residual_relation_detail_rows(
    kind: str,
    instances: Any,
    *,
    authority_boundary: str,
    requirement_by_relation_id: dict[str, str] | None = None,
    source_ref_keys: tuple[str, ...] = (),
    requirement: str | None = None,
) -> list[dict[str, Any]]:
    """
    - Teleology: flatten unpopulated_selective_relations across instances into uniform residual detail rows.
    - Guarantee: returns sorted detail rows (instance_kind/id, relation_id, requirement, reason, pressure_ref, source refs, authority_boundary); requirement filter, when given, restricts the output.
    - Fails: never raises; non-dict instances/residuals and id-less instances are skipped.
    """
    requirement_lookup = requirement_by_relation_id or {}
    rows: list[dict[str, Any]] = []
    for instance in instances:
        if not isinstance(instance, dict):
            continue
        instance_id = str(instance.get("id") or "")
        if not instance_id:
            continue
        relationships = _as_dict(instance.get("relationships"))
        source_refs = {
            key: relationships.get(key)
            for key in source_ref_keys
            if relationships.get(key)
        }
        source_ref = ""
        if source_refs:
            first_key = source_ref_keys[0]
            source_ref = str(source_refs.get(first_key) or next(iter(source_refs.values())))
        for residual in _as_list(relationships.get("unpopulated_selective_relations")):
            if not isinstance(residual, dict):
                continue
            relation_id = str(residual.get("relation_id") or "")
            residual_requirement = str(
                residual.get("requirement")
                or requirement_lookup.get(relation_id)
                or "unspecified"
            )
            if requirement is not None and residual_requirement != requirement:
                continue
            rows.append(
                {
                    "instance_kind": kind,
                    "instance_id": instance_id,
                    f"{kind}_id": instance_id,
                    "source_ref": source_ref,
                    "source_refs": source_refs,
                    "relation_id": relation_id,
                    "requirement": residual_requirement,
                    "reason": residual.get("reason"),
                    "pressure_ref": residual.get("pressure_ref"),
                    "authority_boundary": authority_boundary,
                }
            )
    return sorted(
        rows,
        key=lambda row: (
            _id_sort_key(str(row.get("requirement") or "")),
            _id_sort_key(str(row.get("relation_id") or "")),
            _id_sort_key(str(row.get("instance_id") or "")),
        ),
    )


def _skill_selective_residual_detail_rows(
    skill_instances: Any,
) -> list[dict[str, Any]]:
    """
    - Teleology: flatten skill selective residuals into detail rows annotated with triad role and operated standard.
    - Guarantee: returns sorted rows for every selective residual on the given skill instances.
    - Fails: never raises; non-dict or id-less instances are skipped.
    """
    rows: list[dict[str, Any]] = []
    for instance in skill_instances:
        if not isinstance(instance, dict):
            continue
        skill_id = str(instance.get("id") or "")
        if not skill_id:
            continue
        relationships = _as_dict(instance.get("relationships"))
        source_ref = str(relationships.get("source_markdown_ref") or "")
        for residual in _as_list(relationships.get("unpopulated_selective_relations")):
            if not isinstance(residual, dict):
                continue
            if residual.get("requirement") != "selective":
                continue
            rows.append({
                "skill_id": skill_id,
                "triad_role": instance.get("triad_role"),
                "operates_standard": instance.get("operates_standard"),
                "acts_on_kind": instance.get("acts_on_kind"),
                "source_ref": source_ref,
                "relation_id": residual.get("relation_id"),
                "reason": residual.get("reason"),
                "pressure_ref": residual.get("pressure_ref"),
                "authority_boundary": (
                    "computed_from_skill_markdown_mapping_residuals_not_source_edge_inference"
                ),
            })
    return sorted(
        rows,
        key=lambda row: (
            _id_sort_key(str(row.get("relation_id") or "")),
            _id_sort_key(str(row.get("skill_id") or "")),
        ),
    )


def _skill_residual_candidate_detail_rows(
    root: str | Path | None,
    skill_selective_relation_details: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    - Teleology: annotate each skill residual with same-slug mechanism/concept candidate ids as navigation pressure.
    - Guarantee: returns rows carrying candidate_target_kind, candidate_ids, candidate_count, and a candidate_status; sorted by relation/skill id.
    - Fails: never raises; unsupported relations are labelled 'unsupported_skill_residual_relation'.
    - Non-goal: candidate matches are navigation pressure, not skill-edge support or runtime uptake.
    """
    mechanism_by_slug: dict[str, list[str]] = {}
    for mechanism_id in expected_mechanism_instances(root):
        parts = str(mechanism_id).split(".")
        if len(parts) >= 3 and parts[0] == "mechanism":
            mechanism_by_slug.setdefault(parts[1], []).append(str(mechanism_id))
    concept_by_slug: dict[str, list[str]] = {}
    for concept_id in expected_concept_instances(root):
        slug = str(concept_id).split(".", 1)[-1]
        concept_by_slug.setdefault(slug, []).append(str(concept_id))

    rows: list[dict[str, Any]] = []
    for residual in skill_selective_relation_details:
        relation_id = str(residual.get("relation_id") or "")
        acts_on_kind = str(residual.get("acts_on_kind") or "")
        if relation_id == "skill.uses.mechanism":
            candidate_target_kind = "mechanism"
            candidate_ids = sorted(
                mechanism_by_slug.get(acts_on_kind, []),
                key=_id_sort_key,
            )
            if len(candidate_ids) == 1:
                candidate_status = (
                    "acts_on_kind_matches_single_mechanism_candidate_not_source_edge"
                )
            elif len(candidate_ids) > 1:
                candidate_status = (
                    "acts_on_kind_matches_multiple_mechanism_candidates_not_source_edge"
                )
            else:
                candidate_status = "no_acts_on_kind_mechanism_candidate_named"
        elif relation_id == "skill.applies.concept":
            candidate_target_kind = "concept"
            candidate_ids = sorted(
                concept_by_slug.get(acts_on_kind, []),
                key=_id_sort_key,
            )
            if len(candidate_ids) == 1:
                candidate_status = (
                    "acts_on_kind_matches_single_concept_candidate_not_source_edge"
                )
            elif len(candidate_ids) > 1:
                candidate_status = (
                    "acts_on_kind_matches_multiple_concept_candidates_not_source_edge"
                )
            else:
                candidate_status = "no_acts_on_kind_concept_candidate_named"
        else:
            candidate_target_kind = "unsupported_relation"
            candidate_ids = []
            candidate_status = "unsupported_skill_residual_relation"

        row = _json(residual)
        row.update(
            {
                "candidate_target_kind": candidate_target_kind,
                "candidate_ids": candidate_ids,
                "candidate_count": len(candidate_ids),
                "candidate_count_bucket": str(len(candidate_ids)),
                "candidate_status": candidate_status,
                "claim_ceiling": (
                    "acts_on_kind_candidate_match_is_navigation_pressure_not_skill_edge_support_or_runtime_uptake"
                ),
            }
        )
        rows.append(row)
    return sorted(
        rows,
        key=lambda row: (
            _id_sort_key(str(row.get("relation_id") or "")),
            _id_sort_key(str(row.get("skill_id") or "")),
        ),
    )


def write_skill_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: write every expected skill instance to disk and return the resulting corpus.
    - Guarantee: writes skills/<id>.json for all expected ids (sorted-keys JSON), then returns build_skill_instance_corpus.
    - Fails: raises OSError if a target file cannot be written.
    - When-needed: --write-style regeneration of skill instances.
    - Escalates-to: build_skill_instance_corpus.
    - Non-goal: writing instances does not flip authority off the skill markdown or authorize release.
    """
    resolved = _root(root)
    skill_dir = resolved / SKILL_INSTANCE_DIR_REL
    skill_dir.mkdir(parents=True, exist_ok=True)
    for skill_id, payload in expected_skill_instances(resolved).items():
        (resolved / _skill_instance_rel(skill_id)).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return build_skill_instance_corpus(resolved)


def _standards_registry_rows(root: str | Path | None) -> list[dict[str, Any]]:
    """
    - Teleology: read the standards-registry inventory rows.
    - Guarantee: returns the dict rows under standards_registry.standards.
    - Fails: never raises; absent registry yields [].
    - Escalates-to: core/standards_registry.json.
    """
    registry = _load_optional_dict(root, "core/standards_registry.json")
    return [row for row in _as_list(registry.get("standards")) if isinstance(row, dict)]


def _standard_instance_rel(standard_id: str) -> str:
    """
    - Teleology: compute the standards-dir relative path for a standard id.
    - Guarantee: returns 'standards/<standard_id>.json'.
    - Fails: never raises.
    """
    return f"{STANDARD_INSTANCE_DIR_REL}/{standard_id}.json"


def _standard_registry_row_ref(index: int, standard_id: str) -> str:
    """
    - Teleology: format a stable source-ref pointer into a standards-registry row.
    - Guarantee: returns 'core/standards_registry.json::standards[<index>:<standard_id>]'.
    - Fails: never raises.
    """
    return f"core/standards_registry.json::standards[{index}:{standard_id}]"


def _standard_file_inventory(root: str | Path | None) -> dict[str, Any]:
    """
    - Teleology: reconcile standards-registry ids against on-disk std_microcosm_*.json files.
    - Guarantee: returns registry_ids, file_ids, files_by_id, registry_missing_files, files_not_in_registry, and files_missing_standard_id.
    - Fails: propagates read_json_strict errors on a malformed standard file.
    - Escalates-to: core/standards_registry.json, standards/std_microcosm_*.json.
    """
    resolved = _root(root)
    standard_dir = resolved / STANDARD_INSTANCE_DIR_REL
    registry_rows = _standards_registry_rows(resolved)
    registry_ids = {str(row.get("standard_id") or "") for row in registry_rows if row.get("standard_id")}
    files_by_id: dict[str, str] = {}
    files_missing_standard_id: list[str] = []
    if standard_dir.is_dir():
        for path in sorted(standard_dir.glob("std_microcosm_*.json")):
            rel = path.relative_to(resolved).as_posix()
            payload = read_json_strict(path)
            standard_id = str(_as_dict(payload).get("standard_id") or "")
            if standard_id:
                files_by_id[standard_id] = rel
            else:
                files_missing_standard_id.append(rel)
    file_ids = set(files_by_id)
    return {
        "registry_ids": sorted(registry_ids),
        "file_ids": sorted(file_ids),
        "files_by_id": files_by_id,
        "registry_missing_files": sorted(registry_ids - file_ids),
        "files_not_in_registry": sorted(file_ids - registry_ids),
        "files_missing_standard_id": files_missing_standard_id,
    }


def _standard_required_residual(relation_id: str, reason: str) -> dict[str, Any]:
    """
    - Teleology: build a typed REQUIRED residual-pressure row for an unpopulated standard relation.
    - Guarantee: returns a dict with relation_id, status 'residual_pressure', requirement 'required', reason, and pressure_ref.
    - Fails: never raises.
    """
    return {
        "relation_id": relation_id,
        "status": "residual_pressure",
        "requirement": "required",
        "reason": reason,
        "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
    }


def _standard_used_by_organ_residual_metadata() -> dict[str, str]:
    """
    - Teleology: supply the typed residual metadata attached to an unresolved standard.used_by.organ edge.
    - Guarantee: returns the fixed residual-metadata dict (gap class, requirement 'selective', disposition, claim_ceiling, reentry_condition).
    - Fails: never raises.
    - Non-goal: this metadata is re-entry pressure, not proof of organ usage or acceptance.
    """
    return {
        "residual_status": "typed_residual_pressure",
        "residual_gap_class": "standard_used_by_organ_target_not_accepted_current_authority",
        "residual_relation_id": "standard.used_by.organ",
        "residual_requirement": "selective",
        "residual_disposition": "keep_as_reentry_pressure_not_usage_or_acceptance_proof",
        "claim_ceiling": "standard_used_by_organ_residual_is_reentry_metadata_not_usage_or_acceptance_proof",
        "reentry_condition": (
            "When the target organ is accepted_current_authority, or the standard source "
            "renames/removes the target, rerun --check-standard-corpus and refresh the "
            "aggregate doctrine-lattice surfaces through the builder owner."
        ),
    }


def _standard_triad_skill_id(row: Any) -> str:
    """
    - Teleology: extract a triad skill_id from a standard skills.<role> row.
    - Guarantee: returns the stripped skill_id string, or '' when absent.
    - Fails: never raises.
    """
    return str(_as_dict(row).get("skill_id") or "").strip()


def _known_skill_instance_ids(root: str | Path | None) -> set[str]:
    """
    - Teleology: resolve the set of skill ids to treat as resolvable targets (loaded, else expected).
    - Guarantee: returns the loaded skill instance ids if any exist on disk, otherwise the expected ids.
    - Fails: never raises beyond underlying reads.
    """
    loaded = set(load_skill_instances(root))
    return loaded if loaded else set(expected_skill_instances(root))


def build_standard_instance_from_registry_row(
    row: dict[str, Any],
    index: int,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: project one standards-registry row plus its source standard JSON into a governed standard lattice node.
    - Guarantee: returns the standard instance dict with governs/owns_triad/used_by edges, residuals, anti_claims, and standard_payload; status is 'active' iff the source file exists, else 'missing_source'.
    - Fails: never raises; missing kind_id or triad skill ids become required residuals; unresolved used_by organs carry typed residual metadata.
    - When-needed: regenerating standard instances or diagnosing one standard's contract projection.
    - Escalates-to: expected_standard_instances, core/standards_registry.json.
    - Non-goal: building a node does not upgrade a legacy/draft standard to active v2, nor prove triad skills exist or that organs use the standard.
    """
    standard_id = str(row.get("standard_id") or "")
    source_ref = str(row.get("path") or _standard_instance_rel(standard_id))
    payload = _load_optional_dict(root, source_ref)
    payload_relationships = _as_dict(payload.get("relationships"))
    source_exists = _path(root, source_ref).is_file()
    governs_kind = str(payload.get("kind_id") or row.get("kind_id") or "").strip()
    skills = _as_dict(payload.get("skills"))
    known_skill_ids = _known_skill_instance_ids(root)
    known_organ_ids = set(expected_organ_instances(root))
    used_by_organs = _unique_strings(
        payload_relationships.get("used_by_organs"),
        row.get("used_by_organs"),
    )
    registry_ref = _standard_registry_row_ref(index, standard_id)
    edges: list[dict[str, Any]] = []
    residuals: list[dict[str, Any]] = []

    if governs_kind:
        edges.append(
            _edge(
                relation_id="standard.governs.doctrine_kind",
                relation_verb="governs",
                reverse_verb="governed_by",
                target_kind="doctrine_kind",
                target_id=governs_kind,
                source_ref=f"{source_ref}::kind_id",
                target_status=(
                    "resolved_doctrine_kind_contract"
                    if source_exists
                    else "unresolved_doctrine_kind_contract"
                ),
                justification="Standard JSON declares the governed doctrine kind.",
            )
        )
    else:
        residuals.append(
            _standard_required_residual(
                "standard.governs.doctrine_kind",
                "Standard registry row or source file does not declare kind_id.",
            )
        )

    for role in SKILL_TRIAD:
        skill_row = _as_dict(skills.get(role))
        skill_id = _standard_triad_skill_id(skill_row)
        skill_status = str(skill_row.get("status") or "").strip()
        if skill_id:
            edges.append(
                _edge(
                    relation_id="standard.owns_triad.skill",
                    relation_verb="owns_triad",
                    reverse_verb="operates",
                    target_kind="skill",
                    target_id=skill_id,
                    source_ref=f"{source_ref}::skills.{role}.skill_id",
                    target_status=(
                        "resolved_json_instance"
                        if skill_id in known_skill_ids
                        else "planned_unresolved"
                        if skill_status == "planned"
                        else "unresolved_json_instance"
                    ),
                    justification=(
                        f"Standard JSON declares the {role} skill in its governance triad."
                    ),
                )
            )
        else:
            residuals.append(
                _standard_required_residual(
                    "standard.owns_triad.skill",
                    f"Standard source does not declare skills.{role}.skill_id.",
                )
            )

    used_by_source_ref = (
        f"{source_ref}::relationships.used_by_organs"
        if payload_relationships.get("used_by_organs")
        else f"{registry_ref}.used_by_organs"
    )
    for used_by_index, organ_id in enumerate(used_by_organs):
        target_status = (
            "resolved_json_instance"
            if organ_id in known_organ_ids
            else "unresolved_json_instance"
        )
        edge = _edge(
            relation_id="standard.used_by.organ",
            relation_verb="used_by",
            reverse_verb="uses_standard",
            target_kind="organ",
            target_id=organ_id,
            source_ref=f"{used_by_source_ref}[{used_by_index}]",
            target_status=target_status,
            justification=(
                "Standard source names this organ as a user of the contract. "
                "This is source-declared route pressure only; it does not accept "
                "missing organs or prove runtime use."
            ),
        )
        if target_status != "resolved_json_instance":
            edge.update(_standard_used_by_organ_residual_metadata())
        edges.append(edge)

    source_schema_version = str(payload.get("schema_version") or "missing_source")
    source_status = str(payload.get("status") or row.get("status") or "missing_source")
    active_v2 = source_schema_version == "public_microcosm_standard_v2" and source_status == "active"
    validator_contract = _as_dict(payload.get("validator_contract"))
    receipt_contract = _as_dict(payload.get("receipt_contract"))
    validator_refs = _strings(payload.get("validator_refs"))
    registry_validator = str(row.get("validator_id") or "")
    if registry_validator and registry_validator not in validator_refs:
        validator_refs.append(registry_validator)
    receipt_refs = _strings(payload.get("receipt_refs"))
    registry_receipt = str(row.get("receipt_id") or "")
    if registry_receipt and registry_receipt not in receipt_refs:
        receipt_refs.append(registry_receipt)

    return {
        "id": standard_id,
        "kind": "standard",
        "schema_version": STANDARD_INSTANCE_SCHEMA_VERSION,
        "title": str(payload.get("kind_name") or row.get("kind_name") or standard_id),
        "statement": str(payload.get("kind_name") or row.get("kind_name") or standard_id),
        "governs_kind": governs_kind,
        "source_standard_schema_version": source_schema_version,
        "source_standard_status": source_status,
        "registry_status": row.get("status"),
        "status": "active" if source_exists else "missing_source",
        "created_at": AXIOM_MIGRATION_CREATED_AT,
        "authority_boundary": (
            "standard_json_contract_projected_as_lattice_node_not_completeness_or_release_authority"
        ),
        "source_refs": [
            {
                "path": source_ref,
                "role": "governed_standard_json_source",
            },
            {
                "path": "core/standards_registry.json",
                "role": "standard_inventory_source",
                "row_ref": registry_ref,
            },
        ],
        "relationships": {
            "source_ref": source_ref,
            "source_digest": _sha256(_path(root, source_ref)) if source_exists else None,
            "registry_row_ref": registry_ref,
            "governs_kind": governs_kind,
            "used_by_organs": used_by_organs,
            "triad_skill_ids": [
                _standard_triad_skill_id(skills.get(role))
                for role in SKILL_TRIAD
                if _standard_triad_skill_id(skills.get(role))
            ],
            "edges": edges,
            "unpopulated_selective_relations": residuals,
        },
        "validator_refs": validator_refs,
        "receipt_refs": receipt_refs,
        "omission_receipt": {
            "omitted": [
                "private macro standard bodies",
                "runtime usage proof for planned triad skills",
                "release, publication, provider, or product readiness proof",
            ],
            "reason": (
                "The lattice node projects registry-backed standard JSON identity and typed edges only. "
                "Legacy or draft standard files stay visible as residual pressure instead of being upgraded."
            ),
            "drilldown": source_ref,
            "residual_pressure": [
                {
                    "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
                    "gap_class": "standard_contract_and_triad_population",
                    "reentry_condition": "Upgrade only source standards with real v2/active contracts and bind triad skill ids to governed skill instances when evidence exists.",
                }
            ],
        },
        "anti_claims": [
            "Standard-node projection does not turn legacy or draft standards into active v2 contracts.",
            "A declared or planned triad skill edge is not proof that the skill exists as governed JSON or is used correctly.",
            "Registry coverage is inventory evidence only, not completeness, release readiness, or whole-system correctness.",
        ],
        "standard_payload": {
            "contract_version": "microcosm_standard_instance_projection_payload_v1",
            "source_schema_version": source_schema_version,
            "source_status": source_status,
            "registry_status": row.get("status"),
            "first_wave_required": row.get("first_wave_required"),
            "validator_contract_required": bool(validator_contract.get("required")),
            "validator_contract_validator_id": (
                validator_contract.get("validator_id")
                or validator_contract.get("validator")
                or None
            ),
            "receipt_contract_required": bool(receipt_contract.get("required")),
            "receipt_contract_receipt_id": receipt_contract.get("receipt_id") or None,
            "runtime_acceptance_status": payload.get("runtime_acceptance_status"),
            "contract_projection_status": (
                "active_v2_governed_json"
                if active_v2
                else "legacy_or_draft_standard_contract"
            ),
            "support_contract": {
                "computed_by": "microcosm_core.doctrine_lattice.build_doctrine_projection",
                "support_status": "standard_edges_computed_not_standard_completeness_claim",
            },
            "authority_ceiling": _as_dict(payload.get("authority_ceiling")),
        },
    }


def expected_standard_instances(root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: compute the full expected standard instance corpus from the registry.
    - Guarantee: returns {standard_id: instance} for every registry row carrying a standard_id.
    - Fails: never raises beyond underlying source reads.
    - Escalates-to: build_standard_instance_from_registry_row.
    """
    return _expected_standard_instances_cached(_root_key(root))


@lru_cache(maxsize=32)
def _expected_standard_instances_cached(root_key: str) -> dict[str, dict[str, Any]]:
    """
    - Teleology: lru-cached backend for expected_standard_instances keyed by root string.
    - Guarantee: returns the {standard_id: instance} mapping; identical root_key returns the cached mapping.
    - Fails: never raises beyond underlying source reads.
    """
    root = Path(root_key)
    rows: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(_standards_registry_rows(root)):
        standard_id = str(row.get("standard_id") or "")
        if standard_id:
            rows[standard_id] = build_standard_instance_from_registry_row(row, index, root)
    return rows


def load_standard_instances(root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: select the expected standard instances whose source JSON file actually exists on disk.
    - Guarantee: returns {standard_id: instance} restricted to standard ids present in the on-disk file inventory.
    - Fails: never raises beyond underlying source reads.
    - Escalates-to: _standard_file_inventory.
    """
    inventory = _standard_file_inventory(root)
    file_ids = set(_as_list(inventory.get("file_ids")))
    return {
        standard_id: instance
        for standard_id, instance in expected_standard_instances(root).items()
        if standard_id in file_ids
    }


def _standard_required_gap_rows(instance: dict[str, Any]) -> list[dict[str, Any]]:
    """
    - Teleology: collect a standard instance's required residuals plus unresolved governs/triad edges.
    - Guarantee: returns the list of required residual rows and unresolved required edges for the instance.
    - Fails: never raises.
    """
    relationships = _as_dict(instance.get("relationships"))
    gaps = [
        residual
        for residual in _as_list(relationships.get("unpopulated_selective_relations"))
        if isinstance(residual, dict) and residual.get("requirement") == "required"
    ]
    for edge in _as_list(relationships.get("edges")):
        if not isinstance(edge, dict):
            continue
        if edge.get("relation_id") == "standard.governs.doctrine_kind" and edge.get(
            "target_status"
        ) != "resolved_doctrine_kind_contract":
            gaps.append(edge)
        if edge.get("relation_id") == "standard.owns_triad.skill" and edge.get(
            "target_status"
        ) != "resolved_json_instance":
            gaps.append(edge)
    return gaps


def _standard_triad_role(edge: dict[str, Any]) -> str:
    """
    - Teleology: recover the triad role (author/refine_instance/refine_standard_and_propagate) from an edge's source_ref.
    - Guarantee: returns the role parsed from a '::skills.<role>.skill_id' source_ref, or '' if it does not match.
    - Fails: never raises.
    """
    source_ref = str(_as_dict(edge.get("justification")).get("source_ref") or "")
    match = re.search(r"::skills\.([^.]+)\.skill_id$", source_ref)
    return match.group(1) if match else ""


def _standard_required_relation_gap_detail_rows(
    standard_instances: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    - Teleology: enumerate, per standard, its missing/planned/unresolved/resolved required relations.
    - Guarantee: returns one detail row per standard with a required gap, sorted by standard id; standards with no gap are omitted.
    - Fails: never raises.
    - Escalates-to: build_standard_instance_corpus.
    """
    rows: list[dict[str, Any]] = []
    for instance in standard_instances:
        standard_id = str(instance.get("id") or "")
        if not standard_id:
            continue
        relationships = _as_dict(instance.get("relationships"))
        edges = [
            edge
            for edge in _as_list(relationships.get("edges"))
            if isinstance(edge, dict)
        ]
        required_gap_rows = _standard_required_gap_rows(instance)
        if not required_gap_rows:
            continue
        required_residuals = [
            row
            for row in required_gap_rows
            if row.get("status") == "residual_pressure"
        ]
        planned_triad_edges = [
            edge
            for edge in edges
            if edge.get("relation_id") == "standard.owns_triad.skill"
            and edge.get("target_status") == "planned_unresolved"
        ]
        unresolved_triad_edges = [
            edge
            for edge in edges
            if edge.get("relation_id") == "standard.owns_triad.skill"
            and edge.get("target_status")
            not in {"planned_unresolved", "resolved_json_instance"}
        ]
        resolved_required_edges = [
            edge
            for edge in edges
            if (
                edge.get("relation_id") == "standard.governs.doctrine_kind"
                and edge.get("target_status") == "resolved_doctrine_kind_contract"
            )
            or (
                edge.get("relation_id") == "standard.owns_triad.skill"
                and edge.get("target_status") == "resolved_json_instance"
            )
        ]
        payload = _as_dict(instance.get("standard_payload"))
        rows.append({
            "standard_id": standard_id,
            "governs_kind": instance.get("governs_kind"),
            "source_ref": relationships.get("source_ref"),
            "registry_source_ref": relationships.get("registry_row_ref"),
            "source_standard_schema_version": instance.get("source_standard_schema_version"),
            "source_standard_status": instance.get("source_standard_status"),
            "contract_projection_status": payload.get("contract_projection_status"),
            "required_relation_gap_count": len(required_gap_rows),
            "missing_required_relation_ids": sorted(
                {
                    str(row.get("relation_id"))
                    for row in required_residuals
                    if row.get("relation_id")
                },
                key=_id_sort_key,
            ),
            "planned_required_relation_ids": sorted(
                {
                    str(edge.get("relation_id"))
                    for edge in planned_triad_edges
                    if edge.get("relation_id")
                },
                key=_id_sort_key,
            ),
            "unresolved_required_relation_ids": sorted(
                {
                    str(edge.get("relation_id"))
                    for edge in unresolved_triad_edges
                    if edge.get("relation_id")
                },
                key=_id_sort_key,
            ),
            "resolved_required_relation_ids": sorted(
                {
                    str(edge.get("relation_id"))
                    for edge in resolved_required_edges
                    if edge.get("relation_id")
                },
                key=_id_sort_key,
            ),
            "planned_unresolved_triad_skill_ids": [
                str(edge.get("target_id"))
                for edge in planned_triad_edges
                if edge.get("target_id")
            ],
            "planned_unresolved_triad_skill_roles": [
                role
                for role in (_standard_triad_role(edge) for edge in planned_triad_edges)
                if role
            ],
            "unresolved_triad_skill_ids": [
                str(edge.get("target_id"))
                for edge in unresolved_triad_edges
                if edge.get("target_id")
            ],
            "residual_pressure_refs": sorted(
                {
                    str(row.get("pressure_ref") or row.get("residual_pressure_ref"))
                    for row in required_gap_rows
                    if row.get("pressure_ref") or row.get("residual_pressure_ref")
                },
                key=_id_sort_key,
            ),
            "authority_boundary": (
                "computed_from_standard_instance_edges_not_skill_resolution_or_contract_completion"
            ),
        })
    return sorted(rows, key=lambda row: _id_sort_key(str(row["standard_id"])))


def _standard_used_by_organ_unresolved_detail_rows(
    standard_instances: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    - Teleology: enumerate unresolved standard.used_by.organ edges with their typed residual metadata.
    - Guarantee: returns one row per unresolved used_by edge, sorted by standard then organ id.
    - Fails: never raises.
    - Non-goal: rows are re-entry metadata, not proof of organ acceptance or runtime use.
    """
    rows: list[dict[str, Any]] = []
    for instance in standard_instances:
        standard_id = str(instance.get("id") or "")
        if not standard_id:
            continue
        relationships = _as_dict(instance.get("relationships"))
        payload = _as_dict(instance.get("standard_payload"))
        for edge in _as_list(relationships.get("edges")):
            if not isinstance(edge, dict):
                continue
            if edge.get("relation_id") != "standard.used_by.organ":
                continue
            if edge.get("target_status") == "resolved_json_instance":
                continue
            justification = _as_dict(edge.get("justification"))
            rows.append({
                "standard_id": standard_id,
                "governs_kind": instance.get("governs_kind"),
                "source_ref": relationships.get("source_ref"),
                "registry_source_ref": relationships.get("registry_row_ref"),
                "source_standard_schema_version": instance.get("source_standard_schema_version"),
                "source_standard_status": instance.get("source_standard_status"),
                "registry_status": instance.get("registry_status"),
                "contract_projection_status": payload.get("contract_projection_status"),
                "target_organ_id": edge.get("target_id"),
                "target_status": edge.get("target_status"),
                "edge_source_ref": justification.get("source_ref"),
                "residual_pressure_ref": edge.get("residual_pressure_ref"),
                "residual_status": edge.get("residual_status"),
                "residual_gap_class": edge.get("residual_gap_class"),
                "residual_relation_id": edge.get("residual_relation_id"),
                "residual_requirement": edge.get("residual_requirement"),
                "residual_disposition": edge.get("residual_disposition"),
                "reentry_condition": edge.get("reentry_condition"),
                "claim_ceiling": edge.get("claim_ceiling"),
                "authority_boundary": (
                    "computed_from_standard_relationships_used_by_organs_not_organ_acceptance_or_runtime_use"
                ),
            })
    return sorted(
        rows,
        key=lambda row: (
            _id_sort_key(str(row.get("standard_id") or "")),
            _id_sort_key(str(row.get("target_organ_id") or "")),
        ),
    )


def _standard_used_by_organ_admission_detail_rows(
    unresolved_details: list[dict[str, Any]],
    organ_instances: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    - Teleology: annotate unresolved used_by edges with whether the target organ is an accepted-authority instance.
    - Guarantee: returns rows carrying an admission_status of accepted/not-accepted/missing-id, sorted by standard then organ id.
    - Fails: never raises.
    - Non-goal: admission status is re-entry metadata, not usage or acceptance proof.
    """
    accepted_organ_ids = {
        str(instance.get("id") or "")
        for instance in organ_instances
        if instance.get("id")
    }
    rows: list[dict[str, Any]] = []
    for detail in unresolved_details:
        target_organ_id = str(detail.get("target_organ_id") or "")
        if not target_organ_id:
            admission_status = "missing_target_organ_id"
        elif target_organ_id in accepted_organ_ids:
            admission_status = "target_accepted_organ_exists_edge_still_unresolved"
        else:
            admission_status = "target_organ_not_accepted_current_authority"
        rows.append({
            "standard_id": detail.get("standard_id"),
            "governs_kind": detail.get("governs_kind"),
            "target_organ_id": target_organ_id,
            "target_status": detail.get("target_status"),
            "admission_status": admission_status,
            "source_ref": detail.get("source_ref"),
            "registry_source_ref": detail.get("registry_source_ref"),
            "edge_source_ref": detail.get("edge_source_ref"),
            "source_standard_schema_version": detail.get(
                "source_standard_schema_version"
            ),
            "source_standard_status": detail.get("source_standard_status"),
            "registry_status": detail.get("registry_status"),
            "contract_projection_status": detail.get("contract_projection_status"),
            "residual_pressure_ref": detail.get("residual_pressure_ref"),
            "residual_status": detail.get("residual_status"),
            "residual_gap_class": detail.get("residual_gap_class"),
            "residual_relation_id": detail.get("residual_relation_id"),
            "residual_requirement": detail.get("residual_requirement"),
            "residual_disposition": detail.get("residual_disposition"),
            "reentry_condition": detail.get("reentry_condition"),
            "authority_boundary": (
                "computed_from_standard_used_by_organ_residuals_not_organ_admission_or_edge_support"
            ),
            "claim_ceiling": (
                "standard_used_by_organ_target_admission_status_is_reentry_metadata_not_usage_or_acceptance_proof"
            ),
        })
    return sorted(
        rows,
        key=lambda row: (
            _id_sort_key(str(row.get("standard_id") or "")),
            _id_sort_key(str(row.get("target_organ_id") or "")),
        ),
    )


def _standard_legacy_or_draft_detail_rows(
    standard_instances: Any,
) -> list[dict[str, Any]]:
    """
    - Teleology: enumerate standards whose contract projection is not active v2 governed JSON.
    - Guarantee: returns one row per non-active-v2 standard with source/registry status and unresolved used_by counts, sorted by id.
    - Fails: never raises; non-dict or id-less instances are skipped.
    - Non-goal: rows are re-entry metadata, not active-v2 contract support.
    """
    rows: list[dict[str, Any]] = []
    for instance in standard_instances:
        if not isinstance(instance, dict):
            continue
        standard_id = str(instance.get("id") or "")
        if not standard_id:
            continue
        relationships = _as_dict(instance.get("relationships"))
        payload = _as_dict(instance.get("standard_payload"))
        contract_projection_status = str(
            payload.get("contract_projection_status") or ""
        )
        if contract_projection_status == "active_v2_governed_json":
            continue
        used_by_edges = [
            edge
            for edge in _as_list(relationships.get("edges"))
            if isinstance(edge, dict)
            and edge.get("relation_id") == "standard.used_by.organ"
        ]
        unresolved_used_by_edges = [
            edge
            for edge in used_by_edges
            if edge.get("target_status") != "resolved_json_instance"
        ]
        rows.append(
            {
                "standard_id": standard_id,
                "governs_kind": instance.get("governs_kind"),
                "source_ref": relationships.get("source_ref"),
                "registry_source_ref": relationships.get("registry_row_ref"),
                "source_standard_schema_version": instance.get(
                    "source_standard_schema_version"
                ),
                "source_standard_status": instance.get("source_standard_status"),
                "registry_status": instance.get("registry_status"),
                "contract_projection_status": contract_projection_status,
                "required_relation_gap_count": len(
                    _standard_required_gap_rows(instance)
                ),
                "used_by_organ_edge_count": len(used_by_edges),
                "used_by_organ_unresolved_count": len(unresolved_used_by_edges),
                "unresolved_used_by_organ_ids": sorted(
                    {
                        str(edge.get("target_id"))
                        for edge in unresolved_used_by_edges
                        if edge.get("target_id")
                    },
                    key=_id_sort_key,
                ),
                "residual_pressure_ref": (
                    "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
                ),
                "authority_boundary": (
                    "computed_from_standard_source_status_not_contract_activation_or_runtime_use"
                ),
                "claim_ceiling": (
                    "legacy_or_draft_detail_is_reentry_metadata_not_active_v2_contract_support"
                ),
            }
        )
    return sorted(rows, key=lambda row: _id_sort_key(str(row["standard_id"])))


def _standard_activation_witness_gap_detail_rows(
    standard_instances: Any,
) -> list[dict[str, Any]]:
    """
    - Teleology: enumerate, per non-active standard, the specific activation gaps (schema/status/validator/receipt binding).
    - Guarantee: returns one row per non-active-v2 standard listing activation_gap_ids, sorted by id.
    - Fails: never raises; non-dict or id-less instances are skipped.
    - Non-goal: gap rows are re-entry metadata, not active-contract support.
    """
    rows: list[dict[str, Any]] = []
    for instance in standard_instances:
        if not isinstance(instance, dict):
            continue
        standard_id = str(instance.get("id") or "")
        if not standard_id:
            continue
        payload = _as_dict(instance.get("standard_payload"))
        relationships = _as_dict(instance.get("relationships"))
        contract_projection_status = str(
            payload.get("contract_projection_status") or ""
        )
        if contract_projection_status == "active_v2_governed_json":
            continue
        source_schema_version = str(
            instance.get("source_standard_schema_version")
            or payload.get("source_schema_version")
            or "missing_source"
        )
        source_status = str(
            instance.get("source_standard_status")
            or payload.get("source_status")
            or "missing_source"
        )
        registry_status = str(instance.get("registry_status") or "")
        validator_refs = _strings(instance.get("validator_refs"))
        receipt_refs = _strings(instance.get("receipt_refs"))
        validator_contract_required = bool(
            payload.get("validator_contract_required")
        )
        receipt_contract_required = bool(payload.get("receipt_contract_required"))

        gap_ids: list[str] = []
        if source_schema_version != "public_microcosm_standard_v2":
            gap_ids.append("source_schema_not_public_microcosm_standard_v2")
        if source_status != "active":
            gap_ids.append("source_status_not_active")
        if validator_contract_required and not validator_refs:
            gap_ids.append("required_validator_ref_not_bound")
        if receipt_contract_required and not receipt_refs:
            gap_ids.append("required_receipt_ref_not_bound")

        if not gap_ids:
            gap_ids.append("legacy_projection_status_without_activation_gap")

        rows.append({
            "standard_id": standard_id,
            "governs_kind": instance.get("governs_kind"),
            "source_ref": relationships.get("source_ref"),
            "registry_source_ref": relationships.get("registry_row_ref"),
            "source_standard_schema_version": source_schema_version,
            "source_standard_status": source_status,
            "registry_status": registry_status,
            "contract_projection_status": contract_projection_status,
            "validator_contract_required": validator_contract_required,
            "validator_refs": validator_refs,
            "receipt_contract_required": receipt_contract_required,
            "receipt_refs": receipt_refs,
            "activation_gap_ids": sorted(set(gap_ids), key=_id_sort_key),
            "activation_gap_count": len(set(gap_ids)),
            "residual_pressure_ref": (
                "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
            ),
            "authority_boundary": (
                "computed_from_standard_source_contract_not_activation_or_runtime_use"
            ),
            "claim_ceiling": (
                "activation_witness_gap_detail_is_reentry_metadata_not_active_contract_support"
            ),
        })
    return sorted(rows, key=lambda row: _id_sort_key(str(row["standard_id"])))


RECEIPT_EVIDENCE_SOURCE_KINDS = {
    "axiom",
    "principle",
    "anti_principle",
    "mechanism",
    "organ",
    "paper_module",
    "standard",
}


def _instance_source_ref(instance: dict[str, Any]) -> str:
    """
    - Teleology: resolve the best source_ref handle for an instance across its relationship keys and kind.
    - Guarantee: returns the first present relationship source-ref key, else a kind-specific instance path, else ''.
    - Fails: never raises.
    """
    relationships = _as_dict(instance.get("relationships"))
    for key in (
        "source_ref",
        "source_registry_row_ref",
        "source_atlas_row_ref",
        "registry_row_ref",
        "legacy_markdown_projection",
        "source_markdown_ref",
    ):
        value = str(relationships.get(key) or "").strip()
        if value:
            return value
    kind = str(instance.get("kind") or "")
    instance_id = str(instance.get("id") or "")
    if kind == "mechanism" and instance_id:
        return _mechanism_instance_rel(instance_id)
    if kind == "organ" and instance_id:
        return _organ_instance_rel(instance_id)
    if kind == "paper_module" and instance_id:
        return _paper_module_instance_rel(instance_id)
    if kind == "standard" and instance_id:
        return _standard_instance_rel(instance_id)
    return ""


def _receipt_target_status(root: str | Path | None, receipt_ref: str) -> str:
    """
    - Teleology: classify a receipt ref into a typed resolution status (file-resolved, declared, symbolic, nonlocal, missing).
    - Guarantee: returns one of the receipt status strings based on prefix/suffix and on-disk existence.
    - Fails: never raises; an empty ref returns 'missing_receipt_ref'.
    """
    ref = receipt_ref.strip()
    if not ref:
        return "missing_receipt_ref"
    if ref.startswith("receipts/"):
        return "resolved_receipt_ref" if _receipt_ref_path(root, ref).is_file() else "missing_receipt_ref"
    if ref.startswith("state/") and ref.endswith(".json"):
        return (
            "resolved_nonlocal_receipt_ref"
            if _receipt_ref_path(root, ref).is_file()
            else "declared_nonlocal_receipt_ref"
        )
    if ref.endswith(".json"):
        return "declared_receipt_ref"
    if ref.startswith("receipt."):
        return "declared_receipt_id"
    return "declared_receipt_ref"


def _receipt_ref_path(root: str | Path | None, receipt_ref: str) -> Path:
    """
    - Teleology: resolve the filesystem path a receipt ref points at, including the macro-parent state/ fallback.
    - Guarantee: returns the in-root path if it exists, else the parent-root path for state/ refs, else the in-root path.
    - Fails: never raises.
    """
    ref_path = _path(root, receipt_ref)
    if ref_path.is_file():
        return ref_path
    ref = receipt_ref.strip()
    root_path = Path(root).resolve() if root is not None else microcosm_root()
    if ref.startswith("state/"):
        return root_path.parent / ref
    return ref_path


def _receipt_evidence_edge_rows(
    instances: list[dict[str, Any]],
    root: str | Path | None,
) -> list[dict[str, Any]]:
    """
    - Teleology: derive <kind>.evidenced_by.receipt edges from the receipt_refs declared on source instances.
    - Guarantee: returns sorted edge rows for evidence-bearing kinds, each carrying target_status and a residual pressure ref when the receipt is missing.
    - Fails: never raises; instances of non-evidence kinds or without ids are skipped.
    - Non-goal: a receipt edge routes evidence; it does not certify proof, runtime correctness, or release readiness.
    """
    rows: list[dict[str, Any]] = []
    for instance in instances:
        kind = str(instance.get("kind") or "")
        source_id = str(instance.get("id") or "")
        if kind not in RECEIPT_EVIDENCE_SOURCE_KINDS or not source_id:
            continue
        source_ref = _instance_source_ref(instance)
        for index, receipt_ref in enumerate(_strings(instance.get("receipt_refs"))):
            receipt_id = receipt_ref.strip()
            if not receipt_id:
                continue
            rows.append({
                "relation_id": f"{kind}.evidenced_by.receipt",
                "relation_verb": "evidenced_by",
                "reverse_verb": "evidences",
                "source_kind": kind,
                "source_id": source_id,
                "target_kind": "receipt",
                "target_id": receipt_id,
                "target_status": _receipt_target_status(root, receipt_id),
                "residual_pressure_ref": (
                    "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
                    if _receipt_target_status(root, receipt_id) == "missing_receipt_ref"
                    else None
                ),
                "justification": {
                    "source_ref": (
                        f"{source_ref}.receipt_refs[{index}]"
                        if source_ref
                        else f"{kind}:{source_id}.receipt_refs[{index}]"
                    ),
                    "summary": (
                        "Source instance names this receipt ref as evidence routing; "
                        "presence does not certify proof, runtime correctness, or release readiness."
                    ),
                },
            })
    return sorted(
        rows,
        key=lambda row: (
            str(row["source_kind"]),
            _id_sort_key(str(row["source_id"])),
            _id_sort_key(str(row["target_id"])),
        ),
    )


def _relationship_edge_rows(instances: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    - Teleology: flatten all instances' relationship edges into rows annotated with source kind and id.
    - Guarantee: returns a list of edge dicts each carrying source_kind and source_id.
    - Fails: never raises; kind-less or id-less instances and non-dict edges are skipped.
    """
    rows: list[dict[str, Any]] = []
    for instance in instances:
        kind = str(instance.get("kind") or "")
        source_id = str(instance.get("id") or "")
        if not kind or not source_id:
            continue
        relationships = _as_dict(instance.get("relationships"))
        for edge in _as_list(relationships.get("edges")):
            if not isinstance(edge, dict):
                continue
            row = _json(edge)
            row["source_kind"] = kind
            row["source_id"] = source_id
            rows.append(row)
    return rows


def _derived_code_locus_node_rows(
    edge_rows: list[dict[str, Any]],
    root: str | Path | None,
) -> list[dict[str, Any]]:
    """
    - Teleology: derive code-locus projection nodes by grouping inbound code-locus edges.
    - Guarantee: returns one node per distinct code-locus id with support_status (resolved iff a source edge resolves and the path exists), inbound edges, and gap_count; sorted by id.
    - Fails: never raises.
    - Non-goal: path existence is filesystem grounding only, not code correctness or runtime proof.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for edge in edge_rows:
        if edge.get("target_kind") != "code_locus":
            continue
        code_locus_id = str(edge.get("target_id") or "").strip()
        if not code_locus_id:
            continue
        grouped.setdefault(code_locus_id, []).append(edge)
    rows: list[dict[str, Any]] = []
    for code_locus_id, edges in grouped.items():
        statuses = {str(edge.get("target_status") or "") for edge in edges}
        resolved = "resolved_code_locus" in statuses and _path(root, code_locus_id).is_file()
        rows.append({
            "id": code_locus_id,
            "kind": "code_locus",
            "title": code_locus_id,
            "source_ref": None,
            "source_refs": sorted(
                {
                    str(_as_dict(edge.get("justification")).get("source_ref"))
                    for edge in edges
                    if _as_dict(edge.get("justification")).get("source_ref")
                },
                key=_id_sort_key,
            ),
            "support_status": (
                "resolved_path_named_by_source_edges"
                if resolved
                else "planned_or_unresolved_path_named_by_source_edges"
            ),
            "claim_ceiling": "path_existence_and_source_edge_routing_only_not_code_correctness_or_runtime_proof",
            "path_exists": resolved,
            "inbound_edge_count": len(edges),
            "relation_ids": sorted(
                {str(edge.get("relation_id")) for edge in edges if edge.get("relation_id")},
                key=_id_sort_key,
            ),
            "source_ids": sorted(
                {
                    f"{edge.get('source_kind')}:{edge.get('source_id')}"
                    for edge in edges
                    if edge.get("source_kind") and edge.get("source_id")
                },
                key=_id_sort_key,
            ),
            "gap_count": 0 if resolved else 1,
            "residual_pressure_ref": (
                None
                if resolved
                else "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
            ),
            "authority_boundary": "derived_projection_node_from_source_edges_not_source_file_authority",
        })
    return sorted(rows, key=lambda row: _id_sort_key(str(row["id"])))


def _derived_receipt_node_rows(
    edge_rows: list[dict[str, Any]],
    root: str | Path | None,
) -> list[dict[str, Any]]:
    """
    - Teleology: derive receipt projection nodes by grouping inbound receipt edges and classifying support.
    - Guarantee: returns one node per distinct receipt id with a support_status (resolved/symbolic/nonlocal/declared/missing) and gap_count; sorted by id.
    - Fails: never raises.
    - Non-goal: receipt presence or nonlocal walkability is not proof, runtime correctness, or release authority.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for edge in edge_rows:
        if edge.get("target_kind") != "receipt":
            continue
        receipt_id = str(edge.get("target_id") or "").strip()
        if not receipt_id:
            continue
        grouped.setdefault(receipt_id, []).append(edge)
    rows: list[dict[str, Any]] = []
    for receipt_id, edges in grouped.items():
        statuses = {str(edge.get("target_status") or "") for edge in edges}
        if "missing_receipt_ref" in statuses:
            support_status = "missing_receipt_ref"
            gap_count = 1
        elif "resolved_receipt_ref" in statuses:
            support_status = "receipt_path_resolved"
            gap_count = 0
        elif "declared_receipt_id" in statuses:
            support_status = "symbolic_receipt_id_declared_not_file_resolved"
            gap_count = 0
        elif "resolved_nonlocal_receipt_ref" in statuses:
            support_status = "nonlocal_receipt_path_resolved_not_public_evidence"
            gap_count = 0
        elif "declared_nonlocal_receipt_ref" in statuses:
            support_status = "nonlocal_receipt_ref_declared_not_public_file_resolved"
            gap_count = 1
        else:
            support_status = "declared_receipt_ref_not_file_resolved"
            gap_count = 0
        rows.append({
            "id": receipt_id,
            "kind": "receipt",
            "title": receipt_id,
            "source_ref": None,
            "source_refs": sorted(
                {
                    str(_as_dict(edge.get("justification")).get("source_ref"))
                    for edge in edges
                    if _as_dict(edge.get("justification")).get("source_ref")
                },
                key=_id_sort_key,
            ),
            "support_status": support_status,
            "claim_ceiling": (
                "nonlocal_receipt_handle_is_declared_authority_boundary_not_public_file_evidence"
                if support_status
                in {
                    "nonlocal_receipt_path_resolved_not_public_evidence",
                    "nonlocal_receipt_ref_declared_not_public_file_resolved",
                }
                else "receipt_ref_presence_or_file_existence_not_proof_runtime_correctness_or_release_authority"
            ),
            "path_exists": (
                _receipt_ref_path(root, receipt_id).is_file()
                if receipt_id.startswith(("receipts/", "state/"))
                else None
            ),
            "inbound_edge_count": len(edges),
            "relation_ids": sorted(
                {str(edge.get("relation_id")) for edge in edges if edge.get("relation_id")},
                key=_id_sort_key,
            ),
            "source_ids": sorted(
                {
                    f"{edge.get('source_kind')}:{edge.get('source_id')}"
                    for edge in edges
                    if edge.get("source_kind") and edge.get("source_id")
                },
                key=_id_sort_key,
            ),
            "gap_count": gap_count,
            "residual_pressure_ref": (
                "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
                if gap_count
                else None
            ),
            "authority_boundary": "derived_projection_node_from_receipt_refs_not_receipt_content_proof",
        })
    return sorted(rows, key=lambda row: _id_sort_key(str(row["id"])))


def _derived_doctrine_kind_node_rows(edge_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    - Teleology: derive doctrine-kind projection nodes by grouping inbound standard.governs/skill.acts_on edges.
    - Guarantee: returns one node per kind id with support_status (resolved iff every inbound edge resolves), edge tallies, and gap_count; sorted by id.
    - Fails: never raises.
    - Non-goal: a kind handle is a walkability node, not kind completeness or runtime use.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for edge in edge_rows:
        if edge.get("target_kind") != "doctrine_kind":
            continue
        kind_id = str(edge.get("target_id") or "").strip()
        if not kind_id:
            continue
        grouped.setdefault(kind_id, []).append(edge)
    rows: list[dict[str, Any]] = []
    for kind_id, edges in grouped.items():
        unresolved_edges = [
            edge
            for edge in edges
            if edge.get("target_status") != "resolved_doctrine_kind_contract"
        ]
        rows.append({
            "id": kind_id,
            "kind": "doctrine_kind",
            "title": kind_id,
            "source_ref": None,
            "source_refs": sorted(
                {
                    str(_as_dict(edge.get("justification")).get("source_ref"))
                    for edge in edges
                    if _as_dict(edge.get("justification")).get("source_ref")
                },
                key=_id_sort_key,
            ),
            "support_status": (
                "resolved_doctrine_kind_contract_from_source_edges"
                if not unresolved_edges
                else "doctrine_kind_contract_resolution_gap"
            ),
            "claim_ceiling": "doctrine_kind_contract_handle_only_not_kind_completeness_or_runtime_use",
            "inbound_edge_count": len(edges),
            "relation_ids": sorted(
                {str(edge.get("relation_id")) for edge in edges if edge.get("relation_id")},
                key=_id_sort_key,
            ),
            "source_ids": sorted(
                {
                    f"{edge.get('source_kind')}:{edge.get('source_id')}"
                    for edge in edges
                    if edge.get("source_kind") and edge.get("source_id")
                },
                key=_id_sort_key,
            ),
            "standard_governs_edge_count": len(
                [
                    edge
                    for edge in edges
                    if edge.get("relation_id") == "standard.governs.doctrine_kind"
                ]
            ),
            "skill_acts_on_edge_count": len(
                [
                    edge
                    for edge in edges
                    if edge.get("relation_id") == "skill.acts_on.doctrine_kind"
                ]
            ),
            "gap_count": len(unresolved_edges),
            "residual_pressure_ref": (
                "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
                if unresolved_edges
                else None
            ),
            "authority_boundary": "derived_projection_node_from_standard_skill_kind_edges_not_kind_source_authority",
        })
    return sorted(rows, key=lambda row: _id_sort_key(str(row["id"])))


def _evidence_walkability_health(
    root: str | Path | None,
    instances: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    - Teleology: summarize doctrine-kind/code-locus/receipt walkability derived from instance edges.
    - Guarantee: returns a dict with doctrine_kinds/code_loci/receipts sub-sections (known counts, gap counts, sample/detail rows, support_scope notes).
    - Fails: never raises.
    - When-needed: building the evidence-walkability portion of lattice health.
    - Escalates-to: build_lattice_health.
    - Non-goal: walkability is derived navigability, not proof, runtime correctness, or source-evidence laundering.
    """
    relationship_edges = _relationship_edge_rows(instances)
    receipt_edges = _receipt_evidence_edge_rows(instances, root)
    doctrine_kind_edges = [
        edge for edge in relationship_edges if edge.get("target_kind") == "doctrine_kind"
    ]
    doctrine_kind_nodes = _derived_doctrine_kind_node_rows(relationship_edges)
    code_locus_nodes = _derived_code_locus_node_rows(relationship_edges, root)
    receipt_nodes = _derived_receipt_node_rows(receipt_edges, root)
    doctrine_kind_gap_nodes = [row for row in doctrine_kind_nodes if row["gap_count"]]
    planned_or_unresolved_code_locus_nodes = [
        row for row in code_locus_nodes if row["path_exists"] is not True
    ]
    receipt_nonlocal_support_statuses = {
        "nonlocal_receipt_path_resolved_not_public_evidence",
        "nonlocal_receipt_ref_declared_not_public_file_resolved",
    }
    missing_receipt_nodes = [
        row for row in receipt_nodes if row["support_status"] == "missing_receipt_ref"
    ]
    nonlocal_receipt_nodes = [
        row
        for row in receipt_nodes
        if row["support_status"] in receipt_nonlocal_support_statuses
    ]
    unresolved_nonlocal_receipt_nodes = [
        row
        for row in receipt_nodes
        if row["support_status"]
        == "nonlocal_receipt_ref_declared_not_public_file_resolved"
    ]
    receipt_gap_nodes = [row for row in receipt_nodes if row["gap_count"]]
    return {
        "doctrine_kinds": {
            "known_count": len(doctrine_kind_nodes),
            "inbound_edge_count": len(doctrine_kind_edges),
            "standard_governs_edge_count": len(
                [
                    edge
                    for edge in doctrine_kind_edges
                    if edge.get("relation_id") == "standard.governs.doctrine_kind"
                ]
            ),
            "skill_acts_on_edge_count": len(
                [
                    edge
                    for edge in doctrine_kind_edges
                    if edge.get("relation_id") == "skill.acts_on.doctrine_kind"
                ]
            ),
            "counts_by_support_status": _count_rows_by_key(
                doctrine_kind_nodes,
                "support_status",
            ),
            "counts_by_relation_id": _relation_count_by_id(doctrine_kind_edges),
            "counts_by_source_kind": _count_rows_by_key(doctrine_kind_edges, "source_kind"),
            "gap_count": len(doctrine_kind_gap_nodes),
            "gap_details": doctrine_kind_gap_nodes,
            "sample_nodes": doctrine_kind_nodes[:12],
            "support_scope": "derived from standard.governs and skill.acts_on edges; kind handles are walkability nodes, not complete ontology, runtime use, or release authority",
        },
        "code_loci": {
            "known_count": len(code_locus_nodes),
            "resolved_path_count": len([row for row in code_locus_nodes if row["path_exists"] is True]),
            "planned_or_unresolved_path_count": len(planned_or_unresolved_code_locus_nodes),
            "counts_by_support_status": _count_rows_by_key(code_locus_nodes, "support_status"),
            "planned_or_unresolved_path_details": planned_or_unresolved_code_locus_nodes,
            "inbound_edge_count": len([edge for edge in relationship_edges if edge.get("target_kind") == "code_locus"]),
            "relation_ids": sorted(
                {
                    str(edge.get("relation_id"))
                    for edge in relationship_edges
                    if edge.get("target_kind") == "code_locus" and edge.get("relation_id")
                },
                key=_id_sort_key,
            ),
            "sample_nodes": code_locus_nodes[:12],
            "support_scope": "derived from source relationship edges; path existence is not code correctness, runtime proof, or release authority",
        },
        "receipts": {
            "known_count": len(receipt_nodes),
            "edge_count": len(receipt_edges),
            "resolved_path_count": len([row for row in receipt_nodes if row["support_status"] == "receipt_path_resolved"]),
            "resolved_nonlocal_ref_count": len([row for row in receipt_nodes if row["support_status"] == "nonlocal_receipt_path_resolved_not_public_evidence"]),
            "symbolic_id_count": len([row for row in receipt_nodes if row["support_status"] == "symbolic_receipt_id_declared_not_file_resolved"]),
            "declared_ref_count": len([row for row in receipt_nodes if row["support_status"] == "declared_receipt_ref_not_file_resolved"]),
            "nonlocal_ref_count": len(nonlocal_receipt_nodes),
            "unresolved_nonlocal_ref_count": len(unresolved_nonlocal_receipt_nodes),
            "missing_ref_count": len(missing_receipt_nodes),
            "counts_by_support_status": _count_rows_by_key(receipt_nodes, "support_status"),
            "missing_ref_details": missing_receipt_nodes,
            "nonlocal_ref_details": nonlocal_receipt_nodes,
            "unresolved_nonlocal_ref_details": unresolved_nonlocal_receipt_nodes,
            "gap_details": receipt_gap_nodes,
            "relation_ids": sorted(
                {str(edge.get("relation_id")) for edge in receipt_edges if edge.get("relation_id")},
                key=_id_sort_key,
            ),
            "sample_nodes": receipt_nodes[:12],
            "support_scope": "derived from receipt_refs on source instances; receipt existence is not proof, and nonlocal path walkability is not runtime correctness, release authority, or source evidence laundering",
        },
    }


def _standard_relation_metrics(instances: Any) -> dict[str, int]:
    """
    - Teleology: tally standard edge resolution metrics (governs/triad/used_by resolved vs unresolved vs missing).
    - Guarantee: returns the fixed metrics dict of integer counts over the given standard instances.
    - Fails: never raises; non-dict instances and edges are skipped.
    """
    metrics = {
        "governs_kind_resolved_edge_count": 0,
        "governs_kind_unresolved_edge_count": 0,
        "governs_kind_missing_required_count": 0,
        "triad_skill_resolved_edge_count": 0,
        "triad_skill_planned_unresolved_edge_count": 0,
        "triad_skill_unresolved_edge_count": 0,
        "triad_skill_missing_required_count": 0,
        "used_by_organ_edge_count": 0,
        "used_by_organ_resolved_edge_count": 0,
        "used_by_organ_unresolved_edge_count": 0,
    }
    for instance in instances:
        if not isinstance(instance, dict):
            continue
        relationships = _as_dict(instance.get("relationships"))
        for edge in _as_list(relationships.get("edges")):
            if not isinstance(edge, dict):
                continue
            relation_id = edge.get("relation_id")
            target_status = edge.get("target_status")
            if relation_id == "standard.governs.doctrine_kind":
                if target_status == "resolved_doctrine_kind_contract":
                    metrics["governs_kind_resolved_edge_count"] += 1
                else:
                    metrics["governs_kind_unresolved_edge_count"] += 1
            elif relation_id == "standard.owns_triad.skill":
                if target_status == "resolved_json_instance":
                    metrics["triad_skill_resolved_edge_count"] += 1
                elif target_status == "planned_unresolved":
                    metrics["triad_skill_planned_unresolved_edge_count"] += 1
                else:
                    metrics["triad_skill_unresolved_edge_count"] += 1
            elif relation_id == "standard.used_by.organ":
                metrics["used_by_organ_edge_count"] += 1
                if target_status == "resolved_json_instance":
                    metrics["used_by_organ_resolved_edge_count"] += 1
                else:
                    metrics["used_by_organ_unresolved_edge_count"] += 1
        for residual in _as_list(relationships.get("unpopulated_selective_relations")):
            if (
                not isinstance(residual, dict)
                or residual.get("requirement") != "required"
            ):
                continue
            relation_id = residual.get("relation_id")
            if relation_id == "standard.governs.doctrine_kind":
                metrics["governs_kind_missing_required_count"] += 1
            elif relation_id == "standard.owns_triad.skill":
                metrics["triad_skill_missing_required_count"] += 1
    return metrics


def validate_standard_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: check that registry-backed standard instances exist on disk and justify their edges.
    - Guarantee: returns {status: 'pass'|'blocked', expected_count, json_instance_count, missing/extra ids, files_missing_standard_id, errors[]}; status 'pass' iff no errors.
    - Fails: never raises; missing source files, unaccounted required relations, and unjustified edges are error rows.
    - When-needed: --check-standard-corpus or doctrine-projection validation.
    - Escalates-to: expected_standard_instances, _standard_file_inventory.
    - Non-goal: passing proves registry-backed source presence and edge justification only, not contract activation or release readiness.
    """
    errors: list[dict[str, Any]] = []
    expected = expected_standard_instances(root)
    actual = load_standard_instances(root)
    inventory = _standard_file_inventory(root)
    expected_ids = set(expected)
    actual_ids = set(actual)
    for missing in sorted(expected_ids - actual_ids, key=_id_sort_key):
        _add_error(
            errors,
            code="standard_json_instance_missing",
            path=_standard_instance_rel(missing),
            message="Expected registry-backed standard JSON source file is missing.",
            standard_id=missing,
        )
    for standard_id in sorted(expected_ids & actual_ids, key=_id_sort_key):
        instance = actual[standard_id]
        edges = [
            edge
            for edge in _as_list(_as_dict(instance.get("relationships")).get("edges"))
            if isinstance(edge, dict)
        ]
        residuals = [
            residual
            for residual in _as_list(
                _as_dict(instance.get("relationships")).get("unpopulated_selective_relations")
            )
            if isinstance(residual, dict)
        ]
        for relation_id in ("standard.governs.doctrine_kind", "standard.owns_triad.skill"):
            if not any(edge.get("relation_id") == relation_id for edge in edges) and not any(
                residual.get("relation_id") == relation_id for residual in residuals
            ):
                _add_error(
                    errors,
                    code="standard_required_relation_unaccounted",
                    path=f"{_standard_instance_rel(standard_id)}::relationships",
                    message="Required standard relation is neither resolved nor represented as residual pressure.",
                    standard_id=standard_id,
                    relation_id=relation_id,
                )
        for index, edge in enumerate(edges):
            justification = _as_dict(edge.get("justification"))
            if not justification.get("source_ref") or not justification.get("summary"):
                _add_error(
                    errors,
                    code="standard_edge_missing_source_ref",
                    path=f"{_standard_instance_rel(standard_id)}::relationships.edges[{index}]",
                    message="Standard edge must carry source_ref and summary justification.",
                    standard_id=standard_id,
                )
    return {
        "schema_version": "microcosm_standard_instance_corpus_validation_v1",
        "status": "pass" if not errors else "blocked",
        "expected_count": len(expected),
        "json_instance_count": len(actual),
        "missing_json_ids": sorted(expected_ids - actual_ids, key=_id_sort_key),
        "extra_json_ids": _as_list(inventory.get("files_not_in_registry")),
        "files_missing_standard_id": _as_list(inventory.get("files_missing_standard_id")),
        "errors": errors,
    }


def build_standard_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: aggregate standard inventory, legacy/draft and activation gaps, used_by residuals, and relation metrics into a corpus projection.
    - Guarantee: returns a corpus dict (inventory counts, legacy/activation/used-by detail rows and grouped counts, relation metrics, parity_status, embedded validation).
    - Fails: never raises.
    - Escalates-to: validate_standard_instance_corpus.
    - Non-goal: registry-backed presence is inventory coverage only, not contract completion.
    """
    expected = expected_standard_instances(root)
    actual = load_standard_instances(root)
    validation = validate_standard_instance_corpus(root)
    instances = actual if actual else expected
    relation_metrics = _standard_relation_metrics(instances.values())
    legacy_or_draft_details = _standard_legacy_or_draft_detail_rows(
        instances.values()
    )
    activation_witness_gap_details = _standard_activation_witness_gap_detail_rows(
        instances.values()
    )
    activation_gap_ids = [
        gap_id
        for row in activation_witness_gap_details
        for gap_id in _strings(row.get("activation_gap_ids"))
    ]
    used_by_unresolved_details = _standard_used_by_organ_unresolved_detail_rows(
        list(instances.values())
    )
    used_by_unresolved_standard_ids = sorted(
        {
            str(row.get("standard_id"))
            for row in used_by_unresolved_details
            if row.get("standard_id")
        },
        key=_id_sort_key,
    )
    used_by_unresolved_target_organ_ids = sorted(
        {
            str(row.get("target_organ_id"))
            for row in used_by_unresolved_details
            if row.get("target_organ_id")
        },
        key=_id_sort_key,
    )
    legacy_or_draft_ids = [
        standard_id
        for standard_id, instance in instances.items()
        if _as_dict(instance.get("standard_payload")).get("contract_projection_status")
        != "active_v2_governed_json"
    ]
    required_gap_ids = [
        standard_id
        for standard_id, instance in instances.items()
        if _standard_required_gap_rows(instance)
    ]
    return {
        "schema_version": "microcosm_standard_instance_corpus_v1",
        "source_of_record": "core/standards_registry.json + standards/std_microcosm_*.json",
        "authority_flip_status": "already_json_source_contract_no_markdown_authority_flip",
        "json_authority_migration_status": "source_json_contracts_loaded",
        "expected_standard_count": len(expected),
        "json_instance_count": len(actual),
        "instance_source_class": "registry_backed_standard_json_sources",
        "instance_ids": sorted(actual or expected, key=_id_sort_key),
        "missing_json_ids": validation["missing_json_ids"],
        "extra_json_ids": validation["extra_json_ids"],
        "files_missing_standard_id": validation["files_missing_standard_id"],
        "legacy_or_draft_contract_count": len(legacy_or_draft_ids),
        "legacy_or_draft_contract_ids": sorted(legacy_or_draft_ids, key=_id_sort_key),
        "legacy_or_draft_contract_detail_count": len(legacy_or_draft_details),
        "legacy_or_draft_contract_details": legacy_or_draft_details,
        "legacy_or_draft_contract_counts_by_source_status": _count_rows_by_key(
            legacy_or_draft_details,
            "source_standard_status",
        ),
        "legacy_or_draft_contract_counts_by_source_schema_version": _count_rows_by_key(
            legacy_or_draft_details,
            "source_standard_schema_version",
        ),
        "legacy_or_draft_contract_counts_by_registry_status": _count_rows_by_key(
            legacy_or_draft_details,
            "registry_status",
        ),
        "legacy_or_draft_contract_counts_by_projection_status": _count_rows_by_key(
            legacy_or_draft_details,
            "contract_projection_status",
        ),
        "activation_witness_gap_detail_count": len(
            activation_witness_gap_details
        ),
        "activation_witness_gap_details": activation_witness_gap_details,
        "activation_witness_gap_counts_by_gap_id": dict(
            sorted(Counter(activation_gap_ids).items())
        ),
        "activation_witness_gap_counts_by_source_status": _count_rows_by_key(
            activation_witness_gap_details,
            "source_standard_status",
        ),
        "activation_witness_gap_counts_by_source_schema_version": (
            _count_rows_by_key(
                activation_witness_gap_details,
                "source_standard_schema_version",
            )
        ),
        "activation_witness_gap_counts_by_registry_status": _count_rows_by_key(
            activation_witness_gap_details,
            "registry_status",
        ),
        "activation_witness_gap_counts_by_validator_contract_required": (
            _count_rows_by_key(
                activation_witness_gap_details,
                "validator_contract_required",
            )
        ),
        "activation_witness_gap_counts_by_receipt_contract_required": (
            _count_rows_by_key(
                activation_witness_gap_details,
                "receipt_contract_required",
            )
        ),
        "required_relation_gap_count": sum(
            len(_standard_required_gap_rows(instance)) for instance in instances.values()
        ),
        "required_relation_gap_instance_count": len(required_gap_ids),
        "required_relation_gap_instance_ids": sorted(required_gap_ids, key=_id_sort_key),
        **relation_metrics,
        "used_by_organ_unresolved_detail_count": len(used_by_unresolved_details),
        "used_by_organ_unresolved_details": used_by_unresolved_details,
        "used_by_organ_unresolved_standard_count": len(
            used_by_unresolved_standard_ids
        ),
        "used_by_organ_unresolved_standard_ids": used_by_unresolved_standard_ids,
        "used_by_organ_unresolved_target_organ_count": len(
            used_by_unresolved_target_organ_ids
        ),
        "used_by_organ_unresolved_target_organ_ids": (
            used_by_unresolved_target_organ_ids
        ),
        "used_by_organ_unresolved_counts_by_target_organ_id": _count_rows_by_key(
            used_by_unresolved_details,
            "target_organ_id",
        ),
        "used_by_organ_unresolved_counts_by_target_status": _count_rows_by_key(
            used_by_unresolved_details,
            "target_status",
        ),
        "used_by_organ_unresolved_counts_by_source_status": _count_rows_by_key(
            used_by_unresolved_details,
            "source_standard_status",
        ),
        "used_by_organ_unresolved_counts_by_source_schema_version": _count_rows_by_key(
            used_by_unresolved_details,
            "source_standard_schema_version",
        ),
        "used_by_organ_unresolved_counts_by_registry_status": _count_rows_by_key(
            used_by_unresolved_details,
            "registry_status",
        ),
        "used_by_organ_unresolved_counts_by_projection_status": _count_rows_by_key(
            used_by_unresolved_details,
            "contract_projection_status",
        ),
        "used_by_organ_typed_residual_count": sum(
            1
            for row in used_by_unresolved_details
            if row.get("residual_status") == "typed_residual_pressure"
        ),
        "used_by_organ_typed_residual_counts_by_gap_class": _count_rows_by_key(
            used_by_unresolved_details,
            "residual_gap_class",
        ),
        "used_by_organ_typed_residual_counts_by_requirement": _count_rows_by_key(
            used_by_unresolved_details,
            "residual_requirement",
        ),
        "used_by_organ_typed_residual_counts_by_disposition": _count_rows_by_key(
            used_by_unresolved_details,
            "residual_disposition",
        ),
        "parity_status": validation["status"],
        "validation": validation,
        "source_refs": {
            "registry": "core/standards_registry.json",
            "json_instances": f"{STANDARD_INSTANCE_DIR_REL}/std_microcosm_*.json",
            "standard": "standards/std_microcosm_standard.json",
        },
        "anti_claim": (
            "Standard JSON inventory is projected as lattice coverage only; draft or legacy "
            "contracts and planned triad skills remain explicit residual pressure."
        ),
    }


def _axiom_routing_rows(root: str | Path | None) -> list[dict[str, Any]]:
    """
    - Teleology: read the axiom organ-routing rows that are the axiom source of record.
    - Guarantee: returns the dict rows under axiom_organ_routing.rows.
    - Fails: never raises; absent routing yields [].
    - Escalates-to: core/axiom_organ_routing.json.
    """
    payload = _load_optional_dict(root, AXIOM_ROUTING_REL)
    return [row for row in _as_list(payload.get("rows")) if isinstance(row, dict)]


def _axiom_row_ref(axiom_id: str, index: int) -> str:
    """
    - Teleology: format a stable source-ref pointer into an axiom routing row.
    - Guarantee: returns 'core/axiom_organ_routing.json::rows[<index>:<axiom_id>]'.
    - Fails: never raises.
    """
    return f"{AXIOM_ROUTING_REL}::rows[{index}:{axiom_id}]"


def _axiom_instance_rel(axiom_id: str) -> str:
    """
    - Teleology: compute the governed JSON instance path for an axiom id.
    - Guarantee: returns 'axioms/<axiom_id>.json'.
    - Fails: never raises.
    """
    return f"{AXIOM_INSTANCE_DIR_REL}/{axiom_id}.json"


def _axiom_markdown_rel(axiom_id: str) -> str:
    """
    - Teleology: compute the generated markdown path for an axiom id.
    - Guarantee: returns 'axioms/<axiom_id>.md'.
    - Fails: never raises.
    """
    return f"{AXIOM_INSTANCE_DIR_REL}/{axiom_id}.md"


def _edge(
    *,
    relation_id: str,
    relation_verb: str,
    reverse_verb: str,
    target_kind: str,
    target_id: str,
    source_ref: str,
    target_status: str,
    justification: str,
) -> dict[str, Any]:
    """
    - Teleology: construct one typed lattice edge with justification and conditional residual-pressure ref.
    - Guarantee: returns an edge dict; residual_pressure_ref is set iff target_status is not one of the resolved statuses, else None.
    - Fails: never raises.
    """
    resolved_statuses = {
        "resolved_json_instance",
        "resolved_registry_or_atlas_target",
        "resolved_code_locus",
        "resolved_paper_module_ref",
        "resolved_standard_contract",
        "resolved_doctrine_kind_contract",
    }
    return {
        "relation_id": relation_id,
        "relation_verb": relation_verb,
        "reverse_verb": reverse_verb,
        "target_kind": target_kind,
        "target_id": target_id,
        "target_status": target_status,
        "justification": {
            "source_ref": source_ref,
            "summary": justification,
        },
        "residual_pressure_ref": (
            "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
            if target_status not in resolved_statuses
            else None
        ),
    }


def _debt_ids(layer_debt: Any) -> list[str]:
    """
    - Teleology: collect distinct debt_id strings from a layer-debt list.
    - Guarantee: returns the sorted set of debt_id values among dict items.
    - Fails: never raises; non-dict items are skipped.
    """
    return sorted(
        {
            str(item.get("debt_id"))
            for item in _as_list(layer_debt)
            if isinstance(item, dict) and item.get("debt_id")
        }
    )


def _axiom_substrate_reciprocity_contract(
    *,
    source_ref: str,
    principle_ids: list[str],
    anti_principle_ids: list[str],
    witness_organs: list[str],
    witness_surfaces: list[str],
    negative_case_codes: list[str],
    layer_debt: Any,
) -> dict[str, Any]:
    """
    - Teleology: assemble the law<->substrate reciprocity contract block for an axiom payload.
    - Guarantee: returns the contract dict (law_to_substrate, substrate_to_law, claim_ceiling) from the provided routing fields.
    - Fails: never raises.
    - Non-goal: witness organs and negative cases are support-calculation inputs, not support claims.
    """
    return {
        "contract_version": "microcosm_axiom_substrate_reciprocity_v1",
        "source_authority_ref": source_ref,
        "law_to_substrate": {
            "grounded_principle_ids": principle_ids,
            "guarded_by_anti_principle_ids": anti_principle_ids,
            "substrate_constraint_relation": "organ.constrained_by.axiom",
            "projection_edge_relation_ids": [
                "principle.grounded_by.axiom",
                "anti_principle.guards.axiom",
                "axiom.witnessed_by.organ",
            ],
            "rule": (
                "The axiom governs downstream substrate by constraining organ rows, "
                "grounding principle commitments, and naming anti-principle guards; "
                "those governance edges do not by themselves compute support."
            ),
        },
        "substrate_to_law": {
            "witness_organs": witness_organs,
            "witness_surfaces": witness_surfaces,
            "negative_case_codes": negative_case_codes,
            "layer_debt_ids": _debt_ids(layer_debt),
            "refinement_rule": (
                "Substrate evidence may refine obligation bindings, claim ceilings, "
                "negative-case mappings, and layer-debt status in the routing registry "
                "or evaluator grammar; it does not de-admit the axiom or certify strong "
                "support without the support-cover validator."
            ),
        },
        "claim_ceiling": {
            "computed_by": "validator.microcosm.axiom_support_cover",
            "boundary": (
                "Witness organs and negative cases are inputs to support calculation, "
                "not support claims. Projection output is never source evidence."
            ),
        },
    }


def build_axiom_instance_from_routing_row(
    row: dict[str, Any],
    *,
    index: int,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: project one axiom routing row into a receipt-bound governed axiom JSON instance with grounding/guard/witness edges.
    - Guarantee: returns the axiom instance dict with edges, receipt_refs, anti_claims, and axiom_payload; principle/anti-principle edges are marked resolved and witness edges resolved_registry_or_atlas_target.
    - Fails: never raises.
    - When-needed: regenerating axiom instances or diagnosing one axiom's routing.
    - Escalates-to: expected_axiom_instances, core/axiom_organ_routing.json, validator.microcosm.axiom_support_cover.
    - Non-goal: admission as law does not flip source authority off the routing registry, nor prove the axiom is witnessed, enforced, strong, or complete.
    """
    axiom_id = str(row.get("axiom_id") or "")
    source_ref = _axiom_row_ref(axiom_id, index)
    principle_ids = _strings(row.get("principle_ids"))
    anti_principle_ids = _strings(row.get("anti_principle_ids"))
    witness_organs = _strings(row.get("witness_organs"))
    witness_surfaces = _strings(row.get("witness_surfaces"))
    negative_case_codes = _strings(row.get("negative_case_codes"))
    edges: list[dict[str, Any]] = []
    for principle_id in principle_ids:
        edges.append(
            _edge(
                relation_id="principle.grounded_by.axiom",
                relation_verb="grounds",
                reverse_verb="grounded_by",
                target_kind="principle",
                target_id=principle_id,
                source_ref=f"{source_ref}.principle_ids",
                target_status="resolved_json_instance",
                justification="Axiom routing row grounds this principle id; principle JSON corpus now resolves the target as a receipt-bound active instance.",
            )
        )
    for anti_principle_id in anti_principle_ids:
        edges.append(
            _edge(
                relation_id="anti_principle.guards.axiom",
                relation_verb="guarded_by",
                reverse_verb="guards",
                target_kind="anti_principle",
                target_id=anti_principle_id,
                source_ref=f"{source_ref}.anti_principle_ids",
                target_status="resolved_json_instance",
                justification="Axiom routing row names this anti-principle guard; anti-principle JSON corpus now resolves the target as a receipt-bound active instance.",
            )
        )
    for organ_id in witness_organs:
        edges.append(
            _edge(
                relation_id="axiom.witnessed_by.organ",
                relation_verb="witnessed_by",
                reverse_verb="witnesses",
                target_kind="organ",
                target_id=organ_id,
                source_ref=f"{source_ref}.witness_organs",
                target_status="resolved_registry_or_atlas_target",
                justification="Axiom routing row names this organ as a witness candidate; support strength is computed separately.",
            )
        )

    return {
        "id": axiom_id,
        "kind": "axiom",
        "schema_version": AXIOM_INSTANCE_SCHEMA_VERSION,
        "statement": str(row.get("formal_clause") or ""),
        "title": str(row.get("title") or axiom_id),
        "status": "active",
        "created_at": AXIOM_MIGRATION_CREATED_AT,
        "authority_boundary": (
            "public_axiom_json_instance_synchronized_from_routing_registry_receipt_bound_not_source_authority_flip"
        ),
        "source_refs": [
            {
                "path": source_ref,
                "role": "current_source_of_record_for_axiom_witness_routes",
            },
            {
                "path": f"AXIOMS.md#{axiom_id}",
                "role": "legacy_markdown_projection",
            },
        ],
        "relationships": {
            "source_routing_row_ref": source_ref,
            "lineage": _strings(row.get("lineage")),
            "principle_ids": principle_ids,
            "anti_principle_ids": anti_principle_ids,
            "anti_axiom": row.get("anti_axiom"),
            "witness_organs": witness_organs,
            "witness_surfaces": witness_surfaces,
            "negative_case_codes": negative_case_codes,
            "layer_debt": _as_list(row.get("layer_debt")),
            "edges": edges,
        },
        "validator_refs": [
            "validator.microcosm.axiom",
            "validator.microcosm.axiom_support_cover",
        ],
        "receipt_refs": [_doctrine_record_receipt_ref("axiom", axiom_id)],
        "omission_receipt": {
            "omitted": [
                "private macro source bodies",
                "raw operator voice",
                "provider payload bodies",
                "support-cover generated output as source evidence",
            ],
            "reason": "Axiom instance preserves public-safe routing fields only; support is computed by validator output.",
            "drilldown": source_ref,
        },
        "anti_claims": [
            "This active axiom JSON record does not flip source authority away from core/axiom_organ_routing.json.",
            "Legacy witness_strength is not a computed support verdict.",
            "Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.",
            "Axiom admission as law does not prove that the axiom is witnessed, enforced, strong, or complete.",
        ],
        "axiom_payload": {
            "contract_version": "microcosm_axiom_instance_payload_v1",
            "admission_contract": {
                "mode": "imposed_constitutional_root",
                "proof_required_for_admission": False,
                "status": "admitted_as_public_axiom",
            },
            "formal_model": {
                "formal_clause": str(row.get("formal_clause") or ""),
                "obligations": _json(_as_list(row.get("obligations"))),
                "obligation_source_status": (
                    "pilot_obligations_present"
                    if _as_list(row.get("obligations"))
                    else "not_decomposed_yet"
                ),
            },
            "support_contract": {
                "computed_by": "validator.microcosm.axiom_support_cover",
                "legacy_routing_witness_strength": {
                    "value": row.get("witness_strength"),
                    "status": "legacy_label_not_computed_support_claim",
                },
                "support_status": "computed_in_generated_projection_not_asserted_in_source_instance",
            },
            "substrate_reciprocity_contract": _axiom_substrate_reciprocity_contract(
                source_ref=source_ref,
                principle_ids=principle_ids,
                anti_principle_ids=anti_principle_ids,
                witness_organs=witness_organs,
                witness_surfaces=witness_surfaces,
                negative_case_codes=negative_case_codes,
                layer_debt=row.get("layer_debt"),
            ),
            "projection_contract": {
                "markdown_status": "generated_projection",
                "routing_json_status": "routing_registry_source_of_record_with_receipt_bound_json_projection",
                "source_json_rel": _axiom_instance_rel(axiom_id),
                "generated_markdown_rel": _axiom_markdown_rel(axiom_id),
            },
            "migration_contract": {
                "source_of_record": AXIOM_ROUTING_REL,
                "authority_flip_status": "not_flipped",
                "parity_validator": "microcosm-substrate/scripts/build_doctrine_projection.py --check",
                "residual_pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
            },
        },
    }


def expected_axiom_instances(root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: compute the full expected axiom instance corpus from the routing registry.
    - Guarantee: returns {axiom_id: instance} for every routing row carrying an axiom_id.
    - Fails: never raises beyond underlying source reads.
    - Escalates-to: build_axiom_instance_from_routing_row.
    """
    return _expected_axiom_instances_cached(_root_key(root))


@lru_cache(maxsize=32)
def _expected_axiom_instances_cached(root_key: str) -> dict[str, dict[str, Any]]:
    """
    - Teleology: lru-cached backend for expected_axiom_instances keyed by root string.
    - Guarantee: returns the {axiom_id: instance} mapping; identical root_key returns the cached mapping.
    - Fails: never raises beyond underlying source reads.
    """
    return {
        str(row.get("axiom_id")): build_axiom_instance_from_routing_row(row, index=index)
        for index, row in enumerate(_axiom_routing_rows(Path(root_key)))
        if row.get("axiom_id")
    }


def load_axiom_instances(root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: load the axiom JSON instances already written to disk.
    - Guarantee: returns {id: payload} for each parseable axioms/*.json carrying an id; {} if the directory is absent.
    - Fails: propagates read_json_strict errors on a malformed instance file.
    - Escalates-to: axioms/*.json.
    """
    axiom_dir = _path(root, AXIOM_INSTANCE_DIR_REL)
    rows: dict[str, dict[str, Any]] = {}
    if not axiom_dir.is_dir():
        return rows
    for path in sorted(axiom_dir.glob("*.json")):
        payload = read_json_strict(path)
        if isinstance(payload, dict) and payload.get("id"):
            rows[str(payload["id"])] = payload
    return rows


def validate_axiom_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: check that written axiom instances reproduce the routing source and carry required standard fields.
    - Guarantee: returns {status: 'pass'|'blocked', expected_count, json_instance_count, missing/extra ids, errors[]}; status 'pass' iff no errors.
    - Fails: never raises; missing/extra/required-field/routing-parity defects are error rows.
    - When-needed: --check-axiom-corpus or doctrine-projection validation.
    - Escalates-to: expected_axiom_instances, std_microcosm_axiom.json.
    - Non-goal: passing proves routing-source parity only, not that any axiom is witnessed or supported.
    """
    errors: list[dict[str, Any]] = []
    expected = expected_axiom_instances(root)
    actual = load_axiom_instances(root)
    expected_ids = set(expected)
    actual_ids = set(actual)
    for missing in sorted(expected_ids - actual_ids):
        _add_error(
            errors,
            code="axiom_json_instance_missing",
            path=_axiom_instance_rel(missing),
            message="Expected axiom JSON instance is missing.",
            axiom_id=missing,
        )
    for extra in sorted(actual_ids - expected_ids):
        _add_error(
            errors,
            code="axiom_json_instance_extra",
            path=_axiom_instance_rel(extra),
            message="Axiom JSON instance has no routing row.",
            axiom_id=extra,
        )
    required = set(_as_list(load_kind_standards(root)["axiom"].get("required_fields")))
    for axiom_id in sorted(expected_ids & actual_ids):
        payload = actual[axiom_id]
        missing_required = sorted(required - set(payload))
        if missing_required:
            _add_error(
                errors,
                code="axiom_json_instance_missing_required_fields",
                path=_axiom_instance_rel(axiom_id),
                message="Axiom JSON instance is missing required standard fields.",
                axiom_id=axiom_id,
                missing_required=missing_required,
            )
        if payload != expected[axiom_id]:
            _add_error(
                errors,
                code="axiom_json_instance_routing_parity_mismatch",
                path=_axiom_instance_rel(axiom_id),
                message="Axiom JSON instance is not reproducible from the routing source of record.",
                axiom_id=axiom_id,
            )
    return {
        "schema_version": "microcosm_axiom_instance_corpus_validation_v1",
        "status": "pass" if not errors else "blocked",
        "expected_count": len(expected),
        "json_instance_count": len(actual),
        "missing_json_ids": sorted(expected_ids - actual_ids),
        "extra_json_ids": sorted(actual_ids - expected_ids),
        "errors": errors,
    }


def build_axiom_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: aggregate axiom instance parity and migration state into a corpus projection.
    - Guarantee: returns a corpus dict (counts, instance ids, missing/extra ids, parity_status, embedded validation).
    - Fails: never raises.
    - Escalates-to: validate_axiom_instance_corpus.
    """
    expected = expected_axiom_instances(root)
    actual = load_axiom_instances(root)
    validation = validate_axiom_instance_corpus(root)
    source_class = (
        "json_instances_with_routing_parity"
        if validation["status"] == "pass" and actual
        else "legacy_routing_source_until_json_parity"
    )
    return {
        "schema_version": "microcosm_axiom_instance_corpus_v1",
        "source_of_record": AXIOM_ROUTING_REL,
        "authority_flip_status": (
            "not_flipped_routing_still_source_of_record"
        ),
        "json_authority_migration_status": (
            "receipt_bound_active_instances" if validation["status"] == "pass" and actual else "not_receipt_bound_or_not_parity_fresh"
        ),
        "expected_axiom_count": len(expected),
        "json_instance_count": len(actual),
        "instance_source_class": source_class,
        "instance_ids": sorted(actual or expected),
        "missing_json_ids": validation["missing_json_ids"],
        "extra_json_ids": validation["extra_json_ids"],
        "parity_status": validation["status"],
        "validation": validation,
        "source_refs": {
            "routing_registry": AXIOM_ROUTING_REL,
            "json_instances": f"{AXIOM_INSTANCE_DIR_REL}/*.json",
            "legacy_markdown": "AXIOMS.md",
        },
        "anti_claim": (
            "Axiom JSON presence is migration progress, not proof that every axiom is witnessed or "
            "that source authority has flipped from the routing registry."
        ),
    }


def write_axiom_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: write every expected axiom instance JSON and generated markdown to disk and return the corpus.
    - Guarantee: writes axioms/<id>.json and axioms/<id>.md for all expected ids, then returns build_axiom_instance_corpus.
    - Fails: raises OSError if a target file cannot be written.
    - When-needed: --write-axiom-corpus regeneration.
    - Escalates-to: build_axiom_instance_corpus, render_axiom_markdown.
    - Non-goal: writing instances does not flip authority off the routing registry or authorize release.
    """
    resolved = _root(root)
    axiom_dir = resolved / AXIOM_INSTANCE_DIR_REL
    axiom_dir.mkdir(parents=True, exist_ok=True)
    instances = expected_axiom_instances(resolved)
    for axiom_id, payload in instances.items():
        (resolved / _axiom_instance_rel(axiom_id)).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (resolved / _axiom_markdown_rel(axiom_id)).write_text(
            render_axiom_markdown(payload),
            encoding="utf-8",
        )
    return build_axiom_instance_corpus(resolved)


def render_axiom_markdown(instance: dict[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: render the generated, do-not-hand-edit markdown projection of an axiom instance.
    - Guarantee: returns a markdown string with the formal clause, lattice neighbours, support note, and anti-claims.
    - Fails: never raises; absent fields render as empty/placeholder lines.
    - Non-goal: the markdown is a generated projection and asserts no support.
    """
    axiom_id = str(instance.get("id") or "")
    relationships = _as_dict(instance.get("relationships"))
    payload = _as_dict(instance.get("axiom_payload"))
    formal = _as_dict(payload.get("formal_model"))
    lines = [
        f"# {axiom_id} {instance.get('title')}",
        "",
        "_Generated from the governed axiom JSON instance. Do not edit this markdown by hand._",
        "",
        f"- Source JSON: `{_axiom_instance_rel(axiom_id)}`",
        f"- Routing source of record: `{relationships.get('source_routing_row_ref')}`",
        "- Authority boundary: Active JSON record synchronized from routing registry; source authority has not flipped.",
        "",
        "## Formal Clause",
        "",
        str(formal.get("formal_clause") or instance.get("statement") or ""),
        "",
        "## Lattice Neighbours",
        "",
    ]
    edges = [edge for edge in _as_list(relationships.get("edges")) if isinstance(edge, dict)]
    if edges:
        for edge in edges:
            lines.append(
                f"- `{edge.get('relation_verb')}` -> `{edge.get('target_kind')}:{edge.get('target_id')}` "
                f"({edge.get('target_status')})"
            )
    else:
        lines.append("- No non-root edges declared.")
    lines.extend(
        [
            "",
            "## Support",
            "",
            "Support is computed by `validator.microcosm.axiom_support_cover`; this markdown does not assert support.",
            "",
            "## Anti-Claims",
            "",
        ]
    )
    for anti_claim in _strings(instance.get("anti_claims")):
        lines.append(f"- {anti_claim}")
    return "\n".join(lines) + "\n"


def _extract_axiom_refs(value: str) -> list[str]:
    """
    - Teleology: extract distinct AX-<n> axiom ids from free text.
    - Guarantee: returns the AX-ids found, sorted by numeric suffix.
    - Fails: never raises; returns [] when none match.
    """
    return sorted(set(re.findall(r"\bAX-\d+\b", value)), key=lambda item: int(item.split("-", 1)[1]))


def _axiom_obligation_ref_sort_key(value: str) -> tuple[int, int, str]:
    """
    - Teleology: produce a numeric sort key for AX-<n>.O<m>.<slug> obligation refs.
    - Guarantee: returns a (axiom_num, obligation_num, slug) tuple, or a sentinel (9999, 9999, value) for non-matching strings.
    - Fails: never raises.
    """
    match = re.match(r"^AX-(\d+)\.O(\d+)\.([A-Za-z0-9_]+)$", value)
    if match:
        return (int(match.group(1)), int(match.group(2)), match.group(3))
    return (9999, 9999, value)


def _extract_axiom_obligation_refs(value: str) -> list[str]:
    """
    - Teleology: extract distinct AX-<n>.O<m>.<slug> obligation refs from free text.
    - Guarantee: returns the obligation refs found, sorted by obligation sort key.
    - Fails: never raises; returns [] when none match.
    """
    refs = re.findall(r"\bAX-\d+\.O\d+\.[A-Za-z0-9_]+\b", value)
    return sorted(set(refs), key=_axiom_obligation_ref_sort_key)


def _instance_required_fields(root: str | Path | None, kind: str) -> set[str]:
    """
    - Teleology: compute the union of required fields/keys a kind's instances must carry, from its standard.
    - Guarantee: returns the set of required_fields plus instance_schema.required_keys for the kind.
    - Fails: raises KeyError if the kind is not in the loaded standards.
    - Escalates-to: std_microcosm_<kind>.json.
    """
    standard = load_kind_standards(root)[kind]
    instance_schema = _as_dict(standard.get("instance_schema"))
    return set(_as_list(standard.get("required_fields"))) | set(
        _as_list(instance_schema.get("required_keys"))
    )


def _principle_instance_rel(principle_id: str) -> str:
    """
    - Teleology: compute the governed JSON instance path for a principle id.
    - Guarantee: returns 'principles/<principle_id>.json'.
    - Fails: never raises.
    """
    return f"{PRINCIPLE_INSTANCE_DIR_REL}/{principle_id}.json"


def _principle_markdown_rel(principle_id: str) -> str:
    """
    - Teleology: compute the generated markdown path for a principle id.
    - Guarantee: returns 'principles/<principle_id>.md'.
    - Fails: never raises.
    """
    return f"{PRINCIPLE_INSTANCE_DIR_REL}/{principle_id}.md"


def _anti_principle_instance_rel(anti_principle_id: str) -> str:
    """
    - Teleology: compute the governed JSON instance path for an anti-principle id.
    - Guarantee: returns 'anti_principles/<anti_principle_id>.json'.
    - Fails: never raises.
    """
    return f"{ANTI_PRINCIPLE_INSTANCE_DIR_REL}/{anti_principle_id}.json"


def _anti_principle_markdown_rel(anti_principle_id: str) -> str:
    """
    - Teleology: compute the generated markdown path for an anti-principle id.
    - Guarantee: returns 'anti_principles/<anti_principle_id>.md'.
    - Fails: never raises.
    """
    return f"{ANTI_PRINCIPLE_INSTANCE_DIR_REL}/{anti_principle_id}.md"


def _doctrine_record_receipt_ref(kind: str, record_id: str) -> str:
    """
    - Teleology: compute the doctrine-record receipt path for an axiom/principle/anti-principle id.
    - Guarantee: returns 'receipts/doctrine_records/<subdir>/<record_id>.receipt.json' with subdir mapped per kind.
    - Fails: never raises.
    """
    subdir_by_kind = {
        "axiom": "axioms",
        "principle": "principles",
        "anti_principle": "anti_principles",
    }
    subdir = subdir_by_kind.get(kind, kind)
    return f"{DOCTRINE_RECORD_RECEIPT_DIR_REL}/{subdir}/{record_id}.receipt.json"


def _concept_instance_rel(concept_id: str) -> str:
    """
    - Teleology: compute the governed JSON instance path for a concept id.
    - Guarantee: returns 'concepts/<concept_id>.json'.
    - Fails: never raises.
    """
    return f"{CONCEPT_INSTANCE_DIR_REL}/{concept_id}.json"


def _concept_markdown_rel(concept_id: str) -> str:
    """
    - Teleology: compute the generated markdown path for a concept id.
    - Guarantee: returns 'concepts/<concept_id>.md'.
    - Fails: never raises.
    """
    return f"{CONCEPT_INSTANCE_DIR_REL}/{concept_id}.md"


def _mechanism_instance_rel(mechanism_id: str) -> str:
    """
    - Teleology: compute the governed JSON instance path for a mechanism id.
    - Guarantee: returns 'mechanisms/<mechanism_id>.json'.
    - Fails: never raises.
    """
    return f"{MECHANISM_INSTANCE_DIR_REL}/{mechanism_id}.json"


def _mechanism_markdown_rel(mechanism_id: str) -> str:
    """
    - Teleology: compute the generated markdown path for a mechanism id.
    - Guarantee: returns 'mechanisms/<mechanism_id>.md'.
    - Fails: never raises.
    """
    return f"{MECHANISM_INSTANCE_DIR_REL}/{mechanism_id}.md"


def _organ_instance_rel(organ_id: str) -> str:
    """
    - Teleology: compute the governed JSON instance path for an organ id.
    - Guarantee: returns 'organs/<organ_id>.json'.
    - Fails: never raises.
    """
    return f"{ORGAN_INSTANCE_DIR_REL}/{organ_id}.json"


def _organ_markdown_rel(organ_id: str) -> str:
    """
    - Teleology: compute the generated markdown path for an organ id.
    - Guarantee: returns 'organs/<organ_id>.md'.
    - Fails: never raises.
    """
    return f"{ORGAN_INSTANCE_DIR_REL}/{organ_id}.md"


def _id_sort_key(value: str) -> tuple[str, int, str]:
    """
    - Teleology: produce a stable sort key that orders ID-<n> style ids numerically.
    - Guarantee: returns (prefix, number, value) for 'ABC-123' ids, else ('', 0, value).
    - Fails: never raises.
    """
    match = re.match(r"^([A-Z]+)-(\d+)$", value)
    if match:
        return (match.group(1), int(match.group(2)), value)
    return ("", 0, value)


def _principle_source_rows(root: str | Path | None) -> list[dict[str, Any]]:
    """
    - Teleology: parse PRINCIPLES.md into per-principle source rows with grounding/obligation text and body.
    - Guarantee: returns one row per '## P-<n>' heading with id, title, grounding/obligation refs, body markdown, and source_ref; [] if the file is absent.
    - Fails: never raises.
    - Escalates-to: PRINCIPLES.md.
    """
    path = _path(root, PRINCIPLES_REL)
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    body = text.split("## Anti-Claim", 1)[0]
    matches = list(re.finditer(r"^## (P-\d+) (.+)$", body, flags=re.MULTILINE))
    rows: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        section_start = match.end()
        section_end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        section = body[section_start:section_end].strip()
        grounding_match = re.search(r"^Grounding:\s*(.+)$", section, flags=re.MULTILINE)
        grounding_text = grounding_match.group(1).strip() if grounding_match else ""
        obligation_match = re.search(
            r"^Obligation grounding:\s*(.+)$", section, flags=re.MULTILINE
        )
        obligation_grounding_text = (
            obligation_match.group(1).strip() if obligation_match else ""
        )
        principle_body = section
        metadata_ends = [
            match.end()
            for match in (grounding_match, obligation_match)
            if match is not None
        ]
        if metadata_ends:
            principle_body = section[max(metadata_ends):].strip()
        rows.append(
            {
                "id": match.group(1),
                "title": match.group(2).strip(),
                "grounding_text": grounding_text,
                "axiom_refs": _extract_axiom_refs(grounding_text),
                "obligation_grounding_text": obligation_grounding_text,
                "obligation_refs": _extract_axiom_obligation_refs(
                    obligation_grounding_text
                ),
                "body_markdown": principle_body,
                "source_ref": f"{PRINCIPLES_REL}::{match.group(1)}",
            }
        )
    return rows


def _ref_ids(value: Any) -> list[str]:
    """
    - Teleology: extract distinct ref/id strings from a list of strings or dicts.
    - Guarantee: returns the sorted distinct refs (dict items read ref then id).
    - Fails: never raises; unusable items are dropped.
    """
    refs: list[str] = []
    for item in _as_list(value):
        if isinstance(item, str):
            ref = item.strip()
        elif isinstance(item, dict):
            ref = str(item.get("ref") or item.get("id") or "").strip()
        else:
            ref = ""
        if ref:
            refs.append(ref)
    return sorted(set(refs), key=_id_sort_key)


def _principle_mechanism_governance_from_organ_atlas(
    root: str | Path | None,
) -> dict[str, list[dict[str, str]]]:
    """
    - Teleology: derive principle->mechanism governance edges from organ-atlas rows that name both principle and mechanism refs.
    - Guarantee: returns {principle_id: [{mechanism_id, source_ref}, ...]} built from atlas co-occurrence.
    - Fails: never raises; rows lacking organ/principle/mechanism refs are skipped.
    - Escalates-to: core/organ_atlas.json.
    """
    atlas = _as_dict(_load(root, "core/organ_atlas.json"))
    by_principle: dict[str, dict[str, str]] = {}
    for atlas_index, row in enumerate(_as_list(atlas.get("organs"))):
        if not isinstance(row, dict):
            continue
        organ_id = str(row.get("organ_id") or row.get("id") or "").strip()
        principle_refs = _ref_ids(row.get("principle_refs"))
        mechanism_refs = _ref_ids(row.get("mechanism_refs"))
        if not organ_id or not principle_refs or not mechanism_refs:
            continue
        source_ref = f"core/organ_atlas.json::organs[{atlas_index}:{organ_id}]"
        for principle_id in principle_refs:
            targets = by_principle.setdefault(principle_id, {})
            for mechanism_id in mechanism_refs:
                targets.setdefault(mechanism_id, source_ref)
    return {
        principle_id: [
            {"mechanism_id": mechanism_id, "source_ref": source_ref}
            for mechanism_id, source_ref in sorted(
                targets.items(), key=lambda item: _id_sort_key(item[0])
            )
        ]
        for principle_id, targets in by_principle.items()
    }


def _principle_concept_governance_from_organ_atlas(
    root: str | Path | None,
) -> dict[str, list[dict[str, str]]]:
    """
    - Teleology: derive principle->concept governance edges from organ-atlas rows that name both principle and concept refs.
    - Guarantee: returns {principle_id: [{concept_id, source_ref, target_status}, ...]}; target_status resolved iff the concept is a known specimen.
    - Fails: never raises; rows lacking organ/principle/concept refs are skipped.
    - Escalates-to: core/organ_atlas.json.
    """
    atlas = _as_dict(_load(root, "core/organ_atlas.json"))
    known_concepts = {
        str(row.get("id") or "")
        for row in _concept_source_rows(root)
        if isinstance(row, dict) and row.get("id")
    }
    by_principle: dict[str, dict[str, dict[str, str]]] = {}
    for atlas_index, row in enumerate(_as_list(atlas.get("organs"))):
        if not isinstance(row, dict):
            continue
        organ_id = str(row.get("organ_id") or row.get("id") or "").strip()
        principle_refs = _ref_ids(row.get("principle_refs"))
        concept_refs = _ref_ids(row.get("concept_refs"))
        if not organ_id or not principle_refs or not concept_refs:
            continue
        source_ref = f"core/organ_atlas.json::organs[{atlas_index}:{organ_id}]"
        for principle_id in principle_refs:
            targets = by_principle.setdefault(principle_id, {})
            for concept_id in concept_refs:
                targets.setdefault(
                    concept_id,
                    {
                        "source_ref": source_ref,
                        "target_status": (
                            "resolved_json_instance"
                            if concept_id in known_concepts
                            else "unresolved_json_instance"
                        ),
                    },
                )
    return {
        principle_id: [
            {
                "concept_id": concept_id,
                "source_ref": item["source_ref"],
                "target_status": item["target_status"],
            }
            for concept_id, item in sorted(
                targets.items(), key=lambda item: _id_sort_key(item[0])
            )
        ]
        for principle_id, targets in by_principle.items()
    }


def _anti_principle_negation_targets_from_axiom_routing(
    root: str | Path | None,
) -> dict[str, list[dict[str, str]]]:
    """
    - Teleology: derive anti_principle->principle negation targets from axiom routing rows naming both.
    - Guarantee: returns {anti_principle_id: [{principle_id, source_ref}, ...]} for axioms that ground principles and name anti-principle guards.
    - Fails: never raises; rows missing axiom/principle/anti-principle ids are skipped.
    - Escalates-to: core/axiom_organ_routing.json.
    """
    routing = _as_dict(_load(root, AXIOM_ROUTING_REL))
    by_anti_principle: dict[str, dict[str, str]] = {}
    for row_index, row in enumerate(_as_list(routing.get("rows"))):
        if not isinstance(row, dict):
            continue
        axiom_id = str(row.get("axiom_id") or "").strip()
        principle_ids = _strings(row.get("principle_ids"))
        anti_principle_ids = _strings(row.get("anti_principle_ids"))
        if not axiom_id or not principle_ids or not anti_principle_ids:
            continue
        source_ref = f"{AXIOM_ROUTING_REL}::rows[{row_index}:{axiom_id}]"
        for anti_principle_id in anti_principle_ids:
            targets = by_anti_principle.setdefault(anti_principle_id, {})
            for principle_id in principle_ids:
                targets.setdefault(principle_id, source_ref)
    return {
        anti_principle_id: [
            {"principle_id": principle_id, "source_ref": source_ref}
            for principle_id, source_ref in sorted(
                targets.items(), key=lambda item: _id_sort_key(item[0])
            )
        ]
        for anti_principle_id, targets in by_anti_principle.items()
    }


def _principle_guard_targets_from_axiom_routing(
    root: str | Path | None,
) -> dict[str, list[dict[str, str]]]:
    """
    - Teleology: derive principle->anti_principle guard targets from axiom routing rows naming both.
    - Guarantee: returns {principle_id: [{anti_principle_id, source_ref}, ...]} for axioms that ground principles and name anti-principle guards.
    - Fails: never raises; rows missing axiom/principle/anti-principle ids are skipped.
    - Escalates-to: core/axiom_organ_routing.json.
    """
    routing = _as_dict(_load(root, AXIOM_ROUTING_REL))
    by_principle: dict[str, dict[str, str]] = {}
    for row_index, row in enumerate(_as_list(routing.get("rows"))):
        if not isinstance(row, dict):
            continue
        axiom_id = str(row.get("axiom_id") or "").strip()
        principle_ids = _strings(row.get("principle_ids"))
        anti_principle_ids = _strings(row.get("anti_principle_ids"))
        if not axiom_id or not principle_ids or not anti_principle_ids:
            continue
        source_ref = f"{AXIOM_ROUTING_REL}::rows[{row_index}:{axiom_id}]"
        for principle_id in principle_ids:
            targets = by_principle.setdefault(principle_id, {})
            for anti_principle_id in anti_principle_ids:
                targets.setdefault(anti_principle_id, source_ref)
    return {
        principle_id: [
            {"anti_principle_id": anti_principle_id, "source_ref": source_ref}
            for anti_principle_id, source_ref in sorted(
                targets.items(), key=lambda item: _id_sort_key(item[0])
            )
        ]
        for principle_id, targets in by_principle.items()
    }


def _anti_principle_source_rows(root: str | Path | None) -> list[dict[str, Any]]:
    """
    - Teleology: parse the ANTI_PRINCIPLES.md table into per-row source rows.
    - Guarantee: returns one row per '| AP-' table line with id, title, violated-axiom text/refs, failure statement, and source_ref; [] if the file is absent.
    - Fails: never raises; malformed 3-cell rows are skipped.
    - Escalates-to: ANTI_PRINCIPLES.md.
    """
    path = _path(root, ANTI_PRINCIPLES_REL)
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| AP-"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 3:
            continue
        first = cells[0]
        identifier, _, title = first.partition(" ")
        rows.append(
            {
                "id": identifier.strip(),
                "title": title.strip() or identifier.strip(),
                "violated_axiom_text": cells[1],
                "axiom_refs": _extract_axiom_refs(cells[1]),
                "failure_statement": cells[2],
                "source_ref": f"{ANTI_PRINCIPLES_REL}::{identifier.strip()}",
            }
        )
    return rows


def build_principle_instance_from_source_row(row: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: project one principle source row into a receipt-bound governed principle instance with grounding/governs/guard edges and residuals.
    - Guarantee: returns the principle instance dict; absent governed mechanisms/concepts/guards become residual_pressure rows and the substrate-governance contract block is attached.
    - Fails: never raises.
    - When-needed: regenerating principle instances or diagnosing one principle's governance.
    - Escalates-to: expected_principle_instances, PRINCIPLES.md, validator.microcosm.axiom_support_cover.
    - Non-goal: building an instance does not flip authority off PRINCIPLES.md, nor prove the principle is obligation-supported or governs all downstream targets.
    """
    principle_id = str(row.get("id") or "")
    source_ref = str(row.get("source_ref") or f"{PRINCIPLES_REL}::{principle_id}")
    axiom_refs = _strings(row.get("axiom_refs"))
    obligation_refs = _strings(row.get("obligation_refs"))
    governs_mechanisms = [
        item
        for item in _as_list(row.get("governs_mechanisms"))
        if isinstance(item, dict) and item.get("mechanism_id")
    ]
    governs_concepts = [
        item
        for item in _as_list(row.get("governs_concepts"))
        if isinstance(item, dict) and item.get("concept_id")
    ]
    guarded_by_anti_principles = [
        item
        for item in _as_list(row.get("guarded_by_anti_principles"))
        if isinstance(item, dict) and item.get("anti_principle_id")
    ]
    edges = [
        _edge(
            relation_id="principle.grounded_by.axiom",
            relation_verb="grounded_by",
            reverse_verb="grounds",
            target_kind="axiom",
            target_id=axiom_id,
            source_ref=f"{source_ref}.grounding",
            target_status="resolved_json_instance",
            justification=(
                "Legacy principle grounding names this axiom; axiom JSON parity corpus "
                "resolves the target while support strength remains computed separately."
            ),
        )
        for axiom_id in axiom_refs
    ]
    edges.extend(
        _edge(
            relation_id="principle.governs.mechanism",
            relation_verb="governs",
            reverse_verb="governed_by",
            target_kind="mechanism",
            target_id=str(item.get("mechanism_id")),
            source_ref=str(item.get("source_ref") or source_ref),
            target_status="resolved_json_instance",
            justification=(
                "Organ atlas row names this principle as governing an organ and names "
                "the organ mechanism ref; the principle governs the mechanism route "
                "without turning the generated projection into source evidence."
            ),
        )
        for item in governs_mechanisms
    )
    edges.extend(
        _edge(
            relation_id="principle.governs.concept",
            relation_verb="governs",
            reverse_verb="governed_by",
            target_kind="concept",
            target_id=str(item.get("concept_id")),
            source_ref=str(item.get("source_ref") or source_ref),
            target_status=str(item.get("target_status") or "unresolved_json_instance"),
            justification=(
                "Organ atlas row names this principle as governing an organ and names "
                "the organ concept ref; the principle governs the concept route "
                "without turning the generated projection into source evidence."
            ),
        )
        for item in governs_concepts
    )
    edges.extend(
        _edge(
            relation_id="anti_principle.negates_failure_of.principle",
            relation_verb="failure_guarded_by",
            reverse_verb="negates_failure_of",
            target_kind="anti_principle",
            target_id=str(item.get("anti_principle_id")),
            source_ref=str(item.get("source_ref") or source_ref),
            target_status="resolved_json_instance",
            justification=(
                "Axiom routing names this anti-principle as a guard for the "
                "same axiom that grounds the principle; the reverse edge exposes "
                "the failure guard without converting rejection into positive support."
            ),
        )
        for item in guarded_by_anti_principles
    )
    residuals: list[dict[str, str]] = []
    if not governs_mechanisms:
        residuals.append(
            {
                "relation_id": "principle.governs.mechanism",
                "status": "residual_pressure",
                "reason": "Neither legacy principle prose nor organ-atlas principle_refs name governed mechanism ids.",
            }
        )
    if not any(
        str(item.get("target_status")) == "resolved_json_instance"
        for item in governs_concepts
    ):
        residuals.append(
            {
                "relation_id": "principle.governs.concept",
                "status": "residual_pressure",
                "reason": "Neither legacy principle prose nor organ-atlas principle_refs name governed concept ids that resolve to concept JSON instances.",
            }
        )
    if not guarded_by_anti_principles:
        residuals.append(
            {
                "relation_id": "anti_principle.negates_failure_of.principle",
                "status": "residual_pressure",
                "reason": "Axiom routing does not name anti-principle guards for this principle's grounding axioms.",
            }
        )
    residual_pressure = []
    if residuals or any(edge.get("target_status") != "resolved_json_instance" for edge in edges):
        residual_pressure.append(
            {
                "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
                "gap_class": "principle_governance_edges_unpopulated_or_unresolved",
                "reentry_condition": "Bind principle.governs concept/mechanism edges from source evidence once target ids are named and resolve as generated instances.",
            }
        )
    omission_receipt = {
        "omitted": [
            "private macro source bodies",
            "raw operator voice",
            "concept and mechanism governance targets not named by legacy markdown or organ-atlas rows",
        ],
        "reason": "Principle instance preserves public-safe legacy markdown content and typed source-derived governance edges only.",
        "drilldown": source_ref,
    }
    if residual_pressure:
        omission_receipt["residual_pressure"] = residual_pressure
    governed_mechanism_ids = [
        str(item.get("mechanism_id")) for item in governs_mechanisms
    ]
    governed_concept_ids = [
        str(item.get("concept_id")) for item in governs_concepts
    ]
    guarded_by_anti_principle_ids = [
        str(item.get("anti_principle_id")) for item in guarded_by_anti_principles
    ]
    return {
        "id": principle_id,
        "kind": "principle",
        "schema_version": PRINCIPLE_INSTANCE_SCHEMA_VERSION,
        "statement": str(row.get("body_markdown") or ""),
        "title": str(row.get("title") or principle_id),
        "status": "active",
        "created_at": AXIOM_MIGRATION_CREATED_AT,
        "authority_boundary": (
            "public_principle_json_instance_synchronized_from_legacy_markdown_receipt_bound_not_source_authority_flip"
        ),
        "source_refs": [
            {
                "path": source_ref,
                "role": "legacy_markdown_source_of_record_with_receipt_bound_json_projection",
            },
            {
                "path": f"{source_ref}.obligation_grounding",
                "role": "source_owned_principle_to_axiom_obligation_grounding",
            },
            {
                "path": _principle_instance_rel(principle_id),
                "role": "governed_json_instance",
            },
        ],
        "axiom_refs": axiom_refs,
        "obligation_refs": obligation_refs,
        "governs": governed_mechanism_ids,
        "relationships": {
            "source_markdown_ref": source_ref,
            "axiom_refs": axiom_refs,
            "obligation_refs": obligation_refs,
            "governs_concept_ids": governed_concept_ids,
            "governs_mechanism_ids": governed_mechanism_ids,
            "failure_guarded_by_anti_principle_ids": guarded_by_anti_principle_ids,
            "edges": edges,
            "unpopulated_selective_relations": residuals,
        },
        "validator_refs": [
            "validator.microcosm.principle",
            "microcosm-substrate/scripts/build_doctrine_projection.py --check",
        ],
        "receipt_refs": [_doctrine_record_receipt_ref("principle", principle_id)],
        "omission_receipt": omission_receipt,
        "anti_claims": [
            "This active principle JSON record does not flip source authority away from PRINCIPLES.md.",
            "Grounding to an axiom obligation is not proof that the principle is obligation-supported.",
            "Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.",
            "Absent governs edges are residual pressure, not evidence that no governed concepts or mechanisms exist.",
        ],
        "principle_payload": {
            "contract_version": "microcosm_principle_instance_payload_v1",
            "grounding_axiom_ids": axiom_refs,
            "grounding_obligation_refs": obligation_refs,
            "legacy_heading": f"{principle_id} {row.get('title')}",
            "legacy_grounding_text": str(row.get("grounding_text") or ""),
            "legacy_obligation_grounding_text": str(
                row.get("obligation_grounding_text") or ""
            ),
            "body_markdown": str(row.get("body_markdown") or ""),
            "support_contract": {
                "computed_by": "validator.microcosm.axiom_support_cover",
                "support_status": "computed_in_generated_projection_not_asserted_in_source_instance",
                "grounding_obligation_refs": obligation_refs,
            },
            "substrate_governance_contract": {
                "contract_version": "microcosm_principle_substrate_governance_v1",
                "source_authority_ref": source_ref,
                "principle_to_substrate": {
                    "grounding_axiom_ids": axiom_refs,
                    "grounding_obligation_refs": obligation_refs,
                    "governed_mechanism_ids": governed_mechanism_ids,
                    "governed_concept_ids": governed_concept_ids,
                    "guarding_anti_principle_ids": guarded_by_anti_principle_ids,
                    "projection_edge_relation_ids": [
                        "principle.grounded_by.axiom",
                        "principle.governs.mechanism",
                        "principle.governs.concept",
                        "anti_principle.negates_failure_of.principle",
                    ],
                    "rule": (
                        "The principle guides mechanisms and concepts only through "
                        "source-derived governance edges; it is not a witness and "
                        "does not raise the support ceiling of its grounding axioms."
                    ),
                },
                "substrate_to_principle": {
                    "derived_from": [
                        "PRINCIPLES.md grounding text",
                        "PRINCIPLES.md obligation grounding text",
                        "core/organ_atlas.json principle_refs plus mechanism_refs/concept_refs",
                    ],
                    "governance_source_ref_count": len(
                        {
                            str(item.get("source_ref") or "")
                            for item in governs_mechanisms + governs_concepts
                            if item.get("source_ref")
                        }
                    ),
                    "residual_relation_count": len(residuals),
                    "refinement_rule": (
                        "Substrate rows may refine which mechanisms or concepts the "
                        "principle governs when organ-atlas source rows name those ids; "
                        "support remains inherited from specific grounding axiom obligations."
                    ),
                },
                "claim_ceiling": {
                    "computed_by": "validator.microcosm.axiom_support_cover",
                    "boundary": (
                        "Governance reach is navigability and routing pressure, not proof "
                        "that the principle is obligation-supported or complete."
                    ),
                },
            },
            "projection_contract": {
                "markdown_status": "generated_projection",
                "legacy_markdown_status": "legacy_markdown_source_of_record_with_receipt_bound_json_projection",
                "source_json_rel": _principle_instance_rel(principle_id),
                "generated_markdown_rel": _principle_markdown_rel(principle_id),
            },
            "migration_contract": {
                "source_of_record": PRINCIPLES_REL,
                "authority_flip_status": "not_flipped",
                "parity_validator": "microcosm-substrate/scripts/build_doctrine_projection.py --check",
                "residual_pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
            },
        },
    }


def build_anti_principle_instance_from_source_row(row: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: project one anti-principle source row into a receipt-bound governed instance with guards/negates edges and residuals.
    - Guarantee: returns the anti-principle instance dict; absent negated principles become a residual_pressure row.
    - Fails: never raises.
    - When-needed: regenerating anti-principle instances or diagnosing one anti-principle's guards.
    - Escalates-to: expected_anti_principle_instances, ANTI_PRINCIPLES.md.
    - Non-goal: building an instance does not flip authority off ANTI_PRINCIPLES.md, nor prove every principle-failure relation is mapped.
    """
    anti_principle_id = str(row.get("id") or "")
    source_ref = str(row.get("source_ref") or f"{ANTI_PRINCIPLES_REL}::{anti_principle_id}")
    axiom_refs = _strings(row.get("axiom_refs"))
    negates_principles = [
        item
        for item in _as_list(row.get("negates_principles"))
        if isinstance(item, dict) and item.get("principle_id")
    ]
    edges = [
        _edge(
            relation_id="anti_principle.guards.axiom",
            relation_verb="guards",
            reverse_verb="guarded_by",
            target_kind="axiom",
            target_id=axiom_id,
            source_ref=f"{source_ref}.violated_axioms",
            target_status="resolved_json_instance",
            justification=(
                "Legacy anti-principle row names this violated axiom; axiom JSON active-instance "
                "corpus resolves the guard target."
            ),
        )
        for axiom_id in axiom_refs
    ]
    edges.extend(
        _edge(
            relation_id="anti_principle.negates_failure_of.principle",
            relation_verb="negates_failure_of",
            reverse_verb="failure_guarded_by",
            target_kind="principle",
            target_id=str(item.get("principle_id")),
            source_ref=str(item.get("source_ref") or source_ref),
            target_status="resolved_json_instance",
            justification=(
                "Axiom routing names this anti-principle as a violated-axiom guard "
                "and names the principle ids grounded by the same axiom; this binds "
                "the failure guard to the principle without converting anti-axiom "
                "rejection into positive principle support."
            ),
        )
        for item in negates_principles
    )
    residuals: list[dict[str, str]] = []
    if not negates_principles:
        residuals.append(
            {
                "relation_id": "anti_principle.negates_failure_of.principle",
                "status": "residual_pressure",
                "reason": "Neither legacy anti-principle table nor axiom routing names failed principle ids.",
            }
        )
    omission_receipt = {
        "omitted": [
            "private macro source bodies",
            "raw operator voice",
            "principle negation evidence beyond source-declared axiom routing",
        ],
        "reason": "Anti-principle instance preserves public-safe legacy markdown row plus source-derived axiom and principle guard edges only.",
        "drilldown": source_ref,
    }
    if residuals:
        omission_receipt["residual_pressure"] = [
            {
                "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
                "gap_class": "anti_principle_negates_edges_unpopulated",
                "reentry_condition": "Bind anti_principle.negates_failure_of principle edges from obligation-level principle mapping evidence.",
            }
        ]
    guarded_principle_ids = [
        str(item.get("principle_id")) for item in negates_principles
    ]
    return {
        "id": anti_principle_id,
        "kind": "anti_principle",
        "schema_version": ANTI_PRINCIPLE_INSTANCE_SCHEMA_VERSION,
        "failure_statement": str(row.get("failure_statement") or ""),
        "title": str(row.get("title") or anti_principle_id),
        "status": "active",
        "created_at": AXIOM_MIGRATION_CREATED_AT,
        "authority_boundary": (
            "public_anti_principle_json_instance_synchronized_from_legacy_markdown_receipt_bound_not_source_authority_flip"
        ),
        "source_refs": [
            {
                "path": source_ref,
                "role": "legacy_markdown_source_of_record_with_receipt_bound_json_projection",
            },
            {
                "path": _anti_principle_instance_rel(anti_principle_id),
                "role": "governed_json_instance",
            },
        ],
        "guards": axiom_refs,
        "negates": guarded_principle_ids,
        "relationships": {
            "source_markdown_ref": source_ref,
            "guarded_axiom_refs": axiom_refs,
            "negates_principle_ids": guarded_principle_ids,
            "edges": edges,
            "unpopulated_selective_relations": residuals,
        },
        "validator_refs": [
            "validator.microcosm.anti_principle",
            "microcosm-substrate/scripts/build_doctrine_projection.py --check",
        ],
        "receipt_refs": [_doctrine_record_receipt_ref("anti_principle", anti_principle_id)],
        "omission_receipt": omission_receipt,
        "anti_claims": [
            "This active anti-principle JSON record does not flip source authority away from ANTI_PRINCIPLES.md.",
            "Guarding an axiom is not proof that every relevant principle failure has been mapped.",
            "Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.",
            "Absent negates edges are residual pressure, not evidence that no principle failure target exists.",
        ],
        "anti_principle_payload": {
            "contract_version": "microcosm_anti_principle_instance_payload_v1",
            "guarded_axiom_ids": axiom_refs,
            "guarded_principle_ids": guarded_principle_ids,
            "legacy_heading": f"{anti_principle_id} {row.get('title')}",
            "legacy_violated_axiom_text": str(row.get("violated_axiom_text") or ""),
            "failure_statement": str(row.get("failure_statement") or ""),
            "projection_contract": {
                "markdown_status": "generated_projection",
                "legacy_markdown_status": "legacy_markdown_source_of_record_with_receipt_bound_json_projection",
                "source_json_rel": _anti_principle_instance_rel(anti_principle_id),
                "generated_markdown_rel": _anti_principle_markdown_rel(anti_principle_id),
            },
            "migration_contract": {
                "source_of_record": ANTI_PRINCIPLES_REL,
                "authority_flip_status": "not_flipped",
                "parity_validator": "microcosm-substrate/scripts/build_doctrine_projection.py --check",
                "residual_pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
            },
        },
    }


def expected_principle_instances(root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: compute the full expected principle instance corpus from PRINCIPLES.md plus atlas-derived governance.
    - Guarantee: returns {principle_id: instance} for every parsed principle row.
    - Fails: never raises beyond underlying source reads.
    - Escalates-to: build_principle_instance_from_source_row.
    """
    return _expected_principle_instances_cached(_root_key(root))


@lru_cache(maxsize=32)
def _expected_principle_instances_cached(root_key: str) -> dict[str, dict[str, Any]]:
    """
    - Teleology: lru-cached backend for expected_principle_instances keyed by root string.
    - Guarantee: returns the {principle_id: instance} mapping; identical root_key returns the cached mapping.
    - Fails: never raises beyond underlying source reads.
    """
    mechanism_governance = _principle_mechanism_governance_from_organ_atlas(Path(root_key))
    concept_governance = _principle_concept_governance_from_organ_atlas(Path(root_key))
    principle_guards = _principle_guard_targets_from_axiom_routing(Path(root_key))
    return {
        str(row["id"]): build_principle_instance_from_source_row(
            {
                **row,
                "governs_mechanisms": mechanism_governance.get(str(row["id"]), []),
                "governs_concepts": concept_governance.get(str(row["id"]), []),
                "guarded_by_anti_principles": principle_guards.get(str(row["id"]), []),
            }
        )
        for row in _principle_source_rows(Path(root_key))
        if row.get("id")
    }


def expected_anti_principle_instances(root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: compute the full expected anti-principle instance corpus from ANTI_PRINCIPLES.md plus routing-derived negations.
    - Guarantee: returns {anti_principle_id: instance} for every parsed anti-principle row.
    - Fails: never raises beyond underlying source reads.
    - Escalates-to: build_anti_principle_instance_from_source_row.
    """
    return _expected_anti_principle_instances_cached(_root_key(root))


@lru_cache(maxsize=32)
def _expected_anti_principle_instances_cached(root_key: str) -> dict[str, dict[str, Any]]:
    """
    - Teleology: lru-cached backend for expected_anti_principle_instances keyed by root string.
    - Guarantee: returns the {anti_principle_id: instance} mapping; identical root_key returns the cached mapping.
    - Fails: never raises beyond underlying source reads.
    """
    negations = _anti_principle_negation_targets_from_axiom_routing(Path(root_key))
    return {
        str(row["id"]): build_anti_principle_instance_from_source_row(
            {**row, "negates_principles": negations.get(str(row["id"]), [])}
        )
        for row in _anti_principle_source_rows(Path(root_key))
        if row.get("id")
    }


def load_principle_instances(root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: load the principle JSON instances already written to disk.
    - Guarantee: returns {id: payload} for each parseable principles/*.json carrying an id; {} if the directory is absent.
    - Fails: propagates read_json_strict errors on a malformed instance file.
    - Escalates-to: principles/*.json.
    """
    principle_dir = _path(root, PRINCIPLE_INSTANCE_DIR_REL)
    rows: dict[str, dict[str, Any]] = {}
    if not principle_dir.is_dir():
        return rows
    for path in sorted(principle_dir.glob("*.json")):
        payload = read_json_strict(path)
        if isinstance(payload, dict) and payload.get("id"):
            rows[str(payload["id"])] = payload
    return rows


def load_anti_principle_instances(root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: load the anti-principle JSON instances already written to disk.
    - Guarantee: returns {id: payload} for each parseable anti_principles/*.json carrying an id; {} if the directory is absent.
    - Fails: propagates read_json_strict errors on a malformed instance file.
    - Escalates-to: anti_principles/*.json.
    """
    anti_principle_dir = _path(root, ANTI_PRINCIPLE_INSTANCE_DIR_REL)
    rows: dict[str, dict[str, Any]] = {}
    if not anti_principle_dir.is_dir():
        return rows
    for path in sorted(anti_principle_dir.glob("*.json")):
        payload = read_json_strict(path)
        if isinstance(payload, dict) and payload.get("id"):
            rows[str(payload["id"])] = payload
    return rows


def validate_principle_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: check that written principle instances reproduce PRINCIPLES.md and carry required standard fields.
    - Guarantee: returns {status: 'pass'|'blocked', expected_count, json_instance_count, missing/extra ids, errors[]}; status 'pass' iff no errors.
    - Fails: never raises; missing/extra/required-field/markdown-parity defects are error rows.
    - When-needed: --check-principle-corpus or doctrine-projection validation.
    - Escalates-to: expected_principle_instances.
    - Non-goal: passing proves markdown-source parity only, not obligation support or full governance coverage.
    """
    errors: list[dict[str, Any]] = []
    expected = expected_principle_instances(root)
    actual = load_principle_instances(root)
    expected_ids = set(expected)
    actual_ids = set(actual)
    for missing in sorted(expected_ids - actual_ids, key=_id_sort_key):
        _add_error(errors, code="principle_json_instance_missing", path=_principle_instance_rel(missing), message="Expected principle JSON instance is missing.", principle_id=missing)
    for extra in sorted(actual_ids - expected_ids, key=_id_sort_key):
        _add_error(errors, code="principle_json_instance_extra", path=_principle_instance_rel(extra), message="Principle JSON instance has no legacy markdown source row.", principle_id=extra)
    required = _instance_required_fields(root, "principle")
    for principle_id in sorted(expected_ids & actual_ids, key=_id_sort_key):
        payload = actual[principle_id]
        missing_required = sorted(required - set(payload))
        if missing_required:
            _add_error(errors, code="principle_json_instance_missing_required_fields", path=_principle_instance_rel(principle_id), message="Principle JSON instance is missing required standard fields.", principle_id=principle_id, missing_required=missing_required)
        if payload != expected[principle_id]:
            _add_error(errors, code="principle_json_instance_markdown_parity_mismatch", path=_principle_instance_rel(principle_id), message="Principle JSON instance is not reproducible from PRINCIPLES.md.", principle_id=principle_id)
    return {
        "schema_version": "microcosm_principle_instance_corpus_validation_v1",
        "status": "pass" if not errors else "blocked",
        "expected_count": len(expected),
        "json_instance_count": len(actual),
        "missing_json_ids": sorted(expected_ids - actual_ids, key=_id_sort_key),
        "extra_json_ids": sorted(actual_ids - expected_ids, key=_id_sort_key),
        "errors": errors,
    }


def validate_anti_principle_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: check that written anti-principle instances reproduce ANTI_PRINCIPLES.md and carry required standard fields.
    - Guarantee: returns {status: 'pass'|'blocked', expected_count, json_instance_count, missing/extra ids, errors[]}; status 'pass' iff no errors.
    - Fails: never raises; missing/extra/required-field/markdown-parity defects are error rows.
    - When-needed: --check-anti-principle-corpus or doctrine-projection validation.
    - Escalates-to: expected_anti_principle_instances.
    - Non-goal: passing proves markdown-source parity only, not that every failed-principle relation is mapped.
    """
    errors: list[dict[str, Any]] = []
    expected = expected_anti_principle_instances(root)
    actual = load_anti_principle_instances(root)
    expected_ids = set(expected)
    actual_ids = set(actual)
    for missing in sorted(expected_ids - actual_ids, key=_id_sort_key):
        _add_error(errors, code="anti_principle_json_instance_missing", path=_anti_principle_instance_rel(missing), message="Expected anti-principle JSON instance is missing.", anti_principle_id=missing)
    for extra in sorted(actual_ids - expected_ids, key=_id_sort_key):
        _add_error(errors, code="anti_principle_json_instance_extra", path=_anti_principle_instance_rel(extra), message="Anti-principle JSON instance has no legacy markdown source row.", anti_principle_id=extra)
    required = _instance_required_fields(root, "anti_principle")
    for anti_principle_id in sorted(expected_ids & actual_ids, key=_id_sort_key):
        payload = actual[anti_principle_id]
        missing_required = sorted(required - set(payload))
        if missing_required:
            _add_error(errors, code="anti_principle_json_instance_missing_required_fields", path=_anti_principle_instance_rel(anti_principle_id), message="Anti-principle JSON instance is missing required standard fields.", anti_principle_id=anti_principle_id, missing_required=missing_required)
        if payload != expected[anti_principle_id]:
            _add_error(errors, code="anti_principle_json_instance_markdown_parity_mismatch", path=_anti_principle_instance_rel(anti_principle_id), message="Anti-principle JSON instance is not reproducible from ANTI_PRINCIPLES.md.", anti_principle_id=anti_principle_id)
    return {
        "schema_version": "microcosm_anti_principle_instance_corpus_validation_v1",
        "status": "pass" if not errors else "blocked",
        "expected_count": len(expected),
        "json_instance_count": len(actual),
        "missing_json_ids": sorted(expected_ids - actual_ids, key=_id_sort_key),
        "extra_json_ids": sorted(actual_ids - expected_ids, key=_id_sort_key),
        "errors": errors,
    }


def build_principle_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: aggregate principle instance parity and migration state into a corpus projection.
    - Guarantee: returns a corpus dict (counts, instance ids, missing/extra ids, parity_status, embedded validation).
    - Fails: never raises.
    - Escalates-to: validate_principle_instance_corpus.
    """
    expected = expected_principle_instances(root)
    actual = load_principle_instances(root)
    validation = validate_principle_instance_corpus(root)
    return {
        "schema_version": "microcosm_principle_instance_corpus_v1",
        "source_of_record": PRINCIPLES_REL,
        "authority_flip_status": "not_flipped_legacy_markdown_still_source_of_record",
        "json_authority_migration_status": "receipt_bound_active_instances" if validation["status"] == "pass" and actual else "not_receipt_bound_or_not_parity_fresh",
        "expected_principle_count": len(expected),
        "json_instance_count": len(actual),
        "instance_source_class": "json_instances_with_markdown_parity" if validation["status"] == "pass" and actual else "legacy_markdown_source_until_json_parity",
        "instance_ids": sorted(actual or expected, key=_id_sort_key),
        "missing_json_ids": validation["missing_json_ids"],
        "extra_json_ids": validation["extra_json_ids"],
        "parity_status": validation["status"],
        "validation": validation,
        "source_refs": {
            "legacy_markdown": PRINCIPLES_REL,
            "json_instances": f"{PRINCIPLE_INSTANCE_DIR_REL}/*.json",
        },
        "anti_claim": "Principle JSON presence is migration progress, not proof that every principle is obligation-supported or governs all downstream concepts/mechanisms.",
    }


def build_anti_principle_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: aggregate anti-principle instance parity and migration state into a corpus projection.
    - Guarantee: returns a corpus dict (counts, instance ids, missing/extra ids, parity_status, embedded validation).
    - Fails: never raises.
    - Escalates-to: validate_anti_principle_instance_corpus.
    """
    expected = expected_anti_principle_instances(root)
    actual = load_anti_principle_instances(root)
    validation = validate_anti_principle_instance_corpus(root)
    return {
        "schema_version": "microcosm_anti_principle_instance_corpus_v1",
        "source_of_record": ANTI_PRINCIPLES_REL,
        "authority_flip_status": "not_flipped_legacy_markdown_still_source_of_record",
        "json_authority_migration_status": "receipt_bound_active_instances" if validation["status"] == "pass" and actual else "not_receipt_bound_or_not_parity_fresh",
        "expected_anti_principle_count": len(expected),
        "json_instance_count": len(actual),
        "instance_source_class": "json_instances_with_markdown_parity" if validation["status"] == "pass" and actual else "legacy_markdown_source_until_json_parity",
        "instance_ids": sorted(actual or expected, key=_id_sort_key),
        "missing_json_ids": validation["missing_json_ids"],
        "extra_json_ids": validation["extra_json_ids"],
        "parity_status": validation["status"],
        "validation": validation,
        "source_refs": {
            "legacy_markdown": ANTI_PRINCIPLES_REL,
            "json_instances": f"{ANTI_PRINCIPLE_INSTANCE_DIR_REL}/*.json",
        },
        "anti_claim": "Anti-principle JSON presence is migration progress, not proof that every failed-principle relation is obligation-mapped.",
    }


def write_principle_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: write every expected principle instance JSON and generated markdown to disk and return the corpus.
    - Guarantee: writes principles/<id>.json and principles/<id>.md for all expected ids, then returns build_principle_instance_corpus.
    - Fails: raises OSError if a target file cannot be written.
    - When-needed: --write-principle-corpus regeneration.
    - Escalates-to: build_principle_instance_corpus, render_principle_markdown.
    - Non-goal: writing instances does not flip authority off PRINCIPLES.md or authorize release.
    """
    resolved = _root(root)
    principle_dir = resolved / PRINCIPLE_INSTANCE_DIR_REL
    principle_dir.mkdir(parents=True, exist_ok=True)
    for principle_id, payload in expected_principle_instances(resolved).items():
        (resolved / _principle_instance_rel(principle_id)).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (resolved / _principle_markdown_rel(principle_id)).write_text(
            render_principle_markdown(payload),
            encoding="utf-8",
        )
    return build_principle_instance_corpus(resolved)


def write_principle_instance(
    principle_id: str,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: write a single principle instance JSON and markdown for a named id.
    - Guarantee: writes principles/<id>.json and principles/<id>.md and returns the instance payload.
    - Fails: raises KeyError when the principle id is unknown; raises OSError if a file cannot be written.
    - Escalates-to: expected_principle_instances, render_principle_markdown.
    """
    resolved = _root(root)
    payload = expected_principle_instances(resolved).get(principle_id)
    if payload is None:
        raise KeyError(f"unknown principle id: {principle_id}")
    principle_dir = resolved / PRINCIPLE_INSTANCE_DIR_REL
    principle_dir.mkdir(parents=True, exist_ok=True)
    (resolved / _principle_instance_rel(principle_id)).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (resolved / _principle_markdown_rel(principle_id)).write_text(
        render_principle_markdown(payload),
        encoding="utf-8",
    )
    return payload


def write_anti_principle_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: write every expected anti-principle instance JSON and generated markdown to disk and return the corpus.
    - Guarantee: writes anti_principles/<id>.json and anti_principles/<id>.md for all expected ids, then returns build_anti_principle_instance_corpus.
    - Fails: raises OSError if a target file cannot be written.
    - When-needed: --write-anti-principle-corpus regeneration.
    - Escalates-to: build_anti_principle_instance_corpus, render_anti_principle_markdown.
    - Non-goal: writing instances does not flip authority off ANTI_PRINCIPLES.md or authorize release.
    """
    resolved = _root(root)
    anti_principle_dir = resolved / ANTI_PRINCIPLE_INSTANCE_DIR_REL
    anti_principle_dir.mkdir(parents=True, exist_ok=True)
    for anti_principle_id, payload in expected_anti_principle_instances(resolved).items():
        (resolved / _anti_principle_instance_rel(anti_principle_id)).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (resolved / _anti_principle_markdown_rel(anti_principle_id)).write_text(
            render_anti_principle_markdown(payload),
            encoding="utf-8",
        )
    return build_anti_principle_instance_corpus(resolved)


def render_principle_markdown(instance: dict[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: render the generated, do-not-hand-edit markdown projection of a principle instance.
    - Guarantee: returns a markdown string with statement, lattice neighbours, residuals, support, grounding obligations, and anti-claims.
    - Fails: never raises; absent fields render as empty/placeholder lines.
    - Non-goal: the markdown is a generated projection, not source authority or a support claim.
    """
    principle_id = str(instance.get("id") or "")
    relationships = _as_dict(instance.get("relationships"))
    payload = _as_dict(instance.get("principle_payload"))
    lines = [
        f"# {principle_id} {instance.get('title')}",
        "",
        "_Generated from the governed principle JSON instance. Do not edit this markdown by hand._",
        "",
        f"- Source JSON: `{_principle_instance_rel(principle_id)}`",
        f"- Legacy source of record: `{relationships.get('source_markdown_ref')}`",
        "- Authority boundary: Active JSON record synchronized from legacy markdown; source authority has not flipped.",
        "",
        "## Statement",
        "",
        str(instance.get("statement") or ""),
        "",
        "## Lattice Neighbours",
        "",
    ]
    for edge in _as_list(relationships.get("edges")):
        if isinstance(edge, dict):
            lines.append(f"- `{edge.get('relation_verb')}` -> `{edge.get('target_kind')}:{edge.get('target_id')}` ({edge.get('target_status')})")
    for residual in _as_list(relationships.get("unpopulated_selective_relations")):
        if isinstance(residual, dict):
            lines.append(f"- `{residual.get('relation_id')}` -> residual pressure ({residual.get('reason')})")
    lines.extend(
        [
            "",
            "## Support",
            "",
            str(_as_dict(payload.get("support_contract")).get("support_status") or "computed by generated projection"),
            "",
            "Grounding obligations:",
        ]
    )
    for obligation_ref in _strings(
        _as_dict(payload.get("support_contract")).get("grounding_obligation_refs")
    ):
        lines.append(f"- `{obligation_ref}`")
    lines.extend(
        [
            "",
            "## Anti-Claims",
            "",
        ]
    )
    for anti_claim in _strings(instance.get("anti_claims")):
        lines.append(f"- {anti_claim}")
    return "\n".join(lines) + "\n"


def render_anti_principle_markdown(instance: dict[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: render the generated, do-not-hand-edit markdown projection of an anti-principle instance.
    - Guarantee: returns a markdown string with the rejected failure shape, lattice neighbours, residuals, and anti-claims.
    - Fails: never raises; absent fields render as empty/placeholder lines.
    - Non-goal: the markdown is a generated projection, not source authority.
    """
    anti_principle_id = str(instance.get("id") or "")
    relationships = _as_dict(instance.get("relationships"))
    lines = [
        f"# {anti_principle_id} {instance.get('title')}",
        "",
        "_Generated from the governed anti-principle JSON instance. Do not edit this markdown by hand._",
        "",
        f"- Source JSON: `{_anti_principle_instance_rel(anti_principle_id)}`",
        f"- Legacy source of record: `{relationships.get('source_markdown_ref')}`",
        "- Authority boundary: Active JSON record synchronized from legacy markdown; source authority has not flipped.",
        "",
        "## Rejected Failure Shape",
        "",
        str(instance.get("failure_statement") or ""),
        "",
        "## Lattice Neighbours",
        "",
    ]
    for edge in _as_list(relationships.get("edges")):
        if isinstance(edge, dict):
            lines.append(f"- `{edge.get('relation_verb')}` -> `{edge.get('target_kind')}:{edge.get('target_id')}` ({edge.get('target_status')})")
    for residual in _as_list(relationships.get("unpopulated_selective_relations")):
        if isinstance(residual, dict):
            lines.append(f"- `{residual.get('relation_id')}` -> residual pressure ({residual.get('reason')})")
    lines.extend(["", "## Anti-Claims", ""])
    for anti_claim in _strings(instance.get("anti_claims")):
        lines.append(f"- {anti_claim}")
    return "\n".join(lines) + "\n"


def _concept_source_rows(root: str | Path | None) -> list[dict[str, Any]]:
    """
    - Teleology: read concept population specimens from the concept entry packet into source rows.
    - Guarantee: returns one row per specimen carrying a 'concept.<specimen_id>' id and source_ref; [] if the packet is absent.
    - Fails: never raises; specimens without an id are skipped.
    - Escalates-to: atlas/entry_packet.json.
    """
    payload = _load_optional_dict(root, CONCEPT_ENTRY_PACKET_REL)
    route = _as_dict(payload.get("concept_mechanism_entry_route"))
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(_as_list(route.get("population_specimens"))):
        if not isinstance(row, dict):
            continue
        specimen_id = str(row.get("specimen_id") or "").strip()
        if not specimen_id:
            continue
        copy_row = _json(row)
        copy_row["id"] = f"concept.{specimen_id}"
        copy_row["source_ref"] = (
            f"{CONCEPT_ENTRY_PACKET_REL}::"
            f"concept_mechanism_entry_route.population_specimens[{index}:{specimen_id}]"
        )
        rows.append(copy_row)
    return rows


def _mechanism_source_rows(root: str | Path | None) -> list[dict[str, Any]]:
    """
    - Teleology: read mechanism-registry rows into source rows with stable source refs.
    - Guarantee: returns one row per registry mechanism carrying its id and source_ref.
    - Fails: never raises; rows without an id are skipped.
    - Escalates-to: core/mechanism_sources.json.
    """
    payload = _load_optional_dict(root, MECHANISM_REGISTRY_REL)
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(_as_list(payload.get("mechanisms"))):
        if not isinstance(row, dict):
            continue
        mechanism_id = str(row.get("id") or "").strip()
        if not mechanism_id:
            continue
        copy_row = _json(row)
        copy_row["source_ref"] = f"{MECHANISM_REGISTRY_REL}::mechanisms[{index}:{mechanism_id}]"
        rows.append(copy_row)
    return rows


def _source_ref_rows(source_refs: Any, role: str) -> list[dict[str, str]]:
    """
    - Teleology: wrap a list of source-ref strings into {path, role} rows.
    - Guarantee: returns one {path, role} dict per non-empty string in source_refs.
    - Fails: never raises.
    """
    return [
        {"path": ref, "role": role}
        for ref in _strings(source_refs)
    ]


def build_concept_instance_from_source_row(
    row: dict[str, Any],
    root: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: project one concept population specimen into a governed concept instance with implements/instantiated_by/abides_by edges and residuals.
    - Guarantee: returns the concept instance dict with a cluster_flag and typed edges; targets resolve only when their id is a known instance, else become unresolved edges or residual_pressure rows.
    - Fails: never raises.
    - When-needed: regenerating concept instances or diagnosing one specimen's edges.
    - Escalates-to: expected_concept_instances, atlas/entry_packet.json.
    - Non-goal: a population specimen does not flip authority off the entry packet, nor prove complete concept coverage or principle support.
    """
    concept_id = str(row.get("id") or "")
    source_ref = str(row.get("source_ref") or "")
    standard = load_kind_standards(root)["concept"]
    concept_binding = _as_dict(row.get("concept_binding"))
    mechanism_binding = _as_dict(row.get("mechanism_binding"))
    concept_role = str(concept_binding.get("concept_role") or concept_id)
    principle_ids = _strings(row.get("principle_ids")) + _strings(row.get("principle_refs"))
    mechanism_ids = _strings(row.get("mechanism_ids")) + _strings(row.get("mechanism_refs"))
    axiom_ids = _strings(row.get("axiom_ids")) + _strings(row.get("axiom_refs"))
    principle_justifications = _as_dict(row.get("principle_edge_justifications"))
    mechanism_justifications = _as_dict(row.get("mechanism_edge_justifications"))
    axiom_justifications = _as_dict(row.get("axiom_edge_justifications"))
    known_principles = set(expected_principle_instances(root))
    known_mechanisms = {str(source_row.get("id") or "") for source_row in _mechanism_source_rows(root)}
    known_axioms = set(expected_axiom_instances(root))
    edges: list[dict[str, Any]] = []
    for principle_id in principle_ids:
        edges.append(
            _edge(
                relation_id="concept.implements_or_refines.principle",
                relation_verb="implements_or_refines",
                reverse_verb="refined_by",
                target_kind="principle",
                target_id=principle_id,
                source_ref=f"{source_ref}.principle_ids",
                target_status=(
                    "resolved_json_instance"
                    if principle_id in known_principles
                    else "unresolved_json_instance"
                ),
                justification=str(
                    principle_justifications.get(principle_id)
                    or "Population specimen source row names this principle as the concept boundary refined by the specimen."
                ),
            )
        )
    for mechanism_id in mechanism_ids:
        edges.append(
            _edge(
                relation_id="concept.instantiated_by.mechanism",
                relation_verb="instantiated_by",
                reverse_verb="instantiates",
                target_kind="mechanism",
                target_id=mechanism_id,
                source_ref=f"{source_ref}.mechanism_ids",
                target_status=(
                    "resolved_json_instance"
                    if mechanism_id in known_mechanisms
                    else "unresolved_json_instance"
                ),
                justification=str(
                    mechanism_justifications.get(mechanism_id)
                    or "Population specimen source row names this mechanism as the concrete runtime instance for the concept."
                ),
            )
        )
    for axiom_id in axiom_ids:
        edges.append(
            _edge(
                relation_id="concept.abides_by.axiom",
                relation_verb="abides_by",
                reverse_verb="constrains",
                target_kind="axiom",
                target_id=axiom_id,
                source_ref=f"{source_ref}.axiom_ids",
                target_status=(
                    "resolved_json_instance"
                    if axiom_id in known_axioms
                    else "unresolved_json_instance"
                ),
                justification=str(
                    axiom_justifications.get(axiom_id)
                    or "Population specimen source row names this axiom as a constraining law for the concept boundary."
                ),
            )
        )
    residuals: list[dict[str, Any]] = []
    if not principle_ids:
        residuals.append(
            {
                "relation_id": "concept.implements_or_refines.principle",
                "status": "residual_pressure",
                "reason": "Population specimen states a concept boundary but does not name governed principle ids.",
                "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
            }
        )
    if not mechanism_ids:
        residuals.append(
            {
                "relation_id": "concept.instantiated_by.mechanism",
                "status": "residual_pressure",
                "reason": "Population specimen names a paired mechanism role but not a governed mechanism JSON instance id.",
                "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
            }
        )
    if not axiom_ids:
        residuals.append(
            {
                "relation_id": "concept.abides_by.axiom",
                "status": "residual_pressure",
                "reason": "Population specimen does not name constraining axiom ids at obligation level.",
                "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
            }
        )
    unresolved_edges = [
        edge for edge in edges if edge.get("target_status") != "resolved_json_instance"
    ]
    residual_pressure = []
    if residuals or unresolved_edges:
        residual_pressure.append(
            {
                "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
                "gap_class": "concept_selective_edges_unpopulated_or_unresolved",
                "reentry_condition": "Bind concept implements/instantiated_by/abides_by edges from source evidence once target ids are named and resolve as generated instances.",
            }
        )
    omission_receipt = {
        **_as_dict(row.get("omission_receipt")),
        "reason": (
            "Concept instance preserves public-safe specimen row fields only; "
            "typed concept edges are computed from source-named ids, and unnamed or unresolved relation classes remain residual pressure."
        ),
    }
    if residual_pressure:
        omission_receipt["residual_pressure"] = residual_pressure
    relationships = {
        "source_specimen_ref": source_ref,
        "specimen_id": row.get("specimen_id"),
        "specimen_role": row.get("specimen_role"),
        "entry_ref": row.get("entry_ref"),
        "concept_role": concept_role,
        "relationship_shape": concept_binding.get("relationship_shape"),
        "payload_shape_ref": concept_binding.get("payload_shape_ref"),
        "mechanism_pair_ref": mechanism_binding.get("concept_pair_ref"),
        "principle_refs": principle_ids,
        "mechanism_refs": mechanism_ids,
        "axiom_refs": axiom_ids,
        "edges": edges,
        "unpopulated_selective_relations": residuals,
    }
    cluster_flag = {
        "schema_version": "microcosm_concept_cluster_flag_v1",
        "cluster_id": row.get("specimen_id"),
        "kind": "concept",
        "concept_id": concept_id,
        "claim": concept_role,
        "source_ref": source_ref,
        "specimen_id": row.get("specimen_id"),
        "mechanism_count": len(mechanism_ids),
        "principle_count": len(principle_ids),
        "axiom_count": len(axiom_ids),
        "drilldown": _concept_instance_rel(concept_id),
        "authority_boundary": (
            "cluster_flag_not_source_authority_compact_navigation_row_derived_from_concept_relationships"
        ),
    }
    receipt_refs = _strings(row.get("receipt_refs")) or [
        CONCEPT_MECHANISM_RECORDS_POPULATION_RECEIPT_REL
    ]
    return {
        "id": concept_id,
        "kind": "concept",
        "schema_version": CONCEPT_INSTANCE_SCHEMA_VERSION,
        "statement": concept_role,
        "title": concept_role,
        "status": "active",
        "created_at": AXIOM_MIGRATION_CREATED_AT,
        "authority_boundary": (
            "public_concept_json_seeded_from_entry_packet_specimen_not_authority_flip_until_parity_receipt"
        ),
        "source_refs": [
            {
                "path": source_ref,
                "role": "entry_packet_population_specimen_source_of_record_until_json_parity_flip",
            },
            {
                "path": _concept_instance_rel(concept_id),
                "role": "governed_json_parity_seed",
            },
            *_source_ref_rows(row.get("source_refs"), "specimen_source_ref"),
        ],
        "relationships": relationships,
        "entry_surface_contract": _json(standard.get("entry_surface_contract")),
        "population_specimen_contract": _json(standard.get("population_specimen_contract")),
        "activation_receipt_contract": _json(standard.get("activation_receipt_contract")),
        "cluster_flag": cluster_flag,
        "validator_refs": _strings(row.get("validator_refs")) or [
            "src/microcosm_core/validators/concept_mechanism_population.py"
        ],
        "receipt_refs": receipt_refs,
        "omission_receipt": omission_receipt,
        "anti_claims": [
            *_strings(row.get("anti_claims")),
            "This concept JSON seed does not flip source authority away from atlas/entry_packet.json.",
            "A population specimen is not proof of complete concept coverage or principle support.",
            "Absent concept edges are residual pressure, not evidence that no neighbours exist.",
        ],
        "concept_payload": {
            "contract_version": "microcosm_concept_instance_payload_v1",
            "source_specimen_id": row.get("specimen_id"),
            "concept_binding": _json(concept_binding),
            "paired_mechanism_binding": _json(mechanism_binding),
            "support_contract": {
                "computed_by": "microcosm_core.doctrine_lattice.build_doctrine_projection",
                "support_status": "specimen_route_boundary_only_not_truth_support_claim",
            },
            "projection_contract": {
                "markdown_status": "generated_projection",
                "entry_packet_status": "current_source_of_record_until_parity_flip",
                "source_json_rel": _concept_instance_rel(concept_id),
                "generated_markdown_rel": _concept_markdown_rel(concept_id),
            },
            "migration_contract": {
                "source_of_record": CONCEPT_ENTRY_PACKET_REL,
                "authority_flip_status": "not_flipped",
                "parity_validator": "microcosm-substrate/scripts/build_doctrine_projection.py --check",
                "residual_pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
            },
        },
    }


def _code_locus_target_status(root: str | Path | None, locus: dict[str, Any]) -> str:
    """
    - Teleology: classify a code-locus row into planned/resolved/unresolved by resolution and on-disk existence.
    - Guarantee: returns 'planned_code_locus' when declared planned, else 'resolved_code_locus' iff the path exists, else 'unresolved_code_locus'.
    - Fails: never raises.
    """
    rel = str(locus.get("path") or "")
    if str(locus.get("resolution") or "resolved") == "planned":
        return "planned_code_locus"
    return "resolved_code_locus" if rel and _path(root, rel).is_file() else "unresolved_code_locus"


def build_mechanism_instance_from_source_row(
    row: dict[str, Any],
    root: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: project one mechanism-registry row into a governed mechanism instance with code-locus/runs_in/grounds/upstream edges and residuals.
    - Guarantee: returns the mechanism instance dict; absent code loci/concepts/organs/upstream become residual_pressure rows and a population_binding is synthesized.
    - Fails: never raises.
    - When-needed: regenerating mechanism instances or diagnosing one mechanism's grounding.
    - Escalates-to: expected_mechanism_instances, core/mechanism_sources.json.
    - Non-goal: resolved code-locus paths prove filesystem grounding only, not runtime correctness or release readiness; building an instance does not flip source authority.
    """
    mechanism_id = str(row.get("id") or "")
    source_ref = str(row.get("source_ref") or f"{MECHANISM_REGISTRY_REL}::{mechanism_id}")
    standard = load_kind_standards(root)["mechanism"]
    code_loci = _code_locus_rows(row)
    organ_ids = _strings(row.get("runs_in")) + _strings(row.get("organ_refs"))
    concept_ids = (
        _strings(row.get("concept_refs"))
        + _strings(row.get("concept_ids"))
        + _strings(row.get("grounds_concepts"))
    )
    upstream_ids = _strings(row.get("upstream")) + _strings(row.get("upstream_of"))
    known_concepts = set(expected_concept_instances(root))
    known_mechanisms = {str(source_row.get("id") or "") for source_row in _mechanism_source_rows(root)}
    atlas_ids = {str(atlas.get("organ_id") or "") for atlas in _atlas_organs(root)}
    edges: list[dict[str, Any]] = []
    for index, locus in enumerate(code_loci):
        rel = str(locus.get("path") or "")
        edges.append(
            _edge(
                relation_id="mechanism.grounded_in.code_locus",
                relation_verb="grounded_in",
                reverse_verb="implements",
                target_kind="code_locus",
                target_id=rel,
                source_ref=f"{source_ref}.code_loci[{index}]",
                target_status=_code_locus_target_status(root, locus),
                justification="Mechanism registry row names this code locus as the runtime grounding path.",
            )
        )
    for organ_id in organ_ids:
        edges.append(
            _edge(
                relation_id="mechanism.runs_in.organ",
                relation_verb="runs_in",
                reverse_verb="operates_through",
                target_kind="organ",
                target_id=organ_id,
                source_ref=f"{source_ref}.runs_in",
                target_status=(
                    "resolved_registry_or_atlas_target"
                    if organ_id in atlas_ids
                    else "planned_registry_or_atlas_target"
                ),
                justification="Mechanism registry row names this organ as the runtime host.",
            )
        )
    for concept_id in concept_ids:
        edges.append(
            _edge(
                relation_id="mechanism.grounds.concept",
                relation_verb="grounds",
                reverse_verb="grounded_by",
                target_kind="concept",
                target_id=concept_id,
                source_ref=f"{source_ref}.concept_refs",
                target_status=(
                    "resolved_json_instance" if concept_id in known_concepts else "unresolved_json_instance"
                ),
                justification="Mechanism registry row names this concept grounding target.",
            )
        )
    for upstream_id in upstream_ids:
        edges.append(
            _edge(
                relation_id="mechanism.upstream_of.mechanism",
                relation_verb="upstream_of",
                reverse_verb="downstream_of",
                target_kind="mechanism",
                target_id=upstream_id,
                source_ref=f"{source_ref}.upstream",
                target_status=(
                    "resolved_json_instance"
                    if upstream_id in known_mechanisms
                    else "unresolved_json_instance"
                ),
                justification="Mechanism registry row names this upstream/downstream mechanism relation.",
            )
        )
    residuals: list[dict[str, Any]] = []
    if not code_loci:
        residuals.append(
            {
                "relation_id": "mechanism.grounded_in.code_locus",
                "status": "residual_pressure",
                "reason": "Mechanism source row lacks required code_loci.",
                "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
            }
        )
    if not concept_ids:
        residuals.append(
            {
                "relation_id": "mechanism.grounds.concept",
                "status": "residual_pressure",
                "reason": "Mechanism source row does not name grounded concept ids.",
                "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
            }
        )
    if not organ_ids:
        residuals.append(
            {
                "relation_id": "mechanism.runs_in.organ",
                "status": "residual_pressure",
                "reason": "Mechanism source row does not name organ runtime hosts.",
                "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
            }
        )
    if not upstream_ids:
        residuals.append(
            {
                "relation_id": "mechanism.upstream_of.mechanism",
                "status": "residual_pressure",
                "reason": "Mechanism source row does not name sibling/upstream mechanism relations.",
                "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
            }
        )
    validator_refs = _strings(row.get("validator_refs")) or [
        "microcosm-substrate/scripts/build_doctrine_projection.py --check"
    ]
    receipt_refs = _strings(row.get("receipt_refs")) or [
        CONCEPT_MECHANISM_RECORDS_POPULATION_RECEIPT_REL
    ]
    omission_receipt = {
        "omitted": [
            "private macro source bodies",
            "raw operator voice",
            "provider payload bodies",
            "runtime outputs beyond named public receipt refs",
        ],
        "reason": "Mechanism instance preserves public-safe mechanism registry fields and code-locus refs only.",
        "drilldown": source_ref,
        "residual_pressure": [
            {
                "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
                "gap_class": "mechanism_selective_edges_unpopulated",
                "reentry_condition": "Bind mechanism grounds/upstream edges from source evidence; required code-locus gaps must stay explicit when present.",
            }
        ],
    }
    anti_claims = [
        "This mechanism JSON seed does not flip source authority away from core/mechanism_sources.json.",
        "Resolved code-locus paths prove filesystem grounding only, not runtime correctness or release readiness.",
        "Absent concept or sibling mechanism edges are residual pressure, not evidence that no neighbours exist.",
        "Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.",
    ]
    concept_source_by_id = {
        str(concept_row.get("id") or ""): concept_row
        for concept_row in _concept_source_rows(root)
        if concept_row.get("id")
    }
    matched_concept_rows = [
        concept_source_by_id[concept_id]
        for concept_id in concept_ids
        if concept_id in concept_source_by_id
    ]
    population_binding_source = next(
        (
            _as_dict(concept_row.get("mechanism_binding"))
            for concept_row in matched_concept_rows
            if _as_dict(concept_row.get("mechanism_binding"))
        ),
        {},
    )
    concept_pair_ref = (
        str(population_binding_source.get("concept_pair_ref") or "").strip()
        or (f"{concept_ids[0]}.concept_binding" if concept_ids else f"{source_ref}.concept_refs")
    )
    population_binding = {
        "mechanism_role": (
            str(population_binding_source.get("mechanism_role") or "").strip()
            or str(row.get("statement") or mechanism_id)
        ),
        "concept_pair_ref": concept_pair_ref,
        "source_refs": _unique_strings(
            [source_ref],
            row.get("input_refs"),
            [concept_row.get("source_ref") for concept_row in matched_concept_rows],
        ),
        "transformation_shape": (
            str(population_binding_source.get("transformation_shape") or "").strip()
            or "mechanism registry row -> code_loci -> receipt_refs -> public mechanism record"
        ),
        "state_or_proof_effect": (
            str(population_binding_source.get("state_or_proof_effect") or "").strip()
            or str(row.get("statement") or mechanism_id)
        ),
        "omission_receipt": _json(omission_receipt),
        "anti_claims": anti_claims,
        "validator_refs": validator_refs,
    }
    return {
        "id": mechanism_id,
        "kind": "mechanism",
        "schema_version": MECHANISM_INSTANCE_SCHEMA_VERSION,
        "statement": str(row.get("statement") or ""),
        "title": mechanism_id.rsplit(".", 1)[-1].replace("_", " "),
        "status": str(row.get("status") or "active"),
        "created_at": AXIOM_MIGRATION_CREATED_AT,
        "authority_boundary": (
            "public_mechanism_json_seeded_from_mechanism_registry_not_authority_flip_until_parity_receipt"
        ),
        "source_refs": [
            {
                "path": source_ref,
                "role": "mechanism_registry_source_of_record_until_json_parity_flip",
            },
            {
                "path": _mechanism_instance_rel(mechanism_id),
                "role": "governed_json_parity_seed",
            },
            *_source_ref_rows(row.get("input_refs"), "mechanism_input_ref"),
        ],
        "code_loci": _json(code_loci),
        "organ_refs": organ_ids,
        "relationships": {
            "source_registry_row_ref": source_ref,
            "code_loci": _json(code_loci),
            "runs_in": organ_ids,
            "concept_refs": concept_ids,
            "upstream_mechanism_refs": upstream_ids,
            "edges": edges,
            "unpopulated_selective_relations": residuals,
        },
        "entry_surface_contract": _json(standard.get("entry_surface_contract")),
        "population_specimen_contract": _json(standard.get("population_specimen_contract")),
        "activation_receipt_contract": _json(standard.get("activation_receipt_contract")),
        "validator_refs": validator_refs,
        "receipt_refs": receipt_refs,
        "omission_receipt": omission_receipt,
        "anti_claims": anti_claims,
        "mechanism_payload": {
            "contract_version": "microcosm_mechanism_instance_payload_v1",
            "source_registry_row": _json(row),
            "population_binding": population_binding,
            "resolution_evidence": _json(_as_dict(row.get("resolution_evidence"))),
            "guardrails": _json(_as_list(row.get("guardrails"))),
            "projection_hooks": _json(_as_list(row.get("projection_hooks"))),
            "support_contract": {
                "computed_by": "microcosm_core.doctrine_lattice.build_doctrine_projection",
                "support_status": "code_locus_and_registry_grounding_computed_in_projection_not_asserted_as_correctness",
            },
            "projection_contract": {
                "markdown_status": "generated_projection",
                "registry_status": "current_source_of_record_until_parity_flip",
                "source_json_rel": _mechanism_instance_rel(mechanism_id),
                "generated_markdown_rel": _mechanism_markdown_rel(mechanism_id),
            },
            "migration_contract": {
                "source_of_record": MECHANISM_REGISTRY_REL,
                "authority_flip_status": "not_flipped",
                "parity_validator": "microcosm-substrate/scripts/build_doctrine_projection.py --check",
                "residual_pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
            },
        },
    }


def expected_concept_instances(root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: compute the full expected concept instance corpus from entry-packet specimens.
    - Guarantee: returns {concept_id: instance} for every specimen carrying an id.
    - Fails: never raises beyond underlying source reads.
    - Escalates-to: build_concept_instance_from_source_row.
    """
    return _expected_concept_instances_cached(_root_key(root))


@lru_cache(maxsize=32)
def _expected_concept_instances_cached(root_key: str) -> dict[str, dict[str, Any]]:
    """
    - Teleology: lru-cached backend for expected_concept_instances keyed by root string.
    - Guarantee: returns the {concept_id: instance} mapping; identical root_key returns the cached mapping.
    - Fails: never raises beyond underlying source reads.
    """
    root = Path(root_key)
    return {
        str(row["id"]): build_concept_instance_from_source_row(row, root)
        for row in _concept_source_rows(root)
        if row.get("id")
    }


def expected_mechanism_instances(root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: compute the full expected mechanism instance corpus from the mechanism registry.
    - Guarantee: returns {mechanism_id: instance} for every registry row carrying an id.
    - Fails: never raises beyond underlying source reads.
    - Escalates-to: build_mechanism_instance_from_source_row.
    """
    return _expected_mechanism_instances_cached(_root_key(root))


@lru_cache(maxsize=32)
def _expected_mechanism_instances_cached(root_key: str) -> dict[str, dict[str, Any]]:
    """
    - Teleology: lru-cached backend for expected_mechanism_instances keyed by root string.
    - Guarantee: returns the {mechanism_id: instance} mapping; identical root_key returns the cached mapping.
    - Fails: never raises beyond underlying source reads.
    """
    root = Path(root_key)
    return {
        str(row["id"]): build_mechanism_instance_from_source_row(row, root)
        for row in _mechanism_source_rows(root)
        if row.get("id")
    }


def load_concept_instances(root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: load the concept JSON instances already written to disk.
    - Guarantee: returns {id: payload} for each parseable concepts/*.json carrying an id; {} if the directory is absent.
    - Fails: propagates read_json_strict errors on a malformed instance file.
    - Escalates-to: concepts/*.json.
    """
    concept_dir = _path(root, CONCEPT_INSTANCE_DIR_REL)
    rows: dict[str, dict[str, Any]] = {}
    if not concept_dir.is_dir():
        return rows
    for path in sorted(concept_dir.glob("*.json")):
        payload = read_json_strict(path)
        if isinstance(payload, dict) and payload.get("id"):
            rows[str(payload["id"])] = payload
    return rows


def load_mechanism_instances(root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: load the mechanism JSON instances already written to disk.
    - Guarantee: returns {id: payload} for each parseable mechanisms/*.json carrying an id; {} if the directory is absent.
    - Fails: propagates read_json_strict errors on a malformed instance file.
    - Escalates-to: mechanisms/*.json.
    """
    mechanism_dir = _path(root, MECHANISM_INSTANCE_DIR_REL)
    rows: dict[str, dict[str, Any]] = {}
    if not mechanism_dir.is_dir():
        return rows
    for path in sorted(mechanism_dir.glob("*.json")):
        payload = read_json_strict(path)
        if isinstance(payload, dict) and payload.get("id"):
            rows[str(payload["id"])] = payload
    return rows


def validate_concept_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: check that written concept instances reproduce the entry-packet specimens and carry required standard fields.
    - Guarantee: returns {status: 'pass'|'blocked', expected_count, json_instance_count, missing/extra ids, errors[]}; status 'pass' iff no errors.
    - Fails: never raises; missing/extra/required-field/specimen-parity defects are error rows.
    - When-needed: --check-concept-corpus or doctrine-projection validation.
    - Escalates-to: expected_concept_instances.
    - Non-goal: passing proves specimen-source parity only, not principle grounding, axiom constraint, or mechanism instantiation.
    """
    errors: list[dict[str, Any]] = []
    expected = expected_concept_instances(root)
    actual = load_concept_instances(root)
    expected_ids = set(expected)
    actual_ids = set(actual)
    for missing in sorted(expected_ids - actual_ids, key=_id_sort_key):
        _add_error(errors, code="concept_json_instance_missing", path=_concept_instance_rel(missing), message="Expected concept JSON instance is missing.", concept_id=missing)
    for extra in sorted(actual_ids - expected_ids, key=_id_sort_key):
        _add_error(errors, code="concept_json_instance_extra", path=_concept_instance_rel(extra), message="Concept JSON instance has no entry-packet specimen source row.", concept_id=extra)
    required = _instance_required_fields(root, "concept")
    for concept_id in sorted(expected_ids & actual_ids, key=_id_sort_key):
        payload = actual[concept_id]
        missing_required = sorted(required - set(payload))
        if missing_required:
            _add_error(errors, code="concept_json_instance_missing_required_fields", path=_concept_instance_rel(concept_id), message="Concept JSON instance is missing required standard fields.", concept_id=concept_id, missing_required=missing_required)
        if payload != expected[concept_id]:
            _add_error(errors, code="concept_json_instance_specimen_parity_mismatch", path=_concept_instance_rel(concept_id), message="Concept JSON instance is not reproducible from the entry-packet specimen source.", concept_id=concept_id)
    return {
        "schema_version": "microcosm_concept_instance_corpus_validation_v1",
        "status": "pass" if not errors else "blocked",
        "expected_count": len(expected),
        "json_instance_count": len(actual),
        "missing_json_ids": sorted(expected_ids - actual_ids, key=_id_sort_key),
        "extra_json_ids": sorted(actual_ids - expected_ids, key=_id_sort_key),
        "errors": errors,
    }


def validate_mechanism_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: check that written mechanism instances reproduce the mechanism registry and carry required standard fields.
    - Guarantee: returns {status: 'pass'|'blocked', expected_count, json_instance_count, missing/extra ids, errors[]}; status 'pass' iff no errors.
    - Fails: never raises; missing/extra/required-field/registry-parity defects are error rows.
    - When-needed: --check-mechanism-corpus or doctrine-projection validation.
    - Escalates-to: expected_mechanism_instances.
    - Non-goal: passing proves registry-source parity only, not runtime correctness or complete wiring.
    """
    errors: list[dict[str, Any]] = []
    expected = expected_mechanism_instances(root)
    actual = load_mechanism_instances(root)
    expected_ids = set(expected)
    actual_ids = set(actual)
    for missing in sorted(expected_ids - actual_ids, key=_id_sort_key):
        _add_error(errors, code="mechanism_json_instance_missing", path=_mechanism_instance_rel(missing), message="Expected mechanism JSON instance is missing.", mechanism_id=missing)
    for extra in sorted(actual_ids - expected_ids, key=_id_sort_key):
        _add_error(errors, code="mechanism_json_instance_extra", path=_mechanism_instance_rel(extra), message="Mechanism JSON instance has no mechanism-registry source row.", mechanism_id=extra)
    required = _instance_required_fields(root, "mechanism")
    for mechanism_id in sorted(expected_ids & actual_ids, key=_id_sort_key):
        payload = actual[mechanism_id]
        missing_required = sorted(required - set(payload))
        if missing_required:
            _add_error(errors, code="mechanism_json_instance_missing_required_fields", path=_mechanism_instance_rel(mechanism_id), message="Mechanism JSON instance is missing required standard fields.", mechanism_id=mechanism_id, missing_required=missing_required)
        if payload != expected[mechanism_id]:
            _add_error(errors, code="mechanism_json_instance_registry_parity_mismatch", path=_mechanism_instance_rel(mechanism_id), message="Mechanism JSON instance is not reproducible from the mechanism registry.", mechanism_id=mechanism_id)
    return {
        "schema_version": "microcosm_mechanism_instance_corpus_validation_v1",
        "status": "pass" if not errors else "blocked",
        "expected_count": len(expected),
        "json_instance_count": len(actual),
        "missing_json_ids": sorted(expected_ids - actual_ids, key=_id_sort_key),
        "extra_json_ids": sorted(actual_ids - expected_ids, key=_id_sort_key),
        "errors": errors,
    }


def _unpopulated_relation_count(instances: dict[str, dict[str, Any]]) -> int:
    """
    - Teleology: total the unpopulated_selective_relations residual rows across instances.
    - Guarantee: returns the integer sum of residual rows over all instance values.
    - Fails: never raises.
    """
    return sum(
        len(_as_list(_as_dict(instance.get("relationships")).get("unpopulated_selective_relations")))
        for instance in instances.values()
    )


def build_concept_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: aggregate concept instance parity, migration state, and residual counts into a corpus projection.
    - Guarantee: returns a corpus dict (counts, instance ids, missing/extra ids, unpopulated relation count, parity_status, embedded validation).
    - Fails: never raises.
    - Escalates-to: validate_concept_instance_corpus.
    """
    expected = expected_concept_instances(root)
    actual = load_concept_instances(root)
    validation = validate_concept_instance_corpus(root)
    instances = actual if actual else expected
    return {
        "schema_version": "microcosm_concept_instance_corpus_v1",
        "source_of_record": CONCEPT_ENTRY_PACKET_REL,
        "authority_flip_status": "not_flipped_entry_packet_still_source_of_record",
        "json_authority_migration_status": "parity_seeded" if validation["status"] == "pass" and actual else "not_seeded_or_not_parity_fresh",
        "expected_concept_count": len(expected),
        "json_instance_count": len(actual),
        "instance_source_class": "json_instances_with_entry_packet_parity" if validation["status"] == "pass" and actual else "entry_packet_source_until_json_parity",
        "instance_ids": sorted(actual or expected, key=_id_sort_key),
        "missing_json_ids": validation["missing_json_ids"],
        "extra_json_ids": validation["extra_json_ids"],
        "unpopulated_selective_relation_count": _unpopulated_relation_count(instances),
        "parity_status": validation["status"],
        "validation": validation,
        "source_refs": {
            "entry_packet": CONCEPT_ENTRY_PACKET_REL,
            "json_instances": f"{CONCEPT_INSTANCE_DIR_REL}/*.json",
        },
        "anti_claim": "Concept JSON presence is migration progress, not proof that every concept is principle-grounded, axiom-constrained, or mechanism-instantiated.",
    }


def build_mechanism_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: aggregate mechanism instance parity, code-locus gaps, and residual detail into a corpus projection.
    - Guarantee: returns a corpus dict (counts, without/planned code-loci, residual detail rows and grouped counts, parity_status, embedded validation).
    - Fails: never raises.
    - Escalates-to: validate_mechanism_instance_corpus.
    """
    expected = expected_mechanism_instances(root)
    actual = load_mechanism_instances(root)
    validation = validate_mechanism_instance_corpus(root)
    instances = actual if actual else expected
    residual_details = _residual_relation_detail_rows(
        "mechanism",
        instances.values(),
        authority_boundary=(
            "computed_from_mechanism_source_residuals_not_source_edge_inference"
        ),
        requirement_by_relation_id=_relation_requirement_by_id(root),
        source_ref_keys=("source_registry_row_ref",),
    )
    selective_residual_details = [
        row for row in residual_details if row.get("requirement") == "selective"
    ]
    without_code_loci = [
        mechanism_id
        for mechanism_id, instance in instances.items()
        if not _code_locus_rows(instance)
    ]
    planned_or_unresolved_code_loci = [
        edge.get("target_id")
        for instance in instances.values()
        for edge in _as_list(_as_dict(instance.get("relationships")).get("edges"))
        if isinstance(edge, dict)
        and edge.get("relation_id") == "mechanism.grounded_in.code_locus"
        and edge.get("target_status") != "resolved_code_locus"
    ]
    return {
        "schema_version": "microcosm_mechanism_instance_corpus_v1",
        "source_of_record": MECHANISM_REGISTRY_REL,
        "authority_flip_status": "not_flipped_mechanism_registry_still_source_of_record",
        "json_authority_migration_status": "parity_seeded" if validation["status"] == "pass" and actual else "not_seeded_or_not_parity_fresh",
        "expected_mechanism_count": len(expected),
        "json_instance_count": len(actual),
        "instance_source_class": "json_instances_with_registry_parity" if validation["status"] == "pass" and actual else "mechanism_registry_source_until_json_parity",
        "instance_ids": sorted(actual or expected, key=_id_sort_key),
        "missing_json_ids": validation["missing_json_ids"],
        "extra_json_ids": validation["extra_json_ids"],
        "without_code_loci": sorted(without_code_loci, key=_id_sort_key),
        "without_code_loci_count": len(without_code_loci),
        "planned_or_unresolved_code_loci": sorted(str(item) for item in planned_or_unresolved_code_loci if item),
        "planned_or_unresolved_code_loci_count": len(planned_or_unresolved_code_loci),
        "unpopulated_selective_relation_count": _unpopulated_relation_count(instances),
        "residual_relation_count": len(residual_details),
        "residual_relation_counts_by_relation_id": _relation_count_by_id(
            residual_details
        ),
        "residual_relation_counts_by_requirement": _relation_count_by_requirement(
            residual_details
        ),
        "residual_relation_detail_count": len(residual_details),
        "residual_relation_details": residual_details,
        "selective_residual_relation_count": len(selective_residual_details),
        "selective_residual_relation_counts_by_relation_id": _relation_count_by_id(
            selective_residual_details
        ),
        "selective_residual_relation_detail_count": len(selective_residual_details),
        "selective_residual_relation_details": selective_residual_details,
        "parity_status": validation["status"],
        "validation": validation,
        "source_refs": {
            "mechanism_registry": MECHANISM_REGISTRY_REL,
            "json_instances": f"{MECHANISM_INSTANCE_DIR_REL}/*.json",
        },
        "anti_claim": "Mechanism JSON presence is migration progress; resolved code-locus paths do not prove runtime correctness, release readiness, or complete concept/sibling wiring.",
    }


def write_concept_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: write every expected concept instance JSON and generated markdown to disk and return the corpus.
    - Guarantee: writes concepts/<id>.json and concepts/<id>.md for all expected ids, then returns build_concept_instance_corpus.
    - Fails: raises OSError if a target file cannot be written.
    - When-needed: --write-concept-corpus regeneration.
    - Escalates-to: build_concept_instance_corpus, render_concept_markdown.
    - Non-goal: writing instances does not flip authority off the entry packet or authorize release.
    """
    resolved = _root(root)
    concept_dir = resolved / CONCEPT_INSTANCE_DIR_REL
    concept_dir.mkdir(parents=True, exist_ok=True)
    for concept_id, payload in expected_concept_instances(resolved).items():
        (resolved / _concept_instance_rel(concept_id)).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (resolved / _concept_markdown_rel(concept_id)).write_text(
            render_concept_markdown(payload),
            encoding="utf-8",
        )
    return build_concept_instance_corpus(resolved)


def write_mechanism_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: write every expected mechanism instance JSON and generated markdown to disk and return the corpus.
    - Guarantee: writes mechanisms/<id>.json and mechanisms/<id>.md for all expected ids, then returns build_mechanism_instance_corpus.
    - Fails: raises OSError if a target file cannot be written.
    - When-needed: --write-mechanism-corpus regeneration.
    - Escalates-to: build_mechanism_instance_corpus, render_mechanism_markdown.
    - Non-goal: writing instances does not flip authority off the mechanism registry or authorize release.
    """
    resolved = _root(root)
    mechanism_dir = resolved / MECHANISM_INSTANCE_DIR_REL
    mechanism_dir.mkdir(parents=True, exist_ok=True)
    for mechanism_id, payload in expected_mechanism_instances(resolved).items():
        (resolved / _mechanism_instance_rel(mechanism_id)).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (resolved / _mechanism_markdown_rel(mechanism_id)).write_text(
            render_mechanism_markdown(payload),
            encoding="utf-8",
        )
    return build_mechanism_instance_corpus(resolved)


def _unique_strings(*values: Any) -> list[str]:
    """
    - Teleology: merge several string-list arguments into one order-preserving de-duplicated list.
    - Guarantee: returns the non-empty strings across all arguments in first-seen order, without duplicates.
    - Fails: never raises; non-string members are dropped.
    """
    seen: set[str] = set()
    rows: list[str] = []
    for value in values:
        for item in _strings(value):
            if item not in seen:
                seen.add(item)
                rows.append(item)
    return rows


def _organ_source_rows(root: str | Path | None) -> list[dict[str, Any]]:
    """
    - Teleology: join accepted organ-registry rows with their organ-atlas rows into unified source rows.
    - Guarantee: returns one row per atlas organ that is also an accepted-authority registry organ, carrying source_ref, registry_ref, and registry_payload.
    - Fails: never raises; atlas rows without an accepted registry match are skipped.
    - Escalates-to: core/organ_atlas.json, core/organ_registry.json.
    """
    accepted = _accepted_organs(root)
    registry_by_id = {
        str(row.get("organ_id") or ""): row
        for row in accepted
        if row.get("organ_id")
    }
    registry_index_by_id = {
        str(row.get("organ_id") or ""): index
        for index, row in enumerate(accepted)
        if row.get("organ_id")
    }
    rows: list[dict[str, Any]] = []
    for atlas_index, atlas_row in enumerate(_atlas_organs(root)):
        organ_id = str(atlas_row.get("organ_id") or "").strip()
        if not organ_id or organ_id not in registry_by_id:
            continue
        registry_row = registry_by_id[organ_id]
        copy_row = _json(atlas_row)
        copy_row["source_ref"] = f"core/organ_atlas.json::organs[{atlas_index}:{organ_id}]"
        copy_row["registry_ref"] = (
            "core/organ_registry.json::"
            f"implemented_organs[{registry_index_by_id.get(organ_id, 0)}:{organ_id}]"
        )
        copy_row["registry_payload"] = _json(registry_row)
        rows.append(copy_row)
    return rows


def _paper_module_target_id(ref: str) -> str:
    """
    - Teleology: normalize an organ's paper_module_ref (path or fragment) into a canonical paper-module id.
    - Guarantee: returns the value if already 'paper_module.'-prefixed, else the '#fragment' if present, else 'paper_module.<stem-of-path>'.
    - Fails: never raises; empty input returns empty.
    """
    stripped = str(ref or "").strip()
    if not stripped:
        return stripped
    if stripped.startswith("paper_module."):
        return stripped
    if "#" in stripped:
        fragment = stripped.split("#", 1)[1].strip()
        if fragment:
            return fragment
    return f"paper_module.{Path(stripped.split('#', 1)[0]).stem}"


def _organ_required_residual(relation_id: str, reason: str) -> dict[str, Any]:
    """
    - Teleology: build a typed REQUIRED residual-pressure row for an unpopulated organ relation.
    - Guarantee: returns a dict with relation_id, status 'residual_pressure', requirement 'required', reason, and pressure_ref.
    - Fails: never raises.
    """
    return {
        "relation_id": relation_id,
        "status": "residual_pressure",
        "requirement": "required",
        "reason": reason,
        "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
    }


def _organ_selective_residual(relation_id: str, reason: str) -> dict[str, Any]:
    """
    - Teleology: build a typed SELECTIVE residual-pressure row for an unpopulated organ relation.
    - Guarantee: returns a dict with relation_id, status 'residual_pressure', requirement 'selective', reason, and pressure_ref.
    - Fails: never raises.
    """
    return {
        "relation_id": relation_id,
        "status": "residual_pressure",
        "requirement": "selective",
        "reason": reason,
        "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
    }


def _organ_resolution_context(
    root: str | Path | None,
    *,
    source_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    - Teleology: precompute the standard plus known-id sets used to resolve organ edges.
    - Guarantee: returns a dict of the organ standard, known mechanism/concept/principle/axiom/organ id sets, and paper capsules.
    - Fails: never raises beyond underlying corpus reads.
    """
    rows = source_rows if source_rows is not None else _organ_source_rows(root)
    return {
        "standard": load_kind_standards(root)["organ"],
        "known_mechanisms": set(expected_mechanism_instances(root)),
        "known_concepts": set(expected_concept_instances(root)),
        "known_principles": set(expected_principle_instances(root)),
        "known_axioms": set(expected_axiom_instances(root)),
        "known_organs": {
            str(source_row.get("organ_id") or "")
            for source_row in rows
            if source_row.get("organ_id")
        },
        "paper_capsules": {
            str(paper_row.get("id") or ""): paper_row
            for paper_row in _paper_capsules(root)
            if paper_row.get("id")
        },
    }


def _context_string_set(value: Any) -> set[str]:
    """
    - Teleology: coerce a resolution-context value (set, list, tuple, or other) into a string set.
    - Guarantee: returns a set of stringified members for set/list/tuple input, else the string set of the value.
    - Fails: never raises.
    """
    if isinstance(value, set):
        return {str(item) for item in value}
    if isinstance(value, (list, tuple)):
        return {str(item) for item in value}
    return set(_strings(value))


def build_organ_instance_from_source_row(
    row: dict[str, Any],
    root: str | Path | None = None,
    *,
    resolution_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: project one accepted organ atlas+registry row into a governed organ instance with required and selective lattice edges.
    - Guarantee: returns the organ instance dict; missing paper/mechanism/code refs become required residuals, missing concept/principle/axiom/wires_to become selective residuals, and targets resolve only when ids/paths resolve.
    - Fails: never raises; gaps become residual rows rather than errors.
    - When-needed: regenerating organ instances or diagnosing one organ's edges.
    - Escalates-to: expected_organ_instances, core/organ_atlas.json, core/organ_registry.json.
    - Non-goal: building an instance does not flip source authority off atlas/registry, nor prove runtime correctness or release readiness; selective edges are never inferred from prose/specialty.
    """
    organ_id = str(row.get("organ_id") or "")
    source_ref = str(row.get("source_ref") or f"core/organ_atlas.json::{organ_id}")
    registry_ref = str(row.get("registry_ref") or f"core/organ_registry.json::{organ_id}")
    registry_payload = _as_dict(row.get("registry_payload"))
    context = resolution_context or _organ_resolution_context(root)
    standard = _as_dict(context.get("standard"))
    known_mechanisms = _context_string_set(context.get("known_mechanisms"))
    known_concepts = _context_string_set(context.get("known_concepts"))
    known_principles = _context_string_set(context.get("known_principles"))
    known_axioms = _context_string_set(context.get("known_axioms"))
    known_organs = _context_string_set(context.get("known_organs"))
    paper_capsules = {
        str(key): value
        for key, value in _as_dict(context.get("paper_capsules")).items()
    }
    paper_module_ref = str(row.get("paper_module_ref") or "").strip()
    mechanism_refs = _mechanism_ref_rows(row)
    code_loci = _code_locus_rows(row)
    concept_refs = _unique_strings(row.get("concept_refs"), row.get("instantiates"))
    principle_refs = _unique_strings(row.get("principle_refs"), row.get("governed_by"))
    axiom_refs = _unique_strings(row.get("axiom_refs"), row.get("constrained_by"))
    wires_to = _unique_strings(row.get("wires_to"))
    edges: list[dict[str, Any]] = []
    residuals: list[dict[str, Any]] = []

    if paper_module_ref:
        edges.append(
            _edge(
                relation_id="organ.explained_by.paper_module",
                relation_verb="explained_by",
                reverse_verb="explains",
                target_kind="paper_module",
                target_id=_paper_module_target_id(paper_module_ref),
                source_ref=f"{source_ref}.paper_module_ref",
                target_status=(
                    "resolved_paper_module_ref"
                    if _paper_ref_resolves(root, paper_module_ref, paper_capsules)
                    else "unresolved_paper_module_ref"
                ),
                justification="Organ atlas row names this paper-module ref as the public explanatory surface.",
            )
        )
    else:
        residuals.append(
            _organ_required_residual(
                "organ.explained_by.paper_module",
                "Accepted organ atlas row lacks the required paper_module_ref.",
            )
        )

    if mechanism_refs:
        for index, mechanism_ref in enumerate(mechanism_refs):
            ref = str(mechanism_ref.get("ref") or "")
            resolution_status = str(mechanism_ref.get("resolution_status") or "resolved")
            target_status = (
                "planned_unresolved_mechanism"
                if resolution_status == "planned_unresolved"
                else "resolved_json_instance"
                if ref in known_mechanisms
                else "unresolved_json_instance"
            )
            edges.append(
                _edge(
                    relation_id="organ.operates_through.mechanism",
                    relation_verb="operates_through",
                    reverse_verb="runs_in",
                    target_kind="mechanism",
                    target_id=ref,
                    source_ref=f"{source_ref}.mechanism_refs[{index}]",
                    target_status=target_status,
                    justification=str(
                        mechanism_ref.get("edge_justification")
                        or "Organ atlas row names this mechanism as an operational substrate for the organ."
                    ),
                )
            )
    else:
        residuals.append(
            _organ_required_residual(
                "organ.operates_through.mechanism",
                "Accepted organ atlas row lacks required mechanism_refs.",
            )
        )

    if code_loci:
        for index, locus in enumerate(code_loci):
            rel = str(locus.get("path") or "")
            edges.append(
                _edge(
                    relation_id="organ.implemented_by.code_locus",
                    relation_verb="implemented_by",
                    reverse_verb="implements",
                    target_kind="code_locus",
                    target_id=rel,
                    source_ref=f"{source_ref}.code_loci[{index}]",
                    target_status=_code_locus_target_status(root, locus),
                    justification=str(
                        locus.get("role")
                        or "Organ atlas row names this code locus as a runtime implementation path."
                    ),
                )
            )
    else:
        residuals.append(
            _organ_required_residual(
                "organ.implemented_by.code_locus",
                "Accepted organ atlas row lacks required code_loci.",
            )
        )

    for concept_id in concept_refs:
        edges.append(
            _edge(
                relation_id="organ.instantiates.concept",
                relation_verb="instantiates",
                reverse_verb="instantiated_by",
                target_kind="concept",
                target_id=concept_id,
                source_ref=f"{source_ref}.concept_refs",
                target_status=(
                    "resolved_json_instance" if concept_id in known_concepts else "unresolved_json_instance"
                ),
                justification="Organ atlas row names this recurring concept boundary for the organ.",
            )
        )
    if not concept_refs:
        residuals.append(
            _organ_selective_residual(
                "organ.instantiates.concept",
                "Organ atlas row does not name concept_refs; do not infer concepts from prose or specialty tags.",
            )
        )

    for principle_id in principle_refs:
        edges.append(
            _edge(
                relation_id="organ.governed_by.principle",
                relation_verb="governed_by",
                reverse_verb="governs",
                target_kind="principle",
                target_id=principle_id,
                source_ref=f"{source_ref}.principle_refs",
                target_status=(
                    "resolved_json_instance" if principle_id in known_principles else "unresolved_json_instance"
                ),
                justification="Organ atlas row names this principle as governing the organ.",
            )
        )
    if not principle_refs:
        residuals.append(
            _organ_selective_residual(
                "organ.governed_by.principle",
                "Organ atlas row does not name principle_refs; selective principle governance remains unpopulated.",
            )
        )

    for axiom_id in axiom_refs:
        edges.append(
            _edge(
                relation_id="organ.constrained_by.axiom",
                relation_verb="constrained_by",
                reverse_verb="constrains",
                target_kind="axiom",
                target_id=axiom_id,
                source_ref=f"{source_ref}.axiom_refs",
                target_status=(
                    "resolved_json_instance" if axiom_id in known_axioms else "unresolved_json_instance"
                ),
                justification="Organ atlas row names this axiom as a selective constraint for the organ.",
            )
        )
    if not axiom_refs:
        residuals.append(
            _organ_selective_residual(
                "organ.constrained_by.axiom",
                "Organ atlas row does not name axiom_refs/constrained_by; law binding remains residual pressure.",
            )
        )

    for target_organ_id in wires_to:
        edges.append(
            _edge(
                relation_id="organ.wires_to.organ",
                relation_verb="wires_to",
                reverse_verb="wired_from",
                target_kind="organ",
                target_id=target_organ_id,
                source_ref=f"{source_ref}.wires_to",
                target_status=(
                    "resolved_registry_or_atlas_target"
                    if target_organ_id in known_organs
                    else "unresolved_registry_or_atlas_target"
                ),
                justification="Organ atlas row names this sibling organ wiring relation.",
            )
        )
    if not wires_to:
        residuals.append(
            _organ_selective_residual(
                "organ.wires_to.organ",
                "Organ atlas row does not name sibling wires_to targets.",
            )
        )

    current_receipt = str(registry_payload.get("current_authority_receipt") or "").strip()
    generated_receipts = _strings(registry_payload.get("generated_receipts"))
    receipt_refs = ([current_receipt] if current_receipt else []) + generated_receipts
    role = str(
        row.get("agent_gloss")
        or row.get("human_gloss")
        or registry_payload.get("classification_basis")
        or organ_id
    )
    return {
        "id": organ_id,
        "organ_id": organ_id,
        "kind": "organ",
        "schema_version": ORGAN_INSTANCE_SCHEMA_VERSION,
        "display_name": str(row.get("display_name") or organ_id.replace("_", " ").title()),
        "role": role,
        "statement": role,
        "title": str(row.get("display_name") or organ_id.replace("_", " ").title()),
        "paper_module_ref": paper_module_ref,
        "mechanism_refs": _json(mechanism_refs),
        "code_loci": _json(code_loci),
        "status": str(registry_payload.get("status") or "accepted_current_authority"),
        "evidence_class": str(row.get("evidence_class") or registry_payload.get("evidence_class") or ""),
        "created_at": AXIOM_MIGRATION_CREATED_AT,
        "authority_boundary": (
            "public_organ_json_seeded_from_organ_atlas_and_registry_not_authority_flip_until_parity_receipt"
        ),
        "source_refs": [
            {
                "path": source_ref,
                "role": "organ_atlas_source_of_record_until_json_parity_flip",
            },
            {
                "path": registry_ref,
                "role": "accepted_current_authority_registry_row",
            },
            {
                "path": _organ_instance_rel(organ_id),
                "role": "governed_json_parity_seed",
            },
        ],
        "concept_refs": concept_refs,
        "principle_refs": principle_refs,
        "axiom_refs": axiom_refs,
        "wires_to": wires_to,
        "family": row.get("family"),
        "specialty": _json(_as_list(row.get("specialty"))),
        "relationships": {
            "source_atlas_row_ref": source_ref,
            "source_registry_row_ref": registry_ref,
            "paper_module_ref": paper_module_ref,
            "mechanism_refs": _json(mechanism_refs),
            "code_loci": _json(code_loci),
            "concept_refs": concept_refs,
            "principle_refs": principle_refs,
            "axiom_refs": axiom_refs,
            "wires_to": wires_to,
            "edges": edges,
            "unpopulated_selective_relations": residuals,
        },
        "entry_surface_contract": _json(standard.get("entry_surface_contract")),
        "population_specimen_contract": _json(standard.get("population_specimen_contract")),
        "activation_receipt_contract": _json(standard.get("activation_receipt_contract")),
        "validator_refs": [
            *(_strings([registry_payload.get("validator_command")]) if registry_payload.get("validator_command") else []),
            "microcosm-substrate/scripts/build_doctrine_projection.py --check-organ-corpus",
        ],
        "receipt_refs": receipt_refs,
        "omission_receipt": {
            "omitted": [
                "private macro source bodies",
                "raw operator voice",
                "provider payload bodies",
                "runtime outputs beyond named public receipts",
                "selective doctrine neighbours not named by atlas source rows",
            ],
            "reason": (
                "Organ instance preserves public-safe atlas/registry fields. Required links resolve "
                "only when source ids or paths resolve; selective law/concept/principle edges remain "
                "residual unless source evidence names ids."
            ),
            "drilldown": source_ref,
            "residual_pressure": [
                {
                    "pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
                    "gap_class": "organ_required_and_selective_edges",
                    "reentry_condition": "Populate missing paper/mechanism/code links from source evidence, then bind concept/principle/axiom/wires_to edges only when ids are named.",
                }
            ],
        },
        "anti_claims": [
            "This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.",
            "Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.",
            "Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.",
            "Absent selective organ edges are residual pressure, not evidence that no neighbours exist.",
            "Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.",
        ],
        "organ_payload": {
            "contract_version": "microcosm_organ_instance_payload_v1",
            "source_atlas_row": _json({k: v for k, v in row.items() if k not in {"registry_payload"}}),
            "source_registry_row": _json(registry_payload),
            "claim_ceiling": str(
                row.get("claim_ceiling_restated")
                or registry_payload.get("claim_ceiling")
                or "organ_atlas_registry_binding_only"
            ),
            "support_contract": {
                "computed_by": "microcosm_core.doctrine_lattice.build_doctrine_projection",
                "support_status": "required_edge_resolution_computed_in_projection_not_runtime_correctness_claim",
            },
            "projection_contract": {
                "markdown_status": "generated_projection",
                "atlas_registry_status": "current_source_of_record_until_parity_flip",
                "source_json_rel": _organ_instance_rel(organ_id),
                "generated_markdown_rel": _organ_markdown_rel(organ_id),
            },
            "migration_contract": {
                "source_of_record": "core/organ_atlas.json + core/organ_registry.json",
                "authority_flip_status": "not_flipped",
                "parity_validator": "microcosm-substrate/scripts/build_doctrine_projection.py --check",
                "residual_pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
            },
        },
    }


def expected_organ_instances(root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: compute the full expected organ instance corpus from accepted atlas+registry rows.
    - Guarantee: returns {organ_id: instance} for every accepted joined source row.
    - Fails: never raises beyond underlying source reads.
    - Escalates-to: build_organ_instance_from_source_row.
    """
    return _expected_organ_instances_cached(_root_key(root))


@lru_cache(maxsize=32)
def _expected_organ_instances_cached(root_key: str) -> dict[str, dict[str, Any]]:
    """
    - Teleology: lru-cached backend for expected_organ_instances keyed by root string.
    - Guarantee: returns the {organ_id: instance} mapping; identical root_key returns the cached mapping.
    - Fails: never raises beyond underlying source reads.
    """
    root = Path(root_key)
    source_rows = _organ_source_rows(root)
    context = _organ_resolution_context(root, source_rows=source_rows)
    return {
        str(row["organ_id"]): build_organ_instance_from_source_row(
            row,
            root,
            resolution_context=context,
        )
        for row in source_rows
        if row.get("organ_id")
    }


def load_organ_instances(root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: load the organ JSON instances already written to disk.
    - Guarantee: returns {id: payload} for each parseable organs/*.json carrying an id; {} if the directory is absent.
    - Fails: propagates read_json_strict errors on a malformed instance file.
    - Escalates-to: organs/*.json.
    """
    organ_dir = _path(root, ORGAN_INSTANCE_DIR_REL)
    rows: dict[str, dict[str, Any]] = {}
    if not organ_dir.is_dir():
        return rows
    for path in sorted(organ_dir.glob("*.json")):
        payload = read_json_strict(path)
        if isinstance(payload, dict) and payload.get("id"):
            rows[str(payload["id"])] = payload
    return rows


def validate_organ_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: check that written organ instances reproduce atlas+registry source and carry required standard fields.
    - Guarantee: returns {status: 'pass'|'blocked', expected_count, json_instance_count, missing/extra ids, errors[]}; status 'pass' iff no errors.
    - Fails: never raises; missing/extra/required-field/atlas-registry-parity defects are error rows.
    - When-needed: --check-organ-corpus or doctrine-projection validation.
    - Escalates-to: expected_organ_instances.
    - Non-goal: passing proves atlas/registry-source parity only, not complete links, selective constraints, runtime correctness, or release readiness.
    """
    errors: list[dict[str, Any]] = []
    expected = expected_organ_instances(root)
    actual = load_organ_instances(root)
    expected_ids = set(expected)
    actual_ids = set(actual)
    for missing in sorted(expected_ids - actual_ids, key=_id_sort_key):
        _add_error(errors, code="organ_json_instance_missing", path=_organ_instance_rel(missing), message="Expected organ JSON instance is missing.", organ_id=missing)
    for extra in sorted(actual_ids - expected_ids, key=_id_sort_key):
        _add_error(errors, code="organ_json_instance_extra", path=_organ_instance_rel(extra), message="Organ JSON instance has no accepted atlas/registry source row.", organ_id=extra)
    required = _instance_required_fields(root, "organ")
    for organ_id in sorted(expected_ids & actual_ids, key=_id_sort_key):
        payload = actual[organ_id]
        missing_required = sorted(required - set(payload))
        if missing_required:
            _add_error(errors, code="organ_json_instance_missing_required_fields", path=_organ_instance_rel(organ_id), message="Organ JSON instance is missing required standard fields.", organ_id=organ_id, missing_required=missing_required)
        if payload != expected[organ_id]:
            _add_error(errors, code="organ_json_instance_atlas_registry_parity_mismatch", path=_organ_instance_rel(organ_id), message="Organ JSON instance is not reproducible from organ atlas plus accepted registry row.", organ_id=organ_id)
    return {
        "schema_version": "microcosm_organ_instance_corpus_validation_v1",
        "status": "pass" if not errors else "blocked",
        "expected_count": len(expected),
        "json_instance_count": len(actual),
        "missing_json_ids": sorted(expected_ids - actual_ids, key=_id_sort_key),
        "extra_json_ids": sorted(actual_ids - expected_ids, key=_id_sort_key),
        "errors": errors,
    }


def _relation_residual_count(instances: dict[str, dict[str, Any]], *, requirement: str | None = None) -> int:
    """
    - Teleology: count residual rows across instances, optionally filtered by requirement class.
    - Guarantee: returns the integer count of unpopulated_selective_relations matching the requirement filter (or all when None).
    - Fails: never raises.
    """
    count = 0
    for instance in instances.values():
        for residual in _as_list(_as_dict(instance.get("relationships")).get("unpopulated_selective_relations")):
            if not isinstance(residual, dict):
                continue
            if requirement is None or residual.get("requirement") == requirement:
                count += 1
    return count


def build_organ_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: aggregate organ instance parity, required/selective residual detail, and migration state into a corpus projection.
    - Guarantee: returns a corpus dict (counts, residual detail rows and grouped counts, parity_status, embedded validation).
    - Fails: never raises.
    - Escalates-to: validate_organ_instance_corpus.
    """
    expected = expected_organ_instances(root)
    actual = load_organ_instances(root)
    validation = validate_organ_instance_corpus(root)
    instances = actual if actual else expected
    residual_details = _residual_relation_detail_rows(
        "organ",
        instances.values(),
        authority_boundary=(
            "computed_from_organ_atlas_registry_residuals_not_source_edge_inference"
        ),
        requirement_by_relation_id=_relation_requirement_by_id(root),
        source_ref_keys=("source_atlas_row_ref", "source_registry_row_ref"),
    )
    selective_residual_details = [
        row for row in residual_details if row.get("requirement") == "selective"
    ]
    return {
        "schema_version": "microcosm_organ_instance_corpus_v1",
        "source_of_record": "core/organ_atlas.json + core/organ_registry.json",
        "authority_flip_status": "not_flipped_organ_atlas_registry_still_source_of_record",
        "json_authority_migration_status": "parity_seeded" if validation["status"] == "pass" and actual else "not_seeded_or_not_parity_fresh",
        "expected_organ_count": len(expected),
        "json_instance_count": len(actual),
        "instance_source_class": "json_instances_with_atlas_registry_parity" if validation["status"] == "pass" and actual else "organ_atlas_registry_source_until_json_parity",
        "instance_ids": sorted(actual or expected, key=_id_sort_key),
        "missing_json_ids": validation["missing_json_ids"],
        "extra_json_ids": validation["extra_json_ids"],
        "required_relation_gap_count": _relation_residual_count(instances, requirement="required"),
        "unpopulated_selective_relation_count": _relation_residual_count(instances, requirement="selective"),
        "residual_relation_count": len(residual_details),
        "residual_relation_counts_by_relation_id": _relation_count_by_id(
            residual_details
        ),
        "residual_relation_counts_by_requirement": _relation_count_by_requirement(
            residual_details
        ),
        "residual_relation_detail_count": len(residual_details),
        "residual_relation_details": residual_details,
        "selective_residual_relation_count": len(selective_residual_details),
        "selective_residual_relation_counts_by_relation_id": _relation_count_by_id(
            selective_residual_details
        ),
        "selective_residual_relation_detail_count": len(selective_residual_details),
        "selective_residual_relation_details": selective_residual_details,
        "parity_status": validation["status"],
        "validation": validation,
        "source_refs": {
            "organ_atlas": "core/organ_atlas.json",
            "organ_registry": "core/organ_registry.json",
            "json_instances": f"{ORGAN_INSTANCE_DIR_REL}/*.json",
        },
        "anti_claim": "Organ JSON presence is migration progress, not proof that every organ has complete required links, selective doctrine constraints, runtime correctness, or release readiness.",
    }


def write_organ_instance_corpus(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: write every expected organ instance JSON and generated markdown to disk and return the corpus.
    - Guarantee: writes organs/<id>.json and organs/<id>.md for all expected ids, then returns build_organ_instance_corpus.
    - Fails: raises OSError if a target file cannot be written.
    - When-needed: --write-style regeneration of organ instances.
    - Escalates-to: build_organ_instance_corpus, render_organ_markdown.
    - Non-goal: writing instances does not flip authority off atlas/registry or authorize release.
    """
    resolved = _root(root)
    organ_dir = resolved / ORGAN_INSTANCE_DIR_REL
    organ_dir.mkdir(parents=True, exist_ok=True)
    for organ_id, payload in expected_organ_instances(resolved).items():
        (resolved / _organ_instance_rel(organ_id)).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (resolved / _organ_markdown_rel(organ_id)).write_text(
            render_organ_markdown(payload),
            encoding="utf-8",
        )
    return build_organ_instance_corpus(resolved)


def write_organ_instance(
    organ_id: str,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: write a single organ instance JSON and markdown for a named id.
    - Guarantee: writes organs/<id>.json and organs/<id>.md and returns the instance payload.
    - Fails: raises KeyError when the organ id is unknown; raises OSError if a file cannot be written.
    - Escalates-to: expected_organ_instances, render_organ_markdown.
    """
    resolved = _root(root)
    payload = expected_organ_instances(resolved).get(organ_id)
    if payload is None:
        raise KeyError(f"unknown organ id: {organ_id}")
    organ_dir = resolved / ORGAN_INSTANCE_DIR_REL
    organ_dir.mkdir(parents=True, exist_ok=True)
    (resolved / _organ_instance_rel(organ_id)).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (resolved / _organ_markdown_rel(organ_id)).write_text(
        render_organ_markdown(payload),
        encoding="utf-8",
    )
    return payload


def render_organ_markdown(instance: dict[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: render the generated, do-not-hand-edit markdown projection of an organ instance.
    - Guarantee: returns a markdown string with role, lattice neighbours, residuals, and anti-claims.
    - Fails: never raises; absent fields render as empty/placeholder lines.
    - Non-goal: the markdown is a generated projection, not source authority.
    """
    organ_id = str(instance.get("id") or "")
    relationships = _as_dict(instance.get("relationships"))
    lines = [
        f"# {organ_id} {instance.get('title')}",
        "",
        "_Generated from the governed organ JSON instance. Do not edit this markdown by hand._",
        "",
        f"- Source JSON: `{_organ_instance_rel(organ_id)}`",
        f"- Atlas source of record: `{relationships.get('source_atlas_row_ref')}`",
        f"- Registry source of record: `{relationships.get('source_registry_row_ref')}`",
        "- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.",
        "",
        "## Role",
        "",
        str(instance.get("role") or ""),
        "",
        "## Lattice Neighbours",
        "",
    ]
    for edge in _as_list(relationships.get("edges")):
        if isinstance(edge, dict):
            lines.append(f"- `{edge.get('relation_verb')}` -> `{edge.get('target_kind')}:{edge.get('target_id')}` ({edge.get('target_status')})")
    for residual in _as_list(relationships.get("unpopulated_selective_relations")):
        if isinstance(residual, dict):
            lines.append(f"- `{residual.get('relation_id')}` -> residual pressure ({residual.get('reason')})")
    lines.extend(["", "## Anti-Claims", ""])
    for anti_claim in _strings(instance.get("anti_claims")):
        lines.append(f"- {anti_claim}")
    return "\n".join(lines) + "\n"


def render_concept_markdown(instance: dict[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: render the generated, do-not-hand-edit markdown projection of a concept instance.
    - Guarantee: returns a markdown string with statement, residual neighbours, and anti-claims.
    - Fails: never raises; absent fields render as empty/placeholder lines.
    - Non-goal: the markdown is a generated projection, not source authority.
    """
    concept_id = str(instance.get("id") or "")
    relationships = _as_dict(instance.get("relationships"))
    lines = [
        f"# {concept_id} {instance.get('title')}",
        "",
        "_Generated from the governed concept JSON instance. Do not edit this markdown by hand._",
        "",
        f"- Source JSON: `{_concept_instance_rel(concept_id)}`",
        f"- Entry-packet source of record: `{relationships.get('source_specimen_ref')}`",
        "- Authority boundary: JSON parity seed; entry-packet source authority has not flipped.",
        "",
        "## Statement",
        "",
        str(instance.get("statement") or ""),
        "",
        "## Lattice Neighbours",
        "",
    ]
    for residual in _as_list(relationships.get("unpopulated_selective_relations")):
        if isinstance(residual, dict):
            lines.append(f"- `{residual.get('relation_id')}` -> residual pressure ({residual.get('reason')})")
    lines.extend(["", "## Anti-Claims", ""])
    for anti_claim in _strings(instance.get("anti_claims")):
        lines.append(f"- {anti_claim}")
    return "\n".join(lines) + "\n"


def render_mechanism_markdown(instance: dict[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: render the generated, do-not-hand-edit markdown projection of a mechanism instance.
    - Guarantee: returns a markdown string with statement, lattice neighbours, residuals, and anti-claims.
    - Fails: never raises; absent fields render as empty/placeholder lines.
    - Non-goal: the markdown is a generated projection, not source authority.
    """
    mechanism_id = str(instance.get("id") or "")
    relationships = _as_dict(instance.get("relationships"))
    lines = [
        f"# {mechanism_id} {instance.get('title')}",
        "",
        "_Generated from the governed mechanism JSON instance. Do not edit this markdown by hand._",
        "",
        f"- Source JSON: `{_mechanism_instance_rel(mechanism_id)}`",
        f"- Registry source of record: `{relationships.get('source_registry_row_ref')}`",
        "- Authority boundary: JSON parity seed; mechanism registry source authority has not flipped.",
        "",
        "## Statement",
        "",
        str(instance.get("statement") or ""),
        "",
        "## Lattice Neighbours",
        "",
    ]
    for edge in _as_list(relationships.get("edges")):
        if isinstance(edge, dict):
            lines.append(f"- `{edge.get('relation_verb')}` -> `{edge.get('target_kind')}:{edge.get('target_id')}` ({edge.get('target_status')})")
    for residual in _as_list(relationships.get("unpopulated_selective_relations")):
        if isinstance(residual, dict):
            lines.append(f"- `{residual.get('relation_id')}` -> residual pressure ({residual.get('reason')})")
    lines.extend(["", "## Anti-Claims", ""])
    for anti_claim in _strings(instance.get("anti_claims")):
        lines.append(f"- {anti_claim}")
    return "\n".join(lines) + "\n"


def _node_id(value: str) -> str:
    """
    - Teleology: sanitize an arbitrary string into a mermaid-safe node identifier.
    - Guarantee: returns the value with non-word chars replaced by '_', prefixed 'n_' if empty or leading-digit.
    - Fails: never raises.
    """
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"n_{cleaned}"
    return cleaned


def render_doctrine_mermaid(instances: list[dict[str, Any]]) -> str:
    """
    [ACTION]
    - Teleology: render the doctrine-lattice instances and their edges as a mermaid flowchart.
    - Guarantee: returns a mermaid flowchart string with one node per instance and per edge target, residual targets styled distinctly.
    - Fails: never raises; non-dict edges are skipped.
    - Non-goal: the graph is a generated projection, not source authority.
    """
    lines = [
        "flowchart LR",
        "  classDef axiom fill:#f8fafc,stroke:#334155,color:#0f172a;",
        "  classDef principle fill:#eff6ff,stroke:#2563eb,color:#1e3a8a;",
        "  classDef anti_principle fill:#fef2f2,stroke:#dc2626,color:#7f1d1d;",
        "  classDef concept fill:#ecfeff,stroke:#0891b2,color:#164e63;",
        "  classDef mechanism fill:#f0fdf4,stroke:#16a34a,color:#14532d;",
        "  classDef organ fill:#fdf4ff,stroke:#a21caf,color:#581c87;",
        "  classDef paper_module fill:#fefce8,stroke:#ca8a04,color:#713f12;",
        "  classDef skill fill:#f5f3ff,stroke:#7c3aed,color:#4c1d95;",
        "  classDef standard fill:#eef2ff,stroke:#4f46e5,color:#312e81;",
        "  classDef residual fill:#fff7ed,stroke:#c2410c,color:#7c2d12;",
    ]
    for instance in instances:
        instance_id = str(instance.get("id") or "")
        kind = str(instance.get("kind") or "unknown")
        title = str(instance.get("title") or instance_id)
        class_name = (
            kind
            if kind
            in {
                "axiom",
                "principle",
                "anti_principle",
                "concept",
                "mechanism",
                "organ",
                "paper_module",
                "skill",
                "standard",
            }
            else "residual"
        )
        lines.append(f'  {_node_id(f"{kind}:{instance_id}")}["{kind}:{instance_id}: {title}"]:::{class_name}')
        for edge in _as_list(_as_dict(instance.get("relationships")).get("edges")):
            if not isinstance(edge, dict):
                continue
            target = f"{edge.get('target_kind')}:{edge.get('target_id')}"
            target_node = _node_id(target)
            target_status = str(edge.get("target_status") or "")
            klass = (
                ":::residual"
                if target_status
                not in {
                    "resolved_json_instance",
                    "resolved_registry_or_atlas_target",
                    "resolved_code_locus",
                    "resolved_paper_module_ref",
                    "resolved_standard_contract",
                    "resolved_doctrine_kind_contract",
                }
                else ""
            )
            lines.append(f'  {target_node}["{target}"]{klass}')
            lines.append(
                f"  {_node_id(f'{kind}:{instance_id}')} -- {edge.get('relation_verb')} --> {target_node}"
            )
    return "\n".join(lines) + "\n"


def build_lattice_health(
    root: str | Path | None = None,
    *,
    projection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: compute the cross-kind doctrine-lattice health payload (per-kind parity, support cover, evidence walkability, residual pressure).
    - Guarantee: returns a health dict combining every corpus's parity/gap metrics, axiom support-cover results, evidence walkability, and the derived residual-pressure rows.
    - Fails: never raises; absent on-disk instances fall back to expected instances.
    - When-needed: building the entry card or auditing overall lattice population.
    - Escalates-to: build_*_instance_corpus, evaluate_axiom_support_cover, _evidence_walkability_health.
    - Non-goal: health is a computed projection, not source authority, release readiness, or proof of correctness.
    """
    resolved = _root(root)
    corpus = build_axiom_instance_corpus(resolved)
    principle_corpus = build_principle_instance_corpus(resolved)
    anti_principle_corpus = build_anti_principle_instance_corpus(resolved)
    concept_corpus = build_concept_instance_corpus(resolved)
    mechanism_corpus = build_mechanism_instance_corpus(resolved)
    organ_corpus = build_organ_instance_corpus(resolved)
    paper_module_instance_corpus = build_paper_module_instance_corpus(resolved)
    skill_corpus = build_skill_instance_corpus(resolved)
    standard_corpus = build_standard_instance_corpus(resolved)
    instances = list(load_axiom_instances(resolved).values())
    if not instances:
        instances = list(expected_axiom_instances(resolved).values())
    principle_instances = list(load_principle_instances(resolved).values())
    if not principle_instances:
        principle_instances = list(expected_principle_instances(resolved).values())
    anti_principle_instances = list(load_anti_principle_instances(resolved).values())
    if not anti_principle_instances:
        anti_principle_instances = list(expected_anti_principle_instances(resolved).values())
    concept_instances = list(load_concept_instances(resolved).values())
    if not concept_instances:
        concept_instances = list(expected_concept_instances(resolved).values())
    mechanism_instances = list(load_mechanism_instances(resolved).values())
    if not mechanism_instances:
        mechanism_instances = list(expected_mechanism_instances(resolved).values())
    organ_instances = list(load_organ_instances(resolved).values())
    if not organ_instances:
        organ_instances = list(expected_organ_instances(resolved).values())
    paper_module_instances = list(load_paper_module_instances(resolved).values())
    if not paper_module_instances:
        paper_module_instances = list(expected_paper_module_instances(resolved).values())
    skill_instances = list(load_skill_instances(resolved).values())
    if not skill_instances:
        skill_instances = list(expected_skill_instances(resolved).values())
    standard_instances = list(load_standard_instances(resolved).values())
    if not standard_instances:
        standard_instances = list(expected_standard_instances(resolved).values())
    support = evaluate_axiom_support_cover(resolved)
    support_frontiers = _as_dict(support.get("support_frontiers"))
    piloted_axioms = set(_strings(support.get("piloted_axioms")))
    routing = _load_optional_dict(resolved, AXIOM_ROUTING_REL)
    routing_principles = sorted(
        {
            principle
            for row in _as_list(routing.get("rows"))
            if isinstance(row, dict)
            for principle in _strings(row.get("principle_ids"))
        },
        key=_id_sort_key,
    )
    principle_instance_ids = sorted(
        {str(instance.get("id")) for instance in principle_instances if instance.get("id")},
        key=_id_sort_key,
    )
    all_principles = sorted(set(routing_principles) | set(principle_instance_ids), key=_id_sort_key)
    supported_principles = {
        str(row.get("principle_id"))
        for row in _as_list(support.get("principle_support_index"))
        if isinstance(row, dict) and row.get("principle_id")
    }
    principle_unpopulated_governance = [
        str(instance.get("id"))
        for instance in principle_instances
        if not any(
            isinstance(edge, dict)
            and edge.get("relation_id")
            in {"principle.governs.concept", "principle.governs.mechanism"}
            and edge.get("target_status") == "resolved_json_instance"
            for edge in _as_list(_as_dict(instance.get("relationships")).get("edges"))
        )
    ]
    anti_principle_unpopulated_negates = [
        str(instance.get("id"))
        for instance in anti_principle_instances
        if not any(
            isinstance(edge, dict)
            and edge.get("relation_id") == "anti_principle.negates_failure_of.principle"
            and edge.get("target_status") == "resolved_json_instance"
            for edge in _as_list(_as_dict(instance.get("relationships")).get("edges"))
        )
    ]
    concept_unpopulated_edges = [
        str(instance.get("id"))
        for instance in concept_instances
        if _as_list(_as_dict(instance.get("relationships")).get("unpopulated_selective_relations"))
    ]
    mechanism_unpopulated_edges = [
        str(instance.get("id"))
        for instance in mechanism_instances
        if _as_list(_as_dict(instance.get("relationships")).get("unpopulated_selective_relations"))
    ]
    organs_unconstrained = [
        str(instance.get("id"))
        for instance in organ_instances
        if instance.get("id")
        and not _strings(instance.get("axiom_refs"))
        and not any(
            isinstance(edge, dict) and edge.get("relation_id") == "organ.constrained_by.axiom"
            for edge in _as_list(_as_dict(instance.get("relationships")).get("edges"))
        )
    ]
    organ_required_edge_gaps = [
        str(instance.get("id"))
        for instance in organ_instances
        if instance.get("id")
        and any(
            isinstance(residual, dict) and residual.get("requirement") == "required"
            for residual in _as_list(_as_dict(instance.get("relationships")).get("unpopulated_selective_relations"))
        )
    ]
    organ_selective_edge_gaps = [
        str(instance.get("id"))
        for instance in organ_instances
        if instance.get("id")
        and any(
            isinstance(residual, dict) and residual.get("requirement") == "selective"
            for residual in _as_list(_as_dict(instance.get("relationships")).get("unpopulated_selective_relations"))
        )
    ]
    organ_required_edge_gap_details = _organ_required_edge_gap_detail_rows(organ_instances)
    mechanisms_without_code = [
        str(instance.get("id"))
        for instance in mechanism_instances
        if instance.get("id") and not _code_locus_rows(instance)
    ]
    paper_module_required_subject_gaps = [
        str(instance.get("id"))
        for instance in paper_module_instances
        if instance.get("id")
        and any(
            isinstance(residual, dict)
            and residual.get("relation_id") == "paper_module.explains.organ_or_mechanism"
            for residual in _as_list(_as_dict(instance.get("relationships")).get("unpopulated_selective_relations"))
        )
    ]
    paper_module_selective_edge_gaps = [
        str(instance.get("id"))
        for instance in paper_module_instances
        if instance.get("id")
        and any(
            isinstance(residual, dict) and residual.get("requirement") == "selective"
            for residual in _as_list(_as_dict(instance.get("relationships")).get("unpopulated_selective_relations"))
        )
    ]
    skill_required_edge_gaps = [
        str(instance.get("id"))
        for instance in skill_instances
        if instance.get("id")
        and any(
            isinstance(residual, dict) and residual.get("requirement") == "required"
            for residual in _as_list(_as_dict(instance.get("relationships")).get("unpopulated_selective_relations"))
        )
    ]
    skill_selective_edge_gaps = [
        str(instance.get("id"))
        for instance in skill_instances
        if instance.get("id")
        and any(
            isinstance(residual, dict) and residual.get("requirement") == "selective"
            for residual in _as_list(_as_dict(instance.get("relationships")).get("unpopulated_selective_relations"))
        )
    ]
    skill_selective_relation_details = _skill_selective_residual_detail_rows(
        skill_instances
    )
    skill_selective_relation_counts_by_id = _relation_count_by_id(
        skill_selective_relation_details
    )
    skill_residual_candidate_details = _skill_residual_candidate_detail_rows(
        resolved,
        skill_selective_relation_details,
    )
    organ_selective_relation_details = [
        row
        for row in _as_list(organ_corpus.get("selective_residual_relation_details"))
        if isinstance(row, dict)
    ]
    organ_wires_to_fillability_details = _organ_wires_to_fillability_detail_rows(
        organ_instances,
        mechanism_instances,
        organ_selective_relation_details,
    )
    organ_wires_to_missing_source_declaration_details = [
        row
        for row in organ_wires_to_fillability_details
        if row.get("fillability_status")
        == "mechanism_upstream_wiring_missing_source_declaration"
    ]
    mechanism_selective_relation_details = [
        row
        for row in _as_list(mechanism_corpus.get("selective_residual_relation_details"))
        if isinstance(row, dict)
    ]
    mechanism_upstream_residual_fillability_details = (
        _mechanism_upstream_residual_fillability_detail_rows(
            resolved,
            mechanism_selective_relation_details,
        )
    )
    mechanism_upstream_missing_source_declaration_details = [
        row
        for row in mechanism_upstream_residual_fillability_details
        if row.get("fillability_status")
        == "capsule_dependency_upstream_target_missing_source_declaration"
    ]
    mechanism_upstream_unresolved_subject_details = [
        row
        for row in mechanism_upstream_residual_fillability_details
        if row.get("fillability_status")
        == "capsule_dependency_upstream_target_unresolved_subject"
    ]
    paper_module_selective_relation_details = [
        row
        for row in _as_list(
            paper_module_instance_corpus.get("selective_residual_relation_details")
        )
        if isinstance(row, dict)
    ]
    standard_required_edge_gaps = [
        str(instance.get("id"))
        for instance in standard_instances
        if instance.get("id") and _standard_required_gap_rows(instance)
    ]
    standard_required_relation_gap_details = _standard_required_relation_gap_detail_rows(
        standard_instances
    )
    standard_used_by_organ_unresolved_details = [
        row
        for row in _as_list(
            standard_corpus.get("used_by_organ_unresolved_details")
        )
        if isinstance(row, dict)
    ]
    standard_used_by_organ_admission_details = (
        _standard_used_by_organ_admission_detail_rows(
            standard_used_by_organ_unresolved_details,
            organ_instances,
        )
    )
    standard_used_by_organ_missing_accepted_target_details = [
        row
        for row in standard_used_by_organ_admission_details
        if row.get("admission_status") == "target_organ_not_accepted_current_authority"
    ]
    paper_corpus = _paper_module_corpus(resolved)
    mechanism_capsule_dependency_upstream_parity = (
        _mechanism_capsule_dependency_upstream_parity(resolved)
    )
    json_capsule_ids = {
        str(value).split(".", 1)[1]
        for value in _strings(paper_corpus.get("json_capsule_ids"))
        if "." in str(value)
    }
    markdown_slugs = {
        Path(rel).stem
        for rel in _strings(paper_corpus.get("markdown_files"))
    }
    all_health_instances = (
        instances
        + principle_instances
        + anti_principle_instances
        + concept_instances
        + mechanism_instances
        + organ_instances
        + paper_module_instances
        + skill_instances
        + standard_instances
    )
    evidence_walkability = _evidence_walkability_health(resolved, all_health_instances)
    health = {
        "schema_version": "microcosm_doctrine_lattice_health_v1",
        "status": "deficit",
        "authority_boundary": "generated_health_projection_not_doctrine_authority",
        "anti_claim": (
            "Health rows route gaps to residual pressure; they do not weaken doctrine or upgrade coverage."
        ),
        "source_refs": {
            "axiom_corpus": f"{AXIOM_INSTANCE_DIR_REL}/*.json",
            "principle_corpus": f"{PRINCIPLE_INSTANCE_DIR_REL}/*.json",
            "anti_principle_corpus": f"{ANTI_PRINCIPLE_INSTANCE_DIR_REL}/*.json",
            "concept_corpus": f"{CONCEPT_INSTANCE_DIR_REL}/*.json",
            "mechanism_corpus": f"{MECHANISM_INSTANCE_DIR_REL}/*.json",
            "organ_corpus": f"{ORGAN_INSTANCE_DIR_REL}/*.json",
            "paper_module_instances": f"{PAPER_MODULE_INSTANCE_DIR_REL}/*.json",
            "skill_instances": f"{SKILL_INSTANCE_DIR_REL}/*.json",
            "standard_instances": f"{STANDARD_INSTANCE_DIR_REL}/std_microcosm_*.json",
            "standards_registry": "core/standards_registry.json",
            "routing_registry": AXIOM_ROUTING_REL,
            "principles_legacy_markdown": PRINCIPLES_REL,
            "anti_principles_legacy_markdown": ANTI_PRINCIPLES_REL,
            "skills_legacy_markdown": f"{SKILL_INSTANCE_DIR_REL}/*.md",
            "concept_entry_packet": CONCEPT_ENTRY_PACKET_REL,
            "support_cover": "microcosm_core.validators.axiom_support_cover",
            "organ_atlas": "core/organ_atlas.json",
            "mechanism_registry": MECHANISM_REGISTRY_REL,
            "paper_module_capsules": PAPER_MODULE_CAPSULES_REL,
            "relation_registry": "core/doctrine_lattice_relations.json",
            "receipt_refs": "receipt_refs fields on mechanism, organ, paper_module, and standard instances",
        },
        "axioms": {
            "expected_count": corpus["expected_axiom_count"],
            "json_instance_count": corpus["json_instance_count"],
            "parity_status": corpus["parity_status"],
            "unwitnessed": [
                str(instance.get("id"))
                for instance in instances
                if not _strings(_as_dict(instance.get("relationships")).get("witness_organs"))
                and not _strings(_as_dict(instance.get("relationships")).get("witness_surfaces"))
            ],
            "not_obligation_piloted": sorted(set(corpus["instance_ids"]) - piloted_axioms),
            "support_frontier_count": len(support_frontiers),
        },
        "principles": {
            "known_count": len(all_principles),
            "legacy_markdown_count": len(routing_principles),
            "json_instance_count": principle_corpus["json_instance_count"],
            "expected_json_instance_count": principle_corpus["expected_principle_count"],
            "parity_status": principle_corpus["parity_status"],
            "obligation_level_supported_count": len(supported_principles),
            "unsupported_at_obligation_level": [
                principle for principle in all_principles if principle not in supported_principles
            ],
            "support_scope": "only principles grounded in piloted axiom obligations are computed",
            "unpopulated_governs_edge_count": len(principle_unpopulated_governance),
            "unpopulated_governs_edges": sorted(principle_unpopulated_governance, key=_id_sort_key),
        },
        "anti_principles": {
            "known_count": anti_principle_corpus["expected_anti_principle_count"],
            "json_instance_count": anti_principle_corpus["json_instance_count"],
            "parity_status": anti_principle_corpus["parity_status"],
            "guards_resolved_axiom_edge_count": sum(
                len(
                    [
                        edge
                        for edge in _as_list(_as_dict(instance.get("relationships")).get("edges"))
                        if isinstance(edge, dict)
                        and edge.get("relation_id") == "anti_principle.guards.axiom"
                        and edge.get("target_status") == "resolved_json_instance"
                    ]
                )
                for instance in anti_principle_instances
            ),
            "unpopulated_negates_edge_count": len(anti_principle_unpopulated_negates),
            "unpopulated_negates_edges": sorted(anti_principle_unpopulated_negates, key=_id_sort_key),
            "support_scope": "anti-principle guard edges resolve violated axioms; failed-principle negation binding remains residual until obligation-level mapping exists",
        },
        "concepts": {
            "known_count": concept_corpus["expected_concept_count"],
            "json_instance_count": concept_corpus["json_instance_count"],
            "parity_status": concept_corpus["parity_status"],
            "source_specimen_count": len(_concept_source_rows(resolved)),
            "unpopulated_selective_edge_count": len(concept_unpopulated_edges),
            "unpopulated_selective_edges": sorted(concept_unpopulated_edges, key=_id_sort_key),
            "support_scope": "concept specimen parity and typed selective neighbours are computed from source-named ids; unresolved or omitted selective edges remain residual pressure",
        },
        "organs": {
            "accepted_count": len(_atlas_organs(resolved)),
            "expected_json_instance_count": organ_corpus["expected_organ_count"],
            "json_instance_count": organ_corpus["json_instance_count"],
            "parity_status": organ_corpus["parity_status"],
            "required_edge_gap_count": len(organ_required_edge_gaps),
            "required_edge_gaps": sorted(organ_required_edge_gaps, key=_id_sort_key),
            "required_edge_gap_detail_count": len(organ_required_edge_gap_details),
            "required_edge_gap_details": organ_required_edge_gap_details,
            "unpopulated_selective_edge_count": len(organ_selective_edge_gaps),
            "unpopulated_selective_edges": sorted(organ_selective_edge_gaps, key=_id_sort_key),
            "unpopulated_selective_relation_count": len(organ_selective_relation_details),
            "unpopulated_selective_relation_counts_by_relation_id": _relation_count_by_id(
                organ_selective_relation_details
            ),
            **_selective_residual_group_counts(
                organ_selective_relation_details,
                instance_key="organ_id",
            ),
            "unpopulated_selective_relation_detail_count": len(organ_selective_relation_details),
            "unpopulated_selective_relation_details": organ_selective_relation_details,
            "wires_to_residual_fillability_detail_count": len(
                organ_wires_to_fillability_details
            ),
            "wires_to_residual_fillability_details": organ_wires_to_fillability_details,
            "wires_to_residual_counts_by_fillability_status": _count_rows_by_key(
                organ_wires_to_fillability_details,
                "fillability_status",
            ),
            "wires_to_mechanism_upstream_missing_source_declaration_count": len(
                organ_wires_to_missing_source_declaration_details
            ),
            "wires_to_mechanism_upstream_missing_source_declaration_details": (
                organ_wires_to_missing_source_declaration_details
            ),
            "residual_relation_counts_by_requirement": organ_corpus[
                "residual_relation_counts_by_requirement"
            ],
            "residual_relation_count": organ_corpus["residual_relation_count"],
            "unconstrained_by_axiom_count": len(organs_unconstrained),
            "unconstrained_by_axiom": organs_unconstrained,
            "support_scope": "organ required-edge and selective-neighbour residuals are typed from atlas/registry parity plus the relation registry; wires_to residual fillability is classified from mechanism upstream host-organ graph only; runtime correctness is not claimed",
        },
        "mechanisms": {
            "known_count": mechanism_corpus["expected_mechanism_count"],
            "json_instance_count": mechanism_corpus["json_instance_count"],
            "parity_status": mechanism_corpus["parity_status"],
            "without_code_loci_count": len(mechanisms_without_code),
            "without_code_loci": mechanisms_without_code,
            "planned_or_unresolved_code_loci_count": mechanism_corpus["planned_or_unresolved_code_loci_count"],
            "planned_or_unresolved_code_loci": mechanism_corpus["planned_or_unresolved_code_loci"],
            "unpopulated_selective_edge_count": len(mechanism_unpopulated_edges),
            "unpopulated_selective_edges": sorted(mechanism_unpopulated_edges, key=_id_sort_key),
            "unpopulated_selective_relation_count": len(mechanism_selective_relation_details),
            "unpopulated_selective_relation_counts_by_relation_id": _relation_count_by_id(
                mechanism_selective_relation_details
            ),
            **_selective_residual_group_counts(
                mechanism_selective_relation_details,
                instance_key="mechanism_id",
            ),
            "unpopulated_selective_relation_detail_count": len(mechanism_selective_relation_details),
            "unpopulated_selective_relation_details": mechanism_selective_relation_details,
            "upstream_residual_fillability_detail_count": len(
                mechanism_upstream_residual_fillability_details
            ),
            "upstream_residual_fillability_details": (
                mechanism_upstream_residual_fillability_details
            ),
            "upstream_residual_counts_by_fillability_status": _count_rows_by_key(
                mechanism_upstream_residual_fillability_details,
                "fillability_status",
            ),
            "upstream_capsule_dependency_missing_source_declaration_count": len(
                mechanism_upstream_missing_source_declaration_details
            ),
            "upstream_capsule_dependency_missing_source_declaration_details": (
                mechanism_upstream_missing_source_declaration_details
            ),
            "upstream_capsule_dependency_unresolved_subject_count": len(
                mechanism_upstream_unresolved_subject_details
            ),
            "upstream_capsule_dependency_unresolved_subject_details": (
                mechanism_upstream_unresolved_subject_details
            ),
            "residual_relation_counts_by_requirement": mechanism_corpus[
                "residual_relation_counts_by_requirement"
            ],
            "residual_relation_count": mechanism_corpus["residual_relation_count"],
            "capsule_dependency_upstream_parity": mechanism_capsule_dependency_upstream_parity,
            "support_scope": (
                "mechanism selective residuals are typed from source rows plus the relation registry; capsule depends_on evidence "
                "classifies upstream residual fillability and confirms dependency mechanisms as upstream_of their consumers, "
                "but is not a reverse-edge fill or runtime truth claim."
            ),
        },
        "paper_modules": {
            "markdown_file_count": paper_corpus["markdown_file_count"],
            "json_capsule_backed_count": paper_corpus["json_capsule_count"],
            "json_capsule_count": paper_corpus["json_capsule_count"],
            "without_json_capsule_count": paper_corpus["markdown_without_json_capsule_count"],
            "without_json_capsule": paper_corpus["markdown_without_json_capsule"],
            "expected_json_instance_count": paper_module_instance_corpus["expected_paper_module_count"],
            "json_instance_count": paper_module_instance_corpus["json_instance_count"],
            "json_instance_parity_status": paper_module_instance_corpus["parity_status"],
            "legacy_only_count": paper_module_instance_corpus["legacy_only_count"],
            "legacy_only_json_instance_count": paper_module_instance_corpus["legacy_only_count"],
            "required_subject_gap_count": len(paper_module_required_subject_gaps),
            "required_subject_gaps": sorted(paper_module_required_subject_gaps, key=_id_sort_key),
            "unpopulated_selective_edge_count": len(paper_module_selective_edge_gaps),
            "unpopulated_selective_edges": sorted(paper_module_selective_edge_gaps, key=_id_sort_key),
            "unpopulated_selective_relation_count": len(paper_module_selective_relation_details),
            "unpopulated_selective_relation_counts_by_relation_id": _relation_count_by_id(
                paper_module_selective_relation_details
            ),
            **_selective_residual_group_counts(
                paper_module_selective_relation_details,
                instance_key="paper_module_id",
            ),
            "unpopulated_selective_relation_detail_count": len(paper_module_selective_relation_details),
            "unpopulated_selective_relation_details": paper_module_selective_relation_details,
            "residual_relation_counts_by_requirement": paper_module_instance_corpus[
                "residual_relation_counts_by_requirement"
            ],
            "residual_relation_count": paper_module_instance_corpus[
                "residual_relation_count"
            ],
            "support_scope": "capsule-backed subjects and code loci are computed structural edges; required subject residuals and selective relation residuals remain typed separately, and legacy-only modules do not claim subject coverage",
        },
        "skills": {
            "legacy_markdown_count": len(_skill_source_rows(resolved)),
            "expected_json_instance_count": skill_corpus["expected_skill_count"],
            "json_instance_count": skill_corpus["json_instance_count"],
            "json_instance_parity_status": skill_corpus["parity_status"],
            "required_edge_gap_count": len(skill_required_edge_gaps),
            "required_edge_gaps": sorted(skill_required_edge_gaps, key=_id_sort_key),
            "unpopulated_selective_edge_count": len(skill_selective_edge_gaps),
            "unpopulated_selective_edges": sorted(skill_selective_edge_gaps, key=_id_sort_key),
            "unpopulated_selective_relation_count": len(skill_selective_relation_details),
            "unpopulated_selective_relation_counts_by_relation_id": skill_selective_relation_counts_by_id,
            "unpopulated_selective_relation_counts_by_instance_id": skill_corpus[
                "unpopulated_selective_relation_counts_by_instance_id"
            ],
            "unpopulated_selective_relation_counts_by_pressure_ref": skill_corpus[
                "unpopulated_selective_relation_counts_by_pressure_ref"
            ],
            "unpopulated_selective_relation_counts_by_authority_boundary": skill_corpus[
                "unpopulated_selective_relation_counts_by_authority_boundary"
            ],
            "unpopulated_selective_relation_counts_by_triad_role": skill_corpus[
                "unpopulated_selective_relation_counts_by_triad_role"
            ],
            "unpopulated_selective_relation_counts_by_operates_standard": skill_corpus[
                "unpopulated_selective_relation_counts_by_operates_standard"
            ],
            "unpopulated_selective_relation_counts_by_acts_on_kind": skill_corpus[
                "unpopulated_selective_relation_counts_by_acts_on_kind"
            ],
            "unpopulated_selective_relation_detail_count": len(skill_selective_relation_details),
            "unpopulated_selective_relation_details": skill_selective_relation_details,
            "residual_candidate_detail_count": len(skill_residual_candidate_details),
            "residual_candidate_details": skill_residual_candidate_details,
            "residual_candidate_counts_by_status": _count_rows_by_key(
                skill_residual_candidate_details,
                "candidate_status",
            ),
            "residual_candidate_counts_by_target_kind": _count_rows_by_key(
                skill_residual_candidate_details,
                "candidate_target_kind",
            ),
            "residual_candidate_counts_by_candidate_count": _count_rows_by_key(
                skill_residual_candidate_details,
                "candidate_count_bucket",
            ),
            "support_scope": "skill operated-standard and acted-on-kind edges are computed structural route mappings; selective mechanism/concept residuals are counted separately from affected skill nodes; acts_on_kind candidate matches are navigation pressure, not edge support; workflow correctness or agent uptake are not claimed",
        },
        "standards": {
            "registry_expected_count": standard_corpus["expected_standard_count"],
            "json_instance_count": standard_corpus["json_instance_count"],
            "json_instance_parity_status": standard_corpus["parity_status"],
            "legacy_or_draft_contract_count": standard_corpus["legacy_or_draft_contract_count"],
            "legacy_or_draft_contract_ids": standard_corpus["legacy_or_draft_contract_ids"],
            "legacy_or_draft_contract_detail_count": standard_corpus[
                "legacy_or_draft_contract_detail_count"
            ],
            "legacy_or_draft_contract_details": standard_corpus[
                "legacy_or_draft_contract_details"
            ],
            "legacy_or_draft_contract_counts_by_source_status": standard_corpus[
                "legacy_or_draft_contract_counts_by_source_status"
            ],
            "legacy_or_draft_contract_counts_by_source_schema_version": standard_corpus[
                "legacy_or_draft_contract_counts_by_source_schema_version"
            ],
            "legacy_or_draft_contract_counts_by_registry_status": standard_corpus[
                "legacy_or_draft_contract_counts_by_registry_status"
            ],
            "legacy_or_draft_contract_counts_by_projection_status": standard_corpus[
                "legacy_or_draft_contract_counts_by_projection_status"
            ],
            "activation_witness_gap_detail_count": standard_corpus[
                "activation_witness_gap_detail_count"
            ],
            "activation_witness_gap_details": standard_corpus[
                "activation_witness_gap_details"
            ],
            "activation_witness_gap_counts_by_gap_id": standard_corpus[
                "activation_witness_gap_counts_by_gap_id"
            ],
            "activation_witness_gap_counts_by_source_status": standard_corpus[
                "activation_witness_gap_counts_by_source_status"
            ],
            "activation_witness_gap_counts_by_source_schema_version": standard_corpus[
                "activation_witness_gap_counts_by_source_schema_version"
            ],
            "activation_witness_gap_counts_by_registry_status": standard_corpus[
                "activation_witness_gap_counts_by_registry_status"
            ],
            "activation_witness_gap_counts_by_validator_contract_required": standard_corpus[
                "activation_witness_gap_counts_by_validator_contract_required"
            ],
            "activation_witness_gap_counts_by_receipt_contract_required": standard_corpus[
                "activation_witness_gap_counts_by_receipt_contract_required"
            ],
            "required_edge_gap_count": len(standard_required_edge_gaps),
            "required_edge_gaps": sorted(standard_required_edge_gaps, key=_id_sort_key),
            "required_relation_gap_count": standard_corpus["required_relation_gap_count"],
            "required_relation_gap_instance_count": standard_corpus["required_relation_gap_instance_count"],
            "required_relation_gap_detail_count": len(standard_required_relation_gap_details),
            "required_relation_gap_details": standard_required_relation_gap_details,
            "governs_kind_resolved_edge_count": standard_corpus["governs_kind_resolved_edge_count"],
            "governs_kind_unresolved_edge_count": standard_corpus["governs_kind_unresolved_edge_count"],
            "governs_kind_missing_required_count": standard_corpus["governs_kind_missing_required_count"],
            "triad_skill_resolved_edge_count": standard_corpus["triad_skill_resolved_edge_count"],
            "triad_skill_planned_unresolved_edge_count": standard_corpus["triad_skill_planned_unresolved_edge_count"],
            "triad_skill_unresolved_edge_count": standard_corpus["triad_skill_unresolved_edge_count"],
            "triad_skill_missing_required_count": standard_corpus["triad_skill_missing_required_count"],
            "used_by_organ_edge_count": standard_corpus["used_by_organ_edge_count"],
            "used_by_organ_resolved_edge_count": standard_corpus["used_by_organ_resolved_edge_count"],
            "used_by_organ_unresolved_edge_count": standard_corpus["used_by_organ_unresolved_edge_count"],
            "used_by_organ_unresolved_detail_count": standard_corpus[
                "used_by_organ_unresolved_detail_count"
            ],
            "used_by_organ_unresolved_details": standard_used_by_organ_unresolved_details,
            "used_by_organ_unresolved_standard_count": standard_corpus[
                "used_by_organ_unresolved_standard_count"
            ],
            "used_by_organ_unresolved_standard_ids": standard_corpus[
                "used_by_organ_unresolved_standard_ids"
            ],
            "used_by_organ_unresolved_target_organ_count": standard_corpus[
                "used_by_organ_unresolved_target_organ_count"
            ],
            "used_by_organ_unresolved_target_organ_ids": standard_corpus[
                "used_by_organ_unresolved_target_organ_ids"
            ],
            "used_by_organ_unresolved_counts_by_target_organ_id": standard_corpus[
                "used_by_organ_unresolved_counts_by_target_organ_id"
            ],
            "used_by_organ_unresolved_counts_by_target_status": standard_corpus[
                "used_by_organ_unresolved_counts_by_target_status"
            ],
            "used_by_organ_unresolved_counts_by_source_status": standard_corpus[
                "used_by_organ_unresolved_counts_by_source_status"
            ],
            "used_by_organ_unresolved_counts_by_source_schema_version": standard_corpus[
                "used_by_organ_unresolved_counts_by_source_schema_version"
            ],
            "used_by_organ_unresolved_counts_by_registry_status": standard_corpus[
                "used_by_organ_unresolved_counts_by_registry_status"
            ],
            "used_by_organ_unresolved_counts_by_projection_status": standard_corpus[
                "used_by_organ_unresolved_counts_by_projection_status"
            ],
            "used_by_organ_typed_residual_count": standard_corpus[
                "used_by_organ_typed_residual_count"
            ],
            "used_by_organ_typed_residual_counts_by_gap_class": standard_corpus[
                "used_by_organ_typed_residual_counts_by_gap_class"
            ],
            "used_by_organ_typed_residual_counts_by_requirement": standard_corpus[
                "used_by_organ_typed_residual_counts_by_requirement"
            ],
            "used_by_organ_typed_residual_counts_by_disposition": standard_corpus[
                "used_by_organ_typed_residual_counts_by_disposition"
            ],
            "used_by_organ_admission_detail_count": len(
                standard_used_by_organ_admission_details
            ),
            "used_by_organ_admission_details": standard_used_by_organ_admission_details,
            "used_by_organ_admission_counts_by_admission_status": _count_rows_by_key(
                standard_used_by_organ_admission_details,
                "admission_status",
            ),
            "used_by_organ_admission_counts_by_target_status": _count_rows_by_key(
                standard_used_by_organ_admission_details,
                "target_status",
            ),
            "used_by_organ_admission_counts_by_contract_projection_status": (
                _count_rows_by_key(
                    standard_used_by_organ_admission_details,
                    "contract_projection_status",
                )
            ),
            "used_by_organ_missing_accepted_target_count": len(
                standard_used_by_organ_missing_accepted_target_details
            ),
            "used_by_organ_missing_accepted_target_details": (
                standard_used_by_organ_missing_accepted_target_details
            ),
            "unregistered_standard_file_count": len(standard_corpus["extra_json_ids"]),
            "unregistered_standard_file_ids": standard_corpus["extra_json_ids"],
            "missing_standard_id_file_count": len(standard_corpus["files_missing_standard_id"]),
            "missing_standard_id_files": standard_corpus["files_missing_standard_id"],
            "support_scope": "standard JSON files are inventory-backed contract nodes; governed-kind, triad-skill, source-declared used_by_organs, and target-organ admission status are computed separately from contract activation, organ acceptance, or runtime use claims",
        },
        "doctrine_kinds": evidence_walkability["doctrine_kinds"],
        "code_loci": evidence_walkability["code_loci"],
        "receipts": evidence_walkability["receipts"],
        "projections": {
            "axiom_json_parity": corpus["parity_status"],
            "principle_json_parity": principle_corpus["parity_status"],
            "anti_principle_json_parity": anti_principle_corpus["parity_status"],
            "concept_json_parity": concept_corpus["parity_status"],
            "mechanism_json_parity": mechanism_corpus["parity_status"],
            "organ_json_parity": organ_corpus["parity_status"],
            "paper_module_json_parity": paper_module_instance_corpus["parity_status"],
            "skill_json_parity": skill_corpus["parity_status"],
            "standard_json_parity": standard_corpus["parity_status"],
            "coverage_status": (projection or {}).get("status"),
            "coverage_population_status": (projection or {}).get("population_status"),
        },
        "residual_pressure": [],
    }
    health["residual_pressure"] = _lattice_health_residual_pressure_rows(health)
    if (
        corpus["parity_status"] == "pass"
        and principle_corpus["parity_status"] == "pass"
        and anti_principle_corpus["parity_status"] == "pass"
        and concept_corpus["parity_status"] == "pass"
        and mechanism_corpus["parity_status"] == "pass"
        and organ_corpus["parity_status"] == "pass"
        and paper_module_instance_corpus["parity_status"] == "pass"
        and skill_corpus["parity_status"] == "pass"
        and standard_corpus["parity_status"] == "pass"
        and not health["axioms"]["unwitnessed"]
        and not health["mechanisms"]["without_code_loci"]
        and not health["organs"]["required_edge_gaps"]
        and not health["paper_modules"]["required_subject_gaps"]
        and health["paper_modules"]["without_json_capsule_count"] == 0
        and not health["skills"]["required_edge_gaps"]
        and not health["standards"]["required_edge_gaps"]
        and health["standards"]["legacy_or_draft_contract_count"] == 0
        and not health["residual_pressure"]
    ):
        health["status"] = "partial_axiom_slice_clean"
    return health


def build_doctrine_projection(
    root: str | Path | None = None,
    *,
    generated_at: str | None = None,
    command: str = "python -m microcosm_core.doctrine_lattice --doctrine-projection",
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: build the full doctrine-lattice projection (nodes, justified edges, support calculus, coverage health) from source.
    - Guarantee: returns a projection dict whose status is 'pass' iff coverage status passes; nodes/edges are reproducibly derived and every edge carries source_ref+summary justification.
    - Fails: never raises; absent on-disk instances fall back to expected instances.
    - When-needed: --doctrine-projection / --write-doctrine-projection / projection validation.
    - Escalates-to: build_coverage_projection, render_doctrine_mermaid, validate_doctrine_projection.
    - Non-goal: the projection is generated and never source authority; passing does not authorize release or prove runtime correctness.
    """
    resolved = _root(root)
    coverage = build_coverage_projection(resolved, generated_at=generated_at, command=command)
    corpus = build_axiom_instance_corpus(resolved)
    principle_corpus = build_principle_instance_corpus(resolved)
    anti_principle_corpus = build_anti_principle_instance_corpus(resolved)
    concept_corpus = build_concept_instance_corpus(resolved)
    mechanism_corpus = build_mechanism_instance_corpus(resolved)
    organ_corpus = build_organ_instance_corpus(resolved)
    paper_module_instance_corpus = build_paper_module_instance_corpus(resolved)
    skill_corpus = build_skill_instance_corpus(resolved)
    standard_corpus = build_standard_instance_corpus(resolved)
    instances = list(load_axiom_instances(resolved).values())
    if not instances:
        instances = list(expected_axiom_instances(resolved).values())
    principle_instances = list(load_principle_instances(resolved).values())
    if not principle_instances:
        principle_instances = list(expected_principle_instances(resolved).values())
    anti_principle_instances = list(load_anti_principle_instances(resolved).values())
    if not anti_principle_instances:
        anti_principle_instances = list(expected_anti_principle_instances(resolved).values())
    concept_instances = list(load_concept_instances(resolved).values())
    if not concept_instances:
        concept_instances = list(expected_concept_instances(resolved).values())
    mechanism_instances = list(load_mechanism_instances(resolved).values())
    if not mechanism_instances:
        mechanism_instances = list(expected_mechanism_instances(resolved).values())
    organ_instances = list(load_organ_instances(resolved).values())
    if not organ_instances:
        organ_instances = list(expected_organ_instances(resolved).values())
    paper_module_instances = list(load_paper_module_instances(resolved).values())
    if not paper_module_instances:
        paper_module_instances = list(expected_paper_module_instances(resolved).values())
    skill_instances = list(load_skill_instances(resolved).values())
    if not skill_instances:
        skill_instances = list(expected_skill_instances(resolved).values())
    standard_instances = list(load_standard_instances(resolved).values())
    if not standard_instances:
        standard_instances = list(expected_standard_instances(resolved).values())
    all_instances = (
        instances
        + principle_instances
        + anti_principle_instances
        + concept_instances
        + mechanism_instances
        + organ_instances
        + paper_module_instances
        + skill_instances
        + standard_instances
    )
    support = evaluate_axiom_support_cover(resolved)
    support_frontiers = _as_dict(support.get("support_frontiers"))
    support_by_principle = {
        str(row.get("principle_id")): row
        for row in _as_list(support.get("principle_support_index"))
        if isinstance(row, dict) and row.get("principle_id")
    }
    node_rows: list[dict[str, Any]] = []
    edge_rows: list[dict[str, Any]] = []
    for instance in sorted(
        all_instances,
        key=lambda item: (str(item.get("kind") or ""), _id_sort_key(str(item.get("id") or ""))),
    ):
        instance_id = str(instance.get("id") or "")
        kind = str(instance.get("kind") or "")
        relationships = _as_dict(instance.get("relationships"))
        if kind == "axiom":
            frontier = _as_dict(support_frontiers.get(instance_id))
            strong_gate = _as_dict(_as_dict(support.get("strong_gate_summary")).get(instance_id))
            node = {
                "id": instance_id,
                "kind": "axiom",
                "title": instance.get("title"),
                "source_ref": _axiom_instance_rel(instance_id),
                "routing_source_ref": relationships.get("source_routing_row_ref"),
                "support_status": frontier.get("verdict", "not_obligation_piloted"),
                "claim_ceiling": strong_gate.get("strongest_allowed_claim", "not_computed"),
                "legacy_witness_strength": _as_dict(
                    _as_dict(instance.get("axiom_payload")).get("support_contract")
                ).get("legacy_routing_witness_strength"),
                "gap_count": len(_as_list(relationships.get("layer_debt"))),
                "residual_pressure_ref": (
                    "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
                    if frontier.get("verdict") != "bound_resolved_strength_uncomputable"
                    else None
                ),
            }
        elif kind == "principle":
            support_row = _as_dict(support_by_principle.get(instance_id))
            inherited = _as_dict(support_row.get("inherited_support_verdicts"))
            gap_count = len(_as_list(relationships.get("unpopulated_selective_relations")))
            node = {
                "id": instance_id,
                "kind": "principle",
                "title": instance.get("title"),
                "source_ref": _principle_instance_rel(instance_id),
                "legacy_source_ref": relationships.get("source_markdown_ref"),
                "support_status": (
                    "computed_from_piloted_grounding_axioms"
                    if support_row
                    else "not_obligation_piloted"
                ),
                "claim_ceiling": (
                    "bounded_by_inherited_axiom_support_verdicts"
                    if support_row
                    else "not_computed_no_piloted_grounding_axiom"
                ),
                "inherited_support_verdicts": inherited,
                "grounding_granularity": support_row.get("grounding_granularity"),
                "gap_count": gap_count,
                "residual_pressure_ref": (
                    "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
                    if gap_count or not support_row
                    else None
                ),
            }
        elif kind == "anti_principle":
            gap_count = len(_as_list(relationships.get("unpopulated_selective_relations")))
            node = {
                "id": instance_id,
                "kind": "anti_principle",
                "title": instance.get("title"),
                "source_ref": _anti_principle_instance_rel(instance_id),
                "legacy_source_ref": relationships.get("source_markdown_ref"),
                "support_status": "guard_edges_resolved_truth_status_not_support_claim",
                "claim_ceiling": "axiom_guard_relation_only_no_failed_principle_mapping",
                "gap_count": gap_count,
                "residual_pressure_ref": (
                    "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
                    if gap_count
                    else None
                ),
            }
        elif kind == "concept":
            edge_rows_for_instance = [
                edge
                for edge in _as_list(relationships.get("edges"))
                if isinstance(edge, dict)
            ]
            selective_residuals = [
                residual
                for residual in _as_list(relationships.get("unpopulated_selective_relations"))
                if isinstance(residual, dict)
            ]
            unresolved_edges = [
                edge
                for edge in edge_rows_for_instance
                if edge.get("relation_id")
                in {
                    "concept.implements_or_refines.principle",
                    "concept.instantiated_by.mechanism",
                    "concept.abides_by.axiom",
                }
                and edge.get("target_status") != "resolved_json_instance"
            ]
            gap_count = len(selective_residuals) + len(unresolved_edges)
            node = {
                "id": instance_id,
                "kind": "concept",
                "title": instance.get("title"),
                "source_ref": _concept_instance_rel(instance_id),
                "entry_packet_source_ref": relationships.get("source_specimen_ref"),
                "support_status": "specimen_route_boundary_computed_not_truth_support_claim",
                "claim_ceiling": "entry_packet_specimen_backed_concept_boundary_only",
                "resolved_edge_count": len(edge_rows_for_instance) - len(unresolved_edges),
                "unresolved_edge_count": len(unresolved_edges),
                "selective_edge_gap_count": len(selective_residuals),
                "selective_edge_gap_relation_ids": sorted(
                    {
                        str(residual.get("relation_id"))
                        for residual in selective_residuals
                        if residual.get("relation_id")
                    },
                    key=_id_sort_key,
                ),
                "gap_count": gap_count,
                "residual_pressure_ref": (
                    "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
                    if gap_count
                    else None
                ),
            }
        elif kind == "mechanism":
            edge_rows_for_instance = [
                edge
                for edge in _as_list(relationships.get("edges"))
                if isinstance(edge, dict)
            ]
            code_locus_edges = [
                edge
                for edge in edge_rows_for_instance
                if edge.get("relation_id") == "mechanism.grounded_in.code_locus"
            ]
            planned_or_unresolved_code = [
                edge
                for edge in code_locus_edges
                if edge.get("target_status") != "resolved_code_locus"
            ]
            gap_count = (
                len(_as_list(relationships.get("unpopulated_selective_relations")))
                + len(planned_or_unresolved_code)
            )
            node = {
                "id": instance_id,
                "kind": "mechanism",
                "title": instance.get("title"),
                "source_ref": _mechanism_instance_rel(instance_id),
                "registry_source_ref": relationships.get("source_registry_row_ref"),
                "support_status": (
                    "code_locus_grounded_from_registry"
                    if code_locus_edges and not planned_or_unresolved_code
                    else "required_code_locus_gap"
                ),
                "claim_ceiling": "registry_and_code_locus_grounded_operational_handle_not_runtime_correctness_or_release_proof",
                "resolved_code_locus_count": len(code_locus_edges) - len(planned_or_unresolved_code),
                "planned_or_unresolved_code_locus_count": len(planned_or_unresolved_code),
                "gap_count": gap_count,
                "residual_pressure_ref": (
                    "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
                    if gap_count
                    else None
                ),
            }
        elif kind == "organ":
            edge_rows_for_instance = [
                edge
                for edge in _as_list(relationships.get("edges"))
                if isinstance(edge, dict)
            ]
            required_residuals = [
                residual
                for residual in _as_list(relationships.get("unpopulated_selective_relations"))
                if isinstance(residual, dict) and residual.get("requirement") == "required"
            ]
            selective_residuals = [
                residual
                for residual in _as_list(relationships.get("unpopulated_selective_relations"))
                if isinstance(residual, dict) and residual.get("requirement") == "selective"
            ]
            planned_or_unresolved_required_edges = [
                edge
                for edge in edge_rows_for_instance
                if edge.get("relation_id")
                in {
                    "organ.explained_by.paper_module",
                    "organ.operates_through.mechanism",
                    "organ.implemented_by.code_locus",
                }
                and edge.get("target_status")
                not in {
                    "resolved_paper_module_ref",
                    "resolved_json_instance",
                    "resolved_code_locus",
                }
            ]
            gap_count = (
                len(required_residuals)
                + len(selective_residuals)
                + len(planned_or_unresolved_required_edges)
            )
            organ_gap_details = _organ_required_edge_gap_detail_rows([instance])
            organ_gap_detail = organ_gap_details[0] if organ_gap_details else {}
            node = {
                "id": instance_id,
                "kind": "organ",
                "title": instance.get("title"),
                "source_ref": _organ_instance_rel(instance_id),
                "atlas_source_ref": relationships.get("source_atlas_row_ref"),
                "registry_source_ref": relationships.get("source_registry_row_ref"),
                "support_status": (
                    "required_atlas_links_resolved_not_runtime_correctness_claim"
                    if not required_residuals and not planned_or_unresolved_required_edges
                    else "required_atlas_link_gap"
                ),
                "claim_ceiling": _as_dict(instance.get("organ_payload")).get("claim_ceiling"),
                "resolved_required_edge_count": len(
                    [
                        edge
                        for edge in edge_rows_for_instance
                        if edge.get("relation_id")
                        in {
                            "organ.explained_by.paper_module",
                            "organ.operates_through.mechanism",
                            "organ.implemented_by.code_locus",
                        }
                        and edge.get("target_status")
                        in {
                            "resolved_paper_module_ref",
                            "resolved_json_instance",
                            "resolved_code_locus",
                        }
                    ]
                ),
                "required_edge_gap_count": len(required_residuals) + len(planned_or_unresolved_required_edges),
                "required_edge_gap_relation_ids": organ_gap_detail.get(
                    "missing_required_relation_ids",
                    [],
                ),
                "law_binding_gap_relation_ids": organ_gap_detail.get(
                    "missing_selective_law_relation_ids",
                    [],
                ),
                "resolved_required_edge_relation_ids": organ_gap_detail.get(
                    "resolved_required_relation_ids",
                    [],
                ),
                "selective_edge_gap_count": len(selective_residuals),
                "selective_edge_gap_relation_ids": sorted(
                    {
                        str(residual.get("relation_id"))
                        for residual in selective_residuals
                        if residual.get("relation_id")
                    },
                    key=_id_sort_key,
                ),
                "gap_count": gap_count,
                "residual_pressure_ref": (
                    "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
                    if gap_count
                    else None
                ),
            }
        elif kind == "paper_module":
            edge_rows_for_instance = [
                edge
                for edge in _as_list(relationships.get("edges"))
                if isinstance(edge, dict)
            ]
            required_residuals = [
                residual
                for residual in _as_list(relationships.get("unpopulated_selective_relations"))
                if isinstance(residual, dict) and residual.get("requirement") == "required"
            ]
            selective_residuals = [
                residual
                for residual in _as_list(relationships.get("unpopulated_selective_relations"))
                if isinstance(residual, dict) and residual.get("requirement") == "selective"
            ]
            subject_edges = [
                edge
                for edge in edge_rows_for_instance
                if edge.get("relation_id") == "paper_module.explains.organ_or_mechanism"
            ]
            unresolved_subject_edges = [
                edge
                for edge in subject_edges
                if edge.get("target_status") != "resolved_json_instance"
            ]
            code_locus_edges = [
                edge
                for edge in edge_rows_for_instance
                if edge.get("relation_id") == "paper_module.cites.code_locus"
            ]
            unresolved_code_locus_edges = [
                edge
                for edge in code_locus_edges
                if edge.get("target_status") != "resolved_code_locus"
            ]
            payload = _as_dict(instance.get("paper_module_payload"))
            gap_count = (
                len(required_residuals)
                + len(selective_residuals)
                + len(unresolved_subject_edges)
                + len(unresolved_code_locus_edges)
            )
            node = {
                "id": instance_id,
                "kind": "paper_module",
                "title": instance.get("title"),
                "source_ref": _paper_module_instance_rel(instance_id),
                "legacy_source_ref": relationships.get("legacy_markdown_projection"),
                "capsule_source_ref": (
                    relationships.get("source_ref")
                    if relationships.get("source_authority") == "json_capsule"
                    else None
                ),
                "support_status": (
                    "json_capsule_subject_edges_resolved_not_runtime_correctness_claim"
                    if subject_edges and not unresolved_subject_edges and not required_residuals
                    else "required_subject_gap_or_legacy_only"
                ),
                "claim_ceiling": payload.get("authority_ceiling"),
                "resolved_subject_count": len(subject_edges) - len(unresolved_subject_edges),
                "required_subject_gap_count": len(required_residuals) + len(unresolved_subject_edges),
                "resolved_code_locus_count": len(code_locus_edges) - len(unresolved_code_locus_edges),
                "unresolved_code_locus_count": len(unresolved_code_locus_edges),
                "selective_edge_gap_count": len(selective_residuals),
                "gap_count": gap_count,
                "residual_pressure_ref": (
                    "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
                    if gap_count
                    else None
                ),
            }
        elif kind == "skill":
            edge_rows_for_instance = [
                edge
                for edge in _as_list(relationships.get("edges"))
                if isinstance(edge, dict)
            ]
            required_residuals = [
                residual
                for residual in _as_list(relationships.get("unpopulated_selective_relations"))
                if isinstance(residual, dict) and residual.get("requirement") == "required"
            ]
            selective_residuals = [
                residual
                for residual in _as_list(relationships.get("unpopulated_selective_relations"))
                if isinstance(residual, dict) and residual.get("requirement") == "selective"
            ]
            unresolved_required_edges = [
                edge
                for edge in edge_rows_for_instance
                if edge.get("relation_id")
                in {
                    "skill.operates.standard",
                    "skill.acts_on.doctrine_kind",
                }
                and edge.get("target_status")
                not in {
                    "resolved_standard_contract",
                    "resolved_doctrine_kind_contract",
                }
            ]
            gap_count = len(required_residuals) + len(selective_residuals) + len(unresolved_required_edges)
            node = {
                "id": instance_id,
                "kind": "skill",
                "title": instance.get("title"),
                "source_ref": _skill_instance_rel(instance_id),
                "legacy_source_ref": relationships.get("source_markdown_ref"),
                "triad_role": instance.get("triad_role"),
                "operates_standard": instance.get("operates_standard"),
                "acts_on_kind": instance.get("acts_on_kind"),
                "support_status": (
                    "required_skill_edges_resolved_not_workflow_correctness_claim"
                    if not required_residuals and not unresolved_required_edges
                    else "required_skill_relation_gap"
                ),
                "claim_ceiling": "skill_markdown_digest_and_route_mapping_only_not_agent_uptake_or_runtime_correctness",
                "required_edge_gap_count": len(required_residuals) + len(unresolved_required_edges),
                "selective_edge_gap_count": len(selective_residuals),
                "gap_count": gap_count,
                "residual_pressure_ref": (
                    "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
                    if gap_count
                    else None
                ),
            }
        elif kind == "standard":
            edge_rows_for_instance = [
                edge
                for edge in _as_list(relationships.get("edges"))
                if isinstance(edge, dict)
            ]
            required_residuals = [
                residual
                for residual in _as_list(relationships.get("unpopulated_selective_relations"))
                if isinstance(residual, dict) and residual.get("requirement") == "required"
            ]
            unresolved_required_edges = _standard_required_gap_rows(instance)
            unresolved_used_by_organ_edges = [
                edge
                for edge in edge_rows_for_instance
                if edge.get("relation_id") == "standard.used_by.organ"
                and edge.get("target_status") != "resolved_json_instance"
            ]
            standard_gap_details = _standard_required_relation_gap_detail_rows([instance])
            standard_gap_detail = standard_gap_details[0] if standard_gap_details else {}
            payload = _as_dict(instance.get("standard_payload"))
            gap_count = len(unresolved_required_edges) + len(unresolved_used_by_organ_edges)
            node = {
                "id": instance_id,
                "kind": "standard",
                "title": instance.get("title"),
                "source_ref": relationships.get("source_ref"),
                "registry_source_ref": relationships.get("registry_row_ref"),
                "governs_kind": instance.get("governs_kind"),
                "source_standard_schema_version": instance.get("source_standard_schema_version"),
                "source_standard_status": instance.get("source_standard_status"),
                "support_status": (
                    "standard_required_edges_resolved_not_contract_completeness_claim"
                    if not required_residuals
                    and not [
                        edge
                        for edge in edge_rows_for_instance
                        if edge.get("relation_id") == "standard.governs.doctrine_kind"
                        and edge.get("target_status") != "resolved_doctrine_kind_contract"
                    ]
                    and not [
                        edge
                        for edge in edge_rows_for_instance
                        if edge.get("relation_id") == "standard.owns_triad.skill"
                        and edge.get("target_status") != "resolved_json_instance"
                    ]
                    and not unresolved_used_by_organ_edges
                    else "required_standard_relation_gap"
                    if unresolved_required_edges
                    else "selective_standard_used_by_organ_resolution_gap"
                ),
                "claim_ceiling": "standard_json_contract_inventory_only_not_completeness_release_or_runtime_proof",
                "contract_projection_status": payload.get("contract_projection_status"),
                "required_edge_gap_count": len(unresolved_required_edges),
                "required_edge_gap_relation_ids": sorted(
                    set(standard_gap_detail.get("missing_required_relation_ids", []))
                    | set(standard_gap_detail.get("planned_required_relation_ids", []))
                    | set(standard_gap_detail.get("unresolved_required_relation_ids", [])),
                    key=_id_sort_key,
                ),
                "resolved_required_edge_relation_ids": standard_gap_detail.get(
                    "resolved_required_relation_ids",
                    [],
                ),
                "resolved_triad_skill_count": len(
                    [
                        edge
                        for edge in edge_rows_for_instance
                        if edge.get("relation_id") == "standard.owns_triad.skill"
                        and edge.get("target_status") == "resolved_json_instance"
                    ]
                ),
                "planned_or_unresolved_triad_skill_count": len(
                    [
                        edge
                        for edge in edge_rows_for_instance
                        if edge.get("relation_id") == "standard.owns_triad.skill"
                        and edge.get("target_status") != "resolved_json_instance"
                    ]
                ),
                "planned_unresolved_triad_skill_ids": standard_gap_detail.get(
                    "planned_unresolved_triad_skill_ids",
                    [],
                ),
                "planned_unresolved_triad_skill_roles": standard_gap_detail.get(
                    "planned_unresolved_triad_skill_roles",
                    [],
                ),
                "unresolved_triad_skill_ids": standard_gap_detail.get(
                    "unresolved_triad_skill_ids",
                    [],
                ),
                "used_by_organ_edge_count": len(
                    [
                        edge
                        for edge in edge_rows_for_instance
                        if edge.get("relation_id") == "standard.used_by.organ"
                    ]
                ),
                "unresolved_used_by_organ_count": len(unresolved_used_by_organ_edges),
                "unresolved_used_by_organ_ids": [
                    str(edge.get("target_id"))
                    for edge in unresolved_used_by_organ_edges
                    if edge.get("target_id")
                ],
                "gap_count": gap_count,
                "residual_pressure_ref": (
                    "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
                    if gap_count
                    or payload.get("contract_projection_status") != "active_v2_governed_json"
                    else None
                ),
            }
        else:
            node = {
                "id": instance_id,
                "kind": kind,
                "title": instance.get("title"),
                "source_ref": None,
                "support_status": "unknown_kind_not_computed",
                "claim_ceiling": "not_computed",
                "gap_count": 0,
                "residual_pressure_ref": "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f",
            }
        node.setdefault(
            "authority_boundary",
            _source_instance_node_authority_boundary(kind),
        )
        node_rows.append(node)
        for edge in _as_list(relationships.get("edges")):
            if not isinstance(edge, dict):
                continue
            row = _json(edge)
            row["source_kind"] = kind
            row["source_id"] = instance_id
            edge_rows.append(row)
    receipt_edge_rows = _receipt_evidence_edge_rows(all_instances, resolved)
    edge_rows.extend(receipt_edge_rows)
    node_rows.extend(_derived_doctrine_kind_node_rows(edge_rows))
    node_rows.extend(_derived_code_locus_node_rows(edge_rows, resolved))
    node_rows.extend(_derived_receipt_node_rows(receipt_edge_rows, resolved))
    health = build_lattice_health(resolved, projection=coverage)
    return {
        "_doc": (
            "Generated doctrine-lattice projection from governed JSON instances where present, "
            "legacy routing source where parity is still required, and computed support-cover output."
        ),
        "schema_version": "microcosm_doctrine_lattice_projection_v3",
        "projection_id": "public_microcosm_doctrine_lattice_projection",
        "authority_boundary": "generated_projection_not_source_authority",
        "anti_claim": (
            "This projection cannot upgrade source authority, certify strong support, authorize release, "
            "or count unresolved residual pressure as complete."
        ),
        "generation": {
            "generated_at": generated_at or _now(),
            "generated_by": "microcosm_core.doctrine_lattice.build_doctrine_projection",
            "command": command,
        },
        "source_refs": {
            "axiom_instances": f"{AXIOM_INSTANCE_DIR_REL}/*.json",
            "principle_instances": f"{PRINCIPLE_INSTANCE_DIR_REL}/*.json",
            "anti_principle_instances": f"{ANTI_PRINCIPLE_INSTANCE_DIR_REL}/*.json",
            "concept_instances": f"{CONCEPT_INSTANCE_DIR_REL}/*.json",
            "mechanism_instances": f"{MECHANISM_INSTANCE_DIR_REL}/*.json",
            "organ_instances": f"{ORGAN_INSTANCE_DIR_REL}/*.json",
            "paper_module_instances": f"{PAPER_MODULE_INSTANCE_DIR_REL}/*.json",
            "skill_instances": f"{SKILL_INSTANCE_DIR_REL}/*.json",
            "standard_instances": f"{STANDARD_INSTANCE_DIR_REL}/std_microcosm_*.json",
            "standards_registry": "core/standards_registry.json",
            "axiom_routing": AXIOM_ROUTING_REL,
            "principles_legacy_markdown": PRINCIPLES_REL,
            "anti_principles_legacy_markdown": ANTI_PRINCIPLES_REL,
            "skills_legacy_markdown": f"{SKILL_INSTANCE_DIR_REL}/*.md",
            "concept_entry_packet": CONCEPT_ENTRY_PACKET_REL,
            "mechanism_registry": MECHANISM_REGISTRY_REL,
            "organ_atlas": "core/organ_atlas.json",
            "organ_registry": "core/organ_registry.json",
            "paper_module_capsules": PAPER_MODULE_CAPSULES_REL,
            "coverage_projection": "core/doctrine_lattice_coverage.json",
            "support_cover": "microcosm_core.validators.axiom_support_cover",
            "relation_registry": "core/doctrine_lattice_relations.json",
        },
        "axiom_instance_corpus": corpus,
        "principle_instance_corpus": principle_corpus,
        "anti_principle_instance_corpus": anti_principle_corpus,
        "concept_instance_corpus": concept_corpus,
        "mechanism_instance_corpus": mechanism_corpus,
        "organ_instance_corpus": organ_corpus,
        "paper_module_instance_corpus": paper_module_instance_corpus,
        "skill_instance_corpus": skill_corpus,
        "standard_instance_corpus": standard_corpus,
        "nodes": node_rows,
        "edges": edge_rows,
        "support_truth_calculus": {
            "status": support.get("status"),
            "checker_id": support.get("checker_id"),
            "piloted_axioms": support.get("piloted_axioms"),
            "piloted_axiom_count": len(_strings(support.get("piloted_axioms"))),
            "candidate_axiom_pressure_count": len(_as_list(support.get("candidate_axiom_pressure"))),
            "anti_claims": support.get("anti_claims"),
        },
        "coverage_health": health,
        "projection_freshness": {
            "source_digests": source_file_digests(resolved),
            "freshness_status": "fresh_at_generation",
            "stale_source_behavior": "Regenerate projection and rerun --check after any source digest changes.",
        },
        "status": (
            "pass"
            if corpus["parity_status"] == "pass"
            and principle_corpus["parity_status"] == "pass"
            and anti_principle_corpus["parity_status"] == "pass"
            and concept_corpus["parity_status"] == "pass"
            and mechanism_corpus["parity_status"] == "pass"
            and organ_corpus["parity_status"] == "pass"
            and paper_module_instance_corpus["parity_status"] == "pass"
            and skill_corpus["parity_status"] == "pass"
            and standard_corpus["parity_status"] == "pass"
            and coverage["status"] == "pass"
            else "blocked"
        ),
    }


def write_doctrine_projection(
    root: str | Path | None = None,
    *,
    command: str = "python scripts/build_doctrine_projection.py --write",
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: write the doctrine projection JSON, mermaid graph, and health surfaces to disk and return the projection.
    - Guarantee: writes DOCTRINE_PROJECTION_REL, DOCTRINE_GRAPH_REL, and DOCTRINE_HEALTH_REL, then returns the built projection dict.
    - Fails: raises OSError if a target file cannot be written.
    - When-needed: --write-doctrine-projection regeneration.
    - Escalates-to: build_doctrine_projection, render_doctrine_mermaid.
    - Non-goal: writing generated surfaces does not flip source authority or authorize release.
    """
    resolved = _root(root)
    projection = build_doctrine_projection(
        resolved,
        command=command,
    )
    graph_instances = (
        list(load_axiom_instances(resolved).values())
        + list(load_principle_instances(resolved).values())
        + list(load_anti_principle_instances(resolved).values())
        + list(load_concept_instances(resolved).values())
        + list(load_mechanism_instances(resolved).values())
        + list(load_organ_instances(resolved).values())
        + list(load_paper_module_instances(resolved).values())
        + list(load_skill_instances(resolved).values())
        + list(load_standard_instances(resolved).values())
    )
    graph = render_doctrine_mermaid(graph_instances)
    health = _as_dict(projection.get("coverage_health"))
    outputs = {
        DOCTRINE_PROJECTION_REL: json.dumps(projection, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        DOCTRINE_GRAPH_REL: graph,
        DOCTRINE_HEALTH_REL: json.dumps(health, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    }
    for rel, text in outputs.items():
        target = resolved / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return projection


def validate_doctrine_projection(root: str | Path | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: check that on-disk doctrine projection/graph/health surfaces are reproducible from source and that every corpus passes.
    - Guarantee: returns {status: 'pass'|'blocked', errors[], per-kind corpus sub-results}; status 'pass' iff no corpus errors, no edge-justification/target gaps, and the three generated surfaces match expectation.
    - Fails: never raises (except a malformed on-disk projection file via read_json_strict); every other defect is an error row.
    - When-needed: --check-doctrine-projection before trusting the generated surfaces.
    - Escalates-to: build_doctrine_projection, validate_*_instance_corpus.
    - Non-goal: passing proves source-reproducibility of generated artifacts only, not release readiness or whole-system correctness.
    """
    resolved = _root(root)
    errors: list[dict[str, Any]] = []
    corpus_validation = validate_axiom_instance_corpus(resolved)
    principle_validation = validate_principle_instance_corpus(resolved)
    anti_principle_validation = validate_anti_principle_instance_corpus(resolved)
    concept_validation = validate_concept_instance_corpus(resolved)
    mechanism_validation = validate_mechanism_instance_corpus(resolved)
    organ_validation = validate_organ_instance_corpus(resolved)
    paper_module_validation = validate_paper_module_instance_corpus(resolved)
    skill_validation = validate_skill_instance_corpus(resolved)
    standard_validation = validate_standard_instance_corpus(resolved)
    if corpus_validation["status"] != "pass":
        errors.extend(_as_list(corpus_validation.get("errors")))
    if principle_validation["status"] != "pass":
        errors.extend(_as_list(principle_validation.get("errors")))
    if anti_principle_validation["status"] != "pass":
        errors.extend(_as_list(anti_principle_validation.get("errors")))
    if concept_validation["status"] != "pass":
        errors.extend(_as_list(concept_validation.get("errors")))
    if mechanism_validation["status"] != "pass":
        errors.extend(_as_list(mechanism_validation.get("errors")))
    if organ_validation["status"] != "pass":
        errors.extend(_as_list(organ_validation.get("errors")))
    if paper_module_validation["status"] != "pass":
        errors.extend(_as_list(paper_module_validation.get("errors")))
    if skill_validation["status"] != "pass":
        errors.extend(_as_list(skill_validation.get("errors")))
    if standard_validation["status"] != "pass":
        errors.extend(_as_list(standard_validation.get("errors")))
    expected_projection = build_doctrine_projection(
        resolved,
        generated_at="check",
        command="python scripts/build_doctrine_projection.py --write",
    )
    node_keys = {
        (str(node.get("kind") or ""), str(node.get("id") or ""))
        for node in _as_list(expected_projection.get("nodes"))
        if isinstance(node, dict)
    }
    for index, edge in enumerate(_as_list(expected_projection.get("edges"))):
        if not isinstance(edge, dict):
            continue
        justification = _as_dict(edge.get("justification"))
        if not justification.get("source_ref") or not justification.get("summary"):
            _add_error(
                errors,
                code="doctrine_projection_edge_missing_justification",
                path=f"{DOCTRINE_PROJECTION_REL}::edges[{index}]",
                message="Every generated edge must carry source_ref and summary justification.",
            )
        if edge.get("target_status") in {
            "resolved_json_instance",
            "resolved_doctrine_kind_contract",
        }:
            key = (str(edge.get("target_kind") or ""), str(edge.get("target_id") or ""))
            if key not in node_keys:
                _add_error(
                    errors,
                    code="doctrine_projection_edge_target_unresolved",
                    path=f"{DOCTRINE_PROJECTION_REL}::edges[{index}]",
                    message="Edge target marked resolved_json_instance does not exist in projection nodes.",
                    target_kind=key[0],
                    target_id=key[1],
                )
    projection_path = resolved / DOCTRINE_PROJECTION_REL
    if not projection_path.is_file():
        _add_error(
            errors,
            code="doctrine_projection_missing",
            path=DOCTRINE_PROJECTION_REL,
            message="Generated doctrine projection file is missing.",
        )
    else:
        actual = _as_dict(read_json_strict(projection_path))
        actual["generation"]["generated_at"] = "check"
        if actual != expected_projection:
            for key in (
                "axiom_instance_corpus",
                "principle_instance_corpus",
                "anti_principle_instance_corpus",
                "concept_instance_corpus",
                "mechanism_instance_corpus",
                "organ_instance_corpus",
                "paper_module_instance_corpus",
                "skill_instance_corpus",
                "standard_instance_corpus",
                "nodes",
                "edges",
                "support_truth_calculus",
                "coverage_health",
                "projection_freshness",
                "status",
            ):
                if actual.get(key) != expected_projection.get(key):
                    _add_error(
                        errors,
                        code="doctrine_projection_reproducibility_mismatch",
                        path=f"{DOCTRINE_PROJECTION_REL}::{key}",
                        message=f"Doctrine projection field {key} is not reproducible from source.",
                    )
    graph_path = resolved / DOCTRINE_GRAPH_REL
    expected_graph = render_doctrine_mermaid(
        list(load_axiom_instances(resolved).values())
        + list(load_principle_instances(resolved).values())
        + list(load_anti_principle_instances(resolved).values())
        + list(load_concept_instances(resolved).values())
        + list(load_mechanism_instances(resolved).values())
        + list(load_organ_instances(resolved).values())
        + list(load_paper_module_instances(resolved).values())
        + list(load_skill_instances(resolved).values())
        + list(load_standard_instances(resolved).values())
    )
    if not graph_path.is_file() or graph_path.read_text(encoding="utf-8") != expected_graph:
        _add_error(
            errors,
            code="doctrine_graph_projection_stale",
            path=DOCTRINE_GRAPH_REL,
            message="Doctrine mermaid graph is missing or stale.",
        )
    health_path = resolved / DOCTRINE_HEALTH_REL
    expected_health = _as_dict(expected_projection.get("coverage_health"))
    if not health_path.is_file() or _as_dict(read_json_strict(health_path)) != expected_health:
        _add_error(
            errors,
            code="doctrine_health_projection_stale",
            path=DOCTRINE_HEALTH_REL,
            message="Doctrine health projection is missing or stale.",
        )
    return {
        "schema_version": "microcosm_doctrine_projection_validation_v1",
        "status": "pass" if not errors else "blocked",
        "errors": errors,
        "axiom_corpus": corpus_validation,
        "principle_corpus": principle_validation,
        "anti_principle_corpus": anti_principle_validation,
        "concept_corpus": concept_validation,
        "mechanism_corpus": mechanism_validation,
        "organ_corpus": organ_validation,
        "paper_module_corpus": paper_module_validation,
        "skill_corpus": skill_validation,
        "standard_corpus": standard_validation,
    }


def _kind_coverage_rows(
    standards: dict[str, dict[str, Any]], relation_validation: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """
    - Teleology: summarize per-kind standard coverage (triads present, projection generated-only, lattice/unregistered edge counts).
    - Guarantee: returns {kind: row} with schema/status/source-format flags and edge counts for each standard.
    - Fails: never raises.
    """
    missing_relation_paths = {
        str(error.get("relation_key") or error.get("path") or "")
        for error in _as_list(relation_validation.get("errors"))
        if isinstance(error, dict) and error.get("code") == "lattice_edge_missing_relation_registry_row"
    }
    rows: dict[str, dict[str, Any]] = {}
    for kind, standard in standards.items():
        edges = _iter_standard_edges({kind: standard})
        rows[kind] = {
            "schema_version": standard.get("schema_version"),
            "status": standard.get("status"),
            "source_format": standard.get("source_format"),
            "skill_triad_present": all(key in _as_dict(standard.get("skills")) for key in SKILL_TRIAD),
            "validation_triad_present": all(key in _as_dict(standard.get("validation")) for key in VALIDATION_TRIAD),
            "projection_triad_generated": all(_projection_is_generated_only(_as_dict(standard.get("projections")).get(key)) for key in PROJECTION_TRIAD),
            "lattice_edge_count": len(edges),
            "unregistered_lattice_edge_count": len([edge for edge in edges if edge["relation_key"] in missing_relation_paths]),
        }
    return rows


def build_coverage_projection(
    root: str | Path | None = None,
    *,
    generated_at: str | None = None,
    command: str = "python -m microcosm_core.doctrine_lattice",
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: build the doctrine-lattice coverage projection (contract/relation/population/release statuses, per-kind and join health, deficit summary, next targets).
    - Guarantee: returns a coverage dict with an overall status and per-axis statuses, reproducibly derived from source plus a projection_freshness digest block.
    - Fails: never raises; defects surface as blocked sub-statuses and deficit counts rather than exceptions.
    - When-needed: --write / default build / status; the root coverage artifact other surfaces consume.
    - Escalates-to: validate_kind_standard_contracts, build_*_instance_corpus, validate_coverage_projection.
    - Non-goal: coverage is a generated projection and never source authority; a pass does not authorize publication or prove runtime correctness.
    """
    standards = load_kind_standards(root)
    relation_registry = load_relation_registry(root)
    relation_validation = validate_relation_registry(relation_registry, standards)
    standard_validation = validate_kind_standard_contracts(standards, relation_registry)
    accepted = _accepted_organs(root)
    atlas_rows = _atlas_organs(root)
    atlas_by_id = {str(row.get("organ_id") or ""): row for row in atlas_rows}
    mechanism_sources = _mechanism_sources(root)
    paper_capsule_rows = _paper_capsules(root)
    paper_capsules = {str(row.get("id") or ""): row for row in paper_capsule_rows if row.get("id")}
    registry_atlas_join = _registry_atlas_join_health(
        root,
        accepted,
        atlas_rows,
        mechanism_sources=mechanism_sources,
        paper_capsules=paper_capsules,
    )

    organ_ids = [str(row.get("organ_id") or "") for row in accepted if row.get("organ_id")]
    missing_paper = [oid for oid in organ_ids if not _has_declared_paper_module(atlas_by_id.get(oid, {}))]
    missing_mechanism = [oid for oid in organ_ids if not _has_mechanism_ref(atlas_by_id.get(oid, {}))]
    missing_code_loci = [oid for oid in organ_ids if not _has_code_loci(atlas_by_id.get(oid, {}))]
    paper_corpus = _paper_module_corpus(root)
    axiom_corpus = build_axiom_instance_corpus(root)
    principle_corpus = build_principle_instance_corpus(root)
    anti_principle_corpus = build_anti_principle_instance_corpus(root)
    concept_corpus = build_concept_instance_corpus(root)
    mechanism_corpus = build_mechanism_instance_corpus(root)
    organ_corpus = build_organ_instance_corpus(root)
    paper_module_instance_corpus = build_paper_module_instance_corpus(root)
    skill_corpus = build_skill_instance_corpus(root)
    standard_corpus = build_standard_instance_corpus(root)
    coverage_organ_instances = list(load_organ_instances(root).values()) or list(
        expected_organ_instances(root).values()
    )
    standard_used_by_organ_unresolved_details = [
        row
        for row in _as_list(
            standard_corpus.get("used_by_organ_unresolved_details")
        )
        if isinstance(row, dict)
    ]
    standard_used_by_organ_admission_details = (
        _standard_used_by_organ_admission_detail_rows(
            standard_used_by_organ_unresolved_details,
            coverage_organ_instances,
        )
    )
    standard_used_by_organ_missing_accepted_target_details = [
        row
        for row in standard_used_by_organ_admission_details
        if row.get("admission_status") == "target_organ_not_accepted_current_authority"
    ]
    public_guard = check_public_codex_leaks(root)
    per_kind = _kind_coverage_rows(standards, relation_validation)
    mechanism_capsule_dependency_upstream_parity = (
        _mechanism_capsule_dependency_upstream_parity(root)
    )

    priority_reasons = dict(PRIORITY_ORGAN_TARGETS)
    next_targets = []
    for organ_id, reason in PRIORITY_ORGAN_TARGETS:
        if organ_id in missing_paper or organ_id in missing_mechanism or organ_id in missing_code_loci:
            deficit_classes = []
            if organ_id in missing_paper:
                deficit_classes.append("missing_paper_module_ref")
            if organ_id in missing_mechanism:
                deficit_classes.append("missing_mechanism_ref")
            if organ_id in missing_code_loci:
                deficit_classes.append("missing_code_loci")
            next_targets.append(
                {
                    "organ_id": organ_id,
                    "deficit_classes": deficit_classes,
                    "reason": reason,
                    "suggested_first_action": "Populate required organ links from source evidence; unresolved mechanisms must remain planned and open a WorkItem/cap instead of counting as resolved.",
                }
            )

    contract_status = (
        "pass"
        if standard_validation["status"] == "pass"
        and relation_validation["status"] == "pass"
        and registry_atlas_join["status"] == "pass"
        and standard_corpus["parity_status"] == "pass"
        and public_guard["status"] == "pass"
        else "blocked"
    )
    population_status = (
        "complete"
        if not missing_paper and not missing_mechanism and not missing_code_loci
        else "deficit"
    )
    release_readiness_status = (
        "not_ready_population_deficit"
        if population_status != "complete"
        else "ready_for_separate_release_gate"
    )

    return {
        "_doc": "Generated doctrine lattice coverage projection. Source authority remains the JSON standards, relation registry, organ registry, organ atlas, and paper modules.",
        "schema_version": "microcosm_doctrine_lattice_projection_v2",
        "projection_id": "public_microcosm_doctrine_lattice_coverage",
        "authority_boundary": "generated_coverage_projection_not_doctrine_authority",
        "anti_claim": "Coverage counts are structural presence and validator health, not proof of correctness, completeness, release readiness, or permission to promote generated suggestions as doctrine.",
        "generation": {
            "generated_at": generated_at or _now(),
            "generated_by": "microcosm_core.doctrine_lattice.build_coverage_projection",
            "command": command,
        },
        "source_refs": {
            "relation_registry": "core/doctrine_lattice_relations.json",
            "organ_registry": "core/organ_registry.json",
            "organ_atlas": "core/organ_atlas.json",
            "mechanism_registry": MECHANISM_REGISTRY_REL,
            "paper_module_capsules": PAPER_MODULE_CAPSULES_REL,
            "axiom_instances": f"{AXIOM_INSTANCE_DIR_REL}/*.json",
            "principle_instances": f"{PRINCIPLE_INSTANCE_DIR_REL}/*.json",
            "anti_principle_instances": f"{ANTI_PRINCIPLE_INSTANCE_DIR_REL}/*.json",
            "concept_instances": f"{CONCEPT_INSTANCE_DIR_REL}/*.json",
            "mechanism_instances": f"{MECHANISM_INSTANCE_DIR_REL}/*.json",
            "organ_instances": f"{ORGAN_INSTANCE_DIR_REL}/*.json",
            "paper_module_instances": f"{PAPER_MODULE_INSTANCE_DIR_REL}/*.json",
            "skill_instances": f"{SKILL_INSTANCE_DIR_REL}/*.json",
            "standard_instances": f"{STANDARD_INSTANCE_DIR_REL}/std_microcosm_*.json",
            "axiom_routing": AXIOM_ROUTING_REL,
            "principles_legacy_markdown": PRINCIPLES_REL,
            "anti_principles_legacy_markdown": ANTI_PRINCIPLES_REL,
            "skills_legacy_markdown": f"{SKILL_INSTANCE_DIR_REL}/*.md",
            "standards_registry": "core/standards_registry.json",
            "concept_entry_packet": CONCEPT_ENTRY_PACKET_REL,
            "organ_atlas": "core/organ_atlas.json",
            "organ_registry": "core/organ_registry.json",
            "public_surface_manifest": PUBLIC_SURFACE_MANIFEST_REL,
            "standards": [_standard_rel(kind) for kind in KIND_STANDARD_IDS],
        },
        "contract_status": contract_status,
        "relation_registry_status": relation_validation["status"],
        "projection_reproducibility_status": "fresh_at_generation",
        "population_status": population_status,
        "release_readiness_status": release_readiness_status,
        "public_brand_guard_status": public_guard["status"],
        "organ_count": len(atlas_rows),
        "accepted_current_authority_organ_count": len(accepted),
        "organ_required_edge_coverage": {
            "with_paper_module_ref": len(organ_ids) - len(missing_paper),
            "without_paper_module_ref": missing_paper,
            "with_mechanism_ref": len(organ_ids) - len(missing_mechanism),
            "without_mechanism_ref": missing_mechanism,
            "with_code_loci": len(organ_ids) - len(missing_code_loci),
            "without_code_loci": missing_code_loci,
            "planned_mechanism_count": registry_atlas_join["planned_mechanism_count"],
            "resolved_mechanism_count": registry_atlas_join["resolved_mechanism_count"],
            "missing_mechanism_count": len(missing_mechanism),
            "planned_code_locus_count": registry_atlas_join["planned_code_locus_count"],
            "resolved_code_locus_count": registry_atlas_join["resolved_code_locus_count"],
        },
        "per_kind_coverage": per_kind,
        "relation_registry_health": relation_validation,
        "standard_contract_validation": standard_validation,
        "registry_atlas_join_health": registry_atlas_join,
        "paper_module_corpus": paper_corpus,
        "axiom_instance_corpus": axiom_corpus,
        "principle_instance_corpus": principle_corpus,
        "anti_principle_instance_corpus": anti_principle_corpus,
        "concept_instance_corpus": concept_corpus,
        "mechanism_instance_corpus": mechanism_corpus,
        "organ_instance_corpus": organ_corpus,
        "paper_module_instance_corpus": paper_module_instance_corpus,
        "skill_instance_corpus": skill_corpus,
        "standard_instance_corpus": standard_corpus,
        "mechanism_capsule_dependency_upstream_parity": (
            mechanism_capsule_dependency_upstream_parity
        ),
        "public_codex_leak_guard": public_guard,
        "deficit_summary": {
            "axiom_json_instance_count": axiom_corpus["json_instance_count"],
            "axiom_json_missing_count": len(axiom_corpus["missing_json_ids"]),
            "principle_json_instance_count": principle_corpus["json_instance_count"],
            "principle_json_missing_count": len(principle_corpus["missing_json_ids"]),
            "anti_principle_json_instance_count": anti_principle_corpus["json_instance_count"],
            "anti_principle_json_missing_count": len(anti_principle_corpus["missing_json_ids"]),
            "concept_json_instance_count": concept_corpus["json_instance_count"],
            "concept_json_missing_count": len(concept_corpus["missing_json_ids"]),
            "concept_unpopulated_selective_relation_count": concept_corpus["unpopulated_selective_relation_count"],
            "mechanism_json_instance_count": mechanism_corpus["json_instance_count"],
            "mechanism_json_missing_count": len(mechanism_corpus["missing_json_ids"]),
            "mechanism_without_code_loci_count": mechanism_corpus["without_code_loci_count"],
            "mechanism_planned_or_unresolved_code_loci_count": mechanism_corpus["planned_or_unresolved_code_loci_count"],
            "mechanism_unpopulated_selective_relation_count": mechanism_corpus["unpopulated_selective_relation_count"],
            "mechanism_capsule_dependency_upstream_missing_count": (
                mechanism_capsule_dependency_upstream_parity["missing_edge_count"]
            ),
            "mechanism_capsule_dependency_upstream_unresolved_dependency_count": (
                mechanism_capsule_dependency_upstream_parity["unresolved_dependency_count"]
            ),
            "organ_json_instance_count": organ_corpus["json_instance_count"],
            "organ_json_missing_count": len(organ_corpus["missing_json_ids"]),
            "organ_required_relation_gap_count": organ_corpus["required_relation_gap_count"],
            "organ_unpopulated_selective_relation_count": organ_corpus["unpopulated_selective_relation_count"],
            "paper_module_json_instance_count": paper_module_instance_corpus["json_instance_count"],
            "paper_module_json_missing_count": len(paper_module_instance_corpus["missing_json_ids"]),
            "paper_module_legacy_only_count": paper_module_instance_corpus["legacy_only_count"],
            "paper_module_required_subject_gap_count": paper_module_instance_corpus["required_subject_gap_count"],
            "paper_module_unpopulated_selective_relation_count": paper_module_instance_corpus["unpopulated_selective_relation_count"],
            "paper_module_without_json_capsule_count": paper_corpus["markdown_without_json_capsule_count"],
            "skill_json_instance_count": skill_corpus["json_instance_count"],
            "skill_json_missing_count": len(skill_corpus["missing_json_ids"]),
            "skill_required_relation_gap_count": skill_corpus["required_relation_gap_count"],
            "skill_unpopulated_selective_relation_count": skill_corpus["unpopulated_selective_relation_count"],
            "standard_json_instance_count": standard_corpus["json_instance_count"],
            "standard_json_missing_count": len(standard_corpus["missing_json_ids"]),
            "standard_legacy_or_draft_contract_count": standard_corpus["legacy_or_draft_contract_count"],
            "standard_required_relation_gap_count": standard_corpus["required_relation_gap_count"],
            "standard_required_relation_gap_instance_count": standard_corpus["required_relation_gap_instance_count"],
            "standard_governs_kind_resolved_edge_count": standard_corpus["governs_kind_resolved_edge_count"],
            "standard_governs_kind_unresolved_edge_count": standard_corpus["governs_kind_unresolved_edge_count"],
            "standard_governs_kind_missing_required_count": standard_corpus["governs_kind_missing_required_count"],
            "standard_triad_skill_resolved_edge_count": standard_corpus["triad_skill_resolved_edge_count"],
            "standard_triad_skill_planned_unresolved_edge_count": standard_corpus["triad_skill_planned_unresolved_edge_count"],
            "standard_triad_skill_unresolved_edge_count": standard_corpus["triad_skill_unresolved_edge_count"],
            "standard_triad_skill_missing_required_count": standard_corpus["triad_skill_missing_required_count"],
            "standard_used_by_organ_edge_count": standard_corpus["used_by_organ_edge_count"],
            "standard_used_by_organ_resolved_edge_count": standard_corpus["used_by_organ_resolved_edge_count"],
            "standard_used_by_organ_unresolved_edge_count": standard_corpus["used_by_organ_unresolved_edge_count"],
            "standard_used_by_organ_missing_accepted_target_count": len(
                standard_used_by_organ_missing_accepted_target_details
            ),
            "standard_unregistered_file_count": len(standard_corpus["extra_json_ids"]),
            "standard_missing_standard_id_file_count": len(standard_corpus["files_missing_standard_id"]),
            "organs_missing_paper_module_ref": len(missing_paper),
            "organs_missing_mechanism_ref": len(missing_mechanism),
            "organs_missing_code_loci": len(missing_code_loci),
            "kinds_missing_skill_triad": len([kind for kind, row in per_kind.items() if not row["skill_triad_present"]]),
            "kinds_still_v1_draft": [kind for kind, row in per_kind.items() if row["schema_version"] != "public_microcosm_standard_v2" or row["status"] != "active"],
            "meta_standard_v1": standards["standard"].get("schema_version") != "public_microcosm_standard_v2",
            "unregistered_lattice_edges": len(_as_list(relation_validation.get("errors"))),
            "public_codex_brand_leak_count": public_guard["brand_leak_count"],
            "registry_atlas_join_error_count": len(_as_list(registry_atlas_join.get("errors"))),
        },
        "next_population_targets": next_targets,
        "continuous_population_seat": {
            "cycle": [
                "read coverage projection",
                "classify deficit",
                "inspect source authority",
                "land one reversible patch or open WorkItem/cap",
                "regenerate projection",
                "run validators",
                "attach receipt",
            ],
            "must_not": [
                "mint axioms to satisfy an organ",
                "mint principles to satisfy an organ",
                "promote candidate doctrine into public source",
                "count planned mechanisms as resolved",
                "treat generated projections as source authority",
            ],
        },
        "projection_freshness": {
            "source_digests": source_file_digests(root),
            "freshness_status": "fresh_at_generation",
            "stale_source_behavior": "If any source digest changes, regenerate before acting on coverage counts.",
        },
        "status": contract_status,
    }


def validate_coverage_projection(
    projection: dict[str, Any],
    root: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: check that an on-disk coverage projection is reproducible from current source.
    - Guarantee: returns {status: 'pass'|'blocked', errors[]}; status 'pass' iff the projection equals the freshly built one (digest and per-field mismatches are itemized).
    - Fails: never raises; every divergence from the expected projection is an error row.
    - When-needed: --check coverage before trusting the written artifact.
    - Escalates-to: build_coverage_projection.
    - Non-goal: passing proves source-reproducibility only, not release readiness or whole-system correctness.
    """
    errors: list[dict[str, Any]] = []
    generated_at = _as_dict(projection.get("generation")).get("generated_at") or "check"
    expected = build_coverage_projection(root, generated_at=str(generated_at))
    if projection != expected:
        expected_digests = _as_dict(_as_dict(expected.get("projection_freshness")).get("source_digests"))
        actual_digests = _as_dict(_as_dict(projection.get("projection_freshness")).get("source_digests"))
        if expected_digests != actual_digests:
            _add_error(errors, code="coverage_projection_source_digest_mismatch", path="projection_freshness.source_digests", message="Coverage source digests do not match current sources.")
        for key in (
            "source_refs",
            "contract_status",
            "relation_registry_status",
            "projection_reproducibility_status",
            "population_status",
            "release_readiness_status",
            "public_brand_guard_status",
            "organ_required_edge_coverage",
            "per_kind_coverage",
            "relation_registry_health",
            "registry_atlas_join_health",
            "paper_module_corpus",
            "axiom_instance_corpus",
            "principle_instance_corpus",
            "anti_principle_instance_corpus",
            "concept_instance_corpus",
            "mechanism_instance_corpus",
            "organ_instance_corpus",
            "paper_module_instance_corpus",
            "skill_instance_corpus",
            "standard_instance_corpus",
            "mechanism_capsule_dependency_upstream_parity",
            "deficit_summary",
            "next_population_targets",
            "public_codex_leak_guard",
        ):
            if projection.get(key) != expected.get(key):
                _add_error(errors, code="coverage_projection_reproducibility_mismatch", path=key, message=f"Coverage field {key} is not reproducible from source.")
    return {
        "schema_version": "microcosm_doctrine_lattice_projection_validation_v1",
        "status": "pass" if not errors else "blocked",
        "errors": errors,
    }


def write_coverage_projection(
    root: str | Path | None = None,
    out: str | Path | None = None,
    *,
    generated_at: str | None = None,
    command: str = "python -m microcosm_core.doctrine_lattice --write",
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: write the coverage projection to disk and return it.
    - Guarantee: writes the built coverage projection (sorted-keys JSON) to out or core/doctrine_lattice_coverage.json and returns it.
    - Fails: raises OSError if the target file cannot be written.
    - When-needed: --write coverage regeneration.
    - Escalates-to: build_coverage_projection.
    - Non-goal: writing the projection does not flip source authority or authorize release.
    """
    resolved = Path(root).resolve() if root is not None else microcosm_root()
    projection = build_coverage_projection(resolved, generated_at=generated_at, command=command)
    target = Path(out).resolve() if out is not None else resolved / "core/doctrine_lattice_coverage.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(projection, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return projection


def _status_card(projection: dict[str, Any]) -> dict[str, Any]:
    """
    - Teleology: compress a coverage projection into a compact status card (axis statuses, deficit summary, top targets).
    - Guarantee: returns a status-card dict with the axis statuses, selected deficit counts, and the first three next_population_targets.
    - Fails: never raises; absent fields render as None.
    """
    deficit = _as_dict(projection.get("deficit_summary"))
    targets = _as_list(projection.get("next_population_targets"))
    return {
        "schema_version": "microcosm_doctrine_lattice_status_card_v1",
        "status": projection.get("status"),
        "contract_status": projection.get("contract_status"),
        "relation_registry_status": projection.get("relation_registry_status"),
        "projection_reproducibility_status": projection.get("projection_reproducibility_status"),
        "population_status": projection.get("population_status"),
        "release_readiness_status": projection.get("release_readiness_status"),
        "public_brand_guard_status": projection.get("public_brand_guard_status"),
        "deficit_summary": {
            "concept_json_missing_count": deficit.get("concept_json_missing_count"),
            "concept_unpopulated_selective_relation_count": deficit.get("concept_unpopulated_selective_relation_count"),
            "mechanism_json_missing_count": deficit.get("mechanism_json_missing_count"),
            "mechanism_without_code_loci_count": deficit.get("mechanism_without_code_loci_count"),
            "mechanism_unpopulated_selective_relation_count": deficit.get("mechanism_unpopulated_selective_relation_count"),
            "organ_json_missing_count": deficit.get("organ_json_missing_count"),
            "organ_required_relation_gap_count": deficit.get("organ_required_relation_gap_count"),
            "organ_unpopulated_selective_relation_count": deficit.get("organ_unpopulated_selective_relation_count"),
            "paper_module_json_missing_count": deficit.get("paper_module_json_missing_count"),
            "paper_module_legacy_only_count": deficit.get("paper_module_legacy_only_count"),
            "paper_module_required_subject_gap_count": deficit.get("paper_module_required_subject_gap_count"),
            "paper_module_unpopulated_selective_relation_count": deficit.get("paper_module_unpopulated_selective_relation_count"),
            "paper_module_without_json_capsule_count": deficit.get("paper_module_without_json_capsule_count"),
            "skill_json_missing_count": deficit.get("skill_json_missing_count"),
            "skill_required_relation_gap_count": deficit.get("skill_required_relation_gap_count"),
            "skill_unpopulated_selective_relation_count": deficit.get("skill_unpopulated_selective_relation_count"),
            "standard_json_missing_count": deficit.get("standard_json_missing_count"),
            "standard_legacy_or_draft_contract_count": deficit.get("standard_legacy_or_draft_contract_count"),
            "standard_required_relation_gap_count": deficit.get("standard_required_relation_gap_count"),
            "standard_governs_kind_resolved_edge_count": deficit.get("standard_governs_kind_resolved_edge_count"),
            "standard_triad_skill_resolved_edge_count": deficit.get("standard_triad_skill_resolved_edge_count"),
            "standard_triad_skill_planned_unresolved_edge_count": deficit.get("standard_triad_skill_planned_unresolved_edge_count"),
            "standard_triad_skill_missing_required_count": deficit.get("standard_triad_skill_missing_required_count"),
            "standard_used_by_organ_unresolved_edge_count": deficit.get("standard_used_by_organ_unresolved_edge_count"),
            "standard_unregistered_file_count": deficit.get("standard_unregistered_file_count"),
            "organs_missing_paper_module_ref": deficit.get("organs_missing_paper_module_ref"),
            "organs_missing_mechanism_ref": deficit.get("organs_missing_mechanism_ref"),
            "organs_missing_code_loci": deficit.get("organs_missing_code_loci"),
            "unregistered_lattice_edges": deficit.get("unregistered_lattice_edges"),
            "registry_atlas_join_error_count": deficit.get("registry_atlas_join_error_count"),
        },
        "next_population_targets": targets[:3],
    }


def build_entry_card(
    root: str | Path | None = None,
    *,
    projection: dict[str, Any] | None = None,
    generated_at: str | None = None,
    command: str = "python -m microcosm_core.doctrine_lattice --entry-card",
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: build the Microcosm-local agent entry card routing a cold agent to current doctrine-lattice evidence.
    - Guarantee: returns an entry-card dict with status chips, an agent band ladder, current counts, fake-green guards, and a re-entry condition; status mirrors the coverage projection status.
    - Fails: never raises; it builds its own coverage projection when none is passed.
    - When-needed: --entry-card / --write-entry-card; the cold-start surface for a Microcosm agent.
    - Escalates-to: build_coverage_projection, build_lattice_health, validate_entry_card.
    - Non-goal: the card routes to evidence only; it does not make generated counts source doctrine, count planned rows as resolved, authorize publication, or replace coverage validation.
    """
    if projection is None:
        projection = build_coverage_projection(root, generated_at=generated_at, command=command)
    coverage = _as_dict(projection.get("organ_required_edge_coverage"))
    deficit = _as_dict(projection.get("deficit_summary"))
    axiom_corpus = _as_dict(projection.get("axiom_instance_corpus"))
    principle_corpus = _as_dict(projection.get("principle_instance_corpus"))
    anti_principle_corpus = _as_dict(projection.get("anti_principle_instance_corpus"))
    concept_corpus = _as_dict(projection.get("concept_instance_corpus"))
    mechanism_corpus = _as_dict(projection.get("mechanism_instance_corpus"))
    mechanism_capsule_dependency_upstream_parity = _as_dict(
        projection.get("mechanism_capsule_dependency_upstream_parity")
    )
    organ_corpus = _as_dict(projection.get("organ_instance_corpus"))
    paper_module_corpus = _as_dict(projection.get("paper_module_instance_corpus"))
    skill_corpus = _as_dict(projection.get("skill_instance_corpus"))
    standard_corpus = _as_dict(projection.get("standard_instance_corpus"))
    health = build_lattice_health(root, projection=projection)
    doctrine_kind_health = _as_dict(health.get("doctrine_kinds"))
    code_loci_health = _as_dict(health.get("code_loci"))
    receipts_health = _as_dict(health.get("receipts"))
    status_card = _status_card(projection)
    generated_at_value = generated_at or _as_dict(projection.get("generation")).get("generated_at") or _now()
    next_targets = _as_list(projection.get("next_population_targets"))
    return {
        "_doc": (
            "Generated Microcosm-local agent entry card for doctrine-lattice population. "
            "Source authority remains the JSON standards, registries, organ atlas, paper "
            "capsules, and coverage builder."
        ),
        "schema_version": "microcosm_doctrine_lattice_entry_card_v1",
        "card_id": "microcosm_doctrine_lattice_agent_entry",
        "surface_id": "microcosm_doctrine_lattice",
        "entry_scope": "microcosm_substrate_local_agent_entry_only",
        "agent_entry_definition": (
            "Microcosm agent entry means this public substrate's local entry/status "
            "surface, not the private macro-system bootstrap or provider-specific "
            "AGENTS/CODEX entry."
        ),
        "authority_boundary": (
            "generated_entry_card_not_source_authority_release_authority_proof_authority_"
            "doctrine_promotion_authority_or_macro_bootstrap"
        ),
        "anti_claim": (
            "This card routes a cold Microcosm agent to current doctrine-lattice evidence. "
            "It does not make generated counts source doctrine, count planned rows as "
            "resolved, authorize publication, or replace coverage validation."
        ),
        "generation": {
            "generated_at": generated_at_value,
            "generated_by": "microcosm_core.doctrine_lattice.build_entry_card",
            "command": command,
            "coverage_projection_digest": _sha256_json(projection),
        },
        "source_refs": {
            "coverage_projection": "core/doctrine_lattice_coverage.json",
            "doctrine_projection": DOCTRINE_PROJECTION_REL,
            "doctrine_health": DOCTRINE_HEALTH_REL,
            "axiom_instances": f"{AXIOM_INSTANCE_DIR_REL}/*.json",
            "principle_instances": f"{PRINCIPLE_INSTANCE_DIR_REL}/*.json",
            "anti_principle_instances": f"{ANTI_PRINCIPLE_INSTANCE_DIR_REL}/*.json",
            "concept_instances": f"{CONCEPT_INSTANCE_DIR_REL}/*.json",
            "mechanism_instances": f"{MECHANISM_INSTANCE_DIR_REL}/*.json",
            "organ_instances": f"{ORGAN_INSTANCE_DIR_REL}/*.json",
            "paper_module_instances": f"{PAPER_MODULE_INSTANCE_DIR_REL}/*.json",
            "skill_instances": f"{SKILL_INSTANCE_DIR_REL}/*.json",
            "standard_instances": f"{STANDARD_INSTANCE_DIR_REL}/std_microcosm_*.json",
            "standards_registry": "core/standards_registry.json",
            "axiom_routing": AXIOM_ROUTING_REL,
            "principles_legacy_markdown": PRINCIPLES_REL,
            "anti_principles_legacy_markdown": ANTI_PRINCIPLES_REL,
            "skills_legacy_markdown": f"{SKILL_INSTANCE_DIR_REL}/*.md",
            "concept_entry_packet": CONCEPT_ENTRY_PACKET_REL,
            "entry_route": "atlas/entry_packet.json::doctrine_lattice_route",
            "relation_registry": "core/doctrine_lattice_relations.json",
            "organ_registry": "core/organ_registry.json",
            "organ_atlas": "core/organ_atlas.json",
            "mechanism_registry": MECHANISM_REGISTRY_REL,
            "paper_module_capsules": PAPER_MODULE_CAPSULES_REL,
            "public_surface_manifest": PUBLIC_SURFACE_MANIFEST_REL,
        },
        "status_card": status_card,
        "status_chips": [
            {"chip_id": "contract", "status": projection.get("contract_status")},
            {"chip_id": "population", "status": projection.get("population_status")},
            {"chip_id": "release_readiness", "status": projection.get("release_readiness_status")},
            {"chip_id": "public_brand_guard", "status": projection.get("public_brand_guard_status")},
        ],
        "agent_band_ladder": [
            {
                "band": "atom",
                "use": "Confirm the Microcosm-local scope and current pass/fail chips.",
                "command": "microcosm doctrine-lattice entry-card --root .",
            },
            {
                "band": "flag",
                "use": "Read the compact status card before touching source rows.",
                "command": "microcosm doctrine-lattice status --root .",
            },
            {
                "band": "card",
                "use": "Open generated coverage and the top population targets.",
                "command": "microcosm doctrine-lattice write-entry-card --root .",
            },
            {
                "band": "context",
                "use": "Validate coverage reproducibility from current source.",
                "command": "microcosm doctrine-lattice check --root .",
            },
            {
                "band": "evidence",
                "use": "Inspect source registries and copied capsule receipts named by the card.",
                "refs": [
                    "core/doctrine_lattice_coverage.json",
                    "core/mechanism_sources.json",
                    "core/paper_module_capsules.json",
                ],
            },
        ],
        "current_counts": {
            "accepted_current_authority_organ_count": projection.get("accepted_current_authority_organ_count"),
            "with_paper_module_ref": coverage.get("with_paper_module_ref"),
            "organs_missing_paper_module_ref": deficit.get("organs_missing_paper_module_ref"),
            "with_mechanism_ref": coverage.get("with_mechanism_ref"),
            "organs_missing_mechanism_ref": deficit.get("organs_missing_mechanism_ref"),
            "resolved_mechanism_count": coverage.get("resolved_mechanism_count"),
            "planned_mechanism_count": coverage.get("planned_mechanism_count"),
            "with_code_loci": coverage.get("with_code_loci"),
            "organs_missing_code_loci": deficit.get("organs_missing_code_loci"),
            "resolved_code_locus_count": coverage.get("resolved_code_locus_count"),
            "planned_code_locus_count": coverage.get("planned_code_locus_count"),
            "expected_axiom_count": axiom_corpus.get("expected_axiom_count"),
            "axiom_json_instance_count": axiom_corpus.get("json_instance_count"),
            "axiom_json_missing_count": len(_as_list(axiom_corpus.get("missing_json_ids"))),
            "axiom_json_parity_status": axiom_corpus.get("parity_status"),
            "expected_principle_count": principle_corpus.get("expected_principle_count"),
            "principle_json_instance_count": principle_corpus.get("json_instance_count"),
            "principle_json_missing_count": len(_as_list(principle_corpus.get("missing_json_ids"))),
            "principle_json_parity_status": principle_corpus.get("parity_status"),
            "expected_anti_principle_count": anti_principle_corpus.get("expected_anti_principle_count"),
            "anti_principle_json_instance_count": anti_principle_corpus.get("json_instance_count"),
            "anti_principle_json_missing_count": len(_as_list(anti_principle_corpus.get("missing_json_ids"))),
            "anti_principle_json_parity_status": anti_principle_corpus.get("parity_status"),
            "expected_concept_count": concept_corpus.get("expected_concept_count"),
            "concept_json_instance_count": concept_corpus.get("json_instance_count"),
            "concept_json_missing_count": len(_as_list(concept_corpus.get("missing_json_ids"))),
            "concept_json_parity_status": concept_corpus.get("parity_status"),
            "concept_unpopulated_selective_relation_count": concept_corpus.get("unpopulated_selective_relation_count"),
            "expected_mechanism_count": mechanism_corpus.get("expected_mechanism_count"),
            "mechanism_json_instance_count": mechanism_corpus.get("json_instance_count"),
            "mechanism_json_missing_count": len(_as_list(mechanism_corpus.get("missing_json_ids"))),
            "mechanism_json_parity_status": mechanism_corpus.get("parity_status"),
            "mechanism_without_code_loci_count": mechanism_corpus.get("without_code_loci_count"),
            "mechanism_unpopulated_selective_relation_count": mechanism_corpus.get("unpopulated_selective_relation_count"),
            "mechanism_capsule_dependency_upstream_missing_count": (
                mechanism_capsule_dependency_upstream_parity.get("missing_edge_count")
            ),
            "mechanism_capsule_dependency_upstream_covered_edge_count": (
                mechanism_capsule_dependency_upstream_parity.get("covered_edge_count")
            ),
            "mechanism_capsule_dependency_upstream_unresolved_dependency_count": (
                mechanism_capsule_dependency_upstream_parity.get("unresolved_dependency_count")
            ),
            "expected_organ_count": organ_corpus.get("expected_organ_count"),
            "organ_json_instance_count": organ_corpus.get("json_instance_count"),
            "organ_json_missing_count": len(_as_list(organ_corpus.get("missing_json_ids"))),
            "organ_json_parity_status": organ_corpus.get("parity_status"),
            "organ_required_relation_gap_count": organ_corpus.get("required_relation_gap_count"),
            "organ_unpopulated_selective_relation_count": organ_corpus.get("unpopulated_selective_relation_count"),
            "expected_paper_module_count": paper_module_corpus.get("expected_paper_module_count"),
            "paper_module_json_instance_count": paper_module_corpus.get("json_instance_count"),
            "paper_module_json_missing_count": len(_as_list(paper_module_corpus.get("missing_json_ids"))),
            "paper_module_json_parity_status": paper_module_corpus.get("parity_status"),
            "paper_module_legacy_only_count": paper_module_corpus.get("legacy_only_count"),
            "paper_module_required_subject_gap_count": paper_module_corpus.get("required_subject_gap_count"),
            "paper_module_unpopulated_selective_relation_count": paper_module_corpus.get("unpopulated_selective_relation_count"),
            "expected_skill_count": skill_corpus.get("expected_skill_count"),
            "skill_json_instance_count": skill_corpus.get("json_instance_count"),
            "skill_json_missing_count": len(_as_list(skill_corpus.get("missing_json_ids"))),
            "skill_json_parity_status": skill_corpus.get("parity_status"),
            "skill_required_relation_gap_count": skill_corpus.get("required_relation_gap_count"),
            "skill_unpopulated_selective_relation_count": skill_corpus.get("unpopulated_selective_relation_count"),
            "expected_standard_count": standard_corpus.get("expected_standard_count"),
            "standard_json_instance_count": standard_corpus.get("json_instance_count"),
            "standard_json_missing_count": len(_as_list(standard_corpus.get("missing_json_ids"))),
            "standard_json_parity_status": standard_corpus.get("parity_status"),
            "standard_legacy_or_draft_contract_count": standard_corpus.get("legacy_or_draft_contract_count"),
            "standard_required_relation_gap_count": standard_corpus.get("required_relation_gap_count"),
            "standard_required_relation_gap_instance_count": standard_corpus.get("required_relation_gap_instance_count"),
            "standard_governs_kind_resolved_edge_count": standard_corpus.get("governs_kind_resolved_edge_count"),
            "standard_governs_kind_unresolved_edge_count": standard_corpus.get("governs_kind_unresolved_edge_count"),
            "standard_governs_kind_missing_required_count": standard_corpus.get("governs_kind_missing_required_count"),
            "standard_triad_skill_resolved_edge_count": standard_corpus.get("triad_skill_resolved_edge_count"),
            "standard_triad_skill_planned_unresolved_edge_count": standard_corpus.get("triad_skill_planned_unresolved_edge_count"),
            "standard_triad_skill_unresolved_edge_count": standard_corpus.get("triad_skill_unresolved_edge_count"),
            "standard_triad_skill_missing_required_count": standard_corpus.get("triad_skill_missing_required_count"),
            "standard_used_by_organ_edge_count": standard_corpus.get("used_by_organ_edge_count"),
            "standard_used_by_organ_resolved_edge_count": standard_corpus.get("used_by_organ_resolved_edge_count"),
            "standard_used_by_organ_unresolved_edge_count": standard_corpus.get("used_by_organ_unresolved_edge_count"),
            "standard_used_by_organ_missing_accepted_target_count": (
                health["standards"].get("used_by_organ_missing_accepted_target_count")
            ),
            "standard_unregistered_file_count": len(_as_list(standard_corpus.get("extra_json_ids"))),
            "standard_missing_standard_id_file_count": len(_as_list(standard_corpus.get("files_missing_standard_id"))),
            "doctrine_kind_walkable_node_count": doctrine_kind_health.get("known_count"),
            "doctrine_kind_inbound_edge_count": doctrine_kind_health.get("inbound_edge_count"),
            "doctrine_kind_gap_count": doctrine_kind_health.get("gap_count"),
            "code_locus_walkable_node_count": code_loci_health.get("known_count"),
            "code_locus_walkability_gap_count": code_loci_health.get("planned_or_unresolved_path_count"),
            "receipt_walkable_node_count": receipts_health.get("known_count"),
            "receipt_missing_ref_count": receipts_health.get("missing_ref_count"),
            "receipt_unresolved_nonlocal_ref_count": receipts_health.get("unresolved_nonlocal_ref_count"),
        },
        "next_population_targets": next_targets[:3],
        "fake_green_guards": [
            {
                "guard_id": "planned_mechanism_not_resolved",
                "current_planned_count": coverage.get("planned_mechanism_count"),
                "current_resolved_count": coverage.get("resolved_mechanism_count"),
                "rule": "resolution_status=planned_unresolved increments planned_mechanism_count and never resolved_mechanism_count.",
            },
            {
                "guard_id": "coverage_projection_not_source",
                "rule": "Act on source refs, then regenerate and validate; do not hand-edit generated coverage or this card.",
            },
            {
                "guard_id": "axiom_json_parity_not_authority_flip",
                "rule": "Axiom JSON instances are migration progress; routing registry remains source-of-record until parity receipts justify an authority flip.",
            },
            {
                "guard_id": "principle_json_parity_not_edge_completion",
                "rule": "Principle and anti-principle JSON parity resolves legacy corpus targets, but unpopulated governs/negates edges remain residual pressure.",
            },
            {
                "guard_id": "concept_mechanism_json_parity_not_lattice_completion",
                "rule": "Concept and mechanism JSON parity resolves corpus migration only; unpopulated selective neighbours and code-locus gaps remain explicit residual pressure.",
            },
            {
                "guard_id": "paper_dependency_not_reverse_mechanism_upstream_edge",
                "rule": (
                    "paper_module A depends_on paper_module B maps only to mechanism(B).upstream_of "
                    "mechanism(A); it cannot justify mechanism(A).upstream_of mechanism(B)."
                ),
            },
            {
                "guard_id": "organ_json_parity_not_lattice_completion",
                "rule": "Organ JSON parity resolves atlas/registry migration only; missing required links and selective doctrine constraints remain residual pressure.",
            },
            {
                "guard_id": "standard_inventory_not_contract_completion",
                "rule": "Registry-backed standard JSON presence is inventory coverage only; legacy/draft contracts and unresolved triad skills remain residual pressure.",
            },
            {
                "guard_id": "population_deficit_not_release_gate",
                "rule": "population_status=deficit keeps release_readiness_status at not_ready_population_deficit.",
            },
        ],
        "reentry_condition": (
            "Resume at the first next_population_targets row whose deficits still appear "
            "after `microcosm doctrine-lattice check --root .` passes."
        ),
        "status": projection.get("status"),
    }


def validate_entry_card(
    card: dict[str, Any],
    root: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: check that an on-disk entry card is reproducible from current source.
    - Guarantee: returns {status: 'pass'|'blocked', errors[]}; status 'pass' iff the card equals the freshly built one (per-field and digest mismatches are itemized).
    - Fails: never raises; every divergence from the expected card is an error row.
    - When-needed: --check-entry-card before trusting the written card.
    - Escalates-to: build_entry_card.
    - Non-goal: passing proves source-reproducibility only, not release readiness.
    """
    errors: list[dict[str, Any]] = []
    generation = _as_dict(card.get("generation"))
    generated_at = str(generation.get("generated_at") or "check")
    command = str(generation.get("command") or "python -m microcosm_core.doctrine_lattice --entry-card")
    expected = build_entry_card(root, generated_at=generated_at, command=command)
    if card != expected:
        for key in (
            "source_refs",
            "status_card",
            "status_chips",
            "agent_band_ladder",
            "current_counts",
            "next_population_targets",
            "fake_green_guards",
            "reentry_condition",
            "status",
        ):
            if card.get(key) != expected.get(key):
                _add_error(errors, code="entry_card_reproducibility_mismatch", path=key, message=f"Entry card field {key} is not reproducible from source.")
        if generation.get("coverage_projection_digest") != _as_dict(expected.get("generation")).get("coverage_projection_digest"):
            _add_error(errors, code="entry_card_projection_digest_mismatch", path="generation.coverage_projection_digest", message="Entry card coverage projection digest does not match current sources.")
    return {
        "schema_version": "microcosm_doctrine_lattice_entry_card_validation_v1",
        "status": "pass" if not errors else "blocked",
        "errors": errors,
    }


def write_entry_card(
    root: str | Path | None = None,
    out: str | Path | None = None,
    *,
    generated_at: str | None = None,
    command: str = "python -m microcosm_core.doctrine_lattice --write-entry-card",
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: write the Microcosm-local agent entry card to disk and return it.
    - Guarantee: writes the built entry card (sorted-keys JSON) to out or ENTRY_CARD_REL and returns it.
    - Fails: raises OSError if the target file cannot be written.
    - When-needed: --write-entry-card regeneration.
    - Escalates-to: build_entry_card.
    - Non-goal: writing the card does not flip source authority or authorize publication.
    """
    resolved = Path(root).resolve() if root is not None else microcosm_root()
    card = build_entry_card(resolved, generated_at=generated_at, command=command)
    target = Path(out).resolve() if out is not None else resolved / ENTRY_CARD_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(card, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return card


def main(argv: list[str] | None = None) -> int:
    """CLI entry to build, write, or check the doctrine-lattice projections and corpora.
    [ACTION]

    - Teleology: single build/check front door for the doctrine lattice (coverage, axiom/principle/anti-principle/concept/mechanism corpora, entry card, doctrine projection).
    - Guarantee: the requested write/check/status action runs against the resolved root, prints its JSON result, and exit code matches that result's status.
    - Fails: bad args -> argparse error -> SystemExit(2); any check or write whose status/parity is not pass -> return 1.
    - Reads: routing source of record, PRINCIPLES.md/ANTI_PRINCIPLES.md, entry-packet specimens, mechanism registry, existing projection files under root.
    - Writes (only with --write-* flags): coverage projection, corpus JSON+markdown, entry card, and doctrine projection/graph/health surfaces.
    - When-needed: regenerating or validating doctrine-lattice generated artifacts before commit.
    - Escalates-to: write/validate corpus functions, write/validate_doctrine_projection, write/validate_coverage_projection, build/validate_entry_card.
    """

    parser = argparse.ArgumentParser(description="Build or check the Microcosm doctrine lattice coverage projection.")
    parser.add_argument("--root", default=None, help="Microcosm root. Defaults to detected package/check-out root.")
    parser.add_argument("--out", default=None, help="Output path. Defaults to core/doctrine_lattice_coverage.json under root.")
    parser.add_argument("--write", action="store_true", help="Write the coverage projection.")
    parser.add_argument("--check", action="store_true", help="Check the existing coverage projection against current sources.")
    parser.add_argument("--status", action="store_true", help="Print a compact doctrine-lattice status card.")
    parser.add_argument("--entry-card", action="store_true", help="Print the generated Microcosm-local agent entry card.")
    parser.add_argument("--write-entry-card", action="store_true", help="Write the generated Microcosm-local agent entry card.")
    parser.add_argument("--check-entry-card", action="store_true", help="Check the generated Microcosm-local agent entry card.")
    parser.add_argument("--write-axiom-corpus", action="store_true", help="Seed axiom JSON instances and markdown from the routing source of record.")
    parser.add_argument("--check-axiom-corpus", action="store_true", help="Check axiom JSON instance parity against the routing source of record.")
    parser.add_argument("--write-principle-corpus", action="store_true", help="Seed principle JSON instances and markdown from PRINCIPLES.md.")
    parser.add_argument("--check-principle-corpus", action="store_true", help="Check principle JSON instance parity against PRINCIPLES.md.")
    parser.add_argument("--write-anti-principle-corpus", action="store_true", help="Seed anti-principle JSON instances and markdown from ANTI_PRINCIPLES.md.")
    parser.add_argument("--check-anti-principle-corpus", action="store_true", help="Check anti-principle JSON instance parity against ANTI_PRINCIPLES.md.")
    parser.add_argument("--write-concept-corpus", action="store_true", help="Seed concept JSON instances and markdown from entry-packet population specimens.")
    parser.add_argument("--check-concept-corpus", action="store_true", help="Check concept JSON instance parity against entry-packet population specimens.")
    parser.add_argument("--write-mechanism-corpus", action="store_true", help="Seed mechanism JSON instances and markdown from the mechanism registry.")
    parser.add_argument("--check-mechanism-corpus", action="store_true", help="Check mechanism JSON instance parity against the mechanism registry.")
    parser.add_argument("--doctrine-projection", action="store_true", help="Print the generated doctrine lattice projection.")
    parser.add_argument("--write-doctrine-projection", action="store_true", help="Write doctrine lattice projection, graph, and health surfaces.")
    parser.add_argument("--check-doctrine-projection", action="store_true", help="Check doctrine lattice projection, graph, health, and axiom corpus parity.")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else microcosm_root()
    target = Path(args.out).resolve() if args.out else root / "core/doctrine_lattice_coverage.json"

    if args.check_axiom_corpus:
        result = validate_axiom_instance_corpus(root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1

    if args.write_axiom_corpus:
        result = write_axiom_instance_corpus(root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["parity_status"] == "pass" else 1

    if args.check_principle_corpus:
        result = validate_principle_instance_corpus(root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1

    if args.write_principle_corpus:
        result = write_principle_instance_corpus(root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["parity_status"] == "pass" else 1

    if args.check_anti_principle_corpus:
        result = validate_anti_principle_instance_corpus(root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1

    if args.write_anti_principle_corpus:
        result = write_anti_principle_instance_corpus(root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["parity_status"] == "pass" else 1

    if args.check_concept_corpus:
        result = validate_concept_instance_corpus(root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1

    if args.write_concept_corpus:
        result = write_concept_instance_corpus(root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["parity_status"] == "pass" else 1

    if args.check_mechanism_corpus:
        result = validate_mechanism_instance_corpus(root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1

    if args.write_mechanism_corpus:
        result = write_mechanism_instance_corpus(root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["parity_status"] == "pass" else 1

    if args.check_doctrine_projection:
        result = validate_doctrine_projection(root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1

    if args.write_doctrine_projection:
        projection = write_doctrine_projection(root)
        print(
            json.dumps(
                {
                    "status": projection["status"],
                    "written": [
                        DOCTRINE_PROJECTION_REL,
                        DOCTRINE_GRAPH_REL,
                        DOCTRINE_HEALTH_REL,
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if projection["status"] == "pass" else 1

    if args.doctrine_projection:
        projection = build_doctrine_projection(root)
        print(json.dumps(projection, indent=2, sort_keys=True))
        return 0 if projection["status"] == "pass" else 1

    if args.check_entry_card:
        entry_target = Path(args.out).resolve() if args.out else root / ENTRY_CARD_REL
        current = _as_dict(read_json_strict(entry_target))
        result = validate_entry_card(current, root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1

    if args.write_entry_card:
        card = write_entry_card(root, args.out)
        print(json.dumps({"status": card["status"], "written": str(Path(args.out).resolve() if args.out else root / ENTRY_CARD_REL)}, indent=2, sort_keys=True))
        return 0 if card["status"] == "pass" else 1

    if args.entry_card:
        card = build_entry_card(root)
        print(json.dumps(card, indent=2, sort_keys=True))
        return 0 if card["status"] == "pass" else 1

    if args.check:
        current = _as_dict(read_json_strict(target))
        result = validate_coverage_projection(current, root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1

    projection = write_coverage_projection(root, target) if args.write else build_coverage_projection(root)
    if args.status:
        print(json.dumps(_status_card(projection), indent=2, sort_keys=True))
    else:
        print(json.dumps(projection if not args.write else {"status": projection["status"], "written": str(target)}, indent=2, sort_keys=True))
    return 0 if projection["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
