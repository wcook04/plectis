"""
[PURPOSE]
- Teleology: Provide a single, deterministic dossier rendering surface for build-time compilation and runtime prompt injection.
- Mechanism: Read `codex/dossiers/*.json`, normalize payloads, and render a compact Markdown bundle.
- Non-goal: Mutate dossiers, synthesize contradictions, or persist runtime state.

[INTERFACE]
- Exports:
  - `load_dossier_payloads(root: Path) -> Dict[str, Dict[str, Any]]`
  - `list_dossier_paths(root: Path) -> List[str]`
  - `render_dossier_markdown(root: Path, dossier_names: Iterable[str] | None = None) -> str`
- Inputs: repository root path plus optional dossier-name filter.
- Outputs: JSON dictionaries and Markdown text suitable for builder artifacts or prompt injection.

[FLOW]
- Resolve dossier directory (`codex/substrate/dossiers` preferred, fallback `codex/dossiers`).
- Load dossier JSON files in stable filename order.
- Render each dossier into a compact Markdown section with mechanisms, invariants, anti-patterns, and source runs.
- When-needed: Open when a caller needs the canonical dossier discovery and Markdown rendering surface instead of reading compiled dossier artifacts or dossier JSON files separately.
- Escalates-to: system/core/loader.py::_resolve_compiled_dossier_bundle; tools/meta/builder.py
- Navigation-group: kernel_lib

[DEPENDENCIES]
- codex/dossiers/*.json authored dossier payloads; malformed/non-object records are handled by the loader.

[CONSTRAINTS]
- Reads only; never writes.
- Rendering order is deterministic by dossier filename and mechanism key.
- Invalid/non-dict JSON files degrade to empty dossier sections instead of raising.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def _dossier_dir(root: Path) -> Path:
    """
    [ACTION]
    - Teleology: Resolve the canonical dossier directory with substrate-first fallback semantics.
    - Mechanism: Prefer `codex/substrate/dossiers`, otherwise use `codex/dossiers`.
    - Guarantee: Returns a path under the repository root even when the directory is missing.
    - Fails: None.
    """
    substrate_dir = root / "codex" / "substrate" / "dossiers"
    if substrate_dir.exists():
        return substrate_dir
    return root / "codex" / "dossiers"


def _clean_string_list(value: Any) -> List[str]:
    """
    [ACTION]
    - Teleology: Normalize mixed dossier fields into a stable list of non-empty strings.
    - Mechanism: Accept list/tuple/set/scalar values and strip empties.
    - Guarantee: Returns a JSON-safe list of strings.
    - Fails: None.
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        items = value
    else:
        items = [value]
    out: List[str] = []
    for item in items:
        text = str(item).strip()
        if text:
            out.append(text)
    return out


def list_dossier_paths(root: Path) -> List[str]:
    """
    [ACTION]
    - Teleology: Return the repository-relative dossier file list for manifests and telemetry.
    - Mechanism: Scan the resolved dossier directory for `*.json`.
    - Guarantee: Paths are returned in sorted order relative to `root`.
    - Fails: Missing dossier directory -> Returns empty list.
    - When-needed: Open when engine or loader code needs the stable dossier path inventory before deciding whether dossier injection is available.
    - Escalates-to: system/core/loader.py::_resolve_compiled_dossier_bundle; system/core/engine.py
    """
    dossier_dir = _dossier_dir(root)
    if not dossier_dir.exists():
        return []
    return [
        path.relative_to(root).as_posix()
        for path in sorted(dossier_dir.glob("*.json"))
        if path.is_file()
    ]


def load_dossier_payloads(root: Path) -> Dict[str, Dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Load dossier JSON payloads once for build/runtime consumers.
    - Mechanism: Read each dossier file into a dict keyed by filename stem.
    - Guarantee: Returns only dict payloads; malformed or non-dict files degrade to `{}`.
    - Fails: None.
    - When-needed: Open when a build or runtime surface needs the normalized in-memory dossier payload table instead of the rendered Markdown bundle.
    - Escalates-to: tools/meta/builder.py; system/core/loader.py::_resolve_compiled_dossier_bundle
    """
    dossier_dir = _dossier_dir(root)
    if not dossier_dir.exists():
        return {}

    payloads: Dict[str, Dict[str, Any]] = {}
    for path in sorted(dossier_dir.glob("*.json")):
        if not path.is_file():
            continue
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            payloads[path.stem] = loaded if isinstance(loaded, dict) else {}
        except Exception:
            payloads[path.stem] = {}
    return payloads


def render_dossier_markdown(root: Path, dossier_names: Optional[Iterable[str]] = None) -> str:
    """
    [ACTION]
    - Teleology: Convert authored dossier JSON into a concise Markdown bundle that LLM prompts can digest reliably.
    - Mechanism: Render schema note + per-mechanism bullets for the selected dossiers.
    - Guarantee: Returns deterministic Markdown with a trailing newline.
    - Fails: Missing dossier files -> Returns an empty-state Markdown bundle.
    - When-needed: Open when a prompt-injection or derived-build path needs the exact dossier Markdown rendering contract instead of precompiled `dossiers.md`.
    - Escalates-to: system/core/loader.py::_resolve_compiled_dossier_bundle; tools/meta/builder.py
    """
    payloads = load_dossier_payloads(root)
    requested = None
    if dossier_names is not None:
        requested = {str(name).strip().lower() for name in dossier_names if str(name).strip()}

    dossier_dir = _dossier_dir(root)
    lines: List[str] = [
        "# Active Dossiers",
        "",
        "Compiled from `codex/dossiers/*.json` for prompt injection and machine navigation.",
        "",
    ]

    names = sorted(payloads.keys())
    if requested is not None:
        names = [name for name in names if name.lower() in requested]

    if not names:
        lines.extend(
            [
                "- No dossier payloads are currently available.",
                "",
            ]
        )
        return "\n".join(lines).rstrip() + "\n"

    for name in names:
        payload = payloads.get(name, {})
        source_path = (dossier_dir / f"{name}.json")
        try:
            rel_path = source_path.relative_to(root).as_posix()
        except ValueError:
            rel_path = source_path.as_posix()

        mechanisms_raw = payload.get("mechanisms", {})
        mechanisms = mechanisms_raw if isinstance(mechanisms_raw, dict) else {}
        schema_note = str(payload.get("_schema_note", "") or "").strip()

        lines.extend(
            [
                f"## {name.upper()}",
                f"- Source: `{rel_path}`",
                f"- Mechanism count: {len(mechanisms)}",
            ]
        )
        if schema_note:
            lines.append(f"- Schema note: {schema_note}")

        if not mechanisms:
            lines.extend(
                [
                    "- No active mechanisms recorded.",
                    "",
                ]
            )
            continue

        lines.append("")
        for mechanism_name in sorted(mechanisms.keys()):
            mechanism = mechanisms.get(mechanism_name, {})
            mechanism = mechanism if isinstance(mechanism, dict) else {}

            definition = str(mechanism.get("definition", "") or "").strip()
            invariants = _clean_string_list(mechanism.get("historical_invariants"))
            anti_patterns = _clean_string_list(mechanism.get("anti_patterns"))
            source_runs = _clean_string_list(mechanism.get("source_runs"))
            added = str(mechanism.get("added", "") or "").strip()

            lines.append(f"### {mechanism_name}")
            if definition:
                lines.append(f"- Definition: {definition}")
            if invariants:
                lines.append("- Historical invariants:")
                for item in invariants:
                    lines.append(f"  - {item}")
            if anti_patterns:
                lines.append("- Anti-patterns:")
                for item in anti_patterns:
                    lines.append(f"  - {item}")
            if source_runs:
                lines.append(f"- Source runs: {', '.join(source_runs)}")
            if added:
                lines.append(f"- Added: {added}")
            if not any((definition, invariants, anti_patterns, source_runs, added)):
                lines.append("- Mechanism payload present but empty.")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"
