from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from microcosm_core import cli
from microcosm_core import runtime_shell


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
RECEIPT_NAME = "exported_verifier_lab_kernel_bundle_validation_result.json"


def _display_out(path: Path) -> str:
    return cli._proof_lab_output_ref(str(path))


def _display_receipt(path: Path) -> str:
    return f"{_display_out(path.parent)}/{path.name}"


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
    display_out = _display_out(out_dir)
    display_receipt = _display_receipt(receipt)

    def fail_if_rerun(*_args: object, **_kwargs: object) -> dict:
        raise AssertionError("cached proof-lab card must not rerun the verifier bundle")

    monkeypatch.setattr(cli.verifier_lab_kernel, "run_kernel_bundle", fail_if_rerun)

    status = cli.main(["proof-lab", "--card", "--out", str(out_dir)])

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert status == 0
    assert payload["schema_version"] == "microcosm_proof_lab_first_screen_card_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == f"plectis proof-lab --card --out {display_out}"
    assert payload["cache_status"] == "cached_receipt_read"
    assert payload["cached_receipt_ref"] == display_receipt
    assert payload["cached_receipt_bytes"] == receipt.stat().st_size
    assert payload["cache_freshness"]["status"] == "current"
    assert payload["cache_freshness"]["input_status"] == "current"
    expected_input_count = len(
        cli._proof_lab_input_files(str(cli.DEFAULT_PROOF_LAB_INPUT))
    )
    assert payload["cache_freshness"]["tracked_input_count"] == expected_input_count
    assert expected_input_count >= 1
    assert payload["cache_freshness"]["input_refs_exported"] is False
    assert payload["receipt_ref"] == display_receipt
    assert payload["receipt_refs"] == [display_receipt]
    assert payload["lean_lake_return_code"] == 0
    assert payload["component_metrics"]["corpus_count"] == 7
    assert payload["safe_to_show"]["body_in_receipt"] is False
    assert payload["safe_to_show"]["proof_correctness_claim"] is False
    assert payload["safe_to_show"]["input_refs_exported"] is False
    assert payload["safe_to_show"]["host_private_paths_exported"] is False
    assert "first-screen proof-lab route" in payload["authority"]
    assert payload["anti_claims"]["proof_correctness_claim"] is False
    assert payload["anti_claims"]["provider_calls_authorized"] is False
    assert payload["anti_claims"]["source_mutation_authorized"] is False
    assert (
        payload["anti_claims"]["credential_equivalent_live_access_exported"]
        is False
    )
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
    display_input = cli._proof_lab_input_ref(str(input_dir))
    display_out = _display_out(out_dir)
    display_receipt = _display_receipt(receipt)
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
    assert status == 0
    assert payload["status"] == "stale_cached_receipt"
    assert payload["command"] == (
        f"plectis proof-lab --card --input {display_input} --out {display_out}"
    )
    assert payload["cache_status"] == "stale_cached_receipt"
    assert payload["cache_action"]["status"] == "actionable"
    assert payload["cache_action"]["command"] == (
        "plectis proof-lab --out /tmp/microcosm-proof-lab"
    )
    assert payload["cache_freshness"]["status"] == "stale"
    assert payload["cache_freshness"]["input_status"] == "stale"
    assert payload["cache_freshness"]["tracked_input_count"] == 1
    assert payload["cache_freshness"]["stale_input_count"] == 1
    assert payload["cache_freshness"]["input_refs_exported"] is False
    assert payload["safe_to_show"]["input_refs_exported"] is False
    assert payload["safe_to_show"]["host_private_paths_exported"] is False
    assert (
        payload["anti_claims"]["proof_bodies_or_provider_payloads_exported"]
        is False
    )
    assert payload["cached_receipt_ref"] == display_receipt
    assert payload["receipt_ref"] == display_receipt
    assert "input_refs" not in payload
    assert str(MICROCOSM_ROOT) not in output


def test_cli_proof_lab_cache_freshness_streams_bundle_inputs_without_rglob(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_dir = tmp_path / "verifier-bundle"
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

    def guarded_rglob(self: Path, *_args: object, **_kwargs: object) -> object:
        raise AssertionError("CLI proof-lab cache freshness should stream without rglob")

    monkeypatch.setattr(Path, "rglob", guarded_rglob)

    freshness = cli._proof_lab_cache_freshness(str(input_dir), receipt)

    assert freshness["status"] == "current"
    assert freshness["input_status"] == "current"
    assert freshness["tracked_input_count"] == 2
    assert freshness["stale_input_count"] == 0


def test_cli_proof_lab_cache_freshness_skips_symlinked_input_files(
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "verifier-bundle"
    input_dir.mkdir()
    direct = input_dir / "proof_lab_route.json"
    direct.write_text("{}", encoding="utf-8")
    outside = tmp_path / "outside_payload.json"
    outside.write_text('{"outside": true}', encoding="utf-8")
    symlink = input_dir / "linked_payload.json"
    try:
        symlink.symlink_to(outside)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    receipt = tmp_path / "cached_proof_lab_receipt.json"
    receipt.write_text("{}", encoding="utf-8")
    base_mtime_ns = direct.stat().st_mtime_ns
    os.utime(receipt, ns=(base_mtime_ns + 1_000_000, base_mtime_ns + 1_000_000))
    os.utime(outside, ns=(base_mtime_ns + 2_000_000, base_mtime_ns + 2_000_000))

    freshness = cli._proof_lab_cache_freshness(str(input_dir), receipt)

    assert freshness["status"] == "current"
    assert freshness["input_status"] == "current"
    assert freshness["tracked_input_count"] == 1
    assert freshness["stale_input_count"] == 0
    assert symlink not in cli._proof_lab_input_files(str(input_dir))


def test_cli_proof_lab_cache_freshness_skips_unreadable_scan_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_dir = tmp_path / "verifier-bundle"
    nested = input_dir / "nested"
    nested.mkdir(parents=True)
    direct = input_dir / "proof_lab_route.json"
    direct.write_text("{}", encoding="utf-8")
    skipped = nested / "bundle_manifest.json"
    skipped.write_text("{}", encoding="utf-8")
    receipt = tmp_path / "cached_proof_lab_receipt.json"
    receipt.write_text("{}", encoding="utf-8")
    base_mtime_ns = direct.stat().st_mtime_ns
    os.utime(receipt, ns=(base_mtime_ns + 1_000_000, base_mtime_ns + 1_000_000))
    original_scandir = cli.os.scandir

    def guarded_scandir(path: object) -> object:
        try:
            path_ref = Path(path)
        except TypeError:
            return original_scandir(path)
        if path_ref == nested:
            raise OSError("transient scan failure")
        return original_scandir(path)

    monkeypatch.setattr(cli.os, "scandir", guarded_scandir)

    freshness = cli._proof_lab_cache_freshness(str(input_dir), receipt)

    assert freshness["status"] == "current"
    assert freshness["input_status"] == "current"
    assert freshness["tracked_input_count"] == 1
    assert freshness["stale_input_count"] == 0
    assert cli._proof_lab_input_files(str(nested)) == []


def test_cli_proof_lab_cached_result_treats_unreadable_receipt_metadata_as_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_dir = tmp_path / "verifier-bundle"
    input_dir.mkdir()
    (input_dir / "proof_lab_route.json").write_text("{}", encoding="utf-8")
    out_dir = tmp_path / "proof-lab"
    out_dir.mkdir()
    receipt = out_dir / cli.verifier_lab_kernel.BUNDLE_RESULT_NAME
    receipt.write_text(
        json.dumps(
            {
                "schema_version": "exported_verifier_lab_kernel_bundle_validation_result_v1",
                "status": "pass",
                "proof_lab_component_metrics": {},
                "body_in_receipt": False,
                "authority_ceiling": {"status": "pass"},
                "anti_claim": "receipt-only proof-lab card",
                "receipt_paths": [str(receipt)],
            }
        ),
        encoding="utf-8",
    )
    original_stat = Path.stat

    def guarded_stat(self: Path, *_args: object, **_kwargs: object) -> object:
        if self == receipt:
            raise OSError("transient receipt metadata failure")
        return original_stat(self, *_args, **_kwargs)

    monkeypatch.setattr(
        cli,
        "_proof_lab_canonical_receipt_result",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(Path, "stat", guarded_stat)

    payload = cli._proof_lab_cached_result(str(input_dir), str(out_dir))

    assert payload["status"] == "missing_cached_receipt"
    assert payload["cache_status"] == "missing_cached_receipt"
    assert payload["cached_receipt_bytes"] == 0
    assert payload["cache_freshness"]["status"] == "missing_cached_receipt"
    assert payload["cache_freshness"]["input_status"] == "not_checked"


def test_runtime_shell_proof_lab_cache_freshness_skips_symlinked_input_files(
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / runtime_shell.PROOF_LAB_BUNDLE_REF
    input_dir.mkdir(parents=True)
    direct = input_dir / "proof_lab_route.json"
    direct.write_text("{}", encoding="utf-8")
    outside = tmp_path / "outside_payload.json"
    outside.write_text('{"outside": true}', encoding="utf-8")
    symlink = input_dir / "linked_payload.json"
    try:
        symlink.symlink_to(outside)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    receipt = tmp_path / runtime_shell.PROOF_LAB_RECEIPT_REF
    receipt.parent.mkdir(parents=True)
    receipt.write_text("{}", encoding="utf-8")
    base_mtime_ns = direct.stat().st_mtime_ns
    os.utime(receipt, ns=(base_mtime_ns + 1_000_000, base_mtime_ns + 1_000_000))
    os.utime(outside, ns=(base_mtime_ns + 2_000_000, base_mtime_ns + 2_000_000))

    freshness = runtime_shell._proof_lab_cache_freshness(tmp_path, receipt)

    assert freshness["status"] == "current"
    assert freshness["input_status"] == "current"
    assert freshness["tracked_input_count"] == 1
    assert freshness["stale_input_count"] == 0
    assert symlink not in runtime_shell._proof_lab_input_files(tmp_path)


def test_runtime_shell_proof_lab_cache_freshness_skips_unreadable_scan_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_dir = tmp_path / runtime_shell.PROOF_LAB_BUNDLE_REF
    nested = input_dir / "nested"
    nested.mkdir(parents=True)
    direct = input_dir / "proof_lab_route.json"
    direct.write_text("{}", encoding="utf-8")
    skipped = nested / "bundle_manifest.json"
    skipped.write_text("{}", encoding="utf-8")
    receipt = tmp_path / runtime_shell.PROOF_LAB_RECEIPT_REF
    receipt.parent.mkdir(parents=True)
    receipt.write_text("{}", encoding="utf-8")
    base_mtime_ns = direct.stat().st_mtime_ns
    os.utime(receipt, ns=(base_mtime_ns + 1_000_000, base_mtime_ns + 1_000_000))
    original_scandir = runtime_shell.os.scandir

    def guarded_scandir(path: object) -> object:
        try:
            path_ref = Path(path)
        except TypeError:
            return original_scandir(path)
        if path_ref == nested:
            raise OSError("transient scan failure")
        return original_scandir(path)

    monkeypatch.setattr(runtime_shell.os, "scandir", guarded_scandir)

    freshness = runtime_shell._proof_lab_cache_freshness(tmp_path, receipt)

    assert freshness["status"] == "current"
    assert freshness["input_status"] == "current"
    assert freshness["tracked_input_count"] == 1
    assert freshness["stale_input_count"] == 0


def test_runtime_shell_proof_lab_card_treats_unreadable_receipt_metadata_as_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_dir = tmp_path / runtime_shell.PROOF_LAB_BUNDLE_REF
    input_dir.mkdir(parents=True)
    (input_dir / "proof_lab_route.json").write_text("{}", encoding="utf-8")
    receipt = tmp_path / runtime_shell.PROOF_LAB_RECEIPT_REF
    receipt.parent.mkdir(parents=True)
    receipt.write_text(
        json.dumps(
            {
                "schema_version": "exported_verifier_lab_kernel_bundle_validation_result_v1",
                "status": "pass",
                "proof_lab_component_metrics": {},
                "body_in_receipt": False,
                "authority_ceiling": {"status": "pass"},
                "anti_claim": "receipt-only proof-lab card",
                "receipt_paths": [str(receipt)],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        runtime_shell,
        "_current_default_proof_lab_receipt",
        lambda _root: None,
    )
    original_stat = Path.stat

    def guarded_stat(self: Path, *_args: object, **_kwargs: object) -> object:
        if self == receipt:
            raise OSError("transient receipt metadata failure")
        return original_stat(self, *_args, **_kwargs)

    monkeypatch.setattr(Path, "stat", guarded_stat)

    payload = runtime_shell._proof_lab_first_screen_card(tmp_path)

    assert payload["cache_status"] == "missing_cached_receipt"
    assert payload["cached_receipt_bytes"] == 0
    assert payload["cache_freshness"]["status"] == "missing_cached_receipt"
    assert payload["cache_freshness"]["input_status"] == "not_checked"


def test_proof_lab_card_display_refs_do_not_export_host_private_temp_roots() -> None:
    private_tmp_out = "/private/tmp/microcosm-proof-lab"
    host_private_out = "/private/var/folders/wn/example/microcosm-proof-lab"
    host_private_input = "/private/var/folders/wn/example/verifier-bundle"

    assert cli._proof_lab_output_ref(private_tmp_out) == "/tmp/microcosm-proof-lab"
    assert cli._proof_lab_output_ref(host_private_out) == cli.PROOF_LAB_OUT_PLACEHOLDER
    assert cli._proof_lab_input_ref(host_private_input) == cli.PROOF_LAB_INPUT_PLACEHOLDER

    card = cli._proof_lab_first_screen_card(
        {
            "status": "pass",
            "proof_lab_route_id": "formal_prover_context_strategy_gate",
            "proof_lab_route_component_count": 9,
            "receipt_paths": [
                f"{host_private_out}/{RECEIPT_NAME}",
            ],
            "cached_receipt_ref": f"{host_private_out}/{RECEIPT_NAME}",
            "body_in_receipt": False,
        },
        input_path=host_private_input,
        out_dir=host_private_out,
        command=cli._proof_lab_command(host_private_input, host_private_out),
    )

    serialized = json.dumps(card, sort_keys=True)
    assert "/private/var/folders" not in serialized
    assert card["command"] == (
        "plectis proof-lab --input <proof-lab-input> --out <proof-lab-out>"
    )
    assert card["expanded_command"] == (
        "plectis verifier-lab-kernel run-kernel-bundle "
        "--input <proof-lab-input> --out <proof-lab-out>"
    )
    assert card["input_ref"] == "<proof-lab-input>"
    assert card["out_ref"] == "<proof-lab-out>"
    assert card["cached_receipt_ref"] == f"<proof-lab-out>/{RECEIPT_NAME}"
    assert card["receipt_ref"] == f"<proof-lab-out>/{RECEIPT_NAME}"
    assert card["next_commands"][2] == (
        f"plectis evidence inspect <proof-lab-out>/{RECEIPT_NAME}"
    )
    assert card["safe_to_show"]["host_private_paths_exported"] is False
    assert card["anti_claims"]["release_or_publication_authorized"] is False
    assert card["anti_claims"]["credential_equivalent_live_access_exported"] is False


def test_runtime_shell_proof_lab_card_preserves_receipt_anti_claim(
    tmp_path: Path,
) -> None:
    receipt_path = tmp_path / runtime_shell.PROOF_LAB_RECEIPT_REF
    receipt_path.parent.mkdir(parents=True)
    input_file = (
        tmp_path / runtime_shell.PROOF_LAB_BUNDLE_REF / "proof_lab_route.json"
    )
    input_file.parent.mkdir(parents=True)
    input_file.write_text("{}", encoding="utf-8")
    anti_claim = "receipt-only proof-lab browser card"
    receipt_path.write_text(
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
                "anti_claim": anti_claim,
                "receipt_paths": [str(receipt_path)],
            }
        ),
        encoding="utf-8",
    )

    card = runtime_shell._proof_lab_first_screen_card(tmp_path)

    assert card["anti_claim"] == anti_claim
    assert card["anti_claims"]["proof_correctness_claim"] is False
    assert card["anti_claims"]["provider_calls_authorized"] is False
    assert card["safe_to_show"]["proof_bodies_omitted"] is True
