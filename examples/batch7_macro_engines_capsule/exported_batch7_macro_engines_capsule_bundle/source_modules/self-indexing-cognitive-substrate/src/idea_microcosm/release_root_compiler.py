"""Compile the release root into branch and standards diagnostics.

[PURPOSE]
Make the public-safe release microcosm branch-navigable and diagnosable without
promoting generated projections into source authority.

[INTERFACE]
The public entrypoint is build_release_root_compiler(), with
validate_release_root_artifacts() available for tests and downstream validators.

[FLOW]
Scan release Python source, build the root authority contract, build the branch
graph, validate required evidence and anti-claim fields, then write JSON reports.

[DEPENDENCIES]
Uses only the Python standard library and release-root JSON/source files.

[CONSTRAINTS]
This compiler is scoped to self-indexing-cognitive-substrate and does not
overwrite sibling cold-entry or concept-graph artifacts.
- When-needed: Open when the microcosm needs branch graph, root contract, std_python report, or proof-tail diagnostics from source.
- Escalates-to: codex/standards/std_python.py; microcosms/specimen_suite/std_python_compliance_report.json; src/idea_microcosm/validators.py::validate_release_root_artifacts
- Navigation-group: microcosm_release_root_compiler
- Validator: validator.release_root_compiler; validator.private_boundary
- Receipt: microcosms/specimen_suite/release_root_compiler_receipt.json
- Public-boundary: Compiler success is local fixture evidence only, not hosted CI, publication approval, or private-root equivalence.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BRANCH_GRAPH_PATH = "microcosms/specimen_suite/release_branch_graph.json"
ROOT_CONTRACT_PATH = "microcosms/specimen_suite/release_root_contract.json"
STD_PYTHON_REPORT_PATH = "microcosms/specimen_suite/std_python_compliance_report.json"
RECEIPT_PATH = "microcosms/specimen_suite/release_root_compiler_receipt.json"
STD_PYTHON_STANDARD_PATH = Path("codex/standards/std_python.py")
MICROCOSM_ROUTE_ATOMS = (
    "When-needed",
    "Escalates-to",
    "Navigation-group",
    "Validator",
    "Receipt",
    "Public-boundary",
    "Anti-claim",
)
LEAF_STEM_ALIASES = {
    "atlas_navigation_specimen": "atlas_navigation_bands",
    "executable_grammar_specimen": "executable_grammar_metabolism",
    "frontend_hud_control_surface_specimen": "frontend_cockpit_hud",
    "release_root_compiler": "specimen_suite",
    "release_standards_specimen": "release_standards_axiom_gate",
    "specimen_suite_probe": "specimen_suite",
    "task_ledger_specimen": "task_ledger_cap_economy",
}
LEAF_VALIDATOR_ALIASES = {
    "executable_grammar_metabolism": "validator.executable_grammar_metabolism_specimen",
    "frontend_cockpit_hud": "validator.frontend_hud_control_surface_specimen",
    "release_standards_axiom_gate": "validator.release_standards_axiom_gate_specimen",
    "specimen_suite": "validator.release_specimen_suite_probe",
}

SUPPORT_ROUTE_PROFILES: dict[str, dict[str, Any]] = {
    "__init__": {
        "track": "cold_agent_entry",
        "group": "microcosm_support.package_runtime",
        "when": "Open when import identity, package version, or release-runtime entrypoints need a local package root.",
        "escalates": ["src/idea_microcosm/cli.py", "navigation/entry_packet.json"],
        "validator": "validator.import_smoke",
        "receipt": "receipts/validation_run.json",
    },
    "axiom_kernel": {
        "track": "standards_runtime",
        "group": "microcosm_support.standards_runtime",
        "when": "Open when principles, candidate axioms, or teleology rows need executable release-local obligations.",
        "escalates": ["state/axiom_kernel.json", "state/teleology_map.json", "ports/port_packets.json"],
        "validator": "validator.axiom_kernel",
        "receipt": "receipts/axiom_kernel_seed.json",
    },
    "cold_eval": {
        "track": "cold_agent_entry",
        "group": "microcosm_support.cold_agent_entry",
        "when": "Open when comparing flat repository entry against idea-first cold-agent navigation.",
        "escalates": ["runs/cold_agent_ab/seed_scorecard.json", "navigation/entry_packet.json"],
        "validator": "validator.cold_agent_eval",
        "receipt": "runs/cold_agent_ab/seed_scorecard.json",
    },
    "cold_sandbox": {
        "track": "cold_agent_entry",
        "group": "microcosm_support.clone_probe",
        "when": "Open when validating a clone-local checkout, required public-safe files, or fail-closed gates.",
        "escalates": ["probes/cold_sandbox_probe.py", "receipts/cold_sandbox_probe_latest.json"],
        "validator": "validator.cold_sandbox",
        "receipt": "receipts/cold_sandbox_probe_latest.json",
    },
    "pattern_miner": {
        "track": "standards_runtime",
        "group": "microcosm_support.pattern_transfer",
        "when": "Open when converting bounded pattern rows into clean-room module-blueprint inputs.",
        "escalates": ["registry/internal_pattern_inventory.json", "modules/module_blueprints.json"],
        "validator": "validator.pattern_miner",
        "receipt": "receipts/pattern_miner_seed.json",
    },
    "port_packets": {
        "track": "standards_runtime",
        "group": "microcosm_support.pattern_transfer",
        "when": "Open when turning module blueprints into implementation packets, acceptance checks, and proof refs.",
        "escalates": ["modules/module_blueprints.json", "ports/port_packets.json"],
        "validator": "validator.port_packets",
        "receipt": "receipts/port_packets_seed.json",
    },
    "principle_matrix": {
        "track": "standards_runtime",
        "group": "microcosm_support.standards_runtime",
        "when": "Open when mapping principles and axioms to artifacts, capabilities, validators, and proof refs.",
        "escalates": ["registry/principles.json", "registry/axioms.json", "state/principle_matrix.json"],
        "validator": "validator.principle_enforcement",
        "receipt": "receipts/principle_matrix_seed.json",
    },
    "release_candidates": {
        "track": "release_restraint",
        "group": "microcosm_support.release_selection",
        "when": "Open when scoring public-safe candidate rows without granting release or publication authority.",
        "escalates": ["registry/release_candidates.json", "release/publication_gate.json"],
        "validator": "validator.release_candidates",
        "receipt": "receipts/release_candidates_seed.json",
    },
    "site_projection": {
        "track": "visual_review",
        "group": "microcosm_support.site_projection",
        "when": "Open when rendering sandbox site pages from registry cards, gates, and public-safe projection manifests.",
        "escalates": ["state/site_projection_manifest.json", "microcosms/website_card_projection_gate/card_gate.json"],
        "validator": "validator.site_projection",
        "receipt": "receipts/site_projection_manifest_latest.json",
    },
    "strategy": {
        "track": "durable_work",
        "group": "microcosm_support.work_metabolism",
        "when": "Open when a receipt needs to become a continue-or-repair strategy row.",
        "escalates": ["strategy/ledger.jsonl", "strategy/open_subphases.json"],
        "validator": "validator.strategy_ledger",
        "receipt": "receipts/strategy_tick_latest.json",
    },
    "synthesis": {
        "track": "durable_work",
        "group": "microcosm_support.intent_to_artifact",
        "when": "Open when a release-local note fixture needs idea, capability, and validator matches.",
        "escalates": ["state/idea_graph.json", "state/synthesis_latest.json"],
        "validator": "validator.synthesis",
        "receipt": "receipts/synthesis_seed.json",
    },
    "teleology": {
        "track": "standards_runtime",
        "group": "microcosm_support.teleology",
        "when": "Open when principles and axioms need pressure classes, next moves, or deliverable links.",
        "escalates": ["state/teleology_map.json", "registry/principles.json", "registry/axioms.json"],
        "validator": "validator.teleology_map",
        "receipt": "receipts/teleology_seed.json",
    },
    "validators": {
        "track": "diagnostic_review",
        "group": "microcosm_support.validators",
        "when": "Open when public-boundary, receipt, manifest, or release-root validator behavior needs source proof.",
        "escalates": ["registry/validators.json", "receipts/validation_run.json"],
        "validator": "validator.release_root_compiler",
        "receipt": "receipts/validation_run.json",
    },
    "work_packet": {
        "track": "durable_work",
        "group": "microcosm_support.work_metabolism",
        "when": "Open when a note fixture needs to become bounded implementation steps and acceptance checks.",
        "escalates": ["state/work_items.jsonl", "work_packets/"],
        "validator": "validator.work_packet",
        "receipt": "receipts/work_packet_seed.json",
    },
}

ROLE_ROUTE_PROFILES: dict[str, dict[str, Any]] = {
    "probe": {
        "track": "cold_agent_entry",
        "group": "microcosm_support.probe",
        "when": "Open when a probe wrapper, clone-local smoke check, or receipt-emitting command needs exact code.",
        "escalates": ["src/idea_microcosm/cold_sandbox.py", "receipts/cold_sandbox_probe_latest.json"],
        "validator": "validator.cold_sandbox",
        "receipt": "receipts/cold_sandbox_probe_latest.json",
    },
    "test": {
        "track": "diagnostic_review",
        "group": "microcosm_support.test_contract",
        "when": "Open when std_python, release-root, or leaf-entry expectations need executable test evidence.",
        "escalates": ["microcosms/specimen_suite/std_python_compliance_report.json", "receipts/validation_run.json"],
        "validator": "validator.release_root_compiler",
        "receipt": "receipts/validation_run.json",
    },
    "library": {
        "track": "composition",
        "group": "microcosm_support.release_python_source",
        "when": "Open when a release-root support library is the implementation drilldown after root or leaf selection.",
        "escalates": ["navigation/entry_packet.json", "microcosms/specimen_suite/std_python_compliance_report.json"],
        "validator": "validator.release_root_compiler",
        "receipt": "microcosms/specimen_suite/release_root_compiler_receipt.json",
    },
}

BUILDER_COMMAND = (
    "PYTHONPATH=src python3 -m idea_microcosm.cli build-release-root-compiler "
    "--root . --write-receipt"
)

ROOT_ANTI_CLAIMS = [
    "local fixture evidence is public release approval",
    "generated projections are source authority",
    "hosted public CI is proven by local receipts",
    "the release microcosm is equivalent to the private root",
    "standards diagnostics are security or standards certification",
]

CORE_BRANCH_REQUIREMENTS = [
    "layman_summary",
    "technical_summary",
    "what_to_run",
    "expected_output",
    "evidence_refs",
    "standards_refs",
    "anti_claims",
    "authority_boundary",
    "next_branch",
    "next_gap",
]

STD_PYTHON_PROTECTED_WARNING_BOUNDARIES = {
    "src/idea_microcosm/atlas_navigation_specimen.py": {
        "owner_class": "sibling_cold_entry_owned",
        "protection_status": "protected_sibling",
        "reentry_condition": "Re-enter only after the atlas-navigation/cold-entry lane is explicitly released or this source owner is claimed by a compiler patch.",
    },
    "src/idea_microcosm/cold_start_agent_skills_pack_specimen.py": {
        "owner_class": "sibling_cold_entry_owned",
        "protection_status": "protected_sibling",
        "reentry_condition": "Re-enter only after the cold-start agent skill lane is released and the patch consumes, rather than rewrites, the cold-entry route.",
    },
    "src/idea_microcosm/concept_graph_cards_specimen.py": {
        "owner_class": "sibling_cold_entry_owned",
        "protection_status": "protected_sibling",
        "reentry_condition": "Re-enter only after the concept-graph/cold-entry sibling owner releases this source file.",
    },
    "src/idea_microcosm/concurrency_guard.py": {
        "owner_class": "sibling_concurrency_guard_owned",
        "protection_status": "protected_sibling",
        "reentry_condition": "Re-enter only after the native concurrency guard mission releases this source file.",
    },
    "src/idea_microcosm/redaction_scan.py": {
        "owner_class": "public_safety_scanner_owned",
        "protection_status": "protected_scanner_fixture",
        "reentry_condition": "Re-enter only through the public-safety scanner lane; scanner vocabulary is intentional fixture material, not a leaked secret.",
    },
    "src/idea_microcosm/specimen_suite_probe.py": {
        "owner_class": "sibling_cold_entry_owned",
        "protection_status": "protected_sibling",
        "reentry_condition": "Re-enter only after sibling cold-entry integration work no longer owns specimen-suite probe behavior.",
    },
    "src/idea_microcosm/validators.py": {
        "owner_class": "validator_owned",
        "protection_status": "protected_validator",
        "reentry_condition": "Re-enter only through a validator-owned patch that preserves public-boundary token intent and validator contracts.",
    },
    "tests/test_microcosm_contract.py": {
        "owner_class": "test_contract_owned",
        "protection_status": "protected_test_contract",
        "reentry_condition": "Re-enter only through a test-contract patch or after the sibling cold-entry lane releases contract-test ownership.",
    },
    "tests/test_concurrency_guard.py": {
        "owner_class": "sibling_concurrency_guard_owned",
        "protection_status": "protected_sibling_test",
        "reentry_condition": "Re-enter only after the native concurrency guard mission releases its contract test ownership.",
    },
}

AUTHORITY_TOKEN_PATTERNS = [
    ("public release ready", "publication_permission", "release/publication_gate.json"),
    ("release ready", "publication_permission", "release/publication_gate.json"),
    ("public release approval", "publication_permission", "release/publication_gate.json"),
    ("hosted ready", "hosted_public_evidence", "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json"),
    ("hosted public ready", "hosted_public_evidence", "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json"),
    ("hosted public availability", "hosted_public_evidence", "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json"),
    ("hosted public ci", "hosted_public_evidence", "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json"),
    ("publication approved", "publication_permission", "release/publication_gate.json"),
    ("publication permission", "publication_permission", "release/publication_gate.json"),
    ("thiel ready", "publication_permission", "microcosms/thiel_evidence_packet_gate/evidence_packet.json"),
    ("certified", "certification_claim", ROOT_CONTRACT_PATH),
    ("security certified", "certification_claim", ROOT_CONTRACT_PATH),
    ("standards certified", "certification_claim", ROOT_CONTRACT_PATH),
    ("standards certification", "certification_claim", ROOT_CONTRACT_PATH),
    ("private-root equivalent", "private_root_evidence", ROOT_CONTRACT_PATH),
    ("private-root equivalence", "private_root_evidence", ROOT_CONTRACT_PATH),
    ("private root equivalence", "private_root_evidence", ROOT_CONTRACT_PATH),
    ("benchmark win", "benchmark_claim", "microcosms/lab_evolve_failure_replay/replay_graph.json"),
    ("theorem proved", "theorem_claim", ROOT_CONTRACT_PATH),
]

AUTHORITY_SAFE_CONTEXT_TERMS = [
    "anti_claim",
    "anti-claim",
    "authority_token_patterns",
    "blocked",
    "blocked_without_gate",
    "boundary",
    "cannot",
    "cannot_claim",
    "cannot_infer",
    "does not",
    "fail closed",
    "fail-closed",
    "fail_closed",
    "forbidden_authority_inferences",
    "gate",
    "local diagnostics only",
    "never",
    "no ",
    "non-claim",
    "non_claim",
    "not ",
    "not_",
    "omissions",
    "projection_not_authority",
    "public_safety_boundary",
    "remain",
    "remains",
    "requires",
    "root_anti_claims",
    "unless",
    "until",
    "without",
]

AUTHORITY_STRONG_CONTEXT_TERMS = [
    "anti_claim",
    "anti-claim",
    "authority_token_patterns",
    "blocked",
    "blocked_without_gate",
    "cannot",
    "cannot_claim",
    "cannot_infer",
    "does not",
    "fail closed",
    "fail-closed",
    "fail_closed",
    "forbidden_authority_inferences",
    "local diagnostics only",
    "never",
    "non-claim",
    "non_claim",
    "not certification",
    "not hosted ci proof",
    "not private-root equivalence",
    "not public release approval",
    "not publication permission",
    "projection_not_authority",
    "public_safety_boundary",
    "root_anti_claims",
    "unless",
    "until",
    "without",
]

AUTHORITY_BOUNDARY_CONTEXT_TERMS = sorted(set(AUTHORITY_SAFE_CONTEXT_TERMS) | set(AUTHORITY_STRONG_CONTEXT_TERMS))

AUTHORITY_SCAN_SOURCE_PATHS = [
    "README.md",
    "RELEASE_SCOPE.md",
    "src/idea_microcosm/release_root_compiler.py",
]
AUTHORITY_PUBLIC_SOURCE_PATHS = {"README.md", "RELEASE_SCOPE.md"}
AUTHORITY_PUBLIC_SOURCE_CONTEXT_RADIUS = 2
AUTHORITY_STRUCTURAL_CONTEXT_RADIUS = 24
AUTHORITY_TOKEN_WARNING_BOUNDARIES = {
    "README.md": {
        "owner_class": "sibling_cold_entry_owned",
        "protection_status": "protected_sibling",
        "reentry_condition": (
            "Re-enter only after README/cold-entry ownership is released; update public entry copy to use "
            "explicit fail-closed or anti-claim wording rather than weak negation alone."
        ),
        "next_safe_fix": (
            "Strengthen the public entry sentence with adjacent fail-closed or anti-claim language, then rebuild "
            "release-root compiler artifacts."
        ),
    },
    "RELEASE_SCOPE.md": {
        "owner_class": "sibling_cold_entry_owned",
        "protection_status": "protected_sibling",
        "reentry_condition": (
            "Re-enter only after RELEASE_SCOPE/cold-entry ownership is released; preserve scope boundaries "
            "while strengthening authority copy."
        ),
        "next_safe_fix": (
            "Strengthen release-scope authority wording with explicit fail-closed gate language, then rebuild "
            "release-root compiler artifacts."
        ),
    },
}
AUTHORITY_TOKEN_ROW_ANTI_CLAIMS = [
    "local diagnostics only",
    "not public release approval",
    "not hosted CI proof",
    "not publication permission",
    "not private-root equivalence",
    "not certification",
]
PUBLIC_CLAIMS_STILL_BLOCKED = [
    {
        "claim_id": "public_release_approval",
        "claim": "public release approval",
        "authority_class": "publication_permission",
        "gate_ref": "release/publication_gate.json",
        "status": "blocked_without_publication_gate",
        "reason": "Local release-root diagnostics cannot approve a public release.",
        "anti_claims": ["local validation is public release approval"],
    },
    {
        "claim_id": "hosted_public_readiness",
        "claim": "hosted public readiness",
        "authority_class": "hosted_public_evidence",
        "gate_ref": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json",
        "status": "blocked_without_hosted_public_gate",
        "reason": "Local and clone-shaped receipts do not prove hosted public availability.",
        "anti_claims": ["local receipts prove hosted public readiness"],
    },
    {
        "claim_id": "publication_permission",
        "claim": "publication permission",
        "authority_class": "publication_permission",
        "gate_ref": "release/publication_gate.json",
        "status": "blocked_without_operator_release_and_publication_gates",
        "reason": "Publication requires explicit gate evidence and operator release posture.",
        "anti_claims": ["passing diagnostics grants publication permission"],
    },
    {
        "claim_id": "private_root_equivalence",
        "claim": "private-root equivalence",
        "authority_class": "private_root_evidence",
        "gate_ref": ROOT_CONTRACT_PATH,
        "status": "blocked_always_for_public_release_microcosm",
        "reason": "The release microcosm is a public-safe projection and must not claim private-root equivalence.",
        "anti_claims": ["release microcosm is private-root equivalence"],
    },
    {
        "claim_id": "security_or_standards_certification",
        "claim": "security or standards certification",
        "authority_class": "certification_claim",
        "gate_ref": ROOT_CONTRACT_PATH,
        "status": "blocked_without_external_certification_authority",
        "reason": "std_python and authority-token diagnostics are local standards checks, not certification.",
        "anti_claims": ["standards diagnostics are certification"],
    },
    {
        "claim_id": "theorem_proof",
        "claim": "theorem proof",
        "authority_class": "theorem_claim",
        "gate_ref": ROOT_CONTRACT_PATH,
        "status": "blocked_without_theorem_proof_surface",
        "reason": "Release-root compiler receipts do not prove theorem correctness.",
        "anti_claims": ["release-root diagnostics prove theorem results"],
    },
    {
        "claim_id": "benchmark_win",
        "claim": "benchmark win",
        "authority_class": "benchmark_claim",
        "gate_ref": "microcosms/lab_evolve_failure_replay/replay_graph.json",
        "status": "blocked_without_external_benchmark_evidence",
        "reason": "Failure replay fixtures do not prove external benchmark superiority.",
        "anti_claims": ["fixture replay proves a benchmark win"],
    },
    {
        "claim_id": "thiel_or_recipient_readiness",
        "claim": "Thiel or recipient readiness",
        "authority_class": "publication_permission",
        "gate_ref": "microcosms/thiel_evidence_packet_gate/evidence_packet.json",
        "status": "blocked_without_recipient_review_and_publication_gates",
        "reason": "Application or recipient packet surfaces remain gated and do not authorize public send.",
        "anti_claims": ["local evidence packet approves recipient or Thiel submission"],
    },
]

PROOF_TAIL_REFRESH_GROUPS = [
    {
        "group_id": "release_root_compiler",
        "owner_command": BUILDER_COMMAND,
        "artifact_refs": [BRANCH_GRAPH_PATH, ROOT_CONTRACT_PATH, STD_PYTHON_REPORT_PATH, RECEIPT_PATH],
        "validator_refs": ["validator.release_root_compiler"],
        "public_boundary": "Local release-root compiler proof only; not hosted public proof or publication permission.",
        "repair_boundary": "Refresh through release_root_compiler source and this builder command, then run validate --root .",
        "anti_claims": ["release-root compiler receipt approves public release"],
    },
    {
        "group_id": "artifact_manifest",
        "owner_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-artifact-manifest --root . --write-receipt",
        "artifact_refs": ["state/artifact_manifest.json", "receipts/artifact_manifest.json"],
        "validator_refs": ["validator.artifact_manifest"],
        "public_boundary": "Generated manifest row coverage only; not source authority or rights approval.",
        "repair_boundary": "Refresh through artifact_manifest source or CLI ownership, then run validate --root .",
        "anti_claims": ["artifact manifest row coverage grants publication permission"],
    },
    {
        "group_id": "release_candidate_portfolio",
        "owner_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-release-candidates --root . --write-receipt",
        "artifact_refs": ["state/release_candidate_portfolio.json", "receipts/release_candidate_portfolio.json"],
        "validator_refs": ["validator.release_candidate_portfolio"],
        "public_boundary": "Candidate scoring and ranking only; not release approval or external benchmark proof.",
        "repair_boundary": "Refresh through release_candidates source or CLI ownership, then run validate --root .",
        "anti_claims": ["candidate portfolio ranking is public release approval"],
    },
    {
        "group_id": "site_projection_manifest",
        "owner_command": (
            "PYTHONPATH=src python3 -m idea_microcosm.cli build-site-projection "
            "--root . --mode sandbox_preview --write-receipt"
        ),
        "artifact_refs": [
            "state/site_projection_manifest.json",
            "site/sandbox/site_projection_manifest.json",
            "site/sandbox/site_projection_bundle.json",
            "site/sandbox/site_projection_receipt.json",
            "receipts/site_projection_manifest_latest.json",
        ],
        "validator_refs": ["validator.site_projection_manifest"],
        "public_boundary": "Sandbox projection and local site receipts only; not hosted public availability.",
        "repair_boundary": "Refresh through site_projection source or CLI ownership, then run validate --root .",
        "anti_claims": ["sandbox site projection proves hosted public readiness"],
    },
    {
        "group_id": "public_release_package_manifest_gate",
        "owner_command": (
            "PYTHONPATH=src python3 -m idea_microcosm.cli "
            "build-public-release-package-manifest-gate-specimen --root . --write-receipt"
        ),
        "artifact_refs": [
            "microcosms/public_release_package_manifest_gate/package_manifest.json",
            "microcosms/public_release_package_manifest_gate/receipt.json",
            "microcosms/public_release_package_manifest_gate/package_promotion_gate.json",
            "microcosms/public_release_package_manifest_gate/artifact_digest_requirement_bridge.json",
            "microcosms/public_release_package_manifest_gate/recipient_packet_manifest_bridge.json",
            "microcosms/public_release_package_manifest_gate/release_authority_handshake.json",
        ],
        "validator_refs": ["validator.public_release_package_manifest_gate_specimen"],
        "public_boundary": "Fail-closed package gate evidence only; not operator release permission.",
        "repair_boundary": "Refresh through package gate source or CLI ownership, then run validate --root .",
        "anti_claims": ["package manifest gate alone grants publication permission"],
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_ref(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        try:
            return path.resolve().relative_to(root.parent.resolve()).as_posix()
        except ValueError:
            return path.as_posix()


def _resolve_std_python_standard(root: Path) -> dict[str, Any]:
    local_path = root / STD_PYTHON_STANDARD_PATH
    parent_path = root.parent / STD_PYTHON_STANDARD_PATH
    if local_path.exists():
        selected = local_path
        mode = "microcosm_local"
    else:
        selected = parent_path
        mode = "parent_repo_fallback"
    return {
        "mode": mode,
        "path": _display_ref(selected, root),
        "local_first": True,
        "fallback_path": _display_ref(parent_path, root),
        "exists": selected.exists(),
        "projection_not_authority": True,
        "authority_boundary": "Standard resolution selects a diagnostics contract only; source and validators remain authoritative.",
    }


def _ref_exists(root: Path, ref: str) -> bool:
    if not ref:
        return False
    if ref in {BRANCH_GRAPH_PATH, ROOT_CONTRACT_PATH, STD_PYTHON_REPORT_PATH, RECEIPT_PATH}:
        return True
    if ref.startswith(("standard.", "validator.", "axiom_", "pri_", "capability.")):
        return True
    if ref.startswith("codex/"):
        return (root / ref).exists() or (root.parent / ref).exists()
    clean = ref.split("::", 1)[0]
    if ":" in clean and not clean.startswith("/"):
        return True
    if clean.endswith("/"):
        return (root / clean).is_dir()
    if "*" in clean:
        return bool(list(root.glob(clean)))
    return (root / clean).exists()


def _generated_by(source_owner: str, source_refs: list[str]) -> dict[str, Any]:
    return {
        "source_owner": source_owner,
        "builder_command": BUILDER_COMMAND,
        "source_refs": source_refs,
        "projection_not_authority": True,
    }


def _branch(
    branch_id: str,
    *,
    microcosm_id: str,
    role: str,
    branch_type: str,
    layman_summary: str,
    technical_summary: str,
    what_it_shows: str,
    what_to_run: str,
    expected_output: str,
    what_to_inspect: list[str],
    evidence_refs: list[str],
    standards_refs: list[str],
    axiom_refs: list[str],
    principle_refs: list[str],
    authority_class: str,
    promotion_rules: list[str],
    anti_claims: list[str],
    next_branch: str,
    next_gap: str,
) -> dict[str, Any]:
    return {
        "branch_id": branch_id,
        "microcosm_id": microcosm_id,
        "role": role,
        "branch_type": branch_type,
        "layman_summary": layman_summary,
        "technical_summary": technical_summary,
        "what_it_shows": what_it_shows,
        "what_to_run": what_to_run,
        "expected_output": expected_output,
        "what_to_inspect": what_to_inspect,
        "evidence_refs": evidence_refs,
        "standards_refs": standards_refs,
        "axiom_refs": axiom_refs,
        "principle_refs": principle_refs,
        "authority_class": authority_class,
        "authority_boundary": "Local release-root fixture evidence only; public, hosted, publication, and private-root authority stay separate.",
        "promotion_rules": promotion_rules,
        "anti_claims": anti_claims,
        "next_branch": next_branch,
        "next_gap": next_gap,
    }


def _branch_rows() -> list[dict[str, Any]]:
    shared_anti_claims = [
        "local receipt proves hosted public availability",
        "local receipt approves publication",
        "release fixture is private-root equivalence",
    ]
    return [
        _branch(
            "macrocosm_contribution_assay",
            microcosm_id="macrocosm_contribution_assay",
            role="core",
            branch_type="constitution",
            layman_summary="Names the release root contribution instead of presenting a pile of demos.",
            technical_summary="Selects self_indexing_cognitive_substrate as the composed contribution and binds it to evidence requirements.",
            what_it_shows="The contribution is the composed self-indexing substrate, not a single component.",
            what_to_run=BUILDER_COMMAND,
            expected_output="release_branch_graph.root_summary.selected_contribution == self_indexing_cognitive_substrate",
            what_to_inspect=["microcosms/specimen_suite/macrocosm_contribution_assay.json"],
            evidence_refs=["microcosms/specimen_suite/macrocosm_contribution_assay.json"],
            standards_refs=["standard.principle_enforcement", "standard.axiom_kernel"],
            axiom_refs=["axiom_candidate_standards_shared_grammar"],
            principle_refs=["pri_148", "pri_001"],
            authority_class="local_fixture_evidence",
            promotion_rules=["Requires claim/evidence/anti-claim rows before public copy can cite it."],
            anti_claims=shared_anti_claims,
            next_branch="release_microcosm_ontology",
            next_gap="github_export_scope_manifest_hardening",
        ),
        _branch(
            "release_microcosm_ontology",
            microcosm_id="release_microcosm_ontology",
            role="core",
            branch_type="constitution",
            layman_summary="Explains which surfaces are core, support, exemplar, or boundary.",
            technical_summary="Classifies release artifacts into role-bearing microcosm rows with evidence and next-gap summaries.",
            what_it_shows="Release identity comes from the role graph, not directory shape.",
            what_to_run=BUILDER_COMMAND,
            expected_output="release_branch_graph.status.trunk_count >= 8",
            what_to_inspect=["microcosms/specimen_suite/release_microcosm_ontology.json"],
            evidence_refs=["microcosms/specimen_suite/release_microcosm_ontology.json"],
            standards_refs=["standard.artifact_manifest", "standard.navigation"],
            axiom_refs=["axiom_candidate_meaning_is_relational"],
            principle_refs=["pri_049", "pri_148"],
            authority_class="local_fixture_evidence",
            promotion_rules=["Core role changes require an ontology row and a fresh compiler receipt."],
            anti_claims=shared_anti_claims,
            next_branch="release_branch_graph",
            next_gap="branch route must remain executable, not only descriptive",
        ),
        _branch(
            "release_branch_graph",
            microcosm_id="release_root_branch_graph_compiler",
            role="core",
            branch_type="cold_entry",
            layman_summary="Turns the release root into root, trunks, branches, commands, evidence, and next gaps.",
            technical_summary="Compiles existing microcosm boards into a standards-governed branch graph with entry tracks and mission threads.",
            what_it_shows="A cold human or agent can choose a branch and know what to run, inspect, and not infer.",
            what_to_run=BUILDER_COMMAND,
            expected_output="release_branch_graph.status.branch_count >= 18 and missing_ref_count == 0",
            what_to_inspect=[BRANCH_GRAPH_PATH, RECEIPT_PATH],
            evidence_refs=[BRANCH_GRAPH_PATH, RECEIPT_PATH, "microcosms/specimen_suite/quality_delta_board.json"],
            standards_refs=["standard.navigation", "standard.artifact_manifest", "codex/standards/std_python.py"],
            axiom_refs=["axiom_candidate_standards_shared_grammar", "axiom_candidate_meaning_is_relational"],
            principle_refs=["pri_049", "pri_148"],
            authority_class="generated_navigation_projection",
            promotion_rules=["Projection may guide navigation only when generated_by.projection_not_authority is true."],
            anti_claims=[
                "branch graph is source authority",
                "branch graph approves public release",
                "branch graph replaces source artifacts",
            ],
            next_branch="leaf_entry_contract",
            next_gap="consume leaf entry contract before treating any leaf as independently cloneable",
        ),
        _branch(
            "leaf_entry_contract",
            microcosm_id="leaf_entry_contract",
            role="core",
            branch_type="cold_entry",
            layman_summary="States which leaves are root-backed today and what a standalone leaf would require.",
            technical_summary="Binds every public leaf to an organ, entry track, evidence surface, receipt/probe, entry-track doctrine profile, standards subset, std_python posture, clone posture, and anti-claim set.",
            what_it_shows="A cold reviewer can tell whether to clone the root, inspect a leaf directly, or wait for a wrapper projection.",
            what_to_run=BUILDER_COMMAND,
            expected_output="leaf_entry_contract.summary.leaf_count >= 28, entry_track_doctrine_profiles >= 9, and standalone_leaf_supported_count == 0",
            what_to_inspect=["microcosms/leaf_entry_contract.json", "standards/leaf_entry_contract.json"],
            evidence_refs=[
                "microcosms/leaf_entry_contract.json",
                "standards/leaf_entry_contract.json",
                "paper_modules/leaf_entry_contract.md",
                "paper_modules/leaf_doctrine_profile.md",
                "skills/leaf_porting.md",
            ],
            standards_refs=["standard.leaf_entry_contract", "standard.navigation", "codex/standards/std_python.py"],
            axiom_refs=["axiom_candidate_standards_shared_grammar"],
            principle_refs=["pri_049", "pri_140", "pri_148"],
            authority_class="local_navigation_contract",
            promotion_rules=["Standalone leaf claims require a wrapper projection and fresh validation receipt."],
            anti_claims=[
                "leaf folder is automatically standalone",
                "leaf receipt grants publication permission",
                "paper-module lineage publishes private doctrine",
            ],
            next_branch="summary_ladders",
            next_gap="project every leaf into one-sentence through deep human and AI-native summaries before root-contract drilldown",
        ),
        _branch(
            "summary_ladders",
            microcosm_id="summary_ladders",
            role="core",
            branch_type="cold_entry",
            layman_summary="Gives every leaf a band flag plus one-sentence, concise, medium, and deep descriptions.",
            technical_summary="Projects the leaf entry contract into human-read and AI-native summary layers with proof refs, drilldown order, claim boundaries, and anti-claims.",
            what_it_shows="A cold reviewer can choose the right leaf and depth before opening folders or source.",
            what_to_run="PYTHONPATH=src python3 -m idea_microcosm.cli build-summary-ladders-specimen --root . --write-receipt",
            expected_output="summary_ladders.summary.leaf_count == leaf_entry_contract.summary.leaf_count and length_level_count == 4",
            what_to_inspect=["microcosms/summary_ladders/summary_ladders.json", "microcosms/summary_ladders/README.md"],
            evidence_refs=[
                "microcosms/summary_ladders/summary_ladders.json",
                "microcosms/summary_ladders/README.md",
                "microcosms/summary_ladders/receipt.json",
                "standards/summary_ladder.json",
                "paper_modules/summary_ladder_projection.md",
                "skills/summary_ladder_porting.md",
            ],
            standards_refs=["standard.summary_ladder", "standard.navigation", "standard.leaf_entry_contract"],
            axiom_refs=["axiom_candidate_context_discretionary_capital", "axiom_candidate_meaning_is_relational"],
            principle_refs=["pri_049", "pri_088", "pri_111", "pri_142"],
            authority_class="generated_navigation_projection",
            promotion_rules=["Summary text may route to evidence only; it cannot become source, proof, hosted-public, or publication authority."],
            anti_claims=[
                "one-sentence summary is evidence",
                "summary ladder grants publication permission",
                "AI-native route token proves private-root equivalence",
            ],
            next_branch="release_root_contract",
            next_gap="keep root contract consuming summary layers without letting prose strengthen claims",
        ),
        _branch(
            "release_root_contract",
            microcosm_id="release_root_contract_compiler",
            role="core",
            branch_type="authority",
            layman_summary="States the rules that stop local proof from becoming public authority by accident.",
            technical_summary="Compiles claim, projection, authority, public-boundary, standards, and work-metabolism rules into one root contract.",
            what_it_shows="Authority classes remain separate even when all local fixture checks pass.",
            what_to_run=BUILDER_COMMAND,
            expected_output="release_root_contract.status.authority_collapse_count == 0",
            what_to_inspect=[ROOT_CONTRACT_PATH],
            evidence_refs=[ROOT_CONTRACT_PATH, "microcosms/public_release_package_manifest_gate/release_authority_handshake.json"],
            standards_refs=["standard.release_gate", "standard.receipt", "standard.principle_enforcement"],
            axiom_refs=["axiom_candidate_standards_shared_grammar"],
            principle_refs=["pri_001", "pri_148"],
            authority_class="local_contract_projection",
            promotion_rules=["Every release claim must route to evidence or an explicit fail-closed boundary."],
            anti_claims=ROOT_ANTI_CLAIMS,
            next_branch="std_python_compliance",
            next_gap="consume validator.release_root_compiler in package and cold-start routes without promoting local validation to release authority",
        ),
        _branch(
            "std_python_compliance",
            microcosm_id="std_python_compliance_report",
            role="core",
            branch_type="standards",
            layman_summary="Makes each release Python file diagnosable against the local Python standard.",
            technical_summary="Scans release Python files for std_python tags, type hints, CLI/test posture, dependencies, and public-safe boundaries.",
            what_it_shows="Standards are executable diagnostics rather than advice.",
            what_to_run=BUILDER_COMMAND,
            expected_output="std_python_compliance_report.summary.scanned_count > 0 and no unclassified Python files",
            what_to_inspect=[STD_PYTHON_REPORT_PATH, "codex/standards/std_python.py"],
            evidence_refs=[STD_PYTHON_REPORT_PATH, "codex/standards/std_python.py"],
            standards_refs=["codex/standards/std_python.py", "codex/standards/std_python_compliance_coverage.json"],
            axiom_refs=["axiom_candidate_standards_shared_grammar"],
            principle_refs=["pri_148"],
            authority_class="local_diagnostic_report",
            promotion_rules=["Warnings route to next_fix rows; they do not certify repo-wide compliance."],
            anti_claims=[
                "std_python diagnostics are repo-wide compliance",
                "std_python diagnostics are security certification",
                "warnings are public release blockers without an owning gate",
            ],
            next_branch="executable_grammar_metabolism",
            next_gap="reduce direct-test warnings for release source files with focused tests",
        ),
        _branch(
            "work_metabolism_bridge",
            microcosm_id="concurrency_transaction_mission_control_microcosm",
            role="core",
            branch_type="metabolism",
            layman_summary="Shows how a request becomes claimed work, mutation, proof, closeout, and residuals.",
            technical_summary="Binds Task Ledger projection, mission board, authority boundaries, transaction steps, and residual rows.",
            what_it_shows="Work is tracked through durable metabolism, not only chat or status counts.",
            what_to_run="PYTHONPATH=src python3 -m idea_microcosm.cli build-concurrency-mission-control-specimen --root . --write-receipt",
            expected_output="work_metabolism_bridge.summary.authority_collapse_count == 0",
            what_to_inspect=["microcosms/concurrency_mission_control/work_metabolism_bridge.json"],
            evidence_refs=["microcosms/concurrency_mission_control/work_metabolism_bridge.json"],
            standards_refs=["standard.work_packet", "standard.receipt"],
            axiom_refs=["axiom_candidate_common_sense_up_propagates"],
            principle_refs=["pri_001", "pri_139"],
            authority_class="local_fixture_evidence",
            promotion_rules=["Work closeout requires proof or residual capture before public copy cites it."],
            anti_claims=shared_anti_claims,
            next_branch="task_ledger_cap_economy",
            next_gap="make active work ranking public-safe without exposing private ledger state",
        ),
        _branch(
            "task_ledger_cap_economy",
            microcosm_id="task_ledger_cap_economy_microcosm",
            role="core",
            branch_type="metabolism",
            layman_summary="Shows intent as typed events and projections instead of a loose todo list.",
            technical_summary="Demonstrates event-sourced CAP projection with receipt-backed status and next actions.",
            what_it_shows="Intent remains durable under system drift.",
            what_to_run="PYTHONPATH=src python3 -m idea_microcosm.cli build-task-ledger-specimen --root . --write-receipt",
            expected_output="projection summary is ok and receipt exists",
            what_to_inspect=["microcosms/task_ledger_cap_economy/projection.json", "microcosms/task_ledger_cap_economy/receipt.json"],
            evidence_refs=["microcosms/task_ledger_cap_economy/projection.json", "microcosms/task_ledger_cap_economy/receipt.json"],
            standards_refs=["standard.work_packet", "standard.receipt"],
            axiom_refs=["axiom_candidate_common_sense_up_propagates"],
            principle_refs=["pri_140"],
            authority_class="local_fixture_evidence",
            promotion_rules=["Projection rows browse events; source authority remains event log plus receipts."],
            anti_claims=shared_anti_claims,
            next_branch="status_preserving_control_plane",
            next_gap="map CAP ranking buckets into branch graph entry tracks",
        ),
        _branch(
            "executable_grammar_metabolism",
            microcosm_id="executable_grammar_metabolism_microcosm",
            role="core",
            branch_type="grammar",
            layman_summary="Shows standards accepting, blocking, and routing repairs.",
            technical_summary="Runs synthetic candidate mutations through grammar rules and provider replay repair rows.",
            what_it_shows="A standard can be a runtime gate with repair actions.",
            what_to_run="PYTHONPATH=src python3 -m idea_microcosm.cli build-executable-grammar-metabolism-specimen --root . --write-receipt",
            expected_output="grammar_board.summary.publication_permission_count == 0",
            what_to_inspect=["microcosms/executable_grammar_metabolism/grammar_board.json"],
            evidence_refs=["microcosms/executable_grammar_metabolism/grammar_board.json", "microcosms/executable_grammar_metabolism/receipt.json"],
            standards_refs=["standard.release_candidate_portfolio", "standard.receipt"],
            axiom_refs=["axiom_candidate_evolution_proves_in_microcosm"],
            principle_refs=["pri_148"],
            authority_class="local_fixture_evidence",
            promotion_rules=["New grammar rules require case coverage and fail-closed repair routes."],
            anti_claims=shared_anti_claims,
            next_branch="release_standards_axiom_gate",
            next_gap="turn grammar loops into reusable report rows across branch graph trunks",
        ),
        _branch(
            "release_standards_axiom_gate",
            microcosm_id="release_standards_axiom_gate_microcosm",
            role="core",
            branch_type="standards",
            layman_summary="Prevents vague candidates from guiding the release root.",
            technical_summary="Checks candidate records, validator refs, principle matrix, teleology, and axiom kernel status.",
            what_it_shows="Standards, axioms, and principles have executable coverage.",
            what_to_run="PYTHONPATH=src python3 -m idea_microcosm.cli build-release-standards-gate-specimen --root . --write-receipt",
            expected_output="gate.status == ok and candidate_summary exists",
            what_to_inspect=["microcosms/release_standards_axiom_gate/gate.json"],
            evidence_refs=["microcosms/release_standards_axiom_gate/gate.json", "state/axiom_kernel.json", "state/principle_enforcement_matrix.json"],
            standards_refs=["standard.principle_enforcement", "standard.axiom_kernel", "standard.teleology_map"],
            axiom_refs=["axiom_candidate_standards_shared_grammar"],
            principle_refs=["pri_148", "pri_149"],
            authority_class="local_fixture_evidence",
            promotion_rules=["Candidate rows must keep source refs, standards refs, anti-claims, receipts, and next action."],
            anti_claims=shared_anti_claims,
            next_branch="std_python_compliance",
            next_gap="add release-local examples for every high-pressure standard",
        ),
        _branch(
            "status_preserving_control_plane",
            microcosm_id="status_preserving_control_plane_microcosm",
            role="core",
            branch_type="authority",
            layman_summary="Shows that labels, receipts, projections, and truth authority are not interchangeable.",
            technical_summary="Runs adversarial status-collapse cases through a policy judgment and control-plane board.",
            what_it_shows="Status transitions stay governed by evidence and downgrade rules.",
            what_to_run="PYTHONPATH=src python3 -m idea_microcosm.cli build-status-preserving-control-plane-specimen --root . --write-receipt",
            expected_output="control_plane_board has illegal_allowed_count == 0",
            what_to_inspect=["microcosms/status_preserving_control_plane/control_plane_board.json"],
            evidence_refs=["microcosms/status_preserving_control_plane/control_plane_board.json", "microcosms/status_preserving_control_plane/receipt.json"],
            standards_refs=["standard.release_gate", "standard.receipt"],
            axiom_refs=["axiom_candidate_standards_shared_grammar"],
            principle_refs=["pri_001"],
            authority_class="local_fixture_evidence",
            promotion_rules=["External copy must cite the status policy boundary and fail-closed gate."],
            anti_claims=shared_anti_claims,
            next_branch="public_release_package_manifest_gate",
            next_gap="keep website cards downstream of status-preserving proof",
        ),
        _branch(
            "public_release_package_manifest_gate",
            microcosm_id="public_release_package_manifest_gate_microcosm",
            role="boundary",
            branch_type="boundary",
            layman_summary="Stops package rows from promoting themselves into release authority.",
            technical_summary="Composes package rows with claim refs, standards refs, evidence receipts, anti-claims, and fail-closed public boundaries.",
            what_it_shows="Authority never collapses from local package evidence into public release permission.",
            what_to_run="PYTHONPATH=src python3 -m idea_microcosm.cli build-public-release-package-manifest-gate-specimen --root . --write-receipt",
            expected_output="release_authority_handshake.summary.authority_collapse_count == 0",
            what_to_inspect=["microcosms/public_release_package_manifest_gate/release_authority_handshake.json"],
            evidence_refs=["microcosms/public_release_package_manifest_gate/release_authority_handshake.json", "microcosms/public_release_package_manifest_gate/package_manifest.json"],
            standards_refs=["standard.release_gate", "standard.receipt"],
            axiom_refs=["axiom_candidate_standards_shared_grammar"],
            principle_refs=["pri_001", "pri_148"],
            authority_class="local_boundary_gate",
            promotion_rules=["Hosted, rights, citation, disclosure, and publication gates must each pass before promotion."],
            anti_claims=ROOT_ANTI_CLAIMS,
            next_branch="hosted_public_ci_workflow_gate",
            next_gap="hosted public CI remains fail-closed until external proof exists",
        ),
        _branch(
            "hosted_public_ci_workflow_gate",
            microcosm_id="hosted_public_ci_workflow_gate_microcosm",
            role="boundary",
            branch_type="boundary",
            layman_summary="Separates local clone checks from hosted public CI proof.",
            technical_summary="Keeps hosted-public status as its own fail-closed gate rather than inheriting local receipts.",
            what_it_shows="Local proof cannot grant hosted public status.",
            what_to_run="PYTHONPATH=src python3 -m idea_microcosm.cli build-hosted-public-ci-workflow-gate-specimen --root . --write-receipt",
            expected_output="workflow_gate hosted_public_status remains fail_closed_not_hosted_public",
            what_to_inspect=["microcosms/hosted_public_ci_workflow_gate/workflow_gate.json"],
            evidence_refs=["microcosms/hosted_public_ci_workflow_gate/workflow_gate.json", "microcosms/hosted_public_ci_workflow_gate/receipt.json"],
            standards_refs=["standard.release_gate", "standard.receipt"],
            axiom_refs=["axiom_candidate_standards_shared_grammar"],
            principle_refs=["pri_001"],
            authority_class="fail_closed_boundary",
            promotion_rules=["Hosted public claims require hosted workflow evidence, not local fixture pass."],
            anti_claims=ROOT_ANTI_CLAIMS,
            next_branch="license_citation_disclosure_gate",
            next_gap="positive hosted-public proof remains blocked",
        ),
        _branch(
            "license_citation_disclosure_gate",
            microcosm_id="license_citation_disclosure_gate_microcosm",
            role="boundary",
            branch_type="boundary",
            layman_summary="Keeps rights, citation, and disclosure separate from technical proof.",
            technical_summary="Compiles clearance status into a release gate with explicit omissions.",
            what_it_shows="Legal and disclosure readiness are not implied by passing tests.",
            what_to_run="PYTHONPATH=src python3 -m idea_microcosm.cli build-license-citation-disclosure-gate-specimen --root . --write-receipt",
            expected_output="clearance gate stays fail-closed unless rights and disclosure checks are current",
            what_to_inspect=["microcosms/license_citation_disclosure_gate/clearance_gate.json"],
            evidence_refs=["microcosms/license_citation_disclosure_gate/clearance_gate.json", "microcosms/license_citation_disclosure_gate/receipt.json"],
            standards_refs=["standard.release_gate", "standard.receipt"],
            axiom_refs=["axiom_candidate_standards_shared_grammar"],
            principle_refs=["pri_001"],
            authority_class="fail_closed_boundary",
            promotion_rules=["Publication requires explicit rights, citation, and disclosure clearance."],
            anti_claims=ROOT_ANTI_CLAIMS,
            next_branch="recipient_review_route_gate",
            next_gap="review routing remains private until operator release decision",
        ),
        _branch(
            "recipient_review_route_gate",
            microcosm_id="recipient_review_route_gate_microcosm",
            role="boundary",
            branch_type="boundary",
            layman_summary="Separates reviewer routing from public send permission.",
            technical_summary="Keeps recipient review status behind route gates and evidence packet boundaries.",
            what_it_shows="A recipient packet is not an authorization to publish.",
            what_to_run="PYTHONPATH=src python3 -m idea_microcosm.cli build-recipient-review-route-gate-specimen --root . --write-receipt",
            expected_output="route gate preserves review boundary",
            what_to_inspect=["microcosms/recipient_review_route_gate/route_gate.json"],
            evidence_refs=["microcosms/recipient_review_route_gate/route_gate.json", "microcosms/recipient_review_route_gate/receipt.json"],
            standards_refs=["standard.release_gate", "standard.receipt"],
            axiom_refs=["axiom_candidate_standards_shared_grammar"],
            principle_refs=["pri_001"],
            authority_class="fail_closed_boundary",
            promotion_rules=["Recipient routing requires explicit operator-controlled review posture."],
            anti_claims=ROOT_ANTI_CLAIMS,
            next_branch="apex_reviewer_board",
            next_gap="review copy must keep evidence and anti-claims adjacent",
        ),
        _branch(
            "apex_reviewer_board",
            microcosm_id="apex_reviewer_board",
            role="core",
            branch_type="evaluation",
            layman_summary="Shows the strongest careful inferences a reviewer can draw.",
            technical_summary="Ranks apex paths by evidence density, authority boundaries, public safety, and anti-claim clarity.",
            what_it_shows="Reviewer inference is bounded by evidence and negative claims.",
            what_to_run="PYTHONPATH=src python3 -m idea_microcosm.cli run-specimen-suite-probe --root . --write-receipt",
            expected_output="apex board status remains ok",
            what_to_inspect=["microcosms/specimen_suite/apex_reviewer_board.json"],
            evidence_refs=["microcosms/specimen_suite/apex_reviewer_board.json", "microcosms/specimen_suite/claim_inference_map.json"],
            standards_refs=["standard.receipt", "standard.release_gate"],
            axiom_refs=["axiom_candidate_standards_shared_grammar"],
            principle_refs=["pri_001"],
            authority_class="evaluator_projection",
            promotion_rules=["Reviewer board informs inference only; claim authority remains with source evidence and gates."],
            anti_claims=shared_anti_claims,
            next_branch="quality_delta_board",
            next_gap="keep evaluator outputs feeding patches, not public claims",
        ),
        _branch(
            "quality_delta_board",
            microcosm_id="quality_delta_board",
            role="core",
            branch_type="evaluation",
            layman_summary="Scores what each microcosm contributes and what the next patch lane should be.",
            technical_summary="Dogfoods prior improvements, marks applied patches, and advances the next open gap.",
            what_it_shows="Evaluator output selects repair lanes instead of becoming release authority.",
            what_to_run="PYTHONPATH=src python3 -m idea_microcosm.cli run-specimen-suite-probe --root . --write-receipt",
            expected_output="dogfood_loop_status == previous_gap_observed_and_advanced",
            what_to_inspect=["microcosms/specimen_suite/quality_delta_board.json"],
            evidence_refs=["microcosms/specimen_suite/quality_delta_board.json", "microcosms/specimen_suite/dogfood_control_loop_receipt.json"],
            standards_refs=["standard.receipt", "standard.work_packet"],
            axiom_refs=["axiom_candidate_common_sense_up_propagates"],
            principle_refs=["pri_139"],
            authority_class="evaluator_projection",
            promotion_rules=["Quality rows must point to next source owner before work starts."],
            anti_claims=shared_anti_claims,
            next_branch="dogfood_control_loop",
            next_gap="hosted public boundary remains next open public-boundary gap",
        ),
        _branch(
            "dogfood_control_loop",
            microcosm_id="dogfood_control_loop",
            role="core",
            branch_type="evaluation",
            layman_summary="Shows the system observing its previous patch and selecting the next gap.",
            technical_summary="Records applied patch observation and gap advancement in a receipt-shaped loop.",
            what_it_shows="The release root improves by consuming its own evaluator output.",
            what_to_run="PYTHONPATH=src python3 -m idea_microcosm.cli run-specimen-suite-probe --root . --write-receipt",
            expected_output="dogfood receipt records applied patch and next patch lane",
            what_to_inspect=["microcosms/specimen_suite/dogfood_control_loop_receipt.json"],
            evidence_refs=["microcosms/specimen_suite/dogfood_control_loop_receipt.json"],
            standards_refs=["standard.receipt", "standard.work_packet"],
            axiom_refs=["axiom_candidate_common_sense_up_propagates"],
            principle_refs=["pri_139"],
            authority_class="local_fixture_evidence",
            promotion_rules=["Dogfood receipts guide next local work only after proof refs are present."],
            anti_claims=shared_anti_claims,
            next_branch="release_branch_graph",
            next_gap="consume branch graph in the dogfood loop on the next suite probe patch",
        ),
        _branch(
            "living_substrate_witness",
            microcosm_id="living_substrate_witness",
            role="exemplar",
            branch_type="witness",
            layman_summary="Shows a bounded live capability witness without making it the release identity.",
            technical_summary="Carries the formal-math/living-work exemplar as capability evidence with anti-claims.",
            what_it_shows="Capability examples are witnesses, not the macrocosm contribution.",
            what_to_run="PYTHONPATH=src python3 -m idea_microcosm.cli run-specimen-suite-probe --root . --write-receipt",
            expected_output="living substrate witness remains bounded",
            what_to_inspect=["microcosms/specimen_suite/living_substrate_witness.json"],
            evidence_refs=["microcosms/specimen_suite/living_substrate_witness.json"],
            standards_refs=["standard.receipt"],
            axiom_refs=["axiom_candidate_evolution_proves_in_microcosm"],
            principle_refs=["pri_139"],
            authority_class="bounded_capability_witness",
            promotion_rules=["Witness copy must preserve bounded scope and anti-claims."],
            anti_claims=["witness is release identity", *shared_anti_claims],
            next_branch="macrocosm_contribution_assay",
            next_gap="keep witness linked but demoted from contribution identity",
        ),
    ]


def _trunks() -> list[dict[str, Any]]:
    return [
        {
            "trunk_id": "constitution_and_telos",
            "title": "Constitution And Telos",
            "layman_summary": "What this release root is trying to prove and what it refuses to claim.",
            "technical_summary": "Contribution, ontology, branch graph, root contract, standards, axioms, and principles.",
            "branch_ids": [
                "macrocosm_contribution_assay",
                "release_microcosm_ontology",
                "release_branch_graph",
                "leaf_entry_contract",
                "summary_ladders",
                "release_root_contract",
            ],
            "first_command": BUILDER_COMMAND,
            "expected_output": "root_summary and root contract are generated with projection_not_authority true",
            "first_evidence_ref": BRANCH_GRAPH_PATH,
            "standard_refs": ["standard.principle_enforcement", "standard.axiom_kernel"],
            "authority_boundary": "Constitution rows guide local interpretation only.",
            "anti_claims": ROOT_ANTI_CLAIMS,
        },
        {
            "trunk_id": "cold_entry_and_navigation",
            "title": "Cold Entry And Navigation",
            "layman_summary": "Where a cold human or agent starts.",
            "technical_summary": "Cold-entry atlas is sibling-owned; this compiler consumes it as evidence and adds branch routes.",
            "branch_ids": [
                "release_branch_graph",
                "leaf_entry_contract",
                "summary_ladders",
                "macrocosm_contribution_assay",
                "release_microcosm_ontology",
            ],
            "first_command": BUILDER_COMMAND,
            "expected_output": "entry_tracks.external_agent.first_command is runnable",
            "first_evidence_ref": BRANCH_GRAPH_PATH,
            "standard_refs": ["standard.navigation"],
            "authority_boundary": "Navigation projections do not replace source artifacts.",
            "anti_claims": ["navigation map is source authority", "cold-entry proof is hosted-public proof"],
        },
        {
            "trunk_id": "work_metabolism",
            "title": "Work Metabolism",
            "layman_summary": "How intent becomes claimed, checked work.",
            "technical_summary": "Task Ledger, Work Ledger, transactions, proof, closeout, and residuals.",
            "branch_ids": ["work_metabolism_bridge", "task_ledger_cap_economy"],
            "first_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-concurrency-mission-control-specimen --root . --write-receipt",
            "expected_output": "work_metabolism_bridge.summary.authority_collapse_count == 0",
            "first_evidence_ref": "microcosms/concurrency_mission_control/work_metabolism_bridge.json",
            "standard_refs": ["standard.work_packet", "standard.receipt"],
            "authority_boundary": "Work projections are local proof surfaces, not backlog source authority.",
            "anti_claims": ["status count is action", "classification is completion"],
        },
        {
            "trunk_id": "executable_grammar_and_standards",
            "title": "Executable Grammar And Standards",
            "layman_summary": "How standards become checks.",
            "technical_summary": "Release standards gate, executable grammar, and std_python diagnostics.",
            "branch_ids": ["executable_grammar_metabolism", "release_standards_axiom_gate", "std_python_compliance"],
            "first_command": BUILDER_COMMAND,
            "expected_output": "std_python_compliance_report.summary.scanned_count > 0",
            "first_evidence_ref": STD_PYTHON_REPORT_PATH,
            "standard_refs": ["codex/standards/std_python.py", "standard.principle_enforcement"],
            "authority_boundary": "Diagnostics expose warnings; they do not certify the release.",
            "anti_claims": ["standards diagnostics certify the project", "warnings equal publication permission"],
        },
        {
            "trunk_id": "authority_and_claims",
            "title": "Authority And Claims",
            "layman_summary": "How evidence, claims, and anti-claims stay separate.",
            "technical_summary": "Root contract, status control, package manifest handshake, and fail-closed gates.",
            "branch_ids": ["release_root_contract", "status_preserving_control_plane", "public_release_package_manifest_gate"],
            "first_command": BUILDER_COMMAND,
            "expected_output": "release_root_contract.status.authority_collapse_count == 0",
            "first_evidence_ref": ROOT_CONTRACT_PATH,
            "standard_refs": ["standard.release_gate", "standard.receipt"],
            "authority_boundary": "Local authority classes do not collapse into public release authority.",
            "anti_claims": ROOT_ANTI_CLAIMS,
        },
        {
            "trunk_id": "evidence_replay_and_evaluation",
            "title": "Evidence Replay And Evaluation",
            "layman_summary": "How the system decides what improved and what is next.",
            "technical_summary": "Apex reviewer board, quality board, dogfood loop, executable grammar, and failure replay.",
            "branch_ids": ["apex_reviewer_board", "quality_delta_board", "dogfood_control_loop", "executable_grammar_metabolism"],
            "first_command": "PYTHONPATH=src python3 -m idea_microcosm.cli run-specimen-suite-probe --root . --write-receipt",
            "expected_output": "quality_delta_board.summary.dogfood_loop_status records prior patch observation",
            "first_evidence_ref": "microcosms/specimen_suite/quality_delta_board.json",
            "standard_refs": ["standard.receipt", "standard.work_packet"],
            "authority_boundary": "Evaluator rows choose local next work, not public truth.",
            "anti_claims": ["quality score is publication approval", "local replay is external benchmark proof"],
        },
        {
            "trunk_id": "public_boundary",
            "title": "Public Boundary",
            "layman_summary": "What remains blocked before public claims.",
            "technical_summary": "Hosted, license/citation/disclosure, recipient route, package manifest, and publication gates.",
            "branch_ids": [
                "public_release_package_manifest_gate",
                "hosted_public_ci_workflow_gate",
                "license_citation_disclosure_gate",
                "recipient_review_route_gate",
            ],
            "first_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-public-release-package-manifest-gate-specimen --root . --write-receipt",
            "expected_output": "package manifest gate remains fail-closed where external proof is absent",
            "first_evidence_ref": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json",
            "standard_refs": ["standard.release_gate"],
            "authority_boundary": "Public release stays blocked until each boundary gate proves it.",
            "anti_claims": ROOT_ANTI_CLAIMS,
        },
        {
            "trunk_id": "living_witness_and_exemplars",
            "title": "Living Witness And Exemplars",
            "layman_summary": "Capability examples without identity overclaim.",
            "technical_summary": "Bounded living witness and exemplar branches remain evidence, not release identity.",
            "branch_ids": ["living_substrate_witness"],
            "first_command": "PYTHONPATH=src python3 -m idea_microcosm.cli run-specimen-suite-probe --root . --write-receipt",
            "expected_output": "witness anti-claims remain present",
            "first_evidence_ref": "microcosms/specimen_suite/living_substrate_witness.json",
            "standard_refs": ["standard.receipt"],
            "authority_boundary": "Witnesses demonstrate bounded behavior only.",
            "anti_claims": ["witness is the contribution", "witness proves private-root equivalence"],
        },
    ]


def _missing_refs(root: Path, refs: list[str]) -> list[str]:
    return [ref for ref in refs if not _ref_exists(root, ref)]


def _proof_tail_refresh_plan(root: Path, generated_at: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    total_missing_refs = 0
    all_artifact_refs: list[str] = []
    for group in PROOF_TAIL_REFRESH_GROUPS:
        artifact_refs = list(group["artifact_refs"])
        missing_refs = _missing_refs(root, artifact_refs)
        total_missing_refs += len(missing_refs)
        all_artifact_refs.extend(artifact_refs)
        rows.append(
            {
                "group_id": group["group_id"],
                "owner_command": group["owner_command"],
                "artifact_refs": artifact_refs,
                "validator_refs": list(group["validator_refs"]),
                "public_boundary": group["public_boundary"],
                "repair_boundary": group["repair_boundary"],
                "anti_claims": list(group["anti_claims"]),
                "status": "ok" if not missing_refs else "missing_refs",
                "missing_refs": missing_refs,
                "projection_not_authority": True,
            }
        )
    return {
        "schema_version": "release_proof_tail_refresh_plan_v0",
        "generated_at": generated_at,
        "status": "ok" if total_missing_refs == 0 else "missing_refs",
        "group_count": len(rows),
        "artifact_ref_count": len(all_artifact_refs),
        "missing_ref_count": total_missing_refs,
        "validation_command": "PYTHONPATH=src python3 -m idea_microcosm.cli validate --root .",
        "projection_not_authority": True,
        "source_owner": "src/idea_microcosm/release_root_compiler.py",
        "public_safety_boundary": (
            "Proof-tail refresh proves local generated artifacts are current enough for validation; "
            "it does not prove hosted public availability, publication permission, certification, "
            "or private-root equivalence."
        ),
        "public_claims_still_blocked": _public_claims_still_blocked(),
        "rows": rows,
    }


def _expected_output_failures(branch_graph: dict[str, Any]) -> list[dict[str, Any]]:
    branch_count = len([row for row in branch_graph.get("branches", []) if isinstance(row, dict)])
    failures: list[dict[str, Any]] = []
    for branch in branch_graph.get("branches", []):
        if not isinstance(branch, dict):
            continue
        expected_output = str(branch.get("expected_output", ""))
        for match in re.finditer(r"(?:release_branch_graph\.status\.)?branch_count\s*>=\s*(\d+)", expected_output):
            lower_bound = int(match.group(1))
            if branch_count < lower_bound:
                failures.append(
                    {
                        "branch_id": branch.get("branch_id", "<missing>"),
                        "reason": "expected_output branch_count lower bound exceeds generated branch count",
                        "expected_lower_bound": lower_bound,
                        "actual_branch_count": branch_count,
                    }
                )
    return failures


def _mission_threads() -> list[dict[str, Any]]:
    return [
        {
            "thread_id": "authority_never_collapses",
            "layman_summary": "This thread shows why local evidence cannot turn itself into public-release permission.",
            "branch_ids": ["release_root_contract", "status_preserving_control_plane", "public_release_package_manifest_gate", "hosted_public_ci_workflow_gate"],
            "start_command": BUILDER_COMMAND,
            "evidence_refs": [ROOT_CONTRACT_PATH, "microcosms/public_release_package_manifest_gate/release_authority_handshake.json"],
            "fail_closed_gates": ["hosted_public_ci_workflow_gate", "license_citation_disclosure_gate", "recipient_review_route_gate"],
            "anti_claims": ROOT_ANTI_CLAIMS,
        },
        {
            "thread_id": "work_becomes_durable_substrate",
            "layman_summary": "This thread shows how a loose request becomes tracked, claimed, checked work.",
            "branch_ids": ["work_metabolism_bridge", "task_ledger_cap_economy", "release_branch_graph"],
            "start_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-concurrency-mission-control-specimen --root . --write-receipt",
            "evidence_refs": ["microcosms/concurrency_mission_control/work_metabolism_bridge.json"],
            "anti_claims": ["chat note is durable backlog", "status count is completion"],
        },
        {
            "thread_id": "failure_becomes_teaching",
            "layman_summary": "This thread shows how a failure becomes replayable learning instead of a loose error.",
            "branch_ids": ["executable_grammar_metabolism", "quality_delta_board", "dogfood_control_loop"],
            "start_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-executable-grammar-metabolism-specimen --root . --write-receipt",
            "evidence_refs": ["microcosms/executable_grammar_metabolism/grammar_board.json", "microcosms/specimen_suite/dogfood_control_loop_receipt.json"],
            "anti_claims": ["failure replay proves external benchmark performance", "provider replay measures real provider reliability"],
        },
        {
            "thread_id": "cold_outsider_can_operate",
            "layman_summary": "This thread shows what a newcomer should open, run, inspect, and not infer.",
            "branch_ids": [
                "release_branch_graph",
                "leaf_entry_contract",
                "summary_ladders",
                "macrocosm_contribution_assay",
                "release_microcosm_ontology",
                "std_python_compliance",
            ],
            "start_command": BUILDER_COMMAND,
            "evidence_refs": [BRANCH_GRAPH_PATH, STD_PYTHON_REPORT_PATH, "microcosms/summary_ladders/summary_ladders.json"],
            "anti_claims": ["cold-start route is proof of hosted public availability", "README copy is source authority"],
        },
        {
            "thread_id": "standards_become_runtime",
            "layman_summary": "This thread shows how coding standards become diagnostics instead of advice.",
            "branch_ids": ["std_python_compliance", "release_standards_axiom_gate", "executable_grammar_metabolism"],
            "start_command": BUILDER_COMMAND,
            "evidence_refs": [STD_PYTHON_REPORT_PATH, "microcosms/release_standards_axiom_gate/gate.json"],
            "anti_claims": ["diagnostics are certification", "standards references are enough without tests"],
        },
    ]


def _mission_thread_routes(
    mission_threads: list[dict[str, Any]],
    branches: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    branch_by_id = {str(branch.get("branch_id")): branch for branch in branches}
    routes: list[dict[str, Any]] = []
    for thread in mission_threads:
        steps: list[dict[str, Any]] = []
        for index, branch_id in enumerate(thread.get("branch_ids", []), start=1):
            branch = branch_by_id.get(str(branch_id))
            if not branch:
                continue
            steps.append(
                {
                    "step_id": f"{thread.get('thread_id')}.{index}.{branch_id}",
                    "branch_id": branch_id,
                    "role": branch.get("role"),
                    "branch_type": branch.get("branch_type"),
                    "command": branch.get("what_to_run"),
                    "expected_output": branch.get("expected_output"),
                    "inspect_refs": branch.get("what_to_inspect", []),
                    "evidence_refs": branch.get("evidence_refs", []),
                    "standards_refs": branch.get("standards_refs", []),
                    "authority_class": branch.get("authority_class"),
                    "authority_boundary": branch.get("authority_boundary"),
                    "anti_claims": branch.get("anti_claims", []),
                    "next_branch": branch.get("next_branch"),
                    "next_gap": branch.get("next_gap"),
                }
            )

        commands = sorted({str(step.get("command")) for step in steps if step.get("command")})
        authority_classes = sorted(
            {str(step.get("authority_class")) for step in steps if step.get("authority_class")}
        )
        routes.append(
            {
                "thread_id": thread.get("thread_id"),
                "route_status": "ok" if len(steps) == len(thread.get("branch_ids", [])) else "incomplete",
                "start_command": thread.get("start_command"),
                "step_count": len(steps),
                "command_count": len(commands),
                "commands": commands,
                "evidence_ref_count": sum(len(step.get("evidence_refs", [])) for step in steps),
                "standard_ref_count": sum(len(step.get("standards_refs", [])) for step in steps),
                "anti_claim_count": sum(len(step.get("anti_claims", [])) for step in steps),
                "authority_class_count": len(authority_classes),
                "authority_classes": authority_classes,
                "fail_closed_gates": thread.get("fail_closed_gates", []),
                "proof_sequence": steps,
                "route_boundary": "Compiled branch route only; generated navigation projection remains non-authoritative.",
                "projection_not_authority": True,
                "next_gap": steps[-1]["next_gap"] if steps else "repair missing branch route before publication copy consumes it",
            }
        )
    return routes


def _entry_tracks() -> dict[str, dict[str, Any]]:
    return {
        "human_reviewer": {
            "first_artifact": BRANCH_GRAPH_PATH,
            "first_command": BUILDER_COMMAND,
            "first_evidence": "microcosms/specimen_suite/macrocosm_contribution_assay.json",
            "what_not_to_infer": "Do not infer public-release approval or private-root equivalence.",
            "next_artifact": ROOT_CONTRACT_PATH,
        },
        "technical_cloner": {
            "first_artifact": "README.md",
            "first_command": BUILDER_COMMAND,
            "expected_output": "three generated JSON reports plus optional receipt",
            "first_evidence": STD_PYTHON_REPORT_PATH,
            "what_not_to_infer": "Local diagnostics are not hosted public CI.",
            "next_artifact": BRANCH_GRAPH_PATH,
        },
        "external_agent": {
            "first_artifact": BRANCH_GRAPH_PATH,
            "first_command": BUILDER_COMMAND,
            "expected_output": "branch graph with entry tracks and mission threads",
            "first_evidence": ROOT_CONTRACT_PATH,
            "what_not_to_infer": "Generated graph is navigation, not source authority.",
            "next_artifact": STD_PYTHON_REPORT_PATH,
        },
        "public_boundary_reviewer": {
            "first_artifact": ROOT_CONTRACT_PATH,
            "first_command": "PYTHONPATH=src python3 -m idea_microcosm.cli build-public-release-package-manifest-gate-specimen --root . --write-receipt",
            "first_evidence": "microcosms/public_release_package_manifest_gate/release_authority_handshake.json",
            "fail_closed_checks": ["hosted_public_ci_workflow_gate", "license_citation_disclosure_gate", "recipient_review_route_gate"],
            "what_not_to_infer": "Package manifest rows cannot approve publication.",
            "next_artifact": "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json",
        },
        "future_maintainer": {
            "first_artifact": STD_PYTHON_REPORT_PATH,
            "first_command": BUILDER_COMMAND,
            "first_evidence": RECEIPT_PATH,
            "next_patch_owner": "src/idea_microcosm/release_root_compiler.py",
            "what_not_to_infer": "Warnings are repair rows, not a permission to broad-edit all files.",
            "next_artifact": BRANCH_GRAPH_PATH,
        },
    }


def _python_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    for base in [root / "src" / "idea_microcosm", root / "probes", root / "tests"]:
        if base.exists():
            paths.extend(path for path in base.rglob("*.py") if "__pycache__" not in path.parts)
    return sorted(paths)


def _role_for_path(path: Path) -> str:
    parts = set(path.parts)
    name = path.name
    if "tests" in parts:
        return "test"
    if "probes" in parts:
        return "probe"
    if name == "cli.py":
        return "cli_entrypoint"
    if name.endswith("_specimen.py") or name in {"release_root_compiler.py", "release_standards_specimen.py"}:
        return "builder"
    return "library"


def _branch_for_python(path: Path) -> str:
    stem = path.stem
    mapping = {
        "release_root_compiler": "std_python_compliance",
        "executable_grammar_specimen": "executable_grammar_metabolism",
        "release_standards_specimen": "release_standards_axiom_gate",
        "public_release_package_manifest_gate_specimen": "public_release_package_manifest_gate",
        "status_preserving_control_plane_specimen": "status_preserving_control_plane",
        "task_ledger_specimen": "task_ledger_cap_economy",
        "concurrency_mission_control_specimen": "work_metabolism_bridge",
        "atlas_navigation_specimen": "release_branch_graph",
        "cold_sandbox_probe": "release_branch_graph",
        "test_release_root_compiler": "std_python_compliance",
    }
    if stem in mapping:
        return mapping[stem]
    if stem in LEAF_STEM_ALIASES:
        return LEAF_STEM_ALIASES[stem]
    if stem.endswith("_specimen"):
        return stem.removesuffix("_specimen")
    return "release_python_source"


def _owner_for_python(path: Path) -> str:
    branch_id = _branch_for_python(path)
    if branch_id == "release_python_source":
        return "idea_microcosm_release_source"
    return branch_id


def _module_tag_status(docstring: str | None) -> tuple[str, list[str]]:
    required = ["PURPOSE", "INTERFACE", "FLOW", "DEPENDENCIES", "CONSTRAINTS"]
    if not docstring:
        return "warn", required
    missing = [tag for tag in required if f"[{tag}]" not in docstring]
    return ("pass" if not missing else "warn", missing)


def _type_hint_status(tree: ast.AST) -> tuple[str, list[str]]:
    missing: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("_"):
            continue
        if node.returns is None:
            missing.append(f"{node.name}:return")
        for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]:
            if arg.arg in {"self", "cls"}:
                continue
            if arg.annotation is None:
                missing.append(f"{node.name}:{arg.arg}")
    return ("pass" if not missing else "warn", missing[:12])


def _imports_status(tree: ast.AST) -> tuple[str, list[str]]:
    stdlib = getattr(sys, "stdlib_module_names", set())
    external: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".", 1)[0]
                if top not in stdlib and top != "idea_microcosm":
                    external.add(top)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            module = (node.module or "").split(".", 1)[0]
            if module and module not in stdlib and module != "idea_microcosm":
                external.add(module)
    return ("pass" if not external else "warn", sorted(external))


def _release_test_sources(root: Path) -> tuple[str, list[str]]:
    test_files = sorted(path for path in (root / "tests").glob("test_*.py") if path.is_file())
    chunks = [path.read_text(encoding="utf-8") for path in test_files]
    return "\n".join(chunks), [str(path.relative_to(root)) for path in test_files]


def _docstring_route_atoms(docstring: str | None) -> dict[str, list[str]]:
    atoms = {atom: [] for atom in MICROCOSM_ROUTE_ATOMS}
    if not docstring:
        return atoms
    pattern = re.compile(r"^\s*-?\s*(" + "|".join(re.escape(atom) for atom in MICROCOSM_ROUTE_ATOMS) + r"):\s*(.+?)\s*$")
    for line in docstring.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        atom, value = match.groups()
        atoms[atom].append(value.strip())
    return atoms


def _empty_route_atoms() -> dict[str, list[str]]:
    return {atom: [] for atom in MICROCOSM_ROUTE_ATOMS}


def _merge_route_atoms(*sources: dict[str, list[str]]) -> dict[str, list[str]]:
    merged = _empty_route_atoms()
    for source in sources:
        for atom in MICROCOSM_ROUTE_ATOMS:
            for value in source.get(atom, []):
                if value and value not in merged[atom]:
                    merged[atom].append(value)
    return merged


def _leaf_id_for_python_path(rel_path: str) -> str | None:
    stem = Path(rel_path).stem
    if stem in LEAF_STEM_ALIASES:
        return LEAF_STEM_ALIASES[stem]
    if stem.endswith("_specimen"):
        return stem.removesuffix("_specimen")
    return None


def _leaf_title_from_id(leaf_id: str) -> str:
    if leaf_id == "hosted_public_ci_workflow_gate":
        return "Hosted-Public CI Workflow Gate"
    return leaf_id.replace("_", " ").title()


def _leaf_primary_refs(root: Path, leaf_id: str) -> list[str]:
    leaf_dir = root / "microcosms" / leaf_id
    if not leaf_dir.exists():
        return []
    refs = [f"microcosms/{leaf_id}/README.md"]
    preferred = [
        path
        for path in sorted(leaf_dir.glob("*.json"))
        if path.name not in {"receipt.json"}
    ]
    refs.extend(str(path.relative_to(root)) for path in preferred[:3])
    receipt = leaf_dir / "receipt.json"
    if receipt.exists():
        refs.append(f"microcosms/{leaf_id}/receipt.json")
    return refs


def _leaf_route_atoms(root: Path, rel_path: str, branch_id: str) -> dict[str, list[str]]:
    leaf_id = _leaf_id_for_python_path(rel_path)
    if not leaf_id or not (root / "microcosms" / leaf_id).exists():
        return _empty_route_atoms()
    validator_id = LEAF_VALIDATOR_ALIASES.get(leaf_id, f"validator.{leaf_id}_specimen")
    refs = _leaf_primary_refs(root, leaf_id)
    escalates = ["navigation/microcosm_index.json", *refs]
    title = _leaf_title_from_id(leaf_id)
    return {
        "When-needed": [
            (
                f"Open when a task targets the {title} leaf, its builder code, "
                "receipt trail, validator, or clone-local entry path."
            )
        ],
        "Escalates-to": ["; ".join(escalates)],
        "Navigation-group": [f"microcosm_leaf.{leaf_id}"],
        "Validator": [f"{validator_id}; validator.private_boundary"],
        "Receipt": [f"microcosms/{leaf_id}/receipt.json"],
        "Public-boundary": [
            "Leaf evidence is local fixture evidence; root composition, hosted-public readiness, and publication permission remain gated separately."
        ],
        "Anti-claim": [
            "leaf-local receipts or clone-local inspection prove hosted-public readiness, publication permission, or private-root equivalence"
        ],
    }


def _support_route_atoms(rel_path: str, role: str, branch_id: str) -> dict[str, list[str]]:
    stem = Path(rel_path).stem
    profile = SUPPORT_ROUTE_PROFILES.get(stem) or ROLE_ROUTE_PROFILES.get(role)
    if not profile:
        profile = ROLE_ROUTE_PROFILES["library"]
    escalates = ["navigation/entry_packet.json", *profile.get("escalates", [])]
    return {
        "When-needed": [str(profile["when"])],
        "Escalates-to": ["; ".join(dict.fromkeys(str(item) for item in escalates if item))],
        "Navigation-group": [str(profile.get("group") or f"microcosm_support.{branch_id}")],
        "Validator": [str(profile.get("validator") or "validator.release_root_compiler")],
        "Receipt": [str(profile.get("receipt") or "receipts/validation_run.json")],
        "Public-boundary": [
            "Support-module route inference is a lower-authority navigation projection; source, validators, receipts, and gates remain authoritative."
        ],
        "Anti-claim": [
            "support-module routing proves root composition, hosted-public readiness, publication permission, or private-root equivalence"
        ],
    }


def _inferred_route_atoms(root: Path, rel_path: str, role: str, branch_id: str) -> dict[str, list[str]]:
    leaf_atoms = _leaf_route_atoms(root, rel_path, branch_id)
    if sum(len(values) for values in leaf_atoms.values()) > 0:
        return leaf_atoms
    return _support_route_atoms(rel_path, role, branch_id)


def _route_atom_source_summary(
    authored_atoms: dict[str, list[str]],
    inferred_leaf_atoms: dict[str, list[str]],
    inferred_support_atoms: dict[str, list[str]],
    effective_atoms: dict[str, list[str]],
) -> dict[str, Any]:
    authored_count = sum(len(values) for values in authored_atoms.values())
    inferred_count = sum(len(values) for values in inferred_leaf_atoms.values())
    support_count = sum(len(values) for values in inferred_support_atoms.values())
    return {
        "authored_atom_count": authored_count,
        "inferred_leaf_entry_atom_count": inferred_count,
        "inferred_support_route_atom_count": support_count,
        "effective_atom_count": sum(len(values) for values in effective_atoms.values()),
        "sources": [
            source
            for source, count in (
                ("authored_docstring", authored_count),
                ("existing_leaf_entry_contract", inferred_count),
                ("support_role_route_contract", support_count),
            )
            if count
        ],
        "inference_rule": (
            "Missing file-level route atoms may be inferred from existing leaf README, "
            "receipt, validator, and navigation-index surfaces; inference is a projection, not source authority."
            if inferred_count
            else (
                "Missing file-level route atoms may be inferred from the local support-role route contract; "
                "this is a lower-authority navigation projection, not source authority."
                if support_count
                else ""
            )
        ),
    }


def _first_docstring_signal(docstring: str | None, fallback: str) -> str:
    if not docstring:
        return fallback
    for line in docstring.splitlines():
        cleaned = line.strip().lstrip("-").strip()
        if not cleaned or cleaned.startswith("["):
            continue
        if ":" in cleaned:
            return cleaned
        return cleaned[:180]
    return fallback


def _node_span(node: ast.AST) -> dict[str, int]:
    line_start = int(getattr(node, "lineno", 1) or 1)
    line_end = int(getattr(node, "end_lineno", line_start) or line_start)
    return {"line_start": line_start, "line_end": line_end}


def _annotation_text(node: ast.AST | None) -> str:
    if node is None:
        return "Any"
    try:
        return ast.unparse(node)
    except Exception:
        return "Any"


def _function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args: list[str] = []
    for arg in [*node.args.posonlyargs, *node.args.args]:
        if arg.arg in {"self", "cls"}:
            args.append(arg.arg)
            continue
        args.append(f"{arg.arg}: {_annotation_text(arg.annotation)}")
    if node.args.vararg:
        args.append(f"*{node.args.vararg.arg}: {_annotation_text(node.args.vararg.annotation)}")
    for arg in node.args.kwonlyargs:
        args.append(f"{arg.arg}: {_annotation_text(arg.annotation)}")
    if node.args.kwarg:
        args.append(f"**{node.args.kwarg.arg}: {_annotation_text(node.args.kwarg.annotation)}")
    async_prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
    return f"{async_prefix}{node.name}({', '.join(args)}) -> {_annotation_text(node.returns)}"


def _scope_population_mode(
    atoms: dict[str, list[str]],
    docstring: str | None,
    route_atom_sources: dict[str, Any],
) -> str:
    if int(route_atom_sources.get("authored_atom_count", 0)) > 0:
        return "authored_route_atoms"
    if int(route_atom_sources.get("inferred_leaf_entry_atom_count", 0)) > 0:
        return "inferred_leaf_entry_contract"
    if int(route_atom_sources.get("inferred_support_route_atom_count", 0)) > 0:
        return "inferred_support_route_contract"
    if docstring:
        return "authored_docstring_ast_fallback"
    return "derived_ast_fallback"


def _navigation_group_for_scope(
    atoms: dict[str, list[str]],
    *,
    branch_id: str,
    role: str,
    scope_kind: str,
) -> str:
    explicit = atoms.get("Navigation-group", [])
    if explicit:
        return explicit[0]
    if scope_kind in {"function", "method"}:
        return f"{branch_id}.callable"
    if role == "test":
        return "microcosm_test_contract"
    if role == "probe":
        return "microcosm_probe_contract"
    return branch_id


def _scope_navigation_row(
    *,
    rel_path: str,
    role: str,
    branch_id: str,
    scope_kind: str,
    qualname: str,
    node: ast.AST,
    docstring: str | None,
    signature: str,
    inferred_leaf_atoms: dict[str, list[str]] | None = None,
    inferred_support_atoms: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    authored_atoms = _docstring_route_atoms(docstring)
    leaf_atoms = inferred_leaf_atoms or _empty_route_atoms()
    support_atoms = inferred_support_atoms or _empty_route_atoms()
    atoms = _merge_route_atoms(authored_atoms, leaf_atoms, support_atoms)
    route_atom_sources = _route_atom_source_summary(authored_atoms, leaf_atoms, support_atoms, atoms)
    span = _node_span(node)
    scope_id = f"{rel_path}::{qualname}" if scope_kind != "module" else rel_path
    navigation_group = _navigation_group_for_scope(
        atoms,
        branch_id=branch_id,
        role=role,
        scope_kind=scope_kind,
    )
    source_span_ref = f"{rel_path}:{span['line_start']}-{span['line_end']}"
    fallback_signal = f"{scope_kind} {qualname} in {Path(rel_path).name}"
    return {
        "scope_id": scope_id,
        "path": rel_path,
        "role": role,
        "branch_id": branch_id,
        "scope_kind": scope_kind,
        "qualname": qualname,
        "navigation_group": navigation_group,
        "signature": signature,
        "line_start": span["line_start"],
        "line_end": span["line_end"],
        "source_span_ref": source_span_ref,
        "population_mode": _scope_population_mode(atoms, docstring, route_atom_sources),
        "docstring_present": bool(docstring),
        "first_signal": _first_docstring_signal(docstring, fallback_signal),
        "navigation_atoms": {"atom_count": sum(len(values) for values in atoms.values()), "atoms": atoms},
        "route_atom_sources": route_atom_sources,
        "file_report_ref": f"{STD_PYTHON_REPORT_PATH}::file_rows[path={rel_path}]",
        "scope_report_ref": f"{STD_PYTHON_REPORT_PATH}::scope_rows[scope_id={scope_id}]",
        "authority_boundary": "Scope rows route code comprehension only; exact source span and validators remain authoritative.",
        "anti_claims": [
            "scope card is source authority",
            "derived AST fallback is authored design intent",
            "local navigation index is private-root-wide Python compliance",
        ],
    }


def _scope_rows_for_python(root: Path, path: Path) -> list[dict[str, Any]]:
    rel_path = str(path.relative_to(root))
    text = path.read_text(encoding="utf-8")
    role = _role_for_path(path)
    branch_id = _branch_for_python(path)
    inferred_leaf_module_atoms = _leaf_route_atoms(root, rel_path, branch_id)
    inferred_support_module_atoms = (
        _empty_route_atoms()
        if sum(len(values) for values in inferred_leaf_module_atoms.values()) > 0
        else _support_route_atoms(rel_path, role, branch_id)
    )
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    rows = [
        _scope_navigation_row(
            rel_path=rel_path,
            role=role,
            branch_id=branch_id,
            scope_kind="module",
            qualname=Path(rel_path).stem,
            node=tree,
            docstring=ast.get_docstring(tree),
            signature=f"module {Path(rel_path).stem}",
            inferred_leaf_atoms=inferred_leaf_module_atoms,
            inferred_support_atoms=inferred_support_module_atoms,
        )
    ]
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            rows.append(
                _scope_navigation_row(
                    rel_path=rel_path,
                    role=role,
                    branch_id=branch_id,
                    scope_kind="function",
                    qualname=node.name,
                    node=node,
                    docstring=ast.get_docstring(node),
                    signature=_function_signature(node),
                    inferred_leaf_atoms=inferred_leaf_module_atoms,
                    inferred_support_atoms=inferred_support_module_atoms,
                )
            )
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            rows.append(
                _scope_navigation_row(
                    rel_path=rel_path,
                    role=role,
                    branch_id=branch_id,
                    scope_kind="class",
                    qualname=node.name,
                    node=node,
                    docstring=ast.get_docstring(node),
                    signature=f"class {node.name}",
                    inferred_leaf_atoms=inferred_leaf_module_atoms,
                    inferred_support_atoms=inferred_support_module_atoms,
                )
            )
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not item.name.startswith("_"):
                    rows.append(
                        _scope_navigation_row(
                            rel_path=rel_path,
                            role=role,
                            branch_id=branch_id,
                            scope_kind="method",
                            qualname=f"{node.name}.{item.name}",
                            node=item,
                            docstring=ast.get_docstring(item),
                            signature=_function_signature(item),
                            inferred_leaf_atoms=inferred_leaf_module_atoms,
                            inferred_support_atoms=inferred_support_module_atoms,
                        )
                    )
    return rows


def _scope_navigation_index(scope_rows: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    group_ids = sorted({str(row["navigation_group"]) for row in scope_rows})
    clusters: list[dict[str, Any]] = []
    flags: list[dict[str, Any]] = []
    cards: list[dict[str, Any]] = []
    for group_id in group_ids:
        group_rows = [row for row in scope_rows if row["navigation_group"] == group_id]
        branch_ids = sorted({str(row["branch_id"]) for row in group_rows})
        clusters.append(
            {
                "cluster_id": group_id,
                "band": "cluster_flag",
                "scope_count": len(group_rows),
                "branch_ids": branch_ids,
                "scope_kinds": sorted({str(row["scope_kind"]) for row in group_rows}),
                "first_flag_refs": [f"{STD_PYTHON_REPORT_PATH}::navigation_index.flags[row_id={row['scope_id']}]" for row in group_rows[:8]],
                "authority_boundary": "Cluster rows are navigation projections, not source authority.",
            }
        )

    for row in scope_rows:
        atom_values = row.get("navigation_atoms", {}).get("atoms", {})
        when_needed = atom_values.get("When-needed", [])
        escalates_to = atom_values.get("Escalates-to", [])
        flags.append(
            {
                "row_id": row["scope_id"],
                "band": "flag",
                "cluster_id": row["navigation_group"],
                "title": row["qualname"],
                "path": row["path"],
                "scope_kind": row["scope_kind"],
                "flag": when_needed[0] if when_needed else row["first_signal"],
                "population_mode": row["population_mode"],
                "card_ref": f"{STD_PYTHON_REPORT_PATH}::navigation_index.cards[row_id={row['scope_id']}]",
                "source_span_ref": row["source_span_ref"],
            }
        )
        cards.append(
            {
                "row_id": row["scope_id"],
                "band": "card",
                "cluster_id": row["navigation_group"],
                "title": row["qualname"],
                "path": row["path"],
                "scope_kind": row["scope_kind"],
                "branch_id": row["branch_id"],
                "signature": row["signature"],
                "first_signal": row["first_signal"],
                "when_needed": when_needed,
                "escalates_to": escalates_to,
                "validator_refs": atom_values.get("Validator", []),
                "receipt_refs": atom_values.get("Receipt", []),
                "source_span_ref": row["source_span_ref"],
                "file_report_ref": row["file_report_ref"],
                "scope_report_ref": row["scope_report_ref"],
                "population_mode": row["population_mode"],
                "authority_boundary": row["authority_boundary"],
                "omission_receipt": {
                    "omitted": ["source body", "full caller/callee graph", "runtime execution state"],
                    "reason": "Card band supports route selection and source-span targeting without replacing source.",
                    "drilldown": row["source_span_ref"],
                },
                "anti_claims": row["anti_claims"],
            }
        )

    return {
        "schema_version": "std_python_microcosm_navigation_index_v0",
        "generated_at": generated_at,
        "profile_id": "std_python_microcosm_scope_navigation_v1",
        "authority_posture": "generated_navigation_projection_not_source_authority",
        "source_authority": [
            "codex/standards/std_python.py",
            "src/idea_microcosm/**/*.py",
            "probes/*.py",
            "tests/test_*.py",
        ],
        "band_order": ["cluster_flag", "flag", "card", "source_span"],
        "summary": {
            "scope_row_count": len(scope_rows),
            "cluster_count": len(clusters),
            "flag_count": len(flags),
            "card_count": len(cards),
            "authored_route_atom_scope_count": sum(1 for row in scope_rows if row["population_mode"] == "authored_route_atoms"),
            "inferred_leaf_entry_scope_count": sum(1 for row in scope_rows if row["population_mode"] == "inferred_leaf_entry_contract"),
            "inferred_support_route_scope_count": sum(1 for row in scope_rows if row["population_mode"] == "inferred_support_route_contract"),
            "derived_ast_fallback_scope_count": sum(1 for row in scope_rows if row["population_mode"] == "derived_ast_fallback"),
            "function_or_method_count": sum(1 for row in scope_rows if row["scope_kind"] in {"function", "method"}),
        },
        "clusters": clusters,
        "flags": flags,
        "cards": cards,
        "source_span_policy": "Open exact source spans only after a card selects a scope and source is needed for mutation or proof.",
        "omission_receipt": {
            "omitted": ["source bodies", "dynamic runtime traces", "private-root Python scope graph"],
            "reason": "The microcosm is small enough to expose all scopes as cards while preserving source as authority.",
            "drilldown": "open the selected source_span_ref",
        },
    }


def _microcosm_navigation_profile(
    rel_path: str,
    role: str,
    branch_id: str,
    atoms: dict[str, list[str]],
    route_atom_sources: dict[str, Any] | None = None,
) -> dict[str, Any]:
    missing_route_atoms = [
        atom for atom in ("When-needed", "Escalates-to", "Navigation-group") if not atoms.get(atom)
    ]
    if role == "cli_entrypoint":
        first_band = "command_route"
    elif role in {"builder", "library"}:
        first_band = "std_python_report_row"
    elif role in {"test", "probe"}:
        first_band = "validator_receipt"
    else:
        first_band = "source_span"
    leaf_id = _leaf_id_for_python_path(rel_path)
    return {
        "status": "enriched" if not missing_route_atoms else "sparse",
        "first_band": first_band,
        "branch_id": branch_id,
        "leaf_id": leaf_id,
        "report_row_ref": f"{STD_PYTHON_REPORT_PATH}::file_rows[path={rel_path}]",
        "when_needed": atoms.get("When-needed", []),
        "escalates_to": atoms.get("Escalates-to", []),
        "navigation_group": atoms.get("Navigation-group", []),
        "validator_refs": atoms.get("Validator", []),
        "receipt_refs": atoms.get("Receipt", []),
        "missing_route_atoms": missing_route_atoms,
        "route_atom_sources": route_atom_sources or {},
        "authority_boundary": "Route atoms guide cold-start navigation only; exact source and validators remain authoritative.",
    }


def _navigation_population_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    route_atom_files = [
        row
        for row in rows
        if any(values for values in row.get("navigation_atoms", {}).get("atoms", {}).values())
    ]
    enriched_rows = [
        row
        for row in rows
        if row.get("microcosm_navigation", {}).get("status") == "enriched"
    ]
    missing_route_atoms = sorted(
        {
            atom
            for row in rows
            for atom in row.get("microcosm_navigation", {}).get("missing_route_atoms", [])
        }
    )
    return {
        "navigation_atom_file_count": len(route_atom_files),
        "inferred_leaf_entry_file_count": sum(
            1
            for row in rows
            if int(row.get("route_atom_sources", {}).get("inferred_leaf_entry_atom_count", 0)) > 0
        ),
        "inferred_support_route_file_count": sum(
            1
            for row in rows
            if int(row.get("route_atom_sources", {}).get("inferred_support_route_atom_count", 0)) > 0
        ),
        "microcosm_navigation_enriched_count": len(enriched_rows),
        "leaf_entry_enriched_count": sum(
            1
            for row in enriched_rows
            if row.get("microcosm_navigation", {}).get("leaf_id")
        ),
        "support_route_enriched_count": sum(
            1
            for row in enriched_rows
            if int(row.get("route_atom_sources", {}).get("inferred_support_route_atom_count", 0)) > 0
        ),
        "microcosm_navigation_sparse_count": len(rows) - len(enriched_rows),
        "microcosm_navigation_enriched_paths": [row["path"] for row in enriched_rows[:12]],
        "microcosm_navigation_missing_route_atoms": missing_route_atoms,
    }


def _test_status(root: Path, rel_path: str, role: str, tests_text: str) -> tuple[str, list[str]]:
    if role == "test":
        return "pass", ["test file is itself executable coverage"]
    if Path(rel_path).name == "__init__.py":
        return "pass", ["package marker is covered by import-based release tests"]
    stem = Path(rel_path).stem
    if stem in tests_text or rel_path in tests_text:
        return "pass", ["referenced by release-root tests"]
    if role in {"cli_entrypoint", "probe"}:
        return "pass", ["covered through CLI/probe command tests"]
    return "warn", ["missing direct test reference in release-root tests"]


def _public_safe_status(text: str) -> tuple[str, list[str]]:
    blocked_tokens = [
        "openai_api" + "_key",
        "anthropic_api" + "_key",
        "private" + "_key",
        "BEGIN RSA " + "PRIVATE KEY",
    ]
    hits = [token for token in blocked_tokens if token.lower() in text.lower()]
    return ("pass" if not hits else "warn", hits)


def _diagnostic_next_fix(path: str, diagnostics: list[dict[str, Any]]) -> str:
    if not diagnostics:
        return "none"
    fixes: list[str] = []
    for diagnostic in diagnostics:
        kind = diagnostic.get("kind")
        if kind == "module_tags":
            missing = ", ".join(diagnostic.get("missing", []))
            fixes.append(f"add module docstring tags: {missing}")
        elif kind == "type_hints":
            missing = ", ".join(diagnostic.get("missing", []))
            fixes.append(f"add public function annotations: {missing}")
        elif kind == "dependencies":
            external = ", ".join(diagnostic.get("external", []))
            fixes.append(f"replace or justify release-local dependency: {external}")
        elif kind == "test_reference":
            fixes.append(f"add a direct release-root test reference for {Path(path).stem}")
        elif kind == "public_safety":
            hits = ", ".join(diagnostic.get("hits", []))
            fixes.append(f"review public-safety token hits and preserve secret-boundary intent: {hits}")
        elif kind == "syntax":
            fixes.append("repair Python syntax before standards classification")
        else:
            fixes.append(f"route diagnostic kind {kind} to a release-root repair row")
    return "; ".join(fixes)


def _warning_class_for_row(row: dict[str, Any], protected: bool) -> str:
    diagnostics = row.get("diagnostics", [])
    kinds = {str(diagnostic.get("kind", "unknown")) for diagnostic in diagnostics if isinstance(diagnostic, dict)}
    if not kinds:
        return "none" if row.get("std_python_status") == "pass" else "unknown"
    if "public_safety" in kinds:
        return "public_safety_token"
    if protected:
        return "protected_owner"
    if "module_tags" in kinds:
        return "missing_module_metadata"
    if "test_reference" in kinds:
        return "missing_test"
    if "dependencies" in kinds:
        return "dependency_warning"
    if "syntax" in kinds:
        return "syntax"
    return "unknown"


def _owner_class_for_row(row: dict[str, Any]) -> str:
    path = str(row.get("path", ""))
    if path in STD_PYTHON_PROTECTED_WARNING_BOUNDARIES:
        return str(STD_PYTHON_PROTECTED_WARNING_BOUNDARIES[path]["owner_class"])
    if str(row.get("role")) == "test":
        return "test_contract_owned"
    if str(row.get("role")) == "probe":
        return "probe_owned"
    return "release_root_compiler_owned"


def _next_safe_fix_for_row(row: dict[str, Any], protected_boundary: dict[str, str] | None) -> str:
    next_fix = str(row.get("next_fix") or "")
    if row.get("std_python_status") == "pass":
        return "none"
    if protected_boundary:
        return (
            f"{next_fix}; preserve owner boundary and satisfy reentry condition before mutation"
            if next_fix
            else "preserve owner boundary and satisfy reentry condition before mutation"
        )
    return next_fix or "apply the row diagnostics, then rebuild release-root compiler artifacts"


def _classify_std_python_row(row: dict[str, Any]) -> dict[str, Any]:
    path = str(row.get("path", ""))
    protected_boundary = STD_PYTHON_PROTECTED_WARNING_BOUNDARIES.get(path)
    status = str(row.get("std_python_status", "unknown"))
    protection_status = (
        str(protected_boundary["protection_status"])
        if protected_boundary
        else "patchable_now"
        if status in {"warn", "block"}
        else "fixed"
    )
    row["owner_class"] = _owner_class_for_row(row)
    row["protection_status"] = protection_status
    row["warning_class"] = _warning_class_for_row(row, protected_boundary is not None)
    row["reentry_condition"] = str(protected_boundary["reentry_condition"]) if protected_boundary else ""
    row["next_safe_fix"] = _next_safe_fix_for_row(row, protected_boundary)
    if status == "pass":
        row["standards_debt_status"] = "fixed"
    elif protected_boundary:
        row["standards_debt_status"] = "protected"
    elif protection_status == "patchable_now":
        row["standards_debt_status"] = "patchable"
    else:
        row["standards_debt_status"] = "unknown"
    return row


def _python_row(root: Path, path: Path, tests_text: str) -> dict[str, Any]:
    rel_path = str(path.relative_to(root))
    text = path.read_text(encoding="utf-8")
    role = _role_for_path(path)
    branch_id = _branch_for_python(path)
    diagnostics: list[dict[str, Any]] = []
    try:
        tree = ast.parse(text)
        syntax_status = "pass"
    except SyntaxError as exc:
        empty_atoms = _docstring_route_atoms(None)
        empty_sources = _route_atom_source_summary(empty_atoms, empty_atoms, empty_atoms, empty_atoms)
        return _classify_std_python_row(
            {
            "path": rel_path,
            "role": role,
            "owner_microcosm": _owner_for_python(path),
            "branch_id": branch_id,
            "std_python_status": "block",
            "entrypoint_status": "unknown",
            "type_hint_status": "unknown",
            "cli_status": "unknown",
            "test_status": "unknown",
            "dependency_status": "unknown",
            "public_safe_status": "unknown",
            "projection_authority_status": "unknown",
            "navigation_atoms": {"atom_count": 0, "atoms": empty_atoms},
            "inferred_navigation_atoms": {"atom_count": 0, "atoms": empty_atoms},
            "inferred_support_navigation_atoms": {"atom_count": 0, "atoms": empty_atoms},
            "route_atom_sources": empty_sources,
            "microcosm_navigation": _microcosm_navigation_profile(
                rel_path,
                role,
                branch_id,
                empty_atoms,
                empty_sources,
            ),
            "diagnostics": [{"kind": "syntax", "status": "block", "detail": str(exc)}],
            "evidence_refs": [rel_path],
            "anti_claims": ["syntax diagnostics are not semantic proof"],
            "next_fix": "repair syntax before std_python classification",
            }
        )

    module_docstring = ast.get_docstring(tree)
    authored_route_atoms = _docstring_route_atoms(module_docstring)
    inferred_leaf_route_atoms = _leaf_route_atoms(root, rel_path, branch_id)
    inferred_support_route_atoms = (
        _empty_route_atoms()
        if sum(len(values) for values in inferred_leaf_route_atoms.values()) > 0
        else _support_route_atoms(rel_path, role, branch_id)
    )
    route_atoms = _merge_route_atoms(authored_route_atoms, inferred_leaf_route_atoms, inferred_support_route_atoms)
    route_atom_sources = _route_atom_source_summary(
        authored_route_atoms,
        inferred_leaf_route_atoms,
        inferred_support_route_atoms,
        route_atoms,
    )
    atom_count = sum(len(values) for values in route_atoms.values())
    tag_status, missing_tags = _module_tag_status(module_docstring)
    type_status, missing_type_hints = _type_hint_status(tree)
    dep_status, external_deps = _imports_status(tree)
    test_status, test_details = _test_status(root, rel_path, role, tests_text)
    public_status, public_hits = _public_safe_status(text)

    entrypoint_status = "pass" if role == "cli_entrypoint" and "argparse" in text else "not_required"
    cli_status = "pass" if role != "cli_entrypoint" or "subparsers" in text else "warn"
    projection_authority_status = "pass"

    if tag_status != "pass":
        diagnostics.append({"kind": "module_tags", "status": tag_status, "missing": missing_tags})
    if type_status != "pass":
        diagnostics.append({"kind": "type_hints", "status": type_status, "missing": missing_type_hints})
    if dep_status != "pass":
        diagnostics.append({"kind": "dependencies", "status": dep_status, "external": external_deps})
    if test_status != "pass":
        diagnostics.append({"kind": "test_reference", "status": test_status, "detail": test_details})
    if public_status != "pass":
        diagnostics.append({"kind": "public_safety", "status": public_status, "hits": public_hits})

    statuses = [syntax_status, tag_status, type_status, dep_status, test_status, public_status]
    std_python_status = "block" if "block" in statuses else "warn" if "warn" in statuses else "pass"
    next_fix = _diagnostic_next_fix(rel_path, diagnostics)
    return _classify_std_python_row({
        "path": rel_path,
        "role": role,
        "owner_microcosm": _owner_for_python(path),
        "branch_id": branch_id,
        "std_python_status": std_python_status,
        "entrypoint_status": entrypoint_status,
        "type_hint_status": type_status,
        "cli_status": cli_status,
        "test_status": test_status,
        "dependency_status": dep_status,
        "public_safe_status": public_status,
        "projection_authority_status": projection_authority_status,
        "navigation_atoms": {"atom_count": atom_count, "atoms": route_atoms},
        "authored_navigation_atoms": {
            "atom_count": sum(len(values) for values in authored_route_atoms.values()),
            "atoms": authored_route_atoms,
        },
        "inferred_navigation_atoms": {
            "atom_count": sum(len(values) for values in inferred_leaf_route_atoms.values()),
            "atoms": inferred_leaf_route_atoms,
        },
        "inferred_support_navigation_atoms": {
            "atom_count": sum(len(values) for values in inferred_support_route_atoms.values()),
            "atoms": inferred_support_route_atoms,
        },
        "route_atom_sources": route_atom_sources,
        "microcosm_navigation": _microcosm_navigation_profile(rel_path, role, branch_id, route_atoms, route_atom_sources),
        "diagnostics": diagnostics,
        "evidence_refs": [rel_path, "codex/standards/std_python.py"],
        "anti_claims": [
            "local release-root standards diagnostics only",
            "not private-root-wide compliance",
            "not security certification",
        ],
        "next_fix": next_fix,
    })


def _diagnostic_kind_counts(rows: list[dict[str, Any]], *, status: str | None = None) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for diagnostic in row.get("diagnostics", []):
            if status is not None and diagnostic.get("status") != status:
                continue
            kind = str(diagnostic.get("kind", "unknown"))
            counts[kind] = counts.get(kind, 0) + 1
    return dict(sorted(counts.items()))


def _branch_warning_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        if row.get("std_python_status") == "pass":
            continue
        branch_id = str(row.get("branch_id", "unknown"))
        counts[branch_id] = counts.get(branch_id, 0) + 1
    return dict(sorted(counts.items()))


def _unclassified_warning_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unclassified: list[dict[str, Any]] = []
    for row in rows:
        if row.get("std_python_status") not in {"warn", "block"}:
            continue
        if (
            row.get("warning_class") in {None, "", "unknown"}
            or row.get("owner_class") in {None, "", "unknown"}
            or row.get("protection_status") in {None, "", "unknown"}
            or row.get("standards_debt_status") in {None, "", "unknown"}
            or not row.get("anti_claims")
            or not (row.get("next_safe_fix") or row.get("reentry_condition"))
        ):
            unclassified.append(row)
    return unclassified


def _standards_closure_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    warning_rows = [row for row in rows if row.get("std_python_status") in {"warn", "block"}]
    protected_rows = [row for row in warning_rows if str(row.get("protection_status", "")).startswith("protected")]
    patchable_rows = [row for row in warning_rows if row.get("protection_status") == "patchable_now"]
    unclassified_rows = _unclassified_warning_rows(rows)
    return {
        "protected_warning_count": len(protected_rows),
        "source_patchable_warning_count": len(patchable_rows),
        "unclassified_warning_count": len(unclassified_rows),
        "next_safe_patch_count": len(patchable_rows),
        "standards_closure_status": "ok" if not unclassified_rows else "block",
        "standards_closure_summary": (
            "All residual std_python warnings are classified by owner, protection boundary, and next safe fix."
            if not unclassified_rows
            else "One or more residual std_python warnings lack owner/protection/reentry classification."
        ),
        "next_safe_warning_targets": [
            {
                "path": row.get("path"),
                "warning_class": row.get("warning_class"),
                "owner_class": row.get("owner_class"),
                "next_safe_fix": row.get("next_safe_fix"),
            }
            for row in patchable_rows[:8]
        ],
        "protected_warning_reentry_conditions": [
            {
                "path": row.get("path"),
                "owner_class": row.get("owner_class"),
                "protection_status": row.get("protection_status"),
                "reentry_condition": row.get("reentry_condition"),
            }
            for row in protected_rows
        ],
    }


def _std_python_next_fix(
    *,
    warning_count: int,
    blocker_count: int,
    protected_warning_count: int,
    source_patchable_warning_count: int,
    unclassified_warning_count: int,
) -> str:
    if blocker_count:
        return "Repair std_python blocker rows before strengthening standards claims."
    if unclassified_warning_count:
        return "Classify every residual std_python warning by owner, protection boundary, and re-entry condition."
    if source_patchable_warning_count:
        return "Patch source-owned std_python warning targets listed in next_safe_warning_targets, then rebuild."
    if protected_warning_count and protected_warning_count == warning_count:
        return "Only protected std_python residuals remain; re-enter after sibling, validator, or test-contract ownership is released."
    if warning_count:
        return "Review classified residual std_python warnings and apply the safest owner-specific repair."
    return "No std_python warnings remain; advance the next standards gap through release-root contract ownership."


def _repair_command_for_kind(kind: str) -> str:
    commands = {
        "module_tags": "edit the listed Python files to add [PURPOSE], [INTERFACE], [FLOW], [DEPENDENCIES], and [CONSTRAINTS] atoms, then rebuild the release-root compiler",
        "type_hints": "add the listed public function annotations, then run py_compile and focused release-root tests",
        "dependencies": "remove the dependency or record a release-local dependency boundary, then rebuild the std_python report",
        "test_reference": "add focused tests under tests/test_*.py for the listed modules, then rebuild the std_python report",
        "public_safety": "review the token hit as a public-boundary diagnostic; split harmless fixture literals or keep the warning with anti-claims",
        "syntax": "repair syntax, run py_compile, then rebuild the std_python report",
    }
    return commands.get(kind, "route this diagnostic kind through release_root_compiler repair-plan ownership")


def _build_repair_plan(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        for diagnostic in row.get("diagnostics", []):
            grouped.setdefault(str(diagnostic.get("kind", "unknown")), []).append(row)

    plan: list[dict[str, Any]] = []
    for kind, kind_rows in sorted(grouped.items()):
        statuses = {str(row.get("std_python_status")) for row in kind_rows}
        paths = sorted({str(row.get("path")) for row in kind_rows if row.get("path")})
        plan.append(
            {
                "repair_id": f"std_python.{kind}",
                "diagnostic_kind": kind,
                "status": "block" if "block" in statuses else "warn",
                "file_count": len(paths),
                "first_paths": paths[:8],
                "owner": "src/idea_microcosm/release_root_compiler.py",
                "first_command": _repair_command_for_kind(kind),
                "acceptance_check": (
                    "PYTHONPATH=src python3 -m idea_microcosm.cli build-release-root-compiler "
                    "--root . --write-receipt && PYTHONPATH=src python3 -m idea_microcosm.cli validate --root ."
                ),
                "authority_boundary": "Repair rows are local release-root diagnostics, not certification or release approval.",
                "anti_claims": [
                    "diagnostic repair plan is public release approval",
                    "warning rows prove private-root-wide noncompliance",
                    "repair plan replaces source review",
                ],
            }
        )
    return plan


def _authority_class_rows() -> dict[str, dict[str, Any]]:
    return {
        "local_fixture_evidence": {
            "can_claim": [
                "a local deterministic fixture ran",
                "a JSON report was generated",
                "a validator/test consumed the report",
            ],
            "cannot_claim": ["hosted public availability", "publication permission", "private-root equivalence"],
            "promotion_requires": ["fresh receipt", "claim inference row", "anti-claim row", "boundary gate status"],
        },
        "local_clone_evidence": {
            "can_claim": ["a clone-shaped local check passed"],
            "cannot_claim": ["hosted public CI", "external reviewer outcome"],
            "promotion_requires": ["hosted_public_ci_workflow_gate evidence"],
        },
        "hosted_public_evidence": {
            "can_claim": ["hosted public workflow status when external proof exists"],
            "cannot_claim": ["publication permission", "rights clearance"],
            "promotion_requires": ["operator release toggle plus rights/citation/disclosure clearance"],
        },
        "publication_permission": {
            "can_claim": ["public release may be stated only after all gates pass"],
            "cannot_claim": ["private root is released", "novelty or benchmark superiority"],
            "promotion_requires": ["operator approval", "rights clearance", "hosted proof", "recipient route status"],
        },
        "private_root_evidence": {
            "public_release_handling": "never_expose_private_root_in_release_microcosm",
        },
        "generated_navigation_projection": {
            "can_claim": ["navigation surface points to source refs and commands"],
            "cannot_claim": ["source authority", "publication permission", "hosted public availability"],
            "promotion_requires": ["source owner", "builder command", "projection_not_authority flag"],
        },
        "evaluator_projection": {
            "can_claim": ["local evaluator selected a next inference or repair lane"],
            "cannot_claim": ["truth authority", "publication permission", "hosted public availability"],
            "promotion_requires": ["source evidence row", "receipt row", "anti-claim row"],
        },
        "local_contract_projection": {
            "can_claim": ["the release root contract generated and validates locally"],
            "cannot_claim": ["public release approval", "private-root equivalence", "hosted public availability"],
            "promotion_requires": ["package gate consumption plus external proof gates"],
        },
        "local_diagnostic_report": {
            "can_claim": ["release-local diagnostic status"],
            "cannot_claim": ["standards certification", "security certification", "public release approval"],
            "promotion_requires": ["hosted CI plus independent review gates"],
        },
        "local_boundary_gate": {
            "can_claim": ["a local boundary gate blocked or allowed a bounded local package row"],
            "cannot_claim": ["publication permission", "rights clearance", "private-root equivalence"],
            "promotion_requires": ["all named public-boundary gates current and operator approval"],
        },
        "fail_closed_boundary": {
            "can_claim": ["a missing proof keeps the public claim blocked"],
            "cannot_claim": ["the blocked claim is approved"],
            "promotion_requires": ["fresh evidence for the specific blocked authority class"],
        },
        "bounded_capability_witness": {
            "can_claim": ["a bounded exemplar shows one capability surface"],
            "cannot_claim": ["the exemplar is the release identity", "theorem proof", "benchmark superiority"],
            "promotion_requires": ["separate proof surface for each stronger claim"],
        },
    }


def _authority_lattice() -> dict[str, Any]:
    claim_rows = [
        {
            "claim_id": "release_root_compiler_ran_locally",
            "claim": "The release root compiler generated the branch graph, root contract, and std_python report in this checkout.",
            "authority_class": "local_fixture_evidence",
            "can_infer": ["local builder and validator behavior for this checkout"],
            "cannot_infer": ["hosted public availability", "publication permission", "private-root equivalence"],
            "evidence_refs": [RECEIPT_PATH, ROOT_CONTRACT_PATH, BRANCH_GRAPH_PATH, STD_PYTHON_REPORT_PATH],
            "promotion_requires": ["fresh hosted-public gate receipt", "package manifest gate", "operator release decision"],
            "authority_boundary": "Local fixture evidence only.",
            "anti_claims": ["local compiler receipt is hosted public proof"],
        },
        {
            "claim_id": "std_python_diagnostics_are_actionable",
            "claim": "The release microcosm Python source is diagnosable against the release-local std_python adapter.",
            "authority_class": "local_diagnostic_report",
            "can_infer": ["release-local files have classified diagnostics and repair rows"],
            "cannot_infer": ["standards certification", "security certification", "private-root-wide compliance"],
            "evidence_refs": [STD_PYTHON_REPORT_PATH, "codex/standards/std_python.py"],
            "promotion_requires": ["external audit or hosted CI evidence for any public certification claim"],
            "authority_boundary": "Diagnostic report, not certification.",
            "anti_claims": ["std_python report certifies release quality"],
        },
        {
            "claim_id": "branch_graph_guides_review",
            "claim": "The branch graph gives cold humans and agents a route across commands, evidence, anti-claims, standards, and next gaps.",
            "authority_class": "generated_navigation_projection",
            "can_infer": ["navigation structure exists and has source refs"],
            "cannot_infer": ["generated projection is source authority", "README or graph copy grants publication approval"],
            "evidence_refs": [BRANCH_GRAPH_PATH],
            "promotion_requires": ["source-owner mutation plus builder rerun"],
            "authority_boundary": "Generated navigation projection only.",
            "anti_claims": ["branch graph is source authority"],
        },
        {
            "claim_id": "hosted_public_remains_unproven",
            "claim": "Hosted public availability remains blocked until hosted-public proof is current.",
            "authority_class": "fail_closed_boundary",
            "can_infer": ["the public claim is blocked by default"],
            "cannot_infer": ["hosted public CI has passed", "public release is approved"],
            "evidence_refs": ["microcosms/hosted_public_ci_workflow_gate/workflow_gate.json"],
            "promotion_requires": ["fresh hosted public remote CI receipt"],
            "authority_boundary": "Fail-closed public boundary.",
            "anti_claims": ["stale or absent hosted proof counts as approval"],
        },
        {
            "claim_id": "living_witness_is_bounded",
            "claim": "The living substrate witness is a bounded capability exemplar, not the release identity.",
            "authority_class": "bounded_capability_witness",
            "can_infer": ["one bounded capability witness exists"],
            "cannot_infer": ["theorem proof", "benchmark superiority", "private-root equivalence", "release identity"],
            "evidence_refs": ["microcosms/specimen_suite/living_substrate_witness.json"],
            "promotion_requires": ["separate proof and publication gates for each stronger claim"],
            "authority_boundary": "Exemplar, not identity.",
            "anti_claims": ["capability witness is the release contribution"],
        },
    ]
    forbidden_promotions = [
        {
            "from_authority_class": "local_fixture_evidence",
            "to_authority_class": "hosted_public_evidence",
            "status": "blocked_without_gate",
            "promotion_requires": ["fresh hosted_public_ci_workflow_gate receipt"],
            "anti_claims": ["local fixture evidence proves hosted public availability"],
        },
        {
            "from_authority_class": "local_clone_evidence",
            "to_authority_class": "hosted_public_evidence",
            "status": "blocked_without_gate",
            "promotion_requires": ["fresh hosted public remote proof"],
            "anti_claims": ["local clone proof is hosted public proof"],
        },
        {
            "from_authority_class": "hosted_public_evidence",
            "to_authority_class": "publication_permission",
            "status": "blocked_without_gate",
            "promotion_requires": ["operator release toggle", "rights clearance", "citation/disclosure clearance"],
            "anti_claims": ["hosted CI grants publication permission"],
        },
        {
            "from_authority_class": "generated_navigation_projection",
            "to_authority_class": "private_root_evidence",
            "status": "blocked_without_gate",
            "promotion_requires": ["never expose private-root evidence in public release microcosm"],
            "anti_claims": ["generated projection is private-root equivalence proof"],
        },
        {
            "from_authority_class": "bounded_capability_witness",
            "to_authority_class": "publication_permission",
            "status": "blocked_without_gate",
            "promotion_requires": ["separate publication gate and explicit operator approval"],
            "anti_claims": ["bounded witness grants public release permission"],
        },
    ]
    return {
        "schema_version": "release_authority_lattice_v0",
        "fail_closed_default": True,
        "authority_classes_ref": "release_root_contract.authority_classes",
        "claim_authority_matrix": claim_rows,
        "forbidden_promotions": forbidden_promotions,
        "status": {
            "claim_authority_row_count": len(claim_rows),
            "forbidden_promotion_count": len(forbidden_promotions),
            "authority_matrix_status": "ok",
            "authority_collapse_count": 0,
        },
    }


FORBIDDEN_AUTHORITY_INFERENCES = {
    "benchmark superiority",
    "hosted public availability",
    "anti-claim: hosted public ci has passed",
    "private-root equivalence",
    "public release approval",
    "publication permission",
    "security certification",
    "standards certification",
    "theorem proof",
}


NON_PROMOTING_AUTHORITY_CLASSES = {
    "bounded_capability_witness",
    "evaluator_projection",
    "fail_closed_boundary",
    "generated_navigation_projection",
    "local_boundary_gate",
    "local_clone_evidence",
    "local_contract_projection",
    "local_diagnostic_report",
    "local_fixture_evidence",
}


def _authority_matrix_failures(root: Path, root_contract: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    authority_classes = root_contract.get("authority_classes", {})
    lattice = root_contract.get("authority_lattice", {})
    claim_rows = lattice.get("claim_authority_matrix", [])
    forbidden_promotions = lattice.get("forbidden_promotions", [])
    if lattice.get("fail_closed_default") is not True:
        failures.append({"artifact": "release_root_contract", "reason": "authority lattice must fail closed"})
    if not claim_rows:
        failures.append({"artifact": "release_root_contract", "reason": "missing claim authority matrix"})
    if not forbidden_promotions:
        failures.append({"artifact": "release_root_contract", "reason": "missing forbidden promotion rows"})

    for row in claim_rows:
        if not isinstance(row, dict):
            failures.append({"artifact": "release_root_contract", "reason": "claim authority row is not an object"})
            continue
        claim_id = str(row.get("claim_id", "<missing>"))
        authority_class = str(row.get("authority_class", ""))
        for field in [
            "claim",
            "authority_class",
            "can_infer",
            "cannot_infer",
            "evidence_refs",
            "promotion_requires",
            "authority_boundary",
            "anti_claims",
        ]:
            if not row.get(field):
                failures.append({"claim_id": claim_id, "reason": f"claim authority row missing {field}"})
        if authority_class and authority_class not in authority_classes:
            failures.append({"claim_id": claim_id, "reason": f"unknown authority class {authority_class}"})
        missing_refs = _missing_refs(root, list(row.get("evidence_refs", [])))
        if missing_refs:
            failures.append({"claim_id": claim_id, "missing_evidence_refs": missing_refs})
        can_infer = {str(value).lower() for value in row.get("can_infer", [])}
        cannot_infer = {str(value).lower() for value in row.get("cannot_infer", [])}
        if authority_class in NON_PROMOTING_AUTHORITY_CLASSES:
            collapsed = sorted(FORBIDDEN_AUTHORITY_INFERENCES & can_infer)
            if collapsed:
                failures.append(
                    {
                        "claim_id": claim_id,
                        "reason": "authority collapse: non-promoting class can infer forbidden authority",
                        "collapsed_inferences": collapsed,
                    }
                )
            missing_blockers = sorted(FORBIDDEN_AUTHORITY_INFERENCES & set().union(can_infer, cannot_infer) - cannot_infer)
            if collapsed and missing_blockers:
                failures.append({"claim_id": claim_id, "reason": "forbidden inference lacks cannot_infer blocker"})
        if not row.get("promotion_requires"):
            failures.append({"claim_id": claim_id, "reason": "promotion requires gate is missing"})

    known_classes = set(authority_classes)
    for row in forbidden_promotions:
        if not isinstance(row, dict):
            failures.append({"artifact": "release_root_contract", "reason": "forbidden promotion row is not an object"})
            continue
        from_class = str(row.get("from_authority_class", ""))
        to_class = str(row.get("to_authority_class", ""))
        status = str(row.get("status", ""))
        if from_class not in known_classes or to_class not in known_classes:
            failures.append({"artifact": "release_root_contract", "reason": "forbidden promotion uses unknown authority class"})
        if not status.startswith("blocked") and "fail_closed" not in status:
            failures.append(
                {
                    "artifact": "release_root_contract",
                    "reason": "authority collapse: forbidden promotion is not blocked",
                    "from_authority_class": from_class,
                    "to_authority_class": to_class,
                }
            )
        if not row.get("promotion_requires") or not row.get("anti_claims"):
            failures.append({"artifact": "release_root_contract", "reason": "forbidden promotion missing gate or anti-claim"})
    return failures


def _authority_context_terms(context: str) -> list[str]:
    lower = context.lower()
    return sorted(term for term in AUTHORITY_BOUNDARY_CONTEXT_TERMS if term in lower)


def _authority_context_is_safe(context: str) -> bool:
    strength, _strong_terms, _weak_terms = _authority_boundary_strength(_authority_context_terms(context))
    return strength == "strong"


def _authority_boundary_strength(matched_terms: list[str]) -> tuple[str, list[str], list[str]]:
    strong_terms = sorted(term for term in matched_terms if term in AUTHORITY_STRONG_CONTEXT_TERMS)
    weak_terms = sorted(term for term in matched_terms if term not in AUTHORITY_STRONG_CONTEXT_TERMS)
    if strong_terms:
        return "strong", strong_terms, weak_terms
    if weak_terms:
        return "weak", strong_terms, weak_terms
    return "absent", strong_terms, weak_terms


def _authority_context_for_token(
    rel_path: str,
    lines: list[str],
    line_index: int,
) -> tuple[str, int, list[str], str, list[str], list[str]]:
    radius = (
        AUTHORITY_PUBLIC_SOURCE_CONTEXT_RADIUS
        if rel_path in AUTHORITY_PUBLIC_SOURCE_PATHS
        else AUTHORITY_STRUCTURAL_CONTEXT_RADIUS
    )
    context = "\n".join(lines[max(0, line_index - radius) : line_index + radius + 1])
    matched_terms = _authority_context_terms(context)
    strength, strong_terms, weak_terms = _authority_boundary_strength(matched_terms)
    return context, radius, matched_terms, strength, strong_terms, weak_terms


def _authority_token_owner_boundary(rel_path: str) -> dict[str, str]:
    if rel_path in AUTHORITY_TOKEN_WARNING_BOUNDARIES:
        return dict(AUTHORITY_TOKEN_WARNING_BOUNDARIES[rel_path])
    if rel_path == "src/idea_microcosm/release_root_compiler.py":
        return {
            "owner_class": "release_root_compiler_owned",
            "protection_status": "patchable_now",
            "reentry_condition": "",
            "next_safe_fix": "Patch authority-token scanner rules or source copy, then rebuild release-root compiler artifacts.",
        }
    if rel_path in {BRANCH_GRAPH_PATH, ROOT_CONTRACT_PATH, STD_PYTHON_REPORT_PATH}:
        return {
            "owner_class": "generated_artifact_owned",
            "protection_status": "generated_only",
            "reentry_condition": "Patch the compiler source or upstream source artifact; do not hand-edit generated projections.",
            "next_safe_fix": "Change the source owner that generated this token row, then rebuild release-root compiler artifacts.",
        }
    return {
        "owner_class": "unknown",
        "protection_status": "unknown",
        "reentry_condition": "Classify authority-token ownership before changing public-facing copy.",
        "next_safe_fix": "Add an authority-token ownership boundary in release_root_compiler, then rebuild.",
    }


def _authority_token_standards_debt_status(status: str, protection_status: str) -> str:
    if status == "ok":
        return "fixed"
    if status == "block":
        return "escalated"
    if protection_status == "patchable_now":
        return "patchable"
    if protection_status.startswith("protected") or protection_status == "generated_only":
        return "protected"
    return "unknown"


def _authority_token_classification(rel_path: str, status: str) -> dict[str, Any]:
    boundary = _authority_token_owner_boundary(rel_path)
    protection_status = boundary["protection_status"]
    return {
        "warning_class": "public_safety_token",
        "owner_class": boundary["owner_class"],
        "protection_status": protection_status,
        "reentry_condition": boundary["reentry_condition"],
        "next_safe_fix": boundary["next_safe_fix"],
        "standards_debt_status": _authority_token_standards_debt_status(status, protection_status),
        "anti_claims": AUTHORITY_TOKEN_ROW_ANTI_CLAIMS,
    }


def _authority_warning_is_unclassified(row: dict[str, Any]) -> bool:
    return (
        not row.get("warning_class")
        or not row.get("owner_class")
        or row.get("owner_class") == "unknown"
        or not row.get("protection_status")
        or row.get("protection_status") == "unknown"
        or not row.get("standards_debt_status")
        or row.get("standards_debt_status") == "unknown"
        or not (row.get("reentry_condition") or row.get("next_safe_fix"))
        or not row.get("anti_claims")
    )


def _authority_token_warning_summary(token_rows: list[dict[str, Any]]) -> dict[str, Any]:
    warning_rows = [row for row in token_rows if row.get("status") == "warn"]
    blocker_rows = [row for row in token_rows if row.get("status") == "block"]
    residual_rows = [row for row in token_rows if row.get("status") in {"warn", "block"}]
    protected_rows = [
        row for row in warning_rows if str(row.get("protection_status", "")).startswith("protected")
    ]
    source_patchable_rows = [row for row in warning_rows if row.get("protection_status") == "patchable_now"]
    generated_rows = [row for row in warning_rows if row.get("protection_status") == "generated_only"]
    unclassified_rows = [row for row in warning_rows if _authority_warning_is_unclassified(row)]
    protected_residual_rows = [
        row for row in residual_rows if str(row.get("protection_status", "")).startswith("protected")
    ]
    source_patchable_residual_rows = [
        row for row in residual_rows if row.get("protection_status") == "patchable_now"
    ]
    generated_residual_rows = [
        row for row in residual_rows if row.get("protection_status") == "generated_only"
    ]
    unclassified_residual_rows = [
        row for row in residual_rows if _authority_warning_is_unclassified(row)
    ]
    return {
        "residual_count": len(residual_rows),
        "warning_residual_count": len(warning_rows),
        "blocked_residual_count": len(blocker_rows),
        "protected_warning_count": len(protected_rows),
        "source_patchable_warning_count": len(source_patchable_rows),
        "generated_warning_count": len(generated_rows),
        "unclassified_warning_count": len(unclassified_rows),
        "next_safe_patch_count": len(source_patchable_rows),
        "next_safe_warning_targets": [
            {
                "path": row.get("path"),
                "line": row.get("line"),
                "token": row.get("token"),
                "owner_class": row.get("owner_class"),
                "next_safe_fix": row.get("next_safe_fix"),
            }
            for row in source_patchable_rows
        ],
        "protected_warning_reentry_conditions": [
            {
                "path": row.get("path"),
                "line": row.get("line"),
                "token": row.get("token"),
                "owner_class": row.get("owner_class"),
                "protection_status": row.get("protection_status"),
                "reentry_condition": row.get("reentry_condition"),
            }
            for row in protected_rows
        ],
        "protected_residual_count": len(protected_residual_rows),
        "source_patchable_residual_count": len(source_patchable_residual_rows),
        "generated_residual_count": len(generated_residual_rows),
        "unclassified_residual_count": len(unclassified_residual_rows),
        "next_safe_residual_patch_count": len(source_patchable_residual_rows),
        "next_safe_residual_targets": [
            {
                "path": row.get("path"),
                "line": row.get("line"),
                "token": row.get("token"),
                "status": row.get("status"),
                "owner_class": row.get("owner_class"),
                "next_safe_fix": row.get("next_safe_fix"),
            }
            for row in source_patchable_residual_rows
        ],
        "protected_residual_reentry_conditions": [
            {
                "path": row.get("path"),
                "line": row.get("line"),
                "token": row.get("token"),
                "status": row.get("status"),
                "owner_class": row.get("owner_class"),
                "protection_status": row.get("protection_status"),
                "reentry_condition": row.get("reentry_condition"),
            }
            for row in protected_residual_rows
        ],
        "residual_classification_status": "ok" if not unclassified_residual_rows else "block",
    }


def _public_claims_still_blocked() -> list[dict[str, Any]]:
    return [dict(row) for row in PUBLIC_CLAIMS_STILL_BLOCKED]


def _authority_token_diagnostics(
    root: Path,
    generated_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    scan_inputs: list[tuple[str, str]] = []
    for rel_path in AUTHORITY_SCAN_SOURCE_PATHS:
        path = root / rel_path
        if path.exists():
            scan_inputs.append((rel_path, path.read_text(encoding="utf-8")))
    for rel_path, payload in generated_artifacts.items():
        scan_inputs.append((rel_path, json.dumps(payload, indent=2, sort_keys=True)))

    token_rows: list[dict[str, Any]] = []
    for rel_path, text in scan_inputs:
        lines = text.splitlines()
        for line_index, line in enumerate(lines):
            line_number = line_index + 1
            lower = line.lower()
            for token, authority_class, gate_ref in AUTHORITY_TOKEN_PATTERNS:
                if token not in lower:
                    continue
                (
                    _context,
                    context_radius,
                    matched_terms,
                    boundary_strength,
                    strong_terms,
                    weak_terms,
                ) = _authority_context_for_token(rel_path, lines, line_index)
                status = {
                    "strong": "ok",
                    "weak": "warn",
                    "absent": "block",
                }[boundary_strength]
                context_class = {
                    "strong": "fail_closed_or_anti_claim",
                    "weak": "weak_boundary_signal",
                    "absent": "unsafe_promotion_candidate",
                }[boundary_strength]
                row = {
                    "path": rel_path,
                    "line": line_number,
                    "token": token,
                    "context_radius_lines": context_radius,
                    "context_class": context_class,
                    "boundary_strength": boundary_strength,
                    "matched_boundary_terms": matched_terms,
                    "strong_boundary_terms": strong_terms,
                    "weak_boundary_terms": weak_terms,
                    "authority_class": authority_class,
                    "gate_ref": gate_ref,
                    "evidence_ref": gate_ref if boundary_strength == "strong" else "",
                    "anti_claim_ref": "release_root_contract.anti_claims" if boundary_strength == "strong" else "",
                    "status": status,
                    "reason": (
                        "token is paired with fail-closed, anti-claim, cannot-claim, or promotion-required context in its scan window"
                        if boundary_strength == "strong"
                        else (
                            "token has only weak boundary wording in its scan window; keep fail-closed and inspect before public copy promotion"
                            if boundary_strength == "weak"
                            else "token appears as public-promotion language without a local authority boundary"
                        )
                    ),
                }
                if status != "ok":
                    row.update(_authority_token_classification(rel_path, status))
                token_rows.append(row)

    blocker_count = sum(1 for row in token_rows if row["status"] == "block")
    warning_count = sum(1 for row in token_rows if row["status"] == "warn")
    ok_count = sum(1 for row in token_rows if row["status"] == "ok")
    strong_boundary_count = sum(1 for row in token_rows if row["boundary_strength"] == "strong")
    weak_boundary_count = sum(1 for row in token_rows if row["boundary_strength"] == "weak")
    absent_boundary_count = sum(1 for row in token_rows if row["boundary_strength"] == "absent")
    warning_summary = _authority_token_warning_summary(token_rows)
    public_claims_still_blocked = _public_claims_still_blocked()
    return {
        "schema_version": "release_authority_token_diagnostics_v0",
        "scanned_paths": [path for path, _text in scan_inputs],
        "token_rows": token_rows,
        "public_claims_still_blocked": public_claims_still_blocked,
        "summary": {
            "scanned_path_count": len(scan_inputs),
            "token_count": len(token_rows),
            "ok_count": ok_count,
            "warning_count": warning_count,
            "blocker_count": blocker_count,
            "strong_boundary_count": strong_boundary_count,
            "weak_boundary_count": weak_boundary_count,
            "absent_boundary_count": absent_boundary_count,
            "unsafe_promotion_count": blocker_count,
            "fail_closed_status": "fail_closed" if blocker_count == 0 else "block",
            "blocked_public_claim_count": len(public_claims_still_blocked),
            "blocked_authority_classes": sorted(
                {str(row["authority_class"]) for row in public_claims_still_blocked}
            ),
            **warning_summary,
        },
        "anti_claims": AUTHORITY_TOKEN_ROW_ANTI_CLAIMS,
    }


def _attach_authority_token_diagnostics(
    std_report: dict[str, Any],
    root_contract: dict[str, Any],
    branch_graph: dict[str, Any],
    authority_diagnostics: dict[str, Any],
) -> None:
    summary = authority_diagnostics.get("summary", {})
    std_report["authority_token_diagnostics"] = authority_diagnostics
    std_report["summary"]["authority_warning_count"] = int(summary.get("warning_count", 0))
    std_report["summary"]["authority_token_blocker_count"] = int(summary.get("blocker_count", 0))
    std_report["summary"]["unsafe_promotion_count"] = int(summary.get("unsafe_promotion_count", 0))
    std_report["summary"]["authority_strong_boundary_count"] = int(summary.get("strong_boundary_count", 0))
    std_report["summary"]["authority_weak_boundary_count"] = int(summary.get("weak_boundary_count", 0))
    std_report["summary"]["authority_absent_boundary_count"] = int(summary.get("absent_boundary_count", 0))
    std_report["summary"]["authority_residual_count"] = int(summary.get("residual_count", 0))
    std_report["summary"]["authority_blocked_residual_count"] = int(summary.get("blocked_residual_count", 0))
    std_report["summary"]["authority_protected_warning_count"] = int(summary.get("protected_warning_count", 0))
    std_report["summary"]["authority_source_patchable_warning_count"] = int(
        summary.get("source_patchable_warning_count", 0)
    )
    std_report["summary"]["authority_generated_warning_count"] = int(summary.get("generated_warning_count", 0))
    std_report["summary"]["authority_unclassified_warning_count"] = int(summary.get("unclassified_warning_count", 0))
    std_report["summary"]["authority_next_safe_patch_count"] = int(summary.get("next_safe_patch_count", 0))
    std_report["summary"]["authority_next_safe_warning_targets"] = summary.get("next_safe_warning_targets", [])
    std_report["summary"]["authority_protected_warning_reentry_conditions"] = summary.get(
        "protected_warning_reentry_conditions", []
    )
    std_report["summary"]["authority_protected_residual_count"] = int(summary.get("protected_residual_count", 0))
    std_report["summary"]["authority_source_patchable_residual_count"] = int(
        summary.get("source_patchable_residual_count", 0)
    )
    std_report["summary"]["authority_generated_residual_count"] = int(summary.get("generated_residual_count", 0))
    std_report["summary"]["authority_unclassified_residual_count"] = int(summary.get("unclassified_residual_count", 0))
    std_report["summary"]["authority_next_safe_residual_patch_count"] = int(
        summary.get("next_safe_residual_patch_count", 0)
    )
    std_report["summary"]["authority_next_safe_residual_targets"] = summary.get("next_safe_residual_targets", [])
    std_report["summary"]["authority_protected_residual_reentry_conditions"] = summary.get(
        "protected_residual_reentry_conditions", []
    )
    std_report["summary"]["authority_residual_classification_status"] = summary.get("residual_classification_status")
    std_report["summary"]["blocked_public_claim_count"] = int(summary.get("blocked_public_claim_count", 0))
    std_report["summary"]["blocked_authority_classes"] = summary.get("blocked_authority_classes", [])
    std_report["summary"]["public_claims_still_blocked"] = authority_diagnostics.get(
        "public_claims_still_blocked",
        [],
    )
    if (
        std_report["summary"].get("unclassified_warning_count", 0) == 0
        and std_report["summary"].get("authority_unclassified_residual_count", 0) == 0
        and summary.get("blocker_count", 0) == 0
    ):
        std_report["summary"]["standards_closure_status"] = "ok"
    else:
        std_report["summary"]["standards_closure_status"] = "block"

    root_contract["authority_token_diagnostics"] = {
        "report_ref": STD_PYTHON_REPORT_PATH,
        "summary": summary,
        "public_claims_still_blocked": authority_diagnostics.get("public_claims_still_blocked", []),
        "anti_claims": authority_diagnostics.get("anti_claims", []),
    }
    root_contract["status"]["authority_token_blocker_count"] = int(summary.get("blocker_count", 0))
    root_contract["status"]["unsafe_promotion_count"] = int(summary.get("unsafe_promotion_count", 0))
    root_contract["status"]["authority_warning_count"] = int(summary.get("warning_count", 0))
    root_contract["status"]["authority_weak_boundary_count"] = int(summary.get("weak_boundary_count", 0))
    root_contract["status"]["authority_unclassified_warning_count"] = int(summary.get("unclassified_warning_count", 0))
    root_contract["status"]["authority_next_safe_patch_count"] = int(summary.get("next_safe_patch_count", 0))
    root_contract["status"]["authority_residual_count"] = int(summary.get("residual_count", 0))
    root_contract["status"]["authority_unclassified_residual_count"] = int(
        summary.get("unclassified_residual_count", 0)
    )
    root_contract["status"]["authority_next_safe_residual_patch_count"] = int(
        summary.get("next_safe_residual_patch_count", 0)
    )
    root_contract["status"]["blocked_public_claim_count"] = int(summary.get("blocked_public_claim_count", 0))
    root_contract["status"]["authority_token_status"] = summary.get("fail_closed_status")

    branch_graph["compliance_diagnostics"]["authority_token_status"] = summary.get("fail_closed_status")
    branch_graph["compliance_diagnostics"]["authority_token_blocker_count"] = int(summary.get("blocker_count", 0))
    branch_graph["compliance_diagnostics"]["unsafe_promotion_count"] = int(summary.get("unsafe_promotion_count", 0))
    branch_graph["compliance_diagnostics"]["authority_warning_count"] = int(summary.get("warning_count", 0))
    branch_graph["compliance_diagnostics"]["authority_weak_boundary_count"] = int(summary.get("weak_boundary_count", 0))
    branch_graph["compliance_diagnostics"]["authority_unclassified_warning_count"] = int(
        summary.get("unclassified_warning_count", 0)
    )
    branch_graph["compliance_diagnostics"]["authority_next_safe_patch_count"] = int(summary.get("next_safe_patch_count", 0))
    branch_graph["compliance_diagnostics"]["authority_residual_count"] = int(summary.get("residual_count", 0))
    branch_graph["compliance_diagnostics"]["authority_unclassified_residual_count"] = int(
        summary.get("unclassified_residual_count", 0)
    )
    branch_graph["compliance_diagnostics"]["authority_next_safe_residual_patch_count"] = int(
        summary.get("next_safe_residual_patch_count", 0)
    )
    branch_graph["compliance_diagnostics"]["blocked_public_claim_count"] = int(
        summary.get("blocked_public_claim_count", 0)
    )
    branch_graph["compliance_diagnostics"]["blocked_authority_classes"] = summary.get(
        "blocked_authority_classes",
        [],
    )
    branch_graph["compliance_diagnostics"]["standards_closure_status"] = std_report["summary"].get("standards_closure_status")
    branch_graph["compliance_diagnostics"]["unclassified_warning_count"] = std_report["summary"].get("unclassified_warning_count", 0)
    branch_graph["status"]["standards_closure_status"] = std_report["summary"].get("standards_closure_status")
    branch_graph["status"]["unclassified_warning_count"] = std_report["summary"].get("unclassified_warning_count", 0)


def build_std_python_report(root: Path, generated_at: str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Build the local Python standards report that turns code files into navigable repair rows.
    - Guarantee: Returns file_rows with compliance diagnostics, owner boundaries, route atoms, and next safe fixes.
    - Fails: Syntax errors become block rows; missing report classification becomes validator failure.
    - When-needed: Open when std_python_compliance_report needs schema changes, route-atom projection, or local standard resolution fixes.
    - Escalates-to: codex/standards/std_python.py; microcosms/specimen_suite/std_python_compliance_report.json
    """
    standard_resolution = _resolve_std_python_standard(root)
    standard_abs = root / STD_PYTHON_STANDARD_PATH if standard_resolution["mode"] == "microcosm_local" else root.parent / STD_PYTHON_STANDARD_PATH
    tests_text, test_source_files = _release_test_sources(root)
    python_paths = _python_files(root)
    rows = [_python_row(root, path, tests_text) for path in python_paths]
    scope_rows = [scope_row for path in python_paths for scope_row in _scope_rows_for_python(root, path)]
    scope_rows_by_path: dict[str, list[dict[str, Any]]] = {}
    for scope_row in scope_rows:
        scope_rows_by_path.setdefault(str(scope_row["path"]), []).append(scope_row)
    for row in rows:
        row_scope_rows = scope_rows_by_path.get(str(row["path"]), [])
        row["scope_count"] = len(row_scope_rows)
        row["public_scope_count"] = sum(1 for scope_row in row_scope_rows if scope_row["scope_kind"] != "module")
        row["scope_row_refs"] = [
            f"{STD_PYTHON_REPORT_PATH}::scope_rows[scope_id={scope_row['scope_id']}]"
            for scope_row in row_scope_rows
        ]
    navigation_index = _scope_navigation_index(scope_rows, generated_at)
    excluded = sorted(str(path.relative_to(root)) for path in root.rglob("*.pyc"))
    warning_count = sum(1 for row in rows if row["std_python_status"] == "warn")
    blocker_count = sum(1 for row in rows if row["std_python_status"] == "block")
    diagnostic_kind_counts = _diagnostic_kind_counts(rows)
    navigation_summary = _navigation_population_summary(rows)
    repair_plan = _build_repair_plan(rows)
    repair_plan_kinds = {row["diagnostic_kind"] for row in repair_plan}
    missing_repair_kinds = sorted(set(diagnostic_kind_counts) - repair_plan_kinds)
    closure_summary = _standards_closure_summary(rows)
    next_fix = _std_python_next_fix(
        warning_count=warning_count,
        blocker_count=blocker_count,
        protected_warning_count=int(closure_summary["protected_warning_count"]),
        source_patchable_warning_count=int(closure_summary["source_patchable_warning_count"]),
        unclassified_warning_count=int(closure_summary["unclassified_warning_count"]),
    )
    report = {
        "schema_version": "std_python_compliance_report_v0",
        "standard_ref": [
            "codex/standards/std_python.py",
            "codex/standards/std_python.py::PYTHON_STANDARD.microcosm_navigation_contract",
            "codex/standards/std_python_scope_index.json",
            "codex/standards/std_python_compliance_coverage.json",
        ],
        "standard_resolution": standard_resolution,
        "generated_at": generated_at,
        "generated_by": _generated_by(
            "src/idea_microcosm/release_root_compiler.py::build_std_python_report",
            ["codex/standards/std_python.py", "src/idea_microcosm", "probes", "tests"],
        ),
        "scope": {
            "release_root": "self-indexing-cognitive-substrate",
            "release_root_public_boundary": (
                "manifest-included public-safe synthetic microcosm root, not a private source grant"
            ),
            "scanned_python_files": [row["path"] for row in rows],
            "direct_test_source_files": test_source_files,
            "test_reference_policy": "all tests/test_*.py files are searched for direct module references; CLI entrypoints, probes, and package markers have command/import coverage exceptions",
            "excluded_python_files": excluded,
            "exclusion_reasons": {"__pycache__": "compiled bytecode is not source"},
        },
        "summary": {
            "scanned_count": len(rows),
            "compliant_count": sum(1 for row in rows if row["std_python_status"] == "pass"),
            "warning_count": warning_count,
            "blocker_count": blocker_count,
            "public_safe_count": sum(1 for row in rows if row["public_safe_status"] == "pass"),
            "cli_entrypoint_count": sum(1 for row in rows if row["role"] == "cli_entrypoint"),
            "typed_function_count": sum(1 for row in rows if row["type_hint_status"] == "pass"),
            "missing_test_count": sum(1 for row in rows if row["test_status"] == "warn"),
            "missing_metadata_count": sum(
                1
                for row in rows
                if any(diag.get("kind") == "module_tags" for diag in row.get("diagnostics", []))
            ),
            "dependency_warning_count": sum(1 for row in rows if row["dependency_status"] == "warn"),
            "diagnostic_kind_counts": diagnostic_kind_counts,
            "diagnostic_warning_kind_counts": _diagnostic_kind_counts(rows, status="warn"),
            "diagnostic_blocker_kind_counts": _diagnostic_kind_counts(rows, status="block"),
            "warning_count_by_branch": _branch_warning_counts(rows),
            "scope_row_count": len(scope_rows),
            "scope_navigation_cluster_count": navigation_index["summary"]["cluster_count"],
            "scope_navigation_flag_count": navigation_index["summary"]["flag_count"],
            "scope_navigation_card_count": navigation_index["summary"]["card_count"],
            "scope_navigation_function_or_method_count": navigation_index["summary"]["function_or_method_count"],
            "scope_navigation_authored_route_atom_count": navigation_index["summary"]["authored_route_atom_scope_count"],
            "scope_navigation_inferred_leaf_entry_count": navigation_index["summary"]["inferred_leaf_entry_scope_count"],
            "scope_navigation_inferred_support_route_count": navigation_index["summary"]["inferred_support_route_scope_count"],
            "scope_navigation_derived_fallback_count": navigation_index["summary"]["derived_ast_fallback_scope_count"],
            **navigation_summary,
            **closure_summary,
            "authority_warning_count": 0,
            "authority_token_blocker_count": 0,
            "unsafe_promotion_count": 0,
            "authority_strong_boundary_count": 0,
            "authority_weak_boundary_count": 0,
            "authority_absent_boundary_count": 0,
            "authority_residual_count": 0,
            "authority_blocked_residual_count": 0,
            "authority_protected_warning_count": 0,
            "authority_source_patchable_warning_count": 0,
            "authority_generated_warning_count": 0,
            "authority_unclassified_warning_count": 0,
            "authority_next_safe_patch_count": 0,
            "authority_next_safe_warning_targets": [],
            "authority_protected_warning_reentry_conditions": [],
            "authority_protected_residual_count": 0,
            "authority_source_patchable_residual_count": 0,
            "authority_generated_residual_count": 0,
            "authority_unclassified_residual_count": 0,
            "authority_next_safe_residual_patch_count": 0,
            "authority_next_safe_residual_targets": [],
            "authority_protected_residual_reentry_conditions": [],
            "authority_residual_classification_status": "ok",
            "blocked_public_claim_count": 0,
            "blocked_authority_classes": [],
            "public_claims_still_blocked": [],
            "repair_plan_status": "actionable" if not missing_repair_kinds else "incomplete",
            "repair_plan_missing_kind_count": len(missing_repair_kinds),
            "next_fix": next_fix,
            "next_owner": "src/idea_microcosm/release_root_compiler.py",
        },
        "file_rows": rows,
        "scope_rows": scope_rows,
        "navigation_index": navigation_index,
        "repair_plan": repair_plan,
        "repair_plan_missing_kinds": missing_repair_kinds,
        "anti_claims": [
            "local release-root standards diagnostics only",
            "not private-root-wide compliance",
            "not security certification",
            "not public release approval",
            "not a substitute for hosted CI",
        ],
    }
    report["status"] = "block" if blocker_count else "warn" if warning_count else "ok"
    if standard_abs.exists():
        report["generated_by"]["standard_source"] = str(STD_PYTHON_STANDARD_PATH)
        report["generated_by"]["standard_source_resolution"] = standard_resolution["mode"]
        report["generated_by"]["standard_source_hash"] = _hash_file(standard_abs)
    return report


def build_release_root_contract(root: Path, generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": "release_root_contract_v0",
        "generated_at": generated_at,
        "selected_contribution": "self_indexing_cognitive_substrate",
        "authority_posture": "public_safe_local_release_microcosm_not_private_root_or_publication_authority",
        "generated_by": _generated_by(
            "src/idea_microcosm/release_root_compiler.py::build_release_root_contract",
            [
                "microcosms/specimen_suite/macrocosm_contribution_assay.json",
                "microcosms/specimen_suite/release_microcosm_ontology.json",
                "microcosms/public_release_package_manifest_gate/release_authority_handshake.json",
            ],
        ),
        "constitutional_rules": [
            {
                "rule_id": "claim_routes_to_evidence_or_boundary",
                "statement": "Every public-facing claim must carry evidence refs or anti-claims and an authority boundary.",
                "validator_ref": "release_root_compiler.validate_release_root_artifacts",
                "evidence_refs": ["microcosms/specimen_suite/claim_inference_map.json", BRANCH_GRAPH_PATH],
                "anti_claims": ["claim wording alone is evidence"],
            },
            {
                "rule_id": "projection_is_not_authority",
                "statement": "Generated artifacts navigate and prove builder behavior; they do not replace source authority.",
                "validator_ref": "release_root_compiler.validate_release_root_artifacts",
                "evidence_refs": [BRANCH_GRAPH_PATH, STD_PYTHON_REPORT_PATH],
                "anti_claims": ["generated JSON is source authority"],
            },
            {
                "rule_id": "authority_never_collapses",
                "statement": "Local proof, hosted proof, publication permission, and private-root equivalence remain separate classes.",
                "validator_ref": "release_root_compiler.validate_release_root_artifacts",
                "evidence_refs": ["microcosms/public_release_package_manifest_gate/release_authority_handshake.json"],
                "anti_claims": ["local fixture pass grants publication permission"],
            },
            {
                "rule_id": "public_release_fail_closed",
                "statement": "Absent hosted, rights, disclosure, citation, recipient, or publication proof keeps public claims blocked.",
                "validator_ref": "release_root_compiler.validate_release_root_artifacts",
                "evidence_refs": ["release/publication_gate.json", "microcosms/hosted_public_ci_workflow_gate/workflow_gate.json"],
                "anti_claims": ["no evidence means approved"],
            },
            {
                "rule_id": "standards_are_executable",
                "statement": "Standards must produce diagnostics, repair rows, or validation checks.",
                "validator_ref": "release_root_compiler.validate_release_root_artifacts",
                "evidence_refs": [STD_PYTHON_REPORT_PATH, "microcosms/executable_grammar_metabolism/grammar_board.json"],
                "anti_claims": ["standard prose alone enforces behavior"],
            },
            {
                "rule_id": "proof_tail_refresh_is_source_owned",
                "statement": "Proof-tail artifact groups must route through source-owned builder commands, validator refs, anti-claims, and public-boundary text.",
                "validator_ref": "release_root_compiler.validate_release_root_artifacts",
                "evidence_refs": [BRANCH_GRAPH_PATH + "::proof_tail_refresh_plan", RECEIPT_PATH],
                "anti_claims": ["stale proof-tail artifacts are acceptable without owner commands"],
            },
            {
                "rule_id": "work_metabolism_is_durable",
                "statement": "Intent becomes work only through claims, mutations, receipts, closeout, and residual routing.",
                "validator_ref": "release_root_compiler.validate_release_root_artifacts",
                "evidence_refs": ["microcosms/concurrency_mission_control/work_metabolism_bridge.json"],
                "anti_claims": ["chat status is durable closeout"],
            },
        ],
        "authority_classes": _authority_class_rows(),
        "authority_lattice": _authority_lattice(),
        "projection_rules": {
            "generated_artifact_requires": {
                "source_owner": True,
                "builder_command": True,
                "source_refs": True,
                "receipt_ref": True,
                "projection_not_authority_flag": True,
                "anti_claims": True,
            }
        },
        "branch_rules": {
            "core_branch_requires": {
                "command": True,
                "evidence_ref": True,
                "standard_ref": True,
                "anti_claim": True,
                "next_gap": True,
            },
            "support_branch_requires": {
                "role": True,
                "evidence_or_boundary": True,
            },
            "exemplar_branch_requires": {
                "bounded_scope": True,
                "not_identity": True,
            },
            "boundary_branch_requires": {
                "fail_closed_default": True,
            },
        },
        "status": {
            "missing_rule_ref_count": 0,
            "branch_rule_violation_count": 0,
            "authority_collapse_count": 0,
            "projection_authority_violation_count": 0,
            "authority_matrix_status": "ok",
            "claim_authority_row_count": 5,
            "forbidden_promotion_count": 5,
            "std_python_blocker_count": 0,
            "next_gap": "consume validator.release_root_compiler in package and cold-start routes while hosted-public proof remains fail-closed",
            "next_owner": "public_release_package_manifest_gate_microcosm",
        },
        "anti_claims": ROOT_ANTI_CLAIMS,
    }


def build_release_branch_graph(root: Path, generated_at: str, std_report: dict[str, Any]) -> dict[str, Any]:
    branches = _branch_rows()
    trunks = _trunks()
    mission_threads = _mission_threads()
    mission_thread_routes = _mission_thread_routes(mission_threads, branches)
    proof_tail_refresh_plan = _proof_tail_refresh_plan(root, generated_at)
    all_evidence_refs = [ref for row in branches for ref in row.get("evidence_refs", [])]
    all_standard_refs = [ref for row in branches for ref in row.get("standards_refs", [])]
    all_anti_claims = [claim for row in branches for claim in row.get("anti_claims", [])]
    missing_refs = _missing_refs(root, all_evidence_refs)
    fail_closed_gate_count = sum(1 for row in branches if row["role"] == "boundary")
    std_summary = std_report.get("summary", {})
    std_next_gap = _std_python_next_fix(
        warning_count=int(std_summary.get("warning_count", 0)),
        blocker_count=int(std_summary.get("blocker_count", 0)),
        protected_warning_count=int(std_summary.get("protected_warning_count", 0)),
        source_patchable_warning_count=int(std_summary.get("source_patchable_warning_count", 0)),
        unclassified_warning_count=int(std_summary.get("unclassified_warning_count", 0)),
    )
    return {
        "schema_version": "release_microcosm_branch_graph_v1",
        "generated_at": generated_at,
        "selected_contribution": "self_indexing_cognitive_substrate",
        "generated_by": _generated_by(
            "src/idea_microcosm/release_root_compiler.py::build_release_branch_graph",
            [
                "microcosms/specimen_suite/macrocosm_contribution_assay.json",
                "microcosms/specimen_suite/release_microcosm_ontology.json",
                "microcosms/specimen_suite/quality_delta_board.json",
                ROOT_CONTRACT_PATH,
                STD_PYTHON_REPORT_PATH,
            ],
        ),
        "root_summary": {
            "layman_summary": "A small release root that reads itself, routes work, enforces standards, proves local behavior, and keeps public claims fail-closed.",
            "technical_summary": "A branch graph over release microcosms, root authority contract, std_python diagnostics, mission threads, entry tracks, evidence refs, standards refs, anti-claims, and next gaps.",
            "first_command": BUILDER_COMMAND,
            "first_evidence_ref": BRANCH_GRAPH_PATH,
            "not_claimed": ROOT_ANTI_CLAIMS,
            "next_gap": "consume branch graph in cold-start README/skill copy after sibling cold-entry patch is stable",
        },
        "trunks": trunks,
        "branches": branches,
        "mission_threads": mission_threads,
        "mission_thread_routes": mission_thread_routes,
        "proof_tail_refresh_plan": proof_tail_refresh_plan,
        "entry_tracks": _entry_tracks(),
        "compliance_diagnostics": {
            "std_python_status": std_report.get("status"),
            "microcosm_schema_status": "ok",
            "concept_graph_status": "sibling_owned_consumed_as_evidence",
            "branch_graph_status": "ok" if not missing_refs else "warn",
            "mission_thread_route_status": (
                "ok"
                if mission_thread_routes
                and all(route.get("route_status") == "ok" for route in mission_thread_routes)
                else "warn"
            ),
            "receipt_status": "ok",
            "public_boundary_status": "fail_closed",
            "projection_authority_status": "projection_not_authority",
            "root_contract_authority_matrix_status": "ok",
            "proof_tail_refresh_status": proof_tail_refresh_plan["status"],
            "std_python_repair_plan_status": std_summary.get("repair_plan_status"),
            "std_python_scope_row_count": std_summary.get("scope_row_count", 0),
            "std_python_scope_navigation_card_count": std_summary.get("scope_navigation_card_count", 0),
            "std_python_scope_navigation_function_or_method_count": std_summary.get("scope_navigation_function_or_method_count", 0),
            "protected_warning_count": std_summary.get("protected_warning_count", 0),
            "source_patchable_warning_count": std_summary.get("source_patchable_warning_count", 0),
            "next_safe_patch_count": std_summary.get("next_safe_patch_count", 0),
            "missing_ref_count": len(missing_refs),
            "proof_tail_missing_ref_count": proof_tail_refresh_plan["missing_ref_count"],
            "blocker_count": std_summary.get("blocker_count", 0),
            "warning_count": std_summary.get("warning_count", 0),
        },
        "status": {
            "branch_count": len(branches),
            "trunk_count": len(trunks),
            "mission_thread_count": len(mission_threads),
            "mission_thread_route_count": len(mission_thread_routes),
            "mission_thread_step_count": sum(route.get("step_count", 0) for route in mission_thread_routes),
            "command_count": len({row["what_to_run"] for row in branches} | {row["first_command"] for row in trunks}),
            "evidence_ref_count": len(all_evidence_refs),
            "standard_ref_count": len(all_standard_refs),
            "anti_claim_count": len(all_anti_claims),
            "fail_closed_gate_count": fail_closed_gate_count,
            "missing_ref_count": len(missing_refs),
            "proof_tail_refresh_group_count": proof_tail_refresh_plan["group_count"],
            "proof_tail_missing_ref_count": proof_tail_refresh_plan["missing_ref_count"],
            "cold_entry_status": "sibling_owned_consumed_not_overwritten",
            "standards_status": "diagnostic_warn" if std_report.get("status") == "warn" else std_report.get("status"),
            "next_gap": std_next_gap,
            "next_owner": "src/idea_microcosm/release_root_compiler.py",
        },
        "missing_refs": missing_refs,
        "anti_claims": ROOT_ANTI_CLAIMS,
    }


def validate_release_root_artifacts(
    root: Path,
    branch_graph: dict[str, Any],
    root_contract: dict[str, Any],
    std_report: dict[str, Any],
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for artifact_name, artifact in [
        ("release_branch_graph", branch_graph),
        ("release_root_contract", root_contract),
        ("std_python_compliance_report", std_report),
    ]:
        generated_by = artifact.get("generated_by", {})
        if generated_by.get("projection_not_authority") is not True:
            failures.append({"artifact": artifact_name, "reason": "generated projection must declare projection_not_authority"})
        for field in ["source_owner", "builder_command", "source_refs"]:
            if not generated_by.get(field):
                failures.append({"artifact": artifact_name, "reason": f"missing generated_by.{field}"})

    proof_tail_plan = branch_graph.get("proof_tail_refresh_plan", {})
    if not isinstance(proof_tail_plan, dict) or not proof_tail_plan:
        failures.append({"artifact": "release_branch_graph", "reason": "missing proof-tail refresh plan"})
    else:
        if proof_tail_plan.get("schema_version") != "release_proof_tail_refresh_plan_v0":
            failures.append({"artifact": "release_branch_graph", "reason": "invalid proof-tail refresh plan schema"})
        if proof_tail_plan.get("projection_not_authority") is not True:
            failures.append({"artifact": "release_branch_graph", "reason": "proof-tail refresh plan must declare projection_not_authority"})
        if not proof_tail_plan.get("validation_command"):
            failures.append({"artifact": "release_branch_graph", "reason": "proof-tail refresh plan missing validation command"})
        plan_rows = proof_tail_plan.get("rows", [])
        expected_group_ids = {str(row["group_id"]) for row in PROOF_TAIL_REFRESH_GROUPS}
        actual_group_ids = {
            str(row.get("group_id"))
            for row in plan_rows
            if isinstance(row, dict) and row.get("group_id")
        }
        missing_group_ids = sorted(expected_group_ids - actual_group_ids)
        if missing_group_ids:
            failures.append({"artifact": "release_branch_graph", "missing_proof_tail_group_ids": missing_group_ids})
        observed_missing_ref_count = 0
        for row in plan_rows:
            if not isinstance(row, dict):
                failures.append({"artifact": "release_branch_graph", "reason": "proof-tail refresh row is not an object"})
                continue
            group_id = row.get("group_id", "<missing>")
            for field in [
                "group_id",
                "owner_command",
                "artifact_refs",
                "validator_refs",
                "public_boundary",
                "repair_boundary",
                "anti_claims",
            ]:
                if not row.get(field):
                    failures.append({"group_id": group_id, "reason": f"proof-tail refresh row missing {field}"})
            if row.get("projection_not_authority") is not True:
                failures.append({"group_id": group_id, "reason": "proof-tail refresh row must declare projection_not_authority"})
            missing_refs = _missing_refs(root, list(row.get("artifact_refs", [])))
            observed_missing_ref_count += len(missing_refs)
            if missing_refs:
                failures.append({"group_id": group_id, "missing_proof_tail_refs": missing_refs})
            if row.get("status") != "ok":
                failures.append({"group_id": group_id, "reason": "proof-tail refresh row status must be ok"})
        plan_group_count = proof_tail_plan.get("group_count")
        if int(plan_group_count if plan_group_count is not None else -1) != len(plan_rows):
            failures.append({"artifact": "release_branch_graph", "reason": "proof-tail refresh group count mismatch"})
        plan_missing_ref_count = proof_tail_plan.get("missing_ref_count")
        if int(plan_missing_ref_count if plan_missing_ref_count is not None else -1) != observed_missing_ref_count:
            failures.append({"artifact": "release_branch_graph", "reason": "proof-tail refresh missing-ref count mismatch"})
        if proof_tail_plan.get("status") != "ok":
            failures.append({"artifact": "release_branch_graph", "reason": "proof-tail refresh plan status must be ok"})

    branch_ids = {row.get("branch_id") for row in branch_graph.get("branches", []) if isinstance(row, dict)}
    for branch in branch_graph.get("branches", []):
        if not isinstance(branch, dict):
            failures.append({"artifact": "release_branch_graph", "reason": "branch row is not an object"})
            continue
        branch_id = branch.get("branch_id", "<missing>")
        if branch.get("role") == "core":
            for field in CORE_BRANCH_REQUIREMENTS:
                if not branch.get(field):
                    failures.append({"branch_id": branch_id, "reason": f"core branch missing {field}"})
        if branch.get("role") == "boundary" and "fail" not in json.dumps(branch).lower():
            failures.append({"branch_id": branch_id, "reason": "boundary branch must preserve fail-closed language"})
        missing_refs = _missing_refs(root, list(branch.get("evidence_refs", [])))
        if missing_refs:
            failures.append({"branch_id": branch_id, "missing_evidence_refs": missing_refs})
    failures.extend(_expected_output_failures(branch_graph))

    mission_threads = branch_graph.get("mission_threads", [])
    thread_by_id: dict[str, dict[str, Any]] = {}
    for thread in mission_threads:
        thread_id = thread.get("thread_id", "<missing>")
        if isinstance(thread_id, str) and thread_id:
            thread_by_id[thread_id] = thread
        ids = thread.get("branch_ids", [])
        if len(ids) < 2:
            failures.append({"thread_id": thread_id, "reason": "mission thread needs at least two branches"})
        if not thread.get("start_command"):
            failures.append({"thread_id": thread_id, "reason": "mission thread missing start command"})
        unknown = [branch_id for branch_id in ids if branch_id not in branch_ids]
        if unknown:
            failures.append({"thread_id": thread_id, "unknown_branch_ids": unknown})

    mission_thread_routes = branch_graph.get("mission_thread_routes", [])
    if not mission_thread_routes:
        failures.append({"artifact": "release_branch_graph", "reason": "missing mission thread routes"})
    if len(mission_thread_routes) != len(mission_threads):
        failures.append({"artifact": "release_branch_graph", "reason": "mission thread route count mismatch"})

    for route in mission_thread_routes:
        if not isinstance(route, dict):
            failures.append({"artifact": "release_branch_graph", "reason": "mission thread route is not an object"})
            continue
        thread_id = str(route.get("thread_id", "<missing>"))
        source_thread = thread_by_id.get(thread_id)
        if source_thread is None:
            failures.append({"thread_id": thread_id, "reason": "mission thread route has no source thread"})
        if route.get("projection_not_authority") is not True:
            failures.append({"thread_id": thread_id, "reason": "mission thread route must declare projection_not_authority"})
        if route.get("route_status") != "ok":
            failures.append({"thread_id": thread_id, "reason": "mission thread route status must be ok"})
        if not route.get("start_command"):
            failures.append({"thread_id": thread_id, "reason": "mission thread route missing start command"})
        if not route.get("route_boundary"):
            failures.append({"thread_id": thread_id, "reason": "mission thread route missing authority boundary"})

        proof_sequence = route.get("proof_sequence", [])
        if len(proof_sequence) < 2:
            failures.append({"thread_id": thread_id, "reason": "mission thread route needs at least two proof steps"})
        if route.get("step_count") != len(proof_sequence):
            failures.append({"thread_id": thread_id, "reason": "mission thread route step count mismatch"})
        if source_thread is not None:
            expected_ids = list(source_thread.get("branch_ids", []))
            actual_ids = [step.get("branch_id") for step in proof_sequence if isinstance(step, dict)]
            if actual_ids != expected_ids:
                failures.append({"thread_id": thread_id, "reason": "mission thread route does not match source branch order"})

        for step in proof_sequence:
            if not isinstance(step, dict):
                failures.append({"thread_id": thread_id, "reason": "mission thread route step is not an object"})
                continue
            step_branch_id = step.get("branch_id", "<missing>")
            if step_branch_id not in branch_ids:
                failures.append({"thread_id": thread_id, "unknown_route_branch_id": step_branch_id})
            for field in [
                "command",
                "expected_output",
                "evidence_refs",
                "standards_refs",
                "authority_class",
                "authority_boundary",
                "anti_claims",
                "next_branch",
                "next_gap",
            ]:
                if not step.get(field):
                    failures.append(
                        {
                            "thread_id": thread_id,
                            "branch_id": step_branch_id,
                            "reason": f"mission thread route step missing {field}",
                        }
                    )
            missing_refs = _missing_refs(root, list(step.get("evidence_refs", [])))
            if missing_refs:
                failures.append(
                    {
                        "thread_id": thread_id,
                        "branch_id": step_branch_id,
                        "missing_evidence_refs": missing_refs,
                    }
                )

    authority_classes = root_contract.get("authority_classes", {})
    for class_id in ["local_fixture_evidence", "local_clone_evidence", "hosted_public_evidence", "publication_permission", "private_root_evidence"]:
        if class_id not in authority_classes:
            failures.append({"artifact": "release_root_contract", "reason": f"missing authority class {class_id}"})
    if root_contract.get("status", {}).get("authority_collapse_count") not in (0, None):
        failures.append({"artifact": "release_root_contract", "reason": "authority collapse count must remain zero"})
    if not root_contract.get("constitutional_rules"):
        failures.append({"artifact": "release_root_contract", "reason": "missing constitutional rules"})
    failures.extend(_authority_matrix_failures(root, root_contract))

    file_rows = std_report.get("file_rows", [])
    scanned = std_report.get("scope", {}).get("scanned_python_files", [])
    if not file_rows:
        failures.append({"artifact": "std_python_compliance_report", "reason": "no scanned Python files"})
    if len(file_rows) != len(scanned):
        failures.append({"artifact": "std_python_compliance_report", "reason": "scanned files and file rows disagree"})
    scope_rows = std_report.get("scope_rows", [])
    navigation_index = std_report.get("navigation_index", {})
    navigation_summary = navigation_index.get("summary", {}) if isinstance(navigation_index, dict) else {}
    navigation_cards = navigation_index.get("cards", []) if isinstance(navigation_index, dict) else []
    navigation_flags = navigation_index.get("flags", []) if isinstance(navigation_index, dict) else []
    navigation_clusters = navigation_index.get("clusters", []) if isinstance(navigation_index, dict) else []
    if not scope_rows:
        failures.append({"artifact": "std_python_compliance_report", "reason": "missing scope rows"})
    if not isinstance(navigation_index, dict) or navigation_index.get("schema_version") != "std_python_microcosm_navigation_index_v0":
        failures.append({"artifact": "std_python_compliance_report", "reason": "missing std_python navigation index"})
    if int(std_report.get("summary", {}).get("scope_row_count", -1)) != len(scope_rows):
        failures.append({"artifact": "std_python_compliance_report", "reason": "scope row count mismatch"})
    if int(navigation_summary.get("scope_row_count", -1)) != len(scope_rows):
        failures.append({"artifact": "std_python_compliance_report", "reason": "navigation index scope count mismatch"})
    if int(navigation_summary.get("card_count", -1)) != len(navigation_cards):
        failures.append({"artifact": "std_python_compliance_report", "reason": "navigation index card count mismatch"})
    if int(navigation_summary.get("flag_count", -1)) != len(navigation_flags):
        failures.append({"artifact": "std_python_compliance_report", "reason": "navigation index flag count mismatch"})
    if int(navigation_summary.get("cluster_count", -1)) != len(navigation_clusters):
        failures.append({"artifact": "std_python_compliance_report", "reason": "navigation index cluster count mismatch"})
    if int(navigation_summary.get("function_or_method_count", 0)) <= 0:
        failures.append({"artifact": "std_python_compliance_report", "reason": "navigation index must route callable scopes"})
    if len(navigation_cards) != len(scope_rows):
        failures.append({"artifact": "std_python_compliance_report", "reason": "navigation index must card every scope row"})
    if len(navigation_flags) != len(scope_rows):
        failures.append({"artifact": "std_python_compliance_report", "reason": "navigation index must flag every scope row"})
    file_paths = {str(row.get("path")) for row in file_rows if isinstance(row, dict)}
    for scope_row in scope_rows:
        if not isinstance(scope_row, dict):
            failures.append({"artifact": "std_python_compliance_report", "reason": "scope row is not an object"})
            continue
        for field in [
            "scope_id",
            "path",
            "scope_kind",
            "qualname",
            "navigation_group",
            "source_span_ref",
            "population_mode",
            "scope_report_ref",
            "authority_boundary",
            "anti_claims",
        ]:
            if not scope_row.get(field):
                failures.append({"scope_id": scope_row.get("scope_id", "<missing>"), "reason": f"scope row missing {field}"})
        if scope_row.get("path") not in file_paths:
            failures.append({"scope_id": scope_row.get("scope_id", "<missing>"), "reason": "scope row path has no file row"})
        if ":" not in str(scope_row.get("source_span_ref", "")):
            failures.append({"scope_id": scope_row.get("scope_id", "<missing>"), "reason": "scope row missing source span"})
    for card in navigation_cards:
        if not isinstance(card, dict):
            failures.append({"artifact": "std_python_compliance_report", "reason": "navigation card is not an object"})
            continue
        for field in ["row_id", "band", "cluster_id", "path", "scope_kind", "source_span_ref", "omission_receipt", "anti_claims"]:
            if not card.get(field):
                failures.append({"row_id": card.get("row_id", "<missing>"), "reason": f"navigation card missing {field}"})
        if card.get("band") != "card":
            failures.append({"row_id": card.get("row_id", "<missing>"), "reason": "navigation card has wrong band"})
        if ":" not in str(card.get("source_span_ref", "")):
            failures.append({"row_id": card.get("row_id", "<missing>"), "reason": "navigation card missing source span"})
    repair_plan = std_report.get("repair_plan", [])
    repair_plan_kinds = {
        row.get("diagnostic_kind")
        for row in repair_plan
        if isinstance(row, dict) and row.get("diagnostic_kind")
    }
    observed_diagnostic_kinds: set[str] = set()
    for row in file_rows:
        if not row.get("path") or not row.get("std_python_status"):
            failures.append({"artifact": "std_python_compliance_report", "reason": "unclassified source row"})
        row_diagnostics = row.get("diagnostics", [])
        if row.get("std_python_status") in {"warn", "block"} and not row_diagnostics:
            failures.append({"path": row.get("path"), "reason": "warning or blocker row lacks diagnostics"})
        if row.get("std_python_status") in {"warn", "block"} and not row.get("next_fix"):
            failures.append({"path": row.get("path"), "reason": "warning or blocker row lacks next_fix"})
        if row.get("std_python_status") in {"warn", "block"}:
            for field in [
                "warning_class",
                "owner_class",
                "protection_status",
                "standards_debt_status",
            ]:
                if not row.get(field) or row.get(field) == "unknown":
                    failures.append({"path": row.get("path"), "reason": f"warning row missing {field}"})
            if not (row.get("reentry_condition") or row.get("next_safe_fix")):
                failures.append({"path": row.get("path"), "reason": "warning row missing reentry_condition or next_safe_fix"})
            if not row.get("anti_claims"):
                failures.append({"path": row.get("path"), "reason": "warning row missing anti_claims"})
            if str(row.get("protection_status", "")).startswith("protected") and row.get("standards_debt_status") != "protected":
                failures.append({"path": row.get("path"), "reason": "protected warning row must not be counted as patchable"})
        for diagnostic in row_diagnostics:
            if isinstance(diagnostic, dict) and diagnostic.get("kind"):
                observed_diagnostic_kinds.add(str(diagnostic["kind"]))
        if row.get("public_safe_status") == "block":
            failures.append({"path": row.get("path"), "reason": "public safety blocker in Python diagnostics"})
    missing_repair_kinds = sorted(observed_diagnostic_kinds - repair_plan_kinds)
    if missing_repair_kinds:
        failures.append({"artifact": "std_python_compliance_report", "missing_repair_plan_kinds": missing_repair_kinds})
    if std_report.get("summary", {}).get("repair_plan_status") != "actionable":
        failures.append({"artifact": "std_python_compliance_report", "reason": "repair plan must be actionable"})
    if int(std_report.get("summary", {}).get("unclassified_warning_count", -1)) != 0:
        failures.append({"artifact": "std_python_compliance_report", "reason": "residual warnings must be classified"})
    if std_report.get("summary", {}).get("standards_closure_status") != "ok":
        failures.append({"artifact": "std_python_compliance_report", "reason": "standards closure status must be ok"})
    if int(std_report.get("summary", {}).get("missing_test_count", -1)) != 0:
        failures.append({"artifact": "std_python_compliance_report", "reason": "direct test coverage warnings must be zero"})
    authority_diagnostics = std_report.get("authority_token_diagnostics", {})
    authority_summary = authority_diagnostics.get("summary", {}) if isinstance(authority_diagnostics, dict) else {}
    if not authority_diagnostics:
        failures.append({"artifact": "std_python_compliance_report", "reason": "missing authority token diagnostics"})
    if int(authority_summary.get("unsafe_promotion_count", -1)) != 0:
        failures.append({"artifact": "std_python_compliance_report", "reason": "unsafe authority promotion tokens must be zero"})
    if int(authority_summary.get("blocker_count", -1)) != 0:
        failures.append({"artifact": "std_python_compliance_report", "reason": "authority token blockers must be zero"})
    if authority_summary.get("fail_closed_status") != "fail_closed":
        failures.append({"artifact": "std_python_compliance_report", "reason": "authority token diagnostics must remain fail-closed"})
    if int(authority_summary.get("unclassified_warning_count", -1)) != 0:
        failures.append({"artifact": "std_python_compliance_report", "reason": "authority token warnings must be classified"})
    if int(authority_summary.get("unclassified_residual_count", -1)) != 0:
        failures.append({"artifact": "std_python_compliance_report", "reason": "authority token residuals must be classified"})
    if authority_summary.get("residual_classification_status") != "ok":
        failures.append({"artifact": "std_python_compliance_report", "reason": "authority token residual status must be ok"})
    if int(std_report.get("summary", {}).get("authority_unclassified_residual_count", -1)) != int(
        authority_summary.get("unclassified_residual_count", -2)
    ):
        failures.append({"artifact": "std_python_compliance_report", "reason": "authority residual classification count mismatch"})
    blocked_claims = authority_diagnostics.get("public_claims_still_blocked", []) if isinstance(authority_diagnostics, dict) else []
    if not blocked_claims:
        failures.append({"artifact": "std_python_compliance_report", "reason": "missing public claims still blocked list"})
    if int(authority_summary.get("blocked_public_claim_count", -1)) != len(blocked_claims):
        failures.append({"artifact": "std_python_compliance_report", "reason": "blocked public claim count mismatch"})
    for claim_row in blocked_claims:
        if not isinstance(claim_row, dict):
            failures.append({"artifact": "std_python_compliance_report", "reason": "blocked public claim row is not an object"})
            continue
        for field in ["claim_id", "claim", "authority_class", "gate_ref", "status", "reason", "anti_claims"]:
            if not claim_row.get(field):
                failures.append({"claim_id": claim_row.get("claim_id", "<missing>"), "reason": f"blocked public claim missing {field}"})
        if "blocked" not in str(claim_row.get("status", "")):
            failures.append({"claim_id": claim_row.get("claim_id", "<missing>"), "reason": "public claim must remain blocked"})
    authority_token_rows = authority_diagnostics.get("token_rows", []) if isinstance(authority_diagnostics, dict) else []
    for token_row in authority_token_rows:
        if not isinstance(token_row, dict):
            failures.append({"artifact": "std_python_compliance_report", "reason": "authority token row is not an object"})
            continue
        status = str(token_row.get("status", ""))
        strength = str(token_row.get("boundary_strength", ""))
        strong_terms = token_row.get("strong_boundary_terms", [])
        weak_terms = token_row.get("weak_boundary_terms", [])
        if strength not in {"strong", "weak", "absent"}:
            failures.append({"path": token_row.get("path"), "reason": "authority token row missing boundary_strength"})
        if status == "ok" and (strength != "strong" or not strong_terms):
            failures.append({"path": token_row.get("path"), "reason": "ok authority token row requires strong boundary terms"})
        if status == "warn" and (strength != "weak" or not weak_terms):
            failures.append({"path": token_row.get("path"), "reason": "warning authority token row requires weak boundary terms"})
        if status == "block" and strength != "absent":
            failures.append({"path": token_row.get("path"), "reason": "blocking authority token row must have absent boundary strength"})
        if status in {"warn", "block"}:
            for field in [
                "warning_class",
                "owner_class",
                "protection_status",
                "standards_debt_status",
            ]:
                if not token_row.get(field) or token_row.get(field) == "unknown":
                    failures.append({"path": token_row.get("path"), "reason": f"authority token warning row missing {field}"})
            if not (token_row.get("reentry_condition") or token_row.get("next_safe_fix")):
                failures.append({"path": token_row.get("path"), "reason": "authority token warning row missing reentry_condition or next_safe_fix"})
            if not token_row.get("anti_claims"):
                failures.append({"path": token_row.get("path"), "reason": "authority token warning row missing anti_claims"})
            if (
                status == "warn"
                and str(token_row.get("protection_status", "")).startswith("protected")
                and token_row.get("standards_debt_status") != "protected"
            ):
                failures.append({"path": token_row.get("path"), "reason": "protected authority token warning must not be patchable"})
    return failures


def build_release_root_compiler(
    root: Path,
    *,
    branch_graph_path: str = BRANCH_GRAPH_PATH,
    root_contract_path: str = ROOT_CONTRACT_PATH,
    std_python_report_path: str = STD_PYTHON_REPORT_PATH,
    receipt_path: str = RECEIPT_PATH,
    write_receipt: bool = False,
    at: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    generated_at = at or _utc_now()
    std_report = build_std_python_report(root, generated_at)
    root_contract = build_release_root_contract(root, generated_at)
    branch_graph = build_release_branch_graph(root, generated_at, std_report)
    authority_diagnostics = _authority_token_diagnostics(
        root,
        {
            BRANCH_GRAPH_PATH: branch_graph,
            ROOT_CONTRACT_PATH: root_contract,
            STD_PYTHON_REPORT_PATH: std_report,
        },
    )
    _attach_authority_token_diagnostics(std_report, root_contract, branch_graph, authority_diagnostics)
    failures = validate_release_root_artifacts(root, branch_graph, root_contract, std_report)
    status = "ok" if not failures else "failed"
    root_contract["status"]["branch_rule_violation_count"] = sum(1 for failure in failures if failure.get("branch_id"))
    root_contract["status"]["std_python_blocker_count"] = std_report.get("summary", {}).get("blocker_count", 0)
    root_contract["status"]["projection_authority_violation_count"] = sum(
        1 for failure in failures if "projection_not_authority" in str(failure.get("reason", ""))
    )
    root_contract["status"]["missing_rule_ref_count"] = sum(1 for failure in failures if failure.get("missing_evidence_refs"))
    root_contract["status"]["authority_collapse_count"] = sum(
        1 for failure in failures if "authority collapse" in str(failure.get("reason", ""))
    )
    authority_lattice = root_contract.get("authority_lattice", {})
    root_contract["status"]["authority_matrix_status"] = "ok" if root_contract["status"]["authority_collapse_count"] == 0 else "block"
    root_contract["status"]["claim_authority_row_count"] = len(authority_lattice.get("claim_authority_matrix", []))
    root_contract["status"]["forbidden_promotion_count"] = len(authority_lattice.get("forbidden_promotions", []))

    _write_json(root / branch_graph_path, branch_graph)
    _write_json(root / root_contract_path, root_contract)
    _write_json(root / std_python_report_path, std_report)

    result: dict[str, Any] = {
        "kind": "release_root_compiler_build",
        "schema_version": "release_root_compiler_build_v0",
        "generated_at": generated_at,
        "status": status,
        "outputs": {
            "branch_graph": branch_graph_path,
            "root_contract": root_contract_path,
            "std_python_report": std_python_report_path,
            "proof_tail_refresh_plan": branch_graph_path + "::proof_tail_refresh_plan",
        },
        "summary": {
            "branch_count": branch_graph["status"]["branch_count"],
            "trunk_count": branch_graph["status"]["trunk_count"],
            "mission_thread_count": branch_graph["status"]["mission_thread_count"],
            "mission_thread_route_count": branch_graph["status"]["mission_thread_route_count"],
            "mission_thread_step_count": branch_graph["status"]["mission_thread_step_count"],
            "std_python_scanned_count": std_report["summary"]["scanned_count"],
            "std_python_scope_row_count": std_report["summary"]["scope_row_count"],
            "std_python_scope_navigation_card_count": std_report["summary"]["scope_navigation_card_count"],
            "std_python_scope_navigation_function_or_method_count": std_report["summary"]["scope_navigation_function_or_method_count"],
            "std_python_warning_count": std_report["summary"]["warning_count"],
            "std_python_blocker_count": std_report["summary"]["blocker_count"],
            "std_python_protected_warning_count": std_report["summary"]["protected_warning_count"],
            "std_python_unclassified_warning_count": std_report["summary"]["unclassified_warning_count"],
            "standards_closure_status": std_report["summary"]["standards_closure_status"],
            "authority_warning_count": std_report["summary"]["authority_warning_count"],
            "authority_weak_boundary_count": std_report["summary"]["authority_weak_boundary_count"],
            "authority_residual_count": std_report["summary"]["authority_residual_count"],
            "authority_unclassified_residual_count": std_report["summary"]["authority_unclassified_residual_count"],
            "authority_token_blocker_count": std_report["summary"]["authority_token_blocker_count"],
            "unsafe_promotion_count": std_report["summary"]["unsafe_promotion_count"],
            "blocked_public_claim_count": std_report["summary"]["blocked_public_claim_count"],
            "blocked_authority_classes": std_report["summary"]["blocked_authority_classes"],
            "authority_collapse_count": root_contract["status"]["authority_collapse_count"],
            "missing_ref_count": branch_graph["status"]["missing_ref_count"],
            "proof_tail_refresh_group_count": branch_graph["status"]["proof_tail_refresh_group_count"],
            "proof_tail_missing_ref_count": branch_graph["status"]["proof_tail_missing_ref_count"],
            "proof_tail_refresh_status": branch_graph["compliance_diagnostics"]["proof_tail_refresh_status"],
            "validation_failure_count": len(failures),
        },
        "failures": failures,
        "public_safety_boundary": "Local release-root branch and standards diagnostics only; not hosted-public, publication, certification, or private-root evidence.",
    }
    if write_receipt:
        receipt = {
            "kind": "receipt",
            "schema_version": "receipt_v0",
            "id": "receipt.release_root_compiler",
            "generated_at": generated_at,
            "owner": "idea_microcosm.release_root_compiler",
            "claim_ref": "release_root_branch_graph_and_standards_diagnostics",
            "claim_tier": "fixture_validated",
            "command": BUILDER_COMMAND,
            "result": status,
            "status": status,
            "evidence_refs": [branch_graph_path, root_contract_path, std_python_report_path],
            "proof_tail_refresh_plan_ref": branch_graph_path + "::proof_tail_refresh_plan",
            "proof_tail_refresh_plan": branch_graph["proof_tail_refresh_plan"],
            "omissions": [
                "Does not overwrite sibling cold-entry atlas or concept graph artifacts.",
                "Does not certify std_python compliance across the private repo.",
                "Does not grant hosted public, publication, rights, citation, or disclosure authority.",
                "Does not make stale proof-tail artifacts acceptable without their owner commands.",
            ],
            "summary": result["summary"],
        }
        _write_json(root / receipt_path, receipt)
        result["receipt_written"] = receipt_path
    return result


def compile_release_root(
    root: Path,
    *,
    branch_graph_path: str = BRANCH_GRAPH_PATH,
    root_contract_path: str = ROOT_CONTRACT_PATH,
    std_python_report_path: str = STD_PYTHON_REPORT_PATH,
    receipt_path: str = RECEIPT_PATH,
    write_receipt: bool = False,
    at: str | None = None,
) -> dict[str, Any]:
    """Compatibility entrypoint retained for exact-copy public manifests."""
    return build_release_root_compiler(
        root,
        branch_graph_path=branch_graph_path,
        root_contract_path=root_contract_path,
        std_python_report_path=std_python_report_path,
        receipt_path=receipt_path,
        write_receipt=write_receipt,
        at=at,
    )
