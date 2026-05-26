"""
Audit standard-owned navigation contracts across Kind Atlas rows.

This is a read-only Type B metabolism surface: it compares the rung-0 atlas
with the contracts already declared by standards/profiles, while preserving
projection gaps instead of upgrading support by assertion.
"""
from __future__ import annotations

import json
import runpy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from system.lib.kind_atlas import build_kind_atlas


PAPER_MODULE_STANDARD = Path("codex/standards/std_paper_module.json")
SYSTEM_TERM_STANDARD = Path("codex/standards/std_system_term.json")
RAW_SEED_PRINCIPLES_STANDARD = Path("codex/standards/principles/std_raw_seed_principles.json")
PYTHON_STANDARD = Path("codex/standards/std_python.py")
COMPRESSION_PROFILES = Path("codex/doctrine/compression_profiles.json")
NAVIGATION_CONTRACT_STANDARD = Path("codex/standards/std_navigation_contract.json")
STANDARDS_REGISTRY_STANDARD = Path("codex/standards/std_standards_registry.json")
SYSTEM_ATLAS_STANDARD = Path("codex/standards/std_system_atlas.json")
WAVE_042_DIR = Path(
    "state/meta_missions/system_microcosm_probe/ledgers/"
    "navigation_hologram_microcosm/wave_042"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _navigation_contract_from_json(root: Path, path: Path) -> dict[str, Any] | None:
    contract = _load_json(root / path).get("navigation_contract")
    return contract if isinstance(contract, dict) else None


def _python_navigation_contract(root: Path) -> dict[str, Any] | None:
    path = root / PYTHON_STANDARD
    if not path.exists():
        return None
    try:
        namespace = runpy.run_path(str(path))
    except Exception:
        return None
    standard = namespace.get("PYTHON_STANDARD")
    if not isinstance(standard, dict):
        return None
    contract = standard.get("navigation_contract")
    return contract if isinstance(contract, dict) else None


def _raw_seed_profile_contract(root: Path) -> dict[str, Any] | None:
    data = _load_json(root / COMPRESSION_PROFILES)
    profiles = data.get("profiles")
    if not isinstance(profiles, list):
        return None
    for profile in profiles:
        if isinstance(profile, dict) and profile.get("profile_id") == "raw_seed_voice_context_v1":
            return profile
    return None


def _names_from_items(items: Any, key: str) -> list[str]:
    if not isinstance(items, list):
        return []
    names: list[str] = []
    for item in items:
        if isinstance(item, dict):
            raw = item.get(key) or item.get("id") or item.get("name")
        else:
            raw = item
        if raw:
            names.append(str(raw))
    return names


def _facet_names(contract: dict[str, Any]) -> list[str]:
    facets = contract.get("navigable_facets")
    if isinstance(facets, list):
        return _names_from_items(facets, "facet")
    facets = contract.get("telescope_facets")
    if not isinstance(facets, list):
        facets = (contract.get("facet_telescope_policy") or {}).get("facets")
    return _names_from_items(facets, "facet")


def _scope_names(contract: dict[str, Any]) -> list[str]:
    return _names_from_items(contract.get("navigable_scopes"), "scope")


def _bands(contract: dict[str, Any]) -> list[str]:
    raw = contract.get("navigable_bands") or contract.get("bands")
    return [str(item) for item in raw] if isinstance(raw, list) else []


def _population_policy(contract: dict[str, Any]) -> dict[str, Any]:
    policy = contract.get("population_policy")
    return policy if isinstance(policy, dict) else {}


def _population_mode_counts(policy: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in policy.values():
        if not isinstance(value, dict):
            continue
        mode = value.get("populated_by")
        if not mode:
            continue
        mode_str = str(mode)
        counts[mode_str] = counts.get(mode_str, 0) + 1
    return counts


def _unpopulated_units(policy: dict[str, Any]) -> list[str]:
    return [
        str(key)
        for key, value in policy.items()
        if isinstance(value, dict) and value.get("populated_by") == "unpopulated"
    ]


def _edge_compression_policy(contract: dict[str, Any]) -> dict[str, Any]:
    policy = contract.get("edge_compression_policy")
    return policy if isinstance(policy, dict) else {}


def _contract_row(
    *,
    atlas_row: dict[str, Any],
    status: str,
    contract_ref: str | None,
    contract: dict[str, Any] | None,
    draft: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = contract if isinstance(contract, dict) else draft or {}
    population_policy = _population_policy(source)
    edge_policy = _edge_compression_policy(source)
    return {
        "kind_id": atlas_row.get("kind_id"),
        "kind_title": atlas_row.get("title"),
        "kind_support_status": atlas_row.get("support_status"),
        "contract_status": status,
        "contract_ref": contract_ref,
        "profile_id": source.get("profile_id"),
        "navigable_bands": _bands(source),
        "band_contract_count": len(source.get("band_contracts") or {}) if isinstance(source.get("band_contracts"), dict) else 0,
        "navigable_scopes": _scope_names(source),
        "navigable_facets": _facet_names(source),
        "telescope_facets": _facet_names(source),
        "population_policy": population_policy,
        "population_mode_counts": _population_mode_counts(population_policy),
        "unpopulated_units": _unpopulated_units(population_policy),
        "edge_compression_policy": edge_policy,
        "has_bidirectional_edge_policy": edge_policy.get("bidirectional_gloss_required") is True,
        "axis_split_declared": bool(_bands(source) and _scope_names(source) and _facet_names(source)),
        "source_authority": source.get("source_authority"),
        "currentness_policy": source.get("currentness_policy"),
        "dependency_neighborhood_policy": source.get("dependency_neighborhood_policy"),
        "validation_probe": source.get("validation_probe"),
        "adapter_support_status_preserved": atlas_row.get("support_status"),
        "does_not_upgrade_option_surface_support": atlas_row.get("support_status") != "option_surface_supported",
        "profile_gap": atlas_row.get("profile_gap"),
        "evidence_refs": [contract_ref] if contract_ref else list(atlas_row.get("governing_standard_refs") or []),
    }


def _draft_contracts() -> dict[str, dict[str, Any]]:
    return {
        "standards": {
            "profile_id": "standards_navigation_candidate_v0",
            "navigable_bands": ["purpose", "contract", "schema", "validators"],
            "band_contracts": {"purpose": {}, "contract": {}, "schema": {}, "validators": {}},
            "telescope_facets": ["required_fields", "authority_split", "validator", "companion"],
            "navigable_scopes": ["standard", "companion", "registry_entry", "validator"],
            "navigable_facets": ["required_fields", "authority_split", "validator", "companion"],
            "population_policy": {
                "band:purpose": {"populated_by": "authored"},
                "band:contract": {"populated_by": "authored"},
                "band:schema": {"populated_by": "authored"},
                "band:validators": {"populated_by": "compiled"},
            },
            "edge_compression_policy": {
                "bidirectional_gloss_required": True,
                "first_order_band": "contract",
                "second_order_band": "purpose",
                "beyond_second_order": "omit_with_count_reason_and_drilldown",
            },
            "source_authority": {"source": "codex/standards/std_*.json plus companion std_*.md"},
            "currentness_policy": {"mode": "source_walk_plus_companion_drift_audit"},
            "dependency_neighborhood_policy": {"mode": "registry_and_core_authority_index"},
            "validation_probe": ["std JSON parses", "companion drift audit passes or emits row jobs"],
        },
        "frontend_views": {
            "profile_id": "frontend_view_navigation_candidate_v0",
            "navigable_bands": ["route_id", "purpose", "component_tree", "source_capture"],
            "band_contracts": {"route_id": {}, "purpose": {}, "component_tree": {}, "source_capture": {}},
            "telescope_facets": ["route", "actor", "state", "capture"],
            "navigable_scopes": ["route", "view", "interaction_state", "source_file"],
            "navigable_facets": ["route", "actor", "state", "capture"],
            "population_policy": {
                "band:route_id": {"populated_by": "compiled"},
                "band:purpose": {"populated_by": "compiled"},
                "band:component_tree": {"populated_by": "compiled"},
                "band:source_capture": {"populated_by": "live_computed"},
            },
            "edge_compression_policy": {
                "bidirectional_gloss_required": True,
                "first_order_band": "component_tree",
                "second_order_band": "route_id",
                "beyond_second_order": "omit_with_count_reason_and_drilldown",
            },
            "source_authority": {"source": "frontend navigation graph plus TS/TSX source"},
            "currentness_policy": {"mode": "navigation_graph_option_surface_adapter"},
            "dependency_neighborhood_policy": {"mode": "route_to_component_edges"},
            "validation_probe": ["view graph exists", "component refs resolve"],
        },
        "frontend_components": {
            "profile_id": "frontend_component_navigation_candidate_v0",
            "navigable_bands": ["component_id", "purpose", "props_state", "source"],
            "band_contracts": {"component_id": {}, "purpose": {}, "props_state": {}, "source": {}},
            "telescope_facets": ["props", "state", "children", "view_ownership"],
            "navigable_scopes": ["component", "file", "prop", "state_slice"],
            "navigable_facets": ["props", "state", "children", "view_ownership"],
            "population_policy": {
                "band:component_id": {"populated_by": "compiled"},
                "band:purpose": {"populated_by": "unpopulated", "reason": "Component purpose remains unauthored; the regex-based extractor only emits classification metadata."},
                "band:props_state": {"populated_by": "unpopulated", "reason": "The current extractor does not parse TSX prop/state contracts."},
                "band:source": {"populated_by": "live_computed"},
            },
            "edge_compression_policy": {
                "bidirectional_gloss_required": True,
                "first_order_band": "props_state",
                "second_order_band": "component_id",
                "beyond_second_order": "omit_with_count_reason_and_drilldown",
            },
            "source_authority": {"source": "state/frontend_navigation/component_index.json"},
            "currentness_policy": {"mode": "frontend_component_index_option_surface_adapter"},
            "dependency_neighborhood_policy": {"mode": "imports_and_view_ownership"},
            "validation_probe": ["frontend component index projection exists", "component_id resolves to source span"],
        },
        "skills": {
            "profile_id": "skill_navigation_candidate_v0",
            "navigable_bands": ["triggers", "card", "workflow", "evidence"],
            "band_contracts": {"triggers": {}, "card": {}, "workflow": {}, "evidence": {}},
            "telescope_facets": ["trigger", "transition", "anti_pattern", "receipt"],
            "navigable_scopes": ["skill", "step", "composition_edge", "receipt"],
            "navigable_facets": ["trigger", "transition", "anti_pattern", "receipt"],
            "population_policy": {
                "band:triggers": {"populated_by": "authored"},
                "band:card": {"populated_by": "authored"},
                "band:workflow": {"populated_by": "authored"},
                "band:evidence": {"populated_by": "compiled"},
            },
            "edge_compression_policy": {
                "bidirectional_gloss_required": True,
                "first_order_band": "workflow",
                "second_order_band": "triggers",
                "beyond_second_order": "omit_with_count_reason_and_drilldown",
            },
            "source_authority": {"source": "codex/doctrine/skills/skill_registry.json and SKILL.md files"},
            "currentness_policy": {"mode": "registry_plus_file_mtime"},
            "dependency_neighborhood_policy": {"mode": "composes_with_and_related_doctrine"},
            "validation_probe": ["skill registry row resolves to file", "declared triggers are browse-safe"],
        },
        "axiom_candidates": {
            "profile_id": "axiom_candidate_navigation_candidate_v0",
            "navigable_bands": ["tiny", "flag", "card", "context", "deep"],
            "band_contracts": {"tiny": {}, "flag": {}, "card": {}, "context": {}, "deep": {}},
            "telescope_facets": [
                "formal_clause",
                "dense_clause",
                "violation_predicates",
                "related_principles",
                "russian_doll_exemplar_chain",
            ],
            "navigable_scopes": ["candidate_axiom", "violation_predicate", "related_principle", "exemplar_chain"],
            "navigable_facets": [
                "formal_clause",
                "dense_clause",
                "violation_predicates",
                "related_principles",
                "russian_doll_exemplar_chain",
            ],
            "population_policy": {
                "band:tiny": {"populated_by": "authored"},
                "band:flag": {"populated_by": "authored"},
                "band:card": {"populated_by": "authored"},
                "band:context": {"populated_by": "authored"},
                "band:deep": {"populated_by": "authored"},
            },
            "edge_compression_policy": {
                "bidirectional_gloss_required": True,
                "first_order_band": "context",
                "second_order_band": "flag",
                "beyond_second_order": "omit_with_count_reason_and_drilldown",
            },
            "source_authority": {"source": "raw_seed/system_axiom_candidates.json"},
            "currentness_policy": {"mode": "candidate_not_active_doctrine_with_live_principle_links"},
            "dependency_neighborhood_policy": {"mode": "related_principles_and_governed_planes"},
            "validation_probe": ["candidate remains not active doctrine", "evidence refs resolve"],
        },
        "compression_profiles": {
            "profile_id": "compression_profile_navigation_candidate_v0",
            "navigable_bands": ["profile_id", "bands", "band_contracts", "source_ladder"],
            "band_contracts": {"profile_id": {}, "bands": {}, "band_contracts": {}, "source_ladder": {}},
            "telescope_facets": ["mandatory_preserve", "allowed_loss", "forbidden_collapse", "worker_tier_policy"],
            "navigable_scopes": ["profile", "band_contract", "source_ladder", "worker_tier_policy"],
            "navigable_facets": ["mandatory_preserve", "allowed_loss", "forbidden_collapse", "worker_tier_policy"],
            "population_policy": {
                "band:profile_id": {"populated_by": "authored"},
                "band:bands": {"populated_by": "authored"},
                "band:band_contracts": {"populated_by": "authored"},
                "band:source_ladder": {"populated_by": "authored"},
            },
            "edge_compression_policy": {
                "bidirectional_gloss_required": True,
                "first_order_band": "band_contracts",
                "second_order_band": "profile_id",
                "beyond_second_order": "omit_with_count_reason_and_drilldown",
            },
            "source_authority": {"source": "codex/doctrine/compression_profiles.json"},
            "currentness_policy": {"mode": "profile_registry_parse_plus_skill_refs"},
            "dependency_neighborhood_policy": {"mode": "creator_skill_and_navigator_skill"},
            "validation_probe": ["profile ids unique", "band contracts match declared bands"],
        },
        "annex_patterns": {
            "profile_id": "annex_pattern_navigation_candidate_v0",
            "navigable_bands": ["flag", "card", "family", "contents", "pattern_notes", "source"],
            "band_contracts": {
                "flag": {},
                "card": {},
                "family": {},
                "contents": {},
                "pattern_notes": {},
                "source": {},
            },
            "telescope_facets": ["provenance", "local_translation", "adoption_boundary", "source_fingerprint"],
            "navigable_scopes": ["annex_family", "annex_note", "pattern_transfer", "source_ref"],
            "navigable_facets": ["provenance", "local_translation", "adoption_boundary", "source_fingerprint"],
            "population_policy": {
                "band:flag": {"populated_by": "compiled"},
                "band:card": {"populated_by": "compiled"},
                "band:family": {"populated_by": "authored"},
                "band:contents": {"populated_by": "compiled"},
                "band:pattern_notes": {"populated_by": "authored"},
                "band:source": {"populated_by": "live_computed"},
            },
            "edge_compression_policy": {
                "bidirectional_gloss_required": True,
                "first_order_band": "pattern_notes",
                "second_order_band": "family",
                "beyond_second_order": "omit_with_count_reason_and_drilldown",
            },
            "source_authority": {"source": "annexes/<slug>/annex_notes.json and external source refs"},
            "currentness_policy": {"mode": "annex_notes_option_surface_adapter_plus_external_snapshot"},
            "dependency_neighborhood_policy": {"mode": "pattern_transferred_to_local_targets"},
            "validation_probe": ["annex notes parse", "local transfer keeps source/provenance boundary"],
        },
    }


def _declared_contracts(root: Path) -> dict[str, tuple[str, str, dict[str, Any]]]:
    contracts: dict[str, tuple[str, str, dict[str, Any]]] = {}
    for kind_id, path in (
        ("paper_modules", PAPER_MODULE_STANDARD),
        ("standards", STANDARDS_REGISTRY_STANDARD),
        ("system_terms", SYSTEM_TERM_STANDARD),
        ("principles", RAW_SEED_PRINCIPLES_STANDARD),
        ("system_atlas", SYSTEM_ATLAS_STANDARD),
    ):
        contract = _navigation_contract_from_json(root, path)
        if contract:
            contracts[kind_id] = ("declared", str(path) + "::navigation_contract", contract)
    python_contract = _python_navigation_contract(root)
    if python_contract:
        contracts["python_files"] = ("declared", str(PYTHON_STANDARD) + "::PYTHON_STANDARD.navigation_contract", python_contract)
        contracts["python_scopes"] = ("declared", str(PYTHON_STANDARD) + "::PYTHON_STANDARD.navigation_contract", python_contract)
    raw_seed_contract = _raw_seed_profile_contract(root)
    if raw_seed_contract and raw_seed_contract.get("facet_telescope_policy"):
        contracts["raw_seed_shards"] = (
            "profile_declared",
            str(COMPRESSION_PROFILES) + "::raw_seed_voice_context_v1",
            raw_seed_contract,
        )
    return contracts


def build_kind_band_contract_audit(repo_root: Path | str) -> dict[str, Any]:
    """Build a read-only audit of Kind Atlas rows vs declared navigation contracts."""
    root = Path(repo_root)
    generated_at = _utc_now()
    atlas = build_kind_atlas(root, band="card")
    atlas_rows = atlas.get("rows") if isinstance(atlas.get("rows"), list) else []
    declared = _declared_contracts(root)
    drafts = _draft_contracts()
    rows: list[dict[str, Any]] = []
    for atlas_row in atlas_rows:
        kind_id = str(atlas_row.get("kind_id") or "")
        if kind_id in declared:
            status, ref, contract = declared[kind_id]
            rows.append(_contract_row(atlas_row=atlas_row, status=status, contract_ref=ref, contract=contract))
        elif kind_id in drafts:
            rows.append(
                _contract_row(
                    atlas_row=atlas_row,
                    status="drafted_candidate",
                    contract_ref=None,
                    contract=None,
                    draft=drafts[kind_id],
                )
            )
        else:
            rows.append(
                _contract_row(
                    atlas_row=atlas_row,
                    status="missing",
                    contract_ref=None,
                    contract=None,
                    draft={
                        "navigable_bands": [],
                        "navigable_scopes": [],
                        "navigable_facets": [],
                        "telescope_facets": [],
                        "population_policy": {},
                    },
                )
            )
    status_counts: dict[str, int] = {}
    population_policy_rows = 0
    unpopulated_unit_count = 0
    axis_split_rows = 0
    for row in rows:
        status_counts[str(row["contract_status"])] = status_counts.get(str(row["contract_status"]), 0) + 1
        if row.get("population_policy"):
            population_policy_rows += 1
            unpopulated_unit_count += len(row.get("unpopulated_units") or [])
        if row.get("axis_split_declared"):
            axis_split_rows += 1
    return {
        "kind": "kind_band_contract_audit",
        "schema_version": "kind_band_contract_audit_v1",
        "generated_at": generated_at,
        "authority_posture": "read_only_currentness_audit_not_generic_row_support",
        "governing_standard": str(NAVIGATION_CONTRACT_STANDARD),
        "source_refs": [
            str(NAVIGATION_CONTRACT_STANDARD),
            "codex/standards/std_kind_atlas.json",
            str(PAPER_MODULE_STANDARD),
            str(SYSTEM_TERM_STANDARD),
            str(RAW_SEED_PRINCIPLES_STANDARD),
            str(PYTHON_STANDARD),
            str(COMPRESSION_PROFILES),
            str(STANDARDS_REGISTRY_STANDARD),
            str(SYSTEM_ATLAS_STANDARD),
        ],
        "summary": {
            "total_kinds": len(rows),
            "contract_status_counts": status_counts,
            "declared_count": status_counts.get("declared", 0),
            "profile_declared_count": status_counts.get("profile_declared", 0),
            "drafted_candidate_count": status_counts.get("drafted_candidate", 0),
            "missing_count": status_counts.get("missing", 0),
            "axis_split_rows": axis_split_rows,
            "population_policy_rows": population_policy_rows,
            "unpopulated_unit_count": unpopulated_unit_count,
            "generic_row_command_implemented": True,
            "generic_row_command_ref": "./repo-python kernel.py --row KIND:ID --band BAND",
            "generic_row_command_governing_standard": "codex/standards/std_command_output_projection.json",
            "generic_row_command_safety_rule": (
                "Refuses unpopulated bands honestly via row_band_unavailable; never synthesizes "
                "context/deep over un-routed substrate (Phase 09.45 reversal anchor: "
                "par_phase_09_raw_seed__naming_a_structural_drift_signal_is_not_the_same_as_routing_it_003)."
            ),
            "option_surface_support_upgraded_by_this_audit": False,
        },
        "navigation_boundary": {
            "query_used": False,
            "atlas_first": True,
            "band_names_are_kind_native": True,
            "telescope_aliases": ["telescope", "Russian doll", "holographic tiered compression"],
            "non_goal": "Do not infer a working --telescope adapter from a declared navigation_contract.",
        },
        "rows": rows,
    }
