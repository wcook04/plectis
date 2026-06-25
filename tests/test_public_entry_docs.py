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
    shutil.copy2(MICROCOSM_ROOT / "AGENT_ROUTES.md", public_root / "AGENT_ROUTES.md")
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
        "Plectis smoke check: pass",
        "authority: pass",
        "workingness: clear",
        "served status: pass",
        "plectis hello .",
        "plectis hello --reader cold_cloner .",
        "plectis hello --reader reviewer .",
        "plectis hello --reader skeptical_reviewer .",
        "plectis hello --reader agent .",
        "plectis hello --reader domain_specialist .",
        "`cold_cloner` / `cold-cloner` maps to the public GitHub visitor branch",
        "`skeptical_reviewer` / `skeptical-reviewer` / `reviewer` maps to the safety/evals branch",
        "and `agent` / `type-a-agent` maps to the",
        "repo-reading agent branch",
        "`domain_specialist` / `domain-specialist` is the specialty",
        "ORGANS.md#find-your-specialty",
        "not an expert-review or\ndomain-correctness claim",
        "plectis tour --card .",
        "plectis status --card .",
        "plectis authority --card",
        "plectis workingness --card",
        "plectis legibility-scorecard",
        "If you are staying source-only",
        "PYTHONPATH=src python3 -m microcosm_core tour --card .",
        "PYTHONPATH=src python3 -m microcosm_core status --card .",
        "PYTHONPATH=src python3 -m microcosm_core authority --card",
        "PYTHONPATH=src python3 -m microcosm_core workingness --card",
        "PYTHONPATH=src python3 -m microcosm_core legibility-scorecard",
        "plectis serve . --host 127.0.0.1 --port 8765 --max-requests 7",
        "/project/observatory-card",
        "/workingness-card",
        "Open `/workingness` only when you need the full per-organ failure-envelope map.",
        "make check",
        "Plectis preflight: organ evidence-class registry loads\ncleanly.",
        "make ci",
        "For a cold clone, treat `make ci` as the public green floor.",
        "`make validate`\nadds the doctrine-lattice drift check",
        "maintainer pre-commit gate",
        "not a broader release, proof-correctness, or production claim",
        "make package-smoke",
        "package-install smoke",
        "make standalone-export EXPORT_OUT=/tmp/plectis-export",
        "receipts/release/release_export_receipt.json",
        "cd /tmp/plectis-export/plectis",
        "validate the exported artifact as its own clone",
        "release_authorized=false",
        "provider calls",
        "source mutation",
        "private-root equivalence",
        "Receipts are drilldown evidence",
        "plectis evidence list . --limit 25",
        "plectis evidence inspect . .microcosm/evidence/routes.json",
        "plectis evidence inspect --project . .microcosm/evidence/routes.json",
        "PYTHONPATH=src python3 -m microcosm_core evidence list . --limit 25",
        "PYTHONPATH=src python3 -m microcosm_core evidence inspect . .microcosm/evidence/routes.json",
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
    normalized_agents = " ".join(agents.split())

    for phrase in (
        "not a production security product",
        "./bootstrap.sh",
        "./bootstrap.sh --dry-run",
        "ignored `.microcosm/cold_clone_probe.json` evidence",
        "plectis authority --card",
        "plectis stripping-guard",
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
    assert security.index("./bootstrap.sh") < security.index("make install")

    for phrase in (
        "make install",
        "./bootstrap.sh",
        "./bootstrap.sh --dry-run",
        "make smoke",
        "make package-smoke",
        "make ci",
        ".microcosm/smoke/",
        "make standalone-export EXPORT_OUT=/tmp/plectis-export",
        "receipts/release/release_export_receipt.json",
        "cd /tmp/plectis-export/plectis",
        "validate it from inside the exported artifact",
        "release_authorized=false",
        "plectis hello .",
        "plectis tour --card .",
        "plectis status --card .",
        "plectis authority --card",
        "plectis workingness --card",
        "plectis legibility-scorecard",
        "PYTHONPATH=src python3 -m microcosm_core hello .",
        "real non-secret macro bodies",
        "fake progress",
        "tests/test_public_entry_docs.py",
        "ignored `.microcosm/cold_clone_probe.json` evidence",
    ):
        assert phrase in contributing
    assert "without dumping the full cards into CI logs" in normalized_contributing
    assert contributing.index("./bootstrap.sh") < contributing.index("make smoke")

    for forbidden in (
        "--emit receipts/cold_clone_probe.json",
        "--emit receipts/cold_clone_probe_local.json",
    ):
        assert forbidden not in security
        assert forbidden not in contributing
        assert forbidden not in agents

    for phrase in (
        "./bootstrap.sh",
        "./bootstrap.sh --dry-run",
        "make install",
        "make smoke",
        "make check",
        "make ci",
        "Plectis preflight: organ evidence-class registry loads\ncleanly.",
        "package-install smoke",
        "make standalone-export EXPORT_OUT=/tmp/plectis-export",
        "receipts/release/release_export_receipt.json",
        "cd /tmp/plectis-export/plectis",
        "cold-clone check proves the exported package can install",
        "release_authorized=false",
        "plectis hello .",
        "plectis hello --reader cold_cloner .",
        "plectis hello --reader reviewer .",
        "plectis hello --reader skeptical_reviewer .",
        "plectis hello --reader agent .",
        "plectis hello --reader domain_specialist .",
        "`cold_cloner` / `cold-cloner` maps to the public GitHub visitor branch",
        "`skeptical_reviewer` / `skeptical-reviewer` / `reviewer` maps to the safety/evals branch",
        "and `agent` / `type-a-agent` maps to the",
        "repo-reading agent branch",
        "`domain_specialist` / `domain-specialist` is the specialty",
        "generated organ specialty index",
        "without claiming domain\ncorrectness or expert review",
        "plectis tour --card .",
        "plectis status --card .",
        "plectis authority --card",
        "plectis workingness --card",
        "plectis legibility-scorecard",
        "PYTHONPATH=src python3 -m microcosm_core <command>",
        "public GitHub Actions entry",
        "Do not launch multiple raw `pytest` processes",
        "uses its own `--basetemp`",
        ".microcosm/test-tmp/pytest",
    ):
        assert phrase in agents
    assert "ignored `.microcosm/cold_clone_probe.json` evidence" in normalized_agents
    assert agents.index("./bootstrap.sh") < agents.index("make install")


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
    assert receipt["hardcoded_numeric_organ_count_claims"] == {}
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
    agent_routes = receipt["agent_task_route_projection"]
    assert agent_routes["status"] == "pass"
    assert agent_routes["source_ref"] == "atlas/agent_task_routes.json"
    assert agent_routes["markdown_ref"] == "AGENT_ROUTES.md"
    assert agent_routes["route_count"] == agent_routes["declared_route_count"]
    assert agent_routes["missing_organs"] == []
    assert agent_routes["unexpected_organs"] == []
    assert agent_routes["duplicate_task_classes"] == []
    assert agent_routes["incomplete_routes"] == []
    assert agent_routes["markdown_missing"] == []
    assert agent_routes["doc_deferral_missing"] == []
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
    assert route_contract["first_command"] == "plectis tour --card <project>"
    assert route_contract["primary_first_screen_command"] == (
        "plectis tour --card <project>"
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
        "plectis tour --card <project>",
        "plectis status --card <project>",
        "plectis workingness --card",
        "plectis proof-lab --out /tmp/microcosm-proof-lab",
        "plectis serve <project>",
        "plectis compile <project>",
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
    assert receipt["entry_spine_claims"]["docs"]["AGENTS.md"]["missing_organs"] == (
        _accepted_organs_from_registry()
    )


def test_public_entry_docs_accepts_registry_routed_spine_without_full_inline_inventory(
    tmp_path: Path,
) -> None:
    public_root = _copy_public_entry_tree(tmp_path)
    agents = public_root / "AGENTS.md"
    # The human-front-door README is inherently registry_route after the
    # assurance migration (it names the registries and the inventory-only
    # posture, and never inline-enumerates organs), so it needs no mutation to
    # exercise registry_route mode. This test now drives the AGENTS.md
    # registry_route path explicitly.
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
                "Use [AGENT_ROUTES.md](AGENT_ROUTES.md), "
                "[ORGANS.md#find-your-specialty](ORGANS.md#find-your-specialty), "
                "[ORGANS.md](ORGANS.md), and [ARCHITECTURE.md](ARCHITECTURE.md). "
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


def test_public_entry_docs_block_hardcoded_numeric_organ_count_claim(
    tmp_path: Path,
) -> None:
    public_root = _copy_public_entry_tree(tmp_path)
    readme = public_root / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8")
        + "\nThe public package carries 1 accepted public runtime organs today.\n",
        encoding="utf-8",
    )

    receipt = validate_public_entry_docs(
        public_root,
        public_root / "receipts/first_wave/public_entry_docs_validation.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert "HARDCODED_PUBLIC_ENTRY_ORGAN_COUNT" in receipt["blocking_codes"]
    assert receipt["hardcoded_numeric_organ_count_claims"] == {
        "README.md": [
            "1 accepted public runtime organs",
            "public package carries 1 accepted public runtime organs",
        ],
    }


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


def test_public_entry_docs_block_legacy_name_as_current_product_label(
    tmp_path: Path,
) -> None:
    public_root = _copy_public_entry_tree(tmp_path)
    routes = public_root / "AGENT_ROUTES.md"
    routes.write_text(
        "# Microcosm Agent Task Routes\n\nMicrocosm is a local product.\n",
        encoding="utf-8",
    )

    receipt = validate_public_entry_docs(
        public_root,
        public_root / "receipts/first_wave/public_entry_docs_validation.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert "PUBLIC_LEGACY_PRODUCT_NAME" in receipt["blocking_codes"]
    assert receipt["legacy_public_product_name_hits"]["AGENT_ROUTES.md"] == [
        "# Microcosm",
        "Microcosm Agent Task Routes",
        "Microcosm is a",
    ]


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
        "plectis status --card <project>"
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
    ] == ["plectis status --card <project>"]
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


def test_public_entry_docs_readme_route_selection_is_not_prose_pinned(
    tmp_path: Path,
) -> None:
    # Migrated from test_public_entry_docs_block_readme_route_selection_truth_drift
    # (assurance-preserving projection migration, 2026-06-22). The route-selection
    # TRUTH is owned by atlas/entry_packet.json::route_selection_rule and
    # skills/cold_start_navigation.md, each with its own drift test
    # (test_public_entry_docs_block_entry_packet_route_selection_truth_drift,
    # test_public_entry_docs_block_cold_start_route_selection_truth_drift). The
    # human-front-door README no longer restates route IDs in prose, so the
    # validator must NOT block on README route-selection wording: this guard
    # proves the README is not prose-pinned for route selection.
    public_root = _copy_public_entry_tree(tmp_path)
    readme = public_root / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            "selected_route_id",
            "selected route handle",
        ),
        encoding="utf-8",
    )

    receipt = validate_public_entry_docs(
        public_root,
        public_root / "receipts/first_wave/public_entry_docs_validation.json",
        command="pytest",
    )

    route_contract = receipt["entry_packet_route_contract"]
    assert route_contract["readme_route_selection_missing_phrases"] == []
    assert (
        "readme_route_selection_rule_missing"
        not in route_contract["blocking_reasons"]
    )


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
        "  plectis status --card <project> read the compressed "
        "project/runtime status lens\n"
        "  plectis status-card <project> alias for the compact status lens\n"
        "  plectis spine --card          read the compact runtime spine lens\n"
        "  plectis run --card examples/runtime_shell/demo_project "
        "replay the public runtime demo\n"
        "  plectis authority --card      read the compact authority ceiling lens\n"
        "  plectis intake --card         read the compact intake/projection bridge lens\n"
        "  plectis workingness --card    read the compact behavior/failure "
        "lens\n"
        "  plectis workingness           inspect behavior evidence "
        "and failure gaps\n"
    )
    assert expected_help_block in original
    mutated_help_block = (
        "  plectis workingness --card    read the compact behavior/failure "
        "lens\n"
        "  plectis workingness           inspect behavior evidence "
        "and failure gaps\n"
        "  plectis status --card <project> read the compressed "
        "project/runtime status lens\n"
        "  plectis status-card <project> alias for the compact status lens\n"
        "  plectis spine --card          read the compact runtime spine lens\n"
        "  plectis run --card examples/runtime_shell/demo_project "
        "replay the public runtime demo\n"
        "  plectis authority --card      read the compact authority ceiling lens\n"
        "  plectis intake --card         read the compact intake/projection bridge lens\n"
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
        "plectis status --card <project> before plectis workingness --card"
    ]
    assert help_contract["blocking_reasons"] == ["help_command_order_mismatch"]


def test_public_entry_readme_no_longer_claims_first_slice_only() -> None:
    # Assurance-preserving projection migration (2026-06-22). The README is the
    # human front door, judged structurally + by projection binding (see
    # validators/readme_front_door.py and tests/test_readme_front_door.py), not
    # by exact prose. The README assertions below are the constitutional-TRUTH
    # subset that survived: the rename/compatibility fact, the registry-route
    # inventory posture, the bounded-claim anti-claims, the agent first-action
    # product, and negative guards against stale macro framing. The incidental
    # layout pins (startswith, exact section names, exact table rows, exact
    # phrase positions, the route-ID prose) were retired; their intent moved to
    # the binding validator and the registries. AGENTS.md (agent-facing) keeps
    # all of its own pins unchanged.
    text = (MICROCOSM_ROOT / "README.md").read_text(encoding="utf-8")
    agents = (MICROCOSM_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())
    normalized_agents = " ".join(agents.split())
    expected_organs = _accepted_organs_from_registry()

    # --- README: constitutional truth (projection-free) ---
    # A single H1 and a banner; the banner may precede the H1 (it does), so
    # this is a presence check, not startswith.
    assert "# Plectis" in text
    assert "<img" in text and "alt=" in text
    # Rename / compatibility lineage fact stays available to the human reader.
    assert "Microcosm became Plectis" in text
    assert (
        "Microcosm remains only where compatibility or historical continuity requires it"
        in normalized_text
    )
    assert "Microcosm is the public repo form of the macro system" not in text
    # Registry-route inventory posture: the registries own the inventory; the
    # human README only routes to them in plain English and states the boundary.
    # The raw JSON paths / status-enum / field-name tokens were retired from
    # human prose (their truth is enforced independently by the registries
    # themselves), so the README now passes the registry-route gate via its
    # human links to the generated System map and Release review.
    assert "[System map](ORGANS.md)" in text
    assert "[Release review](RELEASE_REVIEW.md)" in text
    assert (
        "generated from the repository's governed component records"
        in normalized_text
    )
    assert "not a quality or progress score" in normalized_text
    # Bounded-claim truth: anti-claims present, witness reports no source mutation.
    assert "executable research prototype" in normalized_text
    assert "source_files_mutated" in text
    assert "repo -> .microcosm" in text
    for anti_claim in (
        "release",
        "hosting",
        "provider calls",
        "source mutation",
        "not a copy of any private system",
        "proof authority",
    ):
        assert anti_claim in normalized_text, anti_claim
    # The agent first-action product is reachable from the human front door.
    assert "comprehend --first-action" in text
    # Negative guards: no stale macro / reconstruction / false-coverage framing.
    assert "public-safe ten-minute path" not in normalized_text
    assert "public-safe authority ceiling" not in normalized_text
    assert "runnable, synthetic, and receipt-driven" not in text
    assert "public synthetic microcosm" not in text
    assert "private reconstruction control plane" not in text
    assert "only implemented organ here is `pattern_binding_contract`" not in text

    # --- AGENTS.md: agent-facing spine pins (unchanged) ---
    assert agents.startswith("# AGENTS.md - Plectis")
    assert "Microcosm is the public repo form of the macro system" not in agents
    assert "Accepted Public Runtime Spine" in agents
    assert "Real Substrate Posture" in agents
    assert "public entry inventory" in agents
    assert "inventory-only route-alignment metadata" in normalized_agents
    assert "not product progress, release readiness" in agents
    assert "[AGENT_ROUTES.md](AGENT_ROUTES.md)" in agents
    assert "[ORGANS.md#find-your-specialty](ORGANS.md#find-your-specialty)" in agents
    assert "Plectis is the public repo form of the macro system" in agents
    assert "not a synthetic safety proxy" in agents
    assert "Public should carry private by default" in agents
    assert "as much of the macro substrate as possible" in normalized_agents
    assert "The hard exclusion set is narrow" in agents
    assert "raw operator voice, slurs or abusive wording" in normalized_agents
    assert "Any `body_copied=true` claim must point at a real target file" in agents
    assert "not benchmark scores" in agents
    assert "not score-based progress" in agents
    assert "public-safe route" not in normalized_agents
    assert "only to project metadata" not in normalized_agents
    assert "only implemented organ here is `pattern_binding_contract`" not in agents
    assert len(expected_organs) > 1
    assert "pattern_binding_contract" in expected_organs
    assert "bridge_phase_continuity_runtime" in expected_organs
    assert "core/organ_registry.json" in agents
    assert "core/organ_evidence_classes.json" in agents
    assert "AGENT_ROUTES.md" in agents
    assert "plectis reveal" in agents
    assert "spatial-simulation" in agents
    assert "plectis tour --card <project>" in agents
    assert agents.index("plectis tour --card <project>") < agents.index(
        "plectis tour <project>"
    )
    assert "Do not widen Lean/Lake" in agents
    assert "Do not treat prediction fixtures as trading or financial advice" in agents
    assert "source reconstruction workspace" not in agents
    assert "Use only synthetic fixtures" not in agents
    assert "Receipts Are Authority" not in agents
    assert "macro reconstruction contracts" not in agents
    assert "executable research prototype" in normalized_agents
    assert "local project operating substrate" in normalized_agents
    assert "plectis compile <project>" in agents
    assert "repo -> `.microcosm`" in agents
    assert "Fixtures Are Tests" in agents
    assert "Receipts Are Evidence" in agents
    assert "evidence_class" in agents
    assert (
        "`accepted_current_authority` is not an evidence-strength claim"
        in normalized_agents
    )


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
    cold_clone_module = (
        MICROCOSM_ROOT / "paper_modules/cold_clone_probe.md"
    ).read_text(encoding="utf-8")
    normalized_cold_start = " ".join(cold_start.split())
    assert "std_python_microcosm_navigation_assay" in cold_start
    assert "implementation_atlas.python_navigation_assay" in cold_start
    assert "route_utility_curriculum" in cold_start
    assert "route_utility_curriculum.ratchet" in cold_start
    assert "./bootstrap.sh" in cold_start
    assert "./bootstrap.sh --dry-run" in cold_start
    assert "--emit receipts/cold_clone_probe.json" not in cold_start
    assert ".microcosm/cold_clone_probe.json" in cold_start
    assert "card echoes the requested alias or route id" in cold_start
    assert "card prints the canonical follow-up command" not in cold_start
    assert "Source-Root Probe" in cold_start
    assert "before install" in cold_start
    assert "after first-screen behavior is visible" not in cold_start
    assert "Run `./bootstrap.sh` from the public root." in cold_clone_module
    assert "ignored `.microcosm/cold_clone_probe.json` evidence" in cold_clone_module
    assert "--emit receipts/cold_clone_probe.json" not in cold_clone_module
    assert not (MICROCOSM_ROOT / "receipts/cold_clone_probe.json").exists()
    assert "proof-lab --out /tmp/microcosm-proof-lab" in cold_start
    assert "verifier-lab-kernel run-kernel-bundle" in cold_start
    assert "formal_prover_context_strategy_gate" in cold_start
    assert "First-Screen Route Contract" in cold_start
    assert "Bring a folder after the source-root probe" in cold_start
    assert "route_cards_by_id.status_and_workingness" in cold_start
    assert "plectis evidence list <project> --limit 25" in cold_start
    assert "plectis evidence inspect <project> <ref>" in cold_start
    assert "plectis status --card <project>" in cold_start
    assert "`cold_cloner` maps to `public_github_visitor`" in cold_start
    assert "`interesting_parts` / `interesting-parts` maps to that same public visitor" in cold_start
    assert "`skeptical_reviewer` maps to `safety_evals_engineer`" in normalized_cold_start
    assert "and `agent` maps to" in cold_start
    assert "`type_a_agent`" in cold_start
    assert "six cold reader branches" in normalized_cold_start
    assert "Domain specialist: run" in cold_start
    assert "plectis hello --reader domain_specialist <project>" in cold_start
    assert "ORGANS.md#find-your-specialty" in cold_start
    assert (
        "explicit non-claim of domain correctness or expert review"
        in normalized_cold_start
    )
    assert "not new routes" in normalized_cold_start
    assert "front_door.route_explanation" in cold_start
    assert "plectis workingness" in cold_start
    assert (
        "plectis serve <project> --host 127.0.0.1 --port 8765" in cold_start
    )
    assert (
        "plectis serve <project> --host 127.0.0.1 --port 8765 --max-requests 7"
        in cold_start
    )
    assert (
        "PYTHONPATH=src python3 -m microcosm_core serve <project> --host "
        "127.0.0.1 --port 8765 --max-requests 7"
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
    assert "make standalone-export EXPORT_OUT=/tmp/plectis-export" in cold_start
    assert "cd /tmp/plectis-export/plectis" in cold_start
    assert "cold-clone check proves the exported artifact can install" in cold_start
    assert "receipts/release/release_export_receipt.json" in cold_start
    assert "release_authorized=false" in cold_start


def test_public_entry_docs_keep_tour_before_compile() -> None:
    # The tour-before-compile TRUTH is owned by its machine contracts, not by
    # README prose (assurance-preserving projection migration, 2026-06-22):
    #   - atlas/entry_packet.json::first_command and local_first_screen_route
    #     command order (asserted here and in the entry-packet route tests),
    #   - src/microcosm_core/cli.py::FIRST_SCREEN_HELP order
    #     (test_public_entry_docs_block_cli_first_screen_help_drift),
    #   - skills/cold_start_navigation.md ordering (asserted below).
    # The README is the human front door and no longer restates the full
    # command catalogue / "First Run" walkthrough; it routes to QUICKSTART.md
    # and the generated ORGANS.md / CLI help for the exhaustive command set.
    entry_packet = json.loads(
        (MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8")
    )
    assert entry_packet["first_command"] == "plectis tour --card <project>"
    command_path = entry_packet["local_first_screen_route"]["command_path"]
    assert command_path.index("plectis tour --card <project>") < command_path.index(
        "plectis compile <project>"
    )

    cold_start = (MICROCOSM_ROOT / "skills/cold_start_navigation.md").read_text(
        encoding="utf-8"
    )
    assert cold_start.index("Run `plectis tour --card <project>`") < cold_start.index(
        "Run `plectis compile <project>`"
    )
    assert cold_start.index(
        "Open `atlas/entry_packet.json::status_and_workingness_route`"
    ) < cold_start.index(
        "Run `plectis compile <project>`"
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
    assert entry_packet["first_command"] == "plectis tour --card <project>"
    assert route["surface_id"] == "microcosm_local_first_screen"
    assert route["primary_first_screen_command"] == "plectis tour --card <project>"
    assert route["primary_first_screen_command"] == entry_packet["first_command"]
    assert route["command_path"][:6] == [
        "plectis tour --card <project>",
        "plectis status --card <project>",
        "plectis workingness --card",
        "plectis proof-lab --out /tmp/microcosm-proof-lab",
        "plectis observe --card <project>",
        "plectis serve <project> --host 127.0.0.1 --port 8765",
    ]
    assert (
        "plectis serve <project> --host 127.0.0.1 --port 8765 --max-requests 7"
        in route["command_path"]
    )
    assert route["command_path"].index(
        "plectis status --card <project>"
    ) < route["command_path"].index("plectis compile <project>")
    assert route["command_path"].index(
        "plectis proof-lab --out /tmp/microcosm-proof-lab"
    ) < route["command_path"].index("plectis python-lens <project>")
    assert "plectis python-lens <project>" in route["command_path"]
    assert (
        "plectis explain <project> <selected_route_id>"
        in route["command_path"]
    )
    assert route["selected_route_id_source"] == (
        "plectis tour --card <project>::selected_route_id or "
        "plectis tour <project>::selected_route_id or "
        "plectis tour <project>::first_screen.selected_route_id or "
        "plectis compile <project>::selected_route_id"
    )
    assert "readme_onboarding_route is a generated route only" in route[
        "route_selection_rule"
    ]
    assert "plectis evidence list <project> --limit 25" in route["command_path"]
    assert "plectis evidence inspect <project> <ref>" in route["command_path"]
    assert "plectis status --card <project>" in route["command_path"]
    assert "plectis workingness --card" in route["command_path"]
    assert "plectis proof-lab --out /tmp/microcosm-proof-lab" in route[
        "command_path"
    ]
    assert "plectis observe --card <project>" in route["command_path"]
    assert "plectis observe <project>" in entry_packet["allowed_drilldowns"]
    assert route["reader_routes_ref"] == (
        "atlas/entry_packet.json::reader_first_screen_routes"
    )
    assert route["reader_route_ids"] == [
        "public_github_visitor",
        "safety_evals_engineer",
        "hiring_reviewer",
        "peer_developer",
        "domain_specialist",
        "type_a_agent",
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
        "plectis tour --card <project>"
    )
    rows = {row["reader_id"]: row for row in reader_routes["routes"]}
    assert set(rows) == {
        "public_github_visitor",
        "safety_evals_engineer",
        "hiring_reviewer",
        "peer_developer",
        "domain_specialist",
        "type_a_agent",
    }
    assert rows["public_github_visitor"]["first_screen_command"] == (
        "plectis hello <project>"
    )
    assert rows["public_github_visitor"]["next_command"] == (
        "plectis tour --card <project>"
    )
    assert rows["safety_evals_engineer"]["first_screen_command"] == (
        "plectis status --card <project>"
    )
    assert rows["hiring_reviewer"]["first_screen_command"] == (
        "plectis legibility-scorecard"
    )
    assert rows["peer_developer"]["next_command"] == (
        "plectis observe --card <project>"
    )
    assert rows["peer_developer"]["followup_command"] == "plectis observe <project>"
    assert rows["domain_specialist"]["next_command"] == (
        "ORGANS.md#find-your-specialty"
    )
    assert rows["domain_specialist"]["followup_command"] == (
        "plectis tour --card <project>"
    )
    assert "domain correctness" in rows["domain_specialist"]["anti_misread"]
    assert rows["type_a_agent"]["first_screen_command"] == (
        "plectis first-screen --card <project>"
    )
    assert rows["type_a_agent"]["next_command"] == (
        "plectis organ-surface-contract --card --root ."
    )
    assert rows["type_a_agent"]["followup_command"] == (
        "AGENTS.md::Concept And Mechanism Entry"
    )
    assert "source mutation" in rows["type_a_agent"]["anti_misread"]
    assert "maturity score" in rows["safety_evals_engineer"]["anti_misread"]


def test_cold_reader_route_map_names_compact_path_before_drilldowns() -> None:
    route_map = (
        MICROCOSM_ROOT / "paper_modules/cold_reader_route_map.md"
    ).read_text(encoding="utf-8")
    accepted_path = route_map.split("The accepted path is:", 1)[1].split(
        "Full drilldowns stay available", 1
    )[0]
    compact_commands = [
        "plectis hello <project>",
        "plectis tour --card <project>",
        "plectis status --card <project>",
        "plectis authority --card",
        "plectis workingness --card",
        "plectis legibility-scorecard",
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
        "plectis tour <project>",
        "plectis compile <project>",
        "plectis proof-lab --out /tmp/microcosm-proof-lab",
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
    assert route["command"] == "plectis python-lens <project>"
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
    assert proof_lab["command"] == "plectis proof-lab --out /tmp/microcosm-proof-lab"
    assert proof_lab["expanded_command"] == (
        "plectis verifier-lab-kernel run-kernel-bundle --input "
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
    assert front_door["command"] == "plectis tour <project>"
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
    assert recovery_route["command"] == "plectis status --card <project>"
    assert recovery_route["recovery_ref"] in entry_packet["allowed_drilldowns"]
    assert recovery_route["blocking_detail_ref"] in entry_packet["allowed_drilldowns"]
    assert recovery_route["expected_blocked_state"] == {
        "status": "blocked",
        "project_state_status": "missing_state",
        "primary_recovery_command": "plectis tour --card <project>",
        "status_after_recovery_command": "plectis status --card <project>",
        "alternate_recovery_command": "plectis compile <project>",
    }
    assert recovery_route["safe_to_show"]["recovery_command_visible"] is True
    assert recovery_route["safe_to_show"]["source_files_mutated"] is False
    assert recovery_route["safe_to_show"]["provider_calls_authorized"] is False

    workingness = entry_packet["status_and_workingness_route"]
    assert workingness["surface_id"] == "microcosm_status_and_workingness"
    assert workingness["command"] == "plectis status --card <project>"
    assert workingness["next_command"] == "plectis workingness --card"
    assert workingness["status_card_command"] == "plectis status --card <project>"
    assert workingness["workingness_command"] == "plectis workingness --card"
    assert workingness["endpoint"] == "/workingness-card"
    assert workingness["full_endpoint"] == "/workingness"
    assert workingness["workingness_endpoint"] == "/workingness-card"
    assert workingness["workingness_drilldown_endpoint"] == "/workingness"
    assert (
        workingness["status_card_front_door_ref"]
        == "plectis status --card <project>::front_door"
    )
    assert (
        workingness["status_card_route_explanation_ref"]
        == "plectis status --card <project>::front_door.route_explanation"
    )
    assert (
        workingness["status_card_front_door_body_import_ref"]
        == "plectis status --card <project>::front_door.source_open_body_import_floor"
    )
    assert (
        workingness["status_card_body_import_floor_ref"]
        == "plectis status --card <project>::macro_body_import_floor"
    )
    assert workingness["tour_route_card_ref"] == (
        "plectis tour <project>::route_cards_by_id.status_and_workingness"
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
    assert "codex/doctrine/paper_modules/plectis_substrate.md" in doctrine_route[
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
    # README is the human front door and no longer carries bridge-subsystem
    # terminology (assurance-preserving projection migration, 2026-06-22). The
    # "synthetic transport" (never "fake transport") terminology truth stays
    # enforced on the six canonical owners below that actually discuss the
    # bridge: AGENTS.md, the bridge paper module, its standard, its fixture
    # manifest, the organ registry, and the evidence-class registry.
    surfaces = {
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


def test_entry_surfaces_converge_on_first_action_product() -> None:
    """Every cold-entry route must teach the same goal-shaped product, and no
    surface may label a different command as the "First action".

    The product center is `comprehend --first-action`: README, QUICKSTART,
    AGENTS, the three provider adapters, the CLI first screen, and the rendered
    hello card must all carry it; the reader-route ladder uses the
    "First step:" label so the encounter never teaches two first actions.
    """
    product_command = "comprehend --first-action"

    for label, rel in (
        ("README", "README.md"),
        ("QUICKSTART", "QUICKSTART.md"),
        ("AGENTS", "AGENTS.md"),
        ("CLAUDE adapter", "CLAUDE.md"),
        ("CODEX adapter", "CODEX.md"),
        ("CURSOR adapter", "CURSOR.md"),
        ("first-action demonstration", "FIRST_ACTION.md"),
        ("agent task-route selector", "AGENT_ROUTES.md"),
    ):
        text = (MICROCOSM_ROOT / rel).read_text(encoding="utf-8")
        assert product_command in text, label

    # Lead position, not just presence: QUICKSTART teaches the goal-shaped
    # move before its first numbered orientation step, and each provider
    # adapter carries it on the first screenful.
    quickstart = (MICROCOSM_ROOT / "QUICKSTART.md").read_text(encoding="utf-8")
    assert quickstart.index(product_command) < quickstart.index("## 0.")
    # The task-route selector teaches the goal conversion in its preamble,
    # before the per-task-class table starts.
    agent_routes = (MICROCOSM_ROOT / "AGENT_ROUTES.md").read_text(encoding="utf-8")
    assert agent_routes.index(product_command) < agent_routes.index(
        "## Agent Task Route Table"
    )
    for rel in ("CLAUDE.md", "CODEX.md", "CURSOR.md"):
        adapter_head = "\n".join(
            (MICROCOSM_ROOT / rel).read_text(encoding="utf-8").splitlines()[:12]
        )
        assert product_command in adapter_head, rel

    # The hello card's omission receipt routes readers to the composition
    # paper module; that module must not teach a second "First action" either.
    composition_module = (
        MICROCOSM_ROOT / "paper_modules/first_screen_composition_root.md"
    ).read_text(encoding="utf-8")
    assert "First action:" not in composition_module
    assert product_command in composition_module

    import importlib

    cli = importlib.import_module("microcosm_core.cli")
    help_text = str(cli.FIRST_SCREEN_HELP)
    assert product_command in help_text
    # The goal-shaped move leads the command help: nothing is taught before it.
    assert help_text.index(product_command) < help_text.index("hello")

    composition = importlib.import_module("microcosm_core.first_screen_composition")
    card = composition.first_screen_composition_card(MICROCOSM_ROOT, project_label=".")
    hello_text = composition.first_screen_text_card(card)
    assert 'Have a goal? plectis comprehend --first-action "<your goal>"' in hello_text
    # The goal line must LEAD the card (line 2, directly under the title), not
    # trail it: position is the product here, presence alone can be demoted.
    assert hello_text.splitlines()[1].startswith("Have a goal? ")
    # The retired label must not reappear on the reader ladder: the route
    # ladder teaches steps, the product owns "first action".
    assert "First action:" not in hello_text
    agent_text = composition.first_screen_text_card(card, reader_id="type_a_agent")
    assert "First action:" not in agent_text
    assert "First step:" in agent_text
