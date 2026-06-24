from __future__ import annotations

import ast
from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]

RELEASE_FACING_ORGAN_MODULES = (
    "src/microcosm_core/organs/agent_benchmark_integrity_anti_gaming_replay.py",
    "src/microcosm_core/organs/agent_monitor_redteam_falsification_replay.py",
)

REQUIRED_MODULE_TAGS = (
    "[PURPOSE]",
    "[INTERFACE]",
    "[FLOW]",
    "[DEPENDENCIES]",
    "[CONSTRAINTS]",
)


def test_release_facing_organ_modules_carry_python_standard_docs() -> None:
    for rel in RELEASE_FACING_ORGAN_MODULES:
        tree = ast.parse((MICROCOSM_ROOT / rel).read_text(encoding="utf-8"))
        module_doc = ast.get_docstring(tree) or ""
        for tag in REQUIRED_MODULE_TAGS:
            assert tag in module_doc, f"{rel} missing {tag}"

        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                doc = ast.get_docstring(node) or ""
                assert "[ACTION]" in doc, f"{rel}::{node.name} missing [ACTION]"
