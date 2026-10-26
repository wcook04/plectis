"""
[PURPOSE]
(Teleology) Defines the constitutional standard for Python comprehension, compression, routing, and population within ai_workflow.
Acts as the authoritative ABI for the Python substrate's multi-resolution "Holographic Shadow" strategy.

(Mechanism)
1.  **Reference Spec:** Defines the "Contract Atom" grammar and "Signal-to-Noise" laws required for docstrings.
2.  **Compression Constitution:** Defines file, class, function, span, graph-neighborhood, doctrine-route, and entry-packet fidelity bands.
3.  **Population Contract:** Defines deterministic extraction, provider candidate enrichment, row-patch proof gates, and Type A reconciliation.
4.  **Compliance Target:** Passes the Miner's audit (`miner.py`) to demonstrate schema validity.
5.  **Training Prompt:** Serves as the zero-shot instruction context for agents generating documentation.

(Objective)
To let agents route through the cheapest sufficient Python representation before reading source: file cards, local scope atoms, symbol capsules, graph context, doctrine/workflow context, and finally exact source spans when mutation or proof requires it.
Provider-backed population is useful only as bounded candidate evidence; it does not author standards, mutate source, or promote global claims without Type A proof and reconciliation.

[INTERFACE]
- **Inputs:** None (Reference Artifact).
- **Outputs:** None.
- **Exports:** `StandardReference` (Class), `atomic_write_operation` (Function), `PYTHON_STANDARD` (Dict).
- **ABI Contract:**
    - Modules MUST contain: `[PURPOSE]`, `[INTERFACE]`, `[FLOW]`, `[DEPENDENCIES]`, `[CONSTRAINTS]`.
    - Public Classes MUST contain: `[ROLE]`.
    - Public Functions/Methods MUST contain: `[ACTION]`.

[FLOW]
1.  **Ingest:** Developer/AI reads this file to learn the "Contract Atom" grammar.
2.  **Apply:** Docstrings are written/refactored using the atoms defined in `[CONSTRAINTS]`.
3.  **Audit:** `miner.py` validates tag presence against `PYTHON_STANDARD`.
4.  **Compile:** builders extract tags and AST facts into the semantic hologram surfaces under `codex/hologram/system/` plus `codex/standards/std_python_scope_index.json`.
5.  **Populate:** provider lanes may propose local row patches and capsules through `python_navigation_population_lane.py`; the acceptance gate decides promotion eligibility.
6.  **Route:** Entry/context-pack tooling consumes file cards, scope cards, graph hints, and row-patch gaps to decide which Python scopes to read next.
7.  **Validate Apply:** Live docstring enforcement passes must prove progress under the rollout/validator policies defined here and in `std_apply.json`.
8.  **Observe Runtime Use:** Repo Python invocations may emit ignored runtime usage counts that are projected back onto file/scope rows as non-authoritative salience.
9.  **Simulate:** Agents read the Hologram to predict system behavior, failure modes, and side effects.

[DEPENDENCIES]
- **Required:**
  - system.module.path (what you use from it)
  - another.system.module (what you use)
  - [OR] None (if no system imports)
- **Optional Runtime:**
  - External binary/service (e.g., Chrome at port 9222, Docker daemon)
  - Filesystem contract (e.g., codex/substrate/nodes/*.json must exist)
- **Stdlib Rule:** Omit os, json, sys, pathlib, typing. Include ONLY if they impose constraints (subprocess for specific binary, platform.system() for OS-specific behavior, ctypes for memory access).

[CONSTRAINTS]
1.  **Canonical Formatting Rules:**
    - Tags must be uppercase, enclosed in brackets, starting a new line (e.g., `[PURPOSE]`).
    - Payload follows the tag until the next tag.
    - Use bullet points (`-`) for structured atoms.
    - **Do not** nest bracket tags inside the payload text (confuses parsers).
    - This file defines the grammar and audit target for Python documentation. It does not authorize repo-wide enforcement by itself.

2.  **Contract Atom Grammar (The Encoding System):**
    Docstrings must use these prefixes to encode behavior. Narrative paragraphs are forbidden.
    - `Teleology:` Why this exists in the architecture.
    - `Mechanism:` The governing pattern (e.g., "State-Isolated Actor", "Scorched-Earth Auditor").
    - `Guarantee:` Invariant that is ALWAYS true after success.
    - `Forbid:` Illegal state/input that triggers immediate failure.
    - `Fails:` Trigger condition -> Failure Mode -> Failure Shape (Raise/Envelope/Warn).
    - `Warns:` Trigger -> Non-fatal degradation.
    - `Reads:` Required inputs (Disk/Env/Network/State/Config).
    - `Writes:` Persistent side effects (Files/Dirs/Network/Subprocess).
    - `Locks:` Concurrency and serialization rules (Thread-safety, Singleton).
    - `Orders:` Determinism rules (Sorting, Stability, Idempotence).
    - `Schema:` Precise output structure (JSON keys, Artifact names).
    - `Couples:` Cross-module dependency that alters semantics.
    - `Non-goal:` Explicit exclusions to prevent hallucinated capabilities.
    - `When-needed:` Optional trigger condition for opening this surface instead of broad repo search.
    - `Escalates-to:` Optional next higher-fidelity surface (`path` or `path::symbol`) when this docstring is not sufficient.
    - `Navigation-group:` Optional self-model group id that keeps file-local routing aligned with the Python runtime boundary.

3.  **Noise Ban List (Anti-Patterns):**
    - **Narrative Steps:** "1. Do X, 2. Do Y, 3. Return Z" (Redundant with code).
    - **Import Inventories:** "Depends on os, sys, time" (Low signal).
    - **Vague Roles:** "Handles data processing" (Zero signal).
    - **Signature Restatement:** "Takes a string, returns an int" (Redundant with type hints).

4.  **Quality Gates (Enforcement):**
    - Every `[ACTION]` MUST specify: Preconditions, Postconditions (`Guarantee`), and `Fails` (or "Fails: None").
    - Every `[ACTION]` SHOULD begin with `- Teleology: <one-line sentence>` for reliable holographic extraction. Tracked as a quality metric.
    - Every `[ROLE]` MUST specify: Ownership, Mutability, and Concurrency posture.
    - Every `[CONSTRAINTS]` MUST specify: Atomicity and Determinism policy.

5.  **Rollout Boundary:**
    - Repo-wide `std_python.py` enforcement requires a separate robustness policy.
    - Any bulk enforcement pass must define cohort sizing, pre-existing defect handling, rollback semantics, and post-build confirmation before it is considered in-bounds.

6.  **Routing-Fidelity Insight:**
    - A Python docstring is not only local truth; it can also be a first-hop router.
    - Use optional `When-needed`, `Escalates-to`, and `Navigation-group` when they help an IDE or bridge agent decide whether to stay local, open a sibling symbol, or jump to a higher-fidelity authority such as the self-model or apply runbook.
    - This keeps bridge prompts grounded in a compressed global index while letting file-local docstrings advertise the correct next read instead of forcing giant context dumps.

7.  **Structural Substrate Discipline:**
    - Every function/method in the documentation tree must carry a stable `symbol_id` (`path::qualified_name`), line span, and resolved callee references.
    - These enable: caching (stable identity), invalidation (changed callee → stale caller), function-scoped dispatch (span boundaries for large files), and dependency-ordered traversal.
    - `symbol_id` is globally unique across the repo. `owner_symbol_id` links methods to their owning class.

8.  **Recursive Self-Description Compatibility Contract:**
    - `std_python.py` governs a scope-aware protocol, not only a docstring grammar.
    - Scope authority is recursive: function `[ACTION]` atoms describe callable behavior, class `[ROLE]` atoms describe coordination/ownership, module `[PURPOSE|INTERFACE|FLOW|DEPENDENCIES|CONSTRAINTS]` describe file capability, and self-model artifacts own group/boundary classification.
    - Derived navigation surfaces must preserve existing emitted runtime field names even when the conceptual model uses richer language such as `called_by`; compatibility outputs continue to use currently consumed names like `inbound_dependents`.

9.  **Derivation And Precedence Discipline:**
    - Precedence is fixed: `authored > composed > derived > fallback`.
    - `authored`: direct docstring/source declaration.
    - `composed`: roll-up from child scopes in the same authority tree (for example class/file browse summaries composed from public methods or symbols).
    - `derived`: mechanical extraction or graph inversion from authoritative substrate (for example `callee_refs` inversion into `inbound_dependents`).
    - `fallback`: lowest-fidelity non-empty placeholder derived from lexical/name/signature evidence only when higher-precedence sources are absent.
    - Consumers must not silently collapse provenance. Lower-precedence values may keep browse continuity, but they do not override higher-precedence authority.

10. **Browse / Projection Fidelity Ladder:**
    - Fidelity 0: system card for whole-repo orientation.
    - Fidelity 1: boundary/group cards for architectural narrowing.
    - Fidelity 2: file cards for browse-first navigation.
    - Fidelity 3: symbol capsules for public classes/functions/methods.
    - Fidelity 4: full holographic projection from the documentation tree.
    - Fidelity 5: source code.
    - The runtime ladder remains compatibility-first: self-model and scope-index surfaces narrow candidates before source reads.

11. **Provenance And Quality Visibility:**
    - Derived browse fields should declare whether they are `authored`, `composed`, or `derived`.
    - Degraded browse surfaces must expose explicit warnings rather than presenting blanks as clean truth.
    - Canonical degraded-state vocabulary for Python navigation is: `dirty`, `stale`, `suspect`, `ambiguous`, `degraded`.

12. **Cache-Only Navigation Surface Rule:**
    - `codex/hologram/system/navigation_cache.json` is cache-only in the compatibility-first model.
    - It may denormalize or accelerate reads, but it cannot introduce unique semantic fields or become a competing authority.
    - Authoritative Python navigation remains split across `codex/hologram/system/scope_tree.json`, `codex/hologram/system/symbols.json`, and `codex/standards/std_python_scope_index.json`.

13. **Runtime Usage Projection Rule:**
    - Runtime usage counts are salience signals, not source authority and not deletion proof.
    - The raw aggregate lives under ignored state at `state/python_usage/python_usage_stats.json`.
    - Projection fields may appear on `std_python_scope_index.files[].usage` and `std_python_scope_index.scopes[].usage`.
    - Direct file run counts are automatic for non-kernel `repo-python` scripts; `kernel.py` first-contact routes opt out by default and require explicit `AIW_PYTHON_USAGE_STATS=1` because startup telemetry must not tax mandatory agent entry commands. Per-function call counts are higher-cost and must be enabled deliberately with `AIW_PYTHON_USAGE_FUNCTIONS=1`.
    - File counters distinguish direct script runs from repo-local function calls; scope counters use stable `symbol_id` when the runtime can resolve `path::qualname`.
    - Consumers may use `usage.status == "unobserved"` to route review of lonely code, but deletion requires separate reference, test, and owner checks.
"""
from typing import Any, Dict, List

# --- THE EXECUTABLE CONSTITUTION ---
# This dictionary is the SINGLE Source of Truth for the Miner (analysis.py).
# Editing this dictionary automatically updates the enforcement rules.
PYTHON_STANDARD = {
    "module": {
        "required_tags": ["PURPOSE", "INTERFACE", "FLOW", "DEPENDENCIES", "CONSTRAINTS"]
    },
    "public_class": {
        "required_tags": ["ROLE"]
    },
    "public_function": {
        "required_tags": ["ACTION"]
    },
    "contract_atoms": [
        "Teleology", "Mechanism", "Guarantee", "Forbid", "Fails",
        "Warns", "Reads", "Writes", "Locks", "Orders", "Schema",
        "Couples", "Non-goal"
    ],
    "optional_contract_atoms": [
        "When-needed",
        "Escalates-to",
        "Navigation-group"
    ],
    "routing_fidelity": {
        "summary": "Docstrings may act as first-hop routing surfaces: use When-needed for trigger conditions, Escalates-to for the next higher-fidelity authority, and Navigation-group to keep file-local routing aligned with the Python runtime self-model when that materially reduces context load.",
        "preferred_global_index": "codex/hologram/system/scope_tree.json",
        "review_runbook": "codex/doctrine/skills/kernel/apply.md"
    },
    "compression_population_constitution": {
        "summary": "std_python owns the Python substrate's multi-resolution comprehension ladder and the provider-backed population loop that enriches it under proof.",
        "governing_principles": [
            "pri_001::json_contract_markdown_projection",
            "pri_049::minimum_sufficient_read_graph",
            "pri_111::paper_modules_preempt_re_derivation",
            "pri_121::compressed_projection_before_overbudget_prose",
            "pri_127::lossless_compression_requires_full_system_context",
            "pri_128::implementation_is_not_adoption_without_entry_routes",
            "con_016::actor_axes"
        ],
        "comprehension_units": [
            {
                "unit": "source_span",
                "evidentiary_right": "Exact source authority for mutation/proof; not a compression substitute.",
                "population_authority": "deterministic builder or Type A source read"
            },
            {
                "unit": "local_scope_atom",
                "evidentiary_right": "AST/docstring facts for one function, method, or class.",
                "population_authority": "deterministic extraction first; provider may propose candidate enrichment"
            },
            {
                "unit": "local_scope_capsule",
                "evidentiary_right": "Compressed purpose/interface/flow of one scope; local-only unless broader context was supplied.",
                "population_authority": "provider candidate allowed through row-patch proof gate; Type A reconciles"
            },
            {
                "unit": "file_card",
                "evidentiary_right": "Whole-file role, exported interface, internal segmentation, and dependency hints.",
                "population_authority": "Type A or high-context provider packet plus proof gate"
            },
            {
                "unit": "graph_context",
                "evidentiary_right": "Imports, calls, tests, reverse dependencies, route edges, and blast-radius hints.",
                "population_authority": "deterministic graph builder plus proofed enrichments"
            },
            {
                "unit": "doctrine_route_context",
                "evidentiary_right": "Why the file/scope matters to standards, paper modules, skills, WorkItems, and lanes.",
                "population_authority": "paper modules, standards, WorkItems, and Type A reconciliation"
            },
            {
                "unit": "entry_packet",
                "evidentiary_right": "Task-specific minimal read graph handed to a cold agent.",
                "population_authority": "kernel entry/context-pack builder"
            }
        ],
        "fidelity_band_authority": {
            "exact_source": "source_span",
            "deterministic_fact": "local_scope_atom",
            "provider_observation": "local_scope_capsule_candidate",
            "type_a_reconciled_projection": ["file_card", "graph_context", "doctrine_route_context"],
            "operational_consumption": "entry_packet"
        },
        "local_global_claim_boundary": {
            "provider_local_scope_packet": {
                "may_claim": [
                    "local behavior visible in supplied span",
                    "signature/interface facts visible in supplied context",
                    "local dependency signals visible in supplied context",
                    "uncertainty and escalation atoms"
                ],
                "must_not_claim": [
                    "file or subsystem role unless file/graph/doctrine context was supplied",
                    "global ownership or blast radius without graph context",
                    "promotion-ready source truth without Type A proof"
                ],
                "required_fields": [
                    "input_scope_id",
                    "path",
                    "span_or_source_hash",
                    "context_band_supplied",
                    "claim_authority",
                    "confidence",
                    "proof_requirements"
                ]
            }
        },
        "large_file_segmentation": {
            "preferred_sequence": [
                "file_inventory",
                "segment_map",
                "per_scope_capsules",
                "file_synthesis",
                "graph_reconciliation"
            ],
            "segmentation_sources": [
                "AST scopes",
                "classes/functions",
                "docstring tags",
                "import blocks",
                "CLI command groups",
                "builder phases",
                "route-owning slices",
                "test-adjacent regions"
            ],
            "forbidden_shortcut": "whole_giant_file_single_provider_summary"
        },
        "provider_population_boundary": {
            "candidate_lane": "tools/meta/control/python_navigation_population_lane.py",
            "acceptance_standard": "codex/standards/std_navigation_population_acceptance.json",
            "row_patch_surface": "./repo-python kernel.py --option-surface row_patches --band cluster_flag",
            "runtime_eligibility_probe": "./repo-python tools/meta/control/python_navigation_population_lane.py provider-capacity-discovery",
            "current_posture_rule": "Treat provider eligibility as a runtime fact. When discovery reports NVIDIA eligible, use NVIDIA-first for constrained candidate generation. When discovery reports OpenRouter missing_adapter, keep it pending adapter repair rather than in default promotion lanes.",
            "mutation_rule": "Provider output enters as row_patch/receipt/candidate observation only; standards and source mutate only through Type A apply/proof gates."
        },
        "entry_consumption_obligation": {
            "entry_route": "./repo-python kernel.py --entry \"<python task>\" --context-budget 12000",
            "context_pack_route": "./repo-python kernel.py --context-pack \"<python task>\" --context-budget 12000",
            "must_surface": [
                "python_files file_card when a file path is named",
                "python_scopes symbol_capsule when a function/class/method is named",
                "graph_context hints for impact/blast-radius/dependency tasks",
                "source_span drilldown only when mutation/proof needs exact source",
                "row_patches/provider lane when population gaps block route quality"
            ],
            "false_win": "A populated projection is not adopted until entry/context-pack packets consume it."
        }
    },
    "recursive_self_description": {
        "summary": "Compatibility-first recursive self-description contract for Python navigation and browse surfaces.",
        "scope_authority": {
            "function": {
                "authority": "[ACTION]",
                "owns": [
                    "teleology_and_behavior_contract",
                    "routing_atoms_for_callable_scope",
                    "stable_symbol_identity"
                ],
                "compatibility_notes": [
                    "Preserve existing emitted runtime field names.",
                    "Use conceptual called_by language in standards only; emitted compatibility field remains inbound_dependents."
                ]
            },
            "class": {
                "authority": "[ROLE]",
                "owns": [
                    "coordination_role",
                    "ownership_and_mutability",
                    "class_scope_routing"
                ],
                "composition_rule": "Missing browse summaries should compose from public methods before lexical fallback."
            },
            "file": {
                "authority": ["[PURPOSE]", "[INTERFACE]", "[FLOW]", "[DEPENDENCIES]", "[CONSTRAINTS]"],
                "owns": [
                    "module_capability",
                    "export_shape",
                    "file_scope_routing"
                ],
                "composition_rule": "Missing browse summaries or when-needed text should compose from public symbols before mechanical fallback."
            },
            "group_boundary": {
                "authority": "codex/hologram/system/scope_tree.json",
                "owns": [
                    "boundary_membership",
                    "group_classification",
                    "coverage_rollups"
                ],
                "notes": "std_python references group/boundary authority but does not duplicate the taxonomy."
            }
        }
    },
    "derivation_precedence": {
        "summary": "Derived Python browse/navigation values must honor one precedence chain everywhere.",
        "order": [
            "authored",
            "composed",
            "derived",
            "fallback"
        ],
        "definitions": {
            "authored": "Value comes directly from source docstrings or explicitly authored standard-bearing metadata.",
            "composed": "Value is rolled up from child scopes in the same authority tree before any generic derivation.",
            "derived": "Value is mechanically inferred from authoritative substrate such as AST facts, graph inversion, imports, or self-model joins.",
            "fallback": "Lowest-fidelity non-empty placeholder derived from lexical/name/signature evidence only when higher-precedence sources are absent."
        },
        "compatibility_rule": "Precedence may enrich projections but must not rename currently consumed runtime fields."
    },
    "browse_projection_fidelity": {
        "summary": "Compatibility browse ladder for Python navigation surfaces. The constitutional compression lattice lives in compression_population_constitution; these names remain because adapters already consume them.",
        "levels": [
            {
                "level": 0,
                "name": "system_card",
                "scope": "system",
                "artifact_family": [
                    "codex/hologram/system/scope_tree.json"
                ]
            },
            {
                "level": 1,
                "name": "wide_scope_tree",
                "scope": "system_boundary_group_file",
                "artifact_family": [
                    "codex/hologram/system/scope_tree.json"
                ]
            },
            {
                "level": 2,
                "name": "compact_symbol_file_cards",
                "scope": "file_or_symbol",
                "artifact_family": [
                    "codex/standards/std_python_scope_index.json"
                ]
            },
            {
                "level": 3,
                "name": "deep_scope_tree",
                "scope": "file_or_symbol",
                "artifact_family": [
                    "codex/hologram/system/symbols.json"
                ]
            },
            {
                "level": 4,
                "name": "graph_and_quality_enrichment",
                "scope": "cross_cutting",
                "artifact_family": [
                    "codex/hologram/system/graph.json",
                    "codex/hologram/system/quality.json"
                ]
            },
            {
                "level": 5,
                "name": "source_code",
                "scope": "source",
                "artifact_family": [
                    "repo_python_files"
                ]
            }
        ],
        "compatibility_notes": [
            "The runtime may keep current CLI verbs while serving this ladder through existing surfaces.",
            "Higher-fidelity surfaces narrow after lower-fidelity browse results indicate the correct target.",
            "symbol_capsule is a staged population band, not an unimplemented idea; provider-backed local capsules must stay typed as local observations until proofed and reconciled."
        ]
    },
    "navigation_contract": {
        "profile_id": "python_scope_navigation_v0",
        "artifact_kind": "python_scopes",
        "navigable_bands": [
            "module_docs",
            "file_card",
            "symbol_capsule",
            "graph_context",
            "source_span"
        ],
        "band_contracts": {
            "module_docs": {
                "purpose": "Cheapest structural browse row for a Python file.",
                "minimum_payload": ["path", "module [PURPOSE]", "exports or public symbol count", "navigation_group when present"],
                "forbidden": ["function bodies", "full source", "character-truncation summaries"],
                "drilldown_to": "file_card"
            },
            "file_card": {
                "purpose": "File-level structural card composed from module docstring and public symbols.",
                "minimum_payload": ["[INTERFACE]", "[FLOW]", "[DEPENDENCIES]", "[CONSTRAINTS]", "top public symbols", "quality state"],
                "forbidden": ["full source body", "implicit dependency inventory without semantic role"],
                "drilldown_to": "symbol_capsule"
            },
            "symbol_capsule": {
                "purpose": "Function/class/method capsule over signature, docstring atoms, span, and local routing atoms.",
                "minimum_payload": ["symbol_id", "signature", "line span", "[ACTION] or [ROLE]", "when_needed", "escalates_to"],
                "forbidden": ["blind body summary", "prose-length-only compression"],
                "drilldown_to": "graph_context"
            },
            "graph_context": {
                "purpose": "Relational scope packet with callers/callees, inbound dependents, related paths, tests, and quality warnings.",
                "minimum_payload": ["callee_refs", "inbound_dependents", "owner_symbol_id", "related_symbols", "derivation_warnings"],
                "forbidden": ["pretend graph context is source authority", "drop provenance of authored/composed/derived fields"],
                "drilldown_to": "source_span"
            },
            "source_span": {
                "purpose": "Authoritative source read for mutation or proof.",
                "minimum_payload": ["repo path", "line_start", "line_end", "source excerpt or open command"],
                "forbidden": ["generated projection mutation"],
                "drilldown_to": "repo Python source"
            }
        },
        "telescope_facets": [
            {"facet": "module_docstring", "rule": "Module tags telescope file purpose, interface, flow, dependencies, and constraints before source."},
            {"facet": "class_role", "rule": "Class [ROLE] atoms telescope ownership, mutability, and concurrency posture."},
            {"facet": "function_action", "rule": "Function [ACTION] atoms telescope teleology, guarantees, failures, reads/writes, and escalation."},
            {"facet": "symbol_graph", "rule": "Call/dependency edges expand at graph_context, not at the cheapest browse band."},
            {"facet": "source_span", "rule": "Source spans are the evidence layer, not a compression band substitute."}
        ],
        "navigable_scopes": [
            {"scope": "module", "rule": "One Python source file and its module docstring contract."},
            {"scope": "class", "rule": "One class and its [ROLE] atoms, methods, and ownership context."},
            {"scope": "function", "rule": "One top-level function and its [ACTION] atoms."},
            {"scope": "method", "rule": "One class-owned function and owner_symbol_id context."},
            {"scope": "source_span", "rule": "Authoritative line-bounded source evidence."}
        ],
        "navigable_facets": [
            {"facet": "module_docstring", "rule": "[PURPOSE]/[INTERFACE]/[FLOW]/[DEPENDENCIES]/[CONSTRAINTS]."},
            {"facet": "signature", "rule": "Callable/class signature and exported identity."},
            {"facet": "contract_atoms", "rule": "[ACTION]/[ROLE] authored semantic atoms."},
            {"facet": "body", "rule": "Implementation source body, evidence only."},
            {"facet": "symbol_graph", "rule": "Callers, callees, owner, related symbols, and tests."},
            {"facet": "source_span", "rule": "Line-bounded source authority."}
        ],
        "population_policy": {
            "band:module_docs": {"populated_by": "compiled", "emitter": "std_python scope/documentation builders", "source": "repo Python files"},
            "band:file_card": {"populated_by": "compiled", "emitter": "codex/standards/std_python_scope_index.json", "source": "module docstring plus public symbols"},
            "band:symbol_capsule": {
                "populated_by": "staged_population_contract",
                "current_adapter_status": "python_scopes card rows expose symbol_id, signature, line span, local routing atoms, graph hints, and source_span metadata; provider-authored local capsules remain row-patch candidates until proofed.",
                "stage_order": [
                    "routing_atoms_first",
                    "local_scope_capsules_second",
                    "file_synthesis_third",
                    "graph_context_scoring_fourth",
                    "entry_consumption_proof_required_before_scaled_population"
                ],
                "candidate_lane": "tools/meta/control/python_navigation_population_lane.py",
                "acceptance_gate": "codex/standards/std_navigation_population_acceptance.json::lanes.python_navigation_population",
                "authority_boundary": "Provider capsules are local observations unless context_band_supplied includes file, graph, and doctrine context; Type A reconciliation promotes only proofed claims."
            },
            "band:graph_context": {"populated_by": "compiled", "emitter": "codex/hologram/system/symbols.json", "source": "AST/call graph projections"},
            "band:source_span": {"populated_by": "live_computed", "source": "repo Python source lines"},
            "scope:function": {"populated_by": "compiled", "source": "symbol projection entries where kind=function"},
            "facet:body": {"populated_by": "live_computed", "source": "repo Python source lines"}
        },
        "provider_population_lifecycle": {
            "sequence": [
                "select",
                "provider_candidate",
                "row_patch",
                "proof",
                "apply_or_promote_or_reject",
                "projection_rebuild",
                "entry_consumption_probe",
                "probe_disposition"
            ],
            "controller": "tools/meta/control/python_navigation_population_lane.py",
            "proof_gate": "codex/standards/std_navigation_population_acceptance.json",
            "default_provider_posture": "NVIDIA-first when provider-capacity-discovery marks an eligible chat lane; OpenRouter remains pending while discovery reports missing_adapter.",
            "no_direct_mutation": True,
            "population_packet_must_name": [
                "input_scope_id",
                "path",
                "source_fingerprint",
                "span",
                "context_band_supplied",
                "claim_authority",
                "proof_requirements"
            ]
        },
        "adoption_probe_disposition_policy": {
            "summary": "Navigation truth is not established by a green validator alone. Every formal, utility, projection-consumption, or entry-consumption probe must close into one of three durable outcomes.",
            "outcomes": [
                "file_local_defect",
                "standard_amendment_candidate",
                "nothing_to_refine"
            ],
            "file_local_defect": "Use when the target row, provider output, proof bundle, or utility edge is defective under the current standard.",
            "standard_amendment_candidate": "Use when the probe exposes a validator gap, unknown failure class, new policy/grammar boundary, or ambiguity the current standard cannot classify honestly.",
            "nothing_to_refine": "Use only after stewardship_checked, next_best_lane_checked, and a concrete reentry_condition are recorded.",
            "digest_surface": "std_navigation_population_acceptance.json::probe_disposition_contract plus operator digest fields probe_disposition_counts and standard_amendment_candidates.",
            "anti_false_win": "Do not treat formal green, populated projections, or neutral route-probe deltas as adoption proof unless the entry/context-pack consumer and disposition receipt agree."
        },
        "entry_consumption_policy": {
            "entry_packet_must_consume_python_targets": True,
            "exact_file_mentions_route_to": "python_files::file_card",
            "exact_symbol_mentions_route_to": "python_scopes::symbol_capsule",
            "impact_dependency_terms_route_to": "python_scopes graph_context hints plus parent file card",
            "population_gap_terms_route_to": "row_patches cluster/card surfaces before provider dispatch",
            "source_span_rule": "Recommend source-span reads only after the file/scope card or graph context is insufficient for the task."
        },
        "edge_compression_policy": {
            "edge_row_shape": "std_navigation_contract.edge_row_shape",
            "bidirectional_gloss_required": True,
            "first_order_band": "graph_context",
            "second_order_band": "symbol_capsule",
            "beyond_second_order": "omit_with_count_reason_and_drilldown"
        },
        "creator_skill_id": "kernel.std_python_docstring_authoring",
        "navigator_skill_id": "kernel.python_scope_navigation",
        "source_authority": {
            "source": "repo Python files",
            "scope_index": "codex/standards/std_python_scope_index.json",
            "symbol_projection": "codex/hologram/system/symbols.json"
        },
        "currentness_policy": {
            "mode": "generated_scope_index_with_source_spans",
            "rule": "Generated Python projections are browse aids; source spans and freshness/quality warnings decide mutation authority."
        },
        "dependency_neighborhood_policy": {
            "mode": "symbol_graph",
            "rule": "Low bands expose counts/top symbols; graph_context opens callers, callees, related paths, and tests when available."
        },
        "validation_probe": [
            "module rows carry required module docstring tags",
            "public classes/functions carry [ROLE] or [ACTION]",
            "symbol ids, owner ids, and line spans are stable",
            "generated browse fields preserve authored/composed/derived provenance",
            "no navigation band is defined by character truncation alone"
        ]
    },
    "provenance_policy": {
        "summary": "Canonical provenance values for Python browse and navigation fields.",
        "enum": [
            "authored",
            "composed",
            "derived"
        ],
        "field_rule": "Compatibility surfaces should preserve record shape while attaching provenance to enriched fields when available.",
        "notes": "Fallback is part of precedence but not a canonical provenance label; fallback values should be represented as derived output with an accompanying quality/degradation signal."
    },
    "quality_state_policy": {
        "summary": "Canonical degraded-state vocabulary for Python navigation surfaces.",
        "enum": [
            "dirty",
            "stale",
            "suspect",
            "ambiguous",
            "degraded"
        ],
        "field_rule": "Quality states mark reduced trust or incomplete derivation; they do not create new authority.",
        "notes": "Existing warning/status outputs remain valid compatibility surfaces when mapped from these canonical states."
    },
    "emitted_atom_schema": {
        "summary": "Normalized routing atoms emitted from docstrings into the documentation tree, self-model helpers, and the Python scope index.",
        "routing_fields": {
            "when_needed": {
                "source_atom": "When-needed",
                "cardinality": "at_most_one"
            },
            "escalates_to": {
                "source_atom": "Escalates-to",
                "cardinality": "zero_or_more",
                "split_on": ";"
            },
            "navigation_group": {
                "source_atom": "Navigation-group",
                "cardinality": "at_most_one"
            },
            "couples": {
                "source_atom": "Couples",
                "cardinality": "zero_or_more"
            }
        },
        "compatibility_fields": {
            "called_by_concept": {
                "emitted_runtime_field": "inbound_dependents",
                "summary": "The standard may describe inverse call edges as called_by, but emitted compatibility surfaces keep the existing runtime field name inbound_dependents."
            }
        },
        "emission_surfaces": [
            "documentation_tree.files[].module.routing",
            "documentation_tree.files[].classes[].routing",
            "documentation_tree.files[].classes[].methods[].routing",
            "documentation_tree.files[].functions[].routing",
            "scope_index.files[]",
            "scope_index.scopes[]"
        ],
        "browse_enrichment_fields": [
            "browse_summary",
            "search_tokens",
            "signature",
            "owner_symbol_id",
            "related_symbols",
            "inbound_dependents",
            "related_paths",
            "derivation_warnings"
        ]
    },
    "philosophy": {
        "summary": "std_python is the ABI for a self-description loop: files describe themselves, miner audits them, builder compiles them into a wide scope tree plus a deep symbol tree, and apply-time validation proves that edits improved the audited surface.",
        "hologram_doc": "docs/std_python_hologram_philosophy.md",
        "whole_system_index": "codex/hologram/system/scope_tree.json",
        "documentation_tree_artifact": "codex/hologram/system/symbols.json"
    },
    "scope_index": {
        "artifact_path": "codex/standards/std_python_scope_index.json",
        "schema_version": "1.0.0",
        "summary": "Generated scope index for routing atoms across Python file and symbol surfaces.",
        "preferred_match_fields": [
            "when_needed",
            "summary",
            "navigation_group",
            "escalates_to"
        ],
        "browse_role": "Compact file/symbol browse projection for compatibility-first navigation before source reads."
    },
    "documentation_tree": {
        "artifact_path": "codex/hologram/system/symbols.json",
        "schema_version": "1.0.0",
        "entrypoint_names": [
            "main",
            "run",
            "cli",
            "serve",
            "launch",
            "start",
            "execute"
        ],
        "oversized_file_bytes": 500000,
        "symbol_slice_target_count": 12,
        "max_symbol_chunks_per_file": 12,
        "oversized_provider": "chatgpt",
        "default_provider": "chatgpt",
        "default_bridge_workers": 7,
        "observe_symbol_preview_count": 32,
        "observe_toc_symbol_preview_count": 12,
        "provider_prompt_char_caps": {
            "chatgpt": 850000,
            "gemini": 32000
        },
        "provider_chunk_target_chars": {
            "chatgpt": 650000,
            "gemini": 24000
        },
        "legacy_provider_rewrites": {
            "gemini": "chatgpt"
        },
        "provider_population_lanes": {
            "python_navigation_population": {
                "controller": "tools/meta/control/python_navigation_population_lane.py",
                "acceptance_standard": "codex/standards/std_navigation_population_acceptance.json",
                "eligible_provider_source": "provider-capacity-discovery runtime probe",
                "preferred_current_shape": "NVIDIA-first constrained candidate generation when the probe reports eligible lanes; OpenRouter pending adapter repair while reported missing_adapter.",
                "context_rule": "Segment large files before provider use; per-scope provider packets may produce local capsules but not global file/subsystem claims."
            }
        },
        "notes": "Builder and miner should share one symbol/index shape so documentation audits, holographic extraction, and bridge mission chunking all derive from the same AST-grounded facts.",
        "browse_role": "High-fidelity file/symbol semantic tree for symbol capsules and full holographic drilldown."
    },
    "navigation_cache_policy": {
        "artifact_path": "codex/hologram/system/navigation_cache.json",
        "cache_role": "cache_only",
        "authoritative_inputs": [
            "codex/hologram/system/scope_tree.json",
            "codex/hologram/system/symbols.json",
            "codex/standards/std_python_scope_index.json"
        ],
        "forbidden_semantic_behavior": [
            "introduce_unique_semantic_fields",
            "override_authoritative_navigation_contracts",
            "compete_with_scope_tree_or_symbols_as_primary_authority"
        ],
        "notes": "navigation_cache.json may exist as a denormalized acceleration cache, but compatibility-first navigation treats it as fully derived and disposable."
    },
    "runtime_usage_projection": {
        "summary": "Optional runtime salience projected onto Python file/scope browse rows. Direct file run counts are automatic for non-kernel repo-python scripts, while kernel.py first-contact routes opt out by default unless AIW_PYTHON_USAGE_STATS=1 is explicit. Per-function call counts are opt-in because interpreter profiling is expensive. Counts remain evidence for routing, not proof of dead code or semantic importance.",
        "artifact_path": "state/python_usage/python_usage_stats.json",
        "schema_version": "python_runtime_usage_stats_v0",
        "authority_posture": "runtime_observation_projection_not_source_authority",
        "emitter": "sitecustomize.py -> system.lib.python_runtime_usage",
        "activation_surface": "repo-python",
        "function_count_activation": "AIW_PYTHON_USAGE_FUNCTIONS=1",
        "projection_surfaces": [
            "codex/standards/std_python_scope_index.json::__meta.runtime_usage_projection",
            "codex/standards/std_python_scope_index.json::files[].usage",
            "codex/standards/std_python_scope_index.json::scopes[].usage",
            "python_files option surface rows",
            "python_scopes option surface rows"
        ],
        "file_fields": {
            "run_count": "Number of times the file was the direct repo-python entry script when observed.",
            "function_call_count": "Number of repo-local Python call events observed for this file.",
            "last_seen_at": "UTC timestamp of the latest observed run or call.",
            "status": "observed when either count is non-zero, otherwise unobserved."
        },
        "scope_fields": {
            "call_count": "Number of repo-local Python call events observed for this symbol_id.",
            "last_seen_at": "UTC timestamp of the latest observed call.",
            "status": "observed when call_count is non-zero, otherwise unobserved."
        },
        "privacy_policy": {
            "forbidden_fields": [
                "raw argv",
                "source body",
                "environment values"
            ],
            "reason": "Usage projection is a salience map; it must not become a transcript or secret sink."
        },
        "interpretation_policy": {
            "unobserved_means": "No recorded repo-python runtime hit in the current aggregate window.",
            "unobserved_does_not_mean": "safe to delete, unreachable, unused by external callers, or semantically irrelevant.",
            "delete_requires": [
                "reference search",
                "test or route impact check",
                "owning standard or module review"
            ]
        }
    },
    "miner_builder_contract": {
        "analysis_surface": "system.core.analysis.analyze_python_module",
        "self_model_artifact": "codex/hologram/system/scope_tree.json",
        "documentation_tree_artifact": "codex/hologram/system/symbols.json",
        "dirty_source": "documentation_tree.coverage.dirty_paths",
        "validator_policy": "std_python_delta_enforcement"
    },
    "structural_substrate": {
        "summary": "The documentation tree entry for each symbol must carry stable identity, span, and dependency data for caching, invalidation, and context routing.",
        "required_per_function": ["symbol_id", "owner_symbol_id", "line_start", "line_end", "callee_refs"],
        "symbol_id_format": "{repo_relative_path}::{qualified_name}",
        "notes": "symbol_id is globally unique. owner_symbol_id links methods to their class. callee_refs are resolved call targets within the cohort. Spans enable function-scoped dispatch for large files."
    },
    "quality_rubric": {
        "summary": "Five criteria for evaluating bridge-authored documentation quality, derived from Proconsul (annex). Deterministic AST gates run first; LLM judges run after.",
        "criteria": {
            "verbosity": {"check": "heuristic", "severity": "warning", "description": "Excessive words for simple concepts"},
            "triviality": {"check": "heuristic", "severity": "warning", "description": "Restates the function signature or name"},
            "sufficiency": {"check": "ast", "severity": "defect", "description": "Missing required contract atoms for its tag type"},
            "correctness": {"check": "bridge", "severity": "defect", "description": "Claims do not match actual code behavior"},
            "hallucination": {"check": "bridge", "severity": "critical", "description": "References functions, parameters, or behaviors that do not exist"}
        },
        "enforcement_level": "tracked",
        "deterministic_gates_first": True,
        "notes": "AST gates (tag presence, teleology presence, param/return coverage) run before any LLM judge. Proconsul rubric applies after deterministic gates pass."
    },
    "holographic_quality": {
        "summary": "Per-function holographic summaries require a Teleology one-liner as the first content line of [ACTION]. The builder extracts this via _first_signal_line() to populate the documentation tree. Without it, holographic navigation surfaces have unreliable per-function entries.",
        "teleology_required_in_action": True,
        "teleology_format": "First non-empty line of [ACTION] (after dash-stripping) must start with 'Teleology:'",
        "extraction_mechanism": "system.lib.python_documentation_tree._first_signal_line",
        "quality_metric": "teleology_coverage",
        "enforcement_level": "tracked",
        "notes": "Tracked as a quality metric via the hygiene tool, not as a compliance gate (yet). Once coverage exceeds 90%, consider promoting to a compliance requirement."
    },
    "bridge_authoring_lane": {
        "summary": "Safe delegated lane for Python documentation work: `worker_surface=bridge` is the default reusable meta-mission posture, while `worker_surface=subagent` reuses the same batching/context groundwork for tool-using delegated workers. The default gate is the `preview_first_autonomous_proof_gate` defined in `codex/standards/std_navigation_population_acceptance.json`: deterministic AST + parser + projection + route-probe verifiers decide bounded green changes; the operator is escalated to only on red conditions (semantic code edit, import/test/runtime edit, new grammar, unresolved target after retry, possible secret/privacy exposure, high blast radius, validator-inconclusive, repeated rollback). Routing routine bounded validation work to the operator is the named anti-pattern `human_as_validator_bottleneck`; build the validator or quarantine the work instead.",
        "orientation_index": "codex/hologram/system/scope_tree.json",
        "default_timeout_s": 300,
        "resume_timeout_s": 180,
        "resume_provider": "chatgpt",
        "default_worker_surface": "bridge",
        "allowed_worker_surfaces": [
            "bridge",
            "subagent"
        ],
        "preferred_subagent_model": "gpt-5.4-mini",
        "subagent_model_policy": {
            "default_model": "gpt-5.4-mini",
            "allow_smaller_models": True,
            "require_explicit_override_for_larger_models": True,
            "notes": "For `worker_surface=subagent`, use `gpt-5.4-mini` or a smaller model unless the conductor explicitly asks for something larger. If a finished worker's model provenance is unknown or larger than the preferred model, review and retire it before launching the next cohort."
        },
        "worker_surface_notes": {
            "bridge": "Injected-context, one-shot bridge worker. Uses provider/runtime settings and observe-session execution.",
            "subagent": "Scoped tool-using delegated worker. Reuses the same cohort/context prep, but bridge provider/runtime settings are advisory only and the actual execution happens in the IDE agent runtime.",
            "provider_harness": "Hosted provider call through a Type A controller harness. It receives only the bounded packet, returns receipt/row_patch candidates, and never receives source mutation or standard-authoring authority."
        },
        "provider_population_lane_ref": "navigation_contract.provider_population_lifecycle",
        "orientation_artifacts": [
            "codex/hologram/system/scope_tree.json",
            "codex/hologram/system/symbols.json"
        ],
        "probe_orientation_artifact_basename": "documentation_tree_probe_context.json",
        "compact_orientation_artifact_basename": "documentation_tree_context.json",
        "required_context_files": [
            "codex/standards/std_python.py",
            "codex/standards/std_apply.json",
            "codex/doctrine/skills/kernel/apply.md"
        ],
        "probe_context_files": [
            "docs/std_python_hologram_philosophy.md",
            "codex/standards/std_python.py",
            "codex/standards/std_apply.json",
            "codex/doctrine/skills/kernel/apply.md"
        ],
        "synthesis_context_files": [
            "docs/std_python_hologram_philosophy.md",
            "codex/standards/std_python.py",
            "codex/standards/std_apply.json",
            "codex/doctrine/skills/kernel/apply.md"
        ],
        "allowed_apply_ops": [
            "update_docstring",
            "inject_tag"
        ],
        "forbidden_mutations": [
            "semantic_code_edit",
            "import_edit",
            "test_edit",
            "commit"
        ],
        "review_gate": "preview_first_autonomous_proof_gate",
        "review_gate_contract": "codex/standards/std_navigation_population_acceptance.json",
        "review_gate_classification": {
            "green_auto_apply": "All deterministic verifiers pass, source_fingerprint matches, symbol_id resolves, all Escalates-to targets resolve, navigation_group is known, std_python atom parser passes, python syntax preserved, projection rebuild passes, route probe improves or is neutral, rollback materialized, no policy or semantic change.",
            "amber_auto_retry": "Weak trigger language, underanchored but plausible claim, provider disagreement, nonfatal style defect, ambiguous but resolvable target. Retry with stronger independent verifier; downgrade to red on exhausted retries.",
            "red_operator_escalation": "Semantic code edit, import or runtime edit, test edit, new standard grammar, new cross-lattice target type, unresolved target after retry, possible secret or privacy exposure, high blast radius, validator cannot prove grounding, repeated rollback or regression."
        },
        "operator_role": "exception escalation only; reads daily/periodic digest of accepted/rejected/rollback counts, top failure classes, skill deltas proposed, validator gaps found, and policy questions; does not review per-row routine green changes",
        "preferred_review_artifacts": [
            "compiled_apply_plan.json",
            "apply_preview.json"
        ],
        "apply_target_family": "python_std_python_enforcement",
        "cohort_selection_surface": "codex/hologram/system/scope_tree.json::coverage.python.dirty_paths",
        "structural_substrate_policy": "structural_substrate",
        "quality_rubric_policy": "quality_rubric"
    }
}

class StandardReference:
    """
    [ROLE]
    - Teleology: A dummy class to demonstrate the [ROLE] tag requirement.
    - Mechanism: Does nothing; exists purely to pass the Miner's audit.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        self._config = config
        self._buffer: List[str] = []

    def execute_transaction(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        [ACTION]
        - Teleology: A dummy method to demonstrate the [ACTION] tag requirement.
        - Fails: None (Abstract method).
        - Guarantee: Returns a dict (Type hint enforcement).
        """
        return {}

def atomic_write_operation(path: str, content: str) -> bool:
    """
    [ACTION]
    - Teleology: A dummy function to demonstrate the [ACTION] tag requirement.
    - Fails: None.
    - Guarantee: Returns True.
    """
    return True
