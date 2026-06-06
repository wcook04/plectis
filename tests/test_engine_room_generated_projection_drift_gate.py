from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from microcosm_core.engine_room.generated_projection_drift_gate import (
    ANTI_CLAIMS,
    CLAIM_CEILING,
    ProjectionOwner,
    check_projection_drift,
    evaluate_fixture_dir,
    projection_pattern_matches_path,
)


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "fixtures/first_wave/engine_room_generated_projection_drift_gate/input"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _owner(command: tuple[str, ...] = ("builtin:assert-file-equals", "expected/report.md", "generated/report.md")) -> ProjectionOwner:
    return ProjectionOwner(
        owner_id="demo_projection",
        description="Fixture owner for one generated report.",
        artifacts=("generated/report.md",),
        source_authorities=("source/spec.json", "expected/report.md"),
        check_command=command,
        repair_command=("builtin:repair-demo",),
        manual_edit_boundary="Do not hand-edit generated/report.md.",
        deterministic_regeneration_expectation="generated/report.md must match expected/report.md.",
        stale_drift_handling="Run the no-write check before landing generated/report.md.",
        require_fact_authority_lineage=True,
        fact_authority_lineage={
            "authority_ref": "source/spec.json",
            "appearance_refs": ["generated/report.md"],
            "derivation_path": "builtin:assert-file-equals expected/report.md generated/report.md",
            "guard_ref": "tests/test_engine_room_generated_projection_drift_gate.py",
            "treatment": "guarded_public_projection",
            "residual_route": "repair_command:builtin:repair-demo",
        },
    )


def test_clean_owner_runs_no_write_check(tmp_path: Path) -> None:
    _write(tmp_path / "source/spec.json", '{"title":"clean"}\n')
    _write(tmp_path / "expected/report.md", "clean\n")
    _write(tmp_path / "generated/report.md", "clean\n")
    receipt = check_projection_drift(tmp_path, [_owner()])
    assert receipt["status"] == "clean"
    assert receipt["drift_owner_count"] == 0
    assert receipt["fact_authority_lineage"]["status"] == "pass"
    assert receipt["owners"][0]["check_mode"] == "command"
    assert receipt["owners"][0]["fact_authority_lineage"]["status"] == "pass"
    assert receipt["owners"][0]["check_result"]["returncode"] == 0


def test_planted_byte_is_owner_drift(tmp_path: Path) -> None:
    _write(tmp_path / "source/spec.json", '{"title":"expected"}\n')
    _write(tmp_path / "expected/report.md", "expected\n")
    _write(tmp_path / "generated/report.md", "expected plus planted byte\n")
    receipt = check_projection_drift(tmp_path, [_owner()])
    assert receipt["status"] == "drift"
    assert receipt["owners"][0]["status_reasons"] == ["check_command_failed"]


def test_missing_artifact_drifts_even_when_check_passes(tmp_path: Path) -> None:
    _write(tmp_path / "source/spec.json", '{"title":"missing"}\n')
    receipt = check_projection_drift(tmp_path, [_owner(command=("builtin:pass",))])
    assert receipt["status"] == "drift"
    assert "artifact_missing" in receipt["owners"][0]["status_reasons"]


def test_required_fact_authority_lineage_drifts_when_incomplete(tmp_path: Path) -> None:
    _write(tmp_path / "source/spec.json", '{"title":"lineage"}\n')
    _write(tmp_path / "expected/report.md", "lineage\n")
    _write(tmp_path / "generated/report.md", "lineage\n")
    owner = ProjectionOwner(
        owner_id="demo_projection",
        description="Fixture owner with incomplete authority lineage.",
        artifacts=("generated/report.md",),
        source_authorities=("source/spec.json", "expected/report.md"),
        check_command=("builtin:pass",),
        require_fact_authority_lineage=True,
        fact_authority_lineage={
            "authority_ref": "source/spec.json",
            "appearance_refs": ["generated/report.md"],
            "treatment": "guarded_public_projection",
        },
    )
    receipt = check_projection_drift(tmp_path, [owner])
    assert receipt["status"] == "drift"
    assert receipt["fact_authority_lineage"]["status"] == "blocked"
    assert "fact_authority_lineage_invalid" in receipt["owners"][0]["status_reasons"]
    assert receipt["owners"][0]["fact_authority_lineage"]["missing_fields"] == [
        "derivation_path",
        "guard_ref",
        "residual_route",
    ]


def test_changed_path_scopes_to_matching_owner(tmp_path: Path) -> None:
    _write(tmp_path / "source/spec.json", '{"title":"a"}\n')
    _write(tmp_path / "expected/report.md", "a\n")
    _write(tmp_path / "generated/report.md", "a\n")
    _write(tmp_path / "other/source.txt", "other\n")
    _write(tmp_path / "other/out.txt", "other\n")
    other = ProjectionOwner(
        owner_id="other_projection",
        description="Other projection.",
        artifacts=("other/out.txt",),
        source_authorities=("other/source.txt",),
        check_command=("builtin:pass",),
    )
    receipt = check_projection_drift(
        tmp_path,
        [_owner(), other],
        changed_paths=["generated/report.md"],
    )
    assert receipt["selection"]["mode"] == "scoped_paths"
    assert receipt["selection"]["selected_owner_ids"] == ["demo_projection"]
    assert receipt["owner_count"] == 1


def test_source_hash_cache_hit_skips_command(tmp_path: Path) -> None:
    _write(tmp_path / "source/spec.json", '{"title":"cached"}\n')
    _write(tmp_path / "expected/report.md", "cached\n")
    _write(tmp_path / "generated/report.md", "cached\n")
    clean = check_projection_drift(tmp_path, [_owner(command=("builtin:pass",))])
    fingerprint = clean["owners"][0]["source_hash_receipt"]
    cache = {
        "schema_version": "generated_projection_source_hash_receipts_v1",
        "owners": {
            "demo_projection": {
                "owner_id": "demo_projection",
                "status": "clean",
                "check_command": ["builtin:pass"],
                "source_hash": fingerprint["source_hash"],
                "artifact_hash": fingerprint["artifact_hash"],
                "artifact_missing_count": 0,
            }
        },
    }
    cached = check_projection_drift(
        tmp_path,
        [_owner(command=("builtin:pass",))],
        source_hash_cache=cache,
    )
    assert cached["status"] == "clean"
    assert cached["source_hash_cache"]["hit_count"] == 1
    assert cached["owners"][0]["check_mode"] == "source_hash_cache_hit"


def test_path_pattern_matching_matches_registry_shape() -> None:
    assert projection_pattern_matches_path("state/public_views/*.json", "state/public_views/ready.json")
    assert projection_pattern_matches_path("AGENTS.md", "./AGENTS.md")
    assert projection_pattern_matches_path("docs/generated", "docs/generated/report.md")


def test_fixture_matrix_matches_drift_gate_expectations() -> None:
    receipt = evaluate_fixture_dir(INPUT_DIR)
    assert receipt["status"] == "pass"
    assert receipt["case_count"] == 5
    assert receipt["passed_case_count"] == 5
    assert "not_semantic_drift_proof" in ANTI_CLAIMS
    assert "does not prove" in CLAIM_CEILING


def test_module_cli_emits_json_receipt() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "microcosm_core.engine_room.generated_projection_drift_gate",
            "evaluate-fixtures",
            "--input",
            str(INPUT_DIR),
            "--json",
        ],
        cwd=ROOT,
        env={"PYTHONPATH": "src"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["organ_id"] == "engine_room_generated_projection_drift_gate"
    assert payload["status"] == "pass"
