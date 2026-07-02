"""
Implements macro tools command output read for the public Plectis package.

Callers enter through `body_import_verification`, `read_command_output`, and `main`;
constants such as `KIND`, `ERROR_KIND`, `SCHEMA_VERSION`, `COMMAND_OUTPUT_ROOT`, and 6 more
pin local fixture names; dependencies include `argparse`, `json`, `pathlib`, and `typing`.
The helpers are invoked explicitly by CLI or fixture code; importing the module only
declares the available machinery.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

KIND = "command_output_read"
ERROR_KIND = "command_output_read_error"
SCHEMA_VERSION = "command_output_read_v0"
COMMAND_OUTPUT_ROOT = Path("state/command_outputs")
SUPPORTED_BANDS = ("summary", "card", "full")
SOURCE_REF = "system/lib/kernel/commands/navigate.py"
TARGET_REF = (
    "microcosm-substrate/src/microcosm_core/macro_tools/command_output_read.py"
)
SOURCE_SYMBOL_REFS = [
    "system/lib/kernel/commands/navigate.py::cmd_command_output_read",
]
TARGET_SYMBOL_REFS = [
    "microcosm_core.macro_tools.command_output_read::read_command_output",
    "microcosm_core.macro_tools.command_output_read::main",
]
HASH_CHUNK_SIZE = 1024 * 1024


def _repo_root_from_target() -> Path | None:
    """
    Return repo root from target for `microcosm_core.macro_tools.command_output_read`.

    Inputs are the caller-supplied state; notable helpers are `resolve`, `is_file`, and
    `Path`.
    """
    for candidate in Path(__file__).resolve(strict=False).parents:
        if (candidate / SOURCE_REF).is_file():
            return candidate
    return None


def _file_sha256(path: Path) -> str:
    """
    Return the stable digest computed by
    `microcosm_core.macro_tools.command_output_read._file_sha256`.

    The input is `path`; the body uses deterministic JSON encoding or chunked file reads
    before formatting the hash.
    """
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def body_import_verification() -> dict[str, Any]:
    """
    Serialize `microcosm_core.macro_tools.command_output_read.body_import_verification` into
    the payload shape expected by macro tools command output read.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    target_path = Path(__file__).resolve(strict=False)
    repo_root = _repo_root_from_target()
    source_path = repo_root / SOURCE_REF if repo_root else None
    source_digest = (
        _file_sha256(source_path)
        if source_path is not None and source_path.is_file()
        else ""
    )
    target_digest = _file_sha256(target_path) if target_path.is_file() else ""
    status = "verified" if source_digest and target_digest else "target_available"
    return {
        "verification_status": status,
        "verification_mode": "verified_light_edit_recipe",
        "source_to_target_relation": "source_faithful_public_light_edit",
        "source_ref": SOURCE_REF,
        "target_ref": TARGET_REF,
        "source_body_digest": source_digest or None,
        "target_body_digest": target_digest or None,
        "source_symbol_refs": SOURCE_SYMBOL_REFS,
        "target_symbol_refs": TARGET_SYMBOL_REFS,
        "rewrite_recipe_ref": TARGET_REF + "::read_command_output",
        "runtime_consumed_by": [
            (
                "python -m microcosm_core.macro_tools.command_output_read "
                "--root <repo> <state/command_outputs/file.json>"
            ),
            (
                "microcosm-substrate/tests/test_command_output_projection_runtime.py::"
                "test_public_command_output_read_refactor_preserves_summary_card_and_full_bands"
            ),
        ],
        "body_in_receipt": False,
    }


def _error(status: str, **fields: Any) -> dict[str, Any]:
    """
    Serialize `microcosm_core.macro_tools.command_output_read._error` into the payload shape
    expected by macro tools command output read.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    return {
        "kind": ERROR_KIND,
        "schema_version": SCHEMA_VERSION,
        "status": status,
        **fields,
    }


def _relative_expected_root(expected_root: Path, repo_root: Path) -> str:
    """
    Derive relative expected root without touching module import state.

    Inputs are `expected_root` and `repo_root`; notable helpers are `relative_to`.
    """
    try:
        return str(expected_root.relative_to(repo_root))
    except ValueError:
        return str(expected_root)


def read_command_output(
    repo_root: str | Path,
    rel_path: str | Path,
    *,
    band: str = "summary",
) -> dict[str, Any]:
    """
    Read read command output for `microcosm_core.macro_tools.command_output_read`.

    Input comes from `repo_root`, `rel_path`, and `band`; malformed or missing data follows
    the exceptions and checks visible in the body.
    """
    if not str(rel_path):
        return _error("missing_path")

    root = Path(repo_root).resolve()
    expected_root = (root / COMMAND_OUTPUT_ROOT).resolve()
    raw_path = Path(rel_path)
    if not raw_path.is_absolute():
        raw_path = root / raw_path
    target = raw_path.resolve()
    try:
        target.relative_to(expected_root)
    except ValueError:
        return _error(
            "path_outside_command_outputs",
            path=str(rel_path),
            expected_root=_relative_expected_root(expected_root, root),
        )
    if not target.is_file():
        return _error("not_found", path=str(rel_path))

    band_choice = band.strip().lower() if isinstance(band, str) else "summary"
    if band_choice not in SUPPORTED_BANDS:
        return _error(
            "unsupported_band",
            supported_bands=list(SUPPORTED_BANDS),
            band=band_choice,
        )

    try:
        payload_bytes = target.stat().st_size
        with target.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:
        return _error(
            "invalid_json",
            path=str(rel_path),
            error=f"{type(exc).__name__}: {exc}",
        )

    rel = target.relative_to(root).as_posix()
    envelope: dict[str, Any] = {
        "kind": KIND,
        "schema_version": SCHEMA_VERSION,
        "band": band_choice,
        "source_path": rel,
        "source_bytes": payload_bytes,
    }
    if isinstance(payload, Mapping):
        envelope["payload_kind"] = payload.get("kind")
        envelope["payload_schema_version"] = payload.get("schema_version")

    if band_choice == "summary":
        if isinstance(payload, Mapping):
            summary_block = (
                payload.get("summary")
                if isinstance(payload.get("summary"), Mapping)
                else None
            )
            envelope["payload_summary"] = (
                dict(summary_block) if summary_block is not None else None
            )
            envelope["top_keys"] = sorted(str(key) for key in payload.keys())[:24]
        else:
            envelope["payload_summary"] = None
            envelope["top_keys"] = None
        return envelope

    if band_choice == "card":
        if isinstance(payload, Mapping):
            keys = list(payload.keys())[:8]
            envelope["payload"] = {str(key): payload[key] for key in keys}
            envelope["truncated_keys"] = [str(key) for key in list(payload.keys())[8:]]
        else:
            envelope["payload"] = payload
            envelope["truncated_keys"] = []
        return envelope

    envelope["payload"] = payload
    return envelope


def main(argv: list[str] | None = None) -> int:
    """
    Run `microcosm_core.macro_tools.command_output_read` as a command-line entry point.

    The command parses argv, calls this module's builders or validators, and returns the
    status code used by the process wrapper.
    """
    parser = argparse.ArgumentParser(
        prog="python -m microcosm_core.macro_tools.command_output_read"
    )
    parser.add_argument("path")
    parser.add_argument("--root", default=".")
    parser.add_argument("--band", default="summary", choices=SUPPORTED_BANDS)
    args = parser.parse_args(argv)

    result = read_command_output(args.root, args.path, band=args.band)
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 2 if result.get("kind") == ERROR_KIND else 0


if __name__ == "__main__":
    raise SystemExit(main())
