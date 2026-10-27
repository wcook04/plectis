from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

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


def test_missing_source_authority_drifts_even_when_check_passes(tmp_path: Path) -> None:
    # A source-faithfulness claim whose declared source is absent must not
    # report clean just because the check command exits 0.
    _write(tmp_path / "expected/report.md", "present\n")
    _write(tmp_path / "generated/report.md", "present\n")
    receipt = check_projection_drift(tmp_path, [_owner(command=("builtin:pass",))])
    assert receipt["status"] == "drift"
    assert "source_authority_missing" in receipt["owners"][0]["status_reasons"]


def test_glob_pattern_selection_agrees_with_fingerprint_matcher() -> None:
    # Path.glob fingerprints `state/x.json` under `state/**/*.json` (`**`
    # matches zero directories); changed-path selection must not disagree.
    assert projection_pattern_matches_path("state/**/*.json", "state/x.json") is True
    # A changed directory prefix selects glob-pattern owners the same way it
    # already selects non-glob dir patterns.
    assert projection_pattern_matches_path("docs/generated/*.md", "docs") is True
    assert projection_pattern_matches_path("docs/generated/*.md", "unrelated") is False


@pytest.mark.parametrize("pattern", [
    "**/*.md", "**/report.md", "*.md", "docs/**/*.md",
    "docs/gen*/*.md", "docs/gen?/*.md", "docs/gen[ab]/*.md",
])
@pytest.mark.parametrize("field", ["artifacts", "source_authorities"])
def test_every_fingerprinted_glob_member_selects_its_owner(
    tmp_path: Path, pattern: str, field: str,
) -> None:
    for path in ["report.md", "docs/report.md", "docs/gena/report.md", "docs/gena/deep/report.md"]:
        _write(tmp_path / path, "report\n")
    owner = ProjectionOwner(
        owner_id="glob_projection", description="Glob membership regression.",
        artifacts=(pattern,) if field == "artifacts" else (),
        source_authorities=(pattern,) if field == "source_authorities" else (),
        check_command=("builtin:pass",),
    )
    unscoped = check_projection_drift(tmp_path, [owner])
    fingerprint = unscoped["owners"][0]["source_hash_receipt"]
    members = fingerprint["artifact_files" if field == "artifacts" else "source_files"]
    assert members, "The test must exercise actual Path.glob membership."
    for member in members:
        scoped = check_projection_drift(tmp_path, [owner], changed_paths=[member["path"]])
        assert scoped["selection"]["selected_owner_ids"] == [owner.owner_id], member["path"]
        # Deleted files must still route to their owner without consulting the filesystem.
        (tmp_path / member["path"]).unlink()
        assert projection_pattern_matches_path(pattern, member["path"])


def test_root_recursive_glob_drift_is_not_skipped_by_changed_path(tmp_path: Path) -> None:
    _write(tmp_path / "source/expected.txt", "expected\n")
    _write(tmp_path / "generated.md", "changed\n")
    owner = ProjectionOwner(
        owner_id="recursive_report", description="A root report covered by a recursive glob.",
        artifacts=("**/*.md",), source_authorities=("source/expected.txt",),
        check_command=("builtin:assert-file-equals", "source/expected.txt", "generated.md"),
    )
    for paths in [None, ["generated.md"]]:
        receipt = check_projection_drift(tmp_path, [owner], changed_paths=paths)
        assert receipt["status"] == "drift"
        assert receipt["owner_count"] == receipt["drift_owner_count"] == 1
        assert receipt["owners"][0]["status_reasons"] == ["check_command_failed"]


def test_glob_fallback_uses_complete_fixed_directories() -> None:
    assert projection_pattern_matches_path("docs/gen*/*.md", "docs")
    assert projection_pattern_matches_path("docs/gen*/*.md", "docs/gena")
    assert not projection_pattern_matches_path("docs/gen*/*.md", "unrelated/report.md")
    # Conservative fallback may select an extra path within a fixed directory.
    assert projection_pattern_matches_path("docs/**/*.md", "docs/other.txt")


def test_saved_runtime_result_preserves_which_owner_failed(tmp_path: Path) -> None:
    from microcosm_core.organs.generated_projection_drift_runtime import RESULT_NAME, run

    outcomes = []
    for failing in ["left", "right"]:
        case = {
            "case_id": "swapped_owner", "case_type": "negative",
            "expected_status": "drift", "expected_owner_count": 2,
            "files": [{"path": f"{name}.txt", "text": "report body"} for name in ["left", "right"]],
            "owners": [{
                "owner_id": name, "artifacts": [f"{name}.txt"],
                "check_command": ["builtin:fail" if name == failing else "builtin:pass"],
            } for name in ["left", "right"]],
        }
        inputs = tmp_path / failing / "inputs"
        _write(inputs / "case.json", json.dumps(case))
        out = tmp_path / failing / "out"
        run(inputs, out)
        saved = json.loads((out / RESULT_NAME).read_text())["cases"][0]
        assert {row["owner_id"] for row in saved["owners"] if row["status"] == "drift"} == {failing}
        for row in saved["owners"]:
            assert set(row) == {"owner_id", "status", "status_reasons", "check_mode", "check_returncode"}
            assert row["check_returncode"] == (7 if row["owner_id"] == failing else 0)
        outcomes.append(saved)
    assert {k: v for k, v in outcomes[0].items() if k != "owners"} == {
        k: v for k, v in outcomes[1].items() if k != "owners"
    }


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
