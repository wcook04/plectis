"""
[PURPOSE]
- Teleology: Walk the in-repo agent harness configuration substrate
  (.claude/ + codex/doctrine/skills + codex/doctrine/paper_modules +
  reactions.yaml + settings.local.json) and surface inefficiencies, drift,
  and bugs as one structured report. Sibling to `tools/meta/hygiene.py`
  (Python compliance) and `paper_module_coverage` (drift queue) — covers
  the harness configuration plane those skills do not.
- Mechanism: Per-surface checkers each return a list of Finding records
  (severity / kind / target / message). The auditor composes them, prints
  pretty by default or JSON for downstream consumers, and exits with code
  reflecting the worst severity (under --strict, warnings also exit non-zero).
- Non-goal: Does not mutate any file. Does not call out to bridge or
  subagents. Does not replace `tools/meta/hygiene.py` (Python compliance) or
  `paper_module_coverage` (subsystem drift queue). Reports are observation
  only — promotion through skill_authoring / paper_module_authoring / direct
  edits remains the operator's call.

[INTERFACE]
- main(argv) — CLI entry. Flags: --json (machine output), --kind <name>
  (run one checker), --strict (warnings exit non-zero), --quiet (errors only).
- HarnessAuditor(repo_root).run_all() -> list[Finding] for programmatic use.

[FLOW]
1. Discover repo root from script path.
2. For each enabled check, collect findings into one list.
3. Pretty-print grouped by severity, or emit `{summary, findings}` JSON.
4. Exit 0 (clean) / 1 (errors) / 2 (warnings under --strict).

[DEPENDENCIES]
- json, yaml, re, sys, argparse, subprocess, pathlib, dataclasses — stdlib
  plus PyYAML (already a repo dep).
- system.lib.launchable_operations.CATALOG — for reactions cross-check.
- system.lib.principle_projection.scan_principle_projection_contract — for
  point-of-use principle grounding checks.
- tools.meta.factory.build_skill_catalog_projection — for projection drift.

[CONSTRAINTS]
- Read-only. Never writes to disk.
- Each checker isolated: one failure does not abort the others.
- Must run on a clean checkout — no setup state required.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.parse
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib.principle_projection import scan_principle_projection_contract  # noqa: E402

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}
PRINCIPLE_PROJECTION_SEVERITY = {"P0": "error", "P1": "warning", "P2": "info", "P3": "info"}


@dataclass
class Finding:
    severity: str
    kind: str
    target: str
    message: str
    extra: dict[str, Any] = field(default_factory=dict)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _load_json_detect_duplicates(path: Path) -> tuple[Any, list[tuple[str, int]]]:
    """Load JSON and return (data, [(key, count)]) for any duplicate keys at any depth.

    json.loads silently drops duplicate keys. Use object_pairs_hook to catch them.
    """
    dups: list[tuple[str, int]] = []

    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        seen_counts: dict[str, int] = {}
        for key, _ in pairs:
            seen_counts[key] = seen_counts.get(key, 0) + 1
        for key, count in seen_counts.items():
            if count > 1:
                dups.append((key, count))
        return dict(pairs)

    data = json.loads(path.read_text(), object_pairs_hook=hook)
    return data, dups


def _load_skill_types_standard(repo_root: Path) -> dict[str, Any] | None:
    """Load codex/standards/std_skill_types.json if present. Returns None on absence."""
    p = repo_root / "codex/standards/std_skill_types.json"
    if not p.exists():
        return None
    return _load_json(p)


def _load_frontmatter(path: Path) -> dict[str, Any] | None:
    text = path.read_text(errors="ignore")
    # Tolerate leading HTML comments and blank lines before the YAML --- block.
    # Some skill files (e.g. reversal_tracking.md, distillation_rubric.md) prepend
    # an HTML `<!-- purpose: ... -->` block before the frontmatter for semantic
    # commentary; strip those before looking for the fence.
    stripped = re.sub(r"\A(?:\s*<!--.*?-->\s*)+", "", text, flags=re.DOTALL)
    match = re.match(r"---\s*\n(.*?)\n---\s*\n", stripped, re.DOTALL)
    if not match:
        return None
    payload = yaml.safe_load(match.group(1)) or {}
    return payload if isinstance(payload, dict) else None


def _resolve_local_doc_link(repo_root: Path, source_path: Path, raw_target: str) -> Path | None:
    target = urllib.parse.unquote(raw_target.split("#", 1)[0].strip())
    if not target or target.startswith(("http://", "https://", "mailto:")):
        return None
    if target.startswith("/"):
        return Path(target)
    if target.startswith(("./", "../")):
        return (source_path.parent / target).resolve()
    repo_relative = (repo_root / target).resolve()
    if repo_relative.exists():
        return repo_relative
    return (source_path.parent / target).resolve()


def _load_doctrine_node_ids() -> tuple[set[str], set[str], set[str]]:
    concepts: set[str] = set()
    mechanisms: set[str] = set()
    principles: set[str] = set()

    idx_path = REPO_ROOT / "codex/doctrine/doctrine_index.json"
    if idx_path.exists():
        idx = _load_json(idx_path)
        for n in idx.get("concepts", []) or []:
            if isinstance(n, dict) and n.get("id"):
                concepts.add(n["id"])
        for n in idx.get("mechanisms", []) or []:
            if isinstance(n, dict) and n.get("id"):
                mechanisms.add(n["id"])

    for con_file in (REPO_ROOT / "codex/doctrine/concepts").glob("con_*.json"):
        try:
            d = _load_json(con_file)
            cid = d.get("id") or d.get("concept_id")
            if cid:
                concepts.add(cid)
        except Exception:
            continue

    for mech_file in (REPO_ROOT / "codex/doctrine/mechanisms").glob("mech_*.json"):
        try:
            d = _load_json(mech_file)
            mid = d.get("id") or d.get("mechanism_id")
            if mid:
                mechanisms.add(mid)
        except Exception:
            continue

    for principle_file in (REPO_ROOT / "obsidian").glob("**/raw_seed/raw_seed_principles.json"):
        try:
            payload = _load_json(principle_file)
            entries = payload.get("principles") if isinstance(payload, dict) else None
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict) and entry.get("id"):
                        principles.add(entry["id"])
        except Exception:
            continue

    return concepts, mechanisms, principles


class HarnessAuditor:
    def __init__(self, repo_root: Path = REPO_ROOT) -> None:
        self.root = repo_root
        self._concept_ids: set[str] | None = None
        self._mechanism_ids: set[str] | None = None
        self._principle_ids: set[str] | None = None

    def _doctrine_ids(self) -> tuple[set[str], set[str], set[str]]:
        if self._concept_ids is None:
            self._concept_ids, self._mechanism_ids, self._principle_ids = _load_doctrine_node_ids()
        return self._concept_ids, self._mechanism_ids, self._principle_ids  # type: ignore[return-value]

    def check_skill_registry(self) -> list[Finding]:
        findings: list[Finding] = []
        reg_path = self.root / "codex/doctrine/skills/skill_registry.json"
        reg, dup_keys = _load_json_detect_duplicates(reg_path)

        # Duplicate JSON key detection — silent data loss in any plain json.loads.
        for key, count in dup_keys:
            findings.append(Finding(
                "error", "skill_registry_duplicate_json_key", key,
                f"duplicate key {key!r} appears {count} times — json.loads silently drops all but one",
            ))

        # Load the skill_types sibling standard for enum + per-class validation.
        skill_types_std = _load_skill_types_standard(self.root)
        valid_skill_types: set[str] = set()
        per_class_required_fields: dict[str, list[str]] = {}
        if skill_types_std:
            types_block = skill_types_std.get("skill_types", {})
            for key, val in types_block.items():
                if key.startswith("_"):
                    continue
                if isinstance(val, dict):
                    valid_skill_types.add(key)
                    req = val.get("required_agent_surface_fields") or []
                    if isinstance(req, list):
                        per_class_required_fields[key] = [f for f in req if isinstance(f, str)]

        ids: set[str] = set()
        skill_entries: list[tuple[str, dict[str, Any]]] = []
        registered_files: set[str] = set()
        for fam in reg.get("families", []):
            for s in fam.get("skills", []):
                ids.add(s["id"])
                skill_entries.append((fam.get("family_id", "?"), s))
                if s.get("file"):
                    registered_files.add(s["file"])

        con_ids, mech_ids, pri_ids = self._doctrine_ids()

        # Build frontmatter → registry skill_type map once (for mismatch check).
        frontmatter_skill_types: dict[str, str] = {}
        skill_families_dir = self.root / "codex/doctrine/skills"
        for path in skill_families_dir.glob("*/*.md"):
            frontmatter = _load_frontmatter(path)
            if not frontmatter:
                continue
            fid = frontmatter.get("id")
            ftype = frontmatter.get("skill_type")
            if isinstance(fid, str) and isinstance(ftype, str):
                frontmatter_skill_types[fid] = ftype

        # Aggregate coverage tally for skill_type.
        typed_count = 0
        by_class: dict[str, int] = {}

        for family_id, s in skill_entries:
            sid = s["id"]
            file_rel = s.get("file")
            if file_rel and not (self.root / file_rel).exists():
                findings.append(Finding(
                    "error", "skill_registry_missing_file", sid,
                    f"declared file {file_rel} does not exist",
                ))
            for c in s.get("composes_with", []):
                if c not in ids:
                    findings.append(Finding(
                        "error", "skill_registry_broken_composes_with", sid,
                        f"composes_with={c!r} is not a registered skill id",
                    ))
            if not s.get("agent_surface"):
                findings.append(Finding(
                    "warning", "skill_registry_missing_agent_surface", sid,
                    "no agent_surface block (downstream projections fall back to defaults)",
                ))
            holographic = s.get("holographic") or {}
            if not holographic.get("one_liner"):
                findings.append(Finding(
                    "warning", "skill_registry_missing_one_liner", sid,
                    "holographic.one_liner missing — degrades skill_map browse surface",
                ))
            edges = s.get("doctrine_edges", {}) or {}
            for c in edges.get("concepts", []):
                if c not in con_ids:
                    findings.append(Finding(
                        "warning", "skill_registry_unknown_concept_edge", sid,
                        f"doctrine_edges.concepts cites {c} — not in doctrine index",
                    ))
            for m in edges.get("mechanisms", []):
                if m not in mech_ids:
                    findings.append(Finding(
                        "warning", "skill_registry_unknown_mechanism_edge", sid,
                        f"doctrine_edges.mechanisms cites {m} — not in doctrine index",
                    ))
            for p in edges.get("principles", []):
                if p not in pri_ids:
                    findings.append(Finding(
                        "warning", "skill_registry_unknown_principle_edge", sid,
                        f"doctrine_edges.principles cites {p} — not in raw_seed_principles registry",
                    ))

            # skill_type enum + per-class required fields + frontmatter mismatch.
            reg_type = s.get("skill_type")
            if reg_type:
                typed_count += 1
                by_class[reg_type] = by_class.get(reg_type, 0) + 1
                if valid_skill_types and reg_type not in valid_skill_types:
                    findings.append(Finding(
                        "error", "skill_registry_invalid_skill_type", sid,
                        f"skill_type={reg_type!r} is not in std_skill_types.json enum ({sorted(valid_skill_types)})",
                    ))
                elif reg_type in per_class_required_fields:
                    agent_surface = s.get("agent_surface") or {}
                    for req_field in per_class_required_fields[reg_type]:
                        val = agent_surface.get(req_field)
                        if not (isinstance(val, str) and val.strip()):
                            findings.append(Finding(
                                "warning", "skill_registry_missing_required_agent_surface_field",
                                sid,
                                f"skill_type={reg_type!r} requires agent_surface.{req_field}, which is missing or empty",
                            ))

            # frontmatter mismatch (only when both carry a value).
            fm_type = frontmatter_skill_types.get(sid)
            if fm_type and reg_type and fm_type != reg_type:
                findings.append(Finding(
                    "warning", "skill_registry_skill_type_mismatch", sid,
                    f"registry skill_type={reg_type!r} does not match frontmatter {fm_type!r}",
                ))
            if fm_type and valid_skill_types and fm_type not in valid_skill_types:
                findings.append(Finding(
                    "error", "skill_registry_invalid_skill_type", sid,
                    f"frontmatter skill_type={fm_type!r} is not in std_skill_types.json enum",
                ))

        # Orphan-file check. Skips:
        # - schema / projection / scratchpad stems (internal helpers)
        # - files without full frontmatter
        # - kind=redirect compatibility stubs (explicit deprecated-redirect convention)
        # - status=deprecated files (legacy lane stubs; not part of active surface)
        skipped_stems = {"_schema", "skill_map", "frontenddesign", "planning", "scratchpad"}
        for path in skill_families_dir.glob("*/*.md"):
            if path.stem in skipped_stems or path.stem.startswith("_"):
                continue
            frontmatter = _load_frontmatter(path)
            if not frontmatter:
                continue
            if not all(frontmatter.get(key) for key in ("id", "family", "kind", "title")):
                continue
            if frontmatter.get("kind") == "redirect":
                continue
            if frontmatter.get("status") == "deprecated":
                continue
            rel = path.relative_to(self.root).as_posix()
            if rel not in registered_files:
                findings.append(Finding(
                    "warning", "skill_registry_orphan_file", rel,
                    "skill file exists on disk but is not registered in skill_registry.json",
                ))

        # Single aggregate coverage summary — low-noise info row, not per-skill warnings.
        total_skills = len(skill_entries)
        coverage_pct = round(100 * typed_count / total_skills, 1) if total_skills else 0.0
        findings.append(Finding(
            "info", "skill_registry_skill_type_coverage",
            "skill_registry.json",
            f"skill_type coverage: {typed_count}/{total_skills} skills ({coverage_pct}%)",
            extra={"total": total_skills, "typed": typed_count, "coverage_pct": coverage_pct, "by_class": by_class},
        ))
        return findings

    def check_skill_doc_links(self) -> list[Finding]:
        findings: list[Finding] = []
        skill_families_dir = self.root / "codex/doctrine/skills"
        for path in skill_families_dir.glob("*/*.md"):
            frontmatter = _load_frontmatter(path)
            if not frontmatter:
                continue
            for entry in frontmatter.get("doc_links") or []:
                raw_target: str | None = None
                if isinstance(entry, str):
                    raw_target = entry
                elif isinstance(entry, dict):
                    candidate = entry.get("path")
                    if isinstance(candidate, str):
                        raw_target = candidate
                if not raw_target:
                    continue
                resolved = _resolve_local_doc_link(self.root, path, raw_target)
                if resolved is None or resolved.exists():
                    continue
                findings.append(Finding(
                    "warning", "skill_doc_link_rot", path.relative_to(self.root).as_posix(),
                    f"doc_links targets {raw_target} which does not exist",
                ))
        return findings

    def check_settings_local(self) -> list[Finding]:
        findings: list[Finding] = []
        path = self.root / ".claude/settings.local.json"
        if not path.exists():
            findings.append(Finding("warning", "settings_missing", str(path), ".claude/settings.local.json missing"))
            return findings
        settings = _load_json(path)
        allows = settings.get("permissions", {}).get("allow", [])

        for entry in allows:
            if not isinstance(entry, str):
                findings.append(Finding("warning", "settings_non_string_allow", repr(entry), "non-string allow entry"))
                continue
            stripped = entry.strip()
            if "grep" in stripped.lower() and len(stripped) > 60 and stripped.startswith("Bash("):
                findings.append(Finding(
                    "warning", "settings_long_grep_literal", stripped[:80] + "...",
                    "long-literal grep allow — broaden to Bash(grep:*) or Bash(rg:*) instead",
                ))
            if stripped == "Bash(-print)":
                findings.append(Finding(
                    "warning", "settings_orphan_flag", stripped,
                    "orphan-flag allow entry — remove; flag-only entries match nothing useful",
                ))
            if stripped.startswith("Bash(~/"):
                findings.append(Finding(
                    "info", "settings_home_path_in_bash", stripped,
                    "home-relative path in Bash allow — confirm intentional",
                ))
            m = re.match(r"Bash\(rm\s+-rf\s+(.+)\)", stripped)
            if m:
                target = m.group(1)
                if "*" not in target and not (self.root / target.lstrip("/")).exists() and not Path(target).exists():
                    findings.append(Finding(
                        "info", "settings_dead_rm_path", stripped,
                        f"rm -rf allow targets {target} — path does not currently exist",
                    ))

        if len(allows) > 80:
            findings.append(Finding(
                "info", "settings_allow_growth", f"{len(allows)} entries",
                "allow-list above 80 entries — consider broadening to glob patterns",
            ))
        return findings

    def check_hooks(self) -> list[Finding]:
        findings: list[Finding] = []
        settings_path = self.root / ".claude/settings.local.json"
        hook_script = self.root / ".claude/hooks/runtime_hook.py"
        if not settings_path.exists() or not hook_script.exists():
            return findings

        settings = _load_json(settings_path)
        declared = set((settings.get("hooks") or {}).keys())

        src = hook_script.read_text()
        m = re.search(r"CANONICAL_HOOK_NAMES\s*=\s*\{([^}]*)\}", src, re.DOTALL)
        implemented: set[str] = set()
        if m:
            for line in m.group(1).splitlines():
                kv = re.search(r'"([^"]+)":\s*"([^"]+)"', line)
                if kv:
                    implemented.add(kv.group(2))

        for ev in sorted(declared - implemented):
            findings.append(Finding(
                "error", "hook_declared_not_implemented", ev,
                f"settings declares hook {ev} but runtime_hook.py CANONICAL_HOOK_NAMES does not handle it",
            ))
        for ev in sorted(implemented - declared):
            findings.append(Finding(
                "info", "hook_implemented_not_declared", ev,
                f"runtime_hook.py handles {ev} but settings.local.json does not wire it",
            ))

        hooks = settings.get("hooks") or {}
        if not isinstance(hooks, dict):
            return findings
        for event_name, groups in sorted(hooks.items()):
            if not isinstance(groups, list):
                findings.append(Finding(
                    "warning", "hook_settings_invalid_event_shape", str(event_name),
                    "hook event entry must be a list of matcher groups",
                ))
                continue
            for group_index, group in enumerate(groups):
                if not isinstance(group, dict):
                    findings.append(Finding(
                        "warning", "hook_settings_invalid_group_shape", f"{event_name}[{group_index}]",
                        "hook matcher group must be an object",
                    ))
                    continue
                for hook_index, hook in enumerate(group.get("hooks") or []):
                    if not isinstance(hook, dict):
                        findings.append(Finding(
                            "warning", "hook_settings_invalid_command_shape",
                            f"{event_name}[{group_index}].hooks[{hook_index}]",
                            "hook command entry must be an object",
                        ))
                        continue
                    if hook.get("type") != "command" or "runtime_hook.py" not in str(hook.get("command") or ""):
                        continue
                    target = f"{event_name}[{group_index}].hooks[{hook_index}]"
                    timeout_value = hook.get("timeout", group.get("timeout"))
                    if timeout_value is None:
                        findings.append(Finding(
                            "warning", "hook_command_missing_timeout", target,
                            (
                                "runtime_hook.py command hook has no timeout metadata; ignored local "
                                ".claude/settings.local.json should keep decision-kernel hooks sync with an explicit short timeout"
                            ),
                            {
                                "settings_policy": "decision_kernel_sync_timeout_required",
                                "remediation": "add a positive timeout to the local command hook; do not set async=true for runtime_hook.py",
                                "tracked_policy_ref": "codex/doctrine/paper_modules/runtime_hook_ladder.md#hook-settings-policy",
                            },
                        ))
                    elif not isinstance(timeout_value, (int, float)) or timeout_value <= 0:
                        findings.append(Finding(
                            "warning", "hook_command_invalid_timeout", target,
                            "runtime_hook.py command hook timeout must be a positive number",
                            {"timeout": timeout_value},
                        ))
                    if hook.get("async", group.get("async")) is True:
                        findings.append(Finding(
                            "error", "hook_decision_kernel_async", target,
                            "runtime_hook.py is a synchronous decision kernel; async tails need a separate command with dedupe/backpressure",
                        ))
        return findings

    def check_agents(self) -> list[Finding]:
        findings: list[Finding] = []
        agents_dir = self.root / ".claude/agents"
        if not agents_dir.exists():
            findings.append(Finding("info", "agents_dir_missing", str(agents_dir), "no .claude/agents directory"))
            return findings
        for path in agents_dir.glob("*.md"):
            text = path.read_text()
            front_match = re.match(r"---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
            if not front_match:
                findings.append(Finding(
                    "warning", "agent_missing_frontmatter", path.name,
                    "agent persona missing YAML frontmatter (name/description/model/tools)",
                ))
                continue
            front = yaml.safe_load(front_match.group(1)) or {}
            for required in ("name", "description", "model", "tools"):
                if required not in front:
                    findings.append(Finding(
                        "warning", "agent_missing_frontmatter_field", path.name,
                        f"agent persona frontmatter missing field {required!r}",
                    ))
        return findings

    def check_reactions(self) -> list[Finding]:
        findings: list[Finding] = []
        path = self.root / "reactions.yaml"
        if not path.exists():
            return findings
        try:
            data = yaml.safe_load(path.read_text()) or {}
        except yaml.YAMLError as exc:
            findings.append(Finding("error", "reactions_yaml_parse", str(path), f"YAML parse error: {exc}"))
            return findings

        try:
            from system.lib.launchable_operations import CATALOG
            catalog_ids = {op["operation_id"] for op in CATALOG}
        except Exception as exc:
            findings.append(Finding("error", "reactions_catalog_import", "launchable_operations.CATALOG",
                                    f"could not import launchable operation catalog: {exc}"))
            return findings

        for r in data.get("reactions", []) or []:
            rid = r.get("reaction_id", "?")
            action_op = (r.get("action") or {}).get("operation_id")
            if action_op and action_op not in catalog_ids:
                findings.append(Finding(
                    "error", "reactions_unknown_action_op", rid,
                    f"action.operation_id={action_op!r} not in launchable_operations.CATALOG",
                ))
            source_op = (r.get("source") or {}).get("operation_id")
            if source_op and source_op not in catalog_ids:
                findings.append(Finding(
                    "warning", "reactions_unknown_source_op", rid,
                    f"source.operation_id={source_op!r} not in launchable_operations.CATALOG",
                ))
        return findings

    def check_paper_modules(self) -> list[Finding]:
        findings: list[Finding] = []
        report_path = self.root / "codex/doctrine/paper_modules/_validation_report.json"
        if not report_path.exists():
            findings.append(Finding(
                "info", "paper_module_report_missing", str(report_path),
                "run `./repo-python tools/meta/factory/build_paper_module_index.py --check --report`",
            ))
            return findings
        report = _load_json(report_path)
        modules = report.get("modules") or []
        if isinstance(modules, dict):
            modules = list(modules.values())
        for module_report in modules:
            if not isinstance(module_report, dict):
                continue
            slug = module_report.get("slug") or module_report.get("file") or "?"
            for entry in module_report.get("findings", []) or []:
                level = entry.get("level") or entry.get("severity") or "warning"
                kind = entry.get("kind") or entry.get("rule") or "finding"
                msg = entry.get("message") or entry.get("detail") or ""
                findings.append(Finding(
                    level if level in SEVERITY_ORDER else "warning",
                    f"paper_module_{kind}", slug, msg,
                ))
        candidates = report.get("first_author_queue") or []
        if candidates:
            top = []
            for c in candidates[:5]:
                if isinstance(c, dict):
                    top.append(c.get("candidate_slug") or c.get("slug") or "?")
                else:
                    top.append(str(c))
            findings.append(Finding(
                "info", "paper_module_first_author_queue", "queue",
                f"{len(candidates)} subsystems lack a paper module — see paper_module_candidates.json",
                {"top_candidates": top},
            ))
        return findings

    def check_projection_drift(self) -> list[Finding]:
        findings: list[Finding] = []
        try:
            result = subprocess.run(
                ["./repo-python", "tools/meta/factory/build_skill_catalog_projection.py", "--check"],
                cwd=str(self.root), capture_output=True, text=True, timeout=60,
            )
        except Exception as exc:
            findings.append(Finding("warning", "projection_drift_runner", "build_skill_catalog_projection",
                                    f"could not invoke projection builder: {exc}"))
            return findings

        out = (result.stdout or "") + (result.stderr or "")
        for line in out.splitlines():
            if "DRIFT detected" in line:
                target = line.split(":", 1)[0].strip()
                findings.append(Finding(
                    "warning", "projection_drift", target,
                    "projection has drifted from substrate — refresh via build_skill_catalog_projection.py",
                ))
        return findings

    def check_principle_projection(self) -> list[Finding]:
        findings: list[Finding] = []
        audit = scan_principle_projection_contract(self.root)
        for item in audit.get("findings") or []:
            if not isinstance(item, dict):
                continue
            severity = PRINCIPLE_PROJECTION_SEVERITY.get(str(item.get("severity") or ""), "warning")
            finding_id = str(item.get("finding_id") or "principle_projection_contract")
            findings.append(Finding(
                severity,
                f"principle_projection_{finding_id}",
                str(item.get("surface") or "principle_projection_contract"),
                str(item.get("summary") or finding_id),
                {
                    "repair_surface": item.get("repair_surface"),
                    "evidence": item.get("evidence") or {},
                },
            ))
        return findings

    def check_doc_link_rot(self) -> list[Finding]:
        findings: list[Finding] = []
        link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
        # Repo-wide convention: markdown links MAY carry a :LINE suffix to point
        # at a specific line (per Claude/Codex system-prompt guidance). The suffix
        # is not part of the filesystem path — strip it before existence check.
        # Match a single trailing :N where N is a positive integer.
        line_suffix_re = re.compile(r":(\d+)$")
        for doc_name in ("CLAUDE.md", "AGENTS.md"):
            path = self.root / doc_name
            if not path.exists():
                continue
            text = path.read_text()
            for raw_target in link_re.findall(text):
                target = raw_target.split("#", 1)[0].split(" ", 1)[0]
                if not target or target.startswith(("http://", "https://", "mailto:")):
                    continue
                if target.startswith("/"):
                    continue
                decoded = urllib.parse.unquote(target)
                fs_path = line_suffix_re.sub("", decoded)
                resolved = (self.root / fs_path).resolve()
                if not resolved.exists():
                    findings.append(Finding(
                        "error", "doc_link_rot", doc_name,
                        f"{doc_name} links to {target} which does not exist",
                    ))
        return findings

    def run_all(self, kinds: Iterable[str] | None = None) -> list[Finding]:
        all_checks = {
            "skill_registry": self.check_skill_registry,
            "skill_doc_links": self.check_skill_doc_links,
            "settings_local": self.check_settings_local,
            "hooks": self.check_hooks,
            "agents": self.check_agents,
            "reactions": self.check_reactions,
            "paper_modules": self.check_paper_modules,
            "projection_drift": self.check_projection_drift,
            "principle_projection": self.check_principle_projection,
            "doc_link_rot": self.check_doc_link_rot,
        }
        selected = kinds or list(all_checks.keys())
        results: list[Finding] = []
        for name in selected:
            checker = all_checks.get(name)
            if not checker:
                results.append(Finding("warning", "unknown_check", name, f"no checker named {name!r}"))
                continue
            try:
                results.extend(checker())
            except Exception as exc:
                results.append(Finding(
                    "error", "checker_crash", name,
                    f"checker {name} raised {type(exc).__name__}: {exc}",
                ))
        return results


def _summarize(findings: list[Finding]) -> dict[str, int]:
    summary = {"error": 0, "warning": 0, "info": 0, "total": len(findings)}
    by_kind: dict[str, int] = {}
    for f in findings:
        summary[f.severity] = summary.get(f.severity, 0) + 1
        by_kind[f.kind] = by_kind.get(f.kind, 0) + 1
    summary["by_kind"] = by_kind  # type: ignore[assignment]
    return summary


def _print_pretty(findings: list[Finding], quiet: bool) -> None:
    summary = _summarize(findings)
    print(f"harness_audit: {summary['total']} findings ({summary['error']} error, {summary['warning']} warning, {summary['info']} info)")
    print()

    by_severity = {"error": [], "warning": [], "info": []}
    for f in findings:
        by_severity.setdefault(f.severity, []).append(f)

    for severity in ("error", "warning", "info"):
        items = by_severity.get(severity, [])
        if not items:
            continue
        if quiet and severity != "error":
            continue
        print(f"== {severity.upper()} ({len(items)}) ==")
        for f in items:
            print(f"  [{f.kind}] {f.target}: {f.message}")
        print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("[INTERFACE]")[0].strip())
    parser.add_argument("--json", action="store_true", help="emit JSON instead of pretty report")
    parser.add_argument("--kind", action="append", help="restrict to one or more checkers (repeatable)")
    parser.add_argument("--strict", action="store_true", help="exit non-zero on any warning")
    parser.add_argument("--quiet", action="store_true", help="show only error-severity findings")
    args = parser.parse_args(argv)

    auditor = HarnessAuditor()
    findings = auditor.run_all(args.kind)
    summary = _summarize(findings)

    if args.json:
        payload = {"summary": summary, "findings": [asdict(f) for f in findings]}
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _print_pretty(findings, args.quiet)

    if summary["error"] > 0:
        return 1
    if args.strict and summary["warning"] > 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
