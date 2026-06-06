# Microcosm Route Lease Refine Standard And Propagate

Use this public-safe skill when `std_microcosm_route_lease` declares the `refine_standard_and_propagate` triad route for `route_lease`. It is a governed route source for the declared skill id. It does not upgrade the standard from `public_microcosm_standard_v1` / `draft`, prove runtime correctness, authorize release, publication, provider calls, private-body export, source mutation, or whole-system correctness.

## Typed Skill Mapping

```json
{
  "triad_role": "refine_standard_and_propagate",
  "operates_standard": "std_microcosm_route_lease",
  "acts_on_kind": "route_lease",
  "trigger_summary": [
    "The Route lease standard declares this refine standard and propagate skill id with status planned.",
    "A governed skill source row is needed before standard.owns_triad.skill can resolve without treating generated projections as authority."
  ],
  "workflow_summary": [
    "Read std_microcosm_route_lease JSON, its authority ceiling, validator refs, receipt refs, and lattice health before editing route_lease artifacts.",
    "Change the source standard only with reusable evidence, then propagate through governed instances, validators, receipts, generated skill corpus, and lattice projections.",
    "Regenerate the skill corpus and preserve missing mechanism or concept neighbours as residual pressure unless a source mapping names them."
  ],
  "concept_refs": [
    "concept.agent_reliability_and_safety_validator_bundle",
    "concept.architecture_and_navigation_route_contract_bundle"
  ],
  "mechanism_refs": [
    "mechanism.agent_route_observability_runtime.validates_public_route_feedback",
    "mechanism.navigation_hologram_route_plane.validates_public_route_plane_bundle"
  ],
  "mapping_basis": "The standard JSON at standards/std_microcosm_route_lease.json declares this skill route; relationships.used_by_organs=[\"agent_route_observability_runtime\", \"navigation_hologram_route_plane\"] names organ atlas rows whose mechanism_refs=[\"mechanism.agent_route_observability_runtime.validates_public_route_feedback\", \"mechanism.navigation_hologram_route_plane.validates_public_route_plane_bundle\"] and concept_refs=[\"concept.agent_reliability_and_safety_validator_bundle\", \"concept.architecture_and_navigation_route_contract_bundle\"] are the source basis for these selective skill edges. This binds only source-declared lattice neighbours and does not prove runtime correctness, release readiness, provider authority, private-body coverage, or whole-system completeness."
}
```

## Authority Boundary

This skill binds a declared triad route to a governed skill source row. It does not make the standard active, complete, or accepted beyond the standard source status, and it does not infer concept or mechanism neighbours not named in this skill mapping.

Anti-claims:

- A resolved triad skill edge is route coverage, not runtime proof.
- Planned standard skill ids remain bounded by the standard authority ceiling and validation receipts.
- Generated lattice projections are not source evidence for release, capability, or correctness claims.
