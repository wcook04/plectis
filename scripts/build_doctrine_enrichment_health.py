#!/usr/bin/env python3
"""Project Microcosm doctrine and readiness health.

Reads the hand-authored enrichment source of record
(``core/doctrine_enrichment.json``) against the axiom/principle/anti-principle
instance corpora and reports per-kind coverage: how many objects are enriched
and how many carry each reader field. It also reads governed concept and
mechanism JSON rows to report the doctrine-routing floor beyond the 49
reader-enrichment cards, and audits generated paper-module JSON instances for
frontier readiness gaps. Coverage is PRESENCE / STRUCTURE, not correctness; the
latex render check and voice/overclaim review live in the dissemination build
and tests, not here.

The projection is a typed multi-section read model, not a single enrichment
gate. Each emitted section declares its gate role, source, what it proves, and
what it does not prove (see ``SECTION_MODEL``). Sections listed in
``COMPLETION_GATE_SECTIONS`` are the only inputs to the top-level
``status``/``governed_floor_complete``; sections listed in
``FRONTIER_AUDIT_SECTIONS`` are visibility-only and are never folded into the
completion gate without an explicit promotion in the governing standard
(``standards/std_microcosm_doctrine_enrichment.json``,
``paper_module_readiness_audit.completion_gate_policy``).

Usage:
  python3 scripts/build_doctrine_enrichment_health.py --write
  python3 scripts/build_doctrine_enrichment_health.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_doctrine_formal_soundness import run as run_soundness  # noqa: E402
from check_doctrine_reader_ladder import run as run_reader_ladder  # noqa: E402


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
ENRICHMENT_REL = "core/doctrine_enrichment.json"
HEALTH_REL = "core/doctrine_enrichment_health.json"
KIND_DIRS = {
    "axiom": ("receipts/doctrine_records/axioms", "AX-*.receipt.json"),
    "principle": ("receipts/doctrine_records/principles", "P-*.receipt.json"),
    "anti_principle": (
        "receipts/doctrine_records/anti_principles",
        "AP-*.receipt.json",
    ),
}
CONCEPT_ENTRY_PACKET_REL = "atlas/entry_packet.json"
MECHANISM_SOURCES_REL = "core/mechanism_sources.json"
CONCEPT_MECHANISM_POPULATION_RECEIPT_REL = (
    "receipts/concept_mechanism_population/"
    "concept_mechanism_records_population_receipt_20260605T1735Z.json"
)
ROUTING_KINDS = ("concept", "mechanism")
LEGACY_ROUTING_KIND_DIRS = {
    "concept": ("concepts", "concept.*.json"),
    "mechanism": ("mechanisms", "mechanism.*.json"),
}
PAPER_MODULE_DIR = ("paper_modules", "*.json")
REQUIRED_FIELDS = ("deep", "formal", "governs", "requires", "refuses", "example", "counterexample", "enforced_in", "does_not_prove")
ROUTING_REF_FIELDS = ("source_refs", "validator_refs", "receipt_refs", "anti_claims")
MECHANISM_PAYLOAD_REQUIRED_FIELDS = (
    "contract_version",
    "guardrails",
    "migration_contract",
    "projection_contract",
    "resolution_evidence",
    "support_contract",
)
ROUTING_REQUIRED_STRUCTURES = {
    "concept": [
        "source_refs",
        "valid_json_object",
        "validator_refs",
        "receipt_refs",
        "anti_claims",
        "entry_surface_contract",
        "cluster_flag",
        "relationships.edges",
        "resolved_mechanism_route",
        "empty_unpopulated_selective_relations",
    ],
    "mechanism": [
        "source_refs",
        "valid_json_object",
        "validator_refs",
        "receipt_refs",
        "anti_claims",
        "entry_surface_contract",
        "organ_refs",
        "mechanism_payload.contract",
        "relationships.edges",
        "resolved_concept_route",
        "resolved_existing_code_locus",
        "known_residual_selective_relations_counted_not_blocking",
    ],
}
PAPER_MODULE_REQUIRED_STRUCTURES = [
    "valid_json_object",
    "source_refs",
    "validator_refs",
    "receipt_refs_list_present",
    "anti_claims",
    "relationships.source_authority == json_capsule",
    "relationships.edges",
    "resolved_subject_route",
    "resolved_concept_route",
    "resolved_existing_code_locus",
    "required residual relations counted as blockers",
    "selective residual relations counted as frontier pressure",
]

PROJECTION_ROLE = "microcosm_doctrine_and_readiness_health_projection"
PROJECTION_PLANE = "microcosm_substrate_public_read_model"
PROJECTION_DISPLAY_NAME = "Microcosm doctrine and readiness health"
PLANE_NOTE = (
    "Public read model over microcosm-substrate sources only. External"
    " orchestration or control planes that operate on this repository are not"
    " represented in this projection and are never sources of record for it."
)
# The top-level status/governed_floor_complete fold EXACTLY these sections.
# Folding a frontier audit into this tuple requires explicit promotion in the
# governing standard plus a deliberate regression-test update, never a quiet
# checker edit (std_microcosm_doctrine_enrichment.json
# paper_module_readiness_audit.completion_gate_policy).
COMPLETION_GATE_SECTIONS = (
    "reader_enrichment_floor",
    "formal_soundness",
    "reader_ladder",
    "doctrine_routing_floor",
)
FRONTIER_AUDIT_SECTIONS = ("paper_module_readiness_audit",)


def _section_model() -> dict[str, Any]:
    """
    Serialize `scripts.build_doctrine_enrichment_health._section_model` into the payload
    shape expected by scripts build doctrine enrichment health.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    return {
        "reader_enrichment_floor": {
            "gate_role": "completion_floor",
            "counts_toward_completion_gate": True,
            "result_keys": ["kinds", "incomplete", "coverage_complete", "reader_enrichment_complete"],
            "sources_of_record": [
                ENRICHMENT_REL,
                "receipts/doctrine_records/axioms/AX-*.receipt.json",
                "receipts/doctrine_records/principles/P-*.receipt.json",
                "receipts/doctrine_records/anti_principles/AP-*.receipt.json",
            ],
            "proves": "Reader-field presence and structure for the 49 doctrine cards.",
            "does_not_prove": "Correctness, support evidence, proof authority, or release readiness.",
        },
        "formal_soundness": {
            "gate_role": "completion_floor",
            "counts_toward_completion_gate": True,
            "result_keys": ["formal_soundness"],
            "sources_of_record": [ENRICHMENT_REL],
            "proves": "Symbol/formula agreement for every formal block.",
            "does_not_prove": "Mathematical correctness, support evidence, proof authority, or release readiness.",
        },
        "reader_ladder": {
            "gate_role": "completion_floor",
            "counts_toward_completion_gate": True,
            "result_keys": ["reader_ladder"],
            "sources_of_record": [ENRICHMENT_REL],
            "proves": "Plain reading plus bounded analogy present and laundering-free.",
            "does_not_prove": "Analogy fidelity, clarity quality, support evidence, or release readiness.",
        },
        "doctrine_routing_floor": {
            "gate_role": "completion_floor",
            "counts_toward_completion_gate": True,
            "result_keys": ["routing_floor"],
            "sources_of_record": [
                f"{CONCEPT_ENTRY_PACKET_REL}::concept_mechanism_entry_route.population_specimens",
                f"{MECHANISM_SOURCES_REL}::mechanisms",
            ],
            "proves": "Checker-readable walkability of governed concept and mechanism routes.",
            "does_not_prove": "Ontology completeness, topology completeness, runtime correctness, support evidence, or release readiness.",
        },
        "paper_module_readiness_audit": {
            "gate_role": "frontier_audit",
            "counts_toward_completion_gate": False,
            "result_keys": ["paper_module_readiness_audit"],
            "sources_of_record": ["paper_modules/*.json"],
            "instance_owner": "microcosm_core.doctrine_lattice",
            "promotion_contract": (
                "Folding this audit into the completion gate requires explicit"
                " promotion in standards/std_microcosm_doctrine_enrichment.json"
                " (paper_module_readiness_audit.completion_gate_policy) plus a"
                " deliberate update to COMPLETION_GATE_SECTIONS and its"
                " regression tests."
            ),
            "proves": "Paper-module readiness gaps are visible: legacy-only rows, required residuals, unresolved routes.",
            "does_not_prove": "Paper-module floor completion, support evidence, proof authority, runtime correctness, or release readiness.",
        },
    }


def _corpus_ids(root: Path, kind: str) -> list[str]:
    """
    Compute corpus IDs from `root` and `kind`.

    Inputs are `root` and `kind`; notable helpers are `glob`, `loads`, `get`, `append`, and
    1 more.
    """
    subdir, glob = KIND_DIRS[kind]
    ids: list[str] = []
    for path in sorted((root / subdir).glob(glob)):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("record_id"):
            ids.append(str(row["record_id"]))
    return ids


def _legacy_routing_records(root: Path, kind: str) -> list[dict[str, Any]]:
    """
    Return legacy directory routing records for local fixtures and migrations.

    - Teleology: preserve malformed-json and migration coverage for temporary
      concept/mechanism directory fixtures after the public root moved to
      entry-packet and mechanism-source owners.
    - Mechanism: glob the legacy per-kind directory, parse each JSON object,
      and synthesize load-error records for malformed or non-object files.
    - Guarantee: returns checker-shaped records without mutating the checkout.
    - Fails: JSON decode errors become explicit `_routing_load_error` rows;
      missing directories produce an empty list.
    - Non-goal: does not revive legacy directories as current source
      authority or prove concept/mechanism completeness.
    """
    subdir, glob = LEGACY_ROUTING_KIND_DIRS[kind]
    records: list[dict[str, Any]] = []
    for path in sorted((root / subdir).glob(glob)):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            records.append(
                {
                    "id": f"{kind}.invalid_json.{path.name}",
                    "kind": kind,
                    "_routing_load_error": f"json_decode_error:{exc.msg}",
                }
            )
            continue
        if isinstance(row, dict):
            records.append(row)
        else:
            records.append(
                {
                    "id": f"{kind}.json_root_not_object.{path.name}",
                    "kind": kind,
                    "_routing_load_error": "json_root_not_object",
                }
            )
    return records

def _entry_packet_specimens(root: Path) -> list[dict[str, Any]]:
    """
    Read concept population specimens from the current entry packet source.

    - Teleology: make the doctrine routing floor follow the same concept entry
      surface that cold agents are told to use.
    - Mechanism: read `atlas/entry_packet.json`, descend to
      `concept_mechanism_entry_route.population_specimens`, and keep only
      object rows.
    - Guarantee: missing entry packets return an empty list so isolated legacy
      fixture tests can still run without fabricated authority.
    - Fails: malformed JSON or read errors propagate from `json.loads` and
      `read_text`.
    - Non-goal: does not treat the generated health projection or absent
      `concepts/` files as concept source authority.
    """
    path = root / CONCEPT_ENTRY_PACKET_REL
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    route = payload.get("concept_mechanism_entry_route")
    if not isinstance(route, dict):
        return []
    specimens = route.get("population_specimens")
    if not isinstance(specimens, list):
        return []
    return [row for row in specimens if isinstance(row, dict)]


def _mechanism_source_rows(root: Path) -> list[dict[str, Any]]:
    """
    Read governed mechanism rows from `core/mechanism_sources.json`.

    - Teleology: align mechanism routing health with the current mechanism
      registry owner instead of absent generated instance files.
    - Mechanism: read `core/mechanism_sources.json`, extract the `mechanisms`
      list, and retain object rows.
    - Guarantee: missing source files return an empty list so legacy fixture
      fallbacks remain possible.
    - Fails: malformed JSON or filesystem read errors propagate to the caller.
    - Non-goal: does not claim runtime correctness, topology completeness, or
      release authority from registry presence.
    """
    path = root / MECHANISM_SOURCES_REL
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("mechanisms")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _concept_ids(root: Path) -> set[str]:
    """
    Return concept IDs declared by the entry-packet population specimens.

    - Teleology: give relationship checks a bounded resolution set for concept
      targets without consulting generated health output.
    - Mechanism: prefix each entry-packet specimen id with `concept.` and
      collect the resulting IDs.
    - Guarantee: returns only IDs derived from the current entry packet.
    - Fails: propagates entry-packet read/parse failures from
      `_entry_packet_specimens`.
    - Non-goal: does not prove the concept corpus is complete.
    """
    ids: set[str] = set()
    for specimen in _entry_packet_specimens(root):
        specimen_id = str(specimen.get("specimen_id") or "").strip()
        if specimen_id:
            ids.add(f"concept.{specimen_id}")
    return ids


def _mechanism_ids(root: Path) -> set[str]:
    """
    Return mechanism IDs declared by `core/mechanism_sources.json`.

    - Teleology: let concept routing edges distinguish resolved mechanisms
      from residual pressure using the mechanism source owner.
    - Mechanism: collect nonempty `id` values from mechanism source rows.
    - Guarantee: returns a set with no duplicate IDs.
    - Fails: propagates mechanism-source read/parse failures from
      `_mechanism_source_rows`.
    - Non-goal: does not validate the mechanism rows beyond ID presence.
    """
    return {
        str(row["id"])
        for row in _mechanism_source_rows(root)
        if str(row.get("id") or "").strip()
    }


def _accepted_organ_ids(root: Path) -> set[str]:
    """
    Return accepted public organ IDs from atlas and registry sources.

    - Teleology: classify mechanism `runs_in` hosts as resolved only when the
      host exists in a public organ owner surface.
    - Mechanism: read `core/organ_atlas.json::organs` and
      `core/organ_registry.json::implemented_organs`, collecting `organ_id`.
    - Guarantee: returns the union of both organ surfaces without writing
      state.
    - Fails: malformed present JSON propagates; absent files are skipped.
    - Non-goal: does not claim accepted organs are product progress, runtime
      correctness, or release readiness.
    """
    ids: set[str] = set()
    atlas_path = root / "core/organ_atlas.json"
    if atlas_path.exists():
        payload = json.loads(atlas_path.read_text(encoding="utf-8"))
        for row in payload.get("organs") or []:
            if isinstance(row, dict) and row.get("organ_id"):
                ids.add(str(row["organ_id"]))
    registry_path = root / "core/organ_registry.json"
    if registry_path.exists():
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
        for row in payload.get("implemented_organs") or []:
            if isinstance(row, dict) and row.get("organ_id"):
                ids.add(str(row["organ_id"]))
    return ids


def _concept_routing_records(root: Path) -> list[dict[str, Any]]:
    """
    Build concept routing records from entry-packet population specimens.

    - Teleology: audit the concept floor the way a cold agent reaches it:
      through specimen-backed entry-packet rows, not absent JSON instances.
    - Mechanism: convert each population specimen into a checker-shaped
      concept row with source refs, validators, anti-claims, cluster flag, and
      mechanism edges.
    - Guarantee: resolved mechanism edges are judged against
      `core/mechanism_sources.json`; missing entry packets fall back to the
      legacy fixture loader.
    - Fails: malformed owner JSON propagates; unresolved mechanism references
      remain audit issues instead of being silently accepted.
    - Non-goal: does not make specimens proof of ontology completeness,
      support evidence, or release readiness.
    """
    specimens = _entry_packet_specimens(root)
    if not specimens:
        return _legacy_routing_records(root, "concept")
    mechanism_ids = _mechanism_ids(root)
    records: list[dict[str, Any]] = []
    for index, specimen in enumerate(specimens):
        specimen_id = str(specimen.get("specimen_id") or "").strip()
        concept_id = f"concept.{specimen_id}" if specimen_id else f"concept.missing_id.{index}"
        source_ref = (
            f"{CONCEPT_ENTRY_PACKET_REL}::"
            f"concept_mechanism_entry_route.population_specimens[{index}:{specimen_id or '<missing>'}]"
        )
        edges: list[dict[str, Any]] = []
        for edge_index, mechanism_id in enumerate(specimen.get("mechanism_ids") or []):
            target_id = str(mechanism_id)
            edges.append(
                {
                    "relation_id": "concept.instantiated_by.mechanism",
                    "relation_verb": "instantiated_by",
                    "reverse_verb": "instantiates",
                    "target_id": target_id,
                    "target_kind": "mechanism",
                    "target_status": (
                        "resolved_json_instance"
                        if target_id in mechanism_ids
                        else "residual_pressure"
                    ),
                    "justification": {
                        "source_ref": f"{source_ref}.mechanism_ids[{edge_index}]",
                        "summary": "Entry-packet population specimen names this mechanism.",
                    },
                }
            )
        records.append(
            {
                "id": concept_id,
                "kind": "concept",
                "authority_boundary": (
                    "entry_packet_population_specimen_not_concept_completeness_"
                    "support_evidence_or_release_authority"
                ),
                "source_refs": [source_ref, *(specimen.get("source_refs") or [])],
                "validator_refs": specimen.get("validator_refs") or [CONCEPT_ENTRY_PACKET_REL],
                "receipt_refs": [CONCEPT_MECHANISM_POPULATION_RECEIPT_REL],
                "anti_claims": specimen.get("anti_claims") or [
                    "Entry-packet concept specimen is not doctrine completeness or release authority."
                ],
                "entry_surface_contract": {
                    "required": True,
                    "source_ref": "AGENTS.md::Concept And Mechanism Entry",
                },
                "cluster_flag": {
                    "concept_id": concept_id,
                    "specimen_id": specimen_id,
                    "source_ref": source_ref,
                },
                "relationships": {
                    "source_authority": "entry_packet_population_specimen",
                    "source_ref": source_ref,
                    "unpopulated_selective_relations": [],
                    "edges": edges,
                },
            }
        )
    return records


def _mechanism_routing_records(root: Path) -> list[dict[str, Any]]:
    """
    Build mechanism routing records from `core/mechanism_sources.json`.

    - Teleology: make mechanism routing health inspect the live mechanism
      source owner while preserving planned-target and residual pressure.
    - Mechanism: derive checker rows from each mechanism source row, including
      concept edges, organ host edges, upstream mechanism edges, code loci,
      receipt refs, payload contracts, and planned targets.
    - Guarantee: required routes fail closed when concept/code-locus evidence
      is missing; planned organ targets stay visible as non-blocking frontier
      pressure.
    - Fails: malformed owner JSON propagates; nonexistent resolved code loci
      are reported by `_audit_mechanism_routing_record`.
    - Non-goal: does not prove runtime behavior, topology completeness,
      support evidence, or release readiness.
    """
    rows = _mechanism_source_rows(root)
    if not rows:
        return _legacy_routing_records(root, "mechanism")
    concept_ids = _concept_ids(root)
    mechanism_ids = {str(row.get("id")) for row in rows if row.get("id")}
    organ_ids = _accepted_organ_ids(root)
    records: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        mechanism_id = str(row.get("id") or "").strip()
        source_ref = f"{MECHANISM_SOURCES_REL}::mechanisms[{index}:{mechanism_id or '<missing>'}]"
        resolution_evidence = row.get("resolution_evidence")
        validator_refs: list[str] = []
        if isinstance(resolution_evidence, dict):
            validator_refs = [
                str(value)
                for key, value in resolution_evidence.items()
                if ("command" in str(key) or "regression" in str(key)) and value
            ]
        if not validator_refs:
            validator_refs = [MECHANISM_SOURCES_REL]

        edges: list[dict[str, Any]] = []
        for edge_index, concept_id in enumerate(row.get("concept_refs") or []):
            target_id = str(concept_id)
            edges.append(
                {
                    "relation_id": "mechanism.grounded_by.concept",
                    "relation_verb": "grounded_by",
                    "reverse_verb": "grounds",
                    "target_id": target_id,
                    "target_kind": "concept",
                    "target_status": (
                        "resolved_json_instance"
                        if target_id in concept_ids
                        else "residual_pressure"
                    ),
                    "justification": {
                        "source_ref": f"{source_ref}.concept_refs[{edge_index}]",
                        "summary": "Mechanism source row names this concept.",
                    },
                }
            )
        planned_targets = [
            target
            for target in row.get("planned_targets") or []
            if isinstance(target, dict)
        ]
        planned_by_id = {
            (str(target.get("target_kind") or ""), str(target.get("target_id") or "")): target
            for target in planned_targets
        }
        for edge_index, organ_id in enumerate(row.get("runs_in") or []):
            target_id = str(organ_id)
            planned_target = planned_by_id.get(("organ", target_id), {})
            edges.append(
                {
                    "relation_id": "mechanism.runs_in.organ",
                    "relation_verb": "runs_in",
                    "reverse_verb": "runs",
                    "target_id": target_id,
                    "target_kind": "organ",
                    "target_status": str(
                        planned_target.get("target_status")
                        or (
                            "resolved_json_instance"
                            if target_id in organ_ids
                            else "residual_pressure"
                        )
                    ),
                    "residual_pressure_ref": planned_target.get("residual_pressure_ref"),
                    "justification": {
                        "source_ref": f"{source_ref}.runs_in[{edge_index}]",
                        "summary": "Mechanism registry row names this organ as the runtime host.",
                    },
                }
            )
        for edge_index, upstream_id in enumerate(row.get("upstream_of") or []):
            target_id = str(upstream_id)
            edges.append(
                {
                    "relation_id": "mechanism.upstream_of.mechanism",
                    "relation_verb": "upstream_of",
                    "reverse_verb": "downstream_of",
                    "target_id": target_id,
                    "target_kind": "mechanism",
                    "target_status": (
                        "resolved_json_instance"
                        if target_id in mechanism_ids
                        else "residual_pressure"
                    ),
                    "justification": {
                        "source_ref": f"{source_ref}.upstream_of[{edge_index}]",
                        "summary": "Mechanism source row names this downstream mechanism.",
                    },
                }
            )

        residuals: list[dict[str, Any]] = []
        if not row.get("upstream_of"):
            residuals.append(
                {
                    "relation_id": "mechanism.upstream_of.mechanism",
                    "requirement": "selective",
                    "status": "residual_pressure",
                    "source_ref": source_ref,
                    "reason": "Mechanism source row does not name sibling/upstream mechanism relations.",
                }
            )
        records.append(
            {
                "id": mechanism_id,
                "kind": "mechanism",
                "authority_boundary": (
                    "mechanism_source_record_not_runtime_correctness_"
                    "support_evidence_or_release_authority"
                ),
                "source_refs": [source_ref, *(row.get("input_refs") or [])],
                "validator_refs": validator_refs,
                "receipt_refs": row.get("receipt_refs") or [CONCEPT_MECHANISM_POPULATION_RECEIPT_REL],
                "anti_claims": [
                    "Mechanism source rows do not prove runtime correctness, topology completeness, or release readiness."
                ],
                "entry_surface_contract": {
                    "required": True,
                    "source_ref": "AGENTS.md::Concept And Mechanism Entry",
                },
                "organ_refs": row.get("runs_in") or [],
                "code_loci": row.get("code_loci") or [],
                "mechanism_payload": {
                    "contract_version": "mechanism_source_record_v1",
                    "guardrails": row.get("guardrails") or [],
                    "migration_contract": {
                        "source_of_record": MECHANISM_SOURCES_REL,
                        "source_ref": source_ref,
                    },
                    "projection_contract": {
                        "projection_hooks": row.get("projection_hooks") or [],
                    },
                    "resolution_evidence": resolution_evidence or {},
                    "support_contract": {
                        "receipt_refs": row.get("receipt_refs") or [],
                        "input_refs": row.get("input_refs") or [],
                    },
                    "source_registry_row": row,
                },
                "relationships": {
                    "source_authority": "mechanism_source_record",
                    "source_registry_row_ref": source_ref,
                    "unpopulated_selective_relations": residuals,
                    "edges": edges,
                },
            }
        )
    return records


def _routing_records(root: Path, kind: str) -> list[dict[str, Any]]:
    """
    Return governed routing records for concept or mechanism health audits.

    - Teleology: dispatch the doctrine routing floor to the current owner for
      each governed kind.
    - Mechanism: use entry-packet specimens for concepts, mechanism sources
      for mechanisms, and an empty list for unknown kinds.
    - Guarantee: does not write state or read generated health output.
    - Fails: propagates owner read/parse failures from the selected loader.
    - Non-goal: does not invent a new routing source or broaden the completion
      gate beyond concept/mechanism routing.
    """
    if kind == "concept":
        return _concept_routing_records(root)
    if kind == "mechanism":
        return _mechanism_routing_records(root)
    return []


def _paper_module_records(root: Path) -> list[dict[str, Any]]:
    """
    Compute paper module records from `root`.

    Inputs are `root`; notable helpers are `glob`, `loads`, `append`, and `read_text`.
    """
    subdir, glob = PAPER_MODULE_DIR
    records: list[dict[str, Any]] = []
    for path in sorted((root / subdir).glob(glob)):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            records.append(
                {
                    "id": f"paper_module.invalid_json.{path.name}",
                    "kind": "paper_module",
                    "_paper_module_load_error": f"json_decode_error:{exc.msg}",
                }
            )
            continue
        if isinstance(row, dict):
            records.append(row)
        else:
            records.append(
                {
                    "id": f"paper_module.json_root_not_object.{path.name}",
                    "kind": "paper_module",
                    "_paper_module_load_error": "json_root_not_object",
                }
            )
    return records


def _has_field(record: dict[str, Any], field: str) -> bool:
    """
    Return whether has field holds for the scripts build doctrine enrichment health flow.

    The result is derived from `record` and `field` with `get` and `strip`; failing evidence
    is returned or raised exactly where the body says so.
    """
    value = record.get(field)
    if field == "formal":
        return isinstance(value, dict) and bool(str(value.get("latex") or "").strip())
    if field == "example":
        return isinstance(value, dict) and bool(str(value.get("text") or "").strip())
    if field == "counterexample":
        return isinstance(value, dict) and bool(str(value.get("text") or "").strip())
    if field == "enforced_in":
        return isinstance(value, list) and len(value) > 0
    return bool(str(value or "").strip())


def _audit_concept_routing_record(record: dict[str, Any]) -> list[str]:
    """
    Audit whether audit concept routing record holds for the scripts build doctrine
    enrichment health flow.

    The result is derived from `record` with `strip`, `get`, `append`, and `startswith`;
    failing evidence is returned or raised exactly where the body says so.
    """
    issues: list[str] = []
    load_error = str(record.get("_routing_load_error") or "").strip()
    if load_error:
        return [load_error]

    concept_id = str(record.get("id") or "").strip()
    if not concept_id:
        issues.append("id_missing")
    if record.get("kind") != "concept":
        issues.append("kind_not_concept")
    if not str(record.get("authority_boundary") or "").strip():
        issues.append("authority_boundary_missing")

    for field in ROUTING_REF_FIELDS:
        if not isinstance(record.get(field), list) or not record[field]:
            issues.append(f"{field}_missing")

    entry_contract = record.get("entry_surface_contract")
    if not isinstance(entry_contract, dict) or entry_contract.get("required") is not True:
        issues.append("entry_surface_contract_missing")

    cluster_flag = record.get("cluster_flag")
    if not isinstance(cluster_flag, dict) or cluster_flag.get("concept_id") != concept_id:
        issues.append("cluster_flag_mismatch")

    relationships = record.get("relationships")
    if not isinstance(relationships, dict):
        issues.append("relationships_missing")
        return issues

    if relationships.get("unpopulated_selective_relations"):
        issues.append("unpopulated_selective_relations_present")

    edges = relationships.get("edges")
    if not isinstance(edges, list) or not edges:
        issues.append("edges_missing")
        edges = []

    mechanism_route_count = 0
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            issues.append(f"edge_{index}_not_object")
            continue
        relation_id = str(edge.get("relation_id") or "")
        if not relation_id.startswith("concept."):
            issues.append(f"edge_{index}_relation_id_not_concept")
        for field in ("relation_verb", "reverse_verb", "target_id", "target_kind", "target_status"):
            if not str(edge.get(field) or "").strip():
                issues.append(f"edge_{index}_{field}_missing")
        justification = edge.get("justification")
        if not isinstance(justification, dict):
            issues.append(f"edge_{index}_justification_missing")
        else:
            if not str(justification.get("source_ref") or "").strip():
                issues.append(f"edge_{index}_source_ref_missing")
            if not str(justification.get("summary") or "").strip():
                issues.append(f"edge_{index}_summary_missing")
        if edge.get("target_status") != "resolved_json_instance":
            issues.append(f"edge_{index}_target_unresolved")
        if edge.get("target_kind") == "mechanism" and edge.get("target_status") == "resolved_json_instance":
            mechanism_route_count += 1

    if mechanism_route_count == 0:
        issues.append("resolved_mechanism_route_missing")
    return issues


def _audit_mechanism_routing_record(root: Path, record: dict[str, Any]) -> list[str]:
    """
    Audit whether audit mechanism routing record holds for the scripts build doctrine
    enrichment health flow.

    The result is derived from `root` and `record` with `strip`, `get`, `append`,
    `startswith`, and 1 more; failing evidence is returned or raised exactly where the body
    says so.
    """
    issues: list[str] = []
    load_error = str(record.get("_routing_load_error") or "").strip()
    if load_error:
        return [load_error]

    mechanism_id = str(record.get("id") or "").strip()
    if not mechanism_id:
        issues.append("id_missing")
    if record.get("kind") != "mechanism":
        issues.append("kind_not_mechanism")
    if not str(record.get("authority_boundary") or "").strip():
        issues.append("authority_boundary_missing")

    for field in ROUTING_REF_FIELDS:
        if not isinstance(record.get(field), list) or not record[field]:
            issues.append(f"{field}_missing")

    entry_contract = record.get("entry_surface_contract")
    if not isinstance(entry_contract, dict) or entry_contract.get("required") is not True:
        issues.append("entry_surface_contract_missing")

    if not isinstance(record.get("organ_refs"), list) or not record["organ_refs"]:
        issues.append("organ_refs_missing")

    mechanism_payload = record.get("mechanism_payload")
    if not isinstance(mechanism_payload, dict):
        issues.append("mechanism_payload_missing")
    else:
        for field in MECHANISM_PAYLOAD_REQUIRED_FIELDS:
            if not mechanism_payload.get(field):
                issues.append(f"mechanism_payload_{field}_missing")

    code_loci = record.get("code_loci")
    resolved_existing_code_loci = 0
    if not isinstance(code_loci, list) or not code_loci:
        issues.append("code_loci_missing")
    else:
        for index, locus in enumerate(code_loci):
            if not isinstance(locus, dict):
                issues.append(f"code_locus_{index}_not_object")
                continue
            path = str(locus.get("path") or "").strip()
            if not path:
                issues.append(f"code_locus_{index}_path_missing")
            if locus.get("resolution") != "resolved":
                issues.append(f"code_locus_{index}_not_resolved")
            if path and locus.get("resolution") == "resolved":
                if (root / path).exists():
                    resolved_existing_code_loci += 1
                else:
                    issues.append(f"code_locus_{index}_path_not_found")
    if resolved_existing_code_loci == 0:
        issues.append("resolved_existing_code_locus_missing")

    relationships = record.get("relationships")
    if not isinstance(relationships, dict):
        issues.append("relationships_missing")
        return issues

    edges = relationships.get("edges")
    if not isinstance(edges, list) or not edges:
        issues.append("edges_missing")
        edges = []

    concept_route_count = 0
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            issues.append(f"edge_{index}_not_object")
            continue
        relation_id = str(edge.get("relation_id") or "")
        if not relation_id.startswith("mechanism."):
            issues.append(f"edge_{index}_relation_id_not_mechanism")
        for field in ("relation_verb", "reverse_verb", "target_id", "target_kind", "target_status"):
            if not str(edge.get(field) or "").strip():
                issues.append(f"edge_{index}_{field}_missing")
        justification = edge.get("justification")
        if not isinstance(justification, dict):
            issues.append(f"edge_{index}_justification_missing")
        else:
            if not str(justification.get("source_ref") or "").strip():
                issues.append(f"edge_{index}_source_ref_missing")
            if not str(justification.get("summary") or "").strip():
                issues.append(f"edge_{index}_summary_missing")
        if edge.get("target_kind") == "concept" and edge.get("target_status") == "resolved_json_instance":
            concept_route_count += 1

    if concept_route_count == 0:
        issues.append("resolved_concept_route_missing")
    return issues


def _source_planned_target_lookup(record: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    """
    Serialize `scripts.build_doctrine_enrichment_health._source_planned_target_lookup` into
    the payload shape expected by scripts build doctrine enrichment health.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    payload = record.get("mechanism_payload")
    if not isinstance(payload, dict):
        return {}
    source_row = payload.get("source_registry_row")
    if not isinstance(source_row, dict):
        return {}
    planned_targets = source_row.get("planned_targets")
    if not isinstance(planned_targets, list):
        return {}

    relationships = record.get("relationships")
    source_ref = ""
    if isinstance(relationships, dict):
        source_ref = str(relationships.get("source_registry_row_ref") or "")

    lookup: dict[tuple[str, str, str], dict[str, Any]] = {}
    for index, planned_target in enumerate(planned_targets):
        if not isinstance(planned_target, dict):
            continue
        target_kind = str(planned_target.get("target_kind") or "")
        target_id = str(planned_target.get("target_id") or "")
        target_status = str(planned_target.get("target_status") or "")
        if not target_kind or not target_id or not target_status:
            continue
        metadata = dict(planned_target)
        if source_ref:
            metadata["planned_target_source_ref"] = f"{source_ref}.planned_targets[{index}]"
        lookup[(target_kind, target_id, target_status)] = metadata
    return lookup


def _mechanism_residual_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Serialize `scripts.build_doctrine_enrichment_health._mechanism_residual_summary` into
    the payload shape expected by scripts build doctrine enrichment health.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    residual_rows: list[dict[str, Any]] = []
    planned_edge_rows: list[dict[str, Any]] = []
    planned_edge_details: list[dict[str, Any]] = []
    planned_edge_counts_by_target_kind: dict[str, int] = {}
    planned_edge_counts_by_target_status: dict[str, int] = {}
    for record in records:
        if record.get("_routing_load_error"):
            continue
        mechanism_id = str(record.get("id") or "<missing>")
        relationships = record.get("relationships")
        if not isinstance(relationships, dict):
            continue
        residuals = relationships.get("unpopulated_selective_relations")
        if isinstance(residuals, list) and residuals:
            residual_rows.append({"id": mechanism_id, "count": len(residuals)})
        edges = relationships.get("edges")
        if isinstance(edges, list):
            planned_count = 0
            source_planned_targets = _source_planned_target_lookup(record)
            for edge in edges:
                if not isinstance(edge, dict):
                    continue
                target_status = str(edge.get("target_status") or "")
                if not target_status.startswith("planned_"):
                    continue
                planned_count += 1
                target_kind = str(edge.get("target_kind") or "<missing>")
                target_id = str(edge.get("target_id") or "<missing>")
                source_planned_target = source_planned_targets.get(
                    (target_kind, target_id, target_status),
                    {},
                )
                planned_edge_counts_by_target_kind[target_kind] = (
                    planned_edge_counts_by_target_kind.get(target_kind, 0) + 1
                )
                planned_edge_counts_by_target_status[target_status] = (
                    planned_edge_counts_by_target_status.get(target_status, 0) + 1
                )
                justification = edge.get("justification")
                if not isinstance(justification, dict):
                    justification = {}
                if target_kind == "organ":
                    next_safe_mutation_route = "organ_owner_admission_or_runs_in_source_remap"
                    reentry_condition = (
                        "Admit the target through core/organ_registry.json and "
                        "core/organ_atlas.json using the organ-atlas owner lane, "
                        "or remap mechanism.runs_in in core/mechanism_sources.json "
                        "to an accepted public host; never hand-edit generated "
                        "health rows."
                    )
                else:
                    next_safe_mutation_route = f"{target_kind}_owner_admission_or_source_remap"
                    reentry_condition = (
                        "Admit the planned target through its source owner lane "
                        "or remap the source relationship to a resolved public "
                        "target; never hand-edit generated health rows."
                    )
                next_safe_mutation_route = str(
                    source_planned_target.get("next_safe_mutation_route")
                    or next_safe_mutation_route
                )
                reentry_condition = str(
                    source_planned_target.get("reentry_condition") or reentry_condition
                )
                residual_pressure_ref = (
                    source_planned_target.get("residual_pressure_ref")
                    or edge.get("residual_pressure_ref")
                )
                planned_target_source_ref = str(
                    source_planned_target.get("planned_target_source_ref") or ""
                )
                planned_target_authority_boundary = str(
                    source_planned_target.get("authority_boundary") or ""
                )
                planned_edge_details.append(
                    {
                        "id": mechanism_id,
                        "relation_id": str(edge.get("relation_id") or "<missing>"),
                        "target_kind": target_kind,
                        "target_id": target_id,
                        "target_status": target_status,
                        "source_ref": str(justification.get("source_ref") or ""),
                        "summary": str(justification.get("summary") or ""),
                        "residual_pressure_ref": residual_pressure_ref,
                        "next_safe_mutation_route": next_safe_mutation_route,
                        "reentry_condition": reentry_condition,
                        "authority_boundary": (
                            "planned_edge_visibility_only_not_target_admission_"
                            "support_evidence_or_release_authority"
                        ),
                        "planned_target_source_ref": planned_target_source_ref,
                        "planned_target_authority_boundary": planned_target_authority_boundary,
                    }
                )
            if planned_count:
                planned_edge_rows.append({"id": mechanism_id, "count": planned_count})
    return {
        "known_residual_selective_relation_rows": residual_rows,
        "known_residual_selective_relation_row_count": len(residual_rows),
        "known_residual_selective_relation_count": sum(row["count"] for row in residual_rows),
        "planned_edge_rows": planned_edge_rows,
        "planned_edge_row_count": len(planned_edge_rows),
        "planned_edge_count": sum(row["count"] for row in planned_edge_rows),
        "planned_edge_details": planned_edge_details,
        "planned_edge_detail_count": len(planned_edge_details),
        "planned_edge_counts_by_target_kind": dict(sorted(planned_edge_counts_by_target_kind.items())),
        "planned_edge_counts_by_target_status": dict(sorted(planned_edge_counts_by_target_status.items())),
        "residual_policy": "Residual selective relations and planned non-floor edges are disclosed as frontier pressure, not counted as support evidence or topology completeness.",
    }


def _audit_paper_module_readiness_record(root: Path, record: dict[str, Any]) -> list[str]:
    """
    Audit whether audit paper module readiness record holds for the scripts build doctrine
    enrichment health flow.

    The result is derived from `root` and `record` with `strip`, `get`, `append`,
    `startswith`, and 1 more; failing evidence is returned or raised exactly where the body
    says so.
    """
    issues: list[str] = []
    load_error = str(record.get("_paper_module_load_error") or "").strip()
    if load_error:
        return [load_error]

    paper_module_id = str(record.get("id") or "").strip()
    if not paper_module_id:
        issues.append("id_missing")
    if record.get("kind") != "paper_module":
        issues.append("kind_not_paper_module")
    if not str(record.get("authority_boundary") or "").strip():
        issues.append("authority_boundary_missing")

    for field in ("source_refs", "validator_refs", "anti_claims"):
        if not isinstance(record.get(field), list) or not record[field]:
            issues.append(f"{field}_missing")
    if not isinstance(record.get("receipt_refs"), list):
        issues.append("receipt_refs_not_list")

    relationships = record.get("relationships")
    if not isinstance(relationships, dict):
        issues.append("relationships_missing")
        return issues

    if relationships.get("source_authority") != "json_capsule":
        issues.append("source_authority_not_json_capsule")

    residuals = relationships.get("unpopulated_selective_relations")
    if isinstance(residuals, list):
        required_residual_count = sum(
            1 for residual in residuals if isinstance(residual, dict) and residual.get("requirement") == "required"
        )
        if required_residual_count:
            issues.append("required_residual_relations_present")
    elif residuals is not None:
        issues.append("unpopulated_selective_relations_not_list")

    code_loci = relationships.get("code_loci")
    resolved_existing_code_loci = 0
    if not isinstance(code_loci, list) or not code_loci:
        issues.append("code_loci_missing")
    else:
        for index, locus in enumerate(code_loci):
            if not isinstance(locus, dict):
                issues.append(f"code_locus_{index}_not_object")
                continue
            path = str(locus.get("path") or "").strip()
            if not path:
                issues.append(f"code_locus_{index}_path_missing")
            if locus.get("resolution") != "resolved":
                issues.append(f"code_locus_{index}_not_resolved")
            if path and locus.get("resolution") == "resolved":
                if (root / path).exists():
                    resolved_existing_code_loci += 1
                else:
                    issues.append(f"code_locus_{index}_path_not_found")

    edges = relationships.get("edges")
    if not isinstance(edges, list) or not edges:
        issues.append("edges_missing")
        edges = []

    subject_route_count = 0
    concept_route_count = 0
    code_locus_route_count = 0
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            issues.append(f"edge_{index}_not_object")
            continue
        relation_id = str(edge.get("relation_id") or "")
        if not relation_id.startswith("paper_module."):
            issues.append(f"edge_{index}_relation_id_not_paper_module")
        for field in ("relation_verb", "reverse_verb", "target_id", "target_kind", "target_status"):
            if not str(edge.get(field) or "").strip():
                issues.append(f"edge_{index}_{field}_missing")
        justification = edge.get("justification")
        if not isinstance(justification, dict):
            issues.append(f"edge_{index}_justification_missing")
        else:
            if not str(justification.get("source_ref") or "").strip():
                issues.append(f"edge_{index}_source_ref_missing")
            if not str(justification.get("summary") or "").strip():
                issues.append(f"edge_{index}_summary_missing")

        target_status = edge.get("target_status")
        if relation_id == "paper_module.explains.organ_or_mechanism":
            if edge.get("target_kind") in {"organ", "mechanism"} and target_status == "resolved_json_instance":
                subject_route_count += 1
        if relation_id == "paper_module.governed_by.concept":
            if edge.get("target_kind") == "concept" and target_status == "resolved_json_instance":
                concept_route_count += 1
        if relation_id == "paper_module.cites.code_locus":
            if edge.get("target_kind") == "code_locus" and target_status == "resolved_code_locus":
                code_locus_route_count += 1

    if subject_route_count == 0:
        issues.append("resolved_subject_route_missing")
    if concept_route_count == 0:
        issues.append("resolved_concept_route_missing")
    if code_locus_route_count == 0 or resolved_existing_code_loci == 0:
        issues.append("resolved_existing_code_locus_missing")
    return issues


def _paper_module_residual_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Serialize `scripts.build_doctrine_enrichment_health._paper_module_residual_summary` into
    the payload shape expected by scripts build doctrine enrichment health.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    residual_rows: list[dict[str, Any]] = []
    counts_by_requirement: dict[str, int] = {}
    counts_by_relation_id: dict[str, int] = {}
    source_authority_counts: dict[str, int] = {}
    for record in records:
        if record.get("_paper_module_load_error"):
            continue
        paper_module_id = str(record.get("id") or "<missing>")
        relationships = record.get("relationships")
        if not isinstance(relationships, dict):
            continue
        authority = str(relationships.get("source_authority") or "<missing>")
        source_authority_counts[authority] = source_authority_counts.get(authority, 0) + 1
        residuals = relationships.get("unpopulated_selective_relations")
        if not isinstance(residuals, list) or not residuals:
            continue
        required_count = 0
        selective_count = 0
        for residual in residuals:
            if not isinstance(residual, dict):
                continue
            requirement = str(residual.get("requirement") or "<missing>")
            relation_id = str(residual.get("relation_id") or "<missing>")
            counts_by_requirement[requirement] = counts_by_requirement.get(requirement, 0) + 1
            counts_by_relation_id[relation_id] = counts_by_relation_id.get(relation_id, 0) + 1
            if requirement == "required":
                required_count += 1
            elif requirement == "selective":
                selective_count += 1
        residual_rows.append(
            {
                "id": paper_module_id,
                "count": required_count + selective_count,
                "required_count": required_count,
                "selective_count": selective_count,
            }
        )
    return {
        "source_authority_counts": dict(sorted(source_authority_counts.items())),
        "residual_relation_rows": residual_rows,
        "residual_relation_row_count": len(residual_rows),
        "residual_relation_count": sum(row["count"] for row in residual_rows),
        "residual_relation_counts_by_requirement": dict(sorted(counts_by_requirement.items())),
        "residual_relation_counts_by_relation_id": dict(sorted(counts_by_relation_id.items())),
        "required_residual_relation_count": counts_by_requirement.get("required", 0),
        "selective_residual_relation_count": counts_by_requirement.get("selective", 0),
        "residual_policy": "Required paper-module residuals block readiness. Selective residuals are disclosed as frontier pressure, not counted as support evidence or topology completeness.",
    }


def _build_paper_module_readiness_audit(root: Path) -> dict[str, Any]:
    """
    Serialize `scripts.build_doctrine_enrichment_health._build_paper_module_readiness_audit`
    into the payload shape expected by scripts build doctrine enrichment health.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    records = _paper_module_records(root)
    issue_rows = [
        {"id": str(record.get("id") or "<missing>"), "issues": _audit_paper_module_readiness_record(root, record)}
        for record in records
    ]
    issue_rows = [row for row in issue_rows if row["issues"]]
    ready = len(records) - len(issue_rows)
    ready_complete = not issue_rows and ready == len(records)
    residual_summary = _paper_module_residual_summary(records)
    required_gap_ids = [
        row["id"]
        for row in residual_summary["residual_relation_rows"]
        if row["required_count"]
    ]
    return {
        "schema_version": "microcosm_paper_module_readiness_audit_v1",
        "authority_boundary": "Paper-module readiness audit over generated paper-module JSON instances. It exposes walkability and residual pressure only; it is not source authority, support evidence, proof authority, release readiness, or permission to hand-edit generated paper-module rows.",
        "status": "complete" if ready_complete else "frontier",
        "readiness_complete": ready_complete,
        "source_of_record": {
            "paper_module_instances": "paper_modules/*.json",
            "instance_owner": "microcosm_core.doctrine_lattice",
            "upstream_sources": [
                "core/paper_module_capsules.json",
                "paper_modules/*.md legacy inventory",
            ],
        },
        "required_structures": PAPER_MODULE_REQUIRED_STRUCTURES,
        "total_objects": len(records),
        "ready_objects": ready,
        "incomplete_ids": [row["id"] for row in issue_rows],
        "issue_rows": issue_rows,
        "required_gap_ids": required_gap_ids,
        **residual_summary,
    }


def _build_routing_floor(root: Path) -> dict[str, Any]:
    """
    Serialize `scripts.build_doctrine_enrichment_health._build_routing_floor` into the
    payload shape expected by scripts build doctrine enrichment health.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    kinds: dict[str, Any] = {}
    incomplete: list[dict[str, Any]] = []
    for kind in ROUTING_KINDS:
        records = _routing_records(root, kind)
        if kind == "concept":
            issue_rows = [
                {"id": str(record.get("id") or "<missing>"), "issues": _audit_concept_routing_record(record)}
                for record in records
            ]
        elif kind == "mechanism":
            issue_rows = [
                {"id": str(record.get("id") or "<missing>"), "issues": _audit_mechanism_routing_record(root, record)}
                for record in records
            ]
        else:
            issue_rows = []
        issue_rows = [row for row in issue_rows if row["issues"]]
        incomplete.extend(issue_rows)
        routed = len(records) - len(issue_rows)
        kind_row: dict[str, Any] = {
            "total": len(records),
            "routed": routed,
            "incomplete_ids": [row["id"] for row in issue_rows],
            "issue_rows": issue_rows,
            "required_structures": ROUTING_REQUIRED_STRUCTURES[kind],
        }
        if kind == "mechanism":
            kind_row.update(_mechanism_residual_summary(records))
        kinds[kind] = kind_row
    total = sum(row["total"] for row in kinds.values())
    routed = sum(row["routed"] for row in kinds.values())
    complete = not incomplete and total == routed
    return {
        "schema_version": "microcosm_doctrine_routing_floor_v2",
        "authority_boundary": "Concept and mechanism routing floor over governed JSON rows. Structure and route presence only; not concept completeness, topology completeness, support evidence, release authority, or proof correctness.",
        "status": "complete" if complete else "partial",
        "coverage_complete": complete,
        "source_of_record": {
            "concept": f"{CONCEPT_ENTRY_PACKET_REL}::concept_mechanism_entry_route.population_specimens",
            "mechanism": f"{MECHANISM_SOURCES_REL}::mechanisms",
        },
        "covered_kinds": sorted(ROUTING_KINDS),
        "total_objects": total,
        "routed_objects": routed,
        "kinds": kinds,
        "incomplete": incomplete,
    }


def build_health(root: Path) -> dict[str, Any]:
    """
    Serialize `scripts.build_doctrine_enrichment_health.build_health` into the payload shape
    expected by scripts build doctrine enrichment health.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    enrichment_path = root / ENRICHMENT_REL
    enrichment = json.loads(enrichment_path.read_text(encoding="utf-8"))
    by_id: dict[str, dict[str, Any]] = {}
    for record in enrichment.get("records") or []:
        if isinstance(record, dict) and record.get("id"):
            by_id[str(record["id"])] = record

    kinds: dict[str, Any] = {}
    all_missing: list[dict[str, Any]] = []
    for kind in KIND_DIRS:
        corpus_ids = _corpus_ids(root, kind)
        enriched = [oid for oid in corpus_ids if oid in by_id]
        field_counts = {field: 0 for field in REQUIRED_FIELDS}
        for oid in enriched:
            record = by_id[oid]
            for field in REQUIRED_FIELDS:
                if _has_field(record, field):
                    field_counts[field] += 1
        unenriched = [oid for oid in corpus_ids if oid not in by_id]
        partial: list[dict[str, Any]] = []
        for oid in enriched:
            missing = [f for f in REQUIRED_FIELDS if not _has_field(by_id[oid], f)]
            if missing:
                partial.append({"id": oid, "missing_fields": missing})
                all_missing.append({"id": oid, "missing_fields": missing})
        kinds[kind] = {
            "total": len(corpus_ids),
            "enriched": len(enriched),
            "unenriched_ids": unenriched,
            "field_present_counts": field_counts,
            "partial_records": partial,
        }
        all_missing.extend({"id": oid, "missing_fields": ["<no enrichment record>"]} for oid in unenriched)

    total = sum(k["total"] for k in kinds.values())
    enriched_total = sum(k["enriched"] for k in kinds.values())
    routing_floor = _build_routing_floor(root)
    paper_module_readiness_audit = _build_paper_module_readiness_audit(root)
    coverage_complete = all(
        kinds[kind]["enriched"] == kinds[kind]["total"]
        and not kinds[kind]["partial_records"]
        for kind in kinds
    )

    # Formal-statement soundness: every symbol in a formula is defined and every
    # declared symbol is used. This is a structural check the coverage counts
    # cannot see (a record can have a `formal` field that renders yet declare a
    # dangling symbol or use an undefined operator). Correctness of the maths is
    # still reviewed, not counted; this only enforces symbol/formula agreement.
    sound = run_soundness(enrichment_path)
    soundness = {
        "checked": sound["total"],
        "sound": sound["clean"],
        "unsound": sound["defective"],
        "defects": [
            {
                "id": r["id"],
                "dangling": r["dangling"],
                "undefined_vars": r["undefined_vars"],
                "undefined_ops": r["undefined_ops"],
            }
            for r in sound["results"]
            if not r["clean"]
        ],
        "gate": "scripts/check_doctrine_formal_soundness.py",
        "note": "Symbol/formula agreement, not mathematical correctness; correctness is reviewed, not counted.",
    }
    # Reader-ladder accessibility: every object carries a plain reading and a
    # bounded analogy (plain + analogy.text + maps + boundary + why_it_matters +
    # potential_misread), with no laundering, banned visible term, or lay overclaim.
    # Like soundness, this is structural agreement, not a clarity score.
    ladder = run_reader_ladder(enrichment_path)
    reader_ladder = {
        "checked": ladder["total"],
        "sound": ladder["clean"],
        "unsound": ladder["defective"],
        "defects": [
            {"id": r["id"], "issues": r["issues"]}
            for r in ladder["results"]
            if not r["clean"]
        ],
        "gate": "scripts/check_doctrine_reader_ladder.py",
        "note": "Plain reading + bounded analogy present and laundering-free; analogy fidelity and boundary honesty are reviewed, not counted.",
    }
    # This expression folds EXACTLY the sections named in
    # COMPLETION_GATE_SECTIONS; the paper-module readiness audit is frontier
    # visibility and must not enter here without explicit standard promotion.
    complete = (
        coverage_complete
        and soundness["unsound"] == 0
        and reader_ladder["unsound"] == 0
        and routing_floor["status"] == "complete"
    )
    return {
        "schema_version": "microcosm_doctrine_enrichment_health_v1",
        "projection_role": PROJECTION_ROLE,
        "plane": PROJECTION_PLANE,
        "plane_note": PLANE_NOTE,
        "display_name": PROJECTION_DISPLAY_NAME,
        "source_of_record": ENRICHMENT_REL,
        "standard_ref": "standards/std_microcosm_doctrine_enrichment.json",
        "authority_boundary": "Typed multi-section health projection over reader enrichment, concept/mechanism routing floors, and a paper-module readiness frontier audit. Presence/structure, not correctness; never support evidence, proof authority, or release readiness. Generated; do not hand-edit.",
        "completion_gate_sections": list(COMPLETION_GATE_SECTIONS),
        "frontier_audit_sections": list(FRONTIER_AUDIT_SECTIONS),
        "sections": _section_model(),
        "status": "complete" if complete else "partial",
        "coverage_complete": coverage_complete,
        "total_objects": total,
        "enriched_objects": enriched_total,
        "reader_enrichment_total_objects": total,
        "reader_enrichment_complete": coverage_complete,
        "governed_floor_total_objects": total + routing_floor["total_objects"],
        "governed_floor_complete": complete,
        "kinds": kinds,
        "incomplete": all_missing,
        "routing_floor": routing_floor,
        "paper_module_readiness_audit": paper_module_readiness_audit,
        "formal_soundness": soundness,
        "reader_ladder": reader_ladder,
        "render_validation_note": "LaTeX render correctness is enforced by tools/meta/dissemination/tests/test_build_microcosm_public_site.py (zero raw-LaTeX fallbacks), not by this coverage projection.",
    }


def main(argv: list[str] | None = None) -> int:
    """
    Run `scripts.build_doctrine_enrichment_health` as a command-line entry point.

    - Teleology: expose the doctrine enrichment health projection as a CLI
      check/write surface for the public Plectis doctrine floor.
    - Mechanism: parse `--root`, `--write`, and `--check`; resolve the root;
      call `build_health`; optionally write `core/doctrine_enrichment_health.json`;
      print the projection for read/check runs; and return the completion
      status as a process code.
    - Guarantee: with complete source corpora, emits a .json
      `microcosm_doctrine_enrichment_health_v1` projection and returns 0 for
      `--check` only when the governed floor status is complete.
    - Fails: missing or malformed source JSON raises OSError/ValueError from
      the underlying reads; `--check` returns 1 when the generated health
      status is partial.
    - Reads: doctrine enrichment, axiom/principle/anti-principle receipt rows,
      concept/mechanism rows, paper-module rows, and the selected `--root`.
    - Writes: only `core/doctrine_enrichment_health.json`, and only when
      `--write` is passed.
    - Non-goal: does not prove doctrine correctness, support evidence,
      release readiness, proof authority, or private-root equivalence.
    """
    parser = argparse.ArgumentParser(prog="build_doctrine_enrichment_health")
    parser.add_argument("--root", type=Path, default=MICROCOSM_ROOT)
    parser.add_argument("--write", action="store_true", help="write the health projection")
    parser.add_argument("--check", action="store_true", help="fail if coverage is incomplete")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    health = build_health(root)
    if args.write:
        (root / HEALTH_REL).write_text(
            json.dumps(health, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if not args.write or args.check:
        print(json.dumps(health, ensure_ascii=True, indent=2, sort_keys=True))
    if args.check:
        return 0 if health["status"] == "complete" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
