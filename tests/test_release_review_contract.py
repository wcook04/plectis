"""Tests for the committed release reviewer contract (RELEASE_REVIEW.md).

Proves the committed contract matches what the builder would regenerate from
the live sources (the drift gate — including the artifact-subject digests, so
a changed FIRST_ACTION.md without a regen goes red with the drifted files
named), answers every reviewer question from the artifact alone, binds its
subjects by recomputable digest, ships in every distribution lane, carries no
leaks, and refuses tampered or input-starved roots.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import tomllib
from pathlib import Path

import pytest

from microcosm_core import release_export
from microcosm_core.release_candidate_proof import (
    EXTERNAL_SIGNATURE_STATUS,
    FAILURE_INTERPRETATIONS,
    SCHEMA_VERSION as PACKET_SCHEMA_VERSION,
    extract_committed_expectation,
)
from microcosm_core.skeptic_flight_recorder import FIRST_ACTION_HERO_GOAL

_SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "build_release_review.py"
)
_spec = importlib.util.spec_from_file_location("build_release_review", _SCRIPT)
assert _spec and _spec.loader
review_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(review_mod)

_ROOT = Path(__file__).resolve().parents[1]


def _write_min_root(tmp_path: Path) -> Path:
    """A minimal root carrying the builder's two inputs: the committed
    demonstration receipt (with a complete hero row) and FIRST_ACTION.md."""
    demo = {
        "schema_version": "microcosm_first_action_demo_v0",
        "contracts": [
            {
                "goal": FIRST_ACTION_HERO_GOAL,
                "owner": {"organ_id": "alpha_owner_organ"},
                "first_action": {
                    "command": "PYTHONPATH=src python3 -m microcosm_core alpha run --input fixtures/x",
                },
                "proof_path": {
                    "runnable_validator": "PYTHONPATH=src python3 -m microcosm_core.organs.alpha run --input fixtures/x",
                    "validator_command": "python -m microcosm_core.organs.alpha run --input fixtures/x",
                },
            }
        ],
    }
    receipt_path = tmp_path / review_mod.COMMITTED_DEMO_RECEIPT_REL
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(demo), encoding="utf-8")
    (tmp_path / "FIRST_ACTION.md").write_text(
        "# First Correct Action\n\nfixture demonstration body\n", encoding="utf-8"
    )
    return tmp_path


def test_review_contract_check_is_green_on_committed_tree() -> None:
    """The committed contract must match a live regeneration byte-for-byte —
    including the artifact-subject digests, so a drifted demonstration is
    refused here with the stale files named."""
    assert review_mod.main(["--check"]) == 0


def test_review_contract_answers_the_reviewer_questions() -> None:
    """A skeptical reviewer must find claim, subjects, expectations, commands,
    failure reading, and the verifier boundary in the committed doc itself."""
    text = (_ROOT / review_mod.DOC_REL).read_text(encoding="utf-8")
    assert review_mod.GENERATED_MARKER in text
    for heading in (
        "## The claim under review",
        "## The artifact under review",
        "## Expectation policy",
        "## Run the review",
        "## Reading a failure",
        "## What verification proves — and what it cannot",
    ):
        assert heading in text, heading
    assert FIRST_ACTION_HERO_GOAL in text
    assert "finance_forecast_evaluation_spine" in text
    for command in (
        "make release-candidate-proof",
        "make release-candidate-proof-verify",
        "make release-review",
    ):
        assert command in text, command
    # The nonclaims and the no-rerun boundary are load-bearing: the contract
    # must say what it cannot prove, in the artifact, not in chat.
    assert "not release authorization or publication approval" in text
    assert "not externally signed or attested provenance" in text
    assert EXTERNAL_SIGNATURE_STATUS in text
    assert "does not prove the run happened as recorded" in text
    # One obvious cold-review command with hermetic-regeneration semantics,
    # while the no-rerun verify boundary stays separately named.
    assert "one cold-review command" in text
    assert "regenerates the proof packet fresh" in text
    assert "without rerunning anything" in text
    # The work-root and normalization obligations are part of the contract:
    # transient work never sits in-tree and reaches evidence only as tokens.
    assert "outside the source root" in text
    assert "<work-dir>" in text
    assert "<export-out>" in text
    # Every named failure code is interpreted; a red result always classifies.
    for row in FAILURE_INTERPRETATIONS:
        assert f"`{row['code']}`" in text, row["code"]


def test_review_receipt_binds_live_subjects_and_expectation() -> None:
    """The machine receipt's digests must recompute against the live tree and
    its expectation must equal the committed demonstration's hero row."""
    receipt = json.loads((_ROOT / review_mod.RECEIPT_REL).read_text(encoding="utf-8"))
    assert receipt["schema_version"] == review_mod.CONTRACT_SCHEMA
    assert receipt["packet_schema_version"] == PACKET_SCHEMA_VERSION
    assert receipt["hero_goal"] == FIRST_ACTION_HERO_GOAL
    assert receipt["pass_criteria"] == {
        "generate_status": "pass",
        "verify_status": "packet_valid",
    }
    assert receipt["external_signature_status"] == EXTERNAL_SIGNATURE_STATUS
    assert receipt["publication_binding"] == "publication_artifact_not_yet_bound"
    assert (
        receipt["commands"]["review_alias_behavior"]
        == "generate_fresh_then_verify_then_print_card"
    )
    assert receipt["commands"]["no_rerun_verify"] == (
        "make release-candidate-proof-verify"
    )
    assert receipt["failure_interpretations"] == [
        dict(row) for row in FAILURE_INTERPRETATIONS
    ]

    subjects = {row["ref"]: row for row in receipt["artifact_subjects"]}
    assert set(subjects) == set(review_mod.ARTIFACT_SUBJECT_RELS)
    for ref, row in subjects.items():
        digest = hashlib.sha256((_ROOT / ref).read_bytes()).hexdigest()
        assert row["sha256"] == digest, f"stale subject digest: {ref}"

    live_demo = json.loads(
        (_ROOT / review_mod.COMMITTED_DEMO_RECEIPT_REL).read_text(encoding="utf-8")
    )
    assert receipt["expectation"] == extract_committed_expectation(live_demo)
    assert receipt["expectation"]["expected_owner_organ_id"]
    assert receipt["expectation"]["expected_validator_command"]


def test_review_contract_ships_in_every_distribution_lane() -> None:
    """The reviewer contract must reach the reviewer however the artifact
    arrives: sdist, wheel data-files, standalone export, and the entry docs."""
    manifest = (_ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    assert "include RELEASE_REVIEW.md" in manifest

    pyproject = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    data_files = pyproject.get("tool", {}).get("setuptools", {}).get("data-files", {})
    assert "RELEASE_REVIEW.md" in (data_files.get("share/plectis") or [])

    assert "RELEASE_REVIEW.md" in release_export.DEFAULT_INCLUDE_REFS
    assert "RELEASE_REVIEW.md" in release_export.STANDALONE_REQUIRED_PUBLIC_REFS

    readme = (_ROOT / "README.md").read_text(encoding="utf-8")
    assert "RELEASE_REVIEW.md" in readme
    assert "make release-review" in readme

    makefile = (_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "release-review:" in makefile
    assert "tests/test_release_review_contract.py" in makefile
    # The cold-review command really regenerates: the release-review recipe
    # runs generate then the strict no-rerun verify, never a stale-packet cat.
    review_recipe = makefile.split("release-review:", 1)[1]
    assert "$(MAKE) release-candidate-proof" in review_recipe
    assert "$(MAKE) release-candidate-proof-verify" in review_recipe


def test_review_contract_carries_no_leaks() -> None:
    doc_text = (_ROOT / review_mod.DOC_REL).read_text(encoding="utf-8")
    receipt_text = (_ROOT / review_mod.RECEIPT_REL).read_text(encoding="utf-8")
    for body in (doc_text, receipt_text):
        assert "/Users/" not in body and "/home/" not in body
        assert "- Teleology:" not in body


def test_review_write_then_check_goes_red_on_tamper(tmp_path: Path) -> None:
    """Both a hand-edited contract and a changed artifact subject must turn
    --check red with the drifted artifact named."""
    root = _write_min_root(tmp_path)
    assert review_mod.main(["--write", "--root", str(root)]) == 0
    assert review_mod.main(["--check", "--root", str(root)]) == 0

    doc = root / review_mod.DOC_REL
    doc.write_text(doc.read_text() + "\nhand edit\n")
    assert review_mod.main(["--check", "--root", str(root)]) == 1

    # Restore the doc, then drift a SUBJECT: the committed digests no longer
    # match the tree, so the regenerated contract differs and --check refuses.
    assert review_mod.main(["--write", "--root", str(root)]) == 0
    (root / "FIRST_ACTION.md").write_text("changed demonstration\n", encoding="utf-8")
    assert review_mod.main(["--check", "--root", str(root)]) == 1


def test_review_refuses_root_without_committed_demonstration(tmp_path: Path) -> None:
    (tmp_path / "FIRST_ACTION.md").write_text("body\n", encoding="utf-8")
    with pytest.raises(SystemExit) as excinfo:
        review_mod.main(["--write", "--root", str(tmp_path)])
    assert excinfo.value.code == 2


def test_review_refuses_root_with_incomplete_hero_row(tmp_path: Path) -> None:
    root = _write_min_root(tmp_path)
    receipt_path = root / review_mod.COMMITTED_DEMO_RECEIPT_REL
    demo = json.loads(receipt_path.read_text(encoding="utf-8"))
    demo["contracts"][0]["proof_path"] = {}
    receipt_path.write_text(json.dumps(demo), encoding="utf-8")
    with pytest.raises(SystemExit) as excinfo:
        review_mod.main(["--write", "--root", str(root)])
    assert excinfo.value.code == 2


def test_review_guard_refuses_private_path_output(tmp_path: Path) -> None:
    """A committed demonstration carrying a private absolute path must refuse
    to become a written reviewer contract."""
    root = _write_min_root(tmp_path)
    receipt_path = root / review_mod.COMMITTED_DEMO_RECEIPT_REL
    demo = json.loads(receipt_path.read_text(encoding="utf-8"))
    demo["contracts"][0]["first_action"]["command"] = (
        "python /Users/someone/private/run.py"
    )
    receipt_path.write_text(json.dumps(demo), encoding="utf-8")
    with pytest.raises(SystemExit) as excinfo:
        review_mod.main(["--write", "--root", str(root)])
    assert excinfo.value.code == 3
    assert not (root / review_mod.DOC_REL).exists()
