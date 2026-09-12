# Provenance

Plectis is an independent, AI-assisted solo project by William Cook. The public
release artifact is the standalone Plectis repository and its generated
standalone export, not the private `ai_workflow` macro root.

The former public name was Microcosm. It is retained only as a bounded
compatibility and historical label for old links, the `microcosm_core` import
path, the legacy `microcosm` command alias, `.microcosm/` local state, fixture
names, schema names, and frozen receipts.

The project was developed with human direction, selection, review, and
integration by William Cook. AI coding and research tools were used as
assistants during development. Tool and provider names are descriptive only;
Plectis is not affiliated with, sponsored by, or endorsed by OpenAI, Anthropic,
Anysphere/Cursor, the University of Bristol, or any other third party named
descriptively in development records.

## Release Boundary

- Released artifact: the standalone Plectis repository/export.
- Compatibility labels: Microcosm names may remain in package internals,
  historical routes, receipts, fixtures, and schema identifiers where renaming
  would break reviewability or existing local use.
- Not released: private macro-root state, raw seed, private ledgers, browser or
  provider state, account/session material, credentials, recipient-send state,
  private personal data, and any unexported internal annex material.
- License: Apache License, Version 2.0, as carried by [LICENSE](LICENSE).
- Copyright notice: `Copyright 2026 William Cook`.
- Development history: commits in this repository, source files, and the import
  records described below. [Release review](RELEASE_REVIEW.md) links the saved
  command results and explains how to reproduce the listed runs.

## Follow one imported file

The [import ledger](core/substrate_substitution_ledger.json) describes which
components use copied files, adapted files, or validators over example inputs.
For `pattern_binding_contract`, its `source_module_manifest_refs` field links
to [this file manifest](examples/pattern_binding_contract/exported_substrate_bundle/source_module_manifest.json).
Each row in the manifest describes one included file and records its original
path, public copy path, and hashes.

For example, the row named
`pattern_binding_route_readiness_validator_tool_body_import` points to
[this copied Python validator](examples/pattern_binding_contract/exported_substrate_bundle/source_artifacts/macro_tool/tools/meta/factory/check_extracted_pattern_route_readiness.py).
Its `path` is relative to the manifest's directory. `target_sha256` is the
recorded SHA-256 hash of the public copy. The older `target_ref` includes the
former `microcosm-substrate/` directory prefix; use `path` to find the file in
this clone.

You can compare that one public file with its recorded hash from the clone root
with Python 3.11 or newer. No package installation is needed; the command reads
the two files and prints the comparison without writing output files:

```bash
python3 - <<'PY'
import hashlib
import json
from pathlib import Path

manifest = Path("examples/pattern_binding_contract/exported_substrate_bundle/source_module_manifest.json")
rows = json.loads(manifest.read_text())["modules"]
row = next(r for r in rows if r["module_id"] == "pattern_binding_route_readiness_validator_tool_body_import")
target = manifest.parent / row["path"]
matches = hashlib.sha256(target.read_bytes()).hexdigest() == row["target_sha256"]
print(f"target_hash_matches: {matches}")
raise SystemExit(0 if matches else 1)
PY
```

At public commit `27c537e6`, this prints `target_hash_matches: True` and exits
with code 0. A different hash prints `False` and exits with code 1. This compares
one file with one saved hash; it does not establish that every import record
matches the current public files.

The `source_ref`, `source_sha256`, and `source_to_target_relation` fields record
the stated private origin and import relationship. A reader without the private
original can inspect that account and the public copy, but cannot independently
compare the copy with the private original. Hash equality also does not
establish authorship or permission to copy; the licensing and attribution
requirements below still apply.

## Third-Party Material

The public repository may contain package dependencies, generated receipts,
fixtures, source capsules, or documentation references. Included dependencies,
copied source files, datasets, media assets, fonts, screenshots, or copied text
must keep the license and attribution obligations that apply to that included
material.

Pattern-level inspiration, public documentation read during development, and
AI-assisted research do not by themselves make the private macro system or
external reference projects part of this public release. If copied or lightly
adapted third-party expression is ever added, treat it as third-party material
until it is removed, rewritten, or licensed and attributed.

## Public Claims

Plectis is a research prototype and developer tool. It is provided for
inspection, experimentation, and education. It is not a hosted service,
production security product, proof-correctness authority, financial or
investment advice system, trading system, medical/legal/professional advice
system, or claim of endorsement by any tool provider or institution.

Examples and fixtures are synthetic or public-safe unless a file explicitly says
otherwise. Market, prediction, or trading examples are illustrative evidence
boundaries only; they are not recommendations to buy, sell, hold, trade, or rely
on any financial instrument, market, prediction market, or strategy.
