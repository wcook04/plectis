from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.validators.dependency_preflight import run_dependency_preflight


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_SUPPORT = MICROCOSM_ROOT / "core/preflight_support"
READINESS = PREFLIGHT_SUPPORT / "organ_fixture_validator_readiness_v1.json"
NEGATIVE_MATRIX = PREFLIGHT_SUPPORT / "fixture_negative_case_matrix_v1.json"


def _walk_keys(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        keys = list(payload)
        for value in payload.values():
            keys.extend(_walk_keys(value))
        return keys
    if isinstance(payload, list):
        keys: list[str] = []
        for item in payload:
            keys.extend(_walk_keys(item))
        return keys
    return []


def _copy_public_tree(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "fixtures", public_root / "fixtures")
    return public_root


def test_dependency_preflight_passes_with_public_manifest_inputs(tmp_path: Path) -> None:
    public_root = _copy_public_tree(tmp_path)
    out = public_root / "receipts/preflight/dependency_preflight.json"

    receipt = run_dependency_preflight(
        READINESS,
        NEGATIVE_MATRIX,
        out,
        command="pytest",
    )

    assert receipt["status"] == "pass"
    assert receipt["checked_organs"] == [
        "pattern_binding_contract",
        "executable_doctrine_grammar",
        "proof_diagnostic_evidence_spine",
        "navigation_hologram_route_plane",
        "mission_transaction_work_spine",
        "agent_route_observability_runtime",
        "pattern_assimilation_step",
    ]
    assert receipt["blocked_dependency_count"] == 0
    assert receipt["blocked_dependency_codes"] == []
    grammar_check = next(
        row
        for row in receipt["fixture_precondition_checks"]
        if row["organ_id"] == "executable_doctrine_grammar"
    )
    assert grammar_check["input_source"] == "public_fixture_manifest"
    assert grammar_check["missing_fixture_inputs"] == []
    assert receipt["private_state_scan"]["body_redacted"] is True
    assert receipt["private_state_scan"]["blocking_hit_count"] == 0
    text = out.read_text(encoding="utf-8")
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    assert "matched_excerpt" not in _walk_keys(receipt)
    assert "body" not in _walk_keys(receipt)


def test_dependency_preflight_blocks_unsatisfied_accepted_dependency(tmp_path: Path) -> None:
    public_root = _copy_public_tree(tmp_path)
    readiness_copy = tmp_path / "readiness.json"
    payload = json.loads(READINESS.read_text(encoding="utf-8"))
    for row in payload["organ_readiness"]:
        if row["organ_id"] == "pattern_binding_contract":
            row["build_dependencies"] = ["missing_public_root_dependency"]
            break
    readiness_copy.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    receipt = run_dependency_preflight(
        readiness_copy,
        NEGATIVE_MATRIX,
        public_root / "receipts/preflight/dependency_preflight.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert receipt["blocked_dependency_count"] == 1
    assert receipt["blocked_dependency_codes"] == ["MISSING_ACCEPTED_BUILD_DEPENDENCY"]
