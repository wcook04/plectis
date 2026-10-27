"""Run one reviewed component in a fresh interpreter, with bounded diagnostics.

Process isolation contains import and environment changes made by the existing
runners. It is not a filesystem sandbox, a provider authorization, or an HTTP
server. Process-group cleanup cannot contain a deliberately detached descendant;
that needs operating-system containment. The source tree must remain immutable
while a worker is running.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
from typing import Any

from microcosm_core.component_replay import (
    ReplaySelectionError, _component_replay_output, _confined, _json_digest,
    _receipt_bytes, _route_policy, _validate_replay_selection, replay_component,
    replay_verdict,
)
from microcosm_core.receipts import receipt_payload_digest
from microcosm_core.schemas import loads_json_strict, read_json_strict

SCHEMA = "plectis_component_replay_worker_v1"
RESULT_SCHEMA = "plectis_component_replay_worker_result_v1"
MAX_RESULT_BYTES = 16 * 1024 * 1024
_BOOTSTRAP = ("import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); "
              "runpy.run_module('microcosm_core.component_replay_worker',run_name='__main__')")


def _worker_argv(root: Path, out: Path, organ_id: str, result: Path) -> list[str]:
    """The execution route is fixed; indexed command text is never evaluated."""
    trusted_root = Path(__file__).resolve().parents[1]
    return [sys.executable, "-I", "-B", "-c", _BOOTSTRAP, str(trusted_root),
            "--root", str(root), "--out", str(out), "--result", str(result), organ_id]


def _implementation_identity() -> dict[str, Any]:
    """Bind the selected installation and its five entry/host source files.

    This prevents accidental or workspace-shadowed implementation selection. It
    does not authenticate loaded Python bytecode or an adversarial host.
    """
    from microcosm_core import component_replay, receipts, runtime_shell, schemas

    root = Path(__file__).resolve().parents[1]
    modules = {"component_replay_worker.py": Path(__file__).resolve(),
               **{name + ".py": Path(module.__file__).resolve() for name, module in (
                   ("component_replay", component_replay), ("runtime_shell", runtime_shell),
                   ("receipts", receipts), ("schemas", schemas))}}
    if any(path.parent != root / "microcosm_core" for path in modules.values()):
        raise ValueError("mixed implementation origins")
    return {"trusted_package_root": str(root),
            "replay_code_root": str(component_replay.CODE_ROOT.resolve()),
            "entry_host_sha256": {name: hashlib.sha256(_receipt_bytes(path, root)).hexdigest()
                                  for name, path in modules.items()}}


class _BoundedLog:
    def __init__(self, limit: int):
        self.limit, self.total, self.data = limit, 0, bytearray()

    def drain(self, stream) -> None:
        try:
            while chunk := stream.read(65536):
                self.total += len(chunk)
                self.data.extend(chunk[:max(0, self.limit - len(self.data))])
        finally:
            stream.close()

    def fields(self, name: str) -> dict[str, Any]:
        rendered = bytes(self.data).decode("utf-8", errors="replace").encode("utf-8")
        return {name: rendered[:self.limit].decode("utf-8", errors="ignore"),
                f"{name}_bytes": self.total,
                f"{name}_truncated": self.total > len(self.data) or len(rendered) > self.limit}


def _kill_worker(process: subprocess.Popen) -> None:
    # Adapted from corpus_readiness_mathlib_absence_gate._command_result_card:
    # native tools may have descendants, so killing only Python is insufficient.
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        elif process.poll() is None:
            process.kill()
    except ProcessLookupError:
        pass


def _run_worker(argv: list[str], root: Path, timeout: float, log_limit: int) -> dict[str, Any]:
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.update(MICROCOSM_TRACKED_RECEIPT_WRITES="0", PYTHONDONTWRITEBYTECODE="1")
    process = subprocess.Popen(argv, cwd=root, env=environment, shell=False,
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=(os.name == "posix"))
    stdout, stderr = _BoundedLog(log_limit), _BoundedLog(log_limit)
    drainers = [threading.Thread(target=log.drain, args=(stream,), daemon=True)
                for log, stream in ((stdout, process.stdout), (stderr, process.stderr))]
    for thread in drainers:
        thread.start()
    timed_out, lingering = False, False
    try:
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_worker(process)
            process.wait(timeout=5)
        for thread in drainers:
            thread.join(timeout=0.25)
        if any(thread.is_alive() for thread in drainers):
            # A descendant retained a pipe after its parent exited. Do not
            # accept a completed-looking result while that work remains live.
            lingering = True
            _kill_worker(process)
            for thread in drainers:
                thread.join(timeout=1)
    except BaseException:
        _kill_worker(process)
        process.wait(timeout=5)
        raise
    return {"spawned": True, "pid": process.pid, "return_code": process.returncode,
            "timed_out": timed_out, "lingering_descendants": lingering,
            "log_drains_complete": not any(thread.is_alive() for thread in drainers),
            "descendant_cleanup": "posix_process_group" if os.name == "posix" else "worker_process_only",
            "timeout_seconds": timeout, "max_log_bytes_per_stream": log_limit,
            **stdout.fields("stdout"), **stderr.fields("stderr")}


def _read_object(path: Path, parent: Path) -> dict[str, Any]:
    _confined(path, parent)
    if path.stat().st_size > MAX_RESULT_BYTES:
        raise ValueError("worker result exceeds size limit")
    data = _receipt_bytes(path, parent)
    if len(data) > MAX_RESULT_BYTES:
        raise ValueError("worker result exceeds size limit")
    result = loads_json_strict(data.decode("utf-8"), "component replay worker result")
    if not isinstance(result, dict):
        raise ValueError("worker result must be an object")
    _json_digest(result)  # also reject the nonfinite constants accepted by json.loads
    return result


def _validate_worker_replay(summary: dict[str, Any], root: Path, out: Path,
                            organ_id: str, selected: Any, full_routes) -> None:
    """Read the saved evidence again before exposing a worker's pass."""
    from plectis.replay import accept

    if (summary.get("schema_version") != "plectis_component_replay_gate_v2"
            or summary.get("scope") != "component"
            or summary.get("selected_organ_ids") != [organ_id]
            or type(summary.get("component_count")) is not int
            or summary.get("component_count") != 1
            or summary.get("status") not in {"pass", "blocked"}):
        raise ValueError("worker scope or verdict mismatch")
    rows = summary.get("results")
    if (not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict)
            or rows[0].get("organ_id") != organ_id):
        raise ValueError("worker component result mismatch")
    row = rows[0]
    path = Path(summary["summary_ref"])
    if (not path.is_absolute() or path.name != "component-replays.json"
            or path.parent.parent != out or not path.parent.name.startswith("run-")):
        raise ValueError("worker summary is outside its fresh output run")
    _confined(path, out)
    if _read_object(path, out) != summary:
        raise ValueError("worker summary differs from persisted result")
    admission = summary.get("admission")
    if not isinstance(admission, dict) or admission.get("kernel") != "plectis.replay.accept":
        raise ValueError("worker admission missing")
    specs, observations = admission.get("registry_specs"), admission.get("observations")
    if (not isinstance(specs, list) or len(specs) != 1
            or not isinstance(observations, list) or len(observations) != 1
            or not isinstance(specs[0], dict) or not isinstance(observations[0], dict)
            or specs[0].get("component_id") != organ_id
            or observations[0].get("component_id") != organ_id
            or admission.get("run_id") != path.parent.name):
        raise ValueError("worker observation scope mismatch")
    source = summary.get("source_identity_material")
    identity = summary.get("source_identity")
    if (not isinstance(source, dict) or summary.get("source") != source
            or identity != _json_digest(source)):
        raise ValueError("worker source identity mismatch")
    packages = source.get("runtime_package_tree_sha256")
    if (source.get("source_inventory_scheme") != "package_roots_v1"
            or source.get("runtime_package_digest_scheme") != "tree_type_path_bytes_posix_mode_v2"
            or not isinstance(packages, dict) or set(packages) != {"microcosm_core", "plectis"}
            or any(type(value) is not str or len(value) != 64
                   or any(character not in "0123456789abcdef" for character in value)
                   for value in packages.values())
            or source.get("runtime_source_tree_sha256") != _json_digest(packages)
            or source.get("runtime_source_scope") != ["microcosm_core/**", "plectis/**"]
            or summary.get("source_inventory_scheme") != source["source_inventory_scheme"]
            or summary.get("runtime_source_scope") != source["runtime_source_scope"]):
        raise ValueError("worker runtime source inventory scope mismatch")
    expected_routes = _json_digest([_route_policy(step, {}) for step in full_routes()])
    if source.get("route_contract_sha256") != expected_routes:
        raise ValueError("worker did not capture the complete route contract")
    accepted = accept(specs, identity, observations)
    if (type(admission.get("accepted")) is not bool
            or admission["accepted"] != accepted
            or (summary["status"] == "pass") != accepted):
        raise ValueError("worker admission decision mismatch")
    if not accepted:
        if summary.get("execution_state") == "pass":
            raise ValueError("blocked worker reported pass")
        return
    observation = observations[0]
    if (summary.get("execution_state") != "pass" or summary.get("failed_components") != []
            or row.get("status") != "pass" or row.get("receipt_written") is not True
            or type(row.get("primary_receipt_write_count")) is not int
            or row.get("primary_receipt_write_count") != 1
            or summary.get("source_after") != source):
        raise ValueError("worker pass has inconsistent evidence")
    receipt = Path(row["receipt_ref"])
    receipt_name = selected.receipt_name
    # The native witness writes a different name from its exported-bundle
    # compatibility route. Read that declaration without applying the native
    # override a second time or running a native tool.
    if organ_id == "formal_math_lean_proof_witness":
        from microcosm_core.organs.formal_math_lean_proof_witness import RESULT_NAME
        receipt_name = RESULT_NAME
    if (not receipt.is_absolute() or receipt.parent != path.parent / organ_id
            or receipt.name != receipt_name):
        raise ValueError("worker receipt is outside the selected component")
    data = _receipt_bytes(receipt, path.parent / organ_id)
    saved = loads_json_strict(data.decode("utf-8"), "component replay receipt")
    if not isinstance(saved, dict):
        raise ValueError("worker receipt must be an object")
    digest = hashlib.sha256(data).hexdigest()
    payload = receipt_payload_digest(saved)
    if (saved.get("organ_id") != organ_id or saved.get("status") != "pass"
            or replay_verdict(selected, saved) != "pass"
            or row.get("receipt_sha256") != digest
            or observation.get("receipt_digest") != digest
            or observation.get("receipt_payload_digest") != payload
            or observation.get("runner_payload_digest") != payload):
        raise ValueError("worker receipt binding mismatch")


def replay_component_isolated(root: Path, out: Path, organ_id: str, *,
                              timeout_seconds: float = 300,
                              max_log_bytes: int = 16384) -> dict[str, Any]:
    """Replay a known ID in a fresh process; never evaluate a command string.

    Invalid selections fail before process creation. Runners use their declared
    public inputs; this API deliberately has no custom-input or provider flag.
    """
    envelope = {"schema_version": SCHEMA, "status": "blocked", "scope": "component",
                "selected_organ_ids": [organ_id], "execution_state": "unknown",
                "replay": None, "diagnostics": [],
                "worker": {"spawned": False, "pid": None, "return_code": None,
                           "timed_out": False, "stdout": "", "stderr": ""}}
    try:
        if (isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (float, int))
                or not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 3600
                or type(max_log_bytes) is not int or not 0 <= max_log_bytes <= 1024 * 1024):
            raise ReplaySelectionError("invalid_limits", "invalid worker limits")
        from microcosm_core.runtime_shell import RUNTIME_STEPS
        root, out = _component_replay_output(root, out)
        rows = read_json_strict(root / "core/organ_registry.json")["implemented_organs"]
        selected, full_routes = _validate_replay_selection(
            organ_id, RUNTIME_STEPS, rows, lambda: RUNTIME_STEPS)
        implementation = _implementation_identity()
    except (ValueError, OSError, KeyError, TypeError) as exc:
        envelope.update(execution_state=getattr(exc, "code", "invalid_request"),
                        diagnostics=[getattr(exc, "code", type(exc).__name__)])
        return envelope
    try:
        out.mkdir(parents=True, exist_ok=True)
        control_directory = tempfile.TemporaryDirectory(prefix=".worker-", dir=out)
    except OSError as exc:
        envelope.update(execution_state="output_unavailable", diagnostics=[type(exc).__name__])
        return envelope
    with control_directory as control:
        result_path = Path(control) / "result.json"
        try:
            worker = _run_worker(_worker_argv(root, out, organ_id, result_path), root,
                                 float(timeout_seconds), max_log_bytes)
            envelope["worker"] = worker
            if os.name != "posix":
                envelope["diagnostics"].append("descendant_cleanup_not_guaranteed_on_this_platform")
            if worker["timed_out"] or worker["lingering_descendants"]:
                envelope.update(execution_state="timeout" if worker["timed_out"] else "worker_incomplete")
                envelope["diagnostics"].append(envelope["execution_state"])
                return envelope
            if worker["return_code"] not in {0, 1}:
                envelope.update(execution_state="worker_error")
                envelope["diagnostics"].append("worker_exit_rejected")
                return envelope
            result = _read_object(result_path, Path(control))
            summary = result.get("replay")
            if (set(result) != {"schema_version", "replay", "implementation"}
                    or result.get("schema_version") != RESULT_SCHEMA or not isinstance(summary, dict)):
                raise ValueError("worker did not return a replay summary")
            if result["implementation"] != implementation:
                envelope["diagnostics"].append("worker_entry_or_host_bytes_changed")
                raise ValueError("worker implementation origin or entry bytes changed")
            _validate_worker_replay(summary, root, out, organ_id, selected, full_routes)
            if worker["return_code"] != (0 if summary["status"] == "pass" else 1):
                raise ValueError("worker exit differs from replay verdict")
            envelope.update(status=summary["status"], execution_state=summary["execution_state"], replay=summary)
        except (ValueError, OSError, KeyError, TypeError, AttributeError,
                RuntimeError, subprocess.SubprocessError) as exc:
            envelope.update(execution_state="worker_result_rejected", replay=None)
            envelope["diagnostics"].append(type(exc).__name__)
    return envelope


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("organ_id")
    args = parser.parse_args(argv)
    from microcosm_core.runtime_shell import RUNTIME_STEPS
    root, out = _component_replay_output(args.root, args.out)
    _confined(args.result, out)
    registry = read_json_strict(root / "core/organ_registry.json")
    summary = replay_component(root, out, args.organ_id, declared_steps=RUNTIME_STEPS,
                               registry_rows=registry["implemented_organs"],
                               route_provider=lambda: RUNTIME_STEPS)
    args.result.write_text(json.dumps({"schema_version": RESULT_SCHEMA, "replay": summary,
                                      "implementation": _implementation_identity()},
                                     allow_nan=False) + "\n", encoding="utf-8")
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
