from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MICROCOSM_ROOT.parent


def _source_modules_root(path: Path) -> Path:
    parts = path.parts
    source_index = parts.index("source_modules")
    return Path(*parts[: source_index + 1])


def test_agent_execution_trace_source_modules_import_without_macro_root() -> None:
    copied_sources = sorted(
        MICROCOSM_ROOT.glob("**/source_modules/**/agent_execution_trace.py")
    )

    assert len(copied_sources) >= 13

    failures: list[dict[str, object]] = []
    for source_path in copied_sources:
        source_root = _source_modules_root(source_path)
        relative_module_path = source_path.relative_to(source_root).with_suffix("")
        module_name = ".".join(relative_module_path.parts)
        strict_json_path = source_root / "system/lib/strict_json.py"
        assert strict_json_path.is_file()

        script = """
import importlib
import json
import os
import sys

source_root = os.environ["SOURCE_ROOT"]
repo_root = os.environ["REPO_ROOT"]
module_name = os.environ["MODULE_NAME"]
sys.path = [source_root] + [
    item
    for item in sys.path
    if item and not os.path.abspath(item).startswith(repo_root)
]

try:
    module = importlib.import_module(module_name)
    strict_json = importlib.import_module("system.lib.strict_json")
    module_file = os.path.abspath(getattr(module, "__file__", "") or "")
    strict_json_file = os.path.abspath(getattr(strict_json, "__file__", "") or "")
    ok = (
        module_file.startswith(source_root + os.sep)
        and strict_json_file.startswith(source_root + os.sep)
    )
    print(json.dumps({
        "ok": ok,
        "module_file": module_file,
        "strict_json_file": strict_json_file,
    }))
except Exception as exc:
    print(json.dumps({
        "ok": False,
        "error_type": type(exc).__name__,
        "error": str(exc),
    }))
"""
        env = {
            key: value
            for key, value in os.environ.items()
            if key not in {"PYTHONHOME", "PYTHONPATH"}
        }
        env.update(
            {
                "MODULE_NAME": module_name,
                "PYTHONNOUSERSITE": "1",
                "REPO_ROOT": str(REPO_ROOT.resolve()),
                "SOURCE_ROOT": str(source_root.resolve()),
            }
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd="/tmp",
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        if result.returncode != 0 or not payload["ok"]:
            failures.append(
                {
                    "source_path": str(source_path.relative_to(MICROCOSM_ROOT)),
                    "module_name": module_name,
                    "returncode": result.returncode,
                    "payload": payload,
                    "stderr": result.stderr,
                }
            )

    assert failures == []
