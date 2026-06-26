from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from microcosm_core import cli
from microcosm_core import runtime_shell


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
    assert action["command"] == "plectis proof-lab --out /tmp/microcosm-proof-lab"
    assert action["boundary"] == "fresh_tmp_receipt_not_canonical_or_proof_authority"


def _assert_proof_lab_status_scope(proof_lab: dict) -> None:
    if proof_lab["cache_status"] in {
        "stale_cached_receipt",
        "missing_cached_receipt",
    }:
        assert proof_lab["status_scope"] == "route_presence_not_cache_freshness"
        assert proof_lab["fresh_receipt_required"] is True
        return

    assert proof_lab["status_scope"] == "route_presence_and_cache_freshness"
    assert proof_lab["fresh_receipt_required"] is False


def test_status_card_explains_actionable_proof_lab_cache() -> None:
    _run_json("tour", "--card", ".")
    payload = _run_json("status", "--card", ".")
    proof_lab = payload["front_door"]["proof_lab"]
    assert "cache_action" in proof_lab
    _assert_proof_lab_status_scope(proof_lab)
    assert payload["proof_lab"]["status_scope"] == proof_lab["status_scope"]
    assert (
        payload["proof_lab"]["fresh_receipt_required"]
        is proof_lab["fresh_receipt_required"]
    )

    if proof_lab["cache_status"] != "stale_cached_receipt":
        assert proof_lab["cache_action"]["status"] == "not_needed"
        return

    assert proof_lab["status"] == "pass"
    _assert_public_safe_cache_action(proof_lab["cache_action"])


def test_status_card_uses_current_default_proof_lab_receipt(
    monkeypatch,
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "microcosm-proof-lab"
    out_dir.mkdir()
    receipt = out_dir / cli.verifier_lab_kernel.BUNDLE_RESULT_NAME
    shutil.copyfile(cli._canonical_proof_lab_receipt_path(), receipt)
    monkeypatch.setattr(cli, "DEFAULT_PROOF_LAB_OUT", str(out_dir))

    payload = {
        "proof_lab": {
            "status": "pass",
            "endpoint": "/proof-lab",
            "route_id": "formal_prover_context_strategy_gate",
            "receipt_ref": cli.PROOF_LAB_RECEIPT_REF,
            "route_component_count": 9,
            "safe_to_show": {
                "proof_bodies_exported": False,
                "proof_correctness_claim": False,
            },
            "cache_status": "stale_cached_receipt",
            "cache_action": {
                "status": "actionable",
                "command": "microcosm proof-lab --out /tmp/microcosm-proof-lab",
            },
        },
        "front_door": {},
        "front_door_status": {"surface_statuses": {}},
    }

    updated = cli._attach_status_card_front_door_refs(payload)

    assert updated["proof_lab"]["cache_status"] == "cached_receipt_read"
    assert updated["front_door"]["proof_lab"]["cache_status"] == "cached_receipt_read"
    _assert_proof_lab_status_scope(updated["front_door"]["proof_lab"])
    assert updated["front_door"]["proof_lab"]["cache_action"]["status"] == "not_needed"
    assert "next_commands" not in updated["proof_lab"]
    assert (
        updated["front_door_status"]["surface_statuses"]["proof_lab_cache"]
        == "pass"
    )


def test_runtime_status_card_uses_current_default_proof_lab_receipt(
    monkeypatch,
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "microcosm-proof-lab"
    out_dir.mkdir()
    receipt = out_dir / cli.verifier_lab_kernel.BUNDLE_RESULT_NAME
    shutil.copyfile(cli._canonical_proof_lab_receipt_path(), receipt)
    monkeypatch.setattr(
        runtime_shell,
        "_default_proof_lab_receipt_path",
        lambda: receipt,
    )
    original_cache_freshness = runtime_shell._proof_lab_cache_freshness
    canonical_receipt = MICROCOSM_ROOT / runtime_shell.PROOF_LAB_RECEIPT_REF

    def cache_freshness(root: Path, receipt_path: Path) -> dict:
        if receipt_path == canonical_receipt:
            return {
                "schema_version": "microcosm_proof_lab_cache_freshness_v1",
                "status": "stale",
                "input_status": "stale",
                "input_refs_exported": False,
            }
        return original_cache_freshness(root, receipt_path)

    monkeypatch.setattr(runtime_shell, "_proof_lab_cache_freshness", cache_freshness)

    payload = runtime_shell.RuntimeShell(MICROCOSM_ROOT).status_card(
        ".",
        project_ref="<project>",
    )

    assert payload["proof_lab"]["cache_status"] == "cached_receipt_read"
    _assert_proof_lab_status_scope(payload["proof_lab"])
    _assert_proof_lab_status_scope(payload["front_door"]["proof_lab"])
    assert payload["front_door"]["proof_lab"]["cache_action"]["status"] == "not_needed"
    assert (
        payload["front_door"]["proof_lab"]["current_receipt_ref"]
        == f"{runtime_shell.PROOF_LAB_DEFAULT_OUT_REF}/{receipt.name}"
    )
    assert (
        payload["front_door_status"]["surface_statuses"]["proof_lab_cache"]
        == "pass"
    )
    assert "proof_lab_cache" not in payload["front_door_status"][
        "actionable_surface_ids"
    ]


def test_runtime_proof_lab_cache_freshness_streams_bundle_inputs_without_rglob(
    monkeypatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "microcosm-root"
    input_dir = root / runtime_shell.PROOF_LAB_BUNDLE_REF
    nested = input_dir / "nested"
    nested.mkdir(parents=True)
    first = input_dir / "proof_lab_route.json"
    second = nested / "bundle_manifest.json"
    first.write_text("{}", encoding="utf-8")
    second.write_text("{}", encoding="utf-8")
    receipt = tmp_path / "cached_proof_lab_receipt.json"
    receipt.write_text("{}", encoding="utf-8")
    latest_input_mtime_ns = max(
        first.stat().st_mtime_ns,
        second.stat().st_mtime_ns,
    )
    os.utime(
        receipt,
        ns=(latest_input_mtime_ns + 1_000_000, latest_input_mtime_ns + 1_000_000),
    )

    def guarded_rglob(self: Path, *_args, **_kwargs):
        raise AssertionError("proof-lab cache freshness should stream without rglob")

    monkeypatch.setattr(Path, "rglob", guarded_rglob)

    freshness = runtime_shell._proof_lab_cache_freshness(root, receipt)

    assert freshness["status"] == "current"
    assert freshness["input_status"] == "current"
    assert freshness["tracked_input_count"] == 2
    assert freshness["stale_input_count"] == 0


def test_tour_card_carries_proof_lab_cache_action_hint() -> None:
    payload = _run_json("tour", "--card", ".")
    proof_lab = payload["proof_lab"]
    assert "cache_action" in proof_lab
    _assert_proof_lab_status_scope(proof_lab)

    if proof_lab["cache_status"] != "stale_cached_receipt":
        assert proof_lab["cache_action"]["status"] == "not_needed"
        return

    _assert_public_safe_cache_action(proof_lab["cache_action"])
