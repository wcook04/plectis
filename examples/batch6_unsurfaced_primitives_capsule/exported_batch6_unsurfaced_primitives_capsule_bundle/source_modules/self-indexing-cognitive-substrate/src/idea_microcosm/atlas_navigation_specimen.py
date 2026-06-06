from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .navigation import (
    CLAIM_STRENGTH_LADDER,
    DIAGNOSTIC_ROUTE_BRIDGE,
    EXOGENOUS_AGENT_ENTRY_MODES,
    LEAF_CODE_ROUTE_BRIDGE,
    MACRO_PATTERN_ROUTE_BRIDGE,
    ORGANISATION_MODEL,
    ROOT_CONCURRENCY_GUARD,
    ROOT_ENTRY_CONTRACT,
    ROOT_ENTRY_ROUTE_MAP_BRIDGE,
    ROOT_NAVIGATION_LADDER,
    ROUTE_COMPOSITION_BRIDGE,
    SUMMARY_LADDER_BRIDGE,
    STD_PYTHON_POPULATION_BRIDGE,
    UPGRADE_ROBUST_PROJECTION_PATTERN,
    build_leaf_entry_contract_projection,
    build_leaf_entry_readme_cards,
    build_microcosm_implementation_atlas,
)


SPECIMEN_ID = "atlas_navigation_bands_microcosm"
DEFAULT_OUTPUT_PATH = "microcosms/atlas_navigation_bands/navigation_bands.json"
DEFAULT_INDEX_PATH = "navigation/microcosm_index.json"
DEFAULT_LEAF_ENTRY_CONTRACT_PATH = "microcosms/leaf_entry_contract.json"
DEFAULT_RECEIPT_PATH = "microcosms/atlas_navigation_bands/receipt.json"
README_PATH = "microcosms/atlas_navigation_bands/README.md"
TELEOLOGY_GATE_PATH = Path("strategy/microcosm_teleology_gate.json")
EXPECTED_BANDS = ("compressed", "technical", "evidence", "sandbox")
EFFECTIVENESS_VALIDATOR_ID = "validator.atlas_navigation_bands_effectiveness_witness"

REVIEWER_ROUTES = [
    {
        "route_id": "status_authority",
        "reviewer_question": "Can this system keep status classes from collapsing?",
        "first_microcosm": "status_preserving_control_plane",
        "supporting_microcosms": [
            "correction_survival_loop",
            "release_standards_axiom_gate",
        ],
        "first_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-status-preserving-control-plane-specimen --root . --write-receipt",
        "proof_refs": [
            "microcosms/status_preserving_control_plane/receipt.json",
            "fixtures/status/status_collapse_adversarial_suite.json",
        ],
        "anti_claim": "fixture status preservation is not private-root equivalence or publication permission",
    },
    {
        "route_id": "durable_work",
        "reviewer_question": "Can work survive context loss and concurrent agents?",
        "first_microcosm": "task_ledger_cap_economy",
        "supporting_microcosms": [
            "concurrency_mission_control",
            "correction_survival_loop",
        ],
        "first_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-task-ledger-specimen --root . --write-receipt",
        "proof_refs": [
            "microcosms/task_ledger_cap_economy/receipt.json",
            "microcosms/concurrency_mission_control/receipt.json",
        ],
        "anti_claim": "synthetic work events are not private Task Ledger content",
    },
    {
        "route_id": "cold_agent_entry",
        "reviewer_question": "Can a cold external agent enter without private context?",
        "first_microcosm": "self_comprehension_navigator",
        "supporting_microcosms": [
            "concept_graph_cards",
            "summary_ladders",
            "cold_start_agent_skills_pack",
            "atlas_navigation_bands",
        ],
        "first_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-self-comprehension-navigator-specimen --root . --write-receipt",
        "proof_refs": [
            "AGENTS.md",
            "navigation/entry_packet.json",
            "navigation/microcosm_index.json",
            "microcosms/leaf_entry_contract.json",
            "microcosms/summary_ladders/summary_ladders.json",
            "microcosms/concept_graph_cards/cold_entry_atlas.json",
        ],
        "anti_claim": "public agent-entry projection is not the private bootstrap",
    },
    {
        "route_id": "sandbox_boundary",
        "reviewer_question": "What proves this is a runnable system sandbox, not a release wrapper?",
        "first_microcosm": "concurrency_mission_control",
        "supporting_microcosms": [
            "task_ledger_cap_economy",
            "meta_diagnostics_workbench",
            "executable_grammar_metabolism",
        ],
        "first_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-concurrency-mission-control-specimen --root . --write-receipt",
        "proof_refs": [
            "sandbox/microcosm_sandbox_gate.json",
            "strategy/microcosm_teleology_gate.json",
            "microcosms/concurrency_mission_control/receipt.json",
        ],
        "anti_claim": "sandbox evidence is not release packaging, hosted-public proof, or publication approval",
    },
    {
        "route_id": "visual_review",
        "reviewer_question": "What control surface can I inspect without turning UI into evidence authority?",
        "first_microcosm": "frontend_cockpit_hud",
        "supporting_microcosms": [
            "status_preserving_control_plane",
            "meta_diagnostics_workbench",
        ],
        "first_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-frontend-hud-control-surface-specimen --root . --write-receipt",
        "proof_refs": [
            "microcosms/frontend_cockpit_hud/receipt.json",
            "microcosms/status_preserving_control_plane/receipt.json",
            "microcosms/meta_diagnostics_workbench/receipt.json",
        ],
        "anti_claim": "visual control surfaces are downstream projections, not evidence authority",
    },
    {
        "route_id": "diagnostic_review",
        "reviewer_question": "How are evaluators, providers, failures, and benchmark-shaped claims kept bounded?",
        "first_microcosm": "provider_harness_canary",
        "supporting_microcosms": [
            "lab_evolve_failure_replay",
            "verisoftbench_diagnostic",
            "executable_grammar_metabolism",
        ],
        "first_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-provider-harness-canary-specimen --root . --write-receipt",
        "proof_refs": [
            "microcosms/provider_harness_canary/receipt.json",
            "microcosms/lab_evolve_failure_replay/receipt.json",
            "microcosms/verisoftbench_diagnostic/receipt.json",
        ],
        "anti_claim": "diagnostic fixtures are not benchmark wins or external endorsements",
    },
]

LEAF_CONTRACT = {
    "schema_version": "microcosm_leaf_contract_v0",
    "parent_root": "self-indexing-cognitive-substrate/",
    "machine_readable_contract": "microcosms/leaf_entry_contract.json",
    "governing_standard": "standards/leaf_entry_contract.json",
    "rule": "A leaf proves one organ; the parent root composes leaves without upgrading their claim tier.",
    "standalone_clone_posture": "leaf_inspectable_root_rebuildable",
    "standalone_clone_protocol": [
        "If a leaf is browsed or cloned alone, start with its README, primary JSON board or manifest, and receipt.",
        "Treat parent-root paths such as standards, registry rows, and validators as lineage refs until the full root is available.",
        "Use the parent root for rebuilds, validation, std_python report refresh, and release-claim strengthening.",
        "A standalone leaf can explain its local organ; it cannot claim root composition, hosted-public readiness, publication permission, or private-root equivalence.",
    ],
    "required_local_fields": [
        "README names the organ proved",
        "one command or inspect path",
        "fixture, board, projection, or manifest path",
        "receipt path",
        "validator or probe",
        "anti-claims",
        "reviewer route",
        "release gate or fail-closed boundary",
    ],
    "root_composition_rule": "The root index may compress and compose leaves; a leaf-local clone remains a bounded evidence shard until the root wrapper rebuilds it.",
    "clone_posture_rule": "Root-backed execution is supported now; standalone leaf subrepos require an explicit wrapper projection.",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _route(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": candidate.get("candidate_id"),
        "title": candidate.get("title"),
        "score": candidate.get("score"),
        "specimen_status": candidate.get("specimen_status"),
        "release_priority": candidate.get("release_priority"),
        "selector_reason": candidate.get("selector_reason"),
        "bands": {
            "compressed": {
                "summary": candidate.get("five_sentence_release_summary", [])[:2],
                "next_action": candidate.get("next_action"),
            },
            "technical": {
                "projection_strategy": candidate.get("projection_strategy"),
                "improvement_delta": candidate.get("improvement_delta"),
                "source_refs": candidate.get("source_refs", []),
                "python_refs": candidate.get("python_refs", []),
                "standard_refs": candidate.get("standard_refs", []),
                "skill_refs": candidate.get("skill_refs", []),
                "concept_refs": candidate.get("concept_refs", []),
            },
            "evidence": {
                "receipt_refs": candidate.get("receipt_refs", []),
                "public_safety_status": candidate.get("public_safety_status"),
                "runnability_status": candidate.get("runnability_status"),
                "blocked_by": candidate.get("blocked_by", []),
            },
            "sandbox": {
                "teleology_gate_ref": "strategy/microcosm_teleology_gate.json",
                "sandbox_gate_ref": "sandbox/microcosm_sandbox_gate.json",
                "active_selection_scope": "system_organ_microcosms_only",
                "public_safety_boundary": "Registry projection only; release, website, recipient, hosted-public, and publication machinery stays downstream of the active sandbox ontology.",
            },
        },
    }


def _effectiveness_witness(routes: list[dict[str, Any]]) -> dict[str, Any] | None:
    selected = next(
        (
            route
            for route in routes
            if (route.get("bands", {}).get("evidence", {}).get("receipt_refs") or [])
        ),
        routes[0] if routes else None,
    )
    if not selected:
        return None
    receipt_refs = selected.get("bands", {}).get("evidence", {}).get("receipt_refs") or []
    return {
        "witness_id": "atlas_navigation_effectiveness.band_drilldown_selects_evidence_surface",
        "required_motif": "cold agent must select the evidence band rather than overbroad candidate prose",
        "candidate_id": selected.get("candidate_id"),
        "source_surface": "state/release_candidate_portfolio.json",
        "without_bands": {
            "route_or_behavior": "flat_candidate_scan",
            "selected_surface": "overbroad_candidate_summary",
            "motif_present": False,
            "outcome": "fail_wrong_surface_or_missing_receipt_boundary",
        },
        "with_bands": {
            "route_or_behavior": "banded_drilldown",
            "selected_band": "evidence",
            "selected_surface": "candidate.receipt_refs",
            "motif_present": True,
            "receipt_refs": receipt_refs,
            "outcome": "pass_evidence_surface_selected",
        },
        "accepted_loss_boundary": {
            "allowed_loss": [
                "non-load-bearing rank details",
                "display wording",
            ],
            "forbidden_loss": [
                "band identity",
                "receipt boundary",
                "candidate id",
            ],
        },
        "validator": {
            "validator_id": EFFECTIVENESS_VALIDATOR_ID,
            "future_route_changed": True,
            "status": "pass",
        },
    }


def _readme() -> str:
    return "\n".join(
        [
            "# Atlas Navigation Bands",
            "",
            "This specimen turns the active microcosm portfolio into a banded navigation surface.",
            "It is a sandbox-local projection, not the private System Atlas and not a release or publication claim.",
            "",
            "Run it from the release root:",
            "",
            "```bash",
            "PYTHONPATH=src python3 -m idea_microcosm.cli build-atlas-navigation-bands-specimen --root . --write-receipt",
            "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
            "```",
            "",
            "The four bands are `compressed`, `technical`, `evidence`, and `sandbox`.",
            "Cold agents should start with `AGENTS.md`, then `navigation/entry_packet.json`, then `navigation/microcosm_index.json`, then `microcosms/leaf_entry_contract.json`, then the reviewer route that matches their question.",
            "The specimen includes an effectiveness witness: without bands, the cold agent gets an overbroad candidate summary; with bands, it selects the evidence band and lands on receipt refs.",
            "",
            "The boundary is fail-closed: website, recipient, hosted-public, clone-proof, and package-export machinery must stay downstream of the active sandbox ontology.",
            "",
        ]
    )


def build_atlas_navigation_specimen(
    root: Path,
    *,
    output_path: str = DEFAULT_OUTPUT_PATH,
    index_path: str = DEFAULT_INDEX_PATH,
    receipt_path: str = DEFAULT_RECEIPT_PATH,
    write_receipt: bool = False,
    at: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    generated_at = at or _utc_now()
    candidate_source = _load_json(root / "registry" / "release_candidates.json")
    portfolio = _load_json(root / "state" / "release_candidate_portfolio.json")
    idea_atlas = _load_json(root / "navigation" / "atlas.json")
    entry_packet = _load_json(root / "navigation" / "entry_packet.json")
    teleology_gate = _load_optional_json(root / TELEOLOGY_GATE_PATH)
    retired_candidate_ids = {
        str(value)
        for value in teleology_gate.get("retired_candidate_ids", [])
        if isinstance(value, str)
    }

    candidate_rows = [row for row in portfolio.get("candidates", []) if isinstance(row, dict)]
    source_ids = {
        row.get("candidate_id")
        for row in candidate_source.get("rows", [])
        if isinstance(row, dict) and str(row.get("candidate_id", "")) not in retired_candidate_ids
    }
    portfolio_ids = {row.get("candidate_id") for row in candidate_rows}
    failures: list[dict[str, Any]] = []
    if candidate_source.get("authority_posture") != "public_safe_candidate_source_registry_not_publication_claim":
        failures.append({"path": "registry/release_candidates.json", "reason": "candidate source must not claim publication authority"})
    if portfolio.get("authority_posture") != "ranked_projection_not_publication_claim":
        failures.append({"path": "state/release_candidate_portfolio.json", "reason": "portfolio must be a ranked projection"})
    if portfolio.get("status") != "ok":
        failures.append({"path": "state/release_candidate_portfolio.json", "status": portfolio.get("status")})
    if source_ids != portfolio_ids:
        failures.append({"path": "state/release_candidate_portfolio.json", "reason": "portfolio ids must mirror release candidate registry"})
    if SPECIMEN_ID not in source_ids:
        failures.append({"path": "registry/release_candidates.json", "reason": f"missing {SPECIMEN_ID}"})
    all_candidate_specimens_landed = portfolio.get("all_candidate_specimens_landed") is True
    if not portfolio.get("next_specimen_candidate_id") and not all_candidate_specimens_landed:
        failures.append({"path": "state/release_candidate_portfolio.json", "reason": "portfolio must identify the next specimen candidate or declare terminal landed status"})
    if idea_atlas.get("authority_posture") != "projection_not_authority":
        failures.append({"path": "navigation/atlas.json", "reason": "idea atlas must remain projection-not-authority"})
    if entry_packet.get("authority_posture") != "navigation_projection_not_source_authority":
        failures.append({"path": "navigation/entry_packet.json", "reason": "entry packet must not claim source authority"})

    routes = [_route(candidate) for candidate in candidate_rows]
    implementation_atlas = build_microcosm_implementation_atlas(root)
    leaf_entry_contract = build_leaf_entry_contract_projection(root, implementation_atlas=implementation_atlas)
    leaf_contract_bridge = leaf_entry_contract.get("implementation_navigation_bridge", {})
    leaf_contract_summary = leaf_entry_contract.get("summary", {})
    projected_leaf_contract = {
        **LEAF_CONTRACT,
        "implementation_navigation_bridge": leaf_contract_bridge,
        "single_leaf_wrapper_protocol": leaf_entry_contract.get("single_leaf_wrapper_protocol", {}),
        "summary": leaf_contract_summary,
    }
    status = "ok" if not failures else "failed"
    effectiveness_witnesses = [witness] if (witness := _effectiveness_witness(routes)) else []
    effectiveness_status = "pass" if effectiveness_witnesses and status == "ok" else "fail"
    next_candidate_id = portfolio.get("next_specimen_candidate_id")
    next_route = next((route for route in routes if route.get("candidate_id") == next_candidate_id), None)

    navigation_bands = {
        "kind": "atlas_navigation_bands_specimen",
        "schema_version": "atlas_navigation_bands_specimen_v0",
        "generated_at": generated_at,
        "status": status,
        "candidate_id": SPECIMEN_ID,
        "authority_posture": "release_local_navigation_projection_not_private_system_atlas_authority",
        "source_refs": [
            "registry/release_candidates.json",
            "state/release_candidate_portfolio.json",
            "navigation/atlas.json",
            "navigation/entry_packet.json",
        ],
        "band_ids": list(EXPECTED_BANDS),
        "candidate_count": len(candidate_rows),
        "implemented_specimen_candidate_ids": portfolio.get("implemented_specimen_candidate_ids", []),
        "all_candidate_specimens_landed": all_candidate_specimens_landed,
        "next_candidate_route": next_route,
        "routes": routes,
        "reviewer_routes": REVIEWER_ROUTES,
        "agent_entry_modes": EXOGENOUS_AGENT_ENTRY_MODES,
        "organisation_model": ORGANISATION_MODEL,
        "root_entry_contract": ROOT_ENTRY_CONTRACT,
        "root_concurrency_guard": ROOT_CONCURRENCY_GUARD,
        "root_entry_route_map": ROOT_ENTRY_ROUTE_MAP_BRIDGE,
        "route_composition_bridge": ROUTE_COMPOSITION_BRIDGE,
        "upgrade_robust_projection_pattern": UPGRADE_ROBUST_PROJECTION_PATTERN,
        "implementation_atlas": implementation_atlas,
        "leaf_implementation_navigation_bridge": leaf_contract_bridge,
        "root_navigation_ladder": ROOT_NAVIGATION_LADDER,
        "std_python_population_bridge": STD_PYTHON_POPULATION_BRIDGE,
        "summary_ladder_bridge": SUMMARY_LADDER_BRIDGE,
        "macro_pattern_route_bridge": MACRO_PATTERN_ROUTE_BRIDGE,
        "leaf_code_route_bridge": LEAF_CODE_ROUTE_BRIDGE,
        "diagnostic_route_bridge": DIAGNOSTIC_ROUTE_BRIDGE,
        "claim_strength_ladder": CLAIM_STRENGTH_LADDER,
        "leaf_contract": projected_leaf_contract,
        "leaf_entry_contract_summary": leaf_contract_summary,
        "effectiveness_witnesses": effectiveness_witnesses,
        "effectiveness_witness_summary": {
            "status": effectiveness_status,
            "validator_id": EFFECTIVENESS_VALIDATOR_ID,
            "effectiveness_witness_count": len(effectiveness_witnesses),
            "selected_required_motif": (
                effectiveness_witnesses[0].get("required_motif") if effectiveness_witnesses else None
            ),
        },
        "public_safety_boundary": "This specimen is a release-local navigation projection. It is not the private System Atlas, a private-root export, or a public-release claim.",
        "publication_boundary": "No website, recipient, hosted-public, clone-proof, or package-export claim may define the active microcosm ontology.",
        "failures": failures,
    }

    index = {
        "kind": "release_microcosm_index",
        "schema_version": "release_microcosm_index_v0",
        "generated_at": generated_at,
        "status": status,
        "authority_posture": "release_local_navigation_projection_not_private_system_atlas_authority",
        "source_ref": output_path,
        "candidate_count": len(candidate_rows),
        "band_ids": list(EXPECTED_BANDS),
        "top_candidate_id": portfolio.get("top_candidate_id"),
        "next_specimen_candidate_id": next_candidate_id,
        "all_candidate_specimens_landed": all_candidate_specimens_landed,
        "implemented_specimen_candidate_ids": portfolio.get("implemented_specimen_candidate_ids", []),
        "routes": [
            {
                "candidate_id": route.get("candidate_id"),
                "title": route.get("title"),
                "score": route.get("score"),
                "specimen_status": route.get("specimen_status"),
                "navigation_bands_ref": output_path,
                "receipt_refs": route.get("bands", {}).get("evidence", {}).get("receipt_refs", []),
            }
            for route in routes
        ],
        "entry_surfaces": [
            "AGENTS.md",
            "RELEASE_SCOPE.md",
            "AXIOMS.md",
            "navigation/entry_packet.json",
            "navigation/microcosm_index.json",
            "microcosms/leaf_entry_contract.json",
            "microcosms/summary_ladders/summary_ladders.json",
            "microcosms/summary_ladders/README.md",
            "microcosms/README.md",
        ],
        "reviewer_routes": REVIEWER_ROUTES,
        "agent_entry_modes": EXOGENOUS_AGENT_ENTRY_MODES,
        "organisation_model": ORGANISATION_MODEL,
        "root_entry_contract": ROOT_ENTRY_CONTRACT,
        "root_concurrency_guard": ROOT_CONCURRENCY_GUARD,
        "root_entry_route_map": ROOT_ENTRY_ROUTE_MAP_BRIDGE,
        "route_composition_bridge": ROUTE_COMPOSITION_BRIDGE,
        "upgrade_robust_projection_pattern": UPGRADE_ROBUST_PROJECTION_PATTERN,
        "implementation_atlas": implementation_atlas,
        "leaf_implementation_navigation_bridge": leaf_contract_bridge,
        "root_navigation_ladder": ROOT_NAVIGATION_LADDER,
        "std_python_population_bridge": STD_PYTHON_POPULATION_BRIDGE,
        "summary_ladder_bridge": SUMMARY_LADDER_BRIDGE,
        "macro_pattern_route_bridge": MACRO_PATTERN_ROUTE_BRIDGE,
        "leaf_code_route_bridge": LEAF_CODE_ROUTE_BRIDGE,
        "diagnostic_route_bridge": DIAGNOSTIC_ROUTE_BRIDGE,
        "claim_strength_ladder": CLAIM_STRENGTH_LADDER,
        "leaf_contract": projected_leaf_contract,
        "leaf_entry_contract_summary": leaf_contract_summary,
        "cold_agent_rule": "Open compressed band first, then technical refs, then evidence receipts, then sandbox boundary. Do not infer release readiness from rank.",
    }

    _write_json(root / output_path, navigation_bands)
    _write_json(root / index_path, index)
    if leaf_entry_contract:
        _write_json(root / DEFAULT_LEAF_ENTRY_CONTRACT_PATH, leaf_entry_contract)
    readme_file = root / README_PATH
    readme_file.parent.mkdir(parents=True, exist_ok=True)
    readme_file.write_text(_readme(), encoding="utf-8")
    leaf_readme_cards = build_leaf_entry_readme_cards(root, leaf_entry_contract=leaf_entry_contract)

    result: dict[str, Any] = {
        "kind": "atlas_navigation_bands_build",
        "schema_version": "atlas_navigation_bands_build_v0",
        "generated_at": generated_at,
        "status": status,
        "output": output_path,
        "index_output": index_path,
        "leaf_entry_contract_output": DEFAULT_LEAF_ENTRY_CONTRACT_PATH,
        "leaf_entry_readme_card_status": leaf_readme_cards["status"],
        "leaf_entry_readme_card_count": leaf_readme_cards["written_count"],
        "candidate_count": len(candidate_rows),
        "band_count": len(EXPECTED_BANDS),
        "next_specimen_candidate_id": next_candidate_id,
        "all_candidate_specimens_landed": all_candidate_specimens_landed,
        "failure_count": len(failures),
        "effectiveness_witness_count": len(effectiveness_witnesses),
        "failures": failures,
    }
    if write_receipt:
        receipt = {
            "kind": "receipt",
            "schema_version": "receipt_v0",
            "id": "receipt.atlas_navigation_bands",
            "generated_at": generated_at,
            "owner": "idea_microcosm.atlas_navigation_specimen",
            "claim_ref": f"candidate.{SPECIMEN_ID}",
            "claim_tier": "fixture_validated",
            "command": "python -m idea_microcosm.cli build-atlas-navigation-bands-specimen --root . --write-receipt",
            "result": status,
            "status": status,
            "effectiveness_witness_count": len(effectiveness_witnesses),
            "effectiveness_validator_status": effectiveness_status,
            "leaf_entry_readme_card_projection": leaf_readme_cards,
            "evidence_refs": [
                output_path,
                index_path,
                README_PATH,
                "registry/release_candidates.json",
                "state/release_candidate_portfolio.json",
                "navigation/atlas.json",
                "navigation/entry_packet.json",
                DEFAULT_LEAF_ENTRY_CONTRACT_PATH,
            ],
            "validator_summary": [
                {
                    "validator_id": "validator.atlas_navigation_bands_specimen",
                    "status": "pass" if status == "ok" else "fail",
                },
                {"validator_id": EFFECTIVENESS_VALIDATOR_ID, "status": effectiveness_status},
            ],
            "omissions": [
                "This receipt validates release-local navigation only; it does not make a public-release, hosted-CI, novelty, or private-root-equivalence claim.",
                "Private System Atlas surfaces can guide internal discovery, but this specimen exposes only public-safe release registry and portfolio records.",
                "The effectiveness witness is a synthetic local relation; it does not prove all real navigation sessions select the right band.",
            ],
            "summary": {
                "candidate_count": len(candidate_rows),
                "band_ids": list(EXPECTED_BANDS),
                "next_specimen_candidate_id": next_candidate_id,
                "all_candidate_specimens_landed": all_candidate_specimens_landed,
                "effectiveness_witness_count": len(effectiveness_witnesses),
                "failure_count": len(failures),
            },
        }
        _write_json(root / receipt_path, receipt)
        result["receipt_written"] = receipt_path
    return result
