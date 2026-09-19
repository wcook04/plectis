"""
Implements resource root for the public Plectis package.

Callers enter through `installed_microcosm_root`, `is_installed_microcosm_root`,
`project_public_root`, and `microcosm_root`; dependencies include `sys` and `pathlib`.
Importing it does not authorize release work or hidden private-state access; those effects
live behind explicit calls.
"""
from __future__ import annotations

import shlex
import sys
from pathlib import Path


def installed_command(command: str, root: Path) -> str:
    """Bind a published source command to this installation and its shipped inputs.

    Inputs come from the installed data tree. Outputs stay relative to the caller,
    so running an example never writes into site-packages or share/plectis.
    Source-checkout commands retain their documented spelling.
    """
    if not is_installed_microcosm_root(root):
        return command
    parts = shlex.split(command)
    if parts and parts[0] == "PYTHONPATH=src":
        parts.pop(0)
    index = 0
    while index < len(parts) and "=" in parts[index]:
        index += 1
    if parts[index:index + 2] not in (["python3", "-m"], ["python", "-m"]):
        return command
    if len(parts) <= index + 2 or not parts[index + 2].startswith("microcosm_core"):
        return command
    parts[index] = sys.executable
    read_flags = {"--input", "--root", "--manifest", "--policy", "--protocol"}
    for position in range(index + 3, len(parts)):
        token = parts[position]
        flag, equal, value = token.partition("=")
        prior = parts[position - 1] if position else ""
        if (equal and flag in read_flags) or prior in read_flags:
            ref = value if equal else token
            path = Path(ref)
            if not path.is_absolute() and ".." not in path.parts:
                # A missing shipped input must still fail at its declared location.
                bound = str(root / path)
                parts[position] = f"{flag}={bound}" if equal else bound
        elif prior == "--out" and token.startswith("receipts/"):
            parts[position] = ".microcosm/first_action_runs/" + Path(token).name
    return shlex.join(parts)


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
