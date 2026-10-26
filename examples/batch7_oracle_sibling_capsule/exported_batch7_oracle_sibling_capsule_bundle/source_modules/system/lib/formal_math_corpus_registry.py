#!/usr/bin/env python3
"""
[PURPOSE]
- Teleology: Route formal-math corpus and Lean workspace discovery through registered applicability and authority boundaries.
- Mechanism: Validate registry/manifests, select an overview or declared descriptor selectors, and resolve candidate public roots or claim-local Lean scopes without granting proof authority.

[INTERFACE]
- Exports: compile_registry_view, public_attachment_root_specs, path_is_under_corpus_root, claimed_nested_checkout_roots, local_lean_navigation_scope, lean_navigation_claim_paths, and main.
- CLI: --corpus or --problem, --view overview/identity/paper, --repo-root, and --json; emits a view or summary to stdout.

[FLOW]
- Load and validate registry plus authored manifests -> filter exact corpus/problem applicability -> optionally open declared descriptor selectors; claim helpers separately discover and gate candidate workspace paths.

[DEPENDENCIES]
- Reads: codex/doctrine/formal_math_corpus_registry.json, each declared problem manifest, selected descriptor snapshots, and candidate checkout descriptors/.git boundaries.
- Consumers: Lean navigation and public-attachment verification use the returned routes and claim paths.

[CONSTRAINTS]
- Bounds: Overview reads manifests but no descriptors; identity/paper views are declared-selector projections. Discovery/applicability is not checkout verification, proof transfer, or theorem authority.
- Fails: compile_registry_view raises ValueError for invalid registration/selection/descriptor data and propagates file/JSON failures; discovery skips unreadable or mismatched candidates. CLI validation errors become argparse SystemExit(2).
- When-needed: Open when choosing a registered comparator corpus, tracing a descriptor view, or deciding which claimed Lean paths require workspace/attachment navigation.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_REL = Path("codex/doctrine/formal_math_corpus_registry.json")
PROBLEM_ID_RE = re.compile(r"^erdos_(\d+)$")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return payload


def path_is_under_corpus_root(raw_path: Any, root: Path, *, repo_root: Path, require_exists: bool = True) -> bool:
    """Normalize Work Ledger path forms when selecting a public root."""
    token = Path(str(raw_path or "").strip()).expanduser()
    root_resolved = root.resolve()
    candidates = [token] if token.is_absolute() else [repo_root / token, repo_root.parent / token]
    # Work Ledger path claims are rooted in ai_workflow, while a standalone
    # checkout is a sibling repository.  Its canonical claim token therefore
    # carries the checkout directory as the first path component.
    if not token.is_absolute() and token.parts and token.parts[0] == root_resolved.name:
        candidates.append(root_resolved.joinpath(*token.parts[1:]))
    # An unqualified token may be interpreted inside a public attachment only
    # when that source exists. With a missing proof file, its root-qualified
    # claim or absolute coordinate must establish the boundary instead.
    if require_exists or (root_resolved / token).exists():
        candidates.append(root_resolved / token)
    for candidate in candidates:
        if require_exists and not candidate.exists():
            continue
        try:
            candidate.resolve().relative_to(root_resolved)
        except (OSError, ValueError):
            continue
        return True
    return False


def claimed_nested_checkout_roots(
    repo_root: Path, claimed_paths: Sequence[str], *, require_exists: bool = True,
) -> list[Path]:
    """Find exact claimed Lean files in nested Git checkouts, without scanning."""
    repo_root = repo_root.resolve()
    roots: list[Path] = []
    for raw_path in claimed_paths:
        token = Path(str(raw_path or "").strip()).expanduser()
        absolute = (token if token.is_absolute() else repo_root / token).resolve()
        if absolute.suffix.casefold() != ".lean" or (require_exists and not absolute.is_file()):
            continue
        try:
            absolute.relative_to(repo_root)
        except ValueError:
            continue
        for parent in absolute.parents:
            if parent == repo_root:
                break
            if (parent / ".git").exists():
                if parent not in roots:
                    roots.append(parent)
                break
    return roots


def public_attachment_root_specs(
    repo_root: Path,
    *,
    explicit_roots: Mapping[str, Path] | None = None,
    claimed_paths: Sequence[str] = (),
    require_claimed_source_exists: bool = True,
) -> list[tuple[str, Path, str]]:
    """Resolve registered public roots and their evidence for role selection."""
    repo_root = repo_root.expanduser().resolve()
    registry_path = repo_root / REGISTRY_REL
    if not registry_path.is_file():
        return []
    try:
        registry = _read_json(registry_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return []
    explicit = explicit_roots or {}
    specs: list[tuple[str, Path, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in registry.get("corpora") or []:
        if not isinstance(row, Mapping):
            continue
        corpus_id = str(row.get("corpus_id") or "")
        attachment = row.get("attachment")
        if not corpus_id or not isinstance(attachment, Mapping):
            continue
        candidates: list[tuple[Path, str]] = []
        explicit_root = explicit.get(corpus_id)
        if explicit_root is not None:
            candidates.append((Path(explicit_root), "explicit_corpus_root"))
        candidates.extend(
            (root, "claimed_nested_checkout")
            for root in claimed_nested_checkout_roots(
                repo_root, claimed_paths, require_exists=require_claimed_source_exists,
            )
        )
        candidates.extend(
            (
                repo_root.parent / str(candidate),
                "registered_sibling_root",
            )
            for candidate in attachment.get("relative_to_repo_parent_candidates") or []
        )
        cwd = Path.cwd()
        if cwd.is_dir():
            candidates.append((cwd, "current_working_directory"))
        for root, source in candidates:
            try:
                resolved = root.expanduser().resolve()
            except OSError:
                continue
            key = (corpus_id, str(resolved))
            if key in seen or not resolved.is_dir():
                continue
            seen.add(key)
            descriptor_path = resolved / str(
                attachment.get("descriptor_path") or "docs/corpus_descriptor.json"
            )
            if not descriptor_path.is_file():
                continue
            try:
                attached = _read_json(descriptor_path)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if attached.get("corpus_id") != corpus_id:
                continue
            specs.append((corpus_id, resolved, source))
    return specs


def local_lean_navigation_scope(repo_root: Path, claimed_path: str) -> tuple[Path, list[str], Path] | None:
    """The private source roots consumed by MWM's claim-local card owner.

    Export snapshots and arbitrary work files are projections, not proof
    workspaces. Formal-math projects and release consumer/mission modules are
    the established local navigation scopes; public attachments are separate.
    """
    path = Path(str(claimed_path).replace("\\", "/"))
    absolute = path if path.is_absolute() else repo_root / path
    if absolute.suffix != ".lean":
        return None
    try:
        parts = absolute.resolve().relative_to(repo_root.resolve()).parts
    except ValueError:
        return None
    project_index = next((i for i, value in enumerate(parts) if value == "formal_math"), None)
    if project_index is not None and len(parts) > project_index + 2:
        return (repo_root.joinpath(*parts[:project_index + 2]),
                list(parts[project_index + 2:]), repo_root / "formal_math")
    if len(parts) >= 5 and parts[0] == "work" and parts[2] in {"consumers", "missions"}:
        project_root = repo_root.joinpath(*parts[:4])
        return project_root, list(parts[4:]), project_root
    return None


def lean_navigation_claim_paths(repo_root: Path, claimed_paths: Sequence[str]) -> list[str]:
    """Select proof workspace claims, without granting proof/attachment validity.

    Public root selection uses the same registered descriptor discovery as
    MWM. A discovered root remains gated even when later identity verification
    fails; a registry candidate never supplies a valid card by itself.
    """
    lean_paths = [str(p).strip().replace("\\", "/") for p in claimed_paths
                  if str(p).strip().lower().endswith(".lean")]
    public_roots = [root for _, root, _ in public_attachment_root_specs(
        repo_root, claimed_paths=lean_paths,
        require_claimed_source_exists=False)] if lean_paths else []
    # Configured public roots must stay gated when a descriptor is missing or
    # stale. Discovery is not attachment verification and cannot waive the gate.
    if lean_paths:
        try:
            registry = _read_json(repo_root / REGISTRY_REL)
        except (OSError, ValueError, json.JSONDecodeError):
            registry = {}
        for row in registry.get("corpora") or []:
            attachment = row.get("attachment") if isinstance(row, Mapping) else None
            if isinstance(attachment, Mapping):
                public_roots.extend(
                    repo_root.parent / str(candidate)
                    for candidate in attachment.get("relative_to_repo_parent_candidates") or []
                )
    selected = []
    for path in lean_paths:
        absolute = Path(path) if Path(path).is_absolute() else repo_root / path
        try:
            parts = absolute.resolve().relative_to(repo_root.resolve()).parts
        except ValueError:
            parts = ()
        # Keep the legacy top-level formal_math claim gate, including a new
        # not-yet-created source, while project cards retain their module roots.
        canonical_formal = bool(parts and parts[0] == "formal_math")
        if (canonical_formal or local_lean_navigation_scope(repo_root, path) is not None
                or any(path_is_under_corpus_root(path, root, repo_root=repo_root,
                                                require_exists=False)
                       for root in public_roots)):
            selected.append(path)
    return sorted(set(selected))


def _resolve_selector(payload: Mapping[str, Any], selector: str) -> object:
    current: object = payload
    for part in selector.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise ValueError(f"descriptor selector does not resolve: {selector}")
        current = current[part]
    return current


def _normalize_problem_id(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    if normalized.isdecimal():
        normalized = f"erdos_{int(normalized)}"
    elif normalized.startswith("erdos") and normalized[5:].lstrip("_").isdecimal():
        normalized = f"erdos_{int(normalized[5:].lstrip('_'))}"
    if PROBLEM_ID_RE.fullmatch(normalized) is None:
        raise ValueError(f"invalid problem id: {value!r}")
    return normalized


def _manifest_problem_ids(repo_root: Path, manifest_ref: str) -> list[str]:
    manifest = _read_json(repo_root / manifest_ref)
    problems = manifest.get("problems")
    if not isinstance(problems, list):
        raise ValueError(f"manifest problems must be a list: {manifest_ref}")
    problem_ids = [row.get("id") for row in problems if isinstance(row, Mapping)]
    if len(problem_ids) != len(problems) or not all(
        isinstance(problem_id, str)
        and _normalize_problem_id(problem_id) == problem_id
        for problem_id in problem_ids
    ):
        raise ValueError(f"manifest problem ids are invalid: {manifest_ref}")
    if len(problem_ids) != len(set(problem_ids)):
        raise ValueError(f"manifest problem ids are duplicated: {manifest_ref}")
    return problem_ids


def _registry_row(repo_root: Path, row: Mapping[str, Any]) -> dict[str, Any]:
    navigation = row.get("navigation")
    attachment = row.get("attachment")
    if not isinstance(navigation, Mapping) or not isinstance(attachment, Mapping):
        raise ValueError(f"invalid corpus registry row: {row.get('corpus_id')!r}")
    corpus_id = row.get("corpus_id")
    if not isinstance(corpus_id, str) or not corpus_id:
        raise ValueError("corpus registry row is missing corpus_id")
    problem_scope = row.get("problem_scope")
    if not isinstance(problem_scope, Mapping):
        raise ValueError(f"invalid problem_scope for corpus registry row: {corpus_id}")
    scope_kind = problem_scope.get("kind")
    if scope_kind == "all_manifest_problems":
        manifest_ref = problem_scope.get("manifest_ref")
        if not isinstance(manifest_ref, str) or not manifest_ref:
            raise ValueError(f"problem_scope has no manifest_ref for corpus: {corpus_id}")
        problem_ids = _manifest_problem_ids(repo_root, manifest_ref)
    elif scope_kind == "independent_corpus":
        # An independent owner's corpus has no implied membership in the
        # private Erdős manifest. Its descriptor remains independently usable.
        if "manifest_ref" in problem_scope:
            raise ValueError(f"independent_corpus must not declare manifest_ref: {corpus_id}")
        if problem_scope.get("problem_ids", []) != []:
            raise ValueError(f"independent_corpus problem_ids must be empty: {corpus_id}")
        problem_ids = []
    else:
        raise ValueError(f"unsupported problem_scope kind for corpus: {corpus_id}")
    return {
        "corpus_id": corpus_id,
        "display_name": row.get("display_name"),
        "stable_id_scope_note": row.get("stable_id_scope_note"),
        "problem_ids": problem_ids,
        "problem_count": len(problem_ids),
        "problem_scope": dict(problem_scope),
        "descriptor_ref": row.get("descriptor_ref"),
        "disclosure_posture": row.get("disclosure_posture"),
        "attachment_kind": attachment.get("kind"),
        "attachment_candidates": attachment.get("relative_to_repo_parent_candidates", []),
        "identity_view_command": (
            "./repo-python -m system.lib.formal_math_corpus_registry "
            f"--corpus {corpus_id} --view identity --json"
        ),
        "paper_view_command": (
            "./repo-python -m system.lib.formal_math_corpus_registry "
            f"--corpus {corpus_id} --view paper --json"
        ),
        "attachment_verification_command": navigation.get(
            "attachment_verification_command"
        ),
        "consumer_action": navigation.get("consumer_action"),
    }


def compile_registry_view(
    repo_root: Path,
    *,
    corpus_id: str | None = None,
    problem_id: str | None = None,
    view: str = "overview",
) -> dict[str, Any]:
    """Compile a registry-only overview or one descriptor's named selector view."""

    if view not in {"overview", "identity", "paper"}:
        raise ValueError(f"unknown view: {view}")
    if corpus_id is not None and problem_id is not None:
        raise ValueError("corpus_id and problem_id are mutually exclusive")
    if view != "overview" and corpus_id is None:
        raise ValueError(f"--view {view} requires --corpus")
    normalized_problem_id = (
        _normalize_problem_id(problem_id) if problem_id is not None else None
    )

    registry = _read_json(repo_root / REGISTRY_REL)
    navigation_contract = registry.get("navigation_contract")
    if not isinstance(navigation_contract, Mapping):
        raise ValueError("registry navigation_contract must be an object")
    problem_routing_contract = registry.get("problem_routing_contract")
    if not isinstance(problem_routing_contract, Mapping):
        raise ValueError("registry problem_routing_contract must be an object")
    raw_rows = registry.get("corpora")
    if not isinstance(raw_rows, list):
        raise ValueError("registry corpora must be a list")
    if not all(isinstance(row, Mapping) for row in raw_rows):
        raise ValueError("registry corpora rows must be objects")
    rows = list(raw_rows)
    compiled_rows: dict[str, dict[str, Any]] = {}
    for row in rows:
        compiled = _registry_row(repo_root, row)
        if compiled["corpus_id"] in compiled_rows:
            raise ValueError(f"duplicate corpus_id: {compiled['corpus_id']}")
        compiled_rows[compiled["corpus_id"]] = compiled
    selected = [row for row in rows if row.get("corpus_id") == corpus_id]
    if corpus_id is not None and not selected:
        raise ValueError(f"unknown corpus_id: {corpus_id}")

    if corpus_id is not None:
        emitted_rows = selected
    elif normalized_problem_id is not None:
        emitted_rows = [
            row
            for row in rows
            if normalized_problem_id in compiled_rows[row["corpus_id"]]["problem_ids"]
        ]
    else:
        emitted_rows = rows
    payload: dict[str, Any] = {
        "schema_version": "formal_math_corpus_registry_view_v1",
        "kind": "formal_math_corpus_registry_view",
        "view": view,
        "authority_boundary": navigation_contract.get("authority_boundary"),
        "selection_order": navigation_contract.get("selection_order", []),
        "problem_routing_boundary": problem_routing_contract.get(
            "authority_boundary"
        ),
        "filters": {"corpus_id": corpus_id, "problem_id": normalized_problem_id},
        "summary": {
            "registered_corpus_count": len(rows),
            "emitted_corpus_count": len(emitted_rows),
        },
        "corpora": [compiled_rows[row["corpus_id"]] for row in emitted_rows],
    }
    if view == "overview":
        payload["boundary"] = (
            "Registry rows only: no descriptor or attached checkout is opened, and no "
            "mathematical or identity match is inferred. A problem filter returns only "
            "authored applicability links and never proof transfer."
        )
        if normalized_problem_id is not None and not emitted_rows:
            payload["zero_match_meaning"] = problem_routing_contract.get(
                "zero_match_meaning"
            )
        return payload

    row = selected[0]
    descriptor_ref = row.get("descriptor_ref")
    if not isinstance(descriptor_ref, str) or not descriptor_ref:
        raise ValueError(f"registry row has no descriptor_ref: {corpus_id}")
    descriptor = _read_json(repo_root / descriptor_ref)
    if descriptor.get("corpus_id") != corpus_id:
        raise ValueError(
            f"descriptor corpus_id mismatch: expected {corpus_id!r}, "
            f"found {descriptor.get('corpus_id')!r}"
        )
    navigation = row.get("navigation")
    if not isinstance(navigation, Mapping):
        raise ValueError(f"registry row navigation must be an object: {corpus_id}")

    if view == "identity":
        selectors = navigation.get("descriptor_identity_selectors", [])
        if not isinstance(selectors, list) or not all(
            isinstance(selector, str) for selector in selectors
        ):
            raise ValueError("descriptor_identity_selectors must be a string list")
        payload["selector_groups"] = {
            "descriptor_identity": {
                selector: _resolve_selector(descriptor, selector) for selector in selectors
            }
        }
    else:
        paper_selectors = navigation.get("paper_identity_selectors", [])
        expansion_selectors = navigation.get("descriptor_expansion_selectors", [])
        if not isinstance(paper_selectors, list) or not all(
            isinstance(selector, str) for selector in paper_selectors
        ):
            raise ValueError("paper_identity_selectors must be a string list")
        if not isinstance(expansion_selectors, list) or not all(
            isinstance(selector, str) for selector in expansion_selectors
        ):
            raise ValueError("descriptor_expansion_selectors must be a string list")
        payload["selector_groups"] = {
            "paper_identity": {
                selector: _resolve_selector(descriptor, selector)
                for selector in paper_selectors
            },
            "descriptor_expansion_handles": {
                selector: _resolve_selector(descriptor, selector)
                for selector in expansion_selectors
            },
        }
    payload["boundary"] = (
        "Only registry-declared selectors are opened. Descriptor identity is not checkout "
        "verification; paper and navigation artifacts are not Lean proof authority."
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--corpus", help="select one exact registered corpus_id")
    selection.add_argument(
        "--problem",
        help="show registered comparator routes explicitly applicable to one Erdős problem",
    )
    parser.add_argument(
        "--view",
        choices=("overview", "identity", "paper"),
        default="overview",
    )
    parser.add_argument("--json", action="store_true", help="emit the structured view")
    args = parser.parse_args(argv)
    try:
        payload = compile_registry_view(
            args.repo_root.resolve(),
            corpus_id=args.corpus,
            problem_id=args.problem,
            view=args.view,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
