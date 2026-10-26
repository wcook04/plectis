"""Shared replay observations and admission host.

The generated decision core checks the supplied observations. This Python host
is trusted to execute the named runners, observe files and compute hashes; the
core does not prove component semantics or authenticate an arbitrary subprocess.
"""
from __future__ import annotations

from dataclasses import replace
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

from microcosm_core.receipts import normalize_public_receipt_paths
from microcosm_core.schemas import loads_json_strict, read_json_strict

CLAIM_CEILING = "Fresh named runner results over supplied public inputs; no broader correctness or release authority."
CODE_ROOT = Path(__file__).resolve().parents[1]


class UnsupportedInputSymlink(ValueError):
    """An input or receipt uses a link outside the captured file model."""


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
            "registry_policy": registry}


def _source_snapshot(root: Path, routes: Sequence[Any], policies: list[dict[str, Any]]) -> dict[str, Any]:
    sources = {}
    selected = {policy["component_id"] for policy in policies}
    for step in routes:
        if step.organ_id not in selected:
            continue
        reference, source = _runner_identity(step.runner)
        if source:
            sources[reference] = _digest(source.read_bytes())
    registry = root / "core/organ_registry.json"
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False)
    return {"runtime_source_tree_sha256": input_tree_hash(CODE_ROOT),
            "declared_source_tree_sha256": input_tree_hash(root / "src") if (root / "src").exists() else None,
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
    source_before = _source_snapshot(root, [native_replay_step(s) for s in get_routes()], policies)
    source_identity = _json_digest(source_before)
    before, input_errors = {}, {}
    for index, step in enumerate(steps):
        try:
            _confined(root / step.example_rel, root)
            before[index] = input_tree_hash(root / step.example_rel)
        except Exception as exc:
            before[index], input_errors[index] = "", type(exc).__name__
    specs, observations, results, receipts = [], [], [], {}
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
            result = step.runner(root / step.example_rel, component_out, command)
            if not isinstance(result, dict):
                raise ValueError("runner must return an object")
            observation.update(runner_component_id=result.get("organ_id"), runner_status=result.get("status"),
                               runner_verdict=replay_verdict(step, result), runner_native_kind=_native_kind(step, result),
                               runner_payload_digest=payload_digest(result))
            exercise = result.get("exercise")
            row.update(status=observation["runner_verdict"], error_codes=result.get("error_codes", []),
                       execution_status=result.get("execution_status") or (
                           exercise.get("status") if isinstance(exercise, dict) else None))
            for key in ("execution_witness_mode", "verification_performed", "lean_executed", "tool_state",
                        "real_runtime_receipt", "not_a_live_run"):
                row[key] = result.get(key)
            receipt = component_out / step.receipt_name
            row.update(receipt_ref=str(receipt), receipt_written=False)
            data = _receipt_bytes(receipt, out)
            recorded = loads_json_strict(data.decode("utf-8"), "component replay receipt")
            if not isinstance(recorded, dict):
                raise ValueError("receipt must contain an object")
            digest = _digest(data)
            observation.update(receipt_present=True, receipt_digest=digest,
                               receipt_component_id=recorded.get("organ_id"), receipt_status=recorded.get("status"),
                               receipt_verdict=replay_verdict(step, recorded),
                               receipt_native_kind=_native_kind(step, recorded), receipt_payload_digest=payload_digest(recorded, persisted=True))
            row.update(receipt_written=True, receipt_status=recorded.get("status"), receipt_sha256=digest,
                       input_tree_sha256=before[index])
            receipts[index] = (receipt, digest)
            if (observation["runner_component_id"] != step.organ_id or observation["receipt_component_id"] != step.organ_id
                    or observation["runner_status"] != observation["receipt_status"]
                    or observation["runner_payload_digest"] != observation["receipt_payload_digest"]):
                raise ValueError("runner and receipt identity or payload mismatch")
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
        source_after = _source_snapshot(root, [native_replay_step(s) for s in get_routes()], policies)
        after_identity = _json_digest(source_after)
    except Exception:
        source_after, after_identity = {}, ""
    for index, (step, row, observation) in enumerate(zip(steps, results, observations)):
        observation["source_after"] = after_identity
        try:
            _confined(root / step.example_rel, root)
            observation["input_after"] = input_tree_hash(root / step.example_rel)
            if observation["input_before"] != observation["input_after"]:
                row.update(status="input_changed", error="InputMutation")
            if index in receipts:
                path, digest = receipts[index]
                if _digest(_receipt_bytes(path, out)) != digest:
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
            "source": dict(source_before), "source_identity_material": source_before,
            "source_after": source_after, "source_identity": source_identity,
            "input_digest_scheme": "tree_type_path_bytes_posix_mode_v2",
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
