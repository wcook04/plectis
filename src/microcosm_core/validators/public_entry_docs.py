from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path
from typing import Any

from microcosm_core.public_payload_boundary import public_payload_boundary
from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import write_json_atomic
from microcosm_core.schemas import read_json_strict


CHECKER_ID = "checker.microcosm.validators.public_entry_docs"
FIXTURE_ID = "first_wave.public_entry_docs"
REQUIRED_DOCS = [
    "README.md",
    "AGENTS.md",
    "AGENT_ROUTES.md",
    "core/organ_registry.json",
    "core/organ_evidence_classes.json",
    "atlas/entry_packet.json",
    "atlas/agent_task_routes.json",
    "paper_modules/pattern_binding_contract.md",
    "paper_modules/executable_doctrine_grammar.md",
    "paper_modules/proof_diagnostic_evidence_spine.md",
    "paper_modules/formal_math_readiness_gate.md",
    "paper_modules/corpus_readiness_mathlib_absence.md",
    "paper_modules/mathematical_strategy_atlas.md",
    "paper_modules/tactic_portfolio_availability.md",
    "paper_modules/target_shape_tactic_routing.md",
    "paper_modules/formal_math_premise_retrieval.md",
    "paper_modules/formal_math_verifier_trace_repair_loop.md",
    "paper_modules/formal_evidence_cell_anchor_resolver.md",
    "paper_modules/undeclared_library_prior_classifier.md",
    "paper_modules/lean_std_premise_index.md",
    "paper_modules/ring2_premise_precision_recall.md",
    "paper_modules/agent_benchmark_integrity_anti_gaming_replay.md",
    "paper_modules/durable_agent_work_landing_replay.md",
    "paper_modules/research_replication_rubric_artifact_replay.md",
    "paper_modules/world_model_projection_drift_control_room.md",
    "paper_modules/spatial_world_model_counterfactual_simulation_replay.md",
    "paper_modules/materials_chemistry_closed_loop_lab_safety_replay.md",
    "paper_modules/mechanistic_interpretability_circuit_attribution_replay.md",
    "paper_modules/bridge_phase_continuity_runtime.md",
    "paper_modules/provider_context_recipe_budget.md",
    "paper_modules/public_reveal_walkthrough.md",
    "paper_modules/macro_projection_import_protocol.md",
    "paper_modules/formal_math_lean_proof_witness.md",
    "paper_modules/verifier_lab_kernel.md",
    "paper_modules/prediction_oracle_reconciliation.md",
    "paper_modules/standards_meta_diagnostics.md",
    "paper_modules/cold_reader_route_map.md",
    "paper_modules/agent_monitor_redteam_falsification_replay.md",
    "paper_modules/agent_sabotage_scheming_monitor_replay.md",
    "paper_modules/agent_memory_temporal_conflict_replay.md",
    "paper_modules/sleeper_memory_poisoning_quarantine_replay.md",
    "paper_modules/mcp_tool_authority_replay.md",
    "paper_modules/proof_derived_governed_mutation_authorization.md",
    "paper_modules/belief_state_process_reward_replay.md",
    "paper_modules/agent_sandbox_policy_escape_replay.md",
    "paper_modules/indirect_prompt_injection_information_flow_policy_replay.md",
    "paper_modules/agentic_vulnerability_discovery_patch_proof_replay.md",
    "paper_modules/voice_to_doctrine_self_improvement_loop.md",
    "paper_modules/cold_clone_probe.md",
    "skills/cold_start_navigation.md",
]
REQUIRED_PHRASES_BY_DOC = {
    "README.md": [
        "repo -> .microcosm",
        "Real Substrate Posture",
        "Plectis is the public repo form of the macro system",
        "not a synthetic safety proxy",
        "Public should carry private by default",
        "as much of the macro substrate as possible",
        "The exclusion set is narrow",
        # Aligned with the public-copy clean (8af1382420): the README's
        # exclusion-set sentence now uses cold-reader wording instead of the
        # house phrase "raw operator voice, slurs or abusive wording". The pin
        # runs through the full noun phrase so a tail edit cannot slip past;
        # the README pin in tests/test_public_entry_docs.py (first-slice test)
        # converges on this same string.
        "private notes, personal material, and other content that is unsafe for a public source package",
        "Any `body_copied=true` claim must name the source file",
        "microcosm compile .",
        "std_python_microcosm_navigation_assay",
        "implementation_atlas.python_navigation_assay",
        "executable research prototype",
        "local project operating substrate",
        ".microcosm/",
        "Architecture Kernel",
        "microcosm explain <project> <route_id>",
        "Evidence receipts are the black-box recorder",
        "`accepted_current_authority` is not an evidence-strength claim",
        "evidence_class",
        "front_door_status.blocking_surface_ids",
        "Internal Runtime Spine",
        "public entry inventory/read-model",
        "inventory-only route-alignment metadata",
        "not product progress, release readiness",
        "[AGENT_ROUTES.md](AGENT_ROUTES.md)",
        "[ORGANS.md#find-your-specialty](ORGANS.md#find-your-specialty)"
    ],
    "AGENTS.md": [
        "microcosm tour --card <project>",
        "microcosm tour <project>",
        "microcosm compile <project>",
        "repo -> `.microcosm`",
        "Real Substrate Posture",
        "Plectis is the public repo form of the macro system",
        "not a synthetic safety proxy",
        "Public should carry private by default",
        "as much of the macro substrate as possible",
        "Use synthetic fixtures only as regression wrappers",
        "The hard exclusion set is narrow",
        "raw operator voice, slurs or abusive wording",
        "Any `body_copied=true` claim must point at a real target file",
        "executable research prototype",
        "local project operating substrate",
        "make standalone-export EXPORT_OUT=/tmp/microcosm-substrate-export",
        "receipts/release/release_export_receipt.json",
        "cold-clone check proves the exported package can install",
        "It does not authorize release",
        "Treat `microcosm --help` as the bounded first-screen console-command registry.",
        "PYTHONPATH=src python3 -m microcosm_core --help",
        "microcosm explain <project> <route_id>",
        "Accepted Public Runtime Spine",
        "public entry inventory",
        "inventory-only route-alignment metadata",
        "not product progress, release readiness",
        "[AGENT_ROUTES.md](AGENT_ROUTES.md)",
        "[ORGANS.md#find-your-specialty](ORGANS.md#find-your-specialty)",
        "`accepted_current_authority` is not an evidence-strength claim",
        "evidence_class",
        "Fixtures Are Tests",
        "Receipts Are Evidence",
        "Do not treat prediction fixtures as trading or financial advice",
        "Do not widen Lean/Lake"
    ],
    "skills/cold_start_navigation.md": [
        "First-Screen Route Contract",
        "Bring a folder first",
        "atlas/entry_packet.json::local_first_screen_route",
        "microcosm tour --card <project>",
        "microcosm tour <project>",
        "route_cards_by_id.status_and_workingness",
        "microcosm status --card <project>",
        "front_door.route_explanation",
        "microcosm workingness --card",
        "microcosm proof-lab --out /tmp/microcosm-proof-lab",
        "microcosm serve <project> --host 127.0.0.1 --port 8765",
        "microcosm serve <project> --host 127.0.0.1 --port 8765 --max-requests 7",
        "Omit `--max-requests` only when you intentionally want an interactive server",
        "/project/observatory-card",
        "Receipts are evidence drilldowns after the behavior route is visible",
        "evidence_class",
        "`accepted_current_authority` is not an evidence-strength claim",
        "std_python_microcosm_navigation_assay",
        "implementation_atlas.python_navigation_assay",
        "make standalone-export EXPORT_OUT=/tmp/microcosm-substrate-export",
        "cd /tmp/microcosm-substrate-export/microcosm-substrate",
        "cold-clone check proves the exported artifact can install",
        "receipts/release/release_export_receipt.json",
        "release_authorized=false",
        "six cold reader branches",
        "Domain specialist: run",
        "microcosm hello --reader domain_specialist <project>",
        "ORGANS.md#find-your-specialty",
        "explicit non-claim of domain correctness or expert review"
    ],
    "AGENT_ROUTES.md": [
        "Microcosm Agent Task Routes",
        "Agent Task Route Table",
        "`task_class`",
        "atlas/agent_task_routes.json",
        "ORGANS.md#find-your-specialty",
        "Stop when the first command or named result record is visible"
    ]
}


FORBIDDEN_PHRASES_BY_DOC = {
    "README.md": [
        "runnable, synthetic, and receipt-driven",
        "private reconstruction control plane",
        "public synthetic microcosm",
        "public-safe ten-minute path",
        "public-safe authority ceiling",
    ],
    "AGENTS.md": [
        "source reconstruction workspace",
        "Use only synthetic fixtures",
        "Receipts Are Authority",
        "macro reconstruction contracts",
        "only to project\n   metadata",
        "only to project metadata",
        "public-safe route",
    ],
}
# Positive-overclaim prose scan. The lean refactor enforces PRESENCE of
# anti-claims but had no check for the ABSENCE of a contradicting positive
# overclaim, so an affirming sentence could coexist with its own disclaimer and
# pass. These are AFFIRMATIVE constructions with no honest use in the public
# entry docs; the anti-claim NOUNS the docs legitimately disclaim ("release
# readiness", "maturity scores", "whole-system correctness", "private-root
# equivalence") are deliberately NOT matched, and each pattern is verified not
# to fire on the live negated/nominal prose. Mirrors the discipline of
# projections/organ_atlas.OVERCLAIM_PHRASES but tuned for free prose, and is
# applied to the generated atlas docs too (they are the cold-reader surfaces
# README routes to but are otherwise outside this validator's REQUIRED_DOCS).
PUBLIC_ENTRY_OVERCLAIM_PATTERNS = (
    # release / hosting / publication authority
    r"\bis (now |fully )?production-ready\b",
    r"\bis (now |fully )?release-ready\b",
    r"\bship it\b",
    r"\b(authorized|cleared|approved) for (hosted )?release\b",
    r"\bpublish(es|ed)? to pypi\b",
    r"\bdeploy(s|ed|ing)? (it )?to (the )?(hosted|production)\b",
    r"\bdeploy the hosted (service|server|app)\b",
    # provider execution / live access
    r"\bcalls (your|the) (configured )?(model|provider)\b",
    r"\bmakes (live )?provider calls\b",
    r"\bemails (the|you|your|a) \w+",
    r"\bsends to recipients\b",
    r"\bcontrols your browser\b",
    r"\breads your account session\b",
    # private-root / secret equivalence
    r"\bis (functionally |effectively )?the private (macro )?root\b",
    r"\bequals the (private|macro) root\b",
    r"\bis private-root equivalent\b",
    r"\bis reproduced here\b",
    # whole-system proof
    r"\bproven correct\b",
    r"\bfully verified\b",
    r"\bguarantees? correctness\b",
    r"\bproves the (whole |entire )?(theorem|system)\b",
    # evidence-class-as-score
    r"\bquality score\b",
    r"\bmaturity level\b",
)
PUBLIC_ENTRY_OVERCLAIM_SCANNED_DOCS = (
    "README.md",
    "AGENTS.md",
    "AGENT_ROUTES.md",
    "ORGANS.md",
    "ARCHITECTURE.md",
)
PUBLIC_ENTRY_HARDCODED_ORGAN_COUNT_SCANNED_DOCS = (
    "README.md",
    "AGENTS.md",
)
PUBLIC_ENTRY_HARDCODED_ORGAN_COUNT_PATTERNS = (
    r"\b\d+\s+accepted\s+public\s+runtime\s+organs?(?:\s+records)?\b",
    r"\ball\s+\d+\s+runtime\s+organs?\b",
    r"\bthe\s+\d+\s+organs?\s+cluster\b",
    r"\b\d+\s+organs?\s+cluster\s+into\b",
    r"\bpublic\s+package\s+carries\s+\d+\s+accepted\s+public\s+runtime\s+organs?\b",
)
CLI_FIRST_SCREEN_HELP_REL = Path("src/microcosm_core/cli.py")
CLI_FIRST_SCREEN_HELP_COMMAND_ORDER = [
    "microcosm tour --card <project>",
    "microcosm status --card <project>",
    "microcosm workingness --card",
    "microcosm proof-lab --out /tmp/microcosm-proof-lab",
    "microcosm serve <project>",
    "microcosm compile <project>",
]
CLI_FIRST_SCREEN_HELP_BOUNDARY_PHRASES = [
    "local-first only",
    "no provider calls, source mutation, release",
    "hosting, proof-correctness, or credential-equivalent live-access authority",
    "Receipts are evidence drilldowns after the behavior route is visible",
]


def _display(path: Path, *, public_root: Path) -> str:
    """Render a path relative to public_root for receipt display.

    - Teleology: protects receipt-path display fields from leaking absolute/private host paths into the public entry-docs receipt.
    - Guarantee: returns the public-relative display string from public_relative_path(path, display_root=public_root).
    - Fails: None (delegates entirely to public_relative_path; this wrapper itself raises/returns no failure envelope).
    - Reads: the path argument only (no disk read here).
    - Writes: None.
    """
    return public_relative_path(path, display_root=public_root)


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    """Extract the dict-typed rows under payload[key].

    - Teleology: protects every downstream registry/route scan from malformed (non-dict) rows in a loaded manifest, so a poisoned list entry cannot crash or skew counts.
    - Guarantee: returns only the elements of payload[key] that are dicts; missing key yields [].
    - Fails: None (defaults missing key to []; non-dict entries are filtered, not raised).
    - Reads: in-memory payload dict only.
    - Writes: None.
    """
    rows = payload.get(key, [])
    return [row for row in rows if isinstance(row, dict)]


def _receipt_safe_scan(scan: dict[str, Any]) -> dict[str, Any]:
    """Strip the secret-class field names out of a scan summary before it lands in a public receipt.

    - Teleology: protects the public receipt from re-emitting the forbidden-class field names that the secret-exclusion scan carries, which would itself be a leak of the policy's matched-secret schema.
    - Guarantee: returns a shallow copy of scan with key 'forbidden_output_fields' removed; all other scan keys/values preserved.
    - Fails: None (pop with default None cannot raise on a missing key; no rejection path).
    - Reads: in-memory scan dict only.
    - Writes: None.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    safe = dict(scan)
    safe.pop("forbidden_output_fields", None)
    return safe


def _normalized_text(text: str) -> str:
    """Collapse all runs of whitespace in text to single spaces.

    - Teleology: protects required/forbidden-phrase substring checks from false negatives caused by line-wrapping or irregular whitespace in the entry docs.
    - Guarantee: returns text with every whitespace run (including newlines) collapsed to one space and leading/trailing whitespace removed.
    - Fails: None (pure str transform; no rejection path).
    - Writes: None.
    """
    return " ".join(text.split())


def _accepted_organs(public_root: Path) -> list[str]:
    """Read the accepted-authority organ ids from the public organ registry.

    - Teleology: protects the accepted-public-organ inventory claim by sourcing it ONLY from the registry rows whose status is accepted_current_authority, never from hand-counted prose.
    - Guarantee: returns the organ_id strings of core/organ_registry.json::implemented_organs rows whose status == 'accepted_current_authority', in registry order.
    - Fails: missing/invalid core/organ_registry.json -> read_json_strict raises (FileNotFoundError / JSON decode error) before any list is returned.
    - Reads: <public_root>/core/organ_registry.json.
    - Writes: None.
    - When-needed: inspect when verifying the public entry docs' organ count/spine against the registry source of truth.
    - Escalates-to: core/organ_registry.json::implemented_organs[status=accepted_current_authority].
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    registry = read_json_strict(public_root / "core/organ_registry.json")
    return [
        str(row.get("organ_id"))
        for row in _rows(registry, "implemented_organs")
        if row.get("status") == "accepted_current_authority"
    ]


def _duplicates(values: list[str]) -> list[str]:
    """Return the sorted set of values that appear more than once.

    - Teleology: protects organ-id and task-class uniqueness claims by surfacing any duplicated entry that would inflate or double-count the inventory.
    - Guarantee: returns a sorted list of each distinct value seen two or more times in the input; clean input yields [].
    - Fails: None (collects duplicates; never raises or rejects).
    - Writes: None.
    """
    seen: set[str] = set()
    duplicated: set[str] = set()
    for value in values:
        if value in seen:
            duplicated.add(value)
        seen.add(value)
    return sorted(duplicated)


def _organ_slug(organ_id: str) -> str:
    """Convert an organ_id to its hyphenated slug form.

    - Teleology: protects dynamic-inventory phrase matching by letting an organ id be recognized in both underscore and hyphen (slug) spellings.
    - Guarantee: returns organ_id with every underscore replaced by a hyphen.
    - Fails: None (pure str transform).
    - Writes: None.
    """
    return organ_id.replace("_", "-")


def _required_phrase_is_dynamic_inventory(
    phrase: str,
    accepted_organs: list[str],
) -> bool:
    """Decide whether a required-phrase is a registry-derived inventory token (so absence is not a doc defect).

    - Teleology: protects the required-phrase gate from false MISSING_REQUIRED_ENTRY_PHRASE blocks when a phrase is actually a dynamic organ-inventory token that the registry owns, not static entry copy.
    - Guarantee: returns True when the backtick-stripped phrase equals an accepted organ id, an accepted organ slug, or a digit-bearing 'accepted public runtime organ' count phrase; else False.
    - Fails: None (returns a bool; never raises or rejects).
    - Reads: in-memory accepted_organs list only.
    - Writes: None.
    - When-needed: inspect when a required-phrase miss must be classified as registry-owned inventory vs a real doc gap.
    """
    bare = phrase.strip("`")
    if bare in set(accepted_organs):
        return True
    if bare in {_organ_slug(organ_id) for organ_id in accepted_organs}:
        return True
    return bool(
        bare
        and any(char.isdigit() for char in bare)
        and "accepted public runtime organ" in bare
    )


def _has_registry_route(text: str) -> bool:
    """Test whether a doc routes its organ inventory through the registry + evidence-class surfaces.

    - Teleology: protects the 'registry route' honesty mode by confirming a doc that defers per-organ enumeration actually names both registry surfaces and the evidence-class posture, not just one.
    - Guarantee: returns True only when the normalized text contains ALL of core/organ_registry.json, core/organ_evidence_classes.json, accepted_current_authority, and evidence_class.
    - Fails: None (returns False on any missing phrase; never raises).
    - Reads: in-memory text only.
    - Writes: None.
    """
    normalized = _normalized_text(text)
    required = (
        "core/organ_registry.json",
        "core/organ_evidence_classes.json",
        "accepted_current_authority",
        "evidence_class",
    )
    return all(phrase in normalized for phrase in required)


def _public_entry_overclaim_hits(
    doc_text_by_rel: dict[str, str],
    public_root: Path,
) -> dict[str, list[str]]:
    """Scan the cold-reader entry surfaces for affirmative authority overclaims.

    Returns {doc_rel: [matched patterns]}. Empty when clean. Includes the
    generated atlas docs (ORGANS.md/ARCHITECTURE.md) so an overclaim cannot hide
    on the surfaces README routes readers to but that are not in REQUIRED_DOCS.

    - Teleology: protects the public entry/atlas surfaces from an affirmative authority overclaim (production/release-ready, live provider calls, private-root equivalence, proven-correct, evidence-class-as-score) coexisting with its own disclaimer and passing.
    - Guarantee: returns {doc_rel: sorted matched PUBLIC_ENTRY_OVERCLAIM_PATTERNS} for each scanned doc whose lowercased-normalized text matches at least one pattern; clean/absent docs are omitted so {} means no overclaim hit.
    - Fails: an overclaiming phrase -> doc_rel appears in the returned dict -> caller appends PUBLIC_ENTRY_OVERCLAIM blocking code and blocks the receipt.
    - Reads: doc_text_by_rel cache first, else <public_root>/<rel> for each rel in PUBLIC_ENTRY_OVERCLAIM_SCANNED_DOCS (README/AGENTS/AGENT_ROUTES/ORGANS/ARCHITECTURE .md).
    - Writes: None.
    - When-needed: inspect when diagnosing why the receipt blocked on PUBLIC_ENTRY_OVERCLAIM.
    - Escalates-to: PUBLIC_ENTRY_OVERCLAIM_PATTERNS in this module.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    hits: dict[str, list[str]] = {}
    for rel in PUBLIC_ENTRY_OVERCLAIM_SCANNED_DOCS:
        text = doc_text_by_rel.get(rel)
        if text is None:
            path = public_root / rel
            text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if not text:
            continue
        normalized = _normalized_text(text).lower()
        matched = sorted(
            pattern
            for pattern in PUBLIC_ENTRY_OVERCLAIM_PATTERNS
            if re.search(pattern, normalized)
        )
        if matched:
            hits[rel] = matched
    return hits


def _hardcoded_numeric_organ_count_claims(
    doc_text_by_rel: dict[str, str],
) -> dict[str, list[str]]:
    """Scan README/AGENTS for hardcoded numeric organ-count claims that would drift from the registry.

    - Teleology: protects the organ-count claim from a hand-typed number (e.g. 'N accepted public runtime organs') that silently drifts as the registry grows/shrinks.
    - Guarantee: returns {doc_rel: sorted matched count-claim substrings} for each PUBLIC_ENTRY_HARDCODED_ORGAN_COUNT_SCANNED_DOCS (README.md, AGENTS.md) whose normalized text matches PUBLIC_ENTRY_HARDCODED_ORGAN_COUNT_PATTERNS; {} when none.
    - Fails: a hardcoded numeric organ-count phrase -> doc_rel appears in the dict -> caller appends HARDCODED_PUBLIC_ENTRY_ORGAN_COUNT and blocks the receipt.
    - Reads: doc_text_by_rel cache only (no disk read; absent/empty text is skipped).
    - Writes: None.
    - When-needed: inspect when diagnosing a HARDCODED_PUBLIC_ENTRY_ORGAN_COUNT block.
    - Escalates-to: PUBLIC_ENTRY_HARDCODED_ORGAN_COUNT_PATTERNS in this module.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    hits: dict[str, list[str]] = {}
    for rel in PUBLIC_ENTRY_HARDCODED_ORGAN_COUNT_SCANNED_DOCS:
        text = doc_text_by_rel.get(rel, "")
        if not text:
            continue
        normalized = _normalized_text(text)
        matched: set[str] = set()
        for pattern in PUBLIC_ENTRY_HARDCODED_ORGAN_COUNT_PATTERNS:
            for match in re.finditer(pattern, normalized, flags=re.IGNORECASE):
                matched.add(match.group(0))
        if matched:
            hits[rel] = sorted(matched)
    return hits


def _ordered_code_list_after_heading(text: str, heading: str) -> list[str]:
    """Parse a numbered ``code``-span list immediately following a markdown heading.

    - Teleology: protects ordered-list parity checks by extracting the backticked tokens of a numbered list under a heading from doc text.
    - Guarantee: returns, in order, the first backtick-delimited token of each line that starts with a digit and contains '. `'; stops at the next '## ' heading or first non-numbered line after the list begins.
    - Fails: None (returns [] when the heading is absent or no numbered code rows are found; never raises).
    - Reads: in-memory text only.
    - Writes: None.
    """
    if heading not in text:
        return []
    rows: list[str] = []
    started = False
    for line in text.split(heading, 1)[1].splitlines():
        stripped = line.strip()
        if started and stripped.startswith("## "):
            break
        if stripped and stripped[0].isdigit() and ". `" in stripped and "`" in stripped:
            parts = stripped.split("`")
            if len(parts) >= 3:
                rows.append(parts[1])
                started = True
                continue
        if started and stripped and not stripped[0].isdigit():
            break
    return rows


def _bullet_code_list_between(text: str, start_heading: str, end_heading: str) -> list[str]:
    """Parse the bulleted ``code``-span tokens between two headings.

    - Teleology: protects bullet-list parity checks by extracting the backticked tokens of a '- `...`' bullet list bounded by a start and end heading.
    - Guarantee: returns the inner token of each line matching '- `<token>`' within the section after start_heading and before end_heading (end_heading optional; whole tail used if absent).
    - Fails: None (returns [] when start_heading is absent or no bullet rows match; never raises).
    - Reads: in-memory text only.
    - Writes: None.
    """
    if start_heading not in text:
        return []
    section = text.split(start_heading, 1)[1]
    if end_heading in section:
        section = section.split(end_heading, 1)[0]
    rows: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("- `") and stripped.endswith("`"):
            rows.append(stripped[3:-1])
    return rows


def _string_list(value: Any) -> list[str]:
    """Coerce an arbitrary value into a list of only its string elements.

    - Teleology: protects entry-packet route parsing from malformed (non-list / mixed-type) JSON fields so a poisoned value cannot crash the contract scan.
    - Guarantee: returns [] when value is not a list, else the subset of value's elements that are str, order-preserved.
    - Fails: None (non-list and non-str elements are filtered, not raised).
    - Reads: in-memory value only.
    - Writes: None.
    """
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _top_level_string_assignment(source: str, name: str) -> str | None:
    """Statically read the string value of a top-level `name = "..."` assignment via AST.

    - Teleology: protects the CLI first-screen-help contract by reading the FIRST_SCREEN_HELP constant without importing/executing cli.py (no provider/source side effects).
    - Guarantee: returns the str constant assigned to a module-level Assign/AnnAssign target named `name`; returns None if no such string-constant assignment exists.
    - Fails: malformed source -> ast.parse raises SyntaxError (caught by the caller, which records status='blocked'/invalid_cli_help_source); absent assignment -> returns None (caller records missing_first_screen_help_assignment).
    - Reads: in-memory source string only (static parse, no execution).
    - Writes: None.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    module = ast.parse(source)
    for node in module.body:
        if isinstance(node, ast.Assign):
            has_name = any(
                isinstance(target, ast.Name) and target.id == name
                for target in node.targets
            )
            if has_name and isinstance(node.value, ast.Constant):
                if isinstance(node.value.value, str):
                    return node.value.value
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            return node.value.value
    return None


def _cli_first_screen_help_contract(public_root: Path) -> dict[str, Any]:
    """Check that cli.py's FIRST_SCREEN_HELP carries the required commands, in order, with the authority-boundary phrases.

    - Teleology: protects the `microcosm --help` first-screen claim that it is a local-first, bounded console registry from drifting (missing/mis-ordered commands or a dropped boundary disclaimer).
    - Guarantee: returns a dict whose status == PASS only when FIRST_SCREEN_HELP contains every CLI_FIRST_SCREEN_HELP_COMMAND_ORDER command, in non-decreasing position order, and every CLI_FIRST_SCREEN_HELP_BOUNDARY_PHRASE; else status 'blocked'/'missing' with the specific missing_* lists and blocking_reasons.
    - Fails: absent cli.py -> status 'missing'+['missing_cli_help_source']; SyntaxError -> status 'blocked'+['invalid_cli_help_source']+parse_error; no FIRST_SCREEN_HELP string -> 'blocked'+['missing_first_screen_help_assignment']; missing/mis-ordered command or missing boundary phrase -> 'blocked' with the matching blocking_reason.
    - Reads: <public_root>/src/microcosm_core/cli.py (FIRST_SCREEN_HELP constant via AST).
    - Writes: None (returns a dict; the top-level validator writes the receipt).
    - When-needed: inspect when the receipt blocks on CLI_FIRST_SCREEN_HELP_CONTRACT_MISMATCH.
    - Escalates-to: src/microcosm_core/cli.py::FIRST_SCREEN_HELP.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    path = public_root / CLI_FIRST_SCREEN_HELP_REL
    source_ref = f"{CLI_FIRST_SCREEN_HELP_REL.as_posix()}::FIRST_SCREEN_HELP"
    authority = (
        "CLI help first-screen route parity only; not release, hosting, "
        "provider, source-mutation, proof-correctness, or live-access authority"
    )
    if not path.is_file():
        return {
            "status": "missing",
            "source_ref": source_ref,
            "missing_help_commands": CLI_FIRST_SCREEN_HELP_COMMAND_ORDER,
            "help_command_order_mismatch": [],
            "missing_boundary_phrases": CLI_FIRST_SCREEN_HELP_BOUNDARY_PHRASES,
            "blocking_reasons": ["missing_cli_help_source"],
            "authority": authority,
        }
    try:
        help_text = _top_level_string_assignment(
            path.read_text(encoding="utf-8"),
            "FIRST_SCREEN_HELP",
        )
    except SyntaxError as exc:
        return {
            "status": "blocked",
            "source_ref": source_ref,
            "missing_help_commands": CLI_FIRST_SCREEN_HELP_COMMAND_ORDER,
            "help_command_order_mismatch": [],
            "missing_boundary_phrases": CLI_FIRST_SCREEN_HELP_BOUNDARY_PHRASES,
            "blocking_reasons": ["invalid_cli_help_source"],
            "parse_error": type(exc).__name__,
            "authority": authority,
        }
    if help_text is None:
        return {
            "status": "blocked",
            "source_ref": source_ref,
            "missing_help_commands": CLI_FIRST_SCREEN_HELP_COMMAND_ORDER,
            "help_command_order_mismatch": [],
            "missing_boundary_phrases": CLI_FIRST_SCREEN_HELP_BOUNDARY_PHRASES,
            "blocking_reasons": ["missing_first_screen_help_assignment"],
            "authority": authority,
        }

    missing_commands = [
        command
        for command in CLI_FIRST_SCREEN_HELP_COMMAND_ORDER
        if command not in help_text
    ]
    command_positions = {
        command: help_text.index(command)
        for command in CLI_FIRST_SCREEN_HELP_COMMAND_ORDER
        if command in help_text
    }
    order_mismatch = [
        f"{left} before {right}"
        for left, right in zip(
            CLI_FIRST_SCREEN_HELP_COMMAND_ORDER,
            CLI_FIRST_SCREEN_HELP_COMMAND_ORDER[1:],
        )
        if left in command_positions
        and right in command_positions
        and command_positions[left] >= command_positions[right]
    ]
    missing_boundary_phrases = [
        phrase
        for phrase in CLI_FIRST_SCREEN_HELP_BOUNDARY_PHRASES
        if phrase not in help_text
    ]
    blocking_reasons: list[str] = []
    if missing_commands:
        blocking_reasons.append("missing_help_commands")
    if order_mismatch:
        blocking_reasons.append("help_command_order_mismatch")
    if missing_boundary_phrases:
        blocking_reasons.append("missing_boundary_phrases")
    return {
        "status": PASS if not blocking_reasons else "blocked",
        "source_ref": source_ref,
        "required_command_order": CLI_FIRST_SCREEN_HELP_COMMAND_ORDER,
        "missing_help_commands": missing_commands,
        "help_command_order_mismatch": order_mismatch,
        "missing_boundary_phrases": missing_boundary_phrases,
        "blocking_reasons": blocking_reasons,
        "authority": authority,
    }


def _entry_packet_route_contract(
    public_root: Path,
    doc_text_by_rel: dict[str, str],
) -> dict[str, Any]:
    """Validate atlas/entry_packet.json's local-first-screen route, reader routes, cold-clone boundary, and the README/cold-start prose that mirror them.

    - Teleology: protects the cold-reader first-screen route claim (commands, state-refs, observatory endpoints, drilldowns, reader-typed branches, local cold-clone receipt boundary, and safe_to_show flags) from drifting between the packet and the entry prose.
    - Guarantee: returns a dict whose status == PASS only when the packet supplies all required commands/state_refs/observatory_endpoints/drilldown_routes/allowed_drilldowns in the required order, first_command == 'microcosm tour --card <project>' (and primary matches), the route-selection rules are present in packet+README+cold-start, all six reader_ids carry complete fields, the cold-clone boundary points at ./bootstrap.sh + .microcosm/cold_clone_probe.json (and excludes the stale tracked emit/receipt), and every safe_to_show flag (source_files_mutated/provider_calls_authorized/release_authorized/proof_correctness_claim) is exactly False; else 'blocked' with the specific blocking_reasons.
    - Fails: absent entry_packet.json -> status 'missing'+['missing_entry_packet']; unparseable JSON -> 'blocked'+['invalid_entry_packet_json']+parse_error; any missing/mis-ordered/unsafe field -> 'blocked' with the corresponding blocking_reason (e.g. unsafe_safe_to_show_flags, cold_clone_local_receipt_boundary_mismatch, reader_first_screen_routes_missing).
    - Reads: <public_root>/atlas/entry_packet.json; doc_text_by_rel for README.md and skills/cold_start_navigation.md.
    - Writes: None (returns a dict; receipt is written by the top-level validator).
    - When-needed: inspect when the receipt blocks on ENTRY_PACKET_ROUTE_CONTRACT_MISMATCH.
    - Escalates-to: atlas/entry_packet.json::local_first_screen_route / reader_first_screen_routes / cold_clone_probe_route.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    path = public_root / "atlas/entry_packet.json"
    required_commands = [
        "microcosm tour --card <project>",
        "microcosm compile <project>",
        "microcosm python-lens <project>",
        "microcosm explain <project> <selected_route_id>",
        "microcosm evidence list <project> --limit 25",
        "microcosm status --card <project>",
        "microcosm workingness --card",
        "microcosm proof-lab --out /tmp/microcosm-proof-lab",
        "microcosm observe --card <project>",
        "microcosm serve <project> --host 127.0.0.1 --port 8765",
        "microcosm serve <project> --host 127.0.0.1 --port 8765 --max-requests 7",
    ]
    required_state_refs = [
        ".microcosm/catalog.json",
        ".microcosm/routes.json",
        ".microcosm/work_items.json",
        ".microcosm/events.jsonl",
        ".microcosm/evidence/",
        ".microcosm/graph.json",
        ".microcosm/python_lens.json",
    ]
    required_observatory_endpoints = [
        "/",
        "/status",
        "/tour",
        "/workingness-card",
        "/workingness",
        "/proof-lab",
        "/project/python-lens",
        "/project/observe",
        "/project/observatory-card",
        "/project/observatory",
        "/project/explain/<selected_route_id>",
    ]
    required_drilldown_routes = [
        "tour_front_door_status_route",
        "status_before_tour_recovery_route",
        "status_and_workingness_route",
        "python_navigation_route",
        "route_explanation_chain_route",
        "proof_lab_route",
    ]
    required_allowed_refs = [
        "atlas/entry_packet.json::local_first_screen_route",
        "atlas/entry_packet.json::reader_first_screen_routes",
        "atlas/entry_packet.json::cold_clone_probe_route",
        "microcosm tour --card <project>::state_refs",
        "microcosm tour --card <project>::status_card",
        "microcosm tour --card <project>::observatory",
        "microcosm tour --card <project>::proof_lab",
        "atlas/entry_packet.json::status_before_tour_recovery_route",
        "microcosm status --card <project>::front_door.project_state.recovery",
        "microcosm status --card <project>::front_door.project_recovery",
        "microcosm status --card <project>::front_door_status.blocking_surface_details.project_state",
        "microcosm status --card <project>::front_door.route_explanation",
        "microcosm status --card <project>::front_door.source_open_body_import_floor",
        "microcosm status --card <project>::macro_body_import_floor",
        "microcosm observe --card <project>",
        "microcosm observe <project>",
        "microcosm legibility-scorecard",
        "microcosm authority",
        "/workingness-card",
        "/workingness",
    ]
    if not path.is_file():
        return {
            "status": "missing",
            "source_ref": "atlas/entry_packet.json",
            "blocking_reasons": ["missing_entry_packet"],
            "authority": (
                "entry-packet route parity only; not source, release, provider, "
                "proof, or mutation authority"
            ),
        }
    try:
        payload = read_json_strict(path)
    except Exception as exc:
        return {
            "status": "blocked",
            "source_ref": "atlas/entry_packet.json",
            "blocking_reasons": ["invalid_entry_packet_json"],
            "parse_error": type(exc).__name__,
            "authority": (
                "entry-packet route parity only; not source, release, provider, "
                "proof, or mutation authority"
            ),
        }
    if not isinstance(payload, dict):
        payload = {}
    route = payload.get("local_first_screen_route")
    route = route if isinstance(route, dict) else {}
    reader_routes = payload.get("reader_first_screen_routes")
    reader_routes = reader_routes if isinstance(reader_routes, dict) else {}
    reader_route_rows = reader_routes.get("routes")
    reader_route_rows = reader_route_rows if isinstance(reader_route_rows, list) else []
    safe_to_show = route.get("safe_to_show")
    safe_to_show = safe_to_show if isinstance(safe_to_show, dict) else {}
    command_path = _string_list(route.get("command_path"))
    state_refs = _string_list(route.get("state_refs"))
    observatory_endpoints = _string_list(route.get("observatory_endpoints"))
    drilldown_routes = _string_list(route.get("drilldown_routes"))
    allowed_drilldowns = _string_list(payload.get("allowed_drilldowns"))
    receipt_dependencies = _string_list(payload.get("receipt_dependencies"))
    missing_commands = [
        command for command in required_commands if command not in command_path
    ]
    missing_state_refs = [ref for ref in required_state_refs if ref not in state_refs]
    missing_endpoints = [
        endpoint
        for endpoint in required_observatory_endpoints
        if endpoint not in observatory_endpoints
    ]
    missing_drilldown_routes = [
        route_id for route_id in required_drilldown_routes if route_id not in drilldown_routes
    ]
    missing_allowed_drilldowns = [
        ref
        for ref in (
            required_allowed_refs
            + required_commands
            + required_state_refs
            + required_observatory_endpoints
        )
        if ref not in allowed_drilldowns
    ]
    required_command_order = [
        "microcosm tour --card <project>",
        "microcosm status --card <project>",
        "microcosm workingness --card",
        "microcosm proof-lab --out /tmp/microcosm-proof-lab",
        "microcosm observe --card <project>",
        "microcosm serve <project> --host 127.0.0.1 --port 8765",
        "microcosm compile <project>",
        "microcosm python-lens <project>",
        "microcosm explain <project> <selected_route_id>",
        "microcosm evidence list <project> --limit 25",
    ]
    command_positions = {
        command: command_path.index(command)
        for command in required_command_order
        if command in command_path
    }
    command_order_mismatch = [
        f"{left} before {right}"
        for left, right in zip(required_command_order, required_command_order[1:])
        if left in command_positions
        and right in command_positions
        and command_positions[left] >= command_positions[right]
    ]
    first_command = str(payload.get("first_command") or "")
    primary_command = str(route.get("primary_first_screen_command") or "")
    command_mismatch = []
    if first_command != "microcosm tour --card <project>":
        command_mismatch.append("first_command")
    if primary_command != first_command:
        command_mismatch.append("primary_first_screen_command")
    route_selection_rule = str(route.get("route_selection_rule") or "")
    route_selection_required_phrases = [
        "selected_route_id emitted by tour --card, tour, or compile",
        (
            "readme_onboarding_route is a generated route only when the project "
            "has a README"
        ),
        "Empty or non-README folders can select missing_tests_route",
        "missing_tests_route when tests are absent",
    ]
    route_selection_missing_phrases = [
        phrase
        for phrase in route_selection_required_phrases
        if phrase not in route_selection_rule
    ]
    missing_route_selection_rule = bool(route_selection_missing_phrases)
    readme_text = _normalized_text(doc_text_by_rel.get("README.md", ""))
    readme_route_selection_required_phrases = [
        "`selected_route_id` from `microcosm tour --card .`, `microcosm tour .`, or `microcosm compile .`",
        "do not hardcode `readme_onboarding_route` for arbitrary folders",
        "`readme_onboarding_route` is present when the project has a README",
        "`missing_tests_route` when tests are absent",
        "empty/non-README folders can select `missing_tests_route`",
    ]
    readme_route_selection_missing_phrases = [
        phrase
        for phrase in readme_route_selection_required_phrases
        if phrase not in readme_text
    ]
    unsafe_flags = [
        key
        for key in [
            "source_files_mutated",
            "provider_calls_authorized",
            "release_authorized",
            "proof_correctness_claim",
        ]
        if safe_to_show.get(key) is not False
    ]
    required_reader_ids = {
        "public_github_visitor",
        "safety_evals_engineer",
        "hiring_reviewer",
        "peer_developer",
        "domain_specialist",
        "type_a_agent",
    }
    reader_ids = {
        str(row.get("reader_id"))
        for row in reader_route_rows
        if isinstance(row, dict) and row.get("reader_id")
    }
    reader_route_missing_ids = sorted(required_reader_ids - reader_ids)
    reader_route_missing_fields = [
        str(row.get("reader_id") or "<missing_reader_id>")
        for row in reader_route_rows
        if isinstance(row, dict)
        and not all(
            row.get(field)
            for field in (
                "reader_id",
                "first_screen_command",
                "next_command",
                "evidence_focus",
                "anti_misread",
            )
        )
    ]
    reader_route_contract_missing = []
    if reader_routes.get("shared_prerequisite_command") != (
        "microcosm tour --card <project>"
    ):
        reader_route_contract_missing.append("shared_prerequisite_command")
    if reader_routes.get("route_ref") != (
        "atlas/entry_packet.json::reader_first_screen_routes"
    ):
        reader_route_contract_missing.append("route_ref")
    if set(_string_list(route.get("reader_route_ids"))) != required_reader_ids:
        reader_route_contract_missing.append("local_first_screen_reader_route_ids")
    expected_cold_clone_command = "./bootstrap.sh"
    expected_cold_clone_receipt = ".microcosm/cold_clone_probe.json"
    stale_cold_clone_command = (
        "./bootstrap.sh --suite first-wave --emit receipts/cold_clone_probe.json"
    )
    probe_route = payload.get("cold_clone_probe_route")
    probe_route = probe_route if isinstance(probe_route, dict) else {}
    cold_clone_boundary_mismatches = []
    if payload.get("cold_clone_validation_command") != expected_cold_clone_command:
        cold_clone_boundary_mismatches.append("cold_clone_validation_command")
    if route.get("cold_clone_validation_suite") != expected_cold_clone_command:
        cold_clone_boundary_mismatches.append("local_first_screen_route")
    if probe_route.get("command") != expected_cold_clone_command:
        cold_clone_boundary_mismatches.append("cold_clone_probe_route.command")
    if probe_route.get("receipt_ref") != expected_cold_clone_receipt:
        cold_clone_boundary_mismatches.append("cold_clone_probe_route.receipt_ref")
    if expected_cold_clone_command not in allowed_drilldowns:
        cold_clone_boundary_mismatches.append("allowed_drilldowns.default_command")
    if expected_cold_clone_receipt not in allowed_drilldowns:
        cold_clone_boundary_mismatches.append("allowed_drilldowns.local_receipt")
    if expected_cold_clone_receipt not in receipt_dependencies:
        cold_clone_boundary_mismatches.append("receipt_dependencies.local_receipt")
    if stale_cold_clone_command in allowed_drilldowns:
        cold_clone_boundary_mismatches.append("allowed_drilldowns.tracked_emit")
    if "receipts/cold_clone_probe.json" in allowed_drilldowns:
        cold_clone_boundary_mismatches.append("allowed_drilldowns.tracked_receipt")
    if "receipts/cold_clone_probe.json" in receipt_dependencies:
        cold_clone_boundary_mismatches.append("receipt_dependencies.tracked_receipt")
    cold_start_text = _normalized_text(
        doc_text_by_rel.get("skills/cold_start_navigation.md", "")
    )
    cold_start_missing = [
        phrase
        for phrase in (
            required_commands
            + [
                "atlas/entry_packet.json::local_first_screen_route",
                "atlas/entry_packet.json::cold_clone_probe_route",
                "atlas/entry_packet.json::status_and_workingness_route",
                "atlas/entry_packet.json::proof_lab_route",
                "route_cards_by_id.status_and_workingness",
                "/project/observatory-card",
                "before `/project/observatory`",
                "Omit `--max-requests` only when you intentionally want an interactive server",
                "front_door.source_open_body_import_floor",
                "first-screen proof surfaces are visible",
                "Receipts are evidence drilldowns after the behavior route is visible",
                "Reader-Typed Branches",
                "atlas/entry_packet.json::reader_first_screen_routes",
                "six cold reader branches",
                "Domain specialist: run",
                "microcosm hello --reader domain_specialist <project>",
                "ORGANS.md#find-your-specialty",
                "explicit non-claim of domain correctness or expert review",
            ]
        )
        if phrase not in cold_start_text
    ]
    cold_start_route_selection_required_phrases = [
        "Use the `selected_route_id` emitted by `tour --card`, `tour`, or `compile`",
        "`readme_onboarding_route` exists only when the brought project has a README",
        "Do not hardcode `readme_onboarding_route` for arbitrary folders",
        "Empty/non-README folders can select `missing_tests_route`",
        "`missing_tests_route` when tests are absent",
    ]
    cold_start_route_selection_missing_phrases = [
        phrase
        for phrase in cold_start_route_selection_required_phrases
        if phrase not in cold_start_text
    ]
    blocking_reasons: list[str] = []
    if missing_commands:
        blocking_reasons.append("missing_local_first_screen_commands")
    if missing_state_refs:
        blocking_reasons.append("missing_state_refs")
    if missing_endpoints:
        blocking_reasons.append("missing_observatory_endpoints")
    if missing_drilldown_routes:
        blocking_reasons.append("missing_drilldown_routes")
    if missing_allowed_drilldowns:
        blocking_reasons.append("missing_allowed_drilldowns")
    if command_mismatch:
        blocking_reasons.append("first_command_mismatch")
    if command_order_mismatch:
        blocking_reasons.append("first_screen_command_order_mismatch")
    if missing_route_selection_rule:
        blocking_reasons.append("missing_route_selection_rule")
    if readme_route_selection_missing_phrases:
        blocking_reasons.append("readme_route_selection_rule_missing")
    if unsafe_flags:
        blocking_reasons.append("unsafe_safe_to_show_flags")
    if (
        reader_route_missing_ids
        or reader_route_missing_fields
        or reader_route_contract_missing
    ):
        blocking_reasons.append("reader_first_screen_routes_missing")
    if cold_clone_boundary_mismatches:
        blocking_reasons.append("cold_clone_local_receipt_boundary_mismatch")
    if cold_start_missing:
        blocking_reasons.append("cold_start_route_contract_missing")
    if cold_start_route_selection_missing_phrases:
        blocking_reasons.append("cold_start_route_selection_rule_missing")
    return {
        "status": PASS if not blocking_reasons else "blocked",
        "source_ref": "atlas/entry_packet.json",
        "first_command": first_command,
        "primary_first_screen_command": primary_command,
        "missing_local_first_screen_commands": missing_commands,
        "missing_state_refs": missing_state_refs,
        "missing_observatory_endpoints": missing_endpoints,
        "missing_drilldown_routes": missing_drilldown_routes,
        "missing_allowed_drilldowns": missing_allowed_drilldowns,
        "command_mismatch": command_mismatch,
        "command_order_mismatch": command_order_mismatch,
        "missing_route_selection_rule": missing_route_selection_rule,
        "route_selection_missing_phrases": route_selection_missing_phrases,
        "readme_route_selection_missing_phrases": (
            readme_route_selection_missing_phrases
        ),
        "unsafe_safe_to_show_flags": unsafe_flags,
        "reader_route_missing_ids": reader_route_missing_ids,
        "reader_route_missing_fields": reader_route_missing_fields,
        "reader_route_contract_missing": reader_route_contract_missing,
        "cold_clone_boundary_mismatches": cold_clone_boundary_mismatches,
        "cold_start_missing_phrases": cold_start_missing,
        "cold_start_route_selection_missing_phrases": (
            cold_start_route_selection_missing_phrases
        ),
        "blocking_reasons": blocking_reasons,
        "authority": (
            "entry-packet route parity only; not source, release, provider, "
            "proof, or mutation authority"
        ),
    }


def _entry_spine_claims(public_root: Path, expected_organs: list[str]) -> dict[str, Any]:
    """Spine coverage gate with two accepted claim modes.

    The canonical per-organ inventory is the generated ORGANS.md (gated by
    tests/test_organ_atlas.py). A doc may either (a) inline the full family-
    grouped inventory (inline_inventory: every accepted organ id present), or
    (b) route the inventory through the registry (registry_route: reference
    core/organ_registry.json + core/organ_evidence_classes.json and carry the
    inventory-only posture). Either keeps the public entry honest without
    forcing a hand-maintained wall.

    - Teleology: protects the public entry spine inventory claim from a vacuous 'all N organs enumerated below' coverage assertion that lists only a handful, and from undercount drift vs the registry's accepted organs.
    - Guarantee: returns a dict whose status == PASS only when each scanned doc (README Internal Runtime Spine, AGENTS Accepted Public Runtime Spine) either fully inlines every expected organ id with no duplicate, OR is an honest registry_route (names both registry surfaces + inventory-only posture) that makes no false inline-coverage claim; per-doc rows carry claim_mode/claimed_count/missing_organs/duplicate_organs/status.
    - Fails: a doc asserting inline coverage it does not deliver, a partial inline list, a duplicate organ token, or a non-route doc missing organs -> that doc's status 'blocked' -> overall status 'blocked' with the doc in blocked_docs.
    - Reads: <public_root>/README.md and <public_root>/AGENTS.md; expected_organs (registry-derived) passed in.
    - Writes: None.
    - When-needed: inspect when the receipt blocks on PUBLIC_ENTRY_SPINE_CLAIM_MISMATCH.
    - Escalates-to: ORGANS.md (generated by scripts/build_organ_atlas.py; gated by tests/test_organ_atlas.py).
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    expected_set = set(expected_organs)
    docs: dict[str, Any] = {}
    doc_specs = {
        "README.md": ("## Internal Runtime Spine", "## "),
        "AGENTS.md": (
            "## Accepted Public Runtime Spine",
            "## Concept And Mechanism Entry",
        ),
    }
    for rel, (start_heading, end_heading) in doc_specs.items():
        path = public_root / rel
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        normalized = _normalized_text(text)
        section = ""
        if start_heading in text:
            section = text.split(start_heading, 1)[1]
            if end_heading:
                if end_heading == "## ":
                    section = section.split("\n## ", 1)[0]
                elif end_heading in section:
                    section = section.split(end_heading, 1)[0]
        tokens = re.findall(r"`([a-z0-9_]+)`", section)
        counts: dict[str, int] = {}
        for tok in tokens:
            if tok in expected_set:
                counts[tok] = counts.get(tok, 0) + 1
        claimed_count = len(counts)
        missing = [organ_id for organ_id in expected_organs if organ_id not in counts]
        duplicates = sorted(tok for tok, count in counts.items() if count > 1)
        registry_route_present = (
            "core/organ_registry.json" in text
            and "core/organ_evidence_classes.json" in text
            and (
                "inventory-only route-alignment metadata" in normalized
                or "public entry inventory" in normalized
            )
        )
        expected_count = len(expected_organs)
        # A registry_route doc DEFERS enumeration to the registry / ORGANS.md; it
        # may not partially inline organs nor assert inline coverage it does not
        # deliver. Detect a self-contained inline coverage assertion ("all N
        # organs ... enumerated below") so a vacuous "all 47 covered below" while
        # listing only a handful cannot ride through as a route.
        section_normalized = _normalized_text(section).lower()
        inline_coverage_claim = bool(
            re.search(
                r"\b(all|every|each)\b[^.]{0,120}\borgans?\b[^.]{0,120}"
                r"\b(below|here|enumerat\w*|listed|inline)\b",
                section_normalized,
            )
        )
        full_inline = claimed_count == expected_count and not missing
        # A doc may NOT assert inline coverage it does not deliver, in any mode.
        # This kills the vacuous "all 47 organs enumerated below" + list-a-handful
        # bypass while leaving an honest pure route (which makes no such claim)
        # free to defer per-organ enumeration to the registry / ORGANS.md.
        false_coverage_claim = inline_coverage_claim and not full_inline
        if false_coverage_claim:
            claim_mode = "registry_route" if registry_route_present else "inline_inventory"
            row_missing = missing
            status = "blocked"
        elif full_inline:
            claim_mode = "inline_inventory"
            row_missing = missing
            status = PASS if not duplicates else "blocked"
        elif registry_route_present:
            # Pure route: enumeration deferred to the registry / ORGANS.md, whose
            # coverage is proven by the evidence-class registry + atlas gates.
            claim_mode = "registry_route"
            row_missing = []
            status = PASS
        else:
            claim_mode = "inline_inventory"
            row_missing = missing
            status = "blocked"
        docs[rel] = {
            "claim_mode": claim_mode,
            "registry_route_present": registry_route_present,
            "claimed_count": claimed_count,
            "expected_count": len(expected_organs),
            "missing_organs": row_missing,
            "unexpected_organs": [],
            "duplicate_organs": duplicates,
            "status": status,
        }
    blocked_docs = [rel for rel, row in docs.items() if row["status"] != PASS]
    return {
        "status": PASS if not blocked_docs else "blocked",
        "expected_source": (
            "core/organ_registry.json::implemented_organs[status=accepted_current_authority]"
        ),
        "expected_organ_count": len(expected_organs),
        "canonical_inventory_ref": (
            "ORGANS.md (generated by scripts/build_organ_atlas.py; "
            "gated by tests/test_organ_atlas.py)"
        ),
        "docs": docs,
        "blocked_docs": blocked_docs,
        "authority": (
            "public entry spine inventory alignment only; accepted status and "
            "counts are not progress, release, or proof authority; status card "
            "remains the runtime count lens"
        ),
    }


def _evidence_class_registry_summary(
    public_root: Path,
    expected_organs: list[str],
) -> dict[str, Any]:
    """Summarize the evidence-class registry and check it covers exactly the accepted organs with a fail-closed default.

    - Teleology: protects the evidence_class claim by ensuring every accepted organ has exactly one evidence-class row, no extra/duplicate organs, and the registry fail-closes with no silent default class.
    - Guarantee: returns a dict whose status == 'pass' only when there are no missing organs, no unexpected organs, no duplicate organ rows, and fail_closed_no_default is True; otherwise 'blocked' (or 'missing' when the file is absent), with class_count/organ_count/missing_organs/unexpected_organs/duplicate_organs.
    - Fails: absent core/organ_evidence_classes.json -> status 'missing' (missing_organs = all expected); any missing/unexpected/duplicate organ or fail_closed_no_default != True -> status 'blocked'.
    - Reads: <public_root>/core/organ_evidence_classes.json::organ_evidence_classes (via read_json_strict when present).
    - Writes: None.
    - When-needed: inspect when the receipt blocks on EVIDENCE_CLASS_REGISTRY_MISMATCH.
    - Escalates-to: core/organ_evidence_classes.json::organ_evidence_classes.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    path = public_root / "core/organ_evidence_classes.json"
    if not path.is_file():
        return {
            "status": "missing",
            "source_ref": "core/organ_evidence_classes.json",
            "class_count": 0,
            "organ_count": 0,
            "missing_organs": expected_organs,
            "unexpected_organs": [],
            "duplicate_organs": [],
            "fail_closed_no_default": False,
        }
    payload = read_json_strict(path)
    rows = _rows(payload if isinstance(payload, dict) else {}, "organ_evidence_classes")
    seen: set[str] = set()
    duplicates: set[str] = set()
    class_ids: set[str] = set()
    for row in rows:
        organ_id = str(row.get("organ_id") or "")
        evidence_class = str(row.get("evidence_class") or "")
        if organ_id in seen:
            duplicates.add(organ_id)
        if organ_id:
            seen.add(organ_id)
        if evidence_class:
            class_ids.add(evidence_class)
    expected_set = set(expected_organs)
    missing = [organ_id for organ_id in expected_organs if organ_id not in seen]
    unexpected = sorted(organ_id for organ_id in seen if organ_id not in expected_set)
    fail_closed = isinstance(payload, dict) and payload.get("fail_closed_no_default") is True
    return {
        "status": "pass" if not missing and not unexpected and not duplicates and fail_closed else "blocked",
        "source_ref": "core/organ_evidence_classes.json",
        "class_count": len(class_ids),
        "organ_count": len(seen),
        "missing_organs": missing,
        "unexpected_organs": unexpected,
        "duplicate_organs": sorted(duplicates),
        "fail_closed_no_default": fail_closed,
    }


def _agent_task_route_projection(
    public_root: Path,
    expected_organs: list[str],
    doc_text_by_rel: dict[str, str],
) -> dict[str, Any]:
    """Validate that agent entry defers to the generated task-route model.

    - Teleology: protects the agent-task-routing claim by ensuring AGENT_ROUTES.md + atlas/agent_task_routes.json form a complete generated projection that defers authority to organ rows/receipts/claim-ceilings, and that README/AGENTS route to it.
    - Guarantee: returns a dict whose status == PASS only when both surfaces exist, the JSON schema_version is 'microcosm_agent_task_routes_v1' with surface_role 'generated_agent_task_route_projection' and route_count matching, no duplicate task_class, every route+organ row carries its required fields, accepted organs are exactly covered (no missing/unexpected), AGENT_ROUTES.md carries its required phrases, and README/AGENTS carry the deferral links; else 'blocked' with blocking_reasons.
    - Fails: a missing surface -> 'blocked'+['missing_agent_task_route_surfaces']; unparseable JSON -> 'blocked'+['invalid_agent_task_route_json']+parse_error; schema/role/count/duplicate/incomplete/organ/markdown/deferral defects -> 'blocked' with the corresponding blocking_reason.
    - Reads: <public_root>/atlas/agent_task_routes.json, <public_root>/AGENT_ROUTES.md; doc_text_by_rel for README.md and AGENTS.md.
    - Writes: None.
    - When-needed: inspect when the receipt blocks on AGENT_TASK_ROUTE_PROJECTION_MISMATCH.
    - Escalates-to: atlas/agent_task_routes.json::routes / AGENT_ROUTES.md.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    json_rel = "atlas/agent_task_routes.json"
    md_rel = "AGENT_ROUTES.md"
    json_path = public_root / json_rel
    md_path = public_root / md_rel
    blocking_reasons: list[str] = []
    missing_surfaces = [
        rel
        for rel, path in ((json_rel, json_path), (md_rel, md_path))
        if not path.is_file()
    ]
    if missing_surfaces:
        return {
            "status": "blocked",
            "source_ref": json_rel,
            "missing_surfaces": missing_surfaces,
            "blocking_reasons": ["missing_agent_task_route_surfaces"],
            "authority": "agent task routing only; not release, provider, proof, or mutation authority",
        }
    try:
        payload = read_json_strict(json_path)
    except Exception as exc:
        return {
            "status": "blocked",
            "source_ref": json_rel,
            "missing_surfaces": [],
            "parse_error": type(exc).__name__,
            "blocking_reasons": ["invalid_agent_task_route_json"],
            "authority": "agent task routing only; not release, provider, proof, or mutation authority",
        }
    if not isinstance(payload, dict):
        payload = {}
    routes = _rows(payload, "routes")
    expected_set = set(expected_organs)
    seen_organs: set[str] = set()
    duplicate_task_classes = _duplicates(
        [str(row.get("task_class") or "") for row in routes if row.get("task_class")]
    )
    incomplete_routes: list[str] = []
    unexpected_organs: set[str] = set()
    for route in routes:
        task_class = str(route.get("task_class") or "")
        required_route_fields = (
            "task_class",
            "relevant_organs",
            "first_command",
            "allowed_scope",
            "authority_boundary",
            "evidence_ref",
            "receipt_ref",
            "stop_condition",
            "drilldown_target",
        )
        if not all(route.get(field) for field in required_route_fields):
            incomplete_routes.append(task_class or "<missing_task_class>")
        organs = route.get("relevant_organs")
        if not isinstance(organs, list) or not organs:
            incomplete_routes.append(f"{task_class or '<missing_task_class>'}.relevant_organs")
            continue
        for organ in organs:
            if not isinstance(organ, dict):
                incomplete_routes.append(f"{task_class}.invalid_organ_row")
                continue
            organ_id = str(organ.get("organ_id") or "")
            if organ_id in expected_set:
                seen_organs.add(organ_id)
            elif organ_id:
                unexpected_organs.add(organ_id)
            if not all(
                organ.get(field)
                for field in (
                    "display_name",
                    "first_command",
                    "scope_limit",
                    "drilldown_target",
                )
            ):
                incomplete_routes.append(f"{task_class}.{organ_id or 'organ'}")
    missing_organs = [organ_id for organ_id in expected_organs if organ_id not in seen_organs]
    md_text = doc_text_by_rel.get(md_rel)
    if md_text is None:
        md_text = md_path.read_text(encoding="utf-8") if md_path.is_file() else ""
    markdown_missing = [
        phrase
        for phrase in (
            "## Agent Task Route Table",
            "`task_class`",
            "atlas/agent_task_routes.json",
            "ORGANS.md#find-your-specialty",
        )
        if phrase not in md_text
    ]
    doc_deferral_missing = []
    for rel in ("README.md", "AGENTS.md"):
        normalized = _normalized_text(doc_text_by_rel.get(rel, ""))
        for phrase in (
            "[AGENT_ROUTES.md](AGENT_ROUTES.md)",
            "[ORGANS.md#find-your-specialty](ORGANS.md#find-your-specialty)",
        ):
            if phrase not in normalized:
                doc_deferral_missing.append(f"{rel}:{phrase}")
    if payload.get("schema_version") != "microcosm_agent_task_routes_v1":
        blocking_reasons.append("agent_task_route_schema_mismatch")
    if payload.get("surface_role") != "generated_agent_task_route_projection":
        blocking_reasons.append("agent_task_route_surface_role_mismatch")
    if payload.get("route_count") != len(routes):
        blocking_reasons.append("agent_task_route_count_mismatch")
    if duplicate_task_classes:
        blocking_reasons.append("duplicate_agent_task_classes")
    if incomplete_routes:
        blocking_reasons.append("incomplete_agent_task_routes")
    if missing_organs or unexpected_organs:
        blocking_reasons.append("agent_task_route_organ_mismatch")
    if markdown_missing:
        blocking_reasons.append("agent_task_route_markdown_missing")
    if doc_deferral_missing:
        blocking_reasons.append("agent_task_route_deferral_missing")
    return {
        "status": PASS if not blocking_reasons else "blocked",
        "source_ref": json_rel,
        "markdown_ref": md_rel,
        "schema_version": payload.get("schema_version"),
        "route_count": len(routes),
        "declared_route_count": payload.get("route_count"),
        "missing_surfaces": [],
        "missing_organs": missing_organs,
        "unexpected_organs": sorted(unexpected_organs),
        "duplicate_task_classes": duplicate_task_classes,
        "incomplete_routes": sorted(set(incomplete_routes)),
        "markdown_missing": markdown_missing,
        "doc_deferral_missing": doc_deferral_missing,
        "blocking_reasons": blocking_reasons,
        "authority": (
            "agent task routing only; authority remains on organ registry rows, "
            "receipts, and claim ceilings"
        ),
    }


def validate_public_entry_docs(
    root: str | Path,
    out_path: str | Path,
    *,
    command: str,
) -> dict[str, Any]:
    """Top-level public-entry-docs validator: assemble every sub-check into one fail-closed receipt and write it atomically.

    - Teleology: protects the standalone-public-entry claim and real-substrate import posture (presence of all REQUIRED_DOCS, required/forbidden phrases, registry/evidence/route/spine/CLI/cold-clone parity, no overclaim, no hardcoded organ count, no secret leak) so an agent can trust the public entry surfaces without rereading them.
    - Guarantee: returns and atomically writes a public_entry_docs_validation_receipt_v2 whose status == PASS only when blocking_codes is empty after every sub-check passes and the secret-exclusion scan reports zero blocking hits; otherwise status 'blocked' with the sorted blocking_codes set and full per-check detail.
    - Fails: any missing doc/required-phrase, forbidden phrase, registry/evidence/route/spine/CLI/entry-packet mismatch, overclaim, hardcoded organ count, or secret-scan hit -> appends the matching blocking_code -> receipt status 'blocked'. Underlying read_json_strict on a missing/invalid core/organ_registry.json (via _accepted_organs) raises before a receipt is produced.
    - Reads: <public_root>/{all REQUIRED_DOCS}, core/organ_registry.json, core/organ_evidence_classes.json, atlas/entry_packet.json, atlas/agent_task_routes.json, src/microcosm_core/cli.py, core/private_state_forbidden_classes.json.
    - Writes: out_path -> public_entry_docs_validation_receipt_v2 (atomic via write_json_atomic).
    - When-needed: the gate an agent runs/inspects before trusting the public entry docs or any release-boundary readiness signal they carry.
    - Escalates-to: receipt blocking_codes + per-check source_ref fields; tests/test_public_entry_docs.py.
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    public_root = Path(root).resolve(strict=False)
    output_file = Path(out_path)
    accepted = _accepted_organs(public_root)
    missing_docs: list[str] = []
    missing_required_phrases_by_doc: dict[str, list[str]] = {}
    forbidden_phrases_by_doc: dict[str, list[str]] = {}
    stale_first_slice_only_phrases: list[str] = []
    doc_text_by_rel: dict[str, str] = {}
    doc_paths: list[Path] = []
    for rel in REQUIRED_DOCS:
        path = public_root / rel
        doc_paths.append(path)
        if not path.is_file():
            missing_docs.append(rel)
            continue
        text = path.read_text(encoding="utf-8")
        doc_text_by_rel[rel] = text
        normalized = _normalized_text(text)
        missing_phrases = [
            phrase
            for phrase in REQUIRED_PHRASES_BY_DOC.get(rel, [])
            if phrase not in normalized
            and not _required_phrase_is_dynamic_inventory(phrase, accepted)
        ]
        if missing_phrases:
            missing_required_phrases_by_doc[rel] = missing_phrases
        forbidden_phrases = [
            phrase for phrase in FORBIDDEN_PHRASES_BY_DOC.get(rel, []) if phrase in text
        ]
        if forbidden_phrases:
            forbidden_phrases_by_doc[rel] = forbidden_phrases
        if "only implemented\n   organ here is `pattern_binding_contract`" in text:
            stale_first_slice_only_phrases.append(rel)
        if "only implemented organ here is `pattern_binding_contract`" in text:
            stale_first_slice_only_phrases.append(rel)

    entry_spine_claims = _entry_spine_claims(public_root, accepted)
    entry_packet_route_contract = _entry_packet_route_contract(
        public_root,
        doc_text_by_rel,
    )
    cli_first_screen_help_contract = _cli_first_screen_help_contract(public_root)
    duplicate_accepted_organs = _duplicates(accepted)
    missing_accepted_organs: list[str] = []
    unexpected_accepted_organs: list[str] = []
    evidence_class_registry = _evidence_class_registry_summary(public_root, accepted)
    agent_task_route_projection = _agent_task_route_projection(
        public_root,
        accepted,
        doc_text_by_rel,
    )
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    scan = _receipt_safe_scan(
        scan_paths(
            [public_root / rel for rel in REQUIRED_DOCS if (public_root / rel).is_file()],
            forbidden_classes=policy,
            display_root=public_root,
        )
    )
    public_entry_overclaim_by_doc = _public_entry_overclaim_hits(
        doc_text_by_rel, public_root
    )
    hardcoded_numeric_organ_count_claims = _hardcoded_numeric_organ_count_claims(
        doc_text_by_rel
    )
    blocking_codes: list[str] = []
    if missing_docs:
        blocking_codes.append("MISSING_PUBLIC_ENTRY_DOC")
    if missing_required_phrases_by_doc:
        blocking_codes.append("MISSING_REQUIRED_ENTRY_PHRASE")
    if stale_first_slice_only_phrases:
        blocking_codes.append("STALE_FIRST_SLICE_ONLY_ENTRY_TEXT")
    if forbidden_phrases_by_doc:
        blocking_codes.append("PUBLIC_ENTRY_DOC_ROUTE_DRIFT")
    if missing_accepted_organs or unexpected_accepted_organs or duplicate_accepted_organs:
        blocking_codes.append("ACCEPTED_ORGAN_REGISTRY_MISMATCH")
    if evidence_class_registry["status"] != PASS:
        blocking_codes.append("EVIDENCE_CLASS_REGISTRY_MISMATCH")
    if agent_task_route_projection["status"] != PASS:
        blocking_codes.append("AGENT_TASK_ROUTE_PROJECTION_MISMATCH")
    if entry_spine_claims["status"] != PASS:
        blocking_codes.append("PUBLIC_ENTRY_SPINE_CLAIM_MISMATCH")
    if entry_packet_route_contract["status"] != PASS:
        blocking_codes.append("ENTRY_PACKET_ROUTE_CONTRACT_MISMATCH")
    if cli_first_screen_help_contract["status"] != PASS:
        blocking_codes.append("CLI_FIRST_SCREEN_HELP_CONTRACT_MISMATCH")
    if scan["blocking_hit_count"]:
        blocking_codes.append("SECRET_EXCLUSION_SCAN_BLOCKED")
    if public_entry_overclaim_by_doc:
        blocking_codes.append("PUBLIC_ENTRY_OVERCLAIM")
    if hardcoded_numeric_organ_count_claims:
        blocking_codes.append("HARDCODED_PUBLIC_ENTRY_ORGAN_COUNT")

    blocking_codes = sorted(set(blocking_codes))
    status = PASS if not blocking_codes else "blocked"
    receipt = {
        "schema_version": "public_entry_docs_validation_receipt_v2",
        "checker_id": CHECKER_ID,
        "fixture_id": FIXTURE_ID,
        "status": status,
        "command": command,
        "required_docs": REQUIRED_DOCS,
        "missing_docs": missing_docs,
        "missing_required_phrases_by_doc": missing_required_phrases_by_doc,
        "forbidden_phrases_by_doc": forbidden_phrases_by_doc,
        "public_entry_overclaim_by_doc": public_entry_overclaim_by_doc,
        "hardcoded_numeric_organ_count_claims": hardcoded_numeric_organ_count_claims,
        "stale_first_slice_only_phrases": sorted(set(stale_first_slice_only_phrases)),
        "accepted_current_authority_organs": accepted,
        "duplicate_accepted_organs": _duplicates(accepted),
        "entry_spine_claims": entry_spine_claims,
        "entry_packet_route_contract": entry_packet_route_contract,
        "cli_first_screen_help_contract": cli_first_screen_help_contract,
        "evidence_class_registry": evidence_class_registry,
        "agent_task_route_projection": agent_task_route_projection,
        "missing_accepted_organs": missing_accepted_organs,
        "unexpected_accepted_organs": unexpected_accepted_organs,
        "duplicate_accepted_organs": duplicate_accepted_organs,
        "deferred_organs": [],
        "blocking_codes": blocking_codes,
        "secret_exclusion_scan": scan,
        "payload_boundary": public_payload_boundary(
            boundary_id="public_entry_docs",
            command=command,
            surface_ref=_display(output_file, public_root=public_root),
        ),
        "authority_ceiling": {
            "status": PASS,
            "entry_docs_authority": "public_entry_navigation_and_real_substrate_posture",
            "lean_lake_authorized": "bounded_public_witness_only",
            "trading_or_financial_advice_authorized": False,
            "hosted_release_operations_authorized": False,
            "secret_export_authorized": False,
            "metadata_only_standin_policy": "forbidden_when_real_non_secret_macro_body_is_importable",
            "macro_substrate_import_policy": "encourage_maximum_non_secret_macro_substrate_import",
            "body_copied_requires_source_target_validation": True,
        },
        "anti_claim": "Public entry-doc validation proves standalone public entry documentation, cold-start navigation presence, and the real-substrate import posture: Microcosm should carry as much non-secret macro substrate as possible. It does not authorize Lean/Lake beyond the bounded public witness organ, hosted release operations, publication, recipient sends, credentialed provider calls, secret export, raw operator voice, slurs or abusive wording, private personal material, or whole-system correctness; it also does not allow metadata-only stand-ins when a real non-secret macro body can be imported.",
        "receipt_paths": [_display(output_file, public_root=public_root)],
    }
    write_json_atomic(output_file, receipt)
    return receipt


def _parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for the public-entry-docs validator.

    - Teleology: protects the CLI entrypoint by declaring the required --root and --out arguments the validator runs against.
    - Guarantee: returns an ArgumentParser requiring --root and --out.
    - Fails: at parse time, a missing --root or --out -> argparse SystemExit(2) with a usage error (raised by parse_args in main, not here).
    - Writes: None.
    """
    parser = argparse.ArgumentParser(description="Validate public entry docs")
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: run validate_public_entry_docs and return a pass/fail exit code.

    - Teleology: protects the command-line release-gate use of this validator by mapping the receipt status onto a process exit code.
    - Guarantee: returns 0 when the written receipt status == PASS, else 1.
    - Fails: missing required CLI args -> argparse SystemExit(2); a non-PASS receipt -> return 1 (non-zero exit).
    - Reads: same surfaces as validate_public_entry_docs (via --root).
    - Writes: --out receipt (via validate_public_entry_docs).
    - Non-goal: does not authorize release, provider calls, private-root equivalence, static-analysis authority, or whole-system correctness.
    """
    args = _parser().parse_args(argv)
    command = (
        "python -m microcosm_core.validators.public_entry_docs "
        f"--root {args.root} --out {args.out}"
    )
    receipt = validate_public_entry_docs(args.root, args.out, command=command)
    return 0 if receipt["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
