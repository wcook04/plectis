"""
Compile a Rosetta-style navigation context packet from Kind Atlas contracts.

This is a read-only proof surface. It does not implement a generic --row or
--telescope command; it demonstrates how the standard-owned grammar can choose
representative rows and compression bands under a bounded context budget.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from system.lib.kind_atlas import build_kind_atlas
from system.lib.kind_band_contract_audit import build_kind_band_contract_audit
from system.lib.standard_option_surface import build_option_surface


WAVE_044_DIR = Path(
    "state/meta_missions/system_microcosm_probe/ledgers/"
    "navigation_hologram_microcosm/wave_044"
)


REPRESENTATIVE_FIXTURES: dict[str, dict[str, Any]] = {
    "paper_modules": {
        "row_ref": "paper_module:navigation_hologram_theory",
        "source_ref": "codex/doctrine/paper_modules/navigation_hologram_theory.md",
        "evidence_command": "./repo-python kernel.py --paper-module navigation_hologram_theory",
        "why": "Representative theory surface with authored facets, option rows, dependency edges, and currentness-bearing projections.",
    },
    "standards": {
        "row_ref": "standard:std_navigation_contract",
        "source_ref": "codex/standards/std_navigation_contract.json",
        "evidence_command": "./repo-python kernel.py --option-surface standards --band card --ids std_navigation_contract",
        "why": "Representative grammar standard for reading artifact kinds through bands/scopes/facets/population policy.",
    },
    "python_files": {
        "row_ref": "python_file:system/lib/kind_band_contract_audit.py",
        "source_ref": "system/lib/kind_band_contract_audit.py",
        "evidence_command": "sed -n '1,220p' system/lib/kind_band_contract_audit.py",
        "why": "Representative Python source file that consumes contract grammar but still lacks a production option surface.",
    },
    "python_scopes": {
        "row_ref": "python_scope:system.lib.kind_band_contract_audit.build_kind_band_contract_audit",
        "source_ref": "system/lib/kind_band_contract_audit.py",
        "evidence_command": "rg -n 'def build_kind_band_contract_audit' system/lib/kind_band_contract_audit.py",
        "why": "Representative Python symbol scope; its declared symbol_capsule band remains unpopulated until an emitter exists.",
    },
    "frontend_views": {
        "row_ref": "frontend_view:station",
        "source_ref": "state/frontend_navigation/navigation_graph.json",
        "evidence_command": "./repo-python kernel.py --view-graph",
        "why": "Representative legacy frontend navigation row; visible but not standard-owned yet.",
    },
    "frontend_components": {
        "row_ref": "frontend_component:App",
        "source_ref": "system/server/ui/src/App.tsx",
        "evidence_command": "sed -n '1,180p' system/server/ui/src/App.tsx",
        "why": "Representative frontend component source; component purpose/props bands remain projection gaps.",
    },
    "skills": {
        "row_ref": "skill:system_microcosm_probe",
        "source_ref": "codex/doctrine/skills/doctrine/system_microcosm_probe.md",
        "evidence_command": "./repo-python kernel.py --skill-find system_microcosm_probe",
        "why": "Representative procedural transition surface with workflow, anti-patterns, and receipts.",
    },
    "system_terms": {
        "row_ref": "term:living_system_posture",
        "source_ref": "codex/doctrine/system_vocabulary/term_registry.json",
        "evidence_command": "./repo-python kernel.py --term living_system_posture --term-band context",
        "why": "Representative lexical ladder where the same concept expands from word to deep band.",
    },
    "principles": {
        "row_ref": "principle:pri_125",
        "source_ref": "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/raw_seed_principles.json",
        "evidence_command": "jq '.principles[] | select(.id==\"pri_125\")' 'obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/raw_seed_principles.json'",
        "why": "Representative active doctrine row with tests, edges, evidence, and discovery posture.",
    },
    "axiom_candidates": {
        "row_ref": "axiom_candidate:meaning_is_relational",
        "source_ref": "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/system_axiom_candidates.json",
        "evidence_command": "jq '.axiom_candidates[] | select(.slug==\"meaning-is-relational\")' 'obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/system_axiom_candidates.json'",
        "why": "Representative constitutional candidate that constrains compression and edge neighborhoods without becoming active doctrine.",
    },
    "raw_seed_shards": {
        "row_ref": "raw_seed_shard:profile_declared_fixture",
        "source_ref": "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/raw_seed_shards.json",
        "evidence_command": "./repo-python kernel.py --shards --shards-status extracted --shards-limit 1",
        "why": "Representative voice-derived shard surface governed through raw_seed_voice_context_v1.",
    },
    "compression_profiles": {
        "row_ref": "compression_profile:raw_seed_voice_context_v1",
        "source_ref": "codex/doctrine/compression_profiles.json",
        "evidence_command": "jq '.profiles[] | select(.profile_id==\"raw_seed_voice_context_v1\")' codex/doctrine/compression_profiles.json",
        "why": "Representative profile that already declares raw-seed bands, facets, population, and telescope policy.",
    },
    "annex_patterns": {
        "row_ref": "annex_pattern:repo-intelligence-graph",
        "source_ref": "annexes/repo-intelligence-graph/annex_notes.json",
        "evidence_command": "jq '.notes[0:3]' annexes/repo-intelligence-graph/annex_notes.json",
        "why": "Representative external prior-art pattern for deterministic repo maps and evidence-backed row injection.",
    },
    "annex_distillation_patterns": {
        "row_ref": "annex_distillation_pattern:agentic-stack:p005",
        "source_ref": "annexes/annex_distillation_index.json",
        "evidence_command": "./repo-python kernel.py --option-surface annex_distillation_patterns --band flag",
        "why": "Representative annex-distilled pattern (progressive-disclosure skill index) showing how cross-annex pattern rows are mined into a typed option surface; covers the 14th Kind Atlas row that emerged after the original 13-kind fixture set was authored.",
    },
    "transform_job_receipts": {
        "row_ref": "transform_job_receipt:rc_13231a67ef8b44a6",
        "source_ref": "state/compute_workers/receipts/2026-04/rc_13231a67ef8b44a6.json",
        "evidence_command": "./repo-python kernel.py --row transform_job_receipts:rc_13231a67ef8b44a6 --band card",
        "why": "Representative generated compute receipt showing provider, task class, validation, and promotion state as a navigable artifact row.",
    },
    "row_patches": {
        "row_ref": "row_patch:rp_0f140fe32d4c4bfa",
        "source_ref": "state/compute_workers/row_patches/2026-04/rp_0f140fe32d4c4bfa.json",
        "evidence_command": "./repo-python kernel.py --row row_patches:rp_0f140fe32d4c4bfa --band card",
        "why": "Representative generated row patch binding a compute receipt to a target row, target facet, validation status, and promotion state.",
    },
    "compliance_ledger": {
        "row_ref": "compliance_ledger:std_paper_module",
        "source_ref": "codex/hologram/compliance/ledger.json",
        "evidence_command": "./repo-python kernel.py --row compliance_ledger:std_paper_module --band card",
        "why": "Representative generated compliance row showing standard coverage, validator authority, and trigger state.",
    },
    "standard_skill_map": {
        "row_ref": "standard_skill_map:std_skill",
        "source_ref": "codex/hologram/skills/standard_skill_map.json",
        "evidence_command": "./repo-python kernel.py --row standard_skill_map:std_skill --band card",
        "why": "Representative standard-to-skill pairing row showing whether a standard has an authoring skill or is tool-owned.",
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _row_by(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(row.get(key) or ""): row for row in rows}


def _support_factor(status: str) -> float:
    return {
        "option_surface_supported": 1.0,
        "legacy_command_only": 0.72,
        "projection_gap": 0.55,
    }.get(status, 0.45)


def _axis_coverage(row: dict[str, Any]) -> float:
    checks = [
        bool(row.get("navigable_bands")),
        bool(row.get("navigable_scopes")),
        bool(row.get("navigable_facets")),
        bool(row.get("population_policy")),
        bool(row.get("edge_compression_policy")),
    ]
    return sum(1 for value in checks if value) / len(checks)


def _population_factor(row: dict[str, Any]) -> float:
    counts = row.get("population_mode_counts") if isinstance(row.get("population_mode_counts"), dict) else {}
    total = sum(int(value) for value in counts.values() if isinstance(value, int))
    if total <= 0:
        return 0.4
    unpopulated = int(counts.get("unpopulated") or 0)
    return max(0.15, 1.0 - 0.5 * (unpopulated / total))


def _count_signal(row_count: Any, max_count: int) -> float:
    try:
        count = max(0, int(row_count))
    except (TypeError, ValueError):
        count = 0
    if max_count <= 1:
        return 0.0
    return math.log1p(count) / math.log1p(max_count)


def _row_count_int(atlas_row: dict[str, Any]) -> int:
    try:
        return max(0, int(atlas_row.get("row_count") or 0))
    except (TypeError, ValueError):
        return 0


def _population_mode(atlas_row: dict[str, Any]) -> str:
    if atlas_row.get("profile_gap"):
        return "unpopulated"
    if _row_count_int(atlas_row) <= 0:
        return "unpopulated"
    return "compiled"


def _confidence_for(atlas_row: dict[str, Any], population_mode: str) -> dict[str, Any]:
    if atlas_row.get("profile_gap"):
        return {
            "tier": "medium",
            "score": 0.62,
            "reason": "Representative atom emitted from the current Kind Atlas and contract audit; profile gaps lower projection confidence but stay visible for coverage.",
            "scorer_status": "heuristic_v0",
        }
    if population_mode == "unpopulated":
        return {
            "tier": "low",
            "score": 0.48,
            "reason": "The kind is registered and selectable, but the live option surface currently has zero rows; coverage keeps the kind visible without claiming a representative row.",
            "scorer_status": "heuristic_v0",
        }
    return {
        "tier": "high",
        "score": 0.86,
        "reason": "Representative atom emitted from the current Kind Atlas and contract audit; populated option surfaces can carry representative row_refs.",
        "scorer_status": "heuristic_v0",
    }


def _representative_fixture_for(
    fixture: dict[str, Any],
    *,
    population_mode: str,
    row_count: int,
) -> tuple[dict[str, Any], str | None]:
    representative = dict(fixture)
    row_ref = representative.get("row_ref")
    if population_mode == "unpopulated" and row_count <= 0:
        if row_ref:
            representative["candidate_row_ref"] = row_ref
        representative.pop("row_ref", None)
        row_ref = None
    return representative, str(row_ref) if row_ref else None


def _row_identifier(row: dict[str, Any]) -> str:
    for field in (
        "cluster_id",
        "candidate_id",
        "concept_id",
        "mechanism_id",
        "imagination_id",
        "skill_id",
        "standard_id",
        "term_id",
        "principle_id",
        "axiom_candidate_id",
        "profile_id",
        "receipt_id",
        "patch_id",
        "projection_id",
        "anti_pattern_id",
        "slug",
        "id",
        "row_id",
    ):
        value = row.get(field)
        if value:
            return str(value)
    return ""


def _generic_representative_fixture(
    repo_root: Path,
    kind_id: str,
    atlas_row: dict[str, Any],
) -> dict[str, Any]:
    row_count = _row_count_int(atlas_row)
    if row_count <= 0:
        return {}
    bands = atlas_row.get("bands") if isinstance(atlas_row.get("bands"), list) else []
    band = "cluster_flag" if "cluster_flag" in bands and row_count > 50 else "flag"
    try:
        payload = build_option_surface(repo_root, kind_id, band=band)
    except Exception:
        return {}
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    if not rows:
        return {}
    row = rows[0] if isinstance(rows[0], dict) else {}
    stable_id = _row_identifier(row)
    if not stable_id:
        return {}
    source_ref = (
        row.get("source_ref")
        or row.get("authority_path")
        or (payload.get("source_refs") or [None])[0]
        or "<option_surface_row>"
    )
    evidence_command = (
        row.get("evidence_command")
        or row.get("drilldown_command")
        or row.get("card_drilldown_command")
        or atlas_row.get("evidence_command")
    )
    return {
        "row_ref": f"{kind_id}:{stable_id}",
        "source_ref": source_ref,
        "evidence_command": evidence_command,
        "why": (
            f"Representative selected from the {kind_id} {band} option surface; "
            "this avoids hand-maintained Rosetta fixtures for every populated artifact kind."
        ),
        "selection_band": band,
    }


def _band_cost(contract_row: dict[str, Any], band: str) -> int:
    scope_count = len(contract_row.get("navigable_scopes") or [])
    facet_count = len(contract_row.get("navigable_facets") or [])
    unpopulated_count = len(contract_row.get("unpopulated_units") or [])
    base = 42 + 2 * scope_count + 2 * facet_count + 5 * unpopulated_count
    if band == "card":
        return base + 82
    return base


def _coverage_floor_cost(kind_id: str, contract_row: dict[str, Any]) -> int:
    if kind_id == "system_microcosm":
        return 1
    if kind_id == "artifact_projection_debt":
        return 1
    if kind_id == "github_import_candidates":
        return 1
    return _band_cost(contract_row, "flag")


def _kind_utility(atlas_row: dict[str, Any], contract_row: dict[str, Any]) -> dict[str, float]:
    row_count = atlas_row.get("row_count") or 0
    support = _support_factor(str(atlas_row.get("support_status") or ""))
    axis = _axis_coverage(contract_row)
    population = _population_factor(contract_row)
    return {
        "support_factor": round(support, 4),
        "axis_coverage": round(axis, 4),
        "population_factor": round(population, 4),
        "row_count": float(row_count or 0),
    }


def _base_utility(atlas_row: dict[str, Any], contract_row: dict[str, Any], max_row_count: int) -> float:
    factors = _kind_utility(atlas_row, contract_row)
    count = _count_signal(atlas_row.get("row_count"), max_row_count)
    value = (
        0.36 * factors["axis_coverage"]
        + 0.28 * factors["support_factor"]
        + 0.22 * factors["population_factor"]
        + 0.14 * count
    )
    return round(value, 6)


def _upgrade_gain(atlas_row: dict[str, Any], contract_row: dict[str, Any], base_utility: float) -> float:
    support = _support_factor(str(atlas_row.get("support_status") or ""))
    edge_bonus = 0.08 if contract_row.get("has_bidirectional_edge_policy") else 0.0
    gap_penalty = 0.12 if atlas_row.get("profile_gap") else 0.0
    return round(base_utility * (0.42 + 0.22 * support + edge_bonus - gap_penalty), 6)


def _option_card(repo_root: Path, kind_id: str, row_ref: str) -> dict[str, Any] | None:
    if kind_id == "paper_modules":
        payload = build_option_surface(repo_root, "paper_modules", band="card", ids=["navigation_hologram_theory"])
        rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
        return rows[0] if rows else None
    if kind_id == "standards":
        payload = build_option_surface(repo_root, "standards", band="card", ids=["std_navigation_contract"])
        rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
        return rows[0] if rows else None
    return None


def build_navigation_context_rosetta(
    repo_root: Path | str,
    *,
    context_budget: int = 1400,
) -> dict[str, Any]:
    """Build a context packet that maximizes coverage before depth."""
    root = Path(repo_root)
    generated_at = _utc_now()
    atlas = build_kind_atlas(root, band="card")
    audit = build_kind_band_contract_audit(root)
    atlas_rows = atlas.get("rows") if isinstance(atlas.get("rows"), list) else []
    contract_rows = audit.get("rows") if isinstance(audit.get("rows"), list) else []
    atlas_by_kind = _row_by(atlas_rows, "kind_id")
    contract_by_kind = _row_by(contract_rows, "kind_id")
    max_row_count = max([int(row.get("row_count") or 0) for row in atlas_rows] or [1])

    selected: list[dict[str, Any]] = []
    total_cost = 0
    for kind_id, atlas_row in atlas_by_kind.items():
        contract_row = contract_by_kind.get(kind_id, {})
        fixture = REPRESENTATIVE_FIXTURES.get(kind_id, {})
        row_count = _row_count_int(atlas_row)
        population_mode = _population_mode(atlas_row)
        if population_mode == "compiled" and not fixture.get("row_ref"):
            fixture = _generic_representative_fixture(root, kind_id, atlas_row)
        representative, row_ref = _representative_fixture_for(
            fixture,
            population_mode=population_mode,
            row_count=row_count,
        )
        utility = _base_utility(atlas_row, contract_row, max_row_count)
        cost = _coverage_floor_cost(kind_id, contract_row)
        unpopulated_units = list(contract_row.get("unpopulated_units") or [])
        if population_mode == "unpopulated" and row_count <= 0:
            unpopulated_units.append(f"kind:{kind_id}:rows")
        selected.append(
            {
                "atom_id": f"context_atom:{kind_id}:representative",
                "kind_id": kind_id,
                "row_ref": row_ref,
                "selected_band": "flag",
                "selector_policy_id": "direct_enumeration",
                "selection_role": "coverage_floor",
                "estimated_cost": cost,
                "estimated_utility": utility,
                "information_density": round(utility / cost, 6),
                "confidence": _confidence_for(atlas_row, population_mode),
                "extraction_mode": "compiled" if contract_row else "candidate_inference",
                "population_mode": population_mode,
                "population_honesty": {
                    "row_count": row_count,
                    "zero_row_surface": row_count <= 0,
                    "representative_row_ref_required": population_mode == "compiled",
                    "reason": (
                        "Zero-row supported kinds are selectable but unpopulated; row_ref stays null until a live row exists."
                        if population_mode == "unpopulated" and row_count <= 0
                        else "Populated option surface can expose a representative row_ref."
                    ),
                },
                "support_status": atlas_row.get("support_status"),
                "contract_status": contract_row.get("contract_status"),
                "row_count": atlas_row.get("row_count"),
                "axis_vector": {
                    "bands": contract_row.get("navigable_bands") or [],
                    "scopes": contract_row.get("navigable_scopes") or [],
                    "facets": contract_row.get("navigable_facets") or [],
                    "population_modes": contract_row.get("population_mode_counts") or {},
                    "unpopulated_units": unpopulated_units,
                    "has_bidirectional_edge_policy": contract_row.get("has_bidirectional_edge_policy") is True,
                },
                "representative": representative,
                "profile_gap": atlas_row.get("profile_gap"),
                "currentness": atlas_row.get("currentness"),
                "source_authority": contract_row.get("source_authority"),
                "evidence_refs": contract_row.get("evidence_refs") or [],
                "option_surface_command": atlas_row.get("option_surface_command"),
                "card_command": atlas_row.get("card_command"),
                "evidence_command": representative.get("evidence_command") or atlas_row.get("evidence_command"),
            }
        )
        total_cost += cost

    upgrades: list[dict[str, Any]] = []
    for row in selected:
        kind_id = row["kind_id"]
        atlas_row = atlas_by_kind.get(kind_id, {})
        contract_row = contract_by_kind.get(kind_id, {})
        extra_cost = _band_cost(contract_row, "card") - _coverage_floor_cost(kind_id, contract_row)
        gain = _upgrade_gain(atlas_row, contract_row, float(row["estimated_utility"]))
        upgrades.append(
            {
                "kind_id": kind_id,
                "extra_cost": extra_cost,
                "gain": gain,
                "gain_density": round(gain / extra_cost, 6) if extra_cost else 0,
            }
        )
    upgrades.sort(key=lambda item: (-item["gain_density"], item["kind_id"]))

    selected_by_kind = {row["kind_id"]: row for row in selected}
    for upgrade in upgrades:
        if total_cost + upgrade["extra_cost"] > context_budget:
            continue
        row = selected_by_kind[upgrade["kind_id"]]
        row["selected_band"] = "card"
        row["selection_role"] = "coverage_floor_plus_density_upgrade"
        row["estimated_cost"] = int(row["estimated_cost"]) + int(upgrade["extra_cost"])
        row["estimated_utility"] = round(float(row["estimated_utility"]) + float(upgrade["gain"]), 6)
        row["information_density"] = round(float(row["estimated_utility"]) / int(row["estimated_cost"]), 6)
        option_card = _option_card(root, upgrade["kind_id"], str((row.get("representative") or {}).get("row_ref") or ""))
        if option_card:
            row["populated_card"] = option_card
        total_cost += int(upgrade["extra_cost"])

    selected.sort(key=lambda row: (row["selected_band"] != "card", row["kind_id"]))
    coverage_count = len({row["kind_id"] for row in selected})
    card_count = sum(1 for row in selected if row["selected_band"] == "card")

    return {
        "kind": "navigation_context_rosetta_packet",
        "schema_version": "navigation_context_rosetta_packet_v0",
        "generated_at": generated_at,
        "authority_posture": "read_only_rosetta_context_probe_not_production_navigation",
        "source_surfaces": [
            "codex/standards/std_navigation_rosetta_grammar.json",
            "codex/standards/std_navigation_contract.json",
            "codex/standards/std_kind_atlas.json",
            "codex/doctrine/paper_modules/navigation_rosetta_math.md",
            "system/lib/kind_atlas.py",
            "system/lib/kind_band_contract_audit.py",
            "system/lib/standard_option_surface.py",
        ],
        "math_model": {
            "name": "coverage_first_information_density_knapsack_v1",
            "objective": "Maximize coverage and useful density under a bounded context budget while preserving source/currentness honesty.",
            "sets": {
                "K": "artifact kinds from the Kind Atlas",
                "B_k": "kind-native bands declared by the governing navigation contract/profile",
                "x_kb": "1 when kind k is emitted at band b, with at most one selected band per kind",
            },
            "variables": {
                "r_u_t": "Task-family role prior for unit u under task t.",
                "q_u": "Confidence/provenance multiplier for unit u.",
                "p": "Selector policy used to admit or rank a unit.",
            },
            "utility": "u(k,flag)=.36*axis_coverage+.28*support_factor+.22*population_factor+.14*log1p(row_count)/log1p(max_row_count); u(k,card)=u(k,flag)+marginal_contract_gain; edge upgrades multiply by confidence and role_prior when available",
            "constraint": "sum_k cost(k,selected_band) <= context_budget, with coverage floor selecting the cheapest row for every kind before upgrades when possible.",
            "objective_order": [
                "coverage_floor",
                "information_density",
                "risk_reduction",
                "omission_and_evidence_clarity",
            ],
            "layer_depth_rule": "Layer count is native to each kind and must be justified by distinguishable decisions, authority complexity, evidence fan-out, and population availability; extra empty layers are profile drift.",
            "paper_module_ref": "codex/doctrine/paper_modules/navigation_rosetta_math.md",
            "invariants": [
                "query_used=false: kinds are selected by atlas enumeration, not guessed terms.",
                "coverage floor precedes depth: every kind gets a flag row before any kind is upgraded to card.",
                "projection gaps remain visible and can still earn low-cost coverage rows.",
                "unpopulated bands reduce population_factor but do not disappear.",
                "source evidence commands stay behind drilldown rows."
            ],
            "lean_status": "No local Lean proof surface was found in the annex search for this wave; this packet keeps the proof as executable regression tests plus explicit invariants.",
        },
        "semantic_grammar": {
            "governing_standard_ref": "codex/standards/std_navigation_rosetta_grammar.json",
            "context_atom": "A selected noun at a band/scope/facet with selector policy, source authority, population mode, currentness, confidence, extraction mode, cost, utility, evidence command, and omission receipt.",
            "nouns": {
                "row": "A selectable artifact instance such as a paper module, standard, term, principle, Python scope, frontend component, or annex pattern.",
                "scope": "A structural noun inside a row: module, section, function, class, component, paragraph, table row, evidence ref.",
                "facet": "An aspect noun on a scope: gap, intent, body, signature, evidence, aliases, tests, dependency_neighborhood.",
                "band": "A density noun naming how compressed the selected row/scope/facet is for this packet.",
            },
            "verbs": {
                "feeds": "Source or upstream row supplies information, data, pressure, or examples into a target row.",
                "blocks": "Source row prevents safe action on target until a condition is satisfied.",
                "governs": "Source row constrains legal shape, authority, or validation of target.",
                "evidences": "Source row proves or motivates target without necessarily governing it.",
                "populates": "Source or worker emits target band/facet content.",
                "invalidates": "Source freshness, contradiction, or schema change makes target projection stale.",
                "compresses": "Source substrate becomes a lower-band target row under a profile.",
                "routes_to": "Source row tells the navigator which target row or operation to open next.",
                "audits": "Source row checks target for drift, missing fields, stale claims, or contract violations.",
                "supersedes": "Source row replaces target as current authority while preserving target as evidence.",
            },
            "complex_verbs": [
                "feeds_when_fresh",
                "blocks_until_validated",
                "governs_without_populating",
                "evidences_but_does_not_authorize",
                "populates_then_requires_receipt",
                "invalidates_generated_projection",
                "compresses_with_omission_receipt",
                "routes_to_source_evidence",
            ],
            "selector_policies": {
                "direct_enumeration": "Use when a full option surface fits the budget; preferred over model ranking.",
                "dependency_ordered": "Use when graph direction matters and validated summaries can fold lower-level context upward.",
                "calibrated_slate": "Use when the option surface is too large and candidate groups need comparable scores.",
                "beam_telescope": "Use when a tree/lattice must be traversed through multiple expansion decisions.",
                "impact_before_mutation": "Use when a proposed edit/action needs blast-radius context before source detail.",
            },
            "impact_vector": {
                "semantic_flow": "How much meaning or task signal moves across the edge.",
                "authority_flow": "Whether permission, standard legality, or doctrine constraint moves across the edge.",
                "freshness_risk": "How likely the target becomes wrong if the source changed.",
                "mutation_risk": "How dangerous it is to act from the compressed row without opening evidence.",
                "coverage_value": "How many otherwise-hidden artifact classes become visible through this noun/verb pair.",
            },
            "edge_need_formula": "need(edge,task)=dot(task_weights, impact_vector(edge))*authority_factor*freshness_factor*confidence(edge)*role_prior(edge,task)/cost(edge_band)",
            "rosetta_rule": "The smallest packet should expose selected context atoms, nouns, legal verbs, selector policy, impact vector, confidence/provenance, selected band, omitted neighborhoods, and evidence command before any source body is opened.",
        },
        "rosetta_grammar": {
            "description": "A compact meta-row every artifact kind can emit even though each kind keeps native bands, scopes, facets, and source authority.",
            "governing_standard_ref": "codex/standards/std_navigation_rosetta_grammar.json",
            "fields": [
                "atom_id",
                "kind_id",
                "row_ref",
                "selected_band",
                "selector_policy_id",
                "support_status",
                "contract_status",
                "axis_vector",
                "confidence",
                "extraction_mode",
                "population_modes",
                "representative.row_ref",
                "source_authority",
                "currentness",
                "profile_gap",
                "evidence_command",
            ],
            "holographic_property": "Every selected row carries enough of the whole grammar to explain how to expand itself: what kind it is, which band was chosen, which scopes/facets exist, who populates them, what is missing, and where source authority lives.",
        },
        "budget": {
            "context_budget": context_budget,
            "estimated_cost": total_cost,
            "remaining_budget": context_budget - total_cost,
            "coverage_count": coverage_count,
            "total_kinds": len(atlas_rows),
            "card_upgrades": card_count,
        },
        "representative_context_rows": selected,
        "omission_receipt": {
            "omitted": [
                "full source bodies",
                "generic --row dispatch",
                "generic --telescope dispatch",
                "provider/Bridge population jobs",
                "unbounded second-order dependency closure",
            ],
            "reason": "This packet tests the Rosetta grammar for context compression; it does not claim production navigation support beyond existing surfaces.",
            "drilldown": [
                "./repo-python kernel.py --kind-atlas --band card",
                "./repo-python kernel.py --kind-band-contract-audit",
                "./repo-python kernel.py --option-surface paper_modules --band card --ids navigation_hologram_theory",
                "./repo-python kernel.py --option-surface standards --band card --ids std_navigation_contract",
            ],
        },
    }


def write_wave_044_artifacts(repo_root: Path | str, *, context_budget: int = 1400) -> dict[str, Any]:
    root = Path(repo_root)
    packet = build_navigation_context_rosetta(root, context_budget=context_budget)
    out_dir = root / WAVE_044_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    packet_path = out_dir / "navigation_context_rosetta_packet_v0.json"
    grammar_path = out_dir / "rosetta_navigation_grammar_v0.json"
    receipt_path = out_dir / "rosetta_context_compression_receipt.md"
    packet_path.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    grammar = {
        "kind": "rosetta_navigation_grammar",
        "schema_version": "rosetta_navigation_grammar_v0",
        "generated_at": packet["generated_at"],
        "authority_posture": "candidate_navigation_grammar_not_production_dispatch",
        "governing_standard_ref": "codex/standards/std_navigation_rosetta_grammar.json",
        "math_model": packet["math_model"],
        "semantic_grammar": packet["semantic_grammar"],
        "rosetta_grammar": packet["rosetta_grammar"],
        "representative_rows_count": len(packet["representative_context_rows"]),
        "source_packet": str(packet_path.relative_to(root)),
    }
    grammar_path.write_text(json.dumps(grammar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    receipt = f"""# Wave 044 Rosetta Context Compression Receipt

Generated: {packet['generated_at']}

## Claim

The v1 navigation contract can act as a Rosetta stone for context compression: enumerate artifact kinds, emit one grammar-compatible row per kind, then spend remaining budget on card-depth upgrades by information density.

## Result

- Coverage: {packet['budget']['coverage_count']}/{packet['budget']['total_kinds']} kinds.
- Estimated cost: {packet['budget']['estimated_cost']} / {packet['budget']['context_budget']}.
- Card upgrades: {packet['budget']['card_upgrades']}.

## Boundary

This is a read-only probe. It does not implement generic `--row`, production `--telescope`, Bridge/OpenRouter/NVIDIA population, or source mutation.

## Artifacts

- `navigation_context_rosetta_packet_v0.json`
- `rosetta_navigation_grammar_v0.json`

## Next Delta

Use this packet as the fixture for the first real telescope adapter: select one upgraded card row, expand one band/scope/facet, and preserve the same budget/currentness accounting.
"""
    receipt_path.write_text(receipt, encoding="utf-8")
    return {
        "packet": packet,
        "artifact_paths": [
            str(packet_path.relative_to(root)),
            str(grammar_path.relative_to(root)),
            str(receipt_path.relative_to(root)),
        ],
    }
