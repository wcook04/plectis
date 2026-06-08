"""Tests for specificity_v3: the anti-theater layer over real-coverage atoms.

Proves the lens distinguishes body-specific atoms (reference concrete behavior)
from generic-template atoms (the same boilerplate Guarantee/Fails repeated across
many symbols), flags authority-sensitive symbols missing Non-goal, and never
exports the docstring prose it inspects.
"""
from __future__ import annotations

import json
from pathlib import Path

from microcosm_core import project_substrate


# Body-specific: Guarantee/Fails name a concrete path, exception types, envelope.
BODY_SPECIFIC_MODULE = '''"""Module."""


def read_custody_manifest(path):
    """Read the custody manifest.

    - Teleology: load the declared custody manifest for the queue.
    - Guarantee: returns a dict parsed from core/organ_registry.json.
    - Fails: missing path -> raises OSError; malformed JSON -> ValueError.
    - Non-goal: does not authorize source-body export or release.
    """
    return {}
'''


# Template-generic: three symbols share an identical generic Guarantee/Fails.
GENERIC_TEMPLATE_MODULE = '''"""Module."""


def helper_one(value):
    """Helper.

    - Teleology: internal read-only helper.
    - Guarantee: returns a list of the projected values.
    - Fails: missing or malformed input does not raise.
    """
    return []


def helper_two(value):
    """Helper.

    - Teleology: internal read-only helper.
    - Guarantee: returns a list of the projected values.
    - Fails: missing or malformed input does not raise.
    """
    return []


def helper_three(value):
    """Helper.

    - Teleology: internal read-only helper.
    - Guarantee: returns a list of the projected values.
    - Fails: missing or malformed input does not raise.
    """
    return []
'''


# Authority-sensitive (validator name) carrying the triad but NO Non-goal.
VALIDATOR_NO_NONGOAL_MODULE = '''"""Module."""


def validate_release_claim(payload):
    """Validate a release claim.

    - Teleology: gate the public release claim.
    - Guarantee: returns {"ok": True} when the payload validates.
    - Fails: an invalid payload yields a blocked status.
    """
    return {"ok": True}
'''


def _spec_project(tmp_path: Path) -> Path:
    project = tmp_path / "spec_project"
    (project / "src/spec_app").mkdir(parents=True)
    (project / "README.md").write_text("# Spec\n", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        '[project]\nname = "spec-app"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    (project / "src/spec_app/__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (project / "src/spec_app/custody.py").write_text(BODY_SPECIFIC_MODULE, encoding="utf-8")
    (project / "src/spec_app/generic.py").write_text(GENERIC_TEMPLATE_MODULE, encoding="utf-8")
    (project / "src/spec_app/validator_gap.py").write_text(
        VALIDATOR_NO_NONGOAL_MODULE, encoding="utf-8"
    )
    return project


def test_specificity_v3_block_present_and_well_formed(tmp_path: Path) -> None:
    project = _spec_project(tmp_path)
    lens = project_substrate.python_lens(project, write_state=False)
    spec = lens["self_description_coverage"]["specificity_v3"]
    assert spec["schema_version"] == "microcosm_code_lens_specificity_v3"
    assert spec["source_bodies_exported"] is False
    bands = spec["bands"]
    # Bands partition the evaluated real-coverage symbols exactly.
    assert sum(bands.values()) == spec["evaluated_real_coverage_symbols"]
    assert set(bands) == {"body_specific", "generic_unique", "template_generic"}


def test_repeated_generic_atoms_are_template_generic(tmp_path: Path) -> None:
    project = _spec_project(tmp_path)
    lens = project_substrate.python_lens(project, write_state=False)
    spec = lens["self_description_coverage"]["specificity_v3"]
    # The three identical helper docstrings share one fingerprint over the dup
    # threshold -> classified template_generic, not real authored specificity.
    assert spec["bands"]["template_generic"] >= 3
    assert spec["max_fingerprint_repeat"] >= 3
    assert spec["template_fingerprint_count"] >= 1
    assert spec["template_generic_ratio"] > 0.0


def test_concrete_atoms_are_body_specific(tmp_path: Path) -> None:
    project = _spec_project(tmp_path)
    lens = project_substrate.python_lens(project, write_state=False)
    spec = lens["self_description_coverage"]["specificity_v3"]
    # read_custody_manifest + validate_release_claim reference paths/exceptions/
    # envelopes -> body_specific.
    assert spec["bands"]["body_specific"] >= 2


def test_authority_sensitive_missing_non_goal_flags_spot_review(tmp_path: Path) -> None:
    project = _spec_project(tmp_path)
    lens = project_substrate.python_lens(project, write_state=False)
    spec = lens["self_description_coverage"]["specificity_v3"]
    # validate_release_claim is validator-class, real-coverage, no Non-goal.
    assert spec["authority_sensitive_authored"] >= 1
    assert spec["needs_spot_review"] >= 1


def test_specificity_v3_never_exports_docstring_prose(tmp_path: Path) -> None:
    project = _spec_project(tmp_path)
    lens = project_substrate.python_lens(project, write_state=False)
    blob = json.dumps(lens)
    # Distinctive prose from the fixtures must never appear anywhere in the lens.
    assert "returns a list of the projected values" not in blob
    assert "load the declared custody manifest" not in blob


def test_specificity_v3_summary_on_compact_card(tmp_path: Path) -> None:
    project = _spec_project(tmp_path)
    lens = project_substrate.python_lens(project, write_state=False)
    card = project_substrate._self_description_coverage_card(
        lens["self_description_coverage"]
    )
    assert "specificity_v3" in card
    assert "bands" in card["specificity_v3"]
    assert "template_generic_ratio" in card["specificity_v3"]
