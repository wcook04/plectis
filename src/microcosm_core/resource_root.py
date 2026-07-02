"""
Implements resource root for the public Plectis package.

Callers enter through `installed_microcosm_root`, `is_installed_microcosm_root`,
`project_public_root`, and `microcosm_root`; dependencies include `sys` and `pathlib`.
Importing it does not authorize release work or hidden private-state access; those effects
live behind explicit calls.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _has_public_data(root: Path) -> bool:
    """
    Return whether has public data holds for the resource root flow.

    The result is derived from `root` with `is_file`; failing evidence is returned or raised
    exactly where the body says so.
    """
    return (
        (root / "standards/std_microcosm_first_screen_composition_root.json").is_file()
        and (root / "core/organ_evidence_classes.json").is_file()
        and (root / "core/organ_registry.json").is_file()
    )


def installed_microcosm_root() -> Path:
    """
    Derive installed microcosm root without touching module import state.

    Notable helpers are `_installed_microcosm_root_candidates`, `_has_public_data`, and
    `Path`.
    """
    for candidate in _installed_microcosm_root_candidates():
        if _has_public_data(candidate):
            return candidate
    return Path(sys.prefix) / "share/plectis"


def _installed_microcosm_root_candidates() -> tuple[Path, ...]:
    """
    Return installed microcosm root candidates for the resource root flow.

    Notable helpers are `resolve`, `as_posix`, `add`, `append`, and 1 more.
    """
    share_names = ("plectis", "microcosm-substrate")
    candidates = [Path(sys.prefix) / "share" / name for name in share_names]
    module_path = Path(__file__).resolve(strict=False)
    for parent in module_path.parents:
        for name in share_names:
            candidates.append(parent / "share" / name)

    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = candidate.resolve(strict=False).as_posix()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return tuple(deduped)


def is_installed_microcosm_root(root: Path) -> bool:
    """
    Return whether is installed microcosm root holds for the resource root flow.

    The result is derived from `root` with `resolve` and `installed_microcosm_root`; failing
    evidence is returned or raised exactly where the body says so.
    """
    return root.resolve(strict=False) == installed_microcosm_root().resolve(strict=False)


def project_public_root(project: str | Path | None) -> Path | None:
    """
    Return project public root for the resource root flow.

    Inputs are `project`; notable helpers are `expanduser`, `resolve`, `extend`,
    `is_absolute`, and 4 more.
    """
    if project is None:
        return None

    path = Path(project).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.resolve(strict=False)

    candidates = [path] if path.is_dir() else [path.parent]
    candidates.extend(candidates[0].parents)
    for candidate in candidates:
        if _has_public_data(candidate):
            return candidate
    return None


def microcosm_root() -> Path:
    """
    Produce the microcosm root value used by `microcosm_core.resource_root`.

    Notable helpers are `_has_public_data`, `installed_microcosm_root`, `resolve`, and
    `Path`.
    """
    checkout_root = Path(__file__).resolve().parents[2]
    if _has_public_data(checkout_root):
        return checkout_root

    installed_root = installed_microcosm_root()
    if _has_public_data(installed_root):
        return installed_root

    return checkout_root
