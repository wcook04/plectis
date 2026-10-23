# Try one operation

Python 3.11 or newer is enough. From the clone root:

```sh
PYTHONPATH=src python3 examples/operations/evaluation.py --format text
```

The example changes one scoring rule. It reuses eight results, reruns three
tasks, blocks one external action and rejects a stale worker's publication.
The short summary shows the decisions; omit `--format text` for detailed JSON. It uses a temporary
folder and makes no model or network calls. Add `--out /path/to/result.json`
if you want to keep its observations.

Read the [walkthrough](../../docs/guides/verification-study.md) for interpretation.
The ordinary dependency cache makes the same decisions in this fixture; it is
not a performance benchmark.

## Use it in your own program

Install this checkout in your own environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/python examples/operations/evaluation.py
```

On Windows use `.venv\Scripts\python.exe`. Import the one operation you need:

```python
from plectis.repair import make_plan

# input -> score -> external action
# The score changed; input is still usable.
dirty, blocked = make_plan([[], [0], [1]],
                           [False, True, False],
                           [False, False, True])
assert dirty == (False, True, True)
assert blocked == (False, False, True)
```

- [Repair API](../../docs/guides/repair.md): graph decisions and an optional
  synchronous callback host.
- [Publish API](../../docs/guides/publish.md): SQLite result publication and retry
  history. Import `from plectis.publish import PublishStore`.
- [Compatibility API](../../docs/guides/compatibility.md): compare declared
  transition models. Import `from plectis.compatibility import compare`.

For source reuse you may copy `src/plectis` with its generated subpackages and
licence files, plus the root `LICENSE` and `NOTICE`; it needs neither
`microcosm_core` nor installed package metadata for these APIs. Keep `formal/`
and the corresponding check scripts if you want to recheck or change proofs.
The old CLI aliases require the reference toolkit and are separate from these
imports. Tests exercise this copy-only arrangement in a fresh no-pip environment.
Retain attribution and review the [licensing record](../../PROVENANCE.md).

## Development checks

```sh
make operations-test
make verify-operations DAFNY=/absolute/path/to/dafny
make package-smoke
```

The last command installs into a fresh environment and exercises the operations
outside the checkout. The [formal guide](../../formal/README.md) separates
proof rechecking, generated-byte binding and ordinary integration tests.
