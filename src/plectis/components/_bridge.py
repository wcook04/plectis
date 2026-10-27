"""Run a registered generated component kernel in an isolated interpreter.

Python, the host adapter, process and source tree remain trusted. Isolation
prevents ambient imports and accidental generated-module collisions; it is not
an OS sandbox or a proof about the caller's input observations.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import stat
import subprocess
import sys

from ._registry import KERNELS
from .._sealed_kernel import read_kernel_snapshot

def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate response key")
        result[key] = value
    return result


def _constant(_value):
    raise ValueError("non-finite JSON value")


def _float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("non-finite JSON number")
    return result


def kernel_identity(slug: str) -> dict:
    """Bind receipt freshness to the validated kernel and its trusted host code.

    This performs the sealed inventory/hash checks even when a caller plans to
    reuse a cached receipt. Integrity failures propagate; they never authorize
    a cache hit. The identity does not prove the Python host or its observations.
    """
    if type(slug) is not str or slug not in KERNELS:
        raise ValueError("unregistered component kernel")
    here = Path(__file__).resolve().parent
    package = here / slug
    if not stat.S_ISDIR(package.lstat().st_mode):
        raise ValueError("component package must be a local real directory")
    module = KERNELS[slug]
    generated = package / "_generated"
    snapshot = read_kernel_snapshot(generated, module)
    paths = {
        "components/__init__.py": here / "__init__.py",
        "components/_bridge.py": here / "_bridge.py",
        "components/_worker.py": here / "_worker.py",
        "components/_registry.py": here / "_registry.py",
        "_sealed_kernel.py": here.parent / "_sealed_kernel.py",
        f"components/{slug}/__init__.py": package / "__init__.py",
        f"components/{slug}/_adapter.py": package / "_adapter.py",
    }
    trusted_host = {}
    for relative, path in sorted(paths.items()):
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError("component host source must be a local regular file: " + relative)
        trusted_host[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "schema_version": 1,
        "slug": slug,
        "module": module,
        "generated_python": {name: hashlib.sha256(data).hexdigest()
                             for name, data in sorted(snapshot.items())},
        "generated_manifest_sha256": hashlib.sha256(
            (generated / "GENERATED_SHA256.json").read_bytes()).hexdigest(),
        "trusted_host": trusted_host,
    }


def invoke(slug: str, payload):
    """Invoke a registered component; raise on invalid input or worker failure.

    Component-specific type and semantic validation belongs to its trusted
    adapter. The worker has a 30-second timeout. No Python decision or
    unverified implementation is used as a fallback when it fails.
    """
    if type(slug) is not str or slug not in KERNELS:
        raise ValueError("unregistered component kernel")
    try:
        request = json.dumps({"slug": slug, "payload": payload},
                             allow_nan=False, ensure_ascii=True, separators=(",", ":"))
    except (TypeError, ValueError, OverflowError, RecursionError) as error:
        raise ValueError("component payload must be JSON-safe") from error
    worker = Path(__file__).resolve().with_name("_worker.py")
    try:
        process = subprocess.run([sys.executable, "-I", "-B", str(worker)],
                                 input=request, text=True, capture_output=True,
                                 timeout=30, check=False)
        response = json.loads(process.stdout, object_pairs_hook=_object,
                              parse_constant=_constant, parse_float=_float)
    except (OSError, ValueError, subprocess.TimeoutExpired, RecursionError) as error:
        raise RuntimeError("component kernel worker failed") from error
    if process.returncode != 0 or type(response) is not dict or set(response) != {"result"}:
        raise RuntimeError("component kernel worker returned invalid output")
    return response["result"]
