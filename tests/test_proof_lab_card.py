from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from microcosm_core import cli


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_cli_proof_lab_card_reads_cached_receipt_without_rerun(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out_dir = tmp_path / "proof-lab"
    out_dir.mkdir()
    receipt = out_dir / "exported_verifier_lab_kernel_bundle_validation_result.json"
    receipt_payload = {
        "schema_version": "exported_verifier_lab_kernel_bundle_validation_result_v1",
        "status": "pass",
        "proof_lab_route_id": "formal_prover_context_strategy_gate",
        "proof_lab_route_component_count": 9,
        "lean_lake_return_code": 0,
        "lean_compiled_declaration_count": 8,
        "proof_lab_component_metrics": {
            "corpus_count": 7,
            "retrieval_query_count": 4,
            "ring2_mean_precision_at_k": 0.36,
            "proof_diagnostic_accepted_count": 1,
        },
        "body_in_receipt": False,
        "authority_ceiling": {"status": "pass"},
        "anti_claim": "receipt-only proof-lab card",
        "receipt_paths": [str(receipt)],
    }
    receipt.write_text(json.dumps(receipt_payload), encoding="utf-8")

    def fail_if_rerun(*_args: object, **_kwargs: object) -> dict:
        raise AssertionError("cached proof-lab card must not rerun the verifier bundle")

    monkeypatch.setattr(cli.verifier_lab_kernel, "run_kernel_bundle", fail_if_rerun)

    status = cli.main(["proof-lab", "--card", "--out", str(out_dir)])

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert status == 0
    assert payload["schema_version"] == "microcosm_proof_lab_first_screen_card_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == f"microcosm proof-lab --card --out {out_dir}"
    assert payload["cache_status"] == "cached_receipt_read"
    assert payload["cached_receipt_ref"] == str(receipt)
    assert payload["cached_receipt_bytes"] == receipt.stat().st_size
    assert payload["cache_freshness"]["status"] == "current"
    assert payload["cache_freshness"]["input_status"] == "current"
    assert payload["cache_freshness"]["tracked_input_count"] == 3
    assert payload["cache_freshness"]["input_refs_exported"] is False
    assert payload["receipt_ref"] == str(receipt)
    assert payload["receipt_refs"] == [str(receipt)]
    assert payload["lean_lake_return_code"] == 0
    assert payload["component_metrics"]["corpus_count"] == 7
    assert payload["safe_to_show"]["body_in_receipt"] is False
    assert payload["safe_to_show"]["input_refs_exported"] is False
    assert "input_refs" not in payload
    assert str(MICROCOSM_ROOT) not in output


def test_cli_proof_lab_card_marks_input_bundle_stale_without_rerun(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_dir = tmp_path / "verifier-bundle"
    input_dir.mkdir()
    input_file = input_dir / "verifier_lab_packet.json"
    input_file.write_text("{}", encoding="utf-8")
    out_dir = tmp_path / "proof-lab"
    out_dir.mkdir()
    receipt = out_dir / "exported_verifier_lab_kernel_bundle_validation_result.json"
    receipt.write_text(
        json.dumps(
            {
                "schema_version": "exported_verifier_lab_kernel_bundle_validation_result_v1",
                "status": "pass",
                "proof_lab_route_id": "formal_prover_context_strategy_gate",
                "proof_lab_route_component_count": 9,
                "lean_lake_return_code": 0,
                "lean_compiled_declaration_count": 8,
                "proof_lab_component_metrics": {"corpus_count": 1},
                "body_in_receipt": False,
                "authority_ceiling": {"status": "pass"},
                "anti_claim": "receipt-only proof-lab card",
                "receipt_paths": [str(receipt)],
            }
        ),
        encoding="utf-8",
    )
    stale_mtime_ns = receipt.stat().st_mtime_ns + 1_000_000_000
    os.utime(input_file, ns=(stale_mtime_ns, stale_mtime_ns))

    def fail_if_rerun(*_args: object, **_kwargs: object) -> dict:
        raise AssertionError("stale proof-lab card must not rerun the verifier bundle")

    monkeypatch.setattr(cli.verifier_lab_kernel, "run_kernel_bundle", fail_if_rerun)

    status = cli.main(
        [
            "proof-lab",
            "--card",
            "--input",
            str(input_dir),
            "--out",
            str(out_dir),
        ]
    )

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert status == 1
    assert payload["status"] == "stale_cached_receipt"
    assert payload["command"] == (
        f"microcosm proof-lab --card --input {input_dir} --out {out_dir}"
    )
    assert payload["cache_status"] == "stale_cached_receipt"
    assert payload["cache_freshness"]["status"] == "stale"
    assert payload["cache_freshness"]["input_status"] == "stale"
    assert payload["cache_freshness"]["tracked_input_count"] == 1
    assert payload["cache_freshness"]["stale_input_count"] == 1
    assert payload["cache_freshness"]["input_refs_exported"] is False
    assert payload["safe_to_show"]["input_refs_exported"] is False
    assert payload["receipt_ref"] == str(receipt)
    assert "input_refs" not in payload
    assert str(MICROCOSM_ROOT) not in output
