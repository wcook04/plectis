"""
[PURPOSE]
- Teleology: Centralize canonical Codex path layout and legacy alias normalization.
- Mechanism: Map old codex paths (`codex/nodes`, `codex/contracts`, etc.) to
  canonical one-shot-cutover locations under `codex/substrate`, `codex/doctrine`,
  and `codex/derived`.

[INTERFACE]
- normalize_read_path(path): resolve old/new user-facing paths for read flows.
- canonicalize_write_path(path): force canonical locations for new writes.
- resolve_repo_relative(root, rel_path): return an absolute path after canonical write-path normalization.

[FLOW]
- canonicalize_write_path expands shorthand prefixes first, then collapses legacy aliases into canonical cutover destinations.
- normalize_read_path preserves already-canonical paths and otherwise reuses write canonicalization for compatibility reads.
- resolve_repo_relative applies canonicalize_write_path before joining the path to the repo root.
- When-needed: Open when a tool accepts legacy Codex paths or shorthand prefixes but must normalize them onto the post-cutover layout before reading or writing.
- Escalates-to: codex/CODEX.md; codex/_index.md
- Navigation-group: kernel_lib

[DEPENDENCIES]
- pathlib.Path: Build repo-root-resolved canonical paths.
- typing.Optional: Compatibility import retained for callers that import the module surface.

[CONSTRAINTS]
- Read compatibility accepts legacy paths.
- Write canonicalization always emits the new path layout.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

# Exact aliases that should collapse to one canonical target.
_EXACT_ALIASES = {
    "map.json": "codex/derived/map.json",
    "context_map.json": "codex/derived/map.json",
    "codex/map.json": "codex/derived/map.json",
    "codex/context_map.json": "codex/derived/map.json",
    "codex/compiled": "codex/derived/compiled",
    "codex/compiled/": "codex/derived/compiled/",
    "codex/context": "codex/doctrine",
    "codex/context/": "codex/doctrine/",
}

# Prefix aliases from legacy -> canonical cutover layout.
_PREFIX_ALIASES = (
    ("codex/nodes/", "codex/substrate/nodes/"),
    ("codex/contracts/", "codex/substrate/contracts/"),
    ("codex/configs/", "codex/substrate/configs/"),
    ("codex/refs/", "codex/substrate/refs/"),
    ("codex/dossiers/", "codex/substrate/dossiers/"),
    ("codex/context/", "codex/doctrine/"),
    ("codex/compiled/", "codex/derived/compiled/"),
)

# Short-hands accepted by some APIs (without codex/ prefix).
_SHORT_HAND_PREFIXES = (
    ("nodes/", "codex/substrate/nodes/"),
    ("contracts/", "codex/substrate/contracts/"),
    ("configs/", "codex/substrate/configs/"),
    ("refs/", "codex/substrate/refs/"),
    ("dossiers/", "codex/substrate/dossiers/"),
    ("compiled/", "codex/derived/compiled/"),
    ("context/", "codex/doctrine/"),
    ("doctrine/", "codex/doctrine/"),
)

_CANONICAL_PREFIXES = (
    "codex/substrate/",
    "codex/doctrine/",
    "codex/derived/",
    "codex/standards/",
    "codex/CODEX.md",
    "codex/_index.md",
)


def _clean(path: str) -> str:
    token = str(path).strip().replace("\\", "/")
    if not token:
        return token
    while token.startswith("./"):
        token = token[2:]
    token = token.lstrip("/")
    return token


def _apply_aliases(token: str) -> str:
    if token in _EXACT_ALIASES:
        return _EXACT_ALIASES[token]

    for old_prefix, new_prefix in _PREFIX_ALIASES:
        if token.startswith(old_prefix):
            return f"{new_prefix}{token[len(old_prefix):]}"
    return token


def canonicalize_write_path(path: str) -> str:
    """
    [ACTION]
    - Teleology: Force every caller-supplied write target onto the canonical Codex layout before any file mutation happens.
    - Mechanism: Clean the input token, expand shorthand prefixes, collapse exact and prefix legacy aliases, and special-case the historic map aliases.
    - Guarantee: Returns the canonical post-cutover path string for non-empty inputs and preserves the empty string for blank inputs.
    - Fails: None.
    - When-needed: Open when new writes must land under `codex/substrate`, `codex/doctrine`, or `codex/derived` even if the caller supplied a legacy or shorthand path.
    - Escalates-to: codex/CODEX.md
    """
    token = _clean(path)
    if not token:
        return token

    # Expand API shorthands before legacy alias collapsing.
    for short_prefix, canonical_prefix in _SHORT_HAND_PREFIXES:
        if token.startswith(short_prefix):
            token = f"{canonical_prefix}{token[len(short_prefix):]}"
            break

    token = _apply_aliases(token)

    if token == "codex/map.json":
        return "codex/derived/map.json"
    if token == "codex/context_map.json":
        return "codex/derived/map.json"

    return token


def normalize_read_path(path: str) -> str:
    """
    [ACTION]
    - Teleology: Accept legacy read paths without letting compatibility aliases leak into downstream routing or persistence logic.
    - Mechanism: Clean the input token, return it unchanged when it already sits under a canonical prefix, and otherwise reuse write canonicalization to collapse legacy aliases.
    - Guarantee: Returns the original canonical token for already-canonical paths and the normalized canonical token for legacy or shorthand paths.
    - Fails: None.
    - When-needed: Open when a read-side caller must tolerate old `codex/...` aliases while still routing all downstream work through the canonical layout.
    - Escalates-to: codex/_index.md; codex/CODEX.md
    """
    token = _clean(path)
    if not token:
        return token

    for prefix in _CANONICAL_PREFIXES:
        if token.startswith(prefix):
            return token

    return canonicalize_write_path(token)


def codex_root(root: Path) -> Path:
    """
    [ACTION]
    - Teleology: Provide the canonical root directory for all Codex-owned repository surfaces.
    - Mechanism: Append `codex` to the supplied repo root Path.
    - Guarantee: Returns `root / "codex"` without touching the filesystem.
    - Fails: None.
    - When-needed: Open when a caller needs the top-level Codex path anchor before deriving substrate, doctrine, or derived locations.
    - Escalates-to: codex/CODEX.md; codex/_index.md
    - Navigation-group: kernel_lib
    """
    return root / "codex"


def substrate_root(root: Path) -> Path:
    """
    [ACTION]
    - Teleology: Provide the canonical substrate directory for node, contract, config, and dossier artifacts after the cutover.
    - Mechanism: Reuse codex_root() and append `substrate`.
    - Guarantee: Returns `root / "codex" / "substrate"` without touching the filesystem.
    - Fails: None.
    - When-needed: Open when a caller needs the canonical substrate root instead of reconstructing post-cutover paths from legacy aliases.
    - Escalates-to: codex/CODEX.md; codex/_index.md
    - Navigation-group: kernel_lib
    """
    return codex_root(root) / "substrate"


def doctrine_root(root: Path) -> Path:
    """
    [ACTION]
    - Teleology: Provide the canonical doctrine directory for contracts, concepts, mechanisms, and other doctrine-owned surfaces.
    - Mechanism: Reuse codex_root() and append `doctrine`.
    - Guarantee: Returns `root / "codex" / "doctrine"` without touching the filesystem.
    - Fails: None.
    - When-needed: Open when a caller needs the canonical doctrine root before resolving doctrine JSON or markdown assets.
    - Escalates-to: codex/CODEX.md; codex/_index.md
    - Navigation-group: kernel_lib
    """
    return codex_root(root) / "doctrine"


def derived_root(root: Path) -> Path:
    """
    [ACTION]
    - Teleology: Provide the canonical derived directory for compiled maps and other generated Codex projections.
    - Mechanism: Reuse codex_root() and append `derived`.
    - Guarantee: Returns `root / "codex" / "derived"` without touching the filesystem.
    - Fails: None.
    - When-needed: Open when a caller needs the canonical derived root before reading or writing generated Codex artifacts.
    - Escalates-to: codex/CODEX.md; codex/_index.md
    - Navigation-group: kernel_lib
    """
    return codex_root(root) / "derived"


def resolve_repo_relative(root: Path, rel_path: str) -> Path:
    """
    [ACTION]
    - Teleology: Produce a repo-root-resolved filesystem path after applying the canonical Codex write-path rules.
    - Mechanism: Canonicalize the relative path string and join it to the supplied repo root before calling Path.resolve().
    - Guarantee: Returns an absolute Path rooted at `root` and aligned with the canonical Codex layout.
    - Fails: None.
    - When-needed: Open when a caller needs a concrete filesystem Path after normalizing a user-facing Codex path token.
    - Escalates-to: codex/CODEX.md
    """
    normalized = canonicalize_write_path(rel_path)
    return (root / normalized).resolve()
