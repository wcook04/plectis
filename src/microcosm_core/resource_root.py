from __future__ import annotations

import sys
from pathlib import Path


def _has_public_data(root: Path) -> bool:
    return (
        (root / "standards/std_microcosm_first_screen_composition_root.json").is_file()
        and (root / "core/organ_evidence_classes.json").is_file()
        and (root / "core/organ_registry.json").is_file()
    )


def installed_microcosm_root() -> Path:
    for candidate in _installed_microcosm_root_candidates():
        if _has_public_data(candidate):
            return candidate
    return Path(sys.prefix) / "share/microcosm-substrate"


def _installed_microcosm_root_candidates() -> tuple[Path, ...]:
    candidates = [Path(sys.prefix) / "share/microcosm-substrate"]
    module_path = Path(__file__).resolve(strict=False)
    for parent in module_path.parents:
        candidates.append(parent / "share/microcosm-substrate")

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
    return root.resolve(strict=False) == installed_microcosm_root().resolve(strict=False)


def project_public_root(project: str | Path | None) -> Path | None:
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
    checkout_root = Path(__file__).resolve().parents[2]
    if _has_public_data(checkout_root):
        return checkout_root

    installed_root = installed_microcosm_root()
    if _has_public_data(installed_root):
        return installed_root

    return checkout_root
