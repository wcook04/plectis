#!/usr/bin/env python3
"""Build a self-validating holographic research bundle for ai_workflow.

This is a private-side research projection tool. It does not render the public
repo and does not mutate source files. Its job is to turn selected
system-description and dissemination surfaces into a typed, navigable,
auditable JSON snapshot for external research models.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = Path.home() / "Downloads" / "ai_workflow_holographic_research_bundle_2026-05-05.json"
SCHEMA_VERSION = "3.6.7"
DEFAULT_RECEIPT_ROOT = Path(
    os.environ.get(
        "AIW_PUBLIC_PROJECTION_OUTPUT_ROOT",
        Path.home() / ".cache" / "ai_workflow" / "public_projection",
    )
)
PUBLIC_PROJECTION_ARTIFACT_ROOT = "artifact://public_projection"
PROJECTION_RECEIPT_URI = f"{PUBLIC_PROJECTION_ARTIFACT_ROOT}/projection_receipt.json"
PORTABILITY_GATE_REPORT_URI = f"{PUBLIC_PROJECTION_ARTIFACT_ROOT}/portability_gate_report.json"
PUBLIC_OUTPUT_ROOT_PLACEHOLDER = "<public_output_root>"

RECEIPT_ARTIFACT_REFERENCES = {
    "projection_receipt.json": {
        "artifact_uri": PROJECTION_RECEIPT_URI,
        "resolved_to_receipt_id": "receipt:projection_receipt",
        "receipt_kind": "projection_receipt",
        "receipt_resolution_status": "resolved_to_receipt_entity",
    },
    "portability_gate_report.json": {
        "artifact_uri": PORTABILITY_GATE_REPORT_URI,
        "resolved_to_receipt_id": "receipt:portability_gate_report",
        "receipt_kind": "portability_gate_report",
        "receipt_resolution_status": "resolved_to_receipt_entity",
    },
    "projection.lock.json": {
        "artifact_uri": f"{PUBLIC_PROJECTION_ARTIFACT_ROOT}/projection.lock.json",
        "resolved_to_receipt_id": None,
        "receipt_kind": "projection_lock",
        "receipt_resolution_status": "known_projection_control_artifact_not_receipt_entity",
    },
}

SOURCE_PATHS = [
    "codex/doctrine/paper_modules/system_self_comprehension_root.md",
    "codex/doctrine/paper_modules/system_self_comprehension_spine.md",
    "codex/doctrine/paper_modules/system_constitution_seed.md",
    "docs/system_atlas/system_atlas_v0.md",
    "docs/system_atlas/generated_system_facts_at_a_glance.md",
    "dist/type_b/TYPE_B_SYSTEM_GROUNDING_PACKET.md",
    "dist/type_b/AI_WORKFLOW_SYSTEM_PACKET.md",
    "codex/doctrine/agent_bootstrap.json",
    "codex/doctrine/routing_hologram.json",
    "codex/doctrine/documentation_theory_index.json",
    "codex/doctrine/paper_modules/agent_entry_surfaces.md",
    "codex/doctrine/paper_modules/dissemination_strategy.md",
    "codex/standards/std_agent_entry_surface.json",
    "codex/doctrine/concepts/con_036_entry_point.json",
    "codex/doctrine/concepts/con_037_entry_point_probe.json",
    "codex/doctrine/skills/dissemination/dissemination_cycle.md",
    "codex/doctrine/skills/dissemination/dissemination_understanding.md",
    "codex/doctrine/skills/dissemination/dissemination_research_prompting.md",
    "codex/doctrine/skills/dissemination/dissemination_research_assimilation.md",
    "docs/documentation_plane_map.md",
    "docs/agent_instruction_router.md",
    "docs/dissemination/README.md",
    "docs/dissemination/actual_deliverable_v0.md",
    "docs/dissemination/recognition_grade_system_description.md",
    "docs/dissemination/public_projection_boundary_v0.md",
    "docs/dissemination/safety_boundary.md",
    "docs/dissemination/public_trust_packet_v0.md",
    "docs/dissemination/system_paper_v0.md",
    "docs/dissemination/system_paper_traceability_map.md",
    "docs/dissemination/single_system_paper_contract.md",
    "docs/dissemination/open_source_successor_ir_contract.md",
    "docs/dissemination/public_reconstruction_architecture_contract.md",
    "docs/dissemination/system_capability_register.md",
    "docs/dissemination/capability_to_avenue_matrix.md",
    "docs/dissemination/demo_variant_catalog.md",
    "docs/dissemination/demo_shot_list_v0.md",
    "docs/dissemination/private_demo_protocol.md",
    "docs/dissemination/platform_terms_red_flags.md",
    "docs/dissemination/release_ip_license_gate_v0.md",
    "docs/dissemination/public_leaf_readiness_audit.md",
    "docs/dissemination/public_repo_scale_legibility_strategy_v0.md",
    "docs/dissemination/holographic_readme_template.md",
    "docs/dissemination/holographic_research_snapshot.md",
    "docs/dissemination/disclosure_artifact_registry.md",
    "docs/dissemination/provenance_note.md",
    "docs/dissemination/external_legibility_packet.md",
]

ROLES = {
    "codex/doctrine/paper_modules/system_self_comprehension_root.md": "root contract for the system self-comprehension packet family",
    "codex/doctrine/paper_modules/system_self_comprehension_spine.md": "private substrate self-model and System Atlas/coverage-graph spine",
    "codex/doctrine/paper_modules/system_constitution_seed.md": "constitution and ontology seed for substrate axioms and primitives",
    "docs/system_atlas/system_atlas_v0.md": "manual v0 atlas entry over substrate domains",
    "docs/system_atlas/generated_system_facts_at_a_glance.md": "generated fact card; prompt projection, not source authority",
    "dist/type_b/TYPE_B_SYSTEM_GROUNDING_PACKET.md": "compact Type B receiver grounding projection",
    "dist/type_b/AI_WORKFLOW_SYSTEM_PACKET.md": "wide Type B system packet projection",
    "codex/doctrine/agent_bootstrap.json": "authored compressed bootstrap situation routes, minimum read sets, and actor-delivery decisions",
    "codex/doctrine/routing_hologram.json": "generated compact situation-to-skill routing projection",
    "codex/doctrine/documentation_theory_index.json": "machine docs-route graph including the dissemination agent-entry route",
    "codex/doctrine/paper_modules/agent_entry_surfaces.md": "agent entry surface doctrine for compressed route pointers and actor bootstrap boundaries",
    "codex/doctrine/paper_modules/dissemination_strategy.md": "governing dissemination strategy, anti-routes, staged public projection posture, and cold-agent lane invariants",
    "codex/standards/std_agent_entry_surface.json": "standard for cold-agent entry packets, actor delivery, and compressed entry projections",
    "codex/doctrine/concepts/con_036_entry_point.json": "entry point concept: cold entrant prior packet, authority, drilldown, and freshness grammar",
    "codex/doctrine/concepts/con_037_entry_point_probe.json": "entry point probe concept for validating whether entry packets produce correct actor behavior",
    "codex/doctrine/skills/dissemination/dissemination_cycle.md": "composite dissemination skill selecting understanding, research prompting, or assimilation",
    "codex/doctrine/skills/dissemination/dissemination_understanding.md": "dissemination orientation skill and cold-agent read order",
    "codex/doctrine/skills/dissemination/dissemination_research_prompting.md": "public-safe Type B dissemination research prompt authoring skill",
    "codex/doctrine/skills/dissemination/dissemination_research_assimilation.md": "returned-research assimilation skill for owned dissemination surfaces",
    "docs/documentation_plane_map.md": "human documentation-plane map that points dissemination entry to docs-route and the dissemination skill family",
    "docs/agent_instruction_router.md": "operator-oriented trigger router that exposes the dissemination entry command path",
    "docs/dissemination/README.md": "dissemination router and orientation surface",
    "docs/dissemination/actual_deliverable_v0.md": "primary dissemination deliverable authority",
    "docs/dissemination/recognition_grade_system_description.md": "external recognition/category description draft",
    "docs/dissemination/public_projection_boundary_v0.md": "public/private cutline, release classes, proof obligations, and claim tiers",
    "docs/dissemination/safety_boundary.md": "safety and disclosure boundary",
    "docs/dissemination/public_trust_packet_v0.md": "reviewer-facing trust/evidence packet",
    "docs/dissemination/system_paper_v0.md": "draft system paper surface",
    "docs/dissemination/system_paper_traceability_map.md": "paper claim to evidence/implementation traceability map",
    "docs/dissemination/single_system_paper_contract.md": "single-paper contract and anti-fragmentation surface",
    "docs/dissemination/open_source_successor_ir_contract.md": "successor IR and paper-as-IR contract",
    "docs/dissemination/public_reconstruction_architecture_contract.md": "public reconstruction/projection architecture contract",
    "docs/dissemination/system_capability_register.md": "capability inventory for external claims",
    "docs/dissemination/capability_to_avenue_matrix.md": "capability-to-avenue mapping register",
    "docs/dissemination/demo_variant_catalog.md": "demo variant taxonomy and proof-shape catalog",
    "docs/dissemination/demo_shot_list_v0.md": "demo shot list, current blockers, and proof path",
    "docs/dissemination/private_demo_protocol.md": "controlled private demo protocol",
    "docs/dissemination/platform_terms_red_flags.md": "provider/browser/platform terms risk register",
    "docs/dissemination/release_ip_license_gate_v0.md": "release/IP/license/provenance gate",
    "docs/dissemination/public_leaf_readiness_audit.md": "readiness audit for public leaf/projection",
    "docs/dissemination/public_repo_scale_legibility_strategy_v0.md": "repo-scale legibility strategy binding manifest, idea-first microcosm, route handles, receipts, and omission rules",
    "docs/dissemination/holographic_readme_template.md": "public projection README / proof-atlas template",
    "docs/dissemination/holographic_research_snapshot.md": "private Type B research snapshot contract and builder doctrine",
    "docs/dissemination/disclosure_artifact_registry.md": "disclosure artifact registry",
    "docs/dissemination/provenance_note.md": "provenance framing note",
    "docs/dissemination/external_legibility_packet.md": "external legibility packet",
}

TERM_TAXONOMY = {
    "doctrine_axes": {
        "projection_not_authority": ["projection", "not authority", "source authority", "source of truth", "read model", "sidecar"],
        "standards_as_protocol": ["standard", "standards", "axiom", "validator", "schema", "gate", "compile", "enforcement"],
        "metabolism_compression": ["metabolism", "Russian-doll", "compression", "MAPE-K", "digestion", "raw_seed"],
    },
    "system_surfaces": {
        "system_atlas": ["System Atlas", "atlas", "coverage", "graph", "facts at a glance", "inventory"],
        "workitem_spine": ["WorkItem", "Task Ledger", "Work Ledger", "durable work", "capture", "satisfaction", "cap_"],
        "frontend_cockpit": ["Station", "HUD", "cockpit", "frontend", "StationLens", "operator cockpit"],
        "raw_voice_authority": ["raw seed", "raw voice", "operator voice", "voice-as-authority", "operator intent"],
        "entry_point": ["entry point", "entry points", "cold entrant", "prior packet", "next legal action", "omission boundary"],
        "agent_entry_surface": ["agent entry", "entry surface", "agent entry surface", "AGENTS.override.md", "CODEX.md", "CLAUDE.md", "bootstrap projection"],
        "dissemination_router": ["dissemination router", "dissemination skill", "dissemination cycle", "dissemination understanding", "research prompting", "research assimilation"],
    },
    "artifact_forms": {
        "public_successor_projection": ["public projection", "successor", "microcosm", "manifest-driven", "publication_manifest", "public repo"],
        "paper_as_ir": ["paper-as-IR", "PaperSectionIR", "paper section", "traceability", "paper claim", "single paper"],
        "demo_proof": ["demo", "montage", "shot list", "video", "clip", "walkthrough", "proof surface"],
        "evidence_receipts": ["receipt", "evidence", "claim tier", "claim_id", "verification", "proof obligation"],
    },
    "risk_boundaries": {
        "type_a_type_b_boundary": ["Type A", "Type B", "ASK_TYPE_A", "private facts", "authority boundary"],
        "browser_provider_boundary": ["browser", "provider", "ChatGPT", "Claude", "Gemini", "OpenRouter", "NVIDIA NIM", "ToS", "web app"],
        "portability_gate": ["portability", "portability gate", "clean clone", "public replay", "fixture", "reproducible"],
        "release_safety": ["safety", "IP", "license", "secret scan", "redaction", "disclosure", "omission", "forbidden"],
        "recognition_category": ["recognition", "recognizer", "programming systems", "tools for thought", "moldable", "Engelbart", "Bret Victor", "Future of Coding", "agent framework"],
        "annex_prior_art": ["annex", "prior art", "candidate", "installable", "pattern"],
    },
}

TERM_ALIASES = {
    term: aliases
    for _family, terms in TERM_TAXONOMY.items()
    for term, aliases in terms.items()
}

WEAK_TERM_ALIASES = {
    "IP",
    "entry",
    "gate",
    "compile",
    "fixture",
    "projection",
    "atlas",
    "browser",
    "provider",
    "candidate",
    "standard",
    "standards",
}


def _alias_metadata(term: str, alias: str) -> dict[str, str]:
    normalized_term = term.replace("_", " ").lower()
    normalized_alias = alias.replace("_", " ").lower()
    if alias in WEAK_TERM_ALIASES or len(alias) <= 3:
        specificity = "low"
        match_role = "weak_contextual"
    elif normalized_alias == normalized_term or normalized_alias in normalized_term:
        specificity = "high"
        match_role = "direct"
    elif " " in alias or "-" in alias or "_" in alias:
        specificity = "medium"
        match_role = "contextual_phrase"
    else:
        specificity = "medium"
        match_role = "contextual_token"
    return {"text": alias, "specificity": specificity, "match_role": match_role}

PATH_REFERENCE_RE = re.compile(
    r"(?<!https://)(?<!http://)(?<![\w.-])"
    r"((?:[A-Za-z0-9_.@+-]+/)+[A-Za-z0-9_.@+-]+(?:\.[A-Za-z0-9]+)?|"
    r"[A-Za-z0-9_.@+-]+\.(?:md|json|jsonl|py|yaml|yml|sh|tsx|ts|toml))"
)

PRIVATE_MARKER_PATTERNS = {
    "private_home_path": re.compile("/" + r"Users/[A-Za-z0-9_.-]+"),
    "operator_identity": re.compile(r"operator_account_alias|operator_handle_placeholder", re.IGNORECASE),
    "private_email": re.compile(r"operator_account@example\.invalid", re.IGNORECASE),
    "private_chrome_profile": re.compile(r"Library/Application Support/Google/Chrome"),
    "private_obsidian_path": re.compile(r"\.obsidian/|private Obsidian vault", re.IGNORECASE),
    "browser_provider_symbol": re.compile(
        r"claude_app_injector|chatgpt_session_inject|claude_session_transport|"
        r"claude-in-chrome|gemini_web_session|browser_provider_session"
    ),
    "secret_literal": re.compile(r"BEGIN (?:RSA |OPENSSH |EC |)?PRIVATE KEY"),
    "openai_key_shape": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "github_token_shape": re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    "slack_token_shape": re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    "aws_access_key_shape": re.compile(r"AKIA[0-9A-Z]{16}"),
}

CANONICAL_CLAIMS = {
    "claim:public_object_is_controlled_projection": {
        "text": "The public object is a controlled projection of selected private substrate surfaces, not the private repo.",
        "claim_type": "boundary",
        "claim_strength": "local_documented_policy",
        "preferred_paths": [
            "docs/dissemination/public_projection_boundary_v0.md",
            "docs/dissemination/actual_deliverable_v0.md",
            "docs/dissemination/public_trust_packet_v0.md",
        ],
        "terms": ["public_successor_projection", "release_safety"],
    },
    "claim:public_toggle_red": {
        "text": "The current public toggle is red / not ready.",
        "claim_type": "status",
        "claim_strength": "local_documented_status",
        "preferred_paths": [
            "docs/dissemination/public_trust_packet_v0.md",
            "docs/dissemination/holographic_readme_template.md",
            "docs/dissemination/demo_shot_list_v0.md",
        ],
        "terms": ["release_safety", "portability_gate", "evidence_receipts"],
    },
    "claim:projection_not_authority": {
        "text": "Generated packets, facts cards, views, videos, and public docs are projections unless backed by authority.",
        "claim_type": "authority_model",
        "claim_strength": "root_contract_supported",
        "preferred_paths": [
            "codex/doctrine/paper_modules/system_self_comprehension_root.md",
            "docs/system_atlas/generated_system_facts_at_a_glance.md",
            "dist/type_b/TYPE_B_SYSTEM_GROUNDING_PACKET.md",
        ],
        "terms": ["projection_not_authority"],
    },
    "claim:type_a_type_b_boundary": {
        "text": "Type A and Type B describe substrate authority boundaries, not intelligence rank.",
        "claim_type": "authority_model",
        "claim_strength": "local_documented_policy",
        "preferred_paths": [
            "dist/type_b/TYPE_B_SYSTEM_GROUNDING_PACKET.md",
            "dist/type_b/AI_WORKFLOW_SYSTEM_PACKET.md",
            "docs/system_atlas/generated_system_facts_at_a_glance.md",
        ],
        "terms": ["type_a_type_b_boundary"],
    },
    "claim:workitems_are_execution_memory": {
        "text": "WorkItems and ledgers function as durable execution memory rather than loose chat todos.",
        "claim_type": "substrate_architecture",
        "claim_strength": "local_documented_architecture",
        "preferred_paths": [
            "docs/dissemination/actual_deliverable_v0.md",
            "docs/dissemination/system_capability_register.md",
            "dist/type_b/AI_WORKFLOW_SYSTEM_PACKET.md",
        ],
        "terms": ["workitem_spine", "evidence_receipts"],
    },
    "claim:browser_provider_not_public_path": {
        "text": "Browser/provider UI automation is not the public executable path.",
        "claim_type": "release_boundary",
        "claim_strength": "local_documented_policy",
        "preferred_paths": [
            "docs/dissemination/public_projection_boundary_v0.md",
            "docs/dissemination/platform_terms_red_flags.md",
            "docs/dissemination/public_trust_packet_v0.md",
        ],
        "terms": ["browser_provider_boundary", "release_safety"],
    },
    "claim:paper_as_ir": {
        "text": "The paper is intended to behave as successor IR, binding claims to standards, code, tests, and feedback.",
        "claim_type": "paper_contract",
        "claim_strength": "local_documented_architecture",
        "preferred_paths": [
            "docs/dissemination/actual_deliverable_v0.md",
            "docs/dissemination/system_paper_traceability_map.md",
            "docs/dissemination/open_source_successor_ir_contract.md",
        ],
        "terms": ["paper_as_ir", "standards_as_protocol"],
    },
}

CLAIM_RECEIPT_REQUIREMENTS = {
    "claim:public_object_is_controlled_projection": [
        {
            "receipt_kind": "projection_receipt",
            "expected_receipt_uri": PROJECTION_RECEIPT_URI,
            "producer": "tools/meta/dissemination/render_public_projection.py",
            "command_template": "tools/meta/dissemination/render_public_projection.py --output-root <public_output_root>",
            "required_fields": ["manifest_hash", "source_revision", "included_paths", "omission_receipt", "public_toggle_status"],
            "status": "required_not_embedded",
        }
    ],
    "claim:public_toggle_red": [
        {
            "receipt_kind": "portability_gate_report",
            "expected_receipt_uri": PORTABILITY_GATE_REPORT_URI,
            "producer": "tools/meta/dissemination/portability_gate.py",
            "command_template": "tools/meta/dissemination/portability_gate.py --output-root <public_output_root> --report <public_output_root>/portability_gate_report.json",
            "required_fields": ["overall_status", "source_revision", "hard_blockers", "failed_checks"],
            "status": "required_not_embedded",
        }
    ],
    "claim:projection_not_authority": [
        {
            "receipt_kind": "authority_scope_review",
            "expected_receipt_uri": None,
            "producer": "Type A source-authority review",
            "required_fields": ["source_authority", "projection_scope", "downgrade_condition"],
            "status": "source_evidence_only",
        }
    ],
    "claim:type_a_type_b_boundary": [
        {
            "receipt_kind": "type_a_boundary_review",
            "expected_receipt_uri": None,
            "producer": "Type A source-authority review",
            "required_fields": ["private_fact_boundary", "verification_request_boundary"],
            "status": "source_evidence_only",
        }
    ],
    "claim:workitems_are_execution_memory": [
        {
            "receipt_kind": "task_ledger_status_receipt",
            "expected_receipt_uri": "private-runtime://state/task_ledger/events.jsonl",
            "producer": "tools/meta/factory/task_ledger_apply.py validate",
            "required_fields": ["workitem_id", "event_type", "evidence_ref"],
            "status": "private_runtime_reference_not_embedded",
        }
    ],
    "claim:browser_provider_not_public_path": [
        {
            "receipt_kind": "browser_provider_boundary_review",
            "expected_receipt_uri": None,
            "producer": "Type A provider-boundary review",
            "required_fields": ["forbidden_classes", "allowed_public_representations", "provider_terms_review"],
            "status": "source_evidence_only",
        }
    ],
    "claim:paper_as_ir": [
        {
            "receipt_kind": "paper_traceability_receipt",
            "expected_receipt_uri": None,
            "producer": "paper traceability map review",
            "required_fields": ["claim_id", "source_section", "evidence_refs", "validation_command"],
            "status": "source_evidence_only",
        }
    ],
}

GATE_VERIFICATION_CONTRACTS = {
    "gate:public_toggle": {
        "gate_mode": "receipt_conditioned_release_gate",
        "check_command": (
            "jq '{public_toggle_status, blocking_hit_count:.scan_summary.blocking_hit_count, "
            "policy_exception_count:.scan_summary.policy_exception_count}' "
            f"{PROJECTION_RECEIPT_URI}"
        ),
        "required_receipts": [
            {
                "receipt_kind": "projection_receipt",
                "expected_receipt_uri": PROJECTION_RECEIPT_URI,
                "producer": "tools/meta/dissemination/render_public_projection.py",
                "command_template": "tools/meta/dissemination/render_public_projection.py --output-root <public_output_root>",
                "status": "required_not_embedded",
            },
            {
                "receipt_kind": "portability_gate_report",
                "expected_receipt_uri": PORTABILITY_GATE_REPORT_URI,
                "producer": "tools/meta/dissemination/portability_gate.py",
                "command_template": "tools/meta/dissemination/portability_gate.py --output-root <public_output_root> --report <public_output_root>/portability_gate_report.json",
                "status": "required_not_embedded",
            },
        ],
        "blocking_conditions": [
            "projection receipt missing or stale",
            "portability gate report missing or red",
            "privacy or private-path scan hits remain",
        ],
        "unblock_conditions": [
            "fresh projection receipt points at current clean source revision",
            "portability gate report is green or explicitly waived by Type A",
            "redaction and public-release scan receipts are present",
        ],
    },
    "gate:portability": {
        "gate_mode": "executable_gate",
        "check_command": (
            "./repo-python tools/meta/dissemination/portability_gate.py "
            "--manifest publication_manifest.yaml "
            f"--output-root {PUBLIC_OUTPUT_ROOT_PLACEHOLDER} "
            "--report <public_output_root>/portability_gate_report.json --report-only"
        ),
        "required_receipts": [
            {
                "receipt_kind": "portability_gate_report",
                "expected_receipt_uri": PORTABILITY_GATE_REPORT_URI,
                "producer": "tools/meta/dissemination/portability_gate.py",
                "command_template": "tools/meta/dissemination/portability_gate.py --output-root <public_output_root> --report <public_output_root>/portability_gate_report.json",
                "status": "required_not_embedded",
            },
            {
                "receipt_kind": "projection_receipt",
                "expected_receipt_uri": PROJECTION_RECEIPT_URI,
                "producer": "tools/meta/dissemination/render_public_projection.py",
                "command_template": "tools/meta/dissemination/render_public_projection.py --output-root <public_output_root>",
                "status": "required_not_embedded",
            },
        ],
        "blocking_conditions": [
            "clean worktree or clean detached worktree check fails",
            "projection receipt source revision does not match expected source revision",
            "blocking scan hits or missing outputs remain",
        ],
        "unblock_conditions": [
            "portability gate report overall_status is green",
            "projection receipt source revision and manifest hash match the gate report",
            "all hard blockers are cleared or explicitly waived",
        ],
    },
    "gate:browser_provider_boundary": {
        "gate_mode": "type_a_policy_gate",
        "check_command": (
            "rg -n 'browser|provider|ChatGPT|Claude|Gemini|OpenRouter|NVIDIA NIM|ToS' "
            "docs/dissemination/public_projection_boundary_v0.md "
            "docs/dissemination/platform_terms_red_flags.md"
        ),
        "required_receipts": [
            {
                "receipt_kind": "provider_boundary_review",
                "expected_receipt_uri": None,
                "producer": "Type A provider/platform terms review",
                "status": "source_evidence_only",
            }
        ],
        "blocking_conditions": [
            "public artifact depends on live provider web-app automation",
            "credentials, account/session handling, or provider logs would be exposed",
        ],
        "unblock_conditions": [
            "provider behavior is represented by public API examples, synthetic replay, or inert receipts",
            "platform terms review is complete for any public-facing claim",
        ],
    },
}


def _slug(value: str) -> str:
    value = value.lower().replace(".md", "").replace(".json", "")
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return value or "root"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _repo_uri(rel_path: str | Path) -> str:
    return "repo://" + str(rel_path)


def _row_id_for(table_id: str, row_number: int) -> str:
    table_key = table_id.removeprefix("table:")
    return f"row:{table_key}:{row_number:03d}"


def _artifact_uri_for_receipt_kind(receipt_kind: str, owner_id: str | None = None) -> str:
    if receipt_kind == "projection_receipt":
        return PROJECTION_RECEIPT_URI
    if receipt_kind == "portability_gate_report":
        return PORTABILITY_GATE_REPORT_URI
    if receipt_kind == "task_ledger_status_receipt":
        return "private-runtime://state/task_ledger/events.jsonl"
    if owner_id:
        return f"review://{receipt_kind}/{_slug(owner_id)}"
    return f"review://{receipt_kind}"


def _receipt_id_for_requirement(receipt_kind: str, owner_id: str | None = None) -> str:
    if receipt_kind in {"projection_receipt", "portability_gate_report"}:
        return f"receipt:{receipt_kind}"
    suffix = _slug(owner_id or "global")
    return f"receipt:{receipt_kind}:{suffix}"


def _receipt_local_path(receipt_root: Path, receipt_kind: str) -> Path | None:
    if receipt_kind == "projection_receipt":
        return receipt_root / "projection_receipt.json"
    if receipt_kind == "portability_gate_report":
        return receipt_root / "portability_gate_report.json"
    return None


def _normalize_receipt_requirement(owner_id: str, requirement: dict[str, Any]) -> dict[str, Any]:
    receipt_kind = requirement["receipt_kind"]
    receipt_id = _receipt_id_for_requirement(receipt_kind, owner_id)
    expected_uri = requirement.get("expected_receipt_uri") or _artifact_uri_for_receipt_kind(receipt_kind, owner_id)
    return {
        "receipt_id": receipt_id,
        "receipt_kind": receipt_kind,
        "expected_receipt_uri": expected_uri,
        "producer": requirement.get("producer"),
        "command_template": requirement.get("command_template"),
        "required_fields": requirement.get("required_fields", []),
        "status": "required",
        "requirement_status": requirement.get("status", "required_not_embedded"),
    }


def _receipt_requirements_for_owner(owner_id: str, requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_normalize_receipt_requirement(owner_id, requirement) for requirement in requirements]


def _git_output(args: list[str], repo_root: Path) -> str | None:
    try:
        return subprocess.check_output(args, cwd=repo_root, text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _git_output_bytes(args: list[str], repo_root: Path) -> bytes | None:
    try:
        return subprocess.check_output(args, cwd=repo_root, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _status_path_exists(repo_root: Path, path: str) -> bool:
    return bool(path) and (repo_root / path).exists()


def _status_path_is_file(repo_root: Path, path: str) -> bool:
    return bool(path) and (repo_root / path).is_file()


def _shell_unquote_status_path(path: str) -> tuple[str, bool]:
    stripped = path.strip()
    shell_quoted = stripped.startswith('"') and stripped.endswith('"')
    if not shell_quoted:
        return stripped, False
    try:
        parts = shlex.split(stripped)
    except ValueError:
        return stripped.strip('"'), True
    return (parts[0] if parts else stripped.strip('"')), True


def _status_row_from_parts(
    *,
    raw_status: str,
    xy: str,
    path: str,
    original_path: str | None,
    repo_root: Path,
    parser: str,
    path_was_shell_quoted: bool,
) -> dict[str, Any]:
    index_status = xy[0] if len(xy) >= 1 else ""
    worktree_status = xy[1] if len(xy) >= 2 else ""
    return {
        "raw_status": raw_status,
        "index_status": index_status,
        "worktree_status": worktree_status,
        "path": path,
        "original_path": original_path,
        "path_parser": parser,
        "path_was_shell_quoted": path_was_shell_quoted,
        "exists_in_worktree": _status_path_exists(repo_root, path),
        "is_file_in_worktree": _status_path_is_file(repo_root, path),
    }


def _parse_git_status_row(row: str, repo_root: Path) -> dict[str, Any]:
    xy = row[:2] if len(row) >= 2 else row
    payload = row[3:] if len(row) >= 4 and row[2] == " " else row[2:].strip()
    original_path = None
    path = payload
    path_was_shell_quoted = False
    if " -> " in payload:
        original_path, path = payload.split(" -> ", 1)
        original_path, _ = _shell_unquote_status_path(original_path)
    path, path_was_shell_quoted = _shell_unquote_status_path(path)
    return _status_row_from_parts(
        raw_status=row,
        xy=xy,
        path=path,
        original_path=original_path,
        repo_root=repo_root,
        parser="porcelain_text_fallback",
        path_was_shell_quoted=path_was_shell_quoted,
    )


def _decode_git_status_token(token: bytes) -> str:
    return token.decode("utf-8", errors="surrogateescape")


def _parse_git_status_z(raw_status: bytes, repo_root: Path) -> list[dict[str, Any]]:
    tokens = [token for token in raw_status.split(b"\0") if token]
    rows: list[dict[str, Any]] = []
    index = 0
    while index < len(tokens):
        token = _decode_git_status_token(tokens[index])
        xy = token[:2] if len(token) >= 2 else token
        path = token[3:] if len(token) >= 4 and token[2] == " " else token[2:].strip()
        original_path = None
        index_status = xy[0] if len(xy) >= 1 else ""
        worktree_status = xy[1] if len(xy) >= 2 else ""
        if (index_status in {"R", "C"} or worktree_status in {"R", "C"}) and index + 1 < len(tokens):
            index += 1
            original_path = _decode_git_status_token(tokens[index])
        rows.append(
            _status_row_from_parts(
                raw_status=f"{xy} {path}" + (f" -> {original_path}" if original_path else ""),
                xy=xy,
                path=path,
                original_path=original_path,
                repo_root=repo_root,
                parser="porcelain_v1_z",
                path_was_shell_quoted=False,
            )
        )
        index += 1
    return rows


def _git_status_rows(repo_root: Path) -> list[dict[str, Any]]:
    raw_z = _git_output_bytes(["git", "status", "--porcelain=v1", "-z"], repo_root)
    if raw_z is not None:
        return _parse_git_status_z(raw_z, repo_root)
    status = _git_output(["git", "status", "--porcelain"], repo_root) or ""
    return [_parse_git_status_row(line, repo_root) for line in status.splitlines() if line.strip()]


def _git_state(repo_root: Path) -> dict[str, Any]:
    dirty_rows = _git_status_rows(repo_root)
    return {
        "commit": _git_output(["git", "rev-parse", "HEAD"], repo_root),
        "branch": _git_output(["git", "branch", "--show-current"], repo_root),
        "dirty": bool(dirty_rows),
        "dirty_count": len(dirty_rows),
        "dirty_paths": [row["path"] for row in dirty_rows],
        "dirty_status_rows": dirty_rows,
        "dirty_paths_truncated": False,
    }


def _classify_category(rel_path: str) -> str:
    if "system_self_comprehension" in rel_path or rel_path.startswith("dist/type_b/"):
        return "system_identity"
    if rel_path.startswith("docs/system_atlas/") or rel_path.startswith("state/system_atlas/"):
        return "system_atlas"
    if rel_path == "docs/dissemination/README.md":
        return "dissemination_router"
    if "actual_deliverable" in rel_path:
        return "deliverable_authority"
    if any(key in rel_path for key in ("public_projection_boundary", "safety_boundary", "release_ip_license", "public_leaf_readiness", "platform_terms")):
        return "public_boundary"
    if any(key in rel_path for key in ("system_paper", "single_system_paper", "open_source_successor_ir")):
        return "paper_contract"
    if "demo_" in rel_path or "private_demo" in rel_path:
        return "demo_proof"
    if any(key in rel_path for key in ("recognition_grade", "system_capability", "capability_to_avenue", "external_legibility")):
        return "capability_legibility"
    if any(key in rel_path for key in ("public_trust", "disclosure_artifact", "provenance_note", "holographic_readme", "holographic_research_snapshot")):
        return "trust_provenance"
    return "other"


def _authority_scopes(rel_path: str) -> list[dict[str, Any]]:
    scopes: list[dict[str, Any]] = []
    if "system_self_comprehension_root" in rel_path:
        scopes.append({"scope": "system_identity", "posture": "root_contract", "weight": 100})
    if rel_path == "docs/dissemination/actual_deliverable_v0.md":
        scopes.append({"scope": "public_deliverable", "posture": "primary_deliverable_authority", "weight": 95})
    if rel_path == "docs/dissemination/public_projection_boundary_v0.md":
        scopes.append({"scope": "public_boundary", "posture": "boundary_policy", "weight": 92})
    if rel_path.startswith("state/") or "generated_" in rel_path or rel_path.startswith("dist/type_b/"):
        scopes.append({"scope": "read_model", "posture": "projection_not_authority", "weight": 40})
    if rel_path.startswith("docs/dissemination/") and not scopes:
        scopes.append({"scope": "dissemination_policy_or_register", "posture": "policy_or_register", "weight": 70})
    if rel_path.startswith("docs/system_atlas/") and not scopes:
        scopes.append({"scope": "atlas_read_model", "posture": "atlas_read_model", "weight": 65})
    if rel_path.startswith("codex/doctrine/") and not scopes:
        scopes.append({"scope": "doctrine", "posture": "doctrine_or_policy_surface", "weight": 80})
    if not scopes:
        scopes.append({"scope": "general", "posture": "projection_or_policy_surface", "weight": 50})
    return scopes


def _dominant_authority(scopes: list[dict[str, Any]]) -> dict[str, Any]:
    return max(scopes, key=lambda item: int(item.get("weight", 0)))


def _iter_lines_outside_fences(lines: list[str]):
    in_fence = False
    fence_marker = ""
    language = ""
    block_start = 0
    block_lines: list[str] = []
    embedded_blocks: list[dict[str, Any]] = []
    for lineno, line in enumerate(lines, 1):
        marker = re.match(r"^\s*(```|~~~)\s*([A-Za-z0-9_-]+)?", line)
        if marker:
            if not in_fence:
                in_fence = True
                fence_marker = marker.group(1)
                language = marker.group(2) or ""
                block_start = lineno
                block_lines = [line]
                yield lineno, line, True, embedded_blocks
                continue
            if line.strip().startswith(fence_marker):
                block_lines.append(line)
                detected = []
                for offset, block_line in enumerate(block_lines, block_start):
                    if re.match(r"^\s{0,3}#{1,6}\s+", block_line):
                        detected.append({"line": offset, "text": block_line.strip(), "structural": False})
                embedded_blocks.append(
                    {
                        "kind": "fenced_code",
                        "language": language,
                        "line_start": block_start,
                        "line_end": lineno,
                        "detected_headings": detected,
                    }
                )
                in_fence = False
                fence_marker = ""
                language = ""
                yield lineno, line, True, embedded_blocks
                continue
        if in_fence:
            block_lines.append(line)
            yield lineno, line, True, embedded_blocks
        else:
            yield lineno, line, False, embedded_blocks


def _extract_structural_headings(lines: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    headings: list[dict[str, Any]] = []
    embedded_blocks: list[dict[str, Any]] = []
    for lineno, line, in_fence, blocks in _iter_lines_outside_fences(lines):
        embedded_blocks = blocks
        if in_fence:
            continue
        match = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$", line)
        if match:
            headings.append({"line": lineno, "level": len(match.group(1)), "text": match.group(2).strip()})
    return headings, embedded_blocks


def _chunk_markdown(doc_id: str, rel_path: str, text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    lines = text.splitlines()
    headings, embedded_blocks = _extract_structural_headings(lines)
    starts: list[dict[str, Any]] = []
    if not headings or headings[0]["line"] > 1:
        starts.append({"line": 1, "level": 0, "text": "Preamble"})
    starts.extend(headings)
    chunks: list[dict[str, Any]] = []
    for index, heading in enumerate(starts, 1):
        start = int(heading["line"])
        end = int(starts[index]["line"]) - 1 if index < len(starts) else len(lines)
        if start > end:
            continue
        heading_path: list[str] = []
        if heading["level"] == 0:
            heading_path = ["Preamble"]
        else:
            stack: list[dict[str, Any]] = []
            for prior in starts[:index]:
                if prior["level"] == 0:
                    continue
                stack = [item for item in stack if item["level"] < prior["level"]]
                stack.append(prior)
            heading_path = [item["text"] for item in stack]
        content = "\n".join(lines[start - 1 : end])
        chunk_id = f"chunk:{_slug(rel_path)}:{index:03d}"
        chunks.append(
            {
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "source_uri": _repo_uri(rel_path),
                "title": heading["text"],
                "heading_level": heading["level"],
                "heading_path": heading_path,
                "source_span": {"line_start": start, "line_end": end},
                "char_count": len(content),
                "sha256": _sha256_text(content),
                "summary_hint": " ".join(content.strip().split())[:360],
                "content": content,
            }
        )
    return chunks, embedded_blocks


def _chunk_json(doc_id: str, rel_path: str, text: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        content = text
        return [
            {
                "chunk_id": f"chunk:{_slug(rel_path)}:001",
                "doc_id": doc_id,
                "source_uri": _repo_uri(rel_path),
                "title": "JSON text",
                "heading_level": 0,
                "heading_path": ["JSON text"],
                "source_span": None,
                "char_count": len(content),
                "sha256": _sha256_text(content),
                "summary_hint": " ".join(content.strip().split())[:360],
                "content": content,
            }
        ]
    if isinstance(payload, dict):
        items = list(payload.items())
    else:
        items = [("JSON root", payload)]
    chunks = []
    for index, (key, value) in enumerate(items, 1):
        content = json.dumps({key: value}, ensure_ascii=False, indent=2)
        chunks.append(
            {
                "chunk_id": f"chunk:{_slug(rel_path)}:{index:03d}",
                "doc_id": doc_id,
                "source_uri": _repo_uri(rel_path),
                "title": str(key),
                "heading_level": 1,
                "heading_path": [str(key)],
                "source_span": None,
                "char_count": len(content),
                "sha256": _sha256_text(content),
                "summary_hint": " ".join(content.strip().split())[:360],
                "content": content,
            }
        )
    return chunks


def _detect_terms(text: str) -> tuple[list[str], dict[str, list[dict[str, Any]]]]:
    detected: list[str] = []
    matches: dict[str, list[dict[str, Any]]] = {}
    for term, aliases in TERM_ALIASES.items():
        term_matches: list[dict[str, Any]] = []
        for alias in aliases:
            for match in re.finditer(re.escape(alias), text, re.IGNORECASE):
                term_matches.append({"alias": alias, "span": [match.start(), match.end()], **_alias_metadata(term, alias)})
                if len(term_matches) >= 25:
                    break
            if len(term_matches) >= 25:
                break
        if term_matches:
            detected.append(term)
            matches[term] = term_matches
    return sorted(detected), matches


def _canonical_term_ids(terms: list[str] | tuple[str, ...] | set[str]) -> list[str]:
    return sorted(f"term:{term}" if not str(term).startswith("term:") else str(term) for term in terms)


def _attach_term_ids(
    documents: dict[str, Any],
    chunks: dict[str, Any],
    claims: dict[str, Any],
    gates: dict[str, Any],
    routes: dict[str, Any],
) -> None:
    for objects in (documents, chunks, claims, gates, routes):
        for obj in objects.values():
            if obj.get("terms"):
                obj["term_ids"] = _canonical_term_ids(obj["terms"])
            else:
                obj["term_ids"] = []


def _extract_markdown_tables(chunks: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    tables: dict[str, Any] = {}
    rows: dict[str, Any] = {}
    table_indexes_by_source: dict[str, int] = defaultdict(int)
    for chunk_id, chunk in chunks.items():
        lines = chunk["content"].splitlines()
        in_fence = False
        line_offset = (chunk.get("source_span") or {}).get("line_start") or 1
        idx = 0
        while idx < len(lines):
            line = lines[idx]
            if re.match(r"^\s*(```|~~~)", line):
                in_fence = not in_fence
                idx += 1
                continue
            if in_fence or "|" not in line or idx + 1 >= len(lines):
                idx += 1
                continue
            separator = lines[idx + 1]
            if "|" not in separator or not re.match(r"^\s*\|?[\s:|-]+\|[\s:|-]+\|?\s*$", separator):
                idx += 1
                continue
            header = _split_table_row(line)
            if not header:
                idx += 1
                continue
            row_start = idx
            row_lines = []
            idx += 2
            while idx < len(lines) and "|" in lines[idx] and not re.match(r"^\s*(```|~~~)", lines[idx]):
                row_lines.append(lines[idx])
                idx += 1
            if not row_lines:
                continue
            source_slug = _slug(chunk["source_uri"].replace("repo://", ""))
            table_indexes_by_source[source_slug] += 1
            table_index = table_indexes_by_source[source_slug]
            table_id = f"table:{source_slug}:t{table_index:03d}"
            row_ids: list[str] = []
            for row_number, row_line in enumerate(row_lines, 1):
                values = _split_table_row(row_line)
                cells = {header[col]: values[col] if col < len(values) else "" for col in range(len(header))}
                first_value = next((value for value in cells.values() if value), f"row_{row_number:03d}")
                row_id = _row_id_for(table_id, row_number)
                rows[row_id] = {
                    "row_id": row_id,
                    "table_id": table_id,
                    "semantic_key": _slug(first_value),
                    "chunk_id": chunk_id,
                    "doc_id": chunk["doc_id"],
                    "source_uri": chunk["source_uri"],
                    "source_span": {
                        "line_start": line_offset + row_start + row_number + 1,
                        "line_end": line_offset + row_start + row_number + 1,
                    },
                    "cells": cells,
                }
                row_ids.append(row_id)
            tables[table_id] = {
                "table_id": table_id,
                "chunk_id": chunk_id,
                "doc_id": chunk["doc_id"],
                "source_uri": chunk["source_uri"],
                "source_span": {
                    "line_start": line_offset + row_start,
                    "line_end": line_offset + idx - 1,
                },
                "columns": header,
                "row_ids": row_ids,
                "row_count": len(row_ids),
                "id_strategy": "document_local_table_ordinal_v1",
            }
        # Continue scanning the next chunk.
    return tables, rows


def _split_table_row(line: str) -> list[str]:
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    return [cell.strip().replace("<br>", "\n") for cell in text.split("|")]


def _repo_file_index(repo_root: Path) -> tuple[set[str], dict[str, list[str]]]:
    files = set((_git_output(["git", "ls-files"], repo_root) or "").splitlines())
    basename_map: dict[str, list[str]] = defaultdict(list)
    for rel_path in sorted(path for path in files if path):
        basename_map[Path(rel_path).name].append(rel_path)
    return files, basename_map


def _looks_like_conceptual_slash_phrase(path: str, repo_root: Path) -> bool:
    if (repo_root / path).exists():
        return False
    if Path(path).suffix:
        return False
    parts = path.split("/")
    if len(parts) < 2 or len(parts) > 3:
        return False
    known_roots = {
        "annexes",
        "codex",
        "dist",
        "docs",
        "obsidian",
        "runtime",
        "state",
        "system",
        "tests",
        "tools",
    }
    if parts[0] in known_roots:
        return False
    return all(re.fullmatch(r"[A-Za-z0-9_.@+-]+", part or "") for part in parts)


def _privacy_scope_for_path(path: str | None) -> dict[str, Any]:
    if not path:
        return {"privacy_class": "unknown", "volatility": "unknown"}
    if path.startswith(PUBLIC_PROJECTION_ARTIFACT_ROOT):
        return {"privacy_class": "public_projection_artifact", "volatility": "generated_receipt_or_projection_control"}
    if path.startswith("obsidian/"):
        return {"privacy_class": "private_obsidian_surface", "volatility": "operator_private_surface"}
    if path.startswith("state/"):
        return {"privacy_class": "private_runtime_state", "volatility": "volatile_runtime_state"}
    if path.startswith((".claude/", ".codex/")):
        return {"privacy_class": "private_agent_runtime_surface", "volatility": "volatile_runtime_state"}
    if path.startswith(("runtime/", "tmp/")):
        return {"privacy_class": "runtime_surface", "volatility": "volatile_runtime_state"}
    return {"privacy_class": "repo_surface", "volatility": "source_or_projection"}


def _receipt_artifact_reference(raw_ref: str) -> dict[str, Any] | None:
    ref = raw_ref.lstrip("./")
    basename = Path(ref).name
    target = RECEIPT_ARTIFACT_REFERENCES.get(basename)
    if not target:
        return None
    return {
        "artifact_uri": target["artifact_uri"],
        "resolved_to_receipt_id": target["resolved_to_receipt_id"],
        "receipt_kind": target["receipt_kind"],
        "receipt_resolution_status": target["receipt_resolution_status"],
    }


def _resolve_reference_path(
    raw_ref: str,
    chunk: dict[str, Any],
    repo_root: Path,
    selected_paths: set[str],
    tracked_files: set[str],
    basename_map: dict[str, list[str]],
) -> dict[str, Any]:
    ref = raw_ref.lstrip("./")
    receipt_reference = _receipt_artifact_reference(ref)
    if receipt_reference:
        scope = _privacy_scope_for_path(receipt_reference["artifact_uri"])
        return {
            "path": ref,
            "resolved_to": None,
            "resolution": "receipt_artifact_uri",
            "exists_in_repo": False,
            "tracked_in_git": False,
            "selected_for_embedding": False,
            "classification": "receipt_artifact_reference",
            **scope,
            **receipt_reference,
        }

    source_rel = chunk["source_uri"].replace("repo://", "")
    source_dir = str(Path(source_rel).parent)
    direct_exists = (repo_root / ref).exists()
    tracked = ref in tracked_files
    selected = ref in selected_paths
    resolved_to = ref if direct_exists else None
    resolution = "direct_path" if direct_exists else None
    resolution_policy = None
    candidate_count = None
    private_candidate_count = None

    if not resolved_to and "/" not in ref:
        relative_candidate = str(Path(source_dir) / ref)
        if (repo_root / relative_candidate).exists():
            resolved_to = relative_candidate
            resolution = "source_relative_basename"

    if not resolved_to and "/" not in ref:
        candidates = basename_map.get(ref, [])
        if ref == "raw_seed.md" and candidates:
            private_candidates = sorted(candidate for candidate in candidates if candidate.startswith("obsidian/"))
            candidate_count = len(candidates)
            private_candidate_count = len(private_candidates)
            if len(private_candidates) == 1:
                resolved_to = private_candidates[0]
                resolution = "private_surface_basename_policy"
            else:
                resolution_policy = "ambiguous_or_forbidden_private_surface"
        selected_candidates = [candidate for candidate in candidates if candidate in selected_paths]
        existing_candidates = [candidate for candidate in candidates if (repo_root / candidate).exists()]
        if not resolved_to and len(selected_candidates) == 1:
            resolved_to = selected_candidates[0]
            resolution = "selected_basename"
        elif not resolved_to and len(existing_candidates) == 1:
            resolved_to = existing_candidates[0]
            resolution = "unique_repo_basename"

    if resolved_to:
        exists_in_repo = (repo_root / resolved_to).exists()
        selected_for_embedding = resolved_to in selected_paths
    else:
        exists_in_repo = direct_exists
        selected_for_embedding = selected

    scope = _privacy_scope_for_path(resolved_to or ref)
    if resolution_policy == "ambiguous_or_forbidden_private_surface":
        scope = {
            "privacy_class": "ambiguous_private_or_repo_surface",
            "volatility": "resolution_withheld_private_surface_possible",
        }

    if selected_for_embedding:
        classification = "included_selected_source"
    elif scope["volatility"] == "volatile_runtime_state":
        classification = "referenced_volatile_runtime_state_not_embedded"
    elif resolved_to and scope["privacy_class"] != "repo_surface":
        classification = "basename_reference_resolved_private_surface"
    elif resolved_to and exists_in_repo:
        classification = "basename_reference_resolved" if resolution != "direct_path" else "referenced_existing_not_embedded"
    elif ref.startswith(("state/", "obsidian/", ".claude/", ".codex/")):
        classification = "referenced_private_or_runtime_surface"
    elif direct_exists:
        classification = "referenced_existing_not_embedded"
    elif tracked:
        classification = "referenced_tracked_missing_in_worktree"
    elif _looks_like_conceptual_slash_phrase(ref, repo_root):
        classification = "conceptual_slash_phrase"
    else:
        classification = "referenced_unresolved_or_planned"

    result = {
        "path": ref,
        "resolved_to": resolved_to,
        "resolution": resolution,
        "exists_in_repo": exists_in_repo,
        "tracked_in_git": tracked or (resolved_to in tracked_files if resolved_to else False),
        "selected_for_embedding": selected_for_embedding,
        "classification": classification,
        **scope,
    }
    if resolution_policy:
        result["resolution_policy"] = resolution_policy
        result["resolution_blocked_reason"] = "would_resolve_to_private_obsidian_raw_seed_surface_or_multiple_candidates"
    if candidate_count is not None:
        result["candidate_count"] = candidate_count
    if private_candidate_count is not None:
        result["private_candidate_count"] = private_candidate_count
    return result


REFERENCE_CLASS_PRIORITY = {
    "included_selected_source": 10,
    "referenced_existing_not_embedded": 20,
    "receipt_artifact_reference": 25,
    "basename_reference_resolved": 30,
    "basename_reference_resolved_private_surface": 40,
    "referenced_private_or_runtime_surface": 50,
    "referenced_volatile_runtime_state_not_embedded": 60,
    "referenced_tracked_missing_in_worktree": 70,
    "referenced_unresolved_or_planned": 80,
    "conceptual_slash_phrase": 90,
}


def _primary_reference_classification(classifications: list[str]) -> str | None:
    if not classifications:
        return None
    return sorted(classifications, key=lambda value: REFERENCE_CLASS_PRIORITY.get(value, 999))[0]


def _extract_path_references(chunks: dict[str, dict[str, Any]], repo_root: Path, selected_paths: set[str]) -> dict[str, Any]:
    refs: dict[str, dict[str, Any]] = {}
    tracked_files, basename_map = _repo_file_index(repo_root)
    for chunk in chunks.values():
        for match in PATH_REFERENCE_RE.finditer(chunk["content"]):
            raw = match.group(1).strip("`'\"),.;:")
            if raw.startswith(("http", "www.")) or "://" in raw:
                continue
            if raw.startswith("../"):
                continue
            if raw in {".md", ".json"}:
                continue
            ref = raw.lstrip("./")
            if not ref:
                continue
            resolution = _resolve_reference_path(ref, chunk, repo_root, selected_paths, tracked_files, basename_map)
            entry = refs.setdefault(
                ref,
                {
                    "reference_count": 0,
                    "referenced_from": [],
                    **resolution,
                },
            )
            entry["reference_count"] += 1
            if len(entry["referenced_from"]) < 25:
                entry["referenced_from"].append(
                    {
                        "chunk_id": chunk["chunk_id"],
                        "doc_id": chunk["doc_id"],
                        "source_uri": chunk["source_uri"],
                    }
                )
    for entry in refs.values():
        emitted = len(entry["referenced_from"])
        entry["emitted_reference_count"] = emitted
        entry["referenced_from_truncated"] = entry["reference_count"] > emitted
        entry["truncation_policy"] = "first_25_by_source_order" if entry["referenced_from_truncated"] else None
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in sorted(refs.values(), key=lambda item: (-item["reference_count"], item["path"])):
        by_class[entry["classification"]].append(entry)
    canonical_artifacts: dict[str, dict[str, Any]] = {}
    for entry in sorted(refs.values(), key=lambda item: (item.get("resolved_to") or item["path"], item["path"])):
        resolved_to = entry.get("resolved_to")
        if entry.get("artifact_uri"):
            artifact_key = entry["artifact_uri"]
        elif resolved_to:
            artifact_key = _repo_uri(resolved_to)
        else:
            artifact_key = f"unresolved://{entry['path']}"
        artifact = canonical_artifacts.setdefault(
            artifact_key,
            {
                "artifact_id": artifact_key,
                "resolved_to": resolved_to,
                "mention_strings": [],
                "mention_classifications": {},
                "classifications": [],
                "reference_count_total": 0,
                "selected_for_embedding": False,
                "exists_in_repo": False,
                "tracked_in_git": False,
                "privacy_class": entry.get("privacy_class"),
                "volatility": entry.get("volatility"),
                "artifact_uri": entry.get("artifact_uri"),
                "resolved_to_receipt_id": entry.get("resolved_to_receipt_id"),
                "receipt_kind": entry.get("receipt_kind"),
                "receipt_resolution_status": entry.get("receipt_resolution_status"),
                "resolution_policy": entry.get("resolution_policy"),
                "resolution_blocked_reason": entry.get("resolution_blocked_reason"),
            },
        )
        artifact["mention_strings"].append(entry["path"])
        artifact["mention_classifications"][entry["path"]] = entry["classification"]
        artifact["classifications"].append(entry["classification"])
        artifact["reference_count_total"] += int(entry.get("reference_count", 0))
        artifact["selected_for_embedding"] = artifact["selected_for_embedding"] or bool(entry.get("selected_for_embedding"))
        artifact["exists_in_repo"] = artifact["exists_in_repo"] or bool(entry.get("exists_in_repo"))
        artifact["tracked_in_git"] = artifact["tracked_in_git"] or bool(entry.get("tracked_in_git"))
        for field in (
            "artifact_uri",
            "resolved_to_receipt_id",
            "receipt_kind",
            "receipt_resolution_status",
            "resolution_policy",
            "resolution_blocked_reason",
        ):
            if artifact.get(field) is None and entry.get(field) is not None:
                artifact[field] = entry[field]
    for artifact in canonical_artifacts.values():
        artifact["mention_strings"] = sorted(set(artifact["mention_strings"]))
        artifact["classifications"] = sorted(set(artifact["classifications"]))
        artifact["mention_classifications"] = dict(sorted(artifact["mention_classifications"].items()))
        primary = _primary_reference_classification(artifact["classifications"])
        artifact["primary_classification"] = primary
        artifact["classification"] = primary
    canonical_by_class_counts: dict[str, int] = defaultdict(int)
    classification_record_counts: dict[str, int] = defaultdict(int)
    for artifact in canonical_artifacts.values():
        if artifact.get("primary_classification"):
            canonical_by_class_counts[artifact["primary_classification"]] += 1
        for classification in artifact.get("classifications", []):
            classification_record_counts[classification] += 1
    return {
        "total_unique_referenced_paths": len(refs),
        "count_basis": {
            "total_unique_referenced_paths": "mention_string",
            "by_class_counts": "mention_string",
            "canonical_artifact_count": "canonical_artifact",
            "canonical_by_class_counts": "canonical_artifact_primary_classification",
            "classification_record_counts": "canonical_artifact_classification_records",
        },
        "canonical_artifact_count": len(canonical_artifacts),
        "canonical_artifacts": canonical_artifacts,
        "by_class_counts": {key: len(value) for key, value in by_class.items()},
        "canonical_by_class_counts": dict(sorted(canonical_by_class_counts.items())),
        "classification_record_counts": dict(sorted(classification_record_counts.items())),
        "by_class": {key: value[:250] for key, value in by_class.items()},
        "truncated_classes": {key: len(value) > 250 for key, value in by_class.items()},
    }


def _referenced_path_lookup(path_references: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for entries in path_references.get("by_class", {}).values():
        for entry in entries:
            lookup.setdefault(entry["path"], entry)
            if entry.get("resolved_to"):
                lookup.setdefault(entry["resolved_to"], entry)
    for artifact in path_references.get("canonical_artifacts", {}).values():
        if artifact.get("resolved_to"):
            lookup.setdefault(artifact["resolved_to"], artifact)
        for mention in artifact.get("mention_strings", []):
            lookup.setdefault(mention, artifact)
    return lookup


def _dedupe_dirty_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any, Any]] = set()
    for row in rows:
        key = (row.get("raw_status"), row.get("path"), row.get("working_tree_sha256"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _annotate_referenced_artifacts_with_working_tree(
    path_references: dict[str, Any],
    working_tree: dict[str, Any],
) -> dict[str, Any]:
    dirty_by_path = {row["path"]: row for row in working_tree.get("dirty_paths_detail", [])}
    for artifact in path_references.get("canonical_artifacts", {}).values():
        candidates = [artifact.get("resolved_to")] + list(artifact.get("mention_strings", []))
        dirty_rows = _dedupe_dirty_rows([dirty_by_path[path] for path in candidates if path in dirty_by_path])
        artifact["working_tree_dirty"] = bool(dirty_rows)
        artifact["dirty_status_rows"] = dirty_rows
    for entries in path_references.get("by_class", {}).values():
        for entry in entries:
            candidates = [entry.get("resolved_to"), entry.get("path")]
            dirty_rows = _dedupe_dirty_rows([dirty_by_path[path] for path in candidates if path in dirty_by_path])
            entry["working_tree_dirty"] = bool(dirty_rows)
            entry["dirty_status_rows"] = dirty_rows
    return path_references


def _git_head_blob_sha256(repo_root: Path, path: str) -> str | None:
    blob = _git_output_bytes(["git", "show", f"HEAD:{path}"], repo_root)
    if blob is None:
        return None
    return hashlib.sha256(blob).hexdigest()


def _git_diff_text(repo_root: Path, path: str) -> str:
    unstaged = _git_output(["git", "diff", "--", path], repo_root) or ""
    staged = _git_output(["git", "diff", "--cached", "--", path], repo_root) or ""
    return "\n".join(part for part in (staged, unstaged) if part)


def _dirty_provenance_sidecar_id(path: str) -> str:
    return f"dirty_provenance:{_slug(path)}"


def _dirty_provenance_sidecar(
    repo_root: Path,
    detail: dict[str, Any],
    *,
    coverage_scope: str,
    diff_excerpt_limit: int = 4000,
) -> dict[str, Any]:
    path = detail["path"]
    diff_text = _git_diff_text(repo_root, path)
    diff_sha256 = _sha256_text(diff_text) if diff_text else None
    is_private_or_runtime = detail.get("privacy_class") != "repo_surface" or detail.get("volatility") == "volatile_runtime_state"
    if detail.get("volatility") == "operator_private_surface":
        diff_excerpt_policy = "hash_only_operator_private_surface"
    elif detail.get("volatility") == "volatile_runtime_state":
        diff_excerpt_policy = "hash_only_volatile_runtime_state"
    elif detail.get("privacy_class") != "repo_surface":
        diff_excerpt_policy = "hash_only_private_or_sensitive_surface"
    else:
        diff_excerpt_policy = f"first_{diff_excerpt_limit}_chars"
    sidecar = {
        "sidecar_id": _dirty_provenance_sidecar_id(path),
        "path": path,
        "coverage_scope": coverage_scope,
        "raw_status": detail.get("raw_status"),
        "index_status": detail.get("index_status"),
        "worktree_status": detail.get("worktree_status"),
        "working_tree_sha256": detail.get("working_tree_sha256"),
        "embedded_content_sha256": detail.get("working_tree_sha256") if detail.get("embedded_document") else None,
        "dirty_embedded_source_content_captured": bool(detail.get("embedded_document")),
        "dirty_embedded_source_commit_authority": False if detail.get("embedded_document") else None,
        "head_sha256": _git_head_blob_sha256(repo_root, path),
        "diff_sha256": diff_sha256,
        "diff_excerpt_policy": diff_excerpt_policy,
        "privacy_class": detail.get("privacy_class"),
        "volatility": detail.get("volatility"),
    }
    if is_private_or_runtime:
        sidecar["diff_excerpt"] = None
    else:
        sidecar["diff_excerpt"] = diff_text[:diff_excerpt_limit]
        sidecar["diff_excerpt_truncated"] = len(diff_text) > diff_excerpt_limit
    return sidecar


def _working_tree_manifest(
    repo_root: Path,
    selected_paths: set[str],
    path_references: dict[str, Any],
) -> dict[str, Any]:
    repo_state = _git_state(repo_root)
    status_rows = repo_state.get("dirty_status_rows", [])
    referenced_lookup = _referenced_path_lookup(path_references)
    generator_path = "tools/meta/dissemination/build_holographic_research_bundle.py"
    selected_dirty_sources: list[dict[str, Any]] = []
    dirty_referenced_not_embedded: list[dict[str, Any]] = []
    dirty_runtime_state_not_embedded: list[dict[str, Any]] = []
    dirty_paths_detail: list[dict[str, Any]] = []
    dirty_provenance_sidecars: dict[str, dict[str, Any]] = {}
    dirty_selected_source_sidecar_count = 0
    dirty_referenced_not_embedded_sidecar_count = 0

    for row in status_rows:
        path = row["path"]
        exists = bool(row.get("exists_in_worktree"))
        is_file = bool(row.get("is_file_in_worktree"))
        selected = path in selected_paths
        reference_entry = referenced_lookup.get(path)
        working_tree_sha256 = _sha256_file(repo_root / path) if exists and is_file else None
        scope = _privacy_scope_for_path(path)
        detail = {
            **row,
            "path_has_shell_quotes": path.startswith('"') or path.endswith('"'),
            "selected_for_embedding": selected,
            "embedded_document": selected and exists,
            "referenced_by_snapshot": reference_entry is not None,
            "reference_classification": reference_entry.get("classification") if reference_entry else None,
            "working_tree_sha256": working_tree_sha256,
            **scope,
        }
        dirty_paths_detail.append(detail)
        if selected:
            sidecar = _dirty_provenance_sidecar(repo_root, detail, coverage_scope="selected_embedded_source")
            sidecar_id = sidecar["sidecar_id"]
            detail["dirty_provenance_sidecar_id"] = sidecar_id
            detail["dirty_provenance_sidecar_path"] = path
            dirty_provenance_sidecars[sidecar_id] = sidecar
            dirty_selected_source_sidecar_count += 1
            selected_dirty_sources.append(detail)
        elif reference_entry:
            sidecar = _dirty_provenance_sidecar(repo_root, detail, coverage_scope="referenced_not_embedded")
            sidecar_id = sidecar["sidecar_id"]
            detail["dirty_provenance_sidecar_id"] = sidecar_id
            detail["dirty_provenance_sidecar_path"] = path
            dirty_provenance_sidecars[sidecar_id] = sidecar
            dirty_referenced_not_embedded_sidecar_count += 1
            dirty_referenced_not_embedded.append(detail)
        if scope["volatility"] == "volatile_runtime_state" and not selected:
            dirty_runtime_state_not_embedded.append(detail)

    dirty_generator = next((row for row in dirty_paths_detail if row["path"] == generator_path), None)
    malformed_dirty_paths = [
        row
        for row in dirty_paths_detail
        if (
            row["raw_status"]
            and (
                not row["path"]
                or row.get("path_has_shell_quotes")
                or (
                    row.get("worktree_status") != "D"
                    and row.get("index_status") != "D"
                    and not row.get("exists_in_worktree")
                )
            )
        )
    ]
    referenced_or_selected_dirty = [
        row for row in dirty_paths_detail if row.get("selected_for_embedding") or row.get("referenced_by_snapshot")
    ]
    unreferenced_dirty = [
        row
        for row in dirty_paths_detail
        if not row.get("selected_for_embedding") and not row.get("referenced_by_snapshot")
    ]
    dirty_scope_summary = {
        "count_basis": "git_status_path",
        "total_dirty_count": repo_state["dirty_count"],
        "referenced_or_selected_dirty_count": len(referenced_or_selected_dirty),
        "selected_embedded_dirty_count": len(selected_dirty_sources),
        "referenced_not_embedded_dirty_count": len(dirty_referenced_not_embedded),
        "dirty_runtime_state_not_embedded_count": len(dirty_runtime_state_not_embedded),
        "unreferenced_dirty_count": len(unreferenced_dirty),
        "unreferenced_annex_sync_dirty_count": sum(
            1 for row in unreferenced_dirty if str(row.get("path", "")).startswith("annexes/")
        ),
        "private_obsidian_dirty_count": sum(
            1 for row in dirty_paths_detail if row.get("privacy_class") == "private_obsidian_surface"
        ),
        "operator_private_dirty_count": sum(
            1 for row in dirty_paths_detail if row.get("volatility") == "operator_private_surface"
        ),
        "repo_surface_dirty_count": sum(
            1 for row in dirty_paths_detail if row.get("privacy_class") == "repo_surface"
        ),
        "sidecarred_dirty_count": len(dirty_provenance_sidecars),
        "all_dirty_paths_sidecarred": len(dirty_provenance_sidecars) == repo_state["dirty_count"],
        "note": "Private proof-bundle rollup: referenced/selected dirty authority is sidecarred separately from unreferenced repo dirt.",
    }
    return {
        "dirty": repo_state["dirty"],
        "dirty_count": repo_state["dirty_count"],
        "commit": repo_state["commit"],
        "branch": repo_state["branch"],
        "dirty_paths_truncated": repo_state["dirty_paths_truncated"],
        "dirty_status_rows": status_rows,
        "dirty_paths_detail": dirty_paths_detail,
        "malformed_dirty_paths": malformed_dirty_paths,
        "selected_dirty_sources": selected_dirty_sources,
        "selected_dirty_source_count": len(selected_dirty_sources),
        "dirty_generator": dirty_generator,
        "dirty_referenced_not_embedded": dirty_referenced_not_embedded,
        "dirty_referenced_not_embedded_count": len(dirty_referenced_not_embedded),
        "dirty_provenance_sidecars": dirty_provenance_sidecars,
        "dirty_provenance_sidecar_count": len(dirty_provenance_sidecars),
        "dirty_selected_source_sidecar_count": dirty_selected_source_sidecar_count,
        "dirty_referenced_not_embedded_sidecar_count": dirty_referenced_not_embedded_sidecar_count,
        "dirty_runtime_state_not_embedded": dirty_runtime_state_not_embedded,
        "dirty_runtime_state_not_embedded_count": len(dirty_runtime_state_not_embedded),
        "dirty_scope_summary": dirty_scope_summary,
    }


def _extract_freshness(path: str, text: str) -> dict[str, Any]:
    values: list[str] = []
    for pattern in (
        r"generated_at[\"']?\s*[:=]\s*[\"']([^\"']+)[\"']",
        r"Authored:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})",
        r"Generated:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})",
        r"([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.+-]+Z?)",
    ):
        for match in re.finditer(pattern, text):
            if match.group(1) not in values:
                values.append(match.group(1))
            if len(values) >= 10:
                break
    return {
        "source_uri": _repo_uri(path),
        "observed_timestamps_or_dates": values,
        "freshness_note": "extracted heuristically from source text; Type A should verify generator ownership for public use",
    }


def _privacy_report(chunks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    hits: dict[str, list[dict[str, Any]]] = {name: [] for name in PRIVATE_MARKER_PATTERNS}
    for chunk in chunks.values():
        text = chunk["content"]
        for name, pattern in PRIVATE_MARKER_PATTERNS.items():
            for match in pattern.finditer(text):
                if len(hits[name]) >= 100:
                    continue
                line_start = (chunk.get("source_span") or {}).get("line_start") or 1
                local_line = text.count("\n", 0, match.start()) + line_start
                hits[name].append(
                    {
                        "chunk_id": chunk["chunk_id"],
                        "source_uri": chunk["source_uri"],
                        "line": local_line,
                        "redacted_match_preview": "<matched_private_or_sensitive_pattern>",
                    }
                )
    return {
        "report_kind": "privacy_scan_report",
        "contains_source_content": True,
        "redaction": {
            "applied": False,
            "metadata_redacted": False,
            "source_content_redacted": False,
            "absolute_paths_rewritten": False,
            "operator_identity_rewritten": False,
        },
        "scan_scope": ["source_chunks"],
        "shareability_warning": "This is a private research packet. Source content may contain private-path or sensitive-boundary examples; do not treat as public-safe projection.",
        "pattern_counts": {name: len(values) for name, values in hits.items()},
        "hits_by_pattern": {name: values for name, values in hits.items() if values},
    }


def _serialized_privacy_scan(bundle: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(bundle, ensure_ascii=False, sort_keys=True)
    return {
        "scanned_final_serialized_json": True,
        "pattern_counts": {name: len(pattern.findall(text)) for name, pattern in PRIVATE_MARKER_PATTERNS.items()},
        "scan_note": "Counts scan the final JSON text. Matches are not repeated here to avoid increasing leakage.",
    }


def _redacted_generator_argv(output: Path, receipt_root: Path) -> list[str]:
    output_values = {str(output), str(output.expanduser()), str(output.resolve())}
    receipt_root_values = {str(receipt_root), str(receipt_root.expanduser()), str(receipt_root.resolve())}
    redacted: list[str] = []
    previous = None
    for arg in sys.argv:
        if arg in output_values or previous == "--output":
            redacted.append("<output_path>")
        elif arg in receipt_root_values or previous == "--receipt-root":
            redacted.append("<local_receipt_root>")
        else:
            redacted.append(arg)
        previous = arg
    return redacted


def _select_evidence_chunks(claim: dict[str, Any], chunks: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    scored: list[tuple[int, dict[str, Any]]] = []
    preferred = set(claim.get("preferred_paths", []))
    terms = set(claim.get("terms", []))
    for chunk in chunks.values():
        score = 0
        rel_path = chunk["source_uri"].replace("repo://", "")
        if rel_path in preferred:
            score += 100
        score += 15 * len(terms.intersection(set(chunk.get("terms", []))))
        text = chunk["content"].lower()
        for word in re.findall(r"[a-zA-Z_]{6,}", claim["text"].lower()):
            if word in text:
                score += 1
        if score:
            scored.append((score, chunk))
    scored.sort(key=lambda item: (-item[0], item[1]["source_uri"], item[1]["chunk_id"]))
    return [
        {
            "chunk_id": chunk["chunk_id"],
            "doc_id": chunk["doc_id"],
            "source_uri": chunk["source_uri"],
            "title": chunk["title"],
            "source_span": chunk.get("source_span"),
            "support_score": score,
            "support_kind": _support_kind(claim, chunk),
            "why_supports": _why_supports(claim, chunk),
        }
        for score, chunk in scored[:8]
    ]


def _support_kind(claim: dict[str, Any], chunk: dict[str, Any]) -> str:
    rel_path = chunk["source_uri"].replace("repo://", "")
    if rel_path in set(claim.get("preferred_paths", [])):
        return "preferred_source_semantic"
    if set(claim.get("terms", [])).intersection(set(chunk.get("terms", []))):
        return "controlled_term_overlap"
    return "lexical_overlap"


def _why_supports(claim: dict[str, Any], chunk: dict[str, Any]) -> str:
    rel_path = chunk["source_uri"].replace("repo://", "")
    matched_terms = sorted(set(claim.get("terms", [])).intersection(set(chunk.get("terms", []))))
    reasons = []
    if rel_path in set(claim.get("preferred_paths", [])):
        reasons.append("preferred source for this canonical claim")
    if matched_terms:
        reasons.append("controlled-term overlap: " + ", ".join(matched_terms))
    if not reasons:
        reasons.append("lexical overlap with claim wording")
    return "; ".join(reasons)


def _freshness_for_evidence(
    evidence: list[dict[str, Any]],
    documents: dict[str, dict[str, Any]],
    volatile: bool,
) -> dict[str, Any]:
    observed_values: list[str] = []
    missing_paths: list[str] = []
    evidence_doc_ids = sorted({item.get("doc_id") for item in evidence if item.get("doc_id")})
    for doc_id in evidence_doc_ids:
        doc = documents.get(doc_id)
        if not doc:
            continue
        values = doc.get("freshness", {}).get("observed_timestamps_or_dates", [])
        if values:
            observed_values.extend(values)
        else:
            missing_paths.append(doc["relative_path"])
    return {
        "volatile": volatile,
        "evidence_doc_count": len(evidence_doc_ids),
        "observed_timestamps_or_dates": sorted(set(observed_values))[:20],
        "evidence_with_missing_observed_timestamp": sorted(set(missing_paths)),
        "requires_type_a_live_check": volatile or bool(missing_paths),
    }


def _claim_verification_contract(claim_id: str, claim: dict[str, Any]) -> dict[str, Any]:
    volatile = claim.get("claim_type") in {"status", "release_boundary"} or claim_id == "claim:public_toggle_red"
    return {
        "authority_class": claim.get("claim_strength"),
        "receipt_status": "not_receipt_backed",
        "volatile": volatile,
        "last_checked_at": None,
        "required_receipts": _receipt_requirements_for_owner(claim_id, CLAIM_RECEIPT_REQUIREMENTS.get(claim_id, [])),
        "counterevidence": [],
        "downgrade_condition": "Downgrade if Type A evidence, current generated state, or gate receipts contradict the selected local-document evidence.",
    }


def _build_claims(chunks: dict[str, dict[str, Any]], documents: dict[str, dict[str, Any]]) -> dict[str, Any]:
    claims: dict[str, Any] = {}
    for claim_id, claim in CANONICAL_CLAIMS.items():
        evidence = _select_evidence_chunks(claim, chunks)
        contract = _claim_verification_contract(claim_id, claim)
        claims[claim_id] = {
            **claim,
            "authority_class": claim.get("claim_strength"),
            "volatile": contract["volatile"],
            "evidence": evidence,
            "verification_contract": contract,
            "freshness": _freshness_for_evidence(evidence, documents, contract["volatile"]),
            "downgrade_condition": contract["downgrade_condition"],
            "type_a_verification": "Verify current live substrate state before publishing exact counts, gate state, WorkItem ids, or release wording.",
        }
    return claims


def _build_gates(
    chunks: dict[str, dict[str, Any]],
    claims: dict[str, Any],
    documents: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    def evidence_for(terms: list[str], preferred_paths: list[str]) -> list[dict[str, Any]]:
        return _select_evidence_chunks({"text": " ".join(terms), "terms": terms, "preferred_paths": preferred_paths}, chunks)

    gates = {
        "gate:public_toggle": {
            "title": "Public toggle",
            "status": "red_or_not_ready_in_selected_docs",
            "terms": ["release_safety", "public_successor_projection", "portability_gate"],
            "evidence": evidence_for(["release_safety", "public_successor_projection", "portability_gate"], ["docs/dissemination/public_trust_packet_v0.md", "docs/dissemination/holographic_readme_template.md", "docs/dissemination/release_ip_license_gate_v0.md"]),
            "blocks_claims": ["claim:public_object_is_controlled_projection"],
        },
        "gate:portability": {
            "title": "Portability gate",
            "status": "required_before_public_toggle",
            "terms": ["portability_gate", "public_successor_projection", "release_safety"],
            "evidence": evidence_for(["portability_gate", "public_successor_projection"], ["docs/dissemination/public_projection_boundary_v0.md", "docs/dissemination/public_trust_packet_v0.md"]),
            "blocks_claims": ["claim:public_toggle_red"],
        },
        "gate:browser_provider_boundary": {
            "title": "Browser/provider boundary",
            "status": "forbidden_executable_public_path",
            "terms": ["browser_provider_boundary", "release_safety"],
            "evidence": evidence_for(["browser_provider_boundary", "release_safety"], ["docs/dissemination/public_projection_boundary_v0.md", "docs/dissemination/platform_terms_red_flags.md"]),
            "blocks_claims": ["claim:browser_provider_not_public_path"],
        },
    }
    for gate_id, gate in gates.items():
        contract = GATE_VERIFICATION_CONTRACTS.get(gate_id, {})
        gate["verification_contract"] = {
            "receipt_status": "not_receipt_backed",
            "last_checked_at": None,
            **contract,
        }
        gate["verification_contract"]["required_receipts"] = _receipt_requirements_for_owner(
            gate_id,
            gate["verification_contract"].get("required_receipts", []),
        )
        gate["freshness"] = _freshness_for_evidence(gate.get("evidence", []), documents, volatile=True)
    return gates


def _owner_receipt_requirements(claims: dict[str, Any], gates: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    owners: dict[str, list[dict[str, Any]]] = {}
    for objects in (claims, gates):
        for owner_id, obj in objects.items():
            owners[owner_id] = list(obj.get("verification_contract", {}).get("required_receipts", []))
    return owners


def _receipt_required_fields_by_id(owner_to_receipts: dict[str, list[dict[str, Any]]]) -> dict[str, set[str]]:
    fields_by_id: dict[str, set[str]] = defaultdict(set)
    for requirements in owner_to_receipts.values():
        for requirement in requirements:
            fields_by_id[requirement["receipt_id"]].update(requirement.get("required_fields", []))
    return fields_by_id


def _load_json_object(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)
    if not isinstance(payload, dict):
        return None, "receipt payload is not a JSON object"
    return payload, None


def _receipt_produced_at(receipt_kind: str, payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    if receipt_kind == "portability_gate_report":
        return payload.get("gate_generated_at") or payload.get("generated_at")
    return payload.get("generated_at") or payload.get("gate_generated_at") or payload.get("produced_at")


def _receipt_source_revision(receipt_kind: str, payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    if receipt_kind == "portability_gate_report":
        return payload.get("source_revision") or payload.get("receipt_source_revision")
    return payload.get("source_revision") or payload.get("receipt_source_revision")


def _receipt_outcome(receipt_kind: str, payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    if receipt_kind == "portability_gate_report":
        statuses = [
            str(payload.get("overall_status") or "").lower(),
            str(payload.get("publication_status") or "").lower(),
        ]
        if any(status == "red" for status in statuses):
            return "red"
        if statuses and all(status == "green" for status in statuses):
            return "green"
        return "unknown"
    if receipt_kind == "projection_receipt":
        status = str(payload.get("projection_status") or "").lower()
        if status in {"green", "ready", "public_release_safe"}:
            return "green"
        if status == "red" or "not_green" in status or "red" in status:
            return "red"
        status = str(payload.get("public_toggle_status") or "").lower()
        if status in {"green", "ready", "public_release_safe"}:
            return "green"
        if status == "red" or "not_green" in status or "red" in status:
            return "red"
        return "unknown" if status else None
    return None


def _receipt_status(
    *,
    receipt_kind: str,
    payload: dict[str, Any] | None,
    parse_error: str | None,
    required_fields: set[str],
    repo_head: str | None,
) -> tuple[str, dict[str, Any]]:
    if payload is None:
        return "missing_required_receipt", {
            "file_exists": False,
            "parse_error": parse_error,
            "required_fields_present": False,
            "missing_required_fields": sorted(required_fields),
            "source_revision_matches_head": False if repo_head else None,
            "has_produced_at": False,
        }
    missing = sorted(field for field in required_fields if field not in payload)
    source_revision = _receipt_source_revision(receipt_kind, payload)
    produced_at = _receipt_produced_at(receipt_kind, payload)
    revision_matches = source_revision == repo_head if repo_head else None
    outcome = _receipt_outcome(receipt_kind, payload)
    freshness = {
        "file_exists": True,
        "parse_error": parse_error,
        "required_fields_present": not missing,
        "missing_required_fields": missing,
        "source_revision": source_revision,
        "repo_head": repo_head,
        "source_revision_matches_head": revision_matches,
        "produced_at": produced_at,
        "has_produced_at": bool(produced_at),
        "receipt_outcome": outcome,
    }
    if missing or not produced_at or parse_error:
        status = "present_but_unverified"
    elif revision_matches is False:
        status = "present_stale"
    elif outcome == "green":
        status = "present_current_green"
    elif outcome == "red":
        status = "present_current_red"
    else:
        status = "present_current_unverified"
    return status, freshness


def _receipt_status_axes(status: str, freshness: dict[str, Any]) -> dict[str, Any]:
    outcome = freshness.get("receipt_outcome")
    if status == "missing_required_receipt":
        return {
            "presence_status": "missing",
            "freshness_status": "absent",
            "outcome_status": outcome,
            "verification_status": "missing_required_receipt",
        }
    if status == "source_evidence_only":
        return {
            "presence_status": "not_materialized",
            "freshness_status": "source_evidence_only",
            "outcome_status": outcome,
            "verification_status": "source_evidence_only",
        }
    if status == "private_runtime_reference_not_embedded":
        return {
            "presence_status": "referenced_not_embedded",
            "freshness_status": "private_runtime_reference",
            "outcome_status": outcome,
            "verification_status": "private_runtime_reference_not_embedded",
        }
    if status == "present_stale":
        return {
            "presence_status": "present",
            "freshness_status": "stale",
            "outcome_status": outcome,
            "verification_status": "present_stale",
        }
    if status == "present_but_unverified":
        return {
            "presence_status": "present",
            "freshness_status": "unverified",
            "outcome_status": outcome,
            "verification_status": "present_but_unverified",
        }
    if status.startswith("present_current_"):
        suffix = status.removeprefix("present_current_")
        return {
            "presence_status": "present",
            "freshness_status": "current",
            "outcome_status": outcome or suffix,
            "verification_status": "present_current",
        }
    return {
        "presence_status": "unknown",
        "freshness_status": "unknown",
        "outcome_status": outcome,
        "verification_status": status,
    }


def _build_receipts(
    repo_root: Path,
    receipt_root: Path,
    claims: dict[str, Any],
    gates: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, list[str]], dict[str, list[str]]]:
    owner_requirements = _owner_receipt_requirements(claims, gates)
    owner_to_receipts = {
        owner_id: sorted({requirement["receipt_id"] for requirement in requirements})
        for owner_id, requirements in owner_requirements.items()
    }
    receipt_to_owners: dict[str, list[str]] = defaultdict(list)
    for owner_id, receipt_ids in owner_to_receipts.items():
        for receipt_id in receipt_ids:
            receipt_to_owners[receipt_id].append(owner_id)
    required_fields_by_id = _receipt_required_fields_by_id(owner_requirements)
    requirements_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for requirements in owner_requirements.values():
        for requirement in requirements:
            requirements_by_id[requirement["receipt_id"]].append(requirement)

    repo_head = _git_output(["git", "rev-parse", "HEAD"], repo_root)
    receipts: dict[str, Any] = {}
    for receipt_id, requirements in sorted(requirements_by_id.items()):
        first = requirements[0]
        receipt_kind = first["receipt_kind"]
        local_path = _receipt_local_path(receipt_root, receipt_kind)
        payload = None
        parse_error = None
        sha256 = None
        if local_path and local_path.exists() and local_path.is_file():
            payload, parse_error = _load_json_object(local_path)
            sha256 = _sha256_file(local_path) if payload is not None else None
        status, freshness = _receipt_status(
            receipt_kind=receipt_kind,
            payload=payload,
            parse_error=parse_error,
            required_fields=required_fields_by_id.get(receipt_id, set()),
            repo_head=repo_head,
        )
        if first.get("requirement_status") in {"source_evidence_only", "private_runtime_reference_not_embedded"} and payload is None:
            status = first["requirement_status"]
            freshness.update(_receipt_status_axes(status, freshness))
        axes = _receipt_status_axes(status, freshness)
        required_by = sorted(receipt_to_owners.get(receipt_id, []))
        receipt = {
            "receipt_id": receipt_id,
            "receipt_kind": receipt_kind,
            "artifact_uri": first.get("expected_receipt_uri") or _artifact_uri_for_receipt_kind(receipt_kind),
            "local_diagnostic_path": str(local_path) if local_path else None,
            "sha256": sha256,
            "producer": first.get("producer"),
            "command_template": first.get("command_template"),
            "source_revision": _receipt_source_revision(receipt_kind, payload),
            "produced_at": _receipt_produced_at(receipt_kind, payload),
            "status": status,
            **axes,
            "freshness": freshness,
            "required_by": required_by,
            "candidate_owners": required_by,
            "actual_backed_owners": [],
            "required_fields": sorted(required_fields_by_id.get(receipt_id, set())),
            "payload_summary": _receipt_payload_summary(receipt_kind, payload),
        }
        receipts[receipt_id] = receipt
    return receipts, dict(sorted(receipt_to_owners.items())), dict(sorted(owner_to_receipts.items()))


def _receipt_payload_summary(receipt_kind: str, payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {}
    if receipt_kind == "projection_receipt":
        return {
            "manifest_hash": payload.get("manifest_hash"),
            "projection_status": payload.get("projection_status"),
            "public_toggle_status": payload.get("public_toggle_status"),
            "included_count": len(payload.get("included_paths", []) or []),
            "blocking_hit_count": payload.get("scan_summary", {}).get("blocking_hit_count"),
            "policy_exception_count": payload.get("scan_summary", {}).get("policy_exception_count"),
        }
    if receipt_kind == "portability_gate_report":
        return {
            "overall_status": payload.get("overall_status"),
            "publication_status": payload.get("publication_status"),
            "clean_worktree_used": payload.get("clean_worktree_used"),
            "hard_blocker_count": len(payload.get("hard_blockers", []) or []),
            "failed_check_count": len(payload.get("failed_checks", []) or []),
            "manifest_hash": payload.get("manifest_hash"),
        }
    return {"keys": sorted(payload)[:25]}


def _receipt_outcome_supports_owner(owner_id: str, receipt: dict[str, Any] | None) -> bool:
    if not receipt:
        return False
    outcome = receipt.get("freshness", {}).get("receipt_outcome")
    receipt_kind = receipt.get("receipt_kind")
    if (
        owner_id == "claim:public_object_is_controlled_projection"
        and receipt_kind == "projection_receipt"
        and receipt.get("presence_status") == "present"
        and receipt.get("freshness", {}).get("required_fields_present")
    ):
        return True
    if owner_id == "claim:public_toggle_red" and receipt_kind == "portability_gate_report" and outcome == "red":
        return True
    if owner_id in {"gate:public_toggle", "gate:portability"} and outcome == "green":
        return True
    return False


def _receipt_supports_owner(owner_id: str, receipt: dict[str, Any] | None) -> bool:
    if not receipt:
        return False
    status = receipt.get("status")
    receipt_kind = receipt.get("receipt_kind")
    if (
        owner_id == "claim:public_object_is_controlled_projection"
        and receipt_kind == "projection_receipt"
        and receipt.get("presence_status") == "present"
        and receipt.get("freshness_status") == "current"
        and receipt.get("freshness", {}).get("required_fields_present")
        and not receipt.get("freshness", {}).get("parse_error")
    ):
        return True
    if owner_id == "claim:public_toggle_red" and receipt_kind == "portability_gate_report" and status == "present_current_red":
        return True
    if owner_id in {"gate:public_toggle", "gate:portability"} and status == "present_current_green":
        return True
    return False


def _owner_fully_receipt_backed(owner_id: str, obj: dict[str, Any], receipts: dict[str, Any]) -> bool:
    required = obj.get("verification_contract", {}).get("required_receipts", [])
    return bool(required) and all(
        _receipt_supports_owner(owner_id, receipts.get(requirement.get("receipt_id"))) for requirement in required
    )


def _sync_actual_backed_owners(
    claims: dict[str, Any],
    gates: dict[str, Any],
    receipts: dict[str, Any],
) -> None:
    for receipt in receipts.values():
        receipt["actual_backed_owners"] = []
    for _owner_type, objects in (("claim", claims), ("gate", gates)):
        for owner_id, obj in objects.items():
            if not _owner_fully_receipt_backed(owner_id, obj, receipts):
                continue
            for requirement in obj.get("verification_contract", {}).get("required_receipts", []):
                receipt = receipts.get(requirement.get("receipt_id"))
                if receipt is not None:
                    receipt["actual_backed_owners"].append(owner_id)
    for receipt in receipts.values():
        receipt["actual_backed_owners"] = sorted(set(receipt["actual_backed_owners"]))


def _resolved_requirement_status(receipt: dict[str, Any] | None) -> str:
    if not receipt:
        return "missing_receipt_entity"
    status = receipt.get("status")
    if status == "missing_required_receipt":
        return "entity_missing"
    if status in {"source_evidence_only", "private_runtime_reference_not_embedded"}:
        return status
    return f"entity_{status}"


def _sync_receipt_requirement_statuses(
    claims: dict[str, Any],
    gates: dict[str, Any],
    receipts: dict[str, Any],
) -> None:
    for owner_type, objects in (("claim", claims), ("gate", gates)):
        for owner_id, obj in objects.items():
            contract = obj.get("verification_contract", {})
            for requirement in contract.get("required_receipts", []):
                receipt = receipts.get(requirement.get("receipt_id"))
                freshness = receipt.get("freshness", {}) if receipt else {}
                supports_if_current = _receipt_outcome_supports_owner(owner_id, receipt)
                current_supports_owner = _receipt_supports_owner(owner_id, receipt)
                requirement["requirement_status"] = _resolved_requirement_status(receipt)
                requirement["receipt_status"] = receipt.get("status") if receipt else "missing_receipt_entity"
                requirement["receipt_presence_status"] = receipt.get("presence_status") if receipt else "missing"
                requirement["receipt_freshness_status"] = receipt.get("freshness_status") if receipt else "absent"
                requirement["receipt_outcome_status"] = receipt.get("outcome_status") if receipt else None
                requirement["fresh_for_current_head"] = freshness.get("source_revision_matches_head")
                requirement["receipt_outcome"] = freshness.get("receipt_outcome")
                requirement["supports_owner_if_current"] = supports_if_current
                requirement["current_supports_owner"] = current_supports_owner
                requirement["staleness_blocks_support"] = bool(
                    supports_if_current and receipt and receipt.get("status") == "present_stale"
                )
                requirement["supports_owner"] = current_supports_owner
            required = contract.get("required_receipts", [])
            contract["receipt_status"] = (
                "receipt_backed"
                if required and all(requirement.get("supports_owner") for requirement in required)
                else "not_receipt_backed"
            )


def _annotate_claim_dirty_evidence(
    claims: dict[str, Any],
    chunks: dict[str, Any],
    working_tree: dict[str, Any],
) -> None:
    dirty_by_path = {
        row.get("path"): row
        for row in working_tree.get("dirty_paths_detail", [])
        if row.get("selected_for_embedding")
    }
    for claim in claims.values():
        dirty_sources: dict[str, dict[str, Any]] = {}
        for evidence in claim.get("evidence", []):
            chunk = chunks.get(evidence.get("chunk_id"))
            if not chunk:
                continue
            path = chunk.get("source_uri", "").replace("repo://", "")
            dirty = dirty_by_path.get(path)
            if not dirty:
                continue
            entry = dirty_sources.setdefault(
                path,
                {
                    "source_uri": chunk.get("source_uri"),
                    "relative_path": path,
                    "captured": bool(dirty.get("embedded_document")),
                    "commit_authoritative": False,
                    "dirty_sidecar_id": dirty.get("dirty_provenance_sidecar_id"),
                    "working_tree_sha256": dirty.get("working_tree_sha256"),
                    "evidence_chunk_ids": [],
                },
            )
            entry["evidence_chunk_ids"].append(evidence.get("chunk_id"))
        claim["dirty_evidence_sources"] = sorted(dirty_sources.values(), key=lambda item: item["relative_path"])
        claim["dirty_evidence_source_count"] = len(claim["dirty_evidence_sources"])


def _build_routes(documents: dict[str, dict[str, Any]], chunks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    def doc_ids(paths: list[str]) -> list[str]:
        return [doc_id for doc_id, doc in documents.items() if doc["relative_path"] in paths]

    def chunk_ids(paths: list[str], max_per_doc: int = 8) -> list[str]:
        result: list[str] = []
        for doc in documents.values():
            if doc["relative_path"] not in paths:
                continue
            result.extend(doc["chunk_ids"][:max_per_doc])
        return result

    return {
        "route.agent_entry_to_dissemination": {
            "purpose": "Enter the dissemination lane from a cold agent state without re-deriving the 70+ file directory, leaking private substrate, or treating entry as a generic navigation audit.",
            "documents": doc_ids([
                "codex/doctrine/agent_bootstrap.json",
                "codex/doctrine/routing_hologram.json",
                "codex/doctrine/documentation_theory_index.json",
                "codex/doctrine/paper_modules/agent_entry_surfaces.md",
                "codex/standards/std_agent_entry_surface.json",
                "codex/doctrine/concepts/con_036_entry_point.json",
                "codex/doctrine/concepts/con_037_entry_point_probe.json",
                "codex/doctrine/paper_modules/dissemination_strategy.md",
                "codex/doctrine/skills/dissemination/dissemination_cycle.md",
                "codex/doctrine/skills/dissemination/dissemination_understanding.md",
                "codex/doctrine/skills/dissemination/dissemination_research_prompting.md",
                "codex/doctrine/skills/dissemination/dissemination_research_assimilation.md",
                "docs/documentation_plane_map.md",
                "docs/agent_instruction_router.md",
                "docs/dissemination/README.md",
                "docs/dissemination/holographic_research_snapshot.md",
            ]),
            "chunks": chunk_ids([
                "codex/doctrine/agent_bootstrap.json",
                "codex/doctrine/routing_hologram.json",
                "codex/doctrine/documentation_theory_index.json",
                "codex/doctrine/paper_modules/agent_entry_surfaces.md",
                "codex/standards/std_agent_entry_surface.json",
                "codex/doctrine/concepts/con_036_entry_point.json",
                "codex/doctrine/paper_modules/dissemination_strategy.md",
                "codex/doctrine/skills/dissemination/dissemination_cycle.md",
                "codex/doctrine/skills/dissemination/dissemination_understanding.md",
                "docs/documentation_plane_map.md",
                "docs/agent_instruction_router.md",
                "docs/dissemination/README.md",
                "docs/dissemination/holographic_research_snapshot.md",
            ]),
            "terms": [
                "entry_point",
                "agent_entry_surface",
                "dissemination_router",
                "projection_not_authority",
                "public_successor_projection",
                "type_a_type_b_boundary",
            ],
        },
        "route.system_identity_first_contact": {
            "purpose": "Understand what ai_workflow is before touching dissemination strategy.",
            "documents": doc_ids([
                "codex/doctrine/paper_modules/system_self_comprehension_root.md",
                "codex/doctrine/paper_modules/system_self_comprehension_spine.md",
                "codex/doctrine/paper_modules/system_constitution_seed.md",
                "docs/system_atlas/system_atlas_v0.md",
                "docs/system_atlas/generated_system_facts_at_a_glance.md",
                "dist/type_b/TYPE_B_SYSTEM_GROUNDING_PACKET.md",
                "dist/type_b/AI_WORKFLOW_SYSTEM_PACKET.md",
            ]),
            "chunks": chunk_ids([
                "codex/doctrine/paper_modules/system_self_comprehension_root.md",
                "codex/doctrine/paper_modules/system_self_comprehension_spine.md",
                "dist/type_b/TYPE_B_SYSTEM_GROUNDING_PACKET.md",
                "dist/type_b/AI_WORKFLOW_SYSTEM_PACKET.md",
            ]),
            "terms": ["projection_not_authority", "type_a_type_b_boundary", "system_atlas", "raw_voice_authority", "metabolism_compression"],
        },
        "route.public_successor_deliverable": {
            "purpose": "Understand what the public artifact is and is not.",
            "documents": doc_ids([
                "docs/dissemination/README.md",
                "docs/dissemination/actual_deliverable_v0.md",
                "docs/dissemination/public_projection_boundary_v0.md",
                "docs/dissemination/public_reconstruction_architecture_contract.md",
                "docs/dissemination/public_leaf_readiness_audit.md",
                "docs/dissemination/holographic_readme_template.md",
                "docs/dissemination/holographic_research_snapshot.md",
            ]),
            "chunks": chunk_ids([
                "docs/dissemination/actual_deliverable_v0.md",
                "docs/dissemination/public_projection_boundary_v0.md",
                "docs/dissemination/public_leaf_readiness_audit.md",
                "docs/dissemination/holographic_readme_template.md",
                "docs/dissemination/holographic_research_snapshot.md",
            ]),
            "terms": ["public_successor_projection", "release_safety", "projection_not_authority", "portability_gate"],
        },
        "route.paper_as_ir_and_traceability": {
            "purpose": "Understand paper-as-IR, traceability, standards, and evidence contracts.",
            "documents": doc_ids([
                "docs/dissemination/system_paper_v0.md",
                "docs/dissemination/single_system_paper_contract.md",
                "docs/dissemination/system_paper_traceability_map.md",
                "docs/dissemination/open_source_successor_ir_contract.md",
            ]),
            "chunks": chunk_ids([
                "docs/dissemination/system_paper_v0.md",
                "docs/dissemination/system_paper_traceability_map.md",
                "docs/dissemination/open_source_successor_ir_contract.md",
            ]),
            "terms": ["paper_as_ir", "standards_as_protocol", "evidence_receipts"],
        },
        "route.demo_and_frontend_proof": {
            "purpose": "Understand demos, cockpit, videos, and proof surfaces.",
            "documents": doc_ids([
                "docs/dissemination/demo_variant_catalog.md",
                "docs/dissemination/demo_shot_list_v0.md",
                "docs/dissemination/private_demo_protocol.md",
                "docs/dissemination/platform_terms_red_flags.md",
                "docs/dissemination/public_trust_packet_v0.md",
            ]),
            "chunks": chunk_ids([
                "docs/dissemination/demo_variant_catalog.md",
                "docs/dissemination/demo_shot_list_v0.md",
                "docs/dissemination/private_demo_protocol.md",
                "docs/dissemination/platform_terms_red_flags.md",
            ]),
            "terms": ["demo_proof", "frontend_cockpit", "browser_provider_boundary", "evidence_receipts"],
        },
        "route.safety_boundary_and_release_gate": {
            "purpose": "Understand public/private boundary, release classes, redaction, IP, and provider risk.",
            "documents": doc_ids([
                "docs/dissemination/public_projection_boundary_v0.md",
                "docs/dissemination/safety_boundary.md",
                "docs/dissemination/release_ip_license_gate_v0.md",
                "docs/dissemination/platform_terms_red_flags.md",
                "docs/dissemination/disclosure_artifact_registry.md",
                "docs/dissemination/public_leaf_readiness_audit.md",
                "docs/dissemination/provenance_note.md",
            ]),
            "chunks": chunk_ids([
                "docs/dissemination/public_projection_boundary_v0.md",
                "docs/dissemination/safety_boundary.md",
                "docs/dissemination/release_ip_license_gate_v0.md",
                "docs/dissemination/platform_terms_red_flags.md",
                "docs/dissemination/public_leaf_readiness_audit.md",
            ]),
            "terms": ["release_safety", "browser_provider_boundary", "public_successor_projection", "evidence_receipts", "portability_gate"],
        },
        "route.category_and_external_legibility": {
            "purpose": "Understand current category language and where it may be wrong or underspecified.",
            "documents": doc_ids([
                "docs/dissemination/recognition_grade_system_description.md",
                "docs/dissemination/external_legibility_packet.md",
                "docs/dissemination/system_capability_register.md",
                "docs/dissemination/capability_to_avenue_matrix.md",
            ]),
            "chunks": chunk_ids([
                "docs/dissemination/recognition_grade_system_description.md",
                "docs/dissemination/external_legibility_packet.md",
                "docs/dissemination/system_capability_register.md",
            ]),
            "terms": ["recognition_category", "workitem_spine", "frontend_cockpit", "standards_as_protocol", "annex_prior_art"],
        },
    }


def _route_coverage(
    routes: dict[str, Any],
    documents: dict[str, Any],
    chunks: dict[str, Any],
    tables: dict[str, Any],
) -> dict[str, Any]:
    report = {}
    routed_chunks_all = set()
    for route_id, route in routes.items():
        selected = set(route["chunks"])
        routed_chunks_all |= selected
        zero_selected_docs = []
        document_entry_modes = {}
        for doc_id in route["documents"]:
            doc_chunk_ids = set(documents[doc_id]["chunk_ids"])
            if selected.intersection(doc_chunk_ids):
                document_entry_modes[documents[doc_id]["relative_path"]] = "chunk_entry_selected"
            elif any(table.get("doc_id") == doc_id for table in tables.values()):
                document_entry_modes[documents[doc_id]["relative_path"]] = "table_row_entry_selected"
                zero_selected_docs.append(documents[doc_id]["relative_path"])
            else:
                document_entry_modes[documents[doc_id]["relative_path"]] = "document_pointer_only"
                zero_selected_docs.append(documents[doc_id]["relative_path"])
        route_chunk_count = sum(len(documents[doc_id]["chunk_ids"]) for doc_id in route["documents"])
        report[route_id] = {
            "document_count": len(route["documents"]),
            "selected_chunk_count": len(selected),
            "route_total_chunk_count": route_chunk_count,
            "selected_chunk_percent": round((len(selected) / route_chunk_count * 100), 2) if route_chunk_count else 0,
            "zero_selected_chunk_documents": zero_selected_docs,
            "document_entry_modes": document_entry_modes,
        }
    return {
        "routes": report,
        "global_routed_chunk_count": len(routed_chunks_all),
        "global_chunk_count": len(chunks),
        "global_routed_chunk_percent": round((len(routed_chunks_all) / len(chunks) * 100), 2) if chunks else 0,
    }


def _normalized_cells(row: dict[str, Any]) -> dict[str, str]:
    return {_slug(key): value for key, value in row.get("cells", {}).items()}


def _cell(cells: dict[str, str], *names: str) -> str | None:
    for name in names:
        value = cells.get(_slug(name))
        if value:
            return value
    return None


def _clean_inline_value(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if cleaned.startswith("`") and cleaned.endswith("`") and cleaned.count("`") == 2:
        cleaned = cleaned[1:-1].strip()
    return cleaned or None


def _cell_clean(cells: dict[str, str], *names: str) -> str | None:
    return _clean_inline_value(_cell(cells, *names))


def _bool_from_cell(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"yes", "y", "true", "ready", "green"}:
        return True
    if normalized in {"no", "n", "false", "not ready", "red"}:
        return False
    return None


def _blocking_from_text(value: str | None) -> bool | None:
    if not value:
        return None
    normalized = value.lower()
    if any(marker in normalized for marker in ("block", "red", "fail", "cannot", "not found", "absent")):
        return True
    if "allow" in normalized or "pass" in normalized or "green" in normalized:
        return False
    return None


def _capability_ids_from_text(text: str | None) -> list[str]:
    if not text:
        return []
    values = []
    for match in re.findall(r"cap_[A-Za-z0-9_]+", text):
        node_id = "capability:" + _slug(match)
        if node_id not in values:
            values.append(node_id)
    return values


def _split_cell_list(text: str | None) -> list[str]:
    if not text:
        return []
    cleaned = text.replace("`", "")
    parts = re.split(r"\s*(?:,|;|\n|/|\band\b)\s*", cleaned)
    return [part.strip() for part in parts if part.strip()]


def _typed_fields_for_object(object_kind: str, cells: dict[str, str]) -> dict[str, Any]:
    if object_kind == "capability":
        return {
            "capability_id": _cell_clean(cells, "capability_id"),
            "name": _cell_clean(cells, "name"),
            "maturity": _cell_clean(cells, "maturity"),
            "risk_class": _cell_clean(cells, "risk class", "risk_class"),
            "disclosure_class": _cell_clean(cells, "disclosure class", "disclosure_class"),
            "demonstration_path": _cell_clean(cells, "demonstration path", "demo path"),
            "next_verification_step": _cell_clean(cells, "next verification step", "next_verification_step"),
        }
    if object_kind == "capability_refinement":
        raw = _cell(cells, "capability_id")
        return {
            "capability_ids": _capability_ids_from_text(raw),
            "source_capability_cell": raw,
            "public_safe_refinement": _cell(cells, "public safe refinement", "public_safe_refinement"),
            "proof_fixture": _cell(cells, "proof fixture", "proof_fixture"),
        }
    if object_kind == "public_leaf":
        send_ready = _bool_from_cell(_cell(cells, "send_ready", "send ready"))
        return {
            "leaf": _cell_clean(cells, "leaf"),
            "capability_ids": _capability_ids_from_text(_cell(cells, "capability_ids", "capability id", "capability_id")),
            "release_class": _cell_clean(cells, "release_class", "release class"),
            "status": _cell_clean(cells, "status"),
            "send_ready": send_ready,
            "readiness_status": "ready" if send_ready is True else "not_ready" if send_ready is False else None,
            "requires_review": _split_cell_list(_cell(cells, "requires review", "requires_review")),
        }
    if object_kind == "disclosure_artifact":
        return {
            "artifact_id": _cell_clean(cells, "artifact_id", "artifact", "safe_artifact"),
            "capability_ids": _capability_ids_from_text(_cell(cells, "capability_ids", "capability id", "capability_id")),
            "release_class": _cell_clean(cells, "release_class", "release class"),
            "status": _cell_clean(cells, "status", "gate_status"),
            "safe_artifact_route": _cell_clean(cells, "safe_artifact_route", "safe artifact route", "safe_artifact"),
            "forbidden_artifacts": _split_cell_list(_cell(cells, "forbidden_artifacts", "forbidden artifacts")),
            "redaction_status": _cell_clean(cells, "redaction_status", "redaction status"),
        }
    if object_kind == "release_gate_row":
        release_effect = _cell_clean(cells, "release effect", "release_effect")
        release_class = _cell_clean(cells, "release_class", "release class")
        status = _cell_clean(cells, "status", "gate_status")
        return {
            "artifact_or_check": _cell_clean(cells, "artifact", "check", "id"),
            "release_class": release_class,
            "status": status,
            "check_result": _cell_clean(cells, "result", "check result", "check_result"),
            "release_effect": release_effect,
            "blocking": _blocking_from_text(release_effect),
            "field_applicability": {
                "release_class": bool(release_class),
                "status": bool(status),
            },
            "requires_review": _split_cell_list(_cell(cells, "requires review", "requires_review")),
        }
    if object_kind == "agent_entry_surface":
        return {
            "surface_type": _cell_clean(cells, "type"),
            "surface_kind": _cell_clean(cells, "kind"),
            "purpose": _cell_clean(cells, "one-line purpose", "purpose"),
            "symbol_or_file": _cell_clean(cells, "symbol / file", "symbol or file", "path"),
        }
    if object_kind == "agent_entry_plane":
        return {
            "plane": _cell_clean(cells, "plane"),
            "owns": _cell_clean(cells, "owns"),
            "does_not_own": _cell_clean(cells, "does not own", "does_not_own"),
        }
    if object_kind == "agent_entry_runtime_component":
        return {
            "concern": _cell_clean(cells, "concern"),
            "path": _cell_clean(cells, "path"),
            "role": _cell_clean(cells, "role"),
        }
    if object_kind == "dissemination_strategy_object":
        return {
            "name": _cell_clean(cells, "name", "surface"),
            "kind": _cell_clean(cells, "kind"),
            "purpose": _cell_clean(cells, "one-line purpose", "purpose", "role"),
            "symbol_or_path": _cell_clean(cells, "symbol or path", "planned path", "path"),
            "status": _cell_clean(cells, "status"),
            "promotion_trigger": _cell_clean(cells, "promotion trigger", "promotion_trigger"),
        }
    if object_kind == "dissemination_skill_transition":
        return {
            "situation": _cell_clean(cells, "situation", "returned research says"),
            "next_skill": _cell_clean(cells, "next skill", "update"),
        }
    if object_kind == "documentation_route_rule":
        return {
            "question_or_artifact": _cell_clean(
                cells,
                "if the question is",
                "if the question is...",
                "if the task / question is",
                "artifact kind",
                "if the thing you are touching is",
            ),
            "primary_authority": _cell_clean(cells, "primary authority", "open first"),
            "then_route_to": _cell_clean(cells, "then route to"),
        }
    return {}


def _add_semantic_object(
    registries: dict[str, dict[str, Any]],
    registry_name: str,
    object_id: str,
    row: dict[str, Any],
    object_kind: str,
    typed_fields: dict[str, Any] | None = None,
) -> None:
    bucket = registries.setdefault(registry_name, {})
    entry = bucket.setdefault(
        object_id,
        {
            "object_id": object_id,
            "object_kind": object_kind,
            "source_rows": [],
            "source_uri": row["source_uri"],
            "source_table_ids": [],
            "sample_cells": row.get("cells", {}),
            "typed_fields": typed_fields or {},
        },
    )
    entry["source_rows"].append(row["row_id"])
    if row.get("table_id") not in entry["source_table_ids"]:
        entry["source_table_ids"].append(row.get("table_id"))
    if typed_fields:
        entry["typed_fields"].update({key: value for key, value in typed_fields.items() if value not in (None, "", [])})


def _semantic_registries(rows: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    registries: dict[str, dict[str, Any]] = {}
    for row in rows.values():
        cells = _normalized_cells(row)
        source = row["source_uri"].replace("repo://", "")
        if source.endswith("agent_entry_surfaces.md"):
            if cells.get("type") and (cells.get("symbol_file") or cells.get("symbol_or_file")):
                _add_semantic_object(
                    registries,
                    "agent_entry_surfaces",
                    "agent_entry_surface:" + _slug(cells["type"]),
                    row,
                    "agent_entry_surface",
                    _typed_fields_for_object("agent_entry_surface", cells),
                )
            if cells.get("plane") and cells.get("owns"):
                _add_semantic_object(
                    registries,
                    "agent_entry_planes",
                    "agent_entry_plane:" + _slug(cells["plane"]),
                    row,
                    "agent_entry_plane",
                    _typed_fields_for_object("agent_entry_plane", cells),
                )
            if cells.get("concern") and cells.get("path"):
                _add_semantic_object(
                    registries,
                    "agent_entry_runtime_components",
                    "agent_entry_runtime_component:" + _slug(cells["concern"]),
                    row,
                    "agent_entry_runtime_component",
                    _typed_fields_for_object("agent_entry_runtime_component", cells),
                )
        if source.endswith("dissemination_strategy.md"):
            candidate = cells.get("name") or cells.get("surface")
            if candidate and (cells.get("kind") or cells.get("planned_path") or cells.get("path")):
                _add_semantic_object(
                    registries,
                    "dissemination_strategy_objects",
                    "dissemination_strategy_object:" + _slug(candidate),
                    row,
                    "dissemination_strategy_object",
                    _typed_fields_for_object("dissemination_strategy_object", cells),
                )
        if source.endswith("dissemination_cycle.md") and cells.get("situation") and cells.get("next_skill"):
            _add_semantic_object(
                registries,
                "dissemination_skill_transitions",
                "dissemination_skill_transition:" + _slug(cells["situation"]),
                row,
                "dissemination_skill_transition",
                _typed_fields_for_object("dissemination_skill_transition", cells),
            )
        if source.endswith("dissemination_research_assimilation.md") and cells.get("returned_research_says") and cells.get("update"):
            _add_semantic_object(
                registries,
                "dissemination_skill_transitions",
                "dissemination_skill_transition:" + _slug(cells["returned_research_says"]),
                row,
                "dissemination_skill_transition",
                _typed_fields_for_object("dissemination_skill_transition", cells),
            )
        if source.endswith("documentation_plane_map.md") or source.endswith("agent_instruction_router.md"):
            candidate = (
                cells.get("if_the_question_is")
                or cells.get("if_the_task_question_is")
                or cells.get("artifact_kind")
                or cells.get("if_the_thing_you_are_touching_is")
            )
            if candidate:
                _add_semantic_object(
                    registries,
                    "documentation_route_rules",
                    "documentation_route_rule:" + _slug(candidate),
                    row,
                    "documentation_route_rule",
                    _typed_fields_for_object("documentation_route_rule", cells),
                )
        if cells.get("capability_id"):
            capability_ids = _capability_ids_from_text(cells["capability_id"])
            if len(capability_ids) > 1 or "/" in cells["capability_id"]:
                _add_semantic_object(
                    registries,
                    "capability_refinements",
                    "capability_refinement:" + _slug(cells["capability_id"]),
                    row,
                    "capability_refinement",
                    _typed_fields_for_object("capability_refinement", cells),
                )
                continue
            _add_semantic_object(
                registries,
                "capabilities",
                "capability:" + _slug(cells["capability_id"]),
                row,
                "capability",
                _typed_fields_for_object("capability", cells),
            )
        if source.endswith("demo_variant_catalog.md"):
            candidate = cells.get("variant") or cells.get("demo_variant") or cells.get("demo_variant_id")
            if candidate:
                _add_semantic_object(
                    registries,
                    "demo_variants",
                    "demo_variant:" + _slug(candidate),
                    row,
                    "demo_variant",
                    {"variant": candidate},
                )
        if source.endswith("public_leaf_readiness_audit.md") and cells.get("leaf"):
            _add_semantic_object(
                registries,
                "public_leaves",
                "public_leaf:" + _slug(cells["leaf"]),
                row,
                "public_leaf",
                _typed_fields_for_object("public_leaf", cells),
            )
        if source.endswith("disclosure_artifact_registry.md"):
            candidate = cells.get("artifact") or cells.get("artifact_id") or cells.get("safe_artifact")
            if candidate:
                _add_semantic_object(
                    registries,
                    "disclosure_artifacts",
                    "disclosure_artifact:" + _slug(candidate),
                    row,
                    "disclosure_artifact",
                    _typed_fields_for_object("disclosure_artifact", cells),
                )
        if source.endswith("release_ip_license_gate_v0.md"):
            candidate = cells.get("artifact") or cells.get("check") or cells.get("id")
            if candidate:
                _add_semantic_object(
                    registries,
                    "release_gate_rows",
                    "release_gate_row:" + _slug(candidate),
                    row,
                    "release_gate_row",
                    _typed_fields_for_object("release_gate_row", cells),
                )
    return registries


def _route_entity_index(
    routes: dict[str, Any],
    documents: dict[str, Any],
    chunks: dict[str, Any],
    tables: dict[str, Any],
    claims: dict[str, Any],
    gates: dict[str, Any],
    semantic_registries: dict[str, dict[str, Any]],
    owner_to_receipts: dict[str, list[str]],
) -> dict[str, Any]:
    index: dict[str, Any] = {}
    semantic_objects_by_row: dict[str, list[str]] = defaultdict(list)
    for objects in semantic_registries.values():
        for object_id, obj in objects.items():
            for row_id in obj.get("source_rows", []):
                semantic_objects_by_row[row_id].append(object_id)
    for route_id, route in routes.items():
        route_docs = set(route.get("documents", []))
        route_chunks = set(route.get("chunks", []))
        route_terms = set(route.get("terms", []))
        route_tables = [
            table_id
            for table_id, table in tables.items()
            if table.get("chunk_id") in route_chunks or table.get("doc_id") in route_docs
        ]
        route_rows = [row_id for table_id in route_tables for row_id in tables[table_id].get("row_ids", [])]
        route_claims = []
        for claim_id, claim in claims.items():
            evidence_chunks = {evidence["chunk_id"] for evidence in claim.get("evidence", [])}
            claim_terms = set(claim.get("terms", []))
            if evidence_chunks.intersection(route_chunks) or claim_terms.intersection(route_terms):
                route_claims.append(claim_id)
        route_gates = []
        for gate_id, gate in gates.items():
            evidence_chunks = {evidence["chunk_id"] for evidence in gate.get("evidence", [])}
            blocked_claims = set(gate.get("blocks_claims", []))
            if evidence_chunks.intersection(route_chunks) or blocked_claims.intersection(route_claims):
                route_gates.append(gate_id)
        route_receipts = sorted(
            {
                receipt_id
                for owner_id in [*route_claims, *route_gates]
                for receipt_id in owner_to_receipts.get(owner_id, [])
            }
        )
        route_semantic_objects = sorted(
            {
                object_id
                for row_id in route_rows
                for object_id in semantic_objects_by_row.get(row_id, [])
            }
        )
        index[route_id] = {
            "documents": route.get("documents", []),
            "chunks": route.get("chunks", []),
            "tables": route_tables,
            "rows": route_rows,
            "claims": route_claims,
            "gates": route_gates,
            "receipts": route_receipts,
            "semantic_objects": route_semantic_objects,
            "terms": route.get("terms", []),
            "term_ids": route.get("term_ids", _canonical_term_ids(route.get("terms", []))),
        }
    return index


def _attach_route_targets(routes: dict[str, Any], route_to_entities: dict[str, Any]) -> dict[str, Any]:
    for route_id, route in routes.items():
        route["targets"] = route_to_entities.get(route_id, {})
    return routes


def _term_index(chunks: dict[str, dict[str, Any]], max_occurrences: int) -> tuple[dict[str, Any], dict[str, list[str]]]:
    index: dict[str, Any] = {}
    warnings: dict[str, list[str]] = {}
    for family, terms in TERM_TAXONOMY.items():
        for term, aliases in terms.items():
            occurrences = []
            docs = set()
            occurrence_breakdown: dict[str, int] = defaultdict(int)
            for chunk in chunks.values():
                if term not in chunk.get("terms", []):
                    continue
                docs.add(chunk["doc_id"])
                matches = chunk.get("term_matches", {}).get(term, [])
                match_roles = [match.get("match_role") for match in matches if match.get("match_role")]
                role_breakdown = {role: match_roles.count(role) for role in sorted(set(match_roles))}
                for role, count in role_breakdown.items():
                    occurrence_breakdown[role] += count
                alias_metadata = {
                    match["alias"]: {
                        "text": match["alias"],
                        "specificity": match.get("specificity"),
                        "match_role": match.get("match_role"),
                    }
                    for match in matches
                }
                occurrences.append(
                    {
                        "chunk_id": chunk["chunk_id"],
                        "doc_id": chunk["doc_id"],
                        "source_uri": chunk["source_uri"],
                        "title": chunk["title"],
                        "source_span": chunk.get("source_span"),
                        "matched_aliases": sorted(alias_metadata),
                        "matched_alias_metadata": [alias_metadata[key] for key in sorted(alias_metadata)],
                        "match_role_breakdown": role_breakdown,
                    }
                )
            truncated = len(occurrences) > max_occurrences
            index[term] = {
                "term_id": term,
                "canonical_node_id": f"term:{term}",
                "family": family,
                "aliases": aliases,
                "alias_metadata": [_alias_metadata(term, alias) for alias in aliases],
                "occurrence_count": len(occurrences),
                "occurrence_count_basis": "chunk_occurrence",
                "emitted_occurrence_count": min(len(occurrences), max_occurrences),
                "document_count": len(docs),
                "occurrence_breakdown": dict(sorted(occurrence_breakdown.items())),
                "occurrence_breakdown_basis": "alias_hit",
                "truncated": truncated,
                "truncation_policy": f"first_{max_occurrences}_by_source_order" if truncated else None,
                "occurrences": occurrences[:max_occurrences],
            }
            if truncated:
                warnings.setdefault("truncated_term_indexes", []).append(term)
    return index, warnings


def _edge_type_schema() -> dict[str, str]:
    return {
        "contains": "document contains chunk",
        "next_section": "linear section navigation",
        "mentions_term": "chunk matched a controlled concept term",
        "contains_table": "chunk contains parsed markdown table",
        "contains_row": "table contains typed row entity",
        "supported_by": "claim supported by evidence chunk",
        "claim_uses_term": "claim references a controlled concept term",
        "evidenced_by": "gate/status evidenced by chunk",
        "blocks_or_conditions": "gate blocks or conditions claim",
        "gate_uses_term": "gate references a controlled concept term",
        "routes_to_document": "route points to document",
        "routes_to_chunk": "route points to selected chunk",
        "routes_to_table": "route points to table entity",
        "routes_to_row": "route points to row entity",
        "routes_to_claim": "route points to claim entity",
        "routes_to_gate": "route points to gate entity",
        "routes_to_semantic_object": "route points to promoted semantic object",
        "routes_to_term": "route points to concept term",
        "routes_to_receipt": "route points to receipt entity",
        "promoted_from_row": "semantic object is promoted from parsed row entity",
        "requires_receipt": "claim or gate declares a required receipt entity",
        "backed_by_receipt": "claim or gate is backed by a current receipt whose outcome supports that owner",
        "requires_capability": "semantic object requires a promoted capability",
        "demonstrates_capability": "semantic object demonstrates a promoted capability",
        "governs_identity_family": "root identity document governs a derived identity-family document",
        "renders_projection": "source authority renders or conditions a generated projection",
        "governs_boundary": "document governs a public/private or claim boundary",
        "gates_recognition": "document gates recognition/category language",
        "sets_claim_boundary_for": "boundary document sets claim posture for another document",
        "sets_demo_boundary_for": "boundary document sets demo posture for another document",
    }


def _build_graph(
    documents: dict[str, Any],
    chunks: dict[str, Any],
    tables: dict[str, Any],
    rows: dict[str, Any],
    claims: dict[str, Any],
    gates: dict[str, Any],
    receipts: dict[str, Any],
    routes: dict[str, Any],
    semantic_registries: dict[str, dict[str, Any]],
    owner_to_receipts: dict[str, list[str]],
) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []
    for doc_id, doc in documents.items():
        nodes[doc_id] = {"id": doc_id, "type": "document", "label": doc["relative_path"], "category": doc["category"]}
        for chunk_id in doc["chunk_ids"]:
            edges.append({"source": doc_id, "target": chunk_id, "type": "contains"})
    for chunk_id, chunk in chunks.items():
        nodes[chunk_id] = {
            "id": chunk_id,
            "type": "chunk",
            "label": chunk["title"],
            "doc_id": chunk["doc_id"],
            "terms": chunk["terms"],
            "term_ids": chunk.get("term_ids", _canonical_term_ids(chunk.get("terms", []))),
        }
        if chunk.get("prev_chunk_id"):
            edges.append({"source": chunk["prev_chunk_id"], "target": chunk_id, "type": "next_section"})
        for term in chunk.get("terms", []):
            term_id = f"term:{term}"
            nodes.setdefault(term_id, {"id": term_id, "type": "term", "label": term})
            edges.append({"source": chunk_id, "target": term_id, "type": "mentions_term"})
    for table_id, table in tables.items():
        nodes[table_id] = {"id": table_id, "type": "table", "label": table_id, "columns": table["columns"]}
        edges.append({"source": table["chunk_id"], "target": table_id, "type": "contains_table"})
        for row_id in table["row_ids"]:
            edges.append({"source": table_id, "target": row_id, "type": "contains_row"})
    for row_id, row in rows.items():
        nodes[row_id] = {"id": row_id, "type": "row", "label": next(iter(row["cells"].values()), row_id)}
    for claim_id, claim in claims.items():
        nodes[claim_id] = {"id": claim_id, "type": "claim", "label": claim["text"], "claim_type": claim["claim_type"]}
        for evidence in claim["evidence"]:
            edges.append({"source": claim_id, "target": evidence["chunk_id"], "type": "supported_by"})
        claim_backed = _owner_fully_receipt_backed(claim_id, claim, receipts)
        for receipt_id in owner_to_receipts.get(claim_id, []):
            edges.append({"source": claim_id, "target": receipt_id, "type": "requires_receipt"})
            if claim_backed:
                edges.append({"source": claim_id, "target": receipt_id, "type": "backed_by_receipt"})
        for term in claim.get("terms", []):
            term_id = f"term:{term}"
            nodes.setdefault(term_id, {"id": term_id, "type": "term", "label": term})
            edges.append({"source": claim_id, "target": term_id, "type": "claim_uses_term"})
    for gate_id, gate in gates.items():
        nodes[gate_id] = {"id": gate_id, "type": "gate", "label": gate["title"], "status": gate["status"]}
        for evidence in gate["evidence"]:
            edges.append({"source": gate_id, "target": evidence["chunk_id"], "type": "evidenced_by"})
        for claim_id in gate.get("blocks_claims", []):
            edges.append({"source": gate_id, "target": claim_id, "type": "blocks_or_conditions"})
        gate_backed = _owner_fully_receipt_backed(gate_id, gate, receipts)
        for receipt_id in owner_to_receipts.get(gate_id, []):
            edges.append({"source": gate_id, "target": receipt_id, "type": "requires_receipt"})
            if gate_backed:
                edges.append({"source": gate_id, "target": receipt_id, "type": "backed_by_receipt"})
        for term in gate.get("terms", []):
            term_id = f"term:{term}"
            nodes.setdefault(term_id, {"id": term_id, "type": "term", "label": term})
            edges.append({"source": gate_id, "target": term_id, "type": "gate_uses_term"})
    for registry_name, objects in semantic_registries.items():
        for object_id, obj in objects.items():
            nodes[object_id] = {
                "id": object_id,
                "type": "semantic_object",
                "registry": registry_name,
                "label": object_id.split(":", 1)[1],
                "object_kind": obj.get("object_kind"),
            }
            for row_id in obj.get("source_rows", []):
                edges.append({"source": object_id, "target": row_id, "type": "promoted_from_row"})
            for capability_id in obj.get("typed_fields", {}).get("capability_ids", []):
                if capability_id in nodes:
                    edge_type = "requires_capability" if registry_name == "public_leaves" else "demonstrates_capability"
                    edges.append({"source": object_id, "target": capability_id, "type": edge_type})
    for receipt_id, receipt in receipts.items():
        nodes[receipt_id] = {
            "id": receipt_id,
            "type": "receipt",
            "label": receipt.get("receipt_kind"),
            "status": receipt.get("status"),
            "artifact_uri": receipt.get("artifact_uri"),
        }
    for route_id, route in routes.items():
        nodes[route_id] = {"id": route_id, "type": "route", "label": route_id.split(".", 1)[1], "purpose": route["purpose"]}
        for doc_id in route["documents"]:
            edges.append({"source": route_id, "target": doc_id, "type": "routes_to_document"})
        for chunk_id in route["chunks"]:
            edges.append({"source": route_id, "target": chunk_id, "type": "routes_to_chunk"})
        targets = route.get("targets", {})
        for table_id in targets.get("tables", []):
            edges.append({"source": route_id, "target": table_id, "type": "routes_to_table"})
        for row_id in targets.get("rows", []):
            edges.append({"source": route_id, "target": row_id, "type": "routes_to_row"})
        for claim_id in targets.get("claims", []):
            edges.append({"source": route_id, "target": claim_id, "type": "routes_to_claim"})
        for gate_id in targets.get("gates", []):
            edges.append({"source": route_id, "target": gate_id, "type": "routes_to_gate"})
        for object_id in targets.get("semantic_objects", []):
            edges.append({"source": route_id, "target": object_id, "type": "routes_to_semantic_object"})
        for term in route["terms"]:
            nodes.setdefault(f"term:{term}", {"id": f"term:{term}", "type": "term", "label": term})
            edges.append({"source": route_id, "target": f"term:{term}", "type": "routes_to_term"})
        for receipt_id in targets.get("receipts", []):
            edges.append({"source": route_id, "target": receipt_id, "type": "routes_to_receipt"})
    authority_pairs = [
        ("doc:codex_doctrine_paper_modules_system_self_comprehension_root", "doc:codex_doctrine_paper_modules_system_self_comprehension_spine", "governs_identity_family"),
        ("doc:codex_doctrine_paper_modules_system_self_comprehension_root", "doc:dist_type_b_type_b_system_grounding_packet", "renders_projection"),
        ("doc:codex_doctrine_paper_modules_system_self_comprehension_root", "doc:dist_type_b_ai_workflow_system_packet", "renders_projection"),
        ("doc:docs_dissemination_actual_deliverable_v0", "doc:docs_dissemination_public_projection_boundary_v0", "governs_boundary"),
        ("doc:docs_dissemination_actual_deliverable_v0", "doc:docs_dissemination_recognition_grade_system_description", "gates_recognition"),
        ("doc:docs_dissemination_public_projection_boundary_v0", "doc:docs_dissemination_public_trust_packet_v0", "sets_claim_boundary_for"),
        ("doc:docs_dissemination_public_projection_boundary_v0", "doc:docs_dissemination_demo_shot_list_v0", "sets_demo_boundary_for"),
    ]
    for source, target, edge_type in authority_pairs:
        if source in nodes and target in nodes:
            edges.append({"source": source, "target": target, "type": edge_type})
    adjacency: dict[str, list[dict[str, str]]] = defaultdict(list)
    for edge in edges:
        adjacency[edge["source"]].append({"target": edge["target"], "type": edge["type"]})
    return {
        "nodes": nodes,
        "edges": edges,
        "adjacency": dict(adjacency),
        "edge_type_schema": _edge_type_schema(),
        "conditional_edge_types": {
            "backed_by_receipt": (
                "Emitted only when a receipt is current, structurally valid, and supports the specific claim/gate owner."
            )
        },
    }


def _receipt_backing_summary(
    claims: dict[str, Any],
    gates: dict[str, Any],
    receipts: dict[str, Any],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for owner_type, objects in (("claim", claims), ("gate", gates)):
        for owner_id, obj in objects.items():
            contract = obj.get("verification_contract", {})
            required_receipts = contract.get("required_receipts", [])
            statuses = [receipts.get(receipt.get("receipt_id"), {}).get("status", "missing_receipt_entity") for receipt in required_receipts]
            backed = bool(required_receipts) and all(
                _receipt_supports_owner(owner_id, receipts.get(receipt.get("receipt_id")))
                for receipt in required_receipts
            )
            rows.append(
                {
                    "owner_type": owner_type,
                    "owner_id": owner_id,
                    "receipt_status": "receipt_backed" if backed else "not_receipt_backed",
                    "required_receipt_count": len(required_receipts),
                    "required_receipt_ids": [receipt.get("receipt_id") for receipt in required_receipts],
                    "receipt_statuses": statuses,
                    "receipt_supports_owner": [
                        bool(_receipt_supports_owner(owner_id, receipts.get(receipt.get("receipt_id"))))
                        for receipt in required_receipts
                    ],
                    "backed": backed,
                }
            )
    backed_count = sum(1 for row in rows if row["backed"])
    backed_owner_ids = sorted(row["owner_id"] for row in rows if row["backed"])
    unbacked_owner_ids = sorted(row["owner_id"] for row in rows if not row["backed"])
    all_required_owners_backed = bool(rows) and backed_count == len(rows)
    return {
        "any_owner_backed": backed_count > 0,
        "all_required_owners_backed": all_required_owners_backed,
        "all_receipt_backed": all_required_owners_backed,
        "backed_count": backed_count,
        "required_owner_count": len(rows),
        "backed_owner_ids": backed_owner_ids,
        "unbacked_owner_ids": unbacked_owner_ids,
        "rows": rows,
    }


def _validate_bundle(
    documents: dict[str, Any],
    chunks: dict[str, Any],
    tables: dict[str, Any],
    rows: dict[str, Any],
    claims: dict[str, Any],
    gates: dict[str, Any],
    receipts: dict[str, Any],
    routes: dict[str, Any],
    graph: dict[str, Any],
    working_tree: dict[str, Any],
    privacy: dict[str, Any],
    selected_missing: list[str],
    parser_warnings: list[dict[str, Any]],
    term_warnings: dict[str, list[str]],
) -> dict[str, Any]:
    node_ids = set(graph["nodes"].keys())
    edge_endpoint_failures = [
        edge for edge in graph["edges"] if edge["source"] not in node_ids or edge["target"] not in node_ids
    ]
    doc_ids_unique = len(documents) == len(set(documents))
    chunk_ids_unique = len(chunks) == len(set(chunks))
    row_refs = [row_id for table in tables.values() for row_id in table.get("row_ids", [])]
    row_ref_counts: dict[str, int] = defaultdict(int)
    for row_id in row_refs:
        row_ref_counts[row_id] += 1
    duplicate_row_refs = sorted(row_id for row_id, count in row_ref_counts.items() if count > 1)
    missing_row_entities = sorted(row_id for row_id in row_refs if row_id not in rows)
    rows_without_table_reference = sorted(row_id for row_id in rows if row_id not in row_ref_counts)
    table_row_count_failures = [
        {
            "table_id": table_id,
            "declared_row_count": table.get("row_count"),
            "row_id_count": len(table.get("row_ids", [])),
        }
        for table_id, table in tables.items()
        if table.get("row_count") != len(table.get("row_ids", []))
    ]
    table_row_reference_failures = []
    row_column_failures = []
    for table_id, table in tables.items():
        columns = table.get("columns", [])
        for row_id in table.get("row_ids", []):
            row = rows.get(row_id)
            if not row:
                continue
            if row.get("table_id") != table_id:
                table_row_reference_failures.append(
                    {"table_id": table_id, "row_id": row_id, "row_table_id": row.get("table_id")}
                )
            if list(row.get("cells", {}).keys()) != columns:
                row_column_failures.append(
                    {
                        "table_id": table_id,
                        "row_id": row_id,
                        "expected_columns": columns,
                        "actual_columns": list(row.get("cells", {}).keys()),
                    }
                )
    contains_row_edge_failures = []
    for edge in graph["edges"]:
        if edge.get("type") != "contains_row":
            continue
        row = rows.get(edge.get("target"))
        if not row or row.get("table_id") != edge.get("source"):
            contains_row_edge_failures.append(edge)
    used_edge_types = {edge["type"] for edge in graph["edges"]}
    declared_edge_types = set(graph.get("edge_type_schema", {}))
    conditional_edge_types = set(graph.get("conditional_edge_types", {}))
    undeclared_edge_types = sorted(used_edge_types - declared_edge_types)
    declared_but_unused_edge_types = sorted(declared_edge_types - used_edge_types - conditional_edge_types)
    reconstruct_failures = []
    for doc_id, doc in documents.items():
        if doc["kind"] != "markdown":
            continue
        reconstructed: list[str] = []
        for chunk_id in doc["chunk_ids"]:
            # `splitlines()` drops a final empty line when a section ends with a
            # blank source line. Use literal newline splitting so line-span
            # reconstruction validates the markdown sectioner, not Python's
            # convenience behavior.
            reconstructed.extend(chunks[chunk_id]["content"].split("\n"))
        original = doc.get("_original_lines", [])
        if reconstructed != original:
            reconstruct_failures.append(doc["relative_path"])
    term_ids = set(TERM_ALIASES)
    unresolved_term_references = []
    for doc_id, doc in documents.items():
        for term in doc.get("terms", []):
            if term not in term_ids:
                unresolved_term_references.append({"owner_type": "document", "owner_id": doc_id, "term": term})
    for chunk_id, chunk in chunks.items():
        for term in chunk.get("terms", []):
            if term not in term_ids:
                unresolved_term_references.append({"owner_type": "chunk", "owner_id": chunk_id, "term": term})
    for route_id, route in routes.items():
        for term in route.get("terms", []):
            if term not in term_ids:
                unresolved_term_references.append({"owner_type": "route", "owner_id": route_id, "term": term})
    for claim_id, claim in claims.items():
        for term in claim.get("terms", []):
            if term not in term_ids:
                unresolved_term_references.append({"owner_type": "claim", "owner_id": claim_id, "term": term})
    for gate_id, gate in gates.items():
        for term in gate.get("terms", []):
            if term not in term_ids:
                unresolved_term_references.append({"owner_type": "gate", "owner_id": gate_id, "term": term})
    unresolved_receipt_references = []
    for owner_type, objects in (("claim", claims), ("gate", gates)):
        for owner_id, obj in objects.items():
            for receipt in obj.get("verification_contract", {}).get("required_receipts", []):
                receipt_id = receipt.get("receipt_id")
                if receipt_id not in receipts:
                    unresolved_receipt_references.append(
                        {"owner_type": owner_type, "owner_id": owner_id, "receipt_id": receipt_id}
                    )
    dirty_sidecars = working_tree.get("dirty_provenance_sidecars", {})
    unresolved_dirty_provenance_sidecars = []
    for row in working_tree.get("dirty_paths_detail", []):
        sidecar_id = row.get("dirty_provenance_sidecar_id")
        if sidecar_id and sidecar_id not in dirty_sidecars:
            unresolved_dirty_provenance_sidecars.append({"path": row.get("path"), "sidecar_id": sidecar_id})
    critical_failures = []
    if selected_missing:
        critical_failures.append("selected_missing_documents")
    if edge_endpoint_failures:
        critical_failures.append("graph_endpoint_failure")
    if not doc_ids_unique:
        critical_failures.append("document_id_collision")
    if not chunk_ids_unique:
        critical_failures.append("chunk_id_collision")
    if reconstruct_failures:
        critical_failures.append("markdown_reconstruction_failure")
    if duplicate_row_refs:
        critical_failures.append("table_row_id_collision")
    if missing_row_entities:
        critical_failures.append("table_row_missing_entity")
    if rows_without_table_reference:
        critical_failures.append("row_entity_without_table_reference")
    if table_row_count_failures:
        critical_failures.append("table_row_count_mismatch")
    if table_row_reference_failures:
        critical_failures.append("table_row_reference_table_id_mismatch")
    if contains_row_edge_failures:
        critical_failures.append("contains_row_edge_table_id_mismatch")
    if row_column_failures:
        critical_failures.append("table_row_column_mismatch")
    if undeclared_edge_types:
        critical_failures.append("edge_types_missing_from_schema")
    if unresolved_term_references:
        critical_failures.append("term_reference_unresolved")
    if unresolved_receipt_references:
        critical_failures.append("receipt_reference_unresolved")
    if unresolved_dirty_provenance_sidecars:
        critical_failures.append("dirty_provenance_sidecar_unresolved")
    row_table_ok = not (
        duplicate_row_refs
        or missing_row_entities
        or rows_without_table_reference
        or table_row_count_failures
        or table_row_reference_failures
        or contains_row_edge_failures
        or row_column_failures
    )
    graph_ok = not edge_endpoint_failures and not undeclared_edge_types
    content_hash_ok = doc_ids_unique and chunk_ids_unique and not selected_missing and not reconstruct_failures
    term_reference_ok = not unresolved_term_references
    receipt_reference_ok = not unresolved_receipt_references
    dirty_sidecar_reference_ok = not unresolved_dirty_provenance_sidecars
    structural_ok = row_table_ok and graph_ok and content_hash_ok and term_reference_ok and receipt_reference_ok and dirty_sidecar_reference_ok
    privacy_pattern_counts = privacy.get("pattern_counts", {})
    privacy_hits_present = any(int(count) > 0 for count in privacy_pattern_counts.values())
    privacy_redacted = bool(privacy.get("redaction", {}).get("applied"))
    frozen_snapshot_ok = not working_tree.get("dirty")
    receipt_backing = _receipt_backing_summary(claims, gates, receipts)
    all_required_owners_receipt_backed = bool(receipt_backing["all_required_owners_backed"])
    claim_receipt_backed = all_required_owners_receipt_backed
    public_release_safe = (
        frozen_snapshot_ok and privacy_redacted and not privacy_hits_present and all_required_owners_receipt_backed
    )
    dirty_paths_listed = int(working_tree.get("dirty_count", 0)) == len(working_tree.get("dirty_status_rows", [])) == len(working_tree.get("dirty_paths_detail", []))
    dirty_paths_with_shell_quotes_normalized = all(
        not row.get("path_has_shell_quotes") for row in working_tree.get("dirty_paths_detail", [])
    )
    modified_dirty_rows = [
        row
        for row in working_tree.get("dirty_paths_detail", [])
        if row.get("worktree_status") != "D" and row.get("index_status") != "D"
    ]
    modified_dirty_paths_resolve_to_existing_worktree_paths = all(
        row.get("exists_in_worktree") for row in modified_dirty_rows
    )
    modified_dirty_paths_have_working_tree_sha256 = all(
        (not row.get("is_file_in_worktree")) or bool(row.get("working_tree_sha256"))
        for row in modified_dirty_rows
    )
    dirty_selected_sources_embedded = all(
        row.get("embedded_document") and row.get("working_tree_sha256")
        for row in working_tree.get("selected_dirty_sources", [])
    )
    dirty_selected_sources_diffed = all(
        row.get("dirty_provenance_sidecar_id") in dirty_sidecars
        for row in working_tree.get("selected_dirty_sources", [])
    )
    dirty_referenced_not_embedded_sidecarred = (
        len(working_tree.get("dirty_referenced_not_embedded", []))
        == int(working_tree.get("dirty_referenced_not_embedded_sidecar_count", 0))
        and all(
            row.get("dirty_provenance_sidecar_id") in dirty_sidecars
            for row in working_tree.get("dirty_referenced_not_embedded", [])
        )
    )
    dirty_runtime_state_hash_accounted = all(
        (not row.get("exists_in_worktree")) or bool(row.get("working_tree_sha256"))
        for row in working_tree.get("dirty_runtime_state_not_embedded", [])
    )
    all_dirty_paths_sidecarred = int(working_tree.get("dirty_provenance_sidecar_count", 0)) == int(
        working_tree.get("dirty_count", 0)
    )
    dirty_provenance_accounted = (
        dirty_paths_listed
        and dirty_sidecar_reference_ok
        and dirty_paths_with_shell_quotes_normalized
        and modified_dirty_paths_resolve_to_existing_worktree_paths
        and modified_dirty_paths_have_working_tree_sha256
        and dirty_selected_sources_embedded
        and dirty_selected_sources_diffed
        and dirty_referenced_not_embedded_sidecarred
        and dirty_runtime_state_hash_accounted
    )
    private_proof_bundle_ok = (
        structural_ok
        and receipt_reference_ok
        and dirty_provenance_accounted
        and not working_tree.get("dirty_generator")
        and not working_tree.get("malformed_dirty_paths")
    )
    warnings = []
    if parser_warnings:
        warnings.append("parser_warnings_present")
    if term_warnings:
        warnings.append("term_index_warnings_present")
    if working_tree.get("dirty"):
        warnings.append("repo_dirty")
    if working_tree.get("selected_dirty_sources"):
        warnings.append("selected_sources_dirty")
    if working_tree.get("dirty_generator"):
        warnings.append("generator_dirty")
    if working_tree.get("dirty_referenced_not_embedded"):
        warnings.append("dirty_referenced_not_embedded")
    if working_tree.get("dirty_runtime_state_not_embedded"):
        warnings.append("dirty_runtime_state_not_embedded")
    if any((row.get("index_status") or " ") != " " for row in working_tree.get("dirty_paths_detail", [])):
        warnings.append("dirty_staged_file_present")
    if any(
        not row.get("selected_for_embedding") and not row.get("referenced_by_snapshot")
        for row in working_tree.get("dirty_paths_detail", [])
    ):
        warnings.append("dirty_unreferenced_file_present")
    if working_tree.get("malformed_dirty_paths"):
        warnings.append("malformed_dirty_paths_present")
    if privacy_hits_present:
        warnings.append("privacy_hits_present")
    if not privacy_redacted:
        warnings.append("redaction_not_applied")
    return {
        "ok": structural_ok,
        "ok_scope": "structural_only",
        "gates": {
            "structural_ok": structural_ok,
            "row_table_ok": row_table_ok,
            "graph_ok": graph_ok,
            "content_hash_ok": content_hash_ok,
            "term_reference_ok": term_reference_ok,
            "receipt_reference_ok": receipt_reference_ok,
            "dirty_sidecar_reference_ok": dirty_sidecar_reference_ok,
            "dirty_paths_listed": dirty_paths_listed,
            "dirty_paths_with_shell_quotes_normalized": dirty_paths_with_shell_quotes_normalized,
            "modified_dirty_paths_resolve_to_existing_worktree_paths": modified_dirty_paths_resolve_to_existing_worktree_paths,
            "modified_dirty_paths_have_working_tree_sha256": modified_dirty_paths_have_working_tree_sha256,
            "dirty_selected_sources_embedded": dirty_selected_sources_embedded,
            "dirty_selected_sources_diffed": dirty_selected_sources_diffed,
            "dirty_referenced_not_embedded_sidecarred": dirty_referenced_not_embedded_sidecarred,
            "dirty_runtime_state_hash_accounted": dirty_runtime_state_hash_accounted,
            "all_dirty_paths_sidecarred": all_dirty_paths_sidecarred,
            "dirty_provenance_accounted": dirty_provenance_accounted,
            "private_proof_bundle_ok": private_proof_bundle_ok,
            "frozen_snapshot_ok": frozen_snapshot_ok,
            "any_owner_receipt_backed": bool(receipt_backing["any_owner_backed"]),
            "all_required_owners_receipt_backed": all_required_owners_receipt_backed,
            "claim_receipt_backed": claim_receipt_backed,
            "privacy_redacted": privacy_redacted,
            "public_release_safe": public_release_safe,
        },
        "critical_failures": critical_failures,
        "warnings": warnings,
        "notices": [],
        "selected_missing_documents": selected_missing,
        "all_doc_ids_unique": doc_ids_unique,
        "all_chunk_ids_unique": chunk_ids_unique,
        "all_graph_endpoints_resolve": not edge_endpoint_failures,
        "graph_endpoint_failure_count": len(edge_endpoint_failures),
        "undeclared_edge_types": undeclared_edge_types,
        "declared_but_unused_edge_types": declared_but_unused_edge_types,
        "conditional_edge_types": sorted(conditional_edge_types),
        "all_edge_types_declared": not undeclared_edge_types,
        "unresolved_term_references": unresolved_term_references,
        "all_term_references_resolve": term_reference_ok,
        "unresolved_receipt_references": unresolved_receipt_references,
        "all_receipt_references_resolve": receipt_reference_ok,
        "unresolved_dirty_provenance_sidecars": unresolved_dirty_provenance_sidecars,
        "all_dirty_provenance_sidecar_references_resolve": dirty_sidecar_reference_ok,
        "receipt_backing": receipt_backing,
        "markdown_chunks_reconstruct_documents": not reconstruct_failures,
        "markdown_reconstruction_failures": reconstruct_failures,
        "table_row_reference_count": len(row_refs),
        "unique_table_row_reference_count": len(set(row_refs)),
        "row_entity_count": len(rows),
        "all_table_row_ids_unique": not duplicate_row_refs,
        "duplicate_table_row_ids": duplicate_row_refs,
        "missing_row_entities": missing_row_entities,
        "rows_without_table_reference": rows_without_table_reference,
        "table_row_count_failures": table_row_count_failures,
        "table_row_reference_failures": table_row_reference_failures,
        "contains_row_edge_failures": contains_row_edge_failures,
        "row_column_failures": row_column_failures,
        "parser_warnings": parser_warnings,
        "term_index_warnings": term_warnings,
    }


def build_bundle(
    repo_root: Path,
    output: Path,
    max_term_occurrences: int,
    receipt_root: Path | None = None,
) -> dict[str, Any]:
    receipt_root = (receipt_root or DEFAULT_RECEIPT_ROOT).expanduser().resolve()
    selected_paths = set(SOURCE_PATHS)
    documents: dict[str, dict[str, Any]] = {}
    chunks: dict[str, dict[str, Any]] = {}
    path_to_doc_id: dict[str, str] = {}
    selected_missing: list[str] = []
    parser_warnings: list[dict[str, Any]] = []

    for rel_path in SOURCE_PATHS:
        path = repo_root / rel_path
        if not path.exists():
            selected_missing.append(rel_path)
            continue
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        doc_id = f"doc:{_slug(rel_path)}"
        scopes = _authority_scopes(rel_path)
        dominant = _dominant_authority(scopes)
        doc_chunks: list[dict[str, Any]]
        embedded_blocks: list[dict[str, Any]] = []
        if rel_path.endswith(".json"):
            doc_chunks = _chunk_json(doc_id, rel_path, text)
        else:
            doc_chunks, embedded_blocks = _chunk_markdown(doc_id, rel_path, text)
        for index, chunk in enumerate(doc_chunks):
            if index > 0:
                chunk["prev_chunk_id"] = doc_chunks[index - 1]["chunk_id"]
            else:
                chunk["prev_chunk_id"] = None
            if index + 1 < len(doc_chunks):
                chunk["next_chunk_id"] = doc_chunks[index + 1]["chunk_id"]
            else:
                chunk["next_chunk_id"] = None
            terms, matches = _detect_terms(chunk["content"])
            chunk["terms"] = terms
            chunk["term_matches"] = matches
            chunks[chunk["chunk_id"]] = chunk
        for block in embedded_blocks:
            if block["detected_headings"]:
                parser_warnings.append(
                    {
                        "path": rel_path,
                        "warning": "headings_detected_inside_fenced_block_not_used_as_structural_chunks",
                        "line_start": block["line_start"],
                        "line_end": block["line_end"],
                        "detected_headings": block["detected_headings"],
                    }
                )
        doc_terms, _matches = _detect_terms(text)
        documents[doc_id] = {
            "doc_id": doc_id,
            "relative_path": rel_path,
            "source_uri": _repo_uri(rel_path),
            "role": ROLES.get(rel_path, ""),
            "category": _classify_category(rel_path),
            "authority_scopes": scopes,
            "authority_posture": dominant["posture"],
            "authority_weight": dominant["weight"],
            "kind": "json" if rel_path.endswith(".json") else "markdown",
            "bytes": len(raw),
            "line_count": len(text.splitlines()),
            "sha256": _sha256_file(path),
            "chunk_ids": [chunk["chunk_id"] for chunk in doc_chunks],
            "terms": doc_terms,
            "embedded_blocks": embedded_blocks,
            "freshness": _extract_freshness(rel_path, text),
            "_original_lines": text.splitlines(),
        }
        path_to_doc_id[rel_path] = doc_id

    tables, rows = _extract_markdown_tables(chunks)
    term_index, term_warnings = _term_index(chunks, max_term_occurrences)
    claims = _build_claims(chunks, documents)
    gates = _build_gates(chunks, claims, documents)
    routes = _build_routes(documents, chunks)
    semantic_registries = _semantic_registries(rows)
    receipts, receipt_to_owners, owner_to_receipts = _build_receipts(repo_root, receipt_root, claims, gates)
    _sync_receipt_requirement_statuses(claims, gates, receipts)
    _sync_actual_backed_owners(claims, gates, receipts)
    _attach_term_ids(documents, chunks, claims, gates, routes)
    route_to_entities = _route_entity_index(
        routes,
        documents,
        chunks,
        tables,
        claims,
        gates,
        semantic_registries,
        owner_to_receipts,
    )
    routes = _attach_route_targets(routes, route_to_entities)
    graph = _build_graph(
        documents,
        chunks,
        tables,
        rows,
        claims,
        gates,
        receipts,
        routes,
        semantic_registries,
        owner_to_receipts,
    )
    route_coverage = _route_coverage(routes, documents, chunks, tables)
    path_references = _extract_path_references(chunks, repo_root, selected_paths)
    working_tree = _working_tree_manifest(repo_root, selected_paths, path_references)
    path_references = _annotate_referenced_artifacts_with_working_tree(path_references, working_tree)
    _annotate_claim_dirty_evidence(claims, chunks, working_tree)
    privacy = _privacy_report(chunks)
    validation = _validate_bundle(
        documents,
        chunks,
        tables,
        rows,
        claims,
        gates,
        receipts,
        routes,
        graph,
        working_tree,
        privacy,
        selected_missing,
        parser_warnings,
        term_warnings,
    )

    for doc in documents.values():
        doc.pop("_original_lines", None)

    creation_pseudocode = """
function build_holographic_snapshot(repo_root, source_manifest):
    load selected source files
    for each file:
        hash source bytes
        classify role, category, authority scopes
        split markdown by headings while ignoring headings inside fenced code blocks
        split json by top-level keys
        emit canonical document entity without duplicate full content
        emit chunk entities with content, source span, chunk hash, terms, and prev/next links
        record embedded fenced blocks as non-structural blocks
    parse markdown tables outside code fences into table and row entities
    scan all chunks for repo path references and classify included/private/out-of-scope/unresolved
    record dirty working-tree status with selected-source, generator, and volatile-runtime classifications
    build controlled-term index with truncation metadata and matched aliases
    instantiate canonical local claims with evidence chunks, freshness, and receipt requirements
    instantiate executable or Type-A-verification gate contracts from boundary/trust docs
    ingest existing proof receipts as first-class receipt entities without running their producers
    promote selected table rows into semantic registries where stable ids exist
    attach route targets for tables, rows, claims, gates, and promoted semantic objects
    build graph over documents, chunks, terms, tables, rows, claims, gates, receipts, semantic objects, and routes
    validate structural gates separately from frozen-snapshot, privacy-redaction, and release-safety gates
    write normalized json with canonical entities once plus lightweight indexes
""".strip()

    navigation_pseudocode = """
function answer_with_snapshot(bundle, question):
    classify question into question_routes
    read the route purpose, documents, chunks, and term axes
    prefer route.targets / indexes.route_to_entities for row/table/claim/gate/semantic-object entry
    expand from selected chunks through:
        prev/next section edges
        supported claims and gates
        receipt entities, receipt requirements, and executable gate commands
        term_index occurrences
        table rows under the same chunk
        promoted semantic registry objects
        authority parent/child edges
    rank candidates by authority scope, route fit, term overlap, and freshness
    read top chunks/rows/claims first, not every file linearly
    separate local bundle facts, online facts, synthesis, speculation, and Type A verification requests
""".strip()

    research_prompt = """
You are a research AI studying ai_workflow. This JSON is a typed, normalized,
holographic research snapshot, not a flat archive. Start from metadata,
navigation, question_routes, routes, claims, gates, term_index, and graph. Use
chunks and rows as evidence. Treat generated packets, videos, websites,
frontend views, and facts cards as projections unless backed by authority.
For questions about how an agent should enter dissemination, start from
route.agent_entry_to_dissemination before reading individual dissemination
documents.

After reading the local snapshot, search deeply online across programming
systems, HCI, tools for thought, moldable development, live programming,
provenance, reproducible research, observability, artifact evaluation,
mission-control UIs, release safety, redaction, claim indexing, and technical
monographs. Produce a serious research paper that identifies what ai_workflow
is, what traditions clarify it, what comparisons are traps, what blindspots
remain, and what evidence structure would make the controlled public successor
projection legible to serious technical readers.

Do not treat ai_workflow as a toy repo, generic agent framework, PKM, RAG
dashboard, browser automation demo, SaaS product, agent OS, AGI infrastructure,
or first-ever primitive invention. Exact private facts require Type A
verification requests.
""".strip()

    question_routes = {
        "how_should_an_agent_enter_dissemination": ["route.agent_entry_to_dissemination", "route.public_successor_deliverable"],
        "what_is_ai_workflow": ["route.system_identity_first_contact", "route.category_and_external_legibility"],
        "what_is_the_public_artifact": ["route.public_successor_deliverable", "route.safety_boundary_and_release_gate"],
        "how_to_use_the_holographic_bundle_for_dissemination_research": ["route.agent_entry_to_dissemination", "route.public_successor_deliverable", "route.category_and_external_legibility"],
        "what_should_the_paper_contain": ["route.paper_as_ir_and_traceability", "route.public_successor_deliverable"],
        "how_should_video_or_demo_work": ["route.demo_and_frontend_proof", "route.safety_boundary_and_release_gate"],
        "how_to_avoid_overclaiming": ["route.safety_boundary_and_release_gate", "route.category_and_external_legibility"],
        "how_to_evaluate_trust": ["route.paper_as_ir_and_traceability", "route.demo_and_frontend_proof", "route.public_successor_deliverable"],
        "what_is_authoritative": ["route.system_identity_first_contact", "route.safety_boundary_and_release_gate"],
        "what_is_generated_or_stale": ["route.system_identity_first_contact", "route.public_successor_deliverable"],
        "what_claims_are_supported": ["route.paper_as_ir_and_traceability", "route.safety_boundary_and_release_gate"],
    }

    bundle = {
        "schema": {"name": "ai_workflow_holographic_research_snapshot", "version": SCHEMA_VERSION},
        "snapshot": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "purpose": "cold-reader navigation plus bounded system/proof snapshot for external research AI",
            "repo_state": {
                "commit": working_tree["commit"],
                "branch": working_tree["branch"],
                "dirty": working_tree["dirty"],
                "dirty_count": working_tree["dirty_count"],
                "dirty_paths": [row["path"] for row in working_tree["dirty_status_rows"]],
                "dirty_paths_truncated": working_tree["dirty_paths_truncated"],
            },
            "working_tree_state": working_tree,
            "generator": {
                "source_uri": _repo_uri("tools/meta/dissemination/build_holographic_research_bundle.py"),
                "source_sha256": _sha256_file(repo_root / "tools/meta/dissemination/build_holographic_research_bundle.py"),
                "version": SCHEMA_VERSION,
                "command_template": "tools/meta/dissemination/build_holographic_research_bundle.py --output <output_uri> [--max-term-occurrences N] [--receipt-root <local_receipt_root>]",
                "argv_redacted": _redacted_generator_argv(output, receipt_root),
                "output_uri": "downloads://" + output.name,
            },
            "receipt_inputs": {
                "artifact_root": PUBLIC_PROJECTION_ARTIFACT_ROOT,
                "local_diagnostic_root": str(receipt_root),
                "policy": "read_existing_receipts_only_do_not_run_projection_or_gate",
            },
        },
        "manifests": {
            "included_sources": [
                {
                    "path": path,
                    "source_uri": _repo_uri(path),
                    "reason": ROLES.get(path, "selected system-description or dissemination surface"),
                }
                for path in SOURCE_PATHS
            ],
            "selected_missing_documents": selected_missing,
            "referenced_artifacts": path_references,
            "privacy_scan_report": privacy,
        },
        "entities": {
            "documents": documents,
            "chunks": chunks,
            "tables": tables,
            "rows": rows,
            "terms": {
                term: {
                    "term_id": term,
                    "canonical_node_id": f"term:{term}",
                    "family": family,
                    "aliases": aliases,
                    "alias_metadata": [_alias_metadata(term, alias) for alias in aliases],
                }
                for family, terms in TERM_TAXONOMY.items()
                for term, aliases in terms.items()
            },
            "claims": claims,
            "gates": gates,
            "receipts": receipts,
            "routes": routes,
            "semantic_registries": semantic_registries,
        },
        "indexes": {
            "_metadata": {
                "denormalized": True,
                "canonical_sources": {
                    "documents": "entities.documents",
                    "chunks": "entities.chunks",
                    "tables": "entities.tables",
                    "rows": "entities.rows",
                    "semantic_registries": "entities.semantic_registries",
                    "receipts": "entities.receipts",
                    "routes": "entities.routes",
                    "edges": "graph.edges",
                },
            },
            "path_to_doc_id": path_to_doc_id,
            "term_to_occurrences": term_index,
            "route_to_entities": route_to_entities,
            "receipt_to_owners": receipt_to_owners,
            "owner_to_receipts": owner_to_receipts,
            "question_to_routes": question_routes,
            "authority_ladder": sorted(
                [
                    {
                        "doc_id": doc["doc_id"],
                        "relative_path": doc["relative_path"],
                        "authority_weight": doc["authority_weight"],
                        "authority_posture": doc["authority_posture"],
                        "authority_scopes": doc["authority_scopes"],
                    }
                    for doc in documents.values()
                ],
                key=lambda item: -int(item["authority_weight"]),
            ),
        },
        "graph": graph,
        "quality": {
            "validation": validation,
            "coverage": {
                "document_count": len(documents),
                "chunk_count": len(chunks),
                "table_count": len(tables),
                "row_count": len(rows),
                "claim_count": len(claims),
                "gate_count": len(gates),
                "receipt_count": len(receipts),
                "semantic_registry_counts": {name: len(objects) for name, objects in semantic_registries.items()},
                "route_coverage": route_coverage,
            },
            "freshness": {
                "bundle_created_at": datetime.now(timezone.utc).isoformat(),
                "source_observed_at": {doc["relative_path"]: doc["freshness"] for doc in documents.values()},
                "freshness_rule": "date extraction is heuristic; public claims need Type A generator/freshness verification",
            },
            "known_limitations": [
                "This is a selected research snapshot, not a complete live-substrate audit.",
                "Claims and gates carry receipt requirements, but are not release-backed until their receipts are present and fresh.",
                "Referenced artifact classification is heuristic and should be verified before release use.",
                "Privacy scan records pattern presence; it does not redact embedded source content.",
            ],
        },
        "task_prompts": {"research_prompt_2026_05_05": research_prompt},
        "guidance": {
            "creation_pseudocode": creation_pseudocode,
            "navigation_pseudocode": navigation_pseudocode,
        },
    }
    serialized_scan = _serialized_privacy_scan(bundle)
    bundle["manifests"]["privacy_scan_report"]["scan_scope"].append("final_serialized_json")
    bundle["manifests"]["privacy_scan_report"]["serialized_json_scan"] = serialized_scan
    serialized_privacy_hits_present = any(int(count) > 0 for count in serialized_scan["pattern_counts"].values())
    bundle["quality"]["validation"]["serialized_privacy_hits_present"] = serialized_privacy_hits_present
    if serialized_privacy_hits_present and "serialized_privacy_hits_present" not in bundle["quality"]["validation"]["warnings"]:
        bundle["quality"]["validation"]["warnings"].append("serialized_privacy_hits_present")
    bundle["quality"]["privacy"] = {
        "report_kind": "privacy_scan_summary",
        "source_chunk_pattern_counts": privacy["pattern_counts"],
        "serialized_json_pattern_counts": serialized_scan["pattern_counts"],
        "redaction_applied": False,
    }
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-term-occurrences", type=int, default=200)
    parser.add_argument(
        "--receipt-root",
        type=Path,
        default=DEFAULT_RECEIPT_ROOT,
        help="Local diagnostic directory containing projection_receipt.json and portability_gate_report.json if already produced.",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    output = args.output.expanduser().resolve()
    bundle = build_bundle(repo_root, output, args.max_term_occurrences, args.receipt_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    parsed = json.loads(output.read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "output": str(output),
                "schema": parsed["schema"],
                "documents": parsed["quality"]["coverage"]["document_count"],
                "chunks": parsed["quality"]["coverage"]["chunk_count"],
                "tables": parsed["quality"]["coverage"]["table_count"],
                "rows": parsed["quality"]["coverage"]["row_count"],
                "claims": parsed["quality"]["coverage"]["claim_count"],
                "gates": parsed["quality"]["coverage"]["gate_count"],
                "receipts": parsed["quality"]["coverage"]["receipt_count"],
                "validation_ok": parsed["quality"]["validation"]["ok"],
                "bytes": output.stat().st_size,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
