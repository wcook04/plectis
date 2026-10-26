"""
[PURPOSE]
- Teleology: Provide the canonical Python scope-selector grammar and existence predicate
  used by apply-pipeline gates (observe_compiler scope_addressable, apply.py docstring/inject
  normalization). The primitive is one named module so audit/apply/local-to-general
  surfaces can share the same scope-query semantics instead of duplicating ad-hoc AST walks.
- Mechanism: Parse-tree-only inspection over a stdlib `ast.Module`. The grammar covers
  `module`, `class:Name`, `function:Name` / `func:Name`, `method:Class.Method`, dotted
  shorthand, function-with-dot, and bare-name resolution via tree catalog of unique method
  owners. No external dependencies, no Tree-sitter, no ast-grep — the structural-query
  primitive is pattern-transferred from the ast-grep rule shape but evaluated on stdlib AST.

[INTERFACE]
- python_scope_resolve returns the resolved AST node/type evidence used by compiler/apply callers.

- Exports: `python_scope_catalog_from_tree`, `normalize_python_scope_selector`,
  `python_scope_exists`.
- Reads: A parsed `ast.Module` (or `ast.AST`); never the source filesystem.
- Writes: None.

[FLOW]
- Orders: `python_scope_catalog_from_tree(tree)` builds the catalog of top-level
  classes, functions, and unique method owners. `normalize_python_scope_selector(scope, tree=...)`
  translates legacy/loose selector spellings into one canonical AST-addressable form,
  optionally consulting the tree catalog for bare-name resolution. `python_scope_exists(tree, scope)`
  normalizes then walks the parse tree to assert addressability.
- When-needed: Open before mutating apply-gate scope predicates, lifting/duplicating
  scope helpers, or authoring a structural-query rule that must agree with the existing
  apply contract.
- Escalates-to: tools/meta/apply.py::SourceSurgeon (consumer), tools/meta/apply/observe_compiler.py::_run_deterministic_gates (consumer).
- Navigation-group: structural_query_python.

[DEPENDENCIES]
- Couples: tools/meta/apply.py re-exports `normalize_python_scope_selector` and uses it for
  docstring/inject normalization; the apply pipeline depends on these semantics being stable.
- Couples: tools/meta/apply/observe_compiler.py::_run_deterministic_gates uses
  `python_scope_exists` for the `scope_addressable` gate; gate output strings must remain
  stable because tools/meta/factory/python_std_compliance_campaign.py:316 matches the
  literal "scope_addressable" for redispatch classification.

[CONSTRAINTS]
- Guarantee: Pure functions over `ast.AST`; no I/O, no global state.
- Guarantee: Selector grammar is closed under the forms enumerated in
  `system/server/tests/test_observe_compiler.py::test_run_deterministic_gates_scope_existence_matrix`.
  Adding a new selector form requires extending the matrix.
- Non-goal: This module does not parse files, does not handle non-Python languages, does
  not provide rewrite/codemod, and does not implement relational rules. A broader
  structural-query standard is deferred until a second consuming surface is verified.
"""
from __future__ import annotations

import ast
from typing import Any


def _scope_token(value: Any) -> str:
    """
    [ACTION]
    - Teleology: Coerce a loose selector input into a clean stripped string used by
      `normalize_python_scope_selector`.
    - Mechanism: Cast to str, treat None/empty as empty, strip whitespace.
    - Reads: The raw selector value.
    - Guarantee: Always returns a string (possibly empty).
    """
    return str(value or "").strip()


def python_scope_catalog_from_tree(tree: ast.AST) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Build the top-level scope catalog used by selector normalization and
      bare-name resolution: classes, functions (sync + async), and method names whose
      owning class is unambiguous.
    - Mechanism: Walk the module body once. Top-level `FunctionDef`/`AsyncFunctionDef`
      become functions. Top-level `ClassDef` contributes its name and walks its body for
      methods, marking shared method names as ambiguous (owner=None) so callers can
      detect non-unique bare-method-name selectors.
    - Reads: Top-level body of `tree` and immediate `ClassDef` children. Nested classes
      and nested functions are intentionally ignored — the gate semantics are top-level
      only, matching `_scope_exists_in_ast` behavior pre-lift.
    - Returns: `{"functions": set[str], "classes": set[str], "unique_method_owners": dict[str, str]}`.
    - When-needed: Inside `normalize_python_scope_selector` for bare-name lookup.
    """
    functions: set[str] = set()
    classes: set[str] = set()
    method_owners: dict[str, str | None] = {}

    body = list(getattr(tree, "body", []) or [])
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.add(node.name)
            continue
        if not isinstance(node, ast.ClassDef):
            continue
        classes.add(node.name)
        for child in getattr(node, "body", []) or []:
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            prior_owner = method_owners.get(child.name)
            if prior_owner is None and child.name in method_owners:
                continue
            if prior_owner and prior_owner != node.name:
                method_owners[child.name] = None
            else:
                method_owners[child.name] = node.name

    unique_method_owners = {
        method_name: owner
        for method_name, owner in method_owners.items()
        if owner
    }
    return {
        "functions": functions,
        "classes": classes,
        "unique_method_owners": unique_method_owners,
    }


def normalize_python_scope_selector(
    scope: Any,
    *,
    tree: ast.AST | None = None,
) -> str:
    """
    [ACTION]
    - Teleology: Translate legacy / loose Python scope spellings into one canonical
      AST-addressable selector. Supported normalized forms:
        `module`, `class:Name`, `function:Name`, `func:Name`, `method:Class.Method`.
    - Mechanism: Strip and lowercase the kind prefix. Accept `kind name` (space) and
      `kind:name` (colon) shapes. Fold `function:Class.Method` and `func:Class.Method` to
      `method:Class.Method`. Fold dotted shorthand `Class.Method` to `method:Class.Method`.
      For bare names, when a `tree` is provided, look up the catalog for top-level
      function / class / unique method owner; otherwise return the input unchanged.
    - Reads: `scope` value and optional `tree`. Calls `python_scope_catalog_from_tree(tree)`
      for bare-name resolution.
    - Guarantee: Returns a string; never raises. Unknown / unresolvable selectors are
      returned unchanged so downstream gates can apply their own do-not-block policy.
    - When-needed: Before any apply gate or scope predicate that compares a selector
      against AST nodes; consumed by `python_scope_exists` and by
      `tools/meta/apply.py` docstring/inject normalization.
    """
    clean_scope = _scope_token(scope)
    if not clean_scope:
        return ""
    if clean_scope in {"module", "module:"}:
        return "module"

    head, sep, tail = clean_scope.partition(" ")
    if sep and tail.strip():
        prefix = head.strip().lower()
        if prefix == "module":
            return "module"
        if prefix in {"class", "function", "func", "method"}:
            clean_scope = f"{prefix}:{tail.strip()}"

    if ":" in clean_scope:
        kind, name = clean_scope.split(":", 1)
        kind = kind.strip().lower()
        name = name.strip()
        if kind == "module":
            return "module"
        if not name:
            return clean_scope
        if kind in {"function", "func"} and "." in name:
            return f"method:{name}"
        if kind == "class":
            return f"class:{name}"
        if kind in {"function", "func"}:
            return f"function:{name}"
        if kind == "method":
            return f"method:{name}"
        return clean_scope

    if "." in clean_scope:
        return f"method:{clean_scope}"

    if tree is None:
        return clean_scope

    catalog = python_scope_catalog_from_tree(tree)
    if clean_scope in catalog["functions"]:
        return f"function:{clean_scope}"
    if clean_scope in catalog["classes"]:
        return f"class:{clean_scope}"
    owner = catalog["unique_method_owners"].get(clean_scope)
    if owner:
        return f"method:{owner}.{clean_scope}"
    return clean_scope


def python_scope_resolve(tree: ast.AST, scope: Any) -> ast.AST | None:
    """
    [ACTION]
    - Teleology: Resolve a scope selector to the underlying `ast.AST` node so callers
      that need to mutate or inspect the node (SourceSurgeon docstring/inject ops, future
      structural rewriters) can share one dispatch with the apply-gate scope predicate.
      The semantics are byte-equal to the legacy `SourceSurgeon._resolve_target_node`
      pre-lift; existing apply/observe tests serve as integration coverage and the
      `test_observe_compiler.py` parity matrix pins the dispatch shape.
    - Mechanism: Normalize the selector via `normalize_python_scope_selector`, then walk
      the tree by kind:
        * `module`               -> the tree itself.
        * bare `Name`            -> first top-level FunctionDef|AsyncFunctionDef|ClassDef
                                    matching the name; None if not found.
        * `class:Name`           -> top-level ClassDef named Name; None otherwise.
        * `function:Name` /
          `func:Name`            -> top-level FunctionDef|AsyncFunctionDef named Name.
        * `method:Class.Method`  -> FunctionDef|AsyncFunctionDef inside ClassDef Class.
        * any other normalized   -> None (resolver-policy: unresolvable selectors must
                                    not return a surrogate node).
    - Reads: `tree` body and immediate ClassDef children. Nested scopes are intentionally
      not searched, matching pre-lift `_resolve_target_node` semantics.
    - Returns: `ast.AST` for resolved scopes, `None` otherwise.
    - Guarantee: Pure function; preserves byte-equal verdicts to the legacy
      `SourceSurgeon._resolve_target_node` body. Distinct from `python_scope_exists`:
      the existence predicate returns `True` for unknown formats (do-not-block policy
      for apply gates), while this resolver returns `None` because callers need a
      concrete node to mutate.
    - When-needed: Inside any audit/apply surface that needs the actual AST node for a
      Python scope selector, not merely a yes/no answer.
    """
    normalized_scope = normalize_python_scope_selector(scope, tree=tree)
    if normalized_scope == "module":
        return tree

    parts = normalized_scope.split(":", 1)
    if len(parts) != 2 or not parts[1]:
        for node in getattr(tree, "body", []):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == normalized_scope:
                return node
            if isinstance(node, ast.ClassDef) and node.name == normalized_scope:
                return node
        return None

    kind, name = parts[0], parts[1]

    if kind == "class":
        for node in getattr(tree, "body", []):
            if isinstance(node, ast.ClassDef) and node.name == name:
                return node
        return None

    if kind in ("func", "function"):
        # Top-level only — never walks into classes.
        # "function" accepted as bridge-output alias for "func".
        for node in getattr(tree, "body", []):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
                return node
        return None

    if kind == "method":
        if "." not in name:
            return None
        class_name, method_name = name.split(".", 1)
        target_class = None
        for node in getattr(tree, "body", []):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                target_class = node
                break
        if target_class is None:
            return None
        for node in getattr(target_class, "body", []):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == method_name:
                return node
        return None

    return None


def python_scope_exists(tree: ast.AST, scope: Any) -> bool:
    """
    [ACTION]
    - Teleology: Verify that a scope selector resolves to a real AST node in `tree`.
      This is the load-bearing predicate behind the apply-pipeline `scope_addressable`
      gate; preserving its semantics is required because
      `tools/meta/factory/python_std_compliance_campaign.py:316` matches the literal
      gate-name string `"scope_addressable"` for redispatch classification.
    - Mechanism: Normalize the selector via `normalize_python_scope_selector`, then
      dispatch:
        * `module` -> True (always exists)
        * `class:Name` -> True iff a top-level `ClassDef` named Name exists.
        * `function:Name` / `func:Name` -> True iff a top-level
          `FunctionDef`/`AsyncFunctionDef` named Name exists.
        * `method:Class.Method` -> True iff a top-level `ClassDef` named Class contains
          a `FunctionDef`/`AsyncFunctionDef` named Method.
        * any other normalized form (including unresolved bare names) -> True
          (do-not-block policy: unknown formats pass).
    - Reads: `tree` body (top-level nodes only; nested classes are not inspected for
      class:Name; nested method scopes are not inspected for method:Class.Method).
    - Guarantee: Pure function; no I/O; preserves byte-equal verdicts to the legacy
      `_scope_exists_in_ast` helper this module replaces. Verdicts are pinned by
      `system/server/tests/test_observe_compiler.py::test_run_deterministic_gates_scope_existence_matrix`.
    - When-needed: Inside any audit/apply/local-to-general surface that needs to ask
      "does this Python scope exist in this parsed module?" without re-implementing
      the dispatch.
    """
    normalized_scope = normalize_python_scope_selector(scope, tree=tree)
    if normalized_scope == "module":
        return True

    if normalized_scope.startswith("class:"):
        name = normalized_scope.split(":", 1)[-1].strip()
        return any(
            isinstance(node, ast.ClassDef) and node.name == name
            for node in getattr(tree, "body", [])
        )
    if normalized_scope.startswith(("function:", "func:")):
        name = normalized_scope.split(":", 1)[-1].strip()
        return any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
            for node in getattr(tree, "body", [])
        )
    if normalized_scope.startswith("method:"):
        parts = normalized_scope.split(":", 1)[-1].strip()
        if "." in parts:
            cls_name, method_name = parts.rsplit(".", 1)
            for node in getattr(tree, "body", []):
                if isinstance(node, ast.ClassDef) and node.name == cls_name:
                    for child in getattr(node, "body", []):
                        if (
                            isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and child.name == method_name
                        ):
                            return True
        return False
    return True  # Unknown normalized format — do not block, matches legacy policy.
