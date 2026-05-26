from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from microcosm_core import cli
from microcosm_core.runtime_shell import PROOF_LAB_RECEIPT_REF, PROOF_LAB_ROUTE_REF


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle"
)
RECEIPT_NAME = "exported_verifier_lab_kernel_bundle_validation_result.json"


def _proof_lab_result(receipt: Path) -> dict:
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
        "component_statuses": {
            "formal_math_lean_proof_witness": "pass",
        },
        "body_in_receipt": False,
        "authority_ceiling": {"status": "pass"},
        "anti_claim": "proof-lab CLI smoke receipt",
        "receipt_paths": [str(receipt)],
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(receipt_payload), encoding="utf-8")
    return receipt_payload


def test_cli_proof_lab_alias_prints_first_screen_card(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out_dir = tmp_path / "proof-lab"
    receipt = out_dir / RECEIPT_NAME
    display_out = cli._proof_lab_output_ref(str(out_dir))
    display_receipt = f"{display_out}/{RECEIPT_NAME}"

    def run_fake_bundle(input_path: str, output_path: str, *, command: str) -> dict:
        assert Path(input_path).resolve(strict=False) == BUNDLE_INPUT
        assert Path(output_path) == out_dir
        assert command == f"microcosm proof-lab --out {display_out}"
        return _proof_lab_result(receipt)

    monkeypatch.setattr(cli.verifier_lab_kernel, "run_kernel_bundle", run_fake_bundle)

    status = cli.main(["proof-lab", "--out", str(out_dir)])

    output = capsys.readouterr().out
    payload = json.loads(output)
    public_input_ref = "examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle"
    assert status == 0
    assert payload["schema_version"] == "microcosm_proof_lab_first_screen_card_v1"
    assert payload["card_id"] == "first_screen_verifier_lab_kernel"
    assert payload["status"] == "pass"
    assert payload["command"] == f"microcosm proof-lab --out {display_out}"
    assert payload["expanded_command"] == (
        "microcosm verifier-lab-kernel run-kernel-bundle "
        f"--input {public_input_ref} --out {display_out}"
    )
    assert payload["endpoint"] == "/proof-lab"
    assert payload["alias_endpoints"] == ["/verifier-lab-kernel"]
    assert payload["source_lens_endpoint"] == "/proof-loop-depth"
    assert payload["input_ref"] == public_input_ref
    assert payload["bundle_ref"] == public_input_ref
    assert payload["route_id"] == "formal_prover_context_strategy_gate"
    assert payload["route_ref"] == PROOF_LAB_ROUTE_REF
    assert payload["proof_lab_route_id"] == "formal_prover_context_strategy_gate"
    assert payload["proof_lab_route_component_count"] == 9
    assert payload["lean_lake_return_code"] == 0
    assert payload["lean_compiled_declaration_count"] == 8
    assert payload["safe_to_show"]["body_in_receipt"] is False
    assert payload["safe_to_show"]["proof_bodies_exported"] is False
    assert payload["safe_to_show"]["provider_payloads_exported"] is False
    assert payload["safe_to_show"]["host_private_paths_exported"] is False
    assert payload["safe_to_show"]["route_metadata_visible"] is True
    assert receipt.is_file()
    assert payload["receipt_ref"] == display_receipt
    receipt_payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert receipt_payload["status"] == "pass"
    assert receipt_payload["component_statuses"]["formal_math_lean_proof_witness"] == "pass"
    assert payload["canonical_receipt_ref"] == PROOF_LAB_RECEIPT_REF
    assert payload["receipt_refs"] == [display_receipt]
    assert "receipt only after the first-screen card is visible" in payload[
        "reader_action"
    ]
    assert payload["next_commands"] == [
        "microcosm status --card",
        "microcosm proof-loop-depth",
        f"microcosm evidence inspect {display_receipt}",
    ]
    assert "microcosm evidence list" not in payload["next_commands"]
    assert str(MICROCOSM_ROOT) not in output
    assert "/private/tmp" not in output


def test_cli_proof_lab_accepts_copied_input_bundle_outside_public_root(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_dir = tmp_path / "copied-verifier-bundle"
    shutil.copytree(BUNDLE_INPUT, input_dir)
    out_dir = tmp_path / "proof-lab"
    receipt = out_dir / RECEIPT_NAME
    display_input = cli._proof_lab_input_ref(str(input_dir))
    display_out = cli._proof_lab_output_ref(str(out_dir))
    display_receipt = f"{display_out}/{RECEIPT_NAME}"

    def run_fake_bundle(input_path: str, output_path: str, *, command: str) -> dict:
        assert Path(input_path) == input_dir
        assert Path(output_path) == out_dir
        assert command == f"microcosm proof-lab --input {display_input} --out {display_out}"
        return _proof_lab_result(receipt)

    monkeypatch.setattr(cli.verifier_lab_kernel, "run_kernel_bundle", run_fake_bundle)

    status = cli.main(
        [
            "proof-lab",
            "--input",
            str(input_dir),
            "--out",
            str(out_dir),
        ]
    )

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert status == 0
    assert payload["status"] == "pass"
    assert payload["command"] == (
        f"microcosm proof-lab --input {display_input} --out {display_out}"
    )
    assert payload["expanded_command"] == (
        "microcosm verifier-lab-kernel run-kernel-bundle "
        f"--input {display_input} --out {display_out}"
    )
    assert payload["input_ref"] == display_input
    assert payload["route_id"] == "formal_prover_context_strategy_gate"
    assert payload["proof_lab_route_component_count"] == 9
    assert payload["lean_lake_return_code"] == 0
    assert receipt.is_file()
    assert payload["receipt_ref"] == display_receipt
    assert payload["receipt_refs"] == [display_receipt]
    assert str(MICROCOSM_ROOT) not in output
