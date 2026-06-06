#!/usr/bin/env python3
"""
[PURPOSE]
- Teleology: Compare every pin in `requirements.txt` against the actual
  installed package versions in the active venv, and surface any drift
  before it can crash a long-running process.
- Mechanism: Parse requirements.txt, walk `pip list --format=json`, evaluate
  each spec with packaging.specifiers.SpecifierSet, and ALSO run `pip check`
  to catch transitive conflicts that the top-level file cannot constrain.
- Background: This tool exists because of the 2026-04-08 incident where
  Starlette 1.0.0 was silently pulled in over the loose `fastapi>=0.109,<0.112`
  pin (which couldn't constrain transitive deps), removed `on_startup` from
  `Router.__init__`, and crashed `FastAPI(lifespan=...)` at module import
  time. The fix was an explicit `starlette<1.0.0` pin in requirements.txt.
  This tool is the alarm that fires the moment that pin is violated again.

[INTERFACE]
- Reads: `requirements.txt` at the repo root, `pip list` from the active venv.
- Writes: stdout (human or JSON report).
- Exits: 0 on clean state. With `--strict`, exits 1 on any drift, missing
  package, or pip-check failure.
- Args:
    --json     emit machine-readable JSON instead of human text
    --strict   exit nonzero on any drift / missing / pip-check failure
    --quiet    only print drift/failure rows; suppress the OK rollup

[FLOW]
1. Locate repo root (the parent of `tools/dev/`).
2. Parse requirements.txt into (name, specifier) tuples, ignoring blanks
   and comments and stripping `[extras]`.
3. Snapshot installed package versions via `pip list --format=json`.
4. For each pinned package, evaluate Version-in-SpecifierSet. Bucket into
   ok / drifted / missing.
5. Run `pip check` to catch indirect dep conflicts.
6. Print or emit JSON; honor --strict for the exit code.
- When-needed: Open when a repo environment failure might come from version drift between `requirements.txt` and the active venv rather than application code.
- Escalates-to: requirements.txt
- Navigation-group: python_misc_runtime.

[DEPENDENCIES]
- pypi.packaging: SpecifierSet + Version (already a transitive dep of pip,
  always available in any venv that can run pip itself).
- stdlib: subprocess, json, re, argparse, pathlib, sys.

[CONSTRAINTS]
- Must be safe to run in CI / preflight: no network calls, no installs.
- Must use the venv's own python (so it sees the venv's site-packages).
  Run via `./repo-python tools/dev/check_pin_drift.py`.
- Must not import any project code; this is a pure environment audit and
  has to keep working even when system.server.main is broken.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from packaging.utils import canonicalize_name

REPO_ROOT = Path(__file__).resolve().parents[2]
REQ_FILE = REPO_ROOT / "requirements.txt"

# matches: name, optional [extras], optional specifier
_REQ_LINE_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9_.\-]+)"
    r"(?:\[[^\]]+\])?"
    r"\s*(?P<spec>[<>=!~].*)?$"
)


def parse_requirements(path: Path) -> list[tuple[str, str]]:
    """[ACTION]
    - Teleology: Normalize `requirements.txt` lines into the pin/spec pairs this audit evaluates.
    - Mechanism: Strip blanks, comments, include directives, VCS URLs, and extras, then regex-parse the remaining requirement lines into lowercase names plus raw specifier strings.
    - Reads: path.
    - Guarantee: Returns one `(canonical_name, raw_specifier)` tuple per parseable direct requirement line in file order.
    - Fails: OSError from `Path.read_text()` if the requirements file cannot be read.
    - When-needed: Open when checking which requirement syntaxes this drift audit accepts or skips before blaming the installed environment.
- Escalates-to: requirements.txt

    Lines that are blank, comments, `-r` includes, or VCS URLs are skipped.
    Extras are stripped from the name. Spec strings keep their original
    operator/version layout (e.g. ">=0.49.1,<1.0.0").
    """
    out: list[tuple[str, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        if "://" in line:  # skip git+, https URLs etc.
            continue
        match = _REQ_LINE_RE.match(line)
        if not match:
            continue
        name = canonicalize_name(match.group("name"))
        spec = (match.group("spec") or "").strip()
        out.append((name, spec))
    return out


def installed_versions(python_exe: str) -> dict[str, str]:
    """[ACTION]
    - Teleology: Snapshot the active interpreter's installed package versions for drift comparison.
    - Mechanism: Invoke `python_exe -m pip list --format=json`, parse the JSON payload, and lower-case package names for key stability.
    - Reads: The environment reachable through `python_exe`.
    - Guarantee: Returns a `{normalized_name: installed_version}` mapping for every package reported by `pip list`.
    - Fails: `subprocess.CalledProcessError` when pip listing fails; `json.JSONDecodeError` if pip emits invalid JSON.
    - When-needed: Open when the drift report suggests the active venv may differ from the interpreter you expected to audit.
- Escalates-to: repo-python
    """
    raw = subprocess.check_output(
        [python_exe, "-m", "pip", "list", "--format=json"],
        text=True,
    )
    return {canonicalize_name(p["name"]): p["version"] for p in json.loads(raw)}


def evaluate(
    pinned: Iterable[tuple[str, str]],
    installed: dict[str, str],
) -> tuple[list, list, list, list]:
    """[ACTION]
    - Teleology: Classify every declared requirement against the installed-version snapshot.
    - Mechanism: Compare each pinned specifier against the installed version with `packaging`, routing results into ok, drifted, missing, or unparseable buckets.
    - Reads: pinned and installed.
    - Guarantee: Returns `(ok, drifted, missing, unparseable)` buckets whose tuple payloads preserve the requirement name, requested spec, and installed version or parse failure context.
    - Fails: None — version and spec parsing failures are recorded in the unparseable bucket instead of raising.
    - When-needed: Open when you need to understand why a package landed in drifted, missing, or unparseable rather than inspecting the final report only.
- Escalates-to: requirements.txt
    """
    from packaging.specifiers import SpecifierSet
    from packaging.version import InvalidVersion, Version

    ok: list[tuple[str, str, str]] = []
    drifted: list[tuple[str, str, str]] = []
    missing: list[tuple[str, str]] = []
    unparseable: list[tuple[str, str, str]] = []

    for name, spec in pinned:
        version = installed.get(name)
        if version is None:
            missing.append((name, spec))
            continue
        if not spec:
            ok.append((name, "(any)", version))
            continue
        try:
            in_range = Version(version) in SpecifierSet(spec)
        except InvalidVersion as exc:
            unparseable.append((name, spec, f"InvalidVersion: {exc}"))
            continue
        except Exception as exc:  # noqa: BLE001 - report whatever fails
            unparseable.append((name, spec, str(exc)))
            continue
        if in_range:
            ok.append((name, spec, version))
        else:
            drifted.append((name, spec, version))

    return ok, drifted, missing, unparseable


def run_pip_check(python_exe: str) -> tuple[bool, str]:
    """[ACTION]
    - Teleology: Add transitive dependency conflict detection that `requirements.txt` alone cannot express.
    - Mechanism: Run `python_exe -m pip check`, capture stdout/stderr, and return the exit-state boolean plus combined output text.
    - Reads: The environment reachable through `python_exe`.
    - Guarantee: Returns `(passed, full_output)` for the exact `pip check` invocation.
    - Fails: `OSError` if the interpreter cannot launch `pip check`.
    - When-needed: Open when the direct pins look clean but the environment may still be broken by indirect dependency conflicts.
- Escalates-to: repo-python
    """
    result = subprocess.run(
        [python_exe, "-m", "pip", "check"],
        capture_output=True,
        text=True,
    )
    return (result.returncode == 0, (result.stdout + result.stderr).strip())


def emit_human(
    ok: list,
    drifted: list,
    missing: list,
    unparseable: list,
    pip_check_passed: bool,
    pip_check_output: str,
    quiet: bool,
) -> None:
    """[ACTION]
    - Teleology: Render the drift audit into a readable terminal report for operator use.
    - Mechanism: Print grouped sections for drifted, missing, unparseable, and `pip check` failures, then optionally print the ok rollup and final summary line.
    - Reads: The precomputed result buckets and quiet flag supplied by the caller.
    - Writes: stdout.
    - Guarantee: Emits a deterministic section order based on the supplied buckets and never mutates the inputs.
    - Fails: `BrokenPipeError` only if stdout is no longer writable.
    - When-needed: Open when adjusting or explaining the human-facing report layout without re-reading the audit pipeline.
    - Escalates-to: tools/dev/check_pin_drift.py::main.
    """
    if drifted:
        print(f"❌ DRIFTED ({len(drifted)}):")
        for name, spec, version in drifted:
            print(f"   {name:<24} pinned {spec:<28} installed {version}")
        print()

    if missing:
        print(f"⚠️  MISSING ({len(missing)}):")
        for name, spec in missing:
            print(f"   {name:<24} pinned {spec}")
        print()

    if unparseable:
        print(f"⚠️  UNPARSEABLE ({len(unparseable)}):")
        for name, spec, reason in unparseable:
            print(f"   {name:<24} pinned {spec:<28} ({reason})")
        print()

    if not pip_check_passed:
        print("❌ pip check failures:")
        for line in pip_check_output.splitlines():
            print(f"   {line}")
        print()

    if not quiet:
        print(f"✅ OK ({len(ok)}):")
        for name, spec, version in ok:
            print(f"   {name:<24} pinned {spec:<28} installed {version}")
        print()

    total_problems = len(drifted) + len(missing) + len(unparseable) + (0 if pip_check_passed else 1)
    if total_problems == 0:
        print(f"✅ All {len(ok)} pinned packages match installed versions and pip check passes.")
    else:
        print(f"⚠️  {total_problems} issue(s) found across {len(ok) + len(drifted) + len(missing) + len(unparseable)} pinned packages.")


def emit_json(
    ok: list,
    drifted: list,
    missing: list,
    unparseable: list,
    pip_check_passed: bool,
    pip_check_output: str,
) -> None:
    """[ACTION]
    - Teleology: Emit the drift audit as a machine-readable JSON envelope for automation.
    - Mechanism: Project the result buckets plus summary counts and `pip check` status into one JSON object and print it with indentation.
    - Reads: The precomputed result buckets and `REQ_FILE`.
    - Writes: stdout.
    - Guarantee: Emits JSON with keys `requirements_file`, `ok`, `drifted`, `missing`, `unparseable`, `pip_check_passed`, `pip_check_output`, and `summary`.
    - Fails: `BrokenPipeError` only if stdout is no longer writable.
    - When-needed: Open when another tool consumes this audit and you need the exact output schema.
    - Escalates-to: tools/dev/check_pin_drift.py::main.
    """
    payload = {
        "requirements_file": str(REQ_FILE),
        "ok": [{"name": n, "spec": s, "installed": v} for n, s, v in ok],
        "drifted": [{"name": n, "spec": s, "installed": v} for n, s, v in drifted],
        "missing": [{"name": n, "spec": s} for n, s in missing],
        "unparseable": [{"name": n, "spec": s, "reason": r} for n, s, r in unparseable],
        "pip_check_passed": pip_check_passed,
        "pip_check_output": pip_check_output,
        "summary": {
            "ok": len(ok),
            "drifted": len(drifted),
            "missing": len(missing),
            "unparseable": len(unparseable),
        },
    }
    print(json.dumps(payload, indent=2))


def main() -> int:
    """[ACTION]
    - Teleology: Drive the end-to-end pin-drift audit from CLI arguments to exit status.
    - Mechanism: Parse flags, ensure `requirements.txt` exists, compute pin and environment state, choose human or JSON emission, and apply `--strict` to the final exit code.
    - Reads: CLI args, `REQ_FILE`, the active interpreter environment, and stdout/stderr availability.
    - Writes: stdout and stderr.
    - Guarantee: Returns `2` when `requirements.txt` is missing, `1` for strict-mode failures, and `0` otherwise.
    - Fails: Propagates subprocess and file-read exceptions from the audit helpers.
    - When-needed: Open when changing the script's exit-code semantics or CLI behavior rather than its lower-level audit helpers.
- Escalates-to: requirements.txt; repo-python
    """
    parser = argparse.ArgumentParser(
        description="Audit installed packages against requirements.txt pins.",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--strict", action="store_true", help="exit 1 on any drift / missing / pip-check failure")
    parser.add_argument("--quiet", action="store_true", help="suppress the OK rollup in human output")
    args = parser.parse_args()

    if not REQ_FILE.exists():
        print(f"requirements.txt not found at {REQ_FILE}", file=sys.stderr)
        return 2

    pinned = parse_requirements(REQ_FILE)
    installed = installed_versions(sys.executable)
    ok, drifted, missing, unparseable = evaluate(pinned, installed)
    pip_check_passed, pip_check_output = run_pip_check(sys.executable)

    if args.json:
        emit_json(ok, drifted, missing, unparseable, pip_check_passed, pip_check_output)
    else:
        emit_human(ok, drifted, missing, unparseable, pip_check_passed, pip_check_output, args.quiet)

    if args.strict and (drifted or missing or unparseable or not pip_check_passed):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
