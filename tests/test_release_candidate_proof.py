"""Release-candidate proof: the First Correct Action product must be distribution-true.

The hero goal must resolve to the same complete, graph-backed first-action
contract in the source checkout, a fresh package install, and the standalone
export — and the proof machinery (flight recorder first_action_proof block,
three-context release-candidate packet, no-rerun verifiers) must derive every
claim from digest-bound evidence and refuse tampered or divergent packets.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from microcosm_core import comprehension, release_export
from microcosm_core import release_candidate_proof
from microcosm_core.release_candidate_proof import (
    COMMITTED_DEMO_RECEIPT_REL,
    CONTEXT_IDS,
    EXPECTATION_EVIDENCE_REF,
    EXTERNAL_SIGNATURE_STATUS,
    INSTALL_EVIDENCE_SOURCES,
    build_release_candidate_proof,
    derive_cross_context_agreement,
    derive_expectation_policy,
    extract_committed_expectation,
    verify_release_candidate_proof,
)
from microcosm_core.skeptic_flight_recorder import (
    FIRST_ACTION_CLONE_GOAL,
    FIRST_ACTION_HERO_GOAL,
    CommandSpec,
    RunnerResult,
    _packet_payload_sha256,
    build_flight_recorder_packet,
    command_plan,
    first_action_contract_checks,
    verify_flight_recorder_packet,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]

HERO_CONTRACT_PAYLOAD = {
    "schema_version": "microcosm_comprehension_read_pack_v0",
    "found": True,
    "goal": FIRST_ACTION_HERO_GOAL,
    "owner": {
        "organ_id": "finance_forecast_evaluation_spine",
        "display_name": "Finance Forecast Evaluation Spine",
        "evidence_class": "external_subprocess_witness",
        "task_class": "finance",
    },
    "first_action": {
        "action_kind": "run_fixture_command",
        "command": (
            "PYTHONPATH=src python3 -m microcosm_core "
            "finance-forecast-evaluation-spine run "
            "--input fixtures/first_wave/finance_forecast_evaluation_spine/input "
            "--out receipts/first_wave/finance_forecast_evaluation_spine"
        ),
        "writes_outputs_under": "receipts/first_wave/finance_forecast_evaluation_spine",
        "clean_run": {
            "command": (
                "PYTHONPATH=src python3 -m microcosm_core "
                "finance-forecast-evaluation-spine run "
                "--input fixtures/first_wave/finance_forecast_evaluation_spine/input "
                "--out .microcosm/first_action_runs/finance_forecast_evaluation_spine"
            ),
        },
    },
    "proof_path": {
        "runnable_validator": (
            "PYTHONPATH=src python3 -m "
            "microcosm_core.organs.finance_forecast_evaluation_spine run "
            "--input fixtures/first_wave/finance_forecast_evaluation_spine/input "
            "--out receipts/first_wave/finance_forecast_evaluation_spine"
        ),
        "validator_command": (
            "python -m microcosm_core.organs.finance_forecast_evaluation_spine run "
            "--input fixtures/first_wave/finance_forecast_evaluation_spine/input"
        ),
        "authority_receipt": (
            "receipts/acceptance/first_wave/"
            "finance_forecast_evaluation_spine_fixture_acceptance.json"
        ),
        "receipt_refs": ["r1", "r2", "r3", "r4"],
    },
    "reading_boundary": {
        "allowed_scope": "synthetic fixture forecast-evaluation statistics only",
        "stop_condition": (
            "Stop when the first command or named result record is visible."
        ),
    },
    "do_not_claim": "synthetic fixture forecast-evaluation statistics only",
    "authority_ceiling": {
        "release_authorized": False,
        "source_body_export_authorized": False,
        "static_analysis_authority": False,
        "whole_system_correctness_authorized": False,
    },
    "graph_backed": {
        "source": "receipts/code_lens/code_lens_join_index_v0.json#graph",
        "source_schema": "microcosm_code_lens_join_index_v2",
    },
}

ASSAY_PAYLOAD = {
    "schema_version": "microcosm_first_action_assay_v0",
    "scenarios": 19,
    "source_body_leaks": 0,
    "contract_completeness_pct": 100.0,
    "degraded": False,
}


def _clone_contract_payload() -> dict:
    payload = json.loads(json.dumps(HERO_CONTRACT_PAYLOAD))
    payload["goal"] = FIRST_ACTION_CLONE_GOAL
    return payload


def test_first_action_release_candidate_proof_is_distribution_true() -> None:
    """The product the docs sell must be the product every distribution ships.

    Static distribution pins plus an in-process hero compile: FIRST_ACTION.md
    and the comprehension substrate ship in sdist/wheel/export, the installed
    root resolves, the hero contract is complete with no placeholder, and the
    proof lanes (smoke, flight recorder, release-candidate target) all carry
    the first-action encounter.
    """
    manifest = (MICROCOSM_ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    assert "include FIRST_ACTION.md" in manifest

    pyproject = tomllib.loads(
        (MICROCOSM_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    data_files = pyproject.get("tool", {}).get("setuptools", {}).get("data-files", {})
    share_root = data_files.get("share/microcosm-substrate") or []
    assert "FIRST_ACTION.md" in share_root
    assert any(
        destination.startswith("share/microcosm-substrate/receipts/code_lens")
        for destination in data_files
    ), sorted(data_files)

    assert "FIRST_ACTION.md" in release_export.DEFAULT_INCLUDE_REFS
    assert "FIRST_ACTION.md" in release_export.STANDALONE_REQUIRED_PUBLIC_REFS

    # The installed-root ladder must resolve this checkout, and the live
    # compiler must convert the hero goal into a complete contract using the
    # same completeness predicate every proof surface uses.
    assert comprehension.default_root() == MICROCOSM_ROOT
    bundle = comprehension.load_inputs(MICROCOSM_ROOT)
    contract = comprehension.compile_first_action(
        bundle, MICROCOSM_ROOT, FIRST_ACTION_HERO_GOAL
    )
    checks = first_action_contract_checks(contract, 0)
    assert checks == {key: True for key in checks}, checks
    assert comprehension._first_action_contract_complete(contract)
    command = str((contract.get("first_action") or {}).get("command") or "")
    assert "<" not in command

    first_action_doc = (MICROCOSM_ROOT / "FIRST_ACTION.md").read_text(encoding="utf-8")
    assert FIRST_ACTION_HERO_GOAL in first_action_doc
    assert (MICROCOSM_ROOT / "receipts/code_lens/first_action_demo.json").is_file()

    # The committed demonstration is the proof's expectation anchor: its hero
    # row must keep carrying the canonical validator form the live encounters
    # project, and the live extraction must match the live compile.
    committed_demo = json.loads(
        (MICROCOSM_ROOT / COMMITTED_DEMO_RECEIPT_REL).read_text(encoding="utf-8")
    )
    committed_expectation = extract_committed_expectation(committed_demo)
    assert committed_expectation["committed_demonstration_present"] is True
    assert committed_expectation["expected_owner_organ_id"] == (
        (contract.get("owner") or {}).get("organ_id")
    )
    assert committed_expectation["expected_command"] == command
    assert committed_expectation["expected_validator_command"] == (
        (contract.get("proof_path") or {}).get("validator_command")
        or (contract.get("proof_path") or {}).get("runnable_validator")
    )

    makefile = (MICROCOSM_ROOT / "Makefile").read_text(encoding="utf-8")
    assert f'comprehend --first-action "{FIRST_ACTION_CLONE_GOAL}"' in makefile
    assert "release-candidate-proof:" in makefile
    assert "release-candidate-proof-verify:" in makefile
    assert "tests/test_release_candidate_proof.py" in makefile
    assert "tests/test_skeptic_flight_recorder.py" in makefile

    package_smoke = (MICROCOSM_ROOT / "scripts/package_install_smoke.py").read_text(
        encoding="utf-8"
    )
    assert FIRST_ACTION_HERO_GOAL in package_smoke
    assert "comprehension-assay" in package_smoke

    # The flight recorder probes the same encounter with the same goals — and
    # the clone-entry probe must feed smoke/first-action.json BEFORE the
    # check_smoke_outputs probe validates that directory, or the recorder's
    # smoke gate silently degrades to a permanent refused claim.
    plan = command_plan(MICROCOSM_ROOT, MICROCOSM_ROOT / ".microcosm/x", "python3")
    plan_ids = [spec.command_id for spec in plan]
    assert {"first_action_contract", "first_action_hero", "first_action_assay"} <= set(
        plan_ids
    )
    assert plan_ids.index("first_action_contract") < plan_ids.index("check_smoke_outputs")
    contract_spec = next(s for s in plan if s.command_id == "first_action_contract")
    assert contract_spec.stdout_relpath == "smoke/first-action.json"

    # The export-context guard depends on release_export's artifact layout.
    assert (
        release_candidate_proof.EXPORT_ARTIFACT_DIR_NAME
        == release_export.ARTIFACT_DIR_NAME
    )

    # The fresh_install copy contract: the smoke's check names produce exactly
    # the output filenames the proof copies (name + json/txt suffix), and the
    # smoke must scrub a caller PYTHONPATH so the venv console proves the
    # INSTALLED copy rather than a shadowing checkout.
    assert INSTALL_EVIDENCE_SOURCES[0][0] == "first-action.json"
    assert INSTALL_EVIDENCE_SOURCES[1][0] == "first-action-assay.txt"
    assert '"first-action",' in package_smoke
    assert '"first-action-assay",' in package_smoke
    assert 'env.pop("PYTHONPATH", None)' in package_smoke
    assert "import microcosm_core; print(microcosm_core.__file__)" in package_smoke
    assert "workdir: <work-dir>" in package_smoke


def _flight_recorder_fake_runner(
    contract_payload: dict | None = None,
) -> "callable":
    hero_payload = contract_payload or HERO_CONTRACT_PAYLOAD

    def fake_runner(spec: CommandSpec, cwd: Path, env: dict[str, str]) -> RunnerResult:
        if spec.command_id == "first_action_hero":
            body = json.dumps(hero_payload).encode("utf-8")
        elif spec.command_id == "first_action_contract":
            body = json.dumps(_clone_contract_payload()).encode("utf-8")
        elif spec.command_id == "first_action_assay":
            body = json.dumps(ASSAY_PAYLOAD).encode("utf-8")
        elif spec.command_id == "hello":
            body = b"Microcosm first screen\n"
        elif spec.command_id == "version":
            body = b"microcosm 0.1.0\n"
        else:
            body = json.dumps(
                {
                    "schema_version": f"{spec.command_id}_v1",
                    "status": "pass",
                    "safe_to_show": {"provider_calls_authorized": False},
                }
            ).encode("utf-8")
        return RunnerResult(returncode=0, stdout=body, stderr=b"", duration_seconds=0.01)

    return fake_runner


def _fake_snapshot(_: Path) -> dict[str, str]:
    return {"src/microcosm_core/__init__.py": "stable"}


def test_flight_recorder_first_action_proof_round_trip(tmp_path: Path) -> None:
    """The recorder packet carries an evidence-derived first-action proof that
    survives verification, refuses tampering, and preserves honest failures."""
    root = tmp_path / "microcosm-root"
    (root / "src/microcosm_core").mkdir(parents=True)
    (root / "src/microcosm_core/__init__.py").write_text("", encoding="utf-8")
    out_dir = root / ".microcosm/flight"

    packet = build_flight_recorder_packet(
        root=root,
        out_dir=out_dir,
        python_executable="python",
        runner=_flight_recorder_fake_runner(),
        snapshotter=_fake_snapshot,
        generated_at="2026-06-10T00:00:00+00:00",
    )
    proof = packet["first_action_proof"]
    assert proof["status"] == "pass"
    assert proof["failed_checks"] == []
    assert proof["owner"]["organ_id"] == "finance_forecast_evaluation_spine"
    assert proof["hero_goal"] == FIRST_ACTION_HERO_GOAL
    assert proof["clone_entry_goal"] == FIRST_ACTION_CLONE_GOAL
    assert proof["clean_run_command"]
    assert proof["assay"]["scenarios"] == 19
    assert "first_action_proof" not in {
        row["command_id"] for row in packet["evaluator_verdict"]["refused_claims"]
    }
    card_text = (root / packet["human_card_ref"]).read_text(encoding="utf-8")
    assert "## First Action Proof" in card_text
    assert FIRST_ACTION_HERO_GOAL in card_text

    verification = verify_flight_recorder_packet(
        packet_dir=out_dir,
        root=root,
        write_receipt=False,
        verified_at="2026-06-10T00:01:00+00:00",
    )
    assert verification["status"] == "packet_valid"
    rederived = next(
        row
        for row in verification["checks"]
        if row["check_id"] == "first_action_proof_rederived"
    )
    assert rederived["status"] == "pass"

    # Tampering with the proof block — even with a recomputed payload digest —
    # must fail, because the verifier re-derives the block from digest-bound
    # evidence rather than trusting the stored claim.
    packet_path = out_dir / "flight-recorder-packet.json"
    tampered = json.loads(packet_path.read_text(encoding="utf-8"))
    tampered["first_action_proof"]["owner"]["organ_id"] = "some_other_organ"
    tampered["packet_payload_sha256"] = _packet_payload_sha256(tampered)
    packet_path.write_text(json.dumps(tampered, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    refused = verify_flight_recorder_packet(
        packet_dir=out_dir,
        root=root,
        write_receipt=False,
        verified_at="2026-06-10T00:02:00+00:00",
    )
    assert refused["status"] == "digest_mismatch"
    assert any(
        row["check_id"] == "first_action_proof_rederived" and row["status"] == "blocked"
        for row in refused["checks"]
    )


def test_flight_recorder_first_action_proof_preserves_placeholder_failure(
    tmp_path: Path,
) -> None:
    """A placeholder-carrying hero command becomes preserved blocked evidence,
    not a hidden failure — and the honest packet still verifies clean."""
    root = tmp_path / "microcosm-root"
    (root / "src/microcosm_core").mkdir(parents=True)
    (root / "src/microcosm_core/__init__.py").write_text("", encoding="utf-8")
    out_dir = root / ".microcosm/flight"

    broken = json.loads(json.dumps(HERO_CONTRACT_PAYLOAD))
    broken["first_action"]["command"] = (
        'PYTHONPATH=src python3 -m microcosm_core comprehend --first-action "<your goal>"'
    )
    packet = build_flight_recorder_packet(
        root=root,
        out_dir=out_dir,
        python_executable="python",
        runner=_flight_recorder_fake_runner(contract_payload=broken),
        snapshotter=_fake_snapshot,
        generated_at="2026-06-10T00:00:00+00:00",
    )
    proof = packet["first_action_proof"]
    assert proof["status"] == "blocked"
    assert "command_placeholder_free" in proof["failed_checks"]
    assert any(
        row["command_id"] == "first_action_proof"
        for row in packet["evaluator_verdict"]["refused_claims"]
    )
    assert packet["evaluator_verdict"]["status"] == "mixed_claims_preserved"

    verification = verify_flight_recorder_packet(
        packet_dir=out_dir,
        root=root,
        write_receipt=False,
        verified_at="2026-06-10T00:01:00+00:00",
    )
    assert verification["status"] == "packet_valid"


def _plant_committed_demo(
    root: Path,
    *,
    owner_organ_id: str = "finance_forecast_evaluation_spine",
    command: str | None = None,
    validator_command: str | None = None,
) -> None:
    """Write a minimal committed demonstration receipt whose hero row carries
    the expectation the release-candidate proof pins encounters against."""
    demo = {
        "schema_version": "microcosm_first_action_demo_v0",
        "contracts": [
            {
                "goal": FIRST_ACTION_HERO_GOAL,
                "owner": {"organ_id": owner_organ_id},
                "first_action": {
                    "command": command
                    or HERO_CONTRACT_PAYLOAD["first_action"]["command"],
                },
                "proof_path": {
                    "runnable_validator": HERO_CONTRACT_PAYLOAD["proof_path"][
                        "runnable_validator"
                    ],
                    "validator_command": validator_command
                    or HERO_CONTRACT_PAYLOAD["proof_path"]["validator_command"],
                },
            }
        ],
    }
    path = root / COMMITTED_DEMO_RECEIPT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(demo), encoding="utf-8")


def _fake_root(tmp_path: Path, *, plant_demo: bool = True) -> Path:
    root = tmp_path / "microcosm-root"
    (root / "src/microcosm_core").mkdir(parents=True)
    (root / "src/microcosm_core/__init__.py").write_text("", encoding="utf-8")
    if plant_demo:
        _plant_committed_demo(root)
    return root


def _release_candidate_fake_runner(export_owner_organ_id: str | None = None):
    def fake_runner(spec: CommandSpec, cwd: Path, env: dict[str, str]) -> RunnerResult:
        command_id = spec.command_id
        if command_id == "fresh_install.package_smoke":
            work_dir = Path(spec.actual_argv[spec.actual_argv.index("--work-dir") + 1])
            outputs = work_dir / "outputs"
            outputs.mkdir(parents=True, exist_ok=True)
            (outputs / "first-action.json").write_text(
                json.dumps(HERO_CONTRACT_PAYLOAD), encoding="utf-8"
            )
            (outputs / "first-action-assay.txt").write_text(
                json.dumps(ASSAY_PAYLOAD), encoding="utf-8"
            )
            # Real venvs carry absolute-path shebangs; the leak scan must
            # cover the publishable packet surface, never the workspace.
            (work_dir / "venv-shim.txt").write_text(
                "#!/Users/someone/venv/bin/python\n", encoding="utf-8"
            )
            return RunnerResult(0, b"Microcosm package smoke: pass\n", b"", 0.01)
        if command_id == "standalone_export.release_export":
            export_out = Path(spec.actual_argv[spec.actual_argv.index("--out") + 1])
            (export_out / "microcosm-substrate").mkdir(parents=True, exist_ok=True)
            return RunnerResult(0, b'{"status": "pass"}\n', b"", 0.01)
        if command_id.endswith("first_action_hero"):
            payload = json.loads(json.dumps(HERO_CONTRACT_PAYLOAD))
            if export_owner_organ_id and command_id.startswith("standalone_export"):
                payload["owner"]["organ_id"] = export_owner_organ_id
            return RunnerResult(0, json.dumps(payload).encode("utf-8"), b"", 0.01)
        if command_id.endswith("first_action_assay"):
            return RunnerResult(0, json.dumps(ASSAY_PAYLOAD).encode("utf-8"), b"", 0.01)
        if command_id.endswith("demo_check"):
            return RunnerResult(0, b"FIRST_ACTION.md: byte-fresh\n", b"", 0.01)
        raise AssertionError(f"unexpected command: {command_id}")

    return fake_runner


def test_release_candidate_proof_round_trip(tmp_path: Path) -> None:
    """Three passing contexts with identical owner/command matching the
    committed demonstration produce a passing, re-verifiable packet; tampered
    evidence is refused."""
    root = _fake_root(tmp_path)
    out_dir = root / ".microcosm/release-candidate-proof"

    packet = build_release_candidate_proof(
        root=root,
        out_dir=out_dir,
        python_executable="python",
        runner=_release_candidate_fake_runner(),
        generated_at="2026-06-10T00:00:00+00:00",
    )
    assert packet["status"] == "pass"
    assert packet["cross_context_agreement"]["status"] == "pass"
    for context_id in CONTEXT_IDS:
        assert packet["contexts"][context_id]["status"] == "pass", context_id
    assert packet["authority_and_omission_policy"]["release_authorized"] is False
    assert packet["integrity"]["source_mutation_check"]["status"] == "pass"

    # The expectation policy pins the agreed encounter to the committed
    # demonstration, and the demonstration copy itself is digest-bound.
    expectation = packet["expectation_policy"]
    assert expectation["status"] == "pass"
    assert (
        expectation["expected_owner_organ_id"] == "finance_forecast_evaluation_spine"
    )
    assert expectation["expected_validator_command"] == (
        HERO_CONTRACT_PAYLOAD["proof_path"]["validator_command"]
    )
    assert EXPECTATION_EVIDENCE_REF in {
        row["ref"] for row in packet["integrity"]["copied_evidence"]
    }
    assert packet["external_signature_status"] == EXTERNAL_SIGNATURE_STATUS

    card_text = (out_dir / "release-candidate-proof-card.md").read_text(
        encoding="utf-8"
    )
    assert "## Claim under review" in card_text
    assert "finance_forecast_evaluation_spine" in card_text
    assert "External signature status" in card_text
    assert "## Verify this packet" in card_text
    assert "RELEASE_REVIEW.md" in card_text
    assert not (out_dir / "work").exists(), "work trees must be removed after evidence copy"
    packet_text = (out_dir / "release-candidate-proof.json").read_text(encoding="utf-8")
    assert "/Users/" not in packet_text
    assert "src/ai_workflow" not in packet_text

    receipt = verify_release_candidate_proof(
        packet_dir=out_dir,
        root=root,
        write_receipt=True,
        verified_at="2026-06-10T00:01:00+00:00",
    )
    assert receipt["status"] == "packet_valid"
    assert receipt["no_substrate_rerun"] is True

    hero_evidence = out_dir / "export/first-action-hero.json"
    tampered_payload = json.loads(hero_evidence.read_text(encoding="utf-8"))
    tampered_payload["owner"]["organ_id"] = "tampered_organ"
    hero_evidence.write_text(json.dumps(tampered_payload), encoding="utf-8")
    refused = verify_release_candidate_proof(
        packet_dir=out_dir,
        root=root,
        write_receipt=False,
        verified_at="2026-06-10T00:02:00+00:00",
    )
    assert refused["status"] == "digest_mismatch"


def test_release_candidate_proof_blocks_on_cross_context_divergence(
    tmp_path: Path,
) -> None:
    """A contract that resolves to a different owner in the export than in the
    checkout is a different product: the packet must block and name it."""
    root = _fake_root(tmp_path)
    out_dir = root / ".microcosm/release-candidate-proof"

    packet = build_release_candidate_proof(
        root=root,
        out_dir=out_dir,
        python_executable="python",
        runner=_release_candidate_fake_runner(export_owner_organ_id="divergent_organ"),
        generated_at="2026-06-10T00:00:00+00:00",
    )
    assert packet["status"] == "blocked"
    agreement = packet["cross_context_agreement"]
    assert agreement["status"] == "blocked"
    assert agreement["owner_organ_id_identical"] is False
    assert agreement["owner_organ_ids"]["standalone_export"] == "divergent_organ"
    # The honest blocked packet still verifies: verification proves evidence
    # binding, not desirability.
    receipt = verify_release_candidate_proof(
        packet_dir=out_dir,
        root=root,
        write_receipt=False,
        verified_at="2026-06-10T00:01:00+00:00",
    )
    assert receipt["status"] == "packet_valid"
    assert receipt["packet_status"] == "blocked"


def test_release_candidate_proof_blocks_when_agreement_misses_committed_promise(
    tmp_path: Path,
) -> None:
    """Cross-context agreement alone is satisfiable by three contexts agreeing
    on the WRONG product: when every context selects the same owner but that
    owner is not the committed demonstration's owner, the expectation policy —
    not the agreement block — must block the packet and name the mismatch."""
    root = _fake_root(tmp_path, plant_demo=False)
    _plant_committed_demo(root, owner_organ_id="committed_promises_other_organ")
    out_dir = root / ".microcosm/release-candidate-proof"

    packet = build_release_candidate_proof(
        root=root,
        out_dir=out_dir,
        python_executable="python",
        runner=_release_candidate_fake_runner(),
        generated_at="2026-06-10T00:00:00+00:00",
    )
    assert packet["status"] == "blocked"
    assert packet["cross_context_agreement"]["status"] == "pass"
    expectation = packet["expectation_policy"]
    assert expectation["status"] == "blocked"
    assert expectation["failed_checks"] == ["owner_matches_committed_demonstration"]
    # The honest blocked packet still verifies — and the verifier reports the
    # re-derived expectation status, not a paraphrase.
    receipt = verify_release_candidate_proof(
        packet_dir=out_dir,
        root=root,
        write_receipt=False,
        verified_at="2026-06-10T00:01:00+00:00",
    )
    assert receipt["status"] == "packet_valid"
    assert receipt["expectation_policy_status"] == "blocked"


def test_release_candidate_proof_blocks_without_committed_demonstration(
    tmp_path: Path,
) -> None:
    """No committed demonstration means no promise to review against: the
    packet blocks with a named absence instead of passing by vacuity."""
    root = _fake_root(tmp_path, plant_demo=False)
    out_dir = root / ".microcosm/release-candidate-proof"

    packet = build_release_candidate_proof(
        root=root,
        out_dir=out_dir,
        python_executable="python",
        runner=_release_candidate_fake_runner(),
        generated_at="2026-06-10T00:00:00+00:00",
    )
    assert packet["status"] == "blocked"
    expectation = packet["expectation_policy"]
    assert expectation["committed_demonstration_present"] is False
    assert "committed_demonstration_present" in expectation["failed_checks"]
    assert any(
        COMMITTED_DEMO_RECEIPT_REL in note
        for note in packet["integrity"]["work_notes"]
    )
    receipt = verify_release_candidate_proof(
        packet_dir=out_dir, root=root, write_receipt=False
    )
    assert receipt["status"] == "packet_valid"
    assert receipt["packet_status"] == "blocked"


def test_expectation_policy_requires_nonempty_committed_values() -> None:
    """An empty committed expectation can never be satisfied by vacuity."""
    expectation = extract_committed_expectation(
        {"contracts": [{"goal": FIRST_ACTION_HERO_GOAL}]}
    )
    assert expectation["committed_demonstration_present"] is True
    assert expectation["expected_owner_organ_id"] is None
    agreement = derive_cross_context_agreement({})
    policy = derive_expectation_policy(expectation, agreement)
    assert policy["status"] == "blocked"
    assert "owner_matches_committed_demonstration" in policy["failed_checks"]


def test_cross_context_agreement_requires_every_context() -> None:
    """A missing context can never satisfy agreement by vacuity."""
    encounters = {
        "source_checkout": {
            "owner": {"organ_id": "finance_forecast_evaluation_spine"},
            "command": "PYTHONPATH=src python3 -m microcosm_core x run",
        },
        "fresh_install": {
            "owner": {"organ_id": "finance_forecast_evaluation_spine"},
            "command": "PYTHONPATH=src python3 -m microcosm_core x run",
        },
    }
    agreement = derive_cross_context_agreement(encounters)
    assert agreement["status"] == "blocked"
    assert agreement["owner_organ_ids"]["standalone_export"] is None


def test_flight_recorder_refuses_missing_or_inconsistent_proof_block(
    tmp_path: Path,
) -> None:
    """A packet without the proof block — or with a forged 'pass' over failed
    checks — is refused even when its self-digest has been recomputed."""
    root = tmp_path / "microcosm-root"
    (root / "src/microcosm_core").mkdir(parents=True)
    (root / "src/microcosm_core/__init__.py").write_text("", encoding="utf-8")
    out_dir = root / ".microcosm/flight"
    build_flight_recorder_packet(
        root=root,
        out_dir=out_dir,
        python_executable="python",
        runner=_flight_recorder_fake_runner(),
        snapshotter=_fake_snapshot,
        generated_at="2026-06-10T00:00:00+00:00",
    )
    packet_path = out_dir / "flight-recorder-packet.json"
    pristine = packet_path.read_text(encoding="utf-8")

    # Arm 1: block deleted entirely.
    stripped = json.loads(pristine)
    del stripped["first_action_proof"]
    stripped["packet_payload_sha256"] = _packet_payload_sha256(stripped)
    packet_path.write_text(json.dumps(stripped, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    missing = verify_flight_recorder_packet(
        packet_dir=out_dir, root=root, write_receipt=False
    )
    assert missing["status"] == "packet_stale"
    assert any(
        row["check_id"] == "first_action_proof_present" and row["status"] == "blocked"
        for row in missing["checks"]
    )

    # Arm 2: status forged to "pass" while failed checks remain listed.
    forged = json.loads(pristine)
    forged["first_action_proof"]["status"] = "pass"
    forged["first_action_proof"]["failed_checks"] = ["claim_ceiling_present"]
    forged["packet_payload_sha256"] = _packet_payload_sha256(forged)
    packet_path.write_text(json.dumps(forged, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    inconsistent = verify_flight_recorder_packet(
        packet_dir=out_dir, root=root, write_receipt=False
    )
    assert inconsistent["status"] == "packet_stale"
    assert any(
        row["check_id"] == "first_action_proof_consistent" and row["status"] == "blocked"
        for row in inconsistent["checks"]
    )


def test_release_candidate_verifier_isolating_tamper_arms(tmp_path: Path) -> None:
    """Each re-derivation check carries its own weight: forging the stored
    encounters, the agreement block, or the top-level status — with the
    self-digest recomputed every time — is refused by the NAMED check."""
    root = _fake_root(tmp_path)
    out_dir = root / ".microcosm/release-candidate-proof"
    build_release_candidate_proof(
        root=root,
        out_dir=out_dir,
        python_executable="python",
        runner=_release_candidate_fake_runner(),
        generated_at="2026-06-10T00:00:00+00:00",
    )
    packet_path = out_dir / "release-candidate-proof.json"
    pristine = packet_path.read_text(encoding="utf-8")

    def rewrite(mutate) -> dict:
        packet = json.loads(pristine)
        mutate(packet)
        packet["packet_payload_sha256"] = _packet_payload_sha256(packet)
        packet_path.write_text(
            json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return verify_release_candidate_proof(
            packet_dir=out_dir, root=root, write_receipt=False
        )

    def check_status(receipt: dict, check_id: str) -> str:
        return next(row for row in receipt["checks"] if row["check_id"] == check_id)[
            "status"
        ]

    forged_encounter = rewrite(
        lambda p: p["contexts"]["source_checkout"]["encounter"]["owner"].update(
            organ_id="forged_organ"
        )
    )
    assert forged_encounter["status"] == "digest_mismatch"
    assert check_status(forged_encounter, "context_encounters_rederived") == "blocked"
    assert check_status(forged_encounter, "cross_context_agreement_rederived") == "pass"

    forged_agreement = rewrite(
        lambda p: p["cross_context_agreement"].update(owner_organ_id_identical=False)
    )
    assert forged_agreement["status"] == "digest_mismatch"
    assert check_status(forged_agreement, "cross_context_agreement_rederived") == "blocked"
    assert check_status(forged_agreement, "context_encounters_rederived") == "pass"

    forged_status = rewrite(lambda p: p.update(status="blocked"))
    assert forged_status["status"] == "digest_mismatch"
    assert check_status(forged_status, "packet_status_rederived") == "blocked"

    forged_policy = rewrite(
        lambda p: p["authority_and_omission_policy"].update(release_authorized=True)
    )
    assert forged_policy["status"] != "packet_valid"
    assert check_status(forged_policy, "authority_policy_preserved") == "blocked"

    # Forging the expectation block — claiming a different committed promise
    # than the digest-bound demonstration copy carries — is refused by name.
    forged_expectation = rewrite(
        lambda p: p["expectation_policy"].update(
            expected_owner_organ_id="forged_promise_organ"
        )
    )
    assert forged_expectation["status"] == "digest_mismatch"
    assert check_status(forged_expectation, "expectation_policy_rederived") == "blocked"
    assert check_status(forged_expectation, "cross_context_agreement_rederived") == "pass"

    # A packet claiming any external signature posture this lane does not have
    # is claiming provenance it cannot back.
    forged_signature = rewrite(
        lambda p: p.update(external_signature_status="signed_by_github_attestation")
    )
    assert forged_signature["status"] != "packet_valid"
    assert check_status(forged_signature, "authority_policy_preserved") == "blocked"

    # Copied install evidence is digest-bound too: deleting it is refused.
    packet_path.write_text(pristine, encoding="utf-8")
    (out_dir / "install/first-action-hero.json").unlink()
    missing_copy = verify_release_candidate_proof(
        packet_dir=out_dir, root=root, write_receipt=False
    )
    assert missing_copy["status"] != "packet_valid"
    assert check_status(missing_copy, "copied_evidence_sha256") == "blocked"


def test_release_candidate_proof_blocks_on_source_mutation(tmp_path: Path) -> None:
    """A run that mutates tracked source — even via a concurrent writer — must
    block the packet, and the verifier must not bless the mutated receipt."""
    root = _fake_root(tmp_path)
    tracked = root / "src/microcosm_core/__init__.py"
    out_dir = root / ".microcosm/release-candidate-proof"

    inner = _release_candidate_fake_runner()

    def mutating_runner(spec: CommandSpec, cwd: Path, env: dict[str, str]) -> RunnerResult:
        if spec.command_id == "source_checkout.first_action_hero":
            tracked.write_text("MUTATED = 1\n", encoding="utf-8")
        return inner(spec, cwd, env)

    packet = build_release_candidate_proof(
        root=root,
        out_dir=out_dir,
        python_executable="python",
        runner=mutating_runner,
        generated_at="2026-06-10T00:00:00+00:00",
    )
    assert packet["status"] == "blocked"
    assert packet["integrity"]["source_mutation_check"]["status"] == "blocked"
    receipt = verify_release_candidate_proof(
        packet_dir=out_dir, root=root, write_receipt=False
    )
    assert receipt["status"] == "source_mutation_seen"


def test_release_candidate_proof_keep_work_still_passes(tmp_path: Path) -> None:
    """--keep-work keeps the transient work trees without flipping the verdict:
    the leak scan covers the publishable packet surface, not the workspace."""
    root = _fake_root(tmp_path)
    out_dir = root / ".microcosm/release-candidate-proof"
    packet = build_release_candidate_proof(
        root=root,
        out_dir=out_dir,
        python_executable="python",
        runner=_release_candidate_fake_runner(),
        keep_work=True,
        generated_at="2026-06-10T00:00:00+00:00",
    )
    assert packet["status"] == "pass"
    assert (out_dir / "work").is_dir()
    assert packet["authority_and_omission_policy"][
        "work_trees_removed_after_evidence_copy"
    ] is False


def test_release_candidate_proof_is_publicly_discoverable() -> None:
    makefile = (MICROCOSM_ROOT / "Makefile").read_text(encoding="utf-8")
    readme = (MICROCOSM_ROOT / "README.md").read_text(encoding="utf-8")

    assert "RELEASE_CANDIDATE_PROOF_OUT ?= .microcosm/release-candidate-proof" in makefile
    assert (
        "PYTHONPATH=src $(PYTHON) scripts/release_candidate_proof.py --root . "
        "--out $(RELEASE_CANDIDATE_PROOF_OUT) --python $(PYTHON)"
    ) in makefile
    assert (
        "PYTHONPATH=src $(PYTHON) scripts/release_candidate_proof.py verify "
        "$(RELEASE_CANDIDATE_PROOF_VERIFY_DIR) --root ."
    ) in makefile

    assert "make release-candidate-proof" in readme
    assert "make release-candidate-proof-verify" in readme
    assert "distribution-true" in readme
    assert "does not authorize release" in readme
