"""Shared replay observations and admission host.

The generated decision core checks the supplied observations. This Python host
is trusted to execute the named runners, observe files and compute hashes; the
core does not prove component semantics or authenticate an arbitrary subprocess.
"""
from __future__ import annotations

from dataclasses import replace
from contextlib import redirect_stdout
import hashlib
import inspect
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Sequence

from microcosm_core.receipts import normalize_public_receipt_paths, observe_receipt_writes, receipt_payload_digest
from microcosm_core.schemas import loads_json_strict, read_json_strict

CLAIM_CEILING = "Fresh named runner results over supplied public inputs; no broader correctness or release authority."
CODE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_INVENTORY_SCHEME = "package_roots_v1"
RUNTIME_PACKAGE_NAMES = ("microcosm_core", "plectis")
RUNTIME_SOURCE_SCOPE = tuple(f"{name}/**" for name in RUNTIME_PACKAGE_NAMES)


class UnsupportedInputSymlink(ValueError):
    """An input or receipt uses a link outside the captured file model."""


class ReplaySelectionError(ValueError):
    """A selection is invalid before any runner or output creation."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _validate_replay_selection(organ_id: str, declared_steps: Sequence[Any],
                               registry_rows: Sequence[dict[str, Any]],
                               route_provider: Callable[[], Sequence[Any]]):
    """Validate the full universes before selecting exactly one declared route."""
    def unique_ids(rows, field, kind):
        try:
            rows = tuple(rows)
            if any((not isinstance(row, dict)) if kind == "registry" else isinstance(row, dict)
                   for row in rows):
                raise TypeError("invalid universe row")
            ids = [row[field] if kind == "registry" else getattr(row, field) for row in rows]
        except (KeyError, AttributeError, TypeError) as exc:
            raise ReplaySelectionError("invalid_universe", f"invalid {kind} universe") from exc
        if (not ids or any(not isinstance(value, str) or not value for value in ids)
                or len(ids) != len(set(ids))):
            raise ReplaySelectionError("invalid_universe", f"{kind} universe must be nonempty and unique")
        return ids

    try:
        steps = tuple(declared_steps)
    except TypeError as exc:
        raise ReplaySelectionError("invalid_universe", "invalid runtime universe") from exc
    declared = unique_ids(steps, "organ_id", "runtime")
    registered = unique_ids(registry_rows, "organ_id", "registry")
    if set(declared) != set(registered):
        raise ReplaySelectionError("universe_mismatch", "runtime routes must cover the complete component registry")
    if not isinstance(organ_id, str) or organ_id not in declared:
        raise ReplaySelectionError("unknown_component", "unknown exact component ID")
    # IDs become output directory names; receipt/input names are still governed
    # by the existing host's confinement checks.
    if organ_id in {".", ".."} or Path(organ_id).name != organ_id or "\\" in organ_id:
        raise ReplaySelectionError("invalid_component_id", "component ID must be a single directory name")
    selected = next(step for step in steps if step.organ_id == organ_id)
    receipt_name = getattr(selected, "receipt_name", None)
    if (not isinstance(receipt_name, str) or not receipt_name or receipt_name in {".", ".."}
            or Path(receipt_name).name != receipt_name or "\\" in receipt_name):
        raise ReplaySelectionError("invalid_receipt_name", "primary receipt must be a single file name")
    if not callable(route_provider):
        raise ReplaySelectionError("invalid_universe", "route provider must be callable")

    def checked_routes():
        routes = tuple(route_provider())
        routed = unique_ids(routes, "organ_id", "route provider")
        if set(routed) != set(declared):
            raise ReplaySelectionError("universe_mismatch", "route provider must retain the complete runtime universe")
        return routes

    checked_routes()
    return selected, checked_routes


def _component_replay_output(root: Path, out: Path) -> tuple[Path, Path]:
    """Constrain the public component API to this root's ignored run area."""
    root = Path(root).resolve()
    out = Path(out)
    if not out.is_absolute():
        out = root / out
    # Check lexical ancestry before resolution so links cannot disappear.
    out = Path(os.path.abspath(out))
    parent = root / ".microcosm"
    if not out.is_relative_to(parent):
        raise ValueError("component replay output must be under this root's .microcosm directory")
    _confined(out, parent)
    return root, out.resolve()


def _component_execution_state(summary: dict[str, Any]) -> str:
    """Classify existing host evidence without strengthening its verdict."""
    row = summary["results"][0]
    status = row.get("status")
    if summary["status"] == "pass" and summary["admission"]["accepted"] is True:
        return "pass"
    if status in {"source_changed", "input_changed", "receipt_changed"}:
        return status
    if row.get("input_error") == "FileNotFoundError":
        return "missing_input"
    if row.get("tool_state") == "tool_missing":
        return "tool_unavailable"
    if any(value is False for value in row.get("required_tool_availability", {}).values()):
        return "tool_unavailable"
    if status in {"missing_native_lean_witness", "missing_native_lean_lake_witness"}:
        return "missing_native_witness"
    if row.get("error_code") or row.get("receipt_written") or status == "pass":
        return "admission_rejected"
    # A runner exception or an unclassified nonpass result is not evidence of
    # a missing tool or a component's semantic failure.
    return "unknown" if row.get("error") else "blocked"


def replay_component(root: Path, out: Path, organ_id: str, *,
                     declared_steps: Sequence[Any],
                     registry_rows: Sequence[dict[str, Any]],
                     route_provider: Callable[[], Sequence[Any]]) -> dict[str, Any]:
    """Replay one named component through the existing admission host.

    Supply the complete runtime and registry, never an already narrowed list.
    This low-level synchronous API runs trusted component code in the caller's
    process. Backend consumers must use component_replay_worker's isolated
    entry because some runners change process-wide import state.
    """
    selected, full_routes = _validate_replay_selection(
        organ_id, declared_steps, registry_rows, route_provider)
    root, out = _component_replay_output(root, out)
    run = new_replay_directory(root, out)
    # native_replay_step belongs to replay_components; do not apply it twice.
    summary = replay_components(root, run, (selected,), registry_rows=registry_rows,
                                route_provider=full_routes,
                                command=f"plectis component-replay {organ_id}")
    summary.update(scope="component", selected_organ_ids=[organ_id])
    summary["execution_state"] = _component_execution_state(summary)
    summary["summary_ref"] = str(run / "component-replays.json")
    _confined(Path(summary["summary_ref"]), run)
    Path(summary["summary_ref"]).write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def run_component_replay_command(organ_id: str, *, root: Path | None = None,
                                 out: Path | None = None, format: str = "json") -> int:
    """Thin installed CLI seam; it does not evaluate indexed command strings."""
    from microcosm_core.runtime_shell import RUNTIME_STEPS

    root = Path.cwd() if root is None else Path(root)
    out = Path(".microcosm/component-replays") if out is None else Path(out)
    try:
        registry = read_json_strict(root / "core/organ_registry.json")
        with redirect_stdout(sys.stderr):
            summary = replay_component(root, out, organ_id, declared_steps=RUNTIME_STEPS,
                                       registry_rows=registry["implemented_organs"],
                                       route_provider=lambda: RUNTIME_STEPS)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        failure = {"status": "usage_error", "scope": "component", "selected_organ_ids": [organ_id],
                   "execution_state": "unknown", "error_code": getattr(exc, "code", "invalid_replay_request"),
                   "error": str(exc)}
        print(json.dumps(failure), file=sys.stderr)
        return 2
    if format == "text":
        row = summary["results"][0]
        print(f"{organ_id}: {row['status']}")
        print(f"Component replay gate: {summary['status']} (1 selected component)")
        print(f"Summary: {summary['summary_ref']}")
    else:
        print(json.dumps(summary, indent=2))
    return 0 if summary["status"] == "pass" else 1


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_digest(value: Any) -> str:
    return _digest(json.dumps(value, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=False, allow_nan=False).encode())


def input_tree_hash(path: Path) -> str:
    """Capture real files, pruning only declared compiler/cache outputs."""
    if path.is_symlink():
        raise UnsupportedInputSymlink
    if not path.is_dir():
        raise FileNotFoundError(path)
    files = []
    for directory, names, filenames in os.walk(path):
        directory_path = Path(directory)
        files.append(("directory", directory_path.relative_to(path).as_posix(),
                      stat.S_IMODE(directory_path.stat().st_mode)))
        if any((Path(directory) / name).is_symlink() for name in names):
            raise UnsupportedInputSymlink
        names[:] = sorted(name for name in names if name not in {
            ".git", ".microcosm", ".build", "__pycache__", ".venv", ".pytest_cache",
        })
        for name in sorted(filenames):
            candidate = Path(directory) / name
            if candidate.is_symlink():
                raise UnsupportedInputSymlink
            if candidate.suffix in {".pyc", ".pyo"}:
                continue
            if not stat.S_ISREG(candidate.stat().st_mode):
                raise ValueError("captured inputs must be regular files")
            files.append(("file", candidate.relative_to(path).as_posix(),
                          _digest(candidate.read_bytes()), stat.S_IMODE(candidate.stat().st_mode)))
    return _digest(json.dumps(files, sort_keys=True).encode())


def _confined(path: Path, parent: Path) -> None:
    if not path.resolve().is_relative_to(parent.resolve()):
        raise UnsupportedInputSymlink
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink():
            raise UnsupportedInputSymlink
        if ancestor == parent:
            break
    else:
        raise ValueError("path is outside its declared parent")


def _receipt_bytes(path: Path, parent: Path) -> bytes:
    _confined(path, parent)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("receipt must be a regular file")
        captured = stream.read()
    _confined(path, parent)
    return captured


def payload_digest(payload: dict[str, Any], *, persisted: bool = False) -> str:
    """Bind the exact expected writer representation, including provenance.

    Transform raw results once. Preserve already normalized results, including
    hashed originals; compare saved objects unchanged, without a second lossy
    transform that could collapse distinct original witness paths.
    """
    expected = payload if persisted or "public_path_sanitization" in payload else normalize_public_receipt_paths(payload)
    return _json_digest(expected)


def native_replay_step(step: Any) -> Any:
    """Select native fixtures only for explicit assurance replay routes."""
    if step.organ_id == "lean_proof_search_lab_runtime":
        from microcosm_core.organs import lean_proof_search_lab_runtime as lab
        return replace(step, example_rel="fixtures/first_wave/lean_proof_search_lab_runtime/input",
                       input_mode="lean_proof_search_lab_fixture_cases", runner=lab.run,
                       receipt_name=lab.RESULT_NAME)
    if step.organ_id == "formal_math_lean_proof_witness":
        from microcosm_core.organs import formal_math_lean_proof_witness as witness
        return replace(step, example_rel="fixtures/first_wave/formal_math_lean_proof_witness/input",
                       input_mode="first_wave_fixture", runner=witness.run,
                       receipt_name=witness.RESULT_NAME)
    return step


def replay_verdict(step: Any, result: dict[str, Any]) -> str:
    """Check declared execution evidence, without proving the runner truthful."""
    status = result.get("status")
    if not isinstance(status, str) or not status:
        return "missing_verdict"
    if status != "pass":
        return status
    for field in ("exercise", "secret_exclusion_scan", "authority_ceiling"):
        nested = result.get(field)
        if isinstance(nested, dict) and nested.get("status") in {
            "blocked", "fail", "failed", "error", "exception", "locked",
        }:
            return "inconsistent_execution_verdict"
    if result.get("execution_status") in {"blocked", "fail", "failed", "error", "exception"}:
        return "inconsistent_execution_verdict"
    if step.organ_id == "lean_proof_search_lab_runtime":
        from microcosm_core.organs import lean_proof_search_lab_runtime as lab
        if (result.get("execution_witness_mode") != lab.EXECUTION_LIVE
                or result.get("verification_performed") is not True
                or result.get("tool_state") != lab.TOOL_PRESENT_AND_VERIFIED):
            return "missing_native_lean_witness"
    if step.organ_id == "formal_math_lean_proof_witness":
        from microcosm_core.organs import formal_math_lean_proof_witness as witness
        tools, build = result.get("tool_versions"), result.get("lake_build")
        observed, declarations = result.get("observed_negative_cases"), result.get("compiled_declaration_count")
        if (result.get("execution_witness_mode") != "live_lean_lake_execution"
                or result.get("synthetic_contract") is True
                or result.get("not_a_live_run") is True
                or result.get("real_runtime_receipt") is False
                or not isinstance(tools, dict)
                or tools.get("lean_available") is not True or tools.get("lake_available") is not True
                or not isinstance(build, dict) or type(build.get("return_code")) is not int
                or build.get("return_code") != 0 or build.get("timed_out") is not False
                or build.get("skipped") or type(declarations) is not int or declarations < 1
                or not isinstance(observed, dict)
                or not set(witness.EXPECTED_NEGATIVE_CASES).issubset(observed)
                or result.get("missing_negative_cases") != []):
            return "missing_native_lean_lake_witness"
    return status


def _native_kind(step: Any, payload: dict[str, Any]) -> int:
    if replay_verdict(step, payload) != "pass":
        return 0
    return {"lean_proof_search_lab_runtime": 1, "formal_math_lean_proof_witness": 2}.get(step.organ_id, 0)


def _runner_identity(runner: Any) -> tuple[str, Path | None]:
    if type(runner).__module__ == "microcosm_core.runtime_shell" and type(runner).__name__ == "_LazyAttr":
        module = runner._module_loader.__self__.module_name
        filename = Path(__file__).resolve().parents[1].joinpath(*module.split(".")).with_suffix(".py")
        return f"{module}.{runner._attr_name}", filename
    target = runner if inspect.isfunction(runner) or inspect.ismethod(runner) else type(runner)
    filename = inspect.getsourcefile(target)
    return f"{target.__module__}.{target.__qualname__}", Path(filename) if filename else None


def _route_policy(step: Any, registry: dict[str, Any]) -> dict[str, Any]:
    return {"component_id": step.organ_id, "input_ref": step.example_rel,
            "input_mode": getattr(step, "input_mode", "supplied_public_input"),
            "span": getattr(step, "span", ""), "receipt_name": step.receipt_name,
            "runner": _runner_identity(step.runner)[0],
            "receipt_representation": "observed_common_writer_public_payload_v1",
            "registry_policy": registry}


def _runtime_source_inventory(base: Path | None = None) -> dict[str, str]:
    """Hash the two first-party packages in this trusted source/installation.

    CODE_ROOT can be ``src`` or ``site-packages``. Its other siblings are not
    runtime source authority. Missing or linked packages fail closed; they do
    not cause a fallback to scanning the environment or another installation.
    """
    base = Path(os.path.abspath(CODE_ROOT if base is None else base))
    _confined(base, Path(base.anchor))
    packages = {}
    for name in RUNTIME_PACKAGE_NAMES:
        package = base / name
        _confined(package, base)
        packages[name] = input_tree_hash(package)
    return packages


def _source_snapshot(root: Path, routes: Sequence[Any], policies: list[dict[str, Any]], selected_steps: Sequence[Any]) -> dict[str, Any]:
    sources = {}
    for step in selected_steps:
        reference, source = _runner_identity(step.runner)
        if source:
            sources[reference] = _digest(source.read_bytes())
    registry = root / "core/organ_registry.json"
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False)
    runtime_packages = _runtime_source_inventory()
    runtime_hash = _json_digest(runtime_packages)
    declared_source = root / "src"
    if declared_source.is_symlink():
        raise UnsupportedInputSymlink
    declared_hash = input_tree_hash(declared_source) if declared_source.exists() else None
    return {"source_inventory_scheme": SOURCE_INVENTORY_SCHEME,
            "runtime_source_scope": list(RUNTIME_SOURCE_SCOPE),
            "runtime_package_tree_sha256": runtime_packages,
            "runtime_package_digest_scheme": "tree_type_path_bytes_posix_mode_v2",
            "runtime_dependency_boundary": "First-party package bytes and POSIX modes only; standard-library and third-party dependency behavior remain trusted.",
            "runtime_source_tree_sha256": runtime_hash,
            "declared_source_scope": "root/src/** when present; an independent clone-source byte and POSIX-mode snapshot",
            "declared_source_tree_sha256": declared_hash,
            "registry_sha256": _digest(registry.read_bytes()) if registry.exists() else None,
            "core_policy_tree_sha256": input_tree_hash(root / "core") if (root / "core").exists() else None,
            "standards_tree_sha256": input_tree_hash(root / "standards") if (root / "standards").exists() else None,
            "git_head": head.stdout.strip() if head.returncode == 0 else None,
            "route_contract_sha256": _json_digest([_route_policy(step, {}) for step in routes]),
            "selected_policy_sha256": _json_digest(policies), "runner_sources": sources}


def replay_components(root: Path, out: Path, declared_steps: Sequence[Any], *,
                      registry_rows: Sequence[dict[str, Any]] = (),
                      route_provider: Callable[[], Sequence[Any]] | None = None,
                      command: str = "make component-replays") -> dict[str, Any]:
    """Execute selected routes once and admit the complete captured observation set."""
    from plectis.replay import accept

    root, out = root.resolve(), out.resolve()
    if (out.is_relative_to(root) and not out.is_relative_to(root / ".microcosm")) or root.is_relative_to(out):
        raise ValueError("replay output must be external or under ignored .microcosm")
    out.mkdir(parents=True, exist_ok=True)
    run_nonce = secrets.token_hex(16)
    steps = [native_replay_step(step) for step in declared_steps]
    by_id = {row["organ_id"]: row for row in registry_rows}
    policies = [_route_policy(step, by_id.get(step.organ_id, {})) for step in steps]
    get_routes = route_provider or (lambda: declared_steps)
    source_before = _source_snapshot(root, get_routes(), policies, steps)
    source_identity = _json_digest(source_before)
    before, input_errors = {}, {}
    for index, step in enumerate(steps):
        try:
            _confined(root / step.example_rel, root)
            before[index] = input_tree_hash(root / step.example_rel)
        except Exception as exc:
            before[index], input_errors[index] = "", type(exc).__name__
    specs, observations, results, receipts, writer_events = [], [], [], {}, {}
    for index, step in enumerate(steps):
        started = time.monotonic()
        evidence_class = str(by_id.get(step.organ_id, {}).get("evidence_class")
                             or by_id.get(step.organ_id, {}).get("current_evidence_scope")
                             or getattr(step, "input_mode", "supplied_public_input"))
        claim = _json_digest(policies[index])
        spec = {"component_id": step.organ_id, "input_ref": step.example_rel,
                "evidence_class": evidence_class, "claim_digest": claim,
                "native_kind": {"lean_proof_search_lab_runtime": 1,
                                "formal_math_lean_proof_witness": 2}.get(step.organ_id, 0)}
        specs.append(spec)
        observation = {"component_id": step.organ_id, "input_ref": step.example_rel,
                       "evidence_class": evidence_class,
                       "claim_digest": _json_digest(_route_policy(step, by_id.get(step.organ_id, {}))),
                       "source_before": source_identity, "source_after": "", "input_before": before[index],
                       "input_after": "", "runner_component_id": "", "receipt_component_id": "",
                       "runner_payload_digest": "", "receipt_payload_digest": "", "receipt_digest": "",
                       "runner_status": "", "receipt_status": "", "runner_verdict": "", "receipt_verdict": "",
                       "runner_native_kind": 0, "receipt_native_kind": 0, "receipt_present": False}
        row = {"organ_id": step.organ_id, "input_ref": step.example_rel, "status": "error"}
        try:
            if index in input_errors:
                raise ValueError("input snapshot unavailable")
            component_out = out / step.organ_id
            _confined(component_out, out)
            if component_out.exists():
                raise FileExistsError("component output must be fresh")
            receipt = component_out / step.receipt_name
            expected_target = receipt.resolve()
            writes = []
            writer_events[index] = writes

            def capture_write(event, expected_target=expected_target, writes=writes):
                if event.target == expected_target:
                    writes.append(event)

            with observe_receipt_writes(capture_write):
                result = step.runner(root / step.example_rel, component_out, command)
            if not isinstance(result, dict):
                raise ValueError("runner must return an object")
            observation.update(runner_component_id=result.get("organ_id"), runner_status=result.get("status"),
                               runner_verdict=replay_verdict(step, result), runner_native_kind=_native_kind(step, result),
                               runner_payload_digest=writes[0].payload_sha256 if len(writes) == 1 else "")
            row["raw_runner_payload_sha256"] = _json_digest(result)
            row["primary_receipt_write_count"] = len(writes)
            exercise = result.get("exercise")
            row.update(status=observation["runner_verdict"], error_codes=result.get("error_codes", []),
                       execution_status=result.get("execution_status") or (
                           exercise.get("status") if isinstance(exercise, dict) else None))
            for key in ("execution_witness_mode", "verification_performed", "lean_executed", "tool_state",
                        "real_runtime_receipt", "not_a_live_run"):
                row[key] = result.get(key)
            if step.organ_id == "formal_math_lean_proof_witness":
                versions = result.get("tool_versions")
                if isinstance(versions, dict):
                    row["required_tool_availability"] = {
                        key: versions.get(key) for key in ("lean_available", "lake_available")
                        if isinstance(versions.get(key), bool)}
            row.update(receipt_ref=str(receipt), receipt_written=False)
            data = _receipt_bytes(receipt, component_out)
            recorded = loads_json_strict(data.decode("utf-8"), "component replay receipt")
            if not isinstance(recorded, dict):
                raise ValueError("receipt must contain an object")
            digest = _digest(data)
            observation.update(receipt_present=True, receipt_digest=digest,
                               receipt_component_id=recorded.get("organ_id"), receipt_status=recorded.get("status"),
                               receipt_verdict=replay_verdict(step, recorded),
                               receipt_native_kind=_native_kind(step, recorded), receipt_payload_digest=receipt_payload_digest(recorded))
            row.update(receipt_written=True, receipt_status=recorded.get("status"), receipt_sha256=digest,
                       input_tree_sha256=before[index])
            receipts[index] = (receipt, digest, component_out)
            if len(writes) != 1:
                row["error_code"] = "missing_producer_write" if not writes else "duplicate_primary_receipt_write"
                raise ValueError("exactly one primary producer write required")
            if (observation["runner_component_id"] != step.organ_id or observation["receipt_component_id"] != step.organ_id
                    or observation["runner_status"] != observation["receipt_status"]):
                row["error_code"] = "runner_receipt_identity_or_status_mismatch"
                raise ValueError("runner and receipt identity or status mismatch")
            if observation["runner_payload_digest"] != observation["receipt_payload_digest"]:
                row["error_code"] = "producer_public_payload_mismatch"
                raise ValueError("producer intent and saved receipt differ")
            if row["status"] == "pass" and observation["receipt_verdict"] != "pass":
                raise ValueError("receipt execution verdict differs")
        except Exception as exc:
            if row["status"] == "pass" or row["status"] == "error":
                row["status"] = "error"
            row["error"] = type(exc).__name__
            if index in input_errors:
                row["input_error"] = input_errors[index]
            observation["runner_verdict"] = row["status"]
        row["elapsed_seconds"] = round(time.monotonic() - started, 3)
        results.append(row)
        observations.append(observation)
    try:
        source_after = _source_snapshot(root, get_routes(), policies, steps)
        after_identity = _json_digest(source_after)
    except Exception:
        source_after, after_identity = {}, ""
    for index, (step, row, observation) in enumerate(zip(steps, results, observations)):
        observation["source_after"] = after_identity
        try:
            if index in writer_events:
                row["primary_receipt_write_count"] = len(writer_events[index])
                if len(writer_events[index]) != 1 and row["status"] == "pass":
                    row.update(status="error", error="ValueError", error_code="duplicate_primary_receipt_write"
                               if writer_events[index] else "missing_producer_write")
                    observation["runner_payload_digest"] = ""
            _confined(root / step.example_rel, root)
            observation["input_after"] = input_tree_hash(root / step.example_rel)
            if observation["input_before"] != observation["input_after"]:
                row.update(status="input_changed", error="InputMutation")
            if index in receipts:
                path, digest, parent = receipts[index]
                if _digest(_receipt_bytes(path, parent)) != digest:
                    row.update(status="receipt_changed", error="ReceiptMutation")
            if source_identity != after_identity:
                row.update(status="source_changed", error="SourceMutation")
        except Exception as exc:
            row.update(status="error", error=type(exc).__name__)
        if row["status"] != "pass":
            observation["runner_verdict"] = row["status"]
    # No Python fallback to counts: the generated admission decision governs pass.
    admitted = accept(specs, source_identity, observations)
    failures = [r["organ_id"] for r in results if r["status"] != "pass"]
    return {"schema_version": "plectis_component_replay_gate_v2", "status": "pass" if admitted else "blocked",
            "component_count": len(results), "failed_components": failures, "results": results,
            "source_inventory_scheme": SOURCE_INVENTORY_SCHEME,
            "runtime_source_scope": list(RUNTIME_SOURCE_SCOPE),
            "source": dict(source_before), "source_identity_material": source_before,
            "source_after": source_after, "source_identity": source_identity,
            "input_digest_scheme": "tree_type_path_bytes_posix_mode_v2",
            "payload_binding": "producer_public_representation_not_all_raw_api_fields",
            "input_digest_exclusions": [".git", ".microcosm", ".build", "__pycache__", ".venv", ".pytest_cache", "*.pyc", "*.pyo"],
            "admission": {"kernel": "plectis.replay.accept", "accepted": admitted,
                          "run_nonce": run_nonce, "run_id": out.name,
                          "context_boundary": "Evidence class and claim digest are host-selected registry context, not independently proved receipt/domain claims. The nonce is audit context, not freshness authentication.",
                          "diagnostics": [] if admitted else ["generated_admission_rejected_observations"],
                          "registry_specs": specs, "observations": observations},
            "claim_ceiling": CLAIM_CEILING}


def replay_steps(root: Path, out: Path, steps: Sequence[Any]) -> list[dict[str, Any]]:
    """Compatibility helper; callers needing admission consume replay_components."""
    return replay_components(root, out, steps)["results"]


def new_replay_directory(root: Path, out: Path) -> Path:
    root, out = root.resolve(), out.resolve()
    if out.is_relative_to(root) and not out.is_relative_to(root / ".microcosm"):
        raise ValueError("replay output inside checkout must be under .microcosm")
    if root.is_relative_to(out):
        raise ValueError("replay output must not contain checkout")
    out.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="run-", dir=out))
