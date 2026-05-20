from __future__ import annotations

from pathlib import Path
from typing import Any

from .schemas import read_json_strict, read_jsonl_strict


PATTERN_BINDING_OPTIONAL_INPUTS = {
    "authority_chain_handles": "authority_chain_handles.json",
    "duplicate_patterns": "duplicate_pattern_id_conflict.jsonl",
    "generated_projection_authority_upgrade": "generated_projection_authority_upgrade.json",
    "reference_capsules": "reference_capsules.json",
    "source_capsule_with_private_body": "source_capsule_with_private_body.json",
    "valid_binding_overclaim_public_leaf": "valid_binding_overclaim_public_leaf.json",
}

PATTERN_BINDING_SUBSTRATE_BUNDLE_REQUIRED_INPUTS = {
    "bundle_manifest": "bundle_manifest.json",
    "patterns": "pattern_rows.jsonl",
    "source_capsules": "source_capsules.json",
    "forbidden_terms": "private_state_forbidden_terms.json",
    "authority_chain_handles": "authority_chain_handles.json",
    "reference_capsules": "reference_capsules.json",
    "omission_receipts": "omission_receipts.json",
}


def load_pattern_binding_fixture(input_dir: str | Path) -> dict[str, Any]:
    root = Path(input_dir)
    required = {
        "patterns": root / "patterns.jsonl",
        "source_capsules": root / "source_capsules.json",
        "forbidden_terms": root / "private_state_forbidden_terms.json",
    }
    missing = [path.as_posix() for path in required.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing pattern-binding fixture input(s): {', '.join(missing)}")

    payload: dict[str, Any] = {
        "patterns": read_jsonl_strict(required["patterns"]),
        "source_capsules": read_json_strict(required["source_capsules"]),
        "forbidden_terms": read_json_strict(required["forbidden_terms"]),
        "input_paths": {key: path.as_posix() for key, path in required.items()},
    }
    for key, filename in PATTERN_BINDING_OPTIONAL_INPUTS.items():
        path = root / filename
        if not path.is_file():
            continue
        payload["input_paths"][key] = path.as_posix()
        payload[key] = read_jsonl_strict(path) if filename.endswith(".jsonl") else read_json_strict(path)
    return payload


def load_pattern_binding_substrate_bundle(input_dir: str | Path) -> dict[str, Any]:
    root = Path(input_dir)
    required = {
        key: root / filename
        for key, filename in PATTERN_BINDING_SUBSTRATE_BUNDLE_REQUIRED_INPUTS.items()
    }
    missing = [path.as_posix() for path in required.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing pattern-binding substrate bundle input(s): {', '.join(missing)}")

    payload: dict[str, Any] = {
        "input_mode": "exported_substrate_bundle",
        "bundle_manifest": read_json_strict(required["bundle_manifest"]),
        "patterns": read_jsonl_strict(required["patterns"]),
        "source_capsules": read_json_strict(required["source_capsules"]),
        "forbidden_terms": read_json_strict(required["forbidden_terms"]),
        "authority_chain_handles": read_json_strict(required["authority_chain_handles"]),
        "reference_capsules": read_json_strict(required["reference_capsules"]),
        "omission_receipts": read_json_strict(required["omission_receipts"]),
        "input_paths": {key: path.as_posix() for key, path in required.items()},
    }
    return payload


def load_first_wave_fixture(organ_id: str, input_dir: str | Path) -> dict[str, Any]:
    if organ_id != "pattern_binding_contract":
        raise ValueError(f"unsupported first-wave organ in this slice: {organ_id}")
    return load_pattern_binding_fixture(input_dir)
