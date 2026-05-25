from __future__ import annotations

import json
import shutil
from pathlib import Path

from microcosm_core.runtime_shell import RuntimeShell


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
LEGACY_TERMS = [
    "body_" + "red" + "acted",
    "private_" + "state" + "_scan",
    "public_" + "replacement_ref",
    "public_" + "replacement_landed",
]


def _copy_runtime_root(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "examples", public_root / "examples")
    shutil.copytree(MICROCOSM_ROOT / "src", public_root / "src")
    shutil.copytree(MICROCOSM_ROOT / "receipts/first_wave", public_root / "receipts/first_wave")
    shutil.copytree(MICROCOSM_ROOT / "receipts/preflight", public_root / "receipts/preflight")
    return public_root


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
