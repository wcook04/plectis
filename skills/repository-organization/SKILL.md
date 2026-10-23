---
name: repository-organization
description: Use for folder organization, placing new files, tree moves or new file families. Consult local directory roles, preserve published and installed interfaces, and run the executable worktree and staged layout gates.
---

# Repository organization

Read this repository's entry, README, package configuration and directory owners.
`docs/maintainers/repository-layout.json` declares the root interfaces, directory responsibilities,
required owners, executable route checks and documented compatibility exceptions.
Choose a file's home by its consumer; do not split folders merely because of counts.

Preserve imports, CLI names, published links, installed resources, generated provenance
and historical evidence. Before moving a path, inspect its consumers and write an
old-to-new mapping. Edit source owners before rebuilding generated files. Use the
repository's existing architecture workflow if an ownership boundary changes.

Update the README map and concrete role policy with a deliberate new interface or
family. A placement exception needs its exact path and reason; do not exempt a whole
future family to make a check pass. Keep executable commands under their tool owner,
tests under their test owner, and documentation assets beside their guides.

From the repository root:

```sh
python3 skills/repository-organization/scripts/check_layout.py --config docs/maintainers/repository-layout.json
python3 skills/repository-organization/scripts/test_check_layout.py
# After staging the exact owned paths:
python3 skills/repository-organization/scripts/check_layout.py --config docs/maintainers/repository-layout.json --index
```

The working check sees tracked and nonignored untracked files, excluding files deleted
from the working tree. The index check reads staged paths, policy and route contents.
Both use NUL-delimited Git candidates and never descend into ignored build trees.
CI runs the same gate and negative fixtures. Keep existing hooks and hooksPath.
Run the affected behavior and packaging checks, then commit only owned paths.

The portable check and fixtures are copied from the repository-organization skill
asset; project roles remain local. No private runtime or sibling checkout is required.

## Add a folder for your purpose

Create folders that suit this project. Ordinary reversible folder additions and
purpose declarations need no new approval. Add a `directories` entry in the local
policy, for example `"field-notes": {"purpose": "Instrument observations and supporting material"}`.
Update the README map when this becomes a maintained part of the project.

`undeclared_directories: "warn"` reports new folders without blocking them.
Projects may choose `"error"` to require declaration before landing; older policies
without this setting remain strict. Declared placement constraints, required
owners, root interfaces and route checks still apply in either mode. There is no
universal folder template. Suffix restrictions are optional project decisions.

The `repository_layout@2` policy accepts nested declarations such as
`field-notes/instruments`. The deepest declaration explains the local purpose;
all ancestor placement constraints still hold. An optional `guide` names an
existing repository-relative owner document, checked in the same Git view.
Do not use broad exceptions to introduce a legitimate new purpose.

Preserve a local lesson in this workflow and a regression fixture. Generalise the
reusable rule into the canonical skill or helper when evidence supports it, while
keeping this project's folder names and purposes local. Existing skill registries
and builders remain the owners of routing and generated mirrors.
