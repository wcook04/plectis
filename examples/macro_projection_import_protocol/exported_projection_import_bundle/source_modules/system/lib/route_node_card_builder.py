"""
Build compact route-node cards for bounded semantic-routing worker packets.

[PURPOSE]
- Teleology: Give cheap route workers a structured file surface that is richer
  than a path list and cheaper than raw browsing.
- Mechanism: Extract deterministic metadata from local files: path tokens,
  kind, authority plane, headings, JSON keys, Python symbols/imports, top terms,
  exact mentions, and small evidence snippets.
- Non-goal: This module does not call models, score edges, or mutate route
  graphs.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "also",
    "because",
    "before",
    "being",
    "between",
    "could",
    "from",
    "have",
    "into",
    "like",
    "more",
    "must",
    "only",
    "other",
    "path",
    "phase",
    "repo",
    "route",
    "routing",
    "seed",
    "should",
    "source",
    "state",
    "system",
    "target",
    "than",
    "that",
    "their",
    "there",
    "these",
    "this",
    "through",
    "what",
    "when",
    "where",
    "which",
    "with",
    "worker",
}

EXACT_MENTION_TERMS = [
    "nvidia",
    "nim",
    "deepseek",
    "glm",
    "opencode",
    "claude",
    "cursor",
    "rosetta",
    "hologram",
    "embedding",
    "rerank",
    "semantic",
    "standard",
    "principle",
    "axiom",
    "scope_manifest",
    "synth_seed",
    "type_a",
]


def _slug(value: str, *, max_len: int = 72) -> str:
    token = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    token = re.sub(r"_+", "_", token)
    return token[:max_len].strip("_") or "node"


def stable_node_id(path: str) -> str:
    suffix = hashlib.sha1(path.encode("utf-8")).hexdigest()[:8]
    return f"N_{_slug(Path(path).stem)}_{suffix}"


def read_text_sample(repo_root: Path, path: str, *, max_chars: int = 24000) -> str:
    try:
        return (repo_root / path).read_text(encoding="utf-8", errors="replace")[:max_chars]
    except OSError:
        return ""


def top_terms(text: str, *, limit: int = 16) -> list[str]:
    words = [
        word.lower()
        for word in re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", text)
        if word.lower() not in STOPWORDS and len(word) <= 36
    ]
    return [word for word, _count in Counter(words).most_common(limit)]


def path_tokens(path: str) -> list[str]:
    return top_terms(path.replace("/", " ").replace("_", " ").replace("-", " "), limit=12)


def path_kind(path: str) -> str:
    if path.endswith(".py"):
        return "python_runtime"
    if path.endswith(".json"):
        return "json_contract"
    if path.endswith(".md"):
        return "paper_or_annex_note"
    if path.endswith((".ts", ".tsx")):
        return "typescript_runtime"
    return "artifact"


def authority_plane(path: str) -> str:
    if "/standards/" in path or path.startswith("codex/standards/"):
        return "standard"
    if "/paper_modules/" in path or path.startswith("codex/doctrine/paper_modules/"):
        return "paper_module"
    if "/skills/" in path or path.startswith("codex/doctrine/skills/"):
        return "skill"
    if "/raw_seed/" in path or path.endswith("raw_seed.md"):
        return "raw_seed_projection"
    if path.startswith("system/") or path.startswith("tools/"):
        return "runtime"
    if path.startswith("state/"):
        return "state_receipt"
    if path.startswith("annexes/") or "/annexes/" in path:
        return "annex_review"
    return "artifact"


def role_hint(path: str) -> str:
    if "raw_seed_principles" in path:
        return "principle authority source"
    if "system_axiom_candidates" in path:
        return "candidate axiom compression layer"
    if "navigation_hologram_theory" in path:
        return "navigation and routing theory"
    if "inference_tier_ladder" in path:
        return "model tier and authority boundary doctrine"
    if "std_navigation_rosetta" in path:
        return "legal route verb and edge grammar"
    if "nvidia_nim_backend" in path:
        return "NVIDIA provider backend prose note; can be invalidated by newer runtime defaults"
    if path.endswith("nvidia_nim.py"):
        return "NVIDIA runtime client and current model/default authority"
    if path.endswith("type_a_worker_harness.py"):
        return "bounded provider worker harness"
    if path == "opencode.json":
        return "external harness provider config"
    if "scope_manifest" in path:
        return "bounded routing test manifest"
    if "synth_seed" in path:
        return "phase synthesis seed"
    if "opencode_nvidia_type_a_annex" in path:
        return "external harness annex and caveats"
    return "routeable artifact"


def json_keys(text: str, *, limit: int = 24) -> list[str]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    keys: list[str] = []

    def walk(value: Any) -> None:
        if len(keys) >= limit:
            return
        if isinstance(value, Mapping):
            for key, child in value.items():
                if len(keys) >= limit:
                    return
                token = str(key)
                if token not in keys:
                    keys.append(token)
                walk(child)
        elif isinstance(value, list):
            for child in value[:4]:
                walk(child)

    walk(payload)
    return keys


def markdown_headings(text: str, *, limit: int = 12) -> list[str]:
    headings: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^#{1,4}\s+(.+?)\s*$", line)
        if match:
            headings.append(match.group(1).strip())
        if len(headings) >= limit:
            break
    return headings


def python_symbols_and_imports(text: str, *, symbol_limit: int = 20, import_limit: int = 20) -> tuple[list[str], list[str]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [], []
    symbols: list[str] = []
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if len(symbols) < symbol_limit:
                symbols.append(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if len(imports) < import_limit:
                    imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                if len(imports) < import_limit:
                    imports.append(f"{module}.{alias.name}".strip("."))
    return symbols, imports


def domain_tags(path: str, text: str) -> list[str]:
    haystack = f"{path}\n{text[:12000]}".lower()
    tag_rules = {
        "authority": ["principle", "axiom", "governs", "authority", "doctrine"],
        "routing_grammar": ["connector", "verb", "route", "rosetta", "edge"],
        "navigation_theory": ["navigation", "hologram", "option surface", "reverse read"],
        "nvidia_provider": ["nvidia", "nim", "deepseek", "glm", "provider"],
        "embedding": ["embedding", "semantic", "vector", "retrieval", "nv-embed"],
        "runtime_harness": ["harness", "worker", "agent", "opencode", "claude"],
        "state_receipts": ["receipt", "state/", "candidate", "score", "raw_output"],
        "json_contract": ["schema_version", "json", "contract", "machine"],
        "python_runtime": ["def ", "class ", "subprocess", "requests", "argparse"],
        "currentness": ["default", "stale", "current", "version", "model"],
    }
    return [tag for tag, needles in tag_rules.items() if any(needle in haystack for needle in needles)][:8]


def verb_cues(path: str, text: str) -> list[str]:
    haystack = f"{path}\n{text[:12000]}".lower()
    cues: list[str] = []
    if path.endswith(".py") and ("default" in haystack or "model" in haystack):
        cues.append("runtime_defaults_may_invalidate_prose")
    if path.endswith(".py") and ("chat_completion" in haystack or "embed_texts" in haystack or "rerank" in haystack):
        cues.append("runtime_provider_feeds_consumers")
    if path.endswith(".md") and ("backend" in haystack or "provider" in haystack):
        cues.append("backend_prose_can_be_invalidated_by_runtime")
    if "scope_manifest" in path or "navigation" in haystack:
        cues.append("navigation_surface_routes_to_context")
    if "schema" in haystack or "json" in haystack:
        cues.append("schema_or_json_surface_can_populate_artifacts")
    return cues[:6]


def exact_mentions(text: str, path: str) -> list[str]:
    haystack = f"{path}\n{text[:20000]}".lower()
    mentions = [term for term in EXACT_MENTION_TERMS if term.lower() in haystack]
    path_stem = Path(path).stem
    if path_stem and path_stem.lower() in haystack and path_stem not in mentions:
        mentions.append(path_stem)
    return mentions[:18]


def evidence_snippets(path: str, text: str, *, limit: int = 5) -> list[dict[str, str]]:
    snippets: list[dict[str, str]] = []
    if path.endswith(".py"):
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")) or "DEFAULT_" in stripped:
                snippets.append({"label": "python anchor", "text": stripped[:220]})
            if len(snippets) >= limit:
                return snippets
    if path.endswith(".md"):
        for heading in markdown_headings(text, limit=limit):
            snippets.append({"label": "heading", "text": heading})
        return snippets[:limit]
    if path.endswith(".json"):
        for key in json_keys(text, limit=limit):
            snippets.append({"label": "json key", "text": key})
        return snippets[:limit]
    return snippets


def build_node_card(repo_root: Path, path: str, manifest_row: Mapping[str, Any] | None = None) -> dict[str, Any]:
    manifest = dict(manifest_row or {})
    text = read_text_sample(repo_root, path)
    symbols, imports = python_symbols_and_imports(text) if path.endswith(".py") else ([], [])
    keys = json_keys(text) if path.endswith(".json") else []
    headings = markdown_headings(text) if path.endswith(".md") else []
    return {
        "node_id": stable_node_id(path),
        "path": path,
        "kind": manifest.get("kind") or path_kind(path),
        "authority_plane": authority_plane(path),
        "compression_role": manifest.get("role") or role_hint(path),
        "open_for": manifest.get("open_for") or [],
        "exports_or_symbols": symbols,
        "imports_or_dependencies": imports,
        "json_keys_or_schema_terms": keys,
        "headings": headings,
        "path_tokens": path_tokens(path),
        "top_terms": top_terms(f"{path}\n{text}", limit=18),
        "domain_tags": domain_tags(path, text),
        "verb_cues": verb_cues(path, text),
        "exact_mentions": exact_mentions(text, path),
        "evidence_snippets": evidence_snippets(path, text),
        "known_authority_hint": f"{authority_plane(path)}; {role_hint(path)}",
        "source_fingerprint": hashlib.sha1(text.encode("utf-8")).hexdigest()[:16] if text else "missing",
    }


def build_node_cards(
    repo_root: Path,
    paths: Sequence[str],
    *,
    manifest_rows: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    by_path = {
        str(row.get("path")): row
        for row in manifest_rows or []
        if isinstance(row, Mapping) and row.get("path")
    }
    return [build_node_card(repo_root, path, by_path.get(path)) for path in paths]


def slim_node_card(card: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "node_id": card.get("node_id"),
        "path": card.get("path"),
        "kind": card.get("kind"),
        "authority_plane": card.get("authority_plane"),
        "compression_role": card.get("compression_role"),
        "domain_tags": card.get("domain_tags") or [],
        "verb_cues": card.get("verb_cues") or [],
    }
