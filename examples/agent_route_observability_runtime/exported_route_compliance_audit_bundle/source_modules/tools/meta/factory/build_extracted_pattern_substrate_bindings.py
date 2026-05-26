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
        "route_id": "formal_policy_integrity_search_foundry",
        "priority_rank": 2,
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
        ],
        "why_impressive": (
            "The atlas is reusable only when agents can route from generated Kind/System "
            "Atlas rows back to standards, builders, freshness checks, and source-coupling "
            "receipts without treating the generated projection as authority."
        ),
        "candidate_fixture": (
            "Synthetic atlas fixture with five artifact kinds, one owner-check row, one "
            "cluster-first option surface, one stale source manifest, one no-refresh "
            "refusal, and a projection-not-authority receipt."
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
