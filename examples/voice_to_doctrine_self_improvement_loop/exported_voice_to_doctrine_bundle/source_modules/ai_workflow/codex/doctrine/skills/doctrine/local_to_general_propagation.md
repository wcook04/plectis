---
id: "local_to_general_propagation"
kind: "meta"
skill_type: "propagation"
family: "doctrine"
title: "Local-to-General Propagation"
summary: "Atom entrypoint split from an over-budget skill body. Read this file first, then open only the child detail band selected by the current task."
triggers:
  - "Need Local-to-General Propagation"
  - "A local navigation fix should generalize into compressed entry, routing, docs-route, or standard surfaces"
  - "A Codex autonomous-seed mission says self-propagate, generalized self-propagation, pair propagation, propagation outcome, refinement_result, or nothing_to_refine"
  - "A local failure, route miss, repeated workaround, stale projection, or agent confusion might represent a reusable failure class"
  - "Mechanism/WorkItem boundary confusion appears: should mechanisms merge with WorkItems, mechanisms describe work, or mechanism pressure should cluster WorkItems"
focus_paths:
  - codex/doctrine/skills/doctrine/local_to_general_propagation.md
doc_links:
  - codex/doctrine/skills/doctrine/local_to_general_propagation_metadata_and_entry_context.md
  - codex/doctrine/skills/doctrine/local_to_general_propagation_plane_home_decision_table.md
  - codex/doctrine/skills/doctrine/entry_point_projection_care.md
  - codex/doctrine/mechanisms/mech_034_failure_class_propagation_packet.json
  - codex/standards/std_uppropagation_intake.json
  - codex/standards/std_task_ledger.json
  - codex/standards/principles/std_mechanism.json
doctrine_edges:
  concepts: [con_001, con_028]
  mechanisms: [mech_019, mech_034]
  principles: [pri_111, pri_088, pri_049, pri_080, pri_016, pri_134, pri_139]
composes_with:
  - local_to_general_propagation_metadata_and_entry_context
  - local_to_general_propagation_plane_home_decision_table
name: "local-to-general-propagation"
description: "Atom entrypoint for Local-to-General Propagation; select a child band, use mech_034 for failure-class packets, and preserve mechanism/WorkItem boundaries when affinity pressure should generalize."
---
<!-- registry: skill_registry.json -> local_to_general_propagation | family: doctrine -->

## Purpose

This is the cold-entry atom for `local_to_general_propagation`. The prior monolithic skill exceeded the entrypoint-health budget; its load-bearing detail now lives in child skill files under the same family directory.

## Mission Propagation Verbs

For autonomous-seed work, `self-propagate`, generalized self-propagation, and pair propagation mean: route the local lesson into the smallest durable owner surface, then patch that surface when the owner is known and the write is safe. Close with `refined_existing_surface`, `workitem_captured`, or a stewardship-proven `nothing_to_refine`. `workitem_captured` is a residual lane, not the default outcome: use it only when the owner surface is unsafe, blocked, not yet discoverable, or the operator explicitly asked for capture/record-only bookkeeping. A null closeout is valid only when the pass checked stewardship and next-best bounded substrate-care lanes, or recorded the exact blocker/follow-up. If the request also mentions the Codex app queue, open `type_a_autonomous_seed_loop` and `std_autonomous_seed_prompt` first so the receiver treats queued prompts as mission delivery, not automation.

When the same request asks for subagents or sidecars, use them as bounded evidence scouts or disjoint implementation slices, not as the propagation result. The receiving Type A thread still owns the plane-home decision, path claims, source mutation or already-propagated proof, validation receipt, and closeout wording.

Native worker availability is not a completion gate. If a requested subagent or sidecar is unavailable, saturated, late, or no longer needed after controller-owned validation, continue through the smallest viable Type A/Type B lane and record the condition only when it blocks an owned gate or changes reusable delegation policy. For standards/compliance waves, the scanner, adapter, ledger refresh, and route proof are the deliverables; optional worker scouting must not hold the propagation closeout open.

For standards-compliance propagation, prefer an existing owner check before writing a new rule. If a standard already has a builder/checker pair such as `check_navigation_type_plane()`, project that checker into a read-only compliance adapter and let the ledger surface `stale_projection`, `refresh_needed`, `missing_required_field`, or `schema_violation` findings. Do not duplicate drift logic in the adapter when the owner tool already knows how to rebuild or validate the generated projection. If a standard names a scanner but `compliance_ledger` still reports `baseline_inventory_only`, treat that as a source-to-registry handoff: implement/register the adapter and focused tests, then refresh the generated ledger instead of hand-editing it. A subagent may scout candidate standards and owner checks, but the controller owns the adapter, registry wiring, generated refresh, and route proof.

When a standards-compliance scout proposes a broad Atlas-facing scanner but the owner projection already reports source-coupling or generated-output drift, first ask whether a narrower adjacent standard can land cleanly through an existing owner check. Land the clean scanner when it materially improves the shared ledger, cite or capture the broader dirty projection as a residual, and do not use the scout recommendation as permission to hand-edit generated Atlas state.

For Atlas/Kind-Atlas navigation-contract compliance, do not only classify rows as declared versus missing. If a governing standard already carries a top-level `navigation_contract`, have the audit discover it through the Kind Atlas `governing_standard_refs`, then classify shape quality separately as `declared`, `declared_incomplete`, or `missing`. This lets Atlas reduce false missing-contract debt without over-trusting shallow stubs that do not satisfy `std_navigation_contract.required_contract_fields`.

## Owner-Surface Actuation Floor

Propagation debt is not consumed by recording that a lesson exists. If the row names an owner surface, Type A must inspect that owner and either:

1. patch or run the owner mutation lane, then record the propagation/signoff receipt;
2. prove the owner already contains the lesson and record `already_propagated_verified` with exact evidence; or
3. prove the owner patch is unsafe, blocked, or outside the current authority boundary, then capture or block that residual with the re-entry condition.

Do not answer a request to continue, consume, actuate, or work a propagation queue by appending caps or propagation records only. Caps preserve unlanded work; they do not replace the source, standard, skill, route, checker, projector, or code edit that the propagation lesson calls for. A record-only batch is valid only when the operator explicitly asks for bookkeeping or when current-state inspection proves there is no safe owner edit to make.

## Null-Pass / Next-Best Useful Action

Use this band when a pass is about to say `nothing_to_refine`, `already_settled`, `no clean high-value lane`, or any equivalent no-op verdict after bookkeeping, validation, or threshold checks.

A Type A pass may not return a second consecutive null/no-op/settlement-only closeout on the same teleology without broadening to the next bounded substrate-care lane. Ask what the operator was actually trying to improve, then act on the next safe owner surface: propagation, validation ergonomics, projection hygiene, generated-state correctness, context-window safety, concurrency/resource pressure, route discoverability, hidden mutation audit, closeout truthfulness, or operator-friction repair. Stop only when those lanes are unsafe, claimed, policy-bound, or genuinely absent, and name the exact re-entry condition.

Settlement is not refinement. Generated-state, Work Ledger, Task Ledger, or other ledger settlement may set `settlement_done` and `validation_done`; it must not set or imply `refinement_done` unless the pass patched an owner surface, recorded a WorkItem/CAP, or otherwise left a durable improvement beyond settlement. Before saying `nothing_to_refine`, check whether settlement revealed missing source-bundle coverage, omitted audit/source sidecars, owner-tool contract gaps, projection tails, repeated operator-friction, or manual operator challenge. If yes, patch or capture; if no, say what was checked.

## Failure-Class Packet

If the local lesson is a failure, repeated workaround, route miss, stale projection, or agent confusion, do not jump straight from symptom to doctrine. Open `codex/doctrine/mechanisms/mech_034_failure_class_propagation_packet.json` and packetize: local case, failure class, evidence refs, sibling surfaces checked, owner surface, mutation or capture lane, overgeneralization guard, currentness boundary, validation receipt, stop condition, and outcome. The valid outcomes are owner mutation, up-propagation intake, Task Ledger capture, PEER candidate, already-propagated proof, or residual-free `nothing_to_refine` with explicit stewardship/next-best-lane evidence.

## Mechanism / WorkItem Boundary Lessons

When the local lesson says mechanisms are describing work, asks whether mechanisms and WorkItems should merge, or needs WorkItems clustered by mechanism pressure, treat it as cross-authority routing before doctrine mutation.

1. Preserve the authority split: mechanisms own reusable how-patterns and doctrine/code behavior; WorkItems own execution rows, event history, dispositions, and commitment state.
2. Open the compressed lens before inventing a new artifact class:

```bash
./repo-python kernel.py --option-surface mechanisms --band flag
./repo-python kernel.py --option-surface mechanisms --band card --ids <mech_id>
./repo-python kernel.py --option-surface task_ledger --band cluster_flag --ids mechanism:<mech_id>
./repo-python kernel.py --option-surface task_ledger --band cluster_flag --ids mechanism:unclassified_pressure
```

3. If a cluster exists, shape, note, retire, bind, or validate the existing WorkItems through Task Ledger events. Do not mint a parallel mechanism backlog.
4. If the cluster lens is missing or confusing, refine `std_task_ledger.json`, `std_mechanism.json`, `std_agent_entry_surface.json`, and the relevant routing surfaces before closing.
5. If no reusable system behavior remains after those checks, close as `nothing_to_refine` and name the checked surfaces.

## Child Bands

| Need | Open |
|---|---|
| Metadata and entry context | `codex/doctrine/skills/doctrine/local_to_general_propagation_metadata_and_entry_context.md` |
| Plane-home decision table | `codex/doctrine/skills/doctrine/local_to_general_propagation_plane_home_decision_table.md` |
| Stable route or entry-surface projection failure | `codex/doctrine/skills/doctrine/entry_point_projection_care.md` |
| Failure-class packet shape | `codex/doctrine/mechanisms/mech_034_failure_class_propagation_packet.json` + `codex/standards/std_uppropagation_intake.json::failure_class_propagation_packet_contract` |
| Mechanism / WorkItem boundary refinement | this parent skill + `codex/doctrine/skills/task_ledger/task_ledger_metacontrol_uppropagation.md` + `codex/standards/std_agent_entry_surface.json::cross_authority_affinity_route_contract` |

## Minimum Rule

Open the smallest child band that matches the task. Do not read all children by default, and do not copy child detail back into this parent. The parent is the route selector; the child files are the evidence and procedure bands.
