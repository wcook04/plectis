from __future__ import annotations

import sys
from pathlib import Path


def _has_public_data(root: Path) -> bool:
    """Probe whether a directory carries the public-data manifest triple.

    - Teleology: the single membership test that decides whether a candidate path is a usable Plectis public root under the microcosm-substrate compatibility layout.
    - Guarantee: returns True iff all three public manifest files (first-screen composition standard, organ evidence classes, organ registry) exist as files under `root`.
    - Fails: never raises; a missing file or non-directory `root` yields False.
    - Reads: standards/std_microcosm_first_screen_composition_root.json, core/organ_evidence_classes.json, core/organ_registry.json under `root`.
    - When-needed: when auditing why a candidate root was accepted or rejected by the resolvers below.
    - Non-goal: does not validate manifest contents, authorize source-body export, public-safe equivalence, or release; presence only.
    """
    return (
        (root / "standards/std_microcosm_first_screen_composition_root.json").is_file()
        and (root / "core/organ_evidence_classes.json").is_file()
        and (root / "core/organ_registry.json").is_file()
    )


def installed_microcosm_root() -> Path:
    """Resolve the public root of an installed (pip/share) Microcosm payload.

    - Teleology: locate the share/microcosm-substrate data dir for an installed package so readers find the manifest off-checkout.
    - Guarantee: returns the first candidate that passes `_has_public_data`; otherwise returns the canonical `sys.prefix/share/microcosm-substrate` fallback (which may not exist).
    - Fails: never raises; returns the prefix-based fallback Path when no candidate carries the manifest triple.
    - Reads: the public manifest triple under each candidate (via `_has_public_data`); `sys.prefix` and this module's path.
    - When-needed: when a reader is running against an installed package rather than a source checkout.
    - Non-goal: does not guarantee the returned path exists or is release-authorized; presence/location only.
    """
    for candidate in _installed_microcosm_root_candidates():
        if _has_public_data(candidate):
            return candidate
    return Path(sys.prefix) / "share/microcosm-substrate"


def _installed_microcosm_root_candidates() -> tuple[Path, ...]:
    """Enumerate deduped candidate locations for an installed public root.

    - Teleology: produce the ordered search path (prefix share dir, then every parent's share dir) that `installed_microcosm_root` scans.
    - Guarantee: returns a tuple of candidate Paths with duplicates removed by resolved posix key, prefix-share first then ancestor-share dirs in nearest-parent order.
    - Fails: never raises; resolution uses strict=False so missing paths are tolerated.
    - Reads: `sys.prefix` and this module's resolved parents; touches no manifest files.
    - When-needed: when debugging which share directory order the installed-root resolver walks.
    - Non-goal: does not test for manifest presence or authorize any candidate; ordering/dedup only.
    """
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
    """Decide whether a path is the resolved installed public root.

    - Teleology: let callers distinguish an installed-package root from a source-checkout root for path-policy branching.
    - Guarantee: returns True iff `root` resolves (strict=False) to the same path as `installed_microcosm_root()`.
    - Fails: never raises; non-existent paths compare by their strict=False resolution.
    - Reads: the installed-root resolution chain (no manifest file reads beyond what that resolver performs).
    - When-needed: when behavior must differ between installed-package and in-checkout execution.
    - Non-goal: does not validate manifest presence at `root` or authorize release; identity comparison only.
    """
    return root.resolve(strict=False) == installed_microcosm_root().resolve(strict=False)


def project_public_root(project: str | Path | None) -> Path | None:
    """Walk up from a project path to the nearest enclosing public root.

    - Teleology: resolve an operator-supplied project location to the public root that owns its manifest, supporting non-cwd invocations.
    - Guarantee: returns the nearest ancestor (or the path/parent itself) that passes `_has_public_data`; returns None when `project` is None or no ancestor carries the manifest triple.
    - Fails: never raises; returns None on missing manifest or None input. Relative paths are anchored to cwd before resolution.
    - Reads: the public manifest triple under the path and its parents (via `_has_public_data`); cwd for relative inputs.
    - When-needed: when resolving a public root for a project passed on the CLI rather than the current checkout.
    - Non-goal: does not authorize export, private-root equivalence, or release; locates a manifest-bearing root only.
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
    """Resolve the active public root, preferring the source checkout.

    - Teleology: the default public-root entry point readers call when no project is supplied; the canonical "where does my manifest live" answer.
    - Guarantee: returns the source checkout root when it carries the manifest triple, else the installed root when it does, else falls back to the checkout root regardless.
    - Fails: never raises; the final fallback returns the checkout root even when no manifest triple is present.
    - Reads: the public manifest triple under the checkout root and the installed root (via `_has_public_data`); this module's resolved parents.
    - When-needed: as the default root for any reader that did not pass an explicit project path.
    - Escalates-to: project_public_root for explicit-project resolution; installed_microcosm_root for the installed-package branch.
    - Non-goal: does not guarantee the returned root carries the manifest or authorize release; best-effort location only.
    """
    checkout_root = Path(__file__).resolve().parents[2]
    if _has_public_data(checkout_root):
        return checkout_root

    installed_root = installed_microcosm_root()
    if _has_public_data(installed_root):
        return installed_root

    return checkout_root
