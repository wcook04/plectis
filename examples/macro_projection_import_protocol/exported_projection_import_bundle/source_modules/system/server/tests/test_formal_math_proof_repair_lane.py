from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib.generated_projection_registry import get_projection_owner
from system.server.tests.test_formal_math_proofline_spine import RUN_ID, _fixture
from tools.meta.factory import build_formal_math_proof_repair_lane as repair_lane
from tools.meta.factory import build_formal_math_proofline_spine as proofline


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_ledger(repo_root: Path, *, missing_contract: bool = True) -> None:
    repair_item = {
        "id": repair_lane.REPAIR_WORK_ITEM_ID,
        "state": "captured",
        "triage_status": "needs_contract_shaping",
        "missing_contracts": ["satisfaction_contract"] if missing_contract else [],
        "projection_completeness": {"has_satisfaction_contract": not missing_contract},
    }
    _write_json(
        repo_root / "state/task_ledger/ledger.json",
        {
            "work_items": [
                repair_item,
                {"id": proofline.PRIMARY_OWNER, "state": "signoff"},
            ]
        },
    )


def _repair_fixture(repo_root: Path) -> None:
    run_root = _fixture(repo_root)
    env_path = run_root / "oracle_environment_gate_receipt.json"
    env = json.loads(env_path.read_text(encoding="utf-8"))
    env["same_candidate_reduce_existing"]["result"]["stdout_ref"] = "stdout.txt"
    env["same_candidate_reduce_existing"]["result"]["stderr_ref"] = "stderr.txt"
    _write_json(env_path, env)
    (repo_root / "stdout.txt").write_text("proof type mismatch\n", encoding="utf-8")
    (repo_root / "stderr.txt").write_text("", encoding="utf-8")
    _write_ledger(repo_root)
    proofline.write_outputs(run_id=RUN_ID, repo_root=repo_root)


def _nested_keys(payload: object) -> set[str]:
    if isinstance(payload, dict):
        keys = set(payload)
        for value in payload.values():
            keys.update(_nested_keys(value))
        return keys
    if isinstance(payload, list):
        keys: set[str] = set()
        for value in payload:
            keys.update(_nested_keys(value))
        return keys
    return set()


def test_proof_repair_lane_lands_contract_without_dispatch(tmp_path: Path) -> None:
    _repair_fixture(tmp_path)

    receipt = repair_lane.write_outputs(run_id=RUN_ID, repo_root=tmp_path)
    packet = json.loads((tmp_path / repair_lane._input_packet_path(RUN_ID)).read_text())

    assert receipt["status"] == "proof_repair_lane_not_ready_contract_landed"
    assert receipt["candidate"]["task_id"] == "verisoftbench:2"
    assert receipt["proof_repair_attempt"]["provider_dispatch_performed"] is False
    assert receipt["proof_repair_attempt"]["lean_reducer_invoked"] is False
    assert packet["owner_readiness"]["missing_contracts"] == ["satisfaction_contract"]
    assert packet["dispatch_policy"]["provider_dispatch_allowed_now"] is False
    assert _nested_keys(packet).isdisjoint(repair_lane.FORBIDDEN_INLINE_KEYS)


def test_proof_repair_lane_check_flags_body_leakage(tmp_path: Path) -> None:
    _repair_fixture(tmp_path)
    repair_lane.write_outputs(run_id=RUN_ID, repo_root=tmp_path)
    packet_path = tmp_path / repair_lane._input_packet_path(RUN_ID)
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["leak"] = {"lean_proof_body": "by exact hidden"}
    _write_json(packet_path, packet)

    check = repair_lane.check_outputs(run_id=RUN_ID, repo_root=tmp_path)

    assert check["status"] == "FAIL"
    assert any("forbidden inline body-like keys" in issue for issue in check["issues"])


def test_proof_repair_lane_check_passes_and_owner_registered(tmp_path: Path) -> None:
    _repair_fixture(tmp_path)
    repair_lane.write_outputs(run_id=RUN_ID, repo_root=tmp_path)

    check = repair_lane.check_outputs(run_id=RUN_ID, repo_root=tmp_path)
    owner = get_projection_owner(repair_lane.OWNER_ID)

    assert check["status"] == "PASS"
    assert check["lane_status"] == "proof_repair_lane_not_ready_contract_landed"
    assert str(repair_lane._input_packet_path(RUN_ID)) in owner.artifacts
    assert str(repair_lane._receipt_path(RUN_ID)) in owner.artifacts
