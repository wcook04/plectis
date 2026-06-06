from __future__ import annotations

import json
from pathlib import Path

from microcosm_core.runtime_shell import RuntimeShell
from runtime_fixture_tree import copy_microcosm_runtime_root


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
LEGACY_TERMS = [
    "body_" + "red" + "acted",
    "private_" + "state" + "_scan",
    "public_" + "replacement_ref",
    "public_" + "replacement_landed",
]


def _copy_runtime_root(tmp_path: Path) -> Path:
    return copy_microcosm_runtime_root(
        tmp_path,
        MICROCOSM_ROOT,
        static_refs=("examples", "src"),
        mutable_refs=("core", "receipts/first_wave", "receipts/preflight"),
    )


def test_runtime_shell_source_keeps_payload_boundary_vocab_current() -> None:
    source = (MICROCOSM_ROOT / "src/microcosm_core/runtime_shell.py").read_text()

    assert "payload_boundary" in source
    assert "safe_to_show" in source
    for term in LEGACY_TERMS:
        assert term not in source


def test_first_screen_lenses_emit_payload_boundary_vocab(tmp_path: Path) -> None:
    public_root = _copy_runtime_root(tmp_path)
    shell = RuntimeShell(public_root)

    payloads = [
        shell.tour(public_root / "examples/runtime_shell/demo_project")["first_screen"],
        shell.option_surface_lens(),
        shell.stripping_guard(),
    ]
    encoded = json.dumps(payloads, sort_keys=True)

    assert "payload_boundary" in encoded
    assert "safe_to_show" in encoded
    for term in LEGACY_TERMS:
        assert term not in encoded
