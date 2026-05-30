from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from microcosm_core.validators.public_entry_docs import validate_public_entry_docs


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MICROCOSM_ROOT.parent


def _macro_std_microcosm_path() -> Path:
    path = REPO_ROOT / "codex/standards/std_microcosm.json"
    if not path.is_file():
        pytest.skip("macro std_microcosm parity check requires ai_workflow parent root")
    return path


def _macro_entry_lattice_path() -> Path:
    path = REPO_ROOT / "codex/doctrine/paper_modules/microcosm_entry_lattice.md"
    if not path.is_file():
        pytest.skip("macro entry lattice parity check requires ai_workflow parent root")
    return path


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


def _accepted_registry_rows(root: Path = MICROCOSM_ROOT) -> list[dict[str, Any]]:
    registry = json.loads((root / "core/organ_registry.json").read_text(encoding="utf-8"))
    return [
        row
        for row in registry["implemented_organs"]
        if row.get("status") == "accepted_current_authority"
    ]


def _accepted_organs_from_registry(root: Path = MICROCOSM_ROOT) -> list[str]:
    return [str(row["organ_id"]) for row in _accepted_registry_rows(root)]


def _copy_public_entry_tree(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "atlas", public_root / "atlas")
    shutil.copytree(MICROCOSM_ROOT / "paper_modules", public_root / "paper_modules")
    shutil.copytree(MICROCOSM_ROOT / "skills", public_root / "skills")
    (public_root / "src/microcosm_core").mkdir(parents=True)
    shutil.copy2(
        MICROCOSM_ROOT / "src/microcosm_core/cli.py",
        public_root / "src/microcosm_core/cli.py",
    )
    shutil.copy2(MICROCOSM_ROOT / "README.md", public_root / "README.md")
    shutil.copy2(MICROCOSM_ROOT / "AGENTS.md", public_root / "AGENTS.md")
    return public_root


def test_quickstart_gives_cold_clone_command_path_and_boundaries() -> None:
    quickstart_path = MICROCOSM_ROOT / "QUICKSTART.md"
    readme = (MICROCOSM_ROOT / "README.md").read_text(encoding="utf-8")
    quickstart = quickstart_path.read_text(encoding="utf-8")

    assert quickstart_path.is_file()
    assert "[QUICKSTART.md](QUICKSTART.md)" in readme
    for phrase in (
        "python3 -m pip install -e '.[test]'",
        "PYTHONPATH=src python3 -m microcosm_core hello .",
        "make smoke",
        ".microcosm/smoke/",
        "Microcosm smoke check: pass",
        "authority: pass",
        "workingness: clear",
        "served status: pass",
        "microcosm hello .",
        "microcosm tour --card .",
        "microcosm status --card .",
        "microcosm authority --card",
        "microcosm workingness --card",
        "microcosm legibility-scorecard",
        "If you are staying source-only",
        "PYTHONPATH=src python3 -m microcosm_core tour --card .",
        "PYTHONPATH=src python3 -m microcosm_core status --card .",
        "PYTHONPATH=src python3 -m microcosm_core authority --card",
        "PYTHONPATH=src python3 -m microcosm_core workingness --card",
        "PYTHONPATH=src python3 -m microcosm_core legibility-scorecard",
        "microcosm serve . --host 127.0.0.1 --port 8765 --max-requests 6",
        "/project/observatory-card",
        "/workingness-card",
        "Open `/workingness` only when you need the full per-organ failure-envelope map.",
        "make ci",
        "make standalone-export EXPORT_OUT=/tmp/microcosm-substrate-export",
        "receipts/release/release_export_receipt.json",
        "cd /tmp/microcosm-substrate-export/microcosm-substrate",
        "validate the exported artifact as its own clone",
        "release_authorized=false",
        "provider calls",
        "source mutation",
        "private-root equivalence",
        "Receipts are drilldown evidence",
        "microcosm evidence list . --limit 25",
        "microcosm evidence inspect . .microcosm/evidence/routes.json",
        "microcosm evidence inspect --project . .microcosm/evidence/routes.json",
        "--limit 0",
    ):
        assert phrase in quickstart


def test_public_repo_boundary_docs_name_runtime_contracts() -> None:
    security_path = MICROCOSM_ROOT / "SECURITY.md"
    contributing_path = MICROCOSM_ROOT / "CONTRIBUTING.md"
    agents_path = MICROCOSM_ROOT / "AGENTS.md"

    assert security_path.is_file()
    assert contributing_path.is_file()
    assert agents_path.is_file()

    security = security_path.read_text(encoding="utf-8")
    contributing = contributing_path.read_text(encoding="utf-8")
    agents = agents_path.read_text(encoding="utf-8")
    normalized_contributing = " ".join(contributing.split())

    for phrase in (
        "not a production security product",
        "microcosm authority --card",
        "microcosm stripping-guard",
        "make install",
        ".venv/bin/python -m pip install -e '.[test]'",
        "PYTHONPATH=src .venv/bin/python -m pytest tests/test_secret_exclusion_scan.py",
        "PYTHONPATH=src python3 -m microcosm_core authority --card",
        "PYTHONPATH=src python3 -m microcosm_core stripping-guard",
        "tests/test_secret_exclusion_scan.py",
        "Do not paste the suspected secret",
    ):
        assert phrase in security
    assert "python3 -m pytest tests/test_secret_exclusion_scan.py" not in security

    for phrase in (
        "make install",
        "make smoke",
        "make ci",
        ".microcosm/smoke/",
        "make standalone-export EXPORT_OUT=/tmp/microcosm-substrate-export",
        "receipts/release/release_export_receipt.json",
        "cd /tmp/microcosm-substrate-export/microcosm-substrate",
        "validate it from inside the exported artifact",
        "release_authorized=false",
        "microcosm hello .",
        "microcosm tour --card .",
        "microcosm status --card .",
        "microcosm authority --card",
        "microcosm workingness --card",
        "microcosm legibility-scorecard",
        "PYTHONPATH=src python3 -m microcosm_core hello .",
        "real non-secret macro bodies",
        "fake progress",
        "tests/test_public_entry_docs.py",
        "./bootstrap.sh",
        "ignored `.microcosm/cold_clone_probe.json` evidence",
    ):
        assert phrase in contributing
    assert "without dumping the full cards into CI logs" in normalized_contributing

    for forbidden in (
        "--emit receipts/cold_clone_probe.json",
        "--emit receipts/cold_clone_probe_local.json",
    ):
        assert forbidden not in security
        assert forbidden not in contributing
        assert forbidden not in agents

    for phrase in (
        "make install",
        "make smoke",
        "make ci",
        "make standalone-export EXPORT_OUT=/tmp/microcosm-substrate-export",
        "receipts/release/release_export_receipt.json",
        "cd /tmp/microcosm-substrate-export/microcosm-substrate",
        "cold-clone check proves the exported package can install",
        "release_authorized=false",
        "microcosm hello .",
        "microcosm tour --card .",
        "microcosm status --card .",
        "microcosm authority --card",
        "microcosm workingness --card",
        "microcosm legibility-scorecard",
        "PYTHONPATH=src python3 -m microcosm_core <command>",
        "public GitHub Actions entry",
    ):
        assert phrase in agents


def test_public_entry_docs_validate_source_open_payload_boundary(tmp_path: Path) -> None:
    public_root = _copy_public_entry_tree(tmp_path)
    out = public_root / "receipts/first_wave/public_entry_docs_validation.json"
    expected_organs = _accepted_organs_from_registry(public_root)
    expected_evidence_classes = {
        str(row["evidence_class"]) for row in _accepted_registry_rows(public_root)
    }

    receipt = validate_public_entry_docs(public_root, out, command="pytest")

    assert receipt["status"] == "pass"
    assert receipt["missing_docs"] == []
    assert receipt["missing_required_phrases_by_doc"] == {}
    assert receipt["forbidden_phrases_by_doc"] == {}
    assert receipt["stale_first_slice_only_phrases"] == []
    assert receipt["accepted_current_authority_organs"] == expected_organs
    assert receipt["duplicate_accepted_organs"] == []
    assert receipt["evidence_class_registry"] == {
        "status": "pass",
        "source_ref": "core/organ_evidence_classes.json",
        "class_count": len(expected_evidence_classes),
        "organ_count": len(expected_organs),
        "missing_organs": [],
        "unexpected_organs": [],
        "duplicate_organs": [],
        "fail_closed_no_default": True,
    }
    assert receipt["entry_spine_claims"]["status"] == "pass"
    assert receipt["entry_spine_claims"]["expected_organ_count"] == len(expected_organs)
    assert receipt["entry_spine_claims"]["blocked_docs"] == []
    assert (
        "accepted status and counts are not progress"
        in receipt["entry_spine_claims"]["authority"]
    )
    for rel in ("README.md", "AGENTS.md"):
        doc_claim = receipt["entry_spine_claims"]["docs"][rel]
        assert doc_claim["status"] == "pass"
        assert doc_claim["expected_count"] == len(expected_organs)
        if doc_claim["claim_mode"] == "inline_inventory":
            assert doc_claim["claimed_count"] == len(expected_organs)
        else:
            assert doc_claim["claim_mode"] == "registry_route"
            assert doc_claim["registry_route_present"] is True
        assert doc_claim["missing_organs"] == []
        assert doc_claim["unexpected_organs"] == []
        assert doc_claim["duplicate_organs"] == []
    route_contract = receipt["entry_packet_route_contract"]
    assert route_contract["status"] == "pass"
    assert route_contract["source_ref"] == "atlas/entry_packet.json"
    assert route_contract["first_command"] == "microcosm tour --card <project>"
    assert route_contract["primary_first_screen_command"] == (
        "microcosm tour --card <project>"
    )
    assert route_contract["missing_local_first_screen_commands"] == []
    assert route_contract["missing_state_refs"] == []
    assert route_contract["missing_observatory_endpoints"] == []
    assert route_contract["missing_drilldown_routes"] == []
    assert route_contract["missing_allowed_drilldowns"] == []
    assert route_contract["command_mismatch"] == []
    assert route_contract["command_order_mismatch"] == []
    assert route_contract["missing_route_selection_rule"] is False
    assert route_contract["route_selection_missing_phrases"] == []
    assert route_contract["readme_route_selection_missing_phrases"] == []
    assert route_contract["unsafe_safe_to_show_flags"] == []
    assert route_contract["cold_start_missing_phrases"] == []
    assert route_contract["cold_start_route_selection_missing_phrases"] == []
    assert route_contract["blocking_reasons"] == []
    help_contract = receipt["cli_first_screen_help_contract"]
    assert help_contract["status"] == "pass"
    assert help_contract["source_ref"] == (
        "src/microcosm_core/cli.py::FIRST_SCREEN_HELP"
    )
    assert help_contract["required_command_order"] == [
        "microcosm tour --card <project>",
        "microcosm status --card <project>",
        "microcosm workingness --card",
        "microcosm proof-lab --out /tmp/microcosm-proof-lab",
        "microcosm serve <project>",
        "microcosm compile <project>",
    ]
    assert help_contract["missing_help_commands"] == []
    assert help_contract["help_command_order_mismatch"] == []
    assert help_contract["missing_boundary_phrases"] == []
    assert help_contract["blocking_reasons"] == []
    assert receipt["deferred_organs"] == []
    assert receipt["secret_exclusion_scan"]["body_in_receipt"] is False
    assert receipt["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert receipt["payload_boundary"]["source_open_default"] is True
    assert receipt["payload_boundary"]["unsafe_payload_bodies_in_receipt"] is False
    assert receipt["payload_boundary"]["metadata_only_standin_authorized"] is False
    assert receipt["authority_ceiling"]["entry_docs_authority"] == (
        "public_entry_navigation_and_real_substrate_posture"
    )
    assert receipt["authority_ceiling"]["secret_export_authorized"] is False
    assert (
        receipt["authority_ceiling"]["metadata_only_standin_policy"]
        == "forbidden_when_real_non_secret_macro_body_is_importable"
    )
    assert (
        receipt["authority_ceiling"]["macro_substrate_import_policy"]
        == "encourage_maximum_non_secret_macro_substrate_import"
    )
    assert receipt["authority_ceiling"]["body_copied_requires_source_target_validation"] is True
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


def test_public_entry_docs_block_missing_evidence_class_registry(tmp_path: Path) -> None:
    public_root = _copy_public_entry_tree(tmp_path)
    (public_root / "core/organ_evidence_classes.json").unlink()

    receipt = validate_public_entry_docs(
        public_root,
        public_root / "receipts/first_wave/public_entry_docs_validation.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert "EVIDENCE_CLASS_REGISTRY_MISMATCH" in receipt["blocking_codes"]
    assert receipt["evidence_class_registry"]["status"] == "missing"
    assert receipt["evidence_class_registry"]["fail_closed_no_default"] is False


def test_public_entry_docs_block_runtime_spine_claim_mismatch(tmp_path: Path) -> None:
    public_root = _copy_public_entry_tree(tmp_path)
    agents = public_root / "AGENTS.md"
    agents_text = agents.read_text(encoding="utf-8")
    agents.write_text(
        agents_text.replace("- `certificate_kernel_execution_lab`\n", "")
        .replace("certificate_kernel_execution_lab", "")
        .replace("`core/organ_registry.json`", "`core/organ_registry.removed.json`")
        .replace(
            "`core/organ_evidence_classes.json`",
            "`core/organ_evidence_classes.removed.json`",
        ),
        encoding="utf-8",
    )

    receipt = validate_public_entry_docs(
        public_root,
        public_root / "receipts/first_wave/public_entry_docs_validation.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert "PUBLIC_ENTRY_SPINE_CLAIM_MISMATCH" in receipt["blocking_codes"]
    assert receipt["entry_spine_claims"]["status"] == "blocked"
    assert receipt["entry_spine_claims"]["blocked_docs"] == ["AGENTS.md"]
    assert receipt["entry_spine_claims"]["docs"]["AGENTS.md"]["missing_organs"] == [
        "certificate_kernel_execution_lab"
    ]


def test_public_entry_docs_accepts_registry_routed_spine_without_full_inline_inventory(
    tmp_path: Path,
) -> None:
    public_root = _copy_public_entry_tree(tmp_path)
    readme = public_root / "README.md"
    agents = public_root / "AGENTS.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            readme.read_text(encoding="utf-8").split(
                "## Internal Runtime Spine",
                1,
            )[1].split("## ", 1)[0],
            (
                "\n\nThis section routes the full public entry inventory through "
                "`core/organ_registry.json` and `core/organ_evidence_classes.json`. "
                "`accepted_current_authority` is not an evidence-strength claim; "
                "read each `evidence_class` before inferring strength. "
                "This public entry inventory/read-model is inventory-only "
                "route-alignment metadata, not product progress, release readiness, "
                "proof correctness, private-root equivalence, or score-based "
                "progress. It is not trading or financial advice. "
                "It does not authorize release. "
                "Use [ORGANS.md](ORGANS.md) and [ARCHITECTURE.md](ARCHITECTURE.md). "
                "Real Substrate Posture.\n\n"
            ),
        ),
        encoding="utf-8",
    )
    agents.write_text(
        agents.read_text(encoding="utf-8").replace(
            agents.read_text(encoding="utf-8").split(
                "## Accepted Public Runtime Spine",
                1,
            )[1].split("## Rules", 1)[0],
            (
                "\n\nThe full public entry inventory routes through "
                "`core/organ_registry.json` and `core/organ_evidence_classes.json`. "
                "`accepted_current_authority` is not an evidence-strength claim; "
                "read each `evidence_class` before inferring strength. "
                "This public entry inventory is inventory-only route-alignment "
                "metadata, not product progress, release readiness, proof "
                "correctness, private-root equivalence, or score-based progress. "
                "Use [ORGANS.md](ORGANS.md) and [ARCHITECTURE.md](ARCHITECTURE.md). "
                "Real Substrate Posture.\n\n"
            ),
        ),
        encoding="utf-8",
    )

    receipt = validate_public_entry_docs(
        public_root,
        public_root / "receipts/first_wave/public_entry_docs_validation.json",
        command="pytest",
    )

    assert receipt["status"] == "pass"
    assert receipt["entry_spine_claims"]["docs"]["README.md"]["claim_mode"] in {
        "inline_inventory",
        "registry_route",
    }
    assert receipt["entry_spine_claims"]["docs"]["AGENTS.md"]["claim_mode"] == (
        "registry_route"
    )
    assert receipt["missing_required_phrases_by_doc"] == {}


def test_public_entry_docs_block_registry_route_with_false_inline_coverage(
    tmp_path: Path,
) -> None:
    # Regression (audit HIGH): a registry_route spine that FALSELY asserts full
    # inline coverage ("all N organs enumerated below") while listing only a
    # handful must not ride through as a vacuous route. Before the fix this
    # returned status=pass with missing_organs=[].
    public_root = _copy_public_entry_tree(tmp_path)
    accepted = _accepted_organs_from_registry()
    # AGENTS.md has a bounded spine section (heading -> Concept entry) matching
    # the validator's own extraction, so the gutted inventory is unambiguous.
    agents = public_root / "AGENTS.md"
    original = agents.read_text(encoding="utf-8")
    section = original.split("## Accepted Public Runtime Spine", 1)[1].split(
        "## Concept And Mechanism Entry", 1
    )[0]
    three = accepted[:3]
    false_route = (
        "\n\nThe full public entry inventory routes through "
        "`core/organ_registry.json` and `core/organ_evidence_classes.json`. "
        "`accepted_current_authority` is not an evidence-strength claim; read each "
        "`evidence_class`. This public entry inventory is inventory-only "
        "route-alignment metadata, not product progress, release readiness. "
        f"All {len(accepted)} accepted public runtime organs are enumerated below: "
        f"`{three[0]}`, `{three[1]}`, `{three[2]}`.\n\n"
    )
    agents.write_text(original.replace(section, false_route), encoding="utf-8")

    receipt = validate_public_entry_docs(
        public_root,
        public_root / "receipts/first_wave/public_entry_docs_validation.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert "PUBLIC_ENTRY_SPINE_CLAIM_MISMATCH" in receipt["blocking_codes"]
    agents_claim = receipt["entry_spine_claims"]["docs"]["AGENTS.md"]
    assert agents_claim["status"] == "blocked"
    assert agents_claim["claimed_count"] < len(accepted)
    assert agents_claim["missing_organs"]


@pytest.mark.parametrize(
    "overclaim_sentence",
    [
        "Microcosm is production-ready and authorized for hosted release; ship it to PyPI.",
        "When you run it, Microcosm calls your configured model provider and emails the reviewer the scorecard.",
        "This public tree is functionally the private macro root; every secret is reproduced here.",
        "With all organs accepted, Microcosm is proven correct end-to-end.",
        "Read the evidence rank as the quality score and overall maturity level.",
    ],
)
def test_public_entry_docs_block_injected_authority_overclaim(
    tmp_path: Path,
    overclaim_sentence: str,
) -> None:
    # Regression (audit MEDIUM, 5 classes): an affirmative overclaim sentence
    # coexisting with the mandated anti-claim must block. Before the fix the
    # validator only checked anti-claim PRESENCE, never positive-claim ABSENCE.
    public_root = _copy_public_entry_tree(tmp_path)
    readme = public_root / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8") + "\n\n" + overclaim_sentence + "\n",
        encoding="utf-8",
    )

    receipt = validate_public_entry_docs(
        public_root,
        public_root / "receipts/first_wave/public_entry_docs_validation.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert "PUBLIC_ENTRY_OVERCLAIM" in receipt["blocking_codes"]
    assert "README.md" in receipt["public_entry_overclaim_by_doc"]


def test_public_entry_docs_block_overclaim_in_generated_atlas_doc(
    tmp_path: Path,
) -> None:
    # Regression (audit MEDIUM, scope): ORGANS.md/ARCHITECTURE.md are not in
    # REQUIRED_DOCS but ARE cold-reader surfaces README routes to; an overclaim
    # injected there must still block.
    public_root = _copy_public_entry_tree(tmp_path)
    (public_root / "ORGANS.md").write_text(
        "# Organ Atlas\n\nThis substrate is proven correct end-to-end.\n",
        encoding="utf-8",
    )

    receipt = validate_public_entry_docs(
        public_root,
        public_root / "receipts/first_wave/public_entry_docs_validation.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert "PUBLIC_ENTRY_OVERCLAIM" in receipt["blocking_codes"]
    assert "ORGANS.md" in receipt["public_entry_overclaim_by_doc"]


def test_public_entry_docs_block_entry_packet_route_contract_drift(
    tmp_path: Path,
) -> None:
    public_root = _copy_public_entry_tree(tmp_path)
    entry_packet_path = public_root / "atlas/entry_packet.json"
    entry_packet = json.loads(entry_packet_path.read_text(encoding="utf-8"))
    entry_packet["local_first_screen_route"]["command_path"].remove(
        "microcosm status --card <project>"
    )
    entry_packet_path.write_text(
        json.dumps(entry_packet, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    receipt = validate_public_entry_docs(
        public_root,
        public_root / "receipts/first_wave/public_entry_docs_validation.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert "ENTRY_PACKET_ROUTE_CONTRACT_MISMATCH" in receipt["blocking_codes"]
    assert receipt["entry_packet_route_contract"]["status"] == "blocked"
    assert receipt["entry_packet_route_contract"][
        "missing_local_first_screen_commands"
    ] == ["microcosm status --card <project>"]
    assert "missing_local_first_screen_commands" in receipt[
        "entry_packet_route_contract"
    ]["blocking_reasons"]


def test_public_entry_docs_block_cold_clone_tracked_emit_as_default(
    tmp_path: Path,
) -> None:
    public_root = _copy_public_entry_tree(tmp_path)
    entry_packet_path = public_root / "atlas/entry_packet.json"
    entry_packet = json.loads(entry_packet_path.read_text(encoding="utf-8"))
    stale_command = "./bootstrap.sh --suite first-wave --emit receipts/cold_clone_probe.json"
    entry_packet["cold_clone_validation_command"] = stale_command
    entry_packet["local_first_screen_route"]["cold_clone_validation_suite"] = (
        stale_command
    )
    entry_packet["cold_clone_probe_route"]["command"] = stale_command
    entry_packet["cold_clone_probe_route"]["receipt_ref"] = (
        "receipts/cold_clone_probe.json"
    )
    entry_packet["allowed_drilldowns"].extend(
        [stale_command, "receipts/cold_clone_probe.json"]
    )
    entry_packet["receipt_dependencies"].append("receipts/cold_clone_probe.json")
    entry_packet_path.write_text(
        json.dumps(entry_packet, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    receipt = validate_public_entry_docs(
        public_root,
        public_root / "receipts/first_wave/public_entry_docs_validation.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert "ENTRY_PACKET_ROUTE_CONTRACT_MISMATCH" in receipt["blocking_codes"]
    route_contract = receipt["entry_packet_route_contract"]
    assert route_contract["status"] == "blocked"
    assert "cold_clone_local_receipt_boundary_mismatch" in route_contract[
        "blocking_reasons"
    ]
    assert set(route_contract["cold_clone_boundary_mismatches"]) >= {
        "cold_clone_validation_command",
        "local_first_screen_route",
        "cold_clone_probe_route.command",
        "cold_clone_probe_route.receipt_ref",
        "allowed_drilldowns.tracked_emit",
        "allowed_drilldowns.tracked_receipt",
        "receipt_dependencies.tracked_receipt",
    }


def test_public_entry_docs_block_readme_route_selection_truth_drift(
    tmp_path: Path,
) -> None:
    public_root = _copy_public_entry_tree(tmp_path)
    readme = public_root / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            "`missing_tests_route`",
            "`some route`",
        ),
        encoding="utf-8",
    )

    receipt = validate_public_entry_docs(
        public_root,
        public_root / "receipts/first_wave/public_entry_docs_validation.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert "ENTRY_PACKET_ROUTE_CONTRACT_MISMATCH" in receipt["blocking_codes"]
    route_contract = receipt["entry_packet_route_contract"]
    assert "readme_route_selection_rule_missing" in route_contract[
        "blocking_reasons"
    ]
    assert "`missing_tests_route` when tests are absent" in route_contract[
        "readme_route_selection_missing_phrases"
    ]


def test_public_entry_docs_block_entry_packet_route_selection_truth_drift(
    tmp_path: Path,
) -> None:
    public_root = _copy_public_entry_tree(tmp_path)
    entry_packet_path = public_root / "atlas/entry_packet.json"
    entry_packet = json.loads(entry_packet_path.read_text(encoding="utf-8"))
    route = entry_packet["local_first_screen_route"]
    route["route_selection_rule"] = route["route_selection_rule"].replace(
        "Empty or non-README folders can select missing_tests_route, including "
        "missing_tests_route when tests are absent.",
        "README folders select readme_onboarding_route.",
    )
    entry_packet_path.write_text(
        json.dumps(entry_packet, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    receipt = validate_public_entry_docs(
        public_root,
        public_root / "receipts/first_wave/public_entry_docs_validation.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert "ENTRY_PACKET_ROUTE_CONTRACT_MISMATCH" in receipt["blocking_codes"]
    route_contract = receipt["entry_packet_route_contract"]
    assert "missing_route_selection_rule" in route_contract["blocking_reasons"]
    assert "Empty or non-README folders can select missing_tests_route" in (
        route_contract["route_selection_missing_phrases"]
    )
    assert "missing_tests_route when tests are absent" in route_contract[
        "route_selection_missing_phrases"
    ]


def test_public_entry_docs_block_cold_start_route_selection_truth_drift(
    tmp_path: Path,
) -> None:
    public_root = _copy_public_entry_tree(tmp_path)
    cold_start = public_root / "skills/cold_start_navigation.md"
    cold_start.write_text(
        cold_start.read_text(encoding="utf-8").replace(
            "`missing_tests_route`",
            "`some route`",
        ),
        encoding="utf-8",
    )

    receipt = validate_public_entry_docs(
        public_root,
        public_root / "receipts/first_wave/public_entry_docs_validation.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert "ENTRY_PACKET_ROUTE_CONTRACT_MISMATCH" in receipt["blocking_codes"]
    route_contract = receipt["entry_packet_route_contract"]
    assert "cold_start_route_selection_rule_missing" in route_contract[
        "blocking_reasons"
    ]
    assert "Empty/non-README folders can select `missing_tests_route`" in (
        route_contract["cold_start_route_selection_missing_phrases"]
    )
    assert "`missing_tests_route` when tests are absent" in route_contract[
        "cold_start_route_selection_missing_phrases"
    ]


def test_public_entry_docs_block_cli_first_screen_help_drift(
    tmp_path: Path,
) -> None:
    public_root = _copy_public_entry_tree(tmp_path)
    cli_path = public_root / "src/microcosm_core/cli.py"
    original = cli_path.read_text(encoding="utf-8")
    expected_help_block = (
        "  microcosm status --card <project> read the compressed "
        "project/runtime status lens\n"
        "  microcosm spine --card          read the compact runtime spine lens\n"
        "  microcosm run --card examples/runtime_shell/demo_project "
        "replay the public runtime demo\n"
        "  microcosm authority --card      read the compact authority ceiling lens\n"
        "  microcosm intake --card         read the compact intake/projection bridge lens\n"
        "  microcosm workingness --card    read the compact behavior/failure "
        "lens\n"
        "  microcosm workingness           inspect behavior evidence "
        "and failure gaps\n"
    )
    assert expected_help_block in original
    mutated_help_block = (
        "  microcosm workingness --card    read the compact behavior/failure "
        "lens\n"
        "  microcosm workingness           inspect behavior evidence "
        "and failure gaps\n"
        "  microcosm status --card <project> read the compressed "
        "project/runtime status lens\n"
        "  microcosm spine --card          read the compact runtime spine lens\n"
        "  microcosm run --card examples/runtime_shell/demo_project "
        "replay the public runtime demo\n"
        "  microcosm authority --card      read the compact authority ceiling lens\n"
        "  microcosm intake --card         read the compact intake/projection bridge lens\n"
    )
    cli_path.write_text(
        original.replace(expected_help_block, mutated_help_block),
        encoding="utf-8",
    )

    receipt = validate_public_entry_docs(
        public_root,
        public_root / "receipts/first_wave/public_entry_docs_validation.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert "CLI_FIRST_SCREEN_HELP_CONTRACT_MISMATCH" in receipt["blocking_codes"]
    help_contract = receipt["cli_first_screen_help_contract"]
    assert help_contract["status"] == "blocked"
    assert help_contract["missing_help_commands"] == []
    assert help_contract["help_command_order_mismatch"] == [
        "microcosm status --card <project> before microcosm workingness --card"
    ]
    assert help_contract["blocking_reasons"] == ["help_command_order_mismatch"]


def test_public_entry_readme_no_longer_claims_first_slice_only() -> None:
    text = (MICROCOSM_ROOT / "README.md").read_text(encoding="utf-8")
    agents = (MICROCOSM_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())
    normalized_agents = " ".join(agents.split())
    expected_organs = _accepted_organs_from_registry()

    assert "Internal Runtime Spine" in text
    assert "Accepted Public Runtime Spine" in agents
    assert "Real Substrate Posture" in text
    assert "Real Substrate Posture" in agents
    assert "public entry inventory/read-model" in text
    assert "public entry inventory" in agents
    assert "inventory-only route-alignment metadata" in text
    assert "inventory-only route-alignment metadata" in normalized_agents
    assert "not product progress, release readiness" in text
    assert "not product progress, release readiness" in agents
    assert "not a product progress meter" in normalized_text
    assert "bridge_phase_continuity_runtime" in text
    assert "bridge_phase_continuity_runtime" in agents
    assert "bridge-phase-continuity-runtime" in text
    assert "bridge-phase-continuity-runtime" in agents
    assert "Microcosm is the public repo form of the macro system" in text
    assert "Microcosm is the public repo form of the macro system" in agents
    assert "not a synthetic safety proxy" in text
    assert "not a synthetic safety proxy" in agents
    assert "Public should carry private by default" in text
    assert "Public should carry private by default" in agents
    assert "as much of the macro substrate as possible" in normalized_text
    assert "as much of the macro substrate as possible" in normalized_agents
    assert "The exclusion set is narrow" in text
    assert "The hard exclusion set is narrow" in agents
    assert "raw operator voice, slurs or abusive wording" in normalized_text
    assert "raw operator voice, slurs or abusive wording" in normalized_agents
    assert "Any `body_copied=true` claim must name the source file" in text
    assert "Any `body_copied=true` claim must point at a real target file" in agents
    assert "front_door_status.blocking_surface_ids" in text
    assert "exits zero for the expected first-run missing-state recovery card" in normalized_text
    assert "not benchmark scores" in text
    assert "not benchmark scores" in agents
    assert "not score-based progress, maturity" in text
    assert "not score-based progress" in agents
    assert "public-safe ten-minute path" not in normalized_text
    assert "public-safe authority ceiling" not in normalized_text
    assert "public-safe route" not in normalized_agents
    assert "only to project metadata" not in normalized_agents
    assert "only implemented organ here is `pattern_binding_contract`" not in text
    assert "only implemented organ here is `pattern_binding_contract`" not in agents
    assert len(expected_organs) > 1
    assert "pattern_binding_contract" in expected_organs
    assert "bridge_phase_continuity_runtime" in expected_organs
    assert "core/organ_registry.json" in text
    assert "core/organ_registry.json" in agents
    assert "core/organ_evidence_classes.json" in text
    assert "core/organ_evidence_classes.json" in agents
    assert "microcosm reveal" in text
    assert "microcosm spatial-simulation" in text
    assert "microcosm reveal" in agents
    assert "spatial-simulation" in agents
    assert "microcosm tour --card <project>" in agents
    assert agents.index("microcosm tour --card <project>") < agents.index(
        "microcosm tour <project>"
    )
    assert "Do not widen Lean/Lake" in agents
    assert "Do not treat prediction fixtures as trading or financial advice" in agents
    assert "runnable, synthetic, and receipt-driven" not in text
    assert "public synthetic microcosm" not in text
    assert "private reconstruction control plane" not in text
    assert "source reconstruction workspace" not in agents
    assert "Use only synthetic fixtures" not in agents
    assert "Receipts Are Authority" not in agents
    assert "macro reconstruction contracts" not in agents
    assert "local project operating substrate" in normalized_text
    assert "repo -> .microcosm" in text
    assert "microcosm compile ." in text
    assert "front_door.route_explanation" in text
    assert "source_files_mutated=false" in text
    assert "std_python_microcosm_navigation_assay" in text
    assert "implementation_atlas.python_navigation_assay" in text
    assert "route_utility_curriculum" in text
    assert "route_utility_curriculum.ratchet" in text
    assert "executable research prototype" in text
    assert "Architecture Kernel" in text
    assert "microcosm explain <project> <route_id>" in text
    assert "Evidence receipts are the black-box recorder" in text
    assert "evidence_class" in text
    assert "`accepted_current_authority` is not an evidence-strength claim" in normalized_text
    assert "executable research prototype" in normalized_agents
    assert "local project operating substrate" in normalized_agents
    assert "microcosm compile <project>" in agents
    assert "repo -> `.microcosm`" in agents
    assert "Fixtures Are Tests" in agents
    assert "Receipts Are Evidence" in agents
    assert "evidence_class" in agents
    assert "`accepted_current_authority` is not an evidence-strength claim" in normalized_agents


def test_public_entry_commands_do_not_depend_on_parent_state() -> None:
    docs = [
        MICROCOSM_ROOT / "README.md",
        MICROCOSM_ROOT / "skills/cold_start_navigation.md",
    ]

    text_by_name = {path.name: path.read_text(encoding="utf-8") for path in docs}

    for text in text_by_name.values():
        assert "../state/" not in text
        assert "state/microcosm_portfolio/reconstruction" not in text
    cold_start_nav = text_by_name["cold_start_navigation.md"]
    assert "core/preflight_support/organ_fixture_validator_readiness_v1.json" in cold_start_nav
    assert "core/preflight_support/fixture_negative_case_matrix_v1.json" in cold_start_nav
    cold_start = (MICROCOSM_ROOT / "skills/cold_start_navigation.md").read_text(
        encoding="utf-8"
    )
    normalized_cold_start = " ".join(cold_start.split())
    assert "std_python_microcosm_navigation_assay" in cold_start
    assert "implementation_atlas.python_navigation_assay" in cold_start
    assert "route_utility_curriculum" in cold_start
    assert "route_utility_curriculum.ratchet" in cold_start
    assert "proof-lab --out /tmp/microcosm-proof-lab" in cold_start
    assert "verifier-lab-kernel run-kernel-bundle" in cold_start
    assert "formal_prover_context_strategy_gate" in cold_start
    assert "First-Screen Route Contract" in cold_start
    assert "Bring a folder first" in cold_start
    assert "route_cards_by_id.status_and_workingness" in cold_start
    assert "microcosm evidence list <project> --limit 25" in cold_start
    assert "microcosm evidence inspect <project> <ref>" in cold_start
    assert "microcosm status --card <project>" in cold_start
    assert "front_door.route_explanation" in cold_start
    assert "microcosm workingness" in cold_start
    assert (
        "microcosm serve <project> --host 127.0.0.1 --port 8765" in cold_start
    )
    assert (
        "microcosm serve <project> --host 127.0.0.1 --port 8765 --max-requests 6"
        in cold_start
    )
    assert (
        "PYTHONPATH=src python3 -m microcosm_core serve <project> --host "
        "127.0.0.1 --port 8765 --max-requests 6"
    ) in cold_start
    assert (
        "Omit `--max-requests` only when you intentionally want an interactive server"
        in normalized_cold_start
    )
    assert "/project/observatory-card" in cold_start
    assert "before `/project/observatory`" in cold_start
    assert "Receipts are evidence drilldowns after the behavior route is visible" in (
        cold_start
    )
    assert "Do not hardcode `readme_onboarding_route` for arbitrary folders" in (
        cold_start
    )
    assert "Empty/non-README folders can select `missing_tests_route`" in cold_start
    assert "`missing_tests_route` when tests are absent" in cold_start
    assert "atlas/entry_packet.json::local_first_screen_route" in cold_start
    assert "atlas/entry_packet.json::cold_clone_probe_route" in cold_start
    assert "atlas/entry_packet.json::proof_lab_route" in cold_start
    assert "atlas/entry_packet.json::status_and_workingness_route" in cold_start
    assert "make standalone-export EXPORT_OUT=/tmp/microcosm-substrate-export" in cold_start
    assert "cd /tmp/microcosm-substrate-export/microcosm-substrate" in cold_start
    assert "cold-clone check proves the exported artifact can install" in cold_start
    assert "receipts/release/release_export_receipt.json" in cold_start
    assert "release_authorized=false" in cold_start


def test_public_entry_docs_keep_tour_before_compile() -> None:
    entry_packet = json.loads(
        (MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8")
    )
    assert entry_packet["first_command"] == "microcosm tour --card <project>"

    readme = (MICROCOSM_ROOT / "README.md").read_text(encoding="utf-8")
    first_run = readme.split("## First Run", 1)[1]
    installed_block = first_run.split(
        "The same commands work without installing the console script:", 1
    )[0].split("```bash", 1)[1].split("```", 1)[0]
    no_install_block = first_run.split(
        "The same commands work without installing the console script:", 1
    )[1].split("```", 2)[1]
    assert "python3 -m microcosm_core.cli" not in no_install_block
    assert (
        "microcosm serve /tmp/microcosm-scratch --host 127.0.0.1 "
        "--port 8765 --max-requests 6"
    ) in installed_block
    assert (
        "microcosm serve /tmp/microcosm-scratch --host 127.0.0.1 --port 8765\n"
        not in installed_block
    )
    tour_command = (
        "PYTHONPATH=src python3 -m microcosm_core tour --card /tmp/microcosm-scratch"
    )
    status_command = (
        "PYTHONPATH=src python3 -m microcosm_core status --card "
        "/tmp/microcosm-scratch"
    )
    proof_command = (
        "PYTHONPATH=src python3 -m microcosm_core proof-lab --out "
        "/tmp/microcosm-proof-lab"
    )
    serve_command = (
        "PYTHONPATH=src python3 -m microcosm_core serve "
        "/tmp/microcosm-scratch --host 127.0.0.1 --port 8765 --max-requests 6"
    )
    compile_command = (
        "PYTHONPATH=src python3 -m microcosm_core compile "
        "/tmp/microcosm-scratch"
    )
    assert no_install_block.index(tour_command) < no_install_block.index(
        status_command
    )
    assert no_install_block.index(proof_command) < no_install_block.index(
        serve_command
    )
    assert no_install_block.index(serve_command) < no_install_block.index(
        compile_command
    )
    assert no_install_block.index(proof_command) < no_install_block.index(
        compile_command
    )

    cold_start = (MICROCOSM_ROOT / "skills/cold_start_navigation.md").read_text(
        encoding="utf-8"
    )
    assert cold_start.index("Run `microcosm tour --card <project>`") < cold_start.index(
        "Run `microcosm compile <project>`"
    )
    assert cold_start.index(
        "Open `atlas/entry_packet.json::status_and_workingness_route`"
    ) < cold_start.index(
        "Run `microcosm compile <project>`"
    )
    assert cold_start.index(
        "`PYTHONPATH=src python3 -m microcosm_core tour --card <project>`"
    ) < cold_start.index(
        "`PYTHONPATH=src python3 -m microcosm_core compile <project>`"
    )


def test_public_entry_packet_routes_local_first_screen_before_probe() -> None:
    entry_packet = json.loads(
        (MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8")
    )

    route = entry_packet["local_first_screen_route"]
    assert entry_packet["first_command"] == "microcosm tour --card <project>"
    assert route["surface_id"] == "microcosm_local_first_screen"
    assert route["primary_first_screen_command"] == "microcosm tour --card <project>"
    assert route["primary_first_screen_command"] == entry_packet["first_command"]
    assert route["command_path"][:6] == [
        "microcosm tour --card <project>",
        "microcosm status --card <project>",
        "microcosm workingness --card",
        "microcosm proof-lab --out /tmp/microcosm-proof-lab",
        "microcosm observe <project>",
        "microcosm serve <project> --host 127.0.0.1 --port 8765",
    ]
    assert (
        "microcosm serve <project> --host 127.0.0.1 --port 8765 --max-requests 6"
        in route["command_path"]
    )
    assert route["command_path"].index(
        "microcosm status --card <project>"
    ) < route["command_path"].index("microcosm compile <project>")
    assert route["command_path"].index(
        "microcosm proof-lab --out /tmp/microcosm-proof-lab"
    ) < route["command_path"].index("microcosm python-lens <project>")
    assert "microcosm python-lens <project>" in route["command_path"]
    assert (
        "microcosm explain <project> <selected_route_id>"
        in route["command_path"]
    )
    assert route["selected_route_id_source"] == (
        "microcosm tour --card <project>::selected_route_id or "
        "microcosm tour <project>::selected_route_id or "
        "microcosm tour <project>::first_screen.selected_route_id or "
        "microcosm compile <project>::selected_route_id"
    )
    assert "readme_onboarding_route is a generated route only" in route[
        "route_selection_rule"
    ]
    assert "microcosm evidence list <project> --limit 25" in route["command_path"]
    assert "microcosm evidence inspect <project> <ref>" in route["command_path"]
    assert "microcosm status --card <project>" in route["command_path"]
    assert "microcosm workingness --card" in route["command_path"]
    assert "microcosm proof-lab --out /tmp/microcosm-proof-lab" in route[
        "command_path"
    ]
    assert "microcosm observe <project>" in route["command_path"]
    assert route["reader_routes_ref"] == (
        "atlas/entry_packet.json::reader_first_screen_routes"
    )
    assert route["reader_route_ids"] == [
        "public_github_visitor",
        "safety_evals_engineer",
        "hiring_reviewer",
        "peer_developer",
    ]
    assert ".microcosm/events.jsonl" in route["state_refs"]
    assert ".microcosm/evidence/" in route["state_refs"]
    assert ".microcosm/graph.json" in route["state_refs"]
    assert "/" in route["observatory_endpoints"]
    assert "/status" in route["observatory_endpoints"]
    assert "/tour" in route["observatory_endpoints"]
    assert "/workingness-card" in route["observatory_endpoints"]
    assert "/workingness" in route["observatory_endpoints"]
    assert "/proof-lab" in route["observatory_endpoints"]
    assert "/project/observe" in route["observatory_endpoints"]
    assert "/project/observatory-card" in route["observatory_endpoints"]
    assert "/project/observatory" in route["observatory_endpoints"]
    assert "/project/explain/<selected_route_id>" in route["observatory_endpoints"]
    assert "tour_front_door_status_route" in route["drilldown_routes"]
    assert "status_before_tour_recovery_route" in route["drilldown_routes"]
    assert "status_and_workingness_route" in route["drilldown_routes"]
    assert "proof_lab_route" in route["drilldown_routes"]
    assert (
        route["cold_clone_validation_suite"]
        == entry_packet["cold_clone_validation_command"]
    )
    assert route["safe_to_show"]["source_files_mutated"] is False
    assert route["safe_to_show"]["provider_calls_authorized"] is False
    assert route["safe_to_show"]["release_authorized"] is False
    assert route["safe_to_show"]["proof_correctness_claim"] is False

    probe = entry_packet["cold_clone_probe_route"]
    assert probe["command"] == entry_packet["cold_clone_validation_command"]
    assert probe["command"] in entry_packet["allowed_drilldowns"]
    assert probe["receipt_ref"] in entry_packet["allowed_drilldowns"]
    assert probe["receipt_ref"] in entry_packet["receipt_dependencies"]
    assert entry_packet["cold_clone_validation_command"] == "./bootstrap.sh"
    assert route["cold_clone_validation_suite"] == "./bootstrap.sh"
    assert probe["command"] == "./bootstrap.sh"
    assert probe["receipt_ref"] == ".microcosm/cold_clone_probe.json"
    assert "Pass --emit only when refreshing" in probe["tracked_refresh_rule"]
    assert (
        "./bootstrap.sh --suite first-wave --emit receipts/cold_clone_probe.json"
        not in entry_packet["allowed_drilldowns"]
    )
    assert "receipts/cold_clone_probe.json" not in entry_packet[
        "receipt_dependencies"
    ]
    assert (
        probe["entry_role"]
        == "validation suite after local first-screen behavior is visible"
    )
    for command in route["command_path"]:
        assert command in entry_packet["allowed_drilldowns"]
    for ref in route["state_refs"]:
        assert ref in entry_packet["allowed_drilldowns"]
    for endpoint in route["observatory_endpoints"]:
        assert endpoint in entry_packet["allowed_drilldowns"]
    assert "atlas/entry_packet.json::local_first_screen_route" in entry_packet[
        "allowed_drilldowns"
    ]
    assert "atlas/entry_packet.json::reader_first_screen_routes" in entry_packet[
        "allowed_drilldowns"
    ]


def test_public_entry_packet_exposes_reader_typed_routes() -> None:
    entry_packet = json.loads(
        (MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8")
    )

    reader_routes = entry_packet["reader_first_screen_routes"]
    assert reader_routes["shared_prerequisite_command"] == (
        "microcosm tour --card <project>"
    )
    rows = {row["reader_id"]: row for row in reader_routes["routes"]}
    assert set(rows) == {
        "public_github_visitor",
        "safety_evals_engineer",
        "hiring_reviewer",
        "peer_developer",
    }
    assert rows["public_github_visitor"]["first_screen_command"] == (
        "microcosm hello <project>"
    )
    assert rows["public_github_visitor"]["next_command"] == (
        "microcosm tour --card <project>"
    )
    assert rows["safety_evals_engineer"]["first_screen_command"] == (
        "microcosm status --card <project>"
    )
    assert rows["hiring_reviewer"]["first_screen_command"] == (
        "microcosm legibility-scorecard"
    )
    assert rows["peer_developer"]["next_command"] == "microcosm observe <project>"
    assert "maturity score" in rows["safety_evals_engineer"]["anti_misread"]


def test_cold_reader_route_map_names_compact_path_before_drilldowns() -> None:
    route_map = (
        MICROCOSM_ROOT / "paper_modules/cold_reader_route_map.md"
    ).read_text(encoding="utf-8")
    accepted_path = route_map.split("The accepted path is:", 1)[1].split(
        "Full drilldowns stay available", 1
    )[0]
    compact_commands = [
        "microcosm hello <project>",
        "microcosm tour --card <project>",
        "microcosm status --card <project>",
        "microcosm authority --card",
        "microcosm workingness --card",
        "microcosm legibility-scorecard",
    ]

    command_positions = []
    for command in compact_commands:
        wrapped = f"`{command}`"
        assert wrapped in accepted_path
        command_positions.append(accepted_path.index(wrapped))
    assert command_positions == sorted(command_positions)

    drilldowns = route_map.split("Full drilldowns stay available", 1)[1].split(
        "## Reader-Specific Evidence Routing", 1
    )[0]
    for command in [
        "microcosm tour <project>",
        "microcosm compile <project>",
        "microcosm proof-lab --out /tmp/microcosm-proof-lab",
    ]:
        assert f"`{command}`" in drilldowns


def test_public_entry_packet_routes_python_navigation_assay() -> None:
    entry_packet = json.loads(
        (MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8")
    )
    encoded_entry_packet = json.dumps(entry_packet, sort_keys=True)
    assert "body_redacted" not in encoded_entry_packet
    assert "public_first_slice" not in encoded_entry_packet
    assert "public first slice" not in encoded_entry_packet

    route = entry_packet["python_navigation_route"]
    assert route["surface_id"] == "project_python_lens"
    assert route["command"] == "microcosm python-lens <project>"
    assert route["assay_id"] == "std_python_microcosm_navigation_assay"
    assert route["assay_ref"] == ".microcosm/python_lens.json::navigation_assay"
    assert route["implementation_atlas_ref"] == (
        ".microcosm/python_lens.json::implementation_atlas.python_navigation_assay"
    )
    assert (
        route["route_utility_curriculum_ref"]
        == ".microcosm/python_lens.json::route_utility_curriculum"
    )
    assert (
        route["route_utility_ratchet_ref"]
        == ".microcosm/python_lens.json::route_utility_curriculum.ratchet"
    )
    assert ".microcosm/python_lens.json::route_utility_curriculum" in entry_packet[
        "allowed_drilldowns"
    ]
    assert ".microcosm/python_lens.json::route_utility_curriculum.ratchet" in entry_packet[
        "allowed_drilldowns"
    ]
    assert route["canonical_depth_ladder"] == [
        "module_docs",
        "file_card",
        "symbol_capsule",
        "graph_context",
        "source_span",
    ]
    assert route["payload_boundary_ref"] == "project_python_lens_read_model"
    assert route["source_bodies_exported"] is False
    assert "body_redacted" not in route


def test_public_entry_packet_routes_proof_lab_first_screen() -> None:
    entry_packet = json.loads(
        (MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8")
    )

    proof_lab = entry_packet["proof_lab_route"]
    assert proof_lab["surface_id"] == "first_screen_verifier_lab_kernel"
    assert proof_lab["organ_id"] == "verifier_lab_kernel"
    assert proof_lab["command"] == "microcosm proof-lab --out /tmp/microcosm-proof-lab"
    assert proof_lab["expanded_command"] == (
        "microcosm verifier-lab-kernel run-kernel-bundle --input "
        "examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle --out "
        "/tmp/microcosm-proof-lab"
    )
    assert proof_lab["endpoint"] == "/proof-lab"
    assert proof_lab["alias_endpoints"] == ["/verifier-lab-kernel"]
    assert proof_lab["source_lens_endpoint"] == "/proof-loop-depth"
    assert proof_lab["route_id"] == "formal_prover_context_strategy_gate"
    assert proof_lab["route_component_count"] == 9
    assert proof_lab["route_ref"] == (
        "examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle/proof_lab_route.json"
    )
    assert proof_lab["standard_ref"] == "standards/std_microcosm_verifier_lab_kernel.json"
    assert proof_lab["paper_module_ref"] == "paper_modules/verifier_lab_kernel.md"
    assert proof_lab["safe_to_show"]["proof_bodies_exported"] is False
    assert proof_lab["safe_to_show"]["provider_payload_bodies_exported"] is False
    assert proof_lab["safe_to_show"]["credential_equivalent_payloads_exported"] is False
    assert proof_lab["safe_to_show"]["release_authorized"] is False
    assert proof_lab["route_ref"] in entry_packet["allowed_drilldowns"]
    assert proof_lab["receipt_ref"] in entry_packet["allowed_drilldowns"]
    assert proof_lab["command"] in entry_packet["allowed_drilldowns"]
    assert proof_lab["expanded_command"] in entry_packet["allowed_drilldowns"]
    assert proof_lab["receipt_ref"] in entry_packet["receipt_dependencies"]

    front_door = entry_packet["tour_front_door_status_route"]
    assert front_door["surface_id"] == "microcosm_tour_front_door_status"
    assert front_door["command"] == "microcosm tour <project>"
    assert front_door["endpoint"] == "/tour"
    assert front_door["status_ref"] in entry_packet["allowed_drilldowns"]
    assert front_door["receipt_ref"] in entry_packet["allowed_drilldowns"]
    assert "receipts/runtime_shell/public_ten_minute_tour.json" in entry_packet[
        "receipt_dependencies"
    ]
    assert front_door["warning_drilldown_surface_ids"] == ["authority", "intake"]
    assert front_door["safe_to_show"]["release_authorized"] is False
    assert front_door["safe_to_show"]["source_mutation_authorized"] is False
    assert "status" in front_door["expected_fields"]
    assert "blocking_surface_ids" in front_door["top_level_status_rule"]

    recovery_route = entry_packet["status_before_tour_recovery_route"]
    assert recovery_route["surface_id"] == "microcosm_status_before_tour_recovery"
    assert recovery_route["command"] == "microcosm status --card <project>"
    assert recovery_route["recovery_ref"] in entry_packet["allowed_drilldowns"]
    assert recovery_route["blocking_detail_ref"] in entry_packet["allowed_drilldowns"]
    assert recovery_route["expected_blocked_state"] == {
        "status": "blocked",
        "project_state_status": "missing_state",
        "primary_recovery_command": "microcosm tour --card <project>",
        "status_after_recovery_command": "microcosm status --card <project>",
        "alternate_recovery_command": "microcosm compile <project>",
    }
    assert recovery_route["safe_to_show"]["recovery_command_visible"] is True
    assert recovery_route["safe_to_show"]["source_files_mutated"] is False
    assert recovery_route["safe_to_show"]["provider_calls_authorized"] is False

    workingness = entry_packet["status_and_workingness_route"]
    assert workingness["surface_id"] == "microcosm_status_and_workingness"
    assert workingness["command"] == "microcosm status --card <project>"
    assert workingness["next_command"] == "microcosm workingness --card"
    assert workingness["status_card_command"] == "microcosm status --card <project>"
    assert workingness["workingness_command"] == "microcosm workingness --card"
    assert workingness["endpoint"] == "/workingness-card"
    assert workingness["full_endpoint"] == "/workingness"
    assert workingness["workingness_endpoint"] == "/workingness-card"
    assert workingness["workingness_drilldown_endpoint"] == "/workingness"
    assert (
        workingness["status_card_front_door_ref"]
        == "microcosm status --card <project>::front_door"
    )
    assert (
        workingness["status_card_route_explanation_ref"]
        == "microcosm status --card <project>::front_door.route_explanation"
    )
    assert (
        workingness["status_card_front_door_body_import_ref"]
        == "microcosm status --card <project>::front_door.source_open_body_import_floor"
    )
    assert (
        workingness["status_card_body_import_floor_ref"]
        == "microcosm status --card <project>::macro_body_import_floor"
    )
    assert workingness["tour_route_card_ref"] == (
        "microcosm tour <project>::route_cards_by_id.status_and_workingness"
    )
    assert workingness["tour_receipt_ref"] == (
        "receipts/runtime_shell/public_ten_minute_tour.json::"
        "route_cards_by_id.status_and_workingness"
    )
    assert (
        workingness["workingness_map_ref"]
        == "receipts/runtime_shell/workingness_failure_map.json"
    )
    assert "front_door.project_state_status" in workingness["expected_fields"]
    assert "front_door.selected_route_id" in workingness["expected_fields"]
    assert "front_door.route_explanation" in workingness["expected_fields"]
    assert (
        "front_door.route_explanation.reader_drilldowns"
        in workingness["expected_fields"]
    )
    assert (
        "front_door.observatory.project_observe_command"
        in workingness["expected_fields"]
    )
    assert "front_door.source_open_body_import_floor" in workingness["expected_fields"]
    assert (
        "front_door.source_open_body_import_floor.public_safe_body_material_count"
        in workingness["expected_fields"]
    )
    assert (
        "front_door.source_open_body_import_floor.public_safe_body_material_counts_by_class"
        in workingness["expected_fields"]
    )
    assert (
        "front_door.source_open_body_import_floor.direct_source_module_manifest_count"
        in workingness["expected_fields"]
    )
    assert (
        "front_door.source_open_body_import_floor.direct_source_module_manifest_material_count"
        in workingness["expected_fields"]
    )
    assert (
        "front_door.source_open_body_import_floor.latest_verified_source_module_family_ids"
        in workingness["expected_fields"]
    )
    assert (
        "front_door.source_open_body_import_floor.source_module_family_spotlights"
        in workingness["expected_fields"]
    )
    assert (
        "front_door.source_open_body_import_floor.body_text_exported_in_status"
        in workingness["expected_fields"]
    )
    assert (
        "front_door.source_open_body_import_floor.body_text_exported_in_receipts"
        in workingness["expected_fields"]
    )
    assert (
        "route_cards_by_id.status_and_workingness.source_open_body_import_floor"
        in workingness["expected_fields"]
    )
    assert (
        "route_cards_by_id.status_and_workingness.source_open_body_import_floor.latest_verified_source_module_family_ids"
        in workingness["expected_fields"]
    )
    assert (
        "route_cards_by_id.status_and_workingness.source_open_body_import_floor.source_module_family_spotlights"
        in workingness["expected_fields"]
    )
    assert "macro_body_import_floor.source_body_imports" in workingness["expected_fields"]
    assert "map_generation_status" in workingness["expected_fields"]
    assert "failure_envelope_status" in workingness["expected_fields"]
    assert "top_level_status_rule" in workingness["expected_fields"]
    assert "missing_standard_count" in workingness["expected_fields"]
    assert "missing_failure_modes_count" in workingness["expected_fields"]
    assert "gap_preview" in workingness["expected_fields"]
    assert workingness["safe_to_show"]["score_based_progress_authority"] is False
    assert workingness["safe_to_show"]["proof_correctness_claim"] is False
    assert workingness["safe_to_show"]["release_authorized"] is False
    assert workingness["safe_to_show"]["route_lineage_counts_visible"] is True
    assert workingness["safe_to_show"]["source_open_body_import_counts_visible"] is True
    assert workingness["safe_to_show"]["body_text_exported_in_status"] is False
    assert workingness["safe_to_show"]["body_text_exported_in_receipts"] is False
    assert workingness["status_card_command"] in entry_packet["allowed_drilldowns"]
    assert (
        workingness["status_card_front_door_ref"]
        in entry_packet["allowed_drilldowns"]
    )
    assert (
        workingness["status_card_route_explanation_ref"]
        in entry_packet["allowed_drilldowns"]
    )
    assert (
        workingness["status_card_front_door_body_import_ref"]
        in entry_packet["allowed_drilldowns"]
    )
    assert (
        workingness["status_card_body_import_floor_ref"]
        in entry_packet["allowed_drilldowns"]
    )
    assert workingness["workingness_command"] in entry_packet["allowed_drilldowns"]
    assert workingness["tour_route_card_ref"] in entry_packet["allowed_drilldowns"]
    assert workingness["tour_receipt_ref"] in entry_packet["allowed_drilldowns"]
    assert workingness["workingness_map_ref"] in entry_packet["allowed_drilldowns"]
    assert workingness["workingness_map_ref"] in entry_packet["receipt_dependencies"]

    doctrine_route = entry_packet["doctrine_navigation_route"]
    assert doctrine_route["surface_id"] == "microcosm_doctrine_navigation"
    assert doctrine_route["band_ladder"] == [
        "cluster_flag",
        "flag",
        "card",
        "source_receipt",
    ]
    assert "codex/doctrine/paper_modules/microcosm_substrate.md" in doctrine_route[
        "macro_doctrine_refs"
    ]
    assert "codex/standards/std_microcosm.json" in doctrine_route[
        "macro_doctrine_refs"
    ]
    assert "private_state_scan" not in entry_packet["receipt_dependencies"]


def test_public_entry_packet_routes_doctrine_lattice() -> None:
    entry_packet = json.loads(
        (MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8")
    )
    standard = json.loads(_macro_std_microcosm_path().read_text(encoding="utf-8"))

    lattice = entry_packet["doctrine_lattice_route"]
    standard_lattice = standard["doctrine_lattice"]
    assert lattice["surface_id"] == "microcosm_doctrine_lattice"
    assert standard_lattice["entry_surface"] == (
        "microcosm-substrate/atlas/entry_packet.json::doctrine_lattice_route"
    )
    assert standard_lattice["agent_entry_route"] == "sit_microcosm_public_substrate"
    assert lattice["band_ladder"] == [
        "cluster_flag",
        "flag",
        "card",
        "source_receipt",
    ]

    for field in [
        "principle_refs",
        "candidate_axiom_pressure_refs",
        "candidate_axiom_policy",
        "concept_refs",
        "mechanism_refs",
        "standard_refs",
        "paper_module_refs",
    ]:
        assert lattice[field] == standard_lattice[field]

    assert [row["kind"] for row in lattice["atlas_option_surfaces"]] == (
        standard_lattice["atlas_option_surfaces"]
    )
    validation_rule = standard["validation_rules"][0]
    assert validation_rule["id"] == "microcosm_doctrine_lattice_entry_packet_parity"
    assert validation_rule["fields"] == [
        "principle_refs",
        "candidate_axiom_pressure_refs",
        "candidate_axiom_policy",
        "concept_refs",
        "mechanism_refs",
        "standard_refs",
        "paper_module_refs",
        "atlas_option_surfaces",
    ]
    lattice_probe = (
        "PYTHONPATH=microcosm-substrate/src ./repo-pytest "
        "microcosm-substrate/tests/test_public_entry_docs.py::"
        "test_public_entry_packet_routes_doctrine_lattice -q"
    )
    assert standard["validation_probe"][0] == lattice_probe
    assert lattice_probe in standard["validation_probe"]
    assert "candidate-axiom promotion authority" in lattice["authority"]
    assert "candidate_axiom_promotion_authority" in standard_lattice["authority_ceiling"]


def test_public_entry_standard_names_degraded_kernel_fallback() -> None:
    standard = json.loads(_macro_std_microcosm_path().read_text(encoding="utf-8"))
    module_text = _macro_entry_lattice_path().read_text(encoding="utf-8")

    fallback = standard["first_screen_navigation_contract"][
        "degraded_kernel_fallback"
    ]
    assert fallback["trigger"] == (
        "macro_kernel_import_unavailable_due_to_unrelated_concurrent_source_dirt"
    )
    assert fallback["allowed_sources"] == [
        "codex/doctrine/paper_modules/_index.json",
        "codex/doctrine/paper_modules/_route_coverage.json",
        "codex/standards/std_microcosm.json",
        "microcosm-substrate/atlas/entry_packet.json",
        "codex/doctrine/paper_modules/microcosm_entry_lattice.md",
        "codex/doctrine/paper_modules/microcosm_substrate.md",
    ]
    assert fallback["required_actions"] == [
        "capture_import_or_same_path_blocker_before_user_facing_closeout",
        "avoid_unclaimed_source_repair_or_revert",
        "resume_kernel_proof_routes_after_owner_lane_restores_imports",
    ]
    assert fallback["forbidden_actions"] == [
        "repair_foreign_active_session_source_without_claim",
        "treat_sidecar_route_as_source_authority",
        "skip_validation_after_kernel_recovers",
    ]
    assert (
        fallback["authority_ceiling"]
        == "degraded_navigation_continuity_only_not_source_repair_release_provider_proof_or_candidate_axiom_authority"
    )

    validation_rule = next(
        rule
        for rule in standard["validation_rules"]
        if rule["id"] == "microcosm_degraded_kernel_fallback_boundary"
    )
    assert validation_rule["source_ref"] == (
        "codex/standards/std_microcosm.json::"
        "first_screen_navigation_contract.degraded_kernel_fallback"
    )
    assert validation_rule["fields"] == [
        "allowed_sources",
        "required_actions",
        "forbidden_actions",
        "authority_ceiling",
    ]
    assert "first_screen_navigation_contract.degraded_kernel_fallback" in module_text


def test_public_bridge_continuity_copy_uses_synthetic_transport_language() -> None:
    surfaces = {
        "README": MICROCOSM_ROOT / "README.md",
        "AGENTS": MICROCOSM_ROOT / "AGENTS.md",
        "paper module": MICROCOSM_ROOT / "paper_modules/bridge_phase_continuity_runtime.md",
        "standard": MICROCOSM_ROOT
        / "standards/std_microcosm_bridge_phase_continuity_runtime.json",
        "fixture manifest": MICROCOSM_ROOT
        / "core/fixture_manifests/bridge_phase_continuity_runtime.fixture_manifest.json",
        "organ registry": MICROCOSM_ROOT / "core/organ_registry.json",
        "evidence classes": MICROCOSM_ROOT / "core/organ_evidence_classes.json",
    }

    for label, path in surfaces.items():
        text = path.read_text(encoding="utf-8")
        assert "synthetic transport" in text or "synthetic-transport" in text, label
        assert "fake-transport" not in text, label
        assert "fake transport" not in text, label
