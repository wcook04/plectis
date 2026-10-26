from __future__ import annotations

import json
from pathlib import Path

from system.lib.continuation_packet import build_continuation_packet, write_continuation_packet
from system.lib.resume_contract_payload import build_resume_contract_transport_payload


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _seed_family(tmp_path: Path) -> tuple[str, str]:
    family_rel = "obsidian/workstream/09 - Live Family"
    phase_rel = f"{family_rel}/09.4 - Phase 09.4 - Active Runtime"
    family_dir = tmp_path / family_rel
    family_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        family_dir / "phase_family.json",
        {
            "kind": "phase_family",
            "family_id": "09",
            "family_number": "09",
            "family_title": "Live Family",
            "family_dir": family_rel,
            "family_charter_path": f"{family_rel}/family_charter.json",
            "raw_seed_path": f"{family_rel}/raw_seed.md",
            "raw_seed_principles_path": f"{family_rel}/raw_seed/raw_seed_principles.json",
            "meta_ledger_path": f"{family_rel}/meta_ledger.json",
            "phase_memory_path": f"{family_rel}/phase_memory.json",
            "reference_ledger_path": f"{family_rel}/reference_ledger.json",
            "autonomous_seed_path": f"{family_rel}/autonomous_seed.json",
            "autonomous_seed_markdown_path": f"{family_rel}/autonomous_seed.md",
            "active_phase_id": "09_4",
            "active_phase_number": "09.4",
            "active_phase_title": "Phase 09.4 - Active Runtime",
            "active_phase_dir": phase_rel,
        },
    )
    _write_json(family_dir / "family_charter.json", {"kind": "family_charter"})
    (family_dir / "raw_seed.md").write_text("# raw seed\n", encoding="utf-8")
    _write_json(family_dir / "raw_seed" / "raw_seed_principles.json", {"kind": "raw_seed_principles", "principles": []})
    _write_json(family_dir / "meta_ledger.json", {"kind": "meta_ledger", "entries": []})
    _write_json(family_dir / "phase_memory.json", {"kind": "phase_memory", "entries": []})
    _write_json(family_dir / "reference_ledger.json", {"kind": "phase_reference_ledger"})
    _write_json(
        tmp_path / phase_rel / "synth_seed.json",
        {
            "phase_id": "09_4",
            "phase_number": "09.4",
            "phase_title": "Phase 09.4 - Active Runtime",
            "current_wave": {
                "wave_id": "09_4_wave_001",
                "objective": "Canonicalize the continuation packet.",
                "mode": "hybrid",
                "bounded_question": "How should state-backed wakes share one packet shape?",
                "status": "active",
            },
        },
    )
    return family_rel, phase_rel


def test_build_continuation_packet_for_pipeline_signal_includes_family_continuity(tmp_path: Path) -> None:
    family_rel, phase_rel = _seed_family(tmp_path)
    packet = build_continuation_packet(
        tmp_path,
        wait_kind="pipeline_signal",
        artifact_dir=phase_rel,
        source_context={
            "pipeline_id": "PIPE_demo",
            "state_path": f"{phase_rel}/pipeline_state.json",
            "phase_dir": phase_rel,
            "family_dir": family_rel,
            "stage": "results_processed",
            "cycle": 2,
            "next_action": {
                "key": "attention_gate",
                "summary": "Review the current results.",
                "command": "python3 pipeline_advance.py --attention-gate",
            },
            "codex_attention": {
                "needs_attention": True,
                "continue_command": "python3 pipeline_advance.py --force --advance",
            },
            "recommended_commands": {
                "status": "python3 pipeline_advance.py",
                "attention_gate": "python3 pipeline_advance.py --attention-gate",
                "write_resume": "python3 pipeline_advance.py --write-resume",
            },
            "authority_surfaces": {
                "raw_seed": {"path": f"{family_rel}/raw_seed.md"},
                "synth_seed": {"path": f"{phase_rel}/synth_seed.json"},
            },
            "artifacts": {
                "resume_json_path": f"{phase_rel}/pipeline_resume.json",
                "attention_json_path": f"{phase_rel}/pipeline_attention.json",
            },
        },
    )

    assert packet["wait_kind"] == "pipeline_signal"
    assert packet["continuation_packet_path"] == f"{phase_rel}/continuation_packet.json"
    assert packet["family_continuity"]["family_dir"] == family_rel
    assert packet["family_continuity"]["active_phase"]["phase_number"] == "09.4"
    assert packet["family_continuity"]["autonomous_seed_path"] == f"{family_rel}/autonomous_seed.json"
    assert "continuation_packet.json" in packet["codex_wake_prompt"]
    assert packet["continuation_packet_fingerprint"]


def test_continuation_packet_preserves_compaction_resume_prohibitions(tmp_path: Path) -> None:
    family_rel, phase_rel = _seed_family(tmp_path)
    packet = build_continuation_packet(
        tmp_path,
        wait_kind="pipeline_signal",
        artifact_dir=phase_rel,
        source_context={
            "pipeline_id": "PIPE_loop",
            "state_path": f"{phase_rel}/pipeline_state.json",
            "phase_dir": phase_rel,
            "family_dir": family_rel,
            "latest_user_message": (
                "Can you spot improvements given attached agent troubles: "
                "can you refine or grow our pattern ledger"
            ),
            "appended_rows": ["pat_350"],
            "successful_append": True,
            "blockers_seen": ["git_metadata_unwritable"],
            "next_action": {
                "key": "review",
                "summary": "Review the loop evidence.",
                "command": "python3 pipeline_advance.py --attention-gate",
            },
            "recommended_commands": {
                "status": "python3 pipeline_advance.py",
                "attention_gate": "python3 pipeline_advance.py --attention-gate",
                "write_resume": "python3 pipeline_advance.py --write-resume",
            },
        },
    )

    capsule = packet["compaction_resume_capsule"]
    assert capsule["latest_user_intent"] == "diagnose_system_from_transcript"
    assert "append_more_rows_without_new_authorization" in capsule["prohibited_next_actions"]
    assert "rerun_same_seed" in capsule["prohibited_next_actions"]
    assert "Compaction resume capsule:" in packet["codex_resume_prompt"]
    assert "Prohibited next actions" in packet["codex_wake_prompt"]


def test_build_continuation_packet_for_resume_contract_uses_contract_context(tmp_path: Path) -> None:
    family_rel, phase_rel = _seed_family(tmp_path)
    contract_dir = tmp_path / "tools" / "meta" / "apply" / "observe_dumps" / "demo"
    contract_dir.mkdir(parents=True, exist_ok=True)
    packet = build_continuation_packet(
        tmp_path,
        wait_kind="resume_contract",
        artifact_dir="tools/meta/apply/observe_dumps/demo",
        source_context={
            "resume_contract_path": "tools/meta/apply/observe_dumps/demo/resume_contract.json",
            "plan_path": f"{phase_rel}/observe_plan.json",
            "context_bundle": {
                "original_intent": "Unify Codex wake context.",
                "key_files": ["pipeline_codex_handoff.py", "pipeline_signal_watcher.py"],
                "artifact_paths": [f"{phase_rel}/synth_seed.json"],
            },
            "on_success": {
                "read_first": [f"{phase_rel}/synth_seed.json"],
                "artifact_paths": [f"{phase_rel}/pipeline_resume.json"],
                "next_action": "Assimilate the bridge outputs and continue.",
            },
            "on_failure": {
                "read_first": [],
                "artifact_paths": [],
            },
            "resume_artifact_paths": [
                "tools/meta/apply/observe_dumps/demo/resume_contract.json",
                f"{phase_rel}/synth_seed.json",
            ],
            "next_action": {
                "key": "resume_contract_branch_resolution",
                "summary": "Assimilate the bridge outputs and continue.",
                "command": "",
            },
        },
    )

    assert packet["wait_kind"] == "resume_contract"
    assert packet["family_continuity"]["family_dir"] == family_rel
    assert packet["continuation_packet_path"] == "tools/meta/apply/observe_dumps/demo/continuation_packet.json"
    assert "resume_contract seam" in packet["codex_resume_prompt"]
    assert "Unify Codex wake context." in packet["codex_resume_prompt"]


def test_write_continuation_packet_persists_packet(tmp_path: Path) -> None:
    packet = build_continuation_packet(
        tmp_path,
        wait_kind="mission_controller",
        artifact_dir="tools/meta/apply/observe_dumps/demo",
        source_context={
            "state_path": "tools/meta/apply/observe_dumps/demo/_mission_controller_state.json",
            "stage": "results_processed",
            "cycle": 1,
            "next_action": {
                "key": "attention_gate",
                "summary": "Review the mission controller state.",
                "command": "python3 pipeline_advance.py --attention-gate",
            },
            "codex_attention": {"needs_attention": False},
            "recommended_commands": {
                "status": "python3 pipeline_advance.py",
                "attention_gate": "python3 pipeline_advance.py --attention-gate",
                "write_resume": "python3 pipeline_advance.py --write-resume",
            },
            "artifacts": {
                "resume_json_path": "tools/meta/apply/observe_dumps/demo/pipeline_resume.json",
                "attention_json_path": "tools/meta/apply/observe_dumps/demo/pipeline_attention.json",
            },
        },
    )

    path, on_disk = write_continuation_packet(
        tmp_path,
        artifact_dir="tools/meta/apply/observe_dumps/demo",
        packet=packet,
    )

    assert path == "tools/meta/apply/observe_dumps/demo/continuation_packet.json"
    assert json.loads((tmp_path / path).read_text(encoding="utf-8")) == on_disk


def test_build_resume_contract_transport_payload_filters_missing_artifacts(tmp_path: Path) -> None:
    family_rel, phase_rel = _seed_family(tmp_path)
    contract_rel = f"{phase_rel}/resume_contract.json"
    contract_path = tmp_path / contract_rel
    plan_rel = f"{phase_rel}/observe_plan.json"
    existing_rel = f"{phase_rel}/cycle_0/phase_step_result.md"
    missing_rel = f"{phase_rel}/cycle_0/group_responses/01_probe.md"
    _write_json(tmp_path / plan_rel, {"kind": "observe_plan"})
    (tmp_path / existing_rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / existing_rel).write_text("# done\n", encoding="utf-8")
    _write_json(
        contract_path,
        {
            "plan_path": plan_rel,
            "context_bundle": {"artifact_paths": [existing_rel]},
            "on_success": {
                "read_first": [existing_rel],
                "artifact_paths": [missing_rel],
                "next_action": "Assimilate the results.",
            },
            "on_failure": {"read_first": [], "artifact_paths": []},
        },
    )

    payload = build_resume_contract_transport_payload(
        tmp_path,
        resume_contract_path=contract_path,
        artifact_dir=f"{phase_rel}/cycle_0",
    )

    assert f"{phase_rel}/cycle_0/continuation_packet.json" in payload["resume_artifact_paths"]
    assert contract_rel in payload["resume_artifact_paths"]
    assert plan_rel in payload["resume_artifact_paths"]
    assert existing_rel in payload["resume_artifact_paths"]
    assert missing_rel not in payload["resume_artifact_paths"]
    assert payload["extras"]["missing_resume_artifact_candidates"] == [missing_rel]
    assert payload["extras"]["resume_contract_path"] == contract_rel
