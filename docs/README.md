# Plectis documentation

Deeper documentation than the front door. Start at the repository
[README](../README.md); come here when you need the maintainer lanes or the
project plans.

## Maintainers

- [Validation runbook](maintainers/validation.md): the full smoke card set,
  pytest isolation detail, the drift-detection lane, reviewer proof packets,
  and standalone export.
- [Security runbook](maintainers/security-runbook.md): local checks before
  reporting and the release-authority receipt boundary.
- [CLI decomposition plan](maintainers/cli-decomposition.md): the owned plan
  for splitting the monolithic command module.
- [Root migration plan](maintainers/root-migration-plan.md): the owned plan
  for moving the remaining root documents (generated atlas docs and doctrine
  sources) under `docs/` without breaking their builders, validators, and
  packaging.

## Reference (currently at the repository root)

The generated reference surfaces live at the root today and are
builder-owned: [System map](../ORGANS.md), [Architecture](../ARCHITECTURE.md),
[Agent task routes](../AGENT_ROUTES.md), [First action demo](../FIRST_ACTION.md),
and [Release review](../RELEASE_REVIEW.md). The root migration plan tracks
moving them here.
