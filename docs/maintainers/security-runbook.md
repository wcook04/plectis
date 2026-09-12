# Security runbook (maintainers and reporters)

Use this runbook to reproduce a reported result and identify the file,
matching rule, or permission field involved. [SECURITY.md](../../SECURITY.md)
gives the private reporting instructions and what to include in a report.

<a id="local-checks-before-reporting"></a>
## Set up from the repository root

The commands below require Python 3.11 or later. Start in the checkout's root
directory, beside `pyproject.toml` and `bootstrap.sh`:

```bash
./bootstrap.sh
VENV=/tmp/plectis-security-venv make install
```

`bootstrap.sh` runs the cold-clone probe and writes ignored
`.microcosm/cold_clone_probe.json` evidence. It does not refresh tracked
receipts. `./bootstrap.sh --dry-run` prints the probe command without running
it or writing a receipt. `make install` creates the named virtual environment
if absent, upgrades its pip, and installs this checkout with the test extras.

Without `make`, create the environment and install the same extras directly:

```bash
python3 -m venv /tmp/plectis-security-venv
/tmp/plectis-security-venv/bin/python -m pip install -e '.[test]'
```

## Scan the checkout for declared text tokens

This command reads the checkout's scan policy and writes a JSON result outside
the checkout:

```bash
PYTHONPATH=src /tmp/plectis-security-venv/bin/python -m microcosm_core.validators.secret_exclusion_scan --root . --out /tmp/plectis-security-scan.json
/tmp/plectis-security-venv/bin/python -m json.tool /tmp/plectis-security-scan.json
```

The policy is
[core/private_state_forbidden_classes.json](../../core/private_state_forbidden_classes.json).
The scanner searches for its declared synthetic tokens using case-sensitive
substring matching. The
[validator](../../src/microcosm_core/validators/secret_exclusion_scan.py)
selects files; the
[text scanner](../../src/microcosm_core/private_state_scan.py) applies these
rules:

- Read UTF-8 files ending in `.json`, `.jsonl`, `.lean`, `.md`, `.py`, `.sh`,
  `.toml`, or `.txt`, and files named `Dockerfile`, `LICENSE`, `Makefile`, or
  `NOTICE`.
- Skip symbolic links and directories named `.git`, `.microcosm`,
  `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.venv`,
  `build`, `dist`, `microcosm-substrate`, or `node_modules`. Also skip
  directories ending in `.egg-info`, `.pyc` and `.pyo` files, and `.DS_Store`.
- Record token matches in the policy file, files named
  `private_state_forbidden_terms.json`, and `tests/` paths as expected
  negative cases. For paths containing `pattern_binding_contract/input`,
  this exception also requires one of the text markers listed in
  `SYNTHETIC_NEGATIVE_MARKERS` in the text scanner. A negative case remains in
  the results but does not block a pass.
- Record an unreadable or invalid UTF-8 candidate file as a blocking finding.

The command exits `0` when `status` is `pass`, or `1` when the scan returns a
blocked status. In the JSON, inspect `secret_exclusion_scan.scanned_path_count`,
`hit_count`, `blocking_hit_count`, and `hits`. Each hit names a path, term ID,
class, and suggested action; it omits the matched body. `pass` means there
were no blocking findings in the visited files under these rules. It does
not establish that the checkout contains no secrets.

This command scans file text. The separate `scan_json_payload` function in
[secret_exclusion_scan.py](../../src/microcosm_core/secret_exclusion_scan.py)
also examines named JSON fields such as `body` and `provider_payload`; the
checkout command does not apply that additional field test.

## Read the displayed permission fields

These commands print JSON. The environment setting disables runtime receipt
writes while you inspect it:

```bash
MICROCOSM_RUNTIME_RECEIPT_WRITES=0 /tmp/plectis-security-venv/bin/plectis authority --card
MICROCOSM_RUNTIME_RECEIPT_WRITES=0 /tmp/plectis-security-venv/bin/plectis stripping-guard
```

`authority --card` summarises registered components and recorded results,
and prints false permission fields for release, publication, provider calls,
and source mutation. `stripping-guard` constructs eight rule rows and compares
their declared fields and a short list of private-path or token strings in
those rows. It does not scan checkout files or run the tests named in its
`validation_refs`. Both commands exit `0` for a returned `status` of `pass`
and `1` for a blocked status.

The program sets these permission fields in the JSON; it does not apply them
as operating-system access controls. The implementations are
`RuntimeShell.authority_card`, `RuntimeShell.stripping_guard`, and their CLI
dispatch in [runtime_shell.py](../../src/microcosm_core/runtime_shell.py).

## Run the scanner and reporting tests

```bash
PYTHONPATH=src /tmp/plectis-security-venv/bin/python -m pytest tests/test_secret_exclusion_scan.py tests/test_private_state_scan.py tests/test_public_entry_docs.py --basetemp=/tmp/plectis-security-bt
```

These tests exercise synthetic matches, negative-case exceptions, file
selection, unreadable files, and the reporting instructions. They also search
selected public text for named JSON permission fields set to `true` and
committed JSON receipts for specified host-path strings. A passing test run
means those assertions passed; its file selection and matching rules are
defined in the named test files.

<a id="release-authority-reports"></a>
## Reproduce a release-export result

For a report about release, publication, hosting, or provider permission
fields, generate an export with the same environment:

```bash
VENV=/tmp/plectis-security-venv make standalone-export EXPORT_OUT=/tmp/plectis-security-boundary-export
```

This target runs `make install` again, then creates
`/tmp/plectis-security-boundary-export/plectis/`. The Makefile passes `--force`,
so a previous generated `plectis/` directory at that location is replaced.
The exporter copies its selected files, scans and compares the generated
files, and runs command and package-install tests. See
[release_export.py](../../src/microcosm_core/release_export.py) for the file
selection, scan rules, and `blocking_codes`.

Open
`/tmp/plectis-security-boundary-export/plectis/receipts/release/release_export_receipt.json`.
Include its `receipt_id`, `artifact.artifact_payload_hash_sha256`,
`blocking_codes`, and the relevant permission fields in the report. The
exporter writes these values even when export validation passes:

- `authority_receipt.release_authorized=false`
- `authority_receipt.publish_authorized=false`
- `release_candidate_packet.authority_state.release_authorization_gate.invoked=false`
- `release_candidate_packet.release_authorization_gate_decision.release_authorization_allowed_now=false`

The export command accepts no operator authorization receipt and does not
change these fields to approve publication. If release approval is relevant
to the report, identify the separate operator authorization record and the
action it covers. Do not treat export `status: pass` as that approval.

For release-boundary, hosted-header, CI/supply-chain, or unsafe exploit-content
reports, describe the expected and observed behaviour and provide the
smallest redacted reproduction. Follow [SECURITY.md](../../SECURITY.md) when
submitting it; omit private state and live-target exploit steps.
