"""
[PURPOSE]
- Teleology: Act as the 'Source Surgeon' for the repository.
- Mechanism: Observe file scopes into grounded JSON and apply whitelisted atomic edits through a Ghost Filesystem.
- Guarantee: Each operation is syntax-validated before commit.

[INTERFACE]
- Exports: `run(config) -> dict`.
  - Inputs:
    - `mode`: `observe` | `apply`.
    - `plan`: observe (`targets` or `groups`) or apply (`operations`).
    - Observe plans also accept optional `wait_notes` (global note) and `prompt` (injectable guidance text).
    - Grouped observe plans may also provide `meta_instruction` to append custom markdown guidance in each dump folder.
    - Grouped observe plans may set `context_merge_mode` to `group_only` to keep plan-level context out of per-group dumps.
  - Observe-only optional formatting flags:
    - `print_format`: `raw` (default legacy), `python`/`1`, or `json`/`2`.
    - `print_shape`: `preserve_shape`/`2` (default) or `compact`/`1`.
    - `print_options`: optional object alias with `{format, shape}`.
  - `dry_run`: (bool) if true, do not write to disk.
  - `validate_only`: (bool) run schema + preflight validation only; no writes.
  - `capture_diffs`: (bool) include unified diffs in the result.

[FLOW]
- Observe: read requested targets (optionally injecting context files) and return a JSON structure (or write grouped dumps).
- Apply: validate ops against `codex/standards/std_apply.json` -> apply ops sequentially to Ghost FS -> after each op, validate Python syntax for touched files -> if not `dry_run`, commit mutated files to disk.

[DEPENDENCIES]
- Required:
  - codex/standards/std_apply.json: defines allowed operations and required fields.
- Optional:
  - system.lib.utils.resolve_root: repository root resolution (fallback included).
  - system.core.analysis.analyze_python_module: richer observation/compliance extraction when available.

[CONSTRAINTS]
- Forbid: executing any op not listed in `std_apply.json` (or its fallback allowlist).
- Atomicity: stage edits in Ghost FS; only write to disk after validation.
- Determinism: given identical inputs and repo state, produced diffs/logs are stable.
- When-needed: Open when a tooling flow needs the canonical observe/apply substrate, snapshot rollback path, or target-routing summary before mutating files.
- Escalates-to: codex/standards/std_apply.json; system/core/analysis.py; tools/meta/review.py
- Navigation-group: meta_tooling

"""

import sys
import os
import json
import ast
import difflib
import re
import textwrap
import hashlib
from pprint import pformat
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Dict, List, Any, Optional, Tuple, Union

from system.lib.markdown_routing import (
    apply_reference_to_text,
    extract_observe_artifact_payload,
    extract_section_block,
    find_section_bounds,
    markdown_kind,
    normalize_repo_relative_path,
    normalize_route_config,
    parse_frontmatter,
    resolve_reference_artifact_target_family,
    resolve_reference_maps,
    split_frontmatter,
)
from system.lib.observe_runtime import normalize_context_merge_mode, resolve_group_evidence_contract

# --- INTERNAL DEPENDENCIES ---
try:
    from system.lib.utils import resolve_root
except ImportError:
    def resolve_root(hint=None, max_hops=24):
        current = Path.cwd().resolve()
        for _ in range(max_hops):
            if (current / "master_config.json").exists(): return current
            if current.parent == current: break
            current = current.parent
        return Path.cwd().resolve()

try:
    from system.core.analysis import analyze_python_module
except ImportError:
    analyze_python_module = None

try:
    from codex.standards.std_python import PYTHON_STANDARD
except ImportError:
    PYTHON_STANDARD = {}

# Portable `__meta["root"]` for observe dumps and logs — not a host absolute path (safe to paste/share).
OBSERVE_DUMP_REPO_ROOT_MARKER = "."


# Python scope-selector grammar + catalog now live in `system/lib/python_scope_query.py`.
# These re-imports preserve backwards compatibility for in-module callers that referenced
# `_python_scope_catalog_from_tree` and for the lazy attribute shim in
# `tools/meta/apply/__init__.py:90` which resolves `normalize_python_scope_selector` via
# `getattr` against this module. Do not duplicate the logic here; extend the source module.
from system.lib.python_scope_query import (  # noqa: E402  (post-import alias for shim compatibility)
    _scope_token,
    normalize_python_scope_selector,
    python_scope_catalog_from_tree as _python_scope_catalog_from_tree,
    python_scope_resolve,
)


# --- CUSTOM EXCEPTION ---
class ApplyError(Exception):
    """
    [ROLE]
    - Teleology: Structured exception that captures a single operation failure (index + op payload).
    - Ownership: Raised by `SourceSurgeon.apply_plan`; caught by `run()` to return a failure envelope.
    - Mutability: Immutable after construction.
    - Concurrency: Safe to pass across threads/processes (serializable primitives only).
    
    """
    def __init__(
        self,
        message: str,
        op_index: int = -1,
        op: Dict = None,
        detail: str = "",
        completed_ops: List[str] = None,
        touched_files: List[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.op_index = op_index
        self.op = op
        self.detail = detail
        self.completed_ops = completed_ops or []
        self.touched_files = touched_files or []

# --- CORE LOGIC ---
class SourceSurgeon:
    """
    [ROLE]
    - Teleology: Execute observe/apply plans against a repository root using an in-memory Ghost FS.
    - Ownership: Owns resolved root, `std_apply` snapshot, allowed-ops set, Ghost FS staging map, and timestamp for one invocation.
    - Mutability: Ghost FS mutates during apply; disk is only mutated on commit (when `dry_run` is false).
    - Concurrency: Not thread-safe; one instance per execution.
    - When-needed: Open when a caller needs the object that owns Ghost FS state, apply-plan compilation, observation dumps, and live commit behavior.
    - Escalates-to: tools/meta/apply.py::run; codex/standards/std_apply.json
    - Navigation-group: meta_tooling
    
    """
    _CONTEXT_SUPPORTED_EXTENSIONS = {
        ".md", ".markdown", ".txt", ".json", ".yaml", ".yml",
        ".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".html",
        ".toml", ".ini", ".cfg", ".csv", ".tsv", ".sql", ".xml", ".rst"
    }
    _CONTEXT_SKIP_DIRS = {
        ".git", ".svn", ".hg", "__pycache__", "node_modules", "venv",
        ".venv", ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build"
    }
    _CONTEXT_MAX_FILES_PER_DIR = 300
    _CONTEXT_MAX_CHARS_PER_FILE = 500_000
    _CONTEXT_MAX_TOTAL_CHARS = 8_000_000
    _OBSERVE_READING_GUIDE = (
        "This file is a grouped observe dump. Structure: __meta (generation metadata), "
        "__toc (file index with types/sizes), __context (injected reference docs), "
        "observations[] (one per file, each with: file, scope, exists, notes, content, "
        "compliance). Start with __toc to understand scope, then read observations by index."
    )

    def __init__(self, root_hint: Optional[str] = None):
        self.root = resolve_root(root_hint)
        self.ghost_fs: Dict[str, str] = {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
        
        # Load Operations Standard
        self.std_apply = self._load_standard("std_apply.json")
        self.allowed_ops = set(self.std_apply.get("allowed_ops", {}).keys())
        self.target_routing = self._normalize_target_routing(self.std_apply.get("target_routing"))
        
        # Bootstrap Fallback: If standard missing, use defaults
        if not self.allowed_ops:
            self.allowed_ops = {
                "replace_block", "replace_function", "insert_function",
                "add_import", "inject_tag", "overwrite", "create_file",
                "update_docstring", "patch_map", "reference_artifact",
                "append_section", "replace_section"
            }

    def _apply_snapshots_dir(self) -> Path:
        return self.root / "tools" / "meta" / "apply" / "snapshots"

    def _new_apply_snapshot_id(self) -> str:
        ts = (
            datetime.now(timezone.utc)
            .isoformat()
            .replace(":", "-")
            .replace(".", "-")
            .replace("+00:00", "Z")
        )
        return f"APPLY_{ts}_{os.urandom(3).hex()}"

    def _snapshot_group_slug(self, group_label: str, *, group_index: int) -> str:
        raw = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(group_label or "").strip()).strip("._")
        return f"{group_index:03d}_{raw or 'group'}"

    def _write_live_apply_snapshot(
        self,
        original_states: Dict[str, Dict[str, Any]],
        *,
        snapshot_id: Optional[str] = None,
        group_original_states: Optional[Dict[str, Dict[str, Dict[str, Any]]]] = None,
        group_order: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if not original_states:
            return {}

        resolved_snapshot_id = str(snapshot_id or "").strip() or self._new_apply_snapshot_id()
        snapshot_root = self._apply_snapshots_dir() / resolved_snapshot_id
        files_root = snapshot_root / "files"
        entries: List[Dict[str, Any]] = []
        group_entries: List[Dict[str, Any]] = []

        for target in sorted(original_states):
            state = original_states[target]
            existed_before = bool(state.get("existed_before"))
            content = str(state.get("content") or "")
            entry: Dict[str, Any] = {
                "target": target,
                "existed_before": existed_before,
                "snapshot_file": None,
                "sha256": None,
            }
            if existed_before:
                snapshot_file = files_root / target
                snapshot_file.parent.mkdir(parents=True, exist_ok=True)
                snapshot_file.write_text(content, encoding="utf-8")
                entry["snapshot_file"] = str(snapshot_file.relative_to(self.root))
                entry["sha256"] = hashlib.sha256(content.encode("utf-8")).hexdigest()
            entries.append(entry)

        ordered_groups = [
            str(label).strip()
            for label in (group_order or [])
            if str(label).strip()
        ]
        seen_groups: set[str] = set(ordered_groups)
        for label in (group_original_states or {}):
            clean = str(label).strip()
            if clean and clean not in seen_groups:
                ordered_groups.append(clean)
                seen_groups.add(clean)

        for group_index, group_label in enumerate(ordered_groups):
            states = (group_original_states or {}).get(group_label, {})
            if not isinstance(states, dict):
                continue
            group_slug = self._snapshot_group_slug(group_label, group_index=group_index)
            for target in sorted(states):
                state = states[target]
                existed_before = bool(state.get("existed_before"))
                content = str(state.get("content") or "")
                entry = {
                    "target": target,
                    "group_label": group_label,
                    "group_index": group_index,
                    "snapshot_file": None,
                    "existed_before": existed_before,
                    "sha256": None,
                }
                if existed_before:
                    snapshot_file = snapshot_root / "groups" / group_slug / "files" / target
                    snapshot_file.parent.mkdir(parents=True, exist_ok=True)
                    snapshot_file.write_text(content, encoding="utf-8")
                    entry["snapshot_file"] = str(snapshot_file.relative_to(self.root))
                    entry["sha256"] = hashlib.sha256(content.encode("utf-8")).hexdigest()
                group_entries.append(entry)

        manifest = {
            "snapshot_id": resolved_snapshot_id,
            "created_at": self.timestamp,
            "root": str(self.root),
            "entry_count": len(entries),
            "entries": entries,
            "group_order": ordered_groups,
            "group_entry_count": len(group_entries),
            "group_entries": group_entries,
        }
        snapshot_root.mkdir(parents=True, exist_ok=True)
        manifest_path = snapshot_root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        return {
            "snapshot_id": resolved_snapshot_id,
            "snapshot_manifest": str(manifest_path.relative_to(self.root)),
            "rollback_ready": True,
            "entry_count": len(entries),
            "group_order": ordered_groups,
            "group_entry_count": len(group_entries),
        }

    def _load_standard(self, filename: str) -> Dict[str, Any]:
        """Loads a standard JSON from codex/standards/"""
        try:
            # FIXED: Point to the correct standards directory
            path = self.root / "codex/standards" / filename
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _normalize_print_format(self, value: Any) -> str:
        token = str(value).strip().lower() if value is not None else ""
        if token in {"json", "2"}:
            return "json"
        if token in {"python", "py", "1"}:
            return "python"
        return "raw"

    def _normalize_print_shape(self, value: Any) -> str:
        token = str(value).strip().lower() if value is not None else ""
        if token in {"compact", "compressed", "inline", "minified", "minify", "flattened", "1"}:
            return "compact"
        if token in {"preserve_shape", "preserve", "full", "pretty", "multiline", "expanded", "2"}:
            return "preserve_shape"
        return "preserve_shape"

    def _compact_text(self, content: str) -> str:
        lines = [line.rstrip() for line in content.splitlines()]
        compact_lines: List[str] = []
        blank_streak = 0
        for line in lines:
            if line.strip():
                blank_streak = 0
                compact_lines.append(line)
                continue
            blank_streak += 1
            if blank_streak <= 1:
                compact_lines.append("")
        result = "\n".join(compact_lines).strip()
        if content.endswith("\n") and result:
            result += "\n"
        return result

    def _compact_python_source(self, content: str) -> str:
        try:
            compact = ast.unparse(ast.parse(content))
            if content.endswith("\n"):
                compact += "\n"
            return compact
        except Exception:
            return self._compact_text(content)

    def _serialize_json(self, payload: Any, shape: str) -> str:
        if shape == "compact":
            return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _detect_language(self, rel_path: str) -> str:
        suffix = Path(rel_path).suffix.lower()
        if suffix in {".py", ".pyi"}:
            return "python"
        if suffix == ".json":
            return "json"
        if suffix in {".ts", ".tsx"}:
            return "typescript"
        if suffix in {".md", ".markdown"}:
            return "markdown"
        return "text"

    def _extract_symbols(self, content: str, rel_path: str) -> Optional[List[str]]:
        suffix = Path(rel_path).suffix.lower()
        if suffix not in {".py", ".pyi"}:
            return None
        try:
            tree = ast.parse(content)
        except Exception:
            return None

        symbols: List[str] = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                symbols.append(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.append(f"{node.name}()")
        return symbols

    def _observe_symbol_limits(self) -> Tuple[int, int]:
        raw = PYTHON_STANDARD.get("documentation_tree") if isinstance(PYTHON_STANDARD, dict) else {}
        if not isinstance(raw, dict):
            raw = {}
        observe_limit = int(raw.get("observe_symbol_preview_count") or 32)
        toc_limit = int(raw.get("observe_toc_symbol_preview_count") or min(observe_limit, 12))
        return max(4, observe_limit), max(4, toc_limit)

    def _compress_symbols(
        self,
        symbols: Optional[List[str]],
        *,
        limit: int,
        focus_name: str = "",
    ) -> Tuple[Optional[List[str]], int, bool]:
        if symbols is None:
            return None, 0, False
        unique: List[str] = []
        for item in symbols:
            token = str(item or "").strip()
            if not token or token in unique:
                continue
            unique.append(token)
        total = len(unique)
        if total <= limit:
            return unique, total, False
        preview: List[str] = []
        target_tokens = {focus_name, f"{focus_name}()"} if focus_name else set()
        for item in unique:
            if item in target_tokens:
                preview.append(item)
                break
        for item in unique:
            if item in preview:
                continue
            preview.append(item)
            if len(preview) >= limit:
                break
        return preview, total, True

    def _build_observe_toc(self, observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        toc: List[Dict[str, Any]] = []
        _observe_limit, toc_limit = self._observe_symbol_limits()
        for idx, obs in enumerate(observations):
            compliance = obs.get("compliance")
            compliant = None
            if isinstance(compliance, dict):
                value = compliance.get("is_compliant")
                if isinstance(value, bool):
                    compliant = value
            symbol_preview, symbol_count, symbol_truncated = self._compress_symbols(
                obs.get("symbols"),
                limit=toc_limit,
                focus_name=str(obs.get("name") or "").strip(),
            )

            toc.append({
                "i": idx,
                "file": obs.get("file"),
                "lang": obs.get("language"),
                "lines": obs.get("line_count"),
                "bytes": obs.get("byte_count"),
                "symbols": symbol_preview,
                "symbol_count": symbol_count or None,
                "symbols_truncated": symbol_truncated or None,
                "compliant": compliant,
            })
        return toc

    def _build_group_meta_instruction_markdown(
        self,
        *,
        dump_dir: str,
        total_groups: int,
        total_files: int,
        plan_notes: Any,
        wait_notes: Any,
        injected_prompt: Any,
        meta_instruction: Any = None,
    ) -> str:
        """
        Builds a reusable instruction card for grouped observe dump consumers.
        The card is intentionally general but enforces a deep-read, evidence-first posture.
        """
        plan_notes_text = str(plan_notes or "").strip()
        wait_notes_text = str(wait_notes or "").strip()
        prompt_text = str(injected_prompt or "").strip()
        meta_instruction_text = str(meta_instruction or "").strip()
        global_note = wait_notes_text or plan_notes_text or "No global note was provided in this plan."
        prompt_label = prompt_text or "Not specified"

        lines = [
            "# Observe Dump Meta Instruction",
            "",
            "Use this instruction whenever you respond using files from this dump folder.",
            "",
            "## Core Directive",
            "Read the attached dump file deeply before writing anything. Do not skim.",
            "Use evidence from the attached material, not assumptions or memory.",
            "Return a complete, high-density response, not a short summary.",
            "Do not ask clarifying questions. Make reasonable assumptions and continue.",
            "",
            "## Response Contract",
            "Separate facts, inferences, and unknowns.",
            "Cite non-trivial claims with file path plus symbol or file:line evidence when available.",
            "Prioritize contradictions, risks, and decision-critical details over generic commentary.",
            "If the dump contains required output blocks, follow them exactly and in order.",
            "",
            "## Global Note (From Plan)",
            global_note,
            "",
            "## Prompt Tag (From Plan)",
            prompt_label,
            "",
            "## Dump Context",
            f"- dump_dir: `{dump_dir}`",
            f"- total_groups: `{total_groups}`",
            f"- total_files: `{total_files}`",
            "",
            "## Minimum Quality Bar",
            "The response must be operationally useful for next-step decisions without follow-up prompting.",
            "Prefer concrete, testable statements over abstract phrasing.",
            "",
        ]

        if meta_instruction_text:
            lines.extend([
                "## Additional Operator Directive",
                meta_instruction_text,
                "",
            ])

        return "\n".join(lines)

    def _format_observed_content(self, rel_path: str, content: str, print_format: str, print_shape: str) -> str:
        suffix = Path(rel_path).suffix.lower()
        parsed_json = None
        if suffix == ".json":
            try:
                parsed_json = json.loads(content)
            except Exception:
                parsed_json = None

        if print_format == "json":
            payload = parsed_json if parsed_json is not None else content
            return self._serialize_json(payload, print_shape)

        if print_format == "python":
            if parsed_json is not None:
                if print_shape == "compact":
                    return repr(parsed_json)
                return pformat(parsed_json, width=100, sort_dicts=False)
            if suffix in {".py", ".pyi"} and print_shape == "compact":
                return self._compact_python_source(content)
            if print_shape == "compact":
                return self._compact_text(content)
            return content

        # raw mode (legacy-compatible)
        if print_shape == "compact":
            if parsed_json is not None:
                return self._serialize_json(parsed_json, "compact")
            if suffix in {".py", ".pyi"}:
                return self._compact_python_source(content)
            return self._compact_text(content)
        return content

    def _format_context_map(self, context_data: Dict[str, str], print_format: str, print_shape: str) -> Dict[str, str]:
        if not context_data:
            return context_data

        output: Dict[str, str] = {}
        for key, value in context_data.items():
            if not isinstance(value, str):
                output[key] = value
                continue
            if key.startswith("__context_dir__:") or value.startswith("[ERROR]") or value.startswith("[INFO]") or value.startswith("[WARN]"):
                output[key] = value
                continue
            output[key] = self._format_observed_content(key, value, print_format, print_shape)
        return output

    # --- PLAN NORMALIZATION ---
    def _normalize_plan(self, plan: Dict[str, Any], mode: str) -> Dict[str, Any]:
        """
        [ACTION]
        - Teleology: Detect and correct common plan-wrapping mistakes before execution.
        - Mechanism: Checks for payloads buried under documentation keys like 'input_schema'
          or 'plan' (double-wrapped). Hoists the real payload to top level.
        - Fails: None (returns plan unchanged if no correction needed).
        - Guarantee: The returned dict has runtime keys (targets/groups/operations) at the top level.
        """
        # --- KNOWN MISPLACEMENTS ---
        # Agents sometimes nest the real payload under documentation keys they saw in the standard.
        HOIST_CANDIDATES = ["input_schema", "plan", "observe", "observe_plan"]

        # Check: does plan already have the keys we need?
        if mode == "observe":
            has_payload = ("targets" in plan or "groups" in plan)
        elif mode == "apply":
            has_payload = ("operations" in plan)
        else:
            has_payload = True

        if has_payload:
            return plan  # Already correct — fast path

        # Attempt to find payload under a documentation key
        for candidate in HOIST_CANDIDATES:
            nested = plan.get(candidate)
            if isinstance(nested, dict):
                if mode == "observe" and ("targets" in nested or "groups" in nested):
                    return nested
                elif mode == "apply" and "operations" in nested:
                    return nested

        return plan  # Give up — let downstream raise the real error

    def _diff_header_path(self, raw_value: Any) -> str:
        token = str(raw_value or "").strip()
        if not token:
            return ""
        token = token.split("\t", 1)[0].split(" ", 1)[0].strip()
        if token == "/dev/null":
            return ""
        if token.startswith(("a/", "b/")):
            token = token[2:]
        return self._normalize_repo_path(token, field_name="unified_diff.path")

    def _apply_unified_diff_hunks(self, *, target: str, original: str, diff_lines: List[str]) -> str:
        old_lines = original.splitlines(keepends=True)
        output: List[str] = []
        cursor = 0
        index = 0

        while index < len(diff_lines):
            line = diff_lines[index]
            if not line.startswith("@@"):
                index += 1
                continue
            match = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
            if not match:
                raise ApplyError(f"Malformed unified diff hunk header for {target}: {line.strip()}")
            old_start = int(match.group(1))
            anchor = max(old_start - 1, 0)
            if anchor > len(old_lines):
                raise ApplyError(f"Unified diff hunk for {target} starts past EOF.")
            output.extend(old_lines[cursor:anchor])
            cursor = anchor
            index += 1

            while index < len(diff_lines):
                body_line = diff_lines[index]
                if body_line.startswith(("@@", "--- ")):
                    break
                if body_line.startswith("\\ No newline at end of file"):
                    index += 1
                    continue
                prefix = body_line[:1]
                payload = body_line[1:]
                next_is_no_newline_marker = (
                    index + 1 < len(diff_lines)
                    and diff_lines[index + 1].startswith("\\ No newline at end of file")
                )
                if prefix in {" ", "-", "+"} and not body_line.endswith("\n") and not next_is_no_newline_marker:
                    payload = payload + "\n"
                if prefix == " ":
                    if cursor >= len(old_lines):
                        raise ApplyError(f"Unified diff context overruns EOF for {target}.")
                    if old_lines[cursor].rstrip("\n") != payload.rstrip("\n"):
                        raise ApplyError(
                            f"Unified diff context mismatch for {target} near line {cursor + 1}."
                        )
                    output.append(old_lines[cursor])
                    cursor += 1
                elif prefix == "-":
                    if cursor >= len(old_lines):
                        raise ApplyError(f"Unified diff removal overruns EOF for {target}.")
                    if old_lines[cursor].rstrip("\n") != payload.rstrip("\n"):
                        raise ApplyError(
                            f"Unified diff removal mismatch for {target} near line {cursor + 1}."
                        )
                    cursor += 1
                elif prefix == "+":
                    output.append(payload)
                else:
                    raise ApplyError(f"Unsupported unified diff line prefix `{prefix}` for {target}.")
                index += 1

        output.extend(old_lines[cursor:])
        return "".join(output)

    def _operations_from_unified_diff(
        self,
        diff_text: str,
        *,
        group_label: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not str(diff_text or "").strip():
            raise ApplyError("unified_diff must be a non-empty string.")
        lines = diff_text.splitlines(keepends=True)
        operations: List[Dict[str, Any]] = []
        index = 0

        while index < len(lines):
            line = lines[index]
            if not line.startswith("--- "):
                index += 1
                continue
            old_header = line[4:].strip()
            index += 1
            if index >= len(lines) or not lines[index].startswith("+++ "):
                raise ApplyError("Unified diff is missing a matching +++ header.")
            new_header = lines[index][4:].strip()
            index += 1

            old_path = self._diff_header_path(old_header)
            new_path = self._diff_header_path(new_header)
            if new_path == "":
                raise ApplyError("Unified diff deletion is not supported by apply.")
            if old_path and new_path and old_path != new_path:
                raise ApplyError(
                    f"Unified diff rename is not supported: `{old_path}` -> `{new_path}`."
                )
            target = new_path or old_path
            if not target:
                raise ApplyError("Unified diff file header did not resolve to a target path.")

            body: List[str] = []
            while index < len(lines) and not lines[index].startswith("--- "):
                body.append(lines[index])
                index += 1

            if not old_path:
                original = ""
                existed_before = False
            else:
                existed_before = (self.root / old_path).exists()
                original = self.read_file(old_path)
                if not existed_before and not original:
                    raise ApplyError(f"Unified diff target not found on disk: {old_path}")

            updated = self._apply_unified_diff_hunks(target=target, original=original, diff_lines=body)
            operation: Dict[str, Any] = {
                "op": "overwrite" if existed_before else "create_file",
                "target": target,
                "content": updated,
                "source_format": "unified_diff",
            }
            if group_label:
                operation["group_label"] = group_label
            operations.append(operation)

        if not operations:
            raise ApplyError("No unified diff file blocks were found.")
        return operations

    def compile_apply_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        [ACTION]
        - Teleology: Normalize one apply payload into the canonical `operations` list consumed by execution and routing helpers.
        - Mechanism: Normalize the plan shape, preserve explicit operations when present, or expand unified-diff payloads into atomic operations while carrying any top-level group label.
        - Reads: The in-memory plan payload and, for diff expansion, the target files needed to determine create-vs-overwrite behavior.
        - Writes: None.
        - Fails: Raises ApplyError when the plan exposes neither operations nor unified diff content, or when diff targets are malformed.
        - Guarantee: Returns a dict with one normalized `operations` list ready for routing summary or execution.
        - When-needed: Open when an apply payload might be raw unified diff or nested plan data and needs canonical operation expansion.
        - Escalates-to: tools/meta/apply.py::apply_plan; codex/standards/std_apply.json
        - Navigation-group: meta_tooling
        """
        normalized = self._normalize_plan(plan, "apply")
        top_group_label = str(normalized.get("group_label") or "").strip() or None
        operations = normalized.get("operations")
        if isinstance(operations, list):
            compiled_ops: List[Dict[str, Any]] = []
            for item in operations:
                if not isinstance(item, dict):
                    raise ApplyError("Apply operations must be objects.")
                compiled = dict(item)
                if top_group_label and not str(compiled.get("group_label") or "").strip():
                    compiled["group_label"] = top_group_label
                compiled_ops.append(compiled)
            return {"operations": compiled_ops}

        diff_values: List[str] = []
        for key in ("unified_diff", "diff", "patch"):
            value = normalized.get(key)
            if isinstance(value, str) and value.strip():
                diff_values.append(value)
        diff_list = normalized.get("diffs")
        if isinstance(diff_list, list):
            diff_values.extend(str(item) for item in diff_list if isinstance(item, str) and str(item).strip())
        if diff_values:
            compiled_ops: List[Dict[str, Any]] = []
            for diff_text in diff_values:
                compiled_ops.extend(
                    self._operations_from_unified_diff(diff_text, group_label=top_group_label)
                )
            return {"operations": compiled_ops}

        raise ApplyError("Apply plan must contain either operations or unified_diff content.")

    def _normalize_repo_path(self, raw_path: Any, field_name: str = "path") -> str:
        token = str(raw_path).strip() if raw_path is not None else ""
        if not token:
            raise ApplyError(f"{field_name} is required and must be a non-empty path.")

        candidate = Path(token).expanduser()
        resolved = candidate.resolve() if candidate.is_absolute() else (self.root / candidate).resolve()

        try:
            rel = resolved.relative_to(self.root)
        except ValueError:
            raise ApplyError(
                f"{field_name} must resolve inside repo root ({self.root}). Received: {raw_path}"
            )

        normalized = rel.as_posix()
        if not normalized or normalized == ".":
            raise ApplyError(f"{field_name} must resolve to a file path under repo root.")
        return normalized

    def _normalize_target_routing(self, raw_routing: Any) -> Dict[str, Any]:
        if not isinstance(raw_routing, dict):
            return {"policy": {}, "trust_tiers": {}, "families": {}}

        policy = raw_routing.get("policy")
        if not isinstance(policy, dict):
            policy = {}

        raw_trust_tiers = raw_routing.get("trust_tiers")
        if not isinstance(raw_trust_tiers, dict):
            raw_trust_tiers = {}

        raw_families = raw_routing.get("families")
        if isinstance(raw_families, dict):
            family_source = raw_families
        else:
            family_source = {
                key: value
                for key, value in raw_routing.items()
                if key not in {"policy", "trust_tiers", "families"}
            }

        trust_tiers: Dict[str, Dict[str, Any]] = {}
        for name, spec in raw_trust_tiers.items():
            if not isinstance(spec, dict):
                continue
            tier_name = str(name or "").strip()
            if not tier_name:
                continue
            rank_raw = spec.get("rank")
            try:
                rank = int(rank_raw)
            except (TypeError, ValueError):
                rank = 0
            trust_tiers[tier_name] = {
                "rank": rank,
                "default_posture": str(spec.get("default_posture") or "").strip(),
                "description": str(spec.get("description") or "").strip(),
            }

        families: Dict[str, Dict[str, Any]] = {}
        for name, spec in family_source.items():
            if not isinstance(spec, dict):
                continue
            family_name = str(name or "").strip()
            if not family_name:
                continue

            patterns_raw = spec.get("match_patterns")
            if patterns_raw is None and spec.get("match_pattern") is not None:
                patterns_raw = [spec.get("match_pattern")]
            elif isinstance(patterns_raw, str):
                patterns_raw = [patterns_raw]
            elif not isinstance(patterns_raw, list):
                patterns_raw = []

            allowed_ops = [
                str(op).strip()
                for op in spec.get("allowed_ops", [])
                if str(op).strip()
            ]
            required_validators = [
                str(item).strip()
                for item in spec.get("required_validators", [])
                if str(item).strip()
            ]
            trust_tier = str(spec.get("trust_tier") or "").strip()
            default_posture = str(spec.get("default_posture") or "").strip()
            if not default_posture and trust_tier:
                default_posture = str(
                    trust_tiers.get(trust_tier, {}).get("default_posture") or ""
                ).strip()

            families[family_name] = {
                "match_patterns": [
                    str(pattern).strip()
                    for pattern in patterns_raw
                    if str(pattern).strip()
                ],
                "allowed_ops": allowed_ops,
                "required_validators": required_validators,
                "trust_tier": trust_tier,
                "default_posture": default_posture,
                "validator_policy": self._normalize_validator_policy(spec.get("validator_policy")),
                "rollout_policy": self._normalize_rollout_policy(spec.get("rollout_policy")),
                "notes": str(spec.get("notes") or "").strip(),
            }

        return {
            "policy": dict(policy),
            "trust_tiers": trust_tiers,
            "families": families,
        }

    def _target_routing_family_specs(self) -> Dict[str, Dict[str, Any]]:
        families = self.target_routing.get("families", {})
        if isinstance(families, dict):
            return families
        return {}

    def _target_routing_family_spec(self, family_name: str) -> Dict[str, Any]:
        family_specs = self._target_routing_family_specs()
        spec = family_specs.get(str(family_name or "").strip(), {})
        if isinstance(spec, dict):
            return spec
        return {}

    def _target_routing_policy(self) -> Dict[str, Any]:
        policy = self.target_routing.get("policy", {})
        if isinstance(policy, dict):
            return policy
        return {}

    def _target_routing_trust_tiers(self) -> Dict[str, Dict[str, Any]]:
        trust_tiers = self.target_routing.get("trust_tiers", {})
        if isinstance(trust_tiers, dict):
            return trust_tiers
        return {}

    def _trust_tier_rank(self, trust_tier: str) -> int:
        trust_tier = str(trust_tier or "").strip()
        if not trust_tier:
            return 0
        tier_spec = self._target_routing_trust_tiers().get(trust_tier, {})
        rank = tier_spec.get("rank") if isinstance(tier_spec, dict) else None
        if isinstance(rank, int):
            return rank
        defaults = {
            "low_risk_doc_only": 10,
            "high_risk_mutation": 100,
        }
        return defaults.get(trust_tier, 50)

    def _route_pattern_specificity(self, pattern: str) -> int:
        token = str(pattern or "").strip()
        if not token:
            return 0
        return len(token.replace("*", "").replace("?", ""))

    def _path_matches_route_pattern(self, target_path: str, pattern: str) -> bool:
        token = str(pattern or "").strip()
        if not token:
            return False
        target = PurePosixPath(target_path)
        if target.match(token):
            return True
        if token.startswith("**/") and target.match(token[3:]):
            return True
        if token.startswith("*.") and target_path.endswith(token[1:]):
            return True
        return False

    def _normalize_validator_policy(self, value: Any) -> str:
        token = str(value or "").strip()
        if not token:
            return "strict_compliance"
        return token

    def _normalize_rollout_policy(self, value: Any) -> Dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        policy: Dict[str, Any] = {}
        max_touched_files = value.get("max_touched_files")
        if isinstance(max_touched_files, int) and max_touched_files > 0:
            policy["max_touched_files"] = max_touched_files
        if "require_progress_on_dirty_files" in value:
            policy["require_progress_on_dirty_files"] = bool(value.get("require_progress_on_dirty_files"))
        if "notes" in value and isinstance(value.get("notes"), str) and str(value.get("notes")).strip():
            policy["notes"] = str(value.get("notes")).strip()
        return policy

    def _route_payload_from_family(
        self,
        *,
        op_index: int,
        op_type: str,
        target: str,
        family_name: str,
        family_spec: Dict[str, Any],
        best_pattern: str,
        matched_target_families: List[str],
    ) -> Dict[str, Any]:
        return {
            "status": "resolved",
            "op_index": op_index,
            "op": op_type,
            "target": target,
            "family": family_name,
            "match_pattern": best_pattern,
            "allowed_ops": list(family_spec.get("allowed_ops", [])),
            "required_validators": list(family_spec.get("required_validators", [])),
            "trust_tier": str(family_spec.get("trust_tier") or "").strip(),
            "default_posture": str(family_spec.get("default_posture") or "").strip(),
            "validator_policy": self._normalize_validator_policy(family_spec.get("validator_policy")),
            "rollout_policy": self._normalize_rollout_policy(family_spec.get("rollout_policy")),
            "matched_target_families": matched_target_families,
            "notes": str(family_spec.get("notes") or "").strip(),
        }

    def _resolve_target_route_for_op(
        self,
        op_index: int,
        op: Dict[str, Any],
        *,
        preferred_family: str | None = None,
    ) -> Dict[str, Any]:
        op_type = str(op.get("op") or "").strip()
        target = self._normalize_repo_path(op.get("target"), field_name=f"operations[{op_index}].target")
        family_specs = self._target_routing_family_specs()
        preferred_family_name = str(preferred_family or "").strip()
        matched_target_families: List[str] = []
        matches: List[Tuple[int, int, str, str, Dict[str, Any]]] = []
        matched_patterns_by_family: Dict[str, List[str]] = {}

        for family_name, family_spec in family_specs.items():
            match_patterns = family_spec.get("match_patterns", [])
            if not isinstance(match_patterns, list):
                continue
            matched_patterns = [
                str(pattern)
                for pattern in match_patterns
                if self._path_matches_route_pattern(target, str(pattern))
            ]
            if not matched_patterns:
                continue
            matched_target_families.append(family_name)
            matched_patterns_by_family[family_name] = matched_patterns
            allowed_ops = family_spec.get("allowed_ops", [])
            if op_type not in allowed_ops:
                continue
            best_pattern = max(matched_patterns, key=self._route_pattern_specificity)
            matches.append(
                (
                    self._route_pattern_specificity(best_pattern),
                    self._trust_tier_rank(str(family_spec.get("trust_tier") or "")),
                    family_name,
                    best_pattern,
                    family_spec,
                )
            )

        matched_target_families = sorted(set(matched_target_families))
        if preferred_family_name:
            preferred_spec = self._target_routing_family_spec(preferred_family_name)
            if not preferred_spec:
                return {
                    "status": "unresolved",
                    "op_index": op_index,
                    "op": op_type,
                    "target": target,
                    "reason": f"Preferred target_family `{preferred_family_name}` is not configured in target_routing.",
                    "matched_target_families": matched_target_families,
                }
            if preferred_family_name not in matched_target_families:
                matched = ", ".join(matched_target_families) if matched_target_families else "none"
                return {
                    "status": "unresolved",
                    "op_index": op_index,
                    "op": op_type,
                    "target": target,
                    "reason": (
                        f"Preferred target_family `{preferred_family_name}` did not match target `{target}`. "
                        f"Matched routing families: {matched}."
                    ),
                    "matched_target_families": matched_target_families,
                }
            allowed_ops = preferred_spec.get("allowed_ops", [])
            if op_type not in allowed_ops:
                return {
                    "status": "unresolved",
                    "op_index": op_index,
                    "op": op_type,
                    "target": target,
                    "reason": (
                        f"Preferred target_family `{preferred_family_name}` does not allow operation `{op_type}` "
                        f"for target `{target}`."
                    ),
                    "matched_target_families": matched_target_families,
                }
            preferred_patterns = matched_patterns_by_family.get(preferred_family_name, [])
            best_pattern = max(preferred_patterns, key=self._route_pattern_specificity)
            return self._route_payload_from_family(
                op_index=op_index,
                op_type=op_type,
                target=target,
                family_name=preferred_family_name,
                family_spec=preferred_spec,
                best_pattern=best_pattern,
                matched_target_families=matched_target_families,
            )

        if not matches:
            if matched_target_families:
                reason = (
                    f"Operation `{op_type}` is not allowed for target `{target}`. "
                    f"Matched routing families: {', '.join(matched_target_families)}."
                )
            else:
                reason = f"No target_routing family matched target `{target}`."
            return {
                "status": "unresolved",
                "op_index": op_index,
                "op": op_type,
                "target": target,
                "reason": reason,
                "matched_target_families": matched_target_families,
            }

        _pattern_score, _trust_score, family_name, best_pattern, family_spec = max(matches)
        return self._route_payload_from_family(
            op_index=op_index,
            op_type=op_type,
            target=target,
            family_name=family_name,
            family_spec=family_spec,
            best_pattern=best_pattern,
            matched_target_families=matched_target_families,
        )

    def summarize_target_routing(
        self,
        ops: List[Dict[str, Any]],
        *,
        strict: bool = False,
        preferred_family: str | None = None,
    ) -> Dict[str, Any]:
        """
        [ACTION]
        - Teleology: Explain how an apply batch maps onto target-routing families, trust tiers, and validator posture before execution.
        - Mechanism: Resolve each operation against the routing config, aggregate validators/warnings, and summarize batch-wide trust and review requirements.
        - Reads: In-memory operations plus target-routing rules derived from `std_apply.json`.
        - Writes: None.
        - Fails: None intentionally; unresolved routing is surfaced in the returned summary.
        - Guarantee: Returns a routing summary even when target routing is not configured.
        - When-needed: Open when deciding whether an apply batch needs stricter validators, preferred families, or manual review before running.
        - Escalates-to: codex/standards/std_apply.json; tools/meta/apply.py::apply_plan
        - Navigation-group: meta_tooling
        """
        family_specs = self._target_routing_family_specs()
        policy = self._target_routing_policy()
        preferred_family_name = str(preferred_family or "").strip() or None
        if not family_specs:
            return {
                "status": "not_configured",
                "policy": policy,
                "preferred_target_family": preferred_family_name,
                "batch_trust_tier": None,
                "batch_default_posture": None,
                "batch_validator_policy": "strict_compliance",
                "batch_rollout_policy": {},
                "mixed_trust": False,
                "requires_manual_review": False,
                "required_validators": [],
                "resolved_ops": [],
                "unresolved_ops": [],
                "warnings": [],
            }

        resolved_ops: List[Dict[str, Any]] = []
        unresolved_ops: List[Dict[str, Any]] = []
        warnings: List[str] = []
        required_validators: set[str] = set()
        strictest_route: Dict[str, Any] | None = None

        for op_index, op in enumerate(ops):
            if not isinstance(op, dict):
                unresolved_ops.append(
                    {
                        "status": "unresolved",
                        "op_index": op_index,
                        "op": None,
                        "target": None,
                        "reason": "Operation payload must be an object.",
                        "matched_target_families": [],
                    }
                )
                continue
            route = self._resolve_target_route_for_op(
                op_index,
                op,
                preferred_family=preferred_family_name,
            )
            if route.get("status") == "resolved":
                resolved_ops.append(route)
                required_validators.update(route.get("required_validators", []))
                if strictest_route is None or self._trust_tier_rank(
                    str(route.get("trust_tier") or "")
                ) >= self._trust_tier_rank(str(strictest_route.get("trust_tier") or "")):
                    strictest_route = route
                continue
            unresolved_ops.append(route)

        trust_tiers = {
            str(route.get("trust_tier") or "").strip()
            for route in resolved_ops
            if str(route.get("trust_tier") or "").strip()
        }
        mixed_trust = len(trust_tiers) > 1
        if mixed_trust:
            warnings.append(
                "Mixed-trust batch resolved across multiple target_routing trust tiers; caller should treat the batch as manual-review-required."
            )
        if unresolved_ops:
            warnings.extend(str(route.get("reason") or "") for route in unresolved_ops if route.get("reason"))

        batch_trust_tier = str(strictest_route.get("trust_tier") or "") if strictest_route else None
        batch_default_posture = str(strictest_route.get("default_posture") or "") if strictest_route else None
        validator_policies = {
            self._normalize_validator_policy(route.get("validator_policy"))
            for route in resolved_ops
            if route.get("status") == "resolved"
        }
        batch_validator_policy = "strict_compliance"
        if len(validator_policies) == 1:
            batch_validator_policy = next(iter(validator_policies))
        elif len(validator_policies) > 1:
            warnings.append(
                "Mixed validator policies detected across target_routing families; defaulting batch validator policy to strict_compliance."
            )
        batch_rollout_policy: Dict[str, Any] = {}
        rollout_sources: List[str] = []
        max_touched_limits: List[int] = []
        require_progress = False
        rollout_notes: List[str] = []
        for route in resolved_ops:
            route_policy = route.get("rollout_policy")
            if not isinstance(route_policy, dict) or not route_policy:
                continue
            rollout_sources.append(str(route.get("family") or "").strip())
            max_touched = route_policy.get("max_touched_files")
            if isinstance(max_touched, int) and max_touched > 0:
                max_touched_limits.append(max_touched)
            if bool(route_policy.get("require_progress_on_dirty_files")):
                require_progress = True
            note = str(route_policy.get("notes") or "").strip()
            if note:
                rollout_notes.append(note)
        if max_touched_limits:
            batch_rollout_policy["max_touched_files"] = min(max_touched_limits)
        if require_progress:
            batch_rollout_policy["require_progress_on_dirty_files"] = True
        if rollout_sources:
            batch_rollout_policy["families"] = sorted(set(source for source in rollout_sources if source))
        if rollout_notes:
            batch_rollout_policy["notes"] = sorted(set(rollout_notes))
        if batch_trust_tier:
            tier_default = str(
                self._target_routing_trust_tiers().get(batch_trust_tier, {}).get("default_posture") or ""
            ).strip()
            if tier_default and not batch_default_posture:
                batch_default_posture = tier_default

        requires_manual_review = bool(unresolved_ops) or mixed_trust
        if batch_default_posture and batch_default_posture != "preview_first_live_allowed":
            requires_manual_review = True

        if resolved_ops and unresolved_ops:
            status = "partial"
        elif resolved_ops:
            status = "resolved"
        else:
            status = "unresolved"

        summary = {
            "status": status,
            "policy": policy,
            "preferred_target_family": preferred_family_name,
            "batch_trust_tier": batch_trust_tier,
            "batch_default_posture": batch_default_posture,
            "batch_validator_policy": batch_validator_policy,
            "batch_rollout_policy": batch_rollout_policy,
            "mixed_trust": mixed_trust,
            "requires_manual_review": requires_manual_review,
            "required_validators": sorted(required_validators),
            "resolved_ops": resolved_ops,
            "unresolved_ops": unresolved_ops,
            "warnings": warnings,
        }

        if strict and unresolved_ops:
            first = unresolved_ops[0]
            raise ApplyError(
                f"Target routing rejected op {first.get('op_index')}: {first.get('reason')}",
                int(first.get("op_index", -1)),
                ops[int(first.get("op_index", -1))] if isinstance(first.get("op_index"), int) and 0 <= int(first.get("op_index")) < len(ops) else None,
                detail=json.dumps(summary, indent=2),
            )

        return summary

    def _resolve_context_path(self, raw_path: str) -> Path:
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            candidate = self.root / raw_path
        return candidate.resolve()

    def _context_key_for_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.root)).replace("\\", "/")
        except ValueError:
            return str(path)

    def _iter_context_dir_files(self, dir_path: Path):
        for root_dir, dir_names, file_names in os.walk(dir_path):
            dir_names[:] = sorted(
                d for d in dir_names
                if d not in self._CONTEXT_SKIP_DIRS and not d.startswith(".")
            )
            for file_name in sorted(file_names):
                file_path = Path(root_dir) / file_name
                if file_path.suffix.lower() in self._CONTEXT_SUPPORTED_EXTENSIONS:
                    yield file_path

    def _append_context_entry(
        self,
        context: Dict[str, str],
        key: str,
        source_path: Path,
        total_chars: int
    ) -> int:
        if key in context:
            return total_chars

        remaining_budget = self._CONTEXT_MAX_TOTAL_CHARS - total_chars
        if remaining_budget <= 0:
            context[key] = (
                "[WARN] Skipped due to context budget limit "
                f"({self._CONTEXT_MAX_TOTAL_CHARS} chars)."
            )
            return total_chars

        raw_text = source_path.read_text(encoding="utf-8", errors="replace")
        max_chars = min(self._CONTEXT_MAX_CHARS_PER_FILE, remaining_budget)
        if len(raw_text) > max_chars:
            truncation_note = (
                f"\n[TRUNCATED] Context truncated at {max_chars} chars "
                f"(source length: {len(raw_text)} chars)."
            )
            keep = max(0, max_chars - len(truncation_note))
            content = raw_text[:keep] + truncation_note
        else:
            content = raw_text

        context[key] = content
        return total_chars + len(content)

    def _extract_manifest_linked_context_paths(self, source_path: Path) -> List[str]:
        if source_path.suffix.lower() != ".json":
            return []

        try:
            payload = json.loads(source_path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            return []

        refs: List[str] = []
        if not isinstance(payload, dict):
            return refs

        continuation = payload.get("continuation")
        if isinstance(continuation, dict):
            read_paths = continuation.get("read_paths", [])
            if isinstance(read_paths, list):
                refs.extend(str(path) for path in read_paths if str(path).strip())
            latest_artifact = continuation.get("latest_artifact")
            if isinstance(latest_artifact, str) and latest_artifact.strip():
                refs.append(latest_artifact)

        records = payload.get("records", [])
        if isinstance(records, list):
            for record in records:
                if not isinstance(record, dict):
                    continue
                relpath = record.get("relpath")
                if isinstance(relpath, str) and relpath.strip():
                    refs.append(relpath)

        groups = payload.get("groups", [])
        if isinstance(groups, list):
            for group in groups:
                if not isinstance(group, dict):
                    continue
                for key in ("response_file", "dump_file"):
                    relpath = group.get(key)
                    if isinstance(relpath, str) and relpath.strip():
                        refs.append(relpath)

        seen: set[str] = set()
        deduped: List[str] = []
        for ref in refs:
            normalized = str(ref).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return deduped

    def _read_context(self, context_files: List[str]) -> Dict[str, str]:
        """
        Reads context files/directories to inject into observations.
        Observe mode supports directory expansion; apply mode never consumes context_files.
        """
        context: Dict[str, str] = {}
        if not context_files:
            return context

        total_chars = 0

        for raw_path in context_files:
            requested = str(raw_path).strip()
            if not requested:
                continue

            try:
                path = self._resolve_context_path(requested)
            except Exception:
                context[requested] = f"[ERROR] Invalid context path: {requested}"
                continue

            if not path.exists():
                context[requested] = f"[ERROR] Context path not found: {requested}"
                continue

            if path.is_file():
                key = self._context_key_for_path(path)
                try:
                    total_chars = self._append_context_entry(context, key, path, total_chars)
                except Exception as e:
                    context[key] = f"[ERROR] Failed to read context file: {e}"
                    continue

                linked_paths = self._extract_manifest_linked_context_paths(path)
                if linked_paths:
                    expanded = 0
                    skipped = 0
                    for linked in linked_paths:
                        try:
                            linked_path = self._resolve_context_path(linked)
                        except Exception:
                            skipped += 1
                            continue
                        if not linked_path.exists() or not linked_path.is_file():
                            skipped += 1
                            continue
                        linked_key = self._context_key_for_path(linked_path)
                        try:
                            before_count = len(context)
                            next_total = self._append_context_entry(context, linked_key, linked_path, total_chars)
                        except Exception:
                            skipped += 1
                            continue
                        if len(context) > before_count:
                            expanded += 1
                            total_chars = next_total
                    context[f"__context_links__:{key}"] = (
                        "[INFO] Manifest-linked context expansion: "
                        f"expanded={expanded}, referenced={len(linked_paths)}, skipped={skipped}"
                    )
                continue

            if not path.is_dir():
                context[requested] = f"[ERROR] Unsupported context path type: {requested}"
                continue

            expanded = 0
            skipped_by_cap = 0
            skipped_by_budget = 0

            for file_path in self._iter_context_dir_files(path):
                if expanded >= self._CONTEXT_MAX_FILES_PER_DIR:
                    skipped_by_cap += 1
                    continue
                if total_chars >= self._CONTEXT_MAX_TOTAL_CHARS:
                    skipped_by_budget += 1
                    continue

                key = self._context_key_for_path(file_path)
                try:
                    before_count = len(context)
                    next_total = self._append_context_entry(context, key, file_path, total_chars)
                except Exception as e:
                    context[key] = f"[ERROR] Failed to read context file: {e}"
                    continue

                if len(context) > before_count:
                    expanded += 1
                    total_chars = next_total

            summary_key = f"__context_dir__:{requested}"
            summary_parts = [f"expanded={expanded}"]
            if skipped_by_cap:
                summary_parts.append(f"skipped_file_cap={skipped_by_cap}")
            if skipped_by_budget:
                summary_parts.append(f"skipped_budget={skipped_by_budget}")
            context[summary_key] = "[INFO] Directory context expansion: " + ", ".join(summary_parts)

        return context

    def read_file(self, rel_path: str) -> str:
        """
        [ACTION]
        - Teleology: Return file text, preferring Ghost FS overrides.
        - Preconditions: `rel_path` is a repo-relative path.
        - Reads: Ghost FS (if present), otherwise disk at `root/rel_path`.
        - Writes: None.
        - Fails: None (returns empty string for missing paths).
        - Guarantee: Returns a unicode string and does not mutate disk state.
        - When-needed: Open when debugging whether observe/apply is reading staged Ghost FS content or the on-disk file.
        - Escalates-to: tools/meta/apply.py::write_ghost; tools/meta/apply.py::apply_plan
        
        """
        if rel_path in self.ghost_fs:
            return self.ghost_fs[rel_path]
        path = self.root / rel_path
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    def write_ghost(self, rel_path: str, content: str):
        """
        [ACTION]
        - Teleology: Stage a file edit in the in-memory Ghost FS.
        - Preconditions: `rel_path` is repo-relative; `content` is complete file text.
        - Reads: None.
        - Writes: Ghost FS entry for `rel_path`.
        - Fails: None.
        - Guarantee: Subsequent `read_file(rel_path)` returns this content until overwritten.
        
        """
        self.ghost_fs[rel_path] = content

    # --- OBSERVE HISTORY LOG ---
    def _write_observe_log(self, observe_result: Dict[str, Any]) -> None:
        """
        [ACTION]
        - Teleology: Append a metadata-rich entry to observe_history/log.json after each successful observe.
        - Preconditions: `observe_result` is the dict returned by `observe()` or `_observe_grouped()`.
        - Reads: Existing log file (if any) from disk.
        - Writes: observe_history/log.json (append-only).
        - Fails: Silently — never raises; observe must not fail due to logging.
        - Guarantee: Log file is a JSON object with schema_version and entries array.
        """
        try:
            log_dir = self.root / "tools" / "meta" / "apply" / "observe_history"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / "log.json"

            # Read existing log or start fresh
            if log_path.exists():
                try:
                    existing = json.loads(log_path.read_text(encoding="utf-8"))
                    if not isinstance(existing, dict) or "entries" not in existing:
                        existing = {"schema_version": "1.0.0", "entries": []}
                except Exception:
                    existing = {"schema_version": "1.0.0", "entries": []}
            else:
                existing = {"schema_version": "1.0.0", "entries": []}

            # Extract metadata from observe result
            meta = observe_result.get("__meta", {})
            manifest = observe_result.get("manifest", [])
            observations = observe_result.get("observations", [])

            # Determine mode and collect file list
            is_grouped = meta.get("mode") == "grouped_observe"
            if is_grouped:
                files_observed = []
                for entry in manifest:
                    files_observed.extend(entry.get("files", []))
                group_labels = [entry.get("label", "") for entry in manifest]
            else:
                files_observed = [obs.get("file", "") for obs in observations if obs.get("file")]
                group_labels = []

            # Generate unique ID: OBS_{timestamp_slug}_{6-char-hash}
            ts_slug = re.sub(r'[^0-9T]', '-', self.timestamp[:19])
            hash_input = f"{self.timestamp}:{','.join(files_observed)}"
            short_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:6]
            obs_id = f"OBS_{ts_slug}_{short_hash}"

            entry = {
                "id": obs_id,
                "timestamp": self.timestamp,
                "mode": "grouped_observe" if is_grouped else "standard_observe",
                "total_files": meta.get("total_files", len(files_observed)),
                "total_groups": meta.get("total_groups", 0),
                "group_labels": group_labels,
                "files_observed": files_observed,
                "dump_dir": meta.get("dump_dir"),
                "context_files": meta.get("injected_context_files", []),
                "print_format": meta.get("print_format", "raw"),
                "print_shape": meta.get("print_shape", "preserve_shape"),
                "notes": meta.get("wait_notes") or meta.get("plan_notes"),
                "plan_notes": meta.get("plan_notes"),
                "wait_notes": meta.get("wait_notes"),
                "prompt": meta.get("prompt"),
                "result_note_path": meta.get("result_note_path"),
                "result_note_kind": meta.get("result_note_kind"),
                "promotion_target_path": meta.get("promotion_target_path"),
                "promotion_mode": meta.get("promotion_mode"),
                "promotion_section": meta.get("promotion_section"),
                "promotion_gate": meta.get("promotion_gate"),
                "root": meta.get("root") or OBSERVE_DUMP_REPO_ROOT_MARKER,
            }

            existing["entries"].append(entry)

            log_path.write_text(
                json.dumps(existing, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass  # Never crash observe for a logging failure

    # --- MODE 1: OBSERVE ---
    def observe(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        # Context Injection (Load once)
        """
        [ACTION]
        - Teleology: Produce grounded observations of requested file scopes.
        - Preconditions: `plan` contains either `targets` (simple) or `groups` + `dump_dir` (grouped).
        - Reads: Target files via `read_file`; optional `context_files` from disk.
        - Writes: Grouped mode writes JSON dumps under `dump_dir`.
        - Fails: Raises ApplyError on invalid plan shape.
        - Guarantee: Returns a JSON-serializable dict with `__meta` and observations (and optional `__context`).
        - When-needed: Open when a caller needs the exact observe-mode envelope and grouped-versus-standard branching behavior.
        - Escalates-to: tools/meta/apply.py::_observe_grouped; system/core/analysis.py
        - Navigation-group: meta_tooling
        
        """
        print_options = plan.get("print_options") if isinstance(plan.get("print_options"), dict) else {}
        print_format = self._normalize_print_format(
            plan.get("print_format", print_options.get("format"))
        )
        print_shape = self._normalize_print_shape(
            plan.get("print_shape", print_options.get("shape"))
        )

        context_files = plan.get("context_files", [])

        # Grouped Mode
        groups = plan.get("groups")
        if groups:
            return self._observe_grouped(plan, context_files, print_format, print_shape)

        # Standard Mode
        context_data = self._format_context_map(
            self._read_context(context_files),
            print_format=print_format,
            print_shape=print_shape,
        )
        targets = plan.get("targets", [])
        meta = {
            "generated_at": self.timestamp,
            "root": OBSERVE_DUMP_REPO_ROOT_MARKER,
            "target_count": len(targets),
            "print_format": print_format,
            "print_shape": print_shape,
        }
        plan_notes = plan.get("notes")
        wait_notes = plan.get("wait_notes")
        injected_prompt = plan.get("prompt")
        if not wait_notes and isinstance(plan_notes, str):
            wait_notes = plan_notes
        if plan_notes:
            meta["plan_notes"] = plan_notes
        if wait_notes:
            meta["wait_notes"] = wait_notes
        if injected_prompt:
            meta["prompt"] = injected_prompt

        observations = self._observe_targets(targets, print_format, print_shape)
        output = {
            "__reading_guide": self._OBSERVE_READING_GUIDE,
            "__meta": meta,
            "__toc": self._build_observe_toc(observations),
            "__context": context_data,
            "observations": observations
        }
            
        return output

    # --- MODE 1b: GROUPED OBSERVE ---
    def _observe_grouped(
        self,
        plan: Dict[str, Any],
        plan_context_files: List[str],
        print_format: str,
        print_shape: str,
    ) -> Dict[str, Any]:
        groups = plan.get("groups", [])
        dump_dir_raw = plan.get("dump_dir")
        if not dump_dir_raw:
            raise ApplyError("Grouped observe requires 'dump_dir' in plan.")

        dump_dir = self._normalize_repo_path(dump_dir_raw, field_name="dump_dir")
        dump_path = self.root / dump_dir
        dump_path.mkdir(parents=True, exist_ok=True)

        plan_notes = plan.get("notes")
        wait_notes = plan.get("wait_notes")
        injected_prompt = plan.get("prompt")
        meta_instruction = plan.get("meta_instruction")
        route_config = normalize_route_config(plan)
        route_config["result_note_path"] = normalize_repo_relative_path(
            route_config.get("result_note_path"),
            repo_root=self.root,
        )
        route_config["promotion_target_path"] = normalize_repo_relative_path(
            route_config.get("promotion_target_path"),
            repo_root=self.root,
        )
        resolved_reference_maps, reference_map_errors, reference_map_warnings = resolve_reference_maps(
            plan.get("reference_maps"),
            repo_root=self.root,
        )
        if not wait_notes and isinstance(plan_notes, str):
            wait_notes = plan_notes
        total_files = sum(len(g.get("targets", [])) for g in groups)
        manifest = []
        union_context_files: List[str] = []
        plan_context_files = [
            str(item).strip()
            for item in plan_context_files
            if str(item).strip()
        ]
        context_merge_mode = normalize_context_merge_mode(plan.get("context_merge_mode"))

        for idx, group in enumerate(groups, start=1):
            label = group.get("label", f"group_{idx}")
            targets = group.get("targets", [])
            group_notes = group.get("notes")
            group_question = group.get("question")
            group_output_contract = group.get("output_contract")
            group_downstream_consumer = group.get("downstream_consumer")
            raw_group_context_files = group.get("context_files", [])
            if not isinstance(raw_group_context_files, list):
                raw_group_context_files = []
            evidence_contract = resolve_group_evidence_contract(
                self.root,
                plan_context_files=plan_context_files,
                group_context_files=raw_group_context_files,
                targets=targets if isinstance(targets, list) else [],
                context_merge_mode=context_merge_mode,
            )
            effective_context_files = list(evidence_contract["effective_context_files"])
            context_target_overlaps = list(evidence_contract["context_target_overlaps"])
            for item in effective_context_files:
                if item not in union_context_files:
                    union_context_files.append(item)
            group_context_data = self._format_context_map(
                self._read_context(effective_context_files),
                print_format=print_format,
                print_shape=print_shape,
            )

            # Run normal observation logic for this group's targets
            group_result = self._observe_targets(targets, print_format, print_shape)

            # Build group meta with optional notes
            group_meta = {
                "generated_at": self.timestamp,
                "root": OBSERVE_DUMP_REPO_ROOT_MARKER,
                "group_index": idx,
                "group_label": label,
                "file_count": len(targets),
                "print_format": print_format,
                "print_shape": print_shape,
            }
            if plan_notes:
                group_meta["plan_notes"] = plan_notes
            if wait_notes:
                group_meta["wait_notes"] = wait_notes
            if injected_prompt:
                group_meta["prompt"] = injected_prompt
            if group_notes:
                group_meta["group_notes"] = group_notes
            if group_question:
                group_meta["question"] = group_question
            if group_output_contract:
                group_meta["output_contract"] = group_output_contract
            if group_downstream_consumer:
                group_meta["downstream_consumer"] = group_downstream_consumer
            group_meta["context_files"] = effective_context_files
            group_meta["injected_context_files"] = list(group_context_data.keys())
            group_meta["context_merge_mode"] = context_merge_mode
            if context_target_overlaps:
                group_meta["context_target_overlaps"] = context_target_overlaps

            # Write combined group file WITH context
            group_payload = {
                "__reading_guide": self._OBSERVE_READING_GUIDE,
                "__meta": group_meta,
                "__toc": self._build_observe_toc(group_result),
                "__context": group_context_data,
                "observations": group_result
            }

            safe_label = re.sub(r'[^\w\-]', '_', label).strip('_').lower()
            file_name = f"{idx:02d}_{safe_label}.json"
            file_path = dump_path / file_name

            file_path.write_text(
                self._serialize_json(group_payload, print_shape),
                encoding="utf-8"
            )

            manifest_entry = {
                "index": idx,
                "label": label,
                "file_count": len(targets),
                "files": [obs.get("file") for obs in group_result if obs.get("file")],
                "dump_file": str(file_path.relative_to(self.root))
            }
            if group_notes:
                manifest_entry["notes"] = group_notes
            if group_question:
                manifest_entry["question"] = group_question
            if group_output_contract:
                manifest_entry["output_contract"] = group_output_contract
            if group_downstream_consumer:
                manifest_entry["downstream_consumer"] = group_downstream_consumer
            manifest_entry["context_files"] = effective_context_files
            if context_target_overlaps:
                manifest_entry["context_target_overlaps"] = context_target_overlaps
            manifest.append(manifest_entry)

        top_meta = {
            "generated_at": self.timestamp,
            "root": OBSERVE_DUMP_REPO_ROOT_MARKER,
            "mode": "grouped_observe",
            "total_groups": len(groups),
            "total_files": total_files,
            "dump_dir": dump_dir,
            "context_files": plan_context_files,
            "injected_context_files": union_context_files,
            "context_merge_mode": context_merge_mode,
            "print_format": print_format,
            "print_shape": print_shape,
            "meta_instruction_file": f"{dump_dir}/00_meta_instruction.md",
            "result_note_path": route_config["result_note_path"],
            "result_note_kind": route_config["result_note_kind"],
            "embed_original_plan": route_config["embed_original_plan"],
            "concatenate_group_outputs": route_config["concatenate_group_outputs"],
            "reference_maps": list(route_config.get("reference_maps", [])),
            "resolved_reference_maps": resolved_reference_maps,
            "reference_map_errors": reference_map_errors,
            "reference_map_warnings": reference_map_warnings,
            "promotion_target_path": route_config["promotion_target_path"],
            "promotion_mode": route_config["promotion_mode"],
            "promotion_section": route_config["promotion_section"],
            "promotion_gate": route_config["promotion_gate"],
        }
        if isinstance(plan.get("observe_enrichment"), dict):
            top_meta["observe_enrichment"] = plan.get("observe_enrichment")
        if plan_notes:
            top_meta["plan_notes"] = plan_notes
        if wait_notes:
            top_meta["wait_notes"] = wait_notes
        if injected_prompt:
            top_meta["prompt"] = injected_prompt
        for field_name in (
            "cycle_id",
            "pass_index",
            "max_passes",
            "assimilation_gate",
            "prior_synthesis_path",
            "prior_synthesis_waiver",
            "reorientation_note_path",
        ):
            if field_name in plan:
                top_meta[field_name] = plan.get(field_name)

        # --- Write 00_meta_instruction.md guidance card to dump folder ---
        meta_instruction_file_name = "00_meta_instruction.md"
        meta_instruction_text = self._build_group_meta_instruction_markdown(
            dump_dir=dump_dir,
            total_groups=len(groups),
            total_files=total_files,
            plan_notes=plan_notes,
            wait_notes=wait_notes,
            injected_prompt=injected_prompt,
            meta_instruction=meta_instruction,
        )
        (dump_path / meta_instruction_file_name).write_text(
            meta_instruction_text,
            encoding="utf-8",
        )

        # --- Write 00_contents.json index to dump folder ---
        contents_payload = {
            "__reading_guide": (
                "This is the contents index for an observe dump folder. "
                "Read this file first to understand the scope, grouping strategy, "
                "and file targets of this observe pass. Each entry in 'groups' maps "
                "to a numbered JSON file in this folder."
            ),
            "generated_at": self.timestamp,
            "dump_dir": dump_dir,
            "plan_prompt": injected_prompt,
            "plan_notes": plan_notes,
            "wait_notes": wait_notes,
            "meta_instruction_file": meta_instruction_file_name,
            "total_groups": len(groups),
            "total_files": total_files,
            "context_files": plan_context_files,
            "context_merge_mode": context_merge_mode,
            "result_note_path": route_config["result_note_path"],
            "result_note_kind": route_config["result_note_kind"],
            "embed_original_plan": route_config["embed_original_plan"],
            "concatenate_group_outputs": route_config["concatenate_group_outputs"],
            "reference_maps": list(route_config.get("reference_maps", [])),
            "resolved_reference_maps": resolved_reference_maps,
            "reference_map_errors": reference_map_errors,
            "reference_map_warnings": reference_map_warnings,
            "promotion_target_path": route_config["promotion_target_path"],
            "promotion_mode": route_config["promotion_mode"],
            "promotion_section": route_config["promotion_section"],
            "promotion_gate": route_config["promotion_gate"],
            "groups": [
                {
                    "index": entry["index"],
                    "label": entry["label"],
                    "file_count": entry["file_count"],
                    "files": entry["files"],
                    "dump_file": Path(entry["dump_file"]).name,
                    "notes": entry.get("notes"),
                    "question": entry.get("question"),
                    "output_contract": entry.get("output_contract"),
                    "downstream_consumer": entry.get("downstream_consumer"),
                    "context_files": entry.get("context_files", []),
                }
                for entry in manifest
            ],
        }
        (dump_path / "00_contents.json").write_text(
            self._serialize_json(contents_payload, "preserve_shape"),
            encoding="utf-8",
        )

        # --- Write _observe_plan.json snapshot to dump folder ---
        # Preserves the exact plan that produced this dump so an AI reading
        # the folder can reconstruct the intent without external references.
        (dump_path / "_observe_plan.json").write_text(
            self._serialize_json(plan, "preserve_shape"),
            encoding="utf-8",
        )

        return {
            "__meta": top_meta,
            "manifest": manifest,
            "observations": []
        }

    def _observe_targets(self, targets: List[Dict[str, Any]], print_format: str, print_shape: str) -> List[Dict[str, Any]]:
        observations = []
        for target in targets:
            raw_path = target.get("file")
            scope = target.get("scope", "full")
            target_notes = target.get("notes")
            if not raw_path:
                continue

            try:
                rel_path = self._normalize_repo_path(raw_path, field_name="target.file")
            except ApplyError as path_err:
                obs = {
                    "file": str(raw_path),
                    "scope": scope,
                    "exists": False,
                    "line_count": 0,
                    "byte_count": 0,
                    "language": "text",
                    "symbols": None,
                    "error": path_err.message,
                }
                if target_notes:
                    obs["notes"] = target_notes
                observations.append(obs)
                continue

            content = self.read_file(rel_path)
            path_exists = rel_path in self.ghost_fs or (self.root / rel_path).exists()
            language = self._detect_language(rel_path)
            symbols = self._extract_symbols(content, rel_path) if path_exists else None
            observe_symbol_limit, _toc_symbol_limit = self._observe_symbol_limits()
            symbol_preview, symbol_count, symbol_truncated = self._compress_symbols(
                symbols,
                limit=observe_symbol_limit,
                focus_name=str(target.get("name") or "").strip(),
            )
            obs = {
                "file": rel_path,
                "scope": scope,
                "exists": bool(content) or path_exists,
                "line_count": 0,
                "byte_count": 0,
                "language": language,
                "symbols": symbol_preview,
            }
            if symbol_count:
                obs["symbol_count"] = symbol_count
            if symbol_truncated:
                obs["symbols_truncated"] = True
            if target_notes:
                obs["notes"] = target_notes

            if not obs["exists"]:
                obs["error"] = "File not found"
                observations.append(obs)
                continue

            rendered_content = None
            try:
                if scope == "full":
                    rendered_content = self._format_observed_content(
                        rel_path,
                        content,
                        print_format,
                        print_shape,
                    )
                    obs["content"] = rendered_content
                    if rel_path.endswith('.py') and analyze_python_module:
                        try:
                            if rel_path not in self.ghost_fs:
                                analysis = analyze_python_module(self.root / rel_path)
                                obs["compliance"] = {
                                    "is_compliant": analysis.is_compliant,
                                    "missing_module_tags": analysis.missing_module_tags,
                                    "classes_missing_role": analysis.classes_missing_role,
                                    "functions_missing_action": analysis.functions_missing_action
                                }
                        except Exception as e:
                            obs["compliance_error"] = str(e)
                elif scope in ("function", "class"):
                    name = target.get("name")
                    node = self._find_node(content, name, scope)
                    if node:
                        obs["name"] = name
                        obs["line_start"] = node.lineno
                        obs["line_end"] = node.end_lineno
                        lines = content.splitlines(keepends=True)
                        segment = "".join(lines[node.lineno-1 : node.end_lineno])
                        rendered_content = self._format_observed_content(
                            rel_path,
                            segment,
                            print_format,
                            print_shape,
                        )
                        obs["content"] = rendered_content
                    else:
                        obs["error"] = f"{scope} '{name}' not found"
                elif scope == "line_range":
                    start_line = int(target.get("line_start") or 0)
                    end_line = int(target.get("line_end") or 0)
                    if start_line <= 0 or end_line < start_line:
                        obs["error"] = "line_range target requires positive line_start/line_end values"
                    else:
                        lines = content.splitlines(keepends=True)
                        segment = "".join(lines[start_line - 1:end_line])
                        obs["line_start"] = start_line
                        obs["line_end"] = end_line
                        if target.get("name"):
                            obs["name"] = target.get("name")
                        rendered_content = self._format_observed_content(
                            rel_path,
                            segment,
                            print_format,
                            print_shape,
                        )
                        obs["content"] = rendered_content
                elif scope in ("heading", "section", "markdown_heading"):
                    heading = str(target.get("heading") or target.get("name") or "").strip()
                    if not heading:
                        obs["error"] = f"{scope} target requires 'heading' or 'name'"
                    else:
                        _frontmatter, body = parse_frontmatter(content)
                        bounds = find_section_bounds(body, heading)
                        if bounds is None:
                            block = extract_section_block(body, heading)
                            if block is None:
                                obs["error"] = f"heading '{heading}' not found"
                            else:
                                segment = f"## {heading}\n{block}".strip()
                                obs["heading"] = heading
                                obs["name"] = heading
                                rendered_content = self._format_observed_content(
                                    rel_path,
                                    segment,
                                    print_format,
                                    print_shape,
                                )
                                obs["content"] = rendered_content
                        else:
                            heading_start, _heading_end, _content_start, content_end = bounds
                            segment = body[heading_start:content_end].strip()
                            obs["heading"] = heading
                            obs["name"] = heading
                            rendered_content = self._format_observed_content(
                                rel_path,
                                segment,
                                print_format,
                                print_shape,
                            )
                            obs["content"] = rendered_content
                elif scope == "imports":
                    imports = self._extract_imports(content)
                    obs["parsed_imports"] = imports
                elif scope == "outline":
                    # Structural outline: imports, class/function signatures,
                    # docstrings — no function bodies.  Drastically reduces
                    # token count for large files (e.g. 670KB → ~30KB).
                    outline = self._extract_outline(content, rel_path)
                    rendered_content = self._format_observed_content(
                        rel_path,
                        outline,
                        print_format,
                        print_shape,
                    )
                    obs["content"] = rendered_content
                    obs["scope_note"] = "structural outline (imports, class/function signatures, docstrings)"
            except Exception as e:
                obs["error"] = f"Observation failed: {str(e)}"

            if isinstance(rendered_content, str):
                obs["line_count"] = len(rendered_content.splitlines())
                obs["byte_count"] = len(rendered_content.encode("utf-8"))

            observations.append(obs)
        return observations

    # --- MODE 2: APPLY ---
    def apply_plan(
        self,
        plan: Dict[str, Any],
        dry_run: bool = True,
        validate_only: bool = False,
        capture_diffs: bool = False,
        snapshot_id: Optional[str] = None,
        enforce_target_routing: bool = False,
        preferred_target_family: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        [ACTION]
        - Teleology: Execute a whitelisted sequence of atomic operations against the repository.
        - Preconditions: `plan` contains an `operations` list; each op includes required fields per `std_apply.json`.
        - Reads: Target files via `read_file`; `codex/standards/std_apply.json` for schema.
        - Writes: Ghost FS always; disk only when `dry_run` is false.
        - Fails: Raises ApplyError on unknown op/missing fields or on post-op syntax validation failure.
        - Guarantee: If `dry_run` is true, performs no disk writes. If `dry_run` is false, commits only validated content staged in Ghost FS.
        - When-needed: Open when tracing the authoritative apply execution path, including preflight validation, per-op rollback, and live snapshot creation.
        - Escalates-to: codex/standards/std_apply.json; tools/meta/apply.py::restore_apply_snapshot
        - Navigation-group: meta_tooling
        
        """
        compiled_plan = self.compile_apply_plan(plan)
        ops = compiled_plan.get("operations", [])
        log = []
        diffs = []
        failures = []
        warnings = []
        planned_files: List[str] = []
        for op in ops:
            if not isinstance(op, dict) or not op.get("target"):
                continue
            try:
                planned_files.append(
                    self._normalize_repo_path(op.get("target"), field_name="operation.target")
                )
            except ApplyError:
                planned_files.append(str(op.get("target")))
        planned_files = sorted(set(planned_files))

        # 0a. Required Field Validation (from schema)
        allowed_ops_spec = self.std_apply.get("allowed_ops", {})
        for i, op in enumerate(ops):
            op_type = op.get("op")
            spec = allowed_ops_spec.get(op_type, {})
            for field in spec.get("required", []):
                if field not in op or not op[field]:
                    raise ApplyError(f"Op {i} ({op_type}): missing required field '{field}'", i, op)

        routing_summary = self.summarize_target_routing(
            ops,
            strict=enforce_target_routing,
            preferred_family=preferred_target_family,
        )
        warnings.extend(routing_summary.get("warnings", []))

        # 0b. Preflight Validation
        if validate_only or dry_run:
            pf_warnings = self._preflight_check(ops)
            if pf_warnings:
                warnings.extend(pf_warnings)
            if validate_only:
                return {
                    "logs": ["Preflight validation successful"],
                    "warnings": warnings,
                    "dry_run": True,
                    "touched_files": planned_files,
                    "target_routing": routing_summary,
                }

        ghost_snapshot = self.ghost_fs.copy()
        poisoned_files: set = set()
        original_states: Dict[str, Dict[str, Any]] = {}
        group_original_states: Dict[str, Dict[str, Dict[str, Any]]] = {}
        group_order: List[str] = []

        try:
            for i, op in enumerate(ops):
                op_type = op.get("op")
                raw_target = op.get("target")
                group_label = str(op.get("group_label") or "").strip() or "ungrouped"
                if group_label not in group_order:
                    group_order.append(group_label)

                if not raw_target:
                    raise ApplyError(f"Missing target", i, op, completed_ops=log)
                try:
                    target = self._normalize_repo_path(raw_target, field_name=f"operations[{i}].target")
                except ApplyError as path_err:
                    raise ApplyError(path_err.message, i, op, completed_ops=log)
                op = dict(op)
                op["target"] = target
                if op_type not in self.allowed_ops:
                    raise ApplyError(f"Unknown op '{op_type}' (Not in allowed_ops)", i, op, completed_ops=log)

                # Skip ops on files that already broke
                if target in poisoned_files:
                    skip_msg = f"Op {i} ({op_type}) SKIPPED — prior failure on {target}"
                    log.append(skip_msg)
                    continue

                # Snapshot THIS file before mutation
                file_snapshot = self.ghost_fs.get(target)  # None if not yet touched

                try:
                    # 1. Load Context
                    if op_type == "create_file":
                        if (self.root / target).exists():
                             raise ApplyError(f"Cannot create {target}, exists on disk.", i, op, completed_ops=log)
                        if target in self.ghost_fs:
                             raise ApplyError(f"Cannot create {target}, exists in Ghost FS.", i, op, completed_ops=log)
                        current_content = ""
                    else:
                        current_content = self.read_file(target)
                        if not current_content and not (self.root / target).exists() and op_type != "overwrite":
                             raise ApplyError(f"Target {target} not found.", i, op, completed_ops=log)

                    if target not in original_states:
                        original_states[target] = {
                            "existed_before": (self.root / target).exists(),
                            "content": current_content,
                        }
                    group_state = group_original_states.setdefault(group_label, {})
                    if target not in group_state:
                        group_state[target] = {
                            "existed_before": (self.root / target).exists(),
                            "content": current_content,
                        }

                    # 2. Execute Operation
                    if op_type == "replace_block":
                        new_content = self._op_replace_block(current_content, op)
                    elif op_type == "replace_function":
                        new_content = self._op_replace_function(current_content, op)
                    elif op_type == "insert_function":
                        new_content = self._op_insert_function(current_content, op)
                    elif op_type == "add_import":
                        new_content = self._op_add_import(current_content, op)
                    elif op_type == "inject_tag":
                        new_content = self._op_inject_tag(current_content, op)
                    elif op_type == "update_docstring":
                        new_content = self._op_update_docstring(current_content, op)
                    elif op_type == "patch_map":
                        new_content = self._op_patch_map(current_content, op)
                    elif op_type == "reference_artifact":
                        new_content = self._op_reference_artifact(current_content, op)
                    elif op_type == "append_section":
                        new_content = self._op_append_section(current_content, op)
                    elif op_type == "replace_section":
                        new_content = self._op_replace_section(current_content, op)
                    elif op_type in ("overwrite", "create_file"):
                        new_content = op.get("content", "")
                    else:
                        new_content = current_content

                    # 3. Capture Diff (Optional)
                    if capture_diffs:
                        diff = self._generate_diff(target, current_content, new_content)
                        if diff: diffs.append(f"--- Op {i}: {target} ---\n{diff}")

                    # 4. Update Ghost FS
                    self.write_ghost(target, new_content)
                    log.append(f"Op {i} ({op_type}) applied to {target}")

                    # 5. Atomic Syntax Check (Fail Fast)
                    if target.endswith(".py") and new_content.strip():
                        self._validate_syntax(target, new_content, i, op, log)

                except (ApplyError, SyntaxError) as inner_err:
                    # Rollback just this file
                    if file_snapshot is not None:
                        self.ghost_fs[target] = file_snapshot
                    elif target in self.ghost_fs:
                        del self.ghost_fs[target]

                    err_msg = inner_err.message if isinstance(inner_err, ApplyError) else str(inner_err)
                    error_entry = f"Op {i} ({op_type}) FAILED on {target}: {err_msg}"
                    log.append(error_entry)
                    failures.append({"op_index": i, "op": op, "error": err_msg})
                    poisoned_files.add(target)

                    if not dry_run:
                        # In live mode, still fail fast — don't leave a half-applied codebase
                        if isinstance(inner_err, ApplyError):
                            inner_err.touched_files = sorted(self.ghost_fs.keys())
                        self.ghost_fs = ghost_snapshot
                        if isinstance(inner_err, ApplyError):
                            inner_err.completed_ops = log
                            raise inner_err
                        raise ApplyError(
                            f"Logic Error: {err_msg}",
                            i,
                            op,
                            completed_ops=log,
                            touched_files=sorted(self.ghost_fs.keys()),
                        )

                except Exception as e:
                    # Rollback just this file
                    if file_snapshot is not None:
                        self.ghost_fs[target] = file_snapshot
                    elif target in self.ghost_fs:
                        del self.ghost_fs[target]

                    err_msg = str(e)
                    log.append(f"Op {i} ({op_type}) FAILED on {target}: {err_msg}")
                    failures.append({"op_index": i, "op": op, "error": err_msg})
                    poisoned_files.add(target)

                    if not dry_run:
                        touched_files = sorted(self.ghost_fs.keys())
                        self.ghost_fs = ghost_snapshot
                        raise ApplyError(
                            f"Logic Error: {err_msg}",
                            i,
                            op,
                            completed_ops=log,
                            touched_files=touched_files,
                        )

        except ApplyError:
            self.ghost_fs = ghost_snapshot  # Full rollback on live-mode raise
            raise

        # 6. Commit
        snapshot_summary: Dict[str, Any] = {}
        if not dry_run:
            snapshot_summary = self._write_live_apply_snapshot(
                original_states,
                snapshot_id=snapshot_id,
                group_original_states=group_original_states,
                group_order=group_order,
            )
            for rel_path, content in self.ghost_fs.items():
                abs_path = self.root / rel_path
                abs_path.parent.mkdir(parents=True, exist_ok=True)
                abs_path.write_text(content, encoding="utf-8")

        return {
            "logs": log,
            "diffs": diffs,
            "failures": failures,
            "warnings": warnings,
            "touched_files": sorted(self.ghost_fs.keys()),
            "snapshot": snapshot_summary,
            "target_routing": routing_summary,
        }

    def _preflight_check(self, ops: List[Dict]) -> List[str]:
        """Validates payloads before any execution. Returns warnings list."""
        warnings = []
        for i, op in enumerate(ops):
            op_type = op.get("op")
            code_to_check = []
            if op_type == "replace_function":
                code_to_check.append(op.get("new_body", ""))
            elif op_type == "insert_function":
                code_to_check.append(op.get("code", ""))
            elif op_type == "add_import":
                code_to_check.append(op.get("statement", ""))
            elif op_type == "patch_map":
                target = self._normalize_repo_path(
                    op.get("target"),
                    field_name=f"operations[{i}].target",
                )
                source = self.read_file(target)
                self._validate_patch_map(source, op, op_index=i)
            elif op_type == "reference_artifact":
                target = self._normalize_repo_path(
                    op.get("target"),
                    field_name=f"operations[{i}].target",
                )
                source = self.read_file(target)
                self._validate_reference_artifact(source, op, op_index=i)
            elif op_type in {"append_section", "replace_section"}:
                target = self._normalize_repo_path(
                    op.get("target"),
                    field_name=f"operations[{i}].target",
                )
                source = self.read_file(target)
                self._validate_markdown_section_op(source, op, op_index=i)

            for code in code_to_check:
                if not code: continue
                try:
                    wrapped = f"class _PreflightCheck:\n{textwrap.indent(code, '    ')}"
                    ast.parse(wrapped)
                except SyntaxError as e:
                    raise ApplyError(f"Preflight Syntax Check Failed: {e.msg}", i, op, detail=str(e))

            # Safety: detect docstrings being injected via replace_block
            if op_type == "replace_block":
                search_text = op.get("search", "")
                replace_text = op.get("replace", "")
                has_def_or_class = ("def " in search_text or "class " in search_text)
                replace_has_docstring = '"""' in replace_text or "'''" in replace_text
                search_has_docstring = '"""' in search_text or "'''" in search_text
                if has_def_or_class and replace_has_docstring and not search_has_docstring:
                    warnings.append(
                        f"Op {i}: UNSAFE — replace_block injects docstring into a signature/code fragment. "
                        f"Use 'update_docstring' instead for reliable AST-aware docstring insertion."
                    )
        return warnings

    def _generate_diff(self, filename: str, old: str, new: str) -> str:
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        diff = difflib.unified_diff(old_lines, new_lines, fromfile=f"a/{filename}", tofile=f"b/{filename}", n=3)
        return "".join(diff)

    def _validate_syntax(self, filename: str, content: str, op_index: int, op: Dict, log: List[str]):
        try:
            ast.parse(content)
        except SyntaxError as e:
            lines = content.splitlines()
            start = max(0, e.lineno - 4)
            end = min(len(lines), e.lineno + 3)
            context = []
            for j in range(start, end):
                marker = ">> " if (j + 1) == e.lineno else "   "
                context.append(f"{marker}{j+1}: {lines[j]}")
            
            detail = f"File: {filename}\nError: {e.msg}\nLine: {e.lineno}\n\nContext:\n" + "\n".join(context)
            raise ApplyError(f"Syntax Broken by Op {op_index}", op_index, op, detail, completed_ops=log)

    # --- OPERATIONS ---

    def _normalize_map_entry_match(self, value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip()).casefold()

    def _split_map_section_entries(self, section_text: str) -> List[str]:
        lines = section_text.strip().splitlines()
        entries: List[str] = []
        current: List[str] = []
        bullet_re = re.compile(r"^([-*+]\s+|\d+\.\s+)")

        for raw_line in lines:
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped:
                if current:
                    entries.append("\n".join(current).rstrip())
                    current = []
                continue
            if bullet_re.match(stripped) and current:
                entries.append("\n".join(current).rstrip())
                current = [line]
                continue
            current.append(line)

        if current:
            entries.append("\n".join(current).rstrip())
        return entries

    def _render_map_section_entries(self, entries: List[str]) -> str:
        cleaned = [entry.rstrip() for entry in entries if str(entry).strip()]
        if not cleaned:
            return ""
        return "\n\n".join(cleaned)

    def _coerce_map_entry_format(self, entry: str, existing_entries: List[str]) -> str:
        text = str(entry or "").strip()
        if not text:
            raise ApplyError("patch_map entry must be a non-empty string.")
        if re.match(r"^([-*+]\s+|\d+\.\s+)", text):
            return text
        for existing in existing_entries:
            stripped = str(existing).strip()
            match = re.match(r"^([-*+]\s+|\d+\.\s+)", stripped)
            if match:
                return f"{match.group(1)}{text}"
        return f"- {text}"

    def _find_map_entry_index(self, entries: List[str], entry_match: str) -> int:
        normalized_match = self._normalize_map_entry_match(entry_match)
        if not normalized_match:
            raise ApplyError("patch_map entry_match must be a non-empty string.")

        normalized_entries = [self._normalize_map_entry_match(entry) for entry in entries]
        exact_matches = [idx for idx, entry in enumerate(normalized_entries) if entry == normalized_match]
        if len(exact_matches) == 1:
            return exact_matches[0]
        if len(exact_matches) > 1:
            raise ApplyError(f"patch_map entry_match is ambiguous: {entry_match}")

        fuzzy_matches = [
            idx for idx, entry in enumerate(normalized_entries)
            if normalized_match in entry
        ]
        if len(fuzzy_matches) == 1:
            return fuzzy_matches[0]
        if len(fuzzy_matches) > 1:
            raise ApplyError(f"patch_map entry_match matched multiple entries: {entry_match}")
        raise ApplyError(f"patch_map entry_match not found: {entry_match}")

    def _replace_map_section_content(self, body: str, section_title: str, new_section_content: str) -> str:
        bounds = find_section_bounds(body, section_title)
        if bounds is None:
            raise ApplyError(f"patch_map requires section '{section_title}' to exist exactly once.")
        _, _, content_start, content_end = bounds
        updated = new_section_content.strip()
        replacement = "\n" + updated + "\n" if updated else "\n"
        return body[:content_start] + replacement + body[content_end:]

    def _validate_patch_map(self, source: str, op: Dict, op_index: int = -1) -> None:
        frontmatter, body = split_frontmatter(source)
        if not frontmatter:
            raise ApplyError("patch_map target must be markdown with frontmatter.", op_index, op)
        if 'kind: "living_map"' not in frontmatter and "kind: living_map" not in frontmatter:
            raise ApplyError("patch_map target must declare kind: living_map.", op_index, op)

        required_sections = ("KNOWN", "BROKEN", "UNKNOWN", "HISTORY")
        for title in required_sections:
            if find_section_bounds(body, title) is None:
                raise ApplyError(f"patch_map target is missing required section '{title}'.", op_index, op)

        patches = op.get("patches")
        if not isinstance(patches, list) or not patches:
            raise ApplyError("patch_map requires a non-empty patches list.", op_index, op)

        allowed_actions = {"append", "prepend", "remove", "replace", "resolve"}
        for patch in patches:
            if not isinstance(patch, dict):
                raise ApplyError("patch_map patches must be objects.", op_index, op)
            section = str(patch.get("section", "")).strip().upper()
            action = str(patch.get("action", "")).strip().lower()
            if section not in required_sections:
                raise ApplyError(f"patch_map section must be one of: {', '.join(required_sections)}", op_index, op)
            if action not in allowed_actions:
                raise ApplyError("patch_map action must be one of: append, prepend, remove, replace, resolve", op_index, op)
            if action in {"append", "prepend"} and not str(patch.get("entry", "")).strip():
                raise ApplyError(f"patch_map action '{action}' requires 'entry'.", op_index, op)
            if action in {"remove", "replace", "resolve"} and not str(patch.get("entry_match", "")).strip():
                raise ApplyError(f"patch_map action '{action}' requires 'entry_match'.", op_index, op)
            if action == "replace" and not str(patch.get("entry", "")).strip():
                raise ApplyError("patch_map action 'replace' requires 'entry'.", op_index, op)
            if action == "resolve" and not str(patch.get("resolution", "")).strip():
                raise ApplyError("patch_map action 'resolve' requires 'resolution'.", op_index, op)
            if action == "resolve" and section == "HISTORY":
                raise ApplyError("patch_map action 'resolve' cannot target HISTORY.", op_index, op)

    def _op_patch_map(self, source: str, op: Dict) -> str:
        self._validate_patch_map(source, op)
        frontmatter, body = split_frontmatter(source)
        patches = op.get("patches", [])

        for patch in patches:
            section_title = str(patch.get("section", "")).strip().upper()
            action = str(patch.get("action", "")).strip().lower()
            bounds = find_section_bounds(body, section_title)
            if bounds is None:
                raise ApplyError(f"patch_map requires section '{section_title}' to exist exactly once.")
            _, _, content_start, content_end = bounds
            section_content = body[content_start:content_end].strip()
            entries = self._split_map_section_entries(section_content)

            if action in {"append", "prepend"}:
                new_entry = self._coerce_map_entry_format(str(patch.get("entry", "")), entries)
                normalized_new_entry = self._normalize_map_entry_match(new_entry)
                if normalized_new_entry not in {self._normalize_map_entry_match(item) for item in entries}:
                    if action == "append":
                        entries.append(new_entry)
                    else:
                        entries.insert(0, new_entry)
                body = self._replace_map_section_content(body, section_title, self._render_map_section_entries(entries))
                continue

            entry_index = self._find_map_entry_index(entries, str(patch.get("entry_match", "")))
            if action == "remove":
                del entries[entry_index]
                body = self._replace_map_section_content(body, section_title, self._render_map_section_entries(entries))
                continue

            if action == "replace":
                replacement = self._coerce_map_entry_format(str(patch.get("entry", "")), entries)
                entries[entry_index] = replacement
                body = self._replace_map_section_content(body, section_title, self._render_map_section_entries(entries))
                continue

            resolution_entry = self._coerce_map_entry_format(str(patch.get("resolution", "")), entries)
            del entries[entry_index]
            body = self._replace_map_section_content(body, section_title, self._render_map_section_entries(entries))

            history_bounds = find_section_bounds(body, "HISTORY")
            if history_bounds is None:
                raise ApplyError("patch_map requires section 'HISTORY' to exist exactly once.")
            _, _, history_start, history_end = history_bounds
            history_entries = self._split_map_section_entries(body[history_start:history_end].strip())
            normalized_resolution = self._normalize_map_entry_match(resolution_entry)
            if normalized_resolution not in {self._normalize_map_entry_match(item) for item in history_entries}:
                history_entries.insert(0, self._coerce_map_entry_format(resolution_entry, history_entries))
            body = self._replace_map_section_content(body, "HISTORY", self._render_map_section_entries(history_entries))

        return frontmatter + body

    def _validate_reference_artifact(self, source: str, op: Dict, op_index: int = -1) -> None:
        frontmatter, body = split_frontmatter(source)
        if not frontmatter:
            raise ApplyError("reference_artifact target must be markdown with frontmatter.", op_index, op)
        normalized_target = self._normalize_repo_path(
            op.get("target"),
            field_name=f"operations[{op_index}].target" if op_index >= 0 else "target",
        )
        target_kind = markdown_kind(source)
        try:
            target_family, target_kind = resolve_reference_artifact_target_family(
                target_text=source,
                target_path=normalized_target,
            )
        except ValueError as exc:
            raise ApplyError(str(exc), op_index, op)

        section = str(op.get("section", "")).strip()
        if target_family == "living_map":
            required_sections = ("KNOWN", "BROKEN", "UNKNOWN", "HISTORY")
            for title in required_sections:
                if find_section_bounds(body, title) is None:
                    raise ApplyError(f"reference_artifact target is missing required section '{title}'.", op_index, op)
            if section and section.upper() not in required_sections:
                raise ApplyError(
                    "reference_artifact section for living_map must be one of: KNOWN, BROKEN, UNKNOWN, HISTORY",
                    op_index,
                    op,
                )
        elif not section:
            if target_family == "idea_packet":
                raise ApplyError("reference_artifact requires 'section' when target kind is idea_packet.", op_index, op)
            raise ApplyError("reference_artifact requires 'section' when target is an authored obsidian note.", op_index, op)
        elif find_section_bounds(body, section) is None:
            raise ApplyError(
                f"reference_artifact target section was not found or was ambiguous: {section}",
                op_index,
                op,
            )

        source_artifact = self._normalize_repo_path(
            op.get("source_artifact"),
            field_name=f"operations[{op_index}].source_artifact" if op_index >= 0 else "source_artifact",
        )
        source_text = self.read_file(source_artifact)
        if not source_text and not (self.root / source_artifact).exists():
            raise ApplyError(f"reference_artifact source not found: {source_artifact}", op_index, op)
        try:
            extract_observe_artifact_payload(
                source_text=source_text,
                source_artifact=source_artifact,
            )
        except ValueError as exc:
            raise ApplyError(str(exc), op_index, op)

    def _op_reference_artifact(self, source: str, op: Dict) -> str:
        self._validate_reference_artifact(source, op)
        target_kind = str(markdown_kind(source) or "").strip()
        source_artifact = self._normalize_repo_path(op.get("source_artifact"), field_name="source_artifact")
        source_text = self.read_file(source_artifact)
        artifact = extract_observe_artifact_payload(
            source_text=source_text,
            source_artifact=source_artifact,
        )
        try:
            updated, _ = apply_reference_to_text(
                existing_text=source,
                target_kind=target_kind,
                target_path=self._normalize_repo_path(op.get("target"), field_name="target"),
                source_key=str(artifact.get("source_key") or source_artifact),
                source_artifact=source_artifact,
                observe_id=str(artifact.get("observe_id") or ""),
                generated_at=str(artifact.get("generated_at") or ""),
                payload_markdown=str(artifact.get("payload_markdown") or ""),
                section_title=op.get("section"),
                summary=artifact.get("summary"),
            )
        except ValueError as exc:
            raise ApplyError(str(exc), op=op)
        return updated

    def _validate_markdown_section_op(self, source: str, op: Dict, op_index: int = -1) -> None:
        section = str(op.get("section", "")).strip()
        if not section:
            raise ApplyError(f"{op.get('op')} requires a non-empty 'section'.", op_index, op)
        if "content" not in op:
            raise ApplyError(f"{op.get('op')} requires 'content'.", op_index, op)
        target = self._normalize_repo_path(
            op.get("target"),
            field_name=f"operations[{op_index}].target" if op_index >= 0 else "target",
        )
        if not str(target).lower().endswith((".md", ".markdown")):
            raise ApplyError(f"{op.get('op')} target must be markdown.", op_index, op)
        _, body = split_frontmatter(source)
        if find_section_bounds(body or "", section) is None:
            raise ApplyError(
                f"{op.get('op')} target section was not found or was ambiguous: {section}",
                op_index,
                op,
            )

    def _rewrite_markdown_section(self, source: str, *, section: str, content: str, mode: str) -> str:
        frontmatter, body = split_frontmatter(source)
        body = body or ""
        bounds = find_section_bounds(body, section)
        if bounds is None:
            raise ApplyError(f"{mode} target section was not found or was ambiguous: {section}")
        _, _, content_start, content_end = bounds
        existing = body[content_start:content_end].rstrip()
        incoming = str(content).rstrip()
        if mode == "append_section":
            new_section = existing
            if existing and incoming:
                new_section = existing + "\n\n" + incoming
            elif incoming:
                new_section = incoming
        else:
            new_section = incoming
        new_body = body[:content_start] + "\n" + new_section + "\n" + body[content_end:]
        return frontmatter + new_body

    def _op_append_section(self, source: str, op: Dict) -> str:
        self._validate_markdown_section_op(source, op)
        return self._rewrite_markdown_section(
            source,
            section=str(op.get("section", "")).strip(),
            content=str(op.get("content", "")),
            mode="append_section",
        )

    def _op_replace_section(self, source: str, op: Dict) -> str:
        self._validate_markdown_section_op(source, op)
        return self._rewrite_markdown_section(
            source,
            section=str(op.get("section", "")).strip(),
            content=str(op.get("content", "")),
            mode="replace_section",
        )

    def _op_replace_block(self, source: str, op: Dict) -> str:
        search = op.get("search", "")
        replace = op.get("replace", "")
        if not search: return source

        if search in source:
            return source.replace(search, replace, 1)

        # Fuzzy regex fallback — only when explicitly opted in
        if op.get("fuzzy", False):
            search_pattern = re.escape(search)
            search_pattern = search_pattern.replace(r'\ ', r'\s+').replace(r'\n', r'\s+')
            regex = re.compile(search_pattern, re.MULTILINE)

            match = regex.search(source)
            if match:
                start, end = match.span()
                return source[:start] + replace + source[end:]

        s = difflib.SequenceMatcher(None, source, search)
        match = s.find_longest_match(0, len(source), 0, len(search))

        hint = ""
        if "def " in search or "class " in search:
            hint = "\n[HINT] This looks like code. Consider using 'replace_function' for reliable AST-based replacement."

        if match.size > len(search) * 0.6:
            line_no = source[:match.a].count('\n') + 1
            found_snippet = source[match.a : match.a + match.size]
            raise ApplyError(f"Exact match failed. Closest partial match at line {line_no}.{hint}\nMatch content:\n{found_snippet}...")

        raise ApplyError(f"Search text not found.{hint}")

    def _op_add_import(self, source: str, op: Dict) -> str:
        stmt = op.get("statement", "").strip()
        if stmt in source: return source 
        
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return f"{stmt}\n{source}"
            
        last_import_end = 0
        docstring_end = 0
        
        if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, (ast.Str, ast.Constant)):
            docstring_end = tree.body[0].end_lineno

        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                last_import_end = max(last_import_end, node.end_lineno)
            elif isinstance(node, (ast.Try, ast.If)):
                has_import = any(isinstance(c, (ast.Import, ast.ImportFrom)) for c in node.body)
                if has_import:
                    last_import_end = max(last_import_end, node.end_lineno)

        insert_line = last_import_end if last_import_end > 0 else docstring_end
        
        lines = source.splitlines(keepends=True)
        if insert_line > len(lines): insert_line = len(lines)
        
        new_lines = lines[:insert_line] + [f"{stmt}\n"] + lines[insert_line:]
        return "".join(new_lines)

    def _op_replace_function(self, source: str, op: Dict) -> str:
        name = op.get("function_name")
        new_body = op.get("new_body")
        node = self._find_node(source, name, "function")
        if not node: raise ApplyError(f"Function '{name}' not found.")
        
        original_indent = node.col_offset
        new_body_lines = new_body.splitlines()
        
        if new_body_lines:
            first_line_content = new_body_lines[0]
            current_indent = len(first_line_content) - len(first_line_content.lstrip())
            
            if current_indent == 0 and original_indent > 0:
                new_body = textwrap.indent(new_body, " " * original_indent)
            elif current_indent != original_indent:
                raise ApplyError(f"Indentation Mismatch: Original '{name}' indent={original_indent}, new_body indent={current_indent}. Please align them.")

        lines = source.splitlines(keepends=True)
        return "".join(lines[:node.lineno-1]) + new_body + "\n" + "".join(lines[node.end_lineno:])

    def _op_insert_function(self, source: str, op: Dict) -> str:
        after_name = op.get("after_function")
        code = op.get("code")
        node = self._find_node(source, after_name, "function")
        if not node: raise ApplyError(f"Reference function '{after_name}' not found.")
        
        lines = source.splitlines(keepends=True)
        insert_idx = node.end_lineno
        return "".join(lines[:insert_idx]) + "\n\n" + code + "\n" + "".join(lines[insert_idx:])

    def _op_inject_tag(self, source: str, op: Dict) -> str:
        scope = op.get("scope", "module")
        tag = op.get("tag")
        content = op.get("content")

        tree = ast.parse(source)
        target_node = self._resolve_target_node(tree, scope)

        if not target_node: raise ApplyError(f"Scope target '{scope}' not found.")

        doc_node = None
        if (target_node.body and isinstance(target_node.body[0], ast.Expr) and
            isinstance(target_node.body[0].value, (ast.Str, ast.Constant))):
            doc_node = target_node.body[0]

        lines = source.splitlines(keepends=True)

        if not doc_node:
            indent_level = 0
            if hasattr(target_node, 'col_offset'):
                indent_level = target_node.col_offset + 4

            indent_str = " " * indent_level
            new_docstring = f'{indent_str}"""\n{indent_str}[{tag}]\n{indent_str}{content}\n{indent_str}"""\n'

            if scope == "module":
                insert_line = 0
            else:
                if target_node.body:
                    insert_line = target_node.body[0].lineno - 1
                else:
                    insert_line = target_node.end_lineno

            lines.insert(insert_line, new_docstring)
            return "".join(lines)

        else:
            start = doc_node.lineno - 1
            end = doc_node.end_lineno

            raw_doc_lines = lines[start:end]
            raw_doc = "".join(raw_doc_lines)

            if f"[{tag}]" in raw_doc:
                pattern = re.compile(re.escape(f"[{tag}]") + r".*?(?=\n\s*\[|$)", re.DOTALL)
                new_doc = pattern.sub(f"[{tag}]\n{content}", raw_doc)
            else:
                stripped = raw_doc.strip()
                quote = '"""' if stripped.endswith('"""') else "'''"
                if quote not in raw_doc: quote = ""

                if quote:
                    parts = raw_doc.rsplit(quote, 1)
                    pre_quote = parts[0].rstrip()
                    last_line = raw_doc_lines[-1]
                    indent = last_line[:len(last_line) - len(last_line.lstrip())]
                    new_doc = f"{pre_quote}\n\n{indent}[{tag}]\n{indent}{content}\n{indent}{quote}{parts[1]}"
                else:
                     new_doc = raw_doc + f"\n[{tag}]\n{content}"

            return "".join(lines[:start]) + new_doc + "".join(lines[end:])

    def _op_update_docstring(self, source: str, op: Dict) -> str:
        """AST-aware docstring upsert. Replaces if exists, inserts if missing."""
        scope = op.get("scope", "module")
        new_doc_content = op.get("content", "")

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ApplyError(f"Cannot parse source for update_docstring: {e}")

        target_node = self._resolve_target_node(tree, scope)
        if not target_node:
            raise ApplyError(f"update_docstring: scope target '{scope}' not found.")

        lines = source.splitlines(keepends=True)

        # Detect existing docstring
        has_docstring = False
        if (target_node.body and isinstance(target_node.body[0], ast.Expr) and
            isinstance(target_node.body[0].value, (ast.Str, ast.Constant))):
            has_docstring = True
            doc_node = target_node.body[0]

        if has_docstring:
            # --- SCENARIO A: Replace existing docstring ---
            doc_start = doc_node.lineno - 1  # 0-indexed
            doc_end = doc_node.end_lineno      # exclusive

            # Detect original quote style from existing docstring
            first_doc_line = lines[doc_start] if doc_start < len(lines) else ""
            stripped_first = first_doc_line.lstrip()
            quote_style = '"""'
            if stripped_first.startswith("'''"):
                quote_style = "'''"

            # Determine indentation from the existing docstring line
            indent_str = first_doc_line[:len(first_doc_line) - len(first_doc_line.lstrip())]

            # Build new docstring
            doc_lines = new_doc_content.split("\n")
            new_docstring_parts = [f"{indent_str}{quote_style}\n"]
            for dl in doc_lines:
                new_docstring_parts.append(f"{indent_str}{dl}\n")
            new_docstring_parts.append(f"{indent_str}{quote_style}\n")
            new_docstring = "".join(new_docstring_parts)

            return "".join(lines[:doc_start]) + new_docstring + "".join(lines[doc_end:])

        else:
            # --- SCENARIO B: Insert new docstring ---
            if scope == "module":
                # Module-level: insert at line 0
                indent_str = ""
                insert_line = 0
            else:
                # Function/class/method — insert after the def/class line
                # Determine indentation from the first body statement
                if target_node.body:
                    first_body_line = lines[target_node.body[0].lineno - 1] if target_node.body[0].lineno - 1 < len(lines) else ""
                    indent_str = first_body_line[:len(first_body_line) - len(first_body_line.lstrip())]
                    insert_line = target_node.body[0].lineno - 1
                else:
                    # Empty body (e.g. `def foo(): pass` with no actual body nodes)
                    indent_str = " " * (target_node.col_offset + 4)
                    insert_line = target_node.end_lineno

            # Build the docstring
            doc_lines = new_doc_content.split("\n")
            new_docstring_parts = [f"{indent_str}\"\"\"\n"]
            for dl in doc_lines:
                new_docstring_parts.append(f"{indent_str}{dl}\n")
            new_docstring_parts.append(f"{indent_str}\"\"\"\n")
            new_docstring = "".join(new_docstring_parts)

            return "".join(lines[:insert_line]) + new_docstring + "".join(lines[insert_line:])

    # --- HELPERS ---

    def _resolve_target_node(self, tree: ast.AST, scope: str) -> Optional[ast.AST]:
        """
        [ACTION]
        - Teleology: Unified AST scope resolver. Delegates to
          `system.lib.python_scope_query.python_scope_resolve` so the dispatch lives in
          one named primitive shared with `_run_deterministic_gates`'s scope_addressable
          gate (via `python_scope_exists`); see system/server/tests/test_observe_compiler.py
          for the pinned parity matrix.
        - Supports: module, class:X, func:X, method:X.Y, bare names (top-level FunctionDef
          or ClassDef lookup, no class-body descent), and the func/method aliases
          surfaced by `normalize_python_scope_selector`.
        - func:X searches ONLY top-level (tree.body), never walks into classes.
        - method:X.Y finds ClassDef X, then searches ONLY its .body for FunctionDef Y.
        """
        return python_scope_resolve(tree, scope)

    def _find_node(self, source: str, name: str, type_str: str) -> Optional[ast.AST]:
        """Legacy helper — used by replace_function/insert_function."""
        try:
            tree = ast.parse(source)
            return self._find_node_in_tree(tree, name, type_str)
        except SyntaxError:
            return None

    def _find_node_in_tree(self, tree: ast.AST, name: str, type_str: str) -> Optional[ast.AST]:
        """Legacy helper — walks entire tree (used by _find_node)."""
        for node in ast.walk(tree):
            if type_str == "function" and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == name: return node
            elif type_str == "class" and isinstance(node, ast.ClassDef):
                if node.name == name: return node
        return None

    def _extract_outline(self, content: str, rel_path: str) -> str:
        """Return a compact structural outline of a Python file.

        Extracts imports, module-level assignments, class definitions
        (with bases, docstrings, and method signatures), and top-level
        function definitions (with signatures and docstrings).  Function
        and method *bodies* are omitted — only the ``...`` placeholder
        is shown.  This typically reduces a 670 KB file to ~30 KB while
        preserving every name the rest of the codebase can reference.

        For non-Python files we fall back to a line-count summary with
        the first and last 40 lines shown.
        """
        is_python = rel_path.endswith(".py")
        if not is_python:
            return self._extract_outline_fallback(content, rel_path)

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return self._extract_outline_fallback(content, rel_path)

        lines = content.splitlines()
        parts: list[str] = []

        def _src(node: ast.AST) -> str:
            """Best-effort source for a single AST node via ast.unparse (3.9+)."""
            try:
                return ast.unparse(node)
            except Exception:
                # Fallback: grab source lines
                if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                    return "\n".join(lines[node.lineno - 1 : node.end_lineno])
                return repr(node)

        def _docstring(node: ast.AST) -> str | None:
            """Extract docstring from a class/function/module body."""
            body = getattr(node, "body", None)
            if not body:
                return None
            first = body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, (ast.Constant, ast.Str)):
                val = first.value
                s = val.value if isinstance(val, ast.Constant) else val.s
                if isinstance(s, str):
                    # Truncate very long docstrings
                    if len(s) > 300:
                        s = s[:300] + "..."
                    return s
            return None

        def _decorator_lines(node: ast.AST) -> list[str]:
            decorators = getattr(node, "decorator_list", [])
            out: list[str] = []
            for dec in decorators:
                out.append(f"@{_src(dec)}")
            return out

        def _func_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
            """Render a function/method signature line."""
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            args = _src(node.args) if node.args else ""
            ret = ""
            if node.returns:
                ret = f" -> {_src(node.returns)}"
            return f"{prefix} {node.name}({args}){ret}:"

        def _class_header(node: ast.ClassDef) -> str:
            bases = ", ".join(_src(b) for b in node.bases)
            kws = ", ".join(f"{kw.arg}={_src(kw.value)}" for kw in node.keywords)
            all_args = ", ".join(filter(None, [bases, kws]))
            return f"class {node.name}({all_args}):" if all_args else f"class {node.name}:"

        # --- Module-level docstring ---
        mod_doc = _docstring(tree)
        if mod_doc:
            parts.append(f'"""{mod_doc}"""')
            parts.append("")

        # --- Walk top-level nodes ---
        for node in ast.iter_child_nodes(tree):
            # Imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                parts.append(_src(node))

            # Module-level assignments / constants
            elif isinstance(node, ast.Assign):
                # Only show if the target is a simple name (not unpacking)
                targets = node.targets
                if len(targets) == 1 and isinstance(targets[0], ast.Name):
                    name = targets[0].id
                    # Show value for small literals, else just type hint
                    val_src = _src(node.value)
                    if len(val_src) > 120:
                        val_src = val_src[:120] + "..."
                    parts.append(f"{name} = {val_src}")

            elif isinstance(node, ast.AnnAssign) and node.target and isinstance(node.target, ast.Name):
                name = node.target.id
                ann = _src(node.annotation)
                if node.value:
                    val_src = _src(node.value)
                    if len(val_src) > 120:
                        val_src = val_src[:120] + "..."
                    parts.append(f"{name}: {ann} = {val_src}")
                else:
                    parts.append(f"{name}: {ann}")

            # Top-level functions
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                parts.append("")
                for dl in _decorator_lines(node):
                    parts.append(dl)
                parts.append(_func_signature(node))
                doc = _docstring(node)
                if doc:
                    parts.append(f'    """{doc}"""')
                parts.append("    ...")

            # Classes
            elif isinstance(node, ast.ClassDef):
                parts.append("")
                for dl in _decorator_lines(node):
                    parts.append(dl)
                parts.append(_class_header(node))
                cdoc = _docstring(node)
                if cdoc:
                    parts.append(f'    """{cdoc}"""')

                # Class-level assignments
                for child in node.body:
                    if isinstance(child, ast.Assign):
                        for target in child.targets:
                            if isinstance(target, ast.Name):
                                val_src = _src(child.value)
                                if len(val_src) > 100:
                                    val_src = val_src[:100] + "..."
                                parts.append(f"    {target.id} = {val_src}")
                    elif isinstance(child, ast.AnnAssign) and child.target and isinstance(child.target, ast.Name):
                        ann = _src(child.annotation)
                        if child.value:
                            val_src = _src(child.value)
                            if len(val_src) > 100:
                                val_src = val_src[:100] + "..."
                            parts.append(f"    {child.target.id}: {ann} = {val_src}")
                        else:
                            parts.append(f"    {child.target.id}: {ann}")

                # Methods
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        parts.append("")
                        for dl in _decorator_lines(child):
                            parts.append(f"    {dl}")
                        sig = _func_signature(child)
                        parts.append(f"    {sig}")
                        mdoc = _docstring(child)
                        if mdoc:
                            parts.append(f'        """{mdoc}"""')
                        parts.append("        ...")

        outline = "\n".join(parts)
        total_lines = len(lines)
        header = f"# OUTLINE of {rel_path} ({total_lines} lines, {len(content)} bytes)\n"
        return header + outline

    def _extract_outline_fallback(self, content: str, rel_path: str) -> str:
        """Fallback outline for non-Python files: bounded structural summary + samples."""
        lines = content.splitlines()
        total = len(lines)
        if total <= 80 and len(content) <= 80_000:
            return content
        if rel_path.endswith(".json"):
            try:
                payload = json.loads(content)
            except Exception:
                payload = None
            if payload is not None:
                summary = [
                    f"# OUTLINE of {rel_path} ({total} lines, {len(content)} bytes)",
                    "# JSON structural summary",
                ]
                if isinstance(payload, dict):
                    keys = list(payload.keys())
                    summary.append(f"top_level_type: object")
                    summary.append(f"top_level_key_count: {len(keys)}")
                    for key in keys[:80]:
                        value = payload.get(key)
                        if isinstance(value, dict):
                            detail = f"object keys={len(value)} sample_keys={list(value.keys())[:12]}"
                        elif isinstance(value, list):
                            sample_types = sorted({type(item).__name__ for item in value[:20]})
                            detail = f"array length={len(value)} sample_item_types={sample_types}"
                        elif isinstance(value, str):
                            detail = f"string chars={len(value)} sample={value[:160]!r}"
                        else:
                            detail = f"{type(value).__name__} value={value!r}"
                        summary.append(f"- {key}: {detail}")
                    if len(keys) > 80:
                        summary.append(f"- ... {len(keys) - 80} keys omitted")
                elif isinstance(payload, list):
                    sample_types = sorted({type(item).__name__ for item in payload[:50]})
                    summary.append("top_level_type: array")
                    summary.append(f"top_level_length: {len(payload)}")
                    summary.append(f"sample_item_types: {sample_types}")
                    for index, item in enumerate(payload[:20]):
                        if isinstance(item, dict):
                            summary.append(f"- item[{index}]: object keys={list(item.keys())[:20]}")
                        else:
                            summary.append(f"- item[{index}]: {type(item).__name__} value={repr(item)[:180]}")
                    if len(payload) > 20:
                        summary.append(f"- ... {len(payload) - 20} items omitted")
                else:
                    summary.append(f"top_level_type: {type(payload).__name__}")
                    summary.append(f"value_sample: {repr(payload)[:500]}")
                return "\n".join(summary)

        if total <= 80:
            head = content[:4_000]
            tail = content[-4_000:] if len(content) > 4_000 else ""
            return (
                f"# OUTLINE of {rel_path} ({total} lines, {len(content)} bytes)\n"
                f"# --- first 4000 chars ---\n{head}\n"
                f"# --- ... {max(0, len(content) - 8_000)} chars omitted ... ---\n"
                f"# --- last 4000 chars ---\n{tail}"
            )
        head = "\n".join(lines[:40])
        tail = "\n".join(lines[-40:])
        return (
            f"# OUTLINE of {rel_path} ({total} lines, {len(content)} bytes)\n"
            f"# --- first 40 lines ---\n{head}\n"
            f"# --- ... {total - 80} lines omitted ... ---\n"
            f"# --- last 40 lines ---\n{tail}"
        )

    def _extract_imports(self, content: str) -> List[Dict[str, Any]]:
        try: tree = ast.parse(content)
        except SyntaxError: return []
        imports = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({"module": alias.name, "alias": alias.asname, "lineno": node.lineno})
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append({"module": node.module, "lineno": node.lineno})
        return imports

# --- SELF-DOCUMENTATION ---

def _get_usage_examples() -> Dict[str, Any]:
    return {
        "modes": {
            "observe": {
                "description": "Read file contents or analysis.",
                "examples": [
                    {
                        "description": "Observe with context injection and notes",
                        "plan": {
                            "notes": "Checking engine compliance before docstring refactor.",
                            "wait_notes": "Round-1 probe posture: capture facts, inferences, tensions, and unknowns only.",
                            "prompt": "Situation 4 Variant A — structured diagnostic.",
                            "targets": [{"file": "system/core/engine.py", "notes": "Primary target — verify [PURPOSE] and [FLOW] tags."}],
                            "context_files": ["codex/standards/std_python.py"],
                            "print_format": "python",
                            "print_shape": "compact"
                        }
                    },
                    {
                        "description": "Grouped: Batch observations with shared context and notes",
                        "plan": {
                            "notes": "Full server stack audit for Inspector integration.",
                            "wait_notes": "Apply this note to every group report: evidence-first, no fixes.",
                            "prompt": "Situation 9 Variant B — topology-first compact report.",
                            "meta_instruction": "Read attached files deeply. Return a full, evidence-cited response without follow-up questions.",
                            "dump_dir": "obs_output",
                            "context_files": ["codex/standards/std_apply.json"],
                            "print_options": {"format": "json", "shape": "preserve_shape"},
                            "groups": [
                                {
                                    "label": "core_logic",
                                    "notes": "Engine and governance — verify route parity with frontend.",
                                    "targets": [{"file": "system/core/engine.py"}]
                                }
                            ]
                        }
                    }
                ]
            },
            "apply": {
                "description": "Modify files safely using authorized operations.",
                "examples": [
                    {
                        "description": "Basic text replacement",
                        "plan": {
                            "operations": [
                                {
                                    "op": "replace_block",
                                    "target": "path/file.py",
                                    "search": "old_code",
                                    "replace": "new_code"
                                }
                            ]
                        }
                    },
                    {
                        "description": "AST-aware docstring upsert on a method",
                        "plan": {
                            "operations": [
                                {
                                    "op": "update_docstring",
                                    "target": "system/server/session.py",
                                    "scope": "method:SessionManager.ignite_run",
                                    "content": "[ACTION]\n- Teleology: Initialize and start a new run.\n- Fails: Raises HTTPException if engine is busy."
                                }
                            ]
                        }
                    },
                    {
                        "description": "Add docstring to a top-level function",
                        "plan": {
                            "operations": [
                                {
                                    "op": "update_docstring",
                                    "target": "system/lib/utils.py",
                                    "scope": "func:resolve_root",
                                    "content": "[ACTION]\n- Teleology: Locate the repository root directory."
                                }
                            ]
                        }
                    }
                ]
            }
        }
    }


def _resolve_repo_relative_path(root: Path, rel_path: str, *, field_name: str) -> Path:
    candidate = Path(str(rel_path or "").strip())
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ApplyError(f"{field_name} escapes repository root: {rel_path}") from exc
    return resolved


def resolve_apply_snapshot_manifest(root_hint: Optional[str], snapshot_ref: str) -> Path:
    """
    [ACTION]
    - Teleology: Resolve a human-facing snapshot reference into the concrete manifest path for apply rollback.
    - Mechanism: Normalize `latest`, explicit manifest paths, or snapshot IDs under `tools/meta/apply/snapshots/`.
    - Reads: The apply snapshot directory and any explicitly referenced manifest path.
    - Writes: None.
    - Fails: Raises ApplyError when no snapshots exist, the manifest is missing, or the reference escapes the repo root.
    - Guarantee: Returns an on-disk manifest path inside the repository root.
    - When-needed: Open when rollback tooling needs to convert a user-supplied snapshot token into a manifest path before restoring files.
    - Escalates-to: tools/meta/apply.py::restore_apply_snapshot; tools/meta/apply.py
    - Navigation-group: meta_tooling
    """
    root = resolve_root(root_hint)
    token = str(snapshot_ref or "").strip()
    snapshots_dir = root / "tools" / "meta" / "apply" / "snapshots"

    if not token or token == "latest":
        manifests = sorted(
            snapshots_dir.glob("APPLY_*/manifest.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not manifests:
            raise ApplyError("No apply snapshots found.")
        return manifests[0]

    candidate = Path(token)
    if candidate.suffix == ".json":
        resolved = _resolve_repo_relative_path(root, token, field_name="snapshot_ref")
        if not resolved.exists():
            raise ApplyError(f"Apply snapshot manifest not found: {token}")
        return resolved

    manifest_path = (snapshots_dir / token / "manifest.json").resolve()
    try:
        manifest_path.relative_to(root)
    except ValueError as exc:
        raise ApplyError(f"snapshot_ref escapes repository root: {snapshot_ref}") from exc
    if not manifest_path.exists():
        raise ApplyError(f"Apply snapshot manifest not found: {token}")
    return manifest_path


def _restore_snapshot_entries(root: Path, entries: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    restored_files: List[str] = []
    removed_files: List[str] = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        target = str(entry.get("target") or "").strip()
        if not target:
            continue
        target_path = _resolve_repo_relative_path(root, target, field_name="snapshot.target")
        existed_before = bool(entry.get("existed_before"))
        if existed_before:
            snapshot_file = str(entry.get("snapshot_file") or "").strip()
            if not snapshot_file:
                raise ApplyError(f"Snapshot file missing for {target}")
            snapshot_path = _resolve_repo_relative_path(root, snapshot_file, field_name="snapshot.snapshot_file")
            if not snapshot_path.exists():
                raise ApplyError(f"Snapshot file not found for {target}: {snapshot_file}")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(snapshot_path.read_text(encoding="utf-8"), encoding="utf-8")
            restored_files.append(target)
            continue
        if target_path.exists():
            target_path.unlink()
        removed_files.append(target)

    return restored_files, removed_files


def restore_apply_snapshot(
    snapshot_ref: str,
    *,
    root_hint: Optional[str] = None,
    group_label: Optional[str] = None,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Restore files from a saved apply snapshot, optionally from one group suffix onward.
    - Mechanism: Resolve the snapshot manifest, select full-snapshot or group-suffix entries, replay the saved file contents, and report restored/removed targets.
    - Reads: The snapshot manifest plus any referenced snapshot files under `tools/meta/apply/snapshots/`.
    - Writes: Restored file contents to disk and file deletions for targets that did not exist before the snapshot.
    - Fails: Raises ApplyError when snapshot metadata is malformed, missing, or incompatible with the requested group rollback.
    - Guarantee: Returns a summary describing the rollback scope and every restored or removed target.
    - When-needed: Open when an apply run must be rolled back from a saved snapshot or from a specific grouped suffix.
    - Escalates-to: tools/meta/apply.py::resolve_apply_snapshot_manifest; codex/standards/std_apply.json
    - Navigation-group: meta_tooling
    """
    root = resolve_root(root_hint)
    manifest_path = resolve_apply_snapshot_manifest(root, snapshot_ref)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        raise ApplyError("Apply snapshot manifest is malformed: entries must be a list.")

    requested_group = str(group_label or "").strip() or None
    rolled_back_groups: List[str] = []
    rollback_scope = "full_snapshot"
    selected_entries: List[Dict[str, Any]] = [dict(entry) for entry in entries if isinstance(entry, dict)]

    if requested_group:
        group_entries = payload.get("group_entries", [])
        if not isinstance(group_entries, list) or not group_entries:
            raise ApplyError("Apply snapshot manifest does not contain group rollback data.")
        group_order = payload.get("group_order", [])
        if not isinstance(group_order, list):
            group_order = []
        normalized_order = [
            str(label).strip()
            for label in group_order
            if str(label).strip()
        ]
        if requested_group not in normalized_order:
            raise ApplyError(f"Apply snapshot manifest does not include group `{requested_group}`.")
        start_index = normalized_order.index(requested_group)
        rolled_back_groups = normalized_order[start_index:]
        order_index = {label: idx for idx, label in enumerate(rolled_back_groups)}
        restore_by_target: Dict[str, Dict[str, Any]] = {}
        for raw_entry in group_entries:
            if not isinstance(raw_entry, dict):
                continue
            current_group = str(raw_entry.get("group_label") or "").strip()
            if current_group not in order_index:
                continue
            target = str(raw_entry.get("target") or "").strip()
            if not target:
                continue
            existing = restore_by_target.get(target)
            if existing is None or order_index[current_group] < order_index[str(existing.get("group_label") or "").strip()]:
                restore_by_target[target] = dict(raw_entry)
        selected_entries = list(restore_by_target.values())
        rollback_scope = "group_suffix"

    restored_files, removed_files = _restore_snapshot_entries(root, selected_entries)

    return {
        "snapshot_id": str(payload.get("snapshot_id") or manifest_path.parent.name),
        "snapshot_manifest": str(manifest_path.relative_to(root)),
        "restored_files": restored_files,
        "removed_files": removed_files,
        "rollback_scope": rollback_scope,
        "requested_group_label": requested_group,
        "rolled_back_groups": rolled_back_groups,
    }


def summarize_apply_target_routing(
    plan: Dict[str, Any],
    *,
    root_hint: Optional[str] = None,
    strict: bool = False,
    preferred_target_family: Optional[str] = None,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Provide a top-level helper that explains target-routing posture for an apply payload without executing it.
    - Mechanism: Instantiate SourceSurgeon, compile the apply plan into operations, and delegate to summarize_target_routing().
    - Reads: The in-memory plan plus routing rules from `std_apply.json`.
    - Writes: None.
    - Fails: Raises ApplyError when the compiled plan does not expose an operations list.
    - Guarantee: Returns the same routing-summary shape as `SourceSurgeon.summarize_target_routing()`.
    - When-needed: Open when another tool needs routing/trust diagnostics for an apply plan but should not run the plan itself.
    - Escalates-to: tools/meta/apply.py::compile_apply_plan; codex/standards/std_apply.json
    - Navigation-group: meta_tooling
    """
    surgeon = SourceSurgeon(root_hint)
    compiled_plan = surgeon.compile_apply_plan(plan if isinstance(plan, dict) else {})
    operations = compiled_plan.get("operations", [])
    if not isinstance(operations, list):
        raise ApplyError("Apply plan must expose an operations list for target routing summary.")
    return surgeon.summarize_target_routing(
        operations,
        strict=strict,
        preferred_family=preferred_target_family,
    )


def compile_apply_plan(
    plan: Dict[str, Any],
    *,
    root_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Expose apply-plan compilation without requiring callers to manage a SourceSurgeon instance.
    - Mechanism: Build a transient SourceSurgeon and delegate to its compile_apply_plan() method.
    - Reads: The supplied plan payload and any disk state needed during diff expansion.
    - Writes: None.
    - Fails: Propagates ApplyError from SourceSurgeon.compile_apply_plan().
    - Guarantee: Returns a normalized apply plan containing an `operations` list.
    - When-needed: Open when a meta-tool wants canonical apply-plan normalization as a pure helper.
    - Escalates-to: tools/meta/apply.py::summarize_apply_target_routing; tools/meta/apply.py::run
    - Navigation-group: meta_tooling
    """
    surgeon = SourceSurgeon(root_hint)
    return surgeon.compile_apply_plan(plan if isinstance(plan, dict) else {})

# --- ENTRYPOINT ---

def run(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Tool entrypoint that routes to `observe` or `apply` execution and wraps results in a stable envelope.
    - Preconditions: None.
    - Reads: Config/plan; filesystem for standards and targets.
    - Writes: In `apply` with `dry_run` false, writes mutated files; in grouped observe, writes dumps.
    - Fails: Returns metadata.status 'failure' on ApplyError or invalid mode.
    - Guarantee: Always returns a dict with `metadata` and either `data` or `usage_guide`.
    - When-needed: Open when another tool or launcher needs the canonical observe/apply entrypoint and envelope shape for `tools.meta.apply`.
    - Escalates-to: tools/meta/apply.py::compile_apply_plan; tools/meta/apply.py::restore_apply_snapshot; codex/standards/std_apply.json
    - Navigation-group: meta_tooling
    
    """
    surgeon = SourceSurgeon(config.get("root_hint"))
    mode = config.get("mode", "observe")
    plan = config.get("plan", {})
    
    if not plan:
        return {
            "metadata": {
                "status": "info",
                "message": "No plan provided. Returning usage examples.",
                "timestamp": surgeon.timestamp
            },
            "usage_guide": _get_usage_examples()
        }

    # Normalize plan: detect common nesting mistakes (e.g. payload under 'input_schema')
    original_plan = plan
    plan = surgeon._normalize_plan(plan, mode)
    was_corrected = plan is not original_plan

    try:
        if mode == "observe":
            data = surgeon.observe(plan)
            if was_corrected:
                data.setdefault("__meta", {})["_plan_corrected"] = (
                    "Plan payload was nested under a documentation key (e.g. 'input_schema'). "
                    "Auto-hoisted. Fix your plan JSON so targets/groups are at the plan top level."
                )
            # Append to observe history log (silent on failure)
            try:
                surgeon._write_observe_log(data)
            except Exception:
                pass
            return {
                "metadata": {"status": "success", "timestamp": surgeon.timestamp},
                "data": data
            }
        elif mode == "apply":
            dry_run = config.get("dry_run", True)
            validate_only = config.get("validate_only", False)
            capture_diffs = config.get("capture_diffs", True)
            snapshot_id = str(config.get("patch_id") or "").strip() or None
            enforce_target_routing = bool(config.get("enforce_target_routing", False))
            preferred_target_family = str(config.get("preferred_target_family") or "").strip() or None

            result = surgeon.apply_plan(
                plan,
                dry_run=dry_run,
                validate_only=validate_only,
                capture_diffs=capture_diffs,
                snapshot_id=snapshot_id,
                enforce_target_routing=enforce_target_routing,
                preferred_target_family=preferred_target_family,
            )
            
            return {
                "metadata": {"status": "success", "timestamp": surgeon.timestamp},
                "data": {
                    "logs": result.get("logs", []),
                    "diffs": result.get("diffs", []),
                    "failures": result.get("failures", []),
                    "warnings": result.get("warnings", []),
                    "dry_run": dry_run,
                    "touched_files": result.get("touched_files", []),
                    "snapshot": result.get("snapshot", {}),
                    "target_routing": result.get("target_routing", {}),
                }
            }
        else:
            return {
                "metadata": {"status": "failure", "error": f"Unknown mode {mode}", "timestamp": surgeon.timestamp},
                "data": None
            }
    except ApplyError as ae:
        return {
            "metadata": {
                "status": "failure", 
                "error": ae.message, 
                "timestamp": surgeon.timestamp
            },
            "data": {
                "failed_op_index": ae.op_index,
                "failed_op": ae.op,
                "error_detail": ae.detail,
                "completed_ops": ae.completed_ops, 
                "touched_files": ae.touched_files,
            }
        }
    except Exception as e:
        return {
            "metadata": {"status": "failure", "error": str(e), "timestamp": surgeon.timestamp},
            "data": None
        }

if __name__ == "__main__":
    print("Use tools/meta/run_meta.py to execute this tool.")
