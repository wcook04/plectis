# Microcosm Public Reveal Walkthrough Author

Use this public-safe skill when `std_microcosm_public_reveal_walkthrough` declares the `author` triad route for `public_reveal_walkthrough`. It is a governed route source for the declared skill id. It does not upgrade the standard from `public_microcosm_standard_v1` / `draft`, prove runtime correctness, authorize release, publication, provider calls, private-body export, source mutation, or whole-system correctness.

## Typed Skill Mapping

```json
{
  "triad_role": "author",
  "operates_standard": "std_microcosm_public_reveal_walkthrough",
  "acts_on_kind": "public_reveal_walkthrough",
  "trigger_summary": [
    "The Public reveal walkthrough standard declares this author skill id with status planned.",
    "A governed skill source row is needed before standard.owns_triad.skill can resolve without treating generated projections as authority."
  ],
  "workflow_summary": [
    "Read std_microcosm_public_reveal_walkthrough JSON, its authority ceiling, validator refs, receipt refs, and lattice health before editing public_reveal_walkthrough artifacts.",
    "Author only source-backed public fields for the governed instance, including authority boundary, validator expectations, receipt expectations, and anti-claims.",
    "Regenerate the skill corpus and preserve missing mechanism or concept neighbours as residual pressure unless a source mapping names them."
  ],
  "concept_refs": [
    "concept.entry_and_reveal_route_readiness_bundle"
  ],
  "mechanism_refs": [
    "mechanism.public_reveal_walkthrough.validates_public_reveal_walkthrough"
  ],
  "mapping_basis": "The standard JSON at standards/std_microcosm_public_reveal_walkthrough.json declares this author skill route for public_reveal_walkthrough, and core/organ_atlas.json::public_reveal_walkthrough names mechanism_refs=mechanism.public_reveal_walkthrough.validates_public_reveal_walkthrough and concept_refs=concept.entry_and_reveal_route_readiness_bundle. This source mapping binds the skill to those accepted organ neighbours without inferring from prose, generated projections, endpoint coverage, or release claims."
}
```

## Authority Boundary

This skill binds a declared triad route to a governed skill source row. It does not make the standard active, complete, or accepted beyond the standard source status, and it does not infer concept or mechanism neighbours not named in this skill mapping.

Anti-claims:

- A resolved triad skill edge is route coverage, not runtime proof.
- Planned standard skill ids remain bounded by the standard authority ceiling and validation receipts.
- Generated lattice projections are not source evidence for release, capability, or correctness claims.
