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
