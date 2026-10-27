"""Strict short-lived component worker; never imports a caller-selected path."""
from __future__ import annotations

import importlib
import json
import math
from pathlib import Path
import runpy
import stat
import sys

def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate request key")
        result[key] = value
    return result


def _constant(_value):
    raise ValueError("non-finite JSON value")


def _float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("non-finite JSON number")
    return result


def main() -> int:
    try:
        raw = sys.stdin.buffer.read()
        request = json.loads(raw, object_pairs_hook=_object, parse_constant=_constant, parse_float=_float)
        if (type(request) is not dict or set(request) != {"slug", "payload"}
                or type(request["slug"]) is not str):
            raise ValueError("invalid request envelope")
        here = Path(__file__).resolve().parent
        kernels = runpy.run_path(str(here / "_registry.py"))["KERNELS"]
        if request["slug"] not in kernels:
            raise ValueError("unregistered component kernel")
        slug = request["slug"]
        name = kernels[slug]
        # Both paths derive exclusively from the reviewed source-code allowlist.
        package = here / slug
        generated = package / "_generated"
        adapter = package / "_adapter.py"
        if (not stat.S_ISDIR(package.lstat().st_mode)
                or not stat.S_ISREG(adapter.lstat().st_mode)):
            raise ValueError("component package or adapter must be local regular files")
        loader = runpy.run_path(str(here.parent / "_sealed_kernel.py"))
        with loader["sealed_kernel"](generated, name):
            kernel = importlib.import_module(name)
            dafny = importlib.import_module("_dafny")
            evaluate = runpy.run_path(str(adapter)).get("evaluate")
            if not callable(evaluate):
                raise ValueError("component adapter lacks evaluate")
            result = evaluate(request["payload"], kernel, dafny)
            encoded = json.dumps({"result": result}, ensure_ascii=True,
                                 allow_nan=False, separators=(",", ":"))
        print(encoded)
        return 0
    except Exception as error:
        print(json.dumps({"error": type(error).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
