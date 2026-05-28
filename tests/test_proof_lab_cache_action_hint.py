from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _run_json(*args: str) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    result = subprocess.run(
        [sys.executable, "-m", "microcosm_core", *args],
        cwd=MICROCOSM_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    return payload


def _assert_public_safe_cache_action(action: dict) -> None:
    assert action["status"] == "actionable"
    assert action["command"] == "microcosm proof-lab --out /tmp/microcosm-proof-lab"
    assert action["boundary"] == "fresh_tmp_receipt_not_canonical_or_proof_authority"


def test_status_card_explains_actionable_proof_lab_cache() -> None:
    _run_json("tour", "--card", ".")
    payload = _run_json("status", "--card", ".")
    proof_lab = payload["front_door"]["proof_lab"]
    assert "cache_action" in proof_lab

    if proof_lab["cache_status"] != "stale_cached_receipt":
        assert proof_lab["cache_action"]["status"] == "not_needed"
        return

    _assert_public_safe_cache_action(proof_lab["cache_action"])


def test_tour_card_carries_proof_lab_cache_action_hint() -> None:
    payload = _run_json("tour", "--card", ".")
    proof_lab = payload["proof_lab"]
    assert "cache_action" in proof_lab

    if proof_lab["cache_status"] != "stale_cached_receipt":
        assert proof_lab["cache_action"]["status"] == "not_needed"
        return

    _assert_public_safe_cache_action(proof_lab["cache_action"])
