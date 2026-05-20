from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.validators.public_entry_docs import validate_public_entry_docs


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _walk_keys(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        keys = list(payload)
        for value in payload.values():
            keys.extend(_walk_keys(value))
        return keys
    if isinstance(payload, list):
        keys: list[str] = []
        for item in payload:
            keys.extend(_walk_keys(item))
        return keys
    return []


def _copy_public_entry_tree(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "paper_modules", public_root / "paper_modules")
    shutil.copytree(MICROCOSM_ROOT / "skills", public_root / "skills")
    shutil.copy2(MICROCOSM_ROOT / "README.md", public_root / "README.md")
    shutil.copy2(MICROCOSM_ROOT / "AGENTS.md", public_root / "AGENTS.md")
    return public_root


def test_public_entry_docs_validate_and_stay_redacted(tmp_path: Path) -> None:
    public_root = _copy_public_entry_tree(tmp_path)
    out = public_root / "receipts/first_wave/public_entry_docs_validation.json"

    receipt = validate_public_entry_docs(public_root, out, command="pytest")

    assert receipt["status"] == "pass"
    assert receipt["missing_docs"] == []
    assert receipt["missing_required_phrases_by_doc"] == {}
    assert receipt["forbidden_phrases_by_doc"] == {}
    assert receipt["stale_first_slice_only_phrases"] == []
    assert receipt["accepted_current_authority_organs"] == [
        "pattern_binding_contract",
        "executable_doctrine_grammar",
        "proof_diagnostic_evidence_spine",
        "navigation_hologram_route_plane",
        "mission_transaction_work_spine",
        "agent_route_observability_runtime",
        "pattern_assimilation_step",
    ]
    assert receipt["deferred_organs"] == ["formal_math_lean_proof_witness"]
    assert receipt["private_state_scan"]["body_redacted"] is True
    assert receipt["private_state_scan"]["blocking_hit_count"] == 0
    text = out.read_text(encoding="utf-8")
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    assert "matched_excerpt" not in _walk_keys(receipt)
    assert "body" not in _walk_keys(receipt)


def test_public_entry_docs_block_missing_paper_module(tmp_path: Path) -> None:
    public_root = _copy_public_entry_tree(tmp_path)
    (public_root / "paper_modules/cold_clone_probe.md").unlink()

    receipt = validate_public_entry_docs(
        public_root,
        public_root / "receipts/first_wave/public_entry_docs_validation.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert "MISSING_PUBLIC_ENTRY_DOC" in receipt["blocking_codes"]
    assert receipt["missing_docs"] == ["paper_modules/cold_clone_probe.md"]


def test_public_entry_readme_no_longer_claims_first_slice_only() -> None:
    text = (MICROCOSM_ROOT / "README.md").read_text(encoding="utf-8")
    agents = (MICROCOSM_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())
    normalized_agents = " ".join(agents.split())

    assert "Internal Runtime Spine" in text
    assert "Accepted Public Runtime Spine" in agents
    assert "only implemented organ here is `pattern_binding_contract`" not in text
    assert "only implemented organ here is `pattern_binding_contract`" not in agents
    assert "formal_math_lean_proof_witness" in text
    assert "Do not run Lean/Lake" in agents
    assert "runnable, synthetic, and receipt-driven" not in text
    assert "public synthetic microcosm" not in text
    assert "private reconstruction control plane" not in text
    assert "source reconstruction workspace" not in agents
    assert "Use only synthetic fixtures" not in agents
    assert "Receipts Are Authority" not in agents
    assert "macro reconstruction contracts" not in agents
    assert "local project operating substrate" in normalized_text
    assert "executable research prototype" in text
    assert "Architecture Kernel" in text
    assert "microcosm explain <project> <route_id>" in text
    assert "Evidence receipts are the black-box recorder" in text
    assert "executable research prototype" in normalized_agents
    assert "local project operating substrate" in normalized_agents
    assert "Fixtures Are Tests" in agents
    assert "Receipts Are Evidence" in agents


def test_public_entry_commands_do_not_depend_on_parent_state() -> None:
    docs = [
        MICROCOSM_ROOT / "README.md",
        MICROCOSM_ROOT / "skills/cold_start_navigation.md",
    ]

    for path in docs:
        text = path.read_text(encoding="utf-8")
        assert "../state/" not in text
        assert "state/microcosm_portfolio/reconstruction" not in text
        assert "core/preflight_support/organ_fixture_validator_readiness_v1.json" in text
        assert "core/preflight_support/fixture_negative_case_matrix_v1.json" in text
