#
"""
[PURPOSE]
- Teleology: Hydrate on-disk Codex node JSON into validated in-memory `CodexNode` objects for downstream execution.
- Mechanism: Manifest scan -> JSON hydration -> instruction tag injection -> config inheritance/merge -> execution defaults -> governance handoff.
- Non-goal: Perform dependency/graph reasoning or topology enforcement beyond explicit delegation to `system.core.governance`.
[ROLE]
- Teleology: Hydrate on-disk Codex node JSON into validated in-memory `CodexNode` objects.
- Mechanism: Manifest scan -> JSON hydration -> config inheritance -> tag injection -> governance parsing.
- Constraint: IO Boundary only. All graph logic delegates to `system.core.governance`.
[INTERFACE]
- exports: PhysicalLoader, LoaderError
- inputs:
  - root_dir: repository root directory containing `codex/nodes/`
  - inject_sys_path: opt-in mutation of `sys.path` to include `root_dir`
- outputs:
  - `CodexNode` objects (via `system.core.governance.parse_node`)
  - graph dict: `Dict[str, CodexNode]`
  - delegated topology artifacts: waves (`List[List[str]]`), validation issues (`List[ValidationIssue]`)
[FLOW]
- Reads:
  - `codex/nodes/**/*.json` (node candidates)
  - optional per-node `config_file` JSON (repo-relative only)
- Writes:
  - stdout warnings during manifest scan for malformed/non-node JSON
  - `sys.path` when `inject_sys_path=True`
- Couples:
  - `system.core.governance`: source of truth for node normalization, dependency handling, and topology semantics.
- When-needed: Open when a task is about turning on-disk node/config JSON into governance-validated runtime objects or manifest/topology inputs.
- Escalates-to: system/core/governance.py::parse_node; system/core/analysis.py::analyze_python_module
- Navigation-group: system_core
[DEPENDENCIES]
- system.core.governance: validate_topology (graph integrity)
- system.lib.utils: deep_merge (config layering)
- system.sys.path: injection (repo root resolution)
- data.codex/nodes: manifest_scanning (graph discovery)
[CONSTRAINTS]
- Atomic:
  - Node hydration is per-file; no multi-file transaction or rollback is provided.
  - Config merge is in-memory; this module does not persist merged config to disk.
- Orders:
  - `load_all_nodes()` loads in sorted node-id order (deterministic over the manifest keys).
  - `_NodeIndexer.scan()` traverses filesystem candidates in sorted path order (deterministic across platforms/filesystems).
- Locks: None. Caller must serialize concurrent use when filesystem contents may change during scan/load or when `inject_sys_path=True`.
"""

from __future__ import annotations

import importlib
import hashlib
import json
import re
import sys
import copy
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, Optional, Union, Set

# --- THE PIVOT: Import Governance ---
from system.lib.utils import deep_merge
from system.core.governance import (
    parse_node as gov_parse_node,
    compute_waves as gov_compute_waves,
    validate_topology as gov_validate_topology,
    ValidationIssue
)

from system.lib.contracts import CONTRACT_REF_RE
from system.lib.dossiers import list_dossier_paths, render_dossier_markdown

from system.lib.types import (
    CodexNode,
    DuplicateIDError,
    DEFAULT_EXECUTION_CONFIG,
)

class LoaderError(Exception):
    """
    [ROLE]
    - Teleology: Provide a loader-scoped exception type for IO-bound hydration failures and delegated topology/parsing failures.
    - Mechanism: Wrap underlying exceptions with node/path context and re-raise as a single domain surface.
    - Ownership: Owned by loader callers as the primary failure signal for `PhysicalLoader`.
    - Mutability: Immutable after instantiation (exception payload is message + cause).
    - Concurrency: Thread-safe as a value object; does not coordinate concurrent loader access.
    - Guarantee: When raised by this module, message contains a loader-context prefix (e.g., "Loader init failed", "Load node failed").
    """
    pass

class _NodeIndexer:
    """
    [ROLE]
    - Teleology: Build a stable mapping from `node_id` -> on-disk JSON `Path` under `codex/nodes/`.
    - Mechanism: Filesystem scan (`rglob`) -> JSON parse -> extract `"id"` -> enforce uniqueness.
    - Ownership: Owns `root` and derived `nodes_dir` paths; produces manifest dict for `PhysicalLoader`.
    - Mutability: `root`/`nodes_dir` stable after init; manifest produced per `scan()` call.
    - Concurrency: No internal locks; caller must serialize scans if filesystem contents are mutable.
    - Writes: stdout warnings for malformed JSON and helper assets (JSON without `"id"`).
    """

    def __init__(self, root: Union[str, Path] = ".") -> None:
        """
        [ACTION]
        - Teleology: Initialize the indexer with a resolved root and nodes directory.
        - Mechanism: Path resolution via `pathlib.Path.resolve()`.
        - Preconditions: `root` must be a path-like accepted by `pathlib.Path`.
        - Reads: Resolves `root` to an absolute path; derives `codex/nodes` path.
        - Writes: None.
        - Guarantee: Initializes `self.root` and `self.nodes_dir` as resolved absolute paths.
        - Fails: - Propagates `OSError`/`ValueError` from path resolution.
        - Orders: None.
        - Locks: None.
        """
        self.root: Path = Path(root).resolve()
        substrate_nodes = (self.root / "codex" / "substrate" / "nodes").resolve()
        legacy_nodes = (self.root / "codex" / "nodes").resolve()
        self.nodes_dir: Path = substrate_nodes if substrate_nodes.exists() else legacy_nodes

    def scan(self) -> Dict[str, Path]:
        """
        [ACTION]
        - Teleology: Scan the nodes directory to build a mapping of node IDs to file paths.
        - Mechanism: Recursive glob, JSON parsing, and ID extraction with duplicate checking.
        - Preconditions: None.
        - Reads: Walks `self.nodes_dir` recursively and parses candidate `.json` files.
        - Writes:
          - stdout warning when a JSON file is malformed or when a JSON object lacks `"id"`.
        - Guarantee: Returns a manifest mapping `node_id` (str) -> absolute `Path` for each valid node JSON encountered.
        - Fails:
          - `DuplicateIDError` if two JSON files declare the same trimmed `"id"`.
          - Propagates unexpected filesystem exceptions not caught by the per-file parse guard.
        - Forbid:
          - Hidden paths (any path part starting with ".") are excluded from consideration.
        - Orders:
          - Candidate traversal is forced into sorted path order for determinism.
        - Locks: None.
        """
        manifest: Dict[str, Path] = {}
        if not self.nodes_dir.exists():
            return manifest

        # FIX: Deterministic sort to ensure stable graph hashes across platforms
        for path in sorted(self.nodes_dir.rglob("*"), key=str):
            if path.suffix.lower() != ".json":
                continue
            if any(part.startswith(".") for part in path.parts):
                continue

            try:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"⚠️  [LOADER] SKIPPING MALFORMED JSON: {path.name} -> {e}")
                continue

            if isinstance(data, dict):
                nid = data.get("id")
                if nid and isinstance(nid, str):
                    nid = nid.strip()
                    if nid in manifest:
                        raise DuplicateIDError(f"Duplicate Node ID '{nid}' in {path} vs {manifest[nid]}")
                    manifest[nid] = path.resolve()
                else:
                    # Helper assets allowed, just warn
                    print(f"⚠️  [LOADER] SKIPPING NON-NODE JSON (No 'id'): {path.name}")

        return manifest

class PhysicalLoader:
    """
    [ROLE]
    - Teleology: Provide the IO-bound entrypoint that turns on-disk node/config JSON into governance-validated `CodexNode` objects.
    - Mechanism: Index nodes -> read JSON -> inject `@node_path` -> resolve/merge config -> merge execution defaults -> delegate to governance.
    - Ownership: Owns `root`, `_indexer`, and `_manifest` (snapshot at init time).
    - Mutability: `_manifest` is not mutated after init; per-call payloads are constructed from on-disk reads.
    - Concurrency:
      - Locks: None.
      - Posture: Safe for concurrent reads of `manifest` copies; concurrent `load_*` performs parallel disk reads but is not serialized.
      - Forbid: Concurrent use with `inject_sys_path=True` when other threads mutate/assume `sys.path` ordering.
    - Couples: `system.core.governance` defines the authoritative node schema normalization and topology semantics.
    - When-needed: Open when the task needs the runtime-owned entrypoint for node discovery, config inheritance, or delegation into governance topology checks.
    - Escalates-to: system/core/governance.py::parse_node; system/core/governance.py::compute_waves
    """

    def __init__(self, root_dir: Union[str, Path], *, inject_sys_path: bool = True) -> None:
        """
        [ACTION]
        - Teleology: Initialize the physical loader, scanning the repository for nodes.
        - Mechanism: Validates root, optionally updates sys.path, and invokes `_NodeIndexer`.
        - Preconditions:
          - `root_dir` must exist and be a directory.
          - `inject_sys_path` must be an explicit opt-in to mutate interpreter import state.
        - Reads:
          - Filesystem under `<root_dir>/codex/nodes/` during manifest scan.
        - Writes:
          - `sys.path` prepended with `root_dir` when `inject_sys_path=True` and not already present.
        - Guarantee:
          - `self.root` is a resolved directory `Path`.
          - `self._manifest` is a snapshot mapping of discovered node ids to absolute JSON paths.
        - Fails:
          - Raises `LoaderError` if `root_dir` is invalid, scanning fails, or node ids collide.
        - Locks: None.
        - Orders: Manifest contents are deterministic due to sorted scan traversal.
        """
        try:
            self.root: Path = Path(root_dir).resolve()
            if not self.root.exists() or not self.root.is_dir():
                raise LoaderError(f"Invalid root_dir: {self.root}")

            # Explicit opt-in side effect
            if inject_sys_path and str(self.root) not in sys.path:
                sys.path.insert(0, str(self.root))

            self._indexer = _NodeIndexer(self.root)
            self._manifest: Dict[str, Path] = self._indexer.scan()

        except Exception as e:
            raise LoaderError(f"Loader init failed: {e}") from e

    # --- Public Accessors (New Standard) ---

    def get_manifest(self) -> Dict[str, Path]:
        """
        [ACTION]
        - Teleology: Expose the current node manifest.
        - Mechanism: Returns a dictionary copy of the internal manifest.
        - Preconditions: Loader must be initialized successfully.
        - Reads: `self._manifest`.
        - Writes: None.
        - Guarantee: Returns a shallow copy of the manifest (`node_id` -> `Path`).
        - Fails: None.
        - Orders: Copy preserves the current dict iteration order of `self._manifest`.
        - Locks: None.
        """
        return dict(self._manifest)

    def get_nodes_dir(self) -> Path:
        """
        [ACTION]
        - Teleology: Expose the resolved directory path for nodes.
        - Mechanism: Accesses the internal indexer's nodes directory.
        - Preconditions: Loader must be initialized successfully.
        - Reads: `self._indexer.nodes_dir`.
        - Writes: None.
        - Guarantee: Returns the resolved `codex/nodes` directory path.
        - Fails: None.
        - Orders: None.
        - Locks: None.
        """
        return self._indexer.nodes_dir

    @property
    def manifest(self) -> Dict[str, Path]:
        """
        [ACTION]
        - Teleology: Legacy property accessor for the node manifest.
        - Mechanism: Proxies to `get_manifest()`.
        - Preconditions: Loader must be initialized successfully.
        - Reads: `self._manifest`.
        - Writes: None.
        - Guarantee: Returns a shallow copy of the manifest (legacy accessor; safe copy).
        - Fails: None.
        - Orders: Copy preserves the current dict iteration order of `self._manifest`.
        - Locks: None.
        """
        return self.get_manifest()

    # --- Internal IO Helpers ---

    def _read_json(self, path: Path) -> Dict[str, Any]:
        """
        [ACTION]
        - Teleology: safely read and parse a JSON file into a dictionary.
        - Mechanism: `path.open()` context manager with `json.load()`.
        - Preconditions: `path` must be a readable JSON file.
        - Reads: Disk (`path`).
        - Writes: None.
        - Guarantee: Returns a dict representing the JSON object at `path`.
        - Forbid: JSON root that is not an object.
        - Fails: Raises `LoaderError` on read/parse errors or non-object JSON roots.
        - Orders: JSON key order is preserved as parsed by `json.load` (Python dict semantics).
        - Locks: None.
        """
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise LoaderError(f"JSON root must be an object: {path}")
            return data
        except Exception as e:
            raise LoaderError(f"Read failed {path}: {e}") from e

    def _read_json_any(self, path: Path) -> Any:
        """
        [ACTION]
        - Teleology: Read JSON content where the root may be any JSON value.
        - Mechanism: `path.open()` context manager with `json.load()`.
        - Preconditions: `path` must be a readable JSON file.
        - Reads: Disk (`path`).
        - Writes: None.
        - Guarantee: Returns parsed JSON value.
        - Fails: Raises `LoaderError` on read/parse errors.
        """
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise LoaderError(f"Read failed {path}: {e}") from e

    def _resolve_config_file(self, *, node_id: str, ref: str) -> Path:
        """
        [ACTION]
        - Teleology: Enforce strict path safety for config references.
        - Mechanism: Validates extension, absolute paths, traversal, and repo containment.
        - Preconditions: `ref` must be a string.
        - Rules:
          1. Must be repo-relative (relative to `self.root`).
          2. Must not be absolute.
          3. Must not contain `..` or attempt traversal.
          4. Must not use YAML.
        - Guarantee: Returns an absolute path that is strictly contained within `self.root`.
        - Fails: Raises `LoaderError` on any violation.
        """
        if not isinstance(ref, str):
            raise LoaderError(f"config_file ref must be string. Node: {node_id}")

        if ref.lower().endswith((".yaml", ".yml")):
            raise LoaderError(f"YAML forbidden in config_file. Node: {node_id}")

        p = Path(ref)
        if p.is_absolute():
            raise LoaderError(f"Absolute path forbidden in config_file: {ref}. Node: {node_id}")

        if ".." in p.parts:
            raise LoaderError(f"Traversal forbidden in config_file: {ref}. Node: {node_id}")

        target = (self.root / ref).resolve()

        # Containment Check
        try:
            target.relative_to(self.root)
        except ValueError:
            raise LoaderError(f"Config file escapes repo root: {ref}. Node: {node_id}")

        return target

    def _resolve_ref_file(self, *, node_id: str, key: str, ref: str) -> Path:
        """
        [ACTION]
        - Teleology: Resolve a generic `*_ref` JSON pointer with strict repo and namespace safety.
        - Mechanism: Enforce relative JSON path, forbid traversal/absolute paths, require `codex/refs/` prefix.
        - Preconditions: `ref` must be a string.
        - Guarantee: Returns absolute path contained under `self.root/codex/refs`.
        - Fails: Raises `LoaderError` on invalid shape/path.
        """
        if not isinstance(ref, str) or not ref.strip():
            raise LoaderError(f"{key} must be a non-empty string. Node: {node_id}")

        p = Path(ref.strip())
        if p.is_absolute():
            raise LoaderError(f"Absolute path forbidden in {key}: {ref}. Node: {node_id}")
        if ".." in p.parts:
            raise LoaderError(f"Traversal forbidden in {key}: {ref}. Node: {node_id}")
        if p.suffix.lower() != ".json":
            raise LoaderError(f"{key} must point to a .json file: {ref}. Node: {node_id}")

        normalized_ref = p.as_posix()
        if not normalized_ref.startswith("codex/refs/"):
            raise LoaderError(f"{key} must stay under codex/refs/: {ref}. Node: {node_id}")

        target = (self.root / normalized_ref).resolve()
        refs_root = (self.root / "codex" / "refs").resolve()
        try:
            target.relative_to(refs_root)
        except ValueError:
            raise LoaderError(f"{key} escapes codex/refs/: {ref}. Node: {node_id}")
        return target

    def _resolve_ref_pointers(self, *, node_id: str, payload: Any, seen: Optional[Set[str]] = None) -> Any:
        """
        [ACTION]
        - Teleology: Inline config reference pointers (`*_ref`) before tool execution.
        - Mechanism: Recursive walk over dict/list values; loads JSON from `codex/refs`, inserts under stem key.
        - Rules:
          1. Only keys ending with `_ref` are treated as references.
          2. `*_ref` keys are removed after resolution.
          3. If stem key already exists, explicit value wins and ref pointer is discarded.
          4. Nested references are resolved recursively.
          5. Cyclic references are forbidden.
        - Guarantee: Returns a payload with `*_ref` pointers resolved/inlined.
        - Fails: Raises `LoaderError` on invalid/missing refs or recursive pointers.
        """
        seen_refs = seen or set()

        if isinstance(payload, dict):
            resolved: Dict[str, Any] = {}
            for key, value in payload.items():
                if isinstance(key, str) and key.endswith("_ref"):
                    stem = key[:-4]
                    ref_path = self._resolve_ref_file(node_id=node_id, key=key, ref=value)
                    if not ref_path.exists():
                        raise LoaderError(f"Missing {key}: {ref_path} for node {node_id}")
                    ref_rel = ref_path.relative_to(self.root).as_posix()
                    if ref_rel in seen_refs:
                        raise LoaderError(f"Recursive *_ref cycle detected for {ref_rel}. Node: {node_id}")
                    loaded = self._read_json_any(ref_path)
                    inlined = self._resolve_ref_pointers(
                        node_id=node_id,
                        payload=loaded,
                        seen=seen_refs | {ref_rel},
                    )
                    if stem not in payload:
                        resolved[stem] = inlined
                    continue

                resolved[key] = self._resolve_ref_pointers(
                    node_id=node_id,
                    payload=value,
                    seen=seen_refs,
                )
            return resolved

        if isinstance(payload, list):
            return [
                self._resolve_ref_pointers(node_id=node_id, payload=item, seen=seen_refs)
                for item in payload
            ]

        return payload

    def _inject_tags(self, instruction: str, node_path: Path) -> str:
        """
        [ACTION]
        - Teleology: Inject the `@node_path` metadata tag into the instruction string.
        - Mechanism: Regex replacement to remove existing tags, then prepend the new tag.
        - Guarantee: Ensures `instruction` begins with a single `@node_path:<node_path>` line.
        """
        try:
            # 1. Scrub ALL existing lines starting with @node_path: (clean slate)
            # Match start-of-line @node_path: ... end-of-line + optional newline
            cleaned = re.sub(r'^@node_path:.*$(\n)?', '', instruction, flags=re.MULTILINE)
            
            # 2. Prepend the single source of truth
            tag = f"@node_path:{node_path}"
            suppression = "[SYSTEM CONSTRAINT] Output ONLY the contracted format. Do NOT greet, ask questions, hedge, self-assess, or offer additional work. No preamble. No sign-off."
            return f"{tag}\n{suppression}\n{cleaned}"
        except Exception as e:
            raise LoaderError(f"Tag injection failed: {e}") from e

    # --- Contract Resolution ---

    def _resolve_contracts(self, instruction: str) -> str:
        """
        [ACTION]
        - Teleology: Inline contract bodies into instruction text at load time.
        - Mechanism: Regex-scan for `See Contract: codex/contracts/X.md` references,
          read the file, replace the reference line with the contract body wrapped
          in [CONTRACT]/[/CONTRACT] delimiters.
        - Reads: Contract .md files under `codex/contracts/` (cached per loader instance).
        - Writes: None (pure string transform).
        - Guarantee: Every valid `See Contract:` reference is replaced with inline text.
          Invalid/missing refs are left as-is with a warning printed.
        """
        if not hasattr(self, "_contract_cache"):
            self._contract_cache: Dict[str, str] = {}

        def _replace(match: re.Match) -> str:
            raw_ref = str(match.group(1) or "").strip()
            # CONTRACT_REF_RE currently captures the filename only.
            # Normalize to canonical repo-relative path for safe resolution.
            ref = raw_ref if raw_ref.startswith("codex/contracts/") else f"codex/contracts/{Path(raw_ref).name}"
            if ref in self._contract_cache:
                body = self._contract_cache[ref]
            else:
                p = Path(ref)
                if p.is_absolute() or ".." in p.parts:
                    print(f"⚠️  [LOADER] UNSAFE contract ref skipped: {ref}")
                    return match.group(0)
                target = (self.root / ref).resolve()
                try:
                    target.relative_to(self.root)
                except ValueError:
                    print(f"⚠️  [LOADER] Contract ref escapes repo: {ref}")
                    return match.group(0)
                if not target.exists():
                    print(f"⚠️  [LOADER] Contract file not found: {ref}")
                    return match.group(0)
                try:
                    body = target.read_text(encoding="utf-8").strip()
                    self._contract_cache[ref] = body
                except Exception as e:
                    print(f"⚠️  [LOADER] Contract read failed {ref}: {e}")
                    return match.group(0)
            fname = Path(ref).name
            return f"[CONTRACT: {fname}]\n{body}\n[/CONTRACT]"

        return CONTRACT_REF_RE.sub(_replace, instruction)

    def _resolve_map_injections(self, node_id: str, instruction: str) -> str:
        """
        [ACTION]
        - Teleology: Append map-based contract and dossier payloads to the node instruction.
        - Mechanism: Read injection_map and dossier_map arrays from codex/contracts/contract_config.json.
          For each entry whose 'node_ids' list includes node_id, resolve the referenced file and append
          its content to instruction in stable, deterministic order.
        - Contract file entries: injected as [CONTRACT: filename]...body...[/CONTRACT].
        - Dossier file entries: injected as [DOSSIER: filename]...json.dumps(payload, indent=2)...[/DOSSIER].
        - Fallback: If contract_config.json is absent, has no maps, or a mapped file is missing/malformed,
          a warning is printed and execution continues. Never raises an exception.
        - Non-goal: Replace the See Contract: regex fallback path — that path remains active.
        """
        if not hasattr(self, "_contract_config_cache"):
            cfg_path = (self.root / "codex" / "contracts" / "contract_config.json").resolve()
            try:
                with cfg_path.open("r", encoding="utf-8") as f:
                    self._contract_config_cache: Dict[str, Any] = json.load(f)
            except Exception:
                self._contract_config_cache = {}

        cfg = self._contract_config_cache
        appended: List[str] = []

        # --- injection_map: immutable contract .md files ---
        for entry in cfg.get("injection_map") or []:
            if not isinstance(entry, dict):
                continue
            node_ids = entry.get("node_ids") or []
            if not isinstance(node_ids, list) or node_id not in node_ids:
                continue
            file_ref = entry.get("file") or ""
            if not file_ref:
                continue
            fpath = (self.root / file_ref).resolve()
            try:
                fpath.relative_to(self.root)
            except ValueError:
                print(f"\u26a0\ufe0f  [LOADER] injection_map file escapes repo root: {file_ref}")
                continue
            if not fpath.exists():
                print(f"\u26a0\ufe0f  [LOADER] injection_map file not found: {file_ref}")
                continue
            try:
                body = fpath.read_text(encoding="utf-8").strip()
                fname = fpath.name
                appended.append(f"[CONTRACT: {fname}]\n{body}\n[/CONTRACT]")
            except Exception as exc:
                print(f"\u26a0\ufe0f  [LOADER] injection_map read failed {file_ref}: {exc}")

        # --- dossier_map: mutable dossier .json files ---
        for entry in cfg.get("dossier_map") or []:
            if not isinstance(entry, dict):
                continue
            node_ids = entry.get("node_ids") or []
            if not isinstance(node_ids, list) or node_id not in node_ids:
                continue
            file_ref = entry.get("file") or ""
            if not file_ref:
                continue
            fpath = (self.root / file_ref).resolve()
            try:
                fpath.relative_to(self.root)
            except ValueError:
                print(f"\u26a0\ufe0f  [LOADER] dossier_map file escapes repo root: {file_ref}")
                continue
            if not fpath.exists():
                print(f"\u26a0\ufe0f  [LOADER] dossier_map file not found: {file_ref}")
                continue
            try:
                with fpath.open("r", encoding="utf-8") as f:
                    payload = json.load(f)
                fname = fpath.name
                appended.append(f"[DOSSIER: {fname}]\n{json.dumps(payload, indent=2)}\n[/DOSSIER]")
            except Exception as exc:
                print(f"\u26a0\ufe0f  [LOADER] dossier_map read failed {file_ref}: {exc}")

        if appended:
            instruction = instruction.rstrip("\n") + "\n\n" + "\n\n".join(appended) + "\n"
        return instruction

    def _resolve_compiled_dossier_bundle(self) -> str:
        """
        [ACTION]
        - Teleology: Provide a single Markdown dossier bundle for reasoning prompt injection.
        - Mechanism: Prefer the compiled builder artifact; fall back to live rendering from source dossiers.
        - Guarantee: Returns Markdown text or an empty string when dossiers are unavailable.
        - Fails: None.
        """
        compiled_path = (self.root / "codex" / "derived" / "compiled" / "dossiers.md").resolve()
        if compiled_path.exists():
            try:
                return compiled_path.read_text(encoding="utf-8").strip()
            except Exception:
                pass
        if not list_dossier_paths(self.root):
            return ""
        try:
            return render_dossier_markdown(self.root).strip()
        except Exception:
            return ""

    def _inject_compiled_dossiers(self, raw: Dict[str, Any]) -> None:
        """
        [ACTION]
        - Teleology: Append the active dossier Markdown bundle to reasoning-node instructions.
        - Mechanism: Inject a single `[DOSSIER_BUNDLE]...[/DOSSIER_BUNDLE]` block when dossiers exist.
        - Guarantee: Tool nodes are left untouched; duplicate injections are suppressed.
        - Fails: None.
        """
        if raw.get("type") == "tool":
            return
        instruction = raw.get("instruction")
        if not isinstance(instruction, str) or "[DOSSIER_BUNDLE]" in instruction:
            return
        dossier_bundle = self._resolve_compiled_dossier_bundle()
        if not dossier_bundle:
            return
        raw["instruction"] = (
            instruction.rstrip("\n")
            + "\n\n[DOSSIER_BUNDLE]\n"
            + dossier_bundle
            + "\n[/DOSSIER_BUNDLE]\n"
        )

    # --- Core API (The Pivot) ---

    def load_node(self, node_id: str) -> CodexNode:
        """
        [ACTION]
        - Teleology: Hydrate a single node with strict config merging and legacy support.
        - Mechanism:
          1. Strict Path Resolution & Group Resolution.
          2. Tag Injection (Regex).
          3. Legacy Config Extraction (`config.config_file` -> `config_file`).
          4. Config Unwrapping (`type="config"`).
          5. Deep Merge (`base` + `inline`).
          6. Governance Handoff.
        - When-needed: Open when a single node is failing to load or when config inheritance, ref inlining, or group stamping needs exact runtime behavior.
        - Escalates-to: system/core/governance.py::parse_node; system/core/analysis.py::analyze_python_module
        """
        try:
            if node_id not in self._manifest:
                raise LoaderError(f"Node ID not found: '{node_id}'")

            path = self._manifest[node_id]
            raw = self._read_json(path)

            # --- STEP 1.3 CHANGE: Strict Relative Path & Group Stamping ---

            # 1. Strict Relative Path (No Absolute Fallback)
            try:
                rel_path = path.relative_to(self.root)
            except ValueError:
                raise LoaderError(f"Node path escapes repo root: {path}")

            # 2. Group Resolution
            # Prefer the node's explicit group field; only fall back to folder shape
            # for older nodes that do not declare a group.
            try:
                nodes_rel = path.relative_to(self.get_nodes_dir())
                fallback_group = nodes_rel.parts[0] if nodes_rel.parts else "root"
            except (ValueError, IndexError):
                fallback_group = "root"
            raw_group = raw.get("group")
            group = str(raw_group).strip() if isinstance(raw_group, str) and raw_group.strip() else fallback_group

            # 3. Tag Injection (FIXED: REGEX & RELATIVE ONLY)
            if isinstance(raw.get("instruction"), str):
                raw["instruction"] = self._inject_tags(raw["instruction"], rel_path)

            # 3.5. Contract Resolution (Inline contract bodies)
            if isinstance(raw.get("instruction"), str):
                raw["instruction"] = self._resolve_contracts(raw["instruction"])

            # 3.6. Map Injection (contract + dossier payloads from injection_map / dossier_map)
            if isinstance(raw.get("instruction"), str):
                raw["instruction"] = self._resolve_map_injections(node_id, raw["instruction"])

            # 3.7. Compiled dossier bundle injection (reasoning nodes only)
            self._inject_compiled_dossiers(raw)

            # 4. Config Inheritance
            inline_config = raw.get("config", {}) or {}
            cfg_ref = raw.get("config_file")

            # Legacy check inside config block
            if isinstance(inline_config, dict):
                legacy_ref = inline_config.pop("config_file", None)
                cfg_ref = cfg_ref or legacy_ref

            inline_overrides = copy.deepcopy(inline_config) if isinstance(inline_config, dict) else {}
            final_config = inline_config
            if cfg_ref:
                # STRICT RESOLUTION (Repo-Relative)
                base_path = self._resolve_config_file(node_id=node_id, ref=cfg_ref)

                if base_path.exists():
                    base_config = self._read_json(base_path)

                    # --- UNWRAPPER FIX (Unified Standard) ---
                    # If the config file is a "Config Node" (type=config), extract the payload.
                    if isinstance(base_config, dict) and base_config.get("type") == "config":
                        base_config = base_config.get("data", {})
                    # ----------------------------------------

                    final_config = deep_merge(base_config, inline_config)
                else:
                    raise LoaderError(f"Missing config_file: {base_path} for node {node_id}")
            final_config = self._resolve_ref_pointers(node_id=node_id, payload=final_config)
            try:
                merged_hash = hashlib.sha256(
                    json.dumps(final_config, sort_keys=True, ensure_ascii=True).encode("utf-8")
                ).hexdigest()[:12]
            except Exception as e:
                raise LoaderError(f"Config hash failed for node {node_id}: {e}") from e

            # 5. Execution Defaults
            exec_cfg = raw.get("execution", {}) or {}
            # --- FIX: Deepcopy to prevent memory aliasing of mutable defaults across nodes ---
            base_exec = copy.deepcopy(DEFAULT_EXECUTION_CONFIG)
            merged_exec = deep_merge(base_exec, exec_cfg)

            # 6. Construct Payload
            payload = dict(raw)
            payload["id"] = node_id
            payload["config"] = final_config
            payload["execution"] = merged_exec
            payload["group"] = group  # --- STAMPING GROUP ---
            payload["config_ref"] = cfg_ref if isinstance(cfg_ref, str) else None
            payload["inline_overrides"] = inline_overrides
            payload["merged_hash"] = merged_hash
            payload.pop("config_file", None)  # Clean up top-level

            # 7. GOVERNANCE HANDOFF
            return gov_parse_node(payload)

        except Exception as e:
            raise LoaderError(f"Load node failed '{node_id}': {e}") from e

    def load_all_nodes(self) -> Dict[str, CodexNode]:
        """
        [ACTION]
        - Teleology: Load all nodes in the manifest.
        - Mechanism: Iterates sorted manifest keys and calls `load_node`.
        - Order: Sorted by node ID.
        - When-needed: Open when a caller needs the full in-memory graph that the engine and topology validators consume.
        - Escalates-to: system/core/governance.py::validate_graph; system/core/engine.py::GodModeEngine.run
        """
        graph = {}
        for nid in sorted(self._manifest.keys()):
            graph[nid] = self.load_node(nid)
        return graph

    # --- Delegated Topology ---

    def compute_waves(self, graph: Optional[Dict[str, CodexNode]] = None) -> List[List[str]]:
        """
        [ACTION]
        - Teleology: Compute the topological waves of execution for the graph.
        - Mechanism: Delegate to `system.core.governance.compute_waves`.
        - When-needed: Open when loader callers want wave ordering while staying on the loader surface rather than jumping straight into governance code.
        - Escalates-to: system/core/governance.py::compute_waves; system/core/engine.py::GodModeEngine.run
        """
        if graph is None:
            graph = self.load_all_nodes()
        try:
            return gov_compute_waves(graph)
        except ValueError as e:
            raise LoaderError(f"Topology error: {e}") from e

    def validate_topology(self, graph: Optional[Dict[str, CodexNode]] = None) -> List[ValidationIssue]:
        """
        [ACTION]
        - Teleology: Validate the graph structure and consistency.
        - Mechanism: Delegate to `system.core.governance.validate_topology`.
        - When-needed: Open when a loader caller needs missing-dependency or cycle findings without re-implementing graph validation.
        - Escalates-to: system/core/governance.py::validate_graph; system/core/engine.py::GodModeEngine.run
        """
        if graph is None:
            graph = self.load_all_nodes()
        return gov_validate_topology(graph)

    # --- Tool Import ---

    def import_tool(self, dotted_path: str) -> ModuleType:
        """
        [ACTION]
        - Teleology: Import a tool module dynamically.
        - Mechanism: Wraps `importlib.import_module` with error handling.
        - When-needed: Open when a tool node is failing during dynamic import and the caller needs the loader-owned import boundary.
        - Escalates-to: system/core/engine.py; system/core/governance.py::parse_node
        """
        try:
            return importlib.import_module(dotted_path)
        except Exception as e:
            raise LoaderError(f"Tool import failed '{dotted_path}': {e}") from e
