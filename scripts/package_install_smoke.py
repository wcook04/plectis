from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


PRIVATE_MARKERS = (
    "/Users/",
    "/home/",
    "src/ai_workflow",
)
# Captured outputs may legitimately echo the smoke's own work dir (e.g. the
# hello target path); that location is run plumbing, not product content, so
# it is normalized to this token BEFORE the private-marker assert. The assert
# itself stays strict: any other absolute/private path still fails the smoke.
WORK_DIR_TOKEN = "<work-dir>"


def _normalize_work_refs(text: str, work_dir: Path) -> str:
    """Replace every textual variant of the smoke's work dir with WORK_DIR_TOKEN.

    Covers the path as given and fully resolved (e.g. /var vs /private/var on
    macOS) so a host whose temp root lives under a private marker (/home/...)
    cannot fail the marker assert on its own plumbing, while real product
    leaks remain visible.
    """
    for variant in sorted(
        {str(work_dir), work_dir.resolve().as_posix()}, key=len, reverse=True
    ):
        if variant and variant != "/":
            text = text.replace(variant, WORK_DIR_TOKEN)
    return text


@contextlib.contextmanager
def _source_build_lock(source_root: Path):
    """Serialize in-tree wheel builds across concurrent smokes and proof runs.

    pip's in-tree build writes shared intermediates under <source-root>/build;
    two concurrent builds race, and a crashed one leaves residue that fails
    every later build ([Errno 17] on the staged dist-info). The lock lives at
    .microcosm/package_build.lock (gitignored runtime state). POSIX flock
    only; on Windows, or when the lock file cannot be opened, it degrades to
    a no-op rather than blocking the smoke.
    """
    handle = None
    if os.name != "nt":
        try:
            lock_dir = source_root / ".microcosm"
            lock_dir.mkdir(parents=True, exist_ok=True)
            handle = (lock_dir / "package_build.lock").open("w")
            import fcntl

            fcntl.flock(handle, fcntl.LOCK_EX)
        except OSError:
            if handle is not None:
                handle.close()
            handle = None
    try:
        yield
    finally:
        if handle is not None:
            handle.close()


def _clear_stale_wheel_staging(source_root: Path) -> None:
    """Remove crashed-build residue under build/bdist.* before installing.

    A killed wheel build leaves build/bdist.*/wheel/<name>.dist-info behind,
    and setuptools then fails every later build with [Errno 17] File exists.
    Only the bdist staging trees are cleared -- the build/lib incremental
    cache is kept. Call while holding the source build lock so a live
    concurrent build is never swept.
    """
    for staged in (source_root / "build").glob("bdist.*"):
        shutil.rmtree(staged, ignore_errors=True)


def _bin_dir(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts"
    return venv_dir / "bin"


def _run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    stdout_path: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if stdout_path is not None:
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(result.stdout, encoding="utf-8")
    if result.returncode != 0:
        sys.stderr.write(f"command failed ({result.returncode}): {' '.join(argv)}\n")
        if result.stdout:
            sys.stderr.write("--- stdout ---\n")
            sys.stderr.write(result.stdout)
            if not result.stdout.endswith("\n"):
                sys.stderr.write("\n")
        if result.stderr:
            sys.stderr.write("--- stderr ---\n")
            sys.stderr.write(result.stderr)
            if not result.stderr.endswith("\n"):
                sys.stderr.write("\n")
        raise SystemExit(result.returncode)
    return result


def _json_payload(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} must be a JSON object")
    return payload


def _assert_no_private_markers(path: Path, *, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    hits = [marker for marker in PRIVATE_MARKERS if marker in text]
    if hits:
        raise SystemExit(f"{label} leaked private path markers: {hits}")


def _assert_status_pass(payload: dict[str, Any], *, label: str) -> None:
    if payload.get("status") != "pass":
        raise SystemExit(f"{label} status is not pass: {payload.get('status')!r}")


def run_package_smoke(source_root: Path, work_dir: Path, python: str) -> None:
    source_root = source_root.resolve()
    work_dir = work_dir.resolve()
    if not (source_root / "pyproject.toml").is_file():
        raise SystemExit(f"source root lacks pyproject.toml: {source_root}")

    if work_dir.exists():
        shutil.rmtree(work_dir)
    venv_dir = work_dir / "venv"
    output_dir = work_dir / "outputs"
    project_dir = work_dir / "project"
    project_dir.mkdir(parents=True)
    (project_dir / "app.py").write_text('print("plectis package smoke")\n', encoding="utf-8")

    _run([python, "-m", "venv", str(venv_dir)])
    venv_python = _bin_dir(venv_dir) / ("python.exe" if os.name == "nt" else "python")
    plectis = _bin_dir(venv_dir) / ("plectis.exe" if os.name == "nt" else "plectis")
    env = {
        **os.environ,
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
    }
    # A caller-supplied PYTHONPATH (e.g. a dev-tree src/) would shadow the
    # installed package inside the venv and turn this smoke into a checkout
    # test wearing an install costume. Scrub it so "fresh venv" stays true.
    env.pop("PYTHONPATH", None)

    with _source_build_lock(source_root):
        _clear_stale_wheel_staging(source_root)
        _run(
            [
                str(venv_python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-deps",
                str(source_root),
            ],
            env=env,
        )

    # Install-context independence: the console commands below must exercise
    # the pip-installed copy, not a shadowing checkout import.
    import_root = _run(
        [
            str(venv_python),
            "-c",
            "import microcosm_core; print(microcosm_core.__file__)",
        ],
        env=env,
    ).stdout.strip()
    if not import_root.startswith(str(venv_dir)):
        raise SystemExit(
            "installed console resolves microcosm_core outside the venv "
            "(a PYTHONPATH or cwd shadow defeats the install proof)"
        )

    checks: list[tuple[str, list[str], str]] = [
        ("version", [str(plectis), "--version"], "text"),
        ("hello", [str(plectis), "hello", str(project_dir)], "text"),
        (
            "first-screen",
            [str(plectis), "first-screen", "--card", str(project_dir)],
            "json",
        ),
        ("tour", [str(plectis), "tour", "--card", str(project_dir)], "json"),
        ("status", [str(plectis), "status", "--card", str(project_dir)], "json"),
        ("authority", [str(plectis), "authority", "--card"], "json"),
        ("workingness", [str(plectis), "workingness", "--card"], "json"),
        ("legibility", [str(plectis), "legibility-scorecard"], "json"),
        # The goal-shaped product center: the installed console must convert a
        # freeform goal into a first-action contract (graph substrate ships via
        # the share/plectis data files), and its assay must pass
        # from the installed root, not only the dev tree.
        (
            "first-action",
            [
                str(plectis),
                "comprehend",
                "--first-action",
                "How do I evaluate the finance forecasting system?",
            ],
            "contract",
        ),
        (
            "first-action-assay",
            [str(plectis), "comprehension-assay", "--first-action"],
            "text",
        ),
    ]

    for name, argv, kind in checks:
        suffix = "json" if kind in ("json", "contract") else "txt"
        out_path = output_dir / f"{name}.{suffix}"
        _run(argv, env=env, stdout_path=out_path)
        out_path.write_text(
            _normalize_work_refs(out_path.read_text(encoding="utf-8"), work_dir),
            encoding="utf-8",
        )
        _assert_no_private_markers(out_path, label=name)
        if kind == "json":
            _assert_status_pass(_json_payload(out_path, label=name), label=name)

    version_text = (output_dir / "version.txt").read_text(encoding="utf-8").strip()
    if not version_text.startswith("plectis "):
        raise SystemExit(f"version output is not a plectis version: {version_text!r}")

    authority = _json_payload(output_dir / "authority.json", label="authority")
    authority_ceiling = authority.get("authority_ceiling")
    if not isinstance(authority_ceiling, dict):
        raise SystemExit("authority card lacks authority_ceiling")
    if authority_ceiling.get("release_authorized") is not False:
        raise SystemExit("authority card did not keep release_authorized=false")

    workingness = _json_payload(output_dir / "workingness.json", label="workingness")
    if workingness.get("card_status") != "clear":
        raise SystemExit("workingness card_status is not clear")

    contract = _json_payload(output_dir / "first-action.json", label="first-action")
    if contract.get("found") is not True:
        raise SystemExit("first-action contract did not resolve the hero goal")
    action = contract.get("first_action") or {}
    command = str(action.get("command") or "")
    if not command.startswith("PYTHONPATH=src python3 -m microcosm_core"):
        raise SystemExit("first-action contract command is not cold-runnable source form")
    if "<" in command:
        raise SystemExit("first-action contract command carries an unresolved placeholder")
    proof = contract.get("proof_path") or {}
    if not (proof.get("runnable_validator") or proof.get("validation_commands")):
        raise SystemExit("first-action contract lacks a proof path")
    boundary = contract.get("reading_boundary") or {}
    if not (boundary.get("stop_condition") or boundary.get("fallback_guidance")):
        raise SystemExit("first-action contract lacks a reading boundary")
    if not str(contract.get("do_not_claim") or "").strip():
        raise SystemExit("first-action contract lacks a claim ceiling")

    print("Microcosm package smoke: pass")
    # The work dir is host-private; callers that capture this stdout as
    # public evidence must never receive an absolute path from a passing run.
    print("workdir: <work-dir>")
    print(f"version: {version_text}")
    print(
        "checks: version, hello, first-screen, tour, status, authority, "
        "workingness, legibility, first-action, first-action-assay"
    )


def main(argv: list[str] | None = None) -> int:
    """Parse args and run the installed-console package smoke against a fresh venv.

    - Teleology: CLI entry that proves Microcosm installs from source and its installed console card commands stay public-safe.
    - Guarantee: on return the fresh venv was built, the package installed, and all card checks passed without private-path leaks.
    - Fails: install/check failure or private-marker leak -> run_package_smoke raises SystemExit with a nonzero/diagnostic exit.
    - Reads: --source-root pyproject tree; --python interpreter.
    - Writes: --work-dir venv, installed package, and captured card output files.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Install Microcosm into a fresh venv from the local source tree and "
            "run installed-console first-screen checks."
        )
    )
    parser.add_argument("--source-root", type=Path, default=Path.cwd())
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args(argv)
    run_package_smoke(args.source_root, args.work_dir, args.python)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
