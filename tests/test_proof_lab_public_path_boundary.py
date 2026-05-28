from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from microcosm_core.organs.verifier_lab_kernel import (
    BUNDLE_RESULT_NAME,
    run_kernel_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle"
)


def _walk_strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        strings: list[str] = []
        for child in value.values():
            strings.extend(_walk_strings(child))
        return strings
    if isinstance(value, list):
        strings = []
        for child in value:
            strings.extend(_walk_strings(child))
        return strings
    if isinstance(value, str):
        return [value]
    return []


def test_proof_lab_bundle_receipt_normalizes_private_tmp_refs() -> None:
    out_dir = Path("/tmp") / f"microcosm-proof-lab-path-boundary-{uuid.uuid4().hex}"

    try:
        result = run_kernel_bundle(
            BUNDLE_INPUT,
            out_dir,
            command=f"microcosm proof-lab --out /tmp/{out_dir.name}",
        )

        receipt = json.loads((out_dir / BUNDLE_RESULT_NAME).read_text(encoding="utf-8"))
        strings = _walk_strings(receipt)
        component_refs = [
            ref
            for refs in receipt["component_receipt_refs"].values()
            for ref in refs
        ]

        assert result["status"] == "pass"
        assert receipt["status"] == "pass"
        assert not any("/private/tmp" in value for value in strings)
        assert not any("/Users/" in value for value in strings)
        assert not any("src/ai_workflow" in value for value in strings)
        assert receipt["receipt_paths"] == [f"/tmp/{out_dir.name}/{BUNDLE_RESULT_NAME}"]
        assert any(
            ref.startswith(f"/tmp/{out_dir.name}/components/")
            for ref in component_refs
        )
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)
