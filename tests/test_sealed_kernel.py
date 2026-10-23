"""Execution identity at the generated-source import boundary, not a sandbox."""
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import py_compile
import runpy
import shutil
import subprocess
import sys
from types import ModuleType

import pytest

from plectis import _sealed_kernel as loader
from plectis.repair import _host


ROOT = Path(__file__).resolve().parents[1]
REQUESTS = {
    "Repair": {"op": "make", "deps": [[], [0]], "roots": [True, False],
               "effects": [False, True]},
    "Compatibility": {"old_next": [[0]], "old_output": [[0]], "old_initial": 0,
                      "new_next": [[0]], "new_output": [[1]], "new_initial": 0,
                      "inputs": 1, "relation": [[True]]},
}
EXPECTED = {
    "Repair": {"accepted": True, "dirty": [True, True], "blocked": [False, True]},
    "Compatibility": {"accepted": False},
}


@pytest.fixture(params=REQUESTS)
def deployment(request, tmp_path):
    name = request.param
    root = tmp_path / "deployment"
    for relative in ("src/plectis", "formal/repair", "formal/compatibility",
                     "scripts/check"):
        shutil.copytree(ROOT / relative, root / relative,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return root, name


def generated(root, name):
    return root / "src/plectis" / name.lower() / "_generated"


def worker(root, name):
    script = root / "src/plectis" / name.lower() / "_worker.py"
    run = subprocess.run([sys.executable, "-I", "-B", str(script)],
                         input=json.dumps(REQUESTS[name]), text=True,
                         capture_output=True, timeout=15, check=False)
    return run.returncode, json.loads(run.stdout)


def binding(root, name):
    script = root / "scripts/check" / ("check_" + name.lower() + "_kernel.py")
    checker = runpy.run_path(str(script))
    return checker["check_binding"](root, generated(root, name))


def poison(marker, name):
    """A test-only module whose import must never occur in the patched worker."""
    source = "from pathlib import Path\nPath(" + repr(str(marker)) + ").touch()\n"
    if name == "Repair":
        return source + """class default__:
    @staticmethod
    def ValidInputs(*args): return True
    @staticmethod
    def MakePlan(deps, roots, effects): return [False]*len(deps), [False]*len(deps)
    @staticmethod
    def CheckPlan(*args): return True
"""
    return source + """class default__:
    @staticmethod
    def Check(*args): return True
"""


def test_clean_deployment_checks_and_executes(deployment):
    root, name = deployment
    binding(root, name)
    assert worker(root, name) == (0, EXPECTED[name])


@pytest.mark.parametrize("sourceless", [False, True])
def test_same_named_package_is_refused_before_execution(deployment, tmp_path,
                                                       sourceless):
    root, name = deployment
    directory = generated(root, name)
    original = loader.read_kernel_snapshot(directory, name)
    package = directory / name
    package.mkdir()
    marker = tmp_path / "shadow-was-executed"
    source = package / "__init__.py"
    source.write_text(poison(marker, name))
    if sourceless:
        # A .py-only inventory and a fresh pycache_prefix miss this import route.
        py_compile.compile(str(source), cfile=str(package / "__init__.pyc"),
                           doraise=True)
        source.unlink()
    assert all((directory / path).read_bytes() == data
               for path, data in original.items())
    with pytest.raises(ValueError, match="unexpected generated directory"):
        binding(root, name)
    status, response = worker(root, name)
    assert status == 2 and set(response) == {"error"}
    assert not marker.exists()


def test_valid_poisoned_timestamp_cache_is_never_loaded(deployment, tmp_path):
    root, name = deployment
    directory = generated(root, name)
    source = directory / (name + ".py")
    original, times = source.read_bytes(), source.stat()
    marker = tmp_path / "cache-was-executed"
    mutant = poison(marker, name).encode()
    assert len(mutant) < len(original)
    source.write_bytes(mutant + b" " * (len(original) - len(mutant)))
    os.utime(source, ns=(times.st_atime_ns, times.st_mtime_ns))
    # CI may set PYTHONPYCACHEPREFIX on this parent. The isolated negative
    # control ignores it, so ask that interpreter for the cache it will load.
    cache_probe = subprocess.run(
        [sys.executable, "-I", "-B", "-c",
         "import importlib.util, sys; print(importlib.util.cache_from_source(sys.argv[1]))",
         str(source)], capture_output=True, text=True, check=True, timeout=15,
    )
    cache = Path(cache_probe.stdout.strip())
    py_compile.compile(str(source), cfile=str(cache), doraise=True,
                       invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP)
    source.write_bytes(original)
    os.utime(source, ns=(times.st_atime_ns, times.st_mtime_ns))
    # Establish that this is executable, timestamp-valid bytecode, not junk a
    # normal importer would ignore. All mutations are in the disposable copy.
    command = "import sys; sys.path.insert(0, sys.argv[1]); __import__(sys.argv[2])"
    old_import = subprocess.run([sys.executable, "-I", "-B", "-c", command,
                                 str(directory), name], capture_output=True,
                                text=True, timeout=15, check=False)
    assert old_import.returncode == 0, old_import.stderr
    assert marker.exists()
    marker.unlink()
    binding(root, name)
    assert worker(root, name) == (0, EXPECTED[name])
    assert cache.exists() and not marker.exists()


def test_symlink_to_even_identical_source_is_refused(deployment, tmp_path):
    root, name = deployment
    source = generated(root, name) / (name + ".py")
    external = tmp_path / "same-source.py"
    external.write_bytes(source.read_bytes())
    source.unlink()
    source.symlink_to(external)
    with pytest.raises(ValueError, match="symlink"):
        binding(root, name)
    status, response = worker(root, name)
    assert status == 2 and "symlink" in response["error"]


def test_local_manifest_cannot_approve_changed_source(deployment):
    root, name = deployment
    directory = generated(root, name)
    source = directory / (name + ".py")
    source.write_bytes(source.read_bytes() + b"\n# changed\n")
    manifest = directory / "GENERATED_SHA256.json"
    entries = json.loads(manifest.read_text())
    entries[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(entries))
    with pytest.raises(ValueError, match="reviewed loader pin"):
        loader.read_kernel_snapshot(directory, name)
    assert worker(root, name)[0] == 2


def test_source_after_snapshot_cannot_replace_imported_bytes(deployment, monkeypatch):
    root, name = deployment
    directory = generated(root, name)
    capture = loader.read_kernel_snapshot

    def change_after_capture(path, kernel_name):
        snapshot = capture(path, kernel_name)
        (Path(path) / (kernel_name + ".py")).write_text(
            'raise RuntimeError("source changed after capture")\n')
        return snapshot

    monkeypatch.setattr(loader, "read_kernel_snapshot", change_after_capture)
    with loader.sealed_kernel(directory, name):
        module = importlib.import_module(name)
        assert Path(module.__file__).parent != directory
        assert hasattr(module, "default__")
    assert name not in sys.modules and "_dafny" not in sys.modules


def test_ambient_generated_module_is_refused(deployment, monkeypatch):
    root, name = deployment
    monkeypatch.setitem(sys.modules, name, ModuleType(name))
    with pytest.raises(ValueError, match="already present"):
        with loader.sealed_kernel(generated(root, name), name):
            pytest.fail("ambient module was admitted")


@pytest.mark.parametrize("response", [
    {"accepted": True, "dirty": [1], "blocked": [False]},
    {"accepted": True, "dirty": [], "blocked": [False]},
    {"accepted": True, "dirty": [True], "blocked": [False], "extra": True},
    {"accepted": True, "dirty": [True], "blocked": "x"},
])
def test_repair_host_rejects_malformed_plan_response(monkeypatch, response):
    monkeypatch.setattr(_host.subprocess, "run", lambda command, **kwargs:
                        subprocess.CompletedProcess(command, 0, json.dumps(response), ""))
    with pytest.raises(_host.InvalidPlan):
        _host.make_plan([[]], [True], [False])


def test_repair_host_rejects_extra_verdict_field(monkeypatch):
    monkeypatch.setattr(_host.subprocess, "run", lambda command, **kwargs:
                        subprocess.CompletedProcess(command, 0,
                                                    '{"accepted":true,"extra":false}', ""))
    with pytest.raises(_host.InvalidPlan):
        _host.check_plan([[]], [True], [False], [True], [False])
