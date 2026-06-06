# Microcosm Engine Room Demo Refine Instance

Use this public-safe skill when `std_microcosm_engine_room_demo` declares the `refine_instance` triad route for `engine_room_demo`. It is a governed route source for the declared skill id. It does not upgrade the standard from `public_microcosm_standard_v1` / `accepted_public_runtime_standard`, prove runtime correctness, authorize release, publication, provider calls, private-body export, source mutation, or whole-system correctness.

## Typed Skill Mapping

```json
{
  "triad_role": "refine_instance",
  "operates_standard": "std_microcosm_engine_room_demo",
  "acts_on_kind": "engine_room_demo",
  "trigger_summary": [
    "The Engine Room demo standard declares this refine instance skill id with status planned.",
    "A governed skill source row is needed before standard.owns_triad.skill can resolve without treating generated projections as authority."
  ],
  "workflow_summary": [
    "Read std_microcosm_engine_room_demo JSON, its authority ceiling, validator refs, receipt refs, and lattice health before editing engine_room_demo artifacts.",
    "Tighten an existing instance without widening its authority ceiling, weakening validator expectations, or treating receipt presence as proof of runtime correctness.",
    "Regenerate the skill corpus and preserve missing mechanism or concept neighbours as residual pressure unless a source mapping names them."
  ],
  "concept_refs": [
    "concept.import_projection_and_drift_control_bundle"
  ],
  "mechanism_refs": [
    "mechanism.engine_room_demo.validates_public_engine_room_demo"
  ],
  "mapping_basis": "The standard JSON at standards/std_microcosm_engine_room_demo.json declares this refine_instance skill route for engine_room_demo, and core/organ_atlas.json::engine_room_demo names mechanism_refs=mechanism.engine_room_demo.validates_public_engine_room_demo and concept_refs=concept.import_projection_and_drift_control_bundle. This source mapping binds the skill to those accepted organ neighbours without inferring from prose, generated projections, endpoint coverage, or release claims."
}
```

## Authority Boundary

This skill binds a declared triad route to a governed skill source row. It does not make the standard active, complete, or accepted beyond the standard source status, and it does not infer concept or mechanism neighbours not named in this skill mapping.

Anti-claims:

- A resolved triad skill edge is route coverage, not runtime proof.
- Planned standard skill ids remain bounded by the standard authority ceiling and validation receipts.
- Generated lattice projections are not source evidence for release, capability, or correctness claims.
