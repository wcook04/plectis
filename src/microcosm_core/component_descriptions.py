"""Join structural atlas rows to their canonical capsule descriptions.

Capsule compression owns reader-facing descriptions. The atlas still owns
structure, commands and routing; registry claim_ceiling remains normative and
is deliberately outside this reader. No generated view or stale atlas gloss is
used as a fallback. Results are fresh, detached in-memory compatibility views.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

ATLAS_REF = "core/organ_atlas.json"
CAPSULES_REF = "core/paper_module_capsules.json"
DESCRIPTION_FIELDS = ("human_gloss", "agent_gloss", "claim_ceiling_restated")


class ComponentDescriptionError(ValueError):
    """A canonical component description cannot be resolved unambiguously."""


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def capsule_index(capsules: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index explicit IDs and supported guide refs, rejecting all collisions.

    Organ subjects are checked by the resolver, rather than inserted with
    first-match semantics: multiple modules may discuss the same organ.
    """
    index: dict[str, dict[str, Any]] = {}
    for row in capsules:
        if not isinstance(row, dict) or not _text(row.get("id")):
            raise ComponentDescriptionError("capsule_missing_id")
        capsule_id = _text(row["id"])
        if row["id"] != capsule_id:
            raise ComponentDescriptionError(f"noncanonical_capsule_id:{row['id']!r}")
        keys = {capsule_id, f"{CAPSULES_REF}#{capsule_id}"}
        projection = _text(row.get("legacy_markdown_projection"))
        if projection:
            keys.add(projection)
        for key in keys:
            if key in index:
                raise ComponentDescriptionError(f"duplicate_capsule_key:{key}")
            index[key] = row
    return index


def _organ_subjects(capsule: dict[str, Any]) -> set[str]:
    if not isinstance(capsule.get("subjects", []), list):
        raise ComponentDescriptionError(f"invalid_capsule_subjects:{capsule['id']}")
    if any(not isinstance(subject, dict) or (
        subject.get("kind") == "organ" and not _text(subject.get("ref"))
    ) for subject in capsule.get("subjects", [])):
        raise ComponentDescriptionError(f"invalid_capsule_subjects:{capsule['id']}")
    return {
        _text(subject.get("ref"))
        for subject in capsule.get("subjects", [])
        if isinstance(subject, dict) and subject.get("kind") == "organ"
        and _text(subject.get("ref"))
    }


def capsule_for_atlas_row(
    organ_id: str, row: dict[str, Any], index: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], str]:
    """Reuse atlas ID/guide-ref resolution with an explicit, checked primary.

    Explicit refs never fall back to a similarly named ID or subject. Without
    an explicit ref, only the original direct paper_module.<organ_id> identity
    is admissible, and ambiguous subject declarations block it.
    """
    declared = _text(row.get("paper_module_ref"))
    if declared:
        capsule = index.get(declared)
        if capsule is None:
            raise ComponentDescriptionError(f"unresolved_capsule_ref:{organ_id}:{declared}")
    else:
        candidates = {
            _text(candidate.get("id")): candidate
            for candidate in index.values() if organ_id in _organ_subjects(candidate)
        }
        if len(candidates) > 1:
            raise ComponentDescriptionError(f"ambiguous_organ_capsule:{organ_id}")
        capsule = index.get(f"paper_module.{organ_id}")
        if capsule is None:
            raise ComponentDescriptionError(f"missing_capsule_ref:{organ_id}")
    organ_subjects = _organ_subjects(capsule)
    if organ_id not in organ_subjects and (organ_subjects or not declared):
        raise ComponentDescriptionError(f"capsule_subject_mismatch:{organ_id}:{capsule['id']}")
    compression = capsule.get("compression")
    for field in ("one_line", "card", "authority_ceiling"):
        if not isinstance(compression, dict) or not _text(compression.get(field)):
            raise ComponentDescriptionError(f"missing_capsule_compression:{organ_id}:{field}")
    status = "direct" if capsule["id"] == f"paper_module.{organ_id}" else "paper_module_ref_bridge"
    return capsule, status


def resolve_component_capsules(
    atlas_rows: list[dict[str, Any]], capsules: list[dict[str, Any]],
) -> dict[str, tuple[dict[str, Any], str]]:
    """Return one validated canonical capsule and stable join status per organ."""
    index = capsule_index(capsules)
    resolved: dict[str, tuple[dict[str, Any], str]] = {}
    for row in atlas_rows:
        if not isinstance(row, dict) or not _text(row.get("organ_id")):
            raise ComponentDescriptionError("atlas_missing_organ_id")
        organ_id = _text(row["organ_id"])
        if row["organ_id"] != organ_id:
            raise ComponentDescriptionError(f"noncanonical_organ_id:{row['organ_id']!r}")
        if organ_id in resolved:
            raise ComponentDescriptionError(f"duplicate_atlas_organ_id:{organ_id}")
        resolved[organ_id] = capsule_for_atlas_row(organ_id, row, index)
    return resolved


def enrich_description_atlas(
    atlas: dict[str, Any], capsules: dict[str, Any],
) -> dict[str, Any]:
    """Return the compatibility atlas without persisting duplicate authored text."""
    if not isinstance(atlas, dict) or not isinstance(atlas.get("organs"), list):
        raise ComponentDescriptionError("missing_atlas_organs")
    if not isinstance(capsules, dict) or not isinstance(capsules.get("paper_modules"), list):
        raise ComponentDescriptionError("missing_paper_module_capsules")
    resolved = resolve_component_capsules(atlas["organs"], capsules["paper_modules"])
    result = deepcopy(atlas)
    for row in result["organs"]:
        capsule, status = resolved[row["organ_id"]]
        compression = capsule["compression"]
        row.update(
            human_gloss=compression["card"], agent_gloss=compression["card"],
            claim_ceiling_restated=compression["authority_ceiling"],
            one_line=compression["one_line"], card=compression["card"],
            authority_ceiling=compression["authority_ceiling"],
            compression_card=compression["card"],
            compression_authority_ceiling=compression["authority_ceiling"],
            capsule_id=capsule["id"], capsule_join_status=status,
            capsule_subject_status=(
                "declared_organ_match" if row["organ_id"] in _organ_subjects(capsule)
                else "explicit_ref_subject_unrecorded"
            ),
            capsule_legacy_markdown_projection=capsule.get("legacy_markdown_projection", ""),
            description_source_ref=f"{CAPSULES_REF}#{capsule['id']}",
            description_source_fields={
                "human_gloss": "compression.card", "agent_gloss": "compression.card",
                "claim_ceiling_restated": "compression.authority_ceiling",
                "one_line": "compression.one_line",
            },
            description_join_ref=row.get("paper_module_ref") or f"paper_module.{row['organ_id']}",
        )
    return result


def load_description_atlas(root: str | Path, *, atlas_path: str | Path | None = None) -> dict[str, Any]:
    """Read both current source files on every invocation; no process-global cache."""
    from microcosm_core.schemas import read_json_strict

    root = Path(root)
    return enrich_description_atlas(
        read_json_strict(Path(atlas_path) if atlas_path is not None else root / ATLAS_REF),
        read_json_strict(root / CAPSULES_REF),
    )


def enrich_organ_route_rows(payload: Any, atlas: dict[str, Any]) -> Any:
    """Refresh descriptive fields in generated route rows, preserving route structure.

    Only existing organ rows and description keys are refreshed. Route commands,
    normative claim_ceiling, task-level allowed scopes and identities stay intact.
    """
    by_id = {row["organ_id"]: row for row in atlas["organs"]}
    fields = (*DESCRIPTION_FIELDS, "one_line", "card", "authority_ceiling",
              "capsule_id", "capsule_join_status", "description_source_ref")

    def visit(value: Any) -> Any:
        if isinstance(value, list):
            return [visit(item) for item in value]
        if not isinstance(value, dict):
            return value
        result = {key: visit(item) for key, item in value.items()}
        organ_id = result.get("organ_id")
        if isinstance(organ_id, str) and organ_id in by_id:
            source = by_id[organ_id]
            has_description = any(field in result for field in DESCRIPTION_FIELDS + ("one_line", "card", "authority_ceiling"))
            for field in fields:
                if field in result:
                    result[field] = deepcopy(source[field])
            if has_description:
                for field in ("one_line", "card", "authority_ceiling"):
                    result[field] = source[field]
            result["description_source_ref"] = source["description_source_ref"]
        return result

    return visit(payload)
