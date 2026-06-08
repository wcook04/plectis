"""Tests for the code-lens join index v0 builder.

Proves the builder joins organs to runner source files + receipts, rolls up
per-organ specificity, classifies runner custody, refuses a source-body-leaking
lens snapshot, and never emits docstring prose.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


_SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "build_code_lens_join_index.py"
)
_spec = importlib.util.spec_from_file_location("build_code_lens_join_index", _SCRIPT)
assert _spec and _spec.loader
build_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_mod)


def _lens() -> dict:
    return {
        "payload_boundary": {"source_bodies_exported": False},
        "symbol_capsule_rows": [
            {
                "path": "src/microcosm_core/organs/foo.py",
                "symbol_name": "run_work",
                "is_real_coverage": True,
                "atom_specificity": "body_specific",
                "atom_has_non_goal": True,
                "source_class": "source_module",
            },
            {
                "path": "src/microcosm_core/organs/foo.py",
                "symbol_name": "helper",
                "is_real_coverage": False,
                "atom_specificity": "not_applicable",
                "atom_has_non_goal": False,
                "source_class": "source_module",
            },
            {
                "path": "src/microcosm_core/validators/bar.py",
                "symbol_name": "validate_bar",
                "is_real_coverage": True,
                "atom_specificity": "generic_unique",
                "atom_has_non_goal": False,
                "source_class": "source_module",
            },
        ],
    }


def _registry() -> dict:
    return {
        "implemented_organs": [
            {
                "organ_id": "foo",
                "runner": "microcosm_core.organs.foo",
                "evidence_class": "real_substrate_capsule",
                "claim_ceiling": "bounded",
                "status": "implemented",
                "generated_receipts": [
                    "receipts/foo/result.json",
                    "receipts/foo/source_capsules.json",
                ],
                "current_authority_receipt": "receipts/foo/authority.json",
            }
        ]
    }


def test_join_index_joins_organ_to_runner_and_receipts() -> None:
    index = build_mod.build_join_index(_lens(), _registry())
    assert index["schema_version"] == "microcosm_code_lens_join_index_v0"
    assert index["source_bodies_exported"] is False
    assert index["export_band"] == "presence_only"
    assert index["rollup"]["organ_count"] == 1
    assert index["rollup"]["organs_with_resolved_runner_source"] == 1
    impl = [e for e in index["edges"] if e["kind"] == "implemented_by_runner"]
    assert impl == [
        {
            "from_type": "organ",
            "from": "foo",
            "to_type": "source_file",
            "to": "src/microcosm_core/organs/foo.py",
            "kind": "implemented_by_runner",
        }
    ]
    assert len([e for e in index["edges"] if e["kind"] == "emits_receipt"]) == 2


def test_runner_custody_and_specificity_rollup() -> None:
    index = build_mod.build_join_index(_lens(), _registry())
    organ = index["nodes"]["organ"][0]
    # organs/ runner is an exact-copy coupling zone.
    assert organ["runner_custody_basis"] == "directory_coupling_marker"
    # only the real-coverage body_specific symbol counts.
    assert organ["runner_specificity"] == {
        "real_coverage": 1,
        "body_specific": 1,
        "generic_unique": 0,
    }
    split = index["rollup"]["runner_custody_split"]
    assert split.get("directory_coupling_marker") == 1


def test_join_index_refuses_source_body_leak() -> None:
    lens = {"payload_boundary": {"source_bodies_exported": True}, "symbol_capsule_rows": []}
    with pytest.raises(SystemExit):
        build_mod.build_join_index(lens, {"implemented_organs": []})


def test_join_index_authority_ceiling_is_non_authorizing() -> None:
    index = build_mod.build_join_index(_lens(), _registry())
    ceiling = index["authority_ceiling"]
    assert ceiling["release_authorized"] is False
    assert ceiling["source_body_export_authorized"] is False
    assert ceiling["static_analysis_authority"] is False


def test_join_index_carries_no_capsule_prose_fields() -> None:
    # The source_file nodes must be counts/refs only -- never a docstring/prose key.
    index = build_mod.build_join_index(_lens(), _registry())
    for node in index["nodes"]["source_file"]:
        assert set(node) <= {
            "path",
            "source_class",
            "custody_basis",
            "symbol_count",
            "real_coverage",
            "body_specific",
            "generic_unique",
            "has_non_goal",
        }
