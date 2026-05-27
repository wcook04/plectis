#!/usr/bin/env python3
"""
[PURPOSE]
- Teleology: Make macro pattern substrate bindings checkable instead of
  relying on prose coverage summaries.
- Mechanism: Read the extracted pattern ledger plus the substrate-binding
  sidecars, recompute evidence classes, validate concrete refs, and write a
  generated validation report under state/microcosm_portfolio.
- Boundary: This validates macro-side pattern provenance. It does not rebuild
  the public microcosm and does not expose private raw content.

[INTERFACE]
- CLI: --check, --report, --json, --write, --write-sidecars, --commit.
- Exports: build_extracted_pattern_substrate_validation_report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


LEDGER_REL = "state/microcosm_portfolio/extracted_patterns_ledger.jsonl"
BINDINGS_REL = "state/microcosm_portfolio/extracted_pattern_substrate_bindings.json"
WEAK_BINDINGS_REL = "state/microcosm_portfolio/extracted_pattern_weak_bindings.json"
VALIDATION_REPORT_REL = "state/microcosm_portfolio/extracted_pattern_substrate_validation_report.json"
COVERAGE_REPORT_REL = "state/microcosm_portfolio/extracted_pattern_substrate_coverage_report.md"
GOVERNING_STANDARD_REL = "codex/standards/std_extracted_pattern_substrate_bindings.json"

EXPECTED_BINDING_SCHEMA = "extracted_pattern_substrate_bindings_v1"
EXPECTED_WEAK_SCHEMA = "extracted_pattern_weak_bindings_v1"

GROUNDING_CLASS_ORDER = [
    "strong_high_authority",
    "doctrine_only",
    "code_or_state_no_standard",
    "code_or_state_no_paper_module",
    "standard_no_code_validator_or_state",
    "weak_ref_count_lte_2",
    "private_fixture_needed",
    "public_projection_candidate_by_risk_and_novelty",
]

WEAK_CLASS_DEFAULTS: dict[str, dict[str, str]] = {
    "doctrine_only": {
        "why_weak": "Rows route mostly to paper modules or skills. They may motivate real system behavior, but they do not yet name an implementation, validator, generated sidecar, receipt, or state surface.",
        "repair_rule": "Bind each row to at least one code owner or generated artifact. If no code exists, add an explicit not_yet_built status and a synthetic fixture plan before public projection.",
    },
    "code_or_state_no_standard": {
        "why_weak": "Rows have code, proof, state, or command evidence, but the row does not route to a governing standard. This makes the evidence real but under-governed.",
        "repair_rule": "Add the governing standard ref when one already exists; otherwise route a standard gap into pattern_deliverables or a standard candidate.",
    },
    "code_or_state_no_paper_module": {
        "why_weak": "Rows have code, proof, state, command, validator, receipt, or structured-artifact evidence, but the row does not route to a paper module. The tests or artifacts may be more authoritative than the prose, but future reconstruction lacks doctrine that explains the invariant.",
        "repair_rule": "Bind each row to an existing paper module when one already explains the invariant. Otherwise add an explicit doctrine_gap in the detailed binding and create a synthetic fixture before projecting it as a public leaf.",
    },
    "standard_no_code_validator_or_state": {
        "why_weak": "Rows cite a standard or structured standard artifact but do not cite a code owner, validator, proof, runtime state, or receipt. Some have real implementation elsewhere, but the pattern row does not prove it.",
        "repair_rule": "Prefer adding existing validator/test/generated sidecar refs. If the implementation is intentionally absent, add a candidate fixture and not_yet_built marker.",
    },
    "weak_ref_count_lte_2": {
        "why_weak": "Rows have one or two source refs. Some may be valid narrow patterns, but most cannot yet support a future leaf's standard/code/validator/anti-claim stack.",
        "repair_rule": "For high-novelty rows, bind at least one standard or standard gap plus one validator/proof/receipt or fixture plan.",
    },
    "private_fixture_needed": {
        "why_weak": "Rows cite or imply private state such as raw seed, Task Ledger, prompt shelf, bridge/provider/cockpit runtime, or live operator surfaces. Real state can motivate the pattern, but public proof needs synthetic fixtures.",
        "repair_rule": "Create synthetic fixtures that preserve structure while replacing live content. Mark macro-only when structure itself would reveal sensitive operation.",
    },
}

FOUNDATION_COMBINATION_ROUTE_DEFS: list[dict[str, Any]] = [
    {
        "route_id": "standards_registry_executable_grammar_foundation",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
        ],
        "target_existing_organs": [
            "root_binding_and_executable_grammar",
            "executable_doctrine_grammar",
            "pattern_binding_contract",
        ],
        "pattern_ids": [
            "standards_registry_executable_grammar_index",
        ],
        "why_impressive": (
            "The standards registry is the executable contents page for the doctrine lattice: "
            "the root registry, group indexes, type plane, core-authority index, lattice "
            "registry, standards option surface, and registry tests make hundreds of "
            "standards discoverable without grep or parallel ontology."
        ),
        "candidate_fixture": (
            "Synthetic six-standard registry with two group authority indexes, one type-plane "
            "row, one core-authority subset, one lattice artifact-kind row, one standards "
            "option-surface card, and failing fixtures for missing group index, missing "
            "standard ref, stale lattice graph, and treating generated option rows as source."
        ),
        "anti_claim_floor": (
            "This route proves registry-driven discovery and standards-to-projection wiring "
            "for the fixture; it does not claim every individual standard is complete, that "
            "generated option surfaces are source authority, or that public Microcosm can "
            "copy private registry neighborhoods without disclosure and fixture gates."
        ),
        "next_refinement_move": (
            "Keep standards registry work as the root executable-grammar foundation. Future "
            "imports should open codex_standards_registry, standards_as_executable_wiki, "
            "std_standards_registry, std_standards_group_index, std_standard_type_plane, "
            "std_lattice_registry, standards option-surface cards, and focused registry/"
            "lattice tests before adding local standards-routing doctrine."
        ),
    },
    {
        "route_id": "principle_scope_axiom_candidate_lattice_root_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "constitutional_doctrine",
            "navigation_control",
        ],
        "target_existing_organs": [
            "pattern_binding_contract",
            "executable_doctrine_grammar",
            "root_binding_and_executable_grammar",
            "proof_diagnostic_evidence_spine",
            "navigation_hologram_route_plane",
        ],
        "pattern_ids": [
            "principle_scope_axiom_candidate_lattice",
        ],
        "why_impressive": (
            "The principle/axiom lattice becomes reusable only when scoped principles, "
            "teleology refs, candidate-pressure packets, non-law authority posture, "
            "promotion cadence, violation predicates, and option-surface cards travel "
            "as one root doctrine grammar instead of being rediscovered from raw "
            "principle rows, candidate axiom files, or entry-packet warnings."
        ),
        "candidate_fixture": (
            "Synthetic doctrine corpus with four scoped principles, two candidate axioms "
            "under one teleology, one anti-axiom, one refinement-plan row, one "
            "candidate-runtime-pressure entry, and negative fixtures for treating a "
            "candidate as active law, missing violation predicates, missing teleology "
            "refs, and standards card facets declared as strings."
        ),
        "anti_claim_floor": (
            "This route proves scoped principle and candidate-axiom routing for synthetic "
            "fixtures and live owner surfaces. It does not promote any candidate axiom "
            "to active doctrine, certify principle truth timelessly, rewrite raw seed, "
            "make option-surface projections source authority, bypass operator/controller "
            "promotion, or authorize public release of private principle neighborhoods."
        ),
        "next_refinement_move": (
            "Keep principle_scope_axiom_candidate_lattice under root_binding_and_"
            "executable_grammar. Future doctrine-lattice work should open principle_"
            "scope_ontology, raw_seed_principle_scope, std_raw_seed_principles, "
            "std_system_axiom_candidate, agent_operating_packet, candidate runtime "
            "pressure policy, standards and principles option-surface cards, and "
            "focused agent-operating/diagnostic/standards-card tests before changing "
            "principle scope, axiom candidates, or promotion doctrine."
        ),
    },
    {
        "route_id": "kernel_cli_typed_router_navigation_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "navigation_control",
            "standard_owned_option_surfaces",
        ],
        "target_existing_organs": [
            "navigation_hologram_route_plane",
            "root_binding_and_executable_grammar",
            "proof_diagnostic_evidence_spine",
            "pattern_binding_contract",
        ],
        "pattern_ids": [
            "kernel_cli_typed_router",
        ],
        "why_impressive": (
            "The kernel CLI is reusable only when first-contact commands, typed "
            "drilldowns, kind/card row selection, banned-route replacement, route "
            "leases, ceremony budgets, and projection-not-authority receipts travel "
            "as one navigation contract instead of being rediscovered from kernel.py, "
            "entry packets, or option-surface prose."
        ),
        "candidate_fixture": (
            "Synthetic mini-kernel with --info, --entry, --context-pack, --kind-atlas, "
            "--option-surface, and --row commands; one banned-route replacement; one "
            "route-lease admission receipt; one ceremony-budget tier; and negative "
            "fixtures for using option surfaces as first-contact control, treating "
            "generated rows as source authority, and bypassing owner validators."
        ),
        "anti_claim_floor": (
            "This route proves typed kernel routing and command discipline for live "
            "owner surfaces and synthetic fixtures. It does not make Atlas projections "
            "source authority, permit every kernel flag as first-contact control, expose "
            "private payloads, authorize public release, or replace source files, "
            "standards, tests, and owner tools as authority."
        ),
        "next_refinement_move": (
            "Keep kernel_cli_typed_router under navigation_hologram_route_plane with "
            "root_binding_and_executable_grammar and proof_diagnostic_evidence_spine "
            "as carry roots. Future kernel-routing work should open kernel.py, "
            "comprehension_snapshot.py, navigate.py, navigation_context_pack.py, "
            "kind_atlas.py, standard_option_surface.py, std_agent_entry_surface, "
            "navigation_seed, bootstrap, navigation_metabolism, and focused entry/"
            "kind/context/option-surface tests before adding local command doctrine."
        ),
    },
    {
        "route_id": "idea_microcosm_metabolism_meta_loop_laboratory_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "raw_seed_to_doctrine_metabolism",
            "public_microcosm_substrate_boundary",
            "voice_memory_alchemy",
            "navigation_projection_route_plane",
        ],
        "target_existing_organs": [
            "voice_to_doctrine_self_improvement_loop",
            "raw_seed_alchemy_review_suborgan",
            "navigation_hologram_route_plane",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
            "pattern_binding_contract",
        ],
        "pattern_ids": [
            "idea_microcosm_metabolism_meta_loop",
        ],
        "why_impressive": (
            "The Laboratory meta-loop becomes reusable only when microcosm minting, "
            "scoring, projection, sanitization, fixture build, proof-gating, negative "
            "cases, source-open product boundary, and generated-projection authority "
            "ceiling travel as one contract instead of being rediscovered from legacy "
            "idea-microcosm prose, private raw-seed lanes, or public Microcosm docs."
        ),
        "candidate_fixture": (
            "Three synthetic idea cards pass through score -> project -> sanitize -> "
            "fixture-build -> gate: one row is rejected for raw/operator/private leakage, "
            "one row is accepted as a public-safe voice-to-doctrine fixture, and one row "
            "scaffolds a tiny leaf only after owner-surface validation and closeout "
            "receipts are present."
        ),
        "anti_claim_floor": (
            "This route proves the Laboratory meta-loop over public-safe synthetic idea "
            "cards and live voice-to-doctrine owner surfaces. It does not make Laboratory "
            "receipts product authority, collapse Laboratory into public Microcosm, export "
            "raw operator voice or private threads, authorize source mutation, or treat "
            "generated projections as source truth."
        ),
        "next_refinement_move": (
            "Keep idea_microcosm_metabolism_meta_loop under voice_to_doctrine_"
            "self_improvement_loop with microcosm_substrate as the public product boundary. "
            "Future agents should open idea_microcosm_metabolism, microcosm_substrate, "
            "the voice-to-doctrine organ, its standard, fixture manifest, acceptance "
            "receipt, route-readiness audit, and focused option-surface tests before "
            "adding new Laboratory, Microcosm, or raw-seed metabolism doctrine."
        ),
    },
    {
        "route_id": "standard_type_plane_single_drop_grammar",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
        ],
        "target_existing_organs": [
            "pattern_binding_contract",
            "executable_doctrine_grammar",
        ],
        "pattern_ids": [
            "standard_type_plane_single_drop_artifact_contract",
        ],
        "why_impressive": (
            "A single standards type-plane row becomes an executable artifact-kind contract: "
            "source authority, read/write contracts, option surface, validation probe, "
            "mutation lane, projection refs, and renderer-passport coverage fan out from "
            "one root binding instead of being rediscovered in every UI, atlas, or wiki layer."
        ),
        "candidate_fixture": (
            "Synthetic std_standard_type_plane fixture with one artifact kind and no explicit "
            "renderer profile; renderer_passports auto-derives source_authority, validation "
            "probe, mutation lane, projection refs, target option surface, and receipt policy, "
            "then stale-projection check requires build_renderer_passports.py."
        ),
        "anti_claim_floor": (
            "This route proves single-drop artifact-kind registration and projection-not-authority "
            "behavior for the fixture; it does not make generated passports, atlas rows, command "
            "outputs, frontend views, or public exports source authority."
        ),
        "next_refinement_move": (
            "Keep type-plane and renderer-passport work under the root binding/executable grammar "
            "organ; future artifact-kind imports must cite std_standard_type_plane, the paper-module "
            "roof, renderer-passport builder, option-surface card, and focused renderer tests."
        ),
    },
    {
        "route_id": "executable_grammar_metabolism_root_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "pattern_deliverables_registry",
        ],
        "target_existing_organs": [
            "root_binding_and_executable_grammar",
            "pattern_binding_contract",
            "executable_doctrine_grammar",
        ],
        "pattern_ids": [
            "executable_grammar_metabolism",
        ],
        "why_impressive": (
            "Standards become executable grammar only when read contracts, write contracts, "
            "projection contracts, and repair-routing contracts are bound to standards, "
            "paper modules, option surfaces, renderer passports, public-safe specimens, "
            "validation receipts, and anti-claims as one root organ."
        ),
        "candidate_fixture": (
            "Public-safe executable grammar specimen plus one synthetic standards row: "
            "grammar rules must emit accept, block, and repair outcomes; source-capsule "
            "provenance and anti-claims must travel with each decision; negative fixtures "
            "fail when private registry material, raw operator notes, provider transcripts, "
            "publication claims, or generated projections are treated as source authority."
        ),
        "anti_claim_floor": (
            "This route proves standards-as-executable-grammar mechanics for the fixture "
            "and live owner surfaces; it does not prove every standard is complete, make "
            "generated projections authority, or authorize public release of private "
            "registry neighborhoods."
        ),
        "next_refinement_move": (
            "Keep executable_grammar_metabolism under root_binding_and_executable_grammar. "
            "Future standards-as-grammar imports should open this route with "
            "standards_registry_executable_grammar_foundation, standard_type_plane_single_drop_grammar, "
            "standards_as_executable_wiki, the public-safe grammar specimen, and focused "
            "binding/readiness tests before adding local doctrine."
        ),
    },
    {
        "route_id": "config_authority_registry_root_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
        ],
        "target_existing_organs": [
            "root_binding_and_executable_grammar",
            "pattern_binding_contract",
            "executable_doctrine_grammar",
        ],
        "pattern_ids": [
            "config_authority_registry",
        ],
        "why_impressive": (
            "The config authority registry turns behavior-affecting settings into a typed "
            "lookup plane: row contract, effective trace, override chain, safe edit gate, "
            "redaction policy, API, option surface, frontend consumers, and stale-projection "
            "diagnostics are bound before anyone edits master_config or guesses from grep."
        ),
        "candidate_fixture": (
            "Synthetic five-decision config registry with root, domain, generated, frontend, "
            "and secret/private rows; include one conflict where two owners claim the same "
            "key, one config_ref fallback diagnostic, one stale generated projection, and "
            "negative cases for unregistered keys, raw secret values, and generated rows "
            "treated as source authority."
        ),
        "anti_claim_floor": (
            "This route proves config-authority lookup, effective-trace routing, and fixture "
            "validation for the public-safe shape; it does not make master_config the sole "
            "authority, authorize mutation without row-level writers, publish private values, "
            "or make codex/derived/config_authority_registry.json source authority."
        ),
        "next_refinement_move": (
            "Keep config_authority_registry under root_binding_and_executable_grammar. Future "
            "config-plane imports should open std_config_authority_registry, std_tool_config, "
            "federated_config_plane, the config_authorities option surface, ConfigsBoard "
            "config_ref consumer, the API surface, and focused config-authority tests before "
            "changing config doctrine or Settings behavior."
        ),
    },
    {
        "route_id": "marked_region_projection_root_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
        ],
        "target_existing_organs": [
            "root_binding_and_executable_grammar",
            "pattern_binding_contract",
            "executable_doctrine_grammar",
            "navigation_hologram_route_plane",
        ],
        "pattern_ids": [
            "marked_region_projection",
        ],
        "why_impressive": (
            "Marked region projection turns generated markdown slices into named, "
            "source-coupled replace/extract contracts: BEGIN/END markers, builder "
            "ownership, hand-authored framing preservation, check-mode drift "
            "comparison, and projection-not-authority boundaries become reusable "
            "across bootstrap, adapter, routing, skill, and paper-module surfaces."
        ),
        "candidate_fixture": (
            "Synthetic markdown document with three managed regions and hand-authored "
            "framing. Positive cases replace one region, extract another, preserve "
            "surrounding prose, compare fresh render to current content without "
            "writing, and normalize documented volatile fields. Negative cases fail "
            "when markers are missing, begin/end ids disagree, duplicate markers are "
            "ambiguous, or generated region bodies are hand-edited as source doctrine."
        ),
        "anti_claim_floor": (
            "This route proves marked-region projection mechanics for fixtures and "
            "live projection helpers; it does not certify every generated region is "
            "fresh, make markdown projections source authority, authorize hand edits "
            "inside generated blocks, or require a mass migration of every builder."
        ),
        "next_refinement_move": (
            "Keep marked_region_projection under root_binding_and_executable_grammar "
            "with navigation_hologram_route_plane as the consumer-facing route sibling. "
            "Future agents should open std_marked_region_projection, markdown/doc-meta "
            "standards, agent_bootstrap_projection.py, paper_modules.py, "
            "routing_projection.py, projection checkers, generated-region examples, "
            "and focused replace/extract tests before adding projection doctrine or "
            "Microcosm leaves."
        ),
    },
    {
        "route_id": "mechanism_facet_manifest_root_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
        ],
        "target_existing_organs": [
            "root_binding_and_executable_grammar",
            "pattern_binding_contract",
            "executable_doctrine_grammar",
            "navigation_hologram_route_plane",
        ],
        "pattern_ids": [
            "mechanism_facet_manifest",
        ],
        "why_impressive": (
            "The mechanism facet manifest turns mechanism doctrine into typed, ignorable, "
            "versioned facets: inputs, outputs, invariants, examples, edge cases, owner "
            "loci, trace-derived candidates, replay receipts, and missing-facet "
            "diagnostics become separately queryable without weakening the base "
            "mechanism standard."
        ),
        "candidate_fixture": (
            "Synthetic two-mechanism fixture with one accepted owner packet, one "
            "candidate-only projection claim, one consumer requesting a single facet, "
            "one missing-facet finding, one superseded claim, one replay receipt, and "
            "negative cases for treating candidate facets as accepted doctrine or "
            "reading whole mechanism bodies when the facet route is sufficient."
        ),
        "anti_claim_floor": (
            "This route proves typed mechanism-facet routing and candidate-to-accepted "
            "boundaries for the fixture and live navigation-mechanism substrate. It "
            "does not promote candidate facets to mechanism law, certify every mech_* "
            "row has complete facets, or make trace-derived/provider suggestions "
            "source authority before owner acceptance."
        ),
        "next_refinement_move": (
            "Keep mechanism_facet_manifest under root_binding_and_executable_grammar "
            "with navigation_hologram_route_plane as its consumer-facing route sibling. "
            "Future agents should open std_mechanism_facet_manifest, "
            "std_mechanism_projection_ledger, validate_navigation_mechanism_facets.py, "
            "navigation_mechanism_factory.py, navigation_mechanism_candidates option "
            "cards, replay receipts, and focused tests before adding mechanism-facet "
            "doctrine or public Microcosm leaves."
        ),
    },
    {
        "route_id": "json_facets_projection_root_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "navigation_projection_route_plane",
        ],
        "target_existing_organs": [
            "root_binding_and_executable_grammar",
            "pattern_binding_contract",
            "executable_doctrine_grammar",
            "navigation_hologram_route_plane",
        ],
        "pattern_ids": [
            "json_facets_projection",
        ],
        "why_impressive": (
            "JSON facets turn authored JSON doctrine, standards, and annex notes into "
            "typed, schema-hashed atom rows: consumers can read title, claim, contract, "
            "mechanism, trigger, and anti-pattern slices without flattening every JSON "
            "artifact into one opaque body or treating generated state JSON as authority."
        ),
        "candidate_fixture": (
            "Synthetic repo with one doctrine node, one standard JSON, one annex-note row, "
            "and a semantic route map. Positive cases extract only the declared facets, "
            "map them through std_semantic_routing axis families, and force full re-embed "
            "when std_json_facets changes. Negative cases fail for generated state JSON, "
            "bespoke facet names, whole-body-only reads, and stale schema-hash reuse."
        ),
        "anti_claim_floor": (
            "This route proves typed JSON-facet extraction, schema-hash drift gating, "
            "and route-plane participation for live adapters and fixtures; it does not "
            "make generated JSON authority, certify every JSON option surface fresh, "
            "authorize private state release, or replace source standards with embedding "
            "cache rows."
        ),
        "next_refinement_move": (
            "Keep json_facets_projection under root_binding_and_executable_grammar with "
            "navigation_hologram_route_plane as the consumer-facing sibling. Future agents "
            "should open std_json_facets, std_semantic_routing, embedding_sources.py, "
            "embedding_substrate.py, semantic_routing.py, the embedding/semantic-routing "
            "paper modules, and focused JSON-facet tests before adding JSON projection "
            "doctrine, option-surface bands, or Microcosm leaves."
        ),
    },
    {
        "route_id": "command_output_projection_runtime_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "navigation_projection_route_plane",
            "kernel_command_projection_runtime",
        ],
        "target_existing_organs": [
            "root_binding_and_executable_grammar",
            "pattern_binding_contract",
            "executable_doctrine_grammar",
            "navigation_hologram_route_plane",
        ],
        "pattern_ids": [
            "command_output_projection",
        ],
        "why_impressive": (
            "Command-output projection turns CLI stdout into typed status, receipt, "
            "artifact-set, and drilldown envelopes: consumers can request card, full, "
            "or row bands with currentness, omission receipts, validation contracts, "
            "and auditable back-compat boundaries instead of grepping prose."
        ),
        "candidate_fixture": (
            "Synthetic three-command fixture with one status card, one receipt/artifact "
            "projection, one row drilldown, one sidecar-routed heavy payload, and one "
            "consumer reading only the envelope. Positive cases require canonical "
            "envelope fields, row_id shape, peer omission receipts, runnable drilldown "
            "and evidence commands, projected-smaller proof, and sidecar receipts. "
            "Negative cases fail for unpopulated-band synthesis, missing omission "
            "receipts, changed default output, private payload leakage, or downstream "
            "raw-stdout parsing."
        ),
        "anti_claim_floor": (
            "This route proves command-output projection envelopes, audit, duplication "
            "checks, sidecar containment, and public macro-tool import for registered "
            "commands and fixtures. It does not make every command projected by "
            "default, certify every CLI output, remove default back-compat, or "
            "authorize private payload bodies in Microcosm."
        ),
        "next_refinement_move": (
            "Keep command_output_projection under root_binding_and_executable_grammar "
            "with navigation_hologram_route_plane as the consumer-facing sibling. Future "
            "agents should open std_command_output_projection, std_typed_response_map, "
            "std_response_surfaces, command_output_projection.py, command_output_audit.py, "
            "command_output_sidecar.py, registered command projection builders, focused "
            "projection tests, duplication audits, and the Microcosm macro tool before "
            "adding command-output doctrine, option-surface bands, or public leaves."
        ),
    },
    {
        "route_id": "atlas_navigation_bands_option_surface_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "navigation_projection_route_plane",
        ],
        "target_existing_organs": [
            "navigation_hologram_route_plane",
            "root_binding_and_executable_grammar",
            "pattern_binding_contract",
            "executable_doctrine_grammar",
        ],
        "pattern_ids": [
            "atlas_navigation_bands",
        ],
        "why_impressive": (
            "Atlas navigation bands become reusable when compressed, technical, evidence, "
            "and sandbox entry levels are governed as standard-owned option-surface bands "
            "with omission receipts, route leases, source-coupling checks, and explicit "
            "public/private boundaries instead of a one-off self-indexing leaf."
        ),
        "candidate_fixture": (
            "Synthetic atlas with four bands over six rows: cluster-first compressed entry, "
            "technical card drilldown, evidence receipt drilldown, and sandbox fixture view. "
            "Positive cases require each band to name its owner, allowed caller, omission "
            "receipt, source authority, and validation hook. Negative cases fail when a "
            "generated atlas row is treated as source authority, a private body leaks into a "
            "public band, or an agent bypasses the entry packet for grep."
        ),
        "anti_claim_floor": (
            "This route proves banded Atlas entry mechanics over live option-surface and "
            "navigation-route substrate plus synthetic fixtures. It does not certify every "
            "Atlas row, make generated projections source authority, publish private raw "
            "state, or create a new navigation maze beside the existing route plane."
        ),
        "next_refinement_move": (
            "Keep atlas_navigation_bands under navigation_hologram_route_plane with "
            "root_binding_and_executable_grammar as the grammar sibling. Future agents "
            "should open std_agent_entry_surface, std_navigation_contract, std_kind_atlas, "
            "std_paper_module, standard_option_surface.py, kind_atlas.py, navigation "
            "context-pack tests, and the Microcosm pattern card before adding Atlas-band "
            "doctrine, public leaves, or another self-indexing entry surface."
        ),
    },
    {
        "route_id": "compression_profiles_registry_option_surface_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "navigation_projection_route_plane",
            "raw_seed_to_doctrine_metabolism",
        ],
        "target_existing_organs": [
            "navigation_hologram_route_plane",
            "root_binding_and_executable_grammar",
            "pattern_binding_contract",
            "executable_doctrine_grammar",
        ],
        "pattern_ids": [
            "compression_profiles_registry",
        ],
        "why_impressive": (
            "Compression profiles become reusable when profile ids, native bands, "
            "render-profile owner routes, sibling profile relationships, omission "
            "receipts, refresh/check commands, and projection-not-authority boundaries "
            "travel as one typed option surface instead of per-agent summary taste."
        ),
        "candidate_fixture": (
            "Synthetic registry with one contextual profile and two sibling render profiles. "
            "Positive cases require flag/card option rows, card-level band contracts, "
            "owner refresh/check/status routes, sibling profile links, validation probes, "
            "and omission receipts. Negative cases fail when a missing profile is summarized "
            "ad hoc, profile-declared native bands are treated as adapter support, generated "
            "packets are treated as authority, or commands are assigned to a Type B receiver."
        ),
        "anti_claim_floor": (
            "This route proves the profile registry, option-surface adapter, render-profile "
            "pointers, and refresh/check contracts over live and synthetic profile rows. It "
            "does not make the candidate registry a finalized standard, certify every render "
            "packet fresh, publish private raw voice, or authorize generated packets as source "
            "authority."
        ),
        "next_refinement_move": (
            "Keep compression_profiles_registry under navigation_hologram_route_plane with "
            "root_binding_and_executable_grammar as the grammar sibling. Future agents should "
            "open compression_profiles.json, profile_governed_compression.md, system_self_"
            "comprehension_root, compression profile option-surface cards, compression profile "
            "tests, raw_seed_compressed_projection.py, raw_seed_pipeline.py compressed-projection "
            "checks, and packet status sidecars before adding profile doctrine, public packet "
            "leaves, or local summary recipes."
        ),
    },
    {
        "route_id": "system_self_comprehension_render_profile_packet_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "navigation_projection_route_plane",
            "raw_seed_to_doctrine_metabolism",
        ],
        "target_existing_organs": [
            "navigation_hologram_route_plane",
            "root_binding_and_executable_grammar",
            "pattern_binding_contract",
            "executable_doctrine_grammar",
        ],
        "pattern_ids": [
            "system_self_comprehension_render_profile",
        ],
        "why_impressive": (
            "System self-comprehension packets become reusable when render-profile ids, "
            "root-contract ownership, public-safe output paths, status sidecars, "
            "last-green receipts, sibling packet profiles, refresh/check commands, "
            "forbidden-output probes, and command-as-evidence boundaries route as one "
            "owner packet instead of being rederived from prose or copied packet bodies."
        ),
        "candidate_fixture": (
            "Synthetic root self-model with one wide system packet and one compact Type B "
            "packet. Positive cases require root slug, surface family, render_profile_id, "
            "status sidecar, last-green output, sibling profile links, redaction probes, "
            "command-framing probes, projection-not-authority text, and refresh/check "
            "commands. Negative cases fail when raw private ids leak, receiver packets "
            "assign repo commands, stale generated packets are treated as source "
            "authority, or a public Microcosm leaf omits the authority boundary."
        ),
        "anti_claim_floor": (
            "This route proves the governed render-profile packet contract over live "
            "compression-profile, raw-seed projection, packet-status, and synthetic "
            "fixture surfaces. It does not certify every packet fresh, publish private "
            "raw voice, grant repo access to Type B receivers, or make generated packet "
            "markdown source authority."
        ),
        "next_refinement_move": (
            "Keep system_self_comprehension_render_profile under navigation_hologram_route_plane "
            "with root_binding_and_executable_grammar as the grammar sibling. Future agents "
            "should open system_self_comprehension_root, compression_profiles.json render "
            "profile cards, std_raw_seed_compressed_projection, raw_seed_compressed_projection.py, "
            "raw_seed_pipeline.py compressed-projection checks, packet status sidecars, "
            "last-green packet outputs, and focused compression/packet tests before adding "
            "self-description doctrine, public packet leaves, or local summary recipes."
        ),
    },
    {
        "route_id": "live_projection_salience_gate_attention_control_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "navigation_projection_route_plane",
            "raw_seed_to_doctrine_metabolism",
            "agent_entry_runtime_and_behavior_governance",
        ],
        "target_existing_organs": [
            "navigation_hologram_route_plane",
            "root_binding_and_executable_grammar",
            "proof_diagnostic_evidence_spine",
            "agent_route_observability_runtime",
            "pattern_binding_contract",
        ],
        "pattern_ids": [
            "live_projection_salience_gate",
        ],
        "why_impressive": (
            "The live projection salience gate turns cockpit, HUD, Atlas, raw-seed, "
            "Task Ledger, Prompt Shelf, provider, bridge, and agent-entry projections "
            "from tick-driven read models into attention-control surfaces: awareness "
            "can route to background metabolism, Type A, Type B, operator attention, "
            "WorkItem candidacy, bounded workspace broadcast, or suppression without "
            "treating generated projections as source authority."
        ),
        "candidate_fixture": (
            "Synthetic live-projection manifest with three candidate rows over a tiny "
            "authority corpus. One row emits because it changes a Type A or operator "
            "decision; one suppresses represented repeat pressure while preserving "
            "source refs and reason; one stays source-local until evidence allows "
            "WorkItem/provider promotion. Negative cases fail when full queues broadcast, "
            "salience alone promotes a WorkItem, provider dispatch lacks governor/"
            "budget/receipt/failure surfaces, information scent lacks when_to_stop, or "
            "actor lenses fork the row identity."
        ),
        "anti_claim_floor": (
            "This route proves salience-gated projection attention over candidate "
            "extension standards, raw-seed projection owners, and synthetic fixtures. It "
            "does not make salience source authority, create a cockpit registry, require "
            "every projection to emit the extension today, promote WorkItems, dispatch "
            "providers, publish private projection queues, or authorize generated rows "
            "as public Microcosm release evidence."
        ),
        "next_refinement_move": (
            "Keep live_projection_salience_gate under navigation_hologram_route_plane "
            "with root_binding_and_executable_grammar, proof_diagnostic_evidence_spine, "
            "and agent_route_observability_runtime as carry siblings. Future projection "
            "work should open live_control_layer_projections, std_live_projection_"
            "salience_gate, std_raw_seed_compressed_projection, raw_seed_compressed_"
            "projection.py, raw_seed_pipeline.py, create_control_layer_live_projection, "
            "Task Ledger/Prompt Shelf/provider projection owners, and focused raw-seed/"
            "option-surface tests before adding cockpit, HUD, Atlas, or live-projection "
            "doctrine."
        ),
    },
    {
        "route_id": "summary_ladders_system_facts_glance_compression_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "paper_module_authoring_runtime",
            "world_model_attention_and_authority_projection",
            "raw_seed_to_doctrine_metabolism",
        ],
        "target_existing_organs": [
            "navigation_hologram_route_plane",
            "root_binding_and_executable_grammar",
            "proof_diagnostic_evidence_spine",
            "pattern_binding_contract",
            "executable_doctrine_grammar",
        ],
        "pattern_ids": [
            "summary_ladders_compression",
            "system_facts_glance",
        ],
        "why_impressive": (
            "Summary ladders and system facts at-a-glance become reusable when "
            "cold-entry compression rows carry length bands, route tokens, proof "
            "refs, source-authority boundaries, generated sidecars, and refresh "
            "commands as one navigable contract instead of scattered README copy "
            "or volatile prose."
        ),
        "candidate_fixture": (
            "Synthetic cold-entry corpus with one public microcosm leaf ladder and "
            "one generated system-facts card. Positive cases require four summary "
            "lengths, proof refs, anti-claims, std_python or fact-route drilldowns, "
            "projection-not-authority text, owner refresh/check commands, and "
            "route-readiness membership. Negative cases fail when a summary row "
            "becomes proof, facts are hand-edited, dynamic values are treated as "
            "static doctrine, or private-root state is published."
        ),
        "anti_claim_floor": (
            "This route proves cold-entry compression projections over summary "
            "ladder fixtures, System Atlas facts, derived-fact owners, option "
            "surfaces, and synthetic negative cases. It does not certify public "
            "release, make generated rows source authority, replace leaf evidence "
            "or receipts, publish private state, or freeze volatile facts into "
            "static doctrine."
        ),
        "next_refinement_move": (
            "Keep summary_ladders_compression and system_facts_glance under "
            "navigation_hologram_route_plane with root_binding_and_executable_grammar "
            "and proof_diagnostic_evidence_spine as carry siblings. Future cold-entry "
            "compression work should open the summary_ladders specimen, std_summary_"
            "ladder analogue, derived_fact_hologram, std_derived_fact, System Atlas "
            "facts projection, agent_bootstrap_projection.py, and focused builder/"
            "option-surface checks before adding another entry table or facts card."
        ),
    },
    {
        "route_id": "concept_mechanism_curation_doctrine_gate_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "paper_module_authoring_runtime",
            "raw_seed_to_doctrine_metabolism",
            "navigation_projection_route_plane",
        ],
        "target_existing_organs": [
            "root_binding_and_executable_grammar",
            "executable_doctrine_grammar",
            "pattern_binding_contract",
            "navigation_hologram_route_plane",
            "proof_diagnostic_evidence_spine",
            "voice_to_doctrine_self_improvement_loop",
        ],
        "pattern_ids": [
            "concept_mechanism_curation",
        ],
        "why_impressive": (
            "Concept/mechanism curation turns doctrine growth pressure into governed "
            "candidate rows, option-surface cards, curation packets, concept and "
            "mechanism standards, and source-coupled report refreshes. Future agents "
            "can decide add_edges, covered_by_existing, author_new, defer, or reject "
            "without grepping doctrine folders or minting parallel concept/mechanism "
            "owners."
        ),
        "candidate_fixture": (
            "Synthetic doctrine coverage fixture with four candidates: two concepts "
            "and two mechanisms. Positive cases require candidate cards, reopened "
            "evidence anchors, nearest-existing review, one add_edges packet, one "
            "covered_by_existing packet, one defer packet, refreshed candidate report "
            "effects, and option-surface card drilldowns. Negative cases fail when "
            "candidate rows become doctrine authority, curation packets omit reopened "
            "evidence, concepts/mechanisms are hand-minted outside their standards, or "
            "the report is stale after substrate changes."
        ),
        "anti_claim_floor": (
            "This route proves concept/mechanism curation as a governed doctrine "
            "growth gate over candidate reports, curation receipts, standards, skills, "
            "option surfaces, and tests. It does not promote candidate rows into "
            "concept or mechanism law, authorize bulk doctrine minting, replace "
            "std_concept or std_mechanism, make generated reports source authority, "
            "or publish private raw-seed/operator evidence without the owning lanes."
        ),
        "next_refinement_move": (
            "Keep concept_mechanism_curation under root_binding_and_executable_grammar "
            "with navigation_hologram_route_plane, proof_diagnostic_evidence_spine, "
            "and voice_to_doctrine_self_improvement_loop as carry siblings. Future "
            "doctrine-growth work should open concept_mechanism_candidates and "
            "concept_mechanism_candidate_curations option surfaces, std_concept, "
            "std_mechanism, concept_mechanism_curation skill, doctrine_population_loop, "
            "concept_mechanism_coverage.py, build_concept_mechanism_candidates.py, "
            "and focused imagination/index tests before authoring concepts, mechanisms, "
            "or public Microcosm leaves."
        ),
    },
    {
        "route_id": "correction_survival_loop_voice_to_doctrine_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "paper_module_authoring_runtime",
            "raw_seed_to_doctrine_metabolism",
            "mission_transaction_and_scoped_commit",
        ],
        "target_existing_organs": [
            "voice_to_doctrine_self_improvement_loop",
            "mission_transaction_work_spine",
            "pattern_binding_contract",
            "navigation_hologram_route_plane",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "correction_survival_loop",
        ],
        "why_impressive": (
            "Correction survival becomes reusable when an operator correction is captured "
            "before prose, classified, tied to a non-empty route or doctrine diff, "
            "validated by an effectiveness witness, and then linked back to Task Ledger, "
            "local-to-general propagation, egress/capture tripwires, and Microcosm "
            "privacy gates instead of remaining a chat memory."
        ),
        "candidate_fixture": (
            "Synthetic correction loop fixture with four correction utterances, capture "
            "events ordered before prose, typed failure modes, non-noise route diffs "
            "that cite capture ids, future scenarios that route differently after the "
            "patch, and private-content absence checks. Negative cases fail when a "
            "correction is only logged, a route diff omits the capture id, old and new "
            "graphs choose the same action, or real operator/CAP/provider state leaks "
            "into the fixture."
        ),
        "anti_claim_floor": (
            "This route proves a synthetic correction-survival mechanism and its live "
            "routing owners. It does not prove that every private correction survived, "
            "authorize live tripwire mutation, make Task Ledger captures rank or promote "
            "work automatically, expose real operator wording, grant private-root "
            "equivalence, or strengthen hosted-public/release authority."
        ),
        "next_refinement_move": (
            "Keep correction_survival_loop under voice_to_doctrine_self_improvement_loop "
            "with mission_transaction_work_spine, proof_diagnostic_evidence_spine, "
            "pattern_binding_contract, and external_boundary_anti_corruption_runtime as "
            "carry siblings. Future correction work should open the correction-survival "
            "fixture receipt, Task Ledger capture reflex, local_to_general_propagation, "
            "egress compliance tests, extracted-pattern binding checks, and route-readiness "
            "audit before patching tripwires, standards, skills, or paper modules."
        ),
    },
    {
        "route_id": "cross_actor_notice_capture_doctrine_refinement_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "paper_module_authoring_runtime",
            "raw_seed_to_doctrine_metabolism",
            "mission_transaction_and_scoped_commit",
            "agent_runtime_observability_and_egress_membrane",
            "operator_thread_memory_and_type_b_handoff_membrane",
        ],
        "target_existing_organs": [
            "voice_to_doctrine_self_improvement_loop",
            "mission_transaction_work_spine",
            "agent_route_observability_runtime",
            "external_boundary_anti_corruption_runtime",
            "pattern_binding_contract",
            "navigation_hologram_route_plane",
            "proof_diagnostic_evidence_spine",
            "bridge_phase_continuity_runtime",
        ],
        "pattern_ids": [
            "cross_actor_notice_capture",
        ],
        "why_impressive": (
            "Cross-actor notices become reusable when operator, agent, validator, hook, "
            "and Type B contours are classified by notice class, captured without "
            "adoption claims, routed to Task Ledger, Prompt Ledger, actor-axis, "
            "concept/mechanism, paper-module, or standard owners, and then validated "
            "by Type A against live substrate before doctrine or Microcosm projection."
        ),
        "candidate_fixture": (
            "Synthetic four-notice fixture across operator, Type A agent, validator, "
            "and Type B handoff surfaces. Positive cases classify correction, "
            "observation, proposal, and objection lanes; preserve provenance hashes; "
            "route ordinary side work to Task Ledger, prompt friction to Prompt Ledger, "
            "actor-axis drift to con_016, and reusable doctrine to paper-module or "
            "standard owners; then emit one bounded doctrine patch proposal with "
            "validation refs. Negative cases fail when notices become generic TODOs, "
            "Type B claims private substrate authority, doctrine is mutated before "
            "owner verification, provenance is absent, or private transcript/provider "
            "state leaks into the fixture."
        ),
        "anti_claim_floor": (
            "This route proves actor-aware notice routing over synthetic notices and "
            "live owner surfaces. It does not prove every private notice was captured, "
            "promote Type B advice to substrate truth, create a parallel notice board, "
            "rank or promote Task Ledger captures automatically, expose private "
            "operator/provider/browser state, or authorize public Microcosm release."
        ),
        "next_refinement_move": (
            "Keep cross_actor_notice_capture under voice_to_doctrine_self_improvement_loop "
            "with mission_transaction_work_spine, agent_route_observability_runtime, "
            "bridge_phase_continuity_runtime, proof_diagnostic_evidence_spine, "
            "pattern_binding_contract, and external_boundary_anti_corruption_runtime "
            "as carry siblings. Future notice-routing work should open cross_actor_"
            "notice_capture_and_refinement_dynamics, task_ledger, prompt_shelf_"
            "uppropagation_ledger, con_016, Task/Prompt Ledger standards, operator "
            "thread memory lesson-candidate tests, egress capture-reflex tests, and "
            "extracted-pattern binding/readiness checks before changing notice lanes "
            "or projecting public Microcosm leaves."
        ),
    },
    {
        "route_id": "archaeological_voice_coverage_gate_voice_to_doctrine_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "paper_module_authoring_runtime",
            "raw_seed_to_doctrine_metabolism",
            "voice_memory_alchemy",
            "navigation_projection_route_plane",
        ],
        "target_existing_organs": [
            "voice_to_doctrine_self_improvement_loop",
            "raw_seed_alchemy_review_suborgan",
            "pattern_binding_contract",
            "navigation_hologram_route_plane",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "archaeological_voice_coverage_gate",
        ],
        "why_impressive": (
            "Archaeological voice mining becomes reusable when older obsidian/idea "
            "voice is classified before dispatch, coverage-checked against live "
            "doctrine before import, rejected at the import boundary when coverage "
            "metadata is absent, and ledgered for emit, drop_overlaps, and "
            "drop_full_coverage decisions. Future agents can use the archaeology "
            "state, skill, standard, pipeline, and tests instead of rediscovering "
            "where the retread and voice-theft boundaries live."
        ),
        "candidate_fixture": (
            "Synthetic archaeology bundle with one will_voice file, one ai_output "
            "file, one emit shard, one drop_overlaps shard, one drop_full_coverage "
            "shard, and one missing coverage_check shard. Positive cases import only "
            "emit and drop_overlaps into archaeological_shards.json while ledgering "
            "all three coverage decisions and updating corpus_index mining_state. "
            "Negative cases fail when ai_output is mined, coverage_check is empty, "
            "emit or drop_overlaps lacks new_dimension, checked_against omits live "
            "doctrine ids, or archaeological_depth is missing."
        ),
        "anti_claim_floor": (
            "This route proves the coverage-gated archaeology import boundary over "
            "synthetic/private-root-safe fixtures and live owner surfaces. It does "
            "not authorize raw obsidian/idea publication, prove every historical "
            "voice file is classified or mined, convert ai_output into Will voice, "
            "make archaeological shards doctrine law, bypass raw-seed apply lanes, "
            "or authorize public Microcosm release of private voice content."
        ),
        "next_refinement_move": (
            "Keep archaeological_voice_coverage_gate under voice_to_doctrine_"
            "self_improvement_loop with raw_seed_alchemy_review_suborgan, "
            "pattern_binding_contract, navigation_hologram_route_plane, "
            "proof_diagnostic_evidence_spine, and external_boundary_anti_corruption_"
            "runtime as carry siblings. Future voice-archaeology work should open "
            "archaeological_voice_mining, voice_archaeology, std_voice_archaeology, "
            "voice_archaeology_pipeline.py, corpus_index, archaeological_shards, "
            "coverage_ledger, extracted-pattern binding/readiness checks, and the "
            "focused voice-archaeology import tests before mining, importing, or "
            "projecting archaeological voice into Microcosm."
        ),
    },
    {
        "route_id": "voice_archaeology_coverage_aware_third_substrate_voice_to_doctrine_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "paper_module_authoring_runtime",
            "raw_seed_to_doctrine_metabolism",
            "voice_memory_alchemy",
            "navigation_projection_route_plane",
        ],
        "target_existing_organs": [
            "voice_to_doctrine_self_improvement_loop",
            "raw_seed_alchemy_review_suborgan",
            "pattern_binding_contract",
            "navigation_hologram_route_plane",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "voice_archaeology_coverage_aware_third_substrate",
        ],
        "why_impressive": (
            "Voice archaeology is reusable as the third substrate only when the "
            "corpus index, provenance and depth classifier, coverage-aware mining "
            "bundle, embedding search surface, archaeological shard ledger, "
            "coverage ledger, import validator, kernel archaeology packet, and "
            "paper/standard/skill owners travel as one route. Future agents should "
            "open the archaeology substrate directly instead of rediscovering it "
            "from obsidian/idea files, raw-seed metaphors, or scattered pipeline "
            "commands."
        ),
        "candidate_fixture": (
            "Synthetic archaeology corpus with will_voice, mixed, paper_draft, "
            "ai_output, and empty files across shallow, medium, deep, and "
            "foundational archaeological_depth bands. Positive cases require "
            "browse filtering by priority/provenance/depth, coverage embedding "
            "before mining, nearest-doctrine coverage context, checked_against "
            "refs, emit/drop_overlaps/drop_full_coverage ledger decisions, "
            "archaeological_shards import only for allowed decisions, archaeology_"
            "shards embedding search, and option-surface route readiness. Negative "
            "cases fail when ai_output is mined as Will voice, raw obsidian/idea "
            "content is projected, coverage_check is missing or stale, a shard "
            "bypasses the raw-seed/voice apply boundary, or route rows are selected "
            "without the organ bundle."
        ),
        "anti_claim_floor": (
            "This route proves the third-substrate routing contract over live owner "
            "surfaces and synthetic/private-root-safe fixtures. It does not publish "
            "raw obsidian/idea content, prove every historical file is classified "
            "or mined, turn ai_output into operator voice, make archaeological "
            "shards doctrine law, create a new apply lane, bypass coverage gates, "
            "or authorize public Microcosm release of private voice material."
        ),
        "next_refinement_move": (
            "Keep voice_archaeology_coverage_aware_third_substrate under voice_to_"
            "doctrine_self_improvement_loop with raw_seed_alchemy_review_suborgan, "
            "pattern_binding_contract, navigation_hologram_route_plane, proof_"
            "diagnostic_evidence_spine, and external_boundary_anti_corruption_"
            "runtime as carry siblings. Future third-substrate work should open "
            "voice_archaeology, voice_archaeology_build_spec, std_voice_archaeology, "
            "archaeological_voice_mining, voice_archaeology_pipeline.py, "
            "embedding_substrate.py, embedding_sources.py, kernel archaeology flags, "
            "corpus_index, archaeological_shards, coverage_ledger, extracted-pattern "
            "binding/readiness checks, and voice-archaeology tests before mining, "
            "importing, routing, or projecting archaeological voice."
        ),
    },
    {
        "route_id": "raw_seed_atomization_to_shards_voice_to_doctrine_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "paper_module_authoring_runtime",
            "raw_seed_to_doctrine_metabolism",
            "voice_memory_alchemy",
            "navigation_projection_route_plane",
        ],
        "target_existing_organs": [
            "voice_to_doctrine_self_improvement_loop",
            "raw_seed_alchemy_review_suborgan",
            "pattern_binding_contract",
            "navigation_hologram_route_plane",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "raw_seed_atomization_to_shards",
        ],
        "why_impressive": (
            "Raw-seed atomization becomes reusable when paragraph shards, atomized "
            "extracted shards, the atomization ledger, distillation bridge import, "
            "coverage/browser-index refreshes, route-review payloads, raw-seed "
            "standards, and synthetic fixture validators travel as one route. "
            "Future agents can open the atomization owner chain directly instead "
            "of rediscovering it from raw_seed_atomization.md, distillation "
            "rubrics, extracted_shards state, and pipeline tests."
        ),
        "candidate_fixture": (
            "Synthetic family fixture with two raw_seed_shards paragraphs, one "
            "Opus distillation import, one local atomization pass, one retryable "
            "low-signal paragraph, and one route-review projection. Positive cases "
            "assert stable atom_* ids, parent paragraph provenance, ordinal order, "
            "sticky atomization_source, single extracted_shards backlog storage, "
            "append-only atomization ledger states, coverage/browser_index refresh, "
            "and route-readiness through the voice_to_doctrine_self_improvement_"
            "loop organ bundle. Negative cases fail when raw_seed.md is edited, "
            "doctrine is mutated by atomization, low-signal text becomes proposed_"
            "new routing, Opus-seeded shards are overwritten by cheap reruns, or "
            "private operator voice is projected."
        ),
        "anti_claim_floor": (
            "This route proves the raw-seed atomization routing contract over live "
            "owner surfaces and synthetic/private-root-safe fixtures. It does not "
            "publish raw operator voice, replace parent paragraphs as authority, "
            "mutate doctrine, prove every paragraph has been atomized, create a "
            "second extracted-shard backlog, bypass raw-seed apply lanes, or "
            "authorize public Microcosm release of private voice material."
        ),
        "next_refinement_move": (
            "Keep raw_seed_atomization_to_shards under voice_to_doctrine_self_"
            "improvement_loop with raw_seed_alchemy_review_suborgan, pattern_"
            "binding_contract, navigation_hologram_route_plane, proof_diagnostic_"
            "evidence_spine, and external_boundary_anti_corruption_runtime as "
            "carry siblings. Future raw-seed atomization work should open raw_"
            "seed_atomization, raw_seed_substrate, raw_seed_metabolism, raw_seed_"
            "distillation lanes, raw-seed standards, raw_seed_atomization.py, "
            "raw_seed_distillation.py, raw_seed_registry.py, raw_seed_pipeline.py, "
            "family raw_seed_shards/extracted_shards/atomization_ledger/coverage "
            "state, extracted-pattern binding/readiness checks, and focused raw-"
            "seed atomization tests before atomizing, importing, routing, or "
            "projecting shards."
        ),
    },
    {
        "route_id": "raw_seed_maintenance_self_pruning_campaign_voice_to_doctrine_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "paper_module_authoring_runtime",
            "raw_seed_to_doctrine_metabolism",
            "voice_memory_alchemy",
            "external_reference_adoption_membranes",
            "navigation_projection_route_plane",
        ],
        "target_existing_organs": [
            "voice_to_doctrine_self_improvement_loop",
            "raw_seed_alchemy_review_suborgan",
            "pattern_binding_contract",
            "navigation_hologram_route_plane",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "raw_seed_maintenance_deterministic_self_pruning_campaign",
        ],
        "why_impressive": (
            "Raw-seed maintenance becomes reusable only when the deterministic "
            "finding dialect, duplicate-collapse signatures, bounded binning, "
            "bridge maintenance mission pack, preview-first campaign driver, "
            "controller-gated apply replay, launchable operations, run ledger, "
            "documentation-refresh gate, and generated binding/readiness checks "
            "travel as one route. Future agents should open this self-pruning "
            "campaign before trying to turn recurring runtime evidence into "
            "doctrine edits or Microcosm projection claims."
        ),
        "candidate_fixture": (
            "Synthetic maintenance campaign fixture with durable runtime evidence "
            "for parser_import, reaction_barrier, worker_transport, and "
            "throughput_policy incidents. Positive cases assert stable finding_id "
            "and signature collapse, the 4-kind / 7-category / 5-mutation-class "
            "dialect, bins capped at eight findings and five target paths, "
            "required_refresh_paths on every bin, bridge mission packets carrying "
            "finding ids and exact target paths, preview-only apply compilation, "
            "and controller-owned apply-session replay. Negative cases fail when "
            "chat memory or wall-clock state affects findings, a bin mixes "
            "mutation classes, bridge authoring mutates doctrine directly, "
            "documentation_refresh_required_paths are omitted, run artifact refs "
            "are treated as public proof, or private raw-seed/runtime evidence is "
            "projected into Microcosm."
        ),
        "anti_claim_floor": (
            "This route proves the raw-seed maintenance self-pruning campaign "
            "owner chain over live code, standards, mission pack, run ledger, "
            "launchable operations, and synthetic/private-root-safe fixtures. It "
            "does not prove the campaign is currently scheduled, does not add a "
            "reactions-engine auto-fire, does not live-apply doctrine changes, "
            "does not publish raw seed, runtime logs, provider payload bodies, or "
            "operator-private evidence, does not certify that all recurring "
            "findings were repaired, and does not authorize public Microcosm "
            "release of private maintenance artifacts."
        ),
        "next_refinement_move": (
            "Keep raw_seed_maintenance_deterministic_self_pruning_campaign under "
            "voice_to_doctrine_self_improvement_loop with raw_seed_alchemy_review_"
            "suborgan, pattern_binding_contract, navigation_hologram_route_plane, "
            "proof_diagnostic_evidence_spine, and external_boundary_anti_"
            "corruption_runtime as carry siblings. Future maintenance, hygiene, "
            "or self-pruning work should open raw_seed_maintenance_campaign_"
            "runtime, raw_seed_metabolism, doctrine_apply_lanes, reactions_engine, "
            "bridge_runtime, bridge_runtime_control_plane, std_runtime_maintenance_"
            "finding, std_apply, raw_seed_maintenance_findings.py, raw_seed_"
            "maintenance_campaign.py, raw_seed_maintenance_apply_campaign.py, "
            "launchable operation rows, maintenance campaign tests, extracted-"
            "pattern binding/readiness checks, and the focused maintenance "
            "binding test before mining, authoring, applying, routing, or "
            "projecting campaign rows."
        ),
    },
    {
        "route_id": "raw_seed_type_discovery_campaign_voice_to_doctrine_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "paper_module_authoring_runtime",
            "raw_seed_to_doctrine_metabolism",
            "voice_memory_alchemy",
            "navigation_projection_route_plane",
        ],
        "target_existing_organs": [
            "voice_to_doctrine_self_improvement_loop",
            "raw_seed_alchemy_review_suborgan",
            "pattern_binding_contract",
            "navigation_hologram_route_plane",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "raw_seed_type_discovery_campaign",
        ],
        "why_impressive": (
            "Raw-seed type discovery becomes reusable only when the latest-N "
            "selector, per-paragraph type classifier, type-prototype ledger, "
            "Bridge cluster synthesis boundary, NIM guided_json fallback, schema "
            "validator, experiment ledger, and golden-set replay harness travel "
            "as one route. Future agents should open the campaign owner chain and "
            "its explicit blockers instead of rediscovering type pressure from "
            "raw-seed paragraphs, atomization code, provider probes, and bridge "
            "dispatch notes."
        ),
        "candidate_fixture": (
            "Synthetic 10-paragraph raw-seed fixture covering axiom_candidate, "
            "principle_refinement, annex_assimilation_move, routing_obligation, "
            "approval_plane_governance, and substrate_projection_compression. "
            "Positive cases assert latest-N-backwards selection, multi-label "
            "primary/secondary types, move_vector propagation targets, "
            "coverage_check checked_against refs, guided-json schema validation, "
            "Bridge cluster synthesis quarantine, experiment-ledger recording, "
            "and route-readiness through the voice_to_doctrine_self_improvement_"
            "loop organ bundle. Negative cases fail when raw_seed.md is edited, "
            "unclassifiable paragraphs are forced into existing types, emergent "
            "type candidates mutate doctrine without apply-lane ratification, "
            "provider payload bodies are projected, or classifier rows are "
            "selected as standalone Microcosm leaves."
        ),
        "anti_claim_floor": (
            "This route proves the routed owner chain and blocker map for the "
            "raw-seed type-discovery campaign. It does not prove the campaign is "
            "fully runnable, does not ship the missing latest-N selector, mission "
            "template, golden set, type-prototype ledger, or production run, does "
            "not publish raw operator voice or provider payload bodies, does not "
            "promote emergent types into doctrine law, does not bypass raw-seed "
            "apply lanes, and does not authorize public Microcosm release of "
            "private voice material."
        ),
        "next_refinement_move": (
            "Keep raw_seed_type_discovery_campaign under voice_to_doctrine_self_"
            "improvement_loop with raw_seed_alchemy_review_suborgan, pattern_"
            "binding_contract, navigation_hologram_route_plane, proof_diagnostic_"
            "evidence_spine, and external_boundary_anti_corruption_runtime as "
            "carry siblings. Future type-discovery work should open raw_seed_"
            "type_discovery_campaign, raw_seed_atomization, raw_seed_substrate, "
            "raw_seed_metabolism, claude_subagent_delegation, bridge_runtime, "
            "doctrine_apply_lanes, raw_seed_atomization.py, nvidia_nim.py, "
            "bridge.py, meta_mission_workspace.py, run_observe_plan.py, voice_"
            "archaeology_pipeline.py, experiment_ledger.py, extracted-pattern "
            "binding/readiness checks, and the focused type-discovery binding "
            "test before classifying, launching, routing, or projecting campaign "
            "rows."
        ),
    },
    {
        "route_id": "raw_seed_source_index_packet_scope_membrane_voice_to_doctrine_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "paper_module_authoring_runtime",
            "raw_seed_to_doctrine_metabolism",
            "voice_memory_alchemy",
            "external_reference_adoption_membranes",
            "navigation_projection_route_plane",
        ],
        "target_existing_organs": [
            "voice_to_doctrine_self_improvement_loop",
            "raw_seed_alchemy_review_suborgan",
            "pattern_binding_contract",
            "navigation_hologram_route_plane",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "raw_seed_source_index_packet_scope_membrane",
        ],
        "why_impressive": (
            "Raw-seed source indexing becomes reusable only when the bridge packet "
            "option surface, explicit visibility boundary, emit_shards_for and "
            "context_only authority sets, compact bridge response standard, "
            "rubric skills, receive partition, quarantine reasons, bridge receipt, "
            "and generated binding/readiness checks travel as one route. Future "
            "agents should open this membrane before asking whether provider "
            "output can index raw-seed paragraphs or mutate doctrine."
        ),
        "candidate_fixture": (
            "Synthetic packet with two focus paragraphs, one context-only neighbor, "
            "dynamic_fact_rows, drilldown refs, and an omission receipt. Positive "
            "cases assert bridge packets expose only packet-local context, allow "
            "shards only for emit_shards_for parents, preserve source-indexing "
            "legacy keys, carry traceable voice anchors, write bridge receipts, "
            "and import only rows accepted by the receive partition. Negative "
            "cases fail when a context_only paragraph emits a shard, a parent "
            "outside the packet is accepted, provider output claims global "
            "novelty or coverage truth, doctrine/routing mutation is embedded in "
            "the bridge response, trace anchors are missing, or raw operator "
            "voice/provider payload bodies are projected."
        ),
        "anti_claim_floor": (
            "This route proves the raw-seed source-index packet membrane over live "
            "owner surfaces and synthetic/private-root-safe fixtures. It does not "
            "publish raw seed, export provider payload bodies, make bridge output "
            "doctrine authority, certify global coverage or novelty, select "
            "context-only rows as distillation targets, bypass receive quarantine, "
            "or authorize public Microcosm release of private voice material."
        ),
        "next_refinement_move": (
            "Keep raw_seed_source_index_packet_scope_membrane under voice_to_"
            "doctrine_self_improvement_loop with raw_seed_alchemy_review_suborgan, "
            "pattern_binding_contract, navigation_hologram_route_plane, proof_"
            "diagnostic_evidence_spine, and external_boundary_anti_corruption_"
            "runtime as carry siblings. Future source-index or bridge-distillation "
            "work should open raw_seed_distillation_lanes, raw_seed_substrate, "
            "raw_seed_metabolism, bridge_runtime, claude_subagent_delegation, "
            "std_extracted_shards_bridge_compact, distillation_rubric_bridge, "
            "distillation_voice_patterns_bridge, raw_seed_distillation.py, "
            "raw_seed_pipeline.py, extracted-pattern binding/readiness checks, "
            "and the focused source-index packet membrane binding test before "
            "dispatching, importing, routing, or projecting bridge rows."
        ),
    },
    {
        "route_id": "doctrine_compiler_ir_executable_lattice_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "paper_module_authoring_runtime",
            "raw_seed_to_doctrine_metabolism",
            "world_model_attention_and_authority_projection",
        ],
        "target_existing_organs": [
            "root_binding_and_executable_grammar",
            "executable_doctrine_grammar",
            "pattern_binding_contract",
            "navigation_hologram_route_plane",
            "proof_diagnostic_evidence_spine",
        ],
        "pattern_ids": [
            "doctrine_compiler_ir",
        ],
        "why_impressive": (
            "Doctrine compiler IR turns principles, concepts, mechanisms, section "
            "units, overlays, and compatibility tombstones into generated graph, "
            "IR, surface, index, and routing projections with an explicit owner "
            "tool and freshness gate, so doctrine is a compilable substrate rather "
            "than a prose lattice agents must rediscover."
        ),
        "candidate_fixture": (
            "Synthetic doctrine corpus with three principles, one concept, one "
            "mechanism, one section-unit seed, one approved overlay row, and one "
            "compatibility tombstone. Positive cases require graph, compiler IR, "
            "section units, surface, index, routing, projection_updates, "
            "tombstone_candidates, source-authority refs, and the owner check. "
            "Negative cases fail when generated doctrine projections are hand-edited, "
            "stale drift is ignored, runtime state is treated as source authority, "
            "or candidate axioms/overlays are promoted without the owner lane."
        ),
        "anti_claim_floor": (
            "This route proves doctrine graph and compiler-IR routing over live owner "
            "surfaces and synthetic doctrine fixtures. It does not make generated "
            "doctrine projections source authority, promote candidate axioms or "
            "overlay rows, certify public release of private doctrine neighborhoods, "
            "replace authored principle/concept/mechanism sources, or bypass the "
            "doctrine graph projection check/repair lane."
        ),
        "next_refinement_move": (
            "Keep doctrine_compiler_ir under root_binding_and_executable_grammar "
            "with executable_doctrine_grammar, navigation_hologram_route_plane, and "
            "proof_diagnostic_evidence_spine as carry siblings. Future doctrine "
            "compiler work should open system/lib/doctrine_graph.py, "
            "build_doctrine_graph_projection.py, std_doctrine_compiler_ir, "
            "std_doctrine_graph, doctrine_registry_runtime, doctrine_apply_lanes, "
            "generated_projection_registry, config-authority rows, and focused "
            "doctrine-graph/projection tests before editing graph, IR, routing, or "
            "registry doctrine."
        ),
    },
    {
        "route_id": "compound_microcosm_cell_decision_projection_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "navigation_projection_route_plane",
            "generated_projection_source_coupling",
            "pattern_deliverables_registry",
        ],
        "target_existing_organs": [
            "navigation_hologram_route_plane",
            "root_binding_and_executable_grammar",
            "pattern_binding_contract",
            "executable_doctrine_grammar",
        ],
        "pattern_ids": [
            "compound_microcosm_cell_decision_projection",
        ],
        "why_impressive": (
            "Compound microcosm cells turn generated candidate rows into governed "
            "composition decisions: each reusable public-safe cell carries an explicit "
            "decision, public/private boundary, included pattern set, composition "
            "receipt, proof-card route, graph edge, next-drilldown commands, and "
            "anti-claim floor before any public Microcosm leaf can inherit it."
        ),
        "candidate_fixture": (
            "Synthetic constellation with one use_existing or improve_existing public-safe "
            "cell, one private_only cell, and one blocked_until_receipt cell. Positive "
            "cases require decision, microcosm_role, public_private_boundary, included "
            "patterns, composition receipt refs, proof-card refs, graph refs, next "
            "drilldowns, and fail-closed release text. Negative cases fail when a cell "
            "lacks a decision or boundary, private/blocked cells emit public release "
            "permission, generated rows become source authority, or per-pattern leaf "
            "rows bypass the compound-cell receipt."
        ),
        "anti_claim_floor": (
            "This route proves decision-bearing compound-cell routing over live "
            "constellation, System Atlas, proof-card, graph, receipt, and synthetic "
            "fixture surfaces. It does not authorize public release, prove private-root "
            "equivalence, make generated constellation or Atlas rows source authority, "
            "or allow private/provider/feed bodies to be projected without redaction or "
            "synthetic fixtures."
        ),
        "next_refinement_move": (
            "Keep compound_microcosm_cell_decision_projection under "
            "navigation_hologram_route_plane with root_binding_and_executable_grammar as "
            "the grammar sibling. Future agents should open the constellation builder "
            "and state, System Atlas compound-cell cards, composition graph, proof-card "
            "builder, composition receipts, std_system_atlas, and focused "
            "constellation/proof-card tests before adding public Microcosm leaves from "
            "generated cell rows."
        ),
    },
    {
        "route_id": "launchable_operation_contract_root_contract",
        "priority_rank": 0,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "runtime_launch_allowlist",
        ],
        "target_existing_organs": [
            "root_binding_and_executable_grammar",
            "pattern_binding_contract",
            "executable_doctrine_grammar",
            "mission_transaction_work_spine",
        ],
        "pattern_ids": [
            "launchable_operation_contract",
        ],
        "why_impressive": (
            "Launchable operation contracts turn runnable CLI, builder, validator, and "
            "probe surfaces into typed preflight rows: inputs, outputs, side effects, "
            "idempotency, ceremony tier, owner, result landing, residual routing, and "
            "refusal conditions travel with an operation before automated or manual "
            "launchers run it."
        ),
        "candidate_fixture": (
            "Synthetic three-operation allowlist with one idempotent checker, one "
            "mutating builder requiring a landing contract and residual route, and one "
            "rejected unsafe launcher. Positive cases validate catalog identity, "
            "dispatch mode, owner surface, result landing, automatic-source inference, "
            "and idempotent rerun posture; negative cases fail when ad-hoc commands, "
            "missing landing contracts, or coverage-complete-but-unhealthy outcomes are "
            "treated as safe dispatch."
        ),
        "anti_claim_floor": (
            "This route proves launchable-operation contract routing and preflight shape "
            "for the fixture and live launchable-operation/reaction substrate. It does "
            "not authorize arbitrary command execution, certify every repo command has "
            "a contract, make draft standards final law, treat operation coverage as "
            "runtime health, or bypass Work Ledger, Task Ledger, reaction, dispatch, or "
            "generated-owner gates."
        ),
        "next_refinement_move": (
            "Keep launchable_operation_contract under root_binding_and_executable_grammar "
            "with mission_transaction_work_spine as the execution-governance sibling. "
            "Future agents should open std_launchable_operation_contract, "
            "launchable_operations.py, launchable_operation_contracts.py, reactions.yaml, "
            "reactions_engine, contract overlays, launchable-operation tests, and "
            "extracted-pattern readiness checks before adding launcher doctrine or "
            "Microcosm leaves."
        ),
    },
    {
        "route_id": "formal_prover_context_strategy_gate",
        "priority_rank": 1,
        "source_cluster_ids": ["formal_prover_context_library_prior_and_strategy_gate"],
        "target_existing_organs": [
            "proof_diagnostic_evidence_spine",
            "formal_prover_lab_evaluation_suborgan",
        ],
        "pattern_ids": [
            "formal_math_readiness_gate_public_boundary",
            "corpus_readiness_mathlib_absence_gate",
            "lean_std_toolchain_premise_index",
            "provider_context_recipe_budget_policy",
            "mathematical_strategy_atlas_hypothesis_scorer",
            "tactic_portfolio_availability_probe",
            "target_shape_tactic_routing_gate",
            "prover_premise_retrieval_term_scoring",
            "ring2_premise_retrieval_precision_recall_harness",
            "support_affordance_mathlib_declaration_match_terms",
        ],
        "why_impressive": (
            "A public-safe formal-math control stack where corpus readiness, allowed "
            "premise priors, provider-visible context, strategy hypotheses, tactic "
            "availability, and retrieval metrics are all explicit gates before any proof "
            "success claim."
        ),
        "candidate_fixture": (
            "Synthetic Lean/Std mini-corpus with one unavailable Mathlib dependency, a "
            "closed premise index, context budget receipts, tactic availability probe, "
            "strategy-classification reducer, and retrieval precision/recall buckets."
        ),
        "anti_claim_floor": (
            "This route demonstrates the proof-lab control plane and evidence spine; it "
            "must not claim general theorem-proving capability or expose oracle material."
        ),
        "next_refinement_move": (
            "Project as a combined proof-diagnostic organ, then add one validator lane "
            "that checks all gate receipts are present before any solved/unsolved metric "
            "is shown."
        ),
    },
    {
        "route_id": "formal_prover_payload_membrane",
        "priority_rank": 1,
        "source_cluster_ids": [
            "formal_prover_context_library_prior_and_strategy_gate",
            "formal_math_policy_integrity_and_search_foundry",
        ],
        "target_existing_organs": [
            "proof_diagnostic_evidence_spine",
            "formal_prover_lab_evaluation_suborgan",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "formal_prover_payload_policy_boundary",
        ],
        "why_impressive": (
            "A provider-payload membrane for formal-prover work: bounded context packs, "
            "strategy advisories, transform jobs, row patches, provider receipts, and "
            "reducer reports can improve the proof lab while provider text remains below "
            "Lean/proof authority and public projection boundaries."
        ),
        "candidate_fixture": (
            "Synthetic transform job plus provider receipt set with one clean context "
            "hypothesis, one strategy advisory, one forbidden Lean proof-body advisory, "
            "and one oracle-material leak; the reducer accepts only advisory metadata, "
            "keeps provider_results_counted=false, and requires a separate proof receipt "
            "before any green claim."
        ),
        "anti_claim_floor": (
            "This route proves payload-boundary routing for the fixture and live prover "
            "harness/reducer surfaces; it does not call providers, certify theorem "
            "correctness, publish proof bodies, count provider output as success, or "
            "authorize public release without proof receipts."
        ),
        "next_refinement_move": (
            "Keep this route under proof_diagnostic_evidence_spine. The next adjacent "
            "binding is formal_math_proofline_spine_body_safe_lineage, which must prove "
            "body-safe lineage without copying proof bodies, prompts, provider outputs, "
            "or oracle material."
        ),
    },
    {
        "route_id": "formal_math_proofline_body_safe_lineage",
        "priority_rank": 2,
        "source_cluster_ids": [
            "formal_prover_context_library_prior_and_strategy_gate",
            "formal_math_policy_integrity_and_search_foundry",
        ],
        "target_existing_organs": [
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "formal_math_proofline_spine_body_safe_lineage",
        ],
        "why_impressive": (
            "A body-safe formal-math proofline spine turns private Lab-to-Oracle "
            "receipts into public-safe lineage: state, edges, claim boundaries, "
            "repair readiness, and proof authority are derivable without copying "
            "answers, prompts, provider outputs, Lean proof bodies, or oracle material."
        ),
        "candidate_fixture": (
            "Synthetic proofline and repair-lane packets over one failed toy Lean specimen: "
            "positive cases require claim_boundary, proof_level_rejected state, "
            "proof_synthesis_or_repair_quality bottleneck, generated projection owner "
            "coverage, forbidden-body-key empty sets, and a separate proof-repair receipt; "
            "negative cases inject answer, ground_truth_proof, prompt, provider_output, "
            "and lean_proof_body fields and must fail before projection."
        ),
        "anti_claim_floor": (
            "This route proves body-safe lineage and repair-lane routing for the fixture "
            "and live builder receipts; it does not publish benchmark bodies, claim theorem "
            "success, expose proof or prompt payloads, count provider output as proof, "
            "or authorize public release of private formal-math runs."
        ),
        "next_refinement_move": (
            "Keep this route under proof_diagnostic_evidence_spine with the provider "
            "payload membrane and Lean proof witness as siblings. Lean rejection "
            "classification is now bound in the same proof diagnostic spine, so the "
            "next adjacent repair surface is formal_proof_repair_one_row_reducer_gate: "
            "the one-row handoff from typed rejection evidence to a governed repair "
            "attempt and reducer receipt."
        ),
    },
    {
        "route_id": "lean_verifier_failure_classification_membrane",
        "priority_rank": 3,
        "source_cluster_ids": [
            "formal_prover_context_library_prior_and_strategy_gate",
            "formal_math_policy_integrity_and_search_foundry",
        ],
        "target_existing_organs": [
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "lean_verifier_feedback_failure_classification",
        ],
        "why_impressive": (
            "Lean verifier outcomes become typed routing evidence instead of a flat retry "
            "signal: provider contract failures, truth-side leakage, premise-budget "
            "violations, undeclared library priors, premise-retrieval misses, synthesis "
            "failures, and clean passes each land in distinct review outcomes before "
            "repair or escalation."
        ),
        "candidate_fixture": (
            "Synthetic provider-receipt reductions covering the seven reducer classes "
            "(NONE, PROVIDER_CONTRACT_FAIL, SOLUTION_LEAKAGE, "
            "PREMISE_BUDGET_VIOLATION, UNDECLARED_LIBRARY_PRIOR, "
            "PREMISE_RETRIEVAL_MISS, PROOF_SYNTHESIS_FAIL) and the four review "
            "outcomes (accept_as_advisory_signal, reject, retry, bridge_escalate). "
            "Positive cases require Lean PASS plus CLEAN axioms for NONE; negative "
            "cases prove leakage is rejected before repair and provider output never "
            "becomes source authority."
        ),
        "anti_claim_floor": (
            "This route proves classification and review routing for reducer fixtures "
            "and live reducer code; it does not call providers, certify theorem "
            "correctness, publish proof bodies, treat provider text as proof success, "
            "or authorize public benchmark claims."
        ),
        "next_refinement_move": (
            "Keep this route under proof_diagnostic_evidence_spine between the "
            "body-safe proofline route and the formal_proof_repair_one_row_reducer_gate. "
            "Future agents should open reduce_prover_provider_receipts.py, reducer "
            "tests, provider payload membrane, proofline lineage route, and this "
            "option-surface card before routing proof repair or provider escalation."
        ),
    },
    {
        "route_id": "formal_proof_repair_one_row_gate_membrane",
        "priority_rank": 4,
        "source_cluster_ids": [
            "formal_prover_context_library_prior_and_strategy_gate",
            "formal_math_policy_integrity_and_search_foundry",
        ],
        "target_existing_organs": [
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "formal_proof_repair_one_row_reducer_gate",
        ],
        "why_impressive": (
            "A one-row proof-repair gate turns a typed Lean failure plus body-safe "
            "proofline refs into exactly one governed provider repair attempt: provider "
            "text remains advisory, repair packets carry no proof/prompt/oracle bodies, "
            "and only Lean/Lake reducer receipts can promote the result."
        ),
        "candidate_fixture": (
            "Synthetic failed Lean specimen with proof_repair_input_packet, lane receipt, "
            "support-affordance finder refs, strict JSON canary/model inventory receipts, "
            "one transform job, evaluator/reducer terminal status, and benchmark claims "
            "disabled. Negative cases inject forbidden inline proof, prompt, provider, "
            "oracle, or solution keys and must fail before dispatch or projection."
        ),
        "anti_claim_floor": (
            "This route proves the one-row repair gate contract and attempt/evaluator "
            "boundaries for fixtures and live owner code; it does not call providers "
            "during binding validation, certify theorem correctness, expose proof bodies "
            "or oracle material, count provider text as proof success, authorize repeated "
            "blind retries, or authorize public benchmark claims."
        ),
        "next_refinement_move": (
            "Keep this route under proof_diagnostic_evidence_spine after proofline "
            "lineage and Lean failure classification. Future agents should open the "
            "proof repair lane builder, repair-attempt runner, support-affordance "
            "receipts, and reducer/evaluator receipts before attempting provider repair, "
            "retry, escalation, or public projection."
        ),
    },
    {
        "route_id": "formal_policy_integrity_search_foundry",
        "priority_rank": 5,
        "source_cluster_ids": ["formal_math_policy_integrity_and_search_foundry"],
        "target_existing_organs": [
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "blind_policy_problem_id_ablation_gate",
            "adversarial_identifier_rename_evolver",
            "oracle_sidecar_forward_firewall",
            "goal_feature_action_value_posterior_table",
            "canonical_goal_state_hash_loop_pruning",
            "provider_receipt_truth_side_leakage_detector",
            "induction_scheduler_visible_head_gate",
        ],
        "why_impressive": (
            "A research-engine integrity layer: proof-search learning is allowed only "
            "after identifier ablation, oracle/forward firewalls, loop-pruning receipts, "
            "typed failure evidence, and posterior tables preserve the difference between "
            "policy improvement and leakage."
        ),
        "candidate_fixture": (
            "Toy five-problem proof-state fixture with renamed identifiers, a leaking "
            "policy negative case, forward/oracle packet split, duplicate-goal hash loop, "
            "and action-value posterior table generated only from accepted transitions."
        ),
        "anti_claim_floor": (
            "Passing these checks proves integrity of the tested policy loop, not benchmark "
            "performance or absence of every possible memorization channel."
        ),
        "next_refinement_move": (
            "Fold this under the proof diagnostic organ as the no-leak/no-memorization "
            "gate that must run before policy-learning rows are credited."
        ),
    },
    {
        "route_id": "formal_benchmark_leakage_firewall_manifest_contract",
        "priority_rank": 6,
        "source_cluster_ids": [
            "formal_math_policy_integrity_and_search_foundry",
            "formal_prover_context_library_prior_and_strategy_gate",
            "formal_math_proof_organ",
        ],
        "target_existing_organs": [
            "formal_prover_lab_evaluation_suborgan",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "benchmark_split_leakage_firewall_manifest_strip",
        ],
        "why_impressive": (
            "Formal benchmark evidence becomes reusable only if every forward-visible "
            "manifest path strips proof bodies, oracle-only premise ids, and expected "
            "strategy ids before a solver or provider sees the row. This route binds the "
            "source manifest, statement-only hammer bandit, graph benchmark context-pack "
            "audit, zero-leak validation, and test-split-forbidden policy as one "
            "benchmark-integrity contract instead of a scattered implementation detail."
        ),
        "candidate_fixture": (
            "Toy three-problem benchmark manifest with train/dev/test splits, candidate/"
            "ideal/repair bodies present only in the private source objects, forward-safe "
            "rows containing proof_body_withheld_until_oracle=True, statement-only rows "
            "listing forbidden_forward_material, and negative cases that inject "
            "candidate_body, ideal_body, repair_body, oracle_needed_premise_ids, "
            "expected_strategy_ids, or test-split tuning into forward-visible output."
        ),
        "anti_claim_floor": (
            "This route proves manifest serialization and validation boundaries for the "
            "benchmark fixture and live owner code. It does not claim theorem-solving "
            "performance, certify external benchmark correctness, expose proof bodies, "
            "treat oracle comparator success as forward success, or allow tuning on held-out "
            "test failures."
        ),
        "next_refinement_move": (
            "Keep benchmark_split_leakage_firewall_manifest_strip folded into "
            "formal_prover_lab_evaluation_suborgan with proof-diagnostic and "
            "external-boundary siblings. Future formal benchmark imports should open the "
            "manifest serializers, statement-only hammer bandit validator, graph benchmark "
            "context-pack leakage audit, route-readiness sidecars, and option-surface card "
            "before claiming pass-rate evidence, oracle comparator evidence, or public "
            "Microcosm benchmark readiness."
        ),
    },
    {
        "route_id": "formal_continuous_loop_oracle_comparator_contract",
        "priority_rank": 7,
        "source_cluster_ids": [
            "formal_math_policy_integrity_and_search_foundry",
            "formal_prover_context_library_prior_and_strategy_gate",
            "formal_math_proof_organ",
        ],
        "target_existing_organs": [
            "formal_prover_lab_evaluation_suborgan",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "continuous_loop_three_lane_parallel_oracle_comparator",
        ],
        "why_impressive": (
            "The continuous Lab/Oracle/Evolve runner only becomes reusable when its "
            "three lanes stay comparable over the same problem batch: strategy_control "
            "as baseline, skill_foundry_overlay as the forward Lab lane, and "
            "oracle_repair_graph_v0 as the comparator lane. This route binds the "
            "problem-batch manifest, node context contracts, oracle result index, "
            "foundry learning filter, provider trickle queue, and run-summary invariants "
            "so oracle repair cannot inflate forward success or mix provider throughput "
            "failures into math evidence."
        ),
        "candidate_fixture": (
            "Toy five-problem continuous-loop run over one fixed problem_batch_manifest. "
            "The strategy_control lane passes two problems, skill_foundry_overlay passes "
            "three, and oracle_repair_graph_v0 passes four. Validation asserts "
            "forward_success_lane=local_foundry, oracle_repair_counts_as_forward_success=False, "
            "oracle_result_index rows for all three lanes, foundry_learning_index rows only "
            "from the local_foundry lane, no oracle proof body in forward contexts, "
            "direct_provider_dispatch_in_continuous_loop=False, rate_limit_is_math_failure=False, "
            "open_problem_success_claimed=False, and truth_side_leakage_count==0."
        ),
        "anti_claim_floor": (
            "This route proves lane separation, comparator accounting, provider-throughput "
            "isolation, and leakage boundaries for the fixture and live owner code. It "
            "does not claim theorem-solving performance, public release readiness, "
            "provider success, open-problem solution, in-loop mutation safety, or permission "
            "to count oracle repair comparator success as forward Lab success."
        ),
        "next_refinement_move": (
            "Keep continuous_loop_three_lane_parallel_oracle_comparator folded into "
            "formal_prover_lab_evaluation_suborgan with proof-diagnostic and "
            "external-boundary siblings. Future continuous-loop or graph-comparison imports "
            "should open the continuous runner, graph benchmark harness, run receipts, "
            "node contracts, oracle result index, foundry learning index, provider trickle "
            "queue, route-readiness sidecars, and option-surface card before claiming "
            "Lab gains, Evolve candidates, provider-blocked math failure, or public "
            "Microcosm readiness."
        ),
    },
    {
        "route_id": "formal_provider_trickle_queue_rate_limit_contract",
        "priority_rank": 8,
        "source_cluster_ids": [
            "formal_math_policy_integrity_and_search_foundry",
            "formal_prover_context_library_prior_and_strategy_gate",
            "formal_math_proof_organ",
        ],
        "target_existing_organs": [
            "formal_prover_lab_evaluation_suborgan",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "provider_trickle_queue_rate_limit_not_math_failure",
        ],
        "why_impressive": (
            "The provider trickle lane becomes reusable only when provider quota "
            "exhaustion is represented as throughput state, not proof failure. This "
            "route binds the continuous-loop queue projection, formal-ladder dispatch "
            "manifest, provider_trickle_queue.json, rate_limit_state.json, retry-only "
            "429/missing policy, next_resume_command, direct_provider_dispatch_in_"
            "continuous_loop=false, provider_dispatch_added_by_loop=false, and "
            "rate_limit_is_math_failure=false so future imports can preserve local "
            "Lean progress while keeping provider retry/resume work resumable and "
            "outside math-correctness accounting."
        ),
        "candidate_fixture": (
            "Toy formal-ladder dispatch manifest with one ok provider receipt, two "
            "429 receipts, and one missing receipt. The continuous-loop trickle fixture "
            "loads that state and asserts provider_trickle_queue.queued_rows include "
            "only 429/missing rows, queued_count excludes ok receipts, queue_policy."
            "retry_only_statuses=['429','missing'], concurrency=1, direct_provider_"
            "dispatch_in_continuous_loop=False, rate_limit_is_math_failure=False, "
            "rate_limit_state.rate_limit_is_math_failure=False, provider_dispatch_"
            "added_by_loop=False, and next_resume_command routes through formal "
            "problem ladder eval with --resume-rate-limited instead of dispatching "
            "provider work inside the continuous controller."
        ),
        "anti_claim_floor": (
            "This route proves provider-trickle queue routability, throughput/not-math "
            "classification, resume boundary, and anti-contamination accounting for "
            "live continuous-loop source plus a synthetic fixture plan. It does not "
            "claim theorem-solving performance, provider success, proof failure, "
            "math correctness, public Microcosm release authority, permission to treat "
            "429s or missing receipts as failed proofs, permission to dispatch provider "
            "jobs from the continuous loop, or permission to expose provider payloads, "
            "account quota state, private problem manifests, proof bodies, oracle "
            "repair bodies, or credential-equivalent provider/session material."
        ),
        "next_refinement_move": (
            "Keep provider_trickle_queue_rate_limit_not_math_failure folded into "
            "formal_prover_lab_evaluation_suborgan with proof-diagnostic and "
            "external-boundary siblings. Future provider-throughput, context-recipe, "
            "continuous-loop, or Evolve-candidate imports should open the continuous "
            "runner, formal-ladder dispatch/resume manifests, provider queue and "
            "rate-limit receipts, continuous-loop tests, extracted-pattern sidecars, "
            "route-readiness report, and option-surface card before claiming provider "
            "blocking, proof failure, math correctness, or public Microcosm readiness."
        ),
    },
    {
        "route_id": "formal_skill_update_candidate_advisory_quarantine_contract",
        "priority_rank": 9,
        "source_cluster_ids": [
            "formal_math_policy_integrity_and_search_foundry",
            "formal_prover_context_library_prior_and_strategy_gate",
            "formal_math_proof_organ",
        ],
        "target_existing_organs": [
            "formal_prover_lab_evaluation_suborgan",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "skill_update_candidate_promotion_advisory_quarantine_lane",
        ],
        "why_impressive": (
            "Skill-update candidates become reusable only when the Evolve output is "
            "kept advisory and quarantined until heldout or perturbation retest. This "
            "route binds the continuous-loop skill_update_candidates.json artifact, "
            "foundry FAIL rows, oracle-repair success/failure comparison, evidence refs, "
            "context_recipe_update_candidates.json, promotion_policy=advisory_only_"
            "until_retested_on_heldout_or_perturbation_family, and the no in-loop "
            "mutation boundary so future imports can mine repair signals without "
            "silently promoting them into skills or proof-success claims."
        ),
        "candidate_fixture": (
            "Toy five-problem continuous-loop Evolve fixture over one problem batch: "
            "two local_foundry FAIL rows with oracle_repair_success=True produce "
            "mine_oracle_repair_into_skill_candidate rows; one local_foundry FAIL row "
            "with oracle_repair_success=False produces quarantine_until_better_oracle_"
            "signal; two local_foundry PASS rows produce no candidates. Validation "
            "asserts candidate_count=3, evidence_refs carry foundry_learning_row, "
            "proof_attempt_critique, and oracle_repair_check, promotion_policy remains "
            "advisory_only_until_retested_on_heldout_or_perturbation_family, no candidate "
            "body or oracle repair body is forward-visible, provider/context-recipe "
            "candidates are advisory only, and no skill file or public Microcosm body is "
            "mutated by the loop."
        ),
        "anti_claim_floor": (
            "This route proves advisory skill-update candidate routing, quarantine "
            "accounting, evidence-ref linkage, and promotion-boundary discipline for "
            "source-coupled continuous-loop code plus a synthetic fixture plan. It does "
            "not claim theorem-solving performance, provider success, actual skill "
            "promotion, in-loop mutation safety, heldout generalization, public Microcosm "
            "release authority, permission to count oracle repair as forward success, "
            "or permission to expose private problem manifests, proof bodies, oracle "
            "repair bodies, provider payloads, account/session material, or raw run "
            "artifact contents."
        ),
        "next_refinement_move": (
            "Keep skill_update_candidate_promotion_advisory_quarantine_lane under "
            "formal_skill_update_candidate_advisory_quarantine_contract and "
            "formal_prover_lab_evaluation_suborgan. Future Evolve, skill-foundry, "
            "context-recipe, provider-throughput, or graph-variant imports should open "
            "run_prover_continuous_lab_oracle_evolve_loop.py::_skill_update_candidates, "
            "_foundry_learning_index, _oracle_result_index, _context_recipe_update_"
            "candidates, run_loop receipts, continuous-loop tests, extracted-pattern "
            "sidecars, route-readiness report, and the option-surface card before "
            "claiming skill promotion, heldout success, oracle-repair learning, provider "
            "gains, or public Microcosm readiness."
        ),
    },
    {
        "route_id": "market_oracle_equity_diff_grading_contract",
        "priority_rank": 7,
        "source_cluster_ids": [
            "market_evidence_and_refusal_stack",
            "standard_owned_option_surfaces",
        ],
        "target_existing_organs": [
            "market_reasoning_evidence_suborgan",
            "prediction_oracle_reconciliation_suborgan",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "oracle_deterministic_equity_diff_grading_surface",
        ],
        "why_impressive": (
            "The Oracle deterministic grading floor becomes reusable only when "
            "prediction_reconciliation schema rows, oracle_truth_diff_equity node "
            "emission, feed_health readiness accounting, run_compare grading, schema "
            "validator checks, and Oracle/Evolve consumers route as one non-"
            "interpretive contract instead of being rediscovered across Lab, Oracle, "
            "world-model, and Evolve source files."
        ),
        "candidate_fixture": (
            "Synthetic subject/truth run pair with Lab CP2 targets for one hit, one "
            "miss, and one ungraded or feed-degraded target. Positive cases assert "
            "prediction_reconciliation.status=AVAILABLE, rows cover comparable "
            "STOCK/ETF targets exactly once, directional_correct and percent_delta "
            "are deterministic, feed_health separates READY/DEGRADED/BLOCKED from "
            "prediction failure, and interpretive fields stay absent. Negative cases "
            "inject duplicate target rows, summary count mismatch, missing subject or "
            "truth prices, malformed asset_class/direction, and narrative blame in "
            "the deterministic grading row and require refusal before realized "
            "hindsight, CP2 critique, or Evolve can consume the artifact."
        ),
        "anti_claim_floor": (
            "This route proves deterministic Oracle equity-diff grading routability, "
            "feed-health boundary accounting, schema validation, and public-safe "
            "fixture shape over source-coupled Oracle comparison code and tests. It "
            "does not claim market prediction accuracy, truth-driver classification "
            "quality, trading signal quality, realized hindsight explanation, CP2 "
            "critique correctness, automated Evolve mutation safety, provider success, "
            "public release authority, or permission to expose private ticker prices, "
            "run artifacts, provider payloads, account/session material, bridge "
            "responses, or raw run artifact contents."
        ),
        "next_refinement_move": (
            "Keep oracle_deterministic_equity_diff_grading_surface folded into "
            "market_reasoning_evidence_suborgan with prediction_oracle_"
            "reconciliation_suborgan, proof diagnostics, and external-boundary "
            "siblings. Future realized_hindsight_brief, cp2_critique, ideal_cp2, or "
            "Evolve imports should open schema_prediction_reconciliation, "
            "oracle_truth_diff_equity, run_compare.py, schema_validator prediction "
            "reconciliation checks, Oracle runtime/tool tests, Evolve feed_health "
            "tests, extracted-pattern sidecars, route-readiness reports, and the "
            "option-surface card before claiming realized-price grading, feed "
            "coverage, prediction failure, or public Microcosm readiness."
        ),
    },
    {
        "route_id": "market_evolve_oracle_dossier_mutation_contract",
        "priority_rank": 9,
        "source_cluster_ids": [
            "market_evidence_and_refusal_stack",
            "standard_owned_option_surfaces",
        ],
        "target_existing_organs": [
            "market_reasoning_evidence_suborgan",
            "prediction_oracle_reconciliation_suborgan",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "evolve_oracle_to_dossier_mutation_loop",
        ],
        "why_impressive": (
            "The market Evolve loop becomes reusable only when deterministic Oracle "
            "artifacts, realized hindsight, CP2 critique, delta-report schema gates, "
            "dossier allowlists, multi-run doctrine-flag evidence, dry-run patch payloads, "
            "overnight review thresholds, and no-live-mutation boundaries route as one "
            "contract instead of being rediscovered across run_evolve, schema_evolve_delta, "
            "world-model snapshots, and Lab/Oracle paper modules."
        ),
        "candidate_fixture": (
            "Synthetic subject/truth run pair with prediction_reconciliation, "
            "realized_hindsight_brief, cp2_critique, ideal_cp2, lab_cp2, and an "
            "evolve_delta_report containing one UPDATE dossier_delta and one HIGH "
            "doctrine_flag backed by two evidence_runs. Positive cases assert "
            "DOSSIER_ALLOWLIST confinement, source_artifact/source_field provenance, "
            "dry-run patch payloads, codex_review_after_runs=3, and Type A review after "
            "any doctrine flag or patch op. Negative cases inject one-run HIGH flags, "
            "off-allowlist dossier paths, missing source provenance, provider payloads, "
            "or live dossier mutation and require refusal."
        ),
        "anti_claim_floor": (
            "This route proves mutation-loop routability, provenance gates, review "
            "thresholds, and public-safe fixture shape over live owner surfaces. It does "
            "not claim trading signal quality, prediction accuracy, automated doctrine "
            "promotion, live dossier mutation safety, provider success, public release "
            "authority, or permission to expose private ticker prices, run artifacts, "
            "provider payloads, account/session material, or raw bridge responses."
        ),
        "next_refinement_move": (
            "Keep evolve_oracle_to_dossier_mutation_loop folded into market_reasoning_"
            "evidence_suborgan with prediction_oracle_reconciliation, proof diagnostics, "
            "and external-boundary siblings. Future market Lab/Oracle/Evolve imports "
            "should open schema_evolve_delta, run_evolve.py, lab_oracle_evolve_"
            "overnight.py, world-model Lab/Oracle snapshot helpers, reasoning execution "
            "plan tests, the option-surface card, and focused binding/readiness tests "
            "before claiming dossier learning, doctrine mutation, public Microcosm "
            "readiness, or market-decision evidence."
        ),
    },
    {
        "route_id": "market_oracle_cp2_grounding_firewall_contract",
        "priority_rank": 8,
        "source_cluster_ids": [
            "market_evidence_and_refusal_stack",
            "standard_owned_option_surfaces",
        ],
        "target_existing_organs": [
            "market_reasoning_evidence_suborgan",
            "prediction_oracle_reconciliation_suborgan",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "oracle_cp2_grounding_firewall",
        ],
        "why_impressive": (
            "The Oracle ideal_cp2 route becomes reusable only when the shared CP2 schema, "
            "subject-run snapshot ledger set, Golden-ID guard, Oracle meta trace, "
            "truth-side explicit exclusions, and engine hard-fail tests travel as one "
            "hindsight-contamination firewall instead of being rediscovered across "
            "schema_cp2, oracle_cp2_emitter, schema_validator, artifacts, and engine "
            "runtime code."
        ),
        "candidate_fixture": (
            "Synthetic subject/truth run pair with a Lab CP2 evidence_dictionary carrying "
            "two subject-side ledger ids, an Oracle ideal_cp2 that reuses only those ids, "
            "oracle_meta.truth_influence_refs and oracle_meta.explicit_exclusions carrying "
            "truth-side handles, and negative cases for a post-T ledger id in evidence_"
            "dictionary, missing subject snapshot context, missing oracle_meta, invalid "
            "Oracle handle format, a new prediction target outside the subject index, and "
            "truth-only evidence leaking into admissible grounding."
        ),
        "anti_claim_floor": (
            "This route proves Oracle CP2 grounding-firewall routability, shared-schema "
            "reuse, subject-side Golden-ID enforcement, Oracle-meta exclusion tracing, "
            "and public-safe fixture shape over live owner surfaces. It does not claim "
            "market prediction accuracy, truth classification quality, trading signal "
            "quality, automated Evolve mutation safety, provider success, public release "
            "authority, or permission to expose private ticker prices, truth-run artifacts, "
            "provider payloads, account/session material, bridge responses, or raw run "
            "artifact contents."
        ),
        "next_refinement_move": (
            "Keep oracle_cp2_grounding_firewall folded into market_reasoning_evidence_"
            "suborgan with prediction_oracle_reconciliation, proof diagnostics, and "
            "external-boundary siblings. Future Oracle ideal_cp2 or Evolve imports should "
            "open schema_cp2, oracle_cp2_emitter, schema_validator Golden-ID and "
            "oracle_meta validators, artifacts snapshot-ledger helpers, engine Oracle "
            "hard-fail tests, the option-surface card, and focused binding/readiness "
            "tests before claiming hindsight-safe evidence, ideal_cp2 training data, "
            "public Microcosm readiness, or market-decision evidence."
        ),
    },
    {
        "route_id": "formal_graph_variant_multi_arm_benchmark_comparison_contract",
        "priority_rank": 8,
        "source_cluster_ids": [
            "formal_math_policy_integrity_and_search_foundry",
            "formal_prover_context_library_prior_and_strategy_gate",
            "formal_math_proof_organ",
        ],
        "target_existing_organs": [
            "formal_prover_lab_evaluation_suborgan",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "graph_variant_multi_arm_benchmark_comparison",
        ],
        "why_impressive": (
            "The graph benchmark harness only becomes reusable when graph variants are "
            "compared as governed arms over source-backed problem manifests rather than "
            "treated as isolated run scripts. This route binds the GRAPH_VARIANTS "
            "catalog, run_benchmark per-arm receipts, Ring-1/Ring-2/strategy/skill "
            "comparison reports, failure_taxonomy, by_split/by_source accounting, "
            "premise_retrieval_metrics, strategy_control_metrics, leakage audits, and "
            "run_hash material so future Microcosm imports can diagnose whether the "
            "binding constraint is retrieval, strategy selection, proof synthesis, "
            "oracle repair, proof search, provider context, or skill overlay evidence."
        ),
        "candidate_fixture": (
            "Toy ten-arm graph benchmark fixture over one five-problem "
            "problem_source_manifest. Run or replay baseline_graph_v0, "
            "premise_retrieval_graph_v0, strategy_control_graph_v0, "
            "strategy_control_graph_v0_skill_atlas_overlay_v0, "
            "strategy_control_graph_v0_skill_foundry_overlay_v0, "
            "source_guarded_strategy_graph_v0, source_guarded_foundry_graph_v0, "
            "tactic_portfolio_graph_v0, hammer_search_graph_v0, and "
            "oracle_repair_graph_v0. Validation asserts aggregate_report rows expose "
            "pass_count, fail_count, pass_rate, failure_taxonomy, by_split, by_source, "
            "premise_retrieval_metrics, strategy_control_metrics, graph_update_candidates, "
            "cost_totals.provider_calls, leakage_audit status, split_policy='train/dev/test; "
            "no tuning on test', and a run_hash over problem_results, aggregate, and graph "
            "updates. Negative cases inject proof bodies, oracle-only premise ids, expected "
            "strategy ids, provider output bypass, or test-split tuning into forward-visible "
            "rows and require validation failure."
        ),
        "anti_claim_floor": (
            "This route proves benchmark-arm routability, comparison accounting, leakage "
            "boundaries, and receipt anchoring for the live harness plus a synthetic fixture "
            "plan. It does not claim theorem-solving performance, certify an external "
            "benchmark, prove all ten arms have already been replayed in one public "
            "Microcosm receipt, count oracle repair as forward success, use test-split "
            "failures as tuning signals, expose proof bodies or oracle-only premise ids, "
            "or treat provider-context compilation as provider success."
        ),
        "next_refinement_move": (
            "Keep graph_variant_multi_arm_benchmark_comparison folded into "
            "formal_prover_lab_evaluation_suborgan with proof-diagnostic and "
            "external-boundary siblings. Future graph-comparison imports should open the "
            "GRAPH_VARIANTS catalog, run_benchmark, comparison-report helpers, live run "
            "receipts, graph benchmark harness tests, extracted-pattern sidecars, and "
            "option-surface card before claiming graph-node promotion, benchmark "
            "performance, provider strategy fit, or public Microcosm readiness."
        ),
    },
    {
        "route_id": "formal_statement_only_hammer_bandit_action_value_policy_contract",
        "priority_rank": 9,
        "source_cluster_ids": [
            "formal_math_policy_integrity_and_search_foundry",
            "formal_prover_context_library_prior_and_strategy_gate",
            "formal_math_proof_organ",
        ],
        "target_existing_organs": [
            "formal_prover_lab_evaluation_suborgan",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "statement_only_hammer_bandit_action_value_policy",
        ],
        "why_impressive": (
            "The statement-only hammer bandit is reusable only when target-shape "
            "classification, tactic-action gating, Lean-checked clean proof selection, "
            "action-value posterior rows, and status-class firewalls stay coupled. This "
            "route binds the statement-only manifest, hammer action manifest, search "
            "results, selected proofs, proof minimization, failure taxonomy, foundry "
            "learning rows, adapter/oracle/provider comparator reports, and status "
            "transition audit so future imports measure a no-provider baseline without "
            "crediting adapter hints, raw proof bodies, provider hypotheses, or oracle "
            "repair as forward solver discovery."
        ),
        "candidate_fixture": (
            "Toy ten-problem statement-only hammer fixture across target_shape buckets "
            "such as closed_nat_mod_decision, int_linear_arithmetic, nat_arithmetic, "
            "and conjunction. Validation builds a statement_only_problem_manifest with "
            "candidate_body, ideal_body, repair_body, oracle-only premise ids, and "
            "provider payloads absent from forward rows; enumerates only shape-allowed "
            "TACTIC_ACTION entries; selects clean proofs by no-sorry/CLEAN axiom audit, "
            "shortest body, and fastest check; computes hammer_action_value_table buckets "
            "from source_family, target_shape, and tactic_id; and rejects negative cases "
            "that inject adapter candidate success, oracle repair success, provider "
            "hypothesis success, raw proof body credit, missing Lean acceptance, or an "
            "illegal status transition into the statement-only lane."
        ),
        "anti_claim_floor": (
            "This route proves statement-only target-shape action-value routing, status "
            "firewall accounting, comparator isolation, and receipt anchoring for the "
            "live runner plus a synthetic fixture plan. It does not claim theorem-solving "
            "performance, external benchmark certification, provider success, public "
            "Microcosm release authority, permission to count adapter hints or oracle "
            "repairs as forward solver discoveries, permission to train on proof bodies, "
            "or permission to expose private proof, provider, adapter, or oracle payloads."
        ),
        "next_refinement_move": (
            "Keep statement_only_hammer_bandit_action_value_policy folded into "
            "formal_prover_lab_evaluation_suborgan with proof-diagnostic and "
            "external-boundary siblings. Future target-shape, action-value, hammer-search, "
            "provider-strategy, or skill-overlay imports should open the statement-only "
            "hammer runner, run receipts, status transition audit, extracted-pattern "
            "sidecars, route-readiness validators, and option-surface card before "
            "claiming policy credit, provider gains, solver discovery, or public "
            "Microcosm readiness."
        ),
    },
    {
        "route_id": "formal_provider_strategy_match_comparator_contract",
        "priority_rank": 10,
        "source_cluster_ids": [
            "formal_math_policy_integrity_and_search_foundry",
            "formal_prover_context_library_prior_and_strategy_gate",
            "formal_math_proof_organ",
        ],
        "target_existing_organs": [
            "formal_prover_lab_evaluation_suborgan",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "provider_strategy_match_comparator",
        ],
        "why_impressive": (
            "Provider strategy classification only becomes reusable when accepted "
            "advisory rows are compared against the deterministic strategy_control "
            "selector on the same problem manifest without becoming proof success. "
            "This route binds the provider strategy reducer, strategy advisory rows, "
            "invalid/missing/leakage quarantine counts, comparable_count denominator, "
            "strategy_match_rate receipt, and explicit provider_results_counted=false "
            "anti-cheat boundary so future imports can measure provider strategy fit "
            "without crediting provider text, Lean-free classification, or search "
            "efficiency deltas as solver discovery."
        ),
        "candidate_fixture": (
            "Toy ten-problem provider-strategy fixture with provider_strategy_advisory_row "
            "outputs and a deterministic strategy_control_graph_v0 strategy_id map over "
            "the same problem manifest digest. Validation asserts accepted advisories "
            "with deterministic labels form the comparable_count denominator, matches "
            "increment only when provider_strategy_id equals deterministic_strategy_id, "
            "invalid_strategy_id, missing_strategy_id, and invalid_leakage rows are "
            "counted outside the numerator and denominator, provider_results_counted=False, "
            "and search-efficiency metrics such as transitions, depth, and branching "
            "are absent until a separate injected-advisory search wave runs."
        ),
        "anti_claim_floor": (
            "This route proves provider strategy-match comparator routability, reducer "
            "accounting, and anti-cheat boundaries for live reducer code plus a synthetic "
            "fixture plan. It does not claim theorem-solving performance, provider proof "
            "success, solver discovery, search-efficiency gains, public Microcosm release "
            "authority, permission to count rejected/leaking/missing advisories in the "
            "match numerator, permission to run providers in the reducer, or permission "
            "to expose raw provider payloads, proof bodies, oracle material, or private "
            "problem manifests."
        ),
        "next_refinement_move": (
            "Keep provider_strategy_match_comparator folded into formal_prover_lab_"
            "evaluation_suborgan with proof-diagnostic and external-boundary siblings. "
            "Future provider-strategy, context-recipe, or search-efficiency imports "
            "should open reduce_prover_provider_receipts.py, compute_strategy_match_"
            "comparison, provider strategy reducer tests, graph benchmark receipts, "
            "statement-only and graph-variant bindings, route-readiness sidecars, and "
            "the option-surface card before claiming provider gains, proof success, "
            "solver discovery, or public Microcosm readiness."
        ),
    },
    {
        "route_id": "mission_transaction_runtime_work_spine",
        "priority_rank": 3,
        "source_cluster_ids": ["mission_transaction_and_scoped_commit"],
        "target_existing_organs": ["mission_transaction_work_spine"],
        "pattern_ids": [
            "mission_transaction_landing",
            "checkpoint_solo_dev_three_lanes",
            "work_ledger_runtime_claims",
            "concurrency_mission_control",
            "cap_reflex_capture_before_prose",
            "cap_quick_capture_lane",
            "task_sign_off",
        ],
        "why_impressive": (
            "Concurrent agent work becomes replayable substrate: claims, leases, scoped "
            "mutation, preflight conflict detection, checkpoint lane selection, and finalizer "
            "receipts are one transaction rather than scattered TODOs."
        ),
        "candidate_fixture": (
            "Synthetic dirty tree plus two active claims: one same-path conflict must replan, "
            "one owned-path mutation lands through scoped commit, and one broad-checkpoint "
            "case requires explicit operator authorization."
        ),
        "anti_claim_floor": (
            "The route proves lane selection and conflict handling for the fixture; it does "
            "not authorize broad staging or override live ownership claims."
        ),
        "next_refinement_move": (
            "Keep this as the mission root for public concurrency; fold isolated work-ledger "
            "and checkpoint rows into its transaction receipt fixture."
        ),
    },
    {
        "route_id": "agent_trace_to_route_repair_observability",
        "priority_rank": 4,
        "source_cluster_ids": ["agent_runtime_observability_and_egress_membrane"],
        "target_existing_organs": [
            "agent_route_observability_runtime",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "agent_self_observability_plane",
            "type_a_type_b_actor_axes",
            "runtime_hook_ladder",
            "lifecycle_surface_resource_membrane",
            "agent_principle_lens",
            "cli_prompt_trace_terminal_validation_capsule",
            "prompt_shelf_metadata_privacy_index",
            "operator_trace_structurer_manual_intake",
            "operator_bridge_tail_projector_privacy_cursor",
            "agent_mission_status_noise_demotion_reducer",
            "runtime_hook_shadow_intervention_coverage",
            "egress_compliance_stop_hook_mirror",
            "route_lease_mode_control_trace_feedback",
        ],
        "why_impressive": (
            "The agent loop audits itself: actor authority axes classify the trace before "
            "routing, manual trace intake is bounded before joins, traces are metadata-first, "
            "the agent-principle lens binds behavior doctrine to entry failures, noisy status "
            "is demoted, route-lease and hook interventions are checked against observed "
            "failures, and egress compliance is mirrored before final answers leave the "
            "private substrate."
        ),
        "candidate_fixture": (
            "Synthetic session trace with a Type A repo-agent event, Type B advisory handoff, "
            "bounded manual trace intake packet, route miss, agent-principle lens selection, "
            "hook shadow suggestion, mission-status noise row, bridge-tail privacy sentinel, "
            "and egress mirror that blocks private-body leakage while preserving a repair "
            "receipt."
        ),
        "anti_claim_floor": (
            "The route demonstrates actor-axis classification, observability, and repair "
            "mechanics over synthetic traces; it must not imply Type A/B is intelligence level, "
            "that the lens mints principles, that live provider traces are public, or that "
            "raw private operator bodies are public."
        ),
        "next_refinement_move": (
            "Use this as the public route-repair organ and make every hook/manual-trace row cite a "
            "synthetic bounded intake or replay receipt before it can be selected."
        ),
    },
    {
        "route_id": "operator_handoff_attention_membrane",
        "priority_rank": 5,
        "source_cluster_ids": [
            "operator_thread_memory_and_type_b_handoff_membrane",
            "agent_runtime_observability_and_egress_membrane",
        ],
        "target_existing_organs": [
            "agent_route_observability_runtime",
            "external_boundary_anti_corruption_runtime",
            "bridge_phase_continuity_runtime",
        ],
        "pattern_ids": [
            "operator_thread_memory_private_event_projection",
            "operator_thread_continuation_type_b_handoff_shuttle",
            "operator_handoff_linkage_confidence_edge_projector",
            "operator_thread_lesson_candidate_advisory_gate",
            "operator_response_flight_attempt_ledger",
            "operator_response_attention_obligation_lease",
            "operator_response_attention_human_loop_compound",
        ],
        "why_impressive": (
            "The human/browser loop is represented as durable metadata: private thread events, "
            "Type B-to-Type A confidence edges, continuation shuttles, attention leases, and "
            "advisory lesson candidates become replayable without publishing raw bodies."
        ),
        "candidate_fixture": (
            "Synthetic multi-tab thread with private sentinels, response-flight events, pending/"
            "completed/seen attention leases, copy/mark-seen receipts, confidence-banded handoff "
            "edges, and lesson candidates that remain mutation_allowed=false."
        ),
        "anti_claim_floor": (
            "This route proves a metadata membrane around operator attention and handoff; it "
            "does not make private ChatGPT/browser transcripts public-safe."
        ),
        "next_refinement_move": (
            "Project only as a folded compound under existing route, boundary, and bridge organs; "
            "do not select as a standalone browser/HUD leaf."
        ),
    },
    {
        "route_id": "multi_agent_handoff_fanin_replay_spine",
        "priority_rank": 6,
        "source_cluster_ids": [
            "bridge_phase_continuity_runtime",
            "mission_transaction_and_scoped_commit",
            "agent_runtime_observability_and_egress_membrane",
        ],
        "target_existing_organs": [
            "bridge_phase_continuity_runtime",
            "mission_transaction_work_spine",
            "agent_route_observability_runtime",
        ],
        "pattern_ids": [
            "multi_agent_handoff_fanin_replay_compound",
        ],
        "why_impressive": (
            "Bounded worker delegation becomes reusable only when handoff packets, claim "
            "leases, fan-in reducer decisions, continuation packets, and public replay "
            "receipts land as one route instead of isolated worker notes."
        ),
        "candidate_fixture": (
            "Synthetic fan-in replay with one planner, two bounded workers, one reviewer/"
            "dissent packet, Work Ledger claim metadata, a continuation packet, a final "
            "reducer decision, a public replay receipt, and private worker state excluded."
        ),
        "anti_claim_floor": (
            "This route proves fan-in accounting and replay-envelope mechanics for the "
            "fixture; it does not prove live subagent quality, expose worker private state, "
            "authorize bridge send/recipient action, or treat agent count as evidence."
        ),
        "next_refinement_move": (
            "Route future fan-in imports through mission transaction, bridge continuity, "
            "and public agent observability; do not treat worker notes as product evidence "
            "until the reducer receipt and replay boundary are present."
        ),
    },
    {
        "route_id": "system_atlas_source_coupling_route_plane",
        "priority_rank": 7,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "navigation_projection_route_plane",
            "generated_projection_source_coupling",
        ],
        "target_existing_organs": ["navigation_hologram_route_plane"],
        "pattern_ids": [
            "system_atlas_kind_atlas_living_map",
            "system_atlas_source_coupling_gate",
        ],
        "why_impressive": (
            "The atlas is reusable only when agents can route from generated Kind/System "
            "Atlas rows back to standards, builders, freshness checks, and source-coupling "
            "receipts without treating the generated projection as authority or refreshing "
            "source-coupled outputs under active source-lane drift."
        ),
        "candidate_fixture": (
            "Synthetic atlas fixture with five artifact kinds, one owner-check row, one "
            "cluster-first option surface, one stale source manifest, one no-refresh "
            "refusal, one active-source-claim blocker, and a projection-not-authority receipt."
        ),
        "anti_claim_floor": (
            "This route proves source-coupled atlas navigation and no-refresh behavior for "
            "synthetic rows; it does not certify the full generated graph, authorize "
            "generated-only commits under drift, or replace source standards and ledgers."
        ),
        "next_refinement_move": (
            "Keep System Atlas and Kind Atlas imports under the navigation route plane; "
            "future public leaves must cite standards, build_system_atlas.py checks, "
            "option-surface cards, and source-coupling receipts before relying on atlas rows."
        ),
    },
    {
        "route_id": "test_impact_change_validation_spine",
        "priority_rank": 8,
        "source_cluster_ids": [
            "test_intelligence",
            "proof_diagnostic_evidence_spine",
            "mission_transaction_and_scoped_commit",
        ],
        "target_existing_organs": [
            "proof_diagnostic_evidence_spine",
            "mission_transaction_work_spine",
        ],
        "pattern_ids": [
            "test_impact_map_change_to_test_routing",
        ],
        "why_impressive": (
            "Changed-path validation becomes reusable only when the test-impact selector, "
            "declared policy, generated expansion sidecar, test inventory, run-slice receipt, "
            "and fallback floor travel as one evidence route instead of an ad hoc command."
        ),
        "candidate_fixture": (
            "Synthetic five-path change set with declared selectors, one unknown fallback path, "
            "three pytest targets, two validators, an expanded impact-map sidecar, and a "
            "run-test-slice plan receipt that proves the selection is never empty."
        ),
        "anti_claim_floor": (
            "This route proves bounded change-to-test selection and fallback behavior for the "
            "fixture; it does not prove that omitted tests are irrelevant or that the declared "
            "impact map covers every live source path."
        ),
        "next_refinement_move": (
            "Keep the impact-map row under proof diagnostics with mission transaction carried "
            "as the execution sibling; future imports must cite the selector code, generated "
            "sidecar, inventory standard, and focused selector/run-slice tests before reuse."
        ),
    },
    {
        "route_id": "autonomous_proof_gate_three_color_mutation_membrane",
        "priority_rank": 9,
        "source_cluster_ids": [
            "mission_transaction_and_scoped_commit",
            "standard_owned_option_surfaces",
        ],
        "target_existing_organs": [
            "mission_transaction_work_spine",
            "proof_diagnostic_evidence_spine",
            "navigation_hologram_route_plane",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "autonomous_proof_gate_three_color_default",
        ],
        "why_impressive": (
            "The mutation gate stops routing every bounded safe change to the operator: "
            "green changes land only after deterministic verifier, rollback, projection, "
            "route-probe, and scoped-transaction evidence; amber retries are bounded and "
            "strengthen the verifier; red emits an exception packet instead of silently "
            "auto-applying or asking for routine review."
        ),
        "candidate_fixture": (
            "Synthetic three-proposal mutation lane: one green doc/projection change with "
            "path scope, fingerprint, rollback artifact, projection rebuild, route probe, "
            "and scoped commit preflight; one amber underanchored change that retries once "
            "with the stronger independent verifier before resolving; and one red "
            "semantic/private/high-blast proposal that emits decision_needed, "
            "why_machine_gate_failed, safe_fallback, and disconfirming_check."
        ),
        "anti_claim_floor": (
            "This route proves the internal machine-verifiable mutation membrane for "
            "synthetic fixtures and live owner surfaces. It does not authorize live "
            "cloud/account mutation, provider/browser/session access, irreversible "
            "storage changes, public release, public source visibility, benchmark claims, "
            "or bypass of Work Ledger, Task Ledger, scoped commit, publication, or "
            "privacy gates."
        ),
        "next_refinement_move": (
            "Keep autonomous_proof_gate_three_color_default as a composition route over "
            "mission_transaction_work_spine, proof_diagnostic_evidence_spine, and "
            "navigation_hologram_route_plane. Future agents should open "
            "autonomous_proof_gate_default, std_navigation_population_acceptance, "
            "routing_atom_population, std_python bridge_authoring_lane, Python compliance "
            "campaign/verifier owners, mission transaction preflight, scoped commit, and "
            "this option-surface card before promoting another lane or asking for "
            "operator review on bounded green work."
        ),
    },
    {
        "route_id": "autonomous_proof_gate_promotion_amber_escalation_membrane",
        "priority_rank": 10,
        "source_cluster_ids": [
            "mission_transaction_and_scoped_commit",
            "standard_owned_option_surfaces",
            "bridge_continuity_runtime",
        ],
        "target_existing_organs": [
            "formal_prover_lab_evaluation_suborgan",
            "mission_transaction_work_spine",
            "proof_diagnostic_evidence_spine",
            "navigation_hologram_route_plane",
            "bridge_phase_continuity_runtime",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "autonomous_proof_gate_promotion_rule_amber_bounded_retry",
        ],
        "why_impressive": (
            "The promotion membrane makes autonomous proof-gate status a proved admission "
            "contract rather than a label: a lane must show explicit path scope, "
            "deterministic verifier set, independent adjudicator option, rollback artifact, "
            "route probe, and fingerprint contract before using the green/amber/red gate. "
            "Amber stays bounded, the second retry must strengthen independent verification, "
            "and exhaustion downgrades to a red exception packet instead of looping or "
            "routing routine approvals to the operator."
        ),
        "candidate_fixture": (
            "Synthetic promotion ledger with three lanes: one missing rollback artifact and "
            "therefore blocked from claiming gate status; one satisfying all six admission "
            "conditions and allowed to classify green work; and one amber lane whose first "
            "retry is inconclusive, whose second retry must use a stronger independent "
            "verifier, and whose exhaustion emits decision_needed, why_machine_gate_failed, "
            "safe_fallback, evidence, and aggregate-only operator digest fields."
        ),
        "anti_claim_floor": (
            "This route proves internal lane-promotion and amber-escalation discipline for "
            "synthetic fixtures and live owner surfaces. It does not authorize publication, "
            "provider/browser/account access, secret handling, irreversible mutation, public "
            "benchmark claims, or any lane self-declaring autonomous without the six-condition "
            "admission evidence and scoped transaction receipts."
        ),
        "next_refinement_move": (
            "Keep autonomous_proof_gate_promotion_rule_amber_bounded_retry as the admission "
            "and retry contract immediately after autonomous_proof_gate_three_color_default. "
            "Future agents should open autonomous_proof_gate_default, "
            "std_navigation_population_acceptance promotion_rule and amber policy, "
            "routing_atom_population, mission transaction preflight, scoped commit, Python "
            "compliance verifier owners, Work Ledger, Task Ledger, and this option-surface "
            "card before claiming a lane has autonomous proof-gate authority."
        ),
    },
    {
        "route_id": "navigation_population_acceptance_route_plane_contract",
        "priority_rank": 11,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "mission_transaction_and_scoped_commit",
            "proof_diagnostic_evidence_spine",
        ],
        "target_existing_organs": [
            "navigation_hologram_route_plane",
            "proof_diagnostic_evidence_spine",
            "mission_transaction_work_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "navigation_population_acceptance",
        ],
        "why_impressive": (
            "Navigation surface growth becomes governed when every proposed row patch "
            "collapses into a green, amber, or red admission outcome with source "
            "fingerprints, route probes, rollback material, verifier evidence, and an "
            "operator packet only for red cases. The route-plane can then accept, retry, "
            "or quarantine population work without future agents rediscovering the "
            "standard from prose."
        ),
        "candidate_fixture": (
            "Synthetic navigation-population cohort with three row patches: one green "
            "docstring/projection-only patch carrying explicit path scope, matching "
            "fingerprint, route probe, rollback artifact, and verifier receipts; one "
            "amber patch with incomplete green evidence that retries under a stronger "
            "independent verifier; and one red patch with semantic/private/high-blast "
            "risk that emits decision_needed, why_machine_gate_failed, safe_fallback, "
            "evidence, disconfirming_check, and aggregate-only operator digest fields."
        ),
        "anti_claim_floor": (
            "This route proves internal navigation-population admission and disposition "
            "for synthetic fixtures and live owner surfaces. It does not authorize "
            "publication, provider/browser/account access, secret handling, semantic "
            "runtime edits, test edits, irreversible mutation, public release, or bypass "
            "of Work Ledger, Task Ledger, scoped transaction preflight, route readiness, "
            "or owner validators."
        ),
        "next_refinement_move": (
            "Keep navigation_population_acceptance as the route-plane admission contract "
            "under navigation_hologram_route_plane with proof diagnostics, mission "
            "transaction, and external-boundary siblings. Future agents should open "
            "std_navigation_population_acceptance, navigation_population_acceptance.py, "
            "the extracted-pattern binding/readiness sidecars, the option-surface card, "
            "Work Ledger claims, Task Ledger capture rules, route probes, rollback and "
            "fingerprint contracts, and focused acceptance tests before adding another "
            "navigation surface or treating operator review as the default."
        ),
    },
    {
        "route_id": "autonomy_runtime_metabolism_loop_control_contract",
        "priority_rank": 12,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "bridge_continuity_runtime",
            "mission_transaction_and_scoped_commit",
            "agent_runtime_observability_and_egress_membrane",
        ],
        "target_existing_organs": [
            "bridge_phase_continuity_runtime",
            "agent_route_observability_runtime",
            "mission_transaction_work_spine",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "autonomy_runtime_metabolism_loop",
        ],
        "why_impressive": (
            "The always-on autonomy story becomes governable when the daemon contract, "
            "plan substrate, seat lifecycle, serial runtime loop, state root, manual-assist "
            "fallback, stop seam, Work Ledger claims, and proof-gate receipts route as one "
            "artifact-gated control loop instead of being rediscovered across nine paper "
            "modules and runner tests."
        ),
        "candidate_fixture": (
            "Synthetic autonomy runtime tick with one enabled chain item, one Type A seed "
            "seat that records transport/seat evidence, one bridge_campaign observation-only "
            "item that must resolve manual_assist_required, one disabled operation skipped "
            "without dispatch, one stop-at-next-seam flag, one plan_state closeout, and one "
            "red refusal for live provider/account or irreversible mutation."
        ),
        "anti_claim_floor": (
            "This route proves the internal runtime-loop composition for synthetic fixtures "
            "and live owner surfaces. It does not authorize a second resident daemon, live "
            "provider/browser/account mutation, secret handling, public release, irreversible "
            "writes, timer-based completion, bypass of metabolismd start guards, or any "
            "autonomy claim without Work Ledger claims, owner validators, runtime ledger "
            "evidence, and proof-gate receipts."
        ),
        "next_refinement_move": (
            "Keep autonomy_runtime_metabolism_loop as the control contract over the scoped "
            "autonomy runner, daemon composition, plan substrate, Type A seat lifecycle, "
            "state root, and proof gates. Future agents should open std_autonomy_runtime, "
            "std_autonomy_plan, std_type_a_seat_control, overnight_chain_runner.py, "
            "autonomy_plan.py, type_a_seat_control.py, metabolismd.py, codex_driver.py, "
            "codex_resume.py, the option-surface card, and focused runtime tests before "
            "claiming always-on autonomy behavior or splitting the runtime stack further."
        ),
    },
    {
        "route_id": "autonomy_plan_baton_closeout_bridge_continuity_contract",
        "priority_rank": 13,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "bridge_continuity_runtime",
            "mission_transaction_and_scoped_commit",
            "agent_runtime_observability_and_egress_membrane",
        ],
        "target_existing_organs": [
            "bridge_phase_continuity_runtime",
            "mission_transaction_work_spine",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "autonomy_plan_baton_closeout_contract",
        ],
        "why_impressive": (
            "The plan baton and closeout substrate becomes reusable when step validation, "
            "runtime-item compilation, bridge_snapshot application, seat attribution, "
            "five-sentence baton contracts, binary done/needs_another_go closeout flags, "
            "subphase context, Work Ledger continuity, and proof receipts route as one "
            "bridge-continuity contract instead of being rediscovered from autonomy_plan.py, "
            "autonomy_subphase.py, seat probes, and scattered runtime tests."
        ),
        "candidate_fixture": (
            "Synthetic three-step autonomy plan: one codex_task step with a self baton, one "
            "bridge_snapshot step that returns runtime_items, next_step_updates, "
            "provider_limits_observed, five baton sentences, and confidence >= 0.5, and "
            "one runtime_items step with concurrent seat bindings. Positive cases assert "
            "valid step kinds, runtime item kinds, concurrency, seat bindings, closeout "
            "status, baton register, bridge snapshot plan_state merge, and subphase context. "
            "Negative cases fail for four-sentence batons, unsupported closeout status, "
            "low-confidence snapshot application, unknown runtime item kinds, live provider "
            "payload leakage, and rewriting the source plan manifest."
        ),
        "anti_claim_floor": (
            "This route proves the internal autonomy plan baton/closeout continuity contract "
            "for synthetic fixtures and live owner surfaces. It does not launch seats, call "
            "providers, run bridge, authorize a resident daemon, publish private plan state, "
            "certify all plans complete, bypass Work Ledger, Task Ledger, seat approval, "
            "snapshot confidence, scoped commit, or proof gates, or make a bridge snapshot "
            "a substitute for controller-owned closeout."
        ),
        "next_refinement_move": (
            "Keep autonomy_plan_baton_closeout_contract under bridge_phase_continuity_runtime "
            "with mission transaction, proof diagnostics, and external-boundary siblings. "
            "Future plan, baton, closeout, or seat-continuity work should open "
            "autonomy_plan_surface, autonomy_plan_substrate, autonomy_plan_seat_lifecycle, "
            "autonomy_plan_bridge_snapshot, bridge_runtime_control_plane, "
            "claude_subagent_delegation, std_autonomy_plan, std_autonomy_runtime, "
            "std_type_a_seat_control, autonomy_plan.py, autonomy_subphase.py, "
            "codex_runtime_probe.py, overnight_chain_runner.py, the option-surface card, "
            "and focused autonomy plan/snapshot/execution tests before claiming plan "
            "continuity, baton transfer, or closeout semantics."
        ),
    },
    {
        "route_id": "reaction_autonomy_bridge_continuity_contract",
        "priority_rank": 13,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "bridge_continuity_runtime",
            "agent_runtime_observability_and_egress_membrane",
            "kernel_command_projection_runtime",
        ],
        "target_existing_organs": [
            "bridge_phase_continuity_runtime",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
            "agent_route_observability_runtime",
        ],
        "pattern_ids": [
            "reaction_evaluation_dual_fingerprint_dedupe",
            "reaction_wake_barrier_suspend_resume",
            "lifecycle_boundary_to_reaction_signal",
        ],
        "why_impressive": (
            "The reactions substrate becomes reusable when typed signal loading, predicate "
            "matching, armed-state gates, cooldown gates, signal_digest dedupe, terminal "
            "outcome plus ledger-fingerprint dedupe, detached runner spawn, persisted wake "
            "barriers, hard-kill recovery, lifecycle-boundary hook signals, and latest-only "
            "wake semantics route as one bridge-continuity contract instead of being "
            "rediscovered from reactions_engine.py, reactions.yaml, runtime_hook.py, "
            "runtime_hook_ladder, and scattered reaction proof tests."
        ),
        "candidate_fixture": (
            "Synthetic reactions runtime with three rows: one ordinary signal with "
            "dedupe_by=signal_digest and terminal completed_digest_fingerprint history, "
            "one detached operation that installs an operation_completion barrier with a "
            "runner PID and 45-minute hard-kill guard, and one session_lifecycle_boundary "
            "hook event promoted to stable_signal_digest. Positive cases assert six-gate "
            "evaluation, stable digest reuse, completed digest suppression, digest-collision "
            "refire allowance, barrier persistence, PID-exit barrier clearing, hard-kill "
            "force clear, latest-only lifecycle wake, and Work Ledger projection action "
            "routing. Negative cases reject per-event queue-drain claims, concurrent fires "
            "while a barrier is active, timestamp-only refires, live provider/browser "
            "payload export, and reaction mutation without Work Ledger/controller proof."
        ),
        "anti_claim_floor": (
            "This route proves reaction autonomy routing over live owner surfaces and "
            "synthetic/private-root-safe fixtures. It does not start the daemon, fire live "
            "operations, mutate doctrine, publish private hook/session/operator/provider "
            "payloads, claim lifecycle rows are a durable queue, bypass controller review, "
            "or treat reaction logs, generated projections, or latest wake signals as "
            "public release authority."
        ),
        "next_refinement_move": (
            "Keep reaction_evaluation_dual_fingerprint_dedupe, reaction_wake_barrier_"
            "suspend_resume, and lifecycle_boundary_to_reaction_signal under "
            "bridge_phase_continuity_runtime with proof diagnostics, external-boundary, "
            "and agent-route-observability siblings. Future reaction/autonomy work should "
            "open reactions_engine, runtime_hook_ladder, continuous_runtime_layer, "
            "autonomy_runtime_layer, bridge_runtime, std_reactions, std_orchestration_"
            "events, reactions.yaml, runtime_hook.py, lifecycle-boundary tests, reaction "
            "proof/targeted tick tests, generated binding/readiness sidecars, and "
            "option-surface cards before claiming reaction dedupe, wake barriers, "
            "lifecycle wake, or public import readiness."
        ),
    },
    {
        "route_id": "system_control_orchestration_composition_root_contract",
        "priority_rank": 13,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "bridge_continuity_runtime",
            "mission_transaction_and_scoped_commit",
            "agent_runtime_observability_and_egress_membrane",
            "kernel_command_projection_runtime",
        ],
        "target_existing_organs": [
            "bridge_phase_continuity_runtime",
            "agent_route_observability_runtime",
            "mission_transaction_work_spine",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "system_control_orchestration_composition_root",
        ],
        "why_impressive": (
            "Runtime control becomes reusable when phase, factory, mission queue, "
            "apply-staging, bridge locks, docs-route focus, bootstrap actor frames, "
            "reactions projection, Python-standard compliance, state JSON, brief JSON/MD, "
            "event-log fingerprinting, and directive mutation route as one composition "
            "root instead of being rediscovered from every lane independently."
        ),
        "candidate_fixture": (
            "Synthetic orchestration repo with a dormant phase, invalid apply packet, "
            "empty mission queue, neutral docs-route focus, no live bridge lock, one "
            "bootstrap actor-context surface, one reactions projection, and one Python "
            "standard-compliance projection. Positive cases assert the selected driver, "
            "gate reason, coordination owner, next handoff, routing-emphasis tags, actor "
            "frames, state/brief/event artifact paths, event fingerprint idempotence, "
            "and docs-route focus deltas. Negative cases reject direct docs-focus JSON "
            "mutation, direct orchestration_state writes, live bridge/provider payload "
            "export, and treating generated artifacts as source authority."
        ),
        "anti_claim_floor": (
            "This route proves the internal runtime-control composition root over live "
            "owner surfaces and synthetic/private-root-safe snapshots. It does not arm a "
            "runtime phase, launch bridge or provider work, mutate live directives outside "
            "the controller helper, publish private lane payloads, bypass Work Ledger or "
            "proof gates, replace source lane owners, or treat orchestration_state, brief, "
            "or events as public release authority."
        ),
        "next_refinement_move": (
            "Keep system_control_orchestration_composition_root under "
            "bridge_phase_continuity_runtime with agent-route observability, mission "
            "transaction, proof diagnostics, and external-boundary siblings. Future "
            "control-plane or docs-route work should open system_control_runtime_"
            "orchestration, bridge_runtime_control_plane, microcosm_substrate, "
            "system/control/orchestration.py, system/control/documentation_route_focus.py, "
            "std_orchestration_state, std_orchestration_events, std_agent_bootstrap, "
            "generated orchestration state/brief/events artifacts, focused overnight/"
            "runtime-contract tests, route-readiness sidecars, and option-surface cards "
            "before claiming runtime-control ownership, directive mutation, or public "
            "import readiness."
        ),
    },
    {
        "route_id": "continuous_runtime_layer_bridge_continuity_contract",
        "priority_rank": 13,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "bridge_continuity_runtime",
            "mission_transaction_and_scoped_commit",
            "agent_runtime_observability_and_egress_membrane",
        ],
        "target_existing_organs": [
            "bridge_phase_continuity_runtime",
            "agent_route_observability_runtime",
            "mission_transaction_work_spine",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "continuous_runtime_layer",
        ],
        "why_impressive": (
            "The cross-turn runtime substrate becomes reusable when continuation packets, "
            "state-backed Codex handoff, signal watchers, autonomous-seed continuity, "
            "Codex resume transport, phase/pipeline helper boundaries, Work Ledger "
            "claims, proof receipts, and public/private anti-claims route as one "
            "bridge-continuity contract rather than as scattered paper modules and "
            "resume scripts."
        ),
        "candidate_fixture": (
            "Synthetic three-turn continuity run: first turn writes a continuation packet "
            "from state-backed context, second turn resumes from the Codex transport after "
            "a phase or pipeline-state transition, third turn lands one bounded action "
            "with Work Ledger claim, proof receipt, and seed heartbeat; include one busy "
            "thread/manual-assist fallback and one red refusal for provider/account or "
            "irreversible mutation."
        ),
        "anti_claim_floor": (
            "This route proves internal cross-turn continuity and resume wiring for "
            "synthetic fixtures and live owner surfaces. It does not authorize a second "
            "resident daemon, live provider/browser/account access, secret handling, "
            "public release, timer-based completion, unbounded autonomy, or bypass of "
            "Work Ledger, Task Ledger, scoped commit, seed heartbeat, publication, "
            "privacy, or proof gates."
        ),
        "next_refinement_move": (
            "Keep continuous_runtime_layer as the bridge-continuity substrate around "
            "continuation packets, Codex handoff, signal watchers, autonomous seed "
            "continuity, and phase/pipeline helper boundaries. Future agents should open "
            "continuous_runtime_layer, phase_runtime_library, pipeline_runtime_library, "
            "std_autonomous_seed_prompt, std_agent_entry_surface, continuation_packet.py, "
            "pipeline_codex_handoff.py, pipeline_signal_watcher.py, codex_resume.py, "
            "the option-surface card, and focused continuation/resume tests before "
            "claiming persistent runtime behavior or splitting continuity from its "
            "governed wake/claim/proof seams."
        ),
    },
    {
        "route_id": "governor_mode_dispatch_runtime_gas_pedal_contract",
        "priority_rank": 14,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "bridge_continuity_runtime",
            "mission_transaction_and_scoped_commit",
            "agent_runtime_observability_and_egress_membrane",
        ],
        "target_existing_organs": [
            "bridge_phase_continuity_runtime",
            "agent_route_observability_runtime",
            "mission_transaction_work_spine",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "governor_mode_dispatch_state_machine",
        ],
        "why_impressive": (
            "The runtime gas pedal becomes reusable when governor modes, provider budgets, "
            "CPU and memory pressure gates, local-cost classes, provider dispatch history, "
            "metabolismd admission, Work Ledger claims, proof receipts, and no-paid-auto "
            "anti-claims route as one bounded control contract instead of being rediscovered "
            "inside scheduler and provider-pressure code."
        ),
        "candidate_fixture": (
            "Synthetic governor-mode matrix: paused admits no selector dispatch, trickle allows "
            "one remote-light local-light item while blocking heavy local work, active keeps "
            "normal concurrency, overnight widens local pressure tolerance, sprint permits "
            "three ChatGPT dispatches, high CPU or pressure-red cooldown blocks heavy local "
            "launches, and provider spacing history blocks repeat dispatch before the mode "
            "budget expires."
        ),
        "anti_claim_floor": (
            "This route proves internal dispatch admission and resource governance for "
            "synthetic fixtures and live owner surfaces. It does not dispatch providers, "
            "authorize paid spend, run a resident daemon, bypass Work Ledger or proof gates, "
            "override operator stop signals, prove queue execution, or collapse continuity, "
            "autonomy runtime, provider selection, and launch contracts into one owner."
        ),
        "next_refinement_move": (
            "Keep governor_mode_dispatch_state_machine as the runtime gas-pedal contract "
            "around metabolism_governor.py, metabolismd governor commands, provider pressure "
            "signals, dispatch history, launchable-operation local-cost classes, and focused "
            "governor/provider tests. Future agents should open this option-surface card, "
            "continuous_runtime_layer, autonomy_runtime_metabolism_loop, std_metabolism_status, "
            "std_provider_adapter, std_launchable_operation_contract, metabolism_governor.py, "
            "metabolismd.py, provider_metabolism_signal.py, bridge_provider_pressure.py, and "
            "the focused tests before claiming dispatch, resource, or paid-provider behavior."
        ),
    },
    {
        "route_id": "meta_mission_queue_runtime_adapter_contract",
        "priority_rank": 15,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "bridge_continuity_runtime",
            "mission_transaction_and_scoped_commit",
            "agent_runtime_observability_and_egress_membrane",
        ],
        "target_existing_organs": [
            "bridge_phase_continuity_runtime",
            "agent_route_observability_runtime",
            "mission_transaction_work_spine",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "meta_mission_queue_runtime",
        ],
        "why_impressive": (
            "The legacy queue lane becomes reusable when the manifest standard, explicit "
            "operator-authored agenda, serial item executor, sync-only launchable operation "
            "gate, queue ledger/state root, stop/resume seams, Station overnight_queue "
            "payload, Work Ledger claims, and proof-gate receipts route as one adapter "
            "contract instead of being collapsed into the broader autonomy runtime loop."
        ),
        "candidate_fixture": (
            "Synthetic legacy queue manifest with one enabled chain item, one sync operation "
            "item, one disabled item skipped without dispatch, one detached operation rejected "
            "by preflight, one stop-at-next-item-boundary request, one resume-from-next-seam "
            "run, one provider_wait projection, and one red refusal for live provider/account "
            "access or queue-driven reactions arming."
        ),
        "anti_claim_floor": (
            "This route proves internal legacy queue-adapter composition for synthetic "
            "fixtures and live owner surfaces. It does not authorize a scheduler, DAG or "
            "parallel execution, detached operation items, queue-driven reaction arming, "
            "provider/browser/account access, public release, paid spend, a resident daemon, "
            "or bypass of Work Ledger, Task Ledger, stop seams, scoped commit, privacy, or "
            "proof gates."
        ),
        "next_refinement_move": (
            "Keep meta_mission_queue_runtime as the compatibility adapter under "
            "std_autonomy_runtime and autonomy_runtime_metabolism_loop, not as a second "
            "autonomy runtime. Future agents should open meta_mission_queue_runtime, "
            "meta_mission_runtime, overnight_meta_mission_queue, std_meta_mission_queue, "
            "std_autonomy_runtime, overnight_chain_runner.py, chain_runtime.py, "
            "launchable_operations.py, world_model.py, the option-surface card, and "
            "focused queue/runtime tests before claiming queue launch, stop, resume, "
            "provider-wait, or Station overnight_queue behavior."
        ),
    },
    {
        "route_id": "provider_metabolism_ledger_authority_class_contract",
        "priority_rank": 15,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "bridge_continuity_runtime",
            "mission_transaction_and_scoped_commit",
            "agent_runtime_observability_and_egress_membrane",
        ],
        "target_existing_organs": [
            "agent_route_observability_runtime",
            "bridge_phase_continuity_runtime",
            "mission_transaction_work_spine",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "provider_metabolism_ledger",
        ],
        "why_impressive": (
            "Provider output becomes reusable only when calls are routed through a typed "
            "metabolism ledger: provider registry rows, compute ledger/model catalog "
            "projections, task-class policy, worker packet previews, provider receipts, "
            "row patches, cache keys, validation_result evaluator output, cost, latency, "
            "and authority ceilings travel as one accounting contract instead of being "
            "rediscovered across provider docs, harness code, and row-patch state."
        ),
        "candidate_fixture": (
            "Synthetic compute-provider fixture with NVIDIA and OpenRouter registry rows, "
            "one accepted route_worker packet, one rejected high-authority task, one "
            "provider_receipt with cost/latency/validation_result fields, one cache-hit "
            "receipt, and one draft row_patch. Assertions cover independent capacity "
            "lanes, free-only budget, local evidence override policy id, provider output "
            "remaining receipt/row_patch-only, and no source mutation."
        ),
        "anti_claim_floor": (
            "This route proves internal provider accounting, evaluator-output separation, "
            "and authority-ceiling visibility for synthetic fixtures and live owner "
            "surfaces. It does not call providers, run a daemon, dispatch work, claim "
            "slots, promote row patches, mutate source, certify provider output as true, "
            "authorize paid spend, override selector, liveness, reducer, governor, queue, "
            "or apply-lane contracts, or bypass Work Ledger, Task Ledger, scoped commit, "
            "seed heartbeat, privacy, stop, or proof gates."
        ),
        "next_refinement_move": (
            "Keep provider_metabolism_ledger as the provider accounting and evaluator "
            "boundary around compute_throughput.py, build_compute_throughput_ledger.py, "
            "std_compute_provider, std_provider_adapter, std_transform_job, provider "
            "registry rows, compute hologram ledgers, type_a_worker_harness receipts, and "
            "focused compute/provider tests. Future provider work should open this route "
            "with provider_candidate_selector_snapshot, provider_plane_finite_pull_liveness, "
            "type_a_reducer_row_patch_review_gate, compute_worker_receipts, and route-"
            "readiness overlays before claiming provider evidence, dispatch, advisory "
            "status, liveness, or release authority."
        ),
    },
    {
        "route_id": "provider_plane_finite_pull_row_job_membrane_contract",
        "priority_rank": 16,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "bridge_continuity_runtime",
            "mission_transaction_and_scoped_commit",
            "agent_runtime_observability_and_egress_membrane",
        ],
        "target_existing_organs": [
            "agent_route_observability_runtime",
            "bridge_phase_continuity_runtime",
            "mission_transaction_work_spine",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "provider_plane_finite_pull_row_job",
        ],
        "why_impressive": (
            "Provider application-discovery work becomes reusable when the local catalog, "
            "liveness projection, shard selection, allowed source refs, strict output "
            "schema, transform-job seed, no-paid/no-retry budget, source fingerprint, "
            "receipts/row_patch-only sink, forbidden source/doctrine/task-ledger writes, "
            "and Type A reduction route as one finite row-job membrane instead of a hidden "
            "provider queue, daemon, or rediscovered discovery workflow."
        ),
        "candidate_fixture": (
            "Synthetic provider-plane fixture with catalog, receipts, and row_patches shards. "
            "Build application-discovery row jobs for catalog and receipts; assert exactly "
            "one row job per shard, max_candidates <= 3, free-only budget, max_usd 0, "
            "max_retries 0, provider_endpoint authority ceiling, provider_plane_application_"
            "candidate target facet, bounded allowed source refs, forbidden daemon/source/"
            "doctrine/standards/task-ledger writes, strict output schema, source-fingerprint "
            "drift visibility, Type A controller promotion gate, and validation commands."
        ),
        "anti_claim_floor": (
            "This route proves internal finite-pull provider application-discovery row-job "
            "composition for synthetic fixtures and live owner surfaces. It does not call "
            "providers, run a daemon, drain a queue, retry fanout, mutate source, mutate "
            "Task Ledger, promote row patches, certify provider output as true, authorize "
            "paid spend, override selector, liveness, reducer, governor, queue, Work Ledger, "
            "Task Ledger, scoped commit, seed heartbeat, privacy, stop, or proof gates."
        ),
        "next_refinement_move": (
            "Keep provider_plane_finite_pull_row_job as the finite application-discovery "
            "row-job membrane around metabolism_row_jobs.py, provider_plane_application_"
            "catalog.py, provider_plane_liveness.py, type_a_worker_harness.py, std_compute_"
            "provider, std_provider_adapter, std_transform_job, Work Ledger claims, scoped "
            "commit, and focused row-job/provider-plane tests. Future provider-plane work "
            "should open this route with provider_metabolism_ledger, provider_candidate_"
            "selector_snapshot, provider_plane_finite_pull_liveness, type_a_reducer_row_"
            "patch_review_gate, compute_worker_receipts_provider_provenance, and transform_"
            "job_provenance before claiming provider row-job dispatch, provider evidence, "
            "draft row-patch advisory status, liveness, or release authority."
        ),
    },
    {
        "route_id": "compute_worker_receipts_provider_provenance_evidence_contract",
        "priority_rank": 17,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "bridge_continuity_runtime",
            "mission_transaction_and_scoped_commit",
            "agent_runtime_observability_and_egress_membrane",
        ],
        "target_existing_organs": [
            "agent_route_observability_runtime",
            "bridge_phase_continuity_runtime",
            "mission_transaction_work_spine",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "compute_worker_receipts_provider_provenance",
        ],
        "why_impressive": (
            "Provider compute evidence becomes reusable only when receipts route as a "
            "typed provenance contract: transform_job_id, provider_id, runtime provider, "
            "model_id, task_class, prompt_hash, input_packet_digest, output_schema_hash, "
            "local_evidence_override_policy_id, cache_key, source_fingerprints, neighbor "
            "context hash, output_digest, usage, cost, latency, http_status, status, "
            "validation_result, promotion_state, artifact refs, run fingerprint, cache "
            "entry, and draft row_patch lineage travel together instead of being "
            "rediscovered from worker code, row-job packets, ledger projections, or "
            "private receipt directories."
        ),
        "candidate_fixture": (
            "Synthetic receipt-provenance fixture with five receipts across NVIDIA and "
            "OpenRouter and three task classes: ok, cache_hit, schema_fail, policy_reject, "
            "and blocked_duplicate. Assertions cover receipt clustering by task_class, "
            "source_fingerprints present but redacted from public cluster cards, local "
            "evidence override policy id, output_schema_hash, cache_key, run fingerprint, "
            "usage/cost/latency/http_status fields, validation_result semantics, draft "
            "row_patch only for ok receipts, stale-source promotion blocking, and no "
            "source/doctrine/standards mutation."
        ),
        "anti_claim_floor": (
            "This route proves internal provider receipt provenance and draft row-patch "
            "lineage for synthetic fixtures and live owner surfaces. It does not publish "
            "private receipt payloads, call providers, run a daemon, dispatch work, "
            "certify provider output as true, promote row patches, mutate source, override "
            "row-job, selector, liveness, reducer, governor, queue, Work Ledger, Task "
            "Ledger, scoped commit, seed heartbeat, privacy, stop, or proof gates, or "
            "authorize paid spend."
        ),
        "next_refinement_move": (
            "Keep compute_worker_receipts_provider_provenance as the receipt evidence "
            "root around type_a_worker_harness.py, std_transform_job provider_receipt, "
            "std_compute_provider, compute_worker_receipts.md, type_a_worker_harness.md, "
            "state/compute_workers receipts/cache/run_fingerprints/row_patches, and "
            "focused receipt tests. Future provider-plane work should open this route "
            "with provider_metabolism_ledger, provider_plane_finite_pull_row_job, "
            "provider_candidate_selector_snapshot, provider_plane_finite_pull_liveness, "
            "type_a_reducer_row_patch_review_gate, and transform_job_provenance before "
            "claiming provider evidence, stale-source promotion behavior, receipt truth, "
            "or row-patch lineage."
        ),
    },
    {
        "route_id": "transform_job_provenance_seed_lineage_contract",
        "priority_rank": 18,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "bridge_continuity_runtime",
            "mission_transaction_and_scoped_commit",
            "agent_runtime_observability_and_egress_membrane",
        ],
        "target_existing_organs": [
            "agent_route_observability_runtime",
            "bridge_phase_continuity_runtime",
            "mission_transaction_work_spine",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "transform_job_provenance",
        ],
        "why_impressive": (
            "Provider-plane transformations become reusable when the transform_job seed "
            "routes as a typed lineage contract: task_class, target row/facet/band, "
            "source_fingerprints, input_packet digest, output_schema, local evidence "
            "override policy, authority ceiling, forbidden surfaces, provider selection "
            "policy, provider budget, cache_key, validation command, receipt target, "
            "promotion_target, row-job materialization posture, and no-source-mutation "
            "boundary travel together before any receipt or row_patch can be interpreted."
        ),
        "candidate_fixture": (
            "Synthetic transform-job fixture with five jobs: a valid derive_flag job, a "
            "row-job materialized provider_transform_job draft, a forbidden-surface policy "
            "reject, a stale-source-fingerprint promotion block, and a paid-budget veto. "
            "Assertions cover source_fingerprints, input_packet_digest/cache_key stability, "
            "output_schema_hash, local_evidence_override_policy_id, provider budget "
            "free_only/no paid, validation_command presence, receipt_target, promotion_"
            "target draft posture, scheduler refusal without job_path, and no source/"
            "doctrine/standards/Task Ledger mutation."
        ),
        "anti_claim_floor": (
            "This route proves internal transform-job seed lineage and materialization "
            "contracts for synthetic fixtures and live owner surfaces. It does not call "
            "providers, dispatch a scheduler job, claim provider slots, certify provider "
            "output as true, publish private input packets, promote row patches, mutate "
            "source, authorize paid spend, override receipt, row-job, selector, liveness, "
            "reducer, governor, queue, Work Ledger, Task Ledger, scoped commit, seed "
            "heartbeat, privacy, stop, or proof gates."
        ),
        "next_refinement_move": (
            "Keep transform_job_provenance as the seed-lineage owner around "
            "std_transform_job.transform_job, std_provider_navigation_transform_receipt, "
            "type_a_worker_harness.py build/normalize/materialize/run functions, "
            "metabolism_row_jobs.py transform_job_seed rows, compute throughput ledgers, "
            "state/compute_workers/transform_jobs, and focused transform-job tests. Future "
            "provider-plane work should open this route with provider_plane_finite_pull_"
            "row_job, compute_worker_receipts_provider_provenance, provider_metabolism_"
            "ledger, provider_candidate_selector_snapshot, provider_plane_finite_pull_"
            "liveness, and type_a_reducer_row_patch_review_gate before claiming transform "
            "lineage, budget policy, validation command, receipt evidence, dispatch, or "
            "promotion authority."
        ),
    },
    {
        "route_id": "worker_run_fingerprint_dedup_cache_gate_idempotent_dispatch_contract",
        "priority_rank": 19,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "bridge_continuity_runtime",
            "mission_transaction_and_scoped_commit",
            "agent_runtime_observability_and_egress_membrane",
        ],
        "target_existing_organs": [
            "agent_route_observability_runtime",
            "bridge_phase_continuity_runtime",
            "mission_transaction_work_spine",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "worker_run_fingerprint_dedup_cache_gate",
        ],
        "why_impressive": (
            "Provider dispatch becomes reusable only when repeated worker runs route through "
            "a content-addressed idempotency membrane: provider_id, model_id, cache_key, "
            "prompt_hash, cache_hit receipts, failed-status run fingerprints, blocked_"
            "duplicate receipts, running-run collision handling, and explicit force bypass "
            "travel together instead of being rediscovered from transform jobs, receipts, "
            "or provider-call counters."
        ),
        "candidate_fixture": (
            "Synthetic worker fixture with one successful job run, a second identical job "
            "returning cache_hit with no provider call, one schema_fail run that writes a "
            "failed run_fingerprint, a duplicate failed run that emits blocked_duplicate "
            "without provider call, and a force rerun that bypasses the cache/fingerprint "
            "gates while preserving receipt lineage."
        ),
        "anti_claim_floor": (
            "This route proves internal worker idempotency and cache/duplicate suppression "
            "for synthetic fixtures and live owner surfaces. It does not call live providers, "
            "certify provider output as true, publish private receipt payloads, provide a "
            "distributed lock, promote row patches, mutate source, authorize paid spend, "
            "override transform-job, receipt, selector, liveness, reducer, governor, queue, "
            "Work Ledger, Task Ledger, scoped commit, seed heartbeat, privacy, stop, or "
            "proof gates."
        ),
        "next_refinement_move": (
            "Keep worker_run_fingerprint_dedup_cache_gate as the idempotent dispatch owner "
            "around type_a_worker_harness.py FAILED_STATUSES, _fingerprint_path, _cache_path, "
            "run_transform_job, cache_hit and blocked_duplicate receipts, run_fingerprint and "
            "cache artifacts, std_transform_job retry/storage/status contracts, and focused "
            "worker tests. Future provider-plane work should open this route with transform_"
            "job_provenance, compute_worker_receipts_provider_provenance, provider_plane_"
            "finite_pull_row_job, provider_metabolism_ledger, provider_candidate_selector_"
            "snapshot, provider_plane_finite_pull_liveness, and type_a_reducer_row_patch_"
            "review_gate before claiming cache hits, duplicate blocking, force reruns, "
            "provider call counts, or rate-limit protection."
        ),
    },
    {
        "route_id": "annex_distillation_anti_corruption_boundary_adapter_contract",
        "priority_rank": 20,
        "source_cluster_ids": [
            "external_reference_transfer",
            "standard_owned_option_surfaces",
            "agent_runtime_observability_and_egress_membrane",
            "mission_transaction_and_scoped_commit",
        ],
        "target_existing_organs": [
            "external_boundary_anti_corruption_runtime",
            "agent_route_observability_runtime",
            "mission_transaction_work_spine",
            "proof_diagnostic_evidence_spine",
            "navigation_hologram_route_plane",
        ],
        "pattern_ids": [
            "annex_distillation_anti_corruption_boundary",
        ],
        "why_impressive": (
            "External reference transfer becomes reusable only when annex patterns route "
            "through a classified anti-corruption boundary: pattern transfer, upgrade-ours, "
            "hybrid wrap, adapter, defer, reject, archive, and substrate-wedge mappings "
            "travel with source loci, local targets, trust-default controller merge, "
            "standard-transfer fields, rejection/defer triggers, and public projection "
            "anti-claims instead of silently importing foreign semantics."
        ),
        "candidate_fixture": (
            "Synthetic annex distillation fixture with eight external pattern rows covering "
            "lanes 1-5 plus D6 mapping notes: pattern_transfer, upgrade_ours, hybrid_wrap, "
            "anti_corruption_adapter, defer, reject, archive, and substrate_wedge reference. "
            "Assertions cover source_locus/local_target requirements, controller-clean rows "
            "promoted to evaluated, lane 5 rejected with rejection_reason and reevaluation_"
            "trigger, deferred rows with reevaluation_trigger, standard-transfer fields, "
            "notes cross-refs, projection index grouping, and no public standalone leaf."
        ),
        "anti_claim_floor": (
            "This route proves annex distillation classification and external-pattern "
            "anti-corruption boundaries for synthetic fixtures and live owner surfaces. It "
            "does not copy external projects into doctrine, claim upstream truth, publish "
            "private annex payloads, promote annex rows to public release authority, make "
            "lane 6 a distillation-row enum, bypass controller merge, mutate source, or "
            "override Work Ledger, Task Ledger, scoped commit, seed heartbeat, privacy, "
            "stop, or proof gates."
        ),
        "next_refinement_move": (
            "Keep annex_distillation_anti_corruption_boundary as the external-reference "
            "adapter owner around annex_import.py, annex_registry.py, std_annex_"
            "distillation, std_annex_notes, annex paper modules, annex distillation index, "
            "standard-transfer row validation, route_annexes, Work Ledger claims, scoped "
            "commit, and focused annex tests. Future Microcosm import work should open "
            "this route with codex_annex_substrate, microcosm_substrate, bridge_runtime, "
            "claude_subagent_delegation, public_microcosm_evolution_seed, and route-"
            "readiness overlays before claiming external pattern transfer, adaptation, "
            "rejection, archive, substrate wedge, or public projection authority."
        ),
    },
    {
        "route_id": "provider_candidate_selector_snapshot_scorecard_contract",
        "priority_rank": 19,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "bridge_continuity_runtime",
            "mission_transaction_and_scoped_commit",
            "agent_runtime_observability_and_egress_membrane",
        ],
        "target_existing_organs": [
            "agent_route_observability_runtime",
            "bridge_phase_continuity_runtime",
            "mission_transaction_work_spine",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "provider_candidate_selector_snapshot",
        ],
        "why_impressive": (
            "The provider selector becomes reusable when row-job candidates, governor "
            "dispatch gates, provider runtime pressure, historical receipt scorecards, "
            "stale source fingerprints, OpenRouter free hard vetoes, idle explanations, "
            "Work Ledger claims, and proof receipts route as one read-only claimability "
            "contract instead of being rediscovered inside scheduler and provider signal "
            "code."
        ),
        "candidate_fixture": (
            "Synthetic selector snapshot with three candidates from two providers: one "
            "provider scorecard with schema failures demotes a row, one stale receipt "
            "blocks promotion after source-fingerprint drift, one governor or CPU local-cost "
            "gate suppresses a row, one OpenRouter paid-spend case is hard-vetoed, and "
            "one empty queue returns a precise why_nothing_ran idle reason."
        ),
        "anti_claim_floor": (
            "This route proves internal provider-candidate claimability explanation for "
            "synthetic fixtures and live owner surfaces. It does not call providers, "
            "dispatch work, claim slots, enqueue daemon jobs, mutate source, promote row "
            "patches, authorize paid spend, override governor or queue contracts, or "
            "bypass Work Ledger, Task Ledger, scoped commit, seed heartbeat, privacy, "
            "stop, or proof gates."
        ),
        "next_refinement_move": (
            "Keep provider_candidate_selector_snapshot as the read-only selector and "
            "scorecard evidence contract around provider_metabolism_signal.py, "
            "metabolism_scheduler.py, metabolism_row_jobs.py, metabolism_governor.py, "
            "provider receipts, stale-source fingerprints, no-paid-auto posture, and "
            "focused selector tests. Future agents should open this option-surface card, "
            "provider_plane_finite_pull_liveness, meta_mission_queue_runtime, "
            "governor_mode_dispatch_state_machine, std_provider_adapter, "
            "std_metabolism_status, std_launchable_operation_contract, provider signal "
            "tests, scheduler tests, and route-readiness overlays before claiming provider "
            "selection, liveness, queue consumption, or dispatch behavior."
        ),
    },
    {
        "route_id": "provider_plane_finite_pull_liveness_daemon_guard_contract",
        "priority_rank": 20,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "bridge_continuity_runtime",
            "mission_transaction_and_scoped_commit",
            "agent_runtime_observability_and_egress_membrane",
        ],
        "target_existing_organs": [
            "agent_route_observability_runtime",
            "bridge_phase_continuity_runtime",
            "mission_transaction_work_spine",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "provider_plane_finite_pull_liveness",
        ],
        "why_impressive": (
            "The provider plane becomes governable when transform jobs, provider receipts, "
            "draft row patches, row-patch reviews, dormant lanes, backpressured lanes, "
            "queue counts, provider-plane pulse lines, and finite-pull safety invariants "
            "route as one read-only liveness contract instead of being rediscovered as a "
            "daemon, selector, queue, or row-patch promotion behavior."
        ),
        "candidate_fixture": (
            "Synthetic provider-plane fixture with queued transform jobs, successful and "
            "timed-out receipts, one lane with no successful receipt, reviewed and "
            "unreviewed row patches, a stale provider application discovery lane, and a "
            "provider-plane pulse render; assertions cover exact queue counts, dormant "
            "lane reasons, backpressure, recommended read-only actions, and safety fields "
            "for daemon disabled, finite_pull_triggered_batches, provider_endpoint ceiling, "
            "free-only budget, and Type A promotion only."
        ),
        "anti_claim_floor": (
            "This route proves internal read-only provider-plane liveness and finite-pull "
            "safety for synthetic fixtures and live owner surfaces. It does not call "
            "providers, run a daemon, dispatch work, claim slots, promote row patches, "
            "mutate source, authorize paid spend, override selector, governor, queue, or "
            "reducer contracts, or bypass Work Ledger, Task Ledger, scoped commit, seed "
            "heartbeat, privacy, stop, or proof gates."
        ),
        "next_refinement_move": (
            "Keep provider_plane_finite_pull_liveness as the daemon-guarded liveness "
            "contract around provider_plane_liveness.py, provider_plane_application_catalog.py, "
            "provider_row_patch_review.py, transform jobs, receipts, row patches, reviews, "
            "pulse cache, provider standards, and focused liveness tests. Future agents "
            "should open this option-surface card, provider_candidate_selector_snapshot, "
            "type_a_reducer_row_patch_review_gate, std_provider_adapter, std_compute_provider, "
            "std_transform_job, std_metabolism_status, the provider-plane liveness command, "
            "focused tests, and route-readiness overlays before claiming provider liveness, "
            "row-patch backlog, provider dispatch, or queue consumption behavior."
        ),
    },
    {
        "route_id": "type_a_reducer_row_patch_review_gate_evaluator_contract",
        "priority_rank": 21,
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "bridge_continuity_runtime",
            "mission_transaction_and_scoped_commit",
            "agent_runtime_observability_and_egress_membrane",
        ],
        "target_existing_organs": [
            "agent_route_observability_runtime",
            "bridge_phase_continuity_runtime",
            "mission_transaction_work_spine",
            "proof_diagnostic_evidence_spine",
            "external_boundary_anti_corruption_runtime",
        ],
        "pattern_ids": [
            "type_a_reducer_row_patch_review_gate",
        ],
        "why_impressive": (
            "Provider row-patch output becomes governable only when Type A reducer "
            "decisions are immutable, typed, machine-readable review sidecars. This "
            "contract routes accept_as_advisory_signal, reject, retry, bridge_escalate, "
            "and record_no_op decisions, summary counts, invalid-ref handling, and "
            "promotion-boundary evidence as one evaluator gate instead of letting "
            "provider output self-promote from prose or raw patch existence."
        ),
        "candidate_fixture": (
            "Synthetic row-patch review set with one patch for each typed outcome, one "
            "newer duplicate review proving latest-by-patch wins, one unknown patch id "
            "ignored by summary, and one unreviewed draft row patch visible through "
            "provider-plane liveness. Assertions cover 7d outcome counts, accepted "
            "advisory count, rejected/retry/bridge escalation counts, invalid-ref "
            "count, and the promotion_boundary string on every review record."
        ),
        "anti_claim_floor": (
            "This route proves internal Type A reducer review state and aggregation for "
            "synthetic fixtures and live owner surfaces. It does not call providers, "
            "promote row patches, mutate source, certify provider output as true, "
            "authorize paid spend, override selector, liveness, governor, queue, or "
            "apply-lane contracts, or bypass Work Ledger, Task Ledger, scoped commit, "
            "seed heartbeat, privacy, stop, or proof gates."
        ),
        "next_refinement_move": (
            "Keep type_a_reducer_row_patch_review_gate as the evaluator authority boundary "
            "around provider_row_patch_review.py, row_patch_reviews sidecars, transform "
            "jobs, provider receipts, row-patch option surfaces, provider-plane liveness, "
            "std_transform_job, std_compute_provider, and focused provider-plane tests. "
            "Future agents should open this option-surface card, provider_plane_finite_pull_"
            "liveness, provider_candidate_selector_snapshot, the provider standards, "
            "row_patches cluster/card surfaces, and route-readiness overlays before "
            "claiming advisory promotion, review backlog, liveness, dispatch, or queue "
            "consumption behavior."
        ),
    },
]

FRONTIER_COMBINATION_ROUTE_DEFS: list[dict[str, Any]] = [
    {
        "route_id": "agent_safety_replay_gauntlet",
        "priority_rank": 1,
        "combination_kind": "frontier_backlog",
        "source_cluster_ids": [],
        "target_existing_organs": [
            "external_boundary_anti_corruption_runtime",
            "agent_route_observability_runtime",
            "proof_diagnostic_evidence_spine",
        ],
        "prerequisite_route_ids": [
            "agent_trace_to_route_repair_observability",
            "operator_handoff_attention_membrane",
        ],
        "pattern_ids": [
            "agent_benchmark_integrity_anti_gaming_replay_compound",
            "agent_monitor_redteam_falsification_replay_compound",
            "agent_sabotage_scheming_monitor_replay_compound",
            "agent_sandbox_policy_escape_replay_compound",
            "mcp_tool_authority_replay_compound",
            "indirect_prompt_injection_information_flow_policy_replay_compound",
            "agent_memory_temporal_conflict_replay_compound",
            "sleeper_memory_poisoning_quarantine_replay_compound",
        ],
        "public_attention_fit": (
            "Agent capability is now bottlenecked by reliability, monitoring, tool authority, "
            "memory integrity, and benchmark gaming rather than simple task completion."
        ),
        "why_impressive": (
            "A single public-safe replay suite can show adversarial agent behavior, tool-call "
            "authority, prompt-injection taint, sandbox escape attempts, memory poisoning, and "
            "benchmark anti-gaming as typed evidence rather than anecdotes."
        ),
        "candidate_fixture": (
            "Synthetic multi-episode red-team fixture with locked and mutable evaluators, fake "
            "secrets, untrusted tool outputs, memory-write quarantine, monitor verdicts, tool "
            "capability manifests, and replay receipts for pass/fail and false-negative cases."
        ),
        "anti_claim_floor": (
            "This route proves replay instrumentation and containment checks for synthetic "
            "episodes; it does not claim complete security, real-user memory safety, or live "
            "frontier-model alignment."
        ),
        "next_refinement_move": (
            "Add detailed bindings for the replay-compound rows, then make one synthetic "
            "gauntlet manifest that requires monitor, memory, tool-authority, and sandbox "
            "receipts before any pass label is displayed."
        ),
    },
    {
        "route_id": "repository_agent_benchmark_transaction_lab",
        "priority_rank": 2,
        "combination_kind": "frontier_backlog",
        "source_cluster_ids": [],
        "target_existing_organs": [
            "mission_transaction_work_spine",
            "agent_route_observability_runtime",
            "external_boundary_anti_corruption_runtime",
        ],
        "prerequisite_route_ids": [
            "mission_transaction_runtime_work_spine",
            "agent_trace_to_route_repair_observability",
        ],
        "pattern_ids": [
            "repository_issue_patch_oracle_diff_replay_compound",
            "ci_evolution_skill_regression_replay_compound",
            "durable_agent_work_landing_replay_compound",
            "proof_derived_governed_mutation_authorization_compound",
            "workitem_write_admission_gate",
            "workitem_contract_gap_triage_views",
            "provider_slot_claim_cooldown_backpressure",
        ],
        "public_attention_fit": (
            "Coding-agent benchmarks are under pressure to move from solved-patch scores to "
            "replayable work transactions, regression guards, and anti-gaming evidence."
        ),
        "why_impressive": (
            "The repo-agent story becomes a transaction lab: issue capsule, localization, "
            "scoped patch, oracle diff, CI evolution, workitem admission, provider backpressure, "
            "and landing receipt all compose into one auditable benchmark specimen."
        ),
        "candidate_fixture": (
            "Synthetic two-repo benchmark with one bugfix, one feature request, one misleading "
            "test, one unrelated regression guard, active work claims, provider slot pressure, "
            "scoped diff receipts, and FAIL_TO_PASS/PASS_TO_PASS-style oracle grading."
        ),
        "anti_claim_floor": (
            "The lab demonstrates benchmark transaction discipline and regression protection; "
            "it does not report SWE-bench performance or guarantee production delivery rates."
        ),
        "next_refinement_move": (
            "Bind the repo-agent replay rows to mission transaction and agent trace validators, "
            "then generate one public fixture whose score is impossible without a clean scoped "
            "patch, oracle diff, and work-landing receipt."
        ),
    },
    {
        "route_id": "world_model_projection_drift_control_room",
        "priority_rank": 3,
        "combination_kind": "frontier_backlog",
        "source_cluster_ids": [
            "standard_owned_option_surfaces",
            "agent_entry_runtime_and_behavior_governance",
            "world_model_attention_and_authority_projection",
        ],
        "target_existing_organs": [
            "navigation_hologram_route_plane",
            "agent_route_observability_runtime",
            "mission_transaction_work_spine",
        ],
        "prerequisite_route_ids": [
            "agent_trace_to_route_repair_observability",
            "mission_transaction_runtime_work_spine",
        ],
        "pattern_ids": [
            "world_model_cross_plane_drift_aggregate",
            "view_quality_all_view_action_map",
            "compression_profile_governed_option_surface",
            "navigation_hologram_unified_route_plane",
            "agent_principle_failure_cap_assimilation_loop",
            "operator_autonomy_phrase_active_standard_bridge",
            "omission_receipt_reversible_projection_boundary",
            "entry_payload_admission_nonnegotiable_floor",
        ],
        "public_attention_fit": (
            "The attention-grabbing part of a self-indexing substrate is whether agents can "
            "audit drift, route themselves, and repair their own failure modes from typed state."
        ),
        "why_impressive": (
            "A public control room can show the system's world model, projection drift, "
            "compression bands, route leases, omitted-content receipts, view-quality action "
            "maps, and principle-failure CAP assimilation as one self-repair loop."
        ),
        "candidate_fixture": (
            "Synthetic station snapshot with three drift planes, one missing control field, one "
            "route miss, one over-budget projection, one view-quality gap, and a principle-CAP "
            "assimilation receipt that routes to a skill, standard, or explicit rejection."
        ),
        "anti_claim_floor": (
            "The control room proves typed projection and repair mechanics on fixture state; it "
            "does not make generated projections source authority or expose private runtime data."
        ),
        "next_refinement_move": (
            "Turn this into the next public demo spine after route observability: each card must "
            "link to the source plane, the drift reason, the repair route, and the validator that "
            "keeps projection from becoming authority."
        ),
    },
    {
        "route_id": "formal_benchmark_integrity_replay_lab",
        "priority_rank": 4,
        "combination_kind": "frontier_backlog",
        "source_cluster_ids": [
            "formal_math_proof_organ",
            "formal_math_policy_integrity_and_search_foundry",
            "formal_prover_context_library_prior_and_strategy_gate",
        ],
        "target_existing_organs": [
            "proof_diagnostic_evidence_spine",
            "formal_prover_lab_evaluation_suborgan",
            "external_boundary_anti_corruption_runtime",
        ],
        "prerequisite_route_ids": [
            "formal_prover_context_strategy_gate",
            "formal_policy_integrity_search_foundry",
        ],
        "pattern_ids": [
            "formal_math_readiness_proof_spine_compound",
            "formal_math_verifier_trace_repair_loop_compound",
            "formal_evidence_cell_anchor_resolver",
            "undeclared_library_prior_symbol_classifier",
            "agent_benchmark_integrity_anti_gaming_replay_compound",
        ],
        "public_attention_fit": (
            "Formal theorem proving is a high-signal AI frontier, but the public proof needs "
            "readiness gates, verifier traces, benchmark integrity, and explicit library priors."
        ),
        "why_impressive": (
            "The existing Lean/proof diagnostic engine can be framed as a benchmark-integrity "
            "lab: readiness proof spine, verifier-trace repair loop, evidence-cell anchors, "
            "library-prior classifiers, and anti-gaming replay all gate any proof metric."
        ),
        "candidate_fixture": (
            "Synthetic Lean task set with one missing library prior, one verifier trace repair, "
            "one evidence-cell anchor check, one benchmark canary, and one solved/unsolved label "
            "that cannot be emitted until every gate receipt exists."
        ),
        "anti_claim_floor": (
            "This route proves formal benchmark hygiene for the fixture; it does not claim "
            "graduate-level proof performance or public leaderboard results."
        ),
        "next_refinement_move": (
            "Add detailed bindings for the two formal replay compounds and evidence-cell "
            "resolver, then fold this route into the proof diagnostic organ's public README as "
            "the benchmark-integrity section."
        ),
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError as exc:
            rows.append(
                {
                    "_invalid_jsonl": True,
                    "_line_number": line_number,
                    "_error": str(exc),
                }
            )
            continue
        if isinstance(row, dict):
            rows.append(row)
        else:
            rows.append(
                {
                    "_invalid_jsonl": True,
                    "_line_number": line_number,
                    "_error": "jsonl row is not an object",
                }
            )
    return rows


def _hash_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_manifest(repo_root: Path) -> dict[str, Any]:
    inputs = [LEDGER_REL, BINDINGS_REL, WEAK_BINDINGS_REL]
    return {
        "inputs": [
            {
                "path": rel,
                "exists": (repo_root / rel).is_file(),
                "sha256": _hash_file(repo_root / rel),
            }
            for rel in inputs
        ]
    }


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f"{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp, path)
        path.chmod(0o644)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f"{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            if not text.endswith("\n"):
                handle.write("\n")
        os.replace(tmp, path)
        path.chmod(0o644)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _finding(
    *,
    severity: str,
    rule: str,
    message: str,
    pattern_id: str | None = None,
    path: str | None = None,
    expected: Any | None = None,
    observed: Any | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "severity": severity,
        "rule": rule,
        "message": message,
    }
    if pattern_id:
        payload["pattern_id"] = pattern_id
    if path:
        payload["path"] = path
    if expected is not None:
        payload["expected"] = expected
    if observed is not None:
        payload["observed"] = observed
    return payload


def _normalize_ref(ref: str) -> str:
    value = str(ref or "").strip()
    value = re.sub(r"\s+\([^/]*\)$", "", value)
    value = value.split(" #", 1)[0].strip()
    value = value.split("::", 1)[0].strip()
    return value


def _concrete_path_candidate(ref: str) -> str | None:
    value = _normalize_ref(ref)
    if not value:
        return None
    if value.startswith("./"):
        return None
    if value.startswith(("http://", "https://")):
        return None
    if value.startswith("<") or value.endswith(">"):
        return None
    if value.startswith(
        ("standard:", "skill:", "paper_module:", "runtime_surface:", "option_surface:", "git_commit:")
    ):
        return None
    if "\n" in value:
        return None
    return value


def _path_exists(repo_root: Path, ref: str) -> bool:
    candidate = _concrete_path_candidate(ref)
    if candidate is None:
        return True
    return (repo_root / candidate).exists()


def _iter_substrate_refs(binding: Mapping[str, Any]) -> Iterable[tuple[str, str]]:
    substrate = binding.get("substrate_bindings")
    if not isinstance(substrate, Mapping):
        return
    for category, values in substrate.items():
        if isinstance(values, list):
            for value in values:
                if isinstance(value, str):
                    yield str(category), value


def _binding_refs_by_pattern_id(bindings: Mapping[str, Any]) -> dict[str, list[str]]:
    refs_by_pattern_id: dict[str, list[str]] = {}
    detailed_bindings = bindings.get("pattern_bindings")
    if not isinstance(detailed_bindings, list):
        return refs_by_pattern_id
    for binding in detailed_bindings:
        if not isinstance(binding, Mapping):
            continue
        pattern_id = str(binding.get("pattern_id") or "").strip()
        if not pattern_id:
            continue
        refs_by_pattern_id[pattern_id] = [ref for _, ref in _iter_substrate_refs(binding)]
    return refs_by_pattern_id


def _classify_ref(ref: str) -> set[str]:
    value = _normalize_ref(ref)
    classes: set[str] = set()
    if not value:
        return classes

    if value.startswith(("codex/standards/", "microcosm-substrate/standards/")):
        classes.add("standard")
    if value.startswith(("codex/doctrine/paper_modules/", "microcosm-substrate/paper_modules/")):
        classes.add("paper_module")
    if value.startswith(("codex/doctrine/skills/", ".agents/skills/")):
        classes.add("skill")
    if value.startswith(("codex/doctrine/concepts/", "codex/doctrine/mechanisms/")):
        classes.add("concept_or_mechanism")
    if value.startswith(("state/", "tools/meta/control/orchestration_", "codex/ledger/")):
        classes.add("state_or_ledger")
    if value.startswith("obsidian/"):
        classes.add("private_state")
        classes.add("state_or_ledger")
    if "raw_seed" in value or "prompt_shelf" in value or value.startswith("state/task_ledger/"):
        classes.add("private_state")
    if value.startswith(("self-indexing-cognitive-substrate/", "microcosm-substrate/")):
        classes.add("public_microcosm_artifact")
    if value.startswith("formal_math/") or (
        value.startswith("microcosm-substrate/fixtures/") and value.endswith(".lean")
    ):
        classes.add("formal_proof")
        classes.add("test_validator_receipt_or_proof")
    if (
        value == "kernel.py"
        or value == "annex_import.py"
        or value == "checkpoint"
        or value.startswith(("./repo-python ", "./repo-pytest ", "./checkpoint", "python3 kernel.py"))
        or " --option-surface " in value
        or " --row " in value
        or " --context-pack " in value
        or value.endswith(".py")
        or value.startswith(("system/lib/", "system/control/", "tools/", ".claude/hooks/"))
    ):
        classes.add("code_owner_or_command")
    if "/tests/" in value or Path(value).name.startswith("test_"):
        classes.add("test_validator_receipt_or_proof")
    if any(token in value for token in ("validation_report", "route_coverage", "receipt", "manifest")):
        classes.add("generated_artifact_or_receipt")
    if value.endswith((".json", ".jsonl")):
        classes.add("structured_artifact")
    return classes


def _row_evidence_profile(row: Mapping[str, Any], binding_refs: Iterable[str] | None = None) -> dict[str, Any]:
    source_refs = [str(ref) for ref in row.get("source_refs", []) if isinstance(ref, str)]
    detailed_refs = [str(ref) for ref in (binding_refs or []) if isinstance(ref, str)]
    refs = list(dict.fromkeys([*source_refs, *detailed_refs]))
    class_counts: Counter[str] = Counter()
    for ref in refs:
        class_counts.update(_classify_ref(ref))
    private_state_risk = str(row.get("private_state_risk") or "").strip()
    novelty_band = str(row.get("novelty_band") or "").strip()

    has_standard = class_counts["standard"] > 0
    has_paper = class_counts["paper_module"] > 0
    has_high_authority = any(
        class_counts[name] > 0
        for name in (
            "code_owner_or_command",
            "test_validator_receipt_or_proof",
            "generated_artifact_or_receipt",
            "state_or_ledger",
            "formal_proof",
            "structured_artifact",
        )
    )
    grounding_classes: list[str] = []
    if has_standard and has_paper and has_high_authority:
        grounding_classes.append("strong_high_authority")
    if (class_counts["paper_module"] or class_counts["skill"]) and not has_standard and not has_high_authority:
        grounding_classes.append("doctrine_only")
    if has_high_authority and not has_standard:
        grounding_classes.append("code_or_state_no_standard")
    if has_high_authority and not has_paper:
        grounding_classes.append("code_or_state_no_paper_module")
    if has_standard and not has_high_authority:
        grounding_classes.append("standard_no_code_validator_or_state")
    if len(refs) <= 2:
        grounding_classes.append("weak_ref_count_lte_2")
    if private_state_risk in {"medium", "high"} or class_counts["private_state"] > 0:
        grounding_classes.append("private_fixture_needed")
    if private_state_risk in {"none", "low"} and novelty_band in {"medium", "high"}:
        grounding_classes.append("public_projection_candidate_by_risk_and_novelty")

    return {
        "pattern_id": row.get("pattern_id"),
        "source_ref_count": len(source_refs),
        "detailed_binding_ref_count": len(detailed_refs),
        "effective_ref_count": len(refs),
        "evidence_class_counts": dict(sorted(class_counts.items())),
        "grounding_classes": grounding_classes,
        "has_standard": has_standard,
        "has_paper_module": has_paper,
        "has_high_authority_evidence": has_high_authority,
        "private_state_risk": private_state_risk,
        "novelty_band": novelty_band,
    }


def _sorted_counter_dict(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(((str(key), int(value)) for key, value in counter.items()), key=lambda item: (-item[1], item[0])))


def _field_counter(rows: Iterable[Mapping[str, Any]], field: str, fallback: str = "unknown") -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        value = str(row.get(field) or fallback)
        counter[value] += 1
    return _sorted_counter_dict(counter)


def _coverage_summary_from_rows(rows: list[Mapping[str, Any]], profiles: list[Mapping[str, Any]]) -> dict[str, Any]:
    grounding_class_counts: Counter[str] = Counter()
    for profile in profiles:
        grounding_class_counts.update(str(class_id) for class_id in profile.get("grounding_classes", []))
    grounding_counts = {class_id: int(grounding_class_counts.get(class_id) or 0) for class_id in GROUNDING_CLASS_ORDER}
    return {
        "rows": len(rows),
        "families": _field_counter(rows, "organ_family"),
        "current_microcosm_status": _field_counter(rows, "current_microcosm_status"),
        "private_state_risk": _field_counter(rows, "private_state_risk"),
        "novelty_band": _field_counter(rows, "novelty_band"),
        "grounding_class_counts": grounding_counts,
        "note": "Grounding classes overlap; counts are diagnostic routing aids, not mutually exclusive statuses.",
    }


def _strong_pattern_ids(profiles: Iterable[Mapping[str, Any]]) -> list[str]:
    return sorted(
        str(profile.get("pattern_id"))
        for profile in profiles
        if profile.get("pattern_id") and "strong_high_authority" in profile.get("grounding_classes", [])
    )


def _detailed_binding_ids(bindings: Mapping[str, Any]) -> set[str]:
    ids: set[str] = set()
    detailed_bindings = bindings.get("pattern_bindings")
    if not isinstance(detailed_bindings, list):
        return ids
    for binding in detailed_bindings:
        if isinstance(binding, Mapping) and binding.get("pattern_id"):
            ids.add(str(binding["pattern_id"]))
    return ids


def _cluster_roots_by_id(bindings: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    clusters: dict[str, Mapping[str, Any]] = {}
    cluster_roots = bindings.get("load_bearing_cluster_roots")
    if not isinstance(cluster_roots, list):
        return clusters
    for cluster in cluster_roots:
        if isinstance(cluster, Mapping) and cluster.get("cluster_id"):
            clusters[str(cluster["cluster_id"])] = cluster
    return clusters


def _build_combination_routes(
    rows: list[Mapping[str, Any]],
    bindings: Mapping[str, Any],
    profiles: list[Mapping[str, Any]],
    route_defs: Sequence[Mapping[str, Any]],
    *,
    selection_boundary: str,
) -> list[dict[str, Any]]:
    row_by_id = {
        str(row.get("pattern_id")): row
        for row in rows
        if row.get("pattern_id")
    }
    profile_by_id = {
        str(profile.get("pattern_id")): profile
        for profile in profiles
        if profile.get("pattern_id")
    }
    detailed_ids = _detailed_binding_ids(bindings)
    cluster_by_id = _cluster_roots_by_id(bindings)
    routes: list[dict[str, Any]] = []

    for route_def in route_defs:
        pattern_ids = [
            str(pattern_id)
            for pattern_id in route_def.get("pattern_ids", [])
            if isinstance(pattern_id, str) and pattern_id
        ]
        available_ids = [pattern_id for pattern_id in pattern_ids if pattern_id in row_by_id]
        if not available_ids:
            continue

        source_cluster_ids = [
            str(cluster_id)
            for cluster_id in route_def.get("source_cluster_ids", [])
            if isinstance(cluster_id, str) and cluster_id
        ]
        cluster_supported_ids: set[str] = set()
        cluster_refs: list[str] = []
        for cluster_id in source_cluster_ids:
            cluster = cluster_by_id.get(cluster_id)
            if not cluster:
                continue
            supports = cluster.get("supports_pattern_ids")
            if isinstance(supports, list):
                cluster_supported_ids.update(str(pattern_id) for pattern_id in supports if isinstance(pattern_id, str))
            refs = cluster.get("substrate_refs")
            if isinstance(refs, list):
                cluster_refs.extend(str(ref) for ref in refs if isinstance(ref, str))
        cluster_refs = list(dict.fromkeys(cluster_refs))

        rows_for_route = [row_by_id[pattern_id] for pattern_id in available_ids]
        row_refs: list[str] = []
        for row in rows_for_route:
            refs = row.get("source_refs")
            if isinstance(refs, list):
                row_refs.extend(str(ref) for ref in refs if isinstance(ref, str))
        substrate_refs = list(dict.fromkeys([*cluster_refs, *row_refs]))
        profiles_for_route = [
            profile_by_id[pattern_id]
            for pattern_id in available_ids
            if pattern_id in profile_by_id
        ]
        grounding_counts: Counter[str] = Counter()
        for profile in profiles_for_route:
            grounding_counts.update(str(class_id) for class_id in profile.get("grounding_classes", []))
        detailed_present = [pattern_id for pattern_id in available_ids if pattern_id in detailed_ids]

        routes.append(
            {
                "route_id": route_def["route_id"],
                "priority_rank": route_def["priority_rank"],
                "selection_boundary": selection_boundary,
                "source_cluster_ids": source_cluster_ids,
                "target_existing_organs": [
                    str(organ_id)
                    for organ_id in route_def.get("target_existing_organs", [])
                    if isinstance(organ_id, str) and organ_id
                ],
                "available_pattern_ids": available_ids,
                "missing_pattern_ids": [pattern_id for pattern_id in pattern_ids if pattern_id not in row_by_id],
                "cluster_supported_pattern_ids": [
                    pattern_id for pattern_id in available_ids if pattern_id in cluster_supported_ids
                ],
                "detailed_binding_pattern_ids": detailed_present,
                "missing_detailed_binding_pattern_ids": [
                    pattern_id for pattern_id in available_ids if pattern_id not in detailed_ids
                ],
                "ledger_slice": {
                    "available_pattern_count": len(available_ids),
                    "status_counts": _field_counter(rows_for_route, "current_microcosm_status"),
                    "novelty_band_counts": _field_counter(rows_for_route, "novelty_band"),
                    "private_state_risk_counts": _field_counter(rows_for_route, "private_state_risk"),
                    "organ_family_counts": _field_counter(rows_for_route, "organ_family"),
                    "strong_high_authority_count": int(
                        grounding_counts.get("strong_high_authority") or 0
                    ),
                    "public_projection_candidate_count": int(
                        grounding_counts.get("public_projection_candidate_by_risk_and_novelty") or 0
                    ),
                },
                "substrate_ref_sample": substrate_refs[:16],
                "substrate_refs_omitted_count": max(0, len(substrate_refs) - 16),
                "why_impressive": route_def["why_impressive"],
                "candidate_fixture": route_def["candidate_fixture"],
                "anti_claim_floor": route_def["anti_claim_floor"],
                "next_refinement_move": route_def["next_refinement_move"],
            }
        )
        for optional_field in (
            "combination_kind",
            "public_attention_fit",
            "prerequisite_route_ids",
            "pattern_interlocks",
        ):
            if optional_field in route_def:
                routes[-1][optional_field] = route_def[optional_field]

    def _route_priority(route: Mapping[str, Any]) -> int:
        value = route.get("priority_rank")
        return int(value) if value is not None else 999

    return sorted(routes, key=_route_priority)


def _build_foundation_combination_routes(
    rows: list[Mapping[str, Any]],
    bindings: Mapping[str, Any],
    profiles: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return _build_combination_routes(
        rows,
        bindings,
        profiles,
        FOUNDATION_COMBINATION_ROUTE_DEFS,
        selection_boundary="local_combination_priority_only_not_artifact_selection",
    )


def _build_frontier_combination_routes(
    rows: list[Mapping[str, Any]],
    bindings: Mapping[str, Any],
    profiles: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return _build_combination_routes(
        rows,
        bindings,
        profiles,
        FRONTIER_COMBINATION_ROUTE_DEFS,
        selection_boundary="frontier_backlog_priority_only_not_artifact_selection",
    )


def _load_pattern_binding_inputs(repo_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    rows = [row for row in _read_jsonl(repo_root / LEDGER_REL) if not row.get("_invalid_jsonl")]
    bindings = _load_json_sidecar(repo_root, BINDINGS_REL, findings)
    weak_bindings = _load_json_sidecar(repo_root, WEAK_BINDINGS_REL, findings)
    return rows, bindings, weak_bindings, findings


def _class_text(existing_weak_bindings: Mapping[str, Any], class_id: str, field: str) -> str:
    classes = existing_weak_bindings.get("weakness_classes")
    if isinstance(classes, list):
        for weak_class in classes:
            if isinstance(weak_class, Mapping) and weak_class.get("class_id") == class_id:
                value = str(weak_class.get(field) or "").strip()
                if value:
                    return value
    return WEAK_CLASS_DEFAULTS[class_id][field]


def build_refreshed_binding_sidecar(repo_root: Path) -> dict[str, Any]:
    rows, bindings, _weak_bindings, _findings = _load_pattern_binding_inputs(repo_root)
    binding_refs = _binding_refs_by_pattern_id(bindings)
    profiles = [
        _row_evidence_profile(row, binding_refs.get(str(row.get("pattern_id") or "")))
        for row in rows
    ]
    payload = dict(bindings)
    payload.pop("flag" "ship_combination_routes", None)
    payload.setdefault("artifact_role", "macro_pattern_substrate_binding_sidecar")
    payload["schema_version"] = EXPECTED_BINDING_SCHEMA
    binding_contract = payload.get("binding_contract")
    if not isinstance(binding_contract, dict):
        binding_contract = {}
    binding_contract["governing_standard"] = GOVERNING_STANDARD_REL
    payload["binding_contract"] = binding_contract
    payload["source_ledger"] = LEDGER_REL
    payload["source_row_count"] = len(rows)
    payload["last_refreshed_at"] = _utc_now()
    payload["coverage_summary"] = _coverage_summary_from_rows(rows, profiles)
    payload["strong_high_authority_pattern_ids"] = _strong_pattern_ids(profiles)
    payload["foundation_combination_routes"] = _build_foundation_combination_routes(
        rows,
        payload,
        profiles,
    )
    payload["frontier_combination_routes"] = _build_frontier_combination_routes(
        rows,
        payload,
        profiles,
    )

    existing_next = payload.get("next_type_a_pass") if isinstance(payload.get("next_type_a_pass"), Mapping) else {}
    payload["next_type_a_pass"] = {
        "primary_move": (
            "Keep concrete source refs validator-green, then refine the foundation route bundles "
            "before implementing any isolated pattern row."
        ),
        "source_coupled_refresh": {
            "current_ledger_row_count": len(rows),
            "detailed_binding_count": len(payload.get("pattern_bindings") or []),
            "foundation_combination_route_count": len(payload["foundation_combination_routes"]),
            "frontier_combination_route_count": len(payload["frontier_combination_routes"]),
            "coverage_owner": "tools/meta/factory/build_extracted_pattern_substrate_bindings.py --write-sidecars",
        },
        "suggested_owned_paths": [
            BINDINGS_REL,
            WEAK_BINDINGS_REL,
            VALIDATION_REPORT_REL,
            COVERAGE_REPORT_REL,
        ],
        "do_not_do": list(
            existing_next.get("do_not_do")
            if isinstance(existing_next.get("do_not_do"), list)
            else [
                "Do not rebuild self-indexing-cognitive-substrate from this pass.",
                "Do not treat current public microcosm leaves as authority.",
                "Do not publish raw seed, Task Ledger, live provider, prompt shelf, or cockpit state.",
            ]
        ),
    }
    return payload


def build_refreshed_weak_binding_sidecar(repo_root: Path) -> dict[str, Any]:
    rows, _bindings, weak_bindings, _findings = _load_pattern_binding_inputs(repo_root)
    binding_refs = _binding_refs_by_pattern_id(_bindings)
    profiles = [
        _row_evidence_profile(row, binding_refs.get(str(row.get("pattern_id") or "")))
        for row in rows
    ]
    payload = dict(weak_bindings)
    payload["schema_version"] = EXPECTED_WEAK_SCHEMA
    payload["source_ledger"] = LEDGER_REL
    payload["source_row_count"] = len(rows)
    payload["last_refreshed_at"] = _utc_now()
    payload["coverage_summary"] = _coverage_summary_from_rows(rows, profiles)

    ids_by_class: dict[str, list[str]] = {class_id: [] for class_id in WEAK_CLASS_DEFAULTS}
    for profile in profiles:
        pattern_id = str(profile.get("pattern_id") or "").strip()
        if not pattern_id:
            continue
        for class_id in profile.get("grounding_classes", []):
            if class_id in ids_by_class:
                ids_by_class[class_id].append(pattern_id)

    weakness_classes: list[dict[str, Any]] = []
    for class_id in WEAK_CLASS_DEFAULTS:
        ids = sorted(ids_by_class[class_id])
        entry: dict[str, Any] = {
            "class_id": class_id,
            "count": len(ids),
            "why_weak": _class_text(weak_bindings, class_id, "why_weak"),
            "repair_rule": _class_text(weak_bindings, class_id, "repair_rule"),
            "sample_pattern_ids": ids[:12],
            "full_pattern_ids": ids,
        }
        if len(ids) <= 12:
            entry["pattern_ids"] = ids
        weakness_classes.append(entry)
    payload["weakness_classes"] = weakness_classes
    return payload


def build_coverage_report_markdown(
    report: Mapping[str, Any],
    binding_sidecar: Mapping[str, Any],
    weak_sidecar: Mapping[str, Any],
) -> str:
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    coverage = report.get("coverage_projection") if isinstance(report.get("coverage_projection"), Mapping) else {}
    grounding = coverage.get("grounding_class_counts") if isinstance(coverage.get("grounding_class_counts"), Mapping) else {}
    weak_classes = weak_sidecar.get("weakness_classes") if isinstance(weak_sidecar.get("weakness_classes"), list) else []
    cluster_roots = binding_sidecar.get("load_bearing_cluster_roots") if isinstance(binding_sidecar.get("load_bearing_cluster_roots"), list) else []
    foundation_routes = binding_sidecar.get("foundation_combination_routes") if isinstance(binding_sidecar.get("foundation_combination_routes"), list) else []
    frontier_routes = binding_sidecar.get("frontier_combination_routes") if isinstance(binding_sidecar.get("frontier_combination_routes"), list) else []
    strong_ids = coverage.get("strong_high_authority_pattern_ids") if isinstance(coverage.get("strong_high_authority_pattern_ids"), list) else []
    macro_ids = coverage.get("macro_only_candidates") if isinstance(coverage.get("macro_only_candidates"), list) else []
    safe_sample = coverage.get("safe_public_projection_candidate_sample") if isinstance(coverage.get("safe_public_projection_candidate_sample"), list) else []

    weak_lines = []
    for weak_class in weak_classes:
        if not isinstance(weak_class, Mapping):
            continue
        weak_lines.append(f"- `{weak_class.get('class_id')}`: {weak_class.get('count')} rows.")

    cluster_lines = []
    for cluster in cluster_roots[:12]:
        if not isinstance(cluster, Mapping):
            continue
        refs = cluster.get("substrate_refs") if isinstance(cluster.get("substrate_refs"), list) else []
        supports = cluster.get("supports_pattern_ids") if isinstance(cluster.get("supports_pattern_ids"), list) else []
        cluster_lines.append(
            f"- `{cluster.get('cluster_id')}`: supports {len(supports)} pattern rows with {len(refs)} substrate refs."
        )

    foundation_lines = []
    for route in foundation_routes[:8]:
        if not isinstance(route, Mapping):
            continue
        ledger_slice = route.get("ledger_slice") if isinstance(route.get("ledger_slice"), Mapping) else {}
        organs = route.get("target_existing_organs") if isinstance(route.get("target_existing_organs"), list) else []
        foundation_lines.append(
            f"- `{route.get('route_id')}`: {ledger_slice.get('available_pattern_count', 0)} local rows -> "
            f"{', '.join(str(organ) for organ in organs) or 'unrouted'}."
        )

    frontier_lines = []
    for route in frontier_routes[:8]:
        if not isinstance(route, Mapping):
            continue
        ledger_slice = route.get("ledger_slice") if isinstance(route.get("ledger_slice"), Mapping) else {}
        organs = route.get("target_existing_organs") if isinstance(route.get("target_existing_organs"), list) else []
        frontier_lines.append(
            f"- `{route.get('route_id')}`: {ledger_slice.get('available_pattern_count', 0)} local rows -> "
            f"{', '.join(str(organ) for organ in organs) or 'unrouted'}."
        )

    missing_refs = report.get("missing_concrete_source_refs") if isinstance(report.get("missing_concrete_source_refs"), list) else []
    missing_ref_lines = [
        f"- `{item.get('pattern_id')}` -> `{item.get('path')}`"
        for item in missing_refs[:12]
        if isinstance(item, Mapping)
    ]

    missing_ref_count = int(summary.get("missing_concrete_ref_count") or 0)
    next_pass_sentence = (
        "Repair the missing concrete refs, then add detailed bindings for the highest-authority rows "
        "that still lack exact substrate bindings, fixture strategy, and anti-claim entries."
        if missing_ref_count
        else "The concrete-ref validator is green. Add detailed bindings for the highest-authority rows "
        "that still lack exact substrate bindings, fixture strategy, and anti-claim entries."
    )

    lines = [
        "# Extracted Pattern Substrate Coverage Report",
        "",
        f"Generated: {_utc_now()}",
        "Scope: macro side only (`state/microcosm_portfolio/`). This report does not rebuild `self-indexing-cognitive-substrate/` and does not treat the current public leaf set as authority.",
        "",
        "## What Changed",
        "",
        "This projection is now source-coupled to the extracted pattern ledger through `tools/meta/factory/build_extracted_pattern_substrate_bindings.py --write-sidecars`.",
        "",
        "- `extracted_pattern_substrate_bindings.json` preserves curated detailed bindings and recomputes ledger-wide coverage.",
        "- `extracted_pattern_weak_bindings.json` recomputes weak-class membership from live `source_refs` plus curated detailed `substrate_bindings` refs.",
        "- `extracted_pattern_substrate_validation_report.json` validates source counts, detailed binding contracts, missing concrete refs, and cluster roots.",
        "",
        "## Coverage Snapshot",
        "",
        f"The ledger currently has {summary.get('ledger_row_count')} rows. The detailed binding map covers {summary.get('detailed_binding_count')} rows; {summary.get('ledger_ids_without_detailed_binding_count')} rows still lack detailed binding entries.",
        "",
        "High-level counts:",
        "",
        f"- {grounding.get('strong_high_authority', 0)} rows are strongly grounded by the heuristic `standard + paper module + at least one higher-authority substrate class`.",
        f"- {grounding.get('doctrine_only', 0)} rows are doctrine-only.",
        f"- {grounding.get('code_or_state_no_standard', 0)} rows have code, state, proof, or command evidence but no standard binding.",
        f"- {grounding.get('code_or_state_no_paper_module', 0)} rows have code, state, proof, command, validator, receipt, or structured evidence but no paper-module binding.",
        f"- {grounding.get('standard_no_code_validator_or_state', 0)} rows cite standards but do not cite code, validator/proof, runtime state, or receipt refs in the row.",
        f"- {grounding.get('weak_ref_count_lte_2', 0)} rows have two or fewer `source_refs`.",
        f"- {grounding.get('private_fixture_needed', 0)} rows need synthetic fixtures before any public projection.",
        f"- {grounding.get('public_projection_candidate_by_risk_and_novelty', 0)} rows look public-projectable by risk and novelty, assuming fixture and anti-claim gaps are closed first.",
        "",
        "These classes overlap. They are routing diagnostics, not final scores.",
        "",
        "## Strongly Grounded Rows",
        "",
        "Rows currently classified as `strong_high_authority` include:",
        "",
        *[f"- `{pattern_id}`" for pattern_id in strong_ids[:24]],
        "",
        "## Weak Binding Classes",
        "",
        *(weak_lines or ["- none"]),
        "",
        "## Missing Concrete Refs",
        "",
        f"The validator currently finds {missing_ref_count} ledger source refs that do not resolve to a live file or directory.",
        "",
        *(missing_ref_lines or ["- none"]),
        "",
        "## Load-Bearing Cluster Roots",
        "",
        *(cluster_lines or ["- none"]),
        "",
        "## Foundation Route Bundles",
        "",
        "Locally mined route bundles for direct substrate import planning:",
        "",
        *(foundation_lines or ["- none"]),
        "",
        "## Frontier Combination Backlog",
        "",
        "Second-wave route bundles mined from local patterns that align with current external attention: agent reliability, benchmark integrity, formal verification, and projection drift control.",
        "",
        *(frontier_lines or ["- none"]),
        "",
        "## Public Projection Posture",
        "",
        "Likely safe with minimal rewriting, after detailed binding review:",
        "",
        *[f"- `{pattern_id}`" for pattern_id in safe_sample[:16]],
        "",
        "Macro-only or synthetic-fixture-first examples:",
        "",
        *[f"- `{pattern_id}`" for pattern_id in macro_ids[:16]],
        "",
        "## Next Type A Pass",
        "",
        f"Do not mine more rows first. {next_pass_sentence}",
    ]
    return "\n".join(str(line) for line in lines) + "\n"


def write_refreshed_sidecars(repo_root: Path) -> list[str]:
    binding_sidecar = build_refreshed_binding_sidecar(repo_root)
    weak_sidecar = build_refreshed_weak_binding_sidecar(repo_root)
    _atomic_write_json(repo_root / BINDINGS_REL, binding_sidecar)
    _atomic_write_json(repo_root / WEAK_BINDINGS_REL, weak_sidecar)
    report = build_extracted_pattern_substrate_validation_report(repo_root)
    _atomic_write_json(repo_root / VALIDATION_REPORT_REL, report)
    markdown = build_coverage_report_markdown(report, binding_sidecar, weak_sidecar)
    _atomic_write_text(repo_root / COVERAGE_REPORT_REL, markdown)
    return [BINDINGS_REL, WEAK_BINDINGS_REL, VALIDATION_REPORT_REL, COVERAGE_REPORT_REL]


def _load_json_sidecar(repo_root: Path, rel: str, findings: list[dict[str, Any]]) -> dict[str, Any]:
    path = repo_root / rel
    if not path.is_file():
        findings.append(
            _finding(
                severity="error",
                rule="missing_sidecar",
                message=f"Required sidecar {rel} does not exist.",
                path=rel,
            )
        )
        return {}
    try:
        payload = _read_json(path)
    except json.JSONDecodeError as exc:
        findings.append(
            _finding(
                severity="error",
                rule="invalid_json_sidecar",
                message=str(exc),
                path=rel,
            )
        )
        return {}
    if not isinstance(payload, dict):
        findings.append(
            _finding(
                severity="error",
                rule="invalid_json_sidecar",
                message=f"{rel} top-level value must be an object.",
                path=rel,
            )
        )
        return {}
    return payload


def _validate_source_counts(
    *,
    source_name: str,
    expected_count: int,
    observed_count: Any,
    findings: list[dict[str, Any]],
    path: str,
) -> None:
    if observed_count != expected_count:
        findings.append(
            _finding(
                severity="error",
                rule="source_row_count_mismatch",
                message=f"{source_name} source row count no longer matches the extracted pattern ledger.",
                path=path,
                expected=expected_count,
                observed=observed_count,
            )
        )


def _validate_ledger_refs(
    repo_root: Path,
    rows: list[Mapping[str, Any]],
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    missing: list[dict[str, Any]] = []
    for row in rows:
        pattern_id = str(row.get("pattern_id") or "unknown")
        for ref in row.get("source_refs", []):
            if not isinstance(ref, str):
                continue
            candidate = _concrete_path_candidate(ref)
            if candidate is None:
                continue
            if not _path_exists(repo_root, ref):
                record = {"pattern_id": pattern_id, "path": candidate}
                missing.append(record)
                findings.append(
                    _finding(
                        severity="error",
                        rule="missing_concrete_source_ref",
                        pattern_id=pattern_id,
                        path=candidate,
                        message="Pattern source_ref does not resolve to a file or directory in the macro substrate.",
                    )
                )
    return missing


def _validate_binding_sidecar(
    repo_root: Path,
    bindings: Mapping[str, Any],
    ledger_ids: set[str],
    row_by_id: Mapping[str, Mapping[str, Any]],
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    detailed_bindings = bindings.get("pattern_bindings")
    if not isinstance(detailed_bindings, list):
        findings.append(
            _finding(
                severity="error",
                rule="missing_pattern_bindings",
                path=BINDINGS_REL,
                message="Binding sidecar must carry pattern_bindings[].",
            )
        )
        return []

    binding_rows: list[dict[str, Any]] = []
    for binding in detailed_bindings:
        if not isinstance(binding, Mapping):
            findings.append(
                _finding(
                    severity="error",
                    rule="invalid_pattern_binding",
                    path=BINDINGS_REL,
                    message="Each pattern_bindings[] entry must be an object.",
                )
            )
            continue
        pattern_id = str(binding.get("pattern_id") or "").strip()
        if not pattern_id:
            findings.append(
                _finding(
                    severity="error",
                    rule="missing_pattern_id",
                    path=BINDINGS_REL,
                    message="pattern_bindings[] entry lacks pattern_id.",
                )
            )
            continue
        binding_rows.append(dict(binding))
        if pattern_id not in ledger_ids:
            findings.append(
                _finding(
                    severity="error",
                    rule="binding_unknown_pattern_id",
                    pattern_id=pattern_id,
                    path=BINDINGS_REL,
                    message="Detailed binding pattern_id is not present in the extracted pattern ledger.",
                )
            )
        if not str(binding.get("anti_claim") or "").strip():
            findings.append(
                _finding(
                    severity="error",
                    rule="binding_missing_anti_claim",
                    pattern_id=pattern_id,
                    path=BINDINGS_REL,
                    message="Detailed binding must state an anti_claim.",
                )
            )
        if not str(binding.get("fixture_strategy") or "").strip():
            findings.append(
                _finding(
                    severity="error",
                    rule="binding_missing_fixture_strategy",
                    pattern_id=pattern_id,
                    path=BINDINGS_REL,
                    message="Detailed binding must state a fixture_strategy.",
                )
            )
        if not isinstance(binding.get("substrate_bindings"), Mapping) or not binding.get("substrate_bindings"):
            findings.append(
                _finding(
                    severity="error",
                    rule="binding_missing_substrate_refs",
                    pattern_id=pattern_id,
                    path=BINDINGS_REL,
                    message="Detailed binding must carry substrate_bindings.",
                )
            )
        for _, ref in _iter_substrate_refs(binding):
            candidate = _concrete_path_candidate(ref)
            if candidate is not None and not _path_exists(repo_root, ref):
                findings.append(
                    _finding(
                        severity="error",
                        rule="binding_missing_concrete_ref",
                        pattern_id=pattern_id,
                        path=candidate,
                        message="Detailed binding substrate ref does not resolve to a file or directory.",
                    )
                )
        row = row_by_id.get(pattern_id)
        if row:
            risk = str(row.get("private_state_risk") or "")
            if risk in {"medium", "high"}:
                posture = " ".join(
                    [
                        str(binding.get("public_projection_posture") or ""),
                        str(binding.get("fixture_strategy") or ""),
                    ]
                ).lower()
                if not any(token in posture for token in ("synthetic", "static", "macro", "not_ready")):
                    findings.append(
                        _finding(
                            severity="warning",
                            rule="private_state_binding_needs_fixture_posture",
                            pattern_id=pattern_id,
                            path=BINDINGS_REL,
                            message="Private-state-heavy pattern binding should explicitly require synthetic/static/macro-only projection.",
                        )
                    )
    return binding_rows


def _validate_weak_sidecar(
    weak_bindings: Mapping[str, Any],
    ledger_ids: set[str],
    findings: list[dict[str, Any]],
) -> None:
    classes = weak_bindings.get("weakness_classes")
    if not isinstance(classes, list):
        findings.append(
            _finding(
                severity="error",
                rule="missing_weakness_classes",
                path=WEAK_BINDINGS_REL,
                message="Weak-binding sidecar must carry weakness_classes[].",
            )
        )
        return
    for weak_class in classes:
        if not isinstance(weak_class, Mapping):
            continue
        class_id = str(weak_class.get("class_id") or "unknown")
        full_ids = weak_class.get("full_pattern_ids")
        ids = full_ids if isinstance(full_ids, list) else weak_class.get("pattern_ids")
        if isinstance(ids, list):
            if weak_class.get("count") != len(ids):
                findings.append(
                    _finding(
                        severity="warning",
                        rule="weak_class_count_mismatch",
                        path=WEAK_BINDINGS_REL,
                        message=f"Weakness class {class_id} count does not match its explicit pattern id list.",
                        expected=len(ids),
                        observed=weak_class.get("count"),
                    )
                )
            for pattern_id in ids:
                if isinstance(pattern_id, str) and pattern_id not in ledger_ids:
                    findings.append(
                        _finding(
                            severity="error",
                            rule="weak_class_unknown_pattern_id",
                            pattern_id=pattern_id,
                            path=WEAK_BINDINGS_REL,
                            message=f"Weakness class {class_id} references a pattern id outside the ledger.",
                        )
                    )
    for repair in weak_bindings.get("priority_repairs", []):
        if not isinstance(repair, Mapping):
            continue
        pattern_id = str(repair.get("pattern_id") or "")
        if pattern_id and pattern_id not in ledger_ids:
            findings.append(
                _finding(
                    severity="error",
                    rule="priority_repair_unknown_pattern_id",
                    pattern_id=pattern_id,
                    path=WEAK_BINDINGS_REL,
                    message="priority_repairs[] references a pattern id outside the ledger.",
                )
            )


def _validate_binding_contract(
    repo_root: Path,
    bindings: Mapping[str, Any],
    findings: list[dict[str, Any]],
) -> None:
    contract = bindings.get("binding_contract")
    if not isinstance(contract, Mapping):
        findings.append(
            _finding(
                severity="error",
                rule="binding_contract_missing",
                path=BINDINGS_REL,
                message="Binding sidecar must carry binding_contract.",
            )
        )
        return
    governing_standard = str(contract.get("governing_standard") or "").strip()
    if governing_standard != GOVERNING_STANDARD_REL:
        findings.append(
            _finding(
                severity="error",
                rule="binding_contract_governing_standard_mismatch",
                path=BINDINGS_REL,
                message="Binding sidecar must name the extracted-pattern substrate binding standard.",
                expected=GOVERNING_STANDARD_REL,
                observed=governing_standard or None,
            )
        )
        return
    if not _path_exists(repo_root, governing_standard):
        findings.append(
            _finding(
                severity="error",
                rule="binding_contract_governing_standard_missing",
                path=GOVERNING_STANDARD_REL,
                message="Binding sidecar governing_standard does not resolve in the macro substrate.",
            )
        )


def build_extracted_pattern_substrate_validation_report(repo_root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    ledger_path = repo_root / LEDGER_REL
    if not ledger_path.is_file():
        findings.append(
            _finding(
                severity="error",
                rule="missing_ledger",
                path=LEDGER_REL,
                message="Extracted pattern ledger does not exist.",
            )
        )
    ledger_rows = _read_jsonl(ledger_path)
    invalid_jsonl_rows = [row for row in ledger_rows if row.get("_invalid_jsonl")]
    for row in invalid_jsonl_rows:
        findings.append(
            _finding(
                severity="error",
                rule="invalid_ledger_jsonl_row",
                path=f"{LEDGER_REL}:{row.get('_line_number')}",
                message=str(row.get("_error") or "invalid jsonl row"),
            )
        )
    rows = [row for row in ledger_rows if not row.get("_invalid_jsonl")]

    bindings = _load_json_sidecar(repo_root, BINDINGS_REL, findings)
    weak_bindings = _load_json_sidecar(repo_root, WEAK_BINDINGS_REL, findings)

    if bindings and bindings.get("schema_version") != EXPECTED_BINDING_SCHEMA:
        findings.append(
            _finding(
                severity="error",
                rule="invalid_binding_schema_version",
                path=BINDINGS_REL,
                message="Binding sidecar schema_version is not the expected contract.",
                expected=EXPECTED_BINDING_SCHEMA,
                observed=bindings.get("schema_version"),
            )
        )
    if weak_bindings and weak_bindings.get("schema_version") != EXPECTED_WEAK_SCHEMA:
        findings.append(
            _finding(
                severity="error",
                rule="invalid_weak_binding_schema_version",
                path=WEAK_BINDINGS_REL,
                message="Weak-binding sidecar schema_version is not the expected contract.",
                expected=EXPECTED_WEAK_SCHEMA,
                observed=weak_bindings.get("schema_version"),
            )
        )

    ledger_ids = [str(row.get("pattern_id") or "") for row in rows]
    id_counts = Counter(ledger_ids)
    duplicate_ids = sorted(pattern_id for pattern_id, count in id_counts.items() if pattern_id and count > 1)
    for pattern_id in duplicate_ids:
        findings.append(
            _finding(
                severity="error",
                rule="duplicate_pattern_id",
                pattern_id=pattern_id,
                path=LEDGER_REL,
                message="Pattern id appears more than once in the extracted pattern ledger.",
            )
        )
    for row in rows:
        pattern_id = str(row.get("pattern_id") or "")
        if not pattern_id:
            findings.append(
                _finding(
                    severity="error",
                    rule="missing_pattern_id",
                    path=LEDGER_REL,
                    message="Ledger row lacks pattern_id.",
                )
            )
    ledger_id_set = {pattern_id for pattern_id in ledger_ids if pattern_id}
    row_by_id = {str(row.get("pattern_id")): row for row in rows if row.get("pattern_id")}

    ledger_row_count = len(rows)
    if bindings:
        _validate_source_counts(
            source_name="binding sidecar",
            expected_count=ledger_row_count,
            observed_count=bindings.get("source_row_count"),
            findings=findings,
            path=BINDINGS_REL,
        )
        coverage_rows = ((bindings.get("coverage_summary") or {}) or {}).get("rows")
        _validate_source_counts(
            source_name="binding coverage summary",
            expected_count=ledger_row_count,
            observed_count=coverage_rows,
            findings=findings,
            path=BINDINGS_REL,
        )
    if weak_bindings:
        _validate_source_counts(
            source_name="weak-binding sidecar",
            expected_count=ledger_row_count,
            observed_count=weak_bindings.get("source_row_count"),
            findings=findings,
            path=WEAK_BINDINGS_REL,
        )

    missing_source_refs = _validate_ledger_refs(repo_root, rows, findings)
    if bindings:
        _validate_binding_contract(repo_root, bindings, findings)
    detailed_bindings = _validate_binding_sidecar(repo_root, bindings, ledger_id_set, row_by_id, findings) if bindings else []
    _validate_weak_sidecar(weak_bindings, ledger_id_set, findings)

    detailed_ids = {str(binding.get("pattern_id")) for binding in detailed_bindings if binding.get("pattern_id")}
    ledger_ids_without_detailed = sorted(ledger_id_set - detailed_ids)
    detailed_ids_without_ledger = sorted(detailed_ids - ledger_id_set)

    binding_refs = _binding_refs_by_pattern_id(bindings)
    profiles = [
        _row_evidence_profile(row, binding_refs.get(str(row.get("pattern_id") or "")))
        for row in rows
    ]
    evidence_class_counts: Counter[str] = Counter()
    grounding_class_counts: Counter[str] = Counter()
    for profile in profiles:
        evidence_class_counts.update(profile["evidence_class_counts"])
        grounding_class_counts.update(profile["grounding_classes"])

    strong_pattern_ids = sorted(
        str(profile["pattern_id"])
        for profile in profiles
        if "strong_high_authority" in profile["grounding_classes"] and profile.get("pattern_id")
    )
    macro_only_candidates = sorted(
        str(row.get("pattern_id"))
        for row in rows
        if str(row.get("private_state_risk") or "") == "high" and row.get("pattern_id")
    )
    safe_public_projection_candidates = sorted(
        str(profile["pattern_id"])
        for profile in profiles
        if "public_projection_candidate_by_risk_and_novelty" in profile["grounding_classes"]
        and profile.get("pattern_id")
    )

    new_rows_after_declared_count: list[str] = []
    declared_count = bindings.get("source_row_count") if isinstance(bindings, Mapping) else None
    if isinstance(declared_count, int) and 0 <= declared_count < len(rows):
        new_rows_after_declared_count = [
            str(row.get("pattern_id"))
            for row in rows[declared_count:]
            if row.get("pattern_id")
        ]

    findings_by_severity = Counter(str(finding.get("severity") or "unknown") for finding in findings)
    error_count = int(findings_by_severity.get("error") or 0)
    warning_count = int(findings_by_severity.get("warning") or 0)

    load_bearing_clusters = bindings.get("load_bearing_cluster_roots") if isinstance(bindings, Mapping) else []
    if not isinstance(load_bearing_clusters, list):
        load_bearing_clusters = []
    foundation_routes = bindings.get("foundation_combination_routes") if isinstance(bindings, Mapping) else []
    if not isinstance(foundation_routes, list):
        foundation_routes = []
    frontier_routes = bindings.get("frontier_combination_routes") if isinstance(bindings, Mapping) else []
    if not isinstance(frontier_routes, list):
        frontier_routes = []

    report = {
        "kind": "extracted_pattern_substrate_binding_validation_report",
        "schema_version": "extracted_pattern_substrate_binding_validation_report_v1",
        "artifact_role": "validator_over_macro_pattern_substrate_binding_sidecars",
        "generated_at": _utc_now(),
        "authority_boundary": "generated_validation_not_pattern_authority",
        "scope": {
            "side": "macro_private_root",
            "public_microcosm_rebuild": False,
            "private_content_policy": "validate refs and structure only; do not expose private raw seed or operator content",
        },
        "source_manifest": _source_manifest(repo_root),
        "summary": {
            "status": "ok" if error_count == 0 else "needs_binding_repair",
            "recommended_action": "trust_for_projection" if error_count == 0 else "refresh_binding_sidecars_before_projection",
            "ledger_row_count": ledger_row_count,
            "binding_source_row_count": bindings.get("source_row_count") if isinstance(bindings, Mapping) else None,
            "weak_binding_source_row_count": weak_bindings.get("source_row_count") if isinstance(weak_bindings, Mapping) else None,
            "detailed_binding_count": len(detailed_bindings),
            "ledger_ids_without_detailed_binding_count": len(ledger_ids_without_detailed),
            "new_rows_after_declared_count": len(new_rows_after_declared_count),
            "missing_concrete_ref_count": len(missing_source_refs),
            "error_count": error_count,
            "warning_count": warning_count,
        },
        "coverage_projection": {
            "evidence_class_counts": dict(sorted(evidence_class_counts.items())),
            "grounding_class_counts": dict(sorted(grounding_class_counts.items())),
            "strong_high_authority_pattern_ids": strong_pattern_ids,
            "macro_only_candidates": macro_only_candidates,
            "safe_public_projection_candidate_count": len(safe_public_projection_candidates),
            "safe_public_projection_candidate_sample": safe_public_projection_candidates[:24],
        },
        "sidecar_staleness": {
            "new_rows_after_declared_source_count": new_rows_after_declared_count,
            "ledger_ids_without_detailed_binding_count": len(ledger_ids_without_detailed),
            "ledger_ids_without_detailed_binding_sample": ledger_ids_without_detailed[:80],
            "detailed_ids_without_ledger": detailed_ids_without_ledger,
        },
        "missing_concrete_source_refs": missing_source_refs[:120],
        "load_bearing_cluster_roots": [
            {
                "cluster_id": str(cluster.get("cluster_id") or ""),
                "supports_pattern_count": len(cluster.get("supports_pattern_ids") or []),
                "substrate_ref_count": len(cluster.get("substrate_refs") or []),
            }
            for cluster in load_bearing_clusters
            if isinstance(cluster, Mapping)
        ],
        "foundation_combination_routes": [
            {
                "route_id": str(route.get("route_id") or ""),
                "priority_rank": route.get("priority_rank"),
                "available_pattern_count": (
                    (route.get("ledger_slice") or {}).get("available_pattern_count")
                    if isinstance(route.get("ledger_slice"), Mapping)
                    else None
                ),
                "target_existing_organs": route.get("target_existing_organs") or [],
            }
            for route in foundation_routes
            if isinstance(route, Mapping)
        ],
        "frontier_combination_routes": [
            {
                "route_id": str(route.get("route_id") or ""),
                "priority_rank": route.get("priority_rank"),
                "available_pattern_count": (
                    (route.get("ledger_slice") or {}).get("available_pattern_count")
                    if isinstance(route.get("ledger_slice"), Mapping)
                    else None
                ),
                "target_existing_organs": route.get("target_existing_organs") or [],
                "missing_detailed_binding_count": len(
                    route.get("missing_detailed_binding_pattern_ids") or []
                ),
            }
            for route in frontier_routes
            if isinstance(route, Mapping)
        ],
        "next_actions": [
            f"Refresh extracted_pattern_substrate_bindings.json and extracted_pattern_weak_bindings.json against the current {ledger_row_count}-row ledger.",
            "Refine foundation and frontier route bundles before implementing isolated high-authority rows.",
            "For medium/high private-state rows, keep synthetic fixture posture explicit before any public projection.",
            "Promote this validation shape into a standard-adjacent row contract if the binding lane continues.",
        ],
        "findings": findings,
    }
    return report


def write_validation_report(repo_root: Path, report: Mapping[str, Any]) -> list[str]:
    path = repo_root / VALIDATION_REPORT_REL
    _atomic_write_json(path, report)
    return [VALIDATION_REPORT_REL]


def _print_report(report: Mapping[str, Any], written: list[str] | None = None) -> None:
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    print(
        "Extracted pattern substrate bindings: "
        f"ledger_rows={summary.get('ledger_row_count', 0)} | "
        f"detailed_bindings={summary.get('detailed_binding_count', 0)} | "
        f"errors={summary.get('error_count', 0)} warnings={summary.get('warning_count', 0)} | "
        f"status={summary.get('status')}"
    )
    if written is not None:
        if written:
            print("Wrote:")
            for path in written:
                print(f"  - {path}")
        else:
            print("Wrote: none")
    findings = report.get("findings") if isinstance(report.get("findings"), list) else []
    for finding in findings[:12]:
        pattern = f" pattern={finding.get('pattern_id')}" if finding.get("pattern_id") else ""
        path = f" path={finding.get('path')}" if finding.get("path") else ""
        print(f"- {finding.get('severity')} {finding.get('rule')}{pattern}{path}: {finding.get('message')}")
    if len(findings) > 12:
        print(f"... {len(findings) - 12} more findings")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate only; do not write the report.")
    parser.add_argument("--report", action="store_true", help="Print a human summary.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON validation report.",
    )
    parser.add_argument("--write", action="store_true", help="Write the generated validation report.")
    parser.add_argument(
        "--write-sidecars",
        action="store_true",
        help="Refresh binding and weak-binding sidecars, then write validation and coverage reports.",
    )
    parser.add_argument("--commit", action="store_true", help="Alias for --write; kept for builder compatibility.")
    args = parser.parse_args(argv)

    written: list[str] | None = None
    if args.write_sidecars and not args.check:
        written = write_refreshed_sidecars(REPO_ROOT)

    report = build_extracted_pattern_substrate_validation_report(REPO_ROOT)
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    error_count = int(summary.get("error_count") or 0)
    if (args.write or args.commit) and not args.check and not args.write_sidecars:
        written = write_validation_report(REPO_ROOT, report)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True))
    else:
        _print_report(report, written)
    return 1 if args.check and error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
