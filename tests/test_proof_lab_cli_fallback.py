from __future__ import annotations

import json
from pathlib import Path

from microcosm_core import cli
from microcosm_core.runtime_shell import PROOF_LAB_RECEIPT_REF
from microcosm_core.organs import verifier_lab_kernel


def test_proof_lab_cli_uses_canonical_receipt_when_toolchain_missing(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    tool_versions = {
        "lean_available": False,
        "lake_available": False,
        "lean_version_command": {"return_code": 1, "body_redacted": True},
        "lake_version_command": {"return_code": 1, "body_redacted": True},
    }
    monkeypatch.setattr(
        cli.formal_math_lean_proof_witness,
        "_tool_versions",
        lambda: tool_versions,
    )

    def _unexpected_live_rebuild(*args, **kwargs):
        raise AssertionError("toolchain-missing fallback should skip live rebuild")

    monkeypatch.setattr(
        verifier_lab_kernel,
        "run_kernel_bundle",
        _unexpected_live_rebuild,
    )

    out_dir = tmp_path / "proof-lab"
    display_out = cli._proof_lab_output_ref(str(out_dir))
    status = cli.main(["proof-lab", "--out", str(out_dir)])
    payload = json.loads(capsys.readouterr().out)
    receipt_path = out_dir / verifier_lab_kernel.BUNDLE_RESULT_NAME
    display_receipt = f"{display_out}/{verifier_lab_kernel.BUNDLE_RESULT_NAME}"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    assert status == 0
    assert payload["status"] == "pass"
    assert payload["cache_status"] == "canonical_receipt_fallback_toolchain_missing"
    assert payload["live_receipt_rebuild_status"] == "skipped_toolchain_missing"
    assert payload["local_toolchain_status"] == "missing_lean_lake"
    assert payload["canonical_receipt_ref"] == PROOF_LAB_RECEIPT_REF
    assert payload["receipt_ref"] == display_receipt
    assert payload["safe_to_show"]["host_private_paths_exported"] is False
    assert payload["lean_lake_return_code"] == 0
    assert payload["proof_lab_route_component_count"] == 9
    assert payload["safe_to_show"]["proof_bodies_exported"] is False
    assert payload["safe_to_show"]["proof_correctness_claim"] is False
    assert "first-screen proof-lab route" in payload["authority"]
    assert payload["anti_claims"]["proof_correctness_claim"] is False
    assert payload["anti_claims"]["provider_calls_authorized"] is False
    assert (
        payload["anti_claims"]["proof_bodies_or_provider_payloads_exported"]
        is False
    )
    assert payload["authority_ceiling"]["formal_proof_authority"] is False
    assert "bundled canonical public receipt" in payload["fallback_reason"]

    assert receipt["status"] == "pass"
    assert receipt["canonical_receipt_ref"] == PROOF_LAB_RECEIPT_REF
    assert receipt["local_toolchain_status"] == "missing_lean_lake"
    assert receipt["live_receipt_rebuild_status"] == "skipped_toolchain_missing"
    assert receipt["tool_versions"] == tool_versions
