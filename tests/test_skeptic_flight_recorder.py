from __future__ import annotations

import json
from pathlib import Path

from microcosm_core.skeptic_flight_recorder import (
    CommandSpec,
    RunnerResult,
    build_flight_recorder_packet,
    verify_flight_recorder_packet,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_skeptic_flight_recorder_preserves_blocked_authority_evidence(
    tmp_path: Path,
) -> None:
    root = tmp_path / "microcosm-root"
    (root / "src/microcosm_core").mkdir(parents=True)
    (root / "src/microcosm_core/__init__.py").write_text("", encoding="utf-8")
    out_dir = root / ".microcosm/flight"

    def fake_snapshot(snapshot_root: Path) -> dict[str, str]:
        assert snapshot_root == root.resolve(strict=False)
        return {"src/microcosm_core/__init__.py": "stable"}

    def fake_runner(
        spec: CommandSpec,
        cwd: Path,
        env: dict[str, str],
    ) -> RunnerResult:
        assert cwd == root.resolve(strict=False)
        assert env["MICROCOSM_RUNTIME_RECEIPT_WRITES"] == "0"
        if spec.command_id == "authority_card":
            payload = {
                "schema_version": "microcosm_public_authority_card_v1",
                "status": "blocked",
                "command": "plectis authority --card",
                "authority_ceiling": {
                    "provider_calls_authorized": False,
                    "release_authorized": False,
                    "source_mutation_authorized": False,
                },
                "evidence_class_counts": {
                    "semantic_validator": 2,
                    "algorithmic_projection": 1,
                },
                "unsafe_payload_bodies_exported": False,
            }
            return RunnerResult(
                returncode=1,
                stdout=json.dumps(payload).encode("utf-8"),
                stderr=b"",
                duration_seconds=0.01,
            )
        if spec.command_id == "check_smoke_outputs":
            return RunnerResult(
                returncode=1,
                stdout=b"",
                stderr=b"Plectis smoke check: fail\nreason: authority blocked\n",
                duration_seconds=0.01,
            )
        payload = {
            "schema_version": f"{spec.command_id}_v1",
            "status": "pass",
            "command": " ".join(spec.display_argv),
            "safe_to_show": {
                "provider_calls_authorized": False,
                "source_files_mutated": False,
            },
        }
        if spec.command_id == "hello":
            return RunnerResult(
                returncode=0,
                stdout=b"Plectis first screen\n",
                stderr=b"",
                duration_seconds=0.01,
            )
        if spec.command_id == "version":
            return RunnerResult(
                returncode=0,
                stdout=b"plectis 0.1.0\n",
                stderr=b"",
                duration_seconds=0.01,
            )
        return RunnerResult(
            returncode=0,
            stdout=json.dumps(payload).encode("utf-8"),
            stderr=b"",
            duration_seconds=0.01,
        )

    packet = build_flight_recorder_packet(
        root=root,
        out_dir=out_dir,
        python_executable="python",
        runner=fake_runner,
        snapshotter=fake_snapshot,
        generated_at="2026-05-31T00:00:00+00:00",
    )

    packet_path = root / packet["packet_ref"]
    card_path = root / packet["human_card_ref"]
    authority = next(
        row for row in packet["commands"] if row["command_id"] == "authority_card"
    )

    assert packet["schema_version"] == "microcosm_skeptic_flight_recorder_packet_v2"
    assert packet["first_action_proof"]["status"] == "blocked"
    assert packet["first_action_proof"]["schema_version"] == (
        "microcosm_flight_recorder_first_action_proof_v1"
    )
    assert {
        row["command_id"] for row in packet["evaluator_verdict"]["refused_claims"]
    } >= {"first_action_proof"}
    assert packet["status"] == "pass"
    assert packet["evaluator_verdict"]["status"] == "mixed_claims_preserved"
    assert packet["evaluator_verdict"]["command_status_summary"][
        "nonzero_return_code_command_ids"
    ] == ["authority_card", "check_smoke_outputs"]
    assert packet["evaluator_verdict"]["evidence_class_counts"] == {
        "algorithmic_projection": 1,
        "semantic_validator": 2,
    }
    assert authority["selected_json_fields"]["status"] == "blocked"
    assert authority["selected_json_fields"]["authority_ceiling"][
        "provider_calls_authorized"
    ] is False
    assert packet["recorder_integrity"]["private_path_scan"]["status"] == "pass"
    assert packet["recorder_integrity"]["source_mutation_check"][
        "source_files_mutated"
    ] is False
    assert packet_path.is_file()
    assert card_path.is_file()
    assert "authority_card" in card_path.read_text(encoding="utf-8")
    packet_text = packet_path.read_text(encoding="utf-8")
    assert "actual_argv" not in packet_text
    assert "/Users/" not in packet_text
    assert "src/ai_workflow" not in packet_text

    verification = verify_flight_recorder_packet(
        packet_dir=out_dir,
        root=root,
        write_receipt=True,
        verified_at="2026-05-31T00:01:00+00:00",
    )

    verification_path = out_dir / "flight-recorder-verification.json"
    assert verification["status"] == "packet_valid"
    assert verification["statuses"] == ["packet_valid"]
    assert verification["no_substrate_rerun"] is True
    assert verification["provider_calls_authorized"] is False
    assert verification["command_receipts"]["digest_mismatch_count"] == 0
    assert verification["private_path_scan"]["private_path_hit_count"] == 0
    assert verification_path.is_file()
    verification_text = verification_path.read_text(encoding="utf-8")
    assert "/Users/" not in verification_text
    assert "src/ai_workflow" not in verification_text

    hello = next(row for row in packet["commands"] if row["command_id"] == "hello")
    hello_stdout = root / hello["stdout_path"]
    hello_stdout.write_text("tampered\n", encoding="utf-8")
    tampered = verify_flight_recorder_packet(
        packet_dir=out_dir,
        root=root,
        write_receipt=False,
        verified_at="2026-05-31T00:02:00+00:00",
    )

    assert tampered["status"] == "digest_mismatch"
    assert "digest_mismatch" in tampered["statuses"]
    assert tampered["command_receipts"]["digest_mismatch_count"] == 1

    card_path.write_text(
        card_path.read_text(encoding="utf-8") + "\n/Users/example/private\n",
        encoding="utf-8",
    )
    leaked = verify_flight_recorder_packet(
        packet_dir=out_dir,
        root=root,
        write_receipt=False,
        verified_at="2026-05-31T00:03:00+00:00",
    )

    assert leaked["status"] == "private_path_leak"
    assert "private_path_leak" in leaked["statuses"]
    assert leaked["private_path_scan"]["private_path_hit_count"] >= 1


def test_skeptic_flight_recorder_is_publicly_discoverable() -> None:
    makefile = (MICROCOSM_ROOT / "Makefile").read_text(encoding="utf-8")
    readme = (MICROCOSM_ROOT / "README.md").read_text(encoding="utf-8")

    assert "FLIGHT_RECORDER_OUT ?= .microcosm/skeptic-flight-recorder" in makefile
    assert "FLIGHT_RECORDER_VERIFY_DIR ?= $(FLIGHT_RECORDER_OUT)" in makefile
    assert "flight-recorder:" in makefile
    assert "flight-recorder-verify:" in makefile
    assert (
        "PYTHONPATH=src $(PYTHON) scripts/skeptic_flight_recorder.py --root . "
        "--out $(FLIGHT_RECORDER_OUT) --python $(PYTHON)"
    ) in makefile
    assert (
        "PYTHONPATH=src $(PYTHON) scripts/skeptic_flight_recorder.py verify "
        "$(FLIGHT_RECORDER_VERIFY_DIR) --root ."
    ) in makefile

    assert "make flight-recorder" in readme
    assert "make flight-recorder-verify" in readme
    assert "without rerunning the substrate" in readme
    assert "blocked/non-zero commands as preserved evidence" in readme
    assert "does not authorize release, standards" in readme
    assert "provider calls, proof correctness" in readme
